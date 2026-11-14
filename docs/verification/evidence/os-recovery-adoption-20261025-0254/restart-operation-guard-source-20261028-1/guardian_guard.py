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
CONTROL = BASE / 'restart-20261028-1200-pacific-1'
ARM_RECEIPT_REF = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1200-pacific-1/ACTUAL-CONTROLS-ARMED.json', 'bytes': 3171, 'sha256': 'fe3c2193600ce06c98f769d4659faaf52d3035437a98c5fa8d33ab43a7ed8202'}
CONFIG_SHA = 'b8a15af2a6272bf67c73d0c7f097c4a737eea62c1716c1e9a254a48746156b5a'
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
PACKET_SHA = '5bc656cc12b97c2ec5f53312a26e8ef800e45d5451c1f0b5d084576d95ff1b22'
WINDOW_SHA = '0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e'
THREAD = '01a183ec-72e5-7400-8f48-b4efb8725520'
RUN = '7f4af94a83b14cc08f97401f5891d965'
CEILING = Decimal('57774.852125')
SPENT_FLOOR = Decimal('22812.3311000000')
DEADLINE = 1793253600
WINDOW_BOOT_CAP = 1051044.6960026678
JOURNAL_BOOT_CAP = 1051043.6959931096
BOOT_CAP = 1051042.6959879305
MONO_CAP = 1035704.5689393478
BOOT_ID = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
INITIAL = {'watcher': (2109395, '101211669'), 'worker': (2109397, '101211677'), 'server': (2109399, '101211685')}


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
    return dict(pid=pid, start=fields[19], ppid=int(fields[1]), state=fields[0],
                comm=(Path('/proc') / str(pid) / 'comm').read_text().strip())


def validate(window, journal, receipt, state, watcher, observe, clocks, boot_id, armed):
    validate_armed(armed, observe)
    wall, mono, boot = clocks
    need(len(clocks) == 3 and all(finite(v) and v >= 0 for v in clocks), 'invalid clocks')
    need(boot_id == BOOT_ID == journal.get('boot_id') == window.get('boot_id'), 'boot identity')
    need(window.get('deadline_epoch') == DEADLINE and window.get('boot_deadline') == WINDOW_BOOT_CAP,
         'actual immutable window')
    need(window.get('monotonic_deadline') == 1035706.5689547858, 'actual monotonic window')
    need(window.get('credit_run_id') == RUN and Decimal(window['credit_ceiling']) == CEILING, 'window credit identity')
    need(journal.get('packet_sha256') == PACKET_SHA and journal.get('deadline') == DEADLINE,
         'actual guardian packet/deadline')
    need(journal.get('credit_run_id') == RUN, 'guardian credit identity')
    need(journal.get('original_finite') is True and journal.get('initial_prepaid_guard') is True
         and journal.get('credit_started') is True, 'actual finite prepaid guardian')
    cap = journal.get('boot_deadline'); mcap = journal.get('finite_watcher_monotonic_deadline')
    need(finite(cap) and 0 < cap <= JOURNAL_BOOT_CAP and finite(mcap) and 0 < mcap <= MONO_CAP, 'guardian clamps')
    need(wall < DEADLINE and mono < min(mcap, MONO_CAP) and boot < min(cap, BOOT_CAP), 'delivery deadline reached')
    need(not journal.get('transition_hold') and not journal.get('stop_intent')
         and not journal.get('deadline_stop_sent'), 'guardian hold/stop')
    need(journal.get('last_action') == 'WAIT_EXISTING_CREDIT_WATCHER', 'guardian not healthy resident')
    need(receipt.get('deadline') == DEADLINE, 'guardian receipt deadline')
    owner = receipt.get('birth') or {}
    live = observe(receipt.get('pid'))
    need(live is not None and all(live.get(k) == owner.get(k) == armed['actors']['guardian'].get(k) for k in ('pid', 'start'))
         and live.get('state') not in ('Z', 'X'), 'guardian receipt live birth')
    need(owner.get('ppid') == 2111551 and armed['actors']['guardian']['ppid'] == 1311,
         'exact recorded guardian shell to supervisor transition')
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
    need(billing.get('mode') == 'prepaid_credits' and Decimal(str(billing.get('credit_budget'))) == CEILING
         and billing.get('automatic_credit_purchase') is False and billing.get('api_key_billing') is False
         and billing.get('account_wide_balance_guard') is True,
         'resident billing guard')
    return [wall, mono, boot]


def validate_control_config(config):
    need(config.get('expected_thread') == THREAD
         and config.get('credit_run_id') == RUN
         and Decimal(config['credit_ceiling']) == CEILING
         and Decimal(config['credit_spent_floor']) >= SPENT_FLOOR,
         'actual controller account/thread configuration')
    need(config.get('included_first') is True
         and config.get('automatic_credit_purchase') is False
         and config.get('api_key_billing') is False, 'actual controller billing mode')
    clock = config['initial_watch_clock']
    need(clock['boot_id'] == BOOT_ID and clock['watcher_pid'] == INITIAL['watcher'][0]
         and clock['watcher_start'] == INITIAL['watcher'][1]
         and clock['deadline'] == DEADLINE
         and finite(clock['boot_deadline']) and 0 < clock['boot_deadline'] <= JOURNAL_BOOT_CAP
         and finite(clock['watcher_cutoff_lower']) and 0 < clock['watcher_cutoff_lower'] <= MONO_CAP,
         'actual controller watch-clock clamp')
    return config


