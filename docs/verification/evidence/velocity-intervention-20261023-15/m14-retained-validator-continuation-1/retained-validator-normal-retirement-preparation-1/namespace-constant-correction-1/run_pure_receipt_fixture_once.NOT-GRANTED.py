"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted ordinary pure receipt fixture; no root/Docker/compiler/cleanup.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('owned',H)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
def limits():
 os.sched_setaffinity(0,{0})
 for kind,value in ((resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32*2**20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2*2**20)):
  resource.setrlimit(kind,(value,value))
C=D/'actual-pure-receipt-fixture-1'
C.mkdir(mode=0o700)
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_retained_validator_receipt.py')],'purpose':__doc__}
h.write(C/'command.json',command)
oldcwd=os.getcwd();signal.setitimer(signal.ITIMER_REAL,96)
try:
 os.chdir(D)
 result=h.owned_capture(command,C,90,limits)
finally:
 signal.setitimer(signal.ITIMER_REAL,0);os.chdir(oldcwd)
h.write(C/'WHOLE-JOIN.json',result)
print(json.dumps({k:result.get(k) for k in ('returncode','seconds','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out')},sort_keys=True))
if not(result['returncode']==0 and all(result[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and result['error'] is None and result['retirement_error'] is None and result['timed_out'] is False):raise SystemExit(1)
