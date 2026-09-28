import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "native_shutdown_observer", ROOT / "scripts/application-tests/native_shutdown_observer.py")
NSO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NSO)


def reserve(values=None):
    values = list(values or [])
    return {"cpu": {"status": "available", "queries": {"os0": {"values": values}}, "reason": None},
            "numa_memory": {"status": "available", "queries": {"node0": {"values": values},
                            "node1": {"values": values}}, "reason": None}}


def unavailable(reason="provider_absent"):
    return {"cpu": {"status": "unavailable", "queries": {}, "reason": reason},
            "numa_memory": {"status": "unavailable", "queries": {}, "reason": reason}}


def procfs(present):
    return {"state": "present" if present else "absent", "numeric_nodes": [0] if present else [],
            "status": {"0": "RUNNING"} if present else {}, "maps": {"0": "0000-0fff"} if present else {},
            "errors": []}


def phase(name, present=False, live=False):
    process = [{"pid": 123, "starttime_ticks": 77}] if live else []
    return {"phase": name, "processes": process, "procfs": procfs(present), "devices": [], "modules": {},
            "reserves": reserve() if present else unavailable(), "cpu_online": [0, 1],
            "irqs": {"inventory": {"32": {"affinity": "0-1"}}, "added": [], "removed": []},
            "policy": {"selinux": {"enforcing": True, "config": "enforcing"}, "swappiness": 60,
                       "irqbalance": {"state": "active", "config": "IRQBALANCE_BANNED_CPUS="}},
            "limitations": ["internal_mapping_ledger_unobserved"]}


def document():
    rows = [phase("clean_baseline"), phase("booted", present=True),
            phase("workload_live", present=True, live=True),
            phase("workload_retired_pre_stop", present=True),
            phase("destroyed_resources_released_provider_present", present=True), phase("fully_unloaded"),
            phase("policy_restored")]
    device = {"path": "/dev/mcd0", "role": "provider", "type": "char", "major": 240, "minor": 0,
              "owner": {"uid": 0, "gid": 0}, "mode": 0o660,
              "sysfs": {"dev": "240:0", "type": "char"}}
    os_device = {"path": "/dev/mcos0", "role": "os", "type": "char", "major": 241, "minor": 0,
                 "owner": {"uid": 0, "gid": 0}, "mode": 0o660,
                 "sysfs": {"dev": "241:0", "type": "char"}}
    live_module = {"mcctrl": {"refcount": 1, "holders": ["mcctrl-client"]}}
    for index in (1, 2, 3):
        rows[index]["devices"] = [copy.deepcopy(device), copy.deepcopy(os_device)]
        rows[index]["modules"] = copy.deepcopy(live_module)
    rows[4]["devices"] = [copy.deepcopy(device)]
    rows[4]["modules"] = {"mcctrl": {"refcount": 1, "holders": ["mcctrl-client"]}}
    rows[4]["procfs"] = procfs(False)
    rows[5]["reserves"] = unavailable()
    rows[6]["reserves"] = unavailable()
    expectations = {"processes": {}, "procfs": {}, "devices": {}, "modules": {},
                    "cpu_online": [0, 1], "irqs": {"32": {"affinity": "0-1"}},
                    "policy": copy.deepcopy(rows[0]["policy"])}
    for row in rows:
        expectations["processes"][row["phase"]] = copy.deepcopy(row["processes"])
        p = row["procfs"]
        expectations["procfs"][row["phase"]] = {"state": p["state"], "numeric_nodes": list(p["numeric_nodes"]),
                                                    "status_sha256": NSO._map_digest(p["status"]),
                                                    "maps_sha256": NSO._map_digest(p["maps"])}
        expectations["devices"][row["phase"]] = copy.deepcopy(row["devices"])
        expectations["modules"][row["phase"]] = copy.deepcopy(row["modules"])
    return {"schema": "native-shutdown-observer-v2", "expectations": expectations, "phases": rows}


