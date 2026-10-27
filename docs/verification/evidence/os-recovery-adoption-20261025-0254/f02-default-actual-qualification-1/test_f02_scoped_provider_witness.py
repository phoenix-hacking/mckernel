"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact-profile successor regressions; actual accepted clone gate body unchanged.
"""
import copy,hashlib,importlib.util,json,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('accepted_scoped_clone',D/'profile_clone_witness.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
proof=json.loads((D/'CLONE-FINAL-POINTER-AND-WARNINGS.json').read_text());text=(D/'production-rust-undefined.nm').read_text()
FOUR={'idle_halt','allow_oversubscribe','time_sharing','process_idle_callbacks'}
original=set(gate.EXPECTED_PROVIDERS);gate.EXPECTED_PROVIDERS=sorted(original-FOUR);gate.PROOF_SHA=hashlib.sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class ExactF02ProfileWitness(unittest.TestCase):
 def test_actual_exact_four_provider_delta_and_proof(self):
  self.assertEqual(original-set(gate.EXPECTED_PROVIDERS),FOUR);self.assertTrue(gate.validate(text,proof)['status'].startswith('PASS'))
 def test_extra_provider_never_waived(self):
  with self.assertRaisesRegex(RuntimeError,'all other'):gate.validate(text+'                 U unexpected_F02_provider\n',proof)
 def test_each_moved_owner_as_U_refused(self):
  for name in sorted(FOUR):
   with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'all other'):gate.validate(text+'                 U '+name+'\n',proof)
 def test_missing_retained_provider_refused(self):
  changed='\n'.join(text.splitlines()[1:])+'\n'
  with self.assertRaisesRegex(RuntimeError,'all other'):gate.validate(changed,proof)
 def test_obsolete_clone_U_and_core_panic_refused(self):
  for name in ['clone_thread','core::panicking::panic_bounds_check','core::result::unwrap_failed']:
   with self.subTest(name=name),self.assertRaises(RuntimeError):gate.validate(text+'                 U '+name+'\n',proof)
 def test_mutated_fresh_actual_clone_proof_refused(self):
  changed=copy.deepcopy(proof);changed['final_function_exact_object_code_with_only_two_R64_patches']=False
  with self.assertRaisesRegex(RuntimeError,'proof mismatch'):gate.validate(text,changed)
if __name__=='__main__':unittest.main(verbosity=2)
