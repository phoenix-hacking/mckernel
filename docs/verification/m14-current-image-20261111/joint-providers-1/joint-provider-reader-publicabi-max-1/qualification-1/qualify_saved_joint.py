# Saved-data qualification only. No subprocess, target import or ELF tool execution.
import collections,datetime,hashlib,json,re,shlex,struct
from pathlib import Path
from saved_elf import fact,elf
M=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
P=M/'joint-provider-reader-publicabi-max-1';out=P/'qualification-1';meta=P/'metadata-1'
prior=M/'time-bridge-image-operation-sdk-max-1/qualification-1'
B=M/'joint-provider-image-p04source-max-1/stable-baseline7231-1';build=B/'build'
PE=M/'joint-provider-operation-sdk-max-1/capture-correction-1/execution-1'
RE=M/'joint-provider-operation-sdk-max-1/reader-1/execution-1'
parent=RE.parent;request=json.loads((parent/'REQUEST.json').read_text())
producer=json.loads((PE/'RESULT.json').read_text());reader=json.loads((RE/'RESULT.json').read_text())
baseline=json.loads((B/'BASELINE.json').read_text());oracle=json.loads((P/'OUTPUT-ORACLE.json').read_text())
basecmd=json.loads((prior/'ACTUAL-RUST-AND-C-COMMANDS.json').read_text())
def save(name,data):
 p=out/name;assert not p.exists(),str(p);p.write_text(json.dumps(data,indent=2)+'\n');return fact(p)
assert producer['source_commit']==reader['source_commit']==baseline['source_commit']==request['source_commit']=='7231ce6d17af39e9556ee815980a97f180b70eb1'
assert fact(PE/'RESULT.json')['sha256']=='76470805ec4f9a8266664bb21b16d9bed4b5b826bcdcd19e12e92dc05f0768ff'
assert fact(RE/'RESULT.json')['sha256']=='4406bc072ced3672df2272caf30a01150cc86c75a985b82b2643dddebab04243'
assert fact(B/'BASELINE.json')['sha256']=='de6c12876867610aa0e8b1b161d00ab7c0ba3d42da313ef4378bea61a4dc7d46'
assert baseline['all25_inode_independent'] and baseline['all4_producer_captured_artifact_identities_matched'] and not baseline['pending_reader_metadata_copied']
for row in baseline['files']:
 assert fact(Path(row['path']))['sha256']==row['sha256'] and row['independent_inode']
for x,n in [(producer,13),(reader,12)]:
 assert x['all_waits_streams_joined'] and not x['remaining_owned_children'] and not x['original_acceptance'] and len(x['clients'])==n
 assert all(r['exit']==0 and r['pid']>0 and int(r['birth'])>0 and r['direct_wait_joined'] and r['streams_closed'] and not r.get('primary_error') and not r.get('secondary_errors') and not r.get('lifecycle_UNKNOWN') for r in x['clients'])
 assert len(x['phases'])==1 and all(r['exit']==0 and not r['OOMKilled'] and r['owned_container_removed'] and r['client_wait_joined'] for r in x['phases'])
assert len(reader['metadata'])==45
for row in reader['metadata']:assert fact(Path(row['path']))==row
assert reader['request_sha256']==fact(parent/'REQUEST.json')['sha256'] and reader['review_sha256']=='c3c44c6b496500d34a1da6f40c8cfcb90fa35c6ad0ae097e35064e4f891527d7'
assert json.loads((RE/'RESOURCE-RELEASE.json').read_text())['positive_all_scopes'] and json.loads((PE/'RESOURCE-RELEASE.json').read_text())['positive_all_scopes']
for f in [RE.parent/'ROOT-EXEC-COMPLETION.json',PE.parent/'ROOT-EXEC-COMPLETION.json']:
 c=json.loads(f.read_text());assert c['exit_code']==0 and c.get('session_id') is None

old=json.loads((prior/'OWNER-PROVIDER-JOINS.json').read_text())
link_argv=shlex.split((meta/'regenerated-link.txt').read_text());objects=[x for x in link_argv if x.endswith('.o')];assert objects==basecmd['actual_link_inputs'] and len(objects)==11
units={x:elf(build/'kernel'/x) for x in objects};final=elf(build/'kernel/mckernel.img')
# Physical input-section placements, not name-only provider guesses.
maptext=(meta/'image-map.stdout').read_text();placements=collections.defaultdict(list);pending=None
for line in maptext.splitlines():
 m=re.match(r'^\s+((?:\.[^\s]+|__verbose))\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(.+\.o)\s*$',line)
 if m:placements[(m[4],m[1])].append({'address':int(m[2],16),'bytes':int(m[3],16)});pending=None;continue
 m=re.match(r'^\s+((?:\.[^\s]+|__verbose))\s*$',line)
 if m:pending=m[1];continue
 m=re.match(r'^\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(.+\.o)\s*$',line)
 if m and pending:placements[(m[3],pending)].append({'address':int(m[1],16),'bytes':int(m[2],16)});pending=None
 elif line.strip():pending=None
