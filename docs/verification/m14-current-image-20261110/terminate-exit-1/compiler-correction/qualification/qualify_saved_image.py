import collections,hashlib,json,re,struct
from pathlib import Path
root=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1');build=root/'output/build';meta=root/'terminate-exit-incremental-1/compiler-correction-1/metadata'
out=root/'terminate-exit-incremental-1/compiler-correction-1/qualification-1';assert out.is_dir()
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
link_argv=shlex.split((meta/'regenerated-link.txt').read_text());objects=[x for x in link_argv if x.endswith('.o')];assert objects==json.loads((root/'next-credential-f06-1/f06-successor-1/qualification-1/ACTUAL-RUST-AND-C-COMMANDS.json').read_text())['actual_link_inputs']
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

# The method above reuses the independently reviewed first/four-selection-image ELF/map data join, with only
# new saved artifact paths, actual regenerated link input selection, the already
# reviewed exact __verbose section shape, and input/final type equality added.
# Everything below consumes saved bytes/records; it starts no project program.
import copy,datetime
q=root/'terminate-exit-incremental-1/compiler-correction-1';execution=json.loads((q/'execution-1/RESULT.json').read_text())
request=json.loads((q/'REQUEST.json').read_text());binding=json.loads((q/'SOURCE-BINDING.json').read_text())
old=json.loads((root/'next-credential-f06-1/f06-successor-1/qualification-1/OWNER-PROVIDER-JOINS.json').read_text())
assert execution['source_commit']==binding['source_commit']=='f8cf0bd7e0b33bfed8f5d2ce6f69b16c20a9ec21'
assert (q/'execution-1/source-commit.stdout').read_text().strip()==binding['source_commit']
assert (q/'execution-1/ihk-commit.stdout').read_text().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
assert execution['all_client_waits_streams_joined'] and not execution['remaining_owned_child_pids']
assert not execution['old_CPU0_UNKNOWN_released'] and not execution['original_acceptance']
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
for source in binding['actual_six_files']:
 assert fact(Path('/home/holden/mckernel')/source['path'])['sha256']==source['sha256']
assert binding['source_default_F06_OFF_cache_explicit_ON']
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
request['retained_current_four_Rust_entries']=request['retained_prior_ten_Rust_entries']
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
result['selected_terminate_exit_four_function_joins']=selection_rows

retained_ten=[]
for name in request['retained_current_four_Rust_entries']:
 owner=owner_by_name[name];assert owner['owner']['object']=='rust/mckernel_rust.o' and owner['final']['type']=='FUNC'
 assert not any(s['name']==name and s['section_index']!=0 for obj,u in units.items() if not obj.startswith('rust/') for s in u['symbols'])
 retained_ten.append(owner)
result['retained_ten_current_Rust_entries']=retained_ten
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
result['status']='PASS_ACTUALF8CF_TERMINATE_EXIT_RUST_C_EXCLUSION_CORRECTED_LOCK_ABI_PHYSICAL_PROVIDERS'
result['source_commit']=binding['source_commit'];result['baseline_reference']=fact(root/'next-credential-f06-1/f06-successor-1/qualification-1/OWNER-PROVIDER-JOINS.json')
result['stable_green20a_preservation']=fact(root/'stable-baseline1e64-wholeON-1/BASELINE.json')
result['no_original_acceptance']=True
cp=out/'OWNER-PROVIDER-JOINS.json';cp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

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
assert '[ 90%] Linking C executable mckernel.img' in log
assert any('rust/abi_checks.c.o' in s and '/usr/bin/cc ' in s for s in lines)
rustcommand={'schema':'m14-f8cf-saved-production-whole-Rust-command-v1','source':fact(q/'execution-1/build-payload.stdout'),'line_1based':lineno,'literal_command':rustline,'argv':argv,'token_count':len(argv),'Rust_cfg':cfg,'Rust_cfg_count':len(cfg),'terminate_exit_C_compiler_pairs':compiled,'actual_link_argv':link_argv,'actual_link_inputs':objects,'new_driver_probe_or_configure_called_by_qualifier':False,'actual_regeneration_trigger':'Meaningfully corrected f8source retried failednormalnamedbuild with unchanged validwholeONcache; no manual configure'}
rp=out/'ACTUAL-RUST-AND-C-COMMANDS.json';rp.write_text(json.dumps(rustcommand,indent=2,sort_keys=True)+'\n')

