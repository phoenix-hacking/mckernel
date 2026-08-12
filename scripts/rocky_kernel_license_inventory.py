#!/usr/bin/env python3
"""Capture and verify the fail-closed RK-001 source/license inventory.

The capture is intentionally not gate credit.  It inventories the exact locked
SRPM and embedded Linux archive, resolves SPDX identifiers to shipped license
texts where possible, and leaves every missing or ambiguous case unreviewed.
"""

from __future__ import print_function

import argparse
import gzip
import hashlib
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = Path("host-kernel/rocky/source-lock.json")
SERIES = Path("host-kernel/rocky/patches/series.json")
WORKFLOW = Path(".github/workflows/rocky-kernel-source-evidence.yml")
SCHEMA_VERSION = 1
MAX_ARCHIVE_MEMBERS = 250000
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_INVENTORY_BYTES = 1024 * 1024 * 1024
PREFIX_BYTES = 128 * 1024
EXPECTED_CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
EXPECTED_SOURCE_LOCK_SHA256 = (
    "cbca9fe2e92f56ba7dba3dc03b018b11605f5d6c3dfdf9e3e4f33149c442f8ff"
)
EXPECTED_PATCH_SERIES_SHA256 = (
    "6a1a5e8fb13b6ce6ed35bd8e5487bb67ecf92d2be927799b660f21b5631f68fb"
)
EXPECTED_SOURCE_RPM_SHA256 = (
    "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb"
)
EXPECTED_LINUX_ARCHIVE_SHA256 = (
    "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533"
)
EXPECTED_DIST_GIT_COMMIT = "e4cad646580f7f3dfec5e3b6b4ea9e89b7572f6c"
UNEXPANDED_EMBEDDED_OBJECTS = [
    "SOURCES/kernel-abi-stablelists-6.12.0-211.44.1.el10_2.tar.xz",
    "SOURCES/kernel-kabi-dw-6.12.0-211.44.1.el10_2.tar.xz",
]
CAPTURE_BLOCKERS = [
    "every machine-generated item requires independent license/provenance review",
    "generated captures cannot contain reviewed items or close RK-001",
    "two additional embedded source archives remain unexpanded and unreviewed",
    "dist-git and local patch consumption/redistribution scope requires kernel.spec review",
]
EXPECTED_STATIC_NAMESPACE_CLOSURES = {
    "dist-git": {
        "item_count": 77,
        "path_set_sha256": (
            "ffe07b597e0a3b72d5e29e7b05aea8e75bdf112d75068d3d72e28547a4833c22"
        ),
        "source_manifest_sha256": (
            "ac819ee853a73c109c2db5f8735b947c1fae6374fce8b3402779720fe5621e96"
        ),
    },
    "linux": {
        "item_count": 115027,
        "path_set_sha256": (
            "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2"
        ),
        "source_manifest_sha256": (
            "321b8a227f7a9473a94db6fbf747c48727a39b20bd8a24474f68578915ca4e56"
        ),
    },
    "srpm": {
        "item_count": 71,
        "path_set_sha256": (
            "d599d27ba45a688e7f550f793dc467f48e3603fb77efb790331b5b8b42a4ee96"
        ),
        "source_manifest_sha256": (
            "8158ccfb1a5899e47962e45ad107d04e0747fdf0951f167039e7ae3e13d84f47"
        ),
    },
}
EXPECTED_STAGE_REPOSITORY_INPUT_PATHS = sorted([
    "host-kernel/kbuild/Kbuild.in",
    "host-kernel/kbuild/Kconfig",
    "host-kernel/kbuild/parent-integration-v1.json",
    "host-kernel/native-rust/abi/x86_64.rs",
    "host-kernel/native-rust/ihk.rs",
    "host-kernel/native-rust/ihk_ioctl.rs",
    "host-kernel/native-rust/ihk_smp_x86_64.rs",
    "host-kernel/native-rust/ikc_master.rs",
    "host-kernel/native-rust/ikc_queue.rs",
    "host-kernel/native-rust/mcctrl.rs",
    "host-kernel/native-rust/os_registry.rs",
    "host-kernel/native-rust/page_allocator.rs",
    "host-kernel/native-rust/page_owner_registry.rs",
])
EXPECTED_REPOSITORY_INPUT_PATHS = [
    "host-kernel/kbuild/parent-integration-v1.json",
    "host-kernel/kbuild/patches/0001-drivers-misc-add-mckernel-rust-host-modules.patch",
    "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch",
    "host-kernel/kbuild/stage-manifest.json",
    "host-kernel/kbuild/Kbuild.in",
    "host-kernel/kbuild/Kconfig",
    "host-kernel/native-rust/abi/x86_64.rs",
    "host-kernel/native-rust/ihk.rs",
    "host-kernel/native-rust/ihk_ioctl.rs",
    "host-kernel/native-rust/ihk_smp_x86_64.rs",
    "host-kernel/native-rust/ikc_master.rs",
    "host-kernel/native-rust/ikc_queue.rs",
    "host-kernel/native-rust/mcctrl.rs",
    "host-kernel/native-rust/os_registry.rs",
    "host-kernel/native-rust/page_allocator.rs",
    "host-kernel/native-rust/page_owner_registry.rs",
    "host-kernel/rocky/configs/native-rust-evidence.config",
    "host-kernel/rocky/configs/rust-minimal.config",
    "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
    "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
    "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch",
    "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch",
    "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch",
    "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch",
    "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch",
    "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
    "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch",
    "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch",
    "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch",
    "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch",
    "host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch",
    "host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch",
    "host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch",
    "host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch",
    "host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch",
    "host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch",
    "host-kernel/rocky/patches/series.json",
    "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs",
    "scripts/tests/fixtures/ihk_native_master_compile.rs",
    "scripts/tests/fixtures/ihk_native_queue_compile.rs",
    "scripts/tests/fixtures/ihk_ioctl_dispatch_compile.rs",
    "scripts/tests/fixtures/ihk_os_registry_compile.rs",
    "scripts/tests/fixtures/ihk_page_allocator_compile.rs",
    "scripts/tests/fixtures/ihk_page_allocator_lifetime_compile_fail.rs",
    "scripts/tests/fixtures/ihk_page_allocator_must_use_compile_fail.rs",
    "scripts/tests/fixtures/ihk_page_owner_registry_compile.rs",
    "scripts/tests/fixtures/ihk_page_owner_registry_lifetime_compile_fail.rs",
    "scripts/tests/fixtures/ihk_page_owner_registry_sync_compile_fail.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/Documentation/kbuild/makefiles.rst",
    "scripts/tests/fixtures/rust-core-rocky-6.12/Makefile",
    "scripts/tests/fixtures/rust-core-rocky-6.12/arch/arm64/Makefile",
    "scripts/tests/fixtures/rust-core-rocky-6.12/arch/loongarch/kernel/Makefile",
    "scripts/tests/fixtures/rust-core-rocky-6.12/arch/loongarch/kvm/Makefile",
    "scripts/tests/fixtures/rust-core-rocky-6.12/arch/riscv/kernel/Makefile",
    "scripts/tests/fixtures/rust-core-rocky-6.12/drivers/iio/magnetometer/ak8974.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/drivers/input/joystick/magellan.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/drivers/net/wireless/ath/carl9170/fw.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/fs/cachefiles/key.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/fs/netfs/fscache_cache.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/fs/netfs/fscache_cookie.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/include/linux/blk-mq.h",
    "scripts/tests/fixtures/rust-core-rocky-6.12/init/Kconfig",
    "scripts/tests/fixtures/rust-core-rocky-6.12/lib/crypto/aescfb.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/lib/crypto/aesgcm.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/mm/ksm.c",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/Makefile",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/bindings/lib.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/block/mq/tag_set.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/ioctl.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/init/macros.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/lib.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/list/arc.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/sync/arc.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/uaccess.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/macros/module.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/rust/uapi/lib.rs",
    "scripts/tests/fixtures/rust-core-rocky-6.12/scripts/Makefile.build",
    "scripts/tests/fixtures/rust-core-rocky-6.12/scripts/Makefile.compiler",
    "scripts/tests/fixtures/rust-core-rocky-6.12/scripts/Makefile.extrawarn",
    "scripts/tests/fixtures/rust-core-rocky-6.12/scripts/generate_rust_analyzer.py",
]
SOURCE_CLOSURE_KEYS = {
    "entry_type",
    "link_target",
    "origin",
    "path",
    "sha256",
    "size",
    "source_identity",
}
CAPTURE_AUTHORITY_ID = "rk-001-license-capture-source-closure-v1"
REQUIRED_ITEM_KEYS = {
    "authorship_signals",
    "entry_type",
    "license_text_paths",
    "link_target",
    "origin",
    "path",
    "review_status",
    "sha256",
    "size",
    "source_identity",
    "spdx_expression",
    "unresolved_reasons",
}
SPDX_LINE = re.compile(
    br"^(?:SPDX-License-Identifier:|[ \t]*(?://+|/\*+|\*+|#+|;+|--+|\.\.|<!--)"
    br"[ \t]*SPDX-License-Identifier:)[ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
VALID_LICENSE = re.compile(
    br"^(?:Valid-License-Identifier|SPDX-Exception-Identifier):[ \t]*"
    br"([A-Za-z0-9.+-]+)[ \t]*\r?$",
    re.IGNORECASE | re.MULTILINE,
)
SPDX_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")
PATCH_AUTHOR = re.compile(
    br"^(?:From|Author|Signed-off-by|Co-developed-by):[ \t]*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[1-9][0-9]*$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class InventoryError(Exception):
    pass


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=reject_duplicates)
    except InventoryError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise InventoryError("cannot read {0}: {1}".format(path, error))
    if not isinstance(value, dict):
        raise InventoryError("{0} must contain one JSON object".format(path))
    return value


def hash_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def hash_stream(stream, expected_size=None):
    digest = hashlib.sha256()
    size = 0
    prefix = bytearray()
    while True:
        block = stream.read(1024 * 1024)
        if not block:
            break
        if not isinstance(block, bytes):
            raise InventoryError("archive stream returned non-byte data")
        size += len(block)
        if expected_size is not None and size > expected_size:
            raise InventoryError("archive stream exceeded its declared size")
        if len(prefix) < PREFIX_BYTES:
            prefix.extend(block[: PREFIX_BYTES - len(prefix)])
        digest.update(block)
    return size, digest.hexdigest(), bytes(prefix)


def safe_relative(value, label):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise InventoryError("{0} is not a relative path".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise InventoryError("{0} is not a normalized relative path".format(label))
    return path.as_posix()


def repository_file(repo, relative, label):
    relative = safe_relative(relative, label)
    root = repo.resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    resolved = requested.resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(resolved))))
    except ValueError:
        common = None
    if common != root or requested != resolved:
        raise InventoryError("{0} escapes or traverses a symlink".format(label))
    try:
        info = requested.lstat()
    except OSError as error:
        raise InventoryError("{0} is missing: {1}".format(label, error))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise InventoryError("{0} must be a regular non-symlink file".format(label))
    return requested


