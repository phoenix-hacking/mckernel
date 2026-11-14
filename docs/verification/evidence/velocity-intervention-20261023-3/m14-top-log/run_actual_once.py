"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,time
D=Path(__file__).resolve().parent;P=D/'EXECUTABLE-FIXTURE-READY.NOT-EXECUTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='5154de10cf7bbba7a56b477039719b9a8ebea144c66d71937b618ec40ca19706';plan=json.loads(P.read_bytes())
for row in plan['sources']:assert sha(Path(row['path']))==row['sha256']
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.umask(0o077);os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-fixture-cohort-1';A.mkdir(mode=0o700)
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
facts={'memory_available':mem,'memory_required':19<<30,'host_available':host.f_bavail*host.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':scratch.f_bavail*scratch.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bs.st_size,'backing_dev':bs.st_dev,'backing_inode':bs.st_ino,'reserves_preserved':679477248}
c.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required']
sourcebindings=json.loads((D/'SOURCE-BINDINGS.PENDING.json').read_bytes());frozen=[]
for row in [*plan['sources'],*[r[k] for r in sourcebindings['changes'].values() for k in ('before','after')]]:
 assert sha(Path(row['path']))==row['sha256'];frozen.append(row)
frozen+=[{'path':str(D/'run_actual_once.py'),'sha256':sha(D/'run_actual_once.py'),'bytes':(D/'run_actual_once.py').stat().st_size}]
c.write(A/'FROZEN-SOURCES.json',frozen)
tools={}
for p in [Path(plan['commands'][0]['argv'][0]),Path('/usr/bin/gcc-9').resolve(strict=True)]:tools[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
c.write(A/'PROFILE.json',{'scope':__doc__,'root_grant':'Exact5154de10 one CPU6 sequential Rust1.92/GCC9 compile-link-run, no furtherjobs/defaultbuild/native grant.','CPU':6,'jobs':1,'AS':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'tools':tools,'capture_helper_sha256':sha(H)})
results=[];begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96)
try:
 for i,item in enumerate(plan['commands'],1):
  C=A/str(i);C.mkdir(mode=0o700);command={'argv':item['argv'],'purpose':__doc__+' '+item['role'],'cwd':str(D)};c.write(C/'command.json',command);remaining=90-(time.monotonic()-begin);assert remaining>0
  r=c.owned_capture(command,C,remaining,lambda:None);c.write(C/'whole-join.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out'],r
  if i==1:c.write(A/'DURABLE-RUST-OBJECT.json',{'object':c.hashed(D/'fixture-rust.o',32<<20),'compiler_join':r,'durable_before_link':True})
  if i==2:c.write(A/'DURABLE-FIXTURE-ELF.json',{'ELF':c.hashed(D/'fixture',32<<20),'link_join':r,'durable_before_execution':True})
 text=(A/'3/stdout').read_text();assert text=='PASS actual-original-C/full-Rust top-log pairs=179200 raw-varargs+format+vsnprintf+event-oracle\n',repr(text)
 assert all(sha(Path(row['path']))==row['sha256'] for row in frozen)
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_ORIGINAL_C_FULL_RUST_LOGGER_179200_PAIRS','actual_pairs':179200,'planned_pairs':plan['expected_pairs_NOT_ACTUAL'],'entry_routes':['event6invalid','event7allocationfailed','allotherdefaultsilent'],'source_bindings':{'path':str(D/'SOURCE-BINDINGS.PENDING.json'),'sha256':sha(D/'SOURCE-BINDINGS.PENDING.json')},'fixture_ready':{'path':str(P),'sha256':sha(P)},'captures':results,'Rust_object':json.loads((A/'DURABLE-RUST-OBJECT.json').read_bytes())['object'],'fixture_ELF':json.loads((A/'DURABLE-FIXTURE-ELF.json').read_bytes())['ELF'],'CPU_seconds':c.cpu_used(),'CPU6_released':True,'compiler_invocations':1,'GCC_link_invocations':1,'fixture_executions':1,'failed_candidates':0,'corrections':0,'qualifications':plan['limits'],'production_fullcrate_default_C_TU_link_native':'OPEN','canonical_frozen13_currentimage_changes':0};c.write(D/'ACTUAL-LOGGER-FIXTURE-RECEIPT.json',receipt);print(json.dumps({'status':receipt['status'],'actual_pairs':179200,'seconds':[r['seconds'] for r in results],'CPU6_released':True}))
except BaseException as e:
 c.write(A/'FAILURE.json',{'scope':__doc__,'error':repr(e),'retained_completed_commands':len(results),'failure_family':'distincttoplog firstcandidate; atmostoneboundedcorrection thenexpert','compiler_replay_authorized':False});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