cond=copy.deepcopy(json.loads((root/'next-credential-f06-1/f06-successor-1/qualification-1/ORIGINAL-CONDITIONS.json').read_text()))
scope='Actualf8cf correctedterminate-exit normal production image0f7525a7, same IHK8d/configca251/Linux6.12/GCC14/nightly1.95; four new terminate-exit Rust functions/C exclusions and ten retained prior Rust entries; all actual input/linker providers joined and no named UND. No native execution.'
remaining=sum(u['runtime_FUNC_rows'] for u in retainedC)
for row in cond['rows']:
 row['actual_scope']=scope
 if row['decision']=='PRIOR_VERIFIED_SCOPE_REUSED_NOT_REOPENED':continue
 if row.get('parent')=='M14-I02':row['exact_remaining_condition']='Physical normal whole-image build/provider closure now also passes for currentf8cf after four reviewed terminate-exit selections and correctednominal-lock guards. The complete original all-file Rust/assembly cutover image/default/matching-module/capability condition remains open: '+str(remaining)+' actual project-C FUNC rows remain in F03/F06; this compilation-only cohort is not the final all-file native/deployed cohort. Reuse matching module/tool/ABI evidence; no absent algorithm, unspecified inventory or unchanged-build quota is asserted.'
 elif row.get('parent')=='M14-I01':row['exact_remaining_condition']='All actual current globals/imports physically join, and terminate and threeexitgroup entries moved from C to genuineRust. Remaining '+str(remaining)+' project-C function rows and complete original source/header/macro/semantic/default ownership obligations are not retired.'
 elif row.get('parent')=='M14-I03':row['exact_remaining_condition']='Currentf8cf explicitwholeON image was compiled and passively read only. Matching co-boot/module-load/useful applications/process/mapping/thread/signal/native lifecycle and resource-restoration conditions remain unmatched on this artifact, subject to existing genuine source/native/current-free/ownership gates. Reuse only actually matching prior results; all UNKNOWNs stay held.'
 else:row['exact_remaining_condition']='This image proves the actual selected integration/ABI/provider closure of the four terminate-exit functions under unchangedwholeONprofile. Whole original file/default Rust replacement behavior/provider/capability and any genuinely affected functional/native conditions remain open; current C functions are honestly retained. Accepted exact prior file scopes remain closed. No source-only, link-only or count-based original acceptance is inferred.'
cond['schema']='m14-f8cf-terminate-exit-corrected-original-whole-condition-mapping-v1'
cond['E1_E2_decision']='Physical complete image/provider build blocker remains RESOLVED for currentf8cf. Whole original M14-I02 E1/E2 remain NOT FULLY DEMONSTRATED: '+str(remaining)+' actual project-C FUNC rows remain plus original all-file/default/matching-capability/native conditions. Four terminate-exit ownership corrections do not by themselves accept either whole condition.'
cond['clean_build_scope']='Real normal changed-input CMake regeneration, genuineRust and ten C/ASM target compiles plus bare-ld final link passed once ona740 using existing cache. Actual per-object identity equality/changes against qualified594ac are recorded in the owner table. No injected partial object or unchanged build replay.'
cond['current_actual_qualification']=fact(cp);cond['baseline_original_text_mapping']=fact(root/'next-credential-f06-1/f06-successor-1/qualification-1/ORIGINAL-CONDITIONS.json')
oc=out/'ORIGINAL-CONDITIONS.json';oc.write_text(json.dumps(cond,indent=2,sort_keys=True)+'\n')
memory=[]
for phase in execution['phases']:
 mp=q/'execution-1'/(phase['phase']+'-MEMORY.json');samples=json.loads(mp.read_text())['samples'];values=[int(x['memory.max_usage_in_bytes']) for x in samples]
 assert all(x['memory.failcnt']=='0' and 'oom_kill 0' in x['memory.oom_control'] for x in samples)
 memory.append({'phase':phase['phase'],'source':fact(mp),'retained_samples':len(samples),'observed_sampled_highwater_bytes':max(values) if values else None,'exact_terminal_whole_job_peak_proven':False,'scope':'Saved sampled cgroup v1 highwater before exit; actual nonOOM/cgroup limit and positive lifecycle proven independently.'})
