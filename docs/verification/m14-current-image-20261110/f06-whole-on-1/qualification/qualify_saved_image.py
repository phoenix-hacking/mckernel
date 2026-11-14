import collections,hashlib,json,re,struct
from pathlib import Path
root=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1');build=root/'output/build';meta=root/'next-credential-f06-1/f06-successor-1/metadata'
out=root/'next-credential-f06-1/f06-successor-1/qualification-1';assert out.is_dir()
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
link_argv=shlex.split((meta/'regenerated-link.txt').read_text());objects=[x for x in link_argv if x.endswith('.o')];assert objects==json.loads((root/'next-credential-f06-1/credential-only-1/qualification-1/ACTUAL-RUST-AND-C-COMMANDS.json').read_text())['actual_link_inputs']
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
q=root/'next-credential-f06-1/f06-successor-1';execution=json.loads((q/'execution-1/RESULT.json').read_text())
request=json.loads((q/'REQUEST.json').read_text());binding=json.loads((q/'SOURCE-BINDING.json').read_text())
old=json.loads((root/'next-credential-f06-1/credential-only-1/qualification-1/OWNER-PROVIDER-JOINS.json').read_text())
assert execution['source_commit']==binding['source_commit']=='1e64b165ff2a46e6ec7615e804b36c9a936172a8'
assert (q/'execution-1/source-commit.stdout').read_text().strip()==binding['source_commit']
assert (q/'execution-1/ihk-commit.stdout').read_text().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
assert execution['all_client_waits_streams_joined'] and not execution['remaining_owned_child_pids']
assert not execution['old_CPU0_UNKNOWN_released'] and not execution['original_acceptance']
assert all(c['exit']==0 and c['direct_wait_joined'] and c['streams_closed'] for c in execution['clients'])
assert len(execution['phases'])==3 and [p['phase'] for p in execution['phases']]==['configure','build','metadata']
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
assert fact(Path(binding['actual_changed_source']['path']))['sha256']==binding['after_sha256']=='32e44bf79e3058ad2b43b8ed530d606281143fa7217aebad1a194cc49ccdfd97'
assert binding['repository_whole_F06_default_OFF_unchanged']
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
selection_files={'do_signal':'kernel/rust/f06_signal_tail.rs','arch_ptrace_regset_log_bridge':'kernel/rust/f06_signal_ptrace_diagnostics.rs','arch_native_signal_bad_frame_bridge':'kernel/rust/f06_signal_ptrace_diagnostics.rs','arch_rt_sigreturn_xrstor_bridge':'kernel/rust/f06_rt_sigreturn_xrstor.rs'}
selections=[{'symbol':x['name'],'Rust_source':selection_files[x['name']],'Rust_cfg':x['selector'][0],'C_macro':x['selector'][1],'excluded_C_object':'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','source_ABI':x['ABI']} for x in f06_contract['four_owners']]
request['retained_current_four_Rust_entries']=['do_syscall','interrupt_syscall','terminate_host','arch_rt_sigreturn_context_bridge','do_setresuid','do_setresgid']
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
result['selected_F06_four_function_joins']=selection_rows

retained_six=[]
for name in request['retained_current_four_Rust_entries']:
 owner=owner_by_name[name];assert owner['owner']['object']=='rust/mckernel_rust.o' and owner['final']['type']=='FUNC'
 assert not any(s['name']==name and s['section_index']!=0 for obj,u in units.items() if not obj.startswith('rust/') for s in u['symbols'])
 retained_six.append(owner)
