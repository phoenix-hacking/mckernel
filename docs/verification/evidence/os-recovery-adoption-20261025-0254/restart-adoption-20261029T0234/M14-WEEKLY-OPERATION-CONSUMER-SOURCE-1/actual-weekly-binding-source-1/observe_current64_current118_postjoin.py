"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow Root64/65 post-CURRENT118 adapter. Imports/pure validators never observe.
The rejected118 artifact stays rejected; all native acceptance remains historical.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, os, re, resource, time, uuid
HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'INPUTS.json').read_bytes())
NONCE=PINS['nonce'];CID=PINS['CID'];NAME=PINS['NAME']
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
STATUS='PASS_Root64_CURRENT118_POSTJOIN_OBSERVATION_PENDING_INDEPENDENT_ACCEPTANCE'
CURRENT_STATUS='PASS_Root65_CURRENT118_CURRENT_REOBSERVATION_PENDING_ROOT_ACCEPTANCE'
PREFIX=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
PROFILE=dict(uid=1000,cpus=[0],jobs=1,address_space_bytes=2<<30,maximum_CPU_seconds=60,maximum_wall_seconds=120)
def need(ok,why):
 if not ok:raise ValueError(why)
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 need(type(row)is dict and set(row)=={'path','bytes','sha256'} and Path(row['path']).is_absolute() and ref(row['path'])==row,'exact BYTE reference');return Path(row['path'])
def checked(row):return json.loads(auth(row).read_bytes())
def load(row,name):
 spec=importlib.util.spec_from_file_location(name,auth(row));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def actor(row,role=None):
 birth=row.get('birth',row.get('start'));return dict(pid=row['pid'],start=None if birth is None else int(birth),role=role or row['role'],group=row.get('group'),fd=row.get('fd'))

def validate_retained():
 """Retain original history multiset; append only authenticated measured actors."""
 base=load(PINS['base_source'],'CURRENT118_historical_Root63');retained=base.validate_retained()
 current=checked(PINS['base_bindings']);capture=base.validate_current_adoption(current,retained)
 prior=checked(PINS['base_ledger']);need(current['ledger']==PINS['base_ledger'] and len(prior['consumed_nonces'])==71,'genuine Root63 71-nonce base')
 rows=[actor(r) for r in capture['all_recorded_actors_absent']]
 rows.append(actor(capture['observer_self'],'accepted_Root62_capture'))
 receipts=base.validate_capture_commands(capture)
 rows.extend(actor(dict(pid=r['pid'],birth=r['birth'],group=r['pid']),'accepted_Root62_query_client')for r in receipts)
 need(len(rows)==93,'exact accepted Root63 historical actor multiset')
 frontier_core=load(PINS['frontier_core'],'CURRENT118_exact_A2_frontier')
 frontier=frontier_core.validate_closed_unlaunched_frontier(PINS['A2frontier'],current)
 rows.extend(actor(r)for r in frontier['actors'])
 actual=checked(PINS['producer_actors']);producer=checked(PINS['producer_inputs'])
 need(actual['known_pre_retirement_frontier_rows']==109 and len(actual['actual_A3_actor_rows'])==10,'exact measured A3 frontier')
 rows.extend(actor(r)for r in actual['actual_A3_actor_rows'])
 executor=load(PINS['retirement_source'],'CURRENT118_normal_retirement_pure_API');b=executor.bindings()
 need([(r['pid'],r['start'])for r in rows]==[(r['pid'],r['start'])for r in (b['prior_actors']+b['new_known_actors'])[:109]],'all109 actor rows match independently bound normal-retirement frontier')
 refs=producer['refs'];profile=checked(refs['profile']);worker=checked(refs['worker_result'])
 need(len(worker['commands'])==4 and len(profile['exact_commands'])==4,'actual four-command producer')
 for i,(record,command)in enumerate(zip(worker['commands'],profile['exact_commands'])):
  need(record['index']==i and record['argv']==command['argv'] and record['cwd']==command['cwd'] and record['returncode']==0,'exact actual four argv/cwd/return records')
 rejection=checked(PINS['artifact_rejection']);auth(PINS['registry_failure'])
 need(rejection['decision']=='FAIL_INDEPENDENT_ACTUAL_CURRENT118_ORIGINAL389_METADATA_MULTISET_ARTIFACT_NOT_ACCEPTED','original389 rejected; never current artifact acceptance')
 clients=base.validate_recorded_clients([r['receipt']for r in actual['actual_A3_actor_rows']if 'receipt'in r])
 need([(r['pid'],r['birth'])for r in clients]==[(r['pid'],r['birth'])for r in actual['actual_A3_actor_rows']if 'receipt'in r],'five actual measured physical clients')
 facts=dict(base=base,retained=retained,prior=prior,base_capture=capture,frontier=frontier,frontier_core=frontier_core,actors=rows,producer=producer,executor=executor,b=b,unknown_births=actual['unknown_births_not_filled']);failed=validate_failed_custody(facts)
 need([(r['pid'],r['start'])for r in failed[:3]]==[(r['pid'],r['start'])for r in (b['prior_actors']+b['new_known_actors'])[109:]],'exact compatibility three failed actor additions')
 rows.extend(failed);return facts

