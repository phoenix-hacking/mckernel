# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw)
names={'need','write','hashed','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'))
os.chdir(D)
os.environ['RUST_MIN_STACK']='2097152'
def limits():
 os.sched_setaffinity(0,{0})
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]: resource.setrlimit(r,(v,v))
commands=[['/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','--crate-type=lib','--emit=obj','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort','fixture.rs','-o','fixture-rust.o'],['/usr/bin/gcc-9','-std=gnu11','-O2','-Wall','-Werror','-ffunction-sections','-fdata-sections','-Ifixture-include','-Ipreimage/kernel/include','fixture.c','fixture-rust.o','-Wl,--gc-sections','-o','fixture'],[str(D/'fixture')],['/usr/bin/gcc-9','-std=gnu11','-O2','-Wall','-Werror','-DFIXTURE_LOCK_WORDS=1','-ffunction-sections','-fdata-sections','-Ifixture-include','-Ipreimage/kernel/include','fixture.c','fixture-rust.o','-Wl,--gc-sections','-o','fixture-stride8'],[str(D/'fixture-stride8')]]
results=[]
for i,argv in enumerate(commands):
 path=D/('attempt-1-step-'+str(i+1));path.mkdir()
 command={'argv':argv,'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'}
 write(path/'command.json',command)
 result=owned_capture(command,path,90,limits);write(path/'result.json',result);results.append(result)
 if result['returncode']!=0 or not result['direct_child_joined'] or not result['group_absent'] or not result['closed_streams'] or result['error'] or result['retirement_error']:break
write(D/'attempt-1-results.json',results)
print(json.dumps(results))
