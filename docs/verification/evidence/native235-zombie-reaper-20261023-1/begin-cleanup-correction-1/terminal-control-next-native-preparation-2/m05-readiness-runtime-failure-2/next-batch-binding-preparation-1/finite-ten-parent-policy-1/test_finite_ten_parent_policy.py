"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Controlled HOST filesystem directories with exact production-policy shape; UID mismatch mocked.
No production parent publication, Docker, root or native execution.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,os,tempfile,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ten_parent_owner',D/'native_diagnostic_container_owner.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
spec=importlib.util.spec_from_file_location('one_parent_owner',D/'native_diagnostic_container_owner.434b.preimage.py');OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
class PolicyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=D,prefix='ten-host-fixture-');self.root=Path(self.temp.name);self.original=M.HOST_PARENT_BINDINGS;rows=[]
  for i in range(10):
   r=self.root/('m5b%02d'%(i+1));r.mkdir(mode=0o700);p=r/'p';p.mkdir(mode=0o700);rows.append(dict(self.original[i],parent=str(p),retention_parent=str(r),device=p.stat().st_dev))
  M.HOST_PARENT_BINDINGS=tuple(rows)
 def tearDown(self):M.HOST_PARENT_BINDINGS=self.original;self.temp.cleanup()
 def test_declared_production_policy_exact_ten_unique_short_paths(self):
  self.assertEqual(len(self.original),10);self.assertEqual(len({r['parent']for r in self.original}),10)
  for i,r in enumerate(self.original,1):
   self.assertEqual(r['parent'],'/home/holden/mckernel-work/native-runs/m5b%02d/p'%i);self.assertEqual(r['device'],66306);self.assertEqual((r['uid'],r['gid'],r['mode']),(1000,1000,0o700));self.assertLessEqual(len((r['parent']+'/attempt-'+'f'*32+'/qmp.sock').encode()),107)
 def test_actual_filesystem_positive_ten_and_inner_createargv_path_hash(self):
  osha=hashlib.sha256((D/'native_diagnostic_container_owner.py').read_bytes()).hexdigest()
  for i,r in enumerate(M.HOST_PARENT_BINDINGS):
   p=Path(r['parent']);self.assertEqual(M.private_parent(str(p),fresh=True),(p.stat().st_dev,p.stat().st_ino))
   obj=M.DiagnosticOwner(str(p),manifest='/home/holden/mckernel-work/scratch/nm05h2a1/m.json',manifest_sha256='1fb66e1f61d92723b7191ff1464a07df2d3b131f04081a8cd9ca3fc1fc0c3c2d',nonce=('%032x'%(i+1)));argv=obj._create_argv();inner=argv[argv.index(M.IMAGE)+1:];self.assertEqual(inner[inner.index('-B')+1],M.SELF);self.assertEqual(inner[inner.index('--owner-sha256')+1],osha);self.assertIn('type=bind,src='+str(p)+',dst='+str(p),argv)
 def test_outside_allowlist_refused(self):
  p=self.root/'outside';p.mkdir(mode=0o700)
  with self.assertRaisesRegex(M.OwnerError,'one of ten'):M.private_parent(str(p),fresh=True)
 def test_symlink_and_wrong_mode_refused(self):
  row=M.HOST_PARENT_BINDINGS[0];p=Path(row['parent']);p.chmod(0o755)
  with self.assertRaisesRegex(M.OwnerError,'mode0700'):M.private_parent(str(p))
  p.chmod(0o700);p.rename(p.with_name('real'));p.symlink_to(p.with_name('real'),target_is_directory=True)
  with self.assertRaisesRegex(M.OwnerError,'canonical'):M.private_parent(str(p))
 def test_wrong_UID_and_device_refused(self):
  row=M.HOST_PARENT_BINDINGS[0];real=os.fstat
  def uid_mismatch(fd):
   st=real(fd);return types.SimpleNamespace(st_mode=st.st_mode,st_dev=st.st_dev,st_uid=1001,st_gid=st.st_gid,st_ino=st.st_ino)
  with patch.object(M.os,'fstat',side_effect=uid_mismatch):
   with self.assertRaisesRegex(M.OwnerError,'uid/gid1000'):M.private_parent(row['parent'])
  row['device']+=1
  with self.assertRaisesRegex(M.OwnerError,'host-device'):M.private_parent(row['parent'])
 def test_reuse_nonempty_parent_and_retention_sibling_refused(self):
  row=M.HOST_PARENT_BINDINGS[0];p=Path(row['parent']);(p/'previous').touch()
  with self.assertRaisesRegex(M.OwnerError,'fresh empty'):M.private_parent(str(p),fresh=True)
  (p/'previous').unlink();(p.parent/'previous-owner-evidence').touch()
  with self.assertRaisesRegex(M.OwnerError,'dedicated host retention'):M.private_parent(str(p),fresh=True)
 def test_outside_writable_and_all_other_owner_functions_preserved(self):
  p=Path(M.HOST_PARENT_BINDINGS[0]['parent']);M._manifest_outside_writable_parent('/home/holden/mckernel-work/scratch/nm05h2a1/m.json',p)
  with self.assertRaisesRegex(M.OwnerError,'outside writable'):M._manifest_outside_writable_parent(str(p/'manifest.json'),p)
  self.assertEqual(M.SOURCE_HASHES,OLD.SOURCE_HASHES);self.assertEqual(len(M.SOURCE_HASHES),149)
  def funcs(path):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  old=funcs(D/'native_diagnostic_container_owner.434b.preimage.py');new=funcs(D/'native_diagnostic_container_owner.py')
  for name,body in old.items():
   if name!='private_parent':self.assertEqual(new[name],body,name)
if __name__=='__main__':unittest.main(verbosity=2)
