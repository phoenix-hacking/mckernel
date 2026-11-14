"""One fresh second boot followed by the unchanged signal workload; offline only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

BASE = '/home/holden/mckernel-work/host-preparation/native-second-stop-case-preparation-20261021-1/current053d-normalization-runtime-preparation-1/runtime-source-1/two-generation-namespace-4/reboot_capture.py'
BASE_SHA256 = '856ba88df4539307dd8574ab520652a3bc669e72aebd13fcb1683a39dbdc0a85'
ND = '/home/holden/mckernel/scripts/application-tests/native_diagnostic.py'
ND_SHA256 = '1b43934aacf63f21082448a99dd7237759387411200ced997aa2a16700505e5e'
ARGV = ['/bin/mcexec', '-t', '1', '0', 'app', 'A', '', 'B']
ENV = {'PATH': '/usr/bin:/bin', 'COKERNEL_PATH': '/apps'}
OUTPUT = b'handled=1 observed_blocked=1 restored=1\n'


def bound(name, path, digest):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
        raise ValueError('frozen consumer changed')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def need(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(items):
    value = {}
    for key, item in items:
        need(key not in value, 'duplicate key')
        value[key] = item
    return value


# printk info prefix and exact audit formats from the frozen d99 module sources.
PREFIX = r'<6>\[ *[0-9]+\.[0-9]+\] '
IDENTITY = r'os=(?P<os>[0-9]+) generation=(?P<generation>[0-9]+) pid=(?P<pid>[0-9]+)'
AUDIT = [re.compile(PREFIX + module + operation + IDENTITY + suffix) for module, operation, suffix in (
    (r'ihk_smp_x86_64: IHK-SMP: ', r'application SCHEDULE ', r' cpu=0'),
    (r'ihk_smp_x86_64: IHK-SMP: ', r'application retirement ', r' token=[0-9]+ errno=-?[0-9]+'),
    (r'mcctrl: ', r'application_process=release ', r' cleanup_errno=0'),
    (r'ihk_smp_x86_64: IHK-SMP: ', r'application procfs published ', r' tid=[0-9]+'),
    (r'ihk_smp_x86_64: IHK-SMP: ', r'application procfs deleted ', r' tid=[0-9]+'),
    (r'mcctrl: ', r'application_syscall=delivered ', r' worker=[0-9]+ delivery=[0-9]+ cpu=0 number=[0-9]+'),
    (r'mcctrl: ', r'application_syscall=returned ', r' worker=[0-9]+ delivery=[0-9]+ cpu=0 value=-?[0-9]+'),
    (r'mcctrl: ', r'application_syscall=return_route ', r' worker=[0-9]+ delivery=[0-9]+ launcher_cpu=1 guest_cpu=0'),
    (r'mcctrl: ', r'application_process=registered ', r''),
)]


BEGIN_ND = '/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-readiness-runtime-failure-2/coherent-successor-preparation-1/runtime-source-successor-1/strict-native/native_diagnostic.py'
BEGIN_ND_SHA = 'f4c3db94bb9de130577be73f3a1cda1d8ef18b3ec8941d70584751db3f5d86eb'
BEGIN_AUDIT = [re.compile(PREFIX + module + operation + IDENTITY + suffix) for module, operation, suffix in (
    (r'mcctrl: ', r'application_process=cleanup_requested ', r' intent_errno=-?[0-9]+'),
    (r'ihk_smp_x86_64: IHK-SMP: ', r'application cleanup ACK ', r' token=[0-9]+ errno=-?[0-9]+ abandoned=[01]'),
)]

def begin_diagnostic(manifest):
    if manifest is None or 'cleanup_profile' not in manifest:
        return None
    diagnostic = bound('reboot_workload_begin_nd', BEGIN_ND, BEGIN_ND_SHA)
    diagnostic._validate_cleanup_profile(manifest['cleanup_profile'], manifest['modules'])
    return diagnostic


def workload_view(serial, generation, manifest=None):
    """Lossless strict audit partition with complete identity/terminal joins.

    Source-supported transient retirement EAGAIN is kept before its successful
    distinct-token retry. Quarantine errors, foreign identities and duplicate
    events fail before any line can be removed from either epoch's view.
    """
    begin = begin_diagnostic(manifest)
    patterns = AUDIT + BEGIN_AUDIT if begin is not None else AUDIT
    markers = ('application_syscall=', 'application SCHEDULE',
               'application retirement', 'application_process=', 'application procfs')
    if begin is not None:
        markers += ('application cleanup ACK',)
    epochs = {'1': [], '2': []}
    classified = []
    for position, line in enumerate(serial.splitlines(keepends=True)):
        epoch = None
        if any(marker in line for marker in markers):
            need(line.endswith('\n'), 'complete audit record')
            wire = line[:-1]
            if wire.endswith('\r'):
                wire = wire[:-1]
            matches = [(kind, match) for kind, pattern in enumerate(patterns)
                       if (match := pattern.fullmatch(wire))]
            need(len(matches) == 1, 'exact source-supported application audit')
            kind, row = matches[0]
            epoch = row['generation']
            need(row['os'] == '0' and epoch in epochs and
                 0 < int(row['pid']) < 2**64, 'known application audit epoch')
            epochs[epoch].append((position, kind, row['pid'], wire))
        classified.append((epoch, line))
    for epoch, rows in epochs.items():
        scheduled = [row for row in rows if row[1] == 0]
        need(len(scheduled) == 1, 'one scheduled identity per epoch')
        registered = [row for row in rows if row[1] == 8]
        need(len(registered) <= 1 and all(row[0] < scheduled[0][0] for row in registered),
             'optional registered identity precedes schedule')
        pid = scheduled[0][2]
        need(all(row[2] == pid for row in rows), 'all audit rows belong to scheduled PID')
        need(len({(kind, wire) for _, kind, _, wire in rows}) == len(rows), 'duplicate audit event')
        events = {kind: [row for row in rows if row[1] == kind] for kind in range(11 if begin is not None else 8)}
        for kind in ((3, 4) if begin is not None else (2, 3, 4)):
            need(len(events[kind]) == 1, 'one release/procfs event per epoch')
        for kind in (3, 4):
            need(events[kind][0][3].endswith(' tid=' + pid), 'procfs TID matches simple workload PID')
        retirement = []
        for position, _, _, wire in events[1]:
            token, errno = re.search(r' token=([0-9]+) errno=(-?[0-9]+)$', wire).groups()
            need(0 < int(token) < 2**64 and int(errno) in (-11, 0), 'source retirement retry or success')
            retirement.append((position, int(token), int(errno)))
        need(len({token for _, token, _ in retirement}) == len(retirement), 'distinct retirement tokens')
        terminal = [position for position, _, errno in retirement if errno == 0]
        need(len(terminal) == 1 and all(position < terminal[0] for position, _, errno in retirement if errno),
             'transient retries precede unique successful retirement')
        exits = [position for position, _, _, wire in events[5] if wire.endswith(' number=231')]
        need(len(exits) == 1 and scheduled[0][0] < events[3][0][0] < exits[0] <
             events[4][0][0] < terminal[0] and
             all(exits[0] < position for position, _, _ in retirement), 'per-epoch retirement order')
        if begin is None:
            need(terminal[0] < events[2][0][0], 'per-epoch legacy release order')
        else:
            need(not events[2], 'BEGIN profile cannot substitute a legacy release row')
            epoch_view = ''.join(line for found, line in classified if found is None or found == epoch)
            # Invoke the accepted checker on the exact epoch, with its own exit.
            terminal_index = next(i for i, line in enumerate(epoch_view.splitlines())
                                  if 'application_syscall=delivered ' in line and
                                  re.search(r'os=0 generation=' + epoch + r' pid=' + pid +
                                            r' worker=[0-9]+ delivery=[0-9]+ cpu=0 number=231$', line))
            begin._check_begin_cleanup(epoch_view, 'os=0 generation=' + epoch + ' pid=' + pid,
                                       terminal_index)
    return ''.join(line for epoch, line in classified if epoch is None or epoch == str(generation))


def evaluate(manifest, observation):
    serial = observation['serial']
    base = bound('reboot_workload_base', BASE, BASE_SHA256)
    result = base.evaluate(serial)  # All original release/boot assertions retained.
    diagnostic = begin_diagnostic(manifest) or bound('reboot_workload_nd', ND, ND_SHA256)
    need(not diagnostic.BAD_MARKERS.search(serial + '\n' + observation['debugcon']), 'kernel failure marker')
    first_observation = dict(observation, serial=workload_view(serial, 1, manifest))
    first = diagnostic.evaluate(manifest, first_observation)
    lifecycle = bound('reboot_workload_lifecycle', '/home/holden/mckernel/scripts/application-tests/native_diagnostic_lifecycle_capture.py',
                      '0585f78b80e603c010316418ce307794d59e1d92581b845ec6b2e74e22c8954b')
    lifecycle.validate_lifecycle_capture(serial)
    lines = serial.splitlines(keepends=True)
    selected = [(i, x) for i, x in enumerate(lines) if x.startswith('ND_SECOND_PAYLOAD')]
    need(len(selected) == 1, 'one second workload')
    index, line = selected[0]
    need(line.startswith('ND_SECOND_PAYLOAD ') and line.endswith('\n') and len(line.encode()) <= 4096,
         'bounded second workload record')
    wire = line[:-1]
    if wire.endswith('\r'):
        wire = wire[:-1]
    need('\r' not in wire, 'terminal transport CR only')
    report = json.loads(wire[len('ND_SECOND_PAYLOAD '):], object_pairs_hook=pairs)
    need(set(report) == {'argv', 'cwd', 'env', 'raw_wait_status', 'started_ns', 'reaped_ns',
                         'finished_ns', 'streams', 'procfs_empty'}, 'workload fields')
    need(report['argv'] == ARGV and report['cwd'] == '/case/work' and report['env'] == ENV,
         'same second workload launch contract')
    need(type(report['raw_wait_status']) is int and report['raw_wait_status'] == 0 and
         report['procfs_empty'] is True, 'second workload exit and retirement')
    for name in ('started_ns', 'reaped_ns', 'finished_ns'):
        need(type(report[name]) is int and 0 < report[name] < 2**64, 'workload timestamp')
    need(report['started_ns'] <= report['reaped_ns'] <= report['finished_ns'], 'workload time order')
    need(set(report['streams']) == {'stdout', 'stderr'}, 'workload streams')
    for name, expected in [('stdout', OUTPUT), ('stderr', b'')]:
        stream = report['streams'][name]
        need(type(stream) is dict and set(stream) == {'hex', 'eof', 'truncated', 'observed',
             'retained', 'discarded', 'limit', 'eof_ns'}, 'workload stream fields')
        need(type(stream['hex']) is str and stream['hex'] == expected.hex() and
             stream['eof'] is True and stream['truncated'] is False, 'exact workload bytes/EOF')
        for field in ('observed', 'retained', 'discarded', 'limit', 'eof_ns'):
            need(type(stream[field]) is int and 0 <= stream[field] < 2**64, 'stream integer')
        need(stream['observed'] == stream['retained'] == len(expected) and
             stream['discarded'] == 0 and stream['limit'] == 1024 and
             report['started_ns'] <= stream['eof_ns'] <= report['finished_ns'], 'stream accounting')
    reboot = [(i, x) for i, x in enumerate(lines) if x.startswith('ND_REBOOT ')]
    original = [i for i, x in enumerate(lines) if x.startswith('ND_PAYLOAD ')]
    need(len(reboot) == len(original) == 1 and reboot[0][0] < index < original[0], 'publication order')
    need(all(i < index for i, x in enumerate(lines) if x.startswith('ND_REBOOT')), 'complete boot before workload record')
    header = json.loads(reboot[0][1][len('ND_REBOOT '):])
    life_header = json.loads(next(x[len('ND_LIFECYCLE '):] for x in lines if x.startswith('ND_LIFECYCLE ')))
    release_header = json.loads(next(x[len('ND_RESOURCE '):] for x in lines if x.startswith('ND_RESOURCE ')))
    need(first['guest_report']['reaped_ns'] < life_header['started_ns'] <= life_header['finished_ns'] <
         release_header['started_ns'] <= release_header['finished_ns'] < header['started_ns'] <=
         header['finished_ns'] < report['started_ns'] <= report['reaped_ns'] <= report['finished_ns'] <=
         first['guest_report']['finished_ns'], 'full workload/release/reboot/workload order')
    schedules = re.findall(r'application SCHEDULE os=0 generation=2 pid=(\d+) cpu=0\b', serial)
    need(len(schedules) == 1, 'fresh generation2 workload schedule')
    prefix = r'os=0 generation=2 pid=' + schedules[0]
    legacy_lifecycle = () if 'cleanup_profile' in manifest else (
                    r'application retirement ' + prefix + r' token=\d+ errno=0\b',
                    r'application_process=release ' + prefix + r' cleanup_errno=0\b')
    for pattern in (*legacy_lifecycle,
                    *[r'application procfs ' + op + ' ' + prefix + r' tid=' + schedules[0] + r'\b'
                      for op in ('published', 'deleted')]):
        need(len(re.findall(pattern, serial)) == 1, 'generation2 retirement/release')
    second_view = workload_view(serial, 2, manifest)
    if 'cleanup_profile' in manifest:
        diagnostic._check_syscall_trace(second_view, prefix, True)
    else:
        diagnostic._check_syscall_trace(second_view, prefix)
    return dict(result, first_workload_protocol=first['status'], rebooted_os_workload_protocol='PASS', second_workload=report,
                second_stop_verified=False, native_execution_verified=False, full_cycle_verified=False)
