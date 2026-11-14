"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source-only preparation; no compiler/test/runtime."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path('/home/holden/mckernel');B=Path(__file__).resolve().parent;P=B/'production-consumer-preparation-1';P.mkdir();S=P/'source';S.mkdir();O=P/'output-1'
V=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4')
PB=V/'m14-process-next/production-consumer-preparation-1/coherent-current78-refresh-1'
SB=V/'m14-syscall-combined-production-preparation-1'
OLD=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-3/m14-remote-flush/production-consumer-preparation-1')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def sy(p,k):
 return {a[-1] for l in p.read_text().splitlines() if (a:=l.split()) and len(a)>=2 and a[-2]==k}
pr=PB/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json';prec=PB/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'
sr=SB/'EXACT78-PRODUCTION-RUST.CPU-SUCCESSOR.SYMBOL-JOIN.NOT-EXECUTED.json';srec=SB/'header-transport-correction-1/ACTUAL-REMAINING15-CONSUMER-RECEIPT.json'
assert pin(prec)['sha256']=='11a772d7dc46b8d35cf9ddfad585409403245414ebfd58bf3521345464d6b764'
rp=json.loads(pr.read_bytes());rs=json.loads(sr.read_bytes());accepted=json.loads(prec.read_bytes());assert accepted['Rust_recipe']==pin(pr)
assert rp['source_count']==rs['source_count']==78
pc={};sc={}
for k,row in rp['source_inputs'].items():
 p=Path(row['private']['path']);assert pin(p)==row['private'];pc[k]=row['private']
for k,row in rs['source_inputs'].items():sc[k]=pin(Path(row['future_private_path']))
assert set(pc)==set(sc)
assert [k for k in pc if pc[k]['sha256']!=pin(ROOT/k)['sha256']]==['kernel/rust/syscall_policy.rs']
assert [k for k in sc if sc[k]['sha256']!=pin(ROOT/k)['sha256']]==['kernel/rust/process_helpers.rs']
inputs={}
for k in sorted(pc):
 canonical=pin(ROOT/k);src=B/'candidate'/k if k=='kernel/rust/mem_helpers.rs' else ROOT/k
 dst=S/k;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 inputs[k]=dict(canonical_before=canonical,private=pin(dst),modified_target=k=='kernel/rust/mem_helpers.rs',accepted_process_baseline=pc[k],accepted_syscall_baseline=sc[k])
