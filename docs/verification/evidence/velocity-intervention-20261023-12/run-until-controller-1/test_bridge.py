"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline state/clock/process/API doubles only; no subprocess, signal or model call.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import ctypes
import errno
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('private_run_bridge', Path(__file__).with_name('bridge.py'))
b = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(b)
NOW = b.DEADLINE-3600


def state(reason=None, phase='running'):
    return dict(thread_id=b.THREAD, phase=phase, goal={'status': 'active'}, stop_reason=reason,
                settings={'billing': {'mode': 'included_only'}},
                last_rate_limits={'primary': {'usedPercent': 30, 'windowDurationMins': 10080},
                                  'credits': {'hasCredits': True, 'unlimited': False, 'balance': '57774.852125'}})


def decide(s=None, journal=None, now=NOW, retired=False, free=False, permit=None, cancelled=False):
    return b.decide(s or state(), journal or {}, now, retired, free, 'exact-state', permit, cancelled)


class BridgeTests(unittest.TestCase):
    def test_live_resident_untouched_even_with_available_credits(self):
        self.assertEqual(decide(), 'WAIT_RESIDENT_UNCHANGED')

    def test_only_local_real_weekly_exhaustion_is_automatic(self):
        s = state('included_usage_guard', 'stopped'); s['goal']['status'] = 'paused'
        s['last_rate_limits']['primary']['usedPercent'] = 100
        self.assertEqual(decide(s, retired=True, free=True), 'START_EXISTING_LAUNCHER_RECOVERY_ONLY')
        for duration, used in [(300, 100), (10080, 99), (10080, float('inf')), (10080, True)]:
            sample = copy.deepcopy(s); sample['last_rate_limits']['primary'].update(windowDurationMins=duration, usedPercent=used)
            self.assertTrue(decide(sample, retired=True, free=True).startswith('HOLD_'))

    def test_ambiguous_quota_credit_auth_unknown_stops_never_retry(self):
        for reason in ['quota_exhausted', 'credit_balance_decreased', 'credit_balance_unknown',
                       'included_usage_unknown', 'credit_budget_exhausted', 'launcher_error', 'turn_failed']:
            s = state(reason, 'stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
            self.assertTrue(decide(s, retired=True, free=True).startswith('HOLD_'), reason)

    def test_service_hold_wins_even_over_local_guard_or_permit(self):
        s = state('included_usage_guard', 'stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
        for info in ['cyberPolicy', 'authRequired', 'billingHold', {'quota': 'held'}]:
            sample = copy.deepcopy(s); sample['last_error'] = {'codexErrorInfo': info}
            self.assertTrue(decide(sample, retired=True, free=True).startswith('HOLD_'))

    def test_positive_retirement_and_lease_are_both_required(self):
        s = state('included_usage_guard', 'stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
        for retired, free in [(False, False), (True, False), (False, True)]:
            self.assertEqual(decide(s, retired=retired, free=free), 'WAIT_POSITIVE_OLD_MODEL_RETIREMENT_AND_LEASES')

    def test_managed_handoff_needs_final_state_hash_current_resume_and_expiry(self):
        s = state('signal_15', 'stopped'); s['goal']['status'] = 'paused'
        self.assertIn('NO_RESUME', decide(s, retired=True, free=True))
        permit = dict(status='PASS_COORDINATED_MODEL_HANDOFF', thread_id=b.THREAD, deadline=b.DEADLINE,
                      stopped_state_sha256='exact-state', explicit_resume_authorized=True,
                      reason='managed_credit_enablement', review_id='root-final-state-review', expires_unix=NOW+60)
        self.assertEqual(decide(s, retired=True, free=True, permit=permit), 'START_EXISTING_LAUNCHER_RECOVERY_ONLY')
        for key, value in [('stopped_state_sha256','old'), ('explicit_resume_authorized',False), ('expires_unix',NOW)]:
            bad = dict(permit); bad[key] = value
            self.assertIn('NO_RESUME', decide(s, retired=True, free=True, permit=bad))

    def test_later_user_cancel_wins_permit_and_credit(self):
        self.assertEqual(decide(cancelled=True), 'DRAIN_USER_STOP')
        self.assertEqual(decide(state('signal_15'), cancelled=True), 'STOP_USER_STOP')

    def test_deadline_original_one_signal_and_already_draining_skip(self):
        self.assertEqual(decide(now=b.DEADLINE), 'DRAIN_DEADLINE')
        self.assertEqual(decide(journal={'deadline_stop_sent':True}, now=b.DEADLINE), 'WAIT_DEADLINE_DRAIN')
        for s in [state('work_window'), state('signal_15'), state('included_usage_guard')]:
            self.assertEqual(decide(s, now=b.DEADLINE), 'WAIT_DEADLINE_DRAIN')

    def test_finite_watcher_expiry_never_receives_second_bridge_signal(self):
        self.assertEqual(decide(journal={'credit_started':True}, now=b.DEADLINE), 'WAIT_FINITE_WATCHER_DRAIN')
        self.assertEqual(decide(journal={'credit_started':True}, now=b.DEADLINE, retired=True), 'STOP_DEADLINE')

    def test_no_model_start_at_deadline_and_no_unknown_outer_restarts(self):
        s = state('included_usage_guard','stopped'); s['last_rate_limits']['primary']['usedPercent'] = 100
        self.assertEqual(decide(s, now=b.DEADLINE, retired=True, free=True), 'STOP_DEADLINE')
        self.assertEqual(decide(journal={'launch_intent':{}}, retired=True, free=True), 'HOLD_UNCERTAIN_LAUNCH_NO_RETRY')
        self.assertEqual(decide(journal={'launch_intent':{'at':NOW}}), 'HOLD_UNCERTAIN_LAUNCH_NO_RETRY')
        self.assertEqual(decide(journal={'credit_started':True}, retired=True), 'STOP_CREDIT_WATCHER_EXIT_NO_RESTART')

    def test_boot_clock_survives_rollback_suspend_and_rearm(self):
        anchor = 10000
        self.assertEqual(b.effective_now(b.DEADLINE-5000, anchor, anchor), b.DEADLINE)
        self.assertEqual(b.effective_now(b.DEADLINE-20, anchor+5, anchor), b.DEADLINE+5)
        # A previously observed earlierUTC deadline remains latched after a
        # backward correction and after reloading the same retainedjournal.
        self.assertEqual(b.effective_now(b.DEADLINE-5000, anchor-5000, anchor, b.DEADLINE),b.DEADLINE)

    def test_forward_utc_step_stops_finite_worker_once_outside_its_drain_window(self):
        j={'credit_started':True,'finite_remaining_watch':1000}
        self.assertEqual(decide(journal=j,now=b.DEADLINE),'DRAIN_EARLIER_UTC_DEADLINE')
        self.assertEqual(decide(journal=dict(j,deadline_stop_sent=True),now=b.DEADLINE),'WAIT_FINITE_WATCHER_DRAIN')
        self.assertEqual(decide(state('work_window'),journal=j,now=b.DEADLINE),'WAIT_FINITE_WATCHER_DRAIN')
        self.assertEqual(decide(journal=dict(j,finite_remaining_watch=30),now=b.DEADLINE),'WAIT_FINITE_WATCHER_DRAIN')

    def test_preexpiry_forward_backward_rearm_latches_future_cutoff(self):
        saved=b.tighten_cutoff(10000,b.DEADLINE-600,100)
        self.assertEqual(saved,700)
        # The persisted future cutoff survives rearm and a rollback while
        # BOOTTIME advances the remaining600s; the fixed watcher clock does not.
        rearmed=json.loads(json.dumps({'boot_deadline':saved,'finite_watcher_monotonic_deadline':10000}))
        saved=b.tighten_cutoff(rearmed['boot_deadline'],b.DEADLINE-3600,700)
        self.assertEqual(saved,700)
        now=b.effective_now(b.DEADLINE-3600,700,saved)
        self.assertEqual(now,b.DEADLINE)
        self.assertEqual(rearmed['finite_watcher_monotonic_deadline'],10000)
        self.assertEqual(decide(journal={'credit_started':True,'finite_remaining_watch':9300},now=now),
                         'DRAIN_EARLIER_UTC_DEADLINE')

    def test_expiry_and_user_stop_win_over_transition_holds(self):
        s=state();s['service_hold']=True
        self.assertEqual(decide(s,now=b.DEADLINE),'DRAIN_DEADLINE')
        self.assertEqual(decide(s,cancelled=True),'DRAIN_USER_STOP')
        self.assertEqual(decide(journal={'last_clock':b.DEADLINE},now=NOW),'DRAIN_DEADLINE')

    def test_exact_process_retirement_no_pid_arithmetic(self):
        chain = {'watcher':{'pid':9,'start':'11'},'worker':{'pid':50,'start':'12'},'server':{'pid':97,'start':'13'}}
        self.assertTrue(b.old_gone(chain, lambda pid: None))
        self.assertTrue(b.old_gone(chain, lambda pid: {'start':'different'}))
        self.assertFalse(b.old_gone(chain, lambda pid: {'start':chain['worker']['start'] if pid==50 else 'different'}))
        with self.assertRaises(PermissionError):
            b.old_gone(chain, lambda pid: (_ for _ in ()).throw(PermissionError('unknown')))

    def test_fresh_triplet_binds_ppids_and_server_birth(self):
        rows={9:dict(pid=9,start='11',ppid=1,state='S'),50:dict(pid=50,start='12',ppid=9,state='S'),
              97:dict(pid=97,start='13',ppid=50,state='S')}
        s=dict(worker_pid=50,server_pid=97,server_start='13')
        self.assertEqual(b.bind(s, {'watcher_pid':9}, rows.get)['worker']['pid'],50)
        rows[97]['ppid']=49
        with self.assertRaises(ValueError): b.bind(s,{'watcher_pid':9},rows.get)

    def test_prepaid_ceiling_and_unknown_balances(self):
        self.assertEqual(b.prepaid_budget(state()), '57774.852125')
        for balance in ['0','NaN','-1']:
            s=state();s['last_rate_limits']['credits']['balance']=balance
            with self.assertRaises((ValueError,ArithmeticError)): b.prepaid_budget(s)
        s=state();s['last_rate_limits']['credits']['balance']='99999'
        self.assertEqual(b.prepaid_budget(s),'57774.852125')

    def test_restart_reuses_original_vetoes_but_rejects_generic_unknown(self):
        yes=lambda *args:True; no=lambda *args:False
        self.assertFalse(b.strict_restart(yes,-9,state()))
        self.assertFalse(b.strict_restart(yes,0,state()))
        self.assertTrue(b.strict_restart(yes,24,dict(state('active_goal_did_not_continue'),retryable=True)))
        self.assertFalse(b.strict_restart(no,24,dict(state('active_goal_did_not_continue'),retryable=True)))
        for s in [dict(state('launcher_error'),retryable=True),state('rate_limit'),
                  dict(state('server_error'),last_error={'codexErrorInfo':'serverOverloaded'})]:
            self.assertFalse(b.strict_restart(yes,-9,s))
            self.assertFalse(b.strict_restart(yes,-9,s,watchdog=True))
        self.assertTrue(b.strict_restart(yes,-9,state('watchdog_recovery'),watchdog=True))

    def test_stable_credit_id_and_no_fresh_session_flags(self):
        cfg={'deadline_utc':'2026-10-25T00:00:00Z','credit_run_id':'a'*32}
        first=b.launcher_argv(cfg,'100',9999,'fixedpacket','fixednote')
        second=b.launcher_argv(cfg,'100',9999,'fixedpacket','fixednote')
        self.assertEqual(first,second)
        self.assertEqual(first[first.index('--credit-run-id')+1],'a'*32)
        self.assertNotIn('--fresh-session',first)
        self.assertNotIn('--fresh-on-recovery',first)
        self.assertIn('--boot-deadline',first)
        self.assertEqual(first[first.index('--startup-instruction-sha256')+1],'fixednote')

    def test_frozen_packet_note_and_canonical_source_drift_refuse(self):
        root=Path('/mock-private')
        private={'bridge.py':b'bridge','finite_launcher.py':b'entry','CURRENT-INVOCATION.txt':b'currentnote'}
        canonical={'run_os_goal.py':b'launcher','watch_os_goal.py':b'watch','os_goal_credits.py':b'budget'}
        packet={'private':{n:b.digest(v) for n,v in private.items()},'canonical':{n:b.digest(v) for n,v in canonical.items()}}
        wire=json.dumps(packet).encode(); sha=b.digest(wire)
        def read(path):
            if path==root/'FROZEN-PACKET.json':return wire
            if path.parent==root:return private[path.name]
            return canonical[path.name]
        with patch.object(b,'HERE',root),patch.object(Path,'read_bytes',read):
            self.assertEqual(b.verify_packet(sha),packet)
            private['CURRENT-INVOCATION.txt']=b'drift'
            with self.assertRaisesRegex(ValueError,'startup drift'):b.verify_packet(sha)
            private['CURRENT-INVOCATION.txt']=b'currentnote';canonical['watch_os_goal.py']=b'drift'
            with self.assertRaisesRegex(ValueError,'existing launcher'):b.verify_packet(sha)
            with self.assertRaisesRegex(ValueError,'frozen packet'):b.verify_packet('0'*64)

    def test_owned_replacement_watcher_is_polled_reaped_and_never_relaunched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); campaign=root/'campaign'; campaign.mkdir(); private=root/'private';private.mkdir()
            s=state('included_usage_guard','stopped');s['goal']['status']='paused'
            s['last_rate_limits']['primary']['usedPercent']=100
            raw=json.dumps(s).encode();(campaign/'state.json').write_bytes(raw)
            (private/'CURRENT-INVOCATION.txt').write_text('explicit current recovery-only instruction')
            journal=dict(original={name:{'pid':pid,'start':'old'} for name,pid in [('watcher',9),('worker',50),('server',97)]},
                         boot_id='mockboot',boot_deadline=3700,credit_run_id='a'*32,deadline=b.DEADLINE,last_clock=NOW,packet_sha256='packet')
            (private/'journal.json').write_text(json.dumps(journal))
            cfg=dict(deadline_utc='2026-10-25T00:00:00Z',credit_run_id='a'*32)
            alive=[True]
            class Child:
                pid=12345
                polls=0
                def poll(self):
                    self.polls+=1;alive[0]=False;return 0
            child=Child()
            def observed(pid):
                return dict(pid=pid,start='replacement',ppid=1,state='S') if pid==child.pid and alive[0] else None
            sleeps=[0]
            def sleep(unused):
                sleeps[0]+=1
                if sleeps[0]>2:raise AssertionError('replacement child was not reaped')
            with patch.object(b,'HERE',private),patch.object(b,'CAMPAIGN',campaign),\
                 patch.object(b,'birth',side_effect=observed),patch.object(b,'old_gone',return_value=True),\
                 patch.object(b,'leases_free',return_value=True),patch.object(b.time,'time',return_value=NOW),\
                 patch.object(b.time,'clock_gettime',return_value=100),patch.object(b.time,'monotonic',return_value=100),\
                 patch.object(b.time,'sleep',side_effect=sleep),\
                 patch.object(Path,'read_text',return_value='mockboot'),\
                 patch.object(b,'verify_packet',return_value={'private':{'CURRENT-INVOCATION.txt':'fixednote'}}),\
                 patch.object(b.subprocess,'Popen',return_value=child) as popen,patch.object(b,'stop_worker') as stop:
                self.assertEqual(b.run(cfg,'packet'),'STOP_CREDIT_WATCHER_EXIT_NO_RESTART')
            self.assertEqual(popen.call_count,1);self.assertEqual(child.polls,1);stop.assert_not_called()
            self.assertEqual((campaign/'state.json').read_bytes(),raw)

    def test_rearm_source_drift_keeps_guardian_through_preexpiry_forward_backward_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);campaign=root/'campaign';campaign.mkdir();private=root/'private';private.mkdir()
            s=state();s['service_hold']=True
            (campaign/'state.json').write_text(json.dumps(s))
            chain={name:dict(pid=pid,start='old',ppid=1,state='S') for name,pid in [('watcher',9),('worker',50),('server',97)]}
            journal=dict(original=chain,boot_id='mockboot',boot_deadline=3700,credit_run_id='a'*32,
                         deadline=b.DEADLINE,last_clock=NOW,packet_sha256='packet')
            (private/'journal.json').write_text(json.dumps(journal))
            clock=[NOW];boot=[100];gone=[False];sleeps=[0]
            def sleep(unused):
                sleeps[0]+=1
                if sleeps[0]>4:raise AssertionError('guardian lost latched future expiry')
                if sleeps[0]==1:
                    clock[0]=b.DEADLINE-600;boot[0]=105
                elif sleeps[0]==2:
                    clock[0]=NOW;boot[0]=705
            def stop(binding):
                gone[0]=True;current=state('signal_15','stopped');current['goal']['status']='paused'
                (campaign/'state.json').write_text(json.dumps(current))
            with patch.object(b,'HERE',private),patch.object(b,'CAMPAIGN',campaign),\
                 patch.object(b,'verify_packet',side_effect=ValueError('existing launcher source drift')),\
                 patch.object(b,'bind',return_value=chain),\
                 patch.object(b,'read',side_effect=lambda path: {'watcher_pid':9} if path.name=='watcher.json' else json.loads(path.read_bytes())),\
                 patch.object(b,'old_gone',side_effect=lambda unused:gone[0]),patch.object(b,'leases_free',return_value=False),\
                 patch.object(b.time,'time',side_effect=lambda:clock[0]),\
                 patch.object(b.time,'clock_gettime',side_effect=lambda unused:boot[0]),\
                 patch.object(b.time,'monotonic',return_value=100),\
                 patch.object(b.time,'sleep',side_effect=sleep),patch.object(Path,'read_text',return_value='mockboot'),\
                 patch.object(b,'stop_worker',side_effect=stop) as signal_call,patch.object(b.subprocess,'Popen') as spawn:
                self.assertEqual(b.run(dict(deadline_utc='2026-10-25T00:00:00Z',credit_run_id='a'*32),'packet'),'STOP_DEADLINE')
            self.assertEqual(signal_call.call_count,1);spawn.assert_not_called()
            retained=json.loads((private/'journal.json').read_bytes())
            self.assertEqual(retained['boot_deadline'],705)
            self.assertIn('source drift',retained['transition_hold'])

    def test_foreign_watcher_hold_preserves_original_and_never_signals_foreign_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);campaign=root/'campaign';campaign.mkdir();private=root/'private';private.mkdir()
            (campaign/'state.json').write_text(json.dumps(state()))
            original={name:dict(pid=pid,start='old',ppid=1,state='S') for name,pid in [('watcher',9),('worker',50),('server',97)]}
            foreign={name:dict(pid=pid,start='foreign',ppid=1,state='S') for name,pid in [('watcher',10),('worker',51),('server',98)]}
            journal=dict(original=original,boot_id='mockboot',boot_deadline=3700,credit_run_id='a'*32,
                         deadline=b.DEADLINE,last_clock=NOW,packet_sha256='packet')
            (private/'journal.json').write_text(json.dumps(journal))
            clock=[b.DEADLINE-1];gone=[False];sleeps=[0]
            def sleep(unused):
                sleeps[0]+=1
                if sleeps[0]>2:raise AssertionError('foreign watcher replaced trusted lineage')
                clock[0]=b.DEADLINE
                if sleeps[0]==2:gone[0]=True
            def retired(binding):
                self.assertEqual(binding,original)
                return gone[0]
            with patch.object(b,'HERE',private),patch.object(b,'CAMPAIGN',campaign),\
                 patch.object(b,'verify_packet',return_value={}),patch.object(b,'bind',return_value=foreign),\
                 patch.object(b,'read',side_effect=lambda path: {'watcher_pid':10} if path.name=='watcher.json' else json.loads(path.read_bytes())),\
                 patch.object(b,'old_gone',side_effect=retired),patch.object(b,'leases_free',return_value=False),\
                 patch.object(b.time,'time',side_effect=lambda:clock[0]),patch.object(b.time,'clock_gettime',return_value=100),\
                 patch.object(b.time,'monotonic',return_value=100),patch.object(b.time,'sleep',side_effect=sleep),\
                 patch.object(Path,'read_text',return_value='mockboot'),\
                 patch.object(b,'stop_worker') as signal_call,patch.object(b.subprocess,'Popen') as spawn:
                self.assertEqual(b.run(dict(deadline_utc='2026-10-25T00:00:00Z',credit_run_id='a'*32),'packet'),'STOP_DEADLINE')
            signal_call.assert_not_called();spawn.assert_not_called()
            retained=json.loads((private/'journal.json').read_bytes())
            self.assertEqual(retained['original'],original)
            self.assertTrue(retained.get('transition_hold'))

    def test_private_entry_recalculates_finite_window_without_real_launcher(self):
        import sys,types
        path=Path(__file__).with_name('finite_launcher.py')
        spec=importlib.util.spec_from_file_location('private_finite_entry',path)
        entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
        captured=[]
        fake_watch=types.SimpleNamespace(should_restart=lambda *args:True,
             supervise=lambda args,*rest:captured.append(args.hours) or 0)
        fake_goal=types.SimpleNamespace(main=lambda argv:fake_watch.supervise(types.SimpleNamespace(hours=0),None))
        with patch.dict(sys.modules,{'bridge':b,'run_os_goal':fake_goal,'watch_os_goal':fake_watch}),\
             patch.object(sys,'path',list(sys.path)),patch.object(b,'verify_packet',return_value={}) as verify,\
             patch.object(entry.time,'time',return_value=NOW),patch.object(entry.time,'clock_gettime',return_value=100):
            self.assertEqual(entry.main(['--deadline-utc','2026-10-25T00:00:00Z','--boot-deadline','3700',
                                         '--packet-sha256','pinned','--','--credit-budget','100']),0)
        self.assertAlmostEqual(captured[0],3599/3600);self.assertEqual(verify.call_count,2)

    def test_pidfd_prefers_callable_python_builtins(self):
        with patch.object(b.os,'pidfd_open',create=True,return_value=17) as opened,\
             patch.object(b.signal,'pidfd_send_signal',create=True) as sent,\
             patch.object(b,'_linux_pidfd_syscall') as fallback:
            self.assertEqual(b.pidfd_open(123),17)
            b.pidfd_send_signal(17,0)
        opened.assert_called_once_with(123,0)
        sent.assert_called_once_with(17,0,None,0)
        fallback.assert_not_called()

    def test_pidfd_fallback_exact_typed_arguments_and_errno_loader(self):
        syscall=Mock(side_effect=[17,0,0]);library=SimpleNamespace(syscall=syscall)
        with patch.object(b.os,'pidfd_open',None,create=True),\
             patch.object(b.signal,'pidfd_send_signal',None,create=True),\
             patch.object(b.os,'uname',return_value=SimpleNamespace(sysname='Linux',machine='x86_64')),\
             patch.object(b.ctypes,'CDLL',return_value=library) as load:
            self.assertEqual(b.pidfd_open(123),17)
            self.assertIsNone(b.pidfd_send_signal(17,0))
            self.assertIsNone(b.pidfd_send_signal(17,b.signal.SIGTERM))
        self.assertIs(syscall.restype,ctypes.c_long)
        self.assertEqual(load.call_count,3)
        for call in load.call_args_list:self.assertEqual(call.args,(None,));self.assertEqual(call.kwargs,{'use_errno':True})
        opened=syscall.call_args_list[0].args;sent=syscall.call_args_list[1].args
        self.assertEqual([type(v) for v in opened],[ctypes.c_long,ctypes.c_int,ctypes.c_uint])
        self.assertEqual([v.value for v in opened],[434,123,0])
        self.assertEqual([type(v) for v in sent],[ctypes.c_long,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint])
        self.assertEqual([v.value for v in sent],[424,17,0,None,0])
        term=syscall.call_args_list[2].args
        self.assertEqual([type(v) for v in term],[ctypes.c_long,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint])
        self.assertEqual([v.value for v in term],[424,17,int(b.signal.SIGTERM),None,0])

    def test_pidfd_fallback_errno_propagates_for_open_and_send(self):
        def denied(*unused):
            ctypes.set_errno(errno.EPERM)
            return -1
        library=SimpleNamespace(syscall=Mock(side_effect=denied))
        with patch.object(b.os,'pidfd_open',None,create=True),\
             patch.object(b.signal,'pidfd_send_signal',None,create=True),\
             patch.object(b.os,'uname',return_value=SimpleNamespace(sysname='Linux',machine='x86_64')),\
             patch.object(b.ctypes,'CDLL',return_value=library):
            for operation in (lambda:b.pidfd_open(123),lambda:b.pidfd_send_signal(17,0)):
                with self.assertRaises(OSError) as caught:operation()
                self.assertEqual(caught.exception.errno,errno.EPERM)

    def test_pidfd_fallback_rejects_other_architecture_without_syscall(self):
        with patch.object(b.os,'pidfd_open',None,create=True),\
             patch.object(b.os,'uname',return_value=SimpleNamespace(sysname='Linux',machine='aarch64')),\
             patch.object(b.ctypes,'CDLL') as load:
            with self.assertRaises(NotImplementedError):b.pidfd_open(123)
        load.assert_not_called()

    def test_stop_worker_closes_pidfd_on_success_identity_change_and_signal_errno(self):
        chain={'worker':dict(pid=123,start='bound'), 'watcher':dict(pid=9)}
        for changed,send_error in [(False,None),(True,None),(False,OSError(errno.EPERM,'denied'))]:
            observed=dict(pid=123,start='changed' if changed else 'bound',ppid=9)
            with patch.object(b,'pidfd_open',return_value=17) as opened,\
                 patch.object(b,'pidfd_send_signal',side_effect=send_error) as sent,\
                 patch.object(b.os,'close') as close:
                if changed:
                    with self.assertRaises(ValueError):b.stop_worker(chain,lambda pid:observed)
                    sent.assert_not_called()
                elif send_error:
                    with self.assertRaises(OSError) as caught:b.stop_worker(chain,lambda pid:observed)
                    self.assertEqual(caught.exception.errno,errno.EPERM)
                else:b.stop_worker(chain,lambda pid:observed)
                if not changed:sent.assert_called_once_with(17,b.signal.SIGTERM)
                opened.assert_called_once_with(123);close.assert_called_once_with(17)

    def test_stop_worker_open_failure_never_signals_or_closes_unknown_fd(self):
        with patch.object(b,'pidfd_open',side_effect=OSError(errno.ESRCH,'gone')),\
             patch.object(b,'pidfd_send_signal') as sent,patch.object(b.os,'close') as close:
            with self.assertRaises(OSError) as caught:b.stop_worker({'worker':{'pid':123}})
        self.assertEqual(caught.exception.errno,errno.ESRCH)
        sent.assert_not_called();close.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
