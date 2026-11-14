"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Strict receipt join only: inspect actual independent receipts, never execute workload.
"""
from pathlib import Path
import argparse,hashlib,json
SDK='/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json'
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--stage-result',required=True);p.add_argument('--first-review');p.add_argument('--first-inner-result');p.add_argument('--batch-result');a=p.parse_args(argv)
 raw=Path(a.stage_result).read_bytes();stage=json.loads(raw);manifest_path=Path(a.stage_result).with_name('manifest.json');manifest=json.loads(manifest_path.read_text());sdk=json.loads(Path(SDK).read_text())
 assert {Path(r['path']).name:{'bytes':r['size'],'sha256':r['sha256']}for r in manifest['modules']}=={k:{n:v[n]for n in ('bytes','sha256')}for k,v in sdk['artifacts'].items()}
 assert manifest['artifacts']['mckernel_image']['sha256']=='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'
 assert manifest['artifacts']['mcexec']['sha256']=='dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954'
 assert len(stage['final_map'])==62 and stage['expected_epochs']==[1,2]
 result=dict(status='PASS_ACTUAL_CURRENT_TUPLE_STAGE_RECEIPT_JOIN_ONLY',stage_sha256=hashlib.sha256(raw).hexdigest(),first_complete_restoration=False,ten_cycle_batch=False,automatic_credit=False)
 if a.first_review:
  first=json.loads(Path(a.first_review).read_text());assert first['physical_acceptance'] is True and first['P_M05_02_literal_complete'] is True
  assert a.first_inner_result;inner_raw=Path(a.first_inner_result).read_bytes();assert first['inner_result_sha256']==hashlib.sha256(inner_raw).hexdigest()
  inner=json.loads(inner_raw);argv=inner['admitted_qemu_argv'];assert argv[argv.index('-initrd')+1]==manifest['staging']['derived_initramfs']['path'];result['first_complete_restoration']=True
 if a.batch_result:
  assert result['first_complete_restoration'];batch=json.loads(Path(a.batch_result).read_text());assert batch['profile_id']=='current68-zombie-d8d8-image10972-launcherdca0-p05-short32'
  assert batch['stopped_on_failure']is False and batch['qualified_observations']==10 and len(batch['results'])==10 and batch['prior_cycle_credit_transferred']==0
  result['ten_cycle_batch']=True
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