result['retained_six_current_Rust_entries']=retained_six
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
result['status']='PASS_ACTUAL1E64_F06_WHOLE_ON_RUST_AND_DATA_OWNERS_ARCH_C_EXCLUSION_COMPLETE_PHYSICAL_PROVIDERS'
result['source_commit']=binding['source_commit'];result['baseline_reference']=fact(root/'next-credential-f06-1/credential-only-1/qualification-1/OWNER-PROVIDER-JOINS.json')
result['stable_green20a_preservation']=fact(root/'stable-baselinea740-1/BASELINE.json')
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
assert next(p for p in execution['phases'] if p['phase']=='configure')['exit']==0
assert '[ 90%] Linking C executable mckernel.img' in log
assert any('rust/abi_checks.c.o' in s and '/usr/bin/cc ' in s for s in lines)
rustcommand={'schema':'m14-1e64-saved-production-whole-Rust-command-v1','source':fact(q/'execution-1/build-payload.stdout'),'line_1based':lineno,'literal_command':rustline,'argv':argv,'token_count':len(argv),'Rust_cfg':cfg,'Rust_cfg_count':len(cfg),'F06_C_compiler_pairs':compiled,'actual_link_argv':link_argv,'actual_link_inputs':objects,'new_driver_probe_or_configure_called_by_qualifier':False,'actual_regeneration_trigger':'Explicit meaningful one-option wholeON production configure completed0 before unchanged normal namedbuild'}
rp=out/'ACTUAL-RUST-AND-C-COMMANDS.json';rp.write_text(json.dumps(rustcommand,indent=2,sort_keys=True)+'\n')

cond=copy.deepcopy(json.loads((root/'next-credential-f06-1/credential-only-1/qualification-1/ORIGINAL-CONDITIONS.json').read_text()))
scope='Actual1e64 explicitwholeON normal production imagec66492d4, same IHK8d/configca251/Linux6.12/GCC14/nightly1.95; four new F06 Rust functions plus writable data/C exclusions and retained six prior Rust entries; all actual input/linker providers joined and no named UND. No native execution.'
remaining=sum(u['runtime_FUNC_rows'] for u in retainedC)
for row in cond['rows']:
 row['actual_scope']=scope
 if row['decision']=='PRIOR_VERIFIED_SCOPE_REUSED_NOT_REOPENED':continue
 if row.get('parent')=='M14-I02':row['exact_remaining_condition']='Physical normal whole-image build/provider closure now also passes for current1e64 after four reviewed F06 selections and writable data. The complete original all-file Rust/assembly cutover image/default/matching-module/capability condition remains open: '+str(remaining)+' actual project-C FUNC rows remain in F03/F06; this compilation-only cohort is not the final all-file native/deployed cohort. Reuse matching module/tool/ABI evidence; no absent algorithm, unspecified inventory or unchanged-build quota is asserted.'
 elif row.get('parent')=='M14-I01':row['exact_remaining_condition']='All actual current globals/imports physically join, and four F06 function entries and required data moved from C to genuine Rust. Remaining '+str(remaining)+' project-C function rows and complete original source/header/macro/semantic/default ownership obligations are not retired.'
 elif row.get('parent')=='M14-I03':row['exact_remaining_condition']='Current1e64 explicitwholeON image was compiled and passively read only. Matching co-boot/module-load/useful applications/process/mapping/thread/signal/native lifecycle and resource-restoration conditions remain unmatched on this artifact, subject to existing genuine source/native/current-free/ownership gates. Reuse only actually matching prior results; all UNKNOWNs stay held.'
 else:row['exact_remaining_condition']='This image proves the actual selected integration/ABI/provider closure of the four F06 functions plus writabledata in explicitwholeON profile. Whole original file/default Rust replacement behavior/provider/capability and any genuinely affected functional/native conditions remain open; current C functions are honestly retained. Accepted exact prior file scopes remain closed. No source-only, link-only or count-based original acceptance is inferred.'
