"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure approval/refusal fixtures. No root/Docker/compiler/subprocess operation.
Dispatcher must grant the one CPU0 fixture execution separately.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

p = load('bfd_publisher_approval_correction1', HERE / 'publish_bfd_release.approval-correction1.NOT-RELEASED.py')
owner = load('unchanged_accepted_bfd_owner', HERE.parent / 'compile_image_owner.py')

class ApprovalFixtures(unittest.TestCase):
    def setUp(self):
        context = tempfile.TemporaryDirectory(prefix='publisher-fixture-', dir=str(HERE))
        self.addCleanup(context.cleanup)
        self.root = Path(context.name)
        self.clock = patch.object(owner, '_boottime_ns', return_value=10**12)
        self.memory = patch.object(owner, '_mem_available', return_value=24 << 30)
        self.clock.start()
        self.memory.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.memory.stop)
        self.profile = json.loads((HERE.parent / 'COMPILE-PROFILE.json').read_text())
        self.request = json.loads((HERE.parent / 'compile-request.PREPARED.json').read_text())
        self.facts = {'schema':'mckernel.m15-bfd-dual-container-admission.v1', 'operation':self.profile['operation'],
            'request_core_sha256':owner._request_core_hash(self.request), 'profile_sha256':p.PROFILE_SHA,
            'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'observed_boottime_ns':10**12, 'MemAvailable':24 << 30,
            'capacity_verdict':'PASS_DUAL_CONTAINER_COMPILE_CPU6_2G'}
        self.bindings = {'owner_sha256':p.OWNER_SHA, 'helper_sha256':p.HELPER_SHA, 'profile_sha256':p.PROFILE_SHA,
                         'publisher_sha256':hashlib.sha256((HERE / 'publish_bfd_release.approval-correction1.NOT-RELEASED.py').read_bytes()).hexdigest()}
        self.source = {'schema':'mckernel.m15-bfd-owner-source-approval.v1', 'scope':p.SCOPE, 'status':'PASS',
            'reviewer':p.REVIEWER, 'implementation_ownership':False,
            'bindings':{k:self.bindings[k] for k in ('owner_sha256','helper_sha256','profile_sha256')}}
        self.refs = {'query':self.write('admission-candidate.json',self.facts),
                     'request':self.write('unreleased-request.json',self.request),
                     'source_review':self.write('source-approval.json',self.source),
                     'joined':self.write('query-wholejoin.json',{'returncode':0,'direct_child_joined':True,
                         'group_absent':True,'closed_streams':True,'error':None,'retirement_error':None})}
        self.template = json.loads((HERE.parent / 'ROOT-RELEASE.TEMPLATE.json').read_text())
        self.expected = p.expected_payload(self.root,self.profile,self.request,self.facts,self.bindings,self.refs,self.template)
        self.payload = copy.deepcopy(self.expected)
        self.payload_ref = self.write('exact-payload.json',self.payload)
        self.execution = {'schema':'mckernel.m15-bfd-execution-approval.v1','scope':p.SCOPE,'status':'PASS',
            'reviewer':p.REVIEWER,'implementation_ownership':False,'bindings':self.bindings.copy(),
            'request_core_sha256':self.facts['request_core_sha256'],
            'source_review_sha256':self.refs['source_review']['sha256'],'payload_sha256':self.payload_ref['sha256']}
        self.execution_ref = self.write('execution-approval.json',self.execution)
        self.fresh_calls = []

    def write(self, name, document):
        path = self.root / name
        raw = p.document_bytes(document)
        path.write_bytes(raw)
        return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}

    def fresh(self, facts):
        self.fresh_calls.append(facts)
        return owner._fresh_compile_resources(facts)

    def authorize(self, source=None, execution=None, payload=None, expected=None, ref=None):
        return p.authorize(self.source if source is None else source,
                           self.execution if execution is None else execution,
                           self.payload if payload is None else payload,
                           self.expected if expected is None else expected,
                           self.payload_ref if ref is None else ref,self.fresh)

    def assert_unpublished(self):
        for name in ('ROOT-ADMISSION.json','ROOT-RELEASE.json','compile-request.RELEASED.json'):
            self.assertFalse((self.root / name).exists())

    def test_positive_exact_digest_bound_pass_and_real_ttl(self):
        source = p.read_bound_json(**{'path':self.refs['source_review']['path'],'expected':self.refs['source_review']['sha256']})
        execution = p.read_bound_json(self.execution_ref['path'],self.execution_ref['sha256'])
        payload = p.read_bound_json(self.payload_ref['path'],self.payload_ref['sha256'])
        answer = self.authorize(source=source,execution=execution,payload=payload)
        self.assertEqual(answer,self.expected['publication'])
        self.assertEqual(self.fresh_calls,[self.facts])
        self.assert_unpublished()

    def test_hash_matching_fail_source_or_execution_refuses(self):
        for which in ('source','execution'):
            with self.subTest(which=which):
                document = copy.deepcopy(self.source if which=='source' else self.execution)
                document['status']='FAIL'
                ref = self.write(which+'-FAIL.json',document)
                actual = p.read_bound_json(ref['path'],ref['sha256'])
                with self.assertRaisesRegex(ValueError,'PASS required'):
                    self.authorize(**{which:actual})
        self.assertEqual(self.fresh_calls,[])
        self.assert_unpublished()

    def test_null_or_placeholder_approval_refuses(self):
        for source, execution in ((None,self.execution),(self.source,None),({},self.execution),(self.source,{})):
            with self.subTest(source=source,execution=execution), self.assertRaises(ValueError):
                p.authorize(source,execution,self.payload,self.expected,self.payload_ref,self.fresh)
        for which in ('source','execution'):
            changed = copy.deepcopy(self.source if which=='source' else self.execution)
            changed['_template_only_no_authority']=True
            with self.subTest(which=which), self.assertRaises(ValueError):
                self.authorize(**{which:changed})
        self.assertEqual(self.fresh_calls,[])
        self.assert_unpublished()

    def test_wrong_execution_payload_body_refuses_even_with_matching_digest_approval(self):
        changed = copy.deepcopy(self.payload)
        changed['owner_run_argv'][2]='7'
        ref = self.write('wrong-payload.json',changed)
        execution = dict(self.execution,payload_sha256=ref['sha256'])
        with self.assertRaisesRegex(ValueError,'execution payload differs'):
            self.authorize(execution=execution,payload=p.read_bound_json(ref['path'],ref['sha256']),ref=ref)
        self.assertEqual(self.fresh_calls,[])
        self.assert_unpublished()

    def test_wrong_payload_digest_and_changed_bytes_refuse(self):
        with self.assertRaisesRegex(ValueError,'payload digest differs'):
            self.authorize(execution=dict(self.execution,payload_sha256='0'*64))
        Path(self.payload_ref['path']).write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'digest/identity differs'):
            p.read_bound_json(self.payload_ref['path'],self.payload_ref['sha256'])
        self.assertEqual(self.fresh_calls,[])
        self.assert_unpublished()

    def test_wrong_source_profile_publisher_or_request_binding_refuses(self):
        for key in self.bindings:
            changed = copy.deepcopy(self.execution)
            changed['bindings'][key]='0'*64
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'approval differs'):
                self.authorize(execution=changed)
        for key in ('request_core_sha256','source_review_sha256'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'approval differs'):
                self.authorize(execution=dict(self.execution,**{key:'0'*64}))
        changed = copy.deepcopy(self.source)
        changed['bindings']['profile_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'source/profile/helper differs'):
            self.authorize(source=changed)
        self.assertEqual(self.fresh_calls,[])
        self.assert_unpublished()

    def test_expired_genuine_observation_refuses_before_publication(self):
        self.facts['observed_boottime_ns']=10**12-120000000001
        self.refs['query']=self.write('expired-admission.json',self.facts)
        expected = p.expected_payload(self.root,self.profile,self.request,self.facts,self.bindings,self.refs,self.template)
        ref = self.write('expired-payload.json',expected)
        execution = dict(self.execution,payload_sha256=ref['sha256'])
        with self.assertRaisesRegex(owner.OwnerError,'expired or wrong boot'):
            self.authorize(execution=execution,payload=expected,expected=expected,ref=ref)
        self.assertEqual(len(self.fresh_calls),1)
        self.assert_unpublished()

    def test_predicted_document_bytes_match_accepted_owner_serializer(self):
        for name,row in self.expected['publication'].items():
            path = self.root / ('serializer-only-'+name+'.json')
            owner._exclusive_json(path,row['document'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),row['reference']['sha256'])
        self.assert_unpublished()

    def test_release_template_fail_or_null_status_refuses(self):
        for status in ('FAIL',None):
            with self.subTest(status=status), self.assertRaisesRegex(ValueError,'release status required'):
                p.expected_payload(self.root,self.profile,self.request,self.facts,self.bindings,self.refs,
                                   dict(self.template,status=status))
        self.assertEqual(self.fresh_calls,[])
        self.assert_unpublished()

if __name__ == '__main__':
    assert os.sched_getaffinity(0)=={0}, 'dispatcher pure-fixture CPU0 grant required'
    with patch.object(owner.subprocess,'Popen',side_effect=AssertionError('subprocess forbidden')):
        with patch.object(owner._HOST_OWNER,'Docker',side_effect=AssertionError('Docker factory forbidden')):
            unittest.main(verbosity=2)