def stage_repository_input_paths(repo):
    manifest_path = repository_file(
        repo, "host-kernel/kbuild/stage-manifest.json", "stage manifest"
    )
    manifest = read_json(manifest_path)
    inputs = manifest.get("inputs")
    modules = manifest.get("modules")
    parent = manifest.get("parent_integration")
    if not isinstance(inputs, list) or not isinstance(modules, list):
        raise InventoryError("stage manifest input collections are malformed")
    if not isinstance(parent, dict):
        raise InventoryError("stage manifest parent integration is malformed")
    values = [parent.get("repository_path")]
    for item in inputs:
        if not isinstance(item, dict):
            raise InventoryError("stage manifest input row is malformed")
        values.append(item.get("repository_path"))
    for module in modules:
        if not isinstance(module, dict) or not isinstance(module.get("source"), dict):
            raise InventoryError("stage manifest module source row is malformed")
        values.append(module["source"].get("repository_path"))
    normalized = sorted(
        safe_relative(value, "stage repository input") for value in values
    )
    if len(normalized) != len(set(normalized)):
        raise InventoryError("stage manifest repository inputs are duplicated")
    return normalized


def clean_expression(raw):
    text = raw.decode("ascii", errors="strict").strip()
    for marker in ("*/", "-->", "#", "//"):
        if marker in text:
            text = text.split(marker, 1)[0].rstrip()
    if not text or len(text) > 512 or any(ord(char) < 32 for char in text):
        raise InventoryError("malformed SPDX expression")
    return text


