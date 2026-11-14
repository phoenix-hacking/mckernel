"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Changed-only actual004f/acc55/853f source bindings. No observer/owner/cleanup/admission.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,stat,unittest
N=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt2-coherent-entry-preparation-source-1/genuine-postshared-binding-successor-source-1')
READY=N/'READY-ATTEMPT2-GENUINE004F-ACC55-NS853F.STATIC-NOT-EXECUTION.json'
READY_SHA='ec15aeca86185fb582c3dbe7d1f77ce1cfd56e55e7a1951ffc139c19e9daf5e2'
def ref(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return dict(path=str(p),sha256=h.hexdigest(),bytes=p.stat().st_size)
def module(row,name):
 assert ref(row['path'])==row;spec=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
assert ref(READY)['sha256']==READY_SHA
r=json.loads(READY.read_bytes());v=module(r['physical_validator'],'actual_new_shared_physical');f=module(r['fill'],'actual_final_attempt2_fill');caller=module(r['caller'],'actual_final_attempt2_caller');cleanup=module(r['cleanup'],'actual_final_attempt2_cleanup');protocol=cleanup.current230_contract();c=protocol.contract();cfg=json.loads(Path(r['config']['path']).read_bytes());ns=json.loads(Path(r['namespace_initialization']['path']).read_bytes());payload=json.loads(Path(r['payload']['path']).read_bytes());q=json.loads(Path(r['request']['path']).read_bytes());b=f.attempt2_binding()
class ChangedBindings(unittest.TestCase):
 def test_1_genuine_new_actual_schema_decision_consumed(self):
  self.assertTrue(v.validate(r['current_physical'],r['postreturn']));self.assertTrue(b.require_new_runtime_facts(cfg));self.assertEqual(caller.actual_config(Path(r['config']['path']),r['config']['sha256']),cfg)
 def test_2_actual853_namespace_identity_typed_producer_join(self):
  self.assertEqual(ns['identities'],c['namespace']);self.assertEqual(c['static']['namespace_preparation'],r['namespace_initialization']);self.assertEqual(c['current_physical'],r['current_physical']);self.assertEqual(c['current_postjoin'],r['postreturn']);self.assertEqual(cleanup.NAMESPACE_BINDING,{k:v for k,v in dict(path=c['namespace'][0]['path'],device=c['namespace'][0]['device'],inode=c['namespace'][0]['inode'],mode=stat.S_IFDIR|c['namespace'][0]['mode'],uid=1000,gid=1000).items() if k!='path'})
  s=c['source_identity'];n=c['namespace'][0];protocol._source_identity(c,dict(candidate_root=dict(path=s['path'],device=s['dev'],inode=s['inode'],mode=oct(s['mode']),uid=s['uid'],gid=s['gid']),namespace_binding=dict(device=n['device'],inode=n['inode'],mode=stat.S_IFDIR|n['mode'],uid=1000,gid=1000)))
 def test_3_real_changed_fill_current_source_origin_stays_truthful(self):
  actual,rows=f.fetched(Path(r['origin69']['path']),r['origin69']['sha256']);self.assertEqual(len(rows),69);ret=json.loads(Path(r['source_retention']['path']).read_bytes());self.assertTrue(b.validate_source_origin(q,ret));self.assertNotEqual(ret['full_owner_request'],r['request']);self.assertEqual(payload['argv'],cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(payload['argv'],cleanup.CURRENT230_OWNER_ARGV)
 def test_4_historical84_and_process_only_proofs_refused(self):
  A=N.parent.parent;old84=json.loads((A/'diagnostic-c252-refusal-successor-source-1/cleanup-successor-source-1/READY-CLEANUP-SUCCESSOR.SOURCE-ONLY.json').read_bytes())['current_physical']
  for wrong in [old84,r['postreturn']]:
   bad=copy.deepcopy(cfg);bad['physical']=wrong
   with self.assertRaises(RuntimeError):b.require_new_runtime_facts(bad)
 def test_5_wrong_namespace_receipt_refused(self):
  bad=copy.deepcopy(cfg);bad['namespace_initialization']=r['source_origin_binding']
  with self.assertRaisesRegex(RuntimeError,'exact actual853f namespace receipt'):b.require_new_runtime_facts(bad)
 def test_6_no_live_clock_or_holder_or_capture_created(self):
  self.assertIsNone(r['actual_holder']);self.assertIsNone(r['actual_live_clock']);self.assertIsNone(r['actual_admission_grants']);self.assertFalse(os.path.lexists(cfg['capture_root']));self.assertEqual(c['static']['metadata_fill'],r['fill']);self.assertEqual(c['static']['caller'],r['caller']);self.assertEqual(c['static']['caller_base_config'],r['config']);self.assertEqual(c['static']['observer'],r['census_observer'])
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ChangedBindings));print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),actual004f_acc55_853f_consumed=True,original69_9793_not_relabelled=True,no_owner_query_clock_holder_cleanup_or_admission=True),sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