def validate_failed_custody(retained):
 """Actual failed records are history, not positive cleanup/client status."""
 failed=checked(PINS['failed_normal']);join=checked(PINS['failed_recovery_join']);started=checked(PINS['failed_recovery_started'])
 need(failed['status']=='RETAINED_FAILURE_NOT_CUSTODY_CLEARANCE' and failed['positive_wait4_recorded']is False and failed['returncode_claimed']is False and failed['commit_attempted']is False and failed['ownership_reconciliation_required']is True,'failed normal attempt retains UNKNOWN client status and custody')
 need(failed['owner']==dict(pid=2232651,birth=103343097,permanent_mutex=[27,4]) and failed['parent']==dict(pid=2232650,birth=103343093,tool_session=90401) and failed['first_client']==dict(pid=2232653,birth=103343210),'three exact recorded failed-normal actors')
 for key in ['executor','bindings','uncertain','quarantine','command_receipt']:auth(failed[key])
 for row in failed['raw'].values():auth(row)
 need(join['author']=='/root' and join['pid']==started['pid']==2247306 and int(join['birth'])==int(started['birth'])==103642908 and join['parent_pid']==started['parent_pid']==2247305 and int(join['parent_birth'])==int(started['parent_birth'])==103642905 and join['returncode']==1 and join['positive_direct_parent_wait']is True and join['parent_streams_closed']is True,'actual failed recovery rc1 and measured outer parent; no clearance')
 need(join['release_sha256']==PINS['failed_recovery_release']['sha256'] and auth(join['stdout']).read_bytes()==b'','same failed recovery release/empty stdout')
 auth(join['stderr']);auth(PINS['failed_recovery_release'])
 compat=checked(PINS['compatibility_runtime_files']);need(len(compat)==12 and compat['executor']==PINS['retirement_source'] and compat['bindings']==PINS['retirement_bindings'],'exact12 compatibility runtime refs')
 for row in compat.values():auth(row)
 return [dict(pid=2232651,start=103343097,role='CURRENT118_failed_retirement_quarantine_owner',group=None,fd=4),dict(pid=2232650,start=103343093,role='CURRENT118_failed_retirement_parent',group=None,fd=None),dict(pid=2232653,start=103343210,role='CURRENT118_failed_retirement_readonly_client_UNKNOWN',group=None,fd=None),dict(pid=2247306,start=103642908,role='CURRENT118_failed_recovery_operator',group=None,fd=None),dict(pid=2247305,start=103642905,role='CURRENT118_failed_recovery_operator_parent',group=None,fd=None)]

def attach_custody(bindings,retained):
 """One narrow Root supplement; future operator/result/joins stay required inputs."""
 import ast,signal
 row=bindings['custody_supplement'];value=checked(row)
 if retained.get('custody_supplement')is not None:
  need(retained['custody_supplement']==row,'one immutable post-Root64 custody supplement');return value
 need(value['schema']=='mckernel.current118.post-root64-custody.v1' and value['author']=='/root' and value['decision']=='BIND_COMPLETE_RECORDED_POST_ROOT64_CUSTODY' and value['runtime_authority']is None,'Root-only actual custody supplement')
 need(value['base_pending_ledger']==PINS['pending_ledger'] and value['failed_normal_attempt']==PINS['failed_normal'] and value['failed_recovery_join']==PINS['failed_recovery_join'],'exact genuine failed custody history')
 need(value['all_post_base_custody_listed']is True and value['root_attests_no_unlisted_post_base_operation']is True and value['old_readonly_client_status']=='UNKNOWN' and value['current_free']is False,'truthful complete frontier; unknown status and pending clearance preserved')
 need(value['recovery_source']==PINS['recovery_parent_validator'],'exact frozen corrected recovery source; no old failed release alias')
 for key in ['recovery_source','recovery_source_review','recovery_result','target_parent_join','operator_parent_join','independent_recovery_acceptance']:auth(value[key])
 source_review=checked(value['recovery_source_review']);acceptance=checked(value['independent_recovery_acceptance'])
 need(source_review['independent']is True and source_review['implementation_ownership']is False and source_review['files']['executor']==value['recovery_source'] and source_review['decision'].startswith('PASS'),'independent exact existing recovery source')
 # Reuse only the genuine existing pure target-parent predicate. Module top-level
 # config, guards, proc reads and execution are never imported for this check.
 tree=ast.parse(auth(PINS['recovery_parent_validator']).read_bytes());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_parent_join')
 namespace=dict(need=need,signal=signal,G=dict(pid=2232651,starttime='103343097',parent_pid=2232650,parent_birth='103343093'))
 exec(compile(ast.Module(body=[fn],type_ignores=[]),PINS['recovery_parent_validator']['path'],'exec'),namespace)
 namespace['validate_parent_join'](checked(value['target_parent_join']))
 result=checked(value['recovery_result']);parent=checked(value['operator_parent_join'])
 need(result['schema']=='mckernel.current118.failed-idle-helper.retirement-complete.v1' and result['status']=='COMPLETE_FAILED_HELPER_RETIREMENT_PENDING_PARENT_JOIN' and result['parent_positive_join_required']is True and result['current_free']is False and result['old_readonly_client_status']=='UNKNOWN' and result['cleanup_required']is True and result['acceptance_credit']is False,'actual existing owner retirement result remains pending ordinary cleanup/current')
 need(result['target']['pid']==2232651 and str(result['target']['starttime'])=='103343097' and result['target']['parent']==2232650 and result['target']['lock_fd']==4 and result['replacement_root_lock']==[27,4],'exact original failed helper/FD4 only')
 need(parent['author']=='/root' and type(parent['pid'])is int and type(parent['birth'])is int and type(parent['parent_pid'])is int and type(parent['parent_birth'])is int and parent['returncode']==0 and parent['positive_direct_parent_wait']is True and parent['parent_streams_closed']is True and all(parent[k]>0 for k in ['pid','birth','parent_pid','parent_birth']),'new actual recovery operator and measured parent positive join required')
 reply=json.loads(auth(parent['stdout']).read_bytes());need(auth(parent['stderr']).read_bytes()==b'' and reply['status']==result['status'] and reply['receipt']==value['recovery_result']['path'] and reply['receipt_sha256']==value['recovery_result']['sha256'] and reply['cleanup_required']is True,'actual operator stdout binds exact recovery result')
 need(acceptance['independent']is True and acceptance['implementation_ownership']is False and acceptance['decision']=='PASS_EXACT_CURRENT118_FAILED_HELPER_RETIREMENT' and acceptance['current_free']is False and acceptance['old_readonly_client_status']=='UNKNOWN','existing independent actual owner-retirement acceptance, no current-free')
 for key in ['recovery_source','recovery_result','target_parent_join','operator_parent_join']:need(acceptance[key]==value[key],'exact independent recovery acceptance '+key)
 clients=retained['base'].validate_recorded_clients(result['after']['command_receipts']);need(len(clients)==12 and len({r['pid']for r in clients})==12,'three original four-command recovery snapshots; all measured clients retained')
 rows=[dict(pid=parent['pid'],start=parent['birth'],role='CURRENT118_actual_recovery_operator',group=None,fd=None),dict(pid=parent['parent_pid'],start=parent['parent_birth'],role='CURRENT118_actual_recovery_operator_parent',group=None,fd=None)]
 rows.extend(dict(pid=r['pid'],start=r['birth'],role='CURRENT118_actual_recovery_recorded_command',group=r['pid'],fd=None)for r in clients)
 need(value['additional_measured_actors']==rows,'exact actual recovery operator/parent/twelve clients; no invented or omitted births')
 need(type(value['recorded_epoch'])in(int,float) and math.isfinite(value['recorded_epoch']) and all(type(parent[k])in(int,float) and math.isfinite(parent[k])for k in ['start_epoch','finish_epoch']) and checked(PINS['failed_recovery_join'])['finish_epoch']<=parent['start_epoch']<=parent['finish_epoch']<=value['recorded_epoch']<PINS['limits'][0],'post-failure current supplement within original caps')
 retained['actors'].extend(rows);retained['actors'].extend(root3_failed_actors(checked(PINS['post_root3_pending'])));retained['actors'].extend(root4_outer_parent_actors());retained['custody_supplement']=row
 return value


