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

write=ns['write'];records=[];durable={};begin=time.monotonic();A=R/'actual-production-capture-1'
os.umask(0o077);A.mkdir(mode=0o700);failure=None
def rows(text):return [x.split() for x in text.splitlines() if x.split()]
def names(rs,kind):return {x[-1] for x in rs if len(x)>=2 and x[-2]==kind}
def unique(rs,name,kinds):
 a=[x for x in rs if x[-1]==name];assert len(a)==1 and a[0][-2] in kinds,(name,a)
def statbound(row):
 st=Path(row['path']).lstat()
 for key,attr in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid'),('nlink','st_nlink'),('size','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:assert row[key]==getattr(st,attr),(key,row['path'])
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:assert resource.getrlimit(k)==(v,v)
 os.environ['RUST_MIN_STACK']='2097152'
 RF=R/'EXACT-CURRENT78-RUST-RECIPE.GRANTED.json';CF=R/'EXACT-SELECTED-GCC9-MEM-CONSUMER.GRANTED.json'
 assert sha(RF)=='7180b7a6c7bea966ae7b540e556755032c00838be8c73ab236ecc89ad9557351'
 assert sha(CF)=='a9180461d1ffe0d20115461e04d97e119d86876a11ff7c0df0b241ed24713ffc'
 r=json.loads(RF.read_bytes());c=json.loads(CF.read_bytes());oracle=json.loads((R/'EXPECTED-SYMBOLS.json').read_bytes())
 for v in r['source_inputs'].values():
  for key in ['private','canonical_before']:assert sha(Path(v[key]['path']))==v[key]['sha256'],v[key]['path']
 for v in [c['private_source'],c['canonical_preimage'],c['ABI_witness'],*c['actual_header_closure'].values(),*c['current_canonical_headers'].values(),*c['tools'].values(),c['actual_scalar_C_consumer']['source'],c['actual_scalar_C_consumer']['retained_NM'],c['actual_scalar_C_consumer']['retained_relocations'],r['symbol_oracle']]:assert sha(Path(v['path']))==v['sha256'],v['path']
 assert sha(Path(r['argv'][6]))==r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 statbound(c['actual_scalar_C_consumer']['retained_object_not_rehashed']);statbound(oracle['baseline_object_not_rehashed'])
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bk.st_size-bk.st_blocks*512)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
 fact={'MemAvailable':mem,'memory_required':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7,'CPU6_root_exclusive_grant':True}
 write(R/'ADMISSION.json',fact);assert mem>=fact['memory_required'] and fact['HOST_available']>=fact['HOST_required'] and fact['scratch_available']>=fact['scratch_required']
 write(R/'ACTUAL-PROFILE.json',{'scope':__doc__,'profile':r['profile'],'source_identity':r['source_identity'],'Rust_recipe_sha256':sha(RF),'C_recipe_sha256':sha(CF),'driver_sha256':sha(Path(__file__)),'all_helper_global_dependencies_checked':True,'TERM_INT_ALRM_registered':True})
 O=R/'output-1';O.mkdir(mode=0o700);os.chdir(O);signal.setitimer(signal.ITIMER_REAL,96)
 commands=[{'label':'00-current78-Rust-compile','argv':r['argv']},{'label':'01-current78-Rust-symbols','argv':['/usr/bin/nm','-g',str(O/'mckernel_rust.o')]},{'label':'02-current78-Rust-ELF','argv':['/usr/bin/readelf','--wide','--syms',str(O/'mckernel_rust.o')]}]+c['commands'];assert len(commands)==12
 texts={}
 for i,item in enumerate(commands):
  remaining=90-(time.monotonic()-begin);assert remaining>0 and ns['cpu_used']()<60
  cap=A/item['label'];cap.mkdir(mode=0o700);cmd={'argv':item['argv'],'purpose':__doc__+' '+item['label']};write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append({'label':item['label'],'join':j})
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  texts[item['label']]=(cap/'stdout').read_text()
  if i in (0,5,10):
   name={0:'mckernel_rust.o',5:'mem.c.o',10:'mem-arch-rust-partial.o'}[i];durable[name]=ns['hashed'](O/name,32<<20);write(R/('DURABLE-'+name+'.json'),{'object':durable[name],'join':j,'before_observers':True})
  if i==1:
   rn=rows(texts[item['label']]);assert names(rn,'U')==set(oracle['expected_U'])
   assert names(rn,'T')==set(oracle['expected_T'])
   for name in c['expected_partial_Rust_entry_unique_T']:unique(rn,name,{'T'})
   write(R/'ACTUAL-RUST-SYMBOL-RECEIPT.json',{'status':'PASS_CURRENT78_SCALAR_T_ADDITION_U577_UNCHANGED_ALL3042_PRIOR_T_PRESERVED','object':durable['mckernel_rust.o'],'source_identity':r['source_identity'],'U_count':len(names(rn,'U')),'T_count':len(names(rn,'T')),'new_T':'remote_flush_tlb_cpumask','U_removed':[],'U_added':[]})
  if i==2:
   er=[x for x in rows(texts[item['label']]) if x[-1]=='remote_flush_tlb_cpumask'];assert len(er)==1 and er[0][3:5]==['FUNC','GLOBAL'] and er[0][6]!='UND'
  if i==3:
   import re
   for name in c['expected_entries']:assert re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',texts[item['label']],re.S) is None
  if i==6:
   cn=rows(texts[item['label']])
   for name in c['expected_entries']:assert not [x for x in cn if x[-1]==name]
   for name in c['expected_C_callback_providers']:unique(cn,name,{'T'})
   unique(cn,'mem_remote_tlb_geometry',{'R'});unique(cn,'tlb_flush_vector',{'B','C'})
  if i==9:assert 'remote_flush_tlb_cpumask' in texts[item['label']]
  if i==11:
   pn=rows(texts[item['label']])
   for name in oracle['expected_T']+c['expected_C_callback_providers']:unique(pn,name,{'T'})
   for name in c['expected_entries']:assert name not in names(pn,'U')
   unique(pn,'mem_remote_tlb_geometry',{'R'});unique(pn,'tlb_flush_vector',{'B','C'})
 for row in durable.values():statbound(row)
 for v in r['source_inputs'].values():assert sha(Path(v['private']['path']))==v['private']['sha256']
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] and x['join']['retirement_error'] is None for x in records)
 receipt={'scope':__doc__,'status':'PASS_CURRENT78_RUST_COMPLETE_GCC9_MEM_TU_REAL_CURRENT_ARCH_CONSUMER_AND_THREE_OBJECT_PARTIAL_ONLY' if failure is None else 'FAIL_STOPPED_FIRST_UNEXPECTED_NO_RETRY','error':failure,'records':records,'objects':durable,'completed_commands':len(records),'source_identity':r['source_identity'] if 'r' in globals() else None,'elapsed_seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'remaining_C_callbacks':13,'exactGCC14_defaultkernel_native':False,'canonical_writes':0,'compiler_replay_authorized':False}
 write(R/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',receipt);print(json.dumps({k:receipt[k] for k in ['status','error','completed_commands','elapsed_seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
