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
import types
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ORIGINAL = (Path('/dev/shm/mckernel-exact-candidate-f5d8d914-1'),
            Path('/dev/shm/mckernel-exact-metadata-backup-f5d8d914-1'))
QUARANTINE = (Path('/dev/shm/.mckernel-retirement-candidate-1c00d2b8-1'),
              Path('/dev/shm/.mckernel-retirement-metadata-backup-1c00d2b8-1'))
SCHEMA = 'mckernel.read-only-live-reference-snapshot.v7-map-files-v3'
MAX_ROUNDS = 5
MAX_TREE_ATTEMPTS = 3
MAX_CLOSURE_PASSES = 5
PROGRESS = {'roots': [], 'rounds': [], 'tree_observation_transients': []}
AUDIT_SHA256 = '641c39a3f3be3a1012a47f6e073c5e9df4149512acb1944b45d90e3f900d7ab2'
_AUDIT = None


def audit_module():
    """Reuse the reviewed actual classifier/mount scanner, never a reduced model.

    The packet persists the audit next to the observer in its root-private
    directory. resolve() also handles execution through /proc/self/fd/N.
    Standalone source tests consume the same hash-bound repository bytes.
    """
    global _AUDIT
    if _AUDIT is None:
        here = Path(__file__).resolve()
        path = (here.with_name('deleted-audit.sealed.py') if here.name == 'observer.sealed.py'
                else here.parents[3] / 'scripts/native_exact_candidate_deleted_inode_audit.py')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > 1 << 20:
                raise RuntimeError('audit source type/size')
            source = b''
            while len(source) <= 1 << 20:
                part = os.read(fd, (1 << 20) + 1 - len(source))
                if not part:
                    break
                source += part
            if len(source) != before.st_size or hashlib.sha256(source).hexdigest() != AUDIT_SHA256:
                raise RuntimeError('audit source hash')
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise RuntimeError('audit source changed')
        finally:
            os.close(fd)
        module = types.ModuleType('_retirement_reviewed_audit')
        module.__file__ = str(path)
        exec(compile(source, str(path), 'exec'), module.__dict__)
        _AUDIT = module
    return _AUDIT


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
        return audit_module()._identity(pid, tid)
    except FileNotFoundError:
        # A missing stat alone does not authenticate disappearance.
        try:
            (Path('/proc') / str(pid) / 'task' / str(tid)).stat()
        except FileNotFoundError:
            return None
        raise RuntimeError('existing task has no stat')


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
    data = path.read_text(encoding='utf-8')
    if not data:
        return []  # Never complete alone; coverage requires a parsed '/' representative.
    audit_module()._mount_rows(data)  # strict paths, nsfs, IDs and complete nonempty input
    for line in data.splitlines():
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
    return violations, ids[0] if len(ids) == 1 else None, bool(rows) and len(ids) <= 1


def safe_proc_absence(field):
    return field == 'fd' or field.startswith('fd/') or field == 'map_files' or field.startswith('map_files/')


def self_fd_reference_allowed(who, label, observer_pid, allowed_fds):
    return (who[0] == observer_pid and label.startswith('fd/') and
            label.split('/', 1)[1].isdigit() and int(label.split('/', 1)[1]) in allowed_fds)


