#!/usr/bin/env python3
"""Root-only, read-only structured observer for the exact cleanup roots.

The caller is responsible for non-root admission.  After quarantine, root
adversaries are outside this helper's threat model; sealing prevents new
non-root opens while this observer scans.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ORIGINAL = (Path('/dev/shm/mckernel-exact-candidate-68cf089a-1'),
            Path('/dev/shm/mckernel-exact-metadata-backup-68cf089a-1'))
QUARANTINE = (Path('/dev/shm/.mckernel-quarantine-mckernel-exact-candidate-68cf089a-1'),
              Path('/dev/shm/.mckernel-quarantine-mckernel-exact-metadata-backup-68cf089a-1'))
SCHEMA = 'mckernel.read-only-live-reference-snapshot.v6'
MAX_ROUNDS = 5
MAX_TREE_ATTEMPTS = 3
PROGRESS = {'roots': [], 'rounds': [], 'tree_observation_transients': []}


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def unescape(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match.group(1), 8)), value)


def starttime(path):
    text = path.read_text(encoding='ascii')
    close = text.rfind(')')
    tail = text[close + 2:].split()
    if close < 0 or len(tail) < 20:
        raise RuntimeError('malformed proc stat: ' + str(path))
    return tail[19]


def identity(pid, tid):
    try:
        return (pid, tid, starttime(Path('/proc') / str(pid) / 'task' / str(tid) / 'stat'))
    except FileNotFoundError:
        return None


def mount_rows(pid, tid):
    rows = []
    for line in (Path('/proc') / str(pid) / 'task' / str(tid) / 'mountinfo').read_text(encoding='utf-8').splitlines():
        left, marker, right = line.partition(' - ')
        fields, tail = left.split(), right.split()
        if not marker or len(fields) < 6 or len(tail) < 3 or ':' not in fields[2]:
            raise RuntimeError('malformed mountinfo for %d/%d' % (pid, tid))
        rows.append({'mount_id': fields[0], 'parent_id': fields[1], 'device': fields[2],
                     'root': unescape(fields[3]), 'mountpoint': unescape(fields[4]), 'options': fields[5],
                     'optional_fields': fields[6:], 'filesystem': tail[0], 'source': tail[1],
                     'super_options': tail[2:]})
    return rows


def below(value, parent):
    value, parent = value.rstrip('/') or '/', parent.rstrip('/') or '/'
    return parent == '/' or value == parent or value.startswith(parent + '/')


def coordinate(path, rows):
    info = path.lstat()
    device = '%d:%d' % (os.major(info.st_dev), os.minor(info.st_dev))
    choices = [row for row in rows if row['device'] == device and below(str(path), row['mountpoint'])]
    if not choices:
        raise RuntimeError('cannot map target coordinate: ' + str(path))
    row = max(choices, key=lambda item: len(item['mountpoint']))
    relative = os.path.relpath(str(path), row['mountpoint'])
    root = PurePosixPath(row['root'])
    return device, '/' + str(root if relative == '.' else root.joinpath(*Path(relative).parts)).lstrip('/'), row


def open_tree(path):
    """Keep root scan descriptors open so self-FD handling is explicit."""
    transients = []
    for attempt in range(1, MAX_TREE_ATTEMPTS + 1):
        rootfd = None
        opened = set()
        try:
            initial = path.lstat()
            if not stat.S_ISDIR(initial.st_mode) or stat.S_ISLNK(initial.st_mode):
                raise RuntimeError('target is not ordinary directory: ' + str(path))
            rootfd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            opened.add(rootfd)
            if (os.fstat(rootfd).st_dev, os.fstat(rootfd).st_ino) != (initial.st_dev, initial.st_ino):
                raise FileNotFoundError('target replaced while opened')
            found, stack = {(initial.st_dev, initial.st_ino)}, [(rootfd, initial.st_dev)]
            while stack:
                fd, device = stack.pop()
                scanfd = os.dup(fd)
                try:
                    with os.scandir(scanfd) as entries:
                        for entry in entries:
                            info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                            if info.st_dev != device or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
                                raise RuntimeError('unsupported inode/mount in target tree: ' + entry.name)
                            found.add((info.st_dev, info.st_ino))
                            if stat.S_ISDIR(info.st_mode):
                                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                                opened.add(child)
                                stack.append((child, device))
                finally:
                    os.close(scanfd)
                    if fd != rootfd:
                        os.close(fd)
                        opened.discard(fd)
            final = path.lstat()
            if (initial.st_dev, initial.st_ino, initial.st_mode) != (final.st_dev, final.st_ino, final.st_mode):
                raise FileNotFoundError('target changed while observed')
            return initial, found, rootfd, transients
        except BaseException as error:
            for fd in list(opened):
                try:
                    os.close(fd)
                except OSError:
                    pass
            if not isinstance(error, FileNotFoundError):
                raise
            transients.append({'path': str(path), 'attempt': attempt, 'resolution': 'retry'})
    raise RuntimeError('target tree observation did not settle: ' + str(path))


def canonical(rows, targets):
    found = [row for row in rows if row['mountpoint'] == '/dev/shm' and row['root'] == '/' and
             row['filesystem'] == 'tmpfs' and any(row['device'] == target['device'] for target in targets)]
    if len(found) != 1:
        raise RuntimeError('expected exactly one canonical /dev/shm tmpfs mount')
    return found[0]


def is_canonical(row, reference):
    return (row['device'], row['root'], row['mountpoint'], row['filesystem']) == (
        reference['device'], '/', '/dev/shm', 'tmpfs')


def mount_bad(rows, targets, reference):
    result = []
    for row in rows:
        for target in targets:
            if below(row['mountpoint'], target['path']):
                result.append({'kind': 'mountpoint-on-or-below-target', 'target': target['path'], 'mount': row})
            if row['device'] == target['device'] and (below(row['root'], target['filesystem_root']) or
                                                       below(target['filesystem_root'], row['root'])) and not is_canonical(row, reference):
                result.append({'kind': 'tmpfs-target-alias-or-bind', 'target': target['path'], 'mount': row})
    return result


def task_set():
    result = set()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            tasks = list((proc / 'task').iterdir())
        except FileNotFoundError:
            continue
        for task in tasks:
            if task.name.isdigit():
                value = identity(int(proc.name), int(task.name))
                if value is not None:
                    result.add(value)
    return result


def parse_targets(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', action='append', required=True)
    values = tuple(Path(value) for value in parser.parse_args(argv).target)
    if len(values) != 2 or values not in (ORIGINAL, QUARANTINE):
        raise RuntimeError('only the exact ordered original or quarantine target pair is accepted')
    return values


def source_hash():
    with open(__file__, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def self_fd_reference_allowed(who, label, observer_pid, allowed_fds):
    """Only our held directory-scan descriptors may self-reference a target."""
    return (who[0] == observer_pid and label.startswith('fd/') and
            label.split('/', 1)[1].isdigit() and int(label.split('/', 1)[1]) in allowed_fds)


def emit_progress(kind, value):
    print(json.dumps({'schema': SCHEMA + '.progress', 'kind': kind, 'value': value},
                     sort_keys=True, separators=(',', ':')), file=sys.stderr, flush=True)


def failure_record(error):
    return {'schema': SCHEMA, 'status': 'FAIL', 'failure': repr(error), 'observer_sha256': source_hash(),
            'started_at_utc': utcnow(), 'ended_at_utc': utcnow(), 'roots': [], 'rounds': [],
            'permission_denials': [], 'target_references': [], 'unresolved_churn': [], 'mount_proofs': [],
            **PROGRESS}


def observe(target_paths):
    started, own_pid = utcnow(), os.getpid()
    own_start = starttime(Path('/proc') / str(own_pid) / 'stat')
    self_rows, open_fds = mount_rows(own_pid, own_pid), []
    targets, inode_ids, transients = [], set(), []
    try:
        PROGRESS.update({'roots': [], 'rounds': [], 'tree_observation_transients': []})
        for path in target_paths:
            info, members, fd, retries = open_tree(path)
            device, root, row = coordinate(path, self_rows)
            open_fds.append(fd)
            inode_ids.update(members)
            transients.extend(retries)
            targets.append({'path': str(path), 'device_number': info.st_dev, 'device': device, 'filesystem_root': root,
                            'inode': info.st_ino, 'mode': format(stat.S_IMODE(info.st_mode), '04o'),
                            'tree_inode_count': len(members), 'observer_mount': row})
        PROGRESS.update({'roots': targets, 'tree_observation_transients': transients})
        emit_progress('roots', targets)
        reference = canonical(self_rows, targets)
        allowed_self_fds = set(open_fds)
        rounds, all_reconciled, all_expected_absences, prior, pass_streak = [], [], [], None, 0
        for number in range(1, MAX_ROUNDS + 1):
            current = task_set()
            refs, denials, churn, proofs, expected_absences = [], [], [], [], []
            counts = {key: 0 for key in ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}

            def gone(who, field):
                value = identity(who[0], who[1])
                if value is None or value != who:
                    all_reconciled.append({'identity': who, 'field': field,
                                           'resolution': 'exited' if value is None else 'reused'})
                elif field == 'exe':
                    expected_absences.append({'identity': who, 'field': 'exe', 'reason': 'kernel-thread-no-exe'})
                else:
                    churn.append({'identity': who, 'field': field, 'resolution': 'still-live'})

            def probe(who, path, label):
                try:
                    info = path.stat()
                    counts[label.split('/', 1)[0]] += 1
                    if (info.st_dev, info.st_ino) in inode_ids:
                        # Our explicitly held tree directory descriptors are
                        # expected self-observation artifacts and nothing else.
                        if not self_fd_reference_allowed(who, label, own_pid, allowed_self_fds):
                            refs.append({'identity': who, 'field': label, 'link': os.readlink(path)})
                except FileNotFoundError:
                    gone(who, label)
                except PermissionError:
                    denials.append({'identity': who, 'field': label})

            for who in sorted(current):
                pid, tid, _ = who
                base = Path('/proc') / str(pid) / 'task' / str(tid)
                if identity(pid, tid) != who:
                    gone(who, 'pre-scan')
                    continue
                for field in ('cwd', 'root', 'exe'):
                    probe(who, base / field, field)
                for directory in ('fd', 'map_files'):
                    try:
                        with os.scandir(base / directory) as iterator:
                            for child in iterator:
                                probe(who, Path(child.path), directory + '/' + child.name)
                    except FileNotFoundError:
                        gone(who, directory)
                        continue
                    except PermissionError:
                        denials.append({'identity': who, 'field': directory})
                        continue
                try:
                    namespace = os.readlink(base / 'ns/mnt')
                    rows = mount_rows(pid, tid)
                    counts['ns/mnt'] += 1
                    counts['mountinfo'] += len(rows)
                except FileNotFoundError:
                    gone(who, 'ns-or-mountinfo')
                    continue
                except PermissionError:
                    denials.append({'identity': who, 'field': 'ns-or-mountinfo'})
                    continue
                ids = [row['mount_id'] for row in rows if is_canonical(row, reference)]
                violations = mount_bad(rows, targets, reference)
                if len(ids) != 1:
                    violations.append({'kind': 'missing-or-ambiguous-canonical-dev-shm', 'mount_ids': ids})
                refs.extend({'identity': who, 'field': 'mount-violation', 'detail': value} for value in violations)
                proofs.append({'identity': who, 'namespace': namespace, 'mount_ids': [row['mount_id'] for row in rows],
                               'canonical_mount_id': ids[0] if len(ids) == 1 else None})
                if identity(pid, tid) != who:
                    gone(who, 'post-scan')
            complete_proofs = {tuple(proof['identity']) for proof in proofs} == current
            clean = not refs and not denials and not churn and complete_proofs
            if prior is not None and current == prior and clean:
                pass_streak += 1
            else:
                pass_streak = 0
            rounds.append({'round': number, 'task_identities': len(current), 'rescanned_identities': len(current),
                           'identities': [list(item) for item in sorted(current)], 'field_counts': counts,
                           'permission_denials': denials, 'target_references': refs, 'unresolved_churn': churn,
                           'mount_proofs': proofs, 'complete_mount_proofs': complete_proofs,
                           'expected_absences': expected_absences, 'clean': clean})
            PROGRESS['rounds'] = rounds
            emit_progress('round', rounds[-1])
            all_expected_absences.extend(expected_absences)
            if pass_streak >= 2:
                break
            prior = current
        status = 'PASS' if pass_streak >= 2 else 'FAIL'
        return {'schema': SCHEMA, 'status': status, 'observer_sha256': source_hash(),
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'observer_pid': own_pid,
                'observer_starttime': own_start, 'started_at_utc': started, 'ended_at_utc': utcnow(),
                'scan_complete': status == 'PASS', 'roots': targets, 'rounds': rounds,
                'tasks_scanned': sum(round_['rescanned_identities'] for round_ in rounds),
                'tree_observation_transients': transients, 'reconciled_exits_or_reuse': all_reconciled,
                'expected_absences': all_expected_absences, 'allowed_self_scan_fds': sorted(allowed_self_fds),
                'failure': None if status == 'PASS' else 'two consecutive clean, complete stable rounds not obtained',
                'canonical_dev_shm': reference}
    finally:
        for fd in open_fds:
            os.close(fd)


def main(argv=None):
    output = failure_record(RuntimeError('uninitialized'))
    try:
        if os.geteuid() != 0:
            raise RuntimeError('observer requires root')
        output = observe(parse_targets(argv))
    except BaseException as error:
        output = failure_record(error)
    print(json.dumps(output, sort_keys=True, separators=(',', ':')))
    return 0 if output.get('status') == 'PASS' else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        assert self_fd_reference_allowed((8, 8, '1'), 'fd/9', 8, {9})
        assert not self_fd_reference_allowed((8, 8, '1'), 'fd/x', 8, {9})
        assert failure_record(RuntimeError('synthetic'))['status'] == 'FAIL'
        print('observer pure synthetic assertions passed')
    else:
        sys.exit(main())
