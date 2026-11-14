import collections,hashlib,json,re,struct
from pathlib import Path
root=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1');build=root/'output/build';meta=root/'four-selection-incremental-1/metadata'
out=root/'four-selection-incremental-1/qualification-1';assert out.is_dir()
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
import shlex
link_argv=shlex.split((meta/'regenerated-link.txt').read_text());objects=[x for x in link_argv if x.endswith('.o')];assert objects==json.loads((root/'four-selection-incremental-1/REQUEST.json').read_text())['actual_link_object_inputs']
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
p=out/'OWNER-DATA.json';p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

# The method above is the retained first-image ELF/map data join, with only
# new saved artifact paths, actual regenerated link input selection, the already
# reviewed exact __verbose section shape, and input/final type equality added.
# Everything below consumes saved bytes/records; it starts no project program.
import copy,datetime
q=root/'four-selection-incremental-1';execution=json.loads((q/'execution-1/RESULT.json').read_text())
request=json.loads((q/'REQUEST.json').read_text());binding=json.loads((q/'SOURCE-BINDING.json').read_text())
old=json.loads((root/'named-build-1/qualification-1/OWNER-PROVIDER-JOINS.json').read_text())
assert execution['source_commit']==binding['source_commit']=='594acfc067012d87ade1aff7ac0abdc5944ce257'
assert (q/'execution-1/source-commit.stdout').read_text().strip()==binding['source_commit']
assert (q/'execution-1/ihk-commit.stdout').read_text().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
assert execution['all_client_waits_streams_joined'] and not execution['remaining_owned_child_pids']
assert not execution['old_CPU0_UNKNOWN_released'] and not execution['original_acceptance']
assert all(c['exit']==0 and c['direct_wait_joined'] and c['streams_closed'] for c in execution['clients'])
assert len(execution['phases'])==2
for phase in execution['phases']:
 assert phase['attach_exit']==phase['container_exit']==0 and phase['owned_container_removed']
 state=phase['final_state'];assert not state['Running'] and not state['OOMKilled'] and state['Pid']==0 and state['ExitCode']==0
for rec in execution['metadata_outputs']:
 f=fact(Path(rec['path']));assert f['bytes']==rec['bytes'] and f['sha256']==rec['sha256']
for rec in binding['actual_six_current_files']:
 assert fact(Path(rec['actual_path']))['sha256']==rec['after_sha256']
generic_source=Path('/home/holden/mckernel/kernel/syscall.c').read_text()
assert 'struct syscall_request request1 = { 0 };' in generic_source

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
selection_rows=[]
for selection in request['expected_selected_entries']:
 name=selection['symbol'];owner=owner_by_name[name]
 assert owner['owner']['object']=='rust/mckernel_rust.o' and owner['final']['binding']=='GLOBAL' and owner['final']['type']=='FUNC'
 obj=selection['excluded_C_object'].removeprefix('kernel/') if hasattr(str,'removeprefix') else selection['excluded_C_object'][7:]
 definitions=[s for s in units[obj]['symbols'] if s['name']==name and s['section_index']!=0]
 assert not definitions,(name,definitions)
 assert len([s for s in units['rust/mckernel_rust.o']['symbols'] if s['name']==name and s['section_index']!=0 and s['binding']=='GLOBAL'])==1
 rustsource=Path('/home/holden/mckernel')/selection['Rust_source'];text=rustsource.read_text();sig=re.search(r'pub (?:unsafe )?extern "C" fn '+re.escape(name)+r'\([\s\S]*?\)\s*(?:->\s*[^\{]+)?\{',text)
 assert sig,name
 selection_rows.append(dict(selection,physical_owner=owner,C_defined_counterparts=definitions,Rust_source_identity=fact(rustsource),actual_Rust_C_ABI_signature=sig[0][:-1].strip(),real_C_ABI_checks_object=next(u['identity'] for u in unitrows if u['object']=='CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o')))
