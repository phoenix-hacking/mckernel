#!/usr/bin/env python3
"""Root-armed one-shot graceful controller handoff. Never edits launcher state."""
import argparse
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time

REPO = Path('/home/holden/mckernel')
STATE = REPO / '.git/os-autopilot'
HERE = Path(__file__).resolve().parent
EXPECTED = {'watcher': (1347803, '18269758'),
            'worker': (1347805, '18269764'),
            'server': (1347807, '18269770')}
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
SOURCE_NAMES = ('scripts/run_os_goal.py', 'scripts/watch_os_goal.py',
                'scripts/run_os_parallel.py')
LOCK_IDENTITIES = {}


def need(value, message):
    if not value:
        raise RuntimeError(message)


def read(path, cap=16 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and before.st_size <= cap, 'nonregular/oversize input: ' + str(path))
        data = b''
        while len(data) <= cap:
            part = os.read(fd, min(65536, cap + 1 - len(data)))
            if not part:
                break
            data += part
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(len(data) <= cap and all(getattr(before, k) == getattr(after, k) for k in fields),
             'changed input: ' + str(path))
        return data
    finally:
        os.close(fd)


def obj(path):
    return json.loads(read(path))


def digest(path):
    data = read(path, 64 * 1024 * 1024)
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def save(name, value):
    data = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(HERE / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def birth(pid):
    try:
        fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'state': fields[0], 'ppid': int(fields[1]), 'start': fields[19]}
    except FileNotFoundError:
        return None
    except (OSError, IndexError, ValueError) as error:
        raise RuntimeError('unresolved process identity: ' + str(pid)) from error


def boot():
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT, 'boot changed')


def no_service_stop(state, allow_our_signal=False):
    reason = state.get('stop_reason')
    # Examine classification internally; never serialize personal error/config
    # payloads or balances into this handoff's receipts.
    error = state.get('last_error')
    failure = state.get('last_failure') or {}
    info = error.get('codexErrorInfo') if isinstance(error, dict) else error
    prior = failure.get('error') if isinstance(failure, dict) and failure.get('log_dir') == state.get('log_dir') else None
    text = json.dumps([info, prior]).lower()
    need(not any(s in text for s in ('quota', 'credit', 'auth', 'policy', 'usage', 'rate', 'billing')),
         'actual service/auth/policy/quota/rate stop remains authoritative')
    need(not state.get('pause_reason'), 'actual pause remains authoritative')
    goal = state.get('goal') or {}
    need(goal.get('status') not in ('usageLimited', 'budgetLimited', 'blocked', 'complete'),
         'actual goal stop remains authoritative')
    used = ((state.get('last_rate_limits') or {}).get('primary') or {}).get('usedPercent')
    need(type(used) in (int, float) and 0 <= used < 100, 'included usage unknown or reached100')
    if reason == 'included_usage_guard':
        old = (state.get('settings') or {}).get('included_usage_stop_percent')
        need(old == 97 and isinstance(used, (int, float)) and used < 100,
             'not the specifically superseded old97 included guard')
        return
    need(reason is None or allow_our_signal and reason == 'signal_15',
         'unrecognized/external stop reason: ' + str(reason))


def source_matches(arm):
    need(set(arm['source_pins']) == set(SOURCE_NAMES), 'exact controller source set required')
    for name, expected in arm['source_pins'].items():
        need(digest(REPO / name)['sha256'] == expected, 'controller source changed: ' + name)
    # This import is independent of the old worker's already-loaded97 module.
    sys.path.insert(0, str(REPO / 'scripts'))
    module = importlib.import_module('run_os_goal')
    need(module.INCLUDED_USAGE_STOP_PERCENT == 100, 'fresh source import is not100')
    return module.INCLUDED_USAGE_STOP_PERCENT


def lock_files(require_free):
    streams = []
    try:
        for name in ('run.lock', 'watch.lock'):
            fd = os.open(STATE / name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
            stream = os.fdopen(fd, 'rb')
            streams.append(stream)
            st = os.fstat(fd)
            identity = (st.st_dev, st.st_ino)
            need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_uid == os.geteuid(),
                 'launcher lock ownership/type changed')
            if name not in LOCK_IDENTITIES:
                LOCK_IDENTITIES[name] = identity
            need(LOCK_IDENTITIES[name] == identity, 'launcher lock inode changed')
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                free = True
            except BlockingIOError:
                free = False
            need(free == require_free, 'unexpected launcher lock state: ' + name)
        return streams
    except BaseException:
        for stream in streams:
            stream.close()
        raise