qual={'schema':'m14-f8cf-terminate-exit-corrected-actual-image-qualification-v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_CORRECTED_TERMINATE_EXIT_RUST_OWNERS_C_EXCLUSION_LOCK_ABI_AND_PHYSICAL_PROVIDER_CLOSURE','owner':'/root/p04_source_max saved-artifact qualification only; Root executor/publisher','source_commit':binding['source_commit'],'source_binding':fact(q/'SOURCE-BINDING.json'),'actual_execution':fact(q/'execution-1/RESULT.json'),'reviewed_operation':fact(q/'REQUEST.json'),'reviewed_operation_GO':fact(root.parent/'compute-image-operation-review-publicabi-max-1/terminate-exit-incremental-1/compiler-correction-1/REVIEW.json'),'actual_image':result['image'],'actual_map':result['map'],'actual_whole_Rust_object':next(x['identity'] for x in unitrows if x['object']=='rust/mckernel_rust.o'),'actual_constituent_identities':[x['identity'] for x in unitrows],'selected_terminate_exit_four_functions':selection_rows,'retained_ten_current_Rust_entries':retained_ten,'credential_pair_physical_alias':result['credential_pair_physical_alias'],'whole_Rust_and_C_commands':fact(rp),'ELF_layout':{'header':final['header'],'program_headers':final['program_headers'],'arch_start':arch,'notes':notes,'allocated_sections_fully_mapped':True,'no_INTERP_DYNAMIC_or_relocations':True,'origin_MAP_KERNEL_START':'0xfffffffffe800000','new_entry_or_size_not_required_to_equal_old':True},'physical_provider_closure':{'data':fact(cp),'input_global_physical_joins':len(joined),'linker_assignment_joins':len(assign),'all_global_final':len(fg),'strong_import_occurrences':sum(x['import']['binding']=='GLOBAL' for x in imports),'weak_import_occurrences':sum(x['import']['binding']=='WEAK' for x in imports),'unique_import_names':len({x['import']['name'] for x in imports}),'named_undefined':[],'mismatches':[],'new_import_edges':result['new_import_edges'],'removed_import_edges':result['removed_import_edges'],'type_proof_scope':'Every actual input/final symbol kind/size/section/offset is checked. Declared C/Rust ABI and exact supported layouts are supplied by independently reviewed six-file source and genuine C ABI checks target compiled successfully in this build. NOTYPE import names alone are not promoted into signature proof.'},'retained_C_runtime_debt':{'actual_runtime_FUNC_rows':remaining,'unit_rows':retainedC,'delta':result['C_ledger_delta'],'whole_original_C_retirement':False},'inert_C_inputs':[x for x in unitrows if x['language_class']=='C_or_included_C_header' and not x['allocated_executable_section_bytes']],'config_ABI':{'root_config_sha256':saved_identities['/work/output/build/config.h'],'IHK_config_sha256':saved_identities['/work/output/build/ihk/config.h'],'linker_sha256':saved_identities['/work/output/build/kernel/config/smp-x86.lds'],'cache_unchanged_from_green20a':fact(meta/'regenerated-CMakeCache.txt'),'repository_wholeF06_default_OFF':True,'explicit_candidate_cache_wholeF06_ON':True,'PROFILE_ON':True,'clone_zero_initializer_preserved':True,'IHK_HEAD':'8d288b8bd81b50cc3a3f814d949b89bf416a6ec7','unchanged_objects':result['unchanged_constituent_bytes'],'changed_objects':result['changed_constituent_bytes'],'genuine_C_ABI_assert_object_compiled':True},'metadata_records':metadata_records,'lifecycle':{'all_clients_positive_birth_wait_streams':all(x['exit']==0 and x['direct_wait_joined'] and x['streams_closed'] for x in execution['clients']),'actual_client_count':len(execution['clients']),'all_direct_waits_streams_closed':True,'no_owned_children_remain':True,'both_containers_0_nonOOM_Pid0_removed':True,'phases':execution['phases'],'terminal_records':terminal_records,'memory_sample_scope':memory,'old_CPU0_256MiB_job1_UNJOINED_released':False},'original_whole_conditions':fact(oc),'whole_I02_E1_E2_decision':cond['E1_E2_decision'],'stable_green20a_preserved':fact(root/'stable-baseline1e64-wholeON-1/BASELINE.json'),'operations_by_qualifier':'Only offline saved-byte/source/JSON parsing and private result writes. No compiler/build/configure/test/probe/readelf/container/image/native/program or child operation. All producer/reader actions are the already joined Root execution.','original_acceptance':False,'progress_changed_by_qualifier':False,'scope_limit':'Correctedterminate-exit realimage/source/locktypeABI/physicalproviders and fournewRustentries only; previous10Rust/F06data retained. SourceF6defaultOFF/native and completeoriginalconditionsremainopen. Retained project C, all-file/default behavior, matching native/deployment/application/lifecycle and original whole-milestone conditions remain explicit; no duplicate credit or artifact-only C retirement.'}
qp=out/'QUALIFICATION.json';qp.write_text(json.dumps(qual,indent=2,sort_keys=True)+'\n')
for p in [cp,rp,oc,qp]:print(json.dumps(fact(p),sort_keys=True))
print(json.dumps({'image':result['image'],'map':result['map'],'entry':hex(final['header']['entry']),'arch_start_bytes':arch['final']['bytes'],'four_entries':[(x['symbol'],x['physical_owner']['final']['bytes']) for x in selection_rows],'input_joins':len(joined),'linker_joins':len(assign),'imports':len(imports),'unique_imports':len({x['import']['name'] for x in imports}),'remaining_C_FUNC_rows':remaining,'C_delta':result['C_ledger_delta'],'changed_objects':result['changed_constituent_bytes'],'new_import_names':[(x['consumer_object'],x['import']['name']) for x in result['new_import_edges']]},sort_keys=True))

