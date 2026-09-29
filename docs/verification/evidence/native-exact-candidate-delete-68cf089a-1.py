#!/usr/bin/env python3
"""Root-only, lease-owned, quarantine-first deletion of exactly two tmpfs roots.

No root Git command is used.  An unprivileged admission process binds source
cleanliness; this helper trusts only its hash-bound receipt and retained inputs.
Root adversaries are outside scope after root-owned 0700 sealing.
"""
import ctypes
import hashlib
import json
import os
import stat
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

C = Path('/dev/shm/mckernel-exact-candidate-68cf089a-1')
B = Path('/dev/shm/mckernel-exact-metadata-backup-68cf089a-1')
QC = Path('/dev/shm/.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1')
QB = Path('/dev/shm/.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
LEASE = SCRATCH / 'native-exact-build-lease-68cf089a-1.json'
JOURNAL = SCRATCH / 'native-exact-candidate-delete-68cf089a-1.journal.jsonl'
PREFLIGHT = SCRATCH / 'native-exact-candidate-delete-preflight-68cf089a-1.json'
POST_OUT = SCRATCH / 'native-exact-live-reference-post-seal-68cf089a-1.stdout.json'
POST_ERR = SCRATCH / 'native-exact-live-reference-post-seal-68cf089a-1.stderr.txt'
OBSERVER = Path('/home/holden/mckernel/docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py')
RET = Path('/home/holden/mckernel/docs/verification/evidence/stability-native-exact-prepared-candidate-retention-68cf089a-20260929-1.tar.gz')
PREP = Path('/home/holden/mckernel/docs/verification/evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz')
PREP_RECORD = Path('/home/holden/mckernel/docs/verification/stability-native-exact-candidate-preparation-checkpoint-20260929-1.json')
RET_RECORD = Path('/home/holden/mckernel/docs/verification/stability-native-exact-prepared-candidate-retention-20260929-1.json')
INPUTS = SCRATCH / 'native-exact-inputs-68cf089a-1.json'
REQUEST = SCRATCH / 'native-exact-build-request-68cf089a-1.json'
INVENTORY = SCRATCH / 'native-exact-complete-worktree-inventory-68cf089a-1.json'
RELEASE = SCRATCH / 'native-exact-candidate-delete-release-68cf089a-1.json'
RET_SHA = 'eed1879bd35c62d7aa629189dfc0c46254680209ab02f933278c70c8cf9880c6'
PREP_SHA = '78e2b5c44e9ae00f2f463ac8b93723e26d00877fbbe7ecfb285d1d89d6404264'
INPUTS_SHA = 'ae0c5f74e3e3f06176c46f2f174b1109c11a4e88f23ee71fd7432e6325262abd'
REQUEST_SHA = '25f820e2994d41427ed16cf5f062d647125ccb7144f63afe618e88ccce7f576c'
PREP_RECORD_SHA = 'bc8b3a6d819208b7266e39bb91862ddbacba5ec700dcf14b960fe7857aa2be99'
RET_RECORD_SHA = '129d25f80a29fc321cae94c3e1f4db4279e42c1b100ea41c6406a3a3e133f7b6'
OBSERVER_SHA = '4a15271df7e14f1a95136579f157f0fc719048143547be6a54a242b99c3f8e05'
INVENTORY_SHA = '743c05648112cee5af2eda235fba11a2f32d50a9d3074423c0c064d52a1682c0'
RELEASE_SHA = 'UNSET-REQUIRES-INDEPENDENT-RELEASE-SHA256'
ROOTS = ((C, QC, 26, 14117, 10462), (B, QB, 26, 24701, 87))
FRESHNESS_SECONDS = 300
RENAME_NOREPLACE = 1
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
        fail('required regular input missing: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def write_all(fd, data):
    write_loop(lambda chunk: os.write(fd, chunk), data)


def write_loop(writer, data):
    offset = 0
    while offset < len(data):
        count = writer(data[offset:])
        if count <= 0:
            fail('short/failed durable write')
        offset += count


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def free_map():
    def item(path):
        value = os.statvfs(path)
        return value.f_bavail * value.f_frsize
    return {'host': item('/'), 'scratch': item(SCRATCH), 'tmpfs': item('/dev/shm')}


def lstat_id(path):
    try:
        value = path.lstat()
        return {'path': str(path), 'dev': value.st_dev, 'inode': value.st_ino,
                'mode': format(stat.S_IMODE(value.st_mode), '04o'), 'uid': value.st_uid, 'gid': value.st_gid,
                'type': 'directory' if stat.S_ISDIR(value.st_mode) else 'other'}
    except FileNotFoundError:
        return {'path': str(path), 'absent': True}


def survivors():
    return {'original': [lstat_id(C), lstat_id(B)], 'quarantine': [lstat_id(QC), lstat_id(QB)]}


class Journal:
    def __init__(self):
        self.fd = os.open(JOURNAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        fsync_dir(SCRATCH)

    def write(self, phase, fields):
        write_all(self.fd, (json.dumps({'utc': utcnow(), 'phase': phase, **fields}, sort_keys=True,
                                        separators=(',', ':')) + '\n').encode())
        os.fsync(self.fd)

    def close(self):
        os.close(self.fd)


def acquire_lease():
    fd = os.open(LEASE, lease_open_flags(), 0o600)
    try:
        write_all(fd, json.dumps({'schema': 'mckernel.native-exact-candidate-cleanup-lease.v1',
                                  'pid': os.getpid(), 'started_at_utc': utcnow()}, sort_keys=True).encode() + b'\n')
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(SCRATCH)


def lease_open_flags():
    return os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def release_lease():
    os.unlink(LEASE)
    fsync_dir(SCRATCH)


def parse_utc(value):
    if type(value) is not str or not value.endswith('Z'):
        fail('invalid UTC receipt timestamp')
    return datetime.fromisoformat(value[:-1] + '+00:00').timestamp()


def validate_receipt():
    receipt = exact_json(PREFLIGHT)
    required = {'schema': 'mckernel.native-exact-candidate-delete-preflight.v2',
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'observer_sha256': OBSERVER_SHA, 'deleter_sha256': sha(Path(__file__)),
                'inventory_sha256': INVENTORY_SHA, 'retention_capsule_sha256': RET_SHA,
                'preparation_archive_sha256': PREP_SHA, 'preparation_record_sha256': PREP_RECORD_SHA,
                'retention_record_sha256': RET_RECORD_SHA, 'request_sha256': REQUEST_SHA,
                'inputs_sha256': INPUTS_SHA, 'release_record_path': str(RELEASE),
                'release_record_sha256': RELEASE_SHA, 'candidate_sha': '68cf089a22b0a0c034a7f1fcc695853fbf5c07eb',
                'ihk_sha': '3114d9e7101ad52030eb3effa849a5c108972a1f', 'no_active_docker_binds': True}
    for key, value in required.items():
        if receipt.get(key) != value:
            fail('preflight receipt mismatch: ' + key)
    observed = parse_utc(receipt.get('observed_at_utc'))
    if observed > time.time() + 5 or time.time() - observed > FRESHNESS_SECONDS:
        fail('preflight receipt stale')
    receipt_roots = receipt.get('roots')
    if type(receipt_roots) is not list or len(receipt_roots) != 2:
        fail('preflight roots malformed')
    expected = {(str(original), dev, inode) for original, _q, dev, inode, _count in ROOTS}
    actual = {(item.get('path'), item.get('device_number'), item.get('inode')) for item in receipt_roots if type(item) is dict}
    if actual != expected:
        fail('preflight root identities mismatch')


def entry(path, with_digest=True):
    info = path.lstat()
    if stat.S_ISDIR(info.st_mode):
        kind, digest = 'directory', None
    elif stat.S_ISREG(info.st_mode):
        kind, digest = 'file', None
        if with_digest:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino, opened.st_mode) != (info.st_dev, info.st_ino, info.st_mode):
                    fail('safe path file identity changed: ' + str(path))
                value = hashlib.sha256()
                for block in iter(lambda: os.read(fd, 1 << 20), b''):
                    value.update(block)
                digest = value.hexdigest()
            finally:
                os.close(fd)
    elif stat.S_ISLNK(info.st_mode):
        kind = 'symlink'
        digest = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest() if with_digest else None
    else:
        fail('unsupported inventory inode: ' + str(path))
    return {'type': kind, 'mode': format(stat.S_IMODE(info.st_mode), '04o'), 'sha256': digest,
            'dev': info.st_dev, 'inode': info.st_ino}


def inventory_preseal():
    """The only path walk. It binds logical metadata and inode identities."""
    if sha(INVENTORY) != INVENTORY_SHA:
        fail('complete inventory SHA remains unbound')
    manifest = exact_json(INVENTORY)
    if manifest.get('roots') != [str(C), str(B)]:
        fail('complete inventory root binding mismatch')
    rows = manifest.get('worktree_inventory')
    if type(rows) is not list or not rows:
        fail('complete inventory missing worktree_inventory')
    roots = {str(C.relative_to('/')), str(B.relative_to('/'))}
    expected = {}
    for row in rows:
        if type(row) is not dict or set(row) != {'path', 'type', 'mode', 'sha256'}:
            fail('invalid inventory row')
        name = row['path'].rstrip('/')
        parts = PurePosixPath(name).parts
        if (not isinstance(row['path'], str) or row['type'] not in ('directory', 'file', 'symlink') or
                not isinstance(row['mode'], str) or PurePosixPath(name).is_absolute() or '..' in parts or name in expected or
                not any(name == root or name.startswith(root + '/') for root in roots)):
            fail('invalid/outside inventory name')
        if (row['type'] == 'directory' and row['sha256'] is not None) or (row['type'] != 'directory' and
                (not isinstance(row['sha256'], str) or len(row['sha256']) != 64)):
            fail('invalid inventory digest')
        expected[name] = {'type': row['type'], 'mode': row['mode'], 'sha256': row['sha256']}
    with tarfile.open(RET, 'r:gz') as archive:
        members = archive.getmembers()
        if len(members) != 920 or len({member.name for member in members}) != 920:
            fail('capsule count/uniqueness mismatch')
        for member in members:
            if not (member.isdir() or member.isfile() or member.issym()):
                fail('unsupported capsule member')
            kind = 'directory' if member.isdir() else 'file' if member.isfile() else 'symlink'
            digest = None if kind == 'directory' else (hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                      if kind == 'file' else hashlib.sha256(os.fsencode(member.linkname)).hexdigest())
            name = member.name.rstrip('/')
            capsule = {'type': kind, 'mode': format(member.mode, '04o'), 'sha256': digest}
            if any(name == root or name.startswith(root + '/') for root in roots):
                if name in expected and expected[name] != capsule:
                    fail('manifest/capsule mismatch: ' + name)
                expected[name] = capsule
            elif {key: entry(Path('/') / name)[key] for key in ('type', 'mode', 'sha256')} != capsule:
                fail('external capsule mismatch: ' + name)
    allowed = set(expected)
    for name in list(allowed):
        parts = PurePosixPath(name).parts
        allowed.update(str(PurePosixPath(*parts[:index])) for index in range(1, len(parts)))
    for original, _quarantine, dev, inode, _count in ROOTS:
        logical, actual_names, stack = str(original.relative_to('/')), set(), [original]
        root = original.lstat()
        if not stat.S_ISDIR(root.st_mode) or stat.S_ISLNK(root.st_mode) or (root.st_dev, root.st_ino, root.st_uid, root.st_gid, format(stat.S_IMODE(root.st_mode), '04o')) != (dev, inode, 1000, 1000, '0755'):
            fail('top-level original identity/ownership/mode mismatch')
        while stack:
            path = stack.pop()
            rel = path.relative_to(original)
            name = logical if rel == Path('.') else logical + '/' + str(rel)
            actual_names.add(name)
            live = entry(path, with_digest=False)
            wanted = expected.get(name)
            if name not in allowed or (wanted is not None and
                    {key: live[key] for key in ('type', 'mode')} != {key: wanted[key] for key in ('type', 'mode')}):
                fail('inventory differs: ' + name)
            if wanted is None and live['type'] != 'directory':
                fail('derived parent is not directory: ' + name)
            if wanted is None:
                expected[name] = live
            else:
                expected[name] = bind_live_identity(wanted, live)
            if live['type'] == 'directory':
                for child in os.scandir(path):
                    if Path(child.path).lstat().st_dev != dev:
                        fail('nested mount/cross-device entry: ' + child.path)
                    stack.append(Path(child.path))
        if actual_names != {name for name in allowed if name == logical or name.startswith(logical + '/')}:
            fail('unknown/untracked name in root')
    return expected


def bind_live_identity(wanted, live):
    """Add observed identity without replacing the immutable content digest."""
    return dict(wanted, dev=live['dev'], inode=live['inode'])


def fd_open(parentfd, name):
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parentfd)


def check_root_fd(fd, dev, inode, mode, uid, gid):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino, info.st_uid, info.st_gid, format(stat.S_IMODE(info.st_mode), '04o')) != (dev, inode, uid, gid, mode):
        fail('top-level descriptor identity mismatch')


