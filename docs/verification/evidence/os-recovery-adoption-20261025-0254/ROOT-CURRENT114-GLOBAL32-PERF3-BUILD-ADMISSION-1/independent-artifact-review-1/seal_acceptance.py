"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Seal retained offline artifact proofs; performs no execution or resource queries.
"""
from pathlib import Path
import datetime,hashlib,json
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
core=read(D/'CORE-ARTIFACT-READBACK.json');com=read(D/'METADATA-EDGE-ABI-WARNING-COMPLEMENT.json');profile=read(P/'PROFILE.SOURCE-ONLY.json');prod=read(P/'OUTPUT/work/evidence/producer-contract.json');resource=read(P/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json');execution=read(P/'INDEPENDENT-ACTUAL-HELD-RESOURCE-EXECUTION-REVIEW.json')
assert prod['source_profile']==ref(P/'PROFILE.SOURCE-ONLY.json')
assert ref(profile['actual_root_adoption']['path'])==profile['actual_root_adoption']
publication=ref(P/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json');assert execution['source_publication']==publication
assert core['counts']==dict(Rust_selected_providers=59,C_kernel_functions=61,C_arch_functions=19,C_total=80,C_process_OBJECTs=31)
assert len(core['exports'])==59 and len(core['GLOBAL32'])==32 and sum(r['slots'] for r in core['GLOBAL32'])==64 and sum(r['bytes'] for r in core['GLOBAL32'])==2048
assert len(core['LOCAL14'])==14 and sum(r['bytes'] for r in core['LOCAL14'])==448
assert len(core['actual_selected_consumer_proofs'])==76 and len(com['C_metadata_213'])==213
assert len(core['registry_function_proofs'])==2 and core['registry']['original_record_multiset_equal']
metrics={k:com[k] for k in ['actual_commands','span_seconds','sum_command_wall_seconds','CPU_seconds','maximum_child_RSS_KiB_worker_cumulative']};metrics.update(resource_epoch=resource['observed_at_epoch'],resource_to_first_compiler_seconds=com['actual_commands'][0]['started_at_epoch']-resource['observed_at_epoch'])
source_review=E/'next114-debug32-perf3-coherent-source-1/outer-perf-line-restore-source-1/independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json'
mechanical_review=E/'next114-debug32-perf3-coherent-source-1/root-selective-adoption-materialization-proposal-source-1/independent-source-review/INDEPENDENT-SOURCE-REVIEW.json'
proofs={p.name:ref(p) for p in [D/'CORE-ARTIFACT-READBACK.json',D/'METADATA-EDGE-ABI-WARNING-COMPLEMENT.json',D/'SELECTED-DATA-CONSUMERS.json',D/'ALL59-EXACT-ENTRY-ALIASES-AND-CONSUMERS.json',D/'ANONYMOUS-EXACT-SELECTED-ENTRY-EDGES.json',D/'FINITE-ANONYMOUS-OWNER-INVENTORY.json']}
report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT114_SELECTED_DEFAULT_ARTIFACT_AND_CURRENT_CONSUMERS',independent=True,reviewer='/root/current110_execution_review',recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),source_adoption=profile['actual_root_adoption'],source_publication=publication,frozen_profile_publication_null_preserved=True,actual_execution_review=ref(P/'INDEPENDENT-ACTUAL-HELD-RESOURCE-EXECUTION-REVIEW.json'),source_review=ref(source_review),mechanical_review=ref(mechanical_review),previous_acceptance=core['previous_acceptance'],tuple=core['tuple'],counts=core['counts'],proofs=proofs,actual_join=dict(runner=ref(P/'HOLDER/RUNNER.JOINED.json'),holder_terminal=ref(P/'HOLDER/BUILD-LOCAL-TERMINAL.json'),container_terminal=ref(P/'OUTPUT/terminal.json')),metrics=metrics,
production_artifact_findings=[
'All4 exact production commands joined0;3 fresh objects and8 exact retained objects feed genuine11-input raw link.119-source Rust cohort and genuine CURRENT113 origin are reused at accepted source scope.',
'All59 selected Rust exports have unique input/final ownership and complete final-byte reconstruction. Inherited56 and existing atomic alias retain exact113 nonrelocated bodies and positive relocation provenance. Two new wrappers bind genuine existing x86 implementations; u32 hardware-code narrowing and CInt return retain source/actual ABI/HOST qualification.',
'Actual C kernel functions61 plus retained arch functions19 total80; process C OBJECTs31. Exactly3 old C callback definitions disappear: extra_set, init_raw and event_atomic64_read. Accounting is2 new Rust wrappers plus1 already existing Rust atomic bridge newly selected by C alias.',
'GLOBAL32 Ddebug objects own64 slots/2048B, each32B/aligned8, exact original file/function/line, flags0, null format and zero pad;128 R64 string fields bind exact readonly final bytes. GNU_RETAIN is present. All14 LOCAL C records/14slots448B and C configuration objects remain owned by C.',
'All76 functions actually referencing the moved data reconstruct complete final bytes with113 nonrelocated parity. Finite anonymous LOCAL function/data owners and5 self-function jump tables resolve exact current input/final symbols or bytes; no unknown address is skipped.',
'The actual389-record registry has identical record multiset and32B start..stop coverage. Exact final show/store bodies equal113 and retain complete traversal. Moving GLOBAL descriptors into the Rust link-set changes sysfs listing row order; file/function/line matching and update semantics retain every record. Byte-identical listing order is not claimed.',
'All213 remaining C metadata objects retain raw initializers/types/bindings;189 retain identical raw relocations.24 records/38 changed fields have exact original/current named-owner or readonly-string provenance and complete current final bytes.',
'Three new callback table fields resolve actual Rust providers. Both full provider tables and5 actual Rust table consumers reconstruct positive final bytes, including field8/16 extra_set/init_raw and atomic_read field16.',
'39 of59 selected entrypoints have positive direct or exact same-entry alias R64 consumer edges in the11 inputs. Other20 are inherited emitted provider bodies without such a direct raw edge in this tuple. Their body/source acceptance is retained; no new consumer execution or native retirement is inferred from symbol presence.',
'Inherited13 folded arguments, timer120B, idle116B, runqueue208B/17 fields, scalar4 constants/8 consumers, four LOCAL logger records and337B logger/jump table revalidate against actual image. Required ELF entry and symbols pass.'],
warnings=dict(Rust143_entire_stream_equal113=core['warning_stream'],kernel_C_seven_original_messages=com['seven_inherited_kernel_warning_messages'],process_C_stderr_empty=True,link_stderr_equal113=True,six_unused_C_initializers_unchanged=True,inherited_syscall17B_ABI_bridge=com['inherited_syscall17B_ABI_target']),
preserved_open=['Original seven older C section-relative metadata provenance limitations remain OPEN at accepted inherited scope.','Native execution, application coverage, supported whole-file C retirement and full M14/M15 completion remain OPEN; this receipt grants no runtime authority.','Original failed113 E0616 batch, old GNU linker retain failure, withdrawn dead witness, outer PERF FILELINE blocked candidate and offline reader failures remain preserved.'],
reader_failures_preserved=[ref(p) for p in sorted(D.glob('reader-*failure.py'))]+[ref(p) for p in sorted(D.glob('READER-*FAILURE.json'))]+[ref(D/'reader-fifth-kernel-warning-assumption.py'),ref(D/'RECEIPT-ASSEMBLY-PUBLICATION-NULL-FAILURE.json')],blocking_findings=[],actual_compiler_replays=0,native_actions=0,guard_or_resource_queries=0,canonical_mutations=0,native_acceptance=False,wholefile_retirement=False,runtime_authority=None,current_free_authority=False)
out=D/'INDEPENDENT-ACCEPTANCE.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),counts=core['counts'],span_seconds=metrics['span_seconds'],CPU_seconds=metrics['CPU_seconds'],resource_to_compiler=metrics['resource_to_first_compiler_seconds'],blockers=[])))
