"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent pure expectations for restart deltas; no live admission invocation.
"""
import copy
import importlib.util
from pathlib import Path
import unittest
import guardian_guard as g
import test_guardian_guard as fixtures

HERE = Path(__file__).resolve().parent


class RestartBindings(unittest.TestCase):
    def config(self):
        return dict(expected_thread='01a183ec-72e5-7400-8f48-b4efb8725520',
                    credit_run_id='7f4af94a83b14cc08f97401f5891d965',
                    credit_ceiling='57774.852125', credit_spent_floor='22812.3311000000',
                    included_first=True, automatic_credit_purchase=False, api_key_billing=False,
                    initial_watch_clock=dict(boot_deadline=1051043.6959931096,
                        boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', deadline=1793253600,
                        watcher_cutoff_lower=1035704.5689393478,watcher_pid=2109395,watcher_start='101211669'))

    def test_exact_restart_identities_and_clamps(self):
        self.assertEqual(g.THREAD, '01a183ec-72e5-7400-8f48-b4efb8725520')
        self.assertEqual(g.PACKET_SHA, '5bc656cc12b97c2ec5f53312a26e8ef800e45d5451c1f0b5d084576d95ff1b22')
        self.assertEqual(g.INITIAL, {'watcher': (2109395, '101211669'),
                         'worker': (2109397, '101211677'), 'server': (2109399, '101211685')})
        self.assertEqual((g.DEADLINE,g.MONO_CAP,g.BOOT_CAP),
                         (1793253600,1035704.5689393478,1051042.6959879305))
        self.assertEqual(g.WINDOW_BOOT_CAP,1051044.6960026678)
        self.assertEqual(g.ARM_RECEIPT_REF['path'],str(g.CONTROL/'ACTUAL-CONTROLS-ARMED.json'))

    def test_controller_configuration(self):
        config=self.config()
        self.assertEqual(g.validate_control_config(config),config)
        mutations=[('expected_thread','01a18111-26a7-7ef2-bbd6-e33d1c8dc803'),
                   ('credit_run_id','reset'),('credit_ceiling','57775'),('credit_spent_floor','0'),
                   ('included_first',False),('automatic_credit_purchase',True),('api_key_billing',True)]
        for key,value in mutations:
            with self.subTest(key=key):
                candidate=copy.deepcopy(config);candidate[key]=value
                with self.assertRaises(ValueError):g.validate_control_config(candidate)
        for key,value in [('boot_id','other'),('deadline',1793253601),('watcher_pid',1887110),
                          ('watcher_start','96419041'),('boot_deadline',1051043.6959931098),
                          ('watcher_cutoff_lower',1035704.568939348),('watcher_cutoff_lower',float('nan'))]:
            with self.subTest(clock_key=key):
                candidate=copy.deepcopy(config);candidate['initial_watch_clock'][key]=value
                with self.assertRaises(ValueError):g.validate_control_config(candidate)

    def test_parent_receipt_is_mandatory_before_any_io(self):
        with self.assertRaisesRegex(ValueError,'armed receipt not finalized'):
            g.validate_arm_reference(None)
        valid=dict(path=str(g.CONTROL/'ACTUAL-CONTROLS-ARMED.json'),bytes=10,sha256='a'*64)
        self.assertEqual(g.validate_arm_reference(valid),valid)
        for key,value in [('path',str(g.BASE/'ACTUAL-CONTROLS-ARMED.json')),('bytes',True),
                          ('bytes',0),('sha256','0'*63),('sha256','z'*64)]:
            changed=valid.copy();changed[key]=value
            with self.assertRaises(ValueError):g.validate_arm_reference(changed)

    def test_state_billing_and_stop_predicates(self):
        fixture=fixtures.GuardTests();fixture.setUp()
        for key,value in [('automatic_credit_purchase',True),('api_key_billing',True),
                          ('account_wide_balance_guard',False),('mode','api_key')]:
            args=copy.deepcopy(fixture.args);args[3]['settings']['billing'][key]=value
            with self.assertRaises(ValueError):g.validate(*args)
        for key in ('deadline_stop_sent','stop_intent','transition_hold'):
            args=copy.deepcopy(fixture.args);args[1][key]=True
            with self.assertRaises(ValueError):g.validate(*args)

    def test_armed_receipt_and_specific_supervisor_transition(self):
        fixture=fixtures.GuardTests();fixture.setUp()
        armed=fixture.args[8]
        self.assertEqual(g.validate_armed(armed,fixture.procs.get),armed)
        mutations=[('status','PREPARED'),('thread_id','retired'),('native_release',True),
                   ('guardian_packet_sha256','0'*64),('original_window_unchanged_sha256','0'*64),
                   ('steering_interval_seconds',1800)]
        for key,value in mutations:
            candidate=copy.deepcopy(armed);candidate[key]=value
            with self.assertRaises(ValueError):g.validate_armed(candidate,fixture.procs.get)
        for key,value in [('start','597'),('comm','other'),('ppid',2),('state','Z')]:
            procs=copy.deepcopy(fixture.procs);procs[1311][key]=value
            with self.assertRaises(ValueError):g.validate_armed(armed,procs.get)
        for pid in (2111552,2111966,1894242):
            procs=copy.deepcopy(fixture.procs);procs[pid]['ppid']=999
            with self.assertRaises(ValueError):g.validate_armed(armed,procs.get)
        for key in ('deadline_epoch','monotonic_deadline','boot_deadline'):
            candidate=copy.deepcopy(armed);candidate['earliest_control_caps'][key]+=1
            with self.assertRaises(ValueError):g.validate_armed(candidate,fixture.procs.get)

    def test_retired_identity_and_looser_live_clocks_refused(self):
        fixture=fixtures.GuardTests();fixture.setUp()
        for index,key,value in [(3,'thread_id','01a18111-26a7-7ef2-bbd6-e33d1c8dc803'),
                                (1,'packet_sha256','369da48abf196bbe68abc6eb4579deddd8f80fc8522560c9ee983e2ca9ae4203'),
                                (1,'boot_deadline',1051044.6960026678),
                                (1,'finite_watcher_monotonic_deadline',1035705.5689454618)]:
            args=copy.deepcopy(fixture.args);args[index][key]=value
            with self.assertRaises(ValueError):g.validate(*args)


if __name__ == '__main__':unittest.main(verbosity=2)
