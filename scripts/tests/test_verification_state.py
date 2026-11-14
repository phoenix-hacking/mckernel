"""A current-state index must preserve scopes and reject stale accounting."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import tarfile
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


class ReviewedCompilationTests(unittest.TestCase):
    compile_path = "docs/verification/stability-packet001-compile-20260913-1.json"
    retention_path = "docs/verification/stability-review-retention-20260913-1.json"
    helper_review_path = "docs/verification/stability-compile-helper-review-20260913.json"

    def reader(self):
        auditor = state.module_from_path("state_test_reader", ROOT / "scripts/application-tests/audit_drafts.py")
        return auditor.Reader(ROOT)

    def review(self, change=None, *, retention_change=None, omit_helper=False,
               independent_review_change=None, helper_review_change=None):
        reader = self.reader()
        original_json = reader.json

        def document(path):
            value = original_json(path)
            if path == self.compile_path and change:
                change(value)
            if path == self.retention_path and retention_change:
                retention_change(value)
            if path == "docs/verification/stability-packet001-review-20260913.json" and independent_review_change:
                independent_review_change(value)
            if path == self.helper_review_path and helper_review_change:
                helper_review_change(value)
            return value

        reader.json = document
        retentions = state.load_retentions(reader, [self.retention_path])
        infrastructure = [] if omit_helper else [(self.helper_review_path, reader.json(self.helper_review_path))]
        return state.reviewed_compilations(reader, [self.compile_path], retentions, infrastructure)

    def test_three_actual_compiled_revisions_preserve_every_runtime_boundary(self):
        rows = self.review()
        self.assertEqual(set(rows), {"startup.argv-empty", "startup.environment", "startup.stdout-stderr"})
        for value in rows.values():
            self.assertEqual(value["dimensions"]["build"], "COMPILED")
            self.assertEqual(value["dimensions"]["runtime"], "NOT_RUN")
            self.assertEqual(value["dimensions"]["acceptance"], "NOT_VERIFIED")
            self.assertFalse(value["runtime_authorized"])
            self.assertFalse(value["application_acceptance"])
            self.assertEqual(value["retention"]["verified_regular_files"], 47)
            self.assertEqual(value["retention"]["verified_tree_members"], 58)

    def test_compile_record_cannot_award_runtime_or_acceptance(self):
        for field in ("linux_reference_executed", "mckernel_application_executed", "application_acceptance", "production_gate_credit"):
            with self.subTest(field=field), self.assertRaisesRegex(state.StateError, "cannot promote"):
                self.review(lambda document: document.update({field: True}))
        with self.assertRaisesRegex(state.StateError, "did not complete"):
            self.review(lambda document: document.update(status="FAIL"))
        with self.assertRaisesRegex(state.StateError, "compile environment differs"):
            self.review(lambda document: document["command_environment"].update(TMPDIR="/tmp/unreviewed"))

    def test_compilation_requires_independent_helper_and_unique_selected_cases(self):
        with self.assertRaisesRegex(state.StateError, "helper requires"):
            self.review(omit_helper=True)
        with self.assertRaisesRegex(state.StateError, "membership differs"):
            self.review(lambda document: document["cases"].append(copy.deepcopy(document["cases"][0])))

    def test_independent_review_requires_supported_schema_kind_and_status(self):
        for field, value in (("schema_version", True), ("schema_version", 2),
                             ("record_kind", "unreviewed"), ("status", "FAIL"), ("status", "PASS")):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(state.StateError, "independent review status/schema/kind"):
                self.review(independent_review_change=lambda row: row.update({field: value}))

    def test_compile_helper_review_requires_supported_schema_kind_and_status(self):
        for field, value in (("schema_version", True), ("schema_version", 2), ("status", "FAIL"), ("status", "PASS")):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(state.StateError, "compile helper review status/schema"):
                self.review(helper_review_change=lambda row: row.update({field: value}))
        with self.assertRaisesRegex(state.StateError, "compile helper requires"):
            self.review(helper_review_change=lambda row: row.update(record_kind="unreviewed"))

    def test_compile_reviews_cannot_contradict_their_acceptance_boundaries(self):
        for field in ("application_acceptance", "production_gate_credit"):
            for value in (True, 0):
                with self.subTest(review="packet", field=field, value=value), self.assertRaisesRegex(state.StateError, "independent review cannot award"):
                    self.review(independent_review_change=lambda row: row.update({field: value}))
                with self.subTest(review="helper", field=field, value=value), self.assertRaisesRegex(state.StateError, "compile helper review cannot award"):
                    self.review(helper_review_change=lambda row: row.update({field: value}))

    def test_stale_packet_and_compiled_source_oracle_are_rejected(self):
        for field in ("packet", "independent_review"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.review(lambda document: document[field].update(sha256="0" * 64))
        for field in ("source", "oracle"):
            with self.subTest(field=field), self.assertRaisesRegex(state.StateError, "differs from independent review"):
                self.review(lambda document: document["cases"][0][field].update(sha256="0" * 64))

    def test_wrong_compiler_flags_and_failed_command_are_rejected(self):
        def wrong_flag(document):
            command = next(c for c in document["commands"] if c["label"] == "startup.argv-empty-compile")
            command["argv"][command["argv"].index("-std=c11")] = "-std=gnu11"
        with self.assertRaisesRegex(state.StateError, "changed compile/ELF command"):
            self.review(wrong_flag)
        with self.assertRaisesRegex(state.StateError, "failed compiler command"):
            self.review(lambda document: document["commands"][0].update(exit_code=1))

    def test_retention_must_match_record_and_preserve_complete_outputs(self):
        with self.assertRaisesRegex(state.StateError, "exactly one matching"):
            self.review(retention_change=lambda document: document["captures"][0]["record"].update(sha256="0" * 64))
        with self.assertRaisesRegex(state.StateError, "incomplete"):
            self.review(retention_change=lambda document: document["captures"][0].update(excludes=["payload"]))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.review(retention_change=lambda document: document["captures"][0]["archive"].update(sha256="0" * 64))

    def test_archive_links_traversal_duplicates_and_modified_bytes_are_rejected(self):
        for mode in ("link", "traversal", "dot", "duplicate", "bytes"):
            with self.subTest(mode=mode):
                reader = self.reader()
                record = reader.json(self.compile_path)
                retentions = state.load_retentions(reader, [self.retention_path])
                archive_ref = retentions[0]["document"]["captures"][0]["archive"]
                original = reader.verify(archive_ref)
                output = io.BytesIO()
                with tarfile.open(fileobj=io.BytesIO(original), mode="r:gz") as source, \
                        tarfile.open(fileobj=output, mode="w:gz") as changed:
                    altered = False
                    for member in source:
                        content = source.extractfile(member).read() if member.isfile() else None
                        if member.isfile() and not altered:
                            altered = True
                            if mode == "link":
                                member.type, member.linkname, member.size, content = tarfile.SYMTYPE, "/etc/passwd", 0, None
                            elif mode == "traversal":
                                member.name = "../outside"
                            elif mode == "dot":
                                member.name = "."
                            elif mode == "bytes":
                                content = bytes([content[0] ^ 1]) + content[1:]
                            elif mode == "duplicate":
                                changed.addfile(member, io.BytesIO(content))
                        changed.addfile(member, io.BytesIO(content) if content is not None else None)
                corrupted = output.getvalue()
                verify = reader.verify
                # Archive parser must reject these even if an upstream hash verifier were bypassed.
                reader.verify = lambda row: corrupted if row == archive_ref else verify(row)
                with self.assertRaises(state.StateError):
                    state.compile_capture(reader, self.compile_path, record, retentions)

    def test_invalid_elf_and_recorded_interpreter_are_rejected(self):
        for data in (b"not ELF", b"\x7fELF" + b"\0" * 60):
            with self.subTest(data=data[:8]), self.assertRaises(state.StateError):
                state.elf_interpreter(data)
        with self.assertRaisesRegex(state.StateError, "interpreter differs"):
            self.review(lambda document: document["cases"][0].update(interpreter="/unreviewed/loader"))

    def test_compiler_dependency_or_traced_library_omission_is_rejected(self):
        def omit_source(document):
            source = document["cases"][0]["source"]["path"]
            document["compiler_dependencies"] = [r for r in document["compiler_dependencies"] if r["path"] != source]
        with self.assertRaisesRegex(state.StateError, "dependency inventory is incomplete"):
            self.review(omit_source)
        with self.assertRaisesRegex(state.StateError, "closure differs from retained loader trace"):
            self.review(lambda document: document["cases"][0]["runtime_libraries"].pop())

    def test_decompressed_capture_bound_applies_to_tar_bytes(self):
        reader = self.reader()
        record = reader.json(self.compile_path)
        retentions = state.load_retentions(reader, [self.retention_path])
        bound = sum(row["size"] for row in record["outputs"]) + reader.inputs[self.compile_path]["size"] + 1
        with mock.patch.object(state, "MAX_COMPILE_CAPTURE_BYTES", bound), \
                self.assertRaisesRegex(state.StateError, "expanded compile archive exceeds"):
            state.compile_capture(reader, self.compile_path, record, retentions)

    def test_baseline_drift_is_historical_and_initial_snapshot_is_immutable(self):
        reader = self.reader()
        row = state.baseline_relation(reader, "docs/verification/stability-baseline-20260913.json")
        self.assertEqual(row["original_suites_passed"], 8)
        self.assertEqual(row["changed_source_paths"], ["host-kernel/native-rust/smp_application.rs", "host-kernel/native-rust/smp_service.rs"])
        self.assertFalse(row["current_source_acceptance"])
        self.assertFalse(row["catalog_acceptance_credit"])
        original = (ROOT / "docs/verification/stability-state-20260913.json").read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), "62bf12f91a2b2f5017623088d7c9eff404143fcf6d7c2fe732946eb9e30910f5")


if __name__ == "__main__":
    unittest.main()
