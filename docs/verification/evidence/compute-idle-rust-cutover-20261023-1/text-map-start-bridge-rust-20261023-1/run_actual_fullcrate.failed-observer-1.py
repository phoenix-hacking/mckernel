"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact root-granted production Rust object compile and symbol readback only.
No kernel link, native/root/Docker/guest or target register-state execution.
"""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
P=D/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='fec9f0a8b15458db657088b8b80fa1dd3f226c26bf0e35e775158b84f8444c19'
p=json.loads(P.read_text());argv=p['argv'];assert len(argv)==48
assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage']
assert argv[-4:-2]==['-C','codegen-units=1']
assert sha(Path(argv[6]))=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
for row in p['source_inputs'].values():assert sha(Path(row['private']['path']))==row['private']['sha256']
paths={Path(row['private']['path']).resolve() for row in p['source_inputs'].values()}
for row in p['source_inputs'].values():
 path=Path(row['private']['path']);text=path.read_text()
 for relative in re.findall(r'#\[path\s*=\s*"([^\"]+)"\]',text):
  if relative.endswith('mckernel_guest_sysfs.rs'):continue
  assert (path.parent/relative).resolve() in paths
 for macro in ('include!','include_bytes!','include_str!'):assert macro not in text
assert sum('host-kernel/native-rust/' in key for key in p['source_inputs'])==2
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
os.chdir(D/'fullcrate-preparation-1');os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
profile={'scope':__doc__,'authority':'Parent exact fec9f0a8 production Rust recipe grant; same accepted pinnednightly1.95 profile, no bootstrap/stubs/features changed','recipe_sha256':sha(P),'prior_profile_authority':p['profile_authority'],'prior_accepted_fullcrate':p['accepted_previous_fullcrate'],'CPU':6,'jobs':1,'AS_bytes':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE_bytes':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'observed_affinity':sorted(os.sched_getaffinity(0)),'compiler':{'path':argv[6],'sha256':sha(Path(argv[6]))},'source_input_count':len(paths),'native_cfg':['native_linux_irq_work_v6_12','enable_profile','enable_perf','enable_rusage'],'codegen_units':1}
write(D/'ACTUAL-FULLCRATE-PROFILE.json',profile)
cap=D/'actual-fullcrate-compiler-capture-1';cap.mkdir(mode=0o700)
command={'argv':argv,'purpose':__doc__,'cwd':str(Path.cwd()),'profile':profile,'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(cap/'command.json',command)
start=time.monotonic();j=owned_capture(command,cap,90,limits);j['profile_sha256']=sha(D/'ACTUAL-FULLCRATE-PROFILE.json');write(cap/'whole-join.json',j)
if not(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None):
 write(D/'ACTUAL-FULLCRATE-RESULT.json',{'scope':__doc__,'status':'FAIL_PRESERVED_STOP','join':j,'profile':profile});raise SystemExit(1)
obj=Path(argv[-2].split('=',1)[1]);before=sha(obj)
cap=D/'actual-fullcrate-nm-capture-1';cap.mkdir(mode=0o700);command={'argv':['/usr/bin/nm','-g',str(obj)],'purpose':__doc__,'profile_sha256':sha(D/'ACTUAL-FULLCRATE-PROFILE.json')};write(cap/'command.json',command)
n=owned_capture(command,cap,90,limits);write(cap/'whole-join.json',n);assert n['returncode']==0 and n['direct_child_joined'] and n['group_absent'] and n['closed_streams'] and not n['error'] and not n['retirement_error']
rows=[x.split() for x in (cap/'stdout').read_text().splitlines()];symbols={}
for name,kind in [('x86_init_text_map_kernel_start_bridge','T'),('x86_map_kernel_start_geometry','U'),('x86_init_normal_set_large_bridge','T')]:
 matches=[x for x in rows if x and x[-1]==name];assert len(matches)==1 and matches[0][-2]==kind,matches;symbols[name]=matches
assert sha(obj)==before
write(D/'ACTUAL-FULLCRATE-RESULT.json',{'scope':__doc__,'status':'PASS_ACTUAL_PRIVATE_PRODUCTION_FULLCRATE_OBJECT_ONLY','profile':profile,'source_inputs_unchanged':all(sha(Path(r['private']['path']))==r['private']['sha256'] for r in p['source_inputs'].values()),'object':hashed(obj,32<<20),'symbols':symbols,'compiler_join':j,'nm_join':n,'elapsed_seconds':time.monotonic()-start,'canonical_normal_large_bridge_preserved':True,'default_kernel_link':False,'native':False,'whole_file_retirement':False,'CPU6_released':True})
print('PASS exact private production Rust crate: one textmap getter T/no U; one immutable geometry U; normal-large Rust T retained; CPU6 released')
