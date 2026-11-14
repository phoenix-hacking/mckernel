"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted outer capture of the exact frozen937 argv; no retry.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal
P = Path(__file__).resolve().parent
assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
H = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('outercapture', H)
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(sig, cap.stop)
grant = json.loads((P/'ROOT-GRANTED-CWD-CORRECTION-EXECUTION-1.json').read_bytes())
os.umask(0o077)
A = P/'actual-root-granted-cwd-correction-outer-capture-1'
A.mkdir(mode=0o700)
os.environ['RUST_MIN_STACK'] = '2097152'
def limits():
    for key, value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:
        resource.setrlimit(key,(value,value))
limits()
command = dict(argv=grant['argv'],cwd=str(P),purpose=__doc__)
cap.write(A/'command.json', command)
cap.write(A/'GRANT-AND-SOURCE-BINDING.json',dict(grant=grant,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),driver_sha256=hashlib.sha256(Path(grant['argv'][-1]).read_bytes()).hexdigest(),OS_stack=resource.getrlimit(resource.RLIMIT_STACK),RUST_MIN_STACK=os.environ['RUST_MIN_STACK']))
row = cap.owned_capture(command,A,90,limits)
cap.write(A/'whole-join.json',row)
print(json.dumps(row))
raise SystemExit(0 if row['returncode'] == 0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None else 1)
