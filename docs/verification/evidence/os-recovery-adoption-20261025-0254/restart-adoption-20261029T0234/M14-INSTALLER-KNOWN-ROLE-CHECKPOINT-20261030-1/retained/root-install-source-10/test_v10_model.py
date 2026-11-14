"""Functional-only synthetic v9 correction tests. UNRUN; no root operations."""
import hashlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base/'package'))
import install_completion as completion
import install_issuer as issuer
from ownership_latch import CustodyLatch


class ReserveCases(unittest.TestCase):
    def test_full_timeout_and_positive_reserve_required_at_go(self):
        reserve=1000000000
        with patch.object(completion,'remaining',return_value=66000000000):
            with self.assertRaises(ValueError):issuer.require_full_go_reserve({},reserve)
        with patch.object(completion,'remaining',return_value=66000000001):
            issuer.require_full_go_reserve({},reserve)
        with self.assertRaises(TimeoutError):issuer.remaining_timeout_budget(1,60000000001)


class DurableHandoffCases(unittest.TestCase):
    def setup_install(self,events):
        def ident(st):return {'device':st.st_dev,'inode':st.st_ino}
        def read_stable(fd,limit):
            os.lseek(fd,0,os.SEEK_SET);return os.read(fd,limit+1)
        return types.SimpleNamespace(ident=ident,sha=lambda b:hashlib.sha256(b).hexdigest(),read_stable=read_stable,
            write_all=lambda fd,data:os.write(fd,data),journal=lambda fd,event:events.append(event['state']))
    def run_handoff(self,short):
        events=[];result={'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':'a'*64,'proof':'retained'}
        latch=CustodyLatch('HELD');latch.retain(999);install=self.setup_install(events)
        real_fstat=os.fstat;real_write=os.write
        def fstat(fd):
            st=real_fstat(fd)
            return types.SimpleNamespace(st_mode=st.st_mode,st_uid=0,st_nlink=st.st_nlink,st_dev=st.st_dev,st_ino=st.st_ino)
        def write(fd,data):return (len(data)-1 if short else len(data)) if fd==1 else real_write(fd,data)
        with tempfile.TemporaryDirectory() as directory:
            root=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
            try:
                with patch.object(completion,'need_time'),patch('signal.pthread_sigmask',return_value=set()),\
                     patch.object(completion.os,'fstat',side_effect=fstat),patch.object(completion.os,'write',side_effect=write):
                    if short:
                        with self.assertRaises(OSError):completion.publish_full_result(install,latch,9,root,'a'*64,result,{})
                    else:completion.publish_full_result(install,latch,9,root,'a'*64,result,{})
                path=Path(directory)/('INSTALL-RESULT-'+'a'*64+'.json')
                self.assertEqual(json.loads(path.read_bytes()),result)
            finally:os.close(root)
        self.assertIn(999,latch.retained);self.assertIn('RESULT_DURABLE',events)
        return events
    def test_short_stdout_keeps_durable_proof_and_lease(self):
        self.assertNotIn('RESULT_HANDED_OFF',self.run_handoff(True))
    def test_complete_stdout_follows_durable_proof(self):
        events=self.run_handoff(False)
        self.assertLess(events.index('RESULT_DURABLE'),events.index('RESULT_HANDED_OFF'))


class KnownRoleModelCases(unittest.TestCase):
    def setUp(self):
        self.pins={'issuer_sha256':'1'*64,'completion_sha256':'2'*64,'timeout_proof_sha256':completion.TIMEOUT_PROOF_SHA256,'review_sha256':'9'*64}
        self.install=types.SimpleNamespace(MAX_SOURCE=4096,CLOSURE_SHA256='c'*64,root_file=lambda fd:None,
          sha=lambda b:hashlib.sha256(b).hexdigest(),unique=lambda pairs:dict(pairs),
          hex64=lambda value:type(value) is str and len(value)==64)
        self.template={'nonce':'a'*64,'installer_sha256':'d'*64,'interpreter':{'sha256':'e'*64}}
        self.intent={'wait_literal_sha256':'f'*64,'timeout_exe_sha256':completion.TIMEOUT_BINARY_SHA256}
        self.row={'version':1,'record_type':'ROOT_INSTALL_CREATION_MODEL_APPROVAL_V1','scope':'ROOT_CODE_INSTALL_ONLY',
          'nonce':'a'*64,'native_release':False,'native_currentfree':None,'global_descendants':'UNKNOWN',
          'status':'APPROVED_KNOWN_ROLE_MODEL','model_sha256':completion.CREATION_MODEL_SHA256,
          'toolproof_sha256':completion.TIMEOUT_PROOF_SHA256,'issuer_sha256':'1'*64,'completion_sha256':'2'*64,
          'installer_sha256':'d'*64,'wait_sha256':'f'*64,'timeout_sha256':completion.TIMEOUT_BINARY_SHA256,
          'runtime_sha256':'e'*64,'source_closure_sha256':'c'*64,'review_sha256':'9'*64,
          'trusted_platform':'PINNED_TIMEOUT_CPYTHON_LIBC_KERNEL'}
    def test_reviewed_exact_known_roles_do_not_require_new_root_holder(self):
        with patch.object(completion,'SOURCE_PINS',self.pins):
            result=completion.verify_creation_model_value(self.install,{'creation_model_approval':self.row},self.template,self.intent)
        self.assertEqual(result['global_descendants'],'UNKNOWN')
        self.assertNotIn('holder_pid',result)
    def test_wrong_timeout_binary_or_global_claim_fails(self):
        with patch.object(completion,'SOURCE_PINS',self.pins):
            self.row['timeout_sha256']='0'*64
            with self.assertRaises(ValueError):completion.verify_creation_model_value(self.install,{'creation_model_approval':self.row},self.template,self.intent)
            self.row['timeout_sha256']=completion.TIMEOUT_BINARY_SHA256;self.row['global_descendants']='EMPTY'
            with self.assertRaises(ValueError):completion.verify_creation_model_value(self.install,{'creation_model_approval':self.row},self.template,self.intent)
    def test_unverified_toolproof_pin_fails_even_with_matching_receipt(self):
        self.pins['timeout_proof_sha256']='0'*64
        with patch.object(completion,'SOURCE_PINS',self.pins):
            with self.assertRaisesRegex(ValueError,'toolproof'):
                completion.verify_creation_model_value(self.install,{'creation_model_approval':self.row},self.template,self.intent)
    def test_model_binds_actual_timeout_source_proof(self):
        raw=(base/'PROCESS-CREATION-MODEL.json').read_bytes();proof=(base/'TIMEOUT-PROOF.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),completion.CREATION_MODEL_SHA256)
        self.assertEqual(hashlib.sha256(proof).hexdigest(),completion.TIMEOUT_PROOF_SHA256)
        model=json.loads(raw);self.assertEqual(len(model['roles']),3);self.assertEqual(len(model['creation_sites']),2)

if __name__=='__main__':unittest.main()
