"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual main/recover/Transaction.run/preflight/census/process_absent/producer/validator.
Root/file/container mutation boundaries are in-memory and no host mutation runs.
"""
import argparse,ast,hashlib,json,threading,types,unittest
from pathlib import Path
import test_proc_acquisition as t
P=Path(__file__).resolve().parent
SOURCE=(P/'coupled/bound-terminal-proc-v2-source-4/cleanup_pass_image.py').read_text();TREE=ast.parse(SOURCE)
CID='a'*64
class Fixture:
 def __init__(self,fail_at=None,write_fail=False):
  self.fail_at=fail_at;self.write_fail=write_fail;self.censuses=0;self.present=True;self.files=set();self.rows=[];self.phases=['before_exchange']*2
  self.fd=1;self.mfd=None;self.root_locked=True;self.mutation_started=False;self.closed=False;self.signals=[];self.statuses=[];self.holding=threading.Event();self.block=threading.Event();self.quarantine=None
  ns=t.namespace();self.ns=ns
  ns.update(__file__='actual-engine-fixture',__doc__='actual main fixture',argparse=argparse,subprocess=types.SimpleNamespace(SubprocessError=RuntimeError),
    PROCESS_REPORTS=[],PROCESS_TOTAL_LIMIT=16<<20,PROC_LIMIT=4<<20,PROC_CODE=t.PROC,
    os=types.SimpleNamespace(urandom=lambda n:bytes(24),getpid=lambda:20,geteuid=lambda:0,path=types.SimpleNamespace(lexists=lambda p:p.name in self.files),
       fsync=lambda fd:None,rmdir=self.rmdir),Path=lambda p:types.SimpleNamespace(read_bytes=lambda:t.stat(20)),
    parse=json.loads,root_command=self.root_command,docker=self.docker,validate_container_profile=lambda item:None,
    CONTAINER=CID,CONTAINER_NAME='fixture-container',OWNER_NONCE='fixture-owner',EXPECTED_EXIT=0,UUID='fixture-uuid',RELEASE={},
    ROOT=Path('/fixture'),PLAN=Path('/fixture/plan'),JOURNAL=Path('/fixture/journal'),CAPTURE=Path('/fixture/capture'),QUARANTINE=Path('/fixture/quarantine'),MUTEX=Path('/fixture/mutex'),
    ATTEMPT=Path('/fixture/attempt'),SHARED=Path('/fixture/shared'),ARCHIVE_NAMES=('attempt.archive','shared.archive'),
    exists=lambda fd,name:name in self.files,protected_files=lambda:None,capture_logs=self.capture_logs,
    read_at=lambda *a,**k:None,path_device=lambda p:1,rename_exchange=self.exchange,
    RECORDS={Path('/fixture/attempt'):(),Path('/fixture/shared'):()},digest=lambda raw:hashlib.sha256(raw).hexdigest(),observe_identity=lambda p:dict(path=str(p)),
    archive_paths=lambda:[Path('/fixture/attempt.archive'),Path('/fixture/shared.archive')],PUBLISHER_CONTRACT='fixture-original-contract',
    read_bounded=lambda p:b'{}',configure=lambda value,execute:None,
    signal=types.SimpleNamespace(SIG_BLOCK=0,SIG_SETMASK=1,pthread_sigmask=self.sigmask),DEFERRED_SIGNALS={'deferred'},
    Transaction=lambda:self,time=types.SimpleNamespace(sleep=self.hold_sleep),print=self.capture_print)
  t.functions(['validate_process_report','process_absent','census','terminal_result','quarantine_diagnostic','quarantine_wait','recover','main'],ns)
  klass=next(n for n in TREE.body if isinstance(n,ast.ClassDef) and n.name=='Transaction')
  for name in ('run','preflight_fresh'):
   node=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name==name)
   exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual Transaction.'+name+'>','exec'),ns)
   setattr(self,name,types.MethodType(ns[name],self))
 def root_command(self,args,limit):
  self.censuses+=1
  report=json.loads(json.dumps(self.template_report)) if hasattr(self,'template_report') else t.Proc('exhaustion' if self.censuses==self.fail_at else 'positive').run()
  report['challenge']=args[-3];report['caller']=[int(args[-2]),args[-1]]
  return json.dumps(report,sort_keys=True).encode()
 def docker(self,args):
  if args[0]=='ps':return (json.dumps(dict(ID=CID,Names='fixture-container',Labels='mckernel.owner=fixture-owner',State='exited'))+'\n').encode() if self.present else b''
  if args[0]=='inspect':return json.dumps([dict(Id=CID,Name='/fixture-container',Config=dict(Labels={'mckernel.owner':'fixture-owner'}),State=dict(Status='exited',ExitCode=0,Running=False,Pid=0))]).encode()
  if args[0]=='rm':self.present=False;return CID.encode()
  raise AssertionError(args)
 def pinned(self):pass
 def parent_fd(self,path):return 1
 def pristine(self):pass
 def preserved(self):pass
 def lock(self,execute):
  if execute:self.files.add('mutex');self.mfd=2;self.mutation_started=True
 def capture_logs(self,present,execute,transaction=None):
  if execute:self.files.add('capture');self.mutation_started=True
 def load_plan(self):return self.plan
 def prepare(self):
  self.mutation_started=True;self.files.update(('plan','journal','attempt.archive','shared.archive'))
  self.plan=dict(sentinels=[[1,1],[1,2]]);return self.plan
 def create(self,name,data):
  self.mutation_started=True
  if name=='quarantine':
   if self.write_fail:raise OSError('fixture quarantine persistence failed')
   self.quarantine=bytes(data)
  self.files.add(name)
 def state(self,plan):return list(self.rows),list(self.phases)
 def append(self,plan,rows,event,index):
  row=dict(event=event,index=index);self.rows.append(row);rows.append(row)
 def sentinel(self,*args):pass
 def exchange(self,fd,name,archive):self.phases[0 if name=='attempt' else 1]='after_exchange'
 def rmdir(self,name,dir_fd):self.phases[0 if name=='attempt' else 1]='after_release'
 def close(self):self.closed=True;self.root_locked=False
 def sigmask(self,kind,mask):self.signals.append((kind,mask));return {'previous'}
 def capture_print(self,value,**kwargs):self.statuses.append(json.loads(value))
 def hold_sleep(self,seconds):self.holding.set();self.block.wait()
 def main(self):return self.ns['main'](['--release','fixture-release','--release-sha256',hashlib.sha256(b'{}').hexdigest(),'--execute'])
class Tests(unittest.TestCase):
 def test_full_actual_main_fresh_nine_censuses(self):
  f=Fixture();self.assertEqual(f.main(),0);self.assertEqual(f.censuses,9)
  result=f.statuses[-1];self.assertEqual(result['status'],'PASS_EXECUTED');self.assertEqual(len(result['process_reports']),9)
  self.assertEqual([r['event'] for r in f.rows],['before_exchange','after_exchange','release','after_release']*2+['complete'])
  self.assertEqual(f.phases,['after_release']*2);self.assertTrue(f.closed);self.assertEqual(len(f.signals),2)
  size=len(f.ns['canonical'](result['process_reports']));self.assertLess(size,16<<20)
  (P/'FULL-TRANSACTION-MEASUREMENTS.json').write_text(json.dumps(dict(censuses=f.censuses,report_count=9,serialized_report_bytes=size,largest_report_bytes=max(len(f.ns['canonical'](r)) for r in result['process_reports']),terminal_status=result['status'],root_actions=False),sort_keys=True,indent=2)+'\n')
 def test_largest_normal_census_profile_nine_reports_fit_budget(self):
  provider=t.Proc('positive');original=provider.open
  provider.listing=lambda path:['1','20']+[str(2147483647-index) for index in range(4094)]
  def opened(path,mode='r',*args,**kwargs):
   if path.startswith('/proc/') and path.endswith('/stat'):
    pid=int(path.split('/')[2]);return t.io.BytesIO(t.stat(pid,0 if pid==1 else 2147479553,20 if pid==20 else 18446744073709551615))
   return original(path,mode,*args,**kwargs)
  provider.open=opened;report=provider.run();self.assertEqual(report['status'],'COMPLETE')
  f=Fixture();f.template_report=report;self.assertEqual(f.main(),0);self.assertEqual(f.censuses,9)
  reports=f.statuses[-1]['process_reports'];size=len(f.ns['canonical'](reports));largest=max(len(f.ns['canonical'](r)) for r in reports)
  self.assertLess(size,16<<20);self.assertLess(largest,4<<20)
  self.assertLessEqual(len(f.ns['canonical'](reports[:8])),(16<<20)-(4<<20)-1024)
  (P/'MAX-NORMAL-CENSUS-BUDGET.json').write_text(json.dumps(dict(profile_pid_count=4096,sweeps_each=2,normal_report_count=9,largest_report_bytes=largest,serialized_nine_report_bytes=size,reserve_bytes=4<<20,aggregate_limit_bytes=16<<20,report_count_cap=16,physical_acceptance=False),sort_keys=True,indent=2)+'\n')
 def hold_case(self,write_fail):
  f=Fixture(fail_at=9,write_fail=write_fail);thread=threading.Thread(target=f.main,daemon=True);thread.start()
  self.assertTrue(f.holding.wait(2),'nonreturning quarantine hold not reached')
  self.assertTrue(thread.is_alive());self.assertTrue(f.root_locked);self.assertTrue(f.mutation_started);self.assertFalse(f.closed)
  self.assertEqual(len(f.signals),1);self.assertEqual(f.censuses,9);self.assertEqual(f.phases,['after_release']*2)
  self.assertEqual(f.statuses[-1]['status'],'QUARANTINED_ROOT_LOCK_HELD');reports=f.statuses[-1]['process_reports'];self.assertEqual(len(reports),9)
  self.assertEqual(reports[-1]['failure']['reason'],'process-acquisition-exhausted')
  if write_fail:self.assertIsNone(f.quarantine)
  else:
   durable=json.loads(f.quarantine);self.assertEqual(durable['process_reports'],reports);self.assertEqual(durable['schema'],'fp-save-image.cleanup-quarantine.v1')
  self.assertNotIn('complete',[r['event'] for r in f.rows])
  return f
 def test_postmutation_refusal_durable_quarantine_and_hold(self):self.hold_case(False)
 def test_postmutation_quarantine_write_failure_keeps_lock_and_signal_hold(self):self.hold_case(True)
if __name__=='__main__':unittest.main(verbosity=2)
