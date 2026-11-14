"""Materialize Root's reviewed current inputs, then enter the existing caller once."""
import datetime
import math
from decimal import Decimal, InvalidOperation
import argparse
import ast
import pathlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

HERE = Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/normal-operation-1')
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

def aggregate_rss():
    rows={}
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            t=(p/'stat').read_text();v=t[t.rfind(')')+2:].split();rows[int(p.name)]=(int(v[1]),int(v[21])*os.sysconf('SC_PAGE_SIZE'),t[t.find('(')+1:t.rfind(')')])
        except (OSError,ValueError,IndexError):pass
    w={1561218,1824289,1824291,1824293,os.getpid()}
    w.update(p for p,v in rows.items() if v[2] in ('codex','codex-code-mode','dockerd','containerd'))
    while True:
        children={p for p,v in rows.items() if v[0] in w}
        if children<=w:break
        w.update(children)
    return sum(rows[p][1] for p in w if p in rows)

def amount(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Credit amount must be a finite number")
    text = str(value)
    if len(text) > 64:
        raise ValueError("Credit amount is too long")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("Invalid credit amount") from error
    if not number.is_finite() or number < 0 or number > Decimal("1e12"):
        raise ValueError("Credit amount is outside the supported range")
    if positive and number == 0:
        raise ValueError("Credit budget must be positive")
    return number


def available_balance(limits):
    if not isinstance(limits, dict) or not isinstance(limits.get("credits"), dict):
        raise ValueError("Prepaid-credit balance is unknown")
    credits = (limits or {}).get("credits") or {}
    if credits.get("hasCredits") is not True or credits.get("unlimited") is not False:
        raise ValueError("A finite available prepaid-credit balance is required")
    balance = amount(credits.get("balance"))
    if balance <= 0:
        raise ValueError("Prepaid credits are exhausted")
    if (limits or {}).get("spendControlReached"):
        raise ValueError("Account spending control has been reached")
    return balance


def current_account_snapshot():
    """Reuse qualified current-owner9032 receipt data, without an account call."""
    import types
    helper = HERE / 'current_account_snapshot.py'
    expected_owner_path = HERE / 'CURRENT-ACTUAL-OWNER.json'
    helper_raw = helper.read_bytes()
    expected_raw = expected_owner_path.read_bytes()
    assert digest(helper_raw) == 'fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6'
    assert digest(expected_raw) == 'a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'
    module = types.ModuleType('qualified_current_owner_account_consumer')
    module.__file__ = str(helper)
    exec(compile(helper_raw, str(helper), 'exec'), module.__dict__)
    return module.current_account_snapshot(json.loads(expected_raw))


def main():
    assert os.getuid() == 1000 and os.geteuid() == 1000
    assert 6 in os.sched_getaffinity(0)
    os.sched_setaffinity(0, {6})
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    parser=argparse.ArgumentParser()
    parser.add_argument('--operation-review',required=True)
    parser.add_argument('--operation-review-sha256',required=True)
    args=parser.parse_args()
    review_path=Path(args.operation_review)
    assert review_path.is_absolute() and len(args.operation_review_sha256)==64 and all(c in '0123456789abcdef' for c in args.operation_review_sha256)
    review_raw=review_path.read_bytes();review_sha=digest(review_raw)
    assert review_sha==args.operation_review_sha256
    review=json.loads(review_raw)
    expected={'status':'PASS_ACTUAL_INSTALL_ONLY','scope':'ROOT_CODE_INSTALL_ONLY',
              'proposal_sha256':digest((HERE/'RESOURCE-PROPOSAL-CURRENT.json').read_bytes()),
              'driver_sha256':digest((HERE/'prepare_current.py').read_bytes()),
              'parent_manifest_sha256':digest((HERE/'FROZEN-SOURCE.json').read_bytes()),
              'child_manifest_sha256':digest((HERE/'SOURCE-BOUND.json').read_bytes()),
              'native_release':False,'native_currentfree':None,'retire_operation_only':True}
    assert review==expected
    for item in json.loads((HERE/'RESOURCE-PROPOSAL-CURRENT.json').read_bytes())['source_bindings'].values():
        assert digest(Path(item['path']).read_bytes())==item['sha256']
    state = json.loads((REPO / '.git/os-autopilot/state.json').read_bytes())
    assert state['phase'] == 'running' and state['stop_reason'] is None
    assert state['weekly_usage_error'] is None and state['weekly_confirmation_pending'] is False
    binding = {}
    overhead = 0
    for role, pid, ppid, birth in [('watcher', 1824289, 1824287, '56295798'), ('worker', 1824291, 1824289, '56295805'), ('server', 1824293, 1824291, '56295812')]:
        fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
        assert fields[0] not in ('Z', 'X', 'x') and int(fields[1]) == ppid and fields[19] == birth
        assert os.stat('/proc/%d' % pid).st_uid == 1000
        binding[role] = {'pid': pid, 'ppid': ppid, 'start': birth}
        rss = [row for row in Path('/proc/%d/status' % pid).read_text().splitlines() if row.startswith('VmRSS:')]
        assert len(rss) == 1
        overhead += int(rss[0].split()[1]) * 1024
    overhead=aggregate_rss()
    assert overhead < 2 * GIB

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
    assert available >= 26 * GIB  # Retained18 + currentHOST4 + floor4, no native borrow.

    # Never compare a later event against the pre-resource-check state snapshot.
    # Every returned input passed fresh paired state/event/credit checks.
    state, usage, credit, observed = current_account_snapshot()
    assert usage is not None
    observed = datetime.datetime.fromisoformat(usage['at']).timestamp()
    assert 0 <= time.time() - observed < 25
    assert usage['rateLimitReachedType'] is None and (usage['spendControlReached'] is None or usage['spendControlReached'] is False)
    assert usage['primary'] == state['last_rate_limits']['primary']
    assert state.get('auth_mode')=='chatgpt' and state.get('credit_budget_error') is None
    assert credit==state['credit_budget'] and credit.get('id')=='7c6ef3604bfb4008a917bba8cfb6cfaa' and credit.get('budget')=='[PRIVATE_FINITE_CREDIT_AMOUNT_REDACTED]'
    from decimal import Decimal
    assert Decimal(credit['remaining'])>0 and Decimal(credit['spent'])<Decimal(credit['budget'])
    usage.update(credit_run_id=credit['id'],credit_budget=credit['budget'],credit_guard=credit)
    assert usage['primary']['windowDurationMins'] == 10080 and 0 <= usage['primary']['usedPercent'] <= 100
    usage_path=HERE/'ACTUAL-ACCOUNT-CURRENT.json'
    usage_raw=canonical(usage)
    write_once(usage_path,usage)

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
           'manual_invocation': '20261112T094452Z-12a4bea0', 'owner_pid': 1824293, 'owner_birth': '56295812',
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
              'credit_run_id':credit['id'],'credit_budget':credit['budget'],
              'caps': deadlines, 'owner_cap_sha256': cap_sha}
    controls = dict(common, usage_sha256=digest(usage_raw), owner_cap=cap)
    capacity = dict(common, billing_mode='included_first_same_durable_credit_budget', same_thread=True, generic_c_request_still_held=True,
                    native_reservation_bytes=12*GIB, dfd_unknown_bytes=4*GIB, v2_unknown_bytes=2*GIB,
                    publication_max_bytes=2*GIB, planning_ceiling_bytes=4*GIB, non_additive=False,
                    native_workloads_barred=True, other_host_compilation_barred=True, shared_overhead_bytes=2*GIB,
                    independent_review_sha256=review_sha, independent_review_status='PASS_ACTUAL_INSTALL_ONLY',
                    supervisor=binding['server'], scratch_mount_id=int(mount[0]), scratch_mount_device=mount[2],
                    scratch_mount_source=mount[dash + 2])
    controls_sha = write_once(HERE / 'ACTUAL-CONTROLS-CURRENT.json', controls)
    capacity_sha = write_once(HERE / 'ACTUAL-CAPACITY-CURRENT.json', capacity)
    actual = {'version': 1, 'nonce': nonce, 'one_shot_admission_id': secrets.token_hex(32),
              'weekly_used_percent': usage['primary']['usedPercent'], 'weekly_observed_utc_ns': int(observed * 10**9),
              'usage_evidence_sha256': digest(usage_raw), 'service_status': 'NO_NEW_REJECTION', 'sampled_boot_ns': boot,
              'additional_reserved_bytes': 2*GIB, 'sudo_overhead_reserved_bytes': 2*GIB,
              'sudo_overhead_observed_bytes': overhead, 'deadline_boot_ns': cap['expiry_boot_ns'],
              'deadline_mono_ns': cap['expiry_mono_ns'], 'utc_cap_ns': cap['expiry_utc_ns'],
              'phase1_deadline_boot_ns': cap['expiry_boot_ns'] - 70_000_000_000,
              'receipt_expires_boot_ns': cap['expiry_boot_ns'] - 40_000_000_000,
              'join_capture_reserve_ns': 10_000_000_000, 'term_grace_ns': 5_000_000_000,
              'kill_grace_ns': 5_000_000_000, 'join_grace_ns': 10_000_000_000, 'retire_operation_only': True,
              'controls_sha256': controls_sha, 'capacity_sha256': capacity_sha,
              'interpreter_sha256': digest(Path('/usr/bin/python3').resolve(strict=True).read_bytes())}
    prelim_raw=(HERE/'preliminary-current.py').read_bytes()
    # Only definitions are loaded from the pinned current reader, no legacy observer entrypoint.
    import types
    prelim=types.ModuleType('_reviewed_publication_preflight');prelim.__file__=str(HERE/'preliminary-current.py')
    exec(compile(prelim_raw,prelim.__file__,'exec'),prelim.__dict__)
    prelim.controller_checks(controls,capacity,time.time())
    prelim.verify_scratch_mount(capacity)
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


if __name__=='__main__':main()
