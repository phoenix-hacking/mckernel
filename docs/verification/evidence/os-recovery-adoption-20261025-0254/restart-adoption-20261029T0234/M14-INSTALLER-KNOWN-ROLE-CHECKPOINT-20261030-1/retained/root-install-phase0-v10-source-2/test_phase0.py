"""Source-only mocked tests: no root, ioctl, process creation or native work."""
import importlib.util
import pathlib
import stat
import struct
import types
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('phase0_under_test', str(pathlib.Path(__file__).with_name('phase0.py')))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class FakeOS:
    O_WRONLY=1; O_CREAT=2; O_EXCL=4; O_NOFOLLOW=8; O_CLOEXEC=16; O_RDONLY=32; O_APPEND=64; O_RDWR=128
    def __init__(self):
        self.events=[]
        self.flags=0
        self.payload=b''
        self.st=types.SimpleNamespace(st_dev=12, st_ino=34, st_uid=0, st_nlink=1, st_mode=stat.S_IFREG|0o600)
    def open(self,name,flags,mode=0,dir_fd=None):
        self.events.append(('open',name,flags))
        return 3 if flags & self.O_WRONLY else 4
    def fchmod(self,fd,mode): self.events.append(('chmod',fd,mode))
    def fstat(self,fd): self.events.append(('fstat',fd));return self.st
    def write(self,fd,data): self.events.append(('write',fd));self.payload+=bytes(data);return len(data)
    def fsync(self,fd): self.events.append(('fsync',fd))
    def close(self,fd): self.events.append(('close',fd))
    def stat(self,name,dir_fd=None,follow_symlinks=False): self.events.append(('named',name));return self.st


class FakeIoctl:
    def __init__(self,fs): self.fs=fs
    def ioctl(self,fd,op,data,mutate=False):
        self.fs.events.append(('ioctl',fd,op))
        if op==p.GETFLAGS:
            data[:]=struct.pack('I',self.fs.flags)
        elif op==p.SETFLAGS:
            self.fs.flags=struct.unpack('I',data)[0]
        else:
            raise AssertionError('unexpected ioctl')


class FakeInstall:
    def __init__(self,fs,readbacks=None): self.fs=fs;self.readbacks=readbacks
    def read_stable(self,fd,limit):
        self.fs.events.append(('readback',fd))
        return self.fs.payload if self.readbacks is None else next(self.readbacks)
    def root_file(self,fd):
        self.fs.events.append(('root_file',fd))
        if not self.fs.flags & p.IMMUTABLE:raise AssertionError('not immutable')


