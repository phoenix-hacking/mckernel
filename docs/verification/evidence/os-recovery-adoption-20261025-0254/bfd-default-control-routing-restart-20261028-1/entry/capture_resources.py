"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
BFD readonly capture producer. CPU0/2GiB/60CPU; owner positively joins finite child.
"""
from pathlib import Path
import argparse,importlib.util,json,os,resource,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from handoff_common import *
D=Path(__file__).resolve().parent

def load(r,n):
 p=verify_ref(r);s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def guard(b):
 g=load(b['guard_facade'],'BFD_capture_guard');g.configure(b['guard_configuration']);return g

def physical_value(b,physical,first,last):
 fragment=read_json_ref(b['contract'])['Root61_observer_fragment']
 need(physical['Root61']==fragment['current_ledger'] and physical['actual_latest_operation_postjoin_acceptance']==fragment['latest_free'],'genuine Root61/6c83 physical consumer shape')
 need(physical['status']=='PASS_Root61_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE' and physical['current_boundary']==fragment['current_ledger'],'exact35d5 field contract')
 need(physical['pids_current']==0 and physical['no_existing_heavy'] is True and physical['active_shared_records_absent'] is True and physical['boot_id']==BOOT,'physical exclusion/boot')
 need(len(physical['closed_exclusive_probes'])==2 and physical['permanent_mutex']==dict(device=27,inode=4,regular=True,no_kernel_lock_row=True),'positive closed mutex probes')
 in_window(last,b['authorized_cutoffs'])
 return dict(scope=SCOPE,status='ACTUAL_BFD_ROOT61_PREHOLDER_PHYSICAL_PENDING_INDEPENDENT_REVIEW',runtime_authority=None,current_boundary=fragment['current_ledger'],observer=b['observer_source'],guard=b['guard_facade'],observed_clocks=last,first_observed_clocks=first,physical=physical,native_acceptance=False)

def held_values(b,inputs,physical,ready,bootstrap,observed,now):
 A=Path(b['admission']);p=read_json_ref(b['static_refs']['profile']);pins=read_json_ref(b['contract'])['Root61_observer_fragment']
 need(inputs['author']=='/root' and inputs['decision']=='BIND_BFD_ACTUAL_HELD_BUILD_RESOURCES' and inputs['maximum_invocations']==1 and inputs['root_attests_only_intervening_holder_preparation'] is True and inputs['actual_reservations_attested'] is True,'Root exact bounded held reservations')
 need(inputs['nonce']==ready['nonce']==bootstrap['nonce']==b['nonce'] and inputs['profile']==b['static_refs']['profile'] and inputs['nonce_ledger']==pins['current_ledger'] and inputs['native_custody_clearance']==p['native_custody_clearance']==pins['latest_free'],'exact nonce/profile/Root61/free6c83')
 need(inputs['fresh_output_root']==p['actual_output_root'] and bootstrap['native_custody_clearance']==pins['latest_free'],'exact frozen output/current custody')
 ledger=read_json_ref(pins['current_ledger']);need(inputs['nonce'] not in ledger['consumed_nonces'] and ledger['current_physical_clearance_pending'] is False,'unused Root nonce and adopted currentfree')
 need(ready['status']=='ACTUAL_ONE_HEAVY_27_4_HELD_NOT_BUILD_ADMISSION' and ready['bootstrap']==inputs['holder_bootstrap'],'actual holder/bootstrap')
 for k,name in [('source','holder_source'),('runner','runner'),('worker','worker'),('profile','profile')]:need(bootstrap[k]==b['static_refs'][name],'bootstrap exact '+k)
 need(bootstrap['author']=='/root' and bootstrap['decision']=='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER' and bootstrap['maximum_invocations']==1,'exact holder-only grant')
 h=ready['holder'];need(h['fd']==3 and (h['device'],h['inode'])==(27,4),'actual permanent27:4/FD3')
 need(observed['holder_start']==h['starttime'] and observed['holder_fd_device_inode']==[27,4],'actual live birth/FD')
 owners=[v for v in (s.split() for s in observed['lock_rows'].splitlines()) if len(v)>=8 and v[5]=='00:1b:4'];need(len(owners)==1 and owners[0][1:5]==['FLOCK','ADVISORY','WRITE',str(h['pid'])] and owners[0][6:8]==['0','EOF'],'sole fullEOF holder')
 need(inputs['physical_observation']==observed['physical_ref'] and physical['observer']==b['observer_source'] and physical['current_boundary']==pins['current_ledger'],'exact physical/source/current joins')
 need(physical['observed_clocks'][0]<=inputs['at_epoch']<=now[0] and 0<=now[0]-physical['observed_clocks'][0]<=120,'actual physical→Rootinput→held ordering and120s')
 need(observed['memory']['MemAvailable']>=max(22<<30,inputs['other_reserved_memory_bytes']+(16<<30)) and observed['capacity']['host']>=16<<30 and observed['capacity']['scratch']>=14091616256,'actual memory/storage floors')
 need(observed['no_running_containers']['returncode']==0 and observed['no_running_containers']['stdout']==observed['no_running_containers']['stderr']=='','no running Docker')
 need(observed['cgroups']=={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us':'100000','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us':'400000','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes':'12884901888','/sys/fs/cgroup/pids/mckernel-dev/pids.max':'512','/sys/fs/cgroup/pids/mckernel-dev/pids.current':'0'},'exact reviewed cgroups')
 in_window(now,b['authorized_cutoffs'])
 resource=dict(author='/root',runtime_authority='ONE_BUILD_ONLY_RESOURCE_RESERVATION',scope=SCOPE,nonce=b['nonce'],observed_at_epoch=now[0],observed_clocks=now,cpus=[2,3,4,5],heavy_slots_held=1,other_heavy_slots=0,reservation_owner=b['nonce'],cpu_reservation_held=True,reservation_holder=h,container_memory_bytes=12<<30,container_pids=512,aggregate_memory_budget_bytes=p['aggregate_memory_budget_bytes'],other_reserved_memory_bytes=inputs['other_reserved_memory_bytes'],other_reserved_pids=inputs['other_reserved_pids'],aggregate_pid_budget=inputs['aggregate_pid_budget'],coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY',native_custody_unchanged=True,native_custody_clearance=pins['latest_free'],reservation_ready_record=inputs['holder_ready'],reservation_kind='PERMANENT_27_4_ONE_HEAVY_AFTER_CLEARANCE',fresh_output_root=inputs['fresh_output_root'],host_required_free_bytes=16<<30,scratch_required_free_bytes=14091616256,actual_observations=dict(observed,Root_resource_input=inputs['_input_ref']))
 pending=dict(author='/root',decision='GRANT_ONE_BFD_CURRENT_DEFAULT_BUILD_ONLY',maximum_invocations=1,nonce=b['nonce'],runner=b['static_refs']['runner'],worker=b['static_refs']['worker'],profile=b['static_refs']['profile'],review=None,resource_authority=None,input_export_authority=b['static_refs']['input_export'],fresh_output_root=inputs['fresh_output_root'],native_custody_clearance=pins['latest_free'],docker_client_prefix=p['docker_client_prefix'],root_docker_client_only=True)
 return resource,pending

def execute(args):
 need(os.getuid()==os.geteuid()==1000,'UID1000 capture')
 os.sched_setaffinity(0,{0});resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30));resource.setrlimit(resource.RLIMIT_CPU,(60,60));need(os.sched_getaffinity(0)=={0},'CPU0 capture enforced')
 b=read_json(D/'SEALED-ENTRY-BINDINGS.json');g=guard(b);first=g.guard()
 if args.physical_output:
  observer=load(b['observer_source'],'BFD_current61_physical');physical=observer.observe();last=g.guard();value=physical_value(b,physical,first,last);atomic_json(Path(args.physical_output),value);return
 A=Path(args.admission);need(str(A)==b['admission'],'actual frozen BFD cohort only');no_launch(A)
 inputs=read_json(args.root_input);inputs['_input_ref']=reference(Path(args.root_input));physical=read_json_ref(inputs['physical_observation']);ready=read_json_ref(inputs['holder_ready']);bootstrap=read_json_ref(inputs['holder_bootstrap'])
 p=read_json_ref(b['static_refs']['profile']);runner=load(b['static_refs']['runner'],'BFD_actual_unchanged_runner');runner.commands_for_plan(p);runner.verify_bfd_source_export(p)
 h=ready['holder'];z=(Path('/proc')/str(h['pid'])/'fd/3').stat()
 memory={r.split(':')[0]:int(r.split(':')[1].split()[0])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith(('MemAvailable:','MemTotal:'))}
 capacity={k:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for k,p in [('host','/home/holden/mckernel'),('scratch','/home/holden/mckernel-work/scratch')]}
 cg=['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/pids/mckernel-dev/pids.max','/sys/fs/cgroup/pids/mckernel-dev/pids.current']
 import subprocess
 argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-q','--no-trunc'];query=subprocess.run(argv,capture_output=True,text=True,timeout=15)
 observed=dict(holder_start=birth(h['pid']),holder_fd_device_inode=[z.st_dev,z.st_ino],memory=memory,capacity=capacity,cgroups={p:Path(p).read_text().strip() for p in cg},lock_rows=Path('/proc/locks').read_text(),host_threads=int(Path('/proc/loadavg').read_text().split()[3].split('/')[1]),thread_limit=int(Path('/proc/sys/kernel/threads-max').read_text()),no_running_containers=dict(argv=argv,returncode=query.returncode,stdout=query.stdout,stderr=query.stderr),physical_ref=inputs['physical_observation'],capture_profile=dict(affinity=sorted(os.sched_getaffinity(0)),AS_bytes=resource.getrlimit(resource.RLIMIT_AS)[0],CPU_seconds=resource.getrlimit(resource.RLIMIT_CPU)[0]))
 now=g.guard();r,pending=held_values(b,inputs,physical,ready,bootstrap,observed,now)
 rp=atomic_json(A/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json',r);pending['resource_authority']=rp;atomic_json(A/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json',pending)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--physical-output');group.add_argument('--root-input');p.add_argument('--admission');execute(p.parse_args())
