from pathlib import Path
import json,hashlib
T=Path(__file__).resolve().parent;N=T.parent;OLD=Path('/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1')
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
p=T/'known-terminal-inputs.json';known=json.loads(p.read_text())
known['configurator']=ref(OLD/'configure_fourleaf_terminal.py')
oldphysical=json.loads((OLD/'actual-fourleaf-physical-bindings.json').read_text());known['predecessor_guard_name']=Path(oldphysical['guard']['path']).parent.name
prep=json.loads((N/'heavy-proposal-1/actual-preparation-bindings.json').read_text());known['materialization_receipt']=prep['materialization_receipt'];known['actual_source_manifest']=prep['actual_source_manifest']
for name in ['terminal_contract.py','postbuild_future_facts.py','configure_late_terminal.py','future_stage_case.py','prepare_adapters.py','finalize_known.py']:
 r=ref(T/name);known['full_import_closure'][r['path']]=r['sha256']
known['full_import_closure'][known['configurator']['path']]=known['configurator']['sha256']
known['preserved_tests']=dict(status='REUSE_ACCEPTED_UNAFFECTED_39_NOT_REEXECUTED',cleanup_fixture_cases=23,source=ref(Path('/home/holden/mckernel/scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py')),new_affected_fixture_only=True)
known['typed_canonical_addition']=dict(field='future_four_callbacks',facts_schema='mckernel.future-four-callback.postbuild-additive-facts.v1',arg_indices_source_zero_based=[8,9,10,17],machine_slot_decoding_claim=False,fixed_parent_schema='mckernel.independent-rust-four-leaf-image-actual-review.v1')
p.write_text(json.dumps(known,sort_keys=True,indent=2)+'\n')
print('KNOWN source11/full closure complete; explicit author/caps/additive schema/materialization refs; only genuine runtime facts pending')
