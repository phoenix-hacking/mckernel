#!/usr/bin/env python3
"""DRAFT-only continuation for the consumed 704f6654 retirement attempt.

This is deliberately not an execution release.  ``draft_guard`` is the first
operation in ``main`` and rejects every unresolved sentinel before it can open
an output, inspect a process, start Docker, or touch a protected root.  The
future reviewed release must retain the descriptor-based checks below; it may
not rename a quarantine back into an original name or remove the immutable
shared tombstone.

The root-0700 quarantine is an operational exclusion from new ordinary opens.
Privileged/adversarial mutation, reference acquisition, and reference transfer
remain independently excluded during both observation and deletion; this is
not an atomic global /proc proof.
"""
from __future__ import print_function
import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import time
from pathlib import Path

REPO = Path('/home/holden/mckernel')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
PACKET = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recover-704f6654-1.py'
BASIS = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-release-basis-704f6654-1.json'
WRAPPER = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-execution-704f6654-1.sh'
TEST = REPO / 'scripts/tests/test_native_exact_candidate_quarantine_recovery_704f6654.py'
V2_PACKET = REPO / 'docs/verification/evidence/native-exact-candidate-retirement-704f6654-2.py'
V2_RELEASE = REPO / 'docs/verification/evidence/stability-native-exact-candidate-retirement-704f6654-2.release.json'
INVENTORY = REPO / 'docs/verification/evidence/stability-native-exact-candidate-retention-704f6654-20260929-1.inventory.json'
CAPSULE = REPO / 'docs/verification/evidence/stability-native-exact-candidate-retention-704f6654-20260929-1.tar'
SUCCESS = REPO / 'docs/verification/evidence/stability-native-exact-retention-preparation-success-704f6654-20260929-1.json'
HELPER = REPO / 'scripts/native_exact_candidate_retire_704f.py'
OBSERVER = REPO / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-704f6654-2.py'
RAW = REPO / 'docs/verification/evidence/stability-native-exact-retirement-704f6654-failure-20260929-1.tar.gz'
TOMBSTONE = SCRATCH / 'native-exact-build-lease-704f6654-1.json'
EVIDENCE = Path('/dev/shm/.mckernel-retirement-evidence-704f6654-2')
ORIGINALS = (Path('/dev/shm/mckernel-exact-candidate-704f6654-1'),
             Path('/dev/shm/mckernel-exact-metadata-backup-704f6654-1'))
QUARANTINES = (Path('/dev/shm/.mckernel-retirement-candidate-704f6654-2'),
               Path('/dev/shm/.mckernel-retirement-metadata-backup-704f6654-2'))
ROOTS = ((ORIGINALS[0], QUARANTINES[0], 26, 36767),
         (ORIGINALS[1], QUARANTINES[1], 26, 47413))

V2_COMMIT = 'cd4d7e63f0c736f2135834a4372a05fa1c3b29c4'
V2_PACKET_SHA = '27753f96ddc358218cad6a8ade00680894b378190f7ddb981df5b945bfc7c582'
V2_RELEASE_SHA = '19093ec1c3db71f16d5fd93264f474a200c823161b6da522400bbd4b238cc281'
INVENTORY_SHA = '4067c653e4767e63d99f8cc396587e1121dba601ea4f51f1020168cd4c61b8e1'
CAPSULE_SHA = 'b6c85e40cbe7782fa3f1652d43d314091bb25fbf3777312c7d455390d42ecec1'
SUCCESS_SHA = 'be700dd5335fdde0d33c0096a865cf6326cb9c72a99a983ec3764f99e7eeed4d'
HELPER_SHA = '4631190894a214821f02142670a2ce6f77058dc7fae986c0f6295214c705c517'
RAW_SHA = 'ba74523dc6917e113134bb8978b64c76a1332efbf096fa85c5400ce38af78806'
OBSERVER_SHA_REQUIRED = 'OBSERVER_SHA_REQUIRED'
RELEASE_SHA_REQUIRED = 'RELEASE_SHA_REQUIRED'
PACKET_SHA_REQUIRED = 'PACKET_SHA_REQUIRED'
TEST_SHA_REQUIRED = 'TEST_SHA_REQUIRED'
H64 = re.compile(r'^[0-9a-f]{64}$')
FS_IOC_GETFLAGS = 0x80086601
FS_IMMUTABLE_FL = 0x00000010
FLOORS = {'MemAvailable': 4 << 30, 'host_free': 16 << 30, 'scratch_free': 12 << 30, 'tmpfs_free': 4 << 30}
CLAIM = SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.claim.json'
JOURNAL = SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.journal.jsonl'
OUTPUT = SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.evidence'
THREAT = ('Root-owned 0700 quarantines and explicit privileged/adversarial mutation, reference acquisition, '
          'and reference-transfer exclusion are operational controls during observation AND deletion, not an '
          'atomic global proof.')


