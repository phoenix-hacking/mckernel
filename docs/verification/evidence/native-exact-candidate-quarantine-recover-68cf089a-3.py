#!/usr/bin/env python3
"""DRAFT-only recovery-3 state machine; it deliberately cannot execute.

The observer result is an observation-interval proof only.  Root-owned 0700
quarantines must prevent new non-root pathname opens, while the packet must
independently exclude privileged/adversarial target mutation, reference
acquisition, and reference transfer during observation.  It is not an atomic
global /proc census claim.
"""
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
from pathlib import Path, PurePosixPath

REPO = Path('/home/holden/mckernel')
SB = Path('/home/holden/mckernel-work/scratch')
C = Path('/dev/shm/mckernel-exact-candidate-68cf089a-1')
B = Path('/dev/shm/mckernel-exact-metadata-backup-68cf089a-1')
QC = Path('/dev/shm/.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1')
QB = Path('/dev/shm/.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1')
ROOTS = ((C, QC, 26, 14117), (B, QB, 26, 24701))
OLD_LEASE = SB / 'native-exact-build-lease-68cf089a-1.json'
CLAIM1 = SB / 'native-exact-candidate-quarantine-recovery-consumed-68cf089a-1.json'
JOURNAL1 = SB / 'native-exact-candidate-quarantine-recovery-68cf089a-1.journal.jsonl'
CLAIM = SB / 'native-exact-candidate-quarantine-recovery3-claimed-68cf089a-3.json'
JOURNAL = SB / 'native-exact-candidate-quarantine-recovery3-68cf089a-3.journal.jsonl'
PREFLIGHT = SB / 'native-exact-candidate-quarantine-recovery3-preflight-68cf089a-3.json'
OBSERVER_OUT = SB / 'native-exact-candidate-quarantine-recovery3-observer-68cf089a-3.stdout.json'
OBSERVER_ERR = SB / 'native-exact-candidate-quarantine-recovery3-observer-68cf089a-3.stderr.txt'
RELEASE = SB / 'native-exact-candidate-quarantine-recovery3-release-68cf089a-3.json'
EVIDENCE = SB / 'native-exact-candidate-quarantine-recovery3-execution-68cf089a-3'
INVENTORY = SB / 'native-exact-complete-worktree-inventory-68cf089a-1.json'
INVENTORY_SHA = '743c05648112cee5af2eda235fba11a2f32d50a9d3074423c0c064d52a1682c0'
OBSERVER = REPO / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-2.py'
BASIS = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-release-basis-68cf089a-3.json'

ORIGINAL_RECORD = REPO / 'docs/verification/stability-native-exact-cleanup-failure-20260929-1.json'
ORIGINAL_RAW = REPO / 'docs/verification/evidence/stability-native-exact-cleanup-failure-raw-20260929-1.tar.gz'
RECOVERY1_RECORD = REPO / 'docs/verification/stability-native-exact-quarantine-recovery-failure-20260929-1.json'
RECOVERY1_RAW = REPO / 'docs/verification/evidence/stability-native-exact-quarantine-recovery-failure-raw-20260929-1.tar.gz'
ORIGINAL_RECORD_SHA = 'd2150a0a8173c0caaa4c5a6050653947e372480cd059d8d9ff49656dac76ed97'
ORIGINAL_RAW_SHA = 'cc38687005d52ecc4b0d48ffa9ff650832169ba9d426add604b0c4e0f8893eea'
OLD_JOURNAL_SHA = '6bf129586cd9edc9bb2b89519bdad2fb697606dea876eb6ecac1a86d43a04ebe'
OLD_LEASE_SHA = '69ced2395f7c16019b70d9d1b2de45ff2519014178ee145a453e2ed2a24f47e3'
OLD_LEASE_ID = (1831, 31447, 0o600, 0, 0)
RECOVERY1_RECORD_SHA = '2cb8dc42fccd68bcb9c5db1b6a78fa0eb9b478e9f81e5c46c14a8514d7948a7c'
RECOVERY1_RAW_SHA = '0a3e13ec06ba3e7efd0282ab3efd9f51ad18e6261bef6c0691a1ec29700878b5'
CLAIM1_SHA = 'f2d59c24e20b589f5cb9aa9cba1ec4c9c9ba4a84895fe3a468de35d7b5bb41f3'
JOURNAL1_SHA = 'd9a17002fe43df822c367219a4dc58e7a7bb000bce6597a79a5dc6721fe850d4'
PREFLIGHT1_SHA = 'e7af78ba3189eddfc940101f5051038143d3e3624fd65c6c44817a5f736468cf'
RELEASE1_SHA = 'bef067a447793acefc51c0afdf15698766e18f984473c22a80ebda43ffd47983'
OUT1_SHA = '23b098adccd1986cbd6026904e620fc6d997cf256c0d20f66c4dffd7bbb027bd'
ERR1_SHA = '65efce0898ea451dc4af0a0682296e194bcef16707fafaa641bfbd36eabc9512'
OBSERVER_SHA = '71fc9f54c6f7ac8a2e8030ac5a802e2c1354ac0f0ed4cf2737c0c9486a7d3bfa'
OBSERVER_SOURCE_RECORD = REPO / 'docs/verification/stability-native-exact-live-reference-observer-v2-source-success-20260929-1.json'
OBSERVER_SOURCE_RECORD_SHA = '2b4532f37ebbe29980ee93cbf7888dce461f247361ce445c54a59f8fba0b2259'
RELEASE_SENTINEL = 'UNSET-REQUIRES-INDEPENDENT-RECOVERY3-RELEASE-SHA256'
RELEASE_SHA = '46a9e89174b816b492d2069d2ac554cbde43dfcffc61f692d353861df9d47270'
PACKET = BASIS.with_name('native-exact-candidate-quarantine-recovery-execution-68cf089a-3.sh')
TEST = REPO / 'scripts/tests/test_native_exact_candidate_quarantine_recovery_v3.py'
EXECUTION_RELEASE = REPO / 'docs/verification/stability-native-exact-quarantine-recovery3-execution-release-20260929-1.json'
PACKET_HELPER_SENTINEL = '__REPLACE_WITH_FINAL_RECOVERY3_HELPER_SHA256__'
SOURCE_SENTINEL = 'UNSET_REQUIRES_FETCHED_TEMPLATE_CHECKPOINT'
THREAT = ('Quarantines remain root-owned 0700; privileged/adversarial target mutation, '
          'reference acquisition, and reference transfer are independently excluded throughout '
          'observation AND deletion. This is an operational assumption, not machine proof or an atomic census.')
