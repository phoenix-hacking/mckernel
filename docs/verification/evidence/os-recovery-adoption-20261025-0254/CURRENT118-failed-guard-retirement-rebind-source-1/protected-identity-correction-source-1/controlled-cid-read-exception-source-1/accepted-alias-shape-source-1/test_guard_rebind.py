"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retained data and substituted effect leaves only: no pidfd/signal/lock/root calls.
"""
from pathlib import Path
import ast,copy,importlib.util,json,os,signal,types,unittest
from unittest.mock import Mock,patch
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('current118_guard_source_under_test',D/'retire_exact_failed_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Hold(BaseException):pass
class Protocol(unittest.TestCase):
 def run_protocol(self,fail=None):
  events=[];count=[0]
  def snapshot(label,*args):
   events.append(label)
   if fail==label:raise RuntimeError('TEST_ONLY '+label)
   return dict(inputs={'retained':'exact'},clocks=[1793218000,1000000,1015000])
  def publish(path,raw):
   events.append(path.name)
   value=json.loads(raw)
   if path==m.M.PREPARED:self.assertEqual(value['signal_budget'],1)
   if path==m.M.COMPLETE:
    self.assertTrue(value['parent_positive_join_required']);self.assertFalse(value['current_free']);self.assertEqual(value['old_readonly_client_status'],'UNKNOWN')
    if fail=='complete-write':raise OSError('TEST_ONLY durable writer failure')
  def sole(fd):
   events.append('sole-pidfd-signal');count[0]+=1
   if fail=='signal-response':raise OSError('TEST_ONLY uncertain syscall response')
   return dict(syscall=424,signal=9,returncode=0)
  def hold(fd):events.append(('retain-custody',fd));raise Hold()
  def final(*args):
   events.append('final-after-fsync-gate')
   if fail=='final-gate':raise RuntimeError('TEST_ONLY fresh gate refuses')
  ctx=dict(vars(m.M));ctx.update(pidfd_open=lambda:events.append('pidfd-open') or 41,bind_pidfd=lambda fd,p:events.append('bind-pidfd') or dict(pid=m.G['pid'],starttime=m.G['starttime']),publish=publish,sole_sigkill=sole,exit_ready=lambda fd:events.append('positive-exit-ready') or dict(pidfd_exit_ready=True),acquire_root_lock=lambda:events.append('acquire-SAME27:4') or 42,require_lock_holder=lambda pid:events.append(('sole-holder',pid)),quarantine_hold=hold,os=types.SimpleNamespace(getpid=lambda:999999,close=lambda fd:events.append(('close',fd))),signal=types.SimpleNamespace(SIG_BLOCK=0,SIG_SETMASK=2,pthread_sigmask=lambda *args:set(),getsignal=lambda n:None,signal=lambda *args:None))
  with patch.object(m,'bind_release',return_value=(dict(source_checkpoint='a'*40),m.PROFILE)),patch.object(m,'snapshot',side_effect=snapshot),patch.object(m,'final_before_signal',side_effect=final),patch.object(m,'bind_stop_requests'):
   execute,node=m.rebound_protocol(ctx)
   if fail in ('signal-response','after','complete-write'):
    with self.assertRaises(Hold):execute(Path('/TEST_ONLY_RELEASE'), 'b'*64)
   elif fail:
    with self.assertRaises(RuntimeError):execute(Path('/TEST_ONLY_RELEASE'), 'b'*64)
   else:self.assertEqual(execute(Path('/TEST_ONLY_RELEASE'),'b'*64)['status'],'COMPLETE_FAILED_HELPER_RETIREMENT_PENDING_PARENT_JOIN')
  return events,count[0]
 def test_target_owns_lock_until_exit_then_same_inode_acquired_after(self):
  e,n=self.run_protocol();self.assertEqual(n,1)
  self.assertLess(e.index('before1'),e.index('pidfd-open'));self.assertLess(e.index('pidfd-open'),e.index('before2'))
  self.assertLess(e.index(m.M.PREPARED.name),e.index('final-after-fsync-gate'));self.assertLess(e.index('final-after-fsync-gate'),e.index('sole-pidfd-signal'))
  self.assertLess(e.index('sole-pidfd-signal'),e.index('positive-exit-ready'));self.assertLess(e.index('positive-exit-ready'),e.index('acquire-SAME27:4'))
  self.assertLess(e.index(m.M.COMPLETE.name),e.index(('close',42)))
 def test_preproof_and_final_stall_refusal_never_signal_or_acquire(self):
  for fail in ('before1','before2','final-gate'):
   e,n=self.run_protocol(fail);self.assertEqual(n,0);self.assertNotIn('acquire-SAME27:4',e)
 def test_uncertain_signal_consumes_budget_and_retains_custody(self):
  e,n=self.run_protocol('signal-response');self.assertEqual(n,1);self.assertIn(('retain-custody',None),e)
 def test_postproof_or_receipt_failure_keeps_replacement_lock(self):
  for fail in ('after','complete-write'):
   e,n=self.run_protocol(fail);self.assertEqual(n,1);self.assertIn(('retain-custody',42),e);self.assertNotIn(('close',42),e)
 def test_kernel_units_are_original_with_exact_target_no_numeric_fallback(self):
  self.assertEqual(m.T.reference(m.M.__file__)['sha256'],m.B['primitive']['sha256'])
  libc=Mock();libc.syscall.side_effect=[23,0]
  with patch.object(m.M.ctypes,'CDLL',return_value=libc),patch.object(os,'kill') as numeric,patch.object(os,'killpg') as group:
   self.assertEqual(m.M.pidfd_open(),23);self.assertEqual(m.M.sole_sigkill(23)['returncode'],0)
  numeric.assert_not_called();group.assert_not_called();calls=libc.syscall.call_args_list
  self.assertEqual(calls[0].args[0],434);self.assertEqual(calls[0].args[1].value,2232651);self.assertEqual(calls[1].args[0],424);self.assertEqual(calls[1].args[1].value,23)
 def test_fdinfo_rejects_wrong_pid_before_target_identity(self):
  with patch.object(m.M,'proc_bytes',return_value=b'Pid:\t2232652\n'),patch.object(m.M,'guard_identity') as identity,self.assertRaises(m.M.Refusal):m.M.bind_pidfd(41,m.PROFILE)
  identity.assert_not_called()

class BindingAndIdentity(unittest.TestCase):
 def test_retained_current_source_denylist_and_unknown_status(self):
  self.assertTrue(m.data());self.assertEqual(len(m.B['deny_targets']),6);self.assertEqual(len(m.B['prior_actors']),111)
  self.assertEqual(m.PROFILE['first_readonly_client']['status'],'UNKNOWN');self.assertFalse(m.PROFILE['first_readonly_client']['positive_wait4'])
 def test_removing_a_current_control_from_denylist_refused(self):
  bad=copy.deepcopy(m.B);bad['deny_targets'].pop()
  with patch.object(m,'B',bad),self.assertRaises(RuntimeError):m.data()
 def test_old_stopped_container_release_cannot_authorize_pidfd_action(self):
  path=Path(m.G['argv'][5]);digest=m.G['argv'][7]
  with patch.object(m.GUARD,'guard',side_effect=AssertionError('no actual guard')),self.assertRaises(RuntimeError):m.bind_release(path,digest)
 def report(self,before=True):
  rows=[[1,0,'1'],[999999,1,'100'],[2232650,2232649,'103343093']]
  if before:rows.append([2232651,2232650,'103343097'])
  rows.sort();groups=[r+[r[0],r[0]] for r in rows]
  return dict(schema='fp-save-image.proc.v1',uid=0,boot_id=m.B['boot'],challenge='fresh',caller=[999999,'100'],publishers=[[2232651,'103343097','/usr/bin/python3.8']]*2 if before else [],snapshots=[copy.deepcopy(rows),copy.deepcopy(rows)],groups=[copy.deepcopy(groups),copy.deepcopy(groups)])
 def test_two_complete_censuses_and_group_unknown_client_absence(self):
  self.assertTrue(m.validate_process_report(self.report(),'fresh',[999999,'100'],True));self.assertTrue(m.validate_process_report(self.report(False),'fresh',[999999,'100'],False))
  bad=self.report();bad['groups'][0][0][3]=2232653
  with self.assertRaises(RuntimeError):m.validate_process_report(bad,'fresh',[999999,'100'],True)
  bad=self.report(False);bad['groups'][0][0][4]=2232651
  with self.assertRaises(RuntimeError):m.validate_process_report(bad,'fresh',[999999,'100'],False)
 def test_parent_join_mandatory_without_changing_old_client_status(self):
  value=dict(TEST_ONLY=True,author='/root',target_pid=2232651,target_birth='103343097',parent_pid=2232650,parent_birth='103343093',positive_direct_parent_wait=True,returncode=-9,streams_closed=True,tool_session=90401,first_readonly_client_status='UNKNOWN')
  self.assertTrue(m.validate_parent_join(value))
  for key,new in [('positive_direct_parent_wait',False),('returncode',0),('first_readonly_client_status','PASS'),('parent_birth','0')]:
   bad=dict(value);bad[key]=new
   with self.subTest(key=key),self.assertRaises(RuntimeError):m.validate_parent_join(bad)
 def test_prior_new_query_clients_must_be_absent_from_later_full_census(self):
  report=self.report();prior=2232700
  report['snapshots'][0].append([prior,1,'123'])
  report['groups'][0].append([prior,1,'123',prior,prior])
  with self.assertRaises(m.M.Refusal):m.validate_process_report(report,'fresh',[999999,'100'],True,[prior])
  self.assertNotIn(prior,m.M.ABSENT)
 def test_final_clock_and_freshness_after_protected_io_no_signal(self):
  now=[1793218000.,1000000.,1015000.];proof=dict(clocks=list(now));events=[]
  def stall(release):events.append('protected_io');now[0]+=121
  with patch.object(m,'safe',side_effect=stall),patch.object(m.GUARD,'guard',side_effect=lambda:events.append('guardian_io')),patch.object(m.time,'time',side_effect=lambda:now[0]),patch.object(m.time,'monotonic',side_effect=lambda:now[1]),patch.object(m.time,'clock_gettime',side_effect=lambda k:now[2]),self.assertRaisesRegex(RuntimeError,'120s'):m.final_before_signal({},m.PROFILE,[proof,proof],[])
  self.assertEqual(events,['protected_io','guardian_io'])
 def test_readonly_scope_rejects_rm_before_effect(self):
  with patch.object(m,'process_code',return_value='TEST_ONLY'),self.assertRaises(RuntimeError):m.readonly(m.T.PREFIX+['rm','--',m.TB['cid']])
 def test_actual_readonly_wrapper_reaches_final_query_gate_with_existing_transport_interface(self):
  import tempfile
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_guard_query_') as tmp:
   cls,_=m.T.transport(m.TB);commands=cls(Path(tmp),m.T.Stop());seen=[]
   def effect(argv,timeout,check):
    commands.before_popen(argv);seen.append(argv)
    return types.SimpleNamespace(returncode=0,stdout='[]',stderr='')
   with patch.dict(m.STATE,dict(release={},commands=commands),clear=True),patch.object(commands,'exact',side_effect=effect),patch.object(m,'safe',return_value=[1793218000,1000000,1015000]),patch.object(m.GUARD,'guard',return_value=[1793218000,1000000,1015000]),patch.object(m.time,'time',return_value=1793218000),patch.object(m.time,'monotonic',return_value=1000000),patch.object(m.time,'clock_gettime',return_value=1015000):
    result=m.readonly(m.T.PREFIX+['inspect','--type','container',m.TB['cid']]);self.assertEqual(result.returncode,0)
   self.assertEqual(len(seen),1)
 def test_original_protocol_stop_latch_is_shared_with_query_transport(self):
  commands=types.SimpleNamespace(signals=m.T.Stop());requested=[]
  with patch.dict(m.STATE,dict(commands=commands),clear=True):m.bind_stop_requests(requested)
  self.assertIs(commands.signals.requested,requested);requested.append(signal.SIGTERM)
  with self.assertRaises(m.T.Refusal):commands.signals.check()

if __name__=='__main__':unittest.main(verbosity=2)
