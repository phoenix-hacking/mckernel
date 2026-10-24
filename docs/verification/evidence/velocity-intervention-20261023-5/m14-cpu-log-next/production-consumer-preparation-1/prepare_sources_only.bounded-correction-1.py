"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source/recipe preparation only; no compiler/test."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;B=P.parent;S=P/'source';S.mkdir(exist_ok=True);O=P/'output-1'
V5=B.parent
PB=V5/'m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1'
LB=V5/'m14-memory-l3-next/production-consumer-preparation-1'
CB=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-x86-cpu')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def wr(p,j):
 if p.exists():
  assert json.loads(p.read_bytes())==j,('immutable_prepared_JSON_changed',str(p));return
 with p.open('x') as f:json.dump(j,f,indent=2);f.write('\n')
def sy(p,k):return {a[-1] for l in p.read_text().splitlines() if (a:=l.split()) and len(a)>=2 and a[-2]==k}
pr=PB/'EXACT-CURRENT78-RUST-RECIPE.CORRECTED-NOT-GRANTED.json';pj=PB/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'
lr=LB/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json';lj=LB/'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json'
p=json.loads(pr.read_bytes());l=json.loads(lr.read_bytes())
assert pin(pj)['sha256']=='7a0191a235c29356ab48f25fd28e6e33b698ae1bd9a539ab84c795c52fc9993f'
assert pin(lj)['sha256']=='9c3665a24bff5c873055b1603204514fe07359885978c45a9a66c19ecd34df07'
assert pin(ROOT/'kernel/rust/process_helpers.rs')['sha256']=='d04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d'
assert pin(ROOT/'kernel/rust/x86_memory_helpers.rs')['sha256']=='245faf1198d9b7715714d236238172330257f4291776aced4e7cee6c3c518ce2'
assert set(p['source_inputs'])==set(l['source_inputs']) and len(p['source_inputs'])==78
def differences(recipe):
 return [k for k,v in recipe['source_inputs'].items() if pin(ROOT/k)['sha256']!=v['private']['sha256']]
assert differences(p)==['kernel/rust/x86_memory_helpers.rs']
assert differences(l)==['kernel/rust/process_helpers.rs']
inputs={}
for key in sorted(p['source_inputs']):
 canonical=pin(ROOT/key);src=B/'candidate'/key if key=='kernel/rust/x86_cpu_helpers.rs' else ROOT/key;dst=S/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 inputs[key]=dict(canonical_before=canonical,private=pin(dst),only_private_override=key=='kernel/rust/x86_cpu_helpers.rs',accepted_process_baseline=p['source_inputs'][key]['private'],accepted_L3_baseline=l['source_inputs'][key]['private'])
