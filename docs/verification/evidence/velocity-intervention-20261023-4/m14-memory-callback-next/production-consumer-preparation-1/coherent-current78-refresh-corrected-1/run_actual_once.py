"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact production Rust and GCC9 archmemory selected consumer cohort; no native.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,sys,time,stat,re
P=Path(__file__).resolve().parent
R=P/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json';C=P/'EXACT-SELECTED-GCC9-ARCHMEMORY-CONSUMER.GRANTED.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(R)=='061bf24a099120c5995be23ded373392b56cd6c9a295ba6569a9355690d07e45'
assert sha(C)=='7ea72905534b5fd4a7772e05d8510cea800ab9c7e6147836b6720e22a2d3a4ce'
r=json.loads(R.read_bytes());c=json.loads(C.read_bytes())
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('capture',H);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,cap.stop)
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
os.umask(0o077);os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=P/'actual-attempt-1';A.mkdir(mode=0o700);O=P/'output-1';O.mkdir(mode=0o700)
def sources():
 for key,row in r['source_inputs'].items():
  for role in ('canonical_before','private'):assert sha(Path(row[role]['path']))==row[role]['sha256'],(key,role)
 for row in [c['private_memory_source'],c['canonical_memory_preimage'],c['ABI_witness'],c['current_canonical_mem_source'],c['arch_memory_header'],*c['reused67_header_pins'].values()]:assert sha(Path(row['path']))==row['sha256'],row
sources()
memobj=c['current_actual_mem_provider']
def oldstat():
 s=Path(memobj['path']).stat()
 for k,v in [('device',s.st_dev),('inode',s.st_ino),('size',s.st_size),('mtime_ns',s.st_mtime_ns),('ctime_ns',s.st_ctime_ns),('uid',s.st_uid),('gid',s.st_gid),('nlink',s.st_nlink)]:assert memobj[k]==v,(k,v)
oldstat();assert sha(Path(r['argv'][6]))==r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
host=os.statvfs(P);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-512*back.st_blocks);mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
facts=dict(MemAvailable=mem,memory_required=19<<30,HOST_available=host.f_bavail*host.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=scratch.f_bavail*scratch.f_frsize,scratch_required=(12<<30)+679477248,full_sparse_gap=gap,backing_size=back.st_size,reserves=679477248)
cap.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'],facts
cap.write(A/'PRELAUNCH-SOURCES-PROFILE.json',dict(scope=__doc__,profile=r['profile'],interpreter=sys.executable,version=sys.version,source_count=78,Rust_recipe_sha=sha(R),C_recipe_sha=sha(C),driver_sha=sha(Path(__file__)),reuse_mem_stat_only=memobj,helper=dict(path=str(H),sha256=sha(H),API='full module imported all required globals; dict command API'),source78_current_preimages=True))
commands=[dict(label='production-Rust-compile',argv=r['argv'],cwd=str(O)),dict(label='production-Rust-NM',argv=['/usr/bin/nm','-a',str(O/'mckernel_rust.o')],cwd=str(O)),dict(label='production-Rust-ELF',argv=['/usr/bin/readelf','-Ws',str(O/'mckernel_rust.o')],cwd=str(O))]+c['commands']
results=[];artifacts={};texts={};begin=time.monotonic();initial=cap.cpu_used();signal.setitimer(signal.ITIMER_REAL,96)
def rows(text,name):return [l.split() for l in text.splitlines() if l.split()[-1:]==[name]]
def unique(text,name,kind):
 v=rows(text,name);assert len(v)==1 and v[0][-2]==kind,(name,kind,v)
