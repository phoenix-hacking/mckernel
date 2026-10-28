"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only operation-consumer admission against the genuine armed finite guardian.
No control-module imports, locks, signals, RPC, process starts or state writes.
"""
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import time

BASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1')
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
PACKET_SHA = '369da48abf196bbe68abc6eb4579deddd8f80fc8522560c9ee983e2ca9ae4203'
WINDOW_SHA = '0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e'
THREAD = '01a18111-26a7-7ef2-bbd6-e33d1c8dc803'
RUN = '7f4af94a83b14cc08f97401f5891d965'
CEILING = Decimal('57774.852125')
SPENT_FLOOR = Decimal('22812.3311000000')
DEADLINE = 1793253600
BOOT_CAP = 1051044.6960026678
MONO_CAP = 1035705.5689454618
BOOT_ID = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
INITIAL = {'watcher': (1887110, '96419041'), 'worker': (1887113, '96419049'), 'server': (1887115, '96419058')}


def need(value, message):
    if not value:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def raw(path):
    data = path.read_bytes()
    need(len(data) <= 1 << 20, 'metadata cap exceeded')
    return data


def read(path):
    return json.loads(raw(path))


def birth(pid):
    need(type(pid) is int and pid > 0, 'invalid PID')
    fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, start=fields[19], ppid=int(fields[1]), state=fields[0])


def validate(window, journal, receipt, state, watcher, observe, clocks, boot_id):
    wall, mono, boot = clocks
    need(all(finite(v) for v in clocks), 'invalid clocks')
    need(boot_id == BOOT_ID == journal.get('boot_id') == window.get('boot_id'), 'boot identity')
    need(window.get('deadline_epoch') == DEADLINE and window.get('boot_deadline') == BOOT_CAP,
         'actual immutable window')
    need(window.get('monotonic_deadline') == 1035706.5689547858, 'actual monotonic window')
    need(window.get('credit_run_id') == RUN and Decimal(window['credit_ceiling']) == CEILING, 'window credit identity')
    need(journal.get('packet_sha256') == PACKET_SHA and journal.get('deadline') == DEADLINE,
         'actual guardian packet/deadline')
    need(journal.get('credit_run_id') == RUN, 'guardian credit identity')
    need(journal.get('original_finite') is True and journal.get('initial_prepaid_guard') is True
         and journal.get('credit_started') is True, 'actual finite prepaid guardian')
    cap = journal.get('boot_deadline'); mcap = journal.get('finite_watcher_monotonic_deadline')
    need(finite(cap) and 0 < cap <= BOOT_CAP and finite(mcap) and 0 < mcap <= MONO_CAP, 'guardian clamps')
    need(wall < DEADLINE and mono < mcap and boot < cap, 'delivery deadline reached')
    need(not journal.get('transition_hold') and not journal.get('stop_intent')
         and not journal.get('deadline_stop_sent'), 'guardian hold/stop')
    need(journal.get('last_action') == 'WAIT_EXISTING_CREDIT_WATCHER', 'guardian not healthy resident')
    need(receipt.get('deadline') == DEADLINE, 'guardian receipt deadline')
    owner = receipt.get('birth') or {}
    live = observe(receipt.get('pid'))
    need(live is not None and all(live.get(k) == owner.get(k) for k in ('pid', 'start', 'ppid'))
         and live.get('state') not in ('Z', 'X'), 'guardian receipt live birth')
    original = journal.get('original') or {}
    need(set(original) == set(INITIAL) and all((original[k].get('pid'), original[k].get('start')) == v
         for k, v in INITIAL.items()), 'initial lineage changed')
    chain = journal.get('replacement') or original
    need(set(chain) == set(INITIAL), 'guardian chain fields')
    for name, expected in chain.items():
        observed = observe(expected.get('pid'))
        need(observed is not None and observed.get('state') not in ('Z', 'X')
             and all(observed.get(k) == expected.get(k) for k in ('pid', 'start', 'ppid')), 'live chain '+name)
    need(chain['worker']['ppid'] == chain['watcher']['pid']
         and chain['server']['ppid'] == chain['worker']['pid'], 'live PPID chain')
    need(watcher.get('watcher_pid') == chain['watcher']['pid']
         and watcher.get('event') not in ('watcher_stopped', 'restart_limit_reached'), 'watcher record')
    need(state.get('thread_id') == THREAD and state.get('phase') == 'running'
         and (state.get('goal') or {}).get('status') == 'active' and not state.get('stop_reason'), 'active campaign')
    need(state.get('worker_pid') == chain['worker']['pid'] and state.get('server_pid') == chain['server']['pid']
         and state.get('server_start') == chain['server']['start'], 'campaign live chain')
    age = wall - datetime.fromisoformat(state['heartbeat_at'].replace('Z', '+00:00')).timestamp()
    need(0 <= age < 120, 'stale heartbeat')
    need(not any(state.get(k) for k in ('service_hold', 'policy_hold', 'auth_hold', 'billing_hold',
                                     'credit_budget_error', 'last_error')), 'campaign hold/error')
    need(not any(state.get(k) for k in ('checkpoint_requested', 'stop_now', 'paused')),
         'campaign stop/checkpoint requested')
    need(not state.get('transport_uncertain'), 'campaign transport uncertainty')
    for key in ('resume_instruction', 'last_instruction'):
        instruction = state.get(key)
        need(instruction is None or (isinstance(instruction, dict) and instruction.get('status') not in
             ('sending', 'delivery_uncertain', 'intent', 'uncertain')),
             'campaign instruction uncertainty '+key)
    credit = state.get('credit_budget') or {}; billing = (state.get('settings') or {}).get('billing') or {}
    need(credit.get('id') == RUN and Decimal(credit['budget']) == CEILING, 'cumulative credit identity')
    spent = Decimal(credit['spent']); remaining = Decimal(credit['remaining'])
    need(spent.is_finite() and remaining.is_finite() and SPENT_FLOOR <= spent < CEILING
         and 0 < remaining <= CEILING - spent, 'cumulative credit allowance')
    need(billing.get('mode') == 'prepaid_credits' and Decimal(str(billing.get('credit_budget'))) == CEILING,
         'resident billing guard')
    return [wall, mono, boot]


def guard():
    packet_raw = raw(BASE / 'armed-controller/FROZEN-PACKET.json')
    need(hashlib.sha256(packet_raw).hexdigest() == PACKET_SHA, 'frozen packet bytes')
    packet = json.loads(packet_raw)
    for name, sha in packet['private'].items():
        need(hashlib.sha256(raw(BASE / 'armed-controller' / name)).hexdigest() == sha, 'private bytes '+name)
    for name, sha in packet['canonical'].items():
        need(hashlib.sha256(raw(Path('/home/holden/mckernel/scripts') / name)).hexdigest() == sha, 'canonical bytes '+name)
    window_raw = raw(BASE / 'ACTUAL-WINDOW.json')
    need(hashlib.sha256(window_raw).hexdigest() == WINDOW_SHA, 'actual window bytes')
    for path in (BASE / 'armed-controller/USER-STOP.json', BASE / 'new-guardian-binding-preparation-1/USER-STOP.json'):
        need(not path.exists(), 'explicit stop present')
    return validate(json.loads(window_raw), read(BASE / 'armed-controller/journal.json'),
                    read(BASE / 'armed-controller/bridge-start.json'), read(CAMPAIGN / 'state.json'),
                    read(CAMPAIGN / 'watcher.json'), birth,
                    [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)],
                    Path('/proc/sys/kernel/random/boot_id').read_text().strip())
