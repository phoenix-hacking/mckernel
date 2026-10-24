"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One finite private BFD publisher. Actual root execution requires separate release.
Import defines pure approval checks only; main is the sole publication entrypoint.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

D = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
OWNER_SHA = '71381de806c21b7487e1515927543b376199a021a08b965a60d68063241bc794'
HELPER_SHA = '76ff839a839a2f55cd7d537d22221cb1b053390e2b6052b8be2b5d8b20990e63'
PROFILE_SHA = 'e25bec3d2864245092c4202e6ce05c20e00ea8914e8a932eacd19f7a3f3e159a'
REVIEWER = '/root/native235_release_review'

def need(value, message):
    if not value:
        raise ValueError(message)

def document_bytes(value):
    # Match the accepted owner's _exclusive_json serialization exactly.
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def document_digest(value):
    return hashlib.sha256(document_bytes(value)).hexdigest()

def read_bound_json(path, expected):
    path = Path(path)
    need(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected), 'exact input digest required')
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical input path required')
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 32 << 20,
         'bounded regular single-link input required')
    raw = path.read_bytes()
    after = path.lstat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    need(all(getattr(before, key) == getattr(after, key) for key in fields) and
         len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == expected,
         'input digest/identity differs')
    result = json.loads(raw)
    need(isinstance(result, dict), 'input must be an object')
    return result

def expected_payload(root, profile, request, facts, bindings, refs, release_template):
    """The one exact BFD owner operation; no executable variants or review cycle."""
    a = root / 'ROOT-ADMISSION.json'
    r = root / 'ROOT-RELEASE.json'
    released = root / 'compile-request.RELEASED.json'
    aref = {'path': str(a), 'sha256': document_digest(facts)}
    release = dict(release_template)
    need(release.pop('_template_only_no_authority', None) is True, 'retained release template required')
    need(release.get('status') == 'RELEASED_FOR_ONE_COMPILE_ONLY_M15_BFD', 'fixed release status required')
    release['request_core_sha256'] = facts['request_core_sha256']
    release['independent_source_review_sha256'] = refs['source_review']['sha256']
    release['root_admission'] = aref
    rref = {'path': str(r), 'sha256': document_digest(release)}
    final_request = dict(request, compile_only_release=rref)
    owner_argv = ['/usr/bin/taskset', '-c', '0', '/usr/bin/prlimit',
        '--as=2147483648:2147483648', '--cpu=unlimited:unlimited', '--fsize=33554432:33554432',
        '--nofile=256:256', '--core=0:0', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B',
        str(root / 'compile_image_owner.py'), 'run', str(released)]
    return {'schema': 'mckernel.m15-bfd-exact-execution-payload.v1', 'scope': SCOPE,
        'operation': profile['operation'], 'bindings': bindings, 'request_core_sha256': facts['request_core_sha256'],
        'request_candidate': refs['request'], 'admission_candidate': refs['query'],
        'query_outer_wholejoin': refs['joined'], 'owner_source_approval': refs['source_review'],
        'container': {'image_id': profile['image_id'], 'limits': profile['limits'], 'jobs': 1,
                      'exact_inner_argv': request['exact_command'], 'mounts_bound_by_profile_sha256': bindings['profile_sha256']},
        'owner_run_argv': owner_argv,
        'publication': {'admission': {'reference': aref, 'document': facts},
                        'release': {'reference': rref, 'document': release},
                        'request': {'reference': {'path': str(released), 'sha256': document_digest(final_request)},
                                    'document': final_request}}}

def authorize(source_review, execution_review, payload, expected, payload_ref, fresh):
    """Both real PASS decisions and their exact byte/source/request joins precede effects."""
    source_keys = {'schema', 'scope', 'status', 'reviewer', 'implementation_ownership', 'bindings'}
    need(isinstance(source_review, dict) and set(source_review) == source_keys and
         source_review['schema'] == 'mckernel.m15-bfd-owner-source-approval.v1' and
         source_review['scope'] == SCOPE and source_review['status'] == 'PASS' and
         source_review['reviewer'] == REVIEWER and source_review['implementation_ownership'] is False,
         'actual independent source PASS required')
    source_bindings = {key: expected['bindings'][key] for key in ('owner_sha256', 'helper_sha256', 'profile_sha256')}
    need(source_review['bindings'] == source_bindings, 'approved source/profile/helper differs')
    execution_keys = {'schema', 'scope', 'status', 'reviewer', 'implementation_ownership', 'bindings',
                      'request_core_sha256', 'source_review_sha256', 'payload_sha256'}
    need(isinstance(execution_review, dict) and set(execution_review) == execution_keys and
         execution_review['schema'] == 'mckernel.m15-bfd-execution-approval.v1' and
         execution_review['scope'] == SCOPE and execution_review['status'] == 'PASS' and
         execution_review['reviewer'] == REVIEWER and execution_review['implementation_ownership'] is False,
         'actual independent execution PASS required')
    need(execution_review['bindings'] == expected['bindings'] and
         execution_review['request_core_sha256'] == expected['request_core_sha256'] and
         execution_review['source_review_sha256'] == expected['owner_source_approval']['sha256'],
         'execution source/profile/publisher/request approval differs')
    need(isinstance(payload_ref, dict) and set(payload_ref) == {'path', 'sha256'} and
         isinstance(payload_ref['sha256'], str) and re.fullmatch('[0-9a-f]{64}', payload_ref['sha256']) and
         execution_review['payload_sha256'] == payload_ref['sha256'], 'approved exact payload digest differs')
    need(payload == expected, 'approved exact execution payload differs')
    # Call the accepted owner's real same-boot, <=120s and fresh24GiB consumer.
    # This occurs before the first root document can be published.
    fresh(expected['publication']['admission']['document'])
    return expected['publication']

