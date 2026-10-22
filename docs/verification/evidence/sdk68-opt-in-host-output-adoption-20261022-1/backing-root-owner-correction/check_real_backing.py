"""Focused real-backing stat/node checks; no image read, root or Docker."""
import ast,copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,'/home/holden/mckernel/scripts')
spec=importlib.util.spec_from_file_location('backing_successor',HERE/'native_running_external_modules_owner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Backing(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=HERE);self.addCleanup(self.tmp.cleanup);self.parent=Path(self.tmp.name)
  meta=m.BACKING.stat();self.actual_backing=dict(m.node(m.BACKING),size=meta.st_size,nlink=meta.st_nlink)
  self.assertEqual((meta.st_dev,meta.st_ino,meta.st_uid,meta.st_gid,meta.st_size),(66306,47468427,0,0,118111600640))
  self.request=dict(output_parent_identity=m.node(self.parent),backing_identity=copy.deepcopy(self.actual_backing))
  self.mount={'filesystems':[dict(target='/',uuid=m.HOST_UUID,fstype='ext4',options='rw,relatime')]}
 def run_admission(self):
  with mock.patch.object(m,'OUTPUT_PARENT',self.parent),mock.patch.object(m.subprocess,'check_output',return_value=json.dumps(self.mount).encode()):return m.output_admission(self.request)
 def bad(self,key,value):
  self.request['backing_identity'][key]=value
  with self.assertRaisesRegex(m.Refusal,'110GiB root-owned backing'):self.run_admission()
 def test_real_root_owned_backing_positive(self):
  self.assertEqual(len(self.run_admission()['filesystems']),1)
  self.assertEqual(self.request['backing_identity'],self.actual_backing)
 def test_wrong_uid_refused(self):self.bad('uid',1000)
 def test_wrong_gid_refused(self):self.bad('gid',1000)
 def test_wrong_inode_refused(self):self.bad('inode',47468428)
 def test_wrong_size_refused(self):self.bad('size',118111600640-4096)
 def test_wrong_mode_refused(self):self.bad('mode',0o644)
 def test_wrong_nlink_refused(self):self.bad('nlink',2)
 def test_scratch_output_namespace_refused(self):
  self.request['output_parent_identity']=m.node(m.ROOT)
  with mock.patch.object(m,'OUTPUT_PARENT',m.ROOT),self.assertRaisesRegex(m.Refusal,'host output parent identity/device/owner'):m.output_admission(self.request)
 def test_host_parent_root_uid_claim_refused(self):
  self.request['output_parent_identity']['uid']=0
  with self.assertRaisesRegex(m.Refusal,'host output parent identity/device/owner'):self.run_admission()
 def test_only_output_admission_AST_changed_and_canonical_guards_preserved(self):
  def funcs(raw):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
  before=funcs(Path('/home/holden/mckernel/scripts/native_running_external_modules_owner.py').read_bytes());after=funcs((HERE/'native_running_external_modules_owner.py').read_bytes())
  self.assertEqual(set(before),set(after));self.assertEqual([k for k in before if before[k]!=after[k]],['output_admission'])
  self.assertNotIn('RUNTIME_OVERRIDES',(HERE/'native_running_external_modules_owner.py').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
