"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private unprivileged fixtures. No production-root reads, sudo, signals or keeper.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('capture_outer_fixture',HERE/'capture_outer.py')
o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
entry_spec=importlib.util.spec_from_file_location('capture_entry_fixture',HERE/'capture_entry.py')
e=importlib.util.module_from_spec(entry_spec);entry_spec.loader.exec_module(e);o.e=e

class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
 def directory(self,name):
  path=self.base/name;path.mkdir();return path
 def ref(self,name,value):
  path=self.base/name;raw=e.canonical(value) if not isinstance(value,bytes) else value;path.write_bytes(raw)
  return dict(path=str(path),bytes=len(raw),sha256=e.sha(raw))
 def capture(self,name='capture'):
  capture=e.Capture(self.directory(name));self.addCleanup(capture.close);return capture
 def packet(self):
  return dict(predecessor_custodian={'pid':99},predecessor_tool_session_id=1416,successor_custody_adapter='fixture',custody_successor_composition={'fixture':True},confirmed_exit_delta={'fixture':True},window_id=e.WINDOW_ID,fixed_cutoffs=e.CUTOFFS,resources=e.RESOURCES,pipeline_sources={'entry':dict(path='/fixed/capture_entry.py')},source_hashes={'frozen':'hash'},old_actor={'pid':77},command_inbox={'path':'/fixed/inbox','identity':[1,2,0,0,448]},**{key:value for name in ['evidence_directory','entry_capture_directory','outer_capture_directory'] for key,value in [(name,'/fixed/'+name),(name+'_identity',[1,3,0,0,448])]})
 def authorization(self,packet,raw):
  grant=dict(predecessor_custodian=packet['predecessor_custodian'],predecessor_tool_session_id=packet['predecessor_tool_session_id'],successor_custody_adapter=packet['successor_custody_adapter'],custody_successor_composition=packet['custody_successor_composition'],confirmed_exit_delta=packet['confirmed_exit_delta'],author='/root',operation='GRANT_EXACT_SUCCESSOR_STANDBY_ONLY_NO_RETIREMENT',launch_sha256=e.sha(raw),pipeline_sources=packet['pipeline_sources'],source_hashes=packet['source_hashes'],target=packet['old_actor'],fixed_cutoffs=packet['fixed_cutoffs'],resources=packet['resources'],entry_payload_argv=e.payload_argv('/fixed/packet',e.sha(raw),packet),command_inbox=packet['command_inbox'],capture_directories={name:dict(path=packet[name],identity=packet[name+'_identity']) for name in ['evidence_directory','entry_capture_directory','outer_capture_directory']})
  grant_ref=self.ref('grant.json',grant)
  review=dict(status='PASS_EXECUTION_RELEASE',reviewer='/root/independent',root_grant_sha256=grant_ref['sha256'],launch_sha256=e.sha(raw),pipeline_sources=packet['pipeline_sources'])
  return dict(root_grant=grant_ref,independent_execution_review=self.ref('review.json',review))
 def test_entry_source_is_pinned_before_execution(self):
  packet=dict(pipeline_sources=dict(entry=dict(path=str(HERE/'capture_entry.py'),bytes=0,sha256='0'*64)))
  raw=e.canonical(packet)
  with mock.patch.object(o,'bootstrap_read',return_value=b'raise RuntimeError("must not execute")'):
   with self.assertRaisesRegex(ValueError,'entry-source-pin'):o.bootstrap_entry(raw,e.sha(raw))
  self.assertIs(o.e,e)
 def test_duplicate_and_nonfinite_json_refused(self):
  for raw in [b'{"a":1,"a":2}',b'{"a":NaN}']:
   with self.assertRaises(e.Refusal):e.parse(raw)
 def test_regular_reader_rejects_symlink_and_oversize(self):
  path=self.base/'file';path.write_bytes(b'ab');link=self.base/'link';link.symlink_to(path)
  with self.assertRaises(OSError):e.read_file(link)
  with self.assertRaisesRegex(e.Refusal,'bounded-regular-file'):e.read_file(path,1)
 def test_capture_is_exclusive_and_hash_bound(self):
  c=self.capture();ref=c.write('result.json',b'{}\n');self.assertEqual(e.pinned(ref),b'{}\n')
  with self.assertRaises(FileExistsError):c.write('result.json',b'changed')
  with self.assertRaises(e.Refusal):c.write('../escape',b'x')
 def test_sources_require_all_three_exact_bytes(self):
  refs={}
  for role,name in [('runtime','runtime_pipeline.py'),('entry','capture_entry.py'),('outer','capture_outer.py')]:
   refs[role]=self.ref(name,b'# private fixture\n')
  e.verify_sources(dict(pipeline_sources=refs),here=self.base)
  Path(refs['outer']['path']).write_bytes(b'# changed\n')
  with self.assertRaises(e.Refusal):e.verify_sources(dict(pipeline_sources=refs),here=self.base)
 def test_exact_new_cutoffs_and_all_three_expiries(self):
  self.assertEqual(e.CUTOFFS,[1793100290.0,882395.5689528405,897734.6960034363])
  packet=dict(window_id=e.WINDOW_ID,fixed_cutoffs=e.CUTOFFS);e.clock_check(packet,now=[v-1 for v in e.CUTOFFS])
  for index in range(3):
   now=[v-1 for v in e.CUTOFFS];now[index]=e.CUTOFFS[index]
   with self.assertRaises(e.Refusal):e.clock_check(packet,now=now)
  with self.assertRaises(e.Refusal):e.clock_check(dict(window_id=e.WINDOW_ID,fixed_cutoffs=[1,2,3]),now=[0,0,0])
 def test_nested_evidence_directories_refused(self):
  root=self.directory('root');nested=root/'nested';nested.mkdir();other=self.directory('other');inbox=self.directory('inbox')
  packet=dict(evidence_directory=str(root),entry_capture_directory=str(nested),outer_capture_directory=str(other),command_inbox=dict(path=str(inbox)))
  with self.assertRaisesRegex(e.Refusal,'disjoint-pipeline-directories'):e.verify_directories(packet,nested)
 def test_late_authorization_has_no_hash_cycle(self):
  packet=self.packet();raw=e.canonical(packet);auth=self.authorization(packet,raw)
  result=e.verify_authorization(packet,raw,'/fixed/packet',auth)
  envelope=self.ref('authorization.json',auth)
  command=o.launch_argv('/fixed/packet',e.sha(raw),packet,envelope['path'],envelope['sha256'])
  self.assertEqual(command[:7],['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648'])
  self.assertEqual(command[-4:],['--authorization',envelope['path'],'--authorization-sha256',envelope['sha256']])
  self.assertNotIn('--authorization',result['grant']['entry_payload_argv'])
 def test_changed_target_refuses_authorization(self):
  packet=self.packet();raw=e.canonical(packet);auth=self.authorization(packet,raw);packet['old_actor']={'pid':78}
  with self.assertRaisesRegex(e.Refusal,'launch-grant-binding:target'):e.verify_authorization(packet,raw,'/fixed/packet',auth)
 def test_launch_review_must_be_independent(self):
  packet=self.packet();raw=e.canonical(packet);auth=self.authorization(packet,raw)
  review=e.parse(e.pinned(auth['independent_execution_review']));review['reviewer']='/root';auth['independent_execution_review']=self.ref('bad-review.json',review)
  with self.assertRaisesRegex(e.Refusal,'exact-independent-launch-release'):e.verify_authorization(packet,raw,'/fixed/packet',auth)
 def test_inbox_consumes_malformed_command_once(self):
  inbox=self.directory('inbox');c=self.capture();packet=dict(command_inbox=dict(path=str(inbox),identity=e.identity(inbox)),fixed_cutoffs=e.CUTOFFS)
  box=e.Inbox(packet,c,writer_uid=os.getuid());(inbox/'command-000000.json').write_bytes(b'{bad}\n')
  with mock.patch.object(e,'clock_check'):
   with self.assertRaises(ValueError):box.next_command()
   self.assertIsNone(box.next_command())
  self.assertEqual(box.sequence,1);self.assertTrue((c.path/'COMMAND-000000.CONSUMED.json').is_file())
 def test_inbox_preserves_valid_command_bytes(self):
  inbox=self.directory('inbox');c=self.capture();packet=dict(command_inbox=dict(path=str(inbox),identity=e.identity(inbox)))
  box=e.Inbox(packet,c,writer_uid=os.getuid());raw=e.canonical(dict(operation='FINISH_REMAINING_SHARED_ONLY'))
  (inbox/'command-000000.json').write_bytes(raw)
  with mock.patch.object(e,'clock_check'):self.assertEqual(box.next_command()['operation'],'FINISH_REMAINING_SHARED_ONLY')
  self.assertEqual((c.path/'COMMAND-000000.raw.json').read_bytes(),raw)
 def test_true_child_birth_join_streams_exit_and_rusage(self):
  c=self.capture();result=o.capture_child([sys.executable,'-I','-B','-c','import sys; print("out"); print("err",file=sys.stderr); sys.exit(7)'],c)
  birth=e.parse((c.path/'DIRECT-CHILD-BIRTH.json').read_bytes())
  self.assertEqual(birth['process']['ppid'],os.getpid());self.assertEqual(birth['process']['starttime'],result['starttime'])
  self.assertTrue(result['direct_join']);self.assertEqual(result['exit_code'],7);self.assertIn('ru_maxrss',result['rusage'])
  self.assertFalse(result['historical_actor_join_inferred']);self.assertFalse(result['automatic_signal'])
  self.assertEqual((c.path/'STDOUT.raw').read_bytes(),b'out\n');self.assertEqual((c.path/'STDERR.raw').read_bytes(),b'err\n')
  with self.assertRaises(ChildProcessError):os.waitpid(result['pid'],os.WNOHANG)
 def test_overflow_drains_without_kill_and_records_failure(self):
  c=self.capture();result=o.capture_child([sys.executable,'-I','-B','-c','import sys; sys.stdout.write("x"*100000); sys.stderr.write("y"*100000)'],c,maximum=16)
  self.assertEqual(result['exit_code'],0)
  for name,row in result['streams'].items():
   self.assertEqual(row['bytes_observed'],100000);self.assertEqual(row['bytes_stored'],16);self.assertTrue(row['overflow'])
   self.assertEqual((c.path/(name+'.raw')).stat().st_size,16)
 def test_stream_write_fault_drains_and_records_failed_capture(self):
  c=self.capture();write=os.write
  def fail_stdout(fd,data):
   if os.readlink('/proc/self/fd/'+str(fd)).endswith('/STDOUT.raw'):raise OSError('private output fixture failure')
   return write(fd,data)
  with mock.patch.object(o.os,'write',side_effect=fail_stdout):
   result=o.capture_child([sys.executable,'-I','-B','-c','import sys; sys.stdout.write("x"*100000)'],c)
  self.assertEqual(result['exit_code'],0);self.assertTrue(result['direct_join'])
  self.assertEqual(result['streams']['STDOUT']['bytes_observed'],100000)
  self.assertIn('private output fixture failure',result['streams']['STDOUT']['write_error'])
 def test_current_adoption_operation_only(self):
  self.assertIn('ADOPT_AFTER_POSITIVE_PREDECESSOR_JOINS',e.OPERATIONS)
  self.assertNotIn('ADOPT_AFTER_POSITIVE_ORIGINAL_JOINS',e.OPERATIONS)
 def test_child_exec_failure_still_has_direct_join(self):
  c=self.capture();result=o.capture_child(['/nonexistent/private-fixture'],c)
  self.assertEqual(result['exit_code'],126);self.assertTrue(result['direct_join'])
 def test_birth_failure_prevents_exec_without_signal(self):
  c=self.capture();marker=self.base/'must-not-exist'
  with mock.patch.object(o,'child_identity',side_effect=OSError('private birth observer failure')):
   with self.assertRaisesRegex(OSError,'birth observer'):o.capture_child([sys.executable,'-I','-B','-c','from pathlib import Path; Path('+repr(str(marker))+').touch()'],c)
  self.assertFalse(marker.exists())
  fault=e.parse((c.path/'OUTER-UNRESOLVED-CAPTURE.json').read_bytes());self.assertFalse(fault['exec_released'])
  joined=e.parse((c.path/'OUTER-FAULT-DIRECT-CHILD-JOIN.json').read_bytes());self.assertEqual(joined['exit_code'],125);self.assertTrue(joined['direct_join'])

if __name__=='__main__':unittest.main()
