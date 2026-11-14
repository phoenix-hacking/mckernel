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
B=dict(prior_actors=[{'pid':800}],new_known_actors=[{'pid':801}],holder_pid=802,runner_pid=803,cid='TEST_ONLY_CID',name='TEST_ONLY_NAME')
PACKET={'cohort':'/TEST_ONLY/cohort'}
NORMAL=types.SimpleNamespace(PROC_CODE=PROC)
CODE=m.process_source(NORMAL,PACKET,B,[804])
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
 def test_all_original_snapshot_checks_retained(self):
  spec=importlib.util.spec_from_file_location('TEST_ONLY_rejected',D.parent/'whole-snapshot-ENOENT-correction-source-1/retire_exact_current118_stopped_container.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
  prior=ast.parse(old.process_source(NORMAL,PACKET));new=ast.parse(CODE)
  before=next(n for n in prior.body if isinstance(n,ast.FunctionDef) and n.name=='_snapshot_once');after=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_snapshot_once')
  def added(node):
   if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='record_negative_observation':return True
   if isinstance(node,ast.If) and len(node.body)==1 and isinstance(node.body[0],ast.Raise):
    call=node.body[0].exc
    if isinstance(call,ast.Call) and call.args and isinstance(call.args[0],ast.Constant):
     return call.args[0].value in ('caller-raced','observed-concurrent-publisher')
   return False
  # The old caller check is nested; only three newly inserted top-level nodes removed.
  after.body=[node for node in after.body if not added(node)]
  for oldnode,newnode in zip(before.body,after.body):
   if isinstance(oldnode,ast.For):newnode.body=[node for node in newnode.body if not added(node)]
  self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))

class Scenario(Proc):
 def __init__(self,plans,parents=None,pgids=None,sids=None,publishers=(),faults=None,births=None,boot_race=False):
  super().__init__();self.plans=plans;self.parents=parents or {};self.pgids=pgids or {};self.sids=sids or {};self.publishers=set(publishers);self.faults=faults or {};self.births=births or {};self.boot_reads=0;self.boot_race=boot_race;self.namespace={}
 def listdir(self,path):
  assert path=='/proc';self.listings+=1;return [str(x) for x in self.plans[min(self.listings-1,len(self.plans)-1)]]
 def fault(self,path,leaf):
  key=(self.listings,int(path.split('/')[2]),leaf)
  if key in self.faults:raise self.faults[key]
 def open(self,path,mode='r',*a,**k):
  if path=='/proc/sys/kernel/random/boot_id':
   self.boot_reads+=1;return io.StringIO('DIFFERENT' if self.boot_race and self.boot_reads==2 else '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb\n')
  pid=int(path.split('/')[2]);leaf=path.split('/')[-1]
  if leaf=='stat':
   key=(self.listings,pid);self.stat_reads[key]=self.stat_reads.get(key,0)+1;stage='recheck' if self.stat_reads[key]>1 and self.listings else 'stat';self.fault(path,stage)
   value=stat(pid,birth=self.births.get(pid));left,_,right=value.rpartition(b') ');fields=right.split();fields[1]=str(self.parents.get(pid,1)).encode();fields[2]=str(self.pgids.get(pid,1)).encode();fields[3]=str(self.sids.get(pid,1)).encode();return io.BytesIO(left+b') '+b' '.join(fields))
  assert leaf=='cmdline';self.fault(path,leaf);return io.BytesIO(b'unit\0')
 def readlink(self,path):self.fault(path,'exe');return '/usr/bin/rustc' if int(path.split('/')[2]) in self.publishers else '/bin/unit'
 def execute(self):
  out=io.StringIO();err=io.StringIO();caught=None
  with patch('builtins.open',self.open),patch.object(os,'listdir',self.listdir),patch.object(os,'readlink',self.readlink),patch.object(os,'geteuid',return_value=0),patch.object(sys,'argv',['TEST_ONLY','0'*32,'100','1000']),patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):
   try:exec(compile(CODE,'TEST_ONLY_GENERATED_PROC','exec'),self.namespace)
   except BaseException as exc:caught=exc
  return caught,out.getvalue(),[json.loads(line) for line in err.getvalue().splitlines()]
