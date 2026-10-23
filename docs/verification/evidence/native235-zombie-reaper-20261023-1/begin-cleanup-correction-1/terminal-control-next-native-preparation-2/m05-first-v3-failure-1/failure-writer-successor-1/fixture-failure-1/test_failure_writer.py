"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST ONLY backend envelopes over retained M05 serial. No native acceptance.
"""
from pathlib import Path
import copy,importlib.util,json,tempfile,unittest
D=Path(__file__).resolve().parent
B=D.parent.parent
RAW=B/'failed-m05-495e-raw-1/guest'
BASE=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/sdk5-successor-1')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
OLD=load('old_writer',D/'native_diagnostic.preimage.py');NEW=load('new_writer',D/'native_diagnostic.py')
Q=json.loads((RAW/'result.json').read_text())['qemu_evidence'];IDENTITY={k:Q[k] for k in ('pid','pgid','sid','starttime_ticks')}
class Process:
 def terminate(self):pass
 def kill(self):pass
 def wait(self,timeout):return 0
 def communicate(self,timeout):return b'',b''
 def process_identity(self):return dict(IDENTITY)
 def qemu_evidence(self):return copy.deepcopy(Q)
class Qmp:
 def negotiate(self,timeout):pass
 def resume(self,timeout):pass
 def wait_shutdown(self,timeout):return {'status':'shutdown'}
 def terminate(self,timeout):pass
 def close(self,timeout):pass
class WriterTests(unittest.TestCase):
 def exercise(self,mod,process=None,qmp=None,evaluator=None,serial=None):
  with tempfile.TemporaryDirectory(dir=D,prefix='writer-fixture-') as tmp:
   p=Path(tmp);(p/'serial.log').write_bytes((RAW/'serial.log').read_bytes() if serial is None else serial);(p/'debugcon.log').write_bytes((RAW/'debugcon.log').read_bytes())
   original=mod.evaluate
   def refuse(m,o):raise mod.DiagnosticError('evaluation first')
   mod.evaluate=evaluator or refuse
   try:
    with self.assertRaises(mod.DiagnosticError):mod.exercise_lifecycle({},p,lambda timeout:process or Process(),lambda timeout:qmp or Qmp(),timeout=10)
   finally:mod.evaluate=original
   r=json.loads((p/'result.json').read_text());j=json.loads((p/'first-failure.jsonl').read_text());self.assertFalse(r['application_acceptance']);self.assertFalse(r['mckernel_application_executed']);self.assertTrue(r['cleanup']['reaped']);return r,j
 def test_real_evaluation_failure_retains_envelope_and_preimage_loses_it(self):
  for mod,expected in ((OLD,False),(NEW,True)):
   r,j=self.exercise(mod);self.assertEqual('observation' in r,expected);self.assertEqual(j['error'],'evaluation first')
   if expected:self.assertEqual(r['observation']['serial'],(RAW/'serial.log').read_text());self.assertLess(r['observation']['finished_at'],r['observation']['deadline'])
 def test_real_M05_evaluator_retains_actual_serial_TEST_ONLY_host_envelope(self):
  adapter=load('actual_m05_adapter',BASE/'consumer-correction-1/case_evaluator.py');manifest=json.loads((BASE/'actual-stage-1/manifest.json').read_text())
  r,j=self.exercise(NEW,evaluator=lambda _,o:adapter.case_evaluate(manifest,o));self.assertEqual(r['failure']['error'],'M05 case: payload after resource capture');self.assertEqual(r['observation']['serial'],(RAW/'serial.log').read_text());self.assertEqual(j,r['failure'])
 def test_capture_failure_retains_first_error_without_fabricated_observation(self):
  class Bad(Process):
   def communicate(self,timeout):raise RuntimeError('capture failure')
  r,j=self.exercise(NEW,process=Bad());self.assertNotIn('observation',r);self.assertEqual(j['error'],'capture failure');self.assertEqual(r['capture_errors'][0]['phase'],'host-capture')
 def test_lifecycle_failure_priority_over_capture_failure(self):
  class Bad(Process):
   def communicate(self,timeout):raise RuntimeError('secondary capture')
  class Broken(Qmp):
   def resume(self,timeout):raise RuntimeError('first lifecycle')
  r,j=self.exercise(NEW,process=Bad(),qmp=Broken());self.assertEqual(j['error'],'first lifecycle');self.assertEqual(r['failure']['phase'],'lifecycle');self.assertEqual(r['capture_errors'][0]['error'],'secondary capture')
 def test_existing_capture_bound_is_unchanged(self):
  old=NEW.MAX_JSON;NEW.MAX_JSON=64
  try:r,j=self.exercise(NEW,serial=b'x'*65)
  finally:NEW.MAX_JSON=old
  self.assertNotIn('observation',r);self.assertEqual(j['error'],'capture limit exceeded')
 def test_atomic_first_publication_and_dangling_symlink_no_overwrite(self):
  with tempfile.TemporaryDirectory(dir=D,prefix='atomic-fixture-') as tmp:
   p=Path(tmp);NEW.write_record(p,{'status':'FAIL'}, {'error':'first'});before=(p/'result.json').read_bytes();journal=(p/'first-failure.jsonl').read_bytes()
   with self.assertRaisesRegex(NEW.DiagnosticError,'already published'):NEW.write_record(p,{'status':'replacement'},{'error':'second'})
   self.assertEqual(before,(p/'result.json').read_bytes());self.assertEqual(journal,(p/'first-failure.jsonl').read_bytes());self.assertEqual(list(p.glob('.result.*')),[])
  with tempfile.TemporaryDirectory(dir=D,prefix='symlink-fixture-') as tmp:
   p=Path(tmp);(p/'result.json').symlink_to(p/'absent')
   with self.assertRaisesRegex(NEW.DiagnosticError,'already published'):NEW.write_record(p,{'status':'replacement'})
   self.assertFalse((p/'absent').exists())
if __name__=='__main__':unittest.main(verbosity=2)
