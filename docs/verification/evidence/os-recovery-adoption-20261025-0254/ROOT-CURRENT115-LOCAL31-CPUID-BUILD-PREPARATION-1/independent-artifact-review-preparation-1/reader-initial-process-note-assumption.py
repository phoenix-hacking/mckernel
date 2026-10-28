"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retained finite logger, folded arguments and actual process-empty-object readback.
"""
from pathlib import Path
import importlib.util,struct,re,subprocess,json
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current115_prefix',D/'review_actual115.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
globals().update({k:v for k,v in vars(m).items() if not k.startswith('__')})
def fn(e,name):
 s=own(e,name);assert s['type']==2 and e.sections[s['shndx']]['flags']&6==6;return s
img=image
source=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_inherited_core_current112.py';text=source.read_text();segment='q=E/'+text.split('q=E/',1)[1].split('\nmetadata=[]',1)[0]
exec(compile(segment,'unchanged accepted four LOCAL logger337B final-image reader','exec'),globals())
logger_records=records;logger_bindings=bindings;logger_other_targets=other_targets
core=read(auth(contract['accepted114_core']))
def disassemble(name):
 s=image.sym(name);return subprocess.check_output(['objdump','--no-show-raw-insn','-d','--start-address='+str(s['value']),'--stop-address='+str(s['value']+s['size']),str(image.path)],text=True)
cache={};folded=[]
for row in core['thirteen_folded_arguments']:
 value=row['signed_CInt'];reg=row['ABI_argument'];pattern=(r'push\s+\$0x%x\b'%value) if reg=='stack eighth' else r'mov\s+\$0x%x,%%%s\b'%(value,reg)
 if row['consumer'] not in cache:cache[row['consumer']]=disassemble(row['consumer'])
 instructions=[line.strip() for line in cache[row['consumer']].splitlines() if re.search(pattern,line)];assert len(instructions)==1,(row['consumer'],value,reg)
 folded.append({**row,'current_instruction':instructions[0]})
assert set(allocated(oldac,2))-set(allocated(ac,2))=={'obtain_clone_cpuid'} and not set(allocated(ac,2))-set(allocated(oldac,2))
assert not allocated(pc,1) and not allocated(pc,2)
active_sections=[s for s in pc.sections if s['flags']&2 and s['size']]
assert not active_sections,active_sections
abi=own(new,'arch_rt_sigreturn_syscall_bridge');assert abi['size']==17
rr=rels(new,abi);assert len(rr)==1 and rr[0]['target']['name']=='syscall' and rr[0]['addend']==0
raw=bytearray(data(new,abi));off=rr[0]['offset'];v=image.sym('syscall')['value'];struct.pack_into('<Q',raw,off,v);assert bytes(raw)==image.bytes(image.sym(abi['name']))
zero=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT115_SELECTED_PROCESS_C_ZERO_RUNTIME_FUNCTION_OBJECT_AND_ALLOCATED_BYTES',independent=True,reviewer='/root/current110_execution_review',actual_profile=ref(P/'PROFILE.SOURCE-ONLY.json'),actual_process_C_object=ref(pc.path),actual_four_command_join=ref(P/'ROOT-ACTUAL-TOOL-RESULT.json'),allocated_OBJECT_definitions=[],allocated_FUNCTION_definitions=[],nonempty_ALLOC_sections=active_sections,allocated_runtime_bytes=0,exact_previous31_C_OBJECTs_transferred_to_Rust=[r['name'] for r in contract['F02_target31']['internal_debug14']+contract['F02_target31']['configs3']+contract['F02_target31']['readonly14']],storage_final_image_proof=ref(D/'ACTUAL-STORAGE-REGISTRY-PRODUCER-PREFIX.json'),qualified_fields_and_current_folded_dataflow_proof=ref(D/'ACTUAL-PRLIMIT-DATA-FOLDED-WARNING-SUPPLEMENT.json'),native_or_wholefile_contract_evaluation=False,wholefile_contract_evaluator_must_assess_original_supported_config_and_native_requirements=True,runtime_authority=None)
zero_ref=save('ACTUAL-PROCESS-C-ZERO-RUNTIME-STORAGE.json',zero)
report=dict(scope=__doc__.splitlines()[0],decision='PASS_EXACT_CURRENT115_INHERITED_LOGGER_FOLDED_ARGUMENT_AND_SELECTED_C_REMOVAL_COMPLEMENT',independent=True,reviewer='/root/current110_execution_review',actual_Rust=ref(new.path),actual_image=ref(image.path),unchanged_logger_reader=ref(source),four_LOCAL_logger_records=logger_records,four_actual_logger_flag_consumers=logger_bindings,logger_other_exact_targets=logger_other_targets,logger337B_full_final_code_equal114=True,thirteen_current_folded_arguments=folded,C_function_removal_exactly_obtain_clone_cpuid=True,actual_process_zero_runtime=zero_ref,existing_syscall17B_full_final_ABI_reproduced=True,old_unrelated_seven_C_section_relative_deltas_remain_OPEN=True,native_acceptance=False,wholefile_retirement=False)
if __name__=='__main__':print(json.dumps(dict(proof=save('ACTUAL-INHERITED-LOGGER-ABI-COMPLEMENT.json',report),process_zero=zero_ref,decision=report['decision'])))
