#!/usr/bin/env python3
"""Focused mutations for the locked native Rust host input closure."""

from __future__ import print_function

import ast
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import native_rust_host_audit as host_audit  # noqa: E402


class NativeRustHostAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = self.temporary.name
        self.manifest_relative = "host-kernel/kbuild/stage-manifest.json"
        with open(os.path.join(REPO_ROOT, self.manifest_relative), "r", encoding="utf-8") as stream:
            manifest = json.load(stream)
        self.original_manifest = manifest
        paths = {self.manifest_relative, "host-kernel/kbuild/Kbuild.in"}
        paths.update(item["repository_path"] for item in manifest["inputs"])
        paths.update(item["source"]["repository_path"] for item in manifest["modules"])
        for relative in paths:
            source = os.path.join(REPO_ROOT, *relative.split("/"))
            target = os.path.join(self.repo, *relative.split("/"))
            parent = os.path.dirname(target)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            shutil.copy2(source, target)
        self.manifest = os.path.join(self.repo, *self.manifest_relative.split("/"))
        self.old_root = host_audit.ROOT
        self.old_manifest = host_audit.MANIFEST
        host_audit.ROOT = self.repo
        host_audit.MANIFEST = self.manifest

    def tearDown(self):
        host_audit.ROOT = self.old_root
        host_audit.MANIFEST = self.old_manifest
        self.temporary.cleanup()

    def load_manifest(self):
        with open(self.manifest, "r", encoding="utf-8") as stream:
            return json.load(stream)

    def write_manifest(self, value):
        with open(self.manifest, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")

    def test_integrated_repository_closure_passes(self):
        self.assertEqual(0, host_audit.main())

    def test_master_omission_and_digest_drift_fail_closed(self):
        value = self.load_manifest()
        value["inputs"] = [
            item for item in value["inputs"] if item.get("destination") != "ikc_master.rs"
        ]
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "IKC master"):
            host_audit.main()

        value = copy.deepcopy(self.original_manifest)
        master = next(
            item for item in value["inputs"]
            if item.get("destination") == "ikc_master.rs"
        )
        master["sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "digest drift"):
            host_audit.main()

    def test_page_support_omission_and_digest_drift_fail_closed(self):
        for destination in ("page_allocator.rs", "page_owner_registry.rs"):
            with self.subTest(destination=destination):
                value = copy.deepcopy(self.original_manifest)
                value["inputs"] = [
                    item for item in value["inputs"]
                    if item.get("destination") != destination
                ]
                self.write_manifest(value)
                with self.assertRaisesRegex(SystemExit, "support input closure"):
                    host_audit.main()

                value = copy.deepcopy(self.original_manifest)
                item = next(
                    entry for entry in value["inputs"]
                    if entry.get("destination") == destination
                )
                item["sha256"] = "0" * 64
                self.write_manifest(value)
                with self.assertRaisesRegex(SystemExit, "digest drift"):
                    host_audit.main()

    def test_checker_and_tests_parse_with_python_3_6_grammar(self):
        paths = (host_audit.__file__, os.path.abspath(__file__))
        for path in paths:
            with open(path, "r", encoding="utf-8") as stream:
                source = stream.read()
            try:
                ast.parse(source, filename=path, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=path, feature_version=6)


if __name__ == "__main__":
    unittest.main()
