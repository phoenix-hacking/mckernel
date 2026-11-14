"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Typed Root62 post-BFD extension. Import/retained validators perform no live checks.
Root61/free6c83 remain historical; this observer alone supplies no current-free.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
import resource
import re
import subprocess
import uuid
import types
import time

HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'INPUTS.json').read_bytes())
NONCE=PINS['nonce'];CID=PINS['CID'];NAME=PINS['NAME']
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
STATUS='PASS_Root62_BFD_POSTJOIN_OBSERVATION_PENDING_INDEPENDENT_ACCEPTANCE'
CURRENT_STATUS='PASS_Root63_BFD_CURRENT_REOBSERVATION_PENDING_ROOT_ACCEPTANCE'
PREFIX=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']

def need(ok,why):
 if not ok:raise ValueError(why)
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 need(type(row)is dict and set(row)=={'path','bytes','sha256'}and ref(row['path'])==row,'exact BYTE subject');return Path(row['path'])
def checked(row):return json.loads(auth(row).read_bytes())
def load(row,name):
 spec=importlib.util.spec_from_file_location(name,auth(row));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def validate_retained():
 """Reuse genuine61actor/70nonce history and real BFD pure producer validators."""
 history=load(PINS['history_source'],'retained_BFD_Root61_predicates')
 prior,free,ext,actors=history.validate_current(history.CURRENT)
 need(len(prior['consumed_nonces'])==70 and len(actors)==61,'all genuine Root61 history retained')
 packet=checked(PINS['retirement_packet'])
 validator=load(PINS['retained_validator'],'retained_actual_BFD_three_command_validator')
 validator.validate(packet)
 template=checked(PINS['ledger_draft'])['bfd_default_build']
 artifact=checked(PINS['artifact_review'])
 need(artifact['independent']is True and artifact['implementation_ownership']is False and artifact['artifact_acceptance']is True and artifact['runtime_authority']is None,'actual artifact review only')
 need(artifact['producer_nonce']==NONCE and artifact['container']==CID and artifact['actual_worker']==template['worker_result']and artifact['producer_profile']==template['profile'],'exact BFD artifact/producer joins')
 worker=checked(template['worker_result']);profile=checked(template['profile']);plan=checked(template['plan'])
 need(worker['commands']==packet['actual_commands']or all({k:r[k]for k in ['index','argv','cwd','returncode','started_at_epoch','finished_at_epoch']}==v for r,v in zip(worker['commands'],packet['actual_commands'])),'exact original three command records')
 need(len(worker['commands'])==3 and plan['commands']==profile['exact_commands'],'three frozen producer argv')
 for row,command in zip(worker['commands'],profile['exact_commands']):
  need(row['argv']==command['argv']and row['cwd']==command['cwd']and row['returncode']==0,'exact actual BFD argv/cwd/return')
 tool=checked(PINS['holder_tool_join'])
 need(tool['author']=='/root'and tool['decision']=='ROOT_ATTESTS_OBSERVED_ACTUAL_TOOL_SESSION_JOIN'and tool['session_id']==94204 and tool['returncode']==0 and tool['joined']is True,'actual Root tool94204 observation attestation')
 need(tool['actual_tool_response']['chunk_id']=='8c21ed'and tool['actual_tool_response']['exit_code']==0,'original tool response retained')
 need(tool['holder']==dict(pid=2124365,start='101427979')and tool['runner']==dict(pid=2124454,start='101432667'),'actual holder/runner identities')
 finite=checked(PINS['finite_join']);completion=checked(PINS['finite_completion']);prewarm=checked(PINS['prewarm'])
 need(finite['pid']==prewarm['pid']==2123297 and finite['starttime']==prewarm['starttime']==101423116 and finite['returncode']==0 and finite['positive_direct_wait_join']is True and finite['streams_closed']is True and finite['process_group_absent']is True and not finite['remaining_group_members']and not finite['group_observation_errors'],'finite reviewer actual positive parent join')
 need(completion['nonce']==NONCE and completion['actual_positive_join']==PINS['finite_join']and completion['actual_independent_Hot_PASS']==PINS['finite_pass']and completion['finite_runs']==1 and completion['automatic_retries']==0,'finite completion joins exact actual run')
 once=checked(PINS['once']);passed=checked(PINS['finite_pass'])
 need(once['author']=='/root'and once['nonce']==passed['nonce']==NONCE and once['actual_independent_PASS']==PINS['finite_pass'],'actual one-use publication and independent pass')
 known=list(actors)+[dict(pid=2124365,start=101427979,role='BFD_holder'),dict(pid=2124454,start=101432667,role='BFD_runner'),dict(pid=2123297,start=101423116,role='BFD_finite_reviewer')]
 for prefix in ['physical','held']:
  started=checked(PINS[prefix+'_started']);joined=checked(PINS[prefix+'_join'])
  need(joined['pid']==started['pid']and joined['argv']==started['argv']and joined['nonce']==NONCE and joined['returncode']==0 and joined['direct_child_joined']is True and joined['group_absent']is True and joined['closed_streams']is True,'actual BFD '+prefix+' capture positive join')
  need(joined['prewarm_ready']==PINS['prewarm'],'same independent prewarm across captures')
  for key in ['stdout','stderr']:auth(joined[key])
  known.append(dict(pid=started['pid'],start=started['starttime'],role='BFD_'+prefix+'_capture'))
 failed=checked(PINS['failed_retirement_attempt']);failedjoin=checked(failed['parent_join'])
 need(failed['author']=='/root'and failed['decision']=='ACTUAL_FIRST_RETIREMENT_ATTEMPT_FAILED_BEFORE_QUERY_OR_REMOVAL'and failed['actor']['pid']==2145640 and int(failed['actor']['birth'])==101816056 and failed['Docker_queries_started']==failed['removals']==0 and failed['removal_claim_created']is False and failed['container_retained']is True and failed['current_physical_clearance']is False,'actual first UUID failure retained without cleanup/current acceptance')
 need(failedjoin['pid']==2145640 and int(failedjoin['birth'])==101816056 and failedjoin['returncode']==1 and failedjoin['positive_direct_parent_wait']is True and failedjoin['parent_streams_closed']is True,'actual failed actor parent join; future full census must prove absence')
 for key in ['stdout','stderr']:need(failedjoin[key]==failed[key],'same original failure streams');auth(failed[key])
 auth(failed['attempt_started']);auth(failed['release']);auth(failed['source_executor'])
 need(len(known)==66 and known[:61]==actors and len({(r['pid'],r['start'])for r in known[61:]})==5 and not ({(r['pid'],r['start'])for r in known[61:]}&{(r['pid'],r['start'])for r in actors}),'exact61row historical multiset plus five distinct recorded BFD actors')
 known.append(dict(pid=2145640,start=101816056,role='BFD_failed_cleanup_uuid_prequery'))
 second=checked(PINS['failed_retirement_attempt_2']);second_join=checked(second['parent_join'])
 need(second['author']=='/root'and second['decision']=='ACTUAL_SECOND_RETIREMENT_ATTEMPT_FAILED_IN_PREINSPECT_BEFORE_REMOVAL'and second['actor']['pid']==2153594 and int(second['actor']['birth'])==101972261 and second['removals']==0 and second['removal_claim_created']is False and second['container_retained']is True and second['current_physical_clearance']is False and second['build_nonce']==NONCE and second['build_nonce_remains_consumed_once']is True,'actual second image-profile failure retained before removal; no clearance')
 need(second_join['pid']==2153594 and int(second_join['birth'])==101972261 and second_join['returncode']==1 and second_join['positive_direct_parent_wait']is True and second_join['parent_streams_closed']is True,'actual second failed actor direct parent rc1 join; future census must prove absence')
 for key in ['stdout','stderr']:need(second_join[key]==second[key],'same original second failure streams');auth(second[key])
 for key in ['attempt_started','release','source_executor']:auth(second[key])
 need(len(second['commands'])==4,'exact four original second-attempt readonly command records')
 command_refs=[]
 for command in second['commands']:
  refs=[row for row in command['files']if Path(row['path']).name=='JOIN-WAIT4.json'];need(len(refs)==1,'one actual command positive wait4 receipt')
  need(checked(refs[0])==command['join'],'Root retained command row equals original authenticated wait4 receipt')
  for row in command['files']:auth(row)
  need({row['path']for row in command['files']}=={refs[0]['path']}|{row['path']for row in command['join']['raw'].values()},'exact original JOIN/raw receipt closure')
  command_refs.append(refs[0])
 clients=validate_recorded_clients(command_refs)
 need([(row['pid'],row['birth'])for row in clients]==[(2153595,101972338),(2153599,101972387),(2153607,101972458),(2153616,101972497)],'four exact recorded second-attempt query births; no invented client identity')
 known.append(dict(pid=2153594,start=101972261,role='BFD_failed_cleanup_image_preinspect'))
 known.extend(dict(pid=row['pid'],start=row['birth'],role='BFD_failed_cleanup2_recorded_command')for row in clients)
 return dict(prior=prior,prior_free=free,prior_actors=actors,actors=known,bfd=template,packet=packet)

