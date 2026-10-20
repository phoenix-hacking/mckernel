"""One real current-M02 terminal body check, no runtime/parent authority.

Run only after the exact inputs/source/profile review and external CPU6 grant.
All mutated contexts are clearly labeled isolated fixture files.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, stat, sys
sys.dont_write_bytecode = True

def need(ok, why):
    if not ok:
        raise ValueError(why)

def load_source(ref, name):
    path = Path(ref['path'])
    raw = path.read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'exact source ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def full_ref(path):
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    need(all(getattr(before, k) == getattr(after, k) for k in fields), 'stable fixture context')
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size=len(raw), device=before.st_dev, inode=before.st_ino, uid=before.st_uid, gid=before.st_gid, mode=oct(stat.S_IMODE(before.st_mode)), nlink=before.st_nlink, mtime_ns=before.st_mtime_ns, ctime_ns=before.st_ctime_ns)

def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    handle = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, 'wb') as output:
        output.write(raw)
    return full_ref(path)

def refusal(call, name, expected_exception, expected_reason):
    try:
        call()
    except expected_exception as exc:
        need(str(exc) == expected_reason, 'exact expected refusal reason for ' + name)
        return dict(case=name, refused=True, exception_type=type(exc).__name__, reason=str(exc))
    raise ValueError('missing refusal: ' + name)

def main():
    need(sys.version_info[:2] == (3, 8) and sys.executable == '/usr/bin/python3', 'frozen Python3.8 interpreter')
    need(len(sys.argv) == 3, 'exact input path and SHA')
    raw = Path(sys.argv[1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == sys.argv[2], 'whole frozen input identity')
    inputs = json.loads(raw)
    need(inputs['status'] == 'REVIEWED_SOURCE_BODY_CHECK_ONLY' and inputs['runtime_release'] is None, 'source check only')
    decoder = load_source(inputs['candidate'], 'actual_current_child_failure_decoder')
    need(decoder.CONTEXT_REF == inputs['context'], 'actual source-bound context')
    context = decoder.R.checked(inputs['context'])
    terminal = decoder.R.checked(context['physical_FD'])
    decoder.R.read_bytes(inputs['current_M02_snapshot_context'])
    snapshot = load_source(inputs['current_M02_snapshot'], 'actual_current_M02_LAST_terminal_body')
    bindings = dict(physical_projection_source=inputs['candidate'], physical_review=context['physical'], physical_predecessor=inputs['expected_projection'], root_lock_identity=dict(device=27, inode=4, uid=0, gid=0, mode='0o644'))
    # Invoke the actual unchanged current M02 caller's entire terminal body.
    snapshot.terminal_joins(terminal, bindings)
    need(decoder.project(terminal, context['physical']) == inputs['expected_projection'], 'actual whole same-reader projection')
    root = Path(inputs['fixture_output_namespace'])
    root.mkdir(mode=0o700)
    cases = []
    bad = dict(bindings)
    bad['physical_review'] = dict(context['physical'], sha256='0' * 64)
    cases.append(refusal(lambda: snapshot.terminal_joins(terminal, bad), 'current_M02_terminal_wrong_physical_SHA', ValueError, 'whole genuine current report/FD'))
    bad_source = dict(bindings)
    bad_source['physical_projection_source'] = dict(inputs['candidate'], sha256='0' * 64)
    cases.append(refusal(lambda: snapshot.terminal_joins(terminal, bad_source), 'current_M02_terminal_wrong_decoder_source', snapshot.Refusal, 'exact selected known-kind physical decoder'))
    mutations = [
        ('stale_physical_FD', lambda c: c['physical_FD'].update(inode=c['physical_FD']['inode'] + 1), 'full actual raw record identity'),
        ('stale_original_tool_FD', lambda c: c['original_tool_join'].update(inode=c['original_tool_join']['inode'] + 1), 'full actual raw record identity'),
        ('missing_genuine_census_supplement', lambda c: c.update(host_census_supplement=None), 'genuine complete current host census supplement remains unbound'),
        ('native_metadata_authority_swap', lambda c: c.update(native_release=c['metadata_release'], native_release_compact=c['metadata_release_compact']), 'distinct genuine native and metadata authority roles'),
    ]
    original_context = decoder.CONTEXT_REF
    for name, mutate, reason in mutations:
        changed = json.loads(json.dumps(context))
        mutate(changed)
        decoder.CONTEXT_REF = write(root / ('FIXTURE-' + name + '.json'), changed)
        try:
            cases.append(refusal(lambda: decoder.project(terminal, context['physical']), name, ValueError, reason))
        finally:
            decoder.CONTEXT_REF = original_context
    need(len(cases) == 6 and all(row['refused'] for row in cases), 'all affected genuine refusal cases')
    result = dict(status='PASS_CURRENT_CHILD_FAILURE_READER_AND_ACTUAL_M02_TERMINAL_BODY_SOURCE_CHECK_ONLY', actual_M02_terminal_joins=True, actual_same_reader_projection=True, cases=cases, fixture_only=True, production_parent_created=False, root_operations=0, guest_runs=0, runtime_release=None)
    write(root / 'RESULT.json', result)
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
