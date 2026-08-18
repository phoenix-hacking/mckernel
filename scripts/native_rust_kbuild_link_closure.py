#!/usr/bin/env python3
"""Validate raw Kbuild records for the three native Rust host modules.

The validator deliberately consumes only copied ``.cmd`` and ``.mod`` files.
It therefore remains usable after a CI artifact has been detached from the
kernel source and output trees.  A copied evidence ``stage-lock.json`` may be
supplied to bind the compiler dependency closure to the staged Rust inputs.

This is compiler/link provenance only.  It cannot prove that a module loaded,
ran, is production ready, or is eligible for tracker credit.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import sys
import tempfile


SCHEMA_ID = "mckernel-native-rust-kbuild-link-closure-v1"
MODULE_ROOT = "drivers/misc/mckernel"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_RECORD_BYTES = 2 * 1024 * 1024
MAX_STAGE_LOCK_BYTES = 1024 * 1024
STAGE_PROFILE_ID = "rocky-10.2-native-rust-host-modules-v1"

MODULES = (
    {
        "name": "ihk",
        "crate": "ihk",
        "crate_root": "ihk.rs",
        "rust_object": "ihk.o",
        "module_object": "ihk.o",
        "objtool_on_rust_object": True,
    },
    {
        "name": "ihk-smp-x86_64",
        "crate": "ihk_smp_x86_64",
        "crate_root": "ihk_smp_x86_64.rs",
        "rust_object": "ihk_smp_x86_64.o",
        "module_object": "ihk-smp-x86_64.o",
        "objtool_on_rust_object": False,
    },
    {
        "name": "mcctrl",
        "crate": "mcctrl",
        "crate_root": "mcctrl.rs",
        "rust_object": "mcctrl.o",
        "module_object": "mcctrl.o",
        "objtool_on_rust_object": True,
    },
)

EXPECTED_STAGED_FILES = (
    "Kbuild",
    "Kconfig",
    "abi/x86_64.rs",
    "ihk.rs",
    "ihk_ioctl.rs",
    "ihk_smp_x86_64.rs",
    "ikc_master.rs",
    "ikc_queue.rs",
    "mcctrl.rs",
    "os_registry.rs",
    "page_allocator.rs",
    "page_owner_registry.rs",
)
EXPECTED_STAGED_RUST_SOURCES = tuple(
    item for item in EXPECTED_STAGED_FILES if item.endswith(".rs")
)
EXPECTED_STAGE_TARGET = {
    "architecture": "x86_64",
    "config_policy_lock_id": (
        "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-config-policy-v1"
    ),
    "distribution": "Rocky Linux",
    "kernel_nvr_base": "kernel-6.12.0-211.44.1.el10_2",
    "release": "10.2",
    "resolved_config_sha256": None,
    "resolved_kernel_nvr": None,
    "resolved_toolchain_manifest_sha256": None,
    "source_lock_id": (
        "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1"
    ),
    "source_rpm_sha256": (
        "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb"
    ),
    "toolchain_lock_id": (
        "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-toolchain-v1"
    ),
}
_PROJECT_DEPENDENCIES = {
    "ihk": (
        "abi/x86_64.rs",
        "ikc_queue.rs",
        "os_registry.rs",
        "ikc_master.rs",
        "ihk_ioctl.rs",
        "page_allocator.rs",
        "page_owner_registry.rs",
    ),
    "ihk-smp-x86_64": (),
    "mcctrl": (),
}
_KERNEL_RUST_DEPENDENCIES = (
    "./rust/libcore.rmeta",
    "./rust/libkernel.rmeta",
    "./rust/liballoc.rmeta",
    "./rust/libcompiler_builtins.rmeta",
    "./rust/libmacros.so",
    "./rust/libbindings.rmeta",
    "./rust/libuapi.rmeta",
    "./rust/libbuild_error.rmeta",
)


def _cmd_name(target):
    return ".{0}.cmd".format(target.rsplit("/", 1)[-1])


EXPECTED_COMMAND_TARGETS = {}
for _module in MODULES:
    _name = _module["name"]
    _rust_object = _module["rust_object"]
    _module_object = _module["module_object"]
    for _target in (
        "{0}/{1}".format(MODULE_ROOT, _rust_object),
        "{0}/{1}.mod".format(MODULE_ROOT, _name),
        "{0}/{1}.mod.o".format(MODULE_ROOT, _name),
        "{0}/{1}.ko".format(MODULE_ROOT, _name),
    ):
        EXPECTED_COMMAND_TARGETS[_cmd_name(_target)] = _target
    if _module_object != _rust_object:
        _target = "{0}/{1}".format(MODULE_ROOT, _module_object)
        EXPECTED_COMMAND_TARGETS[_cmd_name(_target)] = _target

EXPECTED_CMD_NAMES = tuple(sorted(EXPECTED_COMMAND_TARGETS))
EXPECTED_MOD_NAMES = tuple(sorted("{0}.mod".format(item["name"]) for item in MODULES))
EXPECTED_RAW_RECORD_NAMES = tuple(sorted(EXPECTED_CMD_NAMES + EXPECTED_MOD_NAMES))

_PROJECT_PATH = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:/[A-Za-z0-9_.-]+)*/?drivers/misc/mckernel/"
    r"[A-Za-z0-9_.\-/]+)"
)
_RUST_QUOTED_ATTRIBUTE = "-Zcrate-attr='feature(arbitrary_self_types,new_uninit,used_with_arg)'"
_OBJTOOL_FLAGS = (
    "--hacks=jump_label",
    "--hacks=noinstr",
    "--hacks=skylake",
    "--ibt",
    "--mcount",
    "--mnop",
    "--orc",
    "--retpoline",
    "--rethunk",
    "--sls",
    "--static-call",
    "--uaccess",
    "--prefix=16",
    "--werror",
    "--link",
    "--module",
)
_FORBIDDEN_DRIVER_PREFIXES = (
    "-Clink-arg",
    "-Clink-args",
    "-Clinker",
    "-Cllvm-args",
    "-Cdylib",
    "-Cprefer-dynamic",
    "-Zcodegen-backend",
    "-Zllvm-plugins",
    "-fplugin",
    "-fpass-plugin",
    "-Xclang",
    "--load",
    "--plugin",
    "-plugin",
    "-load",
)
_CODE_INPUT_SUFFIXES = (
    ".a",
    ".asm",
    ".bc",
    ".c",
    ".cc",
    ".cpp",
    ".dll",
    ".dylib",
    ".h",
    ".hh",
    ".hpp",
    ".ll",
    ".o",
    ".pch",
    ".pcm",
    ".rlib",
    ".rmeta",
    ".s",
    ".so",
)
_CLANG_SAFE_FIXED_FLAGS = frozenset(
    (
        "--target=x86_64-linux-gnu",
        "-O2",
        "-c",
        "-falign-functions=16",
        "-falign-loops=1",
        "-fcf-protection=branch",
        "-fintegrated-as",
        "-fno-PIE",
        "-fno-asynchronous-unwind-tables",
        "-fno-common",
        "-fno-delete-null-pointer-checks",
        "-fno-jump-tables",
        "-fno-stack-check",
        "-fno-stack-clash-protection",
        "-fno-strict-aliasing",
        "-fno-strict-overflow",
        "-fpatchable-function-entry=16,16",
        "-fshort-wchar",
        "-fstack-protector-strong",
        "-fstrict-flex-arrays=3",
        "-ftrivial-auto-var-init=zero",
        "-funsigned-char",
        "-g",
        "-m64",
        "-mcmodel=kernel",
        "-mfentry",
        "-mharden-sls=all",
        "-mindirect-branch-cs-prefix",
        "-mfunction-return=thunk-extern",
        "-mno-3dnow",
        "-mno-80387",
        "-mno-avx",
        "-mno-fp-ret-in-387",
        "-mno-mmx",
        "-mno-red-zone",
        "-mno-sse",
        "-mno-sse2",
        "-mretpoline-external-thunk",
        "-mskip-rax-setup",
        "-mstack-alignment=8",
        "-mtune=generic",
        "-nostdinc",
        "-o",
        "-pg",
        "-std=gnu11",
    )
)


class LinkClosureError(RuntimeError):
    """Raised when raw Kbuild provenance escapes the locked graph."""


def canonical_bytes(value):
    """Return duplicate-free canonical JSON bytes with one final LF."""

    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "ascii"
    )


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LinkClosureError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def _require_keys(value, expected, label):
    if not isinstance(value, dict):
        raise LinkClosureError("{0} must be an object".format(label))
    actual = set(value)
    expected = set(expected)
    if actual != expected:
        raise LinkClosureError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(expected - actual), sorted(actual - expected)
            )
        )


def _safe_relative_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value:
        raise LinkClosureError("{0} must be a non-empty POSIX path".format(label))
    if value.startswith("/") or value != os.path.normpath(value).replace(os.sep, "/"):
        raise LinkClosureError("{0} must be a normalized relative path".format(label))
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise LinkClosureError("{0} escapes its root".format(label))
    return value


def _validated_absolute(path, label):
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise LinkClosureError("{0} must be a non-empty POSIX path".format(label))
    if raw != "/" and raw.endswith("/"):
        raise LinkClosureError("{0} has a trailing path separator".format(label))
    pieces = raw.split("/")
    if raw.startswith("/"):
        pieces = pieces[1:]
    if any(piece in ("", ".", "..") for piece in pieces):
        raise LinkClosureError("{0} contains empty, dot, or dot-dot components".format(label))
    if raw.startswith("/"):
        return raw
    return os.path.join(os.getcwd(), raw)


def _stat_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _walk_real_directories(absolute, include_leaf, label):
    pieces = absolute.split("/")[1:]
    if not include_leaf:
        pieces = pieces[:-1]
    current = "/"
    for piece in pieces:
        current = os.path.join(current, piece)
        try:
            info = os.lstat(current)
        except OSError as error:
            raise LinkClosureError("{0} ancestor is unavailable: {1}".format(label, error))
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise LinkClosureError(
                "{0} ancestor must be a real non-symlink directory: {1}".format(
                    label, current
                )
            )


def _real_directory(path, label):
    absolute = _validated_absolute(path, label)
    _walk_real_directories(absolute, True, label)
    try:
        info = os.lstat(absolute)
    except OSError as error:
        raise LinkClosureError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise LinkClosureError("{0} must be a real non-symlink directory".format(label))
    return absolute


def _recheck_identity(binding, label, directory=False):
    absolute, expected = binding
    _walk_real_directories(absolute, directory, label)
    try:
        info = os.lstat(absolute)
    except OSError as error:
        raise LinkClosureError("{0} is unavailable: {1}".format(label, error))
    expected_mode = stat.S_ISDIR if directory else stat.S_ISREG
    if stat.S_ISLNK(info.st_mode) or not expected_mode(info.st_mode):
        raise LinkClosureError("{0} type changed during validation".format(label))
    actual = _stat_identity(info)
    if (directory and actual[:3] != expected[:3]) or (
        not directory and actual != expected
    ):
        raise LinkClosureError("{0} changed during validation".format(label))


def _ascii_lf_bytes(path, label, maximum):
    absolute = _validated_absolute(path, label)
    _walk_real_directories(absolute, False, label)
    try:
        before = os.lstat(absolute)
    except OSError as error:
        raise LinkClosureError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise LinkClosureError("{0} must be a regular non-symlink file".format(label))
    if before.st_size <= 0 or before.st_size > maximum:
        raise LinkClosureError("{0} has an invalid byte size".format(label))
    if not hasattr(os, "O_NOFOLLOW"):
        raise LinkClosureError("{0} requires O_NOFOLLOW support".format(label))
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(absolute, flags)
    except OSError as error:
        raise LinkClosureError("cannot safely open {0}: {1}".format(label, error))
    try:
        opened = os.fstat(descriptor)
        if _stat_identity(opened) != _stat_identity(before):
            raise LinkClosureError("{0} changed between inspection and open".format(label))
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        if _stat_identity(after) != _stat_identity(opened):
            raise LinkClosureError("{0} changed while being read".format(label))
    finally:
        os.close(descriptor)
    binding = (absolute, _stat_identity(before))
    _recheck_identity(binding, label)
    if len(raw) > maximum:
        raise LinkClosureError("{0} is too large".format(label))
    if not raw.endswith(b"\n"):
        raise LinkClosureError("{0} must end with LF".format(label))
    if b"\r" in raw:
        raise LinkClosureError("{0} contains CR or CRLF".format(label))
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise LinkClosureError("{0} is not ASCII: {1}".format(label, error))
    for character in text:
        codepoint = ord(character)
        if character not in ("\t", "\n") and not 0x20 <= codepoint <= 0x7E:
            raise LinkClosureError(
                "{0} contains forbidden control U+{1:04X}".format(label, codepoint)
            )
    return raw, text, binding


def _load_stage_lock(path):
    raw, text, binding = _ascii_lf_bytes(path, "stage lock", MAX_STAGE_LOCK_BYTES)
    try:
        value = json.loads(text, object_pairs_hook=_object_without_duplicates)
    except (TypeError, ValueError) as error:
        raise LinkClosureError("cannot parse stage lock: {0}".format(error))
    if canonical_bytes(value) != raw:
        raise LinkClosureError("stage lock must use canonical JSON bytes")
    _require_keys(
        value,
        (
            "credit_eligible",
            "files",
            "manifest_sha256",
            "parent_integration",
            "production_readiness_blockers",
            "profile_id",
            "purpose",
            "schema_version",
            "target",
        ),
        "stage lock",
    )
    if value["credit_eligible"] is not False or value["purpose"] != "compiler-evidence-only":
        raise LinkClosureError("stage lock must remain compiler-only and credit forbidden")
    if type(value["schema_version"]) is not int or value["schema_version"] != 2:
        raise LinkClosureError("stage lock schema version differs")
    if value["profile_id"] != STAGE_PROFILE_ID:
        raise LinkClosureError("stage lock profile_id differs")
    if not isinstance(value["manifest_sha256"], str) or not HEX64.match(
        value["manifest_sha256"]
    ):
        raise LinkClosureError("stage lock manifest digest differs")
    blockers = value["production_readiness_blockers"]
    if (
        not isinstance(blockers, list)
        or not blockers
        or any(not isinstance(item, str) or not item for item in blockers)
        or len(blockers) != len(set(blockers))
    ):
        raise LinkClosureError("stage lock readiness blockers must be unique and non-empty")
    parent = value["parent_integration"]
    _require_keys(
        parent,
        ("bundle_sha256", "parent_files", "patch_sha256"),
        "stage lock parent integration",
    )
    for field in ("bundle_sha256", "patch_sha256"):
        if not isinstance(parent[field], str) or not HEX64.match(parent[field]):
            raise LinkClosureError(
                "stage lock parent integration {0} must be lowercase SHA-256".format(
                    field
                )
            )
    parent_files = parent["parent_files"]
    if not isinstance(parent_files, list) or len(parent_files) != 2:
        raise LinkClosureError("stage lock parent files differ")
    expected_parent_paths = ("drivers/misc/Makefile", "drivers/misc/Kconfig")
    for index, item in enumerate(parent_files):
        _require_keys(
            item,
            ("path", "postimage_sha256", "preimage_sha256"),
            "stage lock parent files[{0}]".format(index),
        )
        if item["path"] != expected_parent_paths[index]:
            raise LinkClosureError("stage lock parent file path or order differs")
        for field in ("postimage_sha256", "preimage_sha256"):
            if not isinstance(item[field], str) or not HEX64.match(item[field]):
                raise LinkClosureError("stage lock parent file digest differs")
    if value["target"] != EXPECTED_STAGE_TARGET:
        raise LinkClosureError("stage lock target identity or schema differs")

    files = value["files"]
    if not isinstance(files, list):
        raise LinkClosureError("stage lock files must be a list")
    normalized = []
    digests = {}
    for index, item in enumerate(files):
        _require_keys(item, ("path", "sha256"), "stage lock files[{0}]".format(index))
        relative = _safe_relative_path(item["path"], "stage lock files[{0}].path".format(index))
        digest = item["sha256"]
        if not isinstance(digest, str) or not HEX64.match(digest):
            raise LinkClosureError("stage lock file digest must be lowercase SHA-256")
        if relative in digests:
            raise LinkClosureError("stage lock contains duplicate paths")
        normalized.append(relative)
        digests[relative] = digest
    if tuple(normalized) != EXPECTED_STAGED_FILES:
        raise LinkClosureError("stage lock staged file set or order differs")
    return raw, value, digests, binding


def _project_relative(path, label, require_absolute=False):
    if not isinstance(path, str) or not path or "\\" in path:
        raise LinkClosureError("{0} must be a POSIX path".format(label))
    marker = MODULE_ROOT + "/"
    if path.count(marker) != 1:
        raise LinkClosureError("{0} is not under the staged module root".format(label))
    prefix, relative = path.split(marker, 1)
    relative = _safe_relative_path(relative, label)
    if require_absolute:
        if not prefix.startswith("/") or not prefix.endswith("/"):
            raise LinkClosureError("{0} must be an absolute staged source path".format(label))
        if "//" in prefix or any(item in ("", ".", "..") for item in prefix[1:-1].split("/")):
            raise LinkClosureError("{0} has a non-normalized source root".format(label))
    elif prefix not in ("", "./"):
        raise LinkClosureError("{0} must use the Kbuild-relative module root".format(label))
    return relative, prefix[:-1] if prefix.endswith("/") else prefix


def _shell_tokens(command, label, allowed_quotes=()):
    stripped = command
    for quoted in allowed_quotes:
        if stripped.count(quoted) != 1:
            raise LinkClosureError("{0} required quoted argument differs".format(label))
        stripped = stripped.replace(quoted, "ALLOWED_QUOTED_ARGUMENT", 1)
    if "'" in stripped or '"' in stripped:
        raise LinkClosureError("{0} contains extra shell quotes".format(label))
    for marker in (
        "`",
        "$",
        "#",
        "~",
        "\\",
        "|",
        "&",
        ";",
        "<",
        ">",
        "*",
        "?",
        "[",
        "]",
        "{",
        "}",
    ):
        if marker in stripped:
            raise LinkClosureError("{0} contains forbidden shell syntax: {1}".format(label, marker))
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as error:
        raise LinkClosureError("{0} cannot be tokenized: {1}".format(label, error))
    if not tokens:
        raise LinkClosureError("{0} is empty".format(label))
    return tokens


def _require_once(tokens, token, label):
    if tokens.count(token) != 1:
        raise LinkClosureError("{0} must contain exactly one {1}".format(label, token))


def _require_pair(tokens, option, value, label):
    indices = [index for index, token in enumerate(tokens) if token == option]
    if len(indices) != 1 or indices[0] + 1 >= len(tokens) or tokens[indices[0] + 1] != value:
        raise LinkClosureError("{0} {1} value differs".format(label, option))


def _reject_driver_injection(tokens, label):
    for token in tokens:
        lowered = token.lower()
        if any(lowered.startswith(prefix.lower()) for prefix in _FORBIDDEN_DRIVER_PREFIXES):
            raise LinkClosureError("{0} contains a plugin, preload, or alternate-driver flag".format(label))
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            raise LinkClosureError("{0} contains an unexpected environment assignment".format(label))


def _macro_name(payload):
    name = payload.split("=", 1)[0].split("(", 1)[0]
    return name


def _protected_macro_operations(tokens, protected):
    operations = []
    cursor = 0
    while cursor < len(tokens):
        token = tokens[cursor]
        operator = None
        payload = None
        spelling = token
        if token in ("-D", "-U", "--define-macro", "--undefine-macro"):
            operator = "-D" if token in ("-D", "--define-macro") else "-U"
            if cursor + 1 >= len(tokens):
                payload = ""
            else:
                payload = tokens[cursor + 1]
                spelling = token + " " + payload
                cursor += 1
        elif token.startswith("-D") and len(token) > 2:
            operator = "-D"
            payload = token[2:]
        elif token.startswith("-U") and len(token) > 2:
            operator = "-U"
            payload = token[2:]
        elif token.startswith("--define-macro="):
            operator = "-D"
            payload = token.split("=", 1)[1]
        elif token.startswith("--undefine-macro="):
            operator = "-U"
            payload = token.split("=", 1)[1]
        if operator is not None and _macro_name(payload) in protected:
            operations.append((_macro_name(payload), operator, spelling))
        cursor += 1
    return operations


def _objtool_tokens(target):
    return ["./tools/objtool/objtool"] + list(_OBJTOOL_FLAGS) + [target]


def _split_objtool(command, require_objtool, label):
    if command.count(";") > 1:
        raise LinkClosureError("{0} contains extra shell commands".format(label))
    pieces = command.split(" ; ")
    expected_count = 2 if require_objtool else 1
    if len(pieces) != expected_count or any(not item.strip() for item in pieces):
        raise LinkClosureError("{0} objtool command structure differs".format(label))
    if ";" in pieces[0] or (len(pieces) == 2 and ";" in pieces[1]):
        raise LinkClosureError("{0} contains a noncanonical command separator".format(label))
    return [item.strip() for item in pieces]


def _parse_saved_command(name, target, text):
    prefix = "savedcmd_{0} := ".format(target)
    lines = text.splitlines()
    if not lines or not lines[0].startswith(prefix) or lines[0] == prefix:
        raise LinkClosureError("{0} savedcmd target differs".format(name))
    if text.count("savedcmd_") != 1:
        raise LinkClosureError("{0} must contain exactly one savedcmd assignment".format(name))
    return lines[0][len(prefix) :]


def _source_assignment(text, target, label):
    prefix = "source_{0} := ".format(target)
    values = [line[len(prefix) :] for line in text.splitlines() if line.startswith(prefix)]
    if len(values) != 1 or not values[0]:
        raise LinkClosureError("{0} source assignment differs".format(label))
    return values[0]


def _project_references(text, label):
    references = []
    for match in _PROJECT_PATH.finditer(text):
        value = match.group(1)
        relative, unused = _project_relative(
            value,
            "{0} project reference".format(label),
            require_absolute=value.startswith("/"),
        )
        references.append(relative)
    return references


def _validate_reference_surface(name, references, module):
    known = set(EXPECTED_STAGED_RUST_SOURCES)
    for item in MODULES:
        known.update(
            (
                item["name"],
                item["rust_object"],
                item["module_object"],
                ".{0}.d".format(item["rust_object"]),
                ".{0}.mod.o.d".format(item["name"]),
                "{0}.ko".format(item["name"]),
                "{0}.mod".format(item["name"]),
                "{0}.mod.c".format(item["name"]),
                "{0}.mod.o".format(item["name"]),
            )
        )
    for relative in references:
        if relative not in known:
            raise LinkClosureError("{0} references an unknown staged project path".format(name))
        if relative.lower().endswith(".c"):
            expected = "{0}.mod.c".format(module["name"])
            if relative != expected or name != ".{0}.mod.o.cmd".format(module["name"]):
                raise LinkClosureError("{0} references project C outside generated mod.c".format(name))


def _parse_rust_dependency_body(name, target, text, root_token, source_prefix, module):
    lines = text.splitlines()
    source_line = "source_{0} := {1}".format(target, root_token)
    dependency_head = "deps_{0} := \\".format(target)
    if len(lines) < 10 or lines[1:5] != ["", source_line, "", dependency_head]:
        raise LinkClosureError("{0} source/dependency record grammar differs".format(name))

    cursor = 5
    dependencies = []
    while cursor < len(lines) and lines[cursor]:
        line = lines[cursor]
        if not line.startswith("  ") or not line.endswith(" \\"):
            raise LinkClosureError("{0} dependency entry grammar differs".format(name))
        dependency = line[2:-2]
        if not dependency or any(character.isspace() for character in dependency):
            raise LinkClosureError("{0} dependency entry is not one path".format(name))
        dependencies.append(dependency)
        cursor += 1
    if cursor >= len(lines) or not dependencies:
        raise LinkClosureError("{0} dependency block is unterminated or empty".format(name))

    tail = [
        "",
        "{0}: $(deps_{0})".format(target),
        "",
        "$(deps_{0}):".format(target),
    ]
    if module["objtool_on_rust_object"]:
        tail.extend(
            (
                "",
                "{0}: $(wildcard ./tools/objtool/objtool)".format(target),
            )
        )
    if lines[cursor:] != tail:
        raise LinkClosureError("{0} dependency tail or extra content differs".format(name))

    staged_root = "{0}/{1}/".format(source_prefix, MODULE_ROOT)
    project_dependencies = _PROJECT_DEPENDENCIES[module["name"]]
    expected = [staged_root + item for item in project_dependencies]
    expected.extend(_KERNEL_RUST_DEPENDENCIES)
    if dependencies != expected:
        raise LinkClosureError(
            "{0} compiler dependency closure differs: expected={1}, actual={2}".format(
                name, expected, dependencies
            )
        )
    for index, relative in enumerate(project_dependencies):
        parsed, prefix = _project_relative(
            dependencies[index],
            "{0} project dependency".format(name),
            require_absolute=True,
        )
        if parsed != relative or prefix != source_prefix:
            raise LinkClosureError(
                "{0} project dependency escapes the crate-root source tree".format(name)
            )
    return [module["crate_root"]] + list(project_dependencies)


def _parse_rust_record(name, target, command, text, module):
    pieces = _split_objtool(command, module["objtool_on_rust_object"], name)
    compile_command = pieces[0]
    tokens = _shell_tokens(
        compile_command,
        name + " rustc command",
        allowed_quotes=(_RUST_QUOTED_ATTRIBUTE,),
    )
    expected_modfile = "RUST_MODFILE={0}/{1}".format(MODULE_ROOT, module["name"])
    if len(tokens) < 3 or tokens[0] != expected_modfile or tokens[1] != "rustc":
        raise LinkClosureError("{0} must be owned by bare rustc with the exact RUST_MODFILE".format(name))
    compiler_tokens = tokens[1:]
    _reject_driver_injection(compiler_tokens, name)
    _require_pair(compiler_tokens, "--crate-name", module["crate"], name)
    _require_pair(compiler_tokens, "--crate-type", "rlib", name)
    _require_pair(compiler_tokens, "--out-dir", MODULE_ROOT + "/", name)
    _require_pair(compiler_tokens, "-L", "./rust/", name)
    extern_indices = [
        index for index, token in enumerate(compiler_tokens) if token == "--extern"
    ]
    if (
        len(extern_indices) != 2
        or any(index + 1 >= len(compiler_tokens) for index in extern_indices)
        or [compiler_tokens[index + 1] for index in extern_indices]
        != ["force:alloc", "kernel"]
    ):
        raise LinkClosureError("{0} Rust extern input surface differs".format(name))
    for required in (
        "--edition=2021",
        "--target=./scripts/target.json",
        "--cfg",
        "MODULE",
        "--sysroot=/dev/null",
        "force:alloc",
        "kernel",
        "@./include/generated/rustc_cfg",
        _RUST_QUOTED_ATTRIBUTE.replace("'", ""),
    ):
        _require_once(compiler_tokens, required, name)
    output = "{0}/{1}".format(MODULE_ROOT, module["rust_object"])
    depinfo = "--emit=dep-info={0}/.{1}.d".format(MODULE_ROOT, module["rust_object"])
    object_output = "--emit=obj={0}".format(output)
    _require_once(compiler_tokens, depinfo, name)
    _require_once(compiler_tokens, object_output, name)
    responses = [token for token in compiler_tokens if token.startswith("@")]
    if responses != ["@./include/generated/rustc_cfg"]:
        raise LinkClosureError("{0} rustc response-file surface differs".format(name))
    root_token = compiler_tokens[-1]
    relative_root, source_prefix = _project_relative(
        root_token, name + " crate root", require_absolute=True
    )
    if relative_root != module["crate_root"]:
        raise LinkClosureError("{0} crate root differs".format(name))
    rust_inputs = [token for token in compiler_tokens if token.endswith(".rs")]
    if rust_inputs != [root_token]:
        raise LinkClosureError("{0} has extra compiler source inputs".format(name))
    for token in compiler_tokens:
        lowered = token.lower()
        if token in ("-C", "-Z", "-o", "--sysroot", "--target"):
            raise LinkClosureError("{0} contains a split compiler override".format(name))
        if token.startswith("--sysroot=") and token != "--sysroot=/dev/null":
            raise LinkClosureError("{0} contains an alternate sysroot".format(name))
        if token.startswith("--target=") and token != "--target=./scripts/target.json":
            raise LinkClosureError("{0} contains an alternate compiler target".format(name))
        if token.startswith("--emit=") and token not in (depinfo, object_output):
            raise LinkClosureError("{0} contains an extra compiler emission".format(name))
        if token.startswith("--extern=") or (token.startswith("-L") and token != "-L"):
            raise LinkClosureError("{0} contains an extra Rust dependency search input".format(name))
        if token == "-l" or (token.startswith("-l") and len(token) > 2):
            raise LinkClosureError("{0} contains an extra native library input".format(name))
        if lowered.endswith(_CODE_INPUT_SUFFIXES) and token not in (root_token, object_output):
            raise LinkClosureError("{0} consumes an extra source or prebuilt input".format(name))

    if module["objtool_on_rust_object"]:
        objtool = _shell_tokens(pieces[1], name + " objtool command")
        if objtool != _objtool_tokens(output):
            raise LinkClosureError("{0} objtool command differs".format(name))

    sources = _parse_rust_dependency_body(
        name, target, text, root_token, source_prefix, module
    )
    return sorted(sources), source_prefix


def _parse_mod_generator(name, target, command, module):
    normalized = re.sub(r"[ \t]+", " ", command).strip()
    expected = (
        "printf '%s\\n' {0} | awk '!x[$$0]++ {{ print(\"{1}/\"$$0) }}' > {1}/{2}.mod"
    ).format(module["rust_object"], MODULE_ROOT, module["name"])
    if normalized != expected:
        raise LinkClosureError("{0} object-list generator differs".format(name))
    if target != "{0}/{1}.mod".format(MODULE_ROOT, module["name"]):
        raise LinkClosureError("{0} object-list target differs".format(name))


def _parse_generated_mod(name, target, command, text, module, source_prefix):
    basename = "{0}.mod".format(module["crate"])
    raw_basename = "-DKBUILD_BASENAME='\"{0}\"'".format(basename)
    raw_modname = "-DKBUILD_MODNAME='\"{0}\"'".format(module["crate"])
    tokens = _shell_tokens(
        command,
        name + " clang command",
        allowed_quotes=(raw_basename, raw_modname),
    )
    if tokens[0] != "clang":
        raise LinkClosureError("{0} generated mod.c must be compiled by bare clang".format(name))
    _reject_driver_injection(tokens[1:], name)
    output = "{0}/{1}.mod.o".format(MODULE_ROOT, module["name"])
    source = "{0}/{1}.mod.c".format(MODULE_ROOT, module["name"])
    required_tokens = (
        "-nostdinc",
        "--target=x86_64-linux-gnu",
        "-std=gnu11",
        "-D__KERNEL__",
        "-DMODULE",
        '-DKBUILD_BASENAME="{0}"'.format(basename),
        '-DKBUILD_MODNAME="{0}"'.format(module["crate"]),
        "-D__KBUILD_MODNAME={0}".format(module["crate"]),
        "-c",
    )
    for required in required_tokens:
        _require_once(tokens, required, name)

    protected_macros = (
        "__KERNEL__",
        "MODULE",
        "KBUILD_BASENAME",
        "KBUILD_MODNAME",
        "__KBUILD_MODNAME",
    )
    expected_macro_operations = [
        ("__KERNEL__", "-D", "-D__KERNEL__"),
        ("MODULE", "-D", "-DMODULE"),
        (
            "KBUILD_BASENAME",
            "-D",
            '-DKBUILD_BASENAME="{0}"'.format(basename),
        ),
        (
            "KBUILD_MODNAME",
            "-D",
            '-DKBUILD_MODNAME="{0}"'.format(module["crate"]),
        ),
        (
            "__KBUILD_MODNAME",
            "-D",
            "-D__KBUILD_MODNAME={0}".format(module["crate"]),
        ),
    ]
    actual_macro_operations = _protected_macro_operations(tokens, protected_macros)
    if actual_macro_operations != expected_macro_operations:
        raise LinkClosureError(
            "{0} protected compiler macro definitions differ: expected={1}, actual={2}".format(
                name, expected_macro_operations, actual_macro_operations
            )
        )

    expected_include_paths = [
        source_prefix + "/arch/x86/include",
        "./arch/x86/include/generated",
        source_prefix + "/include",
        "./include",
        source_prefix + "/arch/x86/include/uapi",
        "./arch/x86/include/generated/uapi",
        source_prefix + "/include/uapi",
        "./include/generated/uapi",
    ]
    include_paths = [token[2:] for token in tokens if token.startswith("-I")]
    if include_paths != expected_include_paths:
        raise LinkClosureError("{0} include search input closure differs".format(name))
    include_indices = [index for index, token in enumerate(tokens) if token == "-include"]
    if any(index + 1 >= len(tokens) for index in include_indices):
        raise LinkClosureError("{0} has an unterminated forced include".format(name))
    forced_includes = [tokens[index + 1] for index in include_indices]
    expected_forced_includes = [
        source_prefix + "/include/linux/compiler-version.h",
        source_prefix + "/include/linux/kconfig.h",
        source_prefix + "/include/linux/compiler_types.h",
    ]
    if forced_includes != expected_forced_includes:
        raise LinkClosureError("{0} forced-include input closure differs".format(name))
    macro_map = "-fmacro-prefix-map={0}/=".format(source_prefix)
    _require_once(tokens, macro_map, name)
    dependency_output = "-Wp,-MMD,{0}/.{1}.mod.o.d".format(
        MODULE_ROOT, module["name"]
    )
    _require_once(tokens, dependency_output, name)
    if any(token.startswith("-Wp,") and token != dependency_output for token in tokens):
        raise LinkClosureError("{0} preprocessor response surface differs".format(name))
    if any(
        token.startswith("-fmacro-prefix-map=") and token != macro_map
        for token in tokens
    ):
        raise LinkClosureError("{0} contains an alternate macro-prefix map".format(name))
    forbidden_long_input_options = (
        "--config",
        "--gcc-toolchain",
        "--resource-dir",
        "--sysroot",
        "-config",
        "-fmodule-file",
        "-fmodule-map-file",
        "-fmodules-cache-path",
        "-gcc-toolchain",
        "-include=",
    )
    forbidden_joined_input_prefixes = (
        "-B",
        "-fprofile-sample-use",
        "-fprofile-use",
        "-idirafter",
        "-imacros",
        "-include-pch",
        "-iquote",
        "-isysroot",
        "-isystem",
        "-ivfsoverlay",
        "-resource-dir",
    )
    for token in tokens:
        if token.startswith("-include") and token != "-include":
            raise LinkClosureError(
                "{0} contains a joined or alternate forced include".format(name)
            )
        if token in ("--target", "-target") or token.startswith("-target="):
            raise LinkClosureError("{0} contains an alternate compiler target".format(name))
        if token.startswith("--target=") and token != "--target=x86_64-linux-gnu":
            raise LinkClosureError("{0} contains an alternate compiler target".format(name))
        if token.startswith(("-Wa,", "-Wl,")) or token in (
            "-Xassembler",
            "-Xlinker",
        ):
            raise LinkClosureError(
                "{0} contains an assembler/linker response or injection surface".format(
                    name
                )
            )
        if token == "-I" or any(
            token == option or token.startswith(option + "=")
            for option in forbidden_long_input_options
        ):
            raise LinkClosureError(
                "{0} contains an external compiler input option: {1}".format(
                    name, token
                )
            )
        if any(token.startswith(prefix) for prefix in forbidden_joined_input_prefixes):
            raise LinkClosureError(
                "{0} contains a joined external compiler input option".format(name)
            )
        if token.startswith("-fmodule-") or token.startswith("-fmodules-"):
            raise LinkClosureError("{0} contains an external Clang module input".format(name))
        if token == "-Xpreprocessor":
            raise LinkClosureError("{0} contains a preprocessor injection option".format(name))
    _require_pair(tokens, "-o", output, name)
    if tokens[-1] != source or [token for token in tokens if token.endswith(".c")] != [source]:
        raise LinkClosureError("{0} must compile only its generated mod.c".format(name))
    if any(token.startswith("@") for token in tokens):
        raise LinkClosureError("{0} generated mod.c command cannot use response files".format(name))
    for token in tokens:
        if token == "-l" or (token.startswith("-l") and len(token) > 2):
            raise LinkClosureError("{0} contains an extra native library input".format(name))
        allowed_inputs = (source, output) + tuple(expected_forced_includes)
        if token.lower().endswith(_CODE_INPUT_SUFFIXES) and token not in allowed_inputs:
            raise LinkClosureError("{0} consumes an extra source or prebuilt input".format(name))
    allowed_tokens = set(_CLANG_SAFE_FIXED_FLAGS)
    allowed_tokens.update(
        [
            "clang",
            dependency_output,
            macro_map,
            source,
            output,
            "-include",
        ]
    )
    allowed_tokens.update("-I" + item for item in expected_include_paths)
    allowed_tokens.update(expected_forced_includes)
    for token in tokens:
        if token in allowed_tokens:
            continue
        if token.startswith("-D") or token.startswith("-U"):
            continue
        if token.startswith("-W") and not token.startswith(("-Wa,", "-Wl,", "-Wp,")):
            continue
        raise LinkClosureError(
            "{0} contains an unclassified compiler token: {1}".format(name, token)
        )
    if _source_assignment(text, target, name) != source:
        raise LinkClosureError("{0} generated source assignment differs".format(name))


def _parse_aggregate(name, target, command, module):
    pieces = _split_objtool(command, True, name)
    link = _shell_tokens(pieces[0], name + " aggregate link")
    response = "@{0}/{1}.mod".format(MODULE_ROOT, module["name"])
    expected = [
        "ld.lld",
        "-m",
        "elf_x86_64",
        "-z",
        "noexecstack",
        "-r",
        "-o",
        target,
        response,
    ]
    if link != expected:
        raise LinkClosureError("{0} aggregate link or response member differs".format(name))
    objtool = _shell_tokens(pieces[1], name + " objtool command")
    if objtool != _objtool_tokens(target):
        raise LinkClosureError("{0} aggregate objtool command differs".format(name))


def _parse_final_link(name, target, command, module):
    tokens = _shell_tokens(command, name + " final link")
    module_object = "{0}/{1}".format(MODULE_ROOT, module["module_object"])
    generated = "{0}/{1}.mod.o".format(MODULE_ROOT, module["name"])
    expected = [
        "ld.lld",
        "-r",
        "-m",
        "elf_x86_64",
        "-z",
        "noexecstack",
        "--build-id=sha1",
        "-T",
        "scripts/module.lds",
        "-o",
        target,
        module_object,
        generated,
        ".module-common.o",
    ]
    if tokens != expected:
        raise LinkClosureError("{0} final link roots differ".format(name))
    return [module_object, generated, ".module-common.o"]


def _validate_record_set(records_dir):
    records_dir = _real_directory(records_dir, "records directory")
    directory_binding = (records_dir, _stat_identity(os.lstat(records_dir)))
    try:
        names = os.listdir(records_dir)
    except OSError as error:
        raise LinkClosureError("cannot list records directory: {0}".format(error))
    relevant = sorted(
        name for name in names if name.endswith(".cmd") or name.endswith(".mod")
    )
    if tuple(relevant) != EXPECTED_RAW_RECORD_NAMES:
        raise LinkClosureError(
            "raw record set differs: missing={0}, extra={1}".format(
                sorted(set(EXPECTED_RAW_RECORD_NAMES) - set(relevant)),
                sorted(set(relevant) - set(EXPECTED_RAW_RECORD_NAMES)),
            )
        )
    raw = {}
    text = {}
    bindings = {}
    for name in EXPECTED_RAW_RECORD_NAMES:
        record_raw, record_text, binding = _ascii_lf_bytes(
            os.path.join(records_dir, name), "raw record {0}".format(name), MAX_RECORD_BYTES
        )
        raw[name] = record_raw
        text[name] = record_text
        bindings[name] = binding
    return records_dir, raw, text, bindings, directory_binding


def validate_kbuild_link_closure(records_dir, stage_lock_path=None):
    """Validate copied records and return their canonical closure object."""

    records_dir, raw, texts, record_bindings, directory_binding = _validate_record_set(
        records_dir
    )
    stage_value = None
    stage_binding_identity = None
    stage_digests = dict((item, None) for item in EXPECTED_STAGED_FILES)
    if stage_lock_path is not None:
        stage_raw, stage_value, stage_digests, stage_binding_identity = _load_stage_lock(
            stage_lock_path
        )
        stage_binding = {
            "manifest_sha256": stage_value["manifest_sha256"],
            "profile_id": stage_value["profile_id"],
            "schema_version": stage_value["schema_version"],
            "sha256": _sha256(stage_raw),
        }
    else:
        stage_binding = None

    module_results = []
    all_sources = set()
    source_prefixes = set()
    for module in MODULES:
        rust_target = "{0}/{1}".format(MODULE_ROOT, module["rust_object"])
        rust_name = _cmd_name(rust_target)
        rust_command = _parse_saved_command(
            rust_name, rust_target, texts[rust_name]
        )
        sources, source_prefix = _parse_rust_record(
            rust_name, rust_target, rust_command, texts[rust_name], module
        )
        all_sources.update(sources)
        source_prefixes.add(source_prefix)

        mod_target = "{0}/{1}.mod".format(MODULE_ROOT, module["name"])
        mod_name = _cmd_name(mod_target)
        mod_command = _parse_saved_command(mod_name, mod_target, texts[mod_name])
        _parse_mod_generator(mod_name, mod_target, mod_command, module)
        expected_response = "{0}/{1}\n".format(MODULE_ROOT, module["rust_object"]).encode(
            "ascii"
        )
        response_name = "{0}.mod".format(module["name"])
        if raw[response_name] != expected_response:
            raise LinkClosureError("{0} raw object-list response differs".format(response_name))

        generated_target = "{0}/{1}.mod.o".format(MODULE_ROOT, module["name"])
        generated_name = _cmd_name(generated_target)
        generated_command = _parse_saved_command(
            generated_name, generated_target, texts[generated_name]
        )
        _parse_generated_mod(
            generated_name,
            generated_target,
            generated_command,
            texts[generated_name],
            module,
            source_prefix,
        )

        if module["module_object"] != module["rust_object"]:
            aggregate_target = "{0}/{1}".format(MODULE_ROOT, module["module_object"])
            aggregate_name = _cmd_name(aggregate_target)
            aggregate_command = _parse_saved_command(
                aggregate_name, aggregate_target, texts[aggregate_name]
            )
            _parse_aggregate(aggregate_name, aggregate_target, aggregate_command, module)

        final_target = "{0}/{1}.ko".format(MODULE_ROOT, module["name"])
        final_name = _cmd_name(final_target)
        final_command = _parse_saved_command(
            final_name, final_target, texts[final_name]
        )
        final_inputs = _parse_final_link(final_name, final_target, final_command, module)

        for record_name in (
            rust_name,
            mod_name,
            generated_name,
            final_name,
        ) + (
            (_cmd_name("{0}/{1}".format(MODULE_ROOT, module["module_object"])),)
            if module["module_object"] != module["rust_object"]
            else ()
        ):
            references = _project_references(texts[record_name], record_name)
            _validate_reference_surface(record_name, references, module)

        module_results.append(
            {
                "crate": module["crate"],
                "crate_root": module["crate_root"],
                "final_link_inputs": final_inputs,
                "final_module": final_target,
                "module": module["name"],
                "module_object": "{0}/{1}".format(MODULE_ROOT, module["module_object"]),
                "raw_object_list": ["{0}/{1}".format(MODULE_ROOT, module["rust_object"])],
                "rust_object": "{0}/{1}".format(MODULE_ROOT, module["rust_object"]),
                "source_dependencies": sources,
            }
        )

    if len(source_prefixes) != 1:
        raise LinkClosureError("Rust crate roots do not share one staged source tree")
    if tuple(sorted(all_sources)) != tuple(sorted(EXPECTED_STAGED_RUST_SOURCES)):
        raise LinkClosureError(
            "compiler Rust source closure differs: missing={0}, extra={1}".format(
                sorted(set(EXPECTED_STAGED_RUST_SOURCES) - all_sources),
                sorted(all_sources - set(EXPECTED_STAGED_RUST_SOURCES)),
            )
        )

    raw_records = [
        {"name": name, "sha256": _sha256(raw[name]), "size": len(raw[name])}
        for name in EXPECTED_RAW_RECORD_NAMES
    ]
    _recheck_identity(directory_binding, "records directory", directory=True)
    try:
        final_names = os.listdir(records_dir)
    except OSError as error:
        raise LinkClosureError("cannot relist records directory: {0}".format(error))
    final_relevant = tuple(
        sorted(
            name
            for name in final_names
            if name.endswith(".cmd") or name.endswith(".mod")
        )
    )
    if final_relevant != EXPECTED_RAW_RECORD_NAMES:
        raise LinkClosureError("raw record set changed during validation")
    for name in EXPECTED_RAW_RECORD_NAMES:
        _recheck_identity(record_bindings[name], "raw record {0}".format(name))
        final_raw, unused_text, final_binding = _ascii_lf_bytes(
            os.path.join(records_dir, name),
            "raw record {0}".format(name),
            MAX_RECORD_BYTES,
        )
        if final_raw != raw[name] or final_binding[1] != record_bindings[name][1]:
            raise LinkClosureError("raw record {0} changed during validation".format(name))
    if stage_binding_identity is not None:
        _recheck_identity(stage_binding_identity, "stage lock")

    return {
        "claims": {
            "complete_external_build_input_closure": False,
            "credit_eligible": False,
            "load_proven": False,
            "production_ready": False,
            "runtime_proven": False,
        },
        "compilers": {
            "generated_module_source": "clang",
            "linker": "ld.lld",
            "object_postprocessor": "./tools/objtool/objtool",
            "project_source": "rustc",
        },
        "modules": module_results,
        "purpose": "detached compiler and final-link provenance; no runtime or gate credit",
        "raw_record_names": list(EXPECTED_RAW_RECORD_NAMES),
        "raw_records": raw_records,
        "raw_records_sha256": _sha256(canonical_bytes(raw_records)),
        "schema_id": SCHEMA_ID,
        "source_closure": [
            {"path": path, "stage_sha256": stage_digests[path]}
            for path in EXPECTED_STAGED_RUST_SOURCES
        ],
        "source_closure_scope": (
            "staged McKernel Rust project sources named by rustc dependency records; "
            "kernel headers, generated kernel metadata, libraries, and toolchain binaries "
            "remain outside this closure"
        ),
        "stage_lock": stage_binding,
    }


def _safe_output_path(path, label):
    absolute = _validated_absolute(path, label)
    parent = _real_directory(os.path.dirname(absolute) or ".", label + " parent")
    if os.path.lexists(absolute):
        try:
            info = os.lstat(absolute)
        except OSError as error:
            raise LinkClosureError("cannot inspect {0}: {1}".format(label, error))
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise LinkClosureError("{0} must be a regular non-symlink file".format(label))
    return absolute, parent


def write_kbuild_link_closure(records_dir, output_path, stage_lock_path=None):
    """Validate records and atomically write compact canonical JSON."""

    value = validate_kbuild_link_closure(records_dir, stage_lock_path=stage_lock_path)
    output, parent = _safe_output_path(output_path, "output")
    if os.path.basename(output) in EXPECTED_RAW_RECORD_NAMES:
        raise LinkClosureError("output cannot overwrite a raw Kbuild record")
    if stage_lock_path is not None and output == _validated_absolute(
        stage_lock_path, "stage lock"
    ):
        raise LinkClosureError("output cannot overwrite the stage lock")
    parent_binding = (parent, _stat_identity(os.lstat(parent)))
    payload = canonical_bytes(value)
    descriptor, temporary = tempfile.mkstemp(prefix=".kbuild-link-closure.", dir=parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        _recheck_identity(parent_binding, "output parent", directory=True)
        os.replace(temporary, output)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return value


def check_kbuild_link_closure(records_dir, output_path, stage_lock_path=None):
    """Reparse raw records and require an exact canonical output file."""

    value = validate_kbuild_link_closure(records_dir, stage_lock_path=stage_lock_path)
    raw, unused, binding = _ascii_lf_bytes(
        output_path, "link closure output", MAX_RECORD_BYTES
    )
    if raw != canonical_bytes(value):
        raise LinkClosureError("link closure output differs from reparsed raw records")
    _recheck_identity(binding, "link closure output")
    return value


def _arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--stage-lock")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output")
    action.add_argument("--check-output")
    return parser.parse_args(argv)


def main(argv=None):
    args = _arguments(argv)
    try:
        if args.output:
            write_kbuild_link_closure(
                args.records_dir, args.output, stage_lock_path=args.stage_lock
            )
        else:
            check_kbuild_link_closure(
                args.records_dir, args.check_output, stage_lock_path=args.stage_lock
            )
    except LinkClosureError as error:
        print("native Rust Kbuild link closure: {0}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
