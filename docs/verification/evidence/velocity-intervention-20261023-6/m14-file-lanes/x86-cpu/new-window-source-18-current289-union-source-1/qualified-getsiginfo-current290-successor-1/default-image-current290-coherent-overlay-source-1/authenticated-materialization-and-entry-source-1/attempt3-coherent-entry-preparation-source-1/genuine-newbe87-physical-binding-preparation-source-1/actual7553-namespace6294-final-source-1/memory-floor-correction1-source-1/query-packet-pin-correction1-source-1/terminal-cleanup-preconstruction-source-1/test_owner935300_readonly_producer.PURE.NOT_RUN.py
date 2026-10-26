"""Functional OS only; no security testing. Mocked producer controls; no root query/effects."""
import ast,copy,hashlib,importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
S=Path(__file__).parent/'produce_actual_owner935300_cleanup_observation.READONLY.NOT_RELEASED.py'
spec=importlib.util.spec_from_file_location('observation_producer',S);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Tests(unittest.TestCase):
 def test_exact_configure_keys(self):
  p=json.loads(a.PROFILE.read_bytes());t=ast.parse(Path(p['cleanup']['path']).read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='configure');node=next(n for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='required' for v in n.targets));self.assertEqual(a.REQUIRED,set(ast.literal_eval(node.value))|{'normal_owner_join'});self.assertEqual(len(a.REQUIRED),21)
 def test_source_no_cleanup_or_ownership_calls(self):
  t=ast.parse(S.read_text());names={n.func.attr for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)};self.assertFalse(names&{'configure','recover','flock','unlink','rmdir','rename','kill','pidfd_open','execute','duplicate_inherited_root_lock'})
 def test_raw_capture_precedes_guard_and_failure(self):
  p=json.loads(a.PROFILE.read_bytes())
  with tempfile.TemporaryDirectory() as d,mock.patch.object(a.subprocess,'run',return_value=mock.Mock(returncode=1,stdout=b'raw',stderr=b'error')) as run:
   with self.assertRaises(ValueError):a.query(p,Path(d),'inspect')
   self.assertEqual((Path(d)/'inspect.stdout').read_bytes(),b'raw');self.assertEqual((Path(d)/'inspect.stderr').read_bytes(),b'error');self.assertEqual(json.loads((Path(d)/'inspect.status.json').read_bytes())['returncode'],1);self.assertEqual(run.call_args.args[0],p['query_allowlist']['inspect'])
 def test_raw_success_and_timeout(self):
  p=json.loads(a.PROFILE.read_bytes())
  with tempfile.TemporaryDirectory() as d,mock.patch.object(a.subprocess,'run',return_value=mock.Mock(returncode=0,stdout=b'[]',stderr=b'')):self.assertEqual(a.query(p,Path(d),'inspect'),b'[]')
  with tempfile.TemporaryDirectory() as d,mock.patch.object(a.subprocess,'run',side_effect=subprocess.TimeoutExpired(['fixed'],30,output=b'partial',stderr=b'timeout')):
   with self.assertRaises(ValueError):a.query(p,Path(d),'inspect')
   self.assertEqual((Path(d)/'inspect.stdout').read_bytes(),b'partial');self.assertEqual(json.loads((Path(d)/'inspect.status.json').read_bytes())['error'],'TimeoutExpired')
 def fixture(self,root):
  p=json.loads(a.PROFILE.read_bytes());e=mock.Mock();e.parse=json.loads;e.canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode();e.digest=lambda raw:hashlib.sha256(raw).hexdigest();e.ROOT=Path('/scratch');e.UUID='uuid';e.LEASE=root/'absentlease';e.EVIDENCE=root/'evidence';e.OUTPUT=root/'work';e.ATTEMPT=root/'common';e.SHARED=root/'shared';e.REQUEST=root/'request';e.TERMINAL=e.EVIDENCE/'owner-receipt.json';e.ROOT_LOCK=Path('/run/lock/mckernel-development.lock');e.NAMESPACE_BINDING={'device':1};e.NAMESPACE_ANCESTRY=[{'path':'/fixture'}];e.namespace_ancestry.return_value=e.NAMESPACE_ANCESTRY
  paths=[]
  for i in range(7):
   path=e.EVIDENCE/'attempt'/('command-'+str(i))/'status.json';path.parent.mkdir(parents=True);path.write_text(json.dumps({'pid':10+i,'state':'exited','exit_code':0}));paths.append(path)
  request={'image_id':p['target']['image_id'],'source_root':'/source','backup_root':'/backup','candidate_sha':'candidate'}
  for key in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest'):request[key]='/'+key;request[key+'_sha256']='unused'
  pairs={'driver_path':'driver_sha256','provenance_path':'provenance_sha256','host_owner_path':'host_owner_sha256','source_manifest':'source_manifest_sha256','toolchain_manifest':'toolchain_manifest_sha256'}
  for key,hkey in pairs.items():request[hkey]='x'
  joined={'pid':935300,'starttime':'77972425','returncode':1,'direct_child_joined':True,'group_absent':True,'closed_streams':True,'error':None,'retirement_error':None};ready={'holder':{'boot_id':'boot'},'owner_join':joined,'owner_receipt':p['owner_receipt']};receipt=dict(p['target'],status='FAIL');process={'pid':935300,'starttime':'77972425'};contract={'caller_capture_root':str(root/'caller'),'static':{'request':{'path':'/staticrequest'}}}
  blobs={p['ready']['path']:ready,p['owner_receipt']['path']:receipt,p['join']['path']:joined,p['process']['path']:process,p['contract']['path']:contract,'/staticrequest':request}
  def pinned(row):return json.dumps(blobs[row['path']]).encode()
  e.read_bounded.side_effect=lambda path:path.read_bytes() if path in paths else b'{}'
  e.observe_identity.side_effect=lambda path:{'path':str(path),'sha256':'x','size':1}
  e.metadata_inventory.side_effect=lambda path:[{'path':str(path)}]
  protocol=mock.Mock();protocol.required_static_references.return_value=[];e.current230_contract.return_value=protocol
  item={'Id':p['target']['container_id'],'Name':'/'+p['target']['container_name'],'Image':p['target']['image_id'],'Config':{'Labels':{'mckernel.owner':p['target']['owner_nonce']}},'State':{'Status':'exited','Running':False,'Paused':False,'Restarting':False,'OOMKilled':False,'Dead':False,'Pid':0,'ExitCode':1,'Error':''}}
  def query(label):return json.dumps([item] if label=='inspect' else {'filesystems':[{'target':'/scratch','uuid':'uuid','fstype':'ext4','options':'rw,nodev,nosuid'}]}).encode()
  return p,e,pinned,query,protocol,item
 def test_actual_production_branch_shape_and_helpers(self):
  with tempfile.TemporaryDirectory() as d:
   p,e,pinned,q,protocol,item=self.fixture(Path(d))
   with mock.patch.object(a,'pinned',side_effect=pinned),mock.patch.object(a,'holder_check',return_value=True):obs=a.produce(p,e,q)
   self.assertEqual(set(obs),a.REQUIRED);self.assertEqual(len(obs['client_ledger']),7);self.assertEqual(obs['ownership_case'],'FAIL_COMMON_AND_SHARED');self.assertEqual(obs['container_inspect'],item);self.assertIsNone(obs['candidate_tree']);protocol.normal_owner_join_binding.assert_called_once();protocol.typed_source_binding.assert_called_once();e.metadata_inventory.assert_any_call(e.EVIDENCE)
 def test_actual_production_rejects_running(self):
  with tempfile.TemporaryDirectory() as d:
   p,e,pinned,q,protocol,item=self.fixture(Path(d));item['State']['Running']=True
   with mock.patch.object(a,'pinned',side_effect=pinned),mock.patch.object(a,'holder_check',return_value=True),self.assertRaisesRegex(ValueError,'terminalstate'):a.produce(p,e,q)
if __name__=='__main__':unittest.main(verbosity=2)
