import hashlib, os, stat, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PACKET=ROOT/'docs/verification/evidence/native-exact-mckernel-image-preparation-6fed3a10-exportset25.sh'
class PreparationPacket(unittest.TestCase):
 def test_packet_is_bound_and_data_only(self):
  s=PACKET.read_text(); self.assertIn('6fed3a1022db0b4f9828dd42a8bd8f88fc052053',s); self.assertIn('5688f9c8cb83e2aafb43c6aba8e8ff85fe17ddbc83a5935b6b804c1478bdcb98',s); self.assertIn('request_prepare',s)
  self.assertNotIn('docker run',s); self.assertNotIn('lease',s.split('values=',1)[0])
 def test_rejects_arguments_without_touching_targets(self):
  with tempfile.TemporaryDirectory() as d:
   r=subprocess.run(['/bin/bash',str(PACKET),'--bad'],capture_output=True,text=True); self.assertNotEqual(r.returncode,0)
 def test_shell_syntax_and_private_umask(self):
  self.assertEqual(subprocess.run(['bash','-n',str(PACKET)]).returncode,0); self.assertIn('umask 077',PACKET.read_text())
if __name__=='__main__': unittest.main()
