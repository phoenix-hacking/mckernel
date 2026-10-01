"""Bounded regression tests for the build/image/guest shared admission lock.

These tests deliberately exercise only the authenticated source contract and
fake entry work. They never start a build, container, guest, or privileged
transport.
"""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = load("shared_heavy_contract_20261001",
                SCRIPTS / "native_rust_exact_disk_build_wrapper.py")
image_prepare = load("image_prepare_20261001",
                     SCRIPTS / "native_rust_exact_build_image_prepare.py")
guest = load("guest_heavy_20261001", SCRIPTS / "qemu_guest_heavy_v1.py")


class SharedHeavyEntryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lock = self.root / "private-common.lock"
        self.old_path = contract.SHARED_HEAVY_LOCK_PATH
        self.old_release = contract.HEAVY_ENTRY_CONTRACT_RELEASED
        self.image_contract = image_prepare._SHARED_HEAVY_ENTRY_CONTRACT
        self.old_image_path = self.image_contract.SHARED_HEAVY_LOCK_PATH
        self.old_image_release = self.image_contract.HEAVY_ENTRY_CONTRACT_RELEASED
        contract.SHARED_HEAVY_LOCK_PATH = str(self.lock)
        contract.HEAVY_ENTRY_CONTRACT_RELEASED = True
        self.image_contract.SHARED_HEAVY_LOCK_PATH = str(self.lock)
        self.image_contract.HEAVY_ENTRY_CONTRACT_RELEASED = True

    def tearDown(self):
        contract.SHARED_HEAVY_LOCK_PATH = self.old_path
        contract.HEAVY_ENTRY_CONTRACT_RELEASED = self.old_release
        self.image_contract.SHARED_HEAVY_LOCK_PATH = self.old_image_path
        self.image_contract.HEAVY_ENTRY_CONTRACT_RELEASED = self.old_image_release
        self.temp.cleanup()

    def request(self, kind):
        return {"kind": kind, "request": "private-test", "root": str(self.root)}

    def release(self, token, *, status="PASS", retired=True,
                cleanup=False, terminal=None, current=True):
        lock, record = token
        return contract._release_exclusion(lock, record, {
            "status": status, "retired": retired,
            "cleanup_separately_required": cleanup,
            "terminal_container_info": terminal,
            "terminal_container_info_current": current,
        })

    def test_all_entry_modules_bind_the_same_contract_and_lock(self):
        """Build, image, and guest entries share one private O_EXCL inode."""
        self.assertEqual(Path(image_prepare._SHARED_HEAVY_ENTRY_CONTRACT.__file__).resolve(),
                         (SCRIPTS / "native_rust_exact_disk_build_wrapper.py").resolve())
        self.assertIn("acquire_heavy_operation", (SCRIPTS /
                      "native_rust_exact_disk_build_wrapper.py").read_text())
        guest_source = (SCRIPTS / "qemu_guest_heavy_v1.py").read_text()
        self.assertIn("common.SHARED_HEAVY_LOCK_PATH", guest_source)
        self.assertIn("write_claim(lock, record)", guest_source)

        for first in ("build", "image", "guest"):
            token = contract.acquire_heavy_operation(self.request(first), first)
            self.assertTrue(self.lock.is_file())
            first_stat = self.lock.stat()
            row = json.loads(self.lock.read_text())
            self.assertEqual(row["kind"], first)
            for second in ("build", "image", "guest"):
                if second == first:
                    continue
                with self.assertRaisesRegex(contract.AdmissionError,
                                            "operational exclusion already exists"):
                    contract.acquire_heavy_operation(self.request(second), second)
                self.assertEqual((self.lock.stat().st_dev, self.lock.stat().st_ino),
                                 (first_stat.st_dev, first_stat.st_ino))
            self.assertTrue(self.release(token))
            self.assertFalse(self.lock.exists())

    def test_acquisition_precedes_measurement_and_owner_work(self):
        """Production build/image/guest boundaries admit before their hooks."""
        events = []
        build = load("build_wrapper_boundary_20261001",
                     SCRIPTS / "native_rust_exact_disk_build_wrapper.py")
        image = image_prepare

        # The build entry reaches reconciliation only after shared admission.
        build.OPERATIONAL_EXCLUSION_PATH = str(self.root / "build.lock")
        build.SHARED_HEAVY_LOCK_PATH = str(self.lock)
        build_acquire = build.acquire_heavy_operation
        def observed_build_acquire(request, kind):
            token = build_acquire(request, kind)
            events.append(("build", "acquired"))
            return token
        def reconcile(_request):
            events.append(("build", "owner-measurement"))
            raise RuntimeError("stop after bounded reconciliation probe")
        with mock.patch.object(build, "acquire_heavy_operation", observed_build_acquire), \
             mock.patch.object(build, "_dispatcher_reconcile", reconcile):
            with self.assertRaisesRegex(RuntimeError, "bounded reconciliation"):
                build.run_request(dict(self.request("build"),
                                       operational_exclusion_path=str(self.root / "build.lock")))
        self.assertTrue(self.lock.exists())
        self.lock.unlink()

        # Image prepare is called far enough to enter its real measurement hook.
        output, evidence = self.root / "output", self.root / "evidence"
        output_parent, evidence_parent = output.parent, evidence.parent
        def measure(*_args, **_kwargs):
            events.append(("image", "owner-measurement"))
            raise RuntimeError("stop after bounded image measurement probe")
        image_acquire = image._SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation
        def observed_image_acquire(request, kind):
            token = image_acquire(request, kind)
            events.append(("image", "acquired"))
            return token
        with mock.patch.object(image._SHARED_HEAVY_ENTRY_CONTRACT,
                               "acquire_heavy_operation", observed_image_acquire), \
             mock.patch.object(image, "measure", measure):
            with self.assertRaisesRegex(RuntimeError, "image measurement"):
                image.prepare(candidate_sha="a" * 40, output_root=output,
                              evidence_root=evidence,
                              lease_path=self.root / "lease",
                              toolchain_lock=self.root / "toolchain-lock")
        self.assertTrue(self.lock.exists())
        self.lock.unlink()

        # Guest admission uses the authenticated common provider and writes its
        # production claim before creating the evidence root.
        request = {"controller": {"pid": 2, "starttime": "test", "boot_id": "test"},
                   "sources": {"scripts/native_rust_exact_disk_build_wrapper.py": "snapshot-hash"},
                   "config": {"log_dir": str(self.root / "guest"),
                              "overlay": str(self.root / "overlay.qcow2")}}
        snapshots = {"scripts/native_rust_exact_disk_build_wrapper.py": b"snapshot"}
        guest_write_claim = guest.write_claim
        def observed_guest_claim(path, record):
            result = guest_write_claim(path, record)
            if Path(path) == self.lock:
                events.append(("guest", "owner-claim"))
            return result
        with mock.patch.object(guest, "authenticate", return_value=(request, snapshots)), \
             mock.patch.object(guest, "provider", return_value=contract), \
             mock.patch.object(guest, "verify_source_identities"), \
             mock.patch.object(guest, "_AUTHENTICATED_IDENTITIES",
                               {"scripts/native_rust_exact_disk_build_wrapper.py": None}), \
             mock.patch.object(guest, "write_claim", observed_guest_claim):
            guest.admit(self.root / "request.json", "request-hash", "0" * 40,
                        {})
        self.assertTrue(self.lock.exists())
        self.assertTrue((self.root / "guest" / "heavy-operation-acquire.json").exists())
        self.lock.unlink()
        for kind, hook in (("build", "owner-measurement"),
                           ("image", "owner-measurement"),
                           ("guest", "owner-claim")):
            labels = [row[1] for row in events if row[0] == kind]
            self.assertEqual(labels[-1], hook)

    def test_positive_retirement_releases_but_uncertainty_or_failure_retains(self):
        token = contract.acquire_heavy_operation(self.request("build"), "build")
        self.assertFalse(self.release(token, status="FAIL", retired=False))
        self.assertTrue(self.lock.exists())
        self.assertFalse(self.release(token, terminal={"stale": True}))
        self.assertTrue(self.lock.exists())
        self.assertTrue(self.release(token))
        self.assertFalse(self.lock.exists())

    def test_stale_authenticated_wrapper_hash_is_rejected(self):
        owner = load("owner_20261001",
                     SCRIPTS / "native_rust_exact_mckernel_image_container_owner.py")
        source = self.root / "wrapper.py"
        source.write_bytes((SCRIPTS / "native_rust_exact_disk_build_wrapper.py").read_bytes())
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        source.write_bytes(source.read_bytes() + b"\n# stale substitution\n")
        with self.assertRaisesRegex(owner.OwnerError, "hash mismatch"):
            owner._load_heavy_entry_contract(source, expected)

    def test_unreleased_switch_rejects_every_entry_kind_before_work(self):
        contract.HEAVY_ENTRY_CONTRACT_RELEASED = False
        for kind in ("build", "image", "guest"):
            with self.assertRaisesRegex(contract.AdmissionError, "not released"):
                contract.acquire_heavy_operation(self.request(kind), kind)
        self.assertFalse(self.lock.exists())

    def test_guest_and_common_release_switches_are_independent_fail_closed(self):
        request = {"controller": {"pid": 2, "starttime": "test", "boot_id": "test"},
                   "sources": {"scripts/native_rust_exact_disk_build_wrapper.py": "snapshot-hash"},
                   "config": {"log_dir": str(self.root / "guest"),
                              "overlay": str(self.root / "overlay.qcow2")}}
        snapshots = {"scripts/native_rust_exact_disk_build_wrapper.py": b"snapshot"}
        with mock.patch.object(guest, "authenticate", return_value=(request, snapshots)), \
             mock.patch.object(guest, "provider", return_value=contract), \
             mock.patch.object(guest, "verify_source_identities"), \
             mock.patch.object(guest, "_AUTHENTICATED_IDENTITIES",
                               {"scripts/native_rust_exact_disk_build_wrapper.py": None}):
            guest.HEAVY_ENTRY_CONTRACT_RELEASED = False
            with self.assertRaisesRegex(ValueError, "not released"):
                guest.admit(self.root / "request.json", "request-hash", "0" * 40, {})
            self.assertFalse(self.lock.exists())
            guest.HEAVY_ENTRY_CONTRACT_RELEASED = True
            contract.HEAVY_ENTRY_CONTRACT_RELEASED = False
            with self.assertRaisesRegex(ValueError, "not released"):
                guest.admit(self.root / "request.json", "request-hash", "0" * 40, {})
            self.assertFalse(self.lock.exists())


if __name__ == "__main__":
    unittest.main()