def exited(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    return bool(poller.poll(0))


def selected(state):
    return {k: state.get(k) for k in ('phase', 'stop_reason', 'pause_reason', 'worker_pid',
            'server_pid', 'server_start', 'thread_id', 'stop_errors', 'cleanup_verified')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', type=Path, required=True)
    parser.add_argument('--arm-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(args.execute, 'no implicit effect; root must explicitly select --execute')
    need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'), 'pidfd support required')
    deadline = time.monotonic() + 1800
    while not args.arm.exists():
        need(time.monotonic() < deadline, 'root arm did not arrive')
        time.sleep(.25)
    arm_ref = digest(args.arm)
    need(arm_ref['sha256'] == args.arm_sha256, 'arm hash mismatch')
    arm = obj(args.arm)
    need(arm.get('schema') == 'mckernel.included100.controller-handoff-arm.v1'
         and arm.get('status') == 'PASS_ROOT_ARMED', 'root arm not released')
    need(arm.get('helper_sha256') == digest(Path(__file__).resolve())['sha256'], 'helper pin mismatch')
    need(arm.get('boot_id') == BOOT and arm.get('publication_verified') is True,
         'root checkpoint publication is not armed')
    need(re.fullmatch('[0-9a-f]{40}', arm.get('checkpoint_commit', ''))
         and re.fullmatch('[0-9a-f]{40}', arm.get('checkpoint_tree', '')), 'checkpoint commit/tree absent')
    proof = arm['publication_proof']
    need(digest(Path(proof['path'])) == proof, 'checkpoint publication proof changed')
    boot()
    imported_percent = source_matches(arm)
    need(arm.get('expected_owners') == {k: {'pid': v[0], 'start': v[1]} for k, v in EXPECTED.items()},
         'arm old-owner tuple mismatch')
    state = obj(STATE / 'state.json')
    no_service_stop(state)
    need(state.get('phase') == 'running' and state.get('thread_id') == arm['thread_id']
         and (state.get('goal') or {}).get('status') == 'active', 'old saved goal changed')
    watch = obj(STATE / 'watcher.json')
    need(watch.get('watcher_pid') == EXPECTED['watcher'][0]
         and watch.get('worker_pid') == EXPECTED['worker'][0], 'watcher record mismatch')
    need(state.get('worker_pid') == EXPECTED['worker'][0]
         and state.get('server_pid') == EXPECTED['server'][0]
         and state.get('server_start') == EXPECTED['server'][1], 'worker/server record mismatch')
    need(not state.get('stop_errors'), 'old stop errors present')
    for stream in lock_files(False):
        stream.close()
    handles = {}
    identities = {}
    for role, (pid, start) in EXPECTED.items():
        fd = os.pidfd_open(pid, 0)
        handles[role] = fd
        identity = birth(pid)
        need(identity and identity['start'] == start and identity['state'] != 'Z'
             and not exited(fd), 'old identity not authenticated: ' + role)
        identities[role] = identity
    need(identities['worker']['ppid'] == EXPECTED['watcher'][0]
         and identities['server']['ppid'] == EXPECTED['worker'][0], 'old parentage mismatch')
    # O_EXCL journal is the durable once-only guard; never renamed/reset on failure.
    save('once-claimed.json', {'arm': arm_ref, 'at': time.time(), 'owners': identities,
                             'lock_identities': LOCK_IDENTITIES,
                             'pid': os.getpid(), 'start': birth(os.getpid())['start']})
    watcher_log = STATE / 'watcher.jsonl'
    initial_log = watcher_log.stat()
    offset = initial_log.st_size
    source_matches(arm)
    no_service_stop(obj(STATE / 'state.json'))
    signaled_at = time.time()
    signal.pidfd_send_signal(handles['watcher'], signal.SIGTERM)
    save('signal-sent.json', {'at': signaled_at, 'signal': 'SIGTERM', 'target': EXPECTED['watcher'],
                             'method': 'pidfd_send_signal', 'no_worker_or_server_signal_by_helper': True})
    while not all(exited(fd) for fd in handles.values()):
        boot()
        no_service_stop(obj(STATE / 'state.json'), True)
        need(time.monotonic() < deadline, 'old owner retirement timed out; no resume')
        time.sleep(.25)
    # pidfd POLLIN proves exit of the authenticated objects, not PID absence/reuse.
    state = obj(STATE / 'state.json')
    no_service_stop(state, True)
    need(state.get('phase') == 'stopped' and state.get('thread_id') == arm['thread_id']
         and (state.get('goal') or {}).get('status') == 'paused'
         and not state.get('stop_errors'), 'stopped/paused state or graceful stop unresolved')
    now_log = watcher_log.stat()
    need((initial_log.st_dev, initial_log.st_ino) == (now_log.st_dev, now_log.st_ino)
         and now_log.st_size >= offset and now_log.st_size - offset <= 1024 * 1024,
         'watcher event log changed/truncated/oversize')
    with watcher_log.open('rb') as stream:
        stream.seek(offset)
        events = [json.loads(line) for line in stream.read(1024 * 1024 + 1).splitlines()]
    events = [e for e in events if e.get('watcher_pid') == EXPECTED['watcher'][0]
              and e.get('worker_pid') == EXPECTED['worker'][0] and e.get('at', 0) >= signaled_at]
    need(not any(e['event'].startswith('recovery_stopped') or e['event'] == 'worker_kill_timed_out' for e in events),
         'watcher retirement refusal event present')
    need(any(e['event'] == 'worker_exited' for e in events)
         and events and events[-1]['event'] == 'watcher_stopped'
         and events[-1].get('exit_code') == 10, 'authoritative watcher_stopped sequence absent')
    watch = obj(STATE / 'watcher.json')
    need(watch == events[-1], 'final watcher snapshot does not match final event')
    leases = lock_files(True)
    save('old-retirement.json', {'status': 'PASS_AUTHENTICATED_OLD_OWNER_RETIREMENT',
         'pidfd_exit_events': {role: exited(fd) for role, fd in handles.items()},
         'watcher_events': events, 'state': selected(state), 'same_goal_status': 'paused',
         'old_watcher_numeric_wait_status': 'UNKNOWN_NOT_OUR_CHILD',
         'watcher_declared_exit_code': watch['exit_code'],
         'runtime_cleanup_verified_not_claimed': state.get('cleanup_verified'),
         'both_exclusive_launcher_locks_acquired': True})
    boot()
    source_matches(arm)
    no_service_stop(obj(STATE / 'state.json'), True)
    for fd in handles.values():
        os.close(fd)
    # Release only our read-open lock handles. Canonical launcher reacquires and
    # refuses a competing owner; this helper never writes state or lock bytes.
    for stream in leases:
        stream.close()
    argv = [sys.executable, '-I', '-B', str(REPO / 'scripts/run_os_parallel.py'), '--run', '--background']
    save('canonical-launch-command.json', {'argv': argv, 'cwd': str(REPO), 'attempts': 1})
    with (HERE / 'canonical-launch.stdout').open('xb') as out, (HERE / 'canonical-launch.stderr').open('xb') as err:
        child = subprocess.Popen(argv, cwd=REPO, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 start_new_session=True, close_fds=True)
        save('canonical-launch-child.json', {'pid': child.pid, 'identity': birth(child.pid), 'argv': argv})
        try:
            rc = child.wait(timeout=180)
        except subprocess.TimeoutExpired:
            save('canonical-launch-wait.json', {'direct_join': False, 'pid': child.pid,
                 'status': 'TIMEOUT_RETAIN_OWNER_NO_SIGNAL_NO_RETRY', 'identity': birth(child.pid)})
            raise RuntimeError('canonical manual launcher unresolved; no retry')
        save('canonical-launch-wait.json', {'direct_join': True, 'returncode': rc, 'pid': child.pid})
    need(rc == 0, 'canonical manual run refused; no retry')
    need((HERE / 'canonical-launch.stdout').stat().st_size <= 8 * 1024 * 1024
         and (HERE / 'canonical-launch.stderr').stat().st_size <= 8 * 1024 * 1024, 'launch stream cap exceeded')
    launches = []
    for line in read(HERE / 'canonical-launch.stdout').decode().splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and type(value.get('launcher_pid')) is int:
            launches.append(value)
    need(len(launches) == 1, 'canonical background watcher identity not unique')
    new_watcher = launches[0]['launcher_pid']
    until = time.monotonic() + 120
    while True:
        boot()
        new = obj(STATE / 'state.json')
        no_service_stop(new, new.get('worker_pid') == EXPECTED['worker'][0])
        watch = obj(STATE / 'watcher.json')
        if new.get('phase') == 'running' and (new.get('settings') or {}).get('included_usage_stop_percent') == 100:
            break
        need(time.monotonic() < until, 'new effective100 worker not observed; no retry')
        time.sleep(.25)
    need(new.get('thread_id') == arm['thread_id'] and (new.get('goal') or {}).get('status') == 'active',
         'new launcher did not resume same saved goal')
    ids = {'watcher': watch.get('watcher_pid'), 'worker': new.get('worker_pid'), 'server': new.get('server_pid')}
    need(ids['watcher'] == new_watcher, 'new watcher is not the canonical returned child')
    observed = {role: birth(pid) if type(pid) is int else None for role, pid in ids.items()}
    need(all(observed.values()) and all(ids[r] != EXPECTED[r][0] for r in ids), 'new owners not fresh')
    need(observed['worker']['ppid'] == ids['watcher'] and observed['server']['ppid'] == ids['worker']
         and observed['server']['start'] == new.get('server_start')
         and watch.get('worker_pid') == ids['worker'], 'new owner parentage/birth mismatch')
    for stream in lock_files(False):
        stream.close()
    source_matches(arm)
    save('new-effective100-proof.json', {'status': 'PASS_SAME_GOAL_MANUAL_RESUME_EFFECTIVE100',
         'arm': arm_ref, 'fresh_source_import_percent': imported_percent,
         'effective_worker_settings_percent': new['settings']['included_usage_stop_percent'],
         'owners': {r: {'pid': ids[r], **observed[r]} for r in ids},
         'state': selected(new), 'watcher_event': watch, 'manual_launches': 1,
         'goal_status': new['goal']['status'], 'launcher_state_edits_by_helper': 0,
         'purchased_credit_or_API_switch': False})


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        try:
            save('REFUSED.json', {'status': 'REFUSED_NO_AUTOMATIC_RETRY', 'error': str(error), 'at': time.time()})
        except BaseException:
            pass
        raise
