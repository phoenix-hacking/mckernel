"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse the exact v2 observer before holder acquisition, then bind fresh held facts.
No compiler/configure/guest/cleanup, holder creation, grant publication or retry.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,time
D=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/TEST_ONLY-full-recursion-xn7f2vld/prepared/cohort/runtime_guard.py')
GUARD_SHA='599be0e3f296467a58fd11323c6b1e09937d2b8bfc0ccfc11a11e5ca79270192'
BOUNDARY=D/'ROOT-ACTUAL-CURRENT-BOUNDARY.json'
AGGREGATE=23259332608
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(path):return json.loads(Path(path).read_bytes())
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 assert ref(row['path'])==row,'exact current input reference'
 return Path(row['path'])
def write(path,value):
 with Path(path).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def load(path,sha,name):
 assert ref(path)['sha256']==sha,'pinned reviewed helper'
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module
def valid_resource_facts(memory,capacity,other_memory,other_pids,aggregate_pids,threads,thread_limit):
 assert type(other_memory) is int and other_memory>=0 and other_memory+(12<<30)<=AGGREGATE
 assert memory['MemAvailable']>=max(22<<30,other_memory+(16<<30))
 assert capacity['host']>=16<<30 and capacity['scratch']>=14091616256
 assert all(type(v) is int and v>=0 for v in [other_pids,aggregate_pids,threads,thread_limit])
 assert other_pids+512<=aggregate_pids<=thread_limit and threads+other_pids+512<=thread_limit
 return True
