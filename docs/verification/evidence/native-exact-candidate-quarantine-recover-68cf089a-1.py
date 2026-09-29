#!/usr/bin/env python3
"""One-shot root recovery for the retained post-quarantine cleanup failure."""

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

REPO = Path('/home/holden/mckernel')
SB = Path('/home/holden/mckernel-work/scratch')
C = Path('/dev/shm/mckernel-exact-candidate-68cf089a-1')
B = Path('/dev/shm/mckernel-exact-metadata-backup-68cf089a-1')
QC = Path('/dev/shm/.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1')
QB = Path('/dev/shm/.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1')
ROOTS = ((C, QC, 26, 14117, 10462), (B, QB, 26, 24701, 87))
OLD_LEASE = SB / 'native-exact-build-lease-68cf089a-1.json'
OLD_JOURNAL = SB / 'native-exact-candidate-delete-68cf089a-1.journal.jsonl'
OLD_OBSERVER_OUT = SB / 'native-exact-live-reference-post-seal-68cf089a-1.stdout.json'
OLD_OBSERVER_ERR = SB / 'native-exact-live-reference-post-seal-68cf089a-1.stderr.txt'
OLD_PREFLIGHT = SB / 'native-exact-candidate-delete-preflight-68cf089a-1.json'
OLD_RELEASE = SB / 'native-exact-candidate-delete-release-68cf089a-1.json'
OLD_EXECUTION = SB / 'native-exact-cleanup-execution-68cf089a-1'
OLD_HELPER = REPO / 'docs/verification/evidence/native-exact-candidate-delete-68cf089a-1.py'
OLD_PACKET = REPO / 'docs/verification/evidence/native-exact-candidate-cleanup-execution-68cf089a-1.sh'
OLD_DELETER_STDERR = OLD_EXECUTION / 'deleter.stderr'
CLAIM = SB / 'native-exact-candidate-quarantine-recovery-consumed-68cf089a-1.json'
JOURNAL = SB / 'native-exact-candidate-quarantine-recovery-68cf089a-1.journal.jsonl'
PREFLIGHT = SB / 'native-exact-candidate-quarantine-recovery-preflight-68cf089a-1.json'
RELEASE = SB / 'native-exact-candidate-quarantine-recovery-release-68cf089a-1.json'
OBSERVER_OUT = SB / 'native-exact-candidate-quarantine-recovery-observer-68cf089a-1.stdout.json'
OBSERVER_ERR = SB / 'native-exact-candidate-quarantine-recovery-observer-68cf089a-1.stderr.txt'
OBSERVER = REPO / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py'
PACKET = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh'
INVENTORY = SB / 'native-exact-complete-worktree-inventory-68cf089a-1.json'
INV_ARCHIVE = REPO / 'docs/verification/evidence/stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz'
RET = REPO / 'docs/verification/evidence/stability-native-exact-prepared-candidate-retention-68cf089a-20260929-1.tar.gz'
PREP = REPO / 'docs/verification/evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz'
PREP_RECORD = REPO / 'docs/verification/stability-native-exact-candidate-preparation-checkpoint-20260929-1.json'
RET_RECORD = REPO / 'docs/verification/stability-native-exact-prepared-candidate-retention-20260929-1.json'
INPUTS = SB / 'native-exact-inputs-68cf089a-1.json'
REQUEST = SB / 'native-exact-build-request-68cf089a-1.json'
RAW_ARCHIVE = REPO / 'docs/verification/evidence/stability-native-exact-cleanup-failure-raw-20260929-1.tar.gz'
FAILURE_RECORD = REPO / 'docs/verification/stability-native-exact-cleanup-failure-20260929-1.json'

