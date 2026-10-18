"""Cheap no-effect actual owner boundaries; physical admission and release remain separate."""
from pathlib import Path
import importlib.util,json,os,sys,unittest
from unittest import mock
P=Path(__file__).absolute().parent
sys.path.insert(0,str(P))
import native_running_external_modules_owner as m
REAL_MEASURE=m.measure
REAL_LIVE=m.live_admission
sp=importlib.util.spec_from_file_location('canonical_ihk_tests',m.REPO/'scripts/tests/test_native_running_external_modules_owner.py')
base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
# Retain canonical tests but confine every transient fixture to this write allowlist.
base.S=P/'fixture-anchor'/'scripts'
class Tests(base.Tests):
 def setUp(self):
  super().setUp()
  self.patch(m,'HOST_ROOT',self.root)
  self.patch(m,'HOST_DEVICE',self.root.stat().st_dev)
  self.patch(m,'REUSED_INPUT_ROOT',self.i)
 def test_wrong_candidate_parent(self):
  self.q['candidate_root']=str(self.root/'escape'/self.c.name)
  with self.assertRaisesRegex(m.Refusal,'nonce-bound'):self.valid()
 def test_wrong_reused_input(self):
  self.q['input_root']=str(self.root/'other-input')
  with self.assertRaisesRegex(m.Refusal,'reused readonly'):self.valid()
 def test_candidate_symlink_escape(self):
  real=self.c.with_name('real-candidate');self.c.rename(real);self.c.symlink_to(real,target_is_directory=True)
  with self.assertRaisesRegex(m.Refusal,'symlink'):self.valid()
 def measure(self):
  with mock.patch.object(m.host,'measure',return_value={}) as check:
   REAL_MEASURE(self.q)
   return check.call_args.args
 def test_capacity_positive(self):
  args=self.measure();self.assertEqual(args[2:],(18320719872,13488881664))
 def test_candidate_cap_negative(self):
  with (self.c/'cap').open('wb') as f:f.truncate((512<<20)+1)
  with self.assertRaisesRegex(m.Refusal,'budget'):self.measure()
 def test_capture_cap_negative(self):
  q=self.q;d=Path(q['owner_evidence_root']);d.mkdir()
  with (d/'cap').open('wb') as f:f.truncate((64<<20)+1)
  # Modeled scratch device only; the actual type/size/inventory body executes.
  original=Path.lstat
  def ls(p,*a,**kw):
   st=original(p,*a,**kw)
   if p==d or d in p.parents:
    vals=list(st);vals[2]=1828;return os.stat_result(vals)
   return st
  with mock.patch.object(Path,'lstat',ls),mock.patch.object(Path,'stat',ls):
   with self.assertRaisesRegex(m.Refusal,'budget'):self.measure()
 def test_changed_device_negative(self):
  self.patch(m,'HOST_DEVICE',m.HOST_DEVICE+1)
  with self.assertRaisesRegex(m.Refusal,'device'):self.measure()
 def test_hardlink_negative(self):
  os.link(self.c/'modules/ihk.rs',self.c/'extra-link')
  with self.assertRaisesRegex(m.Refusal,'inventory'):self.measure()
 def test_output_symlink_negative(self):
  (self.c/'escape').symlink_to('/etc/passwd')
  with self.assertRaisesRegex(m.Refusal,'inventory'):self.measure()
 def test_host_parent_changed_inode(self):
  with self.assertRaisesRegex(m.Refusal,'parent identity'):m.host_storage_admission()
 def test_unreduced_budget_request_negative(self):
  self.q['disk_budget_bytes']-=1
  with self.assertRaisesRegex(m.Refusal,'budget'):self.valid()
 def test_mount_writable_candidate(self):
  info,name,cid=self.info();m.profile(info,self.q,name,self.nonce,cid)
  row=next(q for q in info['Mounts'] if q['Destination']=='/candidate');self.assertEqual(row['Source'],str(self.c));self.assertTrue(row['RW'])

class MaterializerInputTests(unittest.TestCase):
 def test_existing17_positive(self):
  import materialize_host_candidate as mat
  self.assertEqual(len(mat.validate_inputs(json.loads(mat.PLAN.read_text()))),17)
 def test_changed_input_hash_negative(self):
  import materialize_host_candidate as mat
  plan=json.loads(mat.PLAN.read_text());plan['files'][0]['sha256']='0'*64
  with self.assertRaisesRegex(m.Refusal,'bytes drift'):mat.validate_inputs(plan)

class ActualStorageTests(unittest.TestCase):
 def test_actual_host_mount_positive(self):
  self.assertEqual(m.host_storage_admission()['filesystems'][0]['uuid'],m.HOST_UUID)
 def test_actual_live_two_devices_positive(self):
  import tempfile
  with tempfile.TemporaryDirectory(dir=str(P),prefix='live-fixture-') as tmp:
   q=dict(boot_id=m.BOOT,candidate_root=tmp,input_root=str(m.REUSED_INPUT_ROOT),basis_identity=m.node(m.BASIS),candidate_identity=m.node(Path(tmp)),input_identity=m.node(m.REUSED_INPUT_ROOT))
   observed=REAL_LIVE(q);self.assertIn('host',observed);self.assertIn('scratch',observed)
   q['candidate_identity']['device']=1828
   with self.assertRaisesRegex(m.Refusal,'identity/device'):REAL_LIVE(q)
 def test_actual_host_mount_changed_uuid(self):
  with mock.patch.object(m,'HOST_UUID','changed'):
   with self.assertRaisesRegex(m.Refusal,'UUID/device'):m.host_storage_admission()
 def test_actual_host_mount_changed_device(self):
  with mock.patch.object(m,'HOST_DEVICE',m.HOST_DEVICE+1):
   with self.assertRaisesRegex(m.Refusal,'UUID/device'):m.host_storage_admission()

def load_tests(loader,tests,pattern):
 names=[n for n in loader.getTestCaseNames(Tests) if not n.startswith('test_receipt')]
 return unittest.TestSuite([unittest.TestSuite(Tests(n) for n in names),loader.loadTestsFromTestCase(ActualStorageTests),loader.loadTestsFromTestCase(MaterializerInputTests)])
if __name__=='__main__':unittest.main(verbosity=2)
