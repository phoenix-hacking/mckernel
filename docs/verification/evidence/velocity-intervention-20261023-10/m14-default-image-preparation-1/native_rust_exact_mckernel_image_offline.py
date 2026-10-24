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
import resource
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import time
import uuid

import native_rust_exact_build_offline as provenance

# Authenticate the neighboring provenance selected by this exact driver capsule.
EXPECTED_PROVENANCE_SHA256 = 'c5868d8a336795b5c3d76215bba8bcb3e56a804e00f1014d8b4eeaf6ddb76a69'
_EXPECTED_PROVENANCE_PATH = Path(__file__).with_name("native_rust_exact_build_offline.py").resolve()
if (Path(provenance.__file__).resolve() != _EXPECTED_PROVENANCE_PATH or
        hashlib.sha256(_EXPECTED_PROVENANCE_PATH.read_bytes()).hexdigest() != EXPECTED_PROVENANCE_SHA256):
    raise RuntimeError("production provenance path/hash differs from matched guest capsule")


INPUT_SCHEMA = "mckernel.native-exact-mckernel-image-inputs.v1"
TOOLCHAIN_SCHEMA = "mckernel.native-exact-mckernel-image-toolchain.v1"
TOOLCHAIN_SCHEMA_V2 = "mckernel.native-exact-mckernel-image-toolchain.v2"
KERNEL_BINDING_V2_KEYS = frozenset(("container_root", "container_kernel_dir",
                                    "closure_inventory"))
RECEIPT_SCHEMA = "mckernel.native-exact-mckernel-image-receipt.v1"
IHK_HEAD = provenance.EXPECTED_IHK_HEAD
MAX_JSON = 256 * 1024 * 1024
MAX_TIMEOUT = 24 * 60 * 60
REQUIRED_TOOLS = ("cmake", "cc", "clang", "ld.lld", "rustc", "nm", "readelf", "make", "ld", "objcopy",
                  "ar", "ranlib", "git", "dd")
REQUIRED_LIBRARIES = ("libnuma", "libbfd", "libiberty", "libudev")
LIBRARY_SPECS = {
    "libnuma": {"development_package": "numactl-devel", "linker": {"path": "/usr/lib64/libnuma.so", "owner": "numactl-libs"}, "headers": {"/usr/include/numa.h": "numactl-devel"}},
    "libbfd": {"development_package": "binutils-devel", "linker": {"path": "/usr/lib64/libbfd.so", "owner": "binutils-devel"}, "headers": {"/usr/include/bfd.h": "binutils-devel"}},
    "libiberty": {"development_package": "binutils-devel", "linker": {"path": "/usr/lib64/libiberty.a", "owner": "binutils-devel"}, "headers": {"/usr/include/libiberty.h": "binutils-devel"}},
    "libudev": {"development_package": "systemd-devel", "linker": {"path": "/usr/lib64/libudev.so", "owner": "systemd-libs"}, "headers": {"/usr/include/libudev.h": "systemd-devel"}},
}
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


def _no_symlink_parents(path, label, allow_leaf_symlink=False):
    path = Path(path)
    _fail(path.is_absolute(), label + " must be absolute")
    current = Path(path.anchor)
    for index, component in enumerate(path.parts[1:], start=1):
        current /= component
        if current.is_symlink() and not (allow_leaf_symlink and index == len(path.parts) - 1):
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
    _fail(manifest.get("schema") in (INPUT_SCHEMA, "mckernel.native-exact-build-inputs.v1", provenance.THIN_SCHEMA),
          "source manifest schema")
    _fail(manifest.get("candidate_sha") == candidate_sha, "candidate manifest identity")
    _fail(manifest.get("ihk_sha") == ihk_sha and re.fullmatch(r"[0-9a-f]{40}", ihk_sha),
          "IHK manifest identity")
    _fail(isinstance(manifest.get("gitlinks"), dict) and
          manifest["gitlinks"].get("ihk") == ihk_sha, "IHK gitlink identity")
    if manifest.get('schema') == provenance.THIN_SCHEMA:
        observed = provenance.validate_thin_source(source, manifest, candidate_sha, ihk_sha)
        observed['manifest_sha256'] = _sha256(manifest_path)
        return observed
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


def _tree_inventory(root, symlink_binding=None, visible_roots=None, allow_visible_root=False):
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
                try:
                    target = Path(os.readlink(path))
                    if visible_roots is not None and target.is_absolute():
                        target = _container_path(str(target), visible_roots, "closure symlink")
                    elif symlink_binding is not None and target.is_absolute():
                        container_root, mapped_root = symlink_binding
                        target = mapped_root / target.relative_to(container_root)
                    resolved = target if target.is_absolute() else path.parent / target
                    resolved = resolved.resolve(strict=True)
                except (OSError, RuntimeError) as exc:
                    raise ImageBuildError("closure symlink is dangling or cyclic: " + str(path)) from exc
                containment = (next((Path(host) for host in visible_roots.values()
                                    if root == Path(host) or Path(host) in root.parents), root)
                               if visible_roots is not None and allow_visible_root else root if visible_roots is not None else
                               symlink_binding[1] if symlink_binding is not None else root)
                _fail(resolved == containment or containment in resolved.parents,
                      "closure symlink escapes root: " + str(path))
                row.update(type="symlink", target=os.readlink(path))
                if visible_roots is not None:
                    owning = [(Path(name), Path(host)) for name, host in visible_roots.items()
                              if resolved == Path(host) or Path(host) in resolved.parents]
                    _fail(len(owning) == 1, "closure symlink crosses visible roots: " + str(path))
                    container_root, host_root = owning[0]
                    row.update(resolved=str(resolved.relative_to(host_root)),
                               container_target=str(container_root / resolved.relative_to(host_root)))
                elif symlink_binding is not None:
                    container_root, host_root = symlink_binding
                    row.update(resolved=str(resolved.relative_to(host_root)),
                               container_target=str(container_root / resolved.relative_to(host_root)))
            elif stat.S_ISDIR(st.st_mode):
                row.update(type="directory")
            else:
                _fail(stat.S_ISREG(st.st_mode), "special closure file: " + str(path))
                artifact = _artifact(path, "closure file")
                row.update(type="file", size=artifact["size"], sha256=artifact["sha256"])
            result[str(path.relative_to(root))] = row
    return result


def _container_path(raw, roots, label, allow_leaf_symlink=False):
    """Resolve a v2 container path through an explicit visible-root map.

    Production calls use ``None`` and therefore validate paths exactly as the
    container sees them.  The optional map exists only for the unprivileged
    temporary fixture: it models bind mounts without placing host paths in the
    manifest or requiring privileged mounts in the test process.
    """
    _fail(isinstance(raw, str) and raw.startswith("/"), label + " must be absolute")
    candidate = Path(raw)
    if roots is None:
        translated = candidate
    else:
        matched = [(Path(name), Path(root)) for name, root in roots.items()
                   if candidate == Path(name) or Path(name) in candidate.parents]
        _fail(len(matched) == 1, label + " is outside container root")
        container_root, host_root = matched[0]
        translated = host_root / candidate.relative_to(container_root)
    _no_symlink_parents(translated, label, allow_leaf_symlink=allow_leaf_symlink)
    return translated


def _v2_tool_path(raw, visible_roots, label, allow_leaf_symlink=False):
    """Translate prepared fixture mounts, while retaining literal image paths."""
    _fail(isinstance(raw, str) and raw.startswith("/"), label + " must be absolute")
    if visible_roots is not None and (raw.startswith("/out/") or
                                      raw.startswith("/nightly/")):
        path = _container_path(raw, visible_roots, label,
                               allow_leaf_symlink=allow_leaf_symlink)
    else:
        path = Path(raw)
    _no_symlink_parents(path, label, allow_leaf_symlink=allow_leaf_symlink)
    return path


def _validate_toolchain(path, container_roots=None):
    data = _json(path, "toolchain manifest")
    schema = data.get("schema")
    _fail(schema in (TOOLCHAIN_SCHEMA, TOOLCHAIN_SCHEMA_V2), "toolchain manifest schema")
    v2 = schema == TOOLCHAIN_SCHEMA_V2
    binding = None
    visible_roots = None
    if v2:
        binding = data.get("kernel_binding")
        _fail(isinstance(binding, dict) and set(binding) == KERNEL_BINDING_V2_KEYS,
              "kernel binding schema differs")
        _fail(binding["container_root"] == "/out" and binding["container_kernel_dir"] == "/out/build",
              "kernel binding container mapping differs")
        _fail(isinstance(binding["closure_inventory"], dict) and binding["closure_inventory"],
              "kernel binding closure inventory missing")
        # In production these are the actual isolated container paths.  The
        # optional mapping substitutes private fixture roots without putting
        # host paths in the v2 manifest.
        visible_roots = {"/out": Path("/out"), "/nightly": Path("/nightly")}
        if container_roots is not None:
            _fail(isinstance(container_roots, dict) and set(container_roots) >= {"/out", "/nightly"},
                  "fixture container roots incomplete")
            visible_roots = {name: _canonical(root, "fixture visible root")
                             for name, root in container_roots.items()}
            _fail(all(root.is_dir() for root in visible_roots.values()),
                  "fixture visible root is not a directory")
    if v2 and ("image_tools" in data or "mounted_tools" in data):
        image_tools = data.get("image_tools")
        mounted_tools = data.get("mounted_tools")
        _fail(isinstance(image_tools, dict) and isinstance(mounted_tools, dict),
              "toolchain tool classes incomplete")
        _fail(not (set(image_tools) & set(mounted_tools)),
              "toolchain tool is ambiguously bound")
        tools = {**image_tools, **mounted_tools}
        _fail(set(tools) == set(REQUIRED_TOOLS), "toolchain tools incomplete")
    else:
        tools = data.get("tools")
        _fail(isinstance(tools, dict) and all(name in tools for name in REQUIRED_TOOLS),
              "toolchain tools incomplete")
    _fail(all(isinstance(tools[name].get("version"), str) and tools[name]["version"]
              for name in REQUIRED_TOOLS), "toolchain tool versions incomplete")
    libraries = data.get("libraries", {})
    if v2:
        _fail(isinstance(libraries, dict) and set(libraries) == set(REQUIRED_LIBRARIES),
              "toolchain libraries incomplete")
        for name in REQUIRED_LIBRARIES:
            row = libraries[name]
            spec = LIBRARY_SPECS[name]
            _fail(isinstance(row, dict) and row.get("development_package") == spec["development_package"] and
                  isinstance(row.get("linker"), dict) and isinstance(row.get("headers"), dict) and
                  row["headers"], "toolchain library descriptor incomplete: " + name)
            _fail(set(row["headers"]) == set(spec["headers"]), "toolchain library headers differ: " + name)
            expected = [(row["linker"], spec["linker"]["path"], spec["linker"]["owner"])]
            expected += [(row["headers"][path], path, expected_owner)
                         for path, expected_owner in spec["headers"].items()]
            for artifact, expected_path, expected_owner in expected:
                _fail(isinstance(artifact, dict) and isinstance(artifact.get("path"), str) and
                      artifact["path"].startswith("/usr/") and
                      isinstance(artifact.get("target"), str) and artifact["target"].startswith("/usr/") and
                      isinstance(artifact.get("rpm_nevra"), str) and
                      re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))),
                      "toolchain library artifact differs: " + name)
                _fail(artifact["path"] == expected_path and artifact.get("owner") == expected_owner,
                      "toolchain library role differs: " + name)
    if v2:
        bound = {}
        for name in REQUIRED_TOOLS:
            descriptor = tools[name]
            _fail(isinstance(descriptor, dict) and
                  set(descriptor) >= {"path", "sha256", "version"},
                  "tool " + name + " descriptor")
            if name in (data.get("image_tools") or {}):
                _fail(isinstance(descriptor.get("target"), str),
                      "image tool " + name + " canonical target")
            _fail(isinstance(descriptor["sha256"], str) and
                  re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]),
                  "tool " + name + " hash")
            bound[name] = {"path": descriptor["path"], "sha256": descriptor["sha256"],
                           "version": descriptor["version"]}
    else:
        bound = {name: _tool_descriptor(tools[name], "tool " + name)
                 for name in REQUIRED_TOOLS}
    if v2:
        # v2 descriptors retain the lookup spelling and canonical executable
        # target independently.  The prepared image may use a leaf symlink
        # such as /usr/bin/ld; only the resolved target is hash-bound.
        for name in REQUIRED_TOOLS:
            mounted = ("mounted_tools" not in data or
                       name in (data.get("mounted_tools") or {}))
            if mounted:
                raw = tools[name]["path"]
                translated = _v2_tool_path(raw, visible_roots, "tool " + name + " path")
                translated = _canonical(translated, "tool " + name + " path")
                _fail(translated.is_file() and not translated.is_symlink(),
                      "tool " + name + " path is missing")
                _fail(_sha256(translated) == tools[name]["sha256"], "tool " + name + " hash drift")
            else:
                lookup = _v2_tool_path(tools[name]["path"], visible_roots,
                                       "image tool " + name + " lookup",
                                       allow_leaf_symlink=True)
                target = _v2_tool_path(tools[name]["target"], visible_roots,
                                       "image tool " + name + " target")
                _no_symlink_parents(lookup, "image tool " + name + " lookup",
                                    allow_leaf_symlink=True)
                _no_symlink_parents(target, "image tool " + name + " target")
                target = _canonical(target, "image tool " + name + " target")
                _fail(lookup.is_file() and target.is_file() and not target.is_symlink(),
                      "image tool " + name + " path is missing")
                _fail(lookup.resolve(strict=True) == target,
                      "image tool " + name + " lookup target differs")
                _fail(_sha256(target) == tools[name]["sha256"], "tool " + name + " hash drift")
                # Keep the reviewed lookup spelling for argv[0]-sensitive
                # tools; the canonical target remains the authenticated path.
                bound[name]["path"] = str(lookup)
                bound[name]["target"] = str(target)
                continue
            bound[name]["path"] = str(translated)
    _fail(isinstance(data.get("kernel_dir"), str) or v2, "kernel directory path")
    raw_kernel = binding["container_kernel_dir"] if v2 else data["kernel_dir"]
    kernel_dir = (_container_path(raw_kernel, visible_roots, "kernel directory")
                  if v2 else Path(data["kernel_dir"]))
    kernel_dir = _canonical(kernel_dir, "kernel directory")
    _fail(kernel_dir.is_dir(), "kernel directory must be a directory")
    probe = data.get("linux_probe")
    _fail(isinstance(probe, dict) and
          set(probe) >= {"arch", "release", "kernel_dir"},
          "Linux probe prerequisites missing")
    expected_probe_kernel = binding["container_kernel_dir"] if v2 else str(kernel_dir)
    _fail(probe["arch"] == "x86_64" and probe["kernel_dir"] == expected_probe_kernel,
          "Linux probe identity differs")
    _fail(isinstance(probe["release"], str) and probe["release"],
          "Linux probe release missing")
    for relative in ("Makefile", ".config", "include/config/kernel.release",
                     "include/generated/autoconf.h", "include/generated/utsrelease.h"):
        item = kernel_dir / relative
        _fail(item.is_file() and not item.is_symlink(),
              "Linux probe prerequisite missing: " + relative)
    expected_kernel_inventory = data.get("kernel_inventory")
    if v2:
        expected_kernel_inventory = data.get("kernel_inventory")
    kernel_inventory = _tree_inventory(kernel_dir, visible_roots=visible_roots,
                                       allow_visible_root=v2)
    _fail(kernel_inventory == expected_kernel_inventory,
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
        raw_root = closure["path"]
        root = (_container_path(raw_root, visible_roots, "toolchain closure")
                if v2 else Path(raw_root))
        root = _canonical(root, "toolchain closure")
        inventory = _tree_inventory(root, visible_roots=visible_roots)
        _fail(inventory == closure["inventory"], "complete toolchain inventory differs")
        roots.append(root)
    if not v2:
        _disjoint(roots + [kernel_dir])
    _fail(all((name not in (data.get("mounted_tools") or {}) if v2 and "mounted_tools" in data
               else False) or any(root in Path(ref["path"]).parents for root in roots)
              for name, ref in bound.items()), "tool outside complete toolchain closure")
    path_dirs = data.get("path_dirs")
    _fail(isinstance(path_dirs, list) and path_dirs, "bound PATH missing")
    translated_path_dirs = []
    for directory in path_dirs:
        if v2:
            # Image PATH entries remain in the image namespace; mounted tools
            # retain their explicit /out or /nightly translation.
            directory = (_container_path(directory, visible_roots, "PATH directory")
                         if directory.startswith("/out/") or directory.startswith("/nightly/") else Path(directory))
        else:
            directory = Path(directory)
        directory = _canonical(directory, "PATH directory")
        in_closure = any(root == directory or root in directory.parents for root in roots)
        image_dir = v2 and any(name not in (data.get("mounted_tools") or {}) and
                                Path(ref["path"]).parent == directory
                                for name, ref in bound.items())
        _fail(directory.is_dir() and (in_closure or image_dir), "PATH outside toolchain closure")
        translated_path_dirs.append(directory)
    path_dirs = translated_path_dirs
    for name, descriptor in bound.items():
        selected = next((Path(directory) / name for directory in path_dirs
                         if os.access(str(Path(directory) / name), os.X_OK)), None)
        expected = Path(descriptor.get("target", descriptor["path"]))
        _fail(selected is not None and selected.resolve(strict=True) == expected,
              "PATH tool differs from bound tool: " + name)
    environment = data.get("environment", {})
    _fail(isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str)
                                                  for k, v in environment.items()),
          "toolchain environment")
    # Arbitrary environment can inject compiler plugins, Git executables,
    # library search paths and preloads outside the declared closure.
    _fail(not environment, "unreviewed toolchain environment")
    return {"manifest": data, "manifest_sha256": _sha256(path), "tools": bound,
            "libraries": libraries,
            "kernel_dir": str(kernel_dir), "environment": dict(environment),
            "path": os.pathsep.join(str(directory) for directory in path_dirs)}


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