def validate_pending_ledger(ledger,retained):
 prior=retained['prior']
 need(ledger['author']=='/root'and ledger['complete_within_declared_current_boundary']is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation']is True,'Root-only complete no-unlisted-operation attestation')
 need(ledger['prior_ledger_retained']==PINS['prior_ledger']and ledger['consumed_nonces']==prior['consumed_nonces']+[NONCE]and len(set(ledger['consumed_nonces']))==71,'exact prior70 plus faac once')
 allowed={'author','complete_within_declared_current_boundary','root_attests_no_unlisted_post_boundary_execution_or_custody_operation','consumed_nonces','prior_ledger_retained','current_physical_clearance_pending','bfd_default_build','recorded_epoch','current_thread','note'}
 for key,value in prior.items():
  if key not in allowed:need(ledger[key]==value,'entire inherited typed history retained: '+key)
 need(ledger['current_physical_clearance_pending']is True and ledger['latest_accepted_free_boundary']==prior['latest_accepted_free_boundary'],'old6c83 remains historical; new physical pending')
 expected=dict(retained['bfd']);expected['actual_holder_tool_join_receipt']=PINS['holder_tool_join'];expected['current_default_artifact_acceptance']=PINS['artifact_review'];expected['failed_retirement_attempts']=[PINS['failed_retirement_attempt'],PINS['failed_retirement_attempt_2']]
 need(ledger['prior_pending_ledger']==PINS['prior_pending_root62']and checked(PINS['prior_pending_root62'])['prior_pending_ledger']==PINS['original_pending_root62'],'immutable original and first-failure pending ledgers retained before second failed custody supplement')
 need(ledger['bfd_default_build']==expected,'only exact recorded ordinary BFD extension')
 need(ledger['current_thread']=='01a183ec-72e5-7400-8f48-b4efb8725520'and type(ledger['recorded_epoch'])in (int,float)and math.isfinite(ledger['recorded_epoch'])and retained['packet']['actual_commands'][-1]['finished_at_epoch']<=ledger['recorded_epoch']<PINS['limits'][0],'actual restart identity and postproducer recorded epoch')
 return True

def validate_fresh_physical(history,actors,queries,first,last,limits):
 need(history['Root61']==PINS['prior_ledger'],'Root61 output tagged historical input')
 need(history['pids_current']==0 and history['no_existing_heavy']is True and history['active_shared_records_absent']is True and len(history['closed_exclusive_probes'])==2,'unchanged complete physical/cgroup/shared/exclusive custody predicates')
 need(history['capacity']['/home/holden/mckernel']>=16*2**30 and history['capacity']['/home/holden/mckernel-work/scratch']>=12*2**30,'original capacity floors')
 census=history['group_membership_observation'];need(not census['errors'],'complete fresh full process/group census')
 for actor in actors:
  need(not any(row['pid']==actor['pid']or row['pgrp']==actor.get('group',actor['pid'])for row in census['rows']),'all recorded old/BFD/cleanup actors absent')
 expected=[PREFIX+['ps','-q','--no-trunc'],PREFIX+['ps','-aq','--no-trunc','--filter','id='+CID],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+NAME+'$']]
 need(len(queries)==3,'three exact fresh BFD running/ID/name absence queries')
 for row,argv in zip(queries,expected):need(row['argv']==argv and row['returncode']==0 and row['stdout']==row['stderr']=='','exact fresh BFD ID/name/running absence')
 need(history['boot_id']==BOOT and len(first)==len(last)==len(limits)==3,'same boot and three explicit clocks')
 need(all(type(v)in (int,float)and math.isfinite(v)for v in first+last+limits),'finite clocks')
 need(all(a<=b<limit<=ceiling for a,b,limit,ceiling in zip(first,last,limits,PINS['limits'])),'fresh observation under actual tighter clamps')
 need(history['fixed_cutoffs']==limits,'every recursive history depth uses actual same guard limits')
 need(last[1]-first[1]<=120,'bounded120second readonly observer window')
 return True

