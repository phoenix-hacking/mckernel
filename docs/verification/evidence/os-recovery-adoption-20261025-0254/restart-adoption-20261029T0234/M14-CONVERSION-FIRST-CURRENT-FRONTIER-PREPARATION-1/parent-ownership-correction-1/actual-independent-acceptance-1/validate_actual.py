"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained actual receipt readers. No guard/proc/capture/native calls.
"""
from pathlib import Path
import json,hashlib,importlib.util,ast
D=Path(__file__).resolve().parent;P=D.parent

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def load(p,name):
 sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
q=read(P/'actual-frontier-1/OBSERVATION.json');j=read(P/'actual-frontier-parent-1/DIRECT-PARENT-JOIN.ACTUAL.json');c=read(P/'ROOT-CALLER-CLOSURE.ACTUAL.json')
assert ref(P/'actual-frontier-1/OBSERVATION.json')['sha256']=='17e56c76c12133a996aaaa24d82f5a30b4fcc3df91f0b6dce7d977800e103dc8'
assert ref(P/'actual-frontier-parent-1/DIRECT-PARENT-JOIN.ACTUAL.json')['sha256']=='1d7a4fa6881b0fd6642980f842b869b34c3b19a55b171be74074d7673599d1f1'
assert ref(P/'ROOT-CALLER-CLOSURE.ACTUAL.json')['sha256'].startswith('abbef0c4')
assert j['parent_source']==ref(P/'root_capture_parent.py') and j['parent_source']['sha256'].startswith('7652d825')
assert j['evidence_error']is None and j['returncode']==j['wait4_status']==0 and j['wait4_pid']==j['child']['pid']==2618883 and j['child']['birth']==111481329 and j['child']['ppid']==j['parent']['pid']==2618882 and j['parent']['birth']==111481325
assert j['child']['pgrp']==j['child']['sid']==j['child']['pid'] and j['positive_wait4_join']is j['positive_direct_wait_join']is j['streams_closed']is j['process_group_absent']is True and not j['remaining_group_members']and not j['group_observation_errors']and j['signals_sent']==0
assert auth(j['stderr']).read_bytes()==b'';parentout=json.loads(auth(j['stdout']).read_bytes());assert parentout['output']==ref(P/'actual-frontier-1/OBSERVATION.json')and parentout['current_free']is False
release=read(auth(j['release']));er=read(auth(release['independent_execution_review']));assert er['release_payload']=={k:v for k,v in release.items()if k!='independent_execution_review'}and er['decision']=='PASS_EXACT_CONVERSION_FRONTIER_READONLY_CAPTURE'and er['independent']is True and er['implementation_ownership']is False
assert release['source']==ref(P/'observe_conversion_frontier.py')and release['maximum_invocations']==1 and release['runtime_authority']is release['native_authority']is None
assert j['argv']==[x if x!='EXACT_FINAL_RELEASE_SHA256_FROM_AUTHENTICATED_BYTES'else j['release']['sha256']for x in er['exact_child_argv_with_final_release_hash_placeholder']]
o=load(P/'observe_conversion_frontier.py','independent_actual_observer');checker=o.load(o.CHECKER,'independent_actual_checker');base=checker.BASE.load(checker.BASE.PINS['base_source'],'independent_actual_raw_readers');rows=base.validate_recorded_clients(q['current119_query_command_receipts']);assert len(rows)==3
executor=checker.load(checker.PINS['executor'],'independent_actual_normal');b=executor.bindings();normal=checker.load(b['normal'],'independent_actual_census')
assert rows[0]['argv']==checker.PREFIX+['ps','-aq','--no-trunc','--filter','id='+b['cid']]and rows[1]['argv']==checker.PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+b['name']+'$']
for r in rows:
 assert r['returncode']==r['wait4_status']==0 and r['positive_wait4']is r['streams_closed']is r['group_absent']is True and not r['group_members']and r['signals_sent']==0 and r['client_retirement_unproven']is False
 assert auth(r['raw']['stderr']).read_bytes()==b''
for r in rows[:2]:assert auth(r['raw']['stdout']).read_bytes()==b''
report=read(auth(rows[2]['raw']['stdout']));assert report==q['current119_complete_process_report'];caller=[2618883,'111481329'];assert report['caller']==caller and rows[2]['argv'][-3:]==[report['challenge'],str(caller[0]),caller[1]]
oldfree=read(auth(q['historical_current119_free']));stage=read(auth(q['post_root68_custody_supplement']));r1=read(auth(q['post_root68_resource1_custody_supplement']));actors=oldfree['next_full_postjoin_actor_frontier']+stage['additional_measured_actors']+r1['additional_measured_actors'];assert actors==q['all_recorded_actors_absent']and len(actors)==207 and len({(a['pid'],a['start'])for a in actors})==202
# All prior raw-census obligations, using retained actual report only.
prior=[a['pid']for a in actors]+[rows[0]['pid'],rows[1]['pid']];executor.validate_process(report,normal,b,report['challenge'],caller,prior);checker.BASE.validate_absence_reports([report],actors)
assert q['query_clients']==[dict(pid=r['pid'],birth=r['birth'])for r in rows]and q['observer_self']==dict(pid=2618883,birth=111481329,group=2618883)
assert q['unmeasured_resource1']==r1['unmeasured']and q['unmeasured_resource1_limitations']==r1['unmeasured_limitations']and q['unmeasured_post_root68_outer_tool_actor']==stage['unmeasured_outer_tool_actor']and q['old_readonly_client_status']=='UNKNOWN'
assert q['no_existing_heavy']is q['active_shared_records_absent']is True and q['pids_current']==0 and len(q['closed_exclusive_probes'])==2
assert q['capacity']['/home/holden/mckernel']>=16*2**30 and q['capacity']['/home/holden/mckernel-work/scratch']>=12*2**30 and q['memory']['MemAvailable']>=24*2**30
assert q['cgroup']=={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us':'100000','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us':'400000','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes':'12884901888','/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy':'1','/sys/fs/cgroup/pids/mckernel-dev/pids.max':'512'}
run=q['running_container_observation'];assert run['returncode']==0 and run['stdout']==run['stderr']==''and run['positive_wait']is True
stopped=q['retained_stopped_observation'];assert stopped['returncode']==0 and stopped['stderr']==''and stopped['positive_wait']is True;retained=json.loads(stopped['stdout']);assert len(retained)==1 and retained[0]['State']['Running']is False and retained[0]['State']['Pid']==0 and retained[0]['State']['Status']=='exited'
census=q['group_membership_observation'];assert not census['errors']
for a in actors:assert not any(r['pid']==a['pid']or(a.get('group')is not None and r['pgrp']==a['group'])for r in census['rows'])
limits=(1793774133,1556235.568922472,1571573.6959699572);assert tuple(q['fixed_cutoffs'])==limits and all(0<=a<=z<lim for a,z,lim in zip(q['observed_clocks'],q['last_observed_clocks'],limits))and q['last_observed_clocks'][1]-q['observed_clocks'][1]<120
assert q['native_acceptance']is False and q['runtime_authority']is None and q['current_free_candidate']is True and q['independent_acceptance']is False and q['current_physical_clearance_pending']is True
added=[dict(pid=j['parent']['pid'],start=j['parent']['birth'],role='conversion_frontier_capture_outer_parent',group=j['parent']['pgrp'],fd=None),dict(pid=j['child']['pid'],start=j['child']['birth'],role='conversion_frontier_capture_observer',group=j['child']['pgrp'],fd=None)]+[dict(pid=r['pid'],start=r['birth'],role='conversion_frontier_capture_query_client',group=r['process_group'],fd=None)for r in rows]
expected={(a['pid'],a['start'])for a in added};assert len(expected)==5 and not expected&{(a['pid'],a['start'])for a in actors}
assert c['raw_parent_join']==ref(P/'actual-frontier-parent-1/DIRECT-PARENT-JOIN.ACTUAL.json')and c['raw_observation']==ref(P/'actual-frontier-1/OBSERVATION.json')and c['tool_session']==16628 and c['tool_terminal_returncode']==0 and c['signals_sent']==0 and c['all_exact_identities_absent']is True and c['runtime_authority']is None
assert {(a['pid'],a['birth'])for a in c['measured_current_identity_checks']}==expected and len(c['measured_current_identity_checks'])==5 and all(a['exact_identity_absent']is True and a['current_birth']is None and a['state']=='PID_ABSENT'for a in c['measured_current_identity_checks'])
assert c['old_readonly_client_status']==c['unmeasured_source_tool_identities']=='UNKNOWN'
frontier=actors+added;assert len(frontier)==212 and len({(a['pid'],a['start'])for a in frontier})==207
result=dict(status='PASS_ACTUAL_READONLY_CAPTURE_RAW_THREE_QUERY_JOINS_CENSUS_PHYSICAL_AND_ROOT_CALLER_CLOSURE',actual_observation=ref(P/'actual-frontier-1/OBSERVATION.json'),actual_parent_join=ref(P/'actual-frontier-parent-1/DIRECT-PARENT-JOIN.ACTUAL.json'),actual_caller_closure=ref(P/'ROOT-CALLER-CLOSURE.ACTUAL.json'),query_receipts=q['current119_query_command_receipts'],query_clients=q['query_clients'],additional_measured_actors=added,next_full_actor_frontier=frontier,retained_actor_rows=207,retained_distinct_identities=202,actor_rows=212,distinct_identities=207,retained_duplicates=5,UNKNOWN_preserved=True,actual_guard_calls=0,actual_capture_calls=0,actual_proc_reads=0)
(D/'CHECKS.ACTUAL.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
