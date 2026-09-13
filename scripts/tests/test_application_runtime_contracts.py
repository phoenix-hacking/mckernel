#!/usr/bin/env python3
"""Synthetic metadata tests; fixture artifacts are never execution evidence."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "application-tests" / "runtime_contracts.py"
SPEC = importlib.util.spec_from_file_location("application_runtime_contracts", SOURCE)
contracts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contracts)
CATALOG = json.loads(SOURCE.with_name("cases.json").read_text())
KNOWN = {case["id"]: case for case in CATALOG["cases"]}


class MetadataFixture:
    """Build internally bound toy files; none are actual modules or programs."""

    def __init__(self, directory, case_ids=("startup.argv-empty",)):
        self.directory = directory
        self.serial = 0
        self.case_ids = case_ids
        self.proof = self.file("unit-test-proof.txt", b"SYNTHETIC UNIT TEST ONLY; no runtime evidence\n")
        artifacts = {name: self.file(name, (name + ": synthetic bytes\n").encode())
                     for name in ("linux_kernel", "mckernel_image", "launcher", "compiler")}
        artifacts["native_modules"] = [self.file(name, b"not a loadable module\n")
                                       for name in ("ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko")]
        profile = dict(contracts._INFRA, profile_id="baseline-root-1cpu", network="none",
                       uid=0, gid=0, groups=[0], umask="0022", qemu_argv=["/pinned/qemu", "-no-reboot"])
        self.inputs = {
            "schema_version": 1, "kind": "selected-inputs",
            "source": {"commit": "1" * 40, "dirty_diff": self.file("diff.patch", b""),
                       "compiler_bindings": self.proof},
            "artifacts": artifacts, "profile": profile, "payloads": {},
        }
        self.cases = []
        self.oracles = {}
        for case_id in case_ids:
            source = self.file(case_id + ".c", b"reviewed metadata test source; never compiled\n")
            executable = self.file(case_id + ".elf", b"not an executable; metadata test only\n")
            self.inputs["payloads"][case_id] = {
                "source": source, "executable": executable, "executable_path": "/apps/app",
                "argv": ["app", "A", "", "B"], "env": {"LC_ALL": "C"},
                "cwd": "/case/work", "interpreter": None, "dsos": [], "stdin": None,
            }
            self.oracles[case_id] = {
                "schema_version": 1, "kind": "independent-oracle", "case_id": case_id,
                "version": 1, "source_sha256": source["sha256"], "review_status": "REVIEWED",
                "wait_status": {"kind": "exited", "code": 0},
                "stdout": {"kind": "exact-bytes", "hex": b"A||B\n".hex()},
                "stderr": {"kind": "exact-bytes", "hex": ""}, "predicates": [],
            }
            self.cases.append({"case_id": case_id, "source": source, "oracle": None,
                               "review_status": "REVIEWED", "assertions_reviewed": True,
                               "parameters_reviewed": True, "limits": copy.deepcopy(KNOWN[case_id]["limits"])})
        self.required = set(CATALOG["global_execution_gates"])
        for case_id in case_ids:
            self.required.update(KNOWN[case_id]["requires"])
        self.cap_states = {}
        self.cap_overrides = {}
        self.evidence_overrides = {}
        self.caps_header_overrides = {}
        self.packet_overrides = {}

    def file(self, name, data):
        path = self.directory / name
        with path.open("xb") as stream:
            stream.write(data)
        return {"path": str(path), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def json_file(self, name, value):
        self.serial += 1
        return self.file("{}-{}.json".format(name, self.serial), json.dumps(value, sort_keys=True).encode())

    def build(self):
        inputs_ref = self.json_file("inputs", self.inputs)
        caps = {}
        for name in sorted(self.required):
            evidence = {"schema_version": 1, "kind": "capability-evidence", "status": "PASS",
                        "review_status": "REVIEWED", "selected_inputs_sha256": inputs_ref["sha256"],
                        "capability": name, "artifacts": [self.proof]}
            evidence.update(self.evidence_overrides.get(name, {}))
            state = self.cap_states.get(name, "verified")
            record = {"state": state, "contract": "synthetic validator unit test only",
                      "evidence": [self.json_file("capability-proof", evidence)]}
            if state != "verified":
                record["reason"] = "explicit synthetic missing capability"
            record.update(self.cap_overrides.get(name, {}))
            caps[name] = record
        caps_document = {"schema_version": 1, "kind": "runtime-capabilities",
                         "selected_inputs_sha256": inputs_ref["sha256"], "capabilities": caps}
        caps_document.update(self.caps_header_overrides)
        caps_ref = self.json_file("capabilities", caps_document)
        cases = copy.deepcopy(self.cases)
        for case in cases:
            case["oracle"] = self.json_file("oracle", self.oracles[case["case_id"]])
        packet = {"schema_version": 1, "kind": "execution-packet", "packet_id": "runtime-unit-fixture",
                  "version": 1, "catalog_sha256": hashlib.sha256(SOURCE.with_name("cases.json").read_bytes()).hexdigest(),
                  "selected_inputs_sha256": inputs_ref["sha256"], "capabilities_sha256": caps_ref["sha256"],
                  "mode": "differential-guest", "execution_enabled": True,
                  "review_status": "REVIEWED", "cases": cases}
        packet.update(self.packet_overrides)
        packet_ref = self.json_file("packet", packet)
        bundle_ref = self.json_file("bundle", {"schema_version": 1, "kind": "runtime-bundle",
                                              "selected_inputs": inputs_ref, "capabilities": caps_ref,
                                              "execution_packet": packet_ref})
        return Path(bundle_ref["path"])

    def report(self, stdout=b"A||B\n", stderr=b"", raw=0):
        payload = self.inputs["payloads"][self.case_ids[0]]
        wait = ({"kind": "exited", "code": os.WEXITSTATUS(raw)} if os.WIFEXITED(raw)
                else {"kind": "signaled", "signal": os.WTERMSIG(raw)})
        report = {"schema_version": 1, "status": "COMPLETED", "cleanup_complete": True,
                  "application_acceptance": False, "raw_wait_status": raw,
                  "wait_status": wait, "executable": payload["executable"],
                  "stdin": {"kind": "devnull"}, "timeout_seconds": 10.0,
                  "cleanup_timeout_seconds": 15.0, "streams": {},
                  "payload_monotonic_started": 100.0, "payload_monotonic_deadline": 110.0,
                  "payload_completion_observed_monotonic": 101.0}
        report.update({key: payload[key] for key in ("argv", "env", "cwd", "executable_path")})
        report.update({key: self.inputs["profile"][key] for key in ("uid", "gid", "groups", "umask")})
        for name, data in (("stdout", stdout), ("stderr", stderr)):
            self.serial += 1
            artifact = self.file("stream-{}-{}.bin".format(name, self.serial), data)
            report["streams"][name] = {"artifact": artifact, "eof": True, "truncated": False,
                                       "bytes_observed": len(data), "bytes_retained": len(data),
                                       "discarded_observed_bytes": 0, "limit_bytes": 65536}
        return report


class RuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="application-contract-test-"))

    def tearDown(self):
        result = self._outcome.result
        failed = any(test is self for test, _ in result.failures + result.errors)
        failed = failed or any(error is not None and
                               (test is self or getattr(test, "test_case", None) is self)
                               for test, error in getattr(self._outcome, "errors", ()))
        if failed:
            print("PRESERVED FAILED CONTRACT TEST: {}".format(self.directory), file=sys.stderr)
        else:
            shutil.rmtree(self.directory)

    def test_strict_json_rejects_duplicates_nonfinite_and_huge_integer(self):
        for data in (b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b'NaN',
                     b'Infinity', b'-Infinity', b'1e999', b'9' * 1000, b'{}{}', b'"\xff"'):
            with self.subTest(data=data[:40]), self.assertRaises(contracts.ContractError):
                contracts.strict_json_bytes(data)
        self.assertEqual({"value": 18446744073709551615},
                         contracts.strict_json_bytes(b'{"value":18446744073709551615}'))

    def test_artifact_hashing_streams_and_rejects_stale_size_hash_or_symlink(self):
        fixture = MetadataFixture(self.directory)
        reference = fixture.file("large.bin", b"bounded stream\n" * 30000)
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded artifact read")):
            self.assertEqual(reference, contracts.verify_artifact(reference))
        for changed in (dict(reference, size=reference["size"] + 1), dict(reference, sha256="0" * 64),
                        dict(reference, sha256="a" * 62), dict(reference, size=True)):
            with self.subTest(changed=changed), self.assertRaises(contracts.ContractError):
                contracts.verify_artifact(changed)
        link = self.directory / "link"
        link.symlink_to(reference["path"])
        with self.assertRaises(contracts.ContractError):
            contracts.verify_artifact(dict(reference, path=str(link)))
        loop = self.directory / "artifact-loop"
        loop.symlink_to(loop)
        with self.assertRaises(contracts.ContractError):
            contracts.verify_artifact(dict(reference, path=str(loop)))

    def test_initial_bundle_reader_rejects_fifo_links_directories_and_oversize(self):
        regular = self.directory / "regular.json"
        regular.write_bytes(b"{}")
        link = self.directory / "linked.json"
        link.symlink_to(regular)
        fifo = self.directory / "fifo.json"
        os.mkfifo(str(fifo))
        loop = self.directory / "loop.json"
        loop.symlink_to(loop)
        oversized = self.directory / "oversize.json"
        with oversized.open("wb") as stream:
            stream.seek(contracts.JSON_LIMIT_BYTES)
            stream.write(b"x")
        self.assertEqual({}, contracts.load_json(regular))
        for path in (link, loop, fifo, self.directory, oversized):
            with self.subTest(path=path), self.assertRaises(contracts.ContractError):
                contracts.load_json(path)

    def test_reviewed_three_case_packet_validates_without_accepting_os(self):
        fixture = MetadataFixture(self.directory, ("startup.argv-empty", "startup.argv-whitespace", "startup.environment"))
        bundle = contracts.load_runtime_bundle(fixture.build())
        self.assertEqual(3, len(bundle["cases"]))
        for case_id in fixture.case_ids:
            result = contracts.validate_case(bundle, case_id)
            self.assertEqual("PASS", result["status"])
            self.assertEqual("runtime-contract-metadata", result["scope"])
            self.assertFalse(result["application_acceptance"])
        self.assertEqual("BLOCKED", contracts.validate_case(bundle, "memory.calloc-zero")["status"])

    def test_missing_unsupported_and_blocked_global_capabilities_never_skip_pass(self):
        fixture = MetadataFixture(self.directory)
        for state in ("blocked", "unsupported"):
            fixture.cap_states["runtime-transport-fault-injection"] = state
            result = contracts.validate_case(contracts.load_runtime_bundle(fixture.build()), fixture.case_ids[0])
            self.assertEqual("BLOCKED", result["status"])
            self.assertTrue(any("runtime-transport-fault-injection" in reason for reason in result["reasons"]))
        fixture.required.remove("runtime-transport-fault-injection")
        result = contracts.validate_case(contracts.load_runtime_bundle(fixture.build()), fixture.case_ids[0])
        self.assertEqual("BLOCKED", result["status"])

    def test_case_dependencies_block_until_acceptance_evaluator_exists(self):
        fixture = MetadataFixture(self.directory, ("memory.anonymous-reuse",))
        result = contracts.validate_case(contracts.load_runtime_bundle(fixture.build()), fixture.case_ids[0])
        self.assertEqual("BLOCKED", result["status"])
        self.assertTrue(any("memory.anonymous-zero" in reason for reason in result["reasons"]))

    def test_verified_capability_requires_passing_source_bound_evidence(self):
        fixture = MetadataFixture(self.directory)
        for override in ({"selected_inputs_sha256": "0" * 64}, {"status": "NOT_RUN"},
                         {"status": "COMPLETED"}, {"review_status": "PENDING"}, {"artifacts": []}):
            fixture.evidence_overrides["current-inputs"] = override
            with self.subTest(override=override), self.assertRaises(contracts.ContractError):
                contracts.load_runtime_bundle(fixture.build())
        fixture.evidence_overrides = {}
        fixture.cap_overrides["current-inputs"] = {"evidence": []}
        with self.assertRaises(contracts.ContractError):
            contracts.load_runtime_bundle(fixture.build())

    def test_stale_packet_or_capability_binding_is_rejected(self):
        fixture = MetadataFixture(self.directory)
        for field in ("catalog_sha256", "selected_inputs_sha256", "capabilities_sha256"):
            fixture.packet_overrides = {field: "0" * 64}
            with self.subTest(field=field), self.assertRaises(contracts.ContractError):
                contracts.load_runtime_bundle(fixture.build())
        fixture.packet_overrides = {}
        fixture.caps_header_overrides = {"selected_inputs_sha256": "0" * 64}
        with self.assertRaises(contracts.ContractError):
            contracts.load_runtime_bundle(fixture.build())

    def test_packet_count_duplicates_and_unknown_ids_are_rejected(self):
        fixture = MetadataFixture(self.directory)
        valid_cases = contracts.load_runtime_bundle(fixture.build())["packet"]["cases"]
        unknown_cases = copy.deepcopy(valid_cases)
        unknown_cases[0]["case_id"] = "unknown.unreviewed-case"
        for cases in ([], valid_cases * 4, valid_cases * 2, unknown_cases):
            fixture.packet_overrides = {"cases": cases}
            with self.subTest(count=len(cases)), self.assertRaises(contracts.ContractError):
                contracts.load_runtime_bundle(fixture.build())
        fixture.packet_overrides = {}
        fixture.inputs["payloads"]["unreviewed.extra"] = fixture.inputs["payloads"][fixture.case_ids[0]]
        with self.assertRaises(contracts.ContractError):
            contracts.load_runtime_bundle(fixture.build())

    def test_resource_expansion_unknown_limit_and_boolean_are_rejected(self):
        fixture = MetadataFixture(self.directory)
        original = copy.deepcopy(fixture.cases[0]["limits"])
        for changes in ({"payload_timeout_seconds": 11}, {"qemu_timeout_seconds": 301},
                        {"stdout_limit_bytes": 65537}, {"payload_timeout_seconds": True},
                        {"unknown_relaxation": 1}, {"container_cpus": [0, 1, 2, 3]}):
            fixture.cases[0]["limits"] = dict(original, **changes)
            with self.subTest(changes=changes), self.assertRaises(contracts.ContractError):
                contracts.load_runtime_bundle(fixture.build())
        fixture.cases[0]["limits"] = original
        fixture.inputs["profile"]["network"] = "host"
        with self.assertRaises(contracts.ContractError):
            contracts.load_runtime_bundle(fixture.build())

    def test_pending_oracle_or_parameter_review_and_disabled_execution_block(self):
        fixture = MetadataFixture(self.directory)
        fixture.oracles[fixture.case_ids[0]]["review_status"] = "PENDING"
        fixture.cases[0]["parameters_reviewed"] = False
        fixture.packet_overrides["execution_enabled"] = False
        result = contracts.validate_case(contracts.load_runtime_bundle(fixture.build()), fixture.case_ids[0])
        self.assertEqual("BLOCKED", result["status"])
        self.assertEqual(3, len(result["reasons"]))

    def test_oracle_source_binding_and_postload_source_drift_fail(self):
        fixture = MetadataFixture(self.directory)
        fixture.oracles[fixture.case_ids[0]]["source_sha256"] = "0" * 64
        with self.assertRaises(contracts.ContractError):
            contracts.load_runtime_bundle(fixture.build())
        fixture.oracles[fixture.case_ids[0]]["source_sha256"] = fixture.cases[0]["source"]["sha256"]
        bundle = contracts.load_runtime_bundle(fixture.build())
        Path(fixture.cases[0]["source"]["path"]).write_bytes(b"changed source\n")
        self.assertEqual("FAIL", contracts.validate_case(bundle, fixture.case_ids[0])["status"])

    def test_independent_bytes_pass_only_exact_record_not_printed_pass(self):
        fixture = MetadataFixture(self.directory)
        bundle = contracts.load_runtime_bundle(fixture.build())
        result = contracts.evaluate_case(bundle, fixture.case_ids[0], fixture.report())
        self.assertEqual("PASS", result["status"])
        self.assertEqual("independent-oracle", result["scope"])
        self.assertFalse(result["application_acceptance"])
        wrong = contracts.evaluate_case(bundle, fixture.case_ids[0], fixture.report(stdout=b"PASS\n"),
                                        evidence={"linux_matched": True, "mckernel": "PASS"})
        self.assertEqual("FAIL", wrong["status"])

    def test_raw_signal_is_required_and_exit_128_plus_signal_fails(self):
        fixture = MetadataFixture(self.directory)
        fixture.oracles[fixture.case_ids[0]]["wait_status"] = {"kind": "signaled", "signal": signal.SIGTERM}
        bundle = contracts.load_runtime_bundle(fixture.build())
        self.assertEqual("PASS", contracts.evaluate_case(bundle, fixture.case_ids[0], fixture.report(raw=int(signal.SIGTERM)))["status"])
        self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], fixture.report(raw=143 << 8))["status"])
        report = fixture.report(raw=143 << 8)
        report["wait_status"] = {"kind": "signaled", "signal": signal.SIGTERM}
        self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])

    def test_json_oracle_rejects_duplicates_wrong_types_and_extra_records(self):
        fixture = MetadataFixture(self.directory)
        fixture.oracles[fixture.case_ids[0]]["stdout"] = {"kind": "json-equals", "value": {"argc": 4, "empty": ""}}
        bundle = contracts.load_runtime_bundle(fixture.build())
        for data, status in ((b'{ "empty":"", "argc":4 }\n', "PASS"),
                             (b'{"empty":"","argc":4.0}', "FAIL"),
                             (b'{"empty":"","argc":true}', "FAIL"),
                             (b'{"empty":"","argc":4,"argc":4}', "FAIL"),
                             (b'{"empty":"","argc":4}\n{}', "FAIL")):
            with self.subTest(data=data):
                self.assertEqual(status, contracts.evaluate_case(bundle, fixture.case_ids[0], fixture.report(stdout=data))["status"])

    def test_unsupported_predicates_block_without_expression_execution(self):
        fixture = MetadataFixture(self.directory)
        marker = self.directory / "must-not-exist"
        fixture.oracles[fixture.case_ids[0]]["predicates"] = [
            {"kind": "python", "expression": "open({!r},'w').write('bad')".format(str(marker))}]
        result = contracts.evaluate_case(contracts.load_runtime_bundle(fixture.build()), fixture.case_ids[0], fixture.report())
        self.assertEqual("BLOCKED", result["status"])
        self.assertFalse(marker.exists())
        fixture.oracles[fixture.case_ids[0]]["predicates"] = []
        fixture.oracles[fixture.case_ids[0]]["stdout"] = {"kind": "normalize-until-pass"}
        result = contracts.validate_case(contracts.load_runtime_bundle(fixture.build()), fixture.case_ids[0])
        self.assertEqual("BLOCKED", result["status"])

    def test_incomplete_collection_or_changed_launch_contract_fails(self):
        fixture = MetadataFixture(self.directory)
        bundle = contracts.load_runtime_bundle(fixture.build())
        for changes in ({"status": "TIMED_OUT"}, {"status": "ORPHANED_DESCENDANTS"},
                        {"cleanup_complete": False}, {"raw_wait_status": None},
                        {"argv": ["app", "A", "B"]}, {"executable_path": "/apps/wrong"},
                        {"env": {}}, {"uid": 1000}, {"timeout_seconds": float("inf")},
                        {"stdin": {"kind": "file", "size": 0, "sha256": "0" * 64}}):
            report = fixture.report()
            report.update(changes)
            with self.subTest(changes=changes):
                self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])

    def test_truncation_stream_accounting_and_stale_artifact_fail(self):
        fixture = MetadataFixture(self.directory)
        bundle = contracts.load_runtime_bundle(fixture.build())
        for changes in ({"truncated": True}, {"eof": False}, {"bytes_observed": 100},
                        {"discarded_observed_bytes": 1}, {"discarded_observed_bytes": False},
                        {"limit_bytes": 65537}):
            report = fixture.report()
            report["streams"]["stdout"].update(changes)
            with self.subTest(changes=changes):
                self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])
        report = fixture.report()
        Path(report["streams"]["stdout"]["artifact"]["path"]).write_bytes(b"changed\n")
        self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])

    def test_malformed_collection_containers_and_bool_identities_fail_closed(self):
        fixture = MetadataFixture(self.directory)
        bundle = contracts.load_runtime_bundle(fixture.build())
        for changes in ({"schema_version": False}, {"schema_version": 2}, {"schema_version": 1.0},
                        {"uid": False}, {"gid": False}, {"groups": [False]},
                        {"wait_status": {"kind": "exited", "code": False}},
                        {"wait_status": []}, {"streams": []},
                        {"streams": {"stdout": [], "stderr": {}}},
                        {"streams": {"stdout": {}, "stderr": None}}):
            report = fixture.report()
            report.update(changes)
            with self.subTest(changes=changes):
                self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])

    def test_boolean_artifact_sizes_cannot_alias_zero_or_one(self):
        fixture = MetadataFixture(self.directory)
        payload = fixture.inputs["payloads"][fixture.case_ids[0]]
        payload["executable"] = fixture.file("one-byte-test.elf", b"x")
        payload["stdin"] = fixture.file("empty-input", b"")
        bundle = contracts.load_runtime_bundle(fixture.build())
        report = fixture.report()
        report["stdin"] = dict(payload["stdin"], kind="file")
        self.assertEqual("PASS", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])
        for target, invalid in (("executable", True), ("stdin", False)):
            broken = copy.deepcopy(report)
            broken[target]["size"] = invalid
            with self.subTest(target=target):
                self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], broken)["status"])

    def test_completion_observation_is_finite_consistent_and_within_deadline(self):
        fixture = MetadataFixture(self.directory)
        bundle = contracts.load_runtime_bundle(fixture.build())
        for changes in ({"payload_monotonic_started": False}, {"payload_monotonic_started": -1.0},
                        {"payload_monotonic_deadline": None}, {"payload_monotonic_deadline": 120.0},
                        {"payload_completion_observed_monotonic": float("nan")},
                        {"payload_completion_observed_monotonic": 111.0},
                        {"payload_completion_observed_monotonic": 99.0}):
            report = fixture.report()
            report.update(changes)
            with self.subTest(changes=changes):
                self.assertEqual("FAIL", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])
        report = fixture.report()
        report["payload_completion_observed_monotonic"] = report["payload_monotonic_deadline"]
        self.assertEqual("PASS", contracts.evaluate_case(bundle, fixture.case_ids[0], report)["status"])


if __name__ == "__main__":
    unittest.main()
