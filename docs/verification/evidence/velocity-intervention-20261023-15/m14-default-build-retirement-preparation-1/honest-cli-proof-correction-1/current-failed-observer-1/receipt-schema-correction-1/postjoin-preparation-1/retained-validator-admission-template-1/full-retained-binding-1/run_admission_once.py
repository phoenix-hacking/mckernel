"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,signal,json
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
out=D/'actual-root-retained-admission-1';out.mkdir(mode=0o700)
signal.setitimer(signal.ITIMER_REAL,66)
r=h.owned_capture(json.loads((D/'EXACT-COMMAND.json').read_text()),out,60,lambda:None)
h.write(D/'ACTUAL-ADMISSION-WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({k:r.get(k) for k in ['returncode','seconds','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out']}))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
