"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root fresh mock64 resource/admission data only. No Docker workload or release.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sys,time,subprocess
A=Path(__file__).resolve().parent;E=A.parent.parent.parent
sys.path.insert(0,str(A))
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import final_contract as mc
import final_owner as owner
OBSERVER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-F03-F06-RUSTMM-STRICT235-NATIVE-ADMISSION-1/check_postnative_current.py')
OBSERVER_SHA='9891cf1816c8639a8ca4a55e8ace130c049bd5ef65f1e126ef347353904be6fc'

def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--latest-postjoin',required=True);parser.add_argument('--latest-postjoin-sha256',required=True);args=parser.parse_args()
latest=Path(args.latest_postjoin);assert latest.is_absolute() and ref(latest)['sha256']==args.latest_postjoin_sha256
clocks=owner.check_campaign()
assert ref(OBSERVER)['sha256']==OBSERVER_SHA
spec=importlib.util.spec_from_file_location('accepted_current_native_observer',OBSERVER);obs=importlib.util.module_from_spec(spec);spec.loader.exec_module(obs);physical=obs.observe()
mem={line.split(':')[0]:int(line.split(':')[1].split()[0])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))}
assert mem['MemAvailable']>=24*2**30
cg={p:Path(p).read_text().strip() for p in ['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/pids/mckernel-dev/pids.max','/sys/fs/cgroup/pids/mckernel-dev/pids.current']}
assert list(cg.values())==['100000','400000','12884901888','512','0']
running=subprocess.run(['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-q','--no-trunc'],capture_output=True,text=True,timeout=15)
assert running.returncode==0 and not running.stdout.strip() and not running.stderr
request=json.loads((A/'ADOPT-REQUEST.json').read_text());ledger=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER25.json').read_text())
assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and request['nonce'] not in ledger['consumed_nonces']
publication=A/'ACTUAL-STATIC-SOURCE-PUBLICATION.json';assert publication.is_file()
root=OBSERVER.parent.parent
resources=dict(scope=__doc__.splitlines()[0],observed_clocks=clocks,boot_id=mc.BOOT,no_existing_heavy=True,physical_observer=ref(OBSERVER),current_physical_observation=physical,memory=mem,cgroups=cg,no_running_containers=dict(returncode=running.returncode,stdout=running.stdout,stderr=running.stderr),planned_profile=mc.PREP['profile'],nested_job_pids64_actual_proof='REQUIRED_DRIVER_BEFORE_THREE_CALLS_AND_AFTER_JOINS_NOT_YET_OBSERVED',other_reserved_memory_bytes=6*2**30,aggregate_ceiling_GiB=21.6619,CPU_eligible_count=7,nonce_ledger=ref('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER25.json'),account_guard='pinned new12h actual_account_window.guard called by owner.check_campaign',runtime_authority=None)
rp=A/'ROOT-FRESH-RESOURCE-PHYSICAL-1.json';write(rp,resources)
admission=json.loads((A/'CURRENT-ADMISSION.TEMPLATE.NOT-ACTUAL.json').read_text());admission.update(status='ROOT_RESERVED_DAEMON_PINNED_HELPER_SUFFIX64_SOLE_HEAVY',nonce=request['nonce'],request={k:v for k,v in ref(A/'ADOPT-REQUEST.json').items() if k!='bytes'},one_heavy=True,observed_clocks=clocks,expires_wall=min(clocks[0]+120,mc.CUTOFFS[0]),nonce_ledger_complete=True,consumed_nonces=ledger['consumed_nonces'],resource_physical=ref(rp),latest_postjoin_acceptance=ref(latest),source_publication=ref(publication))
ap=A/'CURRENT-ADMISSION.ACTUAL-1.json';write(ap,admission)
print(json.dumps(dict(status='ROOT_CURRENT_JOINED_SUFFIX64_RESERVATION_PENDING_EXECUTION_REVIEW',admission=ref(ap),observed_clocks=clocks,nonce=request['nonce'],workload_calls=0)))