def root_mode(phase):
    if phase == 'original':
        return '0755'
    if phase == 'sealed':
        return '0700'
    fail('unknown root phase')


def rename_noreplace(parentfd, old, new):
    if LIBC.renameat2(parentfd, os.fsencode(old), parentfd, os.fsencode(new), RENAME_NOREPLACE):
        fail('renameat2(RENAME_NOREPLACE): ' + os.strerror(ctypes.get_errno()))


def fd_names(fd):
    return set(os.listdir(fd))


def fd_hash(fd, name):
    child = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    try:
        info = os.fstat(child)
        if not stat.S_ISREG(info.st_mode):
            fail('file descriptor type rejection: ' + name)
        digest = hashlib.sha256()
        while True:
            block = os.read(child, 1 << 20)
            if not block:
                return info, digest.hexdigest()
            digest.update(block)
    finally:
        os.close(child)


def same(info, wanted, kind):
    return (info.st_dev, info.st_ino, format(stat.S_IMODE(info.st_mode), '04o')) == (wanted['dev'], wanted['inode'], wanted['mode']) and ((kind == 'directory' and stat.S_ISDIR(info.st_mode)) or (kind == 'file' and stat.S_ISREG(info.st_mode)) or (kind == 'symlink' and stat.S_ISLNK(info.st_mode)))


