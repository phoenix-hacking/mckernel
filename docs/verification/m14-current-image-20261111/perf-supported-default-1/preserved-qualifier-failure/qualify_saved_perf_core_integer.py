# Pure saved-file/ELF-byte qualification. No subprocess or project/SUT runtime import.
import argparse,collections,datetime,hashlib,json,re,shlex,struct,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P)) # exact private pure saved-ELF parser only; unrelated to native registered loaders.
from saved_elf import fact,elf
M=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
a=argparse.ArgumentParser();a.add_argument('--build',type=Path,required=True);a.add_argument('--reader-result-sha256',required=True);a.add_argument('--reader-root-completion',type=Path,required=True);a.add_argument('--reader-root-sha256',required=True);args=a.parse_args();build=args.build
PE=P/'source-set-gate-correction-1/execution-1';RE=P/'reader-1/qualified-producer-binding-1/execution-1';meta=P/'metadata-1';out=P/'qualification-1';assert not out.exists();out.mkdir(mode=0o700)
source='c964be3917c8f4c5031108aa927c84894584b667';staged={}
def save(name,value):
 assert name not in staged and not(out/name).exists(),name
 staged[name]=value;(out/name).write_text(json.dumps(value,indent=2)+'\n');return fact(out/name)
request=json.loads((RE.parent/'REQUEST.json').read_text());prodrequest=json.loads((PE.parent/'REQUEST.json').read_text());producer=json.loads((PE/'RESULT.json').read_text());reader=json.loads((RE/'RESULT.json').read_text());oracle=json.loads((P/'AFFECTED-READER-ORACLES.json').read_text());binding=json.loads((P/'SOURCE-BINDINGS.json').read_text())
assert producer['source_commit']==reader['source_commit']==request['source_commit']==source and producer['status'].startswith('PASS_C964_') and reader['status'].startswith('PASS_C964_')
assert fact(PE/'RESULT.json')['sha256']=='bc331c7173f1db51bd08d4feaa9ea7b87c2301f59bbe7a66885253a04a243458' and fact(RE/'RESULT.json')['sha256']==args.reader_result_sha256
assert fact(args.reader_root_completion)['sha256']==args.reader_root_sha256
producer_full=PE/'ROOT-EXEC-COMPLETION.json';life=[]
for directory,x,full,expected_clients,phase_names,cap,req in [(PE,producer,producer_full,20,['configure','build'],2*2**30,prodrequest),(RE,reader,args.reader_root_completion,12,['metadata'],512*2**20,request)]:
 assert len(x['clients'])==expected_clients and x['all_waits_streams_joined'] and x['remaining_owned_children']==[]
 for row in x['clients']:assert row['exit']==0 and row['pid']>0 and int(row['birth'])>0 and row['direct_wait_joined'] and row['streams_closed'] and not row.get('primary_error') and not row.get('secondary_errors') and not row.get('lifecycle_UNKNOWN')
 assert [row['phase'] for row in x['phases']]==phase_names and all(row['exit']==0 and not row['OOMKilled'] and row['owned_container_removed'] and row['client_wait_joined'] for row in x['phases'])
 full_data=json.loads(full.read_text());assert full_data['full_root_tool_terminal'] is True and full_data['session_id_remaining'] is None and full_data['actual_terminal_exit']==0
 release=directory/'RESOURCE-RELEASE.json';assert json.loads(release.read_text())['positive_all_scopes']
 for phase_name in phase_names:
  profile_path=directory/(phase_name+'-PROFILE.json');terminal_path=directory/(phase_name+'-TERMINAL.json');admission_path=directory/(phase_name+'-ADMISSION.json');profile=json.loads(profile_path.read_text());terminal=json.loads(terminal_path.read_text())['State'];admission=json.loads(admission_path.read_text());h=profile['HostConfig'];wanted=req[phase_name+'_phase']['expected_mounts']
  assert {(v['Source'],v['Destination'],not v['RW']) for v in profile['Mounts']}=={(v['source'],v['destination'],v['read_only']) for v in wanted}
  assert h['Memory']==h['MemorySwap']==cap and h['CpusetCpus']=='6' and h['ReadonlyRootfs'] and h['NetworkMode']=='none' and terminal['ExitCode']==terminal['Pid']==0 and not terminal['OOMKilled']
  assert admission['all_current_overhead_bytes']+admission['this_phase_bytes']<=4*2**30
  life.append(dict(phase=phase_name,positive_clients_in_operation=expected_clients,result=fact(directory/'RESULT.json'),profile=fact(profile_path),terminal=fact(terminal_path),admission=fact(admission_path),full_Root_completion=fact(full),positive_release=fact(release)))