assert re.findall(r'^LOAD (.+)$',maptext,re.M)==objects
providers=collections.defaultdict(list);unitrows=[]
for name,u in units.items():
 defs=[s for s in u['symbols'] if s['name'] and s['binding'] in ('GLOBAL','WEAK') and s['section_index']!=0]
 imports=[s for s in u['symbols'] if s['name'] and s['binding'] in ('GLOBAL','WEAK') and s['section_index']==0]
 runtime=[s for s in u['symbols'] if s['name'] and s['type']=='FUNC' and s['bytes'] and 0<s['section_index']<len(u['sections']) and u['sections'][s['section_index']]['flags']&4]
 for s in defs:providers[s['name']].append((name,s))
 unitrows.append({'object':name,'identity':fact(Path(u['path'])),'global_definitions':len([s for s in defs if s['binding']=='GLOBAL']),'weak_definitions':len([s for s in defs if s['binding']=='WEAK']),'strong_imports':len([s for s in imports if s['binding']=='GLOBAL']),'weak_imports':len([s for s in imports if s['binding']=='WEAK']),'runtime_FUNC_rows':len(runtime),'runtime_FUNC_size_sum':sum(s['bytes'] for s in runtime),'runtime_FUNC_names':[s['name'] for s in runtime],'global_definition_names':[s['name'] for s in defs]})
fg=[s for s in final['symbols'] if s['name'] and s['binding'] in ('GLOBAL','WEAK')];named_undef=[s for s in final['symbols'] if s['name'] and s['section_index']==0]
assert not named_undef
missing=[];mismatches=[];joined=[]
for s in fg:
 candidates=providers.get(s['name'],[])
 if not candidates:missing.append(s);continue
 matches=[]
 for obj,t in candidates:
  if t['section_index']==0xfff1:
   if t['value']==s['value']:matches.append({'object':obj,'input':t,'placement':'ABS'})
  elif t['section_index']<len(units[obj]['sections']):
   sec=units[obj]['sections'][t['section_index']]
   for pl in placements[(obj,sec['name'])]:
    if pl['address']+t['value']==s['value'] and t['bytes']==s['bytes'] and t['type']==s['type']:matches.append({'object':obj,'input':t,'section':sec['name'],'placement':pl})
 if len(matches)!=1:mismatches.append({'final':s,'candidates':[(o,t) for o,t in candidates],'physical_matches':matches})
 else:joined.append({'name':s['name'],'final':s,'owner':matches[0]})
imports=[]
byfinal={s['name']:s for s in fg}
for obj,u in units.items():
 for s in u['symbols']:
  if not s['name'] or s['section_index']!=0 or s['binding'] not in ('GLOBAL','WEAK'):continue
  imports.append({'consumer_object':obj,'import':s,'final_provider':byfinal.get(s['name']),'source_input_candidates':[o for o,t in providers.get(s['name'],[])]})
result={'schema':'m14-actual-image-physical-provider-data-v1','status':'ACTUAL_SAVED_METADATA_JOIN_PRELIMINARY','image':fact(build/'kernel/mckernel.img'),'map':fact(build/'kernel/mckernel.img.map'),'final_header':final['header'],'program_headers':final['program_headers'],'unit_summary':unitrows,'final_named_undefined':named_undef,'final_global_or_weak_count':len(fg),'physical_provider_join_count':len(joined),'linker_or_unmapped_globals':missing,'physical_mismatches':mismatches,'physical_provider_joins':joined,'import_joins':imports,'final_symbols':final['symbols'],'final_sections':final['sections']}
assign=[]
for s in missing:
 hits=re.findall(r'^\s+(0x[0-9a-fA-F]+)\s+'+re.escape(s['name'])+r' = \.\s*$',maptext,re.M)
 assert len(hits)==1 and int(hits[0],16)==s['value']
 assert s['name'] in ('_head','_end','__start___verbose','__stop___verbose','vsyscall_page')
 assign.append({'symbol':s,'owner':'actual generated production linker-script assignment','map_address':hits[0]})
assert len(assign)==5
result['linker_defined_global_joins']=assign;result['linker_or_unmapped_globals']=[]
owner_by_name={x['name']:x for x in joined};script_by_name={x['symbol']['name']:x for x in assign}
for edge in imports:
 assert edge['final_provider'] is not None
 edge['physical_provider']=owner_by_name.get(edge['import']['name']) or script_by_name[edge['import']['name']]
 edge['linkage_type_contract']={'consumer_ELF_type':edge['import']['type'],'provider_ELF_type':edge['final_provider']['type'],'provider_bytes':edge['final_provider']['bytes'],'source_ABI_scope':'Real C ABI assertion target/unchanged supported-profile layout plus reviewed original C/Rust declarations. ELF NOTYPE imports do not alone prove a function prototype.'}
result['binary_binding_counts_including_null']=dict(collections.Counter(s['binding'] for s in final['symbols']))
result['binary_named_binding_counts']=dict(collections.Counter(s['binding'] for s in final['symbols'] if s['name']))
loads=[x for x in final['program_headers'] if x['type']==1]
assert final['header']['type']==2 and final['header']['machine']==62
assert len(loads)==2 and [x['flags'] for x in loads]==[5,7]
assert all(x['file_bytes']<=x['memory_bytes'] and x['vaddr']==x['paddr'] and x['align']==4096 for x in loads)
assert loads[0]['vaddr']==0xfffffffffe800000+0x1000
assert not any(x['type'] in (2,3) for x in final['program_headers'])
assert not any(x['type'] in (4,9) and x['bytes'] for x in final['sections'])
for s in final['sections']:
 if not s['flags']&2 or not s['bytes']:continue
 ps=[x for x in loads if x['vaddr']<=s['address'] and s['address']+s['bytes']<=x['vaddr']+x['memory_bytes']]
 assert ps,s['name']
 if s['type']!=8:assert any(s['offset']==x['offset']+s['address']-x['vaddr'] and s['offset']+s['bytes']<=x['offset']+x['file_bytes'] for x in ps),s['name']
