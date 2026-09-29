#!/usr/bin/env python3
"""One-shot, root-only and fail-closed removal of two exact tmpfs directories.

This is intentionally not a general cleanup utility.  The execution packet must
pin the still-unset observer and complete-worktree-manifest hashes before this
program is eligible to mutate anything.
"""
import ctypes
import hashlib
import json
import os
import stat
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

C = Path('/dev/shm/mckernel-exact-candidate-68cf089a-1')
B = Path('/dev/shm/mckernel-exact-metadata-backup-68cf089a-1')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
SNAP = SCRATCH / 'native-exact-live-reference-snapshot-68cf089a-1.json'
POST_SEAL_SNAP = SCRATCH / 'native-exact-live-reference-post-seal-68cf089a-1.json'
PREFLIGHT = SCRATCH / 'native-exact-candidate-delete-preflight-68cf089a-1.json'
LEASE = SCRATCH / 'native-exact-build-lease-68cf089a-1.json'
JOURNAL = SCRATCH / 'native-exact-candidate-delete-68cf089a-1.journal.jsonl'
OBSERVER = Path('/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py')
RET = Path('/home/holden/mckernel/docs/verification/evidence/stability-native-exact-prepared-candidate-retention-68cf089a-20260929-1.tar.gz')
PREP = Path('/home/holden/mckernel/docs/verification/evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz')
PREP_RECORD = Path('/home/holden/mckernel/docs/verification/stability-native-exact-candidate-preparation-checkpoint-20260929-1.json')
RET_RECORD = Path('/home/holden/mckernel/docs/verification/stability-native-exact-prepared-candidate-retention-20260929-1.json')
INPUTS = SCRATCH / 'native-exact-inputs-68cf089a-1.json'
COMPLETE_INVENTORY = SCRATCH / 'native-exact-complete-worktree-inventory-68cf089a-1.json'
REQUEST = SCRATCH / 'native-exact-build-request-68cf089a-1.json'
RET_SHA = 'eed1879bd35c62d7aa629189dfc0c46254680209ab02f933278c70c8cf9880c6'
PREP_SHA = '78e2b5c44e9ae00f2f463ac8b93723e26d00877fbbe7ecfb285d1d89d6404264'
INPUTS_SHA = 'ae0c5f74e3e3f06176c46f2f174b1109c11a4e88f23ee71fd7432e6325262abd'
REQUEST_SHA = '25f820e2994d41427ed16cf5f062d647125ccb7144f63afe618e88ccce7f576c'
PREP_RECORD_SHA = 'bc8b3a6d819208b7266e39bb91862ddbacba5ec700dcf14b960fe7857aa2be99'
RET_RECORD_SHA = '129d25f80a29fc321cae94c3e1f4db4279e42c1b100ea41c6406a3a3e133f7b6'
# The observer source is pinned after its focused syntax/pure-function review.
# The inventory value deliberately BLOCKS execution until a reviewed packet
# supplies a manifest that inventories all live names.
OBSERVER_SHA = 'a1ce4fc683548d8e43053cf5b4e80dfaa55069c6de6579bd390749023d2a615e'
WORKTREE_INVENTORY_SHA = 'UNSET-REQUIRES-COMPLETE-INVENTORY-SHA256'
ROOTS = ((C, 26, 14117, '0755', 10462), (B, 26, 24701, '0755', 87))
FRESHNESS_SECONDS = 300
RENAME_EXCHANGE = 0x2
LIBC = ctypes.CDLL(None, use_errno=True)