result['selected_four_entry_joins']=selection_rows
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
result['status']='PASS_ACTUAL594AC_FOUR_RUST_ENTRIES_C_EXCLUSION_AND_COMPLETE_PHYSICAL_PROVIDER_CLOSURE'
result['source_commit']=binding['source_commit'];result['baseline_reference']=fact(root/'named-build-1/qualification-1/OWNER-PROVIDER-JOINS.json')
result['stable_green20a_preservation']=fact(root/'stable-baseline20a7-1/BASELINE.json')
result['no_original_acceptance']=True
cp=out/'OWNER-PROVIDER-JOINS.json';cp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

log=(q/'execution-1/build-payload.stdout').read_text();lines=log.splitlines()
rustlines=[(i+1,s) for i,s in enumerate(lines) if '--crate-type' in s and '/bin/rustc' in s];assert len(rustlines)==1
lineno,rustline=rustlines[0];argv=shlex.split(rustline);cfg=[argv[i+1] for i,x in enumerate(argv[:-1]) if x=='--cfg']
assert len(argv)==207 and len(cfg)==76
for row in selection_rows:assert row['Rust_cfg'] in cfg
assert '--emit=obj,dep-info=/work/output/build/kernel/rust/mckernel_rust.raw.d' in argv or any('dep-info=' in x for x in argv)
assert 'f06_do_signal_whole_candidate' not in cfg
assert '--cfg' in argv and 'enable_profile' in cfg
cache=(meta/'regenerated-CMakeCache.txt').read_text()
for token in ['ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=OFF','ENABLE_RUST_KERNEL:BOOL=ON','PROFILE_ENABLE:BOOL=ON','ENABLE_UBSAN:BOOL=OFF','MCKERNEL_HOST_IRQ_ABI:STRING=linux-6.12','ENABLE_RUST_M14_SYSCALL_ADAPTERS:BOOL=OFF']:
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
assert 'Re-run cmake file: Makefile older than: /src/kernel/CMakeLists.txt' in log
assert '[ 90%] Linking C executable mckernel.img' in log
assert any('rust/abi_checks.c.o' in s and '/usr/bin/cc ' in s for s in lines)
rustcommand={'schema':'m14-594ac-saved-production-whole-Rust-command-v1','source':fact(q/'execution-1/build-payload.stdout'),'line_1based':lineno,'literal_command':rustline,'argv':argv,'token_count':len(argv),'Rust_cfg':cfg,'Rust_cfg_count':len(cfg),'four_C_compiler_pairs':compiled,'actual_link_argv':link_argv,'actual_link_inputs':objects,'new_driver_probe_or_configure_called_by_qualifier':False,'actual_regeneration_trigger':'Makefile older than /src/kernel/CMakeLists.txt; normal cmake --build graph, no manual configure'}
rp=out/'ACTUAL-RUST-AND-C-COMMANDS.json';rp.write_text(json.dumps(rustcommand,indent=2,sort_keys=True)+'\n')

cond=copy.deepcopy(json.loads((root/'named-build-1/qualification-1/ORIGINAL-CONDITIONS.json').read_text()))
scope='Actual594ac normal production incremental image44ed9519, same IHK8d/configca251/Linux6.12/GCC14/nightly1.95; four real Rust entry owners and excluded C definitions; all actual input/linker providers joined and no named UND. No native execution.'
remaining=sum(u['runtime_FUNC_rows'] for u in retainedC)
for row in cond['rows']:
 row['actual_scope']=scope
 if row['decision']=='PRIOR_VERIFIED_SCOPE_REUSED_NOT_REOPENED':continue
 if row.get('parent')=='M14-I02':row['exact_remaining_condition']='Physical normal whole-image build/provider closure now also passes for current594ac after four reviewed selections. The complete original all-file Rust/assembly cutover image/default/matching-module/capability condition remains open: '+str(remaining)+' actual project-C FUNC rows remain in F03/F06; this compilation-only cohort is not the final all-file native/deployed cohort. Reuse matching module/tool/ABI evidence; no absent algorithm, unspecified inventory or unchanged-build quota is asserted.'
 elif row.get('parent')=='M14-I01':row['exact_remaining_condition']='All actual current globals/imports physically join, and four entry owners moved from C to genuine Rust. Remaining '+str(remaining)+' project-C function rows and complete original source/header/macro/semantic/default ownership obligations are not retired.'
 elif row.get('parent')=='M14-I03':row['exact_remaining_condition']='Current594ac image was compiled and passively read only. Matching co-boot/module-load/useful applications/process/mapping/thread/signal/native lifecycle and resource-restoration conditions remain unmatched on this artifact, subject to existing genuine source/native/current-free/ownership gates. Reuse only actually matching prior results; all UNKNOWNs stay held.'
 else:row['exact_remaining_condition']='This image proves the actual selected integration/ABI/provider closure of the four reviewed changed entries. Whole original file/default Rust replacement behavior/provider/capability and any genuinely affected functional/native conditions remain open; current C functions are honestly retained. Accepted exact prior file scopes remain closed. No source-only, link-only or count-based original acceptance is inferred.'
