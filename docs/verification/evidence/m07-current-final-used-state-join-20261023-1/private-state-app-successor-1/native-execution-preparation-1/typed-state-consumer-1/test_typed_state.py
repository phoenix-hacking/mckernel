"""Functional OS parser fixtures only; no security testing or state instructions.

All output below is modeled TESTONLY text, never a native acceptance record.
Run only under the separately granted ordinary capture profile.
"""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("m07_private_runner", Path(__file__).with_name("native_diagnostic.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def modeled(ospke=True, mpx=True, offset9=2688, early=None):
    """TESTONLY producer grammar; no actual CPUID, app or register state."""
    if early == "maximum":
        rows = ["USED_STATE_CPUID maximum=0000000c insufficient"]
        selected = 0
        reasons = ["NOTEXECUTED osxsave-or-layout"] * 3
    elif early == "osxsave":
        rows = ["USED_STATE_CPUID1 ecx=04000000", "USED_STATE_CPUID7 ebx=00004000 ecx=00000018"]
        selected = 0
        reasons = ["NOTEXECUTED osxsave-or-layout"] * 3
    else:
        rows = ["USED_STATE_CPUID1 ecx=0c000000",
                "USED_STATE_CPUID7 ebx={:08x} ecx={:08x}".format(0x4000 if mpx else 0, 0x18 if ospke else 8),
                "USED_STATE_XCR0=000000000000021f CPUIDD0 eax=0000021f ebx=00000a88 ecx=00000a88 edx=00000000",
                "USED_STATE_COMPONENT id=3 size=64 offset=960 ecx=00000000 edx=00000000",
                "USED_STATE_COMPONENT id=4 size=64 offset=1024 ecx=00000000 edx=00000000",
                "USED_STATE_COMPONENT id=9 size=8 offset={} ecx=00000000 edx=00000000".format(offset9)]
        reasons = ["ELIGIBLE_PENDING" if mpx else "NOTEXECUTED mpx-cpuid-missing"] * 2
        reasons += ["ELIGIBLE_PENDING" if ospke else "NOTEXECUTED ospke-clear"]
        selected = (0x18 if mpx else 0) | (0x200 if ospke else 0)
        if ospke and offset9 == 960 and mpx:
            selected = 0
            reasons = ["NOTEXECUTED overlapping-layout"] * 3
    rows += ["USED_STATE_ELIGIBILITY id={} {}".format(i, reason) for i, reason in zip((3, 4, 9), reasons)]
    rows += ["USED_STATE_REQUIRED=0000000000000218 SELECTED={:016x}".format(selected)]
    if selected == 0:
        rows += ["USED_STATE_NOTEXECUTED no executable selected component"]
    else:
        rows += ["USED_STATE_SYSCALL_PRESERVED mask={:016x} original_restored=1".format(selected),
                 "USED_STATE_FUTEX_PRESERVED mask={:016x} waiter_and_distinct_waker_restored=1".format(selected),
                 "USED_STATE_SIGNAL_PRESERVED mask={:016x} distinct_handler_observed=1 original_restored=1".format(selected)]
        rows += ["USED_STATE_COMPONENT_PRESERVED id={} syscall=1 blocking_futex=1 signal=1 original_restore=1".format(i)
                 for i in (3, 4, 9) if selected & (1 << i)]
        rows += ["USED_STATE_ALL_SELECTED_PRESERVED mask=0000000000000218" if selected == 0x218 else
                 "USED_STATE_PARTIAL required=0000000000000218 notexecuted={:016x}".format(0x218 & ~selected)]
    return ("\n".join(rows) + "\n").encode(), 0 if selected == 0x218 else 77


class TypedStateTests(unittest.TestCase):
    def check(self, data=None, code=None):
        original, rc = modeled()
        return runner.check_state_stdout(original if data is None else data, rc if code is None else code, runner.STATE_ORACLE)

    def reject(self, data, code=0):
        with self.assertRaises(runner.StateOracleError):
            self.check(data, code)

    def test_complete_requires_all_components(self):
        outcome = self.check()
        self.assertTrue(outcome["preservation_pass"])
        self.assertEqual(outcome["selected_mask"], 0x218)

    def test_retained_ospke_clear_is_partial_not_pass(self):
        data, code = modeled(ospke=False)
        result = self.check(data, code)
        self.assertFalse(result["preservation_pass"])
        self.assertEqual(result["notexecuted_mask"], 0x200)
        self.assertEqual(result["component_reasons"][9], "NOTEXECUTED ospke-clear")

    def test_missing_mpx_has_only_pkru_partial(self):
        data, code = modeled(mpx=False)
        self.assertEqual(self.check(data, code)["selected_mask"], 0x200)

    def test_early_maximum_has_no_instructions_or_credit(self):
        data, code = modeled(early="maximum")
        self.assertEqual(self.check(data, code)["selected_mask"], 0)

    def test_missing_osxsave_has_no_xgetbv_rows(self):
        data, code = modeled(early="osxsave")
        self.assertFalse(self.check(data, code)["preservation_pass"])

    def test_overlapping_components_cannot_be_executed(self):
        data, code = modeled(offset9=960)
        self.assertEqual(self.check(data, code)["selected_mask"], 0)

    def test_partial_cannot_exit_zero(self):
        self.reject(modeled(ospke=False)[0])

    def test_complete_cannot_exit_partial(self):
        self.reject(modeled()[0], 77)

    def test_failure_exit_never_preservation(self):
        self.reject(modeled()[0], 1)

    def test_signal_exit_never_preservation(self):
        self.reject(modeled()[0], -11)

    def test_each_boundary_or_restore_claim_required(self):
        data, _ = modeled()
        for marker in (b"original_restored=1", b"waiter_and_distinct_waker_restored=1", b"distinct_handler_observed=1", b"original_restore=1"):
            with self.subTest(marker=marker):
                self.reject(data.replace(marker, marker[:-1] + b"0", 1))

    def test_each_missing_component_report_refused(self):
        data, _ = modeled()
        for i in (3, 4, 9):
            rows = data.splitlines(True)
            self.reject(b"".join(row for row in rows if not row.startswith("USED_STATE_COMPONENT_PRESERVED id={}".format(i).encode())))

    def test_duplicate_or_unknown_row_refused(self):
        data, _ = modeled()
        self.reject(data + data.splitlines(True)[-1])
        self.reject(data + b"UNRECOGNIZED\n")

    def test_row_order_is_frozen(self):
        rows = modeled()[0].splitlines(True)
        rows[-2], rows[-3] = rows[-3], rows[-2]
        self.reject(b"".join(rows))

    def test_truncation_and_nonascii_refused(self):
        data, _ = modeled()
        self.reject(data[:-1])
        self.reject(data + b"\xff\n")
        self.reject(data + b"\x00\n")
        self.reject(b"x" * 16385)

    def test_selected_mask_and_eligibility_not_trusted(self):
        data, _ = modeled(ospke=False)
        self.reject(data.replace(b"NOTEXECUTED ospke-clear", b"ELIGIBLE_PENDING"), 77)
        self.reject(data.replace(b"SELECTED=0000000000000018", b"SELECTED=0000000000000218"), 77)

    def test_layout_u32_or_extent_mismatch_refused(self):
        data, _ = modeled()
        self.reject(data.replace(b"offset=2688", b"offset=4294967296"))
        self.reject(data.replace(b"ebx=00000a88", b"ebx=00000200"))

    def test_wrong_app_or_descriptor_cannot_select_branch(self):
        bad = dict(runner.STATE_ORACLE, app_sha256="0" * 64)
        with self.assertRaises(runner.StateOracleError):
            runner.check_state_stdout(modeled()[0], 0, bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