def _stable_bytes(path, label):
    """Read one no-follow regular inode and reject replacement or byte drift."""
    path = _regular(path, label)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        data = b""
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read()
        after = os.fstat(fd)
        current = path.lstat()
        signature = lambda item: (item.st_dev, item.st_ino, item.st_mode,
                                  item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        _fail(signature(before) == signature(after) == signature(current),
              label + " changed during read")
        return data
    finally:
        os.close(fd)


def _stable_snapshot(path, label):
    """Return bytes plus the bound inode signature for post-write replay."""
    path = _regular(path, label)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read()
        after = os.fstat(fd)
        current = path.lstat()
        signature = lambda item: (item.st_dev, item.st_ino, item.st_mode,
                                  item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        bound = signature(before)
        _fail(bound == signature(after) == signature(current), label + " changed during read")
        return data, bound
    finally:
        os.close(fd)


def _run_process(argv, cwd, env, stdout, stderr, timeout, label, latch=None, output_fsize=None):
    _fail(output_fsize is None or type(output_fsize) is int and 0 < output_fsize <= 1048576, "bounded release export capture")
    _check_signal(latch)
    _fail(timeout > 0 and timeout <= MAX_TIMEOUT, "invalid timeout")
    stdout = Path(stdout); stderr = Path(stderr)
    exit_code = None
    with stdout.open("ab", buffering=0) as out, stderr.open("ab", buffering=0) as err:
        process = None
        try:
            process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdout=out, stderr=err,
                                       start_new_session=True,
                                       preexec_fn=(lambda: resource.setrlimit(resource.RLIMIT_FSIZE, (output_fsize, output_fsize))) if output_fsize is not None else None)
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



def _no_core_panic_undefined(text):
    rows=[]
    for line in text.splitlines():
        words=line.strip().split(None,1)
        _fail(len(words)==2 and words[0] in ('U','w','v'), 'production Rust nm row format')
        rows.append(words[1])
    _fail(rows and rows.count('clone_thread')==1, 'production Rust undefined provider witness')
    forbidden=[name for name in rows if 'panic_bounds_check' in name or 'unwrap_failed' in name]
    _fail(not forbidden, 'unsupported production Rust core panic references: '+repr(forbidden))
    return {'status':'PASS_PRODUCTION_RUST_NO_TARGETED_CORE_PANIC_REFS',
            'undefined_count':len(rows),'clone_thread_undefined':1,'forbidden':forbidden}


def _validate_production_rust_panic_refs(build, tools, evidence, env, timeout, command_rows):
    obj=build/'kernel/rust/mckernel_rust.o'
    before=_artifact(obj, 'actual production Rust object')
    header=obj.read_bytes()[:20]
    _fail(len(header)==20 and header[:7]==b'\x7fELF\x02\x01\x01' and
          int.from_bytes(header[16:18],'little')==1 and int.from_bytes(header[18:20],'little')==62,
          'production Rust object ELF64 little-endian x86-64 ET_REL')
    out=evidence/'production-rust-undefined.nm';err=evidence/'production-rust-undefined.nm.stderr'
    command=[tools['tools']['nm']['path'],'--undefined-only','--demangle',str(obj)]
    row={'phase':'production-rust-core-panic-reference-check','argv':command,'cwd':str(build),
         'exit_code':None,'actual_generated_make_sha256':_sha256(build/'kernel/CMakeFiles/mckernel_rust_obj.dir/build.make')}
    command_rows.append(row)
    row['exit_code']=_run_process(command,build,env,out,err,timeout,row['phase'],output_fsize=1048576)
    _fail(row['exit_code']==0 and err.stat().st_size==0 and out.stat().st_size<1048576,
          'production Rust nm observer failed')
    proof=_no_core_panic_undefined(out.read_text())
    _fail(_artifact(obj,'stable production Rust object')==before,'production Rust object changed during nm')
    proof.update(object=before,nm_stdout=_artifact(out,'production Rust nm'),nm_stderr=_artifact(err,'production Rust nm stderr'),command=row)
    _atomic_json(evidence/'production-rust-core-panic-reference-proof.json',proof)
    return proof


def _validate_image(build, toolchain, evidence, *, native_fork_owned_transaction=False, source_root=None):
    required = {
        "mckernel.img": build / "kernel/mckernel.img",
        "mckernel.img.map": build / "kernel/mckernel.img.map",
        "CMakeCache.txt": build / "CMakeCache.txt",
        "compile_commands.json": build / "compile_commands.json",
        "mckernel_rust.o": build / "kernel/rust/mckernel_rust.o",
        "build.make": build / "kernel/CMakeFiles/mckernel_rust_obj.dir/build.make",
    }
    if native_fork_owned_transaction:
        required.update({
            "mcexec": build / "executer/user/mcexec",
            "mcexec_helpers.o": build / "executer/user/rust/mcexec_helpers.o",
            "mcexec-rust-build.make": build / "executer/user/CMakeFiles/mcexec_rust_helpers.dir/build.make",
        })
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
    link_snapshot = _validate_link_contract(build, evidence, toolchain)
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
    if native_fork_owned_transaction:
        _validate_native_fork_opt_in(build, source_root, toolchain, evidence,
                                     cache, makefile, compile, symbols, object_symbols, required)
    _write_fsync(evidence / "elf-header.txt", header)
    _write_fsync(evidence / "symbols.txt", symbols)
    _write_fsync(evidence / "rust-object-symbols.txt", object_symbols)
    for name, path in required.items():
        _fail(_artifact(path, "validated artifact") == artifacts[name],
              "artifact changed during validation")
    _revalidate_link_contract_snapshots(build, evidence, link_snapshot)
    _check_signal()
    # Keep the exact link inputs and evidence bound beyond image inspection:
    # source/toolchain rechecks, copying and receipt inventory still follow.
    return artifacts, link_snapshot



def _validate_native_fork_opt_in(build, source_root, tools, evidence,
                                  cache, makefile, compile, symbols, rust_symbols, required):
    """Validate actual generated caller flags and linked native/user providers.

    Configuration opt-in is never a task/MM permit, native success or ACK.
    """
    _fail("ENABLE_NATIVE_FORK_OWNED_TRANSACTION:BOOL=ON" in cache, "owned fork option not ON")
    _fail("ENABLE_RUST_USER_TOOLS:BOOL=ON" in cache, "Rust mcexec option not ON")
    _fail("native_linux_irq_work_v6_12" in makefile, "native Rust cfg missing")
    def row_for(relative):
        rows = [row for row in compile if row.get("file") == str(source_root / relative)]
        _fail(len(rows) == 1, "unique actual compile row missing: " + relative)
        row = rows[0]
        return row, list(row["arguments"]) if "arguments" in row else shlex.split(row["command"])
    row, args = row_for("kernel/syscall.c")
    for flag in ("MCKERNEL_NATIVE_FORK_OWNED_TRANSACTION", "MCKERNEL_RUST_SYSCALL_OFFLOAD",
                 "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS", "MCKERNEL_NATIVE_CLONE_TID"):
        _fail(args.count("-D" + flag) == 1, "actual caller flag missing/duplicate: " + flag)
    _, process_args = row_for("kernel/process.c")
    _fail(process_args.count("-DMCKERNEL_RUST_PROCESS_HELPERS") == 1, "actual constructor provider selection")
    user_row, user_args = row_for("executer/user/mcexec.c")
    _fail(user_args.count("-DMCEXEC_RUST_HELPERS") == 1, "actual mcexec C consumer is not Rust-selected")
    obj = Path(args[args.index("-o") + 1])
    if not obj.is_absolute(): obj = Path(row["directory"]) / obj
    nm = tools["tools"]["nm"]["path"]
    caller_symbols = _bounded_output([nm, "-g", str(obj)], "actual owned fork C caller nm")
    bridges = ("process_fork_construct_current_v1", "process_fork_cancel_constructed_current_v1",
               "process_fork_owned_caller_runnable_current_v2", "process_fork_runtime_drain_current_v1")
    for symbol in bridges:
        _fail(len(re.findall(r"\bU\s+" + re.escape(symbol) + r"\s*$", caller_symbols, re.M)) == 1,
              "actual C caller does not consume: " + symbol)
        for label, text in (("Rust object", rust_symbols), ("linked image", symbols)):
            _fail(len(re.findall(r"\bT\s+" + re.escape(symbol) + r"\s*$", text, re.M)) == 1,
                  label + " does not uniquely define " + symbol)
    # The selected real exec commit point must consume the reviewed Rust reset.
    reset = "exec_reset_signal_state_current_v1"
    _fail(len(re.findall(r"\bU\s+" + reset + r"\s*$", caller_symbols, re.M)) == 1,
          "actual C exec commit caller does not import Rust reset")
    for label, text in (("Rust object", rust_symbols), ("linked image", symbols)):
        _fail(len(re.findall(r"\bT\s+" + reset + r"\s*$", text, re.M)) == 1,
              label + " does not uniquely define selected exec reset")
    user_make = required["mcexec-rust-build.make"].read_text(encoding="utf-8", errors="strict")
    _fail("--crate-name mcexec_helpers" in user_make and tools["tools"]["rustc"]["path"] in user_make,
          "real whole mcexec Rust command/tool missing")
    user_symbols = _bounded_output([nm, "-g", str(required["mcexec"])], "actual linked mcexec nm")
    helper_symbols = _bounded_output([nm, "-g", str(required["mcexec_helpers.o"])], "mcexec Rust provider nm")
    user_obj = Path(user_args[user_args.index("-o") + 1])
    if not user_obj.is_absolute(): user_obj = Path(user_row["directory"]) / user_obj
    user_c_symbols = _bounded_output([nm, "-g", str(user_obj)], "actual mcexec C consumer nm")
    entry = "mcexec_main_loop_thread_func_body"
    _fail(len(re.findall(r"\bU\s+" + entry + r"\s*$", user_c_symbols, re.M)) == 1,
          "actual mcexec C does not consume the selected Rust main loop")
    _fail(len(re.findall(r"\bT\s+" + entry + r"\s*$", helper_symbols, re.M)) == 1,
          "actual mcexec Rust does not uniquely define the selected main loop")
    for symbol in ("act_clone_complete", "mcexec_fork_sync_complete_result"):
        for text in (user_symbols, helper_symbols):
            _fail(len(re.findall(r"\bT\s+" + re.escape(symbol) + r"\s*$", text, re.M)) == 1,
                  "real selector1 producer not uniquely Rust-owned: " + symbol)
    _fail(len(re.findall(r"\bT\s+mcexec_clone_child_bridge\s*$", user_symbols, re.M)) == 1,
          "real linked mcexec child bridge missing")
    _write_fsync(evidence / "owned-fork-caller-symbols.txt", caller_symbols)
    _write_fsync(evidence / "owned-fork-mcexec-C-symbols.txt", user_c_symbols)
    _write_fsync(evidence / "owned-fork-mcexec-symbols.txt", user_symbols)
    _write_fsync(evidence / "owned-fork-mcexec-rust-symbols.txt", helper_symbols)
    _atomic_json(evidence / "owned-fork-opt-in.json", {
        "status": "ACTUAL_CONFIG_CALLER_AND_LINK_WITNESSES_ONLY", "option": True,
        "actual_C_caller": str(obj), "bridges": list(bridges),
        "native_runtime_or_final_ACK_acceptance": False,
        "mcexec_artifact": _artifact(required["mcexec"], "matching mcexec"),
    })


def _validate_link_contract(build, evidence, toolchain):
    """Require the final image's direct raw-ld command and live depfile."""
    link = Path(build) / "kernel/CMakeFiles/mckernel.img.dir/link.txt"
    _fail(link.is_file() and not link.is_symlink(), "image link command missing")
    link_bytes, link_snapshot = _stable_snapshot(link, "image link command")
    _fail(link_bytes.endswith(b"\n") and b"\r" not in link_bytes and
          link_bytes.count(b"\n") == 1, "image link command must contain one line")
    try:
        tokens = shlex.split(link_bytes.decode("utf-8", errors="strict"))
    except ValueError as exc:
        raise ImageBuildError("image link command malformed") from exc
    expected_ld = toolchain["tools"]["ld"]["path"]
    _fail(tokens and tokens[0] == expected_ld, "image link is not the bound raw ld")
    _fail(not any(token.startswith(("-Wl,", "-Xlinker")) for token in tokens),
          "image link uses compiler linker wrapper")
    _fail(not any(token.startswith("@") for token in tokens), "image link response file is not allowed")
    _fail(not any(any(character in token for character in (";", "|", "&", "<", ">", "`")) or
                  "$((" in token or "$(" in token for token in tokens),
          "image link shell control is not allowed")
    dependency_tokens = []
    for index, token in enumerate(tokens):
        if token == "--dependency-file":
            _fail(index + 1 < len(tokens), "image link dependency-file argument missing")
            dependency_tokens.append(tokens[index + 1])
        elif token.startswith("--dependency-file="):
            dependency_tokens.append(token.split("=", 1)[1])
    _fail(len(dependency_tokens) == 1, "image link dependency-file is duplicated or missing")
    dependency = dependency_tokens[0]
    _fail(dependency == "CMakeFiles/mckernel.img.dir/link.d" or
          dependency == str(Path(build) / "kernel/CMakeFiles/mckernel.img.dir/link.d"),
          "image link dependency-file spelling differs")
    entry_tokens = [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "-e"]
    _fail(len(entry_tokens) == 1 and entry_tokens[0] == "arch_start" and
          not any(token.startswith("--entry") or (token.startswith("-e") and token != "-e")
                  for token in tokens), "image link entry differs")
    script_tokens = [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "-T"]
    _fail(len(script_tokens) == 1, "image link script is duplicated or missing")
    script = script_tokens[0]
    expected_script = str(Path(build) / "kernel/config/smp-x86.lds")
    _fail(script is not None and script == expected_script and
          not any(token.startswith("--script") or (token.startswith("-T") and token != "-T")
                  for token in tokens),
          "image link script differs")
    _fail(sum(token == "--build-id" for token in tokens) == 1 and
          not any(token.startswith("--build-id=") for token in tokens),
          "image link build-id option differs")
    expected_map = str(Path(build) / "kernel/mckernel.img.map")
    map_tokens = [token[5:] for token in tokens if token.startswith("-Map=")]
    _fail(len(map_tokens) == 1 and map_tokens[0] == expected_map and
          not any(token.startswith("-Map") and token != "-Map=" + expected_map for token in tokens),
          "image link map differs")
    # This freestanding raw-ld contract has no library selection at all.  A
    # name blacklist misses split, equals and colon spellings (and new names).
    _fail(not any(token.startswith(("-l", "--library", "-L", "--default-lib",
                                    "-default-lib")) for token in tokens[1:]),
          "image link includes library-selection/default-library option")
    forbidden_lib_names = {"libc.a", "libc.so", "libpthread.a", "libpthread.so",
                           "libm.a", "libm.so", "libdl.a", "libdl.so", "libgcc_s.so"}
    crt_names = {"crt1.o", "crti.o", "crtn.o", "crtbegin.o", "crtend.o",
                 "crtbeginS.o", "crtendS.o", "crtbeginT.o", "crtendT.o"}
    forbidden_crt = lambda token: Path(token).name in crt_names
    forbidden_lib = lambda token: Path(token).name in forbidden_lib_names or \
        Path(token).name in {"libc.a", "libc.so", "libgcc.a", "libgcc_s.so"}
    _fail(not any(forbidden_crt(token) or forbidden_lib(token) for token in tokens[1:]),
          "image link includes CRT/default library")
    # GNU ld accepts long-option aliases with one dash and abbreviations.
    # Accept only the option spellings emitted by this target, so another
    # spelling cannot silently override its checked entry/script/map/depfile.
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in ("-e", "-T", "-o", "--dependency-file"):
            _fail(index + 1 < len(tokens), "image link option argument missing")
            index += 2
            continue
        _fail(not token.startswith("-") or token == "--build-id" or
              token.startswith(("-Map=", "--dependency-file=")),
              "image link unsupported option spelling: " + token)
        index += 1
    depfile = Path(dependency)
    if not depfile.is_absolute():
        depfile = Path(build) / "kernel" / depfile
    depfile_bytes, dep_snapshot = _stable_snapshot(depfile, "image link dependency file")
    _fail(depfile_bytes, "image link dependency file missing")
    _write_fsync(evidence / "image-link-contract.txt", link_bytes.decode("utf-8"))
    _write_fsync(evidence / "image-link-dependency.d", depfile_bytes.decode("utf-8"))
    link_after, link_after_snapshot = _stable_snapshot(link, "image link command")
    dep_after, dep_after_snapshot = _stable_snapshot(depfile, "image link dependency file")
    _fail((link_after, link_after_snapshot) == (link_bytes, link_snapshot) and
          (dep_after, dep_after_snapshot) == (depfile_bytes, dep_snapshot),
          "image link inputs changed after evidence write")
    evidence_link = _stable_snapshot(evidence / "image-link-contract.txt", "image link evidence")
    evidence_dep = _stable_snapshot(evidence / "image-link-dependency.d", "image dependency evidence")
    _fail(evidence_link[0] == link_bytes and evidence_dep[0] == depfile_bytes,
          "image link evidence changed after write")
    # Nested tuples contain only immutable bytes/integers, including the
    # evidence inode identities; a same-byte replacement is still drift.
    return ((link_bytes, link_snapshot), (depfile_bytes, dep_snapshot),
            evidence_link, evidence_dep)


def _revalidate_link_contract_snapshots(build, evidence, snapshots):
    """Recheck all four byte/inode identities without refreshing the baseline."""
    link_snapshot, dep_snapshot, evidence_link, evidence_dep = snapshots
    link = Path(build) / "kernel/CMakeFiles/mckernel.img.dir/link.txt"
    depfile = Path(build) / "kernel/CMakeFiles/mckernel.img.dir/link.d"
    current_link = _stable_snapshot(link, "image link command")
    current_dep = _stable_snapshot(depfile, "image link dependency file")
    _fail(current_link == link_snapshot and current_dep == dep_snapshot,
          "image link inputs changed during final validation")
    _fail(_stable_snapshot(evidence / "image-link-contract.txt", "image link evidence") == evidence_link and
          _stable_snapshot(evidence / "image-link-dependency.d", "image dependency evidence") == evidence_dep,
          "image link evidence changed during final validation")


def _validate_modules_end_probe(build, toolchain, evidence):
    """Fail closed on the real configure-time external-module probe.

    Older CMake sources did not propagate the nested make status.  Requiring
    its produced module and independently extracting the initialized value
    keeps a configure-only diagnostic from silently accepting that failure.
    """
    module = build / "tmp.resolve_MODULES_END/driver.ko"
    _fail(module.is_file() and not module.is_symlink(),
          "MODULES_END probe driver.ko missing after configure")
    readelf = toolchain["tools"]["readelf"]["path"]
    dd = toolchain["tools"]["dd"]["path"]
    header = _bounded_output([readelf, "-h", str(module)], "MODULES_END probe ELF header",
                             reject_stderr=True)
    _fail("Class:" in header and re.search(r"Class:\s*ELF64\s*$", header, re.M) and
          re.search(r"Data:\s*2's complement, little endian\s*$", header, re.M) and
          re.search(r"Machine:\s*Advanced Micro Devices X86-64\s*$", header, re.M) and
          re.search(r"Type:\s*REL(?:\s|$)", header) is not None,
          "MODULES_END probe is not ELF64 little-endian x86-64")
    sections = _bounded_output([readelf, "-W", "-S", str(module)],
                               "MODULES_END probe readelf", reject_stderr=True)
    section_rows = []
    for match in re.finditer(r"^\s*\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+", sections, re.M):
        section_rows.append({"index": int(match.group(1)), "name": match.group(2), "type": match.group(3),
                             "address": int(match.group(4), 16), "offset": int(match.group(5), 16),
                             "size": int(match.group(6), 16)})
    data_rows = [row for row in section_rows if row["name"] == ".data"]
    _fail(len(data_rows) == 1 and data_rows[0]["type"] == "PROGBITS",
          "MODULES_END probe .data section malformed")
    data = data_rows[0]
    module_size = module.stat().st_size
    _fail(data["size"] >= 8 and data["offset"] + data["size"] <= module_size,
          "MODULES_END probe .data geometry malformed")
    symbols = _bounded_output([readelf, "-W", "-s", str(module)],
                              "MODULES_END probe symbol table", reject_stderr=True)
    symbol_rows = []
    for match in re.finditer(r"^\s*\d+:\s*([0-9A-Fa-f]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$", symbols, re.M):
        symbol_rows.append({"value": int(match.group(1), 16), "size": int(match.group(2)),
                            "type": match.group(3), "bind": match.group(4), "visibility": match.group(5),
                            "section": match.group(6), "name": match.group(7)})
    named = [row for row in symbol_rows if row["name"] == "MAP_KERNEL_START"]
    _fail(len(named) == 1, "MODULES_END probe MAP_KERNEL_START symbol missing or ambiguous")
    symbol = named[0]
    _fail(symbol["type"] == "OBJECT" and symbol["bind"] == "GLOBAL" and
          symbol["visibility"] == "DEFAULT" and symbol["size"] == 8 and
          symbol["section"] == str(data["index"]), "MODULES_END probe MAP_KERNEL_START symbol malformed")
    offset = data["offset"] + symbol["value"] - data["address"]
    _fail(offset >= data["offset"] and offset + 8 <= data["offset"] + data["size"] and
          offset + 8 <= module_size, "MODULES_END probe MAP_KERNEL_START offset malformed")
    value = _bounded_output([dd, "if=" + str(module), "bs=1", "skip=" + str(offset),
                             "count=8", "status=none"],
                            "MODULES_END probe dd", raw_bytes=True, reject_stderr=True)
    _fail(len(value) == 8, "MODULES_END probe MAP_KERNEL_START bytes malformed")
    map_kernel_start = int.from_bytes(value, byteorder="little")
    _fail(0xffff800000000000 <= map_kernel_start <= 0xffffffffffffffff,
          "MODULES_END probe MAP_KERNEL_START is not canonical x86_64")
    value_hex = hex(map_kernel_start)
    linker = build / "kernel/config/smp-x86.lds"
    flags = build / "kernel/CMakeFiles/mckernel.img.dir/flags.make"
    compile_commands = build / "compile_commands.json"
    for path in (linker, flags, compile_commands):
        _fail(path.is_file() and not path.is_symlink(), "MODULES_END probe consumer missing: " + str(path))
    linker_text = linker.read_text(encoding="utf-8", errors="strict")
    _fail(re.search(r"^\s*\.\s*=\s*" + re.escape(value_hex) + r"\s*\+\s*0x1000;\s*$", linker_text, re.M) is not None,
          "MODULES_END probe linker consumer differs")
    def definitions(tokens, label, require_definitions=True):
        """Validate protected macro options in one compiler invocation.

        ``compile_commands.json`` is a database of independent invocations.
        In particular, its rows must never be combined: doing so could make
        two individually incomplete invocations look complete.
        """
        expected = {"MAP_KERNEL_START": value_hex + "UL", "KERNEL_RAM_VADDR": value_hex}
        found = {name: [] for name in expected}
        relevant = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token in ("-D", "-U"):
                _fail(index + 1 < len(tokens), "MODULES_END probe " + label + " compiler option missing argument")
                kind, argument = token, tokens[index + 1]
                index += 2
            elif token.startswith("-D") or token.startswith("-U"):
                kind, argument = token[:2], token[2:]
                index += 1
            else:
                index += 1
                continue
            macro = argument.split("=", 1)[0]
            protected = next((name for name in expected
                              if macro == name or macro.startswith(name + "(") or
                              (macro.startswith(name) and
                               (any(character.isspace() for character in macro[len(name):]) or
                                not re.match(r"^[A-Za-z0-9_]*$", macro[len(name):])))), None)
            if protected is None:
                continue
            relevant = True
            # A function-like spelling is a distinct macro from the protected
            # object-like macro, and can shadow or evade the value check.
            _fail(macro == protected, "MODULES_END probe " + label + " consumer differs")
            _fail(kind == "-D" and "=" in argument and
                  argument.split("=", 1)[1] == expected[protected],
                  "MODULES_END probe " + label + " consumer differs")
            found[protected].append(argument.split("=", 1)[1])
        if require_definitions:
            _fail(all(found[name] and set(found[name]) == {expected[name]} for name in expected),
                  "MODULES_END probe " + label + " consumer differs")
        return relevant

    def text_tokens(text, label):
        try:
            return shlex.split(text)
        except ValueError as exc:
            raise ImageBuildError("MODULES_END probe " + label + " compiler tokens malformed") from exc

    def text_definitions(text, label, require_definitions=True):
        return definitions(text_tokens(text, label), label, require_definitions)

    source_suffixes = (".c", ".cc", ".cpp", ".cxx", ".s", ".S", ".rs")

    def kernel_source_path(path):
        normalized = path.replace("\\", "/")
        return (normalized.startswith("kernel/") or "/kernel/" in normalized) and \
            normalized.endswith(source_suffixes)

    def invocation_has_kernel_source(tokens):
        return any(not token.startswith("-") and kernel_source_path(token) for token in tokens)

    flags_text = flags.read_text(encoding="utf-8", errors="strict")
    compile = _json(compile_commands, "MODULES_END probe compile_commands")
    _fail(isinstance(compile, list), "MODULES_END probe compile_commands malformed")
    text_definitions(flags_text, "flags")
    applicable_rows = 0
    for row_index, row in enumerate(compile):
        _fail(isinstance(row, dict), "MODULES_END probe compile_commands malformed")
        source = row.get("file")
        command = row.get("command")
        arguments = row.get("arguments")
        _fail(isinstance(source, str) and source.strip(),
              "MODULES_END probe compile_commands malformed")
        _fail(command is None or isinstance(command, str),
              "MODULES_END probe compile_commands malformed")
        _fail(arguments is None or (isinstance(arguments, list) and
                                    all(isinstance(argument, str) for argument in arguments)),
              "MODULES_END probe compile_commands malformed")
        _fail(command is not None or arguments is not None,
              "MODULES_END probe compile_commands malformed")
        command_tokens = text_tokens(command, "compile_commands row %d command" % row_index) \
            if command is not None else None
        applicable = kernel_source_path(source) or \
            (command_tokens is not None and invocation_has_kernel_source(command_tokens)) or \
            (arguments is not None and invocation_has_kernel_source(arguments))
        if not applicable:
            continue
        applicable_rows += 1
        # A relevant row may provide one or both standardized encodings.  The
        # row source/invocation makes applicability independent of macro text;
        # every supplied encoding must therefore contain both exact macros.
        if command is not None:
            _fail(command_tokens, "MODULES_END probe compile_commands row %d command empty" % row_index)
            definitions(command_tokens, "compile_commands row %d command" % row_index)
        if arguments is not None:
            _fail(arguments, "MODULES_END probe compile_commands row %d arguments empty" % row_index)
            definitions(arguments, "compile_commands row %d arguments" % row_index)
    _fail(applicable_rows > 0, "MODULES_END probe compile_commands consumer differs")
    observed = {"module": _artifact(module, "MODULES_END probe module"),
                "data_offset": offset, "data_size": data["size"], "section_index": data["index"],
                "map_kernel_start_hex": value_hex,
                "consumers": {str(path.relative_to(build)): _artifact(path, "MODULES_END probe consumer")
                              for path in (linker, flags, compile_commands)},
                "readelf": readelf, "dd": dd}
    _write_fsync(evidence / "modules-end-probe.json",
                 json.dumps(observed, sort_keys=True, indent=2) + "\n")
    return observed


def _validate_gitlink_closure(source_root, manifest_path, base_manifest_path,
                              candidate_sha, ihk_sha, git_tool):
    """Validate the separately mounted libdwarf tree before and after build."""
    document = _json(manifest_path, "gitlink manifest")
    _fail(document.get("schema") == "mckernel.native-exact-mckernel-gitlink-inputs.v1",
          "gitlink manifest schema")
    _fail(document.get("candidate_sha") == candidate_sha and document.get("ihk_sha") == ihk_sha,
          "gitlink manifest identity")
    base_manifest = _json(base_manifest_path, "base source manifest")
    _fail(document.get("base_manifest_sha256") == _sha256(base_manifest_path),
          "gitlink base manifest hash differs")
    consumed = document.get("consumed_gitlinks")
    _fail(isinstance(consumed, dict) and set(consumed) ==
          {"executer/user/lib/libdwarf/libdwarf"}, "consumed gitlink set differs")
    row = consumed["executer/user/lib/libdwarf/libdwarf"]
    _fail(isinstance(row, dict) and row.get("path") ==
          "executer/user/lib/libdwarf/libdwarf", "libdwarf gitlink row missing")
    _fail((base_manifest.get("gitlinks") or {}).get(row["path"]) == row.get("commit") and
          re.fullmatch(r"[0-9a-f]{40}", str(row.get("commit", ""))) and
          re.fullmatch(r"[0-9a-f]{40}", str(row.get("tree", ""))),
          "base manifest gitlink differs")
    root = _canonical(source_root / "executer/user/lib/libdwarf/libdwarf",
                      "libdwarf checkout", directory=source_root)
    git = lambda *args: _git(root, *args, tool=git_tool).decode()
    for args, expected, label in ((["rev-parse", "HEAD"], row.get("commit"), "HEAD"),
                                  (["rev-parse", "HEAD^{tree}"], row.get("tree"), "tree")):
        _fail(git(*args).strip() == expected, "libdwarf " + label + " differs")
    _fail(not git("status", "--porcelain=v1", "--ignored=matching", "--untracked-files=all"),
          "libdwarf checkout is dirty")
    try:
        index_rows = provenance.git_rows(_git(root, "ls-files", "--stage", "-z", tool=git_tool))
        tree_rows = provenance.git_rows(
            _git(root, "ls-tree", "-r", "--full-tree", "-z", "HEAD", tool=git_tool),
            tree=True)
    except provenance.BuildError as exc:
        raise ImageBuildError(str(exc)) from exc
    _fail(index_rows == tree_rows, "libdwarf index differs from HEAD tree")
    _fail(set(index_rows) == set(row.get("files", {})), "libdwarf tracked file set differs")
    observed = {}
    for relative, expected in row.get("files", {}).items():
        _fail(isinstance(relative, str) and relative and not Path(relative).is_absolute() and
              ".." not in Path(relative).parts and "\\" not in relative and "\0" not in relative,
              "libdwarf path escapes checkout")
        path = root / relative
        _fail(path.resolve(strict=False) == path and path.is_file() and not path.is_symlink(),
              "libdwarf path differs: " + relative)
        mode = format(stat.S_IFMT(path.lstat().st_mode) | stat.S_IMODE(path.lstat().st_mode), "06o")
        blob = git("hash-object", "--no-filters", "--", relative).strip()
        observed[relative] = {"mode": mode, "blob": blob, "sha256": _sha256(path)}
        _fail((mode, blob) == tree_rows[relative],
              "libdwarf worktree differs from HEAD tree: " + relative)
        _fail(observed[relative] == expected, "libdwarf tracked path differs: " + relative)
    git_meta = _canonical(root / ".git", "libdwarf Git metadata", directory=root)
    git_dir = git("rev-parse", "--absolute-git-dir").strip()
    common_raw = git("rev-parse", "--git-common-dir").strip()
    common = Path(common_raw)
    if not common.is_absolute():
        common = (root / common).resolve()
    _fail(Path(git_dir) == git_meta and common == git_meta,
          "libdwarf uses external Git metadata")
    _fail(not (git_meta / "objects/info/alternates").exists() and
          not (git_meta / "shallow").exists() and
          git("rev-parse", "--is-shallow-repository").strip() == "false" and
          not git("for-each-ref", "--format=%(refname)", "refs/replace").strip(),
          "libdwarf uses external or replacement Git objects")
    metadata = {}
    for item in sorted(git_meta.rglob("*")):
        relative = item.relative_to(git_meta).as_posix()
        _fail(relative and ".." not in Path(relative).parts,
              "libdwarf Git metadata path differs")
        info = item.lstat()
        _fail(not stat.S_ISLNK(info.st_mode), "libdwarf Git metadata contains symlink")
        _fail(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),
              "libdwarf Git metadata contains special file")
        if stat.S_ISREG(info.st_mode):
            metadata[relative] = {"mode": format(stat.S_IMODE(info.st_mode), "04o"),
                                  "size": info.st_size, "sha256": _sha256(item)}
    _fail(metadata == row.get("git_metadata"), "libdwarf Git metadata differs")
    return document