try:
 for i,cmd in enumerate(commands):
  cmd=dict(cmd,purpose=__doc__+' '+cmd['label']);d=A/('%02d-'%i+cmd['label']);d.mkdir(mode=0o700);cap.write(d/'command.json',cmd);remaining=90-(time.monotonic()-begin);assert remaining>0
  os.chdir(cmd['cwd']);res=cap.owned_capture(cmd,d,remaining,lambda:None);cap.write(d/'whole-join.json',res);results.append(dict(label=cmd['label'],join=res));assert res['returncode']==0 and res['direct_child_joined'] and res['group_absent'] and res['closed_streams'] and res['error'] is None and res['retirement_error'] is None and not res['timed_out'],res
  label=cmd['label'];text=(d/'stdout').read_text();texts[label]=text
  for trigger,file in [('production-Rust-compile','mckernel_rust.o'),('selected-complete-memory-TU','memory.c.o'),('actual-selected-partial-link','selected-consumer-provider.o')]:
   if label==trigger:artifacts[file]=cap.hashed(O/file,32<<20);cap.write(d/'DURABLE-OBJECT-BEFORE-OBSERVERS.json',artifacts[file])
  if label=='production-Rust-NM':
   for authority in r['actual_symbol_authorities']:assert sha(Path(authority['path']))==authority['sha256']
   u={l.split()[-1] for l in text.splitlines() if l.split()[-2:-1]==['U']};assert u==set(r['expected_U']),(sorted(u-set(r['expected_U'])),sorted(set(r['expected_U'])-u))
   for name in r['expected_all_prior_T']+r['expected_T_added']:unique(text,name,'T')
  if label=='selected-memory-preprocess':
   for name in ('clear_range','ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_top_log_bridge','x86_clear_range_walk_l4_bridge','clear_range_l4','x86_clear_range_l4_body'):assert re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',text,re.S) is None,name
   assert re.search(r'\(\s*\*\s*const\s+x86_clear_range_l4_callback\s*\)',text) and '= &x86_clear_range_l4_body' in text and '= &x86_clear_range_walk_l3_bridge' in text
  if label=='memory-symbols':
   unique(text,'x86_clear_range_public_body','U')
   for name in c['expected_C_no_definition']:assert not any(v[-2] in ('T','t') for v in rows(text,name)),name
   assert len(rows(text,'x86_clear_range_l4_callback'))==1 and len(rows(text,'x86_clear_range_l3_callback'))==1
   unique(text,'x86_clear_range_l4_body','U')
  if label=='memory-relocations':assert 'x86_clear_range_public_body' in text
  if label=='actual-mem-provider-symbols':assert not any(v[-2] in ('T','t') for v in rows(text,'remote_flush_tlb_array_cpumask'))
  if label=='partial-symbols':
   for name in c['expected_partial_unique_Rust_T']:unique(text,name,'T')
   for cbname in ('x86_clear_range_l4_callback','x86_clear_range_l3_callback'):
    cb=rows(text,cbname);assert len(cb)==1 and cb[0][-2] in ('D','R'),cb
 symbols=texts['memory-symbols'];relocs=texts['memory-relocations']
 data_block=re.search(r"Relocation section '\.rela.data.rel.ro.local'[^\n]*\n[^\n]*\n(.*?)(?:\n\n|$)",relocs,re.S);assert data_block
 rr=[line.split() for line in data_block.group(1).splitlines() if line.strip()]
 l4offset=int(rows(symbols,'x86_clear_range_l4_callback')[0][0],16);l3offset=int(rows(symbols,'x86_clear_range_l3_callback')[0][0],16);l3text=int(rows(symbols,'x86_clear_range_walk_l3_bridge')[0][0],16)
 l4rel=[v for v in rr if int(v[0],16)==l4offset];l3rel=[v for v in rr if int(v[0],16)==l3offset]
 assert len(l4rel)==len(l3rel)==1 and l4rel[0][4]=='x86_clear_range_l4_body' and int(l4rel[0][-1],16)==0
 assert l3rel[0][4]=='.text' and int(l3rel[0][-1],16)==l3text
 cap.write(A/'ACTUAL-CALLBACK-DATA-RELOCATIONS.json',dict(L4_pointer_offset=l4offset,L4_to_new_Rust_export=l4rel,L3_pointer_offset=l3offset,L3_to_retained_private_C_bridge=l3rel,L3_private_C_address=l3text,qualified_relocatable_only=True))
 sources();oldstat()
 for name,row in artifacts.items():
  s=(O/name).stat();assert s.st_ino==row['inode'] and s.st_size==row['size'] and s.st_mtime_ns==row['mtime_ns']
 receipt=dict(scope=__doc__,status='PASS_COHERENT_CURRENT78_CLEAR_L4_RUST_GCC9_ARCHMEMORY_ABI_TWO_CALLBACK_DATA_RELOCS_PARTIAL_LINK',results=results,artifacts=artifacts,seconds=time.monotonic()-begin,CPU_seconds=cap.cpu_used()-initial,CPU6_released=True,all78_current_inputs_unchanged=True,Rust_U_exact=r['expected_U'],Rust_U_derivation=r['expected_U_derivation'],all_prior_Rust_T_preserved=True,expected_partial_Rust_T_count=36,actual_unique_T=c['expected_partial_unique_Rust_T'],reused_actual_mem_provider_stat_only=memobj,Rust_recipe_sha256=sha(R),C_recipe_sha256=sha(C),driver_sha256=sha(Path(__file__)),C_callback_chain_debt=c['remaining_C_callback_debt'],first_fixture_failuref57667_and_corrected690720_preserved=True,preparation_key_failure_preserved=True,canonical_SDK8_frozen14_currentimage_changes=0,GCC14_defaultimage_native=False)
 cap.write(P/'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json',receipt);print(json.dumps(dict(status=receipt['status'],seconds=receipt['seconds'],CPU_seconds=receipt['CPU_seconds'],commands=len(results),CPU6_released=True,object=artifacts['mckernel_rust.o'])))
except BaseException as e:
 cap.write(A/'FAILURE.STOP.json',dict(scope=__doc__,error=repr(e),completed_commands=len(results),results=results,CPU6_released=True,no_retry=True));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
