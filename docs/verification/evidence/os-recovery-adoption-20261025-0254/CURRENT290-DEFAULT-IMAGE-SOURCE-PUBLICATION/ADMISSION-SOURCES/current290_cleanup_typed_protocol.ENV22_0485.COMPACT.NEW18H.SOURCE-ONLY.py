"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact frozen230 source and normal-owner cleanup proof hooks. No owner imports,
cleanup constructor, mutation, flock, subprocess, compiler or execution release.
Runtime target/holder/client/cleanup results remain genuine future observations.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

CONTRACT = Path(__file__).resolve().parent / 'FROZEN-CURRENT290-CLEANUP-TYPED-PROTOCOL-CONTRACT.ENV22_0485.COMPACT.NEW18H.SOURCE-ONLY.json'
CONTRACT_SHA = '0446f4478bf4e59fb6e0d3d457367797f8000cbfd5c9b4d238d2c88a6142863c'
MAXIMUM_DOCUMENT = 256 << 20
SELECTED_FIELDS = {'path', 'device', 'inode', 'mode', 'uid', 'gid', 'size', 'nlink', 'sha256'}


def need(ok, message):
    if not ok:
        raise RuntimeError('current230 cleanup typed proof: ' + message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('nonfinite JSON')))


def selected_bytes(path, selected, expected=None):
    """Exact existing observe_identity row plus stable descriptor read."""
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts, 'absolute normalized selected path')
    row = selected.get(str(path))
    need(isinstance(row, dict) and set(row) == SELECTED_FIELDS, 'complete selected identity row: ' + str(path))
    directories = []
    fd = None
    try:
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        directories.append((parent, None, None))
        for name in path.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            directories.append((child, parent, name)); parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
             0 <= before.st_size <= MAXIMUM_DOCUMENT, 'unique bounded selected regular file')
        chunks = []
        count = 0
        while count <= before.st_size:
            block = os.read(fd, min(1 << 20, before.st_size + 1 - count))
            if not block:
                break
            chunks.append(block); count += len(block)
        raw = b''.join(chunks)
        observed = dict(path=str(path), device=before.st_dev, inode=before.st_ino,
                        mode=oct(stat.S_IMODE(before.st_mode)), uid=before.st_uid, gid=before.st_gid,
                        size=before.st_size, nlink=before.st_nlink, sha256=digest(raw))
        need(count == before.st_size and observed == row, 'selected bytes/full identity differ')
        identity = lambda m: (m.st_dev, m.st_ino, m.st_mode, m.st_nlink, m.st_uid, m.st_gid,
                              m.st_size, m.st_mtime_ns, m.st_ctime_ns)
        need(identity(os.fstat(fd)) == identity(before) ==
             identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)), 'selected file changed during read')
        for child, parentfd, name in directories[1:]:
            left = os.fstat(child); right = os.stat(name, dir_fd=parentfd, follow_symlinks=False)
            need((left.st_dev, left.st_ino, left.st_mode, left.st_uid, left.st_gid) ==
                 (right.st_dev, right.st_ino, right.st_mode, right.st_uid, right.st_gid), 'selected ancestor changed')
        if expected is not None:
            need(set(expected) == {'path', 'sha256', 'bytes'} and expected['path'] == str(path) and
                 expected['sha256'] == observed['sha256'] and expected['bytes'] == count,
                 'exact frozen selected reference')
        return raw
    finally:
        if fd is not None:
            os.close(fd)
        for directory, _, _ in reversed(directories):
            os.close(directory)


def contract():
    raw = CONTRACT.read_bytes()
    need(digest(raw) == CONTRACT_SHA, 'immutable typed protocol contract')
    return parse(raw)


def required_static_references():
    c = contract()
    rows = list(c['static'].values())
    rows.append(dict(path=str(CONTRACT), sha256=CONTRACT_SHA, bytes=CONTRACT.stat().st_size))
    return rows


def _static(selected):
    c = contract()
    for row in required_static_references():
        selected_bytes(row['path'], selected, row)
    return c


