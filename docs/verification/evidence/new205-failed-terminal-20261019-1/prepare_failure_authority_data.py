"""Bind genuine retained output into failure-only DATA; never grants authority."""
from pathlib import Path
import argparse
import hashlib
import json

F = Path(__file__).resolve().parent
A = F.parent
H = A / 'heavy-proposal-1'
GUARD = Path('/home/holden/mckernel-work/scratch/native-rust-four-callback-affinity-image-guard-bc32500028be40a09ce651f20ade82d4')
REVIEW = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-heavy-review-20261019-1/NEW205-ACTUAL-FAILED-BUILD-AND-CLIENT-RETIREMENT-REVIEW.json')

def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def main(options):
    request = json.loads((A / 'image-request.json').read_bytes())
    sources = json.loads((H / 'source-sha256.json').read_bytes())
    inputs = json.loads((F / 'failed-operation-source-references.json').read_bytes())
    status = json.loads(options.retention_status.read_bytes())
    assert status['returncode'] == 0 and status['direct_child_joined'] is True
    pairs = F / 'retained-production-objects/retained-objects.json'
    result = F / 'retained-production-objects/result.json'
    assert len(json.loads(pairs.read_bytes())) == 12
    outcome = json.loads(result.read_bytes())
    assert outcome['status'] == 'PASS_FINITE_EXACT_RETENTION_ONLY' and outcome['pairs'] == 12 and outcome['artifact_acceptance'] is False and outcome['cleanup_authorized'] is False
    assert outcome['source_release_sha256'] == ref(options.retention_release)['sha256']
    source11 = dict(count=11, source11ref=ref(H / 'source-sha256.json'), request=ref(A / 'image-request.json'), materialization=ref(A / 'materialization-receipt.json'), fullsource=ref(Path(request['source_manifest'])), additional_dispatcher=sources['additional_dispatcher'], toolchain=ref(Path(request['toolchain_manifest'])), provenance=inputs['provenance'], host_owner=request['host_owner_path'], host_owner_sha256=request['host_owner_sha256'])
    actual12 = dict(sources['source_sha256'])
    additional = sources['additional_dispatcher']
    assert len(actual12) == 11 and source11['host_owner'] in actual12 and additional['path'] not in actual12
    actual12[additional['path']] = additional['sha256']
    guards = [path for path in actual12 if path.endswith('native_exact_scratch22_authority3_image_guard_corrected.py')]
    assert len(guards) == 1
    physical = json.loads((F / 'actual-failed-physical-bindings.json').read_bytes())
    data = dict(schema='mckernel.independent-rust-image-failed-build-preservation-authority.v1', decision='NOT_RELEASED_PENDING_INDEPENDENT_FAILURE_PRESERVATION_AUTHORITY', reviewer=None, implementation_author='/root/clone_thread_affinity_rust_repair', implementation_ownership=True, owner_receipt=ref(A / 'owner-evidence/owner-receipt.json'), guard_result=ref(GUARD / 'guard-result.json'), guard_source=ref(Path(guards[0])), current_retirement_review=ref(REVIEW), mutex_postjoin=ref(H / 'failure-mutex-postjoin-readback-1.json'), source11=source11, actual_control_source12=actual12, original_log_authorities=ref(F / 'failed-log-original-authorities.json'), retained_logs=dict(pairs=ref(pairs), release=ref(options.retention_release), result=ref(result), direct_join=ref(options.retention_status), independent_actual_review=ref(options.retention_review)), actual_failed_log_roles=json.loads((F / 'failed-log-original-authorities.json').read_bytes()), ownership=dict(common=physical['common'], shared=physical['shared'], lease_path=str(A / 'image-lease.json'), lease_absent=True), target=physical['target'], required_preserved_directories=[str(A / 'owner-work/output/build'), str(A / 'owner-work/evidence')], retention_scope='Twelve exact failed-log copies only; full host case and partial build remain in place.', production_image_acceptance=False, native_acceptance=False, compute_C_retirement=False, cleanup_authorized=False, physical_release=False, root_authority=False)
    with (F / 'FAILED-BUILD-PRESERVATION-AUTHORITY-DRAFT.json').open('x') as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print('PREPARED_ACTUAL_FAILURE_AUTHORITY_DATA_NOT_RELEASED pairs=12 actualcontrol=12 source11=11')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--retention-status', required=True, type=Path)
    parser.add_argument('--retention-release', required=True, type=Path)
    parser.add_argument('--retention-review', required=True, type=Path)
    main(parser.parse_args())
