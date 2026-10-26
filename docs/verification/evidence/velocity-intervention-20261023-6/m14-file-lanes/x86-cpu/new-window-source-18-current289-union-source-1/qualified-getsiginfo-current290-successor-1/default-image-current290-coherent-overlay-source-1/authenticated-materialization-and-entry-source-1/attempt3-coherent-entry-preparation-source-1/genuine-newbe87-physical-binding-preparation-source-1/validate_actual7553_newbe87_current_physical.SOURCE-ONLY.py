"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact genuine new-be87 physical acceptance consumer. Retained JSON/hash reads only.
"""
from pathlib import Path
import hashlib,json
ACCEPT={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT290-NEWBE87-INDEPENDENT-CURRENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '75535d714a2f487f656244f1f341f52cd715bd2df4a08dd4fc479b6a89d80c8a', 'bytes': 8328}
POST={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-ACTUAL-NEWBE87-ARCHIVAL-POSTRETURN-PROOF.json', 'sha256': '8fc905851b1627bbabe0d7fcfd5b98887a213ed2c473ea28b9af3b6cb066eaea', 'bytes': 1135}
SCHEMA='mckernel.current290.newbe87.shared-archival.current-physical.acceptance.v1'
DECISION='PASS_EXACT_NEW_BE87_SHARED_ARCHIVAL_AND_POSTRETURN_CURRENT_PHYSICAL'
def need(ok,message):
 if not ok:raise RuntimeError('actual newbe87 current physical: '+message)
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def auth(row):
 need(isinstance(row,dict) and set(row)=={'path','sha256','bytes'} and ref(row['path'])==row,'exact retained reference');return Path(row['path'])
def validate(acceptance=ACCEPT,postreturn=POST):
 need(acceptance==ACCEPT and postreturn==POST,'only genuine new7553/8fc physical references; old004f cannot clear')
 proof=json.loads(auth(acceptance).read_bytes());post=json.loads(auth(postreturn).read_bytes())
 need(proof['schema']==SCHEMA and proof['decision']==DECISION,'exact newbe87 schema/DECISION; no oldSDK status coercion')
 need(proof['reviewer']=='/root/review18h' and proof['implementation_ownership'] is False and proof['recorded_by']=='/root','actual independent acceptance role')
 for key in ['raw_and_stat_archive_verified','parent_fsync_completed_before_unlink','active_shared_absent','postreturn_same_mutex27_4_free','helper_direct_join_and_group_absence','original_failed_owner_preserved','retained_input_count134','current_typed_baseline_b4_preserved','all_root_returncodes_zero_and_stderr_empty']:need(proof[key] is True,key)
 need(proof['postreturn_proof']==POST and proof['complete']['sha256']=='1abfbe25b61ec4e4d9ca9ecc4690674e608c5bbccd64942ed9af4c12a5864ed2' and proof['prepared']['sha256']=='0f87abb226d71f28557bc3ef7bef8ac52ea6d05d7302bcafe619f3b08b393880','actual complete/prepared/postreturn')
 need(proof['source']['sha256']=='727598f8e6b49dc50d94fcd839e6c2b3038b26a04c6895141d453def9d00c330' and proof['profile']['sha256']=='35ca99a281fdfc0319883f7eae2597b77f02fe70d7c3e554623d67bc0eeed665' and proof['archive_helper']['sha256']=='4e1705ac10fe6728667ea7bebba3794c07957dfa0701d6f22a1b5a36d81517a3','actual corrected archival sources')
 need(proof['process_retirement_acceptance']['sha256']=='19379a929bf045e90caddd5caa6e2cb96e26268a2b9e7d8b37ea01dab9b590d7' and proof['held_readonly_prerequisite']['sha256']=='47799f1d3b6b9082b892641114b91f095da304efdaa4bf4bdeadc546f1795276','actual prerequisite lineage')
 for key in ['source','profile','archive_helper','complete','prepared','raw_archive','stat_archive','process_retirement_acceptance','held_readonly_prerequisite']:auth(proof[key])
 need(proof['raw_archive']['sha256']=='be87556927c1bd55bdf4db6dac6cbb8a035800c0d58727e48187414b2e119fc8' and proof['raw_archive']['bytes']==268 and proof['stat_archive']['sha256']=='8b83dd00bc9f0133cfbeaae6835b25d6daa5fc401cf0d1b731bf2954ce37db00' and proof['archive_manifest_sha256']=='af3bf0327a3f86846a0400cc4c93e5364f1ea0a207afb2888ea07c5ac91fdd36','exact newbe87 raw/stat/manifest')
 need(proof['failed_owner']=={'pid':904301,'starttime':'77396514','normalized_request_sha256':'5a20b25385d0df0dd233539e5f745222990526da14447d7c9053ea646dac74a7'},'actual failed369 owner, distinct future4d')
 need(proof['helper']=={'pid':922472,'starttime':'77744242','parent_pid':922471,'parent_starttime':'77744240','tool_session':24270,'tool_returncode':0,'direct_join_and_group_absence':True},'actual archival helper+wrapper birth/direct join')
 need(proof['required_absent']==63 and proof['publisher_paths']==16 and proof['verified_retained_hashes']==204 and proof['typed_container_count']==44 and proof['publishers']==0 and proof['record_unlinks']==1 and proof['other_record_unlinks']==proof['signals_sent']==proof['Docker_mutations']==0 and proof['original_owner_status']=='FAIL' and proof['historical_label_map_equality']=='UNPROVEN','actual bounded scope and historical limits')
 need(all(proof[k] is False for k in ['new_heavy_admission_authorized','new_admission_authorized','build_acceptance']),'current physical proof is not new workload admission')
 need(post['tool_session']==24270 and post['tool_joined_exit']==0 and post['helper']==922472 and post['starttime']=='77744242' and post['helper_retained_parent_PROC_row']==[922471,842942,'77744240'] and post['complete_sha256']==proof['complete']['sha256'] and post['raw_archive_sha256']==proof['raw_archive']['sha256'] and post['new_admission_authorized'] is False,'genuine postreturn joins/raw binding')
 need(len(post['observations'])==2,'two actual postreturn observations')
 for row in post['observations']:need(row['helper_and_wrapper_absent']==[922472,922471] and row['checked_group_members']=={'922472':[],'922471':[]} and row['shared_be87_path_absent'] is True and row['existing_mutex27_4_nonblocking_acquire_release'] is True,'actual postreturn free27:4/sharedabsence/helpergroups')
 return True
