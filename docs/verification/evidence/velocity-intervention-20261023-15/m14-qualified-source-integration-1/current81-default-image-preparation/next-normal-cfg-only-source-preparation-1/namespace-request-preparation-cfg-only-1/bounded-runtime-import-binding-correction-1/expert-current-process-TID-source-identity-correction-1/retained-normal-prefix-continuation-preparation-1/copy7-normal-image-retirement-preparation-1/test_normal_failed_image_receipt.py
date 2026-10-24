"""Functional OS/Rust only; no security testing. Pure genuine normal failure gates."""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest
D=Path(__file__).resolve().parent;S=D/'cleanup_copy7_normal_failed_image.py'
spec=importlib.util.spec_from_file_location('normal81_cleanup',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OWNER=json.loads(Path(m.SOURCE_REFS['owner_receipt']['path']).read_bytes())
DRIVER=json.loads(Path(m.SOURCE_REFS['driver_receipt']['path']).read_bytes())
class NormalFailure(unittest.TestCase):
 def reject(self,key,value):
  d=copy.deepcopy(DRIVER);d[key]=value
  with self.assertRaises(m.Refusal):m.normal_driver_failure_binding(d)
 def test_actual_driver(self):m.normal_driver_failure_binding(DRIVER)
 def test_wrong_error(self):self.reject('error','other')
 def test_wrong_phase(self):self.reject('phase','identity')
 def test_unexpected_remaining_image_failure(self):
  d=copy.deepcopy(DRIVER);d['commands'][-1]['exit_code']=2
  with self.assertRaises(m.Refusal):m.normal_driver_failure_binding(d)
 def test_wrong_producer_phase(self):
  d=copy.deepcopy(DRIVER);d['commands'][0]['phase']='other-producer'
  with self.assertRaises(m.Refusal):m.normal_driver_failure_binding(d)
 def test_missing_producer(self):self.reject('commands',DRIVER['commands'][:-1])
 def test_actual_owner_and_normal_layout(self):
  m.image_owner_receipt_binding(OWNER,OWNER['terminal_container_info'],'unused')
  request=json.loads(Path(m.REQUEST).read_bytes());command,mounts=m.image_layout(request)
  self.assertEqual(command,OWNER['terminal_container_info']['Config']['Cmd'])
  self.assertFalse(any('retained-prefix' in a for a in command))
  actual=sorted((r['Destination'],r['Source'],r['Type'],r['RW']) for r in OWNER['terminal_container_info']['Mounts'] if r['Type']=='bind')
  self.assertEqual(mounts,actual);self.assertEqual(len([r for r in mounts if r[3]]),1)
 def test_actual_log_channels_and_wrong_duplicate(self):
  channels={k:Path(m.PASS_LOG_CHANNELS[k]['path']).read_bytes() for k in ('stdout','stderr')}
  self.assertEqual(m.validate_log_channels(0,channels['stdout'],channels['stderr']),Path(m.SOURCE_REFS['container_log']['path']).read_bytes())
  with self.assertRaises(m.Refusal):m.validate_log_channels(0,channels['stdout']*2,channels['stderr'])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NormalFailure))
 if not result.wasSuccessful():raise SystemExit(1)
 doc=dict(schema='mckernel.m14.current-retained-receipt-pure-fixture.v1',status='PASS',tests_run=result.testsRun,source_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 with (D/'ACTUAL-NORMAL-PURE-FIXTURE-RESULT.json').open('x') as f:json.dump(doc,f,sort_keys=True);f.write('\n')
 print(json.dumps(doc,sort_keys=True))
