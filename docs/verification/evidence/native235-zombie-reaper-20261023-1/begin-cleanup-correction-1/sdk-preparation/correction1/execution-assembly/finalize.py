"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind real dispatcher evidence, then mechanically append genuine execution review.
Neither phase executes the SDK owner, capture wrapper, root tools or Git.
"""
from pathlib import Path
import argparse
import hashlib
import json

D = Path(__file__).resolve().parent
R = Path('/home/holden/mckernel')
A = Path('/home/holden/mckernel-work/host-preparation/native235-begin-cleanup-sdk-successor-20261023-2/release-assembly')
P = R / 'docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/none-attach-smoke-1/actual-post-recovery-physical-1'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ref(path):
    return dict(path=str(path), sha256=digest(path), bytes=path.stat().st_size)

def bound(value):
    path = Path(value['path'])
    assert path.is_absolute() and path.resolve() == path and path.is_file()
    assert digest(path) == value['sha256'], str(path)
    return json.loads(path.read_text())

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'

def save(path, value, compact=False):
    with path.open('xb') as stream:
        stream.write(canonical(value) if compact else (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    path.chmod(0o600)

def bind(args):
    inputs = bound(dict(path=str(args.bindings), sha256=args.sha256))
    assert set(inputs) == {'current_Git_fetched_proof', 'dispatcher_preinvoke_measurement'}
    assembly = json.loads((A / 'ASSEMBLY-RESULT.json').read_text())
    payload = bound(assembly['release_payload'])
    assert payload['status'] == 'PROPOSED_PAYLOAD_NOT_EXECUTION_RELEASE'
    assert payload['nonce'] == '56d2c74a5e4f44298f0d2d2c96b7e6bf'
    assert payload['request']['sha256'] == '92aec46808cd40fa5d468e01f4b9b8f657dc8c14792444c4834030889fa2ac08'
    bound(payload['request'])
    physical_ref = dict(path=str(P / 'INDEPENDENT-ACTUAL-PHYSICAL-ACCEPTANCE.json'),
                        sha256='f9de28cc96d30b65fc1967607d6420023fbb016ed84995b37cae0b8bd5279791')
    physical = bound(physical_ref)
    assert physical['status'] == 'PASS_ACTUAL_FAILED_NONE_SMOKE_PHYSICAL_RETIREMENT'
    assert physical['decision'] == 'PASS_PHYSICAL' and physical['reviewer'] == '/root/p12_successor_review'
    assert physical['absence_verified'] is True and physical['lease_retained'] is False
    assert physical['application_acceptance'] is False and physical['owner_and_anchor_positive_ENOENT'] is True
    assert physical['complete_proc_publishers'] == [] and physical['eight_path_absence'] is True
    assert physical['permanent_mutex_identity'] == [27, 4] and physical['null_lost_statuses_preserved'] == 37
    live_ref = dict(path=str(P / 'CURRENT-LIVE-POSTJOIN.json'),
                    sha256='e9d5494affa3ea9d1ebfc3a0199efc86d094e37043d90744ae2accd63852cabd')
    live = bound(live_ref)
    assert live['status'] == 'PASS_CURRENT_LIVE_POSTJOIN'
    assert live['physical_acceptance']['sha256'] == physical_ref['sha256']
    assert live['physical_observations_ended_before_record'] is True
    fetched = bound(inputs['current_Git_fetched_proof'])
    assert inputs['current_Git_fetched_proof']['sha256'] == 'ae91947f33efc5d183fe69345c635ecc2d5e9072a634abb82f55504b3958f1e4'
    assert fetched['status'] == 'PASS_FETCHED_BLOB_VERIFICATION'
    assert fetched['commit'] == fetched['fetched_commit'] == '34c22cd50f87383be20b31e30fbfba25e31a19f1'
    assert fetched['count'] == len(fetched['verified_changed_blobs']) == 409
    actual = {row['path']: row['git_blob'] for row in fetched['verified_changed_blobs']}
    publication = json.loads((D / 'EXACT-SMALL-PUBLICATION-MAP.json').read_text())
    expected = [row['publication'] for row in publication['selected']]
    expected += [row['existing_repository_source'] for row in publication['changed_five_existing_repository_sources']]
    for row in expected:
        relative = str(Path(row['path']).relative_to(R))
        data = Path(row['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256'] and len(data) == row['bytes'], relative
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual.get(relative) == blob, relative
    measurement = inputs['dispatcher_preinvoke_measurement']
    assert set(measurement) == {'observed_unix', 'host_available', 'scratch_available', 'memory_available',
        'full_backing_gap', 'host_required_full_growth_and4GiBbuildpluscampaign', 'active_heavy_owner', 'admission'}
    for key in ('observed_unix', 'host_available', 'scratch_available', 'memory_available',
                'full_backing_gap', 'host_required_full_growth_and4GiBbuildpluscampaign'):
        assert isinstance(measurement[key], (int, float)) and measurement[key] >= 0
    assert measurement['host_available'] >= measurement['host_required_full_growth_and4GiBbuildpluscampaign']
    assert measurement['scratch_available'] >= 12 * 2**30 and measurement['memory_available'] >= 12 * 2**30
    assert measurement['active_heavy_owner'] == 'none since independently accepted P12 failed-smoke retirement'
    assert '27:4' in measurement['admission']
    payload.update(status='PASS_EXECUTION_RELEASE', latest_heavy_physical_acceptance=physical_ref,
        current_live_postjoin=live_ref, current_Git_fetched_proof=inputs['current_Git_fetched_proof'],
        fetched_source_verified=True, dispatcher_preinvoke_measurement=measurement)
    # This is the review payload only; no release.json exists until independent PASS_EXECUTION.
    save(A / 'FINAL-PAYLOAD.CANONICAL.json', payload, compact=True)
    save(D / 'FINAL-PAYLOAD.CANONICAL.json', payload, compact=True)
    result = dict(scope=SCOPE, status='REAL_BINDINGS_COMPLETE_PENDING_EXACT_EXECUTION_REVIEW',
        bindings=ref(args.bindings), physical_acceptance=physical_ref, current_live_postjoin=live_ref,
        final_review_payload=ref(A / 'FINAL-PAYLOAD.CANONICAL.json'), final_release_written=False)
    save(D / 'FINAL-BINDING-RESULT.json', result)
    print(json.dumps(result, sort_keys=True))

def finalize(args):
    record = json.loads((D / 'FINAL-BINDING-RESULT.json').read_text())
    payload_ref = record['final_review_payload']
    payload = bound(payload_ref)
    assert canonical(payload) == Path(payload_ref['path']).read_bytes()
    review_ref = dict(path=str(args.execution_review), sha256=args.sha256)
    review = bound(review_ref)
    assert review['status'] == 'PASS' and review['decision'] == 'PASS_EXECUTION'
    assert review['implementation_ownership'] is False and review['reviewer'] != payload['author']
    assert review['reviewed_release_payload_sha256'] == payload_ref['sha256']
    assert 'execution_review' not in payload
    release = dict(payload, execution_review=review_ref)
    save(A / 'release.json', release, compact=True)
    operation = bound(payload['outer_capture']['operation_template'])
    argv = operation['argv']
    index = argv.index('--release-sha256') + 1
    assert argv[index] == 'ACTUAL_FINAL_RELEASE_SHA256'
    argv[index] = digest(A / 'release.json')
    operation['execution_review'] = review_ref
    # Preserve every other accepted operation field/profile exactly.
    save(A / 'operation.json', operation)
    capture = payload['outer_capture']['source']
    assert digest(Path(capture['path'])) == capture['sha256']
    capture_argv = json.loads((A / 'OUTER-CAPTURE-ARGV.TEMPLATE.json').read_text())
    assert capture_argv[capture_argv.index('--sha256') + 1] == 'ACTUAL_FINAL_OPERATION_SHA256'
    capture_argv[capture_argv.index('--sha256') + 1] = digest(A / 'operation.json')
    save(A / 'LAUNCH-ARGV.json', capture_argv)
    result = dict(scope=SCOPE, status='FINALIZED_EXACT_REVIEWED_PACKET_NOT_EXECUTED',
        release=ref(A / 'release.json'), operation=ref(A / 'operation.json'),
        execution_review=review_ref, launch_argv=capture_argv,
        warning='Launch as a separate dispatcher command with accepted inherited unlimited CPU profile; do not inherit this metadata CPU30/wall35 limit.')
    save(D / 'FINALIZATION-RESULT.json', result)
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--bindings', type=Path)
    group.add_argument('--execution-review', type=Path)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    bind(args) if args.bindings else finalize(args)
