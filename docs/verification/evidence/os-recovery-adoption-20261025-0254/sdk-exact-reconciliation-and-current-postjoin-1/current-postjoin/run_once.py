"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One independently released root readonly held-owner preflight, h990 capture only.
"""
from pathlib import Path
import importlib.util,hashlib,json,os,signal
D=Path(__file__).parent
P=D/'readonly_sdk_after_reconciliation_current_free.py'
assert os.getuid()==os.geteuid()==1000
assert hashlib.sha256(P.read_bytes()).hexdigest()=='91fe27238de060a85037ad6feb4d1f1a52d535ae0b152a0315fa0c7a7da24a34'
profile=D/'EXACT-SDK-POST-RECONCILIATION-CURRENT-FREE-READONLY-PROFILE.json'
assert hashlib.sha256(profile.read_bytes()).hexdigest()=='35edb7296b3e82b9b57ed952d775ebd4727181432c78b6b072fcf57f4ac2e5d2'
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('owned_capture_existing_h990',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
out=D/'actual-post-reconciliation-current-free-1';out.mkdir(mode=0o700)
argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(P)]
h.write(out/'EXACT-READONLY-ARGV.json',dict(scope=__doc__,argv=argv,reader_sha256='91fe27238de060a85037ad6feb4d1f1a52d535ae0b152a0315fa0c7a7da24a34',profile_sha256='35edb7296b3e82b9b57ed952d775ebd4727181432c78b6b072fcf57f4ac2e5d2',signals_to_owner=0,mutex_operations=0))
signal.setitimer(signal.ITIMER_REAL,66)
r=h.owned_capture(dict(argv=argv,purpose=__doc__),out,60,lambda:None)
h.write(out/'WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps(r,sort_keys=True));assert r['returncode']==0 and all(r[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None
print((out/'stdout').read_text())
