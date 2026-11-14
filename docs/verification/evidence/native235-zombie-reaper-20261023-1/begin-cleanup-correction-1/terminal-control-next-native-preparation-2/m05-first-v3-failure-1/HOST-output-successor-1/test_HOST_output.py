"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Controlled directories and policy binding; no Docker or native execution.
"""
from pathlib import Path
import ast,hashlib,importlib.util,os,tempfile,unittest
D=Path(__file__).resolve().parent
BASE=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/sdk5-successor-1/runtime-cohort-1')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
NEW=load('M05_HOST_owner',D/'native_diagnostic_container_owner.py')
OLD=load('M05_accepted_owner',BASE/'native_diagnostic_container_owner.py')
EXISTING=load('accepted_eight_hook_fixtures',BASE/'test_cohort.py')
class HostTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=D,prefix='controlled-output-');self.root=Path(self.tmp.name);self.p=self.root/'p';self.p.mkdir(mode=0o700);self.binding=NEW.HOST_OUTPUT;NEW.HOST_OUTPUT=dict(self.binding,parent=str(self.p),retention_parent=str(self.root),device=self.p.stat().st_dev)
 def tearDown(self):NEW.HOST_OUTPUT=self.binding;self.tmp.cleanup()
 def test_real_private_parent_and_fresh_retention_guard(self):
  self.assertEqual(NEW.private_parent(str(self.p)),(self.p.stat().st_dev,self.p.stat().st_ino));NEW._host_output(str(self.p),NEW.HOST_OUTPUT,fresh=True)
  (self.p/'existing').touch()
  with self.assertRaisesRegex(NEW.OwnerError,'fresh empty'):NEW._host_output(str(self.p),NEW.HOST_OUTPUT,fresh=True)
 def test_incompatible_device_rejected(self):
  NEW.HOST_OUTPUT['device']+=1
  with self.assertRaisesRegex(NEW.OwnerError,'host-device'):NEW.private_parent(str(self.p))
 def test_wrong_path_mode_and_symlink_rejected(self):
  other=self.root/'other';other.mkdir(mode=0o700)
  with self.assertRaises(NEW.OwnerError):NEW.private_parent(str(other))
  self.p.chmod(0o755)
  with self.assertRaisesRegex(NEW.OwnerError,'mode0700'):NEW.private_parent(str(self.p))
  self.p.chmod(0o700);link=self.root/'link';link.symlink_to(self.p,target_is_directory=True)
  with self.assertRaises(NEW.OwnerError):NEW.private_parent(str(link))
 def test_real_create_argv_retains_profile_mounts_and_log_policy(self):
  def owner(mod):
   o=object.__new__(mod.DiagnosticOwner);o.parent=self.p;o.nonce='1'*32;o.name='mckernel-native-diagnostic-'+o.nonce;o.label='mckernel.native-diagnostic.owner='+o.nonce;o.owner_sha='a'*64;o.manifest_path='/home/holden/mckernel-work/scratch/nm05p5a1/m.json';o.manifest_sha256='8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7';return o
  new=owner(NEW)._create_argv();old=owner(OLD)._create_argv();mount='type=bind,src='+str(Path(NEW.SELF).parent)+',dst='+str(Path(NEW.SELF).parent)+',readonly';i=new.index(mount);self.assertEqual(new[i-1],'--mount');del new[i-1:i+1];new=[OLD.SELF if x==NEW.SELF else x for x in new];self.assertEqual(new,old);self.assertIn('type=bind,src='+NEW.SCRATCH+',dst='+NEW.SCRATCH+',readonly',new);self.assertIn('type=bind,src='+str(self.p)+',dst='+str(self.p),new);self.assertFalse(any(x.startswith('--log-')for x in new))
 def test_hooks_source_map_and_nonselected_functions_unchanged(self):
  self.assertEqual(NEW.SOURCE_HASHES,OLD.SOURCE_HASHES);self.assertEqual(NEW.RUNNER,OLD.RUNNER)
  def funcs(path):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  new=funcs(D/'native_diagnostic_container_owner.py');old=funcs(BASE/'native_diagnostic_container_owner.py')
  for name,body in old.items():
   if name!='private_parent':self.assertEqual(new[name],body,name)
def load_tests(loader,tests,pattern):
 suite=unittest.TestSuite();suite.addTests(loader.loadTestsFromTestCase(HostTests));suite.addTests(loader.loadTestsFromTestCase(EXISTING.CohortTests));return suite
if __name__=='__main__':unittest.main(verbosity=2)