HISTORICAL_HELPER_SHA = 'dcb7283805a012590ab35d734ba10cc3992db9d587e32e70c2031296669c9735'
HISTORICAL_PACKET_SHA = 'ab2283d612591d76a92898bdee107d48da331d3588ec63bf9d660e214886abac'
HISTORICAL_EXECUTION_RELEASE_SHA = '4223d34efeb0eddbd919ce9f7cb11d10eec46d3760a54e7a362cef543e9931b7'
OBSERVER_TEST_SHA = '092061125463eda4a332c3354d8a94190bc9ca4c9f5c1ad5269ea08d7bae5a19'
RECOVERY2_RECORD = REPO / 'docs/verification/stability-native-exact-quarantine-recovery2-failure-20260929-1.json'
RECOVERY2_RAW = REPO / 'docs/verification/evidence/stability-native-exact-quarantine-recovery2-failure-raw-20260929-1.tar.gz'
RECOVERY2_RECORD_SHA = 'fbdffcf75f073f22434bbdf43e52281e7bb8a99a30d14c9b1783f057ee133e3b'
RECOVERY2_RAW_SHA = '93fde8f0143931fb2e3105c2a30b94f5480b933dd8f6d9c9348fc5195edce424'
RECOVERY2_BASIS_SHA = '4c50f12c5b500d2ecde1750f47b07b820ba43721c613d13176427440294f8b5a'
RECOVERY2_HELPER_SHA = '5ac3601bb9dc95cc1dba48793239769c06a26651ef6d75cec9a7793f6962f641'
RECOVERY2_PACKET_SHA = 'cc20d87719f2827f21d695cf275bb5890085251ae44e5c2819c7487e10627d46'
RECOVERY2_TEST_SHA = '5d25dc0779568f652f6d11d13d20e7e0862f92c2fc95da85eeaf2f15ee86b195'
RECOVERY2_EXECUTION_RELEASE_SHA = '7dc1b2b15c45408f4bd899f640d80e456ef6bc93cc9070eceabdecd278badc0d'
RECOVERY2_PREFLIGHT_SHA = '468b1d4d765b8d3ff35ff3c638ebcfec16abae153a78ede2097c9a33e1441dec'
CLAIM2 = SB / 'native-exact-candidate-quarantine-recovery2-claimed-68cf089a-2.json'
JOURNAL2 = SB / 'native-exact-candidate-quarantine-recovery2-68cf089a-2.journal.jsonl'
EVIDENCE2 = SB / 'native-exact-candidate-quarantine-recovery2-execution-68cf089a-2'
PREFLIGHT2 = SB / 'native-exact-candidate-quarantine-recovery2-preflight-68cf089a-2.json'
RELEASE2 = SB / 'native-exact-candidate-quarantine-recovery2-release-68cf089a-2.json'
RECOVERY2_OUTPUT_HASHES = {
    'process-preflight.result.json': '71549c7039cc3d8f54d9f042f682aae3fcf264d27055f6c85485dac49e976909',
    'process-preflight.stderr': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'process-preflight.stdout': '4866355721a9683893bed3088c4744c2b488046772c392e1743ba5cf37237e7a',
    'recovery.rc': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865',
    'recovery.stderr': 'a1a0b2a389eece4c306dd8a5beacf44d7f8b3344442d398b572519744da937e9',
    'recovery.stdout': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
}


def fail(message):
    raise RuntimeError(message)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest_bytes(Path(path).read_bytes())


def no_duplicates(items):
    answer = {}
    for key, value in items:
        if key in answer:
            fail('duplicate JSON key: ' + key)
        answer[key] = value
    return answer


def exact_json_bytes(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=no_duplicates)


def validate_journal_bytes(data, expected_sha, phases, label):
    if digest_bytes(data) != expected_sha:
        fail(label + ' journal hash mismatch')
    records = [exact_json_bytes(line) for line in data.splitlines() if line]
    if [record.get('phase') for record in records] != phases:
        fail(label + ' journal phase sequence mismatch')
    prohibited = {'delete-entry', 'delete-start', 'delete-complete', 'old-lease-remove-before', 'terminal-success'}
    if prohibited.intersection(record.get('phase') for record in records):
        fail(label + ' journal contains deletion phase')
    return records


def validate_archive_members(archive_path, required):
    with tarfile.open(archive_path, 'r:gz') as archive:
        for name, wanted in required.items():
            found = [member for member in archive.getmembers() if member.name == name and member.isfile()]
            if len(found) != 1 or digest_bytes(archive.extractfile(found[0]).read()) != wanted:
                fail('archive member mismatch: ' + name)


def archive_member_bytes(archive_path, name):
    with tarfile.open(archive_path, 'r:gz') as archive:
        found = [member for member in archive.getmembers() if member.name == name and member.isfile()]
        if len(found) != 1:
            fail('archive member missing: ' + name)
        return archive.extractfile(found[0]).read()


def validate_historical_archives():
    validate_recovery2_history()
    if sha(ORIGINAL_RAW) != ORIGINAL_RAW_SHA or sha(RECOVERY1_RAW) != RECOVERY1_RAW_SHA:
        fail('historical raw archive hash mismatch')
    prefix = 'home/holden/mckernel-work/scratch/'
    validate_archive_members(ORIGINAL_RAW, {prefix + 'native-exact-build-lease-68cf089a-1.json': OLD_LEASE_SHA})
    validate_archive_members(RECOVERY1_RAW, {
        prefix + 'native-exact-candidate-quarantine-recovery-consumed-68cf089a-1.json': CLAIM1_SHA,
        prefix + 'native-exact-candidate-quarantine-recovery-preflight-68cf089a-1.json': PREFLIGHT1_SHA,
        prefix + 'native-exact-candidate-quarantine-recovery-release-68cf089a-1.json': RELEASE1_SHA,
        prefix + 'native-exact-candidate-quarantine-recovery-observer-68cf089a-1.stdout.json': OUT1_SHA,
        prefix + 'native-exact-candidate-quarantine-recovery-observer-68cf089a-1.stderr.txt': ERR1_SHA})
    validate_journal_bytes(archive_member_bytes(ORIGINAL_RAW, prefix + 'native-exact-candidate-delete-68cf089a-1.journal.jsonl'),
                           OLD_JOURNAL_SHA,
                           ['lease-acquired', 'seal-before', 'seal-after', 'quarantine-after', 'seal-before',
                            'seal-after', 'quarantine-after', 'target-fds-closed', 'terminal-failure'], 'original')
    validate_journal_bytes(archive_member_bytes(RECOVERY1_RAW, prefix + 'native-exact-candidate-quarantine-recovery-68cf089a-1.journal.jsonl'),
                           JOURNAL1_SHA, ['recovery-claimed', 'inventory-reconstructed', 'terminal-failure'], 'recovery-1')


def validate_historical_records(original, recovery1):
    if sha(ORIGINAL_RECORD) != ORIGINAL_RECORD_SHA or sha(RECOVERY1_RECORD) != RECOVERY1_RECORD_SHA:
        fail('historical failure record hash mismatch')
    for path, wanted in (
            (BASIS.with_name('native-exact-candidate-quarantine-recover-68cf089a-1.py'), HISTORICAL_HELPER_SHA),
            (BASIS.with_name('native-exact-candidate-quarantine-recovery-execution-68cf089a-1.sh'), HISTORICAL_PACKET_SHA),
            (BASIS.with_name('native-exact-candidate-quarantine-recovery-release-basis-68cf089a-1.json'), RELEASE1_SHA),
            (REPO / 'docs/verification/stability-native-exact-quarantine-recovery-execution-release-20260929-1.json',
             HISTORICAL_EXECUTION_RELEASE_SHA)):
        if digest_bytes(read_regular(path)) != wanted:
            fail('historical source/execution release binding mismatch')
    if original.get('status') != 'FAIL_PRESERVED' or original.get('deletion_started') is not False:
        fail('original failure record semantics mismatch')
    retained = recovery1.get('retained_artifacts', {})
    state = recovery1.get('retained_state', {})
    if (recovery1.get('status') != 'FAIL_OBSERVER_TASK_CHURN_BEFORE_DELETION' or
            retained.get('claim_sha256') != CLAIM1_SHA or retained.get('journal_sha256') != JOURNAL1_SHA or
            retained.get('preflight_sha256') != PREFLIGHT1_SHA or retained.get('release_sha256') != RELEASE1_SHA or
            retained.get('observer_stdout_sha256') != OUT1_SHA or retained.get('observer_stderr_sha256') != ERR1_SHA or
            state.get('deletion_phase_count') != 0 or state.get('recovery_claim_retained') is not True):
        fail('recovery-1 failure record semantics mismatch')


