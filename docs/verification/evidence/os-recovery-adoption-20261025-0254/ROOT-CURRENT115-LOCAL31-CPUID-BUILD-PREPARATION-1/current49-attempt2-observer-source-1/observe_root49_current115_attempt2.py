"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root49 additive CURRENT115 A2 observer. Unchanged Root48 observe supplies full physical history.
Source only: importing/validate_retained does not observe processes or call guards/subprocesses.
"""
from pathlib import Path
import hashlib,importlib.util,json,os
PINS={'ledger': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER49.json', 'bytes': 42600, 'sha256': '25e77399fefcbe9abdffe86b2248819c6d77ec6aad77c0950abcdb4d1d7ad70e'}, 'free': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/prelaunch-held-only-retirement-source-1/pidfd-syscall-compatibility-source-1/independent-current-free-review-1/CURRENT-FREE.json', 'bytes': 20712, 'sha256': '791f387855e1ce1ff9db0d1a19d1878a4a346a8d0b27c9c316bbd142403a685b'}, 'base': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/current-boundary-observer-source-1/observe_root48_current115.py', 'bytes': 34582, 'sha256': 'd9929d4abaa7032bb77580d9e73da5ba457a49f4b779941aa090063509285574'}, 'base_review': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/current-boundary-observer-source-1/independent-source-review-1/REVIEW.json', 'bytes': 14934, 'sha256': 'e9169192cd09705d4bc173d87b91e1dde3966684473ea88c7d58ee1dc9c8a353'}, 'historical_boundary': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json', 'bytes': 1628, 'sha256': '1586023de82c71f063593b2f21114a2aa369da7b7d817bd4f65cc00a5682ac6a'}, 'retirement': {'abandoned_nonce': 'cf36b84313f404836ec6d80350e0e15a', 'expired_refusal': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/INDEPENDENT-ACTUAL-HELD-RESOURCE-EXECUTION-REVIEW.json', 'bytes': 5725, 'sha256': '91e5ad3309f97e4e5625eaabd246ac8db92351e3955f005762dd84b81d4b4e31'}, 'controlled_SIGINT_action': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/prelaunch-held-only-retirement-source-1/pidfd-syscall-compatibility-source-1/ACTUAL-COMPAT-ONE-HOLDER-INTERRUPT.ACTION.jsonl', 'bytes': 5775, 'sha256': '9bae79a78a445a3a75575d18bac5297bb8cc4a3610d3498be8adf6c9ee5755bd'}, 'positive_tool_join': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/prelaunch-held-only-retirement-source-1/pidfd-syscall-compatibility-source-1/ROOT-ACTUAL-HOLDER-TOOL11857-POSITIVE-JOIN.json', 'bytes': 1135, 'sha256': '7346f1ef476450759ff0f0fbac18dca225df330b2af85322705d3215fde87ef8'}, 'native_or_build_launched': False}, 'reader': {'nonce': '565026d079f0acc22e8e863c3deee226', 'grant': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/foreground-f06-shmget-current114-abi-source-1/local-target-identity-reader-correction-source-1/ROOT-ACTUAL-HOST-GRANT-1.json', 'bytes': 3840, 'sha256': '61b65efb15947109a7e75cf2c7c92d50fbebfdac9d22642480be254985a10644'}, 'consumed_claim': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/foreground-f06-shmget-current114-abi-source-1/local-target-identity-reader-correction-source-1/future-capture-1/CONSUMED-GRANT.json', 'bytes': 2047, 'sha256': '6bb9047605e4f787e57dca5fa7009d2fd2dff0a64dbbc3a86b5961b1102e05e8'}, 'actual_results': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/foreground-f06-shmget-current114-abi-source-1/local-target-identity-reader-correction-source-1/future-capture-1/RESULTS.json', 'bytes': 1873, 'sha256': '469ffe8c85538ab55a83787c90f1e285226ff2b14687c3a16ac22f511317a09d'}, 'actual_tool': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/foreground-f06-shmget-current114-abi-source-1/local-target-identity-reader-correction-source-1/ROOT-ACTUAL-TOOL-RESULT.json', 'bytes': 1703, 'sha256': '38fa0617d76b018b3cbce43ce6f82b47bb6eb72ef8e3b9b171279005fbbe612f'}, 'independent_HOST': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/foreground-f06-shmget-current114-abi-source-1/local-target-identity-reader-correction-source-1/independent-actual-host-review-1/REVIEW.json', 'bytes': 25267, 'sha256': '67fadd26e4eccc8da668fe79233125e4cdfcba6b48a904693d5ef0bebe87b503'}, 'summary': 'Fourproducerprefix reused; onefiniteidentityreaderPASS/.365s; HOSTpartiallinkonly'}, 'current49_boundary_path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json'}

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):assert ref(row['path'])==row;return Path(row['path'])
def checked(row):return json.loads(auth(row).read_bytes())
def load(row,name):
 spec=importlib.util.spec_from_file_location(name,auth(row));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_retained():
 ledger=checked(PINS['ledger']);free=checked(PINS['free']);checked(PINS['base_review']);checked(PINS['historical_boundary']);auth(PINS['base'])
 assert ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert len(ledger['consumed_nonces'])==len(set(ledger['consumed_nonces']))==60 and ledger['latest_accepted_free_boundary']==PINS['free']
 prior=checked(ledger['prior_ledger_retained']);assert len(prior['consumed_nonces'])==59 and ledger['consumed_nonces']==prior['consumed_nonces']+['565026d079f0acc22e8e863c3deee226']
 assert ledger['ordinary_operations_since_prior_heavy_boundary'][:-1]==prior['ordinary_operations_since_prior_heavy_boundary']
 assert 'cf36b84313f404836ec6d80350e0e15a' in ledger['reserved_abandoned_unconsumed_nonces'] and 'cf36b84313f404836ec6d80350e0e15a' not in ledger['consumed_nonces']
 assert free['decision']=='PASS_POSITIVE_HELD_ONLY_CURRENT115_OWNER_RETIREMENT_AND_CURRENT_FREE_PERMANENT_MUTEX' and free['independent'] is True and free['implementation_ownership'] is False and free['normal_owned_retirement'] is True and free['current_free'] is True
 assert free['holder']==dict(path='/run/lock/mckernel-development.lock',pid=1815979,starttime=95215128,device=27,inode=4,fd=3)
 status=free['actual_statuses'];assert status['compat_helper_exitcode']==0 and status['signal_calls']==1 and status['original_holder_tool_session']==11857 and status['original_holder_tool_exitcode']==130 and status['positive_holder_tool_join'] is True and status['closed_holder_tool_streams'] is True
 assert status['builds_started']==status['compiler_commands']==status['Docker_or_guest_launches_from_abandoned_holder']==0
 retirement=ledger['unlaunched115_positive_retirement'];assert retirement==PINS['retirement'] and retirement['native_or_build_launched'] is False
 join=checked(retirement['positive_tool_join']);assert join['author']=='/root' and join['tool_session']==11857 and join['actual_tool_exit_code']==130 and join['positive_tool_join'] is True and join['stdout_stderr_tool_closed'] is True
 assert join['holder_pid']==1815979 and join['holder_starttime']==95215128 and join['signal_calls']==1 and join['compat_helper_actual_tool_exit_code']==0 and join['no_build_READY_or_runner'] is True and join['native_cleanup'] is False
 action=[json.loads(line) for line in auth(retirement['controlled_SIGINT_action']).read_text().splitlines()]
 assert [r['status'] for r in action]==['ENTERED_NO_SIGNAL','ATTEMPTING_EXACT_ONE_PIDFD_SIGINT_NO_RETRY','SIGNAL_SENT_NOT_RETIREMENT'] and action[-1]['signal_calls']==1
 assert action[0]['holder']==free['holder'] and join['compat_helper_action']==retirement['controlled_SIGINT_action']==free['actual_signal_action']
 for key in ('first','second'):
  assert {k:action[1][key][k] for k in ('pid','start','uid','fd','device','inode')}==dict(pid=1815979,start=95215128,uid=1000,fd=3,device=27,inode=4)
  assert action[1][key]['children']==[] and len(action[1][key]['negative_paths_absent'])==10
 reader=PINS['reader'];assert ledger['ordinary_operations_since_prior_heavy_boundary'][-1]==reader and reader['nonce']=='565026d079f0acc22e8e863c3deee226'
 checked(reader['grant']);checked(reader['consumed_claim']);results=checked(reader['actual_results']);tool=checked(reader['actual_tool'])
 assert len(results['results'])==1;child=results['results'][0]['join']
 assert child['pid']==1821142 and child['start']==95311840 and child['returncode']==0 and child['direct_child_joined'] is True and child['group_absent'] is True and child['closed_streams'] is True
 assert not child['remaining_group_members'] and not child['unexpected_group_members'] and not child['timed_out'] and child['error'] is None and child['retirement_error'] is None
 assert tool['author']=='/root' and tool['tool_session']==12590 and tool['actual_tool_exit_code']==0 and tool['positive_tool_terminal_join'] is True and tool['tool_streams_closed'] is True
 assert tool['outer_pid'] is None and tool['outer_starttime'] is None and tool['actual_results']==reader['actual_results']
 return ledger,free,action,child,tool

def observe():
 assert os.getuid()==os.geteuid()==1000
 ledger,free,action,child,tool=validate_retained()
 boundary_path=Path(PINS['current49_boundary_path']);boundary=json.loads(boundary_path.read_bytes())
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 assert boundary['nonce_ledger']==PINS['ledger'] and boundary['native_custody_clearance']==PINS['free'] and boundary['observer']==ref(__file__)
 checked(boundary['independent_current_boundary_review'])
 base=load(PINS['base'],'exact_retained_Root48_current115_physical_history')
 guard=load(dict(path=str(base.GUARD),bytes=base.GUARD.stat().st_size,sha256=base.GUARD_SHA),'same_reviewed_earliest_v2_guard')
 first_clocks=guard.guard()
 historical=base.observe()  # Unchanged d992; all historical controls/probes/CIDs/cgroups/floors reobserved.
 census=historical['group_membership_observation'];assert not census['errors']
 actors=[dict(pid=1815979,start=95215128,role='unlaunched_holder_positive_tool130'),dict(pid=child['pid'],start=child['start'],role='final_F06_reader_positive_join0')]
 for actor in actors:
  assert not Path('/proc',str(actor['pid'])).exists()
  assert not any(row['pid']==actor['pid'] or row['pgrp']==actor['pid'] for row in census['rows'])
 assert not Path('/proc/1815979/fd/3').exists()
 for path in action[1]['second']['negative_paths_absent']:assert not os.path.lexists(path)
 assert len(historical['closed_exclusive_probes'])==2 and historical['pids_current']==0 and historical['no_existing_heavy'] is True
 clocks=guard.guard();assert all(a<b for a,b in zip(clocks,guard.current_cutoffs()))
 return dict(status='PASS_ROOT49_CURRENT115_ATTEMPT2_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE',scope=__doc__.splitlines()[0],runtime_authority=None,Root49=PINS['ledger'],actual_latest_operation_postjoin_acceptance=PINS['free'],current_boundary=ref(boundary_path),observed_clocks=first_clocks,last_observed_clocks=clocks,fixed_cutoffs=list(guard.current_cutoffs()),boot_id=guard.BOOT,
 historical_Root48_ledger=base.ROOT48_LEDGER,historical_Root48_free=base.ROOT48_FREE,historical_Root48_observer=PINS['base'],historical_Root48_reobservation=historical,
 group_membership_observation=census,closed_exclusive_probes=historical['closed_exclusive_probes'],known_numeric_controls_absent=sorted(set(historical['known_numeric_controls_absent']+[a['pid'] for a in actors])),new_exact_actors=actors,positive_held_only_retirement=PINS['retirement'],positive_final_F06_reader=PINS['reader'],outer_reader_PID_birth_uncaptured=True,
 no_existing_heavy=historical['no_existing_heavy'],active_shared_records_absent=historical['active_shared_records_absent'],capacity=historical['capacity'],memory=historical['memory'],cgroup=historical['cgroup'],pids_current=historical['pids_current'],running_container_observation=historical['running_container_observation'],retained_stopped_observation=historical['retained_stopped_observation'],native_acceptance=False,artifact_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
