"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import importlib.util,hashlib,signal,json,sys
D=Path(__file__).parent
assert len(sys.argv)==2
assert len(sys.argv[1])==64 and all(c in '0123456789abcdef' for c in sys.argv[1])
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
C=D/'root-readonly-admission-capture-1';C.mkdir(mode=0o700)
command=dict(argv=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(D/'run_root_sdk_readonly_admission.py'),sys.argv[1]],purpose=__doc__+' Actual existing SDK readers and pinned image inspect only, no target execution or lease.')
signal.setitimer(signal.ITIMER_REAL,66);r=h.owned_capture(command,C,60,lambda:None);h.write(D/'ROOT-READONLY-ADMISSION-WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({k:r.get(k) for k in ['returncode','seconds','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out']}))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