def expressions_from_prefix(prefix):
    values = []
    for match in SPDX_LINE.finditer(prefix):
        try:
            value = clean_expression(match.group(1))
            expression_tokens(value)
        except (UnicodeError, InventoryError):
            return [], "malformed-spdx"
        if value not in values:
            values.append(value)
    if not values:
        return [], "missing-spdx"
    if len(values) != 1:
        return values, "ambiguous-spdx"
    return values, None


def expression_tokens(expression):
    if expression == "NOASSERTION":
        return []
    tokens = [
        token
        for token in SPDX_TOKEN.findall(expression)
        if token.upper() not in ("AND", "OR", "WITH")
    ]
    if not tokens:
        raise InventoryError("SPDX expression has no identifiers: {0}".format(expression))
    return sorted(set(tokens))


def patch_authorship_signals(path, prefix):
    if not path.endswith(".patch"):
        return []
    return sorted(
        set(
            value.decode("utf-8", errors="replace").strip()
            for value in PATCH_AUTHOR.findall(prefix)
        )
    )


def make_item(
    path,
    size,
    digest,
    origin,
    entry_type,
    prefix,
    link_target=None,
    source_identity=None,
):
    path = safe_relative(path, "inventory path")
    expressions, reason = expressions_from_prefix(prefix)
    expression = expressions[0] if len(expressions) == 1 else "NOASSERTION"
    reasons = ["independent-review-required"]
    if reason is not None:
        reasons.append(reason)
    authors = patch_authorship_signals(path, prefix)
    if path.endswith(".patch") and not authors:
        reasons.append("patch-authorship-signal-missing")
    if path.endswith(".patch") and expression == "NOASSERTION":
        reasons.append("patch-license-signal-missing")
    item = {
        "authorship_signals": authors,
        "entry_type": entry_type,
        "license_text_paths": [],
        "link_target": link_target,
        "origin": origin,
        "path": path,
        "review_status": "captured-unreviewed",
        "sha256": digest,
        "size": size,
        "source_identity": dict(source_identity or {}),
        "spdx_expression": expression,
        "unresolved_reasons": sorted(set(reasons)),
    }
    return item


def license_identifiers(prefix):
    return sorted(
        set(match.group(1).decode("ascii") for match in VALID_LICENSE.finditer(prefix))
    )


def normalize_tar_members(archive):
    members = archive.getmembers()
    if not members or len(members) > MAX_ARCHIVE_MEMBERS:
        raise InventoryError("Linux archive member count is empty or exceeds its cap")
    roots = set()
    normalized = []
    for member in members:
        raw = member.name.rstrip("/")
        if not raw:
            continue
        path = PurePosixPath(raw)
        if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
            raise InventoryError("unsafe Linux archive member: {0}".format(member.name))
        if len(path.parts) == 1:
            if not member.isdir():
                raise InventoryError("Linux archive has a file outside its source directory")
            roots.add(path.parts[0])
            continue
        roots.add(path.parts[0])
        relative = PurePosixPath(*path.parts[1:]).as_posix()
        normalized.append((relative, member))
    if len(roots) != 1:
        raise InventoryError("Linux archive must have exactly one top-level directory")
    return normalized


def inventory_linux_archive(archive_path, archive_digest):
    items = []
    licenses = {}
    seen = set()
    total = 0
    try:
        archive = tarfile.open(str(archive_path), mode="r:xz")
    except (OSError, tarfile.TarError) as error:
        raise InventoryError("cannot open Linux source archive: {0}".format(error))
    with archive:
        for relative, member in normalize_tar_members(archive):
            canonical = "linux/{0}".format(relative)
            if canonical in seen:
                raise InventoryError("duplicate Linux archive path: {0}".format(canonical))
            seen.add(canonical)
            origin = "linux-archive:sha256:{0}".format(archive_digest)
            if member.isdir():
                continue
            if member.isreg():
                if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                    raise InventoryError(
                        "Linux archive member exceeds its size cap: {0}".format(
                            canonical
                        )
                    )
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise InventoryError("cannot read archive member: {0}".format(canonical))
                size, digest, prefix = hash_stream(extracted, member.size)
                if size != member.size:
                    raise InventoryError("archive member size changed: {0}".format(canonical))
                total += size
                if total > MAX_ARCHIVE_BYTES:
                    raise InventoryError("Linux archive expansion exceeds its cap")
                item = make_item(
                    canonical,
                    size,
                    digest,
                    origin,
                    "regular",
                    prefix,
                    source_identity={"archive_sha256": archive_digest},
                )
                # Only the canonical LICENSES/ tree declares license texts.
                # Documentation contains literal declaration examples.
                identifiers = (
                    license_identifiers(prefix)
                    if relative.startswith("LICENSES/")
                    else []
                )
                if relative == "COPYING":
                    identifiers.extend(("GPL-2.0", "GPL-2.0-only"))
                if identifiers:
                    for identifier in sorted(set(identifiers)):
                        paths = licenses.setdefault(identifier, [])
                        if canonical not in paths:
                            paths.append(canonical)
                            paths.sort()
                    item["_license_identifiers"] = sorted(set(identifiers))
                items.append(item)
            elif member.issym() or member.islnk():
                target = member.linkname
                if not target or "\x00" in target or PurePosixPath(target).is_absolute():
                    raise InventoryError("unsafe archive link: {0}".format(canonical))
                digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
                items.append(
                    make_item(
                        canonical,
                        len(target.encode("utf-8")),
                        digest,
                        origin,
                        "symlink" if member.issym() else "hardlink",
                        b"",
                        target,
                        {"archive_sha256": archive_digest},
                    )
                )
            else:
                entry_type = "unknown"
                if member.ischr():
                    entry_type = "character-device"
                elif member.isblk():
                    entry_type = "block-device"
                elif member.isfifo():
                    entry_type = "fifo"
                descriptor = "{0}:{1}:{2}".format(
                    entry_type, member.devmajor, member.devminor
                ).encode("ascii")
                item = make_item(
                    canonical,
                    member.size,
                    hashlib.sha256(descriptor).hexdigest(),
                    origin,
                    entry_type,
                    b"",
                    source_identity={"archive_sha256": archive_digest},
                )
                item["unresolved_reasons"].append("nonregular-entry-needs-review")
                item["unresolved_reasons"] = sorted(
                    set(item["unresolved_reasons"])
                )
                items.append(item)
    resolve_items(items, licenses)
    return items, licenses


