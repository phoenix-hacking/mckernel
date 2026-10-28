"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Typed Root61 ordinary116 extension after genuine independent current-free adoption.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
PINS={'ledger60': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER60.json', 'bytes': 24066, 'sha256': 'bd4b75db9c1c7cdb2993aa957c0c9a690eed39210d751ba89319c29ef4fc28d4'}, 'current60_source': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/actual-bfd-physical-input-supplement-1/FULL-QUALIFICATION-RUN-1/TEST_ONLY-bad-recursion-9ply2asc/prepared/current60/observe_current60_postjoin.py', 'bytes': 13268, 'sha256': 'de9f6a1b76faded7a31227d13fe30cab33867ba769eb0a0b7234ea564946f048'}, 'capture2': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-actual-postjoin-current60-source-20261028-1/ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json', 'bytes': 5944082, 'sha256': 'ebbd745f00e17f52fb2e4f589633ca74c9e64e44a643f875c6d9697dc7c9a270'}, 'capture2_join': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-actual-postjoin-current60-source-20261028-1/profile-caller-correction-source-1/ACTUAL-CPU0-POSTJOIN-2.RESULT.json', 'bytes': 1142, 'sha256': '01189006547b80fe7de923c073f7a43951da3297805c9c08a1c4e6e3ae983263'}, 'compose_result': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/actual-host-bound-source-1/root-ordinary-compose-dispatch-source-1/future-capture-1/ACTUAL-COMPOSE-RESULT.json', 'bytes': 3596, 'sha256': '2afd5f7fb1ffb3501bda6071b135e055262a681a6fa2f09f7c07eff737ba3728'}, 'CID': '57a5fb1f62bc707ee90412fe9585718cdaa39e4110854f91bf4cb6df4380fda3'}
CURRENT={'ledger': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER61.json', 'bytes': 24665, 'sha256': '20e2470a6f7f81b188350af1374611801f68eacbf80ee8916814bd48962f4fa2'}, 'latest_free': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-observer-guard-independent-review-20261028-1/CURRENT116-POSTJOIN-REVIEW-1/CURRENT-FREE.json', 'bytes': 12188, 'sha256': '6c83eee41b7e90d0f055034b9bbd30cfc9e32efac9e8285a90fc8948f7b82e7d'}, 'root_inputs': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER61.json', 'bytes': 24665, 'sha256': '20e2470a6f7f81b188350af1374611801f68eacbf80ee8916814bd48962f4fa2'}, 'ledger_key': 'Root61', 'compose_result': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/actual-host-bound-source-1/root-ordinary-compose-dispatch-source-1/future-capture-1/ACTUAL-COMPOSE-RESULT.json', 'bytes': 3596, 'sha256': '2afd5f7fb1ffb3501bda6071b135e055262a681a6fa2f09f7c07eff737ba3728'}}
BOUNDARY=HERE/'cohort/ROOT-ACTUAL-CURRENT-BOUNDARY.json'
STATUS='PASS_Root61_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE'


def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):need(type(r)is dict and set(r)=={'path','bytes','sha256'} and ref(r['path'])==r,'exact BYTE subject');return Path(r['path'])
def checked(r):return json.loads(auth(r).read_bytes())
def load(r,n):
 spec=importlib.util.spec_from_file_location(n,auth(r));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def validate_adoption(ledger,free,observation,prior):
 need(CURRENT is not None,'genuine Root61/free not bound; no current-free default')
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True,'Root61 exact boundary')
 need(ledger['consumed_nonces']==prior['consumed_nonces'] and len(ledger['consumed_nonces'])==70 and ledger['current_native_operation']==prior['current_native_operation'],'same70consumed and genuine native4d1c historical branch')
 need(ledger['current_physical_clearance_pending'] is False and ledger['latest_accepted_free_boundary']==CURRENT['latest_free'],'actual newly adopted currentfree')
 need(free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True and str(free['decision']).startswith('PASS'),'genuine independent currentfree')
 need(observation['Root60']==PINS['ledger60'] and observation['ordinary_build_nonce']=='ff79f7711b2ba35b039f3a191ab09663' and observation['retained_stopped_container']==PINS['CID'],'actual116capture2 branch')
 need(observation['current_free_candidate'] is True and observation['independent_acceptance'] is False and observation['signals_cleanup_workloads']==0,'original capture scope remains observation-only')
 need(observation['pids_current']==0 and observation['no_existing_heavy'] is True and observation['active_shared_records_absent'] is True and len(observation['all53_prior_and_new_actors_absent'])==53,'capture2 all53 actors/custody')
 # The independent receipt is authenticated exactly. Its binding must actually name
 # the exact capture2 reference, never capture1 or oldf76 as new clearance.
 need(free['Root60']==PINS['ledger60'] and free['actual_postjoin_observation']==PINS['capture2'] and free['actual_capture_number']==2 and free['capture1_accepted'] is False,'typed free binds actual Root60/capture2 only')
 need(free['ordinary_build_nonce']=='ff79f7711b2ba35b039f3a191ab09663' and free['prior_native_nonce']=='4d1c28c2d9caa913e4ab1e8a504ac5ea' and free['native_operation_reclassified_as_ordinary'] is False,'typed native/ordinary receipt boundary')
 need(free['all53_accumulated_actor_rows_absent'] is True and free['additional7_HOSTfixture_PID_groups_absent'] is True and free['pids_current']==0 and free['active_shared_records_absent'] is True and free['no_existing_heavy'] is True,'typed currentfree physical closure')
 need(CURRENT['latest_free']!=observation['previous_accepted_free_boundary'],'f76 cannot be relabeled new currentfree')
 return True