class Error(RuntimeError):
    pass


def fail(message):
    raise Error(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(rows):
    value = {}
    for key, item in rows:
        if key in value:
            fail('duplicate JSON key: ' + key)
        value[key] = item
    return value


def exact_json(data):
    try:
        return json.loads(data.decode('utf-8') if isinstance(data, bytes) else data, object_pairs_hook=pairs)
    except (TypeError, UnicodeError, ValueError) as exc:
        fail('invalid JSON: ' + str(exc))


def read_regular(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink < 1:
            fail('not regular: ' + str(path))
        data = b''.join(iter(lambda: os.read(fd, 1 << 20), b''))
        after = os.fstat(fd)
        named = os.stat(str(path), follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mode) != (after.st_dev, after.st_ino, after.st_size, after.st_mode) or (after.st_dev, after.st_ino, after.st_size, after.st_mode) != (named.st_dev, named.st_ino, named.st_size, named.st_mode):
            fail('changed while read: ' + str(path))
        return data
    finally:
        os.close(fd)


def checked(path, wanted):
    value = read_regular(path)
    if digest(value) != wanted:
        fail('hash mismatch: ' + str(path))
    return value


def git_bytes(*args):
    return subprocess.check_output(['/usr/bin/git', '--git-dir=' + str(REPO / '.git'), '--work-tree=' + str(REPO), *args], timeout=30)


def draft_guard(basis=None):
    # This intentionally includes the observer pin: no source draft can reach
    # a side effect while the independent observer is still unbound.
    required = (OBSERVER_SHA_REQUIRED, RELEASE_SHA_REQUIRED, PACKET_SHA_REQUIRED, TEST_SHA_REQUIRED)
    if any(value.endswith('_REQUIRED') for value in required):
        fail('DRAFT_NOT_RELEASED')
    if basis is not None and basis.get('status') != 'PASS_ONE_SHOT_QUARANTINE_CONTINUATION':
        fail('basis is not final')


def validate_draft_basis(value):
    if not isinstance(value, dict) or value.get('status') != 'DRAFT_NOT_RELEASED' or value.get('execution_authorized') is not False:
        fail('draft basis semantics')
    if value.get('observer_sha256') != OBSERVER_SHA_REQUIRED or value.get('release_sha256') != RELEASE_SHA_REQUIRED:
        fail('draft basis sentinel')
    if value.get('operational_threat_assumption') != THREAT:
        fail('threat assumption altered')


def validate_final_basis(value):
    """Mechanical source-finalization shape; execution release remains separate."""
    if not isinstance(value, dict) or value.get('status') != 'PASS_ONE_SHOT_QUARANTINE_CONTINUATION' or value.get('execution_authorized') is not False:
        fail('final basis semantics')
    for key in ('observer_sha256', 'release_sha256', 'packet_sha256', 'test_sha256'):
        if H64.fullmatch(value.get(key, '')) is None:
            fail('final basis pin: ' + key)
    if value.get('one_shot') is not True or value.get('retry') is not False or value.get('rollback') is not False:
        fail('final basis one-shot')
    if value.get('operational_threat_assumption') != THREAT:
        fail('final basis threat')


def validate_authorities():
    """Bind the consumed attempt to fetched bytes, never to current identities."""
    for path, wanted in ((V2_PACKET, V2_PACKET_SHA), (V2_RELEASE, V2_RELEASE_SHA),
                         (INVENTORY, INVENTORY_SHA), (CAPSULE, CAPSULE_SHA),
                         (SUCCESS, SUCCESS_SHA), (HELPER, HELPER_SHA)):
        checked(path, wanted)
    packet = git_bytes('show', V2_COMMIT + ':' + str(V2_PACKET.relative_to(REPO)))
    release = git_bytes('show', V2_COMMIT + ':' + str(V2_RELEASE.relative_to(REPO)))
    if digest(packet) != V2_PACKET_SHA or digest(release) != V2_RELEASE_SHA:
        fail('fetched v2 authority mismatch')
    current = exact_json(read_regular(V2_RELEASE))
    if current.get('status') != 'PASS_ONE_SHOT_RETIRE' or current.get('template', {}).get('commit') != 'ef7b8ef8afa4ac458368f2d4ba26817846fbf8ee':
        fail('v2 release semantics')
    return current


def archive_members(archive):
    with tarfile.open(str(archive), 'r:gz') as stream:
        result = {}
        for member in stream.getmembers():
            if member.name in result:
                fail('duplicate archive member')
            result[member.name] = member
        return result


def archive_bytes(archive, name):
    with tarfile.open(str(archive), 'r:gz') as stream:
        member = next((item for item in stream.getmembers() if item.name == name and item.isfile()), None)
        if member is None:
            fail('archive member absent: ' + name)
        return stream.extractfile(member).read()


def validate_raw_history(archive=RAW, evidence=EVIDENCE, tombstone=TOMBSTONE):
    if digest(read_regular(archive)) != RAW_SHA:
        fail('raw archive hash')
    members = archive_members(archive)
    prefix = '.mckernel-retirement-evidence-704f6654-2/'
    expected = {prefix, 'native-exact-build-lease-704f6654-1.json'}
    expected.update(prefix + name for name in ('archive.sealed.py', 'claim-704f6654-2.json', 'helper.sealed.py', 'journal-704f6654-2.jsonl', 'observer.sealed.py', 'observer.status', 'observer.stderr', 'observer.stdout', 'packet.failure'))
    if set(members) != expected or not members[prefix].isdir():
        fail('raw archive membership')
    live = os.lstat(str(evidence))
    if not stat.S_ISDIR(live.st_mode) or (live.st_uid, live.st_gid, stat.S_IMODE(live.st_mode)) != (0, 0, 0o700):
        fail('historical evidence identity')
    names = set(os.listdir(str(evidence)))
    archived_names = {name[len(prefix):] for name in expected if name.startswith(prefix) and name != prefix}
    if names != archived_names:
        fail('historical evidence membership')
    for name in sorted(archived_names):
        got = read_regular(evidence / name)
        wanted = archive_bytes(archive, prefix + name)
        if got != wanted:
            fail('historical evidence changed: ' + name)
    if read_regular(tombstone) != archive_bytes(archive, 'native-exact-build-lease-704f6654-1.json'):
        fail('tombstone bytes differ from raw archive')


def tombstone_fd(path=TOMBSTONE):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode), info.st_nlink) != (0, 0, 0o600, 1):
        os.close(fd); fail('tombstone identity')
    try:
        flags = fcntl.ioctl(fd, FS_IOC_GETFLAGS, b'\0\0\0\0')
        flags = int.from_bytes(flags[:4], byteorder=sys.byteorder)
    except OSError as exc:
        os.close(fd); fail('tombstone immutable flag unavailable: ' + str(exc))
    if not flags & FS_IMMUTABLE_FL:
        os.close(fd); fail('tombstone not immutable')
    return fd, (info.st_dev, info.st_ino, info.st_size, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode), info.st_nlink, digest(b''.join(iter(lambda: os.read(fd, 1 << 20), b''))))


