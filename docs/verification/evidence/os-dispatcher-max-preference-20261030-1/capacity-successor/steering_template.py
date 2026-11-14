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
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import uuid

THREAD = None  # Parent supplies the actual new active thread in an explicit arm binding.
CAMPAIGN = Path('/home/holden/mckernel/.git/os-autopilot')
LAUNCHER = Path('/home/holden/mckernel/scripts/run_os_goal.py')
OUTPUT = Path(__file__).resolve().parent
INTERVAL = 1200
DEADLINE = float('1793774133')  # Requires a separately authorized actual window; old window expired.
GUARDIAN_JOURNAL = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1930-pacific-1/armed-controller/journal.json')  # Existing live guardian; monitor-only successor.
GUARDIAN_PACKET = None
ARM_BINDING = None
FOCUS = None
HEARTBEAT_MAX_AGE = 120
STATE_CAP = 1 << 20
TAIL_CAP = 8192
EVENT_CAP = 1 << 20
MARKER = '[twenty-minute-engineering-review-comms-v1]'
RECOVERY_CHECKS = None
CLASSIFY_USAGE_FAILURE = None


def load_binding(path, expected_sha):
    """Finalize only the explicit parent-supplied active thread/guardian; never infer one."""
    global THREAD, GUARDIAN_PACKET, ARM_BINDING, FOCUS, RECOVERY_CHECKS, CLASSIFY_USAGE_FAILURE
    raw = path.read_bytes()
    if len(raw) > STATE_CAP or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('exact bounded arm binding required')
    binding = json.loads(raw)
    thread = binding.get('thread_id')
    if (binding.get('status') != 'FINALIZED_FOR_EXPLICIT_ARM' or not isinstance(thread, str)
            or str(uuid.UUID(thread)) != thread or binding.get('deadline') != DEADLINE
            or binding.get('guardian_journal') != str(GUARDIAN_JOURNAL)
            or binding.get('campaign') != str(CAMPAIGN)):
        raise ValueError('new thread, campaign and fixed Sunday guardian/deadline binding required')
    packet = binding.get('guardian_packet_sha256')
    if not isinstance(packet, str) or len(packet) != 64 or any(c not in '0123456789abcdef' for c in packet):
        raise ValueError('actual new guardian packet identity required')
    launcher = binding.get('launcher_sha256')
    if not isinstance(launcher, str) or len(launcher) != 64:
        raise ValueError('reviewed launcher source identity required')
    if binding.get('boot_id') != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        raise ValueError('arm binding boot identity mismatch')
    focus = Path(binding['focus_path'])
    if not focus.is_absolute() or not focus.is_file():
        raise ValueError('actual new run-window focus document required')
    RECOVERY_CHECKS, CLASSIFY_USAGE_FAILURE = load_recovery_checks(binding)
    THREAD, GUARDIAN_PACKET, ARM_BINDING, FOCUS = thread, packet, expected_sha, focus
    return binding


