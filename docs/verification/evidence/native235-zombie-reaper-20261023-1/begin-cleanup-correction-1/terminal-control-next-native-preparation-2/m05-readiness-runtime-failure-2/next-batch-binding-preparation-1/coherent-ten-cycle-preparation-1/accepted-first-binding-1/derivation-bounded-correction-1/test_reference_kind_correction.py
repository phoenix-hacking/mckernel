"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,importlib.util,json,tempfile,unittest
D=Path(__file__).resolve().parent
PROFILE=D.parent/'FIXED-CURRENT-TEN-CYCLE-PROFILE.FIRST-ACCEPTED.json'
s=importlib.util.spec_from_file_location('corrected_actual_deriver',D/'derive_fixed_batch.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class ReferenceKindTests(unittest.TestCase):
 def test_hash_bound_python_roles_decode_as_source(self):
  profile=json.loads(PROFILE.read_text())
  for name in ('resource_decoder','strict_consumer'):
   ref=profile[name];self.assertEqual(M.bound(ref,kind='python'),Path(ref['path']).read_bytes())
 def test_nonJSON_refused_for_JSON_role(self):
  profile=json.loads(PROFILE.read_text())
  for name in ('resource_decoder','strict_consumer'):
   with self.assertRaises(json.JSONDecodeError):M.bound(profile[name],kind='json')
 def test_hash_mutation_and_unknown_role_refused(self):
  with tempfile.TemporaryDirectory(dir=D,prefix='hash-negative-')as tmp:
   p=Path(tmp)/'source.py';original=b'x = 1\n';p.write_bytes(b'x = 2\n');r=dict(path=str(p),sha256=hashlib.sha256(original).hexdigest())
   for kind in('json','python'):
    with self.assertRaisesRegex(ValueError,'exact reference drift'):M.bound(r,kind=kind)
   with self.assertRaisesRegex(ValueError,'reference role'):M.bound(r,kind='auto')
 def test_real_full_profile_derivation_and_unchanged_generated_bodies(self):
  M.main(['--profile',str(PROFILE)]);out=D/'reviewed-ten-cycle-successor';result=json.loads((out/'DERIVATION.json').read_text());self.assertEqual(result['status'],'FIXED_CONSTANTS_DERIVED_FROM_ACTUAL_FIRST_REVIEW_NOT_EXECUTION_RELEASE');self.assertEqual(result['profile_sha256'],hashlib.sha256(PROFILE.read_bytes()).hexdigest())
  source=(M.OLD/'native_diagnostic_batch.py').read_text();generated=(out/'native_diagnostic_batch.py').read_text();old=ast.parse(source);new=ast.parse(generated);changes=[]
  for before,after in zip(old.body,new.body):
   if ast.dump(before,include_attributes=False)!=ast.dump(after,include_attributes=False):
    self.assertIsInstance(before,ast.Assign);changes.append(before.targets[0].id)
  self.assertEqual(set(changes),{'PROFILE_ID','MANIFEST_SHA','AUTHORITY_SHA'})
  for name,ref in [('production_hooks.py',M.OLD/'production-adapter-1/production_hooks.py'),('export_closed_owner.py',M.OLD/'production-adapter-1/export_closed_owner.py')]:self.assertEqual((out/name).read_bytes(),ref.read_bytes())
  self.assertEqual((out/'FIXED-CURRENT-PROFILE.json').read_bytes(),PROFILE.read_bytes())
if __name__=='__main__':unittest.main(verbosity=2)
