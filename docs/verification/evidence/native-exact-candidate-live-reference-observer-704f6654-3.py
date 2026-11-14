#!/usr/bin/env python3
"""V3 of the exact live-reference observer.

This additive source loads the reviewed v2 implementation and replaces only
its identity scan.  The process-level map_files directory is authoritative for
VMAs; task-level map_files paths do not exist on Linux.  A missing, denied, or
malformed process map_files directory while the identity is still live is an
incomplete scan and therefore fails closed.  Individual entries may disappear
after identity revalidation, as with other procfs entries.
"""
import hashlib
import importlib.util
import os
from pathlib import Path


_V2_PATH = Path(__file__).with_name('native-exact-candidate-live-reference-observer-704f6654-2.py')
_SPEC = importlib.util.spec_from_file_location('_mckernel_live_reference_observer_v2', _V2_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError('unable to load reviewed v2 observer')
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)

SCHEMA = 'mckernel.read-only-live-reference-snapshot.v7-map-files-v3'
ORIGINAL = _BASE.ORIGINAL
QUARANTINE = _BASE.QUARANTINE
MAX_ROUNDS = _BASE.MAX_ROUNDS
MAX_TREE_ATTEMPTS = _BASE.MAX_TREE_ATTEMPTS
MAX_CLOSURE_PASSES = _BASE.MAX_CLOSURE_PASSES
PROGRESS = _BASE.PROGRESS


def source_hash():
    with open(__file__, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def _identity_same(who, identity_reader):
    state = _BASE.identity_state(who, identity_reader)
    return state == 'same'


def valid_map_range(name):
    """Accept only a bounded, non-empty, increasing hexadecimal VMA range."""
    import re
    match = re.fullmatch(r'[0-9a-fA-F]+-[0-9a-fA-F]+', name)
    if match is None:
        return False
    start_text, end_text = name.split('-', 1)
    start, end = int(start_text, 16), int(end_text, 16)
    return (start <= 0xffffffffffffffff and end <= 0xffffffffffffffff and
            start < end)


def scan_identity(who, targets, reference, inode_ids, own_pid, allowed_fds,
                  proc_root=Path('/proc'), identity_reader=_BASE.identity,
                  mount_reader=_BASE.mount_rows, stat_reader=None,
                  link_reader=os.readlink):
    """Scan one task identity, using /proc/<tgid>/map_files for VMAs."""
    result = {'identity': who, 'successful': False, 'state': None, 'references': [],
              'denials': [], 'incomplete': [], 'expected_absences': [], 'mount_proof': None,
              'field_counts': {key: 0 for key in
                               ('cwd', 'root', 'exe', 'fd', 'map_files', 'mountinfo', 'ns/mnt')}}

    def observed_state():
        state = _BASE.identity_state(who, identity_reader)
        result['state'] = state
        return state

    if observed_state() != 'same':
        return result
    pid, tid, _ = who
    task_base = Path(proc_root) / str(pid) / 'task' / str(tid)
    process_base = Path(proc_root) / str(pid)

    def probe(path, label):
        try:
            info = (stat_reader or Path.stat)(path)
            result['field_counts'][label.split('/', 1)[0]] += 1
            if (info.st_dev, info.st_ino) in inode_ids and not _BASE.self_fd_reference_allowed(
                    who, label, own_pid, allowed_fds):
                reference_record = {'identity': who, 'field': label, 'link': None,
                                    'device': info.st_dev, 'inode': info.st_ino}
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
        with os.scandir(task_base / 'fd') as iterator:
            for child in iterator:
                if not probe(Path(child.path), 'fd/' + child.name):
                    return result
    except FileNotFoundError:
        if observed_state() != 'same':
            return result
        result['incomplete'].append({'identity': who, 'field': 'fd', 'resolution': 'still-live'})
    except PermissionError:
        result['denials'].append({'identity': who, 'field': 'fd'})

    # map_files is process-wide (tgid), not task-specific.  The directory
    # itself must be present and parseable for a live identity; only an entry
    # disappearing after revalidation is an expected procfs race.
    map_dir = process_base / 'map_files'
    try:
        with os.scandir(map_dir) as iterator:
            for child in iterator:
                name = child.name
                if not valid_map_range(name):
                    result['incomplete'].append({'identity': who, 'field': 'map_files',
                                                 'entry': name, 'resolution': 'malformed-entry'})
                    continue
                if not probe(Path(child.path), 'map_files/' + name):
                    return result
    except FileNotFoundError:
        if observed_state() != 'same':
            return result
        result['incomplete'].append({'identity': who, 'field': 'map_files',
                                     'resolution': 'whole-directory-missing-while-live'})
    except PermissionError:
        if observed_state() == 'same':
            result['incomplete'].append({'identity': who, 'field': 'map_files',
                                         'resolution': 'whole-directory-denied-while-live'})
        return result
    except OSError as error:
        if observed_state() == 'same':
            result['incomplete'].append({'identity': who, 'field': 'map_files',
                                         'resolution': 'whole-directory-parse-failure',
                                         'diagnostic': repr(error)})
        return result

    try:
        namespace = link_reader(task_base / 'ns/mnt')
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
    violations, canonical_id, complete = _BASE.mount_proof(rows, targets, reference)
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


# The reviewed v2 orchestration remains unchanged; replace its global scan
# callback and identity source hash while retaining its exact tree/mount logic.
_BASE.scan_identity = scan_identity
_BASE.source_hash = source_hash
_BASE.SCHEMA = SCHEMA
_BASE.failure_record.__globals__['SCHEMA'] = SCHEMA

for _name in ('safe_proc_absence', 'self_fd_reference_allowed', 'identity_state', 'starttime',
              'node_identity', 'membership_digest', 'open_tree', 'tree_baseline',
              'revalidate_tree', 'mount_proof', 'closure_decision', 'closure_round',
              'advance_streak', 'parse_targets', 'observe', 'main', 'utcnow'):
    globals()[_name] = getattr(_BASE, _name)


if __name__ == '__main__':
    if __import__('sys').argv[1:] == ['--self-test']:
        who = (8, 8, '1')
        assert closure_decision({who}, {who}, [], [], [], [], 1)['clean']
        assert not closure_decision({who}, set(), [], [], [], [], MAX_CLOSURE_PASSES)['clean']
        assert safe_proc_absence('map_files/7-8') and not safe_proc_absence('mountinfo')
        assert self_fd_reference_allowed(who, 'fd/9', 8, {9})
        print('observer v3 pure synthetic assertions passed')
    else:
        raise SystemExit(main())
