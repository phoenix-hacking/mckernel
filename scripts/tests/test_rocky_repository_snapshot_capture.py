#!/usr/bin/env python3

import ast
import copy
import io
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "rocky_repository_snapshot_capture.py"
SPEC = importlib.util.spec_from_file_location("snapshot_capture", str(SCRIPT))
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def deterministic_gzip(data):
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as stream:
        stream.write(data)
    return output.getvalue()


def repomd_xml(objects):
    rows = []
    for row in objects:
        open_fields = ""
        if row.get("open_sha256") is not None:
            open_fields = (
                "<open-checksum type=\"sha256\">{}</open-checksum>"
                "<open-size>{}</open-size>"
            ).format(row["open_sha256"], row["open_size"])
        rows.append(
            (
                "<data type=\"{}\">"
                "<checksum type=\"sha256\">{}</checksum>"
                "{}"
                "<location href=\"{}\"/>"
                "<timestamp>1</timestamp>"
                "<size>{}</size>"
                "</data>"
            ).format(
                row["type"],
                row["sha256"],
                open_fields,
                row["href"],
                row["size"],
            )
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<repomd xmlns=\"http://linux.duke.edu/metadata/repo\">"
        "<revision>10.2</revision>{}</repomd>"
    ).format("".join(rows)).encode("utf-8")


def object_row(data_type, href, compressed, opened=None):
    if opened is None:
        return {
            "href": href,
            "sha256": sha256(compressed),
            "size": len(compressed),
            "type": data_type,
        }
    return {
        "href": href,
        "open_sha256": sha256(opened),
        "open_size": len(opened),
        "sha256": sha256(compressed),
        "size": len(compressed),
        "type": data_type,
    }


class ContractTests(unittest.TestCase):
    def test_repository_contract_is_valid_and_no_credit(self):
        contract, records = snapshot.check_repository_inputs(REPO)
        self.assertEqual(contract["claims"], snapshot.FALSE_CLAIMS)
        self.assertTrue(all(value is False for value in contract["claims"].values()))
        self.assertEqual(len(records), 4)

    def test_any_true_claim_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["claims"]["tracker_credit"] = True
        with self.assertRaisesRegex(snapshot.SnapshotError, "claims"):
            snapshot.validate_contract(changed)

    def test_release_key_identity_change_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["release_key"]["fingerprint"] = "0" * 40
        with self.assertRaisesRegex(snapshot.SnapshotError, "fingerprint"):
            snapshot.validate_contract(changed)

    def test_repository_order_change_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["repositories"].reverse()
        with self.assertRaisesRegex(snapshot.SnapshotError, "repository set"):
            snapshot.validate_contract(changed)

    def test_checker_and_tests_remain_python_3_6_compatible(self):
        forbidden = (
            "from __future__ import " + "annotations",
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "missing_" + "ok=",
            "gzip.Bad" + "GzipFile",
        )
        for relative in (
            snapshot.CHECKER_PATH,
            snapshot.TEST_PATH,
        ):
            path = REPO / relative
            source = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                try:
                    tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
                except TypeError:
                    tree = ast.parse(source, filename=str(path), feature_version=6)
            else:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for fragment in forbidden:
                self.assertNotIn(fragment, source)

    def test_workflow_is_manual_only_and_shell_blocks_parse(self):
        import yaml

        workflow_path = REPO / snapshot.WORKFLOW_PATH
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(workflow_text)
        self.assertIsInstance(workflow, dict)
        trigger = workflow.get("on", workflow.get(True))
        self.assertEqual(set(trigger), {"workflow_dispatch"})
        self.assertIn(
            "bzip2 git-core gnupg2 gzip python3 python3-pyyaml tar xz",
            workflow_text.replace("\\\n            ", ""),
        )
        self.assertIn("python3 -c 'import yaml'", workflow_text)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if script:
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=script.encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr.decode("utf-8", "replace"),
                    )


