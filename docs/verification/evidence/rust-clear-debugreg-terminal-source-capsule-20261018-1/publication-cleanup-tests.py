"""Disposable nested transaction fixtures only; no root/Docker/live cleanup."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import subprocess
import io
import contextlib
import copy
import hashlib
import tarfile
import sys
import unittest
from unittest import mock

def resolve_source(test_file, override=None):
    if override is not None:
        return Path(override).resolve(strict=True)
    return Path(test_file).resolve().parents[1] / 'native_rust_cutover_image_terminal_cleanup.py'


P=Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-terminal-preparation-20261018-1')
SOURCE=(resolve_source(__file__, os.environ.get('NATIVE_FP_CLEANUP_TEST_SOURCE'))
        if Path(__file__).resolve().parent.name=='tests' else P/'cleanup.py')

class NestedCleanupTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('thin_cleanup_fixture',SOURCE)
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.temp=tempfile.TemporaryDirectory(dir=P,prefix='hostsplit-fixture-');self.addCleanup(self.temp.cleanup)
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
        m.CONTAINER='c'*64;m.CONTAINER_NAME='mckernel-image-'+'a'*32;m.OWNER_NONCE='b'*32;m.EXPECTED_EXIT=0
        m.KNOWN_TARGET=dict(container_id=m.CONTAINER,container_name=m.CONTAINER_NAME,owner_nonce=m.OWNER_NONCE,owner_pid=m.OWNER_PID,owner_starttime=m.OWNER_START)
        for p in (m.ATTEMPT,m.SHARED):p.write_bytes(('owned:'+str(p)).encode());p.chmod(0o600)
        m.RECORDS={p:(m.digest(p.read_bytes()),p.stat().st_ino,p.stat().st_size) for p in (m.ATTEMPT,m.SHARED)}
        m.DIRS={p:(p.stat().st_dev,p.stat().st_ino,p.stat().st_nlink) for p in (m.OUTPUT,m.EVIDENCE)}
        m.TERMINAL_SHA=m.digest(m.TERMINAL.read_bytes());m.TERMINAL_INODE=m.TERMINAL.stat().st_ino;m.TERMINAL_SIZE=m.TERMINAL.stat().st_size
        self.canary=m.ROOT/m.ATTEMPT.name;self.canary.write_bytes(b'ROOT basename canary');self.canary.chmod(0o600)
        self.canary_before=(self.canary.stat().st_ino,self.canary.read_bytes())
        self.install_devices()
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
    def install_devices(self):
        # Actual local fixture operations, with device reports modeled at the OS
        # boundary. This is not a live cross-filesystem/root proof.
        m=self.m;actual_stat=os.stat;actual_fstat=os.fstat
        def fullpath(path,dir_fd=None):
            if isinstance(path,int):return Path(os.readlink('/proc/self/fd/'+str(path)))
            path=Path(path)
            if not path.is_absolute():
                path=(Path(os.readlink('/proc/self/fd/'+str(dir_fd))) if dir_fd is not None else Path.cwd())/path
            return path
        def modeled(meta,path):
            fields={name:getattr(meta,name) for name in dir(meta) if name.startswith('st_')}
            fields['st_dev']=66306 if path==m.NAMESPACE or m.NAMESPACE in path.parents else (1828 if path==m.ROOT or m.ROOT in path.parents else meta.st_dev)
            return types.SimpleNamespace(**fields)
        def checked_stat(path,*a,dir_fd=None,**kw):return modeled(actual_stat(path,*a,dir_fd=dir_fd,**kw),fullpath(path,dir_fd))
        def checked_fstat(fd):return modeled(actual_fstat(fd),fullpath(fd))
        patch=mock.patch.object(os,'stat',checked_stat);patch.start();self.addCleanup(patch.stop)
        patch=mock.patch.object(os,'fstat',checked_fstat);patch.start();self.addCleanup(patch.stop)
        m.DEVICE=1828;m.NAMESPACE_BINDING=self.ns_binding();m.NAMESPACE_ANCESTRY=m.namespace_ancestry()
        m.DIRS={p:(p.stat().st_dev,p.stat().st_ino,p.stat().st_nlink) for p in (m.OUTPUT,m.EVIDENCE)}
        m.ROOT_LOCK_BINDING=m.observe_identity(m.ROOT_LOCK)
        real=m.rename_exchange
        def exchange(fd,source,destination,destination_fd=None):
            other=fd if destination_fd is None else destination_fd
            self.assertEqual(os.fstat(fd).st_dev,os.fstat(other).st_dev,'would issue EXDEV exchange')
            return real(fd,source,destination,destination_fd)
        self.patch('rename_exchange',exchange)

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
            self.assertFalse(p.exists());self.assertEqual((p.parent/archive).read_bytes(),before[p])
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
        m=self.m;(m.NAMESPACE/m.ARCHIVE_NAMES[0]).mkdir(mode=0o700)
        with self.assertRaises(m.Refusal):self.transaction().run(True)
        self.assert_canary();self.assertTrue(m.ATTEMPT.is_file())
    def test_wrong_sentinel_identity_refuses(self):
        m=self.m;tx=self.transaction();name=m.ARCHIVE_NAMES[0];(m.NAMESPACE/name).mkdir(mode=0o700)
        with self.assertRaises(m.Refusal):tx.sentinel(name,[m.NAMESPACE_BINDING['device'],-1],tx.nfd)
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
        self.assertEqual(calls[0][0],tx.nfd);self.assertIsNone(calls[0][3])
        self.assertEqual(calls[1][0],tx.fd);self.assertIsNone(calls[1][3]);self.assert_canary()
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
        published_source=staged/'native_rust_cutover_image_terminal_cleanup.py'
        published_source.write_bytes(SOURCE.read_bytes())
        published_test=tests/'test_native_rust_cutover_image_terminal_cleanup.py';published_test.write_text('# fixture')
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



class HostSplitConfigureTests(NestedCleanupTests):
    def release_fixture(self):
        m=self.m
        m.BOOT_ID='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
        m.REQUEST=m.NAMESPACE/'image-request.json';m.LEASE=m.NAMESPACE/'image-lease.json'
        m.SELFTEST=Path(__file__)
        m.TERMINAL.write_bytes(b'{}')
        source=m.NAMESPACE/'materialized-source';source.mkdir(mode=0o700)
        backup=m.ROOT/'mckernel-exact-candidate-scratch-22-authority3-metadata-backup';backup.mkdir(mode=0o700)
        guard=m.ROOT/'native-rust-clear-debugreg-image-guard-20261018-e4becbcd4971479f81426b3872cbe27c'
        status=guard/'command-1/status.json';status.parent.mkdir(parents=True,mode=0o700)
        status.write_bytes(m.canonical(dict(pid=124,state='exited',exit_code=0)));status.chmod(0o600)
        proof=guard/'guard-result.json';proof.write_bytes(b'{}');proof.chmod(0o600)
        for path in (m.EVIDENCE/'attempt',m.OUTPUT/'evidence'):path.mkdir(mode=0o700)
        for path in (m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json'):
            path.write_bytes(b'fixture evidence');path.chmod(0o600)
        request=dict(schema='mckernel.native-exact-mckernel-image-container-request.v1',candidate_sha=m.IMAGE_CANDIDATE,image_id='sha256:'+'e'*64,
                     source_root=str(source),backup_root=str(backup),work_root=str(m.OUTPUT),owner_evidence_root=str(m.EVIDENCE),
                     output_root=str(m.OUTPUT/'output'),evidence_root=str(m.OUTPUT/'evidence'),attempt_root=str(m.EVIDENCE/'attempt'),
                     lease_path=str(m.LEASE),common_exclusion_path=str(m.ATTEMPT),ihk_sha='f'*40,jobs=4,timeout=300,
                     toolchain_roots=[dict(container_path='/out',host_path='/fixture/compiler'),dict(container_path='/nightly',host_path='/fixture/rust')])
        for key in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest'):
            path=m.NAMESPACE/(key+'.json');path.write_bytes(b'fixture source '+key.encode());path.chmod(0o600);request[key]=str(path)
            request[dict(driver_path='driver_sha256',provenance_path='provenance_sha256',host_owner_path='host_owner_sha256',source_manifest='source_manifest_sha256',toolchain_manifest='toolchain_manifest_sha256')[key]]=m.digest(path.read_bytes())
        def source_identity(path):
            row=m.observe_identity(path);return dict(path=str(path),dev=row['device'],inode=row['inode'],uid=row['uid'],gid=row['gid'],mode=int(row['mode'],8),file_type=stat.S_IFDIR)
        request['source_identity']=source_identity(source);request['backup_identity']=source_identity(backup)
        m.REQUEST.write_bytes(m.canonical(request));m.REQUEST.chmod(0o600);m.REQUEST_SHA=m.digest(m.REQUEST.read_bytes())
        target=dict(m.KNOWN_TARGET,image_id=request['image_id'],exit_code=1)
        for path in (m.ATTEMPT,m.SHARED):
            common=path==m.ATTEMPT;meta=path.stat()
            owner=dict(schema='mckernel.native-exact-operational-exclusion.v1' if common else 'mckernel.heavy-operation.v1',
                       pid=target['owner_pid'],starttime=target['owner_starttime'],boot_id=m.BOOT_ID,
                       request_sha256=m.digest(json.dumps(request,sort_keys=True).encode()) if common else m.digest(m.canonical(request)),inode=meta.st_ino)
            owner['dev' if common else 'device']=m.path_device(path)
            if not common:owner['kind']='image'
            path.write_bytes(m.canonical(owner));path.chmod(0o600)
        command,mounts=m.image_layout(request)
        profile=dict(CpusetCpus='2-5',NanoCpus=4000000000,Memory=12884901888,MemorySwap=12884901888,PidsLimit=512,NetworkMode='none',IpcMode='private',ReadonlyRootfs=True,Privileged=False,CapDrop=['ALL'],Init=True,SecurityOpt=['no-new-privileges'],Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'},RestartPolicy={'MaximumRetryCount':0,'Name':'no'},AutoRemove=False)
        inspection=dict(Id=target['container_id'],Name='/'+target['container_name'],Image=target['image_id'],Path='/usr/bin/python3',Args=command,
                        Config=dict(Labels={'mckernel.owner':target['owner_nonce']},User='1000:1000',Entrypoint=['/usr/bin/python3'],Cmd=command,Image=target['image_id']),
                        HostConfig=profile,State=dict(Status='exited',Running=False,Paused=False,Restarting=False,OOMKilled=False,Dead=False,Pid=0,ExitCode=1,Error=''),
                        Mounts=[dict(Destination=d,Source=s,Type=t,RW=rw) for d,s,t,rw in mounts])
        selected=[m.observe_identity(path) for path in (m.REQUEST,m.TERMINAL,proof,m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json',status,*[Path(request[k]) for k in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest')])]
        lock=dict(m.ROOT_LOCK_BINDING,device=27,inode=4,uid=0,gid=0)
        observation=dict(mount=dict(target=str(m.ROOT),uuid=m.UUID,fstype='ext4',options='rw,nodev,nosuid'),root=m.observe_identity(m.ROOT),boot_id=m.BOOT_ID,root_lock=lock,
                         request=m.observe_identity(m.REQUEST),target=target,container_inspect=inspection,retained_exclusions=[m.observe_identity(p) for p in (m.ATTEMPT,m.SHARED)],
                         request_lease_absent=True,inventories={str(p):m.metadata_inventory(p) for p in (m.OUTPUT,m.EVIDENCE)},candidate_root=m.observe_identity(source),
                         candidate_commit=m.IMAGE_CANDIDATE,candidate_tree='d'*40,selected_files=selected,backup_root=m.observe_identity(backup),namespace_binding=m.NAMESPACE_BINDING,
                         namespace_ancestry=m.NAMESPACE_ANCESTRY,client_ledger=[dict(pid=124,status_path=str(status),status_sha256=m.digest(status.read_bytes()))],guard_proof=m.observe_identity(proof))
        review=dict(status='PASS',reviewer='independent-fixture-review',evidence_sha256='a'*64)
        release=dict(schema='fp-save-image.cleanup-release.v1',status='PASS_EXECUTION_RELEASE',baseline_source_sha256=m.BASELINE_SOURCE_SHA,
                     script_sha256=m.digest(SOURCE.read_bytes()),tests_sha256=m.digest(Path(__file__).read_bytes()),publisher_contract=m.PUBLISHER_CONTRACT,
                     source_review=review,execution_review=review,author='fixture-author',fetched_source_verified=True,git_commit='c'*40,git_tree='d'*40,
                     observation=observation,transaction_paths=m.transaction_paths())
        original_record=m.image_record_binding
        def debug_record(path,row,owner,request,target,boot):
            try:return original_record(path,row,owner,request,target,boot)
            except m.Refusal:
                (P/'hostsplit-fixture-record-failure.json').write_text(json.dumps(dict(path=str(path),row=row,owner=owner,target=target,boot=boot,compact_sha=m.digest(m.canonical(request)),spaces_sha=m.digest(json.dumps(request,sort_keys=True).encode())),indent=2)+'\n');raise
        self.patch('image_record_binding',debug_record)
        original_read=m.read_bounded
        # Outer artifact review, Git availability and positive-retirement bodies
        # are not the defect under test; exact source/device/record consumers run.
        def git(command,**kw):
            if 'rev-parse' in command:return b'd'*40+b'\n'
            return SOURCE.read_bytes() if command[-1].endswith(m.PUBLISHED_SCRIPT) else Path(__file__).read_bytes()
        self.patch('typed_source_binding',lambda *args:None)
        self.patch('image_receipt_binding',lambda *args:None)
        patch=mock.patch.object(m.subprocess,'check_output',git);patch.start();self.addCleanup(patch.stop)
        original_observe=m.observe_identity
        self.patch('observe_identity',lambda path:lock if path==m.ROOT_LOCK else original_observe(path))
        return release

    def test_actual_configure_then_transaction_distinct_device_positive(self):
        m=self.m;release=self.release_fixture();m.configure(release)
        self.assertEqual((m.DEVICE,m.NAMESPACE_BINDING['device']),(1828,66306))
        self.assertEqual(m.path_device(m.ATTEMPT),66306);self.assertEqual(m.path_device(m.SHARED),1828)
        self.assertEqual(m.RECORDS[m.ATTEMPT],(release['observation']['retained_exclusions'][0]['sha256'],m.ATTEMPT.stat().st_ino,m.ATTEMPT.stat().st_size))
        # Rebind only the fixture's real unprivileged mutex identity for actual
        # Transaction opening/flock. The production fixed root-lock guard remains.
        original_observe=m.observe_identity
        lock=release['observation']['root_lock'];real_fstat=m.os.fstat
        def fstat(fd):
            meta=real_fstat(fd)
            if Path(os.readlink('/proc/self/fd/'+str(fd)))==m.ROOT_LOCK:
                fields=dict(vars(meta));fields.update(st_dev=27,st_ino=4,st_uid=0,st_gid=0);return types.SimpleNamespace(**fields)
            return meta
        patch=mock.patch.object(m.os,'fstat',fstat);patch.start();self.addCleanup(patch.stop)
        result=self.transaction().run(True);self.assertEqual(result['status'],'PASS_EXECUTED')
        self.assertEqual([r['device'] for r in result['archives']],[66306,1828]);self.assert_canary()

    def test_actual_configure_refuses_wrong_record_device(self):
        m=self.m;release=self.release_fixture();release['observation']['retained_exclusions'][0]['device']=1828
        with self.assertRaisesRegex(m.Refusal,'future-exclusion-binding'):m.configure(release)
        self.assertTrue(m.ATTEMPT.is_file());self.assertTrue(m.SHARED.is_file())

    def test_actual_configure_refuses_changed_namespace_access(self):
        m=self.m;release=self.release_fixture();m.NAMESPACE.chmod(0o755)
        with self.assertRaisesRegex(m.Refusal,'exact-namespace-binding'):m.configure(release)
        self.assertTrue(m.ATTEMPT.is_file());self.assertTrue(m.SHARED.is_file())

    def test_actual_configure_refuses_record_path_substitution(self):
        m=self.m;release=self.release_fixture();release['observation']['retained_exclusions'][0]['path']=str(self.canary)
        with self.assertRaisesRegex(m.Refusal,'exact-exclusions-required'):m.configure(release)
        self.assert_canary()

    def test_postmutation_failure_quarantines_retaining_both_records(self):
        m=self.m;real=m.rename_exchange;calls=[]
        def exchange(*args,**kw):
            real(*args,**kw);calls.append(True);raise m.Refusal('injected-after-exchange')
        self.patch('rename_exchange',exchange)
        self.patch('quarantine_wait',lambda:(_ for _ in ()).throw(RuntimeError('fixture quarantine held')))
        out=io.StringIO()
        with contextlib.redirect_stdout(out),self.assertRaisesRegex(RuntimeError,'fixture quarantine held'):m.recover(True)
        self.assertEqual(len(calls),1);self.assertTrue(m.ATTEMPT.is_dir());self.assertTrue(m.SHARED.is_file())
        archive=m.archive_paths()[0];self.assertTrue(archive.is_file());self.assertEqual(archive.stat().st_dev,66306)
        self.assertTrue(m.QUARANTINE.is_file());self.assertIn('QUARANTINED_ROOT_LOCK_HELD',out.getvalue());self.assert_canary()

    def test_explicit_device_read_refuses_changed_device(self):
        m=self.m;tx=self.transaction()
        with self.assertRaises(m.Refusal):m.read_at(tx.nfd,m.ATTEMPT.name,m.RECORDS[m.ATTEMPT])
        self.assertEqual(m.read_at(tx.nfd,m.ATTEMPT.name,m.RECORDS[m.ATTEMPT],expected_device=66306)[0],m.ATTEMPT.read_bytes())
        with self.assertRaises(m.Refusal):m.path_device(m.ROOT/m.ATTEMPT.name)

    def test_postjoin_cross_parent_tar_keeps_exact_five_flat_originals(self):
        m=self.m;spec=importlib.util.spec_from_file_location('hostsplit_post',P/'postjoin_readback.py');post=importlib.util.module_from_spec(spec);spec.loader.exec_module(post)
        self.transaction().run(True);paths=[m.PLAN,m.JOURNAL,m.CAPTURE]+list(m.archive_paths())
        cp=subprocess.run(post.archive_argv(paths),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=5)
        self.assertFalse(cp.stderr)
        with tarfile.open(fileobj=io.BytesIO(cp.stdout)) as archive:
            self.assertEqual(archive.getnames(),[p.name for p in paths])
            for p in paths:self.assertEqual(archive.extractfile(p.name).read(),p.read_bytes())

if __name__=='__main__':unittest.main(verbosity=2)