# Changed f8 inputs and first actual reader only. No producer or kernel entry.
term_contract_path=root.parent/'terminate-default-ownership-1/correction-1/CONTRACT.json'
term_contract=json.loads(term_contract_path.read_text())
provider_path=Path(term_contract['provider_edges']['path']);provider_contract=json.loads(provider_path.read_text())
actual44={}
for edge in provider_contract['source_named_edges']:
 name=edge['source_named_edge'];p=owner_by_name[name]
 assert p['owner']['object']==edge['owner_object']=='rust/mckernel_rust.o' and p['final']['type']==edge['final']['type']
 if p['final']['type']=='FUNC':assert p['final']['bytes']>0
 if p['final']['type']=='OBJECT':assert p['final']['bytes']==edge['final']['bytes']
 actual44[name]={'actual_physical_owner':p,'source_type_contract':edge['source_type_contract']}
assert len(actual44)==44
archobj='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o';archunit=next(x for x in unitrows if x['object']==archobj)
assert archunit['runtime_FUNC_rows']==archunit['global_definitions']==archunit['weak_definitions']==archunit['allocated_executable_section_bytes']==0
oldarch=next(x for x in old['unit_summary'] if x['object']==archobj);assert archunit['identity']['sha256']==oldarch['identity']['sha256']
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
descriptors={'terminate':static_records('TERMINATE_DEBUG','f03_terminate',3,'terminate',[5271,5292,5511]),'exit_group':static_records('EXIT_GROUP_DEBUG','f03_exit_group',1,'exit_group_log_bridge',[5682])}

