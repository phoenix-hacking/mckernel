#!/usr/bin/env python3
"""Fail-closed tests for RK-001 source evidence capture."""

import ast
import base64
import copy
import contextlib
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_source_evidence as evidence  # noqa: E402


class FakeResponse:
    def __init__(
        self,
        data: bytes,
        url: str,
        status: int = 200,
        content_length: str = "",
        content_encoding: str = "",
        duplicate_length: bool = False,
    ) -> None:
        self.stream = io.BytesIO(data)
        self.url = url
        self.status = status
        self.headers = Message()
        self.headers.add_header(
            "Content-Length", content_length if content_length else str(len(data))
        )
        if duplicate_length:
            self.headers.add_header("Content-Length", str(len(data)))
        if content_encoding:
            self.headers.add_header("Content-Encoding", content_encoding)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def open(self, request, timeout):
        del request, timeout
        return self.response


class RepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock, cls.series, cls.blockers = evidence.check_repository(REPO_ROOT)

    def test_current_contract_is_valid_and_keeps_rk001_blocked(self) -> None:
        self.assertEqual(len(self.blockers), 1)
        self.assertFalse(self.lock["gate"]["credit_eligible"])
        self.assertFalse(self.lock["licenses"]["inventory"]["complete"])
        self.assertEqual(
            {item.split(":", 1)[0] for item in self.blockers},
            {"license_inventory"},
        )

    def test_workflow_uses_exact_rocky_10_2_amd64_manifest(self) -> None:
        workflow = evidence.validate_workflow_contract(REPO_ROOT).decode("utf-8")
        self.assertEqual(workflow.count("image: " + evidence.CONTAINER_IMAGE), 2)
        self.assertEqual(
            evidence.CONTAINER_MANIFEST_DIGEST,
            "sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176",
        )
        self.assertNotIn("image: rockylinux/rockylinux:10.2\n", workflow)
        install_step = workflow.split(
            "- name: Install required verification tools", 1
        )[1].split("- name: Check out the exact candidate commit", 1)[0]
        self.assertIn("git-core gnupg2 gzip python3 rpm", install_step)
        self.assertNotRegex(install_step, r"\bcoreutils\b")
        verify_step = workflow.split(
            "- name: Verify capture contract without claiming gate credit", 1
        )[1].split("- name: Capture exact RK-001 replay evidence", 1)[0]
        self.assertIn('git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD', verify_step)
        self.assertNotIn("safe.directory=*", workflow)

    def test_license_capture_is_an_independent_exact_head_fail_closed_job(self) -> None:
        workflow = evidence.validate_workflow_contract(REPO_ROOT).decode("utf-8")
        _, jobs = workflow.split("\n  capture:\n", 1)
        source_job, license_job = jobs.split("\n  license-inventory:\n", 1)
        self.assertNotIn("rocky_kernel_license_inventory.py", source_job)
        self.assertNotRegex(license_job, r"(?m)^    needs\s*:")
        self.assertIn('ref: ${{ env.EXPECTED_HEAD_SHA }}', license_job)
        self.assertIn('--github-head-sha "$EXPECTED_HEAD_SHA"', license_job)
        self.assertIn('--github-run-id "$GITHUB_RUN_ID"', license_job)
        self.assertIn('--github-run-attempt "$GITHUB_RUN_ATTEMPT"', license_job)
        self.assertIn('--github-repository "$GITHUB_REPOSITORY"', license_job)
        self.assertIn('--container-image "$RK001_CONTAINER_IMAGE"', license_job)
        self.assertIn("rocky_kernel_source_evidence.py", license_job)
        self.assertIn("rocky_kernel_license_inventory.py", license_job)
        self.assertIn("--verify-capture", license_job)
        self.assertIn("sha256sum --check --strict SHA256SUMS", license_job)
        self.assertIn("retention-days: 30", license_job)

    def test_workflow_contract_rejects_top_level_and_trigger_bypasses(self) -> None:
        original = (REPO_ROOT / evidence.WORKFLOW_PATH).read_text(encoding="utf-8")
        on_start = original.index("on:\n")
        permission_start = original.index("\npermissions:\n")
        before_on = original[:on_start]
        after_on = original[permission_start:]
        pull_marker = "  pull_request:\n"
        pull_prefix, pull_trigger = original.split(pull_marker, 1)
        variants = (
            original
            + '\n"env": {EXPECTED_HEAD_SHA: "${{ github.sha }}"}\n',
            original + '\n"jobs": {}\n',
            original + '\n"permissions": {contents: write}\n',
            original + "\nenv: {}\n",
            original + "\n!!str env: {}\n",
            original + "\n*environment_alias: {}\n",
            original + "\n<<: *top_level_defaults\n",
            original.replace(
                "name: Rocky 10.2 kernel source evidence",
                "name: Mutable source evidence\n"
                "# name: Rocky 10.2 kernel source evidence",
                1,
            ),
            before_on + "on:\n  workflow_dispatch:\n" + after_on,
            original.replace(
                "    branches: [codex/rocky-rust-validation]",
                "    branches: [development]\n"
                "    # branches: [codex/rocky-rust-validation]",
                1,
            ),
            original.replace("    branches: [development]", "    branches: [main]", 1),
            original.replace(
                "      - host-kernel/rocky/source-lock.json",
                "      - host-kernel/rocky/source-lock-drift.json",
                1,
            ),
            pull_prefix
            + pull_marker
            + pull_trigger.replace(
                "      - scripts/rocky_kernel_license_inventory.py",
                "      - scripts/rocky_kernel_license_inventory_drift.py",
                1,
            ),
        )
        self.assertNotIn(original, variants)
        self.assertEqual(len(variants), len(set(variants)))
        for workflow in variants:
            with self.subTest(fragment=hashlib.sha256(workflow.encode("utf-8")).hexdigest()):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    path = root / evidence.WORKFLOW_PATH
                    path.parent.mkdir(parents=True)
                    path.write_text(workflow, encoding="utf-8")
                    with self.assertRaises(evidence.EvidenceError):
                        evidence.validate_workflow_contract(root)

    def test_workflow_contract_rejects_conditional_or_comment_attested_bypasses(self) -> None:
        original = (REPO_ROOT / evidence.WORKFLOW_PATH).read_text(encoding="utf-8")
        license_marker = "\n  license-inventory:\n"
        prefix, license_job = original.split(license_marker, 1)
        pinned_image = "      image: " + evidence.CONTAINER_IMAGE
        checkout_action = (
            "        uses: actions/checkout@"
            "11d5960a326750d5838078e36cf38b85af677262 # v4"
        )
        upload_action = (
            "        uses: actions/upload-artifact@"
            "ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2"
        )
        capture_step = "      - name: Capture exhaustive source and license inventory\n"
        variants = (
            original.replace(
                "  license-inventory:\n",
                "  license-inventory:\n    needs: capture\n",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                "    name: Exact-head exhaustive source and license inventory\n",
                "    name: Exact-head exhaustive source and license inventory\n"
                "    if: false\n",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                "    name: Exact-head exhaustive source and license inventory\n",
                "    name: Exact-head exhaustive source and license inventory\n"
                '    "if": false\n',
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                "    name: Exact-head exhaustive source and license inventory\n",
                "    name: Exact-head exhaustive source and license inventory\n"
                "    env:\n"
                "      RK001_CONTAINER_IMAGE: rockylinux/rockylinux:10.2\n",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                capture_step,
                capture_step + "        if: false\n",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                capture_step,
                capture_step + "        continue-on-error: true\n",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                "          LICENSE_EVIDENCE_DIR: "
                "${{ runner.temp }}/rk001-license-inventory\n",
                "          LICENSE_EVIDENCE_DIR: "
                "${{ runner.temp }}/rk001-license-inventory\n"
                "          EXPECTED_HEAD_SHA: ${{ github.sha }}\n",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                pinned_image,
                "      image: rockylinux/rockylinux:10.2\n"
                "      # image: " + evidence.CONTAINER_IMAGE,
                1,
            ),
            original.replace(
                "  RK001_CONTAINER_IMAGE: " + evidence.CONTAINER_IMAGE,
                "  RK001_CONTAINER_IMAGE: rockylinux/rockylinux:10.2\n"
                "  # RK001_CONTAINER_IMAGE: " + evidence.CONTAINER_IMAGE,
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                checkout_action,
                "        uses: actions/checkout@v4 # "
                "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                upload_action,
                "        uses: actions/upload-artifact@v4 # "
                "actions/upload-artifact@"
                "ea165f8d65b6e75b540449e92b4886f43607fa02",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                "          ref: ${{ env.EXPECTED_HEAD_SHA }}",
                "          ref: ${{ github.sha }}\n"
                "          # ref: ${{ env.EXPECTED_HEAD_SHA }}",
                1,
            ),
            prefix
            + license_marker
            + license_job.replace(
                '--github-head-sha "$EXPECTED_HEAD_SHA"',
                '--github-head-sha "$GITHUB_SHA"',
                1,
            ).replace(
                '            --container-image "$RK001_CONTAINER_IMAGE"\n',
                '            --container-image "$RK001_CONTAINER_IMAGE"\n'
                '          # --github-head-sha "$EXPECTED_HEAD_SHA"\n',
                1,
            ),
            original.replace("--verify-capture", "--verify", 1),
        )
        self.assertNotIn(original, variants)
        self.assertEqual(len(variants), len(set(variants)))
        for workflow in variants:
            with self.subTest(fragment=hashlib.sha256(workflow.encode("utf-8")).hexdigest()):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    path = root / evidence.WORKFLOW_PATH
                    path.parent.mkdir(parents=True)
                    path.write_text(workflow, encoding="utf-8")
                    with self.assertRaises(evidence.EvidenceError):
                        evidence.validate_workflow_contract(root)

    def test_runtime_package_capture_matches_the_minimal_rocky_image(self) -> None:
        source = (REPO_ROOT / evidence.CAPTURE_SCRIPT_PATH).read_text(
            encoding="utf-8"
        )
        self.assertIn('"coreutils-single"', source)
        self.assertIn('"git-core"', source)
        self.assertNotIn('            "coreutils",\n', source)
        self.assertIn('"safe.directory={}".format(repo.resolve())', source)

    def test_cli_check_succeeds_without_gate_claim(self) -> None:
        self.assertEqual(evidence.main(["--repo", str(REPO_ROOT), "--check"]), 0)

    def test_checker_and_tests_avoid_post_python_3_6_syntax_and_apis(self) -> None:
        forbidden_fragments = (
            "from __future__ import " + "annotations",
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "capture_" + "output=",
            "missing_" + "ok=",
        )
        forbidden_annotation_patterns = (
            r"\b(?:list|dict|set|tuple)\[[^\]]",
            r"\s\|\sNone\b",
        )
        for relative_path in (
            "scripts/rocky_kernel_source_evidence.py",
            "scripts/tests/test_rocky_kernel_source_evidence.py",
        ):
            path = REPO_ROOT / relative_path
            source = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                try:
                    tree = ast.parse(
                        source, filename=str(path), feature_version=(3, 6)
                    )
                except TypeError:
                    tree = ast.parse(source, filename=str(path), feature_version=6)
            else:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, source, relative_path)
            for pattern in forbidden_annotation_patterns:
                self.assertNotRegex(source, pattern, relative_path)

        python36 = shutil_which("python3.6")
        if python36:
            completed = subprocess.run(
                [
                    python36,
                    str(REPO_ROOT / evidence.CAPTURE_SCRIPT_PATH),
                    "--repo",
                    str(REPO_ROOT),
                    "--check",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )


class StrictInputTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected_at_every_depth(self) -> None:
        for payload in (
            b'{"a":1,"a":2}',
            b'{"outer":{"a":1,"a":2}}',
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(evidence.EvidenceError, "duplicate JSON"):
                    evidence.strict_json_bytes(payload, "fixture")

    def test_non_object_invalid_utf8_and_large_json_are_rejected(self) -> None:
        for payload in (b"[]", b"\xff", b"{" + b" " * evidence.MAX_JSON_BYTES + b"}"):
            with self.subTest(size=len(payload)):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.strict_json_bytes(payload, "fixture")

    def test_canonical_json_is_sorted_compact_finite_and_newline_terminated(self) -> None:
        self.assertEqual(
            evidence.canonical_json_bytes({"z": 1, "a": [True, None]}),
            b'{"a":[true,null],"z":1}\n',
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence.canonical_json_bytes({"bad": float("nan")})

    def test_run_identity_is_exact_and_container_bound(self) -> None:
        valid = evidence.validate_run_identity(
            "a" * 40,
            "123",
            "2",
            "phoenix-hacking/mckernel",
            evidence.CONTAINER_IMAGE,
        )
        self.assertEqual(valid["run_id"], 123)
        cases = (
            ("A" * 40, "123", "2", "phoenix-hacking/mckernel", evidence.CONTAINER_IMAGE),
            ("a" * 40, "0", "2", "phoenix-hacking/mckernel", evidence.CONTAINER_IMAGE),
            ("a" * 40, "123", "0", "phoenix-hacking/mckernel", evidence.CONTAINER_IMAGE),
            ("a" * 40, "123", "2", "mckernel", evidence.CONTAINER_IMAGE),
            ("a" * 40, "123", "2", "phoenix-hacking/mckernel", "rockylinux:10.2"),
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_run_identity(*case)

    def test_os_release_requires_exact_rocky_10_2_without_duplicates(self) -> None:
        self.assertEqual(
            evidence.parse_os_release(b'NAME="Rocky Linux"\nID="rocky"\nVERSION_ID="10.2"\n'),
            {"id": "rocky", "version_id": "10.2"},
        )
        for payload in (
            b"ID=rocky\nVERSION_ID=10.1\n",
            b"ID=rocky\nID=rocky\nVERSION_ID=10.2\n",
            b"ID=rocky\nBROKEN\nVERSION_ID=10.2\n",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_os_release(payload)


class DownloadTests(unittest.TestCase):
    URL = "https://download.rockylinux.org/pub/rocky/locked"

    def test_exact_download_records_no_redirect_and_publishes_verified_bytes(self) -> None:
        payload = b"locked source bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            result = evidence.download_exact(
                self.URL,
                target,
                digest,
                len(payload),
                len(payload),
                FakeOpener(FakeResponse(payload, self.URL)),
            )
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(result["redirect_count"], 0)
            self.assertEqual(result["final_url"], self.URL)
            self.assertEqual(result["sha256"], digest)
            self.assertEqual(target.stat().st_mode & 0o777, 0o400)

    def test_completed_mismatch_reports_full_identity_and_deletes_staged_bytes(self) -> None:
        payload = b"mutable source bytes"
        expected_digest = "0" * 64
        actual_digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "artifact"
            with self.assertRaises(evidence.EvidenceError) as caught:
                evidence.download_exact(
                    self.URL,
                    target,
                    expected_digest,
                    len(payload),
                    len(payload),
                    FakeOpener(FakeResponse(payload, self.URL)),
                )
            message = str(caught.exception)
            for fragment in (
                "url={!r}".format(self.URL),
                "locked_size={}".format(len(payload)),
                "declared_size={}".format(len(payload)),
                "actual_size={}".format(len(payload)),
                "locked_sha256={}".format(expected_digest),
                "actual_sha256={}".format(actual_digest),
            ):
                self.assertIn(fragment, message)
            self.assertFalse(target.exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_content_length_mismatch_reports_header_without_consuming_body(self) -> None:
        payload = b"locked source bytes"
        response = FakeResponse(payload, self.URL, content_length="1")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            with self.assertRaises(evidence.EvidenceError) as caught:
                evidence.download_exact(
                    self.URL,
                    target,
                    hashlib.sha256(payload).hexdigest(),
                    len(payload),
                    len(payload),
                    FakeOpener(response),
                )
            message = str(caught.exception)
            self.assertIn("url={!r}".format(self.URL), message)
            self.assertIn("locked_size={}".format(len(payload)), message)
            self.assertIn("declared_size=1", message)
            self.assertEqual(response.stream.tell(), 0)
            self.assertFalse(target.exists())

    def test_download_mismatch_host_drift_and_ambiguous_headers_fail_closed(self) -> None:
        payload = b"locked source bytes"
        digest = hashlib.sha256(payload).hexdigest()
        cases = (
            ("wrong-hash", self.URL, digest, len(payload), FakeResponse(payload, self.URL)),
            ("final-url", self.URL, digest, len(payload), FakeResponse(payload, self.URL + "/moved")),
            ("length", self.URL, digest, len(payload), FakeResponse(payload, self.URL, content_length="1")),
            ("encoding", self.URL, digest, len(payload), FakeResponse(payload, self.URL, content_encoding="gzip")),
            ("duplicate", self.URL, digest, len(payload), FakeResponse(payload, self.URL, duplicate_length=True)),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, url, expected_digest, expected_size, response in cases:
                with self.subTest(name=name):
                    target = root / name
                    if name == "wrong-hash":
                        expected_digest = "0" * 64
                    with self.assertRaises(evidence.EvidenceError):
                        evidence.download_exact(
                            url,
                            target,
                            expected_digest,
                            expected_size,
                            len(payload),
                            FakeOpener(response),
                        )
                    self.assertFalse(target.exists())

        for url in (
            "http://download.rockylinux.org/pub/rocky/locked",
            "https://evil.invalid/pub/rocky/locked",
            "https://download.rockylinux.org:443/pub/rocky/locked",
            "https://download.rockylinux.org/pub/rocky/locked?mutable=1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_locked_https_url(
                        url, "download.rockylinux.org", "fixture"
                    )

    def test_redirect_handler_rejects_even_same_host_redirects(self) -> None:
        handler = evidence.RejectRedirects()
        request = evidence.urllib.request.Request(self.URL)
        with self.assertRaisesRegex(evidence.EvidenceError, "redirect rejected"):
            handler.redirect_request(
                request,
                io.BytesIO(),
                302,
                "Found",
                {},
                self.URL + "/redirected",
            )


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock, _, _, _, _ = evidence.load_locked_inputs(REPO_ROOT)

    def repomd(self, duplicate_primary: bool = False) -> bytes:
        repository = self.lock["repository_snapshot"]
        primary = repository["primary_metadata"]
        row = """
          <data type="primary">
            <checksum type="sha256">{sha256}</checksum>
            <open-checksum type="sha256">{open_sha256}</open-checksum>
            <location href="{href}"/>
            <timestamp>{timestamp}</timestamp>
            <size>{size}</size>
            <open-size>{open_size}</open-size>
          </data>
        """.format(**primary)
        return (
            '<repomd xmlns="http://linux.duke.edu/metadata/repo">'
            "<revision>{}</revision>{}{}</repomd>".format(
                repository["repomd"]["revision"],
                row,
                row if duplicate_primary else "",
            )
        ).encode("utf-8")

    def test_repomd_exact_primary_identity_is_accepted(self) -> None:
        result = evidence.verify_repomd_primary(self.repomd(), self.lock)
        self.assertEqual(
            result["sha256"],
            self.lock["repository_snapshot"]["primary_metadata"]["sha256"],
        )

    def test_repomd_mutations_and_duplicate_primary_are_rejected(self) -> None:
        mutations = (
            self.repomd().replace(b"<revision>10.2", b"<revision>10.1"),
            self.repomd().replace(b'type="sha256"', b'type="sha1"', 1),
            self.repomd().replace(b"repodata/", b"../", 1),
            self.repomd(duplicate_primary=True),
            b"<!DOCTYPE repomd><repomd/>",
        )
        for payload in mutations:
            with self.subTest(payload=payload[:80]):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.verify_repomd_primary(payload, self.lock)

    def test_open_primary_checks_compressed_and_uncompressed_hashes(self) -> None:
        opened = b"<metadata/>\n"
        compressed = gzip.compress(opened, mtime=0)
        expected = {
            "size": len(compressed),
            "sha256": hashlib.sha256(compressed).hexdigest(),
            "open_size": len(opened),
            "open_sha256": hashlib.sha256(opened).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            path.write_bytes(compressed)
            self.assertEqual(
                evidence.verify_open_primary(path, expected)["open_size"], len(opened)
            )
            wrong = dict(expected)
            wrong["open_sha256"] = "0" * 64
            with self.assertRaises(evidence.EvidenceError):
                evidence.verify_open_primary(path, wrong)


class SignatureParserTests(unittest.TestCase):
    FINGERPRINT = "FC226859C0860BF0DDB95B085B106C736FEDFC85"

    def test_gpg_key_and_validsig_are_bound_to_full_fingerprint_and_time(self) -> None:
        colon = (
            "pub:-:4096:1:5B106C736FEDFC85:0:0::::::\n"
            "fpr:::::::::FC226859C0860BF0DDB95B085B106C736FEDFC85:\n"
            "sub:-:4096:1:1234567890ABCDEF:0:0::::::\n"
            "fpr:::::::::1111111111111111111111111111111111111111:\n"
        ).encode("ascii")
        self.assertEqual(
            evidence.parse_primary_key_fingerprint(colon), self.FINGERPRINT
        )
        status = (
            "[GNUPG:] GOODSIG 5B106C736FEDFC85 Rocky_Linux\n"
            "[GNUPG:] VALIDSIG {0} 20260811 1786434220 0 4 0 1 10 00 {0}\n"
        ).format(self.FINGERPRINT).encode("ascii")
        result = evidence.parse_gpg_validsig(status, self.FINGERPRINT, 1786434220)
        self.assertEqual(result["primary_fingerprint"], self.FINGERPRINT)
        self.assertEqual(result["hash_algorithm_id"], 10)

    def test_gpg_bad_missing_duplicate_and_wrong_time_statuses_fail(self) -> None:
        good_line = (
            "[GNUPG:] VALIDSIG {0} 20260811 1786434220 0 4 0 1 10 00 {0}\n"
        ).format(self.FINGERPRINT)
        cases = (
            good_line,
            "[GNUPG:] GOODSIG 5B106C736FEDFC85 Rocky\n" + good_line + good_line,
            "[GNUPG:] GOODSIG 5B106C736FEDFC85 Rocky\n" + good_line.replace("1786434220", "1"),
            "[GNUPG:] BADSIG 5B106C736FEDFC85 Rocky\n" + good_line,
        )
        for status in cases:
            with self.subTest(status=status):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_gpg_validsig(
                        status.encode("ascii"), self.FINGERPRINT, 1786434220
                    )

    def test_rpm_header_signature_requires_one_ok_header_and_key_suffix(self) -> None:
        output = (
            "/tmp/kernel.src.rpm:\n"
            "    Header V4 RSA/SHA256 Signature, key ID 6fedfc85: OK\n"
            "    Header SHA256 digest: OK\n"
            "    Payload SHA256 digest: OK\n"
        ).encode("ascii")
        result = evidence.parse_rpm_header_signature(output, self.FINGERPRINT)
        self.assertEqual(result["signature_algorithm"], "RSA/SHA256")
        self.assertEqual(result["signer_fingerprint"], self.FINGERPRINT)
        modern = (
            "Header OpenPGP V4 RSA/SHA256, key fingerprint "
            + self.FINGERPRINT
            + " signature: OK\n"
        ).encode("ascii")
        modern_result = evidence.parse_rpm_header_signature(
            modern, self.FINGERPRINT
        )
        self.assertEqual(
            modern_result["signature_key_identity_type"], "fingerprint"
        )
        for broken in (
            output.replace(b"6fedfc85", b"00000000"),
            output.replace(b": OK", b": NOKEY", 1),
            output + b"Header V4 RSA/SHA256 Signature, key ID 6fedfc85: OK\n",
            b"digests signatures OK\n",
        ):
            with self.subTest(broken=broken):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_rpm_header_signature(broken, self.FINGERPRINT)


class DistGitInspectionTests(unittest.TestCase):
    def git(self, repo: Path, *arguments: str) -> bytes:
        return subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout

    def test_annotated_tag_parent_and_every_locked_blob_are_verified(self) -> None:
        if not shutil_which("git"):
            self.skipTest("git is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "dist-git"
            repo.mkdir()
            self.git(repo, "init", "--quiet")
            self.git(repo, "config", "user.name", "RK001 Test")
            self.git(repo, "config", "user.email", "rk001@example.invalid")
            (repo / "README").write_text("parent\n", encoding="utf-8")
            self.git(repo, "add", "README")
            self.git(repo, "commit", "--quiet", "-m", "parent")
            parent = self.git(repo, "rev-parse", "HEAD").decode().strip()

            content = {
                "SPECS/kernel.spec": b"Name: kernel\n",
                "SOURCES/locked.patch": b"one\ntwo\n",
            }
            for relative, data in content.items():
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            self.git(repo, "add", "SPECS", "SOURCES")
            self.git(repo, "commit", "--quiet", "-m", "locked")
            commit = self.git(repo, "rev-parse", "HEAD").decode().strip()
            original_hash = "a" * 64
            tag = "patched/r10/kernel-test"
            self.git(repo, "tag", "-a", tag, "-m", "original hash " + original_hash)
            tag_object = self.git(repo, "rev-parse", tag).decode().strip()

            lock = {
                "dist_git": {
                    "commit": commit,
                    "commit_parent": parent,
                    "content": [
                        {
                            "path": "SPECS/kernel.spec",
                            "sha256": hashlib.sha256(content["SPECS/kernel.spec"]).hexdigest(),
                            "size": len(content["SPECS/kernel.spec"]),
                        }
                    ],
                    "repository_url": "https://git.rockylinux.org/staging/rpms/kernel.git",
                    "tag": tag,
                    "tag_annotation_original_hash": original_hash,
                    "tag_object": tag_object,
                }
            }
            series = {
                "patches": [
                    {
                        "line_count": 2,
                        "path": "SOURCES/locked.patch",
                        "sha256": hashlib.sha256(content["SOURCES/locked.patch"]).hexdigest(),
                        "size": len(content["SOURCES/locked.patch"]),
                    }
                ]
            }
            result = evidence.inspect_dist_git(repo, lock, series)
            self.assertEqual(result["tag_peel"], commit)
            self.assertEqual(len(result["blobs"]), 2)
            self.assertFalse(result["http_redirects_allowed"])

            broken = copy.deepcopy(lock)
            broken["dist_git"]["content"][0]["sha256"] = "0" * 64
            with self.assertRaises(evidence.EvidenceError):
                evidence.inspect_dist_git(repo, broken, series)


class OutputTests(unittest.TestCase):
    def test_evidence_files_are_canonical_sorted_and_checksum_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence.write_evidence_file(root, "z-result.json", {"z": 1})
            evidence.write_evidence_file(root, "a-result.json", {"a": 1})
            names = evidence.finalize_evidence(root)
            self.assertEqual(names, ["a-result.json", "z-result.json", "SHA256SUMS"])
            lines = (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
            self.assertTrue(lines[0].endswith("  a-result.json"))
            self.assertTrue(lines[1].endswith("  z-result.json"))
            self.assertEqual((root / "a-result.json").read_bytes(), b'{"a":1}\n')

    def test_bound_record_does_not_claim_gate_readiness(self) -> None:
        record = evidence.bound_record(
            {"checkpoint_id": evidence.CHECKPOINT_ID}, "acquisition_replay", {"ok": True}
        )
        self.assertNotIn("credit_eligible", record)
        source = (REPO_ROOT / evidence.CAPTURE_SCRIPT_PATH).read_text(encoding="utf-8")
        self.assertIn('"rk_001_ready": False', source)
        self.assertIn('"credit_eligible": False', source)

    def test_log_blocks_round_trip_every_canonical_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence.write_evidence_file(root, "capture-context.json", {"z": 1})
            evidence.write_evidence_file(root, "capture-summary.json", {"a": 2})
            names = evidence.finalize_evidence(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                evidence.print_reconstructable_evidence(root, names)

            lines = output.getvalue().splitlines()
            self.assertEqual(len(lines), len(names) * 3)
            reconstructed = {}
            for index in range(0, len(lines), 3):
                begin = lines[index].split()
                encoded = lines[index + 1]
                end = lines[index + 2].split()
                self.assertEqual(begin[0], "RK001_EVIDENCE_BEGIN")
                self.assertEqual(end, ["RK001_EVIDENCE_END", begin[1]])
                data = base64.b64decode(encoded, validate=True)
                self.assertEqual(len(data), int(begin[2]))
                self.assertEqual(hashlib.sha256(data).hexdigest(), begin[3])
                self.assertEqual(data, (root / begin[1]).read_bytes())
                reconstructed[begin[1]] = data
            self.assertEqual(sorted(reconstructed), sorted(names))

            workflow = evidence.validate_workflow_contract(REPO_ROOT).decode("utf-8")
            capture_step = workflow.split(
                "- name: Capture exact RK-001 replay evidence", 1
            )[1].split("- name: Upload canonical source evidence", 1)[0]
            self.assertIn("--run", capture_step)
            self.assertNotIn("> /", capture_step)
            script = (REPO_ROOT / evidence.CAPTURE_SCRIPT_PATH).read_text(
                encoding="utf-8"
            )
            self.assertIn("print_reconstructable_evidence(output_dir, names)", script)
            self.assertIn("RK001_EVIDENCE_BEGIN", script)


def shutil_which(command: str):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    unittest.main()
