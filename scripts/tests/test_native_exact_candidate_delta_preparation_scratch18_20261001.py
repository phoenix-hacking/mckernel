"""Real canonical admission over disposable Git/overlay/assets; no Docker or guest.

Only fixture identities and tiny asset hashes differ from production. The actual
manifest main, source inventory, verify_inputs, BuildOwner.validate and capacity
measurement execute unchanged. Requires the campaign's mounted scratch and floors.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
P = ROOT/'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch18-20261001.py'
spec = importlib.util.spec_from_file_location('scratch18', P)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Scratch18(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix='scratch18-regression-', dir=p.DEFAULT_SCRATCH)
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        self.src, self.s15, self.s16, self.scratch = [self.r/x for x in ('src','s15','s16','scratch')]
        self.src.mkdir()
        self.scratch.mkdir()
        self.init(self.src)
        ihk = self.r/'ihk-source'
        ihk.mkdir()
        self.init(ihk)
        self.put(ihk, p.OVERLAY_RESULT_REL, b'base\n')
        self.g(ihk,'add','.')
        self.g(ihk,'commit','-qm','ihk')
        self.ihk = self.g(ihk,'rev-parse','HEAD').decode().strip()
        self.put(ihk,p.OVERLAY_RESULT_REL,b'result\n')
        overlay = self.g(ihk,'diff','--binary','HEAD')
        self.put(self.src,p.OVERLAY_REL,overlay)
        self.overlay = p.sha(overlay)
        self.base = p.sha(b'base\n')
        self.result = p.sha(b'result\n')
        self.assets = self.r/'assets'
        self.assets.mkdir()
        # Change constants in committed fixture copies only. The canonical
        # routines and schemas themselves remain byte-for-byte unchanged.
        replacements = {p.IHK:self.ihk, p.OVERLAY_SHA256:self.overlay,
                        p.OVERLAY_BASE_BLOB_SHA:self.base,
                        p.OVERLAY_RESULT_SHA256:self.result,
                        '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18.json':
                        str(self.scratch/'native-exact-candidate-operational-exclusion-scratch18.json')}
        asset_names = ('linux-6.12.0-211.44.1.el10_2.tar.xz',
                       'kernel-x86_64-rhel.config',
                       'kernel-6.12.0-211.44.1.el10_2.src.rpm',
                       '1000-debrand-some-messages.patch')
        asset_hashes = ('4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533',
                        '5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d',
                        '2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb',
                        '080bbc72a543eed6b71daee1b3236b59f3a0f8b3ad20815d962444d3b106b144')
        for name, expected in zip(asset_names,asset_hashes):
            raw = ('tiny fixture '+name).encode()
            self.put(self.assets,name,raw)
            replacements[expected]=p.sha(raw)
        for name in ('native_rust_exact_build_input_manifest',
                     'native_rust_exact_build_offline',
                     'native_rust_exact_build_container_owner'):
            text=(ROOT/'scripts'/(name+'.py')).read_text()
            for before,after in replacements.items(): text=text.replace(before,after)
            self.put(self.src,'scripts/'+name+'.py',text.encode())
        for i in range(13): self.put(self.src,'old%d.txt'%i,b'old\n')
        self.large='docs/verification/evidence/large.bin'
        self.put(self.src,self.large,b'x'*((1<<20)+1))
        self.private_paths = (
            'docs/verification/evidence/native-exact-candidate-retention-c81aeaca-scratch14-20261001.inventory.json',
            'docs/verification/evidence/native-exact-candidate-retention-c81aeaca-scratch14-20261001.tar')
        self.put(self.src,self.private_paths[0],b'i' * 5479703)
        self.put(self.src,self.private_paths[1],b't' * 12247040)
        self.g(self.src,'add','.')
        self.g(self.src,'update-index','--add','--cacheinfo','160000,'+self.ihk+',ihk')
        self.g(self.src,'commit','-qm','source-base')
        self.source_base=self.g(self.src,'rev-parse','HEAD').decode().strip()
        self.historical=self.g(self.src,'hash-object','-w','--stdin',input=b'historical ABI object').decode().strip()
        shutil.copytree(self.src,self.s15,symlinks=True)
        shutil.copytree(ihk,self.s15/'ihk',symlinks=True)
        shutil.copytree(self.src,self.s16,symlinks=True)
        shutil.copytree(ihk,self.s16/'ihk',symlinks=True)
        shutil.copytree(ihk,self.src/'ihk',symlinks=True)
        self.g(self.src,'commit','--allow-empty','-qm','old')
        self.old=self.g(self.src,'rev-parse','HEAD').decode().strip()
        self.previous=self.scratch/p.PREVIOUS_CANDIDATE_NAME
        (self.previous/self.large).parent.mkdir(parents=True)
        (self.s16/self.large).unlink()
        os.link(self.s15/self.large,self.s16/self.large)
        os.link(self.s15/self.large,self.previous/self.large)
        for rel in self.private_paths:
            (self.s15/rel).unlink()
            (self.previous/rel).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(self.s16/rel,self.previous/rel)
        p.PRIVATE_RETENTION = tuple(
            (rel, self.g(self.src,'hash-object',rel).decode().strip(), p.sha((self.src/rel).read_bytes()),
             (self.src/rel).stat().st_size) for rel in self.private_paths)
        # The old immutable metadata deliberately lacks the target commit.
        for i in range(5): self.put(self.src,'new%d.txt'%i,b'new\n')
        for i in range(9): self.put(self.src,'old%d.txt'%i,b'changed\n')
        self.g(self.src,'add','.')
        self.g(self.src,'commit','-qm','target')
        self.target=self.g(self.src,'rev-parse','HEAD').decode().strip()
        self.g(self.src,'update-ref',p.FETCHED_REF,self.target)
        p.SOURCE_BASE = self.source_base
        p.TARGET = self.target
        p.TARGET_TREE = self.g(self.src,'rev-parse',self.target+'^{tree}').decode().strip()
        p.EXACT_DELTA = tuple(
            (status, path, self.g(self.src,'rev-parse',self.target+':'+path).decode().strip())
            for status, path in [row.split('\t',1) for row in
                self.g(self.src,'diff','--name-status','--no-renames',self.old,self.target).decode().splitlines()])
        self.receipt=self.r/'receipt.json'
        self.receipt.write_text(json.dumps({'status':'PASS','image_id':p.IMAGE_ID}))
        delta = self.g(self.src,'diff','--name-status','--no-renames',self.old,self.target).decode().splitlines()
        self.expected_delta = tuple(
            (status, path, self.g(self.src,'rev-parse',self.target+':'+path).decode().strip())
            for status, path in [row.split('\t',1) for row in delta])
        self.kw=dict(old=self.old,baseline=self.old,source_base=self.source_base,target=self.target,expected_delta=self.expected_delta,ihk_expected=self.ihk,
                     overlay_sha=self.overlay,overlay_result_sha=self.result,
                     overlay_base_sha256=self.base,assets_root=self.assets,
                     image_receipt=self.receipt,image_receipt_sha256=p.digest(self.receipt),
                     scratch16=self.s16,previous_candidate=self.previous,expected_shared_files=1)
        self.commands=[]
        original=subprocess.Popen
        def only_git(argv,*args,**kwargs):
            self.commands.append(argv)
            if (not isinstance(argv,(list,tuple)) or
                    argv[0] not in ('/usr/bin/git','uname')):
                raise AssertionError('non-Git subprocess forbidden: '+repr(argv))
            return original(argv,*args,**kwargs)
        self.guard=mock.patch.object(subprocess,'Popen',side_effect=only_git)
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def g(self,root,*args,input=None):
        return subprocess.run(['/usr/bin/git','-C',str(root),*args],input=input,
                              check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout

    def init(self,root):
        self.g(root,'init','-q')
        self.g(root,'config','user.name','fixture')
        self.g(root,'config','user.email','fixture@example.invalid')

    def put(self,root,name,raw):
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o644)

    def prepare(self,**kwargs):
        return p.prepare(self.src,self.s15,self.scratch,**dict(self.kw,**kwargs))

    def set_fetched_ref(self, commit):
        self.g(self.src,'update-ref',p.FETCHED_REF,commit)

    def terminal(self):
        return json.loads((self.scratch/p.TERMINAL_NAME).read_text())

    def test_exact_delta_and_validate_only(self):
        self.assertEqual((self.s15/self.large).stat().st_nlink,3)
        self.assertEqual((self.s16/self.large).stat().st_nlink,3)
        self.assertEqual((self.previous/self.large).stat().st_nlink,3)
        stale = dict(self.kw, expected_delta=self.expected_delta[:-1])
        with self.assertRaisesRegex(p.Refusal, 'exact target allowlist'):
            self.prepare(**stale)
        result=self.prepare()
        self.assertEqual(tuple((status, path, self.g(self.src,'rev-parse',self.target+':'+path).decode().strip())
                               for status, path in result['delta']), self.expected_delta)
        self.assertEqual(result['shared_files'],1)
        self.assertEqual((self.s15/self.large).stat().st_nlink,3)
        self.assertEqual((self.s16/self.large).stat().st_nlink,3)
        self.assertEqual((self.previous/self.large).stat().st_nlink,3)
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())
        self.assertFalse((self.scratch/p.LOG_NAME).exists())

    def test_validate_only_extra_prior_owner_link_refused(self):
        extra=self.r/'validate-only-unrecognized-extra-link.bin'
        os.link(self.s15/self.large,extra)
        with self.assertRaisesRegex(p.Refusal,'unauthenticated prior shared evidence'):
            self.prepare()
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())
        self.assertFalse((self.scratch/p.MANIFEST_NAME).exists())
        self.assertFalse((self.scratch/p.LOG_NAME).exists())

    def test_validate_only_mismatched_prior_owner_refused(self):
        prior=self.previous/self.large
        prior.unlink()
        self.put(self.previous,self.large,b'z'*((1<<20)+1))
        with self.assertRaisesRegex(p.Refusal,'unauthenticated prior shared evidence'):
            self.prepare()
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())
        self.assertFalse((self.scratch/p.MANIFEST_NAME).exists())
        self.assertFalse((self.scratch/p.LOG_NAME).exists())

    def test_validate_only_stale_intermediate_owner_refused(self):
        prior=self.s16/self.large
        prior.unlink()
        self.put(self.s16,self.large,b'z'*((1<<20)+1))
        with self.assertRaisesRegex(p.Refusal,'unauthenticated prior shared evidence'):
            self.prepare()
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())

    def test_validate_only_unknown_missing_large_file_refused(self):
        (self.s15/self.large).unlink()
        with self.assertRaisesRegex(p.Refusal,'unexpected missing large retained evidence'):
            self.prepare()

    def test_validate_only_multilink_private_owner_refused(self):
        extra=self.r/'private-extra-owner.bin'
        os.link(self.s16/self.private_paths[0],extra)
        with self.assertRaisesRegex(p.Refusal,'unauthenticated private retained evidence'):
            self.prepare()

    def test_complete_canonical_preparation(self):
        self.assertEqual((self.s15/self.large).stat().st_nlink,3)
        self.assertEqual((self.s16/self.large).stat().st_nlink,3)
        self.assertEqual((self.previous/self.large).stat().st_nlink,3)
        calls=[]
        original_path=sys.path[:]
        original_modules={name:sys.modules.get(name) for name in
            ('native_rust_exact_build_offline','native_rust_exact_build_input_manifest',
             'native_rust_exact_build_container_owner')}
        def trace(frame,event,arg):
            if event=='call' and frame.f_code.co_name in ('main','verify_inputs','validate'):
                path=Path(frame.f_code.co_filename)
                if (self.scratch/p.CANDIDATE_NAME) in path.parents:
                    calls.append((path.name,frame.f_code.co_name))
                    if frame.f_code.co_name=='validate':
                        request=json.loads((self.scratch/p.REQUEST_NAME).read_text())
                        self.assertEqual(frame.f_locals['self'].r,request)
        previous=sys.getprofile()
        sys.setprofile(trace)
        try: result=self.prepare(execute=True)
        finally: sys.setprofile(previous)
        self.assertEqual(result['status'],'PASS_PREPARE_ONLY')
        self.assertIn(('native_rust_exact_build_input_manifest.py','main'),calls)
        self.assertEqual(calls.count(('native_rust_exact_build_offline.py','verify_inputs')),2)
        self.assertIn(('native_rust_exact_build_container_owner.py','validate'),calls)
        self.assertEqual(sys.path,original_path)
        for name,value in original_modules.items(): self.assertIs(sys.modules.get(name),value)
        candidate=self.scratch/p.CANDIDATE_NAME
        self.assertEqual(self.g(candidate,'rev-parse','HEAD').decode().strip(),self.target)
        self.assertEqual(self.g(candidate,'cat-file','blob',self.historical),b'historical ABI object')
        self.assertEqual(p.snapshot(candidate/self.large),p.snapshot(self.s15/self.large))
        self.assertEqual((candidate/self.large).stat().st_nlink,4)
        self.assertEqual((self.s15/self.large).stat().st_nlink,4)
        self.assertEqual((self.s16/self.large).stat().st_nlink,4)
        self.assertEqual((self.previous/self.large).stat().st_nlink,4)
        for rel in self.private_paths:
            self.assertEqual((candidate/rel).read_bytes(),(self.s16/rel).read_bytes())
            self.assertNotEqual((candidate/rel).stat().st_ino,(self.s16/rel).stat().st_ino)
        self.assertNotEqual((candidate/'.git/index').stat().st_ino,(self.s15/'.git/index').stat().st_ino)
        request=json.loads((self.scratch/p.REQUEST_NAME).read_text())
        self.assertEqual(request['ihk_overlay_base_sha'],self.ihk)
        self.assertEqual(request['ihk_overlay_result_sha'],p.OVERLAY_RESULT_COMMIT_SHA)
        self.assertFalse(request['execution_released'])
        self.assertFalse(Path(request['lease_path']).exists())
        self.assertFalse(Path(request['operational_exclusion_path']).exists())
        self.assertEqual(self.terminal()['returncode'],0)
        self.assertEqual(self.terminal()['phase'],'complete')
        self.assertEqual(self.terminal()['pid'],os.getpid())
        self.assertTrue(self.terminal()['pid_starttime'])
        self.assertEqual(p.digest(self.scratch/p.LOG_NAME),self.terminal()['log_sha256'])

    def test_post_mutation_failure_is_durable_and_preserved(self):
        original=p.Journal.event
        def corrupt(journal,phase,**kwargs):
            original(journal,phase,**kwargs)
            if phase=='canonical-input-verification' and 'returncode' not in kwargs:
                (self.scratch/p.CANDIDATE_NAME/'old0.txt').write_text('corruption\n')
        with mock.patch.object(p.Journal,'event',corrupt):
            with self.assertRaisesRegex(RuntimeError,'Git blob bytes differ'):
                self.prepare(execute=True)
        self.assertEqual(self.terminal()['returncode'],2)
        self.assertEqual(self.terminal()['phase'],'canonical-input-verification')
        self.assertIn('BuildError',self.terminal()['exception'])
        self.assertTrue((self.scratch/p.MANIFEST_NAME).is_file())
        self.assertEqual((self.scratch/p.CANDIDATE_NAME/'old0.txt').read_text(),'corruption\n')
        self.assertEqual((self.s15/'old0.txt').read_text(),'old\n')
        self.assertEqual((self.s15/self.large).stat().st_nlink,4)
        self.assertEqual((self.s16/self.large).stat().st_nlink,4)
        self.assertFalse((self.scratch/p.REQUEST_NAME).exists())

    def test_owner_failure_retains_published_exact_request(self):
        original=p.Journal.event
        def corrupt(journal,phase,**kwargs):
            original(journal,phase,**kwargs)
            if phase=='canonical-owner-validation' and 'returncode' not in kwargs:
                self.receipt.write_text('{}')
        with mock.patch.object(p.Journal,'event',corrupt):
            with self.assertRaisesRegex(ValueError,'image_receipt hash mismatch'):
                self.prepare(execute=True)
        self.assertTrue((self.scratch/p.REQUEST_NAME).is_file())
        self.assertEqual(self.terminal()['phase'],'canonical-owner-validation')
        self.assertEqual(self.terminal()['returncode'],2)

    def test_changed_shared_mode_refused_before_candidate(self):
        (self.s15/self.large).chmod(0o600)
        with self.assertRaisesRegex(p.Refusal,'unauthenticated prior shared evidence'):
            self.prepare(execute=True)
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())
        self.assertEqual(self.terminal()['returncode'],2)

    def test_stale_prior_owner_refused(self):
        prior=self.previous/self.large
        prior.unlink()
        self.put(self.previous,self.large,b'x'*((1<<20)+1))
        with self.assertRaisesRegex(p.Refusal,'prior shared evidence'):
            self.prepare(execute=True)
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())

    def test_extra_prior_owner_link_refused(self):
        extra=self.r/'unrecognized-extra-link.bin'
        os.link(self.s15/self.large,extra)
        with self.assertRaisesRegex(p.Refusal,'prior shared evidence'):
            self.prepare(execute=True)
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())

    def test_changed_shared_bytes_refused_before_candidate(self):
        (self.s15/self.large).write_bytes(b'y'*((1<<20)+1))
        with self.assertRaisesRegex(p.Refusal,'unauthenticated prior shared evidence'):
            self.prepare(execute=True)
        self.assertFalse((self.scratch/p.CANDIDATE_NAME).exists())

    def test_existing_destination_preserved(self):
        candidate=self.scratch/p.CANDIDATE_NAME
        candidate.mkdir()
        with self.assertRaisesRegex(p.Refusal,'destination-present'): self.prepare(execute=True)
        self.assertTrue(candidate.is_dir())
        self.assertFalse((self.scratch/p.LOG_NAME).exists())

    def test_scratch17_destinations_are_not_reused(self):
        # A stale scratch17 destination must remain untouched while scratch18
        # preparation uses only fresh names.
        stale = self.previous
        marker = stale/'do-not-touch'
        marker.write_bytes(b'preserve')
        before = marker.stat()
        result = self.prepare()
        self.assertEqual(result['status'], 'PASS_VALIDATE_ONLY')
        self.assertEqual(marker.read_bytes(), b'preserve')
        self.assertEqual(marker.stat().st_ino, before.st_ino)
        for value in (p.CANDIDATE_NAME, p.MANIFEST_NAME, p.REQUEST_NAME,
                      p.LOG_NAME, p.TERMINAL_NAME, p.LEASE_NAME,
                      p.EXCLUSION_NAME):
            self.assertNotIn('scratch-17', value)
            self.assertTrue('scratch-18' in value or 'scratch18' in value)

    def test_future_target_is_required_and_parent_bound(self):
        with self.assertRaisesRegex(p.Refusal, 'exact future target required'):
            p.prepare(self.src, self.s15, self.scratch, old=self.old,
                      baseline=self.old, target=None, scratch16=self.s16, previous_candidate=self.previous,
                      source_base=self.source_base, expected_shared_files=1)
        with self.assertRaisesRegex(p.Refusal, 'target parent/baseline mismatch'):
            p.prepare(self.src, self.s15, self.scratch, old='0'*40,
                      baseline='0'*40, source_base=self.source_base, target=self.target, scratch16=self.s16, previous_candidate=self.previous,
                      expected_shared_files=1)

    def test_wrong_source_base_is_refused(self):
        with self.assertRaisesRegex(p.Refusal, 'source base is not the reviewed exact source base'):
            self.prepare(source_base='0'*40)

    def test_nonancestor_source_base_is_refused(self):
        unrelated = self.g(self.src,'commit-tree',self.target+'^{tree}',input=b'unrelated source\n').decode().strip()
        target = self.g(self.src,'commit-tree',self.target+'^{tree}','-p',unrelated,
                        input=b'nonancestor target\n').decode().strip()
        self.set_fetched_ref(target)
        original_target, original_tree = p.TARGET, p.TARGET_TREE
        p.TARGET, p.TARGET_TREE = target, self.g(self.src,'rev-parse',target+'^{tree}').decode().strip()
        self.addCleanup(setattr, p, 'TARGET', original_target)
        self.addCleanup(setattr, p, 'TARGET_TREE', original_tree)
        with self.assertRaisesRegex(p.Refusal, 'source base is not an ancestor of baseline'):
            self.prepare(old=unrelated, baseline=unrelated, target=target)

    def test_fetched_descendant_of_target_is_accepted(self):
        descendant = self.g(self.src,'commit-tree',self.target+'^{tree}','-p',self.target,
                            input=b'descendant\n').decode().strip()
        self.set_fetched_ref(descendant)
        self.assertEqual(self.prepare()['status'], 'PASS_VALIDATE_ONLY')

    def test_fetched_baseline_ancestor_is_refused(self):
        self.set_fetched_ref(self.old)
        with self.assertRaisesRegex(p.Refusal, 'target is not reachable from fetched ref'):
            self.prepare()

    def test_fetched_unrelated_commit_is_refused(self):
        unrelated = self.g(self.src,'commit-tree',self.target+'^{tree}',input=b'unrelated\n').decode().strip()
        self.set_fetched_ref(unrelated)
        with self.assertRaisesRegex(p.Refusal, 'target is not reachable from fetched ref'):
            self.prepare()

if __name__=='__main__':
    unittest.main()
