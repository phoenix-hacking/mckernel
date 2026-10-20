from pathlib import Path
import importlib.util,json,os,resource,time,hashlib
D=Path(__file__).resolve().parent;O=D/'check-1'
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['last_rate_limits']['primary']['usedPercent']<100 and state['phase']=='running' and state['stop_reason'] is None
sv=os.statvfs('/home/holden/mckernel-work/scratch');hv=os.statvfs(D);mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert hv.f_bavail*hv.f_frsize>=(16<<30)+(128<<20)+(640<<20) and sv.f_bavail*sv.f_frsize>=(12<<30)+(640<<20) and mem>=18<<30
raw=Path('/home/holden/mckernel-work/host-preparation/current-v6-composite-native-probe-20261020-1/failure-classification-1/trace-reproducer-1/current-raw.bin').read_bytes();assert len(raw)==79295 and hashlib.sha256(raw).hexdigest()=='a11eddb148e2a9d34281d3e239b56b4081e1f2bf75696c121e405bed467eb721'
assert not O.exists();O.mkdir(mode=0o700);vectors=O/'vectors';vectors.mkdir(mode=0o700)
common=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_CORE_THREADS']
commands=[('compile-actual-body-fixture',common+[str(D/'test_failure_export.c'),'-o',str(O/'fixture')],10),('actual-body-fixture',[str(O/'fixture'),str(vectors),'/home/holden/mckernel-work/host-preparation/current-v6-composite-native-probe-20261020-1/failure-classification-1/trace-reproducer-1/current-raw.bin'],10),('compile-current-collector',common+['-static','-DND_PAIR_LAUNCH_EXPANSION',str(D/'candidate/pair_collector.c'),'-o',str(O/'collector')],10)]
records=[];begin=time.monotonic()
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
for label,argv,wall in commands:
 p=O/label;p.mkdir(mode=0o700);m.write(p/'command.json',{'argv':argv});r=m.owned_capture({'argv':argv},p,wall,limits);records.append(r)
 if r['returncode']!=0 or not r['direct_child_joined'] or not r['group_absent'] or m.cpu_used()>30 or time.monotonic()-begin>30:break
ok=len(records)==3 and all(r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] for r in records)
if ok:(O/'collector').chmod(0o700)
m.write(O/'whole.json',dict(status='PASS_CURRENT_COLLECTOR_AND_EXACT_FAILURE_EXPORT_BODY' if ok else 'FAIL_STOP_PRESERVE',records=records,elapsed_seconds=time.monotonic()-begin,CPU_seconds=m.cpu_used(),guest_runs=0))
print(json.dumps(dict(status='PASS' if ok else 'FAIL',records=len(records),elapsed_seconds=time.monotonic()-begin)));raise SystemExit(0 if ok else 1)
