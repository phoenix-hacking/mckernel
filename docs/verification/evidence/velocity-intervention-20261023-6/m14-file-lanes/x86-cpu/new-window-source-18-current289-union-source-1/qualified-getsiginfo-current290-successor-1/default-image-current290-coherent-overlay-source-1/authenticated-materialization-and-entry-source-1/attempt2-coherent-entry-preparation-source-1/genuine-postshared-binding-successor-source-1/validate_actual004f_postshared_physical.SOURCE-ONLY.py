"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact actual004f schema/decision adapter; read retained files only, never observe runtime.
"""
from pathlib import Path
import hashlib,json
ACCEPT = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT290-SHARED-ARCHIVAL-INDEPENDENT-CURRENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '004f4df98b33f930370d842e745935f118dfb7dac0c952f0c84863e69644610e', 'bytes': 7088}
POST = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-ACTUAL-SHARED-ARCHIVAL-POSTRETURN-PROOF.json', 'sha256': 'acc55a86a8eca7a06d678158df7ed447a769c4a9bcf52035fa402968a50d5e4e', 'bytes': 2563}
DECISION='PASS_EXACT_SHARED_RECORD_ARCHIVAL_RECONCILIATION_AND_POSTRETURN_CURRENT_PHYSICAL'
def need(ok,message):
 if not ok:raise RuntimeError('actual post-shared proof: '+message)
def ref(path):
 path=Path(path);h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return dict(path=str(path),sha256=h.hexdigest(),bytes=path.stat().st_size)
def auth(row):
 need(isinstance(row,dict) and set(row)=={'path','sha256','bytes'} and ref(row['path'])==row,'exact retained reference');return Path(row['path'])
def validate(acceptance=ACCEPT,postreturn=POST):
 need(acceptance==ACCEPT and postreturn==POST,'only genuine new004f/acc55 references')
 proof=json.loads(auth(acceptance).read_bytes());post=json.loads(auth(postreturn).read_bytes())
 need(proof['schema']=='mckernel.current290.shared-archival.current-physical.acceptance.v1' and proof['decision']==DECISION,'actual new schema and DECISION field, not oldSDK status')
 need(proof['reviewer']=='/root/review18h' and proof['implementation_ownership'] is False and proof['recorded_by']=='/root','actual independent acceptance role')
 for key in ['raw_and_stat_archive_verified','parent_fsync_completed_before_unlink','active_shared_absent','postreturn_same_mutex27_4_free','helper_direct_join_and_group_absence','original_failed_owner_preserved','retained_input_count134','current_typed_baseline_b4_preserved','all_root_returncodes_zero_and_stderr_empty']:need(proof[key] is True,key)
 need(proof['postreturn_proof']==POST and proof['complete']['sha256']=='1a52c60399c12f48859eddf1623285b24d71d31d09828437b2446636c366a42a','actual complete/postreturn binding')
 need(proof['raw_archive']['sha256']=='324ae871e07d57c1453e57473b64bb31f947d073a9a903b1adca1dad1c1aaaed' and proof['raw_archive']['bytes']==268,'exact oldshared raw archive')
 for row in [proof['raw_archive'],proof['stat_archive'],proof['complete']]:auth(row)
 need(proof['helper']['pid']==898578 and proof['helper']['starttime']=='77303089' and proof['helper']['tool_returncode']==0 and proof['helper']['direct_join_and_group_absence'] is True,'actual helper direct join')
 need(proof['typed_container_count']==44 and proof['publishers']==0 and proof['record_unlinks']==1 and proof['other_record_unlinks']==proof['signals_sent']==proof['Docker_mutations']==0 and proof['original_owner_status']=='FAIL' and proof['historical_label_map_equality']=='UNPROVEN','preserve actual bounded scope and historical limits')
 need(proof['new_heavy_admission_authorized'] is False and proof['build_acceptance'] is False,'physical evidence is not workload admission')
 need(post['tool_session']==67056 and post['tool_joined_exit']==0 and post['helper']==898578 and post['starttime']=='77303089' and post['complete_sha256']==proof['complete']['sha256'],'actual root postreturn join')
 need(len(post['observations'])==2,'two actual postreturn observations')
 for row in post['observations']:need(row['helper898578_absent'] is True and row['group_members']==[] and row['shared_path_absent'] is True and row['permanent_mutex_identity']==[27,4] and row['existing_nonblocking_acquire_release'] is True,'actual postreturn free27:4/absent facts')
 return True