def validate_current(current=None):
 need(CURRENT is not None and current==CURRENT,'exact bound Root61 current')
 old=load(PINS['current60_source'],'retained_actual116_current60_predicates');rows,_common,actors=old.validate_current()
 observation=checked(PINS['capture2']);free=checked(current['latest_free']);ledger=checked(current['ledger'])
 validate_adoption(ledger,free,observation,rows['ledger60'])
 joined=checked(PINS['capture2_join']);need(joined['returncode']==0 and joined['positive_direct_wait4_join'] is True and joined['streams_closed'] is True and joined['pid']==1907223 and int(joined['birth'])==96691234 and joined['process_group_absent'] is True and not joined['remaining_group_members'] and not joined['group_observation_errors'],'actual CPU0 owned capture2 positive join')
 need(current['compose_result']==PINS['compose_result'] and current['ledger_key']=='Root61','original227 composition retained separately')
 supplement=checked(free['additional_HOSTbody2_qualification_supplement']);need(len(supplement['actors'])==7 and supplement['consumed_runtime_nonce_delta']==0,'source qualification stays outside runtime nonce ledger')
 for actor in supplement['actors']:
  auth(actor['evidence']);need(actor['positive_join'] is True and actor['returncode']==0 and actor['group_absent'] is True and actor['streams_closed'] is True,'positive source qualification retirement');actors.append(dict(pid=actor['pid'],start=int(actor['birth']),role='HOSTbody2_source_qualification'))
 actors.append(dict(pid=joined['pid'],start=int(joined['birth']),role='actual_CPU0_capture2'))
 return ledger,free,dict(capture2=PINS['capture2'],ordinary_build=rows['ledger60']['current116_build']),actors


def consumer_value(history,first,last,cutoffs,boot):
 base=history['historical_Root59_native_and_physical']
 value=dict(history)
 for key in ['capacity','memory','cgroup']:
  value[key]=base[key]
 value['running_container_observation']=history['queries'][0]
 value['retained_stopped_observation']=history['queries'][-1]
 value['known_numeric_controls_absent']=sorted(set(base['known_numeric_controls_absent']+[a['pid'] for a in history['all53_prior_and_new_actors_absent']]))
 value.update(status=STATUS,Root61=CURRENT['ledger'],current_boundary=CURRENT['root_inputs'],actual_latest_operation_postjoin_acceptance=CURRENT['latest_free'],actual_current60_postjoin_acceptance=CURRENT['latest_free'],historical_current60_reobservation=history,current_free_candidate=False,independent_acceptance=False,observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=list(cutoffs),boot_id=boot,runtime_authority=None)
 return value


def observe():
 ledger,free,ext,actors=validate_current(CURRENT)
 b=json.loads((HERE/'ROOT61-RUNTIME-DEPENDENCIES.json').read_bytes())
 need(b['author']=='/root' and b['observer']==ref(__file__) and b['ledger']==CURRENT['ledger'],'exact Root61 runtime deps')
 review=checked(b['independent_review']);need(review['independent'] is True and review['implementation_ownership'] is False and review['decision']=='PASS_EXACT_ROOT61_CURRENT118_OBSERVER_DEPENDENCIES' and review['observer']==ref(__file__),'independent Root61 configured deps')
 for key in ['guard_adapter','guard_configuration']:
  need(review[key]==b[key],'exact reviewed '+key);auth(b[key])
 guard=load(b['guard_adapter'],'original227_current61_actual_guard');need(guard.OPERATION=='current118-build','current118-build guard operation');guard.configure(b['guard_configuration']);first=guard.guard()
 old=load(PINS['current60_source'],'genuine116_current60_reobservation');history=old.observe()
 need(history['Root60']==PINS['ledger60'] and history['ordinary_build_nonce']=='ff79f7711b2ba35b039f3a191ab09663','ordinary116 freshly reobserved without replay')
 census=history['group_membership_observation'];need(not census['errors'],'complete current actor census')
 for actor in actors:
  need(not Path('/proc',str(actor['pid'])).exists() and not any(row['pid']==actor['pid'] or row['pgrp']==actor.get('group',actor['pid']) for row in census['rows']),'all prior/build/sourcequalification/capture actors absent')
 last=guard.guard();cutoffs=guard.current_cutoffs();need(all(now<limit<=ceiling for now,limit,ceiling in zip(last,cutoffs,(1793253600.0,1035704.5689393478,1051042.6959879305))),'exact original227 earliest inherited clamps')
 value=consumer_value(history,first,last,cutoffs,guard.BOOT)
 boundary=checked(ref(BOUNDARY))
 need(boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True,'exact Root build boundary descriptor')
 need(boundary['nonce_ledger']==CURRENT['ledger'] and boundary['native_custody_clearance']==CURRENT['latest_free'] and boundary['observer']==ref(__file__),'Root61 build descriptor exact observer/ledger/free')
 for key in ['independent_current_boundary_review','observer_schema','observer_schema_review']:auth(boundary[key])
 schema=checked(boundary['observer_schema']);review=checked(boundary['observer_schema_review'])
 need(schema['observer']==ref(__file__) and schema['ledger_key']=='Root61' and schema['expected_status']==STATUS and schema['current_boundary_key']=='current_boundary' and schema['latest_free_key']=='actual_latest_operation_postjoin_acceptance','exact typed117 observer schema')
 need(review['independent'] is True and review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['reviewed_observer_schema']==boundary['observer_schema'],'independent117 schema source review')
 value['current_boundary']=ref(BOUNDARY)
 return value

if __name__=='__main__':
 print(json.dumps(observe(),indent=2))
