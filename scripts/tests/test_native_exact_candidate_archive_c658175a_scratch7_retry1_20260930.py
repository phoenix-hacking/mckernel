import importlib.util, json, os, pathlib, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parents[2]
PACKET = ROOT/'docs/verification/evidence/native-exact-candidate-archive-c658175a-scratch7-retry1-20260930.py'
spec = importlib.util.spec_from_file_location('packet_c658', PACKET)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class ArchivePacketTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); t=pathlib.Path(self.td.name)
        self.out=t/'out'; self.ev=t/'ev'; self.out.mkdir(); self.ev.mkdir()
        (self.out/'nested').mkdir(); (self.out/'nested'/'artifact').write_bytes(b'output')
        (self.ev/'build').mkdir(); (self.ev/'receipt.json').write_bytes(b'owner')
        (self.ev/'build'/'receipt.json').write_bytes(b'build'); (self.ev/'build'/'driver.log').write_bytes(b'log')
        self.files=[self.out,self.ev]
        self.request=t/'request'; self.manifest=t/'manifest'; self.prep=t/'prep'; self.preplog=t/'preplog'; self.ex=t/'ex'; self.failure=t/'failure'
        for p,b in [(self.request,b'r'),(self.manifest,b'm'),(self.prep,b'p'),(self.preplog,b'l'),(self.ex,b'x'),(self.failure,b'f')]: p.write_bytes(b)
        self.archive=t/'archive.tar'; self.candidate=t/'candidate'; self.candidate.mkdir()
        vals={'OUTPUT':self.out,'EVIDENCE':self.ev,'REQUEST':self.request,'MANIFEST':self.manifest,'PREP':self.prep,'PREP_LOG':self.preplog,'EXCLUSION':self.ex,'FAILURE':self.failure,'ARCHIVE':self.archive,'CANDIDATE':self.candidate}
        for k,v in vals.items(): setattr(m,k,v)
        m.ROOT_IDS={self.out:f'{self.out.stat().st_dev}:{self.out.stat().st_ino}',self.ev:f'{self.ev.stat().st_dev}:{self.ev.stat().st_ino}'}
        m.EXCLUSION_ID=f'{self.ex.stat().st_dev}:{self.ex.stat().st_ino}'
        m.INPUT_DEVICE=self.out.stat().st_dev
        m.INPUTS=[(self.out,'output'),(self.ev,'evidence'),(self.request,'request'),(self.manifest,'manifest'),(self.prep,'prep-terminal'),(self.preplog,'prep-log'),(self.ex,'runtimeblob12-exclusion'),(self.failure,'failure-record')]
        m.EXPECTED={p:m.digest(p) for p in (self.request,self.manifest,self.prep,self.preplog,self.ex,self.failure)}
        m.REFERENCED={self.ev/'receipt.json':m.digest(self.ev/'receipt.json'),self.ev/'build/receipt.json':m.digest(self.ev/'build/receipt.json'),self.ev/'build/driver.log':m.digest(self.ev/'build/driver.log')}
        m.CANDIDATE_ID=f'{self.candidate.stat().st_dev}:{self.candidate.stat().st_ino}'
    def tearDown(self): self.td.cleanup()
    def test_recursive_snapshot_and_candidate_exclusion(self):
        rows=m.inventory(); self.assertIn(('output/nested/artifact','file',(self.out/'nested'/'artifact').stat().st_mode & 0o7777,6,(self.out/'nested'/'artifact').stat().st_mtime_ns,m.digest(self.out/'nested'/'artifact')),rows)
        old=os.environ.get('ARCHIVE_RELEASE'); os.environ['ARCHIVE_RELEASE']='1'
        try: m.make_archive(rows)
        finally:
            if old is None: os.environ.pop('ARCHIVE_RELEASE',None)
            else: os.environ['ARCHIVE_RELEASE']=old
        import tarfile
        with tarfile.open(self.archive) as tf:
            names=tf.getnames(); self.assertIn('evidence/build/driver.log',names); self.assertFalse(any('candidate' in n for n in names))
    def test_rejects_symlink_and_hardlink(self):
        (self.ev/'bad').symlink_to(self.request); self.assertRaises(RuntimeError,m.inventory)
        (self.ev/'bad').unlink(); os.link(self.request,self.ev/'hard'); self.assertRaises(RuntimeError,m.inventory)
    def test_no_replace_and_release_gate(self):
        rows=m.inventory(); self.archive.write_bytes(b'existing'); self.assertRaises(RuntimeError,m.make_archive,rows)
        self.archive.unlink(); os.environ.pop('ARCHIVE_RELEASE',None)
        with mock.patch('sys.argv',['packet','--release']): self.assertRaises(RuntimeError,m.main)
    def test_digest_binding(self):
        self.request.write_bytes(b'changed'); self.assertRaises(RuntimeError,m.inventory)

    def test_candidate_and_live_exclusion_identity_are_mandatory(self):
        m.CANDIDATE_ID='1831:wrong'; self.assertRaises(RuntimeError,m.inventory)
        m.CANDIDATE_ID=f'{self.candidate.stat().st_dev}:{self.candidate.stat().st_ino}'
        m.EXCLUSION_ID='1831:wrong'; self.assertRaises(RuntimeError,m.inventory)

    def test_tree_traversal_errors_are_fatal(self):
        def broken(root, **kwargs):
            kwargs['onerror'](OSError('injected traversal failure'))
            return iter(())
        with mock.patch.object(m.os, 'walk', side_effect=broken):
            self.assertRaises(RuntimeError, m.inventory)

if __name__ == '__main__': unittest.main()