def load_recovery_checks(binding):
    """Select only pinned pure validators, using the same strict transport classifier."""
    refs = binding['recovery_source_sha256']
    transport_path = LAUNCHER.parent / 'os_goal_transport.py'
    raw = transport_path.read_bytes()
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != refs['os_goal_transport.py']:
        raise ValueError('reviewed transport source binding differs')
    spec = importlib.util.spec_from_file_location('monitor_pure_transport', transport_path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    path = LAUNCHER.parent / 'watch_os_goal.py'; raw = path.read_bytes()
    if len(raw) > STATE_CAP or hashlib.sha256(raw).hexdigest() != refs['watch_os_goal.py']:
        raise ValueError('reviewed watcher source binding differs')
    wanted = {'credit_poll_timeout', 'timeout_pause_owned', 'transport_failure_owned', 'transport_pause_owned'}
    nodes = [node for node in ast.parse(raw, str(path)).body
             if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in nodes} != wanted:
        raise ValueError('pure recovery validator interface differs')
    scope = dict(hashlib=hashlib, json=json, READ_ONLY_RPC_METHODS=module.READ_ONLY_RPC_METHODS,
                 classify_usage_failure=module.classify_usage_failure,
                 classify_rpc_failure=module.classify_rpc_failure,
                 classify_service_failure=module.classify_service_failure)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope, module.classify_usage_failure


def watcher_owns_recovery(guardian, watcher):
    """Read-only positive identity check; no process signal or recovery action."""
    chain = guardian.get('replacement', guardian.get('original', {}))
    owner = chain.get('watcher', {})
    pid = owner.get('pid')
    if type(pid) is not int or pid <= 0 or watcher.get('watcher_pid') != pid:
        return False
    if watcher.get('event') in ('watcher_stopped', 'restart_limit_reached'):
        return False
    try:
        fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
        return fields[0] not in ('Z', 'X') and fields[19] == str(owner.get('start'))
    except (OSError, ValueError, IndexError):
        return False


def normal_watcher_retry(state):
    """Recognize existing watcher's narrow capacity/transport classes, without retrying."""
    reason = state.get('stop_reason') or ''
    error = state.get('last_error') or {}
    info = error.get('codexErrorInfo') if isinstance(error, dict) else None
    return (reason in ('server_error', 'turn_failed')
            and info in ('serverOverloaded', 'rateLimitExceeded') or reason == 'rate_limit'
            or reason in ('launcher_error', 'active_goal_did_not_continue')
            and state.get('retryable') is True)


def approved_timeout_wait(state, receipt, watcher_owned):
    """Observe only a pinned live watcher's post-retirement exact-class approval."""
    if not watcher_owned or not isinstance(receipt, dict):
        return False
    goal = state.get('goal') or {}
    before, after = receipt.get('goal_before') or {}, receipt.get('goal_after') or {}
    fingerprint = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    try:
        valid = (receipt.get('approved') is True and receipt.get('schema_version') == 1
                 and receipt.get('thread_id') == THREAD and type(receipt.get('worker_pid')) is int
                 and receipt['worker_pid'] > 0 and isinstance(receipt.get('worker_start'), str)
                 and bool(receipt['worker_start']) and receipt.get('pause_confirmed') is True
                 and receipt.get('pause_method') == 'thread/goal/set'
                 and receipt.get('stop_reason') == 'credit_budget_unknown'
                 and CLASSIFY_USAGE_FAILURE is not None
                 and CLASSIFY_USAGE_FAILURE(receipt.get('credit_budget_error')) is not None
                 and before.get('status') == 'active' and after.get('status') == 'paused'
                 and goal.get('status') == 'paused'
                 and fingerprint(after) == receipt.get('goal_after_sha256') == fingerprint(goal))
    except (ValueError, TypeError):
        return False
    return bool(valid and ((state.get('phase') == 'stopped'
                           and state.get('stop_reason') == 'credit_budget_unknown'
                           and state.get('credit_budget_error') == receipt['credit_budget_error'])
                          or (state.get('phase') == 'starting' and not state.get('stop_reason'))))


def watchdog_checkpoint_owned(state, watcher):
    """Read only the existing birth-bound watchdog request during checkpoint publication."""
    worker, start = state.get('worker_pid'), state.get('worker_start')
    if (type(worker) is not int or not isinstance(start, str) or not start.isdigit()
            or watcher.get('worker_pid') != worker
            or watcher.get('event') not in ('heartbeat_stalled', 'agent_progress_stalled')):
        return False
    path = CAMPAIGN / ('watchdog-request-' + str(worker) + '-' + start + '.json')
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_nlink != 1:
            return False
        request = read_json(path, 4096)
        fields = Path('/proc/' + str(watcher['watcher_pid']) + '/stat').read_text().rsplit(')', 1)[1].split()
        return (request.get('schema_version') == 1 and request.get('worker_pid') == worker
                and request.get('worker_start') == start
                and request.get('watcher_pid') == watcher['watcher_pid']
                and request.get('watcher_start') == fields[19]
                and request.get('reason') == watcher.get('event'))
    except (OSError, ValueError, TypeError, IndexError, KeyError):
        return False


def owned_transport_wait(state, watcher, watcher_owned):
    """Observe proven worker pauses/approved same-watcher recovery; never resume."""
    if not watcher_owned or RECOVERY_CHECKS is None:
        return False
    goal = state.get('goal') or {}
    # Cover the successful pause before the supervisor publishes its decision.
    if watcher.get('worker_pid') == state.get('worker_pid') and goal.get('status') == 'paused':
        if (RECOVERY_CHECKS['transport_pause_owned'](state)
                or RECOVERY_CHECKS['credit_poll_timeout'](state)
                and RECOVERY_CHECKS['timeout_pause_owned'](state)):
            return True
    origin = watcher.get('transport_recovery')
    if not isinstance(origin, dict) or origin.get('approved') is not True or origin.get('thread_id') != THREAD:
        return False
    if origin.get('require_active') is True:
        return goal.get('status') == 'active' and state.get('phase') != 'running'
    try:
        fingerprint = hashlib.sha256(json.dumps(goal, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    except (ValueError, TypeError):
        return False
    if goal.get('status') != 'paused' or origin.get('goal_after_sha256') != fingerprint:
        return False
    return (origin.get('pause_confirmed') is True or origin.get('origin_kind') == 'authenticated_watchdog')


def observe_pause_publication(state, journal, watcher, watcher_owned, boot_now):
    """At most60s passive wait for receipt publication; never recovery authority."""
    goal = state.get('goal') or {}
    if (not watcher_owned or goal.get('status') != 'paused' or state.get('phase') != 'running'
            or state.get('stop_reason') or state.get('thread_id') != THREAD
            or watcher.get('worker_pid') != state.get('worker_pid')):
        journal.pop('pause_publication', None)
        return False
    pid, birth = state.get('worker_pid'), state.get('worker_start')
    if type(pid) is not int or not isinstance(birth, str) or not birth.isdigit():
        return False
    try:
        fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
        live = (fields[0] not in ('Z', 'X') and fields[19] == birth
                and int(fields[1]) == watcher.get('watcher_pid'))
    except (OSError, ValueError, IndexError):
        live = False
    if not live:
        return False
    old = journal.get('pause_publication') or {}
    if (old.get('worker_pid'), old.get('worker_start'), old.get('thread_id')) != (pid, birth, THREAD):
        journal['pause_publication'] = dict(worker_pid=pid, worker_start=birth,
                                          thread_id=THREAD, since_boot=boot_now)
    return True


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


def decision(state, journal, now, backlog, boot_now=None, watcher_owned=False, credit_timeout_recovery=None, watchdog_checkpoint=False, watcher_record=None, pause_publication=False):
    """Pure stop/wait/due decision; only the existing watcher may recover workers."""
    if now >= DEADLINE or (boot_now is not None and
            boot_now >= journal.get('boot_deadline', float('inf'))):
        return 'stop:deadline'
    if THREAD is None:
        return 'stop:unbound_thread'
    if state.get('thread_id') != THREAD:
        return 'stop:thread_changed'
    goal = state.get('goal') or {}
    if goal.get('threadId', THREAD) != THREAD:
        return 'stop:goal_not_active'
    if any(state.get(key) for key in ('policy_hold', 'service_hold', 'auth_hold', 'billing_hold')):
        return 'stop:held'
    # A historical serverOverloaded record is not a live hold. A policy error
    # is never used as a reason to queue another automatic instruction.
    error = state.get('last_error') or {}
    if isinstance(error, dict) and error.get('codexErrorInfo') == 'cyberPolicy':
        return 'stop:policy_error'
    info = error.get('codexErrorInfo') if isinstance(error, dict) else None
    if any(word in json.dumps(info).lower() for word in ('policy', 'quota', 'auth', 'billing', 'credit', 'included_usage', 'budget_exhausted')):
        return 'stop:error_hold'
    if any(state.get(key) is True for key in ('checkpoint_requested', 'stop_now', 'paused')):
        return 'stop:checkpoint_or_pause'
    if journal.get('thread_id', THREAD) != THREAD:
        return 'stop:journal_thread_changed'
    if journal.get('status') in ('intent', 'uncertain', 'stopped'):
        return 'stop:submission_or_prior_stop_requires_review'
    if state.get('transport_uncertain') or any(isinstance(state.get(key), dict) and state[key].get('status') in ('sending', 'delivery_uncertain', 'intent', 'uncertain') for key in ('resume_instruction', 'last_instruction')):
        return 'stop:uncertain_transport_or_submission'
    reason = str(state.get('stop_reason') or '').lower()
    usage_transport = (reason == 'credit_budget_unknown' and CLASSIFY_USAGE_FAILURE is not None
                       and CLASSIFY_USAGE_FAILURE(state.get('credit_budget_error')) is not None)
    if not usage_transport and any(word in reason for word in ('policy', 'quota', 'credit', 'auth', 'billing', 'included_usage', 'needs_user_input', 'goal_cleared', 'budget_exhausted', 'work_window', 'signal_')):
        return 'stop:explicit_stop_or_hold'
    publication = journal.get('pause_publication') or {}
    if (pause_publication and watcher_owned and boot_now is not None
            and publication.get('worker_pid') == state.get('worker_pid')
            and publication.get('worker_start') == state.get('worker_start')
            and publication.get('thread_id') == THREAD
            and type(publication.get('since_boot')) in (int, float)
            and 0 <= boot_now-publication['since_boot'] <= 60):
        return 'wait:watcher_pause_publication'
    if owned_transport_wait(state, watcher_record or {}, watcher_owned):
        return 'wait:watcher_owned_transport'
    if approved_timeout_wait(state, credit_timeout_recovery, watcher_owned):
        return 'wait:watcher_credit_read_timeout'
    if watcher_owned and goal.get('status') in ('active', 'paused'):
        if state.get('stop_reason') == 'watchdog_recovery':
            return 'wait:watcher_watchdog_recovery'
        if state.get('phase') == 'starting' and not state.get('stop_reason'):
            return 'wait:watcher_starting'
        if watchdog_checkpoint and not state.get('stop_reason'):
            return 'wait:watcher_watchdog_checkpoint'
    if goal.get('status') != 'active':
        return 'stop:goal_not_active'
    protected = ('policy', 'quota', 'credit', 'auth', 'billing', 'included_usage',
                 'needs_user_input', 'goal_cleared', 'budget_exhausted', 'work_window', 'signal_')
    if any(word in str(state.get('stop_reason') or '').lower() for word in protected):
        return 'stop:explicit_stop_or_hold'
    if state.get('phase') != 'running' or state.get('stop_reason'):
        if watcher_owned and (normal_watcher_retry(state)
                              or state.get('phase') == 'starting' and not state.get('stop_reason')):
            return 'wait:watcher_recovery'
        return 'stop:phase_' + str(state.get('phase'))
    try:
        age = now - stamp(state['heartbeat_at'])
    except (KeyError, TypeError, ValueError, AttributeError):
        return 'stop:heartbeat_invalid'
    if age > HEARTBEAT_MAX_AGE and watcher_owned:
        return 'wait:watcher_heartbeat'
    if age < -30 or age > HEARTBEAT_MAX_AGE:
        return 'stop:heartbeat_stale'
    if not all(type(state.get(key)) is int and state[key] > 0
               for key in ('worker_pid', 'server_pid')):
        return 'stop:launcher_identity_missing'
    last = journal.get('queued_at', journal.get('baseline_at'))
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
    try:
        with path.open('rb') as stream:
            stream.seek(0, os.SEEK_END); size = stream.tell()
            stream.seek(max(0, size - TAIL_CAP))
            raw = stream.read(TAIL_CAP)
    except FileNotFoundError:
        # Optional logs may not exist until the first dispatcher output, or may
        # be renamed/unlinked before open. No content or acceptance is inferred.
        return {'path': str(path), 'bytes_at_read': None, 'tail': '', 'availability': 'missing'}
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
            'tails': [tail(log_dir / name) for name in ('dispatcher.txt', 'console.log')],
            'resources': resource_headroom(),
            'usage_as_recorded': usage_summary(state),
            'milestone_updates': milestone_updates()}


def usage_summary(state):
    limits = state.get('last_rate_limits') or {}
    summary = {}
    for name, keys in (('primary', ('usedPercent', 'windowDurationMins', 'resetsAt')),
                       ('credits', ('hasCredits', 'unlimited', 'balance'))):
        row = limits.get(name) or {}
        summary[name] = {key: str(row.get(key, 'unknown'))[:128] for key in keys}
    summary['spendControlReached'] = limits.get('spendControlReached', 'unknown')
    return summary


def milestone_updates():
    folder = Path('/home/holden/mckernel/docs/verification/os-milestones-20260914')
    result = {}
    for ident in ('M14', 'M15'):
        try:
            data = read_json(folder / ('rust-cutover-' + ident.lower() + '.json'))
            updates = data.get('engineering_updates') or data.get('updates', [])
            components = data.get('files', [])
            components = list(components.values()) if isinstance(components, dict) else components
            result[ident] = dict(status=data.get('status', 'unknown'),
                as_of=data.get('as_of', 'unknown'),
                last_two_updates=[{key: str(value)[:1024] for key, value in update.items()
                    if key in ('at', 'utc', 'actual_increment', 'actual_progress', 'note')}
                    for update in updates[-2:]],
                component_progress_as_recorded=[dict(id=row.get('id', row.get('path', 'unknown')),
                    owner=str(row.get('owner', 'unknown'))[:160], status=row.get('status', 'unknown'),
                    closure=(row.get('file_closure') or {}).get('status', 'unknown'),
                    checkpoint={key: str(value)[:512] for key, value in
                        (row.get('latest_dispatcher_checkpoint') or {}).items()
                        if key in ('actual', 'implemented', 'limits')})
                    for row in components[:32] if isinstance(row, dict)])
        except (OSError, ValueError, TypeError, AttributeError):
            result[ident] = dict(status='unknown', last_two_updates='unknown')
    try:
        practical = read_json(folder / 'practical-milestones.json')
        checks = [check for milestone in practical['milestones']
                  for check in milestone.get('checks', [])]
        result['practical_checks'] = dict(total=len(checks),
            complete=sum(check.get('status') == 'complete' for check in checks), expected=35)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        result['practical_checks'] = 'unknown'
    return result


def resource_headroom():
    memory = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith(('MemAvailable:', 'MemTotal:')):
                key, value = line.split(':', 1)
                memory[key + '_kib'] = int(value.split()[0])
    except (OSError, ValueError):
        memory = 'unknown'
    disk = {}
    scratch = '/home/holden/mckernel-work/scratch'
    for path in ('/home/holden/mckernel', scratch):
        try:
            mounted = os.path.ismount(path)
            device = os.stat(path).st_dev
            info = os.statvfs(path)
            # An unmounted scratch directory reports HOST capacity; never label it scratch headroom.
            disk[path] = dict(ismount=mounted, st_dev=device,
                available_bytes=(info.f_bavail * info.f_frsize
                                 if path != scratch or mounted else 'unknown'))
        except OSError:
            disk[path] = dict(ismount='unknown', st_dev='unknown', available_bytes='unknown')
    try:
        load = list(os.getloadavg())
    except OSError:
        load = 'unknown'
    return dict(memory=memory, disks=disk, load_average=load)


def bind_deadline(journal, wall, boot, boot_id, guardian):
    if guardian.get('deadline') != DEADLINE or guardian.get('boot_id') != boot_id:
        raise ValueError('guardian deadline/boot identity mismatch')
    if GUARDIAN_PACKET is not None and guardian.get('packet_sha256') != GUARDIAN_PACKET:
        raise ValueError('explicit new guardian packet identity mismatch')
    if ARM_BINDING is not None and journal and journal.get('arm_binding_sha256') != ARM_BINDING:
        raise ValueError('retained supervisor arm binding mismatch')
    cutoff = guardian.get('boot_deadline')
    if type(cutoff) not in (int, float) or not 0 < cutoff < float('inf'):
        raise ValueError('guardian boottime deadline invalid')
    if journal and journal.get('boot_id') != boot_id:
        raise ValueError('retained supervisor boot identity mismatch')
    return dict(journal, boot_id=boot_id, deadline=DEADLINE,
                arm_binding_sha256=ARM_BINDING, guardian_packet_sha256=GUARDIAN_PACKET,
                boot_deadline=min(cutoff, journal.get('boot_deadline', cutoff),
                                  boot + DEADLINE - wall))


def guardian_stop(guardian):
    action = str(guardian.get('last_action') or '')
    if guardian.get('transition_hold') or action.startswith('HOLD_'):
        return 'stop:guardian_hold'
    if (guardian.get('stop_intent') or guardian.get('deadline_stop_sent')
            or 'USER_STOP' in action or 'USER_OR_GOAL_STOP' in action):
        return 'stop:guardian_stopping'
    return None


def instruction(snapshot_path, marker):
    return (marker + '\nFunctional McKernel OS/apps and Rust/assembly migration only; '
            'no security testing. ONLY active thread ' + THREAD + '. '
            'If thread/goal changed, paused, stopped or held, do not act or resume. '
            'Perform the requested twenty-minute engineering steering review. '
            'Keep velocity measurements in non-overlapping twenty-minute buckets; '
            'the review cadence remains twenty minutes. '
            'Authoritative priorities: ' + str(FOCUS) + '. Bounded current and previous '
            'observations: ' + str(snapshot_path) + ' and snapshot.previous.json. '
            'Read latest CURRENT.md, HANDOFF.md and the current Root transaction before choosing the next unfinished operation. '
            'Completed cleanup, consumed build nonces and already joined holders must never be replayed from old instructions. '
            'At the relaunch checkpoint BUILD3 passed three commands at19:30 and CID5487 exited0; '
            'postjoin checker, matching native and witness review remained pending. Reconcile that checkpoint with newer records. '
            'Reuse matching retained nine objects, source6153 and SDK21 where still applicable; '
            'preserve historical native/OCI ownership and failed-operation evidence until verified retirement. Model recovery '
            'does not clear native ownership. Use only ready M14 tasks until original-scope M14 acceptance; no '
            'duplicate ports, filler reviews or new inventory/hash loops. Report actual closure '
            'deltas, blocked durations, time to first compiler, the largest avoidable handoff '
            'and one concrete scheduling adjustment. Preserve the original thirty-minute '
            'measurement baseline and do not claim the 95% target has been achieved. '
            'Complete M14 compute Rust/assembly FIRST under the latest mailbox direction; '
            'keep useful disjoint M14 source, compiler and native lanes; pause M15 until M14 acceptance, '
            'then switch agents to M15 with one canonical integration owner. A HOST link alone '
            'does not retire C; require selected-build ABI/link ownership and matching '
            'functional native proof. Reuse accepted artifacts and retained failures. '
            'Report actual compiled, behavior-tested, production-linked and native-qualified '
            'delta, retired C boundaries, active owners, queue-to-compiler latency, '
            'failure-to-validated-fix time and the critical path next command and owner. '
            'Resolve concrete compiler/link failures and avoidable waiting before capacity '
            'expansion. Measure job CPU/wall and peak memory where available, disk '
            'headroom, overlap and blocked time; never infer acceptance from liveness. '
            'Only AFTER actual M14/M15 acceptance, use bounded reproducible seeded '
            'functional Rust workloads/property/model tests, minimize failures, fix causes '
            'and retain meaningful regressions. Stage behavior-preserving cleanup in '
            'small checked batches after cutover. Apply general Google Rust style to new '
            'or changed Rust with descriptive names, focused modules, contextual errors '
            'and documented small unsafe invariants; omit unrelated platform terminology. '
            'Record a concise checkpoint and concrete useful scheduling change; preserve '
            'coherent Git checkpoints and verify pushed progress. Do not reread or rehash '
            'large unchanged evidence without changed inputs or a required validator. '
            'Preserve one native/heavy controller, permanent27:4 mutex, exact resource '
            'grants, current seven-eligible-CPU cap/HOST reserve and '
            '16GiB HOST/12GiB scratch floors until new actual admission, evidence and retirement rules. '
            'Use remaining included weekly allowance first; credits only after included '
            'remaining is zero, under the existing actual billing/usage guard. '
            'Keep whole-file source owners implementing disjoint missing bodies while '
            'ready candidates enter actual compiler/default/native qualification. '
            'A known watcher-owned capacity/transport retry is observed only; this '
            'monitor never restarts a worker, clears a hold or replays an uncertain queue. '
            'No policy retry, paid-API change, unauthorized resume/restart, workload launch by '
            'this monitor, new framework or repeated approval gate. Stop deadline remains '
            '2026-11-04T06:35:33+00:00. Continue already authorized useful work between reviews.')


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


def step(campaign, output, queue, journal, now, watcher_owned=False, credit_timeout_recovery=None, watchdog_checkpoint=False, watcher_record=None, pause_publication=False):
    state = read_json(campaign / 'state.json')
    boot = time.clock_gettime(time.CLOCK_BOOTTIME)
    publication = observe_pause_publication(state, journal, watcher_record or {}, watcher_owned, boot)
    verdict = decision(state, journal, now, backlog_present(campaign),
                       boot, watcher_owned, credit_timeout_recovery, watchdog_checkpoint, watcher_record, publication)
    if verdict != 'queue':
        return verdict, journal
    observed = snapshot(state)
    # Preserve two compact observations, never full logs or broad hashes.
    current = output / 'snapshot.json'
    if current.exists():
        os.replace(current, output / 'snapshot.previous.json')
    atomic(current, observed)
    fresh = read_json(campaign / 'state.json')
    boot = time.clock_gettime(time.CLOCK_BOOTTIME)
    publication = observe_pause_publication(fresh, journal, watcher_record or {}, watcher_owned, boot)
    verdict = decision(fresh, journal, time.time(), backlog_present(campaign),
                       boot, watcher_owned, credit_timeout_recovery, watchdog_checkpoint, watcher_record, publication)
    if verdict != 'queue':
        return verdict, journal
    if any(fresh.get(k) != state.get(k) for k in ('thread_id', 'log_dir', 'worker_pid', 'server_pid')):
        return ('wait:watcher_identity_transition' if watcher_owned else
                'stop:launcher_identity_changed_during_read'), journal
    marker = MARKER + ' thread=' + THREAD + ' interval=' + str(int(now // INTERVAL))
    pending = dict(journal, thread_id=THREAD, status='intent', intent_at=now, marker=marker)
    # Persist intent before queue mutation. If a crash occurs after submission,
    # restart refuses the ambiguous intent instead of duplicating delivery.
    atomic(output / 'journal.json', pending)
    # Recheck cutoff after durable intent, immediately before queue mutation.
    if (time.time() >= DEADLINE or time.clock_gettime(time.CLOCK_BOOTTIME) >=
            pending.get('boot_deadline', float('inf'))):
        return 'stop:deadline', pending
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
    final = decision(after, done, time.time(), False, time.clock_gettime(time.CLOCK_BOOTTIME),
                     watcher_owned)
    if final.startswith('stop:'):
        return final, done
    return 'queued', done


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--run', action='store_true', help='Explicitly enable queue-only monitor loop')
    mode.add_argument('--check-binding', action='store_true', help='Read-only arm identity checks')
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--binding-sha256', required=True)
    args = parser.parse_args()
    if os.getuid() != 1000 or os.geteuid() != 1000 or os.sched_getaffinity(0) != {0}:
        raise RuntimeError('requires ordinary user1000 and CPU0-only launch profile')
    binding = load_binding(args.binding, args.binding_sha256)
    if args.check_binding:
        _, source_sha = load_queue()
        if source_sha != binding['launcher_sha256']:
            raise RuntimeError('launcher source changed since binding finalization')
        guardian = read_json(GUARDIAN_JOURNAL)
        boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        bound = bind_deadline({}, time.time(), time.clock_gettime(time.CLOCK_BOOTTIME),
                              boot_id, guardian)
        state = read_json(CAMPAIGN / 'state.json')
        verdict = decision(state, bound, time.time(), False,
                           time.clock_gettime(time.CLOCK_BOOTTIME))
        if (guardian_stop(guardian) or state.get('phase') != 'running'
                or verdict != 'queue'
                or not watcher_owns_recovery(guardian, read_json(CAMPAIGN / 'watcher.json'))):
            raise RuntimeError('new active thread/guardian/watcher identities are not armable')
        print(json.dumps(dict(status='PASS_READONLY_EXPLICIT_ARM_BINDING', thread_id=THREAD,
              deadline=DEADLINE, boot_deadline=bound['boot_deadline'],
              guardian_packet_sha256=GUARDIAN_PACKET, arm_binding_sha256=ARM_BINDING,
              queue_mutations=0, process_actions=0)))
        return
    os.umask(0o077)
    with (OUTPUT / 'supervisor.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Never unlink the retained private lock; never touch campaign locks.
        if (OUTPUT / 'stop-request.json').exists():
            raise RuntimeError('prior explicit stop request requires coordinator review')
        queue, source_sha = load_queue()
        if source_sha != binding['launcher_sha256']:
            raise RuntimeError('launcher source changed since binding finalization')
        journal_path = OUTPUT / 'journal.json'
        journal = read_json(journal_path) if journal_path.exists() else {}
        birth = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        atomic(OUTPUT / 'supervisor.json', dict(pid=os.getpid(), start_ticks=birth,
               boot_id=boot, script_path=str(Path(__file__).resolve()), thread_id=THREAD,
               started_at=time.time(), interval_seconds=INTERVAL, launcher_sha256=source_sha,
               arm_binding_sha256=ARM_BINDING, guardian_packet_sha256=GUARDIAN_PACKET))
        guardian = read_json(GUARDIAN_JOURNAL)
        journal = bind_deadline(journal, time.time(), time.clock_gettime(time.CLOCK_BOOTTIME),
                                boot, guardian)
        if 'baseline_at' not in journal and 'queued_at' not in journal:
            journal['baseline_at'] = time.time()
            state = read_json(CAMPAIGN / 'state.json')
            if (guardian_stop(guardian) or state.get('phase') != 'running'
                    or not watcher_owns_recovery(guardian, read_json(CAMPAIGN / 'watcher.json'))):
                raise RuntimeError('initial arm requires healthy running exact thread and live guardian watcher')
            initial = decision(state, journal, time.time(), backlog_present(CAMPAIGN),
                               time.clock_gettime(time.CLOCK_BOOTTIME))
            if initial.startswith('stop:'):
                raise RuntimeError(initial)
            atomic(OUTPUT / 'snapshot.json', snapshot(state))
            event(OUTPUT, dict(at=time.time(), event='baseline:start',
                  interval_seconds=INTERVAL, deadline=DEADLINE,
                  boot_deadline=journal['boot_deadline']))
        atomic(journal_path, journal)
        while True:
            # Tighten on a forward wall jump; a rollback cannot extend retained cutoff.
            guardian = read_json(GUARDIAN_JOURNAL)
            journal = bind_deadline(journal, time.time(), time.clock_gettime(time.CLOCK_BOOTTIME),
                                    boot, guardian)
            atomic(journal_path, journal)
            watcher = read_json(CAMPAIGN / 'watcher.json')
            owned = watcher_owns_recovery(guardian, watcher)
            stopped = ('stop:explicit_monitor_request' if (OUTPUT / 'stop-request.json').exists()
                       else guardian_stop(guardian) or
                       ('stop:watcher_identity_not_live' if not owned else None))
            if stopped:
                verdict = stopped
            else:
                verdict, journal = step(CAMPAIGN, OUTPUT, queue, journal, time.time(), owned, watcher.get('credit_timeout_recovery'), watchdog_checkpoint_owned(read_json(CAMPAIGN / 'state.json'), watcher) if owned else False, watcher)
            if verdict == 'queued' or verdict.startswith(('wait:watcher_', 'stop:')) or verdict == 'wait:queue_backlog':
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
