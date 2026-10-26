#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compose AST function definitions in memory; never execute observer/cleanup functions.
Temporary review/auth fixtures are synthetic and confer no runtime authority.
"""
import ast,copy,hashlib,importlib.util,json,os,subprocess,tempfile,time,types,unittest
from pathlib import Path
D=Path(__file__).resolve().parent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bridge=load('deadscan_bridge',D/'deadscan_runtime_bridge.SOURCE-ONLY.py')
census=load('census_bridge',bridge.FROZEN_INPUTS['census_bridge']['path'])
def engine():
 module=types.ModuleType('pure_source_engine');raw=bridge.authenticated(bridge.FROZEN_INPUTS['baseline']);tree=ast.parse(raw)
 release=json.loads(census.authenticated(census.FROZEN_INPUTS['old_release']))
 module.__dict__.update(__file__=bridge.FROZEN_INPUTS['baseline']['path'],os=os,time=time,json=json,hashlib=hashlib,subprocess=subprocess,Path=Path,RELEASE=release,BOOT_ID=release['observation']['boot_id'],OWNER_PID=release['observation']['target']['owner_pid'],WAITER_PIDS=tuple(row['pid'] for row in release['observation']['client_ledger']))
 names=set(bridge.BASELINE_FUNCTIONS)|set(census.BASELINE_FUNCTIONS)
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.ClassDef) and n.name=='Refusal' or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'PUBLISHED_SCRIPT','PROC_CODE'} for t in n.targets)]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),bridge.FROZEN_INPUTS['baseline']['path'],'exec',dont_inherit=True,optimize=0),module.__dict__)
 census.install_census_delta(module,census.expected_authorization())
 return module
class Installer(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);p=Path(self.tmp.name)/'SYNTHETIC-REVIEW-NOT-AUTHORITY.json'
  p.write_text(json.dumps(dict(decision='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY',reviewer='/root/deadscan_review',installer_sha256=bridge.reference(bridge.__file__)['sha256'],patch_sha256=bridge.FROZEN_INPUTS['patch']['sha256'],synthetic_fixture_only=True)))
  self.authorization=bridge.expected_authorization(bridge.reference(p));self.engine=engine()
 def test_actual_closed_nodes_compose_after_real_c9af_source_delta(self):
  before=dict(self.engine.__dict__);result=bridge.install_deadscan_delta(self.engine,self.authorization)
  self.assertEqual(set(result['changed_slots']),set(bridge.REPLACE));self.assertEqual(set(result['added_slots']),set(bridge.ADD))
  for name,value in before.items():
   if name not in bridge.REPLACE:self.assertIs(self.engine.__dict__[name],value,name)
  self.assertIs(self.engine._DEADSCAN_DELTA_MANIFEST,result)
 def assert_wrong_source_origin_refused(self,name,reason):
  function=self.engine.__dict__[name];original_code=function.__code__
  altered_code=original_code.replace(co_filename='<wrong-source-origin>')
  self.assertEqual(altered_code,original_code) # Code equality alone omits source filename.
  self.assertNotEqual(altered_code.co_filename,original_code.co_filename)
  function.__code__=altered_code;before=dict(self.engine.__dict__)
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,reason):
   bridge.install_deadscan_delta(self.engine,self.authorization)
  self.assertEqual(self.engine.__dict__,before)
  self.assertIs(function.__code__,altered_code)
  self.assertNotIn(bridge.MANIFEST_SLOT,self.engine.__dict__)
 def test_root_command_wrong_source_origin_refused(self):
  self.assert_wrong_source_origin_refused('root_command','census-three-slots-unchanged')
 def test_validate_process_report_wrong_source_origin_refused(self):
  self.assert_wrong_source_origin_refused('validate_process_report','census-three-slots-unchanged')
 def test_same_ofd_read_wrong_source_origin_refused(self):
  self.assert_wrong_source_origin_refused('same_ofd_read','unmodified-baseline-function:same_ofd_read')
 def test_former_reviewer_identity_refused_without_mutation(self):
  review_path=Path(self.authorization['source_review']['path'])
  review=json.loads(review_path.read_text());review['reviewer']='/root/census_lifecycle_review'
  review_path.write_text(json.dumps(review))
  auth=bridge.expected_authorization(bridge.reference(review_path));before=dict(self.engine.__dict__)
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'independent-exact-source-review'):
   bridge.install_deadscan_delta(self.engine,auth)
  self.assertEqual(self.engine.__dict__,before)
 def test_stale_root_authorization_refused_without_mutation(self):
  auth=dict(self.authorization);auth['patch_sha256']='0'*64;before=dict(self.engine.__dict__)
  with self.assertRaises(bridge.DeadscanBridgeRefusal):bridge.install_deadscan_delta(self.engine,auth)
  self.assertEqual(self.engine.__dict__,before)
 def test_missing_census_delta_refused(self):
  self.engine.__dict__.pop('_PROCESS_CENSUS_DELTA_MANIFEST')
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'census-composition'):bridge.install_deadscan_delta(self.engine,self.authorization)
 def test_census_slot_mutation_refused(self):
  self.engine.PROC_CODE='changed'
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'three-slots'):bridge.install_deadscan_delta(self.engine,self.authorization)
 def test_file_identity_spoof_refused(self):
  self.engine.__file__='/synthetic-renamed.py'
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'file-identity'):bridge.install_deadscan_delta(self.engine,self.authorization)
 def test_baseline_deadcaller_modified_refused(self):
  exec('def dead_caller_absent(): return None',self.engine.__dict__)
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'baseline-function'):bridge.install_deadscan_delta(self.engine,self.authorization)
 def test_existing_helper_collision_refused(self):
  self.engine.dead_caller_stat_fields=object()
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'collision'):bridge.install_deadscan_delta(self.engine,self.authorization)
 def test_double_install_refused(self):
  bridge.install_deadscan_delta(self.engine,self.authorization)
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'already-composed'):bridge.install_deadscan_delta(self.engine,self.authorization)
 def test_original_release_changed_refused(self):
  self.engine.RELEASE=copy.deepcopy(self.engine.RELEASE);self.engine.RELEASE['synthetic_changed']=True
  with self.assertRaisesRegex(bridge.DeadscanBridgeRefusal,'original-release'):bridge.install_deadscan_delta(self.engine,self.authorization)
if __name__=='__main__':unittest.main(verbosity=2)
