"""Functional mocked exact rootguard tests only; no security testing/rootentry."""
import copy,importlib.util,json,subprocess,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('exact_guard_test',ROOT/'exact_root_guard_runner.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
PROFILE=json.loads(a.PROFILE.read_text())
class Checks(unittest.TestCase):
 def answer(self):return dict(status='PASS_EXACT_RECOVER_ERROR_READ',co_filename=PROFILE['source']['path'],co_name='recover',local='error',exception_type='Refusal',error_argument='fixture-not-actual-runtime-reason')
 def test_pinned_binaries_helper_sources_and_profile(self):
  import hashlib
  self.assertEqual(hashlib.sha256(a.PROFILE.read_bytes()).hexdigest(),a.PROFILE_SHA)
  for key in ['gdb','python','helper','source','release']:a.authenticate(PROFILE[key])
 def test_success_requires_pre_and_post_equal(self):
  guards=mock.Mock(side_effect=[{'fixture':'same'},{'fixture':'same'}]);run=mock.Mock(return_value=SimpleNamespace(stdout=(json.dumps(self.answer())+'\n').encode(),stderr=b'',returncode=0))
  result=a.perform(PROFILE,guards,run);self.assertEqual(result['status'],'PASS_EXACT_OWNED_QUARANTINE_ERROR_READ');self.assertEqual(guards.call_count,2)
  self.assertEqual(run.call_args.kwargs['timeout'],10);self.assertEqual(run.call_args.kwargs['env']['DEBUGINFOD_URLS'],'')
 def test_timeout_postguard_and_lossless_output(self):
  guards=mock.Mock(side_effect=[{'fixture':'same'},{'fixture':'same'}]);run=mock.Mock(side_effect=subprocess.TimeoutExpired(['ownedgdb'],10,output=b'partial\xff',stderr=b'error'))
  result=a.perform(PROFILE,guards,run);self.assertEqual(result['status'],'REFUSED');self.assertEqual(guards.call_count,2);self.assertEqual(bytes.fromhex(result['stdout']['raw_hex']),b'partial\xff')
 def test_child_error_postguard_always_runs(self):
  guards=mock.Mock(side_effect=[{'fixture':'same'},{'fixture':'same'}]);result=a.perform(PROFILE,guards,mock.Mock(side_effect=OSError('fixture')))
  self.assertEqual(result['status'],'REFUSED');self.assertEqual(guards.call_count,2)
 def test_zero_exit_missing_or_duplicate_pass_refused(self):
  for stdout in [b'',(json.dumps(self.answer())+'\n') .encode()*2]:
   result=a.perform(PROFILE,lambda _: {'fixture':'same'},lambda *args,**kw:SimpleNamespace(stdout=stdout,stderr=b'error',returncode=0));self.assertEqual(result['status'],'REFUSED')
 def test_changed_custody_or_postguard_refuses_without_target_action(self):
  run=lambda *args,**kw:SimpleNamespace(stdout=(json.dumps(self.answer())+'\n').encode(),stderr=b'',returncode=0)
  for after in [{'fixture':'changed'},a.Refusal('fixture stopped')]:
   guard=mock.Mock(side_effect=[{'fixture':'same'},after]);result=a.perform(PROFILE,guard,run);self.assertEqual(result['status'],'REFUSED')
 def test_pre_guard_failure_prevents_debugger(self):
  run=mock.Mock()
  with self.assertRaises(a.Refusal):a.perform(PROFILE,mock.Mock(side_effect=a.Refusal('wrongbirth')),run)
  run.assert_not_called()
 def test_fixed_arguments_no_writes_calls_breakpoints_and_no_optional_pid(self):
  argv=a.readonly_gdb_argv(PROFILE);text='\n'.join(argv)
  self.assertIn('attach 1060806',argv);self.assertIn('Refusal',text);self.assertIn('set may-call-functions off',argv);self.assertIn('set may-write-memory off',argv);self.assertIn('set may-write-registers off',argv);self.assertIn('set may-insert-breakpoints off',argv);self.assertNotIn('set debuginfod enabled off',argv)
 def test_exact_process_birth_parent_argv_executable_and_stopped_state(self):
  snapshot=ROOT.parent.parent/'current290-post-recovery-retirement-review-1/quarantine-readonly-snapshot-1/SNAPSHOT.json'
  data=json.loads(snapshot.read_text());actual=next(row for row in data['processes'] if row['pid']==1060806)
  expected=PROFILE['actor']
  def check(raw,command=None,exe=None):
   def read(path,*args):
    name=Path(path).name
    if name=='stat':return raw
    if name=='cmdline':return bytes.fromhex(actual['cmdline_hex']) if command is None else command
    if name=='status':return b'Uid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n'
    raise AssertionError(name)
   with mock.patch.object(a,'bounded',side_effect=read),mock.patch.object(a.os,'readlink',return_value=expected['exe'] if exe is None else exe):return a.process_identity(expected)
  self.assertEqual(check(actual['stat'].encode())['pid'],1060806)
  for raw,command,exe in [(actual['stat'].replace('80309560','99999999').encode(),None,None),(actual['stat'].replace(') S ',') T ').encode(),None,None),(actual['stat'].replace('1060803 1060803','1 1060803',1).encode(),None,None),(actual['stat'].encode(),b'wrong\0',None),(actual['stat'].encode(),None,'/different/python')]:
   with self.assertRaises(a.Refusal):check(raw,command,exe)
 def test_sudo_parent_original_group1000_preserved(self):
  snapshot=ROOT.parent.parent/'current290-post-recovery-retirement-review-1/quarantine-readonly-snapshot-1/SNAPSHOT.json';data=json.loads(snapshot.read_text());actual=next(row for row in data['processes'] if row['pid']==1060803)
  def read(path,*args):
   return {'stat':actual['stat'].encode(),'cmdline':bytes.fromhex(actual['cmdline_hex']),'status':b'Uid:\t1000\t0\t0\t0\nGid:\t1000\t1000\t1000\t1000\n'}[Path(path).name]
  with mock.patch.object(a,'bounded',side_effect=read),mock.patch.object(a.os,'readlink',return_value='/usr/bin/sudo'):
   value=a.process_identity(PROFILE['parent']);self.assertEqual(value['credentials']['Gid:'],['1000']*4)
 def test_actual_root_entry_rejects_ordinary_uid(self):
  import sys
  with mock.patch.object(a.os,'getuid',return_value=1000),mock.patch.object(a.os,'geteuid',return_value=1000),mock.patch.object(sys,'argv',['guard','--execute-exact-root-read']):
   with self.assertRaisesRegex(a.Refusal,'exact-root-entry-required'):a.main()
if __name__=='__main__':unittest.main(verbosity=2)
