"""One proposed CPU6 grant: two exact no-effect actual-caller vectors."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,subprocess,time
D=Path(__file__).resolve().parent
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(S.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for number in m.STOP_SIGNALS:signal.signal(number,m.stop)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
assert state['phase']=='running' and state['stop_reason'] is None and state['last_rate_limits']['primary']['usedPercent']<100
scratch=Path('/home/holden/mckernel-work/scratch')
assert subprocess.run(['/usr/bin/findmnt','-n','-o','UUID','--target',str(scratch)],check=True,capture_output=True,text=True).stdout.strip()=='2a5768c8-718d-4914-bdc0-6b32c5a92a52'
for path,minimum in [(D,18887655424),(scratch,14026801152)]:
 v=os.statvfs(path);assert v.f_bavail*v.f_frsize>=minimum
assert int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=5<<30
O=D/'contract-check-capture-1';assert not os.path.lexists(O);O.mkdir(mode=0o700)
commands=json.loads((D/'CONTRACT-CHECK-PROPOSAL.json').read_bytes())['commands']
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(10,10));resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
records=[];begin=time.monotonic()
for i,argv in enumerate(commands):
 p=O/str(i);p.mkdir(mode=0o700);cmd=dict(argv=argv);m.write(p/'command.json',cmd)
 r=m.owned_capture(cmd,p,10,limits);records.append(r)
 if not(r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['error'] is None and r['retirement_error'] is None and r['captures']['stderr']['size']==0):break
ok=len(records)==len(commands) and all(r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['error'] is None and r['retirement_error'] is None and r['captures']['stderr']['size']==0 for r in records)
m.write(O/'whole.json',dict(records=records,elapsed_seconds=time.monotonic()-begin,status='PASS' if ok else 'FAIL',scope='Only exactactual LASTcaller sharedknownkindcontract positive/modeidentity-negative; no main/root/snapshot effects'))
print(json.dumps(dict(status='PASS' if ok else 'FAIL',commands=len(records),elapsed_seconds=time.monotonic()-begin)))
raise SystemExit(0 if ok else 1)
