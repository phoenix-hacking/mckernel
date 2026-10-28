"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Original normal Resource2 API adapter to exact reviewed postcompose observer.
No grant/native entry. Original identity/output/guard/floor/cgroup/directory checks retained.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
A=Path(__file__).resolve().parent
OBSERVER_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-1/BOUND-CURRENT-OBSERVER.SOURCE-ONLY.py', 'bytes': 12927, 'sha256': '5ad7fe19d614c8f61c33cf140215b9e5d1cdf9686e8365d8a327126136093d4f'}
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py')
GUARD_SHA='1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(r,name):
 assert ref(r['path'])==r
 spec=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 a=argparse.ArgumentParser();a.add_argument('--output-path',required=True,type=Path);out=a.parse_args().output_path
 assert out.is_absolute() and out.parent==A
 stdout=out.with_name(out.stem+'.PHYSICAL.stdout');stderr=out.with_name(out.stem+'.PHYSICAL.stderr')
 for p in [out,stdout,stderr]:assert not os.path.lexists(p),str(p)
 with out.open('xb') as result,stdout.open('xb') as raw,stderr.open('xb') as errors:
  assert os.getuid()==os.geteuid()==1000 and OBSERVER_REF is not None
  st=json.loads((A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').read_bytes())
  assert st['expected_case']=='P-M06-01-process-exec-wait-235B'
  assert st['expected_guest_argv']==['/bin/mcexec','-t','1','0','/apps/app']
  assert st['current_observer_source']==OBSERVER_REF
  for r in st['capture_sources'].values():assert ref(r['path'])==r
  assert ref(GUARD)['sha256']==GUARD_SHA
  guard=load(ref(GUARD),'literal_earliest_v2_guard_native235');first=guard.guard()
  observer=load(OBSERVER_REF,'literal_reviewed_current235_observer');physical=observer.observe()
  assert physical['Root57']==st['root_ledger35'] and physical['actual_latest_operation_postjoin_acceptance']==st['latest_serial_operation_physical_acceptance']
  assert physical['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' and physical['no_existing_heavy'] is True and physical['pids_current']==0 and physical['active_shared_records_absent'] is True
  assert len(physical['closed_exclusive_probes'])==2 and not physical['group_membership_observation']['errors']
  raw.write((json.dumps(physical,indent=2)+'\n').encode())
  memory={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:'))}
  assert memory['MemAvailable']>=24*2**30
  paths=['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy','/sys/fs/cgroup/pids/mckernel-dev/pids.max']
  cgroup={p:Path(p).read_text().strip() for p in paths};assert list(cgroup.values())==['100000','400000','12884901888','1','512']
  pids=int(Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text());assert pids==0
  directories=[]
  for p in [A/'CAPTURE',Path(st['attempt_parent'])]:
   assert p.is_dir() and not list(p.iterdir());info=p.lstat();directories.append(dict(path=str(p),device=info.st_dev,inode=info.st_ino,mode=info.st_mode,uid=info.st_uid,gid=info.st_gid))
  cutoffs=guard.current_cutoffs();assert all(a<b for a,b in zip(guard.guard(),cutoffs))
  value=dict(scope=__doc__.splitlines()[0],observed_clocks=first,fixed_cutoffs=list(cutoffs),freshness_seconds_max=120,boot_id=guard.BOOT,root_ledger35=st['root_ledger35'],actual_latest_operation_postjoin_acceptance=st['latest_serial_operation_physical_acceptance'],current_physical_observation=physical,
   no_existing_heavy=True,running_container_observation=physical['running_container_observation'],retained_stopped_observation=physical['retained_stopped_observation'],active_shared_records_absent=True,capacity=physical['capacity'],memory=memory,cgroup=cgroup,pids_current=pids,container_reservation=dict(cpus='2-5',jobs=4,RAM_bytes=12884901888,pids=512,swap_bytes=0,network='none'),other_RAM_reserved_bytes=6442450944,aggregate_RAM_ceiling_GiB='21.6619',aggregate_jobs_max=7,fresh_directories=directories,native_acceptance=False)
  result.write((json.dumps(value,indent=2)+'\n').encode())
 print(json.dumps(dict(status='ACTUAL_FRESH_ORIGINAL235_RESOURCE_CAPTURE_NOT_EXECUTION_RELEASE',resource=ref(out))))
if __name__=='__main__':main()