assert inputs['kernel/rust/mem_helpers.rs']['private']['sha256']=='4635a252332cd369e36384f04a414e2b4c2d79726a4f95caafcf1d3ed1a56b4d'
assert inputs['kernel/rust/mem_helpers.rs']['canonical_before']['sha256']=='c0e7f8bd0b117c9b4e0a4e3690ef5ed5cb01bdc6b16f7225de973eba039d72d5'
rows=[[k,v['private']['sha256'],v['private']['bytes']] for k,v in inputs.items()];identity=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
pn=PB/'actual-production-capture-1/01-current78-Rust-symbols/stdout';sn=SB/'header-transport-correction-1/actual-remaining-consumer-attempt-1/11/stdout'
pU,pT=sy(pn,'U'),sy(pn,'T');sU,sT=sy(sn,'U'),sy(sn,'T')
assert len(pU)==577 and len(sU)==574
assert pU-sU=={'syscall_signalfd_publish_bridge','vm_range_insert_dump_bridge','vm_range_insert_log_bridge'} and not sU-pU
assert pT-sT=={'vm_range_insert'} and sT-pT=={'arch_ptrace','syscall_signalfd_publish_bridge'}
canonicalU=(pU|sU)-{'syscall_signalfd_publish_bridge'};priorT=pT|sT
scalar='remote_flush_tlb_cpumask';array='remote_flush_tlb_array_cpumask'
assert scalar in canonicalU and scalar not in priorT and array in priorT
expectedU=canonicalU-{scalar};expectedT=priorT|{scalar}
assert len(canonicalU)==576 and len(expectedU)==575 and len(priorT)==3041 and len(expectedT)==3042
oracle=dict(scope=__doc__,status='EXPECTED_SOURCE_DERIVATION_NOT_COMBINED_COMPILE_PROOF',accepted_process_recipe=pin(pr),accepted_process_receipt=pin(prec),accepted_process_raw_NM=pin(pn),accepted_syscall_recipe=pin(sr),accepted_syscall_complete_consumer_receipt=pin(srec),accepted_syscall_raw_NM=pin(sn),process_baseline_only_current_mismatch='kernel/rust/syscall_policy.rs',syscall_baseline_only_current_mismatch='kernel/rust/process_helpers.rs',actual_raw_U_process_only=sorted(pU-sU),actual_raw_U_syscall_only=sorted(sU-pU),actual_raw_T_process_only=sorted(pT-sT),actual_raw_T_syscall_only=sorted(sT-pT),current_canonical_U_expected_before=sorted(canonicalU),current_canonical_U_count_expected_before=576,new_private_U_expected=sorted(expectedU),new_private_U_count_expected=575,scalar_only_delta=dict(U_removed=[scalar],U_added=[],T_added=[scalar]),all_prior_public_T_expected=sorted(priorT),all_prior_public_T_expected_count=3041,qualification='Disjoint accepted source/body and raw symbol deltas predict current combined set; only next actual compile can prove it. No historical object relabeled current.')
write(P/'EXPECTED-SYMBOLS.FROM-ACCEPTED-RAW-BASELINES.json',oracle)
argv=rp['argv'][:];argv[-2]='--emit=obj='+str(O/'mckernel_rust.o');argv[-1]=str(S/'kernel/rust/lib.rs')
assert [i for i,(a,b) in enumerate(zip(argv,rp['argv'])) if a!=b]==[46,47]
assert pin(Path(argv[6]))['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
pending=V/'m14-memory-callback-next/production-consumer-preparation-1/coherent-current78-refresh-corrected-1'
pending_sources={'kernel/rust/x86_memory_helpers.rs':pin(V/'m14-memory-callback-next/candidate/kernel/rust/x86_memory_helpers.rs'),'arch/x86_64/kernel/memory.c':pin(V/'m14-memory-callback-next/candidate/arch/x86_64/kernel/memory.c')}
assert pending_sources['kernel/rust/x86_memory_helpers.rs']['sha256'].startswith('2994b6fe')
assert pending_sources['arch/x86_64/kernel/memory.c']['sha256'].startswith('2b285')
pending_record=dict(status='PENDING_ROOT_ACCEPTANCE_INTEGRATION_NOT_SELECTED',source_candidate=pending_sources,compiler_observer_stop_receipt=pin(pending/'ACTUAL-PRODUCTION-OBSERVER-STOP-RECEIPT.json'),selected_canonical_archmemory=pin(ROOT/'arch/x86_64/kernel/memory.c'),selected_canonical_Rustmemory=pin(ROOT/'kernel/rust/x86_memory_helpers.rs'),rule='Current recipe selects canonical0da70/ec832 only. If root integrates pending clearL4, halt stale preflight and create explicit additive source/NM-expectation refresh before compiler; do not silently substitute unaccepted postimages.')
assert pending_record['selected_canonical_archmemory']['sha256'].startswith('0da70') and pending_record['selected_canonical_Rustmemory']['sha256'].startswith('ec832')
rust=dict(scope=__doc__,status='SEALED_SOURCE_READY_NO_COMPILER_GRANT',argv=argv,compiler_sha256=pin(Path(argv[6]))['sha256'],source_count=78,source_inputs=inputs,source_identity_rows=rows,source_identity=identity,cfg_count=4,closure_external_modules=2,CGU=1,argv_changed_indices=[46,47],baseline_profile_recipe=pin(pr),baseline_profile_receipt=pin(prec),profile=rp['profile'],only_private_override='kernel/rust/mem_helpers.rs',candidate_source=pin(B/'candidate/kernel/rust/mem_helpers.rs'),source_patch=pin(B/'PRIVATE-SINGLE-TLB-ENTRY.patch'),actual_leaf=pin(B/'ACTUAL-SCALAR-READY-HANDOFF.json'),symbol_oracle=pin(P/'EXPECTED-SYMBOLS.FROM-ACCEPTED-RAW-BASELINES.json'),expected_U_delta=dict(expected_current_canonical_before=576,expected_after=575,removed=[scalar],added=[]),expected_T_added=[scalar],expected_all_prior_T_preserved=True,pending_clear_L4=pending_record,compiler_invocations=0,default_GCC14_kernel_link_native=False)
write(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json',rust)
old=json.loads((OLD/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json').read_bytes())
cargv=old['commands'][2]['argv'][:];oldS=OLD/'source';deltas=[]
for i,a in enumerate(cargv):
 new=a.replace(str(oldS),str(S)).replace(str(OLD/'output-1'),str(O))
 if a!=new:deltas.append(dict(index=i,before=a,after=new));cargv[i]=new
csrc=S/'kernel/mem.c';csrc.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(B/'candidate/kernel/mem.c',csrc)
assert pin(csrc)['sha256']=='638788c79fb96c1edb229d016fa678a02c0fcde6e1b56c7fa45d33b5490354d4'
headers={};canonical_headers={}
for path,row in old['actual_header_closure'].items():
 p=Path(path)
 if p.is_relative_to(oldS):
  key=p.relative_to(oldS);src=ROOT/key;dst=S/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);headers[str(dst)]=pin(dst);canonical_headers[str(key)]=pin(src)
 else:headers[str(p)]=pin(p)
assert len(headers)==67
abi=P/'actual-mem-header-ABI.c'
with abi.open('x') as f:
 f.write((OLD/'actual-mem-header-ABI.c').read_text())
 f.write('\n/* Three-argument real public scalar declaration, no provider implementation. */\n_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_cpumask),void(*)(struct process_vm*,unsigned long,int)),"actual scalar three-argument ABI");\n')
base=cargv[:];i=base.index('-o');del base[i:i+2];i=base.index('-c');del base[i:i+2]
ret=json.loads((B/'EXACT-SINGLE-ENTRY-RECIPE.CURRENT-WALK-CONSUMER.NOT-EXECUTED.json').read_bytes())['actual_C_consumer']
arch=ret['retained_object_not_rehashed']
commands=[dict(label='03-selected-complete-mem-preprocess',argv=base+['-E',str(csrc)]),dict(label='04-real-header-three-argument-callback-ABI',argv=base+['-fsyntax-only',str(abi)]),dict(label='05-selected-complete-mem-TU',argv=cargv),dict(label='06-selected-mem-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'mem.c.o')]),dict(label='07-selected-mem-relocations',argv=['/usr/bin/readelf','-rW',str(O/'mem.c.o')]),dict(label='08-selected-mem-ELF',argv=['/usr/bin/readelf','-SWs',str(O/'mem.c.o')]),dict(label='09-retained-actual-scalar-arch-consumer-relocations',argv=['/usr/bin/readelf','-rW',arch['path']]),dict(label='10-complete-mem-arch-consumer-fullRust-partial-link',argv=['/usr/bin/ld','-r',str(O/'mem.c.o'),arch['path'],str(O/'mckernel_rust.o'),'-o',str(O/'mem-arch-rust-partial.o')]),dict(label='11-selected-partial-symbols',argv=['/usr/bin/nm','-a','-S',str(O/'mem-arch-rust-partial.o')])]
for row in commands:row.update(cwd=str(O),purpose=__doc__+' '+row['label']+'; no target TLB/IRQ instructions or native execution.')
cr=dict(scope=__doc__,status='SEALED_CURRENT_COMPLETE_GCC9_MEM_TU_AND_REAL_SCALAR_ARCH_CONSUMER_NOT_EXECUTED',accepted_command_recipe=pin(OLD/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json'),accepted_complete_mem_consumer=pin(OLD/'expert-observer-correction-1/ACTUAL-PRODUCTION-WHOLE-JOIN.json'),actual_mem_dependency_descriptor=old['actual_mem_dependency_descriptor'],private_source=pin(csrc),canonical_preimage=pin(ROOT/'kernel/mem.c'),ABI_witness=pin(abi),actual_header_closure=headers,current_canonical_headers=canonical_headers,exact_C_argv_delta=deltas,commands=commands,tools={t:pin(Path(t)) for t in [cargv[0],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld']},profile=rp['profile'],Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),expected_C_mem_entry_definitions=[],expected_C_mem_entry_imports=[],expected_entries=[scalar,array],expected_C_callback_providers=old['expected_C_callback_providers'],expected_readonly_C_geometry=old['expected_readonly_C_geometry'],expected_existing_vector=old['expected_existing_vector'],actual_scalar_C_consumer=ret,retained_arch_object_content_not_rehashed=True,expected_partial_Rust_entry_unique_T=[scalar,array],expected_partial_all_prior_Rust_T=pin(P/'EXPECTED-SYMBOLS.FROM-ACCEPTED-RAW-BASELINES.json'),C_consumer_correction='Whole selected mem.c has no remaining call to either scalar or array entry; both C bodies are excluded. Accepted complete arch memory object b1a4 supplies actual scalarU/relocation. FullRust array uses unchanged C callbacks/declarative geometry/vector from mem.c.',remaining_nearby_C_callback_debt=13,compiler_difference='Accepted ordinary GCC9 complete selected TU, not exact GCC14.3.1 production compilation.',pending_clear_L4=pending_record,compiler_invocations=0,production_default_kernel_link_native=False)
write(P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json',cr)
allcommands=[dict(label='00-current78-production-Rust-compile',argv=argv),dict(label='01-current78-Rust-symbols',argv=['/usr/bin/nm','-g',str(O/'mckernel_rust.o')]),dict(label='02-current78-Rust-ELF',argv=['/usr/bin/readelf','--wide','--syms',str(O/'mckernel_rust.o')])]+commands
ready=dict(scope=__doc__,status='ROOT_READY_SOURCE_ONLY_NO_COMPILER_GRANT_NO_CPU_RESERVATION',Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json'),expected_symbol_oracle=pin(P/'EXPECTED-SYMBOLS.FROM-ACCEPTED-RAW-BASELINES.json'),source_count=78,source_identity=identity,only_private_Rust_override='kernel/rust/mem_helpers.rs',C_private_postimage=pin(csrc),header_count=67,actual_commands=allcommands,command_count=12,ordinary_profile=rp['profile'],pinned_compiler_sha256=rust['compiler_sha256'],cfg_count=4,CGU=1,externalmodules=2,pending_clear_L4=pending_record,default_selected_mem_TU_does_not_import_entries=True,actual_scalar_import_from_retained_arch_object=arch,compiler_jobs=0,test_jobs=0,CPU_slots_held=0,canonical_writes=0,remaining_C_callbacks=13,full_current_combined_Rust_mem_TU_partial_proof='NOT_EXECUTED',exact_GCC14_defaultkernel_link_native='OPEN',execution_requirements=['Root explicit one ordinary job grant; fresh19GiB/7jobs aggregate/floors/full sparsegap; same pinned2GiBAS60CPU90+6FSIZE32MiBFD256core0/CGU1/stack2MiB profile.','Before child verify frozen78/header/tool/source/profile and pendingclearL4 canonical state; source identity change stops without compilation.','Reuse unchanged990807 owned_capture dict API with all imports/global dependency verification and preregistered TERM/INT/ALRM; whole joins/groupabsence/closedstreams before CPU release.','Compiler once; hash durable actual Rust object once before NM/readelf; preserve warnings and artifact on observer failure.','Actual fullRust exactU575, all3041priorT plus scalarT; both entries unique in partial; all12 C callback providers retained and all13Ccallback bodies remain debt.','First unexpected failure STOP, preserve all histories; no self-reset/replay.'])
write(P/'PRODUCTION-CONSUMER-READY.json',ready)
print(json.dumps({'ready':pin(P/'PRODUCTION-CONSUMER-READY.json'),'Rust':ready['Rust_recipe'],'C':ready['C_recipe'],'source_identity':identity,'commands':12,'compiler_jobs':0,'CPU_slots_held':0}))