assert len(reader['metadata'])==28 and {Path(v['path']).name for v in reader['metadata']}==set(request['metadata_phase']['output_contract']['required_files'])
for row in reader['metadata']:assert fact(Path(row['path']))==row
original_build=M/'compute-image-source-1/output/build'
for row in producer['actual_artifacts']:
 p=build/Path(row['path']).relative_to(original_build);identity=fact(p);assert identity['sha256']==row['sha256'] and identity['bytes']==row['bytes'] and oct(p.stat().st_mode&0o777)==row['mode']
retirement=PE.parent/'CURRENT-PROCESS-MEMORY-RETIREMENT.json';assert fact(retirement)['sha256']=='80cebf96b58c8cdc8f11709735f77e78c947b64af8b6e2c0ac72bba1289a7a98' and json.loads(retirement.read_text())['after']=={'bytes':0,'jobs':0}
normalQ=M/'perf-normal-integer-provider-review-publicabi-max-1/qualification-1/QUALIFICATION.json';assert fact(normalQ)['sha256']=='1db74dac1b866658a5a9208476ec2cdba09e98f905cbf25a28ebf1e5547197a2'
assert json.loads(normalQ.read_text())['decision'].startswith('GO')
envelope=save('ACTUAL-RECORD-ENVELOPE.json',dict(status='PASS_ACTUAL_TWO_PHASE_PRODUCER_AND31_COMMAND28_RECORD_READER_WITH_POSITIVE_ROOT_LIFECYCLES',source_commit=source,producer=fact(PE/'RESULT.json'),reader=fact(RE/'RESULT.json'),actual_metadata=reader['metadata'],lifecycle=life,actual_source_binding=fact(P/'SOURCE-BINDINGS.json'),canonical_normal_builtin_qualification=fact(normalQ),current_producer_retirement=fact(retirement),original_acceptance=False))
prior=M/'wait-termination-reader-p03-max-1/qualification-1';old=json.loads((prior/'preserved-cohort-bindings-1/OWNER-PROVIDER-JOINS.json').read_text());basecmd=json.loads((prior/'ACTUAL-RUST-AND-C-COMMANDS.json').read_text())
link_argv=shlex.split((meta/'regenerated-link.txt').read_text());objects=[v for v in link_argv if v.endswith('.o')];assert len(objects)==13 and len(set(objects))==13
core_input=next(v for v in producer['actual_readonly_core_inputs'] if v['path'].endswith('/core.o'))
def unit_file(name):
 if name=='/sdk/mckernel-core-195/core.o':return Path(core_input['path'])
 if name.startswith('/work/output/build/'):return build/name[len('/work/output/build/'):]
 if name.startswith('/'):raise AssertionError({'unexpected_link_object_namespace':name})
 return build/'kernel'/name
units={name:elf(unit_file(name)) for name in objects};final=elf(build/'kernel/mckernel.img')
assert [v for v in objects if 'freestanding/compiler_builtins.o' in v] and '/sdk/mckernel-core-195/core.o' in objects
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


