"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Minimal account/window successor of e8b84de3 ordinary admission; resources retained.
"""
import datetime,hashlib,importlib.util,json,os,time
from pathlib import Path
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py')
GUARD_SHA='1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
MIN_MEMORY=23357213694
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok,why):
 if not ok:raise ValueError(why)
def guard_module():
 need(hashlib.sha256(GUARD.read_bytes()).hexdigest()==GUARD_SHA,'reviewed v2 guard drift')
 spec=importlib.util.spec_from_file_location('ordinary_actual_guard_v2',GUARD)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def resource_checks(available,affinity,host_free,scratch_free,growth_reserve):
 need(affinity=={6},'exclusive hardCPU6 profile')
 # Preserve predecessor20GiB floor and stricter HOST19 outer admission floor.
 need(available>=20*2**30 and available>=MIN_MEMORY,'retained ordinary aggregate memory floor')
 need(host_free>=16*2**30+growth_reserve,'HOST16GiB plus full output reserve')
 need(scratch_free>=12*2**30,'scratch12GiB floor')
def admission(profile):
 g=guard_module();clocks=g.guard();cutoffs=g.current_cutoffs()
 need(all(now+90<end for now,end in zip(clocks,cutoffs)),'full ordinary90s before earliest inherited cutoff')
 state=json.loads(g.v1.STATE.read_bytes());account_wall=time.time()
 account_balance=g.check_account_state(state,account_wall)
 available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden/mckernel');scratch=os.statvfs('/home/holden/mckernel-work/scratch')
 hf=host.f_bavail*host.f_frsize;sf=scratch.f_bavail*scratch.f_frsize
 resource_checks(available,os.sched_getaffinity(0),hf,sf,profile['host_growth_reserve_bytes'])
 return dict(wall=clocks[0],monotonic=clocks[1],boottime=clocks[2],fixed_cutoffs=list(cutoffs),
  memory_available_bytes=available,aggregate_reserved_bytes=20*2**30,strict_memory_floor_bytes=MIN_MEMORY,
  host_free_bytes=hf,scratch_free_bytes=sf,budget=state['credit_budget'],heartbeat_at=state['heartbeat_at'],
  phase=state['phase'],account_wall=account_wall,
  heartbeat_age_seconds=account_wall-datetime.datetime.fromisoformat(state['heartbeat_at']).timestamp(),
  available_prepaid_balance=str(account_balance),spendControlReached=state['last_rate_limits'].get('spendControlReached'),
  loadavg=os.getloadavg(),CPU_affinity=sorted(os.sched_getaffinity(0)))
