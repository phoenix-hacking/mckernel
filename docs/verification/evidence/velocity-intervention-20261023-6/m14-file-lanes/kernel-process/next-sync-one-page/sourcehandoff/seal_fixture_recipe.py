"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Freeze one small original-C/Rust/real-ABI/actual-caller fixture, no execution.
"""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parents[1];F=B/'fixture';H=B/'sourcehandoff';R=Path('/home/holden/mckernel');O=B/'output-first-candidate-1'
DUMP=B.parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def main():
 previous=json.loads((DUMP/'sourcehandoff/EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json').read_text());assert pin(DUMP/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json')['sha256']=='16fb6f066adb4783c8d5331bd715c5014b76bc555803b32d9ead161be2884859'
 fixture=(F/'actual_provider.rs').read_text();start=fixture.index('\n#[no_mangle]\npub unsafe extern "C" fn fixture_sync_layout(');leaf=fixture[:start].replace('fn fixture_rust_sync_one_page(','fn sync_one_page(',1)
 assert 'fn fixture_sync_layout' not in leaf and leaf.count('fn kprintf(')==1
 (F/'hosted_production_leaf_provider.rs').write_text(leaf)
 proc=(B/'candidate/kernel/rust/process_helpers.rs').read_text();assert proc.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 # The actual selected caller is compiled unchanged. Its existing helper and
 # callback declarations remain explicit unresolved production providers in this
 # small consumer proof; no fake helper algorithm or C consumer is introduced.
 caller='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;
use core::ptr::null_mut;
use abi::{CInt,CULong,Memobj,ProcessVm,VmRange};
#[repr(C)] struct ProcessSyncArgs { memobj:*mut Memobj }
type ProcessNoirqLockFn=unsafe extern "C" fn(CULong);
type ProcessNoirqUnlockFn=unsafe extern "C" fn(CULong);
type ProcessVisitPteRangeFn=unsafe extern "C" fn(*mut c_void,CULong,CULong,CInt,CInt,*mut c_void,*mut c_void)->CInt;
type ProcessSyncRangeLogFn=unsafe extern "C" fn(*mut ProcessVm,*mut VmRange,CULong,CULong,CInt);
extern "C" {
 fn sync_one_page(arg0:*mut c_void,page_table:*mut c_void,ptep:*mut c_void,pgaddr:*mut c_void,pgshift:CInt)->CInt;
 fn process_sync_memory_range_body_result(vm:*mut ProcessVm,range:*mut VmRange,start:CULong,end:CULong,arg:*mut c_void,visit_step_fn:*mut c_void,lock_fn:Option<ProcessNoirqLockFn>,unlock_fn:Option<ProcessNoirqUnlockFn>,visit_fn:Option<ProcessVisitPteRangeFn>,log_fn:Option<ProcessSyncRangeLogFn>)->CInt;
 fn process_free_range_noirq_lock_bridge(lock_addr:CULong);
 fn process_free_range_noirq_unlock_bridge(lock_addr:CULong);
 fn process_visit_pte_range_bridge(page_table:*mut c_void,start:CULong,end:CULong,pgshift:CInt,flags:CInt,visit_fn:*mut c_void,arg:*mut c_void)->CInt;
 fn process_sync_range_log_bridge(vm:*mut ProcessVm,range:*mut VmRange,start:CULong,end:CULong,error:CInt);
}
'''+(F/'actual_selected_Rust_caller.ACTUAL.inc').read_text()
 (F/'actual_selected_Rust_caller.rs').write_text(caller)
 flags=previous['commands'][2]['argv'][1:];flags=flags[:flags.index('-fno-pie')];gcc='/usr/bin/gcc-9';rv=previous['commands'][0]['argv'][:-3]
 assert rv[-2:]==['-C','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 cmds=[]
 def add(name,argv):cmds.append(dict(name=name,argv=argv,cwd=str(O),purpose=SCOPE+' '+name+'; pure hosted body/ABI/selected-consumer evidence only, no native TLB instruction.'))
 for name,source,obj in [('00-actual-Rust-fixture-body','actual_provider.rs','actual_provider.o'),('01-hosted-Rust-actual-leaf','hosted_production_leaf_provider.rs','actual_leaf.o'),('02-actual-existing-Rust-caller','actual_selected_Rust_caller.rs','actual_caller.o')]:add(name,[*rv,str(F/source),'-o',str(O/obj)])
 add('03-actual-original-C-parity-object',[gcc,*flags,'-fno-pie','-c',str(F/'actual_parity.c'),'-o',str(O/'actual_parity.o')])
 add('04-actual-original-C-Rust-link',[gcc,'-no-pie','-Wl,--no-undefined',str(O/'actual_parity.o'),str(O/'actual_provider.o'),'-o',str(O/'actual_parity')])
 add('05-actual-795-parity-execute',[str(O/'actual_parity')])
 add('06-actual-real-header-ABI',[gcc,*flags,'-fsyntax-only',str(F/'actual_sync_header_ABI.c')])
 for selected,n in [(True,'07'),(False,'09')]:
  label='selected' if selected else 'fallback';obj=O/(label+'.o')
  add(n+'-actual-C-'+label,[gcc,*flags,'-O0','-fno-pie','-DMCKERNEL_RUST_PROCESS_HELPERS' if selected else '-UMCKERNEL_RUST_PROCESS_HELPERS','-c',str(F/'actual_default_and_fallback_consumer.c'),'-o',str(obj)])
  add(('08' if selected else '10')+'-actual-C-'+label+'-symbols',['/usr/bin/nm','-a','-S',str(obj)])
 add('11-hosted-actual-Rust-leaf-symbols',['/usr/bin/nm','-g',str(O/'actual_leaf.o')])
 add('12-actual-existing-caller-relocations',['/usr/bin/readelf','-rW',str(O/'actual_caller.o')])
 add('13-actual-selected-consumer-partial-link',['/usr/bin/ld','-r',str(O/'selected.o'),str(O/'actual_leaf.o'),str(O/'actual_caller.o'),'-o',str(O/'actual_selected_partial.o')])
 add('14-actual-selected-consumer-partial-symbols',['/usr/bin/nm','-a','-S',str(O/'actual_selected_partial.o')])
 add('15-actual-selected-consumer-partial-ELF',['/usr/bin/readelf','-SWr',str(O/'actual_selected_partial.o')])
 assert len(cmds)==16
 current={key:pin(Path(row['path'])) for key,row in previous['current_canonical_header_preimages'].items()};assert current==previous['current_canonical_header_preimages']
 # Finite layout/provider pins only; no broader process-file census.
 provider_paths=['kernel/rust/pte_helpers.rs','kernel/rust/object_helpers.rs','kernel/rust/abi.rs','lib/include/ihk/debug.h']
 providers={key:pin(R/key) for key in provider_paths}
 bindings={str(path.relative_to(B)):pin(path) for directory in ('candidate','fixture','patch','sourcehandoff') for path in (B/directory).rglob('*') if path.is_file()}
 recipe=dict(scope=SCOPE,status='SOURCE_FROZEN_ONE_SYNC_FIXTURE_NOT_GRANTED',commands=cmds,input_bindings=bindings,tools=previous['tools'],accepted_real_C_profile=previous['accepted_real_C_profile'],accepted_prior_production=previous['accepted_prior_production'],actual_header_closure=previous['actual_header_closure'],current_canonical_header_preimages=current,current_provider_pins=providers,profile=previous['profile'],expected_comparisons=795,expected_comparison_breakdown=dict(base_state_shift_flags_operation_debug_matrix=720,ordered_mutation_matrix=72,shortcircuit_NULL_args=3),oracles='Actual original C callback against actual Rust body; independent expected final PTE/error/event tape; actual six PTE providers including atomic dirty updates and actual typed memobj operation dispatch; controlled hosted TLB effect only; exact pointer/UL/int variadic format payloads and ignored logger result. Entry/exit flags independently0/1/128/255; shifts12/21/30; null/fileoff/clean skip; zero-fill flag with unsigned highbit; missing op/defaultsuccess and0/-5/+7/INT_MIN returns; entry/TLB/flush/error/exit mutation points; error log before redirty; NULL args only skipped with disabled diagnostics.',actual_consumer_scope='Unchanged actual Rust sync_process_memory_range entry compiled as standalone consumer with exact existing helper/callback declarations. Its named sync_one_page relocation must survive byte/full-relocation equality into partial and resolve to unique Rust definition; helper/callback providers remain explicit debt, not mocked algorithms.',host_adapter_scope='All TLB effects in hosted leaf/parity are explicit fixture_tlb_effect; real reviewed x86 flush_tlb_single provider remains source-bound in SOURCE-NEXT-BODY and is not executed by these commands.',expected_C_selected='No sync_one_page definition; exactly two original declarative ddebug32B globals, original callsite lines2546/2574 flags0.',expected_C_fallback='Exact extracted original sync_one_page T; ordinary local ddebug rows and original provider imports remain.',required_partial_symbols={'sync_one_page':'unique Rust T','sync_process_memory_range':'unique actual existing Rust T','process_sync_one_page_entry_debug':'D32 Cdata','process_sync_one_page_exit_debug':'D32 Cdata'},remaining_provider_debt=['existing Rust process_sync_memory_range_body_result (standalone declaration only in consumer proof)','existing process_free_range_noirq_lock_bridge/unlock_bridge, process_visit_pte_range_bridge, process_sync_range_log_bridge (real production providers, not executed here)','existing kprintf provider','fixture_tlb_effect explicit hosted architecture-effect adapter'],failure_history=dict(prior_duplicate_E0428='2fb3/e9a correctedaccepted7a retained; new fullmodule reuses existing kprintf declaration once',prior_dump_observer='c774 retained; named-target correction84ef/e48c accepted; no total-relocation cardinality oracle',source_extraction_failure=pin(H/'SOURCE-EXTRACTION-PREPARATION-FAILURE-1.json'),current_sync_compiled_failures=0,next_unexpected_result='STOP_FIRST_UNEXPECTED_RESULT_NO_AUTOMATIC_RETRY'),compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,fullcrate_default_native_credit=False)
 write(H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json',recipe)
 ast.parse((H/'run_owned_first_candidate.py').read_text())
 ready=dict(scope=SCOPE,status='F02_SYNC_ONE_PAGE_ONE_EXECUTABLE_READY_JOB_NO_GRANT',recipe=pin(H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json'),driver=pin(H/'run_owned_first_candidate.py'),source_body=pin(H/'SOURCE-NEXT-BODY.json'),actual_consumer=pin(H/'ACTUAL-CONSUMER-SOURCE-ONLY.json'),predecessor_dump_production=pin(DUMP/'production-consumer-preparation-1/bounded-observer-correction-1/OBSERVER-RESULT.json'),postimages={key:pin(B/'candidate'/key) for key in ['kernel/process.c','kernel/rust/process_helpers.rs']},source_dependencies='Private successor includes accepted private dump predecessor1ec/700; no canonical replacement before root integration/rebase.',prepared_commands=16,prepared_comparisons=795,profile=recipe['profile'],Rust_compiler='Pinned leaf Rust1.92 SHA028fd60b; not production70eb',compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,source_correctness_claim=False,default_fullcrate_native_credit=False,requires='New exact root ordinary CPU6 grant plus fresh admission; no fixture compile/test at preparation time.')
 write(H/'EXECUTABLE-READY.NOT-GRANTED.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(H/'EXECUTABLE-READY.NOT-GRANTED.json'),recipe=ready['recipe'],driver=ready['driver'],commands=16,prepared_comparisons=795,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
