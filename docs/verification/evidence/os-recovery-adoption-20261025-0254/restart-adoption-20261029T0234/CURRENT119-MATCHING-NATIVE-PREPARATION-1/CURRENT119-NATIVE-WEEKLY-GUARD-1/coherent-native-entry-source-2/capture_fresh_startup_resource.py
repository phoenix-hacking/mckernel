"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Original normal Resource2 API adapter to exact reviewed postcompose observer.
No grant/native entry. Original identity/output/guard/floor/cgroup/directory checks retained.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
A=Path(__file__).resolve().parent
OBSERVER_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/CURRENT119-NATIVE-WEEKLY-GUARD-1/post119-resource-successor-source-1/accepted-current-physical-source-1/observe_current119_native_resources.py', 'bytes': 14062, 'sha256': '335e82f3e1a2c0a88d50fcdd1d1410aeb8881d2b07f95dbb0b6057488c641171'}  # Exact unbound source; review remains mandatory
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/CURRENT119-NATIVE-WEEKLY-GUARD-1/native_operation_guard.py')
GUARD_SHA='1f89fba32c016346cec9f11ae96fe1e4b0c5e781c307c34bda646ab7c05f92e4'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(r,name):
 assert ref(r['path'])==r
 spec=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_post119_route(st, context, review):
 # No observation is made here: Root must bind a separately reviewed fresh observer.
 assert st['root_ledger35']==context['current_ledger']
 assert st['latest_serial_operation_physical_acceptance']==context['post119_current_free']
 assert st['current_boundary']==context['current_boundary']
 assert review['decision']=='PASS_EXACT_CURRENT119_RESOURCE_OBSERVER_SOURCE_BINDING' and review['independent'] is True and review['implementation_ownership'] is False
 assert review['observer']==st['current_observer_source'] and review['current_ledger']==context['current_ledger'] and review['current_free']==context['post119_current_free'] and review['current_boundary']==context['current_boundary']
 assert review['complete_actual_actor_frontier'] is True and review['original_resource_lock_holder_cgroup_checks_preserved'] is True and review['runtime_authority'] is None

def validate_post119_physical(context, physical):
 assert physical['current_ledger']==context['current_ledger'] and physical['current_boundary']==context['current_boundary'] and physical['actual_latest_operation_postjoin_acceptance']==context['post119_current_free']
 assert physical['complete_actual_actor_frontier'] is True and physical['native_acceptance'] is False and physical['runtime_authority'] is None

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
  _,_,context,_=guard.binding_metadata(guard.read(guard.ref(guard.BINDING)))
  review=guard.read(st['current_observer_review'])
  validate_post119_route(st,context,review)
  observer=load(OBSERVER_REF,'literal_reviewed_current119_resource_observer');physical=observer.observe()
  validate_post119_physical(context,physical)
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