def root3_failed_actors(ledger):
 """Exact already-joined Root3 failure; no positive cleanup/current-free inference."""
 note=json.loads(ledger['note']);closed=note['closed_failed_current118_cleanup']
 need(closed['native_clearance']is False and closed['permanent_mutex_held']is False,'Root3 closed failure is not clearance')
 for key in ['failure','parent_join','client_join','release']:auth(closed[key])
 failed=checked(closed['failure']);joined=checked(closed['parent_join']);client=checked(closed['client_join']);release=checked(closed['release'])
 need(failed['status']=='FAILED_FIRST_READ_ONLY_PROC_CENSUS_BEFORE_DOCKER' and failed['current_free']is False and failed['docker_commands']==0 and failed['mutation']is False and failed['rm_claimed']is False and failed['signals_sent']==0 and failed['quarantine']is False and failed['original_client2232653_exit']=='UNKNOWN','Root3 original failure/UNKNOWN preserved')
 parent=joined['parent'];child=joined['child']
 need((parent['pid'],parent['birth'],child['pid'],child['birth'],child['ppid'])==(2304474,104745866,2304475,104745869,2304474),'exact Root3 measured parent/executor identity')
 need(joined['release']==closed['release'] and joined['returncode']==1 and joined['positive_direct_parent_wait']is True and joined['positive_wait4_join']is True and joined['wait4_pid']==child['pid'] and joined['wait4_status']==256 and joined['streams_closed']is True and joined['signals_sent']==0 and joined['native_clearance']is False,'Root3 exact positive direct wait4 failure join')
 need(auth(joined['stdout']).read_bytes()==b'' and auth(joined['stderr']).read_bytes()!=b'','Root3 failed parent raw streams')
 need(release['nonce']==NONCE and release['cid']==CID and release['author']=='/root' and release['current_ledger']==note['prior_metadata_boundary'],'Root3 release bound to prior97ce frontier')
 need((failed['executor_pid'],failed['executor_birth'],failed['executor_returncode'])==(child['pid'],child['birth'],1),'failure/executor join identity agrees')
 need((client['pid'],client['birth'],client['wait4_pid'])==(2304484,104745982,2304484) and client['positive_wait4']is True and client['wait4_status']==256 and client['returncode']==1 and client['group_absent']is True and client['group_members']==[] and client['streams_closed']is True and client['client_retirement_unproven']is False and client['signals_sent']==0,'Root3 first readonly client actual positive wait/group/stream closure')
 need((failed['client_pid'],failed['client_birth'],failed['client_returncode'])==(client['pid'],client['birth'],client['returncode']) and failed['client_group_absent']is True and failed['positive_direct_wait4']is True and failed['streams_closed']is True,'failure/client join identity agrees')
 need(set(client['raw'])=={'stdout','stderr','status.json'},'complete Root3 client raw receipt')
 for row in client['raw'].values():auth(row)
 status=checked(client['raw']['status.json']);need(status['state']=='exited' and status['pid']==client['pid'] and status['exit_code']==1 and status['argv']==client['argv'],'Root3 exact raw client exit/argv')
 need(auth(client['raw']['stdout']).read_bytes()==b'' and b'FileNotFoundError'in auth(client['raw']['stderr']).read_bytes(),'Root3 first-census original ENOENT raw failure')
 need(client['argv'][:6]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c'] and client['argv'][-2:]==[str(child['pid']),str(child['birth'])],'Root3 readonly census exact caller')
 need(parent['pgrp']==parent['sid']==parent['pid'] and child['pgrp']==child['sid']==child['pid'] and client['process_group']==client['pid'],'only measured dedicated groups recorded')
 return [dict(pid=parent['pid'],start=parent['birth'],role='CURRENT118_Root3_failed_cleanup_parent',group=parent['pgrp'],fd=None),dict(pid=child['pid'],start=child['birth'],role='CURRENT118_Root3_failed_cleanup_executor',group=child['pgrp'],fd=None),dict(pid=client['pid'],start=client['birth'],role='CURRENT118_Root3_failed_readonly_client',group=client['process_group'],fd=None)]


def validate_pending_ledger(value,retained):
 """Actual Root64 is the exact initial72 boundary, not a71-reader alias."""
 expected=checked(PINS['pending_ledger']);prior=retained['prior']
 need(retained.get('custody_supplement')is not None,'mandatory actual recovery/custody supplement before current frontier')
 allowed={'recorded_epoch','declared_boundary','note','prior_pending_ledger'}
 need(set(value)==set(expected)|{'post_Root64_retirement_custody'},'narrow supplemented72 ledger schema')
 for key,wanted in expected.items():
  if key not in allowed:need(value[key]==wanted,'unchanged exact Root64 history '+key)
 need(value['prior_pending_ledger']==PINS['pending_ledger'] and value['post_Root64_retirement_custody']==retained['custody_supplement'] and checked(retained['custody_supplement'])['recorded_epoch']<=value['recorded_epoch']<PINS['limits'][0],'actual complete supplemented pending frontier; no old683 live alias')
 need(value['author']=='/root' and value['complete_within_declared_current_boundary']is True and value['root_attests_no_unlisted_post_boundary_execution_or_custody_operation']is True,'Root-only complete declared frontier')
 need(value['prior_ledger_retained']==PINS['base_ledger'] and value['consumed_nonces']==prior['consumed_nonces']+[NONCE] and len(value['consumed_nonces'])==len(set(value['consumed_nonces']))==72,'exact prior71 plus consumed A3 e984 once')
 abandoned=retained['frontier']['abandoned_nonces']
 need(not set(abandoned)&set(value['consumed_nonces']) and value['reserved_abandoned_unconsumed_nonces']==prior['reserved_abandoned_unconsumed_nonces']+abandoned,'A2 abandoned1d3 independently forbidden')
 need(value['post_Root63_closed_unlaunched_frontier']==PINS['A2frontier'] and value['current_physical_clearance_pending']is True and value['latest_accepted_free_boundary']==prior['latest_accepted_free_boundary'],'Root63/freee13 historical; new clearance pending')
 build=value['current118_build'];art=build['artifact_acceptance']
 need(build['nonce']==NONCE and build['container_id']==CID and build['container_name']==NAME and build['normal_retirement_pending']is True and build['current_physical_clearance_pending']is True,'exact ordinary build remains pending')
 need(art==dict(status='REJECTED_ORIGINAL_389_METADATA_MULTISET',independent_review=PINS['artifact_rejection'],first_actual_failure=PINS['registry_failure'],accepted_default_remains='CURRENT116 C71/Rust68'),'artifact rejection and accepted116 scope immutable')
 return True

def root4_outer_parent_actors():
 """Only the measured closed outer parent; no inherited group is claimed."""
 ledger=checked(PINS['post_root4_pending']);note=json.loads(ledger['note']);old=checked(PINS['post_root3_pending'])
 need(note['prior_metadata_boundary']==PINS['post_root3_pending'] and note['closed_failed_current118_cleanup']==json.loads(old['note'])['closed_failed_current118_cleanup'],'Root4 metadata retains exact Root3 closed custody')
 closed=note['closed_current118_root4_retirement'];joined=checked(PINS['root4_parent_normalized']);raw=checked(PINS['root4_parent_raw'])
 need(closed['parent_join']==PINS['root4_parent_raw']==joined['raw_parent_capture'] and closed['current_free']is False and closed['records_released']==[],'exact pending Root4 raw-parent metadata, no clearance')
 auth(closed['result']);auth(closed['release'])
 need(raw['release']==closed['release'] and raw['native_clearance']is False and raw['signals_sent']==joined['signals_sent']==0,'Root4 actual release and no signals/native claim')
 child=raw['child'];parent=raw['parent']
 need((parent['pid'],parent['birth'],child['pid'],child['birth'],child['ppid'])==(2311392,104859779,2311393,104859782,2311392),'exact measured Root4 outer parent/child')
 need(joined['author']=='/root' and joined['pid']==child['pid'] and joined['birth']==child['birth'] and joined['parent_pid']==parent['pid'] and joined['parent_birth']==parent['birth'],'normalized Root4 identity projects raw capture')
 for key in ['returncode','wait4_pid','wait4_status','positive_direct_parent_wait','positive_wait4_join','stdout','stderr']:
  need(joined[key]==raw[key],'normalized Root4 raw projection '+key)
 need(joined['returncode']==0 and joined['wait4_pid']==child['pid'] and joined['wait4_status']==0 and joined['positive_direct_parent_wait']is True and joined['positive_wait4_join']is True and joined['parent_streams_closed']is raw['streams_closed']is True,'Root4 positive direct wait and closed streams')
 need(auth(joined['stderr']).read_bytes()==b'' and json.loads(auth(joined['stdout']).read_bytes())==dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=closed['result']),'Root4 raw streams bind exact result')
 return [dict(pid=parent['pid'],start=parent['birth'],role='CURRENT118_Root4_closed_cleanup_outer_parent',group=None,fd=None)]