# Reuse unchanged F06 code/data checks by exact new object bytes and relocation;
# no prior XRSTOR disassembly or hardware operation is repeated.
old_f6_path=root/'next-credential-f06-1/f06-successor-1/qualification-1/F06-CHANGED-PATH-JOINS.json';old_f6=json.loads(old_f6_path.read_text())
dc=owner_by_name['debug_constants'];db,do,dsec=symbol_bytes(rustpath,ru,dc['owner']['input']);df,dfo,dfsec=symbol_bytes(imagepath,final,dc['final'])
assert dc['owner']['object']=='rust/mckernel_rust.o' and dc['final']['type']=='OBJECT' and dc['final']['bytes']==96 and dsec['align']>=32 and dc['final']['value']%32==0 and dsec['flags']&1 and dfsec['flags']&1
debug_words=list(struct.unpack('<12Q',db));assert db==df and debug_words==old_f6['debug_constants']['exact_12_u64_words']
x=owner_by_name['arch_rt_sigreturn_xrstor_bridge'];xb,xo,xsec=symbol_bytes(rustpath,ru,x['owner']['input']);xf,xfo,xfsec=symbol_bytes(imagepath,final,x['final']);assert xb.hex()==old_f6['XSAVE_XRSTOR']['input_code_hex'] and len(xb)==29
xr=relocs_for(x['owner']['input']);assert len(xr)==1 and xr[0]['input_offset']==6 and xr[0]['addend']==0 and xr[0]['input_target']['name']=='x86_cpu_xsave_mask'
assert xf[:6]==xb[:6] and xf[14:]==xb[14:] and struct.unpack('<Q',xf[6:14])[0]==owner_by_name['x86_cpu_xsave_mask']['final']['value']
retained_f6={'unchanged_source_reviewed_proof':fact(old_f6_path),'arch_C_exact_unchanged_object':archunit['identity'],'arch_C_zero_functions_globals_exec':True,'compiler_note_classification_reused':old_f6['arch_C_allocated_section_classification'],'current_Rust_debug_constants_owner':dc,'current_debug_constants_words':debug_words,'current_input_final_debug_bytes_equal':True,'current_XRSTOR_owner':x,'unchanged_XRSTOR_input_code_hex':xb.hex(),'actual_current_relocation':xr[0],'current_final_immediate_matches_mask_owner':True,'repeated_disassembly_test_or_hardware_call':False}

changed_relocs={row['symbol']:{'actual_owner':row['physical_owner'],'source_ABI':row['ABI'],'actual_relocations':relocs_for(row['physical_owner']['owner']['input'])} for row in selection_rows}
assert not any(e['input_target']['name'] in ('terminate_mcexec','terminate_mcexec_do_syscall_bridge') for e in changed_relocs['terminate']['actual_relocations'])
for n in ('exit_group_log_bridge','exit_group_terminate_bridge','exit_group_current_pid_bridge'):assert owner_by_name[n]['owner']['object']=='rust/mckernel_rust.o'
blocks={}
for short,name in [('log','exit_group_log_bridge'),('terminate','exit_group_terminate_bridge'),('pid','exit_group_current_pid_bridge')]:
 p=meta/('exit-group-'+short+'-disassembly.stdout');text=p.read_text();match=re.search(r'^0+[0-9a-f]* <'+re.escape(name)+r'>:\n([\s\S]*?)(?=\nDisassembly of section|\Z)',text,re.M);assert match,name
 blocks[short]={'record':fact(p),'function':name,'actual_physical_owner':owner_by_name[name],'actual_disassembly':match[0],'actual_relocations':changed_relocs[name]['actual_relocations']}
