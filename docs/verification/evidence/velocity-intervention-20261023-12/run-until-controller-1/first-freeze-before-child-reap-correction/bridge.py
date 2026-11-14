"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private one-transition deadline bridge; existing watcher owns model recovery/billing.
No runtime action occurs on import. Only reviewed explicit --run arms actions.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
DEADLINE = datetime(2026, 10, 25, tzinfo=timezone.utc).timestamp()
THREAD = '01a166a8-28f9-7882-9c7c-ffb216a4ee45'
CEILING = Decimal('57774.852125')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic(path, value):
    temp = path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temp.open('w') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read(path, cap=1 << 20):
    raw = path.read_bytes()
    if len(raw) > cap:
        raise ValueError('bounded metadata cap: '+str(path))
    return json.loads(raw)


def birth(pid):
    """None means ENOENT only; unreadable/zombie identity is never clearance."""
    if type(pid) is not int or pid <= 0:
        raise ValueError('invalid PID')
    try:
        fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    if len(fields) < 20:
        raise ValueError('unreadable process identity')
    return dict(pid=pid, start=fields[19], ppid=int(fields[1]), state=fields[0])


def old_gone(binding, observe=birth):
    for row in binding.values():
        now = observe(row['pid'])
        if now is not None and now['start'] == row['start']:
            return False
    return True


def bind(state, watch, observe=birth):
    """Fresh PPID/birth chain, never PID arithmetic or watcher.json liveness."""
    rows = {name: observe(pid) for name, pid in
            [('watcher', watch['watcher_pid']), ('worker', state['worker_pid']), ('server', state['server_pid'])]}
    if any(v is None or v['state'] == 'Z' for v in rows.values()):
        raise ValueError('live triplet unavailable')
    if (rows['worker']['ppid'] != rows['watcher']['pid'] or
            rows['server']['ppid'] != rows['worker']['pid'] or
            rows['server']['start'] != state['server_start']):
        raise ValueError('watcher/worker/server identity chain mismatch')
    return rows


def leases_free(directory):
    for name in ('watch.lock', 'run.lock'):
        with (directory/name).open('rb') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            fcntl.flock(stream, fcntl.LOCK_UN)
    return True


def weekly_exhausted(state):
    limits = state.get('last_rate_limits') or {}
    for name in ('primary', 'secondary'):
        row = limits.get(name) or {}
        if (type(row.get('windowDurationMins')) is int and row['windowDurationMins'] == 10080 and
                type(row.get('usedPercent')) in (int, float) and
                math.isfinite(row['usedPercent']) and row['usedPercent'] == 100):
            return True
    return False


def prepaid_budget(state):
    limits = state.get('last_rate_limits') or {}
    credit = limits.get('credits') or {}
    if (credit.get('hasCredits') is not True or credit.get('unlimited') is not False or
            limits.get('spendControlReached')):
        raise ValueError('finite authorized prepaid balance unavailable/held')
    number = Decimal(str(credit.get('balance')))
    if not number.is_finite() or number <= 0:
        raise ValueError('prepaid balance unavailable/exhausted')
    return str(min(CEILING, number))


def already_draining(state):
    reason = state.get('stop_reason') or ''
    return (bool(reason) or
            state.get('phase') != 'running' or
            (state.get('goal') or {}).get('status') != 'active')


def effective_now(wall, boot, boot_deadline):
    # Persisted BOOTTIME cutoff survives controller restart/suspend and prevents
    # backward wall-clock adjustment from extending this authorized window.
    return max(wall, DEADLINE + boot-boot_deadline)


def strict_restart(original, code, state, watchdog=False, stopped=False):
    """Reuse existing recovery vetoes, then require a positive known class."""
    if not original(code, state, watchdog, stopped):
        return False
    reason = state.get('stop_reason') or ''
    info = (state.get('last_error') or {}).get('codexErrorInfo') if isinstance(state.get('last_error'), dict) else None
    return (reason == 'rate_limit' or
            reason in ('server_error', 'turn_failed') and info in ('serverOverloaded', 'rateLimitExceeded') or
            reason == 'watchdog_recovery' and watchdog or
            reason in ('active_goal_did_not_continue', 'launcher_error') and state.get('retryable') is True)


