"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One explicitly root-granted ordinary actual C/Rust fixture batch; no root/container/guest.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,sys,time
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-batch-actual-consumer-preparation-1')
N=Path(__file__).resolve().parent
PLAN_SHA='5f7fae7783aeee69328ee07ac68bb8edeb74481c3316fa1e8478d7c702397c54'
P=N/'EXACT-REMAINING-EIGHT-COMMANDS.NOT-GRANTED.json'
def need(x,m):
 if not x:raise RuntimeError(m)
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def unique(text,name,kind):
 found=[s.split()[-2] for s in text.splitlines() if s.split() and s.split()[-1]==name];need(found==[kind],'unique symbol '+name+' '+str(found))
need(os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12),'exact actual interpreter before child')
need(pin(P)['sha256']==PLAN_SHA,'fixed single batch plan');p=json.loads(P.read_text())
CURRENT_RECEIPT=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-batch-actual-consumer-preparation-1/current-entry-qualification-1/CURRENT-ENTRY-COHERENT-PRECHECK.SOURCE-RECEIPT.json')
need(pin(CURRENT_RECEIPT)['sha256']=='25aee920ec80cf4089ea7bc3c169040d0f1aba1122825512599abaf6f87025f9','current accepted entry qualification')
for row in json.loads(CURRENT_RECEIPT.read_text())['current_canonical']:need(pin(row['path'])==row,'current accepted entry precheck; STOP no refresh')
for row in p['sources']+p['frozen_actual_header_dependencies']+p['source_predecessors']:need(pin(row['path'])==row,'frozen fixture/header/predecessor '+row['path'])
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();need(pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','accepted owned capture')
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_used(c):
 used={i.argval for i in dis.get_instructions(c) if i.opname=='LOAD_GLOBAL'}
 for v in c.co_consts:
  if isinstance(v,type(c)):used.update(globals_used(v))
 return used
used=set()
for n in functions:used.update(globals_used(ns[n].__code__))
need(not used-set(ns)-set(vars(builtins)),'helper globals before child')
for row in p['retained_objects']:need(ns['hashed'](Path(row['path']),32<<20)==row,'retained actual object stable FD metadata')
a=Path(p['output_directory_identity']['path']).stat();actual=dict(path=str(D/'output-1'),dev=a.st_dev,inode=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)))
need(actual==p['output_directory_identity'],'retained output directory identity')
need(Path.cwd()==D,'actual parent CWD')
for c in p['commands']:
 need(c['cwd']==str(D),'exact command CWD')
 if c['argv'][0].endswith('/rustc'):
  source=next(Path(x) for x in c['argv'] if x.endswith('.rs'));name=c['argv'][c['argv'].index('--crate-name')+1] if '--crate-name' in c['argv'] else source.stem
  need(name=='signal_actual' and Path(c['argv'][c['argv'].index('-o')+1])==D/'output-1/signal-Rust.o','retained compiler crate/output mapping')

mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024;h=os.statvfs('/home/holden/mckernel-work');s=os.statvfs('/home/holden/mckernel-work/scratch');b=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,b.st_size-b.st_blocks*512)
capacity=dict(MemAvailable=mem,HOST_available=h.f_frsize*h.f_bavail,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=s.f_frsize*s.f_bavail,scratch_required=(12<<30)+679477248,backing_bytes=b.st_size,full_backing_gap=gap)
need(mem>=19<<30 and b.st_size==110<<30 and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],'fresh aggregate/floors/fullgap')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());need(state['last_rate_limits']['primary']['usedPercent']<100,'included usage stop')
O=D/'output-1';C=N/'actual-remaining-capture-1';need(O.is_dir() and not C.exists(),'retained output plus fresh capture only');need({x.name for x in O.iterdir()}=={'vdso-Rust.o','vdso-original.o'},'all remaining outputs absent');C.mkdir(mode=0o700)
ns['write'](C/'RETAINED-OBJECTS-AND-CWD-CHECK.json',dict(objects=p['retained_objects'],directory=p['output_directory_identity'],actual_parent_CWD=str(Path.cwd()),compiler_crate_output_checked=True,no_recompile_indices=[0,1]));ns['write'](C/'PLAN.json',p);ns['write'](C/'CAPACITY.json',capacity);os.chdir(D);os.environ['RUST_MIN_STACK']='2097152';os.sched_setaffinity(0,{6})
for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(r,(v,v))
rows=[];failure=None;start=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96)
try:
 for c in p['commands']:
  i=c['original_index']
  remaining=90-(time.monotonic()-start);need(remaining>0 and ns['cpu_used']()<60,'whole ordinary wall/CPU remainder');out=C/('%02d'%i);out.mkdir(mode=0o700);ns['write'](out/'command.json',c)
  result=ns['owned_capture'](c,out,remaining,lambda:None);ns['write'](out/'RESULT.json',result);rows.append(dict(name=c['name'],capture=str(out),result=result))
  need(result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],'first unexpected command '+c['name'])
  need(result['captures']['stderr']['size']==0,'unexpected stderr '+c['name'])
 need(ns['cpu_used']()<=60,'whole CPU cap')
 need('vectors=36876 ' in (C/'03/stdout').read_text(),'actual VDSO vector completion')
 need('selected_C_public_Rust=3456 ' in (C/'07/stdout').read_text(),'actual signal vector completion')
 v=(C/'04/stdout').read_text();unique(v,'vdso_map_global_pages','T');unique(v,'vdso_map_global_pages_body_result','T');unique(v,'x86_arch_setup_pvclock_body_result','T')
 v=(C/'08/stdout').read_text();unique(v,'ptrace_report_signal','T');unique(v,'ptrace_report_signal_body_result','T');unique(v,'do_kill','U');unique(v,'schedule','U')
 v=(C/'09/stdout').read_text();unique(v,'ptrace_report_signal','T');unique(v,'do_kill','T');unique(v,'schedule','T')
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:signal.setitimer(signal.ITIMER_REAL,0)
joined=all(r['result']['direct_child_joined'] and r['result']['group_absent'] and r['result']['closed_streams'] for r in rows)
report=dict(scope=__doc__,status='PASS_ACTUAL_NEXT_F06_TWO_BOUNDARY_BATCH_ONLY' if failure is None else 'FAIL_STOP_FIRST_UNEXPECTED_NO_RETRY',plan=pin(P),driver=pin(Path(__file__)),commands=rows,retained_original_objects=p['retained_objects'],retained_original_results=p['original_successful_command_results'],original_failure=p['original_failure'],error=failure,seconds=time.monotonic()-start,total_CPU=ns['cpu_used'](),whole_joined_group_absent_closed=joined,CPU6_released=joined,actual_vectors=40332 if failure is None else None,controls=p['controls'],baseline_differences=p['baseline_differences'],default_fullfile_image_native=False)
ns['write'](C/'ACTUAL-WHOLE-JOIN.json',report);print(json.dumps(dict(status=report['status'],commands=len(rows),error=failure,seconds=report['seconds'],CPU6_released=joined),sort_keys=True));raise SystemExit(0 if failure is None else 1)
