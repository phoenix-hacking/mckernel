"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,sys,time
D=Path(__file__).resolve().parent.parent;P=D/'sourcehandoff/EXECUTABLE-READY.NOT-EXECUTED.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='12557b00ab25e0959dabeffd82c99cf9089fe2ce5d30a506451ca6dfbc8e57fd'
plan=json.loads(P.read_bytes())
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert sha(H)==plan['profile']['helper_sha256']
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.umask(0o077);os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-fixture-cohort-1';A.mkdir(mode=0o700);results=[];begin=time.monotonic()
try:
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 c.write(A/'INTERPRETER.json',{'path':sys.executable,'version':sys.version,'before_child':True})
 hp=Path(plan['header67_authority']['path']);assert sha(hp)==plan['header67_authority']['sha256'];headers=json.loads(hp.read_bytes())
 frozen=plan['sources']+plan['canonical_preimages']+plan['Rust_public_provider_sources']+list(headers['actual_header_closure'].values())
 for row in frozen:assert sha(Path(row['path']))==row['sha256'],row['path']
 assert sha(Path('/usr/bin/gcc-9'))==headers['tools']['/usr/bin/gcc-9']['sha256']
 c.write(A/'FROZEN-SOURCES.json',frozen);c.write(A/'DRIVER.json',{'path':str(Path(__file__)),'sha256':sha(Path(__file__))})
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 facts={'memory_available':mem,'memory_required':19<<30,'host_available':host.f_bavail*host.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':scratch.f_bavail*scratch.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bs.st_size,'backing_dev':bs.st_dev,'backing_inode':bs.st_ino,'reserves_preserved':679477248,'CPU':6,'root_grant':'exclusive CPU6 onejob eight sequential commands; no competing CPU6 grant'}
 c.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required'],facts
 (D/'output-1').mkdir(mode=0o700)
 c.write(A/'PROFILE.json',{'scope':__doc__,'CPU':6,'AS':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE':32<<20,'NOFILE':256,'core':0,'stack':2097152,'helper_sha256':sha(H),'Rust':{'path':plan['commands'][0]['argv'][0],'sha256':sha(Path(plan['commands'][0]['argv'][0]))}})
 signal.setitimer(signal.ITIMER_REAL,96)
 for i,item in enumerate(plan['commands'],1):
  C=A/str(i);C.mkdir(mode=0o700);command={'argv':item['argv'],'purpose':item['purpose'],'cwd':item['cwd']};c.write(C/'command.json',command)
  remaining=90-(time.monotonic()-begin);assert remaining>0
  r=c.owned_capture(command,C,remaining,lambda:None);c.write(C/'whole-join.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out'],r
  if i==1:c.write(A/'DURABLE-RUST-OBJECT.json',{'object':c.hashed(D/'output-1/fixture-rust.o',32<<20),'compiler_join':r,'before_link':True})
  if i==4:c.write(A/'DURABLE-FIXTURE-ELF.json',{'ELF':c.hashed(D/'output-1/fixture',32<<20),'link_join':r,'before_execution':True})
 assert (A/'5/stdout').read_text()=='PASS direct=819 actual-array-handler=1120 invalid=5 original-C/Rust provider pairs; no completion except real handler decrement\n'
 pp=(A/'8/stdout').read_text()
 for name in plan['targets']:
  import re
  assert not re.search(r'\b'+name+r'\([^;{}]*\)\s*\{',pp),name
 for row in frozen:assert sha(Path(row['path']))==row['sha256'],row['path']
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_1944_ORIGINAL_C_RUST_CALLBACK_PAIRS_PUBLIC_FALLBACK_HEADER_ABI_AND_DEFAULT_C_BODY_EXCLUSION','ready':{'path':str(P),'sha256':sha(P)},'actual_pairs':1944,'direct':819,'actual_array_handler':1120,'invalid':5,'captures':results,'Rust_object':json.loads((A/'DURABLE-RUST-OBJECT.json').read_bytes())['object'],'fixture_ELF':json.loads((A/'DURABLE-FIXTURE-ELF.json').read_bytes())['ELF'],'CPU_seconds':c.cpu_used(),'wall_seconds':time.monotonic()-begin,'CPU6_released':True,'qualifications':plan['fixture_qualifications'],'remaining_C_callback_debt':plan['remaining_C_callback_debt'],'default_production_link_native':'OPEN','canonical_writes':0}
 c.write(A/'FINAL-ACTUAL-FIXTURE-RECEIPT.json',receipt);print(json.dumps({'status':receipt['status'],'commands':len(results),'actual_pairs':1944,'wall_seconds':receipt['wall_seconds'],'CPU6_released':True}))
except BaseException as e:
 c.write(A/'FAILURE.json',{'scope':__doc__,'error':repr(e),'completed_captures':len(results),'captures':results,'CPU6_released':True,'first_unexpected_failure_STOP':True,'no_retry':True});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
