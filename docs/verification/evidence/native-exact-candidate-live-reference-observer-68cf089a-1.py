#!/usr/bin/env python3
"""Root-only, read-only and fail-closed reference snapshot for two tmpfs roots.

This is deliberately a snapshot producer, not a deletion helper. A successful
record means every task identity visible in two consecutive enumerations was
scanned completely, with no permissions or identity churn left unresolved.
"""
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

TARGETS = (Path('/dev/shm/mckernel-exact-candidate-68cf089a-1'),
           Path('/dev/shm/mckernel-exact-metadata-backup-68cf089a-1'))
SCHEMA = 'mckernel.read-only-live-reference-snapshot.v4'
MAX_ROUNDS = 4


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def unescape(value):
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), value)


def proc_starttime(stat_path):
    """Return field 22 without being confused by ')' inside comm."""
    text = stat_path.read_text(encoding='ascii')
    close = text.rfind(')')
    if close < 0:
        raise RuntimeError('malformed proc stat: ' + str(stat_path))
    tail = text[close + 2:].split()
    if len(tail) < 20:
        raise RuntimeError('short proc stat: ' + str(stat_path))
    return tail[19]


def task_identity(pid, tid):
    try:
        return (pid, tid, proc_starttime(Path('/proc') / str(pid) / 'task' / str(tid) / 'stat'))
    except FileNotFoundError:
        return None


def mount_rows(pid, tid):
    path = Path('/proc') / str(pid) / 'task' / str(tid) / 'mountinfo'
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        left, sep, right = line.partition(' - ')
        fields, rfields = left.split(), right.split()
        if not sep or len(fields) < 6 or len(rfields) < 3 or ':' not in fields[2]:
            raise RuntimeError('malformed mountinfo for %d/%d' % (pid, tid))
        rows.append({'mount_id': fields[0], 'parent_id': fields[1], 'device': fields[2],
                     'root': unescape(fields[3]), 'mountpoint': unescape(fields[4]),
                     'options': fields[5], 'optional_fields': fields[6:],
                     'filesystem': rfields[0], 'source': rfields[1],
                     'super_options': rfields[2:]})
    return rows


def is_below(value, parent):
    value = value.rstrip('/') or '/'
    parent = parent.rstrip('/') or '/'
    return parent == '/' or value == parent or value.startswith(parent + '/')


def coordinate(path, rows):
    info = path.lstat()
    device = '%d:%d' % (os.major(info.st_dev), os.minor(info.st_dev))
    choices = [row for row in rows if row['device'] == device and is_below(str(path), row['mountpoint'])]
    if not choices:
        raise RuntimeError('cannot map target filesystem coordinate: ' + str(path))
    row = max(choices, key=lambda candidate: len(candidate['mountpoint']))
    relative = os.path.relpath(str(path), row['mountpoint'])
    root = PurePosixPath(row['root'])
    return device, '/' + str(root if relative == '.' else root.joinpath(*Path(relative).parts)).lstrip('/'), row


def tree(path):
    found, stack = set(), [path]
    while stack:
        item = stack.pop()
        info = item.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            raise RuntimeError('unsupported target inode type: ' + str(item))
        found.add((info.st_dev, info.st_ino))
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(item) as entries:
                stack.extend(Path(entry.path) for entry in entries)
    return found


def canonical_dev_shm(rows, target_rows):
    """The only mount permitted to expose either target is canonical /dev/shm."""
    allowed = []
    for row in rows:
        if (row['mountpoint'] == '/dev/shm' and row['root'] == '/' and row['filesystem'] == 'tmpfs' and
                any(row['device'] == target['device'] for target in target_rows)):
            allowed.append(row)
    if len(allowed) != 1:
        raise RuntimeError('expected exactly one canonical /dev/shm tmpfs mount')
    return allowed[0]


def same_canonical_dev_shm(row, canonical):
    """Mount IDs are recorded, but are namespace-local and cannot be equal."""
    return (row['device'] == canonical['device'] and row['root'] == '/' and
            row['mountpoint'] == '/dev/shm' and row['filesystem'] == 'tmpfs')


def mount_violations(rows, targets, canonical):
    violations = []
    for row in rows:
        for target in targets:
            path, device, root = target['path'], target['device'], target['filesystem_root']
            # Any nested/covering mount in the visible pathname is disallowed,
            # including one from a foreign filesystem.
            if is_below(row['mountpoint'], path):
                violations.append({'kind': 'mountpoint-on-or-below-target', 'target': path, 'mount': row})
            if row['device'] != device:
                continue
            # A source below target is a direct/foreign alias; an ancestor
            # source can expose it elsewhere. Only canonical /dev/shm is safe.
            if (is_below(row['root'], root) or is_below(root, row['root'])) and not same_canonical_dev_shm(row, canonical):
                violations.append({'kind': 'tmpfs-target-alias-or-bind', 'target': path, 'mount': row})
    return violations


def snapshot_tasks():
    identities = set()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        pid = int(proc.name)
        try:
            tids = list((proc / 'task').iterdir())
        except FileNotFoundError:
            continue
        for task in tids:
            if task.name.isdigit():
                identity = task_identity(pid, int(task.name))
                if identity is not None:
                    identities.add(identity)
    return identities


