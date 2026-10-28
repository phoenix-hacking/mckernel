"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent BFD cold/prewarm→Hot finite protocol; Root must not invoke approver.
"""
from pathlib import Path
import argparse,importlib.util,json,os,re,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from handoff_common import *
D=Path(__file__).resolve().parent

def load(r,n):
 p=verify_ref(r);s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def cold(b,H):
 need(b['reviewer']==REVIEWER and b['Root_must_not_execute_approver'] is True,'assigned independent verifier')
 A=Path(b['admission']);need(A.is_absolute() and A.is_dir() and H.is_absolute() and H.is_dir(),'actual admission/handoff');no_launch(A)
 need(re.fullmatch('[a-f0-9]{32}',b['nonce']) is not None,'Root supplied unused exact nonce')
 refs=b['static_refs']
 for r in refs.values():verify_ref(r)
 frozen=read_json(D/'FROZEN-COHORT-PINS.json')
 for k in ['profile','runner','worker','holder_source','input_export','request_payload']:need(refs[k]==frozen[k],'unchanged actual emitted cohort '+k)
 p=read_json_ref(refs['profile']);request=read_json_ref(refs['request_payload']);export=read_json_ref(refs['input_export']);contract=read_json_ref(b['contract']);frag=contract['Root61_observer_fragment']
 need(p['runtime_authority'] is None and len(p['exact_commands'])==3 and p['CPU']=='2-5' and p['memory_bytes']==12<<30 and p['pids']==512 and p['fixed_three_clock_cutoffs']==CUTOFFS,'exact BFD three-command unchanged profile')
 need(p['request_sha256']==refs['request_payload']['sha256']==export['request_sha256'],'exact actual request/export')
 need(p['actual_root_ledger']==frag['current_ledger'] and p['native_custody_clearance']==frag['latest_free'],'exact actual Root61/free6c83')
 schema=read_json_ref(b['observer_schema']);schema_review=read_json_ref(b['observer_schema_review'])
 need(schema['schema_version']=='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1' and schema['observer']==b['observer_source'] and schema['ledger_key']=='Root61' and schema['expected_status']=='PASS_Root61_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE' and schema['current_boundary_key']=='current_boundary' and schema['latest_free_key']=='actual_latest_operation_postjoin_acceptance','exact35d5 unchanged BFD consumer field contract')
 need(schema_review['independent'] is True and schema_review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and schema_review['reviewed_observer_schema']==b['observer_schema'],'actual independent BFD schema source review')
 ledger=read_json_ref(frag['current_ledger']);need(ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and ledger['current_physical_clearance_pending'] is False and b['nonce'] not in ledger['consumed_nonces'],'Root complete unused nonce/currentfree')
 typed=load(frag['current_observer_source'],'reviewed35d5_retained_only');typed.validate_current(typed.CURRENT)
 r=load(refs['runner'],'actual_BFD_cold_runner');r.current_operation_guard();need(r.commands_for_plan(p)==p['exact_commands'],'actual exact3argv');r.verify_bfd_source_export(p)
 need(export['source_export_plan']==p['inputs']['source_export_plan'] and export['source_adoption']==p['actual_source_adoption'] and export['SDK21_recompiled'] is False,'actual accepted readonly source/export prefixes')
 for row in p['inputs']['qualified_readonly_files']:verify_ref(row)
 pub=read_json_ref(b['source_publication']);need(pub['runtime_authority'] is None and pub['status'].startswith('PASS_FETCHED') and re.fullmatch('[a-f0-9]{40}',pub['commit']) is not None,'actual fetched publication')
 for row in pub['rows']:verify_ref(row['actual'])
 published={row['actual']['path'] for row in pub['rows']}
 for row in list(refs.values())+[b['observer_source'],b['guard_facade'],b['guard_configuration'],b['finite_verifier'],b['capture_source'],b['publisher_source']]:need(row['path'] in published,'actual fetched source closure '+row['path'])
 need(b['authorized_cutoffs']==CUTOFFS,'exact all-controls minima');in_window(clocks(),CUTOFFS)
 ready=dict(scope=SCOPE,status='INDEPENDENT_PREWARM_READY_STATIC_CLOSURE_COMPLETE_NOT_EXECUTION_PASS',reviewer=REVIEWER,pid=os.getpid(),starttime=birth(os.getpid()),bindings=reference(Path(b['_bindings'])),verifier=reference(__file__),nonce=b['nonce'],admission=str(A),cold_profile=refs['profile'],cold_export=refs['input_export'],source_publication=b['source_publication'],earliest_clamps=CUTOFFS,actual_resource_authority=None)
 rr=atomic_json(H/'PREWARM_READY.json',ready)
 return dict(b=b,A=A,H=H,p=p,runner=r,ready_ref=rr,limits=CUTOFFS)

def hot(c,marker):
 b,A,H,p,r=c['b'],c['A'],c['H'],c['p'],c['runner'];no_launch(A)
 need(marker['status']=='ROOT_HELD_CAPTURE_COMPLETE_ZERO_POSITIVE_JOIN' and marker['returncode']==0 and marker['direct_child_joined'] is True and marker['group_absent'] is True and marker['closed_streams'] is True,'owned CPU0 capture positively joined')
 need(marker['prewarm_ready']==c['ready_ref'] and marker['nonce']==b['nonce'] and marker['admission']==str(A) and marker['capture_source']==b['capture_source'],'exact prewarm/capture chain')
 pending=read_json_ref(marker['pending_input']);resource=read_json_ref(marker['resource']);physical=read_json_ref(marker['physical']);inputs=read_json_ref(marker['root_resource_input']);ready=read_json_ref(marker['holder_ready']);bootstrap=read_json_ref(marker['holder_bootstrap']);inputs['_input_ref']=marker['root_resource_input']
 need(pending['review'] is None and pending['resource_authority']==marker['resource'],'pending exact resource before actual approval')
 producer=load(b['capture_source'],'BFD_genuine_capture_producer')
 observed=resource['actual_observations'];need(observed['capture_profile']==dict(affinity=[0],AS_bytes=2<<30,CPU_seconds=60),'actual capture enforced profile')
 expected,grant=producer.held_values(b,inputs,physical,ready,bootstrap,observed,resource['observed_clocks']);grant['resource_authority']=marker['resource']
 need(expected==resource and grant==pending,'full actual producer→resource/pending record equality, not key subsets')
 need(resource['reservation_holder']==ready['holder'] and inputs['holder_ready']==marker['holder_ready'] and inputs['holder_bootstrap']==marker['holder_bootstrap'],'same original held owner')
 h=ready['holder'];need(birth(h['pid'])==h['starttime'],'Hot actual holder birth');z=(Path('/proc')/str(h['pid'])/'fd/3').stat();need((z.st_dev,z.st_ino)==(27,4),'Hot actual FD3')
 locks=Path('/proc/locks').read_text();owners=[v for v in (s.split() for s in locks.splitlines()) if len(v)>=8 and v[5]=='00:1b:4'];need(len(owners)==1 and owners[0][1:5]==['FLOCK','ADVISORY','WRITE',str(h['pid'])] and owners[0][6:8]==['0','EOF'],'Hot sole actual fullEOF holder')
 now=r.current_operation_guard();in_window(now,CUTOFFS)
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 r.resource_guards(p,pending,dict(decision='PASS_EXACT_BUILD_ONLY_EXECUTION',independent=True,reviewer=REVIEWER,nonce=b['nonce'],coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY'),resource,now[0],mem,int(Path('/proc/loadavg').read_text().split()[3].split('/')[1]),int(Path('/proc/sys/kernel/threads-max').read_text()),locks,h['starttime'])
 final=r.current_operation_guard();in_window(final,CUTOFFS);need(0<=final[0]-resource['observed_at_epoch']<=120,'FINAL120s')
 no_launch(A)
 return dict(scope=SCOPE,decision='PASS_EXACT_BUILD_ONLY_EXECUTION',independent=True,implementation_ownership=False,maximum_invocations=1,reviewer=REVIEWER,nonce=b['nonce'],payload_sha256=marker['pending_input']['sha256'],approved_input_sha256=marker['pending_input']['sha256'],pending_input=marker['pending_input'],resource_authority=marker['resource'],prewarm_ready=c['ready_ref'],complete_root_capture=reference(H/'ROOT-HELD-CAPTURE.COMPLETE.json'),final_clocks=final,earliest_clamps=CUTOFFS,resource_age_seconds=final[0]-resource['observed_at_epoch'],resource_observed_at_epoch=resource['observed_at_epoch'],verifier=reference(__file__),runtime_authority=None)

def publish_pass(c,result):
 def postfsync():
  verify_ref(result['pending_input']);value=read_json_ref(result['resource_authority']);no_launch(c['A']);now=c['runner'].current_operation_guard();in_window(now,result['earliest_clamps']);need(0<=now[0]-value['observed_at_epoch']<=120,'postfsync original120s')
 result.update(publication_freshness_enforced_by_postfsync_callback=True,receipt_clocks_are_pre_serialization=True)
 return atomic_json(c['H']/'INDEPENDENT-FINITE-REVIEW.PASS.json',result,before_publish=postfsync)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--independent-reviewer',required=True);p.add_argument('--bindings',required=True);p.add_argument('--handoff',required=True);a=p.parse_args();need(a.independent_reviewer==REVIEWER,'Root must not invoke assigned independent approver');b=read_json(a.bindings);b['_bindings']=a.bindings;c=cold(b,Path(a.handoff));end=time.monotonic()+600
 while not (c['H']/'ROOT-HELD-CAPTURE.COMPLETE.json').exists():
  need(time.monotonic()<end,'finite waiter, no automatic replay');in_window(clocks(),c['limits']);time.sleep(.05)
 result=hot(c,read_json(c['H']/'ROOT-HELD-CAPTURE.COMPLETE.json'));print(json.dumps(dict(decision=result['decision'],reference=publish_pass(c,result))))
if __name__=='__main__':main()