def _provenance_predicates(c, selected):
    row = c['static']['provenance']
    raw = selected_bytes(row['path'], selected, row)
    names = {'_thin_require', '_thin_digest', '_thin_canonical', '_thin_path',
             '_thin_real_parents', '_thin_regular_digest', '_thin_check_tracked_link',
             'validate_thin_source', 'validate_thin_document'}
    body = [n for n in ast.parse(raw, row['path']).body if isinstance(n, ast.FunctionDef) and n.name in names]
    need({n.name for n in body} == names and len(body) == len(names), 'exact existing provenance function set')
    ns = dict(hashlib=hashlib, json=json, os=os, stat=stat, Path=Path,
              BASE_CANDIDATE=c['candidate_sha'], BASE_IHK=c['ihk_sha'],
              THIN_SCHEMA='mckernel.m14-combined-production-thin-inputs.v1',
              EXPECTED_SUCCESSOR_CANONICAL_SHA256=c['static']['manifest']['sha256'])
    exec(compile(ast.Module(body=body, type_ignores=[]), row['path'], 'exec'), ns)
    return ns


def _source_identity(c, obs):
    expected = c['source_identity']
    row = obs['candidate_root']
    fixed = dict(path=expected['path'], device=expected['dev'], inode=expected['inode'],
                 mode=oct(expected['mode']), uid=expected['uid'], gid=expected['gid'])
    need(all(row.get(k) == v for k, v in fixed.items()), 'exact separate frozen source-root identity')
    meta = os.lstat(expected['path'])
    need(stat.S_ISDIR(meta.st_mode) and
         (meta.st_dev, meta.st_ino, stat.S_IMODE(meta.st_mode), meta.st_uid, meta.st_gid) ==
         (expected['dev'], expected['inode'], expected['mode'], expected['uid'], expected['gid']),
         'actual frozen source inode')
    namespace = c['namespace'][0]
    need(obs['namespace_binding'] == dict(device=namespace['device'], inode=namespace['inode'],
             mode=stat.S_IFDIR | namespace['mode'], uid=namespace['uid'], gid=namespace['gid']),
         'actual source-prepared namespace4eb5 identity')
    # Work/evidence have real runtime contents now; never demand they stay empty.
    for row in c['namespace']:
        meta = os.lstat(row['path'])
        need(stat.S_ISDIR(meta.st_mode) and
             (meta.st_dev, meta.st_ino, stat.S_IMODE(meta.st_mode), meta.st_uid, meta.st_gid) ==
             (row['device'], row['inode'], row['mode'], row['uid'], row['gid']),
             'same source-prepared namespace/work/evidence inode')


def _capsule(proof_reference, selected, c):
    raw = selected_bytes(proof_reference['path'], selected, proof_reference)
    proof = parse(raw)
    need(proof['status'] == 'PASS_ACTUAL_FETCHED_SOURCE_BLOBS' and
         re.fullmatch('[0-9a-f]{40}', proof['commit']), 'genuine fetched frozen source capsule proof')
    fields = lambda rows: sorted((r['path'], r['sha256'], r['bytes']) for r in rows)
    need(type(c['fetched_capsule_count']) is int and c['fetched_capsule_count'] > 0 and
         len(proof['files']) == len(c['fetched_capsule_files']) == c['fetched_capsule_count'] and
         fields(proof['files']) == fields(c['fetched_capsule_files']), 'exact same68 fetched capsule members')
    # This authenticates the historical proof actually used by this image
    # entry. It makes no claim that cleanup-time HEAD or physical state is old.


