"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact78-input production Rust compile; object hash durable before NM/readelf.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,signal,time
D=Path(__file__).resolve().parent;R=D/'EXACT-PRODUCTION-RECIPE.GRANTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
assert sha(R)=='fcbda7d1997c4259fc5551c6659c006c9ece9f9d5a6043ae74dd8863d92f7205';p=json.loads(R.read_bytes());argv=p['argv'];assert len(argv)==48
assert sha(Path(argv[6]))==p['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage'] and argv[-4:-2]==['-C','codegen-units=1']
old=json.loads(Path(p['baseline_recipe']['path']).read_bytes());assert [i for i,(a,b) in enumerate(zip(argv,old['argv'])) if a!=b]==[46,47]
assert len(p['source_inputs'])==78
for row in p['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private']
assert pin(Path(p['candidate_source']['path']))==p['candidate_source'];assert pin(Path(p['accepted_patch']['path']))==p['accepted_patch']
obj=D/'mckernel_rust.o';assert not obj.exists() and os.getuid()==os.geteuid()==1000
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,c.stop)
os.umask(0o077);os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
facts={'MemAvailable':mem,'aggregate_required':19<<30,'HOST_available':hs.f_bavail*hs.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':ss.f_bavail*ss.f_frsize,'scratch_required':(12<<30)+679477248,'full_backing_gap':gap,'backing_size':bs.st_size,'backing_device':bs.st_dev,'backing_inode':bs.st_ino,'ordinary_HOST_reserve':128<<20,'campaign_emergency_preserved':679477248}
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());used=state['last_rate_limits']['primary']['usedPercent'];assert used<100;facts['included_usage_percent']=used;c.write(D/'ACTUAL-HEADROOM.json',facts)
assert mem>=facts['aggregate_required'] and facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required']
profile={'scope':__doc__,'profile':p['profile'],'affinity':sorted(os.sched_getaffinity(0)),'exact_recipe':pin(R),'FROZEN_driver':pin(D/'run_once.py'),'tools':{str(Path(t)):pin(Path(t)) for t in [argv[0],argv[6],'/usr/bin/nm','/usr/bin/readelf']},'flags_only_diff_indices_from_accepted_recipe':[46,47]};c.write(D/'ACTUAL-PROFILE.json',profile)
begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96)
def capture(name,command):
 A=D/name;A.mkdir(mode=0o700);cmd={'argv':command,'purpose':__doc__,'cwd':str(D),'extra_environment':{'RUST_MIN_STACK':'2097152'},'profile_sha256':sha(D/'ACTUAL-PROFILE.json')};c.write(A/'command.json',cmd);remaining=90-(time.monotonic()-begin);assert remaining>0
 r=c.owned_capture(cmd,A,remaining,lambda:None);c.write(A/'whole-join.json',r)
 assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out'],r
 return r
try:
 compiler=capture('compiler-capture-1',argv)
 durable={'scope':__doc__,'status':'COMPILER_PASS_OBJECT_DURABLE_BEFORE_OBSERVERS','object':c.hashed(obj,32<<20),'compiler_join':compiler,'compiler_invocations':1,'profile':pin(D/'ACTUAL-PROFILE.json'),'no_compiler_replay_for_observer':True};c.write(D/'COMPILE-OBJECT-RECEIPT.json',durable)
except BaseException as e:
 c.write(D/'COMPILE-FAILURE.json',{'scope':__doc__,'error':repr(e),'compiler_replay_authorized':False});raise
try:
 nm=capture('nm-capture-1',['/usr/bin/nm','-g',str(obj)]);elf=capture('readelf-capture-1',['/usr/bin/readelf','--wide','--syms',str(obj)])
 oldnm=Path(p['baseline_nm']['path']);assert sha(oldnm)==p['baseline_nm']['sha256']
 def rows(path):return [line.split() for line in path.read_text().splitlines() if line.strip()]
 before=rows(oldnm);after=rows(D/'nm-capture-1/stdout');oldU={x[-1] for x in before if len(x)>=2 and x[-2]=='U'};newU={x[-1] for x in after if len(x)>=2 and x[-2]=='U'}
 expected=p['expected_U_delta'];assert len(oldU)==expected['before'] and len(newU)==expected['after'] and sorted(oldU-newU)==expected['removed'] and sorted(newU-oldU)==expected['added'],(len(oldU),len(newU),oldU-newU,newU-oldU)
 definitions={};elfrows=rows(D/'readelf-capture-1/stdout')
 for name in p['expected_new_exports']:
  found=[x for x in after if x[-1]==name];assert len(found)==1 and found[0][-2]=='T',(name,found)
  er=[x for x in elfrows if x[-1:]==[name]];assert len(er)==1 and len(er[0])==8 and er[0][3]=='FUNC' and er[0][4]=='GLOBAL' and er[0][6]!='UND' and int(er[0][2])>0,(name,er);definitions[name]={'nm':found,'readelf':er}
 oldT={x[-1] for x in before if len(x)>=3 and x[-2]=='T'};newT={x[-1] for x in after if len(x)>=3 and x[-2]=='T'};assert not oldT-newT and newT-oldT==set(p['expected_new_exports']),(oldT-newT,newT-oldT)
 assert all(pin(Path(row['private']['path']))==row['private'] for row in p['source_inputs'].values())
 st=obj.stat();o=durable['object'];assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(o['device'],o['inode'],o['size'],o['mtime_ns'],o['ctime_ns'])
 cpu=c.cpu_used();assert cpu<=60
 receipt={'scope':__doc__,'status':'PASS_ACTUAL78_PRIVATE_TOP_LOG_PRODUCTION_FULLCRATE_AND_NEW_EXPORT','recipe':pin(R),'source_count':78,'only_source_delta':p['only_delta'],'candidate_source':p['candidate_source'],'profile':pin(D/'ACTUAL-PROFILE.json'),'headroom':pin(D/'ACTUAL-HEADROOM.json'),'object':durable['object'],'object_hashed_once_before_observers':True,'compiler_invocations':1,'compiler_join':compiler,'nm_join':nm,'readelf_join':elf,'new_exports':definitions,'all_prior_T_exports_preserved':True,'production_U_delta':{'before':len(oldU),'after':len(newU),'removed':sorted(oldU-newU),'added':sorted(newU-oldU)},'all78_inputs_unchanged':True,'total_CPU_seconds':cpu,'CPU6_released':True,'whole_C_TU_default_link_native':'OPEN','GCC_kernel_TU_heavy_container_root_guest_currentimage_changes':0,'prior_fixture_family_preserved':p['fixture_family_history']};c.write(D/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json',receipt);print(json.dumps({'status':receipt['status'],'compiler_seconds':compiler['seconds'],'object_sha256':o['sha256'],'object_bytes':o['size'],'CPU6_released':True}))
except BaseException as e:
 c.write(D/'OBSERVER-FAILURE.json',{'scope':__doc__,'status':'STOP_OBSERVER_COMPILER_OBJECT_RETAINED_NO_REPLAY','error':repr(e),'object':durable['object'],'compiler_invocations':1});raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
