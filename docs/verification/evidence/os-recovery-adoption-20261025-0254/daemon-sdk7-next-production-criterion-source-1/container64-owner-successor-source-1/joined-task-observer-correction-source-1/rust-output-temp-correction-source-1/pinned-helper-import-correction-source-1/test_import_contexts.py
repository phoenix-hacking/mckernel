"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Real isolated import/API contexts; no static preparation, compiler or target entry.
"""
from pathlib import Path
import ast,json,subprocess,sys,tempfile,unittest
import pinned_helpers as pinned
U=Path(__file__).resolve().parent;T=U.parent

class RealContexts(unittest.TestCase):
 def context(self,code):
  result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr);return result.stdout
 def test_fixed_bytes_and_genuine_module_context(self):
  for role,function in [('prefix','load'),('audit','validate'),('rustio','runtime_preflight')]:
   path,size,digest=pinned._PINS[role];raw=Path(path).read_bytes();self.assertEqual(pinned.verify_bytes(role,raw),(path,digest))
   module=pinned.helper(role);self.assertEqual(module.__file__,path);self.assertEqual(module.__spec__.origin,path);self.assertEqual(getattr(module,function).__code__.co_filename,path)
   with self.assertRaises(ValueError):pinned.verify_bytes(role,raw+b'\n')
  with self.assertRaises(ValueError):pinned.helper('unlisted')
 def test_literal_prepare_context_without_owner_or_helper_search_path(self):
  code="import sys,runpy;sys.path.insert(0,"+repr(str(U))+");n=runpy.run_path("+repr(str(U/'prepare_adopt_inputs.py'))+",run_name='INERT_IMPORT_ONLY');m=n['mc'];assert 'adopt_owner' not in sys.modules;assert 'prefix_evidence' not in sys.modules;assert m.verify_retained_prefix(m.PREP['retained_prefix_host'])==183;assert m.verify_retained_mock(m.PREP['retained_mock_host'])==17;assert 'prefix_evidence' not in sys.modules;assert m.helper('prefix').__file__=="+repr(pinned._PINS['prefix'][0])+";print('PASS_REAL_PREPARE_IMPORT_CONTEXT_NO_MAIN')"
  self.assertIn('PASS_REAL_PREPARE',self.context(code))
 def test_literal_owner_driver_and_outer_capture_contexts(self):
  for name in ['adopt_owner.py','adopt_driver.py','run_adopt_owned_capture.py']:
   code="import sys,runpy;sys.path.insert(0,"+repr(str(U))+");n=runpy.run_path("+repr(str(U/name))+",run_name='INERT_IMPORT_ONLY');m=n['mc'];assert m.verify_retained_prefix(m.PREP['retained_prefix_host'])==183;assert m.verify_retained_mock(m.PREP['retained_mock_host'])==17;assert m.helper('prefix').__file__=="+repr(pinned._PINS['prefix'][0])+";assert m.helper('audit').__file__=="+repr(pinned._PINS['audit'][0])+";assert m.helper('rustio').__file__=="+repr(pinned._PINS['rustio'][0])+";print('PASS_REAL_ENTRY_IMPORT_CONTEXT_NO_MAIN')"
   with self.subTest(entry=name):self.assertIn('PASS_REAL_ENTRY',self.context(code))
 def test_container_fixture_binding_copy_keeps_accepted_helper_paths(self):
  # Actual fixture startup is -I and inserts its controlled fixture directory.
  # Copy only our own gateway/entry bytes to an inert bind-like location; none
  # of the three accepted helper implementations is copied or changed.
  with tempfile.TemporaryDirectory(prefix='INERT-BIND-IMPORT-',dir=U) as temporary:
   folder=Path(temporary)
   for name in ['run_fixture_suffix.py','pinned_helpers.py']:(folder/name).write_bytes((U/name).read_bytes())
   expected=[pinned._PINS[role][0] for role in ['audit','prefix','rustio','rustio']]
   code="import sys,runpy;sys.path.insert(0,"+repr(str(folder))+");n=runpy.run_path("+repr(str(folder/'run_fixture_suffix.py'))+",run_name='INERT_IMPORT_ONLY');f=n['fixture_helper_bindings']();assert [x.__code__.co_filename for x in f]=="+repr(expected)+";assert 'prefix_evidence' not in sys.modules;print('PASS_REAL_FIXTURE_IMPORT_BINDINGS_NO_MAIN')"
   self.assertIn('PASS_REAL_FIXTURE',self.context(code))
 def test_import_only_delta_preserves_producer_case_and_compiler_bodies(self):
  a=ast.parse((T/'run_fixture_suffix.py').read_bytes());b=ast.parse((U/'run_fixture_suffix.py').read_bytes())
  main_a=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='main');main_b=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='main')
  for name in ['build','execute','closed']:
   x=next(n for n in main_a.body if isinstance(n,ast.FunctionDef) and n.name==name);y=next(n for n in main_b.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertEqual(ast.dump(x,include_attributes=False),ast.dump(y,include_attributes=False))
if __name__=='__main__':unittest.main(verbosity=2)
