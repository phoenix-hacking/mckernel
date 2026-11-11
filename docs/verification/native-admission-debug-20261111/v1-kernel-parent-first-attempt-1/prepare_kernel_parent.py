#!/usr/bin/python3
"""Real v1 kernel-parent configuration only; never create ownership controls."""
import json
import os
import resource
import stat
import time

PROFILE = (
    ('/sys/fs/cgroup/cpu/mckernel-dev',
     (('cpu.cfs_period_us', '100000'), ('cpu.cfs_quota_us', '400000'))),
    ('/sys/fs/cgroup/memory/mckernel-dev',
     (('memory.use_hierarchy', '1'), ('memory.limit_in_bytes', '12884901888'))),
    ('/sys/fs/cgroup/pids/mckernel-dev', (('pids.max', '512'),)),
)


def scalar(path):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0:
            raise ValueError('existing Root-owned v1 scalar required')
        raw = os.read(fd, 128)
        if len(raw) == 128:
            raise ValueError('v1 scalar bound exceeded')
        return raw.decode('ascii').strip()
    finally:
        os.close(fd)


def main():
    result = {'schema': 'm14-f06-real-v1-kernel-parent-configuration-v1',
              'pid': os.getpid(), 'uid': os.getuid(), 'euid': os.geteuid(),
              'affinity': sorted(os.sched_getaffinity(0)),
              'native_admission': False, 'reservation_released': False,
              'source_custody_admitted': False, 'signal_application_executed': False,
              'current_free': 'UNKNOWN', 'historical_unknowns': 'PRESERVED_UNCHANGED',
              'actions': [], 'started_ns': time.time_ns()}
    def event(value):
        print(json.dumps(value, sort_keys=True), flush=True)
    try:
        if result['uid'] != 0 or result['euid'] != 0 or result['affinity'] != [6]:
            raise ValueError('real/effective Root and exact HOST CPU6 required')
        for which, requested in ((resource.RLIMIT_AS, 268435456),
                                 (resource.RLIMIT_CPU, 10),
                                 (resource.RLIMIT_FSIZE, 8388608),
                                 (resource.RLIMIT_CORE, 0)):
            _, hard = resource.getrlimit(which)
            value = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
            resource.setrlimit(which, (value, value))
        os.umask(0o022)
        # Any existing child, including a partial prior attempt, is a new input
        # needing actual reconciliation; never normalize or overwrite it.
        for directory, controls in PROFILE:
            try:
                os.lstat(directory)
            except FileNotFoundError:
                pass
            else:
                raise ValueError('refuse existing child: ' + directory)
            parent = os.path.dirname(directory)
            st = os.stat(parent)
            if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0:
                raise ValueError('actual Root-owned v1 parent required')
            for name, _ in controls:
                scalar(os.path.join(parent, name))
        event({'event': 'ALL_THREE_CHILDREN_ABSENT_PARENTS_VERIFIED',
               'native_admission': False, 'current_free': 'UNKNOWN'})
        for directory, controls in PROFILE:
            event({'event': 'BEFORE_MKDIR', 'path': directory})
            os.mkdir(directory, 0o755)
            row = {'directory': directory, 'scalars': []}
            result['actions'].append(row)
            for name, expected in controls:
                path = os.path.join(directory, name)
                event({'event': 'BEFORE_NEW_SCALAR_WRITE', 'path': path,
                       'expected': expected})
                fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                try:
                    st = os.fstat(fd)
                    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0:
                        raise ValueError('new Root-owned scalar required')
                    raw = (expected + '\n').encode('ascii')
                    if os.write(fd, raw) != len(raw):
                        raise OSError('short scalar write')
                finally:
                    os.close(fd)
                actual = scalar(path)
                if actual != expected:
                    raise ValueError('new scalar readback differs: ' + path)
                row['scalars'].append({'path': path, 'actual': actual})
        result['status'] = 'REAL_KERNEL_PARENT_CONFIGURED_NATIVE_GATES_STILL_UNQUALIFIED'
        code = 0
    except (OSError, ValueError, UnicodeError) as exc:
        result['status'] = 'PARTIAL_OR_FAILED_KERNEL_CONFIGURATION_UNKNOWN_RETAINED'
        result['error'] = {'type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
                           'diagnostic': str(exc)[:512]}
        code = 1
    result['finished_ns'] = time.time_ns()
    event(result)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
