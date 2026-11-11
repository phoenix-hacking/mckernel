"""Private source successor of the qualified account snapshot helper; no issuer entrypoint."""
import datetime
import hashlib
import importlib
import json
import math
import pathlib
import sys
import time
from decimal import Decimal, InvalidOperation
REPO = pathlib.Path('/home/holden/mckernel')
VALIDATOR_SHA256 = '39a03dd8bb33ea943cad02897dee9b6b113187eee30d33ed22a89886b944d870'

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


def _load_current_validator():
    path = REPO / 'scripts/run_os_goal.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == VALIDATOR_SHA256
    scripts = str(REPO / 'scripts')
    # This is the normal canonical script namespace, never a private package.
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    module = importlib.import_module('run_os_goal')
    assert pathlib.Path(module.__file__).resolve() == path.resolve()
    return module.accepted_account_observation


def current_account_snapshot(expected_owner):
    """Read a fresh durable poll/notification snapshot under independent owner pins.

    expected_owner comes from the separately reviewed actual current Root admission;
    it cannot be fabricated from a receipt or copied from an earlier invocation.
    This helper performs no account request, controller write, nonce or issue.
    """
    assert type(expected_owner) is dict
    credit_path = REPO / '.git/os-autopilot/credit-runs/7c6ef3604bfb4008a917bba8cfb6cfaa.json'
    assert expected_owner['credit_run_id'] == '7c6ef3604bfb4008a917bba8cfb6cfaa'
    assert expected_owner['credit_ledger_path'] == str(credit_path)
    assert expected_owner['thread_id'] == '01a18bc3-e072-7810-9426-75101b0856c0'
    assert expected_owner['repo'] == str(REPO)
    assert expected_owner['boot_id'] == pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    state_path = REPO / '.git/os-autopilot/state.json'
    accept = _load_current_validator()
    account_keys = ('phase', 'stop_reason', 'weekly_usage_error', 'weekly_confirmation_pending',
                    'auth_mode', 'credit_budget_error', 'last_rate_limits', 'credit_budget',
                    'log_dir', 'resume_instruction', 'thread_id', 'worker_pid', 'worker_start',
                    'server_pid', 'server_start', 'service_hold', 'auth_hold', 'billing_hold',
                    'policy_hold', 'goal', 'repo', 'guardian_run_id', 'transport_failure',
                    'last_account_observation', 'last_account_notification', 'successful_account_read')

    def checked_state():
        value = json.loads(state_path.read_bytes())
        assert value['phase'] == 'running' and value['stop_reason'] is None
        assert value['weekly_usage_error'] is None and value['weekly_confirmation_pending'] is False
        assert value.get('auth_mode') == 'chatgpt' and value.get('credit_budget_error') is None
        assert not any(value.get(key) for key in ('service_hold', 'auth_hold', 'billing_hold', 'policy_hold'))
        for key in ('log_dir', 'thread_id', 'worker_pid', 'worker_start', 'server_pid',
                    'server_start', 'repo', 'guardian_run_id'):
            assert value.get(key) == expected_owner[key]
        for kind in ('worker', 'server'):
            pid = expected_owner[kind + '_pid']
            assert type(pid) is int and pid > 0
            raw = pathlib.Path('/proc/%d/stat' % pid).read_text()
            fields = raw.rsplit(')', 1)[1].split()
            assert fields[0] in ('R', 'S', 'D', 'T', 't', 'W', 'K', 'P', 'I')
            assert fields[19] == expected_owner[kind + '_start']
        rate = value.get('last_rate_limits')
        assert type(rate) is dict and type(rate.get('primary')) is dict
        used = rate['primary'].get('usedPercent')
        assert isinstance(used, (int, float)) and not isinstance(used, bool) and math.isfinite(used) and 0 <= used <= 100
        assert rate['primary'].get('windowDurationMins') == 10080
        assert rate.get('rateLimitReachedType') is None
        assert rate.get('spendControlReached') is None or rate.get('spendControlReached') is False
        available_balance(rate)
        saved = value['credit_budget']
        assert saved['id'] == expected_owner['credit_run_id']
        assert amount(saved['budget'], positive=True) == amount(expected_owner['credit_budget'], positive=True)
        assert amount(saved['remaining'], positive=True) > 0
        assert amount(saved['spent']) < amount(saved['budget'], positive=True)
        amount(saved['last_balance'], positive=True)
        return value

    last_mismatch = None
    for attempt in range(3):
        before = checked_state()
        credit = json.loads(credit_path.read_bytes())
        assert credit['id'] == expected_owner['credit_run_id']
        assert amount(credit['budget'], positive=True) == amount(expected_owner['credit_budget'], positive=True)
        assert amount(credit['remaining'], positive=True) > 0
        assert amount(credit['spent']) < amount(credit['budget'], positive=True)
        # The original controller is the observation producer; no event is synthesized.
        after = checked_state()
        same_snapshot = all(before.get(key) == after.get(key) for key in account_keys)
        if same_snapshot and credit == after['credit_budget']:
            accepted = accept(after, credit, expected_owner, time.time_ns(), time.monotonic_ns(), 25)
            # Both controller bookends and the real ledger are coherent before
            # validating freshness; transient mismatches consume bounded attempts.
            rate = after['last_rate_limits']
            assert available_balance(rate) == amount(credit['last_balance'], positive=True)
            observed = accepted['received_utc_ns'] / 1000000000
            usage = {'at': datetime.datetime.fromtimestamp(observed, datetime.timezone.utc).isoformat(),
                     'source_event': accepted['method'], 'source_kind': accepted['source'],
                     'primary': rate['primary'], 'rateLimitReachedType': rate.get('rateLimitReachedType'),
                     'spendControlReached': rate.get('spendControlReached'),
                     'receipt_received_utc_ns': accepted['received_utc_ns'],
                     'receipt_received_mono_ns': accepted['received_mono_ns']}
            return after, usage, credit, observed
        last_mismatch = {'attempt': attempt + 1, 'state_changed_fields':
                         [key for key in account_keys if before.get(key) != after.get(key)],
                         'same_credit_record': credit == after['credit_budget']}
    raise AssertionError('fresh current-owner account snapshot did not stabilize: ' + json.dumps(last_mismatch, sort_keys=True))
