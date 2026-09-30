#!/usr/bin/env python3
"""Build one current-source McKernel image without Docker or guest effects.

This is deliberately smaller than the host-module owner.  It consumes a
source checkout, a reviewed source manifest, and a reviewed toolchain manifest;
it only configures and builds the ``mckernel.img`` CMake target in a fresh
output tree.  No package installation, network, module load, root operation,
or guest operation is performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import time
import uuid

import native_rust_exact_build_offline as provenance


INPUT_SCHEMA = "mckernel.native-exact-mckernel-image-inputs.v1"
TOOLCHAIN_SCHEMA = "mckernel.native-exact-mckernel-image-toolchain.v1"
RECEIPT_SCHEMA = "mckernel.native-exact-mckernel-image-receipt.v1"
IHK_HEAD = provenance.EXPECTED_IHK_HEAD
MAX_JSON = 256 * 1024 * 1024
MAX_TIMEOUT = 24 * 60 * 60
REQUIRED_TOOLS = ("cmake", "cc", "rustc", "nm", "readelf", "make", "ld", "objcopy",
                  "ar", "ranlib", "git")
# This diagnostic driver does not establish whole-image Rust ownership.  Its
# receipt states only these symbol-presence and compile-database observations.
PROOF_SCOPE = {
    "linked_rust_ownership": False,
    "complete_migrated_c_exclusion": False,
    "runtime_acceptance": False,
}
EXPECTED_SYMBOLS = (
    "arch_start", "main", "monitor_init", "init_host_ikc2linux",
    "init_host_ikc2mckernel", "prepare_process_ranges_args_envs",
    "mcexec_v10_trace_enter_user",
)
FORBIDDEN_C_SOURCES = (
    "kernel/init.c", "kernel/host.c", "kernel/host_helpers.c",
)
REPRO_ENV = {
    "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
    "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
    "SOURCE_DATE_EPOCH": "1786434034",
    "KBUILD_BUILD_HOST": "rocky-10.2-x86_64", "KBUILD_BUILD_USER": "mckernel",
    "KBUILD_BUILD_VERSION": "1",
    "KBUILD_BUILD_TIMESTAMP": "Tue, 11 Aug 2026 07:40:34 +0000",
    "NATIVE_KERNEL_LOCALVERSION": "-211.44.1.el10_2.mckernel1.x86_64",
    "EXPECTED_KERNEL_RELEASE": "6.12.0-211.44.1.el10_2.mckernel1.x86_64",
}

_ACTIVE_LATCH = None


class ImageBuildError(RuntimeError):
    pass


class SignalLatch:
    """Turn termination signals into bounded child cleanup, not abrupt exit."""

    def __init__(self):
        self.requested = None
        self._previous = {}

    def _handler(self, signum, _frame):
        self.requested = signum

    def __enter__(self):
        global _ACTIVE_LATCH
        _fail(_ACTIVE_LATCH is None, "nested signal latch")
        _ACTIVE_LATCH = self
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            self._previous[signum] = signal.getsignal(signum)
            signal.signal(signum, self._handler)
        return self

    def __exit__(self, _type, _value, _traceback):
        global _ACTIVE_LATCH
        for signum, handler in self._previous.items():
            signal.signal(signum, handler)
        _ACTIVE_LATCH = None
        return False


def _signal_requested(latch=None):
    active = latch if latch is not None else _ACTIVE_LATCH
    return active.requested if active is not None else None


def _check_signal(latch=None):
    requested = _signal_requested(latch)
    _fail(not requested, "interrupt (signal %s)" % requested)


def _fsync_file(path):
    with Path(path).open("rb") as stream:
        os.fsync(stream.fileno())


def _fsync_dir(path):
    fd = os.open(Path(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_fsync(path, text):
    path = Path(path)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_dir(path.parent)


def _group_alive(pgid):
    # killpg(0) also reports unreaped zombies.  They cannot retain files or
    # execute work, so inspect procfs state and only treat live members as a
    # surviving group.  This keeps cleanup bounded even when PID 1 is slow to
    # reap an orphaned grandchild.
    found = False
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            raw = (proc / "stat").read_text(encoding="utf-8")
            fields = raw[raw.rfind(")") + 2:].split()
            if len(fields) >= 3 and int(fields[2]) == pgid:
                found = True
                if fields[0] != "Z":
                    return True
        except (FileNotFoundError, ValueError, UnicodeError):
            continue
    if found:
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _stop_group(pgid):
    if not _group_alive(pgid):
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while _group_alive(pgid) and time.monotonic() < deadline:
        time.sleep(0.05)
    if _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 5
        while _group_alive(pgid) and time.monotonic() < deadline:
            time.sleep(0.05)
    _fail(not _group_alive(pgid), "child process group remains")


def _fail(ok, message):
    if not ok:
        raise ImageBuildError(message)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            _check_signal()
            digest.update(block)
    return digest.hexdigest()


def _canonical(path, label, directory=None):
    path = Path(path)
    _fail(path.is_absolute(), label + " must be absolute")
    _fail(not path.is_symlink(), label + " must not be a symlink")
    _fail(path.exists(), label + " is missing")
    resolved = path.resolve(strict=True)
    _fail(resolved == path, label + " is not canonical")
    if directory is not None:
        try:
            resolved.relative_to(Path(directory).resolve(strict=True))
        except ValueError as exc:
            raise ImageBuildError(label + " escapes bound root") from exc
    return resolved


def _regular(path, label):
    path = _canonical(path, label)
    _fail(stat.S_ISREG(path.lstat().st_mode), label + " must be regular")
    return path


def _json(path, label):
    path = _regular(path, label)
    with path.open("rb") as stream:
        data = stream.read(MAX_JSON + 1)
    _fail(len(data) <= MAX_JSON, label + " is too large")
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ImageBuildError("malformed " + label) from exc


def _atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if value.get("status") == "PASS":
        _check_signal()
    if path.exists() or path.is_symlink():
        os.replace(temporary, path)
    else:
        os.link(temporary, path)
        temporary.unlink()
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _no_symlink_parents(path, label):
    path = Path(path)
    _fail(path.is_absolute(), label + " must be absolute")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current.is_symlink():
            raise ImageBuildError(label + " has symlink parent: " + str(current))


def _disjoint(roots):
    roots = [Path(root).resolve(strict=False) for root in roots]
    for index, left in enumerate(roots):
        for right in roots[index + 1:]:
            _fail(left != right and left not in right.parents and right not in left.parents,
                  "bound roots overlap")


def _tool_descriptor(tool, label):
    _fail(isinstance(tool, dict), label + " descriptor")
    _fail(set(tool) >= {"path", "sha256"}, label + " descriptor fields")
    path = _regular(tool["path"], label + " path")
    digest = tool["sha256"]
    _fail(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest),
          label + " hash")
    _fail(_sha256(path) == digest, label + " hash drift")
    return {"path": str(path), "sha256": digest,
            **({"version": tool["version"]} if "version" in tool else {})}


def _git(source, *args, tool):
    _check_signal()
    _tool_descriptor(tool, "Git")
    command = [tool["path"], "-c", "safe.directory=" + str(source),
               "-c", "core.fsmonitor=", "-c", "core.hooksPath=/dev/null",
               "-C", str(source), *args]
    env = {"PATH": str(Path(tool["path"]).parent), "GIT_OPTIONAL_LOCKS": "0", **REPRO_ENV}
    return _bounded_output(command, "Git identity", env=env, raw_bytes=True, reject_stderr=True)


def _manifest_files(source, manifest):
    rows = manifest.get("repository_files")
    _fail(isinstance(rows, dict) and rows, "source manifest inventory missing")
    observed = {}
    for relative, expected in rows.items():
        _fail(isinstance(relative, str) and relative and not Path(relative).is_absolute() and
              "\\" not in relative and "\0" not in relative and
              all(part not in ("", ".", "..") for part in relative.split("/")),
              "source manifest path escapes checkout")
        _fail(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
              "source manifest hash")
        path = source / relative
        _fail(path.resolve(strict=False) == path, "source path is not canonical: " + relative)
        _fail(path.exists() and not path.is_symlink() and path.is_file(),
              "source path is not an ordinary file: " + relative)
        observed[relative] = _sha256(path)
        _fail(observed[relative] == expected, "source bytes differ: " + relative)
    _fail(observed == rows, "source manifest inventory differs")
    return observed


def _validate_source(source, candidate_sha, ihk_sha, manifest_path, git_tool):
    source = _canonical(source, "source root")
    _fail(source.is_dir(), "source root must be a directory")
    manifest = _json(manifest_path, "source manifest")
    _fail(manifest.get("schema") in (INPUT_SCHEMA, "mckernel.native-exact-build-inputs.v1"),
          "source manifest schema")
    _fail(manifest.get("candidate_sha") == candidate_sha, "candidate manifest identity")
    _fail(manifest.get("ihk_sha") == ihk_sha and re.fullmatch(r"[0-9a-f]{40}", ihk_sha),
          "IHK manifest identity")
    _fail(isinstance(manifest.get("gitlinks"), dict) and
          manifest["gitlinks"].get("ihk") == ihk_sha, "IHK gitlink identity")
    git = lambda root, *args: _git(root, *args, tool=git_tool)
    _fail(git(source, "rev-parse", "HEAD").decode().strip() == candidate_sha,
          "source HEAD differs from candidate")
    ihk = _canonical(source / "ihk", "IHK checkout")
    _fail(ihk.is_dir(), "IHK checkout missing")
    _fail(git(ihk, "rev-parse", "HEAD").decode().strip() == ihk_sha, "IHK HEAD differs")
    overlay = manifest.get("ihk_overlay")
    production_overlay = ihk_sha == provenance.REVIEWED_IHK_HEAD
    if production_overlay:
        expected_overlay = {
            "asset": provenance.IHK_OVERLAY_ASSET,
            "path": provenance.IHK_OVERLAY_PATH,
            "patch_sha256": provenance.IHK_OVERLAY_PATCH_SHA256,
            "base_sha256": provenance.IHK_OVERLAY_BASE_SHA256,
            "result_sha256": provenance.IHK_OVERLAY_RESULT_SHA256,
        }
        _fail(overlay == expected_overlay, "reviewed IHK overlay contract differs")
        try:
            provenance.verify_ihk_overlay(source, git, applied=True)
        except provenance.BuildError as exc:
            raise ImageBuildError(str(exc)) from exc
    else:
        _fail(overlay is None, "unexpected IHK overlay contract")
    try:
        files, gitlinks = provenance.source_inventory(
            source, git, allow_ihk_overlay=production_overlay)
    except provenance.BuildError as exc:
        raise ImageBuildError(str(exc)) from exc
    _fail(manifest.get("gitlinks") == gitlinks, "source gitlink inventory differs")
    _fail(manifest.get("repository_files") == files, "source file inventory differs")
    main_status = git(source, "status", "--porcelain=1", "--untracked-files=all", "-z")
    ihk_status = git(ihk, "status", "--porcelain=1", "--untracked-files=all", "-z")
    if production_overlay:
        # verify_ihk_overlay already established the exact nested working diff;
        # porcelain v1 reports this submodule modification with uppercase M.
        _fail(main_status == b" M ihk\0" and ihk_status ==
              b" M " + provenance.IHK_OVERLAY_PATH.encode() + b"\0",
              "source checkout is dirty")
    else:
        _fail(not main_status and not ihk_status, "source checkout is dirty")
    return {"manifest": manifest, "source": str(source), "ihk": str(ihk),
            "candidate_sha": candidate_sha, "ihk_sha": ihk_sha,
            "repository_files": files, "main_status": main_status.decode(),
            "ihk_status": ihk_status.decode(),
            "manifest_sha256": _sha256(manifest_path)}


def _tree_inventory(root):
    """Exact prepared-tree closure, including directories and symlink contents.

    Symlinks may only resolve inside this same closure.  Separate system library
    trees must be prepared as another complete root rather than silently adding
    ambient files.  Special files are never admitted as build inputs.
    """
    root = _canonical(root, "closure root")
    _fail(root.is_dir(), "closure root is not a directory")
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            _check_signal()
            path = Path(base) / name
            st = path.lstat()
            row = {"mode": stat.S_IMODE(st.st_mode)}
            if stat.S_ISLNK(st.st_mode):
                _fail(root in path.resolve(strict=True).parents,
                      "closure symlink escapes root: " + str(path))
                row.update(type="symlink", target=os.readlink(path))
            elif stat.S_ISDIR(st.st_mode):
                row.update(type="directory")
            else:
                _fail(stat.S_ISREG(st.st_mode), "special closure file: " + str(path))
                artifact = _artifact(path, "closure file")
                row.update(type="file", size=artifact["size"], sha256=artifact["sha256"])
            result[str(path.relative_to(root))] = row
    return result


def _validate_toolchain(path):
    data = _json(path, "toolchain manifest")
    _fail(data.get("schema") == TOOLCHAIN_SCHEMA, "toolchain manifest schema")
    tools = data.get("tools")
    _fail(isinstance(tools, dict) and all(name in tools for name in REQUIRED_TOOLS),
          "toolchain tools incomplete")
    _fail(all(isinstance(tools[name].get("version"), str) and tools[name]["version"]
              for name in REQUIRED_TOOLS), "toolchain tool versions incomplete")
    bound = {name: _tool_descriptor(tools[name], "tool " + name)
             for name in REQUIRED_TOOLS}
    _fail(isinstance(data.get("kernel_dir"), str), "kernel directory path")
    kernel_dir = _canonical(data["kernel_dir"], "kernel directory")
    _fail(kernel_dir.is_dir(), "kernel directory must be a directory")
    probe = data.get("linux_probe")
    _fail(isinstance(probe, dict) and
          set(probe) >= {"arch", "release", "kernel_dir"},
          "Linux probe prerequisites missing")
    _fail(probe["arch"] == "x86_64" and probe["kernel_dir"] == str(kernel_dir),
          "Linux probe identity differs")
    _fail(isinstance(probe["release"], str) and probe["release"],
          "Linux probe release missing")
    for relative in ("Makefile", ".config", "include/config/kernel.release",
                     "include/generated/autoconf.h", "include/generated/utsrelease.h"):
        item = kernel_dir / relative
        _fail(item.is_file() and not item.is_symlink(),
              "Linux probe prerequisite missing: " + relative)
    _fail(_tree_inventory(kernel_dir) == data.get("kernel_inventory"),
          "complete kernel inventory differs")
    release = REPRO_ENV["EXPECTED_KERNEL_RELEASE"]
    _fail(probe["release"] == release and
          (kernel_dir / "include/config/kernel.release").read_text().strip() == release and
          ('#define UTS_RELEASE "' + release + '"') in
          (kernel_dir / "include/generated/utsrelease.h").read_text().splitlines(),
          "target Linux probe release differs")
    config = (kernel_dir / ".config").read_text().splitlines()
    auto = (kernel_dir / "include/generated/autoconf.h").read_text().splitlines()
    _fail("CONFIG_X86_64=y" in config and "CONFIG_64BIT=y" in config and
          "#define CONFIG_X86_64 1" in auto and "#define CONFIG_64BIT 1" in auto,
          "target Linux probe config differs")
    closures = data.get("toolchain_roots")
    _fail(isinstance(closures, list) and closures, "complete toolchain closure missing")
    roots = []
    for closure in closures:
        _fail(isinstance(closure, dict) and set(closure) == {"path", "inventory"},
              "toolchain closure fields")
        root = _canonical(closure["path"], "toolchain closure")
        _fail(_tree_inventory(root) == closure["inventory"], "complete toolchain inventory differs")
        roots.append(root)
    _disjoint(roots + [kernel_dir])
    _fail(all(any(root in Path(ref["path"]).parents for root in roots)
              for ref in bound.values()), "tool outside complete toolchain closure")
    path_dirs = data.get("path_dirs")
    _fail(isinstance(path_dirs, list) and path_dirs, "bound PATH missing")
    for directory in path_dirs:
        directory = _canonical(directory, "PATH directory")
        _fail(directory.is_dir() and any(root == directory or root in directory.parents
                                        for root in roots), "PATH outside toolchain closure")
    for name, descriptor in bound.items():
        selected = next((Path(directory) / name for directory in path_dirs
                         if os.access(str(Path(directory) / name), os.X_OK)), None)
        _fail(selected is not None and selected.resolve(strict=True) == Path(descriptor["path"]),
              "PATH tool differs from bound tool: " + name)
    environment = data.get("environment", {})
    _fail(isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str)
                                                  for k, v in environment.items()),
          "toolchain environment")
    # Arbitrary environment can inject compiler plugins, Git executables,
    # library search paths and preloads outside the declared closure.
    _fail(not environment, "unreviewed toolchain environment")
    return {"manifest": data, "manifest_sha256": _sha256(path), "tools": bound,
            "kernel_dir": str(kernel_dir), "environment": dict(environment),
            "path": os.pathsep.join(path_dirs)}


def _tool_versions(toolchain, evidence):
    versions = {}
    for name, ref in toolchain["tools"].items():
        versions[name] = _bounded_output([ref["path"], "--version"], name + " --version")
        expected = ref.get("version")
        if expected is not None:
            _fail(versions[name].strip() == expected, name + " version differs")
    rust_version = toolchain["tools"]["rustc"].get("version", versions["rustc"].strip())
    _fail("nightly" in rust_version.lower(), "Rust toolchain is not nightly")
    _write_fsync(evidence / "tool-versions.txt",
                 "".join("[%s]\n%s" % (name, versions[name])
                         for name in sorted(versions)))
    return versions


def _bounded_output(argv, label, timeout=30, latch=None, env=None, raw_bytes=False,
                    reject_stderr=False):
    _check_signal(latch)
    process = subprocess.Popen(argv, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE if reject_stderr else subprocess.STDOUT,
                               env=env or {"PATH": "", **REPRO_ENV},
                               start_new_session=True)
    raw = b""
    try:
        deadline = time.monotonic() + timeout
        while True:
            requested = _signal_requested(latch)
            if requested:
                _stop_group(process.pid)
                process.wait(timeout=5)
                raise ImageBuildError(label + " interrupted by signal " + str(requested))
            try:
                raw, error = process.communicate(timeout=min(0.2, max(0.01, deadline - time.monotonic())))
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    _stop_group(process.pid)
                    process.wait(timeout=5)
                    raise ImageBuildError(label + " timed out")
    except BaseException:
        if process.poll() is None or _group_alive(process.pid):
            _stop_group(process.pid)
        if process.poll() is None:
            process.wait(timeout=5)
        raise
    if _group_alive(process.pid):
        _stop_group(process.pid)
        raise ImageBuildError(label + " child process group remains")
    _fail(process.returncode == 0, label + " failed")
    _fail(not reject_stderr or not error,
          label + " unexpected stderr: " + (error or b"").decode("utf-8", "replace"))
    _check_signal(latch)
    return raw if raw_bytes else raw.decode("utf-8", "replace")


def _artifact(path, label):
    path = _regular(path, label)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        _fail(stat.S_ISREG(st.st_mode), "artifact is not regular")
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                _check_signal()
                digest.update(block)
        signature = lambda item: (item.st_dev, item.st_ino, item.st_mode, item.st_size,
                                  item.st_mtime_ns, item.st_ctime_ns)
        _fail(signature(st) == signature(os.fstat(fd)) == signature(path.lstat()),
              "artifact changed during hash")
    finally:
        os.close(fd)
    return {"path": str(path), "size": st.st_size, "mode": stat.S_IMODE(st.st_mode),
            "device": st.st_dev, "inode": st.st_ino,
            "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns, "sha256": digest.hexdigest()}


def _run_process(argv, cwd, env, stdout, stderr, timeout, label, latch=None):
    _check_signal(latch)
    _fail(timeout > 0 and timeout <= MAX_TIMEOUT, "invalid timeout")
    stdout = Path(stdout); stderr = Path(stderr)
    exit_code = None
    with stdout.open("ab", buffering=0) as out, stderr.open("ab", buffering=0) as err:
        process = None
        try:
            process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdout=out, stderr=err,
                                       start_new_session=True)
            deadline = time.monotonic() + timeout
            interrupted = None
            while process.poll() is None:
                requested = _signal_requested(latch)
                if requested:
                    interrupted = "interrupt (signal %d)" % requested
                    break
                try:
                    remaining = max(0.05, min(1.0, deadline - time.monotonic()))
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    if time.monotonic() >= deadline:
                        interrupted = "timeout"
                        break
                except KeyboardInterrupt:
                    interrupted = "interrupt"
                    break
            if interrupted:
                _stop_group(process.pid)
                process.wait(timeout=5)
                raise ImageBuildError(label + " " + interrupted)
            # A successful leader is not sufficient: a detached child in the
            # process group would otherwise survive the receipt and retain files.
            if _group_alive(process.pid):
                _stop_group(process.pid)
                raise ImageBuildError(label + " child process group remains")
            exit_code = process.returncode
            _check_signal(latch)
        finally:
            if process is not None:
                if process.poll() is None or _group_alive(process.pid):
                    _stop_group(process.pid)
                process.wait(timeout=5)
            _fsync_file(stdout)
            _fsync_file(stderr)
    return exit_code


def _copy_evidence(source, destination, expected):
    _check_signal()
    _fail(_artifact(source, "copy source") == expected, "artifact changed before copy")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _fail(not destination.exists() and not destination.is_symlink(),
          "evidence destination already exists")
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        _fail((st.st_dev, st.st_ino) == (expected["device"], expected["inode"]),
              "artifact identity changed before copy")
        with os.fdopen(fd, "rb", closefd=False) as stream, destination.open("xb") as out:
            shutil.copyfileobj(stream, out)
            out.flush()
            os.fsync(out.fileno())
    finally:
        os.close(fd)
    os.chmod(destination, expected["mode"])
    with destination.open("rb") as stream:
        os.fsync(stream.fileno())
    _fsync_dir(destination.parent)
    copied = _artifact(destination, "evidence artifact")
    _fail(all(copied[key] == expected[key] for key in ("size", "mode", "sha256")),
          "artifact evidence copy differs")
    _fail(_artifact(source, "copy source") == expected, "artifact changed during copy")
    _check_signal()
    return copied


def _validate_image(build, toolchain, evidence):
    required = {
        "mckernel.img": build / "kernel/mckernel.img",
        "mckernel.img.map": build / "kernel/mckernel.img.map",
        "CMakeCache.txt": build / "CMakeCache.txt",
        "compile_commands.json": build / "compile_commands.json",
        "mckernel_rust.o": build / "kernel/rust/mckernel_rust.o",
        "build.make": build / "kernel/CMakeFiles/mckernel_rust_obj.dir/build.make",
    }
    for path in required.values():
        _fsync_file(path)
        _fsync_dir(path.parent)
    artifacts = {name: _artifact(path, "image artifact " + name)
                 for name, path in required.items()}
    cache = required["CMakeCache.txt"].read_text(encoding="utf-8", errors="strict")
    makefile = required["build.make"].read_text(encoding="utf-8", errors="strict")
    _fail("ENABLE_RUST_KERNEL:BOOL=ON" in cache, "Rust kernel is not enabled")
    _fail("MCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12" in cache,
          "Linux 6.12 host ABI is not selected")
    _fail("native_linux_irq_work_v6_12" in makefile,
          "native Linux 6.12 Rust work path is not selected")
    compile = _json(required["compile_commands.json"], "compile_commands")
    _fail(isinstance(compile, list), "compile_commands must be an array")
    for row in compile:
        _fail(isinstance(row, dict), "malformed compile command")
        source = row.get("file", "")
        _fail(not any(str(source).replace("\\", "/").endswith(item)
                      for item in FORBIDDEN_C_SOURCES),
              "C fallback source compiled: " + str(source))
    readelf = toolchain["tools"]["readelf"]["path"]
    header = _bounded_output([readelf, "-h", str(required["mckernel.img"])], "readelf")
    _fail("ELF64" in header and "Advanced Micro Devices X86-64" in header and
          re.search(r"Type:\s+EXEC(?:\s|$)", header) is not None,
          "image is not an ELF64 x86-64 EXEC")
    nm = toolchain["tools"]["nm"]["path"]
    symbols = _bounded_output([nm, "-n", str(required["mckernel.img"])], "nm")
    for symbol in EXPECTED_SYMBOLS:
        _fail(re.search(r"\bT\s+" + re.escape(symbol) + r"\s*$", symbols, re.M) is not None,
              "missing image symbol: " + symbol)
    object_symbols = _bounded_output([nm, "-n", str(required["mckernel_rust.o"])],
                                     "Rust object nm")
    for symbol in EXPECTED_SYMBOLS[:5]:
        _fail(re.search(r"\bT\s+" + re.escape(symbol) + r"\s*$", object_symbols, re.M)
              is not None, "Rust object does not own native symbol: " + symbol)
    _write_fsync(evidence / "elf-header.txt", header)
    _write_fsync(evidence / "symbols.txt", symbols)
    _write_fsync(evidence / "rust-object-symbols.txt", object_symbols)
    for name, path in required.items():
        _fail(_artifact(path, "validated artifact") == artifacts[name],
              "artifact changed during validation")
    _check_signal()
    return artifacts


def run(*args, **kwargs):
    with SignalLatch():
        return _run(*args, **kwargs)


def _run(source_root, candidate_sha, ihk_sha, manifest, toolchain, output, evidence,
        *, jobs=4, timeout=19800):
    _fail(isinstance(jobs, int) and not isinstance(jobs, bool) and 1 <= jobs <= 4,
          "jobs must be between 1 and 4")
    _fail(isinstance(timeout, int) and not isinstance(timeout, bool) and 1 <= timeout <= MAX_TIMEOUT,
          "timeout is outside bound")
    source_root = _canonical(source_root, "source root")
    manifest = _canonical(manifest, "source manifest")
    toolchain = _canonical(toolchain, "toolchain manifest")
    output = Path(output); evidence = Path(evidence)
    _no_symlink_parents(output, "output")
    _no_symlink_parents(evidence, "evidence")
    _fail(not output.exists() and not output.is_symlink(), "output must be fresh")
    _fail(not evidence.exists() and not evidence.is_symlink(), "evidence must be fresh")
    _disjoint((source_root, output, evidence, manifest, toolchain))
    tools = _validate_toolchain(toolchain)
    source = _validate_source(source_root, candidate_sha, ihk_sha, manifest, tools["tools"]["git"])
    _check_signal()
    output.mkdir(mode=0o700, parents=False)
    evidence.mkdir(mode=0o700, parents=False)
    build = output / "build"
    build.mkdir(mode=0o700)
    stdout = evidence / "build.stdout.log"
    stderr = evidence / "build.stderr.log"
    stdout.touch(); stderr.touch()
    env = dict(REPRO_ENV, PATH=tools["path"], CC=tools["tools"]["cc"]["path"],
               RUSTC=tools["tools"]["rustc"]["path"],
               KERNEL_DIR=tools["kernel_dir"],
               **tools["environment"])
    command_rows = []
    progress = {"schema": RECEIPT_SCHEMA, "status": "RUNNING", "phase": "identity",
                "candidate_sha": candidate_sha, "ihk_sha": ihk_sha,
                "commands": command_rows, "started_at": time.time()}
    result = {"status": "FAIL", "phase": "identity", "candidate_sha": candidate_sha,
              "ihk_sha": ihk_sha, "commands": command_rows,
              "output_root": str(output), "evidence_root": str(evidence)}
    _atomic_json(evidence / "progress.json", progress)
    try:
        _check_signal()
        versions = _tool_versions(tools, evidence)
        provenance = {
            "schema": RECEIPT_SCHEMA, "candidate_sha": candidate_sha, "ihk_sha": ihk_sha,
            "source": source, "manifest": {"path": str(manifest), "sha256": _sha256(manifest)},
            "toolchain": {"path": str(toolchain), "sha256": _sha256(toolchain),
                          "kernel_dir": tools["kernel_dir"], "tools": tools["tools"],
                          "versions": versions},
            "environment": {key: env[key] for key in sorted(env)
                            if key not in ("PATH",)},
            "jobs": jobs, "timeout_seconds": timeout,
        }
        _atomic_json(evidence / "provenance.json", provenance)
        configure = [tools["tools"]["cmake"]["path"], "-S", str(source_root), "-B", str(build),
                     "-G", "Unix Makefiles",
                     "-DCMAKE_BUILD_TYPE=Debug", "-DBUILD_TARGET=smp-x86",
                     "-DKERNEL_DIR=" + tools["kernel_dir"], "-DENABLE_PERF=ON",
                     "-DENABLE_RUSAGE=ON", "-DENABLE_LINUX_WORK_IRQ_FOR_IKC=ON",
                     "-DRUSTC=" + tools["tools"]["rustc"]["path"],
                     "-DCMAKE_C_COMPILER=" + tools["tools"]["cc"]["path"],
                     "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DENABLE_RUST_KERNEL=ON",
                     "-DENABLE_RUST_IHK_MODULE_HELPERS=ON", "-DENABLE_RUST_USER_TOOLS=ON",
                     "-DMCKERNEL_HOST_IRQ_ABI=linux-6.12"]
        for key, name in (("MAKE_PROGRAM", "make"), ("LINKER", "ld"),
                          ("AR", "ar"), ("RANLIB", "ranlib"), ("NM", "nm"),
                          ("OBJCOPY", "objcopy"), ("READELF", "readelf")):
            configure.append("-DCMAKE_" + key + "=" + tools["tools"][name]["path"])
        configure.append("-DGIT_EXECUTABLE=" + tools["tools"]["git"]["path"])
        build_command = [tools["tools"]["cmake"]["path"], "--build", str(build),
                         "--target", "mckernel.img", "-j" + str(jobs)]
        for phase, command in (("configure", configure), ("build", build_command)):
            _check_signal()
            progress["phase"] = phase
            row = {"phase": phase, "argv": command, "cwd": str(source_root),
                   "env_sha256": hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest(),
                   "exit_code": None}
            command_rows.append(row)
            _atomic_json(evidence / "progress.json", progress)
            row["exit_code"] = _run_process(command, source_root, env, stdout, stderr, timeout, phase)
            _atomic_json(evidence / "progress.json", progress)
            _fail(row["exit_code"] == 0, phase + " failed")
        progress["phase"] = "artifact-validation"
        _check_signal()
        _atomic_json(evidence / "progress.json", progress)
        artifacts = _validate_image(build, tools, evidence)
        source_after = _validate_source(source_root, candidate_sha, ihk_sha, manifest,
                                        tools["tools"]["git"])
        _fail(source_after["repository_files"] == source["repository_files"],
              "source changed during build")
        _fail(source_after["manifest_sha256"] == source["manifest_sha256"],
              "source manifest changed during build")
        tools_after = _validate_toolchain(toolchain)
        _fail(tools_after["manifest_sha256"] == tools["manifest_sha256"],
              "toolchain manifest changed during build")
        copied = {}
        for name, item in artifacts.items():
            relative = {"mckernel.img": "mckernel.img", "mckernel.img.map": "mckernel.img.map",
                        "CMakeCache.txt": "CMakeCache.txt", "compile_commands.json": "compile_commands.json",
                        "mckernel_rust.o": "mckernel_rust.o", "build.make": "build.make"}[name]
            copied[name] = _copy_evidence(Path(item["path"]), evidence / "artifacts" / relative, item)
        _check_signal()
        progress["phase"] = "complete"
        progress["status"] = "PASS"
        _atomic_json(evidence / "progress.json", progress)
        result = {"status": "PASS", "phase": "complete", "candidate_sha": candidate_sha,
                  "ihk_sha": ihk_sha, "source_manifest_sha256": source["manifest_sha256"],
                  "toolchain_manifest_sha256": tools["manifest_sha256"],
                  "commands": command_rows, "artifacts": artifacts,
                  "proof_scope": {**PROOF_SCOPE, "image_text_symbols": list(EXPECTED_SYMBOLS),
                                  "object_text_symbols": list(EXPECTED_SYMBOLS[:5]),
                                  "compile_database_exclusions": list(FORBIDDEN_C_SOURCES)},
                  "evidence_artifacts": copied, "output_root": str(output),
                  "evidence_root": str(evidence)}
    except BaseException as exc:
        progress["status"] = "FAIL"
        progress["error"] = str(exc)
        _atomic_json(evidence / "progress.json", progress)
        result = {"status": "FAIL", "phase": progress.get("phase"),
                  "candidate_sha": candidate_sha, "ihk_sha": ihk_sha,
                  "commands": command_rows, "error": str(exc),
                  "output_root": str(output), "evidence_root": str(evidence)}
    # Hashing evidence itself is interruptible.  Preserve a FAIL receipt even
    # when cancellation arrives here or while the initial receipt is written.
    try:
        _check_signal()
        result["inventory"] = {
            str(item.relative_to(evidence)): {"size": item.stat().st_size, "sha256": _sha256(item)}
            for item in sorted(evidence.rglob("*"))
            if item.is_file() and not item.is_symlink() and item.name != "receipt.json"
        }
        if result["status"] == "PASS":
            for item in artifacts.values():
                _fail(_artifact(item["path"], "final artifact") == item,
                      "artifact changed before receipt")
            for item in copied.values():
                _fail(_artifact(item["path"], "final evidence") == item,
                      "evidence artifact changed before receipt")
        _check_signal()
    except BaseException as exc:
        result.update(status="FAIL", error=str(exc))
    result["finished_at"] = time.time()
    if _signal_requested():
        result.update(status="FAIL", error="interrupt (signal %s)" % _signal_requested())
    if result["status"] == "FAIL":
        progress.update(status="FAIL", error=result.get("error"))
        _atomic_json(evidence / "progress.json", progress)
    try:
        _atomic_json(evidence / "receipt.json", result)
    except ImageBuildError as exc:
        result.update(status="FAIL", error=str(exc))
        progress.update(status="FAIL", error=str(exc))
        _atomic_json(evidence / "progress.json", progress)
        _atomic_json(evidence / "receipt.json", result)
    if _signal_requested():
        result.update(status="FAIL", error="interrupt (signal %s)" % _signal_requested())
        progress.update(status="FAIL", error=result["error"])
        _atomic_json(evidence / "progress.json", progress)
        _atomic_json(evidence / "receipt.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--ihk-sha", default=IHK_HEAD)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--toolchain", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--jobs", required=True, type=int)
    parser.add_argument("--timeout", required=True, type=int)
    args = parser.parse_args(argv)
    result = run(**vars(args))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