def validate_retirement(retained,result_ref,parent_ref):
 executor=retained['executor'];b=retained['b'];value=checked(result_ref)
 receipts=executor.validate_result(value,b)
 joined=checked(parent_ref);cleanup=value['cleanup_actor']
 need(joined['pid']==cleanup['pid'] and int(joined['birth'])==int(cleanup['birth']) and joined['returncode']==0 and joined['positive_direct_parent_wait']is True and joined['parent_streams_closed']is True,'actual retirement direct-parent ABI; inherited parent group is unclaimed')
 need(auth(joined['stderr']).read_bytes()==b'' and json.loads(auth(joined['stdout']).read_bytes())==dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=result_ref),'actual parent streams name exact validated result')
 need(value['final_safety']['mutex']['device']==27 and value['final_safety']['mutex']['inode']==4 and cleanup['mutex_fd']==value['final_safety']['mutex']['fd'] and value['own_fd_closed_only_after_result_on_normal_return']is True,'permanent27:4 own FD; fresh postjoin FD absence still required')
 need(value['original_Docker_actor_gaps']==b['actor_gaps'],'preserve original unknown actor births')
 rows=[actor(dict(cleanup,group=None,fd=cleanup['mutex_fd']),'CURRENT118_cleanup_executor')]
 rows.extend(actor(dict(pid=r['pid'],birth=r['birth'],group=r['pid']),'CURRENT118_cleanup_recorded_command')for r in receipts)
 need(len(rows)==15,'exact cleanup plus14 recorded raw positive-joined clients')
 return value,receipts,rows

