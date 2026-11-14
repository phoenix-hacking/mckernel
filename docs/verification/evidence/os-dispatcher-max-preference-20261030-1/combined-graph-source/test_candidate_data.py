"""Synthetic functional DATA fixtures; no supervisor or production receipts."""
import copy
import json
from pathlib import Path, PurePosixPath
import unittest
import candidate_data as v

EXPECTED_TARGETS = ['/work', '/nightly', '/src', '/out/build', '/src/CMakeLists.txt', '/src/scripts', '/out/source/linux-6.12.0-211.44.1.el10_2', '/src/kernel/CMakeLists.txt', '/src/kernel/process.c', '/src/kernel/rust', '/src/kernel/syscall.c', '/src/host-kernel/native-rust/zero_pages.rs', '/src/kernel/rust/f03_perf_group_cleanup.rs', '/src/kernel/rust/xpmem_helpers.rs', '/src/arch/x86_64/kernel/syscall.c', '/src/host-kernel/native-rust/abi/vdso.rs']


def fixture():
    ids = {}
    def ident(p, kind='directory'):
        if p not in ids:
            ids[p] = dict(device=77, inode=len(ids)+1, kind=kind)
        return copy.deepcopy(ids[p])
    mounts = []
    for i, row in enumerate(v.CONTRACT['mounts']):
        host = row['host'] or '/synthetic-only/' + row['target'].strip('/').replace('/', '-')
        identity = ident(host, 'file' if row['sha256'] else 'directory')
        ancestry = [dict(path=str(p), identity=ident(str(p))) for p in reversed(PurePosixPath(host).parents)]
        parents = [m for m in mounts if PurePosixPath(m['target']) in PurePosixPath(row['target']).parents]
        parent = max(parents, key=lambda m: len(m['target']))['mount_id'] if parents else 9
        mounts.append(dict(host=host, target=row['target'], access=row['access'], identity=identity, ancestry=ancestry, mount_id=100+i, parent_mount_id=parent, content_sha256=row['sha256'] or 'a'*64))
    rust = next(m for m in mounts if m['target']=='/src/kernel/rust')
    pre = dict(parent_identity=copy.deepcopy(rust['identity']), snapshot_sha256='b'*64, members={n:dict(identity=dict(device=88,inode=1000+i,kind='file'),sha256=s) for i,(n,s) in enumerate(v.CONTRACT['rust_parent_members'].items())})
    entries = [{k:copy.deepcopy(m[k]) for k in ('target','identity','mount_id','access','content_sha256')} for m in mounts]
    return dict(synthetic=True,contract_sha256=v.CONTRACT_SHA256,custody=dict(owner='SYNTHETIC-NO-OWNER',pid=123,uid=1000,nonce='SYNTHETIC-NO-AUTH',lease_sha256='c'*64,custody_sha256='d'*64,exclusion='source-writers-excluded-and-work-exclusive'),mounts=mounts,pre_shadow=pre,effective_view=dict(mounts_sha256='e'*64,entries=entries))


class DataTests(unittest.TestCase):
    def parse(self, d): return v.parse_candidate_data(json.dumps(d).encode())
    def reject(self, mutate):
        d=fixture(); mutate(d)
        with self.assertRaises(ValueError): self.parse(d)
    def test_valid_synthetic(self):
        d=self.parse(fixture())
        self.assertEqual([m.target for m in d.mounts],EXPECTED_TARGETS)
        self.assertEqual(len(d.pre_shadow),157)
        self.assertTrue(d.synthetic); self.assertIsNone(d.authority)
        self.assertEqual(d.status,'UNAUTHENTICATED_CANDIDATE_DATA_ONLY')
    def test_every_leaf_null(self):
        original=fixture()
        def leaves(x,p=()):
            if isinstance(x,dict):
                for k,vv in x.items(): yield from leaves(vv,p+(k,))
            elif isinstance(x,list):
                for k,vv in enumerate(x): yield from leaves(vv,p+(k,))
            else: yield p
        for p in leaves(original):
            with self.subTest(path=p):
                d=copy.deepcopy(original); x=d
                for k in p[:-1]: x=x[k]
                x[p[-1]]=None
                with self.assertRaises((ValueError,TypeError)): self.parse(d)
    def test_duplicate_target(self): self.reject(lambda d:d['mounts'].__setitem__(15,copy.deepcopy(d['mounts'][14])))
    def test_duplicate_host(self): self.reject(lambda d:d['mounts'][1].update(host=d['mounts'][0]['host']))
    def test_inode_alias(self): self.reject(lambda d:d['mounts'][1].update(identity=d['mounts'][0]['identity']))
    def test_order(self): self.reject(lambda d:d['mounts'].reverse())
    def test_wrong_ro(self): self.reject(lambda d:d['mounts'][2].update(access='rw'))
    def test_wrong_parent(self): self.reject(lambda d:d['mounts'][12].update(parent_mount_id=999))
    def test_wrong_host(self): self.reject(lambda d:d['mounts'][12].update(host='/synthetic-only/wrong'))
    def test_wrong_identity(self): self.reject(lambda d:d['effective_view']['entries'][12]['identity'].update(inode=999))
    def test_wrong_known_hash(self): self.reject(lambda d:d['mounts'][12].update(content_sha256='0'*64))
    def test_wrong_pre_shadow(self): self.reject(lambda d:d['pre_shadow']['parent_identity'].update(inode=999))
    def test_missing_pre_shadow_member(self): self.reject(lambda d:d['pre_shadow']['members'].pop(next(iter(d['pre_shadow']['members']))))
    def test_ancestry_identity(self): self.reject(lambda d:d['mounts'][2]['ancestry'][0]['identity'].update(inode=999))
    def test_ancestry_missing(self): self.reject(lambda d:d['mounts'][1]['ancestry'].pop())
    def test_duplicate_json_key(self):
        with self.assertRaises(ValueError):v.parse_candidate_data(b'{"synthetic":true,"synthetic":false}')
    def test_boolean_inode(self): self.reject(lambda d:d['mounts'][0]['identity'].update(inode=True))
    def test_no_authority_on_real_tag(self):
        d=fixture();d['synthetic']=False
        parsed=self.parse(d)
        self.assertIsNone(parsed.authority)
        self.assertEqual(parsed.status,'UNAUTHENTICATED_CANDIDATE_DATA_ONLY')

if __name__=='__main__':unittest.main()