def fail(message):
    raise RuntimeError(message)


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def exact_json(path):
    if path.is_symlink() or not path.is_file():
        fail('missing required regular file: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def free_map():
    def available(path):
        value = os.statvfs(path)
        return value.f_bavail * value.f_frsize
    return {'host': available('/'), 'scratch': available(SCRATCH), 'tmpfs': available('/dev/shm')}


class Journal:
    def __init__(self):
        self.fd = os.open(JOURNAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self.write('started', {})

    def write(self, phase, details):
        os.write(self.fd, (json.dumps({'utc': utcnow(), 'phase': phase, **details}, sort_keys=True,
                                       separators=(',', ':')) + '\n').encode())
        os.fsync(self.fd)

    def close(self):
        os.close(self.fd)


def git(path, *arguments):
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C', 'LC_ALL': 'C',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                   'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0',
                   'GIT_ALLOW_PROTOCOL': 'file'}
    return subprocess.check_output(['/usr/bin/git', '-C', str(path), *arguments], env=environment,
                                   text=True, stderr=subprocess.STDOUT).strip()


def stat_starttime(pid):
    text = Path('/proc/%d/stat' % pid).read_text(encoding='ascii')
    tail = text[text.rfind(')') + 2:].split()
    if len(tail) < 20:
        fail('malformed live proc stat')
    return tail[19]


def parse_utc(value):
    if type(value) is not str or not value.endswith('Z'):
        fail('bad snapshot UTC value')
    return datetime.fromisoformat(value[:-1] + '+00:00').timestamp()


def validate_snapshot(snapshot, expected_modes, observer_hash):
    required = {'schema': str, 'observer_sha256': str, 'boot_id': str, 'observer_pid': int,
                'observer_starttime': str, 'started_at_utc': str, 'ended_at_utc': str,
                'rounds': list, 'scan_complete': bool, 'roots': list, 'tasks_scanned': int,
                'field_counts': dict, 'permission_denials': list, 'target_references': list,
                'unresolved_churn': list, 'mount_namespace_task_proofs': list,
                'canonical_dev_shm': dict}
    for key, kind in required.items():
        if key not in snapshot or type(snapshot[key]) is not kind:
            fail('snapshot missing or wrong type: ' + key)
    if snapshot['schema'] != 'mckernel.read-only-live-reference-snapshot.v4' or snapshot['observer_sha256'] != observer_hash:
        fail('snapshot schema/observer pin mismatch')
    if snapshot['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        fail('snapshot boot id mismatch')
    end = parse_utc(snapshot['ended_at_utc'])
    if end > time.time() + 5 or time.time() - end > FRESHNESS_SECONDS:
        fail('snapshot freshness violation')
    if not snapshot['scan_complete'] or not snapshot['rounds'] or not snapshot['field_counts']:
        fail('snapshot has incomplete coverage')
    if snapshot['permission_denials'] != [] or snapshot['target_references'] != [] or snapshot['unresolved_churn'] != []:
        fail('snapshot is not empty of denials/references/churn')
    pid = snapshot['observer_pid']
    try:
        if stat_starttime(pid) != snapshot['observer_starttime']:
            fail('observer PID has been reused')
    except FileNotFoundError:
        pass  # Terminal observer absence is allowed.
    roots = {item.get('path'): item for item in snapshot['roots'] if type(item) is dict}
    if len(roots) != len(ROOTS):
        fail('snapshot roots malformed')
    for (path, dev, inode, _mode, count), expected_mode in zip(ROOTS, expected_modes):
        item = roots.get(str(path))
        if not item or any(key not in item for key in ('device_number', 'inode', 'mode', 'tree_inode_count',
                                                        'device', 'filesystem_root', 'observer_mount')):
            fail('snapshot root fields missing')
        if (item['device_number'], item['inode'], item['mode'], item['tree_inode_count']) != (dev, inode, expected_mode, count):
            fail('snapshot exact root mismatch')


def entry_from_live(path):
    info = path.lstat()
    if stat.S_ISDIR(info.st_mode):
        kind, digest = 'directory', None
    elif stat.S_ISREG(info.st_mode):
        kind, digest = 'file', sha(path)
    elif stat.S_ISLNK(info.st_mode):
        kind, digest = 'symlink', hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    else:
        fail('unsupported live inode: ' + str(path))
    return {'type': kind, 'mode': format(stat.S_IMODE(info.st_mode), '04o'), 'sha256': digest}


def checked_inventory():
    """Return exact allowed names and metadata for both complete live roots."""
    if sha(COMPLETE_INVENTORY) != WORKTREE_INVENTORY_SHA:
        fail('complete worktree inventory manifest hash is not pinned')
    manifest = exact_json(COMPLETE_INVENTORY)
    rows = manifest.get('worktree_inventory')
    if type(rows) is not list or not rows:
        fail('manifest lacks complete worktree_inventory')
    expected = {}
    for row in rows:
        if type(row) is not dict or set(row) != {'path', 'type', 'mode', 'sha256'}:
            fail('invalid worktree inventory row')
        if row['type'] not in ('directory', 'file', 'symlink') or type(row['path']) is not str or type(row['mode']) is not str:
            fail('invalid worktree inventory metadata')
        if ((row['type'] == 'directory' and row['sha256'] is not None) or
                (row['type'] != 'directory' and (type(row['sha256']) is not str or len(row['sha256']) != 64))):
            fail('invalid worktree inventory digest')
        name = row['path'].rstrip('/')
        parsed = PurePosixPath(name)
        if parsed.is_absolute() or '..' in parsed.parts or name in expected:
            fail('unsafe/duplicate inventory name')
        expected[name] = {'type': row['type'], 'mode': row['mode'], 'sha256': row['sha256']}
    # The manifest is the preservation authority for *all* main and IHK
    # tracked entries, not merely paths that happened to be archived.
    for name, metadata in expected.items():
        live = Path('/') / name
        if not live.exists() and not live.is_symlink():
            fail('manifest entry absent live: ' + name)
        if entry_from_live(live) != metadata:
            fail('manifest entry metadata/bytes mismatch: ' + name)
    with tarfile.open(RET, 'r:gz') as archive:
        members = archive.getmembers()
        if len(members) != 920 or len({member.name for member in members}) != 920:
            fail('retention capsule count/uniqueness mismatch')
        for member in members:
            if not (member.isdir() or member.isfile() or member.issym()):
                fail('unsupported capsule entry: ' + member.name)
            live = Path('/') / member.name
            actual = entry_from_live(live)
            kind = 'directory' if member.isdir() else 'file' if member.isfile() else 'symlink'
            member_hash = None if kind == 'directory' else (hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                         if kind == 'file' else hashlib.sha256(os.fsencode(member.linkname)).hexdigest())
            if actual != {'type': kind, 'mode': format(member.mode, '04o'), 'sha256': member_hash}:
                fail('capsule metadata/bytes mismatch: ' + member.name)
            name = member.name.rstrip('/')
            if name.startswith(str(C.relative_to('/')) + '/') or name.startswith(str(B.relative_to('/')) + '/') or name in (str(C.relative_to('/')), str(B.relative_to('/'))):
                prior = expected.get(name)
                capsule = {'type': kind, 'mode': format(member.mode, '04o'), 'sha256': member_hash}
                if prior is not None and prior != capsule:
                    fail('manifest/capsule mismatch: ' + name)
                expected[name] = capsule
    allowed = set(expected)
    for name in list(allowed):
        parts = PurePosixPath(name).parts
        allowed.update(str(PurePosixPath(*parts[:index])) for index in range(1, len(parts)))
    for root, _dev, _inode, _mode, _count in ROOTS:
        root_name = str(root.relative_to('/'))
        actual_names, stack = set(), [root]
        root_dev = root.lstat().st_dev
        while stack:
            item = stack.pop()
            actual_names.add(str(item.relative_to('/')))
            actual = entry_from_live(item)
            name = str(item.relative_to('/'))
            if name not in expected or actual != expected[name]:
                fail('manifest inventory differs from live entry: ' + name)
            if actual['type'] == 'directory':
                for child in os.scandir(item):
                    if Path(child.path).lstat().st_dev != root_dev:
                        fail('nested mount/cross-device live entry: ' + child.path)
                    stack.append(Path(child.path))
        scoped_allowed = {name for name in allowed if name == root_name or name.startswith(root_name + '/')}
        if actual_names != scoped_allowed:
            fail('live root has ignored/untracked/unknown names: ' + root_name)
    return expected


def fd_open_dir(parentfd, name):
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parentfd)


def fd_identity(fd, dev, inode, mode):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino, format(stat.S_IMODE(info.st_mode), '04o')) != (dev, inode, mode):
        fail('held descriptor identity mismatch')


