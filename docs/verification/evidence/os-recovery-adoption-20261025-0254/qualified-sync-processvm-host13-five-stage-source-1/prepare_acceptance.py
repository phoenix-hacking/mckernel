"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed-five data/index bindings over the already prepared accepted observer bodies.
"""
from pathlib import Path
import ast,copy,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;Q=E/'qualified-sync-processvm-next-default-source-1';F=E/'f02-source38-next-current-integration-source-1';B=E/'ROOT-NEXT10-DEFAULT-BUILD-ADMISSION-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def once(s,a,b):
 assert s.count(a)==1,(a[:140],s.count(a));return s.replace(a,b,1)
implementation=read(F/'SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json');x=read(Q/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json');P=read(D/'PROFILE.SOURCE-ONLY.json');names=[r['name'] for r in implementation['data_records']]
assert len(set(names))==13 and set(names)<=set(x['expected_new_undefined'])
x.update(status='STATIC_SYNC_PROCESSVM_HOST13_FIVE_STAGE_ACCEPTANCE_BEFORE_COMPILER',source_plan=ref(D/'COHERENT-COMBINED-SOURCE-PLAN.NOT-GRANTED.json'),profile_template=ref(D/'PROFILE.SOURCE-ONLY.json'),retained_objects=7,new_objects=4,commands=5,HOST13_actual=ref(F/'ACTUAL-HOST13-HANDOFF.json'),HOST13_implementation=ref(F/'SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json'),process_baseline_object=implementation['current_process_object'],process_baseline_OBJECT_count=84,process_expected_OBJECT_count=71,process_expected_FUNC_count=0,HOST13_records=implementation['data_records'],process_remaining71_metadata=ref(F/'REMAINING71-METADATA-OPEN.json'),expected_new_undefined=sorted(set(x['expected_new_undefined'])-set(names)),exact_undefined_delta=dict(removed=x['exact_undefined_delta']['removed']+names,added=[],all_other_provider_witnesses_exact=True),cumulative_seed_undefined_removed=sorted(set(x['cumulative_seed_undefined_removed'])|set(names)),actual_final_consumer13_bindings=None,HOST13_default_retirement=False)
x['warning_policy']['baseline_process_C_stderr']=ref(E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/OUTPUT/work/evidence/01.stderr');save('ACCEPTANCE-INPUTS.SOURCE-ONLY.json',x)
x['HOST13_production_consumer_map']={r['name']:r['Rust_consumer']['name'] for r in implementation['data_records']}
# Existing private free_pages is inlined into this exact public entry in the
# accepted F42 object. Its current relocation to this data record is unique.
x['HOST13_production_consumer_map']['process_free_range_pages_source_line']='process_memory_range_free_bridge'
x['HOST13_one_inline_context']=dict(data='process_free_range_pages_source_line',source_consumer='remaining_free_range_entry::free_pages',production_owner='process_memory_range_free_bridge',source_evidence='Exact unchanged current entry passes Some(free_pages); actual F42 data relocation at1185 is owned by process_memory_range_free_bridge. No other inline-name substitution is allowed.',current_Rust_object=ref(B/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o'))
# Keep the owner-provided ELF storage reader and its source manifest exact.
for name in ['check_thirteen_storage.py','SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json']:(D/name).write_bytes((F/name).read_bytes())
T=D/'validator-templates';T.mkdir(mode=0o700,exist_ok=True);templates={}
for p in (Q/'validator-templates').iterdir():
 if p.suffix!='.py':continue
 s=p.read_text().replace(str(Q/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),str(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'))
 if p.name=='qualify_clone_pointer_and_warning_suffix.py':
  old="Path(next(r['source']['path'] for r in P['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o'))";assert s.count(old)==2;s=s.replace(old,"B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o'")
  s=once(s,"[(1,'kernel','baseline_kernel_C_stderr'),(2,'arch','baseline_arch_C_stderr')]","[(1,'process','baseline_process_C_stderr'),(2,'kernel','baseline_kernel_C_stderr'),(3,'arch','baseline_arch_C_stderr')]")
  s=once(s,"ld=(A/'03.stderr').read_text()","ld=(A/'04.stderr').read_text()")
  s=s.replace('matching_F02_process_not_recompiled=True','changed_HOST13_process_recompiled=True').replace('no_C_or_nine_input_duplicate_clone_or_storage_definitions=True','no_C_or_seven_retained_input_duplicate_clone_or_storage_definitions=True')
 if p.name=='qualify_actual_f02_profile.py':
  s=once(s,"['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']","['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']")
  s=once(s,"process=Elf(HostPath(next(r['source']['path'] for r in P['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')))","process=Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')")
  s=s.replace('PASS_EXACT_FOUR_ARGV_AND_FRESH_OUTPUT_IDENTITIES','PASS_EXACT_FIVE_ARGV_AND_FRESH_OUTPUT_IDENTITIES')
 if p.name=='qualify_actual_image_suffix.py':s=s.replace('eight_RO_input_resolution','seven_RO_input_resolution').replace('AND_EIGHT_EXACT_ORIGINAL_AND_QUALIFIED_F02_OBJECT_REFS','AND_SEVEN_EXACT_ORIGINAL_OBJECT_REFS')
 if p.name=='qualify_next_providers.py':
  s=once(s,"assert P['unchanged_completed_process_prefix']['Root_decision']=='REUSE_EXACT_F02_B8168C1F'","assert P['unchanged_completed_process_prefix']['Root_decision']=='RECOMPILE_CHANGED_PROCESS_SOURCE_ACTUAL_HOST13_QUALIFIED'")
  s=s.replace('source_view_and_eight_prefix_inputs','source_view_and_seven_prefix_inputs').replace('AND_EIGHT_RETAINED_OBJECTS','AND_SEVEN_RETAINED_OBJECTS')
 if p.name=='qualify_retained_f02_owners.py':
  marker="FOUR=['idle_halt','allow_oversubscribe','time_sharing','process_idle_callbacks']"
  s=once(s,marker,"EXPECTED=json.loads(Path("+repr(str(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'))+").read_text())\n"+marker+"\nTHIRTEEN=[r['name'] for r in EXPECTED['HOST13_records']]")
  s=once(s,'assert len(oldmeta)==88 and len(newmeta)==84','assert len(oldmeta)==88 and len(newmeta)==71')
  s=once(s,'assert set(oldmeta)-set(newmeta)==set(FOUR) and not set(newmeta)-set(oldmeta)','assert set(oldmeta)-set(newmeta)==set(FOUR+THIRTEEN) and not set(newmeta)-set(oldmeta)')
  s=s.replace('eight_RO_objects_exact=True','seven_RO_objects_exact=True').replace('new_allocated_OBJECTs=84,only_removed_objects=FOUR,all_84_binding_type_size_initial_bytes_and_relocations_preserved=True','new_allocated_OBJECTs=71,only_removed_objects=FOUR+THIRTEEN,all_71_binding_type_size_initial_bytes_and_relocations_preserved=True').replace('84_PROCESS_METADATA','71_PROCESS_METADATA')
  s=once(s," # Actual fixed LP64 C/Rust source assertions and constructor signatures."," # Current b816 baseline is separately authenticated by the HOST13 gate;\n # all71 metadata names/bytes/RELA above also match the predecessor before F02.\n # This preserves46 mutable descriptor families/78 entries and25 other rodata.\n report['phases']['metadata_classification']=dict(mutable_Ddebug_families=46,descriptor_entries=78,other_readonly_objects=25,logical_line_file_and_relocation_semantics_preserved=True)\n # Actual fixed LP64 C/Rust source assertions and constructor signatures.")
 ast.parse(s,filename=p.name);(T/p.name).write_text(s)
 if p.name not in ['profile_clone_witness.py','narrow_f02_alias_identity.py']:templates[p.name]=dict(parent=ref(p),template_sha256=hashlib.sha256(s.encode()).hexdigest())
host13='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact13 immutable owners and real-consumer relocation or explicit folded-code gap.
"""
from pathlib import Path
import hashlib,importlib.util,json,struct
D=Path(__file__).resolve().parent
STATIC=Path(__STATIC__)
EXPECTED=json.loads((STATIC/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text())
s=(D/'qualify_clone_pointer_and_warning_suffix.py').read_text();ctx={'__file__':str(D/'qualify_host13_storage.py')};exec(compile(s[:s.index("\\nclone=ns['_reuse_elf_function']")],'accepted strict actual readers','exec'),ctx)
P=ctx['P'];B=ctx['B'];rust=ctx['rust'];process=ctx['process'];ref=ctx['ref'];final=ctx['final'];data=ctx['data'];rels=ctx['ns']['_reuse_elf_owning_relocations'];object_bytes=ctx['ns']['_reuse_elf_object_bytes'];Elf=ctx['Elf']
assert ref(Path(EXPECTED['process_baseline_object']['path']))==EXPECTED['process_baseline_object']
source=STATIC/'check_thirteen_storage.py';assert ref(source)==EXPECTED['HOST13_storage_reader']
spec=importlib.util.spec_from_file_location('unchanged_owner_HOST13_storage_reader',source);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
old=owner.Elf(EXPECTED['process_baseline_object']['path']);changed=owner.Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o');new=owner.Elf(B/'kernel/rust/mckernel_rust.o');image=owner.Elf(B/'kernel/mckernel.img')
C=[(r['link_token'],Elf(B/r['build_relative'] if r['replace'] else Path(r['source']['path']))) for r in P['inputs']['objects'] if r['link_token']!='rust/mckernel_rust.o']
rows=[];opened=[]
for record in EXPECTED['HOST13_records']:
 name,value=record['name'],record['value'];prior=old.readonly_int(name,value);assert not changed.definitions(name);a=new.readonly_int(name,value);b=image.readonly_int(name,value)
 assert not [(key,s) for key,elf in C for s in elf.symbols if s['name']==name and s['shndx']!=0]
 # A relocation must be owned by the named real current Rust consumer, not an
 # arbitrary allocated section. Constant folding is never silently accepted.
 consumer=EXPECTED['HOST13_production_consumer_map'][name];symbols=[s for s in rust.symbols if s['name']==consumer and s['shndx']!=0];assert len(symbols)==1 and symbols[0]['type']==2
 fn=symbols[0];f=final(consumer);owned=[r for r in rels(rust,fn) if r['target']['name']==name]
 if not owned:opened.append(dict(data=name,value=value,consumer=consumer,required='Independent exact current final argument-instruction proof of this value at its original controlled provider call; source/HOST parity alone is insufficient',object_code_hex=object_bytes(rust,fn).hex(),final_code_hex=data(f).hex()))
 rows.append(dict(data=name,value=value,baseline=prior,Rust=a,final=b,source_consumer=record['Rust_consumer']['name'],production_consumer=consumer,consumer_object_symbol=fn,consumer_final_symbol=f,exact_consumer_owned_relocations=owned))
report=dict(scope=__doc__.splitlines()[0],status='OPEN_STORAGE13_FINAL_CONSUMER_BINDINGS' if opened else 'PASS_STORAGE13_REAL_CONSUMER_RELOCATIONS_PENDING_INDEPENDENT_FINAL_MAP_REVIEW',records=rows,open_consumer_instruction_proofs=opened,baseline=EXPECTED['process_baseline_object'],new_process=ref(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o'),Rust=ref(B/'kernel/rust/mckernel_rust.o'),image=ref(B/'kernel/mckernel.img'),HOST13_actual=EXPECTED['HOST13_actual'],all13_readonly_CInt4_align4_exact_values_and_unique_Rust_owners=True,final_consumer_bindings_complete=not opened,independent_final_map_review=False,default_retirement=False,native_acceptance=False,Source38_GNU_RETAIN_hold='OPEN_UNCHANGED')
(D/'HOST13-STORAGE-AND-CONSUMERS.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(dict(status=report['status'],records=13,open_consumers=len(opened))))
'''.replace('__STATIC__',repr(str(D)))
ast.parse(host13);(T/'qualify_host13_storage.py').write_text(host13);templates['qualify_host13_storage.py']=dict(parent=ref(F/'check_thirteen_storage.py'),template_sha256=hashlib.sha256(host13.encode()).hexdigest())
x['HOST13_storage_reader']=ref(D/'check_thirteen_storage.py');save('ACCEPTANCE-INPUTS.SOURCE-ONLY.json',x)
save('VALIDATOR-TEMPLATE-SOURCES.json',dict(scope=__doc__.splitlines()[0],status='STATIC_EXACT_FIVE_STAGE_INDEX_MAP_AND_HOST13_READONLY_ACCEPTANCE',runtime_authority=None,templates=templates,unchanged_helpers={n:ref(T/n) for n in ['profile_clone_witness.py','narrow_f02_alias_identity.py']}))
s=(Q/'qualify_produced_cohort.py').read_text();s=once(s,"producer['status']=='ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER' and len(producer['commands'])==4","producer['status']=='ACTUAL_BUILD_ONLY_FIVE_COMMAND_PRODUCER' and len(producer['commands'])==5")
s=once(s,"'qualify_retained_f02_owners.py']:","'qualify_retained_f02_owners.py','qualify_host13_storage.py']:")
needle="  if report['warnings']['new_warning_disposition_required']:report['status']='PASS_REQUIRED_ARTIFACT_GATES_PENDING_EXACT_NEW_DECLARATION_WARNING_DISPOSITION'"
addition=needle+"\n  host13=json.loads((out/'HOST13-STORAGE-AND-CONSUMERS.json').read_text());report['HOST13_storage_and_consumers']=ref(out/'HOST13-STORAGE-AND-CONSUMERS.json');report['HOST13_final_consumer_bindings_complete']=host13['final_consumer_bindings_complete'];report['HOST13_default_retirement']=False\n  if not host13['final_consumer_bindings_complete']:report['status']='OPEN_CONSUMER13_BINDINGS_WITH_ALL_BASE_ARTIFACT_GATES_PASSED'"
s=once(s,needle,addition);s=s.replace('PASS_ACTUAL_SYNC_PROCESSVM_PRODUCER_ELF_PROVIDER_LINK_AND_RETAINED_DATA_GATES','PASS_FIVE_STAGE_SYNC_PROCESSVM_HOST13_BASE_GATES_PENDING_INDEPENDENT_FINAL_MAP_REVIEW');ast.parse(s);(D/'qualify_produced_cohort.py').write_text(s)
(D/'check_postbuild_current.py').write_text((Q/'check_postbuild_current.py').read_text().replace('PASS_SYNC_PROCESSVM_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION','PASS_SYNC_PROCESSVM_HOST13_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION'))
save('REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json',dict(scope=__doc__.splitlines()[0],status='STATIC_COMBINED_FIVE_STAGE_REQUEST_NOT_AUTHORITY',runtime_authority=None,request_sha256=None,nonce=None,actual_Root_admission=None,current_native_clearance=None,resource_authority=None,execution_release=None,actual_producer=None,source_plan=ref(D/'COHERENT-COMBINED-SOURCE-PLAN.NOT-GRANTED.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),reuse=ref(D/'FROZEN-FIVE-STAGE-SEVEN-OBJECT-REUSE-INPUTS.json'),source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),prepublished_acceptance=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),frozen_validators=ref(D/'VALIDATOR-TEMPLATE-SOURCES.json'),prepared_validator=ref(D/'qualify_produced_cohort.py'),prepared_postjoin=ref(D/'check_postbuild_current.py')))
print(json.dumps(dict(status=x['status'],expected_Rust_function_exports=35,new_data_providers=13,process_OBJECTs=[84,71],kernel_arch_FUNCs=[[76,75],[45,31]],expected_U_removed=len(x['exact_undefined_delta']['removed']),expected_U_added=0,actual_final_consumer13_bindings=None)))
