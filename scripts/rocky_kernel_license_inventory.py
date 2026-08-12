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
PREFIX_BYTES = 128 * 1024
REQUIRED_ITEM_KEYS = {
    "entry_type",
    "license_text_paths",
    "origin",
    "path",
    "review_status",
    "sha256",
    "size",
    "spdx_expression",
}
SPDX_LINE = re.compile(
    br"SPDX-License-Identifier:[ \t]*([^\r\n]+)", re.IGNORECASE
)
VALID_LICENSE = re.compile(
    br"(?:Valid-License-Identifier|SPDX-Exception-Identifier):[ \t]*"
    br"([A-Za-z0-9.+-]+)",
    re.IGNORECASE,
)
SPDX_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")
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


def hash_stream(stream):
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


def make_item(path, size, digest, origin, entry_type, prefix, link_target=None):
    path = safe_relative(path, "inventory path")
    expressions, reason = expressions_from_prefix(prefix)
    expression = expressions[0] if len(expressions) == 1 else "NOASSERTION"
    item = {
        "entry_type": entry_type,
        "license_text_paths": [],
        "origin": origin,
        "path": path,
        "review_status": "captured-unreviewed",
        "sha256": digest,
        "size": size,
        "spdx_expression": expression,
    }
    item["_reason"] = reason
    if link_target is not None:
        item["_link_target"] = link_target
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
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise InventoryError("cannot read archive member: {0}".format(canonical))
                size, digest, prefix = hash_stream(extracted)
                if size != member.size:
                    raise InventoryError("archive member size changed: {0}".format(canonical))
                total += size
                if total > MAX_ARCHIVE_BYTES:
                    raise InventoryError("Linux archive expansion exceeds its cap")
                item = make_item(canonical, size, digest, origin, "regular", prefix)
                identifiers = license_identifiers(prefix)
                if relative == "COPYING":
                    identifiers.extend(("GPL-2.0", "GPL-2.0-only"))
                if identifiers:
                    for identifier in sorted(set(identifiers)):
                        if identifier in licenses and licenses[identifier] != canonical:
                            # The top-level COPYING duplicates identifiers whose
                            # canonical machine-readable text lives in LICENSES/.
                            # Prefer LICENSES/ and reject every other collision.
                            if relative == "COPYING":
                                continue
                            if licenses[identifier] == "linux/COPYING":
                                licenses[identifier] = canonical
                                continue
                            raise InventoryError(
                                "duplicate license text for {0}".format(identifier)
                            )
                        licenses[identifier] = canonical
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
                    )
                )
            else:
                raise InventoryError("unsupported Linux archive entry: {0}".format(canonical))
    resolve_items(items, licenses)
    return items, licenses


def resolve_link(path, target):
    relative = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
    if relative == ".." or relative.startswith("../") or not relative.startswith("linux/"):
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
            item["review_status"] = "verified"
            item.pop("_reason", None)
            continue
        expression = item["spdx_expression"]
        if expression != "NOASSERTION":
            missing = [token for token in expression_tokens(expression) if token not in license_map]
            if not missing:
                item["license_text_paths"] = sorted(
                    set(license_map[token] for token in expression_tokens(expression))
                )
                item["review_status"] = "verified"
                item.pop("_reason", None)
    for item in items:
        if item["entry_type"] in ("symlink", "hardlink"):
            target = resolve_link(item["path"], item.pop("_link_target"))
            target_item = by_path.get(target)
            if target_item is not None and target_item.get("review_status") == "verified":
                item["spdx_expression"] = target_item["spdx_expression"]
                item["license_text_paths"] = list(target_item["license_text_paths"])
                item["review_status"] = "verified"
                item.pop("_reason", None)


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
            "srpm/{0}".format(canonical_tail), size, digest, origin, "regular", prefix
        )
        if path.name == linux_name:
            item["spdx_expression"] = lock["licenses"]["declared_spdx_expression"]
            item["_reason"] = "package-expression-needs-review"
            linux_archive = path
        items.append(item)
    missing = sorted(name for name in embedded if not any(path.name == name for path in files))
    if missing or linux_archive is None:
        raise InventoryError("locked embedded objects missing from SRPM: {0}".format(missing))
    resolve_items(items, license_map)
    return items, linux_archive


