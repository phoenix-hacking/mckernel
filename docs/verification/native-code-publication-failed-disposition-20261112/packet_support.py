# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Finite validation helpers for this one four-role read-only packet.
import datetime, hashlib, json, os, pathlib, resource, stat, time

ROOT = pathlib.Path('/home/holden/mckernel')
HERE = pathlib.Path(__file__).resolve().parent
GiB = 2**30

def canon(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def identity(st):
    return dict(dev=st.st_dev, ino=st.st_ino, mode=oct(stat.S_IMODE(st.st_mode)),
                uid=st.st_uid, gid=st.st_gid, nlink=st.st_nlink,
                bytes=st.st_size, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)

def read_fixed(path, expected_sha, limit=262144, uid=1000):
    path = pathlib.Path(path)
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_uid == uid
        assert stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
        assert 0 < before.st_size <= limit
        chunks, count = [], 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - count))
            if not block: break
            chunks.append(block); count += len(block)
            assert count <= limit
        raw = b''.join(chunks)
        assert identity(before) == identity(os.fstat(fd))
        assert digest(raw) == expected_sha
        return json.loads(raw), identity(before)
    finally:
        os.close(fd)

def check_pin(item):
    p = pathlib.Path(item['path'])
    if 'argv_path' in item:
        assert os.path.realpath(item['argv_path']) == str(p)
    fd = os.open(str(p), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_size == item['bytes']
        h = hashlib.sha256()
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            h.update(raw)
        assert identity(before) == identity(os.fstat(fd))
        assert h.hexdigest() == item['sha256']
    finally:
        os.close(fd)

def actor_argv(q, qsha, review, review_sha, admission, admission_sha):
    return q['actor_prefix'] + [str(HERE / 'dispose_failed_publication.py'),
        str(HERE / 'REQUEST.json'), qsha, str(review), review_sha,
        str(admission), admission_sha]

def normalized_argv_sha(argv):
    normalized = list(argv)
    normalized[-1] = '<ADMISSION_SHA256>'
    return digest(canon(normalized))

def validate_admission(q, qsha, review_sha, admission, argv, actor=False):
    # This is the complete shared field union; no account/cap/usage body is read.
    assert set(admission) == set(q['admission_fields'])
    assert admission['schema'] == q['admission_schema']
    assert admission['saved_Root'] == q['saved_Root']
    assert admission['invocation'] == q['invocation']
    assert admission['finite_credit_run_id'] == '7c6ef3604bfb4008a917bba8cfb6cfaa'
    assert admission['request_sha256'] == qsha
    assert admission['review_sha256'] == review_sha
    assert admission['source_binding_sha256'] == q['source_binding_sha256']
    assert admission['actor_argv_normalized_sha256'] == normalized_argv_sha(argv)
    assert admission['capture_layout_sha256'] == q['capture_layout_sha256']
    assert admission['actual_account_service_source_permission_result'] == 'ACCEPTED'
    refs = admission['actual_Root_guard_owner_source_account_service_permission_evidence_refs']
    assert type(refs) is list and refs
    for ref in refs:
        assert set(ref) == {'path','bytes','sha256'}
        assert type(ref['path']) is str and pathlib.Path(ref['path']).is_absolute()
        assert type(ref['bytes']) is int and ref['bytes'] > 0
        assert type(ref['sha256']) is str and len(ref['sha256']) == 64
    assert admission['original_tool_session'] == 36902
    assert admission['original_publisher_bytes_retained'] == 2*GiB
    assert admission['original_publisher_jobs_retained'] == 1
    assert admission['new_actor_planning_bytes'] == 256*2**20
    assert admission['new_actor_jobs'] == 1 and admission['CPU'] == [0]
    assert admission['parent_AS_bytes'] == admission['actor_AS_bytes'] == 128*2**20
    for key in ('current_HOST_jobs_before', 'current_HOST_payload_reserved_bytes',
                'current_controller_worker_overhead_bytes', 'MemAvailable_bytes',
                'host_free_bytes', 'scratch_free_bytes'):
        assert type(admission[key]) is int and admission[key] >= 0
    assert 1 <= admission['current_HOST_jobs_before'] < 3
    assert admission['current_HOST_payload_reserved_bytes'] >= 2*GiB
    assert admission['current_HOST_jobs_before'] + 1 <= 3
    assert admission['current_HOST_payload_reserved_bytes'] + admission['current_controller_worker_overhead_bytes'] + 256*2**20 <= 4*GiB
    assert admission['MemAvailable_bytes'] >= 26*GiB
    assert admission['host_free_bytes'] >= 16*GiB + 32*2**20
    assert admission['scratch_free_bytes'] >= 12*GiB + 32*2**20
    assert admission['native12_and_all_other_holds_unchanged'] is True
    assert admission['no_original_resource_disposition'] is True
    assert type(admission['host_boot_id']) is str and len(admission['host_boot_id']) == 36
    age = time.time() - datetime.datetime.fromisoformat(admission['at']).timestamp()
    assert 0 <= age <= 25
    assert os.sched_getaffinity(0) == {0}
    assert resource.getrlimit(resource.RLIMIT_AS) == (128*2**20, 128*2**20)
    assert resource.getrlimit(resource.RLIMIT_FSIZE) == (8*2**20, 8*2**20)
    assert resource.getrlimit(resource.RLIMIT_NOFILE) == (128, 128)
    assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
    assert admission['failed_scope_one_target_intent'] == q['failed_scope_one_target_intent']
    return age
