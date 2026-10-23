"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic receipts exercise actual join program, no native or acceptance evidence.
"""
from pathlib import Path
from contextlib import redirect_stdout
import copy,hashlib,importlib.util,io,json,tempfile,unittest
A=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/restoration-batch-preparation');s=importlib.util.spec_from_file_location('receipt_join',A/'join_restoration_batch_receipts.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ReceiptJoinTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=Path(self.temp.name)
  self.sdk=json.loads(Path(m.SDK).read_text());old=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/full-tuple-binding-1/actual-stage-1/manifest.json');self.manifest=json.loads(old.read_text());self.manifest['modules']=[dict(path=v['path'],size=v['bytes'],sha256=v['sha256'],mode=33188)for v in self.sdk['artifacts'].values()];self.manifest['staging']['derived_initramfs']['path']='/synthetic/current-zombie-overlay.cpio.gz'
  self.stage=dict(final_map={str(i):{}for i in range(62)},expected_epochs=[1,2]);self.inner=dict(admitted_qemu_argv=['qemu','-initrd','/synthetic/current-zombie-overlay.cpio.gz']);self.first=dict(physical_acceptance=True,P_M05_02_literal_complete=True);self.batch=dict(profile_id='current68-zombie-d8d8-image10972-launcherdca0-p05-short32',stopped_on_failure=False,qualified_observations=10,results=[str(i)for i in range(10)],prior_cycle_credit_transferred=0)
 def run_join(self,first=False,batch=False):
  for name,value in [('manifest.json',self.manifest),('stage-result.json',self.stage),('inner.json',self.inner),('batch.json',self.batch)]: (self.d/name).write_text(json.dumps(value))
  self.first['inner_result_sha256']=hashlib.sha256((self.d/'inner.json').read_bytes()).hexdigest();(self.d/'first.json').write_text(json.dumps(self.first))
  args=['--stage-result',str(self.d/'stage-result.json')]
  if first:args+=['--first-review',str(self.d/'first.json'),'--first-inner-result',str(self.d/'inner.json')]
  if batch:args+=['--batch-result',str(self.d/'batch.json')]
  with redirect_stdout(io.StringIO())as out:m.main(args)
  return json.loads(out.getvalue())
 def test_current_tuple_stage_only_no_credit(self):self.assertFalse(self.run_join()['first_complete_restoration'])
 def test_same_tuple_first_and_ten_receipts_join(self):self.assertTrue(self.run_join(True,True)['ten_cycle_batch'])
 def test_old_first_overlay_refused(self):
  self.inner['admitted_qemu_argv'][-1]='/synthetic/old-20352-overlay'
  with self.assertRaises(AssertionError):self.run_join(True)
 def test_old_module_refused(self):
  self.manifest['modules'][2]['sha256']='0'*64
  with self.assertRaises(AssertionError):self.run_join()
 def test_nine_cycles_refused(self):
  self.batch['qualified_observations']=9
  with self.assertRaises(AssertionError):self.run_join(True,True)
 def test_old_profile_cycle_refused(self):
  self.batch['profile_id']='current68-sdk20352-image10972-launcher0d77-p05-short32'
  with self.assertRaises(AssertionError):self.run_join(True,True)
 def test_prior_cycle_credit_refused(self):
  self.batch['prior_cycle_credit_transferred']=1
  with self.assertRaises(AssertionError):self.run_join(True,True)
 def test_batch_requires_first_actual_review(self):
  with self.assertRaises(AssertionError):self.run_join(False,True)
if __name__=='__main__':unittest.main()
