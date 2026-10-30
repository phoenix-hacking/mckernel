"""Functional OS source/build-input DATA only; no security testing or execution."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';ARCH=A/'M14-ARCH5-CUTOVER-1';QB=A/'M14-REMAINING23-B-1';QA=A/'M14-REMAINING23-A-1';C=A/'M14-REMAINING23-C-1';QD=A/'M14-REMAINING23-D-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def write(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
inputs={'source2':B/'SOURCE-READY.json','A_bridge':QA/'bridge-selection-first20.patch','A_exec_defined_fields':QA/'defined-callers-correction-1/do_execveat.defined-arity.PRIVATE.rs.inc','B':QB/'SOURCE-READY.json','B_actual_ABI_plan':QB/'whole-abi-and-callers-2/SOURCE-READY.json','C':C/'SOURCE-PREPARATION.json','C_approved':C/'defined-callers-correction-1/SOURCE-PREPARATION.json','D':QD/'SOURCE-READY.json','D_approved':QD/'defined-callers-correction-1/SOURCE-READY.json','ARCH5':ARCH/'SOURCE-READY.json','ARCH5_owners':ARCH/'OWNER-LIST.json','first19_actual_acceptance_queue':A/'M14-CONVERSION-FIRST-COMPOSITION-1/actual-build-evidence-update-1/SOURCE-READY.json'}
write('INPUTS.json',{k:ref(p)for k,p in inputs.items()})
# Test-only compile choices are an explicit review proposal, not an activation.
options_on=['MCKERNEL_ARCH5_CUTOVER_CANDIDATE','MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL','MCKERNEL_F03_EXECVEAT_BRIDGE_EXPERIMENTAL','MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL','MCKERNEL_F03_PERF_ENTRY_EXPERIMENTAL','MCKERNEL_F03_CREDENTIAL_REFRESH_EXPERIMENTAL']
options_off=['MCKERNEL_ARCH5_ABI_WITNESS','MCKERNEL_F03_DO_SYSCALL_SUPPORTED_EXPERIMENTAL','MCKERNEL_F03_UTIL_THREAD_WHOLE_EXPERIMENTAL']
write('COMPILE-ONLY-EXPERIMENTAL-PROFILE.PROPOSED.json',dict(status='PROPOSAL_REQUIRES_ROOT_ADOPTED_PRODUCER_AND_EXECUTION_RELEASE',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',cmake_options_ON=options_on,cmake_options_OFF=options_off,kfree_activation='OFF unless actual origin/profile source binding independently supplied',termination_whole='OFF: retained source/typed providers; selected source-origin and lifetime/metadata contracts remain explicit',do_syscall_whole='OFF: no fabricated all-request-args gate; ca85 does not prove clone/coredump/init/exec or all direct callers',util_whole='OFF: host partial-info/initialization/lifetime proof remains open',exec_whole='OFF: fragment only; unresolved actual selected C metadata/ABI29/ACK/descriptor/lifetime/provider contracts',mmap_fork='OFF: range mutator/teardown owner and fork/provider lifetime gaps remain',native_execution=False,default_adoption=False,runtime_authority=None))
# Bind real source witnesses. No C witness/testconsumer is a production link input.
bready=read(QB/'whole-abi-and-callers-2/SOURCE-READY.json')
witnesses=[dict(name='ARCH5_C',source=ref(ARCH/'postimage/arch/x86_64/kernel/include/arch5-abi-witness.inc'),selected_inclusion='append after actual local sigsp definition and actual selected arch syscall headers; MCKERNEL_ARCH5_ABI_WITNESS=ON only in separate probe object',C_array='arch5_c_abi_geometry',Rust_array='arch5_rust_abi_geometry',ordered_slots=61,keymap=ref(ARCH/'ABI-GEOMETRY-KEYS.json'),production_link=False)]
for k in ['request_packet_witness','do_abi_witness','util_abi_witness','paired_consumer']:
 witnesses.append(dict(name=k,source=bready[k],selected_inclusion='actual selected generic syscall TU and real headers, isolated probe; exact selectors recorded, no HOST struct substitute',production_link=False,execute=False))
witnesses.append(dict(name='perf_actual_compile_time_asserts',source=ref(QD/'defined-callers-correction-1/perf-abi-correction-1/SOURCE-CHECKS.json'),selected_inclusion='real mc_perf_event.h, request and binding headers in actual generic C TU; Rust reprC assertions exact source',production_link='assertions only: no allocated C vector permitted'))
write('ACTUAL-ABI-WITNESS-MAP.PROPOSED.json',dict(status='SOURCE_PREPARED_ACTUAL_COMPILATION_AND_ELF_COMPARE_UNRUN',witnesses=witnesses,method='Compare ordered u64 arrays from isolated genuine C/Rust probe objects with exact actual SDK/selected flags, genuine object SHA and key order; do not call witness functions or execute HOST substitute',C_probe_objects_in_production_rawlink=[],production_witness_option='OFF',actual_result=None))
fm=read(D/'FILEMAP.SOURCE-ONLY.json');x=read(B/'AFFECTED-UNIT-CANDIDATE-INPUTS.json');x['parent_input_map']=ref(B/'AFFECTED-UNIT-CANDIDATE-INPUTS.json');x['file_overlay']=fm['files'];x['producer_postimage_rows']=[dict(relative=r['target'],postimage=r['source'],frozen119_preimage=r['frozen119_preimage'])for r in fm['files']];x['next_affected_units']=['Rustcrate mckernel_rust','generic kernel/syscall.c C TU','arch/x86_64/kernel/syscall.c C TU','coherent image relink'];x['C_test_probe_link_inputs']=[];x['experimental_profile']=ref(D/'COMPILE-ONLY-EXPERIMENTAL-PROFILE.PROPOSED.json');x['actual_ABI_witness_map']=ref(D/'ACTUAL-ABI-WITNESS-MAP.PROPOSED.json');x['review_state']='PENDING_CHANGED_COMPOSITION_ABI_AND_ROOT_ACTUAL_PRODUCER_ADOPTION';x['native119_gate_for_next_affected_build']=False
# Original input order has eleven objects: Rust+generic+arch rebuilt; eight reuse.
for row in x['original_link_order']:
 if row['link_token']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o':
  row['candidate_action']='REBUILD_AFFECTED_ARCH_C_OBJECT';row['reuse_previous_object']=False
assert sum(r['candidate_action']=='REUSE_QUALIFIED_EXISTING_OBJECT'for r in x['original_link_order'])==8
assert sum(r['candidate_action']=='REBUILD_AFFECTED_ARCH_C_OBJECT'for r in x['original_link_order'])==1
write('AFFECTED-UNIT-CANDIDATE-INPUTS.json',x)
print('SOURCE/DATA handoff prepared')