ru=units['rust/mckernel_rust.o'];rustpath=Path(ru['path']);imagepath=Path(final['path']);raw=rustpath.read_bytes();image_raw=imagepath.read_bytes();cobj='CMakeFiles/mckernel.img.dir/syscall.c.o';rustobj='rust/mckernel_rust.o';cu=units[cobj];cpath=Path(cu['path']);cache_raw={obj:Path(u['path']).read_bytes() for obj,u in units.items()}
cpp='\n'.join(line for line in Path('/home/holden/mckernel/kernel/syscall.c').read_text().splitlines() if re.match(r'^#define\s+[A-Za-z_]',line))
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


# Actual complete provider image joined before any region or quota decision.
physical=save('OWNER-PROVIDER-JOINS.json',dict(result,status='PASS_ACTUAL_C964_FULL13_PHYSICAL_OWNER_PROVIDER_ZERO_UNDEFINED_JOIN',source_commit=source))
rootrows=[]
for name in oracle['new_public_Rust_roots']:
 x=required_rust(name);rootrows.append(dict(name=name,physical_owner=x,actual_all_code_bytes_and_current_link_relocations=bytes_join(rustobj,x['owner']['input'],x['final']),actual_relocation_provider_edges=[dict(relocation=v,actual_provider=resolve(ru,v['target'])[1]) for v in relocations(ru,x['owner']['input'])]))
for name in oracle['matching_C_definitions_absent']:assert not any(v['name']==name and v['section_index']!=0 for obj,u in units.items() if obj!=rustobj for v in u['symbols']),name
priornames=[v['name'] for v in old['retained34']+old['new2']];assert len(set(priornames))==36;retained=[required_rust(name) for name in priornames]
constant=owner_by_name['f03_perf_owner_entry_constants_v1'];assert constant['owner']['object']==cobj and constant['final']['type']=='OBJECT' and constant['final']['bytes']==96
ib,io,isc=symbol_bytes(cpath,cu,constant['owner']['input']);fb,fo,fsc=symbol_bytes(imagepath,final,constant['final']);words=list(struct.unpack('<12Q',ib));assert ib==fb and not isc['flags']&1 and not fsc['flags']&1 and not relocations(cu,constant['owner']['input'])
assert words[1]==80 and words[3]==8 and words[4:10]==[4,0,3,7,1<<63,298] and words[11]==10
constants=save('ACTUAL-PERF-ENTRY-CONSTANTS96.json',dict(status='PASS_ACTUAL_HEADER_DERIVED_READONLY12WORDS96_BYTES_CURRENT_C_AND_FINAL',physical_owner=constant,input_section=isc,final_section=fsc,input_file_offset=io,final_file_offset=fo,words=words,source_contract='Actual canonical C sizeof(perf_event_attr),sizeof(mckfd),sizeof(mc_perf_event),alignof(mc_perf_event),RAW/HARDWARE/HWCACHE,readformat mask,signbit,NRperf,AP_NOWAIT,F_SETSIG10; real entry.rs validates the first four layout fields and set-signal command. Header/typed normal compile and runtime/type proofs reused; constants10=IHK_MC_AP_NOWAIT is actual recorded value, no guessed alternative.',all_input_final_bytes_equal=True))
expected_words=json.loads((prior/'ACTUAL-ABI104-AND-PUBLIC-TYPES.json').read_text())['current_four_arrays'][0]['words'];arrays=[]
for u,path,names in [(cu,cpath,['f03_do_fork_c_abi_words']),(ru,rustpath,['f03_do_fork_rust_abi_words']),(final,imagepath,['f03_do_fork_c_abi_words','f03_do_fork_rust_abi_words'])]:
 for name in names:
  rows=[v for v in u['symbols'] if v['name']==name and v['section_index']!=0];assert len(rows)==1;v=rows[0];blob,off,section=symbol_bytes(path,u,v);assert v['bytes']==832 and list(struct.unpack('<104Q',blob))==expected_words and not relocations(u,v);arrays.append(dict(artifact=fact(path),symbol=v,section=section,file_offset=off,words=expected_words,sha256=hashlib.sha256(blob).hexdigest(),no_relocations=True))
