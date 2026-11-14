"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual preserved first-V3 observation replay through unchanged batch classifier. No native acceptance.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest
D=Path(__file__).resolve().parent
B=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2')
H=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-readiness-runtime-failure-2/coherent-successor-preparation-1')
ORIGINAL=Path('/home/holden/mckernel-work/host-preparation/p-m05-fixed-profile-batch-adaptation-20261023-1')
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('original_batch',ORIGINAL/'native_diagnostic_batch.py');HOOK=load('original_hooks',ORIGINAL/'production-adapter-1/production_hooks.py')
class ConsumerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.profile=json.loads((D/'FIXED-CURRENT-TEN-CYCLE-PROFILE.PENDING.json').read_text());nd=load('current_nd',H/'runtime-source-successor-1/native_diagnostic.py');cls.profile['_manifest']=nd.load_manifest(cls.profile['manifest']['path'])
  cls.inner=json.loads((B/'m05-readiness-runtime-failure-2/coherent-successor-preparation-1/next-native-preparation-1/actual-post-physical-1/authenticated-owner-export/inner-result.json').read_text());cls.status=json.loads((H/'next-native-preparation-1/actual-M05-HOST-owner-capture-1/status.json').read_text());assert cls.status['returncode']==0
  cls.execution=dict(returncode=cls.status['returncode'],owner_status=cls.inner['status'],observation=cls.inner['observation'],kernel_before=HOOK.before_snapshot(cls.inner['observation']['serial']))
 def test_real_batch_semantics_on_authentic_first_V3_observation(self):
  result=M.evaluate_semantics(self.profile,self.execution);self.assertTrue(result['qualifies_first_restore_reboot']);self.assertFalse(result['automatic_native_acceptance']);self.assertFalse(result['automatic_quota_credit']);(D/'OBSERVED-FIRST-V3-BATCH-SEMANTICS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 def test_wrong_before_snapshot_does_not_qualify(self):
  bad=dict(self.execution,kernel_before=b'wrong retained snapshot');result=M.evaluate_semantics(self.profile,bad);self.assertFalse(result['qualifies_first_restore_reboot']);self.assertIn('qualification_error',result)
 def test_wrong_transport_does_not_qualify(self):
  with self.assertRaises(ValueError):M.evaluate_semantics(self.profile,dict(self.execution,returncode=37))
 def test_exact_ten_nonce_parent_commands_and_unknown_approval_refusal(self):
  spec=json.loads((D/'EXACT-TEN-CASE-SPEC.PENDING.json').read_text());self.assertEqual(len(spec['cases']),10);self.assertEqual(len({r['attempt_parent']for r in spec['cases']}),10);self.assertEqual(len({r['nonce']for r in spec['cases']}),10)
  for r in spec['cases']:
   self.assertEqual(r['command'][r['command'].index('--owner-sha256')+1],self.profile['owner_sha256']);self.assertLessEqual(len((r['attempt_parent']+'/attempt-'+r['nonce']+'/qmp.sock').encode()),107);self.assertIsNone(r['release']['sha256'])
  with self.assertRaises(ValueError):M.validate_spec(spec)
if __name__=='__main__':unittest.main(verbosity=2)