def capture_scope():
 base=load(PINS['base_source'],'CURRENT118_source_scope')
 return dict(schema='mckernel.root64.complete-recursive-readonly-capture-scope.v1',inherited_Root63_bindings=PINS['base_bindings'],inherited_readonly_operation='bfd-postjoin-current62',inherited_scope=base.capture_scope(),explicit_weekly_recursive_entry=PINS['runtime_base_source'],explicit_weekly_recursive_scope=load(PINS['runtime_base_source'],'weekly_recursive_capture_scope').capture_scope(),new_operation=PINS['operation'],new_tracked_commands=3,new_tracked_command_order=['exact CURRENT118 CID absence','exact CURRENT118 name absence','complete normal process/group census'],total_tracked_raw_clients=8,original_full_proc_group_FD_lock_mount_cgroup_resource_Docker_checks=True,two_original_closed_probes=True,automatic_retries=0,cleanup_or_signals=False,unmeasured_inherited_client_births_preserved=True,failed_normal_client_status='UNKNOWN',failed_normal_and_recovery_history_required=True,actual_recovery_operator_parent_and_all_recorded_clients_required=True)

def source_subjects():
 result=dict(observer=ref(__file__),inputs=ref(HERE/'INPUTS.json'))
 runtime=load(PINS['runtime_base_source'],'weekly_recursive_source_closure');result['runtime_base_source']=PINS['runtime_base_source'];auth(PINS['runtime_base_source']);result.update({'weekly_recursive:'+key:value for key,value in runtime.source_subjects().items()})
 for key in ['base_source','base_bindings','base_ledger','frontier_core','A2frontier','producer_inputs','producer_actors','retirement_source','retirement_bindings','guard','shared_guard','guardian','pending_ledger','artifact_rejection','registry_failure']:result[key]=PINS[key];auth(PINS[key])
 inherited=load(PINS['base_source'],'CURRENT118_source_closure').source_subjects()
 result.update({'inherited:'+key:value for key,value in inherited.items()})
 for key,row in checked(PINS['compatibility_runtime_files']).items():auth(row);result['compat:'+key]=row
 for key in ['failed_normal','failed_recovery_join','failed_recovery_started','failed_recovery_release','recovery_parent_validator','recovery_bindings','recovery_source_ready','source1_ready','source1_observer','post_root3_pending','post_root4_pending','root4_parent_normalized','root4_parent_raw']:result[key]=PINS[key];auth(PINS[key])
 return result

def runtime_dependencies(bindings):
 need(bindings['author']=='/root' and bindings['decision']=='BIND_EXACT_ROOT64_CURRENT118_POSTJOIN_OBSERVER' and bindings['runtime_authority']is None,'Root-only new explicit observer binding')
 need(bindings['phase']in ('postjoin_candidate','accepted_current') and bindings['guard_adapter']==PINS['guard'],'exact new64 adapter and typed phase')
 keys=['ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration','custody_supplement','recursive_current63_bindings']
 if bindings['phase']=='accepted_current':keys+=['pending_ledger','latest_free','current_boundary']
 for key in keys:auth(bindings[key])
 review=checked(bindings['independent_review'])
 need(review['decision']=='PASS_EXACT_ROOT64_CURRENT118_POSTJOIN_OBSERVER_DEPENDENCIES' and review['independent']is True and review['implementation_ownership']is False and review['observer']==ref(__file__) and review['phase']==bindings['phase'] and review['capture_scope']==capture_scope(),'independent complete recursive runtime dependency review')
 for key in keys:need(review[key]==bindings[key],'exact reviewed runtime dependency '+key)
 config=checked(bindings['guard_configuration'])
 subjects=source_subjects();subjects.update({key:bindings[key]for key in keys if key not in ('guard_adapter','guard_configuration')})
 need(config['subjects']==subjects and review['source_subjects']==source_subjects(),'exact new source and runtime subjects in operation closure')
 need(config['operation']==PINS['operation'] and config['shared_guard']==PINS['shared_guard'],'explicit readonly operation; no producer alias')
 operation=checked(config['successor']);need(operation['guardian']==dict(source=PINS['guardian'],entrypoint='guard'),'exact4889 restart guardian')
 guard=load(PINS['guard'],'CURRENT118_explicit_current64_adapter');need(guard.OPERATION==PINS['operation'],'explicit current64 API');guard.configure(bindings['guard_configuration']);return guard

def validate_absence_reports(reports,actors):
 pids={r['pid']for r in actors};groups={r['group']for r in actors if r.get('group')is not None}
 need(reports,'complete fresh reports required')
 for report in reports:
  need(len(report['snapshots'])==len(report['groups'])==2,'two complete proc/group snapshots')
  for snapshot,group in zip(report['snapshots'],report['groups']):
   need([r[:3]for r in group]==snapshot,'full same process/group rows')
   need(not any(r[0]in pids for r in snapshot) and not any(r[0]in pids or r[3]in groups or r[4]in groups for r in group),'every recorded PID and measured dedicated group/session absent')
 return True