def fd_entry(fd, name):
    return os.stat(name, dir_fd=fd, follow_symlinks=False)


def fd_file_sha(fd, name):
    childfd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    try:
        digest = hashlib.sha256()
        while True:
            block = os.read(childfd, 1 << 20)
            if not block:
                return digest.hexdigest()
            digest.update(block)
    finally:
        os.close(childfd)


def names(fd):
    with os.scandir('/proc/self/fd/%d' % fd) as entries:
        return {entry.name for entry in entries}


def unlink_validated(fd, expected, prefix, device):
    direct = {name[len(prefix):].split('/', 1)[0] for name in expected if name.startswith(prefix) and name[len(prefix):]}
    if names(fd) != direct:
        fail('descriptor tree changed after validation at ' + prefix)
    for name in sorted(direct):
        rel = prefix + name
        item = expected[rel]
        info = fd_entry(fd, name)
        if info.st_dev != device or format(stat.S_IMODE(info.st_mode), '04o') != item['mode']:
            fail('descriptor entry metadata changed: ' + rel)
        if item['type'] == 'directory':
            subfd = fd_open_dir(fd, name)
            try:
                unlink_validated(subfd, expected, rel + '/', device)
            finally:
                os.close(subfd)
            os.rmdir(name, dir_fd=fd)
        elif item['type'] == 'file':
            if fd_file_sha(fd, name) != item['sha256']:
                fail('descriptor file bytes changed: ' + rel)
            os.unlink(name, dir_fd=fd)
        elif item['type'] == 'symlink':
            if hashlib.sha256(os.fsencode(os.readlink(name, dir_fd=fd))).hexdigest() != item['sha256']:
                fail('descriptor symlink target changed: ' + rel)
            os.unlink(name, dir_fd=fd)
        else:
            fail('unsupported validated type')