def validate_observer_source_record():
    if sha(OBSERVER) != OBSERVER_SHA or sha(OBSERVER_SOURCE_RECORD) != OBSERVER_SOURCE_RECORD_SHA:
        fail('observer-v2 source binding mismatch')
    if sha(REPO / 'scripts/tests/test_native_exact_candidate_live_reference_observer_v2.py') != OBSERVER_TEST_SHA:
        fail('observer-v2 test binding mismatch')


def recovery2_retained_hashes():
    return {**{EVIDENCE2 / name: digest for name, digest in RECOVERY2_OUTPUT_HASHES.items()},
            PREFLIGHT2: RECOVERY2_PREFLIGHT_SHA, RELEASE2: RECOVERY2_BASIS_SHA}


def validate_recovery2_history():
    """Bind the consumed admission failure; none of its inputs becomes an output."""
    paths = {
        RECOVERY2_RECORD: RECOVERY2_RECORD_SHA, RECOVERY2_RAW: RECOVERY2_RAW_SHA,
        BASIS.with_name('native-exact-candidate-quarantine-recovery-release-basis-68cf089a-2.json'): RECOVERY2_BASIS_SHA,
        BASIS.with_name('native-exact-candidate-quarantine-recover-68cf089a-2.py'): RECOVERY2_HELPER_SHA,
        BASIS.with_name('native-exact-candidate-quarantine-recovery-execution-68cf089a-2.sh'): RECOVERY2_PACKET_SHA,
        REPO / 'scripts/tests/test_native_exact_candidate_quarantine_recovery_v2.py': RECOVERY2_TEST_SHA,
        REPO / 'docs/verification/stability-native-exact-quarantine-recovery2-execution-release-20260929-1.json':
            RECOVERY2_EXECUTION_RELEASE_SHA,
    }
    for path, expected in paths.items():
        if digest_bytes(read_regular(path)) != expected:
            fail('recovery2 historical input mismatch: ' + str(path))
    value = exact_json_bytes(read_regular(RECOVERY2_RECORD))
    state = value.get('retained_state', {})
    artifacts = value.get('retained_artifacts', {})
    if (value.get('status') != 'FAIL_SOURCE_ADMISSION_BEFORE_CLAIM' or
            any(state.get(key) is not False for key in ('deletion_started', 'journal_created', 'new_claim_created')) or
            state.get('original_paths_absent') is not True or
            state.get('previous_claim_sha256') != CLAIM1_SHA or state.get('previous_journal_sha256') != JOURNAL1_SHA or
            artifacts.get('preflight_sha256') != RECOVERY2_PREFLIGHT_SHA or
            artifacts.get('release_copy_sha256') != RECOVERY2_BASIS_SHA or
            artifacts.get('raw_archive_sha256') != RECOVERY2_RAW_SHA or value.get('runtime_acceptance') is not False):
        fail('recovery2 failure semantics mismatch')
    required = {str(path.relative_to('/')): digest for path, digest in recovery2_retained_hashes().items()}
    validate_archive_members(RECOVERY2_RAW, required)
    with tarfile.open(RECOVERY2_RAW, 'r:gz') as archive:
        members = archive.getmembers()
        expected_dir = str(EVIDENCE2.relative_to('/'))
        if (len(members) != 9 or {member.name for member in members if member.isfile()} != set(required) or
                [member.name.rstrip('/') for member in members if member.isdir()] != [expected_dir] or
                any(not (member.isfile() or member.isdir()) for member in members)):
            fail('recovery2 failure archive membership mismatch')


def validate_recovery2_retained_state():
    for path in (CLAIM2, JOURNAL2):
        if os.path.lexists(path):
            fail('recovery2 unexpectedly created claim/journal')
    info = os.lstat(EVIDENCE2)
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
        fail('recovery2 evidence directory identity/type mismatch')
    if set(os.listdir(EVIDENCE2)) != set(RECOVERY2_OUTPUT_HASHES):
        fail('recovery2 evidence membership changed')
    for path, expected in recovery2_retained_hashes().items():
        if digest_bytes(read_regular(path)) != expected:
            fail('recovery2 retained evidence mismatch: ' + str(path))


def validate_observer_result(value, member_sets):
    if (value.get('schema') != 'mckernel.read-only-live-reference-snapshot.v7' or
            value.get('status') != 'PASS' or value.get('scan_complete') is not True or
            value.get('observer_sha256') != OBSERVER_SHA or value.get('failure') is not None):
        fail('observer v7 scalar mismatch')
    for key in ('permission_denials', 'target_references', 'tree_revalidation_failures',
                'persistent_tree_revalidation_failures', 'unscanned_final_identities'):
        if key in value and value[key] != []:
            fail('observer sticky top-level finding: ' + key)
    if value.get('complete_mount_proofs', True) is not True:
        fail('observer top-level incomplete mount proof')
    if (type(value.get('tree_observation_transients')) is not list or
            value.get('persistent_tree_revalidation_failures') != []):
        fail('observer tree state missing')
    roots = value.get('roots')
    if type(roots) is not list or len(roots) != len(ROOTS) or len(member_sets) != len(ROOTS):
        fail('observer roots missing')
    for root, expected, members in zip(roots, ROOTS, member_sets):
        _original, quarantine, device, inode = expected
        if (root.get('path'), root.get('device_number'), root.get('inode'), root.get('mode')) != (
                str(quarantine), device, inode, '0700'):
            fail('observer root identity mismatch')
        if root.get('tree_member_identities') != [list(item) for item in sorted(members)]:
            fail('observer descriptor inventory membership mismatch')
    rounds = value.get('rounds')
    if type(rounds) is not list or not 2 <= len(rounds) <= 5:
        fail('observer round count mismatch')
    for number, row in enumerate(rounds, 1):
        if row.get('round') != number:
            fail('observer round sequence mismatch')
        # Early benign identity churn may converge; unsafe observations are sticky.
        for key in ('target_references', 'permission_denials', 'tree_revalidation_failures'):
            if row.get(key) != []:
                fail('observer sticky finding: ' + key)
        if row.get('complete_mount_proofs') is not True:
            fail('observer incomplete mount proof')
        for key in ('unscanned_final_identities', 'unresolved_churn'):
            if type(row.get(key)) is not list:
                fail('observer closure field missing')
        if type(row.get('closure_nonconvergent')) is not bool or type(row.get('clean')) is not bool:
            fail('observer closure boolean missing')
    for row in rounds[-2:]:
        if (row['clean'] is not True or row['unscanned_final_identities'] != [] or
                row['unresolved_churn'] != [] or row['closure_nonconvergent'] is not False):
            fail('observer final two rounds are not closure-clean')


def full_write(fd, data, write=os.write):
    offset = 0
    while offset < len(data):
        count = write(fd, data[offset:])
        if not isinstance(count, int) or count <= 0 or count > len(data) - offset:
            fail('short or invalid write')
        offset += count


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_fd(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        fsync_dir(Path(path).parent)
    except BaseException:
        os.close(fd)
        raise
    return fd


def write_exclusive(path, value):
    data = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True) + '\n').encode()
    fd = exclusive_fd(path)
    try:
        full_write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            fail('not a regular input: ' + str(path))
        data = b''.join(iter(lambda: os.read(fd, 1 << 20), b''))
        after = os.fstat(fd)
        if identity(before) != identity(after) or before.st_size != after.st_size:
            fail('input changed while reading')
        named = os.stat(path, follow_symlinks=False)
        if identity(named) != identity(after):
            fail('input name changed while reading')
        return data
    finally:
        os.close(fd)


