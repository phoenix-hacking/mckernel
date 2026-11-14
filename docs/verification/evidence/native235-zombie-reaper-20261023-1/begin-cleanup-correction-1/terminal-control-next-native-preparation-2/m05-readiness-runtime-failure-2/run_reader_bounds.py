"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw);names={'need','write','hashed','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'))
A=D/'reader-bounds-1';A.mkdir();os.sched_setaffinity(0,{0});os.environ['RUST_MIN_STACK']='2097152'
for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
assert json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent']<100
write(A/'SOURCE-BINDINGS.json',[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in D.iterdir() if p.is_file()])
commands=[('bounds-build',['/usr/bin/gcc-9','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',str(D/'reader_bounds_fixture.c'),str(D/'attempt-1/libbegin_readiness.a'),'-Wl,--gc-sections','-o',str(A/'fixture')],D)]
for mode in ('full-read','oversize-read','empty-read'):
 cwd=A/mode;cwd.mkdir();commands.append((mode,[str(A/'fixture'),mode,str(D/'retained7589-console-klog-LF.kmsg'),str(D/'controlled-epoch2-pending.kmsg')],cwd))
write(A/'EXACT-COMMANDS-BEFORE-EXECUTION.json',[{'purpose':__doc__,'role':name,'argv':argv,'cwd':str(cwd)} for name,argv,cwd in commands])
results=[]
for name,argv,cwd in commands:
 os.chdir(cwd);capture=A/('capture-'+name);capture.mkdir()
 command={'purpose':__doc__,'argv':argv,'cwd':str(cwd),'shell':False};write(capture/'command.json',command)
 joined=owned_capture(command,capture,90,lambda:None);write(capture/'result.json',joined);results.append({'role':name,'whole_join':joined})
 if joined['returncode']!=0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error']:break
status='PASS' if len(results)==4 and all(x['whole_join']['returncode']==0 for x in results) else 'FAIL_STOP'
write(A/'RESULT.json',{'scope':__doc__,'status':status,'operations':results,'native_acceptance':False,'CPU0_released_after_exit':True})
print(json.dumps({'status':status,'operations':len(results)}))
