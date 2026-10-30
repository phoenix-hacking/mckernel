#!/usr/bin/env python3
"""Synthetic conflicting CMake option regression; no configure execution."""
import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('gates',p/'test_successor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Correction(unittest.TestCase):
 def test_conflicting_duplicate_options_rejected(self):
    c=m.Gates().cmds();m.v._selectors({'commands':c},{'commands':c})
    for extra in ('-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=OFF','-DKERNEL_DIR=/other'):
        x=m.Gates().cmds();x[0]['argv'].append(extra)
        with self.subTest(extra=extra),self.assertRaises(ValueError):m.v._selectors({'commands':x},{'commands':x})
if __name__=='__main__':unittest.main(verbosity=2)