def run(*args, **kwargs):
    with SignalLatch():
        return _run(*args, **kwargs)


def _admit_build_gitlink(source, source_root, gitlink_manifest, manifest,
                         candidate_sha, ihk_sha, git_tool):
    if source['manifest'].get('schema') == provenance.THIN_SCHEMA:
        _fail(gitlink_manifest is not None,
              'thin source requires authenticated supplemental libdwarf manifest')
    return (_validate_gitlink_closure(source_root, gitlink_manifest, manifest,
                                      candidate_sha, ihk_sha, git_tool)
            if gitlink_manifest is not None else None)


# One exact accepted-current successor; historical producer remains immutable.
OWNED_FORK_CURRENT_SOURCE_PINS = {'kernel/syscall.c': '1035622a96a5441a85d60a9db15d3ac452b60266d1f8123eb807ce3849c41081', 'kernel/rust/fork_control_guest.rs': '26797f574fa1ba7006eb27ff3a1a7750ec04b83f71a2e90b8c35c4c536b33acd', 'kernel/rust/fork_child_credits.rs': '63b82c97cc6e1204585cfaf2b89ef378b88c1d207a8e82c2f1400bc352f9c98d', 'kernel/rust/fork_constructed_credits.rs': '4c1e96ef4fbf5cb66acc54d900d37fcd68fb4d50dd1337c4428b3f5e2ecd1972', 'kernel/rust/process_helpers.rs': '3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e', 'kernel/rust/sched_helpers.rs': 'd16200db3054d88a83752fda1383d6c101d24de4b787bd78cd42edb46ab251fc', 'kernel/CMakeLists.txt': 'af2758e8cad6fd4baa3c067d23cc81ab483aa71d666ca6249d54e8ccfd2701e5', 'kernel/rust/syscall_policy.rs': 'f1f7866c0f2ccc8e1b0024dfb632ec7359dd2a0a4bcd8e22deb957d48ef6d770', 'kernel/rust/fork_runnable_child.rs': 'a9387ae13b85785176b95fc6ddc79b08bd31dd7960b0730307b41b5a05b5d137', 'kernel/rust/fork_final_ack.rs': '093f742dfe4969d78b2ca6b8b643df94042945e890d26003dec9d1818c34826b', 'kernel/rust/fork_control_registry.rs': 'a2f92bb11cba42fef0d95e1f1e1a4c526351ff90860baed7913fa26c91137ba5', '.kernel-sdk/include/generated/uapi/linux/version.h': '3cc5d7cfe76eb7db13aac6d42be01cd2c5f8da0caaae154798a8d0115bb95571', '.phase5-current-runtime/RETIREMENT-SOURCE-CLOSURE.json': '693518046e937a53a65999f551f1160db28d21fe0cc941da4ee606c49abf0e97'}

# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Inserted into the existing pinned image driver; uses its owned command/capture path.
M14_SOURCE_PINS = {'kernel/rust/tests/run_equivalence.sh': 'b6e5926d39edcdc9b65f00877e74564af4b363ad20034ab5ccccbb9c919ab737', 'kernel/mem.c': '9d53106e7228b5a7654f4250bab58e20e7bc47a28f8ad9675b1c9ac92599b976', 'kernel/rust/page_helpers.rs': 'cfc64f72bf9b94c65417bc8f4e29d65b81f98239fe52ab2a7dd0352ebdfc3f70', 'kernel/process.c': '1ecbc287f2e704e738cc4e9fbe18289226b5aadadc9da88d226dc0ad0bb57234', 'kernel/rust/sched_helpers.rs': 'd16200db3054d88a83752fda1383d6c101d24de4b787bd78cd42edb46ab251fc', 'kernel/include/sched_helpers.h': '9712a3df59eb0251f517ce01254e4576119868924b35f7da6fbee294bff966ae', 'arch/x86_64/kernel/memory.c': '93df0ac24de8163cc5a7e2cce277d3a46c89a607b924c1937f2413e12edf0f66', 'kernel/rust/x86_memory_helpers.rs': '800a18bb4db0e28bf76441fca783b3f8d47066260240fb5107967c23775aa494', 'arch/x86_64/kernel/cpu.c': 'c779079fb6de66991c861c823dca06b2a9ceec16ac4c984995200b668d7e78ce', 'arch/x86_64/kernel/syscall.c': '912fb97a58cc797407979ce835c422578949ff876ac519193d2ebc4855cce791', 'kernel/rust/mem_helpers.rs': '6a527f7a55930d72d6d72c775ee0261c3550e2bd0094fe01031f3aa3238aefd6', 'kernel/rust/process_helpers.rs': '70015d712c29e416881e2fbaccd67026ee15ac7eb915cb80e828485d6f34d71f', 'kernel/rust/syscall_policy.rs': '3ef8288617db7bcc26c56039491295d3f48c53d4f76d111b68dfcc3186546f7d', 'kernel/rust/x86_cpu_helpers.rs': '98914e1ff4d50c2f42ccbdeb1f4f338024b7a9a2143fbad2f59ebd6f6b50dd0b', 'kernel/syscall.c': '34ec8a08c5790aa7533e5a8e3905d1dd1d4989bf0f431b8517ae6d50bbaa54f4'}
M14_IDLE_IMPORTS = ('sched_idle_loop_body_result', 'sched_idle_current_cpu_bridge')
M14_MEMORY_IMPORTS = ('x86_clear_range_public_body', 'clear_range_l1', 'clear_range_l2', 'clear_range_l3')
M14_C_RETIRED_MEMORY_BODIES = ('clear_range_old_action', 'x86_init_normal_set_large_bridge', 'x86_init_text_map_kernel_start_bridge', 'x86_init_text_end_bridge', 'clear_range', 'ihk_mc_pt_clear_range', 'ihk_mc_pt_free_range', 'x86_clear_range_top_log_bridge', 'x86_clear_range_walk_l4_bridge', 'clear_range_l4', 'x86_clear_range_l4_body', 'x86_clear_old_action_bridge', 'x86_clear_phys_to_virt_bridge', 'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge', 'x86_clear_range_public_body', 'clear_range_l1', 'clear_range_l2', 'clear_range_l3')
M14_TIMER_CALLBACKS = ('process_timer_spin_lock_bridge', 'process_timer_spin_unlock_bridge',
                       'process_timer_lapic_enable_bridge', 'process_timer_lapic_disable_bridge')
M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS = '\n/* Actual timer/spin Rust shared-type witness: sourcebound, no compute-C behavior. */\n_Static_assert((sizeof(void *)) == 8UL, "M14 actual Rust sizeof.pointer");\n_Static_assert((sizeof(unsigned long)) == 8UL, "M14 actual Rust sizeof.Culong");\n_Static_assert((sizeof(int)) == 4UL, "M14 actual Rust sizeof.Cint");\n_Static_assert((sizeof(struct thread)) == 5568UL, "M14 actual Rust sizeof.Thread");\n_Static_assert((_Alignof(struct thread)) == 64UL, "M14 actual Rust align.Thread");\n_Static_assert((sizeof(struct cpu_local_var)) == 8128UL, "M14 actual Rust sizeof.CpuLocalVar");\n_Static_assert((_Alignof(struct cpu_local_var)) == 64UL, "M14 actual Rust align.CpuLocalVar");\n_Static_assert((sizeof(struct process)) == 1728UL, "M14 actual Rust sizeof.Process");\n_Static_assert((_Alignof(struct process)) == 64UL, "M14 actual Rust align.Process");\n_Static_assert((sizeof(struct sig_common)) == 2176UL, "M14 actual Rust sizeof.SigCommon");\n_Static_assert((_Alignof(struct sig_common)) == 64UL, "M14 actual Rust align.SigCommon");\n_Static_assert((sizeof(struct timer)) == 56UL, "M14 actual Rust sizeof.Timer");\n_Static_assert((_Alignof(struct timer)) == 8UL, "M14 actual Rust align.Timer");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,current)) == 7848UL, "M14 actual Rust CpuLocalVar.current");\n_Static_assert((__builtin_offsetof(struct thread,cpu_id)) == 16UL, "M14 actual Rust spin.thread_cpu_id_offset");\n_Static_assert((__builtin_offsetof(struct thread,tid)) == 20UL, "M14 actual Rust spin.thread_tid_offset");\n_Static_assert((__builtin_offsetof(struct thread,status)) == 4184UL, "M14 actual Rust spin.thread_status_offset");\n_Static_assert((__builtin_offsetof(struct thread,spin_sleep_lock)) == 4352UL, "M14 actual Rust spin.thread_spin_sleep_lock_offset");\n_Static_assert((__builtin_offsetof(struct thread,spin_sleep)) == 4356UL, "M14 actual Rust spin.thread_spin_sleep_offset");\n_Static_assert((__builtin_offsetof(struct thread,sched_list)) == 4328UL, "M14 actual Rust spin.thread_sched_list_offset");\n_Static_assert((__builtin_offsetof(struct thread,sigpending)) == 4864UL, "M14 actual Rust spin.thread_sigpending_offset");\n_Static_assert((__builtin_offsetof(struct thread,sigcommon)) == 4824UL, "M14 actual Rust spin.thread_sigcommon_offset");\n_Static_assert((__builtin_offsetof(struct sig_common,sigpending)) == 2120UL, "M14 actual Rust spin.sigcommon_sigpending_offset");\n_Static_assert((__builtin_offsetof(struct thread,proc)) == 4304UL, "M14 actual Rust spin.thread_proc_offset");\n_Static_assert((__builtin_offsetof(struct thread,mod_clone)) == 5212UL, "M14 actual Rust spin.thread_mod_clone_offset");\n_Static_assert((__builtin_offsetof(struct process,pid)) == 456UL, "M14 actual Rust spin.proc_pid_offset");\n_Static_assert((__builtin_offsetof(struct process,status)) == 420UL, "M14 actual Rust spin.proc_status_offset");\n_Static_assert((__builtin_offsetof(struct process,update_lock)) == 64UL, "M14 actual Rust spin.proc_update_lock_offset");\n_Static_assert((__builtin_offsetof(struct process,clone_count)) == 1424UL, "M14 actual Rust spin.proc_clone_count_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq_lock)) == 7832UL, "M14 actual Rust spin.cpu_runq_lock_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq_irqstate)) == 7840UL, "M14 actual Rust spin.cpu_runq_irqstate_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,current)) == 7848UL, "M14 actual Rust spin.cpu_current_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,prevpid)) == 7864UL, "M14 actual Rust spin.cpu_prevpid_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq)) == 7872UL, "M14 actual Rust spin.cpu_runq_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq_len)) == 7888UL, "M14 actual Rust spin.cpu_runq_len_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq_reserved)) == 7896UL, "M14 actual Rust spin.cpu_runq_reserved_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,flags)) == 7944UL, "M14 actual Rust spin.cpu_flags_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,status)) == 7920UL, "M14 actual Rust spin.cpu_status_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,in_interrupt)) == 7968UL, "M14 actual Rust spin.cpu_in_interrupt_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,nr_ctx_switches)) == 7984UL, "M14 actual Rust spin.cpu_nr_ctx_switches_offset");\n_Static_assert((__builtin_offsetof(struct thread,status)) == 4184UL, "M14 actual Rust timer.thread_status_offset");\n_Static_assert((__builtin_offsetof(struct thread,sched_list)) == 4328UL, "M14 actual Rust timer.thread_sched_list_offset");\n_Static_assert((__builtin_offsetof(struct thread,spin_sleep_lock)) == 4352UL, "M14 actual Rust timer.thread_spin_sleep_lock_offset");\n_Static_assert((__builtin_offsetof(struct thread,spin_sleep)) == 4356UL, "M14 actual Rust timer.thread_spin_sleep_offset");\n_Static_assert((__builtin_offsetof(struct thread,itimer_enabled)) == 5072UL, "M14 actual Rust timer.thread_itimer_enabled_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq_lock)) == 7832UL, "M14 actual Rust timer.cpu_runq_lock_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq)) == 7872UL, "M14 actual Rust timer.cpu_runq_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,runq_len)) == 7888UL, "M14 actual Rust timer.cpu_runq_len_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,current)) == 7848UL, "M14 actual Rust timer.cpu_current_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,timer_enabled)) == 7980UL, "M14 actual Rust timer.cpu_timer_enabled_offset");\n_Static_assert((__builtin_offsetof(struct cpu_local_var,backlog_list)) == 8056UL, "M14 actual Rust timer.cpu_backlog_list_offset");\n_Static_assert((__builtin_offsetof(struct timer,timeout)) == 0UL, "M14 actual Rust timer.timer_timeout_offset");\n_Static_assert((__builtin_offsetof(struct timer,processes)) == 8UL, "M14 actual Rust timer.timer_waitq_offset");\n_Static_assert((__builtin_offsetof(struct timer,list)) == 32UL, "M14 actual Rust timer.timer_list_offset");\n_Static_assert((__builtin_offsetof(struct timer,thread)) == 48UL, "M14 actual Rust timer.timer_thread_offset");\n_Static_assert((sizeof(struct sched_runqueue_offsets)) == 208UL, "M14 actual Rust descriptor.sizeof.SchedRunqueueOffsets");\n_Static_assert((_Alignof(struct sched_runqueue_offsets)) == 8UL, "M14 actual Rust descriptor.align.SchedRunqueueOffsets");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_cpu_id_offset)) == 0UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_cpu_id_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_tid_offset)) == 8UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_tid_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_status_offset)) == 16UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_status_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_spin_sleep_lock_offset)) == 24UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_spin_sleep_lock_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_spin_sleep_offset)) == 32UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_spin_sleep_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_sched_list_offset)) == 40UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_sched_list_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_sigpending_offset)) == 48UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_sigpending_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_sigcommon_offset)) == 56UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_sigcommon_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,sigcommon_sigpending_offset)) == 64UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.sigcommon_sigpending_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_proc_offset)) == 72UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_proc_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,thread_mod_clone_offset)) == 80UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.thread_mod_clone_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,proc_pid_offset)) == 88UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.proc_pid_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,proc_status_offset)) == 96UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.proc_status_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,proc_update_lock_offset)) == 104UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.proc_update_lock_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,proc_clone_count_offset)) == 112UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.proc_clone_count_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_lock_offset)) == 120UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_runq_lock_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_irqstate_offset)) == 128UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_runq_irqstate_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_current_offset)) == 136UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_current_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_prevpid_offset)) == 144UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_prevpid_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_offset)) == 152UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_runq_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_len_offset)) == 160UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_runq_len_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_reserved_offset)) == 168UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_runq_reserved_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_flags_offset)) == 176UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_flags_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_status_offset)) == 184UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_status_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_in_interrupt_offset)) == 192UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_in_interrupt_offset");\n_Static_assert((__builtin_offsetof(struct sched_runqueue_offsets,cpu_nr_ctx_switches_offset)) == 200UL, "M14 actual Rust descriptor.SchedRunqueueOffsets.cpu_nr_ctx_switches_offset");\n_Static_assert((sizeof(struct timer_runtime_offsets)) == 120UL, "M14 actual Rust descriptor.sizeof.TimerRuntimeOffsets");\n_Static_assert((_Alignof(struct timer_runtime_offsets)) == 8UL, "M14 actual Rust descriptor.align.TimerRuntimeOffsets");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,thread_status_offset)) == 0UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.thread_status_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,thread_sched_list_offset)) == 8UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.thread_sched_list_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,thread_spin_sleep_lock_offset)) == 16UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.thread_spin_sleep_lock_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,thread_spin_sleep_offset)) == 24UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.thread_spin_sleep_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,thread_itimer_enabled_offset)) == 32UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.thread_itimer_enabled_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,cpu_runq_lock_offset)) == 40UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.cpu_runq_lock_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,cpu_runq_offset)) == 48UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.cpu_runq_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,cpu_runq_len_offset)) == 56UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.cpu_runq_len_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,cpu_current_offset)) == 64UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.cpu_current_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,cpu_timer_enabled_offset)) == 72UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.cpu_timer_enabled_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,cpu_backlog_list_offset)) == 80UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.cpu_backlog_list_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,timer_timeout_offset)) == 88UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.timer_timeout_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,timer_waitq_offset)) == 96UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.timer_waitq_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,timer_list_offset)) == 104UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.timer_list_offset");\n_Static_assert((__builtin_offsetof(struct timer_runtime_offsets,timer_thread_offset)) == 112UL, "M14 actual Rust descriptor.TimerRuntimeOffsets.timer_thread_offset");\n_Static_assert((sizeof(__typeof__(&process_timer_spin_lock_bridge))) == 8UL, "M14 actual Rust callback.size.process_timer_spin_lock_bridge");\n_Static_assert((_Alignof(__typeof__(&process_timer_spin_lock_bridge))) == 8UL, "M14 actual Rust callback.align.process_timer_spin_lock_bridge");\n_Static_assert((sizeof(__typeof__(&process_timer_spin_unlock_bridge))) == 8UL, "M14 actual Rust callback.size.process_timer_spin_unlock_bridge");\n_Static_assert((_Alignof(__typeof__(&process_timer_spin_unlock_bridge))) == 8UL, "M14 actual Rust callback.align.process_timer_spin_unlock_bridge");\n_Static_assert((sizeof(__typeof__(&process_timer_lapic_enable_bridge))) == 8UL, "M14 actual Rust callback.size.process_timer_lapic_enable_bridge");\n_Static_assert((_Alignof(__typeof__(&process_timer_lapic_enable_bridge))) == 8UL, "M14 actual Rust callback.align.process_timer_lapic_enable_bridge");\n_Static_assert((sizeof(__typeof__(&process_timer_lapic_disable_bridge))) == 8UL, "M14 actual Rust callback.size.process_timer_lapic_disable_bridge");\n_Static_assert((_Alignof(__typeof__(&process_timer_lapic_disable_bridge))) == 8UL, "M14 actual Rust callback.align.process_timer_lapic_disable_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_irq_save_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_irq_save_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_irq_save_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_irq_save_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_irq_restore_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_irq_restore_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_irq_restore_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_irq_restore_bridge");\n_Static_assert((sizeof(__typeof__(&process_spin_lock_bridge))) == 8UL, "M14 actual Rust callback.size.process_spin_lock_bridge");\n_Static_assert((_Alignof(__typeof__(&process_spin_lock_bridge))) == 8UL, "M14 actual Rust callback.align.process_spin_lock_bridge");\n_Static_assert((sizeof(__typeof__(&process_spin_unlock_bridge))) == 8UL, "M14 actual Rust callback.size.process_spin_unlock_bridge");\n_Static_assert((_Alignof(__typeof__(&process_spin_unlock_bridge))) == 8UL, "M14 actual Rust callback.align.process_spin_unlock_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_noirq_lock_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_noirq_lock_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_noirq_lock_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_noirq_lock_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_noirq_unlock_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_noirq_unlock_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_noirq_unlock_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_noirq_unlock_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_schedule_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_schedule_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_schedule_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_schedule_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_zero_free_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_zero_free_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_zero_free_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_zero_free_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_pause_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_pause_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_pause_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_pause_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_has_signal_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_has_signal_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_has_signal_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_has_signal_bridge");\n_Static_assert((sizeof(__typeof__(&process_sched_runq_log_bridge))) == 8UL, "M14 actual Rust callback.size.process_sched_runq_log_bridge");\n_Static_assert((_Alignof(__typeof__(&process_sched_runq_log_bridge))) == 8UL, "M14 actual Rust callback.align.process_sched_runq_log_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_spin_lock_bridge),unsigned long (*)(unsigned long)),"process_timer_spin_lock_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_spin_unlock_bridge),void (*)(unsigned long,unsigned long)),"process_timer_spin_unlock_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_lapic_enable_bridge),void (*)(unsigned int)),"process_timer_lapic_enable_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_lapic_disable_bridge),void (*)(void)),"process_timer_lapic_disable_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_irq_save_bridge),unsigned long (*)(void)),"process_sched_irq_save_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_irq_restore_bridge),void (*)(unsigned long)),"process_sched_irq_restore_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_spin_lock_bridge),unsigned long (*)(unsigned long)),"process_spin_lock_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_spin_unlock_bridge),void (*)(unsigned long,unsigned long)),"process_spin_unlock_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_noirq_lock_bridge),void (*)(unsigned long)),"process_sched_noirq_lock_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_noirq_unlock_bridge),void (*)(unsigned long)),"process_sched_noirq_unlock_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_schedule_bridge),void (*)(void)),"process_sched_schedule_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_zero_free_bridge),void (*)(void)),"process_sched_zero_free_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_pause_bridge),void (*)(void)),"process_sched_pause_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_has_signal_bridge),int (*)(unsigned long)),"process_sched_has_signal_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_runq_log_bridge),void (*)(int,unsigned long,unsigned long,int,int)),"process_sched_runq_log_bridge actual callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var*)0)->current),struct thread*),"actual current pointer type");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void(*)(int)),"set_timer ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&spin_sleep_or_schedule),void(*)(void)),"spin_sleep ABI");\n'

