import collections,hashlib,json,re,struct
from pathlib import Path
root=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1');build=root/'output/build';meta=root/'mmap-next-source-1/direct-call-type-correction-1/normal-incremental-1/metadata'
out=root/'mmap-next-source-1/direct-call-type-correction-1/normal-incremental-1/qualification-1';assert out.is_dir()
def fact(p):
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 return {'path':str(p),'bytes':n,'sha256':h.hexdigest()}
def elf(p):
 raw=p.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[0][:6]==b'\x7fELF\x02\x01' and h[2]==62
 ss=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])];ns=ss[h[13]];st=raw[ns[4]:ns[4]+ns[5]]
 def z(b,n):return b[n:b.index(b'\0',n)].decode('utf-8','surrogateescape')
 sections=[{'index':i,'name':z(st,s[0]),'type':s[1],'flags':s[2],'address':s[3],'offset':s[4],'bytes':s[5],'link':s[6],'info':s[7],'align':s[8],'entry_bytes':s[9]} for i,s in enumerate(ss)]
 syms=[]
 for s in ss:
  if s[1]!=2:continue
  t=ss[s[6]];strings=raw[t[4]:t[4]+t[5]];assert s[9]==24
  for off in range(s[4],s[4]+s[5],24):
   n,info,other,si,value,size=struct.unpack_from('<IBBHQQ',raw,off);syms.append({'index':(off-s[4])//24,'name':z(strings,n),'binding':{0:'LOCAL',1:'GLOBAL',2:'WEAK'}.get(info>>4,str(info>>4)),'type':{0:'NOTYPE',1:'OBJECT',2:'FUNC',3:'SECTION',4:'FILE',6:'TLS'}.get(info&15,str(info&15)),'visibility':other&3,'section_index':si,'value':value,'bytes':size})
 ph=[struct.unpack_from('<IIQQQQQQ',raw,h[5]+i*h[9]) for i in range(h[10])]
 return {'path':str(p),'header':{'type':h[1],'machine':h[2],'entry':h[4]},'sections':sections,'symbols':syms,'program_headers':[{'type':x[0],'flags':x[1],'offset':x[2],'vaddr':x[3],'paddr':x[4],'file_bytes':x[5],'memory_bytes':x[6],'align':x[7]} for x in ph]}
q=root/'mmap-next-source-1/direct-call-type-correction-1/normal-incremental-1';execution=json.loads((q/'execution-1/RESULT.json').read_text())
assert execution['source_commit']=='f2535305aaef51dd9b15a798f6cab1a16f29e575'
assert execution['all_client_waits_streams_joined'] and not execution['remaining_owned_child_pids']
assert not execution['both_UNKNOWN_released'] and not execution['original_acceptance']
assert len(execution['clients'])==18 and all(x['exit']==0 and x['direct_wait_joined'] and x['streams_closed'] for x in execution['clients'])
assert [x['phase'] for x in execution['phases']]==['build','metadata']
assert all(x['exit']==0 and not x['OOMKilled'] and x['owned_container_removed'] and x['client_wait_joined'] for x in execution['phases'])
import shlex
link_argv=shlex.split((meta/'regenerated-link.txt').read_text());objects=[x for x in link_argv if x.endswith('.o')];assert objects==json.loads((root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/ACTUAL-RUST-AND-C-COMMANDS.json').read_text())['actual_link_inputs']
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
# Preliminary duplicate owner output omitted; final joined table is written once.

# The method above reuses the independently reviewed first/four-selection-image ELF/map data join, with only
# new saved artifact paths, actual regenerated link input selection, the already
# reviewed exact __verbose section shape, and input/final type equality added.
# Everything below consumes saved bytes/records; it starts no project program.
import copy,datetime
q=root/'mmap-next-source-1/direct-call-type-correction-1/normal-incremental-1';execution=json.loads((q/'execution-1/RESULT.json').read_text())
request=json.loads((q/'REQUEST.json').read_text());binding=json.loads((q/'SOURCE-BINDING.json').read_text())
old=json.loads((root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/OWNER-PROVIDER-JOINS.json').read_text())
assert execution['source_commit']==binding['source_commit']=='f2535305aaef51dd9b15a798f6cab1a16f29e575'
assert (q/'execution-1/source-commit.stdout').read_text().strip()==binding['source_commit']
assert (q/'execution-1/ihk-commit.stdout').read_text().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
assert execution['all_client_waits_streams_joined'] and not execution['remaining_owned_child_pids']
assert not execution['both_UNKNOWN_released'] and not execution['original_acceptance']
assert all(c['exit']==0 and c['direct_wait_joined'] and c['streams_closed'] for c in execution['clients'])
assert len(execution['phases'])==2 and [p['phase'] for p in execution['phases']]==['build','metadata']
terminal_records=[]
for phase in execution['phases']:
 assert phase['exit']==0 and not phase['OOMKilled'] and phase['owned_container_removed'] and phase['client_wait_joined']
 tp=q/'execution-1'/(phase['phase']+'-terminal.stdout');terminal=json.loads(tp.read_text())[0];assert terminal['Id']==phase['CID']
 state=terminal['State'];assert not state['Running'] and not state['OOMKilled'] and state['Pid']==0 and state['ExitCode']==0
 terminal_records.append({'phase':phase['phase'],'terminal_record':fact(tp),'CID':phase['CID'],'state':state,'owned_container_removed':True})
metadata_records=[]
for rec in execution['metadata_outputs']:
 f=fact(Path(rec if isinstance(rec,str) else rec['path']))
 if isinstance(rec,dict):assert f['bytes']==rec['bytes'] and f['sha256']==rec['sha256']
 metadata_records.append(f)
for source in binding['source_records']:
 assert fact(Path('/home/holden/mckernel')/source['relative_path'])['sha256']==source['sha256']
assert binding['cache_effective_whole_F06']=='ON; source defaultOFF unchanged'
generic_source=Path('/home/holden/mckernel/kernel/syscall.c').read_text()
assert 'struct syscall_request request1 IHK_DMA_ALIGN = { 0 };' in generic_source

saved_identities={line.split(None,1)[1]:line.split(None,1)[0] for line in (meta/'artifact-identities.sha256').read_text().splitlines()}
saved_modes={}
for line in (meta/'artifact-modes.stdout').read_text().splitlines():
 mode,n,path=line.split(None,2);saved_modes[path]={'mode':mode,'bytes':int(n)}
for u in unitrows:
 path='/work/output/build/kernel/'+u['object'];assert u['identity']['sha256']==saved_identities[path] and u['identity']['bytes']==saved_modes[path]['bytes']
 u['identity']['mode']=saved_modes[path]['mode']
 u['language_class']='Rust' if u['object'].startswith('rust/') else ('assembly' if u['object'].endswith('.S.o') else 'C_or_included_C_header')
 u['allocated_executable_section_bytes']=sum(s['bytes'] for s in units[u['object']]['sections'] if s['flags']&2 and s['flags']&4)
for f in [result['image'],result['map']]:
 path='/work/output/build/kernel/'+Path(f['path']).name;assert f['sha256']==saved_identities[path] and f['bytes']==saved_modes[path]['bytes'];f['mode']=saved_modes[path]['mode']
assert result['image']['mode']=='755'
assert saved_identities['/work/output/build/config.h']=='ca251af0e69e4c82df042063bb9ffc180cbba2bd1c34f246d7589f44ed7bfa3f'
assert saved_identities['/work/output/build/ihk/config.h']=='01628a5a3edb44b73d0b0fc63eeb04be063998944156396594d13565924b6535'
assert saved_identities['/work/output/build/kernel/config/smp-x86.lds']=='b95d62a32abad215818adbde3597fad0607d4d14dddc7fc9adea09d9cd133bbd'
assert not mismatches,mismatches[:1]
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
f06_contract_path=root.parent/'f06-remaining-ownership-1/CONTRACT.json';f06_contract=json.loads(f06_contract_path.read_text())
selections=[dict(x,source_ABI=x['ABI']) for x in request['expected_selected_entries']]
request['retained_current_four_Rust_entries']=request['retained_prior_fourteen_Rust_entries']
selection_rows=[]
for selection in selections:
 name=selection['symbol'];owner=owner_by_name[name]
 assert owner['owner']['object']=='rust/mckernel_rust.o' and owner['final']['binding']=='GLOBAL' and owner['final']['type']=='FUNC'
 obj=selection['excluded_C_object'].removeprefix('kernel/') if hasattr(str,'removeprefix') else selection['excluded_C_object'][7:]
 definitions=[s for s in units[obj]['symbols'] if s['name']==name and s['section_index']!=0]
 assert not definitions,(name,definitions)
 assert len([s for s in units['rust/mckernel_rust.o']['symbols'] if s['name']==name and s['section_index']!=0 and s['binding']=='GLOBAL'])==1
 rustsource=Path('/home/holden/mckernel')/selection['Rust_source'];text=rustsource.read_text();sig=re.search(r'pub (?:unsafe )?extern "C" fn '+re.escape(name)+r'\([\s\S]*?\)\s*(?:->\s*[^\{]+)?\{',text)
 assert sig,name
 selection_rows.append(dict(selection,physical_owner=owner,C_defined_counterparts=definitions,Rust_source_identity=fact(rustsource),actual_Rust_C_ABI_signature=sig[0][:-1].strip(),real_C_ABI_checks_object=next(u['identity'] for u in unitrows if u['object']=='CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o')))
result['selected_do_mmap_function_joins']=selection_rows

retained_fourteen=[]
for name in request['retained_current_four_Rust_entries']:
 owner=owner_by_name[name];assert owner['owner']['object']=='rust/mckernel_rust.o' and owner['final']['type']=='FUNC'
 assert not any(s['name']==name and s['section_index']!=0 for obj,u in units.items() if not obj.startswith('rust/') for s in u['symbols'])
 retained_fourteen.append(owner)
result['retained_fourteen_current_Rust_entries']=retained_fourteen
result['credential_pair_physical_alias']=(owner_by_name['do_setresuid']['final']['value']==owner_by_name['do_setresgid']['final']['value'])

retainedC=[u for u in unitrows if u['language_class']=='C_or_included_C_header' and u['allocated_executable_section_bytes']]
result['retained_C_runtime_units']=retainedC
oldC={u['object']:u for u in old['retained_C_runtime_units']}
result['C_ledger_delta']=[{'object':u['object'],'previous_runtime_FUNC_rows':oldC[u['object']]['runtime_FUNC_rows'],'actual_runtime_FUNC_rows':u['runtime_FUNC_rows'],'removed_function_names':sorted(set(oldC[u['object']]['runtime_FUNC_names'])-set(u['runtime_FUNC_names'])),'added_function_names':sorted(set(u['runtime_FUNC_names'])-set(oldC[u['object']]['runtime_FUNC_names']))} for u in retainedC]
oldunits={u['object']:u for u in old['unit_summary']}
result['unchanged_constituent_bytes']=[u['object'] for u in unitrows if u['identity']['sha256']==oldunits[u['object']]['identity']['sha256']]
result['changed_constituent_bytes']=[u['object'] for u in unitrows if u['identity']['sha256']!=oldunits[u['object']]['identity']['sha256']]
oldimportkeys={(x['consumer_object'],x['import']['name'],x['import']['binding']) for x in old['import_joins']}
newimportkeys={(x['consumer_object'],x['import']['name'],x['import']['binding']) for x in imports}
result['new_import_edges']=[x for x in imports if (x['consumer_object'],x['import']['name'],x['import']['binding']) not in oldimportkeys]
result['removed_import_edges']=[{'consumer_object':o,'name':n,'binding':b} for o,n,b in sorted(oldimportkeys-newimportkeys)]
result['status']='PASS_ACTUAL_F253_DO_MMAP_RUST_C_EXCLUSION_ABI_PHYSICAL_PROVIDERS'
result['source_commit']=binding['source_commit'];result['baseline_reference']=fact(root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/OWNER-PROVIDER-JOINS.json')
result['stable_green20a_preservation']=fact(root/'stable-baselinef8cf0bd7-1/BASELINE.json')
result['no_original_acceptance']=True
cp=out/'OWNER-PROVIDER-JOINS.json'

log=(q/'execution-1/build-payload.stdout').read_text();lines=log.splitlines()
rustlines=[(i+1,s) for i,s in enumerate(lines) if '--crate-type' in s and '/bin/rustc' in s];assert len(rustlines)==1
lineno,rustline=rustlines[0];argv=shlex.split(rustline);cfg=[argv[i+1] for i,x in enumerate(argv[:-1]) if x=='--cfg']
assert len(cfg)==len(set(cfg)) and 'f03_credential_refresh_candidate' in cfg
for row in selection_rows:assert row['Rust_cfg'] in cfg
assert '--emit=obj,dep-info=/work/output/build/kernel/rust/mckernel_rust.raw.d' in argv or any('dep-info=' in x for x in argv)
assert set(f06_contract['selector_closure']['whole_added_cfgs']).issubset(cfg)
assert '--cfg' in argv and 'enable_profile' in cfg
cache=(meta/'regenerated-CMakeCache.txt').read_text()
for token in ['ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=ON','ENABLE_RUST_KERNEL:BOOL=ON','PROFILE_ENABLE:BOOL=ON','ENABLE_UBSAN:BOOL=OFF','MCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12','ENABLE_RUST_M14_SYSCALL_ADAPTERS:BOOL=OFF']:
 assert token in cache,token
commands=json.loads((meta/'regenerated-compile_commands.json').read_text());compiled=[]
for row in selection_rows:
 file='/src/kernel/syscall.c' if row['excluded_C_object'].endswith('/syscall.c.o') and '/__/arch/' not in row['excluded_C_object'] else '/src/arch/x86_64/kernel/syscall.c'
 candidates=[x for x in commands if x['file']==file and 'CMakeFiles/mckernel.img.dir/' in x['command']]
 assert len(candidates)==1
 a=shlex.split(candidates[0]['command']);assert '-D'+row['C_macro'] in a,row['C_macro']
 compiled.append({'symbol':row['symbol'],'file':file,'macro':row['C_macro'],'command':candidates[0]})
deps=(meta/'regenerated-mckernel_rust.d').read_text()
for rel in ['kernel/rust/syscall_offload_entry.rs','kernel/rust/f03_interrupt_syscall.rs','kernel/rust/f03_host_cleanup.rs','kernel/rust/f06_signal_tail.rs']:
 assert '/src/'+rel in deps,rel
assert next(p for p in execution['phases'] if p['phase']=='build')['exit']==0
assert 'Linking C executable mckernel.img' in log
assert any('/src/kernel/syscall.c' in s and '/usr/bin/cc ' in s for s in lines)
rustcommand={'schema':'m14-f253-mmap-saved-production-whole-Rust-command-v1','source':fact(q/'execution-1/build-payload.stdout'),'line_1based':lineno,'literal_command':rustline,'argv':argv,'token_count':len(argv),'Rust_cfg':cfg,'Rust_cfg_count':len(cfg),'do_mmap_C_compiler_pair':compiled,'actual_link_argv':link_argv,'actual_link_inputs':objects,'new_driver_probe_or_configure_called_by_qualifier':False,'actual_regeneration_trigger':'Six reviewed changed mmap/rollback sources trigger normal cache-reusing named build/CMake regeneration; no manual configure'}
rp=out/'ACTUAL-RUST-AND-C-COMMANDS.json';rp.write_text(json.dumps(rustcommand,indent=2,sort_keys=True)+'\n')


# New actual-owner data, closed source/ABI contracts reused. No producer or program is invoked.
reviewroot=root.parent/'do-mmap-final-review-publicabi-max-1/direct-call-type-correction-1'
source_review=reviewroot/'REVIEW.json';atomic_review=reviewroot/'atomic-result-1/REVIEW.json'
provider_path=root.parent/'do-mmap-default-ownership-1/ACTUAL-PROVIDER-ROWS.json';provider_rows=json.loads(provider_path.read_text())['rows']
actual_providers=[]
for previous in provider_rows:
 name=previous['name'];actual=owner_by_name[name]
 assert actual['owner']['object']=='rust/mckernel_rust.o' and actual['final']['type']==previous['final']['type']
 if actual['final']['type']=='FUNC':assert actual['final']['bytes']>0
 else:assert actual['final']['bytes']==previous['final']['bytes']
 actual_providers.append({'name':name,'actual_physical_owner':actual,'previous_type_owner_reference':previous,'source_ABI_and_complete_function_contract':fact(source_review),'address_size_code_equality_with_old_function_not_required':True})
assert len(actual_providers)==56
assert sum(x['actual_physical_owner']['final']['type']=='FUNC' for x in actual_providers)==55
assert sum(x['actual_physical_owner']['final']['type']=='OBJECT' for x in actual_providers)==1
assert sum(u['runtime_FUNC_rows'] for u in retainedC)==32
expected=set(request['source_expected_C_ledger'][0]['source_expected_remaining_names'])
generic=next(u for u in retainedC if u['object']=='CMakeFiles/mckernel.img.dir/syscall.c.o')
assert set(generic['runtime_FUNC_names'])==expected and len(generic['runtime_FUNC_names'])==32
assert len(result['C_ledger_delta'])==1 and result['C_ledger_delta'][0]['removed_function_names']==['do_mmap'] and not result['C_ledger_delta'][0]['added_function_names']
archobj='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o';archunit=next(x for x in unitrows if x['object']==archobj)
assert archunit['runtime_FUNC_rows']==archunit['global_definitions']==archunit['weak_definitions']==archunit['allocated_executable_section_bytes']==0
ru=units['rust/mckernel_rust.o'];rustpath=Path(ru['path']);imagepath=Path(result['image']['path']);raw=rustpath.read_bytes();image_raw=imagepath.read_bytes()
def symbol_bytes(p,unit,sym):
 sec=unit['sections'][sym['section_index']];off=sec['offset']+sym['value']-sec['address'];assert sec['type']!=8 and sec['offset']<=off and off+sym['bytes']<=sec['offset']+sec['bytes']
 with p.open('rb') as f:f.seek(off);b=f.read(sym['bytes'])
 assert len(b)==sym['bytes'];return b,off,sec
def cstr(address):
 secs=[s for s in final['sections'] if s['flags']&2 and s['type']!=8 and s['address']<=address<s['address']+s['bytes']];assert len(secs)==1
 s=secs[0];off=s['offset']+address-s['address'];end=image_raw.index(b'\0',off,min(off+4096,s['offset']+s['bytes']));return image_raw[off:end].decode('utf-8')
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
def static_records(fragment,module,n,func,lines):
 ss=[s for s in ru['symbols'] if fragment in s['name'] and module in s['name'] and s['type']=='OBJECT' and s['bytes']==32*n];assert len(ss)==1,(fragment,ss)
 ins=ss[0];outsyms=[s for s in final['symbols'] if s['name']==ins['name'] and s['type']=='OBJECT' and s['bytes']==ins['bytes']];assert len(outsyms)==1;fs=outsyms[0]
 ib,io,isec=symbol_bytes(rustpath,ru,ins);fb,fo,fsec=symbol_bytes(imagepath,final,fs);assert isec['name']=='__verbose' and isec['flags']&1 and fsec['flags']&1 and ins['value']%8==0 and fs['value']%8==0
 ps=[p for p in placements[('rust/mckernel_rust.o',isec['name'])] if p['address']+ins['value']==fs['value'] and p['bytes']>=isec['bytes']];assert len(ps)==1
 records=[]
 for j,line in enumerate(lines):
  filep,fn,fmt,lf=struct.unpack_from('<QQQI',fb,j*32);assert cstr(filep)=='/src/kernel/syscall.c' and cstr(fn)==func and fmt==0 and lf==line
  records.append({'record_offset':j*32,'file_pointer':filep,'file_string':cstr(filep),'function_pointer':fn,'function_string':cstr(fn),'fmt_pointer':fmt,'line_flags':lf,'logical_line':lf&0xffffff,'initial_upper8_flags':lf>>24,'observed_padding_hex':fb[j*32+28:j*32+32].hex(),'padding_not_an_extra_ABI_requirement':True})
 return {'input_symbol':ins,'final_symbol':fs,'input_section':isec,'actual_input_map_placement':ps[0],'input_file_offset':io,'final_file_offset':fo,'input_bytes_hex':ib.hex(),'final_bytes_hex':fb.hex(),'writable':True,'record_bytes':32,'records':records,'actual_pointer_relocations':relocs_for(ins)}

# Reuse F06 ABI/data scope; allow legitimate codegen and addresses to differ.
dc=owner_by_name['debug_constants'];db,do,dsec=symbol_bytes(rustpath,ru,dc['owner']['input']);df,dfo,dfsec=symbol_bytes(imagepath,final,dc['final'])
assert dc['owner']['object']=='rust/mckernel_rust.o' and dc['final']['type']=='OBJECT' and dc['final']['bytes']==96 and dsec['align']>=32 and dc['final']['value']%32==0 and dsec['flags']&1 and dfsec['flags']&1
words=list(struct.unpack('<12Q',db));assert db==df and words==[8128,7848,7872,7920,64,4208,4328,4304,4184,456,20,18446744073709551615]
descriptors=static_records('MMAP_DEBUG','f03_do_mmap',14,'do_mmap',[5945,6090,6269,6332,6414,6417,6439,6462,6469,6481,6503,6537,6582,6658])
mm=owner_by_name['do_mmap'];mmap_relocs=relocs_for(mm['owner']['input'])
rollback=[]
for name in ['process_add_range_update_bridge','process_add_range_remove_bridge']:
 p=owner_by_name[name];assert p['owner']['object']=='rust/mckernel_rust.o' and p['final']['type']=='FUNC' and p['final']['bytes']>0
 rollback.append({'symbol':name,'actual_physical_owner':p,'actual_current_relocations':relocs_for(p['owner']['input']),'unchanged_source_ABI_and_reviewed_new_transaction_contract':fact(root.parent/'do-mmap-default-ownership-1/provider-correction-1/PROVIDER-CONTRACT.json')})
basecmd=json.loads((root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/ACTUAL-RUST-AND-C-COMMANDS.json').read_text());assert set(cfg)==set(basecmd['Rust_cfg'])|{'f03_do_mmap_candidate'}
for path in ['f03_do_mmap.rs','process_helpers.rs','x86_memory_helpers.rs','f03_terminate.rs','f03_exit_group.rs']:
 assert '/src/kernel/rust/'+path in deps
for x in ['MCKERNEL_DO_SYSCALL_C_FILE=/src/kernel/syscall.c','MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS=0']:assert x in argv
assert 'MCKERNEL_RUST_F03_DO_MMAP' in compiled[0]['command']['command']
assert 'size_of::<SizeT>() == 8 && align_of::<SizeT>() == 8' in (Path('/home/holden/mckernel/kernel/rust/f03_do_mmap.rs').read_text())
assert 'size_of::<CULong>() == 8 && align_of::<CULong>() == 8' in (Path('/home/holden/mckernel/kernel/rust/f03_do_mmap.rs').read_text())
assert 'Rust do_mmap lossless size_t/unsigned long conversions' in generic_source
newdis=meta/'do-mmap-disassembly.stdout';dis=newdis.read_text();assert '<do_mmap>:' in dis
warnings=[]
rawlogs=[]
for suffix in ['stdout','stderr']:
 p=q/'execution-1'/('build-payload.'+suffix);text=p.read_text();rawlogs.append(fact(p))
 for i,line in enumerate(text.splitlines()):
  if re.search(r'\bwarning(?:\[[^]]+\])?:',line):warnings.append({'file':str(p),'line_1based':i+1,'literal':line})
changed={'schema':'m14-f253-do-mmap-actual-changed-path-qualification-v1','status':'PASS_ACTUAL_RUST_DO_MMAP_C_EXCLUSION_TYPED_PROVIDERS_AND_64BIT_GUARDS','source_commit':binding['source_commit'],'actual_do_mmap':selection_rows,'current56_real_provider_rows':actual_providers,'source_ABI_scope':'Reuse918 complete eight-arg/layout/body/54Rust-function contracts plus corrected611d sharedtransaction and actual4da atomic/six rollbackRSS results. Actual ELF types/owners/placements/newrelocations below join these unchanged declarations; NOTYPE imports alone are never signatures.','actual_shared_rollback_providers':rollback,'actual_do_mmap_relocations':mmap_relocs,'actual14_writable_debug_descriptors':descriptors,'paired_SizeT_CULong_width_alignment_guards':{'source_contract':fact(q.parent/'CONTRACT.json'),'selected_Rust_command':fact(rp),'selected_C_command':compiled[0],'both_actual_compiles_exit0':True,'no_pointer_reinterpretation':True},'retained_prior14_Rust_owners':retained_fourteen,'retained_F06_data':{'owner':dc,'exact12words':words,'bytes96_align32_writable':True,'unchanged_source_scope_reused':fact(root/'next-credential-f06-1/f06-successor-1/qualification-1/QUALIFICATION.json'),'new_XRSTOR_or_behavior_test_or_hardware_call':False},'arch_C_zero_executable_implementation':archunit,'targeted_new_do_mmap_passive_disassembly':fact(newdis),'raw_build_streams_unmodified':rawlogs,'raw_warning_lines':warnings,'warning_count_is_not_automatic_rejection_or_suppression':True,'reused_source_GO':fact(source_review),'reused_actual_atomic_GO':fact(atomic_review),'new_body_contract_audit_or_old_suite':False,'original_acceptance':False}
changed_path=out/'MMAP-CHANGED-PATH-JOINS.json';changed_path.write_text(json.dumps(changed,indent=2,sort_keys=True)+'\n')
result['changed_do_mmap_path_qualification']=fact(changed_path);result['retained_prior14_Rust_entries']=retained_fourteen;cp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
cond=copy.deepcopy(json.loads((root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/ORIGINAL-CONDITIONS.json').read_text()))
remaining=sum(u['runtime_FUNC_rows'] for u in retainedC)
scope='Actualf253 normal fullimage '+result['image']['sha256']+', one genuineRust do_mmap/C exclusion, typed56 source-callee/caller/provider rows, paired64bit guards, new sharedrollback source, prior14Rust/zeroarchC and allphysical imports joined. Generic'+str(remaining)+'C remains; sourceF6defaultOFF/cacheON, no program/native call.'
cond['schema']='m14-f253-do-mmap-original-whole-condition-mapping-v1';cond['E1_E2_decision']='Physical currentf253 completeimage/provider blocker RESOLVED. OriginalwholeM14-I02E1/E2 remain OPEN: '+str(remaining)+' genericprojectC FUNC rows/data plus completeall-file/default/capability/matchingmodule/native conditions. This one newentry never accepts a wholeleaf.'
for row in cond['rows']:
 row['actual_scope']=scope
 if row['decision']=='PRIOR_VERIFIED_SCOPE_REUSED_NOT_REOPENED':continue
 if row.get('parent')=='M14-I02':row['exact_remaining_condition']=cond['E1_E2_decision']
 elif row.get('parent')=='M14-I01':row['exact_remaining_condition']='Current selecteddo_mmap is genuinelyRust and itsC counterpart excluded; '+str(remaining)+' genericprojectC FUNC rows plus data and original completeheader/macro/semantic/default ownership obligations remain. Prior acceptedfourfiles stayclosed.'
 elif row.get('parent')=='M14-I03':row['exact_remaining_condition']='Currentf253 was compiled and passivelyread only. Matchingco-boot/module/apps/mapping/process/thread/signal/native resource-restoring lifecycle remain unmatched on thiscohort under genuine admission. No UNKNOWN released.'
 elif row['id'] in ('M14-03-04-DEFAULT','M14-03-05-DEFAULT','M14-F03-DEFAULT'):
  row['decision']='CHANGED_DO_MMAP_SOURCE_ABI_OWNERSHIP_PASS_WHOLE_ORIGINAL_CONDITION_OPEN';row['exact_remaining_condition']='One real currentdo_mmap owner/type/provider/guard/debug/image integration passes. WholeF03 still includes '+str(remaining)+' selected genericCfunctions and original allfile/default/behavior/native conditions. No count-only credit.'
cond['clean_build_scope']='One ordinary cache-reusing materially changed-source incremental image build and firstnew passive metadata read; no manualconfigure, partialinjection, featuredisable, oldsuite or replay. Actual unit equality/differences are observed only.';cond['current_actual_qualification']=fact(cp);cond['baseline_original_text_mapping']=fact(root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/ORIGINAL-CONDITIONS.json')
oc=out/'ORIGINAL-CONDITIONS.json';oc.write_text(json.dumps(cond,indent=2,sort_keys=True)+'\n')
memory=[]
for phase in execution['phases']:
 p=q/'execution-1'/(phase['phase']+'-MEMORY.json');samples=json.loads(p.read_text())['samples'];assert all(x['memory.failcnt']=='0' and 'oom_kill 0' in x['memory.oom_control'] for x in samples)
 memory.append({'phase':phase['phase'],'source':fact(p),'retained_samples':len(samples),'observed_sampled_highwater_bytes':max([int(x['memory.max_usage_in_bytes']) for x in samples]) if samples else None,'exact_terminal_whole_job_peak_proven':False})
qual={'schema':'m14-f253-do-mmap-actual-image-qualification-v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_ACTUAL_RUST_DO_MMAP_C_EXCLUSION_AND_FULL_PHYSICAL_PROVIDER_CLOSURE','owner':'/root/p04_source_max saved-byte qualifier; Root sole executor/publisher','source_commit':binding['source_commit'],'source_binding':fact(q/'SOURCE-BINDING.json'),'actual_execution':fact(q/'execution-1/RESULT.json'),'reviewed_operation':fact(q/'REQUEST.json'),'reviewed_operation_GO':fact(root.parent/'compute-image-operation-review-publicabi-max-1/do-mmap-incremental-1/REVIEW.json'),'actual_image':result['image'],'actual_map':result['map'],'actual_whole_Rust_object':next(x['identity'] for x in unitrows if x['object']=='rust/mckernel_rust.o'),'all11_constituent_identities':[x['identity'] for x in unitrows],'actual_new_do_mmap':selection_rows,'changed_path_proof':fact(changed_path),'commands':fact(rp),'ELF_layout':{'header':final['header'],'arch_start':arch,'program_headers':final['program_headers'],'notes':notes,'allocated_sections_LOAD_covered':True,'no_INTERP_DYNAMIC_or_runtime_relocations':True,'origin':'0xfffffffffe800000','legitimate_changed_addresses_and_codegen_allowed':True},'physical_provider_closure':{'data':fact(cp),'input_global_physical_joins':len(joined),'linker_assignment_joins':len(assign),'actual_final_globals':len(fg),'strong_import_occurrences':sum(x['import']['binding']=='GLOBAL' for x in imports),'weak_import_occurrences':sum(x['import']['binding']=='WEAK' for x in imports),'unique_import_names':len({x['import']['name'] for x in imports}),'named_undefined':[],'physical_mismatches':[],'current56_typed_source_provider_rows':len(actual_providers)},'retained_prior14_Rust_owners':retained_fourteen,'retained_C_runtime_debt':{'actual_FUNC_rows':remaining,'delta':result['C_ledger_delta'],'whole_original_C_retirement':False},'config_ABI':{'config':saved_identities['/work/output/build/config.h'],'IHK_config':saved_identities['/work/output/build/ihk/config.h'],'linker':saved_identities['/work/output/build/kernel/config/smp-x86.lds'],'actual_cache':fact(meta/'regenerated-CMakeCache.txt'),'IHK':'8d288b8bd81b50cc3a3f814d949b89bf416a6ec7','sourceF6defaultOFF':True,'cacheexplicitF6ON':True,'PROFILE_ON':True,'clonezero_initializer_retained':True,'paired_new64bit_C_and_Rust_guards_compiled':True,'unchanged_units_observed':result['unchanged_constituent_bytes'],'changed_units_observed':result['changed_constituent_bytes']},'lifecycle':{'actual_client_count':len(execution['clients']),'all18_positivebirth_wait_streams':True,'bothcontainers0_nonOOM_Pid0_removed':True,'terminal_records':terminal_records,'no_owned_children_remain':True,'both_UNKNOWN_released':False,'sampled_cgroup_highwaters':memory},'raw_warnings':{'raw_streams':rawlogs,'warning_lines':warnings,'all_raw_stream_bytes_retained':True},'metadata_records':metadata_records,'original_whole_conditions':fact(oc),'whole_I02_E1_E2_decision':cond['E1_E2_decision'],'stable_f8_green':fact(root/'stable-baselinef8cf0bd7-1/BASELINE.json'),'qualification_method':fact(out/'qualify_saved_image.py'),'reused_original_qualified_parser':fact(root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1/qualify_saved_image.py'),'qualifier_actions':'Only savedsource/ELF/map/JSON reads and private result writes; no subprocess, producer, compiler, helper, test, readelf/objdump, SDK query, bodyaudit, native/API/program/hardware call.','original_acceptance':False,'progress_changed_by_qualifier':False,'scope_limit':'Supported selectedartifact/source/type/ABI/provider/C-exclusion delta only. Prior14 and accepted scopes retained; genericC32/sourceF6defaultOFF/native/matchedruntime/original wholeconditions remain open.'}
qp=out/'QUALIFICATION.json';qp.write_text(json.dumps(qual,indent=2,sort_keys=True)+'\n')
for p in [qp,changed_path,cp,oc,rp]:print(json.dumps(fact(p),sort_keys=True))
print(json.dumps({'image':result['image'],'map':result['map'],'Rust':next(x['identity'] for x in unitrows if x['object']=='rust/mckernel_rust.o'),'new_do_mmap_bytes':mm['final']['bytes'],'retained_Rust_entries':len(retained_fourteen),'generic_C_FUNC_rows':remaining,'inputglobals':len(joined),'scriptglobals':len(assign),'strongimports':sum(x['import']['binding']=='GLOBAL' for x in imports),'uniqueimports':len({x['import']['name'] for x in imports}),'typed_provider_rows':len(actual_providers),'entry':hex(final['header']['entry']),'Rust_tokens':len(argv),'Rust_cfgs':len(cfg),'actual_clients':len(execution['clients']),'raw_warning_lines':len(warnings)},sort_keys=True))
