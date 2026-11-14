"""Pure proposed attempt-0002 admission comparisons, NOT an execution caller.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This module performs no I/O and conveys no release or current identity claim.
"""
import math

CAPS = {'boot_deadline': 1571568.6959155537,
        'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',
        'deadline': 1793774133,
        'monotonic_deadline': 1556230.5688700147}
THREAD = '01a18bc3-e072-7810-9426-75101b0856c0'
ROLES = frozenset(('guardian', 'monitor', 'server', 'watcher', 'worker'))


def check_controls(receipt, supervisor, observed, now, boot, mono, boot_id, stopped):
    """Compare already authenticated input snapshots; raise on uncertainty.

    The calling owner must separately authenticate exact document path and bytes,
    obtain fresh proc identities and service/usage facts, and own the operation.
    """
    if (not isinstance(receipt, dict) or receipt.get('thread_id') != THREAD or
            receipt.get('caps') != CAPS or receipt.get('native_release') is not False):
        raise ValueError('wrong attempt or caps')
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (now, boot, mono)) or
            boot_id != CAPS['boot_id'] or now >= CAPS['deadline'] or
            boot >= CAPS['boot_deadline'] or mono >= CAPS['monotonic_deadline'] or stopped):
        raise ValueError('stopped or deadline expired')
    rows = receipt.get('binding')
    if not isinstance(rows, dict) or set(rows) != ROLES:
        raise ValueError('controller roles differ')
    if not isinstance(supervisor, dict) or set(supervisor) != {'pid', 'ppid', 'start'}:
        raise ValueError('supervisor identity missing')
    if not isinstance(observed, dict) or set(observed) != ROLES | {'supervisor'}:
        raise ValueError('live identity set differs')
    all_rows = dict(rows, supervisor=supervisor)
    ids = []
    for role, row in all_rows.items():
        if not isinstance(row, dict):
            raise ValueError('malformed identity')
        pid, ppid, start = row.get('pid'), row.get('ppid'), row.get('start')
        if type(pid) is not int or pid <= 0 or type(ppid) is not int or ppid <= 0 or not isinstance(start, str) or not start.isdigit():
            raise ValueError('malformed process identity')
        actual = observed[role]
        if (not isinstance(actual, dict) or actual.get('pid') != pid or
                actual.get('ppid') != ppid or actual.get('start') != start or
                actual.get('state') not in ('R', 'S', 'D', 'I')):
            raise ValueError('controller changed or not live')
        ids.append(pid)
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate process identity')
    if (rows['guardian']['ppid'] != supervisor['pid'] or
            rows['monitor']['ppid'] != supervisor['pid'] or
            rows['watcher']['ppid'] != supervisor['pid'] or
            rows['worker']['ppid'] != rows['watcher']['pid'] or
            rows['server']['ppid'] != rows['worker']['pid']):
        raise ValueError('controller parentage differs')
    return True
