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
 os.sched_setaffinity(0,{7})
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]: resource.setrlimit(r,(v,v))
P=D.parent;a=P/'attempt-1';work=D/'work';work.mkdir()
source=json.loads((D/'SOURCE-BINDINGS.json').read_text())
for name,row in source.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==row['sha256']
os.environ['REAL_ATTEMPT']='attempt-1';os.environ['REAL_WIRE_ROOT']=str(a/'controlled-full-frames');os.environ['FINAL_MODE']='10';os.environ['FINAL_WIRE_PATH']=str(D/'wire-pure-replaced')
rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';gcc='/usr/bin/gcc-9'
commands=[('actual-bridge-build',[gcc,'-std=gnu11','-O1','-g0','-Wall','-Wextra','-DPAIR_ROOT="."','-DPAIR_LAUNCHER="'+str(a/'controlled-launcher')+'"','-I',str(P),'-c',str(D/'bridge_fixture.c'),'-o',str(D/'bridge_fixture.o')],D),
('Rust-relink',[rust,'--edition=2021','--test','-C','codegen-units=1','-C','opt-level=1','-C','debuginfo=0','-C','linker=/usr/bin/gcc-9','-C','link-arg='+str(D/'bridge_fixture.o'),'-C','link-arg='+str(a/'old_trace_witness.o'),str(P/'pair_long_producer.rs'),'-o',str(D/'producer-tests')],D),
('actual-pure-replacement-wire',[str(D/'producer-tests'),'--exact','tests::actual_loop_full_report_trace_consumer_wire','--test-threads=1'],work),
('actual-final-deadline-wire',[str(D/'producer-tests'),'--exact','tests::actual_loop_full_report_trace_consumer_wire','--test-threads=1'],work),
('unchanged-full-consumer-check',['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'check_replacement.py')],D)]
results=[]
for label,argv,cwd in commands:
 if label=='actual-final-deadline-wire':os.environ['FINAL_MODE']='8';os.environ['FINAL_WIRE_PATH']=str(D/'wire-final-deadline')
 os.chdir(cwd);capture=D/label;capture.mkdir();command=dict(argv=argv,cwd=str(cwd),purpose='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',shell=False)
 write(capture/'command.json',command);result=owned_capture(command,capture,90,limits);write(capture/'result.json',result);results.append(dict(label=label,whole_join=result))
 if result['returncode']!=0 or not result['direct_child_joined']or not result['group_absent']or not result['closed_streams']or result['error']or result['retirement_error']:break
write(D/'RESULT.json',dict(status='PASS'if len(results)==5 and results[-1]['whole_join']['returncode']==0 else'FAIL_STOP_FIRST_FAILURE',operations=results,native_acceptance=False))
print(json.dumps(dict(completed=len(results),last=results[-1]['label'],returncode=results[-1]['whole_join']['returncode'])))
