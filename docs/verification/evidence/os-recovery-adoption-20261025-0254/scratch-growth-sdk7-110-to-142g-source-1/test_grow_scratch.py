"""Functional McKernel OS/apps only; pure tests, no root/syscalls/resize."""
import copy
import json
import unittest
from unittest.mock import patch
import grow_scratch as g


class GrowthTests(unittest.TestCase):
    def test_exact_sequence_and_output_order(self):
        events = []
        def run(argv, label, mutating):
            self.assertTrue(mutating)
            events.append(('run', argv))
            return {'returncode': 0}
        results = g.sequence(run, lambda: events.append('before'), lambda: events.append('after'),
                             lambda event, data: events.append((event, data['index'])))
        self.assertEqual(events, ['before'] + [item for i, argv in enumerate(g.COMMANDS)
                         for item in [('mutation_intent', i), ('run', argv)]] + ['after'])
        self.assertEqual(len(results), 3)
        self.assertEqual(g.COMMANDS[0], ['/usr/bin/truncate', '--no-create', '--size=152471339008', g.BACKING])
        self.assertEqual(g.COMMANDS[1:], [['/usr/sbin/losetup', '--set-capacity', '/dev/loop36'],
                                         ['/usr/sbin/resize2fs', '/dev/loop36']])

    def test_preflight_failure_runs_nothing(self):
        runs = []
        def fail():
            raise ValueError('retained-original-preflight')
        with self.assertRaisesRegex(ValueError, 'retained-original-preflight'):
            g.sequence(lambda *x: runs.append(x), fail, lambda: self.fail('postcondition ran'), lambda *x: None)
        self.assertEqual(runs, [])

    def test_each_command_failure_stops_following_commands(self):
        for failed in range(3):
            with self.subTest(failed=failed):
                calls = []
                def run(argv, label, mutating):
                    calls.append(argv)
                    return {'returncode': 1 if len(calls) == failed + 1 else 0}
                with self.assertRaisesRegex(ValueError, 'growth command failed'):
                    g.sequence(run, lambda: None, lambda: self.fail('after failure'), lambda *x: None)
                self.assertEqual(calls, g.COMMANDS[:failed + 1])

    def test_uncertain_child_exception_stops_sequence(self):
        calls = []
        def run(argv, label, mutating):
            calls.append(argv)
            raise TimeoutError('direct child still exists')
        with self.assertRaisesRegex(TimeoutError, 'direct child still exists'):
            g.sequence(run, lambda: None, lambda: self.fail('postcondition ran'), lambda *x: None)
        self.assertEqual(calls, g.COMMANDS[:1])

    def test_postcondition_failure_never_retries(self):
        calls = []
        def failed_after():
            raise ValueError('reserve postcondition original')
        with self.assertRaisesRegex(ValueError, 'reserve postcondition original'):
            g.sequence(lambda argv, *x: calls.append(argv) or {'returncode': 0},
                       lambda: None, failed_after, lambda *x: None)
        self.assertEqual(calls, g.COMMANDS)

    def test_live_account_guard_rejects_stale_or_different_budget(self):
        now = g.END - 1000
        state = dict(phase='running', thread_id='01a170fb-57c3-7ab3-862d-8005bef92a63',
                     heartbeat_at=g.datetime.datetime.fromtimestamp(now, g.datetime.timezone.utc).isoformat(),
                     credit_budget=dict(id='7f4af94a83b14cc08f97401f5891d965', budget='57774.852125', remaining='1'),
                     credit_budget_error=None, last_rate_limits=dict(spendControlReached=False))
        with patch.object(g.Path,'read_text',return_value=json.dumps(state)):
            g.account_guard(now)
            with self.assertRaises(ValueError):
                g.account_guard(now+180)
        for mutate in [lambda s:s['credit_budget'].update(remaining='0'),
                       lambda s:s['credit_budget'].update(id='different'),
                       lambda s:s['last_rate_limits'].update(spendControlReached=True)]:
            wrong=copy.deepcopy(state);mutate(wrong)
            with patch.object(g.Path,'read_text',return_value=json.dumps(wrong)), self.assertRaises(ValueError):
                g.account_guard(now)

    def test_full_capacity_includes_entire_gap_and_growth(self):
        allocated = 102315589632
        required = (g.NEW-g.OLD) + (g.NEW-allocated) + 24*2**30 + 3*2**30
        self.assertEqual(g.full_capacity(required, allocated, 2**30, 2*2**30), required)
        with self.assertRaisesRegex(ValueError, 'HOST'):
            g.full_capacity(required-1, allocated, 2**30, 2*2**30)
        # Immediate allocation plus growth/floors is inadequate for all sparse exposure.
        with self.assertRaises(ValueError):
            g.full_capacity((g.NEW-g.OLD)+27*2**30, allocated, 2**30, 2*2**30)

    def test_reserve_ratio_and_fixed_geometry(self):
        before = dict(uuid=g.UUID, blocksize=4096, blocks=28835840, reserved=288358)
        after = dict(before, blocks=37224448, reserved=372244)
        g.fs_check(before, False); g.fs_check(after, True)
        for value in [0, 288358, 372247]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                g.fs_check(dict(after, reserved=value), True)
        with self.assertRaises(ValueError):
            g.fs_check(dict(after, uuid='different'), True)
        parsed = g.fs_fields('Filesystem UUID: '+g.UUID+'\nBlock size: 4096\nBlock count: 37224448\nReserved block count: 372244\n')
        self.assertEqual(parsed, after)

    def test_readonly_unjoined_and_unknown_spawn_retain_custody(self):
        # Same disposition is used for timeout, signal or unknown Popen acquisition.
        self.assertEqual(g.failure_disposition(False, True, 7, False), 'QUARANTINE')
        self.assertEqual(g.failure_disposition(False, False, 7, False), 'PREFLIGHT_STOP')
        self.assertEqual(g.failure_disposition(True, False, 7, False), 'QUARANTINE')

    def test_post_close_publication_fault_never_claims_retained_fd(self):
        self.assertEqual(g.failure_disposition(True, False, None, True), 'POST_CLOSE_EVIDENCE_FAULT')
        self.assertEqual(g.failure_disposition(False, True, None, True), 'POST_CLOSE_EVIDENCE_FAULT')

    def test_fsize_target_without_widening(self):
        g.fsize_guard(g.resource.RLIM_INFINITY)
        g.fsize_guard(g.NEW)
        with self.assertRaisesRegex(ValueError, 'RLIMIT_FSIZE'):
            g.fsize_guard(g.NEW - 1)

    def test_fixed_cutoff_each_clock_and_boot(self):
        proof_ref = dict(sha256=g.FIXED_CUTOFF_SHA)
        proof = dict(fixed_cutoffs=g.FIXED_CUTOFFS, boot_id=g.FIXED_BOOT_ID)
        before = [x - 1 for x in g.FIXED_CUTOFFS]
        def check(clocks, boot=g.FIXED_BOOT_ID, payload=proof):
            with patch.object(g,'load_ref',return_value=payload), \
                 patch.object(g.Path,'read_text',return_value=boot), \
                 patch.object(g.time,'time',return_value=clocks[0]), \
                 patch.object(g.time,'monotonic',return_value=clocks[1]), \
                 patch.object(g.time,'clock_gettime',return_value=clocks[2]):
                g.fixed_cutoff_guard(proof_ref)
        check(before)
        for index in range(3):
            expired = list(before);expired[index] = g.FIXED_CUTOFFS[index]
            with self.subTest(clock=index), self.assertRaisesRegex(ValueError, 'fixed cutoff reached'):
                check(expired)
        with self.assertRaisesRegex(ValueError, 'boot differs'):
            check(before, boot='different')
        with self.assertRaisesRegex(ValueError, 'proof/boot differs'):
            check(before, payload=dict(proof, fixed_cutoffs=[x+1 for x in g.FIXED_CUTOFFS]))

    def test_grant_review_bindings_and_deadline(self):
        now = g.END - 1000
        source = {'source': 'fixed'}; gr = {'id':'grant'}; rr = {'id':'review'}; cr = {'id':'contract'}
        previous = {'sha256': g.NATIVE2_SHA}
        c = dict(previous_serial_operation=previous, nonce='unique', boot_id='boot', issued_wall=now-1,
                 expires_wall=g.END, account_guard=dict(status='PASS_CURRENT_ACCOUNT_GUARD', observed_wall=now,
                 allowed_until_wall=g.END), source_only=False, execution_authority=True,
                 quiescence=dict(status='PASS_EXCLUSIVE_SCRATCH_GROWTH', observed_wall=now,
                  **{k:True for k in ['no_native_owner','no_Docker_owner','no_other_heavy_owner','no_SDK_lease',
                                      'paused_consumers_reconciled','scratch_exclusive']}),
                 cpu_affinity=[2,3,4,5],jobs=1,address_space_limit=2*2**30,aggregate_limit=12*2**30,
                 native2_current_acceptance={'id':'acceptance'}, fixed_cutoff={'id':'fixed-cutoff'})
        bindings=dict(source=source,previous_serial_operation=previous,nonce='unique',before=g.expected(g.OLD),after=g.expected(g.NEW))
        grant=dict(status='GRANTED_SCRATCH_GROWTH_110_TO_142G',bindings=bindings,contract=cr,commands=g.COMMANDS,lower_reserves=False)
        review=dict(decision='PASS_SCRATCH_GROWTH_EXECUTION',grant=gr,bindings=bindings,implementation_ownership=False,reviewer='independent')
        acceptance=dict(decision='PASS_ACTUAL_NATIVE2_POSTJOIN_CURRENT_PHYSICAL', independent=True)
        def check(c0, g0, r0, when=now):
            docs={'contract':c0,'grant':g0,'review':r0,'acceptance':acceptance}
            with patch.object(g,'load_ref',side_effect=lambda x: {} if 'sha256' in x else docs[x['id']]), \
                 patch.object(g,'account_guard'), patch.object(g,'fixed_cutoff_guard'), patch.object(g.Path,'read_text',return_value='boot'):
                return g.authority(source,gr,rr,cr,when)
        check(c,grant,review)
        self.assertEqual(g.MAX_SNAPSHOT_AGE_SECONDS, 120)
        for snapshot in ('account_guard', 'quiescence'):
            age120 = copy.deepcopy(c)
            age120[snapshot]['observed_wall'] = now - 120
            check(age120, grant, review)
            age121 = copy.deepcopy(c)
            age121[snapshot]['observed_wall'] = now - 121
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                check(age121, grant, review)
        cases=[]
        for key,value in [('commands',g.COMMANDS[:2]),('lower_reserves',True),('bindings',{})]:
            wrong=copy.deepcopy(grant);wrong[key]=value;cases.append((c,wrong,review))
        wrong=copy.deepcopy(review);wrong['implementation_ownership']=True;cases.append((c,grant,wrong))
        for key,value in [('source_only',True),('expires_wall',now+100),('boot_id','wrong'),('jobs',2)]:
            wrong=copy.deepcopy(c);wrong[key]=value;cases.append((wrong,grant,review))
        wrong=copy.deepcopy(c);wrong['quiescence']['no_SDK_lease']=False;cases.append((wrong,grant,review))
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                check(*args)

if __name__ == '__main__':
    unittest.main(verbosity=2)