def typed_source_binding(request, obs, selected_map):
    c = _static(selected_map)
    expected_request = parse(selected_bytes(c['static']['request']['path'], selected_map, c['static']['request']))
    need(request == expected_request, 'exact full952 request, not historical FP request')
    need(request['candidate_sha'] == c['candidate_sha'] and request['ihk_sha'] == c['ihk_sha'] and
         request['source_root'] == c['source_identity']['path'] and request['source_identity'] == c['source_identity'] and
         request['disk_identity'] == c['source_identity'] and request['backup_identity'] == c['backup_identity'] and
         all(request[k] == v for k, v in c['namespace_paths'].items()), 'exact current230 source/vendor/namespace request')
    need(request['source_derivative_sha256'] == c['source_derivative_sha256'] and
         request['materialization_sha256'] == c['materialization_sha256'] and
         request['candidate_identity_scope'] == 'base_git_commit_only' and
         request['native_fork_owned_transaction'] is False, 'image-only derivative identity and honest native scope')
    _source_identity(c, obs)
    materialization = parse(selected_bytes(c['static']['materialization']['path'], selected_map, c['static']['materialization']))
    result = parse(selected_bytes(c['static']['materialization_result']['path'], selected_map, c['static']['materialization_result']))
    need(materialization['status'] == 'ACTUAL_PASS_CURRENT290_SOURCE_MATERIALIZATION_ONLY_HEAVY_ADMISSION_OPEN' and
         materialization['source_identity'] == c['source_identity'] and
         materialization['source_derivative_sha256'] == c['source_derivative_sha256'] and
         materialization['materialization_sha256'] == c['materialization_sha256'] and
         materialization['materialization_result'] == c['static']['materialization_result'] and
         materialization['source_manifest'] == c['static']['manifest'] and
         materialization['owner'] == c['static']['owner'] and materialization['driver'] == c['static']['driver'] and
         materialization['provenance'] == c['static']['provenance'] and
         materialization['actual_bound_request'] == c['static']['request'], 'genuine actual current230 materialization tuple')
    need(result['status'] == 'PASS_CURRENT290_MAIN_WITH_QUALIFIED_COPY7_IHK3114_SOURCE_MATERIALIZATION_ONLY' and
         result['source_root'] == request['source_root'] and result['source_entries'] == 6153 and
         result['regular_files'] == 6104 and result['tracked_symlinks'] == 49 and result['copied_bytes'] == 105804031 and
         result['source_derivative_sha256'] == c['source_derivative_sha256'] and
         result['materialization_sha256'] == c['materialization_sha256'] and
         result['source_manifest_sha256'] == c['static']['manifest']['sha256'], 'actual stable-FD6153-copy result')
    receipt = parse(selected_bytes(c['static']['source_retention']['path'], selected_map, c['static']['source_retention']))
    need(receipt['status'] == 'PASS_EXACT_CURRENT290_FULL_SOURCE_AND_METADATA_RETENTION_ONLY' and
         receipt['source_entries'] == 6153 and receipt['source_bytes'] == 105804031 and type(c['source_retention_output_files']) is int and c['source_retention_output_files'] > 0 and receipt['output_files'] == c['source_retention_output_files'] and
         receipt['all_reopened_content_verified'] is True and receipt['full_owner_request'] == c['static']['request'] and
         receipt['source_manifest'] == c['static']['manifest'], 'exact retained source capsule receipt')
    document = parse(selected_bytes(c['static']['manifest']['path'], selected_map, c['static']['manifest']))
    predicates = _provenance_predicates(c, selected_map)
    # Reuse the exact accepted FULL source/symlink/mode/path/closure predicate,
    # not an invented CPU-only shortcut or historical FP status alias.
    predicates['validate_thin_source'](request['source_root'], document, c['candidate_sha'], c['ihk_sha'])
    return True


def _ownership_case(c, receipt, obs):
    need(receipt['status'] in ('PASS', 'FAIL'), 'finite actual owner status')
    expected = c['ownership_cases'][receipt['status']]
    paths = [row.get('path') for row in obs['retained_exclusions']]
    need(obs['ownership_case'] == expected['case'] and
         obs['shared_record_already_absent'] is expected['shared_record_already_absent'] and
         len(paths) == len(expected['retained_paths']) and set(paths) == set(expected['retained_paths']),
         'exact PASS-common-only or FAIL-common-and-shared ownership case')
    need(os.path.lexists(c['shared_heavy_path']) is (receipt['status'] == 'FAIL'),
         'actual shared-heavy presence must match finite owner outcome')


