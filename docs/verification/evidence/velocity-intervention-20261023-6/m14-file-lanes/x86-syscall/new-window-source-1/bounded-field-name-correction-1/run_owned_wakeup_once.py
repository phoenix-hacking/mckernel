"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted ONE bounded SigSet field-name correction; preserve E0609 failure. No further retry.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,shlex,signal,sys,time
D=Path(__file__).resolve().parent
P=D/'EXACT-WAKEUP-QUEUE.NOT-GRANTED.json'
EXPECTED='9cb911f7648858242eb4b63636b266bc1930eb289ba9dd7b1ee1ec9384d8a3cb'
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=H.read_bytes();need(hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','accepted h990 helper unchanged')
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_used(c):
 used={i.argval for i in dis.get_instructions(c) if i.opname=='LOAD_GLOBAL'}
 for v in c.co_consts:
  if isinstance(v,type(c)):used.update(globals_used(v))
 return used
used=set()
for name in functions:used.update(globals_used(ns[name].__code__))
need(not used-set(ns)-set(vars(builtins)),'helper globals before admission')
need(os.getuid()==os.geteuid()==1000,'ordinary uid')
need(pin(P)['sha256']==EXPECTED,'exact root-granted six-command manifest')
p=json.loads(P.read_text());C=Path(p['capture_root']);O=Path(p['output_root'])
need(C.parent==D and O.parent==D and not C.exists() and not O.exists(),'fresh owned output/capture roots')
C.mkdir(mode=0o700)
rows=[];failure=None;beg=time.monotonic();archive=None;binary=None;cobj=None
try:
 ns['write'](C/'ROOT-GRANT.json',dict(scope=__doc__,source='Parent collaboration followup task, current invocation',manifest_sha256=EXPECTED,grant='CPU6 onejob2GiBAS shared60CPU90wall+6retirement FSIZE32MiB stack2MiB FD256 core0',physical='dda45e/currentf37ff2 accepted per root',prior='Original wakeup command00 E0609 joined/group absent; root one bounded actual val field correction grant',acceptance_owner='/root'))
 ns['write'](C/'PLAN.json',p)
 for row in p['sources']+p['canonical_bindings']+p['frozen_actual_header_dependencies']+p['tools']+[p['compiler'],p['predecessor'],p['original_failure'],p['source_correction']]:
  need(pin(row['path'])==row,'exact source/header/tool pin '+row['path'])
 canonical=Path(p['canonical_bindings'][0]['path']).read_text()
 need((D/'fixture-source/original-wakeup.ACTUAL.inc').read_text().rstrip() in canonical,'byte-extracted original C tail still present')
 mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
 host=os.statvfs('/home/holden/mckernel-work');scratch=os.statvfs('/home/holden/mckernel-work/scratch')
 cap=dict(MemAvailable=mem,HOST_available=host.f_frsize*host.f_bavail,scratch_available=scratch.f_frsize*scratch.f_bavail,ordinary_reservation_bytes=2<<30,aggregate_grant_owner='/root')
 ns['write'](C/'CAPACITY.json',cap)
 need(mem>=2<<30 and cap['HOST_available']>=(16<<30)+(256<<20) and cap['scratch_available']>=(12<<30)+(256<<20),'ordinary memory and host/scratch evidence headroom')
 O.mkdir(mode=0o700);os.chdir(D);os.environ['RUST_MIN_STACK']='2097152';os.sched_setaffinity(0,{6})
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(r,(v,v))
 signal.setitimer(signal.ITIMER_REAL,96)
 for i,c in enumerate(p['commands']):
  remaining=90-(time.monotonic()-beg);need(remaining>0 and ns['cpu_used']()<60,'aggregate wall/CPU remainder')
  out=C/str(i).zfill(2);out.mkdir(mode=0o700);ns['write'](out/'command.json',c)
  result=ns['owned_capture'](c,out,remaining,lambda:None);ns['write'](out/'RESULT.json',result);rows.append(dict(name=c['name'],capture=str(out),result=result))
  need(result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],'first unexpected command '+c['name'])
  if i==0:
   txt=(out/'stdout').read_text()+'\n'+(out/'stderr').read_text();lines=[s.strip().split('native-static-libs:',1)[1].strip() for s in txt.splitlines() if 'native-static-libs:' in s]
   need(len(lines)==1 and 'warning:' not in txt and 'error:' not in txt,'unique native libs / no warnings')
   need(shlex.split(lines[0])==p['expected_native_static_libs'],'exact genuine compiler-native link flags')
   archive=ns['hashed'](O/'libf06_wakeup_host_1.a',32<<20)
  else:need(result['captures']['stderr']['size']==0,'unexpected stderr '+c['name'])
  if i==3:need((out/'stdout').read_text()==p['expected_stdout'],'exact10368 comparisons and30ABI')
  if i==4:
   symbols=(out/'stdout').read_text()
   for name in p['expected_symbol_T']:
    kinds=[line.split()[-2] for line in symbols.splitlines() if line.split() and line.split()[-1]==name]
    need(kinds==['T'],'unique genuine symbol '+name)
  if i==5:need('core::panicking::panic_bounds_check' in (out/'stdout').read_text(),'genuine HOST core checked-index runtime')
 need(ns['cpu_used']()<=60,'whole CPU cap')
 binary=ns['hashed'](O/'wakeup-compare',32<<20);cobj=ns['hashed'](O/'wakeup-C.o',32<<20)
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:signal.setitimer(signal.ITIMER_REAL,0)
joined=all(r['result']['direct_child_joined'] and r['result']['group_absent'] and r['result']['closed_streams'] for r in rows)
report=dict(scope=__doc__,status='PASS_ACTUAL_C_RUST_WAKEUP10368_CONTROLLED_ONLY' if failure is None else 'FAIL_STOP_FIRST_UNEXPECTED_NO_RETRY',manifest=pin(P),driver=pin(Path(__file__)),commands=rows,error=failure,seconds=time.monotonic()-beg,total_CPU=ns['cpu_used'](),whole_joined_group_absent_closed=joined,CPU6_released=joined,actual_cases=10368 if failure is None else None,ABI_values=30 if failure is None else None,archive=archive,binary=binary,C_object=cobj,default_link_native=False,controls=p['controls'])
ns['write'](C/'ACTUAL-WHOLE-JOIN.json',report)
print(json.dumps(dict(status=report['status'],commands=len(rows),error=failure,CPU6_released=joined,seconds=report['seconds']),sort_keys=True));raise SystemExit(0 if failure is None else 1)