def resolve_link(path, target):
    relative = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
    root = path.split("/", 1)[0] + "/"
    if relative == ".." or relative.startswith("../") or not relative.startswith(root):
        return None
    try:
        return safe_relative(relative, "archive link target")
    except InventoryError:
        return None


def resolve_items(items, license_map):
    by_path = {item["path"]: item for item in items}
    for item in items:
        identifiers = item.pop("_license_identifiers", [])
        if identifiers:
            item["spdx_expression"] = " OR ".join(identifiers)
            item["license_text_paths"] = [item["path"]]
            continue
        expression = item["spdx_expression"]
        if expression != "NOASSERTION":
            missing = [token for token in expression_tokens(expression) if token not in license_map]
            if not missing:
                item["license_text_paths"] = sorted(
                    set(
                        path
                        for token in expression_tokens(expression)
                        for path in license_map[token]
                    )
                )
            else:
                item["unresolved_reasons"].append(
                    "license-text-mapping-missing:{0}".format(",".join(missing))
                )
                item["unresolved_reasons"] = sorted(
                    set(item["unresolved_reasons"])
                )
    for item in items:
        if item["entry_type"] in ("symlink", "hardlink"):
            target = resolve_link(item["path"], item["link_target"])
            target_item = by_path.get(target)
            if target_item is not None and target_item["spdx_expression"] != "NOASSERTION":
                item["spdx_expression"] = target_item["spdx_expression"]
                item["license_text_paths"] = list(target_item["license_text_paths"])
            else:
                item["unresolved_reasons"].append(
                    "link-target-missing-or-unlicensed"
                )
            item["unresolved_reasons"].append("link-provenance-needs-review")
            item["unresolved_reasons"] = sorted(set(item["unresolved_reasons"]))


def run_pipeline(first, second, cwd=None):
    try:
        producer = subprocess.Popen(first, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        consumer = subprocess.Popen(
            second,
            stdin=producer.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )
        assert producer.stdout is not None
        producer.stdout.close()
        stdout, consumer_stderr = consumer.communicate()
        producer_stderr = producer.communicate()[1]
    except OSError as error:
        raise InventoryError("cannot run SRPM extraction tools: {0}".format(error))
    if producer.returncode != 0 or consumer.returncode != 0:
        raise InventoryError(
            "SRPM extraction pipeline failed: {0} {1}".format(
                producer_stderr.decode(errors="replace").strip(),
                consumer_stderr.decode(errors="replace").strip(),
            )
        )
    return stdout


def extract_srpm(srpm, destination):
    listing = run_pipeline(
        ["rpm2cpio", str(srpm)], ["cpio", "--quiet", "-it"]
    ).decode("utf-8", errors="strict")
    names = []
    for raw in listing.splitlines():
        clean = raw[2:] if raw.startswith("./") else raw
        names.append(safe_relative(clean, "SRPM member"))
    if not names or len(names) != len(set(names)):
        raise InventoryError("SRPM member list is empty or contains duplicates")
    run_pipeline(
        ["rpm2cpio", str(srpm)],
        ["cpio", "--quiet", "-idm", "--no-absolute-filenames", "--no-preserve-owner"],
        cwd=destination,
    )
    for directory, subdirectories, files in os.walk(str(destination), followlinks=False):
        for name in subdirectories + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise InventoryError("SRPM extraction produced a symlink")


def srpm_inventory(extracted, lock, series, license_map):
    items = []
    files = []
    for directory, _, names in os.walk(str(extracted), followlinks=False):
        for name in names:
            path = Path(directory) / name
            if not path.is_file() or path.is_symlink():
                raise InventoryError("SRPM payload contains a non-regular file")
            files.append(path)
    files.sort(key=lambda path: path.relative_to(extracted).as_posix())
    dist_paths = {
        item["path"]: item for item in list(lock["dist_git"]["content"]) + list(series["patches"])
    }
    embedded = {PurePosixPath(item["path"]).name: item for item in lock["embedded_objects"]}
    linux_name = PurePosixPath(lock["embedded_objects"][2]["path"]).name
    linux_archive = None
    for path in files:
        relative = path.relative_to(extracted).as_posix()
        canonical_tail = (
            "SPECS/kernel.spec" if path.name == "kernel.spec" else "SOURCES/{0}".format(relative)
        )
        size, digest = hash_file(path)
        locked = dist_paths.get(canonical_tail)
        if locked is not None and (size != locked["size"] or digest != locked["sha256"]):
            raise InventoryError("dist-git-bound SRPM object drift: {0}".format(canonical_tail))
        embedded_item = embedded.get(path.name)
        if embedded_item is not None and (
            size != embedded_item["size"] or digest != embedded_item["sha256"]
        ):
            raise InventoryError("embedded SRPM object drift: {0}".format(path.name))
        with path.open("rb") as stream:
            prefix = stream.read(PREFIX_BYTES)
        origin = (
            "dist-git:{0}".format(lock["dist_git"]["commit"])
            if locked is not None
            else "srpm:sha256:{0}".format(lock["source_rpm"]["sha256"])
        )
        item = make_item(
            "srpm/{0}".format(canonical_tail),
            size,
            digest,
            origin,
            "regular",
            prefix,
            source_identity={
                "source_rpm_sha256": lock["source_rpm"]["sha256"],
            },
        )
        if path.name == linux_name:
            item["spdx_expression"] = lock["licenses"]["declared_spdx_expression"]
            item["unresolved_reasons"].append("package-expression-needs-review")
            item["unresolved_reasons"] = sorted(set(item["unresolved_reasons"]))
            linux_archive = path
        items.append(item)
    missing = sorted(name for name in embedded if not any(path.name == name for path in files))
    if missing or linux_archive is None:
        raise InventoryError("locked embedded objects missing from SRPM: {0}".format(missing))
    resolve_items(items, license_map)
    return items, linux_archive


def git_command(repo, arguments):
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "LC_ALL": "C",
        }
    )
    command = ["git", "-c", "safe.directory={0}".format(repo)] + list(arguments)
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo),
            check=True,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        stderr = getattr(error, "stderr", b"").decode(
            "utf-8", errors="replace"
        ).strip()
        raise InventoryError("git command failed: {0}".format(stderr))
    return completed.stdout


