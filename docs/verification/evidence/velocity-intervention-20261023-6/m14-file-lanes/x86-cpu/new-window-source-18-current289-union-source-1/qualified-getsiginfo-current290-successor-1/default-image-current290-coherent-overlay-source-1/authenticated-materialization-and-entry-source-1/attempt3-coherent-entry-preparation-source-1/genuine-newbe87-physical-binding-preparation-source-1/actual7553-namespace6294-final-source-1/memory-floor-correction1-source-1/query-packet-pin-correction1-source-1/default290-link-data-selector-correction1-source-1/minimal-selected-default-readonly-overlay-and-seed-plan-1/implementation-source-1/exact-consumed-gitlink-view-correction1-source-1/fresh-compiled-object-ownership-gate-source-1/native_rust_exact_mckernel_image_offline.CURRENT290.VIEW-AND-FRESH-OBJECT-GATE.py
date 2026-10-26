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
import resource
import shlex
import shutil
import signal
import stat
import subprocess
import time
import uuid

import native_rust_exact_build_offline as provenance


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


def _run(source_root, candidate_sha, ihk_sha, manifest, toolchain, output, evidence,
        *, jobs=4, timeout=19800, container_roots=None, gitlink_manifest=None):
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
    tools = _validate_toolchain(toolchain, container_roots=container_roots)
    source = _validate_source(source_root, candidate_sha, ihk_sha, manifest, tools["tools"]["git"])
    gitlink = (_validate_gitlink_closure(source_root, gitlink_manifest, manifest,
                                         candidate_sha, ihk_sha, tools["tools"]["git"])
               if gitlink_manifest is not None else None)
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
                     "-DCMAKE_C_COMPILER:STRING=" + tools["tools"]["cc"]["path"],
                     "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DENABLE_RUST_KERNEL=ON",
                     "-DENABLE_RUST_IHK_MODULE_HELPERS=ON", "-DENABLE_RUST_USER_TOOLS=ON",
                     "-DMCKERNEL_HOST_IRQ_ABI=linux-6.12",
                     "-DENABLE_NATIVE_FORK_OWNED_TRANSACTION:BOOL=ON",
                     "-DMCKERNEL_RUNTIME_TOOL_RUSTC:FILEPATH=" + tools["tools"]["rustc"]["path"]]
        # CMake receives one cache list: the external-module probe
        # must use the retained kernel's Clang/LLD pair, while CMake's own C
        # project compilation remains independently bound to cc/GCC above.
        if tools["libraries"]:
            configure.append("-DKBUILD_MAKE_FLAGS=CC=" + tools["tools"]["clang"]["path"] +
                             ";LD=" + tools["tools"]["ld.lld"]["path"])
        for key, name in (("MAKE_PROGRAM", "make"), ("LINKER", "ld"),
                          ("AR", "ar"), ("RANLIB", "ranlib"), ("NM", "nm"),
                          ("OBJCOPY", "objcopy"), ("READELF", "readelf")):
            configure.append("-DCMAKE_" + key + ("" if key == "MAKE_PROGRAM" else ":FILEPATH") + "=" + tools["tools"][name]["path"])
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
            if phase == "configure":
                progress["phase"] = "modules-end-probe"
                _atomic_json(evidence / "progress.json", progress)
                _validate_modules_end_probe(build, tools, evidence)
        progress["phase"] = "artifact-validation"
        _check_signal()
        _atomic_json(evidence / "progress.json", progress)
        production_panic_proof = _validate_production_rust_panic_refs(
            build, tools, evidence, env, timeout, command_rows)
        artifacts, link_snapshot = _validate_image(build, tools, evidence)
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
        result.update(production_rust_core_panic_reference_proof=production_panic_proof,
                      native_fork_owned_transaction=False,
                      operation_scope='IMAGE_BUILD_ONLY',
                      kernel_native_fork_config=True,
                      native_executor_pair_acceptance='OPEN')
        if source.get('source_derivative_sha256') is not None:
            result.update(candidate_identity_scope='base_git_commit_only',
                          source_derivative_sha256=source['source_derivative_sha256'],
                          materialization_sha256=source['materialization_sha256'])
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
    parser.add_argument("--gitlink-manifest", type=Path)
    args = parser.parse_args(argv)
    result = run(**vars(args))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


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



import shutil
import sys
import struct

_REUSE_FIXED = json.loads('{"archive": {"bytes": 8509594, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-default-link-failure-retention-1/CURRENT290-DEFAULT-FINAL-LINK-FAILURE-FULL-BUILD-AND-OWNER.tar.gz", "sha256": "eba7d942852d3fd938aaa79fea62da1412db00da06013a1a2933e3eca2627ea5"}, "base_manifest": {"bytes": 35830378, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-inputs.CURRENT290-QUALIFIED-IHK3114.json", "sha256": "3a0653623cc1cdb7ebb0e217274ded31ea8fea5068140af4884c273b493b5018"}, "base_materialization_receipt": {"bytes": 17922, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/ACTUAL-CURRENT290-SOURCE-MATERIALIZATION-AND-EXACT-SIX-READBACK.NOT-BUILD-ACCEPTANCE.json", "sha256": "e2699ae5da9b37f541aa6c27f50b8a2cdfb8a038cde44770309de617591594f9"}, "base_source_root": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source", "candidate_sha": "eb3ce544eb1f479a56933a5c7fa8300ab6dfe533", "commands": {"Rust_actual_default_command": "cd /work/output/build/kernel && /usr/bin/cmake -E env MAKEFLAGS= MCKERNEL_RUST_VERSION=1.8.0 MCKERNEL_RUST_BUILDID=3114d9e MCKERNEL_X86_ENABLE_SSE=1 MCKERNEL_CPU_C_FILE=/src/arch/x86_64/kernel/cpu.c /nightly/bin/rustc --crate-name mckernel_rust --crate-type lib --edition=2021 -C panic=abort -C opt-level=2 -C debuginfo=2 -C code-model=large -C relocation-model=static -C no-redzone=yes -C force-frame-pointers=yes -C overflow-checks=off -C force-unwind-tables=no -C no-vectorize-loops -C no-vectorize-slp -C target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma --cfg f03_io_diagnostic_callbacks_candidate --cfg f03_mincore_candidate --cfg f03_move_pages_candidate --cfg f03_sched_bridges_candidate --cfg f03_signal_process_bridges_candidate --cfg f03_dispatch_context_candidate --cfg f03_leaf_callbacks_candidate --cfg native_linux_irq_work_v6_12 --cfg f03_syscall_entry_candidate --cfg f03_futex_atomic_candidate --cfg f03_futex_no_uaccess_candidate --cfg process_global_storage_candidate --cfg f03_syscall_table_candidate --cfg f03_ptrace_entry_candidate --cfg f03_syscall_table_clone3 --cfg enable_profile --cfg enable_perf --cfg enable_rusage --emit=obj=/work/output/build/kernel/rust/mckernel_rust.o /src/kernel/rust/lib.rs", "Rust_actual_default_makefile": {"bytes": 9297, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "sha256": "51a872a778d2b3e914918fab0de573392a645f58509c25b64bcb3c1cb56fe8d5"}, "Rust_codegen_units_1_must_not_be_added": true, "Rust_flags_must_remain_exact": true, "Rust_input_view": "Actual default77rootmodules/79Rustfiles plus3existingexternalfiles+unchangedCPU-Cenv input;2Rustpostimages only; not Source27/31 test bodies/cfgs/ABI appendices.", "additional_required_proof": "Fresh actualdefault-object LOCAL metadata proof for the4Source30loggerattributes, because Source30CGU1 fixture cannot qualify this defaultCGU-absence profile.", "container_cwd": "/work/output/build/kernel", "link_actual_default": {"bytes": 759, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt", "sha256": "d9d50ed84770a8bff5af2371e19245200d99d61fe3cda28e880bd88e6669e428"}, "link_argv": ["/usr/bin/ld", "-e", "arch_start", "-T", "/work/output/build/kernel/config/smp-x86.lds", "--build-id", "-Map=/work/output/build/kernel/mckernel.img.map", "--dependency-file=CMakeFiles/mckernel.img.dir/link.d", "CMakeFiles/mckernel.img.dir/mem.c.o", "CMakeFiles/mckernel.img.dir/syscall.c.o", "CMakeFiles/mckernel.img.dir/process.c.o", "CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "rust/mckernel_rust.o", "-o", "mckernel.img"], "link_order_exact": ["CMakeFiles/mckernel.img.dir/mem.c.o", "CMakeFiles/mckernel.img.dir/syscall.c.o", "CMakeFiles/mckernel.img.dir/process.c.o", "CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "rust/mckernel_rust.o"], "new_objects": ["kernel/rust/mckernel_rust.o", "kernel/CMakeFiles/mckernel.img.dir/process.c.o"], "new_owner_execution_argv": null, "no_other_C_ASM_compile": true, "no_unchanged_SDK_or_MODULES_END_probe_compile": true, "post_link_existing_validators": ["_validate_modules_end_probe on retained exact driver.ko and current exact consumers", "_validate_production_rust_panic_refs on actual full new Rust object", "_validate_image including rawld/link.d/ELF/required native symbols/compile database", "_revalidate_inputs/source/toolchain/seed/overlay hashes and sourceview after compilation"], "process_command_authority": "Actual current290 CMake compile_commands plus exactly the CMake56e3 APPEND property, independently evaluated with real LANGUAGES NONE probes. A reuse receipt must label this explicit oneflag command derivation, never fresh full configure.", "process_command_expected_argv": ["/usr/bin/cc", "-DIHK_IKC_USE_LINUX_WORK_IRQ", "-DIHK_OS_MANYCORE", "-DKERNEL_RAM_VADDR=0xfffffffffe800000", "-DMAP_KERNEL_START=0xfffffffffe800000UL", "-DMCKERNEL_NATIVE_CLONE3", "-DMCKERNEL_NATIVE_CLONE_TID", "-DMCKERNEL_NATIVE_FAULT_FIXUP", "-DMCKERNEL_NATIVE_FUTEX", "-DMCKERNEL_NATIVE_SIGNAL_STACK", "-DMCKERNEL_RUST_ATOMIC_HELPERS", "-DMCKERNEL_RUST_BITOPS", "-DMCKERNEL_RUST_LIST_HELPERS", "-DMCKERNEL_RUST_LOCK_HELPERS", "-DMCKERNEL_RUST_MCS_RWLOCK_HELPERS", "-DMCKERNEL_RUST_MC_RWLOCK_HELPERS", "-DMCKERNEL_RUST_PTE_HELPERS", "-DMCKERNEL_RUST_REFCOUNT_HELPERS", "-DMCKERNEL_RUST_SPINLOCK_HELPERS", "-DPROFILE_ENABLE", "-D__KERNEL__", "-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE", "-DMCKERNEL_RUST_PROCESS_HELPERS", "-I/work/output/build/kernel/include", "-I/src/kernel/include", "-I/work/output/build/kernel", "-I/work/output/build", "-I/src/ihk/cokernel/smp/x86_64/include", "-I/src/ihk/cokernel/smp/x86_64", "-I/src/ihk/ikc/include", "-I/src/ihk/linux/include", "-I/src/lib/include", "-I/src/arch/x86_64/kernel/include", "-g", "-Wall", "-Wextra", "-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-unused-function", "-Wno-implicit-fallthrough", "-Wno-stringop-truncation", "-ffreestanding", "-O2", "-nostdinc", "-isystem", "/usr/lib/gcc/x86_64-redhat-linux/14/include", "-fno-omit-frame-pointer", "-mcmodel=large", "-mno-red-zone", "-mno-sse", "-o", "CMakeFiles/mckernel.img.dir/process.c.o", "-c", "/src/kernel/process.c"], "process_command_selected_original": {"command": "/usr/bin/cc -DIHK_IKC_USE_LINUX_WORK_IRQ -DIHK_OS_MANYCORE -DKERNEL_RAM_VADDR=0xfffffffffe800000 -DMAP_KERNEL_START=0xfffffffffe800000UL -DMCKERNEL_NATIVE_CLONE3 -DMCKERNEL_NATIVE_CLONE_TID -DMCKERNEL_NATIVE_FAULT_FIXUP -DMCKERNEL_NATIVE_FUTEX -DMCKERNEL_NATIVE_SIGNAL_STACK -DMCKERNEL_RUST_ATOMIC_HELPERS -DMCKERNEL_RUST_BITOPS -DMCKERNEL_RUST_LIST_HELPERS -DMCKERNEL_RUST_LOCK_HELPERS -DMCKERNEL_RUST_MCS_RWLOCK_HELPERS -DMCKERNEL_RUST_MC_RWLOCK_HELPERS -DMCKERNEL_RUST_PTE_HELPERS -DMCKERNEL_RUST_REFCOUNT_HELPERS -DMCKERNEL_RUST_SPINLOCK_HELPERS -DPROFILE_ENABLE -D__KERNEL__ -DMCKERNEL_RUST_PROCESS_HELPERS -I/work/output/build/kernel/include -I/src/kernel/include -I/work/output/build/kernel -I/work/output/build -I/src/ihk/cokernel/smp/x86_64/include -I/src/ihk/cokernel/smp/x86_64 -I/src/ihk/ikc/include -I/src/ihk/linux/include -I/src/lib/include -I/src/arch/x86_64/kernel/include -g -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -Wno-unused-function -Wno-implicit-fallthrough -Wno-stringop-truncation -ffreestanding -O2 -nostdinc -isystem /usr/lib/gcc/x86_64-redhat-linux/14/include -fno-omit-frame-pointer -mcmodel=large -mno-red-zone -mno-sse -o CMakeFiles/mckernel.img.dir/process.c.o -c /src/kernel/process.c", "directory": "/work/output/build/kernel", "file": "/src/kernel/process.c", "output": "kernel/CMakeFiles/mckernel.img.dir/process.c.o"}, "process_only_delta": "-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE exactlyonce; all other compiler/include/options/source/output tokens identical", "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.", "status": "SOURCE_ONLY_RECIPE_REQUIRES_MINIMAL_DRIVER_OWNER_EXTENSION_AND_FRESH_RELEASE"}, "configuration": [{"build_relative": "CMakeCache.txt", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/CMakeCache.txt", "source": {"bytes": 26772, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/CMakeCache.txt", "sha256": "0a76d32d26170bc88370a013dd189af7cd04a342222be2f2f0c03723dee74019"}}, {"build_relative": "compile_commands.json", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/compile_commands.json", "source": {"bytes": 74750, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/compile_commands.json", "sha256": "8355a2fa83310991bd21d3ddea7106d1e40134f2f90b4f0c5d4eb2e218869139"}}, {"build_relative": "kernel/CMakeFiles/mckernel.img.dir/build.make", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/build.make", "source": {"bytes": 30122, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/build.make", "sha256": "d038ece565cc965f11288eac31da307e56bd3c9ec40e9470f89d0756e1decb2f"}}, {"build_relative": "kernel/CMakeFiles/mckernel.img.dir/flags.make", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/flags.make", "source": {"bytes": 3993, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/flags.make", "sha256": "eb3f8f83cf8fffd7599118c70881f7203bee5e4a68894069212287ea54444b24"}}, {"build_relative": "kernel/CMakeFiles/mckernel.img.dir/link.txt", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt", "source": {"bytes": 759, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt", "sha256": "d9d50ed84770a8bff5af2371e19245200d99d61fe3cda28e880bd88e6669e428"}}, {"build_relative": "kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "source": {"bytes": 9297, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make", "sha256": "51a872a778d2b3e914918fab0de573392a645f58509c25b64bcb3c1cb56fe8d5"}}, {"build_relative": "kernel/config/smp-x86.lds", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/config/smp-x86.lds", "source": {"bytes": 915, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/config/smp-x86.lds", "sha256": "b95d62a32abad215818adbde3597fad0607d4d14dddc7fc9adea09d9cd133bbd"}}, {"build_relative": "kernel/include/swapfmt.h", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/include/swapfmt.h", "source": {"bytes": 878, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/include/swapfmt.h", "sha256": "e14e0134c80c2a4bfcda779285b57d46e01a70702eb608fb6b378ff763d90183"}}, {"build_relative": "tmp.resolve_MODULES_END/driver.ko", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/tmp.resolve_MODULES_END/driver.ko", "source": {"bytes": 151688, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/tmp.resolve_MODULES_END/driver.ko", "sha256": "0c5c6d38362e859db21c28cba14101e8bc62119d4b33f5e38820294196444ff6"}}, {"build_relative": "config.h", "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/config.h", "source": {"bytes": 1055, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/config.h", "sha256": "da78d6a8c94b274adad3159b1cc373b00e5de7fea6cc2ae7955a700078db6b2f"}}], "configuration_mode": "REUSED_CONFIGURATION_DERIVED_CURRENT_DEFAULT_COMMANDS", "fresh_full_configure": false, "fresh_materialization": false, "future_nonce": null, "future_pid": null, "ihk_sha": "3114d9e7101ad52030eb3effa849a5c108972a1f", "members": {"bytes": 829416, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-default-link-failure-retention-1/MEMBERS.json", "sha256": "f2b65f3ae91ac069f302e6e10c30e07e42957010507372c1dcf483832a71a03a"}, "objects": [{"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/mem.c.o", "link_token": "CMakeFiles/mckernel.img.dir/mem.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o", "source": {"bytes": 2848, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o", "sha256": "4b595744494abba0493d75a1475e48b3745e1a668f5575543e81797b994e4f7c"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/syscall.c.o", "link_token": "CMakeFiles/mckernel.img.dir/syscall.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o", "source": {"bytes": 397416, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o", "sha256": "4ae43c42620a929f13f6dc83d628e01bc0186bc33c1c988121bfc2a1299931d4"}}, {"action": "new selected compilation", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/process.c.o", "link_token": "CMakeFiles/mckernel.img.dir/process.c.o", "replace": true, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o", "source": {"bytes": 76536, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o", "sha256": "385b8d205d119ade76af5e36bae0a6fd893f8ca7518f45d635979a55c61d4678"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "link_token": "CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "source": {"bytes": 2880, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o", "sha256": "e139686acfa04f6d7576da5656693d13c4235e5beefb7f8ae3c9f7ccf03ea9b0"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "source": {"bytes": 2344, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o", "sha256": "dce0972b3291f970d49a5fa6d64f25c587423aafa63efc8b47bcfdbdfb679c7a"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "source": {"bytes": 2872, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o", "sha256": "3bed7de9807b6d8e70e87722a11b3d103119203822b9e022ebd0ecbc570bbce1"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "source": {"bytes": 16056, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o", "sha256": "66bcbec1fc5086cac18a8009f0e1b36ecaba7bf11f38cadd5de9f03e3873ee44"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "source": {"bytes": 2888, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o", "sha256": "d3207c7a7844086196676c82d66e6aa4f1233e37b167460e23ba089ec71aca85"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "source": {"bytes": 135464, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o", "sha256": "cea862c3d32ab3dfbc8e39d1da50b6fe324bb0ffcb88476915605ea639b832ed"}}, {"action": "reuse exact object; no C/ASM compile", "build_relative": "kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "link_token": "CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "replace": false, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "source": {"bytes": 5568, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o", "sha256": "ebd728290101289164a887deb52dc7977d896e9627a2cb1323fd649db89055c5"}}, {"action": "new selected compilation", "build_relative": "kernel/rust/mckernel_rust.o", "link_token": "rust/mckernel_rust.o", "replace": true, "retained_archive_member": "docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/rust/mckernel_rust.o", "source": {"bytes": 18045008, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build/kernel/rust/mckernel_rust.o", "sha256": "5b70e620fbdc5467757f430c8a45328364abfdcca7dfeb91ec9aa4693d7e6506"}}], "postimages": [{"base": {"bytes": 26500, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source/kernel/CMakeLists.txt", "sha256": "f54e9093abf7850e3c14afef4932b7ad9e67b92a395cf8e031b8e5366e170b7b"}, "base_mode": 384, "container_destination": "/src/kernel/CMakeLists.txt", "postimage": {"bytes": 26715, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/kernel/CMakeLists.txt", "sha256": "f29336679e462746822d5ce9efe1a74491fbea1f0cbb46d56cfdc48ae082b3cc"}, "postimage_mode": 384, "readonly": true, "relative": "kernel/CMakeLists.txt"}, {"base": {"bytes": 2094, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source/kernel/rust/lib.rs", "sha256": "ad7b9f9e66d56f4d6df1d20366ec4697c2448a5930081a944c3b7e78088790ae"}, "base_mode": 384, "container_destination": "/src/kernel/rust/lib.rs", "postimage": {"bytes": 2115, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/default290-corrected-real-crate-source-1/candidate/kernel/rust/lib.rs", "sha256": "a05908f81b3ecd37d22fa75585525b8a4c8cf8cc9c52be57ea9a86e2ec580680"}, "postimage_mode": 384, "readonly": true, "relative": "kernel/rust/lib.rs"}, {"base": {"bytes": 1227766, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source/kernel/rust/syscall_policy.rs", "sha256": "e7d533e6d27d216edfb091f51cbd7705ccde1410ed5d0b2f7efbc8fef4526308"}, "base_mode": 384, "container_destination": "/src/kernel/rust/syscall_policy.rs", "postimage": {"bytes": 1228858, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/default290-corrected-real-crate-source-1/candidate/kernel/rust/syscall_policy.rs", "sha256": "fefec3eb05be2f714dfeca34310901a566557f82ee08de9b9ad0ef0344f74d62"}, "postimage_mode": 384, "readonly": true, "relative": "kernel/rust/syscall_policy.rs"}], "retention_receipt": {"bytes": 10866, "path": "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-default-link-failure-retention-1/SOURCE-RETENTION.json", "sha256": "67489c39965ef088b497a553cb6ec99044cfd442bc1de96fe7e5be4b944a8137"}, "runtime_authority": null, "schema": "mckernel.current290.readonly-three-postimage-nine-object-reuse.v1", "seed_root": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1/actual-current290-default-image-attempt-3/owner-work/output/build"}')
_REUSE_INPUT_SHA256 = 'c9af4c64ac2b414caf7d78b9a1b467edbf17d0252554d2b4a402a49bfd75a4b8'
_REUSE_INPUT_BYTES = 41994
_REUSE_IDENTITY_BASELINE = {}

