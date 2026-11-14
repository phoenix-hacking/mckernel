"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One frozen actual78 Rust production build and selected GCC9 memory consumer cohort.
"""
from pathlib import Path
import hashlib,json,os,signal,resource,sys,time,re,importlib.util,struct
P=Path(__file__).resolve().parent;R=P/'EXACT-PRODUCTION-RUST-RECIPE.FROZEN.NOT-EXECUTED.json';C=P/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(R)=='6846c74b488d258d3bd3b67823624000ba3d6f761683815a26a4b23c6f246c1f';assert sha(C)=='8dfa7e80cc639a7fdf29a28c73ebb0b0079f2676c64eb250439aff82ee7afcbc';r=json.loads(R.read_bytes());c=json.loads(C.read_bytes())
# Both real leaf receipts and actual pinned78 staging are mandatory before compilation.
for key,status,pairs in [('actual_leaf','PASS_ACTUAL_COMPLETE_CLEAR_RANGE_L2_1728_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI',1728),('actual_L1_fixture_receipt','PASS_ACTUAL_COMPLETE_CLEAR_RANGE_L1_432_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI',432)]:
 ref=r[key];assert ref is not None and sha(Path(ref['path']))==ref['sha256'];leaf=json.loads(Path(ref['path']).read_bytes());assert leaf['status']==status and leaf['actual_pairs']==pairs and leaf['CPU6_released'] is True
 assert all(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None for j in leaf['captures'])
batch_ref=r['actual_six_provider_receipt'];assert sha(Path(batch_ref['path']))==batch_ref['sha256'];batch=json.loads(Path(batch_ref['path']).read_bytes());assert batch['status']=='PASS_ACTUAL_SIX_PROVIDER_C_RUST_BATCH_AND_REAL_ABI' and batch['on_off_total_pairs']==937 and batch['CPU6_released'] is True
assert len(batch['results'])==10 and all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] and x['join']['error'] is None and x['join']['retirement_error'] is None for x in batch['results'])
staging_ref=r['actual_source78_materialization'];assert staging_ref is not None and sha(Path(staging_ref['path']))==staging_ref['sha256'];staged=json.loads(Path(staging_ref['path']).read_bytes());assert staged['status']=='PASS_FINITE_PINNED78_SOURCE_STAGING_ONLY' and staged['source_count']==78 and staged['all_current_canonical_pins_equal'] is True and staged['all67_header_pins_equal'] is True
assert sha(Path(staged['source_manifest']['path']))==staged['source_manifest']['sha256']
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8';spec=importlib.util.spec_from_file_location('capture',H);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,cap.stop)
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6};assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
os.umask(0o077);os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
A=P/'actual-attempt-1';A.mkdir(mode=0o700);O=P/'output-1';O.mkdir(mode=0o700)
def sources():
 assert len(r['source_inputs'])==78
 for key,row in r['source_inputs'].items():
  for role in ['canonical_before','private']:assert sha(Path(row[role]['path']))==row[role]['sha256'],(key,role)
 for row in [c['private_memory_source'],c['canonical_memory_preimage'],c['ABI_witness'],c['current_canonical_mem_source'],c['arch_memory_header'],*c['reused67_header_pins'].values()]:assert sha(Path(row['path']))==row['sha256'],row
sources();assert sha(Path(r['argv'][6]))==r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
memobj=c['current_actual_mem_provider']
def stable(row):
 s=Path(row['path']).stat()
 for k,v in [('device',s.st_dev),('inode',s.st_ino),('size',s.st_size),('mtime_ns',s.st_mtime_ns),('ctime_ns',s.st_ctime_ns),('uid',s.st_uid),('gid',s.st_gid),('nlink',s.st_nlink)]:assert row[k]==v,(k,row['path'])
stable(memobj)
host=os.statvfs(P);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512);mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(MemAvailable=mem,memory_required=19<<30,HOST_available=host.f_bavail*host.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=scratch.f_bavail*scratch.f_frsize,scratch_required=(12<<30)+679477248,full_sparse_gap=gap,backing_size=back.st_size,reserves=679477248);cap.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'],facts
cap.write(A/'PRELAUNCH-SOURCE-PROFILE.json',dict(scope=__doc__,Rust_recipe_sha256=sha(R),C_recipe_sha256=sha(C),driver_sha256=sha(Path(__file__)),profile=r['profile'],interpreter=sys.executable,version=sys.version,helper_sha256=sha(H),capture_API='full module all required globals, dict argv/cwd/purpose, registeredTERMINTALRM',current78_sourceguards=True,reused_actual_mem_object_stat=memobj))
commands=[dict(label='production-Rust-compile',argv=r['argv'],cwd=str(O)),dict(label='production-Rust-NM',argv=['/usr/bin/nm','-a',str(O/'mckernel_rust.o')],cwd=str(O)),dict(label='production-Rust-ELF',argv=['/usr/bin/readelf','-Ws',str(O/'mckernel_rust.o')],cwd=str(O))]+c['commands']
def rows(t,n):return [l.split() for l in t.splitlines() if l.split()[-1:]==[n]]
def unique(t,n,kind):
 found=rows(t,n);assert len(found)==1 and found[0][-2]==kind,(n,kind,found)
results=[];artifacts={};texts={};previous_cwd_fd=os.open('.',os.O_RDONLY|os.O_DIRECTORY);all_children_joined=True;begin=time.monotonic();initial=cap.cpu_used();signal.setitimer(signal.ITIMER_REAL,96)
try:
 for i,cmd in enumerate(commands):
  cmd=dict(cmd,purpose=__doc__+' '+cmd['label']);d=A/('%02d-'%i+cmd['label']);d.mkdir(mode=0o700);cap.write(d/'command.json',cmd);os.chdir(cmd['cwd']);remaining=90-(time.monotonic()-begin);assert remaining>0
  assert Path(cmd['cwd']).resolve()==O and Path.cwd()==O
  all_children_joined=False
  j=cap.owned_capture(cmd,d,remaining,lambda:None);all_children_joined=j['direct_child_joined'] and j['group_absent'] and j['closed_streams'];cap.write(d/'whole-join.json',j);results.append(dict(label=cmd['label'],join=j));assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  label=cmd['label'];text=(d/'stdout').read_text();texts[label]=text
  for trigger,file in [('production-Rust-compile','mckernel_rust.o'),('selected-complete-memory-TU','memory.c.o'),('actual-selected-partial-link','selected-consumer-provider.o')]:
   if label==trigger:artifacts[file]=cap.hashed(O/file,32<<20);cap.write(d/'DURABLE-OBJECT-BEFORE-OBSERVERS.json',artifacts[file])
  if label=='production-Rust-NM':
   u={line.split()[-1] for line in text.splitlines() if line.split()[-2:-1]==['U']};assert u==set(r['expected_U']) and len(u)==572,(sorted(u-set(r['expected_U'])),sorted(set(r['expected_U'])-u))
   for name in r['expected_all_prior_T']+r['expected_T_added']:unique(text,name,'T')
  if label=='production-Rust-ELF':
   for name in r['expected_T_added']:
    found=rows(text,name);assert len(found)==1 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND',found
  if label=='selected-memory-preprocess':
   for name in c['expected_C_no_definition']+['clear_range_l4','x86_clear_range_top_log_bridge']:assert re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',text,re.S) is None,name
   for name in c['expected_new_immutable_callback_data']:assert name in text
  if label=='memory-symbols':
   for name in c['expected_C_import']:unique(text,name,'U')
   unique(text,'x86_clear_range_public_body','U')
   for name in c['expected_C_no_definition']:assert not any(v[-2] in ('T','t') for v in rows(text,name)),name
  if label=='memory-relocations':
   imported_relocs={}
   for name in c['expected_C_import']+['x86_clear_range_public_body']:
    found=[line.split() for line in text.splitlines() if len(line.split())>=5 and line.split()[2].startswith('R_X86_64_') and line.split()[4]==name];assert found,(name,'missing exact-symbol C relocation');imported_relocs[name]=found
   cap.write(A/'ACTUAL-EXACT-CLEAR-CALLBACK-IMPORT-RELOCATIONS.json',dict(scope=__doc__,exact_symbol_field=4,proof=imported_relocs))
  if label=='actual-mem-provider-symbols':
   for name in ['remote_flush_tlb_array_cpumask','remote_flush_tlb_cpumask']:assert not any(v[-2] in ('T','t') for v in rows(text,name)),name
  if label=='partial-symbols':
   for name in c['expected_partial_unique_Rust_T']+c['expected_partial_all_prior_Rust_T']:unique(text,name,'T')
 # Exact expert section-aware ELF observer. Each named pointer gets its own
 # symbol section identity before looking at relocation offsets in that section.
 raw=(O/'memory.c.o').read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64
 shoff,shnum,shstr=eh[6],eh[12],eh[13];sections=[dict(zip(['name_off','type','flags','addr','offset','size','link','info','align','entsize'],struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*64))) for i in range(shnum)]
 def payload(sec):return raw[sec['offset']:sec['offset']+sec['size']]
 def string(tab,off):return tab[off:tab.index(b'\0',off)].decode()
 names=payload(sections[shstr])
 for i,s in enumerate(sections):s.update(index=i,name=string(names,s['name_off']))
 symsecs=[s for s in sections if s['type']==2];assert len(symsecs)==1;ss=symsecs[0];assert ss['entsize']==24;strings=payload(sections[ss['link']]);symbols=[]
 for i in range(ss['size']//24):
  no,info,other,idx,val,size=struct.unpack_from('<IBBHQQ',raw,ss['offset']+i*24);symbols.append(dict(index=i,name=string(strings,no),bind=info>>4,type=info&15,shndx=idx,value=val,size=size))
 def sym(name):
  found=[s for s in symbols if s['name']==name];assert len(found)==1,(name,found);return found[0]
 targets=dict(c['expected_new_immutable_callback_data'],x86_clear_range_l4_callback='x86_clear_range_l4_body',x86_clear_range_l3_callback='x86_clear_range_walk_l3_bridge');proof={}
 for ptrname,targetname in targets.items():
  ptr=sym(ptrname);assert ptr['bind']==1 and ptr['type']==1 and ptr['size']==8;section=sections[ptr['shndx']];assert section['align']>=8
  relsecs=[s for s in sections if s['type']==4 and s['info']==ptr['shndx']];assert len(relsecs)==1;rs=relsecs[0];assert rs['link']==ss['index'] and rs['entsize']==24
  found=[]
  for n in range(rs['size']//24):
   off,info,addend=struct.unpack_from('<QQq',raw,rs['offset']+n*24)
   if off==ptr['value']:found.append(dict(offset=off,type=info&0xffffffff,target=symbols[info>>32],addend=addend))
  assert len(found)==1 and found[0]['type']==1;rel=found[0];target=sym(targetname);reltarget=rel['target']
  if target['shndx']==0:assert target['bind']==1 and reltarget['name']==targetname and reltarget['bind']==1 and reltarget['shndx']==0 and rel['addend']==0
  else:
   assert target['bind']==0 and reltarget['type']==3 and reltarget['shndx']==target['shndx'] and reltarget['value']+rel['addend']==target['value']
   assert target['type']==(1 if targetname=='use_1gb_page' else 2)
   if targetname=='use_1gb_page':assert target['size']==4
  proof[ptrname]=dict(pointer=ptr,target=target,section=section,relocation_section=rs,relocation=rel)
 assert len(proof)==10
 cap.write(A/'ACTUAL-TEN-CALLBACK-DATA-RELOCATIONS.json',dict(scope=__doc__,status='PASS_EXACT_SYMBOL_SECTION_RELA_SH_INFO_TARGETS_ALL10',proof=proof,section_offset_identity_not_merged=True,qualification='Relocatable object only; no finalimage protection/native claims'))
 sources();stable(memobj)
 for row in artifacts.values():stable(row)
 receipt=dict(scope=__doc__,status='PASS_ACTUAL_CURRENT_UNION78_SIX_PROVIDER_FULLCRATE_GCC9_MEMORY_ABI_TEN_TYPED_DATA_RELOCS_AND_PARTIAL_LINK',results=results,seconds=time.monotonic()-begin,CPU_seconds=cap.cpu_used()-initial,artifacts=artifacts,source_count=78,all_current78_sources_unchanged=True,Rust_U_exact_count=572,Rust_U_delta=r['expected_U_delta'],all3065priorGlobalT_preserved=True,new_T=r['expected_T_added'],partial_selected_Rust_unique_T=len(c['expected_partial_unique_Rust_T']),all_prior_Rust_global_T_partial=len(c['expected_partial_all_prior_Rust_T']),reused_current_scalar_mem_object_not_rehashed=memobj,Rust_recipe_sha256=sha(R),C_recipe_sha256=sha(C),driver_sha256=sha(Path(__file__)),callbacks=proof,all_first_compile_and_writer_failures_preserved=True,canonical_frozen15_P12_changes=0,actual_L2_fixture=r['actual_leaf'],actual_L1_fixture=r['actual_L1_fixture_receipt'],actual_six_provider_fixture=r['actual_six_provider_receipt'],actual_pinned78_staging=staging_ref,remaining_C_debt=c['retained_C_debt'],default_GCC14_image_native=False,CPU6_released=True)
 cap.write(P/'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json',receipt);print(json.dumps(dict(status=receipt['status'],seconds=receipt['seconds'],CPU_seconds=receipt['CPU_seconds'],commands=len(results),object=artifacts['mckernel_rust.o'],CPU6_released=True)))
except BaseException as e:
 cap.write(A/'FAILURE.STOP.json',dict(scope=__doc__,error=repr(e),completed_commands=len(results),results=results,artifacts_durable_before_observers=artifacts,CPU6_released=True,no_retry=True));raise
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 if all_children_joined:os.fchdir(previous_cwd_fd);os.close(previous_cwd_fd)
