# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import importlib.util,subprocess,os,time,resource,json
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/qmp-runtime-successor-1')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_capture',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
assert h.hashed(H,65536)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
a=['/usr/bin/sudo','-A','/usr/bin/cat',str(D/'actual-capture-1/started.json')]
out=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/qmp-runtime-successor-1/finalization-preparation-1/authenticated-started-read-1');out.mkdir(mode=0o700)
h.write(out/'command.json',a)
def limits():
 os.sched_setaffinity(0,{7})
 for k,v in [(resource.RLIMIT_AS,2147483648),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
streams=[]
for n in ('stdout','stderr'):
 fd=os.open(out/n,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);streams.append(os.fdopen(fd,'wb',buffering=0))
begin=time.monotonic();p=subprocess.Popen(a,stdin=subprocess.DEVNULL,stdout=streams[0],stderr=streams[1],start_new_session=True,preexec_fn=limits);birth=h.process_start(p.pid);rc=p.wait()
for f in streams:f.close()
group=h.members(p.pid);r=dict(returncode=rc,pid=p.pid,start=birth,seconds=time.monotonic()-begin,direct_child_joined=True,group_absent=not group,closed_streams=True,outer_timeout=False,outer_signals=False,outer_kill=False,stdout=h.hashed(out/'stdout',33554432),stderr=h.hashed(out/'stderr',33554432));h.write(out/'ACTUAL-CLOSED-CAPTURE.json',r);print(json.dumps(r))
if rc==0:print((out/'stdout').read_text())
