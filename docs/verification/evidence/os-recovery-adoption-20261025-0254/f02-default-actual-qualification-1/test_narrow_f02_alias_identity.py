"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure regression controls against a broader alias waiver; no compiler/workload.
"""
import copy,json,unittest
from pathlib import Path
from narrow_f02_alias_identity import validate
D=Path(__file__).resolve().parent
ROWS=json.loads((D/'NARROW-ALIAS-ACTUAL-ROWS.json').read_text())
class NarrowAliasIdentityTests(unittest.TestCase):
 def reject(self,field,value,index=1):
  changed=copy.deepcopy(ROWS);changed[index][field]=value
  with self.assertRaises(RuntimeError):validate(changed)
 def test_actual_two_reviewed_pairs(self):self.assertTrue(validate(ROWS)['all_ten_original_named_final_function_addresses'])
 def test_unreviewed_pair(self):self.reject('actual_name','unreviewed_alias')
 def test_wrong_slot(self):self.reject('offset',0)
 def test_wrong_original_name(self):self.reject('original_name','unreviewed_original')
 def test_R64_or_addend_mutation(self):
  for field,value in [('type',2),('addend',8)]:
   with self.subTest(field=field):self.reject(field,value)
 def test_changed_object_identity(self):
  for field,value in [('bind',0),('type',1),('shndx',0),('value',8),('size',1),('other',2)]:
   changed=copy.deepcopy(ROWS);changed[1]['actual_object_symbol'][field]=value
   with self.subTest(field=field),self.assertRaises(RuntimeError):validate(changed)
 def test_changed_final_identity(self):
  for field,value in [('bind',0),('type',1),('shndx',0),('value',8),('size',1),('other',2)]:
   changed=copy.deepcopy(ROWS);changed[2]['actual_final_symbol'][field]=value
   with self.subTest(field=field),self.assertRaises(RuntimeError):validate(changed)
 def test_changed_object_or_final_code(self):
  for field in ['original_object_code_hex','actual_object_code_hex','original_final_code_hex','actual_final_code_hex']:
   with self.subTest(field=field):self.reject(field,'00')
 def test_wrong_final_original_target(self):self.reject('final_table_pointer',0)
 def test_other_slot_cannot_use_even_reviewed_alias(self):self.reject('actual_name','mem_kmalloc_remote_lock_bridge',index=0)
 def test_missing_slot(self):
  with self.assertRaises(RuntimeError):validate(ROWS[:-1])
if __name__=='__main__':unittest.main(verbosity=2)
