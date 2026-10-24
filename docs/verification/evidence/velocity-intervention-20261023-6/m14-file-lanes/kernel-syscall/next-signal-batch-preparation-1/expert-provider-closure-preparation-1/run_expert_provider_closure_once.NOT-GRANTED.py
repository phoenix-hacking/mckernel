"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One controlled actual C/Rust three-body signal batch plus real headers/whole selected TU/partial ownership.
No signalfd replay/full78/native/IRQ/scheduler/guest execution. Root grants CPU6 separately.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,sys,time
E=Path(__file__).resolve().parent;N=E.parent;B=N/'bounded-monitor-scaffold-correction-1';F=E/'output-1';A=E/'actual-provider-closure-1';RF=E/'EXACT-EXPERT-PROVIDER-CLOSURE.NOT-GRANTED.json'
records=[];durable={};armed=False;initial=os.getcwd()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
def rows(text):return [l.split() for l in text.splitlines() if l.split()]
def symbol(rs,name,kind):
 found=[x for x in rs if x[-1]==name];assert len(found)==1 and found[0][-2]==kind,(name,kind,found)
 return found[0]
try:
 A.mkdir(mode=0o700)
 assert pin(RF)['sha256']=='968270b92ebceafc9b3668dc573ae7b11de1e9681f9eed89ff738a3522814e22'
 plan=json.loads(RF.read_bytes());old=json.loads(Path(plan['original_recipe']['path']).read_bytes());corrected=json.loads(Path(plan['corrected_recipe']['path']).read_bytes());assert len(plan['commands'])==12
 for row in [plan['original_recipe'],plan['corrected_recipe'],plan['corrected_driver'],plan['provider_relation'],plan['link_stderr'],*plan['retained_history']]:assert pin(Path(row['path']))==row
 for row in [*old['source_inputs'].values(),*plan['source_inputs'].values()]:assert pin(Path(row['path']))==row
 provider_relation=json.loads(Path(plan['provider_relation']['path']).read_bytes())
 for item in provider_relation['source_fragments'].values():
  for key in ['actual_source','byteexact_fragment']:assert pin(Path(item[key]['path']))==item[key]
  assert Path(item['actual_source']['path']).read_bytes().count(Path(item['byteexact_fragment']['path']).read_bytes())==1
 for row in provider_relation['header_sources']:assert pin(Path(row['path']))==row
 for row in [old['accepted_prior_signalfd'],old['Rust192_profile_reused'],old['GCC9_profile_reused'],*old['prior_failures'],corrected['scaffold_source'],corrected['source_delta']]:assert pin(Path(row['path']))==row
 for item in corrected['quote_include_transport']:
  for key in ['original','corrected_transport']:assert pin(Path(item[key]['path']))==item[key]
 def meta(q):
  z=q.lstat();assert stat.S_ISREG(z.st_mode) and z.st_nlink==1
  return dict(path=str(q),device=z.st_dev,inode=z.st_ino,uid=z.st_uid,gid=z.st_gid,mode=oct(stat.S_IMODE(z.st_mode)),nlink=z.st_nlink,size=z.st_size,mtime_ns=z.st_mtime_ns,ctime_ns=z.st_ctime_ns)
 for item in plan['retained_objects']:
  row=item['object'];assert meta(Path(row['path']))=={k:row[k] for k in meta(Path(row['path']))};durable[Path(row['path']).name]=row
 positive_path=E/'RETAINED-POSITIVE-COMMAND00-AND-CORRECTED01.json'
 assert pin(positive_path)['sha256']=='9db754579f1a9bad6ad27fea2a93861e19df912a1bec289ccf6a6cb3108e5b4e'
 positive=json.loads(positive_path.read_bytes())
 for item in positive['positive']:
  for key in ['command','whole_join','profile']:assert pin(Path(item[key]['path']))==item[key]
  j=item['record']['whole_join'];assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None
  for cap in j['captures'].values():
   raw=Path(cap['path']).read_bytes();assert len(raw)==cap['size'] and hashlib.sha256(raw).hexdigest()==cap['sha256']
 expected=[]
 for row in corrected['commands'][1:]:
  argv=[plan['exact_argv_substitutions'].get(a,a) for a in row['argv']]
  if row['label']=='02-link-actual-C-Rust-fixture':argv.insert(argv.index('-o'),str(F/'selected_providers.o'))
  if row['label']=='10-actual-three-body-partial-link':argv.append(str(F/'selected_providers.o'))
  expected.append(dict(row,argv=argv,cwd=str(E)))
 assert plan['commands'][2:]==expected
 closure=json.loads(Path(old['header_closure']['path']).read_bytes())
 for row in closure['headers'].values():assert pin(Path(row['path']))==row
 relation=json.loads(Path(old['current_union_relations']['path']).read_bytes())
 for key in ['current_union_C','current_union_policy','current_union_process_helpers']:
  row=relation[key];assert pin(Path(row['path']))==row
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version.startswith('3.9.12 ')
 F.mkdir(mode=0o700)
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)];ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def deps(code):
  found={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for c in code.co_consts:
   if isinstance(c,type(code)):found.update(deps(c))
  return found
 needed=set()
 for name in names:needed.update(deps(ns[name].__code__))
 assert not needed-set(ns)-set(vars(builtins))
 tools={str(p):pin(p) for p in [Path(plan['commands'][0]['argv'][0]),Path('/usr/bin/gcc-9'),Path('/usr/bin/ld'),Path('/usr/bin/nm'),Path(sys.executable)]}
 assert tools[plan['commands'][0]['argv'][0]]['sha256']=='028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1'
 write(A/'HELPER-TOOL-PROVIDER-PREFLIGHT.json',dict(scope=__doc__,helper=pin(helper),missing_globals=[],namespace_dict_API=True,dependencies=sorted(needed),interpreter=sys.executable,version=sys.version,tools=tools,known_kernelstring_memset_provider='explicit host-only byte loop ABI unsignedlong/size_t',controlled_host_callbacks=True,before_first_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_jobs_ceiling=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(A/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']=str(2<<20)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 write(A/'ACTUAL-PROFILE.json',dict(scope=__doc__,recipe=pin(RF),driver=pin(Path(__file__)),CPU=[6],jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,stack_bytes=2<<20,authority='Root must separately grant expert-adopted exact real Rust provider closure only; old00 and corrected01 reused without replay; both FAIL preserved; firstunexpectedSTOPexpert no automatic retry'))
 begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);armed=True
 for operation in plan['commands']:
  label=operation['label'];cap=A/label;cap.mkdir(mode=0o700);cmd={k:operation[k] for k in ['argv','cwd','purpose']};cmd['scope']=plan['scope'];prior=os.getcwd()
  try:
   os.chdir(cmd['cwd']);cmd['actual_cwd']=os.getcwd();write(cap/'command.json',cmd);remaining=90-(time.monotonic()-begin);assert remaining>0
   joined=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',joined);records.append(dict(label=label,capture=str(cap),whole_join=joined))
  finally:os.chdir(prior)
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],dict(label=label,join=joined)
  output=(cap/'stdout').read_text()
  if label=='P1-check-seven-provider-NM-closure':
   rs=rows(output);exported={x[-1] for x in rs if x[-2]=='T'};undefined={x[-1] for x in rs if x[-2]=='U'};assert exported==set(plan['provider_exports']) and not undefined,(exported,undefined)
  if label=='03-actual-three-body-equivalence':assert output=='PASS_F03_ACTUAL_C_RUST_SIGNAL_BATCH pending=128 sigsuspend=144 sigaction=5440 total=5712 real_layout_fields=34 consumed_node_poison=144 host_forward_error_ignored=1488 controlled_callbacks_only=1\n',output
  if label=='06-selected-full-TU-preprocess':
   for name in plan['exports']+['do_sigsuspend','syscall_sigcommon_writer_lock_bridge','syscall_sigcommon_writer_unlock_bridge']:
    assert re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',output,re.S) is None,('selected C body remains',name)
   assert len(re.findall(r'\bsyscall_forward_sigaction_update_bridge\s*\([^;{}]*\)\s*\{',output,re.S))==1
  if label in ['08-selected-C-ownership','09-actual-Rust-ownership','11-partial-linked-ownership']:
   rs=rows(output)
   for name in plan['exports']:
    if label=='08-selected-C-ownership':assert not any(x[-1]==name and x[-2] in ['T','t'] for x in rs),(name,'C body still selected')
    else:symbol(rs,name,'T')
   if label in ['08-selected-C-ownership','11-partial-linked-ownership']:symbol(rs,'syscall_forward_sigaction_update_bridge','T')
  artifacts={'P0-compile-exact-existing-seven-Rust-providers':'selected_providers.o','02-link-actual-C-Rust-fixture':'signal_batch_actual','07-selected-complete-C-TU':'selected-signal-syscall.o','10-actual-three-body-partial-link':'selected-signal-plus-Rust.o'}
  if label in artifacts:
   name=artifacts[label];durable[name]=ns['hashed'](F/name,32<<20);write(cap/'DURABLE-OBJECT-HASHED-ONCE.json',dict(object=durable[name],before_later_consumers=True))
  assert ns['cpu_used']()<=60
 for row in [*old['source_inputs'].values(),*plan['source_inputs'].values()]:assert pin(Path(row['path']))==row
 for row in closure['headers'].values():assert pin(Path(row['path']))==row
 for key in ['current_union_C','current_union_policy','current_union_process_helpers']:
  row=relation[key];assert pin(Path(row['path']))==row
 for item in provider_relation['source_fragments'].values():
  for key in ['actual_source','byteexact_fragment']:assert pin(Path(item[key]['path']))==item[key]
 for row in provider_relation['header_sources']:assert pin(Path(row['path']))==row
 for item in plan['retained_objects']:
  row=item['object'];assert meta(Path(row['path']))=={k:row[k] for k in meta(Path(row['path']))}
 result=dict(scope=__doc__,status='PASS_F03_EXPERT_REAL_RUST_PROVIDER_CLOSURE_REUSED_RUST00_C01_5712_CASES_ABI_TU_PARTIAL_ONLY',recipe=pin(RF),profile=pin(A/'ACTUAL-PROFILE.json'),headroom=pin(A/'ACTUAL-HEADROOM.json'),current_union_relations=old['current_union_relations'],records=records,objects_hashed_once=durable,actual_cases=plan['expected_cases'],old_signalfd_replays=0,full78_production_Rust=False,GCC14_default_link=False,native=False,file_retired=False,C_forward_partial_context_debt=plan['C_forward_debt'],first_signalfd_failure_history=old['prior_failures'],threebody_failure_history=plan['retained_history'],reused_positive_object_provenance=pin(positive_path),original_Rust00_replays=0,corrected_C01_replays=0,new_seven_provider_compiler_invocations=1,canonical_mutations=0,CPU6_released=True,seconds=time.monotonic()-begin,total_CPU_seconds=ns['cpu_used']())
 write(A/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(A/'ACTUAL-WHOLE-JOIN.json'),commands=len(records),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 write(A/'FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY',error=type(exc).__name__+': '+str(exc),records=records,objects_retained=durable,CPU6_released=all(r['whole_join']['direct_child_joined'] and r['whole_join']['group_absent'] and r['whole_join']['closed_streams'] for r in records)));raise
finally:
 if armed:signal.setitimer(signal.ITIMER_REAL,0)
 os.chdir(initial)
