import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/'docs/verification/evidence/native-exact-candidate-scratch21-preparation-execution-wrapper-20261001.py'
spec=importlib.util.spec_from_file_location('wrapper21',PATH)
p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

class Wrapper21(unittest.TestCase):
 def test_fresh_exact_inputs(self):
  self.assertEqual(p.CONTROLLER,'fc6b5a7442078ebec4168ae7b43f038973257f78')
  self.assertEqual(len(p.DESTINATIONS),10)
  self.assertTrue(all(not x.exists() and not x.is_symlink() for x in p.DESTINATIONS))
 def test_exact_single_call_and_early_owner_check(self):
  git_values=[(p.CONTROLLER+'\n').encode()]+[(value+'\n').encode() for value in p.ROOT_HEADS.values()]
  with mock.patch.object(p,'digest',side_effect=lambda path:{p.HELPER:p.HELPER_SHA256,p.TEST:p.TEST_SHA256}[path]), \
      mock.patch.object(p.helper._IMPL,'git',side_effect=git_values), \
      mock.patch.object(p.helper,'validate_owner_exclusion') as exclusion, \
      mock.patch.object(p.helper._IMPL,'prepare',return_value={'status':'PASS_PREPARE_ONLY'}) as prepare, \
      mock.patch.object(p.shutil,'disk_usage',return_value=type('U',(),{'free':64<<30})()):
   self.assertEqual(p.admit_and_prepare(),{'status':'PASS_PREPARE_ONLY'})
  exclusion.assert_called_once_with(p.ROOT)
  prepare.assert_called_once_with(
   p.ROOT,p.SCRATCH15,p.SCRATCH,execute=True,target=p.helper.TARGET,
   old=p.helper.BASELINE,baseline=p.helper.BASELINE,source_base=p.helper.SOURCE_BASE,
   expected_delta=p.helper.EXACT_DELTA,expected_initial_links=5,scratch16=p.SCRATCH16,
   previous_candidate=p.SCRATCH18,additional_shared_roots=(p.SCRATCH17,p.SCRATCH20),
   exclusion=p.helper.ACTIVE_EXCLUSION)

if __name__=='__main__': unittest.main()
