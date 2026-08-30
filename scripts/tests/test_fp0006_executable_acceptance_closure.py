#!/usr/bin/env python3
"""Adversarial tests for the noncrediting FP-0006 acceptance census."""

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fp0006_executable_acceptance_closure as closure

REAL_SUBPROCESS_RUN = subprocess.run


class AcceptanceClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_bytes = (
            ROOT / closure.CONTRACT_PATH
        ).read_bytes()
        cls.contract = closure.load_json(cls.contract_bytes, "test contract")
        legacy_path = cls.contract["frozen_inputs"]["legacy_behavior_authority"][
            "path"
        ]
        cls.legacy = closure.load_json(
            (ROOT / legacy_path).read_bytes(), "test legacy authority"
        )
        negative_path = cls.contract["frozen_inputs"]["negative_dispatch_reference"][
            "path"
        ]
        cls.negative = closure.load_json(
            (ROOT / negative_path).read_bytes(), "test negative reference"
        )

    @classmethod
    def run_public(cls, repo=ROOT, expect_success=True, **kwargs):
        command = [
            sys.executable,
            "-I",
            str(ROOT / "scripts/fp0006_executable_acceptance_closure.py"),
            "--repo",
            str(repo),
        ]
        option_names = {
            "failure_flows": "--failure-flows",
            "failure_semantics_v3": "--failure-semantics-v3",
            "failure_sites": "--failure-sites",
            "runtime_result_authority": "--runtime-result-authority",
            "semantic_review_v3": "--semantic-review-v3",
        }
        for name in sorted(kwargs):
            if name not in option_names:
                raise TypeError("unexpected test option: {0}".format(name))
            command.extend([option_names[name], kwargs[name]])
        process = REAL_SUBPROCESS_RUN(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            universal_newlines=True,
        )
        if not expect_success:
            return process
        if process.returncode != 0:
            raise AssertionError(process.stderr)
        return json.loads(process.stdout)

    def test_contract_is_canonical_and_self_anchored(self):
        self.assertEqual(self.contract_bytes, closure.pretty_bytes(self.contract))
        self.assertEqual(len(self.contract_bytes), closure.EXPECTED_CONTRACT_SIZE)
        self.assertEqual(
            hashlib.sha256(self.contract_bytes).hexdigest(),
            closure.EXPECTED_CONTRACT_SHA256,
        )

    def test_exact_census_succeeds_without_external_rows(self):
        result = self.run_public()
        census = result["declarative_census"]
        self.assertEqual(census["behavior_declaration_count"], 1326)
        self.assertEqual(census["acceptance_test_declaration_count"], 1326)
        self.assertEqual(census["compiler_failure_site_reference_count"], 971)
        self.assertEqual(census["bounded_failure_flow_reference_count"], 2602)
        self.assertEqual(census["c_semantic_question_reference_count"], 205)
        self.assertEqual(census["rust_mir_site_reference_count"], 420)
        self.assertEqual(
            census[
                "direct_strong_same_module_ctu_structural_inventory_"
                "reference_status"
            ],
            "required-missing",
        )
        self.assertIn(
            "direct_strong_same_module_ctu_structural_inventory",
            result["required_missing"],
        )
        self.assertIs(census["declarative_behavior_acceptance_join_complete"], True)
        self.assertEqual(result["execution_census"]["runtime_result_count"], 0)
        self.assertEqual(
            result["execution_census"]["result_authority_status"],
            "required-missing",
        )

    def test_every_completion_or_credit_claim_is_exact_false(self):
        result = self.run_public()
        self.assertEqual(set(result["claims"]), set(closure._false_claims()))
        for value in result["claims"].values():
            self.assertIs(type(value), bool)
            self.assertIs(value, False)
        self.assertEqual(
            result["gate"],
            {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
        )

    def test_declarative_ids_are_not_reported_as_results(self):
        result = self.run_public()
        self.assertIs(result["execution_census"]["declarative_ids_are_results"], False)
        self.assertEqual(result["execution_census"]["runtime_result_count"], 0)
        self.assertEqual(
            result["joins"]["behavior_to_acceptance_declarations"]["kind"],
            "declarative-only",
        )
        for name in (
            "declarations_to_compiler_sites",
            "failure_flows_to_executable_results",
            "full_cross_authority_join",
            "semantic_rows_to_runtime_results",
        ):
            self.assertIs(result["joins"][name]["complete"], False)
            self.assertEqual(result["joins"][name]["status"], "required-missing")

    def test_exact_integer_rejects_bool(self):
        contract = copy.deepcopy(self.contract)
        contract["schema_version"] = True
        with self.assertRaisesRegex(closure.ClosureError, "schema version"):
            closure.validate_contract(contract)
        with self.assertRaisesRegex(closure.ClosureError, "exact integer"):
            closure.require_int(False, "count")

    def test_false_claim_cannot_be_promoted(self):
        contract = copy.deepcopy(self.contract)
        contract["claims"]["gate_pass"] = True
        with self.assertRaisesRegex(closure.ClosureError, "claims must all remain false"):
            closure.validate_contract(contract)

        negative = copy.deepcopy(self.negative)
        negative["claims"]["gate_pass"] = True
        inputs = self.contract["frozen_inputs"]
        with self.assertRaisesRegex(closure.ClosureError, "must remain.*false"):
            closure.validate_negative_reference(
                negative,
                inputs["negative_dispatch_reference"],
                inputs["compiler_failure_site_authority"],
                inputs["bounded_failure_flow_authority"],
            )

    def test_required_missing_cannot_be_promoted(self):
        contract = copy.deepcopy(self.contract)
        contract["frozen_inputs"]["compiler_failure_site_authority"][
            "artifact_availability"
        ] = "committed"
        with self.assertRaisesRegex(closure.ClosureError, "availability overclaims"):
            closure.validate_contract(contract)

    def test_ctu_inventory_cannot_gain_authority_or_change_gate(self):
        metadata = self.contract["frozen_inputs"]["semantic_evidence_authority"]
        inventory = metadata["direct_ctu_structural_inventory"]
        self.assertIs(inventory["fresh_execution_authority"], False)
        self.assertEqual(inventory["status"], "required-missing")
        self.assertNotIn("required_status", inventory)
        self.assertEqual(
            inventory["blocker_retained"],
            "cross_translation_unit_call_graph_not_linked",
        )
        for field, value in (
            ("fresh_execution_authority", True),
            ("status", "presented-raw"),
            ("artifact_availability", "committed"),
        ):
            with self.subTest(field=field):
                hostile = copy.deepcopy(self.contract)
                hostile["frozen_inputs"]["semantic_evidence_authority"][
                    "direct_ctu_structural_inventory"
                ][field] = value
                with self.assertRaisesRegex(
                    closure.ClosureError, "structural inventory"
                ):
                    closure.validate_contract(hostile)
        hostile = copy.deepcopy(self.contract)
        hostile["frozen_inputs"]["semantic_evidence_authority"][
            "direct_ctu_structural_inventory"
        ]["required_status"] = (
            "direct_strong_same_module_cross_translation_unit_call_graph_"
            + "li" + "nked"
        )
        with self.assertRaisesRegex(
            closure.ClosureError, "structural inventory"
        ):
            closure.validate_contract(hostile)
        result = self.run_public()
        self.assertFalse(any(result["claims"].values()))
        self.assertEqual(
            result["gate"],
            {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
        )

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaisesRegex(closure.ClosureError, "duplicate JSON key"):
            closure.load_json(b'{"a":1,"a":2}\n', "duplicate")

    def test_nonfinite_json_is_rejected(self):
        with self.assertRaisesRegex(closure.ClosureError, "non-finite JSON"):
            closure.load_json(b'{"a":NaN}\n', "nonfinite")

    def test_canonical_id_digest_is_order_independent(self):
        self.assertEqual(
            closure._id_set_digest(["BHV-B", "BHV-A"]),
            closure._id_set_digest(["BHV-A", "BHV-B"]),
        )
        self.assertEqual(
            closure._pair_set_digest([("B", "2"), ("A", "1")]),
            closure._pair_set_digest([("A", "1"), ("B", "2")]),
        )

    def test_duplicate_behavior_id_is_rejected(self):
        legacy = copy.deepcopy(self.legacy)
        legacy["behaviors"][-1]["id"] = legacy["behaviors"][0]["id"]
        metadata = self.contract["frozen_inputs"]["legacy_behavior_authority"]
        with self.assertRaisesRegex(closure.ClosureError, "duplicated"):
            closure.validate_legacy_authority(legacy, metadata)

    def test_declaration_edge_mutation_is_rejected(self):
        legacy = copy.deepcopy(self.legacy)
        legacy["acceptance_tests"][0]["behavior_ids"] = [
            legacy["behaviors"][1]["id"]
        ]
        metadata = self.contract["frozen_inputs"]["legacy_behavior_authority"]
        with self.assertRaisesRegex(closure.ClosureError, "do not join"):
            closure.validate_legacy_authority(legacy, metadata)

    def test_wrong_external_path_is_rejected(self):
        process = self.run_public(
            expect_success=False, failure_sites="evidence/wrong.json"
        )
        self.assertEqual(process.returncode, 1)
        self.assertIn("exact frozen path", process.stderr)

    def test_unfrozen_semantic_artifact_is_rejected(self):
        path = self.contract["frozen_inputs"]["semantic_evidence_authority"][
            "artifact"
        ]["path"]
        process = self.run_public(expect_success=False, failure_semantics_v3=path)
        self.assertEqual(process.returncode, 1)
        self.assertIn("no frozen digest/size", process.stderr)

    def test_unfrozen_runtime_result_authority_is_rejected(self):
        process = self.run_public(
            expect_success=False, runtime_result_authority="result.json"
        )
        self.assertEqual(process.returncode, 1)
        self.assertIn("no frozen path/digest", process.stderr)

    def test_external_identity_is_checked_before_json_parse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = "ci/evidence/sites.json"
            target = root / path
            target.parent.mkdir(parents=True)
            target.write_bytes(b'{"duplicate":1,"duplicate":2}\n')
            metadata = {
                "path": path,
                "sha256": "0" * 64,
                "size": target.stat().st_size,
            }
            called = []
            with closure.RepositorySnapshot(root) as snapshot:
                with self.assertRaisesRegex(closure.ClosureError, "SHA-256 changed"):
                    closure._present_external(
                        snapshot,
                        path,
                        metadata,
                        "external",
                        lambda value: called.append(value),
                    )
            self.assertEqual(called, [])

    def test_symlink_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "real.json").write_text("{}\n", encoding="utf-8")
            (root / "link.json").symlink_to("real.json")
            with closure.RepositorySnapshot(root) as snapshot:
                with self.assertRaisesRegex(closure.ClosureError, "without following links"):
                    snapshot.read("link.json", "link")

    def test_symlink_directory_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "real").mkdir()
            (root / "real" / "value.json").write_text("{}\n", encoding="utf-8")
            (root / "alias").symlink_to("real", target_is_directory=True)
            with closure.RepositorySnapshot(root) as snapshot:
                with self.assertRaisesRegex(closure.ClosureError, "without following links"):
                    snapshot.read("alias/value.json", "directory link")

    def test_hardlink_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.json"
            linked = root / "linked.json"
            original.write_text("{}\n", encoding="utf-8")
            os.link(str(original), str(linked))
            with closure.RepositorySnapshot(root) as snapshot:
                with self.assertRaisesRegex(closure.ClosureError, "hard-linked"):
                    snapshot.read("linked.json", "hard link")

    def test_mutation_during_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "large.bin"
            target.write_bytes(b"A" * 131072)
            original_read = closure.os.read
            mutated = [False]

            def hooked_read(descriptor, count):
                data = original_read(descriptor, count)
                if data and not mutated[0]:
                    mutated[0] = True
                    target.write_bytes(b"B" * 17)
                return data

            with closure.RepositorySnapshot(root) as snapshot:
                with mock.patch.object(closure.os, "read", side_effect=hooked_read):
                    with self.assertRaisesRegex(
                        closure.ClosureError, "ended before|changed while"
                    ):
                        snapshot.read("large.bin", "mutating input")

    def test_aggregate_mutation_after_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.json"
            second = root / "second.json"
            first.write_text('{"a":1}\n', encoding="utf-8")
            second.write_text('{"b":2}\n', encoding="utf-8")
            with closure.RepositorySnapshot(root) as snapshot:
                snapshot.read("first.json", "first")
                snapshot.read("second.json", "second")
                first.write_text('{"a":3}\n', encoding="utf-8")
                with self.assertRaisesRegex(closure.ClosureError, "aggregate decision"):
                    snapshot.finalize()

    def test_path_replacement_after_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "value.json"
            replacement = root / "replacement.json"
            target.write_text('{"a":1}\n', encoding="utf-8")
            replacement.write_text('{"a":1}\n', encoding="utf-8")
            replaced = [False]
            with closure.RepositorySnapshot(root) as snapshot:
                snapshot.read("value.json", "value")
                os.replace(str(replacement), str(target))
                replaced[0] = True
                with self.assertRaisesRegex(
                    closure.ClosureError,
                    "path identity changed|value\\.json changed before aggregate decision",
                ):
                    snapshot.finalize()
            self.assertIs(replaced[0], True)

    def test_self_oracle_global_rebinding_does_not_change_anchor(self):
        with mock.patch.object(closure, "EXPECTED_CONTRACT_SHA256", "0" * 64), mock.patch.object(
            closure, "EXPECTED_CONTRACT_SIZE", 1
        ), mock.patch.object(closure, "CONTRACT_PATH", "attacker.json"):
            result = self.run_public()
        self.assertEqual(
            result["contract"]["sha256"],
            "52e8c45f6909e78db8919b78213aac4728d3a5157f6c270193338ec66de60707",
        )
        self.assertEqual(result["contract"]["size"], 5938)

    def test_no_public_build_census_callable_authority_exists(self):
        self.assertFalse(hasattr(closure, "build_census"))

    def test_exact_prior_closure_cell_attack_is_unavailable(self):
        with self.assertRaises(AttributeError):
            code = closure.build_census.__code__
            freevars = code.co_freevars
            closure.build_census.__closure__[freevars.index("builder")].cell_contents = (
                lambda *args, **kwargs: {
                    "claims": {"gate_pass": True, "credit_eligible": True},
                    "gate": {"gate_id": "FP-0006", "points_awarded": 50, "status": "PASS"},
                }
            )

    def test_exact_prior_class_call_code_attack_is_unavailable(self):
        with self.assertRaises(AttributeError):
            call = type(closure.build_census).__call__
            call.__code__ = (lambda: None).__code__

    def test_mutable_claim_factory_cannot_promote_output(self):
        promoted = dict(self.contract["claims"])
        promoted["gate_pass"] = True
        promoted["credit_eligible"] = True
        with mock.patch.object(closure, "_false_claims", return_value=promoted) as factory:
            result = self.run_public()
        self.assertEqual(factory.call_count, 0)
        self.assertFalse(any(result["claims"].values()))

    def test_rebound_contract_validator_cannot_mutate_emitted_claims(self):
        original = closure.validate_contract

        def promote(contract):
            inputs = original(contract)
            contract["claims"]["gate_pass"] = True
            contract["claims"]["credit_eligible"] = True
            return inputs

        with mock.patch.object(
            closure, "validate_contract", side_effect=promote
        ) as rebound:
            result = self.run_public()
        self.assertEqual(rebound.call_count, 0)
        self.assertIs(result["claims"]["gate_pass"], False)
        self.assertIs(result["claims"]["credit_eligible"], False)
        self.assertEqual(result["gate"]["points_awarded"], 0)

    def test_rebound_internal_builder_cannot_replace_public_builder(self):
        promoted = {"claims": {"gate_pass": True, "credit_eligible": True}}
        with mock.patch.object(
            closure, "_build_census_anchored", return_value=promoted
        ) as rebound:
            result = self.run_public()
        self.assertEqual(rebound.call_count, 0)
        self.assertFalse(any(result["claims"].values()))

    def test_replaced_worker_code_is_not_inherited_by_fresh_exec(self):
        original_code = closure._build_census_anchored.__code__

        def promoted_worker(*args, **kwargs):
            return {
                "claims": {"gate_pass": True, "credit_eligible": True},
                "gate": {"gate_id": "FP-0006", "points_awarded": 50, "status": "PASS"},
            }

        try:
            closure._build_census_anchored.__code__ = promoted_worker.__code__
            result = self.run_public()
        finally:
            closure._build_census_anchored.__code__ = original_code
        self.assertFalse(any(result["claims"].values()))
        self.assertEqual(result["gate"]["points_awarded"], 0)

    def test_replaced_emitter_code_is_not_inherited_by_fresh_cli(self):
        original_code = closure._PublicCensusEmitter.emit.__code__

        def promoted_emit(self, repo, output, *args, **kwargs):
            return {
                "claims": {"gate_pass": True, "credit_eligible": True},
                "gate": {"gate_id": "FP-0006", "points_awarded": 50, "status": "PASS"},
            }

        try:
            closure._PublicCensusEmitter.emit.__code__ = promoted_emit.__code__
            result = self.run_public()
        finally:
            closure._PublicCensusEmitter.emit.__code__ = original_code
        self.assertFalse(any(result["claims"].values()))
        self.assertEqual(result["gate"]["points_awarded"], 0)

    def test_imported_emitter_rejects_patched_serializer_and_output_sinks(self):
        promoted = {
            "claims": {"gate_pass": True, "credit_eligible": True},
            "gate": {"gate_id": "FP-0006", "points_awarded": 50, "status": "PASS"},
        }
        serializer = mock.Mock(return_value=closure.canonical_bytes(promoted))
        atomic_output = mock.Mock()
        stdout = mock.Mock()
        builder = mock.Mock(return_value=promoted)
        with tempfile.TemporaryDirectory() as temporary:
            output = str(Path(temporary) / "promoted.json")
            with mock.patch.object(closure, "pretty_bytes", serializer), mock.patch.object(
                closure, "_atomic_write", atomic_output
            ), mock.patch.object(closure, "_build_census_anchored", builder), mock.patch.object(
                closure, "__name__", "__main__"
            ), mock.patch.object(closure.sys, "stdout", stdout):
                for destination in (None, output):
                    with self.subTest(destination=destination):
                        with self.assertRaisesRegex(
                            closure.ClosureError, "only from a fresh CLI interpreter"
                        ):
                            closure._PublicCensusEmitter().emit(ROOT, destination)
        serializer.assert_not_called()
        atomic_output.assert_not_called()
        builder.assert_not_called()
        stdout.write.assert_not_called()

    def test_fake_worker_protocol_cannot_promote_claims(self):
        promoted = {
            "claims": {"gate_pass": True, "credit_eligible": True},
            "gate": {"gate_id": "FP-0006", "points_awarded": 50, "status": "PASS"},
        }
        fake = mock.Mock(
            returncode=0,
            stderr=b"",
            stdout=closure.canonical_bytes(promoted),
        )
        with mock.patch.object(closure.subprocess, "run", return_value=fake):
            result = self.run_public()
        self.assertFalse(any(result["claims"].values()))
        self.assertEqual(result["gate"]["points_awarded"], 0)

    def test_rebound_global_comparator_cannot_accept_promoted_protocol(self):
        promoted = self.run_public()
        promoted["joins"]["full_cross_authority_join"] = {
            "complete": True,
            "status": "PASS",
        }
        fake = mock.Mock(
            returncode=0,
            stderr=b"",
            stdout=closure.canonical_bytes(promoted),
        )
        with mock.patch.object(closure, "strict_equal", return_value=True), mock.patch.object(
            closure.subprocess, "run", return_value=fake
        ):
            result = self.run_public()
        self.assertFalse(any(result["claims"].values()))
        self.assertIs(result["joins"]["full_cross_authority_join"]["complete"], False)

    def test_modified_contract_cannot_bless_itself(self):
        modified = bytearray(self.contract_bytes)
        modified[-2:-1] = b" "
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / closure.CONTRACT_PATH
            target.parent.mkdir(parents=True)
            target.write_bytes(bytes(modified))
            attacker_digest = hashlib.sha256(bytes(modified)).hexdigest()
            with mock.patch.object(
                closure, "EXPECTED_CONTRACT_SHA256", attacker_digest
            ), mock.patch.object(closure, "EXPECTED_CONTRACT_SIZE", len(modified)):
                process = self.run_public(root, expect_success=False)
        self.assertEqual(process.returncode, 1)
        self.assertIn("SHA-256 changed", process.stderr)

    def test_python_36_grammar(self):
        for relative in (
            "scripts/fp0006_executable_acceptance_closure.py",
            "scripts/tests/test_fp0006_executable_acceptance_closure.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                ast.parse(source, filename=relative, feature_version=(3, 6))
            else:
                ast.parse(source, filename=relative)

    def test_cli_emits_noncrediting_result(self):
        command = [
            sys.executable,
            "-I",
            str(ROOT / "scripts/fp0006_executable_acceptance_closure.py"),
            "--repo",
            str(ROOT),
        ]
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            universal_newlines=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["gate"]["status"], "IN_PROGRESS")
        self.assertIn("required-missing", process.stderr)
        self.assertFalse(any(result["claims"].values()))


if __name__ == "__main__":
    unittest.main()
