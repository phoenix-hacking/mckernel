"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fresh read-only native admission inputs; no container/guest creation or cleanup.
"""
from pathlib import Path
import json,os,time,subprocess,hashlib
A=Path(__file__).resolve().parent;E=A.parent
accept=E/'F03-F06-DEFAULT-NATIVE-ENTRY-CLEARANCE.json';d=json.loads(accept.read_bytes());assert d['decision']=='PASS_F03_F06_BUILD_POSTJOIN_CURRENT_PHYSICAL' and d['implementation_ownership'] is False
clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
assert all(c<e for c,e in zip(clocks,[1793100290,882395.5689528405,897734.6960034363]))
source=E/'ROOT-CURRENT290-NATIVE-FILES-ADMISSION-1/check_postnative_current.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='66fcc41a7e6c9be22d596efd2a3a19042aace8c351e74e21013b7de357466273'
r=subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',str(source)],capture_output=True,timeout=40)
assert r.returncode==0 and not r.stderr
(A/'FRESH-POSTNATIVE-READONLY.stdout').write_bytes(r.stdout);(A/'FRESH-POSTNATIVE-READONLY.stderr').write_bytes(r.stderr);current=json.loads(r.stdout)
# Bind exact accepted latest F02 actors and retained stopped CID, in addition
# to the unchanged prior-native owner/group/custody observer. No cleanup.
assert d['known_actors_absent'] is True and d['two_own_probe_FDs_closed'] is True and d['mount_UUID_floors_matched'] is True
oldraw=Path(d['actual_current']['path']).read_bytes();assert len(oldraw)==d['actual_current']['bytes'] and hashlib.sha256(oldraw).hexdigest()==d['actual_current']['sha256'];latest=json.loads(oldraw)
for actor in latest['retired_births']:
 assert actor['state']=='absent' and not Path('/proc',str(actor['pid'])).exists()
 assert not any(row['pid']==actor['pid'] or row['pgrp']==actor['pid'] for row in current['group_membership_observation']['rows'])
terminalraw=Path(d['terminal']['path']).read_bytes();assert len(terminalraw)==d['terminal']['bytes'] and hashlib.sha256(terminalraw).hexdigest()==d['terminal']['sha256'];terminal=json.loads(terminalraw)
assert terminal['container']==d['container_retained'] and terminal['state']['Running'] is False and terminal['state']['Pid']==0 and terminal['state']['ExitCode']==0

mem={}
for line in Path('/proc/meminfo').read_text().splitlines():
 k,v=line.split(':',1)
 if k in ['MemTotal','MemAvailable']:mem[k]=int(v.split()[0])*1024
assert mem['MemAvailable']>=24*2**30
paths=['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy','/sys/fs/cgroup/pids/mckernel-dev/pids.max']
cgroup={p:Path(p).read_text().strip() for p in paths};assert list(cgroup.values())==['100000','400000','12884901888','1','512']
pids=int(Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text());assert pids==0
docker_argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-q','--no-trunc']
docker_running=subprocess.run(docker_argv,capture_output=True,text=True,timeout=15)
assert docker_running.returncode==0 and not docker_running.stderr and not docker_running.stdout.strip()
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running'
raw=accept.read_bytes();acceptref=dict(path=str(accept),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
result=dict(scope=__doc__.splitlines()[0],observed_clocks=clocks,freshness_seconds_max=120,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),launcher_guard={k:state[k] for k in ['phase','thread_id','heartbeat_at','credit_budget','credit_budget_error','last_rate_limits']},actual_latest_F03_F06_postjoin_acceptance=acceptref,current_physical_observation=current,no_existing_heavy=True,running_container_observation=dict(argv=docker_argv,returncode=docker_running.returncode,stdout=docker_running.stdout,stderr=docker_running.stderr,positive_wait=True),active_shared_records_absent=True,capacity=current['capacity'],memory=mem,cgroup=cgroup,pids_current=pids,container_reservation=dict(cpus='2-5',jobs=4,RAM_bytes=12884901888,pids=512,swap_bytes=0),other_RAM_reserved_bytes=6442450944,aggregate_RAM_ceiling_GiB=21.7531,aggregate_jobs_max=7,fresh_directories=[])
static=json.loads((A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').read_bytes())
assert static['latest_serial_operation_physical_acceptance']==acceptref
for p in [A/'CAPTURE',Path(static['attempt_parent'])]:
 assert p.is_dir() and not list(p.iterdir());s=p.lstat();result['fresh_directories'].append(dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid))
print(json.dumps(result,indent=2))
