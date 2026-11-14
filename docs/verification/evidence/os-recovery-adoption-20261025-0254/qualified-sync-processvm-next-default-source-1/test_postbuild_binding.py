"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap data-only observer binding tests; never call observe/probes/Docker/current scan.
"""
from pathlib import Path
import copy,importlib.util,json,unittest
from unittest.mock import patch
A=Path(__file__).resolve().parent;B=A.parent/'ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1'
spec=importlib.util.spec_from_file_location('new_exact_postjoin_binding',A/'check_postbuild_current.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ExactBindingTests(unittest.TestCase):
 def test_bound_module_changes_only_declared_literals(self):
  vector=dict(admission=A.name,CID='b'*64,nonce='a'*32,tool='ROOT-ACTUAL-HOLDER-TOOL-RESULT.json',holder_pid=2000001,holder_start=3000001,runner_pid=2000002,runner_start=3000002,container_name='/current290-build-only-'+'a'*32,status='PASS_NEXT10_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION')
  with patch('subprocess.run',side_effect=AssertionError('no runtime calls permitted')) as command:
   module,record=m.bound_observer(vector)
   self.assertEqual(module.ADMISSION,A);self.assertEqual(module.OUTPUT,A/'OUTPUT');self.assertEqual(module.CID,'b'*64);self.assertEqual(record['statement_or_guard_changes'],0);self.assertEqual(module.MUTEX,Path('/run/lock/mckernel-development.lock'));command.assert_not_called()
 def test_actual_bindings_schema_from_retained_completed_trace_no_observer_execution(self):
  # Retained historical files test only literal metadata schema, not availability.
  with patch.object(m,'A',B),patch('subprocess.run',side_effect=AssertionError('no runtime calls permitted')):
   values=m.actual_bindings()
  self.assertEqual(values['CID'],'33ae9294008a13ab890cc3fcbce4c100f8b5c5e95ee27d5d9d3914a2871e7c48');self.assertEqual(values['holder_pid'],1353039);self.assertEqual(values['runner_pid'],1353536);self.assertEqual(values['tool'],'ROOT-ACTUAL-HOLDER-TOOL-RESULT.json')
 def test_missing_data_binding_refused(self):
  with self.assertRaisesRegex(RuntimeError,'exact finite data'):m.bound_observer({})
if __name__=='__main__':unittest.main(verbosity=2)
