"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static projection of exact retained, independently accepted failed-native retirement.
No live observers, imports of runtime owners, clocks, grants or workload execution.
"""
import argparse,copy,hashlib,json
from pathlib import Path
INPUTS={'acceptance': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT290-NATIVE1-INDEPENDENT-FAILED-ATTEMPT-POSTJOIN-ACCEPTANCE.json', 'bytes': 1633, 'sha256': '8e4aeaea2241e2cc71aba776bbb69c5761dea318ac64f2c598fd24d9a119db29'}, 'post': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/POSTNATIVE-CURRENT.stdout', 'bytes': 119340, 'sha256': '0935f32a5a893eb616dcd547cb6c32c1387390bb7b6e30d82c325e1d2d694f1c'}, 'command': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/POSTNATIVE-CURRENT-COMMAND.json', 'bytes': 619, 'sha256': '733389bea593162ed6d90f6f5d8418d042290caa9a5db62d6a7b40789464b27c'}, 'owner_export': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/OWNER-RAW-EXPORT.json', 'bytes': 21513, 'sha256': '9ffebe2e8ff173eb03108837cdadf95f5bf97217d7aa41a2d55f166cc2e4b4ae'}, 'caller_join': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/CAPTURE/JOINED.json', 'bytes': 232, 'sha256': 'e2a52c828f5289e08eda035e4203060cd623a8ef9926f4e53cfa428a1badeb76'}, 'owner': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/OWNER-RAW/owner.json', 'bytes': 797, 'sha256': '5088f670f601de78940a96150aef35c71bfe296ead8bb3efe7a097492b74331d'}, 'owner_result': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/OWNER-RAW/result.json', 'bytes': 256, 'sha256': '0ab46fef23ad9582c9ac97e76a423f24dcb1c50b6c8f3d8d5278114f6dabc026'}, 'terminal_inspection': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/OWNER-RAW/021-inspect.stdout', 'bytes': 41208, 'sha256': 'e11a48049e650a69351947ecb854c3dee0510e1568fd61e02289bc3b82ab7622'}, 'terminal_command': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-NATIVE-STARTUP-ADMISSION-1/OWNER-RAW/021-inspect.json', 'bytes': 279, 'sha256': '3da729f35b11afd624681bc99e5f56d1cdc403d4abdff2dcb6e156abb687b4c5'}, 'origin': {'path': '/home/holden/mckernel-work/host-preparation/daemon-sdk7-new18h-source-1/CONSUMER.NEXT18H.PENDING.json', 'bytes': 12496, 'sha256': '6d8ba10f30546fa9aceeca6c76da7f0c9fe050963f0e7d78dfbdc99cc6823c2d'}, 'adapter': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-sdk7-current-authority-composition-source-1/sdk7_authority_adapter.CURRENT-WINDOW.SOURCE-ONLY.py', 'bytes': 22336, 'sha256': 'af1e529c2f618c079a2ce7b71e71a113342f21d6a11db7ee97fbdb2c7738ef99'}, 'window': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-sdk7-current-authority-composition-source-1/WINDOW.EARLIEST-PARENT-BOUND.SOURCE-ONLY.json', 'bytes': 1061, 'sha256': '3911bcd329383467e7a6ce8a36e3bbab9605fdcde80e2b85e0963e5a360dbed2'}}
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok,reason):
 if not ok:raise ValueError(reason)
def render(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def document_ref(path,value):
 raw=render(value);return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def bound(ref):
 raw=Path(ref['path']).read_bytes();need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact-retained-input-changed');return json.loads(raw)
def validate_retirement(v,refs):
 acceptance,post,join,owner,result,terminal,command=v['acceptance'],v['post'],v['caller_join'],v['owner'],v['owner_result'],v['terminal_inspection'],v['terminal_command']
 need(acceptance.get('decision')=='PASS_ACTUAL_FAILED_NATIVE_POSTJOIN_CURRENT_PHYSICAL' and acceptance.get('independent') is True and acceptance.get('reviewer') not in (None,'','/root'),'independent-failed-native-retirement-acceptance')
 need(acceptance['actual']==refs['post'] and acceptance['command']==refs['command'] and acceptance['owner_export']==refs['owner_export'] and acceptance['caller_join']==refs['caller_join'],'acceptance-exact-provenance')
 need(acceptance['native_acceptance'] is False and acceptance['application_acceptance'] is False and post['native_acceptance'] is False,'failed-native-scope-preserved')
 need(result==post['original_failure_preserved'] and result['status']=='FAIL' and result['application_acceptance'] is False and result['absence_verified'] is True and result['lease_retained'] is False,'failed-native-result-and-retirement')
 cid=result['container'];nonce=owner['nonce']
 need(terminal[0]['Id']==post['exact_container_absent']==cid and terminal[0]['Config']['Labels']['mckernel.native-diagnostic.owner']==nonce,'terminal-cid-owner-relation')
 state=terminal[0]['State']
 need(state['Running'] is False and state['Paused'] is False and state['Restarting'] is False and state['Pid']==0 and state['Status']=='exited' and state['ExitCode']==1,'actual-failed-nonrunning-terminal-state')
 need(command['returncode']==0 and command['command']['reaped'] is True and v['command']['returncode']==0,'retained-observers-positive-return-and-reap')
 need(join['joined'] is True and join['returncode']==1 and join['finished_at']<=post['observed_at'],'actual-failed-caller-joined')
 actors=post['known_actor_births_absent'];numeric=set(post['known_numeric_controls_absent'])
 need(actors[str(join['caller_pid'])]==int(join['caller_starttime']) and actors[str(owner['outer']['pid'])]==owner['outer']['proc_starttime'] and set(map(int,actors))<=numeric,'accepted-actor-birth-closure')
 groups={owner['outer']['pgid']}
 need(len(post['commands_actual_reaped'])==25,'exact-native-client-count')
 for item in post['commands_actual_reaped']:
  child=item['command'];need(child['reaped'] is True and actors[str(child['pid'])]==child['proc_starttime'] and child['pid'] in numeric,'all-retained-client-reaps')
  groups.add(child['pgid'])
 census=post['group_membership_observation'];need(census['errors']==[] and not any(row['pgrp'] in groups for row in census['rows']),'accepted-all-original-groups-absent')
 for line in post['closed_exclusive_probes']:
  fields=line.split();need(fields[1:4]==['FLOCK','ADVISORY','WRITE'] and fields[5:] == ['00:1b:4','0','EOF'],'permanent-mutex-probe-identity')
 need(len(post['closed_exclusive_probes'])==2,'two-closed-exclusive-probes')
 docker=post['docker_observations'];need(len(docker)==3,'three-exact-container-absence-observations')
 for row in docker:
  need(row['returncode']==0 and row['stderr']=='' and cid not in row['stdout'].splitlines(),'accepted-native-container-absent')
  if '--filter' in row['argv']:need(row['stdout']=='','native-name-nonce-absent')
 # Scope of the accepted Root source includes closure of capture streams and
 # permanent-holder retirement. This projection adds no independent acceptance.
 need(acceptance['scope_limit'].startswith('Failed native attempt normalretirement and currentavailability at'),'accepted-normal-retirement-scope')
 return cid,nonce,state

def compose(v,refs,out):
 cid,nonce,state=validate_retirement(v,refs);origin=v['origin'];post=v['post'];window=v['window'];out=Path(out)
 need(origin['owner']['sha256']=='94d8d3fd6e2b1181c1ea9a3b53d7d3dbaad00140c4fa8335310e75808456c750' and origin['provider']['sha256']=='89639e9d56c390968a86a95bb734128ec61bd0f6de28f7c7992cfb9e00b9ef96','unchanged-sdk7-owner-and-provider')
 terminal=dict(container=cid,state=copy.deepcopy(state),source_only_projection=True,inspection=refs['terminal_inspection'],inspection_command=refs['terminal_command'],original_native_failure=refs['owner_result'],independent_retirement_acceptance=refs['acceptance'],native_acceptance=False,application_acceptance=False)
 terminal_ref=document_ref(out/'LATEST-NATIVE1-TERMINAL.PROJECTION.json',terminal)
 closure=dict(schema='mckernel.owned-operation-closure.v1',status='PASS_OWNED_OPERATION_CLOSED',scope=SCOPE,source_only_projection=True,projection_adds_no_independent_acceptance=True,nonce=nonce,boot_id=window['boot_id'],closed_wall=post['observed_at'],terminal=terminal_ref,container=cid,direct_child_joined=True,group_absent=True,closed_streams=True,holder_retired=True,container_dispositions=[dict(cid=cid,disposition='absent',independently_accepted=True,acceptance=refs['acceptance'])],original_workload_status='FAIL',native_acceptance=False,application_acceptance=False,independent_retirement_acceptance=refs['acceptance'],actual_postjoin=refs['post'],caller_join=refs['caller_join'],owner_export=refs['owner_export'],no_fresh_workload_admission=True)
 closure_ref=document_ref(out/'LATEST-NATIVE1-CLOSURE.PROJECTION.json',closure)
 head=dict(schema='mckernel.serial-operation-head.v1',status='STATIC_LATEST_KNOWN_OPERATION_BINDING_ROOT_FINALIZATION_REQUIRED',latest_operation=closure_ref,consumed_nonces=None,no_intervening_operation=None,known_consumed_nonce_from_bound_evidence=nonce,latest_acceptance=refs['acceptance'])
 head_ref=document_ref(out/'OPERATION-HEAD.TEMPLATE.NOT-RELEASED.json',head)
 live=dict(schema='mckernel.daemon7.live-environment-observation.v1',status='TEMPLATE_NOT_A_FRESH_OBSERVATION',latest_operation=closure_ref,operation_head=head_ref,clock=None,global_mutex_rows=None,active_records_absent=None,no_unknown_owned_operations=None,root_mutex=None,container_dispositions=None,accepted_previous_observation=refs['post'],accepted_previous_observed_wall=post['observed_at'])
 live_ref=document_ref(out/'LIVE-OBSERVATION.TEMPLATE.NOT-RELEASED.json',live)
 request=copy.deepcopy(v['original_request'])
 for key in ('nonce','request_path','candidate_root','candidate_identity','owner_evidence_root','output_parent_identity','input_identity','basis_identity','backing_identity'):request[key]=None
 request['boot_id']=window['boot_id']
 request_ref=document_ref(out/'SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json',request)
 bundle=dict(schema='mckernel.daemon7.live-admission.v1',status='STATIC_BOUND_LATEST_RETIRED_NATIVE1_NOT_EXECUTABLE',parent_window=refs['window'],query_window=refs['window'],request=request_ref,operation_head=head_ref,latest_operation=closure_ref,live_observation=live_ref,query=None,query_join=None,reservation=None,root_admission_review=None)
 query=dict(status='STATIC_QUERY_BINDING_NOT_A_QUERY_RELEASE',bundle=None,adapter=refs['adapter'],parent_window=refs['window'],request=request_ref,operation_head=head_ref,latest_operation=closure_ref,live_observation=live_ref,profile=origin['profile'],capture_helper=origin['capture_helper'],actual_nonce=None,aggregate_memory_GiB=None,owned_holder=None,evidence_root=None,independent_query_release=None)
 fill=dict(status='STATIC_FILL_BINDING_NOT_AN_EXECUTION_PAYLOAD',bundle=None,adapter=refs['adapter'],historical_origin=refs['origin'],historical_source_approval=origin['source_approval'],historical_sdk21_artifact=origin['SDK21_artifact_behavior'],latest_operation=closure_ref,actual_query=None,actual_query_join=None,reservation=None,root_admission_review=None,execution_review=None,runtime_authority=None)
 owner_argv=['/home/holden/anaconda3/bin/python3','-I','-B',origin['owner']['path'],'--request','<ACTUAL_NEW_REQUEST_ABSOLUTE_PATH>','--request-sha256','<ACTUAL_NEW_REQUEST_SHA256>','--release','<ACTUAL_REVIEWED_SDK7_RELEASE_ABSOLUTE_PATH>','--release-sha256','<ACTUAL_REVIEWED_SDK7_RELEASE_SHA256>']
 command=dict(scope=SCOPE,status='EXACT_EXISTING_OWNER_ARGUMENT_SHAPE_NOT_RELEASED',required_uid=1000,owner=origin['owner'],argv=owner_argv,source_only=True,commands=origin['seven_commands'],provider=origin['provider'],profile=origin['profile'],blocked_root_finalization=['fresh nonce and exactly owner-compatible fresh request/candidate/evidence identities','Root current operation head with complete consumed-nonce ledger and no intervening serialized operation','fresh live observation with allthree actual clocks and current absent ownership/mutex/container disposition','source-reviewed hash-exact query release and actual owned27:4 holder+complete h990 capture','actual identity/resource/image-only query plus wholejoin, current aggregate environment and sole-heavy reservation','independent exact root admission metadata review, source publication, execution-payload review and execution release'],actual_live_query_calls=0,actual_sdk_commands=0,native_acceptance=False)
 return {'LATEST-NATIVE1-TERMINAL.PROJECTION.json':terminal,'LATEST-NATIVE1-CLOSURE.PROJECTION.json':closure,'OPERATION-HEAD.TEMPLATE.NOT-RELEASED.json':head,'LIVE-OBSERVATION.TEMPLATE.NOT-RELEASED.json':live,'SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json':request,'SDK7-BUNDLE.STATIC.NOT-RELEASED.json':bundle,'SDK7-QUERY.STATIC.NOT-RELEASED.json':query,'SDK7-FILL.STATIC.NOT-RELEASED.json':fill,'NEXT-UNPRIVILEGED-SDK7-OWNER.COMMAND.NOT-RELEASED.json':command}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--emit-dir',type=Path,required=True);args=parser.parse_args()
 v={name:bound(ref) for name,ref in INPUTS.items() if name!='adapter'}
 v['original_request']=bound(v['origin']['request']);refs=dict(INPUTS)
 args.emit_dir.mkdir(mode=0o700,exist_ok=False)
 outputs=compose(v,refs,args.emit_dir.resolve())
 for name,value in outputs.items():
  with (args.emit_dir/name).open('xb') as stream:stream.write(render(value))
 print(json.dumps(dict(status='PASS_STATIC_NATIVE1_RETIREMENT_TO_SDK7_BINDING_NO_EXECUTION',outputs=len(outputs),directory=str(args.emit_dir))))
if __name__=='__main__':main()