class Phase0Custody(unittest.TestCase):
    def setUp(self):
        p.HELD=[]
        p.WRITERS=[]

    def test_writer_closed_before_immutable_and_readback(self):
        fs=FakeOS();install=FakeInstall(fs)
        with mock.patch.object(p,'os',fs), mock.patch.object(p,'fcntl',FakeIoctl(fs)), mock.patch.object(p,'writer_event'), mock.patch.object(p.signal,'pthread_sigmask',return_value=set()):
            fd,sha=p.immutable_file(9,'start-intent.json',b'actual',install)
        self.assertEqual(fd,4)
        self.assertEqual(sha,p.digest(b'actual'))
        close=fs.events.index(('close',3))
        seal=fs.events.index(('ioctl',4,p.SETFLAGS))
        reads=[i for i,e in enumerate(fs.events) if e==('readback',4)]
        self.assertLess(close,reads[0]);self.assertLess(reads[0],seal);self.assertLess(seal,reads[-1])
        self.assertEqual(len(reads),2)

    def test_changed_postseal_readback_rejected(self):
        fs=FakeOS();install=FakeInstall(fs,iter((b'actual',b'drift')))
        with mock.patch.object(p,'os',fs), mock.patch.object(p,'fcntl',FakeIoctl(fs)), mock.patch.object(p,'writer_event'), mock.patch.object(p.signal,'pthread_sigmask',return_value=set()):
            with self.assertRaisesRegex(ValueError,'final readback'):
                p.immutable_file(9,'host-custody.json',b'actual',install)

    def test_close_failure_is_unknown_and_never_retried(self):
        class CloseFails(FakeOS):
            def close(self,fd):
                self.events.append(('close',fd))
                raise OSError('unknown close disposition')
        fs=CloseFails();install=FakeInstall(fs)
        with mock.patch.object(p,'os',fs), mock.patch.object(p,'fcntl',FakeIoctl(fs)), mock.patch.object(p,'writer_event') as journal, mock.patch.object(p.signal,'pthread_sigmask',return_value=set()):
            with self.assertRaisesRegex(OSError,'unknown close disposition'):
                p.immutable_file(9,'intent.json',b'actual',install)
        self.assertEqual(fs.events.count(('close',3)),1)
        self.assertEqual(p.WRITERS[-1]['state'],'CLOSE_UNKNOWN')
        self.assertTrue(any(call.args[0]['state']=='RECEIPT_WRITER_DISPOSITION_UNKNOWN' for call in journal.call_args_list))
        self.assertFalse(any(event[0]=='open' and event[2]&fs.O_RDONLY for event in fs.events))

    def test_write_failure_retains_registered_writer(self):
        class WriteFails(FakeOS):
            def write(self,fd,data):raise OSError('write failed')
        fs=WriteFails();install=FakeInstall(fs)
        with mock.patch.object(p,'os',fs), mock.patch.object(p,'fcntl',FakeIoctl(fs)), mock.patch.object(p,'writer_event'), mock.patch.object(p.signal,'pthread_sigmask',return_value=set()):
            with self.assertRaisesRegex(OSError,'write failed'):
                p.immutable_file(9,'intent.json',b'actual',install)
        self.assertEqual(p.WRITERS[-1]['state'],'OPEN')
        self.assertIn(3,p.HELD)
        self.assertNotIn(('close',3),fs.events)

    def test_lease_open_registers_before_stops_resume(self):
        fs=FakeOS()
        def mask(how,values):
            if how==p.signal.SIG_SETMASK:
                self.assertEqual(p.WRITERS[-1]['state'],'OPEN')
                self.assertIn(p.WRITERS[-1]['fd'],p.HELD)
            fs.events.append(('mask',how))
            return set()
        with mock.patch.object(p,'os',fs), mock.patch.object(p.signal,'pthread_sigmask',side_effect=mask):
            record=p._tracked_open(9,'lease',fs.O_RDWR|fs.O_CREAT|fs.O_EXCL,0o600)
        self.assertEqual(record['name'],'lease')
        self.assertEqual(record['state'],'OPEN')
        self.assertEqual(fs.events[0],('mask',p.signal.SIG_BLOCK))
        self.assertEqual(fs.events[-1],('mask',p.signal.SIG_SETMASK))

    def test_extra_or_missing_admission_fields_rejected(self):
        with self.assertRaisesRegex(ValueError,'admission schema'):
            p.run({'nonce':'0'*64},None,None,None,None,b'',b'',b'',{})

    def test_unknown_native_state_cannot_be_promoted(self):
        names = ('nonce outer_pid outer_birth one_shot_admission_id operation_parent code_parent_parent '
                 'deadline_boot_ns deadline_mono_ns utc_cap_ns phase1_deadline_boot_ns receipt_expires_boot_ns '
                 'weekly_used_percent weekly_observed_utc_ns service_status host_floor_bytes scratch_path '
                 'scratch_floor_bytes min_mem_available_bytes join_capture_reserve_ns term_grace_ns kill_grace_ns '
                 'join_grace_ns retire_operation_only owner_release owner_release_sha256 profile_sha256 '
                 'native12 scratch21 mutex27_4 v2_birth retained_2gib_bytes '
                 'native_currentfree no_unlisted_later_operation').split()
        req = dict.fromkeys(names)
        req.update(nonce='0'*64, one_shot_admission_id='1'*64, native12='HELD', scratch21='HELD',
                   mutex27_4='HELD', v2_birth=None, retained_2gib_bytes=2147483648,
                   native_currentfree=True, no_unlisted_later_operation='UNKNOWN')
        install=types.SimpleNamespace(hex64=lambda value: isinstance(value,str) and len(value)==64)
        issuer=mock.Mock()
        with mock.patch.object(p.os,'getuid',return_value=0), mock.patch.object(p.os,'geteuid',return_value=0), mock.patch.object(p.os,'mkdir') as mkdir:
            with self.assertRaisesRegex(ValueError,'unknown historical ownership'):
                p.run(req,install,issuer,None,None,b'',b'',b'',{})
            mkdir.assert_not_called()
            issuer.require_outer_ancestor.assert_not_called()

    def test_nan_cannot_be_serialized_into_receipt(self):
        with self.assertRaises(ValueError):
            p.canonical({'weekly_used_percent':float('nan')})


if __name__=='__main__':
    unittest.main()