def logical_scope(expected, original):
    logical = str(original.relative_to('/'))
    return {name[len(logical) + 1:]: value for name, value in expected.items() if name.startswith(logical + '/')}


def delete_verified(fd, expected, prefix, device, journal, root_name):
    direct = {name[len(prefix):].split('/', 1)[0] for name in expected if name.startswith(prefix) and name[len(prefix):]}
    if fd_names(fd) != direct:
        fail('descriptor inventory changed at ' + prefix)
    for name in sorted(direct):
        rel, wanted = prefix + name, expected[prefix + name]
        journal.write('delete-entry', {'root': root_name, 'path': rel})
        first = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if first.st_dev != device or not same(first, wanted, wanted['type']):
            fail('descriptor lstat rejection: ' + rel)
        if wanted['type'] == 'directory':
            child = fd_open(fd, name)
            try:
                if not same(os.fstat(child), wanted, 'directory'):
                    fail('directory fstat rejection: ' + rel)
                delete_verified(child, expected, rel + '/', device, journal, root_name)
            finally:
                os.close(child)
            if not same(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted, 'directory'):
                fail('directory inode changed before rmdir: ' + rel)
            os.rmdir(name, dir_fd=fd)
        elif wanted['type'] == 'file':
            opened, digest = fd_hash(fd, name)
            if not same(opened, wanted, 'file') or digest != wanted['sha256']:
                fail('file descriptor/hash rejection: ' + rel)
            if not same(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted, 'file'):
                fail('file inode changed before unlink: ' + rel)
            os.unlink(name, dir_fd=fd)
        elif wanted['type'] == 'symlink':
            if hashlib.sha256(os.fsencode(os.readlink(name, dir_fd=fd))).hexdigest() != wanted['sha256']:
                fail('symlink target rejection: ' + rel)
            if not same(os.stat(name, dir_fd=fd, follow_symlinks=False), wanted, 'symlink'):
                fail('symlink inode changed before unlink: ' + rel)
            os.unlink(name, dir_fd=fd)
        else:
            fail('unsupported validated type')


