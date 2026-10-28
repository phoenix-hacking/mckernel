"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source composition controls. No compiler, guest, clock or workload call.
"""
from pathlib import Path
import copy
import importlib.util
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('composition',HERE/'compose.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CompositionTests(unittest.TestCase):
    def test_actual_reviewed_union(self):
        base,changed,recipe,checks=m.compose()
        self.assertEqual(len(changed),7)
        self.assertEqual(len(recipe['ordered_commands']),4)
        self.assertEqual(len(recipe['retained_inputs']),8)
        self.assertTrue(checks['shared_Rust_hunks_commute'])
        for path,text in changed.items():
            self.assertEqual((HERE/'candidate'/path).read_text(),text)

    def test_wrong_patch_preimage_rejected(self):
        with self.assertRaises(ValueError):m.apply('wrong\n','--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n')

    def test_ambiguous_patch_preimage_rejected(self):
        with self.assertRaises(ValueError):m.apply('old\nold\n','--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n')

    def test_duplicate_application_rejected(self):
        patch_text='--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n'
        with self.assertRaises(ValueError):m.apply(m.apply('old\n',patch_text),patch_text)

    def mutate_json(self,key,mutate):
        original=m.checked
        def changed(row):
            value=original(row)
            if row==m.INPUTS[key]:value=copy.deepcopy(value);mutate(value)
            return value
        with patch.object(m,'checked',changed):
            with self.assertRaises(ValueError):m.compose()

    def test_review_not_independent_rejected(self):
        self.mutate_json('reviewF03',lambda x:x.update(independent=False))

    def test_extra_compiler_command_rejected(self):
        self.mutate_json('recipe116',lambda x:x['ordered_commands'].append(x['ordered_commands'][0]))

    def test_missing_retained_object_rejected(self):
        self.mutate_json('recipe116',lambda x:x['retained_inputs'].pop())

    def test_wrong_origin_compiler_context_rejected(self):
        original=m.read
        def changed(row):
            raw=original(row)
            if row['path'].endswith('/candidate/scripts/f06_origin_command_profile.json'):
                return raw.replace(b'/usr/bin/cc',b'/usr/bin/different-cc')
            return raw
        # This mutation also changes the old profile hash and must fail its
        # original producer/profile join before deriving any successor.
        with patch.object(m,'read',changed):
            with self.assertRaises(ValueError):m.compose()

    def test_missing_header_binding_rejected(self):
        original=m.read
        def changed(row):
            raw=original(row)
            if row['path'].endswith('perf-mmap-binding.C.inc'):return raw+b'/* unexpected */\n'
            return raw
        with patch.object(m,'read',changed):
            with self.assertRaises(ValueError):m.compose()

    def test_two_debug_descriptors_remain_in_new_child(self):
        _,changed,_,_=m.compose();leaf=changed['kernel/rust/f06_vdso_info.rs']
        self.assertEqual(leaf.count('#[link_section = "__verbose"]'),2)
        self.assertEqual(leaf.count('func: b"vdso_get_vdso_info'),2)
        self.assertIn('read_volatile(addr_of!((*vdso).busy))',leaf)

if __name__=='__main__':unittest.main(verbosity=2)