for text in ['cmp    $0x1000000,%eax','jae','mov    %edi,%esi','xor    %eax,%eax','kprintf']:assert text in blocks['log']['actual_disassembly'],text
for text in ['R_X86_64_64\tterminate','jmp    *%rax']:assert text in blocks['terminate']['actual_disassembly'],text
for text in ['$0xc0000101,%ecx','rdmsr','%gs:0x0,%eax','$0x1fc0,%rax,%rax','0x1ea8(%rcx,%rax,1),%rax','0x10d0(%rax),%rax','0x1c8(%rax),%eax']:assert text in blocks['pid']['actual_disassembly'],text
blocks['log']['source_instruction_join']='Volatile32-bit line_flags load, unsigned >=0x01000000 accepts any upper8flag; original signedCintPID EDI→ESI, correct vararg AL0 and tail-call realRustkprintf. No formatter executed.'
blocks['terminate']['source_instruction_join']='No status/group argument register writes: incoming EDI/ESI low32 forwarded unchanged through actualR64 relocation/tail-jump to unique newRustterminate; source ABI void(CInt,CInt).'
blocks['pid']['source_instruction_join']='Actual originalCLS path reads GSBASE/MSR then GSindex, real locals/num_processors/clv Rustdata; stride8128,current7848,Thread.proc4304,Process.pid456 and finalEAX32 match current realABI. PrivilegedRDMSR/GS code was only passively disassembled, never HOST invoked.'
new_cfgs={'f03_terminate_candidate','f03_exit_group_bridges_candidate'};baseline_cmds=json.loads((root/'next-credential-f06-1/f06-successor-1/qualification-1/ACTUAL-RUST-AND-C-COMMANDS.json').read_text());assert set(cfg)==set(baseline_cmds['Rust_cfg'])|new_cfgs
assert 'MCKERNEL_TERMINATE_C_FILE=/src/kernel/syscall.c' in argv
for rel in ['f03_terminate.rs','f03_exit_group.rs']:assert '/src/kernel/rust/'+rel in deps
assert all('-D'+name in shlex.split(compiled[0]['command']['command']) for name in ('MCKERNEL_RUST_F03_TERMINATE','MCKERNEL_RUST_F03_EXIT_GROUP_BRIDGES'))
source_review_path=root.parent/'terminate-default-review-publicabi-max-1/compiler-correction-1/REVIEW.json';source_review=json.loads(source_review_path.read_text())
type_contract_path=Path(source_review['type_ABI']['path']);type_contract=json.loads(type_contract_path.read_text())
assert binding['source_correction_patch']['sha256']=='a70481e62e82cf06cc52eb88f8c4d72d23c1426df868758dc50546e34a78bc24'
assert 'SPINLOCK_IN_MCS_RWLOCK' in generic_source and 'MCKERNEL_RUST_F03_TERMINATE' in generic_source
offsets=term_contract['unsafe_ownership_and_ABI']['new_paired_C_Rust_offset_assertions'];assert sum(len(x) for x in offsets.values())==18
changed={'schema':'m14-f8cf-terminate-exit-actual-changed-path-qualification-v1','status':'PASS_REAL_CORRECTED_RUST_TERMINATE_EXIT_ABI_DEBUG_AND_PROVIDER_OWNERSHIP','runtime_source_commit':binding['source_commit'],'actual_four_Rust_entries':selection_rows,'actual18paired_field_assertions_source_contract':offsets,'actual_selected_generic_C_command':compiled[0]['command'],'actual_Rust_command':fact(rp),'nominal_lock_boundary':{'source_correction_review':fact(source_review_path),'actual_type_ABI_contract':fact(type_contract_path),'representation_pointer_semantics_proof':source_review['representation_and_pointer_proof'],'new_real_compiler_C_Rust_guard_scope':source_review['new_assertions_and_real_next_check'],'actual_new_whole_Rust_and_generic_C_compile_exit':0,'original26E0308_result':binding['failed_operation'],'first_reader_was_previously_unstarted':True,'source_assertions_do_not_grant_native_lifetime_acceptance':True},'actual44source_named_provider_joins':actual44,'source_named_edge_reference':fact(provider_path),'source_named44_is_not_object_import_count':True,'changed_four_function_relocation_joins':changed_relocs,'debug_descriptors':descriptors,'targeted_exit_lowering':blocks,'retained_prior10_Rust_entries':retained_ten,'retained_F06_data_encoding_and_zeroarchC':retained_f6,'original_failed78_preserved':binding['failed_operation'],'original_source_body_ABI_reviews_reused':[fact(root.parent/'terminate-default-review-publicabi-max-1/REVIEW.json'),fact(root.parent/'terminate-default-review-publicabi-max-1/correction-1/REVIEW.json'),fact(root.parent/'exit-group-bridge-review-p04tests-max-1/REVIEW.json')],'new_body_fixture_or_source_audit':False,'native_program_or_hardware_execution_by_qualifier':False,'original_acceptance':False}
changed_path=out/'TERMINATE-EXIT-CHANGED-PATH-JOINS.json';changed_path.write_text(json.dumps(changed,indent=2,sort_keys=True)+'\n')
result['changed_terminate_exit_path_qualification']=fact(changed_path);result['retained_prior10_Rust_entries']=retained_ten;cp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
cond=json.loads(oc.read_text());cond['schema']='m14-f8cf-corrected-terminate-exit-original-condition-mapping-v1';cond['E1_E2_decision']='Actualf8 correctednormal full-image/ABI/provider/ownership closure passes once. OriginalwholeM14-I02E1/E2 remain OPEN:33 genericprojectC functions/data and completeall-file/default/capability/native conditions are not accepted by this build. SourceF6defaultOFF with explicitcacheON remains distinct.';cond['clean_build_scope']='Original78 attempt failed26E0308, preserved. One independentlyreviewed nominal-layout correction f8 retried only normalnamedimage; succeededthen firstunstartedreader. OnlygenericC/wholeRust bytes changed againstc664,9units equal; no partial injection/oldbodyfixture/readbackreplay.';cond['current_actual_qualification']=fact(cp)
for row in cond['rows']:
 row['actual_scope']='Actualf8 image0f7525a7, fourRustterminate/exitentries+Cexclusions/18+lockABIguards/44typedproviders/4debugrecords+targetlowering, prior10Rust/F6data/zeroarchC retained, allglobal/import providers/noUND. Generic33C remains; sourceF6defaultOFF/cacheON, no native.'
 if row.get('parent')=='M14-I02':row['exact_remaining_condition']=cond['E1_E2_decision']
 elif row.get('parent')=='M14-I01' and row['decision']!='PRIOR_VERIFIED_SCOPE_REUSED_NOT_REOPENED':row['exact_remaining_condition']='Four complete terminate/exit-groupprojectC definitions are genuinely replaced in currentselectedimage; actual33 genericC function rows plus data and original completeproject/header/macro/default ownership remain. AcceptedfourM14 scopes stayclosed.'
 elif row['id'] in ('M14-03-04-DEFAULT','M14-03-05-DEFAULT','M14-F03-DEFAULT'):
  row['decision']='CHANGED_TERMINATE_EXIT_SOURCE_ABI_OWNERSHIP_PASS_WHOLE_ORIGINAL_CONDITION_OPEN';row['exact_remaining_condition']='This exact correctedsource/compiler/image proves uniqueRustterminate andthreeexitentries, actualtype/debug/provider/lowerings andnoCcounterparts. The original whole-region/file condition still includes other livegenericC/requiredimplementations and applicable original matchingbehavior/native conditions; no source/count-only or four-entry acceptance is inferred. Reuse unchanged priorproofs; no invented fixture quota.'
