"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
CURRENT119 postjoin extension of exact accepted LIVE physical observer APIs.
Import/metadata validators never invoke guard/proc/process/Docker/cleanup.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,os,re,resource,time,uuid
HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'INPUTS.json').read_text())
def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(r):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'}and Path(r['path']).is_absolute()and not Path(r['path']).is_symlink()and ref(r['path'])==r,'exact immutable BYTE subject');return Path(r['path'])
def checked(r):return json.loads(auth(r).read_bytes())
def load(r,name):
 p=auth(r);s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
BASE=load(PINS['base_source'],'unchanged_live_Root65_observer')
BOOT=BASE.BOOT;PREFIX=BASE.PREFIX;PROFILE=BASE.PROFILE
STATUS='PASS_Root67_CURRENT119_POSTJOIN_OBSERVATION_PENDING_INDEPENDENT_ACCEPTANCE'

def validate_metadata():
 """Reuse old history only at its pre119 scope; consume actual119 facts separately."""
 executor=load(PINS['executor'],'actual119_normal_retirement');b=executor.bindings();need(PINS['retirement_bindings']==ref(Path(PINS['executor']['path']).parent/'BINDINGS.json'),'same119 executor/bindings')
 ledger=checked(PINS['ledger']);consumed=checked(PINS['consumed_ledger']);prior=checked(PINS['base_ledger']);entry=ledger['current119_build']
 need(ledger['consumed_nonces']==prior['consumed_nonces']+[b['nonce']]and len(ledger['consumed_nonces'])==73 and ledger['current_native_operation']==prior['current_native_operation'],'exact73 once, native history unchanged')
 need(PINS['consumed_ledger']==b['current_ledger']and consumed['current119_build']==b['current_build_ledger_entry'],'genuine73nonce consumed-build entry unchanged')
 allowed={'note','prior_ledger_retained','recorded_epoch','status','current119_build'}
 need(set(ledger)==set(consumed)and all(ledger[k]==v for k,v in consumed.items()if k not in allowed),'all consumed/native/current118/history fields retained exactly')
 expected=dict(consumed['current119_build']);expected.update(normal_retirement_pending=False,retirement_result=PINS['retirement_result'],retirement_parent_join=PINS['retirement_parent_join'],independent_retirement_acceptance=PINS['retirement_acceptance'])
 need(ledger['prior_ledger_retained']==PINS['consumed_ledger']and consumed['recorded_epoch']<=ledger['recorded_epoch']<PINS['limits'][0]and entry==expected and entry['container']==b['cid']and entry['current_physical_clearance_pending']is True and entry['current_free']is None and ledger['current_physical_clearance_pending']is True,'actual Root67 retirement pending fresh current, never Root65 as post119 free')
 acceptance=checked(PINS['retirement_acceptance'])
 need(acceptance['decision']=='PASS_EXACT_CURRENT119_STOPPED_CONTAINER_RETIREMENT_AND_PARENT_JOIN'and acceptance['independent']is True and acceptance['implementation_ownership']is False and acceptance['retirement_result']==PINS['retirement_result']and acceptance['bindings']==PINS['retirement_bindings']and acceptance['normalized_parent_join']==PINS['retirement_parent_join']and acceptance['raw_parent_join']==PINS['retirement_raw_parent_join'],'independently accepted actual119 result and parent proofs')
 value,receipts,retired=BASE.validate_retirement(dict(executor=executor,b=b),PINS['retirement_result'],PINS['retirement_parent_join'])
 normalized=checked(PINS['retirement_parent_join']);parent=checked(PINS['retirement_raw_parent_join']);need(normalized['actual_parent_receipt']==PINS['retirement_raw_parent_join']and normalized['parent_pid']==parent['parent']['pid']==2562993 and normalized['parent_birth']==parent['parent']['birth']==110549500,'exact measured outer parent raw and normalized projection')
 need(parent['child']['pid']==value['cleanup_actor']['pid']and parent['child']['birth']==value['cleanup_actor']['birth']and parent['returncode']==parent['wait4_status']==0 and parent['positive_wait4_join']is True and parent['streams_closed']is True and parent['process_group_absent']is True and not parent['remaining_group_members']and not parent['group_observation_errors'],'positive119 child directwait/group/streams; no inherited parent-group claim')
 actors=list(b['prior_actors'])+list(b['new_known_actors'])
 for row in retired:
  row=dict(row);row['role']=row['role'].replace('CURRENT118','CURRENT119');actors.append(row)
 actors.append(dict(pid=parent['parent']['pid'],start=parent['parent']['birth'],role='CURRENT119_retirement_outer_parent',group=None,fd=None))
 need(len(b['prior_actors'])==168 and len(b['new_known_actors'])==2 and len(receipts)==14 and len(actors)==PINS['known_actor_count']==186,'exact168+2+owner+14clients+outerparent known frontier')
 need(sum(a['pid']==2562993 for a in actors)==1 and actors[-1]['group']is None,'outer parent once with unclaimed inherited group')
 artifact=checked(PINS['artifact_acceptance']);evidence=checked(PINS['artifact_evidence'])
 need(artifact['decision']=='PASS_INDEPENDENT_ACTUAL_CURRENT119_SELECTED_DEFAULT_ARTIFACT_SOURCE_ABI_LINK_AND_CURRENT_CONSUMERS'and artifact['independent']is True and artifact['implementation_ownership']is False and artifact['artifact_acceptance']is True and artifact['native_acceptance']is False,'exact119 independently qualified artifact scope, no native acceptance')
 need(evidence['actual_image']==PINS['image']and PINS['image']['sha256']=='759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31','genuine119 image, no118rejection relabel')
 return executor,b,actors,receipts

