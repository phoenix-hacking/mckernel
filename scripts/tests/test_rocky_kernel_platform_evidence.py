#!/usr/bin/env python3
"""Fail-closed tests for bounded RK-003/RK-005 evidence capture."""

import ast
import copy
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
from pathlib import Path, PurePosixPath
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_platform_evidence as evidence  # noqa: E402


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
        del exc_type, exc, traceback
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
        cls.plan, cls.toolchain_blockers, cls.config_blockers = evidence.check_repository(
            REPO_ROOT
        )

    def test_current_contract_is_valid_and_never_claims_credit(self) -> None:
        self.assertEqual(
            self.plan["gate_claims"], {"RK-003": False, "RK-005": False}
        )
        self.assertTrue(self.toolchain_blockers)
        self.assertTrue(self.config_blockers)
        self.assertFalse(self.plan["phases"][0]["blockers_after_phase"] == [])
        self.assertEqual(
            [phase["implemented"] for phase in self.plan["phases"]],
            [True, False, False],
        )

    def test_plan_is_byte_locked_and_container_is_amd64_manifest(self) -> None:
        plan_bytes = (REPO_ROOT / evidence.PLAN_PATH).read_bytes()
        self.assertEqual(
            hashlib.sha256(plan_bytes).hexdigest(), evidence.EXPECTED_PLAN_SHA256
        )
        self.assertEqual(
            self.plan["container"]["manifest_digest"],
            evidence.CONTAINER_MANIFEST_DIGEST,
        )
        self.assertEqual(self.plan["container"]["platform"], "linux/amd64")
        self.assertEqual(self.plan["bootstrap"]["artifact_count"], 47)
        self.assertEqual(
            sum(item["size"] for item in self.plan["bootstrap"]["artifacts"]),
            self.plan["bootstrap"]["total_bytes"],
        )
        self.assertFalse(
            self.plan["bootstrap"]["dnf_repository_network_requested"]
        )
        self.assertNotIn(
            "coreutils",
            {
                item["nevra"].split("-", 1)[0]
                for item in self.plan["bootstrap"]["artifacts"]
            },
        )

    def test_workflow_uses_only_pinned_actions_and_container(self) -> None:
        workflow_bytes = evidence.validate_workflow_contract(REPO_ROOT)
        self.assertEqual(
            hashlib.sha256(workflow_bytes).hexdigest(),
            evidence.EXPECTED_WORKFLOW_SHA256,
        )
        workflow = workflow_bytes.decode("utf-8")
        self.assertEqual(
            workflow.count("image: " + evidence.CONTAINER_IMAGE), 1
        )
        self.assertNotIn("image: rockylinux/rockylinux:10.2\n", workflow)
        self.assertNotIn("actions/checkout@v", workflow)
        self.assertNotIn("actions/upload-artifact@v", workflow)
        self.assertEqual(
            workflow.count(
                "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
            ),
            2,
        )
        self.assertEqual(workflow.count("set-safe-directory: false"), 1)
        self.assertEqual(workflow.count("set-safe-directory: true"), 1)
        self.assertNotIn("dnf -y install", workflow)
        script = (REPO_ROOT / evidence.CAPTURE_SCRIPT_PATH).read_text(
            encoding="utf-8"
        )
        self.assertIn('"--disablerepo=*"', script)
        self.assertIn('"--cacheonly"', script)
        self.assertIn('"safe.directory={}".format(canonical_repo)', script)
        self.assertNotIn("safe.directory=*", script)
        self.assertNotIn("--global", script)
        self.assertIn('git -c "safe.directory=$canonical_workspace"', workflow)
        self.assertNotIn("safe.directory=*", workflow)
        self.assertNotIn("git config --global", workflow)
        self.assertEqual(workflow.count(" rev-parse HEAD"), 1)
        mutated = workflow_bytes + (
            b"\n# forbidden extra execution\n"
            b"# uses: owner/action@0000000000000000000000000000000000000000\n"
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "bytes changed"):
            evidence.validate_workflow_bytes(mutated)

    def test_cli_check_succeeds_but_run_without_identity_fails(self) -> None:
        self.assertEqual(evidence.main(["--repo", str(REPO_ROOT), "--check"]), 0)
        self.assertEqual(
            evidence.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--run",
                    "--phase",
                    evidence.IMPLEMENTED_PHASE,
                ]
            ),
            2,
        )

    def test_checker_and_tests_avoid_post_python_3_6_syntax_and_apis(self) -> None:
        forbidden_fragments = (
            "from __future__ import " + "annotations",
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "capture_" + "output=",
            "missing_" + "ok=",
            "dirs_exist_" + "ok=",
        )
        forbidden_annotation_patterns = (
            r"\b(?:list|dict|set|tuple)\[[^\]]",
            r"\s\|\sNone\b",
        )
        for relative_path in (
            "scripts/rocky_kernel_platform_evidence.py",
            "scripts/tests/test_rocky_kernel_platform_evidence.py",
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
    @classmethod
    def setUpClass(cls) -> None:
        (
            cls.plan,
            cls.toolchain,
            cls.config,
            cls.source,
            _,
            _,
            _,
        ) = evidence.load_locked_inputs(REPO_ROOT)
        cls.plan_bytes = (REPO_ROOT / evidence.PLAN_PATH).read_bytes()

    def test_duplicate_json_keys_are_rejected_at_every_depth(self) -> None:
        for payload in (b'{"a":1,"a":2}', b'{"outer":{"a":1,"a":2}}'):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(evidence.EvidenceError, "duplicate JSON"):
                    evidence.strict_json_bytes(payload, "fixture")

    def test_non_object_invalid_utf8_and_large_json_are_rejected(self) -> None:
        payloads = (b"[]", b"\xff", b"{" + b" " * evidence.MAX_JSON_BYTES + b"}")
        for payload in payloads:
            with self.subTest(size=len(payload)):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.strict_json_bytes(payload, "fixture")

    def test_canonical_json_is_sorted_finite_and_newline_terminated(self) -> None:
        self.assertEqual(
            evidence.canonical_json_bytes({"z": 1, "a": [True, None]}),
            b'{"a":[true,null],"z":1}\n',
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence.canonical_json_bytes({"bad": float("nan")})

    def test_any_plan_byte_change_requires_validator_review(self) -> None:
        mutated = copy.deepcopy(self.plan)
        mutated["gate_claims"]["RK-003"] = True
        mutated_bytes = evidence.canonical_json_bytes(mutated)
        with self.assertRaisesRegex(evidence.EvidenceError, "bytes changed"):
            evidence.validate_plan(
                mutated,
                mutated_bytes,
                self.toolchain,
                self.config,
                self.source,
            )

    def test_repository_input_rejects_symlinks_and_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            regular = root / "regular"
            regular.write_text("ok", encoding="utf-8")
            self.assertEqual(evidence.repository_file(root, Path("regular")), regular)
            outside = root.parent / (root.name + "-outside")
            outside.write_text("outside", encoding="utf-8")
            try:
                link = root / "link"
                link.symlink_to(outside)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.repository_file(root, Path("link"))
                with self.assertRaises(evidence.EvidenceError):
                    evidence.repository_file(root, Path("../" + outside.name))
            finally:
                outside.unlink()

    def test_https_policy_rejects_redirect_prone_or_ambiguous_urls(self) -> None:
        valid = "https://download.rockylinux.org/pub/rocky/locked"
        self.assertEqual(
            evidence.validate_https_url(
                valid, ["download.rockylinux.org"], "fixture"
            ),
            valid,
        )
        for url in (
            "http://download.rockylinux.org/pub/rocky/locked",
            "https://evil.invalid/pub/rocky/locked",
            "https://download.rockylinux.org:443/pub/rocky/locked",
            "https://download.rockylinux.org/pub/rocky/locked?latest=1",
            "https://user@download.rockylinux.org/pub/rocky/locked",
        ):
            with self.subTest(url=url):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_https_url(
                        url, ["download.rockylinux.org"], "fixture"
                    )


class SourceEvidenceStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source, _ = evidence.read_repository_json(
            REPO_ROOT, evidence.SOURCE_LOCK_PATH
        )

    def test_current_missing_source_evidence_remains_valid_blocked_input(self) -> None:
        blockers = evidence.validate_source_evidence_state(self.source, REPO_ROOT)
        self.assertTrue(blockers)
        self.assertFalse(self.source["gate"]["credit_eligible"])

    def test_fully_verified_source_gate_is_accepted_without_platform_credit(self) -> None:
        source = copy.deepcopy(self.source)
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary).resolve()
            for index, name in enumerate(sorted(source["evidence"])):
                payload = ("verified-source-evidence-{}\n".format(name)).encode(
                    "ascii"
                )
                relative = "evidence/{}.json".format(index)
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                row = source["evidence"][name]
                row["blocker"] = None
                row["evidence_path"] = relative
                row["evidence_sha256"] = hashlib.sha256(payload).hexdigest()
                row["status"] = "verified"
                if name == "srpm_header_signature":
                    row["signature_algorithm"] = "RSA/SHA256"
                    row["signer_fingerprint"] = (
                        evidence.platform_lock.EXPECTED_RELEASE_KEY["fingerprint"]
                    )
            inventory_payload = b"verified-license-inventory\n"
            inventory_path = repo / "evidence/licenses.json"
            inventory_path.write_bytes(inventory_payload)
            inventory = source["licenses"]["inventory"]
            inventory.update(
                {
                    "blocker": None,
                    "complete": True,
                    "inventory_path": "evidence/licenses.json",
                    "inventory_sha256": hashlib.sha256(
                        inventory_payload
                    ).hexdigest(),
                    "item_count": 1,
                    "status": "verified",
                }
            )
            source["gate"]["credit_eligible"] = True
            self.assertEqual(
                evidence.validate_source_evidence_state(source, repo), []
            )
            source["gate"]["credit_eligible"] = False
            with self.assertRaisesRegex(evidence.EvidenceError, "credit state"):
                evidence.validate_source_evidence_state(source, repo)


class RunIdentityTests(unittest.TestCase):
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

    def test_os_release_requires_exact_rocky_10_2(self) -> None:
        self.assertEqual(
            evidence.parse_os_release(
                b'NAME="Rocky Linux"\nID="rocky"\nVERSION_ID="10.2"\n'
            ),
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


class InventoryTests(unittest.TestCase):
    def test_runtime_inventory_normalizes_unsorted_rpm_output(self) -> None:
        raw = b"zpkg-0:1-1.x86_64\napkg-0:1-1.x86_64\n"
        with mock.patch.object(evidence, "run_command", return_value=(raw, b"")):
            packages, data = evidence.rpm_inventory()
        self.assertEqual(
            packages, ["apkg-0:1-1.x86_64", "zpkg-0:1-1.x86_64"]
        )
        self.assertEqual(
            data, b"apkg-0:1-1.x86_64\nzpkg-0:1-1.x86_64\n"
        )

    def test_archived_inventory_requires_canonical_unique_rows(self) -> None:
        canonical = b"apkg-0:1-1.x86_64\nzpkg-0:1-1.x86_64\n"
        self.assertEqual(
            evidence.parse_rpm_inventory_bytes(canonical, "fixture"),
            ["apkg-0:1-1.x86_64", "zpkg-0:1-1.x86_64"],
        )
        for payload in (
            canonical[::-1],
            b"zpkg-0:1-1.x86_64\napkg-0:1-1.x86_64\n",
            b"apkg-0:1-1.x86_64\napkg-0:1-1.x86_64\n",
            b"apkg-0:1-1.x86_64",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_rpm_inventory_bytes(payload, "fixture")

    def test_bootstrap_signature_checks_use_only_private_rpmdb(self) -> None:
        script = (REPO_ROOT / evidence.CAPTURE_SCRIPT_PATH).read_text(
            encoding="utf-8"
        )
        self.assertNotIn('Path("/var/lib/rpm")', script)
        self.assertEqual(script.count("create_private_rpmdb("), 4)


class DownloadTests(unittest.TestCase):
    URL = "https://download.rockylinux.org/pub/rocky/locked"

    def session(self, response: FakeResponse) -> evidence.NetworkSession:
        return evidence.NetworkSession(
            ["download.rockylinux.org"], FakeOpener(response)
        )

    def test_exact_download_publishes_read_only_bytes_then_seals(self) -> None:
        payload = b"locked rpm bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            session = self.session(FakeResponse(payload, self.URL))
            result = session.download_exact(
                self.URL, target, digest, len(payload), len(payload)
            )
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(target.stat().st_mode & 0o777, 0o400)
            self.assertEqual(result["redirect_count"], 0)
            session.seal()
            with self.assertRaisesRegex(evidence.EvidenceError, "after acquisition seal"):
                session.download_exact(
                    self.URL, Path(temporary) / "second", digest, len(payload), len(payload)
                )

    def test_mismatch_drift_and_ambiguous_headers_fail_without_artifact(self) -> None:
        payload = b"locked rpm bytes"
        digest = hashlib.sha256(payload).hexdigest()
        cases = (
            ("hash", "0" * 64, len(payload), FakeResponse(payload, self.URL)),
            ("final-url", digest, len(payload), FakeResponse(payload, self.URL + "/moved")),
            ("length", digest, len(payload), FakeResponse(payload, self.URL, content_length="1")),
            ("encoding", digest, len(payload), FakeResponse(payload, self.URL, content_encoding="gzip")),
            ("duplicate", digest, len(payload), FakeResponse(payload, self.URL, duplicate_length=True)),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, expected_digest, expected_size, response in cases:
                with self.subTest(name=name):
                    target = root / name
                    with self.assertRaises(evidence.EvidenceError):
                        self.session(response).download_exact(
                            self.URL,
                            target,
                            expected_digest,
                            expected_size,
                            len(payload),
                        )
                    self.assertFalse(target.exists())

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
    PRIMARY = {
        "href": "repodata/" + "a" * 64 + "-primary.xml.gz",
        "open_sha256": "b" * 64,
        "open_size": 10,
        "sha256": "a" * 64,
        "size": 20,
    }

    @classmethod
    def repository(cls):
        return {
            "id": "baseos",
            "primary": copy.deepcopy(cls.PRIMARY),
            "repomd": {"revision": "10.2"},
        }

    def repomd(self, duplicate_primary: bool = False) -> bytes:
        row = """
          <data type="primary">
            <checksum type="sha256">{sha256}</checksum>
            <open-checksum type="sha256">{open_sha256}</open-checksum>
            <location href="{href}"/>
            <size>{size}</size>
            <open-size>{open_size}</open-size>
          </data>
        """.format(**self.PRIMARY)
        return (
            '<repomd xmlns="http://linux.duke.edu/metadata/repo">'
            "<revision>10.2</revision>{}{}</repomd>".format(
                row, row if duplicate_primary else ""
            )
        ).encode("utf-8")

    def test_repomd_exact_primary_identity_is_accepted(self) -> None:
        result = evidence.parse_repomd(self.repomd(), self.repository())
        self.assertEqual(result["primary"], self.PRIMARY)

    def test_repomd_mutations_and_duplicate_primary_fail_closed(self) -> None:
        mutations = (
            self.repomd().replace(b"<revision>10.2", b"<revision>10.1"),
            self.repomd().replace(b'type="sha256"', b'type="sha1"', 1),
            self.repomd(duplicate_primary=True),
            b"<!DOCTYPE repomd><repomd/>",
        )
        for payload in mutations:
            with self.subTest(payload=payload[:80]):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_repomd(payload, self.repository())

    def primary_xml(self, duplicate: bool = False, bad_size: bool = False) -> bytes:
        package = """
          <package type="rpm">
            <name>rust</name><arch>x86_64</arch>
            <version epoch="0" ver="1.92.0" rel="1.el10"/>
            <checksum type="sha256" pkgid="YES">{digest}</checksum>
            <size package="{size}" installed="1" archive="1"/>
            <location href="Packages/r/rust.rpm"/>
          </package>
        """.format(digest="c" * 64, size=10 if not bad_size else 9)
        return (
            '<metadata xmlns="http://linux.duke.edu/metadata/common" packages="{}">{}{}</metadata>'.format(
                2 if duplicate else 1, package, package if duplicate else ""
            )
        ).encode("utf-8")

    def artifact(self):
        return {
            "arch": "x86_64",
            "epoch": 0,
            "name": "rust",
            "nevra": "rust-0:1.92.0-1.el10.x86_64",
            "release": "1.el10",
            "repository_location": "Packages/r/rust.rpm",
            "sha256": "c" * 64,
            "size": 10,
            "version": "1.92.0",
        }

    def test_primary_open_digest_and_locked_artifact_are_verified(self) -> None:
        plain = self.primary_xml()
        compressed = gzip.compress(plain)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            path.write_bytes(compressed)
            self.assertEqual(
                evidence.verify_primary_open_identity(
                    path, hashlib.sha256(plain).hexdigest(), len(plain)
                )["open_size"],
                len(plain),
            )
            found = evidence.parse_primary_artifacts(
                path, "baseos", [self.artifact()]
            )
            self.assertIn(self.artifact()["nevra"], found)

    def test_primary_duplicate_mismatch_and_xml_declaration_fail(self) -> None:
        fixtures = (
            self.primary_xml(duplicate=True),
            self.primary_xml(bad_size=True),
            b'<!DOCTYPE metadata><metadata xmlns="http://linux.duke.edu/metadata/common"/>',
        )
        with tempfile.TemporaryDirectory() as temporary:
            for index, plain in enumerate(fixtures):
                with self.subTest(index=index):
                    path = Path(temporary) / (str(index) + ".gz")
                    path.write_bytes(gzip.compress(plain))
                    if index == 2:
                        with self.assertRaises(evidence.EvidenceError):
                            evidence.verify_primary_open_identity(
                                path, hashlib.sha256(plain).hexdigest(), len(plain)
                            )
                    else:
                        with self.assertRaises(evidence.EvidenceError):
                            evidence.parse_primary_artifacts(
                                path, "baseos", [self.artifact()]
                            )


class SignatureAndResolutionTests(unittest.TestCase):
    FINGERPRINT = "FC226859C0860BF0DDB95B085B106C736FEDFC85"

    def test_gpg_status_requires_one_exact_validsig(self) -> None:
        valid = (
            "[GNUPG:] NEWSIG\n[GNUPG:] VALIDSIG {} 2026-08-11 0 4 0 1 10 00 {}\n".format(
                self.FINGERPRINT, self.FINGERPRINT
            )
        ).encode("ascii")
        self.assertEqual(
            evidence.parse_gpgv_status(valid, self.FINGERPRINT)["status"],
            "verified",
        )
        for payload in (
            valid.replace(self.FINGERPRINT.encode(), b"0" * 40, 1),
            valid + valid,
            b"[GNUPG:] BADSIG 6FEDFC85 Rocky\n",
        ):
            with self.subTest(payload=payload[:80]):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_gpgv_status(payload, self.FINGERPRINT)

    def test_rpm_signature_requires_header_payload_and_expected_key(self) -> None:
        valid = (
            "archive.rpm:\n"
            "    Header V4 RSA/SHA256 Signature, key ID 6fedfc85: OK\n"
            "    Header SHA256 digest: OK\n"
            "    Payload SHA256 digest: OK\n"
        ).encode("ascii")
        result = evidence.parse_rpm_signature(valid, self.FINGERPRINT)
        self.assertEqual(result["signer_fingerprint"], self.FINGERPRINT)
        mutations = (
            valid.replace(b"6fedfc85", b"00000000"),
            valid.replace(b"Payload SHA256 digest: OK\n", b""),
            valid.replace(b": OK", b": NOT OK", 1),
            valid + valid,
        )
        for payload in mutations:
            with self.subTest(payload=payload[-80:]):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_rpm_signature(payload, self.FINGERPRINT)

    def test_buildrequires_are_canonical_and_reviewed_rust_is_separate(self) -> None:
        result = evidence.parse_buildrequires(
            b"make\ngcc >= 14\nmake\n", evidence.EXPECTED_REVIEWED_RUST_BUILDREQUIRES
        )
        self.assertEqual(result["rocky_effective"], ["gcc >= 14", "make"])
        self.assertEqual(
            result["reviewed_rocky_rust_additions"],
            ["bindgen", "rust", "rust-src"],
        )
        for payload in (b"rust\nmake\n", b"%{unresolved}\n", b"\x01bad\n", b""):
            with self.subTest(payload=payload):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.parse_buildrequires(
                        payload, evidence.EXPECTED_REVIEWED_RUST_BUILDREQUIRES
                    )

    def test_dist_git_raw_url_is_commit_bound_and_normalized(self) -> None:
        source, blockers = evidence.load_source_inputs(REPO_ROOT)
        self.assertTrue(blockers)
        url = evidence.source_raw_url(source, "SPECS/kernel.spec")
        self.assertIn(source["dist_git"]["commit"], url)
        self.assertTrue(url.endswith("/SPECS/kernel.spec"))
        with self.assertRaises(evidence.EvidenceError):
            evidence.source_raw_url(source, "../kernel.spec")


class OutputTests(unittest.TestCase):
    def test_output_is_exclusive_regular_and_has_strict_sha256sums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = evidence.prepare_output_dir(Path(temporary).resolve() / "evidence")
            evidence.write_output_json(
                root, PurePosixPath("manifest.json"), {"schema_version": 1}
            )
            evidence.write_output_bytes(
                root, PurePosixPath("archives/file.rpm"), b"rpm"
            )
            sums = evidence.write_sha256sums(root).read_text(encoding="ascii")
            self.assertIn("  manifest.json\n", sums)
            self.assertIn("  archives/file.rpm\n", sums)
            self.assertNotIn("SHA256SUMS", sums)
            with self.assertRaises(evidence.EvidenceError):
                evidence.write_output_bytes(
                    root, PurePosixPath("manifest.json"), b"overwrite"
                )

    def test_sha256_manifest_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = evidence.prepare_output_dir(Path(temporary).resolve() / "evidence")
            evidence.write_output_bytes(root, PurePosixPath("regular"), b"ok")
            (root / "link").symlink_to(root / "regular")
            with self.assertRaisesRegex(evidence.EvidenceError, "symlink"):
                evidence.write_sha256sums(root)

    def test_output_directory_rejects_relative_existing_and_symlink_paths(self) -> None:
        with self.assertRaises(evidence.EvidenceError):
            evidence.prepare_output_dir(Path("relative"))
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            existing = parent / "existing"
            existing.mkdir()
            with self.assertRaises(evidence.EvidenceError):
                evidence.prepare_output_dir(existing)
            symlink = parent / "link"
            symlink.symlink_to(existing, target_is_directory=True)
            with self.assertRaises(evidence.EvidenceError):
                evidence.prepare_output_dir(symlink)


def shutil_which(command: str):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    unittest.main()
