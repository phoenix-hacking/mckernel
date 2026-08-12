#!/usr/bin/env python3
"""Validate and stage the native Rust-for-Linux host-module build inputs."""

from __future__ import print_function

import argparse
import ctypes
import difflib
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import tempfile


SCHEMA_VERSION = 2
PARENT_SCHEMA_VERSION = 1
PRODUCTION_STAGE_ENABLED = False
EVIDENCE_STAGE_PURPOSE = "compiler-evidence-only"
PROFILE_ID = "rocky-10.2-native-rust-host-modules-v1"
DEFAULT_MANIFEST = "host-kernel/kbuild/stage-manifest.json"
EXPECTED_DESTINATION = {
    "kernel_relative_root": "drivers/misc/mckernel",
    "parent_kbuild_integration": "drivers/misc/Makefile",
    "parent_kconfig_integration": "drivers/misc/Kconfig",
}
EXPECTED_BUILD_CONTRACT = {
    "allowed_project_source_suffixes": [".rs"],
    "build_system": "Linux in-tree Kbuild with Rust-for-Linux",
    "compiler_invocation_owner": "Linux Kbuild",
    "forbidden_project_input_suffixes": [".a", ".c", ".cc", ".cpp", ".o", ".so"],
    "manual_rustc_invocation_forbidden": True,
    "prebuilt_project_objects_forbidden": True,
    "project_c_link_objects": 0,
}
EXPECTED_TARGET = {
    "architecture": "x86_64",
    "config_policy_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-config-policy-v1",
    "distribution": "Rocky Linux",
    "kernel_nvr_base": "kernel-6.12.0-211.44.1.el10_2",
    "release": "10.2",
    "resolved_config_sha256": None,
    "resolved_kernel_nvr": None,
    "resolved_toolchain_manifest_sha256": None,
    "source_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    "source_rpm_sha256": "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
    "toolchain_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-toolchain-v1",
}
EXPECTED_INPUTS = (
    {
        "destination": "Kbuild",
        "kind": "kbuild_template",
        "repository_path": "host-kernel/kbuild/Kbuild.in",
        "sha256": "f33c826539ed0807617337ba64a1cb646daf510cc06a44b47243d14e366d67a3",
    },
    {
        "destination": "Kconfig",
        "kind": "kconfig",
        "repository_path": "host-kernel/kbuild/Kconfig",
        "sha256": "69f14cc7d347d6da3d6cbe0199e35fab72e40f6af3683df1c337efd449721296",
    },
    {
        "destination": "abi/x86_64.rs",
        "kind": "shared_rust_abi",
        "repository_path": "host-kernel/native-rust/abi/x86_64.rs",
        "sha256": "b5980e5b621914a120a0e6b72241477c48aee85615ae4cc76077f3874e35f860",
    },
    {
        "destination": "ikc_queue.rs",
        "kind": "rust_module",
        "repository_path": "host-kernel/native-rust/ikc_queue.rs",
        "sha256": "514f9bce452498e5e9394c450532b040c44fce1ac7a6b5158c76f3d4c7270d40",
    },
    {
        "destination": "os_registry.rs",
        "kind": "rust_support_module",
        "repository_path": "host-kernel/native-rust/os_registry.rs",
        "sha256": "29464b8ca1038d87cc0d5f760eb22e0cbd7a1a512ae88f4c550574a784d1e49d",
    },
)
EXPECTED_PARENT_INTEGRATION_REF = {
    "repository_path": "host-kernel/kbuild/parent-integration-v1.json",
    "sha256": "c1028925dd59034da5692c4384c61158236064be80c4e5a551c2d08a290f5caa",
}
EXPECTED_PARENT_SOURCE = {
    "archive_basename": "linux-6.12.0-211.44.1.el10_2.tar.xz",
    "archive_sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
    "archive_root": "linux-6.12.0-211.44.1.el10_2",
    "source_lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    "source_lock_repository_path": "host-kernel/rocky/source-lock.json",
    "source_lock_sha256": "6b8571b229f31bf68b58749217391d917a2ba2028ac876e8475be1ec5bfef222",
    "source_rpm_sha256": "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
}
EXPECTED_PARENT_PATCH = {
    "format": "unified-diff",
    "path_strip": 1,
    "repository_path": "host-kernel/kbuild/patches/0001-drivers-misc-add-mckernel-rust-host-modules.patch",
    "sha256": "25b0724a2523c3fd5d6d8b824b72c6e6b19c2b16edebaa6719b53c22d4d5c7d9",
}
EXPECTED_PARENT_FILES = [
    {
        "insertion": {
            "anchor": "obj-y\t\t\t\t+= keba/",
            "line": "obj-$(CONFIG_MCKERNEL_IHK_RUST)\t+= mckernel/",
            "placement": "after",
        },
        "path": "drivers/misc/Makefile",
        "postimage_sha256": "548e7eed491c9287908870a4783be57c15a360f03ecc68a4c4856e7c5c51a74f",
        "preimage_sha256": "3f998f3c28cae01f8cb6e3b283f25175635ff2510ba40ce60235a3c059a9a238",
    },
    {
        "insertion": {
            "anchor": "endmenu",
            "line": 'source "drivers/misc/mckernel/Kconfig"',
            "placement": "before",
        },
        "path": "drivers/misc/Kconfig",
        "postimage_sha256": "ed57d452061fb74e62d5dce3aa3680aec0b70811b87b57a25554dc4dd4c33e4a",
        "preimage_sha256": "679b6c945aebec04f936c184b724f1b0d6daa6d760ec3bb4d6b56db905c19683",
    },
]
EXPECTED_PARENT_ABSENT_PATHS = [
    "drivers/misc/mckernel",
    "drivers/misc/mckernel/Kbuild",
    "drivers/misc/mckernel/Kconfig",
]
PARENT_VERIFICATION_SCOPE = (
    "byte-exact parent preimages, intended insertions, postimages, and patch bytes only; "
    "no build, runtime, or RK-007 credit"
)
MODULE_BLOCKERS = []
READINESS_BLOCKERS = [
    "selected Rocky kernel source, toolchain, and config evidence is not gate-ready",
    "upstream Rust-for-Linux sample has not built through this staging path",
    "production namespace and import metadata has not been proven from built modules",
    "zero-project-C final link manifests have not been captured",
]
EXPECTED_MODULES = (
    {
        "crate": "ihk",
        "normalized_name": "ihk",
        "output": "ihk.ko",
        "kconfig_symbol": "CONFIG_MCKERNEL_IHK_RUST",
        "dependencies": [],
        "production_namespace": "MCKERNEL_IHK_V1",
        "required_import_namespaces": [],
        "source_destination": "ihk.rs",
        "source_repository_path": "host-kernel/native-rust/ihk.rs",
        "source_sha256": "ff0ab16b609fd333cdc412d3e15ce27fbaf0fb9e880655deb11109bb3b80d22e",
    },
    {
        "crate": "ihk_smp_x86_64",
        "normalized_name": "ihk_smp_x86_64",
        "output": "ihk-smp-x86_64.ko",
        "kconfig_symbol": "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST",
        "dependencies": ["ihk"],
        "production_namespace": None,
        "required_import_namespaces": ["MCKERNEL_IHK_V1"],
        "source_destination": "ihk_smp_x86_64.rs",
        "source_repository_path": "host-kernel/native-rust/ihk_smp_x86_64.rs",
        "source_sha256": "44aae46f0177abf98133ed86041a3682c7f894ec85c5cdd122ec816802e1106d",
    },
    {
        "crate": "mcctrl",
        "normalized_name": "mcctrl",
        "output": "mcctrl.ko",
        "kconfig_symbol": "CONFIG_MCKERNEL_MCCTRL_RUST",
        "dependencies": ["ihk"],
        "production_namespace": None,
        "required_import_namespaces": ["MCKERNEL_IHK_V1"],
        "source_destination": "mcctrl.rs",
        "source_repository_path": "host-kernel/native-rust/mcctrl.rs",
        "source_sha256": "3b996deb4a3eb26f93e45a243d2f7dc075344cee95ff583eeaf20d602ab63e31",
    },
)
EXPECTED_TOP_LEVEL_KEYS = {
    "build_contract",
    "destination",
    "inputs",
    "modules",
    "parent_integration",
    "profile_id",
    "readiness",
    "schema_version",
    "target",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(Exception):
    pass


def _object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def load_json(path):
    try:
        with open(path, "r") as stream:
            return json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (IOError, OSError, ValueError) as error:
        raise ValidationError("cannot load {0}: {1}".format(path, error))


def canonical_json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _require_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValidationError("{0} must be an object".format(label))
    actual = set(value)
    if actual != set(expected):
        raise ValidationError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(set(expected) - actual), sorted(actual - set(expected))
            )
        )


