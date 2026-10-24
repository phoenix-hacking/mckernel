"""Functional OS/Rust only; no security testing. Pure COPY6 retirement predicates."""
from pathlib import Path
import copy, hashlib, importlib.util, json, unittest
D=Path(__file__).resolve().parent
S=D/'cleanup_failed_retained_validator.py'
spec=importlib.util.spec_from_file_location('copy6_cleanup',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OWNER=json.loads(Path(m.SOURCE_REFS['owner_receipt']['path']).read_bytes())
LOG=Path(m.SOURCE_REFS['container_log']['path']).read_bytes()
class Gates(unittest.TestCase):
    def test_exact_owner(self):
        m.image_owner_receipt_binding(OWNER,OWNER['terminal_container_info'],'unused')
    def test_owner_PASS(self):
        r=copy.deepcopy(OWNER);r['status']='PASS'
        with self.assertRaises(m.Refusal):m.image_owner_receipt_binding(r,OWNER['terminal_container_info'],'unused')
    def test_owner_unretired(self):
        r=copy.deepcopy(OWNER);r['retired']=False
        with self.assertRaises(m.Refusal):m.image_owner_receipt_binding(r,OWNER['terminal_container_info'],'unused')
    def test_owner_uncertain_client(self):
        r=copy.deepcopy(OWNER);r['client_retirement_unproven']=True
        with self.assertRaises(m.Refusal):m.image_owner_receipt_binding(r,OWNER['terminal_container_info'],'unused')
    def test_owner_wrong_exit(self):
        r=copy.deepcopy(OWNER);r['exit_code']=0
        with self.assertRaises(m.Refusal):m.image_owner_receipt_binding(r,OWNER['terminal_container_info'],'unused')
    def test_exact_early_failure(self):m.early_entry_failure_binding(LOG,False)
    def test_changed_early_failure(self):
        with self.assertRaises(m.Refusal):m.early_entry_failure_binding(LOG[:-1],False)
    def test_driver_evidence_present_refused(self):
        with self.assertRaises(m.Refusal):m.early_entry_failure_binding(LOG,True)
    def test_exact_stderr_log_channel(self):self.assertEqual(m.validate_log_channels(0,b'',LOG),LOG)
    def test_wrong_log_channels(self):
        for rc,out,err in [(1,b'',LOG),(0,LOG,b''),(0,b'',LOG+b'\n'),(0,b'',b'')]:
            with self.assertRaises(m.Refusal):m.validate_log_channels(rc,out,err)
    def test_exact_namespace_and_clients(self):
        self.assertEqual(m.namespace_ancestry(),m.NAMESPACE_ANCESTRY)
        self.assertEqual(len(set(m.KNOWN_CLIENT_PIDS)),7)
        self.assertNotIn('driver_receipt',m.SOURCE_REFS)
    def test_genuine_owner_command_and_mounts(self):
        request=json.loads(Path(m.REQUEST).read_bytes())
        command,mounts=m.image_layout(request)
        self.assertEqual(command,OWNER['terminal_container_info']['Config']['Cmd'])
        self.assertEqual(command[-2:],['--retained-prefix49-authority','/work/output/retained-prefix49.AUTHORITY.json'])
        actual=OWNER['terminal_container_info']['Mounts']
        actual=sorted((r['Destination'],r['Source'],r['Type'],r['RW']) for r in actual if r['Type']=='bind')
        self.assertEqual(mounts,actual)
        self.assertEqual(len([r for r in mounts if r[3]]),1)
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Gates))
    if not result.wasSuccessful():raise SystemExit(1)
    doc=dict(schema='mckernel.m14.current-retained-receipt-pure-fixture.v1',status='PASS',tests_run=result.testsRun,source_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with (D/'ACTUAL-PURE-FIXTURE-RESULT.json').open('x') as f:json.dump(doc,f,sort_keys=True);f.write('\n')
    print(json.dumps(doc,sort_keys=True))
