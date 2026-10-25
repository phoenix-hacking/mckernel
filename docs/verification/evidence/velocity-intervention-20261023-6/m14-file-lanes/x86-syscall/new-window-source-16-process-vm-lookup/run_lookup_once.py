"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted CPU6 process-VM lookup HOST parity batch.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,sys,time
D=Path(__file__).resolve().parent
P=D/'EXACT-LOOKUP-RECIPE.NOT-GRANTED.json'
EXPECTED='996811a0cf88a42a6884fc3721bf84c51928021e83381b538ba0f64ba70998e8'
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def pin(path):
 p=Path(path);raw=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
need(len(sys.argv)==3 and sys.argv[1]=='--root-grant','explicit root grant file required; source preparation never admits work')
G=Path(sys.argv[2]).resolve();grant=json.loads(G.read_text());need(pin(P)['sha256']==EXPECTED,'immutable exact07d803 descriptor')
j=json.loads(P.read_text());need(grant['descriptor']==pin(P) and grant['status']=='ROOT_GRANTED_ONCE' and grant['CPU_assignment']==6 and grant['driver']==pin(Path(__file__)) and grant['maximum_invocations']==1,'explicit exact descriptor/CPU0 admission')
expected_profile=dict(j['proposed_profile']);expected_profile['CPU_assignment']=6
need(grant['profile']==expected_profile,'root explicit CPU6 assignment; other profile limits unchanged')
need(os.getuid()==os.geteuid()==1000,'ordinary UID')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();need(hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','h990 capture')
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture','read_pinned_source'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_used(code):
 used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
 for value in code.co_consts:
  if isinstance(value,type(code)):used.update(globals_used(value))
 return used
AUTH=D/'SOURCE16-FD-AUTHORITIES.NOT-GRANTED.json'
need(pin(AUTH)['sha256']=='4235662179b7752fe8cd52f8c7a37c35cdb4ba5d0c924c8c8fef8b448e47d9f2','exact FD source authority map')
authorities=json.loads(AUTH.read_text());ns['source_authorities']=lambda:authorities
used=set()
for name in functions:used.update(globals_used(ns[name].__code__))
need(not used-set(ns)-set(vars(builtins)),'capture globals complete before child')
for name in authorities:ns['read_pinned_source'](Path(name),32<<20)
for row in j['sources']+j['headers']+j['reused_lock_inputs']:need(pin(row['path'])==row,'exact fixture source/header/object')
checked=dict(status='PASS_FROZEN_SOURCE_PINS_ONLY',compiler_or_fixture_commands=0)
O=Path(j['output_root']);C=Path(j['capture_root']);need(O.parent==D and C.parent==D and not O.exists() and not C.exists(),'fresh exact roots')
C.mkdir(mode=0o700);rows=[];failure=None;objects=[];start=time.monotonic()
try:
 ns['write'](C/'ROOT-GRANT.json',grant);ns['write'](C/'PLAN.json',j);ns['write'](C/'PREFLIGHT-AT-ADMISSION.json',checked)
 need(pin(j['compiler']['path'])==j['compiler'],'pinned HOST Rust1.92 compiler')
 for tool in j['tools']:need(pin(tool['path'])==tool,'pinned GCC9/objcopy/nm')
 mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden/mckernel-work');scratch=os.statvfs('/home/holden/mckernel-work/scratch')
 cap=dict(MemAvailable=mem,HOST_available=host.f_frsize*host.f_bavail,scratch_available=scratch.f_frsize*scratch.f_bavail,ordinary_reservation_bytes=2<<30,MemAvailable_min_bytes=19<<30,root_aggregate_owner='/root')
 ns['write'](C/'CAPACITY.json',cap)
 need(mem>=19<<30 and cap['HOST_available']>=(16<<30)+(256<<20) and cap['scratch_available']>=(12<<30)+(256<<20),'actual ordinary resource floors; no lowered proposal')
 O.mkdir(mode=0o700);os.chdir(j['commands'][0]['cwd']);os.environ['RUST_MIN_STACK']='2097152';os.sched_setaffinity(0,{6})
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for lim,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_STACK,2<<20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(lim,(value,value))
 signal.setitimer(signal.ITIMER_REAL,96)
 for i,command in enumerate(j['commands']):
  remaining=90-(time.monotonic()-start);need(remaining>0 and ns['cpu_used']()<60,'whole CPU/wall remainder')
  out=C/str(i).zfill(2);out.mkdir(mode=0o700);ns['write'](out/'command.json',command)
  remaining_cpu=int(60-ns['cpu_used']());need(remaining_cpu>=1,'shared remaining CPU exhausted before child')
  def child_limits():
   resource.setrlimit(resource.RLIMIT_CPU,(remaining_cpu,remaining_cpu))
  result=ns['owned_capture'](command,out,remaining,child_limits);ns['write'](out/'RESULT.json',result);rows.append(dict(name=command['name'],capture=str(out),result=result))
  need(result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],'first unexpected command '+command['name'])
  if i==0:
   diagnostics=(out/'stdout').read_text()+'\n'+(out/'stderr').read_text()
   libs=[line.strip().split('native-static-libs:',1)[1].strip().split() for line in diagnostics.splitlines() if 'native-static-libs:' in line]
   need(libs==[j['expected_native_static_libs']] and 'warning:' not in diagnostics and 'error:' not in diagnostics,'exact HOST native static libraries/no unexpected compiler diagnostic')
  else:need(result['captures']['stderr']['size']==0,'unexpected stderr '+command['name'])
  if i==4:need((out/'stdout').read_text()==j['expected_stdout'],'exact3420realVMlookup/ABI12/cache/oracle parity')
  if i==5:need((out/'stdout').read_text()==j['expected_ELF_stdout'],'exact bounded data owner ELF witness')
 need(ns['cpu_used']()<=60,'whole CPU cap')
 for name in authorities:ns['read_pinned_source'](Path(name),32<<20)
 for row in j['sources']+j['headers']+j['reused_lock_inputs']:
  need(pin(row['path'])==row,'post-run exact source/selector/header '+row['path'])
 for name in ('lookup-Rust.o','liblookup_actual.a','original-C.o','compare-C.o','lookup-compare'):objects.append(ns['hashed'](O/name,32<<20))
