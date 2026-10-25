"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
AST-isolated real Transaction.pinned regression; all filesystem/lock services mocked.
"""
import ast,copy,types,unittest
from pathlib import Path
SOURCE=Path(__file__).with_name('cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py')
PARENT='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/proof-path-correction-source-1/cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py'
class Refusal(Exception):pass
class PinnedNamespace(unittest.TestCase):
 def setUp(self):
  self.meta=types.SimpleNamespace(st_dev=101,st_ino=202,st_mode=0o40700,st_uid=1000,st_gid=1000)
  self.binding=dict(path='/fixture/namespace',device=101,inode=202,mode=0o40700,uid=1000,gid=1000)
  self.rootlock=dict(device=27,inode=4);self.ancestor=['root-ancestor'];self.nsancestor=['namespace-ancestor'];self.chain=['root-chain'];self.nchain=['namespace-chain'];self.saved=copy.copy(self.meta)
 def call(self,source=SOURCE):
  tree=ast.parse(source.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Transaction');method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='pinned')
  rootmeta=types.SimpleNamespace(st_dev=27,st_ino=4)
  def fstat(fd):return rootmeta if fd==1 else self.saved if fd==2 else self.meta
  def directory(path):return (3,self.chain) if path=='ROOT' else (4,self.nchain)
  env=dict(validate_mount=lambda:None,observe_identity=lambda path:self.rootlock,ROOT_LOCK_BINDING=self.rootlock,ROOT_LOCK='LOCK',identity=lambda m:(m.st_dev,m.st_ino),os=types.SimpleNamespace(fstat=fstat,close=lambda fd:None),Path=lambda path:types.SimpleNamespace(read_text=lambda:'BOOT'),BOOT_ID='BOOT',directory=directory,ROOT='ROOT',NAMESPACE='/fixture/namespace',NAMESPACE_BINDING=self.binding,NAMESPACE_ANCESTRY=['namespace-ancestor'],namespace_ancestry=lambda:self.nsancestor,Refusal=Refusal)
  exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual-Transaction.pinned>','exec'),env)
  obj=types.SimpleNamespace(rfd=1,nfd=2,fd=3,mfd=None,chain=['root-chain'],namespace_chain=['namespace-chain'])
  return env['pinned'](obj)
 def test_original_mismatch_reproduced(self):
  with self.assertRaisesRegex(Refusal,'namespace-parent-replaced'):self.call(Path(PARENT))
 def test_exact_current_identity_accepted(self):self.call()
 def test_each_wrong_binding_field_rejected(self):
  for key in self.binding:
   with self.subTest(field=key):
    saved=self.binding[key];self.binding[key]='WRONG' if key=='path' else saved+1
    with self.assertRaisesRegex(Refusal,'namespace-parent-replaced'):self.call()
    self.binding[key]=saved
 def test_wrong_root_ancestor_rejected(self):
  self.chain=['replaced']
  with self.assertRaisesRegex(Refusal,'ancestor-replaced'):self.call()
 def test_wrong_namespace_ancestor_rejected(self):
  self.nsancestor=['replaced']
  with self.assertRaisesRegex(Refusal,'namespace-parent-replaced'):self.call()
 def test_wrong_namespace_chain_rejected(self):
  self.nchain=['replaced']
  with self.assertRaisesRegex(Refusal,'namespace-parent-replaced'):self.call()
 def test_replaced_open_namespace_fd_rejected(self):
  self.saved.st_ino+=1
  with self.assertRaisesRegex(Refusal,'namespace-parent-replaced'):self.call()
if __name__=='__main__':unittest.main()