def parse_tree(payload):
    rows = []
    seen = set()
    for raw in payload.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, raw_path = raw.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (UnicodeError, ValueError) as error:
            raise InventoryError("dist-git tree row is malformed: {0}".format(error))
        safe_relative(path, "dist-git tree path")
        if path in seen:
            raise InventoryError("duplicate dist-git tree path: {0}".format(path))
        if kind != "blob" or not COMMIT.fullmatch(oid):
            raise InventoryError("unsupported dist-git object: {0}".format(path))
        if mode not in ("100644", "100755", "120000"):
            raise InventoryError("unsupported dist-git blob mode: {0}".format(mode))
        seen.add(path)
        rows.append((path, mode, oid))
    if not rows:
        raise InventoryError("dist-git tree is empty")
    return rows


def inventory_dist_git(dist_git, lock, license_map):
    commit = lock["dist_git"]["commit"]
    rows = parse_tree(
        git_command(dist_git, ["ls-tree", "-rz", "--full-tree", commit])
    )
    items = []
    for path, mode, oid in rows:
        payload = git_command(dist_git, ["cat-file", "blob", oid])
        entry_type = "symlink" if mode == "120000" else "regular"
        link_target = None
        if entry_type == "symlink":
            try:
                link_target = payload.decode("utf-8")
            except UnicodeError:
                raise InventoryError("dist-git symlink target is not UTF-8: {0}".format(path))
        item = make_item(
            "dist-git/{0}".format(path),
            len(payload),
            hashlib.sha256(payload).hexdigest(),
            "rocky-dist-git:{0}".format(commit),
            entry_type,
            payload[:PREFIX_BYTES],
            link_target,
            {"git_blob_oid": oid, "git_mode": mode},
        )
        if entry_type == "symlink":
            item["unresolved_reasons"].append("dist-git-symlink-needs-review")
            item["unresolved_reasons"] = sorted(set(item["unresolved_reasons"]))
        items.append(item)
    resolve_items(items, license_map)
    return items


def repository_patch_items(repo, head, license_map):
    if stage_repository_input_paths(repo) != EXPECTED_STAGE_REPOSITORY_INPUT_PATHS:
        raise InventoryError(
            "repository license authority differs from the exact staging input closure"
        )
    items = []
    for relative in EXPECTED_REPOSITORY_INPUT_PATHS:
        path = repository_file(repo, relative, "local patch input")
        size, digest = hash_file(path)
        payload = git_command(repo, ["show", "{0}:{1}".format(head, relative)])
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise InventoryError(
                "local patch input differs from the bound repository commit: {0}".format(
                    relative
                )
            )
        oid = git_command(
            repo, ["rev-parse", "{0}:{1}".format(head, relative)]
        ).decode("ascii").strip()
        if not COMMIT.fullmatch(oid):
            raise InventoryError("local patch input has no immutable blob ID")
        items.append(
            make_item(
                "repository/{0}".format(relative),
                size,
                digest,
                "repository-commit:{0}".format(head),
                "regular",
                payload[:PREFIX_BYTES],
                source_identity={"git_blob_oid": oid, "git_commit": head},
            )
        )
    resolve_items(items, license_map)
    return items


def git_head(repo):
    head = git_command(repo, ["rev-parse", "HEAD"]).decode("ascii").strip()
    if not COMMIT.fullmatch(head):
        raise InventoryError("repository HEAD is not a full commit")
    return head


def validate_binding(repo, args):
    head = git_head(repo)
    if args.github_head_sha != head:
        raise InventoryError("GitHub head does not match checked-out repository")
    for label, value in (
        ("github run id", args.github_run_id),
        ("github run attempt", args.github_run_attempt),
    ):
        if not isinstance(value, str) or not RUN_ID.fullmatch(value):
            raise InventoryError("{0} is invalid".format(label))
    if args.github_repository != "phoenix-hacking/mckernel":
        raise InventoryError("unexpected GitHub repository")
    if args.container_image != EXPECTED_CONTAINER_IMAGE:
        raise InventoryError("container image differs from the locked Rocky 10.2 image")
    return {
        "container_image": args.container_image,
        "github_head_sha": head,
        "github_repository": args.github_repository,
        "github_run_attempt": args.github_run_attempt,
        "github_run_id": args.github_run_id,
    }


def validate_capture_binding(binding):
    expected_keys = {
        "container_image",
        "github_head_sha",
        "github_repository",
        "github_run_attempt",
        "github_run_id",
    }
    if not isinstance(binding, dict) or set(binding) != expected_keys:
        raise InventoryError("capture binding fields changed")
    if binding["container_image"] != EXPECTED_CONTAINER_IMAGE:
        raise InventoryError("capture binding has the wrong Rocky image")
    if binding["github_repository"] != "phoenix-hacking/mckernel":
        raise InventoryError("capture binding has the wrong repository")
    if not COMMIT.fullmatch(binding["github_head_sha"]):
        raise InventoryError("capture binding head is not a full commit")
    for key in ("github_run_attempt", "github_run_id"):
        if not isinstance(binding[key], str) or not RUN_ID.fullmatch(binding[key]):
            raise InventoryError("capture binding {0} is invalid".format(key))
    return binding


