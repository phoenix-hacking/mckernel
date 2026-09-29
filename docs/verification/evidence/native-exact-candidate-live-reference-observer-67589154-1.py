#!/usr/bin/env python3
"""Root-only read-only observer for the two exact retirement cleanup roots.

V2 deliberately does not require a globally unchanged /proc task census.  A
task which has exited cannot retain an fd, mapping, cwd, root, or executable
reference, so an exact (pid, tid, starttime) identity which disappears is a
safe reconciliation.  In contrast, an identity which is replaced while being
scanned, a target reference, a denial, or an incomplete mount proof rejects a
round.  Each round takes bounded closure snapshots until every identity in its
final returned census has a successful scan bound to that identity.  Two
closure-clean rounds are required.

This is an observation-interval result, not an atomic global census: the
root-owned mode-0700 quarantines must prevent new non-root pathname opens, and
the packet/operational contract must independently exclude adversarial reference
transfer/acquisition or a privileged mutator during observation.  Sequential
/proc enumeration cannot establish either of those facts.
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


ORIGINAL = (Path('/dev/shm/mckernel-exact-candidate-67589154-1'),
            Path('/dev/shm/mckernel-exact-metadata-backup-67589154-1'))
QUARANTINE = (Path('/dev/shm/.mckernel-retirement-candidate-67589154-1'),
              Path('/dev/shm/.mckernel-retirement-metadata-backup-67589154-1'))
SCHEMA = 'mckernel.read-only-live-reference-snapshot.v7'
MAX_ROUNDS = 5
MAX_TREE_ATTEMPTS = 3
MAX_CLOSURE_PASSES = 5
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
                who = identity(int(proc.name), int(task.name))
                if who is not None:
                    result.add(who)
    return result


def mount_rows(pid, tid):
    rows = []
    path = Path('/proc') / str(pid) / 'task' / str(tid) / 'mountinfo'
    for line in path.read_text(encoding='utf-8').splitlines():
        left, marker, right = line.partition(' - ')
        fields, tail = left.split(), right.split()
        if not marker or len(fields) < 6 or len(tail) < 3 or ':' not in fields[2]:
            raise RuntimeError('malformed mountinfo for %d/%d' % (pid, tid))
        rows.append({'mount_id': fields[0], 'parent_id': fields[1], 'device': fields[2],
                     'root': unescape(fields[3]), 'mountpoint': unescape(fields[4]),
                     'options': fields[5], 'optional_fields': fields[6:],
                     'filesystem': tail[0], 'source': tail[1], 'super_options': tail[2:]})
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


def node_identity(info):
    """The root/child identity fields which must remain unchanged."""
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid,
            stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode))


def membership_digest(members):
    text = ''.join(':'.join(str(value) for value in member) + '\n' for member in sorted(members))
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def open_tree(path, directory_opener=os.open):
    """Return stable tree inode identities and retain the root descriptor."""
    transients = []
    for attempt in range(1, MAX_TREE_ATTEMPTS + 1):
        rootfd, opened = None, set()
        try:
            initial = path.lstat()
            if not stat.S_ISDIR(initial.st_mode) or stat.S_ISLNK(initial.st_mode):
                raise RuntimeError('target is not ordinary directory: ' + str(path))
            rootfd = directory_opener(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            opened.add(rootfd)
            if node_identity(os.fstat(rootfd)) != node_identity(initial):
                raise FileNotFoundError('target replaced while opened')
            found, stack = {node_identity(initial)}, [(rootfd, initial.st_dev)]
            while stack:
                fd, device = stack.pop()
                scanfd = os.dup(fd)
                try:
                    with os.scandir(scanfd) as entries:
                        for entry in entries:
                            info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                            if info.st_dev != device or not (stat.S_ISDIR(info.st_mode) or
                                                              stat.S_ISREG(info.st_mode) or
                                                              stat.S_ISLNK(info.st_mode)):
                                raise RuntimeError('unsupported inode/mount in target tree: ' + entry.name)
                            found.add(node_identity(info))
                            if stat.S_ISDIR(info.st_mode):
                                child = directory_opener(entry.name, os.O_RDONLY | os.O_DIRECTORY |
                                                          os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                                opened.add(child)
                                if node_identity(os.fstat(child)) != node_identity(info):
                                    raise FileNotFoundError('child replaced while opened: ' + entry.name)
                                stack.append((child, device))
                finally:
                    os.close(scanfd)
                    if fd != rootfd:
                        os.close(fd)
                        opened.discard(fd)
            final = path.lstat()
            if node_identity(initial) != node_identity(final):
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


def tree_baseline(path, directory_opener=os.open):
    info, members, fd, transients = open_tree(path, directory_opener)
    try:
        return {'path': str(path), 'root_identity': node_identity(info), 'members': members,
                'member_count': len(members), 'membership_sha256': membership_digest(members),
                'observation_transients': transients}
    finally:
        os.close(fd)


def revalidate_tree(baseline):
    """Re-open and compare an exact root and its full member identity set."""
    try:
        observed = tree_baseline(Path(baseline['path']))
    except BaseException as error:
        return {'path': baseline['path'], 'kind': 'tree-revalidation-error', 'failure': repr(error)}
    if observed['root_identity'] != baseline['root_identity']:
        return {'path': baseline['path'], 'kind': 'tree-root-identity-changed',
                'expected': baseline['root_identity'], 'observed': observed['root_identity']}
    if observed['members'] != baseline['members']:
        return {'path': baseline['path'], 'kind': 'tree-membership-changed',
                'expected_sha256': baseline['membership_sha256'],
                'observed_sha256': observed['membership_sha256'],
                'expected_count': baseline['member_count'], 'observed_count': observed['member_count']}
    return None


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


def mount_proof(rows, targets, reference):
    """An isolated namespace is complete only when it proves no target alias."""
    ids = [row['mount_id'] for row in rows if is_canonical(row, reference)]
    violations = mount_bad(rows, targets, reference)
    if len(ids) > 1:
        violations.append({'kind': 'ambiguous-canonical-dev-shm', 'mount_ids': ids})
    return violations, ids[0] if len(ids) == 1 else None, len(ids) <= 1


def safe_proc_absence(field):
    return field == 'fd' or field.startswith('fd/') or field == 'map_files' or field.startswith('map_files/')


def self_fd_reference_allowed(who, label, observer_pid, allowed_fds):
    return (who[0] == observer_pid and label.startswith('fd/') and
            label.split('/', 1)[1].isdigit() and int(label.split('/', 1)[1]) in allowed_fds)


def source_hash():
    with open(__file__, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def emit_progress(kind, value):
    print(json.dumps({'schema': SCHEMA + '.progress', 'kind': kind, 'value': value},
                     sort_keys=True, separators=(',', ':')), file=sys.stderr, flush=True)


def identity_state(who, identity_reader=identity):
    current = identity_reader(who[0], who[1])
    if current == who:
        return 'same'
    return 'exited' if current is None else 'reused'


def scan_identity(who, targets, reference, inode_ids, own_pid, allowed_fds,
                  proc_root=Path('/proc'), identity_reader=identity, mount_reader=mount_rows,
                  stat_reader=None, link_reader=os.readlink):
    """Scan one identity once.  An exit is safe; replacement is not a scan."""
    result = {'identity': who, 'successful': False, 'state': None, 'references': [],
              'denials': [], 'incomplete': [], 'expected_absences': [], 'mount_proof': None,
              'field_counts': {key: 0 for key in ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}}

    def observed_state():
        state = identity_state(who, identity_reader)
        result['state'] = state
        return state

    if observed_state() != 'same':
        return result
    pid, tid, _ = who
    base = Path(proc_root) / str(pid) / 'task' / str(tid)

    def probe(path, label):
        try:
            info = (stat_reader or Path.stat)(path)
            result['field_counts'][label.split('/', 1)[0]] += 1
            if (info.st_dev, info.st_ino) in inode_ids and not self_fd_reference_allowed(
                    who, label, own_pid, allowed_fds):
                reference_record = {'identity': who, 'field': label, 'link': None}
                try:
                    reference_record['link'] = link_reader(path)
                except OSError as error:
                    reference_record['link_diagnostic_failure'] = repr(error)
                result['references'].append(reference_record)
            return True
        except FileNotFoundError:
            if observed_state() != 'same':
                return False
            if label == 'exe':
                result['expected_absences'].append({'identity': who, 'field': label,
                                                     'reason': 'kernel-thread-no-exe'})
            elif safe_proc_absence(label):
                result['expected_absences'].append({'identity': who, 'field': label,
                                                     'reason': 'per-entry-procfs-absence'})
            else:
                result['incomplete'].append({'identity': who, 'field': label,
                                             'resolution': 'still-live'})
            return True
        except PermissionError:
            result['denials'].append({'identity': who, 'field': label})
            return True

    for field in ('cwd', 'root', 'exe'):
        if not probe(base / field, field):
            return result
    for directory in ('fd', 'map_files'):
        try:
            with os.scandir(base / directory) as iterator:
                for child in iterator:
                    if not probe(Path(child.path), directory + '/' + child.name):
                        return result
        except FileNotFoundError:
            if observed_state() != 'same':
                return result
            if safe_proc_absence(directory):
                result['expected_absences'].append({'identity': who, 'field': directory,
                                                     'reason': 'per-entry-procfs-absence'})
            else:
                result['incomplete'].append({'identity': who, 'field': directory,
                                             'resolution': 'still-live'})
        except PermissionError:
            result['denials'].append({'identity': who, 'field': directory})
    try:
        namespace = link_reader(base / 'ns/mnt')
        rows = mount_reader(pid, tid)
        result['field_counts']['ns/mnt'] += 1
        result['field_counts']['mountinfo'] += len(rows)
    except FileNotFoundError:
        if observed_state() == 'same':
            result['incomplete'].append({'identity': who, 'field': 'ns-or-mountinfo',
                                         'resolution': 'still-live'})
        return result
    except PermissionError:
        result['denials'].append({'identity': who, 'field': 'ns-or-mountinfo'})
        return result
    violations, canonical_id, complete = mount_proof(rows, targets, reference)
    result['references'].extend({'identity': who, 'field': 'mount-violation', 'detail': value}
                                for value in violations)
    result['mount_proof'] = {'identity': who, 'namespace': namespace,
                             'mount_ids': [row['mount_id'] for row in rows],
                             'canonical_mount_id': canonical_id, 'complete': complete}
    if not complete:
        result['incomplete'].append({'identity': who, 'field': 'mount-proof',
                                     'resolution': 'incomplete'})
    state = observed_state()
    result['state'] = state
    if state == 'same' and not result['references'] and not result['denials'] and not result['incomplete']:
        result['successful'] = True
    return result


def closure_decision(final_live, successful, references, denials, incomplete, replacements, closure_passes):
    """Pure acceptance decision used by the synthetic regression suite."""
    missing = set(final_live) - set(successful)
    clean = not (missing or references or denials or incomplete or replacements)
    return {'clean': clean, 'missing_final': missing,
            'nonconvergent': bool(missing) and closure_passes >= MAX_CLOSURE_PASSES}


def closure_round(scanner, snapshot):
    """Pure bounded closure harness: scanner(identity) returns a scan result dict."""
    pending, successful, records = set(snapshot()), set(), []
    references, denials, incomplete, replacements = [], [], [], []
    final_live = set()
    for pass_number in range(1, MAX_CLOSURE_PASSES + 1):
        for who in sorted(pending):
            record = scanner(who)
            records.append(record)
            references.extend(record.get('references', []))
            denials.extend(record.get('denials', []))
            incomplete.extend(record.get('incomplete', []))
            if record.get('state') == 'reused':
                replacements.append({'identity': who, 'resolution': 'reused-during-scan'})
            if record.get('successful'):
                successful.add(who)
        final_live = set(snapshot())
        decision = closure_decision(final_live, successful, references, denials, incomplete,
                                    replacements, pass_number)
        if not decision['missing_final']:
            return {'closure_passes': pass_number, 'final_live': final_live, 'successful': successful,
                    'records': records, 'references': references, 'denials': denials,
                    'incomplete': incomplete, 'replacements': replacements, **decision}
        pending = decision['missing_final']
    return {'closure_passes': MAX_CLOSURE_PASSES, 'final_live': final_live, 'successful': successful,
            'records': records, 'references': references, 'denials': denials,
            'incomplete': incomplete, 'replacements': replacements,
            **closure_decision(final_live, successful, references, denials, incomplete,
                               replacements, MAX_CLOSURE_PASSES)}


def advance_streak(clean, streak):
    return streak + 1 if clean else 0


def failure_record(error):
    return {'schema': SCHEMA, 'status': 'FAIL', 'failure': repr(error), 'observer_sha256': source_hash(),
            'started_at_utc': utcnow(), 'ended_at_utc': utcnow(), 'roots': [], 'rounds': [],
            'permission_denials': [], 'target_references': [], 'unresolved_churn': [], 'mount_proofs': [],
            **PROGRESS}


def parse_targets(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', action='append', required=True)
    values = tuple(Path(value) for value in parser.parse_args(argv).target)
    if len(values) != 2 or values not in (ORIGINAL, QUARANTINE):
        raise RuntimeError('only the exact ordered original or quarantine target pair is accepted')
    return values


def observe(target_paths):
    started, own_pid = utcnow(), os.getpid()
    own_start = starttime(Path('/proc') / str(own_pid) / 'stat')
    self_rows, open_fds = mount_rows(own_pid, own_pid), []
    targets, trees, inode_ids, transients = [], [], set(), []
    try:
        PROGRESS.update({'roots': [], 'rounds': [], 'tree_observation_transients': []})
        for path in target_paths:
            info, members, fd, retries = open_tree(path)
            device, root, row = coordinate(path, self_rows)
            open_fds.append(fd)
            inode_ids.update((member[0], member[1]) for member in members)
            transients.extend(retries)
            tree = {'path': str(path), 'root_identity': node_identity(info), 'members': members,
                    'member_count': len(members), 'membership_sha256': membership_digest(members)}
            trees.append(tree)
            targets.append({'path': str(path), 'device_number': info.st_dev, 'device': device,
                            'uid': info.st_uid, 'gid': info.st_gid,
                            'filesystem_root': root, 'inode': info.st_ino,
                            'mode': format(stat.S_IMODE(info.st_mode), '04o'),
                            'tree_root_identity': tree['root_identity'],
                            'tree_member_identities': [list(member) for member in sorted(members)],
                            'tree_inode_count': len(members),
                            'tree_membership_sha256': tree['membership_sha256'], 'observer_mount': row})
        PROGRESS.update({'roots': targets, 'tree_observation_transients': transients})
        emit_progress('roots', targets)
        reference, allowed_self_fds = canonical(self_rows, targets), set(open_fds)
        rounds, reconciled, expected_absences, persistent_tree_failures, streak = [], [], [], [], 0
        for number in range(1, MAX_ROUNDS + 1):
            result = closure_round(lambda who: scan_identity(who, targets, reference, inode_ids,
                                                              own_pid, allowed_self_fds), task_set)
            tree_failures = [failure for failure in (revalidate_tree(tree) for tree in trees)
                             if failure is not None]
            persistent_tree_failures.extend(tree_failures)
            for record in result['records']:
                if record.get('state') == 'exited':
                    reconciled.append({'identity': record['identity'], 'resolution': 'exited'})
                expected_absences.extend(record.get('expected_absences', []))
            proof_rows = [record['mount_proof'] for record in result['records']
                          if record.get('mount_proof') is not None]
            counts = {key: sum(record['field_counts'][key] for record in result['records'])
                      for key in ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}
            round_record = {'round': number, 'closure_passes': result['closure_passes'],
                            'task_identities': len(result['final_live']),
                            'rescanned_identities': len(result['records']),
                            'identities': [list(item) for item in sorted(result['final_live'])],
                            'field_counts': counts, 'permission_denials': result['denials'],
                            'target_references': result['references'],
                            'unresolved_churn': result['replacements'],
                            'unscanned_final_identities': [list(item) for item in sorted(result['missing_final'])],
                            'closure_nonconvergent': result['nonconvergent'], 'tree_revalidation_failures': tree_failures,
                            'mount_proofs': proof_rows,
                            'complete_mount_proofs': not result['incomplete'],
                            'clean': result['clean'] and not persistent_tree_failures}
            rounds.append(round_record)
            PROGRESS['rounds'] = rounds
            emit_progress('round', round_record)
            streak = advance_streak(round_record['clean'], streak)
            if streak >= 2:
                break
        status = 'PASS' if streak >= 2 else 'FAIL'
        return {'schema': SCHEMA, 'status': status, 'observer_sha256': source_hash(),
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'observer_pid': own_pid,
                'observer_starttime': own_start, 'started_at_utc': started, 'ended_at_utc': utcnow(),
                'scan_complete': status == 'PASS', 'roots': targets, 'rounds': rounds,
                'tasks_scanned': sum(round_['rescanned_identities'] for round_ in rounds),
                'tree_observation_transients': transients,
                'persistent_tree_revalidation_failures': persistent_tree_failures,
                'reconciled_exits': reconciled,
                'expected_absences': expected_absences, 'allowed_self_scan_fds': sorted(allowed_self_fds),
                'failure': None if status == 'PASS' else 'two consecutive closure-clean rounds not obtained',
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
        who = (8, 8, '1')
        assert closure_decision({who}, {who}, [], [], [], [], 1)['clean']
        assert not closure_decision({who}, set(), [], [], [], [], MAX_CLOSURE_PASSES)['clean']
        assert safe_proc_absence('map_files/7-8') and not safe_proc_absence('mountinfo')
        assert self_fd_reference_allowed(who, 'fd/9', 8, {9})
        print('observer v2 pure synthetic assertions passed')
    else:
        sys.exit(main())
