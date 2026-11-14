# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import importlib.util,json,subprocess,time,os
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-14/continuation-review/runtime-successor-3')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_capture',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
assert h.hashed(H,65536)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
r=json.loads((D/'ACTUAL-FINAL-SERIALIZATION-AND-REALCLOCK-CONSUMER.json').read_text())
assert r['status']=='PASS_PUBLISHED_FINAL_SERIALIZATION_AND_FULL_REALCLOCK_RELEASE_CONSUMER' and r['actual_published_request_pre_effect_consumer']=='PASS_ACTUAL_FINAL_SERIALIZED_REQUEST_PRE_EFFECT_GUARDS'
a=json.loads((D/'ROOT-ARGV.FINAL.NOT-EXECUTED.json').read_text());assert a[0:2]==['/usr/bin/sudo','-A'] and time.time()<r['expires_unix']
out=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-14/continuation-review/segment90-admission-finalization-preparation-1/runtime3-binding-1/actual-root-controller-outer-1');out.mkdir(mode=0o700)
h.write(out/'command.json',a)
streams=[]
for n in ('stdout','stderr'):
 fd=os.open(out/n,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);streams.append(os.fdopen(fd,'wb',buffering=0))
begin=time.monotonic();p=subprocess.Popen(a,stdin=subprocess.DEVNULL,stdout=streams[0],stderr=streams[1],start_new_session=True);birth=h.process_start(p.pid)
h.write(out/'started.json',dict(pid=p.pid,start=birth,expires_remaining=r['expires_unix']-time.time()))
print(json.dumps(dict(status='ROOT_CONTROLLER_STARTED',pid=p.pid,start=birth)),flush=True)
rc=p.wait()
for f in streams:f.close()
group=h.members(p.pid)
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',pid=p.pid,start=birth,returncode=rc,seconds=time.monotonic()-begin,direct_child_joined=True,group_absent=not group,remaining_group_members=group,closed_streams=True,outer_timeout=False,outer_signals=False,outer_kill=False,stdout=h.hashed(out/'stdout',384*2**20),stderr=h.hashed(out/'stderr',384*2**20))
h.write(out/'ACTUAL-CLOSED-CAPTURE.json',result);print(json.dumps(result),flush=True)