def validate_generated_item(item, binding=None):
    if not isinstance(item, dict) or set(item) != REQUIRED_ITEM_KEYS:
        raise InventoryError("inventory item has an invalid schema")
    safe_relative(item["path"], "inventory item path")
    if not SHA256.fullmatch(item.get("sha256", "")):
        raise InventoryError("inventory item SHA-256 is malformed")
    if (
        isinstance(item.get("size"), bool)
        or not isinstance(item.get("size"), int)
        or item["size"] < 0
    ):
        raise InventoryError("inventory item size is malformed")
    if not isinstance(item.get("origin"), str) or not item["origin"]:
        raise InventoryError("inventory item origin is missing")
    if not isinstance(item.get("source_identity"), dict) or not item["source_identity"]:
        raise InventoryError("inventory item source identity is missing")
    path = item["path"]
    origin = item["origin"]
    identity = item["source_identity"]
    if path.startswith("linux/"):
        if origin != "linux-archive:sha256:{0}".format(
            EXPECTED_LINUX_ARCHIVE_SHA256
        ) or identity != {"archive_sha256": EXPECTED_LINUX_ARCHIVE_SHA256}:
            raise InventoryError("Linux inventory item has the wrong source authority")
    elif path.startswith("dist-git/"):
        if (
            origin != "rocky-dist-git:{0}".format(EXPECTED_DIST_GIT_COMMIT)
            or set(identity) != {"git_blob_oid", "git_mode"}
            or not COMMIT.fullmatch(identity.get("git_blob_oid", ""))
            or identity.get("git_mode") not in ("100644", "100755", "120000")
        ):
            raise InventoryError("dist-git inventory item has the wrong source authority")
    elif path.startswith("srpm/"):
        if (
            origin
            not in (
                "srpm:sha256:{0}".format(EXPECTED_SOURCE_RPM_SHA256),
                "dist-git:{0}".format(EXPECTED_DIST_GIT_COMMIT),
            )
            or identity != {"source_rpm_sha256": EXPECTED_SOURCE_RPM_SHA256}
        ):
            raise InventoryError("SRPM inventory item has the wrong source authority")
    elif path.startswith("repository/"):
        if binding is None:
            raise InventoryError("repository item needs the capture binding")
        head = binding["github_head_sha"]
        if (
            origin != "repository-commit:{0}".format(head)
            or set(identity) != {"git_blob_oid", "git_commit"}
            or not COMMIT.fullmatch(identity.get("git_blob_oid", ""))
            or identity.get("git_commit") != head
        ):
            raise InventoryError("repository item has the wrong source authority")
    else:
        raise InventoryError("inventory item has an unknown source namespace")
    if item.get("review_status") != "captured-unreviewed":
        raise InventoryError("generated inventory may not contain reviewed items")
    reasons = item.get("unresolved_reasons")
    if (
        not isinstance(reasons, list)
        or reasons != sorted(set(reasons))
        or "independent-review-required" not in reasons
        or any(not isinstance(reason, str) or not reason for reason in reasons)
    ):
        raise InventoryError("inventory item review reasons are incomplete")
    license_paths = item.get("license_text_paths")
    if not isinstance(license_paths, list) or license_paths != sorted(set(license_paths)):
        raise InventoryError("inventory license-text paths are malformed")
    for license_path in license_paths:
        safe_relative(license_path, "inventory license text")
    if not isinstance(item.get("spdx_expression"), str) or not item["spdx_expression"]:
        raise InventoryError("inventory SPDX expression is malformed")
    authors = item.get("authorship_signals")
    if (
        not isinstance(authors, list)
        or authors != sorted(set(authors))
        or any(not isinstance(author, str) or not author for author in authors)
    ):
        raise InventoryError("inventory authorship signals are malformed")
    link_target = item.get("link_target")
    if item.get("entry_type") in ("symlink", "hardlink"):
        if not isinstance(link_target, str) or not link_target:
            raise InventoryError("inventory link target is missing")
    elif link_target is not None:
        raise InventoryError("non-link inventory item has a link target")
    if item["path"].endswith(".patch"):
        if not authors and "patch-authorship-signal-missing" not in reasons:
            raise InventoryError("patch lacks authorship evidence or a blocker")
        if (
            item["spdx_expression"] == "NOASSERTION"
            and "patch-license-signal-missing" not in reasons
        ):
            raise InventoryError("patch lacks license evidence or a blocker")
    return item


def source_namespace(path):
    for namespace in ("dist-git", "linux", "repository", "srpm"):
        if path.startswith(namespace + "/"):
            return namespace
    raise InventoryError("inventory item has an unknown source namespace")


def source_closure(items):
    ordered = sorted(items, key=lambda item: item["path"])
    path_digest = hashlib.sha256()
    source_digest = hashlib.sha256()
    for item in ordered:
        row = {key: item[key] for key in SOURCE_CLOSURE_KEYS}
        path_digest.update((item["path"] + "\n").encode("utf-8"))
        source_digest.update(canonical_json(row) + b"\n")
    return {
        "item_count": len(ordered),
        "path_set_sha256": path_digest.hexdigest(),
        "source_manifest_sha256": source_digest.hexdigest(),
    }


def inventory_source_closures(items):
    grouped = {name: [] for name in ("dist-git", "linux", "repository", "srpm")}
    for item in items:
        grouped[source_namespace(item["path"])].append(item)
    closures = {name: source_closure(grouped[name]) for name in sorted(grouped)}
    if any(value["item_count"] < 1 for value in closures.values()):
        raise InventoryError("inventory omits a required source namespace")
    return closures


def expected_source_closures(repo, binding):
    validate_capture_binding(binding)
    head = git_head(repo)
    if head != binding["github_head_sha"]:
        raise InventoryError("capture binding differs from the verification checkout")
    repository_items = repository_patch_items(repo, head, {})
    expected = dict(EXPECTED_STATIC_NAMESPACE_CLOSURES)
    expected["repository"] = source_closure(repository_items)
    return {name: expected[name] for name in sorted(expected)}


def validate_source_closures(items, binding, repo):
    actual = inventory_source_closures(items)
    expected = expected_source_closures(repo, binding)
    if actual != expected:
        differences = sorted(
            name for name in expected if actual.get(name) != expected.get(name)
        )
        raise InventoryError(
            "inventory source closure differs for: {0}".format(
                ", ".join(differences)
            )
        )
    return actual


def derived_capture_scope(closures):
    namespaces = {}
    for name in sorted(closures):
        namespaces[name] = dict(closures[name])
        namespaces[name]["complete"] = True
    return {
        "authority_id": CAPTURE_AUTHORITY_ID,
        "namespaces": namespaces,
        "unexpanded_embedded_objects": UNEXPANDED_EMBEDDED_OBJECTS,
    }


def expected_capture_authority_record():
    namespaces = dict(EXPECTED_STATIC_NAMESPACE_CLOSURES)
    namespaces["repository"] = {
        "paths": EXPECTED_REPOSITORY_INPUT_PATHS,
        "verification": (
            "recompute exact blob OIDs, bytes, and closure from the bound Git commit"
        ),
    }
    return {
        "authority_id": CAPTURE_AUTHORITY_ID,
        "closure_algorithm": (
            "sha256 over canonical sorted path rows and canonical source-identity rows"
        ),
        "namespaces": {name: namespaces[name] for name in sorted(namespaces)},
        "scope_is_derived_from_verified_closures": True,
    }