def validate_new_commands(capture,retained,retirement_receipts,actors):
 base=retained['base'];original=base.validate_capture_commands(capture['historical_Root63_reobservation'])
 rows=base.validate_recorded_clients(capture['current118_query_command_receipts'])
 need(len(rows)==3 and len(capture['current118_complete_process_reports'])==1,'exact two CID/name plus one complete census')
 expected=[PREFIX+['ps','-aq','--no-trunc','--filter','id='+CID],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+NAME+'$']]
 for row,argv in zip(rows[:2],expected):need(row['argv']==argv and auth(row['raw']['stdout']).read_bytes()==auth(row['raw']['stderr']).read_bytes()==b'','exact new CID/name absence raw replies')
 executor=retained['executor'];b=retained['b'];normal=load(b['normal'],'CURRENT118_pure_raw_census');prior_pids=[r['pid']for r in retirement_receipts+original+rows[:2]]+[r['pid']for r in actors];code=executor.process_source(normal,checked(b['packet']),b,prior_pids)
 row=rows[2];argv=row['argv'];caller=capture['observer_self']
 need(len(argv)==10 and argv[:7]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code] and re.fullmatch('[0-9a-f]{32}',argv[7]) and argv[8:]==[str(caller['pid']),str(caller['birth'])],'exact full census code/challenge/real caller')
 report=json.loads(auth(row['raw']['stdout']).read_bytes());need(report==capture['current118_complete_process_reports'][0],'same raw complete report')
 executor.validate_process(report,normal,b,argv[7],[caller['pid'],str(caller['birth'])],prior_pids)
 validate_absence_reports(capture['historical_Root63_reobservation']['complete_process_reports']+[report],actors)
 clients=original+rows
 need(capture['query_clients']==[dict(pid=r['pid'],birth=r['birth'])for r in clients],'all eight real client identities; no invented birth')
 return clients

def validate_capture(capture,bindings,retained):
 attach_custody(bindings,retained)
 pending_ref=bindings.get('pending_ledger',bindings['ledger']);validate_pending_ledger(checked(pending_ref),retained)
 retirement,receipts,retired=validate_retirement(retained,bindings['retirement_result'],bindings['retirement_parent_join'])
 actors=retained['actors']+retired
 need(capture['status']==STATUS and capture['Root64']==pending_ref and capture['current_boundary']==pending_ref and capture['ordinary_CURRENT118_build_nonce']==NONCE and capture['retired_CURRENT118_CID']==CID,'exact Root64 raw observation')
 need(capture['retirement_result']==bindings['retirement_result'] and capture['retirement_parent_join']==bindings['retirement_parent_join'],'exact retirement/postjoin capture chain')
 need(capture['all_recorded_actors_absent']==actors and len(actors)==len(retained['actors'])+15,'exact retained/failed/recovery plus cleanup+14; no actor dropped')
 need(capture['current_free_candidate']is True and capture['independent_acceptance']is False and capture['current_physical_clearance_pending']is True and capture['actual_latest_operation_postjoin_acceptance']is None,'raw candidate cannot self-accept')
 need(capture['artifact_acceptance']is False and capture['native_acceptance']is False and capture['runtime_authority']is None and capture['artifact_rejection']==PINS['artifact_rejection'] and capture['registry_failure']==PINS['registry_failure'],'rejected118/native history not promoted')
 need(capture['unknown_births_not_filled']==retained['unknown_births'] and capture['unmeasured_actor_gaps']==retained['b']['actor_gaps'] and capture['unmeasured_inherited_observer_client_births']is True,'all unknown birth limitations retained')
 first=capture['observed_clocks'];last=capture['last_observed_clocks'];limits=capture['fixed_cutoffs']
 need(capture['boot_id']==BOOT and len(first)==len(last)==len(limits)==3 and all(type(v)in(int,float) and math.isfinite(v)for v in first+last+limits),'same boot finite clocks')
 need(all(0<a<=b<limit<=maximum for a,b,limit,maximum in zip(first,last,limits,PINS['limits'])) and 0<=last[1]-first[1]<=120,'original120s current caps')
 need(first[0]>=checked(pending_ref)['recorded_epoch'],'fresh after entire actual pending frontier')
 old=capture['historical_Root63_reobservation']
 need(old['Root63']==PINS['base_ledger'] and old['actual_latest_operation_postjoin_acceptance']==retained['prior']['latest_accepted_free_boundary'] and old['pids_current']==0 and old['no_existing_heavy']is True and old['active_shared_records_absent']is True and len(old['closed_exclusive_probes'])==2,'full historical machinery and original closed probes retained')
 need(old['fixed_cutoffs']==limits and first[0]<=old['observed_clocks'][0]<=old['last_observed_clocks'][0]<=last[0],'entire inherited chain inside same current caps/window')
 retained['base'].validate_fresh_physical(old['historical_Root61_reobservation'],actors,old['BFD_exact_absence_queries'],old['observed_clocks'],old['last_observed_clocks'],limits)
 need(old['capacity']['/home/holden/mckernel']>=16*2**30 and old['capacity']['/home/holden/mckernel-work/scratch']>=12*2**30,'original floors')
 clients=validate_new_commands(capture,retained,receipts,actors)
 need(all(first[0]<=r['started_epoch']<=r['finished_epoch']<=last[0]for r in clients),'all eight raw receipt clocks within fresh capture')
 need(capture['post_Root64_retirement_custody']==bindings['custody_supplement'] and capture['old_readonly_client_status']=='UNKNOWN','supplement carried into raw result without positive old-client status')
 need(capture['complete_recursive_capture_scope']==capture_scope() and capture['fresh_postjoin_PID_FD_lock_absence']is True,'full inherited+new scope and fresh own-FD/mutex proof')
 return clients

