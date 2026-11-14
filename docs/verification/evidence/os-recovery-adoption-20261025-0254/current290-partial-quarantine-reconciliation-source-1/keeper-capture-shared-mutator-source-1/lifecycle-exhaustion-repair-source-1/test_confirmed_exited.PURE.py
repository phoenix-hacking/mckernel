"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
All process operations below use private virtual fixtures; no production scanner.
"""
import ast,errno,importlib.util,types,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
OLD=D.parents[2]/'current290-dead-caller-proc-snapshot-lifecycle-source-1/whole-pair-enoent-correction-source-1/test_whole_pair_correction.PURE.py'
spec=importlib.util.spec_from_file_location('retained_whole_pair_tests',OLD);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
OriginalRunner=old.Runner;Refusal=old.Refusal
class Runner(OriginalRunner):
 def __init__(self,corrected=True):
  super().__init__(corrected)
  self.ns['_DEAD_CALLER_RETAINED_HISTORY_SEED']=dict(observed_births={},observed_pids=[],confirmed_exited_pids=[],prior_compact_sequences=[])
  self.directories_absent=set();self.directory_errors={};self.directory_calls=[]
  if corrected:
   raw=(D/'dead_caller_confirmed_exited.FOCUSED-FUNCTIONS.SOURCE-ONLY.py').read_bytes()
   exec(compile(ast.parse(raw),str(D/'dead_caller_confirmed_exited.FOCUSED-FUNCTIONS.SOURCE-ONLY.py'),'exec'),self.ns)
  def stat(path,follow_symlinks=False):
   self.directory_calls.append(path);count=self.directory_calls.count(path)
   if (path,count) in self.directory_errors:raise self.directory_errors[path,count]
   if int(path.split('/')[2]) in self.directories_absent:raise FileNotFoundError(errno.ENOENT,'exited',path)
   return types.SimpleNamespace()
  self.ns['os'].stat=stat
 def exited(self,pid):
  self.directories_absent.add(pid)
  for count in range(1,9):self.missing('/proc/%d/stat'%pid,count)
old.Runner=Runner
class RetainedControls(old.WholePair):
 def test_observer_birth_change_after_partial_refuses(self):
  r=Runner();r.missing('/proc/77/cmdline');calls=[0]
  def observer(pid):
   calls[0]+=1;return dict(pid=88,starttime='999' if calls[0]>2 else '555',uids=[0]*4,gids=[0]*4)
  r.ns['same_ofd_process']=observer
  with self.assertRaisesRegex(Refusal,'observer-raced'):r.run()
  self.assertEqual(r.enumerations,1)
 # Narrow new semantics: unconfirmed first-read loss cannot retry itself benign.
 def test_first_stat_enoent_restarts_entire_pair(self):
  r=Runner();r.missing('/proc/77/stat')
  with self.assertRaisesRegex(Refusal,'exited-pid-reappeared'):r.run()
  self.assertEqual(r.enumerations,1)
 def test_three_incomplete_pairs_refuse(self):
  # Unchanged three retries apply to later-stage incomplete reads.
  r=Runner();r.missing('/proc/77/cmdline',1);r.missing('/proc/77/cmdline',2);r.missing('/proc/77/cmdline',3)
  with self.assertRaisesRegex(Refusal,'retry-exhausted'):r.run()
  self.assertEqual(r.enumerations,3)
class ConfirmedExited(unittest.TestCase):
 def fixture(self):
  r=Runner();r.exited(77);r.batches=[['1','77','88'],['1','88']];return r
 def test_minimized_original_three_distinct_first_stat_losses_exhaust(self):
  r=OriginalRunner();r.batches=[['1','77','88'],['1','78','88'],['1','79','88']]
  for pid in (77,78,79):r.missing('/proc/%d/stat'%pid)
  with self.assertRaisesRegex(Refusal,'retry-exhausted'):r.run()
  self.assertEqual(r.enumerations,3)
  self.assertEqual([row['status'] for row in r.observations()],['REFUSED']*3)
 def test_three_distinct_exited_entries_complete_same_two_snapshots(self):
  r=Runner();r.batches=[['1','77','78','79','88'],['1','88']]
  for pid in (77,78,79):r.exited(pid)
  r.run();self.assertEqual(r.enumerations,2)
  observation=r.observations()[0]
  self.assertEqual(observation['status'],'PASS_CURRENT_PAIR_WITH_CONFIRMED_EXITED_ROWS')
  self.assertEqual({row['pid'] for row in observation['current_absence_rows']},{77,78,79})
  self.assertEqual(len(observation['raw_full_eof_snapshots']),2)
  for row in observation['current_absence_rows']:
   self.assertEqual(row['state'],'CURRENT_ABSENT_UNOBSERVED_HISTORY')
   self.assertEqual(row['historical_birth'],'UNKNOWN')
   self.assertEqual(len(row['confirmations']),8)
  self.assertTrue(all(r.reads['/proc/%d/stat'%pid]==5 for pid in (77,78,79)))
 def test_directory_presence_refuses_even_with_double_stat_enoent(self):
  r=self.fixture();r.directories_absent.clear()
  with self.assertRaisesRegex(Refusal,'exited-pid-reappeared'):r.run()
 def test_directory_eacces_or_wrong_filename_never_become_absence(self):
  for error in (PermissionError(errno.EACCES,'denied','/proc/77'),FileNotFoundError(errno.ENOENT,'wrong','/proc/78')):
   r=self.fixture();r.directory_errors['/proc/77',1]=error
   with self.subTest(error=error),self.assertRaises(type(error)):r.run()
 def test_late_stat_reappearance_refuses_at_each_completion(self):
  for count in (2,3,4,5):
   r=self.fixture();del r.errors['/proc/77/stat',count]
   with self.subTest(count=count),self.assertRaisesRegex(Refusal,'exited-pid-reappeared'):r.run()
 def test_late_directory_reappearance_refuses_at_each_completion(self):
  for count in (1,2,3,4):
   r=self.fixture();original=r.ns['os'].stat
   def stat(path,follow_symlinks=False):
    if path=='/proc/77' and r.directory_calls.count(path)+1==count:
     r.directory_calls.append(path);return object()
    return original(path,follow_symlinks=follow_symlinks)
   r.ns['os'].stat=stat
   with self.subTest(count=count),self.assertRaisesRegex(Refusal,'exited-pid-reappeared'):r.run()
 def test_reenumeration_never_reclassifies_unknown_pid(self):
  r=self.fixture();r.batches[1]=['1','77','88']
  with self.assertRaisesRegex(Refusal,'exited-pid-reenumerated'):r.run()
 def test_previously_observed_birth_uses_old_pair_retry(self):
  r=Runner();r.batches=[['1','77','88'],['1','77','88'],['1','88'],['1','88']];r.missing('/proc/77/stat',3)
  r.run();self.assertEqual(r.enumerations,4)
  self.assertEqual([row['status'] for row in r.observations()],['REFUSED','PASS_FULL_EOF_RECHECK'])
  self.assertFalse(any(row['current_absence_rows'] for row in r.observations()))
 def test_protected_init_and_observer_absence_never_tombstoned(self):
  for pid in (1,88):
   r=self.fixture();r.exited(pid)
   with self.subTest(pid=pid),self.assertRaises(FileNotFoundError):r.run()
 def test_later_lifecycle_evidence_is_retained_after_initial_success(self):
  r=Runner();r.run();self.assertEqual(r.observations()[0]['status'],'PASS_FULL_EOF_RECHECK')
  r.enumerations=0;r.batches=[['1','78','88'],['1','88']];r.exited(78);r.run()
  self.assertEqual(r.observations()[1]['current_absence_rows'][0]['pid'],78)
  self.assertIn('88',r.observations()[1]['observed_births'])
  self.assertEqual(r.observations()[1]['observed_pids'],[1,77,78,88])
 def test_confirmation_refusal_preserves_newly_observed_stat_bytes(self):
  r=self.fixture();del r.errors['/proc/77/stat',3]
  with self.assertRaisesRegex(Refusal,'exited-pid-reappeared'):r.run()
  row=r.observations()[0]['current_absence_rows'][0]
  self.assertEqual(row['state'],'REFUSED_CONFIRMATION_UNOBSERVED_HISTORY')
  self.assertEqual(bytes.fromhex(row['confirmations'][-1]['stat_hex']),old.old.stat(77))
 def test_confirmed_exit_carries_across_pair_restart_without_erasing_fact(self):
  r=self.fixture();r.batches=[['1','77','79','88'],['1','77','88']];r.missing('/proc/79/cmdline')
  with self.assertRaisesRegex(Refusal,'exited-pid-reenumerated'):r.run()
  self.assertEqual([row['status'] for row in r.observations()],['REFUSED','REFUSED'])
  self.assertEqual(r.observations()[0]['confirmed_exited_pids'],[77])
  self.assertEqual(r.reads['/proc/77/stat'],2)
 def test_confirmed_exit_carries_across_invocations(self):
  r=self.fixture();r.run();self.assertEqual(r.reads['/proc/77/stat'],5)
  r.enumerations=0;r.batches=[['1','77','88']]
  with self.assertRaisesRegex(Refusal,'exited-pid-reenumerated'):r.run()
  self.assertEqual(r.reads['/proc/77/stat'],5)
 def test_prior_pid_only_failure_never_becomes_eligible(self):
  r=Runner();r.ns['DEAD_CALLER_OBSERVATIONS']=[dict(sequence=0,status='REFUSED',raw_full_eof_snapshots=[[dict(pid=77,stat_hex=None,stat_after_hex=None,cmdline_hex=None,executable=None)]])]
  for count in (1,2,3):r.missing('/proc/77/stat',count)
  with self.assertRaisesRegex(Refusal,'retry-exhausted'):r.run()
  self.assertEqual(r.enumerations,3);self.assertEqual(r.directory_calls,[])
  self.assertTrue(all(not row['current_absence_rows'] for row in r.observations()[1:]))
 def test_preinventory_compact_gap_stays_unknown(self):
  r=self.fixture();r.ns['DEAD_CALLER_OBSERVATIONS']=[dict(sequence=12,status='PASS_FULL_EOF_RECHECK',snapshots=[])]
  r.run();observation=r.observations()[-1]
  self.assertEqual(observation['prior_compact_sequences'],[12])
  self.assertEqual(observation['prior_compact_pid_history'],'UNKNOWN')
  self.assertEqual(observation['current_absence_rows'][0]['eligibility'],'NO_PRIOR_RETAINED_OBSERVED_PID_OR_BIRTH')
 def test_prior_complete_raw_birth_seeds_without_fabricating_null_birth(self):
  r=Runner();r.ns['_DEAD_CALLER_RETAINED_HISTORY_SEED']=dict(observed_births={'77':'123'},observed_pids=[77,78],confirmed_exited_pids=[],prior_compact_sequences=[1,2])
  for count in (1,2,3):r.missing('/proc/78/stat',count)
  r.batches=[['1','78','88']]*3
  with self.assertRaisesRegex(Refusal,'retry-exhausted'):r.run()
  self.assertNotIn('78',r.observations()[-1]['observed_births'])
  self.assertIn(78,r.observations()[-1]['observed_pids'])
if __name__=='__main__':unittest.main(verbosity=2)