def revalidate_tombstone(fd, wanted):
    now = os.fstat(fd)
    if (now.st_dev, now.st_ino, now.st_size, now.st_uid, now.st_gid, stat.S_IMODE(now.st_mode), now.st_nlink) != wanted[:7]:
        fail('tombstone descriptor changed')
    named = os.stat(str(TOMBSTONE), follow_symlinks=False)
    if (named.st_dev, named.st_ino, named.st_size, named.st_uid, named.st_gid, stat.S_IMODE(named.st_mode), named.st_nlink) != wanted[:7]:
        fail('tombstone name changed')
    flags = int.from_bytes(fcntl.ioctl(fd, FS_IOC_GETFLAGS, b'\0\0\0\0')[:4], byteorder=sys.byteorder)
    if not flags & FS_IMMUTABLE_FL:
        fail('tombstone immutable flag cleared')
    os.lseek(fd, 0, os.SEEK_SET)
    if digest(b''.join(iter(lambda: os.read(fd, 1 << 20), b''))) != wanted[7]:
        fail('tombstone bytes changed')


def reopen_tombstone(wanted):
    """The retained descriptor is checked again through a fresh nofollow open."""
    fd, got = tombstone_fd()
    try:
        if got != wanted:
            fail('tombstone reopened identity/hash changed')
        revalidate_tombstone(fd, wanted)
    finally:
        os.close(fd)


