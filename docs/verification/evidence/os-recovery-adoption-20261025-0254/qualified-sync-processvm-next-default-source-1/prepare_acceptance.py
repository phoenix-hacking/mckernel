"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepublish exact current-object/source expectations and reuse accepted observers.
"""
from pathlib import Path
import ast,copy,hashlib,json,struct
D=Path(__file__).resolve().parent;E=D.parent;B=E/'ROOT-NEXT10-DEFAULT-BUILD-ADMISSION-1';S=E/'next10-validator-report-ref-correction-1';A=S/'actual-qualification-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def once(text,old,new):
 assert text.count(old)==1,(old[:140],text.count(old));return text.replace(old,new,1)
raw=(E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py').read_bytes();assert hashlib.sha256(raw).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
ns={'struct':struct};exec(compile(ast.Module(body=[n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf'],type_ignores=[]),'accepted metadata-only parser','exec'),ns);Elf=ns['_ReuseElf']
P=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text());old=json.loads((S/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text());plan=json.loads((D/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json').read_text());receipt=E/'NEXT10-DEFAULT-INDEPENDENT-ARTIFACT-AND-POSTJOIN-ACCEPTANCE.json';assert ref(receipt)['sha256']=='b9edb7a5c8cf9355cab4defa1fc1fbd8713f22ee91e77cd91c021e273d24d483'
carry=[x['name'] for x in json.loads((A/'NEXT-PROVIDERS-RESULT.json').read_text())['phases']['actual_thirty_three_Rust_exports']];assert len(carry)==33
new=['sync_child_event','do_process_vm_read_writev'];all_exports=carry+new;assert len(set(all_exports))==35
remove3=['sync_child_event'];remove6=['arch_process_vm_rw_'+name+'_bridge' for name in ['memcpy','phys_to_virt','page_fault','vtop','release_vm','hold_vm','update_unlock','update_lock','process_unlock','find_process','lookup_range','read_unlock','read_lock']]+['do_process_vm_read_writev']
baseline={};expected={}
for token,removed in [('CMakeFiles/mckernel.img.dir/syscall.c.o',remove3),('CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o',remove6)]:
 path=B/'OUTPUT/work/output/build/kernel'/token;elf=Elf(path);functions={r['name']:r for r in elf.symbols if r['type']==2 and 0<r['shndx']<len(elf.sections) and elf.sections[r['shndx']]['flags']&2};assert set(removed)<=set(functions)
 baseline[token]=dict(object=ref(path),allocated_FUNC_count=len(functions),all_names=sorted(functions),selected_metadata=[functions[n] for n in removed]);expected[token]=dict(remove=removed,expected_remaining_names=sorted(set(functions)-set(removed)),unexplained_compiler_elisions_allowed=[])
assert [v['allocated_FUNC_count'] for v in baseline.values()]==[76,45]
undefined={line.split(None,1)[1] for line in (A/'production-rust-undefined.nm').read_text().splitlines()};assert set(new)<=undefined
# Exact HOST-qualified new Rust-owned metadata; these bytes and declarations
# must survive production compilation and final linking. No runtime-page claim.
F3=Path(plan['qualified_F03_actual']['path']).parent;obj=F3/'output-PENDING-ROOT/sync_child.o';host=Elf(obj);storage={}
for name in ['f03_sync_child_offsets_v1','f03_sync_child_attr_Rust_ABI_v1','f03_sync_child_Rust_inherit_pattern_v1']:
 values=[s for s in host.symbols if s['name']==name and s['shndx']!=0];assert len(values)==1;v=values[0];sec=host.sections[v['shndx']];assert v['bind']==1 and v['type']==1 and sec['flags']&2 and not sec['flags']&5
 storage[name]=dict(size=v['size'],alignment=sec['align'],bytes_hex=host.raw[sec['offset']+v['value']:sec['offset']+v['value']+v['size']].hex(),HOST_symbol=v,HOST_section=sec)
assert [x['size'] for x in storage.values()]==[64,32,104]
x=copy.deepcopy(old);x.update(status='STATIC_SYNC_PROCESSVM_ACCEPTANCE_FROZEN_BEFORE_COMPILER_NOT_ACCEPTANCE',source_plan=ref(D/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json'),profile_template=ref(D/'PROFILE.SOURCE-ONLY.json'),prior_accepted_artifact=ref(receipt),prior_accepted_producer=ref(B/'OUTPUT/work/evidence/producer-contract.json'),prior_first_compiler_epoch=json.loads((B/'OUTPUT/work/evidence/producer-contract.json').read_text())['commands'][0]['started_at_epoch'],all_Rust_exports=all_exports,carried_forward_Rust_exports=carry,new_unique_Rust_exports=new,direct_existing_Rust_exports=[],baseline_C_objects=baseline,expected_C_function_sets=expected,expected_new_undefined=sorted(undefined-set(new)),baseline_undefined=ref(A/'production-rust-undefined.nm'),exact_undefined_delta=dict(removed=new,added=[],all_other_provider_witnesses_exact=True),cumulative_seed_undefined_removed=sorted(set(old['cumulative_seed_undefined_removed'])|{'do_process_vm_read_writev'}),cumulative_seed_undefined_added=['f03_do_exit_debug_v2'],genuine_C_providers_retained=[dict(name='f03_do_exit_debug_v2',type=1,size=64)],new_Rust_readonly_storage=storage,new_storage_HOST_object=ref(obj),body_reuse='Two newly selected public Rust exports; existing orchestration, thirteen adapters, logger and offset bodies reused. Fifteen C FUNC removals are expected selection deltas, never new-algorithm counts or accepted retirement.',existing_completed_base_gate_sources={n:ref(S/'validator-templates'/n) for n in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_actual_image_suffix.py','qualify_next_providers.py','qualify_retained_f02_owners.py','profile_clone_witness.py','narrow_f02_alias_identity.py']})
x['warning_policy'].update(baseline_Rust_count=141,baseline_Rust_stderr=ref(B/'OUTPUT/work/evidence/00.stderr'),baseline_kernel_C_stderr=ref(B/'OUTPUT/work/evidence/01.stderr'),baseline_arch_C_stderr=ref(B/'OUTPUT/work/evidence/02.stderr'),baseline_ld_stderr=ref(B/'OUTPUT/work/evidence/03.stderr'),prior_exact_typed_pointer_warning_disposition=ref(receipt),new_Rust_warning_count=None,new_warning_disposition='Retain prior141 warning debt, including the exact fixed-x86 pointer declaration disposition. Capture actual added/removed headers; only source-bound unused imports or independently disposed exact declarations qualify. Unknown new categories block. No suppression/casts/recompile.',new_ld_warning_must_equal=(B/'OUTPUT/work/evidence/03.stderr').read_text())
x['source_config_holds']+=plan['holds'];save('ACCEPTANCE-INPUTS.SOURCE-ONLY.json',x)
# Reuse corrected accepted gates, adapting only finite cohort data and adding
# the exact three new immutable data objects to the existing provider observer.
T=D/'validator-templates';T.mkdir(mode=0o700);templates={}
for p in (S/'validator-templates').iterdir():
 if p.suffix!='.py':continue
 text=p.read_text().replace(str(E/'qualified-next-ten-selector-default-source-1/ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),str(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'))
 if p.name=='qualify_actual_f02_profile.py':text=once(text,"NEXT_ADDED={'sync_child_event', 'f03_do_exit_debug_v2'}","NEXT_ADDED=set(EXPECTED['cumulative_seed_undefined_added'])")
 if p.name=='qualify_next_providers.py':
  text=once(text,"for name,type_,size in [('f03_do_exit_debug_v2',1,64),('sync_child_event',2,None)]:","for item in EXPECTED['genuine_C_providers_retained']:\n  name,type_,size=item['name'],item['type'],item['size']")
  needle=" # Current producer selected only the frozen cfgs, preserving genuine undefined NOCACHE."
  addition=''' # Exact new Rust immutable data providers, bound to the genuine-header HOST witness.
 host_ref=EXPECTED['new_storage_HOST_object'];assert ref(Path(host_ref['path']))==host_ref
 data=ns['data'];object_bytes=ns['ns']['_reuse_elf_object_bytes'];storage={}
 for name,witness in EXPECTED['new_Rust_readonly_storage'].items():
  rows=definitions(rust,name);assert len(rows)==1;(a,)=rows;sec=rust.sections[a['shndx']]
  assert a['bind']==1 and a['type']==1 and a['size']==witness['size'] and sec['align']>=witness['alignment'] and a['value']%witness['alignment']==0
  assert sec['flags']&2 and not sec['flags']&5, 'new immutable metadata section must be allocated/read-only/non-executable'
  assert object_bytes(rust,a).hex()==witness['bytes_hex']
  assert not [(key,s) for key,elf in C.items() for s in definitions(elf,name)]
  b=final(name);assert (b['bind'],b['type'],b['size'])==(1,1,witness['size']) and b['value']%witness['alignment']==0
  assert sections[b['shndx']]['flags']&2 and not sections[b['shndx']]['flags']&5
  assert data(b).hex()==witness['bytes_hex'];storage[name]=dict(Rust_symbol=a,final_symbol=b,exact_HOST_bytes=True,unique_Rust_provider=True)
 report['phases']['new_Rust_immutable_metadata']=storage
'''
  text=once(text,needle,addition+needle);text=text.replace('actual_thirty_three_Rust_exports','actual_thirty_five_Rust_exports').replace('TEN_SELECTOR_33_RUST_EXPORTS','SYNC_PROCESSVM_35_RUST_EXPORTS')
 if p.name=='qualify_retained_f02_owners.py':text=text.replace('nine_RO_objects_exact=True','eight_RO_objects_exact=True')
 ast.parse(text,filename=p.name);(T/p.name).write_text(text)
 if p.name not in ['profile_clone_witness.py','narrow_f02_alias_identity.py']:templates[p.name]=dict(parent=ref(p),template_sha256=hashlib.sha256(text.encode()).hexdigest())
save('VALIDATOR-TEMPLATE-SOURCES.json',dict(scope=__doc__.splitlines()[0],status='STATIC_CORRECTED_ACCEPTED_GATE_REUSE_WITH_EXACT_SYNC_PROCESSVM_INPUTS',runtime_authority=None,templates=templates,unchanged_helpers={n:ref(T/n) for n in ['profile_clone_witness.py','narrow_f02_alias_identity.py']}))
driver=(S/'qualify_produced_cohort.py').read_text().replace('actual_thirty_three_Rust_exports','actual_thirty_five_Rust_exports').replace('TEN_SELECTOR','SYNC_PROCESSVM');ast.parse(driver);(D/'qualify_produced_cohort.py').write_text(driver)
reader=(B/'check_postbuild_current.py').read_text().replace('PASS_NEXT10_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION','PASS_SYNC_PROCESSVM_DEFAULT_BUILD_POSTJOIN_CURRENT_PHYSICAL_OBSERVATION');ast.parse(reader);(D/'check_postbuild_current.py').write_text(reader)
save('POSTJOIN-READER-PREPARATION.SOURCE-ONLY.json',dict(scope=__doc__.splitlines()[0],status='PREPARED_DATA_ONLY_SAME_ACCEPTED_POSTJOIN_OBSERVER_NOT_EXECUTED',parent=ref(B/'check_postbuild_current.py'),prepared=ref(D/'check_postbuild_current.py'),implementation_delta='Result status literal only; same exact ten data substitutions from actual new Root metadata; guard statements/queries/probes/mount floors unchanged',Root_copy_byteexact_to_future_admission=True,Root_save_actual_holder_tool_as='ROOT-ACTUAL-HOLDER-TOOL-RESULT.json',actual_admission=None,nonce=None,holder=None,CID=None,physical_acceptance=False))
request=dict(scope=__doc__.splitlines()[0],status='STATIC_QUALIFIED_SYNC_PROCESSVM_SOURCE_PROFILE_ACCEPTANCE_NOT_GRANTED',runtime_authority=None,request_sha256=None,nonce=None,actual_Root_admission=None,current_native_clearance=None,resource_authority=None,execution_release=None,actual_producer=None,source_plan=ref(D/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),reuse=ref(D/'FROZEN-SYNC-PROCESSVM-EIGHT-OBJECT-REUSE-INPUTS.json'),Rust_closed_source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),prepublished_acceptance_inputs=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),frozen_validator_templates=ref(D/'VALIDATOR-TEMPLATE-SOURCES.json'),prepared_future_validator=ref(D/'qualify_produced_cohort.py'),prepared_postjoin_reader=ref(D/'check_postbuild_current.py'));save('REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json',request)
print(json.dumps(dict(status=x['status'],Rust_exports=35,new_public_exports=2,expected_C_counts=[len(z['expected_remaining_names']) for z in expected.values()],expected_U_removed=2,new_U=0,new_storage_sizes=[v['size'] for v in storage.values()],runtime_actions=0)))
