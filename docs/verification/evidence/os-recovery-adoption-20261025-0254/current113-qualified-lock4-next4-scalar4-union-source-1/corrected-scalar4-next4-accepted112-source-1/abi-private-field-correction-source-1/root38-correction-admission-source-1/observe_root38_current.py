"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow Root38 wrapper preserves Root37 failed-container contract and adds exactV3.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
LEDGER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER38.json')
FREE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-root37-1/independent-actual-native-review-1/REVIEW.json')
BASE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1/root37-correction-admission-source-1/observe_root37_current.py')
REFS=[{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER38.json', 'bytes': 4390, 'sha256': '9b3d64ab84d59b6abbc7b1df05cf4034a9d53a2dd1cfb4d76013f554f0b7e282'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-root37-1/independent-actual-native-review-1/REVIEW.json', 'bytes': 63017, 'sha256': '9d3aa7ff83c3bec493a575a8035ce59963e92fb2a82d549febd89ab34c8ce066'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1/root37-correction-admission-source-1/observe_root37_current.py', 'bytes': 5380, 'sha256': '8cbc47cdfb9c0fdcfdc82093a4a99fa506c791683aee5dc7725fcaa367c1ddbf'}]

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def observe():
 assert os.getuid()==os.geteuid()==1000
 for r in REFS:auth(r)
 ledger=read(LEDGER);review=read(FREE)
 assert ledger['latest_accepted_free_boundary']==ref(FREE) and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_F05_V3_PRE_GUEST_FAILED_BATCH_RETIREMENT_AND_CURRENT_FREE' and review['normal_owned_retirement'] is True and review['current_free'] is True
 clients=review['owned_client_retirement'];assert clients['count']==25 and clients['all_exact_reaped'] is True and len(clients['commands'])==25
 assert all(row['command']['reaped'] is True and row['command']['returncode']==row['returncode'] for row in clients['commands'].values())
 snapshot=read(auth(review['evidence']['RETAINED-OWNER-SNAPSHOT.json']));result=snapshot['owner_records']['result.json']
 assert result['status']=='FAIL' and result['absence_verified'] is True and result['lease_retained'] is False and result['secondary']==[] and result['container']==review['container']
 spec=importlib.util.spec_from_file_location('root38_retained_root37_observer',BASE)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.observe()
 # Prior28controls+two failedbuild actors and retained363375Exit1 remain distinct.
 assert len(original['known_numeric_controls_absent'])==30 and original['retained_container_exit']==1
 actors=review['fresh_current']['all_28_owned_pids_and_groups_absent'];assert len(actors)==28 and actors[:3]==[1735781,1735836,1735840]
 assert all(not Path('/proc',str(pid)).exists() for pid in actors)
 census=original['group_membership_observation'];assert not census['errors'] and not any(row['pgrp'] in actors for row in census['rows'])
 queries=[]
 for retained in review['fresh_current']['container_queries']:
  child=subprocess.run(retained['argv'],capture_output=True,text=True,timeout=15)
  assert child.returncode==retained['returncode'] and child.stdout==retained['stdout'] and child.stderr==retained['stderr']
  queries.append(dict(argv=retained['argv'],returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==5 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT38_V3_PRE_GUEST_FAILED_RETIREMENT_CURRENT_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root38=ref(LEDGER),accepted_V3_retirement=ref(FREE),original_observer=ref(BASE),original_Root37_observation=original,known_numeric_controls_absent=original['known_numeric_controls_absent']+actors,group_membership_observation=census,closed_exclusive_probes=original['closed_exclusive_probes'],new_V3_25_clients_reaped=True,new_V3_exact_container_absent=review['container'],new_V3_actor_controls=actors,new_V3_queries=queries,retained_failed113_container=original['retained_stopped_container'],retained_failed113_container_exit=1,artifact_acceptance=False,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
