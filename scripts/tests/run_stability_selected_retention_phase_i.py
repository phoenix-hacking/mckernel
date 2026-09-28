#!/usr/bin/env python3
"""Source-only Phase-I driver; this API is not an execution release.

The reviewed manifest is an independently pinned JSON document. It binds argv,
cwd, both roots, the complete declared input closure, archive mappings, exact
file/directory membership and the validator selection. Inputs are authenticated
before root creation and again after each child. The caller must supply the
exclusive source-owner lease; this program is not a sandbox for hostile code.

installation.json, validation.json and controls.json are append-only NDJSON
journals: each complete line is independently durable, including on failure.
They are deliberately never rewritten to turn an incomplete attempt into PASS.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile

DIAGNOSTIC_NAMES = frozenset(("authentication.json", "installation.json", "validation.json", "controls.json", "cr.bin", "space.bin", "tab.bin", "missing-lf.bin", "extra-blank.bin", "mode2-stage.stdout", "mode2-stage.stderr", "mode3-stage.stdout", "mode3-stage.stderr"))
CONTROL_CASES = (("cr.bin", b"x\r\n", "CR"), ("space.bin", b"x \n", "TRAILING"), ("tab.bin", b"x\t\n", "TRAILING"), ("missing-lf.bin", b"x", "FINAL_LF"), ("extra-blank.bin", b"x\n\n", "EXTRA_EOF_BLANK"))
VALIDATOR = '''import sys
def check(b):
    if b"\\r" in b: return "CR"
    if any(line.endswith((b" ", b"\\t")) for line in b.split(b"\\n")): return "TRAILING"
    if not b.endswith(b"\\n"): return "FINAL_LF"
    if b.endswith(b"\\n\\n"): return "EXTRA_EOF_BLANK"
    return None
assert check(b"x\\ny\\n") is None
assert check(b"x\\n\\ny\\n") is None
for data, expected in ((b"x\\r\\n", "CR"), (b"x \\n", "TRAILING"), (b"x\\t\\n", "TRAILING"), (b"x", "FINAL_LF"), (b"x\\n\\n", "EXTRA_EOF_BLANK")):
    assert check(data) == expected
if len(sys.argv) < 2: raise SystemExit("NO_INPUT")
for name in sys.argv[1:]:
    with open(name, "rb") as source: problem = check(source.read())
    if problem: raise SystemExit(problem + ":" + name)
print("PASS_WHITESPACE")'''
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _digest(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "bytes_hex": data.hex()}


def _identity(s):
    return {"dev": s.st_dev, "ino": s.st_ino, "uid": s.st_uid,
            "nlink": s.st_nlink, "mode": s.st_mode, "size": s.st_size,
            "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns}


def _same_inode(a, b):
    return (a.st_dev, a.st_ino, a.st_uid, a.st_mode) == (b.st_dev, b.st_ino, b.st_uid, b.st_mode)


def _write_all(fd, data):
    pos = 0
    while pos < len(data):
        n = os.write(fd, data[pos:])
        if n <= 0:
            raise OSError("short write")
        pos += n


def _line(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _new_file(dirfd, name, data):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dirfd)
    try:
        _write_all(fd, data)
        os.fsync(fd)
        os.fsync(dirfd)
    finally:
        os.close(fd)


def _json_at(dirfd, name, value):
    _new_file(dirfd, name, _line(value))


class Journal:
    def __init__(self, root, name):
        self.root, self.name = root, name
        self.fd = os.open(name, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root.fd)
        try:
            os.fsync(self.fd)
            os.fsync(root.fd)
        except BaseException:
            os.close(self.fd)
            raise
        self.identity = os.fstat(self.fd)

    def append(self, value):
        before = os.stat(self.name, dir_fd=self.root.fd, follow_symlinks=False)
        if not _same_inode(before, self.identity) or before.st_nlink != 1:
            raise ValueError("journal identity changed: " + self.name)
        _write_all(self.fd, _line(value))
        os.fsync(self.fd)
        os.fsync(self.root.fd)

    def close(self):
        os.close(self.fd)


def _root_preflight(path):
    p = Path(path)
    if str(p) != str(path) or not p.is_absolute() or any(c in str(p) for c in "\r\n") or os.path.lexists(p):
        raise ValueError("root must be absent, absolute, canonical and newline-free")
    if p.parent.resolve() != p.parent or not p.parent.is_dir():
        raise ValueError("root parent must be canonical")
    return p


class Root:
    """Keep both descriptors even when authentication or fsync subsequently fails."""
    def __init__(self, path, owner):
        self.path, self.owner = path, owner
        self.pfd = self.fd = None
        self.created = False

    def create(self):
        self.pfd = os.open(str(self.path.parent), DIR_FLAGS)
        self.parent_identity = os.fstat(self.pfd)
        old = os.umask(0o077)
        try:
            os.mkdir(self.path.name, 0o700, dir_fd=self.pfd)
            self.created = True
        finally:
            os.umask(old)
        self.fd = os.open(self.path.name, DIR_FLAGS, dir_fd=self.pfd)
        self.identity = os.fstat(self.fd)
        # Authenticate ownership immediately; make the directory entry durable
        # before any child or diagnostic work can begin.
        self.verify()
        os.fsync(self.pfd)
        os.fsync(self.fd)

    def verify(self):
        s = os.fstat(self.fd)
        named = os.stat(self.path.name, dir_fd=self.pfd, follow_symlinks=False)
        parent = os.stat(self.path.parent, follow_symlinks=False)
        if (self.path.parent.resolve() != self.path.parent or
                not _same_inode(parent, self.parent_identity) or
                not _same_inode(named, self.identity) or not _same_inode(s, self.identity) or
                not stat.S_ISDIR(s.st_mode) or stat.S_IMODE(s.st_mode) != 0o700 or
                s.st_uid != self.owner):
            raise ValueError("root identity changed: " + str(self.path))

    def close(self):
        for fd in (self.fd, self.pfd):
            if fd is not None:
                os.close(fd)


def _read_regular(dirfd, name, owner=None):
    before = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            (owner is not None and before.st_uid != owner)):
        raise ValueError("member must be regular, single-link and owner-local: " + name)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dirfd)
    try:
        if _identity(os.fstat(fd)) != _identity(before):
            raise ValueError("member changed while opening: " + name)
        chunks = []
        while True:
            b = os.read(fd, 1024 * 1024)
            if not b:
                break
            chunks.append(b)
        if (_identity(os.fstat(fd)) != _identity(before) or
                _identity(os.stat(name, dir_fd=dirfd, follow_symlinks=False)) != _identity(before)):
            raise ValueError("member changed while reading: " + name)
        return b"".join(chunks), _identity(before)
    finally:
        os.close(fd)


def _tree(root):
    files, directories = {}, {}
    root.verify()

    def visit(fd, prefix=""):
        for name in sorted(os.listdir(fd)):
            rel = prefix + name
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(s.st_mode):
                if s.st_uid != root.owner:
                    raise ValueError("directory owner mismatch: " + rel)
                child = os.open(name, DIR_FLAGS, dir_fd=fd)
                try:
                    if _identity(s) != _identity(os.fstat(child)):
                        raise ValueError("directory identity changed: " + rel)
                    directories[rel] = _identity(s)
                    visit(child, rel + "/")
                    if _identity(s) != _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)):
                        raise ValueError("directory changed during traversal: " + rel)
                finally:
                    os.close(child)
            else:
                data, identity = _read_regular(fd, name, root.owner)
                files[rel] = {"identity": identity, **_digest(data)}
    visit(root.fd)
    root.verify()
    return {"files": files, "directories": directories}


def _diagnostic_files(root, expected):
    tree = _tree(root)
    if tree["directories"] or set(tree["files"]) != set(expected) or not set(expected) <= DIAGNOSTIC_NAMES:
        raise ValueError("diagnostic membership violation")
    return tree


def _failure(rootfd, mode, stage, expected, observed):
    vals = ("FAIL_PHASE_I", mode if mode in ("mode2", "mode3", "global") else "global", stage, expected, observed, "PRESERVE_PARTIAL_ROOT_NO_RETRY")
    vals = tuple(str(v).replace("\r", "\\r").replace("\n", "\\n") for v in vals)
    data = "\n".join("%s=%s" % (k, v) for k, v in zip(("status", "mode", "stage", "expected", "observed", "action"), vals)) + "\n"
    _new_file(rootfd, "phase-i-failure.txt", data.encode())


class PhaseIFailure(RuntimeError):
    def __init__(self, stage, original, secondary=()):
        self.stage, self.original, self.secondary = stage, original, list(secondary)
        super().__init__(stage + ": " + str(original) + ("; evidence persistence: " + "; ".join(self.secondary) if self.secondary else ""))


def _relative(name):
    if (not isinstance(name, str) or not name or any(c in name for c in "\r\n") or
            PurePosixPath(name).is_absolute() or str(PurePosixPath(name)) != name or
            any(p in (".", "..") for p in PurePosixPath(name).parts)):
        raise ValueError("invalid member name")
    return name


def _pinned(item):
    path = Path(item["path"])
    if not path.is_absolute() or str(path) != item["path"] or path.parent.resolve() != path.parent:
        raise ValueError("input path must be canonical")
    data, identity = _read_regular(None, str(path))
    if _digest(data)["sha256"] != item["sha256"] or len(data) != item["size"]:
        raise ValueError("reviewed input hash/size mismatch: " + str(path))
    return data, identity


def _review(reviewed, command, candidate, diagnostics, cwd):
    if not isinstance(reviewed, dict) or set(reviewed) != {"manifest"}:
        raise ValueError("authenticated reviewed manifest required")
    raw, manifest_identity = _pinned(reviewed["manifest"])
    contract = json.loads(raw)
    if (contract["command_argv"] != list(command) or contract["cwd"] != cwd or
            contract["candidate_root"] != str(candidate) or contract["diagnostics_root"] != str(diagnostics)):
        raise ValueError("command, cwd or roots are not reviewed")
    inputs = contract["authenticated_inputs"]
    paths = [x["path"] for x in inputs]
    if (not inputs or len(paths) != len(set(paths)) or
            sorted(paths) != sorted(contract["required_inputs"]) or
            not contract["command_inputs"] or not set(contract["command_inputs"]) <= set(paths) or
            command[0] not in paths or str(Path(sys.executable).resolve()) not in paths):
        raise ValueError("complete authenticated input closure required")
    authenticated = {}
    for item in inputs:
        data, identity = _pinned(item)
        authenticated[item["path"]] = {"pin": item, "identity": identity, "data": data}
    expected, mapping = contract["expected_membership"], contract["archive_mapping"]
    if not expected or not mapping:
        raise ValueError("nonempty reviewed membership and archive mapping required")
    for name, spec in expected.items():
        _relative(name)
        if set(spec) != {"size", "sha256"} or not isinstance(spec["size"], int) or spec["size"] < 0 or len(spec["sha256"]) != 64:
            raise ValueError("invalid file specification")
    dirs = contract["expected_directories"]
    needed = {str(p) for name in expected for p in PurePosixPath(name).parents if str(p) != "."}
    if len(dirs) != len(set(dirs)) or set(dirs) != needed:
        raise ValueError("exact prescribed directory membership required")
    for name in dirs:
        _relative(name)
    selected = contract["validator_members"]
    if not selected or len(selected) != len(set(selected)) or set(selected) != set(mapping):
        raise ValueError("validator must cover every installed archive mapping")
    for name, source in mapping.items():
        _relative(name)
        _relative(source["member"])
        if name not in expected or source["archive"] not in authenticated:
            raise ValueError("mapping outside authenticated closure")
        # Read only pinned archive bytes; do not extract or execute a member.
        with tarfile.open(fileobj=io.BytesIO(authenticated[source["archive"]]["data"]), mode="r:*") as archive:
            members = [m for m in archive.getmembers() if m.name == source["member"]]
            if len(members) != 1 or not members[0].isfile():
                raise ValueError("archive member missing, duplicate or nonregular")
            data = archive.extractfile(members[0]).read()
            if {k: _digest(data)[k] for k in ("size", "sha256")} != expected[name]:
                raise ValueError("archive mapping bytes mismatch")
    timeout = contract["timeout_seconds"]
    if not isinstance(timeout, int) or not 1 <= timeout <= 300:
        raise ValueError("bounded child timeout required")
    return contract, {"manifest": {"pin": reviewed["manifest"], "identity": manifest_identity},
                      "inputs": {p: {k: v for k, v in item.items() if k != "data"} for p, item in authenticated.items()}}


def _membership(root, contract):
    tree = _tree(root)
    if set(tree["files"]) != set(contract["expected_membership"]) or set(tree["directories"]) != set(contract["expected_directories"]):
        raise ValueError("reviewed membership mismatch")
    for name, spec in contract["expected_membership"].items():
        if any(tree["files"][name][key] != spec[key] for key in ("sha256", "size")):
            raise ValueError("reviewed member hash mismatch: " + name)
    return tree


def run_phase_i(candidate_root, diagnostics_root, command, *, controls=True, cwd=None, reviewed=None):
    if not controls:
        raise ValueError("all five controls are mandatory")
    cwd = str(cwd or Path(__file__).resolve().parents[2])
    contract, authentication = _review(reviewed, command, candidate_root, diagnostics_root, cwd)
    rp, dp = _root_preflight(candidate_root), _root_preflight(diagnostics_root)
    if rp == dp or rp in dp.parents or dp in rp.parents:
        raise ValueError("roots overlap")
    r, d = Root(rp, os.geteuid()), Root(dp, os.geteuid())
    journals, expected_diagnostics = [], set()
    stage = "root-create"

    def journal(name):
        j = Journal(d, name)
        journals.append(j)
        expected_diagnostics.add(name)
        return j

    def verify_roots_inputs():
        r.verify()
        d.verify()
        _, current = _review(reviewed, command, candidate_root, diagnostics_root, cwd)
        if current != authentication:
            raise ValueError("authenticated input identity changed")

    def child(argv, log, expected, label):
        # No postprocess, membership or stream-file write precedes publication
        # of this result. A failed child stays the primary failure if publishing
        # its result also fails. The exception carries the bytes to the caller.
        record = {"event": label, "argv": list(argv), "cwd": cwd}
        failure = None
        try:
            cp = subprocess.run(argv, cwd=cwd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False, timeout=contract["timeout_seconds"])
            record.update(returncode=cp.returncode, stdout=_digest(cp.stdout), stderr=_digest(cp.stderr))
            if cp.returncode != expected[0] or (expected[1] is not None and cp.stdout != expected[1]) or (expected[2] is not None and cp.stderr != expected[2]):
                failure = RuntimeError("unexpected process result: " + json.dumps(record, sort_keys=True))
        except Exception as exc:
            record.update(launch_error=repr(exc), stdout=_digest(getattr(exc, "stdout", None) or b""),
                          stderr=_digest(getattr(exc, "stderr", None) or b""))
            failure = exc
        try:
            log.append(record)
        except Exception as exc:
            raise PhaseIFailure(label, failure or RuntimeError(json.dumps(record)), [repr(exc)]) from exc
        if failure is not None:
            raise PhaseIFailure(label, failure)
        verify_roots_inputs()
        return cp

    try:
        r.create()
        d.create()
        stage = "authentication"
        _json_at(d.fd, "authentication.json", {"authenticated": authentication, "contract": contract,
                 "candidate_root": _identity(os.fstat(r.fd)), "diagnostics_root": _identity(os.fstat(d.fd))})
        expected_diagnostics.add("authentication.json")
        install = journal("installation.json")
        stage = "installation"
        pre = _tree(r)
        install.append({"event": "pre-install", "candidate": pre})
        cp = child(list(command), install, (0, None, None), "installation-process")
        stage = "installation-streams"
        for name, data in (("mode2-stage.stdout", cp.stdout), ("mode2-stage.stderr", cp.stderr)):
            _new_file(d.fd, name, data)
            expected_diagnostics.add(name)
        stage = "membership"
        post = _membership(r, contract)
        install.append({"event": "post-install", "candidate": post, "archive_mapping": contract["archive_mapping"]})
        _diagnostic_files(d, expected_diagnostics)
        stage = "candidate-validator"
        validation = journal("validation.json")
        python = str(Path(sys.executable).resolve())
        argv = [python, "-B", "-c", VALIDATOR] + [str(r.path / name) for name in contract["validator_members"]]
        child(argv, validation, (0, b"PASS_WHITESPACE\n", b""), stage)
        if _membership(r, contract) != post:
            raise ValueError("candidate changed during validator")
        stage = "controls"
        control_log = journal("controls.json")
        for name, payload, prefix in CONTROL_CASES:
            stage = "control-" + name
            _new_file(d.fd, name, payload)
            expected_diagnostics.add(name)
            before = _diagnostic_files(d, expected_diagnostics)["files"][name]
            if before["sha256"] != _digest(payload)["sha256"]:
                raise ValueError("control input mismatch")
            path = str(d.path / name)
            child([python, "-B", "-c", VALIDATOR, path], control_log, (1, b"", (prefix + ":" + path + "\n").encode()), stage)
            if _diagnostic_files(d, expected_diagnostics)["files"][name] != before:
                raise ValueError("control changed during validator")
            if _membership(r, contract) != post:
                raise ValueError("candidate changed during control")
        stage = "finalization"
        verify_roots_inputs()
        _diagnostic_files(d, expected_diagnostics)
        if _membership(r, contract) != post:
            raise ValueError("candidate changed before finalization")
        result = {"status": "PASS_PHASE_I", "argv": list(command), "returncode": cp.returncode,
                  "candidate": post, "controls": 5}
        validation.append({"event": "complete", **result})
        return result
    except Exception as exc:
        failure = exc if isinstance(exc, PhaseIFailure) else PhaseIFailure(stage, exc)
        if r.fd is not None:
            try:
                _failure(r.fd, "global", failure.stage, "reviewed Phase-I contract", str(failure))
            except Exception as persist:
                failure = PhaseIFailure(failure.stage, failure.original, failure.secondary + ["failure-record: " + repr(persist)])
        elif r.created:
            failure = PhaseIFailure(failure.stage, failure.original, failure.secondary + ["failure-record: created root could not be opened safely"])
        raise failure from exc
    finally:
        for j in journals:
            j.close()
        r.close()
        d.close()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-root", required=True)
    p.add_argument("--diagnostics-root", required=True)
    p.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    p.parse_args(argv)
    raise SystemExit("reviewed contract API required; no CLI release")


if __name__ == "__main__":
    main()