cond['schema']='m14-1e64-explicit-F06-wholeON-original-whole-condition-mapping-v1'
cond['E1_E2_decision']='Physical complete image/provider build blocker remains RESOLVED for current1e64. Whole original M14-I02 E1/E2 remain NOT FULLY DEMONSTRATED: '+str(remaining)+' actual project-C FUNC rows remain plus original all-file/default/matching-capability/native conditions. Four F06 function/data ownership corrections do not by themselves accept either whole condition.'
cond['clean_build_scope']='Real normal changed-input CMake regeneration, genuineRust and ten C/ASM target compiles plus bare-ld final link passed once ona740 using existing cache. Actual per-object identity equality/changes against qualified594ac are recorded in the owner table. No injected partial object or unchanged build replay.'
cond['current_actual_qualification']=fact(cp);cond['baseline_original_text_mapping']=fact(root/'next-credential-f06-1/credential-only-1/qualification-1/ORIGINAL-CONDITIONS.json')
oc=out/'ORIGINAL-CONDITIONS.json';oc.write_text(json.dumps(cond,indent=2,sort_keys=True)+'\n')
memory=[]
for phase in execution['phases']:
 mp=q/'execution-1'/(phase['phase']+'-MEMORY.json');samples=json.loads(mp.read_text())['samples'];values=[int(x['memory.max_usage_in_bytes']) for x in samples]
 assert all(x['memory.failcnt']=='0' and 'oom_kill 0' in x['memory.oom_control'] for x in samples)
 memory.append({'phase':phase['phase'],'source':fact(mp),'retained_samples':len(samples),'observed_sampled_highwater_bytes':max(values) if values else None,'exact_terminal_whole_job_peak_proven':False,'scope':'Saved sampled cgroup v1 highwater before exit; actual nonOOM/cgroup limit and positive lifecycle proven independently.'})
qual={'schema':'m14-1e64-explicit-F06-wholeON-actual-image-qualification-v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_EXPLICIT_WHOLE_F06_RUST_FUNCTION_DATA_ABI_ARCH_C_ZERO_PHYSICAL_PROVIDER_CLOSURE','owner':'/root/p04_source_max saved-artifact qualification only; Root executor/publisher','source_commit':binding['source_commit'],'source_binding':fact(q/'SOURCE-BINDING.json'),'actual_execution':fact(q/'execution-1/RESULT.json'),'reviewed_operation':fact(q/'REQUEST.json'),'reviewed_operation_GO':fact(root.parent/'compute-image-operation-review-p03-max-1/f06-successor-1/REVIEW.json'),'actual_image':result['image'],'actual_map':result['map'],'actual_whole_Rust_object':next(x['identity'] for x in unitrows if x['object']=='rust/mckernel_rust.o'),'actual_constituent_identities':[x['identity'] for x in unitrows],'selected_F06_four_functions':selection_rows,'retained_six_current_Rust_entries':retained_six,'credential_pair_physical_alias':result['credential_pair_physical_alias'],'whole_Rust_and_C_commands':fact(rp),'ELF_layout':{'header':final['header'],'program_headers':final['program_headers'],'arch_start':arch,'notes':notes,'allocated_sections_fully_mapped':True,'no_INTERP_DYNAMIC_or_relocations':True,'origin_MAP_KERNEL_START':'0xfffffffffe800000','new_entry_or_size_not_required_to_equal_old':True},'physical_provider_closure':{'data':fact(cp),'input_global_physical_joins':len(joined),'linker_assignment_joins':len(assign),'all_global_final':len(fg),'strong_import_occurrences':sum(x['import']['binding']=='GLOBAL' for x in imports),'weak_import_occurrences':sum(x['import']['binding']=='WEAK' for x in imports),'unique_import_names':len({x['import']['name'] for x in imports}),'named_undefined':[],'mismatches':[],'new_import_edges':result['new_import_edges'],'removed_import_edges':result['removed_import_edges'],'type_proof_scope':'Every actual input/final symbol kind/size/section/offset is checked. Declared C/Rust ABI and exact supported layouts are supplied by independently reviewed six-file source and genuine C ABI checks target compiled successfully in this build. NOTYPE import names alone are not promoted into signature proof.'},'retained_C_runtime_debt':{'actual_runtime_FUNC_rows':remaining,'unit_rows':retainedC,'delta':result['C_ledger_delta'],'whole_original_C_retirement':False},'inert_C_inputs':[x for x in unitrows if x['language_class']=='C_or_included_C_header' and not x['allocated_executable_section_bytes']],'config_ABI':{'root_config_sha256':saved_identities['/work/output/build/config.h'],'IHK_config_sha256':saved_identities['/work/output/build/ihk/config.h'],'linker_sha256':saved_identities['/work/output/build/kernel/config/smp-x86.lds'],'cache_unchanged_from_green20a':fact(meta/'regenerated-CMakeCache.txt'),'repository_wholeF06_default_OFF':True,'explicit_candidate_cache_wholeF06_ON':True,'PROFILE_ON':True,'clone_zero_initializer_preserved':True,'IHK_HEAD':'8d288b8bd81b50cc3a3f814d949b89bf416a6ec7','unchanged_objects':result['unchanged_constituent_bytes'],'changed_objects':result['changed_constituent_bytes'],'genuine_C_ABI_assert_object_compiled':True},'metadata_records':metadata_records,'lifecycle':{'all_clients_positive_birth_wait_streams':all(x['exit']==0 and x['direct_wait_joined'] and x['streams_closed'] for x in execution['clients']),'actual_client_count':len(execution['clients']),'all_direct_waits_streams_closed':True,'no_owned_children_remain':True,'both_containers_0_nonOOM_Pid0_removed':True,'phases':execution['phases'],'terminal_records':terminal_records,'memory_sample_scope':memory,'old_CPU0_256MiB_job1_UNJOINED_released':False},'original_whole_conditions':fact(oc),'whole_I02_E1_E2_decision':cond['E1_E2_decision'],'stable_green20a_preserved':fact(root/'stable-baselinea740-1/BASELINE.json'),'operations_by_qualifier':'Only offline saved-byte/source/JSON parsing and private result writes. No compiler/build/configure/test/probe/readelf/container/image/native/program or child operation. All producer/reader actions are the already joined Root execution.','original_acceptance':False,'progress_changed_by_qualifier':False,'scope_limit':'Explicit wholeF06 opt-in image/real C ABI/physical providers and four new Rust functions plus writable data only; previous six Rust entries retained. Source defaultOFF/native and complete original conditions remain open. Retained project C, all-file/default behavior, matching native/deployment/application/lifecycle and original whole-milestone conditions remain explicit; no duplicate credit or artifact-only C retirement.'}
qp=out/'QUALIFICATION.json';qp.write_text(json.dumps(qual,indent=2,sort_keys=True)+'\n')
for p in [cp,rp,oc,qp]:print(json.dumps(fact(p),sort_keys=True))
print(json.dumps({'image':result['image'],'map':result['map'],'entry':hex(final['header']['entry']),'arch_start_bytes':arch['final']['bytes'],'four_entries':[(x['symbol'],x['physical_owner']['final']['bytes']) for x in selection_rows],'input_joins':len(joined),'linker_joins':len(assign),'imports':len(imports),'unique_imports':len({x['import']['name'] for x in imports}),'remaining_C_FUNC_rows':remaining,'C_delta':result['C_ledger_delta'],'changed_objects':result['changed_constituent_bytes'],'new_import_names':[(x['consumer_object'],x['import']['name']) for x in result['new_import_edges']]},sort_keys=True))

