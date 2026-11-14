"""Functional deterministic process-lifecycle fixtures; no security testing.
All procfs/identity IO is mocked, including root UID; no root/native queries.
"""
import ast,builtins,contextlib,copy,errno,hashlib,io,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
ROOT=Path(__file__).resolve().parent
OLD=(ROOT/'PROC_CODE.ORIGINAL.v1.py').read_text();NEW=(ROOT/'PROC_CODE.LIFECYCLE.v2.py').read_text()
SOURCE=next(ROOT.glob('native*.py'));TREE=ast.parse(SOURCE.read_text())
CALLER=[99,'100'];BOOT='fixture-boot';CHALLENGE='a'*48

def stat_bytes(pid,birth=None,state='S',bad_number=False):
 fields=['0']*50;fields[0]=state;fields[1]='10' if pid==99 else '1';fields[19]=birth or ('100' if pid==99 else str(1000+pid))
 if bad_number:fields[10]='bad'
 return (str(pid)+' (fixture) '+' '.join(fields)+'\n').encode()
class FS:
 def __init__(self,lists=None,events=None,exe=None,boot=None):
  self.lists=lists or [[1,99,31]]*2;self.events=events or {};self.exe=exe or {};self.snapshot=0;self.counts={};self.boot=boot or [BOOT]*20;self.boot_reads=0
 def listdir(self,path):
  assert path=='/proc';self.snapshot+=1;value=self.lists[min(self.snapshot-1,len(self.lists)-1)]
  if isinstance(value,Exception):raise value
  return [str(pid) for pid in value]
 def event(self,pid,leaf):
  key=(self.snapshot,pid,leaf);self.counts[key]=self.counts.get(key,0)+1
  event=self.events.get((*key,self.counts[key]))
  path='/proc/'+str(pid)+'/'+leaf
  if event=='gone':raise FileNotFoundError(errno.ENOENT,'No such file or directory',path)
  if isinstance(event,Exception):raise event
  return event
 def open(self,path,mode='r',*args,**kw):
  path=str(path)
  if path=='/proc/sys/kernel/random/boot_id':
   value=self.boot[min(self.boot_reads,len(self.boot)-1)];self.boot_reads+=1
   if isinstance(value,Exception):raise value
   return io.StringIO(value+'\n')
  _,proc,pid,leaf=path.split('/');assert proc=='proc';pid=int(pid);event=self.event(pid,leaf)
  if isinstance(event,bytes):return io.BytesIO(event)
  if leaf=='stat':return io.BytesIO(stat_bytes(pid))
  if leaf=='cmdline':return io.BytesIO((self.exe.get(pid,'/usr/bin/sleep')+'\0').encode())
  raise AssertionError(path)
 def readlink(self,path):
  pid=int(str(path).split('/')[2]);self.event(pid,'exe');return self.exe.get(pid,'/usr/bin/sleep')

def run(code,fs):
 fakeos=SimpleNamespace(listdir=fs.listdir,readlink=fs.readlink,geteuid=lambda:0,path=os.path)
 fakesys=SimpleNamespace(argv=['collector',CHALLENGE,str(CALLER[0]),CALLER[1]])
 stdout=io.StringIO();failure=None
 with mock.patch.dict(sys.modules,{'os':fakeos,'sys':fakesys}),contextlib.redirect_stdout(stdout):
  try:exec(compile(code,'<retained-PROC_CODE>','exec'),{'__builtins__':dict(vars(builtins),open=fs.open)})
  except Exception as exc:failure=exc
 raw=stdout.getvalue();return (json.loads(raw) if raw else None),failure

def validate(report):
 class Refusal(RuntimeError):pass
 node=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='validate_process_report')
 ns=dict(Refusal=Refusal,BOOT_ID=BOOT,OWNER_PID=9000,WAITER_PIDS=(9001,));exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
 ns['validate_process_report'](report,CHALLENGE,CALLER)
 return True