def repository_patch_items(repo, head, license_map):
    paths = [
        "host-kernel/kbuild/parent-integration-v1.json",
        "host-kernel/kbuild/patches/0001-drivers-misc-add-mckernel-rust-host-modules.patch",
        "host-kernel/kbuild/stage-manifest.json",
        "host-kernel/rocky/patches/series.json",
    ]
    items = []
    for relative in paths:
        path = repository_file(repo, relative, "local patch input")
        size, digest = hash_file(path)
        with path.open("rb") as stream:
            prefix = stream.read(PREFIX_BYTES)
        items.append(
            make_item(
                "repository/{0}".format(relative),
                size,
                digest,
                "repository-commit:{0}".format(head),
                "regular",
                prefix,
            )
        )
    resolve_items(items, license_map)
    return items


def git_head(repo):
    try:
        completed = subprocess.run(
            ["git", "-c", "safe.directory={0}".format(repo), "rev-parse", "HEAD"],
            cwd=str(repo),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise InventoryError("cannot resolve repository HEAD: {0}".format(error))
    head = completed.stdout.decode("ascii").strip()
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
    if not isinstance(args.container_image, str) or "@sha256:" not in args.container_image:
        raise InventoryError("container image must be digest pinned")
    return {
        "container_image": args.container_image,
        "github_head_sha": head,
        "github_repository": args.github_repository,
        "github_run_attempt": args.github_run_attempt,
        "github_run_id": args.github_run_id,
    }


def write_capture(output_dir, items, binding, lock_sha, series_sha):
    if output_dir.exists() or output_dir.is_symlink():
        raise InventoryError("output directory already exists")
    output_dir.mkdir(mode=0o700)
    ordered = sorted(items, key=lambda item: item["path"])
    if len({item["path"] for item in ordered}) != len(ordered):
        raise InventoryError("inventory contains duplicate paths")
    unresolved = []
    raw_digest = hashlib.sha256()
    inventory_path = output_dir / "license-inventory.jsonl.gz"
    with inventory_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for item in ordered:
                reason = item.pop("_reason", None)
                if set(item) != REQUIRED_ITEM_KEYS:
                    raise InventoryError("inventory item has an invalid schema")
                line = canonical_json(item) + b"\n"
                raw_digest.update(line)
                compressed.write(line)
                if item["review_status"] != "verified":
                    unresolved.append({"path": item["path"], "reason": reason or "unresolved"})
    inventory_size, inventory_sha = hash_file(inventory_path)
    counts = {}
    for item in ordered:
        key = item["review_status"]
        counts[key] = counts.get(key, 0) + 1
    summary = {
        "binding": binding,
        "complete": not unresolved,
        "credit_eligible": False,
        "inventory": {
            "compressed_sha256": inventory_sha,
            "compressed_size": inventory_size,
            "item_count": len(ordered),
            "path": inventory_path.name,
            "uncompressed_sha256": raw_digest.hexdigest(),
        },
        "review_counts": counts,
        "schema_version": SCHEMA_VERSION,
        "source_lock_sha256": lock_sha,
        "unresolved_count": len(unresolved),
        "unresolved_sample": unresolved[:200],
        "patch_series_sha256": series_sha,
    }
    summary_path = output_dir / "license-inventory-summary.json"
    summary_path.write_bytes(canonical_json(summary) + b"\n")
    _, summary_sha = hash_file(summary_path)
    checksums = "{0}  {1}\n{2}  {3}\n".format(
        inventory_sha, inventory_path.name, summary_sha, summary_path.name
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="ascii")
    return summary


def verify_capture(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise InventoryError("capture directory is missing or symlinked")
    summary = read_json(directory / "license-inventory-summary.json")
    if summary.get("schema_version") != SCHEMA_VERSION or summary.get("credit_eligible") is not False:
        raise InventoryError("capture summary schema or credit policy changed")
    inventory = summary.get("inventory")
    if not isinstance(inventory, dict):
        raise InventoryError("capture summary inventory is missing")
    path = repository_file(directory, inventory.get("path"), "captured inventory")
    size, digest = hash_file(path)
    if size != inventory.get("compressed_size") or digest != inventory.get("compressed_sha256"):
        raise InventoryError("compressed inventory digest or size mismatch")
    raw_digest = hashlib.sha256()
    count = 0
    previous = None
    unresolved = 0
    try:
        with gzip.open(str(path), "rb") as stream:
            for line in stream:
                if not line.endswith(b"\n"):
                    raise InventoryError("inventory line is not newline terminated")
                raw_digest.update(line)
                try:
                    item = json.loads(line.decode("ascii"), object_pairs_hook=reject_duplicates)
                except (UnicodeError, ValueError) as error:
                    raise InventoryError("invalid inventory JSON: {0}".format(error))
                if not isinstance(item, dict) or set(item) != REQUIRED_ITEM_KEYS:
                    raise InventoryError("inventory item schema changed")
                if canonical_json(item) + b"\n" != line:
                    raise InventoryError("inventory JSON is not canonical")
                path_text = safe_relative(item["path"], "inventory item path")
                if previous is not None and path_text <= previous:
                    raise InventoryError("inventory paths are duplicate or unsorted")
                previous = path_text
                if not SHA256.fullmatch(item.get("sha256", "")):
                    raise InventoryError("inventory item SHA-256 is malformed")
                if item.get("review_status") != "verified":
                    unresolved += 1
                count += 1
    except (OSError, EOFError) as error:
        raise InventoryError("cannot read compressed inventory: {0}".format(error))
    if count != inventory.get("item_count") or raw_digest.hexdigest() != inventory.get(
        "uncompressed_sha256"
    ):
        raise InventoryError("inventory count or uncompressed digest mismatch")
    if unresolved != summary.get("unresolved_count"):
        raise InventoryError("unresolved inventory count mismatch")
    if summary.get("complete") is not (unresolved == 0):
        raise InventoryError("capture completeness contradicts unresolved items")
    return summary


def check_repository(repo):
    lock_path = repository_file(repo, SOURCE_LOCK.as_posix(), "source lock")
    series_path = repository_file(repo, SERIES.as_posix(), "patch series")
    workflow = repository_file(repo, WORKFLOW.as_posix(), "source evidence workflow")
    lock = read_json(lock_path)
    series = read_json(series_path)
    if lock.get("schema_version") != 1 or series.get("schema_version") != 1:
        raise InventoryError("source lock or patch series schema changed")
    inventory = lock.get("licenses", {}).get("inventory")
    if not isinstance(inventory, dict) or inventory.get("required") is not True:
        raise InventoryError("source lock no longer requires a license inventory")
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
    except ImportError as error:
        raise InventoryError("cannot import source-lock verifier: {0}".format(error))
    cache_root = args.cache_root.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    try:
        srpm = source_lock.acquire_source(lock, cache_root, timeout=300.0)
    except Exception as error:
        raise InventoryError("locked SRPM acquisition failed: {0}".format(error))
    with tempfile.TemporaryDirectory(prefix="rk001-license-") as temporary:
        extracted = Path(temporary) / "srpm"
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
        local_items = repository_patch_items(repo, binding["github_head_sha"], license_map)
        summary = write_capture(
            args.output_dir.resolve(),
            linux_items + srpm_items + local_items,
            binding,
            lock_sha,
            series_sha,
        )
    verify_capture(args.output_dir.resolve())
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
            summary = verify_capture(args.verify_capture.resolve())
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
