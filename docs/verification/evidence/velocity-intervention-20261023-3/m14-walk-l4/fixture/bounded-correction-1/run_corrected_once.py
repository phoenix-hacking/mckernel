"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,time
D=Path(__file__).resolve().parents[2];P=D/'fixture/bounded-correction-1/EXECUTABLE-READY.NOT-EXECUTED.json';W=D/'fixture'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='54de9766fabb6281e16e7773b70d6d11457d156cae83f0c40a063a6ad223ec5d';plan=json.loads(P.read_bytes())
for row in [plan['corrected_source'],plan['fixture_only_diff'],*plan['product_postimages_unchanged'],plan['product_patch']]:assert sha(Path(row['path']))==row['sha256']
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.umask(0o077);os.chdir(W);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'fixture/bounded-correction-1/actual-cohort-1';A.mkdir(mode=0o700)
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
facts={'memory_available':mem,'memory_required':19<<30,'host_available':host.f_bavail*host.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':scratch.f_bavail*scratch.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bs.st_size,'backing_dev':bs.st_dev,'backing_inode':bs.st_ino,'reserves_preserved':679477248}
c.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required']
frozen=[plan['corrected_source'],plan['fixture_only_diff'],*plan['product_postimages_unchanged'],plan['product_patch']]
for row in frozen:assert sha(Path(row['path']))==row['sha256']
frozen=frozen+[{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__).resolve()),'bytes':Path(__file__).stat().st_size}]
c.write(A/'FROZEN-SOURCES.json',frozen)
import sys
assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9),sys.version
c.write(A/'INTERPRETER-PREREQUISITE.json',{'executable':sys.executable,'version':sys.version,'capture_API':'owned_capture(dict,capture_dir,wall,preexec) imported full unchanged module with all required globals','before_first_child':True})
tools={}
for p in [Path('/home/holden/anaconda3/bin/python3').resolve(strict=True),Path('/usr/bin/gcc-9').resolve(strict=True)]:tools[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
c.write(A/'PROFILE.json',{'scope':__doc__,'root_grant':'Exact54de9766 CPU6 bounded correction four commands GCC9link/run/PUBLICfallbackheader, reused Rust object no rebuild or rehash; stop furtherfailure.','CPU':6,'jobs':1,'AS':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'tools':tools,'capture_helper_sha256':sha(H)})
obj=plan['Rust_object_durable_metadata']
def check_object():
 st=Path(obj['path']).stat()
 for key,value in [('device',st.st_dev),('inode',st.st_ino),('size',st.st_size),('mtime_ns',st.st_mtime_ns),('ctime_ns',st.st_ctime_ns),('uid',st.st_uid),('gid',st.st_gid),('nlink',st.st_nlink)]:assert obj[key]==value
check_object();c.write(A/'REUSED-RUST-OBJECT-STAT.json',{'object':obj,'not_rehashed':True,'no_Rust_recompile':True})
results=[];begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96)
try:
 for i,item in enumerate(plan['commands'],1):
  C=A/str(i);C.mkdir(mode=0o700);command={'argv':item['argv'],'purpose':__doc__+' '+item['role'],'cwd':str(W)};c.write(C/'command.json',command);remaining=90-(time.monotonic()-begin);assert remaining>0
  r=c.owned_capture(command,C,remaining,lambda:None);c.write(C/'whole-join.json',r);results.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out'],r
  if i==1:c.write(A/'DURABLE-FIXTURE-ELF.json',{'ELF':c.hashed(W/'bounded-correction-1/fixture',32<<20),'link_join':r,'durable_before_execution':True})
 text=(A/'2/stdout').read_text();assert text=='PASS 224 original-C/Rust pairs; actual production walk_pte_l4; callback ABI/order/mutations/errors; no callback retained\n',repr(text)
 assert all(sha(Path(row['path']))==row['sha256'] for row in frozen)
 check_object()
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_ORIGINAL_C_FULL_RUST_WALK_L4_224_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI','actual_pairs':224,'planned_pairs':224,'captures':results,'ready':{'path':str(P),'sha256':sha(P)},'Rust_object':obj,'fixture_ELF':json.loads((A/'DURABLE-FIXTURE-ELF.json').read_bytes())['ELF'],'CPU_seconds':c.cpu_used(),'CPU6_released':True,'compiler_invocations':0,'GCC_link_invocations':1,'GCC_header_syntax_invocations':2,'fixture_executions':1,'failed_candidates':1,'corrections':1,'qualifications':['No production source change; no fullcrate/defaultlink/native credit'],'callback_chain_C_debt':['clear_range_l4/l3/l2/l1/effect/log retained C callback chain'],'controlled_callback_qualification':'Controlled callback; actual production Rust walker and original C wrapper; no native callback-chain retirement','production_fullcrate_default_C_TU_link_native':'OPEN','canonical_frozen14_currentimage_changes':0};c.write(D/'fixture/bounded-correction-1/ACTUAL-CORRECTED-FIXTURE-RECEIPT.json',receipt);print(json.dumps({'status':receipt['status'],'actual_pairs':224,'seconds':[r['seconds'] for r in results],'CPU6_released':True}))
except BaseException as e:
 c.write(A/'FAILURE.json',{'scope':__doc__,'error':repr(e),'retained_completed_commands':len(results),'failure_family':'distinctwalk_l4 boundedcorrection after70ee28; furtherfailure expert STOP no retry','compiler_replay_authorized':False});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
