"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
from contextlib import ExitStack
import copy,importlib.util,unittest
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('bound_stager',D/'stage_m05_two_generation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ModeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.b=m.load_binding();cls.old=m.authorities(cls.b);cls.ov=m.module('unchanged_overlay',cls.b['overlay_source']['path'])
 def test_authentic0700_source_produces_preserved0755_guest_metadata(self):
  with ExitStack() as stack:
   src=m.authenticated(self.ov,self.b['collector'],stack);self.assertEqual(src.identity['st_mode'],0o100700);self.assertEqual(src.identity['st_uid'],1000);src.verify()
  final=m.validate_selection({'init':self.b['collector']},self.old,self.b);self.assertEqual(final['init']['mode'],0o100755);m.verify_delta(self.old,final,self.b)
 def test_wrong_source_mode_or_kind_refused(self):
  for mode in (0o100755,0o100600,0o040700,0o120700):
   b=copy.deepcopy(self.b);b['collector']['mode']=mode
   with self.assertRaises(ValueError):m.validate_selection({'init':b['collector']},self.old,b)
   with ExitStack() as stack:
    with self.assertRaises(ValueError):m.authenticated(self.ov,b['collector'],stack)
 def test_wrong_guest_metadata_refused(self):
  final=m.validate_selection({'init':self.b['collector']},self.old,self.b)
  for field in ('mode','uid','gid','nlink','mtime'):
   wrong=copy.deepcopy(final);wrong['init'][field]+=1
   with self.assertRaises(ValueError):m.verify_delta(self.old,wrong,self.b)
if __name__=='__main__':unittest.main(verbosity=2)