M14_MIGRATION_RUST_LOG_PROVIDER = 'process_sched_migrate_log_bridge'
M14_MIGRATION_HEADER_ABI_ASSERTIONS = '_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_request_migrate),void(*)(int,struct thread*)),"migration public ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(process_sched_migrate_debug),struct ddebug),"migration original descriptor type");\n_Static_assert(sizeof(struct ddebug)==32 && _Alignof(struct ddebug)==8,"migration descriptor ABI");\n_Static_assert(__builtin_offsetof(struct ddebug,file)==0 && __builtin_offsetof(struct ddebug,func)==8 && __builtin_offsetof(struct ddebug,fmt)==16,"migration descriptor pointer layout");\n_Static_assert(__builtin_types_compatible_p(__typeof__(process_sched_migrate_debug.file),const char*) && __builtin_types_compatible_p(__typeof__(process_sched_migrate_debug.func),const char*) && __builtin_types_compatible_p(__typeof__(process_sched_migrate_debug.fmt),const char*),"migration descriptor pointer types");\n_Static_assert(DDEBUG_DEFAULT==0,"migration original default selector flags");\n'
M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS = '_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_public_body),int(*)(void*,struct process_vm*,unsigned long,unsigned long,int,struct memobj*)),"six-input Rust entry ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_set_range_clear_bridge),int(*)(void*,void*,unsigned long,unsigned long,int,void*)),"six-input actual set-range adapter ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_clear_range),int(*)(page_table_t,struct process_vm*,void*,void*)),"public clear ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_free_range),int(*)(page_table_t,struct process_vm*,void*,void*,struct memobj*)),"public free ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual C remote-flush header ABI");\n_Static_assert(__builtin_types_compatible_p(x86_clear_remote_flush_fn_t,void(*)(void*,unsigned long*,int,int)),"actual erased Rust flush callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_top_log_bridge),void(*)(int,void*,unsigned long,unsigned long,int)),"actual C top-log provider ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l4_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"actual C walker provider ABI");\n'
M14_RUST_EXPORTS = ('process_sched_migrate_log_bridge', 'sched_request_migrate', 'sched_request_migrate_body_result', 'spin_sleep_or_schedule', 'sched_spin_sleep_or_schedule_body_result', 'set_timer', 'get_this_cpu_local_var', 'timer_set_timer_body_result', 'process_sched_set_timer_bridge', 'sched_idle_loop_body_result', 'sched_idle_current_cpu_bridge', 'x86_clear_old_action_bridge', 'x86_clear_phys_to_virt_bridge', 'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge', 'page_unmap', 'x86_init_normal_set_large_bridge', 'x86_init_text_map_kernel_start_bridge', 'x86_init_text_end_bridge', 'sched_idle_begin_body_result', 'sched_idle_iteration_body_result', 'sched_idle_runqueue_has_running_result', 'process_sched_cpu_local_bridge', 'get_cpu_local_var', 'ihk_mc_get_processor_id', 'ihk_mc_pt_clear_range', 'ihk_mc_pt_free_range', 'x86_clear_range_public_body', 'x86_clear_range_top_log_bridge', 'remote_flush_tlb_array_cpumask', 'x86_clear_range_walk_l4_bridge', 'init_pstate_and_turbo', 'x86_clear_range_l4_body', 'vm_range_insert', 'syscall_signalfd_publish_bridge', 'arch_ptrace', 'mem_tlb_atomic_dec_bridge', 'mem_tlb_atomic_inc_bridge', 'mem_tlb_atomic_read_bridge', 'mem_tlb_atomic_set_bridge', 'mem_tlb_current_cpu_bridge', 'mem_tlb_flush_all_bridge', 'mem_tlb_flush_single_bridge', 'mem_tlb_get_vector_bridge', 'mem_tlb_interrupt_cpu_bridge', 'mem_tlb_noirq_lock_bridge', 'mem_tlb_noirq_unlock_bridge', 'mem_tlb_pause_bridge', 'mem_tlb_rdtsc_bridge', 'remote_flush_tlb_cpumask', 'vm_range_insert_dump_bridge', 'vm_range_insert_log_bridge', 'arch_ptrace_syscall_event', 'syscall_signalfd_create_bridge', 'x86_context_line_log_bridge', 'x86_cpu_ulong_log_bridge', 'clear_range_l1', 'clear_range_l2', 'clear_range_l3')


# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _m14_check_page_unmap_symbols(mem_symbols, rust_symbols, final_symbols):
    def rows(text, symbol):
        return [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
    def unique(text, symbol, allowed, size=None):
        found = rows(text, symbol)
        _fail(len(found) == 1 and found[0][-2] in allowed,
              'M14 page_unmap provider type/count: ' + symbol)
        if size is not None:
            _fail(len(found[0]) == 4 and int(found[0][1], 16) == size,
                  'M14 page_unmap immutable ABI geometry width: ' + symbol)
    _fail(not any(row[-2] == 'T' for row in rows(mem_symbols, 'page_unmap')),
          'M14 original C page_unmap wrapper selected')
    unique(rust_symbols, 'page_unmap', ('T',))
    unique(final_symbols, 'page_unmap', ('T',))
    for symbol, size in (('page_unmap_hash_shift', 4), ('page_unmap_hash_mask', 8),
                         ('page_unmap_lock_stride', 8)):
        unique(mem_symbols, symbol, ('R',), size)
        unique(rust_symbols, symbol, ('U',))
        unique(final_symbols, symbol, ('R',), size)
    for symbol in ('page_hash_lock_bridge', 'page_hash_unlock_bridge', 'page_unmap_log_bridge'):
        unique(mem_symbols, symbol, ('T',))
        unique(rust_symbols, symbol, ('U',))
        unique(final_symbols, symbol, ('T',))
    # The accepted GCC9 object uses COMMON for this unchanged tentative global;
    # default GCC14 can use BSS. Both require one allocated provider, never U.
    unique(mem_symbols, 'page_hash_locks', ('B', 'C'))
    unique(rust_symbols, 'page_hash_locks', ('U',))
    unique(final_symbols, 'page_hash_locks', ('B', 'C'))


def _validate_m14_page_unmap_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row, args = _m14_selected_row(source_root, build, 'kernel/mem.c',
                                'MCKERNEL_RUST_PAGE_HELPERS', tools)
    obj = (Path(row['directory']) / args[args.index('-o') + 1]).resolve(strict=True)
    objects['kernel/mem.c'] = _artifact(obj, 'M14 actual default public page_unmap C consumer')
    out = build / 'm14-production'
    oi = args.index('-o')
    pp = _m14_observe(args[:oi] + ['-E', str(source_root / 'kernel/mem.c')],
                      'selected-mem-public-page-unmap-preprocess', out, tools, env, timeout, command_rows)
    _fail(re.search(r'\bint\s+page_unmap\s*\([^;{}]*\)\s*\{', pp, re.S) is None
          and re.search(r'\bint\s+page_unmap\s*\([^;{}]*\)\s*;', pp, re.S) is not None,
          'M14 selected public page_unmap C exclusion/declaration')
    texts = []
    for path, label in ((obj, 'default-mem-public-ownership'),
                        (build / 'kernel/rust/mckernel_rust.o', 'Rust-public-page-unmap-ownership'),
                        (build / 'kernel/mckernel.img', 'image-public-page-unmap-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'], '-S', '-g', str(path)],
                                 label, out, tools, env, timeout, command_rows))
    _m14_check_page_unmap_symbols(*texts)
    return dict(public_Rust_provider='page_unmap', C_wrapper_excluded=True,
                immutable_geometry_widths={'page_unmap_hash_shift': 4,
                                           'page_unmap_hash_mask': 8,
                                           'page_unmap_lock_stride': 8},
                callbacks=('page_hash_lock_bridge', 'page_hash_unlock_bridge', 'page_unmap_log_bridge'),
                default_mem_object=objects['kernel/mem.c'], native=False)


def _m14_check_textmap_symbols(memory_symbols, rust_symbols, image_symbols):
    def rows(text, symbol):
        return [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
    getter = 'x86_init_text_map_kernel_start_bridge'
    geometry = 'x86_map_kernel_start_geometry'
    _fail(not rows(memory_symbols, getter), 'M14 textmap original C getter selected')
    for text in (rust_symbols, image_symbols):
        found = rows(text, getter)
        _fail(len(found) == 1 and found[0][-2] == 'T', 'M14 textmap unique Rust getter owner')
    for text in (memory_symbols, image_symbols):
        found = rows(text, geometry)
        _fail(len(found) == 1 and len(found[0]) == 4 and found[0][-2] == 'R' and
              int(found[0][1], 16) == 8, 'M14 textmap immutable LP64 geometry provider')
    found = rows(rust_symbols, geometry)
    _fail(len(found) == 1 and found[0][-2] == 'U', 'M14 textmap Rust geometry consumer')
    _fail(not any(row[-2] == 'U' for row in rows(rust_symbols, getter)), 'M14 textmap unresolved Rust getter')
    end_getter = 'x86_init_text_end_bridge'
    _fail(not any(row[-2] in ('T', 't') for row in rows(memory_symbols, end_getter)),
          'M14 text-end original C getter selected')
    for text in (rust_symbols, image_symbols):
        found = rows(text, end_getter)
        _fail(len(found) == 1 and found[0][-2] == 'T', 'M14 text-end unique Rust getter')
    found = rows(rust_symbols, '_end')
    _fail(len(found) == 1 and found[0][-2] == 'U', 'M14 text-end Rust linker-address consumer')
    found = rows(image_symbols, '_end')
    _fail(len(found) == 1 and found[0][-2].upper() != 'U',
          'M14 final linker _end must be defined; no type/width assumption')



def _validate_m14_textmap_contract(build, tools, env, timeout, command_rows, objects):
    out = build / 'm14-production'
    texts = []
    for path, label in ((Path(objects['arch/x86_64/kernel/memory.c']['path']), 'default-memory-textmap-ownership'),
                        (build/'kernel/rust/mckernel_rust.o', 'Rust-textmap-ownership'),
                        (build/'kernel/mckernel.img', 'image-textmap-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'], '-S', '-g', str(path)],
                                 label, out, tools, env, timeout, command_rows))
    _m14_check_textmap_symbols(*texts)
    return dict(getter='x86_init_text_map_kernel_start_bridge', C_getter_excluded=True,
                geometry='x86_map_kernel_start_geometry', immutable_geometry_bytes=8,
                text_end_getter='x86_init_text_end_bridge', Rust_end_import=True, final_end_defined=True,
                native=False)


# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _m14_check_set_timer_symbols(process_symbols, rust_symbols, image_symbols):
    def rows(text, symbol):
        return [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
    def unique(text, symbol, kind, size=None):
        found = rows(text, symbol)
        _fail(len(found) == 1 and found[0][-2] == kind, 'M14 set_timer provider type/count: '+symbol)
        if size is not None:
            _fail(len(found[0]) == 4 and int(found[0][1], 16) == size, 'M14 set_timer provider width: '+symbol)
    _fail(not any(row[-2] in ('T','t') for row in rows(process_symbols, 'set_timer')),
          'M14 original C set_timer body selected')
    _fail(not any(row[-2] in ('T','t') for row in rows(process_symbols, 'spin_sleep_or_schedule')),
          'M14 original C spin_sleep_or_schedule body selected')
    for symbol in ('spin_sleep_or_schedule','sched_spin_sleep_or_schedule_body_result',
                   'set_timer','get_this_cpu_local_var','timer_set_timer_body_result','process_sched_set_timer_bridge'):
        unique(rust_symbols, symbol, 'T')
        unique(image_symbols, symbol, 'T')
    for symbol in ('spin_sleep_or_schedule', 'process_sched_runqueue_offsets'):
        _fail(not any(row[-2] == 'U' for row in rows(rust_symbols, symbol)),
              'M14 spin wrapper/descriptor unresolved in production Rust: '+symbol)
    unique(process_symbols, 'process_timer_runtime_offsets', 'R', 120)
    unique(rust_symbols, 'process_timer_runtime_offsets', 'U')
    unique(image_symbols, 'process_timer_runtime_offsets', 'R', 120)
    unique(process_symbols, 'time_sharing', 'D', 4)
    unique(rust_symbols, 'time_sharing', 'U')
    unique(image_symbols, 'time_sharing', 'D', 4)
    for symbol in M14_TIMER_CALLBACKS:
        unique(process_symbols, symbol, 'T')
        unique(rust_symbols, symbol, 'U')
        unique(image_symbols, symbol, 'T')


def _validate_m14_set_timer_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row, args = _m14_selected_row(source_root, build, 'kernel/process.c', 'MCKERNEL_RUST_PROCESS_HELPERS', tools)
    out = build/'m14-production'
    oi = args.index('-o')
    pp = _m14_observe(args[:oi]+['-E', str(source_root/'kernel/process.c')],
                      'selected-process-set-timer-preprocess', out, tools, env, timeout, command_rows)
    _fail(re.search(r'\bvoid\s+set_timer\s*\([^;{}]*\)\s*\{',pp,re.S) is None and
          re.search(r'\bvoid\s+set_timer\s*\([^;{}]*\)\s*;',pp,re.S) is not None,
          'M14 selected set_timer declaration/body exclusion')
    _fail(re.search(r'\bvoid\s+spin_sleep_or_schedule\s*\([^;{}]*\)\s*\{',pp,re.S) is None and
          re.search(r'\bvoid\s+spin_sleep_or_schedule\s*\([^;{}]*\)\s*;',pp,re.S) is not None,
          'M14 selected spin_sleep_or_schedule declaration/body exclusion')
    fields = ('thread_status_offset','thread_sched_list_offset','thread_spin_sleep_lock_offset',
              'thread_spin_sleep_offset','thread_itimer_enabled_offset','cpu_runq_lock_offset',
              'cpu_runq_offset','cpu_runq_len_offset','cpu_current_offset','cpu_timer_enabled_offset',
              'cpu_backlog_list_offset','timer_timeout_offset','timer_waitq_offset','timer_list_offset','timer_thread_offset')
    witness = ['_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8,"timer LP64");',
               '_Static_assert(sizeof(struct timer_runtime_offsets)==120 && _Alignof(struct timer_runtime_offsets)==8,"timer descriptor ABI");',
               '_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void(*)(int)),"set_timer ABI");']
    for index, field in enumerate(fields):
        witness.append('_Static_assert(__builtin_offsetof(struct timer_runtime_offsets,'+field+')=='+str(index*8)+',"timer field layout");')
        witness.append('_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets*)0)->'+field+'),unsigned long),"timer field type");')
    for name, prototype in (('process_timer_spin_lock_bridge','unsigned long(*)(unsigned long)'),
                            ('process_timer_spin_unlock_bridge','void(*)(unsigned long,unsigned long)'),
                            ('process_timer_lapic_enable_bridge','void(*)(unsigned int)'),
                            ('process_timer_lapic_disable_bridge','void(*)(void)')):
        witness.append('_Static_assert(__builtin_types_compatible_p(__typeof__(&'+name+'),'+prototype+'),"timer callback ABI");')
    abi_source=out/'actual-process-set-timer-ABI.c'
    abi_source.write_text((source_root/'kernel/process.c').read_text()+'\n'+'\n'.join(witness)+'\n')
    selected=args.copy();selected[oi+1]=str(out/'actual-process-set-timer-ABI.o');selected[-1]=str(abi_source)
    phase=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
               phase='m14-selected-complete-process-TU-timer-ABI',argv=selected,cwd=row['directory'],exit_code=None)
    command_rows.append(phase)
    phase['exit_code']=_run_process(selected,Path(row['directory']),env,out/'process-timer-ABI.stdout',out/'process-timer-ABI.stderr',timeout,phase['phase'])
    _fail(phase['exit_code']==0,'M14 actual whole process.c timer ABI witness compile')
    texts=[]
    for path,label in ((Path(objects['kernel/process.c']['path']),'default-process-timer-ownership'),
                       (build/'kernel/rust/mckernel_rust.o','Rust-timer-ownership'),
                       (build/'kernel/mckernel.img','image-timer-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    _m14_check_set_timer_symbols(*texts)
    return dict(provider='set_timer',C_body_excluded=True,C_import_required=False,
                descriptor_bytes=120,descriptor_align=8,fields=fields,callbacks=M14_TIMER_CALLBACKS,
                time_sharing_bytes=4,actual_whole_process_ABI_compile=phase,native=False)


# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _validate_m14_migration_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row,args=_m14_selected_row(source_root,build,'kernel/process.c','MCKERNEL_RUST_PROCESS_HELPERS',tools)
    out=build/'m14-production';oi=args.index('-o')
    pp=_m14_observe(args[:oi]+['-E',str(source_root/'kernel/process.c')],
                     'selected-process-migration-preprocess',out,tools,env,timeout,command_rows)
    getter='sched_request_migrate';log='process_sched_migrate_log_bridge';descriptor='process_sched_migrate_debug'
    for name in (getter,log):
        _fail(re.search(r'\bvoid\s+'+name+r'\s*\([^;{}]*\)\s*\{',pp,re.S) is None,
              'M14 selected original C migration implementation: '+name)
    _fail(re.search(r'\bvoid\s+'+getter+r'\s*\([^;{}]*\)\s*;',pp,re.S) is not None,
          'M14 migration public declaration missing')
    texts=[]
    process_object=Path(objects['kernel/process.c']['path'])
    for path,label in ((process_object,'default-process-migration-ownership'),
                       (build/'kernel/rust/mckernel_rust.o','Rust-migration-ownership'),
                       (build/'kernel/mckernel.img','image-migration-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    def rows(text,name):
        return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    for name in (getter,log):
        _fail(not any(r[-2] in ('T','t') for r in rows(texts[0],name)),
              'M14 original C migration body selected: '+name)
    for text in texts[1:]:
        for name in (getter,'sched_request_migrate_body_result',log):
            found=rows(text,name)
            _fail(len(found)==1 and found[0][-2]=='T','M14 unique actual Rust/final migration provider: '+name)
    found=rows(texts[1],descriptor)
    _fail(len(found)==1 and found[0][-2]=='U','M14 actual fullRust diagnostic descriptor import')
    for text in (texts[0],texts[2]):
        found=rows(text,descriptor)
        _fail(len(found)==1 and len(found[0])==4 and found[0][-2]=='D' and
              int(found[0][1],16)==32 and int(found[0][0],16)%8==0,
              'M14 unique aligned32byte diagnostic descriptor data')
    symbols=_m14_observe([tools['tools']['readelf']['path'],'-sW',str(process_object)],
                         'default-process-migration-debug-symbol',out,tools,env,timeout,command_rows)
    found=[l.split() for l in symbols.splitlines() if l.split()[-1:]==[descriptor]]
    _fail(len(found)==1 and found[0][2]=='32' and found[0][3]=='OBJECT' and
          found[0][4]=='GLOBAL' and found[0][-2].isdigit(),'M14 actual C descriptor object binding')
    section_index=int(found[0][-2])
    sections=_m14_observe([tools['tools']['readelf']['path'],'-SW',str(process_object)],
                          'default-process-migration-debug-section',out,tools,env,timeout,command_rows)
    verbose=[int(m.group(1)) for m in re.finditer(r'^\s*\[\s*(\d+)\]\s+__verbose\s+PROGBITS\b',sections,re.M)]
    _fail(verbose==[section_index],'M14 diagnostic descriptor not in original __verbose input section')
    # Exact canonical source binds file/function/line422/default0/fmtNULL;
    # this proves actual object data/type/section, never native log execution.
    return dict(getter=getter,Rust_body='sched_request_migrate_body_result',Rust_log=log,
                C_implementation_bodies_excluded=True,C_getter_import_required=False,
                C_descriptor=descriptor,descriptor_bytes=32,descriptor_alignment=8,
                C_input_section='__verbose',original_selector_source_bound=True,
                migration_numeric_layout_credit=False,native=False)



# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

M14_L4_HEADER_ABI_ASSERTIONS = '_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l4_callback),int(*const)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"exact immutable retained callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_l4_body),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"exact complete L4 Rust callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l3_callback),int(*const)(void*,unsigned long,unsigned long,unsigned long,void*)),"exact retained L3 callback ABI");\n/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual complete canonical memory.c and real headers. */\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_public_body),int(*)(void*,struct process_vm*,unsigned long,unsigned long,int,struct memobj*)),"six-input Rust entry ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_set_range_clear_bridge),int(*)(void*,void*,unsigned long,unsigned long,int,void*)),"six-input actual set-range adapter ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_clear_range),int(*)(page_table_t,struct process_vm*,void*,void*)),"public clear ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_free_range),int(*)(page_table_t,struct process_vm*,void*,void*,struct memobj*)),"public free ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual C remote-flush header ABI");\n_Static_assert(__builtin_types_compatible_p(x86_clear_remote_flush_fn_t,void(*)(void*,unsigned long*,int,int)),"actual erased Rust flush callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_top_log_bridge),void(*)(int,void*,unsigned long,unsigned long,int)),"actual Rust top-log export ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l4_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"actual C walker provider ABI");\n\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l4_callback),int(*const)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"exact immutable retained callback ABI");\n\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_l4_body),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"exact complete L4 Rust callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l3_callback),int(*const)(void*,unsigned long,unsigned long,unsigned long,void*)),"exact retained L3 callback ABI");\n\n/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l3),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L3 callback ABI");\n#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_child_walk),x86_clear_child_walk_fn_t const),"x86_clear_l3_child_walk ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"x86_clear_l3_memobj_flush ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"x86_clear_l3_rss_sub ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"x86_clear_l3_memobj_rss_sub ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"x86_clear_l3_range_log ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"x86_clear_l3_effect_log ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_use_1gb_page),const int *const),"live use1GB borrowed address ABI");\n#endif\n\n_Static_assert(PFL3_SIZE == ((pte_t)0x80),"exact C PFL3_SIZE1GB bit matches Rust");\n_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"PFL3_SIZE actual x86 ABI width");\n\n/* Additive full L2/L1 and retained L1 walker identity real-header witnesses. */\n_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l2),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L2 callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l1),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L1 callback ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"immutable L1 walker identity ABI");\n_Static_assert(PTL2_SHIFT==21 && PTL2_SIZE==(1UL<<21) && PFL2_SIZE==((pte_t)0x80),"L2 geometry");\n_Static_assert(PTL1_SHIFT==12 && PTL1_SIZE==(1UL<<12),"L1 geometry");\n'
M14_SUCCESSOR_C_CALLBACKS = {'arch/x86_64/kernel/cpu.c': ('x86_running_on_kvm_bridge', 'x86_cpuid6_bridge', 'x86_read_msr_bridge', 'x86_write_msr_bridge'), 'kernel/syscall.c': ('syscall_alloc_bridge', 'syscall_mckfd_lock_bridge', 'syscall_mckfd_unlock_bridge')}
M14_SUCCESSOR_SELECTION = (('kernel/mem.c', 'MCKERNEL_RUST_MEM_HELPERS', ('remote_flush_tlb_array_cpumask', 'mem_tlb_atomic_dec_bridge', 'mem_tlb_atomic_inc_bridge', 'mem_tlb_atomic_read_bridge', 'mem_tlb_atomic_set_bridge', 'mem_tlb_current_cpu_bridge', 'mem_tlb_flush_all_bridge', 'mem_tlb_flush_single_bridge', 'mem_tlb_get_vector_bridge', 'mem_tlb_interrupt_cpu_bridge', 'mem_tlb_noirq_lock_bridge', 'mem_tlb_noirq_unlock_bridge', 'mem_tlb_pause_bridge', 'mem_tlb_rdtsc_bridge', 'remote_flush_tlb_cpumask')), ('kernel/process.c', 'MCKERNEL_RUST_PROCESS_HELPERS', ('vm_range_insert', 'vm_range_insert_dump_bridge', 'vm_range_insert_log_bridge')), ('arch/x86_64/kernel/cpu.c', 'MCKERNEL_RUST_X86_CPU_HELPERS', ('init_pstate_and_turbo', 'x86_context_line_log_bridge', 'x86_cpu_ulong_log_bridge')), ('kernel/syscall.c', 'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS', ('syscall_signalfd_publish_bridge', 'arch_ptrace_syscall_event', 'syscall_signalfd_create_bridge')), ('arch/x86_64/kernel/syscall.c', 'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS', ('arch_ptrace', 'arch_ptrace_syscall_event')), ('arch/x86_64/kernel/memory.c', 'MCKERNEL_RUST_X86_MEMORY_PUBLIC', ('clear_range_l1', 'clear_range_l2', 'clear_range_l3')))
M14_SUCCESSOR_ABI = {'kernel/mem.c': '/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#include <kmsg.h>\n#include <kmalloc.h>\n#include <string.h>\n#include <ihk/cpu.h>\n#include <ihk/lock.h>\n#include <ihk/mm.h>\n#include <ihk/page_alloc.h>\n#include <registers.h>\n#ifdef ATTACHED_MIC\n#include <sysdeps/mic/mic/micconst.h>\n#include <sysdeps/mic/mic/micsboxdefine.h>\n#endif\n#include <cls.h>\n#include <page.h>\n#include <kref.h>\n#include <bitops.h>\n#include <cpulocal.h>\n#include <init.h>\n#include <cas.h>\n#include <rusage_private.h>\n#include <syscall.h>\n#include <profile.h>\n#include <process.h>\n#include <limits.h>\n#include <sysfs.h>\n#include <ihk/debug.h>\n#include <llist.h>\n#include <bootparam.h>\n#include <memobj.h>\n\n//#define DEBUG_PRINT_MEM\n\n#ifdef DEBUG_PRINT_MEM\n#undef DDEBUG_DEFAULT\n#define DDEBUG_DEFAULT DDEBUG_PRINT\n#endif\n\ntypedef unsigned long (*mem_rdtsc_fn_t)(void);\ntypedef int (*mem_current_cpu_fn_t)(void);\ntypedef int (*mem_get_vector_fn_t)(int type);\ntypedef void (*mem_interrupt_cpu_fn_t)(int cpu, int vector);\ntypedef void (*mem_noirq_lock_fn_t)(unsigned long lock_addr);\ntypedef void (*mem_atomic_set_fn_t)(unsigned long atomic_addr, int value);\ntypedef void (*mem_atomic_inc_fn_t)(unsigned long atomic_addr);\ntypedef int (*mem_atomic_read_fn_t)(unsigned long atomic_addr);\ntypedef void (*mem_flush_tlb_single_fn_t)(unsigned long addr);\ntypedef void (*mem_flush_tlb_all_fn_t)(void);\ntypedef void (*mem_pause_fn_t)(void);\nint mem_remote_flush_tlb_array_body_result(\n\t\tstruct process_vm *vm, unsigned long *addr, int nr_addr,\n\t\tint cpu_id, struct tlb_flush_entry *tlb_flush_vector,\n\t\tint vector_size, int vector_start, int cpu_set_bits,\n\t\tmem_rdtsc_fn_t rdtsc_fn,\n\t\tmem_current_cpu_fn_t current_cpu_fn,\n\t\tmem_get_vector_fn_t get_vector_fn,\n\t\tmem_interrupt_cpu_fn_t interrupt_cpu_fn,\n\t\tmem_noirq_lock_fn_t lock_fn,\n\t\tmem_noirq_lock_fn_t unlock_fn,\n\t\tmem_atomic_set_fn_t atomic_set_fn,\n\t\tmem_atomic_inc_fn_t atomic_inc_fn,\n\t\tmem_atomic_read_fn_t atomic_read_fn,\n\t\tmem_flush_tlb_single_fn_t flush_single_fn,\n\t\tmem_flush_tlb_all_fn_t flush_all_fn,\n\t\tmem_pause_fn_t pause_fn);\nextern const int mem_remote_tlb_geometry[3];\n_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual entry ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(mem_remote_tlb_geometry),const int[3]),"immutable C int geometry ABI");\n_Static_assert(sizeof(int)==4&&_Alignof(int)==4&&sizeof(unsigned long)==8,"actual x86_64 scalar ABI");\nconst unsigned long M14_C_TLB_LAYOUT[15]={\n sizeof(int),_Alignof(int),sizeof(unsigned long),sizeof(struct process_vm*),\n sizeof(const int[3]),_Alignof(const int[3]),sizeof(struct tlb_flush_entry),_Alignof(struct tlb_flush_entry),\n __builtin_offsetof(struct tlb_flush_entry,vm),__builtin_offsetof(struct tlb_flush_entry,addr),\n __builtin_offsetof(struct tlb_flush_entry,nr_addr),__builtin_offsetof(struct tlb_flush_entry,pending),\n __builtin_offsetof(struct tlb_flush_entry,lock),CPU_SETSIZE,sizeof(mem_rdtsc_fn_t)};\nconst int M14_C_TLB_GEOMETRY[3]={IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,CPU_SETSIZE};\nunsigned long mem_tlb_rdtsc_bridge(void);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_rdtsc_bridge),mem_rdtsc_fn_t),"mem_tlb_rdtsc_bridge ABI");\nint mem_tlb_current_cpu_bridge(void);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_current_cpu_bridge),mem_current_cpu_fn_t),"mem_tlb_current_cpu_bridge ABI");\nint mem_tlb_get_vector_bridge(int type);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_get_vector_bridge),mem_get_vector_fn_t),"mem_tlb_get_vector_bridge ABI");\nvoid mem_tlb_interrupt_cpu_bridge(int cpu, int vector);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_interrupt_cpu_bridge),mem_interrupt_cpu_fn_t),"mem_tlb_interrupt_cpu_bridge ABI");\nvoid mem_tlb_noirq_lock_bridge(unsigned long lock_addr);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_noirq_lock_bridge),mem_noirq_lock_fn_t),"mem_tlb_noirq_lock_bridge ABI");\nvoid mem_tlb_noirq_unlock_bridge(unsigned long lock_addr);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_noirq_unlock_bridge),mem_noirq_lock_fn_t),"mem_tlb_noirq_unlock_bridge ABI");\nvoid mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_set_bridge),mem_atomic_set_fn_t),"mem_tlb_atomic_set_bridge ABI");\nvoid mem_tlb_atomic_inc_bridge(unsigned long atomic_addr);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_inc_bridge),mem_atomic_inc_fn_t),"mem_tlb_atomic_inc_bridge ABI");\nint mem_tlb_atomic_read_bridge(unsigned long atomic_addr);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_read_bridge),mem_atomic_read_fn_t),"mem_tlb_atomic_read_bridge ABI");\nvoid mem_tlb_flush_single_bridge(unsigned long addr);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_flush_single_bridge),mem_flush_tlb_single_fn_t),"mem_tlb_flush_single_bridge ABI");\nvoid mem_tlb_flush_all_bridge(void);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_flush_all_bridge),mem_flush_tlb_all_fn_t),"mem_tlb_flush_all_bridge ABI");\nvoid mem_tlb_pause_bridge(void);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_pause_bridge),mem_pause_fn_t),"mem_tlb_pause_bridge ABI");\n\n/* Accepted actual13adapter provider geometry and handler completion ABI. */\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_dec_bridge),void(*)(unsigned long)),"actual handler completion callback ABI");\n_Static_assert(sizeof(ihk_atomic_t)==4 && _Alignof(ihk_atomic_t)==4 && __builtin_offsetof(ihk_atomic_t,counter)==0,"actual atomic counter ABI");\n_Static_assert(sizeof(ihk_spinlock_t)==4 && _Alignof(ihk_spinlock_t)==4 && __builtin_offsetof(ihk_spinlock_t,head_tail)==0,"actual ticketlock ABI");\n', 'kernel/process.c': '/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#include <process.h>\n#include <process_helpers.h>\nextern int vm_range_insert(struct process_vm *,struct vm_range *);\nextern void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);\nextern void vm_range_insert_dump_bridge(struct process_vm *);\ntypedef int (*entry_t)(struct process_vm *,struct vm_range *);\ntypedef void (*log_t)(int,struct process_vm *,struct vm_range *,struct vm_range *);\ntypedef void (*dump_t)(struct process_vm *);\n_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"supported LP64 ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&vm_range_insert),entry_t),"full entry signature");\n_Static_assert(__builtin_offsetof(struct vm_range,vm_rb_node)==0,"Rust container conversion leading rb_node");\n_Static_assert(sizeof(((struct process_vm *)0)->vm_range_tree)==sizeof(struct rb_root),"actual root extent");\n_Static_assert(__alignof__(struct rb_root)==__alignof__(((struct process_vm *)0)->vm_range_tree),"actual root alignment");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->start),unsigned long),"range start unsigned long");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->end),unsigned long),"range end unsigned long");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_vm_range_insert_result),int (*)(struct rb_root *,struct vm_range *,struct process_vm *,log_t,dump_t)),"existing Rust body helper ABI");\n', 'arch/x86_64/kernel/cpu.c': '/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#include <ihk/cpu.h>\n#include <registers.h>\nextern void init_pstate_and_turbo(void);\nextern int no_turbo;\nextern int x86_running_on_kvm_bridge(void);\nextern void x86_cpuid6_bridge(unsigned long *, unsigned long *);\nextern unsigned long x86_read_msr_bridge(int);\nextern void x86_write_msr_bridge(int,unsigned long);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&init_pstate_and_turbo),void(*)(void)),"public complete entry ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(no_turbo),int),"existing boot data ABI");\n_Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8,"LP64 scalar ABI");\n_Static_assert(MSR_PLATFORM_INFO==0xce&&MSR_NHM_TURBO_RATIO_LIMIT==0x1ad&&MSR_IA32_PERF_CTL==0x199&&MSR_IA32_ENERGY_PERF_BIAS==0x1b0,"actual MSR constants");\n', 'kernel/syscall.c': '/* Functional OS/Rust migration only; no security testing.\n * Compile later with the exact supported kernel/syscall.c include/config profile.\n * This is the independent real-header witness, separate from host C fixture views.\n */\n#include <process.h>\n#define OFF(T,F) __builtin_offsetof(T,F)\n_Static_assert(sizeof(long)==8 && sizeof(unsigned long)==8, "mask word ABI");\n_Static_assert(sizeof(struct mckfd)==80, "mckfd size");\n_Static_assert(OFF(struct mckfd,next)==0, "mckfd next");\n_Static_assert(OFF(struct mckfd,fd)==8, "mckfd fd");\n_Static_assert(OFF(struct mckfd,sig_no)==12, "zeroed sig_no/Rust padding");\n_Static_assert(OFF(struct mckfd,data)==16, "mckfd data");\n_Static_assert(OFF(struct process,mckfd_lock)==1284, "process lock");\n_Static_assert(OFF(struct process,mckfd)==1288, "process list head");\n_Static_assert(OFF(struct thread,proc)==4304, "thread process");\n\n_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_ptrace),long(*)(long,int,long,long)),"actual kernel caller arch_ptrace ABI");\n'}

def _validate_m14_clear_range_contract(source_root,build,tools,env,timeout,command_rows,objects):
    row,args=_m14_selected_row(source_root,build,'arch/x86_64/kernel/memory.c','MCKERNEL_RUST_X86_MEMORY_PUBLIC',tools)
    out=build/'m14-production';oi=args.index('-o')
    abi=out/'actual-clear-range-header-ABI.c'
    abi.write_text('#include '+json.dumps(str(source_root/'arch/x86_64/kernel/memory.c'))+'\n'+M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS+M14_L4_HEADER_ABI_ASSERTIONS)
    _m14_observe(args[:oi]+['-fsyntax-only',str(abi)],'selected-clear-range-real-header-ABI',out,tools,env,timeout,command_rows)
    paths=(Path(objects['arch/x86_64/kernel/memory.c']['path']),Path(objects['kernel/mem.c']['path']),
           build/'kernel/rust/mckernel_rust.o',build/'kernel/mckernel.img')
    texts=[]
    for path,label in zip(paths,('default-memory-clear-range-ownership','default-mem-remote-flush-ownership',
                                'Rust-clear-range-ownership','image-clear-range-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    def unique(text,name,kind):
        found=rows(text,name)
        _fail(len(found)==1 and found[0][-2]==kind,'M14 clear-range provider/import: '+name)
    unique(texts[0],'x86_clear_range_public_body','U')
    for name in ('ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_public_body','x86_clear_range_top_log_bridge'):
        _fail(not any(r[-2] in ('T','t') for r in rows(texts[0],name)),'M14 old clear/free C body selected')
        unique(texts[2],name,'T');unique(texts[3],name,'T')
    for name,index in (('remote_flush_tlb_array_cpumask',1),('x86_clear_range_walk_l4_bridge',0)):
        _fail(not any(r[-2] in ('T','t') for r in rows(texts[index],name)),'M14 retired C provider body selected: '+name)
        unique(texts[2],name,'T');unique(texts[3],name,'T')
    return dict(Rust_providers=('ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_public_body'),
                actual_C_memory_import='x86_clear_range_public_body',clear_free_C_imports_required=False,
                actual_C_providers=(),retired_C_provider_bodies=('remote_flush_tlb_array_cpumask','x86_clear_range_walk_l4_bridge'),
                Rust_top_logger='x86_clear_range_top_log_bridge',C_logger_import_required=False,
                real_header_logger_ABI_in_existing_eight_assertions=True,
                real_header_ABI_assertions=11,lower_C_callback_chain_remains_computeC_debt=True,native=False)


# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _m14_l4_callback_object(path):
    """Accepted section/RELA observer semantics; resolve compiler-selected indices."""
    import struct
    raw=Path(path).read_bytes()
    eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _fail(eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64,'M14 L4 ELF64 relocatable object')
    sections=[dict(zip(('name_off','type','flags','addr','offset','size','link','info','align','entsize'),struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64))) for i in range(eh[12])]
    def payload(sec):return raw[sec['offset']:sec['offset']+sec['size']]
    def string(tab,off):return tab[off:tab.index(b'\0',off)].decode()
    names=payload(sections[eh[13]])
    for i,sec in enumerate(sections):sec.update(index=i,name=string(names,sec['name_off']))
    tables=[s for s in sections if s['type']==2]
    _fail(len(tables)==1 and tables[0]['entsize']==24,'M14 L4 actual symbol table')
    table=tables[0];strings=payload(sections[table['link']]);symbols=[]
    for i in range(table['size']//24):
        name,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',raw,table['offset']+i*24)
        symbols.append(dict(index=i,name=string(strings,name),bind=info>>4,type=info&15,shndx=ndx,value=value,size=size))
    def symbol(name):
        found=[s for s in symbols if s['name']==name]
        _fail(len(found)==1,'M14 unique callback/helper '+name)
        return found[0]
    child=symbol('x86_clear_range_walk_l3_bridge')
    _fail(child['bind']==0 and child['type']==2 and 0<child['shndx']<len(sections),'M14 retained private L3 C child')
    proof={}
    for name in ('x86_clear_range_l4_callback','x86_clear_range_l3_callback'):
        sym=symbol(name)
        _fail(sym['bind']==1 and sym['type']==1 and sym['size']==8 and 0<sym['shndx']<len(sections),'M14 callback pointer binding/extent')
        sec=sections[sym['shndx']]
        _fail(sec['flags']&2 and not sec['flags']&4 and sec['align']>=8 and sym['value']+8<=sec['size'],'M14 allocated nonexecuting pointer section')
        relsecs=[s for s in sections if s['type']==4 and s['info']==sym['shndx']]
        _fail(len(relsecs)==1 and relsecs[0]['link']==table['index'] and relsecs[0]['entsize']==24,'M14 callback owning RELA section')
        rs=relsecs[0];found=[]
        for i in range(rs['size']//24):
            off,info,addend=struct.unpack_from('<QQq',raw,rs['offset']+i*24)
            if off==sym['value']:found.append(dict(offset=off,type=info&0xffffffff,target=symbols[info>>32],addend=addend))
        _fail(len(found)==1 and found[0]['type']==1,'M14 callback exact R_X86_64_64 pointer relocation')
        rel=found[0];target=rel['target']
        if name=='x86_clear_range_l4_callback':
            _fail(target['name']=='x86_clear_range_l4_body' and target['bind']==1 and target['shndx']==0 and rel['addend']==0,'M14 L4 pointer targets public Rust entry')
        else:
            direct=target['name']==child['name'] and target['type']==2 and rel['addend']==0
            section=target['type']==3 and target['shndx']==child['shndx'] and target['value']+rel['addend']==child['value']
            _fail(direct or section,'M14 L3 pointer targets exact retained private C child')
        proof[name]=dict(symbol=sym,section=sec,relocation_section=rs,relocation=rel)
    return dict(callbacks=proof,retained_private_C_child=child,section_indices_and_function_offsets_not_hardcoded=True,C_const_pointer_ABI_checked_separately=True,lower_C_callback_chain_remains=True)


def _m14_Rust_callback_relocations(path,targets):
    """Count only required callback relocations; keep the 1MiB observer cap."""
    import struct
    raw=Path(path).read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _fail(eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64,'M14 Rust relocation object ABI')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64) for i in range(eh[12])]
    tables=[(i,s) for i,s in enumerate(sections) if s[1]==2]
    _fail(len(tables)==1 and tables[0][1][9]==24,'M14 Rust actual symbol table')
    index,table=tables[0];strings_sec=sections[table[6]];strings=raw[strings_sec[4]:strings_sec[4]+strings_sec[5]]
    names=[]
    for i in range(table[5]//24):
        offset=struct.unpack_from('<I',raw,table[4]+i*24)[0];names.append(strings[offset:strings.index(b'\0',offset)].decode())
    counts={name:0 for name in targets}
    for sec in sections:
        if sec[1]!=4 or sec[6]!=index or not sections[sec[7]][2]&2:continue
        _fail(sec[9]==24,'M14 Rust actual RELA stride')
        for i in range(sec[5]//24):
            off,info,addend=struct.unpack_from('<QQq',raw,sec[4]+i*24);name=names[info>>32]
            if name in counts:counts[name]+=1
    _fail(all(counts.values()),'M14 actual Rust callback relocation missing')
    return counts



# Functional OS/Rust only; no security testing. Exact current accepted ownership.
M14_CURRENT_RUST_PROVIDERS = {'kernel/mem.c': ('mem_tlb_atomic_dec_bridge', 'mem_tlb_atomic_inc_bridge', 'mem_tlb_atomic_read_bridge', 'mem_tlb_atomic_set_bridge', 'mem_tlb_current_cpu_bridge', 'mem_tlb_flush_all_bridge', 'mem_tlb_flush_single_bridge', 'mem_tlb_get_vector_bridge', 'mem_tlb_interrupt_cpu_bridge', 'mem_tlb_noirq_lock_bridge', 'mem_tlb_noirq_unlock_bridge', 'mem_tlb_pause_bridge', 'mem_tlb_rdtsc_bridge', 'remote_flush_tlb_cpumask'), 'kernel/process.c': ('vm_range_insert_dump_bridge', 'vm_range_insert_log_bridge'), 'kernel/syscall.c': ('arch_ptrace_syscall_event', 'syscall_signalfd_create_bridge'), 'arch/x86_64/kernel/syscall.c': ('arch_ptrace_syscall_event',), 'arch/x86_64/kernel/cpu.c': ('x86_context_line_log_bridge', 'x86_cpu_ulong_log_bridge'), 'arch/x86_64/kernel/memory.c': ('clear_range_l1', 'clear_range_l2', 'clear_range_l3')}
M14_CURRENT_CPU_ABI_WARNINGS = b"In file included from /work/output/build/m14-production/successor-ABI-arch-x86_64-kernel-cpu-c.c:1:\n/src/arch/x86_64/kernel/cpu.c: In function 'arch_save_panic_regs':\n/src/arch/x86_64/kernel/cpu.c:3732:37: warning: taking address of packed member of 'struct x86_cpu_local_variables' may result in an unaligned pointer value [-Waddress-of-packed-member]\n 3732 |                                 x86v->panic_regs, &x86v->paniced, USER_END,\n      |                                 ~~~~^~~~~~~~~~~~\n/src/arch/x86_64/kernel/cpu.c:3732:51: warning: taking address of packed member of 'struct x86_cpu_local_variables' may result in an unaligned pointer value [-Waddress-of-packed-member]\n 3732 |                                 x86v->panic_regs, &x86v->paniced, USER_END,\n      |                                                   ^~~~~~~~~~~~~~\n/src/arch/x86_64/kernel/cpu.c:3758:48: warning: taking address of packed member of 'struct x86_cpu_local_variables' may result in an unaligned pointer value [-Waddress-of-packed-member]\n 3758 |                 sregs = (struct segment_regs *)&x86v->panic_regs[17];\n      |                                                ^~~~~~~~~~~~~~~~~~~~~\n/src/arch/x86_64/kernel/cpu.c:3787:48: warning: taking address of packed member of 'struct x86_cpu_local_variables' may result in an unaligned pointer value [-Waddress-of-packed-member]\n 3787 |                 sregs = (struct segment_regs *)&x86v->panic_regs[17];\n      |                                                ^~~~~~~~~~~~~~~~~~~~~\n"

def _m14_check_current_provider_symbols(texts, rust, image):
    def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    for relative,names in M14_CURRENT_RUST_PROVIDERS.items():
        for name in names:
            _fail(not any(r[-2] in ('T','t') for r in rows(texts[relative],name)), 'M14 retired current C provider remains: '+name)
            for text in (rust,image):
                found=rows(text,name)
                _fail(len(found)==1 and found[0][-2]=='T', 'M14 current unique Rust/final provider missing: '+name)
    return M14_CURRENT_RUST_PROVIDERS

def _m14_cpu_abi_stderr_allowed(name, raw):
    # All other sites require empty stderr. This exact warning is still retained.
    return raw==b'' or (name=='successor-real-ABI-arch-x86_64-kernel-cpu-c' and raw==M14_CURRENT_CPU_ABI_WARNINGS)

# Functional OS/Rust only; no security testing. Exact named consumer evidence.
def _m14_completion_reference_encoding(rel):
    _fail(rel['symbol']=='mem_tlb_atomic_dec_bridge' and rel['binding']==1 and rel['shndx']==0 and rel['addend']==0 and rel['allocated'], 'M14 exact completion consumer symbol/addend/section')
    if rel['type']==1:return 'R_X86_64_64_direct_64bit_provider_address'
    if rel['type']==27:return 'R_X86_64_GOT64_64bit_provider_GOT_offset'
    raise ImageBuildError('M14 unsupported completion-pointer encoding')

def _m14_allocated_provider_relocations(path, names, required_completion=False):
    import struct
    raw=Path(path).read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _fail(eh[0][:6]==b'\x7fELF\x02\x01' and eh[1:3]==(1,62) and eh[11]==64,'M14 current provider ELF64 ET_REL x86_64')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64) for i in range(eh[12])]
    def string(sec,off):
        data=raw[sec[4]:sec[4]+sec[5]]
        return data[off:data.index(b'\0',off)].decode()
    section_names=sections[eh[13]];proof=[]
    for index,sec in enumerate(sections):
        if sec[1]!=4:continue
        _fail(sec[7]<len(sections) and sec[6]<len(sections),'M14 relocation section identity')
        target=sections[sec[7]]
        if not target[2]&2:continue
        table=sections[sec[6]];_fail(sec[9]==24 and table[1]==2 and table[9]==24,'M14 current RELA/symtab stride')
        strings=sections[table[6]]
        for i in range(sec[5]//24):
            offset,info,addend=struct.unpack_from('<QQq',raw,sec[4]+i*24)
            symbol_index=info>>32;_fail(symbol_index<table[5]//24,'M14 relocation symbol index')
            name,attr,other,ndx,value,size=struct.unpack_from('<IBBHQQ',raw,table[4]+symbol_index*24)
            name=string(strings,name)
            if name not in names:continue
            _fail(offset<target[5] and attr>>4==1 and ndx==0,'M14 allocated provider reference must import exact global Rust provider')
            proof.append(dict(symbol=name,binding=attr>>4,symbol_type=attr&15,shndx=ndx,type=info&0xffffffff,addend=addend,allocated=True,relocation_section_index=index,relocation_section=string(section_names,sec[0]),target_section_index=sec[7],target_section=string(section_names,target[0]),offset=offset))
    if required_completion:
        selected=[r for r in proof if r['symbol']=='mem_tlb_atomic_dec_bridge']
        _fail(len(selected)==1,'M14 one actual handler completion-pointer reference')
        selected[0]['encoding']=_m14_completion_reference_encoding(selected[0])
    return proof


def _validate_m14_successor_contract(source_root,build,tools,env,timeout,command_rows,objects):
    out=build/'m14-production';texts={};selection=[]
    def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    def unique(text,name,kind):
        found=rows(text,name);_fail(len(found)==1 and found[0][-2]==kind,'M14 successor owner/import '+name)
        return found[0]
    for relative,macro,retired in M14_SUCCESSOR_SELECTION:
        row,args=_m14_selected_row(source_root,build,relative,macro,tools)
        obj=(Path(row['directory'])/args[args.index('-o')+1]).resolve(strict=True)
        objects[relative]=_artifact(obj,'M14 successor actual complete default C object')
        tag=relative.replace('/','-').replace('.','-');oi=args.index('-o')
        pp=_m14_observe(args[:oi]+['-E',str(source_root/relative)],'successor-selected-'+tag,out,tools,env,timeout,command_rows)
        for name in retired:_fail(re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',pp,re.S) is None,'M14 successor C implementation selected '+name)
        texts[relative]=_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(obj)],'successor-symbols-'+tag,out,tools,env,timeout,command_rows)
        assertions=M14_SUCCESSOR_ABI.get(relative)
        if assertions:
            witness=out/('successor-ABI-'+tag+'.c');witness.write_text('#include '+json.dumps(str(source_root/relative))+'\n'+assertions)
            _m14_observe(args[:oi]+['-fsyntax-only',str(witness)],'successor-real-ABI-'+tag,out,tools,env,timeout,command_rows)
        selection.append(dict(source=relative,macro=macro,excluded_C_bodies=retired))
    rust=_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(build/'kernel/rust/mckernel_rust.o')],'successor-Rust-symbols',out,tools,env,timeout,command_rows)
    image=_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(build/'kernel/mckernel.img')],'successor-image-symbols',out,tools,env,timeout,command_rows)
    callback_relocations=_m14_Rust_callback_relocations(build/'kernel/rust/mckernel_rust.o',tuple(name for names in M14_SUCCESSOR_C_CALLBACKS.values() for name in names))
    for relative,names in M14_SUCCESSOR_C_CALLBACKS.items():
        for name in names:
            unique(texts[relative],name,'T');unique(rust,name,'U');unique(image,name,'T')
    current_rust_providers=_m14_check_current_provider_symbols(texts,rust,image)
    current_allocated_references={relative:_m14_allocated_provider_relocations(Path(objects[relative]['path']),names,relative=='kernel/mem.c') for relative,names in M14_CURRENT_RUST_PROVIDERS.items()}
    geometry=unique(texts['kernel/mem.c'],'mem_remote_tlb_geometry','R')
    _fail(len(geometry)==4 and int(geometry[1],16)==12,'M14 actual three-int readonly remote geometry')
    unique(rust,'mem_remote_tlb_geometry','U');unique(image,'mem_remote_tlb_geometry','R')
    vector=rows(texts['kernel/mem.c'],'tlb_flush_vector')
    _fail(len(vector)==1 and vector[0][-2] in ('B','C'),'M14 retained ordinary C TLB vector')
    for name in ('syscall_signalfd_publish_bridge','arch_ptrace','vm_range_insert','init_pstate_and_turbo','remote_flush_tlb_array_cpumask','x86_clear_range_walk_l4_bridge','x86_clear_range_l4_body'):
        unique(rust,name,'T');unique(image,name,'T')
    unique(texts['kernel/syscall.c'],'arch_ptrace','U')
    kernel_reloc=_m14_observe([tools['tools']['readelf']['path'],'-rW',objects['kernel/syscall.c']['path']],'successor-kernel-syscall-relocations',out,tools,env,timeout,command_rows)
    _fail(any(line.split()[4:5]==['arch_ptrace'] for line in kernel_reloc.splitlines()),'M14 actual C arch_ptrace consumer relocation')
    callbacks=_m14_l4_callback_object(Path(objects['arch/x86_64/kernel/memory.c']['path']))
    for name in ('x86_clear_range_l4_callback','x86_clear_range_l3_callback'):
        found=rows(image,name);_fail(len(found)==1 and found[0][-2] in ('D','R') and int(found[0][1],16)==8,'M14 final callback global pointer extent')
    return dict(actual_default_C_selections=selection,actual_C_callbacks=M14_SUCCESSOR_C_CALLBACKS,current_Rust_providers=current_rust_providers,current_allocated_Rust_consumer_references=current_allocated_references,actual_Rust_callback_relocation_counts=callback_relocations,remote_readonly_geometry_bytes=12,retained_TLB_vector=True,L4_section_aware_pointer_proof=callbacks,signalfd_Rust_internal_no_C_import_required=True,arch_ptrace_exact_C_import_relocation=True,compute_C_callback_debt_remains=True,native=False)



def _validate_m14_source_pins(source_root):
    for relative, checksum in M14_SOURCE_PINS.items():
        _fail(_sha256(_regular(source_root / relative, 'M14 selected source')) == checksum,
              'M14 exact postimage differs: ' + relative)


def _m14_selected_row(source_root, build, relative, macro, tools):
    rows = json.loads((build / 'compile_commands.json').read_text())
    selected = [r for r in rows if r.get('file') == str(source_root / relative)]
    _fail(len(selected) == 1, 'M14 unique actual compile row: ' + relative)
    row = selected[0]
    args = list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
    _fail(args[0] == tools['tools']['cc']['path'] and '14.3.1' in tools['tools']['cc']['version'],
          'M14 pinned GCC14 actual compiler differs')
    _fail(args.count('-D' + macro) == 1 and args.count('-o') == 1 and
          args[-2:] == ['-c', str(source_root / relative)], 'M14 exact selected C flags')
    return row, args


def _m14_observe(command, name, out, tools, env, timeout, command_rows):
    stdout, stderr = out / (name + '.stdout'), out / (name + '.stderr')
    row = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
               phase='m14-' + name, argv=command, cwd=str(out), exit_code=None)
    command_rows.append(row)
    row['exit_code'] = _run_process(command, out, env, stdout, stderr, timeout,
                                    row['phase'], output_fsize=1 << 20)
    stderr_raw=stderr.read_bytes()
    _fail(row['exit_code'] == 0 and _m14_cpu_abi_stderr_allowed(name,stderr_raw), 'M14 observer failed: ' + name)
    if stderr_raw:row['stderr_qualification']='EXACT_FOUR_SOURCE_BOUND_EXISTING_GCC14_PACKED_MEMBER_WARNINGS_PRESERVED'
    row.update(stdout_sha256=_sha256(stdout), stderr_sha256=_sha256(stderr))
    return stdout.read_text()


def _validate_m14_selected_memory_TU(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    _validate_m14_source_pins(source_root)
    row, args = _m14_selected_row(source_root, build, 'arch/x86_64/kernel/memory.c',
                                'MCKERNEL_RUST_X86_MEMORY_PUBLIC', tools)
    out = build / 'm14-production'
    out.mkdir(mode=0o700)
    oi = args.index('-o')
    pp = _m14_observe(args[:oi] + ['-E', str(source_root / 'arch/x86_64/kernel/memory.c')],
                      'selected-memory-preprocess', out, tools, env, timeout, command_rows)
    for name in M14_C_RETIRED_MEMORY_BODIES + M14_MEMORY_IMPORTS:
        _fail(re.search(r'\b' + name + r'\s*\([^;{}]*\)\s*\{', pp, re.S) is None,
              'M14 original C definition selected: ' + name)
    _fail(all('extern ' in pp[max(0, match.start()-20):match.start()]
              for match in [re.search(r'\b'+name+r'\s*\(', pp) for name in M14_MEMORY_IMPORTS]
              if match is not None) and all(re.search(r'\b'+name+r'\s*\(', pp) is not None
                                          for name in M14_MEMORY_IMPORTS),
          'M14 selected external Rust declarations missing')
    selected = args.copy()
    selected[oi+1] = str(out / 'selected-memory.o')
    phase = dict(phase='m14-selected-complete-memory-TU', argv=selected,
                 cwd=row['directory'], source_sha256=M14_SOURCE_PINS['arch/x86_64/kernel/memory.c'], exit_code=None)
    command_rows.append(phase)
    phase['exit_code'] = _run_process(selected, Path(row['directory']), env, stdout, stderr,
                                      timeout, phase['phase'])
    _fail(phase['exit_code'] == 0, 'M14 selected actual memory TU failed')
    _atomic_json(evidence / 'm14-selected-memory-TU.json', dict(status='PASS_PINNED_MEMORY_TU_ONLY',
        compile=phase, object=_artifact(out/'selected-memory.o', 'selected memory object'),
        actual_default_link='PENDING', native=False))


def _validate_m14_default_link(source_root, build, tools, evidence, env, timeout, command_rows):
    _validate_m14_source_pins(source_root)
    out = build / 'm14-production'
    objects = {}
    for relative, macro, imports in (
        ('kernel/process.c', 'MCKERNEL_RUST_PROCESS_HELPERS', M14_IDLE_IMPORTS),
        ('arch/x86_64/kernel/memory.c', 'MCKERNEL_RUST_X86_MEMORY_PUBLIC', M14_MEMORY_IMPORTS)):
        row, args = _m14_selected_row(source_root, build, relative, macro, tools)
        obj = Path(row['directory']) / args[args.index('-o')+1]
        obj = obj.resolve(strict=True)
        objects[relative] = _artifact(obj, 'M14 actual default C object')
        label = 'default-process' if relative == 'kernel/process.c' else 'default-memory'
        nm = _m14_observe([tools['tools']['nm']['path'], '-u', str(obj)], label+'-imports', out,
                          tools, env, timeout, command_rows)
        reloc = _m14_observe([tools['tools']['readelf']['path'], '-rW', str(obj)], label+'-relocations', out,
                             tools, env, timeout, command_rows)
        for name in imports:
            _fail(sum(line.split()[-1:] == [name] for line in nm.splitlines()) == 1 and
                  any(name in line for line in reloc.splitlines()), 'M14 default C import/relocation: '+name)
    makefile = (build/'kernel/CMakeFiles/mckernel_rust_obj.dir/build.make').read_text()
    _fail(all('--cfg '+cfg in makefile for cfg in
              ('native_linux_irq_work_v6_12','enable_profile','enable_perf','enable_rusage')),
          'M14 full production Rust configuration differs')
    _fail('mckernel_equivalence' not in makefile, 'M14 test equivalence CPU provider selected')
    for filename, name in [('kernel/rust/mckernel_rust.o','Rust object'),('kernel/mckernel.img','final image')]:
        path = build/filename
        objects[filename] = _artifact(path, 'M14 '+name)
        text = _m14_observe([tools['tools']['nm']['path'], '-g', '--defined-only', str(path)],
                            'Rust-definitions' if filename.endswith('.o') else 'image-definitions', out,
                            tools, env, timeout, command_rows)
        for symbol in M14_RUST_EXPORTS:
            found = [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
            _fail(len(found) == 1 and found[0][-2] == 'T', 'M14 unique Rust/final owner missing: '+symbol)
    undefined = _m14_observe([tools['tools']['nm']['path'], '-u', str(build/'kernel/mckernel.img')],
                             'final-undefined', out, tools, env, timeout, command_rows)
    _fail(undefined.strip() == '', 'M14 final unresolved provider')
    # The new bridge has Rust-internal callback consumers. PUBLIC excludes both
    # its C definition and all four C caller bodies; no C import is required.
    # Exact source pin binds the reviewed four Rust callback sites even when
    # optimization resolves the local callback without an external relocation.
    rust_undefined = _m14_observe([tools['tools']['nm']['path'], '-u', str(build/'kernel/rust/mckernel_rust.o')],
                                  'Rust-undefined', out, tools, env, timeout, command_rows)
    _fail(not any(line.split()[-1:] == ['x86_init_normal_set_large_bridge'] for line in rust_undefined.splitlines()),
          'M14 bridge unresolved in full production Rust object')
    page_unmap_proof = _validate_m14_page_unmap_contract(source_root, build, tools, env, timeout, command_rows, objects)
    textmap_proof = _validate_m14_textmap_contract(build, tools, env, timeout, command_rows, objects)
    set_timer_proof = _validate_m14_set_timer_contract(source_root, build, tools, env, timeout, command_rows, objects)
    migration_proof = _validate_m14_migration_contract(source_root, build, tools, env, timeout, command_rows, objects)
    clear_range_proof = _validate_m14_clear_range_contract(source_root,build,tools,env,timeout,command_rows,objects)
    successor_proof = _validate_m14_successor_contract(source_root,build,tools,env,timeout,command_rows,objects)
    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',
        source_pins=M14_SOURCE_PINS, objects=objects, page_unmap_public_contract=page_unmap_proof, textmap_contract=textmap_proof, set_timer_contract=set_timer_proof, migration_contract=migration_proof, clear_range_contract=clear_range_proof, successor_contract=successor_proof, idle_imports=M14_IDLE_IMPORTS,
        memory_imports=M14_MEMORY_IMPORTS, unique_Rust_and_image_exports=M14_RUST_EXPORTS,
        native=False, whole_M14_area_retired=False)
    _revalidate_m14_objects(proof)
    _atomic_json(evidence/'m14-combined-default-link.json', proof)
    return proof


def _revalidate_m14_objects(proof):
    for item in proof['objects'].values():
        _fail(_artifact(Path(item['path']), 'M14 final stable object') == item,
              'M14 default object changed before publication')



def _validate_owned_fork_current_sources(source_root):
    for relative, expected in OWNED_FORK_CURRENT_SOURCE_PINS.items():
        path = _regular(source_root / relative, "owned fork current prerequisite " + relative)
        _fail(_sha256(path) == expected, "owned fork current prerequisite drift " + relative)


def _run(source_root, candidate_sha, ihk_sha, manifest, toolchain, output, evidence,
        *, jobs=4, timeout=19800, container_roots=None, gitlink_manifest=None,
        native_fork_owned_transaction=False):
    _fail(isinstance(native_fork_owned_transaction, bool), "native fork opt-in must be Boolean")
    _fail(isinstance(jobs, int) and not isinstance(jobs, bool) and 1 <= jobs <= 4,
          "jobs must be between 1 and 4")
    _fail(isinstance(timeout, int) and not isinstance(timeout, bool) and 1 <= timeout <= MAX_TIMEOUT,
          "timeout is outside bound")
    source_root = _canonical(source_root, "source root")
    _validate_m14_source_pins(source_root)
    if native_fork_owned_transaction:
        _validate_owned_fork_current_sources(source_root)
    manifest = _canonical(manifest, "source manifest")
    toolchain = _canonical(toolchain, "toolchain manifest")
    output = Path(output); evidence = Path(evidence)
    _no_symlink_parents(output, "output")
    _no_symlink_parents(evidence, "evidence")
    _fail(not output.exists() and not output.is_symlink(), "output must be fresh")
    _fail(not evidence.exists() and not evidence.is_symlink(), "evidence must be fresh")
    _disjoint((source_root, output, evidence, manifest, toolchain))
    tools = _validate_toolchain(toolchain, container_roots=container_roots)
    source = _validate_source(source_root, candidate_sha, ihk_sha, manifest, tools["tools"]["git"])
    gitlink = _admit_build_gitlink(source, source_root, gitlink_manifest, manifest,
                                   candidate_sha, ihk_sha, tools["tools"]["git"])
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
                          "libraries": tools["libraries"], "versions": versions},
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
        if native_fork_owned_transaction:
            configure.append("-DENABLE_NATIVE_FORK_OWNED_TRANSACTION=ON")
        # CMake receives one cache list: the external-module probe
        # must use the retained kernel's Clang/LLD pair, while CMake's own C
        # project compilation remains independently bound to cc/GCC above.
        if tools["libraries"]:
            configure.append("-DKBUILD_MAKE_FLAGS=CC=" + tools["tools"]["clang"]["path"] +
                             ";LD=" + tools["tools"]["ld.lld"]["path"])
        for key, name in (("MAKE_PROGRAM", "make"), ("LINKER", "ld"),
                          ("AR", "ar"), ("RANLIB", "ranlib"), ("NM", "nm"),
                          ("OBJCOPY", "objcopy"), ("READELF", "readelf")):
            configure.append("-DCMAKE_" + key + "=" + tools["tools"][name]["path"])
        configure.append("-DGIT_EXECUTABLE=" + tools["tools"]["git"]["path"])
        build_command = [tools["tools"]["cmake"]["path"], "--build", str(build),
                         "--target", "mckernel.img", "-j" + str(jobs)]
        rust_object_command = [tools["tools"]["cmake"]["path"], "--build", str(build),
                               "--target", "mckernel_rust_obj", "-j" + str(jobs)]
        for phase, command in (("configure", configure), ("production-rust-object", rust_object_command), ("build", build_command)):
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
            if phase == "production-rust-object":
                progress["phase"] = "production-rust-core-panic-reference-check"
                _atomic_json(evidence / "progress.json", progress)
                production_rust_proof = _validate_production_rust_panic_refs(build, tools, evidence, env, timeout, command_rows)
            if phase == "configure":
                progress["phase"] = "modules-end-probe"
                _atomic_json(evidence / "progress.json", progress)
                _validate_modules_end_probe(build, tools, evidence)
                _validate_reset_production_abi(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)
                _validate_release_fp_regs_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)
                _validate_release_tid_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)
                _validate_clone_affinity_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)
                _validate_m14_selected_memory_TU(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)
        progress["phase"] = "artifact-validation"
        _check_signal()
        _atomic_json(evidence / "progress.json", progress)
        artifacts, link_snapshot = _validate_image(build, tools, evidence,
            native_fork_owned_transaction=native_fork_owned_transaction, source_root=source_root)
        m14_proof = _validate_m14_default_link(source_root, build, tools, evidence, env, timeout, command_rows)
        source_after = _validate_source(source_root, candidate_sha, ihk_sha, manifest,
                                        tools["tools"]["git"])
        if gitlink_manifest is not None:
            _validate_gitlink_closure(source_root, gitlink_manifest, manifest,
                                      candidate_sha, ihk_sha, tools["tools"]["git"])
        _fail(source_after["repository_files"] == source["repository_files"],
              "source changed during build")
        _fail(source_after["manifest_sha256"] == source["manifest_sha256"],
              "source manifest changed during build")
        tools_after = _validate_toolchain(toolchain, container_roots=container_roots)
        _fail(tools_after["manifest_sha256"] == tools["manifest_sha256"],
              "toolchain manifest changed during build")
        copied = {}
        for name, item in artifacts.items():
            relative = {"mckernel.img": "mckernel.img", "mckernel.img.map": "mckernel.img.map",
                        "CMakeCache.txt": "CMakeCache.txt", "compile_commands.json": "compile_commands.json",
                        "mckernel_rust.o": "mckernel_rust.o", "build.make": "build.make",
                        "mcexec": "mcexec", "mcexec_helpers.o": "mcexec_helpers.o",
                        "mcexec-rust-build.make": "mcexec-rust-build.make"}[name]
            copied[name] = _copy_evidence(Path(item["path"]), evidence / "artifacts" / relative, item)
        _check_signal()
        progress["phase"] = "complete"
        progress["status"] = "PASS"
        _atomic_json(evidence / "progress.json", progress)
        _fail(production_rust_proof['object']['sha256']==artifacts['mckernel_rust.o']['sha256'],
              'final image Rust object differs from prelink panic-reference proof')
        result = {"m14_combined_production_linkage":m14_proof, "production_rust_core_panic_reference_proof":production_rust_proof,
                  "status": "PASS", "phase": "complete", "candidate_sha": candidate_sha,
                  "ihk_sha": ihk_sha, "source_manifest_sha256": source["manifest_sha256"],
                  "toolchain_manifest_sha256": tools["manifest_sha256"],
                  "commands": command_rows, "artifacts": artifacts,
                  "proof_scope": {**PROOF_SCOPE, "image_text_symbols": list(EXPECTED_SYMBOLS),
                                  "object_text_symbols": list(EXPECTED_SYMBOLS[:5]),
                                  "compile_database_exclusions": list(FORBIDDEN_C_SOURCES)},
                  "native_fork_owned_transaction": native_fork_owned_transaction,
                  "evidence_artifacts": copied, "output_root": str(output),
                  "evidence_root": str(evidence)}
        if source.get('source_derivative_sha256') is not None:
            result['candidate_identity_scope'] = 'base_git_commit_only'
            result['source_derivative_sha256'] = source['source_derivative_sha256']
            result['materialization_sha256'] = source['materialization_sha256']
        if gitlink is not None:
            result["gitlink_manifest_sha256"] = _sha256(gitlink_manifest)
    except BaseException as exc:
        if gitlink_manifest is not None:
            try:
                _validate_gitlink_closure(source_root, gitlink_manifest, manifest,
                                          candidate_sha, ihk_sha, tools["tools"]["git"])
            except BaseException as closure_exc:
                exc = ImageBuildError(str(exc) + "; gitlink closure revalidation failed: " + str(closure_exc))
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
        if result["status"] == "PASS":
            # Publication is the last boundary: inventory and all source/tool
            # checks and artifact copies must precede this immutable recheck.
            _revalidate_link_contract_snapshots(build, evidence, link_snapshot)
            _revalidate_m14_objects(m14_proof)
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


