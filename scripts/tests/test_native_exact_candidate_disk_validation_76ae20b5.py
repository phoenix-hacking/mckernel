import subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).parents[2]
PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-disk-validation-76ae20b5-2.sh'
class ValidationPacketTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.text=PACKET.read_text()
 def test_syntax_and_template(self):
  self.assertEqual(subprocess.run(['/usr/bin/bash','-n',str(PACKET)]).returncode,0)
  self.assertIn('RELEASE_HASH_REQUIRED',self.text)
  self.assertIn('f0a625768a4d10c6bf42794cc502148c5bac6b13683f5c3bb37138a4f922f303',self.text)
 def test_bindings_and_no_mutation(self):
  for t in ('1831,4204970','e2a7cd887df743587dd05c9d9e63252829e4ad004f7954a143760b3af752190c','6afcf2d1f260bc30b08f21ebf133af3cfc0a9410f3c69f0dfd221ecff4e4c2ba','192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c','dbe24f5b7cdd94f9ba2f9846073b6b2cd6e5f00ffca55f4ce99d4343261b5100','431e26b1d2c5acb2c4c0c586b3f3bcbd1dea88e51ac5bdf57613fe774cd7f2d3','f4ee6d4c458243c566a5c29fcc0023475d16df78170e111dfc110ddae51ca304','mckernel.exact-tree-inventory.v2','GIT_OPTIONAL_LOCKS=0','os.O_NOFOLLOW','os.O_EXCL','EXPECTED_CORRUPT_GZIP_FAIL','PASS_DISK_VALIDATION'):
   self.assertIn(t,self.text)
  for t in ('unlink(','rmtree(','truncate','docker','qemu-system','BuildOwner(r).run'):
   self.assertNotIn(t,self.text)
if __name__=='__main__': unittest.main()
