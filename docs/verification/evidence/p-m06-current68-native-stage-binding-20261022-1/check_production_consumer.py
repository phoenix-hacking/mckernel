"""Read-only current typedjoin + actual unchanged productionFDconsumer checks."""
from pathlib import Path
from contextlib import ExitStack
import ast,copy,importlib.util,json,sys,unittest
from unittest import mock
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('binding',HERE/'prepare_binding.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.prepare()
spec=importlib.util.spec_from_file_location('stager',HERE/'native_diagnostic_stager.current68.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
report=json.loads(b.REPORT.read_bytes());accept=json.loads(b.ACCEPT.read_bytes());retire=json.loads(b.RETIRE.read_bytes());original=json.loads(Path(report['original_driver_receipt']['path']).read_bytes())
replacements=json.loads((HERE/'REPLACEMENTS.ACTUAL-CURRENT68-AND-IMAGE.json').read_bytes());data=json.loads((HERE/'CURRENT68-STAGE-INPUT-DATA.json').read_bytes())
class ProductionConsumers(unittest.TestCase):
 def test_actual_typed_data_join_preserves_original_FAIL_make0(self):
  self.assertTrue(b.validate_join(report,accept,retire,original));self.assertEqual(original['status'],'FAIL');self.assertEqual(original['make_returncode'],0)
 def test_unknown_profile_and_mixed_vermagic_refuse(self):
  changed=copy.deepcopy(accept);changed['export_profile']='unknown'
  with self.assertRaisesRegex(AssertionError,'export profile'):b.validate_join(report,changed,retire,original)
  changed=copy.deepcopy(report);changed['artifacts']['mcctrl']['modinfo']['vermagic']='different'
  with self.assertRaisesRegex(AssertionError,'vermagic'):b.validate_join(changed,accept,retire,original)
 def test_unknown_module_or_relabelled_old_receipt_refuse(self):
  changed=copy.deepcopy(accept);changed['artifacts']['other.ko']=changed['artifacts'].pop('mcctrl.ko')
  with self.assertRaisesRegex(AssertionError,'three modules'):b.validate_join(report,changed,retire,original)
  changed=copy.deepcopy(original);changed['status']='BUILD_ARTIFACT_CHECKS_PASS'
  with self.assertRaisesRegex(AssertionError,'failed build receipt'):b.validate_join(report,accept,retire,changed)
 def test_production_replacement_map_accepts_REAL_3ko_image_launcher(self):
  with ExitStack()as stack:
   got=s._replacement_map(replacements,stack)
   self.assertEqual(set(got),set(s.MCEEXEC_REPLACEMENT_PATHS))
   for rel,item in got.items():self.assertEqual(item['sha256'],replacements[rel]['sha256']);s._recheck_source(item)
 def test_production_replacement_map_wrong_module_hash_refuses(self):
  changed=copy.deepcopy(replacements);changed['modules/mcctrl.ko']['sha256']='0'*64
  with ExitStack()as stack,self.assertRaisesRegex(s.StagerError,'replacement source hash mismatch'):s._replacement_map(changed,stack)
 def test_selected3_REAL_payloads_match_exact_casepins(self):
  # Only whole-baseinventory is a fixture; all app hashes and source stats real.
  inv=[dict(path=rel,type='file',sha256=value+'0'*57 if rel=='bin/native-boot' else value)for rel,value in s.EXPECTED.items()]
  inv += [dict(path=s.LOADER,type='file'),dict(path=s.LIBC,type='file')]
  for case in data['cases']:
   with mock.patch.object(s,'_inventory',return_value=inv):
    s._check_inputs(Path('/unused-base-fixture'),Path(case['binary']['path']),Path(data['collector']['path']),replacements)
  with mock.patch.object(s,'_inventory',return_value=inv),self.assertRaisesRegex(s.StagerError,'selected app payload path/hash mismatch'):
   s._check_inputs(Path('/unused-base-fixture'),Path(replacements['images/mckernel.img']['path']),Path(data['collector']['path']),replacements)
 def test_only_selected_payload_check_function_changed(self):
  def funcs(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_bytes()).body if isinstance(n,ast.FunctionDef)}
  before=funcs(b.BASE);after=funcs(HERE/'native_diagnostic_stager.current68.py');self.assertEqual(set(before),set(after));self.assertEqual([k for k in before if before[k]!=after[k]],['_check_inputs'])
  self.assertEqual(s.MCEEXEC_SHA256,data['launcher']['sha256']);self.assertEqual(s.MCEEXEC_SIZE,data['launcher']['bytes'])
if __name__=='__main__':unittest.main(verbosity=2)
