"""Actual main entry-path regression; root/release/profile boundaries mocked.
All source, case, predecessor and artifact reads use real stable_bytes. Stop
immediately after actual prerequisite joins, before any observation or lock.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/m07-sigill-successor-native-data-preparation-20261022-1/actual-terminal-preparation-1/bound-terminal-source-correction-1')
class EntryComplete(Exception):pass

def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def entry(module,case_path=None):
 if case_path is not None:
  module.FAILURE_CASE=case_path;module.FAILURE_CASE_SHA=hashlib.sha256(case_path.read_bytes()).hexdigest()
 original=module.current_pass_prerequisites
 def joined(*args):
  original(*args)
  raise EntryComplete('all genuine prerequisite joins passed; no observation attempted')
 with patch.object(module.os,'getuid',return_value=0),patch.object(module.os,'geteuid',return_value=0),patch.object(module.resource,'setrlimit'),patch.object(module,'validate_observation_release',return_value={}),patch.object(module,'current_pass_prerequisites',side_effect=joined):
  # Directory/lock/subprocess boundaries remain unavailable even if entry changes.
  with patch.object(module.os,'mkdir',side_effect=AssertionError('mutation forbidden')),patch.object(module.fcntl,'flock',side_effect=AssertionError('locking forbidden')),patch.object(module.subprocess,'run',side_effect=AssertionError('child forbidden')):
   module.main(['--git-commit','0'*40,'--git-tree','0'*40,'--observation-release','/not-used','--observation-release-sha256','0'*64])

def main():
 original=load(OLD/'observe_current_pass_image_retirement.py','original_observer')
 try:entry(original)
 except TypeError as exc:assert "NoneType" in str(exc)
 else:raise AssertionError('original null entry defect not reproduced')
 fixed=load(HERE/'observe_current_pass_image_retirement.py','corrected_observer')
 try:entry(fixed)
 except EntryComplete:pass
 else:raise AssertionError('corrected real entry failed to reach joined boundary')
 case=json.loads((HERE/'PASS-CASE-STATIC.json').read_bytes())
 assert case['current_live_postjoin']==case['finite_roles']['guard_postjoin']
 assert all(case[k] is None for k in ('postjoin_result','cleanup_release','cleanup_result','observation','observation_release'))
 variants=[]
 c=copy.deepcopy(case);c['current_live_postjoin']=None;variants.append(('null',c,'exact genuine predecessor'))
 c=copy.deepcopy(case);del c['current_live_postjoin'];variants.append(('missing',c,'exact genuine predecessor'))
 c=copy.deepcopy(case);c['current_live_postjoin']={'path':'/nonexistent-future-cleanup-postjoin','sha256':'0'*64};variants.append(('future-substitution',c,'exact genuine predecessor'))
 c=copy.deepcopy(case);c['current_live_postjoin']['sha256']='0'*64;variants.append(('reference-drift',c,'exact genuine predecessor'))
 c=copy.deepcopy(case);c['current_live_postjoin']['sha256']='0'*64;c['finite_roles']['guard_postjoin']['sha256']='0'*64;variants.append(('receipt-hash-drift',c,'source digest differs'))
 c=copy.deepcopy(case);c['target']['container_id']='wrong';variants.append(('target-drift',c,'retained target mismatch'))
 c=copy.deepcopy(case);c['artifact_acceptance']['sha256']='0'*64;variants.append(('artifact-hash-drift',c,'source digest differs'))
 refused=[]
 for label,c,reason in variants:
  path=HERE/('negative-'+label+'.json');path.write_text(json.dumps(c,sort_keys=True)+'\n')
  fixed=load(HERE/'observe_current_pass_image_retirement.py','corrected_'+label.replace('-','_'))
  try:entry(fixed,path)
  except RuntimeError as exc:
   assert reason in str(exc),(label,str(exc));refused.append(label)
  else:raise AssertionError('negative entry accepted:'+label)
 print(json.dumps(dict(status='PASS_ACTUAL_MAIN_PREREQUISITE_ENTRY_ONLY',original_TypeError_reproduced=True,positive_real_bound_inputs=True,negative_refusals=refused,root_release_profile_boundaries_mocked=True,source_case_receipt_artifact_reads_real=True,no_root_observation_or_cleanup=True,physical_clearance=False,execution_authorized=False),sort_keys=True))
if __name__=='__main__':main()
