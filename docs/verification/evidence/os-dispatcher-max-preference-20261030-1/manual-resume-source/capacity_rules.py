"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure, capacity-specific decisions. A catalog advertises models; it does not prove
that any model currently has inference capacity or account entitlement.
"""
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/holden/mckernel/scripts")))
from run_os_goal import dispatcher_candidates, DISPATCHER_MODEL_PREFERENCE

DEADLINE = 1793774133
CREDIT = '7f4af94a83b14cc08f97401f5891d965'
CEILING = Decimal('57774.852125')
# Actual NEW1930 control minima, recorded 2026-10-29T04:44:30Z.
BOOT_CAP = 1571574.6959790066
MONO_CAP = 1556236.568932019
HOLDS = ('service_hold', 'policy_hold', 'auth_hold', 'billing_hold',
         'credit_budget_error', 'transport_uncertain', 'stop_errors')
PREFERRED = DISPATCHER_MODEL_PREFERENCE


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite numeric clock required')
    return value


def remaining(caps, wall, boot, mono, boot_id):
    if caps['boot_id'] != boot_id or caps['deadline'] != DEADLINE:
        raise ValueError('same boot and original absolute deadline required')
    b, m = number(caps['boot_deadline']), number(caps['monotonic_deadline'])
    if not 0 < b <= BOOT_CAP or not 0 < m <= MONO_CAP:
        raise ValueError('inherited operational clock cap widened')
    return min(DEADLINE-number(wall), b-number(boot), m-number(mono))


def tighten(caps, wall, boot, mono):
    wall, boot, mono = number(wall), number(boot), number(mono)
    if (caps['deadline'] != DEADLINE or not 0 < number(caps['boot_deadline']) <= BOOT_CAP
            or not 0 < number(caps['monotonic_deadline']) <= MONO_CAP):
        raise ValueError('original finite cutoff caps required')
    return dict(caps, boot_deadline=min(caps['boot_deadline'], boot+max(0, DEADLINE-wall)),
                monotonic_deadline=min(caps['monotonic_deadline'], mono+max(0, DEADLINE-wall)))


def budget_ok(ledger, floor):
    try:
        budget, spent = (Decimal(str(ledger[k])) for k in ('budget', 'spent'))
        minimum = Decimal(str(floor))
        return (ledger.get('id') == CREDIT and budget == CEILING
                and all(x.is_finite() for x in (budget, spent, minimum))
                and 0 <= minimum <= spent)
    except (KeyError, ValueError, ArithmeticError):
        return False


def no_holds(state):
    if any(state.get(key) for key in HOLDS):
        return False
    for key in ('resume_instruction', 'last_instruction'):
        row = state.get(key)
        if row is not None and (not isinstance(row, dict) or row.get('status') != 'accepted_by_server'):
            return False
    limits = state.get('last_rate_limits') or {}
    return not limits.get('spendControlReached')


def root_capacity(state):
    """Exact typed producer failure and failed root-turn identity; never a message match."""
    if (not no_holds(state) or state.get('phase') != 'stopped'
            or state.get('stop_reason') not in {'server_error', 'turn_failed'}):
        return False
    error, failure, typed, goal = (state.get('last_error'), state.get('last_failure'),
                                 state.get('transport_failure'), state.get('goal'))
    if not all(isinstance(x, dict) for x in (error, failure, typed, goal)):
        return False
    root = state.get('thread_id')
    return bool(isinstance(root, str) and root and error.get('codexErrorInfo') == 'serverOverloaded'
                and failure.get('thread_id') == root and isinstance(failure.get('id'), str)
                and failure['id'] and failure.get('error') == error
                and failure.get('reason') in {'server_error', 'turn_failed'}
                and failure.get('log_dir') == state.get('log_dir')
                and typed.get('schema_version') == 1 and typed.get('class') == 'service_transient'
                and typed.get('worker_pid') == state.get('worker_pid')
                and isinstance(typed.get('worker_start'), str) and typed['worker_start'].isdigit()
                and typed['worker_start'] == state.get('worker_start')
                and typed.get('thread_id') == root and typed.get('mutating') is False
                and typed.get('method') is None and typed.get('error_type') == 'ServiceTransient'
                and typed.get('service_error') == error and typed.get('error') == canonical(error)
                and typed.get('channel_unusable') is False
                and goal.get('threadId', root) == root and goal.get('status') == 'blocked')


def live_root_matches(state, live_goal, turns):
    if not root_capacity(state) or canonical(live_goal) != canonical(state['goal']):
        return False
    if not isinstance(turns, list) or not turns or any(t.get('status') == 'inProgress' for t in turns):
        return False
    failure = state['last_failure']
    last = turns[0]
    return (last.get('id') == failure['id'] and last.get('status') == 'failed'
            and last.get('willRetry') is not True and failure.get('will_retry') is not True
            and last.get('error') == failure['error'])


def terminal_child_hint(row):
    return (isinstance(row, dict) and row.get('codexErrorInfo') == 'serverOverloaded'
            and 'turn_failed' in row.get('events', []) and row.get('automatic_retry') is False
            and row.get('willRetry') is not True)


def child_capacity(state, row, live_goal, turns, now):
    if (not no_holds(state) or state.get('phase') != 'running' or state.get('stop_reason')
            or state.get('last_error') is not None or state.get('last_failure') is not None
            or (state.get('goal') or {}).get('status') != 'active'
            or live_goal.get('status') != 'active'
            or live_goal.get('threadId', state.get('thread_id')) != state.get('thread_id')):
        return False
    try:
        age = now-datetime.fromisoformat(state['heartbeat_at'].replace('Z', '+00:00')).timestamp()
        due = number(row['retry_not_before_unix'])
    except (KeyError, ValueError, TypeError):
        return False
    if (not 0 <= age < 120 or now < due or not terminal_child_hint(row)
            or row.get('thread_id') == state.get('thread_id')
            or not isinstance(row.get('thread_id'), str) or not row['thread_id']
            or not isinstance(row.get('turn_id'), str) or not row['turn_id']
            or 'turn_failed' not in row.get('events', []) or row.get('automatic_retry') is not False
            or not isinstance(turns, list) or not turns):
        return False
    last = turns[0]
    return (not any(t.get('status') == 'inProgress' for t in turns)
            and last.get('id') == row['turn_id'] and last.get('status') == 'failed'
            and last.get('willRetry') is not True
            and (last.get('error') or {}).get('codexErrorInfo') == 'serverOverloaded')


def effort_for(catalog, model):
    return next((r['effort'] for r in dispatcher_candidates(catalog)
                 if r['model'] == model), None)


def choose_model(catalog, current, failures, boot):
    unavailable = {current} | {model for model, failed in failures.items()
                               if boot < failed + 60}
    return next((r['model'] for r in dispatcher_candidates(catalog, unavailable)), None)


def worker_routing(catalog, model, effort):
    """Separate advertised worker levels; no dispatcher-effort inheritance."""
    if type(effort) is not str or effort_for(catalog, model) != effort:
        raise ValueError('dispatcher pair differs from canonical advertised preference')
    rows = [r for r in catalog['models'] if r.get('model') == model]
    offered = set(rows[0].get('efforts', [])) if rows else set()
    levels = dict(default_worker='medium', complex_worker='high', auditor='low', reviewer='high')
    if not set(levels.values()) <= offered:
        raise ValueError('independent lower worker efforts are not advertised')
    return dict(dispatcher=dict(model=model, effort=effort),
                **{role: dict(model=model, effort=level) for role, level in levels.items()})


def retired(binding, observe):
    """Only positively absent or positively different births qualify; unreadable raises."""
    if set(binding) != {'watcher', 'worker', 'server', 'guardian', 'monitor'}:
        raise ValueError('complete model envelope binding required')
    for name, row in binding.items():
        if (name in {'guardian', 'monitor'} and set(row) == {'not_started'}
                and row['not_started'] is True):
            continue
        if (type(row.get('pid')) is not int or row['pid'] <= 0
                or not isinstance(row.get('start'), str) or not row['start'].isdigit() or int(row['start']) <= 0):
            raise ValueError('invalid retained process birth')
        actual = observe(row['pid'])
        if actual is not None and (not isinstance(actual.get('start'), str)
                                   or not actual['start'].isdigit() or int(actual['start']) <= 0):
            raise ValueError('unreadable observed process birth')
        if actual is not None and actual['start'] == row['start']:
            return False
    return True


def submission_action(record):
    # No replay after an intent whose process identity or queue result is unknown.
    return 'HOLD_UNCERTAIN_SUBMISSION' if record.get('status') in {'intent', 'uncertain'} else 'CHECK'