# Actual whole-F06 changed-path checks. These consume only the positively joined
# producer's saved records and the same exact hashed artifacts, never kernel code.
archobj='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'
archunit=next(x for x in unitrows if x['object']==archobj)
assert archunit['runtime_FUNC_rows']==0 and archunit['allocated_executable_section_bytes']==0
assert archunit['global_definitions']==archunit['weak_definitions']==0
assert not any(s['name'] and s['type']=='FUNC' and s['bytes'] and 0<s['section_index']<len(units[archobj]['sections']) and units[archobj]['sections'][s['section_index']]['flags']&2 for s in units[archobj]['symbols'])
old_arch_globals=next(x for x in old['unit_summary'] if x['object']==archobj)['global_definition_names']
assert set(old_arch_globals)=={'do_signal','arch_ptrace_regset_log_bridge','arch_native_signal_bad_frame_bridge','arch_rt_sigreturn_xrstor_bridge','debug_constants'}
for name in old_arch_globals:assert owner_by_name[name]['owner']['object']=='rust/mckernel_rust.o'

ru=units['rust/mckernel_rust.o'];imagepath=Path(result['image']['path']);rustpath=Path(ru['path'])
def symbol_bytes(p,unit,sym):
 sec=unit['sections'][sym['section_index']];off=sec['offset']+sym['value']-sec['address']
 assert sec['type']!=8 and sec['offset']<=off and off+sym['bytes']<=sec['offset']+sec['bytes']
 with p.open('rb') as f:f.seek(off);blob=f.read(sym['bytes'])
 assert len(blob)==sym['bytes'];return blob,off,sec