def validate_arm_reference(ref):
    need(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'},
         'actual parent armed receipt not finalized')
    need(ref['path'] == str(CONTROL / 'ACTUAL-CONTROLS-ARMED.json')
         and type(ref['bytes']) is int and ref['bytes'] > 0
         and type(ref['sha256']) is str and len(ref['sha256']) == 64
         and all(c in '0123456789abcdef' for c in ref['sha256']),
         'exact actual parent armed receipt reference')
    return ref


def validate_armed(armed, observe):
    need(armed.get('status') == 'LIVE_CONTINUED_CAMPAIGN_GUARDIAN_20MIN_STEERING_AND_RETAINED_PHONE'
         and armed.get('thread_id') == THREAD and armed.get('phase') == 'running'
         and armed.get('goal_status') == 'active' and armed.get('native_release') is False
         and armed.get('guardian_packet_sha256') == PACKET_SHA
         and armed.get('original_window_unchanged_sha256') == WINDOW_SHA
         and armed.get('steering_interval_seconds') == 1200, 'actual parent control receipt')
    caps = armed['earliest_control_caps']
    need((caps['deadline_epoch'], caps['monotonic_deadline'], caps['boot_deadline']) ==
         (DEADLINE, MONO_CAP, BOOT_CAP), 'actual parent earliest control clamps')
    credit = armed['credit_budget']
    need(credit['id'] == RUN and Decimal(credit['budget']) == CEILING
         and Decimal(credit['spent']) >= SPENT_FLOOR, 'actual parent cumulative account receipt')
    need(armed['auxiliary_leases_held'] == dict(guardian=True,monitor=True,phone=True),
         'actual parent auxiliary lease receipt')
    supervisor = observe(1311)
    need(supervisor is not None and supervisor.get('pid') == 1311
         and supervisor.get('start') == '596' and supervisor.get('ppid') == 1
         and supervisor.get('comm') == 'systemd' and supervisor.get('state') not in ('Z','X'),
         'actual measured auxiliary supervisor birth/name')
    expected = dict(INITIAL, guardian=(2111552, '101236067'),
                    monitor=(2111966, '101243270'), phone=(1894242, '96505809'))
    need(set(armed['actors']) == set(expected), 'actual parent control actors')
    for name, identity in expected.items():
        actor = armed['actors'][name]
        need((actor.get('pid'), actor.get('start')) == identity, 'actual parent actor '+name)
        live = observe(actor['pid'])
        # Auxiliary launch shells exited after recording their initial births.
        # Only the measured existing supervisor 1311 is an allowed reparent.
        if name in ('guardian', 'monitor', 'phone'):
            recorded = dict(guardian=1311,monitor=2111963,phone=1311)
            need(actor['ppid'] == recorded[name], 'actual parent recorded auxiliary PPID '+name)
            parents = (1311,)
        else:
            parents = (actor['ppid'],)
        need(live is not None and live.get('state') not in ('Z','X')
             and (live.get('pid'), live.get('start')) == identity and live.get('ppid') in parents,
             'actual parent live actor '+name)
    return armed


def guard():
    ref = validate_arm_reference(ARM_RECEIPT_REF)
    receipt_raw = raw(Path(ref['path']))
    need(len(receipt_raw) == ref['bytes'] and hashlib.sha256(receipt_raw).hexdigest() == ref['sha256'],
         'actual parent armed receipt bytes')
    packet_raw = raw(CONTROL / 'armed-controller/FROZEN-PACKET.json')
    need(hashlib.sha256(packet_raw).hexdigest() == PACKET_SHA, 'frozen packet bytes')
    packet = json.loads(packet_raw)
    for name, sha in packet['private'].items():
        need(hashlib.sha256(raw(CONTROL / 'armed-controller' / name)).hexdigest() == sha, 'private bytes '+name)
    for name, sha in packet['canonical'].items():
        need(hashlib.sha256(raw(Path('/home/holden/mckernel/scripts') / name)).hexdigest() == sha, 'canonical bytes '+name)
    config_raw = raw(CONTROL / 'armed-controller/CONFIG.json')
    need(hashlib.sha256(config_raw).hexdigest() == CONFIG_SHA, 'actual controller config bytes')
    validate_control_config(json.loads(config_raw))
    window_raw = raw(BASE / 'ACTUAL-WINDOW.json')
    need(hashlib.sha256(window_raw).hexdigest() == WINDOW_SHA, 'actual window bytes')
    for path in (CONTROL / 'USER-STOP.json', CONTROL / 'armed-controller/USER-STOP.json', BASE / 'armed-controller/USER-STOP.json', BASE / 'new-guardian-binding-preparation-1/USER-STOP.json'):
        need(not path.exists(), 'explicit stop present')
    return validate(json.loads(window_raw), read(CONTROL / 'armed-controller/journal.json'),
                    read(CONTROL / 'armed-controller/bridge-start.json'), read(CAMPAIGN / 'state.json'),
                    read(CAMPAIGN / 'watcher.json'), birth,
                    [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)],
                    Path('/proc/sys/kernel/random/boot_id').read_text().strip(), json.loads(receipt_raw))
