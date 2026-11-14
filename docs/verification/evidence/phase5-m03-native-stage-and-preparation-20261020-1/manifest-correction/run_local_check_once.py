from pathlib import Path
import importlib.util,json,os,resource,time
D=Path(__file__).resolve().parent;O=D/'local-check-capture-1'
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running' and state['stop_reason'] is None and state['last_rate_limits']['primary']['usedPercent']<100
for path,floor in [(D,16<<30),(Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 v=os.statvfs(path);assert v.f_bavail*v.f_frsize>=floor+(512<<20)
assert int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=2<<30
assert not O.exists() and not (D/'LOCAL-CHECK-RESULT.json').exists();O.mkdir(mode=0o700)
for name in ['manifest.json','stage-result.json','COMPLETION-RESULT.json']:assert not (D/name).exists()
cmd={'argv':['/home/holden/anaconda3/bin/python3.9','-I','-B',str(D/'check_existing.py')]};m.write(O/'command.json',cmd)
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
begin=time.monotonic();r=m.owned_capture(cmd,O,33,limits);m.write(O/'whole.json',dict(record=r,elapsed_seconds=time.monotonic()-begin,scope='actual retained archive/full canonical manifest validation +2negatives only; no metadata completion or recompression'))
print(json.dumps(dict(returncode=r['returncode'],direct_child_joined=r['direct_child_joined'],group_absent=r['group_absent'],elapsed_seconds=time.monotonic()-begin)))
raise SystemExit(0 if r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['error'] is None and r['retirement_error'] is None and r['captures']['stderr']['size']==0 else 1)