dc=owner_by_name['debug_constants'];ins=dc['owner']['input'];fs=dc['final']
assert ins['binding']==fs['binding']=='GLOBAL' and ins['type']==fs['type']=='OBJECT' and ins['bytes']==fs['bytes']==96
ib,ioff,isec=symbol_bytes(rustpath,ru,ins);fb,foff,fsec=symbol_bytes(imagepath,final,fs)
assert isec['flags']&1 and isec['flags']&2 and fsec['flags']&1 and fsec['flags']&2
assert isec['align']>=32 and ins['value']%32==0 and fs['value']%32==0
words=list(struct.unpack('<12Q',ib));assert words==list(struct.unpack('<12Q',fb))==f06_contract['required_data_owner']['selected20a_expected_words']
debug_join={'source_ABI':f06_contract['required_data_owner'],'physical_owner':dc,'input_section':isec,'final_section':fsec,'input_file_offset':ioff,'final_file_offset':foff,'input_and_final_bytes_hex':ib.hex(),'exact_12_u64_words':words,'size_bytes':96,'alignment_bytes':32,'writable_input_and_final':True,'offset0_field_layout_source_assertions':'repr(C,align(32)), only [usize;12] field at0; genuine CABI/profileff48 and actual12 compiler-evaluated words match source contract.'}

# Join observed XRSTOR bytes and the actual relocation to the complete mask.
x=owner_by_name['arch_rt_sigreturn_xrstor_bridge'];xb,xoff,xsec=symbol_bytes(rustpath,ru,x['owner']['input']);xfb,xfoff,xfsec=symbol_bytes(imagepath,final,x['final'])
assert len(xb)==29 and xb[:6]==bytes.fromhex('55 48 89 e5 48 b8') and xb[6:14]==bytes(8)
assert xb[14:]==bytes.fromhex('48 8b 00 48 89 c2 48 c1 ea 20 0f ae 2f 5d c3')
disasm_path=meta/'f06-xrstor-disassembly.stdout';disasm=disasm_path.read_text()
block=re.search(r'^0+[0-9a-f]* <arch_rt_sigreturn_xrstor_bridge>:\n([\s\S]*?)(?=\nDisassembly of section|\Z)',disasm,re.M);assert block
for text in ['R_X86_64_64\tx86_cpu_xsave_mask','mov    (%rax),%rax','mov    %rax,%rdx','shr    $0x20,%rdx','xrstor (%rdi)']:assert text in block[0],text
maskowner=owner_by_name['x86_cpu_xsave_mask'];assert maskowner['owner']['object']=='rust/mckernel_rust.o' and maskowner['final']['type']=='OBJECT' and maskowner['final']['bytes']==8
raw=rustpath.read_bytes();function_relocs=[]
for sec in ru['sections']:
 if sec['type']!=4 or sec['info']!=x['owner']['input']['section_index']:continue
 assert sec['entry_bytes']==24
 for off in range(sec['offset'],sec['offset']+sec['bytes'],24):
  ro,ri,ra=struct.unpack_from('<QQq',raw,off);target=ru['symbols'][ri>>32]
  function_relocs.append({'offset':ro,'observed_ELF64_relocation_type':ri&0xffffffff,'addend':ra,'symbol':target})
assert len(function_relocs)==1 and function_relocs[0]['offset']==6 and function_relocs[0]['addend']==0 and function_relocs[0]['symbol']['name']=='x86_cpu_xsave_mask'
assert xfb[:6]==xb[:6] and xfb[14:]==xb[14:] and struct.unpack('<Q',xfb[6:14])[0]==maskowner['final']['value']
xrstor_join={'physical_owner':x,'saved_disassembly':fact(disasm_path),'exact_function_disassembly':block[0],'input_code_hex':xb.hex(),'final_code_hex':xfb.hex(),'input_file_offset':xoff,'final_file_offset':xfoff,'actual_relocation':function_relocs[0],'tool_decoded_relocation':'R_X86_64_64','full_mask_provider':maskowner,'instruction_contract':'Incoming snapshot pointer remains RDI (no instruction writes it). Load actual64-bit x86_cpu_xsave_mask into RAX; copy to RDX, shift right32 for EDX while EAX retains low32; XRSTOR(%rdi). Input imm64 relocation and final patched provider address agree. Only passive encoding/source ABI proof; no hardware restore/snapshot-extent/native acceptance.'}

