"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact Root37 successor: original28controls plus two positively joined build actors.
Retained failed container must remain stopped exit1, not be treated as absent.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
LEDGER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER37.json')
FREE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT113-CORRECTED-SCALAR4-NEXT4-BUILD-ADMISSION-1/independent-failed-build-review-1/CURRENT-FREE.json')
BASE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/root36-admission-preparation-source-1/observe_root36_current.py')
REFS=[{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER37.json', 'bytes': 4591, 'sha256': 'b6ed7c321b348e90e13a51607d88af09893ab760e3decdd4d16d000a130155e8'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT113-CORRECTED-SCALAR4-NEXT4-BUILD-ADMISSION-1/independent-failed-build-review-1/CURRENT-FREE.json', 'bytes': 92521, 'sha256': '070e0f2c4f367da3444f30300bfbeb193af6d1bb7cc6cda663a1cb154bfe9f13'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/root36-admission-preparation-source-1/observe_root36_current.py', 'bytes': 5114, 'sha256': '6b6da525fb30e1793fd7e4d3b350b8d3f07c27b0c2c31c4b37439759c4412876'}]

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def observe():
 assert os.getuid()==os.geteuid()==1000
 for r in REFS:auth(r)
 ledger=read(LEDGER);review=read(FREE)
 assert ledger['latest_accepted_free_boundary']==ref(FREE) and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_CURRENT113_FAILED_RUST_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX' and review['normal_owned_retirement'] is True and review['current_free'] is True
 assert review['actual_failure']['error_code']=='E0616' and review['actual_failure']['no_passing_current113_compiler_prefix'] is True
 for key in ['holder_tool_result','local_terminal','runner_join','container_terminal']:auth(review[key])
 assert review['positive_termination']['local_holder_positive_join'] is True and review['positive_termination']['runner_positive_join'] is True
 spec=importlib.util.spec_from_file_location('root37_retained_root36_observer',BASE)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.observe()
 # Original Root36/28controls/25clients/lease and global current contract unchanged.
 assert original['exact25clients_reaped'] is True
 old=review['fresh_current']['prior_native_28_controls_absent'];new=review['fresh_current']['new_holder_and_runner_absent']
 assert len(old)==28 and len(new)==2 and original['known_numeric_controls_absent']==old
 extra=[r['pid'] for r in new]
 assert all(not Path('/proc',str(pid)).exists() for pid in extra)
 census=original['group_membership_observation'];assert not census['errors'] and not any(r['pgrp'] in extra for r in census['rows'])
 queries=[]
 for retained in review['fresh_current']['exact_new_container_queries']:
  argv=retained['argv'];child=subprocess.run(argv,capture_output=True,text=True,timeout=15)
  assert child.returncode==retained['returncode'] and not child.stderr
  if argv[4]=='inspect':
   values=json.loads(child.stdout);assert len(values)==1 and values[0]['Id']==review['container']
   assert values[0]['State']==review['positive_termination']['container_state']
   assert values[0]['State']['Running'] is False and values[0]['State']['Pid']==0 and values[0]['State']['ExitCode']==1 and values[0]['State']['OOMKilled'] is False
  else:assert child.stdout==retained['stdout']
  queries.append(dict(argv=argv,returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==3 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT37_FAILED113_RETAINED_CONTAINER_CURRENT_OBSERVATION_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root37=ref(LEDGER),accepted_failed_build_retirement=ref(FREE),original_observer=ref(BASE),original_observation=original,known_numeric_controls_absent=old+extra,new_build_actors_absent=new,group_membership_observation=census,retained_stopped_container=review['container'],retained_container_exit=1,exact_container_queries=queries,closed_exclusive_probes=original['closed_exclusive_probes'],artifact_acceptance=False,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
