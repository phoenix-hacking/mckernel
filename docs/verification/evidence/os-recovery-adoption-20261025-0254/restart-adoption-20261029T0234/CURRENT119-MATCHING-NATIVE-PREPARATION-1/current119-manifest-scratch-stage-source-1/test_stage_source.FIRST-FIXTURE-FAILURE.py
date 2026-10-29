"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/JSON-only stage applicability tests; never calls main, owner or scratch IO.
"""
from pathlib import Path
import ast,copy,hashlib,json,unittest
D=Path(__file__).resolve().parent
source=D/'root_stage_bound_manifest_once.py';tree=ast.parse(source.read_bytes());pins=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='PINS'for t in n.targets)));namespace={'PINS':pins};node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_bound_source');exec(compile(ast.Module(body=[node],type_ignores=[]),str(source)+':PURE_METADATA_ONLY','exec'),namespace);validate=namespace['validate_bound_source']

def read(p):return json.loads(Path(p).read_bytes())
class Stage(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=read(pins['manifest']['path']);cls.b=read(pins['binding']['path']);cls.r=read(pins['composition_review']['path']);cls.profile=read(D/'SCRATCH-STAGE.PROFILE.NOT-GRANTED.json')
 def test_exact_actual119_source_metadata(self):
  self.assertTrue(validate(self.m,self.b,self.r))
  for key in ['manifest','binding','composition_review']:
   raw=Path(pins[key]['path']).read_bytes();self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(pins[key]['bytes'],pins[key]['sha256']))
 def test_wrong_image_manifest_map_or_review_rejected(self):
  variants=[]
  for field in ['independent','implementation_ownership','guest_execution_authorized']:
   r=copy.deepcopy(self.r);r[field]=not r[field];variants.append((self.m,self.b,r))
  r=copy.deepcopy(self.r);r['full_map_records']=59;variants.append((self.m,self.b,r))
  r=copy.deepcopy(self.r);r['changed_final_map_records']+=['apps/app'];variants.append((self.m,self.b,r))
  m=copy.deepcopy(self.m);m['artifacts']['mckernel_image']['sha256']='de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024';variants.append((m,self.b,self.r))
  b=copy.deepcopy(self.b);b['manifest']['sha256']='0'*64;variants.append((self.m,b,self.r))
  for m,b,r in variants:
   with self.assertRaises(AssertionError):validate(m,b,r)
 def test_no_prior_authority_nonce_or_clearance_replay(self):
  for key in ['source_authority','capability','nonce','current_ledger','current_free','native_release','native_acceptance']:
   b=copy.deepcopy(self.b);b[key]='TEST_ONLY_OLD_AUTHORITY'
   with self.assertRaises(AssertionError):validate(self.m,b,self.r)
  self.assertIsNone(self.profile['new_stage_grant']);self.assertIsNone(self.profile['actual_scratch_stage']);self.assertIsNone(self.profile['runtime_authority'])
 def test_short_outside_parent_namespace_and_235_preservation(self):
  parent=Path(pins['planned_parent']);inputs=Path(pins['scratch_parent']);manifest=Path(pins['scratch_manifest']);self.assertEqual(parent.parent,inputs.parent);self.assertEqual(manifest.parent,inputs);self.assertNotIn(parent,manifest.parents);self.assertLessEqual(len(parent.name),8);self.assertLessEqual(len(inputs.name),8)
  prior=read(self.profile['prior_accepted_stage_source_review']['path']);old=read(prior['actual_manifest']['path'])
  for key in ['case_id','payload','profile','modules','cleanup_profile']:self.assertEqual(self.m[key],old[key])
  for key in ['collector','overlay_source']:self.assertEqual(self.m['staging'][key],old['staging'][key])
 def test_accepted_effect_region_unchanged(self):
  original=ast.parse(Path(self.profile['prior_accepted_stage_source']['path']).read_bytes());oldmain=next(n for n in original.body if isinstance(n,ast.FunctionDef)and n.name=='main');newmain=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main'))
  calls=[i for i,n in enumerate(newmain.body)if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='validate_bound_source'];self.assertEqual(len(calls),1);preflight=calls[0];first_mutation=next(i for i,n in enumerate(newmain.body)if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Attribute)and n.value.func.attr=='mkdir');self.assertLess(preflight,first_mutation);newmain.body.pop(preflight)
  replacements={'composition_review':'binder','m119n1':'f02p115n1','m119n1i':'f02p115n1-inputs','literal_matching119_235_owner':'literal_matching115_235_owner','759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31':'de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024','ACTUAL_ROOT_ORDINARY_MATCHING119_235_MANIFEST_SCRATCH_STAGE_OWNER_API_PASS':'ACTUAL_ROOT_ORDINARY_MATCHING115_235_MANIFEST_SCRATCH_STAGE_OWNER_API_PASS'}
  class Context(ast.NodeTransformer):
   def visit_Constant(self,n):
    if isinstance(n.value,str)and n.value in replacements:return ast.copy_location(ast.Constant(value=replacements[n.value]),n)
    return n
  newmain=Context().visit(newmain);self.assertEqual(ast.dump(oldmain,include_attributes=False),ast.dump(newmain,include_attributes=False))
  self.assertEqual(ast.dump(next(n for n in original.body if isinstance(n,ast.FunctionDef)and n.name=='ref'),include_attributes=False),ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='ref'),include_attributes=False))
if __name__=='__main__':unittest.main()
