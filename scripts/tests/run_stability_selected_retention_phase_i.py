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
if not __debug__: raise SystemExit("SELF_TESTS_DISABLED")
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


def _secondary_close(exc, label, close_error):
    """Keep *exc* primary while making a cleanup failure inspectable."""
    text = "SECONDARY_CLOSE_%s: %r" % (label, close_error)
    secondary = getattr(exc, "secondary", None)
    if secondary is not None:
        secondary.append(text)
        if hasattr(exc, "args"):
            exc.args = (str(exc).split("; evidence persistence:", 1)[0] +
                        "; evidence persistence: " + "; ".join(secondary),)
    else:
        notes = getattr(exc, "__notes__", [])
        notes.append(text)
        exc.__notes__ = notes


def _close_preserving(exc, fd, label):
    if fd is None:
        return
    try:
        os.close(fd)
    except Exception as close_error:
        _secondary_close(exc, label, close_error)


def _line(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _new_file(dirfd, name, data):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dirfd)
    try:
        _write_all(fd, data)
        os.fsync(fd)
        os.fsync(dirfd)
        identity = _identity(os.fstat(fd))
        if (identity != _identity(os.stat(name, dir_fd=dirfd, follow_symlinks=False)) or
                identity["nlink"] != 1 or identity["uid"] != os.geteuid()):
            raise ValueError("new evidence file identity changed: " + name)
        result = {"identity": identity, **_digest(data)}
    except BaseException as exc:
        _close_preserving(exc, fd, "NEW_FILE_%s" % name)
        raise
    else:
        os.close(fd)
        return result


def _json_at(dirfd, name, value):
    return _new_file(dirfd, name, _line(value))


class Journal:
    def __init__(self, root, name):
        self.root, self.name = root, name
        self.fd = os.open(name, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root.fd)
        try:
            os.fsync(self.fd)
            os.fsync(root.fd)
            self.identity = os.fstat(self.fd)
        except BaseException as exc:
            _close_preserving(exc, self.fd, "JOURNAL_INIT_%s" % name)
            self.fd = None
            raise
        self.data = b""

    def verify(self):
        data, identity = _read_regular(self.root.fd, self.name, self.root.owner)
        if identity != _identity(self.identity) or data != self.data:
            raise ValueError("journal identity/content changed: " + self.name)

    def append(self, value):
        self.verify()
        data = _line(value)
        _write_all(self.fd, data)
        os.fsync(self.fd)
        os.fsync(self.root.fd)
        self.identity = os.fstat(self.fd)
        self.data += data
        self.verify()

    def close(self):
        fd, self.fd = self.fd, None
        if fd is not None:
            os.close(fd)


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

    def close(self, on_errors=None):
        errors = []
        backup = None
        if on_errors is not None and self.fd is not None:
            try:
                backup = os.dup(self.fd)
            except Exception as exc:
                errors.append("SECONDARY_CLOSE_ROOT_BACKUP: %r" % (exc,))
        for attr in ("fd", "pfd"):
            fd = getattr(self, attr)
            setattr(self, attr, None)
            if fd is not None:
                try:
                    os.close(fd)
                except Exception as exc:
                    errors.append("SECONDARY_CLOSE_ROOT_%s: %r" % (attr.upper(), exc))
        if on_errors is not None:
            try:
                on_errors(errors, backup)
            finally:
                if backup is not None:
                    try:
                        os.close(backup)
                    except Exception:
                        # The original close report is already published; a
                        # duplicate cleanup close must never replace it.
                        pass
        return errors


def _read_regular(dirfd, name, owner=None):
    before = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            (owner is not None and before.st_uid != owner)):
        raise ValueError("member must be regular, single-link and owner-local: " + name)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
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
        result = b"".join(chunks), _identity(before)
    except BaseException as exc:
        _close_preserving(exc, fd, "READ_REGULAR_%s" % name)
        raise
    else:
        os.close(fd)
        return result


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
                except BaseException as exc:
                    # A traversal failure remains primary if child close fails.
                    _close_preserving(exc, child, "TREE_%s" % rel)
                    raise
                else:
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
    # Preserve ordinary diagnostic text while escaping every line separator.
    escapes = {ord(c): "\\u%04x" % ord(c) for c in "\v\f\x1c\x1d\x1e\x85\u2028\u2029"}
    escapes.update({ord("\r"): "\\r", ord("\n"): "\\n"})
    vals = tuple(str(v).translate(escapes) for v in vals)
    data = "\n".join("%s=%s" % (k, v) for k, v in zip(("status", "mode", "stage", "expected", "observed", "action"), vals)) + "\n"
    _new_file(rootfd, "phase-i-failure.txt", data.encode())