def consumer_value(history,ledger_ref,retirement_ref,retirement_join_ref,actors,queries,first,last,limits):
 """Candidate-only result. A separate real postjoin acceptance must clear pending."""
 value=dict(history)
 value.pop('Root61',None)
 value['known_numeric_controls_absent']=sorted(set(history['known_numeric_controls_absent']+[actor['pid']for actor in actors]))
 value.update(status=STATUS,Root62=ledger_ref,current_boundary=ledger_ref,actual_latest_operation_postjoin_acceptance=None,previous_historical_Root61=PINS['prior_ledger'],previous_historical_free=checked(PINS['prior_ledger'])['latest_accepted_free_boundary'],historical_Root61_reobservation=history,ordinary_BFD_build_nonce=NONCE,retired_BFD_CID=CID,BFD_retirement_result=retirement_ref,BFD_retirement_parent_join=retirement_join_ref,all_recorded_actors_absent=actors,BFD_exact_absence_queries=queries,current_free_candidate=True,independent_acceptance=False,current_physical_clearance_pending=True,observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=limits,boot_id=BOOT,native_acceptance=False,artifact_acceptance=False,runtime_authority=None,unmeasured_producer_Docker_client_births=True,unmeasured_births_are_not_claimed_retired=True)
 return value

def validate_parent_join(value,actor):
 need(value['pid']==actor['pid']and int(value['starttime'])==int(actor['birth'])and value['returncode']==0 and value['positive_direct_wait_join']is True and value['streams_closed']is True and value['process_group_absent']is True and not value['remaining_group_members']and not value['group_observation_errors'],'separate parent positive retirement join; result cannot prove own exit')