class CallerPathTests(unittest.TestCase):
    def run_main(self, arguments):
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            result = snapshot.main(["--repo", str(REPO)] + arguments)
        return result, stderr.getvalue()

    def test_direct_symlink_output_fails_without_outside_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            output = root / "output"
            output.symlink_to(outside, target_is_directory=True)
            result, error = self.run_main(["--capture", "--output-dir", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("must not be a symlink", error)
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_output_parent_fails_without_outside_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            alias = root / "alias"
            alias.symlink_to(outside, target_is_directory=True)
            output = alias / "payload"
            result, error = self.run_main(["--capture", "--output-dir", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("symlink component", error)
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_diagnostics_parent_fails_without_outside_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            alias = root / "alias"
            alias.symlink_to(outside, target_is_directory=True)
            output = root / "payload"
            diagnostics = alias / "diagnostics"
            result, error = self.run_main(
                [
                    "--capture",
                    "--output-dir",
                    str(output),
                    "--diagnostics-dir",
                    str(diagnostics),
                ]
            )
            self.assertEqual(result, 1)
            self.assertIn("symlink component", error)
            self.assertFalse(output.exists())
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_artifact_fails_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            target = outside / "snapshot.tar"
            target.write_bytes(b"not-a-snapshot\n")
            artifact = root / "snapshot.tar"
            artifact.symlink_to(target)
            result, error = self.run_main(["--verify-artifact", str(artifact)])
            self.assertEqual(result, 1)
            self.assertIn("must not be a symlink", error)
            self.assertEqual(target.read_bytes(), b"not-a-snapshot\n")
            self.assertEqual(sorted(path.name for path in outside.iterdir()), ["snapshot.tar"])

    def test_output_and_diagnostics_must_not_overlap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = (
                (root / "same", root / "same"),
                (root / "payload", root / "payload" / "diagnostics"),
                (root / "diagnostics" / "payload", root / "diagnostics"),
            )
            for output, diagnostics in cases:
                result, error = self.run_main(
                    [
                        "--capture",
                        "--output-dir",
                        str(output),
                        "--diagnostics-dir",
                        str(diagnostics),
                    ]
                )
                self.assertEqual(result, 1)
                self.assertIn("must not overlap", error)
                self.assertFalse(output.exists())


class RepomdTests(unittest.TestCase):
    def test_parses_every_supported_compression_binding(self):
        opened = b"<metadata>bounded</metadata>\n"
        import bz2
        import lzma

        rows = [
            object_row("primary", "repodata/primary.xml.gz", gzip.compress(opened), opened),
            object_row("filelists", "repodata/filelists.xml.bz2", bz2.compress(opened), opened),
            object_row("other", "repodata/other.xml.xz", lzma.compress(opened), opened),
            object_row("group", "repodata/groups.xml", opened),
        ]
        parsed = snapshot.parse_repomd(repomd_xml(rows), 64)
        self.assertEqual(
            [row["compression"] for row in parsed["objects"]],
            ["gzip", "bzip2", "xz", "none"],
        )

    def test_path_traversal_fails_closed(self):
        data = b"x"
        row = object_row("primary", "repodata/../primary.xml", data)
        with self.assertRaisesRegex(snapshot.SnapshotError, "normalized relative path"):
            snapshot.parse_repomd(repomd_xml([row]), 64)

    def test_encoded_url_traversal_and_duplicate_semantic_children_fail_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        with self.assertRaisesRegex(snapshot.SnapshotError, "HTTPS policy"):
            snapshot.validate_https_url(
                "https://download.rockylinux.org/pub/rocky/%2e%2e/escape",
                contract["network"]["allowed_hosts"],
                "fixture URL",
            )
        handler = snapshot.BoundedRedirectHandler(
            contract["network"]["allowed_hosts"],
            2,
            required_prefix="https://download.rockylinux.org/pub/rocky/10.2/BaseOS/",
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "base URL"):
            handler.redirect_request(
                None,
                None,
                302,
                "Found",
                {},
                "https://download.rockylinux.org/pub/rocky/10.2/AppStream/escape",
            )

        data = b"primary"
        row = object_row("primary", "repodata/primary.xml", data)
        xml = repomd_xml([row]).replace(
            b"<checksum type=\"sha256\">",
            b"<checksum type=\"sha256\">",
            1,
        ).replace(
            b"</checksum>",
            b"</checksum><checksum type=\"sha256\">" + sha256(data).encode("ascii") + b"</checksum>",
            1,
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "multiplicity"):
            snapshot.parse_repomd(xml, 64)

        xml = repomd_xml([row]).replace(
            b"<location href=\"repodata/primary.xml\"/>",
            b"<location href=\"repodata/primary.xml\"/>"
            b"<location href=\"repodata/other.xml\"/>",
            1,
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "multiplicity"):
            snapshot.parse_repomd(xml, 64)

    def test_duplicate_data_type_fails_closed(self):
        data = b"x"
        rows = [
            object_row("primary", "repodata/a.xml", data),
            object_row("primary", "repodata/b.xml", data),
        ]
        with self.assertRaisesRegex(snapshot.SnapshotError, "duplicated"):
            snapshot.parse_repomd(repomd_xml(rows), 64)

    def test_compressed_object_without_open_binding_fails_closed(self):
        data = gzip.compress(b"x")
        row = object_row("primary", "repodata/primary.xml.gz", data)
        with self.assertRaisesRegex(snapshot.SnapshotError, "open hash"):
            snapshot.parse_repomd(repomd_xml([row]), 64)

    def test_unsupported_compression_fails_closed(self):
        data = b"zchunk"
        row = object_row("primary", "repodata/primary.xml.zck", data, b"x")
        with self.assertRaisesRegex(snapshot.SnapshotError, "unsupported"):
            snapshot.parse_repomd(repomd_xml([row]), 64)

    def test_compressed_and_open_hashes_are_both_verified(self):
        opened = b"<metadata>verified</metadata>\n"
        compressed = gzip.compress(opened)
        row = snapshot.parse_repomd(
            repomd_xml(
                [object_row("primary", "repodata/primary.xml.gz", compressed, opened)]
            ),
            64,
        )["objects"][0]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            path.write_bytes(compressed)
            result = snapshot.verify_metadata_object(path, row, 1024, [0, 4096])
            self.assertTrue(result["open_checksum_declared"])
            self.assertEqual(result["verified_open_sha256"], sha256(opened))
            path.write_bytes(compressed + b"tamper")
            with self.assertRaisesRegex(snapshot.SnapshotError, "compressed bytes"):
                snapshot.verify_metadata_object(path, row, 1024, [0, 4096])

    def test_open_byte_limit_is_enforced(self):
        opened = b"x" * 1025
        compressed = gzip.compress(opened)
        row = snapshot.parse_repomd(
            repomd_xml(
                [object_row("primary", "repodata/primary.xml.gz", compressed, opened)]
            ),
            64,
        )["objects"][0]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            path.write_bytes(compressed)
            with self.assertRaisesRegex(snapshot.SnapshotError, "byte limit"):
                snapshot.verify_metadata_object(path, row, 1024, [0, 4096])


class DeterministicArtifactTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.input_records = snapshot.check_repository_inputs(REPO)
        self.contract = copy.deepcopy(self.contract)
        self.key = b"synthetic-key-for-offline-unit-test\n"
        self.signature = b"synthetic-signature\n"
        self.opened = b"<metadata>unit-test</metadata>\n"
        self.compressed = deterministic_gzip(self.opened)
        self.object_href = "repodata/unit-primary.xml.gz"
        self.repomd = repomd_xml(
            [object_row("primary", self.object_href, self.compressed, self.opened)]
        )
        self.contract["release_key"]["size"] = len(self.key)
        self.contract["release_key"]["sha256"] = sha256(self.key)
        self.signature_record = {
            "hash_algorithm_id": 8,
            "primary_fingerprint": snapshot.RELEASE_FINGERPRINT,
            "public_key_algorithm_id": 1,
            "signature_fingerprint": snapshot.RELEASE_FINGERPRINT,
            "signature_timestamp": 1,
            "status": "verified",
        }

    def fake_download(self, url, destination, maximum, contract, required_prefix=None):
        if url == snapshot.RELEASE_KEY_URL:
            data = self.key
        elif url.endswith("repodata/repomd.xml.asc"):
            data = self.signature
        elif url.endswith("repodata/repomd.xml"):
            data = self.repomd
        elif url.endswith(self.object_href):
            data = self.compressed
        else:
            raise AssertionError("unexpected URL: {}".format(url))
        if len(data) > maximum:
            raise snapshot.SnapshotError("synthetic download exceeds limit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return {
            "final_url": url,
            "redirect_count": 0,
            "sha256": sha256(data),
            "size": len(data),
            "url": url,
        }

    def test_capture_is_deterministic_and_offline_verifiable(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output_one = temporary / "one"
            output_two = temporary / "two"
            diagnostics = temporary / "diagnostics"
            patches = (
                mock.patch.object(snapshot, "download_to_path", self.fake_download),
                mock.patch.object(
                    snapshot,
                    "verify_key_fingerprint",
                    side_effect=lambda path, fingerprint: fingerprint,
                ),
                mock.patch.object(
                    snapshot,
                    "verify_detached_signature",
                    return_value=self.signature_record,
                ),
            )
            with patches[0], patches[1], patches[2]:
                first = snapshot.capture_snapshot(
                    REPO,
                    output_one,
                    diagnostics,
                    self.contract,
                    self.input_records,
                )
                second = snapshot.capture_snapshot(
                    REPO,
                    output_two,
                    None,
                    self.contract,
                    self.input_records,
                )
                verified = snapshot.verify_artifact(
                    REPO,
                    output_one / "snapshot.tar",
                    self.contract,
                    self.input_records,
                )
            self.assertEqual(first["snapshot_identity"], second["snapshot_identity"])
            self.assertEqual(
                (output_one / "snapshot.tar").read_bytes(),
                (output_two / "snapshot.tar").read_bytes(),
            )
            self.assertEqual(verified, first)
            report = json.loads((diagnostics / "drift-report.json").read_text())
            self.assertEqual(report["claims"], snapshot.diagnostics_claims())
            self.assertTrue(all(value is False for value in report["claims"].values()))

    def test_tar_metadata_is_canonical(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            tree = temporary / "tree"
            tree.mkdir()
            (tree / "b").write_bytes(b"b")
            (tree / "a").write_bytes(b"a")
            artifact = temporary / "snapshot.tar"
            snapshot.create_deterministic_tar(tree, artifact)
            with tarfile.open(str(artifact), "r:") as archive:
                members = archive.getmembers()
            self.assertEqual([member.name for member in members], ["a", "b"])
            for member in members:
                self.assertEqual(
                    (member.mode, member.uid, member.gid, member.mtime),
                    (0o644, 0, 0, 0),
                )


if __name__ == "__main__":
    unittest.main()
