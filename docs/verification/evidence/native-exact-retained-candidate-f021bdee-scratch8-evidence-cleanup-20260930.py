#!/usr/bin/env python3
"""Disjoint c658-style exact-evidence cleanup plan for stopped f021bdee.

This fresh packet delegates only the already-reviewed fail-closed cleanup and
census implementation.  It is audit-only unless an operator explicitly asks
for plan publication or apply; all current f021 build inputs remain protected.
"""
import argparse, importlib.util, os, json
from pathlib import Path

REPO=Path('/home/holden/mckernel')
BASE_PATH=REPO/'docs/verification/evidence/native-exact-retained-candidate-c658175a-evidence-cleanup-20260930.py'
spec=importlib.util.spec_from_file_location('reviewed_cleanup',BASE_PATH)
BASE=importlib.util.module_from_spec(spec); spec.loader.exec_module(BASE)

CANDIDATE_COMMIT='f021bdee206944fc9c68a3f1f2e0f6683a849435'
CANDIDATE_ROOT=Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-f021bdee-scratch-8')
CANDIDATE_IDENTITY='1831:5242921'
LIVE_SCRATCH=Path('/home/holden/mckernel-work/scratch')
LIVE_PATHS=[LIVE_SCRATCH/'native-exact-build-output-f021bdee-scratch-8',LIVE_SCRATCH/'native-exact-build-evidence-f021bdee-scratch-8',LIVE_SCRATCH/'native-exact-build-request-f021bdee-scratch-8.json',LIVE_SCRATCH/'native-exact-inputs-f021bdee-scratch-8.json',LIVE_SCRATCH/'native-exact-candidate-preparation-f021bdee-scratch-8-terminal.json',LIVE_SCRATCH/'native-exact-candidate-preparation-f021bdee-scratch-8.log',LIVE_SCRATCH/'native-exact-metadata-backup-f021bdee-scratch-8',LIVE_SCRATCH/'native-exact-metadata-evidence-f021bdee-scratch-8',LIVE_SCRATCH/'native-exact-candidate-operational-exclusion-selfdigest-13.json']
LIVE_CANDIDATE=CANDIDATE_ROOT
LIVE_FAILURE=REPO/'docs/verification/evidence/native-exact-build-f021bdee-scratch8-export-allowlist-failure-20260930.json'
LIVE_EVIDENCE=LIVE_PATHS[1]; LIVE_OUTPUT=LIVE_PATHS[0]; PROTECTED_LIVE_EXCLUSION=LIVE_PATHS[-1]
PROTECTED_CONTAINER={"id":"b34323f6c4352e8bae669d006e11076a64a5734ed165a6ce866bd4e7aa04c001","name":"mckernel-exact-d01624939ead44118fc2352bc4d83860","state":"exited","exit_code":1}
EXPECTED_SCRATCH_MOUNT=["/dev/loop39","ext4","7:39","/home/holden/mckernel-work/scratch"]

for name,value in {'CANDIDATE_COMMIT':CANDIDATE_COMMIT,'CANDIDATE_ROOT':CANDIDATE_ROOT,'CANDIDATE_IDENTITY':CANDIDATE_IDENTITY,'REPO':REPO,'LIVE_SCRATCH':LIVE_SCRATCH,'LIVE_CANDIDATE':LIVE_CANDIDATE,'LIVE_FAILURE':LIVE_FAILURE,'LIVE_EVIDENCE':LIVE_EVIDENCE,'LIVE_OUTPUT':LIVE_OUTPUT,'PROTECTED_LIVE_EXCLUSION':PROTECTED_LIVE_EXCLUSION}.items(): setattr(BASE,name,value)
BASE.EXPECTED_IDENTITIES={}; BASE.EXPECTED_DEVICES={}

def live_guard(root):
    root=Path(root).resolve(strict=True)
    for p in LIVE_PATHS+[LIVE_FAILURE]:
        q=Path(p).resolve(strict=False)
        if q==root or root in q.parents or q in root.parents: BASE.die('retained root overlaps protected f021 input')
    for p in LIVE_PATHS:
        if os.path.lexists(p) and p.is_symlink(): BASE.die('protected f021 input is linked')
BASE.live_guard=live_guard

_BASE_AUDIT=BASE.audit
_BASE_VALIDATE=BASE.validate_census
def validate_census(census):
    actual=[x.split() for x in census['mount_device'].get('output','').splitlines() if x.strip() and not x.startswith('SOURCE')]
    if census['mount_device'].get('returncode') != 0 or len(actual)!=1 or actual[0][:4] != EXPECTED_SCRATCH_MOUNT:
        BASE.die('unexpected nested mount/device')
    # Reuse the proven evaluator for all non-mount safety dimensions.
    shadow=dict(census); shadow['mount_device']={'returncode':0,'output':'SOURCE FSTYPE MAJ:MIN TARGET\n/dev/nvme0n1p2 ext4 259:2 /\n','stderr':''}
    return _BASE_VALIDATE(shadow)
BASE.validate_census=validate_census

def audit(root=CANDIDATE_ROOT,repo=REPO,commit=CANDIDATE_COMMIT):
    if Path(root) != CANDIDATE_ROOT or Path(repo) != REPO or commit != CANDIDATE_COMMIT:
        BASE.die('wrong f021 audit binding')
    result=_BASE_AUDIT(root,repo,commit)
    result['protected_f021_runtime']={'paths':[str(p) for p in LIVE_PATHS],'container':PROTECTED_CONTAINER}
    return result
BASE.audit=audit
def apply(plan): return BASE.apply(plan)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--plan',required=True); ap.add_argument('--apply',action='store_true'); ap.add_argument('--write-plan',action='store_true'); a=ap.parse_args()
    result=apply(json.loads(Path(a.plan).read_text())) if a.apply else audit()
    if a.write_plan: BASE.atomic_write(a.plan,result)
    print(json.dumps(result,sort_keys=True)); return 0
if __name__=='__main__': main()