arch=owner_by_name['arch_start'];assert arch['owner']['object']=='rust/mckernel_rust.o' and arch['final']['type']=='FUNC' and arch['final']['bytes']>0 and final['header']['entry']==arch['final']['value']
assert any(x['flags']&1 and x['vaddr']<=final['header']['entry']<x['vaddr']+x['memory_bytes'] for x in loads)
result['arch_start_physical_owner']=arch
notes=[]
with Path(result['image']['path']).open('rb') as f:
 for s in final['sections']:
  if s['name'] not in ('.note.mckernel.boot','.note.gnu.build-id'):continue
  f.seek(s['offset']);blob=f.read(s['bytes']);i=0
  while i<len(blob):
   ns,ds,kind=struct.unpack_from('<III',blob,i);i+=12;name=blob[i:i+ns].rstrip(b'\0').decode('ascii');i+=(ns+3)&~3;desc=blob[i:i+ds];i+=(ds+3)&~3
   notes.append({'section':s['name'],'owner':name,'kind':kind,'descriptor_hex':desc.hex(),'descriptor_u32':list(struct.unpack('<IIII',desc)) if name=='MCKERNEL' else None})
assert next(x for x in notes if x['owner']=='MCKERNEL')['descriptor_u32']==[4,0x60c00,7616,1]
result['actual_notes']=notes
assert not mismatches and not result['linker_or_unmapped_globals']
ru=units['rust/mckernel_rust.o'];rustpath=Path(ru['path']);imagepath=Path(result['image']['path']);raw=rustpath.read_bytes();image_raw=imagepath.read_bytes()
def symbol_bytes(p,unit,sym):
 sec=unit['sections'][sym['section_index']];off=sec['offset']+sym['value']-sec['address'];assert sec['type']!=8 and sec['offset']<=off and off+sym['bytes']<=sec['offset']+sec['bytes']
 with p.open('rb') as f:f.seek(off);b=f.read(sym['bytes'])
 assert len(b)==sym['bytes'];return b,off,sec

def relocs_for(sym):
 edges=[]
 for sec in ru['sections']:
  if sec['type']!=4 or sec['info']!=sym['section_index']:continue
  assert sec['entry_bytes']==24
  for off in range(sec['offset'],sec['offset']+sec['bytes'],24):
   ro,ri,ra=struct.unpack_from('<QQq',raw,off)
   if not sym['value']<=ro<sym['value']+sym['bytes']:continue
   target=ru['symbols'][ri>>32];e={'input_offset':ro,'observed_ELF_relocation_type':ri&0xffffffff,'addend':ra,'input_target':target}
   if target['binding'] in ('GLOBAL','WEAK'):
    e['actual_physical_provider']=owner_by_name.get(target['name']) or script_by_name.get(target['name']);assert e['actual_physical_provider'],target
   else:
    assert 0<target['section_index']<len(ru['sections']),target
    e['local_whole_Rust_section']=ru['sections'][target['section_index']]
   edges.append(e)
 return edges

# New joint-path analysis over the current actual immutable files.
cobj='CMakeFiles/mckernel.img.dir/syscall.c.o';rustobj='rust/mckernel_rust.o'
cu=units[cobj];cpath=Path(cu['path']);cache_raw={obj:Path(u['path']).read_bytes() for obj,u in units.items()}
def relocations(u,sym):
 data=cache_raw.get(next((obj for obj,v in units.items() if v is u),''))
 if data is None:data=Path(u['path']).read_bytes()
 rows=[]
 for sec in u['sections']:
  if sec['type']!=4 or sec['info']!=sym['section_index']:continue
  assert sec['entry_bytes']==24
  for off in range(sec['offset'],sec['offset']+sec['bytes'],24):
   ro,ri,ra=struct.unpack_from('<QQq',data,off)
   if sym['value']<=ro<sym['value']+sym['bytes']:rows.append({'input_offset':ro,'type':ri&0xffffffff,'addend':ra,'target':u['symbols'][ri>>32]})
 return rows

def resolve(u,t):
 if t['binding'] in ('GLOBAL','WEAK'):
  item=owner_by_name.get(t['name']) or script_by_name.get(t['name']);assert item,t
  return item['final']['value'] if 'final' in item else item['symbol']['value'],item
 if t['section_index']==0xfff1:return t['value'],{'absolute_input':t}
 obj=next(obj for obj,v in units.items() if v is u);sec=u['sections'][t['section_index']]
 candidates=placements[(obj,sec['name'])]
 if t['name']:
  fs=[x for x in final['symbols'] if x['name']==t['name'] and x['type']==t['type'] and x['bytes']==t['bytes'] and x['section_index']!=0]
  possible=[(pl,x) for pl in candidates for x in fs if pl['address']+t['value']==x['value']]
  if len(possible)==1:return possible[0][1]['value'],{'object':obj,'input':t,'section':sec,'placement':possible[0][0],'final':possible[0][1]}
 assert len(candidates)==1,{'local_target':t,'section':sec,'placements':candidates}
 return candidates[0]['address']+t['value'],{'object':obj,'input':t,'section':sec,'placement':candidates[0]}