def identity(info):
    return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode),
            stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def wanted_identity(info):
    return {'dev': info.st_dev, 'inode': info.st_ino,
            'type': ('directory' if stat.S_ISDIR(info.st_mode) else
                     'file' if stat.S_ISREG(info.st_mode) else
                     'symlink' if stat.S_ISLNK(info.st_mode) else 'unsupported'),
            'mode': format(stat.S_IMODE(info.st_mode), '04o'),
            'uid': info.st_uid, 'gid': info.st_gid}


def assert_identity(info, wanted):
    actual = wanted_identity(info)
    if any(actual[key] != wanted[key] for key in ('dev', 'inode', 'type', 'mode', 'uid', 'gid')):
        fail('descriptor/name identity mismatch')


def open_checked(parentfd, name, wanted, opener=os.open):
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if wanted['type'] == 'directory':
        flags |= os.O_DIRECTORY
    before = os.stat(name, dir_fd=parentfd, follow_symlinks=False)
    assert_identity(before, wanted)
    fd = opener(name, flags, dir_fd=parentfd)
    try:
        assert_identity(os.fstat(fd), wanted)
        assert_identity(os.stat(name, dir_fd=parentfd, follow_symlinks=False), wanted)
        return fd
    except BaseException:
        os.close(fd)
        raise


def root_wanted(device, inode):
    return dict(dev=device, inode=inode, type='directory', mode='0700', uid=0, gid=0)


def validate_inventory_bytes(data, expected_sha=INVENTORY_SHA, roots=(C, B), counts=(10462, 87)):
    if digest_bytes(data) != expected_sha:
        fail('inventory hash mismatch')
    value = exact_json_bytes(data)
    if (set(value) != {'schema_version', 'roots', 'worktree_inventory'} or value.get('schema_version') != 1 or
            value.get('roots') != [str(root) for root in roots] or type(value.get('worktree_inventory')) is not list):
        fail('inventory schema/roots mismatch')
    prefixes = [str(root.relative_to('/')) for root in roots]
    actual_counts, names = [0] * len(roots), set()
    for row in value['worktree_inventory']:
        if type(row) is not dict or set(row) != {'path', 'type', 'mode', 'sha256'}:
            fail('inventory row schema mismatch')
        raw = row['path']
        if not isinstance(raw, str):
            fail('inventory path type')
        name = raw.rstrip('/')
        if (not name or str(PurePosixPath(name)) != name or PurePosixPath(name).is_absolute() or
                '..' in PurePosixPath(name).parts or name in names or
                (raw != name and (raw != name + '/' or row['type'] != 'directory'))):
            fail('inventory path malformed/duplicate')
        names.add(name)
        if (row['type'] not in ('file', 'directory', 'symlink') or
                not isinstance(row['mode'], str) or not re.fullmatch(r'[0-7]{4}', row['mode']) or
                (row['type'] == 'directory' and row['sha256'] is not None) or
                (row['type'] != 'directory' and not re.fullmatch(r'[0-9a-f]{64}', str(row['sha256'])))):
            fail('inventory type/mode/digest malformed')
        matches = [i for i, prefix in enumerate(prefixes) if name == prefix or name.startswith(prefix + '/')]
        if len(matches) != 1:
            fail('inventory row outside roots')
        actual_counts[matches[0]] += 1
    if actual_counts != list(counts):
        fail('inventory root count mismatch')
    return value


def validate_inventory_input():
    return validate_inventory_bytes(read_regular(INVENTORY))


