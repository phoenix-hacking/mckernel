"""Bounded, unprivileged tests for the retry2 execution-release packet."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'docs/verification/evidence/native-exact-scratch18-retry2-execution-20261001.py'

def load():
    spec = importlib.util.spec_from_file_location('retry2_execution', SOURCE)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class ExecutionReleaseTests(unittest.TestCase):
    def setUp(self):
        self.m = load(); self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name); self.m.ROOT = root
        self.m.PREP_REQUEST = root/'prepared.json'; self.m.PREP_PLAN = root/'plan'; self.m.PREP_JOURNAL = root/'journal'; self.m.PREP_MUTEX = root/'mutex'
        self.m.OUTPUT = root/'out'; self.m.EVIDENCE = root/'evidence'; self.m.OWNER = root/'owner'; self.m.EXECUTION_REQUEST = root/'execution.json'
        for p in (self.m.OUTPUT,self.m.EVIDENCE,self.m.OWNER): p.mkdir(mode=0o700)
        q = {'preparation_only':False,'execution_released':False,'executable':True,'launcher_aggregate_memory_gib':'16.2158','host_floor':0,'scratch_floor':0}
        self.raw = self.m.canonical(q) + b'\n'; self.m.PREP_REQUEST.write_bytes(self.raw)
        self.m.PREP_PLAN.write_bytes(self.m.canonical({'schema':'scratch18.retry2.preparation.v1','release_commit':self.m.RELEASE_COMMIT,'request_sha256':self.m.sha(self.raw),'cleanup_publication_sha256':'0a711653f48d1e29705de818d6297dca34c89e7ed142dfbef8368de2b854cf10','paths':[str(self.m.OUTPUT),str(self.m.EVIDENCE),str(self.m.OWNER),str(self.m.PREP_REQUEST)]}))
        self.m.PREP_JOURNAL.write_bytes(b'\n'.join(self.m.canonical({'event':('complete' if i==7 else 'x')}) for i in range(8))+b'\n'); self.m.PREP_MUTEX.write_bytes(b'')
        self.q = q
        self.ids = {str(p): self.m.rec(p) for p in (self.m.PREP_MUTEX,self.m.PREP_PLAN,self.m.PREP_JOURNAL,self.m.PREP_REQUEST,self.m.OUTPUT,self.m.EVIDENCE,self.m.OWNER)}
        self.fake_wrapper = mock.Mock()
        self.fake_wrapper.validate_request.return_value={'status':'PASS_COMPATIBILITY_ONLY','execution_released':False}
        self.fake_wrapper.census_request.return_value={'status':'PASS_READ_ONLY','execution_released':False,'processes':[],'containers':[]}
        self.fake_wrapper.run_request.return_value={'status':'PASS','execution_released':False}

    def patch_admission(self):
        self.patches = [mock.patch.object(self.m,'bound_sources',return_value={self.m.WRAPPER:b'',self.m.CLEANUP:b''}), mock.patch.object(self.m,'cleanup_ok',return_value={'result':'PASS_TERMINAL_REPLAY'}), mock.patch.object(self.m,'prepared',return_value=(self.q,self.raw,self.ids)), mock.patch.object(self.m,'load_wrapper',return_value=self.fake_wrapper)]
        for p in self.patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def test_default_is_read_only_and_has_no_derived_request(self):
        self.patch_admission(); result = self.m.release(False)
        self.assertEqual(result['status'],'PASS_VALIDATE_ONLY'); self.assertFalse(result['execution_released']); self.assertFalse(self.m.EXECUTION_REQUEST.exists())

    def test_release_fields_are_the_only_flag_changes(self):
        self.patch_admission(); result = self.m.release(False)
        derived = json.loads(self.m.canonical(dict(self.q, execution_released=True)) or b'{}')
        self.assertEqual(result['derived_request_sha256'], self.m.sha(self.m.canonical(dict(self.q, execution_released=True))+b'\n'))
        self.assertTrue(result['executable']); self.assertEqual(set(self.q), set(derived))

    def test_execute_publishes_o_excl_and_calls_wrapper_once(self):
        self.patch_admission()
        with mock.patch.object(self.m.os,'execv',side_effect=RuntimeError('sentinel')) as ex:
            result = self.m.release(execute=True)
        ex.assert_not_called(); self.assertEqual(result['status'],'PASS_EXECUTED'); self.fake_wrapper.run_request.assert_called_once(); self.assertTrue(self.m.EXECUTION_REQUEST.exists()); self.assertEqual(self.m.EXECUTION_REQUEST.read_bytes().count(b'"execution_released":true'),1)

    def test_second_execute_refuses_existing_published_request(self):
        self.patch_admission(); self.m.EXECUTION_REQUEST.write_bytes(b'old')
        with self.assertRaisesRegex(self.m.Refusal,'execution-request-present'): self.m.release(execute=True)

    def test_identity_change_after_census_is_rejected(self):
        self.patch_admission(); original=self.m.bind; calls=[0]
        def raced(path,row):
            calls[0]+=1
            if calls[0]==1: raise self.m.Refusal('identity-binding:raced')
            return original(path,row)
        with mock.patch.object(self.m,'bind',side_effect=raced):
            with self.assertRaisesRegex(self.m.Refusal,'identity-binding'): self.m.release(False)

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaises(self.m.Refusal): self.m.strict(b'{"a":1,"a":2}')

    def test_canonical_digest_is_stable(self):
        self.assertEqual(self.m.sha(self.m.canonical({'b':1,'a':[True,None]})), self.m.sha(self.m.canonical({'a':[True,None],'b':1})))

    def test_unsafe_path_is_rejected(self):
        with self.assertRaises(self.m.Refusal): self.m.directory(Path('/tmp/../etc'))

    def test_production_records_include_directory_stat_size_and_full_hashes(self):
        m = self.m
        self.assertEqual(m.EXPECTED['/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-18-retry2-20261001-output'][6], 4096)
        self.assertEqual(m.EXPECTED['/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-18-retry2-20261001-evidence'][6], 4096)
        self.assertEqual(m.EXPECTED['/home/holden/mckernel-work/scratch/native-exact-scratch18-retry2-20261001-owner-evidence'][6], 4096)
        self.assertEqual(len(m.EXPECTED['/home/holden/mckernel-work/scratch/native-exact-scratch18-retry2-preparation.plan.json'][7]), 64)
        self.assertEqual(len(m.EXPECTED['/home/holden/mckernel-work/scratch/native-exact-scratch18-retry2-preparation.journal.jsonl'][7]), 64)

    def test_fixed_production_binding_accepts_exact_record_shape(self):
        m = self.m
        ids = {}
        for path, row in m.EXPECTED.items():
            ids[path] = {'path':path,'device':row[0],'inode':row[1],'nlink':row[2],
                         'mode':row[3],'uid':row[4],'gid':row[5],'size':row[6],
                         'sha256':row[7]}
        with mock.patch.object(m, 'ROOT', Path('/home/holden/mckernel-work/scratch')):
            m.fixed_production_bindings(ids)

    def test_authenticated_wrapper_buffer_is_consumed_without_path_reread(self):
        self.patch_admission()
        with mock.patch.object(self.m, 'read_regular', side_effect=AssertionError('replacement reread')):
            result = self.m.release(False)
        self.assertEqual(result['status'], 'PASS_VALIDATE_ONLY')
        self.m.load_wrapper.assert_called_once_with(b'')

if __name__ == '__main__': unittest.main()
