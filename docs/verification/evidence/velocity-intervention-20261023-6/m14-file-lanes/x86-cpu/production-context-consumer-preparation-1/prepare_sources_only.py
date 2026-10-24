"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source-only context production preparation."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;B=P.parent;S=P/'source';S.mkdir();O=P/'output-1'
OLD=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-cpu-log-next/production-consumer-preparation-1')
COR=OLD/'bounded-header-transport-correction-1'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def wr(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2);f.write('\n')
baseline=OLD/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json';br=json.loads(baseline.read_bytes())
proof=COR/'FINAL-ACTUAL-PRODUCTION-HANDOFF.json';assert pin(proof)['sha256']=='6ae4c5c6db9db6a75708a55d9a729288a10cec11e32272d58d37b5d7a1f6b77e'
assert len(br['source_inputs'])==78
inputs={}
for k,v in br['source_inputs'].items():
 canonical=pin(ROOT/k);assert canonical['sha256']==v['private']['sha256'],k
 src=B/'candidate'/k if k=='kernel/rust/x86_cpu_helpers.rs' else ROOT/k
 dst=S/k;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 inputs[k]=dict(canonical_before=canonical,accepted_CPUlog_baseline=v['private'],private=pin(dst),only_private_override=k=='kernel/rust/x86_cpu_helpers.rs')
