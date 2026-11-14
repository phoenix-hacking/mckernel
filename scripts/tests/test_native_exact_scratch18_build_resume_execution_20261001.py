"""Disposable resume admission tests. No production census or execution."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'docs/verification/evidence/native-exact-scratch18-build-resume-execution-20261001.py'

def load():
    spec = importlib.util.spec_from_file_location('scratch18_resume', SOURCE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.m = load(); m = self.m
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); m.REPO = self.root / 'repo'; m.REPO.mkdir()
        m.ROOT = self.root / 'scratch'; m.ROOT.mkdir()
        for key in ('REQUEST', 'ARCHIVE', 'MUTEX', 'ATTEMPT', 'SHARED', 'LEASE', 'OUTPUT', 'EVIDENCE'):
            setattr(m, key, m.ROOT / getattr(m, key).name)
        m.ARCHIVE.mkdir(); m.OUTPUT.mkdir(); m.EVIDENCE.mkdir()
        self.request = {'output_root': str(m.OUTPUT), 'evidence_root': str(m.EVIDENCE), 'lease_path': str(m.LEASE)}
        request_bytes = m.canonical(self.request) + b'\n'
        m.REQUEST_SHA256 = m.sha(request_bytes); m.CANONICAL_SHA256 = m.sha(m.canonical(self.request))
        plan = {'fixture': 'plan'}; m.PLAN_SHA256 = m.sha(m.canonical(plan))
        terminal = {'event': 'complete', 'state': 2, 'plan_sha256': m.PLAN_SHA256}
        fixtures = {m.REQUEST: request_bytes, m.ARCHIVE/'attempt.archive': b'attempt',
                    m.ARCHIVE/'shared.archive': b'shared', m.ARCHIVE/'plan.json': m.canonical(plan)+b'\n',
                    m.ARCHIVE/'journal.jsonl': m.canonical(terminal)+b'\n', m.MUTEX: b''}
        for path, data in fixtures.items(): path.write_bytes(data); path.chmod(0o600)
        m.RECORDS = tuple(self.record(path) for path in fixtures)
        self.bound = {}
        for relative in (*m.DEPENDENCIES, m.PACKET, m.TEST):
            path = m.REPO / relative; path.parent.mkdir(parents=True, exist_ok=True)
            data = ('# fixture ' + relative).encode(); path.write_bytes(data)
            self.bound[relative] = data
        m.DEPENDENCIES = {relative: m.sha(self.bound[relative]) for relative in m.DEPENDENCIES}
        self.commit = 'a' * 40
        self.git_patch = mock.patch.object(m, 'git', side_effect=self.git); self.git_patch.start(); self.addCleanup(self.git_patch.stop)
        self.directory_patch = mock.patch.object(m, 'check_directory', side_effect=self.check_directory)
        self.directory_patch.start(); self.addCleanup(self.directory_patch.stop)
        self.recovery = types.SimpleNamespace(recover=mock.Mock(return_value={'status':'PASS_VALIDATE_ONLY','state':2,'terminal':True}))
        self.wrapper = types.SimpleNamespace(validate_request=mock.Mock(return_value={
            'status':'PASS_COMPATIBILITY_ONLY','execution_released':False,'request_sha256':m.CANONICAL_SHA256}))
        self.modules = mock.patch.object(m, 'module', side_effect=lambda path, data: self.recovery if path == m.HELPER else self.wrapper)
        self.modules.start(); self.addCleanup(self.modules.stop)

    def record(self, path):
        st = path.lstat()
        return (path, st.st_dev, st.st_ino, st.st_nlink, stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid, st.st_size, self.m.sha(path.read_bytes()))

    def git(self, args):
        if args[0] == 'rev-parse': return (self.commit+'\n').encode()
        if args[0] == 'show': return self.bound[args[1].split(':', 1)[1]]
        return b''

    def check_directory(self, path, inode, names):
        if set(p.name for p in path.iterdir()) != set(names): raise self.m.Refusal('directory-contents')

    def run_main(self, execute=False):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            rc=self.m.main(['--release-commit',self.commit]+(['--execute'] if execute else []))
        return rc, json.loads(output.getvalue())

    def test_validate_is_read_only_and_runs_both_real_api_boundaries(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with mock.patch.object(self.m.os,'execv') as execute:
            rc, result=self.run_main()
        self.assertEqual(rc,0); self.assertEqual(result['status'],'PASS_VALIDATE_ONLY')
        self.assertIs(result['execution_released'],False)
        self.recovery.recover.assert_called_once_with(False)
        self.wrapper.validate_request.assert_called_once_with(self.request)
        execute.assert_not_called()
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_exact_exec_once_after_census_compatibility_and_final_rechecks(self):
        m=self.m; events=[]; final=m.final_bindings
        self.recovery.recover.side_effect=lambda execute: events.append(('recover',execute)) or {'status':'PASS_VALIDATE_ONLY','state':2,'terminal':True}
        self.wrapper.validate_request.side_effect=lambda request: events.append('compatibility') or {'status':'PASS_COMPATIBILITY_ONLY','execution_released':False,'request_sha256':m.CANONICAL_SHA256}
        def final_check(*args): events.append('final'); return final(*args)
        def execute(program,args): events.append('exec'); raise RuntimeError('exec boundary')
        with mock.patch.object(m,'final_bindings',side_effect=final_check), mock.patch.object(m.os,'execv',side_effect=execute) as call:
            with self.assertRaisesRegex(RuntimeError,'exec boundary'): self.run_main(True)
        self.assertEqual(events,[('recover',False),'compatibility','final','final','exec'])
        expected=['/usr/bin/python3','-E','-s','-B',str(m.REPO/m.WRAPPER),str(m.REQUEST),'--launcher-aggregate-gib','16.2158']
        call.assert_called_once_with('/usr/bin/python3',expected)

    def test_each_exact_file_identity_field_and_bytes_are_required(self):
        for row in self.m.RECORDS:
            for index in range(1,9):
                wrong=list(row); wrong[index]=wrong[index]+1 if type(wrong[index]) is int else '0'*64
                with self.subTest(path=row[0].name,index=index), self.assertRaises(self.m.Refusal):
                    self.m.read_regular(row[0],tuple(wrong))

    def test_symlink_parent_leaf_and_hardlink_are_rejected(self):
        path=self.m.REQUEST; alias=self.root/'alias'; alias.symlink_to(path)
        with self.assertRaises(OSError): self.m.read_regular(alias)
        parent=self.root/'parent'; parent.symlink_to(path.parent,target_is_directory=True)
        with self.assertRaises(OSError): self.m.read_regular(parent/path.name)
        alias.unlink(); os.link(path,alias)
        with self.assertRaisesRegex(self.m.Refusal,'artifact-shape'): self.m.read_regular(path)

    def test_changed_open_file_is_rejected(self):
        m=self.m; real=m.os.read
        def read(fd,count):
            data=real(fd,count)
            if data: m.REQUEST.write_bytes(b'changed')
            return data
        with mock.patch.object(m.os,'read',side_effect=read):
            with self.assertRaisesRegex(m.Refusal,'artifact-raced'): m.read_regular(m.REQUEST)

    def test_absent_paths_include_dangling_symlinks(self):
        for path in (self.m.ATTEMPT,self.m.SHARED,self.m.LEASE):
            path.symlink_to(self.root/'missing')
            with self.assertRaisesRegex(self.m.Refusal,'live-ownership'): self.m.retained()
            path.unlink()

    def test_no_output_or_evidence_entries_allowed(self):
        for path in (self.m.OUTPUT,self.m.EVIDENCE,self.m.ARCHIVE):
            added=path/'unexpected'; added.touch()
            with self.assertRaisesRegex(self.m.Refusal,'directory-contents'): self.m.retained()
            added.unlink()

    def test_directory_identity_is_bound(self):
        m=self.m; self.directory_patch.stop()
        try:
            with self.assertRaisesRegex(m.Refusal,'directory-binding'):
                m.check_directory(m.OUTPUT,-1,())
        finally: self.directory_patch.start()

    def test_canonical_request_and_plan_are_independently_bound(self):
        for field in ('CANONICAL_SHA256','PLAN_SHA256'):
            with mock.patch.object(self.m,field,'0'*64):
                with self.assertRaisesRegex(self.m.Refusal,'canonical-binding'): self.m.retained()

    def test_terminal_mutations_reject_even_with_matching_raw_file_binding(self):
        m=self.m; path=m.ARCHIVE/'journal.jsonl'; original=path.read_bytes(); rows=m.RECORDS
        for key,value in (('event','after'),('state',True),('state',1),('plan_sha256','0'*64)):
            terminal=json.loads(original); terminal[key]=value; path.write_bytes(m.canonical(terminal)+b'\n')
            m.RECORDS=tuple(self.record(path) if row[0]==path else row for row in rows)
            with self.assertRaisesRegex(m.Refusal,'terminal-binding'): m.retained()

    def test_recovery_must_be_exact_terminal_state_two(self):
        good=self.recovery.recover.return_value
        for bad in (None,dict(good,state=1),dict(good,state=True),dict(good,terminal=False),dict(good,terminal=1),dict(good,extra=1)):
            self.recovery.recover.return_value=bad
            with mock.patch.object(self.m.os,'execv') as execute:
                self.assertEqual(self.run_main(True)[0],1); execute.assert_not_called()
        self.wrapper.validate_request.assert_not_called()

    def test_downstream_must_bind_existing_request_and_not_grant_execution(self):
        good=self.wrapper.validate_request.return_value
        for bad in (None,dict(good,status='PASS'),dict(good,execution_released=True),dict(good,request_sha256='0'*64)):
            self.wrapper.validate_request.return_value=bad
            with mock.patch.object(self.m.os,'execv') as execute:
                self.assertEqual(self.run_main(True)[0],1); execute.assert_not_called()

    def test_full_ref_commit_dependency_and_packet_bindings(self):
        m=self.m
        self.assertEqual(m.sources(self.commit),self.bound)
        for bad in ('abc','A'*40,'a'*39):
            with self.assertRaisesRegex(m.Refusal,'release-commit'): m.sources(bad)
        with mock.patch.object(m,'git',return_value=b'0'*40+b'\n'):
            with self.assertRaisesRegex(m.Refusal,'release-ref-mismatch'): m.sources(self.commit)
        for relative in (*m.DEPENDENCIES,m.PACKET,m.TEST):
            path=m.REPO/relative; original=path.read_bytes(); path.write_bytes(original+b'changed')
            with self.subTest(relative=relative),self.assertRaises(m.Refusal):m.sources(self.commit)
            path.write_bytes(original)

    def test_every_full_ancestor_is_checked_and_failure_blocks(self):
        for ancestor in self.m.ANCESTORS:
            self.assertEqual(len(ancestor),40)
            def git(args):
                if args==['merge-base','--is-ancestor',ancestor,self.commit]: raise self.m.Refusal('ancestry')
                return self.git(args)
            with mock.patch.object(self.m,'git',side_effect=git),mock.patch.object(self.m.os,'execv') as execute:
                self.assertEqual(self.run_main(True)[0],1); execute.assert_not_called()

    def test_late_source_or_request_change_never_executes(self):
        for target in ('sources','retained'):
            original=getattr(self.m,target); calls=[0]
            def changed(*args):
                calls[0]+=1
                if calls[0]>=3: raise self.m.Refusal('late replacement')
                return original(*args)
            with mock.patch.object(self.m,target,side_effect=changed),mock.patch.object(self.m.os,'execv') as execute:
                self.assertEqual(self.run_main(True)[0],1); execute.assert_not_called()

    def test_refusal_at_any_gate_never_executes(self):
        for target in ('sources','retained','module','final_bindings'):
            with mock.patch.object(self.m,target,side_effect=self.m.Refusal('blocked')),mock.patch.object(self.m.os,'execv') as execute:
                self.assertEqual(self.run_main(True)[0],1); execute.assert_not_called()

    def test_production_pins_and_argv_remain_exact_without_production_execution(self):
        m=load()
        self.assertEqual(m.REVIEW_STATE,'SOURCE_PENDING_REVIEW')
        self.assertEqual(m.REQUEST.name,'native-exact-build-request-scratch-18-execution.json')
        self.assertEqual(m.RECORDS[0][1:8],(1831,90729,1,0o600,1000,1000,2973))
        for relative,expected in m.DEPENDENCIES.items():self.assertEqual(m.sha((REPO/relative).read_bytes()),expected)
        self.assertNotIn('publish',m.__dict__)
        self.assertEqual(m.wrapper_argv()[0:4],['/usr/bin/python3','-E','-s','-B'])

if __name__=='__main__':unittest.main()