def bytes_join(obj,sym,fsym):
 u=units[obj];ib,io,sec=symbol_bytes(Path(u['path']),u,sym);fb,fo,fsec=symbol_bytes(imagepath,final,fsym)
 assert len(ib)==len(fb);covered=set();rows=[]
 for edge in relocations(u,sym):
  off=edge['input_offset']-sym['value'];target,proof=resolve(u,edge['target']);kind=edge['type'];place=fsym['value']+off
  if kind==1:width=8;expected=(target+edge['addend'])&((1<<64)-1)
  elif kind in (2,4):width=4;expected=(target+edge['addend']-place)&0xffffffff
  elif kind in (10,11):width=4;expected=(target+edge['addend'])&0xffffffff
  elif kind==24:width=8;expected=(target+edge['addend']-place)&((1<<64)-1)
  else:raise AssertionError({'unqualified_relocation':edge,'name':sym['name']})
  observed=int.from_bytes(fb[off:off+width],'little');merge_proof=None
  # ELF SHF_MERGE|SHF_STRINGS may pool/reorder individual literals. The
  # relocation points at the identical actual terminated input string, not
  # necessarily a linearly placed whole input section plus its old addend.
  target_symbol=edge['target'];target_index=target_symbol['section_index']
  if kind==1 and target_symbol['binding']=='LOCAL' and 0<target_index<len(u['sections']):
   ts=u['sections'][target_index]
   if ts['flags']&0x30==0x30:
    assert ts['entry_bytes']==1 and ts['type']==1
    ip=ts['offset']+target_symbol['value']+edge['addend'];assert ts['offset']<=ip<ts['offset']+ts['bytes']
    rr=cache_raw[obj];end=rr.index(b'\0',ip,ts['offset']+ts['bytes']);literal=rr[ip:end+1]
    dest=[x for x in final['sections'] if x['type']==1 and x['flags']&2 and not x['flags']&1 and x['address']<=observed and observed+len(literal)<=x['address']+x['bytes']];assert len(dest)==1
    pos=dest[0]['offset']+observed-dest[0]['address'];assert image_raw[pos:pos+len(literal)]==literal
    merge_proof={'ELF_flags_MERGE_STRINGS':ts['flags'],'input_section':ts,'input_file_offset':ip,'final_section':dest[0],'final_file_offset':pos,'actual_literal_hex_including_NUL':literal.hex(),'exact_input_final_literal_bytes_equal':True,'reason':'Linker permitted pooling; exact payload/protection/bounds required, no function/provider/name alias waiver.'}
    expected=observed
  assert observed==expected,(sym['name'],edge,observed,expected)
  covered.update(range(off,off+width));rows.append({'function_or_data_offset':off,'width':width,'relocation':edge,'actual_final_value':observed,'expected_final_value':expected,'actual_target_provider':proof,'merged_literal_identity_proof':merge_proof})
 assert all(x==y for n,(x,y) in enumerate(zip(ib,fb)) if n not in covered),(sym['name'],'unrelocated bytes')
 return {'input_file_offset':io,'input_section':sec,'input_bytes_sha256':hashlib.sha256(ib).hexdigest(),'final_file_offset':fo,'final_section':fsec,'final_bytes_sha256':hashlib.sha256(fb).hexdigest(),'bytes':len(ib),'all_nonrelocated_bytes_equal':True,'all_current_relocations_exact':rows}

def required_rust(name,kind='FUNC'):
 item=owner_by_name[name];assert item['owner']['object']==rustobj and item['final']['type']==kind and item['final']['bytes']>0,name
 assert len([s for s in ru['symbols'] if s['name']==name and s['section_index']!=0])==1
 assert not any(s['name']==name and s['section_index']!=0 for obj,u in units.items() if obj!=rustobj for s in u['symbols']),name
 return item

newroots=oracle['new13_roots']['names'];assert len(newroots)==13
rootrows=[]
for name in newroots:
 row=required_rust(name);rootrows.append({'name':name,'physical_owner':row,'actual_code_bytes_and_link_patches':bytes_join(rustobj,row['owner']['input'],row['final'])})

# Decode actual table pointer fields, including source C macro aliases.
cpp=Path('/home/holden/mckernel/kernel/syscall.c').read_text()
def candidates(name):
 return [name]+re.findall(r'^#define\s+'+re.escape(name)+r'\s+([A-Za-z_][A-Za-z0-9_]*)\s*$',cpp,re.M)
def table(name,size,fields,scalar=None):
 item=owner_by_name[name];assert item['owner']['object']==cobj and item['final']['type']=='OBJECT' and item['final']['bytes']==size
 sym=item['owner']['input'];ib,io,sec=symbol_bytes(cpath,cu,sym);fb,fo,fs=symbol_bytes(imagepath,final,item['final']);assert not(sec['flags']&1) and not(fs['flags']&1)
 rel=relocations(cu,sym);rows=[]
 for field,off,source in fields:
  es=[e for e in rel if e['input_offset']==sym['value']+off];assert len(es)==1 and es[0]['type']==1,(name,field,es)
  edge=es[0];address,provider=resolve(cu,edge['target']);value=struct.unpack_from('<Q',fb,off)[0];assert value==(address+edge['addend'])&((1<<64)-1)
  opts=candidates(source);matches=[owner_by_name[n] for n in opts if n in owner_by_name and owner_by_name[n]['final']['value']==value]
  assert matches,(name,field,source,edge,value,opts)
  assert provider['owner']['object']==rustobj and provider['final']['type']=='FUNC' and provider['final']['bytes']>0,(name,field,provider)
  rows.append({'field':field,'offset':off,'source_target':source,'source_C_macro_alias_candidates':opts,'actual_input_relocation':edge,'actual_final_pointer':value,'actual_physical_target':provider,'matches_current_source_target_or_macro_alias':[x['name'] for x in matches],'typed_source_contract':'Actual current C typedef/19-slot struct and real Rust alias declaration under compiled7231/profile/ff48 guards; ELF NOTYPE alone is insufficient.'})
 if scalar is not None:
  off,want=scalar;assert struct.unpack_from('<i',ib,off)[0]==struct.unpack_from('<i',fb,off)[0]==want
 return {'name':name,'physical_owner':item,'current_input_file_offset':io,'current_final_file_offset':fo,'bytes':size,'readonly_actual_input_and_final':True,'pointer_fields':rows,'all_bytes_and_current_link_relocations':bytes_join(cobj,sym,item['final']),'scalar':scalar}