# Record every relocation of the changed public function sections, distinguishing
# compiler-local Rust section references from real external ABI/provider edges.
changed_function_relocs=[]
for entry in selection_rows:
 owner=entry['physical_owner'];sym=owner['owner']['input'];edges=[]
 for sec in ru['sections']:
  if sec['type']!=4 or sec['info']!=sym['section_index']:continue
  assert sec['entry_bytes']==24
  for off in range(sec['offset'],sec['offset']+sec['bytes'],24):
   ro,ri,ra=struct.unpack_from('<QQq',raw,off)
   if not sym['value']<=ro<sym['value']+sym['bytes']:continue
   target=ru['symbols'][ri>>32];edge={'consumer_input_offset':ro,'observed_relocation_type':ri&0xffffffff,'addend':ra,'input_target':target}
   if target['binding'] in ('GLOBAL','WEAK'):
    edge['physical_provider']=owner_by_name.get(target['name']) or script_by_name.get(target['name']);assert edge['physical_provider'],target
    edge['scope']='Actual global physical provider; source79d066/d866 gives the genuine ABI/lifetime signature, not NOTYPE name-only inference.'
   else:
    assert 0<target['section_index']<len(ru['sections']),target
    edge['scope']='Compiler-local definition or section inside the exact wholeRust object; no external provider substitution.';edge['local_Rust_section']=ru['sections'][target['section_index']]
   edges.append(edge)
 changed_function_relocs.append({'function':entry['symbol'],'source_ABI':entry['source_ABI'],'physical_owner':owner,'actual_relocation_edges':edges})
assert not any(x['import']['name'].startswith(('__atomic','__sync')) for x in imports)
terminate=owner_by_name['terminate'];assert terminate['owner']['object']=='CMakeFiles/mckernel.img.dir/syscall.c.o' and terminate['final']['type']=='FUNC'
cfg_before=json.loads((root/'next-credential-f06-1/credential-only-1/qualification-1/ACTUAL-RUST-AND-C-COMMANDS.json').read_text())['Rust_cfg'];assert set(cfg)==set(cfg_before)|set(f06_contract['selector_closure']['whole_added_cfgs'])
arch_compile=next(x for x in commands if x['file']=='/src/arch/x86_64/kernel/syscall.c' and 'CMakeFiles/mckernel.img.dir/' in x['command']);arch_argv=shlex.split(arch_compile['command'])
for name in f06_contract['selector_closure']['C_definitions']:assert arch_argv.count('-D'+name)==1,name
before_cache=(root/'next-credential-f06-1/credential-only-1/metadata/regenerated-CMakeCache.txt').read_text()
cache_annotation_deltas=[('//ASM compiler\nCMAKE_ASM_COMPILER:STRING=/usr/bin/cc','//No help, variable specified on the command line.\nCMAKE_ASM_COMPILER:UNINITIALIZED=/usr/bin/cc'),('//C compiler\nCMAKE_C_COMPILER:STRING=/usr/bin/cc','//No help, variable specified on the command line.\nCMAKE_C_COMPILER:UNINITIALIZED=/usr/bin/cc'),('//Path to a program.\nCMAKE_LINKER:FILEPATH=/usr/bin/ld','//No help, variable specified on the command line.\nCMAKE_LINKER:UNINITIALIZED=/usr/bin/ld')]
expected_cache=before_cache
for before,after in cache_annotation_deltas:
 assert expected_cache.count(before)==1;expected_cache=expected_cache.replace(before,after,1)
