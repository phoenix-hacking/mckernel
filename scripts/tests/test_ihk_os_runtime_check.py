"""Regression tests for the source-bound native OS runtime contract."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ihk_os_runtime_check as runtime


class IhkOsRuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-os-runtime-contract-")
        self.repo = Path(self.temporary.name) / "repo"
        for relative in (runtime.CONTRACT, *runtime.INPUTS):
            destination = self.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

    def tearDown(self):
        self.temporary.cleanup()

    def contract(self):
        return json.loads((self.repo / runtime.CONTRACT).read_text(encoding="utf-8"))

    def write_contract(self, contract):
        (self.repo / runtime.CONTRACT).write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def test_contract_binds_historical_and_current_lifecycle_scopes(self):
        derived = runtime.derive_contract(self.repo)
        self.assertEqual(derived, self.contract())
        behavior = derived["behavior"]
        self.assertFalse(behavior["historical_unbooted_v1"]["image_boot"])
        self.assertEqual(
            "NotBooted", behavior["historical_unbooted_v1"]["backend_abi"]["allowed_status"]
        )
        current = behavior["current_boot_application_service_shutdown"]
        self.assertIn("remains NotBooted", current["boot_prepare"])
        self.assertIn("prior admission state unchanged", current["boot_prepare"])
        self.assertIn("may have CPU effects", current["boot_start_nonzero"])
        self.assertIn("ShutdownGuard drop restores", current["shutdown_v5_nonzero"])
        self.assertIn("only an open gate", current["shutdown_admission_rollback"])
        self.assertIn("remains closed", current["closed_gate_retry"])
        self.assertIn("after Ready publication", current["reboot"])
        self.assertIn("nonzero reboot start publishes Failed", current["reboot"])
        self.assertIn("before its AdmissionOwner release", current["owner_release_order"])

    def test_checker_rejects_stale_no_effect_boot_and_blanket_reopen_claims(self):
        contract = self.contract()
        current = contract["behavior"]["current_boot_application_service_shutdown"]
        current["boot_start_nonzero"] = "Failed-without-partial-effects"
        current["boot_prepare"] = "failure publishes Failed and reopens admission"
        current["shutdown_admission_rollback"] = "every pre-effect error reopens admission"
        self.write_contract(contract)
        with self.assertRaisesRegex(ValueError, "contract differs"):
            runtime.validate_repository(self.repo)

    def test_checker_rejects_source_change_without_a_contract_rebind(self):
        source = self.repo / runtime.SOURCE
        source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "contract differs"):
            runtime.validate_repository(self.repo)


if __name__ == "__main__":
    unittest.main()