cond['schema']='m14-594ac-four-selection-original-whole-condition-mapping-v1'
cond['E1_E2_decision']='Physical complete image/provider build blocker remains RESOLVED for current594ac. Whole original M14-I02 E1/E2 remain NOT FULLY DEMONSTRATED: '+str(remaining)+' actual project-C FUNC rows remain plus original all-file/default/matching-capability/native conditions. Four selected entry ownership corrections do not by themselves accept either whole condition.'
cond['clean_build_scope']='Real normal changed-input CMake regeneration, genuineRust and ten C/ASM target compiles plus bare-ld final link passed once on594ac using existing cache. Eight constituent byte hashes remain equal to retained20a; three changed constituents are genuinely new. No injected partial object or unchanged build replay.'
cond['current_actual_qualification']=fact(cp);cond['baseline_original_text_mapping']=fact(root/'named-build-1/qualification-1/ORIGINAL-CONDITIONS.json')
oc=out/'ORIGINAL-CONDITIONS.json';oc.write_text(json.dumps(cond,indent=2,sort_keys=True)+'\n')
memory=[]
for phase in execution['phases']:
 values=[int(v) for sample in phase.get('memory_samples',[]) for key,v in sample.get('values',{}).items() if key.endswith('/memory.max_usage_in_bytes')]
 memory.append({'phase':phase['phase'],'retained_samples':len(phase.get('memory_samples',[])),'observed_sampled_highwater_bytes':max(values) if values else None,'exact_terminal_whole_job_peak_proven':False,'scope':'Saved sampled cgroup v1 highwater before exit; actual nonOOM/cgroup limit and positive lifecycle proven independently.'})