def write_capture(output_dir, items, binding, lock_sha, series_sha, repo):
    validate_capture_binding(binding)
    if lock_sha != EXPECTED_SOURCE_LOCK_SHA256:
        raise InventoryError("capture source-lock digest is not authoritative")
    if series_sha != EXPECTED_PATCH_SERIES_SHA256:
        raise InventoryError("capture patch-series digest is not authoritative")
    try:
        output_dir.mkdir(mode=0o700)
    except OSError as error:
        raise InventoryError("cannot create fresh capture directory: {0}".format(error))
    ordered = sorted(items, key=lambda item: item["path"])
    if not ordered or len({item["path"] for item in ordered}) != len(ordered):
        raise InventoryError("inventory is empty or contains duplicate paths")
    for item in ordered:
        validate_generated_item(item, binding)
    closures = validate_source_closures(ordered, binding, repo)
    raw_digest = hashlib.sha256()
    inventory_path = output_dir / "license-inventory.jsonl.gz"
    signal_issue_count = 0
    unresolved_sample = []
    with inventory_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for item in ordered:
                line = canonical_json(item) + b"\n"
                raw_digest.update(line)
                compressed.write(line)
                if item["unresolved_reasons"] != ["independent-review-required"]:
                    signal_issue_count += 1
                if len(unresolved_sample) < 200:
                    unresolved_sample.append(
                        {
                            "path": item["path"],
                            "reasons": item["unresolved_reasons"],
                        }
                    )
    inventory_size, inventory_sha = hash_file(inventory_path)
    summary = {
        "binding": binding,
        "blockers": CAPTURE_BLOCKERS,
        "complete": False,
        "credit_eligible": False,
        "inventory": {
            "compressed_sha256": inventory_sha,
            "compressed_size": inventory_size,
            "item_count": len(ordered),
            "path": inventory_path.name,
            "uncompressed_sha256": raw_digest.hexdigest(),
        },
        "patch_series_sha256": series_sha,
        "review_complete": False,
        "review_counts": {"captured-unreviewed": len(ordered)},
        "schema_version": SCHEMA_VERSION,
        "scope": derived_capture_scope(closures),
        "signal_issue_count": signal_issue_count,
        "source_lock_sha256": lock_sha,
        "unresolved_count": len(ordered),
        "unresolved_sample": unresolved_sample,
    }
    summary_path = output_dir / "license-inventory-summary.json"
    summary_path.write_bytes(canonical_json(summary) + b"\n")
    _, summary_sha = hash_file(summary_path)
    checksums = "{0}  {1}\n{2}  {3}\n".format(
        inventory_sha, inventory_path.name, summary_sha, summary_path.name
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="ascii")
    return summary


def verify_capture(directory, repo):
    if directory.is_symlink() or not directory.is_dir():
        raise InventoryError("capture directory is missing or symlinked")
    summary_path = repository_file(
        directory, "license-inventory-summary.json", "capture summary"
    )
    summary = read_json(summary_path)
    expected_summary_keys = {
        "binding",
        "blockers",
        "complete",
        "credit_eligible",
        "inventory",
        "patch_series_sha256",
        "review_complete",
        "review_counts",
        "schema_version",
        "scope",
        "signal_issue_count",
        "source_lock_sha256",
        "unresolved_count",
        "unresolved_sample",
    }
    if set(summary) != expected_summary_keys:
        raise InventoryError("capture summary fields changed")
    if summary_path.read_bytes() != canonical_json(summary) + b"\n":
        raise InventoryError("capture summary is not canonical JSON")
    validate_capture_binding(summary["binding"])
    if (
        summary["schema_version"] != SCHEMA_VERSION
        or summary["credit_eligible"] is not False
        or summary["review_complete"] is not False
        or summary["complete"] is not False
        or summary["blockers"] != CAPTURE_BLOCKERS
        or summary["source_lock_sha256"] != EXPECTED_SOURCE_LOCK_SHA256
        or summary["patch_series_sha256"] != EXPECTED_PATCH_SERIES_SHA256
    ):
        raise InventoryError("capture summary overclaims or changes its authorities")
    inventory = summary.get("inventory")
    expected_inventory_keys = {
        "compressed_sha256",
        "compressed_size",
        "item_count",
        "path",
        "uncompressed_sha256",
    }
    if not isinstance(inventory, dict) or set(inventory) != expected_inventory_keys:
        raise InventoryError("capture summary inventory is missing or changed")
    if inventory["path"] != "license-inventory.jsonl.gz":
        raise InventoryError("capture inventory path changed")
    path = repository_file(directory, inventory["path"], "captured inventory")
    size, digest = hash_file(path)
    if size != inventory["compressed_size"] or digest != inventory["compressed_sha256"]:
        raise InventoryError("compressed inventory digest or size mismatch")
    raw_digest = hashlib.sha256()
    raw_size = 0
    count = 0
    previous = None
    signal_issue_count = 0
    unresolved_sample = []
    items = []
    try:
        with gzip.open(str(path), "rb") as stream:
            for line in stream:
                if len(line) > 1024 * 1024 or not line.endswith(b"\n"):
                    raise InventoryError("inventory line is oversized or unterminated")
                raw_size += len(line)
                if raw_size > MAX_INVENTORY_BYTES:
                    raise InventoryError("inventory expansion exceeds its cap")
                raw_digest.update(line)
                try:
                    item = json.loads(
                        line.decode("ascii"), object_pairs_hook=reject_duplicates
                    )
                except (UnicodeError, ValueError) as error:
                    raise InventoryError("invalid inventory JSON: {0}".format(error))
                validate_generated_item(item, summary["binding"])
                items.append(item)
                if canonical_json(item) + b"\n" != line:
                    raise InventoryError("inventory JSON is not canonical")
                path_text = item["path"]
                if previous is not None and path_text <= previous:
                    raise InventoryError("inventory paths are duplicate or unsorted")
                previous = path_text
                if item["unresolved_reasons"] != ["independent-review-required"]:
                    signal_issue_count += 1
                if len(unresolved_sample) < 200:
                    unresolved_sample.append(
                        {"path": path_text, "reasons": item["unresolved_reasons"]}
                    )
                count += 1
                if count > MAX_ARCHIVE_MEMBERS:
                    raise InventoryError("inventory item count exceeds its cap")
    except (OSError, EOFError) as error:
        raise InventoryError("cannot read compressed inventory: {0}".format(error))
    if (
        count < 1
        or count != inventory["item_count"]
        or raw_digest.hexdigest() != inventory["uncompressed_sha256"]
        or summary["unresolved_count"] != count
        or summary["review_counts"] != {"captured-unreviewed": count}
        or summary["signal_issue_count"] != signal_issue_count
        or summary["unresolved_sample"] != unresolved_sample
    ):
        raise InventoryError("inventory counts, digest, or review state is stale")
    closures = validate_source_closures(items, summary["binding"], repo)
    if summary["scope"] != derived_capture_scope(closures):
        raise InventoryError("capture scope is not derived from verified closures")
    _, summary_sha = hash_file(summary_path)
    checksums = "{0}  {1}\n{2}  {3}\n".format(
        digest, path.name, summary_sha, summary_path.name
    ).encode("ascii")
    checksum_path = repository_file(directory, "SHA256SUMS", "capture checksums")
    if checksum_path.read_bytes() != checksums:
        raise InventoryError("capture checksum manifest is stale")
    return summary


