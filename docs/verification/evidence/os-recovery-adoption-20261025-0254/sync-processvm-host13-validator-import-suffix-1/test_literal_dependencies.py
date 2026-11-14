"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Test the exact runpy/import interface without executing any artifact gate.
"""
from pathlib import Path
import copy,importlib.util,json,runpy,sys,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('corrected_readonly_driver',D/'qualify_produced_cohort.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manifest=json.loads((D/'VALIDATOR-TEMPLATE-SOURCES.json').read_text())
class LiteralDependencies(unittest.TestCase):
 def test_actual_literal_runpy_and_both_accepted_dependencies(self):
  with patch('subprocess.run',side_effect=AssertionError('no runtime/observer call permitted')) as calls:
   helpers=m.bind_validator_dependencies(manifest)
   # The real interpreter resolves this import exactly as runpy artifact gates do.
   probe=runpy.run_path(str(D/'literal_import_probe.py'),run_name='__main__')
   self.assertEqual(Path(probe['profile_clone_witness'].__file__),Path(helpers['profile_clone_witness.py']['path']))
   spec=importlib.util.spec_from_file_location('actual_cohort_narrow_alias',Path(helpers['narrow_f02_alias_identity.py']['path']));gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
   self.assertTrue(callable(gate.validate));self.assertEqual(len(gate.TARGETS),10);calls.assert_not_called()
 def test_changed_dependency_hash_rejected(self):
  changed=copy.deepcopy(manifest);changed['unchanged_helpers']['profile_clone_witness.py']['sha256']='0'*64
  with self.assertRaisesRegex(AssertionError,'dependency changed'):m.bind_validator_dependencies(changed)
 def test_missing_dependency_rejected(self):
  changed=copy.deepcopy(manifest);changed['unchanged_helpers'].pop('narrow_f02_alias_identity.py')
  with self.assertRaises(AssertionError):m.bind_validator_dependencies(changed)
 def test_original_proof_files_are_not_copied_into_fresh_output(self):
  self.assertFalse((D/'actual-qualification-1').exists());self.assertFalse((D/'profile_clone_witness.py').exists());self.assertFalse((D/'narrow_f02_alias_identity.py').exists())
if __name__=='__main__':unittest.main(verbosity=2)