def execute(args):
 assert os.getuid()==os.geteuid()==1000
 boundary=read(BOUNDARY)
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 for key in ['nonce_ledger','native_custody_clearance','observer','independent_current_boundary_review']:auth(boundary[key])
 OBSERVER=Path(boundary['observer']['path']);OBSERVER_SHA=boundary['observer']['sha256']
 guard=load(GUARD,GUARD_SHA,'current110_reviewed_v2_guard');clocks=guard.guard()
 if args.physical_output:
  output=Path(args.physical_output);assert output.is_absolute() and not output.exists()
  observer=load(OBSERVER,OBSERVER_SHA,'current110_reused_current_physical_observer')
  physical=observer.observe()  # Its free-mutex probes require this BEFORE holder setup.
  after=guard.guard()
  write(output,dict(scope=SCOPE,status='ACTUAL_CURRENT110_PHYSICAL_OBSERVATION_PENDING_ROOT_ACCEPTANCE',
   runtime_authority=None,current_boundary=ref(BOUNDARY),guard=ref(GUARD),observer=ref(OBSERVER),observed_clocks=after,
   first_observed_clocks=clocks,physical=physical,native_acceptance=False))
  print(json.dumps(dict(status='PHYSICAL_OBSERVATION_ONLY_NO_HOLDER_OR_RELEASE',observation=ref(output))))
  return
 root=Path(args.admission);assert root.is_absolute() and root.parent==E and root.name.startswith('ROOT-') and root.resolve(strict=True)==root
 inputs=read(args.root_input)
 assert inputs['author']=='/root' and inputs['decision']=='BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES'
 assert inputs['maximum_invocations']==1 and inputs['root_attests_only_intervening_holder_preparation'] is True
 assert inputs['profile']==ref(root/'PROFILE.SOURCE-ONLY.json')
 profile=read(auth(inputs['profile']));assert profile['runtime_authority'] is None and profile['request_sha256']==inputs['request_sha256']
 request=read(auth(inputs['request']));assert request['nonce']==inputs['nonce'] and request['request_sha256']==inputs['request_sha256']
 ledger=read(auth(inputs['nonce_ledger']))
 assert inputs['nonce_ledger']==boundary['nonce_ledger'] and inputs['current_boundary']==ref(BOUNDARY)
 assert inputs['native_custody_clearance']==boundary['native_custody_clearance']
 assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert inputs['nonce'] not in ledger['consumed_nonces']
 publication=read(auth(inputs['source_publication']));assert publication['runtime_authority'] is None
 physical_ref=inputs['physical_observation'];physical=read(auth(physical_ref))
 assert physical['status']=='ACTUAL_CURRENT110_PHYSICAL_OBSERVATION_PENDING_ROOT_ACCEPTANCE'
 assert physical['guard']==ref(GUARD) and physical['observer']==ref(OBSERVER) and physical['current_boundary']==ref(BOUNDARY)
 assert 0<=clocks[0]-physical['observed_clocks'][0]<=120,'fresh physical observation, never renewed'
 assert inputs['native_custody_clearance']==profile['native_custody_clearance'];auth(inputs['native_custody_clearance'])
 ready=read(root/'HOLDER/HOLDER.READY.json');bootstrap=read(root/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
 assert ready['status']=='ACTUAL_ONE_HEAVY_27_4_HELD_NOT_BUILD_ADMISSION'
 assert ready['nonce']==bootstrap['nonce']==inputs['nonce']
 assert bootstrap['author']=='/root' and bootstrap['maximum_invocations']==1
 assert bootstrap['decision']=='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER'
 assert bootstrap['profile']==inputs['profile'] and bootstrap['runner']==inputs['runner'] and bootstrap['worker']==inputs['worker']
 assert bootstrap['source']==ref(root/'hold_and_run_build_only.py') and ready['bootstrap']==ref(root/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
 holder=ready['holder'];assert (holder['device'],holder['inode'])==(27,4)
 current=int((Path('/proc')/str(holder['pid'])/'stat').read_text().rsplit(')',1)[1].split()[19]);assert current==holder['starttime']
 assert (os.stat(holder['path']).st_dev,os.stat(holder['path']).st_ino)==(27,4)
 locks=Path('/proc/locks').read_text()
 assert any(len(v)>=8 and v[1:4]==['FLOCK','ADVISORY','WRITE'] and v[4]==str(holder['pid']) and v[5:8]==['00:1b:4','0','EOF'] for v in (line.split() for line in locks.splitlines()))
 memory={line.split(':')[0]:int(line.split(':')[1].split()[0])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))}
 capacity={key:os.statvfs(path).f_bavail*os.statvfs(path).f_frsize for key,path in [('host','/home/holden/mckernel'),('scratch','/home/holden/mckernel-work/scratch')]}
 threads=int(Path('/proc/loadavg').read_text().split()[3].split('/')[1]);limit=int(Path('/proc/sys/kernel/threads-max').read_text())
 valid_resource_facts(memory,capacity,inputs['other_reserved_memory_bytes'],inputs['other_reserved_pids'],inputs['aggregate_pid_budget'],threads,limit)
 cgpaths=['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/pids/mckernel-dev/pids.max','/sys/fs/cgroup/pids/mckernel-dev/pids.current']
 cgroups={p:Path(p).read_text().strip() for p in cgpaths};assert list(cgroups.values())==['100000','400000','12884901888','512','0']
 argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-q','--no-trunc']
 query=subprocess.run(argv,capture_output=True,text=True,timeout=15);assert query.returncode==0 and not query.stdout.strip() and not query.stderr
 runner=load(root/'run_build_only.py',inputs['runner']['sha256'],'current110_held_source_map_reader')
 assert inputs['runner']==ref(root/'run_build_only.py') and inputs['worker']==ref(root/'build_only_worker.py')
 runner.commands_for_plan(profile)
 source_rows=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in profile['inputs']['postimages']]+[r['postimage'] for r in runner.source_directory_postimages(profile)]
 assert len(runner.source_directory_postimages(profile))==121
 for row in source_rows:auth(row)
 export=read(auth(inputs['input_export_authority']));assert export['qualified_readonly_files']==source_rows and export['request_sha256']==profile['request_sha256']
 assert not (root/'OUTPUT').exists()
 clocks=guard.guard()
 # Root's actual bounded input supplies authority; observations supply only facts.
 resource=dict(author='/root',runtime_authority='ONE_BUILD_ONLY_RESOURCE_RESERVATION',scope=SCOPE,
  nonce=inputs['nonce'],observed_at_epoch=clocks[0],observed_clocks=clocks,
  cpus=[2,3,4,5],heavy_slots_held=1,other_heavy_slots=0,reservation_owner=inputs['nonce'],
  cpu_reservation_held=True,reservation_holder=holder,container_memory_bytes=12<<30,container_pids=512,
  aggregate_memory_budget_bytes=AGGREGATE,other_reserved_memory_bytes=inputs['other_reserved_memory_bytes'],
  other_reserved_pids=inputs['other_reserved_pids'],aggregate_pid_budget=inputs['aggregate_pid_budget'],
  coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY',native_custody_unchanged=True,
  native_custody_clearance=inputs['native_custody_clearance'],reservation_ready_record=ref(root/'HOLDER/HOLDER.READY.json'),
  reservation_kind='PERMANENT_27_4_ONE_HEAVY_AFTER_CLEARANCE',fresh_output_root=str(root/'OUTPUT'),
  host_required_free_bytes=16<<30,scratch_required_free_bytes=14091616256,
  actual_observations=dict(memory=memory,capacity=capacity,cgroups=cgroups,host_threads=threads,thread_limit=limit,
   lock_rows=locks,no_running_containers=dict(argv=argv,returncode=query.returncode,stdout=query.stdout,stderr=query.stderr),
   physical_observation=physical_ref,exact_v2_account_guard=ref(GUARD),Root_resource_input=ref(args.root_input)))
 rp=root/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json';write(rp,resource)
 grant=dict(author='/root',decision='GRANT_ONE_CURRENT290_BUILD_ONLY',maximum_invocations=1,nonce=inputs['nonce'],
  runner=inputs['runner'],worker=inputs['worker'],profile=inputs['profile'],review=None,resource_authority=ref(rp),
  input_export_authority=inputs['input_export_authority'],fresh_output_root=str(root/'OUTPUT'),
  native_custody_clearance=inputs['native_custody_clearance'],docker_client_prefix=profile['docker_client_prefix'],root_docker_client_only=True)
 gp=root/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json';write(gp,grant)
 print(json.dumps(dict(status='ACTUAL_CURRENT110_HELD_RESOURCE_PENDING_INDEPENDENT_EXECUTION_REVIEW',resource=ref(rp),pending_input=ref(gp),runtime_release=False)))
def main():
 parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True)
 mode.add_argument('--physical-output');mode.add_argument('--root-input');parser.add_argument('--admission')
 args=parser.parse_args()
 if args.root_input:assert args.admission,'actual Root admission path required'
 execute(args)
if __name__=='__main__':main()