def capture_observer():
    for path in (POST_OUT, POST_ERR):
        if path.exists() or path.is_symlink():
            fail('observer capture path not fresh: ' + str(path))
    outfd = errfd = None
    try:
        outfd = os.open(POST_OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        errfd = os.open(POST_ERR, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            result = subprocess.run([sys.executable, str(OBSERVER), '--target', str(QC), '--target', str(QB)],
                                    stdin=subprocess.DEVNULL, stdout=outfd, stderr=errfd, check=False, timeout=120)
        finally:
            os.fsync(outfd)
            os.fsync(errfd)
    finally:
        if outfd is not None:
            os.close(outfd)
        if errfd is not None:
            os.close(errfd)
        fsync_dir(SCRATCH)
    if result.returncode != 0:
        fail('observer returned failure; captures retained')
    record = exact_json(POST_OUT)
    if record.get('schema') != 'mckernel.read-only-live-reference-snapshot.v6' or record.get('status') != 'PASS' or record.get('observer_sha256') != OBSERVER_SHA:
        fail('observer PASS schema/hash mismatch')
    if Path('/proc/%d' % record.get('observer_pid', -1)).exists():
        fail('observer process not terminal')
    if record.get('boot_id') != Path('/proc/sys/kernel/random/boot_id').read_text().strip() or not record.get('scan_complete'):
        fail('observer boot/coverage mismatch')
    observed = {(item.get('path'), item.get('device_number'), item.get('inode'), item.get('mode'),
                 item.get('tree_inode_count')) for item in record.get('roots', []) if type(item) is dict}
    expected = {(str(quarantine), dev, inode, '0700', count)
                for _original, quarantine, dev, inode, count in ROOTS}
    if observed != expected:
        fail('observer exact quarantine roots mismatch')
    rounds = record.get('rounds')
    if type(rounds) is not list or len(rounds) < 2 or not all(round_.get('clean') and round_.get('complete_mount_proofs')
                                                              for round_ in rounds[-2:]):
        fail('observer converged clean-round proof mismatch')
    return record


def main():
    if os.geteuid() != 0:
        fail('root-only helper')
    journal = Journal()
    lease = False
    try:
        acquire_lease(); lease = True
        before = free_map()
        journal.write('lease-acquired', {'lease': str(LEASE), 'helper_sha256': sha(Path(__file__)),
                                         'inventory_sha256': INVENTORY_SHA, 'inputs_sha256': INPUTS_SHA,
                                         'release_sha256': RELEASE_SHA, 'free_before': before,
                                         'planned_roots': survivors()})
        validate_receipt()
        for path, value in ((RET, RET_SHA), (PREP, PREP_SHA), (PREP_RECORD, PREP_RECORD_SHA),
                            (RET_RECORD, RET_RECORD_SHA), (INPUTS, INPUTS_SHA), (REQUEST, REQUEST_SHA),
                            (INVENTORY, INVENTORY_SHA), (RELEASE, RELEASE_SHA), (OBSERVER, OBSERVER_SHA)):
            if sha(path) != value:
                fail('fixed input hash mismatch: ' + str(path))
        expected = inventory_preseal()
        parentfd = os.open('/dev/shm', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        held = []
        try:
            for original, quarantine, dev, inode, count in ROOTS:
                if quarantine.exists() or quarantine.is_symlink():
                    fail('quarantine exists: ' + str(quarantine))
                fd = fd_open(parentfd, original.name)
                check_root_fd(fd, dev, inode, '0755', 1000, 1000)
                held.append((original, quarantine, fd, dev, inode, count))
            for original, quarantine, fd, dev, inode, _count in held:
                journal.write('seal-before', {'original': lstat_id(original), 'quarantine': str(quarantine)})
                os.fchown(fd, 0, 0); os.fchmod(fd, 0o700)
                check_root_fd(fd, dev, inode, '0700', 0, 0)
                journal.write('seal-after', {'original': lstat_id(original)})
                rename_noreplace(parentfd, original.name, quarantine.name)
                journal.write('quarantine-after', {'original': lstat_id(original), 'quarantine': lstat_id(quarantine)})
            for _o, _q, fd, _d, _i, _c in held:
                os.close(fd)
            held = []
            journal.write('target-fds-closed', {'survivors': survivors()})
            capture_observer()
            journal.write('observer-pass', {'stdout': str(POST_OUT), 'stderr': str(POST_ERR)})
            for original, quarantine, dev, inode, _count in ROOTS:
                qfd = fd_open(parentfd, quarantine.name)
                try:
                    check_root_fd(qfd, dev, inode, '0700', 0, 0)
                    scoped = logical_scope(expected, original)
                    journal.write('delete-start', {'original': str(original), 'quarantine': str(quarantine), 'inode': inode})
                    delete_verified(qfd, scoped, '', dev, journal, str(original))
                finally:
                    os.close(qfd)
                os.rmdir(quarantine.name, dir_fd=parentfd)
                journal.write('delete-complete', {'original': str(original), 'quarantine': str(quarantine), 'survivors': survivors()})
        finally:
            for _o, _q, fd, _d, _i, _c in held:
                os.close(fd)
            os.close(parentfd)
        if any(not item.get('absent') for group in survivors().values() for item in group):
            fail('original/quarantine path remains')
        after = free_map()
        result = {'schema': 'mckernel.native-exact-candidate-deletion-result.v4', 'targets_absent': True,
                  'observer_sha256': OBSERVER_SHA, 'free_before': before, 'free_after': after,
                  'net_statvfs_delta_bytes': {key: after[key] - before[key] for key in before},
                  'attributable_entry_bytes': 'not derivable from statvfs; journal binds every deleted entry'}
        journal.write('terminal-success', result)
        release_lease(); lease = False
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    except BaseException as error:
        try:
            journal.write('terminal-failure', {'error': repr(error), 'survivors': survivors(), 'lease_retained': lease})
        except BaseException:
            pass
        raise
    finally:
        journal.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        assert RENAME_NOREPLACE == 1 and (lease_open_flags() & os.O_EXCL)
        chunks = []
        write_loop(lambda block: (chunks.append(block[:1]) or 1), b'abc')
        assert b''.join(chunks) == b'abc'
        assert root_mode('original') == '0755' and root_mode('sealed') == '0700'
        assert logical_scope({str(C.relative_to('/')) + '/x': 1, str(B.relative_to('/')) + '/y': 2}, C) == {'x': 1}
        class Fake:
            st_dev, st_ino, st_mode = 26, 9, stat.S_IFIFO | 0o600
        assert not same(Fake(), {'dev': 26, 'inode': 9, 'mode': '0600'}, 'file')
        assert bind_live_identity({'type': 'file', 'mode': '0644', 'sha256': 'a' * 64},
                                  {'dev': 26, 'inode': 9, 'sha256': None})['sha256'] == 'a' * 64
        assert bind_live_identity({'type': 'symlink', 'mode': '0777', 'sha256': 'b' * 64},
                                  {'dev': 26, 'inode': 10, 'sha256': None})['sha256'] == 'b' * 64
        print('deleter pure synthetic assertions passed')
    else:
        main()