def source_subjects():
 result=dict(observer=ref(__file__),inputs=ref(HERE/'INPUTS.json'))
 for key,value in PINS.items():
  if type(value)is dict and set(value)=={'path','bytes','sha256'}:auth(value);result[key]=value
 result.update({'inherited:'+key:value for key,value in BASE.source_subjects().items()})
 return result

def capture_scope():
 return dict(schema='mckernel.current119.complete-postjoin-readonly-scope.v1',inherited_source=PINS['base_source'],prebuild_historical_Root65_bindings=PINS['base_bindings'],inherited_scope=BASE.capture_scope(),new_operation=PINS['operation'],new_tracked_commands=3,new_command_order=['exact119CIDabsence','exact119nameabsence','fullnormalcensus'],new_known_actor_count=186,all_original_physical_algorithms=True,automatic_retries=0,signals_or_cleanup=False,old_client_UNKNOWN_preserved=True)

def runtime_dependencies(binding):
 need(binding['author']=='/root'and binding['decision']=='BIND_EXACT_CURRENT119_POSTJOIN_OBSERVER'and binding['phase']=='postjoin_candidate'and binding['runtime_authority']is None and binding['ledger']==PINS['ledger'],'Root-only exact pending119 observer binding')
 config=checked(binding['guard_configuration']);review=checked(binding['independent_review']);subjects=source_subjects()
 need(config['schema']=='mckernel.sealed-operation-guard-adapter-config.v1'and config['operation']==PINS['operation']and config['shared_guard']==PINS['shared_guard']and config['subjects']==subjects,'exact new readonly operation source closure')
 need(review['decision']=='PASS_EXACT_CURRENT119_POSTJOIN_OBSERVER_DEPENDENCIES'and review['independent']is True and review['implementation_ownership']is False and review['observer']==ref(__file__)and review['inputs']==ref(HERE/'INPUTS.json')and review['source_subjects']==subjects and review['capture_scope']==capture_scope()and review['ledger']==PINS['ledger']and review['guard_configuration']==binding['guard_configuration'],'independent complete119/recursive dependency review')
 guard=load(PINS['guard_adapter'],'exact_current119_readonly_adapter');guard.configure(binding['guard_configuration']);return guard

