#!/usr/bin/python3
"""Finite unreleased duplicate cleanup. Default SOURCE_ONLY; no historical replay.
Only --execute can unlink exact pinned candidates. Independent release binds
source, manifest, fresh observation, resource reserve and existing exclusions.
Root --observe is read-only except acquiring/releasing existing flock.
No root/Docker/operation executed during source preparation.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

BASE = Path('/home/holden/mckernel-work/host-preparation/duplicate-archive-cleanup-execution-preparation-20261018-1')
REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
MANIFEST = Path('/home/holden/mckernel-work/host-preparation/supervisor-scratch-duplicate-cleanup-20261018-1/candidate-manifest.json')
PIN = '8255bbf869d9904b8ff0a4d6e2ce6dc5264493db1b2c3f6574ad98c04982956d'
ADVISORY = Path('/home/holden/mckernel-work/host-preparation/supervisor-pair-terminal-source-review-20261018-1/CLEANUP-CANDIDATE-REVIEW.md')
ADVISORY_PIN = 'be259235b8657dde76f4ee77c8963328318876ebc48d5d5732e727f92098ddd3'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
LOCK = Path('/run/lock/mckernel-development.lock')
LOCK_ID = (27, 4)
PARENTS = {str(ROOT / n) for n in ('native-application-start-retained-20260908-1', 'native-ultra-final-retained-20260909-1', 'native-application-launcher-retained-20260908-1')}
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}
ATTEST = ('no_active_or_queued_indirect_consumers', 'no_writers_or_rename_publishers', 'sole_cleanup_coordinator', 'scratch21_and_exclusions_preserved', 'included_usage_guard_active')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def raw_small(path, cap=4 << 20):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, 'small file shape: ' + str(path))
        raw = os.read(fd, cap + 1)
        require(len(raw) == before.st_size and meta(os.fstat(fd)) == meta(before), 'small file raced')
        require(meta(os.lstat(path)) == meta(before), 'small file name raced')
        return raw
    finally:
        os.close(fd)


def meta(s):
    return dict(dev=s.st_dev, inode=s.st_ino, mode=stat.S_IMODE(s.st_mode), uid=s.st_uid, gid=s.st_gid,
                nlink=s.st_nlink, size=s.st_size, allocated_bytes=s.st_blocks * 512,
                mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, is_regular=stat.S_ISREG(s.st_mode))


def pinned():
    raw = raw_small(MANIFEST)
    require(digest(raw) == PIN and digest(raw_small(ADVISORY)) == ADVISORY_PIN, 'frozen input pin')
    m = json.loads(raw)
    rows = m['rows']
    require(len(rows) == 120 and len({r['candidate'] for r in rows}) == 120, 'exact count')
    for r in rows:
        p = Path(r['candidate'])
        require(str(p.parent) in PARENTS and '..' not in p.parts, 'allowlist parent')
        require(r['candidate_metadata']['dev'] == 1828 and r['candidate_metadata']['nlink'] == 1, 'candidate shape')
        require(r['retained_repo_path'] == str(REPO / 'docs/verification/evidence' / p.name), 'retained join')
    return m


def run(argv, data=None):
    p = subprocess.run(argv, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, timeout=45)
    require(p.returncode == 0, 'command failed: ' + repr(argv) + ' ' + p.stderr[:2048].decode(errors='replace'))
    require(len(p.stdout) <= 32 << 20, 'command output bound')
    return p.stdout


def safe_directory(path):
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts, 'absolute directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [[os.fstat(fd).st_dev, os.fstat(fd).st_ino]]
    try:
        for name in p.parts[1:]:
            n = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = n
            s = os.fstat(fd)
            chain.append([s.st_dev, s.st_ino])
        return fd, chain
    except BaseException:
        os.close(fd)
        raise


def related(path, parents):
    return any(path == p or path.startswith(p + '/') for p in parents)


def exposes(path, parents):
    return related(path, parents) or any(p.startswith(path.rstrip('/') + '/') for p in parents)


def capacity():
    result = {}
    for label, path in [('host', REPO), ('scratch', ROOT)]:
        s = os.statvfs(path)
        result[label] = dict(bavail=s.f_bavail, bfree=s.f_bfree, blocks=s.f_blocks, frsize=s.f_frsize,
                             available_bytes=s.f_bavail * s.f_frsize)
    return result


def mount_identity():
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT, 'boot changed')
    item = json.loads(run(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o', 'TARGET,SOURCE,FSTYPE,UUID']).decode())['filesystems']
    require(len(item) == 1, 'mount shape')
    mount = item[0]
    require(mount['target'] == str(ROOT) and mount['source'] == '/dev/loop36' and mount['uuid'] == UUID and mount['fstype'] == 'ext4', 'mount binding')
    require(os.stat(ROOT).st_dev == 1828, 'mount device')
    loops = json.loads(run(['/usr/sbin/losetup', '--json', '--list', '--output', 'NAME,BACK-FILE,OFFSET,SIZELIMIT', '/dev/loop36']))['loopdevices']
    require(len(loops) == 1 and loops[0]['name'] == '/dev/loop36', 'loop binding')
    back = loops[0]['back-file']
    require(not back.endswith(' (deleted)'), 'deleted backing')
    s = os.lstat(back)
    require(stat.S_ISREG(s.st_mode) and s.st_size == 110 * (1 << 30), '110GiB backing required')
    return {'mount': mount, 'loop': loops[0], 'backing_identity': [s.st_dev, s.st_ino, s.st_size]}


def records():
    result = {}
    for p in sorted(ROOT.iterdir()):
        if any(term in p.name for term in ('lease', 'lock', 'exclusion', 'quarantine')):
            s = p.lstat()
            require(stat.S_ISREG(s.st_mode), 'ownership record not regular: ' + str(p))
            result[str(p)] = {'metadata': meta(s), 'sha256': digest(raw_small(p))}
    require(str(ROOT / 'mckernel-heavy-operation.lock') not in result, 'heavy owner present')
    return result


def git_available(rows):
    expected = {}
    for r in rows:
        expected[r['restoration']['git_blob']] = ('blob', str(r['restoration']['size']))
        expected[r['restoration']['git_commit']] = ('commit', None)
    keys = sorted(expected)
    data = ('\n'.join(keys) + '\n').encode()
    output = run(['/usr/bin/git', '-c', 'safe.directory=' + str(REPO), '-C', str(REPO), 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], data).decode().splitlines()
    require(len(output) == len(keys), 'Git object census')
    for key, line in zip(keys, output):
        parts = line.split()
        kind, size = expected[key]
        require(len(parts) == 3 and parts[0] == key and parts[1] == kind and (size is None or parts[2] == size), 'Git object unavailable: ' + key)
    return {'objects': len(keys), 'object_ids_sha256': digest(data)}


def container_census():
    ids = run(['/usr/bin/docker', 'ps', '-aq', '--no-trunc']).decode().splitlines()
    require(len(ids) <= 256, 'container census bound')
    rows = []
    for cid in ids:
        require(len(cid) == 64 and all(c in '0123456789abcdef' for c in cid), 'container ID')
        items = json.loads(run(['/usr/bin/docker', 'inspect', '--type', 'container', cid]))
        require(len(items) == 1 and items[0]['Id'] == cid, 'container inspect')
        item = items[0]
        for bind in item['Mounts']:
            source = bind.get('Source', '')
            require(source and not exposes(source, PARENTS), 'container exposes candidate ancestry: ' + cid + ' ' + source)
        rows.append({'id': cid, 'mounts': item['Mounts'], 'state': item['State']['Status']})
    require(run(['/usr/bin/docker', 'ps', '-aq', '--no-trunc']).decode().splitlines() == ids, 'container set raced')
    return rows


def decode_mount(s):
    for a, b in [('\\040', ' '), ('\\011', '\t'), ('\\012', '\n'), ('\\134', '\\')]:
        s = s.replace(a, b)
    return s


def proc_identity(pid):
    parts = Path('/proc', str(pid), 'stat').read_bytes().rpartition(b') ')[2].split()
    require(len(parts) >= 20, 'proc stat')
    return int(parts[19]), int(parts[6]), parts[0].decode()


def strip_deleted(path):
    suffix = ' (deleted)'
    return path[:-len(suffix)] if path.endswith(suffix) else path


def process_census(held, proc_root=Path('/proc')):
    # Any disappearance/permission failure refuses this attempt. No silent skip.
    pids = sorted(int(p.name) for p in proc_root.iterdir() if p.name.isdigit())
    require(len(pids) <= 4096, 'PID bound')
    identities = []
    inode_targets = {(r['candidate_metadata']['dev'], r['candidate_metadata']['inode']) for r in held['rows']}
    self_fds = set(held['target_fds']) | set(held['parent_fds'])
    for pid in pids:
        before = proc_identity(pid)
        identities.append([pid, before[0]])
        root = proc_root / str(pid)
        tasks = sorted(p.name for p in (root / 'task').iterdir())
        require(len(tasks) <= 4096, 'task bound')
        is_kernel = bool(before[1] & 0x200000)
        if before[2] not in ('Z', 'X', 'x') and not is_kernel:
            # Every task may have its own fs/files namespace.
            for tid in tasks:
                task = root / 'task' / tid
                for name in ('cwd', 'root', 'exe'):
                    target = os.readlink(task / name)
                    require(not related(strip_deleted(target), PARENTS), 'process path consumer')
                # Stream the live scandir iterator so its one enumeration FD
                # remains open while checked. Never skip inherited scanner FDs.
                fd_dir = task / 'fd'
                fd_dir_stat = os.stat(fd_dir)
                transient = 0
                count = 0
                if pid == os.getpid():
                    require(len(tasks) == 1, 'scanner unexpectedly multithreaded')
                    require(all(fd > 2 for fd in self_fds), 'held exemption overlaps standard descriptors')
                with os.scandir(fd_dir) as entries:
                    for entry in entries:
                        count += 1
                        require(count <= 65536 and entry.name.isdigit(), 'FD bound or shape')
                        number = int(entry.name)
                        f = fd_dir / entry.name
                        target = os.readlink(f)
                        fs = os.stat(f)
                        if pid == os.getpid() and number in self_fds:
                            # Exactly descriptors supplied by Held's live opens.
                            require(meta(os.fstat(number)) == meta(fs), 'held exemption raced')
                            continue
                        is_enumerator = (pid == os.getpid() and stat.S_ISDIR(fs.st_mode)
                                         and (fs.st_dev, fs.st_ino) == (fd_dir_stat.st_dev, fd_dir_stat.st_ino)
                                         and target == '/proc/%s/task/%s/fd' % (pid, tid))
                        if is_enumerator:
                            # One live scandir FD only. An inherited duplicate
                            # of this directory creates a second and refuses.
                            transient += 1
                            require(transient == 1, 'extra self enumeration descriptor')
                            continue
                        require((fs.st_dev, fs.st_ino) not in inode_targets and not related(strip_deleted(target), PARENTS), 'open descriptor consumer')
                if pid == os.getpid():
                    require(transient == 1, 'self enumeration descriptor not accounted')
            for line in (root / 'maps').read_text().splitlines():
                fields = line.split(None, 5)
                require(len(fields) >= 5, 'maps parse')
                major, minor = (int(n, 16) for n in fields[3].split(':'))
                require((os.makedev(major, minor), int(fields[4])) not in inode_targets, 'mapped target consumer')
                if len(fields) == 6:
                    require(not related(strip_deleted(fields[5]), PARENTS), 'mapped path consumer')
            # Namespace mount roots expose ancestry even if mountpoint is elsewhere.
            for line in (root / 'mountinfo').read_text().splitlines():
                f = line.split()
                require(len(f) >= 10 and '-' in f, 'mountinfo parse')
                source_root, target = decode_mount(f[3]), decode_mount(f[4])
                # The ordinary scratch filesystem mount itself is expected.
                if f[2] == '7:36' and not (source_root == '/' and target == str(ROOT)):
                    source = str(ROOT) if source_root == '/' else str(ROOT) + source_root
                    require(not exposes(source, PARENTS), 'namespace bind source')
                require(not any(target == p or target.startswith(p + '/') for p in PARENTS), 'candidate child mount')
        require(proc_identity(pid) == before, 'process identity changed')
        require(sorted(p.name for p in (root / 'task').iterdir()) == tasks, 'task set raced')
    require(sorted(int(p.name) for p in proc_root.iterdir() if p.name.isdigit()) == pids, 'PID set raced')
    return identities


class Held:
    def __init__(self, rows):
        self.rows, self.parents, self.targets, self.chains = rows, {}, {}, {}
        try:
            for name in sorted(PARENTS | {str(REPO / 'docs/verification/evidence')}):
                self.parents[name], self.chains[name] = safe_directory(name)
            for r in rows:
                path = Path(r['candidate'])
                self.targets[str(path)] = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.parents[str(path.parent)])
            self.check_all()
        except BaseException:
            self.close()
            raise

    def check(self, r):
        p = Path(r['candidate'])
        require(meta(os.fstat(self.targets[str(p)])) == r['candidate_metadata'], 'held candidate drift')
        require(meta(os.stat(p.name, dir_fd=self.parents[str(p.parent)], follow_symlinks=False)) == r['candidate_metadata'], 'candidate name drift')
        retained = Path(r['retained_repo_path'])
        require(meta(os.stat(retained.name, dir_fd=self.parents[str(retained.parent)], follow_symlinks=False)) == r['retained_metadata'], 'retained metadata drift')

    def ancestry(self):
        for name, expected in self.chains.items():
            fd, chain = safe_directory(name)
            try:
                require(chain == expected and (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == tuple(expected[-1]), 'parent ancestry drift')
                require((os.fstat(self.parents[name]).st_dev, os.fstat(self.parents[name]).st_ino) == tuple(expected[-1]), 'held parent drift')
            finally:
                os.close(fd)

    def check_all(self):
        self.ancestry()
        for r in self.rows:
            self.check(r)

    def census_input(self):
        return dict(rows=self.rows, target_fds=list(self.targets.values()), parent_fds=list(self.parents.values()))

    def close(self):
        for fd in list(self.targets.values()) + list(self.parents.values()):
            os.close(fd)
        self.targets, self.parents = {}, {}


def unmatched(m):
    # Exact direct-parent inventory only; no recursion/broad source scan.
    return {p: {name: meta(os.lstat(Path(p) / name)) for name in sorted(os.listdir(p))
                 if str(Path(p) / name) not in {r['candidate'] for r in m['rows']}} for p in sorted(PARENTS)}


def snapshot(m, h, lockfd):
    require((os.fstat(lockfd).st_dev, os.fstat(lockfd).st_ino) == LOCK_ID, 'root mutex fd')
    require((os.lstat(LOCK).st_dev, os.lstat(LOCK).st_ino) == LOCK_ID, 'root mutex name')
    h.check_all()
    return dict(mount=mount_identity(), records=records(), containers=container_census(),
                processes=process_census(h.census_input()), git=git_available(m['rows']),
                parents={k: v for k, v in h.chains.items()}, unmatched=unmatched(m))


def record(stream, event):
    stream.write(json.dumps(event, sort_keys=True) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('SOURCE_ONLY', 'observe', 'execute'), default='SOURCE_ONLY')
    parser.add_argument('--release')
    args = parser.parse_args()
    m = pinned()
    source_sha = digest(raw_small(Path(__file__).resolve()))
    if args.mode == 'SOURCE_ONLY':
        print(json.dumps({'status': 'SOURCE_ONLY', 'source_sha256': source_sha, 'manifest_sha256': PIN, 'count': 120, 'missing': ['independent release', 'fresh root observation', 'real executor identity', 'root consumer attestation', 'CPU7 fixture permission/results']}))
        return
    require(os.geteuid() == 0 and args.release, 'root and explicit release required')
    release_raw = raw_small(args.release)
    release = json.loads(release_raw)
    require(release['source_sha256'] == source_sha and release['manifest_sha256'] == PIN, 'release source/input pins')
    require(release['status'] == ('OBSERVATION_RELEASE' if args.mode == 'observe' else 'EXECUTION_RELEASE'), 'release mode')
    require(all(release['attestations'].get(k) is True for k in ATTEST), 'campaign owner attestations')
    require(release['independent_review']['status'] == 'PASS' and len(release['independent_review']['sha256']) == 64, 'independent review required')
    identity = proc_identity(os.getpid())[0]
    require(proc_identity(release['coordinator_identity'][0])[0] == release['coordinator_identity'][1], 'coordinator identity')
    require(release['boot_id'] == BOOT and time.time() <= release['expires_unix'] <= time.time() + 600, 'release freshness')
    lockfd = os.open(LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    h = None
    try:
        require((os.fstat(lockfd).st_dev, os.fstat(lockfd).st_ino) == LOCK_ID, 'persistent root mutex27:4')
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        h = Held(m['rows'])
        observation = snapshot(m, h, lockfd)
        cap = capacity()
        for label, floor in [('host', 16 << 30), ('scratch', 12 << 30)]:
            reserve = release['minimum_available_bytes'][label]
            require(reserve >= floor and cap[label]['available_bytes'] >= reserve, 'resource floor/reserve')
        if args.mode == 'execute':
            require(observation['records'] == release['expected_records'], 'current lease/exclusion mismatch')
        if args.mode == 'observe':
            print(json.dumps({'status': 'OBSERVED_NO_EFFECT', 'observed_unix': time.time(), 'executor': [os.getpid(), identity, BOOT], 'observation': observation, 'capacity': cap}, sort_keys=True))
            return
        require(raw_small(args.release) == release_raw, 'release changed')
        # Process IDs are required complete fresh census evidence, not equality
        # with the previous observer PID. All other bindings must match exactly.
        previous = release['observation']
        require(0 <= time.time() - release['observed_unix'] <= 120, 'stale observation')
        require({k: v for k, v in observation.items() if k != 'processes'} == {k: v for k, v in previous.items() if k != 'processes'}, 'fresh observation drift')
        journal = Path(release['journal'])
        require(journal.parent == BASE and journal.name.startswith('actual-') and journal.suffix == '.jsonl', 'new private journal path')
        jdir, _ = safe_directory(BASE)
        try:
            jfd = os.open(journal.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=jdir)
            os.fsync(jdir)
        finally:
            os.close(jdir)
        removed = []
        current_path = None
        with os.fdopen(jfd, 'w') as stream:
            record(stream, {'status': 'PREFLIGHT_PASS', 'executor': [os.getpid(), identity, BOOT], 'source_sha256': source_sha, 'manifest_sha256': PIN, 'release_sha256': digest(release_raw), 'observation': observation, 'before_capacity': cap})
            try:
                for r in m['rows']:
                    current_path = r['candidate']
                    h.ancestry()
                    h.check(r)
                    require(records() == observation['records'], 'ownership/exclusion drift')
                    require(mount_identity() == observation['mount'], 'mount drift')
                    p = Path(r['candidate'])
                    record(stream, {'status': 'UNLINK_INTENT', 'path': str(p), 'metadata': r['candidate_metadata']})
                    os.unlink(p.name, dir_fd=h.parents[str(p.parent)])
                    removed.append(str(p))
                    os.fsync(h.parents[str(p.parent)])
                    fd = h.targets.pop(str(p))
                    os.close(fd)
                    record(stream, {'status': 'REMOVED', 'path': str(p)})
                    current_path = None
                require(unmatched(m) == observation['unmatched'], 'unmatched preservation drift')
                for r in m['rows']:
                    require(not os.path.lexists(r['candidate']), 'removed name reappeared')
                    require(meta(os.lstat(r['retained_repo_path'])) == r['retained_metadata'], 'retained postflight drift')
                git_available(m['rows'])
                record(stream, {'status': 'COMPLETE', 'removed': removed, 'allocated_bytes': sum(r['candidate_metadata']['allocated_bytes'] for r in m['rows']), 'after_capacity': capacity(), 'host_reclaim_claimed': False, 'trim': False})
            except BaseException as exc:
                record(stream, {'status': 'STOP_PARTIAL', 'error': repr(exc), 'removed': removed, 'failed_or_uncertain_path': current_path, 'not_attempted': [r['candidate'] for r in m['rows'] if r['candidate'] not in removed and r['candidate'] != current_path], 'removed_allocated_bytes': sum(r['candidate_metadata']['allocated_bytes'] for r in m['rows'] if r['candidate'] in removed), 'after_capacity': capacity()})
                raise
    finally:
        if h is not None:
            h.close()
        os.close(lockfd)  # flock released; persistent mutex never unlinked


if __name__ == '__main__':
    main()