def gone(pid,leaf='stat'):return FileNotFoundError(errno.ENOENT,'TEST_ONLY disappeared','/proc/'+str(pid)+'/'+leaf)
class ExpertTests(unittest.TestCase):
 def assert_fatal(self,p,message,events=0):
  error,out,rows=p.execute();self.assertIsInstance(error,ValueError);self.assertIn(message,str(error));self.assertEqual(out,'');self.assertEqual(len(rows),events);return p
 def test_retained_publisher_counterexample_and_own_recheck_loss(self):
  p=Scenario([[1,100,150,200],[1,100,300]],publishers=[150],faults={(1,200,'stat'):gone(200)});self.assert_fatal(p,'observed-concurrent-publisher');self.assertEqual(p.listings,1)
  p=Scenario([[1,100,150],[1,100,300]],publishers=[150],faults={(1,150,'recheck'):gone(150)});self.assert_fatal(p,'observed-concurrent-publisher');self.assertEqual(p.listings,1)
 def test_known_reused_prior_pids_and_forbidden_groups_before_other_loss(self):
  for pid in [800,801,802,803,804]:
   with self.subTest(pid=pid):
    p=Scenario([[1,100,pid,200]],births={pid:999999},faults={(1,200,'stat'):gone(200)});self.assert_fatal(p,'observed-');self.assertEqual(p.listings,1)
  for kwargs in [dict(pgids={150:800}),dict(sids={150:803}),dict(pgids={150:804})]:
   self.assert_fatal(Scenario([[1,100,150,200]],faults={(1,200,'stat'):gone(200)},**kwargs),'observed-forbidden')
 def test_out_of_order_and_cross_attempt_descendants_remain_negative(self):
  self.assert_fatal(Scenario([[1,100,500,400]],parents={500:400,400:802}),'observed-owner-waiter-or-descendant')
  p=Scenario([[1,100,500,200],[1,100,400]],parents={500:400,400:802},faults={(1,200,'stat'):gone(200)});self.assert_fatal(p,'observed-owner-waiter-or-descendant',events=1);self.assertEqual(p.namespace['observed_parents'][500],{400});self.assertEqual(p.namespace['observed_parents'][400],{802})
  p=Scenario([[1,100,500],[1,100,400]],parents={500:400,400:802});self.assert_fatal(p,'observed-owner-waiter-or-descendant');self.assertEqual(p.listings,2);self.assertIn(500,p.namespace['observed_parents'])
 def test_unrelated_negative_free_disappearance_still_allowed(self):
  p=Scenario([[1,100,200],[1,100,300]],faults={(1,200,'cmdline'):gone(200,'cmdline')});error,out,events=p.execute();self.assertIsNone(error);self.assertEqual(len(events),1);self.assertEqual([[r[0] for r in rows] for rows in json.loads(out)['snapshots']],[[1,100,300],[1,100,300]]);self.assertIn(200,p.namespace['observed_parents'])
 def test_caller_birth_and_boot_races_remain_fatal(self):
  self.assert_fatal(Scenario([[1,100,300]],births={100:9999},faults={(1,100,'cmdline'):gone(100,'cmdline')}),'caller-raced')
  self.assert_fatal(Scenario([[1,100,300]],boot_race=True),'boot-raced')
 def test_exact_prior_command_prefix_at_all_three_proc_receipts(self):
  tree=ast.parse((D/'retire_exact_current118_stopped_container.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_result');roles=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='roles' for t in n.targets));loop=next(n for n in fn.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and any(isinstance(t,ast.Name) and t.id=='receipt_index' for t in n.target.elts))
  context=dict(normal=NORMAL,packet=PACKET,b=B,profile={'inputs':{'image':'TEST_ONLY_IMAGE'}},PREFIX=m.PREFIX,actor={'pid':100,'birth':1000},process_source=m.process_source,need=m.need,re=m.re)
  exec(compile(ast.Module(body=[roles],type_ignores=[]),'TEST_ONLY_ROLES','exec'),context);receipts=[];positions=[]
  for index,role in enumerate(context['roles']):
   if role=='PROC':
    positions.append(index);code=m.process_source(NORMAL,PACKET,B,[r['pid'] for r in receipts]);argv=['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,'0'*32,'100','1000']
   else:argv=m.PREFIX+role
   receipts.append(dict(pid=5000+index,argv=argv))
  context['receipts']=receipts;check=compile(ast.Module(body=[loop],type_ignores=[]),'TEST_ONLY_RECEIPT_LOOP','exec');exec(check,context);self.assertEqual(positions,[0,5,12])
  for index in positions:
   bad=copy.deepcopy(receipts);bad[index]['argv'][6]=m.process_source(NORMAL,PACKET,B,[999999]);context['receipts']=bad
   with self.subTest(index=index),self.assertRaises(m.Refusal):exec(check,context)
 def test_actual_call_and_census_source_context_prefix(self):
  called=[];commands=types.SimpleNamespace(children=[types.SimpleNamespace(pid=804)],client_retirement_unproven=False,exact=lambda argv,*a,**k:called.append(argv) or types.SimpleNamespace(stdout='TEST_ONLY'))
  fake=types.SimpleNamespace(normal=NORMAL,p=PACKET,b=B,commands=commands,safe=lambda:None,m=types.SimpleNamespace(proc_stat=lambda pid:['']*19+['1000']))
  args=['-c',m.process_source(NORMAL,PACKET,B,[804]),'0'*32,str(os.getpid()),'1000'];m.Actual.call(fake,args,root_process=True);self.assertEqual(len(called),1)
  bad=list(args);bad[1]=m.process_source(NORMAL,PACKET,B,[])
  with self.assertRaises(m.Refusal):m.Actual.call(fake,bad,root_process=True)
  tree=ast.parse((D/'retire_exact_current118_stopped_container.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Actual');census=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='census');source_calls=[n for n in ast.walk(census) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='process_source'];self.assertEqual(len(source_calls),1);self.assertEqual([ast.dump(a,include_attributes=False) for a in source_calls[0].args],[ast.dump(ast.parse(x,mode='eval').body,include_attributes=False) for x in ['self.normal','self.p','self.b','prior_pids']])

if __name__=='__main__':unittest.main()
