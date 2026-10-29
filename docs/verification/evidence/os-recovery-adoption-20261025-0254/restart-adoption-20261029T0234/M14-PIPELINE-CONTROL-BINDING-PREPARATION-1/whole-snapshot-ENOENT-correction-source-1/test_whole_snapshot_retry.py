"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic /proc effect leaves only; no real proc, root, process or Docker actions.
"""
from pathlib import Path
from unittest.mock import patch
import ast,copy,errno,importlib.util,io,json,os,sys,types,unittest
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('TEST_ONLY_census_executor',D/'retire_exact_current118_stopped_container.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
normal_path=Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py')
tree=ast.parse(normal_path.read_text());PROC=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets)))
CODE=m.process_source(types.SimpleNamespace(PROC_CODE=PROC),{'cohort':'/TEST_ONLY/cohort'})
def stat(pid,malformed=False,birth=None):
 fields=['S','1','1','1']+['0']*46;fields[19]=str(pid*10 if birth is None else birth)
 return ((str(pid)+' (unit) '+('bad' if malformed else ' '.join(fields))+'\n').encode())
class Proc:
 def __init__(self,leaf='stat',failures=1,error=None,second=False,bad=None):self.leaf=leaf;self.failures=failures;self.error=error;self.second=second;self.bad=bad;self.listings=0;self.stat_reads={}
 def affected(self):return (self.listings>=(2 if self.second else 1) and self.listings<(2 if self.second else 1)+self.failures)
 def fault(self,path,leaf):
  if self.affected() and path.startswith('/proc/200/') and leaf==self.leaf:
   raise self.error if self.error is not None else FileNotFoundError(errno.ENOENT,'TEST_ONLY disappeared',path)
 def listdir(self,path):
  assert path=='/proc';self.listings+=1
  return ['1','100','200'] if self.affected() or self.bad else ['1','100','300']
 def open(self,path,mode='r',*a,**k):
  assert isinstance(path,str) and path.startswith('/proc/')
  if path=='/proc/sys/kernel/random/boot_id':return io.StringIO('7bfc5687-6c04-4d15-84eb-b92ab9a55dcb\n')
  pid=int(path.split('/')[2]);leaf=path.split('/')[-1]
  if leaf=='stat':
   key=(self.listings,pid);self.stat_reads[key]=self.stat_reads.get(key,0)+1
   stage='recheck' if self.stat_reads[key]>1 and self.listings else 'stat';self.fault(path,stage)
   value=stat(pid,malformed=self.bad=='malformed' and pid==200,birth=999 if self.bad=='birth-race' and pid==200 and stage=='recheck' else None)
   return io.BytesIO(value)
  assert leaf=='cmdline';self.fault(path,leaf)
  return io.BytesIO(b'unterminated' if self.bad=='cmdline' and pid==200 else b'unit\0')
 def readlink(self,path):self.fault(path,'exe');return '/bin/unit'
 def execute(self):
  out=io.StringIO();err=io.StringIO();caught=None
  with patch('builtins.open',self.open),patch.object(os,'listdir',self.listdir),patch.object(os,'readlink',self.readlink),patch.object(os,'geteuid',return_value=0),patch.object(sys,'argv',['TEST_ONLY','0'*32,'100','1000']),patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):
   try:exec(compile(CODE,'TEST_ONLY_GENERATED_PROC','exec'),{})
   except BaseException as exc:caught=exc
  return caught,out.getvalue(),[json.loads(line) for line in err.getvalue().splitlines()]
class Tests(unittest.TestCase):
 def test_all_four_disappearances_restart_whole_first_snapshot(self):
  for leaf in ['stat','cmdline','exe','recheck']:
   with self.subTest(leaf=leaf):
    p=Proc(leaf);error,out,events=p.execute();self.assertIsNone(error);report=json.loads(out);self.assertEqual([[r[0] for r in rows] for rows in report['snapshots']],[[1,100,300],[1,100,300]]);self.assertEqual(events,[dict(schema='mckernel.proc.whole-snapshot-abandoned.v1',phase='first',attempt=1,maximum_attempts=3,errno=2,filename='/proc/200/'+('stat' if leaf=='recheck' else leaf))]);self.assertEqual(p.listings,3)
 def test_second_snapshot_independently_restarts(self):
  p=Proc(second=True);error,out,events=p.execute();self.assertIsNone(error);self.assertEqual(events[0]['phase'],'second');self.assertEqual(p.listings,3);self.assertEqual(len(json.loads(out)['snapshots']),2)
 def test_exact_three_attempts_then_failclosed_no_partial_report(self):
  p=Proc(failures=10);error,out,events=p.execute();self.assertIsInstance(error,FileNotFoundError);self.assertEqual(out,'');self.assertEqual(p.listings,3);self.assertEqual([r['attempt'] for r in events],[1,2,3])
 def test_no_retry_for_other_errno_wrong_paths_or_malformed_data(self):
  faults=[PermissionError(errno.EACCES,'TEST_ONLY','/proc/200/stat'),OSError(errno.EIO,'TEST_ONLY','/proc/200/stat'),FileNotFoundError(errno.ENOENT,'TEST_ONLY','/proc/sys/kernel/random/boot_id'),FileNotFoundError(errno.ENOENT,'TEST_ONLY','/proc/200/status'),FileNotFoundError(errno.ENOENT,'TEST_ONLY','/proc/self/stat'),FileNotFoundError(errno.ENOENT,'TEST_ONLY','/proc/200/../stat'),FileNotFoundError(errno.ENOENT,'TEST_ONLY',None)]
  for fault in faults:
   with self.subTest(fault=repr(fault)):
    p=Proc(error=fault);error,out,events=p.execute();self.assertIs(error,fault);self.assertEqual(p.listings,1);self.assertEqual(events,[]);self.assertEqual(out,'')
  for bad in ['malformed','birth-race','cmdline']:
   with self.subTest(bad=bad):
    p=Proc(failures=0,bad=bad);error,out,events=p.execute();self.assertIsInstance(error,ValueError);self.assertEqual(p.listings,1);self.assertEqual(out,'');self.assertEqual(events,[])
 def test_strict_snapshot_body_unchanged(self):
  spec=importlib.util.spec_from_file_location('TEST_ONLY_prior',D.parent/'current-guardian-source-1/retire_exact_current118_stopped_container.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
  prior=ast.parse(old.process_source(types.SimpleNamespace(PROC_CODE=PROC),{'cohort':'/TEST_ONLY/cohort'}));new=ast.parse(CODE)
  before=next(n for n in prior.body if isinstance(n,ast.FunctionDef) and n.name=='snapshot');after=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_snapshot_once');after.name='snapshot';self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))
if __name__=='__main__':unittest.main()