assert cache==expected_cache.replace('ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=OFF','ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=ON',1)
assert 'MCKERNEL_F06_SIGNAL_METADATA_RS=/work/output/build/kernel/rust/f06-origin/f06_signal_metadata.rs' in argv
assert '/work/output/build/kernel/rust/f06-origin/f06_signal_metadata.rs' in deps
for rel in ['f06_rt_sigreturn_xrstor.rs','f06_signal_tail.rs','f06_signal_ptrace_diagnostics.rs','f06_signal_trap_info.rs']:assert '/src/kernel/rust/'+rel in deps
sigmeta=json.loads((meta/'f06-signal-metadata.json').read_text());origin=json.loads((meta/'f06-origin-binding.json').read_text())
assert sigmeta['source_sha256']==origin['source_sha256']=='4f6ea41af837748aae2d9581c7c45963c5cd5367093c8aebb1e62b12f75994ca' and sigmeta['origin']=='/src/arch/x86_64/kernel/syscall.c'
for name,value in sigmeta['sites'].items():assert re.search(r'\b'+re.escape(name)+r'\s*:\s*[^=]+\s*=\s*'+str(value)+r'\s*;', (meta/'f06-signal-metadata.rs').read_text()),name
postgate_path=q/'execution-1/CONFIGURE-POSTGATE.json';postgate=json.loads(postgate_path.read_text())
assert postgate['explicit_whole_F06_ON'] and postgate['repository_default_not_promoted'] and postgate['generated_compiler_linker_MAP_agree'] and postgate['generated_compute_IHK_F06_records_nonempty']
assert postgate['genuine_driver_ko_bytes']==145296 and postgate['driver_ko_sha256']=='712f062a26e5c7db4d656021f62bd6b94cca3b09a926f3e8476cc93d44f45794' and postgate['supported_MAP_KERNEL_START']=='0xfffffffffe800000'
assert fact(meta/'regenerated-CMakeCache.txt')['sha256']==postgate['cache_sha256']
changed={'schema':'m14-F06-1e64-actual-changed-path-data-ABI-encoding-joins-v1','status':'PASS_EXPLICIT_WHOLE_ON_ARCH_RUST_FUNCTION_DATA_AND_ENCODING_PROOF','functions':selection_rows,'function_relocation_joins':changed_function_relocs,'arch_C_object':archunit,'arch_C_allocated_sections':[s for s in units[archobj]['sections'] if s['flags']&2 and s['bytes']],'old_arch_five_global_definitions_now_Rust':old_arch_globals,'debug_constants':debug_join,'XSAVE_XRSTOR':xrstor_join,'retained_six_Rust_entries':retained_six,'real_retained_project_C_terminate':terminate,'terminate_ABI':'Source-reviewed void terminate(int,int), not noreturn; original return/error path is retained. This actual projectC body remains migration debt.','no_atomic_hostruntime_import':True,'F06_source_contract':fact(f06_contract_path),'source_GO':fact(root.parent/'f06-remaining-ownership-review-publicabi-max-1/REVIEW.json'),'actual_two_counter_tests_qualification':fact(root.parent/'f06-remaining-ownership-review-publicabi-max-1/actual-tests-1/RESULT.json'),'configure_postgate':fact(postgate_path),'whole_metadata_records':[fact(meta/n) for n in ['f06-origin-binding.json','f06-signal-metadata.json','f06-signal-metadata.rs']],'profile_delta':'Only explicit existingcache wholeF06 OFF→ON; actual83cfgs are baseline77unionsevenwhole (contextalreadyselected), all7 Cmacro pairs once, real signal metadata env/deps; source defaultOFF unchanged.','original_acceptance':False,'native_or_hardware_executed':False}
changed_path=out/'F06-CHANGED-PATH-JOINS.json';changed_path.write_text(json.dumps(changed,indent=2,sort_keys=True)+'\n')
result['F06_changed_path_qualification']=fact(changed_path);result['arch_C_no_allocated_executable_or_function_or_global_implementation']=True
cp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
cond=json.loads(oc.read_text());cond['schema']='m14-1e64-explicit-F06-wholeON-original-condition-mapping-v1'
cond['E1_E2_decision']='Physical source/config/image/provider build closure passes for actual1e64 explicitwholeON. Original whole M14-I02 E1/E2 remain OPEN: 37 actual generic projectC FUNC rows remain and sourcewholeF06 defaultOFF/native/all-file/matching-capability requirements are not accepted by this opt-in compilation.'
cond['clean_build_scope']='One meaningful explicitOFF→ON productionconfigure, normal incremental namedimage and passive metadata passed once. Source1e64 contains exact reviewed atomic fix32e44; source defaultOFF preserved. Nine constituent byte hashes equal qualifieda740, onlyarchC and wholeRust changed; zero partial injection.'
cond['current_actual_qualification']=fact(cp)
for row in cond['rows']:
 row['actual_scope']='Actual1e64 explicitwholeF06ON imagec66492d4; actual4newF06Rust FUNCs+96B writabledata, zeroarchC runtime, retained6Rust entries, all physical providers/imports/noUND; generic37C functions remain, source defaultOFF, no native execution.'
 if row['id'] in ('M14-06-02-DEFAULT','M14-06-03-DEFAULT','M14-F06-DEFAULT'):
  row['decision']='EXPLICIT_ON_SOURCE_CODEGEN_ABI_OWNERSHIP_PASS_WHOLE_ORIGINAL_DEFAULT_CONDITION_OPEN';row['exact_remaining_condition']='This matched explicitwholeON build now genuinely selects complete source-reviewed F06 paths/functions/data and excludes archC implementation. Repository source default is stillOFF; no default promotion/complete supported functional/native condition is claimed. Root must assess the exact original default/capability/behavior condition and any necessary future reviewed default change, reusing this unchanged ownership/ABI/encoding/body evidence rather than rerunning it.'
 elif row.get('parent')=='M14-I02':row['exact_remaining_condition']=cond['E1_E2_decision']
 elif row.get('parent')=='M14-I01' and row['decision']!='PRIOR_VERIFIED_SCOPE_REUSED_NOT_REOPENED':row['exact_remaining_condition']='Current explicitwholeON has no live archC and all global/import providers physically join, but37 genericC function rows plus original complete per-header/macro/semantic project ownership/default requirements remain open.'
