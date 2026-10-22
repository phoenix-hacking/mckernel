"""Actual embedded producer + validator + process_absent/census; explicit proc/time/root boundaries only."""
import ast,builtins,contextlib,copy,io,json,os,sys,time,types,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parent
SOURCE=(P/'coupled/bound-terminal-proc-v2-source-4/cleanup_pass_image.py').read_text();TREE=ast.parse(SOURCE)
PROC=ast.literal_eval(next(n.value for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets)))
BOOT='fixture-boot';CALLER=[20,'20']
def stat(pid,parent=1,start=None):
 values=[b'0']*50;values[0]=b'S';values[1]=str(parent).encode();values[19]=str(pid if start is None else start).encode()
 return str(pid).encode()+b' (fixture) '+b' '.join(values)+b'\n'
class Proc:
 def __init__(self,scenario):self.scenario=scenario;self.sweep=0;self.reads={};self.clock=0;self.sleeps=[]
 def listing(self,path):
  assert path=='/proc';self.sweep+=1
  if self.scenario=='deadline':self.clock=5_000_000_000
  extra=self.scenario in ('initial','after','publisher','exhaustion','retry-reuse','prior-owner','prior-descendant') and (self.sweep==1 or self.scenario=='exhaustion')
  return ['1','20']+(['30','40'] if extra else [])
 def open(self,path,mode='r',*args,**kwargs):
  if path=='/proc/sys/kernel/random/boot_id':return io.StringIO(BOOT)
  pid=int(path.split('/')[2]);part=path.split('/')[3];key=(self.sweep,pid,part);self.reads[key]=self.reads.get(key,0)+1
  if self.scenario=='permission' and self.sweep==1 and pid==30:raise PermissionError(13,'denied',path)
  if self.scenario in ('initial','exhaustion','retry-reuse','prior-owner','prior-descendant','publisher') and self.sweep>=1 and pid==40:raise FileNotFoundError(2,'gone',path)
  if self.scenario=='after' and self.sweep==1 and pid==30 and part=='stat' and self.reads[key]==2:raise FileNotFoundError(2,'gone',path)
  if part=='stat':
   if self.scenario=='malformed' and self.sweep==1 and pid==20:return io.BytesIO(b'bad')
   parent=999 if self.scenario=='prior-descendant' and pid==30 else (0 if pid==1 else 1)
   start=21 if self.scenario=='snapshot-reuse' and self.sweep==2 and pid==20 else None
   if self.scenario=='retry-reuse' and self.sweep==2 and pid==20:start=21
   return io.BytesIO(stat(pid,parent,start))
  assert part=='cmdline';return io.BytesIO(b'fixture\0')
 def readlink(self,path):
  return '/usr/bin/make' if self.scenario=='publisher' and self.sweep==1 and path=='/proc/30/exe' else '/usr/bin/fixture'
 def monotonic(self):self.clock+=1000;return self.clock
 def sleep(self,seconds):self.sleeps.append(seconds);self.clock+=int(seconds*1e9)
 def run(self):
  out=io.StringIO()
  with patch('builtins.open',self.open),patch.object(os,'listdir',self.listing),patch.object(os,'readlink',self.readlink),patch.object(os,'geteuid',lambda:0),patch.object(time,'monotonic_ns',self.monotonic),patch.object(time,'sleep',self.sleep),patch.object(sys,'argv',['producer','challenge','20','20']),contextlib.redirect_stdout(out):exec(compile(PROC,'<actual embedded producer>','exec'),{})
  return json.loads(out.getvalue())
class Refusal(ValueError):pass
def functions(names,ns):
 for name in names:
  node=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name)
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual function '+name+'>','exec'),ns)
 return ns
