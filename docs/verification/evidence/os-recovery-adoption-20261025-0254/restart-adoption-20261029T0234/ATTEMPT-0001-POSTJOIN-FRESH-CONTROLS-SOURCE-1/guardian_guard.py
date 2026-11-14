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
import stat

BASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1')
PARENT_CONTROL = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1')
CONTROL = PARENT_CONTROL / 'attempt-0001'
ARM_RECEIPT_REF = {'path': str(CONTROL / 'ACTUAL-CONTROLS-ARMED.json'), 'bytes': 1226, 'sha256': '4ff25cbf4135e78c58d973bd3f22c4fc7f305e96cb37bc620ebff0c617cf2db2'}
CONFIG_SHA = '15749406bc63e9cfc0f976b8b7433c2e18caad82865766c1a61becfc6d7e9a5c'
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
PACKET_SHA = '218fcd01f401826e942512b68718d7b990b3e0bebda06fcf7c1f1bbcdcb6e0b1'
WINDOW_SHA = 'c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
THREAD = '01a18a76-4f1e-7900-8ed6-127394e93689'
DEADLINE = 1793774133
WINDOW_BOOT_CAP = 1571576.6960040887
JOURNAL_BOOT_CAP = 1571572.6959598332
BOOT_CAP = 1571572.6959598332
MONO_CAP = 1556234.56891299
BOOT_ID = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
INITIAL = {'watcher': (2659029, '112181497'), 'worker': (2659031, '112181511'), 'server': (2659033, '112181528')}
EXPECTED_ACTORS = {'watcher': (2659029, '112181497', 2526816), 'worker': (2659031, '112181511', 2659029), 'server': (2659033, '112181528', 2659031), 'guardian': (2659144, '112181699', 2526816), 'monitor': (2659146, '112181810', 2526816)}
SUPERVISOR = (2526816, '109909996', 1311)
PHONE = (2526610, '109904364', 1311)



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


