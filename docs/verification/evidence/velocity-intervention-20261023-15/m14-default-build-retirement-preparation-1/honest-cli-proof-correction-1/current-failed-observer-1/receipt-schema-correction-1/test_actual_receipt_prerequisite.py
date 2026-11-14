"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure actual retained-receipt prerequisite regression; no root/Docker/process observation/cleanup.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest
D=Path(__file__).resolve().parent
S=D/'observe_current_failed_image_retirement.RECEIPT-SCHEMA-CORRECTED.py'
spec=importlib.util.spec_from_file_location('current_failed_observer',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CASE=json.loads(m.stable_bytes(m.FAILURE_CASE,m.FAILURE_CASE_SHA,4<<20))
def actual(role):
 r=CASE['finite_roles'][role];return json.loads(m.stable_bytes(Path(r['path']),r['sha256']))
ARTIFACT=actual('driver_receipt');JOIN=actual('fixture_whole_join')
class ActualReceipt(unittest.TestCase):
 def check(self,artifact):m.current_pass_prerequisites(m.KNOWN_TOOL_TERMINAL,CASE,JOIN,artifact)
 def test_actual_hashbound_receipt_without_schema(self):
  self.assertNotIn('schema',ARTIFACT);self.check(copy.deepcopy(ARTIFACT))
 def test_added_fabricated_schema_refused(self):
  a=copy.deepcopy(ARTIFACT);a['schema']='mckernel.native-exact-mckernel-image-receipt.v1'
  with self.assertRaises(RuntimeError):self.check(a)
 def test_missing_commands_refused(self):
  a=copy.deepcopy(ARTIFACT);del a['commands']
  with self.assertRaises(RuntimeError):self.check(a)
 def test_PASS_relabelling_refused(self):
  a=copy.deepcopy(ARTIFACT);a['status']='PASS'
  with self.assertRaises(RuntimeError):self.check(a)
 def test_other_failure_refused(self):
  a=copy.deepcopy(ARTIFACT);a['error']='other'
  with self.assertRaises(RuntimeError):self.check(a)
 def test_failed_compile_refused(self):
  a=copy.deepcopy(ARTIFACT);a['commands'][0]['exit_code']=1
  with self.assertRaises(RuntimeError):self.check(a)
 def test_missing_real_link_refused(self):
  a=copy.deepcopy(ARTIFACT);a['commands']=[x for x in a['commands'] if x['phase']!='build']
  with self.assertRaises(RuntimeError):self.check(a)
if __name__=='__main__':unittest.main(verbosity=2)
