"""Pure synthetic snapshot fixtures, functional OS only; no security testing.
No subprocess, owner, admission, SDK compile or real source-tree operation.
"""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('snapshot',HERE/'sdk13_data32_input_snapshot.py')
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class SnapshotFixtures(unittest.TestCase):
    def make(self, tmp):
        top=Path(tmp); root=top/'src'; root.mkdir(); (root/'dir').mkdir()
        f=root/'dir'/'input'; f.write_bytes(b'abcd')
        (root/'link').symlink_to('dir/input')
        rows=[{'relative':'dir','kind':'dir'}, {'relative':'dir/input','kind':'file','bytes':4,'sha256':hashlib.sha256(b'abcd').hexdigest()},
              {'relative':'link','kind':'symlink','target':'dir/input'}]
        tree=s.base._tree(root,rows)
        stable=top/'stable'; stable.write_bytes(b'data'); ref=s.base._file(stable)
        work=top/'work'; evidence=top/'evidence'
        snap={'profile':ref,'proposal':ref,'map':ref,'toolchain_manifest':ref,'toolchain_lock':ref,
              'source_identities':{'/src':tree},'work_parent':s.base._directory_identity(top.stat()),
              'evidence_parent':s.base._directory_identity(top.stat())}
        bound={'profile_sha256':'p','proposal_sha256':'q','request_sha256':'r',
               'source_map':{'trees':{'/src':{'entries':rows}}},'source_identities':snap['source_identities'],
               'snapshot':snap,'mounts':[],'commands':[],'outputs':[],
               'profile_path':'profile','request_path':'proposal','source_map_path':'map',
               'lease':top/'lease','work':work,'owner_evidence':evidence,'attempt':evidence/'attempt','work_identity':None}
        request={'source_map_sha256':'map','work_root':str(work),'attempt_root':str(evidence/'attempt'),'lease_path':str(bound['lease'])}
        keys=('profile_sha256','proposal_sha256','request_sha256','source_map','source_identities','snapshot','mounts','commands','outputs','profile_path','request_path','source_map_path')
        lease={'identity':[1,2],'sha256':'lease'}; guard={'identity':'admission'}
        bound['_input_snapshot']={'valid':True,'pid':os.getpid(),'birth':s._birth(),'lease':lease,
          'guard_sha256':s._canonical(guard),'prehashed_sha256':'prehash','expires':1000000,'request_full_sha256':s._canonical(request),
          'bound_sha256':s._canonical({k:bound[k] for k in keys}), 'lease_check':lambda:b'lease', 'admission_check':lambda:guard}
        return bound,request,lease,guard,root,stable

    def run_check(self,bound,request,lease,guard):
        with mock.patch.object(s,'_lease',return_value=lease), mock.patch.object(s,'_guard',return_value=guard):
            s.revalidate(bound,request)

    def test_same_size_file_change_with_restored_mtime_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,r,l,g,root,_=self.make(tmp); self.run_check(b,r,l,g)
            f=root/'dir/input'; st=f.stat(); f.write_bytes(b'wxyz'); os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns))
            with self.assertRaisesRegex(ValueError,'source member changed'): self.run_check(b,r,l,g)
            self.assertFalse(b['_input_snapshot']['valid'])

    def test_new_directory_mask_and_symlink_retarget_fail(self):
        for mutation in ('new','symlink'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                b,r,l,g,root,_=self.make(tmp)
                if mutation=='new': (root/'dir/mask').write_bytes(b'x')
                else: (root/'link').unlink(); (root/'link').symlink_to('dir')
                with self.assertRaisesRegex(ValueError,'changed'): self.run_check(b,r,l,g)
                self.assertFalse(b['_input_snapshot']['valid'])

    def test_root_and_profile_identity_drift_fail(self):
        for mutation in ('root','profile'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                b,r,l,g,root,profile=self.make(tmp)
                if mutation=='root': root.chmod(0o700 if root.stat().st_mode&0o077 else 0o755)
                else: profile.write_bytes(b'xxxx')
                with self.assertRaisesRegex(ValueError,'changed|drift'): self.run_check(b,r,l,g)

    def test_lease_admission_and_request_change_fail(self):
        for mutation in ('lease','admission','request'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                b,r,l,g,_,_=self.make(tmp)
                if mutation=='lease': l={'identity':[1,3],'sha256':'other'}
                elif mutation=='admission': g={'identity':'different'}
                else: r['extra']='different'
                with self.assertRaisesRegex(ValueError,'changed'): self.run_check(b,r,l,g)
                self.assertFalse(b['_input_snapshot']['valid'])

    def test_admission_expiry_is_rejected(self):
        request={'source_map_sha256':'map'}; core=s._canonical(request)
        value={'request_sha256':core,'profile_sha256':s.base.PROFILE_SHA,'source_map_sha256':'map',
               'root_release_identity':{'a':1},'quiescence_identity':{'a':1},'daemon_identity':{'a':1},
               'lease_identity':[1,2],'expires_monotonic_ns':101,'prehashed_sha256':'prehash',
               'snapshot_receipt_identity':{'a':1}}
        with mock.patch.object(s.time,'monotonic_ns',return_value=100):
            s._guard(lambda:value,request,{'identity':[1,2]},101,'prehash')
        with mock.patch.object(s.time,'monotonic_ns',return_value=101):
            with self.assertRaisesRegex(ValueError,'expired'): s._guard(lambda:value,request,{'identity':[1,2]},101,'prehash')

    def test_adoption_checks_prior_hash_and_current_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,_,_,_,root,_=self.make(tmp); rows=b['source_map']['trees']['/src']['entries']
            tree=b['snapshot']['source_identities']['/src']; normalized=[]
            for row in rows:
                if row['kind']!='dir':
                    entry=dict(row); entry['identity']=list(tree['entries'][row['relative']]); normalized.append(entry)
            pre={'root':str(root),'root_identity':list(tree['identity']),'entries':normalized}
            s._adopt_tree(root,rows,pre)
            altered=copy.deepcopy(pre); altered['entries'][0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'byte digest differs'): s._adopt_tree(root,rows,altered)
            (root/'dir/input').write_bytes(b'bad!')
            with self.assertRaisesRegex(ValueError,'file identity changed'): s._adopt_tree(root,rows,pre)

    def test_revalidation_never_rehashes_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,r,l,g,_,_=self.make(tmp)
            with mock.patch.object(s.base,'_collect',side_effect=AssertionError('full pass repeated')):
                self.run_check(b,r,l,g)

if __name__=='__main__': unittest.main(verbosity=2)
