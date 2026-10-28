"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Original227 current observer template. Root53/build115/WAKE history genuine;
CURRENT is mechanically Root-filled only after actual compose/Root54, never guessed.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess
PINS={'ledger53': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER53.json', 'bytes': 11644, 'sha256': '21172cfd0e4428e77bd3ddab4658e89067a7835e5ee102f8a067e99aacda5000'}, 'free115': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-4/independent-postbuild-current-free-review-1/CURRENT-FREE.json', 'bytes': 5561, 'sha256': '270a93392db9d5c64c7546d43ac36cb604b85da4668884736b4920b623c3111d'}, 'base': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/attempt4-root51-boundary-contract-correction-source-1/observe_root51_current115_attempt4.py', 'bytes': 15134, 'sha256': 'b3abfdada1909b9b3a945f522cb0f6b7abe0dc87b7bba5e844ee4d1703b127ad'}, 'base_boundary': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/attempt4-root51-boundary-contract-correction-source-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json', 'bytes': 2488, 'sha256': '3a80b9315b9d2baf8eae9e693f8ce17476116b0d9df5e63c2b1d1e6c2af75b82'}, 'wake': {'scope': 'HOST_ONLY_NO_NATIVE_AUTHORITY', 'nonce': '316dbe102f50b2960a4c088d0a6aeda8', 'grant': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/genuine-executer-include-closure-source-1/ROOT-ACTUAL-HOST-GRANT-1.json', 'bytes': 3615, 'sha256': 'df82c844e0fd1549b2a1cefe1f2b84dc2c043db80448f1bee2203ee0a4ee2c92'}, 'actual_results': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/genuine-executer-include-closure-source-1/future-capture-1/RESULTS.json', 'bytes': 9581, 'sha256': 'b20a33c5611ab2300581d7adf9f65af2f7b0d4bf3d6bc7b960b55f98ce747bcc'}, 'Root_tool': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f03-next-selected-family-source-3/current114-perf-restore-correction-source-1/absolute-helper-context-correction-source-1/genuine-executer-include-closure-source-1/ROOT-ACTUAL-TOOL-RESULT.json', 'bytes': 1352, 'sha256': 'cf10c322b85d31e4613e648aec39bc9635f673a3be44054ef04bd50f6c27c65d'}, 'actual_commands': 5, 'positive_joins': True, 'groups_absent': True, 'closed_streams': True, 'independent_acceptance': None}, 'guard': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py', 'bytes': 4521, 'sha256': '1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'}}
CURRENT=None  # ROOT_ACTUAL_POSTCOMPOSE_CURRENT_LITERAL
STATUS='PASS_ROOT_CURRENT_LEDGER_KEY_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def checked(r):return json.loads(auth(r).read_bytes())
def load(r,name):
 spec=importlib.util.spec_from_file_location(name,auth(r));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_retained53():
 l=checked(PINS['ledger53']);f=checked(PINS['free115']);auth(PINS['base']);checked(PINS['base_boundary'])
 assert l['author']=='/root' and l['complete_within_declared_current_boundary'] is True and l['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert len(l['consumed_nonces'])==len(set(l['consumed_nonces']))==64 and l['latest_accepted_free_boundary']==PINS['free115']
 assert f['decision']=='PASS_POSITIVE_CURRENT115_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX' and f['independent'] is True and f['implementation_ownership'] is False and f['current_free'] is True and f['normal_owned_retirement'] is True
 assert f['holder']==dict(path='/run/lock/mckernel-development.lock',pid=1849845,starttime=95775567,device=27,inode=4,fd=3)
 assert f['runner']==dict(pid=1849881,starttime=95777018,returncode=0,joined=True) and f['actual_four_commands_returncodes']==[0,0,0,0]
 assert f['retained_stopped_container']==f['container']=='52ae1a85fda1adfaa0a0a3c72306a60a6df0144359f0cd6b9ed1d83c2fc2385c'
 terminal=checked(f['container_terminal']);assert terminal['container']==f['container'] and terminal['returncode']==0 and terminal['state']['Running'] is False and terminal['state']['Pid']==0 and terminal['state']['ExitCode']==0 and terminal['state']['OOMKilled'] is False
 ext=checked(f['fresh_current_extension']);assert ext['new_actor_PID_paths_absent'] is True and ext['new_actor_process_groups_absent'] is True and ext['holder_fd3_absent'] is True and ext['permanent_27_4_lock_rows_absent'] is True
 assert len(ext['exact_CID_queries'])==4 and all(q['positive_wait'] is True and q['streams_closed'] is True for q in ext['exact_CID_queries'])
 op=PINS['wake'];assert l['ordinary_operations_since_prior_heavy_boundary']==[op];r=checked(op['actual_results']);tool=checked(op['Root_tool']);checked(op['grant'])
 assert len(r['results'])==5 and [x['join']['returncode'] for x in r['results']]==[0]*5
 assert tool['tool_session_id']==50015 and tool['tool_exit_code']==0 and tool['tool_positive_join'] is True and tool['outer_pid'] is None and tool['outer_birth'] is None
 actors=[dict(pid=f['holder']['pid'],start=f['holder']['starttime'],role='CURRENT115_holder'),dict(pid=f['runner']['pid'],start=f['runner']['starttime'],role='CURRENT115_runner')]
 for row in r['results']:
  j=row['join'];validate_join(j);actors.append(dict(pid=j['pid'],start=j['start'],role='WAKE_suffix_child'))
 return l,f,ext,actors

def validate_join(j):
 assert j['direct_child_joined'] is True and j['group_absent'] is True and j['closed_streams'] is True
 assert not j['remaining_group_members'] and not j['unexpected_group_members'] and not j['timed_out'] and j['error'] is None and j['retirement_error'] is None
 assert type(j['pid']) is int and type(j['start']) is int

def validate_current(current):
 assert current is not None,'actual postcompose Root54 metadata required; template is not observation authority'
 root_inputs=checked(current['root_inputs']);assert root_inputs['author']=='/root' and current['root_inputs']==current['ledger'] and root_inputs['latest_accepted_free_boundary']==current['latest_free']
 l53,free,ext,actors=validate_retained53();l=checked(current['ledger']);accepted=checked(current['latest_free']);compose=checked(current['compose_result']);j=checked(compose['join']);validate_join(j)
 assert l['author']=='/root' and l['complete_within_declared_current_boundary'] is True and l['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert current['ledger_key']=='ROOT_CURRENT_LEDGER_KEY' and Path(current['ledger']['path']).name=='ROOT_CURRENT_LEDGER_BASENAME'
 assert l['latest_accepted_free_boundary']==current['latest_free'] and accepted['independent'] is True and accepted['current_free'] is True and accepted['normal_owned_retirement'] is True
 assert l['consumed_nonces'][:64]==l53['consumed_nonces'] and len(l['consumed_nonces'])>64 and len(set(l['consumed_nonces']))==len(l['consumed_nonces'])
 new_nonces=l['consumed_nonces'][64:]
 operations=[op for op in l['ordinary_operations_since_prior_heavy_boundary'] if op['nonce'] in new_nonces]
 assert [op['nonce'] for op in operations]==new_nonces and compose['nonce'] in new_nonces
 for op in operations:
  if 'actual_results' in op:rows=checked(op['actual_results'])['results']
  else:
   assert 'actual_whole_join' in op;rows=[dict(join=checked(op['actual_whole_join']))]
  assert rows
  for row in rows:
   item=row['join'];validate_join(item);actors.append(dict(pid=item['pid'],start=item['start'],role='postRoot53_ordinary_child'))
 assert compose['status']=='ACTUAL_ONE_46D_COMPOSE_ZERO_JOINED_FULL_RECEIPT_NOT_NATIVE' and j['returncode']==0
 assert compose['current_nonce_ledger']==PINS['ledger53'] and compose['current_native_free']==PINS['free115']
 assert current['compose_result']['sha256'] in json.dumps(l),'genuine Root54 explicitly retains actual composition result'
 assert any(a['pid']==j['pid'] and a['start']==j['start'] for a in actors)
 return l,accepted,ext,actors

def observe():
 assert os.getuid()==os.geteuid()==1000
 ledger,accepted,ext,actors=validate_current(CURRENT)
 guard=load(PINS['guard'],'original_earliest_v2_guard_native227');first=guard.guard()
 base=load(PINS['base'],'exact_actual115_Root51_b3ab_original_history');history=base.observe()
 census=history['group_membership_observation'];assert not census['errors']
 for actor in actors:
  assert not Path('/proc',str(actor['pid'])).exists()
  assert not any(r['pid']==actor['pid'] or r['pgrp']==actor['pid'] for r in census['rows'])
 assert not Path('/proc/1849845/fd/3').exists()
 queries=[]
 for expected in ext['exact_CID_queries']:
  q=subprocess.run(expected['argv'],capture_output=True,text=True,timeout=15)
  assert (q.returncode,q.stdout,q.stderr)==(expected['returncode'],expected['stdout'],expected['stderr'])
  queries.append(dict(argv=expected['argv'],returncode=q.returncode,stdout=q.stdout,stderr=q.stderr,positive_wait=True,streams_closed=True))
 assert len(history['closed_exclusive_probes'])==2 and history['pids_current']==0 and history['no_existing_heavy'] is True
 last=guard.guard();assert all(a<b for a,b in zip(last,guard.current_cutoffs()))
 return dict(status=STATUS,scope=__doc__.splitlines()[0],runtime_authority=None,ROOT_CURRENT_LEDGER_KEY=CURRENT['ledger'],current_boundary=CURRENT['root_inputs'],actual_latest_operation_postjoin_acceptance=CURRENT['latest_free'],observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=list(guard.current_cutoffs()),boot_id=guard.BOOT,
 historical_Root53=PINS['ledger53'],historical_CURRENT115_free=PINS['free115'],historical_Root51_observer=PINS['base'],historical_Root51_reobservation=history,new_exact_actors=actors,current115_exact_CID_queries=queries,
 known_numeric_controls_absent=sorted(set(history['known_numeric_controls_absent']+[a['pid'] for a in actors])),group_membership_observation=census,closed_exclusive_probes=history['closed_exclusive_probes'],no_existing_heavy=history['no_existing_heavy'],active_shared_records_absent=history['active_shared_records_absent'],capacity=history['capacity'],memory=history['memory'],cgroup=history['cgroup'],pids_current=history['pids_current'],running_container_observation=history['running_container_observation'],retained_stopped_observation=history['retained_stopped_observation'],native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
