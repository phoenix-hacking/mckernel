# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Preparation only: source reads and writes only this private/evidence packet.
from pathlib import Path
import ast,hashlib,json,shutil
P=Path(__file__).resolve().parent; R=Path('/home/holden/mckernel'); E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1'
L=Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2')
LR=R/'docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(name,data): (P/name).write_text(json.dumps(data,indent=2)+'\n')
def allpaths(v):
 if isinstance(v,dict):return set().union(*(allpaths(x) for x in v.values())) if v else set()
 if isinstance(v,list):return set().union(*(allpaths(x) for x in v)) if v else set()
 return {v} if isinstance(v,str) and v.startswith('/') else set()
bind=json.loads((P/'SOURCE-BINDINGS.json').read_text()); targets={v['path'] for v in bind['source_inputs'].values()}
pre={rel:dict(expected=row,observed=pin(Path(row['path'])),match=pin(Path(row['path']))==row) for rel,row in bind['source_inputs'].items()};assert all(v['match'] for v in pre.values())
owner=L/'source/native_diagnostic_container_owner.py';assert pin(owner)['sha256']=='401657d55cd24609d81a98f00efdb6141185ccfd2766092aa69f2be30d7ca70c'
sourcehashes=next(ast.literal_eval(n.value) for n in ast.parse(owner.read_bytes()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_HASHES' for t in n.targets));assert len(sourcehashes)==156 and not targets&set(sourcehashes)
query_path=L/'QUERY-INPUTS.json';query=json.loads(query_path.read_text());assert pin(query_path)['sha256']=='62f6482caedf4cf5ced17661fafd7c136a552977982e7dfdf96c9f08f3471890'
cohort_path=L/'COHORT-BINDINGS.json';cohort=json.loads(cohort_path.read_text())
assert not targets&allpaths(query) and not targets&allpaths(cohort)
for name in ['native_diagnostic_container_owner.py','repaired_image_authority.py','composite_module_binding.py','CURRENT68-SDK5-AUTHORITY-LINKS.json']:
 assert pin(L/'source'/name)==cohort[name]
# Follow precisely the proof-descriptor reads in the two selected authority validators,
# without importing/executing either validator or traversing historical source manifests.
selected={}
def read(ref):
 path=Path(ref['path']);assert pin(path)==ref,ref
 selected[str(path)]=pin(path);return json.loads(path.read_text())
links=read(cohort['CURRENT68-SDK5-AUTHORITY-LINKS.json'])
proofs={name:read(ref) for name,ref in links['proofs'].items()}
read(proofs['SDK5_acceptance']['actual_reads']);read(proofs['SDK5_acceptance']['owner_receipt'])
read(proofs['launcher_build_acceptance']['receipt']);read(proofs['image_build_acceptance']['producer_receipt']);read(proofs['current235_acceptance']['physical_acceptance'])
assert not targets&set(selected)
# Manifest and serialized release are selected runtime artifact/input authorities.
release=LR/'final-execution-release-1/PAYLOAD.production-canonical.json';rel=json.loads(release.read_text());manifest=Path(rel['manifest']['path']);assert pin(manifest)['sha256']==rel['manifest']['sha256'];md=json.loads(manifest.read_text());assert not targets&allpaths(md)
review=E/'INDEPENDENT-SOURCE-ABI-ACCEPTANCE.ROOT-RECORD.json';reviewdata=json.loads(review.read_text());assert reviewdata['verdict']=='PASS_PRIVATE_SET_TIMER_SOURCE_ABI_AND_ACTUAL_RUST_OBJECT_CONSUMER_ONLY'
report=dict(scope=bind.get('scope'),status='PASS_PREPARATION_ONLY_NO_CANONICAL_WRITES',canonical_preimages=pre,old_LONG_owner=pin(owner),SOURCE_HASHES_count=156,SOURCE_HASHES_paths=sorted(sourcehashes),three_targets_absent_from_156=True,query_input_binding=pin(query_path),query_pins_count=len(query['pins']),cohort_binding=pin(cohort_path),selected_transitive_authority_proof_reads=selected,selected_authority_readset_target_intersection=[],runtime_manifest=pin(manifest),serialized_release=pin(release),runtime_manifest_target_intersection=[],query_target_intersection=[],cohort_target_intersection=[],independent_review=pin(review),qualification='Read-only source dependency/overlap preparation. No lifecycle/retirement/lease conclusion; root retains physical review and integration authority.')
write('INTEGRATION-PREPARATION-CHECK.json',report)
worklist=R/'docs/verification/os-milestones-20260914/rust-cutover-m14.json';w=json.loads(worklist.read_text())
write('M14-PARTIAL-APPEND.PROPOSED.NOT-APPLIED.json',dict(scope=bind['scope'],status='PROPOSAL_ONLY_AFTER_ROOT_CANONICAL_INTEGRATION',worklist_preparation_identity=pin(worklist),file_id='M14-F02',subgoal_id='M14-02-04',subgoal_title='Runqueue selection, wakeups, idle transitions, migration/affinity and post-switch release sequencing.',preserve_existing_subgoal_status='partial',preserve_existing_idle_defaultlink_evidence=True,append_implementation_evidence=dict(path='docs/verification/evidence/compute-process-next-body-cutover-20261023-1/CANONICAL-INTEGRATION.ROOT-RECEIPT.json',scope='After exact root integration only: set_timer public C orchestration wrapper moved into existing Rust scheduler/timer body; exact C fallback and4Cprimitive callbacks retained. Bounded partial slice only.'),append_focused_evidence=[dict(path='docs/verification/evidence/compute-process-next-body-cutover-20261023-1/ACTUAL-LEAF-RECEIPT.json',sha256='1b1d55a3bc57d3122607dc026b29c446a244977130597c5480f2541ab93241d7',scope='25750 actual originalC/Rust wrapper/state/callback comparisons and realheaderABI; host fixture only.'),dict(path='docs/verification/evidence/compute-process-next-body-cutover-20261023-1/ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json',sha256='7f2e8d83fe83067e64cdd6628cfb6dcc704d3ff99ef2c5d763faef9afe5969d3',scope='Exact78input productionRust object; Tset_timer/noUset_timer, exact5providerimports and existingmemoryexports; observer-only correction preserved; no wholeC/defaultkernel/native.')],new_slice_production_link='OPEN',new_slice_native='OPEN',wholefile_retirement_credit=False,do_not_replace_existing_rust_consumer='Keep idle consumer and append sched_helpers.rs::set_timer as another partial consumer.'))
write('CANONICAL-INTEGRATION.RECEIPT-TEMPLATE.NOT-EXECUTED.json',dict(scope=bind['scope'],status='NOT_EXECUTED_TEMPLATE',execution_owner='/root',source_bindings=pin(P/'SOURCE-BINDINGS.json'),independent_review=pin(review),preparation=pin(P/'INTEGRATION-PREPARATION-CHECK.json'),expected_preimages=bind['source_inputs'],expected_postimages={rel:dict(path=bind['source_inputs'][rel]['path'],sha256=row['sha256'],bytes=row['bytes']) for rel,row in bind['outputs'].items()},actual_preimages=None,actual_postimages=None,canonical_files_written=None,whole_C_TU_default_link_native='OPEN',worklist_updated=False))
for name in ['prepare_integration_handoff.py','INTEGRATION-PREPARATION-CHECK.json','M14-PARTIAL-APPEND.PROPOSED.NOT-APPLIED.json','CANONICAL-INTEGRATION.RECEIPT-TEMPLATE.NOT-EXECUTED.json']:shutil.copyfile(P/name,E/name)
print(json.dumps(dict(preparation=pin(P/'INTEGRATION-PREPARATION-CHECK.json'),proposal=pin(P/'M14-PARTIAL-APPEND.PROPOSED.NOT-APPLIED.json'),transitive_authority_read_count=len(selected),target_intersection=[])))
