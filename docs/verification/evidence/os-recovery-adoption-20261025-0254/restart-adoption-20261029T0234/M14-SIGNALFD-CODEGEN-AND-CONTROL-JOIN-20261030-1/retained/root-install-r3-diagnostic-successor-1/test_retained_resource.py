"""Functional-only synthetic R3 retained-resource check; no process operations."""
import contextlib
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('test_r3_caller',HERE/'prepare_and_exec.py')
caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)


class RetainedResource(unittest.TestCase):
    def test_prior_unknown_four_gib_is_charged_and_global_ceiling_holds(self):
        now=1000000000000
        live={'controls_sha256':'c'*64,'capacity_sha256':'d'*64,
              'caps':{'boot_deadline':2000,'monotonic_deadline':2000,'deadline':2000}}
        actual={'version':1,'weekly_used_percent':95,'weekly_observed_utc_ns':now,'usage_evidence_sha256':'a'*64,
                'service_status':'NO_NEW_REJECTION','sampled_boot_ns':now,'additional_reserved_bytes':4*1024**3,
                'sudo_overhead_reserved_bytes':512*1024**2,'sudo_overhead_observed_bytes':0,
                'deadline_boot_ns':now+150000000000,'deadline_mono_ns':now+150000000000,'utc_cap_ns':now+150000000000,
                'phase1_deadline_boot_ns':now+100000000000,'receipt_expires_boot_ns':now+125000000000,
                'join_capture_reserve_ns':10000000000,'term_grace_ns':3000000000,'kill_grace_ns':5000000000,
                'join_grace_ns':10000000000,'retire_operation_only':False,'controls_sha256':'c'*64,
                'capacity_sha256':'d'*64,'interpreter_sha256':'e'*64}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(caller.time,'clock_gettime_ns',return_value=now))
            stack.enter_context(mock.patch.object(caller.time,'time_ns',return_value=now))
            stack.enter_context(mock.patch.object(caller.time,'monotonic_ns',return_value=now))
            self.assertEqual(caller.fresh_values(actual,live),now)
            with self.assertRaises(ValueError):caller.fresh_values(dict(actual,additional_reserved_bytes=4*1024**3-1),live)
            with self.assertRaises(ValueError):caller.fresh_values(dict(actual,additional_reserved_bytes=5*1024**3),live)


if __name__=='__main__':unittest.main()