ps=[(f,i*8,t) for i,(f,t) in enumerate(oracle['actual_ptrace_table']['expected_source_slots'])]
ptrace_table=table('f03_ptrace_entry_ops_v1',152,ps)
unmap_fields=[(x['source_field'],x['offset'],x['expected_target']) for x in oracle['actual_unmap_tables']['f03_do_munmap_binding_v1']['slots']]
unmap_table=table('f03_do_munmap_binding_v1',48,unmap_fields)
clear_table=table('f03_clear_host_pte_binding_v1',24,[('forward',8,'syscall_do_syscall3_bridge'),('log',16,'clear_host_pte_log_bridge')],(0,11))
tables=save('ACTUAL-CALLBACK-TABLES.json',{'status':'PASS_CURRENT_PHYSICAL_PTRACE19_UNMAP6_CLEAR2_POINTERS_AND_REAL_TYPED_TARGETS','source_commit':request['source_commit'],'ptrace19':ptrace_table,'unmap6':unmap_table,'clear2':clear_table,'HOST_fixture19_is_not_production_table_proof':True})

# Source-compatible true lower owners; inspect current raw edges without an
# invented demand that inlined/aliased source calls retain identical opcodes.
mapping_path=M/'f06-ptrace-default-whole-review-p04tests-max-1/MAPPING.PENDING.json';mapping=json.loads(mapping_path.read_text())
lower=mapping['required_provider_and_ABI_join']['fifteen_direct_changed_family_lower_roots']+['do_munmap','do_munmap_body_result','clear_host_pte','clear_host_pte_body_result','set_host_vma_body_result','syscall_generic_forwarding','syscall_generic_forwarding_body_result','do_syscall','begin_free_pages_pending','remove_process_memory_range','finish_free_pages_pending','f03_unmap_begin','f03_unmap_remove','f03_unmap_finish','f03_do_munmap_log_v1','process_thread_ptrace_saved_context_clear_result','process_thread_ptrace_trace_syscall_update_result','process_thread_ptrace_pending_signal_take_result','set_single_step','find_thread','thread_unlock','ihk_mc_get_processor_id','ihk_mc_syscall_set_arg0','ihk_mc_syscall_set_arg1','ihk_mc_syscall_set_arg2']
lowerrows=[required_rust(n) for n in dict.fromkeys(lower)]
context=[]
for n in oracle['context19_edges']['callers']:
 item=required_rust(n);edges=relocations(ru,item['owner']['input']);refs=[x for x in edges if x['target']['name'] in ('syscall_policy_forward_context_bridge','syscall_generic_forwarding')]
 assert refs,(n,'actual context reference not yet resolved',edges)
 context.append({'caller':n,'physical_owner':item,'actual_current_references':[{'relocation':x,'actual_provider':resolve(ru,x['target'])[1]} for x in refs],'source_ABI':'Existing SyscallForwardContextFn(CInt,void*)->CLong; number/pointer unchanged; complete source/normal compiler provenance and actual same-image Rust forwarder, no generic/exec fixture execution.'})
assert len(context)==19
# All original ptrace/register/debug/event/data roots in the independent map.
region=[]
for group in mapping['required_region_map']:
 entries=[]
 for n in group.get('required_image_roots',[]):entries.append(required_rust(n,'OBJECT' if n=='debug_constants' else 'FUNC'))
 region.append({'region':group['region'],'required_current_physical_owners':entries,'implementation_mapping_reused':group['implementation']})

# Current104 words in all four actual copies; no compiler/witness invocation.
oldabi=json.loads((prior/'ACTUAL-ABI104-AND-REQUEST72.json').read_text());expected_words=oldabi['current_four_arrays'][0]['words'];assert len(expected_words)==104
arrays=[]
for unit,path,names in [(cu,cpath,['f03_do_fork_c_abi_words']),(ru,rustpath,['f03_do_fork_rust_abi_words']),(final,imagepath,['f03_do_fork_c_abi_words','f03_do_fork_rust_abi_words'])]:
 for n in names:
  syms=[s for s in unit['symbols'] if s['name']==n and s['section_index']!=0];assert len(syms)==1;s=syms[0];b,off,sec=symbol_bytes(path,unit,s);assert s['type']=='OBJECT' and s['bytes']==832 and list(struct.unpack('<104Q',b))==expected_words and sec['align']>=8 and s['value']%8==0
  assert not relocations(unit,s)
  arrays.append({'artifact':fact(path),'symbol':s,'section':sec,'file_offset':off,'words':expected_words,'data_sha256':hashlib.sha256(b).hexdigest(),'no_relocations_in_target':True})
abi_current=save('ACTUAL-ABI104-AND-TYPED-TABLES.json',{'status':'PASS_ALL_FOUR_CURRENT_OBJECT_FINAL104_WORD_ARRAYS_AND_REAL_TABLE_GEOMETRY','prior_actual104':fact(prior/'ACTUAL-ABI104-AND-REQUEST72.json'),'current_four_arrays':arrays,'ptrace152_19slot_wakeup8':tables,'request72_alignment8_offsets':[0,4,8,16,24],'no_new_ABI_witness_compiler_test_or_helper':True})