def _require_string_list(value, label, allow_empty=True):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValidationError("{0} must be a {1}list".format(label, "non-empty " if not allow_empty else ""))
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationError("{0} entries must be non-empty strings".format(label))
    if len(value) != len(set(value)):
        raise ValidationError("{0} contains duplicates".format(label))


def _safe_relative_path(value, label):
    if not isinstance(value, str) or not value:
        raise ValidationError("{0} must be a non-empty relative path".format(label))
    if "\\" in value or value.startswith("/") or value != os.path.normpath(value):
        raise ValidationError("{0} is not a normalized POSIX-style relative path".format(label))
    if value == "." or value.startswith("../") or "/../" in value or value.endswith("/.."):
        raise ValidationError("{0} escapes its root".format(label))
    return value


def _repo_regular_file(repo_root, relative, label):
    relative = _safe_relative_path(relative, label)
    repo_real = os.path.realpath(repo_root)
    candidate = os.path.join(repo_real, relative)
    candidate_real = os.path.realpath(candidate)
    try:
        inside = os.path.commonpath([repo_real, candidate_real]) == repo_real
    except ValueError:
        inside = False
    if not inside:
        raise ValidationError("{0} resolves outside the repository".format(label))
    try:
        info = os.lstat(candidate)
    except OSError as error:
        raise ValidationError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValidationError("{0} must be a regular, non-symlink file".format(label))
    if candidate_real != candidate:
        raise ValidationError("{0} traverses a symlink".format(label))
    return candidate