def source_hash():
    with open(__file__, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def valid_map_range(name):
    """Accept only bounded, non-empty, increasing hexadecimal VMA ranges."""
    match = re.fullmatch(r'[0-9a-fA-F]+-[0-9a-fA-F]+', name)
    if match is None:
        return False
    start_text, end_text = name.split('-', 1)
    start, end = int(start_text, 16), int(end_text, 16)
    return (start <= 0xffffffffffffffff and end <= 0xffffffffffffffff and
            start < end)


def emit_progress(kind, value):
    print(json.dumps({'schema': SCHEMA + '.progress', 'kind': kind, 'value': value},
                     sort_keys=True, separators=(',', ':')), file=sys.stderr, flush=True)


def identity_state(who, identity_reader=identity):
    current = identity_reader(who[0], who[1])
    if current == who:
        return 'same'
    return 'exited' if current is None else 'reused'


def scan_identity(who, targets, reference, inode_ids, own_pid, allowed_fds,
                  proc_root=Path('/proc'), identity_reader=identity,
                  mount_reader=mount_rows, stat_reader=None,
                  link_reader=os.readlink, mount_coverage=None):
    """Scan one task identity, using /proc/<tgid>/map_files for VMAs."""
    result = {'identity': who, 'successful': False, 'state': None, 'references': [],
              'denials': [], 'incomplete': [], 'expected_absences': [], 'mount_proof': None,
              'field_counts': {key: 0 for key in
                               ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}}

    def observed_state():
        state = identity_state(who, identity_reader)
        result['state'] = state
        return state

    if observed_state() != 'same':
        return result
    pid, tid, _ = who
    task_base = Path(proc_root) / str(pid) / 'task' / str(tid)
    process_base = Path(proc_root) / str(pid)
    audit = audit_module()
    classification = None
    try:
        classification = audit._classification_bound(who, True)
    except (OSError, ValueError):
        result['incomplete'].append({'identity': who, 'field': 'classification'})

    def special_absence(label):
        failures = []
        allowed = (classification in ('kernel-thread', 'zombie') and
                   audit._revalidate_classification(who, classification, failures, True))
        result['incomplete'].extend({'identity': who, 'field': label, 'resolution': value}
                                    for value in failures)
        return allowed

    def probe(path, label):
        try:
            info = (stat_reader or Path.stat)(path)
            result['field_counts'][label.split('/', 1)[0]] += 1
            if (info.st_dev, info.st_ino) in inode_ids and not self_fd_reference_allowed(
                    who, label, own_pid, allowed_fds):
                reference_record = {'identity': who, 'field': label, 'link': None,
                                    'device': info.st_dev, 'inode': info.st_ino}
                try:
                    reference_record['link'] = link_reader(path)
                except OSError as error:
                    reference_record['link_diagnostic_failure'] = repr(error)
                result['references'].append(reference_record)
            return True
        except (FileNotFoundError, ProcessLookupError):
            if observed_state() != 'same':
                return False
            if label in ('cwd', 'root', 'exe') and special_absence(label):
                result['expected_absences'].append({'identity': who, 'field': label,
                                                     'reason': classification + '-absent-surface'})
            elif label.startswith('fd/') or label.startswith('map_files/'):
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
        if not probe(task_base / field, field):
            return result

    try:
        with os.scandir(str(task_base / 'fd')) as iterator:
            for child in iterator:
                if not child.name.isdigit():
                    result['incomplete'].append({'identity': who, 'field': 'fd', 'resolution': 'malformed-entry'})
                    continue
                if not probe(task_base / 'fd' / child.name, 'fd/' + child.name):
                    return result
    except FileNotFoundError:
        if observed_state() != 'same':
            return result
        if not special_absence('fd'):
            result['incomplete'].append({'identity': who, 'field': 'fd', 'resolution': 'still-live'})
    except PermissionError:
        result['denials'].append({'identity': who, 'field': 'fd'})

    # map_files is process-wide (tgid), not task-specific.  The directory
    # itself must be present and parseable for a live identity; only an entry
    # disappearing after revalidation is an expected procfs race.
    map_dir = process_base / 'map_files'
    try:
        with os.scandir(str(map_dir)) as iterator:
            for child in iterator:
                name = child.name
                if not valid_map_range(name):
                    result['incomplete'].append({'identity': who, 'field': 'map_files',
                                                 'entry': name, 'resolution': 'malformed-entry'})
                    continue
                if not probe(map_dir / name, 'map_files/' + name):
                    return result
    except FileNotFoundError:
        if observed_state() != 'same':
            return result
        if not special_absence('map_files'):
            result['incomplete'].append({'identity': who, 'field': 'map_files',
                                         'resolution': 'whole-directory-missing-while-live'})
    except PermissionError:
        if observed_state() == 'same':
            result['incomplete'].append({'identity': who, 'field': 'map_files',
                                         'resolution': 'whole-directory-denied-while-live'})
    except OSError as error:
        if observed_state() == 'same':
            result['incomplete'].append({'identity': who, 'field': 'map_files',
                                         'resolution': 'whole-directory-parse-failure',
                                         'diagnostic': repr(error)})

    coverage = mount_coverage if mount_coverage is not None else {'observed': set(), 'full': []}
    failures = []
    # Read namespace/root independently of mountinfo. The reviewed scanner
    # preserves aliases even when another surface is absent or malformed.
    audit._scan_mountinfo(pid, failures,
                         tuple((target['device_number'], target['filesystem_root']) for target in targets),
                         tid, who, classification if classification in ('kernel-thread', 'zombie') else None,
                         coverage)
    try:
        rows = mount_reader(pid, tid)
        result['field_counts']['mountinfo'] += len(rows)
        violations = mount_bad(rows, targets, reference)
        result['references'].extend({'identity': who, 'field': 'mount-violation', 'detail': value}
                                    for value in violations)
    except FileNotFoundError:
        if observed_state() == 'same' and not special_absence('mountinfo'):
            failures.append('mountinfo-missing')
    except (OSError, ValueError, RuntimeError) as error:
        failures.append('mountinfo-uninspected:' + repr(error))
    if mount_coverage is None:
        audit._finish_mount_coverage(coverage, failures)
    if classification is not None:
        audit._revalidate_classification(who, classification, failures, True)
    result['incomplete'].extend({'identity': who, 'field': 'mount-proof', 'resolution': value}
                                for value in failures)
    result['mount_proof'] = {'identity': who, 'namespaces': sorted(coverage['observed']),
                             'complete': not failures}
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
            coverage = {'observed': set(), 'full': []}
            result = closure_round(lambda who: scan_identity(who, targets, reference, inode_ids,
                                                              own_pid, allowed_self_fds,
                                                              mount_coverage=coverage), task_set)
            mount_failures = []
            audit_module()._finish_mount_coverage(coverage, mount_failures)
            if not result['final_live']:
                mount_failures.append('empty-task-census')
            result['incomplete'].extend(mount_failures)
            result['clean'] = result['clean'] and not mount_failures
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
                            'mount_namespace_coverage': {
                                'observed': sorted(coverage['observed']),
                                'root_representatives': [
                                    {'namespace': namespace, 'identity': list(who),
                                     'task': task, 'classification': classification, 'root': '/'}
                                    for namespace, who, task, classification in coverage['full']],
                                'failures': mount_failures},
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
        print('observer v3 pure synthetic assertions passed')
    else:
        sys.exit(main())