# Prove current function bytes against actual final relocation patches, reused
# source names/ABI and genuine endpoint owners rather than name counts.
retained=[required_rust(x['name']) for x in json.loads((prior/'QUALIFICATION.json').read_text())['retained15_plus_fork']]
retained.append(required_rust('syscall_policy_do_syscall2_bridge'));assert len(retained)==17
# Full writable96-byte debug contract and new source-bound32-byte descriptor.
dc=required_rust('debug_constants','OBJECT');db,_,ds=symbol_bytes(rustpath,ru,dc['owner']['input']);df,_,dfs=symbol_bytes(imagepath,final,dc['final'])
assert db==df and len(db)==96 and ds['flags']&1 and dfs['flags']&1 and ds['align']>=32 and list(struct.unpack('<12Q',db))==[8128,7848,7872,7920,64,4208,4328,4304,4184,456,20,18446744073709551615]
def cstring_at(address):
 sec=next(s for s in final['sections'] if s['bytes'] and s['address']<=address<s['address']+s['bytes'] and s['type']!=8);off=sec['offset']+address-sec['address'];return image_raw[off:image_raw.index(b'\0',off)].decode()
dbs=[s for s in ru['symbols'] if 'PTRACE_WAKEUP_DEBUG' in s['name'] and s['type']=='OBJECT' and s['section_index']!=0];assert len(dbs)==1
ds=dbs[0];fs=[s for s in final['symbols'] if s['name']==ds['name'] and s['type']=='OBJECT' and s['section_index']!=0];assert len(fs)==1 and ds['bytes']==fs[0]['bytes']==32
pv,pvo,pvs=symbol_bytes(imagepath,final,fs[0]);ip,_,ips=symbol_bytes(rustpath,ru,ds);assert ips['flags']&1 and pvs['flags']&1
fp,func,fmt,flags=struct.unpack_from('<QQQI',pv);assert cstring_at(fp)=='/src/kernel/syscall.c' and cstring_at(func)=='ptrace_wakeup_log_bridge' and fmt==0 and flags&0xffffff==24429
new_debug={'input':ds,'final':fs[0],'file':cstring_at(fp),'function':cstring_at(func),'fmt':fmt,'line':flags&0xffffff,'flags':flags>>24,'input_section':ips,'final_section':pvs,'byte_relocation_join':bytes_join(rustobj,ds,fs[0])}
# Actual current13 lowerings are saved; use streaming selected function text to
# avoid duplicating large whole-object relocation listings in qualifier memory.
def selected_asm(name,kind):
 f=meta/('new-'+name+'-'+kind+'-disassembly.stdout');lines=[];on=False
 with f.open() as h:
  for line in h:
   if re.search(r'<'+re.escape(name)+r'>:',line):on=True
   elif on and line.startswith('Disassembly of section '):break
   if on:lines.append(line)
 return ''.join(lines)
freeasm=selected_asm('ptrace_detach_kfree_bridge','Rust');assert '$0x1231' in freeasm
free_lowering={'source_logical_line':4657,'actual4657_immediate_seen':True,'captured_assembly':fact(meta/'new-ptrace_detach_kfree_bridge-Rust-disassembly.stdout'),'actual_function':next(x for x in rootrows if x['name']=='ptrace_detach_kfree_bridge')}

# Actual generated command/cfg/source/macro/default/data and finite unchanged
# input identity rejoin; nine unchanged files reuse prior raw ownership facts.
saved_ids={line.split(None,1)[1]:line.split(None,1)[0] for line in (meta/'artifact-identities.sha256').read_text().splitlines()};saved_modes={}
for line in (meta/'artifact-modes.stdout').read_text().splitlines():
 mode,n,path=line.split(None,2);saved_modes[path]={'mode':mode,'bytes':int(n)}
oldunits={x['object']:x for x in old['unit_summary']}
for u in unitrows:
 key='/work/output/build/kernel/'+u['object'];assert u['identity']['sha256']==saved_ids[key] and u['identity']['bytes']==saved_modes[key]['bytes'];u['identity']['mode']=saved_modes[key]['mode'];u['language_class']='Rust' if u['object']==rustobj else ('assembly' if u['object'].endswith('.S.o') else 'C_or_included_C_header');u['allocated_executable_section_bytes']=sum(s['bytes'] for s in units[u['object']]['sections'] if s['flags']&2 and s['flags']&4)
for f in [result['image'],result['map']]:
 key='/work/output/build/kernel/'+Path(f['path']).name;assert f['sha256']==saved_ids[key] and f['bytes']==saved_modes[key]['bytes'];f['mode']=saved_modes[key]['mode']
changed=[x['object'] for x in unitrows if x['identity']['sha256']!=oldunits[x['object']]['identity']['sha256']];unchanged=[x['object'] for x in unitrows if x['object'] not in changed]
assert changed==[cobj,rustobj] and len(unchanged)==9
for k in ['config.h','ihk/config.h','kernel/config/smp-x86.lds']:
 f=next(x for x in baseline['files'] if x['path']==str(build/k));assert f['same_as_prior14d'] and saved_ids['/work/output/build/'+k]==f['sha256']
