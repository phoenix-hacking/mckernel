"""Functional OS source handoff only; no security testing or execution."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def write(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
assert not (D/'SOURCE-READY.json').exists();checks=read(D/'SOURCE-CHECKS.json');assert checks['status']=='PASS_PRIVATE_CHANGED_COMPOSITION_SOURCE_ONLY'
q=read(A/'M14-CONVERSION-FIRST-COMPOSITION-1/actual-build-evidence-update-1/47-SYMBOL-QUEUE.ACTUAL-BUILD-UPDATE.json');inputs=read(D/'INPUTS.json');updates={
 'do_syscall':('B','SOURCE_COMPOSED_WHOLE_OFF','all direct caller initialized wire fields incl clone/coredump/init; thread/endpoint/response lifetime; actual29 geometry and C metadata ownership'),
 'util_thread':('B','SOURCE_COMPOSED_WHOLE_OFF','actual23 geometry and partial host-info initialization/ownership/lifetime; args5 Root intended zero alone insufficient'),
 'wait_host_wait4_bridge':('B','COMPILE_ONLY_EXPERIMENTAL_COHORT','natural request72/align8 exact ca85 six slots; actual29 packet ABI, callgraph and synchronous lifetime remain'),
 'syscall_do_syscall3_bridge':('B','COMPILE_ONLY_EXPERIMENTAL_COHORT','same declared arity natural request; no all-caller proof'),
 'syscall_policy_do_syscall2_bridge':('B','COMPILE_ONLY_EXPERIMENTAL_COHORT','same declared arity natural request; no all-caller proof'),
 'syscall_policy_do_syscall3_bridge':('B','COMPILE_ONLY_EXPERIMENTAL_COHORT','same declared arity natural request; no all-caller proof'),
 'syscall_execveat_bridge':('A_bridge','COMPILE_ONLY_EXPERIMENTAL_COHORT','wrapper forwards C do_execveat; line-family actualCPP feedback required; no ACK or whole exec lifetime claim'),
 'do_execveat':('A_exec_defined_fields','WHOLE_SOURCE_FRAGMENT_COMPOSED_OFF','approved phase1six/phase2three fields; selected metadata/descriptor/transport/ACK/full lifetime and actualABI29 open'),
 'ptrace_detach_do_kill_bridge':('C','COMPILE_ONLY_EXISTING_LEAF_PAIR','existing do_kill provider pointer/borrow lifetime; actual selected ABI review'),
 'ptrace_detach_kfree_bridge':('C','OFF_EXISTING_RUST_METADATA_REUSED','actual profile/source origin and ownership proof required; no activation'),
 'interrupt_syscall':('C_approved','COMPILE_ONLY_APPROVED_DEFINED_PROFILE','Root approved three arguments plus unusedzero fields; original lifetime/transport/tuple matching remains'),
 'ptrace_wakeup_log_bridge':('C_approved','COMPILE_ONLY_APPROVED_DEFINED_PROFILE','Root approved low32 unsignedhex diagnostic; exact original389 profile and logger context remains'),
 'terminate':('C','WHOLE_SOURCE_LEAF_OFF','original389 source profile/ownership/lifetime and actualC/Rust ABI; no host ACK inferred'),
 'terminate_mcexec':('C','WHOLE_SOURCE_LEAF_OFF','actual ABI/atomic/lifetime+metadata ownership'),
 'terminate_host':('C','WHOLE_SOURCE_LEAF_OFF','actual ABI/refcount/threadprocess lifetime'),
 'sys_perf_event_open':('D_approved','COMPILE_ONLY_EXPERIMENTAL_COHORT','real perf104/request72/binding352 compile asserts; provider/ioctl/borrow lifetime remains'),
 'do_setresuid':('D','COMPILE_ONLY_EXPERIMENTAL_COHORT','original ignored ioctl failure does not prove initialized output; preserve intended original semantics and host contract'),
 'do_setresgid':('D','COMPILE_ONLY_EXPERIMENTAL_COHORT','same ignored ioctl output/lifetime limitation'),
 'syscall_forward_rt_sigprocmask_bridge':('D_approved','COMPILE_ONLY_EXPERIMENTAL_COHORT','approved six scratch registers and exact meaningful volatile order; actual wire/context lifetime remains'),
 'syscall_forward_sigaction_update_bridge':('D_approved','COMPILE_ONLY_EXPERIMENTAL_COHORT','approved six scratch registers and ordered action store/read; actual wire/context lifetime remains')}
for r in q['rows']:
 if r['scope']=='F06_arch':r['next_private_source']=dict(state='COMPILE_ONLY_ARCH5_EXPERIMENTAL',input=inputs['ARCH5'],contract='Exact ROW-CONTRACTS and61slot real geometry/codegen/lifetime/GS/TSS/xstate; no native clearance')
 elif r['symbol']in updates:
  key,state,gate=updates[r['symbol']];r['next_private_source']=dict(state=state,input=inputs[key],unmet_predicate=gate)
q['combined_source_filemap']=ref(D/'FILEMAP.SOURCE-ONLY.json');q['actual_build_evidence']['full_artifact_and_389_independent_qualification']='Root reports accepted2565 full389; original bound build-map receipt retained unchanged';q['accepted_C_retirement']=0;q['native_validated_candidates']=0;write('47-SYMBOL-QUEUE.NEXT-SOURCE.json',q)
# Enumerate exact per-interface ABI obligations, including cases that have only
# source assertions/signature witnesses and must not imply actual geometry PASS.
abi=read(D/'ACTUAL-ABI-WITNESS-MAP.PROPOSED.json');abi['interface_obligations']=[dict(symbol=s,source=inputs[k],state=state,exact_unmet=gate,actual_ABI_result=None)for s,(k,state,gate)in updates.items()]+[dict(symbol=r['symbol'],source=inputs['ARCH5'],state='61_SLOT_MATCHED_REAL_HEADER_PROBE_PROPOSED',actual_ABI_result=None)for r in q['rows']if r['scope']=='F06_arch'];write('ACTUAL-ABI-WITNESS-MAP.PROPOSED.json',abi)
# Update map reference after adding complete interface obligations.
x=read(D/'AFFECTED-UNIT-CANDIDATE-INPUTS.json');x['actual_ABI_witness_map']=ref(D/'ACTUAL-ABI-WITNESS-MAP.PROPOSED.json');write('AFFECTED-UNIT-CANDIDATE-INPUTS.json',x)
(D/'ROOT-NEXT.md').write_text('''Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One37target private overlay/complete patch composes source2 with A bridge9208, exact exec defined-fields a0b05 (whole OFF), B opt-in wiring5282/natural constructor d1e/paired ABI plan11e6, termination family878c+QueueC1b33+approved55b447, D credential cda8/perf dde53/signal13d481, and the single ARCH5 eight-file patch1c73 including line-neutral six-descriptor transfer and approved SIGTRAP. Other incoming whole mmap/fork proposals remain explicit separate unresolved queues; no source was reimplemented or excluded as unsupported. No earlier F06 fragment was replayed over ARCH5. Old first149/source2/canonical119 remain unchanged.

Eight focused composition groups PASS. All17 inherited external leaves are exact; inherited lib remains exact; every new module and dependency occurs once. ARCH5 prefix and six originalC tuple transfer are retained byte-for-byte, with all47 remaining inherited line!/file! sites at their exact supplied coordinates. Whole exec source is appended under its OFF cfg. C wrapper/line restorations are exact incoming bytes, including the A bridge9208 family which still requires actual preprocessor/compiler feedback: no more manual line arithmetic is inferred. Actual full original389 registry for this candidate remains unrun; no oracle/source constants/ELF rewrites are proposed.

Mechanical failures are preserved: a nonunique blank-line deletion required exact surrounding-context anchoring; D CMake option insertion then had ambiguous16line contexts, resolved using Root-confirmed unique inherited wakeup-writer Rust/C cohort anchors. A bridge C flag is appended in the later C property cohort after baseline source COMPILE_DEFINITIONS; placing it in early Rust-cfg setup would be overwritten. Both source pair and cohort checks now pass. Whole source contracts were not changed by the compositor.

The test-only experimental compile profile proposes constructors, exec bridge, D signal/perf/credentials and ARCH5 paired selections. Approved interrupt/logger pairs remain in the exact /src Linux6.12 nonUBSAN source cohort. Do_syscall/util whole selectors stay OFF because all-caller initialized wire/lifetime/host partial-info contracts remain incomplete; no ca85 proof is fabricated for clone/coredump/init. Kfree stays OFF without genuine origin/profile binding. Termination/exec whole selectors stay OFF with explicit selected metadata/ABI/lifetime/provider gaps. These choices are source/build-test proposals, not runtime/default adoption. Credential ioctl failure remains ignored as before and never implies initialized output. No originating service/account restriction is cleared.

Root's next executable step is to adopt this exact filemap into one fresh reviewed producer profile, apply the explicit compile-only option/flag deltas, and compile the affected Rust crate, generic C and arch C, then relink. Reuse the eight exact existing objects/SDK21/source6153; arch30bd is predecessor evidence only and must be rebuilt. No clean SDK build or CURRENT119 native precondition is needed. Actual profile/namespace/grant remains Root-authored. Actual compiler/codegen/provider/CPP/original389 feedback is required before any integration acceptance.

ABI probes are separate qualification objects under the exact real selected SDK headers/flags: ARCH61 ordered u64 geometry, request72/align8 and packet fields, do_syscall29, util23, and perf104/request72/binding352 assertions. Compare ELF array bytes with the exact Rust counterpart and recorded object identities. Do not execute C test consumers/HOST substitutes and never add their allocated C arrays/functions to production rawlink. ARCH5_ABI_WITNESS stays OFF in the production candidate; no final C0 claim can use a witness-enabled image. ACTUAL-ABI-WITNESS-MAP enumerates every interface and its actual missing result.

The first19 image1cd7 is a separate actual compiled/linked candidate whose full artifact/original389 was reported independently accepted2565; it is not native validation or C retirement. Accepted119 baseline47, native0/C-retirement0/files4of6 and all retained custody/UNKNOWN history are unchanged. This packet starts no compiler, guard, controller, cleanup, native or billing action.
''')
files=['compose_source.py','check_source.py','prepare_handoff.py','seal_source.py','INPUTS.json','FILEMAP.SOURCE-ONLY.json','COMBINED.PRIVATE-NOT-APPLIED.patch','MERGE-LOG.json','SOURCE-CHECKS.json','COMPILE-ONLY-EXPERIMENTAL-PROFILE.PROPOSED.json','ACTUAL-ABI-WITNESS-MAP.PROPOSED.json','AFFECTED-UNIT-CANDIDATE-INPUTS.json','47-SYMBOL-QUEUE.NEXT-SOURCE.json','ROOT-NEXT.md','FIRST-MERGE-FAILURE.json','SECOND-MERGE-CONTEXT.FAILURE.json']
write('SOURCE-READY.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_COHERENT_COMBINED_SOURCE_AND_COMPILE_INPUTS_READY_PENDING_CHANGED_REVIEW_AND_ROOT_ADOPTION',files={n:ref(D/n)for n in files},source_targets=37,baseline_actual_compiled19='Root reported independent artifact/original389 accepted2565; native/adoption separate',independent_combined_source_review=None,actual_compiler_CPP_ABI_link_native=False,C_retirement=False,runtime_authority=None))
print(json.dumps(dict(ready=ref(D/'SOURCE-READY.json'),patch=ref(D/'COMBINED.PRIVATE-NOT-APPLIED.patch'),map=ref(D/'AFFECTED-UNIT-CANDIDATE-INPUTS.json'),checks=ref(D/'SOURCE-CHECKS.json'))))