def validate_candidate(value):
 executor,b,actors,retirement=validate_metadata()
 need(value['status']==STATUS and value['Root67']==PINS['ledger']and value['current119_retirement_result']==PINS['retirement_result']and value['current119_artifact_acceptance']==PINS['artifact_acceptance']and value['all_recorded_actors_absent']==actors,'exact own119 current candidate, retained historical metadata stays separate')
 need(value['current_free_candidate']is True and value['independent_acceptance']is False and value['native_acceptance']is False and value['runtime_authority']is None,'candidate never self-accepted free/native authority')
 records=BASE.load(BASE.PINS['base_source'],'unchanged_command_receipt_validator').validate_recorded_clients(value['current119_command_receipts']);need(len(records)==3,'three new readonly command receipts')
 expected=[PREFIX+['ps','-aq','--no-trunc','--filter','id='+b['cid']],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+b['name']+'$']]
 for row,argv in zip(records[:2],expected):need(row['argv']==argv and auth(row['raw']['stdout']).read_bytes()==auth(row['raw']['stderr']).read_bytes()==b'','new exact119 CID/name absence bytes')
 historical=value['historical_pre119_Root65_reobservation']
 prior_binding=checked(PINS['base_bindings']);prior_retained=BASE.validate_retained();BASE.attach_custody(prior_binding,prior_retained);previous=BASE.validate_current_adoption(prior_binding,prior_retained)
 _,prior_receipts,prior_retired=BASE.validate_retirement(prior_retained,prior_binding['retirement_result'],prior_binding['retirement_parent_join'])
 expected_prior_actors=prior_retained['actors']+prior_retired+[BASE.actor(previous['observer_self'],'accepted_Root64_capture')]+[BASE.actor(dict(r,group=r['pid']),'accepted_Root64_query_client')for r in previous['query_clients']]
 need(historical['all_recorded_actors_absent']==expected_prior_actors,'exact inherited reobservation actor closure')
 BASE.validate_new_commands(historical,prior_retained,prior_receipts,expected_prior_actors)
 normal=load(b['normal'],'unchanged_normal_census_consumer');prior_pids=[r['pid']for r in retirement+records[:2]]+[a['pid']for a in actors]+[r['pid']for r in historical['query_clients']];caller=value['observer_self'];code=executor.process_source(normal,checked(b['packet']),b,prior_pids)
 row=records[2];argv=row['argv'];need(len(argv)==10 and argv[:7]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code]and re.fullmatch('[0-9a-f]{32}',argv[7])and argv[8:]==[str(caller['pid']),str(caller['birth'])],'exact full119census source/challenge/caller')
 report=executor.strict(auth(row['raw']['stdout']).read_bytes());need(report==value['current119_process_report'],'same raw full report');executor.validate_process(report,normal,b,argv[7],[caller['pid'],str(caller['birth'])],prior_pids)
 recursive=historical['historical_Root63_reobservation'];runtime=load(BASE.PINS['runtime_base_source'],'unchanged_full_physical_consumer')
 runtime.validate_fresh_physical(recursive['historical_Root61_reobservation'],actors,recursive['BFD_exact_absence_queries'],recursive['observed_clocks'],recursive['last_observed_clocks'],recursive['fixed_cutoffs'])
 historical_retained=BASE.validate_retained();load(BASE.PINS['live_frontier_core'],'unchanged_closed_unlaunched_consumer').validate_fresh_closed_unlaunched(recursive,historical_retained['frontier'],historical_retained['base'])
 BASE.validate_absence_reports(historical['historical_Root63_reobservation']['complete_process_reports']+historical['current118_complete_process_reports']+[report],actors)
 first=value['observed_clocks'];last=value['last_observed_clocks'];limits=value['fixed_cutoffs'];need(len(first)==len(last)==len(limits)==3 and all(type(x)in(int,float)and math.isfinite(x)for x in first+last+limits)and all(0<=a<=z<c<=m for a,z,c,m in zip(first,last,limits,PINS['limits']))and 0<=last[1]-first[1]<=120,'actualQ finite tighter current clocks,120s original capture bound')
 return records

