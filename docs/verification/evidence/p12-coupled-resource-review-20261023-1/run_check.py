"""Fixed ordinary coupled-consumer check; uses accepted direct-join capture helper."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, time
D=Path(__file__).resolve().parent
P=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(P.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted_capture',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert os.sched_getaffinity(0)=={0}
assert resource.getrlimit(resource.RLIMIT_AS)==(512*2**20,512*2**20)
assert resource.getrlimit(resource.RLIMIT_CPU)==(20,20)
assert resource.getrlimit(resource.RLIMIT_FSIZE)==(8*2**20,8*2**20)
assert resource.getrlimit(resource.RLIMIT_NPROC)==(126258,126258)
O=D/'ordinary-check-3';O.mkdir(mode=0o700)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,m.stop)
signal.setitimer(signal.ITIMER_REAL,25)
start=time.monotonic()
command={'argv':['/usr/bin/python3','-I','-B',str(D/'check_coupled.py'),str(O/'fixture')]}
record=m.owned_capture(command,O,25,lambda:None)
signal.setitimer(signal.ITIMER_REAL,0)
assert sum(p.stat().st_size for p in O.rglob('*')if p.is_file())<=32*2**20
ok=(record['returncode']==0 and record['direct_child_joined'] and record['group_absent']and record['closed_streams'] and not record['timed_out']and not record['error']and not record['retirement_error']and record['captures']['stderr']['size']==0)
value={'status':'PASS_COUPLED_CONSUMER_NO_NATIVE' if ok else 'FAIL_PRESERVE_FIRST','record':record,'seconds':time.monotonic()-start,'native_acceptance':False,'runtime_release':'NOT_RELEASED'}
m.write(O/'receipt.json',value);print(json.dumps({'status':value['status'],'seconds':value['seconds']}))
raise SystemExit(0 if ok else 1)
