"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary actual selectedGCC9 wholememory/headerABI/ownership/reloc/partialld-r check.
No Rust recompile/rehash, no GCC14/defaultkernel/native claim.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,time,re
P=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'};body=[]
for n in ast.parse(raw,str(SOURCE)).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets):body.append(n)
ns={'__file__':str(SOURCE)};exec(compile(ast.Module(body=body,type_ignores=[]),str(SOURCE),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6};os.environ['RUST_MIN_STACK']='2097152'
packet=P/'PREPARED-ACTUAL-CONSUMER-COMMANDS.json';assert hashlib.sha256(packet.read_bytes()).hexdigest()=='f1eb5ed05eac4e6733fdccbf630c3333944b9bec72ee07c055c28ef13ad5ae5d';j=json.loads(packet.read_text())
for key in ('canonical_memory','canonical_Rust','C_mem_provider_source','ABI_witness','Rust_source78_authority','Rust_compile_recipe','accepted_C_mem_provider_receipt','base_GCC9_recipe','base_ld_r_recipe'):
 pin=j[key];assert hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['sha256'],key
obj=j['Rust_object_durable_metadata']
def check_Rust_stat():
 s=os.lstat(obj['path']);assert stat.S_ISREG(s.st_mode) and s.st_dev==obj['device'] and s.st_ino==obj['inode'] and s.st_size==obj['size'] and s.st_mtime_ns==obj['mtime_ns'] and s.st_ctime_ns==obj['ctime_ns'] and s.st_uid==obj['uid'] and s.st_gid==obj['gid'] and s.st_nlink==obj['nlink'] and stat.S_IMODE(s.st_mode)==int(obj['mode'],8)
check_Rust_stat()
cap=P/'actual-owned-capture-1';cap.mkdir(mode=0o700)
host=os.statvfs(P);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=os.stat('/home/holden/mckernel-work/scratch.ext4');gap=max(0,back.st_size-512*back.st_blocks);mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(scope=__doc__,HOST_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,backing_size=back.st_size,backing_blocks=back.st_blocks,full_sparse_gap=gap,HOST_required=17179869184+gap+16106090496+377487360+679477248+67108864,scratch_required=13631488000,MemAvailable=mem,root_reserved_memory=19*1073741824)
ns['write'](cap/'ACTUAL-PRE-CAPACITY.json',facts);assert facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'] and mem>=19*1073741824,facts
ns['write'](cap/'commands.json',dict(commands=j['commands'],source_bindings_sha256='f1eb5ed05eac4e6733fdccbf630c3333944b9bec72ee07c055c28ef13ad5ae5d',Rust_durable_object=obj,Rust_object_not_rehashed=True,Rust_recompile=False))
def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
def unique(text,name,kind):
 found=rows(text,name);assert len(found)==1 and found[0][-2]==kind,(name,kind,found)
durable_artifacts={}
begin=time.monotonic();start_ns=time.time_ns();initial=ns['cpu_used']();results=[];texts={}
for i,command in enumerate(j['commands'],1):
 remaining=90-(time.monotonic()-begin);cpu=60-(ns['cpu_used']()-initial);assert remaining>0 and cpu>0;child_cpu=max(1,int(cpu))
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 os.chdir(command['cwd']);out=cap/str(i);out.mkdir(mode=0o700);ns['write'](out/'command.json',command)
 result=ns['owned_capture'](command,out,remaining,limits);ns['write'](out/'whole-join.json',result);results.append(dict(label=command['label'],result=result))
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
 if command['label']=='selected-complete-memory-TU':durable_artifacts['memory.c.o']=ns['hashed'](P/'memory.c.o',32<<20)
 if command['label']=='actual-selected-partial-link':durable_artifacts['selected-consumer-provider.o']=ns['hashed'](P/'selected-consumer-provider.o',32<<20)
 text=(out/'stdout').read_text();texts[command['label']]=text
 if command['label']=='selected-memory-preprocess':
  for name in ('clear_range','ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_top_log_bridge'):
   assert re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',text,re.S) is None,('oldCbodyselected',name)
  assert re.search(r'\bextern\s+int\s+x86_clear_range_public_body\s*\(',text) is not None
 if command['label']=='memory-symbols':
  unique(text,'x86_clear_range_public_body','U')
  for name in ('ihk_mc_pt_clear_range','ihk_mc_pt_free_range'):
   assert not any(r[-2] in ('T','t') for r in rows(text,name)),name
  unique(text,'x86_clear_range_walk_l4_bridge','T')
  assert not any(r[-2] in ('T','t') for r in rows(text,'x86_clear_range_top_log_bridge'))
 if command['label']=='memory-relocations':assert 'x86_clear_range_public_body' in text
 if command['label']=='actual-mem-provider-symbols':unique(text,'remote_flush_tlb_array_cpumask','T')
 if command['label']=='partial-symbols':
  for name in j['expected_Rust_providers']+j['expected_C_providers']:unique(text,name,'T')
check_Rust_stat()
for key in ('canonical_memory','canonical_Rust','C_mem_provider_source'):
 pin=j[key];assert hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['sha256']
artifacts=durable_artifacts
for name,pin in artifacts.items():
 st=(P/name).stat();assert st.st_size==pin['size'] and st.st_ino==pin['inode'] and st.st_mtime_ns==pin['mtime_ns']
whole=dict(scope=__doc__,status='PASS_ACTUAL_GCC9_SELECTED_COMPLETE_MEMORY_TU_REAL_HEADER_ABI_C_RUST_OWNERSHIP_RELOCATION_PARTIAL_LINK_ONLY',results=results,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used']()-initial,start_ns=start_ns,end_ns=time.time_ns(),artifacts=artifacts,Rust_durable_object_not_rehashed=obj,Rust_recompile=False,actual_Rust_providers=j['expected_Rust_providers'],actual_C_providers=j['expected_C_providers'],remaining2_C_providers_remain_computeC_debt=True,top_log_Rust_selected=True,default_GCC14_image_link_native=False)
ns['write'](cap/'ACTUAL-WHOLE-JOIN.json',whole);print(json.dumps(whole,sort_keys=True))
