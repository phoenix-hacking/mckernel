#!/usr/bin/env python3
"""One-shot retirement of one fully reconstructible evidence subtree.

The target and all evidence identities are fixed.  This program never removes
the candidate root, metadata backup, external preparation records, build
outputs, images, or container records.  A visible READY record is not by itself
success; callers must also retain exit status zero and independently verify the
journal.
"""
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

REPO = Path('/home/holden/mckernel')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
ROOT = SCRATCH / 'mckernel-exact-candidate-c81aeaca-scratch-14'
TARGET = ROOT / 'docs/verification/evidence'
QUARANTINE = ROOT / 'docs/verification/.retired-evidence-c81aeaca-20261001-1'
INVENTORY = REPO / 'docs/verification/evidence/native-exact-candidate-retention-c81aeaca-scratch14-20261001.inventory.json'
CAPSULE = REPO / 'docs/verification/evidence/native-exact-candidate-retention-c81aeaca-scratch14-20261001.tar'
CHECKPOINT = REPO / 'docs/verification/evidence/native-exact-c81-scratch14-retention-artifacts-checkpoint-20261001.json'
TOOL = REPO / 'docs/verification/evidence/native-exact-scratch14-evidence-subtree-retire-20261001.py'
REMOTE = 'refs/remotes/origin/codex/local-native-staging-repair'
ARTIFACT_COMMIT = 'bca2aa984fb1efda83d3355aba8c9beeda3ec084'
INVENTORY_SHA = '12de35d422c6ec014e9ed893c1e1c7ffdb772969ff6f5a5978258203f5519630'
CAPSULE_SHA = '8ca6a306ade8b7eb88d62488b239e5c9a3b7c5fb4b11f9af8d313d0497c8203d'
CHECKPOINT_SHA = 'ffe49c22d1e98dd8070e4e861ea0060bb6d8b99fd37ceb80e4e01ca49af9ef38'
ROOT_ID = (1831, 1464725, 1000, 1000, 0o755)
TARGET_ID = (1831, 1465177, 1000, 1000, 0o755)
DEVICE = 1831
HOST_FLOOR = 16 << 30
SCRATCH_FLOOR = 12 << 30
LOCK = SCRATCH / 'native-exact-build-development.lock'
CLAIM = SCRATCH / 'native-exact-scratch14-evidence-retire-20261001-1.claim.json'
JOURNAL = SCRATCH / 'native-exact-scratch14-evidence-retire-20261001-1.journal.jsonl'
STATUS = SCRATCH / 'native-exact-scratch14-evidence-retire-20261001-1.status.json'
LEASES = (
    SCRATCH / 'native-exact-build-lease-c81aeaca-scratch-14.json',
    SCRATCH / 'native-exact-mckernel-image-lease-c81aeaca-exportset-25.json',
)
NOFOLLOW = getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0)


class Refusal(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise Refusal(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_path(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(argv, ok=(0,)):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=180, check=False)
    require(result.returncode in ok, 'command-failed:' + Path(argv[0]).name)
    return result


def git(*args):
    command = ['/usr/bin/sudo', '-A', '-u', '#1000', '/usr/bin/env', '-i',
               'PATH=/usr/bin:/bin', 'HOME=/nonexistent', 'LANG=C', 'LC_ALL=C',
               'TZ=UTC', 'GIT_CONFIG_NOSYSTEM=1', 'GIT_CONFIG_GLOBAL=/dev/null',
               'GIT_NO_REPLACE_OBJECTS=1', 'GIT_TERMINAL_PROMPT=0',
               'GIT_OPTIONAL_LOCKS=0', '/usr/bin/git', '-C', str(REPO), *args]
    return subprocess.check_output(command, stderr=subprocess.PIPE, timeout=60)


def exclusive_json(path, record):
    data = (json.dumps(record, sort_keys=True) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW, 0o600)
    try:
        offset = 0
        while offset < len(data):
            amount = os.write(fd, data[offset:])
            require(amount > 0, 'short-write')
            offset += amount
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


class Journal:
    def __init__(self, path):
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                          os.O_APPEND | NOFOLLOW, 0o600)
        os.fsync(self.fd)
        parent = os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)

    def append(self, record):
        data = (json.dumps(record, sort_keys=True) + '\n').encode()
        offset = 0
        while offset < len(data):
            amount = os.write(self.fd, data[offset:])
            require(amount > 0, 'journal-short-write')
            offset += amount
        os.fsync(self.fd)

    def close(self):
        if self.fd is not None:
            fd, self.fd = self.fd, None
            os.fsync(fd)
            os.close(fd)