def observe(binding,out):
 executor,b,actors,retirement=validate_metadata();guard=runtime_dependencies(binding);first=guard.guard()
 # Invoke the original accepted physical/61→60→common chain unchanged, at its
 # existing accepted pre119 scope. Its prior free is never relabeled post119.
 historical=BASE.observe(checked(PINS['base_bindings']),out)
 cls,_=executor.transport(b);commands=cls(out,executor.Stop())
 def before_popen(argv):
  guard.guard();limits=tuple(guard.current_cutoffs());now=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME));need(all(0<a<c<=m for a,c,m in zip(now,limits,PINS['limits']))and 0<=now[1]-first[1]<120,'direct current caps before Popen, no following I/O')
 commands.before_popen=before_popen
 for argv in [PREFIX+['ps','-aq','--no-trunc','--filter','id='+b['cid']],PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+b['name']+'$']]:
  response=commands.exact(argv,30);need(response.stdout==response.stderr=='','fresh119CID/name absent')
 normal=load(b['normal'],'unchanged119normalcensus');primitive=load(b['primitive'],'unchanged119birth');caller=[os.getpid(),primitive.proc_stat(os.getpid())[19]];challenge=uuid.uuid4().hex
 records=BASE.load(BASE.PINS['base_source'],'existing_command_records').command_records(commands);prior_pids=[r['pid']for r in retirement+records]+[a['pid']for a in actors]+[r['pid']for r in historical['query_clients']]
 code=executor.process_source(normal,checked(b['packet']),b,prior_pids);response=commands.exact(['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,challenge,str(caller[0]),caller[1]],30);report=executor.strict(response.stdout);executor.validate_process(report,normal,b,challenge,caller,prior_pids)
 recursive=historical['historical_Root63_reobservation'];runtime=load(BASE.PINS['runtime_base_source'],'unchanged_full_physical_consumer')
 runtime.validate_fresh_physical(recursive['historical_Root61_reobservation'],actors,recursive['BFD_exact_absence_queries'],recursive['observed_clocks'],recursive['last_observed_clocks'],recursive['fixed_cutoffs'])
 historical_retained=BASE.validate_retained();load(BASE.PINS['live_frontier_core'],'unchanged_closed_unlaunched_consumer').validate_fresh_closed_unlaunched(recursive,historical_retained['frontier'],historical_retained['base'])
 BASE.validate_absence_reports(historical['historical_Root63_reobservation']['complete_process_reports']+historical['current118_complete_process_reports']+[report],actors)
 for actor in actors:
  need(not Path('/proc',str(actor['pid'])).exists(),'fresh every119/historical PID absent')
  if actor.get('fd')is not None:need(not Path('/proc',str(actor['pid']),'fd',str(actor['fd'])).exists(),'fresh own holder/cleanup FD absent')
 need(not any(len(v)>=8 and v[5]=='00:1b:4'for v in (line.split()for line in Path('/proc/locks').read_text().splitlines())),'permanent27:4 has no holder')
 last=guard.guard();limits=list(guard.current_cutoffs());value=dict(status=STATUS,Root67=PINS['ledger'],current119_retirement_result=PINS['retirement_result'],current119_artifact_acceptance=PINS['artifact_acceptance'],historical_pre119_Root65_reobservation=historical,all_recorded_actors_absent=actors,current119_command_receipts=commands.receipts,current119_process_report=report,observer_self=dict(pid=caller[0],birth=int(caller[1]),group=os.getpgrp()),observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=limits,boot_id=BOOT,current_free_candidate=True,independent_acceptance=False,native_acceptance=False,runtime_authority=None,unmeasured_actor_gaps=b['actor_gaps'],old_readonly_client_status='UNKNOWN',complete_recursive_capture_scope=capture_scope(),fresh_PID_FD_lock_absence=True)
 validate_candidate(value);return value

def main():
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
 for key in ('bindings','release','output'):parser.add_argument('--'+key,type=Path,required=True)
 parser.add_argument('--release-sha256',required=True);args=parser.parse_args();release_ref=ref(args.release);need(release_ref['sha256']==args.release_sha256,'exact release SHA');release=checked(release_ref)
 need(release['author']=='/root'and release['decision']=='AUTHORIZE_ONE_CURRENT119_POSTJOIN_READONLY_CAPTURE'and release['maximum_invocations']==1 and release['source']==ref(__file__)and release['inputs']==ref(HERE/'INPUTS.json')and release['bindings']==ref(args.bindings)and release['output']==str(args.output)and release['capture_scope']==capture_scope()and release['execution_profile']==PROFILE,'one complete exact source/profile/output readonly capture')
 review=checked(release['independent_execution_review']);need(review['decision']=='PASS_EXACT_CURRENT119_READONLY_CAPTURE'and review['independent']is True and review['implementation_ownership']is False and review['release_payload']=={k:v for k,v in release.items()if k!='independent_execution_review'},'independent exact capture release review')
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}and 0<resource.getrlimit(resource.RLIMIT_AS)[0]<=2<<30 and 0<resource.getrlimit(resource.RLIMIT_CPU)[0]<=60,'same reviewed ordinary profile');out=args.output.parent;need(out.parent==HERE and out.name.startswith('actual-postjoin-capture-')and not out.exists(),'fresh confined output');out.mkdir(mode=0o700)
 with args.output.open('x')as stream:
  try:value=observe(checked(ref(args.bindings)),out)
  except BaseException as error:stream.write(json.dumps(dict(status='READONLY_CURRENT119_CAPTURE_FAILED_NO_RETRY',error=repr(error),runtime_authority=None))+'\n');raise
  stream.write(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(status=STATUS,output=ref(args.output),current_free=False)))
if __name__=='__main__':main()
