"""One ordinary metadata child, accepted direct-join capture implementation."""
from pathlib import Path
import importlib.util
import json
import os
import resource
import subprocess
import time

D=Path(__file__).resolve().parent
O=D/'cli-check-1'
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_owned_capture',S)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.sched_getaffinity(0)=={6}
assert resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
assert state['phase']=='running' and state['stop_reason'] is None
assert state['last_rate_limits']['primary']['usedPercent']<100
scratch=Path('/home/holden/mckernel-work/scratch')
uuid=subprocess.run(['/usr/bin/findmnt','-n','-o','UUID','--target',str(scratch)],check=True,capture_output=True,text=True).stdout.strip()
assert uuid=='2a5768c8-718d-4914-bdc0-6b32c5a92a52'
# Retain the previous complete-image growth and emergency reservations, plus
# another 1MiB of bounded metadata; root separately admits concurrent growth.
for path,minimum in [(D,18886606848+(1<<20)),(scratch,14025752576+(1<<20))]:
    v=os.statvfs(path);assert v.f_bavail*v.f_frsize>=minimum
assert int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=5<<30
assert not O.exists();O.mkdir(mode=0o700)
cmd={'argv':['/home/holden/anaconda3/bin/python3.9','-I','-B',str(D/'check_machine_assembly_cli.py')]}
m.write(O/'command.json',cmd)
def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
begin=time.monotonic()
r=m.owned_capture(cmd,O,33,limits)
m.write(O/'whole.json',dict(record=r,elapsed_seconds=time.monotonic()-begin,
    scope='saved actual39cd physical adapter and coupled assembly body only; no live snapshot or guest'))
print(json.dumps(dict(returncode=r['returncode'],direct_child_joined=r['direct_child_joined'],
    group_absent=r['group_absent'],elapsed_seconds=time.monotonic()-begin)))
raise SystemExit(0 if r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['error'] is None and r['retirement_error'] is None and r['captures']['stderr']['size']==0 else 1)