assert [k for k,v in inputs.items() if v['private']['sha256']!=v['canonical_before']['sha256']]==['kernel/rust/x86_cpu_helpers.rs']
assert inputs['kernel/rust/x86_cpu_helpers.rs']['private']['sha256']=='26180e00c1d6673aa600f0ec9afed5d100ca6e0c39af803c3328e58f8cc88fb9'
rows=[[k,v['private']['sha256'],v['private']['bytes']] for k,v in inputs.items()];identity=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
pn=PB/'actual-production-capture-1/01-current78-Rust-symbols/stdout';ln=LB/'actual-attempt-1/01-production-Rust-NM/stdout'
pU,pT=sy(pn,'U'),sy(pn,'T');lU,lT=sy(ln,'U'),sy(ln,'T')
assert len(pU)==577 and len(lU)==584 and len(pT)==len(lT)==3044
newL3={'x86_clear_l3_child_walk','x86_clear_l3_effect_log','x86_clear_l3_memobj_flush','x86_clear_l3_memobj_rss_sub','x86_clear_l3_range_log','x86_clear_l3_rss_sub','x86_clear_l3_use_1gb_page'}
assert lU-pU==newL3|{'vm_range_insert_log_bridge'} and pU-lU=={'process_vm_range_insert_debug'}
assert lT-pT=={'clear_range_l3'} and pT-lT=={'vm_range_insert_log_bridge'}
canonicalU=(pU|lU)-{'vm_range_insert_log_bridge'};priorT=pT|lT
target='x86_cpu_ulong_log_bridge';assert target not in canonicalU|priorT
expectedU=canonicalU;expectedT=priorT|{target};assert len(expectedU)==584 and len(priorT)==3045 and len(expectedT)==3046
proof=dict(scope=__doc__,status='EXPECTED_EXACT_SETS_DERIVED_FROM_TWO_ACCEPTED_DISJOINT_ACTUAL_SOURCE_COHORTS_NOT_COMBINED_COMPILE',accepted_process_recipe=pin(pr),accepted_process_actual=pin(pj),accepted_process_raw_NM=pin(pn),accepted_L3_recipe=pin(lr),accepted_L3_actual=pin(lj),accepted_L3_raw_NM=pin(ln),actual_L3_nine_binding_proof=pin(LB/'actual-attempt-1/ACTUAL-NINE-CALLBACK-DATA-RELOCATIONS.json'),current_process_root_actual_integration_notice='Root confirms actual874500f6 kernel/process.c08c238a0 +Rustprocessd04b48c8; observed exactcanonicalhashes verified beforefreeze.',current_process_C=pin(ROOT/'kernel/process.c'),current_process_Rust=pin(ROOT/'kernel/rust/process_helpers.rs'),current_L3_C=pin(ROOT/'arch/x86_64/kernel/memory.c'),current_L3_Rust=pin(ROOT/'kernel/rust/x86_memory_helpers.rs'),process_baseline_only_current_mismatch='kernel/rust/x86_memory_helpers.rs',L3_baseline_only_current_mismatch='kernel/rust/process_helpers.rs',raw_process_only_U=sorted(pU-lU),raw_L3_only_U=sorted(lU-pU),raw_process_only_T=sorted(pT-lT),raw_L3_only_T=sorted(lT-pT),L3_nine_relocations_are_not_nine_new_U=True,expected_current_canonical_U=sorted(canonicalU),expected_U=sorted(expectedU),expected_U_count=584,CPU_log_U_added=[],CPU_log_U_removed=[],all_prior_T=sorted(priorT),all_prior_T_count=3045,expected_new_T=[target],expected_T=sorted(expectedT),expected_T_count=3046,qualification='Disjoint source-bound actual symbol deltas predict exact current combined set. Nextactualcompiler only can prove combinedcurrentobject; no historicalobject relabeled current.')
wr(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json',proof)
cpuRecipe=CB/'production-consumer-preparation-1/EXACT-PRODUCTION-RUST-RECIPE.GRANTED-WHEN-READY.json'
cp=json.loads(cpuRecipe.read_bytes());argv=p['argv'][:]
assert argv[:-2]==cp['argv'][:-2] and len(argv)==48
argv[-2]='--emit=obj='+str(O/'mckernel_rust.o');argv[-1]=str(S/'kernel/rust/lib.rs')
assert pin(Path(argv[6]))['sha256']==p['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
r=dict(scope=__doc__,status='SEALED_CURRENT78_CPU_LOG_RECIPE_NOT_GRANTED_NOT_EXECUTED',argv=argv,compiler_sha256=p['compiler_sha256'],profile=p['profile'],source_count=78,source_inputs=inputs,source_identity_rows=rows,source_identity=identity,only_private_override='kernel/rust/x86_cpu_helpers.rs',accepted_F04_profile_recipe=pin(cpuRecipe),accepted_F04_actual_profile_proof=pin(CB/'production-consumer-preparation-1/FINAL-ACTUAL-PRODUCTION-HANDOFF.json'),profile_argv_changes_only_source_output_indices=[46,47],cfg_count=4,CGU=1,closure_external_modules=2,actual_CPU_log_leaf=pin(B/'ACTUAL-CPU-LOG-READY-HANDOFF.json'),source_patch=pin(B/'PRIVATE-CPU-ULONG-LOG.patch'),CPU_log_candidate=pin(B/'candidate/kernel/rust/x86_cpu_helpers.rs'),exact_symbol_oracle=pin(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json'),expected_U_delta=dict(before=584,after=584,added=[],removed=[]),expected_T_delta=dict(before=3045,after=3046,added=[target],removed=[]),pending_inputs=[],canonical_process_d04b_actual_root_notice_received=True,compiler_jobs=0,production_link_native=False)
wr(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json',r)
oldCommand=CB/'sourcehandoff/bounded-correction-1/actual-bounded-correction-capture-1/05-complete-selected-cpu-TU-compile/command.json'
cargv=json.loads(oldCommand.read_bytes())['argv'][:]
for i,a in enumerate(cargv):
 if a.startswith('-I'+str(ROOT)+'/'):cargv[i]='-I'+str(S/Path(a[2:]).relative_to(ROOT))
i=cargv.index('-c')+1;cargv[i]=str(S/'arch/x86_64/kernel/cpu.c');i=cargv.index('-o')+1;cargv[i]=str(O/'cpu.c.o')
dst=S/'arch/x86_64/kernel/cpu.c';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(B/'candidate/arch/x86_64/kernel/cpu.c',dst);assert pin(dst)['sha256']=='2d29bca555936a213f0a7296a302ec57b55c575536c33a58285b07b203390eca'
headerProfile=CB/'sourcehandoff/EXACT-ORDINARY-FIXTURE-AND-CONSUMER.NOT-GRANTED.json';hp=json.loads(headerProfile.read_bytes());headers={};canonicalHeaders={}
for path,row in hp['header_closure'].items():
 src=Path(path)
 if src.is_relative_to(ROOT):
  key=src.relative_to(ROOT);d=S/key;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,d);headers[str(d)]=pin(d);canonicalHeaders[str(key)]=pin(src)
 else:headers[str(src)]=pin(src)
assert len(headers)==55
abi=P/'actual-CPU-log-header-ABI.c';shutil.copy2(B/'fixture/actual_header_selection.c',abi);shutil.copy2(B/'fixture/selected-body.inc',P/'selected-body.inc')
base=cargv[:];i=base.index('-o');del base[i:i+2];i=base.index('-c');del base[i:i+2]
cmds=[dict(label='03-selected-complete-CPU-preprocess',argv=base+['-E',str(dst)]),dict(label='04-real-header-CPU-log-callback-ABI',argv=base+['-fsyntax-only',str(abi)]),dict(label='05-selected-complete-CPU-TU',argv=cargv),dict(label='06-selected-complete-CPU-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'cpu.c.o')]),dict(label='07-actual-default-CPU-log-relocations',argv=['/usr/bin/readelf','-rW',str(O/'cpu.c.o')]),dict(label='08-selected-complete-CPU-ELF',argv=['/usr/bin/readelf','-SWs',str(O/'cpu.c.o')]),dict(label='09-complete-CPU-fullRust-partial-link',argv=['/usr/bin/ld','-r',str(O/'cpu.c.o'),str(O/'mckernel_rust.o'),'-o',str(O/'cpu-rust-partial.o')]),dict(label='10-partial-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'cpu-rust-partial.o')])]
for x in cmds:x.update(cwd=str(O),purpose=__doc__+' '+x['label']+'; no CPU/MSR/IRQ/native instruction execution.')
oldC=json.loads((CB/'production-consumer-preparation-1/EXACT-REUSED-GCC9-CPU-CONSUMER.GRANTED-WHEN-READY.json').read_bytes())
c=dict(scope=__doc__,status='SEALED_COMPLETE_CURRENT_SELECTED_GCC9_CPU_TU_ABI_RELOC_FULLRUST_PARTIAL_NOT_GRANTED_NOT_EXECUTED',accepted_actual_compile_command=pin(oldCommand),accepted_F04_actual=pin(CB/'production-consumer-preparation-1/FINAL-ACTUAL-PRODUCTION-HANDOFF.json'),private_source=pin(dst),canonical_preimage=pin(ROOT/'arch/x86_64/kernel/cpu.c'),header_profile_derivation=pin(headerProfile),actual_header_closure=headers,current_canonical_headers=canonicalHeaders,ABI_witness=pin(abi),actual_selected_declaration_source=pin(P/'selected-body.inc'),commands=cmds,tools={t:pin(Path(t)) for t in [cargv[0],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld']},profile=p['profile'],Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),expected_C_target=dict(name=target,kind='U',no_C_definition=True),expected_C_callback_providers=oldC['expected_C_callback_providers'],expected_data=oldC['expected_data'],expected_real_C_callback_callers=['ihk_mc_init_ap','arch_save_panic_regs'],expected_named_target_relocations=2,expected_partial_unique_global_T=[target,'kprintf'],expected_prior_Rust_T=pin(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json'),C_debt='Existing F04 four C callbacks preserved; every other Cfunction unchanged. This slice retires only selectedCPU_ulong_log body after actuallink/native, not wholeCPUfile.',other_mem_C_callback_debt=13,current_mem_provider_reuse='Not required for CPU-only partial. Existing memimports remainqualified U; no stub/substitute or duplicated Cmemprovider added.',compiler_difference='Accepted ordinary GCC9 complete selected CPU TU; exact GCC14 finalkernel/native remainOPEN.',sourceonly=True,compiler_jobs=0)
wr(P/'EXACT-SELECTED-GCC9-CPU-CONSUMER.NOT-EXECUTED.json',c)
ready=dict(scope=__doc__,status='ROOT_READY_FROZEN_AFTER_ACTUAL_PROCESS_D04B_INTEGRATION_NO_COMPILER_GRANT',Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-CPU-CONSUMER.NOT-EXECUTED.json'),exact_expected_sets=pin(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-RAW.json'),source_count=78,source_identity=identity,header_count=55,only_private_Rust_override='kernel/rust/x86_cpu_helpers.rs',private_C=pin(dst),profile=p['profile'],compiler='Pinnednightly1.95 SHA70ebcbba; leafRust1.92 notproduction.',cfg=4,CGU=1,externalmodules=2,compiler_flags_unchanged_except_source_output_paths=True,command_count=11,commands=[dict(label='00-current78-Rust-compile',argv=argv),dict(label='01-current78-Rust-symbols',argv=['/usr/bin/nm','-g',str(O/'mckernel_rust.o')]),dict(label='02-current78-Rust-ELF',argv=['/usr/bin/readelf','--wide','--syms',str(O/'mckernel_rust.o')])]+cmds,expected_U_count=584,expected_U_added=[],expected_U_removed=[],expected_all3045prior_T_preserved=True,expected_new_T=target,expected_T_count=3046,pending_inputs=[],root_process_integration_notice='Actual874500f6 confirmed, currentd04b verified beforefreeze',actual_L3_9c_source_baseline_used=True,compiler_jobs=0,test_jobs=0,CPU_slots_held=0,canonical_mutations=0,frozen15_P12_mutations=0,next_operation='Rootexclusive ordinary CPUgrant then fresh19GiB/7jobs/floors/fullgap and exactsource/tool/profile preflight. Runoneactual48argvRustcompile,durableobjecthashoncebeforeNM/readelf; ifPASS run8preparedcompleteCPU/ABI/reloc/partialcommands. h990dict+preregisteredhandlers/directwholejoins; stopfirstunexpectedfailure preservehistory.',whole_current_combined_proof=False,defaultGCC14_finalkernel_link_native=False,variadic_leaf_not_formatter_execution_qualification_retained=True)
wr(P/'PRODUCTION-CONSUMER-READY.json',ready)
print(json.dumps({'ready':pin(P/'PRODUCTION-CONSUMER-READY.json'),'Rust':ready['Rust_recipe'],'C':ready['C_recipe'],'identity':identity,'U':584,'T':3046,'commands':11,'jobs':0}))