def exchange(parentfd, old, new):
    result = LIBC.renameat2(parentfd, os.fsencode(old), parentfd, os.fsencode(new), RENAME_EXCHANGE)
    if result:
        error = ctypes.get_errno()
        fail('renameat2 exchange failed: ' + os.strerror(error))


def external_preflight():
    receipt = exact_json(PREFLIGHT)
    required = {'schema': 'mckernel.native-exact-candidate-delete-preflight.v1', 'lease_absent': True,
                'fresh_docker_no_bind_mounts': True, 'reviewed_execution_release': True}
    if any(receipt.get(key) != value for key, value in required.items()):
        fail('external lease/docker/release preflight is incomplete')


def main():
    if os.geteuid() != 0:
        fail('root-only: fchmod/fchown descriptor sealing is mandatory')
    journal = Journal()
    try:
        before = free_map()
        journal.write('preflight', {'free_before': before})
        if LEASE.exists() or LEASE.is_symlink():
            fail('build lease exists')
        external_preflight()
        for path, expected_hash in ((RET, RET_SHA), (PREP, PREP_SHA), (PREP_RECORD, PREP_RECORD_SHA),
                                    (RET_RECORD, RET_RECORD_SHA), (INPUTS, INPUTS_SHA), (REQUEST, REQUEST_SHA)):
            if sha(path) != expected_hash:
                fail('fixed evidence hash mismatch: ' + str(path))
        if git(C, 'rev-parse', 'HEAD') != '68cf089a22b0a0c034a7f1fcc695853fbf5c07eb' or git(C / 'ihk', 'rev-parse', 'HEAD') != '3114d9e7101ad52030eb3effa849a5c108972a1f':
            fail('candidate/IHK commit mismatch')
        expected = checked_inventory()
        validate_snapshot(exact_json(SNAP), ('0755', '0755'), OBSERVER_SHA)
        parentfd = os.open('/dev/shm', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        held, sentinels = [], []
        try:
            for path, dev, inode, mode, count in ROOTS:
                fd = fd_open_dir(parentfd, path.name)
                fd_identity(fd, dev, inode, mode)
                held.append((path, fd, dev, inode, count))
            for path, _fd, _dev, _inode, _count in held:
                sentinel = '.mckernel-delete-sentinel-' + path.name
                os.mkdir(sentinel, 0o700, dir_fd=parentfd)  # exclusive/fixed/fresh
                os.chown(sentinel, 0, 0, dir_fd=parentfd, follow_symlinks=False)
                sentinels.append(sentinel)
            journal.write('descriptors-held', {'targets': [str(path) for path, *_ in held], 'sentinels': sentinels})
            for _path, fd, _dev, _inode, _count in held:
                os.fchmod(fd, 0o700)
                os.fchown(fd, 0, 0)
            journal.write('sealed', {})
            # This post-seal record is an execution-packet input produced by the
            # complete observer; helper never invokes Docker or trusts a pre-seal scan.
            validate_snapshot(exact_json(POST_SEAL_SNAP), ('0700', '0700'), OBSERVER_SHA)
            expected = checked_inventory()
            journal.write('post-seal-observer-and-inventory-validated', {})
            for (path, fd, dev, inode, _count), sentinel in zip(held, sentinels):
                fd_identity(fd, dev, inode, '0700')
                exchange(parentfd, path.name, sentinel)
                swapped = fd_entry(parentfd, sentinel)
                if (swapped.st_dev, swapped.st_ino) != (dev, inode):
                    fail('exchange did not quarantine held inode')
                journal.write('quarantined-root', {'target': str(path), 'quarantine_name': sentinel, 'inode': inode})
                qfd = fd_open_dir(parentfd, sentinel)
                try:
                    fd_identity(qfd, dev, inode, '0700')
                    root_name = str(path.relative_to('/'))
                    scoped = {name[len(root_name) + 1:]: value for name, value in expected.items()
                              if name.startswith(root_name + '/')}
                    unlink_validated(qfd, scoped, '', dev)
                finally:
                    os.close(qfd)
                os.rmdir(sentinel, dir_fd=parentfd)
                # The old pathname now names our controlled empty sentinel only.
                os.rmdir(path.name, dir_fd=parentfd)
                journal.write('removed-root', {'target': str(path), 'inode': inode})
            if C.exists() or B.exists():
                fail('target names remain after deletion')
        finally:
            for _path, fd, _dev, _inode, _count in held:
                os.close(fd)
            os.close(parentfd)
        after = free_map()
        result = {'schema': 'mckernel.native-exact-candidate-deletion-result.v2',
                  'observer_sha256': OBSERVER_SHA, 'targets_absent': True, 'free_before': before, 'free_after': after,
                  'net_statvfs_delta_bytes': {key: after[key] - before[key] for key in before},
                  'attributable_entry_bytes': 'not derivable from statvfs; exact deleted inventory is journal-bound',
                  'retention_capsule_sha256': RET_SHA, 'preparation_archive_sha256': PREP_SHA,
                  'preparation_record_sha256': PREP_RECORD_SHA, 'retention_record_sha256': RET_RECORD_SHA}
        journal.write('terminal-success', result)
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    except BaseException as error:
        try:
            journal.write('terminal-failure', {'error': repr(error)})
        except BaseException:
            pass
        raise
    finally:
        journal.close()


if __name__ == '__main__':
    main()
