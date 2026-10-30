#!/usr/bin/env python3
"""Synthetic predecessor gate; no configure or other physical execution."""
import importlib.util,pathlib,unittest
b=pathlib.Path(__file__).parent.parent
s=importlib.util.spec_from_file_location('oldtests',b/'m14-configure-sdk-v8-source-1/test_successor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Regression(unittest.TestCase):
 def test_override_forms_rejected(self):
  for extra in ('-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL:BOOL=OFF','-UKERNEL_DIR','-C/tmp/initial.cmake'):
   c=m.Gates().cmds();c[0]['argv'].append(extra)
   with self.subTest(extra=extra),self.assertRaises(ValueError):m.v._selectors({'commands':c},{'commands':c})
 def test_empty_equal_flags_allowed(self):
  c=m.Gates().cmds();a=c[0]['argv'];a[a.index('-DKBUILD_MAKE_FLAGS=CC=x')]='-DKBUILD_MAKE_FLAGS=';a[a.index('-DMCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS=CC=x')]='-DMCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS='
  m.v._selectors({'commands':c},{'commands':c})
if __name__=='__main__':unittest.main(verbosity=2)