def _validate_digest(path, expected, label):
    if not isinstance(expected, str) or not HEX64.match(expected):
        raise ValidationError("{0}.sha256 must be lowercase SHA-256".format(label))
    actual = sha256_file(path)
    if actual != expected:
        raise ValidationError("{0} digest mismatch: expected {1}, got {2}".format(label, expected, actual))


def _read_text(path, label):
    try:
        with open(path, "r") as stream:
            return stream.read()
    except (IOError, OSError, UnicodeError) as error:
        raise ValidationError("cannot read {0}: {1}".format(label, error))


def _validate_parent_integration(repo_root, reference):
    if reference != EXPECTED_PARENT_INTEGRATION_REF:
        raise ValidationError("parent_integration differs from the hard-locked parent bundle")
    bundle_path = _repo_regular_file(
        repo_root, reference["repository_path"], "parent_integration.repository_path"
    )
    _validate_digest(bundle_path, reference["sha256"], "parent_integration")
    bundle = load_json(bundle_path)
    _require_keys(
        bundle,
        {
            "checkpoint",
            "credit_eligible",
            "parent_files",
            "patch",
            "profile_id",
            "required_absent_paths",
            "schema_version",
            "selected_source",
            "verification_scope",
        },
        "parent integration bundle",
    )
    if bundle["schema_version"] != PARENT_SCHEMA_VERSION or bundle["profile_id"] != PROFILE_ID:
        raise ValidationError("parent integration bundle identity differs")
    if bundle["checkpoint"] != "integrity_only" or bundle["credit_eligible"] is not False:
        raise ValidationError("parent integration bundle may not claim readiness or credit")
    if bundle["selected_source"] != EXPECTED_PARENT_SOURCE:
        raise ValidationError("parent integration selected source differs from the locked Rocky source")
    selected = bundle["selected_source"]
    source_lock_path = _repo_regular_file(
        repo_root, selected["source_lock_repository_path"], "parent integration source lock"
    )
    _validate_digest(source_lock_path, selected["source_lock_sha256"], "parent integration source lock")
    source_lock = load_json(source_lock_path)
    if source_lock.get("lock_id") != selected["source_lock_id"]:
        raise ValidationError("parent integration source-lock ID differs")
    if source_lock.get("source_rpm", {}).get("sha256") != selected["source_rpm_sha256"]:
        raise ValidationError("parent integration source RPM differs from its source lock")
    archive_objects = [
        item
        for item in source_lock.get("embedded_objects", [])
        if item.get("path") == "SOURCES/" + selected["archive_basename"]
    ]
    if len(archive_objects) != 1 or archive_objects[0].get("sha256") != selected["archive_sha256"]:
        raise ValidationError("parent integration source archive differs from its source lock")
    if bundle["patch"] != EXPECTED_PARENT_PATCH:
        raise ValidationError("parent integration patch identity differs")
    if bundle["parent_files"] != EXPECTED_PARENT_FILES:
        raise ValidationError("parent integration preimages, insertions, or postimages differ")
    if bundle["required_absent_paths"] != EXPECTED_PARENT_ABSENT_PATHS:
        raise ValidationError("parent integration destination absence contract differs")
    if bundle["verification_scope"] != PARENT_VERIFICATION_SCOPE:
        raise ValidationError("parent integration verification scope differs")

    patch_path = _repo_regular_file(
        repo_root, bundle["patch"]["repository_path"], "parent integration patch"
    )
    _validate_digest(patch_path, bundle["patch"]["sha256"], "parent integration patch")
    try:
        with open(patch_path, "rb") as stream:
            patch_bytes = stream.read()
    except (IOError, OSError) as error:
        raise ValidationError("cannot read parent integration patch: {0}".format(error))
    if not patch_bytes.endswith(b"\n") or b"\r" in patch_bytes or b"\0" in patch_bytes:
        raise ValidationError("parent integration patch must be LF-only text ending in a newline")
    return {
        "bundle": bundle,
        "bundle_path": bundle_path,
        "bundle_sha256": reference["sha256"],
        "patch_bytes": patch_bytes,
        "patch_path": patch_path,
    }


def _apply_parent_insertion(preimage, item):
    label = item["path"]
    if sha256_bytes(preimage) != item["preimage_sha256"]:
        raise ValidationError("parent preimage digest mismatch: {0}".format(label))
    if b"\r" in preimage or not preimage.endswith(b"\n"):
        raise ValidationError("parent preimage must be LF-only text ending in a newline: {0}".format(label))
    try:
        text = preimage.decode("utf-8")
    except UnicodeError as error:
        raise ValidationError("parent preimage is not UTF-8 text ({0}): {1}".format(label, error))
    lines = text.splitlines()
    insertion = item["insertion"]
    matches = [index for index, line in enumerate(lines) if line == insertion["anchor"]]
    if len(matches) != 1:
        raise ValidationError(
            "parent insertion anchor must occur exactly once ({0}): got {1}".format(label, len(matches))
        )
    index = matches[0]
    if insertion["placement"] == "after":
        index += 1
    elif insertion["placement"] != "before":
        raise ValidationError("unsupported parent insertion placement: {0}".format(label))
    lines.insert(index, insertion["line"])
    postimage = ("\n".join(lines) + "\n").encode("utf-8")
    if sha256_bytes(postimage) != item["postimage_sha256"]:
        raise ValidationError("parent postimage digest mismatch: {0}".format(label))
    return postimage


