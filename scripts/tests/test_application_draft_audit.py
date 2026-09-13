"""Evidence-integrity and literal-input regressions for the draft-only auditor."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("application_draft_audit", ROOT / "scripts/application-tests/audit_drafts.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class FrozenDraftAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit.audit(ROOT)

    def test_complete_immutable_accounting_has_no_acceptance_credit(self):
        counts = self.result["counts"]
        self.assertEqual((counts["packets"], counts["cases"]), (97, 273))
        self.assertEqual(counts["draft_status"], {"DRAFTED": 6, "DRAFTED_WITH_UNRESOLVED": 267})
        self.assertEqual(counts["corrected_references"], 9)
        self.assertEqual(counts["report_metadata_discrepancies"], 1)
        self.assertFalse(self.result["runtime_authorized"])
        self.assertFalse(self.result["acceptance_credit"])
        self.assertEqual(self.result["application_tests_accepted"], 0)
        self.assertEqual(len({c["case_id"] for c in self.result["cases"]}), 273)
        self.assertTrue(all(c["acceptance_status"] == "not-verified" for c in self.result["cases"]))

    def test_every_question_is_preserved_and_conservatively_routed(self):
        original = json.loads((ROOT / audit.BASE / "queue-summary.json").read_text())
        questions = self.result["question_classifications"]
        self.assertEqual([q["text"] for q in questions], original["prioritized_max_questions"])
        self.assertEqual(len(questions), 220)
        self.assertEqual(self.result["counts"]["case_question_strings"], 273)
        self.assertTrue(all(q["resolution_status"] == "review-routing-only" for q in questions))
        self.assertTrue(all(q["evidence"] and q["tags"] for q in questions))

    def test_only_inspected_simulations_receive_a_source_verdict(self):
        reviewed = [c for c in self.result["cases"]
                    if c["fixture_inspection"]["status"] == "inspected-simulation-not-runtime-test"]
        self.assertEqual(len(reviewed), 22)
        self.assertTrue(all(c["family"] in {"failure", "exhaust"} for c in reviewed))
        other_source = [c for c in self.result["cases"]
                        if c["fixture_inspection"]["status"] == "not-semantically-reviewed"]
        self.assertEqual(len(other_source), 231)
        self.assertTrue(all(c["fixture_inspection"]["source_evidence"] for c in reviewed))

    def test_all_seven_length_discrepancies_remain_findings(self):
        got = {r["case_id"]: (r["declared_size"], r["observed_size"])
               for r in self.result["input_findings"]}
        self.assertEqual(got, {
            "app.cat-file": (24, 36), "app.cp": (160, 176),
            "app.sort-numeric": (40960, 36864), "app.head": (800, 900),
            "app.tail": (800, 900), "app.zstd-decompress": (41, 42),
            "app.bash-pipeline": (224, 240),
        })
        self.assertEqual(self.result["counts"]["input_specifications"], 20)

    def test_audit_is_deterministic_and_inputs_remain_unchanged(self):
        second = audit.audit(ROOT)
        self.assertEqual(audit.canonical(self.result), audit.canonical(second))
        reader = audit.Reader(ROOT)
        for identity in self.result["inputs"]:
            reader.verify(identity)


class BoundaryTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(audit.AuditError, "duplicate JSON key"):
            audit.load_json('{"size":24,"size":36}')

    def test_literal_utf8_does_not_silently_decode_backslash_n(self):
        value = audit.generated_bytes({"kind": "repeat-utf8", "text": "copy-data\\n", "count": 16})
        self.assertEqual(value, b"copy-data\\n" * 16)
        self.assertEqual(len(value), 176)

    def test_numbered_and_numeric_generators_preserve_boundaries(self):
        self.assertEqual(audit.generated_bytes({"kind": "numbered-lines", "first": 1, "last": 2,
                                               "width": 3, "prefix": "line-", "newline": True}),
                         b"line-001\nline-002\n")
        self.assertEqual(audit.generated_bytes({"kind": "descending-padded-integers", "count": 3,
                                               "width": 2, "newline": True}), b"03\n02\n01\n")

    def test_unknown_ambiguous_or_oversized_inputs_are_rejected(self):
        for value in [
            {"stdin": {"hex": "00", "generator": {"kind": "repeat-byte", "hex_byte": "00", "count": 1}}},
            {"stdin": {"generator": {"kind": "unspecified"}}},
            {"stdin": {"generator": {"kind": "repeat-byte", "hex_byte": "00", "count": audit.MAX_INPUT_BYTES + 1}}},
            {"stdin": {"hex": "0"}}, {"stdin": {"hex": "00 01"}},
            {"stdin": {"hex": "00", "size": True}},
        ]:
            with self.subTest(value=value), self.assertRaises(audit.AuditError):
                audit.input_observations(value)

    def test_declared_content_hash_mismatch_is_reported(self):
        rows = audit.input_observations({"stdin": {"hex": "00", "sha256": "0" * 64}})
        self.assertFalse(rows[0]["sha256_matches"])
        self.assertEqual(rows[0]["content_sha256"], audit.digest(b"\x00"))

    def test_reader_rejects_stale_hash_symlinks_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real").write_bytes(b"unchanged")
            (root / "link").symlink_to("real")
            reader = audit.Reader(root)
            for path in ["link", "../real", "/real", "./real"]:
                with self.subTest(path=path), self.assertRaises(audit.AuditError):
                    reader.read(path)
            with self.assertRaisesRegex(audit.AuditError, "hash mismatch"):
                reader.verify({"path": "real", "sha256": "0" * 64})
            reader = audit.Reader(root)
            reader.read("real")
            (root / "real").write_bytes(b"changed")
            with self.assertRaisesRegex(audit.AuditError, "changed during audit"):
                reader.recheck()

    def test_corrections_require_exact_original_report_and_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "correct").write_bytes(b"oracle")
            original = {"path": "wrong", "sha256": audit.digest(b"oracle")}
            correction = {"report_sha256": audit.digest(b"report"), "original": original,
                          "resolved": {"path": "correct", "sha256": audit.digest(b"oracle")},
                          "reason": "explicit independently inspected correction"}
            resolved, changed = audit.resolve_reference(audit.Reader(root), "report.json", b"report", 0,
                                                        original, {("report.json", 0): correction})
            self.assertTrue(changed)
            self.assertEqual(resolved["path"], "correct")
            with self.assertRaisesRegex(audit.AuditError, "report binding"):
                audit.resolve_reference(audit.Reader(root), "report.json", b"edited", 0,
                                        original, {("report.json", 0): correction})
            with self.assertRaisesRegex(audit.AuditError, "original reference"):
                audit.resolve_reference(audit.Reader(root), "report.json", b"report", 0,
                                        {"path": "other", "sha256": original["sha256"]},
                                        {("report.json", 0): correction})
            with self.assertRaisesRegex(audit.AuditError, "missing regular input"):
                audit.resolve_reference(audit.Reader(root), "report.json", b"report", 1, original,
                                        {("report.json", 0): correction})


if __name__ == "__main__":
    unittest.main()
