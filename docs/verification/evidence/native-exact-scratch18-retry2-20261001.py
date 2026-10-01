#!/usr/bin/env python3
"""Preparation only. Partial transactions are retained and refused on replay.

Default validation is read-only. This program never starts a build or guest.
Preparation requires a fetched cleanup terminal publication; a later, separate
execution release must bind the resulting request bytes and live identities.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import types

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
REVIEW_STATE = 'SOURCE_PENDING_REVIEW'
RELEASE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
ANCESTORS = ('89ab5c555aac9177a789efc67ddc775dacb25d6d',
             '215d338c06cc70ca6bad471eb2d035fb5650246f',
             '126a70890b258d7f21e08bfd5c77fe51c3c77e65',
             'd224cb46c2c52609f01e3b0601493e9443e2d365')
PREFIX = 'docs/verification/evidence/'
PACKET = PREFIX + 'native-exact-scratch18-retry2-20261001.py'
TEST = 'scripts/tests/test_native_exact_scratch18_retry2_20261001.py'
TEMPLATE = PREFIX + 'native-exact-scratch18-retry2-request-20261001.json'
WRAPPER = 'scripts/native_rust_exact_disk_build_wrapper.py'
FAILURE = PREFIX + 'native-exact-scratch18-build-admission-failure-20261001-1.json'
DEPENDENCIES = {
    TEMPLATE: 'eed75f5db927bd3eb0f1af7c16bc71952581578843eead2630ecf37d7162f106',
    WRAPPER: 'ccfbd404ff2428c4eb8841948b761118a42bd25ed8875c583755e6a97d8f0393',
    'scripts/tests/test_native_rust_exact_disk_build_wrapper.py': '1f7c573fd03e27e6a61e5d9ad19718f9eb8409e6749654c313625d66a7c9bdc3',
    FAILURE: '40497b42fd0906cfe45af35ee07a9be736948db8cda84d036216e9670663aec7',
    PREFIX + 'native-exact-scratch18-build-execution-20261001.py': '072de9ddb8a9911a1183bdd086bdafdd50fbd2680065d17a66b64663adc8c185',
}
REQUEST = ROOT / 'native-exact-build-request-scratch-18-retry2-20261001.json'
CANONICAL_SHA256 = '42cbf1b2b76ca445bbbf39ca69739032ca5b972da7da01ea5f1bcaea9ec026d9'
ATTEMPT = ROOT / 'native-exact-candidate-operational-exclusion-scratch18.json'
SHARED = ROOT / 'mckernel-heavy-operation.lock'
LEASE = ROOT / 'native-exact-build-lease-scratch18-retry2-20261001.json'
OUTPUT = ROOT / 'mckernel-exact-candidate-scratch-18-retry2-20261001-output'
EVIDENCE = ROOT / 'mckernel-exact-candidate-scratch-18-retry2-20261001-evidence'
OWNER_EVIDENCE = ROOT / 'native-exact-scratch18-retry2-20261001-owner-evidence'
CLEANUP_PUBLICATION = PREFIX + 'native-exact-scratch18-interrupt-cleanup-terminal-20261001.json'
PUBLISHER_CONTRACT = {'schema': 'scratch18.publisher-contract.v1',
    'coordination': 'sole-campaign-coordinator-no-concurrent-build-or-cleanup',
    'publishers': 'project-owned-regular-file-O_CREAT|O_EXCL-only',
    'census': 'privileged-full-process-and-active-container-before-transaction-and-every-rmdir',
    'excluded': 'arbitrary-same-UID-directory-substitution-after-final-check'}
OLD_LEASE = ROOT / 'native-exact-build-lease-scratch-18.json'
PREP_PLAN = ROOT / 'native-exact-scratch18-retry2-preparation.plan.json'
PREP_JOURNAL = ROOT / 'native-exact-scratch18-retry2-preparation.journal.jsonl'
PREP_MUTEX = ROOT / 'native-exact-scratch18-retry2-preparation.mutex'

class Refusal(ValueError): pass

def sha(data): return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise Refusal('duplicate-json-key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)

def directory(path, chain=None):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts: raise Refusal('noncanonical-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if chain is not None: chain.append(identity(os.fstat(fd)))
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
            if chain is not None: chain.append(identity(os.fstat(fd)))
        return fd
    except BaseException:
        os.close(fd); raise

def read_regular(path, record=None):
    path = Path(path); dfd = directory(path.parent); fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 16 << 20:
            raise Refusal('artifact-shape')
        data = bytearray()
        while len(data) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            if not block: break
            data.extend(block)
        after = os.fstat(fd); entry = os.stat(path.name, dir_fd=dfd, follow_symlinks=False)
        fields = ('st_dev', 'st_ino', 'st_nlink', 'st_mode', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
            any(getattr(before, k) != getattr(entry, k) for k in fields) or len(data) != before.st_size):
            raise Refusal('artifact-raced')
        if record is not None:
            actual = (path, before.st_dev, before.st_ino, before.st_nlink,
                      stat.S_IMODE(before.st_mode), before.st_uid, before.st_gid, before.st_size, sha(data))
            if actual != record: raise Refusal('artifact-binding')
        return bytes(data)
    finally:
        if fd is not None: os.close(fd)
        os.close(dfd)

def git(args):
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C', 'LC_ALL': 'C',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': '/dev/null',
                   'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1',
                   'GIT_TERMINAL_PROMPT': '0'}
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '--git-dir', str(REPO / '.git'), *args],
                            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode: raise Refusal('git-check-failed:' + args[0])
    return result.stdout

def sources(commit):
    if not isinstance(commit, str) or re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise Refusal('release-commit')
    if git(['rev-parse', '--verify', RELEASE_REF + '^{commit}']).decode().strip() != commit:
        raise Refusal('release-ref-mismatch')
    git(['cat-file', 'commit', commit])
    for ancestor in ANCESTORS: git(['merge-base', '--is-ancestor', ancestor, commit])
    result = {}
    for relative in (*DEPENDENCIES, PACKET, TEST):
        raw = read_regular(REPO / relative)
        if relative in DEPENDENCIES and sha(raw) != DEPENDENCIES[relative]:
            raise Refusal('dependency-hash:' + relative)
        if git(['show', commit + ':' + relative]) != raw: raise Refusal('release-blob:' + relative)
        result[relative] = raw
    return result

def check_request(request):
    if sha(canonical(request)) != CANONICAL_SHA256:
        raise Refusal('request-canonical-binding')
    expected_paths = {
        'output_root': OUTPUT, 'evidence_root': EVIDENCE,
        'source_root': ROOT / 'mckernel-exact-candidate-scratch-18',
        'owner_evidence_root': OWNER_EVIDENCE, 'lease_path': LEASE,
        'operational_exclusion_path': ATTEMPT,
    }
    for key, path in expected_paths.items():
        if request.get(key) != str(path): raise Refusal('prepared-request-paths')
    return request

def module(relative, data):
    loaded = types.ModuleType('_bound_scratch18_resume_dependency')
    loaded.__file__ = str(REPO / relative)
    exec(compile(data, loaded.__file__, 'exec'), loaded.__dict__)
    return loaded

def compatibility(bound, request):
    wrapper = module(WRAPPER, bound[WRAPPER])
    if (wrapper.OPERATIONAL_EXCLUSION_PATH != str(ATTEMPT) or
        wrapper.SHARED_HEAVY_LOCK_PATH != str(SHARED)):
        raise Refusal('wrapper-ownership-paths')
    result = wrapper.validate_request(request)
    if (not isinstance(result, dict) or set(result) != {'status', 'execution_released', 'request_sha256'} or
        result['status'] != 'PASS_COMPATIBILITY_ONLY' or result['execution_released'] is not False or
        result['request_sha256'] != CANONICAL_SHA256):
        raise Refusal('downstream-validation')

def absent(paths):
    for path in paths:
        fd = directory(path.parent)
        try:
            try: os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError: continue
            raise Refusal('required-absent:' + str(path))
        finally: os.close(fd)

def cleanup(commit):
    """Authenticate the fetched schema-v5 cleanup and all retained records."""
    raw = read_regular(REPO / CLEANUP_PUBLICATION)
    if git(['show', commit + ':' + CLEANUP_PUBLICATION]) != raw:
        raise Refusal('cleanup-publication-blob')
    report = strict_json(raw)
    required = {'schema', 'result', 'acceptance_credit', 'cleanup_source',
                'publisher_contract', 'execution', 'archives',
                'transaction_records', 'active_paths_absent', 'preservation', 'capacity', 'next'}
    if (not isinstance(report, dict) or set(report) != required or
        report['schema'] != 'mckernel.native-exact.scratch18-interrupt-cleanup-terminal.v1' or
        report['result'] != 'PASS_TERMINAL_REPLAY' or report['acceptance_credit'] is not False or
        report['active_paths_absent'] != [str(ATTEMPT), str(OLD_LEASE), str(SHARED)] or
        not isinstance(report['publisher_contract'], dict) or
        not isinstance(report['execution'], dict) or report['execution'].get('journal_events') != 13 or
        report['execution'].get('container_absent') is not True or
        not isinstance(report['archives'], dict) or not isinstance(report['transaction_records'], dict) or
        not isinstance(report['preservation'], dict)):
        raise Refusal('cleanup-publication-schema')
    expected = {
        'plan': ROOT / 'native-exact-scratch18-interrupt-cleanup.plan.json',
        'journal': ROOT / 'native-exact-scratch18-interrupt-cleanup.journal.jsonl',
        'mutex': ROOT / 'native-exact-scratch18-interrupt-cleanup.mutex',
        'attempt_archive': ROOT / 'native-exact-scratch18-interrupt-attempt.archive',
        'lease_archive': ROOT / 'native-exact-scratch18-interrupt-lease.archive',
        'shared_archive': ROOT / 'native-exact-scratch18-interrupt-shared.archive',
        'terminal': ROOT / 'mckernel-exact-candidate-scratch-18-evidence/inspect-terminal.json',
    }
    rows = {}
    plan_preview_raw = read_regular(expected['plan'])
    plan_preview = strict_json(plan_preview_raw)
    if (not isinstance(plan_preview, dict) or plan_preview.get('schema') != 'scratch18.interrupt-cleanup.v5' or
        plan_preview.get('device') != expected['plan'].stat().st_dev):
        raise Refusal('cleanup-plan-schema')
    for key, section in (('attempt_archive', ('archives', 'attempt')),
                         ('lease_archive', ('archives', 'lease')),
                         ('shared_archive', ('archives', 'shared')),
                         ('plan', ('transaction_records', 'plan')),
                         ('journal', ('transaction_records', 'journal')),
                         ('mutex', ('transaction_records', 'mutex'))):
        row = report[section[0]].get(section[1])
        if not isinstance(row, dict):
            raise Refusal('cleanup-publication-artifacts')
        rows[key] = row
    terminal = report['preservation'].get('terminal_inspect_sha256')
    if not isinstance(terminal, str) or not re.fullmatch('[0-9a-f]{64}', terminal):
        raise Refusal('cleanup-publication-terminal')
    blobs = {}
    for key, path in expected.items():
        row = rows.get(key)
        if key == 'terminal':
            term = plan_preview.get('terminal')
            if (not isinstance(term, list) or len(term) != 4 or term[0] != path.name):
                raise Refusal('cleanup-terminal-binding')
            row = {'path': str(path), 'device': plan_preview['device'], 'inode': term[2],
                   'size': term[3], 'mode': '0600', 'sha256': term[1]}
        if row is None:
            raise Refusal('cleanup-publication-artifacts')
        rows[key] = row
        fields = ('path', 'dev', 'inode', 'nlink', 'mode', 'uid', 'gid', 'size', 'sha256')
        allowed = {'path', 'device', 'inode', 'size', 'mode', 'sha256'}
        if key.endswith('_archive'):
            allowed |= {'uid', 'gid'}
        # The publication uses device/inode/size/mode/uid/gid without nlink;
        # nlink is authenticated live by read_regular and must be one.
        if (not isinstance(row, dict) or set(row) != allowed or
            row['path'] != str(path) or row['device'] < 0 or row['inode'] < 0 or
            row['size'] < 0 or row['mode'] != '0600' or
            any(type(row[k]) is not int for k in ('device', 'inode', 'size')) or
            any(type(row[k]) is not int or row[k] < 0 for k in ('uid', 'gid') if k in row) or
            not isinstance(row['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256'])):
            raise Refusal('cleanup-artifact-schema')
        live = os.stat(path)
        if ('uid' not in row or 'gid' not in row) and (live.st_uid, live.st_gid) != (1000, 1000):
            raise Refusal('cleanup-artifact-owner')
        record = (path, row['device'], row['inode'], 1, int(row['mode'], 8),
                  row.get('uid', live.st_uid), row.get('gid', live.st_gid), row['size'], row['sha256'])
        blobs[key] = read_regular(path, record)
    plan = strict_json(blobs['plan'])
    if blobs['plan'] != plan_preview_raw:
        raise Refusal('cleanup-plan-raced')
    if (not isinstance(plan, dict) or plan.get('schema') != 'scratch18.interrupt-cleanup.v5' or
        plan.get('root') != str(ROOT) or plan.get('device') != ROOT.stat().st_dev or
        plan.get('publisher_contract') != PUBLISHER_CONTRACT or
        report['publisher_contract'] != PUBLISHER_CONTRACT):
        raise Refusal('cleanup-plan-schema')
    mutex = plan.get('mutex')
    if (not isinstance(mutex, list) or len(mutex) != 2 or
        mutex[0] != plan['device'] or rows['mutex']['device'] != mutex[0] or
        rows['mutex']['inode'] != mutex[1]):
        raise Refusal('cleanup-mutex-binding')
    terminal_plan = plan.get('terminal')
    if (not isinstance(terminal_plan, list) or len(terminal_plan) != 4 or
        terminal_plan[0] != expected['terminal'].name or
        terminal_plan[1] != report['preservation']['terminal_inspect_sha256'] or
        terminal_plan[1] != rows['terminal']['sha256'] or
        terminal_plan[2] != rows['terminal']['inode'] or terminal_plan[3] != rows['terminal']['size']):
        raise Refusal('cleanup-terminal-binding')
    names = [ATTEMPT.name, OLD_LEASE.name, SHARED.name]
    archives = [expected['attempt_archive'], expected['lease_archive'], expected['shared_archive']]
    records = plan.get('records')
    if (not isinstance(records, list) or len(records) != 3 or
        any(not isinstance(r, list) or len(r) != 5 for r in records) or
        [r[0] for r in records] != names or [r[1] for r in records] != [p.name for p in archives]):
        raise Refusal('cleanup-plan-records')
    for row, key in zip(records, ('attempt_archive', 'lease_archive', 'shared_archive')):
        if (not isinstance(row[2], str) or not re.fullmatch('[0-9a-f]{64}', row[2]) or
            type(row[3]) is not int or type(row[4]) is not int or row[3] < 0 or row[4] < 0):
            raise Refusal('cleanup-archive-record')
        archive_row = rows[key]
        if (row[2] != archive_row['sha256'] or row[3] != archive_row['inode'] or row[4] != archive_row['size']):
            raise Refusal('cleanup-archive-binding')
    previous = sha(canonical(plan)); rows = blobs['journal'].splitlines(keepends=True)
    legal = [(event, index) for index in range(3)
             for event in ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 3)]
    if len(rows) != len(legal):
        raise Refusal('cleanup-journal-terminal')
    for sequence, (line, (event, index)) in enumerate(zip(rows, legal)):
        body = {'event': event, 'index': index, 'sequence': sequence,
                'plan_sha256': sha(canonical(plan)), 'previous': previous}
        previous = sha(canonical(body))
        if line != canonical(dict(body, hash=previous)) + b'\n':
            raise Refusal('cleanup-journal-binding')
    absent((ATTEMPT, SHARED, OLD_LEASE, LEASE))
    return raw

def write_all(fd, raw):
    while raw:
        count = os.write(fd, raw)
        if count <= 0: raise Refusal('write-no-progress')
        raw = raw[count:]

def identity(st):
    return [st.st_dev, st.st_ino, stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid]

class Preparation:
    """No partial replay: any existing mutex or plan requires separate recovery."""
    def __init__(self):
        self.chain = []
        self.fd = directory(ROOT, self.chain)
        self.root_identity = identity(os.fstat(self.fd))
        self.mutex = None
        self.identities = {}

    def close(self):
        if self.mutex is not None: os.close(self.mutex)
        os.close(self.fd)

    def pinned(self):
        chain = []
        fd = directory(ROOT, chain)
        try:
            if chain != self.chain: raise Refusal('root-replaced')
        finally: os.close(fd)
        for name, expected in self.identities.items():
            if identity(os.stat(name, dir_fd=self.fd, follow_symlinks=False)) != expected:
                raise Refusal('prepared-entry-replaced:' + name)

    def create(self, path, data):
        self.pinned()
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=self.fd)
        try:
            self.identities[path.name] = identity(os.fstat(fd))
            write_all(fd, data); os.fsync(fd)
        finally: os.close(fd)
        os.fsync(self.fd); self.pinned()

    def event(self, event, path):
        self.pinned()
        fd = os.open(PREP_JOURNAL.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            if identity(os.fstat(fd)) != self.identities[PREP_JOURNAL.name]:
                raise Refusal('journal-replaced')
            write_all(fd, canonical({'event':event, 'path':str(path)}) + b'\n'); os.fsync(fd)
        finally: os.close(fd)
        self.pinned()

    def run(self, commit, bound, request, cleanup_raw):
        absent((PREP_MUTEX, PREP_PLAN, PREP_JOURNAL, REQUEST, OUTPUT, EVIDENCE, OWNER_EVIDENCE))
        self.pinned()
        self.mutex = os.open(PREP_MUTEX.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=self.fd)
        fcntl.flock(self.mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.identities[PREP_MUTEX.name] = identity(os.fstat(self.mutex))
        os.fsync(self.mutex); os.fsync(self.fd)
        self.create(PREP_PLAN, canonical({'schema':'scratch18.retry2.preparation.v1',
            'release_commit':commit, 'request_sha256':sha(canonical(request)+b'\n'),
            'cleanup_publication_sha256':sha(cleanup_raw), 'root':self.root_identity,
            'paths':[str(x) for x in (OUTPUT,EVIDENCE,OWNER_EVIDENCE,REQUEST)]}) + b'\n')
        self.create(PREP_JOURNAL, b'')
        for path in (OUTPUT, EVIDENCE, OWNER_EVIDENCE):
            self.event('before-directory', path)
            os.mkdir(path.name, 0o700, dir_fd=self.fd)
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try:
                self.identities[path.name] = identity(os.fstat(fd)); os.fsync(fd)
            finally: os.close(fd)
            os.fsync(self.fd); self.event('after-directory', path)
        # The authenticated real wrapper validates the exact production-shaped
        # request with the newly created empty roots, before request publication.
        compatibility(bound, request)
        if sources(commit) != bound or cleanup(commit) != cleanup_raw: raise Refusal('binding-raced')
        self.pinned(); self.event('before-request', REQUEST)
        raw = canonical(request) + b'\n'
        self.create(REQUEST, raw)
        if read_regular(REQUEST) != raw: raise Refusal('request-replaced')
        compatibility(bound, strict_json(read_regular(REQUEST)))
        self.pinned()
        if sources(commit) != bound or cleanup(commit) != cleanup_raw: raise Refusal('binding-raced')
        if read_regular(REQUEST) != raw: raise Refusal('request-replaced')
        self.event('complete', REQUEST)
        return {'status':'PASS_PREPARED', 'execution_released':False,
                'request':str(REQUEST), 'request_sha256':sha(raw),
                'canonical_request_sha256':sha(canonical(request)),
                'identities':self.identities}

def admit(commit, prepare=False):
    bound = sources(commit)
    request = check_request(strict_json(bound[TEMPLATE]))
    cleanup_raw = cleanup(commit)
    absent((PREP_MUTEX, PREP_PLAN, PREP_JOURNAL, REQUEST, OUTPUT, EVIDENCE, OWNER_EVIDENCE))
    if not prepare:
        return {'status':'PASS_PREPARATION_READY', 'execution_released':False,
                'request_exists':False, 'canonical_request_sha256':CANONICAL_SHA256}
    operation = Preparation()
    try: return operation.run(commit, bound, request, cleanup_raw)
    finally: operation.close()

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(admit(args.release_commit, args.prepare), sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True))
        return 1

if __name__ == '__main__': raise SystemExit(main())
