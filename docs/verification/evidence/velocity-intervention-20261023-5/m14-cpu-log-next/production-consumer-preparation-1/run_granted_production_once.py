"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time,sys,dis,builtins,types
R=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assigns={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
tree=ast.parse(H.read_bytes());nodes=[]
for n in tree.body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):nodes.append(n)
 elif isinstance(n,ast.FunctionDef) and n.name in functions:nodes.append(n)
 elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assigns for t in n.targets):nodes.append(n)
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_needed(code):
 out={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
 for v in code.co_consts:
  if isinstance(v,types.CodeType):out.update(globals_needed(v))
 return out
for n in functions:
 assert not (globals_needed(ns[n].__code__)-set(ns)-set(vars(builtins))),n


write=ns['write'];records=[];durable={};begin=time.monotonic();A=R/'actual-production-capture-1';os.umask(0o077);A.mkdir(mode=0o700);failure=None
def rows(text):return [x.split() for x in text.splitlines() if x.split()]
def names(rs,k):return {x[-1] for x in rs if len(x)>=2 and x[-2]==k}
def unique(rs,n,kinds):
 x=[a for a in rs if a[-1]==n];assert len(x)==1 and x[0][-2] in kinds,(n,x);return x[0]
def statbound(v):
 st=Path(v['path']).lstat()
 for k,a in [('device','st_dev'),('inode','st_ino'),('size','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:assert v[k]==getattr(st,a),(v['path'],k)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:assert resource.getrlimit(k)==(v,v)
 os.environ['RUST_MIN_STACK']='2097152'
 READY=R/'PRODUCTION-CONSUMER-READY.json';RF=R/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json';CF=R/'EXACT-SELECTED-GCC9-CPU-CONSUMER.NOT-EXECUTED.json'
 assert sha(READY)=='65cc8b7c9b235209a86deba7a46f5dd6892355a49bba4cb9c09b3ea204eaaeeb'
 assert sha(RF)=='c7d01f3ea67dffac02f43b380eb17892a0021644ae5be183cb1d71374e41a0fa'
 assert sha(CF)=='23d181b4760598d30bb423ce665b8a191281ab327cac3c06ee31839d6ae0a051'
 ready=json.loads(READY.read_bytes());r=json.loads(RF.read_bytes());c=json.loads(CF.read_bytes());oracle=json.loads((R/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json').read_bytes())
 assert r['source_identity']=='b97b717aa69760f3792bff5ae5e5a4d8797c79a9305d3466d9e5b7c04cd10ee6'
 for v in r['source_inputs'].values():
  for k in ['private','canonical_before']:assert sha(Path(v[k]['path']))==v[k]['sha256'],v[k]['path']
 frozen=[c['private_source'],c['canonical_preimage'],c['ABI_witness'],c['actual_selected_declaration_source'],*c['actual_header_closure'].values(),*c['current_canonical_headers'].values(),*c['tools'].values(),r['exact_symbol_oracle'],r['source_patch'],r['actual_CPU_log_leaf'],r['accepted_F04_profile_recipe'],r['accepted_F04_actual_profile_proof']]
 for v in frozen:assert sha(Path(v['path']))==v['sha256'],v['path']
 assert len(r['argv'])==48 and sha(Path(r['argv'][6]))==r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bk.st_size-bk.st_blocks*512)
 fact={'MemAvailable':mem,'required_memory':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7,'root_exclusive_CPU6_grant':True}
 write(R/'ACTUAL-HEADROOM.json',fact);assert mem>=fact['required_memory'] and fact['HOST_available']>=fact['HOST_required'] and fact['scratch_available']>=fact['scratch_required']
 write(R/'ACTUAL-PROFILE.json',{'scope':__doc__,'profile':r['profile'],'source_identity':r['source_identity'],'Rust_recipe_sha256':sha(RF),'C_recipe_sha256':sha(CF),'driver_sha256':sha(Path(__file__)),'helper_sha256':sha(H),'all_helper_global_dependencies_checked':True,'TERM_INT_ALRM_registered':True,'accepted_profile_48argv_preserved':True})
 O=R/'output-1';O.mkdir(mode=0o700);os.chdir(O);signal.setitimer(signal.ITIMER_REAL,96)
 commands=ready['commands'];assert len(commands)==11;texts={}
 for i,item in enumerate(commands):
  left=90-(time.monotonic()-begin);assert left>0 and ns['cpu_used']()<60
  cap=A/item['label'];cap.mkdir(mode=0o700);cmd={'argv':item['argv'],'purpose':__doc__+' '+item['label'],'cwd':str(O)};write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,left,lambda:None);write(cap/'whole-join.json',j);records.append({'name':item['label'],'join':j})
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  texts[item['label']]=(cap/'stdout').read_text()
  if i in (0,5,9):
   name={0:'mckernel_rust.o',5:'cpu.c.o',9:'cpu-rust-partial.o'}[i];durable[name]=ns['hashed'](O/name,32<<20);write(R/('DURABLE-'+name+'.json'),{'object':durable[name],'join':j,'hashed_once_before_observers':True})
  if i==1:
   rn=rows(texts[item['label']]);assert names(rn,'U')==set(oracle['expected_U']),(len(names(rn,'U')),names(rn,'U')-set(oracle['expected_U']),set(oracle['expected_U'])-names(rn,'U'))
   assert names(rn,'T')==set(oracle['expected_T'])
   unique(rn,'x86_cpu_ulong_log_bridge',{'T'});unique(rn,'kprintf',{'T'})
   write(R/'ACTUAL-RUST-SYMBOL-RECEIPT.json',{'scope':__doc__,'status':'PASS_CURRENT78_U584_UNCHANGED_ALL3045_PRIOR_T_PRESERVED_CPU_LOG_NEW_T','object':durable['mckernel_rust.o'],'source_identity':r['source_identity'],'U_count':len(names(rn,'U')),'T_count':len(names(rn,'T')),'new_T':'x86_cpu_ulong_log_bridge','U_added':[],'U_removed':[]})
  if i==2:
   elf=[x for x in rows(texts[item['label']]) if x[-1]=='x86_cpu_ulong_log_bridge'];assert len(elf)==1 and elf[0][3:5]==['FUNC','GLOBAL'] and elf[0][6]!='UND'
  if i==3:
   import re
   assert re.search(r'\bx86_cpu_ulong_log_bridge\s*\([^;{}]*\)\s*\{',texts[item['label']],re.S) is None
  if i==6:
   cn=rows(texts[item['label']]);unique(cn,'x86_cpu_ulong_log_bridge',{'U'})
   for name in c['expected_C_callback_providers']:unique(cn,name,{'T'})
   data=unique(cn,c['expected_data']['name'],{c['expected_data']['kind']});assert int(data[-3],16)==c['expected_data']['size']
  if i==7:
   relevant=[];section=''
   for line in texts[item['label']].splitlines():
    if line.startswith('Relocation section '):section=line
    if 'x86_cpu_ulong_log_bridge' in line and '.rela.text' in section:relevant.append(line)
   assert len(relevant)==c['expected_named_target_relocations'],relevant
   write(R/'ACTUAL-DEFAULT-CPU-CALLBACK-RELOCATIONS.json',{'scope':__doc__,'target':'x86_cpu_ulong_log_bridge','actual_text_relocations':relevant,'expected_current_source_callers':c['expected_real_C_callback_callers'],'count':len(relevant)})
  if i==10:
   pn=rows(texts[item['label']])
   for name in oracle['expected_T']+c['expected_C_callback_providers']:unique(pn,name,{'T'})
   unique(pn,'kprintf',{'T'});assert 'x86_cpu_ulong_log_bridge' not in names(pn,'U')
   data=unique(pn,c['expected_data']['name'],{c['expected_data']['kind']});assert int(data[-3],16)==c['expected_data']['size']
 for v in durable.values():statbound(v)
 for v in r['source_inputs'].values():assert sha(Path(v['private']['path']))==v['private']['sha256']
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] and x['join']['retirement_error'] is None for x in records)
 out={'scope':__doc__,'status':'PASS_CURRENT78_RUST_COMPLETE_SELECTED_GCC9_CPU_TU_REAL_CALLBACK_ABI_RELOCATIONS_AND_PARTIAL_ONLY' if failure is None else 'FAIL_FIRST_UNEXPECTED_STOP_NO_RETRY','error':failure,'completed_commands':len(records),'records':records,'objects':durable,'seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used'](),'source_identity':r['source_identity'] if 'r' in globals() else None,'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'canonical_writes':0,'GCC14_defaultkernel_link_native':False,'all_other_C_debt_preserved':True,'compiler_replay_authorized':False}
 write(R/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',out);print(json.dumps({k:out[k] for k in ['status','error','completed_commands','seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
