"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure synthetic phase-reference tests; source bytes only, no runtime operations.
"""
import copy
import hashlib
from pathlib import Path
import unittest
import growth_recovery_validator as v

def r(name):return dict(path=name,bytes=1,sha256='0'*64)
class PhaseBindings(unittest.TestCase):
    def fixture(self):
        def source(name):
            p=Path(v.__file__).resolve().parent/name;raw=p.read_bytes()
            return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        recovery={k:r(k) for k in ('recovery_source','recovery_ofd_source','copy_review','actual_copy','retire_review','pidfd_retirement','close_review','actual_normal_close','qualified_online_postconditions','old_actual_joins','current_physical_acceptance')}
        recovery['recovery_source']=source('recover_growth_custody.py');recovery['recovery_ofd_source']=source('ofd_primitives.py')
        packet=dict(sources={'recover_growth_custody.py':recovery['recovery_source'],'ofd_primitives.py':recovery['recovery_ofd_source']},copy_review=recovery['copy_review'],qualified_postconditions=recovery['qualified_online_postconditions'],target=v.TARGET,phase='COPY_ONLY')
        packetref=r('packet')
        ready=dict(source_packet=packetref,data=dict(qualified_postconditions=recovery['qualified_online_postconditions'],consumed_copy=r('copy_marker')))
        retired=dict(source_packet=packetref,wall=10,data=dict(consumed_retire=r('retire_marker')))
        closed=dict(source_packet=packetref,wall=20,data=dict(consumed_close=r('close_marker')))
        docs=dict(actual_copy=ready,pidfd_retirement=retired,actual_normal_close=closed)
        def review(decision,payload):return dict(decision=decision,implementation_ownership=False,reviewer='/root/custody_release_review',payload_sha256=hashlib.sha256(v.canonical(payload)).hexdigest())
        docs['copy_review']=review('PASS_COPY_ONLY',{k:x for k,x in packet.items() if k!='copy_review'})
        commands={}
        for action,name in [('RETIRE','retire'),('CLOSE','close')]:
            payload=dict(action=action,author='/root',ready=recovery['actual_copy'],source_packet=packetref,target=v.TARGET,qualified_postconditions=recovery['qualified_online_postconditions'],expires_wall=30)
            if action=='RETIRE':payload.update(signal=9,target_pidfd_signal_count=1)
            else:payload.update(pidfd_exit=recovery['pidfd_retirement'],old_actual_joins=recovery['old_actual_joins'],current_fs_acceptance=recovery['current_physical_acceptance'])
            docs[name+'_review']=review('PASS_'+action+'_ONLY',payload)
            commands[name+'_marker']=dict(payload=payload,review=recovery[name+'_review'])
        stored=dict(packet=packet,copy_marker=dict(source_packet=packetref,copy_review=recovery['copy_review']),**commands)
        stored[recovery['recovery_ofd_source']['path']]=b'fake source bytes'
        return recovery,docs,stored
    def call(self,f):return v.phase_bindings(f[0],f[1],lambda ref,*_:f[2][ref['path']])
    def test_matching_packet_and_consumed_reviews_pass(self):self.assertEqual(self.call(self.fixture()),r('packet'))
    def test_unrelated_source_packet_or_cited_review_payload_rejected(self):
        cases=[(0,['recovery_source'],r('unrelated_source')),
               (2,['packet','sources','ofd_primitives.py'],r('unrelated_ofd')),
               (2,['packet','copy_review'],r('unrelated_review')),
               (2,['packet','qualified_postconditions'],r('unrelated_qualification')),
               (1,['copy_review','payload_sha256'],'1'*64),
               (2,['retire_marker','review'],r('unrelated_review')),
               (2,['retire_marker','payload','signal'],15),
               (1,['retire_review','payload_sha256'],'1'*64),
               (2,['close_marker','payload','ready'],r('other_ready')),
               (2,['close_marker','payload','source_packet'],r('other_packet')),
               (1,['close_review','payload_sha256'],'1'*64),
               (1,['actual_normal_close','source_packet'],r('other_packet'))]
        for index,path,value in cases:
            f=copy.deepcopy(self.fixture());target=f[index]
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            with self.subTest(path=path),self.assertRaises((ValueError,KeyError)):self.call(f)
    def test_missing_actual_consumed_phase_receipt_refused(self):
        f=self.fixture();del f[1]['actual_normal_close']['data']['consumed_close']
        with self.assertRaises(KeyError):self.call(f)
if __name__=='__main__':unittest.main(verbosity=2)
