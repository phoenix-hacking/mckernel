"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,sys,time
D=Path(__file__).resolve().parent;P=D/'EXECUTABLE-READY.NOT-EXECUTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='17bc54c7c056c0aa85c9e9e9b6832c7b346fab11c9e1c967e78151adfd14fcd3'
plan=json.loads(P.read_bytes())
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)==plan['capture_helper_sha256']
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.umask(0o077);os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-VM-fixture-capture-1';A.mkdir(mode=0o700);results=[];durable={};begin=time.monotonic()
try:
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for row in plan['frozen_inputs']:assert sha(Path(row['path']))==row['sha256'],row['path']
 c.write(A/'FROZEN-INPUTS.json',plan['frozen_inputs']);c.write(A/'DRIVER-INTERPRETER.json',{'driver':{'path':str(Path(__file__)),'sha256':sha(Path(__file__))},'executable':sys.executable,'version':sys.version,'before_child':True})
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 facts={'memory_available':mem,'memory_required':19<<30,'host_available':host.f_bavail*host.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':scratch.f_bavail*scratch.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bs.st_size,'reserves_preserved':679477248,'CPU':6,'root_grant_required':True}
 c.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required'],facts
 (D/'output-1').mkdir(mode=0o700);c.write(A/'PROFILE.json',dict(plan['profile'],CPU=6));signal.setitimer(signal.ITIMER_REAL,96)
 for i,item in enumerate(plan['commands']):
  C=A/str(i);C.mkdir(mode=0o700);command={'argv':item['argv'],'purpose':item['purpose'],'cwd':item['cwd']};c.write(C/'command.json',command);remaining=90-(time.monotonic()-begin);assert remaining>0
  r=c.owned_capture(command,C,remaining,lambda:None);c.write(C/'whole-join.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None,r
  if i in (0,1,2,3):
   name={0:'fixture-rust.o',1:'fixture-c.o',2:'memset.o',3:'fixture'}[i];durable[name]=c.hashed(D/'output-1'/name,32<<20);c.write(A/('DURABLE-'+name+'.json'),durable[name])
 assert (A/'4/stdout').read_text()=='PASS VM fault-PTE=1944 node=324 exact original-C/default-Rust trace/log/output/error pairs\n'
 for row in plan['frozen_inputs']:assert sha(Path(row['path']))==row['sha256'],row['path']
 for name,m in durable.items():
  st=Path(m['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(m[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_TWO_VM_PUBLIC_ENTRIES_2268_ORIGINAL_C_RUST_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI','actual_pairs':2268,'faultPTE':1944,'NUMAnode':324,'captures':results,'durable_objects':durable,'CPU_seconds':c.cpu_used(),'wall_seconds':time.monotonic()-begin,'CPU6_released':True,'qualifications':plan['qualifications'],'production_fullcrate_GCC14_defaultlink_native':'OPEN','canonical_writes':0,'all13_tests_replayed':False}
 c.write(A/'FINAL-ACTUAL-VM-FIXTURE-RECEIPT.json',receipt);print(json.dumps({'status':receipt['status'],'actual_pairs':2268,'commands':len(results),'wall_seconds':receipt['wall_seconds'],'CPU6_released':True}))
except BaseException as e:
 c.write(A/'FAILURE.json',{'scope':__doc__,'error':repr(e),'captures':results,'durable_objects':durable,'CPU6_released':True,'first_unexpected_STOP':True,'no_retry':True});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
