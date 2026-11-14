"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicit NEW12h operation account/window successor; pure checks and read-only guard.
No release, nonce, ledger mutation, operation, process creation, signal or cleanup.
"""
import ast
import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
STATE = Path('/home/holden/mckernel/.git/os-autopilot/state.json')
CREDITS = Path('/home/holden/mckernel/scripts/os_goal_credits.py')
CREDITS_SHA256 = 'adf5187240ed8199746eef3b59b79d4d38c4ae8ac5821c8d8324833926b21ec3'
WINDOW_SHA256 = '91bdfb1de3955a684d0766ffa85a5e18deda8f5f49c6ce1d85fcdbf2df6e3d86'
THREAD = '01a17e6f-112f-7660-8771-85d15e07a26c'
RUN = '7f4af94a83b14cc08f97401f5891d965'
BUDGET = Decimal('57774.852125')
MIN_SPENT = Decimal('22812.3311')
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
# Legacy helper order is wall, MONOTONIC, BOOTTIME; preserve that order explicitly.
CUTOFFS = (1793165769.0, 947875.677502648, 963213.804550928)

def need(ok, why):
    if not ok:
        raise ValueError(why)

def _canonical_functions():
    raw = CREDITS.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == CREDITS_SHA256, 'canonical credit source drift')
    names = {'amount', 'available_balance'}
    nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name in names]
    need(len(nodes) == 2 and {n.name for n in nodes} == names, 'exact canonical credit functions')
    namespace = {'Decimal': Decimal, 'InvalidOperation': InvalidOperation}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CREDITS)+':EXACT_PURE_FUNCTIONS', 'exec'), namespace)
    return namespace['amount'], namespace['available_balance']

amount, available_balance = _canonical_functions()

def load_window():
    raw = (HERE/'ACTUAL-WINDOW.json').read_bytes()
    need(hashlib.sha256(raw).hexdigest() == WINDOW_SHA256, 'actual window source drift')
    window = json.loads(raw)
    need(window['window_id'] == 'new12h-20261027-1793122569' and window['boot_id'] == BOOT
         and window['deadline_epoch'] == CUTOFFS[0]
         and window['monotonic_deadline'] == CUTOFFS[1]
         and window['boot_deadline'] == CUTOFFS[2]
         and window['credit_run_id'] == RUN and amount(window['credit_ceiling']) == BUDGET,
         'fixed actual window binding')
    return window

def check_window(window, clocks, boot_id):
    need(window == load_window(), 'exact actual window required')
    need(boot_id == BOOT, 'same actual boot required')
    need(isinstance(clocks, (list, tuple)) and len(clocks) == 3
         and all(type(v) in (int, float) and math.isfinite(v) for v in clocks), 'three finite clocks')
    need(all(0 <= observed < cutoff for observed, cutoff in zip(clocks, CUTOFFS)), 'fixed actual cutoff')
    return clocks

def check_account_state(state, wall):
    """Read-only successor of historical guard; canonical balance semantics retained."""
    need(type(wall) in (int, float) and math.isfinite(wall), 'finite account observation clock')
    age = wall-datetime.datetime.fromisoformat(state['heartbeat_at']).timestamp()
    credit = state['credit_budget']
    spent, remaining = amount(credit['spent']), amount(credit['remaining'])
    need(state['phase'] == 'running' and state.get('stop_reason') is None
         and state.get('stop_now', False) is False
         and state['thread_id'] == THREAD and state['goal']['status'] == 'active'
         and not any(state.get(k) for k in ('service_hold', 'policy_hold', 'auth_hold', 'billing_hold'))
         and credit['id'] == RUN and amount(credit['budget']) == BUDGET
         and MIN_SPENT <= spent < BUDGET and remaining == BUDGET-spent and remaining > 0
         and state['credit_budget_error'] is None and 0 <= age < 180,
         'same actual cumulative account guard')
    billing = state['settings']['billing']
    need(billing['mode'] == 'prepaid_credits' and amount(billing['credit_budget']) == BUDGET
         and billing['automatic_credit_purchase'] is False and billing['api_key_billing'] is False
         and billing['account_wide_balance_guard'] is True, 'unchanged resident credit guard')
    return available_balance(state['last_rate_limits'])

def guard():
    """Read-only live precondition check; successful return grants no operation."""
    clocks = [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)]
    check_window(load_window(), clocks, Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    check_account_state(json.loads(STATE.read_bytes()), clocks[0])
    return clocks
