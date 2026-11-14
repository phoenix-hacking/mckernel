"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compile artifacts and execute ONLY the synthetic eligibility/byte-oracle tests.
Never execute app.rs/component_state.S or any target register-state operation.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(H),'exec'))
os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
proposed=json.loads((D/'PROPOSED-ORDINARY-COMMANDS.NOT-EXECUTED.json').read_text())
compiler=Path(proposed['compiler']['path'])
profile={'scope':__doc__,'authority':'Parent explicit CPU6 ordinary compile/pure semantic test grant; existing Rust1.92/GCC9 profile; no state-app execution','cpu':6,'jobs':1,'AS_bytes':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE_bytes':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'compiler':{'path':str(compiler),'sha256':hashlib.sha256(compiler.read_bytes()).hexdigest()},'owned_helper_sha256':hashlib.sha256(raw).hexdigest()}
write(D/'ACTUAL-ORDINARY-PROFILE.json',profile)
commands=[('compile-pure-semantics',proposed['semantic_test_compile_argv']),('run-pure-semantics-only',proposed['semantic_test_run_argv']),('assemble-state-artifact-only',['/usr/bin/gcc-9','-c',str(D/'component_state.S'),'-o',str(D/'component_state.o')]),('link-static-state-app-artifact-only',proposed['private_app_compile_argv']),('inspect-static-app-ELF',['/usr/bin/readelf','-W','-l',str(D/'state-app')]),('inspect-probe-artifact',['/usr/bin/objdump','-d','--disassemble=component_probe',str(D/'state-app')]),('inspect-handler-artifact',['/usr/bin/objdump','-d','--disassemble=component_handler',str(D/'state-app')])]
results=[]
for i,(label,argv) in enumerate(commands):
 cap=D/('ordinary-attempt-1-step-'+str(i+1));cap.mkdir(mode=0o700)
 cmd={'argv':argv,'purpose':__doc__,'label':label,'profile':profile,'cwd':str(D),'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(cap/'command.json',cmd)
 j=owned_capture(cmd,cap,90,limits);j['profile_sha256']=hashlib.sha256((D/'ACTUAL-ORDINARY-PROFILE.json').read_bytes()).hexdigest();write(cap/'whole-join.json',j);results.append({'label':label,'capture':str(cap),'join':j})
 if not(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']):
  write(D/'ordinary-attempt-1-results.json',{'scope':__doc__,'status':'FAIL_PRESERVED_STOP','results':results,'state_app_execution':False});raise SystemExit(1)
elf=(D/'ordinary-attempt-1-step-5/stdout').read_text();assert ' INTERP ' not in elf
stack=[x for x in elf.splitlines() if 'GNU_STACK' in x];assert len(stack)==1 and ' RWE ' not in stack[0]
probe=(D/'ordinary-attempt-1-step-6/stdout').read_text();handler=(D/'ordinary-attempt-1-step-7/stdout').read_text()
assert 'xsave64' in probe and 'xrstor64' in probe and 'syscall' in probe
assert 'xsave64' in handler and 'xrstor64' in handler
assert '\tcall' not in probe and '\tcall' not in handler
write(D/'ordinary-attempt-1-results.json',{'scope':__doc__,'status':'PASS_PURE_SEMANTICS_AND_STATIC_ARTIFACT_ONLY','profile':profile,'results':results,'pure_test_stdout':(D/'ordinary-attempt-1-step-2/stdout').read_text(),'state_app':hashed(D/'state-app',32<<20),'assembly_object':hashed(D/'component_state.o',32<<20),'static_no_interpreter':True,'stack_non_executable':True,'actual_probe_and_handler_no_call_instructions':True,'state_app_execution':False,'state_register_preservation_proven':False,'native_or_M07_acceptance':False,'CPU6_released_after_wholejoins':True})
print('PASS pure semantic tests + assembled component artifact + static Rust app link/ELF inspection only; no app/register execution; CPU6 released')
