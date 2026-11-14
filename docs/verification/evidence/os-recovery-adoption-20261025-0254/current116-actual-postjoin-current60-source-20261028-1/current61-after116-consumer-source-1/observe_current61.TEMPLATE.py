"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Typed Root61 ordinary116 extension after genuine independent current-free adoption.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
PINS=None  # ROOT_RETAINED_ACTUAL_PINS
CURRENT=None  # ROOT_ACTUAL61_CURRENT_LITERAL
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


def observe():
 ledger,free,ext,actors=validate_current(CURRENT)
 b=json.loads((HERE/'ROOT61-RUNTIME-DEPENDENCIES.json').read_bytes())
 need(b['author']=='/root' and b['observer']==ref(__file__) and b['ledger']==CURRENT['ledger'],'exact Root61 runtime deps')
 review=checked(b['independent_review']);need(review['independent'] is True and review['implementation_ownership'] is False and review['decision']=='PASS_EXACT_ROOT61_ORIGINAL227_OBSERVER_DEPENDENCIES' and review['observer']==ref(__file__),'independent Root61 configured deps')
 for key in ['guard_adapter','guard_configuration']:
  need(review[key]==b[key],'exact reviewed '+key);auth(b[key])
 guard=load(b['guard_adapter'],'original227_current61_actual_guard');need(guard.OPERATION=='original227','original227 guard operation');guard.configure(b['guard_configuration']);first=guard.guard()
 old=load(PINS['current60_source'],'genuine116_current60_reobservation');history=old.observe()
 need(history['Root60']==PINS['ledger60'] and history['ordinary_build_nonce']=='ff79f7711b2ba35b039f3a191ab09663','ordinary116 freshly reobserved without replay')
 census=history['group_membership_observation'];need(not census['errors'],'complete current actor census')
 for actor in actors:
  need(not Path('/proc',str(actor['pid'])).exists() and not any(row['pid']==actor['pid'] or row['pgrp']==actor.get('group',actor['pid']) for row in census['rows']),'all prior/build/sourcequalification/capture actors absent')
 last=guard.guard();cutoffs=guard.current_cutoffs();need(all(now<limit<=ceiling for now,limit,ceiling in zip(last,cutoffs,(1793253600.0,1035705.5689454618,1051043.6959931096))),'exact original227 earliest inherited clamps')
 value=dict(history);value.update(status=STATUS,Root61=CURRENT['ledger'],current_boundary=CURRENT['root_inputs'],actual_latest_operation_postjoin_acceptance=CURRENT['latest_free'],actual_current60_postjoin_acceptance=CURRENT['latest_free'],historical_current60_reobservation=history,current_free_candidate=False,independent_acceptance=False,observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=list(cutoffs),boot_id=guard.BOOT,runtime_authority=None)
 return value

if __name__=='__main__':
 print(json.dumps(observe(),indent=2))
