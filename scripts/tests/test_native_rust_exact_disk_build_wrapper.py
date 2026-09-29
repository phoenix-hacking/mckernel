import copy
import shutil
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import sys

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
        return {"status": "PASS"}


def request(source):
    return {
        "source_root": str(source),
        "memory_allocation_roots": [str(source)],
    }


class WrapperTests(unittest.TestCase):
    def setUp(self):
        FakeOwner.calls = FakeOwner.validations = 0
        FakeOwner.CliSignals.entered = FakeOwner.CliSignals.exited = 0
        FakeOwner.measurement = {
            "memory_allocation_memory_backed_bytes": 0,
            "memory_allocation_roots": [{"filesystem": "ext4"}],
            "aggregate_memory_required": wrapper.LAUNCHER_AGGREGATE_BYTES,
        }

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
                loaded = wrapper._load_owner({"source_root": str(source)})
            self.assertNotEqual(loaded.provenance, sentinel)
            self.assertEqual(Path(loaded.provenance.__file__).resolve(),
                             (scripts / "native_rust_exact_build_offline.py").resolve())


if __name__ == "__main__":
    unittest.main()