oc.write_text(json.dumps(cond,indent=2,sort_keys=True)+'\n')
qual=json.loads(qp.read_text());qual['F06_changed_path_proof']=fact(changed_path);qual['physical_provider_closure']['data']=fact(cp);qual['original_whole_conditions']=fact(oc);qual['whole_I02_E1_E2_decision']=cond['E1_E2_decision'];qual['explicit_whole_ON_vs_default_scope']={'candidate_cache_ON':True,'repository_source_default_OFF':True,'default_promotion':False,'native_hardware_or_API_execution':False};qual['config_ABI']['exact_cache_only_ONE_option_delta']=True;qual['config_ABI']['actual_configure_postgate']=fact(postgate_path);qual['metadata_records']=metadata_records;qual['stable_current_a740_baseline']=fact(root/'stable-baselinea740-1/BASELINE.json');qual.pop('stable_green20a_preserved',None)
qual['retained_C_runtime_debt']['arch_C_runtime_zero']=True;qual['qualification_method']=fact(out/'qualify_saved_image.py');qual['operations_by_qualifier']='Offline positively joined saved-artifact/source/JSON parsing and private result writes only; no producer/configure/build/test/readelf/objdump/container/native/hardware/program or subprocess operation. Root actual3phase execution is reused.'
qp.write_text(json.dumps(qual,indent=2,sort_keys=True)+'\n')
print('FINAL_CHANGED_PATH_FREEZE')
for p in [changed_path,cp,oc,qp,rp]:print(json.dumps(fact(p),sort_keys=True))
print(json.dumps({'image':result['image'],'map':result['map'],'Rust_object':next(u['identity'] for u in unitrows if u['object']=='rust/mckernel_rust.o'),'C_FUNC_rows':remaining,'input_globals':len(joined),'script_globals':len(assign),'strong_imports':sum(x['import']['binding']=='GLOBAL' for x in imports),'unique_imports':len({x['import']['name'] for x in imports}),'selected_functions':[(x['symbol'],x['physical_owner']['final']['bytes']) for x in selection_rows],'debug_words':words,'XRSTOR_bytes':len(xb),'entry':hex(final['header']['entry']),'unchanged_objects':len(result['unchanged_constituent_bytes']),'actual_Rust_argv_tokens':len(argv),'actual_Rust_cfgs':len(cfg)},sort_keys=True))