assert result['image']['mode']=='755'
archunit=next(x for x in unitrows if x['object']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o');assert archunit['allocated_executable_section_bytes']==archunit['runtime_FUNC_rows']==archunit['global_definitions']==archunit['weak_definitions']==0
Cunits=[x for x in unitrows if x['language_class']=='C_or_included_C_header' and x['allocated_executable_section_bytes']]
ledger=[{'object':x['object'],'previous_count':oldunits[x['object']]['runtime_FUNC_rows'],'actual_count':x['runtime_FUNC_rows'],'removed':sorted(set(oldunits[x['object']]['runtime_FUNC_names'])-set(x['runtime_FUNC_names'])),'added':sorted(set(x['runtime_FUNC_names'])-set(oldunits[x['object']]['runtime_FUNC_names'])),'actual_names':x['runtime_FUNC_names']} for x in Cunits]
cl=next(x for x in ledger if x['object']==cobj);assert cl['removed']==sorted(newroots) and not cl['added'] and cl['actual_count']==13
log=(PE/'build-payload.stdout').read_text();rl=[(i+1,s) for i,s in enumerate(log.splitlines()) if '/bin/rustc' in s and '--crate-type' in s];assert len(rl)==1;line_no,rustline=rl[0];argv=shlex.split(rustline);cfg=[argv[i+1] for i,s in enumerate(argv[:-1]) if s=='--cfg']
added=['f03_memory_host_offload_candidate','f06_ptrace_resume_callbacks_candidate','f03_policy_forward_context_bridge_candidate'];assert set(cfg)==set(basecmd['Rust_cfg'])|set(added) and len(cfg)==len(set(cfg))
cc=json.loads((meta/'regenerated-compile_commands.json').read_text());crow=[x for x in cc if x['file']=='/src/kernel/syscall.c' and x['output']=='kernel/CMakeFiles/mckernel.img.dir/syscall.c.o'];assert len(crow)==1
for flag in oracle['compiled_selection_and_source']['new_C_macros']+['MCKERNEL_RUST_F03_DO_SYSCALL2_BRIDGE','MCKERNEL_RUST_F03_DO_FORK']:assert '-D'+flag in shlex.split(crow[0]['command'])
cache=(meta/'regenerated-CMakeCache.txt').read_text()
for token in ['ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=ON','ENABLE_RUST_KERNEL:BOOL=ON','PROFILE_ENABLE:BOOL=ON','ENABLE_PERF:BOOL=ON','ENABLE_RUSAGE:BOOL=ON','ENABLE_LINUX_WORK_IRQ_FOR_IKC:BOOL=ON','ENABLE_UBSAN:BOOL=OFF','MCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12','ENABLE_RUST_M14_SYSCALL_ADAPTERS:BOOL=OFF','ENABLE_NATIVE_FORK_OWNED_TRANSACTION:BOOL=OFF','MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL:BOOL=OFF','MCKERNEL_CRASH_DEFS_HEADER:FILEPATH=/sdk/crash-9.0.1/defs.h']:assert token in cache,token
assert 'ptrace_callback_host_controls' not in cfg and 'f03_forward_adapters_candidate' not in cfg
for filename in ['f03_memory_host_offload.rs','f03_policy_forward_context_bridge.rs','f06_ptrace_resume_callbacks.rs','f03_ptrace_adapters.rs']:
 assert '/src/kernel/rust/'+filename in (meta/'regenerated-mckernel_rust.d').read_text() and '/src/kernel/rust/'+filename in (meta/'regenerated-Rust-build.make').read_text()
assert new_debug['flags']==int(next(x.split('=',1)[1] for x in argv if x.startswith('MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS=')))
commands=save('ACTUAL-RUST-AND-C-COMMANDS.json',{'source':fact(PE/'build-payload.stdout'),'line_1based':line_no,'literal_command':rustline,'argv':argv,'Rust_cfg':cfg,'Rust_cfg_count':len(cfg),'actual_C_command':crow[0],'actual_link_inputs':objects,'actual_link_argv':link_argv,'only_added_cfgs':added,'actual_source_commit':request['source_commit'],'17mounts_real_a875_source_guard':'Inherited genuine selecting cache/header mount+FILEPATH from prior14d configure, current stable header/cache/source pins and actual producer17mount profile; no configure or old test replay.'})

# Both actual single-container phases and all positive25 clients plus separate
# full Root completions; no unsupported20/28/client-count prediction.
life=[]
for d,q,phase,cap in [(PE,json.loads((M/'joint-provider-operation-sdk-max-1/REQUEST.json').read_text()),'build',2*2**30),(RE,request,'metadata',512*2**20)]:
 profile=json.loads((d/(phase+'-PROFILE.json')).read_text());term=json.loads((d/(phase+'-TERMINAL.json')).read_text())['State'];ad=json.loads((d/(phase+'-ADMISSION.json')).read_text());wanted=q[phase+'_phase']['expected_mounts'];assert len(profile['Mounts'])==len(wanted) and {(x['Source'],x['Destination'],not x['RW']) for x in profile['Mounts']}=={(x['source'],x['destination'],x['read_only']) for x in wanted}
 h=profile['HostConfig'];assert profile['Image']=='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94' and h['CpusetCpus']=='6' and h['Memory']==h['MemorySwap']==cap and h['ReadonlyRootfs'] and h['NetworkMode']=='none' and h['CapDrop']==['ALL'];assert term['ExitCode']==0 and term['Pid']==0 and not term['Running'] and not term['OOMKilled'];assert ad['all_current_overhead_bytes']+ad['this_phase_bytes']<=4*2**30 and ad['MemAvailable_bytes']>=26*2**30
 life.append({'phase':phase,'profile':fact(d/(phase+'-PROFILE.json')),'terminal':fact(d/(phase+'-TERMINAL.json')),'state':term,'admission':fact(d/(phase+'-ADMISSION.json')),'positive_release':fact(d/'RESOURCE-RELEASE.json'),'full_Root_completion':fact(d.parent/'ROOT-EXEC-COMPLETION.json')})
result.update({'status':'PASS_CURRENT7231_PHYSICAL_OWNERS_AND_PROVIDER_CLOSURE','source_commit':request['source_commit'],'new13':[x['physical_owner'] for x in rootrows],'retained17':retained,'retained_C_runtime_units':Cunits,'C_ledger_delta':ledger})
physical=save('OWNER-PROVIDER-JOINS.json',result)
changedproof=save('JOINT-CHANGED-PATH-JOINS.json',{'status':'PASS_NEW13_RUST_CEXCLUSION_ACTUAL_TABLES_CONTEXT19_LOWER_TYPED_PHYSICAL_SOURCE_JOIN','source_commit':request['source_commit'],'new13_roots':rootrows,'actual_tables':tables,'actual_context19_call_edges':context,'required_same_image_lower_owners':lowerrows,'prior_ptrace_region_mapping':fact(mapping_path),'current_required_ptrace_region_owners':region,'prior17_retained_current_Rust':retained,'current_four104':abi_current,'new_writable32B_ptrace_Ddebug':new_debug,'trackedfree_actual4657':free_lowering,'debug_constants96_current':{'physical_owner':dc,'actual12words':list(struct.unpack('<12Q',db)),'input_section':ds,'final_section':dfs},'actual_source_commands':commands,'Cledger':ledger,'unchanged_units':unchanged,'changed_units':changed,'all_current_raw_lowerings':[fact(meta/('new-'+n+'-'+kind+'-disassembly.stdout')) for n in newroots for kind in ['Rust','final']],'held_fixture_native_or_actual_target_execution':False,'physical_data':physical})
warnings=[{'line_1based':i+1,'text':s} for i,s in enumerate(log.splitlines()) if 'warning' in s.lower()]
summary=save('QUALIFICATION.json',{'schema':'m14-joint13-actual-image-qualification-v1','status':'PASS_ACTUAL7231_NEW13_RUST_OWNERS_REAL_TABLES_ABI_PROVIDERS_CURRENT_PROFILE_WHOLE_CONDITION_REVIEW_SEPARATE','owner':'/root/public_abi_join_max saved-result author; Root sole compositor/executor/publisher, P03/P04Tests independent whole01/03 decisions','source_commit':request['source_commit'],'source_binding':request['source_binding'],'source_integration':fact(M/'joint-provider-composition-2/CANONICAL-INTEGRATION.json'),'producer':fact(PE/'RESULT.json'),'reader':fact(RE/'RESULT.json'),'reader_operation':fact(parent/'REQUEST.json'),'reader_operation_GO':fact(M/'joint-provider-operation-review-source-acquisition-max-1/reader-1/REVIEW.json'),'corrected_reader_component':fact(P/'correction-1/READER-PHASE.json'),'preserved_physical25':fact(B/'BASELINE.json'),'actual_image':result['image'],'actual_map':result['map'],'actual_Rust':next(x['identity'] for x in unitrows if x['object']==rustobj),'all11_inputs':[x['identity'] for x in unitrows],'new13_nonempty_unique_Rust_Cexcluded':rootrows,'current_actual_table_joins':tables,'current_four104_ABI':abi_current,'changed_path':changedproof,'physical_provider_data':physical,'input_provider_joins':len(joined),'linker_provider_joins':len(assign),'strong_import_occurrences':sum(x['import']['binding']=='GLOBAL' for x in imports),'unique_import_names':len({x['import']['name'] for x in imports}),'named_undefined':[],'commands':commands,'retained17_Rust':retained,'actual_C_FUNC_remaining':sum(x['runtime_FUNC_rows'] for x in Cunits),'C_ledger':ledger,'entry':final['header']['entry'],'arch_start':arch,'LOADS':loads,'notes':notes,'all_allocated_sections_LOAD_covered':True,'no_INTERP_DYNAMIC_or_runtime_relocations':True,'arch_C_executable_bytes':0,'changed_units':changed,'unchanged_units':unchanged,'metadata_records':reader['metadata'],'lifecycle':{'producer_clients':13,'reader_clients':12,'total_actual_clients':25,'both_CID_exit0_nonOOM_Pid0_removed':True,'all_clients_positive_direct_birth_wait_streams':True,'positive_scopes':life,'remaining_owned_children':[]},'raw_build_warning_lines':warnings,'all_build_streams':[fact(PE/('build-payload.'+s)) for s in ['stdout','stderr']],'method':fact(out/'qualify_saved_joint.py'),'pure_ELF_method':fact(out/'saved_elf.py'),'reused_qualified_physical_source':fact(prior/'qualify_saved_clock.py'),'actions':'Only stdlib saved-file JSON/text/ELF byte reads and private result writes. No subprocess/readelf/objdump/compiler/build/driver/program/helper/SUT/test/SDK query/native/replay/canonical/cache mutation. No current source body was executed; exact imported fact/elf are pure saved-byte parsers, not target helpers.','whole_original_conditions':'Author qualification only. P03 whole01 map23cb and P04Tests whole03 map522e independently assess complete original source regions/typed provider closure and default criterion. No labels/count-only or whole-file-zeroC substitute, no altered original criterion or external inventory prerequisite.','functional_native_acceptance_or_hold_release':False,'original_acceptance_or_progress_mutated':False})
rr=save('RESULT.json',{'status':summary and 'PASS_ACTUAL_JOINT7231_ARTIFACT_ABI_PROVIDER_QUALIFICATION','qualification':summary,'changed_path':changedproof,'actual_tables':tables,'ABI104':abi_current,'physical_providers':physical,'new_Rust_roots':13,'context_edges':19,'ptrace_pointer_slots':19,'unmap_pointer_slots':6,'clear_pointer_slots':2,'all_metadata_records':45,'original_condition_accepted':False,'native':False,'producer_or_test_or_read_replayed':False})
print(json.dumps({'qualification':summary,'result':rr,'changed':changedproof,'tables':tables,'ABI':abi_current,'physical':physical,'image':result['image'],'new_root_bytes':{x['name']:x['physical_owner']['final']['bytes'] for x in rootrows},'providers':len(joined),'imports':len(imports),'remainingC':sum(x['runtime_FUNC_rows'] for x in Cunits)},indent=2))
