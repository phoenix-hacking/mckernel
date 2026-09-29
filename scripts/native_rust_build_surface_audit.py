#!/usr/bin/env python3
"""Enforce one fail-closed Kconfig/Kbuild authority for native Rust modules."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import stat
import sys

if __package__:
    from .native_rust_kconfig_policy import (
        KconfigPolicyError,
        validate_native_rust_kbuild,
        validate_native_rust_kconfig,
    )
else:
    from native_rust_kconfig_policy import (
        KconfigPolicyError,
        validate_native_rust_kbuild,
        validate_native_rust_kconfig,
    )


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = "host-kernel/kbuild/stage-manifest.json"
NATIVE_ROOT = "host-kernel/native-rust"
AUTHORITATIVE_INPUTS = {
    "Kbuild": "host-kernel/kbuild/Kbuild.in",
    "Kconfig": "host-kernel/kbuild/Kconfig",
}
SUPPLEMENTAL_INPUTS = {
    "abi/x86_64.rs": "host-kernel/native-rust/abi/x86_64.rs",
    "ikc_master.rs": "host-kernel/native-rust/ikc_master.rs",
    "ikc_queue.rs": "host-kernel/native-rust/ikc_queue.rs",
    "os_registry.rs": "host-kernel/native-rust/os_registry.rs",
    "device_registry.rs": "host-kernel/native-rust/device_registry.rs",
    "ihk_ioctl.rs": "host-kernel/native-rust/ihk_ioctl.rs",
    "page_allocator.rs": "host-kernel/native-rust/page_allocator.rs",
    "page_owner_registry.rs": "host-kernel/native-rust/page_owner_registry.rs",
    "smp_resource.rs": "host-kernel/native-rust/smp_resource.rs",
    "smp_cpu.rs": "host-kernel/native-rust/smp_cpu.rs",
    "smp_memory.rs": "host-kernel/native-rust/smp_memory.rs",
    "os_runtime.rs": "host-kernel/native-rust/os_runtime.rs",
    "os_service.rs": "host-kernel/native-rust/os_service.rs",
    "abi/os_service.rs": "host-kernel/native-rust/abi/os_service.rs",
    "abi/application.rs": "host-kernel/native-rust/abi/application.rs",
    "ihk_mapping.rs": "host-kernel/native-rust/ihk_mapping.rs",
    "smp_image.rs": "host-kernel/native-rust/smp_image.rs",
    "smp_loader.rs": "host-kernel/native-rust/smp_loader.rs",
    "smp_startup.rs": "host-kernel/native-rust/smp_startup.rs",
}
CRATE_ROOTS = ("ihk.rs", "ihk_smp_x86_64.rs", "mcctrl.rs")
GENERATED_INPUTS = frozenset(("ihk-compat-build-id.bin",))
FORBIDDEN_BUILD_BASENAMES = frozenset(("kbuild", "kconfig", "makefile"))
EXPECTED_SYMBOLS = (
    "MCKERNEL_IHK_RUST",
    "MCKERNEL_IHK_SMP_X86_64_RUST",
    "MCKERNEL_MCCTRL_RUST",
)
EXPECTED_KBUILD_LINES = (
    "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o",
    "obj-$(CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST) += ihk-smp-x86_64.o",
    "ihk-smp-x86_64-y := ihk_smp_x86_64.o",
    "obj-$(CONFIG_MCKERNEL_MCCTRL_RUST) += mcctrl.o",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class AuditError(Exception):
    pass


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_reject_duplicates)
    except AuditError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise AuditError("cannot read manifest: {0}".format(error))
    if not isinstance(value, dict):
        raise AuditError("manifest must contain one JSON object")
    return value


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_file(repo, relative, label):
    if not isinstance(relative, str) or not relative or relative.startswith("/"):
        raise AuditError("{0} is not a normalized repository path".format(label))
    if any(part in ("", ".", "..") for part in relative.split("/")):
        raise AuditError("{0} is not a normalized repository path".format(label))
    root = os.path.realpath(repo)
    requested = os.path.join(root, *relative.split("/"))
    resolved = os.path.realpath(requested)
    try:
        common = os.path.commonpath((root, resolved))
    except ValueError:
        common = ""
    if common != root or requested != resolved:
        raise AuditError("{0} escapes or traverses a symlink".format(label))
    try:
        info = os.lstat(requested)
    except OSError as error:
        raise AuditError("{0} is missing: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise AuditError("{0} must be a regular non-symlink file".format(label))
    return requested


def _read_text(path, label):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return stream.read()
    except (OSError, UnicodeError) as error:
        raise AuditError("cannot read {0}: {1}".format(label, error))


def _rust_tokens(source, label):
    """Lex enough Rust to inspect external modules and literal file includes.

    Comments and quoted text cannot introduce declarations. Unsupported syntax at
    the dependency sites fails closed instead of silently shortening the graph.
    """
    tokens = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("//", index):
            end = source.find("\n", index + 2)
            index = len(source) if end < 0 else end + 1
            continue
        if source.startswith("/*", index):
            depth = 1
            index += 2
            while depth:
                if index >= len(source):
                    raise AuditError("unterminated Rust comment in {0}".format(label))
                if source.startswith("/*", index):
                    depth += 1
                    index += 2
                elif source.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            continue
        raw = re.match(r'(?:br|r)(#+)?"', source[index:])
        if raw:
            hashes = raw.group(1) or ""
            start = index + len(raw.group(0))
            terminator = '"' + hashes
            end = source.find(terminator, start)
            if end < 0:
                raise AuditError("unterminated raw Rust string in {0}".format(label))
            tokens.append(("raw_string", source[start:end]))
            index = end + len(terminator)
            continue
        if char == '"' or (char == "b" and source[index:index + 2] == 'b"'):
            start = index + (2 if char == "b" else 1)
            end = start
            while end < len(source):
                if source[end] == "\\":
                    end += 2
                elif source[end] == '"':
                    break
                else:
                    end += 1
            if end >= len(source):
                raise AuditError("unterminated Rust string in {0}".format(label))
            tokens.append(("string", source[start:end]))
            index = end + 1
            continue
        if char == "'":
            # A lifetime is an apostrophe plus identifier; a character literal
            # has its own closing quote and cannot contain dependency syntax.
            match = re.match(r"'(?:\\.|[^'\\])'", source[index:])
            if match:
                index += len(match.group(0))
                continue
        match = re.match(r"[A-Za-z_][A-Za-z_0-9]*", source[index:])
        if match:
            tokens.append(("ident", match.group(0)))
            index += len(match.group(0))
        else:
            tokens.append(("punct", char))
            index += 1
    return tokens


def _literal_relative(value, label):
    if not value or "\\" in value or value.startswith("/"):
        raise AuditError("nonliteral or escaped dependency path in {0}".format(label))
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise AuditError("unnormalized dependency path in {0}".format(label))
    return value


def _punct(tokens, index, value):
    return index < len(tokens) and tokens[index] == ("punct", value)


def _include_dependency(tokens, index, label):
    kind, value = tokens[index]
    if kind != "ident" or value not in ("include", "include_str", "include_bytes"):
        return None
    if not _punct(tokens, index + 1, "!"):
        return None
    if value == "include":
        raise AuditError("source include! requires explicit closure review in {0}".format(label))
    if (not _punct(tokens, index + 2, "(") or index + 3 >= len(tokens)
            or tokens[index + 3][0] != "string" or not _punct(tokens, index + 4, ")")):
        raise AuditError("nonliteral {0}! dependency in {1}".format(value, label))
    return _literal_relative(tokens[index + 3][1], label), index + 5


def _dependencies(source, label):
    tokens = _rust_tokens(source, label)
    modules = []
    includes = []
    pending_path = None
    brace_depth = 0
    inline_scopes = []
    index = 0
    while index < len(tokens):
        kind, value = tokens[index]
        if _punct(tokens, index, "#") and _punct(tokens, index + 1, "["):
            depth = 1
            end = index + 2
            while depth and end < len(tokens):
                if _punct(tokens, end, "["):
                    depth += 1
                elif _punct(tokens, end, "]"):
                    depth -= 1
                end += 1
            if depth:
                raise AuditError("malformed Rust attribute in {0}".format(label))
            body = tokens[index + 2:end - 1]
            # Attribute values can themselves expand file-reading macros (for
            # example #[doc = include_str!("file")]). Inspect them before
            # skipping the attribute as module-declaration metadata.
            body_index = 0
            while body_index < len(body):
                dependency = _include_dependency(body, body_index, label)
                if dependency is None:
                    body_index += 1
                else:
                    included, body_index = dependency
                    includes.append(included)
            if body and body[0] == ("ident", "path"):
                if len(body) != 3 or not _punct(body, 1, "=") or body[2][0] != "string":
                    raise AuditError("malformed path attribute in {0}".format(label))
                if pending_path is not None:
                    raise AuditError("duplicate path attribute in {0}".format(label))
                pending_path = _literal_relative(body[2][1], label)
            elif any(token == ("ident", "path") for token in body):
                raise AuditError("conditional or ambiguous path attribute in {0}".format(label))
            index = end
            continue
        dependency = _include_dependency(tokens, index, label)
        if dependency is not None:
            included, index = dependency
            includes.append(included)
            continue
        if value == "mod" and kind == "ident":
            if index + 2 >= len(tokens) or tokens[index + 1][0] != "ident":
                raise AuditError("malformed module declaration in {0}".format(label))
            if _punct(tokens, index + 2, ";"):
                modules.append((tokens[index + 1][1], pending_path,
                                tuple(scope[1] for scope in inline_scopes)))
                pending_path = None
                index += 3
                continue
            if _punct(tokens, index + 2, "{"):
                if pending_path is not None:
                    raise AuditError("path attribute on inline module in {0}".format(label))
                brace_depth += 1
                inline_scopes.append((brace_depth, tokens[index + 1][1]))
                index += 3
                continue
            raise AuditError("malformed module declaration in {0}".format(label))
        if kind == "punct" and value == "{":
            brace_depth += 1
        elif kind == "punct" and value == "}":
            if inline_scopes and inline_scopes[-1][0] == brace_depth:
                inline_scopes.pop()
            brace_depth -= 1
        index += 1
    if pending_path is not None:
        raise AuditError("unattached path attribute in {0}".format(label))
    return modules, includes


def discover_native_closure(repo):
    """Return exact relative paths reached from all three native crate roots."""
    repo = os.path.realpath(repo)
    seen = set()
    parsed_modules = set()
    pending = [(root, True) for root in CRATE_ROOTS]
    generated = set()
    while pending:
        relative, is_root = pending.pop()
        if relative in parsed_modules:
            continue
        path = _repository_file(repo, NATIVE_ROOT + "/" + relative, "Rust closure " + relative)
        parsed_modules.add(relative)
        seen.add(relative)
        modules, includes = _dependencies(_read_text(path, relative), relative)
        parent = os.path.dirname(relative)
        stem = os.path.splitext(os.path.basename(relative))[0]
        module_base = parent if is_root or stem == "mod" else os.path.join(parent, stem)
        for name, explicit, inline_prefix in modules:
            if explicit is not None:
                explicit_base = (os.path.join(module_base, *inline_prefix)
                                 if inline_prefix else parent)
                target = os.path.normpath(os.path.join(explicit_base, explicit)).replace(os.sep, "/")
            else:
                base = os.path.join(module_base, *inline_prefix, name)
                first = base + ".rs"
                second = os.path.join(base, "mod.rs")
                first_exists = os.path.lexists(os.path.join(repo, NATIVE_ROOT, first))
                second_exists = os.path.lexists(os.path.join(repo, NATIVE_ROOT, second))
                if first_exists == second_exists:
                    raise AuditError("missing or ambiguous module {0} from {1}".format(name, relative))
                target = first if first_exists else second
            if not target.endswith(".rs"):
                raise AuditError("external module is not Rust source: {0}".format(target))
            pending.append((target, False))
        for included in includes:
            target = os.path.normpath(os.path.join(parent, included)).replace(os.sep, "/")
            if target in GENERATED_INPUTS:
                if relative != "ihk_smp_x86_64.rs" or target in generated:
                    raise AuditError("generated compatibility byte include is duplicated or redirected")
                generated.add(target)
                continue
            _repository_file(repo, NATIVE_ROOT + "/" + target, "embedded source " + target)
            seen.add(target)
    if generated != GENERATED_INPUTS:
        raise AuditError("generated compatibility byte dependency differs")
    return frozenset(seen)


def _check_native_root(repo):
    root = os.path.realpath(repo)
    native_root = os.path.join(root, *NATIVE_ROOT.split("/"))
    if os.path.realpath(native_root) != native_root or not os.path.isdir(native_root):
        raise AuditError("native Rust source root is missing or traverses a symlink")
    for directory, subdirectories, files in os.walk(native_root, followlinks=False):
        for name in subdirectories + files:
            if name.lower() in FORBIDDEN_BUILD_BASENAMES:
                relative = os.path.relpath(os.path.join(directory, name), root)
                raise AuditError(
                    "duplicate native Rust build-control surface is forbidden: {0}".format(
                        relative
                    )
                )


def _check_manifest(repo):
    manifest_path = _repository_file(repo, MANIFEST, "stage manifest")
    manifest = _read_json(manifest_path)
    inputs = manifest.get("inputs")
    expected_inputs = dict(AUTHORITATIVE_INPUTS)
    closure = discover_native_closure(repo)
    expected_inputs.update(dict(
        (relative, NATIVE_ROOT + "/" + relative)
        for relative in closure if relative not in CRATE_ROOTS
    ))
    if not isinstance(inputs, list):
        raise AuditError("stage manifest inputs must be a list")
    by_destination = {}
    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            raise AuditError("manifest input {0} must be an object".format(index))
        destination = item.get("destination")
        if not isinstance(destination, str):
            raise AuditError("manifest input {0} destination must be text".format(index))
        if destination in by_destination:
            raise AuditError("duplicate staged destination: {0}".format(destination))
        by_destination[destination] = item
    if set(by_destination) != set(expected_inputs) or len(inputs) != len(expected_inputs):
        raise AuditError("manifest input destinations differ from recursive staging surface: missing={0}, extra={1}".format(
            sorted(set(expected_inputs) - set(by_destination)),
            sorted(set(by_destination) - set(expected_inputs))))

    paths = {}
    for destination in sorted(expected_inputs):
        item = by_destination[destination]
        expected_path = expected_inputs[destination]
        if item.get("repository_path") != expected_path:
            raise AuditError(
                "{0} authority redirected from {1}".format(destination, expected_path)
            )
        expected_kind = {
            "Kbuild": "kbuild_template", "Kconfig": "kconfig",
            "abi/x86_64.rs": "shared_rust_abi", "ihk_ioctl.rs": "rust_ioctl_dispatch",
            "ikc_queue.rs": "rust_module", "ikc_master.rs": "rust_module",
        }.get(destination)
        if expected_kind is None:
            expected_kind = "embedded_assembly_source" if destination.endswith(".S") else "rust_support_module"
        if item.get("kind") != expected_kind:
            raise AuditError("{0} staging kind differs".format(destination))
        expected_digest = item.get("sha256")
        if not isinstance(expected_digest, str) or not HEX64.fullmatch(expected_digest):
            raise AuditError("{0} authority digest is malformed".format(destination))
        path = _repository_file(repo, expected_path, destination + " authority")
        if _sha256(path) != expected_digest:
            raise AuditError("{0} authority digest drift".format(destination))
        paths[destination] = path
    return dict((name, paths[name]) for name in AUTHORITATIVE_INPUTS)


def _check_kconfig(path):
    text = _read_text(path, "Kconfig authority")
    if "MCKERNEL_RUST_" in text:
        raise AuditError("authoritative Kconfig contains retired MCKERNEL_RUST_* aliases")
    try:
        policy = validate_native_rust_kconfig(text)
    except KconfigPolicyError as error:
        raise AuditError("authoritative Kconfig policy violation: {0}".format(error))
    if policy["symbols"] != EXPECTED_SYMBOLS:
        raise AuditError("authoritative Kconfig symbol graph changed or uses a legacy alias")


def _check_kbuild(path):
    text = _read_text(path, "Kbuild authority")
    if "CONFIG_MCKERNEL_RUST_" in text:
        raise AuditError("authoritative Kbuild contains retired CONFIG_MCKERNEL_RUST_* aliases")
    try:
        mappings = validate_native_rust_kbuild(text)
    except KconfigPolicyError as error:
        raise AuditError("authoritative Kbuild policy violation: {0}".format(error))
    if mappings != EXPECTED_KBUILD_LINES:
        raise AuditError("authoritative Kbuild module graph changed or uses a legacy alias")


def audit(repo):
    repo = os.path.realpath(repo)
    _check_native_root(repo)
    paths = _check_manifest(repo)
    _check_kconfig(paths["Kconfig"])
    _check_kbuild(paths["Kbuild"])
    return {
        "authoritative_inputs": tuple(
            AUTHORITATIVE_INPUTS[key] for key in sorted(AUTHORITATIVE_INPUTS)
        ),
        "module_count": len(EXPECTED_SYMBOLS),
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=ROOT)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = audit(args.repo)
    except AuditError as error:
        print("native Rust build-surface audit failed: {0}".format(error), file=sys.stderr)
        return 1
    print(
        "native-rust-build-surface-audit: PASS modules={0} authorities=Kconfig,Kbuild".format(
            result["module_count"]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