def namespace():return dict(Refusal=Refusal,BOOT_ID=BOOT,OWNER_PID=999,WAITER_PIDS=(),json=json,canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def validate(report,owner=999):
 ns=functions(['validate_process_report'],namespace());ns['OWNER_PID']=owner;ns['validate_process_report'](report,'challenge',CALLER)
class Tests(unittest.TestCase):
 def positive(self,name,failed=0):
  provider=Proc(name);report=provider.run();self.assertEqual(report['status'],'COMPLETE');self.assertEqual(len(report['acquisition']['attempts']),2+failed);validate(report);return report
 def test_two_full_sweeps(self):self.positive('positive')
 def test_initial_stat_vanish_retained(self):
  r=self.positive('initial',1);f=r['acquisition']['attempts'][0]['failure'];self.assertEqual((f['pid'],f['phase'],f['identity']),(40,'initial-stat',None));self.assertEqual(len(r['snapshots']),2);self.assertRaisesRegex(Refusal,'descendant',validate,r,40)
 def test_vanish_after_identity(self):
  r=self.positive('after',1);self.assertEqual(r['acquisition']['attempts'][0]['failure']['identity'],[30,1,'30']);self.assertIn([30,1,'30'],r['acquisition']['observed'])
 def test_publisher_before_failed_sweep(self):
  r=Proc('publisher').run();self.assertEqual(r['status'],'COMPLETE');self.assertEqual(r['publishers'],[[30,'30','/usr/bin/make']]);self.assertRaisesRegex(Refusal,'publisher',validate,r)
 def test_prior_owner_and_descendant(self):
  r=Proc('prior-owner').run();self.assertRaisesRegex(Refusal,'descendant',validate,r,30)
  r=Proc('prior-descendant').run();self.assertRaisesRegex(Refusal,'descendant',validate,r)
 def test_pid_reuse_across_retries_and_snapshots(self):
  for name in ('retry-reuse','snapshot-reuse'):
   r=Proc(name).run();self.assertEqual(r['status'],'REFUSED');self.assertEqual(r['failure']['reason'],'process-raced');self.assertRaises(Refusal,validate,r)
 def test_exhaustion(self):
  r=Proc('exhaustion').run();self.assertEqual(r['failure']['reason'],'process-acquisition-exhausted');self.assertEqual(len(r['acquisition']['attempts']),8);self.assertEqual(r['snapshots'],[]);self.assertRaises(Refusal,validate,r)
 def test_deadline(self):
  r=Proc('deadline').run();self.assertEqual(r['failure']['reason'],'process-acquisition-deadline');self.assertLessEqual(len(r['acquisition']['attempts']),1);self.assertRaises(Refusal,validate,r)
 def test_malformed_permissions(self):
  for name in ('malformed','permission'):
   p=Proc(name)
   if name=='permission':
    original=p.listing
    p.listing=lambda path:original(path)+['30']
   r=p.run();self.assertEqual(r['status'],'REFUSED');self.assertEqual(len(r['acquisition']['attempts']),1);self.assertRaises(Refusal,validate,r)
 def test_schema_ledger_and_snapshot_omissions(self):
  r=Proc('initial').run()
  variants=[]
  c=copy.deepcopy(r);c['snapshots']=c['snapshots'][:1];variants.append(c)
  c=copy.deepcopy(r);c['acquisition']['observed']=[x for x in c['acquisition']['observed'] if x[0]!=30];variants.append(c)
  c=copy.deepcopy(r);c['acquisition']['attempts'][0]['failure']['identity']=[40,1,'40'];variants.append(c)
  c=copy.deepcopy(r);c['schema']='fp-save-image.proc.v1';variants.append(c)
  c=copy.deepcopy(r);c['acquisition']['attempts'][0]['failure']=None;variants.append(c)
  for c in variants:self.assertRaises(Refusal,validate,c)
 def test_actual_process_absent_census_refusal_stops_docker_and_mutation(self):
  for scenario in ('positive','initial','publisher','exhaustion','snapshot-reuse','malformed','deadline'):
   r=Proc(scenario).run();called=[];ns=namespace();ns.update(PROCESS_REPORTS=[],PROC_LIMIT=4<<20,PROCESS_TOTAL_LIMIT=16<<20,PROC_CODE=PROC,
    os=types.SimpleNamespace(urandom=lambda n:bytes(24),getpid=lambda:20),Path=lambda p:types.SimpleNamespace(read_bytes=lambda:stat(20)),
    parse=json.loads,root_command=lambda argv,limit:json.dumps(dict(r,challenge=bytes(24).hex())).encode(),docker=lambda argv:called.append(argv))
   functions(['validate_process_report','process_absent','census'],ns)
   # Docker boundary raises only for valid absence; every refusal returns first.
   ns['docker']=lambda argv:(_ for _ in ()).throw(RuntimeError('docker reached'))
   expected=RuntimeError if scenario in ('positive','initial') else Refusal
   with self.assertRaises(expected):ns['census']()
   self.assertEqual(len(ns['PROCESS_REPORTS']),1);self.assertEqual(ns['PROCESS_REPORTS'][0]['acquisition'],r['acquisition'])
 def test_actual_transaction_preflight_refusal_retains_no_mutation(self):
  method=next(n for n in TREE.body if isinstance(n,ast.ClassDef) and n.name=='Transaction')
  method=next(n for n in method.body if isinstance(n,ast.FunctionDef) and n.name=='preflight_fresh')
  for scenario in ('publisher','exhaustion','snapshot-reuse','malformed','deadline'):
   r=Proc(scenario).run();events=[];ns=namespace();ns.update(PROCESS_REPORTS=[],PROC_LIMIT=4<<20,PROCESS_TOTAL_LIMIT=16<<20,PROC_CODE=PROC,
    os=types.SimpleNamespace(urandom=lambda n:bytes(24),getpid=lambda:20),Path=lambda p:types.SimpleNamespace(read_bytes=lambda:stat(20)),
    parse=json.loads,root_command=lambda argv,limit:json.dumps(dict(r,challenge=bytes(24).hex())).encode(),docker=lambda argv:events.append('docker'),
    exists=lambda *a:False,protected_files=lambda:None,capture_logs=lambda *a,**k:events.append('capture'),
    MUTEX=Path('/fixture/mutex'),PLAN=Path('/fixture/plan'),JOURNAL=Path('/fixture/journal'),CAPTURE=Path('/fixture/capture'),QUARANTINE=Path('/fixture/quarantine'),
    ATTEMPT=Path('/fixture/attempt'),SHARED=Path('/fixture/shared'),ARCHIVE_NAMES=('a','b'))
   functions(['validate_process_report','process_absent','census'],ns)
   exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual Transaction.preflight_fresh>','exec'),ns)
   # Existing root/filesystem boundaries are inert; actual preflight/census/acquisition control flow executes.
   tx=types.SimpleNamespace(root_locked=True,mutation_started=False,mfd=None,fd=-1,pinned=lambda:None,parent_fd=lambda p:-1,lock=lambda _:None,pristine=lambda:None)
   self.assertRaises(Refusal,ns['preflight_fresh'],tx)
   self.assertEqual(events,[]);self.assertFalse(tx.mutation_started);self.assertIsNone(tx.mfd)
 def test_postjoin_actual_census_refusal_retention_and_restore(self):
  report=Proc('exhaustion').run();state=[(1073741824,2147483648)];out=io.StringIO()
  resource=types.SimpleNamespace(RLIMIT_AS=1,getrlimit=lambda _:state[0],setrlimit=lambda _,value:state.__setitem__(0,value))
  source=(P/'coupled/bound-terminal-proc-v2-source-4/postjoin_readback.py').read_text()
  node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='census_at_2g')
  def census():raise Refusal('process-acquisition-refused')
  m=types.SimpleNamespace(census=census,PROCESS_REPORTS=[report])
  ns=dict(resource=resource,sys=types.SimpleNamespace(stderr=out),json=json,need=lambda ok,why:None if ok else (_ for _ in ()).throw(RuntimeError(why)))
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual postjoin census_at_2g>','exec'),ns)
  self.assertRaises(Refusal,ns['census_at_2g'],m)
  self.assertEqual(state[0],(1073741824,2147483648));retained=json.loads(out.getvalue());self.assertEqual(retained['process_reports'],[report])
 def test_finite_count_cap_refuses_before_next_acquisition(self):
  called=[];ns=namespace();ns.update(PROCESS_REPORTS=[{} for _ in range(16)],PROC_LIMIT=4<<20,PROCESS_TOTAL_LIMIT=16<<20,PROC_CODE=PROC,
    os=types.SimpleNamespace(urandom=lambda n:bytes(24),getpid=lambda:20),Path=lambda p:types.SimpleNamespace(read_bytes=lambda:stat(20)),
    parse=json.loads,root_command=lambda *a:called.append(a))
  functions(['process_absent'],ns)
  self.assertRaisesRegex(Refusal,'process-report-count',ns['process_absent']);self.assertEqual(called,[])
 def test_aggregate_cap_refuses_before_next_acquisition(self):
  called=[];ns=namespace();ns.update(PROCESS_REPORTS=[{'retained':'x'*(12<<20)}],PROC_LIMIT=4<<20,PROCESS_TOTAL_LIMIT=16<<20,PROC_CODE=PROC,
    os=types.SimpleNamespace(urandom=lambda n:bytes(24),getpid=lambda:20),Path=lambda p:types.SimpleNamespace(read_bytes=lambda:stat(20)),
    parse=json.loads,root_command=lambda *a:called.append(a))
  functions(['process_absent'],ns)
  self.assertRaisesRegex(Refusal,'aggregate-cap',ns['process_absent']);self.assertEqual(called,[])
if __name__=='__main__':unittest.main(verbosity=2)
