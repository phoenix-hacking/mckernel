"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure recipe consistency controls; no command execution.
"""
from pathlib import Path
import copy
import importlib.util
import hashlib
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('correction',HERE/'correct_recipe.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.recipe,cls.history=m.corrected();cls.encoder=staticmethod(m.actual_encoder())

    def test_four_current_hashes_and_origin_paths(self):
        self.assertEqual(m.validate_recipe(self.recipe,self.encoder),'/work/output/build/kernel/rust/f06-origin')

    def test_changed_argv_have_fresh_hashes(self):
        self.assertEqual([r['index'] for r in self.history if r['argv_changed_from116']],[0,2])
        for i in [0,2]:
            row=self.history[i]
            self.assertNotEqual(row['current117_argv_sha256'],row['historical116_recorded_argv_sha256'])
            self.assertNotEqual(row['current117_argv_sha256'],row['historical116_recomputed_argv_sha256'])

    def test_unchanged_commands_keep_exact_hashes(self):
        for i in [1,3]:
            self.assertEqual(self.history[i]['current117_argv_sha256'],self.history[i]['historical116_recorded_argv_sha256'])

    def test_original_bad_recipe_rejected(self):
        with self.assertRaises(ValueError):m.validate_recipe(m.checked(m.PINS['original117_recipe']),self.encoder)

    def test_tampered_rust_argv_rejected(self):
        changed=copy.deepcopy(self.recipe);changed['ordered_commands'][0]['argv'].insert(-1,'--cfg=unreviewed')
        with self.assertRaises(ValueError):m.validate_recipe(changed,self.encoder)

    def test_tampered_arch_argv_rejected(self):
        changed=copy.deepcopy(self.recipe);changed['ordered_commands'][2]['argv'].append('-DMODIFIED')
        with self.assertRaises(ValueError):m.validate_recipe(changed,self.encoder)

    def test_wrong_encoder_without_final_LF_rejected(self):
        changed=copy.deepcopy(self.recipe);command=changed['ordered_commands'][0]
        command['argv_sha256']=hashlib.sha256(self.encoder(command['argv']).removesuffix(b'\n')).hexdigest()
        with self.assertRaises(ValueError):m.validate_recipe(changed,self.encoder)

    def test_old_origin_output_path_rejected(self):
        changed=copy.deepcopy(self.recipe);changed['prerequisite_origin']['output']='/work/output/build/kernel/f06-origin'
        with self.assertRaises(ValueError):m.validate_recipe(changed,self.encoder)

    def test_arch_include_drift_rejected_even_with_new_matching_hash(self):
        changed=copy.deepcopy(self.recipe);command=changed['ordered_commands'][2]
        command['argv']=[arg.replace('/kernel/rust/f06-origin','/kernel/other-origin') for arg in command['argv']]
        command['argv_sha256']=hashlib.sha256(self.encoder(command['argv'])).hexdigest()
        with self.assertRaises(ValueError):m.validate_recipe(changed,self.encoder)

    def test_sources_unchanged_and_exact_recipe_file(self):
        for row in m.checked(m.PINS['seven_source_map'])['writes']:m.read(row['postimage'])
        self.assertEqual(json.loads((HERE/'MINIMAL-FOUR-COMMAND-CONTINUATION.CORRECTED.NOT-GRANTED.json').read_bytes()),self.recipe)

if __name__=='__main__':unittest.main(verbosity=2)