OLD_JOURNAL_SHA = '6bf129586cd9edc9bb2b89519bdad2fb697606dea876eb6ecac1a86d43a04ebe'
OLD_OBSERVER_OUT_SHA = '8eb6762e135a808a252d0cfa991935af6d6db6814a1203baa7e1ec04b98dac06'
OLD_OBSERVER_ERR_SHA = 'e9e6526237e203fa99fe62b05fc0421e6bfb888c4e38c75d6348f0fa55e24d68'
OLD_LEASE_SHA = '69ced2395f7c16019b70d9d1b2de45ff2519014178ee145a453e2ed2a24f47e3'
OLD_PREFLIGHT_SHA = '78ce57751e4a5e11fc7a0567d30235624f443e11c64f20abda18699750e565de'
OLD_RELEASE_SHA = '704c84096fe7181bc2ff366881b874235bfb1e8b04002c7ff90d651f9eff7323'
OLD_HELPER_SHA = '5500e77e68240052cef1e72616c500635c33a1d1cc8aceee93719f943ac5c753'
OLD_PACKET_SHA = 'd3d4c0640fc52a8d8fbb2d64831780d7ca4c76ffa5cfe539896cc43dbc5c5729'
OLD_DELETER_STDERR_SHA = '166c9c5457a8b969434d3a20ce9d417005f7e60c2f99de0ed2eeee22eb145d8b'
RAW_ARCHIVE_SHA = 'cc38687005d52ecc4b0d48ffa9ff650832169ba9d426add604b0c4e0f8893eea'
FAILURE_RECORD_SHA = 'd2150a0a8173c0caaa4c5a6050653947e372480cd059d8d9ff49656dac76ed97'
OBSERVER_SHA = 'e6f46761aeaa64a4dffc30dee0865dea7784a920333b730dfc42f98c44688e4d'
INVENTORY_SHA = '743c05648112cee5af2eda235fba11a2f32d50a9d3074423c0c064d52a1682c0'
INV_ARCHIVE_SHA = '6be734da7ee54eec0523fa961a0264b5242637c26d56952f524b84c907f0b044'
RET_SHA = 'eed1879bd35c62d7aa629189dfc0c46254680209ab02f933278c70c8cf9880c6'
PREP_SHA = '78e2b5c44e9ae00f2f463ac8b93723e26d00877fbbe7ecfb285d1d89d6404264'
PREP_RECORD_SHA = 'bc8b3a6d819208b7266e39bb91862ddbacba5ec700dcf14b960fe7857aa2be99'
RET_RECORD_SHA = '129d25f80a29fc321cae94c3e1f4db4279e42c1b100ea41c6406a3a3e133f7b6'
INPUTS_SHA = 'ae0c5f74e3e3f06176c46f2f174b1109c11a4e88f23ee71fd7432e6325262abd'
REQUEST_SHA = '25f820e2994d41427ed16cf5f062d647125ccb7144f63afe618e88ccce7f576c'
RELEASE_SHA = 'UNSET-REQUIRES-INDEPENDENT-RECOVERY-RELEASE-SHA256'
RELEASE_SENTINEL = 'UNSET-REQUIRES-INDEPENDENT-RECOVERY-RELEASE-SHA256'
HELPER_PIN_SENTINEL = '__REPLACE_WITH_FINAL_RECOVERY_HELPER_SHA256__'
PACKET_RELEASE_SENTINEL = '__REPLACE_WITH_FINAL_RECOVERY_RELEASE_SHA256__'
OLD_LEASE_ID = (1831, 31447, 0o600, 0, 0)
OLD_HELPER_PID = 3673971
FRESHNESS_SECONDS = 300


class TerminationRequested(RuntimeError):
    pass


def fail(message):
    raise RuntimeError(message)


def request_termination(signum, _frame):
    raise TerminationRequested('termination signal ' + str(signum))


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def write_loop(writer, data):
    offset = 0
    while offset < len(data):
        count = writer(data[offset:])
        if count <= 0:
            fail('short durable write')
        offset += count


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exact_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            fail('not a regular input: ' + str(path))
        chunks = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                return b''.join(chunks)
            chunks.append(block)
    finally:
        os.close(fd)


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('duplicate JSON key: ' + key)
        result[key] = value
    return result


def exact_json(path):
    return json.loads(exact_bytes(path).decode('utf-8'), object_pairs_hook=reject_duplicates)


def require_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        fail(label + ' keys mismatch')


def require_path_hash(value, path, digest, label):
    require_keys(value, ('path', 'sha256'), label)
    if value != {'path': str(path), 'sha256': digest}:
        fail(label + ' binding mismatch')


def lstat_id(path):
    try:
        value = os.lstat(path)
        return {'path': str(path), 'dev': value.st_dev, 'inode': value.st_ino,
                'mode': format(stat.S_IMODE(value.st_mode), '04o'),
                'uid': value.st_uid, 'gid': value.st_gid,
                'type': 'directory' if stat.S_ISDIR(value.st_mode) else 'other'}
    except FileNotFoundError:
        return {'path': str(path), 'absent': True}


def assert_absent(path):
    try:
        os.lstat(path)
    except FileNotFoundError:
        return
    fail('path must be absent: ' + str(path))


def check_quarantine(path, device, inode):
    value = os.lstat(path)
    if (not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode) or
            (value.st_dev, value.st_ino, stat.S_IMODE(value.st_mode), value.st_uid, value.st_gid) !=
            (device, inode, 0o700, 0, 0)):
        fail('quarantine identity mismatch: ' + str(path))