def main():
    need(os.getuid() == os.geteuid() == 0 and os.sched_getaffinity(0) == {7}, 'root CPU7 publisher required')
    need(len(sys.argv) == 11, 'ten exact publication inputs required')
    owner_path = D / 'compile_image_owner.py'
    need(hashlib.sha256(owner_path.read_bytes()).hexdigest() == OWNER_SHA, 'accepted owner changed')
    need(hashlib.sha256((D / 'compile_host_helper.py').read_bytes()).hexdigest() == HELPER_SHA and
         hashlib.sha256((D / 'COMPILE-PROFILE.json').read_bytes()).hexdigest() == PROFILE_SHA,
         'accepted helper/profile changed')
    spec = importlib.util.spec_from_file_location('bfd_compile_owner_finalization', owner_path)
    o = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = o
    spec.loader.exec_module(o)
    capture = D / 'admission-preparation-1/actual-readonly-query-1'
    refs = {'query': {'path': str(capture / 'ROOT-ADMISSION.CANDIDATE.json'), 'sha256': sys.argv[1]},
            'request': {'path': str(capture / 'REQUEST.FINALIZED.UNRELEASED.CANDIDATE.json'), 'sha256': sys.argv[2]},
            'review': {'path': sys.argv[3], 'sha256': sys.argv[4]},
            'source_review': {'path': sys.argv[5], 'sha256': sys.argv[6]},
            'joined': {'path': sys.argv[7], 'sha256': sys.argv[8]},
            'payload': {'path': sys.argv[9], 'sha256': sys.argv[10]}}
    documents = {key: read_bound_json(ref['path'], ref['sha256']) for key, ref in refs.items()}
    whole = documents['joined']
    need(whole.get('returncode') == 0 and whole.get('direct_child_joined') is True and
         whole.get('group_absent') is True and whole.get('closed_streams') is True and
         whole.get('error') is None and whole.get('retirement_error') is None, 'actual query outer wholejoin required')
    facts, request = documents['query'], documents['request']
    o._validate_compile_domain(request)
    need(request.get('compile_only_release') is None and facts.get('request_core_sha256') == o._request_core_hash(request),
         'exact unreleased request/core required')
    need(facts.get('profile_sha256') == PROFILE_SHA and facts.get('operation') == o.COMPILE_PROFILE['operation'] and
         facts.get('schema') == 'mckernel.m15-bfd-dual-container-admission.v1' and
         facts.get('capacity_verdict') == 'PASS_DUAL_CONTAINER_COMPILE_CPU6_2G' and
         '_template_only_no_authority' not in facts, 'actual fixed BFD admission required')
    bindings = {'owner_sha256': OWNER_SHA, 'helper_sha256': HELPER_SHA, 'profile_sha256': PROFILE_SHA,
                'publisher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    template = json.loads((D / 'ROOT-RELEASE.TEMPLATE.json').read_text())
    need(template.get('owner_sha256') == OWNER_SHA and template.get('host_helper_sha256') == HELPER_SHA and
         template.get('profile_sha256') == PROFILE_SHA and template.get('operation') == o.COMPILE_PROFILE['operation'],
         'retained release template source/profile bindings differ')
    expected = expected_payload(D, o.COMPILE_PROFILE, request, facts, bindings, refs, template)
    publication = authorize(documents['source_review'], documents['review'], documents['payload'], expected,
                            refs['payload'], o._fresh_compile_resources)
    need(not any(os.path.lexists(row['reference']['path']) for row in publication.values()), 'root publication path already exists')
    def publish(row):
        path, document = Path(row['reference']['path']), row['document']
        o._exclusive_json(path, document)
        os.chmod(path, 0o644)
        fd = os.open(path, os.O_RDONLY)
        os.fsync(fd)
        os.close(fd)
        o._fsync_dir(D)
        actual = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        need(actual == row['reference'], 'published bytes differ from exact approved payload')
        return actual
    aref = publish(publication['admission'])
    o._read_root_document(aref, D / 'ROOT-ADMISSION.json', 'published BFD root admission')
    rref = publish(publication['release'])
    final_request = publication['request']['document']
    o._validate_launch_admission(final_request)
    qref = publish(publication['request'])
    need(o._request_core_hash(final_request) == facts['request_core_sha256'], 'published request core differs')
    print(json.dumps({'scope': SCOPE, 'status': 'PUBLISHED_BFD_ROOT_DOCUMENTS_NOT_EXECUTION_ACCEPTANCE',
        'root_admission': aref, 'root_release': rref, 'released_request': qref,
        'actual_query': refs['query'], 'independent_execution_review': refs['review'],
        'independent_owner_source_review': refs['source_review'], 'approved_exact_payload': refs['payload'],
        'actual_query_outer_wholejoin': refs['joined']}, sort_keys=True))

if __name__ == '__main__':
    main()
