"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
PREVIOUS=D.parent/'production-combined-3/ordinary-fullcrate-callback3-1'
ROOT=Path('/home/holden/mckernel')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((PREVIOUS/'result.json').read_text());assert old['status']=='PASS_ACTUAL_82INPUT_FULLCRATE'
command=json.loads((PREVIOUS/'command.json').read_text());argv=command['argv'].copy()
assert len(argv)==46 and sha(Path(argv[6]))=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
assert argv[-10:-2]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage']
oldinputs=json.loads((PREVIOUS/'input-bindings-82.json').read_text())['inputs']
inputs={}
for p in sorted((D/'whole-crate/kernel/rust').glob('*.rs')):
 rel='kernel/rust/'+p.name
 if p.name!='x86_memory_helpers.rs':assert sha(p)==sha(ROOT/rel),'copied canonical dependency changed; preserve before rebuilding'
 inputs[rel]={'path':str(p),'sha256':sha(p),'canonical_source':str(ROOT/rel),'canonical_sha256':sha(ROOT/rel),'private_modified':p.name=='x86_memory_helpers.rs'}
for rel in ('host-kernel/native-rust/abi/vdso.rs','host-kernel/native-rust/zero_pages.rs'):
 row=oldinputs[rel];source=Path(row['path']);assert sha(source)==row['sha256']==sha(ROOT/rel),'unchanged admitted external module required'
 p=D/'whole-crate'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(source.read_bytes());inputs[rel]={'path':str(p),'sha256':sha(p),'prior_profile_source':row}
for rel,row in inputs.items():
 for rawpath in re.findall(r'#\[path\s*=\s*"([^"]+)"\]',Path(row['path']).read_text()):
  if rawpath.endswith('mckernel_guest_sysfs.rs'):continue # cfg native_sysfs_verify remains disabled exactly as prior profile.
  target=(Path(row['path']).parent/rawpath).resolve();assert target in [Path(x['path']).resolve() for x in inputs.values()],str(target)
 for macro in ('include!','include_str!','include_bytes!'):assert macro not in Path(row['path']).read_text()
helper=ROOT/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'
raw=helper.read_bytes();assert sha(helper)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(helper),'exec'))
obj=D/'mckernel_rust.o';argv[-2]='--emit=obj='+str(obj);argv[-1]=str(D/'whole-crate/kernel/rust/lib.rs');argv[-2:-2]=['-C','codegen-units=1']
profile={'scope':__doc__,'authority':'Parent explicit reuse of existing accepted pinned nightly1.95 ordinary fullcrate profile; one CPU6 job and explicit CGU1 tightening','prior_result':{'path':str(PREVIOUS/'result.json'),'sha256':sha(PREVIOUS/'result.json')},'prior_command':{'path':str(PREVIOUS/'command.json'),'sha256':sha(PREVIOUS/'command.json')},'prior_runner':{'path':str(PREVIOUS/'run_fullcrate.py') if (PREVIOUS/'run_fullcrate.py').exists() else str(next(PREVIOUS.glob('run_*.py'))),'sha256':sha(next(PREVIOUS.glob('run_*.py')))},'compiler':{'path':argv[6],'sha256':sha(Path(argv[6]))},'unchanged_cfg':['native_linux_irq_work_v6_12','enable_profile','enable_perf','enable_rusage'],'CPU':6,'jobs':1,'address_space_bytes':2<<30,'cpu_seconds':60,'wall_seconds':90,'retirement_seconds':6,'file_size_bytes':32<<20,'nofile':256,'core':0,'RUST_MIN_STACK':2097152,'command_delta':'only source/output paths and explicit CGU1 resource tightening; no feature/cfg deletion, bootstrap or native stubs','source_closure_count':len(inputs)}
write(D/'FULLCRATE-PROFILE-AUTHORITY.json',profile);write(D/'fullcrate-input-bindings.json',inputs)
os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
def limits():
 for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
cap=D/'fullcrate-compiler-capture-1';cap.mkdir(mode=0o700);cmd={'argv':argv,'purpose':__doc__,'profile_authority':profile,'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(cap/'command.json',cmd)
result=owned_capture(cmd,cap,90,limits);result['profile_authority_sha256']=sha(D/'FULLCRATE-PROFILE-AUTHORITY.json');write(cap/'whole-join.json',result)
assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and not result['error'] and not result['retirement_error'],result
cap=D/'fullcrate-nm-capture-1';cap.mkdir(mode=0o700);cmd={'argv':['/usr/bin/nm','-g',str(obj)],'purpose':__doc__};write(cap/'command.json',cmd);j=owned_capture(cmd,cap,90,limits);write(cap/'whole-join.json',j)
assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']
rows=[x.split() for x in (cap/'stdout').read_text().splitlines() if x.split() and x.split()[-1]=='x86_init_normal_set_large_bridge'];assert len(rows)==1 and rows[0][-2]=='T',rows
write(D/'fullcrate-result.json',{'scope':__doc__,'status':'PASS_CURRENT_PRIVATE_PRODUCTION_FULLCRATE','profile_authority':profile,'source_closure_count':len(inputs),'object':hashed(obj,32<<20),'bridge_symbol_rows':rows,'whole_join':result,'nm_join':j,'unique_Rust_bridge_definition':True,'unresolved_bridge':False,'production_kernel_default_link':False,'native':False,'whole_memory_area_retired':False})
print('PASS current private production fullcrate; '+str(len(inputs))+' pinned source inputs; exactly one bridge T/no bridge U; no default-kernel link/native credit')