def validate_old_lease():
    value = os.lstat(OLD_LEASE)
    if (not stat.S_ISREG(value.st_mode) or stat.S_ISLNK(value.st_mode) or
            (value.st_dev, value.st_ino, stat.S_IMODE(value.st_mode), value.st_uid, value.st_gid) != OLD_LEASE_ID or
            sha(OLD_LEASE) != OLD_LEASE_SHA):
        fail('old lease identity/hash mismatch')
    lease = exact_json(OLD_LEASE)
    if lease != {'schema': 'mckernel.native-exact-candidate-cleanup-lease.v1',
                 'pid': OLD_HELPER_PID, 'started_at_utc': '2026-09-29T05:32:34.727836Z'}:
        fail('old lease bytes/schema mismatch')
    if Path('/proc/%d' % OLD_HELPER_PID).exists():
        fail('old helper PID exists or was reused')


def validate_failure_journal():
    if sha(OLD_JOURNAL) != OLD_JOURNAL_SHA:
        fail('old journal hash mismatch')
    records = [json.loads(line, object_pairs_hook=reject_duplicates)
               for line in exact_bytes(OLD_JOURNAL).decode('utf-8').splitlines()]
    phases = [record.get('phase') for record in records]
    expected = ['lease-acquired', 'seal-before', 'seal-after', 'quarantine-after',
                'seal-before', 'seal-after', 'quarantine-after', 'target-fds-closed',
                'terminal-failure']
    if phases != expected:
        fail('old journal phase sequence mismatch')
    prohibited = {'observer-pass', 'delete-start', 'delete-entry', 'delete-complete', 'terminal-success'}
    if prohibited.intersection(phases):
        fail('old journal contains deletion/success phase')
    first = records[0]
    if (first.get('helper_sha256') != OLD_HELPER_SHA or first.get('inventory_sha256') != INVENTORY_SHA or
            first.get('inputs_sha256') != INPUTS_SHA or first.get('release_sha256') != OLD_RELEASE_SHA or
            first.get('lease') != str(OLD_LEASE)):
        fail('old journal lease record binding mismatch')
    before = records[1]
    after = records[2]
    renamed = records[3]
    if (before.get('original', {}).get('inode') != 14117 or after.get('original', {}).get('mode') != '0700' or
            renamed.get('quarantine', {}).get('inode') != 14117 or
            renamed.get('quarantine', {}).get('path') != str(QC)):
        fail('old candidate quarantine phase mismatch')
    before = records[4]
    after = records[5]
    renamed = records[6]
    if (before.get('original', {}).get('inode') != 24701 or after.get('original', {}).get('mode') != '0700' or
            renamed.get('quarantine', {}).get('inode') != 24701 or
            renamed.get('quarantine', {}).get('path') != str(QB)):
        fail('old backup quarantine phase mismatch')
    closed = records[7].get('survivors', {})
    terminal = records[8]
    for value in (closed, terminal.get('survivors', {})):
        originals = value.get('original', [])
        quarantines = value.get('quarantine', [])
        if len(originals) != 2 or not all(item.get('absent') is True for item in originals):
            fail('old journal original survivor mismatch')
        if [(item.get('path'), item.get('inode'), item.get('mode')) for item in quarantines] != [
                (str(QC), 14117, '0700'), (str(QB), 24701, '0700')]:
            fail('old journal quarantine survivor mismatch')
    if terminal.get('error') != "RuntimeError('observer returned failure; captures retained')" or terminal.get('lease_retained') is not True:
        fail('old journal terminal failure mismatch')
    return records


def validate_raw_archive_lease():
    member_name = 'home/holden/mckernel-work/scratch/native-exact-build-lease-68cf089a-1.json'
    with tarfile.open(RAW_ARCHIVE, 'r:gz') as archive:
        matches = [member for member in archive.getmembers() if member.name == member_name and member.isfile()]
        if len(matches) != 1 or hashlib.sha256(archive.extractfile(matches[0]).read()).hexdigest() != OLD_LEASE_SHA:
            fail('raw archive old lease preservation mismatch')


