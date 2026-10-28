"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pinned Python3.9 ordinary file-identity/no-follow metadata regression only.
"""
from pathlib import Path
import ast,os,stat,sys,tempfile,unittest
D=Path(__file__).parent
FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
def values(st):return {k:getattr(st,k)for k in FIELDS}
class MetadataAPI(unittest.TestCase):
 def test_regular_file_exact_record_fields(self):
  self.assertEqual(sys.version_info[:2],(3,9))
  with tempfile.TemporaryDirectory(dir=D)as temporary:
   p=Path(temporary)/'regular';p.write_bytes(b'functional-stage-metadata')
   observed=values(p.lstat());expected=values(os.stat(p,follow_symlinks=False))
   self.assertEqual(observed,expected);self.assertEqual(tuple(observed),FIELDS)
   self.assertTrue(stat.S_ISREG(observed['st_mode']));self.assertEqual(observed['st_nlink'],1)
   self.assertEqual(observed['st_size'],len(b'functional-stage-metadata'))
 def test_symlink_no_follow_and_identity_change(self):
  with tempfile.TemporaryDirectory(dir=D)as temporary:
   d=Path(temporary);target=d/'target';target.write_bytes(b'functional-target-data')
   link=d/'link';link.symlink_to(target.name)
   observed=values(link.lstat());expected=values(os.stat(link,follow_symlinks=False))
   self.assertEqual(observed,expected);self.assertEqual(tuple(observed),FIELDS)
   self.assertTrue(stat.S_ISLNK(observed['st_mode']));self.assertEqual(observed['st_size'],len(target.name))
   self.assertNotEqual(observed,values(link.stat()))
   before=values(target.lstat());target.unlink();target.symlink_to(link.name)
   self.assertNotEqual(values(target.lstat()),before)
 def test_exact_single_source_expression_delta(self):
  original=(D.parent/'check_retained_stage.py').read_bytes();corrected=(D/'check_retained_stage_py39.py').read_bytes()
  self.assertEqual(original.count(b"Path(row['path']).stat(follow_symlinks=False)"),1)
  self.assertEqual(corrected,original.replace(b"Path(row['path']).stat(follow_symlinks=False)",b"Path(row['path']).lstat()"))
  ast.parse(corrected)
if __name__=='__main__':unittest.main(verbosity=2)