def _cleanup_failure(rootfd, original, errors):
    data, _ = _read_regular(rootfd, "phase-i-failure.txt")
    record = {
        "original_path": "phase-i-failure.txt",
        "original_sha256": hashlib.sha256(data).hexdigest(),
        "original_exception_type": type(getattr(original, "original", original)).__name__,
        "original_stage": getattr(original, "stage", "unknown"),
        "original_message": str(getattr(original, "original", original)),
        "cleanup_errors": list(errors),
    }
    _new_file(rootfd, "phase-i-cleanup-failure.txt", _line(record))


class PhaseIFailure(RuntimeError):
    def __init__(self, stage, original, secondary=()):
        self.stage, self.original, self.secondary = stage, original, list(secondary)
        super().__init__(stage + ": " + str(original) + ("; evidence persistence: " + "; ".join(self.secondary) if self.secondary else ""))

    def add_secondary(self, errors):
        self.secondary.extend(errors)
        self.args = (self.stage + ": " + str(self.original) + "; evidence persistence: " + "; ".join(self.secondary),)


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
    if hashlib.sha256(data).hexdigest() != item["sha256"] or len(data) != item["size"]:
        raise ValueError("reviewed input hash/size mismatch: " + str(path))
    return data, identity


def _review(reviewed, command, candidate, diagnostics, cwd):
    if not isinstance(reviewed, dict) or set(reviewed) != {"manifest"}:
        raise ValueError("authenticated reviewed manifest required")
    raw, manifest_identity = _pinned(reviewed["manifest"])
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate manifest field: " + key)
            result[key] = value
        return result
    contract = json.loads(raw, object_pairs_hook=unique_object)
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
    journals, expected_diagnostics, immutable_diagnostics = [], set(), {}
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

    def verify_diagnostics():
        tree = _diagnostic_files(d, expected_diagnostics)
        for name, expected in immutable_diagnostics.items():
            if tree["files"][name] != expected:
                raise ValueError("diagnostic identity/content changed: " + name)
        for log in journals:
            log.verify()
        return tree

    def publish(name, data):
        immutable_diagnostics[name] = _new_file(d.fd, name, data)
        expected_diagnostics.add(name)

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
        secondary = []
        try:
            log.append(record)
        except Exception as exc:
            # Carry the real result even if its journal cannot be persisted.
            failure = failure or RuntimeError(json.dumps(record))
            secondary.append(repr(exc))
        try:
            verify_roots_inputs()
        except Exception as exc:
            if failure is None:
                failure = exc
            else:
                secondary.append("post-child authentication: " + repr(exc))
        if failure is not None:
            raise PhaseIFailure(label, failure, secondary)
        return cp

    try:
        r.create()
        d.create()
        stage = "authentication"
        immutable_diagnostics["authentication.json"] = _json_at(d.fd, "authentication.json", {"authenticated": authentication, "contract": contract,
                 "candidate_root": _identity(os.fstat(r.fd)), "diagnostics_root": _identity(os.fstat(d.fd))})
        expected_diagnostics.add("authentication.json")
        install = journal("installation.json")
        stage = "installation"
        pre = _tree(r)
        install.append({"event": "pre-install", "candidate": pre})
        cp = child(list(command), install, (0, None, None), "installation-process")
        stage = "installation-streams"
        for name, data in (("mode2-stage.stdout", cp.stdout), ("mode2-stage.stderr", cp.stderr)):
            publish(name, data)
        stage = "membership"
        post = _membership(r, contract)
        install.append({"event": "post-install", "candidate": post, "archive_mapping": contract["archive_mapping"]})
        verify_diagnostics()
        stage = "candidate-validator"
        validation = journal("validation.json")
        python = str(Path(sys.executable).resolve())
        argv = [python, "-B", "-c", VALIDATOR] + [str(r.path / name) for name in contract["validator_members"]]
        child(argv, validation, (0, b"PASS_WHITESPACE\n", b""), stage)
        verify_diagnostics()
        if _membership(r, contract) != post:
            raise ValueError("candidate changed during validator")
        stage = "controls"
        control_log = journal("controls.json")
        for name, payload, prefix in CONTROL_CASES:
            stage = "control-" + name
            publish(name, payload)
            before = verify_diagnostics()["files"][name]
            if before["sha256"] != _digest(payload)["sha256"]:
                raise ValueError("control input mismatch")
            path = str(d.path / name)
            child([python, "-B", "-c", VALIDATOR, path], control_log, (1, b"", (prefix + ":" + path + "\n").encode()), stage)
            if verify_diagnostics()["files"][name] != before:
                raise ValueError("control changed during validator")
            if _membership(r, contract) != post:
                raise ValueError("candidate changed during control")
        stage = "finalization"
        verify_roots_inputs()
        verify_diagnostics()
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
    except BaseException as exc:
        # Preserve termination/cancellation identity and traceback.  The
        # failure record is still durable evidence, but must not turn a
        # KeyboardInterrupt/SystemExit into a cleanup-only PhaseIFailure.
        try:
            if r.fd is not None:
                _failure(r.fd, "global", stage, "reviewed Phase-I contract",
                         type(exc).__name__ + ": " + str(exc))
            elif r.created:
                _secondary_close(exc, "FAILURE_RECORD", RuntimeError("created root could not be opened safely"))
        except BaseException as persist:
            _secondary_close(exc, "FAILURE_RECORD", persist)
        raise
    finally:
        active = sys.exc_info()[1]
        errors = []
        for j in journals:
            try:
                j.close()
            except Exception as exc:
                errors.append("SECONDARY_CLOSE_JOURNAL: " + repr(exc))
        errors.extend(d.close())
        cleanup_failure = None
        def publish_cleanup(cleanup_errors, rootfd=None):
            target = rootfd if rootfd is not None else r.fd
            if target is None or not cleanup_errors:
                return
            try:
                _cleanup_failure(target, active or cleanup_failure, cleanup_errors)
            except BaseException as exc:
                if active is not None:
                    _secondary_close(active, "CLEANUP_RECORD", exc)
                elif cleanup_failure is not None:
                    cleanup_failure.add_secondary(["cleanup-record: " + repr(exc)])
        if errors:
            if isinstance(active, PhaseIFailure):
                active.add_secondary(errors)
            elif active is not None:
                for error in errors:
                    _secondary_close(active, "FINALIZATION", RuntimeError(error))
            else:
                cleanup_failure = PhaseIFailure("finalization", RuntimeError("descriptor close failure"), errors)
                try:
                    if r.fd is not None:
                        _failure(r.fd, "global", "finalization", "all descriptors closed", str(cleanup_failure))
                except Exception as exc:
                    cleanup_failure.add_secondary(["failure-record: " + repr(exc)])
        prior_errors = list(errors)
        root_cleanup_seen = []
        def root_close_report(root_errors, backup):
            root_cleanup_seen.extend(root_errors)
            publish_cleanup(prior_errors + root_errors, backup)
        errors = r.close(on_errors=root_close_report)
        if errors:
            if isinstance(active, PhaseIFailure):
                active.add_secondary(errors)
            elif active is not None:
                for error in errors:
                    _secondary_close(active, "FINALIZATION", RuntimeError(error))
            else:
                cleanup_failure = cleanup_failure or PhaseIFailure("finalization", RuntimeError("candidate descriptor close failure"))
                cleanup_failure.add_secondary(errors + ["failure-record: candidate descriptor already closed"])
        if cleanup_failure is not None:
            raise cleanup_failure


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-root", required=True)
    p.add_argument("--diagnostics-root", required=True)
    p.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    p.parse_args(argv)
    raise SystemExit("reviewed contract API required; no CLI release")


if __name__ == "__main__":
    main()
