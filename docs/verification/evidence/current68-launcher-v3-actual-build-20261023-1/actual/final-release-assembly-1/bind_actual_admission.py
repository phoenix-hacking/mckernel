"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual read-only admission to private review payloads; no root/build operation.
"""
from pathlib import Path
import argparse,hashlib,json
D=Path(__file__).resolve().parent;L=D.parent;B=L/'bound-source-1';R=L.parent.parent

def sha(raw):return hashlib.sha256(raw).hexdigest()
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),sha256=sha(raw),bytes=len(raw))
def load(path):return json.loads(Path(path).read_bytes())
def exact(path,digest):
 raw=Path(path).read_bytes();assert sha(raw)==digest;return json.loads(raw)
def save(path,value):
 raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def main():
 p=argparse.ArgumentParser();p.add_argument('--admission',required=True);p.add_argument('--admission-sha256',required=True);p.add_argument('--status',required=True);p.add_argument('--status-sha256',required=True);a=p.parse_args()
 admission=exact(a.admission,a.admission_sha256);status=exact(a.status,a.status_sha256)
 assert status['returncode']==0 and status.get('streams_closed',status.get('closed_streams'))is True
 assert status.get('direct_child_joined',status.get('direct_joined'))is True and status.get('process_group_absent',status.get('group_absent'))is True
 assert admission['status']=='PASS_FRESH_READ_ONLY_V3_LAUNCHER_ADMISSION_AFTER_FAILED_PRECREATE_OWNER'and admission['mutation']is False and admission['running_containers']==[]
 physical=L.parent/'failed-precreate-physical-retirement-1/INDEPENDENT-FINAL-PHYSICAL-ACCEPTANCE-1.json';physical_ref=ref(physical);assert physical_ref['sha256']=='84c3d0a9a83117d74e9e12c54265b83ca9f1408871ec374ea24780378a3faa39'and admission['sdk_predecessor']==ref(R/'INDEPENDENT-ACTUAL-SDK68-V3-ARTIFACT-AND-PHYSICAL-ACCEPTANCE-1.json')
 request=load(L/'pinned-launcher-request.PAYLOAD-NOT-RELEASED.json');assert isinstance(request['disk_admission'],dict)
 request['disk_admission']=dict(host_free_floor=16<<30,scratch_free_floor=12<<30,host_root='/home/holden/mckernel',scratch_root='/home/holden/mckernel-work/scratch',host_device=admission['host_device'],scratch_device=admission['scratch_device'])
 request['pending_root_execution_authority']['fresh_live_admission']=ref(a.admission)
 payload=D/'pinned-launcher-request.FINAL-PAYLOAD-NOT-RELEASED.json';save(payload,request)
 source=ref(L.parent/'INDEPENDENT-CUMULATIVE-LAUNCHER-SOURCE-REVIEW-1.json');static=ref(L.parent/'INDEPENDENT-FINAL-STATIC-LAUNCHER-BINDING-REVIEW-1.json');owner=ref(B/'launcher_only_container_owner.py');driver=ref(B/'launcher_only_offline.py');plan=ref(B/'launcher-plan.json')
 grant=dict(status='NOT_RELEASED_RESOURCE_GRANT_PAYLOAD',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',billing='included_weekly_only',admission=ref(a.admission),admission_status=ref(a.status),heavy_operations=1,container_cpus='2-5',container_memory=12<<30,memory_swap=12<<30,pids=512,network='none',jobs=1,host_UID_NPROC='inherited',aggregate_memory_required=17411582669,latest_retired_predecessor_event=physical_ref,floor_host=16<<30,floor_scratch=12<<30,campaign_reserve=679477248,host_full_growth_minimum=admission['minimum_host'],scratch_UUID='2a5768c8-718d-4914-bdc0-6b32c5a92a52',reserve_mutation=False)
 save(D/'ROOT-FRESH-RESOURCE-GRANT.PAYLOAD.json',grant)
 authority=dict(decision='NOT_RELEASED_EXACT_ONE_V3_PINNED_LAUNCHER_ONLY_BUILD_PAYLOAD',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',independent_conditional_review=None,resource_grant=None,latest_retired_predecessor=physical_ref,source_acceptance=source,static_binding_acceptance=static,driver_sha256=driver['sha256'],owner_sha256=owner['sha256'],source_sha256='8f9fbe474220433118e6662c9f2517f73a547730575b83ffb73255d06e9b40d7',guest_or_module_execution=False,binding_requirement='ROOT-FINAL-REQUEST-BINDING-1.json exact actualFINALrequest/hash/ownerargv and this genuine authority; one invocation.',on_failure='Preserve owners/evidence; no unchanged replay or invented ACK.')
 save(D/'ROOT-EXACT-EXECUTION-AUTHORITY.PAYLOAD.json',authority)
 ownerargv=['/usr/bin/python3','-I','-B',str(B/'launcher_only_container_owner.py'),str(D/'pinned-launcher-request.FINAL.json')]
 binding=dict(decision='NOT_RELEASED_FINAL_BINDING_PAYLOAD',request=dict(path=str(D/'pinned-launcher-request.FINAL.json'),bytes=None,sha256=None),authority=None,resource_grant=None,admission=ref(a.admission),owner_argv=ownerargv,runtime_owner_nonce=None,container_identity=None,actual_lease=None)
 save(D/'ROOT-FINAL-REQUEST-BINDING.PAYLOAD.json',binding)
 packet=dict(status='ACTUAL_CORRECTED_DRIVER_FRESH_ADMISSION_BOUND_FINAL_REQUEST_REVIEW_PAYLOAD_NO_EXECUTION_AUTHORITY',request_payload=ref(payload),root_binding_payload=ref(D/'ROOT-FINAL-REQUEST-BINDING.PAYLOAD.json'),resource_grant_payload=ref(D/'ROOT-FRESH-RESOURCE-GRANT.PAYLOAD.json'),execution_authority_payload=ref(D/'ROOT-EXACT-EXECUTION-AUTHORITY.PAYLOAD.json'),admission=ref(a.admission),admission_status=ref(a.status),newest_retired_predecessor=physical_ref,source_review=source,static_review=static,owner=owner,driver=driver,plan=plan,production_target_argv=['/usr/bin/cmake','--build','/work/output/build','--target','mcexec','-j1'],owner_argv=ownerargv,root_fields_still_required=['Genuine independent exact conditional execution review','Root genuine resource grant and one-shot execution authority; no future PID/container/nonce/lease invented','Existing empty0700 UID1000 C work/evidence namespace retained; do not recreate. Fresh root heavy/census remains clear'],publication_HEAD_reported_by_root='caf3c246b2f76cbaad831f7fb25c57a4d16983c9',reviewed_source_blob_commit='5fd2c0d2e1e45130009a6d5eb7d88839eb029500',fetched_source_authority=ref(R/'ROOT-FETCHED-ACTUAL-SDK-ACCEPTANCE-CHECKPOINT-1.json'),readonly_admission_review=None,actual_build=False,native_acceptance=False,source_correction=ref(L/'READY-DRIVER-HASH-CORRECTION-1.json'),actual_boundary_control=ref(L/'ACTUAL-DRIVER-BOUNDARY-CONTROL-RESULT.json'),full_static_timeout=ref(L/'ACTUAL-STATIC-VALIDATOR-RESULT.json'),original_static_scope_only=True)
 save(D/'ACTUAL-FINAL-REQUEST-REVIEW-PACKET.json',packet);print(json.dumps(ref(D/'ACTUAL-FINAL-REQUEST-REVIEW-PACKET.json'),sort_keys=True))
if __name__=='__main__':main()
