"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite Root34 successor around the original reviewed current-availability observer.
No cleanup, release, workload, signals or new global observer implementation.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
LEDGER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER34.json')
FREE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json')
BASE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-final-ring-suffix-source-1/new12h-operation-preparation-1/resource-observer-window-correction-source-1/check_postnative_current_new12h.py')
REFS=[{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER34.json', 'bytes': 3677, 'sha256': 'c817825d68c8aa736acb9dbe05296b3dec9e40f574dc1a3bf7ef4bfa95bf8f88'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json', 'bytes': 63069, 'sha256': 'bf19e5a464ce05f49657acce7e598ce1125d8bf913c85631d5883190290e4890'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-final-ring-suffix-source-1/new12h-operation-preparation-1/resource-observer-window-correction-source-1/check_postnative_current_new12h.py', 'bytes': 8767, 'sha256': '2b7362126fbe70475a208e40df9eb56fa12df0993d83d0aa9b9a22a36638481c'}]

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def auth(row):assert ref(row['path'])==row;return Path(row['path'])
def observe():
 assert os.getuid()==os.geteuid()==1000
 for row in REFS:auth(row)
 ledger=read(LEDGER);review=read(FREE)
 assert ledger['latest_accepted_free_boundary']==ref(FREE)
 assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_ROOT4_NATIVE_OWNER_RETIREMENT_AND_CURRENT_FREE' and review['normal_owned_retirement'] is True and review['current_free'] is True
 retired=review['owned_client_retirement'];assert retired['count']==25 and retired['all_exact_reaped'] is True and len(retired['commands'])==25
 assert all(v['command']['reaped'] is True and v['command']['returncode']==v['returncode'] for v in retired['commands'].values())
 snapshot=read(auth(review['evidence']['retained_owner_and_guest_snapshot']))
 result=snapshot['owner_records']['result.json']
 assert result['status']=='FAIL' and result['absence_verified'] is True and result['lease_retained'] is False
 assert result['container']==review['container'] and result['secondary']==[]
 spec=importlib.util.spec_from_file_location('root34_unchanged_reviewed_baseline',BASE)
 baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
 physical=baseline.observe()
 # The original bounded global census and closed permanent-mutex probes are reused.
 absent=review['fresh_current']['all_owned_pids_and_groups_absent']
 assert len(absent)==28 and all(not Path('/proc',str(pid)).exists() for pid in absent)
 census=physical['group_membership_observation']
 assert not census['errors'] and not any(r['pgrp'] in absent for r in census['rows'])
 assert len(physical['closed_exclusive_probes'])==2
 queries=[]
 for retained in review['fresh_current']['container_queries']:
  argv=retained['argv']
  assert argv[0:4]==['sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
  child=subprocess.run(argv,capture_output=True,text=True,timeout=15)
  assert child.returncode==retained['returncode'] and child.stdout==retained['stdout'] and child.stderr==retained['stderr']
  queries.append(dict(argv=argv,returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==5 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT34_EXACT_POSTROOT4_CURRENT_OBSERVATION_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root34=ref(LEDGER),accepted_native_retirement=ref(FREE),exact25clients_reaped=True,exact_container_absent=review['container'],known_numeric_controls_absent=absent,group_membership_observation=census,closed_exclusive_probes=physical['closed_exclusive_probes'],lease_released_retained_result=result,docker_observations=queries,unchanged_reviewed_global_observer=ref(BASE),unchanged_baseline_observation=physical,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
