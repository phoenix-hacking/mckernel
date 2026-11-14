"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted original-C/public-Rust pure restart policy fixture.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,shlex,stat,sys,time
D=Path(__file__).resolve().parent
N=D
P=D/'EXACT-RETAINED-RESTART-SUFFIX.NOT-GRANTED.json'
PLAN_SHA='97ae299d6a3159ebfe37173c7299b2e869ec3c8092baf9c69f15bb5cd78de046'
def need(x,m):
 if not x:raise RuntimeError(m)
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def unique(text,name,kind):
 found=[s.split()[-2] for s in text.splitlines() if s.split() and s.split()[-1]==name];need(found==[kind],'unique symbol '+name+' '+str(found))
need(os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12),'exact actual interpreter before child')
need(pin(P)['sha256']==PLAN_SHA,'fixed single restart batch plan');p=json.loads(P.read_text())
for row in p['sources']+p['frozen_actual_header_dependencies']+p['source_predecessors']+p['current_source_guards']+p['other_tools']:
 need(pin(row['path'])==row,'source/header/provider/tool pin '+row['path'])
g=p['current_C_reference'];s=Path(g['path']).read_text();i=s.index(g['signature']);j=s.index('\n}\n',i)+3
need(s[i:j].encode()==Path(g['actual_reference']['path']).read_bytes(),'exact current original C body changed; STOPno refresh')
need(Path.cwd()==D,'actual parent CWD')
need(pin(p['actual_compiler']['path'])==p['actual_compiler'],'pinnedRust1.92')
for row in p['pinned_toolchain_runtime_metadata']:
 q=Path(row['path']);a=q.stat();actual=dict(path=str(q),dev=a.st_dev,inode=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)),size=a.st_size,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns,content_hash_not_claimed=True)
 need(actual==row,'same genuine runtime metadata')
archive=p['retained_archive'];q=Path(archive['path']);a=q.stat()
actual=dict(path=str(q),device=a.st_dev,inode=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)),nlink=a.st_nlink,size=a.st_size,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns)
need(actual=={k:v for k,v in archive.items() if k!='sha256'},'retained successful Rust archive stable metadata; no recompile/rehash')
facts=json.loads(Path(p['retained_archive_receipt']['path']).read_text());need(facts['archive']==archive and facts['native_static_libs']==p['retained_native_static_libs'],'same actual Rust compile native libraries')
native_libs=p['retained_native_static_libs'];need(p['Rust_recompile'] is False and p['original_indices']==[1,2,3,4,5],'only remaining C/link/run/NM suffix')
link=p['commands'][1]['argv'];need(link[1].endswith('/restart-C.o') and link[2]==archive['path'] and link[3:link.index('-o')]==native_libs,'same actual compiler native flags after retained archive')

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
mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024;h=os.statvfs('/home/holden/mckernel-work');s=os.statvfs('/home/holden/mckernel-work/scratch');b=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,b.st_size-b.st_blocks*512)
capacity=dict(MemAvailable=mem,HOST_available=h.f_frsize*h.f_bavail,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=s.f_frsize*s.f_bavail,scratch_required=(12<<30)+679477248,backing_bytes=b.st_size,full_backing_gap=gap)
need(mem>=19<<30 and b.st_size==110<<30 and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],'fresh aggregate/floors/fullgap')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());need(state['last_rate_limits']['primary']['usedPercent']<100,'included usage stop')
O=Path(p['output_root']);C=Path(p['capture_root']);need(O.parent==N and C.parent==N and not O.exists() and not C.exists(),'fresh expert suffix only');O.mkdir(mode=0o700);C.mkdir(mode=0o700)
ns['write'](C/'PLAN.json',p);ns['write'](C/'CAPACITY.json',capacity);os.chdir(D);os.environ['RUST_MIN_STACK']='2097152';os.sched_setaffinity(0,{6})
for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(r,(v,v))
rows=[];failure=None;start=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96)
try:
 for i,template in enumerate(p['commands']):
  c=dict(template);c['argv']=list(template['argv']);original_index=p['original_indices'][i]
  remaining=90-(time.monotonic()-start);need(remaining>0 and ns['cpu_used']()<60,'whole wall/CPU remainder');out=C/str(original_index).zfill(2);out.mkdir(mode=0o700);ns['write'](out/'command.json',c)
  result=ns['owned_capture'](c,out,remaining,lambda:None);ns['write'](out/'RESULT.json',result);rows.append(dict(name=c['name'],original_index=original_index,capture=str(out),result=result))
  need(result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],'first unexpected command '+c['name'])
  need(result['captures']['stderr']['size']==0,'unexpected stderr '+c['name'])
 need(ns['cpu_used']()<=60,'whole CPU cap')
 text=(C/'03/stdout').read_text();need(text.startswith('PASS actual_legacy_native_C_vs_Rust_restart vectors=248640 ') and len(text.splitlines())==1,'all exact restart cases')
 v=(C/'04/stdout').read_text()
 for name in ('arch_signal_restart_result','fixture_restart_actual_Rust_ABI'):
  unique(v,name,'T')
 need('core::panicking::panic_bounds_check' in (C/'05/stdout').read_text(),'genuine HOST core checked-index runtime')
 binary=ns['hashed'](O/'restart-compare',32<<20);c_object=ns['hashed'](O/'restart-C.o',32<<20)
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:signal.setitimer(signal.ITIMER_REAL,0)
joined=all(r['result']['direct_child_joined'] and r['result']['group_absent'] and r['result']['closed_streams'] for r in rows)
report=dict(scope=__doc__,status='PASS_ACTUAL_C_RUST_RESTART248640_REAL_HEADER_SUFFIX_ONLY' if failure is None else 'FAIL_STOP_FIRST_UNEXPECTED_EXPERT_REQUIRED',plan=pin(P),driver=pin(Path(__file__)),commands=rows,error=failure,seconds=time.monotonic()-start,total_CPU=ns['cpu_used'](),whole_joined_group_absent_closed=joined,CPU6_released=joined,actual_cases=248640 if failure is None else None,archive=archive,binary=binary if 'binary' in globals() else None,C_object=c_object if 'c_object' in globals() else None,native_static_libs=native_libs,Rust_recompiled=False,retained_archive_rehashed=False,controls=p['control_scope'],remaining_native=p['remaining_native'],VDSO_or_ptrace_replayed=False,default_fullfile_image_native=False)
ns['write'](C/'ACTUAL-WHOLE-JOIN.json',report);print(json.dumps(dict(status=report['status'],commands=len(rows),error=failure,seconds=report['seconds'],CPU6_released=joined),sort_keys=True));raise SystemExit(0 if failure is None else 1)
