"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine compiled source composition only; no observer/acquisition/root calls.
"""
import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bridge=load('confirmed_exit_installer',D/'lifecycle_runtime_bridge.SOURCE-ONLY.py')
old=load('prior_final_installer_tests',Path(bridge.INPUTS['prior_installer']['path']).parent/'test_deadscan_installer.PURE.py')
class Installer(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);tmp=Path(self.tmp.name)
  prior_review=tmp/'SYNTHETIC-PRIOR-REVIEW.json';prior_review.write_text(json.dumps(dict(decision='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY',reviewer='/root/deadscan_review',installer_sha256=old.bridge.reference(old.bridge.__file__)['sha256'],patch_sha256=old.bridge.FROZEN_INPUTS['patch']['sha256'],synthetic_fixture_only=True)))
  self.engine=old.engine();old.bridge.install_deadscan_delta(self.engine,old.bridge.expected_authorization(old.bridge.reference(prior_review)))
  review=tmp/'SYNTHETIC-CURRENT-REVIEW.json';review.write_text(json.dumps(dict(decision='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY',reviewer='independent-private-fixture-only',installer_sha256=bridge.reference(bridge.__file__)['sha256'],patch_sha256=bridge.INPUTS['patch']['sha256'],synthetic_fixture_only=True)))
  self.auth=bridge.expected_authorization(bridge.reference(review))
 def refused_unchanged(self,reason):
  before=dict(self.engine.__dict__)
  with self.assertRaisesRegex(bridge.LifecycleBridgeRefusal,reason):bridge.install_confirmed_exit_delta(self.engine,self.auth)
  self.assertEqual(self.engine.__dict__,before)
 def test_genuine_prior_composition_changes_only_two_slots_adds_one(self):
  before=dict(self.engine.__dict__);result=bridge.install_confirmed_exit_delta(self.engine,self.auth)
  self.assertEqual(result['changed_slots'],list(bridge.REPLACE));self.assertEqual(result['added_slots'],list(bridge.ADD+bridge.STATE_ADD))
  for name,value in before.items():
   if name not in bridge.REPLACE:self.assertIs(self.engine.__dict__[name],value,name)
  self.assertIs(self.engine._CONFIRMED_EXIT_DELTA_MANIFEST,result)
  self.assertEqual(self.engine._DEAD_CALLER_RETAINED_HISTORY_SEED['source'],bridge.INPUTS['history_seed'])
  self.assertEqual(result['prior_compact_sequences'],list(range(1,13)))
  seed=self.engine._DEAD_CALLER_RETAINED_HISTORY_SEED
  for pid in (1195287,1195372,1195602):
   self.assertIn(pid,seed['observed_pids']);self.assertNotIn(str(pid),seed['observed_births'])
  for name in bridge.REPLACE+bridge.ADD:
   self.assertIs(self.engine.__dict__[name].__globals__,self.engine.__dict__)
   self.assertEqual(self.engine.__dict__[name].__code__.co_filename,bridge.INPUTS['patch']['path'])
 def test_missing_prior_delta_refused(self):
  del self.engine._DEADSCAN_DELTA_MANIFEST;self.refused_unchanged('prior-deadscan')
 def test_prior_manifest_wrong_installer_refused(self):
  self.engine._DEADSCAN_DELTA_MANIFEST=copy.deepcopy(self.engine._DEADSCAN_DELTA_MANIFEST);self.engine._DEADSCAN_DELTA_MANIFEST['installer']['sha256']='0'*64;self.refused_unchanged('prior-deadscan')
 def test_prior_census_changed_refused(self):
  self.engine.PROC_CODE='altered';self.refused_unchanged('census-three-slots')
 def test_changed_existing_observer_refused(self):
  exec('def dead_caller_absent(): return None',self.engine.__dict__);self.refused_unchanged('unmodified-prior-function:dead_caller_absent')
 def test_equal_code_wrong_source_filename_refused(self):
  fn=self.engine.dead_caller_absent;fn.__code__=fn.__code__.replace(co_filename='<wrong-origin>');self.refused_unchanged('unmodified-prior-function:dead_caller_absent')
 def test_changed_old_validator_refused(self):
  exec('def validate_dead_caller_snapshots(*args): return True',self.engine.__dict__);self.refused_unchanged('unmodified-prior-function:validate_dead_caller_snapshots')
 def test_new_helper_collision_refused(self):
  self.engine.dead_caller_confirm_exited=object();self.refused_unchanged('helper-slot-collision')
 def test_stale_authorization_refused(self):
  self.auth['patch_sha256']='0'*64;self.refused_unchanged('exact-root-source')
 def test_root_cannot_be_own_independent_review(self):
  review=Path(self.auth['source_review']['path']);value=json.loads(review.read_text());value['reviewer']='/root';review.write_text(json.dumps(value));self.auth=bridge.expected_authorization(bridge.reference(review));self.refused_unchanged('independent-exact-current')
 def test_changed_release_refused(self):
  self.engine.RELEASE=copy.deepcopy(self.engine.RELEASE);self.engine.RELEASE['changed']=True;self.refused_unchanged('original-release')
 def test_double_install_refused(self):
  bridge.install_confirmed_exit_delta(self.engine,self.auth);self.refused_unchanged('already-confirmed-exit')
if __name__=='__main__':unittest.main(verbosity=2)
