"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unbound fresh pre-holder Resource2 observer using accepted actual CURRENT119 history.
"""
from pathlib import Path
import hashlib,importlib.util,json,math,os,time,uuid
HERE=Path(__file__).resolve().parent
BINDING=HERE/'ROOT-ACTUAL-RESOURCE-OBSERVER-BINDING.json'
CHECKER={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/observe_current67_current119_postjoin.py','bytes':17647,'sha256':'5e9090daf0ada1cda26d5d0bdc6bc695964ae1113a620785427b9dac9a452859'}
CAPTURE={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-postjoin-capture-current119-root1/CAPTURE.json','bytes':25678630,'sha256':'b80a78a7d4835b149198230e5a979e5deeb23e383711b746a7372c8f117758b7'}
PARENT={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-postjoin-parent-root1/DIRECT-PARENT-JOIN.ACTUAL.json','bytes':3100,'sha256':'4cf360feb8a87c9565e763db047f388f0828f7a017b73ea57b0c4f15e91200eb'}
ACCEPTED_FREE={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-acceptance-1/CURRENT-FREE.ACTUAL.json','bytes':49224,'sha256':'3fd1a6facf34a9e6ac9259526da96ddee2dd22c6032ee47b37be97e56d0086e3'}
PHYSICAL={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-physical-history-successor-source-20261028-1/physical_history_successor.py','bytes':9521,'sha256':'af7cfd5a37a56672205ef0bc133d0c679aa5a7103450cf73ff1ba4f50479ca87'}
GUARD={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/CURRENT119-NATIVE-WEEKLY-GUARD-1/native_operation_guard.py','bytes':11333,'sha256':'1f89fba32c016346cec9f11ae96fe1e4b0c5e781c307c34bda646ab7c05f92e4'}
LIMITS=(1793774133,1556235.568922472,1571573.6959699572)
def need(v,why):
 if not v:raise ValueError(why)
def ref(p):
 p=Path(p);need(p.is_absolute() and not p.is_symlink() and p.is_file(),'absolute byte source');b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'} and ref(r['path'])==r,'exact byte reference');return Path(r['path'])
def read(r):return json.loads(auth(r).read_bytes())
def load(r,n):
 spec=importlib.util.spec_from_file_location(n,auth(r));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def frontier(checker,free,capture,parent):
 _,_,actors,_=checker.validate_metadata() # pure metadata, never validate_candidate
 need(capture['status']==checker.STATUS and capture['Root67']==checker.PINS['ledger'] and capture['all_recorded_actors_absent']==actors and capture['current_free_candidate'] is True and capture['independent_acceptance'] is False and capture['old_readonly_client_status']=='UNKNOWN','actual pending capture and exact prior frontier')
 need(free['schema']=='mckernel.independent-root67-current119-postjoin-current-free.v1' and free['decision']=='PASS_ROOT67_CURRENT119_POSTJOIN_CURRENT_FREE' and free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True and free['Root67']==checker.PINS['ledger'] and free['actual_postjoin_observation']==CAPTURE and free['capture_positive_join']==PARENT and free['old_readonly_client_status']=='UNKNOWN','actual independent post119 free binds exact pending capture and parent')
 need(parent['author']=='/root' and (parent['parent']['pid'],parent['parent']['birth'],parent['parent']['pgrp'])==(2569587,110664396,2569587) and (parent['child']['pid'],parent['child']['birth'],parent['child']['pgrp'])==(2569588,110664400,2569588) and parent['child']['ppid']==2569587 and parent['returncode']==parent['wait4_status']==0 and parent['positive_wait4_join'] is True and parent['positive_direct_wait_join'] is True and parent['streams_closed'] is True and parent['process_group_absent'] is True and not parent['remaining_group_members'] and not parent['group_observation_errors'] and parent['signals_sent']==0,'exact actual parent/observer positive join; no parent-group absence claim')
 need(capture['observer_self']==dict(pid=2569588,birth=110664400,group=2569588),'exact actual observer identity')
 base=checker.BASE;old=capture['historical_pre119_Root65_reobservation'];legacy=base.load(base.PINS['base_source'],'pure_retained_recorded_clients')
 oldrows=legacy.validate_capture_commands(old['historical_Root63_reobservation'])+legacy.validate_recorded_clients(old['current118_query_command_receipts'])
 newrows=legacy.validate_recorded_clients(capture['current119_command_receipts']);rows=oldrows+newrows
 need(len(rows)==11 and len({x['pid']for x in rows})==11 and old['query_clients']==[dict(pid=x['pid'],birth=x['birth']) for x in oldrows],'all exact 8+3 raw joined clients')
 result=list(actors)+[dict(pid=x['pid'],start=x['birth'],role='CURRENT119_accepted_query_client',group=x['pid'],fd=None)for x in rows]+[dict(pid=2569588,start=110664400,role='CURRENT119_accepted_capture_observer',group=2569588,fd=None),dict(pid=2569587,start=110664396,role='CURRENT119_accepted_capture_outer_parent',group=None,fd=None)]
 need(free['reviewed_observer']==CHECKER and free['recorded_actor_count']==186 and free['query_client_count']==11 and free['next_full_actor_count']==199 and free['next_distinct_actor_identities']==194 and free['consumed_nonce_count']==73 and free['native_acceptance'] is False and free['artifact_acceptance'] is True and free['runtime_authority'] is None,'actual accepted scope, 73 nonce, artifact only')
 need(free['query_clients']==[dict(pid=x['pid'],birth=x['birth'],group=x['pid'])for x in rows] and free['next_full_postjoin_actor_frontier']==result,'accepted exact preserved actor multiset and client identities')
 need(len(result)==199 and len({(x['pid'],x['start'])for x in result})==194 and len({(x['pid'],x['start'])for x in result[186:]})==13 and not {(x['pid'],x['start'])for x in result[:186]} & {(x['pid'],x['start'])for x in result[186:]},'199 retained rows, 194 measured identities; 13 actual new identities; no guessed births')
 return result

def validate_adoption(ledger,boundary,ledger_ref,free_ref,free,actors):
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and ledger['current_physical_clearance_pending'] is False and ledger['latest_accepted_free_boundary']==free_ref and len(ledger['consumed_nonces'])==len(set(ledger['consumed_nonces']))==73,'actual post119 adopted ledger and unchanged73')
 custody=ledger['current119_postjoin_custody']
 need(custody['independent_current_free']==free_ref and custody['capture']==CAPTURE and custody['parent_join']==PARENT and custody['next_full_actor_frontier']==actors and custody['query_clients']==free['query_clients'] and custody['actor_rows']==199 and custody['distinct_identities']==194 and custody['old_readonly_client_status']=='UNKNOWN' and custody['native_acceptance'] is False,'actual Root custody retains exact accepted frontier')
 need(boundary['author']=='/root' and boundary['nonce_ledger']==ledger_ref and boundary['native_custody_clearance']==free_ref and boundary['root_attests_exact_current_boundary'] is True and boundary['retained_actor_rows']==199 and boundary['distinct_actor_identities']==194 and boundary['native_acceptance'] is False,'exact Root68 actual boundary')

def validate_route(binding,context,review):
 need(binding['author']=='/root' and binding['decision']=='BIND_CURRENT119_NATIVE_RESOURCE_OBSERVER' and binding['runtime_authority'] is None and binding['source']==ref(__file__),'Root source-only observer binding')
 for k in ('current_ledger','current_free','current_boundary'):need(binding[k]==context[{'current_free':'post119_current_free'}.get(k,k)],'same exact native operation context '+k)
 need(review['decision']=='PASS_EXACT_CURRENT119_FRESH_RESOURCE_OBSERVER' and review['independent'] is True and review['implementation_ownership'] is False and review['observer']==binding['source'] and review['current_ledger']==binding['current_ledger'] and review['current_free']==binding['current_free'] and review['current_boundary']==binding['current_boundary'] and review['complete_actual_actor_frontier'] is True and review['original_resource_lock_holder_cgroup_checks_preserved'] is True and review['runtime_authority'] is None,'independent exact physical observer review')
 need(review['binding_payload']=={k:v for k,v in binding.items() if k!='independent_review'},'independent complete binding payload')

def observe():
 binding=read(ref(BINDING));guard=load(GUARD,'exact_current119_native_guard_resource');first=guard.guard();_,_,context,_=guard.binding_metadata(guard.read(guard.ref(guard.BINDING)))
 review=read(binding['independent_review']);validate_route(binding,context,review)
 need(binding['current_free']==ACCEPTED_FREE,'exact independently accepted current119 capture, no prior free alias')
 checker=load(CHECKER,'exact_current119_postjoin_source');capture=read(CAPTURE);parent=read(PARENT);free=read(binding['current_free']);actors=frontier(checker,free,capture,parent)
 validate_adoption(read(binding['current_ledger']),read(binding['current_boundary']),binding['current_ledger'],binding['current_free'],free,actors)
 history_binding=read(binding['physical_history_binding'])
 need(history_binding['guard_adapter']==ref(HERE/'native_history_guard.py') and history_binding['guard_config']==guard.ref(guard.BINDING),'exact retained physical history with native Q adapter')
 physical=load(PHYSICAL,'accepted_original_physical_history');physical.configure(binding['physical_history_binding']);historical=physical.observe()
 # Reuse the unchanged normal-retirement transport and full-process predicate.
 executor,b,_,retirement=checker.validate_metadata();out=Path(binding['query_output_directory'])
 need(out.is_absolute() and out.is_dir() and not any(out.iterdir()),'fresh dedicated output directory')
 cls,_=executor.transport(b);commands=cls(out,executor.Stop())
 def before_popen(argv):
  guard.guard();caps=guard.current_cutoffs();now=(time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME))
  need(all(0<a<c<=m for a,c,m in zip(now,caps,LIMITS)) and 0<=now[1]-first[1]<120,'direct live Q caps immediately before each Popen')
 commands.before_popen=before_popen
 for argv in [checker.PREFIX+['ps','-aq','--no-trunc','--filter','id='+b['cid']],checker.PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+b['name']+'$']]:
  response=commands.exact(argv,30);need(response.stdout==response.stderr=='','exact119 CID and name remain absent')
 normal=checker.load(b['normal'],'unchanged119_full_normal_census');primitive=checker.load(b['primitive'],'unchanged119_birth_helper');caller=[os.getpid(),primitive.proc_stat(os.getpid())[19]]
 records=checker.BASE.load(checker.BASE.PINS['base_source'],'unchanged_recorded_clients').command_records(commands)
 prior_pids=[r['pid']for r in retirement+records]+[a['pid']for a in actors];challenge=uuid.uuid4().hex
 code=executor.process_source(normal,checker.checked(b['packet']),b,prior_pids)
 response=commands.exact(['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,challenge,str(caller[0]),caller[1]],30)
 report=executor.strict(response.stdout);executor.validate_process(report,normal,b,challenge,caller,prior_pids);checker.BASE.validate_absence_reports([report],actors)
 records=checker.BASE.load(checker.BASE.PINS['base_source'],'unchanged_resource_client_receipts').command_records(commands)
 need(len(records)==3,'exact three fresh joined query clients')
 census=historical['group_membership_observation'];need(not census['errors'],'complete original group observation')
 for a in actors:
  need(not Path('/proc',str(a['pid'])).exists(),'every measured post119 actor PID absent')
  if a.get('fd') is not None:need(not Path('/proc',str(a['pid']),'fd',str(a['fd'])).exists(),'recorded owner FD absent')
  need(not any(r['pid']==a['pid'] or (a.get('group') is not None and r['pgrp']==a['group']) for r in census['rows']),'measured PID and dedicated group absent')
 need(not any(len(x)>=8 and x[5]=='00:1b:4' for x in (line.split()for line in Path('/proc/locks').read_text().splitlines())),'permanent mutex absent pre-holder')
 need(historical['no_existing_heavy'] is True and historical['active_shared_records_absent'] is True and historical['pids_current']==0 and len(historical['closed_exclusive_probes'])==2,'unchanged full original physical resource checks')
 need(historical['capacity']['/home/holden/mckernel']>=16*2**30 and historical['capacity']['/home/holden/mckernel-work/scratch']>=12*2**30,'original host and scratch floors')
 last=guard.guard();limits=guard.current_cutoffs();need(all(0<=a<=z<c<=m for a,z,c,m in zip(first,last,limits,LIMITS)) and last[1]-first[1]<=120,'same current Q clocks and freshness')
 result=dict(historical);result.update(current_ledger=binding['current_ledger'],current_boundary=binding['current_boundary'],actual_latest_operation_postjoin_acceptance=binding['current_free'],complete_actual_actor_frontier=True,all_recorded_actors_absent=actors,old_readonly_client_status='UNKNOWN',historical_current119_capture=CAPTURE,current119_query_command_receipts=commands.receipts,current119_complete_process_report=report,query_clients=[dict(pid=r['pid'],birth=r['birth'])for r in records],observer_self=dict(pid=caller[0],birth=int(caller[1]),group=os.getpgrp()),observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=list(limits),native_acceptance=False,runtime_authority=None)
 return result
