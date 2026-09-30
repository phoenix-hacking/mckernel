import copy
import shutil
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import sys
import hashlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import native_rust_exact_disk_build_wrapper as wrapper


class FakeOwner:
    LIMITS = dict(wrapper.EXPECTED_LIMITS)

    class provenance:
        ENV = {}

    class CliSignals:
        entered = 0
        exited = 0

        def __enter__(self):
            FakeOwner.CliSignals.entered += 1
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            FakeOwner.CliSignals.exited += 1
            return False

    calls = 0
    validations = 0
    measurement = None

    def __init__(self, request, signals=None):
        self.request = request
        self.signals = signals
        self.measurement = copy.deepcopy(FakeOwner.measurement)

    def validate(self):
        FakeOwner.validations += 1

    def run(self):
        self.validate()
        FakeOwner.calls += 1
        return {"status": "PASS", "retired": True,
                "cleanup_separately_required": False,
                "terminal_container_info": None,
                "terminal_container_info_current": True}


def request(source):
    return {
        "source_root": str(source),
        "memory_allocation_roots": [str(source)],
        "operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH,
    }


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.lock_dir = Path(tempfile.mkdtemp(prefix="mckernel-wrapper-lock-"))
        wrapper.OPERATIONAL_EXCLUSION_PATH = str(
            self.lock_dir / "native-exact-candidate-operational-exclusion-runtimeblob-12.json")
        FakeOwner.calls = FakeOwner.validations = 0
        FakeOwner.CliSignals.entered = FakeOwner.CliSignals.exited = 0
        FakeOwner.measurement = {
            "memory_allocation_memory_backed_bytes": 0,
            "memory_allocation_roots": [{"filesystem": "ext4", "memory_effect_bytes": 0, "allocated_bytes": 1}],
            "memory_allocation_total_bytes": 1,
            "memory_allocation_tmpfs_bytes": 0,
            "candidate_memory_effect": {"classification": "none", "bytes": 0},
            "aggregate_memory_required": wrapper.EXPECTED_LIMITS["Memory"],
        }

    def tearDown(self):
        lock = Path(wrapper.OPERATIONAL_EXCLUSION_PATH)
        if lock.exists():
            lock.unlink()
        self.lock_dir.rmdir()

    def invoke(self, req, aggregate=wrapper.LAUNCHER_AGGREGATE_GIB):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            (source / "scripts").mkdir()
            owner_path = source / "scripts" / "native_rust_exact_build_container_owner.py"
            owner_path.write_text("# test placeholder\n")
            req = dict(req(source))
            with mock.patch.object(wrapper, "_load_owner", return_value=types.SimpleNamespace(
                    LIMITS=FakeOwner.LIMITS, provenance=FakeOwner.provenance,
                    CliSignals=FakeOwner.CliSignals,
                    BuildOwner=FakeOwner)):
                return wrapper.run_request(req, aggregate)

    def test_exact_boundary_runs_once(self):
        result = self.invoke(request)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(FakeOwner.calls, 1)
        self.assertEqual(FakeOwner.validations, 2)
        self.assertEqual(FakeOwner.CliSignals.entered, 1)
        self.assertEqual(FakeOwner.CliSignals.exited, 1)

    def test_fresh_exclusion_replaces_retired_tombstone(self):
        self.assertNotEqual(wrapper.OPERATIONAL_EXCLUSION_PATH,
                            wrapper.RETIRED_OPERATIONAL_EXCLUSION_PATH)
        self.assertTrue(wrapper.OPERATIONAL_EXCLUSION_PATH.endswith(
            "native-exact-candidate-operational-exclusion-runtimeblob-12.json"))
        for rejected_path in (
            wrapper.RETIRED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.REVIEWED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.SUPERSEDED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.CLOSUREFIX_OPERATIONAL_EXCLUSION_PATH,
            wrapper.RUNTIMECLOSURE_OPERATIONAL_EXCLUSION_PATH,
            wrapper.OFFLINECWD_OPERATIONAL_EXCLUSION_PATH,
            wrapper.MEMORYMAP_OPERATIONAL_EXCLUSION_PATH,
            wrapper.MEMORYMAP_RELOCATED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.MAPPINGBINDING_OPERATIONAL_EXCLUSION_PATH,
            wrapper.LIFECYCLEBINDING_OPERATIONAL_EXCLUSION_PATH,
            wrapper.OBJTOOLBINDING_OPERATIONAL_EXCLUSION_PATH,
        ):
            old_request = request
            def rejected_request(source, path=rejected_path):
                value = old_request(source)
                value["operational_exclusion_path"] = path
                return value
            with self.assertRaisesRegex(wrapper.AdmissionError,
                                        "reviewed exact path"):
                self.invoke(rejected_request)
        self.assertEqual(FakeOwner.calls, 0)
        lock, record = wrapper._acquire_exclusion(
            {"operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH})
        self.assertTrue(lock.exists())
        self.assertEqual(record["request_sha256"], wrapper._request_hash(
            {"operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH}))
        lock.unlink()
        result = self.invoke(request)
        self.assertEqual(result["status"], "PASS")

    def test_failed_minus_two_exclusion_is_rejected(self):
        old_request = request
        def failed_request(source):
            value = old_request(source)
            value["operational_exclusion_path"] = (
                wrapper.REVIEWED_OPERATIONAL_EXCLUSION_PATH)
            return value
        with self.assertRaisesRegex(wrapper.AdmissionError,
                                    "reviewed exact path"):
            self.invoke(failed_request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_failed_minus_three_exclusion_is_rejected(self):
        old_request = request
        def failed_request(source):
            value = old_request(source)
            value["operational_exclusion_path"] = (
                wrapper.SUPERSEDED_OPERATIONAL_EXCLUSION_PATH)
            return value
        with self.assertRaisesRegex(wrapper.AdmissionError,
                                    "reviewed exact path"):
            self.invoke(failed_request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_closurefix_four_exclusion_is_rejected(self):
        old_request = request
        def failed_request(source):
            value = old_request(source)
            value["operational_exclusion_path"] = (
                wrapper.CLOSUREFIX_OPERATIONAL_EXCLUSION_PATH)
            return value
        with self.assertRaisesRegex(wrapper.AdmissionError,
                                    "reviewed exact path"):
            self.invoke(failed_request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_existing_exclusion_fails_closed(self):
        lock = Path(wrapper.OPERATIONAL_EXCLUSION_PATH)
        lock.write_text("partial")
        with self.assertRaisesRegex(wrapper.AdmissionError, "already exists"):
            self.invoke(request)

    def test_exclusion_record_short_writes_are_completed(self):
        original_write = wrapper.os.write
        writes = []
        def short_write(fd, data):
            if len(data) > 1:
                chunk = data[:max(1, len(data) // 2)]
                writes.append(len(chunk))
                return original_write(fd, chunk)
            return original_write(fd, data)
        with mock.patch.object(wrapper.os, "write", side_effect=short_write):
            result = self.invoke(request)
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(len(writes), 1)

    def test_uncertain_owner_result_retains_exclusion(self):
        result = {"status": "PASS", "retired": True,
                  "cleanup_separately_required": True,
                  "terminal_container_info": {"Id": "retained"},
                  "terminal_container_info_current": True}
        with mock.patch.object(FakeOwner, "run", return_value=result):
            self.invoke(request)
        self.assertTrue(Path(wrapper.OPERATIONAL_EXCLUSION_PATH).exists())
        self.assertEqual(FakeOwner.provenance.ENV["GIT_OPTIONAL_LOCKS"], "0")

    def test_excess_aggregate_rejected_without_run(self):
        FakeOwner.measurement["aggregate_memory_required"] += 1
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_nonzero_memory_rejected_without_run(self):
        FakeOwner.measurement["memory_allocation_memory_backed_bytes"] = 1
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_wrong_limits_rejected_without_run(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            FakeOwner.LIMITS = dict(wrapper.EXPECTED_LIMITS, CpusetCpus="0-3")
            try:
                with self.assertRaises(wrapper.AdmissionError):
                    self.invoke(request)
            finally:
                FakeOwner.LIMITS = dict(wrapper.EXPECTED_LIMITS)
        self.assertEqual(FakeOwner.calls, 0)

    def test_wrong_launcher_argument_rejected_without_owner_load(self):
        with mock.patch.object(wrapper, "_load_owner") as load:
            with self.assertRaises(wrapper.AdmissionError):
                wrapper.run_request({"source_root": "/unused"}, "16.2159")
            load.assert_not_called()

    def test_tmpfs_root_rejected_without_run(self):
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(lambda source: {"source_root": str(source),
                                        "memory_allocation_roots": ["/tmpfs/source"]})
        self.assertEqual(FakeOwner.calls, 0)

    def test_second_measurement_is_guarded_before_run(self):
        original = FakeOwner.validate

        def mutate_after_first(self):
            original(self)
            if FakeOwner.validations > 1:
                self.measurement["aggregate_memory_required"] = 22548578304

        with mock.patch.object(FakeOwner, "validate", mutate_after_first):
            with self.assertRaises(wrapper.AdmissionError):
                self.invoke(request)
        self.assertEqual(FakeOwner.calls, 0)
        self.assertEqual(FakeOwner.validations, 2)

    def test_owner_and_provenance_are_loaded_from_candidate_package(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            scripts = source / "scripts"
            scripts.mkdir()
            for name in ("native_rust_exact_build_container_owner.py",
                         "native_rust_exact_build_offline.py"):
                shutil.copy(ROOT / "scripts" / name, scripts / name)
            sentinel = types.ModuleType("native_rust_exact_build_offline")
            sentinel.__file__ = "/host/sentinel.py"
            with mock.patch.dict(sys.modules,
                                 {"native_rust_exact_build_offline": sentinel}):
                req = {"source_root": str(source),
                       "driver_path": str(scripts / "native_rust_exact_build_offline.py"),
                       "owner_path_sha256": hashlib.sha256((scripts / "native_rust_exact_build_container_owner.py").read_bytes()).hexdigest(),
                       "driver_path_sha256": hashlib.sha256((scripts / "native_rust_exact_build_offline.py").read_bytes()).hexdigest(),
                       "provenance_path_sha256": hashlib.sha256((scripts / "native_rust_exact_build_offline.py").read_bytes()).hexdigest()}
                loaded = wrapper._load_owner(req)
            self.assertNotEqual(loaded.provenance, sentinel)
            self.assertEqual(Path(loaded.provenance.__file__).resolve(),
                             (scripts / "native_rust_exact_build_offline.py").resolve())

    def test_owner_as_driver_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td); scripts = source / "scripts"; scripts.mkdir()
            owner = scripts / "native_rust_exact_build_container_owner.py"
            provenance = scripts / "native_rust_exact_build_offline.py"
            shutil.copy(ROOT / "scripts" / owner.name, owner)
            shutil.copy(ROOT / "scripts" / provenance.name, provenance)
            owner_hash = hashlib.sha256(owner.read_bytes()).hexdigest()
            prov_hash = hashlib.sha256(provenance.read_bytes()).hexdigest()
            with self.assertRaisesRegex(wrapper.AdmissionError, "driver_path must equal"):
                wrapper._load_owner({"source_root": str(source),
                    "driver_path": str(owner), "driver_path_sha256": owner_hash,
                    "owner_path_sha256": owner_hash, "provenance_path_sha256": prov_hash})

    def test_untrusted_candidate_is_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td); scripts = source / "scripts"; scripts.mkdir()
            owner = scripts / "native_rust_exact_build_container_owner.py"
            provenance = scripts / "native_rust_exact_build_offline.py"
            owner.write_text("raise RuntimeError('sentinel executed')\n")
            provenance.write_text("raise RuntimeError('provenance executed')\n")
            with self.assertRaisesRegex(wrapper.AdmissionError, "owner_path hash mismatch"):
                wrapper._load_owner({"source_root": str(source),
                    "owner_path_sha256": "0" * 64,
                    "provenance_path_sha256": "0" * 64})

    def test_ramfs_and_inconsistent_rows_rejected(self):
        FakeOwner.measurement["memory_allocation_roots"][0]["filesystem"] = "ramfs"
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)
        FakeOwner.measurement["memory_allocation_roots"][0]["filesystem"] = "ext4"
        FakeOwner.measurement["memory_allocation_roots"][0]["memory_effect_bytes"] = 1
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)

    def test_missing_total_rejected(self):
        del FakeOwner.measurement["memory_allocation_total_bytes"]
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)


if __name__ == "__main__":
    unittest.main()