assert inputs['kernel/rust/x86_cpu_helpers.rs']['private']['sha256']=='98914e1ff4d50c2f42ccbdeb1f4f338024b7a9a2143fbad2f59ebd6f6b50dd0b'
assert [k for k,v in inputs.items() if v['canonical_before']['sha256']!=v['private']['sha256']]==['kernel/rust/x86_cpu_helpers.rs']
rows=[[k,v['private']['sha256'],v['private']['bytes']] for k,v in inputs.items()];identity=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
nm=OLD/'actual-production-capture-1/01-current78-Rust-symbols/stdout';oldNM=[x.split() for x in nm.read_text().splitlines() if x.split()]
U={x[-1] for x in oldNM if len(x)>=2 and x[-2]=='U'};T={x[-1] for x in oldNM if len(x)>=2 and x[-2]=='T'}
target='x86_context_line_log_bridge';assert len(U)==584 and len(T)==3046 and target in U and target not in T
assert {'kprintf','__kprintf','x86_cpu_ulong_log_bridge'}<=T
expectedU=U-{target};expectedT=T|{target}
oracle=dict(scope=__doc__,status='EXPECTED_FROM_ACTUAL_EXACT_CURRENT78_CPU_LOGGER_BASELINE_ONLY',actual_CPUlog_proof=pin(proof),actual_Rust_NM=pin(nm),actual_Rust_symbol_receipt=pin(OLD/'ACTUAL-RUST-SYMBOL-RECEIPT.json'),actual_Rust_object_not_rehashed=json.loads(proof.read_bytes())['objects']['Rust_original_durable_not_rehashed'],baseline_other77_exact_currentcanonical=True,expected_U=sorted(expectedU),expected_U_count=583,U_removed=[target],U_added=[],all_prior_T=sorted(T),all_prior_T_count=3046,expected_T=sorted(expectedT),expected_T_count=3047,new_T=[target],source_scope='Privatecontext9891 only; stack/NMI drafts excluded. Existing __kprintf provider alreadyT, so new declaration adds no externalU.',current_merged_runtime_proof=False)
wr(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-CPU-LOGGER.json',oracle)
argv=br['argv'][:];argv[-2]='--emit=obj='+str(O/'mckernel_rust.o');argv[-1]=str(S/'kernel/rust/lib.rs')
assert len(argv)==48 and [i for i,(a,b) in enumerate(zip(argv,br['argv'])) if a!=b]==[46,47]
assert pin(Path(argv[6]))['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
r=dict(scope=__doc__,status='SEALED_CONTEXT_ONLY_CURRENT78_PRODUCTION_RUST_NOT_GRANTED_NOT_EXECUTED',argv=argv,compiler_sha256=br['compiler_sha256'],profile=br['profile'],source_count=78,source_identity_rows=rows,source_identity=identity,source_inputs=inputs,only_private_override='kernel/rust/x86_cpu_helpers.rs',cfg_count=4,CGU=1,closure_external_modules=2,accepted_profile_recipe=pin(baseline),accepted_profile_actual=pin(proof),argv_changed_indices=[46,47],exact_symbol_oracle=pin(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-CPU-LOGGER.json'),expected_U_delta=dict(before=584,after=583,removed=[target],added=[]),expected_T_delta=dict(before=3046,after=3047,added=[target],removed=[]),source_patch=pin(B/'PRIVATE-COMPLETE-CONTEXT-LOGGER.patch'),CPU_context_candidate=pin(B/'candidate/kernel/rust/x86_cpu_helpers.rs'),actual_context_leaf=pin(B/'ACTUAL-CONTEXT-READY-HANDOFF.json'),root_independent_context_review='Rootreports callback_reviewPASS12240pairs13commands; no duplicate review.',stack_formatter_included=False,NMI_frame_included=False,compiler_jobs=0,defaultGCC14_kernel_link_native=False)
wr(P/'EXACT-CURRENT78-CONTEXT-RUST.NOT-EXECUTED.json',r)
oldRemaining=COR/'EXECUTABLE-READY.REMAINING7.NOT-GRANTED.json';oc=json.loads(oldRemaining.read_bytes());closure=json.loads((COR/'EXACT-HEADER-CLOSURE-CORRECTION.json').read_bytes())
headers={};canonicalHeaders={}
for path,row in closure['new_header_closure'].items():
 p=Path(path)
 if p.is_relative_to(COR/'source'):
  rel=p.relative_to(COR/'source');src=ROOT/rel;dst=S/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);headers[str(dst)]=pin(dst);canonicalHeaders[str(rel)]=pin(src)
 else:headers[str(p)]=pin(p)
assert len(headers)==56
csrc=S/'arch/x86_64/kernel/cpu.c';csrc.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(B/'candidate/arch/x86_64/kernel/cpu.c',csrc);assert pin(csrc)['sha256']=='c779079fb6de66991c861c823dca06b2a9ceec16ac4c984995200b668d7e78ce'
cargv=oc['commands'][1]['argv'][:]
for i,a in enumerate(cargv):
 if a.startswith('-I'+str(COR/'source')+'/'):cargv[i]='-I'+str(S/Path(a[2:]).relative_to(COR/'source'))
cargv[cargv.index('-c')+1]=str(csrc);cargv[cargv.index('-o')+1]=str(O/'cpu.c.o')
abi=P/'actual-context-header-ABI.c';text=(B/'fixture/actual_header_selection.c').read_text()
text+='\n/* Exact unchanged C outer-lock provider signatures from current cpu.c. */\nextern unsigned long x86_kprintf_lock_bridge(void);\nextern void x86_kprintf_unlock_bridge(unsigned long);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_kprintf_lock_bridge),unsigned long(*)(void)),"outer lock ABI");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_kprintf_unlock_bridge),void(*)(unsigned long)),"outer unlock ABI");\n'
abi.write_text(text);shutil.copy2(B/'fixture/selected-body.inc',P/'selected-body.inc')
baseC=cargv[:];i=baseC.index('-o');del baseC[i:i+2];i=baseC.index('-c');del baseC[i:i+2]
commands=[dict(label='03-selected-complete-CPU-preprocess',argv=baseC+['-E',str(csrc)]),dict(label='04-real-context-header-and-outer-lock-ABI',argv=baseC+['-fsyntax-only',str(abi)]),dict(label='05-selected-complete-CPU-TU',argv=cargv),dict(label='06-selected-CPU-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'cpu.c.o')]),dict(label='07-actual-context-C-caller-relocations',argv=['/usr/bin/readelf','-rW',str(O/'cpu.c.o')]),dict(label='08-selected-CPU-ELF',argv=['/usr/bin/readelf','-SWs',str(O/'cpu.c.o')]),dict(label='09-complete-CPU-fullRust-partial-link',argv=['/usr/bin/ld','-r',str(O/'cpu.c.o'),str(O/'mckernel_rust.o'),'-o',str(O/'cpu-rust-partial.o')]),dict(label='10-partial-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'cpu-rust-partial.o')])]
for x in commands:x.update(cwd=str(O),purpose=__doc__+' '+x['label']+'; metadata/compile only, no target register/IRQ/formatter/native execution.')
callbacks=oc['expected_C_callback_providers']+['x86_kprintf_lock_bridge','x86_kprintf_unlock_bridge']
c=dict(scope=__doc__,status='SEALED_COMPLETE_CURRENT_SELECTED_GCC9_CPU_CONTEXT_CONSUMER_NOT_GRANTED_NOT_EXECUTED',accepted_GCC9_profile=pin(oldRemaining),accepted_actual_CPUlog=pin(proof),private_source=pin(csrc),canonical_preimage=pin(ROOT/'arch/x86_64/kernel/cpu.c'),actual_header_closure=headers,current_canonical_headers=canonicalHeaders,witness_header_count=56,witness_specific_dependency_graph=json.loads((B/'EXECUTABLE-READY.NOT-EXECUTED.json').read_bytes())['actual_witness_include_graph'],retained_kmsg_header_from_accepted_transport='kmsg.h retained in56union to preserveacceptedclosure; currentcontextwitness usesactualihk/debug.h includingbothproviders andcompiler/types dependencies.',ABI_witness=pin(abi),selected_declaration_source=pin(P/'selected-body.inc'),commands=commands,tools={t:pin(Path(t)) for t in [cargv[0],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld']},profile=br['profile'],Rust_recipe=pin(P/'EXACT-CURRENT78-CONTEXT-RUST.NOT-EXECUTED.json'),expected_C_target=dict(name=target,kind='U',no_C_definition=True),expected_real_C_target_caller='ihk_mc_print_user_context passes logger into actualRustx86_print_user_context_body_result; actualRustarch_show_interrupt_context resolvesnewRustlocalexportinternally.',expected_named_target_text_relocations=1,preserved_C_providers=callbacks,expected_data=oc['expected_data'],expected_partial_unique_T=[target,'x86_cpu_ulong_log_bridge','kprintf','__kprintf'],existing_Rust_context_caller_bodies_unchanged=True,actual_context_leaf=pin(B/'ACTUAL-CONTEXT-READY-HANDOFF.json'),C_debt='All remaining Chelpers/outerlockproviders and13memcallbacks remain explicitdebt. Only completecontextline logger replacement is in thissourcecohort.',current_Cmem_provider='NotrequiredforCPU-onlypartial; retainexistingunrelatedU, no extra8f7source/objectcopy.',stack_formatter_included=False,NMI_frame_included=False,compiler_jobs=0,exact_GCC14_defaultkernel_native=False)
wr(P/'EXACT-SELECTED-GCC9-CONTEXT-CPU.NOT-EXECUTED.json',c)
ready=dict(scope=__doc__,status='ONE_CONTEXT_ONLY_PRODUCTION_QUEUE_READY_NO_EXECUTION_GRANT',Rust_recipe=pin(P/'EXACT-CURRENT78-CONTEXT-RUST.NOT-EXECUTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-CONTEXT-CPU.NOT-EXECUTED.json'),exact_symbol_oracle=pin(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-CPU-LOGGER.json'),source_identity=identity,source_count=78,only_private_Rust_override='kernel/rust/x86_cpu_helpers.rs',private_C=pin(csrc),profile=br['profile'],compiler_sha256=r['compiler_sha256'],argv_count=48,cfg_count=4,CGU=1,externalmodules=2,header_count=56,command_count=11,commands=[dict(label='00-current78-context-Rust-compile',argv=argv),dict(label='01-current78-context-Rust-symbols',argv=['/usr/bin/nm','-g',str(O/'mckernel_rust.o')]),dict(label='02-current78-context-Rust-ELF',argv=['/usr/bin/readelf','--wide','--syms',str(O/'mckernel_rust.o')])]+commands,expected_U_count=583,expected_T_count=3047,expected_U_removed=[target],expected_U_added=[],all3046prior_T_preserved=True,pending_canonical_integrations=[],canonical_context_integration_not_prerequisite=True,stack_formatter_included=False,NMI_frame_included=False,actual_leaf_replayed=False,historical_evidence_copied_into_source=False,compiler_jobs=0,test_jobs=0,CPU_slots_held=0,canonical_sharedABI_CMake_P12_Git_writes=0,next_operation='RootexclusiveordinaryCPUgrant; same2GiBAS60CPU90+6FSIZE32MiBFD256core0/CGU1stack2MiB/nightly70eb4cfg/GCC9; fresh19GiB/7jobs/floors/fullgap. h990dict+registeredhandlers/directwholejoins. CompileRustonce/hashdurableobjectoncebeforeobservers; thenwholeCPU/witness/reloc/partial onlyifRustPASS. Stopfirstunexpectedfailure preserveallhistories.',current_combined_production_proof=None,defaultGCC14_finalkernel_link_native=False,source_prep_kmsg_prefix_failures_preserved=True)
wr(P/'PRODUCTION-CONTEXT-CONSUMER-READY.json',ready)
print(json.dumps({'ready':pin(P/'PRODUCTION-CONTEXT-CONSUMER-READY.json'),'Rust':ready['Rust_recipe'],'C':ready['C_recipe'],'source_identity':identity,'commands':11,'U':583,'T':3047,'jobs':0}))
