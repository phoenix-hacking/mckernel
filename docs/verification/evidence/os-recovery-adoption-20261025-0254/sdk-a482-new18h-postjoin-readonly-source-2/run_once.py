"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One independently released root readonly normal-retirement postjoin, h990 capture only.
"""
from pathlib import Path
import importlib.util,hashlib,json,os,signal
D=Path(__file__).parent
P=D/'readonly_sdk_a482_normal_postjoin.py'
assert os.getuid()==os.geteuid()==1000
assert hashlib.sha256(P.read_bytes()).hexdigest()=='d50369a90b83dae2f6530d01ea04e19c3141b751eafeecc9ea3e06858ec67914'
profile=D/'EXACT-SDK-A482-NORMAL-POSTJOIN-READONLY-PROFILE.json'
assert hashlib.sha256(profile.read_bytes()).hexdigest()=='ef7ea750bbea4e6b1745f6f97dcb7223a3faeecc061b538e89dcf82bda8f4c69'
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('owned_capture_existing_h990',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
out=D/'actual-sdk-a482-new18h-postjoin-2';out.mkdir(mode=0o700)
argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(P)]
h.write(out/'EXACT-READONLY-ARGV.json',dict(scope=__doc__,argv=argv,reader_sha256='d50369a90b83dae2f6530d01ea04e19c3141b751eafeecc9ea3e06858ec67914',profile_sha256='ef7ea750bbea4e6b1745f6f97dcb7223a3faeecc061b538e89dcf82bda8f4c69',signals_to_owner=0,mutex_operations=0))
signal.setitimer(signal.ITIMER_REAL,66)
r=h.owned_capture(dict(argv=argv,purpose=__doc__),out,60,lambda:None)
h.write(out/'WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps(r,sort_keys=True));assert r['returncode']==0 and all(r[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None
print((out/'stdout').read_text())
