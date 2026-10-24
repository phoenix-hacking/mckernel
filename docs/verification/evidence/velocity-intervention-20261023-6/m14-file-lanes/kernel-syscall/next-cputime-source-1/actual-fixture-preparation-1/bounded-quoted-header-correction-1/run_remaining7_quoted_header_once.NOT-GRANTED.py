"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded exact quoted-header materialization correction; suffix05-11 only; retain passed00-04.
No live IRQ/clock/timer/signal/kernel effects; Root grants CPU6 separately.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,sys,time
C=Path(__file__).resolve().parent;P=C.parent;RF=C/'EXACT-REMAINING7-QUOTED-HEADER.NOT-GRANTED.json';A=C/'actual-remaining7-1';O=C/'output-1'
records=[];durable={};armed=False;initial=os.getcwd()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
def rows(text):return [l.split() for l in text.splitlines() if l.split()]
def symbol(rs,name,kind):
 found=[x for x in rs if x[-1]==name];assert len(found)==1 and found[0][-2]==kind,(name,kind,found)
try:
 A.mkdir(mode=0o700)
 assert pin(RF)['sha256']=='d898ce133ef2ef652ae27a828a112b4ade8ee052495fb67dc363d29d3aa01d75'
 plan=json.loads(RF.read_bytes());assert len(plan['commands'])==7
 for key in ['original_recipe','first_failure','first_failed_stderr','materialization','retained_positive']:
  v=plan[key];assert pin(Path(v['path']))==v
 original=json.loads(Path(plan['original_recipe']['path']).read_bytes())
 expected=[dict(v,argv=[plan['argv_output_substitutions'].get(a,a) for a in v['argv']]) for v in original['commands'][5:]]
 assert plan['commands']==expected
 positive=json.loads(Path(plan['retained_positive']['path']).read_bytes())
 assert len(positive['records'])==5 and positive['objects']==plan['retained_objects']
 for rec in positive['records']:
  j=rec['join'];assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None
  for cap in j['captures'].values():
   raw=Path(cap['path']).read_bytes();assert len(raw)==cap['size'] and hashlib.sha256(raw).hexdigest()==cap['sha256']
 assert Path(positive['runtime_stdout']['path']).read_text()==plan['expected_stdout']
 def retained_meta(q):
  z=q.lstat();assert stat.S_ISREG(z.st_mode) and z.st_nlink==1
  return dict(path=str(q),device=z.st_dev,inode=z.st_ino,uid=z.st_uid,gid=z.st_gid,mode=oct(stat.S_IMODE(z.st_mode)),nlink=z.st_nlink,size=z.st_size,mtime_ns=z.st_mtime_ns,ctime_ns=z.st_ctime_ns)
 for name,v in plan['retained_objects'].items():
  assert retained_meta(Path(v['path']))=={k:v[k] for k in retained_meta(Path(v['path']))};durable[name]=v
 material=json.loads(Path(plan['materialization']['path']).read_bytes())
 assert pin(Path(material['original']['path']))==material['original'] and pin(Path(material['private']['path']))==material['private']
 assert (P/'candidate'/material['literal_quote']).resolve()==Path(material['quote_resolution'])
 assert Path(material['original']['path']).read_bytes()==Path(material['private']['path']).read_bytes()
 assert not re.findall(rb'^\s*#\s*include\b',Path(material['original']['path']).read_bytes(),re.M)

 for row in plan['inputs'].values():assert pin(Path(row['path']))==row
 for row in plan['canonical'].values():assert pin(Path(row['path']))==row
 for row in plan['provider_sources'].values():assert pin(Path(row['path']))==row
 for k in ['production_source_handoff','original_profile','corrected_quote_transport_authority','headers','Rust_tool','prior_failure_history','forwarding_HOLD']:
  row=plan[k];assert pin(Path(row['path']))==row
 for row in plan['tools'].values():assert pin(Path(row['path']))==row
 relation=plan['body_relation']
 assert Path(relation['original_C']['path']).read_bytes()==Path(relation['fixture_C_original']['path']).read_bytes()
 assert Path(relation['production_Rust']['path']).read_bytes()==Path(relation['fixture_Rust']['path']).read_bytes()
 assert Path(plan['canonical']['C']['path']).read_bytes().count(Path(relation['original_C']['path']).read_bytes())==1
 provider_raw={k:Path(v['path']).read_bytes() for k,v in plan['provider_sources'].items()}
 for name in ['tsc_to_ts','ts_add','ts_to_tv','tv_sub']:
  raw=(P/'fixture'/(name+'.UNCHANGED-RUST.inc')).read_bytes()
  source=next(v for k,v in provider_raw.items() if k.endswith('/syscall_policy.rs' if name=='tsc_to_ts' else '/timer.rs'))
  assert source.count(raw)==1,('not byteexact actual provider',name)
 headers=json.loads(Path(plan['headers']['path']).read_bytes())
 for row in headers['headers'].values():assert pin(Path(row['path']))==row
 for t in headers['quote_transport']:
  assert pin(Path(t['original']['path']))==t['original'] and pin(Path(t['private']['path']))==t['private']
  assert Path(t['original']['path']).read_bytes()==Path(t['private']['path']).read_bytes()
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version.startswith('3.9.12 ')
 assert not O.exists(),'refuse existing output namespace'
 rust=original['commands'][0]['argv'];assert rust[1:3]==['--crate-name','f03_cputime_actual'] and plan['Rust_tool']['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 fixture=(P/'fixture/cputime_actual.c').read_text();assert '__inline_memset' in fixture and '__inline_memcpy' in fixture and 'fixture_monitor' in fixture and '#undef cpu_disable_interrupt_save' in fixture
 actual=(P/'fixture/cputime_actual.rs').read_text();assert '#![feature(core_intrinsics)]' in actual and 'panic_handler' not in actual
 H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
 ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
 def deps(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for v in code.co_consts:
   if isinstance(v,type(code)):used.update(deps(v))
  return used
 needed=set()
 for name in functions:needed.update(deps(ns[name].__code__))
 assert not needed-set(ns)-set(vars(builtins))
 write(A/'HELPER-TOOL-PROVIDER-PREFLIGHT.json',dict(scope=__doc__,helper=pin(H),missing_globals=[],namespace_dict_API=True,dependencies=sorted(needed),tools=plan['tools'],actual_interpreter=sys.executable,version=sys.version,real_arithmetic=plan['actual_arithmetic'],controlled_effects=plan['controlled_effects'],no_fake_panic_provider=True,before_first_child=True,time_ns=time.time_ns()))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_jobs_ceiling=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248,measured_time_ns=time.time_ns())
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(A/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O.mkdir(mode=0o700)
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']=str(2<<20)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 write(A/'ACTUAL-PROFILE.json',dict(scope=__doc__,recipe=pin(RF),driver=pin(Path(__file__)),profile=plan['profile'],actual_affinity=sorted(os.sched_getaffinity(0)),authority='Root separate explicit grant required; accepted ordinary2GiB/60CPU/90+6/F32MiB/FD256/core0/bothstacks2MiB/CGU1/h990. Sole bounded header correction; next unexpected failure STOP expert; all signal families and partialcontext HOLD retained. No other body folded.'))
 begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);armed=True
 for op in plan['commands']:
  label=op['label'];cap=A/label;cap.mkdir(mode=0o700);cmd={k:op[k] for k in ['argv','cwd','purpose']};cmd['scope']=plan['scope'];before=os.getcwd()
  try:
   os.chdir(cmd['cwd']);cmd['actual_cwd']=os.getcwd();assert cmd['actual_cwd']==cmd['cwd'];cmd['started_time_ns']=time.time_ns();write(cap/'command.json',cmd)
   remaining=90-(time.monotonic()-begin);assert remaining>0
   joined=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',joined);records.append(dict(label=label,command=pin(cap/'command.json'),join=joined))
  finally:os.chdir(before)
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],dict(label=label,join=joined)
  output=(cap/'stdout').read_text()
  if label=='03-actual-cputime-equivalence':assert output==plan['expected_stdout'],output
  if label=='06-selected-complete-TU-preprocess':
   for name in ['reset_cputime','set_cputime']:assert re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',output,re.S) is None,('C body still selected',name)
  if label=='08-selected-C-symbols':
   rs=rows(output)
   for name in ['reset_cputime','set_cputime']:assert not any(x[-1]==name and x[-2] in ['T','t'] for x in rs),name
   symbol(rs,'set_cputime','U')
  if label=='09-actual-Rust-provider-closure':
   rs=rows(output)
   for name in plan['expected_Rust_exports']:symbol(rs,name,'T')
   undefined={x[-1] for x in rs if x[-2]=='U'};assert undefined<=set(plan['allowed_Rust_undefined']),('unresolved real provider outside explicit effect/host-memory closure',sorted(undefined))
   write(cap/'ACTUAL-PROVIDER-CLOSURE.json',dict(scope=__doc__,exports=plan['expected_Rust_exports'],actual_undefined=sorted(undefined),allowed=plan['allowed_Rust_undefined'],no_fake_panic_or_core_ABI=True))
  if label=='11-partial-symbols':
   rs=rows(output)
   for name in ['reset_cputime','set_cputime']:symbol(rs,name,'T')
  artifacts={'00-Rust-actual-cputime-and-real-time-providers':'cputime_actual.o','01-C-original-cputime-real-structures':'cputime_actual_C.o','02-link-actual-cputime-fixture':'cputime_actual','07-selected-complete-C-TU':'selected-cputime-syscall.o','10-selected-C-plus-Rust-partial':'selected-cputime-plus-Rust.o'}
  if label in artifacts:
   durable[artifacts[label]]=ns['hashed'](O/artifacts[label],32<<20);write(cap/'DURABLE-OBJECT-HASHED-ONCE.json',dict(object=durable[artifacts[label]],before_later_consumers=True))
  assert ns['cpu_used']()<=60
 for row in [*plan['inputs'].values(),*plan['canonical'].values(),*plan['provider_sources'].values()]:assert pin(Path(row['path']))==row
 for row in headers['headers'].values():assert pin(Path(row['path']))==row
 for row in durable.values():
  st=Path(row['path']).lstat();assert stat.S_ISREG(st.st_mode) and st.st_dev==row['device'] and st.st_ino==row['inode'] and st.st_size==row['size'] and st.st_mtime_ns==row['mtime_ns'] and st.st_ctime_ns==row['ctime_ns']
 result=dict(scope=__doc__,status='PASS_ACTUAL_CPUTIME_RETAINED3255_48LAYOUT_AND_CORRECTED_REAL_HEADERS_GCC9_TU_PARTIAL_ONLY',recipe=pin(RF),profile=pin(A/'ACTUAL-PROFILE.json'),headroom=pin(A/'ACTUAL-HEADROOM.json'),records=records,objects=durable,retained_positive=plan['retained_positive'],original_first_failure=plan['first_failure'],materialization=plan['materialization'],new_commands=7,retained_commands=5,Rust_compiler_invocations=0,old_runtime_replays=0,reset_pairs=12,set_pairs=3243,total_pairs=3255,real_layout_fields=48,actual_os_effects=False,CPU6_released=True,seconds=time.monotonic()-begin,total_CPU_seconds=ns['cpu_used'](),prior_failure_history=plan['prior_failure_history'],partial_context_hold_preserved=plan['forwarding_HOLD'],canonical_mutations=0,engineering_percentage=None,full78_production=False,default_link=False,native=False,file_retired=False)
 write(A/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(A/'ACTUAL-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 if A.exists():write(A/'FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_AUTOMATIC_RETRY',error=type(exc).__name__+': '+str(exc),records=records,objects_retained=durable,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)))
 raise
finally:
 if armed:signal.setitimer(signal.ITIMER_REAL,0)
 os.chdir(initial)
