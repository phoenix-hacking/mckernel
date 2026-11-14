# Pure saved-file/ELF-byte analysis only. No subprocess, SUT or project runtime import.
import argparse,collections,datetime,hashlib,json,re,shlex,struct,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))  # Only the exact private pure saved-byte parser, never native source loading.
from saved_elf import fact,elf
M=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
SDK=M/'wait-termination-image-operation-sdk-max-1';RE=SDK/'reader-1/execution-1';PE=SDK/'execution-1';meta=SDK/'metadata-1'
a=argparse.ArgumentParser();a.add_argument('--build',type=Path,required=True);args=a.parse_args();build=args.build;out=P/'qualification-1'
assert not out.exists()
adoption=json.loads((P/'READER-ADOPTION.json').read_text());oracle=json.loads((P/'OUTPUT-ORACLE.json').read_text());sdkoracle=json.loads((SDK/'reader-1/OUTPUT-ORACLE.json').read_text());request=json.loads((RE.parent/'REQUEST.json').read_text());prodrequest=json.loads((SDK/'REQUEST.json').read_text());source=oracle['source_commit']
assert source==request['source_commit']==prodrequest['source_commit']=='6aae8273960583ec7fb194926292bd10ab1bc585'
for x in [adoption['SDK_parent_request'],adoption['SDK_reader_parent_request'],adoption['SDK_phase'],adoption['SDK_helper'],adoption['SDK_oracle'],adoption['SDK_source_bindings']]:assert fact(Path(x['path']))==x
producer=json.loads((PE/'RESULT.json').read_text());reader=json.loads((RE/'RESULT.json').read_text())
assert producer['source_commit']==reader['source_commit']==source
assert producer['status'].startswith('PASS_') and reader['status'].startswith('PASS_')
assert fact(RE/'RESULT.json')['sha256']=='12e6fb78f2d61cb4176965958866ef0b56b555c8ea51e9baea03c265e4368da3'
life=[]
for e,x,phase,count,cap,req in [(PE,producer,'build',13,2*2**30,prodrequest),(RE,reader,'metadata',12,512*2**20,request)]:
 assert len(x['clients'])==count and x['all_waits_streams_joined'] and not x['remaining_owned_children']
 for r in x['clients']:assert r['exit']==0 and r['pid']>0 and int(r['birth'])>0 and r['direct_wait_joined'] and r['streams_closed'] and not r.get('primary_error') and not r.get('secondary_errors') and not r.get('lifecycle_UNKNOWN')
 assert len(x['phases'])==1 and all(r['exit']==0 and not r['OOMKilled'] and r['owned_container_removed'] and r['client_wait_joined'] for r in x['phases'])
 full=json.loads((e.parent/'ROOT-EXEC-COMPLETION.json').read_text());assert full['exit_code']==0 and not full.get('session_id') and json.loads((e/'RESOURCE-RELEASE.json').read_text())['positive_all_scopes']
 profile=json.loads((e/(phase+'-PROFILE.json')).read_text());term=json.loads((e/(phase+'-TERMINAL.json')).read_text())['State'];ad=json.loads((e/(phase+'-ADMISSION.json')).read_text());wanted=req[phase+'_phase']['expected_mounts'];assert {(r['Source'],r['Destination'],not r['RW']) for r in profile['Mounts']}=={(r['source'],r['destination'],r['read_only']) for r in wanted};h=profile['HostConfig'];assert h['Memory']==h['MemorySwap']==cap and h['CpusetCpus']=='6' and h['ReadonlyRootfs'] and h['NetworkMode']=='none' and term['ExitCode']==term['Pid']==0 and not term['OOMKilled'] and ad['all_current_overhead_bytes']+ad['this_phase_bytes']<=4*2**30
 life.append(dict(phase=phase,actual_positive_clients=count,actual_labels=[r['label'] for r in x['clients']],result=fact(e/'RESULT.json'),profile=fact(e/(phase+'-PROFILE.json')),terminal=fact(e/(phase+'-TERMINAL.json')),full_Root_completion=fact(e.parent/'ROOT-EXEC-COMPLETION.json'),positive_release=fact(e/'RESOURCE-RELEASE.json')))