def _render_parent_patch(parent_files, preimages, postimages):
    chunks = []
    for item in parent_files:
        path = item["path"]
        chunks.append("diff --git a/{0} b/{0}\n".format(path))
        chunks.extend(
            difflib.unified_diff(
                preimages[path].decode("utf-8").splitlines(True),
                postimages[path].decode("utf-8").splitlines(True),
                fromfile="a/" + path,
                tofile="b/" + path,
                n=3,
            )
        )
    return "".join(chunks).encode("utf-8")


def verify_parent_source_archive(plan, archive_path):
    parent = plan["parent_integration"]
    bundle = parent["bundle"]
    selected = bundle["selected_source"]
    archive_path = os.path.abspath(archive_path)
    try:
        info = os.lstat(archive_path)
    except OSError as error:
        raise ValidationError("selected source archive is unavailable: {0}".format(error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValidationError("selected source archive must be a regular, non-symlink file")
    if os.path.basename(archive_path) != selected["archive_basename"]:
        raise ValidationError("selected source archive basename differs")
    _validate_digest(archive_path, selected["archive_sha256"], "selected source archive")

    try:
        with tarfile.open(archive_path, mode="r:xz") as archive:
            members = archive.getmembers()
            normalized_names = [member.name.rstrip("/") for member in members]
            root = selected["archive_root"]
            for relative in bundle["required_absent_paths"]:
                locked = root + "/" + relative
                if any(name == locked or name.startswith(locked + "/") for name in normalized_names):
                    raise ValidationError("selected source already contains locked destination: {0}".format(relative))

            preimages = {}
            for item in bundle["parent_files"]:
                member_name = root + "/" + item["path"]
                matching = [member for member in members if member.name.rstrip("/") == member_name]
                if len(matching) != 1 or not matching[0].isfile():
                    raise ValidationError(
                        "selected source must contain one regular parent file: {0}".format(item["path"])
                    )
                stream = archive.extractfile(matching[0])
                if stream is None:
                    raise ValidationError("cannot read selected source parent: {0}".format(item["path"]))
                preimages[item["path"]] = stream.read()
    except (IOError, OSError, tarfile.TarError) as error:
        raise ValidationError("cannot inspect selected source archive: {0}".format(error))

    postimages = {}
    for item in bundle["parent_files"]:
        postimages[item["path"]] = _apply_parent_insertion(preimages[item["path"]], item)
    rendered = _render_parent_patch(bundle["parent_files"], preimages, postimages)
    if rendered != parent["patch_bytes"]:
        raise ValidationError("parent integration patch bytes differ from exact intended insertions")
    return {
        "archive_sha256": selected["archive_sha256"],
        "parent_files": [
            {
                "path": item["path"],
                "postimage_sha256": item["postimage_sha256"],
                "preimage_sha256": item["preimage_sha256"],
            }
            for item in bundle["parent_files"]
        ],
        "patch_sha256": bundle["patch"]["sha256"],
    }


def _validate_kbuild(text):
    expected = []
    for module in EXPECTED_MODULES:
        object_name = module["output"][:-3] + ".o"
        expected.append("obj-$({0}) += {1}".format(module["kconfig_symbol"], object_name))
        if "-" in object_name:
            expected.append("{0}-y := {1}.o".format(object_name[:-2], module["crate"]))
    substantive = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if substantive != expected:
        raise ValidationError("Kbuild template must contain only the three native Rust module objects")
    lowered = text.lower()
    for forbidden in ("rustc", "prebuilt_objects", "$(shell", ".a ", ".c ", ".cc ", ".cpp "):
        if forbidden in lowered:
            raise ValidationError("Kbuild template contains forbidden construct: {0}".format(forbidden))


def _validate_kconfig(text):
    symbols = re.findall(r"^config ([A-Z0-9_]+)$", text, re.MULTILINE)
    expected = [module["kconfig_symbol"][len("CONFIG_"):] for module in EXPECTED_MODULES]
    if symbols != expected:
        raise ValidationError("Kconfig must define exactly the three locked native Rust symbols")
    if "\tdepends on RUST\n" not in text or "\tdepends on X86_64\n" not in text:
        raise ValidationError("Kconfig must require Rust and x86_64")
    blocks = {}
    for index, symbol in enumerate(expected):
        tail = text.split("config {0}\n".format(symbol), 1)[1]
        blocks[symbol] = tail.split("\nconfig ", 1)[0] if index + 1 < len(expected) else tail.split("\nendmenu", 1)[0]
    for symbol, block in blocks.items():
        if not re.search(r'^\ttristate "[^"\n]+"$', block, re.MULTILINE):
            raise ValidationError("{0} must be a tristate".format(symbol))
        dependencies = re.findall(r"^\tdepends on (.+)$", block, re.MULTILINE)
        expected_dependencies = [] if symbol == expected[0] else ["MCKERNEL_IHK_RUST"]
        if dependencies != expected_dependencies:
            raise ValidationError("{0} dependency set differs from the locked graph".format(symbol))
        if re.search(r"^\s*(default|def_bool|def_tristate|select|imply|visible if|range|option)\b", block, re.MULTILINE):
            raise ValidationError("{0} contains a forbidden implicit configuration rule".format(symbol))
    if re.search(r"^\s*(source|rsource|osource|orsource|select|imply)\b", text, re.MULTILINE):
        raise ValidationError("Kconfig staging fragment may not include hidden source/select/imply edges")


def _validate_input(repo_root, item, index):
    label = "inputs[{0}]".format(index)
    _require_keys(item, {"destination", "kind", "repository_path", "sha256"}, label)
    if index >= len(EXPECTED_INPUTS) or item != EXPECTED_INPUTS[index]:
        raise ValidationError("{0} differs from the hard-locked staging input".format(label))
    expected_destination = {
        "kbuild_template": "Kbuild",
        "kconfig": "Kconfig",
        "shared_rust_abi": "abi/x86_64.rs",
        "rust_module": "ikc_queue.rs",
        "rust_support_module": "os_registry.rs",
    }.get(item["kind"])
    if expected_destination is None:
        raise ValidationError("{0}.kind is not a locked staging input kind".format(label))
    if item["destination"] != expected_destination:
        raise ValidationError("{0}.destination must be {1}".format(label, expected_destination))
    path = _repo_regular_file(repo_root, item["repository_path"], label + ".repository_path")
    _validate_digest(path, item["sha256"], label)
    text = _read_text(path, label)
    if item["kind"] == "kbuild_template":
        _validate_kbuild(text)
    elif item["kind"] == "kconfig":
        _validate_kconfig(text)
    elif item["kind"] == "shared_rust_abi":
        required = (
            "pub struct IhkIkcQueueHead",
            "assert_layout!(IhkIkcQueueHead, 64, 8,",
            '#[cfg(not(target_endian = "little"))]',
            '#[cfg(not(target_pointer_width = "64"))]',
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique ABI marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ('extern "c"', "unsafe", "include!", "include_bytes!", "asm!(", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    elif item["kind"] == "rust_module":
        required = (
            "use super::abi::IhkIkcQueueHead;",
            "pub(crate) struct SharedQueue",
            "pub(crate) fn try_enqueue",
            "pub(crate) fn try_dequeue",
            "pub(crate) unsafe fn attach",
        )
        for token in required:
            if text.count(token) != 1:
                raise ValidationError("{0} lacks a unique queue marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ('extern "c"', "include!", "include_bytes!", "asm!(", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    else:
        required = (
            "pub(crate) const OS_CAPACITY: usize = 64;",
            "const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;",
            "impl Drop for ReservationGuard<'_>",
            "impl Drop for DestroyGuard<'_>",
            "RegistryError::StaleHandle",
        )
        for token in required:
            if text.count(token) < 1:
                raise ValidationError("{0} lacks registry marker: {1}".format(label, token))
        lowered = text.lower()
        for forbidden in ('extern "c"', "unsafe", "include!", "include_bytes!", "asm!(", "module!"):
            if forbidden in lowered:
                raise ValidationError("{0} contains forbidden executable/boundary construct: {1}".format(label, forbidden))
    return {
        "destination": item["destination"],
        "path": path,
        "sha256": item["sha256"],
    }


def _validate_module(repo_root, module, expected, index):
    label = "modules[{0}]".format(index)
    _require_keys(
        module,
        {
            "blockers",
            "crate",
            "dependencies",
            "kconfig_symbol",
            "normalized_name",
            "output",
            "production_namespace",
            "required_import_namespaces",
            "source",
        },
        label,
    )
    for field in (
        "crate",
        "dependencies",
        "kconfig_symbol",
        "normalized_name",
        "output",
        "production_namespace",
        "required_import_namespaces",
    ):
        if module[field] != expected[field]:
            raise ValidationError("{0}.{1} differs from the locked module contract".format(label, field))
    if module["blockers"] != MODULE_BLOCKERS:
        raise ValidationError("{0}.blockers differs from the locked crate-root checkpoint".format(label))
    _require_keys(module["source"], {"destination", "repository_path", "sha256"}, label + ".source")
    source = module["source"]
    if source["destination"] != expected["source_destination"]:
        raise ValidationError("{0}.source.destination differs from the locked crate root".format(label))
    if source["repository_path"] != expected["source_repository_path"]:
        raise ValidationError("{0}.source.repository_path differs from the locked crate root".format(label))
    if source["sha256"] != expected["source_sha256"]:
        raise ValidationError("{0}.source.sha256 differs from the locked crate root".format(label))
    path = _repo_regular_file(repo_root, source["repository_path"], label + ".source.repository_path")
    if not path.endswith(".rs"):
        raise ValidationError("{0}.source must be a Rust source file".format(label))
    _validate_digest(path, source["sha256"], label + ".source")
    text = _read_text(path, label + ".source")
    if "module!" not in text or "impl kernel::Module" not in text:
        raise ValidationError("{0}.source lacks a native Rust-for-Linux module entry point".format(label))
    if module["crate"] == "ihk":
        for fragment in ('#[path = "abi/x86_64.rs"]\nmod abi;', "mod ikc_queue;"):
            if text.count(fragment) != 1:
                raise ValidationError(
                    "{0}.source does not bind the staged IHK queue graph: {1}".format(
                        label, fragment
                    )
                )
    lowered = text.lower()
    for forbidden in ("extern \"c\"", "include_bytes!", "global_asm!", "asm!("):
        if forbidden in lowered:
            raise ValidationError("{0}.source contains unreviewed boundary construct: {1}".format(label, forbidden))
    return {
        "destination": source["destination"],
        "path": path,
        "sha256": source["sha256"],
    }, list(module["blockers"])


def validate_manifest(repo_root, manifest_path):
    repo_root = os.path.realpath(repo_root)
    manifest_path = os.path.abspath(manifest_path)
    try:
        original_info = os.lstat(manifest_path)
    except OSError as error:
        raise ValidationError("manifest is unavailable: {0}".format(error))
    if stat.S_ISLNK(original_info.st_mode) or not stat.S_ISREG(original_info.st_mode):
        raise ValidationError("manifest must be a regular, non-symlink file")
    manifest_real = os.path.realpath(manifest_path)
    try:
        inside = os.path.commonpath([repo_root, manifest_real]) == repo_root
    except ValueError:
        inside = False
    if not inside:
        raise ValidationError("manifest resolves outside the repository")
    if manifest_real != manifest_path:
        raise ValidationError("manifest traverses a symlink")
    manifest = load_json(manifest_path)
    _require_keys(manifest, EXPECTED_TOP_LEVEL_KEYS, "manifest")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported schema_version")
    if manifest["profile_id"] != PROFILE_ID:
        raise ValidationError("profile_id differs from the selected Rocky profile")
    if manifest["build_contract"] != EXPECTED_BUILD_CONTRACT:
        raise ValidationError("build_contract does not enforce the locked native Rust-only path")
    if manifest["destination"] != EXPECTED_DESTINATION:
        raise ValidationError("destination does not match the locked in-tree staging path")
    if manifest["target"] != EXPECTED_TARGET:
        raise ValidationError("target differs from the locked Rocky identity or overclaims resolved evidence")
    parent_integration = _validate_parent_integration(repo_root, manifest["parent_integration"])

    inputs = manifest["inputs"]
    if not isinstance(inputs, list) or len(inputs) != len(EXPECTED_INPUTS):
        raise ValidationError(
            "inputs must contain exactly Kbuild, Kconfig, the shared x86_64 ABI, "
            "the IHK queue module, and the OS registry"
        )
    staged_files = [_validate_input(repo_root, item, index) for index, item in enumerate(inputs)]
    destinations = [item["destination"] for item in staged_files]
    if destinations != [
        "Kbuild", "Kconfig", "abi/x86_64.rs", "ikc_queue.rs", "os_registry.rs"
    ]:
        raise ValidationError(
            "inputs must be ordered as Kbuild, Kconfig, abi/x86_64.rs, "
            "ikc_queue.rs, os_registry.rs"
        )

    modules = manifest["modules"]
    if not isinstance(modules, list) or len(modules) != len(EXPECTED_MODULES):
        raise ValidationError("modules must contain exactly the three locked modules")
    blockers = []
    for index, expected in enumerate(EXPECTED_MODULES):
        source, module_blockers = _validate_module(repo_root, modules[index], expected, index)
        blockers.extend(module_blockers)
        staged_files.append(source)

    _require_keys(manifest["readiness"], {"blockers", "checkpoint", "credit_eligible"}, "readiness")
    if manifest["readiness"] != {
        "blockers": READINESS_BLOCKERS,
        "checkpoint": "crate_roots_bound",
        "credit_eligible": False,
    }:
        raise ValidationError("readiness must remain the locked crate-roots-bound state")
    blockers.extend(manifest["readiness"]["blockers"])
    if len({item["destination"] for item in staged_files}) != len(staged_files):
        raise ValidationError("staged destinations must be unique")
    if len({item["path"] for item in staged_files}) != len(staged_files):
        raise ValidationError("each staged destination must have a distinct repository input")

    deduplicated = []
    for blocker in blockers:
        if blocker not in deduplicated:
            deduplicated.append(blocker)
    return {
        "blockers": deduplicated,
        "credit_eligible": False,
        "destination": manifest["destination"]["kernel_relative_root"],
        "files": staged_files,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "parent_integration": parent_integration,
        "repo_root": repo_root,
    }


def _stage_lock(plan):
    parent = plan["parent_integration"]
    return {
        "files": [
            {"path": item["destination"], "sha256": item["sha256"]}
            for item in sorted(plan["files"], key=lambda value: value["destination"])
        ],
        "manifest_sha256": plan["manifest_sha256"],
        "parent_integration": {
            "bundle_sha256": parent["bundle_sha256"],
            "parent_files": [
                {
                    "path": item["path"],
                    "postimage_sha256": item["postimage_sha256"],
                    "preimage_sha256": item["preimage_sha256"],
                }
                for item in parent["bundle"]["parent_files"]
            ],
            "patch_sha256": parent["bundle"]["patch"]["sha256"],
        },
        "profile_id": PROFILE_ID,
        "schema_version": SCHEMA_VERSION,
        "target": EXPECTED_TARGET,
    }


def _evidence_stage_lock(plan):
    lock = _stage_lock(plan)
    lock.update(
        {
            "credit_eligible": False,
            "production_readiness_blockers": list(READINESS_BLOCKERS),
            "purpose": EVIDENCE_STAGE_PURPOSE,
        }
    )
    return lock


def _kernel_target(kernel_tree, destination):
    kernel_tree = os.path.abspath(kernel_tree)
    try:
        info = os.lstat(kernel_tree)
    except OSError as error:
        raise ValidationError("kernel tree is unavailable: {0}".format(error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValidationError("kernel tree must be a real directory, not a symlink")
    kernel_real = os.path.realpath(kernel_tree)
    target = os.path.join(kernel_real, _safe_relative_path(destination, "destination"))
    parent = os.path.dirname(target)
    parent_real = os.path.realpath(parent)
    if not os.path.isdir(parent) or parent_real != parent:
        raise ValidationError("staging parent must already exist without symlink traversal")
    if os.path.commonpath([kernel_real, parent_real]) != kernel_real:
        raise ValidationError("staging destination escapes the kernel tree")
    return target, parent


def _rename_directory_noreplace(parent, temporary, target):
    parent = os.path.abspath(parent)
    temporary = os.path.abspath(temporary)
    target = os.path.abspath(target)
    if os.path.dirname(temporary) != parent or os.path.dirname(target) != parent:
        raise ValidationError("no-replace rename requires sibling directories")
    old_name = os.path.basename(temporary)
    new_name = os.path.basename(target)
    if old_name in ("", ".", "..") or new_name in ("", ".", ".."):
        raise ValidationError("no-replace rename received an unsafe directory name")

    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as error:
        raise ValidationError("renameat2 is unavailable; refusing a racy staging rename: {0}".format(error))
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        parent_fd = os.open(parent, flags)
    except OSError as error:
        raise ValidationError("cannot open staging parent for atomic rename: {0}".format(error))
    try:
        ctypes.set_errno(0)
        result = renameat2(
            parent_fd,
            os.fsencode(old_name),
            parent_fd,
            os.fsencode(new_name),
            1,
        )
        if result != 0:
            number = ctypes.get_errno()
            if number in (errno.EEXIST, errno.ENOTEMPTY):
                raise ValidationError("staging destination appeared concurrently: {0}".format(target))
            if number in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
                raise ValidationError("atomic no-replace rename is unsupported; staging remains unchanged")
            raise ValidationError("atomic no-replace rename failed: {0}".format(os.strerror(number)))
    finally:
        os.close(parent_fd)


def _stage_locked(plan, kernel_tree, lock):
    target, parent = _kernel_target(kernel_tree, plan["destination"])
    if os.path.lexists(target):
        raise ValidationError("staging destination already exists: {0}".format(target))
    temporary = tempfile.mkdtemp(prefix=".mckernel-stage-", dir=parent)
    try:
        os.chmod(temporary, 0o755)
        for item in plan["files"]:
            destination = os.path.join(temporary, item["destination"])
            destination_parent = os.path.dirname(destination)
            if destination_parent != temporary and not os.path.isdir(destination_parent):
                os.makedirs(destination_parent, 0o755)
                os.chmod(destination_parent, 0o755)
            with open(item["path"], "rb") as source, open(destination, "wb") as output:
                shutil.copyfileobj(source, output)
            os.chmod(destination, 0o644)
        lock_path = os.path.join(temporary, "stage-lock.json")
        with open(lock_path, "wb") as stream:
            stream.write(canonical_json_bytes(lock))
        os.chmod(lock_path, 0o644)
        expected = {item["destination"]: item["sha256"] for item in plan["files"]}
        expected["stage-lock.json"] = sha256_bytes(canonical_json_bytes(lock))
        for name, digest in expected.items():
            if sha256_file(os.path.join(temporary, name)) != digest:
                raise ValidationError("staged temporary file digest mismatch: {0}".format(name))
        _rename_directory_noreplace(parent, temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)
    _verify_locked_stage(plan, kernel_tree, lock)
    return target


def _verify_locked_stage(plan, kernel_tree, lock):
    target, unused_parent = _kernel_target(kernel_tree, plan["destination"])
    del unused_parent
    try:
        info = os.lstat(target)
    except OSError as error:
        raise ValidationError("staged directory is unavailable: {0}".format(error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValidationError("staged destination must be a real directory")
    if stat.S_IMODE(info.st_mode) != 0o755:
        raise ValidationError("staged destination mode must be 0755")
    expected = {item["destination"]: item["sha256"] for item in plan["files"]}
    expected["stage-lock.json"] = sha256_bytes(canonical_json_bytes(lock))
    actual = []
    actual_directories = []
    for root, directories, files in os.walk(target):
        for directory in directories:
            actual_directories.append(os.path.relpath(os.path.join(root, directory), target))
        for name in files:
            actual.append(os.path.relpath(os.path.join(root, name), target))
    expected_directories = set()
    for name in expected:
        parent = os.path.dirname(name)
        while parent:
            expected_directories.add(parent)
            parent = os.path.dirname(parent)
    if set(actual_directories) != expected_directories:
        raise ValidationError("staged directory closure differs")
    for name in expected_directories:
        path = os.path.join(target, name)
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValidationError("staged directory must be real and non-symlink: {0}".format(name))
        if stat.S_IMODE(info.st_mode) != 0o755:
            raise ValidationError("staged directory mode must be 0755: {0}".format(name))
    if set(actual) != set(expected):
        raise ValidationError(
            "staged file closure differs: missing={0}, extra={1}".format(
                sorted(set(expected) - set(actual)), sorted(set(actual) - set(expected))
            )
        )
    for name, digest in expected.items():
        path = os.path.join(target, name)
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValidationError("staged file must be regular and non-symlink: {0}".format(name))
        if sha256_file(path) != digest:
            raise ValidationError("staged file digest mismatch: {0}".format(name))
    if load_json(os.path.join(target, "stage-lock.json")) != lock:
        raise ValidationError("stage-lock.json content differs from the deterministic lock")
    return target


def stage(plan, kernel_tree):
    if not PRODUCTION_STAGE_ENABLED:
        raise ValidationError(
            "crate-roots-bound schema v{0} cannot stage production modules without build evidence".format(
                SCHEMA_VERSION
            )
        )
    if plan.get("credit_eligible") is not True or plan["blockers"]:
        raise ValidationError("staging is blocked: {0}".format("; ".join(plan["blockers"])))
    return _stage_locked(plan, kernel_tree, _stage_lock(plan))


def verify_stage(plan, kernel_tree):
    if not PRODUCTION_STAGE_ENABLED:
        raise ValidationError(
            "crate-roots-bound schema v{0} has no verifiable production stage".format(
                SCHEMA_VERSION
            )
        )
    if plan.get("credit_eligible") is not True or plan["blockers"]:
        raise ValidationError("stage verification requires a gate-ready manifest")
    return _verify_locked_stage(plan, kernel_tree, _stage_lock(plan))


def _require_evidence_only_plan(plan):
    if plan.get("credit_eligible") is not False:
        raise ValidationError("compiler-evidence staging may never claim gate credit")
    if plan.get("blockers") != READINESS_BLOCKERS:
        raise ValidationError("compiler-evidence staging requires the exact readiness blockers")


def stage_for_evidence(plan, kernel_tree):
    _require_evidence_only_plan(plan)
    return _stage_locked(plan, kernel_tree, _evidence_stage_lock(plan))


def verify_evidence_stage(plan, kernel_tree):
    _require_evidence_only_plan(plan)
    return _verify_locked_stage(plan, kernel_tree, _evidence_stage_lock(plan))


def _print_blockers(plan, stream):
    for blocker in plan["blockers"]:
        print("BLOCKED: {0}".format(blocker), file=stream)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--gate-ready", action="store_true")
    action.add_argument("--verify-parent-source-archive", metavar="SOURCE_TAR_XZ")
    action.add_argument("--stage", metavar="KERNEL_TREE")
    action.add_argument("--verify-stage", metavar="KERNEL_TREE")
    action.add_argument("--stage-for-evidence", metavar="KERNEL_TREE")
    action.add_argument("--verify-evidence-stage", metavar="KERNEL_TREE")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    repo_root = os.path.realpath(args.repo)
    manifest_path = args.manifest
    if not os.path.isabs(manifest_path):
        manifest_path = os.path.join(repo_root, manifest_path)
    try:
        plan = validate_manifest(repo_root, manifest_path)
        if args.check:
            print("Rocky Rust staging manifest integrity: PASS")
            if plan["blockers"]:
                print("Rocky Rust staging gate: NOT READY ({0} blockers)".format(len(plan["blockers"])))
                _print_blockers(plan, sys.stdout)
            return 0
        if args.gate_ready:
            print("Rocky Rust staging gate: NOT READY", file=sys.stderr)
            _print_blockers(plan, sys.stderr)
            return 1
        if args.verify_parent_source_archive:
            result = verify_parent_source_archive(plan, args.verify_parent_source_archive)
            print(
                "Rocky parent integration source verification: PASS ({0}, patch {1})".format(
                    result["archive_sha256"], result["patch_sha256"]
                )
            )
            print(
                "RK-007 credit: NOT ELIGIBLE (crate-roots-bound schema v{0})".format(
                    SCHEMA_VERSION
                )
            )
            return 0
        if args.stage:
            print("Staged native Rust inputs at {0}".format(stage(plan, args.stage)))
            return 0
        if args.verify_stage:
            print("Verified native Rust stage at {0}".format(verify_stage(plan, args.verify_stage)))
            return 0
        if args.stage_for_evidence:
            print(
                "Staged credit-forbidden compiler evidence inputs at {0}".format(
                    stage_for_evidence(plan, args.stage_for_evidence)
                )
            )
            print("RK-007 credit: NOT ELIGIBLE (compiler evidence only)")
            return 0
        print(
            "Verified credit-forbidden compiler evidence stage at {0}".format(
                verify_evidence_stage(plan, args.verify_evidence_stage)
            )
        )
        print("RK-007 credit: NOT ELIGIBLE (compiler evidence only)")
        return 0
    except (OSError, ValidationError) as error:
        print("Rocky Rust staging validation failed: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
