"""Functional-only caller DATA and FD-state tests; UNRUN, no real root/fork/signals."""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('test_install_caller',HERE/'prepare_and_exec.py')
caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)


class CallerData(unittest.TestCase):
    def setUp(self):
        self.nonce='a'*64;self.profile='b'*64
        self.root={'pid':101,'birth':'11'};self.keeper={'pid':102,'birth':'12','direct_wait_status':0}
        self.installer={'pid':103,'birth':'13','pidfd_terminal':True,'keeper_direct_wait_status':0}
        self.observed={'root_parent':{'pid':101,'birth':'11'},'keeper':{'pid':102,'birth':'12'},'installer':{'pid':103,'birth':'13'}}
        self.closure=(caller.BASE/'root-install-source-10'/'SOURCE-CLOSURE.json').read_bytes()
        self.assertEqual(hashlib.sha256(self.closure).hexdigest(),caller.CLOSURE_SHA)
        files=[{'name':r['name'],'sha256':r['sha256']} for r in json.loads(self.closure)['files']]
        proof={'nonce':self.nonce,'source_closure_sha256':caller.CLOSURE_SHA,'native_release':False,'native_currentfree':None,
               'global_descendants':'UNKNOWN','install_proof':{'files':files}}
        result={'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','authority':None,'lease_disposition':'HELD','nonce':self.nonce,'root_parent':self.root,'stdout_capture':{'device':8,'inode':9},'native_release':False,'native_currentfree':None,'proof':proof,
                'terminal_evidence':{'keeper':self.keeper,'installer':self.installer}}
        common={'scope':'ROOT_CODE_INSTALL_ONLY','nonce':self.nonce,'profile_sha256':self.profile,'native_release':False,'native_currentfree':None,'root_parent':self.root}
        self.full=dict(common,record_type='ROOT_INSTALL_FULL_DATA_V1',result=result)
        self.final=dict(common,record_type='ROOT_INSTALL_DISPOSITION_DATA_V1',full_sha256=caller.digest(caller.canon(self.full)),lease_disposition='VERIFIED_CLOSED',outcome='COMPLETE')
        self.request={'nonce':self.nonce,'profile_sha256':self.profile}
    def parse(self,full=None,final=None,observed=None,status=0):
        raw=caller.canon(self.full if full is None else full)+caller.canon(self.final if final is None else final)
        with mock.patch.object(caller,'read',return_value=self.closure):
            return caller.parse_captured_data(raw,self.request,self.observed if observed is None else observed,status,{'device':8,'inode':9})
    def test_two_records_and_separate_observed_roles(self):
        result=self.parse();self.assertEqual(result['lease_disposition'],'VERIFIED_CLOSED')
    def test_missed_actual_role_stays_unknown(self):
        with self.assertRaises(ValueError):self.parse(observed={'root_parent':self.observed['root_parent']})
    def test_full_hash_mismatch_and_unknown_close_refused(self):
        final=dict(self.final,full_sha256='c'*64)
        with self.assertRaises(ValueError):self.parse(final=final)
        final=dict(self.final,outcome='UNKNOWN')
        with self.assertRaises(ValueError):self.parse(final=final)
    def test_nonzero_sudo_wait_and_short_data_refused(self):
        with self.assertRaises(ValueError):self.parse(status=256)
        with self.assertRaises(ValueError):caller.parse_captured_data(caller.canon(self.full),self.request,self.observed,0,{'device':8,'inode':9})
    def test_producer_capture_must_match_caller_inode(self):
        self.full['result']['stdout_capture']['inode']=10
        self.final['full_sha256']=caller.digest(caller.canon(self.full))
        with self.assertRaises(ValueError):self.parse()
    def test_installer_terminal_must_be_real_boolean(self):
        self.full['result']['terminal_evidence']['installer']['pidfd_terminal']=1
        self.final['full_sha256']=caller.digest(caller.canon(self.full))
        with self.assertRaises(ValueError):self.parse()
    def test_roles_are_observed_only_within_the_supplied_tree(self):
        def row(pid,ppid,uid,pgrp):return {'pid':pid,'ppid':ppid,'uid':uid,'pgrp':pgrp,'birth':str(pid)}
        root=row(101,100,0,90);keeper=row(102,101,0,90);installer=row(103,102,0,103)
        tree={100:(row(100,99,1000,90),b'sudo'),101:(root,b'python\0-c\0boot\0'),102:(keeper,b'python\0-c\0boot\0'),103:(installer,b'python\0-c\0wait\0')}
        got=caller.identify_roles(tree,100,'boot','wait')
        self.assertEqual(got,{'root_parent':root,'keeper':keeper,'installer':installer})
        tree.pop(103);self.assertNotIn('installer',caller.identify_roles(tree,100,'boot','wait'))


class FDDisposition(unittest.TestCase):
    def test_uncertain_close_is_consumed_and_never_retried(self):
        record={'fd':55,'historical_fd':None,'state':'OWNED'}
        with mock.patch.object(caller,'OWNED',[record]),mock.patch.object(caller.signal,'pthread_sigmask',return_value=set()), \
             mock.patch.object(caller.os,'close',side_effect=InterruptedError('uncertain')) as close:
            with self.assertRaises(InterruptedError):caller.owned_close(record)
            self.assertEqual(record['state'],'CLOSURE_UNKNOWN');self.assertIsNone(record['fd'])
            with self.assertRaises(ValueError):caller.owned_close(record)
            close.assert_called_once_with(55)


if __name__=='__main__':unittest.main()
