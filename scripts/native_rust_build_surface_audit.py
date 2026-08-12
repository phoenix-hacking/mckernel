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


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = "host-kernel/kbuild/stage-manifest.json"
NATIVE_ROOT = "host-kernel/native-rust"
AUTHORITATIVE_INPUTS = {
    "Kbuild": "host-kernel/kbuild/Kbuild.in",
    "Kconfig": "host-kernel/kbuild/Kconfig",
}
SUPPLEMENTAL_INPUTS = {
    "abi/x86_64.rs": "host-kernel/native-rust/abi/x86_64.rs",
    "ikc_queue.rs": "host-kernel/native-rust/ikc_queue.rs",
}
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
    expected_inputs.update(SUPPLEMENTAL_INPUTS)
    if not isinstance(inputs, list) or len(inputs) != len(expected_inputs):
        raise AuditError(
            "stage manifest must name exactly the build authorities and locked supplemental inputs"
        )
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
    if set(by_destination) != set(expected_inputs):
        raise AuditError("manifest input destinations differ from the locked staging surface")

    paths = {}
    for destination in sorted(expected_inputs):
        item = by_destination[destination]
        expected_path = expected_inputs[destination]
        if item.get("repository_path") != expected_path:
            raise AuditError(
                "{0} authority redirected from {1}".format(destination, expected_path)
            )
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
    symbols = tuple(re.findall(r"^config ([A-Z0-9_]+)$", text, re.MULTILINE))
    if symbols != EXPECTED_SYMBOLS:
        raise AuditError("authoritative Kconfig symbol graph changed or uses a legacy alias")
    if "MCKERNEL_RUST_" in text:
        raise AuditError("authoritative Kconfig contains retired MCKERNEL_RUST_* aliases")


def _check_kbuild(path):
    text = _read_text(path, "Kbuild authority")
    substantive = tuple(
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if substantive != EXPECTED_KBUILD_LINES:
        raise AuditError("authoritative Kbuild module graph changed or uses a legacy alias")
    if "CONFIG_MCKERNEL_RUST_" in text:
        raise AuditError("authoritative Kbuild contains retired CONFIG_MCKERNEL_RUST_* aliases")


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
