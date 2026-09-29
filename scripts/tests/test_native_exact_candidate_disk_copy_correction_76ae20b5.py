import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
PACKET = ROOT / 'docs/verification/evidence/native-exact-candidate-disk-copy-correction-76ae20b5-1.sh'

class DiskCopyCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.text = PACKET.read_text()

    def test_shell_and_template(self):
        self.assertEqual(subprocess.run(['/usr/bin/bash','-n',str(PACKET)]).returncode, 0)
        self.assertIn('RELEASE_HASH_REQUIRED', self.text)
        self.assertIn('6603bc25f3c4b4f49a909fac73097a2d5f54b59d4da292868393e0a4b57030db', self.text)
        self.assertRegex(hashlib.sha256(PACKET.read_bytes()).hexdigest(), r'^[0-9a-f]{64}$')

    def test_binds_originals_and_fresh_outputs(self):
        for token in ('SOURCE_ID=26:58679','SOURCE_BACKUP_ID=26:69465','DEST_ID=1831:4194306',
                      'DEST_BACKUP_ID=1831:4204970','ORIGINAL_REQUEST_SHA=',
                      'DEST_INDEX=','DEST_IHK_INDEX=','source-index','source-ihk-index',
                      'GIT_OPTIONAL_LOCKS=0','owner.provenance.ENV=dict',
                      'SOURCE_FINAL_POST','DEST_FINAL_POST','portable inventories differ',
                      'post-validation inventories differ','os.ftruncate(fd,0)',
                      'while view:','BUILD_EVIDENCE','driver_path=str(dest/',
                      'LOG_FINAL_FSYNC=PASS','DERIVED_REQUEST_SHA256='):
            self.assertIn(token, self.text)
        self.assertIn('os.O_EXCL', self.text)
        self.assertIn('os.fchown', self.text)
        self.assertIn('os.O_NOFOLLOW', self.text)
        self.assertIn('os.fsync', self.text)

    def test_no_runtime_or_destructive_operations(self):
        for forbidden in ('rm -','sudo','docker','qemu-system','make -j','cmake --build','BuildOwner(r).run','unlink(','rmtree('):
            self.assertNotIn(forbidden, self.text)

if __name__ == '__main__': unittest.main()