def normal_owner_join_binding(receipt, join, target, item, receipt_sha, request, obs, selected_map):
    c = _static(selected_map)
    paths = c['normal_paths']
    selected_join = selected_map.get(paths['owner.JOIN.json'])
    need(obs['normal_owner_join'] == selected_join and
         parse(selected_bytes(paths['owner.JOIN.json'], selected_map)) == join, 'actual fixed normal-owner JOIN proof')
    owner_raw = selected_bytes(c['owner_receipt'], selected_map)
    need(digest(owner_raw) == receipt_sha and parse(owner_raw) == receipt and
         receipt['schema'] == 'mckernel.native-exact-mckernel-image-container-receipt.v1' and
         receipt['status'] in ('PASS', 'FAIL') and receipt['retired'] is True and
         receipt['terminal_container_retained'] is True and receipt['cleanup_separately_required'] is True and
         receipt.get('client_retirement_unproven') is not True and receipt['candidate_sha'] == c['candidate_sha'],
         'positive actual owner receipt; upstream exact Docker inspect predicate remains required')
    need(all(receipt[k] == target[k] for k in ('container_id', 'container_name', 'owner_nonce', 'exit_code')) and
         item['Id'] == target['container_id'], 'actual owner/target/container join')
    _ownership_case(c, receipt, obs)
    process = parse(selected_bytes(paths['owner.PROCESS.json'], selected_map))
    entry = parse(selected_bytes(paths['ACTUAL-OWNER-ENTRY.json'], selected_map))
    ready = parse(selected_bytes(paths['ROOT-NORMAL-CLEANUP-COMPLETION-READY.json'], selected_map))
    holder = entry['holder']
    need(entry['owner_argv'] == process['argv'] == join['argv'] == c['owner_argv'] and
         process['pid'] == join['pid'] == target['owner_pid'] and
         process['starttime'] == join['starttime'] == target['owner_starttime'] and
         process['pgid'] == process['pid'] and process['parent_pid'] == entry['caller_pid'] == holder['pid'] and
         entry['caller_starttime'] == holder['starttime'] and holder['boot_id'] == obs['boot_id'] and
         holder['fd'] in process['inherited_fds'] and process['stdin_from_parent_fd'] is None,
         'actual normal caller/owner PID birth argv and inherited holder relation')
    need(holder['path'] == '/run/lock/mckernel-development.lock' and
         holder['identity'] == dict(device=27, inode=4, uid=0, gid=0, mode=0o644, nlink=1) and
         holder['fd'] == holder['original_holder_fd'] and holder['transported_fd'] == 0 and
         holder['transport'] == 'STDIN_FD0_SUDO_A', 'declared same-OFD holder; live FD proof remains adapter-owned')
    need(join['returncode'] == (0 if receipt['status'] == 'PASS' else 1) and
         join['direct_child_joined'] is True and join['group_absent'] is True and
         join['closed_streams'] is True and join['error'] is None and join['retirement_error'] is None and
         ready['caller_pid'] == holder['pid'] and ready['holder'] == holder and ready['owner_join'] == join and
         ready['owner_receipt'] == dict(path=c['owner_receipt'], sha256=receipt_sha, bytes=len(owner_raw)),
         'actual fully joined normal owner, not a historical guard-result alias')
    for stream in ('stdout', 'stderr'):
        reference = join[stream]
        need(set(reference) == {'path', 'sha256', 'bytes'} and join['captures'][stream] == reference and
             reference['path'] == str(Path(c['caller_capture_root']) / ('owner.' + stream)),
             'exact normal capture reference shape/path')
        raw = selected_bytes(reference['path'], selected_map, reference)
        if stream == 'stdout':
            need(parse(raw) == receipt, 'actual normal-owner stdout equals retained receipt')
        else:
            need(raw == b'', 'normal owner stderr empty')
    grant_reference = entry['root_execution_grant']
    grant = parse(selected_bytes(grant_reference['path'], selected_map, grant_reference))
    need(grant['author'] == '/root' and grant['decision'] == 'GRANT_ONE_CURRENT290_IMAGE_OWNER' and
         grant['caller_sha256'] == c['static']['caller']['sha256'] and grant['holder'] == holder and
         grant['owner_argv'] == c['owner_argv'] and grant['operation_scope'] == c['source_scope'],
         'actual source-bound root normal-owner execution grant')
    payload_ref = grant['payload']
    payload = parse(selected_bytes(payload_ref['path'], selected_map, payload_ref))
    need(payload['argv'] == c['owner_argv'] and payload['source']['request'] == c['static']['request'] and
         request == parse(selected_bytes(c['static']['request']['path'], selected_map, c['static']['request'])),
         'actual released payload exact952 normal-owner source')
    _capsule(payload['fetched_publication'], selected_map, c)
    return True


def completion_result_requirements():
    """Exact source/interface requirements, never an invented runtime PASS."""
    return dict(existing_cleanup_result='Engine terminal_result schema/status/container/UUID/boot/release/plan/journal/archive facts stay engine-owned and unchanged.',
                parent_control='Root completion must bind THIS joined cleanup source/request/argv/result/streams/postflight, same holderPID/birth/FD/boot27:4, ownerreceipt/CID/nonce and independent exact protocol review.',
                client_ledger='Engine must retain complete EVIDENCE/attempt/command-*/status.json set, every PID/hash/exited/nonnegative-exit/no-client-retirement-unproven predicate; no historical FP guard root.',
                runtime_unproven=True, actual_C_retirement=False)
