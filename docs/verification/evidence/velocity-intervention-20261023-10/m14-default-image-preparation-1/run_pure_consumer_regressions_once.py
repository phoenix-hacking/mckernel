"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,sys,time
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=D/'CURRENT-DRIVER-AND-PURE-TESTS.FINAL.READY-NOT-EXECUTED.json';assert sha(P)=='78b15a44c47665dc06be7a3a4f91b0611c5218a268958e03ad3b11ed75614117';plan=json.loads(P.read_bytes())
assert sha(Path(plan['tests']['path']))=='1e3479388b4c799bedf4a930cff6c37d2a75aee31674d5cb4b1de1c6be358f06'
assert sha(Path(plan['driver']['path']))==plan['driver']['sha256'];assert sha(Path(plan['current_owner']['path']))==plan['current_owner']['sha256']
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,c.stop)
os.umask(0o077);os.chdir(D);os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,8<<20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-pure-consumer-regressions-1';A.mkdir(mode=0o700);results=[]
try:
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 command={'argv':plan['argv'],'cwd':str(D),'purpose':__doc__+' Actual13 pureoffline currentdefault-image consumer regressions, no compiler/root/build.'}
 c.write(A/'command.json',command);c.write(A/'PROFILE.json',{'scope':__doc__,'root_grant':'ONE exact13pureoffline regression CPU0; no sourcecopy/compiler/imagebuild/root/guest','CPU':0,'jobs':1,'AS':512<<20,'CPU_seconds':10,'wall_seconds':15,'retire_seconds':6,'FSIZE':8<<20,'NOFILE':128,'core':0,'helper_sha256':sha(H),'ready':{'path':str(P),'sha256':sha(P)},'test_source':plan['tests'],'driver':plan['driver'],'owner':plan['current_owner'],'interpreter':{'path':sys.executable,'version':sys.version},'driver_source':{'path':str(Path(__file__)),'sha256':sha(Path(__file__))}})
 signal.setitimer(signal.ITIMER_REAL,21);r=c.owned_capture(command,A,15,lambda:None);results.append(r);c.write(A/'RESULT.json',r)
 assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None,r
 err=(A/'stderr').read_text();assert 'Ran 13 tests in ' in err and err.endswith('\nOK\n'),repr(err)
 assert sha(Path(plan['tests']['path']))==plan['tests']['sha256'] and sha(Path(plan['driver']['path']))==plan['driver']['sha256'] and sha(Path(plan['current_owner']['path']))==plan['current_owner']['sha256']
 out={'scope':__doc__,'status':'PASS_ACTUAL13_PURE_OFFLINE_CURRENT_DEFAULT_IMAGE_CONSUMER_REGRESSIONS_ONLY','actual_tests':13,'result':r,'CPU_seconds':c.cpu_used(),'CPU0_released':True,'compiler_sourcecopy_Docker_root_namespace_imagebuild_guest':False,'heavy_build_release':None,'default_link':None,'native':None,'old_failures_preserved':True};c.write(A/'FINAL-ACTUAL-PURE-REGRESSION-RECEIPT.json',out);print(json.dumps({'status':out['status'],'actual_tests':13,'seconds':r['seconds'],'CPU0_released':True}))
except BaseException as e:
 c.write(A/'FAILURE.json',{'scope':__doc__,'error':repr(e),'results':results,'CPU0_released':True,'STOP_no_retry':True});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