class ShutdownObserverTests(unittest.TestCase):
    def test_one_cycle_is_diagnostic_only(self):
        result = NSO.validate(document())
        self.assertEqual(result["status"], "PROTOCOL_PASS")
        self.assertFalse(result["application_acceptance"])
        self.assertEqual(result["phases"], list(NSO.PHASES))
        self.assertEqual(result["limitations"], ["internal_mapping_ledger_unobserved"])

    def test_missing_duplicate_out_of_order_and_timeout_phases_reject(self):
        for mutate in (
                lambda rows: rows.pop(),
                lambda rows: rows.append(copy.deepcopy(rows[-1])),
                lambda rows: rows.__setitem__(1, rows[2])):
            value = document(); mutate(value["phases"])
            with self.subTest(mutate=mutate), self.assertRaisesRegex(NSO.ShutdownObservationError, "phase"):
                NSO.validate(value)
        value = document(); value["phases"][2]["procfs"]["errors"] = ["timeout"]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "error"):
            NSO.validate(value)

    def test_query_read_failure_and_stale_procfs_sysfs_reject(self):
        value = document(); value["phases"][4]["procfs"]["state"] = "absent"; value["phases"][4]["procfs"]["numeric_nodes"] = [4]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "absent procfs"):
            NSO.validate(value)
        value = document(); value["phases"][1]["procfs"]["errors"] = ["EIO"]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "error"):
            NSO.validate(value)
        device = {"path": "/dev/mcos0", "role": "os", "type": "char", "major": 240, "minor": 0,
                  "owner": {"uid": 0, "gid": 0}, "mode": 0o660,
                  "sysfs": {"dev": "240:1", "type": "char"}}
        value = document(); value["phases"][1]["devices"] = [device]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "sysfs"):
            NSO.validate(value)

    def test_residual_reserves_wrong_refs_and_identities_reject(self):
        value = document(); value["phases"][4]["reserves"] = reserve([2])
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "residual"):
            NSO.validate(value)
        value = document(); value["phases"][1]["modules"] = {"mcctrl": {"refcount": 2, "holders": ["x"]}}
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "module"):
            NSO.validate(value)
        value = document(); value["phases"][2]["processes"][0]["starttime_ticks"] = 78
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "identity"):
            NSO.validate(value)

    def test_unavailable_reserves_need_a_known_reason_and_no_queries(self):
        value = document(); value["phases"][5]["reserves"]["cpu"]["reason"] = "empty"
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "bad unavailable"):
            NSO.validate(value)
        value = document(); value["phases"][5]["reserves"]["numa_memory"]["queries"] = {"node0": {"values": []}}
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "unavailable reserve has queries"):
            NSO.validate(value)

    def test_device_role_must_match_provider_or_os_namespace(self):
        value = document(); value["phases"][1]["devices"][0]["role"] = "os"
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "role/path"):
            NSO.validate(value)
        value = document(); value["phases"][4]["devices"].append({
            "path": "/dev/mcos0", "role": "os", "type": "char", "major": 241, "minor": 0,
            "owner": {"uid": 0, "gid": 0}, "mode": 0o660,
            "sysfs": {"dev": "241:0", "type": "char"}})
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "provider resources"):
            NSO.validate(value)

    def test_lifecycle_device_and_reserve_invariants_reject_hostile_drift(self):
        value = document(); value["phases"][0]["devices"] = [copy.deepcopy(value["phases"][1]["devices"][0])]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "unclean baseline"):
            NSO.validate(value)
        value = document(); value["phases"][2]["devices"] = [copy.deepcopy(value["phases"][2]["devices"][0])]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "provider/OS"):
            NSO.validate(value)
        value = document(); value["phases"][4]["devices"].append(copy.deepcopy(value["phases"][1]["devices"][1]))
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "provider resources"):
            NSO.validate(value)
        value = document(); value["phases"][5]["reserves"]["cpu"]["reason"] = "query_unavailable"
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "provider-absent"):
            NSO.validate(value)

    def test_policy_cpu_and_irq_drift_reject(self):
        value = document(); value["phases"][-1]["policy"]["swappiness"] = 1
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "policy"):
            NSO.validate(value)
        value = document(); value["phases"][3]["cpu_online"] = [0]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "CPU"):
            NSO.validate(value)
        value = document(); value["phases"][3]["irqs"]["inventory"]["33"] = {"affinity": "1"}
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "IRQ added"):
            NSO.validate(value)
        value = document(); value["phases"][6]["irqs"]["inventory"]["32"]["affinity"] = "1"
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "IRQ affinity restoration"):
            NSO.validate(value)

    def test_external_procfs_expectations_and_phase_transitions_reject_drift(self):
        value = document(); value["phases"][2]["procfs"]["status"]["0"] = "STALE"
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "procfs content/digest"):
            NSO.validate(value)
        value = document(); value["phases"][1]["devices"] = []
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "provider/OS"):
            NSO.validate(value)
        value = document(); value["phases"][3]["processes"] = [{"pid": 123, "starttime_ticks": 77}]
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "workload not retired"):
            NSO.validate(value)
        value = document(); value["phases"][5]["modules"] = {"mcctrl": {"refcount": 0, "holders": []}}
        with self.assertRaisesRegex(NSO.ShutdownObservationError, "fully unloaded"):
            NSO.validate(value)

    def test_cli_writes_once_and_reports_evidence_write_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input.json", Path(directory) / "result.json"
            source.write_text(json.dumps(document()))
            self.assertEqual(NSO.main([str(source), "--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["status"], "PROTOCOL_PASS")
            self.assertEqual(NSO.main([str(source), "--output", str(output)]), 2)
            failed = Path(directory) / "failed.json"
            with mock.patch.object(NSO.os, "write", side_effect=OSError("evidence disk failure")):
                self.assertEqual(NSO.main([str(source), "--output", str(failed)]), 2)


if __name__ == "__main__":
    unittest.main()
