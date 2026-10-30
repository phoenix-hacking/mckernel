"""Mocked stdout/custody DATA regressions; no privileged or process actions."""
import contextlib
import importlib.util
import io
import json
import pathlib
import stat
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('data_output_fixture',str(pathlib.Path(__file__).with_name('data_output.py')))
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


def sample():
    return {'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':'a'*64,'authority':None,
            'native_release':False,'native_currentfree':None,'lease_disposition':'HELD',
            'proof':{'nonce':'a'*64,'native_release':False,'native_currentfree':None,'global_descendants':'UNKNOWN',
                     'keeper':{'pid':321,'birth':'123'},'installer':{'pid':322,'birth':'124','pgid':322},'installer_wait_status':0},
            'independent_verification':{'checked':True},
            'terminal_evidence':{'keeper':{'pid':321,'birth':'123','direct_wait_status':0},
                                 'installer':{'pid':322,'birth':'124','pidfd_terminal':True,'keeper_direct_wait_status':0}}}


class DataOutput(unittest.TestCase):
    def setUp(self):
        d._STATE='NEW';d._HANDOFF=None
        self.caps={'boot_ns':10000,'mono_ns':10000,'utc_ns':10000}
        self.st=type('Stat',(),{'st_mode':stat.S_IFREG|0o600,'st_nlink':1,'st_dev':9,'st_ino':10,'st_uid':1000,'st_gid':1000})()
        self.proc='323 (root) S '+'0 '*18+'9876\n'

    @contextlib.contextmanager
    def environment(self,write_effect=None,fsync_effect=None):
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(d.os,'getuid',return_value=0))
            stack.enter_context(mock.patch.object(d.os,'geteuid',return_value=0))
            stack.enter_context(mock.patch.object(d.os,'getpid',return_value=323))
            stack.enter_context(mock.patch('builtins.open',side_effect=lambda *a,**k:io.StringIO(self.proc)))
            stack.enter_context(mock.patch.object(d.os,'fstat',return_value=self.st))
            stack.enter_context(mock.patch.object(d.fcntl,'fcntl',return_value=d.os.O_WRONLY))
            stack.enter_context(mock.patch.object(d.time,'clock_gettime_ns',return_value=1))
            stack.enter_context(mock.patch.object(d.time,'monotonic_ns',return_value=1))
            stack.enter_context(mock.patch.object(d.time,'time_ns',return_value=1))
            write=stack.enter_context(mock.patch.object(d.os,'write',side_effect=write_effect or (lambda fd,data:len(data))))
            fsync=stack.enter_context(mock.patch.object(d.os,'fsync',side_effect=fsync_effect))
            close=stack.enter_context(mock.patch.object(d.os,'close'))
            yield write,fsync,close

    def test_exact_full_and_final_wire_records(self):
        with self.environment() as (write,fsync,close):
            sha=d.publish_full('a'*64,'b'*64,sample(),self.caps)
            d.publish_disposition('a'*64,'b'*64,sha,'VERIFIED_CLOSED','COMPLETE',self.caps)
        full={'record_type':'ROOT_INSTALL_FULL_DATA_V1','scope':'ROOT_CODE_INSTALL_ONLY','nonce':'a'*64,
              'profile_sha256':'b'*64,'root_parent':{'pid':323,'birth':'9876'},'native_release':False,
              'native_currentfree':None,'result':sample()}
        final={'record_type':'ROOT_INSTALL_DISPOSITION_DATA_V1','scope':'ROOT_CODE_INSTALL_ONLY',
               'nonce':'a'*64,'profile_sha256':'b'*64,'root_parent':{'pid':323,'birth':'9876'},
               'full_sha256':sha,'lease_disposition':'VERIFIED_CLOSED','outcome':'COMPLETE',
               'native_release':False,'native_currentfree':None}
        wire=lambda row:(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
        self.assertEqual(write.call_args_list,[mock.call(1,wire(full)),mock.call(1,wire(final))])
        self.assertEqual(fsync.call_args_list,[mock.call(1),mock.call(1)])
        close.assert_not_called()

    def test_short_full_write_is_unknown_and_never_retried(self):
        with self.environment(write_effect=lambda fd,data:len(data)-1) as (write,fsync,close):
            with self.assertRaisesRegex(OSError,'short DATA write'):
                d.publish_full('a'*64,'b'*64,sample(),self.caps)
            self.assertEqual(d._STATE,'UNKNOWN')
            with self.assertRaises(ValueError):d.publish_full('a'*64,'b'*64,sample(),self.caps)
            write.assert_called_once();fsync.assert_not_called();close.assert_not_called()

    def test_failed_fsync_leaves_full_unknown_and_never_closes(self):
        with self.environment(fsync_effect=OSError('fsync failure')) as (write,fsync,close):
            with self.assertRaisesRegex(OSError,'fsync failure'):d.publish_full('a'*64,'b'*64,sample(),self.caps)
            self.assertEqual(d._STATE,'UNKNOWN');write.assert_called_once();fsync.assert_called_once();close.assert_not_called()

    def test_postclose_short_write_retains_unknown_without_retry(self):
        calls=[]
        def write(fd,data):
            calls.append(data)
            return len(data) if len(calls)==1 else len(data)-1
        with self.environment(write_effect=write) as (out,fsync,close):
            sha=d.publish_full('a'*64,'b'*64,sample(),self.caps)
            with self.assertRaises(OSError):d.publish_disposition('a'*64,'b'*64,sha,'VERIFIED_CLOSED','UNKNOWN',self.caps)
            self.assertEqual(d._STATE,'UNKNOWN')
            with self.assertRaises(ValueError):d.publish_disposition('a'*64,'b'*64,sha,'VERIFIED_CLOSED','UNKNOWN',self.caps)
            self.assertEqual(out.call_count,2);close.assert_not_called()

    def test_cap_expires_during_flush_so_full_is_unknown(self):
        with self.environment() as (out,fsync,close):
            with mock.patch.object(d.time,'clock_gettime_ns',side_effect=[1,10001]):
                with self.assertRaises(TimeoutError):d.publish_full('a'*64,'b'*64,sample(),self.caps)
            self.assertEqual(d._STATE,'UNKNOWN');out.assert_called_once();fsync.assert_called_once();close.assert_not_called()

    def test_impossible_close_outcome_is_rejected(self):
        with self.environment():
            sha=d.publish_full('a'*64,'b'*64,sample(),self.caps)
            with self.assertRaises(ValueError):d.publish_disposition('a'*64,'b'*64,sha,'CLOSURE_UNKNOWN','COMPLETE',self.caps)

    def test_float_alias_in_role_proof_is_rejected(self):
        result=sample();result['proof']['keeper']['pid']=321.0
        with self.environment():
            with self.assertRaises(ValueError):d.publish_full('a'*64,'b'*64,result,self.caps)

if __name__=='__main__':unittest.main()