oc.write_text(json.dumps(cond,indent=2,sort_keys=True)+'\n')
qual=json.loads(qp.read_text());qual['schema']='m14-f8cf-actual-corrected-terminate-exit-image-qualification-v1';qual['changed_terminate_exit_proof']=fact(changed_path);qual['physical_provider_closure']['data']=fact(cp);qual['original_whole_conditions']=fact(oc);qual['whole_I02_E1_E2_decision']=cond['E1_E2_decision'];qual['corrected_compiler_family']={'failed_original78':binding['failed_operation'],'independent_source_GO62307':fact(source_review_path),'bounded_source_delta':binding['source_exact_delta'],'actual_Rust_C_target_compile_pass':True,'no_original_failure_erased':True,'no_unchanged_retry':True};qual['qualification_method']=fact(out/'qualify_saved_image.py');qual['lifecycle']['actual_client_count_scope']='18 explicit clientreceipts inRESULT; no duplicate count of containerwait clients. Root reported unifiedouter session53253 fullyJOINED separately; no extra two client rows invented.';qual['operations_by_qualifier']='Only positively joined saved-byte/source/JSON parsing and private result writes. No compiler/build/readelf/objdump/counter/bodyfixture/container/privilegedRDMSR/GS/kernel/native/program/subprocess action.';qual['scope_limit']='Genuine correctedRustTerminate/exit default-source selections/realC+RustABI/provider/image/debug/lowering proof only. Prior10Rust/F6zeroarchC preserved. Generic33C, sourceF6defaultOFF, original completefile/default/matchedbehavior/native/lifecycle acceptance remain separate.';qp.write_text(json.dumps(qual,indent=2,sort_keys=True)+'\n')
print('FINAL_CHANGED_PATH_FREEZE')
for p in [qp,changed_path,cp,oc,rp]:print(json.dumps(fact(p),sort_keys=True))
print(json.dumps({'image':result['image'],'map':result['map'],'Rust':next(x['identity'] for x in unitrows if x['object']=='rust/mckernel_rust.o'),'four_Rust_entries':[(x['symbol'],x['physical_owner']['final']['bytes']) for x in selection_rows],'C_FUNC_rows':remaining,'inputglobals':len(joined),'scriptglobals':len(assign),'imports':len(imports),'uniqueimports':len({x['import']['name'] for x in imports}),'provider_source_edges':len(actual44),'entry':hex(final['header']['entry']),'actual_Rust_tokens':len(argv),'actual_Rust_cfgs':len(cfg),'changed_objects':result['changed_constituent_bytes']},sort_keys=True))