def reconstruct_inventory(manifest, roots):
    rows = {row['path'].rstrip('/'): row for row in manifest['worktree_inventory']}
    result = {}
    for original, quarantine, device, inode in roots:
        prefix = str(original.relative_to('/'))
        parentfd = os.open(quarantine.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            rootfd = open_checked(parentfd, quarantine.name, root_wanted(device, inode))
            try:
                seen = set()
                def walk(fd, relative):
                    name = prefix + ('/' + relative if relative else '')
                    wanted = rows.get(name)
                    current = wanted_identity(os.fstat(fd))
                    if (wanted is None or wanted['type'] != 'directory' or current['dev'] != device or
                            current['mode'] != ('0700' if not relative else wanted['mode'])):
                        fail('inventory directory mismatch')
                    seen.add(name)
                    if relative:
                        result[(str(quarantine), relative)] = dict(wanted, **current)
                    for child_name in sorted(os.listdir(fd)):
                        rel = relative + '/' + child_name if relative else child_name
                        full = prefix + '/' + rel
                        wanted = rows.get(full)
                        info = os.stat(child_name, dir_fd=fd, follow_symlinks=False)
                        current = wanted_identity(info)
                        if (wanted is None or current['dev'] != device or
                                any(current[key] != wanted[key] for key in ('type', 'mode'))):
                            fail('inventory entry mismatch')
                        if current['type'] == 'directory':
                            child = open_checked(fd, child_name, current)
                            try:
                                walk(child, rel)
                            finally:
                                os.close(child)
                        else:
                            if current['type'] == 'file':
                                child = open_checked(fd, child_name, current)
                                try:
                                    hasher = hashlib.sha256()
                                    for block in iter(lambda: os.read(child, 1 << 20), b''):
                                        hasher.update(block)
                                    assert_identity(os.fstat(child), current)
                                    digest = hasher.hexdigest()
                                finally:
                                    os.close(child)
                            elif current['type'] == 'symlink':
                                digest = digest_bytes(os.fsencode(os.readlink(child_name, dir_fd=fd)))
                            else:
                                fail('unsupported inventory inode')
                            assert_identity(os.stat(child_name, dir_fd=fd, follow_symlinks=False), current)
                            if digest != wanted['sha256']:
                                fail('inventory content mismatch')
                            seen.add(full)
                            result[(str(quarantine), rel)] = dict(wanted, **current)
                walk(rootfd, '')
                if seen != {name for name in rows if name == prefix or name.startswith(prefix + '/')}:
                    fail('inventory membership mismatch')
                assert_identity(os.fstat(rootfd), root_wanted(device, inode))
                assert_identity(os.stat(quarantine.name, dir_fd=parentfd, follow_symlinks=False),
                                root_wanted(device, inode))
            finally:
                os.close(rootfd)
        finally:
            os.close(parentfd)
    return result


def inventory_member_sets(expected):
    return [{(device, inode)} | {(row['dev'], row['inode']) for (root, _rel), row in expected.items()
                                if root == str(quarantine)}
            for _original, quarantine, device, inode in ROOTS]


def delete_verified(fd, expected, prefix, device, journal, root_name, expected_dir=None):
    if expected_dir is None:
        fail('directory descriptor expectation required')
    assert_identity(os.fstat(fd), expected_dir)
    direct = {name[len(prefix):].split('/', 1)[0] for name in expected if name.startswith(prefix)}
    if set(os.listdir(fd)) != direct:
        fail('descriptor inventory changed')
    for name in sorted(direct):
        rel, wanted = prefix + name, expected[prefix + name]
        assert_identity(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted)
        if wanted['dev'] != device:
            fail('cross-device entry')
        if wanted['type'] == 'directory':
            child = open_checked(fd, name, wanted)
            try:
                delete_verified(child, expected, rel + '/', device, journal, root_name, wanted)
                assert_identity(os.fstat(child), wanted)
                assert_identity(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted)
                journal.write('delete-entry', dict(root=root_name, path=rel, operation='rmdir'))
                os.rmdir(name, dir_fd=fd)
                os.fsync(fd)
            finally:
                os.close(child)
        else:
            if wanted['type'] == 'file':
                child = open_checked(fd, name, wanted)
                try:
                    hasher = hashlib.sha256()
                    for block in iter(lambda: os.read(child, 1 << 20), b''):
                        hasher.update(block)
                    assert_identity(os.fstat(child), wanted)
                    digest = hasher.hexdigest()
                finally:
                    os.close(child)
            elif wanted['type'] == 'symlink':
                digest = digest_bytes(os.fsencode(os.readlink(name, dir_fd=fd)))
            else:
                fail('unsupported inode')
            if digest != wanted['sha256']:
                fail('delete content mismatch')
            assert_identity(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted)
            journal.write('delete-entry', dict(root=root_name, path=rel, operation='unlink'))
            os.unlink(name, dir_fd=fd)
            os.fsync(fd)
    assert_identity(os.fstat(fd), expected_dir)


class Journal:
    def __init__(self, path=JOURNAL):
        self.fd = exclusive_fd(path)
    def write(self, phase, fields):
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            full_write(self.fd, (json.dumps(dict(phase=phase, **fields), sort_keys=True) + '\n').encode())
            os.fsync(self.fd)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    def close(self):
        os.close(self.fd)


def create_claim(path=CLAIM, release_sha=RELEASE_SHA, helper_sha=None):
    write_exclusive(path, dict(schema='mckernel.recovery3-claim.v2',
                              original_journal_sha256=OLD_JOURNAL_SHA,
                              recovery1_claim_sha256=CLAIM1_SHA, recovery1_journal_sha256=JOURNAL1_SHA,
                              recovery2_failure_sha256=RECOVERY2_RECORD_SHA, recovery2_raw_sha256=RECOVERY2_RAW_SHA,
                              recovery2_preflight_sha256=RECOVERY2_PREFLIGHT_SHA,
                              observer_v2_sha256=OBSERVER_SHA, release_sha256=release_sha,
                              helper_sha256=helper_sha or sha(Path(__file__))))


def survivor_state(protected=None, lease=None, claims=None):
    protected = (C, B, QC, QB) if protected is None else protected
    lease = OLD_LEASE if lease is None else lease
    claims = (CLAIM1, CLAIM2, JOURNAL2, CLAIM) if claims is None else claims
    def presence(path):
        try:
            info = os.lstat(path)
            return dict(present=True, identity=list(identity(info)))
        except FileNotFoundError:
            return dict(present=False)
        except OSError as error:
            return dict(present=None, observation_error=repr(error))
    return dict(paths={str(path): presence(path) for path in protected},
                old_lease=presence(lease), claims={str(path): presence(path) for path in claims})


def with_claimed_journal(action, journal_path=None, claim_path=None, snapshot=survivor_state):
    # Creation of the second object is deliberately inside the protected block.
    journal = Journal(JOURNAL if journal_path is None else journal_path)
    previous = {}
    def interrupted(signum, _frame):
        raise RuntimeError('interrupted by signal ' + str(signum))
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, interrupted)
        journal.write('journal-created', {'state': snapshot()})
        create_claim(CLAIM if claim_path is None else claim_path)
        journal.write('recovery3-claimed', {'state': snapshot()})
        result = action(journal)
        journal.write('terminal-success', {'state': snapshot(), 'result': result})
        return result
    except BaseException as error:
        # Do not misreport lease retention if failure follows its successful unlink.
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        journal.write('terminal-failure', {'error': repr(error), 'state': snapshot()})
        raise
    finally:
        journal.close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def remove_old_lease_after_absence(journal, lease=OLD_LEASE, protected=(C, B, QC, QB),
                                   expected_sha=OLD_LEASE_SHA, expected_identity=OLD_LEASE_ID):
    if any(os.path.lexists(path) for path in protected):
        fail('protected path remains before old lease removal')
    parentfd = os.open(Path(lease).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        wanted = dict(zip(('dev', 'inode', 'mode', 'uid', 'gid'), expected_identity))
        wanted.update(type='file', mode=format(wanted['mode'], '04o'))
        fd = open_checked(parentfd, Path(lease).name, wanted)
        data = b''.join(iter(lambda: os.read(fd, 1 << 20), b''))
        if digest_bytes(data) != expected_sha:
            fail('old lease digest mismatch')
        assert_identity(os.fstat(fd), wanted)
        assert_identity(os.stat(Path(lease).name, dir_fd=parentfd, follow_symlinks=False), wanted)
        if any(os.path.lexists(path) for path in protected):
            fail('protected path reappeared before lease removal')
        journal.write('old-lease-remove-before', {'path': str(lease), 'validated': True})
        os.unlink(Path(lease).name, dir_fd=parentfd)
        os.fsync(parentfd)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parentfd)


