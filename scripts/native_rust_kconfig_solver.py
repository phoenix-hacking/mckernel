#!/usr/bin/env python3
"""Run and verify the bounded native-Rust Kconfig dependency matrix.

This is a configuration solver check, not build, runtime, production, gate, or
tracker evidence.  ``run`` consumes an already acquired, patched, and staged
Linux 6.12 source tree plus a generated seed configuration.  It runs every
matrix case serially in a fresh out-of-tree directory and records only the
closed, non-crediting result surface described below.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import native_rust_kconfig_policy as kconfig_policy


SCHEMA_VERSION = 1
ARTIFACT_NAME = "kconfig-solver-matrix.json"
STAGED_KCONFIG_PATH = "drivers/misc/mckernel/Kconfig"
VALUES = ("n", "m", "y")
MODULE_VALUES = ("n", "y")
CONFIG_RUST = "CONFIG_RUST"
CONFIG_X86_64 = "CONFIG_X86_64"
CONFIG_MODULES = "CONFIG_MODULES"
CONFIG_PROVIDER = "CONFIG_MCKERNEL_IHK_RUST"
CONFIG_SMP = "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST"
CONFIG_MCCTRL = "CONFIG_MCKERNEL_MCCTRL_RUST"
MODULE_SYMBOLS = (CONFIG_PROVIDER, CONFIG_SMP, CONFIG_MCCTRL)
RESULT_SYMBOLS = (
    CONFIG_MODULES,
    CONFIG_PROVIDER,
    CONFIG_SMP,
    CONFIG_MCCTRL,
    CONFIG_RUST,
    CONFIG_X86_64,
)
REQUEST_SYMBOLS = RESULT_SYMBOLS
SOURCE_TREE_DOMAIN = b"mckernel-native-rust-linux-source-tree-v1\x00"
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
OCTAL_MODE = re.compile(r"^[0-7]{4}$")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
CONFIG_SET = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
MAKEFILE_ASSIGNMENT = re.compile(r"^([A-Z]+) = ([0-9]+)$")
EXPECTED_COUNTS = {
    "case_count": 54,
    "matrix_make_invocation_count": 108,
    "module_result_distribution": {"0": 36, "1": 2, "2": 8, "3": 8},
    "negative_make_invocation_count": 2,
    "total_make_invocation_count": 110,
    "two_pass_byte_identical_count": 54,
}
EXPECTED_CLAIMS = {
    "credit_eligible": False,
    "gate_credit_awarded": False,
    "independent_replay_proven": False,
    "per_case_config_bytes_retained": False,
    "production_configuration_proven": False,
    "runtime_behavior_proven": False,
    "tracker_credit": False,
}
EXPECTED_LIMITATIONS = {
    "artifact_scope": "canonical JSON report only; per-case .config bytes are not transported",
    "check_scope": "schema, oracle, reported facts, and supplied current input bindings only; make is not replayed",
    "fact_scope": "per-row hashes and sizes are runner-reported facts pending independent replay",
}
REPORTED_FACT_SCOPE = (
    "runner-reported hashes and sizes; per-case .config bytes not transported"
)
CAPTURE_STATUS = "captured-unreviewed"
REMOVED_ENVIRONMENT_KEYS = (
    "ARCH",
    "GNUMAKEFLAGS",
    "KBUILD_EXTMOD",
    "KBUILD_KCONFIG",
    "KBUILD_OUTPUT",
    "KBUILD_SRC",
    "KCONFIG_ALLCONFIG",
    "KCONFIG_CONFIG",
    "KCONFIG_NOSILENTUPDATE",
    "KCONFIG_OVERWRITECONFIG",
    "LLVM",
    "MAKEFLAGS",
    "MAKEFILES",
    "MAKELEVEL",
    "MFLAGS",
    "O",
)
FIXED_ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
MAKE_ARGV_TEMPLATE = (
    "make",
    "ARCH=x86_64",
    "LLVM=1",
    "O=<case-output-directory>",
    "olddefconfig",
)
MAKE_TIMEOUT_SECONDS = 1800
EXPECTED_RUNNER = {
    "argv_template": list(MAKE_ARGV_TEMPLATE),
    "cwd": "linux-source-tree",
    "execution": {
        "case_output_policy": "fresh-separate-O-directory",
        "matrix_case_count": 54,
        "matrix_order": "MODULES[n,y]-provider[n,m,y]-smp[n,m,y]-mcctrl[n,m,y]",
        "negative_case_count": 1,
        "passes_per_executed_case": 2,
        "serial": True,
        "timeout_seconds_per_invocation": MAKE_TIMEOUT_SECONDS,
    },
    "fixed_environment": dict(FIXED_ENVIRONMENT),
    "inherited_environment_policy": "all other process keys inherited; binary identity not claimed",
    "removed_environment_keys": list(REMOVED_ENVIRONMENT_KEYS),
}
TOP_KEYS = {
    "claims",
    "counts",
    "inputs",
    "limitations",
    "matrix",
    "negative_checks",
    "runner",
    "schema_version",
    "status",
}


class SolverError(Exception):
    """Raised when the matrix runner or evidence validator fails closed."""


def _exact_type(value, expected, label):
    if type(value) is not expected:
        raise SolverError("{0} has the wrong JSON type".format(label))
    return value


def _exact_keys(value, keys, label):
    _exact_type(value, dict, label)
    actual = set(value)
    if actual != set(keys):
        raise SolverError(
            "{0} keys differ: expected {1}, got {2}".format(
                label, sorted(keys), sorted(actual)
            )
        )


def _ascii_text_bytes(data, label):
    if not isinstance(data, bytes):
        raise SolverError("{0} must be bytes".format(label))
    for byte in bytearray(data):
        if byte not in (0x09, 0x0A) and not 0x20 <= byte <= 0x7E:
            raise SolverError(
                "{0} contains unsupported byte 0x{1:02x}".format(label, byte)
            )
    if data and not data.endswith(b"\n"):
        raise SolverError("{0} must end with LF".format(label))
    return data.decode("ascii")


def _ascii_no_tab_bytes(data, label):
    text = _ascii_text_bytes(data, label)
    if b"\t" in data:
        raise SolverError("{0} contains a forbidden TAB".format(label))
    return text


def _stat_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _read_regular_file(path, label):
    path = os.path.abspath(path)
    try:
        before = os.lstat(path)
    except OSError as error:
        raise SolverError("cannot stat {0}: {1}".format(label, error))
    if not stat.S_ISREG(before.st_mode):
        raise SolverError("{0} must be a regular non-symlink file".format(label))
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or _stat_identity(
                opened
            ) != _stat_identity(before):
                raise SolverError("{0} changed while it was opened".format(label))
            chunks = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
            after = os.fstat(descriptor)
            if _stat_identity(after) != _stat_identity(opened):
                raise SolverError("{0} changed while it was read".format(label))
        finally:
            os.close(descriptor)
    except SolverError:
        raise
    except OSError as error:
        raise SolverError("cannot read {0}: {1}".format(label, error))
    if len(data) != before.st_size:
        raise SolverError("{0} size changed while it was read".format(label))
    try:
        final = os.lstat(path)
    except OSError as error:
        raise SolverError("cannot restat {0}: {1}".format(label, error))
    if not stat.S_ISREG(final.st_mode) or _stat_identity(final) != _stat_identity(
        before
    ):
        raise SolverError("{0} path changed while it was read".format(label))
    return data


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _mode_string(mode):
    return "{0:04o}".format(stat.S_IMODE(mode))


def _write_all(descriptor, data, label):
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        try:
            written = os.write(descriptor, view[offset:])
        except OSError as error:
            raise SolverError("cannot write {0}: {1}".format(label, error))
        if written <= 0:
            raise SolverError("short write while creating {0}".format(label))
        offset += written


def _digest_record(
    path, logical_path, label, require_ascii=False, include_mode=False
):
    try:
        before = os.lstat(path)
    except OSError as error:
        raise SolverError("cannot stat {0}: {1}".format(label, error))
    data = _read_regular_file(path, label)
    try:
        after = os.lstat(path)
    except OSError as error:
        raise SolverError("cannot restat {0}: {1}".format(label, error))
    if _stat_identity(before) != _stat_identity(after):
        raise SolverError("{0} identity changed while binding it".format(label))
    if require_ascii:
        _ascii_text_bytes(data, label)
    record = {
        "path": logical_path,
        "sha256": _sha256(data),
        "size": len(data),
    }
    if include_mode:
        record["mode"] = _mode_string(after.st_mode)
    return record, data


def _safe_absolute_directory(path, label):
    if not isinstance(path, str) or not path or not os.path.isabs(path):
        raise SolverError("{0} must be an absolute path".format(label))
    if path != os.path.normpath(path):
        raise SolverError("{0} must be lexically normalized".format(label))
    if os.path.realpath(path) != path:
        raise SolverError("{0} must not contain symlink components".format(label))
    try:
        metadata = os.lstat(path)
    except OSError as error:
        raise SolverError("cannot stat {0}: {1}".format(label, error))
    if not stat.S_ISDIR(metadata.st_mode):
        raise SolverError("{0} must be a real directory".format(label))
    return path


def _safe_absolute_file(path, label):
    if not isinstance(path, str) or not path or not os.path.isabs(path):
        raise SolverError("{0} must be an absolute path".format(label))
    if path != os.path.normpath(path):
        raise SolverError("{0} must be lexically normalized".format(label))
    if os.path.realpath(path) != path:
        raise SolverError("{0} must not contain symlink components".format(label))
    _read_regular_file(path, label)
    return path


def _is_within(path, directory):
    try:
        return os.path.commonpath((path, directory)) == directory
    except ValueError:
        return False


def _prepare_matrix_directory(path, source):
    if not isinstance(path, str) or not path or not os.path.isabs(path):
        raise SolverError("matrix directory must be an absolute path")
    if path != os.path.normpath(path):
        raise SolverError("matrix directory must be lexically normalized")
    if not SAFE_NAME.fullmatch(os.path.basename(path)):
        raise SolverError("matrix directory basename is unsafe")
    parent = _safe_absolute_directory(os.path.dirname(path), "matrix parent")
    if os.path.lexists(path):
        raise SolverError("matrix directory already exists")
    if _is_within(path, source) or _is_within(source, path):
        raise SolverError("matrix directory must be separate from the source tree")
    try:
        os.mkdir(path, 0o700)
    except OSError as error:
        raise SolverError("cannot create matrix directory: {0}".format(error))
    if os.path.realpath(path) != path or not stat.S_ISDIR(os.lstat(path).st_mode):
        raise SolverError("created matrix directory is unsafe")
    return path


def _safe_source_symlink(root, absolute, relative):
    try:
        target = os.readlink(absolute)
    except OSError as error:
        raise SolverError("cannot read source symlink {0}: {1}".format(relative, error))
    try:
        target.encode("ascii")
    except UnicodeEncodeError:
        raise SolverError("source symlink target is not ASCII: {0}".format(relative))
    if not target or os.path.isabs(target) or "\x00" in target:
        raise SolverError("source symlink target is unsafe: {0}".format(relative))
    resolved = os.path.realpath(os.path.join(os.path.dirname(absolute), target))
    if not _is_within(resolved, root) or not os.path.exists(resolved):
        raise SolverError("source symlink escapes or is broken: {0}".format(relative))
    return target


def source_tree_digest(root):
    """Return a deterministic digest of regular bytes, safe symlinks, and modes."""

    root = _safe_absolute_directory(root, "Linux source tree")
    root_before = os.lstat(root)
    digest = hashlib.sha256()
    digest.update(SOURCE_TREE_DOMAIN)
    counts = {"directory": 0, "file": 0, "symlink": 0}

    def record(kind, relative, mode, payload):
        try:
            relative.encode("ascii")
        except UnicodeEncodeError:
            raise SolverError("source path is not ASCII: {0!r}".format(relative))
        row = [kind, relative, mode, payload]
        digest.update(
            (json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
                "ascii"
            )
        )

    def visit(directory, prefix):
        try:
            entries = list(os.scandir(directory))
        except OSError as error:
            raise SolverError("cannot scan source tree: {0}".format(error))
        entries.sort(key=lambda item: item.name)
        for entry in entries:
            name = entry.name
            try:
                name.encode("ascii")
            except UnicodeEncodeError:
                raise SolverError("source path component is not ASCII")
            if name in (".", "..") or "/" in name or "\x00" in name:
                raise SolverError("source path component is unsafe")
            relative = name if not prefix else prefix + "/" + name
            absolute = os.path.join(directory, name)
            try:
                metadata = os.lstat(absolute)
            except OSError as error:
                raise SolverError("cannot stat source entry {0}: {1}".format(relative, error))
            mode = stat.S_IMODE(metadata.st_mode)
            if stat.S_ISDIR(metadata.st_mode):
                counts["directory"] += 1
                record("directory", relative, mode, None)
                visit(absolute, relative)
            elif stat.S_ISREG(metadata.st_mode):
                counts["file"] += 1
                data = _read_regular_file(absolute, "source entry " + relative)
                record("file", relative, mode, [len(data), _sha256(data)])
            elif stat.S_ISLNK(metadata.st_mode):
                counts["symlink"] += 1
                record(
                    "symlink",
                    relative,
                    mode,
                    _safe_source_symlink(root, absolute, relative),
                )
            else:
                raise SolverError("source entry is not a regular file/directory/symlink: {0}".format(relative))

    record("root", ".", stat.S_IMODE(root_before.st_mode), None)
    visit(root, "")
    root_after = os.lstat(root)
    if (
        root_before.st_dev != root_after.st_dev
        or root_before.st_ino != root_after.st_ino
        or root_before.st_mode != root_after.st_mode
    ):
        raise SolverError("Linux source root identity or mode changed during hashing")
    return {
        "directory_count": counts["directory"],
        "entry_count": sum(counts.values()),
        "file_count": counts["file"],
        "path": "linux-source-tree",
        "root_mode": _mode_string(root_after.st_mode),
        "sha256": digest.hexdigest(),
        "symlink_count": counts["symlink"],
    }


def _parse_linux_version(makefile_bytes):
    text = _ascii_text_bytes(makefile_bytes, "Linux source Makefile")
    values = {}
    for line in text[:-1].split("\n") if text else []:
        match = MAKEFILE_ASSIGNMENT.match(line)
        if match and match.group(1) in ("VERSION", "PATCHLEVEL"):
            if match.group(1) in values:
                raise SolverError("Linux Makefile version assignment is duplicated")
            values[match.group(1)] = match.group(2)
    if values != {"PATCHLEVEL": "12", "VERSION": "6"}:
        raise SolverError("Linux source must be version 6.12")
    return "6.12"


def parse_config(data, label):
    text = _ascii_no_tab_bytes(data, label)
    result = {}
    lines = text[:-1].split("\n") if text else []
    for number, line in enumerate(lines, 1):
        set_match = CONFIG_SET.match(line)
        unset_match = CONFIG_UNSET.match(line)
        if set_match:
            symbol, value = set_match.groups()
        elif unset_match:
            symbol, value = unset_match.group(1), "n"
        else:
            if line.startswith("CONFIG_") or line.startswith("# CONFIG_"):
                raise SolverError(
                    "{0}:{1}: malformed config assignment".format(label, number)
                )
            if line and not line.startswith("#"):
                raise SolverError(
                    "{0}:{1}: non-comment config text is forbidden".format(
                        label, number
                    )
                )
            continue
        if symbol in result:
            raise SolverError("{0}: duplicate config symbol {1}".format(label, symbol))
        result[symbol] = value
    return result


def _config_line(symbol, value):
    if value == "n":
        return "# {0} is not set".format(symbol)
    if value in ("m", "y"):
        return "{0}={1}".format(symbol, value)
    raise SolverError("invalid tristate value for {0}".format(symbol))


def requested_config(seed_bytes, request, allow_negative=False):
    _exact_request(request, "request", allow_negative=allow_negative)
    text = _ascii_text_bytes(seed_bytes, "seed config")
    parse_config(seed_bytes, "seed config")
    replaced = set(request)
    kept = []
    for line in text[:-1].split("\n"):
        match = CONFIG_SET.match(line) or CONFIG_UNSET.match(line)
        if match and match.group(1) in replaced:
            continue
        kept.append(line)
    if kept and kept[-1] != "":
        kept.append("")
    kept.append("# Native Rust Kconfig solver request; no tracker credit.")
    for symbol in REQUEST_SYMBOLS:
        kept.append(_config_line(symbol, request[symbol]))
    return ("\n".join(kept) + "\n").encode("ascii")


def matrix_requests():
    requests = []
    for modules in MODULE_VALUES:
        for provider in VALUES:
            for smp in VALUES:
                for mcctrl in VALUES:
                    requests.append(
                        {
                            CONFIG_MODULES: modules,
                            CONFIG_PROVIDER: provider,
                            CONFIG_SMP: smp,
                            CONFIG_MCCTRL: mcctrl,
                            CONFIG_RUST: "y",
                            CONFIG_X86_64: "y",
                        }
                    )
    return requests


def _exact_request(request, label, allow_negative=False):
    _exact_keys(request, REQUEST_SYMBOLS, label)
    for symbol in REQUEST_SYMBOLS:
        value = _exact_type(request[symbol], str, label + "." + symbol)
        if value not in VALUES:
            raise SolverError("{0}.{1} has an invalid tristate".format(label, symbol))
    if request[CONFIG_MODULES] not in MODULE_VALUES:
        raise SolverError("{0}.CONFIG_MODULES must be n or y".format(label))
    if request[CONFIG_X86_64] != "y" and not allow_negative:
        raise SolverError("matrix requests require CONFIG_X86_64=y")
    if request[CONFIG_RUST] != "y" and not allow_negative:
        raise SolverError("matrix requests require CONFIG_RUST=y")


def oracle(request):
    _exact_request(request, "oracle request", allow_negative=True)
    result = dict((symbol, request[symbol]) for symbol in RESULT_SYMBOLS)
    if (
        request[CONFIG_MODULES] != "y"
        or request[CONFIG_RUST] != "y"
        or request[CONFIG_X86_64] != "y"
        or request[CONFIG_PROVIDER] == "n"
    ):
        for symbol in MODULE_SYMBOLS:
            result[symbol] = "n"
        return result
    result[CONFIG_PROVIDER] = "m"
    result[CONFIG_SMP] = "n" if request[CONFIG_SMP] == "n" else "m"
    result[CONFIG_MCCTRL] = "n" if request[CONFIG_MCCTRL] == "n" else "m"
    return result


def _case_id(index, request):
    return "case-{0:02d}-modules-{1}-provider-{2}-smp-{3}-mcctrl-{4}".format(
        index,
        request[CONFIG_MODULES],
        request[CONFIG_PROVIDER],
        request[CONFIG_SMP],
        request[CONFIG_MCCTRL],
    )


def _sanitized_environment(environ=None):
    source = os.environ if environ is None else environ
    result = dict(source)
    for name in REMOVED_ENVIRONMENT_KEYS:
        result.pop(name, None)
    result.update(FIXED_ENVIRONMENT)
    return result


def _run_make(source, output, case_id, pass_number, environ):
    command = list(MAKE_ARGV_TEMPLATE)
    command[3] = "O=" + output
    try:
        process = subprocess.Popen(
            command,
            cwd=source,
            env=environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(b"", timeout=MAKE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise SolverError(
            "{0} pass {1} olddefconfig timed out".format(case_id, pass_number)
        )
    except OSError as error:
        raise SolverError(
            "{0} pass {1} could not execute make: {2}".format(
                case_id, pass_number, error
            )
        )
    if process.returncode != 0:
        detail = stderr[-512:].decode("ascii", "backslashreplace")
        raise SolverError(
            "{0} pass {1} olddefconfig failed with {2}: {3}".format(
                case_id, pass_number, process.returncode, detail
            )
        )
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise SolverError("subprocess capture type escaped the closed runner")


def _extract_result(config_bytes, label):
    values = parse_config(config_bytes, label)
    result = {}
    for symbol in RESULT_SYMBOLS:
        if symbol not in values:
            raise SolverError("{0} is missing {1}".format(label, symbol))
        value = values[symbol]
        if value not in VALUES:
            raise SolverError("{0} has non-tristate {1}".format(label, symbol))
        result[symbol] = value
    if result[CONFIG_MODULES] not in MODULE_VALUES:
        raise SolverError("{0} resolved CONFIG_MODULES outside n/y".format(label))
    return result


def _run_two_pass_case(
    source,
    matrix_root,
    case_id,
    seed_bytes,
    request,
    environ,
    allow_negative=False,
):
    case_dir = os.path.join(matrix_root, case_id)
    if os.path.lexists(case_dir):
        raise SolverError("case output already exists: {0}".format(case_id))
    os.mkdir(case_dir, 0o700)
    config_path = os.path.join(case_dir, ".config")
    initial = requested_config(seed_bytes, request, allow_negative=allow_negative)
    descriptor = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        _write_all(descriptor, initial, case_id + " initial .config")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    hashes = []
    sizes = []
    snapshots = []
    for pass_number in (1, 2):
        _run_make(source, case_dir, case_id, pass_number, environ)
        _safe_absolute_directory(case_dir, case_id + " output directory")
        _safe_absolute_file(
            config_path, "{0} pass {1} .config".format(case_id, pass_number)
        )
        snapshot = _read_regular_file(
            config_path, "{0} pass {1} .config".format(case_id, pass_number)
        )
        _ascii_text_bytes(snapshot, case_id + " .config")
        snapshots.append(snapshot)
        hashes.append(_sha256(snapshot))
        sizes.append(len(snapshot))
    if snapshots[0] != snapshots[1]:
        raise SolverError("{0} olddefconfig passes are not byte-identical".format(case_id))
    result = _extract_result(snapshots[1], case_id + " resolved config")
    expected = oracle(request)
    if result != expected:
        raise SolverError(
            "{0} result differs from oracle: expected {1}, got {2}".format(
                case_id, expected, result
            )
        )
    return {
        "byte_identical": True,
        "case_id": case_id,
        "config_sha256_passes": hashes,
        "config_size_passes": sizes,
        "fact_scope": REPORTED_FACT_SCOPE,
        "request": request,
        "result": result,
        "selected_module_count": sum(
            1 for symbol in MODULE_SYMBOLS if result[symbol] == "m"
        ),
        "status": CAPTURE_STATUS,
    }


def _input_bindings(source, seed):
    makefile_record, makefile_bytes = _digest_record(
        os.path.join(source, "Makefile"), "Makefile", "Linux source Makefile", True
    )
    makefile_record["linux_version"] = _parse_linux_version(makefile_bytes)
    staged_record, staged_bytes = _digest_record(
        os.path.join(source, *STAGED_KCONFIG_PATH.split("/")),
        STAGED_KCONFIG_PATH,
        "staged native Rust Kconfig",
        True,
    )
    try:
        kconfig_policy.validate_native_rust_kconfig(staged_bytes.decode("ascii"))
    except (UnicodeDecodeError, kconfig_policy.KconfigPolicyError) as error:
        raise SolverError("staged native Rust Kconfig violates policy: {0}".format(error))
    seed_record, seed_bytes = _digest_record(
        seed, "seed.config", "seed config", True, include_mode=True
    )
    seed_values = parse_config(seed_bytes, "seed config")
    if seed_values.get(CONFIG_RUST) != "y":
        raise SolverError("seed config must contain CONFIG_RUST=y")
    if seed_values.get(CONFIG_X86_64) != "y":
        raise SolverError("seed config must contain CONFIG_X86_64=y")
    return {
        "seed_config": seed_record,
        "source_makefile": makefile_record,
        "source_tree": source_tree_digest(source),
        "staged_kconfig": staged_record,
    }, seed_bytes


def canonical_json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("ascii")


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SolverError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def _validate_digest_record(record, label, expected_path, extra_keys=()):
    keys = {"path", "sha256", "size"}.union(extra_keys)
    _exact_keys(record, keys, label)
    if _exact_type(record["path"], str, label + ".path") != expected_path:
        raise SolverError("{0}.path differs from the locked path".format(label))
    digest = _exact_type(record["sha256"], str, label + ".sha256")
    if not HEX_SHA256.fullmatch(digest):
        raise SolverError("{0}.sha256 is malformed".format(label))
    size = _exact_type(record["size"], int, label + ".size")
    if size < 1:
        raise SolverError("{0}.size must be positive".format(label))
    if "mode" in extra_keys:
        mode = _exact_type(record["mode"], str, label + ".mode")
        if not OCTAL_MODE.fullmatch(mode):
            raise SolverError("{0}.mode is malformed".format(label))


def _validate_source_tree_record(record):
    keys = {
        "directory_count",
        "entry_count",
        "file_count",
        "path",
        "root_mode",
        "sha256",
        "symlink_count",
    }
    _exact_keys(record, keys, "inputs.source_tree")
    if record["path"] != "linux-source-tree":
        raise SolverError("inputs.source_tree.path differs")
    if type(record["path"]) is not str or type(record["sha256"]) is not str:
        raise SolverError("inputs.source_tree strings have the wrong type")
    if not HEX_SHA256.fullmatch(record["sha256"]):
        raise SolverError("inputs.source_tree.sha256 is malformed")
    if type(record["root_mode"]) is not str or not OCTAL_MODE.fullmatch(
        record["root_mode"]
    ):
        raise SolverError("inputs.source_tree.root_mode is malformed")
    for key in ("directory_count", "entry_count", "file_count", "symlink_count"):
        if type(record[key]) is not int or record[key] < 0:
            raise SolverError("inputs.source_tree.{0} is invalid".format(key))
    if record["entry_count"] != (
        record["directory_count"] + record["file_count"] + record["symlink_count"]
    ):
        raise SolverError("inputs.source_tree counts do not add up")
    if record["file_count"] < 2:
        raise SolverError("inputs.source_tree does not contain the required files")


def _validate_result(result, label):
    _exact_keys(result, RESULT_SYMBOLS, label)
    for symbol in RESULT_SYMBOLS:
        if type(result[symbol]) is not str or result[symbol] not in VALUES:
            raise SolverError("{0}.{1} is not an exact tristate".format(label, symbol))
    if result[CONFIG_MODULES] not in MODULE_VALUES:
        raise SolverError("{0}.CONFIG_MODULES must be n or y".format(label))


def _validate_case(row, index, expected_request):
    label = "matrix[{0}]".format(index)
    _exact_keys(
        row,
        {
            "byte_identical",
            "case_id",
            "config_sha256_passes",
            "config_size_passes",
            "fact_scope",
            "request",
            "result",
            "selected_module_count",
            "status",
        },
        label,
    )
    expected_id = _case_id(index, expected_request)
    if type(row["case_id"]) is not str or row["case_id"] != expected_id:
        raise SolverError("{0}.case_id/order differs".format(label))
    _exact_request(row["request"], label + ".request")
    if row["request"] != expected_request:
        raise SolverError("{0}.request/order differs".format(label))
    _validate_result(row["result"], label + ".result")
    if row["result"] != oracle(expected_request):
        raise SolverError("{0}.result differs from the oracle".format(label))
    if row["byte_identical"] is not True:
        raise SolverError("{0}.byte_identical must be true".format(label))
    if row["status"] != CAPTURE_STATUS or type(row["status"]) is not str:
        raise SolverError("{0}.status must be captured-unreviewed".format(label))
    if row["fact_scope"] != REPORTED_FACT_SCOPE or type(row["fact_scope"]) is not str:
        raise SolverError("{0}.fact_scope differs".format(label))
    hashes = row["config_sha256_passes"]
    sizes = row["config_size_passes"]
    if type(hashes) is not list or len(hashes) != 2:
        raise SolverError("{0} must have exactly two config hashes".format(label))
    if type(sizes) is not list or len(sizes) != 2:
        raise SolverError("{0} must have exactly two config sizes".format(label))
    if hashes[0] != hashes[1]:
        raise SolverError("{0} config hashes are not identical".format(label))
    for digest in hashes:
        if type(digest) is not str or not HEX_SHA256.fullmatch(digest):
            raise SolverError("{0} config hash is malformed".format(label))
    for size in sizes:
        if type(size) is not int or size < 1:
            raise SolverError("{0} config size is malformed".format(label))
    if sizes[0] != sizes[1]:
        raise SolverError("{0} config sizes are not exact and identical".format(label))
    selected = sum(
        1 for symbol in MODULE_SYMBOLS if row["result"][symbol] == "m"
    )
    if type(row["selected_module_count"]) is not int or row["selected_module_count"] != selected:
        raise SolverError("{0}.selected_module_count differs".format(label))


def validate_document(document):
    _exact_keys(document, TOP_KEYS, "matrix document")
    if type(document["schema_version"]) is not int or document["schema_version"] != SCHEMA_VERSION:
        raise SolverError("schema_version differs")
    if type(document["status"]) is not str or document["status"] != CAPTURE_STATUS:
        raise SolverError("status must be captured-unreviewed")
    if document["claims"] != EXPECTED_CLAIMS:
        raise SolverError("claims must be the exact all-false non-crediting set")
    for key in EXPECTED_CLAIMS:
        if document["claims"].get(key) is not False:
            raise SolverError("claims.{0} must be false".format(key))
    if document["limitations"] != EXPECTED_LIMITATIONS:
        raise SolverError("limitations differ from the exact JSON-only boundary")
    for key in EXPECTED_LIMITATIONS:
        if type(document["limitations"].get(key)) is not str:
            raise SolverError("limitations.{0} has the wrong type".format(key))
    counts = document["counts"]
    _exact_keys(counts, EXPECTED_COUNTS, "counts")
    for key in (
        "case_count",
        "matrix_make_invocation_count",
        "negative_make_invocation_count",
        "total_make_invocation_count",
        "two_pass_byte_identical_count",
    ):
        if type(counts[key]) is not int:
            raise SolverError("counts.{0} has the wrong type".format(key))
    distribution = counts["module_result_distribution"]
    _exact_keys(
        distribution,
        EXPECTED_COUNTS["module_result_distribution"],
        "counts.module_result_distribution",
    )
    for key in ("0", "1", "2", "3"):
        if type(distribution[key]) is not int:
            raise SolverError(
                "counts.module_result_distribution.{0} has the wrong type".format(
                    key
                )
            )
    if counts != EXPECTED_COUNTS:
        raise SolverError("counts differ from the locked 54-case distribution")
    if document["runner"] != EXPECTED_RUNNER:
        raise SolverError("runner differs from the exact command/environment policy")
    runner = document["runner"]
    if type(runner) is not dict:
        raise SolverError("runner has the wrong type")
    if runner["execution"]["serial"] is not True:
        raise SolverError("runner.execution.serial must be true")
    for key in (
        "matrix_case_count",
        "negative_case_count",
        "passes_per_executed_case",
        "timeout_seconds_per_invocation",
    ):
        if type(runner["execution"][key]) is not int:
            raise SolverError("runner.execution.{0} has the wrong type".format(key))

    inputs = document["inputs"]
    _exact_keys(
        inputs,
        {"seed_config", "source_makefile", "source_tree", "staged_kconfig"},
        "inputs",
    )
    _validate_digest_record(
        inputs["seed_config"],
        "inputs.seed_config",
        "seed.config",
        {"mode"},
    )
    _validate_digest_record(
        inputs["source_makefile"],
        "inputs.source_makefile",
        "Makefile",
        {"linux_version"},
    )
    if inputs["source_makefile"].get("linux_version") != "6.12" or type(
        inputs["source_makefile"].get("linux_version")
    ) is not str:
        raise SolverError("inputs.source_makefile.linux_version must be 6.12")
    _validate_source_tree_record(inputs["source_tree"])
    _validate_digest_record(
        inputs["staged_kconfig"],
        "inputs.staged_kconfig",
        STAGED_KCONFIG_PATH,
    )

    matrix = _exact_type(document["matrix"], list, "matrix")
    requests = matrix_requests()
    if len(matrix) != len(requests):
        raise SolverError("matrix must contain exactly 54 cases")
    distribution = {"0": 0, "1": 0, "2": 0, "3": 0}
    for index, expected_request in enumerate(requests):
        _validate_case(matrix[index], index, expected_request)
        distribution[str(matrix[index]["selected_module_count"])] += 1
    if distribution != EXPECTED_COUNTS["module_result_distribution"]:
        raise SolverError("observed module distribution differs")

    negatives = document["negative_checks"]
    _exact_keys(negatives, {"rust_disabled", "x86_64_disabled_fixture"}, "negative_checks")
    rust = negatives["rust_disabled"]
    _exact_keys(
        rust,
        {
            "byte_identical",
            "case_id",
            "config_sha256_passes",
            "config_size_passes",
            "fact_scope",
            "request",
            "result",
            "selected_module_count",
            "status",
        },
        "negative_checks.rust_disabled",
    )
    rust_request = {
        CONFIG_MODULES: "y",
        CONFIG_PROVIDER: "y",
        CONFIG_SMP: "y",
        CONFIG_MCCTRL: "y",
        CONFIG_RUST: "n",
        CONFIG_X86_64: "y",
    }
    _validate_case_like_negative(rust, "negative-rust-disabled", rust_request, "negative_checks.rust_disabled")
    fixture = negatives["x86_64_disabled_fixture"]
    _exact_keys(fixture, {"executed", "reason", "request", "result", "status"}, "negative_checks.x86_64_disabled_fixture")
    fixture_request = {
        CONFIG_MODULES: "y",
        CONFIG_PROVIDER: "y",
        CONFIG_SMP: "y",
        CONFIG_MCCTRL: "y",
        CONFIG_RUST: "y",
        CONFIG_X86_64: "n",
    }
    _exact_request(fixture["request"], "negative X86 request", allow_negative=True)
    if fixture["request"] != fixture_request:
        raise SolverError("X86 fixture request differs")
    _validate_result(fixture["result"], "negative X86 result")
    if fixture["result"] != oracle(fixture_request):
        raise SolverError("X86 fixture result differs from the structural oracle")
    if fixture["executed"] is not False:
        raise SolverError("X86 fixture must not claim an ARCH=x86_64 execution")
    if fixture["status"] != "structural-fixture" or type(fixture["status"]) is not str:
        raise SolverError("X86 fixture status differs")
    expected_reason = "ARCH=x86_64 forces CONFIG_X86_64=y; the n case is a structural oracle fixture only."
    if fixture["reason"] != expected_reason or type(fixture["reason"]) is not str:
        raise SolverError("X86 fixture reason differs")
    return document


def _validate_case_like_negative(row, case_id, request, label):
    if row["case_id"] != case_id or type(row["case_id"]) is not str:
        raise SolverError("{0}.case_id differs".format(label))
    _exact_request(row["request"], label + ".request", allow_negative=True)
    if row["request"] != request:
        raise SolverError("{0}.request differs".format(label))
    _validate_result(row["result"], label + ".result")
    if row["result"] != oracle(request):
        raise SolverError("{0}.result differs".format(label))
    if row["byte_identical"] is not True or row["status"] != CAPTURE_STATUS:
        raise SolverError("{0} did not record an unreviewed two-pass capture".format(label))
    if row["fact_scope"] != REPORTED_FACT_SCOPE or type(row["fact_scope"]) is not str:
        raise SolverError("{0}.fact_scope differs".format(label))
    hashes = row["config_sha256_passes"]
    sizes = row["config_size_passes"]
    if type(hashes) is not list or len(hashes) != 2 or hashes[0] != hashes[1]:
        raise SolverError("{0} hashes differ".format(label))
    if any(
        type(item) is not str or not HEX_SHA256.fullmatch(item) for item in hashes
    ):
        raise SolverError("{0} hashes are malformed".format(label))
    if type(sizes) is not list or len(sizes) != 2:
        raise SolverError("{0} sizes differ".format(label))
    for size in sizes:
        if type(size) is not int or size < 1:
            raise SolverError("{0} sizes are malformed".format(label))
    if sizes[0] != sizes[1]:
        raise SolverError("{0} sizes differ".format(label))
    if type(row["selected_module_count"]) is not int or row["selected_module_count"] != 0:
        raise SolverError("{0} must resolve zero native Rust modules".format(label))


def validate_matrix_bytes(data):
    _ascii_no_tab_bytes(data, ARTIFACT_NAME)
    try:
        document = json.loads(data.decode("ascii"), object_pairs_hook=_reject_duplicate_pairs)
    except SolverError:
        raise
    except (ValueError, UnicodeDecodeError) as error:
        raise SolverError("invalid matrix JSON: {0}".format(error))
    validate_document(document)
    if data != canonical_json_bytes(document):
        raise SolverError("matrix JSON is not canonical compact sorted-key JSON plus LF")
    return document


def run_solver(source, seed, matrix_dir, environ=None):
    source = _safe_absolute_directory(source, "Linux source tree")
    seed = _safe_absolute_file(seed, "seed config")
    matrix_dir = _prepare_matrix_directory(matrix_dir, source)
    inputs, seed_bytes = _input_bindings(source, seed)
    environment = _sanitized_environment(environ)
    rows = []
    for index, request in enumerate(matrix_requests()):
        rows.append(
            _run_two_pass_case(
                source,
                matrix_dir,
                _case_id(index, request),
                seed_bytes,
                request,
                environment,
            )
        )
    rust_request = {
        CONFIG_MODULES: "y",
        CONFIG_PROVIDER: "y",
        CONFIG_SMP: "y",
        CONFIG_MCCTRL: "y",
        CONFIG_RUST: "n",
        CONFIG_X86_64: "y",
    }
    rust_negative = _run_two_pass_case(
        source,
        matrix_dir,
        "negative-rust-disabled",
        seed_bytes,
        rust_request,
        environment,
        allow_negative=True,
    )
    x86_request = {
        CONFIG_MODULES: "y",
        CONFIG_PROVIDER: "y",
        CONFIG_SMP: "y",
        CONFIG_MCCTRL: "y",
        CONFIG_RUST: "y",
        CONFIG_X86_64: "n",
    }
    final_inputs, final_seed = _input_bindings(source, seed)
    if final_inputs != inputs or final_seed != seed_bytes:
        raise SolverError("source tree, staged Kconfig, Makefile, or seed changed during the run")
    document = {
        "claims": dict(EXPECTED_CLAIMS),
        "counts": json.loads(json.dumps(EXPECTED_COUNTS)),
        "inputs": inputs,
        "limitations": dict(EXPECTED_LIMITATIONS),
        "matrix": rows,
        "negative_checks": {
            "rust_disabled": rust_negative,
            "x86_64_disabled_fixture": {
                "executed": False,
                "reason": "ARCH=x86_64 forces CONFIG_X86_64=y; the n case is a structural oracle fixture only.",
                "request": x86_request,
                "result": oracle(x86_request),
                "status": "structural-fixture",
            },
        },
        "runner": json.loads(json.dumps(EXPECTED_RUNNER)),
        "schema_version": SCHEMA_VERSION,
        "status": CAPTURE_STATUS,
    }
    validate_document(document)
    artifact = os.path.join(matrix_dir, ARTIFACT_NAME)
    descriptor = os.open(artifact, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        data = canonical_json_bytes(document)
        _write_all(descriptor, data, ARTIFACT_NAME)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    validate_matrix_bytes(_read_regular_file(artifact, ARTIFACT_NAME))
    return artifact, document


def check_matrix(matrix, source, seed):
    matrix = _safe_absolute_file(matrix, ARTIFACT_NAME)
    if os.path.basename(matrix) != ARTIFACT_NAME:
        raise SolverError("matrix artifact must be named {0}".format(ARTIFACT_NAME))
    source = _safe_absolute_directory(source, "Linux source tree")
    seed = _safe_absolute_file(seed, "seed config")
    document = validate_matrix_bytes(_read_regular_file(matrix, ARTIFACT_NAME))
    observed, unused_seed = _input_bindings(source, seed)
    if document["inputs"] != observed:
        raise SolverError("matrix input digests do not match source/staged-Kconfig/seed")
    if not unused_seed:
        raise SolverError("seed config is empty")
    return document


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    run = subparsers.add_parser("run", help="run all 54 cases and emit the matrix")
    run.add_argument("--source", required=True)
    run.add_argument("--seed", required=True)
    run.add_argument("--matrix-dir", required=True)
    check = subparsers.add_parser("check", help="validate a canonical emitted matrix")
    check.add_argument("--matrix", required=True)
    check.add_argument("--source", required=True)
    check.add_argument("--seed", required=True)
    return parser


def main(argv=None):
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "run":
            artifact, document = run_solver(
                arguments.source, arguments.seed, arguments.matrix_dir
            )
            print(
                "native Rust Kconfig solver: CAPTURED-UNREVIEWED cases={0} artifact={1}".format(
                    document["counts"]["case_count"], artifact
                )
            )
            return 0
        if arguments.command == "check":
            document = check_matrix(arguments.matrix, arguments.source, arguments.seed)
            print(
                "native Rust Kconfig solver matrix: CAPTURE-VALIDATED cases={0}".format(
                    document["counts"]["case_count"]
                )
            )
            return 0
        parser.error("a command is required")
    except SolverError as error:
        print("native Rust Kconfig solver: FAIL: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
