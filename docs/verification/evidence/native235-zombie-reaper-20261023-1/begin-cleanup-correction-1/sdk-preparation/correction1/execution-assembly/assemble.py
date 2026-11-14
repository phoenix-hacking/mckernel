"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical descendant of accepted9850 SDK assembly. No execution authority.
"""
from pathlib import Path
import ast
import hashlib
import json
import os

D = Path(__file__).resolve().parent
R = Path('/home/holden/mckernel')
B = Path('/home/holden/mckernel-work/host-preparation/native235-begin-cleanup-sdk-successor-20261023-2')
A = B / 'release-assembly'
OLD = Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/release-assembly')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
REQUEST_SHA = '92aec46808cd40fa5d468e01f4b9b8f657dc8c14792444c4834030889fa2ac08'
NONCE = '56d2c74a5e4f44298f0d2d2c96b7e6bf'

def load(path):
    return json.loads(path.read_text())

def ref(path, expected=None):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected:
        assert digest == expected, (str(path), digest, expected)
    return dict(path=str(path), sha256=digest, bytes=len(data))

def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    path.chmod(0o600)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'

def bytes_once(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(0o600)

def main():
    assert os.sched_getaffinity(0) == {6}
    req = ref(B / 'request.json', REQUEST_SHA)
    request = load(B / 'request.json')
    assert request['nonce'] == NONCE and request['request_path'] == req['path']
    assert request['backing_identity']['size'] == 110 * 2**30
    cohort = load(B / 'RUNTIME-COHORT.json')
    assert len(cohort) == 11
    for row in cohort.values():
        assert ref(Path(row['path']), row['sha256'])['bytes'] == row['bytes']
    source_sha = {name: row['sha256'] for name, row in cohort.items()}
    # This review is a transcription of the exact genuine independent message,
    # retained verbatim by the dispatcher; never generated from an implementation PASS.
    review_input = ref(D / 'INDEPENDENT-SOURCE-REVIEW.INPUT.json',
        'a7275994b90c51ad9af1b9eb1d1ee631df62219de65d30aed9e1b817974a8f29')
    review = load(D / 'INDEPENDENT-SOURCE-REVIEW.INPUT.json')
    assert review['status'] == 'PASS' and review['decision'] == 'PASS_SOURCE_SDK_SUCCESSOR_PREPARATION_AND_CONDITIONAL_BUILD_PROFILE'
    assert review['reviewer'] == '/root/p12_identity_review' and review['implementation_ownership'] is False
    assert review['source_sha256'] == source_sha
    assert review['request_sha256'] == REQUEST_SHA
    assert review['execution_authorized'] is False
    review = dict(review, decision='PASS_SOURCE', independent_review_input=review_input,
                  original_independent_decision=review['decision'])
    actual_tests = D.parents[2] / 'actual-tests/ACTUAL-RESULT.json'
    # Bind the actual six-test evidence, not a new test or native acceptance claim.
    tests_ref = ref(actual_tests, 'dde47cfef6fb1f57f8220c4dff672be71d1a83f3db45fc139f38c1a20a6d0c29')
    assert load(actual_tests)['actual_tests'] == 6 and load(actual_tests)['status'] == 'ACTUAL_BODY_TESTS_PASS'
    A.mkdir(mode=0o700, exist_ok=False)
    write(A / 'ROOT-INDEPENDENT-SOURCE-REVIEW.json', review)
    base = load(OLD / 'RELEASE-PAYLOAD.PROPOSED.json')
    payload = {key: base[key] for key in ('schema', 'author', 'execution_count', 'historical_observer')}
    payload.update(status='PROPOSED_PAYLOAD_NOT_EXECUTION_RELEASE', boot_id=request['boot_id'],
                   nonce=NONCE, terminal_policy=request['terminal_policy'],
                   request=dict(path=req['path'], sha256=req['sha256']), source_sha256=source_sha,
                   source_review=ref(A / 'ROOT-INDEPENDENT-SOURCE-REVIEW.json'),
                   fetched_source_verified=False, current_Git_fetched_proof=None,
                   current_live_postjoin=None, latest_heavy_physical_acceptance=None,
                   dispatcher_preinvoke_measurement=None,
                   actual_source11_identity_readback=dict(dataset=ref(B / 'RUNTIME-COHORT.json'),
                                                        canonical_guard_result=ref(B / 'PURE-PREPARATION-VALIDATION.json')))
    assert payload['terminal_policy'] == 'remove-owned-terminal'
    operation = load(OLD / 'OPERATION-EXACT-REQUEST.TEMPLATE.json')
    owner = cohort['scripts/native_running_external_modules_owner.py']['path']
    code = "import sys,runpy; sys.path.insert(0,'/home/holden/mckernel/scripts'); runpy.run_path(" + repr(owner) + ",run_name='__main__')"
    argv = operation['argv']
    assert argv[argv.index('-I') + 2] == '-c'
    argv[argv.index('-I') + 3] = code
    argv[argv.index('--request') + 1] = req['path']
    argv[argv.index('--request-sha256') + 1] = req['sha256']
    argv[argv.index('--release') + 1] = str(A / 'release.json')
    assert argv[argv.index('--release-sha256') + 1] == 'ACTUAL_FINAL_RELEASE_SHA256'
    operation.update(actual_nonce=NONCE, actual_release=str(A / 'release.json'),
                     capture_directory=str(A / 'owner-capture-1'), execution_review=None,
                     status='EXACT_SUCCESSOR_REQUEST_PENDING_REVIEW_RELEASE')
    write(A / 'OPERATION-EXACT-REQUEST.TEMPLATE.json', operation)
    capture = Path(base['outer_capture']['source']['path'])
    capture_ref = ref(capture, 'f64dc4118fb7416d0d11eb4501778d4b7416bfef169be432f5b4be114d322e8d')
    payload['outer_capture'] = dict(source=dict(path=capture_ref['path'], sha256=capture_ref['sha256']),
        operation_template=ref(A / 'OPERATION-EXACT-REQUEST.TEMPLATE.json'),
        mechanical_finalization=base['outer_capture']['mechanical_finalization'])
    bytes_once(A / 'RELEASE-PAYLOAD.PROPOSED.CANONICAL.json', canonical(payload))
    write(A / 'RELEASE-PAYLOAD.PROPOSED.json', payload)
    write(A / 'OUTER-CAPTURE-ARGV.TEMPLATE.json', ['/usr/bin/taskset', '-c', '7',
        '/home/holden/anaconda3/bin/python3', '-I', '-B', str(capture), '--operation',
        str(A / 'operation.json'), '--sha256', 'ACTUAL_FINAL_OPERATION_SHA256'])
    input_map = load(B / 'CURRENT68-BEGIN-CLEANUP-INPUT-MAP.json')
    predecessor = load(Path(input_map['predecessor_preparation']['path']))
    prior = {row['path']: row for row in predecessor['closure']}
    changed_names = set(input_map['changed_relative_rows'])
    assert changed_names == {'abi/application.rs', 'ihk_smp_x86_64.rs', 'smp_service.rs', 'smp_application.rs', 'mcctrl_process.rs'}
    reused = []
    changed = []
    for row in input_map['rows']:
        name = row['relative']
        source = row['source']
        if name in changed_names:
            origin = D.parents[2] / ('consumer' if name == 'mcctrl_process.rs' else 'provider') / name
            publication_ref = ref(origin, source['sha256'])
            assert publication_ref['bytes'] == source['bytes']
            changed.append(dict(relative=name, private_source=source, existing_repository_source=publication_ref))
        else:
            assert source['sha256'] == prior[name]['sha256'] and source['bytes'] == prior[name]['bytes']
            reused.append(dict(relative=name, sha256=source['sha256'], bytes=source['bytes'],
                               accepted_preparation=input_map['predecessor_preparation'], accepted_origin=prior[name]['origin']))
    assert len(reused) == 63 and len(changed) == 5
    write(A / 'REUSED-63-ACCEPTED-SOURCE-REFERENCES.json', dict(
        status='63_UNCHANGED_ACCEPTED9850_SOURCE_REFERENCES_NO_NEW_COPIES', rows=reused))
    pending = dict(scope=SCOPE, status='REFUSED_EXECUTION_PENDING_REAL_P12_RETIREMENT_AND_FRESH_ROOT_BINDINGS',
        p12_retirement=None, retained_python_pid=3502879, latest_heavy_physical_acceptance=None,
        current_live_postjoin=None, dispatcher_preinvoke_measurement=None,
        current_Git_fetched_proof=None, fetched_source_verified=False, execution_review=None,
        qualifications='No physical PASS or final release is inferred from the staged request, source review or ordinary tests.',
        next_root_steps=['positive independent P12 physical retirement evidence',
                         'fresh live root resource/identity/lease observations under accepted guards',
                         'checkpoint and verify exact published source blobs fetched from GitHub',
                         'bind those real refs and set final proposed payload status PASS_EXECUTION_RELEASE',
                         'independent PASS_EXECUTION for exact canonical payload digest excluding execution_review',
                         'write final release.json; bind its hash in operation.json; hash operation and invoke accepted capture once'])
    write(A / 'PENDING-EXECUTION-DEPENDENCIES.json', pending)
    refs = [(B / 'derived-runtime' / name, 'derived-runtime/' + name) for name in (
        'native_running_external_modules_owner.py', 'native_running_external_modules_offline.py')]
    refs += [(B / name, name) for name in ('request.json', 'preparation.json',
        'CURRENT68-BEGIN-CLEANUP-INPUT-MAP.json', 'RUNTIME-COHORT.json', 'PURE-PREPARATION-VALIDATION.json', 'staging-once/result.json')]
    refs += [(A / name, name) for name in ('ROOT-INDEPENDENT-SOURCE-REVIEW.json',
        'OPERATION-EXACT-REQUEST.TEMPLATE.json', 'RELEASE-PAYLOAD.PROPOSED.CANONICAL.json',
        'RELEASE-PAYLOAD.PROPOSED.json', 'OUTER-CAPTURE-ARGV.TEMPLATE.json',
        'REUSED-63-ACCEPTED-SOURCE-REFERENCES.json', 'PENDING-EXECUTION-DEPENDENCIES.json')]
    publication = []
    for source, name in refs:
        dest = D / 'retained' / name
        bytes_once(dest, source.read_bytes())
        private_ref = ref(source)
        publication_ref = ref(dest)
        assert private_ref['sha256'] == publication_ref['sha256']
        publication.append(dict(private=private_ref, publication=publication_ref))
    publication_map = dict(scope=SCOPE, status='EXACT_SMALL_SUCCESSOR_COPIES_PENDING_ROOT_GIT_FETCHED_PROOF',
        selected=publication, changed_five_existing_repository_sources=changed,
        reused63=ref(A / 'REUSED-63-ACCEPTED-SOURCE-REFERENCES.json'), actual_tests=tests_ref,
        git_commit=None, fetched_proof=None, private_execution_paths_preserved=True, large_archive_copies=0)
    write(D / 'EXACT-SMALL-PUBLICATION-MAP.json', publication_map)
    result = dict(scope=SCOPE, status='EXACT_ASSEMBLY_READY_REFUSED_PENDING_PHYSICAL_AND_EXECUTION_RELEASE',
        request=req, source_identity=input_map['source_identity'], source_review=ref(A / 'ROOT-INDEPENDENT-SOURCE-REVIEW.json'),
        release_payload=ref(A / 'RELEASE-PAYLOAD.PROPOSED.CANONICAL.json'),
        operation=ref(A / 'OPERATION-EXACT-REQUEST.TEMPLATE.json'),
        capture_argv=ref(A / 'OUTER-CAPTURE-ARGV.TEMPLATE.json'),
        publication_map=ref(D / 'EXACT-SMALL-PUBLICATION-MAP.json'), runtime_cohort=source_sha,
        pending_dependencies=ref(A / 'PENDING-EXECUTION-DEPENDENCIES.json'), author='/root',
        execution_review=None, p12_retirement=None, compiler_operations=0, root_Docker_guest_operations=0)
    write(A / 'ASSEMBLY-RESULT.json', result)
    write(D / 'ASSEMBLY-RESULT.json', result)
    print(json.dumps(dict(status=result['status'], request=req, source_review=result['source_review'],
                         publication_copies=len(publication), reused_source_refs=len(reused),
                         final_release_written=False, p12_retirement=None)))

if __name__ == '__main__':
    main()
