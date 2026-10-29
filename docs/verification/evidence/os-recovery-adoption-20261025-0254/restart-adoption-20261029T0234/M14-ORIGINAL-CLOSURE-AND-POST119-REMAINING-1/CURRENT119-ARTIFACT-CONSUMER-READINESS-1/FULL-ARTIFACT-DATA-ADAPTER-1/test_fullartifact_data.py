"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure metadata and exact-source fixtures; no actual artifact access.
"""
from pathlib import Path
import copy,json,unittest
from unittest import mock
import create_fullartifact_data as m

class Adapter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.template=m.read(m.D/'FULL-ARTIFACT-INPUT.TEMPLATE.NOT-AUTHORITY.json')
 def test_source_only_input_and_compiled_files_never_opened(self):
  original=Path.read_bytes
  def bounded(path):
   self.assertNotIn(path.suffix,('.o','.img','.a','.so','.ko'));return original(path)
  with mock.patch.object(Path,'read_bytes',bounded):
   self.assertEqual(m.build(),self.template)
  s=self.template['source_facts'];self.assertEqual((len(s['canonical_paths']),s['source_files'],s['Rust_files']),(18,133,122));self.assertEqual(sum(not r['replace']for r in s['link_objects']),8)
 def test_stale116_bindings_rejected(self):
  for mutate in [lambda d:d['source_facts'].__setitem__('source_files',121),lambda d:d['source_facts'].__setitem__('Rust_files',112),lambda d:d['source_facts'].__setitem__('source_adoption',{'path':'TEST_ONLY_OLD116','bytes':1,'sha256':'0'*64}),lambda d:d['source_facts']['link_objects'].pop()]:
   d=copy.deepcopy(self.template);mutate(d)
   with self.assertRaises(AssertionError):m.validate_source_data(d)
 def test_projected_or_claimed_artifact_facts_rejected(self):
  for field in ['actual_linked_provider_count','actual_linked_storage_count','actual_selected_C_function_count']:
   d=copy.deepcopy(self.template);d['source_facts'][field]=47
   with self.assertRaises(AssertionError):m.validate_source_data(d)
  d=copy.deepcopy(self.template);d['actual_qualification_results']['original389_identity_multiset']='PASS_FROM_SOURCE'
  with self.assertRaises(AssertionError):m.validate_source_data(d)
 def test_all_original_functions_and_counter_bound_exactly(self):
  names=[r['name']for r in self.template['validator_nodes']];self.assertEqual(len(names),len(set(names)));self.assertIn('registry',names);self.assertIn('compare',names);self.assertIn('relocated_function',names);self.assertIn('warnings',names)
  for row in self.template['validator_nodes']:self.assertEqual(m.unit(row['source'],row['name']),row)
  d=copy.deepcopy(self.template);d['validator_nodes'][0]['AST_sha256']='0'*64
  with self.assertRaises(AssertionError):m.validate_source_data(d)
  d=copy.deepcopy(self.template);d['original389']['sha256']='0'*64
  with self.assertRaises(AssertionError):m.validate_source_data(d)
 def test_weekly_only_and_all_actual_slots_open(self):
  self.assertEqual(self.template['weekly_only'],{'allowance':'codex','window_minutes':10080,'reset_upper_bound_epoch':1793774133,'stop_used_percent':100,'prepaid_fallback':False,'runtime_grant':None})
  self.assertTrue(all(v is None for v in self.template['actual_postbuild_inputs'].values()));self.assertTrue(all(v is None for v in self.template['actual_qualification_results'].values()))
  self.assertFalse(self.template['direct_old_review_script_execution_allowed'])
if __name__=='__main__':unittest.main()
