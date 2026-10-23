#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Queue engineering review requests for the existing running dispatcher only.
No app server, inference, workload, root command, resume or restart is invoked.
"""
import argparse
import ast
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import uuid

THREAD = '01a166a8-28f9-7882-9c7c-ffb216a4ee45'
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
LAUNCHER = Path('/home/holden/mckernel/scripts/run_os_goal.py')
OUTPUT = Path(__file__).resolve().parent
INTERVAL = 600
HEARTBEAT_MAX_AGE = 120
STATE_CAP = 1 << 20
TAIL_CAP = 8192
EVENT_CAP = 1 << 20
MARKER = '[ten-minute-engineering-review-v1]'


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def read_json(path, maximum=STATE_CAP):
    with path.open('rb') as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > maximum:
            raise ValueError('nonregular or oversized JSON: ' + str(path))
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('JSON cap exceeded')
    return json.loads(raw)


def atomic(path, value):
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temp.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def decision(state, journal, now, backlog):
    """Pure stop/due decision; stale or held campaigns are never retried."""
    if state.get('thread_id') != THREAD:
        return 'stop:thread_changed'
    if state.get('phase') != 'running':
        return 'stop:phase_' + str(state.get('phase'))
    goal = state.get('goal') or {}
    if goal.get('status') != 'active' or goal.get('threadId', THREAD) != THREAD:
        return 'stop:goal_not_active'
    if state.get('stop_reason') or state.get('policy_hold') or state.get('service_hold'):
        return 'stop:held'
    # A historical serverOverloaded record is not a live hold. A policy error
    # is never used as a reason to queue another automatic instruction.
    error = state.get('last_error') or {}
    if isinstance(error, dict) and error.get('codexErrorInfo') == 'cyberPolicy':
        return 'stop:policy_error'
    if any(state.get(key) is True for key in ('checkpoint_requested', 'stop_now', 'paused')):
        return 'stop:checkpoint_or_pause'
    try:
        age = now - stamp(state['heartbeat_at'])
    except (KeyError, TypeError, ValueError, AttributeError):
        return 'stop:heartbeat_invalid'
    if age < -30 or age > HEARTBEAT_MAX_AGE:
        return 'stop:heartbeat_stale'
    if not all(type(state.get(key)) is int and state[key] > 0
               for key in ('worker_pid', 'server_pid')):
        return 'stop:launcher_identity_missing'
    if journal.get('thread_id', THREAD) != THREAD:
        return 'stop:journal_thread_changed'
    if journal.get('status') in ('intent', 'uncertain', 'stopped'):
        return 'stop:submission_or_prior_stop_requires_review'
    last = journal.get('queued_at')
    if last is not None:
        if not isinstance(last, (int, float)) or now < last:
            return 'stop:clock_or_journal_invalid'
        if now - last < INTERVAL:
            return 'wait:interval'
    if backlog:
        return 'wait:queue_backlog'
    return 'queue'


def backlog_present(campaign):
    # Any pending instruction prevents this periodic task from adding pressure.
    # Any sending instruction is uncertain delivery, never a replay signal.
    for name in ('pending', 'sending'):
        folder = campaign / 'instructions' / name
        if folder.exists():
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.name.endswith('.json'):
                        return True
    return False


def tail(path):
    with path.open('rb') as stream:
        stream.seek(0, os.SEEK_END); size = stream.tell()
        stream.seek(max(0, size - TAIL_CAP))
        raw = stream.read(TAIL_CAP)
    return {'path': str(path), 'bytes_at_read': size,
            'tail': raw.decode('utf-8', errors='replace')}


def snapshot(state):
    log_dir = Path(state['log_dir'])
    expected_parent = CAMPAIGN / 'runs'
    if log_dir.parent != expected_parent or log_dir.is_symlink():
        raise ValueError('unexpected campaign log directory')
    return {'at': time.time(), 'thread_id': THREAD, 'heartbeat_at': state['heartbeat_at'],
            'phase': state['phase'], 'goal_status': state['goal']['status'],
            'worker_pid': state['worker_pid'], 'server_pid': state['server_pid'],
            'tails': [tail(log_dir / name) for name in ('dispatcher.txt', 'console.log')]}


def instruction(snapshot_path, marker):
    return (marker + '\nFunctional McKernel OS/apps and Rust/assembly migration only; '
            'no security testing. This request applies ONLY to active thread ' + THREAD + '. '
            'If thread/goal changed, paused, stopped or held, do not act or resume. '
            'The user requests an intelligent engineering review and steering every ten minutes. '
            'Perform that review now using actual recent logs, exact accepted artifacts and active '
            'agent results. Local bounded observation: ' + str(snapshot_path) + '. '
            'Keep M14 Rust/assembly conversion AND P12 final functional session progressing in '
            'parallel when measured resources and existing reviewed controls permit; this latest '
            'parallel priority supersedes the short Rust-first instruction. Identify concrete '
            'implementation/link/native progress and failures, the current critical path, stalled '
            'handoffs and redundant preparation; directly steer ready owners and remove avoidable '
            'waiting. Reuse accepted work. Explain material course changes with evidence and '
            'record a concise engineering checkpoint. Distinguish producer mixed-work counters '
            'from wall time/heartbeat and formal terminal acceptance. Do not infer credit, healthy '
            'flow or physical clearance from liveness. Preserve one native/heavy controller, '
            'permanent27:4 mutex, exact resource grants, evidence and failure/retirement rules. '
            'This periodic request authorizes no policy-hold retry, model/paid-API change, '
            'resume/restart, unchecked workload, new framework or repeated approval gate. '
            'Do not wait for this timer to continue already authorized useful work.')


def load_queue():
    # Reuse exactly the existing queue_instruction implementation and its small
    # helpers; do not import/start a launcher or its server-related dependencies.
    raw = LAUNCHER.read_bytes()
    tree = ast.parse(raw, str(LAUNCHER))
    wanted = {'utc', 'atomic_json', 'queue_instruction'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    if {n.name for n in nodes} != wanted:
        raise ValueError('existing queue API/functions changed')
    import uuid as uuid_module
    scope = dict(os=os, json=json, tempfile=tempfile, Path=Path, datetime=datetime, timezone=timezone,
                 uuid4=uuid_module.uuid4)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(LAUNCHER), 'exec'), scope)
    return scope['queue_instruction'], hashlib.sha256(raw).hexdigest()


def event(output, data):
    path = output / 'events.jsonl'
    raw = (json.dumps(data, sort_keys=True) + '\n').encode()
    if path.exists() and path.stat().st_size + len(raw) > EVENT_CAP:
        os.replace(path, output / 'events.previous.jsonl')
    with path.open('ab') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def step(campaign, output, queue, journal, now):
    state = read_json(campaign / 'state.json')
    verdict = decision(state, journal, now, backlog_present(campaign))
    if verdict != 'queue':
        return verdict, journal
    observed = snapshot(state)
    # Preserve two compact observations, never full logs or broad hashes.
    current = output / 'snapshot.json'
    if current.exists():
        os.replace(current, output / 'snapshot.previous.json')
    atomic(current, observed)
    fresh = read_json(campaign / 'state.json')
    verdict = decision(fresh, journal, time.time(), backlog_present(campaign))
    if verdict != 'queue':
        return verdict, journal
    if any(fresh.get(k) != state.get(k) for k in ('thread_id', 'log_dir', 'worker_pid', 'server_pid')):
        return 'stop:launcher_identity_changed_during_read', journal
    marker = MARKER + ' thread=' + THREAD + ' interval=' + str(int(now // INTERVAL))
    pending = dict(thread_id=THREAD, status='intent', intent_at=now, marker=marker)
    # Persist intent before queue mutation. If a crash occurs after submission,
    # restart refuses the ambiguous intent instead of duplicating delivery.
    atomic(output / 'journal.json', pending)
    try:
        ident = queue(campaign, instruction(current, marker))
    except Exception:
        pending['status'] = 'uncertain'
        atomic(output / 'journal.json', pending)
        raise
    done = dict(pending, status='queued', queued_at=time.time(), instruction_id=ident)
    atomic(output / 'journal.json', done)
    # queue_instruction has no atomic compare-thread argument. Pin thread in
    # request text and detect an immediate change; never queue again on change.
    after = read_json(campaign / 'state.json')
    final = decision(after, done, time.time(), False)
    if final.startswith('stop:'):
        return final, done
    return 'queued', done


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicitly enable queue-only monitor loop')
    args = parser.parse_args()
    if not args.run:
        parser.error('--run required; this file is preparation only until explicitly launched')
    if os.getuid() != 1000 or os.geteuid() != 1000 or os.sched_getaffinity(0) != {0}:
        raise RuntimeError('requires ordinary user1000 and CPU0-only launch profile')
    os.umask(0o077)
    with (OUTPUT / 'supervisor.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Never unlink the retained private lock; never touch campaign locks.
        if (OUTPUT / 'stop-request.json').exists():
            raise RuntimeError('prior explicit stop request requires coordinator review')
        queue, source_sha = load_queue()
        journal_path = OUTPUT / 'journal.json'
        journal = read_json(journal_path) if journal_path.exists() else {}
        birth = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        atomic(OUTPUT / 'supervisor.json', dict(pid=os.getpid(), start_ticks=birth,
               boot_id=boot, script_path=str(Path(__file__).resolve()), thread_id=THREAD,
               started_at=time.time(), interval_seconds=INTERVAL, launcher_sha256=source_sha))
        while True:
            verdict, journal = step(CAMPAIGN, OUTPUT, queue, journal, time.time())
            if verdict in ('queued', 'wait:queue_backlog') or verdict.startswith('stop:'):
                # Log backlog transitions only, not one line per polling tick.
                if verdict == 'queued' or verdict != journal.get('last_logged_event'):
                    event(OUTPUT, dict(at=time.time(), event=verdict,
                                      instruction_id=journal.get('instruction_id')))
                    journal['last_logged_event'] = verdict
                    if journal_path.exists():
                        atomic(journal_path, journal)
            if verdict.startswith('stop:'):
                atomic(journal_path, dict(journal, thread_id=THREAD, status='stopped', reason=verdict))
                return
            time.sleep(15)


if __name__ == '__main__':
    main()