def member_identity(info):
    kind = 'directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode) else 'unsupported'
    return {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'kind': kind, 'size': info.st_size}


def validate_quarantines(release):
    if any(os.path.lexists(str(path)) for path in ORIGINALS):
        fail('original path unexpectedly present')
    rows = release.get('roots')
    if not isinstance(rows, list) or len(rows) != 2:
        fail('released root map')
    result = []
    for (original, quarantine, device, inode), row in zip(ROOTS, rows):
        if row.get('path') != str(original) or row.get('quarantine_name') != quarantine.name:
            fail('released quarantine name')
        info = os.lstat(str(quarantine))
        actual = member_identity(info)
        if actual != {'device': device, 'inode': inode, 'uid': 0, 'gid': 0, 'mode': 0o700, 'kind': 'directory', 'size': info.st_size}:
            fail('quarantine root identity')
        expected = {entry['path']: entry for entry in row.get('members', []) if isinstance(entry, dict)}
        if len(expected) != len(row.get('members', [])):
            fail('released member duplicate')
        found = {}
        for base, dirs, files in os.walk(str(quarantine), topdown=True, followlinks=False):
            names = dirs + files
            for name in names:
                path = Path(base) / name
                rel = str(path.relative_to(quarantine))
                item = os.lstat(str(path)); got = member_identity(item)
                wanted = expected.get(rel)
                if wanted is None or any(got[key] != wanted.get(key) for key in got):
                    fail('released member identity: ' + rel)
                if got['device'] != device:
                    fail('cross-device member: ' + rel)
                if got['kind'] == 'file' and digest(read_regular(path)) != wanted.get('sha256'):
                    fail('released file hash: ' + rel)
                if got['kind'] == 'symlink' and (os.readlink(str(path)) != wanted.get('target') or digest(os.fsencode(os.readlink(str(path)))) != wanted.get('sha256')):
                    fail('released symlink: ' + rel)
                found[rel] = dict(wanted, **got)
        if set(found) != set(expected):
            fail('released member map incomplete')
        # Device/inode multiplicity is the released hardlink map.  A copied
        # file with matching bytes but a different inode cannot be adopted.
        released_links, actual_links = {}, {}
        for item in expected.values():
            released_links[(item['device'], item['inode'])] = released_links.get((item['device'], item['inode']), 0) + 1
        for item in found.values():
            actual_links[(item['device'], item['inode'])] = actual_links.get((item['device'], item['inode']), 0) + 1
        if actual_links != released_links:
            fail('released hardlink map')
        result.append(expected)
    return result


def validate_observer(value, expected):
    if value.get('schema') != 'mckernel.read-only-live-reference-snapshot.v7' or value.get('status') != 'PASS' or value.get('observer_sha256') != OBSERVER_SHA_REQUIRED:
        fail('observer v7')
    if value.get('complete_mount_proofs') is not True:
        fail('observer mount proof')
    roots = value.get('roots')
    if not isinstance(roots, list) or len(roots) != 2:
        fail('observer roots')
    for root, (_original, quarantine, device, inode), members in zip(roots, ROOTS, expected):
        identities = sorted([[item['device'], item['inode']] for item in members.values()] + [[device, inode]])
        if (root.get('path'), root.get('device_number'), root.get('inode'), root.get('mode'), root.get('tree_member_identities')) != (str(quarantine), device, inode, '0700', identities):
            fail('observer exact member identities')
    rounds = value.get('rounds')
    if not isinstance(rounds, list) or len(rounds) < 2:
        fail('observer rounds')
    sticky = ('target_references', 'permission_denials', 'tree_revalidation_failures', 'persistent_tree_revalidation_failures', 'unscanned_final_identities')
    if any(value.get(key, []) != [] for key in sticky):
        fail('observer sticky finding')
    for row in rounds:
        if any(row.get(key, []) != [] for key in ('target_references', 'permission_denials', 'tree_revalidation_failures')) or row.get('complete_mount_proofs') is not True:
            fail('observer round finding')
    for row in rounds[-2:]:
        if row.get('clean') is not True or row.get('unresolved_churn') != [] or row.get('closure_nonconvergent') is not False or row.get('unscanned_final_identities') != []:
            fail('observer final clean rounds')