def decide(state, journal, now, retired, free, state_sha, permit=None, cancelled=False):
    if now < journal.get('last_clock', now)-2:
        return 'HOLD_CLOCK_REGRESSION'
    if state.get('thread_id') != THREAD:
        return 'HOLD_THREAD_CHANGED'
    if state.get('service_hold') or state.get('policy_hold') or state.get('billing_hold'):
        return 'HOLD_EXPLICIT_SERVICE_AUTH_BILLING'
    if cancelled:
        return 'DRAIN_USER_STOP' if not already_draining(state) else 'STOP_USER_STOP'
    if now >= DEADLINE:
        # The replacement has its own finite watcher cutoff. Never race that
        # watcher with another TERM; second signals shorten Campaign's drain.
        if journal.get('credit_started'):
            return 'WAIT_FINITE_WATCHER_DRAIN' if not retired else 'STOP_DEADLINE'
        if already_draining(state) or journal.get('deadline_stop_sent'):
            return 'WAIT_DEADLINE_DRAIN' if not retired else 'STOP_DEADLINE'
        return 'DRAIN_DEADLINE'
    if 'launch_intent' in journal and not journal.get('credit_started'):
        return 'HOLD_UNCERTAIN_LAUNCH_NO_RETRY'
    if journal.get('credit_started'):
        return 'WAIT_EXISTING_CREDIT_WATCHER' if not retired else 'STOP_CREDIT_WATCHER_EXIT_NO_RESTART'
    if state.get('phase') != 'stopped':
        if state.get('phase') == 'running' and (state.get('goal') or {}).get('status') != 'active':
            return 'WAIT_USER_OR_GOAL_STOP_NO_RESUME'
        return 'WAIT_RESIDENT_UNCHANGED'
    if not retired or not free:
        return 'WAIT_POSITIVE_OLD_MODEL_RETIREMENT_AND_LEASES'
    if (state.get('resume_instruction') or {}).get('status') in ('sending', 'delivery_uncertain'):
        return 'HOLD_UNCERTAIN_INSTRUCTION'
    reason = state.get('stop_reason')
    error = state.get('last_error')
    info = error.get('codexErrorInfo') if isinstance(error, dict) else None
    if isinstance(info, (str, dict)) and any(word in json.dumps(info).lower()
            for word in ('policy', 'auth', 'billing', 'spendcontrol', 'quota')):
        return 'HOLD_SERVICE_AUTH_BILLING_ERROR'
    automatic = (reason == 'included_usage_guard' and weekly_exhausted(state) and
                 ((state.get('settings') or {}).get('billing') or {}).get('mode') == 'included_only')
    # A paused/signal state is never authorization by itself. Managed transfer
    # needs explicit root approval of the FINAL stopped state, after retirement.
    managed = (isinstance(permit, dict) and permit.get('status') == 'PASS_COORDINATED_MODEL_HANDOFF' and
               permit.get('thread_id') == THREAD and permit.get('deadline') == DEADLINE and
               permit.get('stopped_state_sha256') == state_sha and permit.get('explicit_resume_authorized') is True and
               type(permit.get('expires_unix')) in (int, float) and now < permit['expires_unix'] <= DEADLINE and
               permit.get('reason') == 'managed_credit_enablement' and bool(permit.get('review_id')) and
               (reason == 'work_window' or isinstance(reason, str) and reason.startswith('signal_')))
    if not (automatic or managed):
        if reason == 'work_window' or isinstance(reason, str) and reason.startswith('signal_'):
            return 'WAIT_EXPLICIT_POSTSTOP_HANDOFF_PERMIT_NO_RESUME'
        return 'HOLD_STOP_NOT_AUTHORIZED_FOR_CREDIT_TRANSITION'
    if (state.get('goal') or {}).get('status') in ('complete', 'budgetLimited'):
        return 'HOLD_GOAL_COMPLETE_OR_BUDGET_HOLD'
    # Remote/service quota, auth, billing, unknown and credit_balance_decreased
    # never enter the automatic path above. Preflight rechecks actual balance.
    try:
        prepaid_budget(state)
    except (ValueError, TypeError, ArithmeticError):
        return 'HOLD_PREPAID_BALANCE'
    return 'START_EXISTING_LAUNCHER_RECOVERY_ONLY'


