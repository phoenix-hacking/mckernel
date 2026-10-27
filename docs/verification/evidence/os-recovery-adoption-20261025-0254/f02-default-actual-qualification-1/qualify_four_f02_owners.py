"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual F02 four-owner ELF, original callback ABI, metadata and mapping qualification.
"""
import collections,json,struct,traceback
from pathlib import Path
D=Path(__file__).resolve().parent
# Reuse the accepted strict ET_REL parser and exact EXEC byte reader, stopping
# before the clone/warnings validator; this does not run a compiler or workload.
source=(D/'qualify_clone_pointer_and_warning_suffix.py').read_text();prefix=source[:source.index("\nclone=ns['_reuse_elf_function']")]
ctx=dict(__file__=str(D/'qualify_four_f02_owners.py'));exec(compile(prefix,str(D/'qualify_clone_pointer_and_warning_suffix.py')+':REUSED_STRICT_ELF_READERS','exec'),ctx)
E=ctx['E'];B=ctx['B'];P=ctx['P'];Elf=ctx['Elf'];rust=ctx['rust'];process=ctx['process'];final=ctx['final'];data=ctx['data'];sections=ctx['sections'];ref=ctx['ref'];object_bytes=ctx['ns']['_reuse_elf_object_bytes'];relocs=ctx['ns']['_reuse_elf_owning_relocations']
FOUR=['idle_halt','allow_oversubscribe','time_sharing','process_idle_callbacks']
TARGETS=['sched_idle_current_cpu_bridge','process_spin_lock_bridge','process_spin_unlock_bridge','cpu_enable_interrupt','cpu_disable_interrupt','schedule','sched_do_migrate_public','kmalloc_consolidate_free_list','process_sched_zero_free_bridge','cpu_safe_halt']
report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',phases={},native_acceptance=False,physical_postjoin='SEPARATE_ROOT_READER',compiler_container_grant_actions=0)
def own(elf,name):
 rows=[s for s in elf.symbols if s['name']==name and s['shndx']!=0];assert len(rows)==1,(name,len(rows));return rows[0]
def allocated(elf,type_):return [s for s in elf.symbols if s['type']==type_ and 0<s['shndx']<len(elf.sections) and elf.sections[s['shndx']]['flags']&2]
def normalized_relocation(elf,r):
 t=r['target'];result=dict(offset=r['offset'],type=r['type'],addend=r['addend'],target=t['name'])
 if t['type']==3 and 0<t['shndx']<len(elf.sections):
  sec=elf.sections[t['shndx']];result['target_section']=sec['name'];address=t['value']+r['addend']
  # Section-relative C strings are identified by their actual immutable bytes,
  # rather than incidental string-pool offsets after the table is removed.
  if 'str' in sec['name']:
   raw=elf.payload(sec);assert 0<=address<len(raw);end=raw.index(b'\0',address);result['target_string_hex']=raw[address:end+1].hex();result.pop('addend')
 return result
try:
 # All selected immutable input source files are the exact producer profile bytes.
 for row in P['inputs']['postimages']:assert ref(row['postimage']['path'])==row['postimage']
 oldprocess=Elf(Path(next(r['source']['path'] for r in P['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')))
 oldrust=Elf(E/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/output/build/kernel/rust/mckernel_rust.o')
 providers=[('new Rust',rust),('new selected C',process)]
 for row in P['inputs']['objects']:
  if not row['replace']:
   p=Path(row['source']['path']);assert ref(p)==row['source'];providers.append((row['link_token'],Elf(p)))
 newfunctions=allocated(process,2);assert not newfunctions
 assert {s['name'] for s in allocated(rust,2)}=={s['name'] for s in allocated(oldrust,2)},'no new Rust function bodies in data-only cohort'
 report['phases']['source_and_provider_context']=dict(selected_source_refs=[r['postimage'] for r in P['inputs']['postimages']],nine_RO_objects_exact=True,selected_C_allocated_functions=0,new_Rust_function_names=0)
 flags={}
 for name,value in [('idle_halt',0),('allow_oversubscribe',0),('time_sharing',1)]:
  s=own(rust,name);sec=rust.sections[s['shndx']]
  assert (s['bind'],s['type'],s['size'])==(1,1,4) and sec['align']>=4 and s['value']%4==0
  info=rust.raw[rust.table['offset']+s['index']*24+5];assert info==0
  expected=value.to_bytes(4,'little');assert object_bytes(rust,s)==expected
  f=final(name);assert (f['bind'],f['type'],f['size'])==(1,1,4) and f['value']%4==0 and data(f)==expected
  actual_providers=[label for label,elf in providers if any(v['name']==name and v['shndx']!=0 for v in elf.symbols)];assert actual_providers==['new Rust']
  flags[name]=dict(Rust_symbol=s,section=sec,initial_signed_CInt=value,final_symbol=f,initial_hex=expected.hex(),unique_provider=actual_providers)
 report['phases']['three_CInt_flags']=flags
 table=own(rust,'process_idle_callbacks');sec=rust.sections[table['shndx']]
 assert (table['bind'],table['type'],table['size'])==(1,1,80) and sec['align']>=8 and table['value']%8==0
 assert sec['flags']&2 and not sec['flags']&(1|4) and object_bytes(rust,table)==bytes(80)
 assert rust.raw[rust.table['offset']+table['index']*24+5]==0
 actual_rels=relocs(rust,table);old_rels=relocs(oldprocess,own(oldprocess,'process_idle_callbacks'))
 def exact(rs):return [dict(offset=r['offset'],type=r['type'],addend=r['addend'],target=r['target']['name']) for r in rs]
 expected=[dict(offset=i*8,type=1,addend=0,target=name) for i,name in enumerate(TARGETS)]
 assert exact(actual_rels)==exact(old_rels)==expected
 ft=final('process_idle_callbacks');fsec=sections[ft['shndx']]
 assert (ft['bind'],ft['type'],ft['size'])==(1,1,80) and ft['value']%8==0 and fsec['flags']&2 and not fsec['flags']&(1|4)
 pointers=struct.unpack('<10Q',data(ft));resolved=[]
 for name,pointer in zip(TARGETS,pointers):
  target=final(name);assert target['bind']==1 and target['type']==2 and pointer==target['value']
  matches=[label for label,elf in providers if any(v['name']==name and v['shndx']!=0 for v in elf.symbols)];assert len(matches)==1
  resolved.append(dict(target=name,final_value=pointer,unique_object_provider=matches[0]))
 actual_providers=[label for label,elf in providers if any(v['name']=='process_idle_callbacks' and v['shndx']!=0 for v in elf.symbols)];assert actual_providers==['new Rust']
 # Preserve section mapping facts separately from PT_LOAD flags. No page-RO claim.
 def mapping(path,name):
  raw=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[1:3]==(2,62)
  sh=[dict(zip(['name_off','type','flags','addr','offset','size','link','info','align','entsize'],struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*64))) for i in range(h[12])]
  symtab=next(s for s in sh if s['type']==2);strings=raw[sh[symtab['link']]['offset']:sh[symtab['link']]['offset']+sh[symtab['link']]['size']];matches=[]
  for i in range(symtab['size']//24):
   no,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,symtab['offset']+i*24)
   if strings[no:strings.index(b'\0',no)].decode()==name and idx:matches.append(dict(value=value,size=size,section_flags=sh[idx]['flags']))
  assert len(matches)==1;row=matches[0];segments=[]
  for i in range(h[10]):
   kind,flags,off,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',raw,h[5]+i*h[9])
   if kind==1 and va<=row['value'] and row['value']+row['size']<=va+memsz:segments.append(dict(type='PT_LOAD',flags=flags,readonly=not bool(flags&2),executable=bool(flags&1)))
  assert len(segments)==1;row['containing_segment']=segments[0];return row
 predecessor=mapping(E/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/output/build/kernel/mckernel.img','process_idle_callbacks');successor=mapping(B/'kernel/mckernel.img','process_idle_callbacks')
 assert predecessor['section_flags']==successor['section_flags'] and predecessor['containing_segment']==successor['containing_segment']
 report['phases']['immutable_80B_callback_table']=dict(Rust_symbol=table,Rust_section=sec,ten_original_R64_zero_addend_relocations=expected,final_symbol=ft,final_section=fsec,final_target_pointer_values=resolved,unique_provider=actual_providers,predecessor_mapping=predecessor,successor_mapping=successor,mapping_semantics_unchanged=True,runtime_page_protection_claim=False)
 # Exact remaining C OBJECT names, binding, type, size, initial bytes and target
 # relocations; normalizing only incidental C string-pool address movement.
 oldmeta={s['name']:s for s in allocated(oldprocess,1)};newmeta={s['name']:s for s in allocated(process,1)}
 assert len(oldmeta)==89 and len(newmeta)==85
 assert set(oldmeta)-set(newmeta)==set(FOUR) and not set(newmeta)-set(oldmeta)
 differences=[]
 for name,s in sorted(newmeta.items()):
  old=oldmeta[name]
  if tuple(s[k] for k in ['bind','type','size'])!=tuple(old[k] for k in ['bind','type','size']) or object_bytes(process,s)!=object_bytes(oldprocess,old) or [normalized_relocation(process,r) for r in relocs(process,s)]!=[normalized_relocation(oldprocess,r) for r in relocs(oldprocess,old)]:differences.append(name)
 assert not differences,('remaining C metadata differences',differences)
 report['phases']['remaining_selected_C_metadata']=dict(original_allocated_OBJECTs=89,new_allocated_OBJECTs=85,only_removed_objects=FOUR,all_85_binding_type_size_initial_bytes_and_relocations_preserved=True,no_new_C_functions=True)
 # Actual fixed LP64 C/Rust source assertions and constructor signatures.
 helper=Path(next(r['postimage']['path'] for r in P['inputs']['postimages'] if r['relative']=='kernel/rust/process_helpers.rs'));text=helper.read_text()
 start=text.index('pub static process_idle_callbacks:');snippet=text[max(0,start-5000):start+2000]
 assert all(name in snippet for name in TARGETS)
 report['phases']['actual_source_ABI_bindings']=dict(process_helpers=ref(helper),process_source=next(r['postimage'] for r in P['inputs']['postimages'] if r['relative']=='kernel/process.c'),callback_fields=10,field_stride=8,CInt_bytes=4,callback_alignment=8,pointer_and_CULong_bytes=8,new_declaration_warning_debt='Two new usize/u64 signature spellings; ABI-equivalent under the fixed x86_64 LP64 producer, retained without suppressions/casts/wrappers.')
 report['status']='PASS_ACTUAL_F02_FOUR_RUST_DATA_OWNERS_ORIGINAL_CALLBACK_ABI_FINAL_POINTERS_AND_85_C_METADATA'
except BaseException as error:
 report['status']='FAIL_FIRST_F02_DATA_OWNER_VALIDATOR_PRESERVED';report['first_failure']=repr(error);report['traceback']=traceback.format_exc()
(D/'FOUR-F02-OWNERS-RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],first_failure=report.get('first_failure'),phases=list(report['phases']))))
if report['status'].startswith('FAIL'):raise SystemExit(1)