def identity(path):
    value = os.lstat(path)
    require(stat.S_ISDIR(value.st_mode) and not stat.S_ISLNK(value.st_mode),
            'directory-identity')
    return (value.st_dev, value.st_ino, value.st_uid, value.st_gid,
            stat.S_IMODE(value.st_mode))


def open_directory(path):
    """Open every absolute ancestor without following a symlink."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
    try:
        for component in Path(path).parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def mount_paths():
    paths = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split()
        require(len(fields) >= 10 and '-' in fields, 'mountinfo-format')
        paths.append(fields[4].replace('\\040', ' ').replace('\\011', '\t')
                     .replace('\\012', '\n').replace('\\134', '\\'))
    return paths


def reject_nested_mount(path):
    prefix = str(path) + '/'
    require(all(item != str(path) and not item.startswith(prefix)
                for item in mount_paths()), 'nested-mount')


def inventory_rows():
    require(sha_path(INVENTORY) == INVENTORY_SHA and
            sha_path(CAPSULE) == CAPSULE_SHA and
            sha_path(CHECKPOINT) == CHECKPOINT_SHA, 'artifact-hash')
    inventory_rel = str(INVENTORY.relative_to(REPO))
    capsule_rel = str(CAPSULE.relative_to(REPO))
    checkpoint_rel = str(CHECKPOINT.relative_to(REPO))
    require(sha_bytes(git('show', ARTIFACT_COMMIT + ':' + inventory_rel)) == INVENTORY_SHA and
            sha_bytes(git('show', ARTIFACT_COMMIT + ':' + capsule_rel)) == CAPSULE_SHA and
            sha_bytes(git('show', ARTIFACT_COMMIT + ':' + checkpoint_rel)) == CHECKPOINT_SHA,
            'artifact-not-fetched')
    require(git('merge-base', '--is-ancestor', ARTIFACT_COMMIT, REMOTE) == b'',
            'artifact-ancestry')
    require(git('show', REMOTE + ':' + str(TOOL.relative_to(REPO))) == TOOL.read_bytes(),
            'tool-not-fetched')
    data = json.loads(INVENTORY.read_text())
    checkpoint = json.loads(CHECKPOINT.read_text())
    for record in checkpoint['external_preparation_records'].values():
        path = Path(record['path'])
        value = os.lstat(path)
        require(stat.S_ISREG(value.st_mode) and not stat.S_ISLNK(value.st_mode) and
                value.st_dev == record['device'] and value.st_ino == record['inode'] and
                value.st_size == record['bytes'] and value.st_nlink == 1 and
                sha_path(path) == record['sha256'], 'external-preparation-record')
    rows = [row for row in data['entries'] if row['root'] == 'candidate' and
            (row['path'] == 'docs/verification/evidence' or
             row['path'].startswith('docs/verification/evidence/'))]
    require(len(rows) == 2677 and all(row['classification'] == 'reconstructible'
                                     for row in rows), 'inventory-scope')
    return rows


def hash_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    for block in iter(lambda: os.read(fd, 1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def census(base, rows, root_override=None):
    prefix = 'docs/verification/evidence'
    expected = {row['path'][len(prefix):].lstrip('/'): row for row in rows}
    actual = {}
    inode_set = set()

    def visit(fd, rel):
        value = os.fstat(fd)
        row = expected.get(rel)
        wanted_uid, wanted_gid, wanted_mode = ((root_override if rel == '' and root_override
                                                else (row['uid'], row['gid'], row['mode'])))
        require(row is not None and row['type'] == 'directory' and
                value.st_dev == DEVICE and value.st_uid == wanted_uid and
                value.st_gid == wanted_gid and stat.S_IMODE(value.st_mode) == wanted_mode,
                'directory-metadata')
        pair = (value.st_dev, value.st_ino)
        require(pair not in inode_set, 'member-hardlink-or-alias')
        inode_set.add(pair)
        actual[rel] = {'dev': value.st_dev, 'ino': value.st_ino, 'type': 'directory',
                       'uid': value.st_uid, 'gid': value.st_gid,
                       'mode': stat.S_IMODE(value.st_mode)}
        for name in os.listdir(fd):
            child_rel = name if not rel else rel + '/' + name
            value = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(value.st_dev == DEVICE and not stat.S_ISLNK(value.st_mode),
                    'member-device-or-symlink')
            pair = (value.st_dev, value.st_ino)
            require(pair not in inode_set, 'member-hardlink-or-alias')
            row = expected.get(child_rel)
            require(row is not None and value.st_uid == row['uid'] and
                    value.st_gid == row['gid'] and
                    stat.S_IMODE(value.st_mode) == row['mode'], 'member-metadata')
            if stat.S_ISDIR(value.st_mode):
                require(row['type'] == 'directory', 'member-type')
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW,
                                dir_fd=fd)
                try:
                    current = os.fstat(child)
                    require((current.st_dev, current.st_ino) == pair,
                            'member-replaced')
                    visit(child, child_rel)
                finally:
                    os.close(child)
            elif stat.S_ISREG(value.st_mode):
                file_fd = os.open(name, os.O_RDONLY | NOFOLLOW, dir_fd=fd)
                try:
                    current = os.fstat(file_fd)
                    require((current.st_dev, current.st_ino) == pair and
                            row['type'] == 'regular' and current.st_nlink == 1 and
                            current.st_size == row['size'] and
                            hash_fd(file_fd) == row['sha256'], 'member-content')
                    inode_set.add(pair)
                    actual[child_rel] = {'dev': current.st_dev, 'ino': current.st_ino,
                                         'type': 'regular', 'uid': current.st_uid,
                                         'gid': current.st_gid,
                                         'mode': stat.S_IMODE(current.st_mode),
                                         'size': current.st_size,
                                         'sha256': row['sha256'], 'nlink': current.st_nlink}
                finally:
                    os.close(file_fd)
            else:
                raise Refusal('member-special')
    root_fd = open_directory(base)
    try:
        visit(root_fd, '')
    finally:
        os.close(root_fd)
    require(set(actual) == set(expected), 'member-set')
    return actual


def no_live_references(path):
    result = subprocess.run(['/usr/bin/sudo', '-A', '/usr/bin/lsof', '-nP', '-w',
                             '+D', str(path)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=180)
    require(result.returncode == 1 and not result.stdout and not result.stderr,
            'open-reference')
    ids = run(['/usr/bin/sudo', '-A', '/usr/bin/docker', 'ps', '-q']).stdout.splitlines()
    for cid in ids:
        obj = json.loads(run(['/usr/bin/sudo', '-A', '/usr/bin/docker', 'inspect',
                              cid.decode()]).stdout)[0]
        for mount in obj.get('Mounts', []):
            source = mount.get('Source', '')
            require(not (source == str(path) or source.startswith(str(path) + '/') or
                         str(path).startswith(source.rstrip('/') + '/')),
                    'running-container-reference')


def no_deleted_inodes(inodes):
    """Reject a retained descriptor to any inode retired by this transaction."""
    result = run(['/usr/bin/sudo', '-A', '/usr/bin/lsof', '-nP', '-w',
                  '-F0pDi', '+L1'], ok=(0, 1))
    require(not result.stderr and (result.returncode == 0 or not result.stdout),
            'deleted-inode-census-visibility')
    device = None
    for field in result.stdout.split(b'\0'):
        if field.startswith(b'D'):
            try:
                device = int(field[1:], 16)
            except ValueError:
                raise Refusal('deleted-inode-census-format')
        elif field.startswith(b'i') and device is not None:
            try:
                inode = int(field[1:])
            except ValueError:
                raise Refusal('deleted-inode-census-format')
            require((device, inode) not in inodes, 'deleted-inode-reference')


def rename_noreplace(source, destination):
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.renameat2
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                         ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    parent = open_directory(source.parent)
    try:
        if function(parent, os.fsencode(source.name), parent,
                    os.fsencode(destination.name), 1) != 0:
            raise OSError(ctypes.get_errno(), 'renameat2')
        os.fsync(parent)
    finally:
        os.close(parent)


def purge_directory(path, expected, journal):
    def same(value, record):
        return (value.st_dev == record['dev'] and value.st_ino == record['ino'] and
                value.st_uid == record['uid'] and value.st_gid == record['gid'] and
                stat.S_IMODE(value.st_mode) == record['mode'] and
                (record['type'] == 'directory' and stat.S_ISDIR(value.st_mode) or
                 record['type'] == 'regular' and stat.S_ISREG(value.st_mode) and
                 value.st_nlink == record['nlink'] and value.st_size == record['size']))

    def purge(fd, rel):
        names = os.listdir(fd)
        prefix = rel + '/' if rel else ''
        immediate = {key[len(prefix):] for key in expected
                     if key.startswith(prefix) and key != rel and
                     '/' not in key[len(prefix):]}
        require(set(names) == immediate, 'delete-member-set')
        for name in names:
            child_rel = name if not rel else rel + '/' + name
            value = os.stat(name, dir_fd=fd, follow_symlinks=False)
            record = expected.get(child_rel)
            require(record is not None and same(value, record) and
                    not stat.S_ISLNK(value.st_mode), 'delete-member-identity')
            if stat.S_ISDIR(value.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW,
                                dir_fd=fd)
                try:
                    require(same(os.fstat(child), record), 'delete-directory-replaced')
                    purge(child, child_rel)
                finally:
                    os.close(child)
                os.rmdir(name, dir_fd=fd)
                os.fsync(fd)
            elif stat.S_ISREG(value.st_mode):
                file_fd = os.open(name, os.O_RDONLY | NOFOLLOW, dir_fd=fd)
                try:
                    require(same(os.fstat(file_fd), record) and
                            hash_fd(file_fd) == record['sha256'],
                            'delete-file-replaced')
                finally:
                    os.close(file_fd)
                os.unlink(name, dir_fd=fd)
                os.fsync(fd)
            else:
                raise Refusal('delete-member-special')
            journal.append({'event': 'member-deleted', 'path': child_rel,
                            'dev': record['dev'], 'ino': record['ino'],
                            'type': record['type']})
        os.fsync(fd)
    parent = open_directory(path.parent)
    child = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=parent)
    try:
        require(same(os.fstat(child), expected['']), 'delete-root-identity')
        purge(child, '')
    finally:
        os.close(child)
    os.rmdir(path.name, dir_fd=parent)
    os.fsync(parent)
    journal.append({'event': 'root-deleted', 'dev': expected['']['dev'],
                    'ino': expected['']['ino']})
    os.close(parent)


def candidate_git_status(rows, deleted=False):
    command = ['/usr/bin/sudo', '-A', '-u', '#1000', '/usr/bin/env', '-i',
               'PATH=/usr/bin:/bin', 'HOME=/nonexistent', 'LANG=C', 'LC_ALL=C',
               'TZ=UTC', 'GIT_CONFIG_NOSYSTEM=1', 'GIT_CONFIG_GLOBAL=/dev/null',
               'GIT_NO_REPLACE_OBJECTS=1', 'GIT_TERMINAL_PROMPT=0',
               'GIT_OPTIONAL_LOCKS=0', '/usr/bin/git', '-C', str(ROOT)]
    head = subprocess.check_output(command + ['rev-parse', 'HEAD']).decode().strip()
    require(head == 'c81aeaca5cedd893981a058444fa11a03a49a744', 'candidate-head')
    status = subprocess.check_output(command + ['status', '--ignored', '--porcelain=v1',
                                                  '--', 'docs/verification/evidence'],
                                     ).decode().splitlines()
    expected_files = sorted(row['path'] for row in rows if row['type'] == 'regular')
    if deleted:
        observed = sorted(line[3:] for line in status if line.startswith(' D '))
        require(observed == expected_files and len(status) == len(expected_files),
                'post-delete-git-status')
    else:
        require(not status, 'pre-delete-git-status')


def execute():
    require(os.geteuid() == 0, 'root-required')
    require(not any(os.path.lexists(path) for path in (CLAIM, JOURNAL, STATUS, QUARANTINE)),
            'one-shot-collision')
    require(identity(ROOT) == ROOT_ID and identity(TARGET) == TARGET_ID,
            'target-identity')
    require(not any(os.path.lexists(path) for path in LEASES), 'active-lease')
    require(os.statvfs(REPO).f_bavail * os.statvfs(REPO).f_frsize >= HOST_FLOOR and
            os.statvfs(SCRATCH).f_bavail * os.statvfs(SCRATCH).f_frsize >= SCRATCH_FLOOR,
            'capacity-floor')
    rows = inventory_rows()
    candidate_git_status(rows)
    reject_nested_mount(TARGET)
    before_snapshot = census(TARGET, rows)
    no_live_references(TARGET)
    exclusive_json(CLAIM, {'status': 'PENDING', 'target': str(TARGET),
                           'target_identity': TARGET_ID, 'inventory': INVENTORY_SHA,
                           'capsule': CAPSULE_SHA, 'time_ns': time.time_ns()})
    journal = Journal(JOURNAL)
    renamed = False
    try:
        journal.append({'event': 'preflight-pass', 'members': len(rows),
                        'inodes': len(before_snapshot)})
        rename_noreplace(TARGET, QUARANTINE)
        renamed = True
        require(identity(QUARANTINE) == TARGET_ID, 'quarantine-root-identity')
        journal.append({'event': 'quarantine-renamed', 'identity': identity(QUARANTINE)})
        reject_nested_mount(QUARANTINE)
        after_snapshot = census(QUARANTINE, rows)
        require(after_snapshot == before_snapshot, 'quarantine-census')
        no_live_references(QUARANTINE)
        # Remove traversal/write authority from the original uid before any
        # unlink.  A fresh descriptor census after this boundary detects a
        # last-moment replacement; non-root candidate writers can no longer
        # reach any descendant while the transaction owns the root-only fd.
        quarantine_fd = open_directory(QUARANTINE)
        try:
            os.fchown(quarantine_fd, 0, 0)
            os.fchmod(quarantine_fd, 0o500)
            os.fsync(quarantine_fd)
        finally:
            os.close(quarantine_fd)
        locked_snapshot = census(QUARANTINE, rows, root_override=(0, 0, 0o500))
        expected_locked = dict(after_snapshot)
        expected_locked[''] = dict(expected_locked[''], uid=0, gid=0, mode=0o500)
        require(locked_snapshot == expected_locked, 'quarantine-lockdown-census')
        no_live_references(QUARANTINE)
        journal.append({'event': 'quarantine-verified'})
        purge_directory(QUARANTINE, locked_snapshot, journal)
        require(not os.path.lexists(TARGET) and not os.path.lexists(QUARANTINE),
                'post-delete-path')
        no_deleted_inodes({(row['dev'], row['ino']) for row in before_snapshot.values()})
        candidate_git_status(rows, deleted=True)
        inventory_rows()
        require(identity(ROOT) == ROOT_ID and sha_path(INVENTORY) == INVENTORY_SHA and
                sha_path(CAPSULE) == CAPSULE_SHA, 'post-delete-preservation')
        journal.append({'event': 'deletion-complete', 'deleted_inodes': len(before_snapshot)})
        journal.close()
        exclusive_json(STATUS, {'status': 'READY_FOR_VERIFICATION',
                                'transaction': 'PASS', 'target': str(TARGET),
                                'deleted_inodes': len(before_snapshot),
                                'journal_sha256': sha_path(JOURNAL)})
        return 0
    except BaseException as error:
        try:
            if journal.fd is not None:
                renamed = (os.path.lexists(QUARANTINE) and not os.path.lexists(TARGET))
                journal.append({'event': 'failure', 'error': type(error).__name__,
                                'renamed': renamed,
                                'target_present': os.path.lexists(TARGET),
                                'quarantine_present': os.path.lexists(QUARANTINE)})
                journal.close()
        except BaseException:
            pass
        raise


def main(argv=None):
    require((sys.argv[1:] if argv is None else argv) == ['--execute'], 'usage')
    lock_fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute()
    finally:
        os.close(lock_fd)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BaseException as error:
        print('RETIREMENT_FAIL ' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        sys.exit(1)