def _reuse_require(condition, message):
    if not condition:
        raise RuntimeError('readonly reuse: ' + message)

def _reuse_file(path, expected):
    path = Path(path)
    _reuse_require(not path.is_symlink() and path.is_file(), 'regular input missing: ' + str(path))
    for parent in path.parents:
        _reuse_require(not parent.is_symlink(), 'symlink input parent')
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        _reuse_require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'input identity changed at open')
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        after_fd = os.fstat(stream.fileno())
    after = path.stat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns, item.st_mode)
    _reuse_require(identity(before) == identity(opened) == identity(after_fd) == identity(after), 'input changed while hashing')
    _reuse_require(after.st_size == expected['bytes'] and digest.hexdigest() == expected['sha256'], 'input bytes/hash differs: ' + str(path))
    baseline = _REUSE_IDENTITY_BASELINE.setdefault(str(path), identity(after))
    _reuse_require(identity(after) == baseline, 'input inode/metadata changed since first authentication')
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=after.st_size, dev=after.st_dev, inode=after.st_ino)

def _reuse_layout(fixed):
    _reuse_require(fixed == _REUSE_FIXED, 'frozen input data differs')
    _reuse_require(len(fixed['postimages']) == 3 and {row['relative'] for row in fixed['postimages']} == {'kernel/CMakeLists.txt', 'kernel/rust/lib.rs', 'kernel/rust/syscall_policy.rs'}, 'three allowed postimages')
    objects = fixed['objects']
    _reuse_require(len(objects) == 11 and len({row['build_relative'] for row in objects}) == 11, '11 unique ordered objects required')
    _reuse_require(sum(not row['replace'] for row in objects) == 9, 'nine reused objects required')
    _reuse_require({row['build_relative'] for row in objects if row['replace']} == {'kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'kernel/rust/mckernel_rust.o'}, 'two replacement objects differ')
    for row in objects + fixed['configuration']:
        path = Path(row['build_relative'])
        _reuse_require(not path.is_absolute() and '..' not in path.parts, 'seed destination escapes')
        _reuse_require(Path(row['source']['path']) == Path(fixed['seed_root']) / path, 'seed original path differs')
    return fixed

def _reuse_authenticate(input_path, *, container=False):
    _reuse_file(input_path, dict(sha256=_REUSE_INPUT_SHA256, bytes=_REUSE_INPUT_BYTES))
    fixed = _reuse_layout(json.loads(Path(input_path).read_text()))
    seed = Path('/seed-build') if container else Path(fixed['seed_root'])
    aliases = {'archive': '/seed-archive.tar.gz', 'members': '/seed-members.json', 'retention_receipt': '/seed-retention.json'}
    proofs = {}
    for key, alias in aliases.items():
        proofs[key] = _reuse_file(alias if container else fixed[key]['path'], fixed[key])
    member_doc = json.loads(Path(aliases['members'] if container else fixed['members']['path']).read_text())
    rows = {row['member']: row for row in member_doc['members']}
    _reuse_require(len(rows) == len(member_doc['members']), 'duplicate retained archive member')
    for row in fixed['objects'] + fixed['configuration']:
        retained = rows.get(row['retained_archive_member'])
        _reuse_require(retained is not None and retained['kind'] == 'regular' and retained['source'] == row['source'], 'seed/archive member binding differs')
        _reuse_file(seed / row['build_relative'], row['source'])
    for row in fixed['postimages']:
        path = Path('/src') / row['relative'] if container else row['postimage']['path']
        _reuse_file(path, row['postimage'])
        _reuse_require(row['readonly'] is True and row['container_destination'] == '/src/' + row['relative'], 'postimage is not exact readonly destination')
    return proofs

def _reuse_mounts(input_path):
    fixed = _REUSE_FIXED
    mounts = [(Path(fixed['base_source_root']), '/base-src', True),
              (Path(fixed['seed_root']), '/seed-build', True),
              (Path(input_path), '/reuse-inputs.json', True)]
    for key, target in (('archive', '/seed-archive.tar.gz'), ('members', '/seed-members.json'), ('retention_receipt', '/seed-retention.json')):
        mounts.append((Path(fixed[key]['path']), target, True))
    mounts.extend((Path(row['postimage']['path']), row['container_destination'], True) for row in fixed['postimages'])
    return mounts

def _reuse_run(source_root, candidate_sha, ihk_sha, manifest, toolchain, output, evidence,
        *, jobs=4, timeout=19800, container_roots=None, gitlink_manifest=None):
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
    tools = _validate_toolchain(toolchain, container_roots=container_roots)
    source = _reuse_validate_source(source_root, candidate_sha, ihk_sha, manifest, tools["tools"]["git"])
    gitlink = (_validate_gitlink_closure(source_root, gitlink_manifest, manifest,
                                         candidate_sha, ihk_sha, tools["tools"]["git"])
               if gitlink_manifest is not None else None)
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
        _reuse_prepare_build(build, evidence)
        _validate_modules_end_probe(build, tools, evidence)
        for phase, command in _reuse_commands():
            _check_signal()
            progress['phase'] = phase
            row = dict(phase=phase, argv=command, cwd=str(build / 'kernel'),
                       env_sha256=hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest(), exit_code=None)
            command_rows.append(row)
            _atomic_json(evidence / 'progress.json', progress)
            row['exit_code'] = _run_process(command, build / 'kernel', env, stdout, stderr, timeout, phase)
            _atomic_json(evidence / 'progress.json', progress)
            _fail(row['exit_code'] == 0, phase + ' failed')
        for seed in _REUSE_FIXED['objects']:
            if not seed['replace']:
                _reuse_file(build / seed['build_relative'], seed['source'])
        _reuse_authenticate('/reuse-inputs.json', container=True)
        progress["phase"] = "artifact-validation"
        _check_signal()
        _atomic_json(evidence / "progress.json", progress)
        production_panic_proof = _validate_production_rust_panic_refs(
            build, tools, evidence, env, timeout, command_rows)
        fresh_object_ownership = _reuse_validate_changed_rust_object(build, evidence)
        artifacts, link_snapshot = _validate_image(build, tools, evidence)
        source_after = _reuse_validate_source(source_root, candidate_sha, ihk_sha, manifest,
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
        result.update(production_rust_core_panic_reference_proof=production_panic_proof,
                      native_fork_owned_transaction=False,
                      operation_scope='IMAGE_BUILD_ONLY',
                      kernel_native_fork_config=True,
                      native_executor_pair_acceptance='OPEN')
        result['readonly_reuse'] = dict(
            schema=_REUSE_FIXED['schema'], inputs_sha256=_REUSE_INPUT_SHA256,
            fresh_object_ownership=fresh_object_ownership,
            configuration_mode=_REUSE_FIXED['configuration_mode'],
            fresh_full_configure=False, reused_object_count=9,
            replaced_object_count=2, link_input_count=11,
            postimages=_REUSE_FIXED['postimages'],
            objects=[dict(build_relative=row['build_relative'], reused=not row['replace'],
                          artifact=_artifact(build / row['build_relative'], 'final link object'))
                     for row in _REUSE_FIXED['objects']])
        if source.get('source_derivative_sha256') is not None:
            result.update(candidate_identity_scope='base_git_commit_only',
                          source_derivative_sha256=source['source_derivative_sha256'],
                          materialization_sha256=source['materialization_sha256'])
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
            for selected in result['readonly_reuse']['objects']:
                _fail(_artifact(build / selected['build_relative'], 'final reuse object') == selected['artifact'],
                      'final reuse object changed before receipt')
            _reuse_authenticate('/reuse-inputs.json', container=True)
            _revalidate_link_contract_snapshots(build, evidence, link_snapshot)
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

_REUSE_FRESH_RUN = _run
_REUSE_FRESH_MAIN = main

_REUSE_CONSUMED_GITLINK_VIEWS = json.loads('[{"entries": {".": {"kind": "directory", "mode": 16832}, ".git": {"kind": "directory", "mode": 16832}, ".git/HEAD": {"bytes": 41, "kind": "regular", "mode": 33152, "sha256": "ee3e06cee2c306101d8a4f2bfb733a64877b0720bbf8c65b228756134f762735"}, ".git/branches": {"kind": "directory", "mode": 16832}, ".git/config": {"bytes": 92, "kind": "regular", "mode": 33152, "sha256": "cfe7ba1238c9a78be7535d7c63bcaf5a4d5011d46b07c9b45d3bbf7d6c312dfe"}, ".git/description": {"bytes": 73, "kind": "regular", "mode": 33152, "sha256": "85ab6c163d43a17ea9cf7788308bca1466f1b0a8d1cc92e26e9bf63da4062aee"}, ".git/hooks": {"kind": "directory", "mode": 16832}, ".git/hooks/applypatch-msg.sample": {"bytes": 478, "kind": "regular", "mode": 33216, "sha256": "0223497a0b8b033aa58a3a521b8629869386cf7ab0e2f101963d328aa62193f7"}, ".git/hooks/commit-msg.sample": {"bytes": 896, "kind": "regular", "mode": 33216, "sha256": "1f74d5e9292979b573ebd59741d46cb93ff391acdd083d340b94370753d92437"}, ".git/hooks/fsmonitor-watchman.sample": {"bytes": 3079, "kind": "regular", "mode": 33216, "sha256": "9c34ab6527211ec8605b2a563f5329ed8f66dbfbd11e677c78da6c3171085604"}, ".git/hooks/post-update.sample": {"bytes": 189, "kind": "regular", "mode": 33216, "sha256": "81765af2daef323061dcbc5e61fc16481cb74b3bac9ad8a174b186523586f6c5"}, ".git/hooks/pre-applypatch.sample": {"bytes": 424, "kind": "regular", "mode": 33216, "sha256": "e15c5b469ea3e0a695bea6f2c82bcf8e62821074939ddd85b77e0007ff165475"}, ".git/hooks/pre-commit.sample": {"bytes": 1638, "kind": "regular", "mode": 33216, "sha256": "d6d114e507a3295ff3a2e214611c2f5c0d13eaf0ed53f595ba02e4cc714fca18"}, ".git/hooks/pre-merge-commit.sample": {"bytes": 416, "kind": "regular", "mode": 33216, "sha256": "d3825a70337940ebbd0a5c072984e13245920cdf8898bd225c8d27a6dfc9cb53"}, ".git/hooks/pre-push.sample": {"bytes": 1348, "kind": "regular", "mode": 33216, "sha256": "4b1119e1e13a212571976f4aee77847cdbd40978546d6273a557e238981a40d1"}, ".git/hooks/pre-rebase.sample": {"bytes": 4898, "kind": "regular", "mode": 33216, "sha256": "4febce867790052338076f4e66cc47efb14879d18097d1d61c8261859eaaa7b3"}, ".git/hooks/pre-receive.sample": {"bytes": 544, "kind": "regular", "mode": 33216, "sha256": "a4c3d2b9c7bb3fd8d1441c31bd4ee71a595d66b44fcf49ddb310252320169989"}, ".git/hooks/prepare-commit-msg.sample": {"bytes": 1492, "kind": "regular", "mode": 33216, "sha256": "e9ddcaa4189fddd25ed97fc8c789eca7b6ca16390b2392ae3276f0c8e1aa4619"}, ".git/hooks/update.sample": {"bytes": 3610, "kind": "regular", "mode": 33216, "sha256": "751c037320024ec2ee2757f3ffae0b10ad2c946367684e7059d4dc97eac7e431"}, ".git/index": {"bytes": 36812, "kind": "regular", "mode": 33152, "sha256": "673fdce650c711fe89f268f995c3cd68ffb8c20adcc241b343d91b4246da62f8"}, ".git/info": {"kind": "directory", "mode": 16832}, ".git/info/exclude": {"bytes": 240, "kind": "regular", "mode": 33152, "sha256": "6671fe83b7a07c8932ee89164d1f2793b2318058eb8b98dc5c06ee0a5a3b0ec1"}, ".git/logs": {"kind": "directory", "mode": 16832}, ".git/logs/HEAD": {"bytes": 256, "kind": "regular", "mode": 33152, "sha256": "43dc20b05cf614b8a3f3492ed1da7cf327118dc8031a5e87cfe247af226a7550"}, ".git/objects": {"kind": "directory", "mode": 16832}, ".git/objects/info": {"kind": "directory", "mode": 16832}, ".git/objects/pack": {"kind": "directory", "mode": 16832}, ".git/objects/pack/pack-fee6618494c05a738a42ee8a2433ae535e3a3770.idx": {"bytes": 286672, "kind": "regular", "mode": 33024, "sha256": "df54908fd3271278484420b47dabfaf60cc8ee8ebbffc97529bc7e69798625cb"}, ".git/objects/pack/pack-fee6618494c05a738a42ee8a2433ae535e3a3770.pack": {"bytes": 31652154, "kind": "regular", "mode": 33024, "sha256": "dff4ca87d074af036346701d2565f8fa578d54d7222d7672b5b8ba9b73b31302"}, ".git/packed-refs": {"bytes": 46, "kind": "regular", "mode": 33152, "sha256": "6110899c7adc374885f9552bddfb76fa28a7f7ca3c05fb8b74471a457e1e57c8"}, ".git/refs": {"kind": "directory", "mode": 16832}, ".git/refs/heads": {"kind": "directory", "mode": 16832}, ".git/refs/tags": {"kind": "directory", "mode": 16832}, ".gitignore": {"bytes": 41, "kind": "regular", "mode": 33188, "sha256": "99ede16c2d16f6073fb57a2466a263b685821394abc748bcb0ce65eaf8a889c2"}, "AUTHORS": {"bytes": 37, "kind": "regular", "mode": 33188, "sha256": "cb843ef537aaafeeb73ff78318fd77e296b8116bf988b597cc6a5a7088dc157d"}, "CMakeLists.txt": {"bytes": 1008, "kind": "regular", "mode": 33188, "sha256": "8d453ea37a4592ec4a4ac3aa31951dca25a7ee6baba2d43ecd0a49069b68a842"}, "COPYING": {"bytes": 540, "kind": "regular", "mode": 33188, "sha256": "7215e8de2ed9d877d7d0d16ca532a4632e48d590b3baed2bd28dc1d7e431da9c"}, "ChangeLog": {"bytes": 1564, "kind": "regular", "mode": 33188, "sha256": "d0dc23f3f64a2dc03b73e8ce8765cb8bd61359ba0f7334e926fc19700fc33421"}, "INSTALL": {"bytes": 15752, "kind": "regular", "mode": 33188, "sha256": "e07808836b9bd90b07bc32117cde46b06821ff718514f575719a0ec5c306a24a"}, "Makefile.am": {"bytes": 1138, "kind": "regular", "mode": 33188, "sha256": "9f29b7df8f51132e8ce5eb5135cd0a90a34d9febd768619379970a1b94db6d6b"}, "Makefile.in": {"bytes": 27340, "kind": "regular", "mode": 33188, "sha256": "08ce9fe286b895951fdad1cf33397e8b2e40fbe89f0ca6034bad5a1938bd7ba8"}, "NEWS": {"bytes": 3074, "kind": "regular", "mode": 33188, "sha256": "06daf1c6525dced22563a24f8277758981565bb10cb3b0f1a22e5e545fec302d"}, "README": {"bytes": 6204, "kind": "regular", "mode": 33188, "sha256": "afe4f3aa52a16985848cd24fe964182785d8c27e3cc5751e661e91a905ad6d28"}, "README.md": {"bytes": 673, "kind": "regular", "mode": 33188, "sha256": "37d6338c509d0971c64573c6f3acd13a0170b0c65e037e7bfefa3a61a31430a4"}, "aclocal.m4": {"bytes": 44352, "kind": "regular", "mode": 33188, "sha256": "7bccb5f9eb244732dc840fcea9ef4a6503fc6f96614fcff64ab1d945f4717ae1"}, "appveyor.yml": {"bytes": 1340, "kind": "regular", "mode": 33188, "sha256": "e1bb4f0dd242c7160385053ff5497864aad35894fb2ec92497dfb82c62a1b581"}, "ar-lib": {"bytes": 5826, "kind": "regular", "mode": 33261, "sha256": "73f97940d6551db8f0b266941e318571aac460bf3bbf364e445ebeebcfcfdd16"}, "autom4te.cache": {"kind": "directory", "mode": 16832}, "autom4te.cache/output.0": {"bytes": 680986, "kind": "regular", "mode": 33188, "sha256": "cfc8c6099c7d5240c866b4048dfe797eefec93de7da877c9af29f3813a237b4a"}, "autom4te.cache/output.1": {"bytes": 680986, "kind": "regular", "mode": 33188, "sha256": "cfc8c6099c7d5240c866b4048dfe797eefec93de7da877c9af29f3813a237b4a"}, "autom4te.cache/requests": {"bytes": 15055, "kind": "regular", "mode": 33188, "sha256": "31d6bb62f5e911bbcd3adc88732ab38d16afef3775639bd8c3f000a426fbc65b"}, "autom4te.cache/traces.0": {"bytes": 128082, "kind": "regular", "mode": 33188, "sha256": "a51eabfac71f97cb11d5d337e23ae242d522e19c135ae64867120251d92e2cbf"}, "autom4te.cache/traces.1": {"bytes": 57114, "kind": "regular", "mode": 33188, "sha256": "26a71c26345c5ea458b727edc041723c74b257da34c86947e5d1a88e7e487d08"}, "bugxml": {"kind": "directory", "mode": 16832}, "bugxml/README": {"bytes": 561, "kind": "regular", "mode": 33188, "sha256": "1506d71572643ce641c35f6ee5676a00bb4fd64d8799bb412f3fa0ab76e64329"}, "bugxml/bugrecord.py": {"bytes": 8934, "kind": "regular", "mode": 33261, "sha256": "a6baa0dbe4b8c874d1f8126379aaf064dc25ecc7735124ee8aa5198fe561989d"}, "bugxml/data.template": {"bytes": 116, "kind": "regular", "mode": 33188, "sha256": "299710524917cf2cce4ff0694e68240ba28f4d7d2d4c9dcca0d32ffef74b2a6c"}, "bugxml/data.txt": {"bytes": 43415, "kind": "regular", "mode": 33188, "sha256": "0ddbf4ec5607d09bbd36ed09429cdf501a92045588ffb228226b8f600738d707"}, "bugxml/readbugs.py": {"bytes": 6860, "kind": "regular", "mode": 33261, "sha256": "a2c26842f9f35c056ce531e87765f04f70081745eb881df72d5ccd57474f7022"}, "cmake": {"kind": "directory", "mode": 16832}, "cmake/AutoconfHelper.cmake": {"bytes": 12641, "kind": "regular", "mode": 33188, "sha256": "1efabeda88c3af51136d3e899645cfb18d03deec1b4d6fc9f8fbfa3af6693e18"}, "cmake/FindLibElf.cmake": {"bytes": 1559, "kind": "regular", "mode": 33188, "sha256": "8cf5f86a09560abfbc6597afcd9a70a87df1d0c6fe59c877eedff01b926d3963"}, "cmake/LibdwarfMacros.cmake": {"bytes": 531, "kind": "regular", "mode": 33188, "sha256": "1daa674589e560d5b6d8662549ce10441f74c255b78475f1461b8455b7e736b1"}, "codingstyle.txt": {"bytes": 11992, "kind": "regular", "mode": 33188, "sha256": "8018ae1e5524631caecd739d4ecdf0f71c22d038a5d608c95b5d3393b490e769"}, "compile": {"bytes": 7333, "kind": "regular", "mode": 33261, "sha256": "41856428226c049fa0ea4ca7a574c28416de2769b55ed7feea4ab5e60283af16"}, "config.guess": {"bytes": 43499, "kind": "regular", "mode": 33261, "sha256": "fbc2337aa59a204f5d74743b82c8be7aab8b39853b4e54a888008f70430c4305"}, "config.h.in": {"bytes": 5265, "kind": "regular", "mode": 33188, "sha256": "73e4cbdcfbfff78d549743d2b9ad4cc832b9c9ae6f7ba71385d1b85ff45ecdd8"}, "config.sub": {"bytes": 36144, "kind": "regular", "mode": 33261, "sha256": "72e02ea93447038f8ced24f296b31e0f397bbcc6b32abdcf9b38c80f153433fd"}, "configure": {"bytes": 676883, "kind": "regular", "mode": 33261, "sha256": "e4e3b2b5584cfe11dc87e25f491db29a1cda3c8011a81b1b2b28492792a577cd"}, "configure.ac": {"bytes": 18573, "kind": "regular", "mode": 33188, "sha256": "b7fa767653d143045e75ab9e75782e9d9759ce3ced73a21cc52164b249211ace"}, "configure.cmake": {"bytes": 866, "kind": "regular", "mode": 33188, "sha256": "3ec66d81c4c091834de223789e4beb706178fc9a516d94677fb74ff62da13f05"}, "depcomp": {"bytes": 23566, "kind": "regular", "mode": 33261, "sha256": "786149ab4493e86b837077ebaecab65ef6230ae8a619b17fa5c1695564a427e9"}, "dwarfdump": {"kind": "directory", "mode": 16832}, "dwarfdump/CMakeLists.txt": {"bytes": 5933, "kind": "regular", "mode": 33188, "sha256": "33671a8b22ef0ac9a2ad5a1cd68dc567f3e0acf291f8205cecb58dee415af9be"}, "dwarfdump/CODINGSTYLE": {"bytes": 1543, "kind": "regular", "mode": 33188, "sha256": "991a9f3f4047b8131116e138440a671c04461d0ce927af57ac4c24bf8ac79cb0"}, "dwarfdump/COPYING": {"bytes": 1004, "kind": "regular", "mode": 33188, "sha256": "9b09867a527426ac6730f7d1ae2979dce3cf3acc33a0c030d1d0a37878e54781"}, "dwarfdump/ChangeLog": {"bytes": 19019, "kind": "regular", "mode": 33188, "sha256": "b22de9ebf77fead3bae7adb1c71c4f9dbea166c76128c4d19b97c1420c60293a"}, "dwarfdump/ChangeLog2006": {"bytes": 14145, "kind": "regular", "mode": 33188, "sha256": "55fe0f4984d1d0c19788352cff21d946efe0269ecab7938eb64a83a4d029cee7"}, "dwarfdump/ChangeLog2007": {"bytes": 5785, "kind": "regular", "mode": 33188, "sha256": "3d9b18ca7b6481db1a984bfbd964fa7f317c2b7c8fd12d63d47112cd80a92c73"}, "dwarfdump/ChangeLog2008": {"bytes": 5100, "kind": "regular", "mode": 33188, "sha256": "ecd65e3c040d395d35a967b2fdd474c9db7f32b6683b8871f319ff7110956b42"}, "dwarfdump/ChangeLog2009": {"bytes": 15040, "kind": "regular", "mode": 33188, "sha256": "a4401e6a84272d7f01170dfc1d12b283e8a24d50f313035440b87702f97388aa"}, "dwarfdump/ChangeLog2010": {"bytes": 5416, "kind": "regular", "mode": 33188, "sha256": "f564e80f3195ffccc656df6d11c10d5899af636a9f3f888267bcf526ea1f0993"}, "dwarfdump/ChangeLog2011": {"bytes": 16217, "kind": "regular", "mode": 33188, "sha256": "b10c505558315ff0d47e4725fc142b675d2b65349ae3ebe2e4abb5d079ee90e1"}, "dwarfdump/ChangeLog2012": {"bytes": 6431, "kind": "regular", "mode": 33188, "sha256": "42dd4e65d01e644a14be530b68faa87266e2fefbe07bd75290d1f21fe6b0edca"}, "dwarfdump/ChangeLog2013": {"bytes": 4294, "kind": "regular", "mode": 33188, "sha256": "afdc3c7f21d4e5fbc10ba4b598d06cf9886b5afab8fe284ca59fa6c5b2af89f9"}, "dwarfdump/ChangeLog2014": {"bytes": 7562, "kind": "regular", "mode": 33188, "sha256": "cc8829993f8932db1b3daca0b33299aae5f8b8b0bae032fa6eff380db4da0b7e"}, "dwarfdump/ChangeLog2015": {"bytes": 21137, "kind": "regular", "mode": 33188, "sha256": "23ca176cd031b4fd82434b89848d5644d116434210e2ffd82cb81c0fa90880b0"}, "dwarfdump/ChangeLog2016": {"bytes": 24663, "kind": "regular", "mode": 33188, "sha256": "5ee9f19c71639e6cad25c600a2fcf42af74a61ed7dde7112d23a219be2151668"}, "dwarfdump/ChangeLog2017": {"bytes": 11471, "kind": "regular", "mode": 33188, "sha256": "72da8b2f4925fe0ee633afb197e3d2ae5e6f575b88f553249d1c75828973132e"}, "dwarfdump/DWARFDUMPCOPYRIGHT": {"bytes": 3910, "kind": "regular", "mode": 33188, "sha256": "09ceea62f90d786ec0c3feaaa4303fea9ba20e2d70131a7f9f162e771bcdb217"}, "dwarfdump/GPL.txt": {"bytes": 17987, "kind": "regular", "mode": 33188, "sha256": "ab15fd526bd8dd18a9e77ebc139656bf4d33e97fc7238cd11bf60e2b9b8666c6"}, "dwarfdump/Makefile.am": {"bytes": 6665, "kind": "regular", "mode": 33188, "sha256": "8c29a6c8b9ee60a96d91f2857ce2bf767f447a92d49051ab06403527f55e485d"}, "dwarfdump/Makefile.in": {"bytes": 174093, "kind": "regular", "mode": 33188, "sha256": "b5a96f730dbca8c8d4eeb7e2f674f5d073b2551b13bcf78f3ae386fb6b624d23"}, "dwarfdump/NEWS": {"bytes": 11551, "kind": "regular", "mode": 33188, "sha256": "717ecf91b104e7809e6c00deb953cc75940ac627ae92779dc0109450fcf9f4ad"}, "dwarfdump/README": {"bytes": 3171, "kind": "regular", "mode": 33188, "sha256": "bdb709e4e45a7df324c6156cc00a8c67f46ef62ac82ef886361c1350aab7f91d"}, "dwarfdump/addrmap.c": {"bytes": 3504, "kind": "regular", "mode": 33188, "sha256": "110f4dc83b22dd8003f6d14df3d1a4f5f491f24c20f67b2dc2ea86484aded1ea"}, "dwarfdump/addrmap.h": {"bytes": 1487, "kind": "regular", "mode": 33188, "sha256": "8051adce5a7b39a0006ece956995a2821ada0978b4e820e3f1f254cc784eca38"}, "dwarfdump/checkutil.c": {"bytes": 18068, "kind": "regular", "mode": 33188, "sha256": "dd28af42ac41cd9f61d965180e0b9a482afc380896df1d707993381956d068c4"}, "dwarfdump/checkutil.h": {"bytes": 3858, "kind": "regular", "mode": 33188, "sha256": "f9e97aea57f8535f124a8686309bd503475b95e2969e1f2c5182ab430ff728d9"}, "dwarfdump/command_options.c": {"bytes": 45461, "kind": "regular", "mode": 33188, "sha256": "f3d1351e7efbdd05cb51de8801cb1014ed72c177a084000ac53d50565fc2aaf5"}, "dwarfdump/command_options.h": {"bytes": 1361, "kind": "regular", "mode": 33188, "sha256": "de4fbfcdf9c6a249254a2a464aa75c98f76e97be64ea565c7ed1b935db8e9914"}, "dwarfdump/common.c": {"bytes": 3012, "kind": "regular", "mode": 33188, "sha256": "d5647304596b162e8a42c4175ec059449edf2e5901b71fd1dd38272864912a52"}, "dwarfdump/common.h": {"bytes": 1390, "kind": "regular", "mode": 33188, "sha256": "0cbad2403e907efd2c0077a5e98c97dd0fad1bd9f94b3ebd2a13f9e874a0c545"}, "dwarfdump/compiler_info.c": {"bytes": 15866, "kind": "regular", "mode": 33188, "sha256": "5e49d64bb5d58af290f63e4f4049981869db6af142876849f613bde2ea719d7c"}, "dwarfdump/compiler_info.h": {"bytes": 2278, "kind": "regular", "mode": 33188, "sha256": "d9083f437d59a943f0a172ce2a13163a44803857729b0583c0520994e4382d5d"}, "dwarfdump/config.h.in.cmake": {"bytes": 3424, "kind": "regular", "mode": 33188, "sha256": "ff29f1d547199eed072fcccd28c2c4acc798e54d24163ce9003035db8fc7051c"}, "dwarfdump/configure": {"bytes": 164341, "kind": "regular", "mode": 33261, "sha256": "1eeb9a827e6ffb4a418c4aa071689dab06b422bf31ac3f4464a2f755b89d6fa1"}, "dwarfdump/configure.cmake": {"bytes": 2398, "kind": "regular", "mode": 33188, "sha256": "f601442790c9cbed13c1b012d406875e209d38e7a2602d29b18f1174d8bfdb89"}, "dwarfdump/defined_types.h": {"bytes": 1410, "kind": "regular", "mode": 33188, "sha256": "2f155e3d6f6ba6c848e0038f8aa44fea251f48ec1fb76eaecdafa014a799ec89"}, "dwarfdump/dwarf_tsearch.h": {"bytes": 3705, "kind": "regular", "mode": 33188, "sha256": "71c0156f4f56d190145d45911c3778ae3b1639f1e8c718d0fed82dc1751b542b"}, "dwarfdump/dwarf_tsearchbal.c": {"bytes": 27373, "kind": "regular", "mode": 33188, "sha256": "8c08c1b87185f90d6450f96e7b3bd5e895785da288fd37bad6179b4562735022"}, "dwarfdump/dwarfdump.1": {"bytes": 19634, "kind": "regular", "mode": 33188, "sha256": "53de01a4b511a515c970fc06e773dd5a75e4313172057b5333e2780eb1af8b4e"}, "dwarfdump/dwarfdump.c": {"bytes": 53951, "kind": "regular", "mode": 33188, "sha256": "c18e2cf31b8545bd554d1c6961e745e5052013dda98c999583918767a6889c6a"}, "dwarfdump/dwarfdump.conf": {"bytes": 15352, "kind": "regular", "mode": 33188, "sha256": "e9858fd56fbee29179a5c79ad3aab0bfd8c18ccf2deebdedcedb7a4c5e76e90c"}, "dwarfdump/dwconf.c": {"bytes": 42015, "kind": "regular", "mode": 33188, "sha256": "8bf76ba90e897f634359d38bd93d34c1964d903c278a7ce7cd5b0047ef6276cc"}, "dwarfdump/dwconf.h": {"bytes": 4449, "kind": "regular", "mode": 33188, "sha256": "811f9c2412ee520267fa0cce2acebcdd9a8b0204547011757953f6ddd7428d69"}, "dwarfdump/dwgetopt.c": {"bytes": 11288, "kind": "regular", "mode": 33188, "sha256": "2858e2e380ab38bd33d5e602f84b4a71743c664461395135572318a599297863"}, "dwarfdump/dwgetopt.h": {"bytes": 3255, "kind": "regular", "mode": 33188, "sha256": "5d8fe20b4d2dc5e0c63608093e27bc0fe562c554a778e7ea89711b942f30bea3"}, "dwarfdump/esb.c": {"bytes": 25077, "kind": "regular", "mode": 33188, "sha256": "72402e322947c86512836bcb281dcec95c879de5487e9c5400e5c2f088364b0e"}, "dwarfdump/esb.h": {"bytes": 5035, "kind": "regular", "mode": 33188, "sha256": "9c3a743f23a3a0df8af8b78444994e8643881974cb60edd0cec2b029a2e695c8"}, "dwarfdump/getopttest.c": {"bytes": 20392, "kind": "regular", "mode": 33188, "sha256": "1afd4efadff54ebc4ea9bf2c9487abc204c470feb9eae4ecea0848e5a035da63"}, "dwarfdump/glflags.c": {"bytes": 12779, "kind": "regular", "mode": 33188, "sha256": "48aa9ad7f5026c7cd99077c1b3fdbd2a5d2f36c342a1f66c43e4528604e417a1"}, "dwarfdump/glflags.h": {"bytes": 14146, "kind": "regular", "mode": 33188, "sha256": "2f3d66289a13192d7a65c1757bbc9f9b158aa5318c8254839cb6801ffc5c82d1"}, "dwarfdump/globals.h": {"bytes": 10050, "kind": "regular", "mode": 33188, "sha256": "2985c60ee73e22cdcc635e1eb63a66115e06e0ae88e4e42d5061165462a164d5"}, "dwarfdump/helpertree.c": {"bytes": 5330, "kind": "regular", "mode": 33188, "sha256": "114db849e5799a0628042337117e1ed6c5dd192ad8bb3cb89f77fd90f3550b3d"}, "dwarfdump/helpertree.h": {"bytes": 2494, "kind": "regular", "mode": 33188, "sha256": "f4341ba08ab12af7f84bf30be6e5975348be1a596b4d84ae631357cc788ebefe"}, "dwarfdump/macrocheck.c": {"bytes": 15930, "kind": "regular", "mode": 33188, "sha256": "6d8b9a86d8a3eb2e256f811f4144e17c2c9ff324bc95b636f84f80a969ac9604"}, "dwarfdump/macrocheck.h": {"bytes": 2063, "kind": "regular", "mode": 33188, "sha256": "a4e1a9c1359f4c62315628ff4876826c7af2e267a6d8ec034619ab6922f7eebc"}, "dwarfdump/makename.c": {"bytes": 4063, "kind": "regular", "mode": 33188, "sha256": "bd84c59f45edeaf1407bb6aa7798dbe872b53160ac2867d11dbcd22e23d849b4"}, "dwarfdump/makename.h": {"bytes": 1827, "kind": "regular", "mode": 33188, "sha256": "3013715e597244fad4653826e52b952d9160e9e6119a60ddba12c1416822be4d"}, "dwarfdump/naming.c": {"bytes": 8597, "kind": "regular", "mode": 33188, "sha256": "81e11e6ecd39a3dbd28e7e6d9a91731f68511e819cc15b13e6ad835c6799bf6a"}, "dwarfdump/naming.h": {"bytes": 3258, "kind": "regular", "mode": 33188, "sha256": "67d02e16d416c974fc2cc0d173d19fcae6312dec40e676ab92ffd8ee056bd766"}, "dwarfdump/print_abbrevs.c": {"bytes": 26373, "kind": "regular", "mode": 33188, "sha256": "22bf441ca1777405a468822dbed471c5b4d9fcd8ac3c8103520f80154ca4855d"}, "dwarfdump/print_aranges.c": {"bytes": 11618, "kind": "regular", "mode": 33188, "sha256": "94fcf7cc7e1bb95e2c38d4f3446760288a4bf18f1e0bfbc811134a89e71fc7a6"}, "dwarfdump/print_debugfission.c": {"bytes": 6658, "kind": "regular", "mode": 33188, "sha256": "de2cf32ef5c466fcb907a5bef24ef774078dc184647085a0351cb213e578159a"}, "dwarfdump/print_die.c": {"bytes": 229222, "kind": "regular", "mode": 33188, "sha256": "1f82eb4c700d3e40c8c0cc6bb6b4983b7bbe79a222b1cb0fac43e675b31b2d47"}, "dwarfdump/print_dnames.c": {"bytes": 2730, "kind": "regular", "mode": 33188, "sha256": "4c11e7965ad6598be73f6bf29e9fa1b0477458ddd1481555c86c582835db85c8"}, "dwarfdump/print_frames.c": {"bytes": 92870, "kind": "regular", "mode": 33188, "sha256": "7ea7a3f438ad11bc9e04ad3a3fb61bd97478ce49d50acab4b22e091c7e3681fb"}, "dwarfdump/print_frames.h": {"bytes": 1701, "kind": "regular", "mode": 33188, "sha256": "ed8e9d9391601267a0c3541bc87200315351e6c8ef858aaf38076968d8e497c4"}, "dwarfdump/print_gdbindex.c": {"bytes": 14337, "kind": "regular", "mode": 33188, "sha256": "cc5e78ade1bba72f855dee622e0f3b1ebf1b60f41903b49664d77ffbf3ecd076"}, "dwarfdump/print_lines.c": {"bytes": 35984, "kind": "regular", "mode": 33188, "sha256": "1f83937b9453a44c9f3b7f3b14daafb59b0cd28f5c8eb25b06bb27d8b68163ac"}, "dwarfdump/print_locs.c": {"bytes": 5598, "kind": "regular", "mode": 33188, "sha256": "7ac0ff3d18af5570fd9884fa13970984c64f25ae8a5e6771774d0e4b0a7c97ec"}, "dwarfdump/print_macro.c": {"bytes": 16578, "kind": "regular", "mode": 33188, "sha256": "338b677525ffb69495292047fa41b7401f297bccb26fa1515846a8bec0411781"}, "dwarfdump/print_macros.c": {"bytes": 6919, "kind": "regular", "mode": 33188, "sha256": "39fe3736bba917eb8350f85eaa0dccfa8585a220dbfbba7ecce78055403234ac"}, "dwarfdump/print_pubnames.c": {"bytes": 10558, "kind": "regular", "mode": 33188, "sha256": "d3c3a337bf060374302b2decb133c0a18cfb6284c8ff247e161e15881faa1bdb"}, "dwarfdump/print_ranges.c": {"bytes": 13000, "kind": "regular", "mode": 33188, "sha256": "6ac73a4ab07f7a712a7a5abe392e57a14bb9708e6bb343f94e6b179fe4543bbf"}, "dwarfdump/print_reloc.c": {"bytes": 27777, "kind": "regular", "mode": 33188, "sha256": "d32db818d2da8ea266ec50c6d8cd38bb20a2992b47241fbf680a837c31ff4d1f"}, "dwarfdump/print_reloc.h": {"bytes": 1492, "kind": "regular", "mode": 33188, "sha256": "0584f75218a8a3667bd018cbff8300d7be2a32d5deabc158ded05adba88087f2"}, "dwarfdump/print_section_groups.c": {"bytes": 8932, "kind": "regular", "mode": 33188, "sha256": "aee5a08c0b44d62f4cf88226d214407bb6b4559a42bff0314ac1c48ffaa097f8"}, "dwarfdump/print_sections.c": {"bytes": 3875, "kind": "regular", "mode": 33188, "sha256": "3951bece71331748c4898c26575e1aa195e2d723ade0b93a4752dc589763b7dd"}, "dwarfdump/print_sections.h": {"bytes": 1799, "kind": "regular", "mode": 33188, "sha256": "324c9db1c6e69a131ffc7476959023ffa39e4964bbe8a3f20ce59b432bd0194c"}, "dwarfdump/print_static_funcs.c": {"bytes": 4714, "kind": "regular", "mode": 33188, "sha256": "9faf05ff65ccaab88f12b2562e983ccce12656804da7309497a5180a8d32a2b2"}, "dwarfdump/print_static_vars.c": {"bytes": 3401, "kind": "regular", "mode": 33188, "sha256": "1cc347c7ea0da1b5b3eb8b17cf6f3c127189b29c7ca23ea0696bb3e0236b7bc7"}, "dwarfdump/print_str_offsets.c": {"bytes": 5781, "kind": "regular", "mode": 33188, "sha256": "4cc1cd6e4833bb031376b6c86beeef66849d5d7531a6e76af76d1497634971dc"}, "dwarfdump/print_strings.c": {"bytes": 3313, "kind": "regular", "mode": 33188, "sha256": "1bb18c3059ff21ec046147a452ec4c20a4d837db9c6f70b84bca357a1b8da339"}, "dwarfdump/print_types.c": {"bytes": 4962, "kind": "regular", "mode": 33188, "sha256": "8d231f0f8c41d1260d47146c524cd545b72f59ceebfa5ee2ddc2b610d3cbca10"}, "dwarfdump/print_weaknames.c": {"bytes": 3412, "kind": "regular", "mode": 33188, "sha256": "428dd36a6570a1b433ed59e5928f63388186e4fe92d21e502735c9cb2788e311"}, "dwarfdump/runtests.sh": {"bytes": 2948, "kind": "regular", "mode": 33261, "sha256": "65ead756ac535a93fb94a7458e1fd2fc1c6b77c5ea20ab49afe40432483359d8"}, "dwarfdump/sanitized.c": {"bytes": 6894, "kind": "regular", "mode": 33188, "sha256": "eb3aade4f1a25311158448d3c4eea13ae12953e88a24fc06856bc30b5b9e0f08"}, "dwarfdump/sanitized.h": {"bytes": 1720, "kind": "regular", "mode": 33188, "sha256": "48ce351d390ed3a81c1a9c44af7499491f806ef651dfd5090c5e623ed98ace8d"}, "dwarfdump/section_bitmaps.c": {"bytes": 6257, "kind": "regular", "mode": 33188, "sha256": "c10ad437f2b489018e0d0a408e2971629e73055bc204aa10cb548cff4ea6619b"}, "dwarfdump/section_bitmaps.h": {"bytes": 8104, "kind": "regular", "mode": 33188, "sha256": "d90b7299fe0369275ac0fe8c0d888864d6223e0a05d4734747d0faff4083672f"}, "dwarfdump/strstrnocase.c": {"bytes": 3445, "kind": "regular", "mode": 33188, "sha256": "f782094a40dbea55745241a18a6461ac7ee82a853263aabe9fee47c00d207f3e"}, "dwarfdump/tag_attr.c": {"bytes": 18114, "kind": "regular", "mode": 33188, "sha256": "04f533a80cd1cb82d21849f275f21efe6fb51e863861b7b680107c3f24e8719f"}, "dwarfdump/tag_attr.list": {"bytes": 18455, "kind": "regular", "mode": 33188, "sha256": "fd043bb9b6d8c2760b783bc79b9b8f2385b4e41e943e6231faf85400068478e3"}, "dwarfdump/tag_attr_ext.list": {"bytes": 3752, "kind": "regular", "mode": 33188, "sha256": "430f4a9e134a2b318d34b8985ee5a543d96770c6aac98298cb65909e154fa7c9"}, "dwarfdump/tag_common.c": {"bytes": 4154, "kind": "regular", "mode": 33188, "sha256": "b623a3508019ad6d9001e3da16074e686c3fc6758afe044cedab9bf23952b81b"}, "dwarfdump/tag_common.h": {"bytes": 4017, "kind": "regular", "mode": 33188, "sha256": "0082cd12cc88ecbb33e114f389479d7fadae44921c2ce2a09d60804c15e2960f"}, "dwarfdump/tag_tree.c": {"bytes": 16594, "kind": "regular", "mode": 33188, "sha256": "b9b3467d22bb4b07b222d1737efcc015e867f5c1e4e2a36ea08fc067207b7eb5"}, "dwarfdump/tag_tree.list": {"bytes": 12900, "kind": "regular", "mode": 33188, "sha256": "5c10f6cce6fa5ab4fae9f862b3e799b074dd67769a3d3d8bd69c92322d2a77d2"}, "dwarfdump/tag_tree_ext.list": {"bytes": 3181, "kind": "regular", "mode": 33188, "sha256": "d3dd9e314d33f8836c50943c526fcebcc3d5e0431d42941805ac89a096138991"}, "dwarfdump/testesb.c": {"bytes": 12853, "kind": "regular", "mode": 33188, "sha256": "17939fbdd3206084bac16ea31ec7e978d6625d91b448d56598ec80725b0d9548"}, "dwarfdump/true_section_name.c": {"bytes": 3560, "kind": "regular", "mode": 33188, "sha256": "32c0fa66dc7ddfd046b539f25796cee2118bcf99ba2fbb8d028aeea29dc547f1"}, "dwarfdump/uri.c": {"bytes": 9934, "kind": "regular", "mode": 33188, "sha256": "3e382d31709c171541524322079d5ac33de8f04ff2bf62a7b10b8b18bf9ba90d"}, "dwarfdump/uri.h": {"bytes": 1336, "kind": "regular", "mode": 33188, "sha256": "50cc494a9a140c08d0e999ce472af29f7ccad83776fda9e960b156ed3ecbc18c"}, "dwarfdump/uritablebuild.c": {"bytes": 3934, "kind": "regular", "mode": 33188, "sha256": "d4c201a8e0082877385c57b241b283fbecb7f4faeeff253c9f666f03e78d8e45"}, "dwarfdump/warningcontrol.h": {"bytes": 1246, "kind": "regular", "mode": 33188, "sha256": "81507d4dce39e1cc9cbb3e5d5895ac0414f8c02921e98b15a17f6b2836a2e70d"}, "dwarfexample": {"kind": "directory", "mode": 16832}, "dwarfexample/CMakeLists.txt": {"bytes": 852, "kind": "regular", "mode": 33188, "sha256": "e0f4593effcc82a3bc2389607fca0320423569aa9ec34f3ec51e012d3ef23355"}, "dwarfexample/ChangeLog": {"bytes": 1236, "kind": "regular", "mode": 33188, "sha256": "2ae25bb21e5fa7d23651736b5fa08eb82118dacdbc48d056dc664a688c979244"}, "dwarfexample/ChangeLog2009": {"bytes": 463, "kind": "regular", "mode": 33188, "sha256": "5aca29f73792f6b152496d7300063b592c3a57577dc7efbdbc580ed9b06c13f7"}, "dwarfexample/ChangeLog2010": {"bytes": 567, "kind": "regular", "mode": 33188, "sha256": "f7b9483fa5bfb15ded678d26a1692b752a9c05caee125ae02a06e2fb21e7d2aa"}, "dwarfexample/ChangeLog2011": {"bytes": 245, "kind": "regular", "mode": 33188, "sha256": "9ce12a2dc85982c784529fdd686ef457fbc9dcb9c2dea0d4f03e83b4286f0fec"}, "dwarfexample/ChangeLog2012": {"bytes": 20, "kind": "regular", "mode": 33188, "sha256": "a59301161a61a908bfdca9c7a65224a5385a8823d834ad10551cf2370a3967ad"}, "dwarfexample/ChangeLog2013": {"bytes": 419, "kind": "regular", "mode": 33188, "sha256": "971e2b026fdfc3ddff7c44b59a9da184bab9c47d5c88506ec6e809d106459033"}, "dwarfexample/ChangeLog2014": {"bytes": 280, "kind": "regular", "mode": 33188, "sha256": "ad5af8d10028d1228eaffedf457e8ae4e72cb1b3e5ad003817bf3d2852982f91"}, "dwarfexample/ChangeLog2015": {"bytes": 1142, "kind": "regular", "mode": 33188, "sha256": "59c76d871e8c45e9c0bc843905f936ebc91d935e4cb0992b691ddf900c2f56b1"}, "dwarfexample/ChangeLog2016": {"bytes": 1824, "kind": "regular", "mode": 33188, "sha256": "f078f6baa2c604d936673ea8885f2ba6bfa4633a77380e23641f3975cf1c9d8e"}, "dwarfexample/ChangeLog2017": {"bytes": 533, "kind": "regular", "mode": 33188, "sha256": "03c7ae32abf32dec935fd57c7d5eaa4ed58d171c0550b0a9c7826564fe6a0b2a"}, "dwarfexample/Makefile.am": {"bytes": 906, "kind": "regular", "mode": 33188, "sha256": "0ec03cd639fabb6d1e21e414835f2bb2094db500f759afb5f5a986de5ec5f879"}, "dwarfexample/Makefile.in": {"bytes": 25474, "kind": "regular", "mode": 33188, "sha256": "cca3d982c107172b1a1d187be3cfee228b300a1988f2d1c0c6e6d89751f1cc47"}, "dwarfexample/NEWS": {"bytes": 462, "kind": "regular", "mode": 33188, "sha256": "7c6706965bf27ca913efdc4cd021b3b0d6b5f27ec5918a529664b25a9946e4dd"}, "dwarfexample/config.h.in.cmake": {"bytes": 2596, "kind": "regular", "mode": 33188, "sha256": "30e870cdb39757b29a7d70be8c1440449d022316a4ae3223f64d364ca2edb286"}, "dwarfexample/configure.cmake": {"bytes": 1077, "kind": "regular", "mode": 33188, "sha256": "783d9e673e552baa73b220052b938ffe80f6ef6cfa1337e03c018edc3653c4e5"}, "dwarfexample/frame1.c": {"bytes": 21718, "kind": "regular", "mode": 33188, "sha256": "077e5ef97db9e31ae7fe4dfa1c57c570e8724414353348afda29b422a97a28ac"}, "dwarfexample/simplereader.c": {"bytes": 34700, "kind": "regular", "mode": 33188, "sha256": "5f00d4a76a10d176f3ea506b0e214e996c00d8ee75caa2351d30a1eb37760dbf"}, "dwarfgen": {"kind": "directory", "mode": 16832}, "dwarfgen/CMakeLists.txt": {"bytes": 1043, "kind": "regular", "mode": 33188, "sha256": "fe7ba87d1860aaaa2a4b6d1001840aca5e548d87fc705febd0f7ad5b38e7ca60"}, "dwarfgen/COPYING": {"bytes": 1805, "kind": "regular", "mode": 33188, "sha256": "f5196b0feccd92b276895a294710d644e7d30326e18ebf5b29f77213c004d475"}, "dwarfgen/ChangeLog": {"bytes": 4826, "kind": "regular", "mode": 33188, "sha256": "fe3243ca39e828ae385f1323037378f4f658d9a045c5bb5b1f21f230cdd7eb82"}, "dwarfgen/ChangeLog2011": {"bytes": 968, "kind": "regular", "mode": 33188, "sha256": "44ffea269845b745527b6095fa53c3371a254f67e3563e1e1988320879cfea12"}, "dwarfgen/ChangeLog2012": {"bytes": 44, "kind": "regular", "mode": 33188, "sha256": "cf8117b0867f26175b02602f91eceed1b9327445bd547d69287e27de73316386"}, "dwarfgen/ChangeLog2013": {"bytes": 3209, "kind": "regular", "mode": 33188, "sha256": "3820f2c4ac8dc16d847602700fb10a85fce159cc8da409fcfcfc56527addf903"}, "dwarfgen/ChangeLog2014": {"bytes": 1650, "kind": "regular", "mode": 33188, "sha256": "4b526c5594b2f2aab71785e2aff1fb0d9e36ac606f0d1ea518135230b1ed08b6"}, "dwarfgen/ChangeLog2015": {"bytes": 1426, "kind": "regular", "mode": 33188, "sha256": "5ac0df84f8d9c091bd713de512f89edb9ea6571e0010aea30a6dad54adceefbc"}, "dwarfgen/ChangeLog2016": {"bytes": 1813, "kind": "regular", "mode": 33188, "sha256": "19efcc6343bfe0450a127cd3211248c66d6626177c5827c32bd3edea3ac81eca"}, "dwarfgen/ChangeLog2017": {"bytes": 1079, "kind": "regular", "mode": 33188, "sha256": "9e504b61d6807807d9fe0a79656b54a58f5058a3fd27cf42b567f968ad5bc837"}, "dwarfgen/Makefile.am": {"bytes": 1031, "kind": "regular", "mode": 33188, "sha256": "9b9bbe06613c9a630ca976c5041518630f0be4e9f8f7f1aef9f8e3382d364038"}, "dwarfgen/Makefile.in": {"bytes": 33351, "kind": "regular", "mode": 33188, "sha256": "2d2ff8d5c384772c31455b1fd2872b397b54550f6297207067d50b6fd531ce42"}, "dwarfgen/NEWS": {"bytes": 246, "kind": "regular", "mode": 33188, "sha256": "9d5b6bf4dd82e201c8350ee2938094ebdd6f82664bfcf8f313a3cee1521d2bae"}, "dwarfgen/README": {"bytes": 1509, "kind": "regular", "mode": 33188, "sha256": "5ce4400a9a5140b5abe4e6141f44bd981543a2a073363f3a2ffdb39f24bcbeca"}, "dwarfgen/TESTmallocfail": {"bytes": 686, "kind": "regular", "mode": 33188, "sha256": "e4972d644d2301ca5a9cbed1192593858e4b9b526da7df6f3e1d46d796e77cde"}, "dwarfgen/config.h.in.cmake": {"bytes": 2698, "kind": "regular", "mode": 33188, "sha256": "0b611af959faa10b05e92eae8a926e2f9b2f32ba62ec8a96bf5a50982be377c9"}, "dwarfgen/configure.cmake": {"bytes": 1054, "kind": "regular", "mode": 33188, "sha256": "221fe2d62a7e2bb03ee1ed74a5cd782a8d5d78e870bdc7e1bcf963971bdcdaad"}, "dwarfgen/createirepformfrombinary.cc": {"bytes": 15998, "kind": "regular", "mode": 33188, "sha256": "98652363abe49ea813871f355be85aed28a2e3a32573737f0f38314b2afcfe2d"}, "dwarfgen/createirepfrombinary.cc": {"bytes": 23809, "kind": "regular", "mode": 33188, "sha256": "f9310c43db4fd922f3bfd923f644ee71e9d25de80e0ade7192ea7ff62f46c060"}, "dwarfgen/createirepfrombinary.h": {"bytes": 1601, "kind": "regular", "mode": 33188, "sha256": "71cce08da1aa13bf44f265fb0dbe40280a66eb1910e4f43571d8833e8a84cd3b"}, "dwarfgen/dwarf-generator.txt": {"bytes": 968, "kind": "regular", "mode": 33261, "sha256": "a71e8c74de9fa8a84b20bcbb625c3ddb1c51634a513bfb05d09ca8b75045edbd"}, "dwarfgen/dwarfgen.1": {"bytes": 2128, "kind": "regular", "mode": 33188, "sha256": "51f94317662126b29e1a23cca903febc962bfda2da1c09a1e0fc18564b545c82"}, "dwarfgen/dwarfgen.cc": {"bytes": 33454, "kind": "regular", "mode": 33188, "sha256": "67dc5a8f2cea1a213f67f42b33ae0f9e612f7ce09c3c0aeb7b39194f2d720190"}, "dwarfgen/fakemalloc.in": {"bytes": 2027, "kind": "regular", "mode": 33188, "sha256": "6901e640998d4ce68ab34376fa4c127873e737fd6cbf02f8aba7dc6f8ec8d41a"}, "dwarfgen/general.h": {"bytes": 2461, "kind": "regular", "mode": 33188, "sha256": "454ab8d0448a044ab94efd469fc43d2963ebe8a1ea82bb4e6fa1bba14fbd27db"}, "dwarfgen/irepattrtodbg.cc": {"bytes": 13619, "kind": "regular", "mode": 33188, "sha256": "6cb781d76b20271d8395a8a407526c399dcea4a6910c14ebdf67dc69c917266f"}, "dwarfgen/irepattrtodbg.h": {"bytes": 1726, "kind": "regular", "mode": 33188, "sha256": "5593c9b2d4b3a854bb93e89e2e375772bedfcc4983f3279a107c75a5ba4ee646"}, "dwarfgen/irepdie.h": {"bytes": 11523, "kind": "regular", "mode": 33188, "sha256": "4feecdbaae8ccab7452d338ab18dda8f7b5f5d59e36ba1e6cb505d7d0e5035d8"}, "dwarfgen/irepform.h": {"bytes": 24865, "kind": "regular", "mode": 33188, "sha256": "27cfc09fcf5cd2430485ded0528907ed1248d2584ed3f2b92f4b4c91927d2a23"}, "dwarfgen/irepframe.h": {"bytes": 6341, "kind": "regular", "mode": 33188, "sha256": "970cd9bb1330dfc4039df2bf3b15ad494fe93a35f0542b40e9d6b2828f8eddd1"}, "dwarfgen/irepline.h": {"bytes": 4026, "kind": "regular", "mode": 33188, "sha256": "a48999e9dc80c5b3ba86c558f5abdb3223cade8559185e932d8eb09ad7300715"}, "dwarfgen/irepmacro.h": {"bytes": 2241, "kind": "regular", "mode": 33188, "sha256": "b0af17bb6cd1aecac9a0c5a1782a00c4fe8523b108129e7fdb37ca41a5d1b2e8"}, "dwarfgen/ireppubnames.h": {"bytes": 3021, "kind": "regular", "mode": 33188, "sha256": "30ecda63ea1bb2c6f2f358f6867000eba3f76f8de9fec4eab4e0077bc0f9549f"}, "dwarfgen/irepresentation.h": {"bytes": 5628, "kind": "regular", "mode": 33188, "sha256": "5cb886463c9eeeea32f0725ac4e8e74bdded195ead187e51bfe452dc6ba776ca"}, "dwarfgen/ireptodbg.cc": {"bytes": 24315, "kind": "regular", "mode": 33188, "sha256": "f1ca58f70fd26c14aae025501494da83002272c6ff5fc33913ced333195e74e8"}, "dwarfgen/ireptodbg.h": {"bytes": 1613, "kind": "regular", "mode": 33188, "sha256": "b9380433649359ae4c756dd3d6963febd15547ae825e549e5336fc46d7193e9e"}, "dwarfgen/strtabdata.h": {"bytes": 3049, "kind": "regular", "mode": 33188, "sha256": "8abb4a7ed64c71beb6548dc06d0fb9f6788b49fd17f5606d3ddad31a48fc964f"}, "install-sh": {"bytes": 15155, "kind": "regular", "mode": 33261, "sha256": "fb968adf6c7fa83071ad294c8a5a13a63c92a8f109f78bae51a80d6eee59990d"}, "libdwarf": {"kind": "directory", "mode": 16832}, "libdwarf/CHANGES": {"bytes": 3902, "kind": "regular", "mode": 33188, "sha256": "7254f7cbbae80ae9d0991d80cf323d0f7db9f9670d206ecc832537eb336ec8d4"}, "libdwarf/CMakeLists.txt": {"bytes": 4959, "kind": "regular", "mode": 33188, "sha256": "801616d674612578cd7c2590b087153824659164ce620820db869b631863b74f"}, "libdwarf/CODINGSTYLE": {"bytes": 2776, "kind": "regular", "mode": 33188, "sha256": "88b0967538347b5ac4b4b5f5d9220830a3f14fc8d60c378bd2c6445a71caa1eb"}, "libdwarf/COPYING": {"bytes": 1035, "kind": "regular", "mode": 33188, "sha256": "b7af62004f2f2841f1b2ed1adb75de5f1bcf1101302dedba76b7c704bbaa35bb"}, "libdwarf/ChangeLog": {"bytes": 25284, "kind": "regular", "mode": 33188, "sha256": "bfd0916c4aced24d94e58d5d7bff7e0c97e2a07be15277826d87f52b17c7247e"}, "libdwarf/ChangeLog2006": {"bytes": 35540, "kind": "regular", "mode": 33188, "sha256": "07272bcbc453fad8d7a399391843f625e2f1fe784640f37eadd128dc311b5683"}, "libdwarf/ChangeLog2007": {"bytes": 12052, "kind": "regular", "mode": 33188, "sha256": "430e468c04b67db3fcb20ca4f4fc43872ba06e87206fb52ab5dc1d56bf6aa716"}, "libdwarf/ChangeLog2008": {"bytes": 14059, "kind": "regular", "mode": 33188, "sha256": "67b91de9f820882e726c8a1a0550807116aa37965eef84d1e58f791a4c64eede"}, "libdwarf/ChangeLog2009": {"bytes": 19039, "kind": "regular", "mode": 33188, "sha256": "c0e5a560c68def0a57a9c82797c5c9c33653dee135f50db4113bc8c3698135f4"}, "libdwarf/ChangeLog2010": {"bytes": 9210, "kind": "regular", "mode": 33188, "sha256": "4d44e9169fbf0dc05d1508f84eecfd2132395c5cabcb8bfa8c2af177114d0cac"}, "libdwarf/ChangeLog2011": {"bytes": 15955, "kind": "regular", "mode": 33188, "sha256": "4cdb9561069e9adf49701a929536b8a2b89a5c38eec294302905c1f5842b4b14"}, "libdwarf/ChangeLog2012": {"bytes": 7312, "kind": "regular", "mode": 33188, "sha256": "0280d9bbdaf8f93f0145d1f8bcb9a80b4c3f2fad36ee2b3a904d0f0c57169c94"}, "libdwarf/ChangeLog2013": {"bytes": 12389, "kind": "regular", "mode": 33188, "sha256": "852d2405f2c6a4a9395edb0274aa13113b7234179dbf542ca83bb1f9ba9a542d"}, "libdwarf/ChangeLog2014": {"bytes": 20524, "kind": "regular", "mode": 33188, "sha256": "690f0063ac312d03fb48e2e34a49e2f49de2981584353a191fb4f99cb399ea70"}, "libdwarf/ChangeLog2015": {"bytes": 38199, "kind": "regular", "mode": 33188, "sha256": "97184fa7aae50c5fe00bde8c382fc602e42380216d7963623a8330056779f72c"}, "libdwarf/ChangeLog2016": {"bytes": 45083, "kind": "regular", "mode": 33188, "sha256": "26f91e1b8460a2322728aa523d788a4d724a4b1f9bcded08bbe8c199c1dcb3c0"}, "libdwarf/ChangeLog2017": {"bytes": 18495, "kind": "regular", "mode": 33188, "sha256": "5b16f7eed48ba894937b5bfaade795603655e692f18a6a877922c9a9385e74f4"}, "libdwarf/LGPL.txt": {"bytes": 26436, "kind": "regular", "mode": 33188, "sha256": "5df07007198989c622f5d41de8d703e7bef3d0e79d62e24332ee739a452af62a"}, "libdwarf/LIBDWARFCOPYRIGHT": {"bytes": 1567, "kind": "regular", "mode": 33188, "sha256": "d5a231dfc6f3f739be86bf06e726e7599a07ccadf775e104b633190086392c73"}, "libdwarf/Makefile.am": {"bytes": 4934, "kind": "regular", "mode": 33188, "sha256": "c761f4d7ed88c86de26e62853295c7a9130a53d0f5b141bb06748204a1a40c48"}, "libdwarf/Makefile.in": {"bytes": 121736, "kind": "regular", "mode": 33188, "sha256": "d7a4e95982cb051752e89856db2708f6ab6dfb0931e4a828e6d8014a70759353"}, "libdwarf/NEWS": {"bytes": 25256, "kind": "regular", "mode": 33188, "sha256": "6a7341d0b18379b72192db5d8bdf4b85b680397525458db1bb598fdd59a221ec"}, "libdwarf/README": {"bytes": 10415, "kind": "regular", "mode": 33188, "sha256": "6db9a57ab3d92d01d2b04dc7617dd43844429ffaa5296d85bc51b5235bd4c0d4"}, "libdwarf/checkexamples.c": {"bytes": 49059, "kind": "regular", "mode": 33188, "sha256": "604d9b6a80a590992db350c3b042293d0ac7afa53121cffda1d8d23ba34e95aa"}, "libdwarf/config.h.in.cmake": {"bytes": 5022, "kind": "regular", "mode": 33188, "sha256": "58ffc3c99df0bdeee9182d09a716b341e7bd93ed9bc20356709e668f1edf3c68"}, "libdwarf/configure.cmake": {"bytes": 5670, "kind": "regular", "mode": 33188, "sha256": "e78550708d7037ad561f5a47b15f410b8ecb1bfa5b65e5649ad30d6ca25b4e85"}, "libdwarf/dw-linetableheader.txt": {"bytes": 1635, "kind": "regular", "mode": 33188, "sha256": "7c6bd92c0215f12a405dcb87db33fa630b84568a084df294c5c95f310e75b717"}, "libdwarf/dwarf.h": {"bytes": 70048, "kind": "regular", "mode": 33188, "sha256": "de2e12d52dcfd3395c56d5231917df03e2d6414d29e43a62f908aa3f27a8bf76"}, "libdwarf/dwarf_abbrev.c": {"bytes": 9200, "kind": "regular", "mode": 33188, "sha256": "8b230f5c966c60825a388e8a02528ebde6cfe2ba3657b682a058f24566ed2137"}, "libdwarf/dwarf_abbrev.h": {"bytes": 1868, "kind": "regular", "mode": 33188, "sha256": "dadf913e76d6ac7f5dd2fb9385e0ba5e4790a06e8341ecff549777a5ff674669"}, "libdwarf/dwarf_alloc.c": {"bytes": 24442, "kind": "regular", "mode": 33188, "sha256": "ff054e1955fc6b1b588db7cded04fc9333b1789b56656da71b5661888c261d91"}, "libdwarf/dwarf_alloc.h": {"bytes": 1583, "kind": "regular", "mode": 33188, "sha256": "ba54ba69ee91aa07d103c66e0eedc524b3e31fa35f20dc6626c10801b6f84162"}, "libdwarf/dwarf_arange.c": {"bytes": 22468, "kind": "regular", "mode": 33188, "sha256": "dcadd937640c9047bf8ed77d8a2a9b7b18d1cfaf8676fd080500d06a46817814"}, "libdwarf/dwarf_arange.h": {"bytes": 2017, "kind": "regular", "mode": 33188, "sha256": "ddb3538a097b4c5015d4047a1a8df969516d961e7d78a0114dbca2ea4ccddb9e"}, "libdwarf/dwarf_base_types.h": {"bytes": 5198, "kind": "regular", "mode": 33188, "sha256": "92153201eb67d3a4cef74b258ac50a4e91d71f590cad41659754cf0a9b455c0f"}, "libdwarf/dwarf_die_deliv.c": {"bytes": 77611, "kind": "regular", "mode": 33188, "sha256": "4363284e3102d922df3d764ece4444f12cbcbce64afa016024eb572b1fc6b681"}, "libdwarf/dwarf_die_deliv.h": {"bytes": 1712, "kind": "regular", "mode": 33188, "sha256": "a2dfc8c6aa7522f2beb4a8b4893a73d9c53f6451b4708f89b669c199b416feaf"}, "libdwarf/dwarf_dnames.c": {"bytes": 40430, "kind": "regular", "mode": 33188, "sha256": "dc0aae21d5b229316461c986feb613a666d93528701ed5be8ce83b0e684f3b6c"}, "libdwarf/dwarf_dnames.h": {"bytes": 3523, "kind": "regular", "mode": 33188, "sha256": "764f67e98ed1ce0fc5845d0c7afdde22db6bca05f5da25575f209c44a5514166"}, "libdwarf/dwarf_dsc.c": {"bytes": 8501, "kind": "regular", "mode": 33188, "sha256": "c22833af988762452b62ddf18e06f78582dd8a838bed0a95609ea371c3329fe1"}, "libdwarf/dwarf_dsc.h": {"bytes": 2102, "kind": "regular", "mode": 33188, "sha256": "1d85655b1fdd10111b71991aa8d936d577765eaba740d065795ce611915a9dd2"}, "libdwarf/dwarf_elf_access.c": {"bytes": 42641, "kind": "regular", "mode": 33188, "sha256": "d1bb8fdfe106153632ba4d9b16c1d300832e72204b08223d32725f0eaa5d12c4"}, "libdwarf/dwarf_elf_access.h": {"bytes": 1581, "kind": "regular", "mode": 33188, "sha256": "af1365ec23b1d42f95f9607a98a2ad53efee510d1b0a1c3f65e7a9b1fee53907"}, "libdwarf/dwarf_errmsg_list.h": {"bytes": 23826, "kind": "regular", "mode": 33188, "sha256": "9fc6a94752139023da9adee5a8b10a8867a89ceb1d30ef14f2b520d0c72452ff"}, "libdwarf/dwarf_error.c": {"bytes": 4558, "kind": "regular", "mode": 33188, "sha256": "946fbc17217704d86f9a39828038e2145dc602a44347fe863e6c86d6d50c8ab3"}, "libdwarf/dwarf_error.h": {"bytes": 2009, "kind": "regular", "mode": 33188, "sha256": "32582da487788e9de1387b69ba3c359ebf13766feff4327c7310b270d01ed315"}, "libdwarf/dwarf_form.c": {"bytes": 51809, "kind": "regular", "mode": 33188, "sha256": "f598a98516027fe8ab3f6b04ba04752a6add612db928ca888af35f1465214b80"}, "libdwarf/dwarf_frame.c": {"bytes": 90115, "kind": "regular", "mode": 33188, "sha256": "4610b3489884998396177cb1ed099ede3ccfa8b7c2c82ba754da3b5a602c3db0"}, "libdwarf/dwarf_frame.h": {"bytes": 16108, "kind": "regular", "mode": 33188, "sha256": "63c8e54d149a3f061f426682cbb8e2760cbe233b2892e6f669de3b2126c06d19"}, "libdwarf/dwarf_frame2.c": {"bytes": 59618, "kind": "regular", "mode": 33188, "sha256": "1d704cd1e81748d9c952fb620ed2d3aae23377dadada6e5b842084706d096a9a"}, "libdwarf/dwarf_funcs.c": {"bytes": 3512, "kind": "regular", "mode": 33188, "sha256": "166922c611a69355d247f85d78d2a1b4ba3cde8c25bcde6137562b3073d287f9"}, "libdwarf/dwarf_funcs.h": {"bytes": 1199, "kind": "regular", "mode": 33188, "sha256": "e252fcbf6dd969c9387bc0601b120891407661bc708722550e8d3f3121813811"}, "libdwarf/dwarf_gdbindex.c": {"bytes": 17524, "kind": "regular", "mode": 33188, "sha256": "2643d3b6f7b0efc7ff473da2c135082c773443276a41aea135eb260b10af9561"}, "libdwarf/dwarf_gdbindex.h": {"bytes": 2920, "kind": "regular", "mode": 33188, "sha256": "5463edba8c8e41249343ed1f96bf8f7c561d2c348caa907d620289ad0306512f"}, "libdwarf/dwarf_global.c": {"bytes": 20654, "kind": "regular", "mode": 33188, "sha256": "1bf1a684a1bf75c9bba4250bb90efbb08a2b08bde12a464b8364358716811061"}, "libdwarf/dwarf_global.h": {"bytes": 3677, "kind": "regular", "mode": 33188, "sha256": "c0e63f0758ef411f7a52f184cfea3b7abd992fb46bad3e847d44331ded93ec01"}, "libdwarf/dwarf_groups.c": {"bytes": 10726, "kind": "regular", "mode": 33188, "sha256": "a6db658b44884641821cbc2d01db58da5356eb0ca74e7e27aa3ff46fd89875cc"}, "libdwarf/dwarf_harmless.c": {"bytes": 7322, "kind": "regular", "mode": 33188, "sha256": "b5c6d4850447fec7bfd62a85f097d1967944b032f03d579ccad8136b18ed1900"}, "libdwarf/dwarf_harmless.h": {"bytes": 1206, "kind": "regular", "mode": 33188, "sha256": "6c18d75192ec6a1193e96e6cc839c9d64a7e13095461332c9af0b3ff8791b3a8"}, "libdwarf/dwarf_incl.h": {"bytes": 1741, "kind": "regular", "mode": 33188, "sha256": "f4123eb2bce096e7c4159d3de7683c3013b4aec8da3fffe6700a21977c540d9c"}, "libdwarf/dwarf_init_finish.c": {"bytes": 68197, "kind": "regular", "mode": 33188, "sha256": "a2275efe2eb769d438fb8ff58f6227bb71de510400ece0365938cd1a35c603cf"}, "libdwarf/dwarf_leb.c": {"bytes": 13516, "kind": "regular", "mode": 33188, "sha256": "1f42aa202a8ec28e1162ece3532c4fa1eb59257d1cadc0e7953d6e428845b3a4"}, "libdwarf/dwarf_line.c": {"bytes": 63841, "kind": "regular", "mode": 33188, "sha256": "87b214fdbc0fce3b6f5bc78efe2d31c061c95c076b74df19eb5343d4f46d2e0f"}, "libdwarf/dwarf_line.h": {"bytes": 16231, "kind": "regular", "mode": 33188, "sha256": "aac266f4ef108978c706c73907e4fe715401292b58f9690123de44bddc9aba8c"}, "libdwarf/dwarf_line_table_reader_common.h": {"bytes": 76313, "kind": "regular", "mode": 33188, "sha256": "f96c755908ba0c20148e77b565a550003186bfc1a5366c6cd00b01cb346130a2"}, "libdwarf/dwarf_loc.c": {"bytes": 53476, "kind": "regular", "mode": 33188, "sha256": "ec15df5e8a1b23b3c34354e88e17cd71da2a52ef83e54520871a5eb2116427fe"}, "libdwarf/dwarf_loc.h": {"bytes": 5319, "kind": "regular", "mode": 33188, "sha256": "0f703b39b9e34322974da0da7e1d749b82058a309931396695bc5facf99916b7"}, "libdwarf/dwarf_loc2.h": {"bytes": 30046, "kind": "regular", "mode": 33188, "sha256": "919df595870e13357d98a782b27748bcda4f03ca72ddaee1b2d56551f2c7e193"}, "libdwarf/dwarf_macro.c": {"bytes": 16042, "kind": "regular", "mode": 33188, "sha256": "1774851fb5973fa7437948003c63c765f2693aa4bcdfb259e2b5e69a50f67037"}, "libdwarf/dwarf_macro.h": {"bytes": 1167, "kind": "regular", "mode": 33188, "sha256": "4ae56e804100e428cd56188e0f066131628d6371e4599e7b26ae07b1452c628e"}, "libdwarf/dwarf_macro5.c": {"bytes": 49362, "kind": "regular", "mode": 33188, "sha256": "83eb9ac0d6575a73b0bbd9e011a634a3ed60807e0db0e9bf94e54fa2c83cfd51"}, "libdwarf/dwarf_macro5.h": {"bytes": 4647, "kind": "regular", "mode": 33188, "sha256": "6010e68357524ebfc5c99eb69cd4fecd94dff8bb1a00f78755286a3b2597ef02"}, "libdwarf/dwarf_opaque.h": {"bytes": 34802, "kind": "regular", "mode": 33188, "sha256": "044197a8d89a4f0430e169d2fd454ff225ff850b56e2d60973e999f76175c75c"}, "libdwarf/dwarf_original_elf_init.c": {"bytes": 7420, "kind": "regular", "mode": 33188, "sha256": "11bd282140424fb9adcfdb26e5508ed78b991229072f93041158406c963971ba"}, "libdwarf/dwarf_print_lines.c": {"bytes": 22829, "kind": "regular", "mode": 33188, "sha256": "cf61a8e1c825ffb838070e625c51e78eed73ef47f93ae1d434c7af30315555bd"}, "libdwarf/dwarf_pubtypes.c": {"bytes": 3758, "kind": "regular", "mode": 33188, "sha256": "87ba89f767bc62274258ca5206faaef9e5e67fd145652d159eac77625c0850fe"}, "libdwarf/dwarf_query.c": {"bytes": 54499, "kind": "regular", "mode": 33188, "sha256": "a88107fe8b1897cb09f61457c02163824c549746cb605eaef541a4f5eb3b4704"}, "libdwarf/dwarf_ranges.c": {"bytes": 8156, "kind": "regular", "mode": 33188, "sha256": "b1a6c51abdd44734a353ead18388be075f52cca67b4c4eb6d279989537583c3c"}, "libdwarf/dwarf_reloc_386.h": {"bytes": 3686, "kind": "regular", "mode": 33188, "sha256": "3d08af044c956aef9e52fb79efd1aec60fab33fbf5a2f1d49a396a1a8da6c633"}, "libdwarf/dwarf_reloc_arm.h": {"bytes": 12503, "kind": "regular", "mode": 33188, "sha256": "14a5306a89b09fd028c11d0e9f8669ecf73a3ff123473c2e97e53028368547d2"}, "libdwarf/dwarf_reloc_mips.h": {"bytes": 4641, "kind": "regular", "mode": 33188, "sha256": "e3aa52f3b30842e8ae5e4debee2bd060fe30e522f63211f847f9d53918ad5d59"}, "libdwarf/dwarf_reloc_ppc.h": {"bytes": 11006, "kind": "regular", "mode": 33188, "sha256": "b35933e026834f90ac2b1011632e6bde7f023009fd5d6e617fd9e8a70fba7403"}, "libdwarf/dwarf_reloc_ppc64.h": {"bytes": 14150, "kind": "regular", "mode": 33188, "sha256": "a39998c88c65245a2d3800dd0e7a55660ca57c1ae1b6e84237838511affb2976"}, "libdwarf/dwarf_reloc_x86_64.h": {"bytes": 6239, "kind": "regular", "mode": 33188, "sha256": "92a3657ab8610d8670bf3e99c56d5c03ba20c15713a73c7d42c33e9f72c600da"}, "libdwarf/dwarf_str_offsets.c": {"bytes": 12571, "kind": "regular", "mode": 33188, "sha256": "17cfffd60fec15efa992f13ef216f6a796cce1f265ac6dccd4d286bd4ceea5cd"}, "libdwarf/dwarf_str_offsets.h": {"bytes": 2239, "kind": "regular", "mode": 33188, "sha256": "6227ff205b597174315837c78874e2790760d5f3ffcf4c5dc591c80be2d32e1a"}, "libdwarf/dwarf_string.c": {"bytes": 2644, "kind": "regular", "mode": 33188, "sha256": "5fd027f5cf650c60cc34887d25102990ff39e7f322cfa0085f22f35c2dc25953"}, "libdwarf/dwarf_stubs.c": {"bytes": 1506, "kind": "regular", "mode": 33188, "sha256": "a21d5f6b8504417cf62c3e0ba562b8c37ca74454405a74a3e1dafa256ce97b60"}, "libdwarf/dwarf_test_errmsg_list.c": {"bytes": 8245, "kind": "regular", "mode": 33188, "sha256": "dd3dd5b6a7b8ac747ae349b57cae9c8176a86fcf9d7f0fedd393a3cc5e22e664"}, "libdwarf/dwarf_tied.c": {"bytes": 11623, "kind": "regular", "mode": 33188, "sha256": "6d69824b8d73d28e18b641e34b65c22743a31828a641d19172d91e1eb3ae10de"}, "libdwarf/dwarf_tsearch.h": {"bytes": 4345, "kind": "regular", "mode": 33188, "sha256": "ad875b1cb51e746d525e9ef8181da4dd13bcc003fc11ba2f6c44065c09d7d244"}, "libdwarf/dwarf_tsearchhash.c": {"bytes": 19100, "kind": "regular", "mode": 33188, "sha256": "fd19401b8e26e5b798207a45a6c37f9bd9197433d01f17d6ce90333b8fdd6bb8"}, "libdwarf/dwarf_types.c": {"bytes": 3533, "kind": "regular", "mode": 33188, "sha256": "68041341ac9041c58c37664030b01f6a1586a40c27a2f6a2073a097fb479992f"}, "libdwarf/dwarf_types.h": {"bytes": 1194, "kind": "regular", "mode": 33188, "sha256": "48118637710ceabf3297456d2bb897ccf76afcadcd1695c303395dc954972a9a"}, "libdwarf/dwarf_util.c": {"bytes": 42311, "kind": "regular", "mode": 33188, "sha256": "3fdc80b2f2b34e823a4f010988174a7923121d809b37d89a95cf5f592846fd5d"}, "libdwarf/dwarf_util.h": {"bytes": 21104, "kind": "regular", "mode": 33188, "sha256": "a91e53bf926b5939530a6549b8dcb1033d452a689111cf80f16f5bf80e1db4c2"}, "libdwarf/dwarf_vars.c": {"bytes": 3509, "kind": "regular", "mode": 33188, "sha256": "7c7b442b073d16eeed236269a9a09b78b46462668a4f1cf767b5277bb05a423a"}, "libdwarf/dwarf_vars.h": {"bytes": 1192, "kind": "regular", "mode": 33188, "sha256": "89ad2b657f5003771a8ef3faf0baafc8b291a43a559601a5f20e0cbd69b207ce"}, "libdwarf/dwarf_weaks.c": {"bytes": 3480, "kind": "regular", "mode": 33188, "sha256": "f0b91c770563e0bb95f83f525f60a7c641f2535255acb745368888d1c5963365"}, "libdwarf/dwarf_weaks.h": {"bytes": 1194, "kind": "regular", "mode": 33188, "sha256": "626f49baec85f262f3333d359e0d177fbae86ddb186b652f9cf52ced523f9423"}, "libdwarf/dwarf_xu_index.c": {"bytes": 19766, "kind": "regular", "mode": 33188, "sha256": "c1b2616c5f8b217a6bdeca92439827006c045eb3782ce5057a6168157849b395"}, "libdwarf/dwarf_xu_index.h": {"bytes": 2023, "kind": "regular", "mode": 33188, "sha256": "e84a3653ee64c80b47174f91d2faaeb5c6704c07f9994a2d333c012f6fe69702"}, "libdwarf/dwgetopt.c": {"bytes": 11288, "kind": "regular", "mode": 33188, "sha256": "2858e2e380ab38bd33d5e602f84b4a71743c664461395135572318a599297863"}, "libdwarf/dwgetopt.h": {"bytes": 3255, "kind": "regular", "mode": 33188, "sha256": "5d8fe20b4d2dc5e0c63608093e27bc0fe562c554a778e7ea89711b942f30bea3"}, "libdwarf/gennames.c": {"bytes": 20000, "kind": "regular", "mode": 33188, "sha256": "68432b165c2f9ca46168ce74bbaa1b0a490149ed4943b69a07aa727b28de01f9"}, "libdwarf/libdwarf.h.in": {"bytes": 171097, "kind": "regular", "mode": 33188, "sha256": "727cd79fecf8f9b469eb20fd0d1cf4bd3102b1d96a77b3320a99d323763f527c"}, "libdwarf/libdwarf2.1.mm": {"bytes": 399967, "kind": "regular", "mode": 33188, "sha256": "0003abc35399d7d7d4785008b2532ace51c4d4cd5a0468498a64372d4e669371"}, "libdwarf/libdwarf2.1.pdf": {"bytes": 451132, "kind": "regular", "mode": 33188, "sha256": "05e4d9975c7e45ad9a2dffc118f17b693f4ade74ad2ea8e2e69d3e9dd717f011"}, "libdwarf/libdwarf2p.1.mm": {"bytes": 105911, "kind": "regular", "mode": 33188, "sha256": "70ba97a058207cec4e47487fb33f42e1171988dc08b19defa4b373bf1eeacbb7"}, "libdwarf/libdwarf2p.1.pdf": {"bytes": 139441, "kind": "regular", "mode": 33188, "sha256": "31980c22115632ef7a42ce353f3f58a59a76cb99c94874ac804056a7b74788ce"}, "libdwarf/libdwarf_version.h": {"bytes": 220, "kind": "regular", "mode": 33188, "sha256": "234da16645fdacdd93449f3fa387b5102bbabd7f836ecc6d6ecf7c0c2fcd8b65"}, "libdwarf/libdwarfdefs.h": {"bytes": 2490, "kind": "regular", "mode": 33188, "sha256": "2865de22dcc3bc12cc5d8a79f5add9621219594e1192b0802c896b128608be0e"}, "libdwarf/malloc_check.c": {"bytes": 9503, "kind": "regular", "mode": 33188, "sha256": "edf7040bc0c9da80172b6066219047d964dc30e80f2ad231ae0ba0bc135c443e"}, "libdwarf/malloc_check.h": {"bytes": 1966, "kind": "regular", "mode": 33188, "sha256": "52e42acd322a41c574ce23019f2ac5f3a72a41a1ebac7d63ec41f15b4812bd5a"}, "libdwarf/mips_extensions.mm": {"bytes": 48943, "kind": "regular", "mode": 33188, "sha256": "fbb9959b951c5b9c377860759477444afa0411cd23f4375cea6b6a7f2d57a01e"}, "libdwarf/mips_extensions.pdf": {"bytes": 57910, "kind": "regular", "mode": 33188, "sha256": "247d43a5347713ecdcdbce72028cd0e5bdbe5e412ba589de8dfbf154ea5aebad"}, "libdwarf/pdfbld.sh": {"bytes": 485, "kind": "regular", "mode": 33261, "sha256": "74a90d6970fa682d3fa91c50221c2c2997315df0c374d1c18c7a67e09f21000e"}, "libdwarf/pro_alloc.c": {"bytes": 5719, "kind": "regular", "mode": 33188, "sha256": "60d0b02f59e2d57b3f87ef52badb84338845719eb3afe6c78492593b2296fb64"}, "libdwarf/pro_alloc.h": {"bytes": 1312, "kind": "regular", "mode": 33188, "sha256": "7b6ee7e7d5013ade58733debddce081aa1a16f979380b3657852694f129c60c7"}, "libdwarf/pro_arange.c": {"bytes": 10380, "kind": "regular", "mode": 33188, "sha256": "fa73cb495e5593c7a894cc914692c94b4a8f8dec199c6ec503fbc48943b49d6c"}, "libdwarf/pro_arange.h": {"bytes": 1725, "kind": "regular", "mode": 33188, "sha256": "d632b3912b204caeb5988d54f846d61b77a9f18199c542667a4c84495225c5eb"}, "libdwarf/pro_die.c": {"bytes": 24293, "kind": "regular", "mode": 33188, "sha256": "9580e1f1f8b38ae7e9b51b30abc88b9c843e4ee629e6df0dff739dfbe674050e"}, "libdwarf/pro_die.h": {"bytes": 2344, "kind": "regular", "mode": 33188, "sha256": "8faf96aeb5e51f7d8c1e88778c1403aba5dfa62bff3fb959360ceb7e575b2f9e"}, "libdwarf/pro_dnames.c": {"bytes": 1909, "kind": "regular", "mode": 33188, "sha256": "ce9a86acd237ab1d3cc548c4c16e52f810afc85d78caf9de66da5c90c6076c22"}, "libdwarf/pro_dnames.h": {"bytes": 2589, "kind": "regular", "mode": 33188, "sha256": "36b4bdd2e1ef4f7e780ef0e655c857fe60ff57ed440ce089d8279027cdc8556b"}, "libdwarf/pro_encode_nm.c": {"bytes": 3064, "kind": "regular", "mode": 33188, "sha256": "4317df6558992b6b8f642fb0ccf35efca00f9cdb96ef63a2b1f5448034c46780"}, "libdwarf/pro_encode_nm.h": {"bytes": 1431, "kind": "regular", "mode": 33188, "sha256": "0aff6bfe4556e74be397c7fb351eae73864a9400c053275cd9803877534bd620"}, "libdwarf/pro_error.c": {"bytes": 3258, "kind": "regular", "mode": 33188, "sha256": "0034a5ac712c0fe6ca01ec59daacb925925c3b4e0194e8750c00ae9d36815db0"}, "libdwarf/pro_error.h": {"bytes": 1564, "kind": "regular", "mode": 33188, "sha256": "f42f9f8a01890ccf19b14dd8da3569d970fec82de20a28465f609feaded3c6b5"}, "libdwarf/pro_expr.c": {"bytes": 16276, "kind": "regular", "mode": 33188, "sha256": "c3b14d1aefa57fd908960d399257b11be76564559c0348251e4708fec5f1bc82"}, "libdwarf/pro_expr.h": {"bytes": 1349, "kind": "regular", "mode": 33188, "sha256": "f669356cbee7a2f09ea57803915cbbbb587a232d876caf97b6457fcd65e27410"}, "libdwarf/pro_finish.c": {"bytes": 3155, "kind": "regular", "mode": 33188, "sha256": "66374ccc1f20d78e2e2db36027df7296bc5eff2603bacd9d400e4bb83bd70e1d"}, "libdwarf/pro_forms.c": {"bytes": 38753, "kind": "regular", "mode": 33188, "sha256": "74669fb8f6d5ac92557b13f4aa8de160e47cf5d8d2f4681e1ff9c3c171168461"}, "libdwarf/pro_frame.c": {"bytes": 18979, "kind": "regular", "mode": 33188, "sha256": "3ce68e6c05cd9b328a2a66ddf25160c37da442ce50d22c3fae95e5329ccc97e2"}, "libdwarf/pro_frame.h": {"bytes": 3784, "kind": "regular", "mode": 33188, "sha256": "afaa4594428008ddd0031436c8f2fdc5b152523a478ec663db18bdf76c9360ce"}, "libdwarf/pro_funcs.c": {"bytes": 1728, "kind": "regular", "mode": 33188, "sha256": "0d9e142b5a50e9cb6b41c4d6869d34605cc19867a6b640d2ab1eb22591c0c13d"}, "libdwarf/pro_incl.h": {"bytes": 2748, "kind": "regular", "mode": 33188, "sha256": "9d03145275cdd5e789c8ee7380b26ab348c5658153146b20dcdfe5b4c99b67aa"}, "libdwarf/pro_init.c": {"bytes": 13572, "kind": "regular", "mode": 33188, "sha256": "69a912bdd67841ece8cbb53047230900761ab7428428f48ab864e87b49f6ed2f"}, "libdwarf/pro_line.c": {"bytes": 12683, "kind": "regular", "mode": 33188, "sha256": "f5acd645cbe40e53a199ac2f3486f93704b718f8a78a1055d9d07f41fb25f20c"}, "libdwarf/pro_line.h": {"bytes": 3458, "kind": "regular", "mode": 33188, "sha256": "b5f409b78637f62056c9a39e346e4288949f1dc7a1a8c4ba6cd31a770b5a685f"}, "libdwarf/pro_macinfo.c": {"bytes": 13478, "kind": "regular", "mode": 33188, "sha256": "a048082930d19d84437b7560cbfdff0865f246c65ba1c35c5436539a5009d006"}, "libdwarf/pro_macinfo.h": {"bytes": 1203, "kind": "regular", "mode": 33188, "sha256": "a8af44d05b3e6cd49343d52e3efa8cae1872250c0fda4f44007735d1ce7aa744"}, "libdwarf/pro_opaque.h": {"bytes": 20694, "kind": "regular", "mode": 33188, "sha256": "b02f28ce4fa7017016b1a65d0f5e6ded9176356099564846179012477ab9b2de"}, "libdwarf/pro_pubnames.c": {"bytes": 1957, "kind": "regular", "mode": 33188, "sha256": "c35176559684ed429bf945a55c48a3a22d3dae82bb66deefa4cbb436b17c0571"}, "libdwarf/pro_reloc.c": {"bytes": 7736, "kind": "regular", "mode": 33188, "sha256": "b4169c0a2683485958be5b9f4eebf10257533306ee4257f9da4cf910a5534951"}, "libdwarf/pro_reloc.h": {"bytes": 1394, "kind": "regular", "mode": 33188, "sha256": "339483694e5b7eb812b6794b364e296d573f6e9521b37f88735dbd9e5aaa77dc"}, "libdwarf/pro_reloc_stream.c": {"bytes": 8377, "kind": "regular", "mode": 33188, "sha256": "7708e9c02300895671d6237ebe72307d17e4c3550823a30f627651df92b6be0a"}, "libdwarf/pro_reloc_stream.h": {"bytes": 1837, "kind": "regular", "mode": 33188, "sha256": "6f8c0baf6f86005c1cfb1d5ac1816987fa98c6c0f4dd53d9dc545f2946185f81"}, "libdwarf/pro_reloc_symbolic.c": {"bytes": 9381, "kind": "regular", "mode": 33188, "sha256": "9327368aa7973d943b84494ac0e2f1d96880057da9ac3e1a3becb15ac0cd7d11"}, "libdwarf/pro_reloc_symbolic.h": {"bytes": 1633, "kind": "regular", "mode": 33188, "sha256": "50d00a5c98b915511052653040338f1cedb79d39da07a1912bf81127a5bc4ee5"}, "libdwarf/pro_section.c": {"bytes": 117417, "kind": "regular", "mode": 33188, "sha256": "fc6b03a15f9f07cf7fe8c43065c22dcfe4908d195ad1222d2f0e6e4d37bfba8c"}, "libdwarf/pro_section.h": {"bytes": 3621, "kind": "regular", "mode": 33188, "sha256": "db5f59c61859cbb9be26608f18b90222b2310e520f31692234cf7c68db300154"}, "libdwarf/pro_types.c": {"bytes": 8352, "kind": "regular", "mode": 33188, "sha256": "04d4553dc58f4966af6cf61c8063812a517d9880db180475d570686e6082d67b"}, "libdwarf/pro_types.h": {"bytes": 1303, "kind": "regular", "mode": 33188, "sha256": "c3f08ccde823c9dc139d3427d5de0c84a89d1cadd07adf83e6e6921eb307fd84"}, "libdwarf/pro_util.h": {"bytes": 1477, "kind": "regular", "mode": 33188, "sha256": "daef0e30ca86f3792eb60c4247ad1378d1aedf9b81c17ab1bf11042fa2b7fe19"}, "libdwarf/pro_vars.c": {"bytes": 1718, "kind": "regular", "mode": 33188, "sha256": "1913b363faba699e375b500cdee54a89231c0709fc2b4c1eb310005cc29ed0e3"}, "libdwarf/pro_weaks.c": {"bytes": 1716, "kind": "regular", "mode": 33188, "sha256": "99f0a0df0b163c0ba0f3f53f0623a3ae03d9afad3da80445449371234579d980"}, "libdwarf/runtests.sh": {"bytes": 916, "kind": "regular", "mode": 33261, "sha256": "3071c92a2e2ea7d66e319a37d3f49438825eb288b3cb53fc1b9a4ad2f3755a70"}, "ltmain.sh": {"bytes": 324404, "kind": "regular", "mode": 33188, "sha256": "2304d53af1f63b76a11651efdd18578adf2bda1ffc2c257100cba374b55f284b"}, "m4": {"kind": "directory", "mode": 16832}, "m4/ax_prog_cc_for_build.m4": {"bytes": 4035, "kind": "regular", "mode": 33188, "sha256": "d1c6a543a8ef0a3c4c4595304306640beefdfb95b51c02588dd1f9f4b1b199f2"}, "m4/dw_compiler.m4": {"bytes": 2487, "kind": "regular", "mode": 33188, "sha256": "8b21a47feeb3c188ec224f35008f9839c3f96b180d99e1f1ac84011004688b13"}, "m4/libtool.m4": {"bytes": 306377, "kind": "regular", "mode": 33188, "sha256": "b536dbb2ebd38ef29247623db961d36f1d0bfbfde40f7c1bf774833a9067ebc5"}, "m4/ltoptions.m4": {"bytes": 14514, "kind": "regular", "mode": 33188, "sha256": "e77ebba8361b36f14b4d0927173a034b98c5d05049697a9ded84d85eb99a7990"}, "m4/ltsugar.m4": {"bytes": 4384, "kind": "regular", "mode": 33188, "sha256": "5a6735cda60e0ba0d1b706c0ef648f5d096298da46daefd9cdecdb6a0f4584d3"}, "m4/ltversion.m4": {"bytes": 699, "kind": "regular", "mode": 33188, "sha256": "a27b754709de61575197bf5a980696c98ae49da3f92f0de8ee7f42dd543b7465"}, "m4/lt~obsolete.m4": {"bytes": 6140, "kind": "regular", "mode": 33188, "sha256": "26fa3285c35dd6ab00ed1e466ba92a17e4655e01897731ec18a587a4cf5e4f8d"}, "missing": {"bytes": 6872, "kind": "regular", "mode": 33261, "sha256": "b1a337b731bbb58846d31ca2f5143c293a455fa41b481e236e89a9016d96b034"}, "scripts": {"kind": "directory", "mode": 16832}, "scripts/BLDLIBDWARF": {"bytes": 951, "kind": "regular", "mode": 33261, "sha256": "44204727ceeac5012281b19bcb3acf778f5ba2b69cfe0301c3dd596ce0bfaebf"}, "scripts/BLDLIBDWARFTAR": {"bytes": 1656, "kind": "regular", "mode": 33261, "sha256": "b78b85e767b477227fecf35a1505814ca6e1444640bf8e8358299f1fddec01a5"}, "scripts/BLDTESTDIR": {"bytes": 4205, "kind": "regular", "mode": 33188, "sha256": "8eccd568fddd3cef86a37d3336b43d15b9004c993a33f58745fddc44a081af45"}, "scripts/CLEANUP": {"bytes": 861, "kind": "regular", "mode": 33188, "sha256": "f243ebaf5044ceb15512d350fae6986d7c9347e33ea70eb86546b707ffe58368"}, "scripts/CPTARTOWEBDIR": {"bytes": 650, "kind": "regular", "mode": 33261, "sha256": "52791eab0e846ac9fb882f2411d33cac4c886f213632f210518e00c0048a6c96"}, "scripts/CPTOPUBLIC": {"bytes": 1316, "kind": "regular", "mode": 33261, "sha256": "ebc0546a9431a8db5774245ef65afad2d9c9ccf432f686468abccfc10aaf371c"}, "scripts/CREATINGARELEASE": {"bytes": 3506, "kind": "regular", "mode": 33188, "sha256": "52d4fdef91edb81cd1083df2b74ad304b87b5e6b3b63a78c3dd29aa060f2ee5b"}, "scripts/ChangeLog": {"bytes": 696, "kind": "regular", "mode": 33188, "sha256": "2d13c6c63fc240fcb601f8a6ee97f5a0ad0d7033f644838d48b1dd2627b07a5f"}, "scripts/FIX-CONFIGURE-TIMES": {"bytes": 1982, "kind": "regular", "mode": 33188, "sha256": "4e680ecf645cd1b5996e452a4128617d2bd75211803cc2a6410b2ae7dcd9f47f"}, "scripts/GETTOTOP": {"bytes": 841, "kind": "regular", "mode": 33188, "sha256": "c9dff99747b95a006b78b203c800f2a55dfee813fbd6f284a6dc8797519682ef"}, "scripts/REBLDLIBDWARF": {"bytes": 962, "kind": "regular", "mode": 33261, "sha256": "37b9a0203ff4bac8dd68c2ace39e4e055c7488b54d122b0a2069ebb6d7a87b68"}, "scripts/SETUP_MASTER_TREE": {"bytes": 3238, "kind": "regular", "mode": 33188, "sha256": "93d069bf0459da5b6d13d51d5d290ae6eafd56d34b4fb0ddadb061f9c83ad395"}, "scripts/UPD.awk": {"bytes": 248, "kind": "regular", "mode": 33188, "sha256": "51d57727042c7a16dd2ae9b5f681a047d2a7348bfc60de4f36e2754f5d0e5401"}, "scripts/UPDATEDWARFDUMPVERSION.sh": {"bytes": 1101, "kind": "regular", "mode": 33188, "sha256": "034aae032d225587b297aa3abd6e42362d9d16f649504302ce401cb5d07b63c1"}, "scripts/buildandreleasetest.sh": {"bytes": 2150, "kind": "regular", "mode": 33188, "sha256": "06e8f59a6ccc30bff3131623454cc9c5b99e146d6d4fea36d2fd79fcc847a9d0"}, "scripts/fixlibdwarfelf.sh": {"bytes": 417, "kind": "regular", "mode": 33188, "sha256": "8d1caf090755c08837e4c19c1916a4c034b9010810185273d0fa195bc876ba27"}, "scripts/generatedcasetext.c": {"bytes": 11721, "kind": "regular", "mode": 33188, "sha256": "ef535dd90039c006dd59a8cc0043bf2ec43771408bccd6c2d8cdd2a21a8b77f7"}, "scripts/longopt.txt": {"bytes": 9611, "kind": "regular", "mode": 33188, "sha256": "0e732a6bafe5bd45f95a36d5d2598b049deebe2f79b8580f856858dcde2c8fc8"}, "test-driver": {"bytes": 4640, "kind": "regular", "mode": 33261, "sha256": "7c1ae35455771ae32050c2ed109e3d297160b6d1a2f70b0278cf6968e5e7e98c"}, "tsearch": {"kind": "directory", "mode": 16832}, "tsearch/ChangeLog": {"bytes": 1023, "kind": "regular", "mode": 33188, "sha256": "ae64485eb68643a6287338d098bc3b33fdb165cc633746e07bb699df27d43a64"}, "tsearch/ChangeLog2014": {"bytes": 612, "kind": "regular", "mode": 33188, "sha256": "ce74c89848f2806efe7aaacb5fbfa00a432668195572f593fb88348d83564694"}, "tsearch/ChangeLog2015": {"bytes": 134, "kind": "regular", "mode": 33188, "sha256": "9852b3625753ada22dc7e0e4b8a6cba674fbabbf785dd49facd4b3fdb84a1310"}, "tsearch/ChangeLog2016": {"bytes": 1498, "kind": "regular", "mode": 33188, "sha256": "a06be27572f663e9b015bfc719ad8263036fb403fe4984ad7e0f0a3ec35b4fd9"}, "tsearch/ChangeLog2017": {"bytes": 195, "kind": "regular", "mode": 33188, "sha256": "c024f9fbd9b9338348fe96f5ed0fe9d5985297db4bcbbdedc191899f80311ea4"}, "tsearch/ESSAY.txt": {"bytes": 15566, "kind": "regular", "mode": 33188, "sha256": "73550aed95e397deb1cdf86e7dc7e6317f06750b61c41e3bb89e389310a3fa3d"}, "tsearch/Makefile": {"bytes": 2468, "kind": "regular", "mode": 33188, "sha256": "1c11a0ccc94b8d5da51e453cbbe4f4fe6f4ee7af73131ce945e40c83a141e819"}, "tsearch/README": {"bytes": 6382, "kind": "regular", "mode": 33188, "sha256": "dab6d8b5e119028a65c2e04fa36487281fea54049a98224470ab8f423db485f3"}, "tsearch/RUNTEST": {"bytes": 2805, "kind": "regular", "mode": 33188, "sha256": "6a3ad777dc5645d1701f657a746b7f5cb54a0d9aa1e7a7011df3e6c83095cf7d"}, "tsearch/config.h": {"bytes": 633, "kind": "regular", "mode": 33188, "sha256": "c8216ea92d2d4acebb3e07d2681c03335ae4a936fe8e06f30e1e61bbe1858054"}, "tsearch/dwarf_incl.h": {"bytes": 1421, "kind": "regular", "mode": 33188, "sha256": "387b00c3d76f6df6138dc0b938c813531a27234ea6193eeddd99f3ef1b1cdabe"}, "tsearch/dwarf_tsearch.c": {"bytes": 1999, "kind": "regular", "mode": 33188, "sha256": "64f992a2495c484090abafd5063ae69ec076968dadc3946bb41549f09ae8f4ca"}, "tsearch/dwarf_tsearch.h": {"bytes": 4123, "kind": "regular", "mode": 33188, "sha256": "69dbc34c74b1eef442c3025456fc65e4ec27af337a566395942c917fc49e54ac"}, "tsearch/dwarf_tsearchbal.c": {"bytes": 27333, "kind": "regular", "mode": 33188, "sha256": "542fee97a2926d1c34e0727cba239576bfd4a1a32fef1bf92b7ed1374b876b3b"}, "tsearch/dwarf_tsearchbin.c": {"bytes": 14322, "kind": "regular", "mode": 33188, "sha256": "5fb106cdf9c4b5348fbf959779ff6fab631c90e57b1ff06ef700ed840641e74c"}, "tsearch/dwarf_tsearchepp.c": {"bytes": 14983, "kind": "regular", "mode": 33188, "sha256": "3f0f0724489e26d0787e5e1df65c20090c89e8b4c524bd3cb7f37b6231d46817"}, "tsearch/dwarf_tsearchhash.c": {"bytes": 19101, "kind": "regular", "mode": 33188, "sha256": "21db9d5163596a7982e7953f8b96202b172d05d639e291dc6db4b83cd4a7cd52"}, "tsearch/dwarf_tsearchred.c": {"bytes": 22447, "kind": "regular", "mode": 33188, "sha256": "aebd37d9775d2034e9829f381a0ccff63cee598a10337deab55f3cc7fc769b76"}, "tsearch/scripts": {"kind": "directory", "mode": 16832}, "tsearch/scripts/TEST.sh": {"bytes": 114, "kind": "regular", "mode": 33188, "sha256": "9e6f61687747e76f939554a53fb7a8a903fe60a6e78a7889b051a421e25970c9"}, "tsearch/scripts/badsample": {"bytes": 389, "kind": "regular", "mode": 33188, "sha256": "4ef145fe4099f2f612fd0c1354e0d9431c59e941f4a532b7bbfd4d1b78fc4703"}, "tsearch/scripts/comparator.py": {"bytes": 2656, "kind": "regular", "mode": 33188, "sha256": "cfea6f67e6a7856a3d1fee99587f9a1e853c1e77ace3ee9b63ccdd0412f80d05"}, "tsearch/scripts/comparatorsample": {"bytes": 427, "kind": "regular", "mode": 33188, "sha256": "36c1ed5530381afeaa8b1318168fffb66eeb7b9345743eb315167a74d701bf39"}, "tsearch/scripts/concatlines.py": {"bytes": 2031, "kind": "regular", "mode": 33188, "sha256": "ed1139a0dde1a03f2232c70b199463d329c6e7d939639797dc8c5b3ec540de91"}, "tsearch/scripts/concatlinesample": {"bytes": 1776, "kind": "regular", "mode": 33188, "sha256": "63a2eae20cff546451a4178b9925459d38ab05e6d499c5d44c8da1f973e1aaad"}, "tsearch/scripts/secondsample": {"bytes": 427, "kind": "regular", "mode": 33188, "sha256": "36c1ed5530381afeaa8b1318168fffb66eeb7b9345743eb315167a74d701bf39"}, "tsearch/scripts/testin": {"bytes": 28, "kind": "regular", "mode": 33188, "sha256": "d7a8a6a383621aaaeb6277f43c18c9fbe608899620878fe974b0af664416cff2"}, "tsearch/tsearch.c": {"bytes": 6224, "kind": "regular", "mode": 33188, "sha256": "db7eb433f21b4ddd71a44fcf0ece4c073d93841cdedf7ef0e8ce3d2cbe2be4e2"}, "tsearch/tsearch_tester.c": {"bytes": 33389, "kind": "regular", "mode": 33188, "sha256": "8f066ccd3b98cf323737371406d86771467603dc3baa606606d85820101ba65b"}, "tsearch/tsearchlibtimes.csv": {"bytes": 1407, "kind": "regular", "mode": 33188, "sha256": "9c2e095f9ed6366fc83bea17a455ae152eee35a82489e596518ae69dbd51cc81"}, "tsearch/tsearchlibtimes.ods": {"bytes": 16720, "kind": "regular", "mode": 33188, "sha256": "02b47e40e39ff9a50dc87fa0d4a7ead204f69aa507e2f38a04f49a4134f9a8c4"}}, "host_root": "/home/holden/mckernel-work/scratch/native-exact-mckernel-gitlink-libdwarf-942c927b-scratch22-authority3-image1-20261017", "manifest": {"bytes": 96783, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/gitlink-inputs.CURRENT290-IHK3114.SOURCE-ONLY.json", "sha256": "e0c1abf3e0a16c9ff4a328d66f54fa126be0955d9ef54158ae520f7aa5d64c05"}, "path": "executer/user/lib/libdwarf/libdwarf"}]')

def _reuse_view_entries(root):
    root = Path(root)
    found = {'.': root}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(parent) / name
            found[str(path.relative_to(root))] = path
    return found

def _reuse_compare_source_views(base, effective, postimages, consumed_views):
    base, effective = Path(base), Path(effective)
    expected_postimages = {row['relative']: row['postimage'] for row in postimages}
    base_rows = _reuse_view_entries(base)
    effective_rows = _reuse_view_entries(effective)
    _reuse_require(len(consumed_views) == 1 and consumed_views[0]['path'] == 'executer/user/lib/libdwarf/libdwarf', 'exact consumed nested mount set differs')
    for view in consumed_views:
        relative_root = view['path']
        original_root = base / relative_root
        mounted_root = effective / relative_root
        _reuse_require(original_root.is_dir() and not original_root.is_symlink() and not any(original_root.iterdir()), 'consumed base gitlink directory is not empty')
        mounted = _reuse_view_entries(mounted_root)
        _reuse_require(mounted.keys() == view['entries'].keys(), 'consumed vendor membership differs')
        for relative, path in mounted.items():
            expected = view['entries'][relative]
            current = path.lstat()
            _reuse_require(current.st_mode == expected['mode'], 'consumed vendor mode/type differs')
            if expected['kind'] == 'directory':
                _reuse_require(path.is_dir() and not path.is_symlink(), 'consumed vendor directory differs')
            else:
                _reuse_require(expected['kind'] == 'regular', 'consumed vendor kind differs')
                _reuse_file(path, expected)
        # Remove only descendants of this exact fully checked consumed root.
        # Its root itself remains in the ordinary membership comparison.
        effective_rows = {key: value for key, value in effective_rows.items()
                          if not key.startswith(relative_root + '/')}
    _reuse_require(base_rows.keys() == effective_rows.keys(), 'effective tree membership differs from authenticated base')
    consumed_roots = {view['path'] for view in consumed_views}
    for relative, original in base_rows.items():
        if relative in consumed_roots:
            continue
        current = effective_rows[relative]
        left, right = original.lstat(), current.lstat()
        _reuse_require(left.st_mode == right.st_mode, 'effective tree mode differs: ' + relative)
        if original.is_symlink():
            _reuse_require(current.is_symlink() and os.readlink(original) == os.readlink(current), 'effective symlink differs')
        elif original.is_file():
            expected = expected_postimages.get(relative) or dict(bytes=left.st_size, sha256=_sha256(original))
            _reuse_file(current, expected)
        else:
            _reuse_require(original.is_dir() and current.is_dir(), 'effective entry type differs')
    return dict(status='PASS_EXACT_BASE_PLUS_THREE_POSTIMAGES_AND_CONSUMED_GITLINK_VIEW', consumed_roots=sorted(consumed_roots))

def _reuse_validate_source(source_root, candidate_sha, ihk_sha, manifest, git):
    _reuse_require(str(source_root) == '/src', 'effective source alias differs')
    _reuse_require(candidate_sha == _REUSE_FIXED['candidate_sha'] and ihk_sha == _REUSE_FIXED['ihk_sha'], 'base source identities differ')
    _reuse_file(manifest, _REUSE_FIXED['base_manifest'])
    observed = _validate_source(Path('/base-src'), candidate_sha, ihk_sha, manifest, git)
    _reuse_file('/libdwarf-inputs.json', _REUSE_CONSUMED_GITLINK_VIEWS[0]['manifest'])
    _reuse_compare_source_views(Path('/base-src'), Path('/src'), _REUSE_FIXED['postimages'], _REUSE_CONSUMED_GITLINK_VIEWS)
    _reuse_authenticate('/reuse-inputs.json', container=True)
    return observed


def _reuse_prepare_build(build, evidence):
    _reuse_require(str(build) == '/work/output/build', 'fresh reuse output alias differs')
    fixed = _REUSE_FIXED
    _reuse_authenticate('/reuse-inputs.json', container=True)
    for row in fixed['configuration'] + [row for row in fixed['objects'] if not row['replace']]:
        source = Path('/seed-build') / row['build_relative']
        target = build / row['build_relative']
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _reuse_require(not target.exists() and not target.is_symlink(), 'seed output not fresh')
        with target.open('xb') as stream:
            with source.open('rb') as incoming:
                shutil.copyfileobj(incoming, stream)
            stream.flush()
            os.fsync(stream.fileno())
        _reuse_file(target, row['source'])
    (build / 'kernel/rust').mkdir(mode=0o700, parents=True, exist_ok=True)
    database = build / 'compile_commands.json'
    rows = json.loads(database.read_text())
    matched = [row for row in rows if row.get('file') == '/src/kernel/process.c']
    _reuse_require(matched == [fixed['commands']['process_command_selected_original']], 'actual process command changed')
    matched[0]['command'] = shlex.join(fixed['commands']['process_command_expected_argv'])
    _atomic_json(database, rows)
    # Generated files are retained inputs. This separate record identifies the
    # sole command derivation; it does not call them newly configured outputs.
    _atomic_json(evidence / 'readonly-reuse-command-derivation.json', dict(
        configuration_mode=fixed['configuration_mode'], fresh_full_configure=False,
        process_command=fixed['commands']['process_command_expected_argv'],
        seed_configuration=fixed['configuration'], objects=fixed['objects'],
        postimages=fixed['postimages'], source_base=fixed['base_manifest']))

def _reuse_commands():
    fixed = _REUSE_FIXED
    rust = shlex.split(fixed['commands']['Rust_actual_default_command'])
    _reuse_require(rust[:3] == ['cd', '/work/output/build/kernel', '&&'], 'Rust default command cwd differs')
    _reuse_require(not any('codegen-units' in arg for arg in rust), 'unexpected CGU override')
    return [('recompile-full-Rust', rust[3:]),
            ('recompile-process', fixed['commands']['process_command_expected_argv']),
            ('raw-ld-11-inputs', fixed['commands']['link_argv'])]

def _run(*args, readonly_reuse_inputs=None, **kwargs):
    if readonly_reuse_inputs is None:
        return _REUSE_FRESH_RUN(*args, **kwargs)
    _reuse_require(str(readonly_reuse_inputs) == '/reuse-inputs.json', 'reuse descriptor alias differs')
    return _reuse_run(*args, **kwargs)

def main(argv=None):
    values = list(sys.argv[1:] if argv is None else argv)
    if '--readonly-reuse-inputs' not in values:
        return _REUSE_FRESH_MAIN(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--candidate-sha', required=True)
    parser.add_argument('--ihk-sha', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--jobs', type=int, required=True)
    parser.add_argument('--timeout', type=int, required=True)
    parser.add_argument('--gitlink-manifest', type=Path)
    parser.add_argument('--readonly-reuse-inputs', type=Path, required=True)
    result = run(**vars(parser.parse_args(values)))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1



class _ReuseElf:

    def __init__(self, path):
        self.raw = path.read_bytes()
        eh = struct.unpack_from('<16sHHIQQQIHHHHHH', self.raw)
        assert eh[0][:6] == b'\x7fELF\x02\x01' and eh[1] == 1 and (eh[2] == 62) and (eh[11] == 64)
        self.sections = [dict(zip(['name_off', 'type', 'flags', 'addr', 'offset', 'size', 'link', 'info', 'align', 'entsize'], struct.unpack_from('<IIQQQQIIQQ', self.raw, eh[6] + i * 64))) for i in range(eh[12])]
        names = self.payload(self.sections[eh[13]])
        for (i, section) in enumerate(self.sections):
            section.update(index=i, name=self.string(names, section['name_off']))
        tables = [s for s in self.sections if s['type'] == 2]
        assert len(tables) == 1 and tables[0]['entsize'] == 24
        self.table = tables[0]
        strings = self.payload(self.sections[self.table['link']])
        self.symbols = []
        for i in range(self.table['size'] // 24):
            (no, info, other, idx, value, size) = struct.unpack_from('<IBBHQQ', self.raw, self.table['offset'] + i * 24)
            self.symbols.append(dict(index=i, name=self.string(strings, no), bind=info >> 4, type=info & 15, shndx=idx, value=value, size=size))

    @staticmethod
    def string(table, offset):
        return table[offset:table.index(b'\x00', offset)].decode()

    def payload(self, section):
        return self.raw[section['offset']:section['offset'] + section['size']]

    def sym(self, name):
        found = [s for s in self.symbols if s['name'] == name]
        assert len(found) == 1, (name, found)
        return found[0]

    def data(self, name):
        sym = self.sym(name)
        assert sym['shndx'] not in (0, 65521) and sym['type'] == 1
        data = self.payload(self.sections[sym['shndx']])
        assert sym['value'] + sym['size'] <= len(data)
        return data[sym['value']:sym['value'] + sym['size']]

    def word(self, name):
        data = self.data(name)
        assert len(data) == 8, (name, len(data))
        return int.from_bytes(data, 'little')

def _reuse_elf_owning_relocations(elf, symbol):
    result = []
    for sec in elf.sections:
        if sec['type'] != 4 or sec['info'] != symbol['shndx']:
            continue
        assert sec['link'] == elf.table['index'] and sec['entsize'] == 24 and (sec['size'] % 24 == 0)
        for i in range(sec['size'] // 24):
            (offset, info, addend) = struct.unpack_from('<QQq', elf.raw, sec['offset'] + 24 * i)
            assert info >> 32 < len(elf.symbols)
            if symbol['value'] <= offset < symbol['value'] + symbol['size']:
                result.append(dict(offset=offset - symbol['value'], type=info & 4294967295, target=elf.symbols[info >> 32], addend=addend, owning_section=sec['info']))
    return result

def _reuse_elf_object_bytes(elf, sym):
    sec = elf.sections[sym['shndx']]
    assert sym['value'] + sym['size'] <= sec['size']
    return bytes(sym['size']) if sec['type'] == 8 else elf.payload(sec)[sym['value']:sym['value'] + sym['size']]

def _reuse_elf_cstring(elf, relocation):
    target = relocation['target']
    assert relocation['type'] == 1 and 0 < target['shndx'] < len(elf.sections)
    section = elf.sections[target['shndx']]
    assert section['flags'] & 2
    payload = elf.payload(section)
    start = target['value'] + relocation['addend']
    assert 0 <= start < len(payload)
    return payload[start:payload.index(b'\x00', start)].decode()

def _reuse_elf_descriptor(elf, symbol, filename, function, line):
    section = elf.sections[symbol['shndx']]
    assert symbol['size'] == 32 and symbol['value'] % 8 == 0
    assert section['name'] == '__verbose' and section['flags'] & 3 == 3 and (not section['flags'] & 4)
    assert section['align'] >= 8
    initial = _reuse_elf_object_bytes(elf, symbol)
    assert initial[:24] == bytes(24) and initial[28:] == bytes(4)
    assert int.from_bytes(initial[24:28], 'little') == line
    relas = _reuse_elf_owning_relocations(elf, symbol)
    assert len(relas) == 2 and {r['offset'] for r in relas} == {0, 8}
    for rela in relas:
        assert _reuse_elf_cstring(elf, rela) == (filename if rela['offset'] == 0 else function)
    return dict(symbol=symbol, initial_hex=initial.hex(), relocations=relas, filename=filename, function=function, line=line)

def _reuse_elf_function(elf, name):
    rows = [row for row in elf.symbols if row['name'] == name and row['shndx'] != 0]
    assert len(rows) == 1 and rows[0]['bind'] == 1 and (rows[0]['type'] == 2)
    symbol = rows[0]
    assert 0 < symbol['shndx'] < len(elf.sections)
    assert symbol['size'] > 0 and elf.sections[symbol['shndx']]['flags'] & 6 == 6
    return symbol

def _reuse_elf_undefined(elf):
    return {row['name'] for row in elf.symbols if row['name'] and row['shndx'] == 0}

def _reuse_elf_panic_targets(elf, symbol):
    return [row['target']['name'] for row in _reuse_elf_owning_relocations(elf, symbol) if any((part in row['target']['name'] for part in ('panic_const', 'panicking', 'rust_begin_unwind', 'panic_fmt')))]

def _reuse_validate_changed_rust_object(build, evidence):
    _reuse_require(__debug__, 'strict object assertions disabled')
    old_path = Path('/seed-build/kernel/rust/mckernel_rust.o')
    new_path = Path(build) / 'kernel/rust/mckernel_rust.o'
    old_snapshot = _artifact(old_path, 'retained old full Rust object')
    new_snapshot = _artifact(new_path, 'fresh compiled full Rust object')
    old = _ReuseElf(old_path)
    new = _ReuseElf(new_path)
    old_handler = _reuse_elf_function(old, 'move_pages_smp_handler')
    new_handler = _reuse_elf_function(new, 'move_pages_smp_handler')
    original_panics = _reuse_elf_panic_targets(old, old_handler)
    assert len(original_panics) == 2
    assert any(('panic_const_div_by_zero' in name for name in original_panics))
    assert any(('panic_const_div_overflow' in name for name in original_panics))
    assert not _reuse_elf_panic_targets(new, new_handler)
    assert _reuse_elf_undefined(new) == _reuse_elf_undefined(old) - set(original_panics), 'unexpected whole-object import change'
    assert not any(('panic_const_div_by_zero' in name or 'panic_const_div_overflow' in name for name in _reuse_elf_undefined(new)))
    logger_function = _reuse_elf_function(new, 'arch_process_vm_rw_log_bridge')
    logger_code_relocations = _reuse_elf_owning_relocations(new, logger_function)
    policy = Path('/src/kernel/rust/syscall_policy.rs')
    policy_lines = policy.read_text().splitlines()
    markers = ['F06_PROCESS_VM_IOV_LOCAL_DEBUG', 'F06_PROCESS_VM_IOV_REMOTE_DEBUG', 'F06_PROCESS_VM_FOUND_DEBUG', 'F06_PROCESS_VM_COPY_DEBUG']
    logger_proof = {}
    for marker in markers:
        previous = [row for row in old.symbols if marker in row['name'] and row['type'] == 1]
        assert len(previous) == 1 and previous[0]['bind'] == 1, 'original GLOBAL defect control'
        symbols = [row for row in new.symbols if marker in row['name'] and row['type'] == 1]
        assert len(symbols) == 1
        symbol = symbols[0]
        assert symbol['bind'] == 0 and symbol['size'] == 32
        assert 0 < symbol['shndx'] < len(new.sections)
        other_offset = new.table['offset'] + symbol['index'] * new.table['entsize'] + 5
        assert new.raw[other_offset] == 0, 'LOCAL logger visibility must remain DEFAULT0'
        overlaps = [row for row in new.symbols if row['type'] == 1 and row['shndx'] == symbol['shndx'] and row['size'] and (max(row['value'], symbol['value']) < min(row['value'] + row['size'], symbol['value'] + symbol['size']))]
        assert len(overlaps) == 1, 'duplicate or overlapping logger storage'
        starts = [index for (index, line) in enumerate(policy_lines) if 'static mut ' + marker + ':' in line]
        assert len(starts) == 1
        start = starts[0]
        end = next((index for index in range(start, len(policy_lines)) if policy_lines[index].strip() == '};'))
        source_lines = [index + 1 for index in range(start, end + 1) if 'line_flags: line!()' in policy_lines[index]]
        assert len(source_lines) == 1
        record = _reuse_elf_descriptor(new, symbol, str(policy), 'arch_process_vm_rw_log_bridge', source_lines[0])
        consumers = []
        for relocation in logger_code_relocations:
            target = relocation['target']
            if target['shndx'] != symbol['shndx']:
                continue
            address = target['value'] + relocation['addend']
            if symbol['value'] <= address < symbol['value'] + symbol['size']:
                assert relocation['type'] == 1, 'actual large-model data reference must retain 64-bit ABI'
                consumers.append(relocation)
        assert consumers, 'no actual logger callback instruction edge'
        logger_proof[marker] = {'record': record, 'callback_consumer_relocations': consumers}
    result = {'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'status': 'PASS_ACTUAL_DEFAULT_WHOLE_RUST_HANDLER_NO_PANIC_AND_FOUR_LOCAL_LOGGERS', 'new_Rust_object': {'path': str(new_path), 'bytes': new_path.stat().st_size, 'sha256': hashlib.sha256(new_path.read_bytes()).hexdigest()}, 'old_handler': old_handler, 'new_handler': new_handler, 'removed_original_panic_imports': original_panics, 'whole_undefined_set_exact_except_removed_panics': True, 'logger_callback': logger_function, 'logger_proof': logger_proof, 'actual_default_flags_without_explicit_codegen_units': True, 'canonical_edits': 0, 'partial_or_final_link_validated': False, 'native': False}
    _fail(_artifact(old_path, 'retained old full Rust object') == old_snapshot,
          'retained old Rust object changed during strict ownership gate')
    _fail(_artifact(new_path, 'fresh compiled full Rust object') == new_snapshot,
          'fresh compiled Rust object changed during strict ownership gate')
    result['old_Rust_object'] = old_snapshot
    result['new_Rust_object'] = new_snapshot
    result['mandatory_fresh_compiled_object_gate'] = True
    _atomic_json(Path(evidence) / 'fresh-compiled-rust-ownership-proof.json', result)
    return result

if __name__ == "__main__":
    raise SystemExit(main())
