"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reminder stop contracts and existing-queue integration in a temporary directory.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
from foreground_reminder import decision, load_queue, INTERVAL, LAUNCHER


def run():
    now = datetime.fromisoformat('2026-10-30T03:45:00+00:00').timestamp()
    state = dict(thread_id='target', phase='running', goal=dict(status='active'),
                 heartbeat_at='2026-10-30T03:45:00+00:00', settings=dict(billing=dict(mode='included_only')),
                 weekly_usage=dict(windowDurationMins=10080, canonicalResetsAt=1793774133,
                                   sameAuthorizedPeriod=True, usedPercent=54))
    config = dict(target_thread='target', caps=dict(deadline=now+10000, boot_id='boot',
                  boot_deadline=10000, monotonic_deadline=10000))
    check = lambda value, wall=now, boot=1, mono=1: decision(value, config, wall, boot, mono, 'boot')
    assert INTERVAL == 15 * 60 and check(state) == 'ready'
    for key in ('service_hold','policy_hold','auth_hold','billing_hold','last_error','last_failure','transport_uncertain'):
        assert check(dict(state, **{key: True})).startswith('stop:')
    assert check(dict(state, phase='stopped')).startswith('stop:')
    assert check(dict(state, goal=dict(status='paused'))).startswith('stop:')
    assert check(dict(state, thread_id='other')).startswith('stop:')
    assert check(state, wall=now+10000).startswith('stop:')
    assert check(state, boot=10000).startswith('stop:')
    assert check(state, mono=10000).startswith('stop:')
    for value in (100, 101, None, float('nan')):
        row = deepcopy(state); row['weekly_usage']['usedPercent'] = value
        assert check(row).startswith('stop:')
    assert check(dict(state, weekly_effective_boot_end=1)).startswith('stop:')
    assert check(dict(state, weekly_confirmation_pending=True)).startswith('wait:')
    assert check(dict(state, heartbeat_at='2026-10-30T03:40:00+00:00')).startswith('wait:')
    # The actual existing queue helper must create one ordinary pending message,
    # without importing/starting the launcher, RPC or campaign execution.
    queue = load_queue(hashlib.sha256(LAUNCHER.read_bytes()).hexdigest())
    with tempfile.TemporaryDirectory(prefix='mckernel-reminder-queue-test-') as temporary:
        directory = Path(temporary)
        (directory/'state.json').write_text(json.dumps(state))
        before = (directory/'state.json').read_bytes()
        ident = queue(directory, 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Test reminder.')
        pending = list((directory/'instructions/pending').glob('*.json'))
        assert len(pending) == 1 and pending[0].stem == ident
        assert json.loads(pending[0].read_bytes())['id'] == ident
        assert (directory/'state.json').read_bytes() == before
    print('PASS_REMINDER_CADENCE_STOP_GATES_AND_EXISTING_QUEUE_INTEGRATION')


if __name__ == '__main__':
    run()