def validate_acceptance(free,capture,capture_ref,parent,parent_ref,bindings,retained):
 clients=validate_capture(capture,bindings,retained)
 need(free['post_Root64_retirement_custody']==bindings['custody_supplement'] and free['old_readonly_client_status']=='UNKNOWN','independent acceptance retains exact supplementary history and UNKNOWN status')
 need(checked(capture_ref)==capture and checked(parent_ref)==parent,'same exact authenticated capture and parent bytes')
 retained['base'].validate_parent_join(parent,capture['observer_self']) # Generic capture-parent ABI remains strict.
 need(free['independent']is True and free['implementation_ownership']is False and free['decision']=='PASS_ROOT64_CURRENT118_POSTJOIN_CURRENT_FREE' and free['current_free']is True,'new independent current-free only')
 for key,wanted in [('Root64',bindings.get('pending_ledger',bindings['ledger'])),('actual_postjoin_observation',capture_ref),('capture_positive_join',parent_ref),('retirement_result',bindings['retirement_result']),('retirement_parent_join',bindings['retirement_parent_join'])]:need(free[key]==wanted,'exact independent acceptance '+key)
 need(free['producer_nonce']==NONCE and free['all_recorded_actors_absent']is True and free['pids_current']==0 and free['no_existing_heavy']is True and free['fresh_cleanup_PID_and_own_FD_absent']is True and free['permanent_mutex_rows_absent']is True,'fresh actual retirement/capture absence acceptance')
 need(free['native_operation_reclassified_as_ordinary']is False and free['artifact_acceptance']is False and free['native_acceptance']is False and free['artifact_rejection']==PINS['artifact_rejection'],'currentfree never accepts rejected artifact/native')
 need(free['unknown_births_not_filled']==capture['unknown_births_not_filled'] and free['unmeasured_actor_gaps']==capture['unmeasured_actor_gaps'] and free['complete_recursive_capture_scope']==capture_scope(),'same explicit limitations/full scope')
 return clients

