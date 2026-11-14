#!/usr/bin/python3
"""Ordinary independent artifact review; fixed hash-bound reviewer bindings only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

FIELDS = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
CAP = 4 << 20
SOURCE_SHA = '0c134ee778b273610ead1ecc507caa038642459c0a065c956b4431c35c755917'
APPLY_SHA = 'f88d6f1b27828b6063f7e28fb01f9617e41da4478ef42c7b0b97a936e04b039b'
MANIFEST_SHA = '8255bbf869d9904b8ff0a4d6e2ce6dc5264493db1b2c3f6574ad98c04982956d'
CONDITIONAL_SHA = 'b6cfea61a7c55080459bab39ae407090014ed707b3f5928527dc5263d1b96b20'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
P = Path('/home/holden/mckernel-work/host-preparation/duplicate-archive-cleanup-execution-preparation-20261018-1')
A = Path('/home/holden/mckernel-work/host-preparation/evening-cleanup-apply-20261019-1')
O = Path(__file__).absolute().parent


def need(value, predicate):
    if not value:
        raise ValueError(predicate)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, cap=CAP):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, 'regular bounded input: ' + str(path))
        blocks = []
        used = 0
        while True:
            block = os.read(fd, min(65536, cap - used + 1))
            if not block:
                break
            used += len(block)
            need(used <= cap, 'input cap: ' + str(path))
            blocks.append(block)
        after = os.fstat(fd)
        need(all(getattr(before, k) == getattr(after, k) == getattr(os.lstat(path), k) for k in FIELDS), 'input stable metadata: ' + str(path))
        raw = b''.join(blocks)
        need(len(raw) == before.st_size, 'input complete bytes: ' + str(path))
        return raw, {k: getattr(after, k) for k in FIELDS}
    finally:
        os.close(fd)


def load(path):
    return json.loads(read(path)[0])


def source_meta(row):
    fields = row.split(':', 7)
    need(len(fields) == 8, 'source stat fields')
    dev, ino, uid, gid, mode, links, size = [int(x, 16 if i == 4 else 10) for i, x in enumerate(fields[:7])]
    need(stat.S_ISREG(mode) and (uid, gid, stat.S_IMODE(mode), links) == (0, 0, 0o600, 1) and size <= 32 << 20, 'source root regular shape')
    stamps = re.findall(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.(\d{9}) ([+-]\d{4})', fields[7])
    need(len(stamps) == 2, 'source nanosecond timestamps')
    nanos = [int(datetime.datetime.strptime(x + ' ' + z, '%Y-%m-%d %H:%M:%S %z').timestamp()) * 10**9 + int(y) for x, y, z in stamps]
    return dict(dev=dev, inode=ino, uid=uid, gid=gid, mode=stat.S_IMODE(mode), nlink=links, size=size, mtime_ns=nanos[0], ctime_ns=nanos[1])


def check(binding, expected_release_sha):
    precheck = binding['mode'] == 'PRECHECK_COMPLETED_OBSERVATION8_FAILED_APPLY1'
    need(precheck or binding['mode'] == 'FINAL_ACTUAL_OBSERVATION9_APPLY2', 'reviewed checker role')
    SOURCE_SHA = binding['engine_source_sha256']
    APPLY_SHA = binding['apply_wrapper_sha256']
    CONDITIONAL_SHA = binding['apply_conditional_review_sha256']
    A = Path(binding['apply_base'])
    need(SOURCE_SHA in ('0c134ee778b273610ead1ecc507caa038642459c0a065c956b4431c35c755917', '5586388673348be64bd1e5b1734f60e6f26c87f77bb4ba019a063ea4b808d566'), 'reviewed source generation')
    base = Path(binding['observer_base'])
    rb = base / binding['readback_dirname']
    release_path = Path(binding['apply_release'])
    raw_release, _ = read(release_path)
    need(digest(raw_release) == expected_release_sha, 'entire exact apply release hash')
    release = json.loads(raw_release)
    decision_raw, _ = read(binding['observer_decision'])
    need(digest(decision_raw) == binding['observer_decision_sha256'], 'observer independent decision hash')
    decision = json.loads(decision_raw)
    commands = decision[binding['decision_readback_key']]['commands']
    receipt = load(rb / 'result.json')
    need(len(receipt['commands']) == len(commands) == 5, 'five exact readbacks')
    for actual, approved in zip(receipt['commands'], commands):
        need(actual['name'] == approved['name'] and actual['argv'] == approved['argv'], 'readback exact name/argv')
        need(actual['direct_child_joined'] is True and actual['returncode'] == 0, 'readback direct joined zero')
        for label, capture in actual['captures'].items():
            raw, metadata = read(capture['path'], 32 << 20)
            need(metadata == capture['after'], 'ordinary held/reopened FD metadata')
            need(capture['before']['st_size'] == 0 and all(capture['before'][k] == metadata[k] for k in FIELDS[:6]), 'ordinary FD birth identity')
            need((metadata['st_uid'], metadata['st_gid'], stat.S_IMODE(metadata['st_mode']), metadata['st_nlink']) == (1000, 1000, 0o600, 1), 'ordinary capture shape')
            need(len(raw) == capture['bytes'] and digest(raw) == capture['sha256'], 'ordinary capture bytes/hash')
            need(label != 'stderr' or raw == b'', 'readback helper stderr empty')
    before, _ = read(rb / 'stat-before.stdout')
    after, _ = read(rb / 'stat-after.stdout')
    need(before == after, 'source pre/post metadata identical')
    rows = before.decode().splitlines()
    need(rows == receipt['source_stat_rows'] and len(rows) == 3, 'source three rows')
    metas = [source_meta(row) for row in rows]
    raw0, _ = read(rb / 'raw-0.stdout', 32 << 20)
    raw1, _ = read(rb / 'raw-1.stdout', 32 << 20)
    raw2, _ = read(rb / 'raw-2.stdout', 32 << 20)
    need(all(meta['size'] == len(raw) for meta, raw in zip(metas, (raw0, raw1, raw2))), 'source/raw sizes')
    app = json.loads(raw0)
    events = [json.loads(row) for row in raw2.splitlines()]
    need([e['status'] for e in events] == ['STARTING', 'LAUNCHED', 'OBSERVATION_JOINED'], 'complete finite observer journal')
    final = events[-1]
    need(final['direct_joined'] and final['whole_group_retired'] and final['remaining_group'] == [] and final['mutex_identity_preserved_and_available'], 'positive observer group/mutex retirement')
    need(final['returncode'] == 0 and not final.get('timed_out'), 'observer zero/no timeout')
    need(final['pid'] == final['pgid'] == events[1]['pid'] and final['starttime'] == events[1]['starttime'], 'observer process generation')
    for i, raw in enumerate((raw0, raw1)):
        need(all(final['capture_metadata'][i][k] == v for k, v in metas[i].items()), 'source held FD/stat metadata join')
        need(final['capture_sha256'][i] == digest(raw), 'source held FD/hash join')
    need(raw1 == b'', 'observer stderr empty')
    outer = load(base / binding['outer_status'])
    need(outer['direct_child_joined'] and outer['returncode'] == 0 and read(base / binding['outer_stderr'])[0] == b'', 'outer direct joined zero')
    observer_release, _ = read(base / binding['observer_release'])
    need(digest(observer_release) == final['release_sha256'], 'observer release hash')
    need(app['status'] == 'OBSERVED_NO_EFFECT' and app['executor'] == [final['pid'], final['starttime'], BOOT], 'complete actual observer identity/status')
    need(final['source_sha256'] == SOURCE_SHA and final['wrapper_sha256'] == binding['observer_wrapper_sha256'], 'observer exact source/wrapper pins')
    need(digest(read(binding['engine_source_artifact'])[0]) == SOURCE_SHA and digest(read(binding['apply_wrapper'])[0]) == APPLY_SHA, 'current engine/apply source pins')
    need(release['status'] == 'EXECUTION_RELEASE' and release['source_sha256'] == SOURCE_SHA and release['manifest_sha256'] == MANIFEST_SHA and release['observation_wrapper_sha256'] == APPLY_SHA, 'exact apply role/pins')
    need(release['independent_review']['status'] == 'PASS' and release['independent_review']['sha256'] == CONDITIONAL_SHA == digest(read(binding['apply_conditional_review'])[0]), 'apply conditional review exact bind')
    need(all(release['attestations'].get(k) is True for k in ('no_active_or_queued_indirect_consumers', 'no_writers_or_rename_publishers', 'sole_cleanup_coordinator', 'scratch21_and_exclusions_preserved', 'included_usage_guard_active')), 'required genuine attestations')
    need(release['boot_id'] == final['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT, 'live boot')
    coordinator, start = release['coordinator_identity']
    if not precheck:
        need(Path(binding['engine_source_artifact']) == P / 'exact120.py', 'live actual engine source path')
        need(int(Path('/proc', str(coordinator), 'stat').read_bytes().rpartition(b') ')[2].split()[19]) == start, 'live coordinator generation')
    snapshot = app['observation']
    need(set(snapshot) == {'containers', 'git', 'mount', 'parents', 'processes', 'records', 'unmatched'}, 'complete snapshot fields')
    need(release['expected_records'] == snapshot['records'], 'exact release expected records')
    projection = {k: v for k, v in snapshot.items() if k != 'processes'}
    need({k: v for k, v in release['observation'].items() if k != 'processes'} == projection, 'all immutable snapshot fields exact')
    need(release['observed_unix'] == app['observed_unix'], 'original observation epoch preserved')
    need(snapshot['git'] == {'object_ids_sha256': '0757f1ee6142e6dee7aeec67ce4e864f5abc032318e4ca8015881c0327b8aca5', 'objects': 122, 'repository_owner': [1000, 1000]}, 'Git122 unchanged oracle')
    for label, floor in [('host', 17985175552), ('scratch', 13421772800)]:
        need(release['minimum_available_bytes'][label] >= floor and app['capacity'][label]['available_bytes'] >= release['minimum_available_bytes'][label], 'observed capacity reserves')
    predecessor = release['physical_predecessor']
    need(predecessor['status'] == 'POSITIVE_PHYSICAL_RETIREMENT_RECORDED' and predecessor['independent_actual_review_pending'] is True, 'honest predecessor assembly status')
    allowed = {str(base / binding['outer_status']), str(rb / 'raw-2.stdout'), str(rb / 'result.json')} | {str(rb / (name + '.status.json')) for name in ('stat-before', 'raw-0', 'raw-1', 'raw-2', 'stat-after')}
    need({f['path'] for f in predecessor['files']} == allowed, 'exact predecessor receipt scope')
    for row in predecessor['files']:
        need(digest(read(row['path'])[0]) == row['sha256'], 'predecessor actual hash')
    publication = release['publication']
    need(publication['path'] in binding['allowed_publications'], 'reviewed publication path')
    need(digest(read(publication['path'])[0]) == publication['sha256'] == binding['allowed_publications'][publication['path']], 'exact published proof hash')
    need(release['journal'] == binding['engine_journal'], 'exact originalP journal')
    if precheck:
        failure_raw, _ = read(binding['completed_failure_review'])
        need(digest(failure_raw) == binding['completed_failure_review_sha256'], 'completed failed apply review hash')
        failure = json.loads(failure_raw)
        need(failure['status'] == 'ACCEPT_FAILED_APPLY1_PREFLIGHT_REFUSAL_AND_POSITIVE_RETIREMENT_NO_DELETION' and failure['actual_release_sha256'] == expected_release_sha, 'completed failed apply provenance')
    else:
        need(Path(release['journal']).parent == P and not os.path.lexists(release['journal']), 'fresh originalP journal')
        need(len(binding['apply_capture_paths']) == 3 and not any(os.path.lexists(path) for path in binding['apply_capture_paths']), 'fresh apply capture names')
    now = time.time()
    age = now - app['observed_unix']
    fresh = 0 <= age < 120 and now <= release['expires_unix'] <= now + 600
    profile = load(binding['apply_profile'])
    argv = profile['argv'][:]
    argv[argv.index('--release') + 1] = str(release_path)
    argv[argv.index('--release-sha256') + 1] = expected_release_sha
    return {'status': 'PASS_PRECHECK_COMPLETED_OBSERVATION8_AND_FAILED_APPLY1_PROVENANCE' if precheck else ('PASS_FINAL_ACTUAL_OBSERVATION9_AND_EXACT_APPLY2_RELEASE' if fresh else 'HOLD_ORIGINAL_OBSERVATION9_FRESHNESS'), 'actual_release_path': str(release_path), 'actual_release_sha256': expected_release_sha, 'actual_release_bytes': len(raw_release), 'observation_raw_sha256': digest(raw0), 'actual_positive_retirement': {'outer_pid': outer['pid'], 'pid': final['pid'], 'starttime': final['starttime'], 'direct_joined': True, 'whole_group_retired': True, 'remaining_group': [], 'mutex_available': True}, 'source_sha256': SOURCE_SHA, 'apply_wrapper_sha256': APPLY_SHA, 'observer_wrapper_sha256': final['wrapper_sha256'], 'time_unix': now, 'observed_unix': app['observed_unix'], 'observation_age_seconds': age, 'age120_check': fresh, 'source_engine_120_after_new_snapshot_mandatory': True, 'exact_supervisor_argv': argv, 'immutable_snapshot_sha256': digest(json.dumps(projection, sort_keys=True, separators=(',', ':')).encode()), 'fd_metadata_readback_and_source_hash_joins': True, 'exact_snapshot_release_predecessor_provenance': True, 'scope': 'Only one exact120 apply under published conditional profile. No release/source mutation, trim, broader removal or retry. Actual242eventjournal and retirement acceptance remain separate.', 'final_apply_authority': fresh and not precheck}


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--binding', required=True)
    parser.add_argument('--binding-sha256', required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args()
    need(os.getuid() == os.geteuid() == 1000, 'ordinary reviewer only')
    raw, _ = read(args.binding)
    need(digest(raw) == args.binding_sha256, 'reviewer fixed binding hash')
    binding = json.loads(raw)
    try:
        result = check(binding, args.release_sha256)
    except Exception as exc:
        result = {'status': 'HOLD_ACTUAL_ARTIFACT_PREDICATE', 'predicate': str(exc), 'error_type': type(exc).__name__, 'actual_release_sha256': args.release_sha256, 'time_unix': time.time(), 'final_apply_authority': False}
    result['binding_sha256'] = args.binding_sha256
    result['checker_sha256'] = digest(read(__file__)[0])
    result['reviewer_root_execution'] = False
    destination = Path(binding['output'])
    need(destination.parent == O and destination.suffix == '.json', 'private exact reviewer report')
    with destination.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'predicate': result.get('predicate'), 'report': str(destination), 'report_sha256': digest(read(destination)[0]), 'observation_age_seconds': result.get('observation_age_seconds'), 'final_apply_authority': result['final_apply_authority']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
