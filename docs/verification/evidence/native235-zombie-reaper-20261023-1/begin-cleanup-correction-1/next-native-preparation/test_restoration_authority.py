"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual stager authority/selection bodies with explicitly synthetic new SDK documents.
No binary reads, authority claims, archive transforms, stages or native execution.
"""
from pathlib import Path
import copy,importlib.util,json,unittest
F=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/begin-cleanup-native-successor-2')
S=F/'restoration-batch-readiness-1/stage-binding'
spec=importlib.util.spec_from_file_location('begin_stager_body',S/'stage_m05_two_generation.TEMPLATE.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def load(p):return json.loads(Path(p).read_text())
def fixture():
 b=load(S/'BINDING.PENDING.json');sdkpath='/explicit-fixture-only/accepted-sdk.json';sdksha='c'*64;patchsha='d'*64
 m.SDK_SUCCESSOR_PATH=sdkpath;m.SDK_SUCCESSOR_SHA=sdksha;m.SDK_SUCCESSOR_DECISION='EXPLICIT_FIXTURE_ACCEPTANCE';m.SNAPSHOT_BINDING_SHA=patchsha
 b['authority']['current_SDK_acceptance']=dict(path=sdkpath,sha256=sdksha,size=1,mode=33152);b['authority']['begin_snapshot_binding']=dict(path=m.SNAPSHOT_BINDING_PATH,sha256=patchsha,size=1,mode=33152)
 for member,sha in [('modules/ihk-smp-x86_64.ko','a'*64),('modules/mcctrl.ko','b'*64)]:b['replacements'][member].update(sha256=sha,size=1234)
 sdk=dict(status='PASS',implementation_ownership=False,decision=m.SDK_SUCCESSOR_DECISION,physical_acceptance=True,native_acceptance=False,source_identity='db7f2ac4ddc023874ddf6b2b8de2c86c41bbf6efb601f33d4d0f501aa1957598',artifacts={Path(k).name:dict(bytes=v['size'],sha256=v['sha256'])for k,v in b['replacements'].items()if k.startswith('modules/')})
 patch=dict(matched_artifact_acceptance=dict(sdk=dict(path=sdkpath,sha256=sdksha)),changed_record_allowlist=['modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'],new_runtime_tuple={k:copy.deepcopy(b['replacements'][k])for k in ['modules/ihk-smp-x86_64.ko','modules/mcctrl.ko']})
 docs=dict(current_SDK_acceptance=sdk,begin_snapshot_binding=patch,v3_snapshot_receipt=load(b['authority']['v3_snapshot_receipt']['path']))
 old=load(b['authority']['baseline_overlay_manifest']['path'])['final_map']
 return b,docs,old
class Checks(unittest.TestCase):
 def test_exact_two_member_authority(self):
  b,d,old=fixture();m.sdk_artifact_authority(d,b);self.assertEqual(len(old),62)
 def test_same_five_selection_and_57_original_members(self):
  b,d,old=fixture();final=m.validate_selection(b['replacements'],old,b);self.assertEqual(sum(old[k]==final[k]for k in old),57)
 def test_old_one_member_binding_refused(self):
  b,d,_=fixture();d['begin_snapshot_binding']['changed_record_allowlist']=['modules/mcctrl.ko']
  with self.assertRaises(ValueError):m.sdk_artifact_authority(d,b)
 def test_mixed_smp_snapshot_refused(self):
  b,d,_=fixture();b['replacements']['modules/ihk-smp-x86_64.ko']['sha256']='0'*64
  with self.assertRaises(ValueError):m.sdk_artifact_authority(d,b)
 def test_mixed_mcctrl_snapshot_refused(self):
  b,d,_=fixture();b['replacements']['modules/mcctrl.ko']['sha256']='0'*64
  with self.assertRaises(ValueError):m.sdk_artifact_authority(d,b)
 def test_changed_ihk_refused(self):
  b,d,_=fixture();b['replacements']['modules/ihk.ko']['sha256']='0'*64
  with self.assertRaises(ValueError):m.sdk_artifact_authority(d,b)
 def test_wrong_sdk_source_refused(self):
  b,d,_=fixture();d['current_SDK_acceptance']['source_identity']='0'*64
  with self.assertRaises(ValueError):m.sdk_artifact_authority(d,b)
 def test_oracle_drift_refused(self):
  b,d,old=fixture();b['payload_contract']['oracle']['stdout_hex']=''
  with self.assertRaises(ValueError):m.validate_selection(b['replacements'],old,b)
 def test_null_new_descriptor_refused(self):
  b,d,_=fixture();b['replacements']['modules/ihk-smp-x86_64.ko']['sha256']=None
  with self.assertRaises(ValueError):m.sdk_artifact_authority(d,b)
if __name__=='__main__':unittest.main(verbosity=2)