def _validate_reset_production_abi(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    """Before image make: actual configured GCC14 flags and actual selected headers."""
    rows = json.loads((build / 'compile_commands.json').read_text())
    proofs = {
        'arch/x86_64/kernel/cpu.c': r'''
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
#error production Rust CPU helper selection missing
#endif
#ifndef MCKERNEL_NATIVE_SIGNAL_STACK
#error production native signal selection missing
#endif
_Static_assert(sizeof(struct i387_fxsave_struct) == 512, "FXSAVE size");
_Static_assert(_Alignof(struct i387_fxsave_struct) == 16, "FXSAVE alignment");
_Static_assert(__builtin_offsetof(struct i387_fxsave_struct, mxcsr_mask) == 28, "FXSAVE mask offset");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rust_x86_restore_fp_regs), void (*)(struct thread *, int, int, const void *, uint64_t, int)), "restore prototype");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rust_x86_clear_fp_regs), void (*)(struct thread *, int, int, const void *, uint64_t, int)), "clear prototype");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rust_x86_native_signal_mxcsr_mask), unsigned int (*)(int)), "mask prototype");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rust_x86_native_signal_reset_fp), long (*)(int, int, const void *, uint64_t, int)), "reset prototype");
''',
        'kernel/process.c': r'''
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
#error production Rust scheduler helper selection missing
#endif
_Static_assert(sizeof(struct sched_exit_debug) == 40, "SchedExitDebug size");
_Static_assert(_Alignof(struct sched_exit_debug) == 8, "SchedExitDebug alignment");
_Static_assert(__builtin_offsetof(struct sched_exit_debug, num_threads) == 0, "SchedExitDebug threads");
_Static_assert(__builtin_offsetof(struct sched_exit_debug, total_memory_usage) == 8, "SchedExitDebug memory");
_Static_assert(__builtin_offsetof(struct sched_exit_debug, memory_stat_rss) == 16, "SchedExitDebug rss");
_Static_assert(__builtin_offsetof(struct sched_exit_debug, memory_stat_mapped_file) == 24, "SchedExitDebug mapped");
_Static_assert(__builtin_offsetof(struct sched_exit_debug, page_sizes) == 32, "SchedExitDebug pages");
_Static_assert(__builtin_offsetof(struct thread, ptrace_debugreg) == 5016, "Thread debug pointer offset");
_Static_assert(sizeof(struct thread) == 5568, "Thread size");
_Static_assert(_Alignof(struct thread) == 64, "Thread alignment");
_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_schedule_debug_handoff), void (*)(struct thread *, struct thread *)), "debug handoff prototype");

'''}
    proofs['kernel/process.c'] += M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS
    proofs['kernel/process.c'] += M14_MIGRATION_HEADER_ABI_ASSERTIONS
    abi_rows = []
    for relative, assertions in proofs.items():
        original = source_root / relative
        selected = [row for row in rows if Path(row['file']).resolve() == original.resolve()]
        _fail(len(selected) == 1, 'production ABI compile row count: ' + relative)
        row = selected[0]
        args = list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
        _fail(args[0] == tools['tools']['cc']['path'], 'production ABI compiler differs')
        _fail('14.3.1' in tools['tools']['cc']['version'], 'production ABI requires pinned GCC14')
        fixture = build / ('production-abi-' + original.stem + '.c')
        fixture.write_bytes(original.read_bytes() + assertions.encode()) if relative == 'kernel/process.c' else fixture.write_text('#include ' + json.dumps(str(original)) + '\n' + assertions)
        command = [args[0]]
        skip = False
        for token in args[1:]:
            if skip:
                skip = False
                continue
            if token in ('-o', '-MF', '-MT', '-MQ'):
                skip = True
                continue
            if token in ('-c', '-MD', '-MMD', '-MP') or token == str(original):
                continue
            command.append(token)
        command += ['-fsyntax-only', str(fixture)]
        phase = 'production-abi-' + original.stem
        evidence_row = {'phase': phase, 'argv': command, 'cwd': row['directory'],
                        'fixture_sha256': _sha256(fixture), 'source_sha256': _sha256(original),
                        'exit_code': None}
        command_rows.append(evidence_row)
        evidence_row['exit_code'] = _run_process(command, Path(row['directory']), env, stdout, stderr, timeout, phase)
        abi_rows.append(evidence_row)
        _atomic_json(evidence / 'production-abi-checks.json', {'status': 'PENDING' if len(abi_rows) != 2 else 'PASS' if evidence_row['exit_code'] == 0 else 'FAIL', 'checks': abi_rows})
        _fail(evidence_row['exit_code'] == 0, phase + ' failed')

RELEASE_FP_REGS_C_ABI_ASSERTIONS = '#include <process.h>\n#include <ihk/mm.h>\n#include <ihk/debug.h>\n_Static_assert(__builtin_offsetof(struct thread, fp_regs)==4784,"Thread.fp_regs");\n_Static_assert(sizeof(((struct thread *)0)->fp_regs)==8,"FP pointer width");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&release_fp_regs),void(*)(struct thread *)),"release ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void(*)(void *,int,int,char *,int)),"free ABI");\n_Static_assert(sizeof(struct ddebug)==32 && _Alignof(struct ddebug)==8,"debug descriptor ABI");\n_Static_assert(PAGE_SIZE==4096UL && PAGE_SHIFT==12,"page geometry");\n'

def _validate_release_fp_regs_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    """Affected full-TU/full-crate checks in the existing pre-make ABI phase."""
    rows = json.loads((build / 'compile_commands.json').read_text())
    cpu = source_root / 'arch/x86_64/kernel/cpu.c'
    selected = [r for r in rows if Path(r['file']).resolve() == cpu.resolve()]
    _fail(len(selected) == 1, 'release CPU compile row count')
    row = selected[0]
    args = list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
    _fail(args[0] == tools['tools']['cc']['path'] and '14.3.1' in tools['tools']['cc']['version'], 'release pinned GCC14')
    _fail(args.count('-DMCKERNEL_RUST_X86_CPU_HELPERS') == 1, 'release selected default CPU flag')
    out = build / 'release-fp-regs-production'
    out.mkdir(mode=0o700)
    header = out / 'production-c-abi-assertions.h'
    header.write_text(RELEASE_FP_REGS_C_ABI_ASSERTIONS)
    common = [args[0]]
    skip = False
    for token in args[1:]:
        if skip:
            skip = False
            continue
        if token in ('-o', '-MF', '-MT', '-MQ'):
            skip = True
            continue
        if token in ('-c', '-MD', '-MMD', '-MP') or token == str(cpu):
            continue
        common.append(token)
    commands = []
    for mode in ('selected', 'fallback'):
        command = list(common)
        if mode == 'fallback':
            command.remove('-DMCKERNEL_RUST_X86_CPU_HELPERS')
        command += ['-include', str(header), '-c', str(cpu), '-o', str(out / (mode + '-cpu.o'))]
        commands.append(('release-full-cpu-' + mode, command, Path(row['directory'])))
    makefile = build / 'kernel/CMakeFiles/mckernel_rust_obj.dir/build.make'
    candidates = []
    for line in makefile.read_text().splitlines():
        if '/nightly/bin/rustc ' not in line:
            continue
        tokens = shlex.split(line)
        _fail(tokens[:3] == ['cd', str(build / 'kernel'), '&&'], 'release Rust make cwd')
        command = tokens[3:]
        _fail(command[:3] == [tools['tools']['cmake']['path'], '-E', 'env'], 'release Rust env prefix')
        _fail(command.count('/nightly/bin/rustc') == 1 and command[-1] == str(source_root / 'kernel/rust/lib.rs'), 'release real full crate')
        _fail(sum(t.startswith('--emit=obj=') for t in command) == 1, 'release Rust emit count')
        candidates.append(command)
    _fail(len(candidates) == 1, 'release Rust make command count')
    native = candidates[0]
    _fail(native.count('native_linux_irq_work_v6_12') == 1, 'release native crate cfg')
    for mode in ('native', 'legacy'):
        command = [('--emit=obj=' + str(out / (mode + '-mckernel_rust.o'))) if t.startswith('--emit=obj=') else t for t in native]
        if mode == 'legacy':
            index = command.index('native_linux_irq_work_v6_12')
            _fail(index > 0 and command[index - 1] == '--cfg', 'release legacy cfg pair')
            del command[index - 1:index + 1]
        commands.append(('release-full-crate-' + mode, command, build / 'kernel'))
    proof = []
    for phase, command, cwd in commands:
        evidence_row = {'phase': phase, 'argv': command, 'cwd': str(cwd), 'exit_code': None,
                        'cpu_source_sha256': _sha256(cpu), 'assertion_header_sha256': _sha256(header),
                        'generated_rust_make_sha256': _sha256(makefile)}
        command_rows.append(evidence_row)
        evidence_row['exit_code'] = _run_process(command, cwd, env, stdout, stderr, timeout, phase)
        proof.append(evidence_row)
        _atomic_json(evidence / 'release-fp-regs-production-checks.json', {'status': 'PENDING', 'checks': proof})
        _fail(evidence_row['exit_code'] == 0, phase + ' failed')
    # Exact exports and descriptor size are checked on complete prebuild objects.
    for name, defined in [('selected-cpu.o', False), ('fallback-cpu.o', True), ('native-mckernel_rust.o', True), ('legacy-mckernel_rust.o', True)]:
        path = out / name
        nmout = out / (name + '.nm')
        nmerr = out / (name + '.nm.stderr')
        command = [tools['tools']['nm']['path'], '-S', '--defined-only', str(path)]
        code = _run_process(command, out, env, nmout, nmerr, timeout, 'release-export-' + name, output_fsize=1048576)
        _fail(code == 0 and nmerr.stat().st_size == 0 and nmout.stat().st_size < 1048576, 'release export observer ' + name)
        symbols = [line.split() for line in nmout.read_text().splitlines()]
        exports = [v for v in symbols if len(v) >= 4 and v[-1] == 'release_fp_regs' and v[-2] == 'T']
        _fail(len(exports) == int(defined), 'release export count ' + name)
        if 'mckernel_rust' in name:
            descriptor = [v for v in symbols if len(v) >= 4 and 'RELEASE_FP_REGS_DEBUG' in v[-1]]
            _fail(len(descriptor) == 1 and int(descriptor[0][-3], 16) == 32, 'release real Rust descriptor size ' + name)
        proof.append({'phase': 'release-export-' + name, 'argv': command, 'exit_code': code,
                      'object_sha256': _sha256(path), 'stdout_sha256': _sha256(nmout), 'stderr_bytes': nmerr.stat().st_size})
    _atomic_json(evidence / 'release-fp-regs-production-checks.json', {'status': 'PASS', 'checks': proof,
                 'default_link': 'PENDING_IMAGE_MAKE', 'descriptor_relocations_and_release_body': 'PENDING_POSTBUILD'})


FUTURE_CALLBACK_SYMBOLS = ['process_release_hash_detach_bridge', 'process_release_sibling_detach_bridge', 'process_current_resource_set_bridge', 'process_release_final_cleanup_bridge']
FUTURE_ABI_ASSERTION_COUNT = 110
RELEASE_TID_PROCESS_ASSERTIONS = '_Static_assert(sizeof(struct thread)==5568,"Thread.size");\n_Static_assert(_Alignof(struct thread)==64,"Thread.align");\n_Static_assert(__builtin_offsetof(struct thread,hash_list)==0,"Thread.hash_list");\n_Static_assert(__builtin_offsetof(struct thread,tid)==20,"Thread.tid");\n_Static_assert(__builtin_offsetof(struct thread,proc)==4304,"Thread.proc");\n_Static_assert(__builtin_offsetof(struct thread,system_tsc)==5040,"Thread.system_tsc");\n_Static_assert(__builtin_offsetof(struct thread,user_tsc)==5048,"Thread.user_tsc");\n_Static_assert(sizeof(struct process)==1728,"Process.size");\n_Static_assert(_Alignof(struct process)==64,"Process.align");\n_Static_assert(__builtin_offsetof(struct process,update_lock)==64,"Process.update_lock");\n_Static_assert(__builtin_offsetof(struct process,tids)==256,"Process.tids");\n_Static_assert(__builtin_offsetof(struct process,nr_tids)==264,"Process.nr_tids");\n_Static_assert(__builtin_offsetof(struct process,stime)==1296,"Process.stime");\n_Static_assert(__builtin_offsetof(struct process,utime)==1312,"Process.utime");\n_Static_assert(sizeof(struct cpu_local_var)==8128,"CPU.size");\n_Static_assert(_Alignof(struct cpu_local_var)==64,"CPU.align");\n_Static_assert(__builtin_offsetof(struct cpu_local_var,resource_set)==7912,"CPU.resource_set");\n_Static_assert(sizeof(struct resource_set)==384,"ResourceSet.size");\n_Static_assert(_Alignof(struct resource_set)==64,"ResourceSet.align");\n_Static_assert(__builtin_offsetof(struct resource_set,thread_hash)==32,"ResourceSet.thread_hash");\n_Static_assert(sizeof(struct thread_hash)==5888,"ThreadHash.size");\n_Static_assert(_Alignof(struct thread_hash)==64,"ThreadHash.align");\n_Static_assert(__builtin_offsetof(struct thread_hash,lock)==1216,"ThreadHash.lock");\n_Static_assert(sizeof(((struct thread_hash*)0)->lock)/sizeof(((struct thread_hash*)0)->lock[0])==73,"ThreadHash.bucket_count");\n_Static_assert(HASH_SIZE==73,"ThreadHash.hash_size");\n_Static_assert(sizeof(((struct thread_hash*)0)->lock[0])==64,"ThreadHash.bucket_size");\n_Static_assert(_Alignof(__typeof__(((struct thread_hash*)0)->lock[0]))==64,"ThreadHash.bucket_align");\n_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64,"McsNode.size");\n_Static_assert(_Alignof(struct mcs_rwlock_node_irqsave)==64,"McsNode.align");\n_Static_assert(__builtin_offsetof(struct mcs_rwlock_node_irqsave,irqsave)==0,"McsNode.irqsave");\n_Static_assert(sizeof(struct timespec)==16,"TimeSpec.size");\n_Static_assert(_Alignof(struct timespec)==8,"TimeSpec.align");\n_Static_assert(sizeof(struct list_head)==16,"List.size");\n_Static_assert(__builtin_offsetof(struct list_head,next)==0,"List.next");\n_Static_assert(__builtin_offsetof(struct list_head,prev)==8,"List.prev");\n_Static_assert(sizeof(struct mcexec_tid)==16,"TidEntry.size");\n_Static_assert(_Alignof(struct mcexec_tid)==8,"TidEntry.align");\n_Static_assert(__builtin_offsetof(struct mcexec_tid,thread)==8,"TidEntry.thread");\n_Static_assert(sizeof(struct ddebug)==32,"Ddebug.size");\n_Static_assert(_Alignof(struct ddebug)==8,"Ddebug.align");\n_Static_assert(_Alignof(struct list_head)==8,"List.align");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->tids),struct mcexec_tid*),"three-leaf ABI type 0");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->nr_tids),int),"three-leaf ABI type 1");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->tid),int),"three-leaf ABI type 2");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->system_tsc),unsigned long),"three-leaf ABI type 3");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->user_tsc),unsigned long),"three-leaf ABI type 4");\n_Static_assert(__builtin_types_compatible_p(__typeof__(get_this_cpu_local_var()),struct cpu_local_var*),"three-leaf ABI type 5");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct resource_set*)0)->thread_hash),struct thread_hash*),"three-leaf ABI type 6");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&__release_tid),void(*)(struct process*,struct thread*)),"three-leaf ABI type 7");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_time_account_bridge),void(*)(void*)),"three-leaf ABI type 8");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_hash_detach_bridge),void(*)(void*)),"three-leaf ABI type 9");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_release_tid_bridge),void(*)(void*,void*)),"three-leaf ABI type 10");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_mcs_writer_lock_bridge),void(*)(unsigned long,void*)),"three-leaf ABI type 11");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_mcs_writer_unlock_bridge),void(*)(unsigned long,void*)),"three-leaf ABI type 12");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&thread_hash),int(*)(int)),"three-leaf ABI type 13");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&tsc_to_ts),void(*)(unsigned long,struct timespec*)),"three-leaf ABI type 14");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&ts_add),void(*)(struct timespec*,const struct timespec*)),"three-leaf ABI type 15");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_release_tid_body_result),int(*)(void*,int,unsigned long,unsigned long,void*,int,process_tid_log_fn_t)),"three-leaf ABI type 16");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_list_is_linked_result),int(*)(const struct list_head*)),"three-leaf ABI type 17");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_list_detach_result),void(*)(struct list_head*)),"three-leaf ABI type 18");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var*)0)->resource_set),struct resource_set*),"three-leaf ABI type 19");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->hash_list),struct list_head),"three-leaf ABI type 20");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread_hash*)0)->lock[0]),mcs_rwlock_lock_t),"three-leaf ABI type 21");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->update_lock),mcs_rwlock_lock_t),"three-leaf ABI type 22");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct mcs_rwlock_node_irqsave*)0)->irqsave),unsigned long),"three-leaf ABI type 23");\n_Static_assert(__builtin_offsetof(struct mcexec_tid,tid)==0,"TidEntry.tid");\n_Static_assert(__builtin_offsetof(struct ddebug,fmt)==16,"Ddebug.fmt");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct mcexec_tid*)0)->tid),int),"four-leaf additional ABI type 0");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&__find_and_replace_tid),void(*)(struct process*,struct thread*,int)),"four-leaf additional ABI type 1");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_replace_tid_bridge),void(*)(void*,void*,int)),"four-leaf additional ABI type 2");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_replace_tid_body_result),int(*)(void*,int,unsigned long,unsigned long,unsigned long,void*,int,int,process_tid_log_fn_t)),"four-leaf additional ABI type 3");\n_Static_assert(__builtin_offsetof(struct process, hash_list) == 0, "process.hash_list");\n_Static_assert(__builtin_offsetof(struct process, parent) == 272, "process.parent");\n_Static_assert(__builtin_offsetof(struct process, children_lock) == 320, "process.children_lock");\n_Static_assert(__builtin_offsetof(struct process, siblings_list) == 384, "process.siblings_list");\n_Static_assert(__builtin_offsetof(struct process, pid) == 456, "process.pid");\n_Static_assert(__builtin_offsetof(struct resource_set, process_hash) == 24, "resource_set.process_hash");\n_Static_assert(__builtin_offsetof(struct process_hash, lock) == 1216, "process_hash.lock");\n_Static_assert(sizeof(((struct process_hash *)0)->lock[0]) == 64, "hash lock size");\n_Static_assert(sizeof(struct mcs_rwlock_node_irqsave) == 64, "writer node size");\n_Static_assert(__alignof__(struct mcs_rwlock_node_irqsave) == 64, "writer node alignment");\n_Static_assert(HASH_SIZE == 73, "hash bucket count");\n_Static_assert(__builtin_offsetof(struct cpu_local_var, resource_set) == 7912, "cpu.resource_set");\n_Static_assert(__builtin_offsetof(struct resource_set, pid1) == 320, "resource_set.pid1");\n_Static_assert(__builtin_offsetof(struct process, children_list) == 288, "process.children_list");\n_Static_assert(sizeof(((struct cpu_local_var *)0)->resource_set) == 8, "resource_set pointer size");\n_Static_assert(sizeof(((struct resource_set *)0)->pid1) == 8, "pid1 pointer size");\n_Static_assert(sizeof(struct list_head) == 16, "list head size");\n_Static_assert(__builtin_offsetof(struct list_head, next) == 0, "list next offset");\n_Static_assert(sizeof(struct mcs_rwlock_node_irqsave) == 64, "reader node size");\n_Static_assert(__alignof__(struct mcs_rwlock_node_irqsave) == 64, "reader node alignment");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_current_resource_set_bridge),void*(*)(void)),"future callback type process_current_resource_set_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_release_hash_detach_bridge),void(*)(void*,void*)),"future callback type process_release_hash_detach_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_release_sibling_detach_bridge),void(*)(void*)),"future callback type process_release_sibling_detach_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_release_final_cleanup_bridge),void(*)(void*)),"future callback type process_release_final_cleanup_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_mcs_reader_lock_bridge),void(*)(unsigned long,void*)),"future callback type process_mcs_reader_lock_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_mcs_reader_unlock_bridge),void(*)(unsigned long,void*)),"future callback type process_mcs_reader_unlock_bridge");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&hugefileobj_cleanup),void(*)(void)),"future callback type hugefileobj_cleanup");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_hash),int(*)(int)),"future callback type process_hash");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct resource_set*)0)->process_hash),struct process_hash*),"future callback member ((struct resource_set*)0)->process_hash");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct resource_set*)0)->pid1),struct process*),"future callback member ((struct resource_set*)0)->pid1");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->parent),struct process*),"future callback member ((struct process*)0)->parent");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->pid),int),"future callback member ((struct process*)0)->pid");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->siblings_list),struct list_head),"future callback member ((struct process*)0)->siblings_list");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->children_list),struct list_head),"future callback member ((struct process*)0)->children_list");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->children_lock),mcs_rwlock_lock_t),"future callback member ((struct process*)0)->children_lock");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process_hash*)0)->lock[0]),mcs_rwlock_lock_t),"future callback member ((struct process_hash*)0)->lock[0]");\n_Static_assert(sizeof(((struct process_hash*)0)->lock)/sizeof(((struct process_hash*)0)->lock[0])==73,"ProcessHash.bucket_count");\n_Static_assert(_Alignof(__typeof__(((struct process_hash*)0)->lock[0]))==64,"ProcessHash.bucket_align");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_clone_thread_base_state_body_result),int(*)(void*,const void*,unsigned long,unsigned long,unsigned long)),"affinity actual process base initializer ABI");\n'

def _validate_release_tid_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    """Affected actual process TU and already-compiled real native/legacy crates."""
    rows = json.loads((build / 'compile_commands.json').read_text())
    process = source_root / 'kernel/process.c'
    _fail(_sha256(process) == '64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044', 'actual integrated process source drift')
    _fail(_sha256(source_root / 'kernel/rust/process_helpers.rs') == '3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e', 'actual current lifecycle/Rust source drift')
    matches = [r for r in rows if Path(r['file']).resolve() == process.resolve()]
    _fail(len(matches) == 1, 'release TID actual process compile row count')
    row = matches[0]
    args = list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
    _fail(args[0] == tools['tools']['cc']['path'] and '14.3.1' in tools['tools']['cc']['version'], 'release TID pinned GCC14')
    _fail(not any('ENABLE_TOFU' in token for token in args), 'future callback ordinary noTOFU ABI configuration')
    _fail(args.count('-DMCKERNEL_RUST_PROCESS_HELPERS') == 1, 'release TID default selected process macro')
    out = build / 'release-tid-production'
    out.mkdir(mode=0o700)
    fixture = out / 'production-process.c'
    # No release prototype is injected: real source must supply the declaration
    # before its destroy bridge. Truthful source provenance remains source-root.
    fixture.write_text('#line 1 ' + json.dumps(str(process)) + chr(10) + process.read_text() +
                       chr(10) + '#line 1 "release_tid_assertions.inc"' + chr(10) + RELEASE_TID_PROCESS_ASSERTIONS)
    common = [args[0]]
    skip = False
    for token in args[1:]:
        if skip:
            skip = False
            continue
        if token in ('-o', '-MF', '-MT', '-MQ'):
            skip = True
            continue
        if token in ('-c', '-MD', '-MMD', '-MP') or token == str(process):
            continue
        common.append(token)
    proof = []
    for mode in ('selected', 'fallback'):
        command = list(common)
        if mode == 'fallback':
            command.remove('-DMCKERNEL_RUST_PROCESS_HELPERS')
        command += ['-Werror=implicit-function-declaration', '-c', str(fixture), '-o', str(out / (mode + '-process.o'))]
        phase = 'release-tid-full-process-' + mode
        row_proof = {'phase': phase, 'argv': command, 'cwd': row['directory'],
                     'source_sha256': _sha256(process), 'full_TU_fixture_sha256': _sha256(fixture),
                     'exit_code': None, 'no_injected_release_prototype': True}
        command_rows.append(row_proof)
        row_proof['exit_code'] = _run_process(command, Path(row['directory']), env, stdout, stderr, timeout, phase)
        proof.append(row_proof)
        _atomic_json(evidence / 'release-tid-production-checks.json', {'status': 'PENDING', 'checks': proof})
        _fail(row_proof['exit_code'] == 0, phase + ' failed')
    # Existing FP gate immediately before this extension produces both full crates
    # once. Do not repeat those compiler invocations or accept extracted fixtures.
    objects = [('selected-process.o', out / 'selected-process.o', False),
               ('fallback-process.o', out / 'fallback-process.o', True),
               ('native-mckernel_rust.o', build / 'release-fp-regs-production/native-mckernel_rust.o', True),
               ('legacy-mckernel_rust.o', build / 'release-fp-regs-production/legacy-mckernel_rust.o', True)]
    for name, obj, defined in objects:
        nmout = out / (name + '.nm')
        nmerr = out / (name + '.nm.stderr')
        command = [tools['tools']['nm']['path'], '-S', str(obj)]
        code = _run_process(command, out, env, nmout, nmerr, timeout, 'release-tid-export-' + name, output_fsize=1048576)
        _fail(code == 0 and nmerr.stat().st_size == 0 and nmout.stat().st_size < 1048576, 'release TID symbol capture ' + name)
        symbols = [line.split() for line in nmout.read_text().splitlines()]
        definitions = [v for v in symbols if len(v) >= 4 and v[-1] == '__release_tid' and v[-2] == 'T']
        unresolved = [v for v in symbols if len(v) >= 2 and v[-1] == '__release_tid' and v[-2] == 'U']
        _fail(len(definitions) == int(defined), 'release TID symbol definition ' + name)
        for normal_symbol in ('process_destroy_thread_time_account_bridge', 'process_destroy_thread_hash_detach_bridge'):
            normal_definitions = [v for v in symbols if len(v) >= 4 and v[-1] == normal_symbol and v[-2] == 'T']
            normal_unresolved = [v for v in symbols if len(v) >= 2 and v[-1] == normal_symbol and v[-2] == 'U']
            _fail(len(normal_definitions) == int(defined), 'normal teardown symbol definition ' + name + ':' + normal_symbol)
            _fail(len(normal_unresolved) == 0, 'normal teardown unresolved symbol ' + name + ':' + normal_symbol)
        replace_definitions = [v for v in symbols if len(v) >= 4 and v[-1] == '__find_and_replace_tid' and v[-2] == 'T']
        replace_unresolved = [v for v in symbols if len(v) >= 2 and v[-1] == '__find_and_replace_tid' and v[-2] == 'U']
        _fail(len(replace_definitions) == int(defined), 'replace TID symbol definition ' + name)
        _fail(len(replace_unresolved) == int(name == 'selected-process.o'), 'replace TID selected consumer reference ' + name)
        for callback_symbol in FUTURE_CALLBACK_SYMBOLS:
            defs=[v for v in symbols if len(v)>=4 and v[-1]==callback_symbol and v[-2]=='T']
            undefs=[v for v in symbols if len(v)>=2 and v[-1]==callback_symbol and v[-2]=='U']
            _fail(len(defs)==int(defined) and not undefs,'future callback origin '+name+':'+callback_symbol)
        release_defs=[v for v in symbols if len(v)>=4 and v[-1]=='release_process' and v[-2]=='T']
        release_undefs=[v for v in symbols if len(v)>=2 and v[-1]=='release_process' and v[-2]=='U']
        _fail(len(release_defs)==int(defined),'actual default release_process origin '+name)
        _fail(len(release_undefs)==0,'actual release_process unresolved origin '+name)
        if name == 'selected-process.o':
            _fail(len(unresolved) == 1, 'release TID actual selected destroy callback reference')
        else:
            _fail(len(unresolved) == 0, 'release TID unresolved symbol ' + name)
        if 'mckernel_rust' in name:
            descriptors = [v for v in symbols if len(v) >= 4 and 'RELEASE_TID_DEBUG' in v[-1]]
            _fail(len(descriptors) == 1 and int(descriptors[0][-3], 16) == 32, 'release TID real crate descriptor size ' + name)
            replace_descriptors = [v for v in symbols if len(v) >= 4 and 'REPLACE_TID_DEBUG' in v[-1]]
            _fail(len(replace_descriptors) == 1 and int(replace_descriptors[0][-3], 16) == 32, 'replace TID real crate descriptor size ' + name)
        proof.append({'phase': 'release-tid-export-' + name, 'argv': command, 'exit_code': code,
                      'object_sha256': _sha256(obj), 'stdout_sha256': _sha256(nmout), 'stderr_bytes': nmerr.stat().st_size})
    _atomic_json(evidence / 'release-tid-production-checks.json',
                 {'status': 'PASS', 'checks': proof, 'full_native_legacy_crates_reused': True, 'actual_C_ABI_assertions':FUTURE_ABI_ASSERTION_COUNT,'future_callback_symbols':FUTURE_CALLBACK_SYMBOLS,
                  'default_link': 'PENDING_IMAGE_MAKE', 'body_consumer_descriptor': 'PENDING_POSTBUILD', 'four_leaf_symbols': ['__release_tid', 'process_destroy_thread_time_account_bridge', 'process_destroy_thread_hash_detach_bridge', '__find_and_replace_tid']})

AFFINITY_SYMBOLS = ['sched_clone_affinity_snapshot_result','sched_clone_affinity_inherit_result','sched_setaffinity_body_result','process_clone_thread_base_state_body_result']
AFFINITY_C_ASSERTIONS = '/* Included after the ACTUAL full syscall.c TU; no local ABI declarations. */\n#ifdef MCKERNEL_RUST_SCHED_POLICY_HELPERS\n_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_clone_affinity_snapshot_result),int(*)(unsigned long,unsigned long,unsigned long,size_t,int)),"clone snapshot ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_clone_affinity_inherit_result),int(*)(unsigned long,unsigned long,size_t)),"clone inherit ABI");\n#endif\n_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_setaffinity_body_result),long(*)(int,size_t,unsigned long,unsigned long,unsigned long,unsigned long,size_t,int,const struct sched_syscall_offsets*,sched_find_thread_fn_t,sched_thread_unlock_fn_t,sched_hold_thread_fn_t,sched_release_thread_fn_t,syscall_copy_from_user_fn_t,sched_request_migrate_fn_t)),"actual setaffinity ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_clone_thread_base_state_body_result),int(*)(void*,const void*,unsigned long,unsigned long,unsigned long)),"actual base initializer ABI");\n_Static_assert(sizeof(unsigned long)==8,"native unsigned long");\n_Static_assert(sizeof(size_t)==8,"native size_t");\n_Static_assert(sizeof(cpu_set_t)==128,"native CPU mask bytes");\n_Static_assert(_Alignof(cpu_set_t)==8,"native CPU mask alignment");\n_Static_assert(sizeof(struct sched_syscall_offsets)==72,"scheduler offset aggregate size");\n_Static_assert(_Alignof(struct sched_syscall_offsets)==8,"scheduler offset aggregate align");\n'
AFFINITY_LAYOUT_CELLS = [('sizeof(cpu_set_t)', 'core::mem::size_of::<abi::CpuSet>()'), ('_Alignof(cpu_set_t)', 'core::mem::align_of::<abi::CpuSet>()'), ('sizeof(struct thread)', 'core::mem::size_of::<abi::Thread>()'), ('_Alignof(struct thread)', 'core::mem::align_of::<abi::Thread>()'), ('sizeof(struct process)', 'core::mem::size_of::<abi::Process>()'), ('_Alignof(struct process)', 'core::mem::align_of::<abi::Process>()'), ('__builtin_offsetof(struct thread,proc)', 'core::mem::offset_of!(abi::Thread,proc)'), ('__builtin_offsetof(struct thread,sched_param)', 'core::mem::offset_of!(abi::Thread,sched_param)'), ('__builtin_offsetof(struct thread,sched_policy)', 'core::mem::offset_of!(abi::Thread,sched_policy)'), ('__builtin_offsetof(struct thread,cpu_id)', 'core::mem::offset_of!(abi::Thread,cpu_id)'), ('__builtin_offsetof(struct thread,cpu_set)', 'core::mem::offset_of!(abi::Thread,cpu_set)'), ('__builtin_offsetof(struct thread,in_kernel)', 'core::mem::offset_of!(abi::Thread,in_kernel)'), ('__builtin_offsetof(struct process,pid)', 'core::mem::offset_of!(abi::Process,pid)'), ('__builtin_offsetof(struct process,ruid)', 'core::mem::offset_of!(abi::Process,ruid)'), ('__builtin_offsetof(struct process,euid)', 'core::mem::offset_of!(abi::Process,euid)'), ('__builtin_offsetof(struct process,cpu_set)', 'core::mem::offset_of!(abi::Process,cpu_set)'), ('sizeof(struct sched_syscall_offsets)', 'core::mem::size_of::<SchedSyscallOffsets>()'), ('_Alignof(struct sched_syscall_offsets)', 'core::mem::align_of::<SchedSyscallOffsets>()'), ('__builtin_offsetof(struct sched_syscall_offsets,thread_proc_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,thread_proc_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,thread_sched_param_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,thread_sched_param_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,thread_sched_policy_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,thread_sched_policy_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,thread_cpu_id_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,thread_cpu_id_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,thread_cpu_set_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,thread_cpu_set_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,proc_pid_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,proc_pid_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,proc_ruid_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,proc_ruid_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,proc_euid_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,proc_euid_offset)'), ('__builtin_offsetof(struct sched_syscall_offsets,proc_cpu_set_offset)', 'core::mem::offset_of!(SchedSyscallOffsets,proc_cpu_set_offset)')]
AFFINITY_SOURCE_PINS = {'kernel/syscall.c': '1035622a96a5441a85d60a9db15d3ac452b60266d1f8123eb807ce3849c41081', 'kernel/rust/sched_helpers.rs': 'd16200db3054d88a83752fda1383d6c101d24de4b787bd78cd42edb46ab251fc', 'kernel/rust/process_helpers.rs': '3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e', 'kernel/rust/abi.rs': 'ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e', 'kernel/rust/syscall_policy.rs': 'f1f7866c0f2ccc8e1b0024dfb632ec7359dd2a0a4bcd8e22deb957d48ef6d770'}

def _validate_clone_affinity_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    """Fresh205 source graph: actual full syscall TU, actual layouts and full crates."""
    for name, expected in AFFINITY_SOURCE_PINS.items():
        _fail(_sha256(source_root/name)==expected,'affinity actual dependency drift '+name)
    rows=json.loads((build/'compile_commands.json').read_text())
    syscall=source_root/'kernel/syscall.c'
    matches=[r for r in rows if Path(r['file']).resolve()==syscall.resolve()]
    _fail(len(matches)==1,'affinity actual syscall compile row count')
    row=matches[0];args=list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
    _fail(args[0]==tools['tools']['cc']['path'] and '14.3.1' in tools['tools']['cc']['version'],'affinity pinned actual GCC14')
    for macro in ['-DMCKERNEL_RUST_SCHED_POLICY_HELPERS','-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS']:
        _fail(args.count(macro)==1,'affinity selected production macro '+macro)
    out=build/'clone-affinity-production';out.mkdir(mode=0o700)
    ctable='\nconst unsigned long mckernel_affinity_layout[] __attribute__((used,section(".mckernel_affinity_abi")))={'+','.join(c for c,r in AFFINITY_LAYOUT_CELLS)+'};\n'
    fixture=out/'production-syscall.c'
    fixture.write_text('#line 1 '+json.dumps(str(syscall))+'\n'+syscall.read_text()+'\n#include <process_helpers.h>\n'+AFFINITY_C_ASSERTIONS+ctable)
    common=[args[0]];skip=False
    for token in args[1:]:
        if skip:skip=False;continue
        if token in ('-o','-MF','-MT','-MQ'):skip=True;continue
        if token in ('-c','-MD','-MMD','-MP') or token==str(syscall):continue
        common.append(token)
    # Preserve original syscall.c quote-include lookup for the generated full TU.
    common+=['-iquote',str(syscall.parent)]
    proof=[]
    def run_checked(phase,command,cwd,expected=None):
        rec={'phase':phase,'argv':command,'cwd':str(cwd),'exit_code':None,'syscall_source_sha256':_sha256(syscall),'generated_fixture_sha256':_sha256(fixture)}
        command_rows.append(rec);rec['exit_code']=_run_process(command,cwd,env,stdout,stderr,timeout,phase)
        proof.append(rec);_atomic_json(evidence/'clone-affinity-production-checks.json',{'status':'PENDING','checks':proof})
        _fail(rec['exit_code']==0,phase+' failed')
    for mode in ('selected','fallback'):
        command=list(common)
        if mode=='fallback':command.remove('-DMCKERNEL_RUST_SCHED_POLICY_HELPERS')
        command+=['-Werror=implicit-function-declaration','-c',str(fixture),'-o',str(out/(mode+'-syscall.o'))]
        run_checked('affinity-full-syscall-'+mode,command,Path(row['directory']))
    # A data-only layout probe imports actual abi.rs and exact production offsets struct.
    # It is additional ABI evidence, never a substitute for both actual full crates.
    sched=(source_root/'kernel/rust/sched_helpers.rs').read_text();start=sched.index('#[repr(C)]\npub struct SchedSyscallOffsets {');end=sched.index('}',start)+1
    actual_struct=sched[start:end]
    probe=out/'actual-affinity-layout.rs'
    probe.write_text('#![no_std]\n#[path='+json.dumps(str(source_root/'kernel/rust/abi.rs'))+'] mod abi;\nuse abi::SizeT;\n'+actual_struct+'\n#[no_mangle] #[used] #[link_section=".mckernel_affinity_abi"] pub static MCKERNEL_AFFINITY_LAYOUT:[u64;'+str(len(AFFINITY_LAYOUT_CELLS))+']=['+','.join('('+r+') as u64' for c,r in AFFINITY_LAYOUT_CELLS)+'];\n')
    makefile=build/'kernel/CMakeFiles/mckernel_rust_obj.dir/build.make';candidates=[]
    for line in makefile.read_text().splitlines():
        if '/nightly/bin/rustc ' not in line:continue
        tokens=shlex.split(line);_fail(tokens[:3]==['cd',str(build/'kernel'),'&&'],'affinity Rust make cwd')
        command=tokens[3:]
        _fail(command[:3]==[tools['tools']['cmake']['path'],'-E','env'] and command[-1]==str(source_root/'kernel/rust/lib.rs'),'affinity actual fullcrate command')
        candidates.append(command)
    _fail(len(candidates)==1,'affinity Rust make command count')
    rustcmd=[('--emit=obj='+str(out/'actual-rust-layout.o')) if x.startswith('--emit=obj=') else x for x in candidates[0]];rustcmd[-1]=str(probe)
    _fail(sum(x.startswith('--emit=obj=') for x in rustcmd)==1,'affinity layout emit count')
    run_checked('affinity-actual-Rust-layout',rustcmd,build/'kernel')
    layouts=[]
    for name in ['selected-syscall','fallback-syscall','actual-rust-layout']:
        path=out/(name+'.bin');command=[tools['tools']['objcopy']['path'],'--dump-section','.mckernel_affinity_abi='+str(path),str(out/(name+'.o')),'/dev/null']
        run_checked('affinity-layout-capture-'+name,command,out)
        blob=path.read_bytes();_fail(len(blob)==8*len(AFFINITY_LAYOUT_CELLS),'affinity actual layout cell count '+name);layouts.append(blob)
    _fail(layouts[0]==layouts[1]==layouts[2],'actual C/Rust affinity layout mismatch')
    objects=[('selected-syscall',out/'selected-syscall.o'),('fallback-syscall',out/'fallback-syscall.o'),('selected-process',build/'release-tid-production/selected-process.o'),('fallback-process',build/'release-tid-production/fallback-process.o'),('native-rust',build/'release-fp-regs-production/native-mckernel_rust.o'),('legacy-rust',build/'release-fp-regs-production/legacy-mckernel_rust.o')]
    for name,obj in objects:
        nmout=out/(name+'.nm');nmerr=out/(name+'.nm.stderr');command=[tools['tools']['nm']['path'],'-S',str(obj)]
        code=_run_process(command,out,env,nmout,nmerr,timeout,'affinity-exports-'+name,output_fsize=1048576)
        _fail(code==0 and nmerr.stat().st_size==0,'affinity symbol capture '+name);symbols=[x.split() for x in nmout.read_text().splitlines()]
        for symbol in AFFINITY_SYMBOLS:
            definitions=[x for x in symbols if len(x)>=4 and x[-1]==symbol and x[-2]=='T']
            unresolved=[x for x in symbols if len(x)>=2 and x[-1]==symbol and x[-2]=='U']
            if name in ('native-rust','legacy-rust'):_fail(len(definitions)==1 and not unresolved,'affinity fullcrate unique export '+name+':'+symbol)
            elif symbol in AFFINITY_SYMBOLS[:2]:_fail(not definitions and len(unresolved)==int(name=='selected-syscall'),'affinity actual Cclone selected references '+name+':'+symbol)
            elif symbol=='process_clone_thread_base_state_body_result' and name in ('selected-process','fallback-process'):_fail(not definitions and len(unresolved)==1,'affinity actual Cclone initializer reference '+name)
        proof.append({'phase':'affinity-exports-'+name,'object_sha256':_sha256(obj),'capture_sha256':_sha256(nmout),'exit_code':code})
    _atomic_json(evidence/'clone-affinity-production-checks.json',{'status':'PASS','checks':proof,'layout_cells':len(AFFINITY_LAYOUT_CELLS),'layout_bytes_sha256':hashlib.sha256(layouts[0]).hexdigest(),'actual_syscall_C_assertions_selected':10,'actual_syscall_C_assertions_fallback':8,'fresh_native_legacy_fullcrates_reused_once':True,'old_compiled_inputs_adopted':False,'symbols':AFFINITY_SYMBOLS,'linked_default_and_N3_initialCPU':'PENDING_IMAGE_AND_NATIVE'})

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
    parser.add_argument("--gitlink-manifest", type=Path)
    parser.add_argument("--native-fork-owned-transaction", action="store_true")
    args = parser.parse_args(argv)
    result = run(**vars(args))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
