#!/usr/bin/env python3
"""Adversarial tests for the bounded RK-001 license-decision foundation."""

from __future__ import print_function

import ast
import copy
import gzip
import hashlib
import io
import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rocky_kernel_license_decisions as decisions


MANIFEST = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-decisions-ef58-v1.json"
)
DEFAULT_ARTIFACT = Path(
    "/workspace/scratch/1962bd8160f6/ci-evidence/ef58860e/"
    "rk001-license-inventory-32192199002-1.zip"
)


def false_values(value):
    if isinstance(value, dict):
        result = []
        for key in sorted(value):
            result.extend(false_values(value[key]))
        return result
    return [value]


def zip_bytes(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 18, 22, 21, 38))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return output.getvalue()


class LicenseDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest_bytes = MANIFEST.read_bytes()
        cls.authority = decisions.load_authority(REPO_ROOT)

    def artifact_path(self):
        configured = os.environ.get("MCKERNEL_RK001_LICENSE_ARTIFACT")
        candidates = []
        if configured:
            candidates.append(Path(configured))
        candidates.extend(
            [
                DEFAULT_ARTIFACT,
                Path("/tmp/rk001-license-inventory-32192199002-1.zip"),
            ]
        )
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        self.skipTest("exact ef58860e RK-001 inventory artifact is not materialized")

    def artifact_entries(self):
        with zipfile.ZipFile(str(self.artifact_path()), "r") as archive:
            return [(info.filename, archive.read(info)) for info in archive.infolist()]

    def item(self):
        return {
            "authorship_signals": [],
            "entry_type": "regular",
            "license_text_paths": ["linux/LICENSES/preferred/GPL-2.0"],
            "link_target": None,
            "origin": "linux-archive:sha256:{0}".format("2" * 64),
            "path": "linux/drivers/example.c",
            "review_status": "captured-unreviewed",
            "sha256": "1" * 64,
            "size": 1,
            "source_identity": {"archive_sha256": "2" * 64},
            "spdx_expression": "GPL-2.0-only",
            "unresolved_reasons": ["independent-review-required"],
        }

    def classify(self, item):
        decisions.validate_item(item)
        return decisions.classify_item(item, decisions.catalog(self.authority))

    def test_new_files_retain_python_3_6_grammar(self):
        for relative in (
            "scripts/rocky_kernel_license_decisions.py",
            "scripts/tests/test_rocky_kernel_license_decisions.py",
        ):
            path = REPO_ROOT / relative
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for fragment in (
                ".is_relative" + "_to(",
                ".remove" + "prefix(",
                ".remove" + "suffix(",
                "capture_" + "output=",
                "missing_" + "ok=",
            ):
                self.assertNotIn(fragment, source)

    def test_manifest_is_canonical_digest_locked_and_valid(self):
        self.assertEqual(
            hashlib.sha256(self.manifest_bytes).hexdigest(),
            decisions.AUTHORITY_SHA256,
        )
        value = decisions.read_json_bytes(
            self.manifest_bytes, "authority", canonical=True
        )
        self.assertEqual(decisions.validate_authority(copy.deepcopy(value)), value)

    def test_all_credit_legal_durability_and_tracker_claims_are_false(self):
        self.assertEqual(
            false_values(self.authority["claims"]),
            [False] * len(false_values(self.authority["claims"])),
        )
        self.assertEqual(
            self.authority["gate"],
            {
                "credit_eligible": False,
                "gate_id": "RK-001",
                "points_awarded": 0,
                "status": "TODO",
                "tracker_credit": False,
            },
        )

    def test_exact_result_counts_are_conservative_and_close(self):
        result = self.authority["expected_result"]
        self.assertEqual(result["inventory_item_count"], 115265)
        self.assertEqual(result["machine_classified_count"], 72616)
        self.assertEqual(result["unresolved_count"], 42649)
        self.assertEqual(
            result["machine_classified_count"] + result["unresolved_count"],
            result["inventory_item_count"],
        )
        self.assertEqual(sum(result["basis_counts"].values()), 115265)
        self.assertEqual(
            result["basis_counts"]["ambiguous-spdx-needs-review"], 15
        )
        self.assertEqual(
            result["basis_counts"]["noncanonical-spdx-needs-review"], 61
        )
        self.assertEqual(
            result["basis_counts"]["archive-or-rpm-spec-needs-review"], 31
        )
        self.assertEqual(
            result["basis_counts"]["nonregular-link-needs-review"], 83
        )

    def test_namespace_counts_cover_every_inventory_item(self):
        result = self.authority["expected_result"]
        namespace_total = 0
        resolved_total = 0
        for namespace in ("dist-git", "linux", "repository", "srpm"):
            values = result["namespace_decision_counts"][namespace]
            namespace_total += sum(values.values())
            resolved_total += values[decisions.RESOLVED]
        self.assertEqual(namespace_total, result["inventory_item_count"])
        self.assertEqual(resolved_total, result["machine_classified_count"])

    def test_exact_spdx_parser_accepts_only_structured_uppercase_operators(self):
        cases = {
            "GPL-2.0-only": (["GPL-2.0-only"], []),
            "GPL-2.0-only OR MIT": (["GPL-2.0-only", "MIT"], []),
            "(GPL-2.0 WITH Linux-syscall-note) OR BSD-3-Clause": (
                ["BSD-3-Clause", "GPL-2.0"],
                ["Linux-syscall-note"],
            ),
            "GPL-2.0-only AND (MIT OR Apache-2.0)": (
                ["Apache-2.0", "GPL-2.0-only", "MIT"],
                [],
            ),
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(
                    decisions.parse_spdx_expression(expression), expected
                )

    def test_noncanonical_and_malformed_spdx_syntax_is_rejected(self):
        expressions = (
            "GPL-2.0-only or MIT",
            "GPL-2.0-only and MIT",
            "GPL-2.0-only OR",
            "OR GPL-2.0-only",
            "(GPL-2.0-only",
            "GPL-2.0-only)",
            "(GPL-2.0-only OR MIT) WITH Linux-syscall-note",
            "GPL-2.0-only WITH",
            "NOASSERTION",
            "GPL-2.0-only / MIT",
            "GPL-2.0-only\tOR MIT",
            "GPL-2.0-only\u00a0OR\u00a0MIT",
            "GPL-2.0-only\x7fOR MIT",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(decisions.DecisionError):
                    decisions.parse_spdx_expression(expression)

    def test_deep_spdx_and_json_nesting_fail_as_bounded_decision_errors(self):
        expression = "(" * 1500 + "GPL-2.0-only" + ")" * 1500
        with self.assertRaises(decisions.DecisionError):
            decisions.parse_spdx_expression(expression)
        nested = b'{"x":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}\n"
        with self.assertRaises(decisions.DecisionError):
            decisions.read_json_bytes(nested, "deep JSON", canonical=True)

    def test_exact_spdx_with_known_text_is_machine_classified_only(self):
        result = self.classify(self.item())
        self.assertEqual(result["decision"], decisions.RESOLVED)
        self.assertEqual(result["basis"], decisions.RESOLVED_BASIS)
        self.assertNotIn("approved", result["decision"])
        self.assertNotIn("legal", result["decision"])

    def test_links_archives_specs_ambiguity_and_missing_signals_stay_unresolved(self):
        cases = []
        link = self.item()
        link["entry_type"] = "symlink"
        link["link_target"] = "example-target.c"
        cases.append((link, "nonregular-link-needs-review"))
        archive = self.item()
        archive["path"] = "srpm/SOURCES/source.tar.xz"
        cases.append((archive, "archive-or-rpm-spec-needs-review"))
        spec = self.item()
        spec["path"] = "srpm/SPECS/kernel.spec"
        cases.append((spec, "archive-or-rpm-spec-needs-review"))
        ambiguous = self.item()
        ambiguous["unresolved_reasons"] = [
            "ambiguous-spdx",
            "independent-review-required",
        ]
        cases.append((ambiguous, "ambiguous-spdx-needs-review"))
        missing = self.item()
        missing["license_text_paths"] = []
        missing["spdx_expression"] = "NOASSERTION"
        missing["unresolved_reasons"] = [
            "independent-review-required",
            "missing-spdx",
        ]
        cases.append((missing, "missing-spdx-needs-review"))
        for item, basis in cases:
            with self.subTest(basis=basis):
                result = self.classify(item)
                self.assertEqual(result["decision"], decisions.UNRESOLVED)
                self.assertEqual(result["basis"], basis)

    def test_noncanonical_extra_signal_and_unknown_text_cases_stay_unresolved(self):
        cases = []
        lowercase = self.item()
        lowercase["spdx_expression"] = "GPL-2.0-only or MIT"
        lowercase["license_text_paths"].append(
            "linux/LICENSES/preferred/MIT"
        )
        lowercase["license_text_paths"].sort()
        cases.append((lowercase, "noncanonical-spdx-needs-review"))
        extra = self.item()
        extra["unresolved_reasons"] = [
            "independent-review-required",
            "patch-license-signal-missing",
        ]
        cases.append((extra, "capture-signal-needs-review"))
        absent = self.item()
        absent["license_text_paths"] = []
        cases.append((absent, "license-evidence-needs-review"))
        unknown = self.item()
        unknown["spdx_expression"] = "LicenseRef-Unknown"
        cases.append((unknown, "license-evidence-needs-review"))
        for item, basis in cases:
            with self.subTest(basis=basis):
                result = self.classify(item)
                self.assertEqual(result["decision"], decisions.UNRESOLVED)
                self.assertEqual(result["basis"], basis)

    def test_exception_requires_its_exact_known_exception_text(self):
        item = self.item()
        item["spdx_expression"] = "GPL-2.0-only WITH Linux-syscall-note"
        result = self.classify(item)
        self.assertEqual(result["basis"], "license-evidence-needs-review")
        item["license_text_paths"] = [
            "linux/LICENSES/exceptions/Linux-syscall-note",
            "linux/LICENSES/preferred/GPL-2.0",
        ]
        result = self.classify(item)
        self.assertEqual(result["basis"], decisions.RESOLVED_BASIS)

    def test_item_schema_duplicate_keys_and_noncanonical_rows_fail_closed(self):
        item = self.item()
        mutated = copy.deepcopy(item)
        mutated["unknown"] = False
        with self.assertRaises(decisions.DecisionError):
            decisions.validate_item(mutated)
        for key in ("authorship_signals", "license_text_paths", "unresolved_reasons"):
            malformed = copy.deepcopy(item)
            malformed[key] = [[]]
            with self.subTest(key=key):
                with self.assertRaises(decisions.DecisionError):
                    decisions.validate_item(malformed)
        duplicate = b'{"path":"linux/a","path":"linux/b"}\n'
        with self.assertRaisesRegex(decisions.DecisionError, "duplicate JSON key"):
            decisions.read_json_bytes(duplicate, "row", canonical=True)
        pretty = json.dumps(item, indent=2, sort_keys=True).encode("ascii") + b"\n"
        with self.assertRaisesRegex(decisions.DecisionError, "canonical"):
            decisions.read_json_bytes(pretty, "row", canonical=True)

    def test_manifest_claim_gate_policy_and_expected_result_mutations_fail_closed(self):
        mutations = []
        for claim in sorted(self.authority["claims"]):
            value = copy.deepcopy(self.authority)
            value["claims"][claim] = True
            mutations.append(value)
        gate = copy.deepcopy(self.authority)
        gate["gate"]["status"] = "PASS"
        mutations.append(gate)
        credit = copy.deepcopy(self.authority)
        credit["gate"]["points_awarded"] = 75
        mutations.append(credit)
        policy = copy.deepcopy(self.authority)
        policy["decision_policy"]["resolved_basis"] = "manual-approval"
        mutations.append(policy)
        unknown = copy.deepcopy(self.authority)
        unknown["unknown"] = False
        mutations.append(unknown)
        for mutation in mutations:
            with self.assertRaises(decisions.DecisionError):
                decisions.validate_authority(mutation)

        changed_result = copy.deepcopy(self.authority)
        changed_result["expected_result"]["machine_classified_count"] += 1
        with self.assertRaisesRegex(decisions.DecisionError, "exact decision result"):
            decisions.require_exact(
                self.authority["expected_result"],
                changed_result["expected_result"],
                "exact decision result",
            )

    def test_nested_authority_schema_types_and_source_identity_are_closed(self):
        mutations = []
        empty_claims = copy.deepcopy(self.authority)
        empty_claims["claims"] = {}
        mutations.append(empty_claims)
        extra_claim = copy.deepcopy(self.authority)
        extra_claim["claims"]["not_a_required_claim"] = False
        mutations.append(extra_claim)
        blocker_type = copy.deepcopy(self.authority)
        blocker_type["remaining_blockers"] = [False]
        mutations.append(blocker_type)
        source_type = copy.deepcopy(self.authority)
        source_type["artifact"]["source_commit"] = False
        mutations.append(source_type)
        binding = copy.deepcopy(self.authority)
        binding["capture"]["binding"]["github_head_sha"] = "1" * 40
        mutations.append(binding)
        count_type = copy.deepcopy(self.authority)
        count_type["expected_result"]["basis_counts"][
            decisions.RESOLVED_BASIS
        ] = False
        mutations.append(count_type)
        embedded_type = copy.deepcopy(self.authority)
        embedded_type["capture"]["unexpanded_embedded_objects"] = [[]]
        mutations.append(embedded_type)
        embedded_empty = copy.deepcopy(self.authority)
        embedded_empty["capture"]["unexpanded_embedded_objects"] = []
        mutations.append(embedded_empty)
        identifiers_type = copy.deepcopy(self.authority)
        identifiers_type["known_license_texts"][0]["identifiers"] = [[]]
        mutations.append(identifiers_type)
        for key in ("basis_counts", "decision_counts", "capture_reason_counts"):
            wrong_container = copy.deepcopy(self.authority)
            wrong_container["expected_result"][key] = False
            mutations.append(wrong_container)
        mixed_counts = copy.deepcopy(self.authority)
        mixed_counts["expected_result"]["basis_counts"] = ["x", 1]
        mutations.append(mixed_counts)
        nested_reason = copy.deepcopy(self.authority)
        nested_reason["expected_result"]["capture_reason_counts"][
            "missing-spdx"
        ] = []
        mutations.append(nested_reason)
        for mutation in mutations:
            with self.assertRaises(decisions.DecisionError):
                decisions.validate_authority(mutation)

    def test_gzip_line_reader_rejects_oversized_row_before_unbounded_iteration(self):
        payload = gzip.compress(b"x" * (decisions.MAX_LINE_BYTES + 1), compresslevel=9)
        with self.assertRaisesRegex(decisions.DecisionError, "oversized"):
            list(decisions.bounded_gzip_lines(payload))
        self.assertEqual(
            list(decisions.bounded_gzip_lines(gzip.compress(b"a\nb\n"))),
            [b"a\n", b"b\n"],
        )
        corrupt = bytearray(gzip.compress(b'{"x":0}\n' * 1000))
        corrupt[10] ^= 0xff
        with self.assertRaisesRegex(decisions.DecisionError, "decompress"):
            list(decisions.bounded_gzip_lines(bytes(corrupt)))

    def test_retargeted_manifest_bytes_fail_the_frozen_digest(self):
        mutated = copy.deepcopy(self.authority)
        mutated["artifact"]["github_run_id"] = "1"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authority.json"
            path.write_bytes(decisions.canonical_json(mutated, newline=True))
            with self.assertRaisesRegex(decisions.DecisionError, "digest differs"):
                decisions.load_authority(REPO_ROOT, path)

    def test_exact_artifact_replays_all_rows_and_decision_digest(self):
        result = decisions.review_artifact(self.artifact_path(), self.authority)
        self.assertEqual(result, self.authority["expected_result"])
        self.assertEqual(result["inventory_item_count"], 115265)
        self.assertEqual(
            result["decision_stream_sha256"],
            "4770cb2676f8da2383860f5a087c8ede4190c00e60b37d7e4b48fa5bdba0279e",
        )

    def test_outer_artifact_byte_mutation_is_rejected(self):
        data = bytearray(self.artifact_path().read_bytes())
        data[-1] ^= 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutated.zip"
            path.write_bytes(bytes(data))
            with self.assertRaisesRegex(decisions.DecisionError, "ZIP digest differs"):
                decisions.read_artifact(path, self.authority["artifact"])

    def test_extra_zip_member_is_rejected_even_with_rebound_outer_digest(self):
        data = zip_bytes(self.artifact_entries() + [("extra", b"unexpected\n")])
        artifact = copy.deepcopy(self.authority["artifact"])
        artifact["zip_sha256"] = hashlib.sha256(data).hexdigest()
        artifact["zip_size"] = len(data)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "extra.zip"
            path.write_bytes(data)
            with self.assertRaisesRegex(decisions.DecisionError, "closure or order"):
                decisions.read_artifact(path, artifact)

    def test_unsupported_zip_compression_is_rejected_after_rebinding(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, payload in self.artifact_entries():
                info = zipfile.ZipInfo(name, date_time=(2026, 8, 18, 22, 21, 38))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, payload)
        data = output.getvalue()
        artifact = copy.deepcopy(self.authority["artifact"])
        artifact["zip_sha256"] = hashlib.sha256(data).hexdigest()
        artifact["zip_size"] = len(data)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stored.zip"
            path.write_bytes(data)
            with self.assertRaisesRegex(decisions.DecisionError, "compression"):
                decisions.read_artifact(path, artifact)

    def test_corrupt_deflate_member_is_a_controlled_rejection(self):
        data = bytearray(zip_bytes(self.artifact_entries()))
        name_length, extra_length = struct.unpack_from("<HH", data, 26)
        compressed_offset = 30 + name_length + extra_length
        data[compressed_offset] ^= 0xff
        mutated = bytes(data)
        artifact = copy.deepcopy(self.authority["artifact"])
        artifact["zip_sha256"] = hashlib.sha256(mutated).hexdigest()
        artifact["zip_size"] = len(mutated)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "corrupt-deflate.zip"
            path.write_bytes(mutated)
            with self.assertRaises(decisions.DecisionError):
                decisions.read_artifact(path, artifact)

    def test_internal_checksum_mutation_is_rejected_after_outer_rebinding(self):
        entries = self.artifact_entries()
        changed = []
        for name, payload in entries:
            if name == "SHA256SUMS":
                payload = payload.replace(payload[:1], b"0", 1)
            changed.append((name, payload))
        data = zip_bytes(changed)
        artifact = copy.deepcopy(self.authority["artifact"])
        artifact["zip_sha256"] = hashlib.sha256(data).hexdigest()
        artifact["zip_size"] = len(data)
        record = dict((row["name"], row) for row in artifact["members"])["SHA256SUMS"]
        mutated_sum = dict(changed)["SHA256SUMS"]
        record["sha256"] = hashlib.sha256(mutated_sum).hexdigest()
        record["size"] = len(mutated_sum)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checksum.zip"
            path.write_bytes(data)
            files = decisions.read_artifact(path, artifact)
            with self.assertRaisesRegex(decisions.DecisionError, "checksum manifest"):
                decisions.verify_checksum_manifest(files, artifact)

    def test_capture_summary_overclaim_and_count_mutations_are_rejected(self):
        files = decisions.read_artifact(
            self.artifact_path(), self.authority["artifact"]
        )
        summary = decisions.read_json_bytes(
            files["license-inventory-summary.json"], "summary", canonical=True
        )
        mutations = []
        overclaim = copy.deepcopy(summary)
        overclaim["credit_eligible"] = True
        mutations.append(overclaim)
        count = copy.deepcopy(summary)
        count["inventory"]["item_count"] -= 1
        mutations.append(count)
        binding = copy.deepcopy(summary)
        binding["binding"]["github_head_sha"] = "1" * 40
        mutations.append(binding)
        empty_sample = copy.deepcopy(summary)
        empty_sample["unresolved_sample"] = []
        mutations.append(empty_sample)
        nested_sample = copy.deepcopy(summary)
        nested_sample["unresolved_sample"] = [[]]
        mutations.append(nested_sample)
        mixed_sample = copy.deepcopy(summary)
        mixed_sample["unresolved_sample"] = ["x", 1]
        mutations.append(mixed_sample)
        malformed_sample = copy.deepcopy(summary)
        malformed_sample["unresolved_sample"][0] = {
            "path": False,
            "reasons": None,
        }
        mutations.append(malformed_sample)
        for mutation in mutations:
            with self.assertRaises(decisions.DecisionError):
                decisions.validate_summary(
                    decisions.canonical_json(mutation, newline=True), self.authority
                )

    def test_capture_unresolved_sample_is_bound_to_inventory_rows(self):
        files = decisions.read_artifact(
            self.artifact_path(), self.authority["artifact"]
        )
        summary = decisions.validate_summary(
            files["license-inventory-summary.json"], self.authority
        )
        mutated = copy.deepcopy(summary)
        mutated["unresolved_sample"][0]["path"] = "dist-git/000-retargeted"
        with self.assertRaisesRegex(decisions.DecisionError, "inventory binding"):
            decisions.analyze_inventory(
                files["license-inventory.jsonl.gz"], mutated, self.authority
            )

    def test_source_lock_and_tracker_remain_uncredited_and_unregistered(self):
        source_lock_path = REPO_ROOT / "host-kernel/rocky/source-lock.json"
        source_lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
        self.assertEqual(
            source_lock["gate"],
            {
                "credit_eligible": False,
                "gate_id": "RK-001",
                "policy": (
                    "Credit is forbidden while any required evidence or the complete "
                    "license inventory is missing or unverified."
                ),
            },
        )
        self.assertNotIn(
            "rk001-license-decisions-ef58-v1.json",
            source_lock_path.read_text(encoding="utf-8"),
        )
        tracker = (REPO_ROOT / "final-push.txt").read_text(encoding="utf-8")
        self.assertIn("GATE|RK-001|WS10|75|TODO|-|", tracker)
        self.assertNotIn("GATE|RK-001|WS10|75|PASS|", tracker)

    def test_cli_reports_todo_and_false_credit(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "rocky_kernel_license_decisions.py"),
                "--artifact",
                str(self.artifact_path()),
            ],
            cwd=str(REPO_ROOT),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        output = completed.stdout.decode("ascii")
        self.assertIn("items=115265", output)
        self.assertIn("machine_classified=72616", output)
        self.assertIn("unresolved=42649", output)
        self.assertIn("gate=TODO credit=false", output)


if __name__ == "__main__":
    unittest.main()