def validate_release():
    data = exact_bytes(RELEASE)
    if hashlib.sha256(data).hexdigest() != RELEASE_SHA:
        fail('recovery release hash mismatch')
    value = json.loads(data.decode('utf-8'), object_pairs_hook=reject_duplicates)
    require_keys(value, ('schema_version', 'record_kind', 'status', 'packet_id', 'source_checkpoint',
                         'template_helper', 'template_packet', 'corrected_observer', 'original_failure',
                         'inventory', 'artifacts', 'roots', 'one_shot', 'retry', 'rollback',
                         'acceptance_credit'), 'release')
    if (type(value['schema_version']) is not int or value['schema_version'] != 3 or
            value['record_kind'] != 'native_exact_candidate_quarantine_recovery_release_basis' or
            value['status'] != 'PASS_ONE_SHOT_QUARANTINE_RECOVERY' or
            value['packet_id'] != 'native-exact-candidate-quarantine-recovery-68cf089a-1' or
            type(value['source_checkpoint']) is not str or re.fullmatch(r'[0-9a-f]{40}', value['source_checkpoint']) is None or
            value['one_shot'] is not True or type(value['one_shot']) is not bool or
            value['retry'] is not False or type(value['retry']) is not bool or
            value['rollback'] is not False or type(value['rollback']) is not bool or
            value['acceptance_credit'] is not False or type(value['acceptance_credit']) is not bool):
        fail('recovery release scalar mismatch')
    require_path_hash(value['corrected_observer'], OBSERVER, OBSERVER_SHA, 'observer')
    require_keys(value['inventory'], ('path', 'sha256', 'archive_path', 'archive_sha256'), 'inventory')
    if value['inventory'] != {'path': str(INVENTORY), 'sha256': INVENTORY_SHA,
                              'archive_path': str(INV_ARCHIVE), 'archive_sha256': INV_ARCHIVE_SHA}:
        fail('recovery inventory binding mismatch')
    expected_failure = {
        'journal': {'path': str(OLD_JOURNAL), 'sha256': OLD_JOURNAL_SHA},
        'observer_stdout': {'path': str(OLD_OBSERVER_OUT), 'sha256': OLD_OBSERVER_OUT_SHA},
        'observer_stderr': {'path': str(OLD_OBSERVER_ERR), 'sha256': OLD_OBSERVER_ERR_SHA},
        'lease': {'path': str(OLD_LEASE), 'sha256': OLD_LEASE_SHA},
        'preflight': {'path': str(OLD_PREFLIGHT), 'sha256': OLD_PREFLIGHT_SHA},
        'release': {'path': str(OLD_RELEASE), 'sha256': OLD_RELEASE_SHA},
        'raw_archive': {'path': str(RAW_ARCHIVE), 'sha256': RAW_ARCHIVE_SHA},
        'failure_record': {'path': str(FAILURE_RECORD), 'sha256': FAILURE_RECORD_SHA},
        'original_helper': {'path': str(OLD_HELPER), 'sha256': OLD_HELPER_SHA},
        'original_packet': {'path': str(OLD_PACKET), 'sha256': OLD_PACKET_SHA},
        'deleter_stderr': {'path': str(OLD_DELETER_STDERR), 'sha256': OLD_DELETER_STDERR_SHA}}
    require_keys(value['original_failure'], expected_failure, 'original failure')
    for key, expected in expected_failure.items():
        if value['original_failure'][key] != expected:
            fail('original failure release binding mismatch: ' + key)
    expected_artifacts = {
        'inputs': {'path': str(INPUTS), 'sha256': INPUTS_SHA},
        'request': {'path': str(REQUEST), 'sha256': REQUEST_SHA},
        'preparation_archive': {'path': str(PREP), 'sha256': PREP_SHA},
        'preparation_record': {'path': str(PREP_RECORD), 'sha256': PREP_RECORD_SHA},
        'retention_capsule': {'path': str(RET), 'sha256': RET_SHA},
        'retention_record': {'path': str(RET_RECORD), 'sha256': RET_RECORD_SHA}}
    if value['artifacts'] != expected_artifacts:
        fail('recovery artifact binding mismatch')
    expected_roots = [
        {'original_path': str(C), 'quarantine_path': str(QC), 'device_number': 26, 'inode': 14117,
         'mode': '0700', 'uid': 0, 'gid': 0, 'tree_inode_count': 10462},
        {'original_path': str(B), 'quarantine_path': str(QB), 'device_number': 26, 'inode': 24701,
         'mode': '0700', 'uid': 0, 'gid': 0, 'tree_inode_count': 87}]
    if value['roots'] != expected_roots:
        fail('recovery roots binding mismatch')
    for key, path in (('template_helper', 'docs/verification/evidence/native-exact-candidate-quarantine-recover-68cf089a-1.py'),
                      ('template_packet', 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh')):
        require_keys(value[key], ('path', 'sha256'), key)
        if value[key]['path'] != path or re.fullmatch(r'[0-9a-f]{64}', value[key]['sha256']) is None:
            fail(key + ' malformed')
    helper = Path(__file__).read_bytes()
    line = ("RELEASE_SHA = '" + RELEASE_SHA + "'").encode()
    if helper.count(line) != 1:
        fail('recovery helper release assignment mismatch')
    template = helper.replace(line, ("RELEASE_SHA = '" + RELEASE_SENTINEL + "'").encode())
    if hashlib.sha256(template).hexdigest() != value['template_helper']['sha256']:
        fail('recovery helper differs from template')
    packet = PACKET.read_bytes()
    pattern = re.compile(rb'(?m)^FINAL_HELPER_SHA=([0-9a-f]{64}); RELEASE_SHA=([0-9a-f]{64})$')
    matches = list(pattern.finditer(packet))
    if len(matches) != 1 or matches[0].group(1).decode() != sha(Path(__file__)) or matches[0].group(2).decode() != RELEASE_SHA:
        fail('recovery packet final pin mismatch')
    replacement = ('FINAL_HELPER_SHA=' + HELPER_PIN_SENTINEL + '; RELEASE_SHA=' + PACKET_RELEASE_SENTINEL).encode()
    if hashlib.sha256(pattern.sub(replacement, packet)).hexdigest() != value['template_packet']['sha256']:
        fail('recovery packet differs from template')
    return value


def parse_utc(value):
    if type(value) is not str or not value.endswith('Z'):
        fail('invalid preflight UTC timestamp')
    return datetime.fromisoformat(value[:-1] + '+00:00').timestamp()


def validate_preflight(release):
    value = exact_json(PREFLIGHT)
    required = {'schema': 'mckernel.native-exact-candidate-quarantine-recovery-preflight.v1',
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'helper_sha256': sha(Path(__file__)), 'observer_sha256': OBSERVER_SHA,
                'inventory_sha256': INVENTORY_SHA, 'release_record_path': str(RELEASE),
                'release_record_sha256': RELEASE_SHA, 'source_checkpoint': release['source_checkpoint'],
                'packet_sha256': sha(PACKET), 'no_active_docker_binds': True,
                'old_helper_pid_absent': True, 'old_lease_sha256': OLD_LEASE_SHA,
                'old_journal_sha256': OLD_JOURNAL_SHA}
    if set(value) != set(required) | {'observed_at_utc', 'admission_started_boottime_ns', 'roots'}:
        fail('recovery preflight keys mismatch')
    for key, expected in required.items():
        if type(value.get(key)) is not type(expected) or value.get(key) != expected:
            fail('recovery preflight mismatch: ' + key)
    observed = parse_utc(value['observed_at_utc'])
    if observed > time.time() + 5 or time.time() - observed > FRESHNESS_SECONDS:
        fail('recovery preflight stale')
    started = value['admission_started_boottime_ns']
    now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if type(started) is not int or started > now or now - started > FRESHNESS_SECONDS * 1_000_000_000:
        fail('recovery admission window stale')
    expected = [(str(QC), 26, 14117), (str(QB), 26, 24701)]
    roots = value['roots']
    if (type(roots) is not list or len(roots) != 2 or
            not all(type(item) is dict and set(item) == {'path', 'device_number', 'inode'} and
                    type(item['path']) is str and type(item['device_number']) is int and
                    type(item['inode']) is int for item in roots) or
            [(item['path'], item['device_number'], item['inode']) for item in roots] != expected):
        fail('recovery preflight roots mismatch')


class Journal:
    def __init__(self):
        self.fd = os.open(JOURNAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        fsync_dir(SB)

    def write(self, phase, fields):
        data = (json.dumps({'utc': utcnow(), 'phase': phase, **fields}, sort_keys=True,
                           separators=(',', ':')) + '\n').encode()
        write_loop(lambda block: os.write(self.fd, block), data)
        os.fsync(self.fd)

    def close(self):
        os.close(self.fd)


def create_claim():
    data = (json.dumps({'schema': 'mckernel.native-exact-candidate-quarantine-recovery-claim.v1',
                        'old_journal_sha256': OLD_JOURNAL_SHA, 'old_lease_sha256': OLD_LEASE_SHA,
                        'release_sha256': RELEASE_SHA, 'helper_sha256': sha(Path(__file__)),
                        'created_at_utc': utcnow()}, sort_keys=True, separators=(',', ':')) + '\n').encode()
    fd = os.open(CLAIM, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_loop(lambda block: os.write(fd, block), data)
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(SB)


def file_digest(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            fail('not regular file: ' + str(path))
        digest = hashlib.sha256()
        for block in iter(lambda: os.read(fd, 1 << 20), b''):
            digest.update(block)
        return info, digest.hexdigest()
    finally:
        os.close(fd)


def live_entry(path, digest=False):
    info = os.lstat(path)
    if stat.S_ISDIR(info.st_mode):
        kind, value = 'directory', None
    elif stat.S_ISREG(info.st_mode):
        kind, value = 'file', file_digest(path)[1] if digest else None
    elif stat.S_ISLNK(info.st_mode):
        kind, value = 'symlink', hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest() if digest else None
    else:
        fail('unsupported quarantine inode: ' + str(path))
    return {'type': kind, 'mode': format(stat.S_IMODE(info.st_mode), '04o'), 'sha256': value,
            'dev': info.st_dev, 'inode': info.st_ino}


def reconstruct_inventory():
    if sha(INVENTORY) != INVENTORY_SHA:
        fail('inventory hash mismatch')
    manifest = exact_json(INVENTORY)
    if manifest.get('roots') != [str(C), str(B)]:
        fail('inventory roots mismatch')
    rows = manifest.get('worktree_inventory')
    if type(rows) is not list or not rows:
        fail('inventory rows missing')
    expected = {}
    prefixes = {str(C.relative_to('/')): (C, QC, 26, 14117, 10462),
                str(B.relative_to('/')): (B, QB, 26, 24701, 87)}
    for row in rows:
        if type(row) is not dict or set(row) != {'path', 'type', 'mode', 'sha256'}:
            fail('inventory row malformed')
        name = row['path'].rstrip('/')
        if (type(row['path']) is not str or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or
                row['type'] not in ('directory', 'file', 'symlink') or type(row['mode']) is not str or name in expected):
            fail('inventory row invalid')
        matches = [prefix for prefix in prefixes if name == prefix or name.startswith(prefix + '/')]
        if len(matches) != 1:
            fail('inventory row outside roots')
        if (row['type'] == 'directory' and row['sha256'] is not None) or (row['type'] != 'directory' and
                (type(row['sha256']) is not str or re.fullmatch(r'[0-9a-f]{64}', row['sha256']) is None)):
            fail('inventory digest invalid')
        expected[name] = {'type': row['type'], 'mode': row['mode'], 'sha256': row['sha256']}
    result = {}
    for prefix, (_original, quarantine, device, inode, count) in prefixes.items():
        check_quarantine(quarantine, device, inode)
        actual, stack = set(), [quarantine]
        while stack:
            path = stack.pop()
            rel = path.relative_to(quarantine)
            logical = prefix if rel == Path('.') else prefix + '/' + str(rel)
            actual.add(logical)
            wanted = expected.get(logical)
            if wanted is None:
                fail('unexpected quarantine name: ' + logical)
            live = live_entry(path)
            wanted_mode = '0700' if rel == Path('.') else wanted['mode']
            if live['type'] != wanted['type'] or live['mode'] != wanted_mode or live['dev'] != device:
                fail('quarantine inventory metadata mismatch: ' + logical)
            if rel != Path('.'):
                result[(str(quarantine), str(rel))] = dict(wanted, dev=live['dev'], inode=live['inode'])
            if live['type'] == 'directory':
                with os.scandir(path) as entries:
                    stack.extend(Path(entry.path) for entry in entries)
        wanted_names = {name for name in expected if name == prefix or name.startswith(prefix + '/')}
        if actual != wanted_names or len(actual) != count:
            fail('quarantine inventory name/count mismatch: ' + str(quarantine))
    return result


def capture_observer():
    for path in (OBSERVER_OUT, OBSERVER_ERR):
        if path.exists() or path.is_symlink():
            fail('recovery observer capture exists: ' + str(path))
    outfd = errfd = None
    try:
        outfd = os.open(OBSERVER_OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        errfd = os.open(OBSERVER_ERR, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            result = subprocess.run([sys.executable, str(OBSERVER), '--target', str(QC), '--target', str(QB)],
                                    stdin=subprocess.DEVNULL, stdout=outfd, stderr=errfd,
                                    check=False, timeout=180)
        finally:
            os.fsync(outfd)
            os.fsync(errfd)
    finally:
        if outfd is not None:
            os.close(outfd)
        if errfd is not None:
            os.close(errfd)
        fsync_dir(SB)
    if result.returncode != 0:
        fail('corrected recovery observer failed; captures retained')
    value = exact_json(OBSERVER_OUT)
    if (value.get('schema') != 'mckernel.read-only-live-reference-snapshot.v6' or value.get('status') != 'PASS' or
            value.get('observer_sha256') != OBSERVER_SHA or value.get('scan_complete') is not True or
            Path('/proc/%d' % value.get('observer_pid', -1)).exists()):
        fail('corrected recovery observer record mismatch')
    observed = [(item.get('path'), item.get('device_number'), item.get('inode'), item.get('mode'),
                 item.get('tree_inode_count')) for item in value.get('roots', []) if type(item) is dict]
    expected = [(str(QC), 26, 14117, '0700', 10462), (str(QB), 26, 24701, '0700', 87)]
    if observed != expected:
        fail('corrected recovery observer roots mismatch')
    rounds = value.get('rounds')
    if type(rounds) is not list or len(rounds) < 2 or not all(
            round_.get('clean') is True and round_.get('complete_mount_proofs') is True
            for round_ in rounds[-2:]):
        fail('corrected recovery observer convergence mismatch')
    return value


def same(info, wanted, kind):
    return ((info.st_dev, info.st_ino, format(stat.S_IMODE(info.st_mode), '04o')) ==
            (wanted['dev'], wanted['inode'], wanted['mode']) and
            ((kind == 'directory' and stat.S_ISDIR(info.st_mode)) or
             (kind == 'file' and stat.S_ISREG(info.st_mode)) or
             (kind == 'symlink' and stat.S_ISLNK(info.st_mode))))


def fd_names(fd):
    return set(os.listdir(fd))


def delete_verified(fd, expected, prefix, device, journal, root_name):
    direct = {name[len(prefix):].split('/', 1)[0] for name in expected
              if name.startswith(prefix) and name[len(prefix):]}
    if fd_names(fd) != direct:
        fail('descriptor inventory changed at ' + root_name + '/' + prefix)
    for name in sorted(direct):
        rel = prefix + name
        wanted = expected[rel]
        first = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if first.st_dev != device or not same(first, wanted, wanted['type']):
            fail('descriptor identity mismatch: ' + rel)
        journal.write('delete-entry', {'root': root_name, 'path': rel,
                                       'inode': first.st_ino, 'type': wanted['type']})
        if wanted['type'] == 'directory':
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            try:
                if not same(os.fstat(child), wanted, 'directory'):
                    fail('directory descriptor mismatch: ' + rel)
                delete_verified(child, expected, rel + '/', device, journal, root_name)
            finally:
                os.close(child)
            if not same(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted, 'directory'):
                fail('directory changed before rmdir: ' + rel)
            os.rmdir(name, dir_fd=fd)
        elif wanted['type'] == 'file':
            child = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            try:
                opened = os.fstat(child)
                digest = hashlib.sha256()
                for block in iter(lambda: os.read(child, 1 << 20), b''):
                    digest.update(block)
            finally:
                os.close(child)
            if not same(opened, wanted, 'file') or digest.hexdigest() != wanted['sha256']:
                fail('file content/identity mismatch: ' + rel)
            if not same(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted, 'file'):
                fail('file changed before unlink: ' + rel)
            os.unlink(name, dir_fd=fd)
        elif wanted['type'] == 'symlink':
            if hashlib.sha256(os.fsencode(os.readlink(name, dir_fd=fd))).hexdigest() != wanted['sha256']:
                fail('symlink target mismatch: ' + rel)
            if not same(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted, 'symlink'):
                fail('symlink changed before unlink: ' + rel)
            os.unlink(name, dir_fd=fd)
        else:
            fail('unsupported verified type')


def scoped(expected, quarantine):
    return {relative: value for (root, relative), value in expected.items() if root == str(quarantine)}


def main():
    if os.geteuid() != 0:
        fail('root-only quarantine recovery')
    signal.signal(signal.SIGTERM, request_termination)
    signal.signal(signal.SIGINT, request_termination)
    release = validate_release()
    validate_preflight(release)
    fixed = ((OLD_JOURNAL, OLD_JOURNAL_SHA), (OLD_OBSERVER_OUT, OLD_OBSERVER_OUT_SHA),
             (OLD_OBSERVER_ERR, OLD_OBSERVER_ERR_SHA), (OLD_PREFLIGHT, OLD_PREFLIGHT_SHA),
             (OLD_RELEASE, OLD_RELEASE_SHA), (OLD_HELPER, OLD_HELPER_SHA), (OLD_PACKET, OLD_PACKET_SHA),
             (OLD_DELETER_STDERR, OLD_DELETER_STDERR_SHA), (RAW_ARCHIVE, RAW_ARCHIVE_SHA),
             (FAILURE_RECORD, FAILURE_RECORD_SHA),
             (OBSERVER, OBSERVER_SHA), (INVENTORY, INVENTORY_SHA), (INV_ARCHIVE, INV_ARCHIVE_SHA),
             (RET, RET_SHA), (PREP, PREP_SHA), (PREP_RECORD, PREP_RECORD_SHA),
             (RET_RECORD, RET_RECORD_SHA), (INPUTS, INPUTS_SHA), (REQUEST, REQUEST_SHA))
    for path, digest in fixed:
        if sha(path) != digest:
            fail('fixed recovery input mismatch: ' + str(path))
    validate_old_lease()
    validate_failure_journal()
    validate_raw_archive_lease()
    assert_absent(C)
    assert_absent(B)
    check_quarantine(QC, 26, 14117)
    check_quarantine(QB, 26, 24701)
    create_claim()
    journal = Journal()
    try:
        journal.write('recovery-claimed', {'claim': str(CLAIM), 'claim_sha256': sha(CLAIM),
                                           'old_lease': lstat_id(OLD_LEASE),
                                           'old_journal_sha256': OLD_JOURNAL_SHA,
                                           'release_sha256': RELEASE_SHA,
                                           'survivors': [lstat_id(QC), lstat_id(QB)]})
        expected = reconstruct_inventory()
        journal.write('inventory-reconstructed', {'entries': len(expected),
                                                   'survivors': [lstat_id(QC), lstat_id(QB)]})
        observer = capture_observer()
        journal.write('observer-pass', {'stdout': str(OBSERVER_OUT), 'stdout_sha256': sha(OBSERVER_OUT),
                                        'stderr': str(OBSERVER_ERR), 'stderr_sha256': sha(OBSERVER_ERR),
                                        'rounds': len(observer['rounds'])})
        parentfd = os.open('/dev/shm', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            for original, quarantine, device, inode, _count in ROOTS:
                assert_absent(original)
                fd = os.open(quarantine.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                             dir_fd=parentfd)
                try:
                    root = os.fstat(fd)
                    if (root.st_dev, root.st_ino, stat.S_IMODE(root.st_mode), root.st_uid, root.st_gid) != (
                            device, inode, 0o700, 0, 0):
                        fail('reopened quarantine root mismatch')
                    journal.write('delete-start', {'original': str(original), 'quarantine': str(quarantine),
                                                   'device': device, 'inode': inode})
                    delete_verified(fd, scoped(expected, quarantine), '', device, journal, str(original))
                finally:
                    os.close(fd)
                current = os.stat(quarantine.name, dir_fd=parentfd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (device, inode):
                    fail('quarantine root changed before final rmdir')
                os.rmdir(quarantine.name, dir_fd=parentfd)
                fsync_dir('/dev/shm')
                journal.write('delete-complete', {'original': str(original), 'quarantine': str(quarantine),
                                                  'survivors': [lstat_id(QC), lstat_id(QB)]})
        finally:
            os.close(parentfd)
        for path in (C, B, QC, QB):
            assert_absent(path)
        validate_old_lease()
        journal.write('old-lease-remove-before', {'lease': lstat_id(OLD_LEASE),
                                                  'lease_sha256': sha(OLD_LEASE),
                                                  'archive_sha256': RAW_ARCHIVE_SHA})
        os.unlink(OLD_LEASE)
        fsync_dir(SB)
        if OLD_LEASE.exists() or OLD_LEASE.is_symlink():
            fail('old lease remains after unlink')
        result = {'schema': 'mckernel.native-exact-candidate-quarantine-recovery-result.v1',
                  'targets_absent': True, 'old_lease_absent': True,
                  'claim_path': str(CLAIM), 'claim_sha256': sha(CLAIM),
                  'journal_path': str(JOURNAL), 'observer_sha256': OBSERVER_SHA,
                  'completed_at_utc': utcnow(), 'acceptance_credit': False}
        journal.write('terminal-success', result)
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    except BaseException as error:
        try:
            journal.write('terminal-failure', {'error': repr(error), 'old_lease': lstat_id(OLD_LEASE),
                                               'survivors': [lstat_id(C), lstat_id(B), lstat_id(QC), lstat_id(QB)]})
        except BaseException:
            pass
        raise
    finally:
        journal.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        assert OLD_LEASE_ID == (1831, 31447, 0o600, 0, 0)
        assert RELEASE_SHA == RELEASE_SENTINEL or re.fullmatch(r'[0-9a-f]{64}', RELEASE_SHA)
        print('quarantine recovery pure assertions passed')
    else:
        main()
