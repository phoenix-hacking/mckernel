"""Functional OS only; no security testing. Expired recorded metadata controls, never live authority."""
import contextlib,copy,hashlib,importlib.util,json,os,subprocess,tempfile,time,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('readonly_actual_fields',HERE/'collect_actual_fields.READONLY.NOT-AUTHORITY.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.guards=contextlib.ExitStack()
  for obj,name in [(subprocess,'Popen'),(subprocess,'run'),(os,'system'),(os,'kill')]:cls.guards.enter_context(mock.patch.object(obj,name,side_effect=AssertionError('no transport/action '+name)))
  cls.addClassCleanup(cls.guards.close);cls.expected=m.decode((HERE/'EXPIRED-Z-EXPECTED.FIXTURE-NO-AUTHORITY.json').read_bytes());cls.cohort=m.document(cls.expected['cohort']);cls.bundle=m.load_bundle(cls.expected,cls.cohort)
 def test_expired_recorded_metadata_only_core(self):
  result=m.check_recorded(self.expected,self.bundle);self.assertLess(result['expires_at'],time.time());self.assertEqual(result['canonical_sha256'],'5ad5a3d14969ce110deff83f3e3793cef16bd333b4e950536745c25b7c9e9d13')
 def test_wrong_source_binding_after_valid_canonical_rejected(self):
  bad=copy.deepcopy(self.bundle);bad['payload']['source']['owner']['sha256']='0'*64;bad['ready']['canonical_payload_sha256']=hashlib.sha256(bad['canonical'](bad['payload'])).hexdigest()
  with self.assertRaisesRegex(RuntimeError,'source roles'):m.check_recorded(self.expected,bad)
 def test_wrong_census_request_rejected(self):
  bad=copy.deepcopy(self.bundle);bad['census']['request']['sha256']='0'*64
  with self.assertRaisesRegex(RuntimeError,'census request'):m.check_recorded(self.expected,bad)
 def test_namespace_presence_after_valid_canonical_rejected(self):
  bad=copy.deepcopy(self.bundle);bad['payload']['namespace']['rows'][3]['exists']=True;bad['ready']['canonical_payload_sha256']=hashlib.sha256(bad['canonical'](bad['payload'])).hexdigest()
  with self.assertRaisesRegex(RuntimeError,'remaining paths absent'):m.check_recorded(self.expected,bad)
 def test_mutated_raw_reference_rejected(self):
  with tempfile.TemporaryDirectory() as temporary:
   p=Path(temporary)/'raw';p.write_bytes(b'original');row=m.reference(p);p.write_bytes(b'mutated!')
   with self.assertRaisesRegex(RuntimeError,'exact reference bytes'):m.auth(row)
 def test_expired_live_check_fails_before_proc(self):
  recorded=m.check_recorded(self.expected,self.bundle)
  with mock.patch.object(m,'read_proc',side_effect=AssertionError('no live proc query')) as proc:
   with self.assertRaisesRegex(RuntimeError,'expired before live'):m.check_live(self.bundle,recorded)
   proc.assert_not_called()
 def test_expired_fixture_cannot_enter_live_collector(self):
  p=HERE/'EXPIRED-Z-EXPECTED.FIXTURE-NO-AUTHORITY.json'
  with self.assertRaisesRegex(RuntimeError,'preclock expected cohort'):m.collect(str(p),hashlib.sha256(p.read_bytes()).hexdigest())
if __name__=='__main__':unittest.main(verbosity=2)
