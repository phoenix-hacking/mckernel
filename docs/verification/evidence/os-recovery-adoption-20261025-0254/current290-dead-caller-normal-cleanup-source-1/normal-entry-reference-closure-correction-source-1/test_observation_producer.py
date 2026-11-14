"""Functional OS only; no security testing. Mocked producer controls; no root query/effects."""
import ast,copy,hashlib,importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
S=Path(__file__).parent/'produce_actual_owner1043716_cleanup_observation.EXACT-DEAD-CALLER.READONLY.NOT_RELEASED.py'
spec=importlib.util.spec_from_file_location('observation_producer',S);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Tests(unittest.TestCase):
 def test_exact_configure_keys(self):
  p=json.loads(a.PROFILE.read_bytes());t=ast.parse(Path(p['cleanup']['path']).read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='configure');node=next(n for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='required' for v in n.targets));self.assertEqual(a.REQUIRED,set(ast.literal_eval(node.value))|{'normal_owner_join'});self.assertEqual(len(a.REQUIRED),21)
 def test_source_no_cleanup_or_ownership_calls(self):
  t=ast.parse(S.read_text());names={n.func.attr for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)};self.assertFalse(names&{'configure','recover','unlink','rmdir','rename','kill','pidfd_open','execute','duplicate_inherited_root_lock'})
 def query_fake(self,returncode=0,stdout=b'[]',stderr=b'',error=None):
  def run(argv,**kw):
   kw['stdout'].write(stdout);kw['stderr'].write(stderr)
   if error is not None:raise error
   return mock.Mock(returncode=returncode)
  return run
 def test_raw_capture_precedes_guard_and_failure(self):
  p=json.loads(a.PROFILE.read_bytes())
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d,mock.patch.object(a.subprocess,'run',side_effect=self.query_fake(1,b'raw',b'error')):
   with self.assertRaises(ValueError):a.query(p,Path(d),'inspect')
   self.assertEqual((Path(d)/'inspect.stdout').read_bytes(),b'raw');self.assertEqual((Path(d)/'inspect.stderr').read_bytes(),b'error')
 def test_raw_success_and_timeout(self):
  p=json.loads(a.PROFILE.read_bytes())
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d,mock.patch.object(a.subprocess,'run',side_effect=self.query_fake()):self.assertEqual(a.query(p,Path(d),'inspect'),b'[]')
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d,mock.patch.object(a.subprocess,'run',side_effect=self.query_fake(stdout=b'partial',stderr=b'timeout',error=subprocess.TimeoutExpired(['fixed'],30))):
   with self.assertRaises(ValueError):a.query(p,Path(d),'inspect')
   self.assertEqual((Path(d)/'inspect.stdout').read_bytes(),b'partial');self.assertEqual(json.loads((Path(d)/'inspect.status.json').read_bytes())['error'],'TimeoutExpired')
 def fixture(self,root):
  p=json.loads(a.PROFILE.read_bytes());e=mock.Mock();e.parse=json.loads;e.canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode();e.digest=lambda raw:hashlib.sha256(raw).hexdigest();e.ROOT=Path('/scratch');e.UUID='uuid';e.LEASE=root/'absentlease';e.EVIDENCE=root/'evidence';e.OUTPUT=root/'work';e.ATTEMPT=root/'common';e.SHARED=root/'shared';e.REQUEST=root/'request';e.TERMINAL=e.EVIDENCE/'owner-receipt.json';e.ROOT_LOCK=Path('/run/lock/mckernel-development.lock');e.NAMESPACE_BINDING={'device':1};e.NAMESPACE_ANCESTRY=[{'path':'/fixture'}];e.namespace_ancestry.return_value=e.NAMESPACE_ANCESTRY
  paths=[]
  for i in range(7):
   path=e.EVIDENCE/'attempt'/('command-'+str(i))/'status.json';path.parent.mkdir(parents=True);path.write_text(json.dumps({'pid':10+i,'state':'exited','exit_code':0}));paths.append(path)
  request={'image_id':p['target']['image_id'],'source_root':'/source','backup_root':'/backup','candidate_sha':'eb3ce544eb1f479a56933a5c7fa8300ab6dfe533'}
  for key in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest'):request[key]='/'+key;request[key+'_sha256']='unused'
  pairs={'driver_path':'driver_sha256','provenance_path':'provenance_sha256','host_owner_path':'host_owner_sha256','source_manifest':'source_manifest_sha256','toolchain_manifest':'toolchain_manifest_sha256'}
  for key,hkey in pairs.items():request[hkey]='x'
  joined={'pid':1043716,'starttime':'80020161','returncode':1,'direct_child_joined':True,'group_absent':True,'closed_streams':True,'error':None,'retirement_error':None};ready={'holder':{'boot_id':'boot'},'owner_join':joined,'owner_receipt':p['owner_receipt']};receipt=dict(p['target'],status='FAIL');process={'pid':1043716,'starttime':'80020161'};contract={'caller_capture_root':str(root/'caller'),'static':{'request':{'path':'/staticrequest'}}}
  blobs={p['ready']['path']:ready,p['owner_receipt']['path']:receipt,p['join']['path']:joined,p['process']['path']:process,p['contract']['path']:contract,'/staticrequest':request}
  def pinned(row):return json.dumps(blobs[row['path']]).encode()
  e.read_bounded.side_effect=lambda path:path.read_bytes() if path in paths else b'{}'
  e.observe_identity.side_effect=lambda path:{'path':str(path),'sha256':'x','size':1}
  e.metadata_inventory.side_effect=lambda path:[{'path':str(path)}]
  protocol=mock.Mock();protocol.required_static_references.return_value=[];protocol.required_runtime_references.return_value=['/fixture/runtime-required'];e.current230_contract.return_value=protocol
  item={'Id':p['target']['container_id'],'Name':'/'+p['target']['container_name'],'Image':p['target']['image_id'],'Config':{'Labels':{'mckernel.owner':p['target']['owner_nonce']}},'State':{'Status':'exited','Running':False,'Paused':False,'Restarting':False,'OOMKilled':False,'Dead':False,'Pid':0,'ExitCode':1,'Error':''}}
  def query(label):return json.dumps([item] if label=='inspect' else {'filesystems':[{'target':'/scratch','uuid':'uuid','fstype':'ext4','options':'rw,nodev,nosuid'}]}).encode()
  return p,e,pinned,query,protocol,item
 def test_actual_production_branch_shape_and_helpers(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
   p,e,pinned,q,protocol,item=self.fixture(Path(d))
   with mock.patch.object(a,'pinned',side_effect=pinned),mock.patch.object(a,'dead_caller_check',return_value=True),mock.patch.object(a,'normal_entry_references',return_value=[{'path':'/fixture/actual-normal-grant'}]):obs=a.produce(p,e,q)
   self.assertEqual(set(obs),a.REQUIRED);self.assertEqual(len(obs['client_ledger']),7);self.assertEqual(obs['ownership_case'],'FAIL_COMMON_AND_SHARED');self.assertEqual(obs['container_inspect'],item);self.assertEqual(obs['candidate_tree'],'a2da2013134a682d8c22c1843eda39f85e96176a');self.assertIn('/fixture/runtime-required',{r['path'] for r in obs['selected_files']});self.assertIn('/fixture/actual-normal-grant',{r['path'] for r in obs['selected_files']});protocol.required_runtime_references.assert_called_once();protocol.normal_owner_join_binding.assert_called_once();protocol.typed_source_binding.assert_called_once();e.metadata_inventory.assert_any_call(e.EVIDENCE)
 def test_actual_production_rejects_running(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
   p,e,pinned,q,protocol,item=self.fixture(Path(d));item['State']['Running']=True
   with mock.patch.object(a,'pinned',side_effect=pinned),mock.patch.object(a,'dead_caller_check',return_value=True),mock.patch.object(a,'normal_entry_references',return_value=[{'path':'/fixture/actual-normal-grant'}]),self.assertRaisesRegex(ValueError,'terminalstate'):a.produce(p,e,q)
 def test_bootstrap_current_source_pins(self):
  p,e=a.bootstrap()
  self.assertEqual(e.DEAD_CALLER_FROZEN,p['dead_caller_new_ofd'])
  self.assertEqual(p['target']['owner_pid'],1043716)
  self.assertEqual(p['candidate_tree'],'a2da2013134a682d8c22c1843eda39f85e96176a')
 def test_busy_newOFD_refuses_and_closes_without_mutation(self):
  p=json.loads(a.PROFILE.read_bytes());e=mock.Mock();e.ROOT_LOCK=Path('/fixture/mutex');e.DEAD_CALLER_MODE='EXACT_DEAD_CALLER_NEW_OFD'
  e.observe_identity.return_value={'device':27,'inode':4,'uid':0,'gid':0,'mode':'0o644','nlink':1,'size':0}
  with mock.patch.object(a,'pinned',return_value=b'{}'),mock.patch.object(a,'dead_caller_check'),mock.patch.object(a.os,'open',return_value=99),mock.patch.object(a.os,'close') as close,mock.patch.object(a.fcntl,'flock',side_effect=BlockingIOError):
   with self.assertRaises(BlockingIOError):a.acquire_readonly_custody(e,p)
   close.assert_called_once_with(99)
 def alarm_mocks(self,timer=(0.,0.)):
  import contextlib
  stack=contextlib.ExitStack()
  stack.enter_context(mock.patch.object(a.signal,'getitimer',return_value=timer))
  stack.enter_context(mock.patch.object(a.signal,'getsignal',return_value='previous'))
  changes=stack.enter_context(mock.patch.object(a.signal,'signal'))
  timers=stack.enter_context(mock.patch.object(a.signal,'setitimer'))
  return stack,changes,timers
 def test_owned_alarm_expiry_and_restore(self):
  stack,changes,timers=self.alarm_mocks()
  with stack:
   with self.assertRaises(a.ObserverDeadlineExpired):
    with a.own_observer_deadline():changes.call_args_list[0].args[1](a.signal.SIGALRM,None)
   self.assertEqual(timers.call_args_list,[mock.call(a.signal.ITIMER_REAL,240),mock.call(a.signal.ITIMER_REAL,0)])
   self.assertEqual(changes.call_args_list[-1],mock.call(a.signal.SIGALRM,'previous'))
 def test_existing_alarm_refused_untouched(self):
  stack,changes,timers=self.alarm_mocks((12.,0.))
  with stack:
   with self.assertRaisesRegex(ValueError,'existingalarmrefused'):
    with a.own_observer_deadline():self.fail('entered')
   changes.assert_not_called();timers.assert_not_called()
 def test_query_deadline_preserves_raw_and_propagates(self):
  p=json.loads(a.PROFILE.read_bytes())
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d,mock.patch.object(a.subprocess,'run',side_effect=self.query_fake(stdout=b'partial',stderr=b'rawerror',error=a.ObserverDeadlineExpired('fixture'))):
   with self.assertRaises(a.ObserverDeadlineExpired):a.query(p,Path(d),'inspect')
   self.assertEqual((Path(d)/'inspect.stdout').read_bytes(),b'partial')
   self.assertEqual((Path(d)/'inspect.stderr').read_bytes(),b'rawerror')
   self.assertEqual(json.loads((Path(d)/'inspect.status.json').read_text())['error'],'ObserverDeadlineExpired')
 def test_actual_stdlib_run_deadline_kills_and_reaps_own_mock_child(self):
  events=[]
  class Child:
   def __enter__(self):return self
   def __exit__(self,*args):events.append('reap')
   def communicate(self,*args,**kwargs):raise a.ObserverDeadlineExpired('fixture')
   def kill(self):events.append('kill')
   def wait(self):events.append('wait');return -9
  with mock.patch.object(a.subprocess,'Popen',return_value=Child()):
   with self.assertRaises(a.ObserverDeadlineExpired):a.subprocess.run(['/fixture/query'],timeout=30)
  self.assertEqual(events,['kill','reap'])
 def test_main_expiry_before_and_after_lock_no_pass_and_unlock(self):
  import io,contextlib,sys
  for acquired in (False,True):
   with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
    p=json.loads(a.PROFILE.read_bytes());p['capture_directory']=str(Path(d)/'capture');e=mock.Mock();e.DEAD_CALLER_OBSERVATIONS=[{'fixture':'raw'}];e.canonical=lambda v:json.dumps(v).encode()
    stack,changes,timers=self.alarm_mocks();stdout=io.StringIO()
    with stack,mock.patch.object(sys,'argv',['producer','--execute-readonly']),mock.patch.object(a.os,'geteuid',return_value=0),mock.patch.object(a,'bootstrap',return_value=(p,e)),mock.patch.object(a,'acquire_readonly_custody',return_value=99,side_effect=None if acquired else a.ObserverDeadlineExpired('beforelock')),mock.patch.object(a,'produce',side_effect=a.ObserverDeadlineExpired('afterlock')),mock.patch.object(a.os,'close') as close,contextlib.redirect_stdout(stdout):
     with self.assertRaises(a.ObserverDeadlineExpired):a.main()
    self.assertNotIn('PASS_READONLY',stdout.getvalue());bundle=json.loads(stdout.getvalue());self.assertEqual(bundle['status'],'REFUSED_READONLY_OBSERVER')
    self.assertEqual(bundle['readable_evidence']['process_evidence']['raw_utf8'],json.dumps([{'fixture':'raw'}]))
    self.assertEqual(close.call_args_list.count(mock.call(99)),int(acquired))
 def test_readable_lossless_binding(self):
  raw=b'{"fixture":"exact raw bytes"}'
  value=a.readable_evidence(raw)
  self.assertEqual(value['raw_utf8'].encode(),raw);self.assertEqual(value['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(value['bytes'],len(raw))
if __name__=='__main__':unittest.main(verbosity=2)
