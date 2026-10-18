"""Affected 16MiB append boundaries only; ordinary, no subprocess or signals."""
from pathlib import Path
import importlib.util,io,unittest
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('reader_cap16',R/'readback_capture.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class ExactCapBoundary(unittest.TestCase):
 def test_exact_16m_capture_is_accepted(self):
  self.assertEqual(m.CAP,16<<20)
  output=io.BytesIO();payload=b'x'*m.CAP
  self.assertEqual(m.append_bounded(output,payload,0,m.CAP),m.CAP)
  self.assertEqual(output.getvalue(),payload)
 def test_16m_plus_one_rejected_before_any_write(self):
  output=io.BytesIO();payload=b'x'*(m.CAP+1)
  with self.assertRaisesRegex(ValueError,'CAPTURE_LIMIT_BEFORE_WRITE'):
   m.append_bounded(output,payload,0,m.CAP)
  self.assertEqual(output.getvalue(),b'')
 def test_one_more_byte_after_exact_total_is_rejected_without_changing_capture(self):
  output=io.BytesIO();payload=b'x'*(m.CAP-1)
  used=m.append_bounded(output,payload,0,m.CAP)
  used=m.append_bounded(output,b'y',used,m.CAP)
  with self.assertRaisesRegex(ValueError,'CAPTURE_LIMIT_BEFORE_WRITE'):
   m.append_bounded(output,b'z',used,m.CAP)
  self.assertEqual(output.getvalue(),payload+b'y')
if __name__=='__main__':unittest.main(verbosity=2)