def main():
    if os.geteuid() != 0:
        raise RuntimeError('observer requires root')
    started = utcnow()
    own_pid = os.getpid()
    own_start = proc_starttime(Path('/proc') / str(own_pid) / 'stat')
    self_rows = mount_rows(own_pid, own_pid)
    targets, inode_ids = [], set()
    for target_path in TARGETS:
        info = target_path.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise RuntimeError('target is not an ordinary directory: ' + str(target_path))
        device, root, row = coordinate(target_path, self_rows)
        members = tree(target_path)
        inode_ids.update(members)
        targets.append({'path': str(target_path), 'device_number': info.st_dev, 'device': device,
                        'filesystem_root': root, 'inode': info.st_ino,
                        'mode': format(stat.S_IMODE(info.st_mode), '04o'),
                        'tree_inode_count': len(members), 'observer_mount': row})
    canonical = canonical_dev_shm(self_rows, targets)
    references, denials, unresolved, exits, mount_proofs = [], [], [], [], []
    field_counts = {name: 0 for name in ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}
    covered, prior = set(), None

    def vanished(identity, field):
        current = task_identity(identity[0], identity[1])
        if current is None or current != identity:
            exits.append({'identity': identity, 'field': field,
                          'resolution': 'exited' if current is None else 'reused'})
            return True
        unresolved.append({'identity': identity, 'field': field, 'resolution': 'still-live'})
        return False

    def probe(identity, path, label):
        try:
            info = path.stat()
            field_counts[label.split('/', 1)[0]] += 1
            if (info.st_dev, info.st_ino) in inode_ids:
                references.append({'identity': identity, 'field': label, 'link': os.readlink(path)})
        except FileNotFoundError:
            vanished(identity, label)
        except PermissionError:
            denials.append({'identity': identity, 'field': label})

    def scan(identity):
        pid, tid, _start = identity
        base = Path('/proc') / str(pid) / 'task' / str(tid)
        for name in ('cwd', 'root', 'exe'):
            probe(identity, base / name, name)
        for directory in ('fd', 'map_files'):
            try:
                children = list((base / directory).iterdir())
            except FileNotFoundError:
                vanished(identity, directory)
                continue
            except PermissionError:
                denials.append({'identity': identity, 'field': directory})
                continue
            for child in children:
                probe(identity, child, directory + '/' + child.name)
        try:
            ns = os.readlink(base / 'ns/mnt')
            field_counts['ns/mnt'] += 1
        except FileNotFoundError:
            vanished(identity, 'ns/mnt')
            return
        except PermissionError:
            denials.append({'identity': identity, 'field': 'ns/mnt'})
            return
        try:
            rows = mount_rows(pid, tid)
            field_counts['mountinfo'] += len(rows)
        except FileNotFoundError:
            vanished(identity, 'mountinfo')
            return
        except PermissionError:
            denials.append({'identity': identity, 'field': 'mountinfo'})
            return
        bad = mount_violations(rows, targets, canonical)
        canonical_ids = [row['mount_id'] for row in rows if same_canonical_dev_shm(row, canonical)]
        if len(canonical_ids) != 1:
            references.append({'identity': identity, 'field': 'mount-violation',
                               'detail': {'kind': 'missing-or-ambiguous-canonical-dev-shm',
                                          'mount_ids': canonical_ids}})
        if bad:
            references.extend({'identity': identity, 'field': 'mount-violation', 'detail': item} for item in bad)
        mount_proofs.append({'identity': identity, 'namespace': ns,
                             'mount_ids': [row['mount_id'] for row in rows],
                             'canonical_mount_id': canonical_ids[0] if len(canonical_ids) == 1 else None})

    rounds = []
    for number in range(1, MAX_ROUNDS + 1):
        current = snapshot_tasks()
        for identity in sorted(current - covered):
            scan(identity)
            covered.add(identity)
        rounds.append({'round': number, 'task_identities': len(current),
                       'new_identities': len(current - (prior or set()))})
        if prior is not None and current == prior and not unresolved:
            break
        prior = current
    else:
        unresolved.append({'field': 'enumeration', 'resolution': 'did-not-converge'})
    if proc_starttime(Path('/proc') / str(own_pid) / 'stat') != own_start:
        unresolved.append({'field': 'observer', 'resolution': 'identity-changed'})
    if denials or references or unresolved:
        raise RuntimeError('incomplete live-reference scan: denials=%d refs=%d unresolved=%d' %
                           (len(denials), len(references), len(unresolved)))
    with open(__file__, 'rb') as source:
        observer_sha = hashlib.sha256(source.read()).hexdigest()
    output = {'schema': SCHEMA, 'observer_sha256': observer_sha,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'observer_pid': own_pid, 'observer_starttime': own_start,
              'started_at_utc': started, 'ended_at_utc': utcnow(), 'rounds': rounds,
              'scan_complete': True, 'roots': targets, 'tasks_scanned': len(covered),
              'field_counts': field_counts, 'mount_namespace_task_proofs': mount_proofs,
              'permission_denials': [], 'target_references': [], 'unresolved_churn': [],
              'reconciled_exits_or_reuse': exits, 'canonical_dev_shm': canonical}
    print(json.dumps(output, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