def check_repository(repo):
    lock_path = repository_file(repo, SOURCE_LOCK.as_posix(), "source lock")
    series_path = repository_file(repo, SERIES.as_posix(), "patch series")
    workflow = repository_file(repo, WORKFLOW.as_posix(), "source evidence workflow")
    lock = read_json(lock_path)
    series = read_json(series_path)
    lock_size, lock_digest = hash_file(lock_path)
    series_size, series_digest = hash_file(series_path)
    if lock_size < 1 or lock_digest != EXPECTED_SOURCE_LOCK_SHA256:
        raise InventoryError("source-lock bytes differ from the reviewed identity")
    if series_size < 1 or series_digest != EXPECTED_PATCH_SERIES_SHA256:
        raise InventoryError("patch-series bytes differ from the reviewed identity")
    if lock.get("licenses", {}).get("capture_authority") != (
        expected_capture_authority_record()
    ):
        raise InventoryError("source-lock capture closure authority differs")
    try:
        import rocky_kernel_source_lock as source_lock
    except ImportError as error:
        raise InventoryError("cannot import source-lock validator: {0}".format(error))
    try:
        blockers = source_lock.validate_loaded_manifests(
            lock, series, series_path.read_bytes(), repo
        )
    except source_lock.SourceLockError as error:
        raise InventoryError("source-lock validation failed: {0}".format(error))
    if len(blockers) != 1 or not blockers[0].startswith("license_inventory:"):
        raise InventoryError("license inventory is not the sole RK-001 blocker")
    workflow_text = workflow.read_text(encoding="utf-8")
    for token in (
        "rocky_kernel_license_inventory.py",
        "--capture",
        "rk001-license-inventory-",
        "cpio",
        "xz",
    ):
        if token not in workflow_text:
            raise InventoryError("source workflow lacks license capture token: {0}".format(token))
    return lock, series


def capture(repo, args):
    lock, series = check_repository(repo)
    binding = validate_binding(repo, args)
    lock_path = repository_file(repo, SOURCE_LOCK.as_posix(), "source lock")
    series_path = repository_file(repo, SERIES.as_posix(), "patch series")
    _, lock_sha = hash_file(lock_path)
    _, series_sha = hash_file(series_path)
    try:
        import rocky_kernel_source_lock as source_lock
        import rocky_kernel_source_evidence as source_evidence
    except ImportError as error:
        raise InventoryError("cannot import source verifiers: {0}".format(error))
    cache_root = args.cache_root.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    try:
        srpm = source_lock.acquire_source(lock, cache_root, timeout=300.0)
    except Exception as error:
        raise InventoryError("locked SRPM acquisition failed: {0}".format(error))
    with tempfile.TemporaryDirectory(prefix="rk001-license-") as temporary:
        work = Path(temporary)
        extracted = work / "srpm"
        extracted.mkdir()
        extract_srpm(srpm, extracted)
        linux_name = PurePosixPath(lock["embedded_objects"][2]["path"]).name
        candidates = list(extracted.rglob(linux_name))
        if len(candidates) != 1:
            raise InventoryError("exact Linux source archive is missing or duplicated")
        linux_path = candidates[0]
        linux_size, linux_sha = hash_file(linux_path)
        expected_linux = lock["embedded_objects"][2]
        if linux_size != expected_linux["size"] or linux_sha != expected_linux["sha256"]:
            raise InventoryError("embedded Linux archive identity changed")
        linux_items, license_map = inventory_linux_archive(linux_path, linux_sha)
        srpm_items, _ = srpm_inventory(extracted, lock, series, license_map)
        try:
            source_evidence.fetch_and_verify_dist_git(work, lock, series)
        except source_evidence.EvidenceError as error:
            raise InventoryError(
                "locked dist-git acquisition failed: {0}".format(error)
            )
        dist_git_items = inventory_dist_git(work / "dist-git", lock, license_map)
        local_items = repository_patch_items(repo, binding["github_head_sha"], license_map)
        summary = write_capture(
            args.output_dir.resolve(),
            linux_items + srpm_items + dist_git_items + local_items,
            binding,
            lock_sha,
            series_sha,
            repo,
        )
    verify_capture(args.output_dir.resolve(), repo)
    print(
        "RK-001 license inventory captured: items={0} unresolved={1} complete={2}".format(
            summary["inventory"]["item_count"],
            summary["unresolved_count"],
            str(summary["complete"]).lower(),
        )
    )


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--verify-capture", type=Path)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--github-repository")
    parser.add_argument("--container-image")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo.resolve()
    try:
        if args.check:
            check_repository(repo)
            print("RK-001 license inventory capture contract: PASS")
            return 0
        if args.verify_capture is not None:
            summary = verify_capture(args.verify_capture.resolve(), repo)
            print(
                "RK-001 license capture verified: items={0} unresolved={1}".format(
                    summary["inventory"]["item_count"], summary["unresolved_count"]
                )
            )
            return 0
        required = {
            "--cache-root": args.cache_root,
            "--container-image": args.container_image,
            "--github-head-sha": args.github_head_sha,
            "--github-repository": args.github_repository,
            "--github-run-attempt": args.github_run_attempt,
            "--github-run-id": args.github_run_id,
            "--output-dir": args.output_dir,
        }
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            raise InventoryError("--capture requires {0}".format(", ".join(missing)))
        capture(repo, args)
        return 0
    except InventoryError as error:
        print("RK-001 license inventory error: {0}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
