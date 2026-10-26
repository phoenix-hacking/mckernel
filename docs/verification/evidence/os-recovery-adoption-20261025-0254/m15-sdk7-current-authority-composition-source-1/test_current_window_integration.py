"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused pure integration checks; parent fourteen-test suite is reused, not rerun.
"""
import ast,copy,hashlib,json,unittest
from pathlib import Path
import sdk7_current_window as w
D=Path(__file__).resolve().parent
P=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/parallel-m15-sdk-queue-1')
class Integration(unittest.TestCase):
 def test_actual_pinned_root_boundary_is_earlier_than_static_samples(self):
  parent=w.bound(w.PARENT_WINDOW);proof=w.bound(w.ROOT_CUTOFF);value=w.normalize(parent,proof)
  self.assertEqual([value['deadline_epoch'],value['monotonic_deadline'],value['boot_deadline']],w.FIXED)
  self.assertLess(value['monotonic_deadline'],parent['monotonic_deadline'])
  self.assertLess(value['boot_deadline'],parent['boot_deadline'])
  for start,end in [('start_epoch','deadline_epoch'),('start_monotonic','monotonic_deadline'),('start_boot','boot_deadline')]:self.assertEqual(value[end]-value[start],64800)
  self.assertEqual(w.validate_window(value),value)
 def test_old_later_window_and_changed_window_boot_or_credit_are_refused(self):
  parent=w.bound(w.PARENT_WINDOW);proof=w.bound(w.ROOT_CUTOFF)
  with self.assertRaisesRegex(ValueError,'exact-earliest-bound'):w.validate_window(parent)
  for key,value in [('window_id','other'),('boot_id','other'),('credit_run_id','other'),('fixed_cutoffs',[1793100290.0,882396.0,897735.0])]:
   altered=copy.deepcopy(proof);altered[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):w.normalize(parent,altered)
 def test_consumer_changes_only_window_import_and_one_load(self):
  old=ast.parse((P/'sdk7_authority_adapter.py').read_bytes());new=ast.parse((D/'sdk7_authority_adapter.CURRENT-WINDOW.SOURCE-ONLY.py').read_bytes())
  class WindowLoad(ast.NodeTransformer):
   def visit_Call(self,node):
    if ast.dump(node,include_attributes=False)==ast.dump(ast.parse('json.loads(WINDOW.read_bytes())',mode='eval').body,include_attributes=False):return ast.copy_location(ast.Call(func=ast.Name(id='load_window',ctx=ast.Load()),args=[],keywords=[]),node)
    return self.generic_visit(node)
  def functions(tree):return {n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
  oldf,newf=functions(old),functions(new);self.assertEqual(set(oldf),set(newf))
  for name in oldf:
   expected=WindowLoad().visit(oldf[name]) if name=='main' else oldf[name]
   self.assertEqual(ast.dump(expected,include_attributes=False),ast.dump(newf[name],include_attributes=False),name)
  for name in ('prepare_current_window_bindings.py','retained_sdk21_authority.py'):
   self.assertEqual((D/name).read_bytes(),(P/name).read_bytes())
  self.assertEqual(hashlib.sha256((P/'sdk7_authority_adapter.py').read_bytes()).hexdigest(),'6341a77c21fbb1de9aeb35f8d9875ffdb8673933f6912f4abd50c8144a9d9284')
if __name__=='__main__':unittest.main(verbosity=2)