abi=save('ACTUAL-ABI104-AND-PERF-TYPES.json',dict(status='PASS_FOUR104_WORD_ARRAYS_CURRENT_REAL_TYPED_PERF_ENTRY_AND_REQUEST_CALLBACK_LAYOUT',current_four_arrays=arrays,source_binding=fact(P/'SOURCE-BINDINGS.json'),real_72B_request_80B_Mckfd_and_production_type_guards='Actual current canonical full source30 compiled through genuine production C and full Rust with paired selection; old complete typed ABI/source review reused. No NOTYPE-name-only type inference.',prior_qualified104=fact(prior/'ACTUAL-ABI104-AND-PUBLIC-TYPES.json'),entry_constants96=constants))
dc=required_rust('debug_constants','OBJECT');db,_,dcs=symbol_bytes(rustpath,ru,dc['owner']['input']);df,_,dcfs=symbol_bytes(imagepath,final,dc['final']);assert db==df and len(db)==96 and dcs['flags']&1 and dcfs['flags']&1 and dcs['align']>=32
assert list(struct.unpack('<12Q',db))==[8128,7848,7872,7920,64,4208,4328,4304,4184,456,20,18446744073709551615]
regionmap=json.loads((M/'perf-default-whole-region-map-p03-max-1/MAPPING.PROPOSED.json').read_text());regions=[];allregionroots=[]
for region in regionmap['complete_nonperf_regions']:
 roots=[]
 for v in region['unique_supported_6aae_Rust_definitions']:
  x=required_rust(v['name']);roots.append(dict(name=v['name'],source_binding=v['source_binding'],current_physical_owner=x));allregionroots.append(v['name'])
 regions.append(dict(region=region['region'],current_required_Rust_roots=roots,scope_source='Frozen complete original03-05 region mapping7c40 unchanged'))
assert len(allregionroots)==43 and len(set(allregionroots))==43
lower_region=[required_rust(v['name']) for v in regionmap['credential_error_aware_provider_disposition']['current_6aae_actual_lower_Rust_owners']+regionmap['file_and_other_delegated_semantics']['actual_dispatch_and_forward_Rust_owners']]
dispatch=regionmap['actual_dispatch_binding'];dispatchname=dispatch['table_physical_owner']['name'];dispatchbinding=dispatch['binding_physical_owner']['name'];dtable=required_rust(dispatchname,'OBJECT');dbinding=required_rust(dispatchbinding,'OBJECT');dispatchproof=dict(table=dtable,binding=dbinding,table_all_current_data_and_relocations=bytes_join(rustobj,dtable['owner']['input'],dtable['final']),binding_all_current_data_and_relocations=bytes_join(rustobj,dbinding['owner']['input'],dbinding['final']))
regionproof=save('ACTUAL-COMPLETE-03-05-REGION-OWNER-JOINS.json',dict(status='PASS_CURRENT_ALL43_NONPERF_ROOTS_AND_ERROR_AWARE_CREDENTIAL_AND_DELEGATED_DISPATCH_PROVIDERS',original_frozen_mapping=fact(M/'perf-default-whole-region-map-p03-max-1/MAPPING.PROPOSED.json'),regions=regions,all43_nonperf_roots=allregionroots,current_typed_lower_owners=lower_region,actual_native_dispatch_table=dispatchproof,new_perf_public_roots=rootrows,original_acceptance=False))
ids={};modes={}
for line in (meta/'artifact-identities.sha256').read_text().splitlines():h,path=line.split(None,1);ids[path.strip()]=h
for line in (meta/'artifact-modes.stdout').read_text().splitlines():mode,n,path=line.split(None,2);modes[path]=dict(mode=mode,bytes=int(n))
oldunits={v['object']:v for v in old['unit_summary']};ledger=[];changed=[];unchanged=[]
for u in unitrows:
 obj=u['object'];u['language_class']='Rust_or_Rust_upstream' if obj==rustobj or 'compiler_builtins.o' in obj or obj=='/sdk/mckernel-core-195/core.o' else ('assembly' if obj.endswith('.S.o') else 'C_or_included_C_header');u['allocated_executable_section_bytes']=sum(v['bytes'] for v in units[obj]['sections'] if v['flags']&2 and v['flags']&4)
 if obj in oldunits:
  (unchanged if oldunits[obj]['identity']['sha256']==u['identity']['sha256'] else changed).append(obj)
  key='/work/output/build/kernel/'+obj;assert ids[key]==u['identity']['sha256'] and modes[key]['bytes']==u['identity']['bytes'];u['identity']['mode']=modes[key]['mode']
  if u['language_class']=='C_or_included_C_header' and (u['runtime_FUNC_rows'] or oldunits[obj]['runtime_FUNC_rows']):ledger.append(dict(object=obj,previous_count=oldunits[obj]['runtime_FUNC_rows'],actual_count=u['runtime_FUNC_rows'],removed=sorted(set(oldunits[obj]['runtime_FUNC_names'])-set(u['runtime_FUNC_names'])),added=sorted(set(u['runtime_FUNC_names'])-set(oldunits[obj]['runtime_FUNC_names'])),actual_names=u['runtime_FUNC_names']))