def validate_retirement(executor,result_ref,parent_join_ref):
 b=executor.bindings();value=checked(result_ref)
 receipts=executor.validate_result(value,b)
 parent=checked(parent_join_ref);actor=value['cleanup_actor']
 need(parent['pid']==actor['pid']and int(parent['birth'])==int(actor['birth'])and parent['returncode']==0 and parent['positive_direct_parent_wait']is True and parent['parent_streams_closed']is True,'actual Root direct retirement-parent ABI and exact cleanup identity; no inherited-group absence claim')
 stdout=auth(parent['stdout']).read_bytes();need(auth(parent['stderr']).read_bytes()==b'','actual retirement parent streams and empty stderr')
 published=json.loads(stdout)
 need(published==dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=result_ref),'actual Root-parent stdout names exact validated retirement RESULT')
 need(value['final_safety']['mutex']['device']==27 and value['final_safety']['mutex']['inode']==4 and value['cleanup_actor']['mutex_fd']==value['final_safety']['mutex']['fd'],'same original normal cleanup27:4 FD')
 need(value['own_fd_closed_only_after_result_on_normal_return']is True,'normal return closes own FD only')
 need(value['original_Docker_actor_gaps']==b['actor_gaps'],'original unmeasured producer/writer births stay explicit')
 actors=[dict(pid=value['cleanup_actor']['pid'],start=int(value['cleanup_actor']['birth']),role='BFD_cleanup_executor',group=None,inherited_parent_group_absence_not_claimed=True)]
 for receipt in receipts:actors.append(dict(pid=receipt['pid'],start=receipt['birth'],role='BFD_cleanup_recorded_command'))
 # Retained duplicate rows stay explicit; only identical evidence-created command
 # identities may repeat. No unknown producer Docker birth is filled in.
 return b,value,receipts,actors

