"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted real ELF-end original-C/Rust, PUBLIC/fallback ABI/relocation checks.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
os.chdir(D);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
profile={'scope':__doc__,'authority':'Root explicit CPU6 real ELF-end original-C/Rust + actual PUBLIC/fallback ABI/relocation focused grant; no fullcrate/kernel/native','CPU':6,'jobs':1,'AS_bytes':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE_bytes':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'CGU':1,'code_model':'large (existing production x86 kernel ABI model)','Rust_compiler':{'path':rust,'sha256':sha(Path(rust))},'GCC':{'path':'/usr/bin/gcc-9','sha256':sha(Path('/usr/bin/gcc-9'))},'helper_sha256':sha(H)}
write(D/'ACTUAL-LEAF-PROFILE.json',profile)
c=['-std=gnu11','-O2','-Wall','-Werror','-fno-pie','-no-pie','-mcmodel=large','-Ipreimage/arch/x86_64/kernel/include','-Ipreimage/lib/include']
commands=[('Rust-actual-address-getter',[rust,'--edition=2021','--crate-type=lib','--emit=obj','-D','warnings','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort','-C','code-model=large','-C','relocation-model=static','fixture.rs','-o','fixture-rust.o']),('GCC-original-C-vs-Rust-real-ELF-end',['/usr/bin/gcc-9',*c,'-DMCKERNEL_RUST_X86_MEMORY_PUBLIC','fixture.c','fixture-rust.o','-o','fixture-public']),('run-original-C-vs-Rust-real-ELF-end',[str(D/'fixture-public')]),('GCC-C-fallback-real-ELF-end',['/usr/bin/gcc-9',*c,'fixture.c','-o','fixture-fallback']),('run-C-fallback-real-ELF-end',[str(D/'fixture-fallback')]),('GCC-PUBLIC-consumer',['/usr/bin/gcc-9',*c,'-O0','-DMCKERNEL_RUST_X86_MEMORY_PUBLIC','-c','consumer.c','-o','public-consumer.o']),('GCC-C-fallback-consumer',['/usr/bin/gcc-9',*c,'-O0','-c','consumer.c','-o','fallback-consumer.o']),('partial-link-actual-default-selection',['/usr/bin/ld','-r','public-consumer.o','fixture-rust.o','-o','public-rust-bound.o']),('nm-Rust',['/usr/bin/nm','fixture-rust.o']),('nm-PUBLIC-C',['/usr/bin/nm','public-consumer.o']),('nm-fallback-C',['/usr/bin/nm','fallback-consumer.o']),('nm-bound',['/usr/bin/nm','public-rust-bound.o']),('Rust-relocations64',['/usr/bin/readelf','-Wr','fixture-rust.o']),('actual-Rust-getter-disassembly',['/usr/bin/objdump','-dr','--disassemble=x86_init_text_end_bridge','fixture-rust.o']),('nm-real-ELF-provider',['/usr/bin/nm','fixture-public']),('finite-source-reversal',['/home/holden/anaconda3/bin/python3','-I','-B','verify_source_delta.py']),('harness-bash-syntax',['/bin/bash','-n','postimage/kernel/rust/tests/run_equivalence.sh'])]
write(D/'ACTUAL-LEAF-COMMANDS.json',{'scope':__doc__,'profile':profile,'commands':commands,'source_bindings':{name:hashed(D/name,32<<20) for name in ('fixture.rs','fixture.c','consumer.c','original_bridge.c.inc','selected_bridge.c.inc','production.patch','source-pins.json')}})
results=[];begin=time.monotonic()
for i,(label,argv) in enumerate(commands):
 cap=D/('leaf-attempt-1-step-'+str(i+1));cap.mkdir(mode=0o700);cmd={'argv':argv,'label':label,'purpose':__doc__,'profile_sha256':sha(D/'ACTUAL-LEAF-PROFILE.json'),'cwd':str(D)};write(cap/'command.json',cmd);j=owned_capture(cmd,cap,90,limits);write(cap/'whole-join.json',j);results.append({'label':label,'capture':str(cap),'join':j})
 if not(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']):
  write(D/'ACTUAL-LEAF-RESULT.json',{'scope':__doc__,'status':'FAIL_PRESERVED_STOP','results':results,'profile':profile});raise SystemExit(1)
outs={row['label']:(Path(row['capture'])/'stdout').read_text() for row in results}
def syms(label,name):return [x.split()[-2] for x in outs[label].splitlines() if x.split() and x.split()[-1]==name]
getter='x86_init_text_end_bridge'
assert syms('nm-Rust',getter)==['T'] and syms('nm-Rust','_end')==['U']
assert syms('nm-PUBLIC-C',getter)==['U']
assert syms('nm-fallback-C',getter)==['t'] and syms('nm-fallback-C','_end')==['U']
assert syms('nm-bound',getter)==['T'] and syms('nm-bound','_end')==['U']
assert len(syms('nm-real-ELF-provider','_end'))==1 and syms('nm-real-ELF-provider','_end')!=['U']
assert 'R_X86_64_64' in outs['Rust-relocations64'] and '_end' in outs['Rust-relocations64']
assert outs['run-original-C-vs-Rust-real-ELF-end'].startswith('PASS original-C/selected-provider real_ELF_end=')
assert outs['run-C-fallback-real-ELF-end'].startswith('PASS original-C/selected-provider real_ELF_end=')
write(D/'ACTUAL-LEAF-RESULT.json',{'scope':__doc__,'status':'PASS_ACTUAL_C_RUST_REAL_ELF_END_ADDRESS_ABI_SELECTION','profile':profile,'results':results,'seconds':time.monotonic()-begin,'symbols':{'Rust':['T getter','U _end'],'PUBLIC_C':['U getter','no C body'],'fallback_C':['local t getter','U _end'],'partial_link':['one T getter','U linker _end'],'ELF':['defined actual linker _end']},'relocation64':True,'original_C_Rust_real_ELF_address_equal':True,'Rust_object':hashed(D/'fixture-rust.o',32<<20),'host_ELF':hashed(D/'fixture-public',32<<20),'full_production_crate':False,'default_kernel_link':False,'native':False,'whole_file_retirement':False,'CPU6_released':True})
print('PASS original-C/Rust actual ELF end address + real-header64bit ABI/relocation + PUBLIC/fallback symbols + finite source/harness; CPU6 released')
