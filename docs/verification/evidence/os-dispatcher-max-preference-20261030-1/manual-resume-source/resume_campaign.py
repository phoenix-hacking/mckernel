"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Explicit one-shot same-thread manual resume. Reuse the existing finite watcher,
weekly quota policy, guardian, steering monitor and typed capacity supervisor.
Never edits stopped state, resets credit, performs native cleanup, or replays a
rejected request. All process submissions retain intent and actual identities.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')
CAMPAIGN = REPO / '.git/os-autopilot'
sys.path.insert(0, str(HERE))
import capacity_supervisor as s
from readiness import fresh_heartbeat, live_guardian
from manual_policy import manual_blocked_ready, tightest_caps, phone_matches, require
from prepare_resume import lease_free, select_routing
sys.path.insert(0, str(REPO / 'scripts'))
from run_os_goal import RPC


def verify(expected):
    raw = (HERE / 'RESUME-SOURCE-PACKET.json').read_bytes()
    if s.digest(raw) != expected:
        raise ValueError('manual resume source packet changed')
    packet = json.loads(raw)
    for name, digest in packet['private'].items():
        path = HERE / name
        if HERE not in path.resolve().parents or s.digest(path.read_bytes()) != digest:
            raise ValueError('reviewed manual source changed: ' + name)
    required={'PREPARED-RESUME.json','STOPPED-STATE.json','PREFLIGHT.json','RETIRED-CONTROLLER-OBSERVATIONS.json','PRIOR-ENVELOPE.json','RETAINED-CREDIT-LEDGER.json','REJECTED-REQUEST.json','MODEL-CATALOG.json','PHONE-OBSERVATION.json','INHERITED-SOURCE-REFS.json','resume_campaign.py','prepare_resume.py','manual_policy.py','manual_arm.py','readiness.py','capacity_rules.py','capacity_supervisor.py','catalog_probe.py','guardian_template.py','finite_launcher_template.py','steering_template.py','weekly_policy.py','ENGINEERING-HANDOFF.md','bootstrap/FROZEN-PACKET.json','bootstrap/CONFIG.json','bootstrap/CURRENT-INVOCATION.txt','bootstrap/bridge.py','bootstrap/finite_launcher.py','bootstrap/weekly_policy.py'}
    if not required <= set(packet['private']):
        raise ValueError('manual source packet lacks complete prepared source set')
    prepared = s.read(HERE / 'PREPARED-RESUME.json')
    for name, expected_support in prepared['canonical_support'].items():
        if Path(name).name != name or s.digest((REPO/'scripts'/name).read_bytes()) != expected_support:
            raise ValueError('canonical supporting source changed: '+name)
    for path, expected_prior in s.read(HERE/'INHERITED-SOURCE-REFS.json').items():
        if s.digest(Path(path).read_bytes()) != expected_prior:
            raise ValueError('inherited cap/monitor source changed: '+path)
    for name, digest in prepared['canonical'].items():
        if s.digest((REPO / 'scripts' / name).read_bytes()) != digest:
            raise ValueError('canonical source changed: ' + name)
    spec = importlib.util.spec_from_file_location('manual_resume_bootstrap', HERE / 'bootstrap/bridge.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify_packet(prepared['bootstrap_sha256'])
    return packet, prepared


def phone_live(phone, observed):
    retained = phone.get('owner') or {}
    value = retained.get('starttime')
    if not ((type(value) is int and value > 0) or
            (type(value) is str and value.isdigit() and int(value) > 0)):
        return False
    return bool(observed is not None and observed.get('pid') == retained.get('pid')
                and observed.get('start') == str(value) and observed.get('state') not in ('Z', 'X')
                and phone.get('phase') == 'running')


def readonly_preflight(prepared):
    original = (HERE / 'STOPPED-STATE.json').read_bytes()
    if (CAMPAIGN / 'state.json').read_bytes() != original:
        raise ValueError('saved stopped state changed; re-review before resume')
    state = json.loads(original)
    if not s.no_holds(state) or not s.instructions_clear():
        raise ValueError('explicit or uncertain account/instruction hold')
    old = s.read(HERE / 'RETIRED-CONTROLLER-OBSERVATIONS.json')
    for name, row in old.items():
        retained = row['retained']
        actual = s.birth(retained['pid'])
        if actual is not None and actual['start'] == retained['start']:
            raise ValueError('old controller identity still present: ' + name)
    if not all(lease_free(Path(name)) for name in s.read(HERE/'PREFLIGHT.json')['leases']):
        raise ValueError('core lease is owned; never unlink it')
    if s.remaining(prepared['caps'], *s.clocks(), s.boot_id()) <= 120:
        raise ValueError('weekly operational ceiling reached')
    if (CAMPAIGN / 'credit-runs' / (s.CREDIT + '.json')).read_bytes() != (HERE / 'RETAINED-CREDIT-LEDGER.json').read_bytes():
        raise ValueError('historical ledger changed; reconcile it')
    directory = HERE / 'runtime-preflight'
    directory.mkdir()
    rpc = RPC(['/home/holden/.local/bin/codex', '-C', str(REPO), 'app-server', '--stdio'], directory, lambda event: None)
    try:
        rpc.call('initialize', {'clientInfo': {'name': 'mckernel-explicit-manual-resume', 'version': '1.0'},
                                'capabilities': {'experimentalApi': True}}, timeout=15)
        rpc.send({'method': 'initialized', 'params': {}})
        account = rpc.call('account/read', {'refreshToken': False}, timeout=15).get('account') or {}
        limits = rpc.call('account/rateLimits/read', {}, timeout=15)['rateLimits']
        weekly = limits.get('primary') or {}
        if (account.get('type') != 'chatgpt' or limits.get('limitId') != 'codex'
                or limits.get('spendControlReached') or limits.get('rateLimitReachedType')
                or weekly.get('windowDurationMins') != 10080 or weekly.get('resetsAt') != s.DEADLINE
                or type(weekly.get('usedPercent')) not in (int, float) or not 0 <= weekly['usedPercent'] < 100):
            raise ValueError('fresh weekly account proof failed')
        goal = rpc.call('thread/goal/get', {'threadId': prepared['root']}, timeout=15)['goal']
        turns = rpc.call('thread/turns/list', {'threadId': prepared['root'], 'limit': 1,
                      'sortDirection': 'desc', 'itemsView': 'notLoaded'}, timeout=15)['data']
        manual_blocked_ready(state, goal, turns)
        from catalog_probe import model_rows
        live_catalog={'models':model_rows(rpc.call('model/list', {}, timeout=15)['data'])}
        selected,routing,_=select_routing(live_catalog)
        if selected != dict(model=prepared['target_model'], effort=prepared['target_effort']) or routing != prepared['initial_routing']:
            raise ValueError('advertised selected routing changed; prepare/review a fresh envelope')
        s.create(directory / 'OBSERVATION.json', dict(scope=s.SCOPE, at=time.time(),
                 goal=goal, turns=turns, rate_limits=limits, native_clearance=False))
    finally:
        rpc.close()
    phone = s.read(CAMPAIGN / 'phone-control/watch-status.json')
    now = s.birth(phone['owner']['pid'])
    phone_matches(phone, now, prepared['prior_config'], s.read(HERE/'PHONE-OBSERVATION.json')['state'])
    s.create(HERE / 'RETAINED-LIVE-PHONE.json', dict(observed_at=time.time(), state=phone, identity=now))
    return state


def start(expected, review_path):
    packet, prepared = verify(expected)
    review = s.read(review_path)
    if review.get('status') != 'PASS_MANUAL_RESUME_SOURCE' or review.get('source_packet_sha256') != expected:
        raise ValueError('exact independent manual resume review is required')
    if (HERE / 'watcher-LAUNCH-INTENT.json').exists() or (HERE / 'HOLD.json').exists():
        raise ValueError('one-shot resume already has intent or hold; inspect, never replay')
    stopped = readonly_preflight(prepared)
    verify(expected)
    if (CAMPAIGN / 'state.json').read_bytes() != (HERE / 'STOPPED-STATE.json').read_bytes():
        raise ValueError('stopped state changed immediately before submission')
    # Complete fallible bookkeeping BEFORE submission; own every later exception.
    journal = dict(status='manual_resume_arming', caps=prepared['caps'], current_envelope=s.read(HERE / 'PRIOR-ENVELOPE.json'),
                   credit_spent_floor=json.loads((HERE / 'RETAINED-CREDIT-LEDGER.json').read_bytes())['spent'],
                   attempts=[dict(status='manual_submission_pending', directory=str(HERE), model=prepared['target_model'],
                                  at=time.time(), explicit_user_resume=True)],
                   child_requests={}, failures={})
    watcher = None
    try:
        watcher = s.spawn(prepared['argv'], HERE, 'watcher')
        journal['attempts'][0].update(status='manual_watcher_started', watcher=watcher)
        s.atomic(HERE / 'journal.json', journal)
        until = time.monotonic() + 120
        bound_model = None
        while True:
            s.reap_children()
            state = s.read(CAMPAIGN / 'state.json')
            candidate = {key: state.get(key) for key in ('worker_pid','worker_start','server_pid','server_start')}
            complete = (candidate['worker_pid'] != stopped['worker_pid']
                        and all(type(candidate[key]) is int and candidate[key] > 0 for key in ('worker_pid','server_pid'))
                        and all(type(candidate[key]) is str and candidate[key].isdigit() for key in ('worker_start','server_start')))
            if complete:
                if bound_model is None:
                    bound_model = candidate
                elif candidate != bound_model:
                    raise ValueError('new manual model identities changed while awaiting heartbeat')
            if state.get('worker_pid') != stopped['worker_pid'] and state.get('phase') == 'stopped':
                raise ValueError('new manual worker stopped; preserve its new error without retry')
            if (state.get('phase') == 'running' and (state.get('goal') or {}).get('status') == 'active'
                    and (HERE / 'bootstrap/initial-watch-clock.json').exists()
                    and bound_model is not None
                    and fresh_heartbeat(state, journal['attempts'][0]['at'], time.time(), bound_model)):
                break
            if time.monotonic() >= until:
                raise ValueError('new same-thread worker not positively active within arm interval')
            time.sleep(1)
        if state['thread_id'] != prepared['root'] or not s.no_holds(state):
            raise ValueError('resumed Root or hold binding changed')
        if state['settings']['model'] != prepared['target_model'] or state['settings']['effort'] != prepared['target_effort']:
            raise ValueError('actual dispatcher model/effort differs from explicit user target')
        if state['settings'].get('model_routing') != prepared['initial_routing'] or state['settings'].get('agents') != prepared['initial_agent_settings']:
            raise ValueError('actual independent lower worker routing/settings differ')
        effective = state.get('effective_permissions') or {}
        if effective.get('sandbox', {}).get('type') != 'dangerFullAccess' or effective.get('approval_policy') != 'never':
            raise ValueError('resumed thread permissions differ')
        config = prepared['prior_config']
        config['caps'] = prepared['caps']
        from manual_arm import arm_manual_same_thread
        arm_manual_same_thread(config, dict(canonical=prepared['canonical']), journal, HERE, watcher,
                          prepared['bootstrap_sha256'], (HERE / 'bootstrap/CURRENT-INVOCATION.txt').read_bytes(),
                          s.read(HERE / 'MODEL-CATALOG.json'), prepared['target_model'])
        config.update(initial_envelope=journal['current_envelope'], initial_model=prepared['target_model'],
                      caps=journal['caps'], user_authorization='Explicit same-Root user resume; rejected generic_c request remains held; typed capacity fallback only.',
                      credit_spent_floor=journal['credit_spent_floor'])
        s.create(HERE / 'CONFIG.json', config)
        capacity_packet = dict(scope=s.SCOPE, status='SEALED_MANUAL_SAME_ROOT_INCLUDED_ONLY', canonical=prepared['canonical'],
                          private={name: s.digest((HERE / name).read_bytes()) for name in s.PRIVATE})
        csha = s.create(HERE / 'SOURCE-PACKET.json', capacity_packet)
        s.check_packet(HERE / 'SOURCE-PACKET.json', csha)
        journal.update(status='armed', source_packet_sha256=csha)
        s.atomic(HERE / 'journal.json', journal)
        capacity = s.spawn(['/usr/bin/taskset','-c','0',s.PYTHON,'-B',str(HERE / 'capacity_supervisor.py'),
                            '--run','--packet-sha256',csha], HERE, 'capacity')
        until = time.monotonic() + 20
        while True:
            s.reap_children()
            if (HERE / 'supervisor.json').exists() and not s.free_lease(HERE / 'supervisor.lock'):
                actual = s.read(HERE / 'supervisor.json')
                if actual.get('pid') == capacity['pid'] and actual['birth']['start'] == capacity['start']:
                    break
            if time.monotonic() >= until:
                raise ValueError('capacity supervisor did not acquire its exclusive lease')
            time.sleep(1)
        state = s.read(CAMPAIGN / 'state.json')
        s.live_binding(journal['current_envelope'], state)
        if state['phase'] != 'running' or state['goal']['status'] != 'active' or not s.no_holds(state):
            raise ValueError('campaign stopped before final activation receipt')
        s.create(HERE / 'ACTUAL-CAPACITY-FALLBACK-ARMED.json', dict(scope=s.SCOPE, status='PASS_ACTUAL_MANUAL_SAME_ROOT_RESUME',
              thread_id=state['thread_id'], binding=journal['current_envelope']['binding'], supervisor=capacity,
              source_packet_sha256=csha, manual_source_packet_sha256=expected, caps=journal['caps'],
              same_thread=True, billing_mode='included_only', generic_c_request_still_held=True,
              weekly_usage=state.get('weekly_usage'), native_release=False, at=time.time()))
        print(json.dumps(dict(status='CAMPAIGN_RESTARTED_CONTROLS_ARMED', thread_id=state['thread_id'],
               weekly_usage=state.get('weekly_usage'), evidence=str(HERE))), flush=True)
        while s.DIRECT_CHILDREN:
            s.reap_children()
            time.sleep(5)
    except Exception as error:
        # Reporting failure must never suppress retirement of submitted actors.
        try:
            s.create(HERE / 'HOLD.json', dict(scope=s.SCOPE, error_type=type(error).__name__, message=str(error),
                     at=time.time(), automatic_retry=False, native_release=False))
        except Exception as report_error:
            print('Manual resume HOLD publication failed: ' + repr(report_error), flush=True)
        try:
            drain_manual_envelope(journal, watcher, prepared)
        except Exception as drain_error:
            try:
                s.create(HERE / 'DRAIN-HOLD.json', dict(error_type=type(drain_error).__name__,
                         message=str(drain_error), at=time.time(), automatic_retry=False))
            except Exception:
                pass
            print('Manual resume retirement unresolved: ' + repr(drain_error), flush=True)
        raise


def drain_manual_envelope(journal, watcher, prepared):
    # spawn() registers its direct Popen BEFORE birth/receipt publication. Recover
    # that actual child if publication failed, instead of trusting a missing return.
    owned = [(child, directory, label) for child, directory, label in s.DIRECT_CHILDREN.values()
             if directory == HERE and label == 'watcher']
    if watcher is None:
        if not owned:
            return  # Submission did not create a known direct process.
        if len(owned) != 1:
            raise ValueError('ambiguous submitted watcher; preserve all direct handles')
        child = owned[0][0]
        if child.poll() is not None:
            s.reap_children()
            return
        watcher = s.birth(child.pid)
        if watcher is None or watcher['ppid'] != os.getpid():
            raise ValueError('submitted watcher birth/parent cannot be positively recovered')
    envelope = journal['current_envelope']
    if envelope.get('directory') == str(HERE):
        guard = envelope['binding']['guardian']
        actual = None if guard.get('not_started') else s.birth(guard['pid'])
        if not live_guardian(guard, actual):
            # A dead/zombie guardian cannot receive the stop. The unchanged
            # drain then uses its existing exact bound-worker pidfd fallback.
            envelope = dict(envelope, binding=dict(envelope['binding'], guardian=dict(not_started=True)))
        s.drain(envelope, 'manual_resume_partial_arm_hold')
        return
    # Before auxiliary publication, stop the exact direct watcher through pidfd.
    # Its canonical normal-finally path retires only its model worker/server.
    spec = importlib.util.spec_from_file_location('manual_exact_watcher_stop', HERE / 'guardian_template.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual = s.birth(watcher['pid'])
    if actual is None:
        s.reap_children()
        return
    if actual['start'] != watcher['start'] or actual['ppid'] != os.getpid():
        raise ValueError('submitted watcher identity changed; no signal')
    fd = module.pidfd_open(watcher['pid'])
    try:
        actual = s.birth(watcher['pid'])
        if actual is None or actual['start'] != watcher['start'] or actual['ppid'] != os.getpid():
            raise ValueError('submitted watcher changed after pidfd acquisition; no signal')
        import signal
        module.pidfd_send_signal(fd, signal.SIGTERM)
    finally:
        os.close(fd)
    until = time.monotonic() + 60
    while True:
        s.reap_children()
        actual = s.birth(watcher['pid'])
        state = s.read(CAMPAIGN / 'state.json')
        live_models = []
        if state.get('thread_id') == prepared['root'] and state.get('worker_pid') != json.loads((HERE / 'STOPPED-STATE.json').read_bytes())['worker_pid']:
            for role in ('worker', 'server'):
                if type(state.get(role + '_pid')) is int:
                    current = s.birth(state[role + '_pid'])
                    if current is not None and current['start'] == state.get(role + '_start'):
                        live_models.append(current)
        if (actual is None or actual['start'] != watcher['start']) and not live_models:
            return
        if time.monotonic() >= until:
            raise ValueError('submitted watcher/model retirement unresolved; preserve, never retry')
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--review', type=Path)
    args = parser.parse_args()
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise ValueError('ordinary UID1000 required')
    if not args.run:
        verify(args.source_sha256)
        print('PASS_SOURCE_ONLY_NO_RUNTIME')
        return
    if args.review is None:
        parser.error('--run requires the exact independent review receipt')
    start(args.source_sha256, args.review)


if __name__ == '__main__':
    main()
