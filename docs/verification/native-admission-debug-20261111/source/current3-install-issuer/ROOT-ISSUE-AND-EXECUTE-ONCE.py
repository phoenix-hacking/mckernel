"""Materialize Root's reviewed current inputs, then enter the existing caller once."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

HERE = Path('/home/holden/mckernel-work/m14-resume-20261105-1/current-owner-publication-private-3')
REPO = Path('/home/holden/mckernel')
BOOT = '3ba4f2ca-4323-433d-bfb8-7859268121b6'
GIB = 1024**3

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def write_once(path, value):
    raw = canonical(value)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    return digest(raw)

assert os.getuid() == 1000 and os.geteuid() == 1000
assert 6 in os.sched_getaffinity(0)
os.sched_setaffinity(0, {6})
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
review_path = HERE / 'ROOT-INDEPENDENT-REVIEW.ACTUAL.json'
review_raw = review_path.read_bytes()
review_sha = digest(review_raw)
assert review_sha == 'a5cb9698e742631d49fb72de7afcd3b53d9db6c6d2652c74626f2505ece2d68d'
review = json.loads(review_raw)
for name, key in [('prepare_current.py', 'driver_sha256'), ('RESOURCE-PROPOSAL-CURRENT.json', 'proposal_sha256'),
                  ('FROZEN-SOURCE.json', 'parent_manifest_sha256'), ('SOURCE-BOUND.json', 'child_manifest_sha256')]:
    assert digest((HERE / name).read_bytes()) == review[key], name

state = json.loads((REPO / '.git/os-autopilot/state.json').read_bytes())
assert state['phase'] == 'running' and state['stop_reason'] is None
assert state['weekly_usage_error'] is None and state['weekly_confirmation_pending'] is False
binding = {}
overhead = 0
for role, pid, ppid, birth in [('watcher', 22540, 1392, '301112'), ('worker', 22543, 22540, '301120'),
                               ('server', 22545, 22543, '301128')]:
    fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    assert fields[0] not in ('Z', 'X', 'x') and int(fields[1]) == ppid and fields[19] == birth
    assert os.stat('/proc/%d' % pid).st_uid == 1000
    binding[role] = {'pid': pid, 'ppid': ppid, 'start': birth}
    rss = [row for row in Path('/proc/%d/status' % pid).read_text().splitlines() if row.startswith('VmRSS:')]
    assert len(rss) == 1
    overhead += int(rss[0].split()[1]) * 1024
assert overhead < 1536 * 1024**2

scratch = '/home/holden/mckernel-work/scratch-readonly-20261105'
mount_rows = [row.split() for row in Path('/proc/self/mountinfo').read_text().splitlines()
              if len(row.split()) > 5 and row.split()[4] == scratch]
assert len(mount_rows) == 1
mount = mount_rows[0]
dash = mount.index('-')
assert mount[dash + 1] == 'ext4' and 'ro' in mount[5].split(',')
assert 'ro' in mount[dash + 3].split(',') and 'norecovery' in mount[dash + 3].split(',')
headroom = {}
for path, floor in [('/var/lib', 16 * GIB), (scratch, 12 * GIB)]:
    fs = os.statvfs(path)
    headroom[path] = fs.f_bavail * fs.f_frsize
    assert headroom[path] >= floor
memory = [row for row in Path('/proc/meminfo').read_text().splitlines() if row.startswith('MemAvailable:')]
assert len(memory) == 1
available = int(memory[0].split()[1]) * 1024
assert available >= 28 * GIB  # Conservative 22 GiB historical + 2 GiB HOST + 4 GiB floor.

# Obtain the actual current event; never print or retain its credits fields.
protocol = REPO / '.git/os-autopilot/runs/20261105T221223Z-74c11d83/protocol.jsonl'
with protocol.open('rb') as stream:
    stream.seek(0, 2)
    stream.seek(max(0, stream.tell() - 4 * 1024 * 1024))
    lines = stream.read().splitlines()
usage = None
for raw in reversed(lines):
    try:
        row = json.loads(raw)
    except (ValueError, UnicodeError):
        continue
    event = row.get('event', {})
    if event.get('method') == 'account/rateLimits/updated':
        rate = event['params']['rateLimits']
        usage = {'at': row['at'], 'source_event': event['method'], 'primary': rate['primary'],
                 'rateLimitReachedType': rate.get('rateLimitReachedType'),
                 'spendControlReached': rate.get('spendControlReached')}
        break
assert usage is not None
observed = datetime.datetime.fromisoformat(usage['at']).timestamp()
assert 0 <= time.time() - observed < 25
assert usage['rateLimitReachedType'] is None and usage['spendControlReached'] is None
assert usage['primary'] == state['last_rate_limits']['primary']
assert usage['primary']['windowDurationMins'] == 10080 and 0 <= usage['primary']['usedPercent'] < 100
usage_path = REPO / 'docs/verification/m14-current-included-usage-20261105.json'
usage_raw = canonical(usage)
fd = os.open(str(usage_path), os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
try:
    assert os.fstat(fd).st_uid == 1000
    os.fchmod(fd, 0o600)
    os.write(fd, usage_raw)
    os.fsync(fd)
finally:
    os.close(fd)

nonce = secrets.token_hex(32)
for name in ('mckernel-install-' + nonce, 'mckernel-code-' + nonce):
    assert not os.path.lexists('/var/lib/' + name)
utc = time.time_ns()
boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
mono = time.monotonic_ns()
# Whole-second bounds avoid float/Decimal rounding widening the selected cap.
deadlines = {'deadline': (utc + 150_000_000_000) // 10**9,
             'boot_deadline': (boot + 150_000_000_000) // 10**9,
             'monotonic_deadline': (mono + 150_000_000_000) // 10**9, 'boot_id': BOOT}
cap = {'version': 1, 'record_type': 'ROOT_PUBLICATION_ONE_SHOT_CAP_V1', 'scope': 'ROOT_CODE_INSTALL_ONLY',
       'manual_invocation': '20261105T221223Z-74c11d83', 'owner_pid': 22545, 'owner_birth': '301128',
       'boot_id': BOOT, 'nonce': nonce, 'preliminary_sha256': digest((HERE / 'preliminary-current.py').read_bytes()),
       'profile_sha256': digest((HERE / 'PROFILE.SOURCE-ONLY.json').read_bytes()),
       'parent_manifest_sha256': review['parent_manifest_sha256'], 'child_manifest_sha256': review['child_manifest_sha256'],
       'driver_sha256': review['driver_sha256'], 'independent_review_sha256': review_sha,
       'native_release': False, 'native_currentfree': None, 'issued_utc_ns': utc, 'issued_boot_ns': boot,
       'issued_mono_ns': mono, 'expiry_utc_ns': deadlines['deadline'] * 10**9,
       'expiry_boot_ns': deadlines['boot_deadline'] * 10**9, 'expiry_mono_ns': deadlines['monotonic_deadline'] * 10**9}
assert cap['expiry_utc_ns'] <= usage['primary']['resetsAt'] * 10**9
cap_sha = write_once(HERE / 'ROOT-ONE-SHOT-CAP.ACTUAL.json', cap)
common = {'scope': 'ROOT_CODE_INSTALL_ONLY', 'thread_id': '01a18bc3-e072-7810-9426-75101b0856c0',
          'native_release': False, 'native_currentfree': None, 'nonce': nonce, 'binding': binding,
          'caps': deadlines, 'owner_cap_sha256': cap_sha}
controls = dict(common, usage_sha256=digest(usage_raw), owner_cap=cap)
capacity = dict(common, billing_mode='included_only', same_thread=True, generic_c_request_still_held=True,
                native_reservation_bytes=12*GIB, dfd_unknown_bytes=4*GIB, v2_unknown_bytes=2*GIB,
                publication_max_bytes=4*GIB, planning_ceiling_bytes=12*GIB, non_additive=True,
                native_workloads_barred=True, other_host_compilation_barred=True, shared_overhead_bytes=2*GIB,
                independent_review_sha256=review_sha, independent_review_status='PASS_ACTUAL_INSTALL_ONLY',
                supervisor=binding['server'], scratch_mount_id=int(mount[0]), scratch_mount_device=mount[2],
                scratch_mount_source=mount[dash + 2])
controls_sha = write_once(HERE / 'ACTUAL-CONTROLS-CURRENT.json', controls)
capacity_sha = write_once(HERE / 'ACTUAL-CAPACITY-CURRENT.json', capacity)
actual = {'version': 1, 'nonce': nonce, 'one_shot_admission_id': secrets.token_hex(32),
          'weekly_used_percent': usage['primary']['usedPercent'], 'weekly_observed_utc_ns': int(observed * 10**9),
          'usage_evidence_sha256': digest(usage_raw), 'service_status': 'NO_NEW_REJECTION', 'sampled_boot_ns': boot,
          'additional_reserved_bytes': 4*GIB, 'sudo_overhead_reserved_bytes': 2*GIB,
          'sudo_overhead_observed_bytes': overhead, 'deadline_boot_ns': cap['expiry_boot_ns'],
          'deadline_mono_ns': cap['expiry_mono_ns'], 'utc_cap_ns': cap['expiry_utc_ns'],
          'phase1_deadline_boot_ns': cap['expiry_boot_ns'] - 70_000_000_000,
          'receipt_expires_boot_ns': cap['expiry_boot_ns'] - 40_000_000_000,
          'join_capture_reserve_ns': 10_000_000_000, 'term_grace_ns': 5_000_000_000,
          'kill_grace_ns': 5_000_000_000, 'join_grace_ns': 10_000_000_000, 'retire_operation_only': True,
          'controls_sha256': controls_sha, 'capacity_sha256': capacity_sha,
          'interpreter_sha256': digest(Path('/usr/bin/python3').resolve(strict=True).read_bytes())}
actual_path = HERE / 'ACTUAL-VALUES-CURRENT.json'
actual_sha = write_once(actual_path, actual)
write_once(HERE / 'ROOT-DYNAMIC-ADMISSION.ACTUAL.json',
           {'status': 'ADMITTED_CODE_PUBLICATION_ONCE', 'nonce': nonce, 'review_sha256': review_sha,
            'controls_sha256': controls_sha, 'capacity_sha256': capacity_sha, 'actual_sha256': actual_sha,
            'headroom_bytes': headroom, 'memory_available_bytes': available, 'control_rss_bytes': overhead,
            'native_release': False, 'native_currentfree': None, 'historical_reservation_release': False})
reservation_parent = HERE / 'reservations'
os.mkdir(str(reservation_parent), 0o700)
print(json.dumps({'status': 'ENTERING_REVIEWED_PUBLICATION_CALLER_ONCE', 'nonce': nonce,
                  'usage_percent': usage['primary']['usedPercent'], 'cap_seconds': 150}), flush=True)
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-I', '-B', str(HERE / 'prepare_current.py'),
         '--actual-values', str(actual_path), '--actual-values-sha256', actual_sha,
         '--operation-review', str(review_path), '--operation-review-sha256', review_sha,
         '--reservation-parent', str(reservation_parent), '--execute'])