def rmdir_root_verified(quarantine, device, inode, journal):
    parentfd = os.open(Path(quarantine).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        wanted = root_wanted(device, inode)
        fd = open_checked(parentfd, Path(quarantine).name, wanted)
        try:
            if os.listdir(fd):
                fail('root not empty')
            assert_identity(os.fstat(fd), wanted)
            assert_identity(os.stat(Path(quarantine).name, dir_fd=parentfd, follow_symlinks=False), wanted)
            journal.write('root-rmdir', dict(path=str(quarantine), inode=inode))
            os.rmdir(Path(quarantine).name, dir_fd=parentfd)
            os.fsync(parentfd)
        finally:
            os.close(fd)
    finally:
        os.close(parentfd)


def validate_current_state():
    validate_recovery2_retained_state()
    for path in (C, B):
        if os.path.lexists(path):
            fail('original path unexpectedly present')
    for _original, quarantine, device, inode in ROOTS:
        assert_identity(os.lstat(quarantine), root_wanted(device, inode))
    info = os.lstat(OLD_LEASE)
    if (not stat.S_ISREG(info.st_mode) or
            (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid) != OLD_LEASE_ID):
        fail('old lease identity mismatch')
    for path, wanted in ((OLD_LEASE, OLD_LEASE_SHA), (CLAIM1, CLAIM1_SHA), (JOURNAL1, JOURNAL1_SHA)):
        if digest_bytes(read_regular(path)) != wanted:
            fail('retained recovery state hash mismatch')


def historical_bindings():
    return dict(original_record=ORIGINAL_RECORD_SHA, original_raw=ORIGINAL_RAW_SHA,
                original_journal=OLD_JOURNAL_SHA, old_lease=OLD_LEASE_SHA,
                recovery1_record=RECOVERY1_RECORD_SHA, recovery1_raw=RECOVERY1_RAW_SHA,
                recovery1_claim=CLAIM1_SHA, recovery1_journal=JOURNAL1_SHA,
                recovery1_preflight=PREFLIGHT1_SHA, recovery1_basis=RELEASE1_SHA,
                recovery1_observer_stdout=OUT1_SHA, recovery1_observer_stderr=ERR1_SHA,
                recovery1_helper=HISTORICAL_HELPER_SHA, recovery1_packet=HISTORICAL_PACKET_SHA,
                recovery1_execution_release=HISTORICAL_EXECUTION_RELEASE_SHA,
                observer=OBSERVER_SHA, observer_test=OBSERVER_TEST_SHA,
                observer_source_record=OBSERVER_SOURCE_RECORD_SHA, inventory=INVENTORY_SHA,
                recovery2_record=RECOVERY2_RECORD_SHA, recovery2_raw=RECOVERY2_RAW_SHA,
                recovery2_basis=RECOVERY2_BASIS_SHA, recovery2_helper=RECOVERY2_HELPER_SHA,
                recovery2_packet=RECOVERY2_PACKET_SHA, recovery2_test=RECOVERY2_TEST_SHA,
                recovery2_execution_release=RECOVERY2_EXECUTION_RELEASE_SHA,
                recovery2_preflight=RECOVERY2_PREFLIGHT_SHA)


def normalize_helper(data, release_sha):
    old = ("RELEASE_SHA = '" + release_sha + "'").encode()
    if data.count(old) != 1:
        fail('helper release substitution not unique')
    return data.replace(old, ("RELEASE_SHA = '" + RELEASE_SENTINEL + "'").encode(), 1)


def normalize_packet(data, release_sha, helper_sha):
    for old, new in (
            ('RELEASE_SHA=' + release_sha, 'RELEASE_SHA=' + RELEASE_SENTINEL),
            ('FINAL_HELPER_SHA=' + helper_sha, 'FINAL_HELPER_SHA=' + PACKET_HELPER_SENTINEL)):
        if data.count((old + '\n').encode()) != 1:
            fail('packet substitution not unique')
        data = data.replace((old + '\n').encode(), (new + '\n').encode(), 1)
    return data


def validate_draft_basis(value):
    if (value.get('status') != 'DRAFT_NOT_RELEASED' or
            value.get('source_checkpoint') != SOURCE_SENTINEL or
            value.get('template_basis_sha256') != SOURCE_SENTINEL or
            value.get('execution_authorized') is not False or value.get('runtime_acceptance') is not False or
            'final_helper_sha256' in value or 'release_sha256' in value or
            value.get('operational_threat_assumption') != THREAT or
            value.get('historical_bindings') != historical_bindings()):
        fail('invalid DRAFT basis')
    return value


def validate_released_basis(value, basis_bytes=None, helper_bytes=None, packet_bytes=None, test_bytes=None,
                            release_sha=None):
    release_sha = RELEASE_SHA if release_sha is None else release_sha
    basis_bytes = read_regular(BASIS) if basis_bytes is None else basis_bytes
    helper_bytes = read_regular(Path(__file__)) if helper_bytes is None else helper_bytes
    packet_bytes = read_regular(PACKET) if packet_bytes is None else packet_bytes
    test_bytes = read_regular(TEST) if test_bytes is None else test_bytes
    if (value.get('status') != 'PASS_ONE_SHOT_QUARANTINE_RECOVERY3' or
            not re.fullmatch(r'[0-9a-f]{40}', value.get('source_checkpoint', '')) or
            not re.fullmatch(r'[0-9a-f]{64}', value.get('template_basis_sha256', '')) or
            value.get('execution_authorized') is not True or value.get('runtime_acceptance') is not False or
            'final_helper_sha256' in value or 'release_sha256' in value or
            value.get('operational_threat_assumption') != THREAT or
            value.get('historical_bindings') != historical_bindings()):
        fail('released basis scalar/history mismatch')
    if digest_bytes(basis_bytes) != release_sha or exact_json_bytes(basis_bytes) != value:
        fail('released basis hash/value mismatch')
    for key, data in (
            ('template_helper', normalize_helper(helper_bytes, release_sha)),
            ('template_packet', normalize_packet(packet_bytes, release_sha, digest_bytes(helper_bytes))),
            ('template_test', test_bytes)):
        if digest_bytes(data) != value.get(key, {}).get('sha256'):
            fail('released template normalization mismatch: ' + key)
    return value


def git_bytes(*args):
    return subprocess.check_output(['/usr/bin/git', '--git-dir=' + str(REPO / '.git'),
                                    '--work-tree=' + str(REPO), *args],
                                   stdin=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)


def validate_source(value):
    # Unrelated preexisting dirty/untracked work is allowed. These exact inputs are not.
    head = git_bytes('rev-parse', '--verify', 'HEAD').decode().strip()
    upstream = git_bytes('rev-parse', '--verify', '@{upstream}').decode().strip()
    fetched = git_bytes('rev-parse', '--verify', 'FETCH_HEAD').decode().strip()
    if not re.fullmatch(r'[0-9a-f]{40}', head) or head != upstream or head != fetched:
        fail('HEAD/upstream/fetched commit mismatch')
    source = value['source_checkpoint']
    files = (Path(__file__), PACKET, BASIS, TEST)
    for path in files:
        relative = str(path.relative_to(REPO))
        data = read_regular(path)
        if git_bytes('show', head + ':' + relative) != data:
            fail('final input differs from fetched Git blob: ' + relative)
        template = git_bytes('show', source + ':' + relative)
        if path == BASIS:
            if digest_bytes(template) != value['template_basis_sha256']:
                fail('template basis source mismatch')
            draft = exact_json_bytes(template)
            validate_draft_basis(draft)
            normalized = dict(value, status='DRAFT_NOT_RELEASED', source_checkpoint=SOURCE_SENTINEL,
                              template_basis_sha256=SOURCE_SENTINEL, execution_authorized=False)
            if draft != normalized:
                fail('final basis exceeded mechanical substitutions')
        else:
            key = 'template_helper' if path == Path(__file__) else 'template_packet' if path == PACKET else 'template_test'
            if value[key]['path'] != relative or digest_bytes(template) != value[key]['sha256']:
                fail('template Git blob mismatch')
    return head


def validate_execution_release(value, head):
    data = read_regular(EXECUTION_RELEASE)
    relative = str(EXECUTION_RELEASE.relative_to(REPO))
    if git_bytes('show', head + ':' + relative) != data:
        fail('execution release differs from fetched blob')
    release = exact_json_bytes(data)
    expected = dict(status='PASS_ONE_SHOT_QUARANTINE_RECOVERY3_EXECUTION', runtime_acceptance=False,
                    one_shot=True, retry=False, rollback=False,
                    source_checkpoint=value['source_checkpoint'], basis_sha256=RELEASE_SHA,
                    helper_sha256=sha(Path(__file__)), packet_sha256=sha(PACKET), test_sha256=sha(TEST),
                    operational_threat_assumption=THREAT)
    if any(release.get(key) != wanted for key, wanted in expected.items()):
        fail('separate final execution release mismatch')
    return digest_bytes(data)


def capacity():
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    result = dict(mem_available=int(mem['MemAvailable'].split()[0]) * 1024)
    for key, path in (('host_free', REPO), ('scratch_free', SB), ('tmpfs_free', Path('/dev/shm'))):
        item = os.statvfs(path)
        result[key] = item.f_bavail * item.f_frsize
    validate_capacity(result)
    return result


def validate_capacity(value):
    for key, floor in (('host_free', 16 << 30), ('scratch_free', 12 << 30),
                       ('tmpfs_free', 4 << 30), ('mem_available', 4 << 30)):
        if type(value.get(key)) is not int or value[key] < floor:
            fail('capacity below floor: ' + key)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def ancestors():
    result, pid = set(), os.getpid()
    while pid > 0 and pid not in result:
        result.add(pid)
        status = Path('/proc/' + str(pid) + '/status').read_text()
        pid = int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
    return result


def evaluate_processes(data, allowed):
    prohibited = {'make', 'gmake', 'cmake', 'ninja', 'ninja-build', 'cc', 'gcc', 'g++', 'clang', 'clang++',
                  'rustc', 'cargo', 'mcexec', 'cc1', 'cc1plus', 'collect2', 'as', 'ld', 'ld.lld',
                  'ccache', 'sccache'}
    owners = r'(?:native_rust_exact_build_(?:container_owner|offline)|(?:native|linux)_diagnostic_container_owner)\.py'
    parsed = []
    for line in data.decode('utf-8', errors='strict').splitlines():
        fields = line.split(None, 3)
        if len(fields) != 4:
            fail('malformed process capture')
        pid, ppid = int(fields[0]), int(fields[1])
        comm, args = fields[2:]
        if pid not in allowed and (comm in prohibited or comm.startswith('qemu') or
                re.fullmatch(r'(?:gcc|g\+\+|clang|clang\+\+)-[0-9.]+', comm) or
                re.search(r'(?:^|/|\s)(?:' + owners + r'|native-exact-candidate-(?:quarantine-recover|delete)[^\s]*\.py)(?:\s|$)', args)):
            fail('prohibited process owner: ' + str(pid) + ' ' + comm)
        parsed.append(dict(pid=pid, ppid=ppid, comm=comm))
    if not parsed:
        fail('empty process capture')
    return parsed


def capture_command(argv, stem, run=subprocess.run, timeout=30):
    out = exclusive_fd(EVIDENCE / (stem + '.stdout'))
    err = None
    result = None
    error = None
    try:
        err = exclusive_fd(EVIDENCE / (stem + '.stderr'))
        try:
            result = run(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                         check=False, timeout=timeout)
        except BaseException as caught:
            error = caught
        finally:
            os.fsync(out)
            os.fsync(err)
    finally:
        os.close(out)
        if err is not None:
            os.close(err)
    write_exclusive(EVIDENCE / (stem + '.result.json'),
                    dict(argv=argv, returncode=None if result is None else result.returncode,
                         error=None if error is None else repr(error)))
    if error is not None:
        raise error
    if result.returncode != 0:
        fail('capture command failed: ' + stem)
    return read_regular(EVIDENCE / (stem + '.stdout'))


def root_observation():
    result = []
    for original, quarantine, device, inode in ROOTS:
        if os.path.lexists(original):
            fail('original root present')
        info = os.lstat(quarantine)
        assert_identity(info, root_wanted(device, inode))
        result.append(dict(path=str(quarantine), identity=list(identity(info))))
    return result


def prepare_packet():
    basis = exact_json_bytes(read_regular(BASIS))
    if basis.get('status') == 'DRAFT_NOT_RELEASED':
        validate_draft_basis(basis)
        fail('DRAFT recovery-3 is non-executable')
    if os.geteuid() == 0:
        fail('packet must start non-root')
    validate_released_basis(basis)
    head = validate_source(basis)
    execution_sha = validate_execution_release(basis, head)
    validate_recovery2_retained_state()
    # mkdir is an atomic exclusive reservation of this output directory.
    for path in (EVIDENCE, PREFLIGHT, CLAIM, JOURNAL, OBSERVER_OUT, OBSERVER_ERR, RELEASE):
        if os.path.lexists(path):
            fail('one-shot output already exists: ' + str(path))
    os.mkdir(EVIDENCE, 0o700)
    fsync_dir(SB)
    allowed = sorted(ancestors())
    data = capture_command(['/usr/bin/ps', '-eo', 'pid=,ppid=,comm=,args='], 'process-preflight')
    processes = evaluate_processes(data, set(allowed))
    value = dict(schema='mckernel.recovery3-preflight.v2', boot_id=boot_id(),
                 monotonic=time.monotonic(), wall_time=time.time(), helper_sha256=sha(Path(__file__)),
                 packet_sha256=sha(PACKET), basis_sha256=RELEASE_SHA, test_sha256=sha(TEST),
                 source_checkpoint=basis['source_checkpoint'], head=head, execution_release_sha256=execution_sha,
                 roots=root_observation(), capacity=capacity(), process_sha256=digest_bytes(data),
                 process_allowed_ancestors=allowed, process_rows=processes, prepare_pid=os.getpid(),
                 operational_threat_assumption=THREAT, historical_bindings=historical_bindings(),
                 old_state=survivor_state())
    write_exclusive(RELEASE, read_regular(BASIS))
    write_exclusive(PREFLIGHT, value)
    fsync_dir(EVIDENCE)


def validate_preflight(value, basis, head, execution_sha, process_data, now=None, boot=None):
    now = time.monotonic() if now is None else now
    boot = boot_id() if boot is None else boot
    expected = dict(schema='mckernel.recovery3-preflight.v2', boot_id=boot,
                    helper_sha256=sha(Path(__file__)), packet_sha256=sha(PACKET), basis_sha256=RELEASE_SHA,
                    test_sha256=sha(TEST), source_checkpoint=basis['source_checkpoint'], head=head,
                    execution_release_sha256=execution_sha, operational_threat_assumption=THREAT,
                    historical_bindings=historical_bindings())
    if any(value.get(key) != wanted for key, wanted in expected.items()):
        fail('preflight source/boot/assumption mismatch')
    if not isinstance(value.get('monotonic'), (int, float)) or not 0 <= now - value['monotonic'] <= 120:
        fail('stale preflight')
    if not isinstance(value.get('wall_time'), (int, float)) or abs(time.time() - value['wall_time']) > 120:
        fail('preflight wall time mismatch')
    if value.get('roots') != root_observation() or value.get('old_state') != survivor_state():
        fail('preflight retained state mismatch')
    validate_capacity(value.get('capacity', {}))
    capacity()
    allowed = value.get('process_allowed_ancestors')
    if type(allowed) is not list or not all(type(pid) is int and pid > 0 for pid in allowed):
        fail('preflight process ancestry missing')
    prepare_pid = value.get('prepare_pid')
    if (type(prepare_pid) is not int or prepare_pid not in allowed or
            os.path.exists('/proc/' + str(prepare_pid)) or
            not (set(allowed) - {prepare_pid}).issubset(ancestors())):
        fail('preflight process ancestry changed')
    if digest_bytes(process_data) != value.get('process_sha256'):
        fail('preflight process capture hash mismatch')
    if evaluate_processes(process_data, set(allowed)) != value.get('process_rows'):
        fail('preflight process evaluation mismatch')


def paths_intersect(a, b):
    for path in (a, b):
        if not isinstance(path, str) or not path.startswith('/') or '\x00' in path:
            fail('Docker mount path malformed')
    a, b = os.path.normpath(a), os.path.normpath(b)
    return os.path.commonpath((a, b)) in (a, b)


def evaluate_docker(inspected):
    if type(inspected) is not list:
        fail('Docker inspect is not a list')
    for container in inspected:
        if type(container) is not dict or type(container.get('Mounts')) is not list:
            fail('Docker inspect mount data missing')
        for mount in container['Mounts']:
            if type(mount) is not dict:
                fail('Docker mount malformed')
            for key in ('Source', 'Destination'):
                path = mount.get(key)
                if any(paths_intersect(path, str(target)) for target in (C, B, QC, QB)):
                    fail('Docker mount intersects protected path: ' + key)
    return dict(containers=len(inspected), protected_intersections=[])


def capture_docker():
    ids = capture_command(['/usr/bin/docker', 'ps', '--all', '--quiet', '--no-trunc'], 'docker-ps').decode().splitlines()
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[0-9a-f]{64}', item) for item in ids):
        fail('Docker container IDs malformed')
    inspected = []
    if ids:
        inspected = exact_json_bytes(capture_command(['/usr/bin/docker', 'inspect', *ids], 'docker-inspect'))
        if {row.get('Id') for row in inspected} != set(ids) or len(inspected) != len(ids):
            fail('Docker inspection set mismatch')
    else:
        write_exclusive(EVIDENCE / 'docker-inspect.stdout', b'[]\n')
        write_exclusive(EVIDENCE / 'docker-inspect.stderr', b'')
        write_exclusive(EVIDENCE / 'docker-inspect.result.json', dict(argv=[], returncode=0, empty_ps=True))
    result = evaluate_docker(inspected)
    result.update(ps_sha256=sha(EVIDENCE / 'docker-ps.stdout'),
                  inspect_sha256=sha(EVIDENCE / 'docker-inspect.stdout'))
    write_exclusive(EVIDENCE / 'docker-evaluation.json', result)


def capture_observer(expected_members, run=subprocess.run):
    outfd = exclusive_fd(OBSERVER_OUT)
    errfd = None
    try:
        errfd = exclusive_fd(OBSERVER_ERR)
        try:
            result = run(['/usr/bin/python3', '-B', str(OBSERVER), '--target', str(QC), '--target', str(QB)],
                         stdin=subprocess.DEVNULL, stdout=outfd, stderr=errfd, check=False, timeout=180)
        finally:
            os.fsync(outfd)
            os.fsync(errfd)
    finally:
        os.close(outfd)
        if errfd is not None:
            os.close(errfd)
    if result.returncode != 0:
        fail('observer failed; captures retained')
    value = exact_json_bytes(read_regular(OBSERVER_OUT))
    validate_observer_result(value, expected_members)
    return dict(stdout_sha256=sha(OBSERVER_OUT), stderr_sha256=sha(OBSERVER_ERR),
                observer_sha256=OBSERVER_SHA, rounds=len(value['rounds']))


def execute_released_recovery(basis):
    if os.geteuid() != 0:
        fail('released recovery requires root')
    validate_released_basis(basis)
    head = validate_source(basis)
    execution_sha = validate_execution_release(basis, head)
    validate_historical_records(exact_json_bytes(read_regular(ORIGINAL_RECORD)),
                                exact_json_bytes(read_regular(RECOVERY1_RECORD)))
    validate_historical_archives()
    validate_observer_source_record()
    validate_current_state()
    manifest = validate_inventory_input()
    if digest_bytes(read_regular(RELEASE)) != RELEASE_SHA:
        fail('retained basis copy mismatch')
    validate_preflight(exact_json_bytes(read_regular(PREFLIGHT)), basis, head, execution_sha,
                       read_regular(EVIDENCE / 'process-preflight.stdout'))
    # Root observations happen inside this sole released privileged invocation.
    capture_docker()
    data = capture_command(['/usr/bin/ps', '-eo', 'pid=,ppid=,comm=,args='], 'process-root')
    evaluate_processes(data, ancestors())
    def action(journal):
        expected = reconstruct_inventory(manifest, ROOTS)
        journal.write('inventory-reconstructed', dict(entries=len(expected), traversal_fds_closed=True))
        observed = capture_observer(inventory_member_sets(expected))
        journal.write('observer-pass', observed)
        # The operational exclusion of privileged mutation/references spans this entire interval.
        for _original, quarantine, device, inode in ROOTS:
            parentfd = os.open(quarantine.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                rootfd = open_checked(parentfd, quarantine.name, root_wanted(device, inode))
                try:
                    delete_verified(rootfd, {key[1]: row for key, row in expected.items()
                                             if key[0] == str(quarantine)}, '', device, journal,
                                    str(quarantine), root_wanted(device, inode))
                finally:
                    os.close(rootfd)
            finally:
                os.close(parentfd)
            rmdir_root_verified(quarantine, device, inode, journal)
        remove_old_lease_after_absence(journal)
        state = survivor_state()
        if any(row['present'] is not False for row in state['paths'].values()) or state['old_lease']['present'] is not False:
            fail('post-deletion absence mismatch')
        return dict(schema='mckernel.recovery3-result.v2', status='PASS', targets_absent=True,
                    old_lease_absent=True, runtime_acceptance=False, observer=observed)
    result = with_claimed_journal(action)
    print(json.dumps(result, sort_keys=True), flush=True)


def finish_packet(rc):
    write_exclusive(EVIDENCE / 'recovery.rc', (str(rc) + '\n').encode())
    for name in ('recovery.stdout', 'recovery.stderr'):
        path = EVIDENCE / name
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                fail('packet output replaced')
            os.fsync(fd)
        finally:
            os.close(fd)
    fsync_dir(EVIDENCE)
    if rc != 0:
        fail('recovery failed with rc=' + str(rc))
    result = exact_json_bytes(read_regular(EVIDENCE / 'recovery.stdout'))
    if (result.get('schema') != 'mckernel.recovery3-result.v2' or result.get('status') != 'PASS' or
            result.get('targets_absent') is not True or result.get('old_lease_absent') is not True or
            result.get('runtime_acceptance') is not False):
        fail('helper success result malformed')
    print(json.dumps(result, sort_keys=True))


def run_packet_command(argv):
    # This unprivileged capture process inherits only the askpass path; the
    # privileged target receives the explicit env -i environment in the packet.
    if os.geteuid() == 0 or not PREFLIGHT.is_file():
        fail('packet command requires non-root prepared invocation')
    basis = exact_json_bytes(read_regular(BASIS))
    validate_released_basis(basis)
    expected = ['/usr/bin/sudo', '-A', '/usr/bin/env', '-i', 'PATH=/usr/bin:/bin',
                'HOME=/nonexistent', '/usr/bin/setsid', '--wait', '/usr/bin/timeout',
                '--signal=TERM', '--kill-after=10s', '900s', '/usr/bin/python3', '-B', str(Path(__file__))]
    if argv != expected:
        fail('packet command differs from reviewed invocation')
    out = exclusive_fd(EVIDENCE / 'recovery.stdout')
    err = None
    try:
        err = exclusive_fd(EVIDENCE / 'recovery.stderr')
        try:
            completed = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, check=False)
        finally:
            os.fsync(out)
            os.fsync(err)
    finally:
        os.close(out)
        if err is not None:
            os.close(err)
        fsync_dir(EVIDENCE)
    return completed.returncode


def main():
    if sys.argv[1:] == ['--prepare-packet']:
        return prepare_packet()
    if len(sys.argv) == 3 and sys.argv[1] == '--finish-packet':
        return finish_packet(int(sys.argv[2]))
    if len(sys.argv) > 2 and sys.argv[1] == '--run-command':
        return run_packet_command(sys.argv[2:])
    if sys.argv[1:]:
        fail('unsupported arguments')
    basis = exact_json_bytes(read_regular(BASIS))
    if basis.get('status') == 'DRAFT_NOT_RELEASED':
        validate_draft_basis(basis)
        fail('DRAFT recovery-3 template is non-executable; independent release required')
    execute_released_recovery(basis)


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        basis = exact_json_bytes(read_regular(BASIS))
        if basis.get('status') == 'DRAFT_NOT_RELEASED':
            validate_draft_basis(basis)
        else:
            validate_released_basis(basis)
        assert paths_intersect('/dev/shm', str(QC))
        assert not paths_intersect('/dev/shm/unrelated', str(QC))
        try:
            validate_observer_result({}, [])
        except RuntimeError:
            pass
        else:
            raise AssertionError('invalid observer accepted')
        print('recovery-3 pure synthetic assertions passed')
    else:
        sys.exit(main())
