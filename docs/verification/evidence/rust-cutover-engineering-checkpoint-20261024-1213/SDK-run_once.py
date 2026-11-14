"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import time
ENTRY_WALL=time.monotonic()
from pathlib import Path
import importlib.util,resource,hashlib,json,signal,os
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGALRM]:signal.signal(sig,h.stop)
assert os.getuid()==1000 and os.sched_getaffinity(0)=={7}
for key,val in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(key,(val,val))
os.environ['RUST_MIN_STACK']='2097152'
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
assert mem>=25501368320
S=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/retained-composite-consumer-1/run_retained_consumer_once.NOT-GRANTED.py')
assert hashlib.sha256(S.read_bytes()).hexdigest()=='09f80a774326ad474018a3cff4103163da3474ec14bf858838bce117b3eb498e'
command=dict(argv=['/home/holden/anaconda3/bin/python3', '-I', '-B', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/resource-parallelism/sdk-operation/inert-rust-boilerplate-correction-1/retained-composite-consumer-1/run_retained_consumer_once.NOT-GRANTED.py'],purpose=__doc__+' Complete retained SDK artifact/objtool graph consumer plus eight pure parser regressions; no build/objtool/container/guest execution.')
def budgets():
    cpu=h.cpu_used();wall=time.monotonic()-ENTRY_WALL
    assert cpu<=60 and wall<=90,(cpu,wall)
    return dict(CPU_seconds=cpu,wall_seconds=wall)
pre=budgets()
h.write(D/'ROOT-GRANT.json',dict(command=command,MemAvailable=mem,profile='CPU0ordinary/CPU7observer AS2GiB CPU60 wholewall90+6 F32 FD256 core0 bothstack2MiB; exact root SELF+CHILDREN/entrywall checked',source_consumer_review='m14_build_release_review PASS a6d968a5 with explicit root whole-budget closure',pre=pre))
signal.setitimer(signal.ITIMER_REAL,max(0.001,96-(time.monotonic()-ENTRY_WALL)))
r=h.owned_capture(command,D,90-(time.monotonic()-ENTRY_WALL),lambda:None)
h.write(D/'WHOLE-JOIN.json',r)
post=budgets()
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None
h.write(D/'ROOT-WHOLE-BUDGET-ACCEPTANCE.json',dict(status='PASS_WHOLE_JOB_BUDGET_AND_JOIN',pre=pre,post=post,scope=__doc__))
final=budgets()
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps(dict(returncode=r['returncode'],seconds=r['seconds'],budget=final,direct_child_joined=True,group_absent=True,closed_streams=True)))
