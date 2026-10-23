"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute only the root-granted leaf compile/ABI/geometry/consumer fixture packet.
No root, Docker, guest, state assembly, whole crate or kernel build.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(D/'SOURCE-CANDIDATE.json')=='523289990a4fef8a0475c436cad55fee5409a0638798ccb9494febf12641293f'
assert sha(D/'production.patch')=='441c4e4df2dee7ca3ad81a7d45e0bb89197780e725f0c8dd34b3cfd5c102d59b'
assert sha(D/'PROPOSED-ORDINARY-COMMANDS.NOT-EXECUTED.json')=='7aacf3c62cde58c65d3f6834aeadea26b33d1a18b56e85414418ae060ff40b87'
source=json.loads((D/'SOURCE-CANDIDATE.json').read_text())
for key in ('source_pins','production_patch','actual_original_C_fixture','actual_Rust_fixture','real_header_fixture','selected_C_consumer','finite_source_verifier','ABI_and_next_checks','ordinary_proposal'):
 row=source[key];assert sha(Path(row['path']))==row['sha256'],key
raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
p=json.loads((D/'PROPOSED-ORDINARY-COMMANDS.NOT-EXECUTED.json').read_text())
profile={'scope':__doc__,'authority':'Parent explicit execution of exact prepared7aacf3c ordinary packet after CPU6 normal guard release','CPU':6,'jobs':1,'AS_bytes':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE_bytes':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'allowed_affinity_observed':sorted(os.sched_getaffinity(0)),'owned_helper_sha256':sha(H),'proposal_sha256':sha(D/'PROPOSED-ORDINARY-COMMANDS.NOT-EXECUTED.json'),'rustc':{'path':p['commands'][0]['argv'][0],'sha256':sha(Path(p['commands'][0]['argv'][0]))},'gcc':{'path':'/usr/bin/gcc-9','sha256':sha(Path('/usr/bin/gcc-9'))}}
write(D/'ACTUAL-ORDINARY-PROFILE.json',profile)
rows=[];begin=time.monotonic()
for i,c in enumerate(p['commands']):
 cap=D/('ordinary-attempt-1-step-'+str(i+1));cap.mkdir(mode=0o700)
 command={'argv':c['argv'],'purpose':__doc__,'label':c['label'],'cwd':str(D),'profile':profile,'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(cap/'command.json',command)
 j=owned_capture(command,cap,90,limits);j['profile_sha256']=sha(D/'ACTUAL-ORDINARY-PROFILE.json');write(cap/'whole-join.json',j);rows.append({'label':c['label'],'capture':str(cap),'join':j})
 if not(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None):
  write(D/'ordinary-attempt-1-results.json',{'scope':__doc__,'status':'FAIL_PRESERVED_STOP','results':rows});raise SystemExit(1)
outputs={x['label']:(Path(x['capture'])/'stdout').read_text() for x in rows}
def symbols(text,name):return [x.split()[-2] for x in text.splitlines() if x.split() and x.split()[-1]==name]
name='x86_init_text_map_kernel_start_bridge';data='x86_map_kernel_start_geometry'
assert symbols(outputs['nm-bound'],name)==['T']
assert symbols(outputs['nm-bound'],data)==['R']
assert symbols(outputs['nm-PUBLIC-C'],name)==['U']
assert symbols(outputs['nm-PUBLIC-C'],data)==['R']
assert symbols(outputs['nm-fallback-C'],name)==['t']
assert symbols(outputs['nm-fallback-C'],data)==[]
for i in range(7):assert outputs['run-original-C-vs-PUBLIC-Rust-'+str(i)].startswith('PASS original-C/selected-provider geometry=')
assert outputs['run-exact-C-fallback'].startswith('PASS original-C/selected-provider geometry=')
assert sha(D/'SOURCE-CANDIDATE.json')==profile.get('source_sha256', '523289990a4fef8a0475c436cad55fee5409a0638798ccb9494febf12641293f')
write(D/'ordinary-attempt-1-results.json',{'scope':__doc__,'status':'PASS_ACTUAL_LEAF_ORIGINAL_C_RUST_HEADER_GEOMETRY_AND_SELECTION','profile':profile,'results':rows,'seconds':time.monotonic()-begin,'original_C_vs_Rust_geometry_cases':7,'fallback_cases':1,'retained_geometry_reference':p['retained_geometry_source'],'retained_geometry_argument':p['retained_profile_geometry_argument'],'symbols':{'bound_bridge':['T'],'bound_data':['R'],'PUBLIC_C_bridge':['U'],'PUBLIC_C_data':['R'],'fallback_bridge':['t'],'fallback_data':[]},'Rust_object':hashed(D/'fixture-rust.o',32<<20),'bound_object':hashed(D/'public-rust-bound.o',32<<20),'source_candidate_unchanged':True,'full_crate':False,'default_kernel_link':False,'native':False,'whole_file_retirement':False,'CPU6_released':True})
print('PASS seven actual original-C/Rust geometry cases + exact C fallback; real-header64bit ABI; PUBLIC data R/getter U -> unique bound Rust T/data R; finite source/harness checks; CPU6 released')
