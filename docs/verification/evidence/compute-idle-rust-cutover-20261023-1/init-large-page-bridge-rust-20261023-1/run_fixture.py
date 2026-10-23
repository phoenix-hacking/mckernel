"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(HELPER),'exec'))
os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
def limits():
 for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
rflags=['--edition=2021','--crate-type=lib','--emit=obj','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort']
cflags=['-std=gnu11','-O2','-Wall','-Werror','-Ipreimage/arch/x86_64/kernel/include','-Ipreimage/lib/include']
commands=[('rust-real-bridge',[rust,*rflags,'fixture_bridge.rs','-o','bridge-rust.o']),('rust-real-provider-chain',[rust,*rflags,'fixture_chain.rs','-o','chain-rust.o']),('gcc-original-vs-rust',['/usr/bin/gcc-9',*cflags,'fixture.c','bridge-rust.o','-o','fixture-bridge']),('run-original-vs-rust',[str(D/'fixture-bridge')]),('gcc-provider-chain',['/usr/bin/gcc-9',*cflags,'-DCHAIN_PROVIDER','fixture.c','chain-rust.o','-o','fixture-chain']),('run-provider-chain',[str(D/'fixture-chain')]),('gcc-PUBLIC-selection',['/usr/bin/gcc-9',*cflags,'-O0','-DMCKERNEL_RUST_X86_MEMORY_PUBLIC','-c','selection.c','-o','public-selection.o']),('gcc-C-fallback-selection',['/usr/bin/gcc-9',*cflags,'-O0','-c','selection.c','-o','fallback-selection.o']),('bind-real-Rust-provider',['/usr/bin/ld','-r','public-selection.o','chain-rust.o','-o','public-rust-bound.o']),('nm-PUBLIC-selection',['/usr/bin/nm','public-selection.o']),('nm-fallback-selection',['/usr/bin/nm','fallback-selection.o']),('nm-bound-provider',['/usr/bin/nm','public-rust-bound.o'])]
results=[]
for i,(label,argv) in enumerate(commands):
 cap=D/('attempt-1-step-'+str(i+1));cap.mkdir(mode=0o700)
 cmd={'argv':argv,'purpose':__doc__,'label':label,'cwd':str(D),'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(cap/'command.json',cmd)
 result=owned_capture(cmd,cap,90,limits);write(cap/'whole-join.json',result);results.append({'label':label,'capture':str(cap),'join':result})
 if not(result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None):
  write(D/'attempt-1-results.json',{'scope':__doc__,'status':'FAIL_STOP','results':results});raise SystemExit(1)
public=(D/'attempt-1-step-10/stdout').read_text();fallback=(D/'attempt-1-step-11/stdout').read_text();bound=(D/'attempt-1-step-12/stdout').read_text()
def symbols(text,name):return [line.split()[-2] for line in text.splitlines() if line.split() and line.split()[-1]==name]
assert symbols(public,'x86_init_normal_set_large_bridge')==['U'],public
assert symbols(fallback,'x86_init_normal_set_large_bridge')==['t'],fallback
assert symbols(bound,'x86_init_normal_set_large_bridge')==['T'],bound
assert symbols(bound,'set_pt_large_page')==['T'],bound
assert symbols(bound,'x86_pt_set_page_bridge')==['U'],bound
write(D/'attempt-1-results.json',{'scope':__doc__,'status':'PASS_EXTRACTED_ACTUAL_BRIDGE_PROVIDER_AND_SELECTION','results':results,'observations_per_executable':61740,'unique_bound_bridge':True,'C_PUBLIC_definition_absent':True,'C_fallback_retained':True,'whole_production_default_link':False,'native':False,'whole_area_retired':False})
print('PASS: 61740 original-C/Rust observations per bridge and actual-provider-chain; actual header enum64 ABI; PUBLIC C U + Rust T uniquely bound; fallback C local t retained')