def launcher_argv(config, budget, boot_deadline):
    return ['/usr/bin/taskset', '-c', '0,2-7', '/home/holden/anaconda3/bin/python3', '-B',
            str(HERE/'finite_launcher.py'), '--deadline-utc', config['deadline_utc'],
            '--boot-deadline', str(boot_deadline), '--',
            '--model', 'gpt-6.1-sol', '--effort', 'medium', '--profile', 'aggressive',
            '--max-agents', '11', '--build-jobs', '7', '--agent-windows', 'off', '--stall-seconds', '0',
            '--quiet',
            '--grace-seconds', '30', '--credit-budget', budget,
            '--credit-run-id', config['credit_run_id'], '--startup-instruction-file', str(HERE/'CURRENT-INVOCATION.txt'),
            '--startup-instruction-sha256', digest((HERE/'CURRENT-INVOCATION.txt').read_bytes())]


def stop_worker(binding, observe=birth):
    row = binding['worker']
    fd = os.pidfd_open(row['pid'])
    try:
        current = observe(row['pid'])
        if current is None or current['start'] != row['start'] or current['ppid'] != binding['watcher']['pid']:
            raise ValueError('worker identity changed; no signal')
        signal.pidfd_send_signal(fd, signal.SIGTERM)
    finally:
        os.close(fd)