def validate_docker(records, release):
    want = release.get('docker', {}).get('terminal_containers')
    if not isinstance(want, dict) or set(want) != {row.get('Id') for row in records if isinstance(row, dict)} or len(records) != 4:
        fail('Docker terminal census')
    protected = [str(path) for path in ORIGINALS + QUARANTINES]
    for row in records:
        if row != want.get(row.get('Id')):
            fail('Docker terminal record')
        for mount in row.get('Mounts', []):
            source = mount.get('Source', '')
            if any(os.path.commonpath((os.path.normpath(source), path)) in (os.path.normpath(source), path) for path in protected):
                fail('unknown protected Docker mount')


def docker_census():
    """A full ``ps --all``/inspect snapshot; unknown IDs fail closed."""
    ids = subprocess.check_output(['/usr/bin/docker', 'ps', '--all', '--quiet', '--no-trunc'], timeout=60).decode('ascii', 'strict').splitlines()
    if len(ids) != 4 or len(ids) != len(set(ids)) or any(H64.fullmatch(item) is None for item in ids):
        fail('Docker census identifiers')
    data = subprocess.check_output(['/usr/bin/docker', 'inspect', *ids], timeout=60)
    rows = exact_json(data)
    if not isinstance(rows, list) or {row.get('Id') for row in rows if isinstance(row, dict)} != set(ids):
        fail('Docker census inspect omission')
    after = subprocess.check_output(['/usr/bin/docker', 'ps', '--all', '--quiet', '--no-trunc'], timeout=60).decode('ascii', 'strict').splitlines()
    if after != ids:
        fail('Docker census churn')
    return rows