assert len(ledger)==1 and ledger[0]['removed']==sorted(oracle['C_ledger']['expected_only_removed']) and ledger[0]['added']==[] and set(ledger[0]['actual_names'])==set(oracle['C_ledger']['expected_retained_debt'])
archC=next(v for v in unitrows if v['object']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o');assert archC['allocated_executable_section_bytes']==archC['runtime_FUNC_rows']==archC['global_definitions']==0
log=(PE/'build-payload.stdout').read_text();rustlines=[(n+1,line) for n,line in enumerate(log.splitlines()) if '/bin/rustc' in line and '--crate-type' in line];whole=[(n,line) for n,line in rustlines if '--crate-name mckernel_rust' in line];assert len(whole)==1;lineno,line=whole[0];argv=shlex.split(line);cfg=[argv[i+1] for i,v in enumerate(argv[:-1]) if v=='--cfg'];assert len(cfg)==len(set(cfg)) and set(cfg)==set(basecmd['Rust_cfg'])|{'f03_perf_owner_protocol'}
assert '--sysroot=/dev/null' in argv and '--extern' in argv and any('core=/sdk/mckernel-core-195/libcore.rmeta'==v for v in argv) and any(v.startswith('compiler_builtins=') and v.endswith('/kernel/rust/freestanding/libcompiler_builtins.rmeta') for v in argv)
cc=json.loads((meta/'regenerated-compile_commands.json').read_text());crow=[v for v in cc if v['file']=='/src/kernel/syscall.c' and v['output']=='kernel/CMakeFiles/mckernel.img.dir/syscall.c.o'];assert len(crow)==1 and '-DMCKERNEL_RUST_F03_PERF_OWNER_PROTOCOL' in shlex.split(crow[0]['command'])
oldflags={v for v in shlex.split(basecmd['actual_C_command']['command']) if v.startswith('-DMCKERNEL_')};newflags={v for v in shlex.split(crow[0]['command']) if v.startswith('-DMCKERNEL_')};assert newflags==oldflags|{'-DMCKERNEL_RUST_F03_PERF_OWNER_PROTOCOL'}
cache=(meta/'regenerated-CMakeCache.txt').read_text();bound=json.loads(Path(request['inputs']['path']).read_text())
for token in bound['current_cache_required_fields']+['PROFILE_ENABLE:BOOL=ON','ENABLE_PERF:BOOL=ON','ENABLE_RUSAGE:BOOL=ON','ENABLE_UBSAN:BOOL=OFF']:assert token in cache,token
commands=save('ACTUAL-RUST-C-NORMAL-PROVIDER-AND-LINK-COMMANDS.json',dict(source=fact(PE/'build-payload.stdout'),whole_Rust_line_1based=lineno,whole_Rust_literal=line,whole_Rust_argv=argv,Rust_cfg=cfg,Rust_cfg_count=len(cfg),only_added_cfg='f03_perf_owner_protocol',actual_C_command=crow[0],only_added_C_macro='MCKERNEL_RUST_F03_PERF_OWNER_PROTOCOL',actual_link_argv=link_argv,actual_link_inputs=objects,new_generated_normal_integer_material_Q=fact(normalQ),no_HOST_projection_or_standalone_H_object_injection=True))
changedproof=save('PERF-CORE-INTEGER-CHANGED-PATH-JOINS.json',dict(status='PASS_CURRENT_NEW2_PHYSICAL_RUST_OWNERS_C_EXCLUSIONS_REAL96B_ENTRY_CURRENT104_ALL13_PROVIDERS',source_commit=source,new2=rootrows,entry_constants96=constants,four104=abi,current_complete_regions=regionproof,retained36=retained,debug_constants96=dict(physical_owner=dc,input_section=dcs,final_section=dcfs,words=list(struct.unpack('<12Q',db))),actual_commands=commands,C_ledger=ledger,changed_existing_units=changed,unchanged_existing_units=unchanged,new_provider_units=[v for v in objects if v not in oldunits],physical=physical,canonical_normal_provider_Q=fact(normalQ)))
qualification=save('QUALIFICATION.json',dict(status='PASS_ACTUAL_C964_NORMAL_CORE_INTEGER_AND_PERF_FULL_IMAGE_OWNERSHIP_ABI_PROVIDER_COMPONENTS_FOR_INDEPENDENT_COMPLETE_ORIGINAL03_05_DEFAULT_DECISION',source_commit=source,actual_image=fact(build/'kernel/mckernel.img'),actual_map=fact(build/'kernel/mckernel.img.map'),actual_Rust=fact(rustpath),actual_C=fact(cpath),actual_record_envelope=envelope,actual_new2=rootrows,changed_path_joins=changedproof,complete_original_region_joins=regionproof,actual_constants96=constants,current_four104=abi,full13_owner_provider_map=physical,input_provider_joins=len(joined),linker_provider_joins=len(assign),strong_import_occurrences=sum(v['import']['binding']=='GLOBAL' for v in imports),unique_import_names=len({v['import']['name'] for v in imports}),named_undefined=[],prior36_retained=retained,actual_C_ledger=ledger,actual_current_arch_start=arch,actual_entry=final['header']['entry'],actual_LOADS=loads,actual_notes=notes,no_INTERP_DYNAMIC_or_runtime_relocations=True,all_allocated_sections_LOAD_covered=True,current_archC_exec_FUNC_globals_zero=True,canonical_normal_builtin_qualification=fact(normalQ),producer=fact(PE/'RESULT.json'),reader=fact(RE/'RESULT.json'),lifecycle=life,actual_positive_clients=32,raw_build_warning_lines=[dict(line_1based=i+1,text=line) for i,line in enumerate(log.splitlines()) if 'warning' in line.lower()],method=fact(Path(__file__)),pure_saved_parser=fact(P/'saved_elf.py'),original_DEFAULT_or_FUNCTIONAL_native_parent_or_milestone_acceptance=False,limits='Pure saved ELF/source/artifact qualification; whole original03-05 DEFAULT is separately independently decided; remaining exec/UTI C4 and all native/FUNCTIONAL/UNKNOWN holds unchanged.'))
result=save('RESULT.json',dict(status='PASS_SAVED_DATA_ONLY_CURRENT_C964_IMAGE_QUALIFICATION',qualification=qualification,component=changedproof,physical=physical,records=28,clients=32,source_commit=source,source_implementation_or_SUT_tools_not_executed=True))
print(json.dumps(dict(qualification=qualification,result=result,changed=changedproof,physical=physical,newroot_bytes={v['name']:v['physical_owner']['final']['bytes'] for v in rootrows},physical_provider_joins=len(joined),linker_globals=len(assign),strong_import_occurrences=sum(v['import']['binding']=='GLOBAL' for v in imports),named_undefined=0,C_ledger=ledger)))
