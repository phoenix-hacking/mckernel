"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact Root51 A3 source observer; unchanged Root49/48 observe() supplies physical history.
Import/validate_retained are data-only; only Root may invoke observe under fresh authority.
"""
from pathlib import Path
import hashlib,importlib.util,json,os
PINS={'ledger': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER51.json', 'bytes': 47673, 'sha256': '80bf0d2a7111fd983755c6dfaafc215c32a6f8a56406ab3a9c414a61ce66621a'}, 'free': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/attempt2-held-only-retirement-source-1/independent-current-free-review-1/CURRENT-FREE.json', 'bytes': 88232, 'sha256': '040b08c75d06794f8599c8a51ac69e7915c9e1d8373f2f794423168fb41ff8c7'}, 'base': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/current49-attempt2-observer-source-1/observe_root49_current115_attempt2.py', 'bytes': 12935, 'sha256': '54500dd1409000807e7f2afcbc39d4198b4f54358f35fc792311657cc976eca8'}, 'base_boundary': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json', 'bytes': 1560, 'sha256': '9065db592e141ab93e5b285777d0185860fcb79cabeb29f675c09eb86f41c943'}, 'retirement': {'abandoned_nonce': '92e8d698cfe12176ddd0375937cbaeb1', 'actual_schema_refusal': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-2/independent-execution-review-1/REVIEW.json', 'bytes': 4174, 'sha256': '6e3ae7a52ef26e54e0d97d541b0f0a45568ba64ba855200a73bfae859398a5c7'}, 'controlled_SIGINT_action': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/attempt2-held-only-retirement-source-1/ACTUAL-A2-ONE-HOLDER-INTERRUPT.ACTION.jsonl', 'bytes': 5705, 'sha256': '4dae214c98e06954e13d99ddee9ad648b031f4cb2c17d0747947b9a6fbdb6361'}, 'positive_tool_join': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/attempt2-held-only-retirement-source-1/ROOT-ACTUAL-HOLDER-TOOL78413-POSITIVE-JOIN.json', 'bytes': 1305, 'sha256': '4848fed86f0e012f33bb139feb9c17e2a5d0f7dbc234473570bba9c81daa7bac'}, 'native_or_build_launched': False}, 'new_operations': [{'nonce': '69fdd9797d5e89afb1bef0555c63842a', 'grant': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-host-preparation-source-1/ROOT-ACTUAL-THREE-STEP-HOST-GRANT-1.json', 'bytes': 2089, 'sha256': '74b1390b56e561c6562fd91dc91620734de0ab7ca87eeabf972f6d97652d4621'}, 'consumed_claim': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-host-preparation-source-1/future-capture-1/CONSUMED-GRANT.json', 'bytes': 2018, 'sha256': 'c54a5825a93bc5d9f7d5ac8a3b1e5399134646724740f579239c74110a0937da'}, 'actual_results': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-host-preparation-source-1/future-capture-1/RESULTS.json', 'bytes': 5868, 'sha256': '1e30fde6edf97ca7c7ecfe842709e5e9deb3bf07eaaf8e1d42ae30d2c4abe5ca'}, 'actual_tool': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-host-preparation-source-1/ROOT-ACTUAL-TOOL-RESULT.json', 'bytes': 1412, 'sha256': '5430f3701bc6e8c309b87ab633d1051a663d978d0846daed07c2a690b5fcbbea'}, 'summary': 'Threeactual227HOSTcommands/all26controls0; genericab3eproductionELF reused/no payload/prod/readelfreplay; independentactualHOSTreviewpending'}, {'nonce': '7afe5d0bf1631a014acfc9be0ca95ec9', 'grant': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/ROOT-ACTUAL-HOST-GRANT-1.json', 'bytes': 3529, 'sha256': 'f4ffc54762c970bcb176c4bbb9a8b9ec3f85280b9a670eb98ede61e3a7177f21'}, 'consumed_claim': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/future-capture-1/CONSUMED-GRANT.json', 'bytes': 2102, 'sha256': 'f24f331a928323426ff5fd19cc9eb4523251743a70a3eda752ae39281c3bab9f'}, 'actual_results': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/future-capture-1/RESULTS.json', 'bytes': 5487, 'sha256': '5b5325f642801485d39478fffa11f4cc5fdfc3f73fb5ffa94249ce69dced7607'}, 'first_failure': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/future-capture-1/FIRST-FAILURE.json', 'bytes': 158, 'sha256': '332bdf711051e2b67601573c35e0c95f3146d1a9253e2e3501b56fa5ba81033e'}, 'actual_tool': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/ROOT-ACTUAL-TOOL-RESULT.json', 'bytes': 1263, 'sha256': 'cb78102db1da00a6d9e0b18a5e4588e58d51bd7bc587068614960704a719a75d'}, 'summary': 'Two fullRust producers0 retained; CABIstep2failed missinggenuineexecuter/include/uti.h,3..6UNRUN. Contextsuffixrepairpending, notOS/algorithmfailure.'}], 'boundary_path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/attempt3-root51-metadata-rebase-source-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json', 'guard': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py', 'bytes': 4521, 'sha256': '1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'}}
STATUS='PASS_ROOT51_CURRENT115_ATTEMPT3_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):assert ref(row['path'])==row;return Path(row['path'])
def checked(row):return json.loads(auth(row).read_bytes())
def load(row,name):
 spec=importlib.util.spec_from_file_location(name,auth(row));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_retained():
 ledger=checked(PINS['ledger']);free=checked(PINS['free']);auth(PINS['base']);checked(PINS['base_boundary'])
 assert ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert len(ledger['consumed_nonces'])==len(set(ledger['consumed_nonces']))==62 and ledger['latest_accepted_free_boundary']==PINS['free']
 p50=checked(ledger['prior_ledger_retained']);p49=checked(p50['prior_ledger_retained'])
 assert len(p50['consumed_nonces'])==61 and len(p49['consumed_nonces'])==60
 assert ledger['consumed_nonces']==p49['consumed_nonces']+[o['nonce'] for o in PINS['new_operations']]
 assert ledger['ordinary_operations_since_prior_heavy_boundary']==p49['ordinary_operations_since_prior_heavy_boundary']+PINS['new_operations']
 for nonce in ['cf36b84313f404836ec6d80350e0e15a','92e8d698cfe12176ddd0375937cbaeb1']:
  assert nonce in ledger['reserved_abandoned_unconsumed_nonces'] and nonce not in ledger['consumed_nonces']
 assert free['decision']=='PASS_POSITIVE_HELD_ONLY_CURRENT115_ATTEMPT2_OWNER_RETIREMENT_AND_CURRENT_FREE_PERMANENT_MUTEX' and free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True and free['normal_owned_retirement'] is True
 assert free['holder']==dict(path='/run/lock/mckernel-development.lock',pid=1831939,starttime=95475556,device=27,inode=4,fd=3)
 st=free['actual_statuses'];assert st['compat_helper_exitcode']==0 and st['signal_calls']==1 and st['original_holder_tool_session']==78413 and st['original_holder_tool_exitcode']==130 and st['positive_holder_tool_join'] is True and st['closed_holder_tool_streams'] is True
 assert st['builds_started']==st['compiler_commands_from_abandoned_holder']==st['Docker_or_guest_launches_from_abandoned_holder']==0
 retirement=ledger['unlaunched115_A2_positive_retirement'];assert retirement==PINS['retirement'] and retirement['native_or_build_launched'] is False
 join=checked(retirement['positive_tool_join']);assert join['tool_session']==78413 and join['actual_tool_exit_code']==130 and join['positive_tool_join'] is True and join['tool_streams_closed'] is True
 assert join['holder_pid']==1831939 and join['holder_starttime']==95475556 and join['actual_signal_helper_exit_code']==0 and join['signal_calls']==1
 action=[json.loads(x) for x in auth(retirement['controlled_SIGINT_action']).read_text().splitlines()]
 assert [r['status'] for r in action]==['ENTERED_NO_SIGNAL','ATTEMPTING_EXACT_ONE_PIDFD_SIGINT_NO_RETRY','SIGNAL_SENT_NOT_RETIREMENT'] and action[-1]['signal_calls']==1
 assert action[0]['holder']==free['holder'] and join['action']==retirement['controlled_SIGINT_action']==free['actual_signal_action']
 for key in ('first','second'):
  assert {k:action[1][key][k] for k in ['pid','start','uid','fd','device','inode']}==dict(pid=1831939,start=95475556,uid=1000,fd=3,device=27,inode=4)
  assert action[1][key]['children']==[] and len(action[1][key]['negative_paths_absent'])==10
 actors=[dict(pid=1831939,start=95475556,role='A2_held_only_positive130')];joins=[];tools=[]
 for index,op in enumerate(PINS['new_operations']):
  checked(op['grant']);checked(op['consumed_claim']);r=checked(op['actual_results']);tool=checked(op['actual_tool']);tools.append(tool)
  assert tool['author']=='/root' and tool['positive_tool_terminal_join'] is True and tool['tool_streams_closed'] is True and tool['actual_results']==op['actual_results']
  assert len(r['results'])==3
  expected=[0,0,0] if index==0 else [0,0,1]
  assert [x['join']['returncode'] for x in r['results']]==expected
  for row in r['results']:
   j=row['join'];assert j['direct_child_joined'] is True and j['group_absent'] is True and j['closed_streams'] is True
   assert not j['remaining_group_members'] and not j['unexpected_group_members'] and not j['timed_out'] and j['error'] is None and j['retirement_error'] is None
   actors.append(dict(pid=j['pid'],start=j['start'],role='227_HOST_child' if index==0 else 'WAKE_HOST_child'));joins.append(dict(nonce=op['nonce'],result=op['actual_results'],index=row['index'],join=j))
  if index==0:
   assert tool['actual_tool_exit_code']==0 and tool['outer_pid']==1834925 and tool['outer_starttime']==95535523 and tool['actual_new227_controls']==26 and tool['production_recompiled'] is False
   actors.append(dict(pid=1834925,start=95535523,role='227_HOST_outer'))
  else:assert tool['tool_session']==85955 and tool['actual_tool_exit_code']==1 and tool['outer_pid'] is None and tool['outer_starttime'] is None
 assert len(actors)==8 and all(type(a['start']) is int for a in actors)
 return ledger,free,action,actors,joins,tools

def observe():
 assert os.getuid()==os.geteuid()==1000
 ledger,free,action,actors,joins,tools=validate_retained()
 bpath=Path(PINS['boundary_path']);boundary=json.loads(bpath.read_bytes())
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 assert boundary['nonce_ledger']==PINS['ledger'] and boundary['native_custody_clearance']==PINS['free'] and boundary['observer']==ref(__file__)
 checked(boundary['independent_current_boundary_review'])
 schema=checked(boundary['observer_schema']);review=checked(boundary['observer_schema_review'])
 assert schema==dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(__file__),ledger_key='Root51',expected_status=STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')
 assert review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['independent'] is True and review['reviewed_observer_schema']==boundary['observer_schema']
 guard=load(PINS['guard'],'unchanged_earliest_v2_guard_root51');first=guard.guard()
 base=load(PINS['base'],'exact_unchanged_Root49_physical_history');historical=base.observe()
 census=historical['group_membership_observation'];assert not census['errors']
 for actor in actors:
  assert not Path('/proc',str(actor['pid'])).exists()
  assert not any(row['pid']==actor['pid'] or row['pgrp']==actor['pid'] for row in census['rows'])
 assert not Path('/proc/1831939/fd/3').exists()
 for path in action[1]['second']['negative_paths_absent']:assert not os.path.lexists(path)
 assert len(historical['closed_exclusive_probes'])==2 and historical['pids_current']==0 and historical['no_existing_heavy'] is True
 clocks=guard.guard();assert all(a<b for a,b in zip(clocks,guard.current_cutoffs()))
 return dict(status=STATUS,scope=__doc__.splitlines()[0],runtime_authority=None,Root51=PINS['ledger'],actual_latest_operation_postjoin_acceptance=PINS['free'],current_boundary=ref(bpath),observed_clocks=first,last_observed_clocks=clocks,fixed_cutoffs=list(guard.current_cutoffs()),boot_id=guard.BOOT,
 historical_Root49_ledger=base.PINS['ledger'],historical_Root49_free=base.PINS['free'],historical_Root49_observer=PINS['base'],historical_Root49_reobservation=historical,
 group_membership_observation=census,closed_exclusive_probes=historical['closed_exclusive_probes'],known_numeric_controls_absent=sorted(set(historical['known_numeric_controls_absent']+[a['pid'] for a in actors])),new_exact_actors=actors,new_ordinary_positive_joins=joins,positive_A2_held_only_retirement=PINS['retirement'],WAKE_outer_PID_birth_uncaptured=True,WAKE_failed_CABI_preserved=True,
 no_existing_heavy=historical['no_existing_heavy'],active_shared_records_absent=historical['active_shared_records_absent'],capacity=historical['capacity'],memory=historical['memory'],cgroup=historical['cgroup'],pids_current=historical['pids_current'],running_container_observation=historical['running_container_observation'],retained_stopped_observation=historical['retained_stopped_observation'],native_acceptance=False,artifact_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
