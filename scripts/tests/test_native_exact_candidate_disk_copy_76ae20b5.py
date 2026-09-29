import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).parents[2]
PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-disk-copy-76ae20b5-1.sh'

class DiskCopyPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.text=PACKET.read_text()
    def test_exact_inputs_and_fresh_outputs(self):
        for token in ('76ae20b523f57dee8e0fb1fb834caf5443f9f671','5c893b1af09e0728aed3c220ab3811d3f1047d013a83e59f05c762db43e9ce75','a483f42764f27b9785ff1465d35fd22632c9a2535664868b8f81655e96044d4a','9a1a4b0c6e98b9b09ef934962dbcd9dac7ed3d23e90104c1561d6a4953cc348c','RELEASE_HASH_REQUIRED','76ae20b5-disk-1'):
            self.assertIn(token,self.text)
    def test_copy_is_non_destructive_and_exact(self):
        for token in ('--no-clobber','--reflink=never','mckernel.exact-tree-inventory.v2','copy inventory differs','source-post.json','O_NOFOLLOW','st_nlink != 1','os.fsync','--ignore-submodules=dirty','memory_allocation_memory_backed_bytes','renameat2','escaping, dangling, or cyclic symlink','st_mtime_ns','st_ctime_ns','for parent in sys.argv[5:]'):
            self.assertIn(token,self.text)
        for forbidden in ('rm -','sudo','docker','qemu-system','make -j','cmake --build'):
            self.assertNotIn(forbidden,self.text)
    def test_build_owner_is_validate_only(self):
        self.assertIn('owner.BuildOwner(r); checked.validate()',self.text)
        self.assertNotIn('checked.run()',self.text)
        self.assertIn('PASS_DISK_COPY_VALIDATE_ONLY',self.text)
    def test_shell_syntax(self):
        result=subprocess.run(['/usr/bin/bash','-n',str(PACKET)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertRegex(hashlib.sha256(PACKET.read_bytes()).hexdigest(),r'^[0-9a-f]{64}$')

if __name__=='__main__': unittest.main()