def read_fresh(path, now, max_age, opener=os.open):
    """Read one regular inode and its own freshness, reject replacement or mutation."""
    fd=opener(str(path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 <= now-before.st_mtime < max_age, 'stale/future or nonregular activity file')
        chunks=[]; total=0
        while True:
            part=os.read(fd,65536)
            if not part: break
            total += len(part); need(total <= 1 << 20, 'activity metadata cap');chunks.append(part)
        after=os.fstat(fd); current=os.stat(path,follow_symlinks=False)
        signature=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
        need(signature(before)==signature(after)==signature(current), 'activity file replaced or mutated')
        return json.loads(b''.join(chunks))
    finally:
        os.close(fd)


def validate_controller_journals(supervisor, guardian, monitor, now):
    need(supervisor.get('status') == 'armed' and supervisor.get('source_packet_sha256') == '15b838961836117a97ddd04269a01a055d733636bf2d5fa3f1d5ce5391ecfeae', 'supervisor persisted status/packet')
    envelope=supervisor.get('current_envelope') or {}
    need(envelope.get('thread_id')==THREAD and envelope.get('directory')==str(CONTROL)
         and envelope.get('guardian_dir')==str(CONTROL/'armed-controller') and envelope.get('monitor_dir')==str(CONTROL/'twenty-minute-steering')
         and envelope.get('guardian_packet_sha256')==PACKET_SHA and envelope.get('monitor_arm_sha256')==MONITOR_ARM_SHA
         and envelope.get('model')=='gpt-6.1-terra', 'supervisor current envelope')
    bindings=envelope.get('binding') or {};need(set(bindings)==set(EXPECTED_ACTORS), 'supervisor exact actor set')
    for name,identity in EXPECTED_ACTORS.items():
        actor=bindings[name];need((actor.get('pid'),actor.get('start'),actor.get('ppid'))==identity, 'supervisor actor '+name)
    attempts=supervisor.get('attempts');need(type(attempts) is list and attempts and attempts[-1].get('status')=='healthy_envelope'
         and attempts[-1].get('thread_id')==THREAD and attempts[-1].get('directory')==str(CONTROL), 'supervisor current attempt health')
    for row in attempts+list((supervisor.get('child_requests') or {}).values()):
        need(row.get('status') not in ('intent','uncertain','sending','delivery_uncertain'), 'supervisor uncertain operation')
    need(guardian.get('packet_sha256')==PACKET_SHA and guardian.get('boot_id')==BOOT_ID
         and guardian.get('last_action')=='WAIT_RESIDENT_UNCHANGED' and finite(guardian.get('last_clock'))
         and 0 <= now-guardian['last_clock'] < 30, 'guardian finite fresh loop')
    need(not any(guardian.get(k) for k in ('transition_hold','stop_intent','deadline_stop_sent','credit_started')), 'guardian holds')
    need(monitor.get('thread_id')==THREAD and monitor.get('arm_binding_sha256')==MONITOR_ARM_SHA
         and monitor.get('guardian_packet_sha256')==PACKET_SHA and monitor.get('boot_id')==BOOT_ID
         and monitor.get('status')=='queued', 'monitor current healthy loop')
    caps=supervisor.get('caps') or {};need(caps.get('boot_id')==BOOT_ID, 'supervisor boot identity')
    triples=[(caps.get('deadline'),caps.get('monotonic_deadline'),caps.get('boot_deadline')),
             (guardian.get('deadline'),guardian.get('finite_watcher_monotonic_deadline'),guardian.get('boot_deadline')),
             (monitor.get('deadline'),MONO_CAP,monitor.get('boot_deadline'))]
    limits=(DEADLINE,MONO_CAP,BOOT_CAP)
    for row in triples:
        need(all(finite(x) and 0 < x <= cap for x,cap in zip(row,limits)), 'valid current caps')
    weekly=supervisor.get('weekly_effective_end');need(finite(weekly) and 0 < weekly <= DEADLINE, 'supervisor weekly ceiling')
    return tuple(min(*(row[i] for row in triples), limits[i], weekly if i==0 else limits[i]) for i in range(3))


def live_journals(now):
    # Producer loops: 5s supervisor/guardian, 15s monitor. Three missed intervals hold.
    supervisor=read_fresh(PARENT_CONTROL/'journal.json',now,30)
    guardian=read_fresh(CONTROL/'armed-controller/journal.json',now,30)
    monitor=read_fresh(CONTROL/'twenty-minute-steering/journal.json',now,45)
    return supervisor,guardian,monitor,validate_controller_journals(supervisor,guardian,monitor,now)


def current_caps():
    return live_journals(time.time())[3]


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
    need(live is not None and all(live.get(k) == owner.get(k) == armed['binding']['guardian'].get(k) for k in ('pid', 'start'))
         and live.get('state') not in ('Z', 'X') and owner.get('ppid') == SUPERVISOR[0], 'guardian receipt live birth')
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
    need(armed.get('thread_id') == THREAD and armed.get('native_release') is False
         and armed.get('guardian_packet_sha256') == PACKET_SHA and armed.get('monitor_arm_sha256') == MONITOR_ARM_SHA,
         'actual current control receipt')
    caps = armed['caps']
    need(caps['boot_id'] == BOOT_ID and (caps['deadline'], caps['monotonic_deadline'], caps['boot_deadline']) == (DEADLINE, MONO_CAP, BOOT_CAP), 'current earliest caps')
    need(set(armed['binding']) == set(EXPECTED_ACTORS), 'exact current actors')
    for name, identity in EXPECTED_ACTORS.items():
        row = armed['binding'][name]
        need((row.get('pid'), row.get('start'), row.get('ppid')) == identity, 'recorded actor '+name)
    return armed


def validate_armed(armed, observe):
    validate_armed_metadata(armed)
    for name, identity in list(EXPECTED_ACTORS.items()) + [('capacity-supervisor', SUPERVISOR), ('phone', PHONE)]:
        live = observe(identity[0])
        need(live is not None and live.get('state') not in ('Z','X') and
             (live.get('pid'), live.get('start'), live.get('ppid')) == identity, 'live actor '+name)
    return armed



AUTH_START=1793251609.1432834
WEEK_SECONDS=604800
ARM_STATUS = 'LIVE_CONFIRMED_QUOTA_SAME_WEEK_CONTROLS'

def require_live_binding():
    need(all(value is not None for value in (ARM_RECEIPT_REF, CONFIG_SHA, PACKET_SHA, INITIAL, EXPECTED_ACTORS, MONITOR_ARM_SHA, PHONE_PACKET_SHA)), 'unbound current controls')

RESET=1793774133
WEEKLY_IDENTITY=dict(limit_id='codex',window_duration_mins=10080,resets_at=RESET)
MONITOR_ARM_SHA = '151d1484b1812012dcefc3cfb7cd4a498aad908c12820919d606997f4af633d6'
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
    paths=[(SUPERVISOR[0], PARENT_CONTROL/'supervisor.lock', 1211448),
           (EXPECTED_ACTORS['guardian'][0], CONTROL/'armed-controller/bridge.lock', 1214726),
           (EXPECTED_ACTORS['monitor'][0], CONTROL/'twenty-minute-steering/supervisor.lock', 1214735),
           (PHONE[0], CAMPAIGN/'phone-control/watch.lock', 47586630)]
    subjects=[]
    for pid,path,inode in paths:
        st=path.stat()
        need(inode is None or st.st_ino == inode, 'exact auxiliary lease inode')
        subjects.append((pid,st.st_dev,st.st_ino))
    return validate_lease_rows(Path('/proc/locks').read_text().splitlines(),subjects)


def validate_auxiliary_argv(read_argv):
    # taskset execs the recorded Python argv after its three-element prefix.
    entries = [(SUPERVISOR[0], PARENT_CONTROL/'CAPACITY-ARM-LAUNCH-INTENT.json', '6c4510ea38f0399f119f66069f547f8068a48d3853bd24df4013c4417c9b4fbe'),
               (EXPECTED_ACTORS['guardian'][0], CONTROL/'guardian-LAUNCH-INTENT.json', '85c6d5d24a0bbf3142347573d1db20c40028bcba1a082390652e46d1f192e48e'),
               (EXPECTED_ACTORS['monitor'][0], CONTROL/'monitor-LAUNCH-INTENT.json', 'cf8765733e940af0374d427ea141d0f16af77d30d410611868c8557ba9d227cd'),
               (PHONE[0], PARENT_CONTROL/'phone-window-adapter/ARM-LAUNCH-INTENT.json', 'b8ad23b06a5d17fd20c25733e7893d57be59432e2c8989548b321cb4c88193d6')]
    for pid, path, sha in entries:
        content=raw(path)
        need(hashlib.sha256(content).hexdigest()==sha, 'exact recorded launch intent')
        argv=json.loads(content)['argv']
        need(argv[:3]==['/usr/bin/taskset','-c','0'] and read_argv(pid)==argv[3:], 'actual auxiliary argv '+str(pid))
    return True


def actual_argv(pid):
    raw_argv=(Path('/proc')/str(pid)/'cmdline').read_bytes()
    need(raw_argv.endswith(b'\0'), 'complete proc argv')
    return [part.decode('utf-8') for part in raw_argv[:-1].split(b'\0')]


def validate_monitor_phone(monitor, monitor_journal, phone, phone_age):
    need(monitor.get('pid') == EXPECTED_ACTORS['monitor'][0] and monitor.get('start_ticks') == EXPECTED_ACTORS['monitor'][1]
         and monitor.get('thread_id') == THREAD and monitor.get('arm_binding_sha256') == MONITOR_ARM_SHA
         and monitor.get('guardian_packet_sha256') == PACKET_SHA and monitor.get('interval_seconds') == 1200, 'current monitor publication')
    need(monitor_journal.get('thread_id') == THREAD and monitor_journal.get('arm_binding_sha256') == MONITOR_ARM_SHA
         and monitor_journal.get('guardian_packet_sha256') == PACKET_SHA and monitor_journal.get('status') == 'queued'
         and monitor_journal.get('boot_id') == BOOT_ID and finite(monitor_journal.get('boot_deadline')) and 0 < monitor_journal.get('boot_deadline') <= BOOT_CAP,
         'monitor current queue and cap')
    need(phone.get('owner') == {'pid': PHONE[0], 'starttime': int(PHONE[1])} and phone.get('phase') == 'running'
         and phone.get('last_error') is None and phone.get('boot_id') == BOOT_ID and phone.get('deadline_epoch') == DEADLINE
         and phone.get('window_sha256') == WINDOW_SHA and phone.get('interval') == 60.0
         and 0 <= phone_age < 180, 'retained phone status/heartbeat')
    return True

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
    phone_dir = PARENT_CONTROL / 'phone-window-adapter'
    phone_packet_raw = raw(phone_dir / 'PHONE-PACKET.json')
    need(hashlib.sha256(phone_packet_raw).hexdigest() == PHONE_PACKET_SHA, 'exact retained phone packet')
    phone_packet = json.loads(phone_packet_raw)
    for name, sha in phone_packet['private'].items():
        need(hashlib.sha256(raw(phone_dir / name)).hexdigest() == sha, 'phone private bytes '+name)
    need(hashlib.sha256(raw(Path('/home/holden/mckernel/scripts/os_phone_instructions.py'))).hexdigest() == phone_packet['canonical_phone_sha256'], 'canonical phone bytes')
    monitor_source = CONTROL / 'twenty-minute-steering/steer_every_twenty_minutes.py'
    need(hashlib.sha256(raw(monitor_source)).hexdigest() == 'fc9d95c04da6f7bb7a51e9348e6162c0be96ee277803d1cfe44dccab9663e0f2', 'exact current monitor source')
    need(hashlib.sha256(raw(PARENT_CONTROL / 'capacity_supervisor.py')).hexdigest() == 'efcf6ee1a1a7766044e0585f021c01648027b76fc64a10cff72d63af66f9ef59', 'exact capacity supervisor source')
    need(not any((PARENT_CONTROL / n).exists() for n in ('STOP.json','HOLD.json','DRAIN-HOLD.json')) and not (CONTROL / 'twenty-minute-steering/stop-request.json').exists(), 'supervisor or monitor stop/hold requested')
    validate_auxiliary_argv(actual_argv)
    validate_auxiliary_leases()
    now=time.time()
    _,guardian_journal,monitor_journal,dynamic_caps=live_journals(now)
    phone=read_fresh(CAMPAIGN / 'phone-control/watch-status.json',now,180)
    validate_monitor_phone(read(CONTROL / 'twenty-minute-steering/supervisor.json'), monitor_journal, phone, 0)
    result=validate(json.loads(window_raw), guardian_journal,
                    read(CONTROL / 'armed-controller/bridge-start.json'), read(CAMPAIGN / 'state.json'),
                    read(CAMPAIGN / 'watcher.json'), birth,
                    [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)],
                    Path('/proc/sys/kernel/random/boot_id').read_text().strip(), json.loads(receipt_raw))
    need(all(now < cap for now,cap in zip(result,dynamic_caps)), 'current controller dynamic minimum reached')
    return result
