"""A current-state index must preserve scopes and reject stale accounting."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("verification_state", ROOT / "scripts/application-tests/verification_state.py")
state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state)


class StateCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = state.build_state(ROOT)

    def test_all_original_gates_and_denominators_are_retained(self):
        production = self.value["native_production"]
        self.assertEqual(len(production["gates"]), 130)
        self.assertEqual(len({g["ident"] for g in production["gates"]}), 130)
        self.assertEqual((production["earned_points"], production["total_points"], production["percent"]),
                         (350, 10000, 3.5))
        self.assertEqual(production["status_counts"], {"PASS": 6, "IN_PROGRESS": 1, "TODO": 123, "BLOCKED": 0})
        self.assertTrue(all(g["dimensions"]["acceptance"] == g["status"] for g in production["gates"]))
        self.assertTrue(all(g["dimensions"]["runtime"] == "not-inferred" for g in production["gates"]))
        self.assertEqual(len(self.value["language"]["gates"]), 7)
        self.assertEqual(self.value["language"]["status_counts"], {"IN_PROGRESS": 3, "TODO": 4})
        self.assertIsNone(self.value["combined_whole_os_percentage"])

    def test_every_tracker_current_table_and_case_is_present(self):
        trackers = {r["path"]: r for r in self.value["trackers"]}
        self.assertEqual(set(trackers), set(state.TRACKERS))
        for name, count in [("overview.txt", 12), ("overview2.txt", 12), ("full-port.txt", 11),
                            ("rust-source-retirement.txt", 11), ("VALIDATION_PROGRESS.MD", 10)]:
            self.assertEqual(len(trackers[name]["rows"]), count, name)
        self.assertEqual(len(trackers["migration.txt"]["standalone_rows"]), 5)
        self.assertEqual(len(trackers["migration.txt"]["core_rows"]), 9)
        app = self.value["applications"]
        self.assertEqual(len(app["cases"]), 273)
        self.assertEqual(len({r["case_id"] for r in app["cases"]}), 273)
        self.assertEqual(len(app["question_classifications"]), 220)
        self.assertEqual(len(app["input_findings"]), 7)
        self.assertEqual(app["accepted_catalog_cases"], 0)
        for row in app["cases"]:
            self.assertEqual(set(row["dimensions"]), {"implementation", "review", "build", "runtime", "acceptance"})
            self.assertEqual(row["dimensions"]["acceptance"], "not-verified")

    def test_baselines_and_infrastructure_are_separate_from_acceptance(self):
        self.assertEqual(len(self.value["historical_baselines"]), 2)
        for row in self.value["historical_baselines"]:
            self.assertFalse(row["catalog_acceptance_credit"])
            self.assertFalse(row["current_runtime_replayed_by_this_index"])
        self.assertEqual(len(self.value["infrastructure_records"]), 2)
        self.assertTrue(all(not r["promotes_production_language_or_application_gate"]
                            for r in self.value["infrastructure_records"]))
        for row in self.value["infrastructure_sources"]:
            self.assertFalse(row["test_source_is_test_result"])
            self.assertEqual(row["dimensions"]["acceptance"], "not-verified")

    def test_snapshot_is_deterministic_and_all_bound_bytes_remain_exact(self):
        self.assertEqual(self.value, state.build_state(ROOT))
        for identity in self.value["inputs"]:
            import hashlib
            content = (ROOT / identity["path"]).read_bytes()
            self.assertEqual(len(content), identity["size"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), identity["sha256"])


class StateBoundaryTests(unittest.TestCase):
    def language_text(self):
        return (ROOT / state.LANGUAGE).read_text()

    def test_language_omission_duplication_and_unknown_status_fail(self):
        text = self.language_text()
        first = next(l for l in text.splitlines() if l.startswith("| MK-LANG-001 |"))
        for altered in [text.replace(first, ""), text + "\n" + first,
                        text.replace("| IN_PROGRESS:", "| ACCEPTED:", 1)]:
            with self.subTest(altered=altered[-80:]), self.assertRaises(state.StateError):
                state.parse_language(altered)

    def test_missing_tracker_claim_or_table_is_not_assumed_complete(self):
        with self.assertRaises(state.StateError):
            state.excerpt("no score here", r"^OVERALL COMPLETION")
        with self.assertRaises(state.StateError):
            state.table_rows("heading\nno rows", "heading", r"^(gate) (PASS)$")

    def test_linked_pass_record_cannot_promote_any_gate(self):
        row = state.infrastructure_record({"path": "untrusted.json", "sha256": "0" * 64, "size": 1},
                                          {"status": "PASS", "production_gate_credit": True,
                                           "application_catalog_passed": 273})
        self.assertEqual(row["recorded_status"], "PASS")
        self.assertFalse(row["promotes_production_language_or_application_gate"])
        self.assertNotIn("earned_points", row)
        self.assertNotIn("acceptance", row)

    def test_existing_output_and_symlink_are_not_overwritten(self):
        fixture = {"status": "EVIDENCE_INDEX_ONLY", "trackers": [],
                   "native_production": {"gate_count": 130, "earned_points": 350},
                   "language": {"gates": []}, "applications": {"cases": [], "accepted_catalog_cases": 0}}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing.json"
            target.write_bytes(b"original")
            link = Path(directory) / "link.json"
            link.symlink_to(target)
            with mock.patch.object(state, "build_state", return_value=fixture):
                for path in [target, link]:
                    with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                        self.assertEqual(state.main(["--output", str(path)]), 1)
                    self.assertEqual(target.read_bytes(), b"original")

    def test_check_rejects_modified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            target.write_text('{}\n')
            with mock.patch.object(state, "build_state", return_value={"different": True}):
                with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                    self.assertEqual(state.main(["--check", str(target)]), 1)


if __name__ == "__main__":
    unittest.main()
