from pathlib import Path
import importlib.util,json,os,resource,time
N=Path(__file__).resolve().parent;O=N/'export-capture-1';O.mkdir(mode=0o700)
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['last_rate_limits']['primary']['usedPercent']<100 and state['phase']=='running' and state['stop_reason'] is None
sv=os.statvfs('/home/holden/mckernel-work/scratch');hv=os.statvfs(N);mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert hv.f_bavail*hv.f_frsize>=(16<<30)+(32<<20)+(640<<20) and sv.f_bavail*sv.f_frsize>=(12<<30)+(640<<20) and mem>=18<<30
cmd={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(N/'export.py')]}
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
begin=time.monotonic();r=m.owned_capture(cmd,O,33,limits);m.write(O/'whole.json',dict(record=r,elapsed_seconds=time.monotonic()-begin,scope='finite closed HOST66 evidence export only; no workloads'))
print(json.dumps(r));raise SystemExit(0 if r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] else 1)
