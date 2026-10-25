"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Disposable transaction fixtures only: no root/Docker/production lock or cleanup.
"""
import os,json,hashlib,importlib.util,unittest
from pathlib import Path
D=Path(__file__).parent
SOURCE=D/'native_rust_cutover_image_terminal_cleanup.CURRENT290.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='8d918b3f7675791129e3e757283cea1fade93c134f71c292f995a93707addfec'
BASE=Path('/home/holden/mckernel/scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py')
BASE_SHA='2fba315ad96f271124cf78f7441faa306f58ea03ae35cdbe78bba5be6488d630'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
spec=importlib.util.spec_from_file_location('existing_disposable_tests',BASE)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.SOURCE=SOURCE;b.P=D/'current290-tempfile-finite-transaction-output-4';b.P.mkdir(mode=0o700)
class FiniteOwnershipTests(b.NestedCleanupTests):
    def case(self,passed):
        m=self.m
        m.OWNERSHIP_CASE='PASS_COMMON_ONLY_SHARED_ABSENT' if passed else 'FAIL_COMMON_AND_SHARED'
        if passed:m.SHARED.unlink();del m.RECORDS[m.SHARED]
        return m
    def execute_case(self,passed):
        m=self.case(passed);paths=m.owned_record_paths();before={p:p.read_bytes() for p in paths}
        tx=self.transaction();r=tx.run(True)
        self.assertEqual(r['status'],'PASS_EXECUTED');self.assertTrue(r['terminal']);self.assertTrue(r['container_absent'])
        self.assertEqual(len(m.JOURNAL.read_text().splitlines()),5 if passed else 9)
        self.assertEqual(len(m.archive_paths()),1 if passed else 2)
        for p,a in zip(paths,m.archive_paths()):self.assertFalse(p.exists());self.assertEqual(a.read_bytes(),before[p])
        if passed:self.assertFalse((m.ROOT/m.ARCHIVE_NAMES[1]).exists());self.assertFalse(m.SHARED.exists())
        self.assertEqual(tx.run(True)['status'],'PASS_TERMINAL_REPLAY');self.assert_canary()
        self.assertEqual((m.OUTPUT/'published.img').read_bytes(),b'preserved image')
    def test_pass_common_only_five_events(self):self.execute_case(True)
    def test_fail_common_shared_nine_events(self):self.execute_case(False)
    def test_pass_shared_present_refused(self):
        m=self.m;m.OWNERSHIP_CASE='PASS_COMMON_ONLY_SHARED_ABSENT'
        with self.assertRaises(m.Refusal):self.transaction()
    def test_pass_unused_archive_present_refused(self):
        m=self.case(True);(m.ROOT/m.ARCHIVE_NAMES[1]).write_bytes(b'unowned')
        with self.assertRaises(m.Refusal):self.transaction()
    def test_pass_shared_reappeared_refused(self):
        m=self.case(True);tx=self.transaction();m.SHARED.write_bytes(b'unowned')
        with self.assertRaises(m.Refusal):tx.run(True)
    def test_invalid_case_refused(self):
        m=self.m;m.OWNERSHIP_CASE='UNKNOWN'
        with self.assertRaises(m.Refusal):m.owned_record_paths()
    def test_wrong_case_binding_refused(self):
        m=self.case(True)
        with self.assertRaises(m.Refusal):m.ownership_case_binding({'status':'PASS'},{'ownership_case':'FAIL_COMMON_AND_SHARED','shared_record_already_absent':False},[{'path':str(m.ATTEMPT)}])
    def test_duplicate_fail_paths_refused(self):
        m=self.case(False)
        with self.assertRaises(m.Refusal):m.ownership_case_binding({'status':'FAIL'},{'ownership_case':'FAIL_COMMON_AND_SHARED','shared_record_already_absent':False},[{'path':str(m.ATTEMPT)}]*2)
names=[k for k in FiniteOwnershipTests.__dict__ if k.startswith('test_')]
suite=unittest.TestSuite(FiniteOwnershipTests(n) for n in names)
result=unittest.TextTestRunner(verbosity=2).run(suite)
record=dict(scope=__doc__,status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),production_cleanup=False,root_mutex_touched=False,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
(b.P/'RESULT.json').open('x').write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps(record,sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
