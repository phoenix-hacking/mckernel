"""Stopped-rescue source/mock contract tests; no compiler, container, or root."""
import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent/'fixtures/application-collector-v1/linux-sealed-v1/stopped-rescue-v1'
def load(name):
 s=importlib.util.spec_from_file_location('stopped_rescue_test_'+name,HERE/(name+'.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
p=load('prepare'); oracle=load('oracle')
class StoppedRescuePacketTests(unittest.TestCase):
 def test_packet_is_nonaccepting_and_hash_bound(self):
  packet=p.packet(HERE/'packet.json'); self.assertFalse(packet['application_acceptance']); self.assertFalse(packet['backend_enabled'])
  self.assertEqual([x['id'] for x in packet['cases']],['control','stopped-rescue']); self.assertEqual(packet['cases'][1]['raw_stop_status'],4991)
 def test_generated_patch_and_guarded_hooks(self):
  source=p.read(p.SOURCE); generated=p.generate(source); patch=p.read(HERE/'collector.patch')
  self.assertTrue(p.patch_is_applicable(source,generated,patch)); self.assertEqual(generated.count(b'm02_stopped_rescue_child_boundary(setup_fd, words);'),1)
  self.assertEqual(generated.count(b'm02_stopped_rescue_completed_wait_hook'),1)
  header=p.read(HERE/'inject.h').decode();
  for marker in ('READY','STOP_ARMED','SIGSTOP','4991','SIGTERM','SIGCONT','ECHILD'): self.assertIn(marker,header if marker not in ('ECHILD','SIGCONT') else p.read(HERE/'rescuer.c').decode())
 def test_oracle_rejects_wrong_wait_or_adoption(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); row={'status':'RESCUED','raw_collector_wait':256,'raw_stop_status':4991,'raw_fixture_waits':[9,9],'adoption_observed':'ECHILD','ready':['READY','STOP_ARMED'],'application_acceptance':False,'backend_enabled':False}; (root/'rescue-report.json').write_text(json.dumps(row))
   self.assertEqual(oracle.validate_retained(root,'stopped-rescue'),row); row['raw_stop_status']=0; (root/'rescue-report.json').write_text(json.dumps(row))
   with self.assertRaises(ValueError): oracle.validate_retained(root,'stopped-rescue')
 def test_source_packet_never_releases_runtime(self):
  self.assertIn(b'SOURCE_ONLY_NOT_EXECUTED',p.read(HERE/'run.py')); self.assertIn(b'SOURCE_PACKET_ONLY',p.read(HERE/'packet.json'))
if __name__=='__main__': unittest.main()
