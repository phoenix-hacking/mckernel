"""Pure source draft checks; no process, root, daemon or container operation."""
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

p=Path(__file__).with_name('daemon_image_parent.attempt2.py')
s=importlib.util.spec_from_file_location('parent_draft',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class DeadlineAndHold(unittest.TestCase):
    def test_overall_deadline_bounded(self):
        with mock.patch.object(m.time,'monotonic',return_value=1):
            self.assertEqual(m.validated_overall_deadline({'operation_deadline_monotonic':50}),50)
            for value in (None,False,0,-1,1,float('nan'),float('inf'),m.MONO_LIMIT+1):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    m.validated_overall_deadline({'operation_deadline_monotonic':value})
    def test_parent_gate_result_requires_complete_positive_proof(self):
        good={'utc':10,'boot':10,'mono':10,'weekly_observed_utc':9,'expiry_utc':20}
        with mock.patch.object(m,'parent_effect_gate',return_value=good):
            self.assertIs(m.parent_custody_gate({}),True)
        for value in (None,False,True,{}, {'utc':10}, dict(good,mono=float('nan')),dict(good,expiry_utc=10)):
            with self.subTest(value=value), mock.patch.object(m,'parent_effect_gate',return_value=value):
                with self.assertRaises(ValueError): m.parent_custody_gate({})
    def test_unbound_health_unconditionally_blocks_effect_gate(self):
        nonce='a'*32;sup={'pid':5,'ppid':1,'start':'10'}
        release={'schema':'mckernel.sdk13.daemon-image-readonly-release.attempt2.v1',
                 'operation':'ONE_DAEMON_METADATA_AND_ONE_EXACT_IMAGE_INSPECT',
                 'reader_sha256':m.READER_SHA,'image_argv':m.IMAGE_ARGV,'parent_as_bytes':536870912,
                 'image_as_bytes':536870912,'daemon_sample':'IN_PROCESS',
                 'image_process_group':'INHERIT_PARENT_GROUP','cpu':7,'query_count':1,'nonce':nonce,
                 'parent_sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'docker_sha256':m.DOCKER_SHA,
                 'gate_sha256':m.GATE_SHA,'custody_sha256':m.CUSTODY_SHA,
                 'capacity_supervisor':sup,'controller_identities':{'supervisor':sup},
                 'operation_deadline_monotonic':50}
        controls={'binding':{}}
        token={'release':[1]*10,'controls':[2]*10,'nonce':nonce}
        proc='x (x) S 1 '+'0 '*17+'10 0'
        with mock.patch.object(m,'OPERATION_DEADLINE',50), mock.patch.object(m.time,'monotonic',return_value=1), mock.patch.object(m.time,'clock_gettime',return_value=1), mock.patch.object(m,'bound_document',side_effect=[release,controls]), mock.patch.object(m,'verified_source',return_value=b'def check_controls(*args): pass\n'), mock.patch.object(m.signal,'sigpending',return_value=set()), mock.patch.object(m.os.path,'lexists',return_value=False), mock.patch.object(Path,'read_text',return_value=proc):
            with self.assertRaisesRegex(ValueError,'current controller health is not bound'):
                m.parent_effect_gate(token)

if __name__=='__main__': unittest.main(verbosity=2)
