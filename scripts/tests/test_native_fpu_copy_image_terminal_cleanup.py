"""Disposable nested transaction fixtures only; no root/Docker/live cleanup."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

def resolve_source(test_file, override=None):
    if override is not None:
        return Path(override).resolve(strict=True)
    return Path(test_file).resolve().parents[1] / 'native_fpu_copy_image_terminal_cleanup.py'


SOURCE = resolve_source(__file__, os.environ.get('NATIVE_FP_CLEANUP_TEST_SOURCE'))

class NestedCleanupTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('thin_cleanup_fixture',SOURCE)
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        m=self.m;m.ROOT=Path(self.temp.name);m.NAMESPACE=m.ROOT/'fixed-parent'/'fixed-case'
        m.NAMESPACE.mkdir(parents=True,mode=0o700);m.NAMESPACE.parent.chmod(0o700)
        for name in ('ATTEMPT','OUTPUT','EVIDENCE'):
            setattr(m,name,m.NAMESPACE/name.lower())
        for name in ('SHARED','MUTEX','PLAN','JOURNAL','CAPTURE','QUARANTINE','ROOT_LOCK'):
            setattr(m,name,m.ROOT/name.lower())
        m.ARCHIVE_NAMES=('common.archive','shared.archive')
        for path in (m.OUTPUT,m.EVIDENCE):path.mkdir(mode=0o700)
        m.TERMINAL=m.EVIDENCE/'owner-receipt.json';m.TERMINAL.write_bytes(b'fixture receipt');m.TERMINAL.chmod(0o600)
        (m.OUTPUT/'published.img').write_bytes(b'preserved image')
        m.NAMESPACE_BINDING=self.ns_binding();m.NAMESPACE_ANCESTRY=m.namespace_ancestry()
        m.ROOT_LOCK.touch(mode=0o644);m.ROOT_LOCK.chmod(0o644)
        m.ROOT_LOCK_BINDING=m.observe_identity(m.ROOT_LOCK)
        m.DEVICE=m.ROOT.stat().st_dev;m.BOOT_ID='fixture-boot';m.RELEASE={'fixture':True}
        m.OWNER_PID=123;m.OWNER_START='42';m.WAITER_PIDS=(124,125)
        m.CONTAINER='c'*64;m.CONTAINER_NAME='owned';m.OWNER_NONCE='n';m.EXPECTED_EXIT=0
        for p in (m.ATTEMPT,m.SHARED):p.write_bytes(('owned:'+str(p)).encode());p.chmod(0o600)
        m.RECORDS={p:(m.digest(p.read_bytes()),p.stat().st_ino,p.stat().st_size) for p in (m.ATTEMPT,m.SHARED)}
        m.DIRS={p:(p.stat().st_ino,p.stat().st_nlink) for p in (m.OUTPUT,m.EVIDENCE)}
        m.TERMINAL_SHA=m.digest(m.TERMINAL.read_bytes());m.TERMINAL_INODE=m.TERMINAL.stat().st_ino;m.TERMINAL_SIZE=m.TERMINAL.stat().st_size
        self.canary=m.ROOT/m.ATTEMPT.name;self.canary.write_bytes(b'ROOT basename canary');self.canary.chmod(0o600)
        self.canary_before=(self.canary.stat().st_ino,self.canary.read_bytes())
        self.present=True
        self.patch('validate_mount',lambda:None)
        self.patch('protected_files',lambda:None)
        self.patch('census',lambda:self.present)
        self.patch('docker',self.docker)
        self.patch('capture_logs',self.capture)
        original=m.Path.read_text
        def read_text(path,*a,**kw):
            if str(path)=='/proc/sys/kernel/random/boot_id':return m.BOOT_ID
            return original(path,*a,**kw)
        patch=mock.patch.object(m.Path,'read_text',read_text);patch.start();self.addCleanup(patch.stop)
    def ns_binding(self):
        p=self.m.NAMESPACE;s=p.lstat()
        return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
    def patch(self,name,value):
        patch=mock.patch.object(self.m,name,value);patch.start();self.addCleanup(patch.stop)
    def docker(self,args):
        self.assertEqual(args,['rm','--',self.m.CONTAINER]);self.present=False
        return self.m.CONTAINER.encode()
    def capture(self,present,execute=False,transaction=None):
        if execute and not self.m.CAPTURE.exists():transaction.create(self.m.CAPTURE.name,b'raw fixture logs')
    def transaction(self):
        tx=self.m.Transaction();self.addCleanup(tx.close);return tx
    def assert_canary(self):
        self.assertEqual((self.canary.stat().st_ino,self.canary.read_bytes()),self.canary_before)
    def test_nested_positive_exchange_release_replay_preserves_root_canary_outputs(self):
        m=self.m;before={p:p.read_bytes() for p in (m.ATTEMPT,m.SHARED)}
        tx=self.transaction();result=tx.run(True)
        self.assertEqual(result['status'],'PASS_EXECUTED')
        for p,archive in zip((m.ATTEMPT,m.SHARED),m.ARCHIVE_NAMES):
            self.assertFalse(p.exists());self.assertEqual((m.ROOT/archive).read_bytes(),before[p])
        self.assert_canary();self.assertEqual((m.OUTPUT/'published.img').read_bytes(),b'preserved image')
        self.assertEqual(m.TERMINAL.read_bytes(),b'fixture receipt')
        self.assertEqual(tx.run(True)['status'],'PASS_TERMINAL_REPLAY')
        plan=json.loads(m.PLAN.read_bytes());self.assertEqual(plan['records'][0][:2],[str(m.ATTEMPT),str(m.NAMESPACE)])
        self.assertEqual(plan['namespace']['ancestry'],m.NAMESPACE_ANCESTRY)
    def test_symlink_namespace_refuses_and_keeps_canary(self):
        m=self.m;m.NAMESPACE.rename(m.NAMESPACE.with_name('saved'));m.NAMESPACE.symlink_to(m.NAMESPACE.with_name('saved'),target_is_directory=True)
        with self.assertRaises((m.Refusal,OSError)):self.transaction()
        self.assert_canary()
    def test_replaced_namespace_refuses(self):
        m=self.m;m.NAMESPACE.rename(m.NAMESPACE.with_name('saved'));m.NAMESPACE.mkdir(mode=0o700)
        with self.assertRaises(m.Refusal):self.transaction()
        self.assert_canary()
    def test_namespace_mode_owner_device_and_ancestor_changes_refuse(self):
        m=self.m
        for field,value in [('mode',stat.S_IFDIR|0o755),('uid',999),('device',-1)]:
            with self.subTest(field=field):
                before=dict(m.NAMESPACE_BINDING);m.NAMESPACE_BINDING[field]=value
                with self.assertRaises(m.Refusal):self.transaction()
                m.NAMESPACE_BINDING=before
        m.NAMESPACE.parent.chmod(0o755)
        with self.assertRaises(m.Refusal):self.transaction()
        self.assert_canary()
    def test_namespace_changed_after_open_refuses(self):
        m=self.m;tx=self.transaction();m.NAMESPACE.rename(m.NAMESPACE.with_name('saved'));m.NAMESPACE.mkdir(mode=0o700)
        with self.assertRaises(m.Refusal):tx.pinned()
        self.assert_canary()
    def test_wrong_parent_same_basename_and_dotdot_refuse(self):
        m=self.m;tx=self.transaction()
        for p in (m.ROOT/m.ATTEMPT.name,m.NAMESPACE.parent/m.ATTEMPT.name,m.NAMESPACE/'..'/m.ATTEMPT.name):
            with self.subTest(path=p),self.assertRaises(m.Refusal):tx.parent_fd(p)
        self.assert_canary()
    def test_nested_active_record_drift_refuses(self):
        m=self.m;tx=self.transaction();m.ATTEMPT.write_bytes(b'foreign owner')
        with self.assertRaises(m.Refusal):tx.run(True)
        self.assert_canary();self.assertEqual(m.ATTEMPT.read_bytes(),b'foreign owner')
    def test_unbound_archive_refuses(self):
        m=self.m;(m.ROOT/m.ARCHIVE_NAMES[0]).mkdir(mode=0o700)
        with self.assertRaises(m.Refusal):self.transaction().run(True)
        self.assert_canary();self.assertTrue(m.ATTEMPT.is_file())
    def test_wrong_sentinel_identity_refuses(self):
        m=self.m;tx=self.transaction();name=m.ARCHIVE_NAMES[0];(m.ROOT/name).mkdir(mode=0o700)
        with self.assertRaises(m.Refusal):tx.sentinel(name,[m.DEVICE,-1])
        self.assert_canary()
    def test_partial_journal_refuses_without_releasing_nested_owner(self):
        m=self.m;tx=self.transaction();tx.lock(True);plan=tx.prepare();m.JOURNAL.write_bytes(b'{')
        with self.assertRaises(m.Refusal):tx.state(plan)
        self.assertTrue(m.ATTEMPT.is_file());self.assertTrue(m.SHARED.is_file());self.assert_canary()
    def test_raced_regular_owner_after_release_is_preserved_on_replay(self):
        m=self.m;tx=self.transaction();tx.run(True);m.ATTEMPT.write_bytes(b'new owner');m.ATTEMPT.chmod(0o600)
        tx.run(True);self.assertEqual(m.ATTEMPT.read_bytes(),b'new owner');self.assert_canary()
    def test_cross_directory_exchange_uses_both_exact_parents(self):
        m=self.m;tx=self.transaction();tx.lock(True);plan=tx.prepare()
        old=m.rename_exchange;calls=[]
        def exchange(fd,source,destination,destination_fd=None):
            calls.append((fd,source,destination,destination_fd));return old(fd,source,destination,destination_fd)
        with mock.patch.object(m,'rename_exchange',side_effect=exchange):tx.run(True)
        self.assertEqual(calls[0][0],tx.nfd);self.assertEqual(calls[0][3],tx.fd)
        self.assertEqual(calls[1][0],tx.fd);self.assertEqual(calls[1][3],tx.fd);self.assert_canary()
    def test_untyped_base_source_cannot_replace_typed_authority(self):
        m=self.m
        for request in ({'candidate_sha':m.IMAGE_CANDIDATE}, {'source_identity':{'inode':354150},'candidate_identity_scope':'base_git_commit_only'}):
            with self.subTest(request=request),self.assertRaises(m.Refusal):m.typed_source_binding(request,{}, {})
    def test_source_or_cid_drift_does_not_weaken_protected_guard(self):
        m=self.m;tx=self.transaction()
        with mock.patch.object(m,'protected_files',side_effect=m.Refusal('source identity drift')),self.assertRaises(m.Refusal):tx.run(True)
        self.assertTrue(m.ATTEMPT.is_file());self.assert_canary()
        m.EXPECTED_CONTAINER={'Id':'c'*64,'Config':{},'HostConfig':{},'Mounts':[]}
        with self.assertRaises(m.Refusal):m.validate_container_profile({'Id':'d'*64})

    def test_published_and_isolated_source_layout_resolution(self):
        staged=self.m.ROOT/'publication'/'scripts';tests=staged/'tests';tests.mkdir(parents=True)
        published_source=staged/'native_fpu_copy_image_terminal_cleanup.py'
        published_source.write_bytes(SOURCE.read_bytes())
        published_test=tests/'test_native_fpu_copy_image_terminal_cleanup.py';published_test.write_text('# fixture')
        self.assertEqual(resolve_source(published_test),published_source)
        spec=importlib.util.spec_from_file_location('published_layout_fixture',resolve_source(published_test))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertTrue(hasattr(module,'Transaction'))
        self.assertEqual(resolve_source(Path(__file__),str(SOURCE)),SOURCE)
    def test_exact_current_attempt_owner_start_cid_nonce_binding(self):
        m=self.m;target=dict(m.KNOWN_TARGET)
        ref={'path':str(m.REQUEST),'sha256':m.REQUEST_SHA}
        m.validate_attempt_binding(target,ref)
        for key,value in [('owner_pid',662188),('owner_starttime','6199402'),
                          ('container_id','d'*64),('owner_nonce','e'*32),('container_name','mckernel-image-'+'f'*32)]:
            changed=dict(target);changed[key]=value
            with self.subTest(field=key),self.assertRaises(m.Refusal):m.validate_attempt_binding(changed,ref)

if __name__=='__main__':unittest.main(verbosity=2)