def run(config):
    if (datetime.fromisoformat(config['deadline_utc'].replace('Z', '+00:00')).timestamp() != DEADLINE or
            len(config['credit_run_id']) != 32 or any(c not in '0123456789abcdef' for c in config['credit_run_id'])):
        raise ValueError('fixed deadline or credit identity invalid')
    journal_path = HERE/'journal.json'
    journal = read(journal_path) if journal_path.exists() else {}
    state_raw = (CAMPAIGN/'state.json').read_bytes(); state = json.loads(state_raw)
    if state['thread_id'] != THREAD:
        raise ValueError('exact existing thread required')
    if not journal:
        if (state.get('phase') != 'running' or (state.get('goal') or {}).get('status') != 'active' or
                state.get('stop_reason') or
                not 0 <= time.time()-datetime.fromisoformat(state['heartbeat_at'].replace('Z', '+00:00')).timestamp() < 120):
            raise ValueError('first arm requires fresh healthy resident; no restart or guessing')
        journal = dict(original=bind(state, read(CAMPAIGN/'watcher.json')),
                       boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                       boot_deadline=time.clock_gettime(time.CLOCK_BOOTTIME)+(DEADLINE-time.time()),
                       credit_run_id=config['credit_run_id'], deadline=DEADLINE, last_clock=time.time())
        atomic(journal_path, journal)
    if journal['credit_run_id'] != config['credit_run_id'] or journal['deadline'] != DEADLINE:
        raise ValueError('retained deadline/credit identity changed')
    if journal['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        raise ValueError('reboot requires explicit reconciliation')
    while True:
        raw = (CAMPAIGN/'state.json').read_bytes(); state = json.loads(raw)
        now = effective_now(time.time(), time.clock_gettime(time.CLOCK_BOOTTIME), journal['boot_deadline'])
        if not journal.get('credit_started') and state.get('phase') == 'running':
            watched = read(CAMPAIGN/'watcher.json')
            if watched.get('watcher_pid') != journal['original']['watcher']['pid']:
                return 'HOLD_EXTERNAL_WATCHER_CHANGED'
            if not already_draining(state):
                # A watcher recovery replaces worker/server. Retirement proof
                # must follow the latest actual chain, not just first-arm PIDs.
                journal['original'] = bind(state, watched)
                atomic(journal_path, journal)
        expected = journal.get('replacement', journal['original'])
        if journal.get('credit_started') and 'replacement' not in journal:
            observed = birth(journal['replacement_watcher_pid'])
            retired = observed is None or observed['start'] != journal['replacement_watcher_start']
        else:
            retired = old_gone(expected)
        permit = read(HERE/'handoff.json') if (HERE/'handoff.json').exists() else None
        action = decide(state, journal, now, retired, leases_free(CAMPAIGN), digest(raw), permit,
                        cancelled=(HERE/'USER-STOP.json').exists())
        journal.update(last_action=action, last_clock=max(now, journal.get('last_clock', now)))
        atomic(journal_path, journal)
        if action.startswith('DRAIN_'):
            live = bind(state, read(CAMPAIGN/'watcher.json'))
            if journal.get('stop_intent'):
                raise ValueError('prior signal intent is uncertain; no duplicate TERM')
            journal['stop_intent'] = dict(reason=action, binding=live, at=now)
            atomic(journal_path, journal)  # Persist BEFORE the exact one signal.
            stop_worker(live)
            journal['deadline_stop_sent'] = True
            atomic(journal_path, journal)
        elif action.startswith('START_'):
            # No native clearance is forged: initial model may only reconcile
            # preserved owners/source. New guest/build waits actual clearance.
            argv = launcher_argv(config, prepaid_budget(state), journal['boot_deadline'])
            journal.update(launch_intent=dict(argv=argv, state_sha256=digest(raw), at=now))
            atomic(journal_path, journal)
            if ((HERE/'USER-STOP.json').exists() or digest((CAMPAIGN/'state.json').read_bytes()) != digest(raw) or
                    not old_gone(journal['original']) or not leases_free(CAMPAIGN) or time.time() >= DEADLINE):
                raise ValueError('transition changed after intent; preserve state, never replay')
            with (HERE/'replacement-launcher.log').open('ab', buffering=0) as stream:
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                         start_new_session=True)
            journal.update(credit_started=True, replacement_watcher_pid=child.pid,
                           replacement_watcher_start=birth(child.pid)['start'])
            atomic(journal_path, journal)
            # Observe the existing watcher-published new chain; no second launch.
        elif action.startswith(('HOLD_', 'STOP_')):
            return action
        if journal.get('credit_started') and state.get('phase') == 'running':
            candidate = bind(state, read(CAMPAIGN/'watcher.json'))
            if (candidate['watcher']['pid'] == journal['replacement_watcher_pid'] and
                    candidate['watcher']['start'] == journal['replacement_watcher_start']):
                journal['replacement'] = candidate
                atomic(journal_path, journal)
        remaining = min(DEADLINE-time.time(), journal['boot_deadline']-time.clock_gettime(time.CLOCK_BOOTTIME))
        time.sleep(min(5, max(0.01, remaining)) if remaining > 0 else 5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--cancel', action='store_true')
    args = parser.parse_args()
    if args.cancel:
        atomic(HERE/'USER-STOP.json', dict(explicit_stop=True, at=time.time()))
        return
    if not args.run:
        parser.error('explicit --run required; preparation is not arming')
    os.umask(0o077)
    with (HERE/'bridge.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = read(HERE/'CONFIG.json')
        atomic(HERE/'bridge-start.json', dict(pid=os.getpid(), birth=birth(os.getpid()), deadline=DEADLINE))
        print(run(config), flush=True)


if __name__ == '__main__':
    main()
