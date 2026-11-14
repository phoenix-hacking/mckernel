"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One actual exec-entry original-C/Rust equivalence and real ABI fixture; existing C lifecycle effect controlled.
No real exec, delegated syscall, IRQ, guest or compiler replay. Root grants CPU6 separately.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,sys,time
P=Path(__file__).resolve().parent;RF=P/'EXACT-EXEC-ENTRY-FIXTURE.NOT-GRANTED.json';A=P/'actual-fixture-1';O=P/'output-1'
records=[];durable={};armed=False;initial=os.getcwd()
def pin(q):
 b=q.read_bytes();return dict(path=str(q),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(q,v):
 with q.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
def rows(text):return [l.split() for l in text.splitlines() if l.split()]
def symbol(rs,name,kind):
 found=[x for x in rs if x[-1]==name];assert len(found)==1 and found[0][-2]==kind,(name,kind,found)
try:
 A.mkdir(mode=0o700)
 assert pin(RF)['sha256']=='f083fb60c132da2dcc3a10d902f8da3dc48786448f323027bf2667ac3fb30173'
 plan=json.loads(RF.read_bytes());assert len(plan['commands'])==8
 for row in [*plan['inputs'].values(),*plan['tools'].values(),plan['header_closure'],plan['actual_ABI'],plan['private_ABI'],plan['source_handoff'],plan['accepted_profile'],*plan['prior_failures'],*plan['forwarding_HOLD']]:assert pin(Path(row['path']))==row
 assert Path(plan['actual_ABI']['path']).read_bytes()==Path(plan['private_ABI']['path']).read_bytes()
 def relations():
  for row in plan['source_relations']:
   frag=row['exact_fragment'];assert pin(Path(frag['path']))==frag
   assert Path(row['current_source']).read_bytes().count(Path(frag['path']).read_bytes())==1,('selected body/helper relation changed',row)
 relations()
 headers=json.loads(Path(plan['header_closure']['path']).read_bytes())
 for row in headers['headers'].values():assert pin(Path(row['path']))==row
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version.startswith('3.9.12 ')
 assert not O.exists(),'refuse old output namespace'
 assert plan['commands'][0]['argv'][1:3]==['--crate-name','f03_exec_entries_actual']
 assert plan['tools'][plan['commands'][0]['argv'][0]]['sha256']=='028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1'
 c=(P/'fixture/exec_entries_actual.c').read_text();assert '__inline_memset' in c and '__inline_memcpy' in c
 H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assigns={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assigns for t in n.targets)]
 ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
 def deps(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for v in code.co_consts:
   if isinstance(v,type(code)):used.update(deps(v))
  return used
 needed=set()
 for name in names:needed.update(deps(ns[name].__code__))
 assert not needed-set(ns)-set(vars(builtins))
 write(A/'HELPER-TOOL-PROVIDER-PREFLIGHT.json',dict(scope=__doc__,helper=pin(H),dependencies=sorted(needed),missing_globals=[],namespace_dict_API=True,interpreter=sys.executable,version=sys.version,tools=plan['tools'],controlled_effect='Full do_execveat lifecycle only; actual complete Rust helpers/getters and literal C fallback remain real',no_fake_panic_or_core_ABI=True,before_first_child=True,time_ns=time.time_ns()))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_jobs_ceiling=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248,measured_time_ns=time.time_ns())
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(A/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O.mkdir(mode=0o700)
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']=str(2<<20)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 write(A/'ACTUAL-PROFILE.json',dict(scope=__doc__,recipe=pin(RF),driver=pin(Path(__file__)),profile=plan['profile'],actual_affinity=sorted(os.sched_getaffinity(0)),authority='Separate root CPU6 grant required; accepted ordinary2GiB/60CPU/90+6/F32MiB/FD256/core0/both2MiB/CGU1/h990. FirstunexpectedSTOP; one candidate plus one bounded correction before expert; prior failures and partialcontext HOLD preserved.'))
 begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);armed=True
 for op in plan['commands']:
  label=op['label'];cap=A/label;cap.mkdir(mode=0o700);cmd={k:op[k] for k in ['argv','cwd','purpose']};cmd['scope']=plan['scope'];before=os.getcwd()
  try:
   os.chdir(cmd['cwd']);cmd['actual_cwd']=os.getcwd();assert cmd['actual_cwd']==cmd['cwd'];cmd['started_time_ns']=time.time_ns();write(cap/'command.json',cmd)
   remaining=90-(time.monotonic()-begin);assert remaining>0
   j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(label=label,command=pin(cap/'command.json'),join=j))
  finally:os.chdir(before)
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],dict(label=label,join=j)
  output=(cap/'stdout').read_text()
  if label=='03-actual-exec-entry-equivalence':assert output==plan['expected_stdout'],output
  if label=='04-original-C-and-existing-provider-symbols':
   rs=rows(output)
   for name in ['sys_execve','sys_execveat']:symbol(rs,name,'U')
   symbol(rs,'syscall_execveat_bridge','T')
   for name in ['f03_original_sys_execve','f03_original_sys_execveat']:symbol(rs,name,'T')
  if label=='05-actual-Rust-genuine-provider-closure':
   rs=rows(output)
   for name in plan['Rust_exports']:symbol(rs,name,'T')
   undefined={x[-1] for x in rs if x[-2]=='U'};assert undefined<=set(plan['allowed_Rust_undefined']),('missing actual provider outside controlled lifecycle/host memory closure',sorted(undefined))
   write(cap/'ACTUAL-PROVIDER-CLOSURE.json',dict(scope=__doc__,actual_undefined=sorted(undefined),allowed=plan['allowed_Rust_undefined'],no_fake_panic_or_core_ABI=True))
  if label=='07-partial-selected-unique-symbols':
   rs=rows(output)
   for name in ['sys_execve','sys_execveat','syscall_execveat_bridge']:symbol(rs,name,'T')
  artifacts={'00-Rust-actual-entries-genuine-getters-and-helpers':'exec_entries_Rust.o','01-C-original-entries-fallback-real-structures':'exec_entries_C.o','02-link-original-C-and-actual-Rust':'exec_entries_actual','06-original-C-actual-Rust-partial':'exec_entries_partial.o'}
  if label in artifacts:
   durable[artifacts[label]]=ns['hashed'](O/artifacts[label],32<<20);write(cap/'DURABLE-OBJECT-HASHED-ONCE.json',dict(object=durable[artifacts[label]],before_later_consumers=True))
  assert ns['cpu_used']()<=60
 for row in plan['inputs'].values():assert pin(Path(row['path']))==row
 for row in headers['headers'].values():assert pin(Path(row['path']))==row
 assert pin(Path(plan['actual_ABI']['path']))==plan['actual_ABI'];relations()
 for v in durable.values():
  z=Path(v['path']).lstat();assert stat.S_ISREG(z.st_mode) and z.st_dev==v['device'] and z.st_ino==v['inode'] and z.st_size==v['size'] and z.st_mtime_ns==v['mtime_ns'] and z.st_ctime_ns==v['ctime_ns']
 result=dict(scope=__doc__,status='PASS_ACTUAL_LITERAL_C_RUST_EXEC_ENTRIES_4788_PAIRS_14_REAL_LAYOUT_AND_PARTIAL_ONLY',recipe=pin(RF),profile=pin(A/'ACTUAL-PROFILE.json'),headroom=pin(A/'ACTUAL-HEADROOM.json'),records=records,objects=durable,execve_pairs=84,execveat_pairs=4704,total_pairs=4788,real_layout_fields=14,actual_exec_lifecycle=False,original_C_provider_debt=plan['C_provider_debt'],firstbyte_prepolicy_read_preserved_valid_buffer_only=True,invalid_filename_pointer_EFAULT_proof=False,CPU6_released=True,seconds=time.monotonic()-begin,total_CPU_seconds=ns['cpu_used'](),prior_failures=plan['prior_failures'],partial_context_hold=plan['forwarding_HOLD'],canonical_mutations=0,engineering_percentage=None,current_full78=False,default_link=False,native=False,file_retired=False)
 write(A/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(A/'ACTUAL-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 if A.exists():write(A/'FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_AUTOMATIC_RETRY',error=type(exc).__name__+': '+str(exc),records=records,objects_retained=durable,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)))
 raise
finally:
 if armed:signal.setitimer(signal.ITIMER_REAL,0)
 os.chdir(initial)