# Artifact parsing begins only after both real complete Root-owned operations above passed.
assert len(reader['metadata'])==23 and {Path(r['path']).name for r in reader['metadata']}==set(adoption['required_records'])
for row in reader['metadata']:assert fact(Path(row['path']))==row
for row in producer['actual_artifacts']:
 rel=Path(row['path']).relative_to(SDK.parent/'compute-image-source-1/output/build');f=build/rel;observed=fact(f);assert observed['bytes']==row['bytes'] and observed['sha256']==row['sha256']
prior=M/'mprotect-signal-reader-p03-max-1/qualification-1';old=json.loads((prior/'OWNER-PROVIDER-JOINS.json').read_text());basecmd=json.loads((prior/'ACTUAL-RUST-AND-C-COMMANDS.json').read_text())
staged={}
def save(name,d):
 assert name not in staged and not(out/name).exists(),name
 staged[name]=d;b=(json.dumps(d,indent=2)+'\n').encode();return dict(path=str(out/name),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
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

ru=units['rust/mckernel_rust.o'];rustpath=Path(ru['path']);imagepath=Path(result['image']['path']);raw=rustpath.read_bytes();image_raw=imagepath.read_bytes();cobj='CMakeFiles/mckernel.img.dir/syscall.c.o';rustobj='rust/mckernel_rust.o';cu=units[cobj];cpath=Path(cu['path']);cache_raw={obj:Path(u['path']).read_bytes() for obj,u in units.items()}
# Alias declarations only, not a source-body audit.
cpp=(P/'C-ALIAS-DEFINITIONS.txt').read_text()

def symbol_bytes(p,unit,sym):
 sec=unit['sections'][sym['section_index']];off=sec['offset']+sym['value']-sec['address'];assert sec['type']!=8 and sec['offset']<=off and off+sym['bytes']<=sec['offset']+sec['bytes']
 with p.open('rb') as f:f.seek(off);b=f.read(sym['bytes'])
 assert len(b)==sym['bytes'];return b,off,sec

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
  rows.append({'field':field,'offset':off,'source_target':source,'source_C_macro_alias_candidates':opts,'actual_input_relocation':edge,'actual_final_pointer':value,'actual_physical_target':provider,'matches_current_source_target_or_macro_alias':[x['name'] for x in matches],'typed_source_contract':'Actual current C typedef/repr(C) immutable table and genuine Rust declarations under produced f199/profile/ff48 compile guards; ELF NOTYPE alone is insufficient.'})
 if scalar is not None:
  off,want=scalar;assert struct.unpack_from('<i',ib,off)[0]==struct.unpack_from('<i',fb,off)[0]==want
 return {'name':name,'physical_owner':item,'current_input_file_offset':io,'current_final_file_offset':fo,'bytes':size,'readonly_actual_input_and_final':True,'pointer_fields':rows,'all_bytes_and_current_link_relocations':bytes_join(cobj,sym,item['final']),'scalar':scalar}

def cstring_at(address):
 sec=next(s for s in final['sections'] if s['bytes'] and s['address']<=address<s['address']+s['bytes'] and s['type']!=8);off=sec['offset']+address-sec['address'];return image_raw[off:image_raw.index(b'\0',off)].decode()

def selected_asm(name,kind):
 f=meta/('new-'+name+'-'+kind+'-disassembly.stdout');lines=[];on=False
 with f.open() as h:
  for line in h:
   if re.search(r'<'+re.escape(name)+r'>:',line):on=True
   elif on and line.startswith('Disassembly of section '):break
   if on:lines.append(line)
 return ''.join(lines)


newroots=oracle['new_roots'];rootrows=[]
for n in newroots:
 x=required_rust(n);rootrows.append(dict(name=n,physical_owner=x,actual_code_bytes_and_link_patches=bytes_join(rustobj,x['owner']['input'],x['final'])))
for n in oracle['C_exclusions']:assert not any(s['name']==n and s['section_index']!=0 for obj,u in units.items() if obj!=rustobj for s in u['symbols']),n
retained=[required_rust(n) for n in oracle['prior34']];assert len(retained)==34
fields=[(r['name'],r['offset'],r['source_target']) for r in oracle['wait_table']['fields']];wt=table('f03_wait_c_dependencies',48,fields)
tables=save('ACTUAL-WAIT-TABLE.json',dict(status='PASS_REAL48B_SIX_TYPED_RUST_POINTERS_NEW_SLOT0',source_commit=source,wait_table=wt))
callers=[]
for name in ('wait4_do_wait_bridge','check_sig_pending','terminate'):
 x=required_rust(name);ib,io,sec=symbol_bytes(rustpath,ru,x['owner']['input']);fb,fo,fs=symbol_bytes(imagepath,final,x['final']);edges=relocations(ru,x['owner']['input']);callers.append(dict(name=name,physical_owner=x,input_final_bytes=bytes_join(rustobj,x['owner']['input'],x['final']),actual_references=[dict(relocation=e,resolved_provider=resolve(ru,e['target'])[1]) for e in edges],input_hex=ib.hex(),final_hex=fb.hex()))
wcall=callers[0];assert any(e['relocation']['target']['name']=='f03_wait_c_dependencies' and e['relocation']['addend']==0 for e in wcall['actual_references'])
pending=callers[1];assert any(e['relocation']['target']['name'] in ('terminate_mcexec','terminate_mcexec_body_result','do_syscall') for e in pending['actual_references'])
# No assertion that the source callback survives compiler inlining as a named R64.
callerproof=save('ACTUAL-CALLER-BYTES-AND-REFERENCES.json',dict(status='ALL_CURRENT_CALLER_BYTES_RELOCATIONS_JOINED_PENDING_INLINE_SEMANTIC_ANNOTATION',callers=callers,wait_slot0_target=rootrows[0],actual_C_exclusions=oracle['C_exclusions']))
oldabi=json.loads((prior/'ACTUAL-ABI104-AND-SIGNAL-TYPES.json').read_text());expected_words=oldabi['current_four_arrays'][0]['words'];arrays=[]
for u,path,names in [(cu,cpath,['f03_do_fork_c_abi_words']),(ru,rustpath,['f03_do_fork_rust_abi_words']),(final,imagepath,['f03_do_fork_c_abi_words','f03_do_fork_rust_abi_words'])]:
 for n in names:
  syms=[s for s in u['symbols'] if s['name']==n and s['section_index']!=0];assert len(syms)==1;sym=syms[0];b,off,sec=symbol_bytes(path,u,sym);assert sym['bytes']==832 and list(struct.unpack('<104Q',b))==expected_words and not relocations(u,sym);arrays.append(dict(artifact=fact(path),symbol=sym,section=sec,file_offset=off,words=expected_words,data_sha256=hashlib.sha256(b).hexdigest(),no_relocations=True))
abi=save('ACTUAL-ABI104-AND-PUBLIC-TYPES.json',dict(status='PASS_CURRENT_FOUR104_PLUS_COMPILED_WAIT_TERMINATION_REQUEST_PUBLIC_TYPES',current_four_arrays=arrays,real72B_types='Actual400ad/f62 production C/Rust compile guards; realff48/current104 and actualnewSource6aae',source_bindings=request['source_binding'],prior_actual104=fact(prior/'ACTUAL-ABI104-AND-SIGNAL-TYPES.json')))
dc=required_rust('debug_constants','OBJECT');db,_,dcsec=symbol_bytes(rustpath,ru,dc['owner']['input']);df,_,dfsec=symbol_bytes(imagepath,final,dc['final']);assert db==df and len(db)==96 and dcsec['flags']&1 and dfsec['flags']&1 and dcsec['align']>=32 and list(struct.unpack('<12Q',db))==[8128,7848,7872,7920,64,4208,4328,4304,4184,456,20,18446744073709551615]
lowers={n:{k:dict(file=fact(meta/('new-'+n+'-'+k+'-disassembly.stdout')),selected_text=selected_asm(n,k)) for k in ('Rust','final')} for n in newroots}
lowernames=['do_syscall','terminate_mcexec_body_result','atomic_cmpxchg_ulong','get_this_cpu_local_var','ihk_mc_get_processor_id','syscall_offload_prepare_result','syscall_send_prepare_result','syscall_request_publish_result','send_syscall','check_sig_pending','wait4_do_wait_bridge','terminate'];lowerrows=[required_rust(n) for n in lowernames]
ids={};modes={}
for line in (meta/'artifact-identities.sha256').read_text().splitlines():h,path=line.split(None,1);ids[path.strip()]=h
for line in (meta/'artifact-modes.stdout').read_text().splitlines():mode,n,path=line.split(None,2);modes[path]=dict(mode=mode,bytes=int(n))
oldunits={x['object']:x for x in old['unit_summary']}
for u in unitrows:
 key='/work/output/build/kernel/'+u['object'];assert u['identity']['sha256']==ids[key] and u['identity']['bytes']==modes[key]['bytes'];u['identity']['mode']=modes[key]['mode'];u['language_class']='Rust' if u['object']==rustobj else ('assembly' if u['object'].endswith('.S.o') else 'C_or_included_C_header');u['allocated_executable_section_bytes']=sum(s['bytes'] for s in units[u['object']]['sections'] if s['flags']&2 and s['flags']&4)
for f in (result['image'],result['map']):key='/work/output/build/kernel/'+Path(f['path']).name;assert f['sha256']==ids[key] and f['bytes']==modes[key]['bytes'];f['mode']=modes[key]['mode']
changed=[x['object'] for x in unitrows if x['identity']['sha256']!=oldunits[x['object']]['identity']['sha256']];unchanged=[x['object'] for x in unitrows if x['object'] not in changed];assert changed==[cobj,rustobj] and len(unchanged)==9
archC=next(x for x in unitrows if x['object']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o');assert archC['allocated_executable_section_bytes']==archC['runtime_FUNC_rows']==archC['global_definitions']==0
Cunits=[x for x in unitrows if x['language_class']=='C_or_included_C_header' and x['allocated_executable_section_bytes']];ledger=[dict(object=x['object'],previous_count=oldunits[x['object']]['runtime_FUNC_rows'],actual_count=x['runtime_FUNC_rows'],removed=sorted(set(oldunits[x['object']]['runtime_FUNC_names'])-set(x['runtime_FUNC_names'])),added=sorted(set(x['runtime_FUNC_names'])-set(oldunits[x['object']]['runtime_FUNC_names'])),actual_names=x['runtime_FUNC_names']) for x in Cunits];assert ledger[0]['removed']==sorted(oracle['C_exclusions']) and not ledger[0]['added']
log=(PE/'build-payload.stdout').read_text();rr=[(i+1,s) for i,s in enumerate(log.splitlines()) if '/bin/rustc' in s and '--crate-type' in s];assert len(rr)==1;lineno,rline=rr[0];argv=shlex.split(rline);cfg=[argv[i+1] for i,x in enumerate(argv[:-1]) if x=='--cfg'];added=['f03_wait_host_provider_candidate','f03_terminate_host_provider_candidate'];assert set(cfg)==set(basecmd['Rust_cfg'])|set(added) and len(cfg)==len(set(cfg))
cc=json.loads((meta/'regenerated-compile_commands.json').read_text());crow=[x for x in cc if x['file']=='/src/kernel/syscall.c' and x['output']=='kernel/CMakeFiles/mckernel.img.dir/syscall.c.o'];assert len(crow)==1
for flag in ['MCKERNEL_RUST_F03_WAIT_HOST_PROVIDER','MCKERNEL_RUST_F03_TERMINATE_HOST_PROVIDER']:assert '-D'+flag in shlex.split(crow[0]['command'])
cache=(meta/'regenerated-CMakeCache.txt').read_text()
for token in ['ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=ON','ENABLE_RUST_KERNEL:BOOL=ON','PROFILE_ENABLE:BOOL=ON','ENABLE_PERF:BOOL=ON','ENABLE_RUSAGE:BOOL=ON','ENABLE_LINUX_WORK_IRQ_FOR_IKC:BOOL=ON','ENABLE_UBSAN:BOOL=OFF','MCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12','ENABLE_RUST_M14_SYSCALL_ADAPTERS:BOOL=OFF','ENABLE_NATIVE_FORK_OWNED_TRANSACTION:BOOL=OFF','MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL:BOOL=OFF','MCKERNEL_CRASH_DEFS_HEADER:FILEPATH=/sdk/crash-9.0.1/defs.h']:assert token in cache,token
commands=save('ACTUAL-RUST-AND-C-COMMANDS.json',dict(source=fact(PE/'build-payload.stdout'),line_1based=lineno,literal_command=rline,argv=argv,Rust_cfg=cfg,Rust_cfg_count=len(cfg),actual_C_command=crow[0],actual_link_inputs=objects,actual_link_argv=link_argv,only_added_cfgs=added,actual_source_commit=source))

result.update(status='PASS_ACTUAL6AAE_FULL_PHYSICAL_OWNER_PROVIDER_JOIN',source_commit=source,new2=[x['physical_owner'] for x in rootrows],retained34=retained,C_ledger_delta=ledger)
physical=save('OWNER-PROVIDER-JOINS.json',result)
changedproof=save('WAIT-TERMINATION-CHANGED-PATH-JOINS.json',dict(status='PASS_NEW_TWO_PUBLIC_ROOTS_C_EXCLUSIONS_WAIT_TABLE_ABI_PROVIDER_COMPONENTS_INLINE_CALLER_ANNOTATION_PENDING',source_commit=source,new2=rootrows,actual_wait_table=tables,current_callers=callerproof,current_four104=abi,required_lower_owners=lowerrows,prior34=retained,debug_constants96=dict(physical_owner=dc,input_section=dcsec,final_section=dfsec,words=list(struct.unpack('<12Q',db))),new_lowerings=lowers,actual_commands=commands,C_ledger=ledger,changed_units=changed,unchanged_units=unchanged,physical=physical))
summary=save('COMPONENT-FACTS.json',dict(status='PASS_PHYSICAL_TABLE_ABI_PROVIDER_COMPONENTS_PENDING_ACTUAL_INLINE_CALLER_SEMANTIC_ANNOTATION',source_commit=source,producer=fact(PE/'RESULT.json'),reader=fact(RE/'RESULT.json'),adopted_reader=fact(P/'READER-ADOPTION.json'),actual_image=result['image'],actual_map=result['map'],actual_Rust=next(x['identity'] for x in unitrows if x['object']==rustobj),new2=rootrows,actual_table=tables,actual_callers=callerproof,ABI104=abi,physical_provider_data=physical,changed_path=changedproof,commands=commands,input_provider_joins=len(joined),linker_provider_joins=len(assign),strong_import_occurrences=sum(x['import']['binding']=='GLOBAL' for x in imports),unique_import_names=len({x['import']['name'] for x in imports}),named_undefined=[],retained34=retained,C_ledger=ledger,entry=final['header']['entry'],arch_start=arch,LOADS=loads,notes=notes,no_INTERP_DYNAMIC_or_runtime_relocations=True,all_allocated_sections_LOAD_covered=True,archC_exec_FUNC_globals_zero=True,lifecycle=life,actual_positive_clients=25,metadata_records=reader['metadata'],method=fact(Path(__file__)),pure_ELF_parser=fact(P/'saved_elf.py'),reused_method=fact(M/'mprotect-signal-reader-p03-max-1/qualification-1/inlining-correction-1/qualify_saved_mprotect_signal.py'),remaining_qualification='Actual pending-signal termination source call has compiler-inlined body; final typed group/CAS/nohost/initializedrequest/NR231/do_syscall block annotation is required. Component records are frozen now; no failed named-call assumption or ELF replay needed.',original_acceptance_or_native_or_hold_release=False,raw_build_warnings=[dict(line_1based=i+1,text=line) for i,line in enumerate(log.splitlines()) if 'warning' in line.lower()]))
out.mkdir()
for name,d in staged.items():(out/name).write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(component=summary,changed=changedproof,tables=tables,ABI=abi,physical=physical,callers=callerproof,new_roots={x['name']:x['physical_owner']['final']['bytes'] for x in rootrows},input_globals=len(joined),imports=len(imports),Cledger=ledger),indent=2))