def runtime_dependencies(bindings):
 need(bindings['author']=='/root'and bindings['decision']=='BIND_EXACT_ROOT62_BFD_POSTJOIN_OBSERVER'and bindings['runtime_authority']is None,'Root-only actual observer binding')
 for key in ['ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration','independent_review']:auth(bindings[key])
 need(bindings['guard_adapter']==PINS['guard_adapter'],'new exact current62 adapter; no producer-op alias')
 review=checked(bindings['independent_review'])
 need(review['decision']=='PASS_EXACT_ROOT62_BFD_POSTJOIN_OBSERVER_DEPENDENCIES'and review['independent']is True and review['implementation_ownership']is False and review['observer']==ref(__file__),'independent exact new runtime dependency review')
 for key in ['ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration']:need(review[key]==bindings[key],'exact reviewed '+key)
 need(review['capture_scope']==capture_scope(),'independent review covers full inherited recursive query/probe chain and five tracked commands')
 need(bindings['phase']in ('postjoin_candidate','accepted_current')and review['phase']==bindings['phase'],'explicit candidate/current phase')
 if bindings['phase']=='accepted_current':
  for key in ['pending_ledger','latest_free','current_boundary']:need(review[key]==bindings[key],'exact adopted current '+key);auth(bindings[key])
 config=checked(bindings['guard_configuration'])
 need(config['operation']==PINS['new_operation']and config['shared_guard']==PINS['shared_guard'],'new current62 operation and exact restart shared guard')
 operation=checked(config['successor']);need(operation['guardian']==dict(source=PINS['guardian'],entrypoint='guard'),'actual restart guardian4889 at new current boundary')
 common=checked(ref(HERE/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json'))
 root61=checked(ref(HERE/'history/ROOT61-RUNTIME-DEPENDENCIES.json'))
 physical=checked(common['physical_history_configuration'])
 need(common['account_window_guard']==root61['guard_adapter']==physical['guard_adapter']==bindings['guard_adapter'],'same new adapter every recursive depth')
 need(common['account_window_guard_configuration']==root61['guard_configuration']==physical['guard_config']==bindings['guard_configuration'],'same new config every recursive depth')
 guard=load(bindings['guard_adapter'],'actual_current62_new_operation_adapter')
 need(guard.OPERATION==PINS['new_operation'],'explicit postjoin operation only');guard.configure(bindings['guard_configuration'])
 return guard

def validate_recorded_clients(receipts):
 result=[checked(row)for row in receipts]
 for row in result:
  need(type(row['birth'])is int and row['birth']>0 and row['positive_wait4']is True and row['wait4_pid']==row['pid']and row['wait4_status']==0 and row['returncode']==0 and row['group_absent']is True and not row['group_members']and row['streams_closed']is True and row['client_retirement_unproven']is False and row['signals_sent']==0,'every new query client has birth/wait4/group/stream proof')
  need(set(row['raw'])=={'stdout','stderr','status.json'},'full original query stream/status captures')
  for value in row['raw'].values():auth(value)
  status=checked(row['raw']['status.json']);need(status['state']=='exited'and status['pid']==row['pid']and status['argv']==row['argv']and status['exit_code']==0,'same exact original query status and argv')
 return result

def command_records(commands):
 need(not commands.client_retirement_unproven,'readonly observer command uncertainty preserved')
 return validate_recorded_clients(commands.receipts)

def validate_capture_commands(capture):
 rows=validate_recorded_clients(capture['query_command_receipts'])
 need(len(rows)==5,'exact two full census and three absence command receipts')
 executor=load(PINS['retirement_executor'],'pure_exact_postjoin_query_scope');b=executor.bindings()
 tree=ast.parse(auth(b['normal']).read_bytes())
 values=[ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(target,ast.Name)and target.id=='PROC_CODE'for target in node.targets)]
 need(len(values)==1 and type(values[0])is str,'exact inherited full census source')
 code=executor.process_source(types.SimpleNamespace(PROC_CODE=values[0]),checked(b['packet']))
 normal=executor.load(b['normal'],'pure_unchanged_normal_census_revalidation')
 retirement=checked(capture['BFD_retirement_result']);retired=executor.validate_result(retirement,b)
 retired_pids=[row['pid']for row in retired]+[retirement['cleanup_actor']['pid']]
 caller=capture['observer_self']
 for index in (0,4):
  argv=rows[index]['argv']
  need(len(argv)==10 and argv[:6]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c']and argv[6]==code and re.fullmatch('[0-9a-f]{32}',argv[7])and argv[8:]==[str(caller['pid']),str(caller['birth'])],'exact existing group-extended full census command/caller')
  report=json.loads(auth(rows[index]['raw']['stdout']).read_bytes())
  need(report==capture['complete_process_reports'][0 if index==0 else 1],'same original full census raw report')
  executor.validate_process(report,normal,b,argv[7],[caller['pid'],str(caller['birth'])],retired_pids+[row['pid']for row in rows[:index]])
 expected=[PREFIX+['ps','-q','--no-trunc'],PREFIX+['ps','-aq','--no-trunc','--filter','id='+CID],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+NAME+'$']]
 for index,(row,argv)in enumerate(zip(rows[1:4],expected),1):
  need(row['argv']==argv and auth(row['raw']['stdout']).read_bytes()==auth(row['raw']['stderr']).read_bytes()==b'','same exact fresh query argv/empty raw replies')
  need(capture['BFD_exact_absence_queries'][index-1]['command_receipt']==capture['query_command_receipts'][index],'same exact query receipt in candidate result')
 return rows

def source_subjects():
 """Static source closure only; no runtime-config hash cycle or live check."""
 result=dict(observer=ref(__file__),inputs=ref(HERE/'INPUTS.json'),history_data_filler=ref(HERE/'bind_history.py'),guard_adapter=PINS['guard_adapter'],shared_guard=PINS['shared_guard'],guardian=PINS['guardian'],retirement_executor=PINS['retirement_executor'],retirement_bindings=PINS['retirement_bindings'])
 for name in ['observe_bfd_current61.py','observe_bfd_current60_history.py','observe_bfd_root59_history.py']:result['history:'+name]=ref(HERE/'history'/name)
 executor=load(PINS['retirement_executor'],'pure_current62_source_closure');b=executor.bindings()
 for key in ['primitive','normal','backend']:result['reused:'+key]=b[key]
 physical=checked(ref(HERE/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json'))['physical_history_observer']
 result['physical_successor']=physical
 chain=load(physical,'pure_complete_current62_physical_source_closure').source_chain()
 for path,row in chain.items():result['historical_physical:'+path]=row
 return result

def capture_scope():
 """The release covers the complete recursive chain before the tracked commands."""
 return dict(schema='mckernel.root62.complete-recursive-readonly-capture-scope.v1',recursive_entry=PINS['history_runtime_source'],physical_successor=checked(ref(HERE/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json'))['physical_history_observer'],inherited_scope=['Root61 -> Root60 -> Root59 configured common -> explicit physical successor -> every authenticated historical observer', 'all unchanged inherited Docker read-only argv, historical observer subprocess wrappers and findmnt query', 'complete inherited proc/group/cgroup/FD/socket/mount/capacity reads', 'two original closed exclusive custody probes; no cleanup lock held across workloads'],additional_tracked_commands=5,additional_tracked_command_order=['complete normal process/group census','Docker running absence','exact BFD CID absence','exact BFD name absence','complete normal process/group census'],automatic_retries=0,cleanup_or_signals=False,new_inherited_observer_client_births_remain_unmeasured=True)

def observe(bindings,out):
 """Released readonly capture only; no cleanup, force, signal or record-release API."""
 retained=validate_retained();ledger=checked(bindings['ledger'])
 current_capture=None
 if bindings['phase']=='postjoin_candidate':validate_pending_ledger(ledger,retained)
 else:current_capture=load({'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current62-after-bfd-default-build-source-20261028-1/review-correction-source-1/attempt2-binding-successor-1/retirement-parent-abi-correction-source-1/observe_current62_bfd_postjoin.py', 'bytes': 37436, 'sha256': 'da5a628ca0248c30f78fe6617f50a33b7c469a1095ed4dd28a7d2f1257bd6935'},'frozen_historical_Root63_adoption_only').validate_current_adoption(bindings,retained)
 executor=load(PINS['retirement_executor'],'exact_BFD_normal_retirement_pure_API')
 b,retirement,retirement_commands,retired=validate_retirement(executor,bindings['retirement_result'],bindings['retirement_parent_join'])
 actors=retained['actors']+retired
 if current_capture is not None:
  actors.append(dict(pid=current_capture['observer_self']['pid'],start=current_capture['observer_self']['birth'],role='accepted_Root62_postjoin_capture'))
  actors.extend(dict(pid=row['pid'],start=row['birth'],role='accepted_Root62_query_client')for row in current_capture['query_clients'])
 guard=runtime_dependencies(bindings);first=guard.guard()
 history=load(PINS['history_runtime_source'],'configured_recursive_Root61_historical_observation').observe()
 # Reuse the executor's exact existing wait4 Docker/client transport. This caller
 # never constructs Actual, acquires its cleanup FD, calls safe(), rm or release.
 cls,_namespace=executor.transport(b);commands=cls(out,executor.Stop())
 def before_popen(argv):
  guard.guard()
  limits=tuple(guard.current_cutoffs()) # Finish all source/config/review I/O first.
  now=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME))
  need(len(limits)==3 and all(type(v)in (int,float)and math.isfinite(v)for v in now+limits)and all(0<a<limit<=ceiling for a,limit,ceiling in zip(now,limits,PINS['limits']))and 0<=now[1]-first[1]<120,'final direct UTC/MONO/BOOT caps and preproof age immediately before Popen; no subsequent I/O')
 commands.before_popen=before_popen
 normal=load(b['normal'],'unchanged_full_process_census_predicates')
 primitive=load(b['primitive'],'unchanged_proc_birth_helper')
 packet=checked(b['packet']);caller=[os.getpid(),primitive.proc_stat(os.getpid())[19]]
 reports=[]
 def census():
  challenge=uuid.uuid4().hex;prior=[r['pid']for r in retirement_commands+command_records(commands)]
  code=executor.process_source(normal,packet)
  argv=['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,challenge,str(caller[0]),caller[1]]
  response=commands.exact(argv,30);report=executor.strict(response.stdout)
  executor.validate_process(report,normal,b,challenge,caller,prior+[r['pid']for r in actors])
  reports.append(report)
 census()
 queries=[]
 for argv in [PREFIX+['ps','-q','--no-trunc'],PREFIX+['ps','-aq','--no-trunc','--filter','id='+CID],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+NAME+'$']]:
  response=commands.exact(argv,30);queries.append(dict(argv=argv,returncode=response.returncode,stdout=response.stdout,stderr=response.stderr,command_receipt=commands.receipts[-1]))
 census();records=command_records(commands)
 for actor in actors:
  need(not Path('/proc',str(actor['pid'])).exists(),'recorded old/build/cleanup PID remains absent')
 need(not Path('/proc',str(retirement['cleanup_actor']['pid']),'fd',str(retirement['cleanup_actor']['mutex_fd'])).exists()and not Path('/proc/2124365/fd/3').exists(),'old BFD holder and normal cleanup FD3 absent')
 last=guard.guard();limits=list(guard.current_cutoffs())
 validate_fresh_physical(history,actors,queries,first,last,limits)
 value=consumer_value(history,bindings['ledger'],bindings['retirement_result'],bindings['retirement_parent_join'],actors,queries,first,last,limits)
 value.update(complete_process_reports=reports,query_command_receipts=commands.receipts,query_clients=[dict(pid=r['pid'],birth=r['birth'])for r in records],observer_self=dict(pid=caller[0],birth=int(caller[1]),group=os.getpgrp()),retirement_executor=PINS['retirement_executor'],unmeasured_actor_gaps=b['actor_gaps'],unmeasured_inherited_observer_client_births=True,inherited_observer_client_births_are_not_claimed_recorded=True,complete_recursive_capture_scope=capture_scope())
 value['known_numeric_controls_absent']=sorted(set(value['known_numeric_controls_absent']+[row['pid']for row in records]))
 if current_capture is not None:
  value.pop('Root62')
  value.update(status=CURRENT_STATUS,Root63=bindings['ledger'],current_boundary=bindings['current_boundary'],actual_latest_operation_postjoin_acceptance=bindings['latest_free'],current_free_candidate=False,current_physical_clearance_pending=False,historical_accepted_Root62_capture=checked(bindings['latest_free'])['actual_postjoin_observation'])
 return value

def validate_acceptance(free,capture,capture_ref,parent_join,parent_join_ref,pending_ref,retirement_ref,retirement_join_ref):
 """Pure independent acceptance bindings; called only after capture has exited."""
 need(free['independent']is True and free['implementation_ownership']is False and free['decision']=='PASS_ROOT62_BFD_POSTJOIN_CURRENT_FREE'and free['current_free']is True,'genuine independent new current-free acceptance')
 need(free['Root62']==pending_ref and free['actual_postjoin_observation']==capture_ref and free['capture_positive_join']==parent_join_ref and free['retirement_result']==retirement_ref and free['retirement_parent_join']==retirement_join_ref,'exact new ledger/retirement/capture/join acceptance')
 need(capture['Root62']==pending_ref and capture['status']==STATUS and capture['ordinary_BFD_build_nonce']==NONCE and capture['current_free_candidate']is True and capture['independent_acceptance']is False and capture['actual_latest_operation_postjoin_acceptance']is None,'raw capture never self-accepts or relabels old6c83')
 validate_parent_join(parent_join,capture['observer_self'])
 need(free['producer_nonce']==NONCE and free['native_operation_reclassified_as_ordinary']is False and free['pids_current']==0 and free['no_existing_heavy']is True and free['all_recorded_actors_absent']is True,'typed new current-free scope')
 need(free['unmeasured_producer_Docker_client_births']is True and free['unmeasured_births_are_not_claimed_retired']is True,'preserve original unmeasured child-birth limitation')
 need(free['unmeasured_actor_gaps']==capture['unmeasured_actor_gaps'],'all original unmeasured actor limitations retained')
 need(free['unmeasured_inherited_observer_client_births']is capture['unmeasured_inherited_observer_client_births']is True and free['inherited_observer_client_births_are_not_claimed_recorded']is capture['inherited_observer_client_births_are_not_claimed_recorded']is True and capture['complete_recursive_capture_scope']==capture_scope(),'inherited query subprocesses remain explicit unmeasured client-birth scope')
 clients=validate_capture_commands(capture)
 need(capture['query_clients']==[dict(pid=r['pid'],birth=r['birth'])for r in clients],'accepted query identities derive only from real command receipts')
 need({row['pid']for row in clients}<=set(capture['known_numeric_controls_absent']),'all positive-joined query client identities enter current absence history')
 return True

def validate_current_adoption(bindings,retained):
 """Explicit Root63/free adoption of the real Root62 capture; no nonce append."""
 ledger=checked(bindings['ledger']);pending=checked(bindings['pending_ledger']);free=checked(bindings['latest_free'])
 validate_pending_ledger(pending,retained)
 capture_ref=free['actual_postjoin_observation'];join_ref=free['capture_positive_join'];capture=checked(capture_ref);joined=checked(join_ref)
 validate_acceptance(free,capture,capture_ref,joined,join_ref,bindings['pending_ledger'],bindings['retirement_result'],bindings['retirement_parent_join'])
 need(ledger['author']=='/root'and ledger['complete_within_declared_current_boundary']is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation']is True,'Root-only newly adopted current ledger')
 need(ledger['prior_ledger_retained']==bindings['pending_ledger']and ledger['consumed_nonces']==pending['consumed_nonces']and len(ledger['consumed_nonces'])==71,'same71 consumed; read-only capture adds no duplicate nonce')
 allowed={'prior_ledger_retained','latest_accepted_free_boundary','current_physical_clearance_pending','bfd_default_build','recorded_epoch','current_thread','note'}
 for key,value in pending.items():
  if key not in allowed:need(ledger[key]==value,'unchanged pending/history field on adoption: '+key)
 need(ledger['current_physical_clearance_pending']is False and ledger['latest_accepted_free_boundary']==bindings['latest_free'],'genuine new free, never historical6c83')
 need(ledger['current_thread']==pending['current_thread']and type(ledger['recorded_epoch'])in (int,float)and math.isfinite(ledger['recorded_epoch'])and pending['recorded_epoch']<=ledger['recorded_epoch']<PINS['limits'][0],'same actual restart identity and forward recorded epoch')
 expected=dict(pending['bfd_default_build']);expected.update(current_physical_clearance_pending=False,current_free=bindings['latest_free'])
 need(ledger['bfd_default_build']==expected,'only ordinary BFD physical pending/free adoption changes')
 boundary=checked(bindings['current_boundary'])
 need(boundary['author']=='/root'and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY'and boundary['root_attests_exact_current_boundary']is True and boundary['nonce_ledger']==bindings['ledger']and boundary['native_custody_clearance']==bindings['latest_free']and boundary['observer']==ref(__file__),'actual Root63 descriptor binds new observer/ledger/free')
 for key in ['independent_current_boundary_review','observer_schema','observer_schema_review']:auth(boundary[key])
 schema=checked(boundary['observer_schema']);schema_review=checked(boundary['observer_schema_review'])
 need(schema['schema_version']=='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1'and schema['observer']==ref(__file__)and schema['ledger_key']=='Root63'and schema['expected_status']==CURRENT_STATUS and schema['current_boundary_key']=='current_boundary'and schema['latest_free_key']=='actual_latest_operation_postjoin_acceptance','exact typed current63 schema')
 need(schema_review['independent']is True and schema_review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING'and schema_review['reviewed_observer_schema']==boundary['observer_schema'],'independent new current schema source review')
 return capture

def main():
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
 parser.add_argument('--bindings',type=Path,required=True);parser.add_argument('--release',type=Path,required=True);parser.add_argument('--release-sha256',required=True);parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();release_ref=ref(args.release);need(release_ref['sha256']==args.release_sha256,'exact Root readonly capture release bytes')
 release=checked(release_ref);binding_ref=ref(args.bindings)
 need(release['author']=='/root'and release['decision']=='AUTHORIZE_ONE_ROOT62_BFD_POSTJOIN_READONLY_CAPTURE'and release['maximum_invocations']==1 and release['source']==ref(__file__)and release['inputs']==ref(HERE/'INPUTS.json')and release['bindings']==binding_ref and release['output']==str(args.output),'one exact reviewed source/config/output readonly capture')
 need(release['capture_scope']==capture_scope(),'reviewed full recursive capture scope before five tracked new commands')
 need(release['execution_profile']==dict(uid=1000,cpus=[0],jobs=1,address_space_bytes=2<<30,maximum_CPU_seconds=60,maximum_wall_seconds=120),'exact ordinary readonly capture execution profile')
 review=checked(release['independent_execution_review']);need(review['independent']is True and review['implementation_ownership']is False and review['decision']=='PASS_EXACT_ROOT62_READONLY_CAPTURE'and review['release_payload']=={k:v for k,v in release.items()if k!='independent_execution_review'},'independent exact capture execution release')
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0},'ordinary UID1000 CPU0 source-qualified observer profile')
 need(0<resource.getrlimit(resource.RLIMIT_AS)[0]<=2<<30 and 0<resource.getrlimit(resource.RLIMIT_CPU)[0]<=60,'actual address-space/CPU bounds inherited before capture')
 out=args.output.parent;need(out.parent==HERE and out.name.startswith('actual-postjoin-capture-')and not out.exists(),'fresh source-confined readonly capture metadata root')
 out.mkdir(mode=0o700)
 with args.output.open('x')as stream:
  try:value=observe(checked(binding_ref),out)
  except BaseException as error:
   stream.write(json.dumps(dict(status='READONLY_ROOT62_CAPTURE_FAILED_NO_RETRY',error=repr(error),runtime_authority=None))+'\n');raise
  stream.write(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(status=STATUS,output=ref(args.output),runtime_authority=None)))

if __name__=='__main__':main()
