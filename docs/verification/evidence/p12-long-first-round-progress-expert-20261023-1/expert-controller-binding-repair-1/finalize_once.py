# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,subprocess,time,os,resource,importlib.util
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_capture',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
assert h.hashed(H,65536)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
template=D/'finalization-readiness-1/FINAL-ATTACH-APPROVED-REVIEW.COMMAND.json'
assert h.hashed(template,65536)['sha256']=='c41d8abd67b557e90c4184c83205dd31e6bb39fafa0370a396f1db8ffab97ba4'
a=json.loads(template.read_text())['argv'];a[-5:]=[str(D/'ROOT-PRE-REVIEW-PAYLOAD.json'),'727348b74955ad27f0c378a026869ff3225fd9d984b0823bb22c7a9ca32523c0',str(D/'APPROVED-INDEPENDENT-REVIEW.json'),'/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/expert-controller-binding-repair-1/admission-preparation-1/authenticated-admission-readback-1/stdout','ea295d6ccf3ccd58ea1109b5badb3a9a8e3e583147c6e23ef9d42101f9f02dff']
out=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/expert-controller-binding-repair-1/actual-finalization-capture-1');out.mkdir(mode=0o700);h.write(out/'command.json',a)
def limits():
 os.sched_setaffinity(0,{0})
 for k,v in [(resource.RLIMIT_AS,2147483648),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
streams=[]
for n in ('stdout','stderr'):
 fd=os.open(out/n,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);streams.append(os.fdopen(fd,'wb',buffering=0))
begin=time.monotonic();p=subprocess.Popen(a,stdin=subprocess.DEVNULL,stdout=streams[0],stderr=streams[1],start_new_session=True,preexec_fn=limits);birth=h.process_start(p.pid);rc=p.wait()
for f in streams:f.close()
group=h.members(p.pid);r=dict(returncode=rc,pid=p.pid,start=birth,seconds=time.monotonic()-begin,direct_child_joined=True,group_absent=not group,closed_streams=True,outer_timeout=False,outer_signals=False,outer_kill=False,stdout=h.hashed(out/'stdout',33554432),stderr=h.hashed(out/'stderr',33554432));h.write(out/'ACTUAL-CLOSED-CAPTURE.json',r);print(json.dumps(r));print((out/'stdout').read_text());print((out/'stderr').read_text());assert rc==0 and not group
