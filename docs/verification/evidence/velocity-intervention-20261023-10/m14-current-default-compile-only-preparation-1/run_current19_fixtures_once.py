"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Pure fake-backend consumer fixtures only."""
from pathlib import Path
import hashlib,importlib.util,json,os,signal,sys,time
D=Path(__file__).resolve().parent
PINS={'SOURCE-DELTA.AND-BINDINGS.NOT-EXECUTED.json': 'a428978be676a077651336950df25f1ba6bef9c754b6b8e466bbbcafe6fc92d4', 'compile_image_owner.py': '38f5b1aeafe507f36d88ab5b7caed44e289aa62f70749dead1a0d54c854dae4a', 'COMPILE-PROFILE.json': 'e2e6610e3d583f5a718e9f4b7cd7f2a53e4929fe00469226978c02ee76c0091b', 'compile-request.PREPARED.json': '15109f0f9518c29bcff1c029a59a0163298b97a812938a1326e83e8adbcf242e', 'test_compile_owner.py': 'eee51f34f08d7e2003fb3d4128608b5106021c6f84d8b70dc64f94a0931f5260'}
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.umask(0o077);os.chdir(D)
A=D/'actual-current19-fixtures-1';A.mkdir(mode=0o700)
r=None;begin=time.monotonic()
try:
 assert os.sched_getaffinity(0)=={0}
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for n,h in PINS.items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h,n
 cmd={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_compile_owner.py')],'cwd':str(D),'purpose':__doc__}
 c.write(A/'command.json',cmd);c.write(A/'SOURCE-PINS.json',PINS)
 signal.setitimer(signal.ITIMER_REAL,50)
 r=c.owned_capture(cmd,A,45,lambda:None);c.write(A/'ACTUAL-WHOLE-JOIN.json',r)
 assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None,r
 raw=(A/'stderr').read_bytes();assert b'Ran 19 tests' in raw and b'OK' in raw,raw
 for n,h in PINS.items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h,n
 out={'scope':__doc__,'status':'PASS_19_ACTUAL_CURRENT_COMPILE_ONLY_PURE_CONSUMER_FIXTURES','actual_tests':19,'whole_join':r,'CPU_seconds':c.cpu_used(),'wall_seconds':time.monotonic()-begin,'CPU0_released':True,'source_pins':PINS,'root_admission':None,'Docker_build_guest_execution':None,'engineering_percentage':None}
 c.write(A/'FINAL-ACTUAL-19-FIXTURE-RECEIPT.json',out);print(json.dumps(out))
except BaseException as e:
 c.write(A/'FAILURE.json',{'scope':__doc__,'error':repr(e),'whole_join':r,'STOP_no_retry':True,'CPU0_released':True});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