class Checks(unittest.TestCase):
 def test_original_actual_errno2_reproducer(self):
  retained=(ROOT/'ORIGINAL-ACTUAL-COLLECTOR.stderr').read_bytes();self.assertEqual(len(retained),192);self.assertEqual(hashlib.sha256(retained).hexdigest(),'1781f39d0960d572cb51c609210705e722790ba7363696c6915e5f20e0eeb4f4');self.assertIn(b'/proc/1060848/stat',retained)
  fs=FS([[1,99,1060848]],{(1,1060848,'stat',1):'gone'});report,error=run(OLD,fs);self.assertIsNone(report);self.assertIs(type(error),FileNotFoundError);self.assertEqual(error.filename,'/proc/1060848/stat')
 def test_stable_no_retry_exact_complete_pair(self):
  fs=FS();report,error=run(NEW,fs);self.assertIsNone(error);self.assertEqual(report['attempts'],1);self.assertEqual(report['retry_failures'],[]);self.assertEqual(fs.snapshot,2);self.assertTrue(validate(report));self.assertEqual([len(x) for x in report['snapshots']],[3,3])
 def test_first_partial_pair_discard_and_normal_exit_fresh_pair(self):
  fs=FS([[1,31,99,1060848],[1,99,51],[1,99,51]],{(1,1060848,'stat',1):'gone'});report,error=run(NEW,fs);self.assertIsNone(error);self.assertTrue(validate(report));self.assertEqual(report['attempts'],2);self.assertEqual(fs.snapshot,3);self.assertEqual(report['retry_failures'][0]['snapshot'],1)
  for rows in report['snapshots']:self.assertEqual({row[0] for row in rows},{1,99,51})
 def test_second_snapshot_failure_discards_both_prior_snapshots(self):
  fs=FS([[1,99,31],[1,41,99,1060848],[1,99,51],[1,99,51]],{(2,1060848,'stat',1):'gone'});report,error=run(NEW,fs);self.assertIsNone(error);self.assertTrue(validate(report));self.assertEqual(fs.snapshot,4);self.assertEqual(report['retry_failures'][0]['snapshot'],2)
  for rows in report['snapshots']:self.assertEqual({row[0] for row in rows},{1,99,51})
 def test_persistent_churn_exactly_three_failed_attempts_no_output(self):
  fs=FS([[1,99,1060848]]*3,{(n,1060848,'stat',1):'gone' for n in [1,2,3]});report,error=run(NEW,fs);self.assertIsNone(report);self.assertEqual(fs.snapshot,3);self.assertIs(type(error),RuntimeError);self.assertIn('process-census-lifecycle-exhausted',str(error));data=json.loads(str(error).split(':',1)[1]);self.assertEqual(len(data['retry_failures']),3)
 def test_all_three_enumerated_paths_and_second_stat_retry(self):
  for leaf,count in [('stat',1),('cmdline',1),('exe',1),('stat',2)]:
   fs=FS([[1,99,31],[1,99,51],[1,99,51]],{(1,31,leaf,count):'gone'});report,error=run(NEW,fs);self.assertIsNone(error);self.assertTrue(validate(report));self.assertEqual(report['attempts'],2);self.assertEqual(report['retry_failures'][0]['operation'],leaf)
 def test_protected_caller_loss_never_retries(self):
  for event in [{(0,99,'stat',1):'gone'},{(1,99,'stat',1):'gone'}]:
   fs=FS([[1,99,31]],event);report,error=run(NEW,fs);self.assertIsNone(report);self.assertIs(type(error),FileNotFoundError);self.assertLessEqual(fs.snapshot,1)
 def test_changed_birth_malformed_and_intermediate_caller_bad_stat_no_retry(self):
  for events in [{(1,31,'stat',2):stat_bytes(31,birth='999')},{(1,31,'stat',1):b'bad'}, {(1,99,'stat',3):stat_bytes(99,state='?')},{(1,99,'stat',3):stat_bytes(99,bad_number=True)}]:
   fs=FS([[1,99,31]],events);report,error=run(NEW,fs);self.assertIsNone(report);self.assertIs(type(error),ValueError);self.assertEqual(fs.snapshot,1)
 def test_permission_unknown_wrong_path_or_enumeration_error_no_retry(self):
  errors=[PermissionError(errno.EACCES,'denied','/proc/31/stat'),OSError(errno.EIO,'io','/proc/31/stat'),FileNotFoundError(errno.ENOENT,'gone','/proc/different/stat')]
  for error in errors:
   fs=FS([[1,99,31]],{(1,31,'stat',1):error});report,actual=run(NEW,fs);self.assertIsNone(report);self.assertIs(actual,error);self.assertEqual(fs.snapshot,1)
  fs=FS([FileNotFoundError(errno.ENOENT,'gone','/proc')]);report,error=run(NEW,fs);self.assertIsNone(report);self.assertIs(type(error),FileNotFoundError);self.assertEqual(fs.snapshot,1)
 def test_boot_change_does_not_retry(self):
  fs=FS(boot=[BOOT,'other']);report,error=run(NEW,fs);self.assertIsNone(report);self.assertIs(type(error),ValueError);self.assertEqual(fs.snapshot,0)
 def test_known_native_publisher_at_last_stat_and_before_churn_no_retry(self):
  for entries,events in [([1,99,31],{(1,31,'stat',2):'gone'}),([1,31,99,1060848],{(1,1060848,'stat',1):'gone'})]:
   fs=FS([entries],events,exe={31:'/usr/bin/gcc'});report,error=run(NEW,fs);self.assertIsNone(report);self.assertIs(type(error),ValueError);self.assertIn('native-publisher-observed',str(error));self.assertEqual(fs.snapshot,1)
 def test_stable_native_publisher_and_related_owner_still_refused(self):
  report,error=run(NEW,FS(exe={31:'/usr/bin/gcc'}));self.assertIsNone(error)
  with self.assertRaisesRegex(RuntimeError,'concurrent-build'):validate(report)
  report,error=run(NEW,FS([[1,99,9000]]*2));self.assertIsNone(error)
  with self.assertRaisesRegex(RuntimeError,'owner-waiter'):validate(report)
 def test_strict_lifecycle_metadata_schema_and_count_guards(self):
  report,error=run(NEW,FS([[1,99,31],[1,99,51],[1,99,51]],{(1,31,'stat',1):'gone'}));self.assertIsNone(error)
  for change in [lambda r:r.update(schema='fp-save-image.proc.v1'),lambda r:r.update(attempts=4),lambda r:r['retry_failures'][0].update(pid=99),lambda r:r['retry_failures'][0].update(errno=13),lambda r:r['retry_failures'][0].update(path='/proc/other/stat'),lambda r:r['retry_failures'][0].update(extra=1),lambda r:r.update(extra=1),lambda r:r['snapshots'][0].pop()]:
   candidate=copy.deepcopy(report);change(candidate)
   with self.assertRaises(RuntimeError):validate(candidate)
  fs=FS([list(range(1,4098))]);report,error=run(NEW,fs);self.assertIsNone(report);self.assertEqual(str(error),'process-count');self.assertEqual(fs.snapshot,1)
 def test_root_command_retains_actual_rc_and_stderr_with_no_stdout_dump(self):
  node=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='root_command')
  class Refusal(RuntimeError):pass
  raw=(ROOT/'ORIGINAL-ACTUAL-COLLECTOR.stderr').read_bytes();calls=[]
  def child(*args,**kwargs):calls.append(kwargs);return SimpleNamespace(returncode=1,stdout=b'PRIVATE_FIXTURE_STDOUT',stderr=raw)
  ns=dict(Refusal=Refusal,os=SimpleNamespace(geteuid=lambda:0),subprocess=SimpleNamespace(run=child,DEVNULL=-3,PIPE=-1),hashlib=hashlib,json=json);exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
  with self.assertRaises(Refusal) as caught:ns['root_command'](['/usr/bin/python3'],1<<20)
  context=json.loads(str(caught.exception).split(':/usr/bin/python3:',1)[1]);self.assertEqual(context['returncode'],1);self.assertEqual(bytes.fromhex(context['stderr_prefix_hex']),raw);self.assertTrue(context['stderr_complete']);self.assertEqual(context['stderr_bytes'],192);self.assertNotIn('PRIVATE_FIXTURE_STDOUT',str(caught.exception));self.assertEqual(calls[0]['timeout'],30)
if __name__=='__main__':unittest.main(verbosity=2)