def seal_and_run_observer(expected):
    """Finalized-only descriptor seal; observer is never reopened by pathname."""
    source = checked(OBSERVER, OBSERVER_SHA_REQUIRED)
    os.mkdir(str(OUTPUT), 0o700)
    sealed = OUTPUT / 'observer.sealed.py'
    fd = os.open(str(sealed), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, source); os.fsync(fd)
    finally:
        os.close(fd)
    read_fd = os.open(str(sealed), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(read_fd)
        if not stat.S_ISREG(before.st_mode) or digest(b''.join(iter(lambda: os.read(read_fd, 1 << 20), b''))) != OBSERVER_SHA_REQUIRED:
            fail('sealed observer changed')
        result = subprocess.check_output(['/usr/bin/python3', '-B', '/proc/self/fd/' + str(read_fd), '--target', str(QUARANTINES[0]), '--target', str(QUARANTINES[1])], timeout=180)
        if os.fstat(read_fd).st_ino != before.st_ino:
            fail('sealed observer descriptor changed')
    finally:
        os.close(read_fd)
    value = exact_json(result); validate_observer(value, expected)
    return value


def validate_capacity(statvfs=os.statvfs, meminfo='/proc/meminfo'):
    text = Path(meminfo).read_text()
    match = re.search(r'^MemAvailable:\s+(\d+)\s+kB$', text, re.M)
    if match is None or int(match.group(1)) * 1024 < FLOORS['MemAvailable']:
        fail('MemAvailable floor')
    for path, key in ((REPO, 'host_free'), (SCRATCH, 'scratch_free'), (Path('/dev/shm'), 'tmpfs_free')):
        row = statvfs(str(path))
        if row.f_bavail * row.f_frsize < FLOORS[key]:
            fail('capacity floor: ' + key)


def validate_conflicts(proc=Path('/proc')):
    forbidden = {'qemu-system-x86_64', 'qemu-kvm', 'native_rust_exact_build_container_owner.py', 'native_exact_candidate_retire.py'}
    for row in proc.iterdir():
        if not row.name.isdigit() or int(row.name) == os.getpid():
            continue
        try:
            values = (row / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, PermissionError):
            continue
        names = {os.path.basename(value.decode('utf-8', 'surrogateescape')) for value in values if value}
        if forbidden.intersection(names):
            fail('conflicting process or guest')


def exclusive_json(path, value):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        data = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
        os.write(fd, data); os.fsync(fd)
    finally:
        os.close(fd)


def append_journal(fd, phase, **fields):
    data = (json.dumps(dict(phase=phase, **fields), sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    os.write(fd, data); os.fsync(fd)


def close_descriptors(descriptors):
    """Bounded explicit cleanup used after observer/journal failures."""
    failure = None
    for fd in descriptors:
        if fd is None:
            continue
        try:
            os.close(fd)
        except OSError as exc:
            failure = failure or exc
    if failure is not None:
        fail('descriptor cleanup: ' + str(failure))


def delete_dirfd(fd, expected, journal, root_name):
    names = set(os.listdir(fd))
    if names != {key.split('/', 1)[0] for key in expected}:
        fail('delete-before-proof membership')
    for name in sorted(names):
        subset = {key[len(name) + 1:]: value for key, value in expected.items() if key == name or key.startswith(name + '/')}
        wanted = expected[name]; info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if member_identity(info) != {key: wanted[key] for key in ('device', 'inode', 'uid', 'gid', 'mode', 'kind', 'size')}:
            fail('delete identity changed')
        journal('before-entry', root=root_name, path=name)
        if wanted['kind'] == 'directory':
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                nested = {key[len(name) + 1:]: value for key, value in expected.items()
                          if key.startswith(name + '/')}
                delete_dirfd(child, nested, journal, root_name + '/' + name)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=fd)
        else:
            os.unlink(name, dir_fd=fd)
        journal('after-entry', root=root_name, path=name)


def execute_final(observer_value=None, docker_before=None, docker_after=None):
    """Finalized-only one-shot order, retained here for independent review.

    The future release calls this only after all four sentinels are replaced
    and its separate execution-release verifier succeeds.  A claim is created
    first and never removed on failure, so a failed continuation is consumed.
    """
    basis = exact_json(read_regular(BASIS))
    draft_guard(basis)
    release = validate_authorities()
    validate_raw_history()
    tomb_fd, tomb = tombstone_fd()
    journal_fd = None
    try:
        exclusive_json(CLAIM, {'schema': 'mckernel.quarantine-continuation-claim.v1',
                               'one_shot': True, 'retry': False, 'rollback': False,
                               'release_sha256': RELEASE_SHA_REQUIRED, 'tombstone': str(TOMBSTONE)})
        journal_fd = os.open(str(JOURNAL), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        append_journal(journal_fd, 'claim-created')
        validate_capacity(); validate_conflicts(); revalidate_tombstone(tomb_fd, tomb)
        expected = validate_quarantines(release)
        if docker_before is None:
            docker_before = docker_census()
        if observer_value is None:
            observer_value = seal_and_run_observer(expected)
        if docker_after is None:
            docker_after = docker_census()
        validate_docker(docker_before, release)
        validate_observer(observer_value, expected)
        # Reference exclusion and Docker census are repeated after observer,
        # and again immediately before the first unlink/rmdir boundary.
        validate_conflicts(); validate_docker(docker_after, release)
        revalidate_tombstone(tomb_fd, tomb); append_journal(journal_fd, 'proofs-complete')
        for (_original, quarantine, device, inode), members in zip(ROOTS, expected):
            parent_fd = os.open(str(quarantine.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                root_fd = os.open(quarantine.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                try:
                    info = os.fstat(root_fd)
                    if (info.st_dev, info.st_ino, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (device, inode, 0, 0, 0o700):
                        fail('root changed before deletion')
                    delete_dirfd(root_fd, members, lambda phase, **row: append_journal(journal_fd, phase, **row), quarantine.name)
                finally:
                    os.close(root_fd)
                append_journal(journal_fd, 'before-root', root=str(quarantine)); os.rmdir(quarantine.name, dir_fd=parent_fd)
                append_journal(journal_fd, 'after-root', root=str(quarantine))
            finally:
                os.close(parent_fd)
        if any(os.path.lexists(str(path)) for path in ORIGINALS + QUARANTINES):
            fail('terminal root absence')
        validate_raw_history(); revalidate_tombstone(tomb_fd, tomb); reopen_tombstone(tomb)
        append_journal(journal_fd, 'terminal-success')
    finally:
        if journal_fd is not None:
            os.close(journal_fd)
        os.close(tomb_fd)


def run_released():
    """Future-only execution skeleton; draft_guard is intentionally first."""
    draft_guard(exact_json(read_regular(BASIS)))
    fail('independent execution release required')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    draft_guard(exact_json(read_regular(BASIS)))
    if args.execute:
        run_released()
    fail('DRAFT_NOT_RELEASED')


if __name__ == '__main__':
    main()
