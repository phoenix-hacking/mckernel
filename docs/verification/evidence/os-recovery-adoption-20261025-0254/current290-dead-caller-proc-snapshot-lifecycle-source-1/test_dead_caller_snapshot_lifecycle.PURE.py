#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Extract only exact frozen e49 functions; all proc reads, identities and UID mocked.
"""
import ast,copy,errno,hashlib,json,os,time,types,unittest
from pathlib import Path
from unittest import mock
D=Path(__file__).resolve().parent
BASE=D.parent/'current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py'
BASE_SHA='e49eaf2a7bacc6a64523f9f6c91516b9a3abefc875cdc1d8941c4e6b55473de3'
class Refusal(RuntimeError):pass

def stat(pid,ppid=1,pgrp=None,birth='123',state=b'S'):
 fields=[b'0']*50;fields[0]=state;fields[1]=str(ppid).encode();fields[2]=str(pid if pgrp is None else pgrp).encode();fields[6]=b'0';fields[19]=birth.encode()
 return str(pid).encode()+b' (fixture) '+b' '.join(fields)+b'\n'
class ProcPath:
 entries=['1','77','88']
 def __init__(self,path):self.path=str(path)
 @property
 def name(self):return self.path.rsplit('/',1)[-1]
 def __truediv__(self,part):return ProcPath(self.path+'/'+part)
 def __str__(self):return self.path
 def iterdir(self):return [ProcPath('/proc/'+pid) for pid in self.entries]
 def read_text(self):return 'fixture-boot\n'

def load(corrected=False):
 raw=BASE.read_bytes();assert hashlib.sha256(raw).hexdigest()==BASE_SHA
 tree=ast.parse(raw);names={'validate_dead_caller_snapshots','validate_dead_operation_argv','record_dead_caller_observation','dead_caller_absent'}
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if corrected:
  patch=ast.parse((D/'dead_caller_snapshot_lifecycle.FOCUSED-FUNCTIONS.SOURCE-ONLY.py').read_bytes())
  replacements={n.name:n for n in patch.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  nodes=[n for n in nodes if n.name not in replacements]+list(replacements.values())
 ns=dict(Path=ProcPath,os=types.SimpleNamespace(getuid=lambda:0,geteuid=lambda:0,getpid=lambda:88,readlink=lambda path:'/usr/bin/python3',path=os.path),time=time,Refusal=Refusal,json=json,errno=errno,
         DEAD_CALLER_BINDING=dict(boot_id='fixture-boot',caller_pid=900,owner_pid=901,group_ids=[900,901],recorded_children=[],operation_argv_paths=['/namespace/old']),WAITER_PIDS=[902],DEAD_CALLER_OBSERVATIONS=[],DEAD_CALLER_CAPTURE_BYTES=0,
         digest=lambda raw:hashlib.sha256(raw).hexdigest(),canonical=lambda value:(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode(),same_ofd_process=lambda pid:dict(pid=88,starttime='555',uids=[0]*4,gids=[0]*4))
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(BASE),'exec'),ns)
 return ns
class Baseline(unittest.TestCase):
 def test_actual_e49_ordinary_process_exit_is_uncaught(self):
  ns=load();reads={}
  def read(path,limit):
   reads[path]=reads.get(path,0)+1
   if path=='/proc/77/stat' and reads[path]==2:raise FileNotFoundError(errno.ENOENT,'ordinary exited',path)
   if path.endswith('/stat'):return stat(int(path.split('/')[2]))
   return b'/usr/bin/python3\0'
  ns['same_ofd_read']=read
  with self.assertRaises(FileNotFoundError):ns['dead_caller_absent']()
  self.assertEqual(len(ns['DEAD_CALLER_OBSERVATIONS']),1)
  self.assertIn('FileNotFoundError',ns['DEAD_CALLER_OBSERVATIONS'][0]['error'])
class Corrected(unittest.TestCase):
 def setUp(self):
  self.ns=load(True);self.reads={};self.failures=0;self.stat_overrides={};self.commands={};self.exes={};self.mode=None
  def read(path,limit):
   self.reads[path]=self.reads.get(path,0)+1
   pid=int(path.split('/')[2])
   if path.endswith('/cmdline'):
    if self.mode=='command_missing' and pid==77:raise FileNotFoundError(errno.ENOENT,'exited',path)
    return self.commands.get(pid,b'/usr/bin/python3\0')
   if path.endswith('/stat'):
    count=self.reads[path]
    if pid==77:
     fail=self.mode=='persistent' and count%2==0 or self.mode=='first_missing' and count==1 or self.mode in ('once','observer_lost','permission','wrong_filename') and count==2
     if fail:
      self.failures+=1
      if self.mode=='permission':raise PermissionError(errno.EACCES,'denied',path)
      raise FileNotFoundError(errno.ENOENT,'exited','/wrong/stat' if self.mode=='wrong_filename' else path)
    if self.mode=='reuse' and pid==77 and count>2:return stat(pid,birth='999')
    return self.stat_overrides.get(pid,stat(pid,birth='555' if pid==88 else '123'))
   raise AssertionError(path)
  self.ns['same_ofd_read']=read
  self.ns['os'].readlink=lambda path:self.exes.get(int(str(path).split('/')[2]),'/usr/bin/python3')
 def test_once_ordinary_exit_discards_partial_and_gets_new_complete_pair(self):
  self.mode='once';self.ns['dead_caller_absent']()
  observations=self.ns['DEAD_CALLER_OBSERVATIONS'];self.assertEqual(len(observations),2)
  self.assertEqual(observations[0]['status'],'REFUSED');self.assertIn('DeadCallerOrdinaryExit',observations[0]['error'])
  self.assertEqual(observations[1]['status'],'PASS_FULL_EOF_RECHECK')
  self.assertEqual(len(observations[1]['raw_full_eof_snapshots']),2)
  self.assertTrue(all(len(rows)==3 for rows in observations[1]['raw_full_eof_snapshots']))
  self.assertEqual(self.reads['/proc/77/stat'],6)
 def test_persistent_churn_stops_at_three_fresh_pairs(self):
  self.mode='persistent'
  with self.assertRaisesRegex(Refusal,'retry-exhausted'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,3);self.assertEqual(len(self.ns['DEAD_CALLER_OBSERVATIONS']),3)
 def test_first_stat_missing_is_unknown_hard(self):
  self.mode='first_missing'
  with self.assertRaises(FileNotFoundError):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,1)
 def test_cmdline_missing_is_unknown_hard(self):
  self.mode='command_missing'
  with self.assertRaises(FileNotFoundError):self.ns['dead_caller_absent']()
 def test_permission_never_retries(self):
  self.mode='permission'
  with self.assertRaises(PermissionError):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,1)
 def test_nonexact_filename_never_retries(self):
  self.mode='wrong_filename'
  with self.assertRaises(FileNotFoundError):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,1)
 def test_unknown_parent_chain_never_retries(self):
  self.mode='once';self.stat_overrides[77]=stat(77,ppid=44)
  with self.assertRaises(FileNotFoundError):self.ns['dead_caller_absent']()
 def test_known_publisher_cannot_vanish_behind_retry(self):
  self.mode='once';self.exes[77]='/usr/bin/make'
  with self.assertRaisesRegex(Refusal,'known-publisher'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,0);self.assertEqual(self.reads['/proc/77/stat'],1)
 def test_namespace_argv_cannot_vanish_behind_retry(self):
  self.mode='once';self.commands[77]=b'python3\0/namespace/old/runner.py\0'
  with self.assertRaisesRegex(Refusal,'operation-process'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,0)
 def test_original_group_cannot_vanish_behind_retry(self):
  self.mode='once';self.stat_overrides[77]=stat(77,pgrp=900)
  with self.assertRaisesRegex(Refusal,'group-present'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,0)
 def test_original_caller_pid_presence_refused_before_followup(self):
  self.ns['DEAD_CALLER_BINDING']['caller_pid']=77;self.mode='once'
  with self.assertRaisesRegex(Refusal,'descendant-present'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,0)
 def test_observed_descendant_presence_is_hard(self):
  self.stat_overrides[77]=stat(77,ppid=900);self.mode='once'
  with self.assertRaisesRegex(Refusal,'descendant-present'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,0)
 def test_birth_reuse_across_complete_snapshots_is_hard(self):
  self.mode='reuse'
  with self.assertRaisesRegex(Refusal,'pid-reused'):self.ns['dead_caller_absent']()
 def test_root_observer_continuity_cannot_retry(self):
  self.mode='observer_lost';count=[0]
  def observer(pid):
   count[0]+=1
   return dict(pid=88,starttime='changed' if count[0]>2 else '555',uids=[0]*4,gids=[0]*4)
  self.ns['same_ofd_process']=observer
  with self.assertRaisesRegex(Refusal,'observer-raced'):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,1)
 def test_observer_read_loss_records_partial_and_refuses(self):
  self.mode='observer_lost';count=[0]
  def observer(pid):
   count[0]+=1
   if count[0]>2:raise FileNotFoundError(errno.ENOENT,'observer missing','/proc/88/stat')
   return dict(pid=88,starttime='555',uids=[0]*4,gids=[0]*4)
  self.ns['same_ofd_process']=observer
  with self.assertRaises(FileNotFoundError):self.ns['dead_caller_absent']()
  self.assertEqual(self.failures,1)
  self.assertEqual(len(self.ns['DEAD_CALLER_OBSERVATIONS']),1)
  self.assertIn(':observer:FileNotFoundError',self.ns['DEAD_CALLER_OBSERVATIONS'][0]['error'])
 def test_capture_bound_unchanged(self):
  self.ns['DEAD_CALLER_CAPTURE_BYTES']=16<<20
  with self.assertRaisesRegex(Refusal,'capture-total-bound'):self.ns['dead_caller_absent']()
 def test_malformed_stat_hard(self):
  self.stat_overrides[77]=b'bad'
  with self.assertRaisesRegex(Refusal,'process-stat'):self.ns['dead_caller_absent']()
 def test_live_empty_command_hard(self):
  self.commands[77]=b''
  with self.assertRaisesRegex(Refusal,'live-command-unknown'):self.ns['dead_caller_absent']()
 def test_original_snapshot_and_argv_validators_identical(self):
  old=load();new=load(True)
  for name in ('validate_dead_caller_snapshots','validate_dead_operation_argv'):
   self.assertEqual(old[name].__code__.co_code,new[name].__code__.co_code)
if __name__=='__main__':unittest.main(verbosity=2)
