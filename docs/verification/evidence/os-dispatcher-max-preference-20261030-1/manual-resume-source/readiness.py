"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure manual startup heartbeat and model-controller liveness predicates.
"""
from datetime import datetime
import math


def fresh_heartbeat(state, invocation_started, now, expected):
    keys = ('worker_pid', 'worker_start', 'server_pid', 'server_start')
    if any(state.get(key) != expected.get(key) for key in keys):
        return False
    for key in ('worker_pid', 'server_pid'):
        if type(expected.get(key)) is not int or expected[key] <= 0:
            return False
    for key in ('worker_start', 'server_start'):
        if type(expected.get(key)) is not str or not expected[key].isdigit() or int(expected[key]) <= 0:
            return False
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in (invocation_started, now)):
        return False
    try:
        parsed = datetime.fromisoformat(state['heartbeat_at'].replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return False
        heartbeat = parsed.timestamp()
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError):
        return False
    return invocation_started <= heartbeat <= now and now - heartbeat < 120


def live_guardian(retained, observed):
    return bool(not retained.get('not_started') and observed is not None
                and (observed.get('pid'), observed.get('start')) == (retained.get('pid'), retained.get('start'))
                and observed.get('state') not in ('Z', 'X'))