def validate_current_adoption(bindings,retained):
 attach_custody(bindings,retained)
 pending=checked(bindings['pending_ledger']);validate_pending_ledger(pending,retained)
 free=checked(bindings['latest_free']);capture_ref=free['actual_postjoin_observation'];parent_ref=free['capture_positive_join'];capture=checked(capture_ref)
 validate_acceptance(free,capture,capture_ref,checked(parent_ref),parent_ref,bindings,retained)
 ledger=checked(bindings['ledger']);need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary']is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation']is True,'Root-only newly accepted ledger')
 allowed={'prior_ledger_retained','latest_accepted_free_boundary','current_physical_clearance_pending','current118_build','recorded_epoch','note','status'}
 for key,value in pending.items():
  if key not in allowed:need(ledger[key]==value,'unchanged history/adoption '+key)
 need(set(ledger)==set(pending) and ledger['consumed_nonces']==pending['consumed_nonces'] and len(ledger['consumed_nonces'])==72 and ledger['prior_ledger_retained']==bindings['pending_ledger'],'same72 once; pending64 retained')
 need(ledger['current_physical_clearance_pending']is False and ledger['latest_accepted_free_boundary']==bindings['latest_free'] and pending['recorded_epoch']<=ledger['recorded_epoch']<PINS['limits'][0],'actual new free after pending64')
 expected=dict(pending['current118_build']);expected.update(normal_retirement_pending=False,current_physical_clearance_pending=False,current_free=bindings['latest_free'],retirement_result=bindings['retirement_result'],retirement_parent_join=bindings['retirement_parent_join'])
 need(ledger['current118_build']==expected,'only truthful physical retirement/current adoption; artifact rejection remains')
 boundary=checked(bindings['current_boundary'])
 need(boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary']is True and boundary['nonce_ledger']==bindings['ledger'] and boundary['native_custody_clearance']==bindings['latest_free'] and boundary['observer']==ref(__file__),'Root65 descriptor binds actual new observer/ledger/free')
 schema=checked(boundary['observer_schema']);review=checked(boundary['observer_schema_review'])
 need(schema==observer_schema() and review['independent']is True and review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['reviewed_observer_schema']==boundary['observer_schema'],'exact Root65 typed observer schema and independent review')
 auth(boundary['independent_current_boundary_review']);return capture

def observer_schema():
 return dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(__file__),ledger_key='Root65',expected_status=CURRENT_STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')

def observe(bindings,out):
 retained=validate_retained();attach_custody(bindings,retained);accepted=None
 if bindings['phase']=='postjoin_candidate':validate_pending_ledger(checked(bindings['ledger']),retained)
 else:accepted=validate_current_adoption(bindings,retained)
 retirement,retirement_commands,retired=validate_retirement(retained,bindings['retirement_result'],bindings['retirement_parent_join'])
 actors=retained['actors']+retired
 if accepted is not None:
  actors.append(actor(accepted['observer_self'],'accepted_Root64_capture'))
  actors.extend(actor(dict(r,group=r['pid']),'accepted_Root64_query_client')for r in accepted['query_clients'])
 guard=runtime_dependencies(bindings);first=guard.guard()
 historical=load(PINS['runtime_base_source'],'weekly_recursive_Root63_live_observer').observe(checked(bindings['recursive_current63_bindings']),out)
 retained['base'].validate_fresh_physical(historical['historical_Root61_reobservation'],actors,historical['BFD_exact_absence_queries'],historical['observed_clocks'],historical['last_observed_clocks'],historical['fixed_cutoffs'])
 retained['frontier_core'].validate_fresh_closed_unlaunched(historical,retained['frontier'],retained['base'])
 executor=retained['executor'];b=retained['b'];cls,_=executor.transport(b);commands=cls(out,executor.Stop())
 def before_popen(argv):
  guard.guard();limits=tuple(guard.current_cutoffs()) # All I/O completes first.
  now=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME))
  need(len(limits)==3 and all(type(v)in(int,float) and math.isfinite(v)for v in now+limits) and all(0<a<limit<=maximum for a,limit,maximum in zip(now,limits,PINS['limits'])) and 0<=now[1]-first[1]<120,'final direct clocks/caps/age; no I/O after this before Popen')
 commands.before_popen=before_popen
 for argv in [PREFIX+['ps','-aq','--no-trunc','--filter','id='+CID],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+NAME+'$']]:
  response=commands.exact(argv,30);need(response.stdout==response.stderr=='','fresh exact CID/name absence')
 normal=load(b['normal'],'CURRENT118_unchanged_full_census');primitive=load(b['primitive'],'CURRENT118_original_birth_helper')
 caller=[os.getpid(),primitive.proc_stat(os.getpid())[19]];challenge=uuid.uuid4().hex
 original=retained['base'].validate_capture_commands(historical);prior_records=retained['base'].command_records(commands);prior_pids=[r['pid']for r in retirement_commands+original+prior_records]+[r['pid']for r in actors]
 code=executor.process_source(normal,checked(b['packet']),b,prior_pids);argv=['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,challenge,str(caller[0]),caller[1]]
 response=commands.exact(argv,30);report=executor.strict(response.stdout)
 records=retained['base'].command_records(commands)
 executor.validate_process(report,normal,b,challenge,caller,prior_pids)
 validate_absence_reports(historical['complete_process_reports']+[report],actors)
 for row in actors:need(not Path('/proc',str(row['pid'])).exists(),'fresh recorded actor PID absent')
 for row in actors:
  if row.get('fd')is not None:need(not Path('/proc',str(row['pid']),'fd',str(row['fd'])).exists(),'fresh holder/cleanup own FD absent')
 need(not any(len(parts)>=8 and parts[5]=='00:1b:4'for parts in (line.split()for line in Path('/proc/locks').read_text().splitlines())),'fresh permanent27:4 no lock rows')
 last=guard.guard();limits=list(guard.current_cutoffs())
 value=dict(status=STATUS,Root64=bindings['ledger'],current_boundary=bindings['ledger'],actual_latest_operation_postjoin_acceptance=None,historical_Root63_reobservation=historical,ordinary_CURRENT118_build_nonce=NONCE,retired_CURRENT118_CID=CID,retirement_result=bindings['retirement_result'],retirement_parent_join=bindings['retirement_parent_join'],all_recorded_actors_absent=actors,current118_query_command_receipts=commands.receipts,current118_complete_process_reports=[report],query_clients=[dict(pid=r['pid'],birth=r['birth'])for r in original+records],observer_self=dict(pid=caller[0],birth=int(caller[1]),group=os.getpgrp()),observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=limits,boot_id=BOOT,current_free_candidate=True,independent_acceptance=False,current_physical_clearance_pending=True,artifact_acceptance=False,native_acceptance=False,runtime_authority=None,artifact_rejection=PINS['artifact_rejection'],registry_failure=PINS['registry_failure'],unknown_births_not_filled=retained['unknown_births'],unmeasured_actor_gaps=b['actor_gaps'],unmeasured_inherited_observer_client_births=True,complete_recursive_capture_scope=capture_scope(),fresh_postjoin_PID_FD_lock_absence=True,post_Root64_retirement_custody=bindings['custody_supplement'],old_readonly_client_status='UNKNOWN')
 if accepted is None:validate_capture(value,bindings,retained)
 else:
  need(len(actors)==len(retained['actors'])+24,'all retained/failed/recovery/cleanup plus accepted capture and eight clients')
  # Accepted-phase reobservation still runs all original runtime predicates above.
  need(all(a<=z<limit<=maximum for a,z,limit,maximum in zip(first,last,limits,PINS['limits'])) and 0<=last[1]-first[1]<=120,'unchanged accepted observation window/caps')
  value.pop('Root64');value.update(status=CURRENT_STATUS,Root65=bindings['ledger'],current_boundary=bindings['current_boundary'],actual_latest_operation_postjoin_acceptance=bindings['latest_free'],current_free_candidate=False,current_physical_clearance_pending=False,historical_accepted_Root64_capture=checked(bindings['latest_free'])['actual_postjoin_observation'])
 return value

def main():
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
 for key in ('bindings','release','output'):parser.add_argument('--'+key,type=Path,required=True)
 parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
 release_ref=ref(args.release);need(release_ref['sha256']==args.release_sha256,'exact release SHA')
 release=checked(release_ref);binding_ref=ref(args.bindings)
 need(release['author']=='/root' and release['decision']=='AUTHORIZE_ONE_ROOT64_CURRENT118_POSTJOIN_READONLY_CAPTURE' and release['maximum_invocations']==1 and release['source']==ref(__file__) and release['inputs']==ref(HERE/'INPUTS.json') and release['bindings']==binding_ref and release['output']==str(args.output) and release['capture_scope']==capture_scope() and release['execution_profile']==PROFILE,'one exact complete source/config/output/scope ordinary capture release')
 review=checked(release['independent_execution_review']);need(review['independent']is True and review['implementation_ownership']is False and review['decision']=='PASS_EXACT_ROOT64_READONLY_CAPTURE' and review['release_payload']=={k:v for k,v in release.items()if k!='independent_execution_review'},'independent exact execution review')
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0} and 0<resource.getrlimit(resource.RLIMIT_AS)[0]<=2<<30 and 0<resource.getrlimit(resource.RLIMIT_CPU)[0]<=60,'ordinary reviewed CPU0/UID1000/resource profile')
 out=args.output.parent;need(out.parent==HERE and out.name.startswith('actual-postjoin-capture-') and not out.exists(),'fresh confined output')
 out.mkdir(mode=0o700)
 with args.output.open('x')as stream:
  try:value=observe(checked(binding_ref),out)
  except BaseException as error:stream.write(json.dumps(dict(status='READONLY_ROOT64_CAPTURE_FAILED_NO_RETRY',error=repr(error),runtime_authority=None))+'\n');raise
  stream.write(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(status=value['status'],output=ref(args.output),runtime_authority=None)))
if __name__=='__main__':main()
