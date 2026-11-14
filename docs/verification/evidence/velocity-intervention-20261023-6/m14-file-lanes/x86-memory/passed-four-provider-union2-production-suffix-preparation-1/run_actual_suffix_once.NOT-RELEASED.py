"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One selected GCC9 memory consumer suffix of the root-shared combined Rust object.
"""
from pathlib import Path
import hashlib,json,os,signal,resource,sys,time,re,importlib.util,struct
P=Path(__file__).resolve().parent;R=P/'EXACT-ROOT-SHARED-RUST-REQUIREMENTS.NOT-COMPILED.json';C=P/'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.FROZEN.NOT-EXECUTED.json'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(R)=='f0f926c31e99c2619d28fea70fd7acf7cb28912637e271545ab120cbfffe67d0';assert sha(C)=='06d37eda19d174669e985573a86cb0d533d5e52408fd70978f7ed9f9b8c9155d';r=json.loads(R.read_bytes());c=json.loads(C.read_bytes())
# Actual root-produced binding is a separate immutable reviewed metadata input.
assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1])
K=P/'ROOT-COMBINED-OBJECT-BINDING.ACTUAL.json';assert sha(K)==sys.argv[1]
k=json.loads(K.read_bytes())
for field in ['Rust_object','source_manifest','Rust_compile_command','source_profile_acceptance','mem_C_object','mem_C_source','mem_C_source_acceptance']:assert k[field] is not None,field
for field in ['source_manifest','Rust_compile_command','source_profile_acceptance','mem_C_source','mem_C_source_acceptance']:assert sha(Path(k[field]['path']))==k[field]['sha256'],field
manifest=json.loads(Path(k['source_manifest']['path']).read_bytes());assert manifest['count']==78 and len(manifest['sources'])==78
x86=next(x for x in manifest['sources'] if x['relative']=='kernel/rust/x86_memory_helpers.rs')
assert x86['sha256']==r['expected_x86_Rust']['sha256'] and sha(Path(x86['path']))==x86['sha256']
lib=next(x for x in manifest['sources'] if x['relative']=='kernel/rust/lib.rs')
compiled=json.loads(Path(k['Rust_compile_command']['path']).read_bytes())['argv']
assert compiled[:-2]==r['baseline_Rust_prefix'] and compiled[-1]==lib['path'] and compiled[-2]=='--emit=obj='+k['Rust_object']['path']
for leafref in r['actual_passed_fragments']:
 assert sha(Path(leafref['ref']['path']))==leafref['ref']['sha256'];leaf=json.loads(Path(leafref['ref']['path']).read_bytes());assert leaf['status']==leafref['status'] and leaf[leafref['pair_key']]==leafref['count'] and leaf['CPU6_released'] is True
 assert all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in leaf['results'])
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8';spec=importlib.util.spec_from_file_location('capture',H);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,cap.stop)
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6};assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
os.umask(0o077);os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
A=P/'actual-attempt-1';A.mkdir(mode=0o700);O=P/'output-1';O.mkdir(mode=0o700)
def sources():
 for row in [c['private_memory_source'],c['canonical_memory_preimage'],c['ABI_witness'],c['current_canonical_mem_source'],c['arch_memory_header'],*c['reused67_header_pins'].values()]:assert sha(Path(row['path']))==row['sha256'],row
sources()
memobj=k['mem_C_object'];rustobj=k['Rust_object']
def stable(row):
 s=Path(row['path']).stat()
 for k,v in [('device',s.st_dev),('inode',s.st_ino),('size',s.st_size),('mtime_ns',s.st_mtime_ns),('ctime_ns',s.st_ctime_ns),('uid',s.st_uid),('gid',s.st_gid),('nlink',s.st_nlink)]:assert row[k]==v,(k,row['path'])
stable(memobj);stable(rustobj);assert rustobj['size']<=32<<20
host=os.statvfs(P);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512);mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
facts=dict(MemAvailable=mem,memory_required=19<<30,HOST_available=host.f_bavail*host.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=scratch.f_bavail*scratch.f_frsize,scratch_required=(12<<30)+679477248,full_sparse_gap=gap,backing_size=back.st_size,reserves=679477248);cap.write(A/'HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['HOST_available']>=facts['HOST_required'] and facts['scratch_available']>=facts['scratch_required'],facts
cap.write(A/'PRELAUNCH-SOURCE-PROFILE.json',dict(scope=__doc__,Rust_recipe_sha256=sha(R),C_recipe_sha256=sha(C),driver_sha256=sha(Path(__file__)),profile=r['profile'],interpreter=sys.executable,version=sys.version,helper_sha256=sha(H),capture_API='full module all required globals, dict argv/cwd/purpose, registeredTERMINTALRM',current_C_sourceguards=True,shared_root_object_binding_sha256=sha(K),shared_actual_source_manifest=k['source_manifest'],reused_actual_mem_object_stat=memobj))
commands=[dict(label='production-Rust-NM',argv=['/usr/bin/nm','-a',rustobj['path']],cwd=str(O)),dict(label='production-Rust-ELF',argv=['/usr/bin/readelf','-Ws',rustobj['path']],cwd=str(O))]+[dict(cmd,argv=[arg.replace('__ROOT_COMBINED_RUST_OBJECT__',rustobj['path']).replace('__ROOT_COHERENT_MEM_C_OBJECT__',memobj['path']) for arg in cmd['argv']]) for cmd in c['commands']]

def rows(t,n):return [l.split() for l in t.splitlines() if l.split()[-1:]==[n]]
def unique(t,n,kind):
 found=rows(t,n);assert len(found)==1 and found[0][-2]==kind,(n,kind,found)
results=[];artifacts={"root-shared-mckernel_rust.o":rustobj};texts={};actual_root_T=set();actual_root_U=set();previous_cwd_fd=os.open('.',os.O_RDONLY|os.O_DIRECTORY);all_children_joined=True;begin=time.monotonic();initial=cap.cpu_used();signal.setitimer(signal.ITIMER_REAL,96)
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
   u={line.split()[-1] for line in text.splitlines() if line.split()[-2:-1]==['U']};actual_root_U=u
   actual_root_T={line.split()[-1] for line in text.splitlines() if line.split()[-2:-1]==['T']}
   assert not set(r['expected_T_added'])&u and set(r['required_Rust_U_metadata'])<=u
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
   for name in set(c['expected_partial_unique_Rust_T'])|actual_root_T:unique(text,name,'T')
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
 # Reuse the same allocated-section ELF parser for the new declarative ABI.
 metadata_proof={};descriptor_proof={}
 for name,value in c['immutable_metadata'].items():
  obj=sym(name);sec=sections[obj['shndx']];assert obj['bind']==1 and obj['type']==1 and sec['flags']&2 and not sec['flags']&1
  data=payload(sec)[obj['value']:obj['value']+obj['size']]
  if value=='file':assert data==c['private_memory_source']['path'].encode()+b'\0'
  else:assert obj['size']==4 and struct.unpack('<i',data)[0]==value
  metadata_proof[name]=dict(symbol=obj,section=sec,value=value)
 for name,expected in c['debug_descriptor_sites'].items():
  obj=sym(name);sec=sections[obj['shndx']];assert obj['bind']==1 and obj['type']==1 and obj['size']==32 and sec['name']=='__verbose' and sec['flags']&3==3 and sec['align']>=8
  data=payload(sec)[obj['value']:obj['value']+32];assert struct.unpack_from('<I',data,24)[0]==expected['line'] and struct.unpack_from('<Q',data,16)[0]==0
  rs=[x for x in sections if x['type']==4 and x['info']==obj['shndx']];assert len(rs)==1 and rs[0]['link']==ss['index'];decoded={}
  for n in range(rs[0]['size']//24):
   off,info,addend=struct.unpack_from('<QQq',raw,rs[0]['offset']+n*24)
   if obj['value']<=off<obj['value']+32:
    assert info&0xffffffff==1;target=symbols[info>>32];decoded[off-obj['value']]=string(payload(sections[target['shndx']]),target['value']+addend)
  assert decoded=={0:c['private_memory_source']['path'],8:expected['function']}
  descriptor_proof[name]=dict(symbol=obj,section=sec,line=expected['line'],flags=0,fmt=None,strings=decoded)
 cap.write(A/'ACTUAL-SEVEN-IMMUTABLE-AND-FIVE-DDEBUG-DATA.json',dict(scope=__doc__,immutable=metadata_proof,debug_descriptors=descriptor_proof,qualification='Allocated sections and actual relocation strings only; runtime flags/control and page ownership are separate.'))
 sources();stable(memobj);stable(rustobj)
 for row in artifacts.values():stable(row)
 receipt=dict(scope=__doc__,status='PASS_ACTUAL_ROOT_SHARED_RUST_FOUR_PROVIDER_GCC9_SUFFIX_ONLY',results=results,seconds=time.monotonic()-begin,CPU_seconds=cap.cpu_used()-initial,artifacts=artifacts,root_binding_sha256=sha(K),root_shared_source_manifest=k['source_manifest'],actual_Rust_global_T=len(actual_root_T),actual_Rust_U=len(actual_root_U),all3086priorGlobalT_preserved=True,new_T=r['expected_T_added'],all_actual_Rust_T_preserved_in_partial=True,callbacks=proof,immutable_metadata=metadata_proof,debug_descriptors=descriptor_proof,actual_leaf_fragments=r['actual_passed_fragments'],Rust_local_compiler_commands=0,C_recipe_sha256=sha(C),requirements_sha256=sha(R),driver_sha256=sha(Path(__file__)),remaining_C_debt=c['retained_C_debt'],default_GCC14_image_native=False,CPU6_released=True)
 cap.write(P/'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json',receipt);print(json.dumps(dict(status=receipt['status'],seconds=receipt['seconds'],CPU_seconds=receipt['CPU_seconds'],commands=len(results),object=artifacts['root-shared-mckernel_rust.o'],CPU6_released=True)))
except BaseException as e:
 cap.write(A/'FAILURE.STOP.json',dict(scope=__doc__,error=repr(e),completed_commands=len(results),results=results,artifacts_durable_before_observers=artifacts,CPU6_released=True,no_retry=True));raise
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 if all_children_joined:os.fchdir(previous_cwd_fd);os.close(previous_cwd_fd)
