"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only operation-consumer admission against the genuine armed finite guardian.
No control-module imports, locks, signals, RPC, process starts or state writes.
"""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import time
import os

BASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1')
CONTROL = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1')
ARM_RECEIPT_REF = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/ACTUAL-CONTROLS-ARMED.json', 'bytes': 2021, 'sha256': '42c8b2a0045a7720f15ef591436a0158c2e08f219e30982d22f961c19be4c039'}
CONFIG_SHA = 'a35c97e0b8ba9fb1d2e84a6b7a08cdecc01ef1da3b1216634dbb91e7bb60521d'
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
PACKET_SHA = '37ec170a9c65b65a4fd4749f0db554a77131432817e00c8d09e70186f0aa6a39'
WINDOW_SHA = 'c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
THREAD = '01a18582-1fc6-77b1-bfb6-15c86483f579'
DEADLINE = 1793774133
WINDOW_BOOT_CAP = 1571576.6960040887
JOURNAL_BOOT_CAP = 1571573.6959699572
BOOT_CAP = 1571573.6959699572
MONO_CAP = 1556235.568922472
BOOT_ID = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
INITIAL = {'watcher': (2525801, '109898158'), 'worker': (2525803, '109898174'), 'server': (2525805, '109898192')}

GUARDIAN_LAUNCH_PPID = 2526572
GUARDIAN_RECORDED_PPID = 1311
EXPECTED_ACTORS = {'watcher': (2525801, '109898158'), 'worker': (2525803, '109898174'), 'server': (2525805, '109898192'), 'guardian': (2526573, '109903679'), 'monitor': (2526609, '109904364'), 'phone': (2526610, '109904364')}
AUX_RECORDED_PPIDS = {'guardian': 1311, 'monitor': 1311, 'phone': 1311}


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
    need(window.get('monotonic_deadline') == 1556238.568953068, 'actual monotonic window')
    need(window.get('billing_mode') == 'included_only' and window.get('allow_prepaid_fallback') is False and window.get('weekly_limit_identity') == WEEKLY_IDENTITY, 'actual weekly-only window')
    need(journal.get('packet_sha256') == PACKET_SHA and journal.get('deadline') == DEADLINE,
         'actual guardian packet/deadline')
    need(journal.get('original_finite') is True and not journal.get('initial_prepaid_guard') and not journal.get('credit_started'), 'actual included-only finite guardian')
    cap = journal.get('boot_deadline'); mcap = journal.get('finite_watcher_monotonic_deadline')
    need(finite(cap) and 0 < cap <= JOURNAL_BOOT_CAP and finite(mcap) and 0 < mcap <= MONO_CAP, 'guardian clamps')
    need(wall < DEADLINE and mono < min(mcap, MONO_CAP) and boot < min(cap, BOOT_CAP), 'delivery deadline reached')
    need(not journal.get('transition_hold') and not journal.get('stop_intent')
         and not journal.get('deadline_stop_sent'), 'guardian hold/stop')
    need(journal.get('last_action') == 'WAIT_RESIDENT_UNCHANGED', 'guardian not healthy resident')
    need(receipt.get('deadline') == DEADLINE, 'guardian receipt deadline')
    owner = receipt.get('birth') or {}
    live = observe(receipt.get('pid'))
    need(live is not None and all(live.get(k) == owner.get(k) == armed['actors']['guardian'].get(k) for k in ('pid', 'start'))
         and live.get('state') not in ('Z', 'X'), 'guardian receipt live birth')
    need(owner.get('ppid') == GUARDIAN_LAUNCH_PPID and armed['actors']['guardian']['ppid'] == GUARDIAN_RECORDED_PPID,
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
    validate_weekly_account(state, wall)
    need(mono<state['weekly_effective_monotonic_end'] and boot<state['weekly_effective_boot_end'], 'confirmed earlier monotonic/boot end reached')
    return [wall, mono, boot]


def validate_control_config(config):
    need(config.get('expected_thread') == THREAD and config.get('billing_mode') == 'included_only'
         and config.get('allow_prepaid_fallback') is False and config.get('initial_credit_budget') is None
         and config.get('automatic_credit_purchase') is False and config.get('api_key_billing') is False,
         'actual weekly included-only controller configuration')
    clock=config['initial_watch_clock']
    need(clock['boot_id']==BOOT_ID and clock['watcher_pid']==INITIAL['watcher'][0]
         and clock['watcher_start']==INITIAL['watcher'][1] and clock['deadline']==DEADLINE
         and finite(clock['boot_deadline']) and 0<clock['boot_deadline']<=BOOT_CAP
         and finite(clock['watcher_cutoff_lower']) and 0<clock['watcher_cutoff_lower']<=MONO_CAP,
         'actual weekly finite watcher clamp')
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


def validate_armed_metadata(armed):
    need(armed.get('status')==ARM_STATUS and armed.get('thread_id')==THREAD
         and armed.get('native_release')is False and armed.get('guardian_packet_sha256')==PACKET_SHA,
         'actual weekly parent control receipt')
    caps=armed['caps']
    need(caps['boot_id']==BOOT_ID and (caps['deadline'],caps['monotonic_deadline'],caps['boot_deadline'])==(DEADLINE,MONO_CAP,BOOT_CAP),'actual weekly earliest finite caps')
    billing=armed['billing']
    need(billing['mode']=='included_only' and billing['credit_budget']is None and billing['automatic_credit_purchase']is False and billing['api_key_billing']is False and billing['account_wide_balance_guard']is False,'actual weekly receipt has no prepaid guard')
    row=armed['weekly_usage']
    validate_confirmed_row(row)
    need(armed['monitor_arm_sha256']==MONITOR_ARM_SHA and armed['phone_packet_sha256']==PHONE_PACKET_SHA,'actual weekly auxiliary publications')
    return armed


def validate_armed(armed, observe):
    validate_armed_metadata(armed)
    supervisor = observe(1311)
    need(supervisor is not None and supervisor.get('pid') == 1311
         and supervisor.get('start') == '596' and supervisor.get('ppid') == 1
         and supervisor.get('comm') == 'systemd' and supervisor.get('state') not in ('Z','X'),
         'actual measured auxiliary supervisor birth/name')
    expected = EXPECTED_ACTORS
    need(set(armed['actors']) == set(expected), 'actual parent control actors')
    for name, identity in expected.items():
        actor = armed['actors'][name]
        need((actor.get('pid'), actor.get('start')) == identity, 'actual parent actor '+name)
        live = observe(actor['pid'])
        # Auxiliary launch shells exited after recording their initial births.
        # Only the measured existing supervisor 1311 is an allowed reparent.
        if name in ('guardian', 'monitor', 'phone'):
            recorded = AUX_RECORDED_PPIDS
            need(actor['ppid'] == recorded[name], 'actual parent recorded auxiliary PPID '+name)
            parents = (1311,)
        else:
            parents = (actor['ppid'],)
        need(live is not None and live.get('state') not in ('Z','X')
             and (live.get('pid'), live.get('start')) == identity and live.get('ppid') in parents,
             'actual parent live actor '+name)
    return armed



AUTH_START=1793251609.1432834
WEEK_SECONDS=604800
ARM_STATUS = 'LIVE_CONFIRMED_QUOTA_SAME_WEEK_CONTROLS'

def require_live_binding():
    need(all(value is not None for value in (ARM_STATUS, ARM_RECEIPT_REF, CONFIG_SHA, PACKET_SHA, INITIAL, EXPECTED_ACTORS, GUARDIAN_LAUNCH_PPID, GUARDIAN_RECORDED_PPID, AUX_RECORDED_PPIDS, MONITOR_ARM_SHA, PHONE_PACKET_SHA)), "UNBOUND: genuine quota-confirmation arm/actors/publications required")

RESET=1793774133
WEEKLY_IDENTITY=dict(limit_id='codex',window_duration_mins=10080,resets_at=RESET)
MONITOR_ARM_SHA = '23c409cf4dfa8f3a9150945dbe53073526d4232c4207b8ac76c60a158451d2c6'
PHONE_PACKET_SHA = '8f55b85c80f8065897b149083ef5ddf81de955621347d71e499221e3e50fac6b'

class WeeklyWindowChanged(ValueError):
    pass


def weekly_row(limits, reset_at=RESET):
    if (type(reset_at) is not int or reset_at != RESET or not isinstance(limits, dict)
            or limits.get('limitId') != 'codex'):
        raise ValueError('authorized codex weekly limits required')
    rows=[]
    for name in ('primary','secondary'):
        row=limits.get(name)
        if isinstance(row,dict) and row.get('windowDurationMins') == 10080:
            rows.append((name,row))
    if len(rows)!=1:
        raise ValueError('one unambiguous weekly usage row required')
    name,row=rows[0];used=row.get('usedPercent');reset=row.get('resetsAt')
    if (type(row.get('windowDurationMins')) is not int or type(used) not in (int,float)
            or not math.isfinite(used) or not 0<=used<=100):
        raise ValueError('finite weekly usage required')
    # A valid 100% usage notification remains decisive even if reset metadata
    # itself is malformed; it cannot authorize further included inference.
    if type(reset) is not int and used<100:
        raise ValueError('reported weekly reset metadata required for confirmation')
    same_period=(type(reset) is int and reset-WEEK_SECONDS<=AUTH_START<reset)
    return dict(slot=name,usedPercent=used,windowDurationMins=10080,resetsAt=reset,
                canonicalResetsAt=RESET,authorizationStart=AUTH_START,sameAuthorizedPeriod=same_period)


def validate_confirmed_row(row):
    need(type(row) is dict, 'confirmed weekly usage required')
    parsed=weekly_row(dict(limitId='codex', **{row.get('slot','invalid'):dict(usedPercent=row.get('usedPercent'),windowDurationMins=row.get('windowDurationMins'),resetsAt=row.get('resetsAt'))}))
    need(parsed==row and parsed['sameAuthorizedPeriod'] and parsed['usedPercent']<100, 'confirmed same authorized period and unexhausted usage')
    return parsed


def validate_weekly_account(state,wall):
    # Reuse exact controller weekly_row; no account RPC or private account file.
    # state.credit_budget is retained historical data; only settings.billing is live.
    billing=(state.get('settings')or{}).get('billing')or{}
    need(billing.get('mode')=='included_only' and billing.get('credit_budget')is None
         and billing.get('automatic_credit_purchase')is False and billing.get('api_key_billing')is False
         and billing.get('account_wide_balance_guard')is False,'current included-only worker billing')
    row=validate_confirmed_row(state.get('weekly_confirmed_usage'))
    need(state.get('weekly_usage')==row and not state.get('weekly_confirmation_pending') and not state.get('weekly_usage_error'), 'fresh confirmation required; advisory metadata cannot grant admission')
    need(state.get('weekly_effective_boot_id')==BOOT_ID, 'confirmed quota boot identity')
    effective=[state.get('weekly_effective_end'),state.get('weekly_effective_monotonic_end'),state.get('weekly_effective_boot_end')]
    need(all(finite(x) and 0<x<=cap for x,cap in zip(effective,[RESET,1556236.568932019,1571574.6959790066])), 'confirmed quota ceilings may only tighten')
    need(wall<effective[0], 'confirmed earlier weekly end reached')
    need(state.get('weekly_usage_thread_id')==THREAD and state.get('weekly_usage_worker_pid')==INITIAL['worker'][0]
         and state.get('weekly_usage_worker_start')==INITIAL['worker'][1],'weekly account observation belongs to current worker/Root')
    age=wall-datetime.fromisoformat(state['weekly_usage_observation_at'].replace('Z','+00:00')).timestamp()
    need(0<=age<120,'weekly account observation unavailable or stale')
    return row


def validate_lease_rows(rows,subjects):
    for pid,device,inode in subjects:
        need(any(len(fields)>=8 and fields[1:4]==['FLOCK','ADVISORY','WRITE'] and fields[4]==str(pid)
                 and fields[5]==format(os.major(device),'02x')+':'+format(os.minor(device),'02x')+':'+str(inode)
                 and fields[6:8]==['0','EOF'] for fields in (line.split()for line in rows)),
             'actual dedicated auxiliary lease held by measured actor '+str(pid))
    return True


def validate_auxiliary_leases():
    paths=[(EXPECTED_ACTORS['guardian'][0],CONTROL/'armed-controller/bridge.lock'),
           (EXPECTED_ACTORS['monitor'][0],CONTROL/'twenty-minute-steering/supervisor.lock'),
           (EXPECTED_ACTORS['phone'][0],CAMPAIGN/'phone-control/watch.lock')]
    subjects=[]
    for pid,path in paths:
        st=path.stat();subjects.append((pid,st.st_dev,st.st_ino))
    return validate_lease_rows(Path('/proc/locks').read_text().splitlines(),subjects)

def guard():
    require_live_binding()
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
    validate_auxiliary_leases()
    return validate(json.loads(window_raw), read(CONTROL / 'armed-controller/journal.json'),
                    read(CONTROL / 'armed-controller/bridge-start.json'), read(CAMPAIGN / 'state.json'),
                    read(CAMPAIGN / 'watcher.json'), birth,
                    [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)],
                    Path('/proc/sys/kernel/random/boot_id').read_text().strip(), json.loads(receipt_raw))
