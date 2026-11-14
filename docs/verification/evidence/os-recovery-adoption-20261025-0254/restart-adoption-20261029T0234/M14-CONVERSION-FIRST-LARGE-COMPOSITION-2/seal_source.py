"""Functional OS source/data handoff only; no security testing or runtime authority."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def write(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
m=read(D/'FILEMAP.SOURCE-ONLY.json');inputs=read(D/'INPUTS.json');q=read(B/'47-SYMBOL-QUEUE.json')
gates={
'do_syscall':'OFF: exact selected initialized request arguments, synchronous response/endpoint/thread lifetime, PROFILE_ENABLE/non-ToFu/nonFugaku ABI and ownership review; selected C constants/Ddebug data require genuine Rust ownership before retirement',
'util_thread':'OFF: Root args5=0 intent only, host partial-info/lifetime and selected UTI context/layout/provider contracts, ABI review; selected C layout/constants/origin/descriptor/Ddebug data are still project C ownership debt',
'wait_host_wait4_bridge':'OFF: ca85 defined six wire slots; natural alignment correction f847/4ef source accepted; exact callgraph, 29-word transport ABI, lifetime/codegen and independent unsafe review open',
'syscall_do_syscall3_bridge':'OFF: same declared-arity six-slot contract, selected caller closure/29-word ABI/lifetime/codegen open',
'syscall_policy_do_syscall2_bridge':'OFF: same declared-arity six-slot contract, selected caller closure/29-word ABI/lifetime/codegen open',
'syscall_policy_do_syscall3_bridge':'OFF: same declared-arity six-slot contract, selected caller closure/29-word ABI/lifetime/codegen open'}
for r in q['rows']:
 if r['symbol']in gates:
  r.update(candidate_state='PRIVATELY_COMPOSED_OFF_PENDING_CONTRACT_AND_REVIEW',candidate_default_selection_intent=False,gate=gates[r['symbol']],references=[inputs['dispatch'if r['symbol']=='do_syscall'else 'util'if r['symbol']=='util_thread'else 'constructors_natural_alignment'],inputs['Root_defined_contract']])
assert len(q['rows'])==47;q['status']='SOURCE_ONLY_LARGE_SUCCESSOR_QUEUE_NO_EXECUTION_CREDIT';q['composition_parent']=ref(B/'47-SYMBOL-QUEUE.json');q['nonlisted_constructor_export']='syscall_do_syscall2_bridge is reused supplemental export, not an invented 48th qualified symbol';q['implementation_or_C_retirement_credit']=False
write('47-SYMBOL-QUEUE.json',q)
x=read(B/'AFFECTED-UNIT-CANDIDATE-INPUTS.json');x['parent_input_map']=ref(B/'AFFECTED-UNIT-CANDIDATE-INPUTS.json');x['file_overlay']=m['files'];x['producer_postimage_rows']=[dict(relative=r['target'],postimage=r['source'],frozen119_preimage=r['frozen119_preimage'])for r in m['files']];x['review_state']='PENDING_INDEPENDENT_CHANGED_COMPOSITION_AND_LARGE_BODY_CONTRACT_REVIEW';x['new_large_selection']={'do_syscall':'OFF: no C/Rust cfg activation added','util_thread':'OFF: no C/Rust cfg activation added','request_constructors':'OFF unless explicit MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL; no default ON'};x['native119_gate_for_next_affected_build']=False;x['new_affected_units']=False;x['runtime_authority']=None
assert len(x['original_link_order'])==11 and sum(r['candidate_action']=='REUSE_QUALIFIED_EXISTING_OBJECT'for r in x['original_link_order'])==8
write('AFFECTED-UNIT-CANDIDATE-INPUTS.json',x)
(D/'ROOT-NEXT.md').write_text('''Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private successor composes the frozen first20 bundle with exact existing do_syscall/util_thread Rust fragments at EOF and the five declared-arity constructor exports. All 16 inherited leaf BYTErefs remain exact; the one new external leaf is the natural-alignment correction d1e40575. The first20 snapshot and CURRENT119 canonical sources are untouched. Seven focused composition groups pass; complete 21-target patch applies outside repository-prefix filtering. The first apply attempt silently skipped C hunks because Git discovered the outer repository. The retained failure record and bounded correction isolate repository discovery and now assert every expected C selector plus exact reverse projection. No compiler or preprocessor ran.

All 53 inherited Rust location-macro coordinates and text stay exact. Reversing the three exact contributed C deltas restores every byte of the first20 C postimage, including its source-proved original389 metadata projection. The large inputs' exact conditional #line mappings and fallback bodies are reused, not renumbered. This is source projection, not an actual preprocessed/ELF 389 acceptance. No oracle, ELF, registry constants or existing descriptor tuples are rewritten. Selected large C constants/layout/origin/Ddebug tables remain explicit C data ownership debt and must not be described as final Rust retirement.

Do_syscall and util whole-body C/Rust selectors stay absent from CMake; constructors require an explicit experimental option which has no default ON. Kfree activation and origin flags stay OFF. Exact incoming body signatures/providers and OFF fallbacks are retained. See the updated 47-symbol queue for caller initialization, response/endpoint/thread lifetime, partial UTI info, 29-word packet ABI and metadata ownership gates. Supplemental syscall_do_syscall2_bridge is not a new qualified 48th symbol. Root ca85 wire semantics and natural request alignment are reused, not whole-request initialization.

Next Root-owned action is independent changed-source/ABI review, then a coherent source export and the existing affected Rust crate + generic syscall.c TU + image relink recipe. There is no CURRENT119 native prerequisite for this next affected build. Reuse exact existing arch30bd plus eight qualified objects, SDK21 and source6153 from AFFECTED-UNIT-CANDIDATE-INPUTS; this packet creates no actual build profile, namespace, release or execution authority. Existing resource and operation gates still apply.

Termination family 878cebb3, F06 whole/context35fca369, exec/fork/mmap candidates remain separate OFF source queues with ownership/ABI/metadata/request-lifetime gaps; they are not treated as compatible accepted ready leaves here. No newly selected runtime C, source-only C retirement, compile, link or native acceptance is claimed. Historical UNKNOWN, native custody, physical5b361, first149 snapshot and all controls are untouched.
''')
files=['compose_source.py','check_source.py','seal_source.py','INPUTS.json','FILEMAP.SOURCE-ONLY.json','LARGE-COMPOSITION.PRIVATE-NOT-APPLIED.patch','COMPOSITION-APPLY.json','SOURCE-CHECKS.json','47-SYMBOL-QUEUE.json','AFFECTED-UNIT-CANDIDATE-INPUTS.json','ROOT-NEXT.md','FIRST-COMPOSITION-CHECK.FAILURE.json']
write('SOURCE-READY.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_LARGE_COMPOSITION_SOURCE_CHECKS_PASS_DEFAULT_OFF_PENDING_INDEPENDENT_REVIEW',files={n:ref(D/n)for n in files},source_targets=21,inherited_leaves_exact=16,new_constructor_leaf_external=True,large_modules_exact_reuse=2,independent_review=None,actual_compile_link_native=False,C_retirement=False,runtime_authority=None))
print(json.dumps(dict(ready=ref(D/'SOURCE-READY.json'),patch=m['patch'],checks=ref(D/'SOURCE-CHECKS.json'),affected_map=ref(D/'AFFECTED-UNIT-CANDIDATE-INPUTS.json'))))
