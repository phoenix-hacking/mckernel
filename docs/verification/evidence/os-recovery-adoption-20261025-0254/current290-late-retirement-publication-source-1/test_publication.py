"""Functional OS only; no security testing. Private UID1000 metadata fixtures only.
Root inbox ownership is simulated for validation; no production paths or processes.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import prepare_retirement_grant as p
import publish_reviewed_retirement as pub
pub.p=p # Fixture identity injection never runs through either production CLI.


class PublicationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.prep=self.root/'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2';self.prep.mkdir()
  for name in ('RUNTIME','ENTRY','OUTER','INBOX'):(self.prep/name).mkdir(mode=0o700)
  self.packet=dict(author='/root',scope=p.SCOPE,window_id=p.WINDOW,fixed_cutoffs=p.CUTOFFS,standby_seconds=120,mode='STANDBY_ONLY_UNTIL_SEPARATE_RETIREMENT_AUTH',pipeline_sources=p.PIPELINE,source_hashes=p.SOURCE_HASHES,predecessor_custodian=p.PREDECESSOR,old_actor=p.ORIGIN,successor_custody_adapter=p.ADAPTER,custody_successor_composition=dict(target=p.PREDECESSOR,lock_origin_pid=1060806,predecessor_launch_sha256=p.PREDECESSOR_LAUNCH_SHA,custody_adapter=p.ADAPTER))
  for key,name in [('evidence_directory','RUNTIME'),('entry_capture_directory','ENTRY'),('outer_capture_directory','OUTER')]:
   self.packet[key]=str(self.prep/name);self.packet[key+'_identity']=p.real_directory(self.prep/name)
  inbox_identity=p.real_directory(self.prep/'INBOX');inbox_identity[2:]=[0,0,0o700]
  self.packet['command_inbox']=dict(path=str(self.prep/'INBOX'),identity=inbox_identity)
  launch_raw=p.canonical(self.packet);(self.prep/'LAUNCH-PACKET.json').write_bytes(launch_raw)
  self.keeper=dict(pid=1234567,pgid=1234560,starttime='90000000')
  argv=['/home/holden/anaconda3/bin/python3.9','-I','-B',p.PIPELINE['entry']['path'],'--packet',str(self.prep/'LAUNCH-PACKET.json'),'--packet-sha256',p.sha(launch_raw),'--capture-directory',str(self.prep/'ENTRY'),'--authorization',str(self.prep/'LAUNCH-AUTHORIZATION.json'),'--authorization-sha256','a'*64]
  process=dict(scope=p.SCOPE,keeper=self.keeper,launch_sha256=p.sha(launch_raw),old_actor=p.ORIGIN,source_hashes=p.SOURCE_HASHES,command_hex=('\0'.join(argv)+'\0').encode().hex())
  held=dict(scope=p.SCOPE,custody_adapter=p.ADAPTER,predecessor_custodian=p.PREDECESSOR,predecessor_launch_sha256=p.PREDECESSOR_LAUNCH_SHA,old_actor=p.ORIGIN,positive_pidfd_target_alive=True,actor_birth_rechecked=True,actual_retirement=False,quarantine_untouched=True,custody=dict(holder_pid=1193473,holder_fd=6,retained_fd=6,device=27,inode=4,lock_origin_pid=1060806,same_description_observed=True))
  (self.prep/'RUNTIME/PROCESS.json').write_bytes(p.canonical(process));(self.prep/'RUNTIME/HELD-CUSTODY.json').write_bytes(p.canonical(held))
  original=p.build_grant;real_directory=p.real_directory
  def fixture_build(prep,*,evidence_root):
   def fixture_identity(path):
    result=real_directory(path)
    if Path(path)==self.prep/'INBOX':result[2:]=[0,0,0o700]
    return result
   with mock.patch.object(p,'real_directory',side_effect=fixture_identity):return original(prep,evidence_root=evidence_root)
  self.patch=mock.patch.object(p,'build_grant',side_effect=fixture_build);self.patch.start();self.addCleanup(self.patch.stop)
 def prepare(self):return p.prepare(self.prep,evidence_root=self.root)
 def publish(self,digest):return pub.publish(self.prep,digest,evidence_root=self.root)
 def snapshot(self):return {str(path.relative_to(self.prep)):path.read_bytes() for path in self.prep.rglob('*') if path.is_file()}
 def test_exact_prepare_then_explicit_publication_preserves_inputs(self):
  before=self.snapshot();prepared=self.prepare();self.assertEqual(prepared['keeper'],self.keeper)
  grant,_=p.read_regular(self.prep/p.GRANT_NAME)
  self.assertEqual(grant['target'],p.PREDECESSOR);self.assertNotEqual(grant['target'],p.ORIGIN)
  result=self.publish(prepared['root_grant']['sha256'])
  command,_=p.read_regular(self.prep/'INBOX/command-000000.json');review,_=p.read_regular(self.prep/p.REVIEW_NAME)
  self.assertEqual(command['operation'],p.OPERATION);self.assertEqual(command['root_grant'],prepared['root_grant'])
  self.assertEqual(review['root_grant_sha256'],prepared['root_grant']['sha256']);self.assertEqual(review['reviewer'],'/root/custody_release_review')
  self.assertEqual(review['status'],'PASS_EXECUTION_RELEASE');self.assertFalse(review['root_explicit_review_attestation']['automated_review'])
  self.assertEqual(result['keeper'],self.keeper)
  after=self.snapshot()
  for name,raw in before.items():self.assertEqual(after[name],raw)
  self.assertEqual(set(after)-set(before),{p.GRANT_NAME,p.REVIEW_NAME,'INBOX/command-000000.json'})
 def test_wrong_approved_hash_has_no_publication_effects(self):
  self.prepare();before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'approved-grant-sha'):self.publish('0'*64)
  self.assertEqual(self.snapshot(),before)
 def test_prepare_and_publisher_never_overwrite(self):
  prepared=self.prepare()
  with self.assertRaises(FileExistsError):self.prepare()
  self.publish(prepared['root_grant']['sha256']);before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'fresh-review-and-command'):self.publish(prepared['root_grant']['sha256'])
  self.assertEqual(self.snapshot(),before)
 def test_existing_command_prevents_even_review_creation(self):
  prepared=self.prepare();(self.prep/'INBOX/command-000000.json').write_bytes(b'untouched')
  before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'fresh-review-and-command'):self.publish(prepared['root_grant']['sha256'])
  self.assertEqual(self.snapshot(),before);self.assertFalse((self.prep/p.REVIEW_NAME).exists())
 def test_changed_grant_is_rejected_even_with_its_new_hash(self):
  self.prepare();path=self.prep/p.GRANT_NAME;grant=json.loads(path.read_bytes());grant['target']=p.ORIGIN;raw=p.canonical(grant);path.write_bytes(raw);before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'unchanged-exact-new-keeper-grant'):self.publish(p.sha(raw))
  self.assertEqual(self.snapshot(),before)
 def test_old_process_has_no_effect(self):
  path=self.prep/'RUNTIME/PROCESS.json';process=json.loads(path.read_bytes());process['keeper']['pid']=1203549;path.write_bytes(p.canonical(process));before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'new-actual-keeper'):self.prepare()
  self.assertEqual(self.snapshot(),before)
 def test_changed_source_binding_has_no_effect(self):
  path=self.prep/'LAUNCH-PACKET.json';packet=json.loads(path.read_bytes());packet['pipeline_sources']['runtime']['sha256']='0'*64;path.write_bytes(p.canonical(packet));before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'exact-selected-source-bindings'):self.prepare()
  self.assertEqual(self.snapshot(),before)
 def test_symlink_preparation_parent_refused(self):
  alias=self.root/'alias';alias.symlink_to(self.prep,target_is_directory=True);before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'real-parent-path'):p.prepare(alias,evidence_root=self.root)
  self.assertEqual(self.snapshot(),before)
 def test_isolated_interpreter_loads_pinned_helper_then_refuses_uid(self):
  before=self.snapshot()
  result=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).parent/'publish_reviewed_retirement.py'),str(self.prep),'0'*64],capture_output=True,check=False)
  self.assertEqual(result.returncode,1);self.assertIn(b'uid0-reviewed-publication-only',result.stderr)
  self.assertNotIn(b'ModuleNotFoundError',result.stderr);self.assertEqual(self.snapshot(),before)
 def test_uid_main_guards_have_no_effect(self):
  before=self.snapshot()
  with mock.patch.object(p.os,'getuid',return_value=1000),mock.patch.object(p.os,'geteuid',return_value=1000):
   with self.assertRaisesRegex(ValueError,'uid0'):pub.main([str(self.prep),'0'*64])
  with mock.patch.object(p.os,'getuid',return_value=0),mock.patch.object(p.os,'geteuid',return_value=0):
   with self.assertRaisesRegex(ValueError,'uid1000'):p.main([str(self.prep)])
  self.assertEqual(self.snapshot(),before)

if __name__=='__main__':unittest.main()
