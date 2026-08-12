#!/usr/bin/env python3
"""Fail closed unless native Rust host-module staging has only locked Rust inputs."""

from __future__ import print_function

import hashlib
import json
import os
import re
import stat
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "host-kernel", "kbuild", "stage-manifest.json")
FORBIDDEN_SUFFIXES = (".c", ".cc", ".cpp", ".o", ".a", ".so")
FORBIDDEN_RUST_PATTERNS = (
    r'extern\s+"C"',
    r'include_bytes!\s*\(',
    r'include!\s*\(',
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8") as stream:
        return stream.read()


def die(message):
    raise SystemExit("native Rust host audit failed: " + message)


def regular_repo_file(relative):
    if not relative or relative.startswith("/") or ".." in relative.split("/"):
        die("unsafe repository path: {0}".format(relative))
    path = os.path.join(ROOT, relative)
    try:
        st = os.lstat(path)
    except OSError as error:
        die("missing locked file {0}: {1}".format(relative, error))
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        die("locked input is not a regular file: {0}".format(relative))
    if os.path.realpath(path) != path:
        die("locked input traverses a symlink: {0}".format(relative))
    return path


def main():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    contract = manifest["build_contract"]
    if contract.get("project_c_link_objects") != 0:
        die("project_c_link_objects must be zero")
    if contract.get("manual_rustc_invocation_forbidden") is not True:
        die("manual rustc invocation must be forbidden")
    if contract.get("prebuilt_project_objects_forbidden") is not True:
        die("prebuilt project objects must be forbidden")

    destinations = set()
    modules = manifest.get("modules", [])
    if len(modules) != 3:
        die("expected exactly three native host modules")
    for module in modules:
        source = module["source"]
        relative = source["repository_path"]
        if not relative.endswith(".rs"):
            die("non-Rust crate root: {0}".format(relative))
        if any(relative.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            die("forbidden project input: {0}".format(relative))
        path = regular_repo_file(relative)
        if sha256(path) != source["sha256"]:
            die("crate root digest drift: {0}".format(relative))
        text = read_text(path)
        if "module!" not in text or "impl kernel::Module" not in text:
            die("missing Rust-for-Linux module entry point: {0}".format(relative))
        for pattern in FORBIDDEN_RUST_PATTERNS:
            if re.search(pattern, text):
                die("unreviewed implementation escape hatch in {0}: {1}".format(relative, pattern))
        destination = source["destination"]
        if destination in destinations:
            die("duplicate staged destination: {0}".format(destination))
        destinations.add(destination)

    support = [
        item for item in manifest.get("inputs", [])
        if item.get("kind") in (
            "shared_rust_abi", "rust_module", "rust_support_module"
        )
    ]
    if [item.get("destination") for item in support] != [
        "abi/x86_64.rs",
        "ikc_queue.rs",
        "os_registry.rs",
        "ikc_master.rs",
        "page_allocator.rs",
        "page_owner_registry.rs",
    ]:
        die(
            "Rust support input closure differs from the locked ABI, queue, "
            "OS registry, IKC master, page allocator, and page-owner registry"
        )
    for item in support:
        relative = item.get("repository_path")
        if not isinstance(relative, str) or not relative.endswith(".rs"):
            die("non-Rust support input: {0}".format(relative))
        path = regular_repo_file(relative)
        if sha256(path) != item.get("sha256"):
            die("support input digest drift: {0}".format(relative))
        text = read_text(path)
        for pattern in FORBIDDEN_RUST_PATTERNS:
            if re.search(pattern, text):
                die("unreviewed implementation escape hatch in {0}: {1}".format(relative, pattern))
        destination = item.get("destination")
        if destination in destinations:
            die("duplicate staged destination: {0}".format(destination))
        destinations.add(destination)

    kbuild = regular_repo_file("host-kernel/kbuild/Kbuild.in")
    ktext = read_text(kbuild).lower()
    for token in ("rustc", "$(shell", ".c ", ".o ", ".a ", ".so "):
        if token in ktext:
            die("forbidden Kbuild construct: {0}".format(token))

    print("native-rust-host-audit: PASS modules=3 project_c_link_objects=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