except BaseException as error:failure=type(error).__name__+': '+str(error)
finally:signal.setitimer(signal.ITIMER_REAL,0)
joined=all(r['result']['direct_child_joined'] and r['result']['group_absent'] and r['result']['closed_streams'] for r in rows)
report=dict(scope=__doc__,status='PASS_ACTUAL_VM_LOOKUP3420_ABI12_PROVIDER' if failure is None else 'FAIL_STOP_FIRST_UNEXPECTED_PRESERVE_NO_RETRY',descriptor=pin(P),driver=pin(Path(__file__)),root_grant=pin(G),commands=rows,error=failure,seconds=time.monotonic()-start,CPU_seconds=ns['cpu_used'](),CPU_assignment=6,CPU6_released=joined,whole_joined_group_absent_closed=joined,actual_cases=j['expected_cases'] if failure is None else None,objects=objects,canonical_writes=0,no_new_default_flag=True,VM_lookup_borrowed_under_controlled_lock_leaf_only=True,production_default_native=False,remaining=['Independentactualresultreview','Currentfullcrate/productiondefault/native not tested','Nativeborrowedlifetime/cacheconcurrency OPEN'],max_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
ns['write'](C/'ACTUAL-WHOLE-JOIN.json',report);print(json.dumps(dict(status=report['status'],commands=len(rows),error=failure,seconds=report['seconds'],CPU_seconds=report['CPU_seconds'],CPU6_released=joined),sort_keys=True));raise SystemExit(0 if failure is None else 1)
