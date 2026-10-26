#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual e49/45fd function ASTs and additive successor; fake proc only.
"""
import ast,errno,hashlib,importlib.util,json,types,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('old_fixture',D.parent/'test_dead_caller_snapshot_lifecycle.PURE.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
Refusal=old.Refusal
class Runner:
 def __init__(self,corrected=True):
  self.ns=old.load(not corrected);self.enumerations=0;self.reads={};self.rows={};self.commands={};self.exes={};self.errors={};self.batches=None;self.calls=[]
  if corrected:
   tree=ast.parse((D/'dead_caller_whole_pair_enoent.FOCUSED-FUNCTIONS.SOURCE-ONLY.py').read_bytes());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))],type_ignores=[]),str(D/'dead_caller_whole_pair_enoent.FOCUSED-FUNCTIONS.SOURCE-ONLY.py'),'exec'),self.ns)
  runner=self
  class P(old.ProcPath):
   def __truediv__(self,part):return P(self.path+'/'+part)
   def iterdir(self):
    runner.enumerations+=1;batch=runner.batches[runner.enumerations-1] if runner.batches else ['1','77','88']
    return [P('/proc/'+name) for name in batch]
  self.ns['Path']=P
  def read(path,limit):
   self.calls.append(path);self.reads[path]=self.reads.get(path,0)+1;key=(path,self.reads[path]);pid=int(path.split('/')[2])
   if key in self.errors:raise self.errors[key]
   if path.endswith('/stat'):
    value=self.rows.get((pid,self.reads[path]),self.rows.get(pid,old.stat(pid,birth='555' if pid==88 else '123')))
    return value
   return self.commands.get(pid,b'/usr/bin/python3\0')
  self.ns['same_ofd_read']=read
  def readlink(path):
   path=str(path);self.calls.append(path);self.reads[path]=self.reads.get(path,0)+1;key=(path,self.reads[path])
   if key in self.errors:raise self.errors[key]
   return self.exes.get(int(path.split('/')[2]),'/usr/bin/python3')
  self.ns['os'].readlink=readlink
 def missing(self,path,count=1,kind=FileNotFoundError):self.errors[(path,count)]=kind(errno.ENOENT,'fixture exited',path)
 def run(self):return self.ns['dead_caller_absent']()
 def observations(self):return self.ns['DEAD_CALLER_OBSERVATIONS']
class WholePair(unittest.TestCase):
 def malformed_case(self,raw):
  for corrected in (False,True):
   r=Runner(corrected);r.rows[77]=raw;r.missing('/proc/77/stat',2);r.batches=[['1','77','88'],['1','88'],['1','88']]
   if corrected:
    with self.assertRaisesRegex(Refusal,'process-stat'):r.run()
    self.assertEqual(r.enumerations,1)
   else:r.run();self.assertEqual([o['status'] for o in r.observations()],['REFUSED','PASS_FULL_EOF_RECHECK'])
 def test_original_accepts_nonnumeric_birth_successor_refuses(self):self.malformed_case(old.stat(77,birth='not-a-number'))
 def test_original_accepts_negative_group_successor_refuses(self):self.malformed_case(old.stat(77,pgrp=-1))
 def test_all_available_stat_fields_validate_before_retry(self):
  raw=old.stat(77).split();raw[42]=b'not-number';r=Runner();r.rows[77]=b' '.join(raw);r.missing('/proc/77/stat',2)
  with self.assertRaisesRegex(Refusal,'stat-number'):r.run()
 def once(self,kind,count=1,second_pair=False):
  r=Runner();r.missing('/proc/77/'+kind,count);r.batches=([['1','77','88'],['1','77','88'],['1','88'],['1','88']] if second_pair else [['1','77','88'],['1','88'],['1','88']]);r.run()
  self.assertEqual(r.enumerations,4 if second_pair else 3)
  self.assertEqual([o['status'] for o in r.observations()],['REFUSED','PASS_FULL_EOF_RECHECK'])
  final=r.observations()[1]['raw_full_eof_snapshots'];self.assertEqual(len(final),2);self.assertEqual([[row['pid'] for row in snapshot] for snapshot in final],[[1,88],[1,88]])
  return r
 def test_first_stat_enoent_restarts_entire_pair(self):self.once('stat')
 def test_cmdline_enoent_restarts_entire_pair(self):self.once('cmdline')
 def test_executable_enoent_restarts_entire_pair(self):self.once('exe')
 def test_second_snapshot_loss_discards_completed_first_snapshot(self):self.once('stat',3,True)
 def test_second_stat_enoent_restarts_entire_pair(self):self.once('stat',2)
 def test_forbidden_numeric_pid_refuses_before_first_read(self):
  r=Runner();r.ns['DEAD_CALLER_BINDING']['caller_pid']=77;r.missing('/proc/77/stat')
  with self.assertRaisesRegex(Refusal,'descendant-present'):r.run()
  self.assertNotIn('/proc/77/stat',r.calls)
 def test_known_publisher_argv_refuses_before_exe_loss(self):
  r=Runner();r.commands[77]=b'make\0';r.missing('/proc/77/exe')
  with self.assertRaisesRegex(Refusal,'known-publisher'):r.run()
  self.assertNotIn('/proc/77/exe',r.calls)
 def test_known_publisher_executable_refuses_before_second_stat_loss(self):
  r=Runner();r.exes[77]='/usr/bin/make';r.missing('/proc/77/stat',2)
  with self.assertRaisesRegex(Refusal,'known-publisher'):r.run()
  self.assertEqual(r.reads['/proc/77/stat'],1)
 def test_namespace_argv_refuses_before_exe_loss(self):
  r=Runner();r.commands[77]=b'python3\0/namespace/old/runner.py\0';r.missing('/proc/77/exe')
  with self.assertRaisesRegex(Refusal,'operation-process'):r.run()
 def test_forbidden_group_refuses_before_cmdline_loss(self):
  r=Runner();r.rows[77]=old.stat(77,pgrp=900);r.missing('/proc/77/cmdline')
  with self.assertRaisesRegex(Refusal,'group-present'):r.run()
 def test_forbidden_lineage_refuses_before_cmdline_loss(self):
  r=Runner();r.rows[77]=old.stat(77,ppid=900);r.missing('/proc/77/cmdline')
  with self.assertRaisesRegex(Refusal,'descendant-present'):r.run()
 def test_seen_birth_persists_across_partial_pair(self):
  r=Runner();r.missing('/proc/77/cmdline');r.rows[(77,2)]=old.stat(77,birth='999')
  with self.assertRaisesRegex(Refusal,'pid-reused'):r.run()
 def test_three_incomplete_pairs_refuse(self):
  r=Runner()
  for count in (1,2,3):r.missing('/proc/77/stat',count)
  with self.assertRaisesRegex(Refusal,'retry-exhausted'):r.run()
  self.assertEqual(r.enumerations,3);self.assertEqual(len(r.observations()),3)
 def test_subclass_not_builtin_enoent_refuses(self):
  class Sub(FileNotFoundError):pass
  r=Runner();r.missing('/proc/77/stat',kind=Sub)
  with self.assertRaises(Sub):r.run()
  self.assertEqual(r.enumerations,1)
 def test_wrong_filename_refuses(self):
  r=Runner();r.errors[('/proc/77/stat',1)]=FileNotFoundError(errno.ENOENT,'wrong','/proc/78/stat')
  with self.assertRaises(FileNotFoundError):r.run()
  self.assertEqual(r.enumerations,1)
 def test_permission_refuses(self):
  r=Runner();r.errors[('/proc/77/stat',1)]=PermissionError(errno.EACCES,'no','/proc/77/stat')
  with self.assertRaises(PermissionError):r.run()
 def test_observer_birth_change_after_partial_refuses(self):
  r=Runner();r.missing('/proc/77/stat');calls=[0]
  def observer(pid):
   calls[0]+=1;return dict(pid=88,starttime='999' if calls[0]>2 else '555',uids=[0]*4,gids=[0]*4)
  r.ns['same_ofd_process']=observer
  with self.assertRaisesRegex(Refusal,'observer-raced'):r.run()
  self.assertEqual(r.enumerations,1)
 def test_observer_enoent_hard(self):
  r=Runner();r.missing('/proc/88/stat')
  with self.assertRaises(FileNotFoundError):r.run()
  self.assertEqual(r.enumerations,1)
 def test_capture_ceiling_unchanged(self):
  r=Runner();r.ns['DEAD_CALLER_CAPTURE_BYTES']=16<<20
  with self.assertRaisesRegex(Refusal,'capture-total-bound'):r.run()
 def test_process_count_ceiling_unchanged(self):
  r=Runner();r.batches=[['nonpid']*4097]
  with self.assertRaisesRegex(Refusal,'process-count'):r.run()
if __name__=='__main__':unittest.main(verbosity=2)
