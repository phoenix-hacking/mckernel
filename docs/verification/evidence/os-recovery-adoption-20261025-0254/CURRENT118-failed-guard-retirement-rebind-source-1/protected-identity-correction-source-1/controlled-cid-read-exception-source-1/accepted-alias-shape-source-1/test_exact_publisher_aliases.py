"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact original publication contract and private disposable two-name test fixtures.
"""
from pathlib import Path
import copy,importlib.util,os,tempfile,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('exact_alias_identity_test',D/'retire_exact_failed_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ExactPublisherAliases(unittest.TestCase):
 def fixture(self,root):
  contract=m.T.authenticated(m.B['publisher_alias_contract'],True);publisher=m.T.load(contract['publisher_source'],'original_accepted_atomic_json_for_TEST_ONLY')
  p=root/'TEST_ONLY.json';publisher.atomic_json(p,dict(TEST_ONLY=True,value='exact immutable metadata'))
  alias=p.with_name(p.name+'.complete-source-'+str(os.getpid()));z=p.lstat()
  fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  pair=dict(canonical=m.T.reference(p),alias=m.T.reference(alias),publisher_pid=os.getpid(),expected={k:getattr(z,k) for k in fields})
  test_contract=dict(contract,pairs=[pair]);original=m.T.authenticated
  def auth(ref,declared_json=False):return test_contract if ref==m.B['publisher_alias_contract'] else original(ref,declared_json)
  return p,alias,pair,auth
 def test_exact_current118_writer_contract_and_six_declared_pairs(self):
  self.assertTrue(m.data());c=m.T.authenticated(m.B['publisher_alias_contract'],True)
  self.assertEqual(c['publisher_source']['sha256'],'1afec85a8ba2a174a8167ebfc18cfcd9c0266fac131ec02b6890443f5befd156');self.assertEqual(len(c['pairs']),6)
  self.assertEqual(c['pairs'][0]['canonical']['bytes'],514);self.assertEqual(c['pairs'][0]['expected']['st_ino'],1206855)
  self.assertTrue(all(p['expected']['st_nlink']==2 and p['expected']['st_mode']&4095==0o400 for p in c['pairs']))
  self.assertLessEqual(max(r['bytes'] for r in m.B['protected']),m.M.FILE_LIMIT)
 def test_real_original_publisher_two_name_shape_passes_exact_adapter(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_alias_') as tmp:
   p,alias,pair,auth=self.fixture(Path(tmp))
   with patch.object(m.T,'authenticated',side_effect=auth):row,raw=m.publisher_alias_identity(p)
   self.assertEqual(row['nlink'],2);self.assertEqual(row['sha256'],pair['canonical']['sha256']);self.assertIsNone(raw)
   with self.assertRaises(m.M.Refusal):m.M.file_identity(p)
 def test_third_link_refused_without_changing_other_files_nlink_contract(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_alias_third_') as tmp:
   p,alias,pair,auth=self.fixture(Path(tmp));os.link(p,Path(tmp)/'unexpected-third-name')
   with patch.object(m.T,'authenticated',side_effect=auth),self.assertRaises(RuntimeError):m.publisher_alias_identity(p)
 def test_known_alias_must_still_be_same_inode_and_never_symlink(self):
  for symlink in [False,True]:
   with tempfile.TemporaryDirectory(prefix='TEST_ONLY_alias_substitution_') as tmp:
    p,alias,pair,auth=self.fixture(Path(tmp));payload=alias.read_bytes();alias.unlink()
    if symlink:alias.symlink_to(p)
    else:alias.write_bytes(payload)
    with patch.object(m.T,'authenticated',side_effect=auth),self.assertRaises((RuntimeError,m.T.Refusal)):m.publisher_alias_identity(p)
 def test_arbitrary_row_never_receives_alias_shape(self):
  with self.assertRaises(RuntimeError):m.publisher_alias_identity(Path('/usr/bin/python3.8'))
if __name__=='__main__':unittest.main(verbosity=2)
