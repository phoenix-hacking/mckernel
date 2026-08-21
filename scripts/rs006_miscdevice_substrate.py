#!/usr/bin/env python3
"""Fail-closed source-substrate checker for the RS-006 Rust miscdevice base.

Two checked upstream backports and one repository-local hardening patch are
active ordered Rocky compatibility inputs. Successful structural and
exact-source replay proves only that narrow source substrate and cannot award
build, runtime, review, RS-006, or tracker credit.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile


CONTRACT_PATH = "host-kernel/contracts/rs006-miscdevice-substrate-v1.json"
EXPECTED_CONTRACT_SHA256 = "8cc1e351ac7bb49e1b55bd8f7a656a02203d897e31d630d4ee4f8479f674f561"
SOURCE_LOCK_PATH = "host-kernel/rocky/source-lock.json"

BASELINE_PATCHES = (
    ("host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
     "85069fa5d4e1de8a0d0172480604c74deba0caeafd34268a6735d069599e5113"),
    ("host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
     "c52bde4ace32fbd908b6c5ed5e4ac1881effd6e9ebd5813e7e083d74a5f34997"),
    ("host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch",
     "4af4b725292a080a9bf69f37308cb4099e957674001f0fc83239f4be29f07ec1"),
    ("host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch",
     "3ef23cf99a4523a6045a29b70f49ba0080242d7b219db7f0bca58b4f7d73fbb7"),
    ("host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch",
     "0ba29993d78fea5db3c0ff8dbf41bf8a6c08b00d9803fc85da7805e698ac8c33"),
    ("host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch",
     "315ec61d17c5d3cc97c6123f30bcffa08befcc00c487efaa5e6eda38333d29c5"),
    ("host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch",
     "d9a58b1123e5f5522efb7ad7b7837c406b955c1a1c4a7a38f0d2faa4dd4285fc"),
    ("host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
     "ab3f6adaed3fcb65669ffc0baccdb3d7a9b7e3df9d0c5889228c775585daacaa"),
    ("host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch",
     "076b0b48effba9bed12cb00a4c93318353aa26344f14b0b1bba5508c55a1bcfb"),
    ("host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch",
     "2781f4eac05a806a58e76a035f2dba45f137a9147512c87cf9f63b1deb40c7e0"),
    ("host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch",
     "2104f602c62bbda355089fb0210647b39d511e77bbdb9857e5c092c004f490a1"),
    ("host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch",
     "3aeb8de2d5eee43f56268475b8911e6e14eef59e3b8007b4719b8c4ef0a1b691"),
    ("host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch",
     "329e86bdadf721f366b58582bf893df451a25e1f5cb91715bb789e10c242f021"),
    ("host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch",
     "e98032b0d88ea5dbaffdbdf39a16423fded48dbed41adec29cc232782ba6d24b"),
    ("host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch",
     "b07d58736bfe7e9ef5f9c3c4ce2807514f2cd01ab1146620fc09eb4f98ac8f29"),
    ("host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch",
     "ea3a2c85b9dc1c15d3307c3958512b812d56297930d58fc6912adfb2ea3e7284"),
    ("host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch",
     "890a11c4540d4c003773482c47858a946156e4cf0d2e04d3a9ed8e1a9382fd4b"),
    ("host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch",
     "e271fa6f30bb3b39a24ae2f926dfa067577997ecf2076e412b5575a4d785021e"),
)

ACTIVE_PATCHES = (
    {
        "path": "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
        "sha256": "bc9b84c4c8bf36b7fac02dd3d04e1a170b86ee143b76739a6eed3e564cdebc2b",
        "bytes": 1935,
        "commit": "a69dc41a4211b0da311ae3a3b79dd4497c9dfb60",
        "provenance": "upstream",
        "subject": "rust: types: add Opaque::try_ffi_init",
        "paths": ("rust/kernel/types.rs",),
    },
    {
        "path": "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
        "sha256": "d377b5bd91d507e383b8673beac42381b9b6c37a47bba7955c768a8f6ddaad25",
        "bytes": 10726,
        "commit": "f893691e742688ae21ad597c5bba13bef54706cd",
        "provenance": "upstream",
        "subject": "rust: miscdevice: add base miscdevice abstraction",
        "paths": (
            "rust/bindings/bindings_helper.h",
            "rust/kernel/lib.rs",
            "rust/kernel/miscdevice.rs",
        ),
    },
    {
        "path": "host-kernel/rocky/patches/0020a-rust-miscdevice-bind-file-operations-to-module.patch",
        "sha256": "3a49240fc0a10d5ec14cd33d0ec7d09775209edd08fba10a6ee786dc59ea5b21",
        "bytes": 3353,
        "provenance": "repository-local",
        "subject": "rust: miscdevice: bind file operations to their module",
        "paths": ("rust/kernel/miscdevice.rs",),
        "local_origin": "McKernel RS-006 miscdevice module-owner compatibility",
        "rocky_base": "linux-6.12.0-211.44.1.el10_2",
        "license": "GPL-2.0",
        "integration_status": "active-ordered-unbuilt",
    },
)

BASE_RELEVANT = (
    ("rust/kernel/types.rs", 19590,
     "3fe4d0cc0910560abefbd668afdb7aad90629b90079ad5e09a6b4346203f9413",
     "9e7ca066355cd590dfe773abcdda464f4e321b75"),
    ("rust/kernel/lib.rs", 4089,
     "730fce907dbd8c48439f63f506d9400ceb707282846f1e325822c77dc99a56f0",
     "b5f4b3ce6b48203507f89bcc4b0bf7b076be6247"),
    ("rust/bindings/bindings_helper.h", 1201,
     "e7590a0468bb99dbf3f32dc5a3d40d2f5f35b4ac50803e9f755825a856ad518c",
     "ae82e9c941afa17c48737d2b2e49ac6d26f670b1"),
    ("include/linux/miscdevice.h", 3289,
     "0a51c5c8f0d9e461f09ad69a248085c17c28d63087b63c99e62d83a206dd6bf9",
     "c0fea6ca507681215b2eda389ab9af0ce4aa52d6"),
    ("include/linux/fs.h", 128701,
     "ce7f9802dfb48399470e77e59dfe26209688da06da2a206a2be6eabdf57a34d6",
     "ab26204359f3101b9ccb50af93f0d008af20b7da"),
)

AFTER_0018 = (
    ("rust/kernel/types.rs", 19590,
     "3fe4d0cc0910560abefbd668afdb7aad90629b90079ad5e09a6b4346203f9413",
     "9e7ca066355cd590dfe773abcdda464f4e321b75"),
    ("rust/kernel/lib.rs", 4122,
     "7e4ab7eda6ffea5c0309dfcbac7ab91c7ea3107d2c706bb7e07d41687fbd9fd9",
     "a0a35b5fda1f818df78640ae212c2d9e4e4838dd"),
    ("rust/bindings/bindings_helper.h", 1201,
     "e7590a0468bb99dbf3f32dc5a3d40d2f5f35b4ac50803e9f755825a856ad518c",
     "ae82e9c941afa17c48737d2b2e49ac6d26f670b1"),
)

AFTER_ACTIVE_PATCHES = (
    ("rust/kernel/types.rs", 20478,
     "3fde339b8a41b521407faa9e45d51ce9ecb183a170e9c650a72d25c73d50f6f7",
     "070d03152937fab82da406591b2f772f7354ca66"),
    ("rust/kernel/lib.rs", 4142,
     "12079556f6e69f48db7fc887227e9243f9fc6837715afb5eaddf57bab8850cdd",
     "8bd848693072fed0a1458134212b266719855753"),
    ("rust/bindings/bindings_helper.h", 1231,
     "f2644392ca91a791e4ab2ffb05a9b30a911a51f1ae025c696c710cfb3a447d07",
     "84303bf221dd95808cf7eeae7909a3fe8fbc492e"),
    ("rust/kernel/miscdevice.rs", 7705,
     "0f2c43a6a64688b6b8387de4813a76289a66f67a1787893d747273c36983b8ee",
     "0e336f63e64c4c996e2894b08f60df30ff793fff"),
)

READINESS_BLOCKERS = (
    "the two upstream backports and repository-local module-owner patch are integrated as ordered source inputs, but source replay alone does not prove an exact configured kernel build",
    "an exact Rocky Linux configured kernel compile with Rust 1.92 has not been captured for this three-patch series",
    "the repository-local module-owner and explicit compat-ioctl change lacks independent source, license, module-owner, compat-ABI, and pinned-lifetime review",
    "the dynamic-minor miscdevice API cannot represent the legacy fixed 64-minor IHK OS-device publication model by itself",
    "the abstraction exposes no read, write, poll, mmap, llseek, or file-flag access needed by broader McKernel device semantics",
    "no McKernel crate uses this substrate and no exact module-load, ioctl, compat-ioctl, teardown, or runtime evidence exists",
)

DIFF_HEADER = re.compile(br"^diff --git a/([^\n]+) b/([^\n]+)$", re.MULTILINE)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ContractError(Exception):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob(data):
    header = "blob {0}\0".format(len(data)).encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _json_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _safe_relative(value, label):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ContractError("{0} is not a normalized relative path".format(label))
    parts = value.split("/")
    if value.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise ContractError("{0} escapes its root".format(label))
    return value


def _safe_file(root, relative, label):
    relative = _safe_relative(relative, label)
    root = os.path.realpath(root)
    path = os.path.join(root, *relative.split("/"))
    resolved = os.path.realpath(path)
    try:
        inside = os.path.commonpath((root, resolved)) == root
    except ValueError:
        inside = False
    if not inside or resolved != path:
        raise ContractError("{0} escapes or traverses a symlink".format(label))
    try:
        info = os.lstat(path)
    except OSError as error:
        raise ContractError("{0} is unavailable: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ContractError("{0} must be a regular non-symlink file".format(label))
    with open(path, "rb") as stream:
        return path, stream.read()


def _safe_kernel_root(path):
    absolute = os.path.abspath(path)
    resolved = os.path.realpath(path)
    try:
        info = os.lstat(path)
    except OSError as error:
        raise ContractError("kernel source is unavailable: {0}".format(error))
    if absolute != resolved or stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ContractError("kernel source must be a real non-symlink directory")
    return resolved


def _read_repo(repo_root, relative, label):
    return _safe_file(repo_root, relative, label)[1]


def _load_contract(data):
    if _sha256(data) != EXPECTED_CONTRACT_SHA256:
        raise ContractError("RS-006 contract digest changed")
    try:
        contract = json.loads(data.decode("utf-8"), object_pairs_hook=_json_without_duplicates)
    except (UnicodeError, ValueError) as error:
        raise ContractError("cannot parse RS-006 contract: {0}".format(error))
    if not isinstance(contract, dict):
        raise ContractError("RS-006 contract must be an object")
    expected_keys = {
        "capability_scope", "claim_scope", "contract_id", "exact_replay",
        "active_series", "integration", "readiness", "schema_version", "target",
    }
    if set(contract) != expected_keys:
        raise ContractError("RS-006 contract top-level keys differ")
    if contract.get("schema_version") != 1:
        raise ContractError("RS-006 contract schema differs")
    if contract.get("contract_id") != "rs-006-rocky-miscdevice-substrate-v1":
        raise ContractError("RS-006 contract id differs")
    target = contract.get("target", {})
    if target.get("gate_id") != "RS-006" or target.get("architecture") != "x86_64":
        raise ContractError("RS-006 target differs")
    readiness = contract.get("readiness", {})
    if readiness.get("status") != "NOT_READY" or readiness.get("credit_eligible") is not False:
        raise ContractError("RS-006 readiness must remain NOT_READY and credit-ineligible")
    if tuple(readiness.get("blockers", ())) != READINESS_BLOCKERS:
        raise ContractError("RS-006 readiness blockers differ")
    integration = contract.get("integration", {})
    for field in (
            "license_authority_integrated", "main_compatibility_series_integrated",
            "source_lock_integrated", "workflow_integrated"):
        if integration.get(field) is not True:
            raise ContractError("RS-006 {0} must remain true".format(field))
    if integration.get("temporary_filenames") is not False:
        raise ContractError("RS-006 filenames must remain active and ordered")
    if integration.get("preserved_predecessor_numbers") != [
            "0013", "0014", "0015", "0016", "0017", "0018"]:
        raise ContractError("RS-006 predecessor-number vector differs")
    if integration.get("active_patch_numbers") != ["0019", "0020", "0020a"]:
        raise ContractError("RS-006 active-number vector differs")
    series = contract.get("active_series", ())
    if len(series) != len(ACTIVE_PATCHES):
        raise ContractError("RS-006 active patch count differs")
    expected_upstream_order = [row["commit"] for row in ACTIVE_PATCHES[:2]]
    actual_upstream_order = [row.get("upstream_commit") for row in series[:2]]
    if actual_upstream_order != expected_upstream_order:
        raise ContractError("RS-006 upstream prerequisite order differs")
    if series[1].get("parent_commit") != expected_upstream_order[0]:
        raise ContractError("miscdevice commit is not bound to its explicit prerequisite")
    for actual, expected in zip(series, ACTIVE_PATCHES):
        if (
            actual.get("patch_path") != expected["path"]
            or actual.get("patch_sha256") != expected["sha256"]
            or actual.get("patch_bytes") != expected["bytes"]
        ):
            raise ContractError("RS-006 active patch identity differs")
        if expected["provenance"] == "repository-local":
            for field in ("integration_status", "license", "local_origin", "rocky_base"):
                if actual.get(field) != expected[field]:
                    raise ContractError("RS-006 local active patch provenance differs")
    replay = contract.get("exact_replay", {})
    if replay.get("baseline_compatibility_patch_count") != len(BASELINE_PATCHES):
        raise ContractError("RS-006 baseline compatibility count differs")
    if replay.get("baseline_terminal_patch") != BASELINE_PATCHES[-1][0]:
        raise ContractError("RS-006 baseline terminal patch differs")
    if "preimages_after_0018" not in replay or "preimages_after_0012" in replay:
        raise ContractError("RS-006 ordered preimage boundary differs")
    return contract


def _validate_patch(data, expected):
    if len(data) != expected["bytes"] or _sha256(data) != expected["sha256"]:
        raise ContractError("active patch identity changed: {0}".format(expected["path"]))
    if b"\r" in data or b"\0" in data:
        raise ContractError("active patch must be LF-only non-binary text")
    if expected["provenance"] == "upstream":
        first = data.split(b"\n", 1)[0].decode("ascii", "strict")
        if first != "From {0} Mon Sep 17 00:00:00 2001".format(expected["commit"]):
            raise ContractError("active patch commit provenance changed")
    else:
        required_headers = (
            "From: McKernel local compatibility integration",
            "Status: active ordered Rocky compatibility patch; unbuilt and noncrediting",
            "License: " + expected["license"],
        )
        text = data.decode("utf-8", "strict")
        if any(text.count(header) != 1 for header in required_headers):
            raise ContractError("local active patch provenance changed")
        if "Upstream-Commit:" in text or "Stable-Commit:" in text:
            raise ContractError("local active patch invents upstream provenance")
    subject = b"Subject: [PATCH] " + expected["subject"].encode("utf-8") + b"\n"
    if subject not in data:
        raise ContractError("active patch subject changed")
    paths = []
    for left, right in DIFF_HEADER.findall(data):
        if left != right:
            raise ContractError("active patch renames are forbidden")
        paths.append(left.decode("utf-8"))
    if tuple(paths) != expected["paths"]:
        raise ContractError("active patch path vector changed")
    if b"GIT binary patch" in data:
        raise ContractError("active patch must be textual")


def _validate_file_vector(root, rows, label):
    for relative, expected_bytes, expected_sha, expected_blob in rows:
        data = _safe_file(root, relative, label + ":" + relative)[1]
        if len(data) != expected_bytes or _sha256(data) != expected_sha:
            raise ContractError("{0} byte identity changed: {1}".format(label, relative))
        if _git_blob(data) != expected_blob:
            raise ContractError("{0} Git blob identity changed: {1}".format(label, relative))


def _validate_binding_headers(source):
    misc = _safe_file(source, "include/linux/miscdevice.h", "miscdevice C API")[1]
    fs = _safe_file(source, "include/linux/fs.h", "file-operations C API")[1]
    requirements = (
        (misc, br"^#define MISC_DYNAMIC_MINOR\s+255$", "dynamic misc minor"),
        (misc, br"struct miscdevice\s*\{.*?const struct file_operations \*fops;.*?\};",
         "miscdevice file-operations field"),
        (misc, br"extern int misc_register\(struct miscdevice \*misc\);",
         "miscdevice registration"),
        (misc, br"extern void misc_deregister\(struct miscdevice \*misc\);",
         "miscdevice deregistration"),
        (fs, br"#ifdef CONFIG_COMPAT\s+extern long compat_ptr_ioctl\(",
         "compat ioctl fallback"),
        (fs, br"struct file_operations\s*\{.*?long \(\*unlocked_ioctl\).*?"
             br"long \(\*compat_ioctl\).*?int \(\*open\).*?int \(\*release\)",
         "open/release/ioctl file operations"),
        (fs, br"extern int generic_file_open\(struct inode \* inode, struct file \* filp\);",
         "generic file open"),
    )
    for data, pattern, label in requirements:
        if not re.search(pattern, data, re.MULTILINE | re.DOTALL):
            raise ContractError("exact Rocky binding header lacks {0}".format(label))


def _patch_paths(data):
    paths = []
    for left, right in DIFF_HEADER.findall(data):
        if left != right:
            raise ContractError("baseline patch rename is unsupported")
        relative = left.decode("utf-8")
        _safe_relative(relative, "patch target")
        if relative not in paths:
            paths.append(relative)
    if not paths:
        raise ContractError("patch has no textual targets")
    return paths


def _run_patch(root, patch_path):
    command = [
        "patch", "-p1", "--batch", "--forward", "--fuzz=0",
        "--no-backup-if-mismatch", "-i", patch_path,
    ]
    process = subprocess.Popen(
        command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = process.communicate()[0]
    return process.returncode, output.decode("utf-8", "replace")


def replay_exact_source(repo_root, kernel_source, patch_data):
    source = _safe_kernel_root(kernel_source)
    _validate_file_vector(source, BASE_RELEVANT, "exact Rocky base preimage")
    _validate_binding_headers(source)
    if os.path.lexists(os.path.join(source, "rust/kernel/miscdevice.rs")):
        raise ContractError("exact Rocky base unexpectedly contains rust/kernel/miscdevice.rs")

    baseline_data = []
    all_paths = []
    for relative, digest in BASELINE_PATCHES:
        data = _read_repo(repo_root, relative, "baseline compatibility patch")
        if _sha256(data) != digest:
            raise ContractError("baseline compatibility patch changed: {0}".format(relative))
        baseline_data.append((relative, data))
        for path in _patch_paths(data):
            if path not in all_paths:
                all_paths.append(path)
    for data in patch_data:
        for path in _patch_paths(data):
            if path not in all_paths and path != "rust/kernel/miscdevice.rs":
                all_paths.append(path)

    with tempfile.TemporaryDirectory(prefix="rs006-miscdevice-replay-") as temporary:
        tree = os.path.join(temporary, "linux")
        os.mkdir(tree)
        for relative in all_paths:
            source_path = _safe_file(source, relative, "exact Rocky replay input")[0]
            destination = os.path.join(tree, *relative.split("/"))
            parent = os.path.dirname(destination)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            shutil.copyfile(source_path, destination)

        patch_files = []
        for index, (relative, data) in enumerate(baseline_data):
            destination = os.path.join(temporary, "baseline-{0:02d}.patch".format(index + 1))
            with open(destination, "wb") as stream:
                stream.write(data)
            patch_files.append((relative, destination))
        for index, data in enumerate(patch_data):
            destination = os.path.join(temporary, "active-{0:02d}.patch".format(index + 1))
            with open(destination, "wb") as stream:
                stream.write(data)
            patch_files.append((ACTIVE_PATCHES[index]["path"], destination))

        for relative, patch_path in patch_files[:len(BASELINE_PATCHES)]:
            status, output = _run_patch(tree, patch_path)
            if status:
                raise ContractError("strict baseline replay failed for {0}: {1}".format(
                    relative, output.strip()))
        _validate_file_vector(tree, AFTER_0018, "post-0018 preimage")
        if os.path.lexists(os.path.join(tree, "rust/kernel/miscdevice.rs")):
            raise ContractError("post-0018 miscdevice preimage must be absent")

        active_files = patch_files[len(BASELINE_PATCHES):]
        for relative, patch_path in active_files:
            status, output = _run_patch(tree, patch_path)
            if status:
                raise ContractError("strict active-patch replay failed for {0}: {1}".format(
                    relative, output.strip()))
        _validate_file_vector(tree, AFTER_ACTIVE_PATCHES, "active-patch postimage")

        for relative, patch_path in active_files:
            status, _output = _run_patch(tree, patch_path)
            if status == 0:
                raise ContractError("active patch accepted a second application: {0}".format(relative))
    return {
        "baseline_patch_count": len(BASELINE_PATCHES),
        "active_patch_count": len(ACTIVE_PATCHES),
        "postimage_count": len(AFTER_ACTIVE_PATCHES),
        "strict_fuzz": 0,
    }


def _validate_authority_bindings(repo_root):
    path_authorities = (
        SOURCE_LOCK_PATH,
        "scripts/rocky_kernel_source_lock.py",
        "scripts/rocky_kernel_license_inventory.py",
        "scripts/linux_api_exact_probe.py",
        "scripts/rocky_kernel_config_resolution.py",
        "scripts/rocky_kernel_config_resolution_v2.py",
        "host-kernel/rocky/evidence/config-resolution-contract-v1.json",
        "host-kernel/rocky/evidence/config-resolution-contract-v2.json",
        "scripts/rocky_kernel_rk006_patch_authority.py",
        "host-kernel/rocky/rk006-patch-authority-v1.json",
        "scripts/tests/test_rust_target_compatibility_patches.py",
        ".github/workflows/native-rust-host-modules-exact-build.yml",
        ".github/workflows/rs001-linux-api-exact-probe.yml",
    )
    for relative in path_authorities:
        data = _read_repo(repo_root, relative, "integration authority")
        for patch in ACTIVE_PATCHES:
            needle = patch["path"].encode("utf-8")
            if needle not in data and os.path.basename(needle) not in data:
                raise ContractError(
                    "active patch is absent from authority {0}".format(relative))
    provenance_data = _read_repo(
        repo_root, "scripts/linux_api_exact_probe.py", "exact-probe authority")
    for patch in ACTIVE_PATCHES:
        if patch["provenance"] == "upstream" and patch["commit"].encode("ascii") not in provenance_data:
            raise ContractError("active patch provenance is absent from exact-probe authority")
        if patch["provenance"] == "repository-local" and (
                patch["local_origin"].encode("utf-8") not in provenance_data
                or patch["integration_status"].encode("ascii") not in provenance_data):
            raise ContractError("local active patch provenance is absent from exact-probe authority")


def check(repo_root, kernel_source=None, contract_override=None, patch_overrides=None):
    repo_root = os.path.realpath(repo_root)
    contract_data = contract_override
    if contract_data is None:
        contract_data = _read_repo(repo_root, CONTRACT_PATH, "RS-006 contract")
    contract = _load_contract(contract_data)
    patch_overrides = patch_overrides or {}
    patch_data = []
    for expected in ACTIVE_PATCHES:
        data = patch_overrides.get(expected["path"])
        if data is None:
            data = _read_repo(repo_root, expected["path"], "active patch")
        _validate_patch(data, expected)
        patch_data.append(data)
    _validate_authority_bindings(repo_root)
    replay = None
    if kernel_source:
        replay = replay_exact_source(repo_root, kernel_source, patch_data)
    return contract, replay


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--kernel-source")
    parser.add_argument("--require-source-replay", action="store_true")
    args = parser.parse_args(argv)
    if args.require_source_replay and not args.kernel_source:
        parser.error("--require-source-replay requires --kernel-source")
    try:
        contract, replay = check(args.repo, args.kernel_source)
    except ContractError as error:
        print("RS-006 miscdevice substrate: INVALID: {0}".format(error), file=sys.stderr)
        return 1
    if args.require_source_replay and replay is None:
        print("RS-006 miscdevice substrate: INVALID: source replay absent", file=sys.stderr)
        return 1
    replay_status = "passed" if replay is not None else "not-run"
    print("RS-006 miscdevice substrate: {0} (credit={1}; source_replay={2})".format(
        contract["readiness"]["status"],
        str(contract["readiness"]["credit_eligible"]).lower(),
        replay_status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