qual={'schema':'m14-594ac-four-selection-actual-image-qualification-v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_CHANGED_FOUR_RUST_OWNERS_C_EXCLUSION_ACTUAL_IMAGE_ABI_AND_PHYSICAL_PROVIDER_CLOSURE','owner':'/root/p04_source_max saved-artifact qualification only; Root executor/publisher','source_commit':binding['source_commit'],'source_binding':fact(q/'SOURCE-BINDING.json'),'actual_execution':fact(q/'execution-1/RESULT.json'),'reviewed_operation':fact(q/'REQUEST.json'),'reviewed_operation_GO':fact(root.parent/'compute-image-operation-review-p03-max-1/four-selection-incremental-1/REVIEW.json'),'actual_image':result['image'],'actual_map':result['map'],'actual_whole_Rust_object':next(x['identity'] for x in unitrows if x['object']=='rust/mckernel_rust.o'),'actual_constituent_identities':[x['identity'] for x in unitrows],'selected_four_entries':selection_rows,'whole_Rust_and_C_commands':fact(rp),'ELF_layout':{'header':final['header'],'program_headers':final['program_headers'],'arch_start':arch,'notes':notes,'allocated_sections_fully_mapped':True,'no_INTERP_DYNAMIC_or_relocations':True,'origin_MAP_KERNEL_START':'0xfffffffffe800000','new_entry_or_size_not_required_to_equal_old':True},'physical_provider_closure':{'data':fact(cp),'input_global_physical_joins':len(joined),'linker_assignment_joins':len(assign),'all_global_final':len(fg),'strong_import_occurrences':sum(x['import']['binding']=='GLOBAL' for x in imports),'weak_import_occurrences':sum(x['import']['binding']=='WEAK' for x in imports),'unique_import_names':len({x['import']['name'] for x in imports}),'named_undefined':[],'mismatches':[],'new_import_edges':result['new_import_edges'],'removed_import_edges':result['removed_import_edges'],'type_proof_scope':'Every actual input/final symbol kind/size/section/offset is checked. Declared C/Rust ABI and exact supported layouts are supplied by independently reviewed six-file source and genuine C ABI checks target compiled successfully in this build. NOTYPE import names alone are not promoted into signature proof.'},'retained_C_runtime_debt':{'actual_runtime_FUNC_rows':remaining,'unit_rows':retainedC,'delta':result['C_ledger_delta'],'whole_original_C_retirement':False},'inert_C_inputs':[x for x in unitrows if x['language_class']=='C_or_included_C_header' and not x['allocated_executable_section_bytes']],'config_ABI':{'root_config_sha256':saved_identities['/work/output/build/config.h'],'IHK_config_sha256':saved_identities['/work/output/build/ihk/config.h'],'linker_sha256':saved_identities['/work/output/build/kernel/config/smp-x86.lds'],'cache_unchanged_from_green20a':fact(meta/'regenerated-CMakeCache.txt'),'wholeF06_OFF':True,'PROFILE_ON':True,'clone_zero_initializer_preserved':True,'IHK_HEAD':'8d288b8bd81b50cc3a3f814d949b89bf416a6ec7','eight_unchanged_objects':result['unchanged_constituent_bytes'],'three_changed_objects':result['changed_constituent_bytes'],'genuine_C_ABI_assert_object_compiled':True},'metadata_records':execution['metadata_outputs'],'lifecycle':{'all20_clients_positive_birth_wait_streams':len(execution['clients'])==20,'all_direct_waits_streams_closed':True,'no_owned_children_remain':True,'both_containers_0_nonOOM_Pid0_removed':True,'phases':[{k:v for k,v in p.items() if k!='memory_samples'} for p in execution['phases']],'memory_sample_scope':memory,'old_CPU0_256MiB_job1_UNJOINED_released':False},'original_whole_conditions':fact(oc),'whole_I02_E1_E2_decision':cond['E1_E2_decision'],'stable_green20a_preserved':fact(root/'stable-baseline20a7-1/BASELINE.json'),'operations_by_qualifier':'Only offline saved-byte/source/JSON parsing and private result writes. No compiler/build/configure/test/probe/readelf/container/image/native/program or child operation. All producer/reader actions are the already joined Root execution.','original_acceptance':False,'progress_changed_by_qualifier':False,'scope_limit':'Compiled image/real C ABI/physical providers and four changed Rust selections only. Retained project C, all-file/default behavior, matching native/deployment/application/lifecycle and original whole-milestone conditions remain explicit; no duplicate credit or artifact-only C retirement.'}
qp=out/'QUALIFICATION.json';qp.write_text(json.dumps(qual,indent=2,sort_keys=True)+'\n')
for p in [cp,rp,oc,qp]:print(json.dumps(fact(p),sort_keys=True))
print(json.dumps({'image':result['image'],'map':result['map'],'entry':hex(final['header']['entry']),'arch_start_bytes':arch['final']['bytes'],'four_entries':[(x['symbol'],x['physical_owner']['final']['bytes']) for x in selection_rows],'input_joins':len(joined),'linker_joins':len(assign),'imports':len(imports),'unique_imports':len({x['import']['name'] for x in imports}),'remaining_C_FUNC_rows':remaining,'C_delta':result['C_ledger_delta'],'changed_objects':result['changed_constituent_bytes'],'new_import_names':[(x['consumer_object'],x['import']['name']) for x in result['new_import_edges']]},sort_keys=True))
