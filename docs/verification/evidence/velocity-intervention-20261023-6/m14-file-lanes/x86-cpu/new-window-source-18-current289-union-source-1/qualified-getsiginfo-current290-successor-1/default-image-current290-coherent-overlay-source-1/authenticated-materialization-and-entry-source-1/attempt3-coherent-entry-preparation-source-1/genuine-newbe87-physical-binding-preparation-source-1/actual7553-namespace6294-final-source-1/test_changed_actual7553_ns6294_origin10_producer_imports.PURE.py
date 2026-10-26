"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Changed actual7553/6294 and receipt-candidate10field producer/import bindings only.
No query, namespace init, owner, cleanup, holder, clock or admission execution.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,stat,unittest
Z=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1');READY=Z/'READY-ATTEMPT3-ACTUAL7553-NS6294-FINAL-STATIC.NOT-EXECUTION.json';READY_SHA='c6da48e1486bf7826b0012568188ae57e89a9d3f821adf1e9dd1805b4b567239'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def module(row,name):
 assert ref(row['path'])==row;s=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
assert ref(READY)['sha256']==READY_SHA
r=json.loads(READY.read_bytes());v=module(r['physical_validator'],'actual7553_physical');f=module(r['fill'],'final3_fill');caller=module(r['caller'],'final3_caller');cleanup=module(r['cleanup'],'final3_cleanup');protocol=cleanup.current230_contract();c=protocol.contract();cfg=json.loads(Path(r['config']['path']).read_bytes());ns=json.loads(Path(r['namespace_initialization']['path']).read_bytes());payload=json.loads(Path(r['payload']['path']).read_bytes());q=json.loads(Path(r['request']['path']).read_bytes());b=f.attempt2_binding()
def observation():
 s=c['source_identity'];n=c['namespace'][0];return dict(candidate_root=dict(path=s['path'],device=s['dev'],inode=s['inode'],mode=oct(s['mode']),uid=s['uid'],gid=s['gid']),namespace_binding=dict(device=n['device'],inode=n['inode'],mode=stat.S_IFDIR|n['mode'],uid=1000,gid=1000))
class ChangedFinal3(unittest.TestCase):
 def test_1_actual7553_schema_decision_and_actual6294(self):
  self.assertTrue(v.validate(r['current_physical'],r['postreturn']));self.assertTrue(b.require_new_runtime_facts(cfg));self.assertEqual(caller.actual_config(Path(r['config']['path']),r['config']['sha256']),cfg)
 def test_2_actual_namespace3_typed_producer_identity(self):
  self.assertEqual(ns['identities'],c['namespace']);self.assertEqual([x['inode'] for x in c['namespace']],[59653441,59653442,59653443]);self.assertEqual(c['static']['namespace_preparation'],r['namespace_initialization']);protocol._source_identity(c,observation());self.assertEqual(cleanup.NAMESPACE_BINDING,observation()['namespace_binding'])
 def test_3_actual_fill_origin69_and_truthful10_field_relation(self):
  pub,rows=f.fetched(Path(r['origin69']['path']),r['origin69']['sha256']);self.assertEqual(len(rows),69);ret=json.loads(Path(r['source_retention']['path']).read_bytes());self.assertTrue(b.validate_source_origin(q,ret));self.assertNotEqual(ret['full_owner_request'],r['request']);data=b.data();origin=json.loads(Path(data['published_origin_request']['path']).read_bytes());self.assertEqual(set(q)-set(origin),{'image_receipt_candidate_sha'});self.assertEqual(len([k for k in q if q[k]!=origin.get(k)]),10);self.assertEqual(q['image_receipt_candidate_sha'],'942c927b1ec93cc31284ff498455909d9bb2d0fc');self.assertEqual(q['candidate_sha'],origin['candidate_sha'])
 def test_4_actual_prepare_template_paths_and_argv_coherent(self):
  # Exercise actual effect-free producer loader at exact filenames consumed by prepare.
  self.assertEqual(f.load(f.D/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json'),payload);self.assertEqual(f.load(f.D/'COMPACT-C252-CENSUS-REQUEST.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json')['full_owner_request'],r['request']);self.assertTrue(all((f.D/name).is_file() for name in f.SOURCES));self.assertEqual(payload['argv'],cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(payload['argv'],cleanup.CURRENT230_OWNER_ARGV);self.assertEqual(Path(cfg['commands']['five_observations']['source']['path']).name,'capture_readonly_admission.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.py')
 def test_5_old004f_or_process1937_cannot_clear_newentry(self):
  E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
  for p in [E/'CURRENT290-SHARED-ARCHIVAL-INDEPENDENT-CURRENT-PHYSICAL-ACCEPTANCE.json',E/'CURRENT290-PROCESS903-INDEPENDENT-RETIREMENT-ACCEPTANCE.json']:
   bad=copy.deepcopy(cfg);bad['physical']=ref(p)
   with self.assertRaises(RuntimeError):b.require_new_runtime_facts(bad)
 def test_6_wrong_namespace_receipt_and_inode_refused(self):
  bad=copy.deepcopy(cfg);bad['namespace_initialization']=r['source_origin_binding']
  with self.assertRaises(RuntimeError):b.require_new_runtime_facts(bad)
  bad=observation();bad['namespace_binding']['inode']+=1
  with self.assertRaises(RuntimeError):protocol._source_identity(c,bad)
 def test_7_added_receipt_candidate_not_coerced_or_dropped(self):
  ret=json.loads(Path(r['source_retention']['path']).read_bytes())
  for op in ['drop','wrong']:
   bad=copy.deepcopy(q)
   if op=='drop':bad.pop('image_receipt_candidate_sha')
   else:bad['image_receipt_candidate_sha']=q['candidate_sha']
   with self.assertRaises(RuntimeError):b.validate_source_origin(bad,ret)
 def test_8_final_imports_static_bindings_no_live_artifacts(self):
  self.assertEqual(c['static']['metadata_fill'],r['fill']);self.assertEqual(c['static']['caller'],r['caller']);self.assertEqual(c['static']['caller_base_config'],r['config']);self.assertEqual(c['static']['observer'],r['census_observer']);self.assertEqual(c['current_physical'],r['current_physical']);self.assertEqual(c['current_postjoin'],r['postreturn']);self.assertEqual(cleanup.PUBLISHED_SCRIPT,str(Path(r['cleanup']['path']).relative_to('/home/holden/mckernel')))
  for k in ['actual_holder','actual_live_clock','actual_admission_grants']:self.assertIsNone(r[k])
  self.assertFalse(os.path.lexists(cfg['capture_root']));self.assertFalse(os.path.lexists(Z/'actual-readonly-admission-capture-1'))
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ChangedFinal3));print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),actual7553_6294_consumed=True,original69_9793_586_truthful=True,no_runtime_query_clock_owner_namespace_cleanup=True),sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
