"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure current retained-validator receipt gates; no root/Docker/processfactory/cleanup.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys,tempfile,unittest
D=Path(__file__).resolve().parent
S=D/'cleanup_failed_retained_validator.py'
spec=importlib.util.spec_from_file_location('current_retained_cleanup',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OWNER=json.loads(Path(m.SOURCE_REFS['owner_receipt']['path']).read_bytes())
DRIVER=json.loads(Path(m.SOURCE_REFS['driver_receipt']['path']).read_bytes())
PRODUCER=json.loads(Path(m.SOURCE_REFS['original_compiled_driver_receipt']['path']).read_bytes())
COPY=json.loads(Path(m.SOURCE_REFS['retained_copy_binding']['path']).read_bytes())
class CurrentRetainedGate(unittest.TestCase):
 def gate(self,owner=None,driver=None,producer=None,copied=None):
  owner=copy.deepcopy(OWNER if owner is None else owner)
  values={'driver_receipt':DRIVER if driver is None else driver,'original_compiled_driver_receipt':PRODUCER if producer is None else producer,'retained_copy_binding':COPY if copied is None else copied}
  old={k:m.SOURCE_REFS[k] for k in values}
  try:
   with tempfile.TemporaryDirectory(prefix='TESTONLY-current-retained-receipt-') as t:
    for k,v in values.items():
     p=Path(t)/(k+'.json');raw=(json.dumps(v,sort_keys=True)+'\n').encode();p.write_bytes(raw)
     m.SOURCE_REFS[k]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    return m.image_owner_receipt_binding(owner,OWNER['terminal_container_info'],m.SOURCE_REFS['owner_receipt']['sha256'])
  finally:m.SOURCE_REFS.update(old)
 def test_actual_retained_failure_and_original_compiled_copy(self):self.gate()
 def test_owner_PASS_relabel_refused(self):
  o=copy.deepcopy(OWNER);o['status']='PASS'
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_other_current_error_refused(self):
  d=copy.deepcopy(DRIVER);d['error']='other'
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_missing_current_relocation_observer_refused(self):
  d=copy.deepcopy(DRIVER);d['commands']=d['commands'][:1]
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_failed_current_observer_refused(self):
  d=copy.deepcopy(DRIVER);d['commands'][0]['exit_code']=1
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_failed_original_build_refused(self):
  p=copy.deepcopy(PRODUCER);p['commands'][0]['exit_code']=1
  with self.assertRaises(m.Refusal):self.gate(producer=p)
 def test_unverified_retained_copy_refused(self):
  c=copy.deepcopy(COPY);c['complete_build_copy_verified']=False
  with self.assertRaises(m.Refusal):self.gate(copied=c)
 def test_namespace_constant_and_all_eight_pinned_ancestors(self):
  self.assertEqual(m.NAMESPACE, m.ATTEMPT.parent)
  actual=m.namespace_ancestry()
  self.assertEqual(len(actual), 8)
  self.assertEqual(actual, m.NAMESPACE_ANCESTRY)
  expected_paths=[str(p) for p in reversed((m.NAMESPACE, *m.NAMESPACE.parents))]
  self.assertEqual([row['path'] for row in actual], expected_paths)
  self.assertEqual(actual[-1]['path'], str(m.NAMESPACE))
  self.assertEqual({k:v for k,v in actual[-1].items() if k!='path'}, m.NAMESPACE_BINDING)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(CurrentRetainedGate)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 if not(result.wasSuccessful() and result.testsRun==8):sys.exit(1)
 record={'schema':'mckernel.m14.current-retained-receipt-pure-fixture.v1','status':'PASS','tests_run':result.testsRun,'source_sha256':hashlib.sha256(S.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 raw=(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode()
 fd=os.open(D/'CURRENT-RECEIPT-FIXTURE-PASS.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 print(json.dumps(record,sort_keys=True))
