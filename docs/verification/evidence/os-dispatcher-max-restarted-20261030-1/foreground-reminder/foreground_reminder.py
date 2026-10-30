"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This foreground window's explicitly requested 15-minute priority reminders.
Queue text through the existing launcher inbox. No RPC, model turn, campaign
restart, physical workload, controller replacement, or native cleanup.
"""
import argparse
import ast
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from uuid import uuid4

HERE = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')
CAMPAIGN = REPO / '.git/os-autopilot'
LAUNCHER = REPO / 'scripts/run_os_goal.py'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
INTERVAL = 900


def read(path):
    raw = path.read_bytes()
    if len(raw) > 1 << 20:
        raise ValueError('bounded reminder metadata required')
    return json.loads(raw)


def atomic(path, value):
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temporary.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def birth(pid):
    try:
        fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    return dict(pid=pid, start=fields[19], ppid=int(fields[1]), state=fields[0])


def decision(state, config, wall, boot, mono, boot_id):
    caps = config['caps']
    if (boot_id != caps['boot_id'] or wall >= caps['deadline']
            or boot >= caps['boot_deadline'] or mono >= caps['monotonic_deadline']):
        return 'stop:weekly_ceiling'
    for observed, key in ((wall, 'weekly_effective_end'), (boot, 'weekly_effective_boot_end'),
                          (mono, 'weekly_effective_monotonic_end')):
        value = state.get(key)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or observed >= value):
            return 'stop:confirmed_weekly_ceiling'
    if state.get('thread_id') != config['target_thread']:
        return 'stop:campaign_thread_changed'
    if state.get('phase') != 'running' or (state.get('goal') or {}).get('status') != 'active' or state.get('stop_reason'):
        return 'stop:campaign_not_active'
    if any(state.get(k) for k in ('service_hold','policy_hold','auth_hold','billing_hold','last_error','last_failure','transport_uncertain')):
        return 'stop:preserved_hold'
    if ((state.get('settings') or {}).get('billing') or {}).get('mode') != 'included_only':
        return 'stop:billing_changed'
    usage = state.get('weekly_usage') or {}
    used = usage.get('usedPercent')
    if (usage.get('windowDurationMins') != 10080 or usage.get('canonicalResetsAt') != 1793774133
            or usage.get('sameAuthorizedPeriod') is not True or type(used) not in (int, float)
            or not math.isfinite(used) or not 0 <= used < 100):
        return 'stop:weekly_allowance'
    if state.get('weekly_confirmation_pending'):
        return 'wait:quota_confirmation'
    try:
        stamp = datetime.fromisoformat(state['heartbeat_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or not 0 <= wall - stamp.timestamp() < 120:
            return 'wait:heartbeat'
    except (KeyError, TypeError, ValueError, AttributeError):
        return 'wait:heartbeat'
    return 'ready'


def load_queue(expected):
    raw = LAUNCHER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('existing launcher queue source changed')
    wanted = {'utc', 'atomic_json', 'queue_instruction'}
    nodes = [n for n in ast.parse(raw, str(LAUNCHER)).body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    if {n.name for n in nodes} != wanted:
        raise ValueError('existing queue interface changed')
    scope = dict(os=os, json=json, tempfile=tempfile, Path=Path, datetime=datetime, timezone=timezone, uuid4=uuid4)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(LAUNCHER), 'exec'), scope)
    return scope['queue_instruction']


def verify(expected):
    raw = (HERE / 'SOURCE-PACKET.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('foreground reminder packet changed')
    packet = json.loads(raw)
    for name, digest in packet['sources'].items():
        if Path(name).name != name or hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest:
            raise ValueError('foreground reminder source changed: ' + name)
    config = read(HERE / 'CONFIG.json')
    if config['interval_seconds'] != INTERVAL or config['caps']['deadline'] != 1793774133:
        raise ValueError('explicit cadence or original ceiling changed')
    return config


def message(config, sequence):
    # Fresh bounded facts accompany each dispatch. Historical queue rows are
    # explicitly labeled as a baseline, never promoted to current acceptance.
    state = read(CAMPAIGN / 'state.json')
    root = REPO / 'docs/verification/os-milestones-20260914'
    import itertools
    with (root / 'CURRENT.md').open() as source:
        cursor = ''.join(itertools.islice(source, 30))
    work = {name: read(root / ('rust-cutover-' + name.lower() + '.json')) for name in ('M14','M15')}
    queue_path = REPO / config['baseline_function_queue']
    baseline = read(queue_path)
    rows = [dict(symbol=row['symbol'], scope=row.get('scope'), owner=row.get('owner'),
                 state=(row.get('actual_conversion_first_build') or {}).get('state'), gate=row.get('gate'))
            for row in baseline['rows']
            if (row.get('actual_conversion_first_build') or {}).get('state') != 'COMPILED_LINKED_RUST_CANDIDATE_GENERIC_C_BODY_ABSENT']
    snapshot = dict(at=time.time(), current_cursor=cursor,
        milestone_status={name: data.get('status') for name,data in work.items()},
        active_agents=[dict(name=row.get('name'), status=row.get('status'), turn_id=row.get('turn_id'))
                       for row in (state.get('agents') or {}).values() if row.get('status') == 'inProgress'],
        baseline_function_queue=str(queue_path), baseline_remaining_rows=rows,
        baseline_is_historical=True, native_release=False)
    context = HERE / ('context-%05d-%s.json' % (sequence, uuid4().hex[:8]))
    with context.open('x') as out:
        json.dump(snapshot, out, sort_keys=True, indent=2)
        out.flush(); os.fsync(out.fileno())
    agents = ', '.join(row['name'] or 'unnamed' for row in snapshot['active_agents']) or 'none observed'
    return (SCOPE + '\n[foreground-window-15min-SPECIFIC] origin_window=' + config['origin_window']
        + ' ONLY active campaign thread=' + config['target_thread'] + ' reminder=' + str(sequence)
        + '\nFresh bounded context: ' + str(context) + '. Active turns observed: ' + agents + '.\n'
        'The user requires VERY SPECIFIC steering from THIS WINDOW every15minutes, extremely fast fixes, M14 completion then immediate M15. '
        'Give concrete instructions and changed results; use the following execution priorities.\n'
        '1. M14 acceptance cursor: refresh the actual selected artifact and remaining original C names for '
        'F03 kernel/syscall.c and F06 arch/x86_64/kernel/syscall.c. The prior qualified queue in the context has23generic+5arch remaining; '
        'that count is historical until joined to the latest artifact. Keep four accepted file goals and35/35 functional closure distinct. '
        'For each changed remaining function record function name, C/Rust path, actual owner/active turn, implemented/selected/compiled-linked/native-retired state, '
        'exact blocking condition and next executable check. Retain unchanged rows; do not restart an inventory.\n'
        '2. Root physical critical path: reconcile Root70 against the actual consumed conversion build, accepted normal-retirement/caller evidence and later operations. '
        'The retained CONVERSION-FIRST-POSTJOIN-CURRENTFREE-PREPARATION-1/ROOT-NEXT.md identifies the prepared observation path. '
        'Name the exact outstanding custody or source-binding field, its owner and the next command/profile needed; refresh actual operation-specific review/admission. '
        'Do not repeat a completed cleanup or nonce, invent current-free, or wait for CURRENT119 native acceptance before independent source conversion/integration.\n'
        '3. Reuse concrete existing lanes, subject to their current allowed scope: composition owns the nonheld signal/perf group composite and exact paired C/Rust selectors/provider wiring; '
        'arch_source/signal_review own eligible diagnostic-budget/signal ABI and source-location metadata; '
        'cred_source owns do_setresuid/do_setresgid snapshot lifetime and host-error rollback contracts; '
        'mmap_source owns eligible do_mmap/do_fork VM references, writer reservation/mutator/teardown participation and child/enqueue pins; '
        'dispatch_source owns do_syscall/util_thread initialized wire args and caller/host lifetimes. '
        'Verify actual current owners and paths before assigning; keep disjoint private writes and one canonical compositor. '
        'Use followup_task to start each dependency-ready idle owner; each assignment names the exact function/path, fix, output patch and next check. '
        'Retain precise unresolved conditions where a lane is blocked; do not duplicate a port or create filler reviews. '
        'All held requests, equivalent replay exclusions and undefined ABI/behavior domains remain held.\n'
        '4. Integrate compatible completed fixes into one candidate and run changed Rust/C compilation plus link once fresh physical controls allow. '
        'For each failure capture the actual command, first meaningful compiler/link error, owning file/function and bounded correction; '
        'fix it immediately and rerun the affected check. Reuse SDK21, matching accepted Rust, unaffected objects and existing original389 metadata oracle. '
        'Finish supported default ownership/zero-C and matching application/lifecycle/native validation before file retirement or M14 acceptance.\n'
        '5. At each coherent fix checkpoint, push promptly using python3 -B scripts/push_os_checkpoint.py origin <engineering-branch>. '
        'Report actual commit, changed files, checks passed and fetched verification; preserve failures and dirty work. '
        'Report changed function/build/native/retirement counts and elapsed blocked time honestly; unknown timing stays unknown. '
        'State the NEXT command or concrete deliverable and its owner instead of a generic progress claim.\n'
        '6. As soon as original-scope M14 acceptance is recorded, dispatch M15 automatically: reuse existing Rust and artifacts; '
        'assign disjoint MM adapters, user CLIs/programs, BFD adapters and libihk API owners, enumerate at least30 distinct original C functions per coherent batch, '
        'then combined default build/link and matching consumer/native checks before retirement. Complete a smaller final remainder without padding.\n'
        'Relay the applicable concrete instructions to currently active agents. Keep this steering brief enough that engineering continues. '
        'Preserve ownership/resource and service/account controls, weekly included-only exhaustion/original reset ceiling and no prepaid fallback. '
        'This reminder grants no workload, cleanup, retry, acceptance or budget authority; pause/stop/hold remains authoritative.')


def run(config, expected):
    if os.getuid() != 1000 or os.geteuid() != 1000 or os.sched_getaffinity(0) != {0}:
        raise ValueError('ordinary UID1000/CPU0-only reminder required')
    with (HERE / 'reminder.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (HERE / 'status.json').exists():
            raise ValueError('retained reminder state requires explicit reconciliation; never replay')
        queue = load_queue(config['launcher_sha256'])
        status = dict(scope=SCOPE, origin_window=config['origin_window'], target_thread=config['target_thread'],
             owner=birth(os.getpid()), interval_seconds=INTERVAL, source_packet_sha256=expected,
             deliveries=config['previous_deliveries'], phase='running', started_at=time.time(),
             replacement_notice_pending=True, next_due_monotonic=time.monotonic())
        atomic(HERE / 'status.json', status)
        while True:
            state = read(CAMPAIGN / 'state.json')
            verdict = decision(state, config, time.time(), time.clock_gettime(time.CLOCK_BOOTTIME),
                       time.monotonic(), Path('/proc/sys/kernel/random/boot_id').read_text().strip())
            if (HERE / 'STOP.json').exists():
                verdict = 'stop:foreground_reminders_cancelled'
            if verdict.startswith('stop:'):
                status.update(phase='stopped', reason=verdict, stopped_at=time.time())
                atomic(HERE / 'status.json', status)
                return
            if all(read(REPO / 'docs/verification/os-milestones-20260914' / filename).get('status') == 'complete'
                   for filename in ('rust-cutover-m14.json', 'rust-cutover-m15.json')):
                status.update(phase='stopped', reason='M14_and_M15_accepted', stopped_at=time.time())
                atomic(HERE / 'status.json', status)
                return
            if verdict == 'ready' and time.monotonic() >= status['next_due_monotonic']:
                # Bound to the live current worker/server and guardian; no controller action.
                control = read(Path(config['guardian_journal']))
                guardian = birth(config['guardian']['pid'])
                watcher = control.get('replacement', control['original'])['watcher']
                actual = birth(watcher['pid'])
                if (guardian is None or guardian['start'] != config['guardian']['start'] or guardian['state'] in ('Z','X')
                        or control.get('packet_sha256') != config['guardian_packet_sha256']
                        or time.clock_gettime(time.CLOCK_BOOTTIME) >= control['boot_deadline']
                        or actual is None or actual['start'] != watcher['start'] or actual['state'] in ('Z','X')
                        or control.get('transition_hold') or str(control.get('last_action','')).startswith(('HOLD_','STOP_'))):
                    raise ValueError('current guardian/watcher unavailable; no reminder queued')
                for role in ('worker', 'server'):
                    actor = birth(state[role + '_pid'])
                    expected_parent = watcher['pid'] if role == 'worker' else state['worker_pid']
                    if (actor is None or actor['start'] != state[role + '_start'] or actor['state'] in ('Z','X')
                            or actor['ppid'] != expected_parent):
                        raise ValueError('current model actor changed; no reminder queued')
                # Existing pending messages finish first; one reminder cannot accumulate.
                if any(list((CAMPAIGN / 'instructions' / stage).glob('*.json')) for stage in ('pending','sending')):
                    time.sleep(5)
                    continue
                sequence = status['deliveries'] + 1
                text = message(config, sequence)
                verify(expected)
                fresh = read(CAMPAIGN / 'state.json')
                if (decision(fresh, config, time.time(), time.clock_gettime(time.CLOCK_BOOTTIME), time.monotonic(),
                             Path('/proc/sys/kernel/random/boot_id').read_text().strip()) != 'ready'
                        or any(fresh.get(key) != state.get(key) for key in ('thread_id','worker_pid','worker_start','server_pid','server_start'))):
                    time.sleep(5)
                    continue
                # Intent precedes queue mutation; an uncertain result is held without replay.
                status.update(phase='intent', intent_at=time.time(), sequence=sequence,
                              message_sha256=hashlib.sha256(text.encode()).hexdigest())
                atomic(HERE / 'status.json', status)
                ident = queue(CAMPAIGN, text)
                receipt = dict(sequence=sequence, instruction_id=ident, queued_at=time.time(),
                               origin_window=config['origin_window'], target_thread=config['target_thread'],
                               message_sha256=status['message_sha256'])
                with (HERE / ('delivery-%05d.json' % sequence)).open('x') as out:
                    json.dump(receipt, out, sort_keys=True, indent=2)
                    out.flush(); os.fsync(out.fileno())
                next_due = time.monotonic() + INTERVAL
                if status.pop('replacement_notice_pending', False):
                    carried = config['carried_next_due_monotonic']
                    if carried > time.monotonic():
                        next_due = carried
                status.update(phase='running', deliveries=sequence, last_instruction_id=ident,
                              last_queued_at=receipt['queued_at'], next_due_monotonic=next_due)
                atomic(HERE / 'status.json', status)
                print(json.dumps(receipt), flush=True)
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    config = verify(args.source_sha256)
    if not args.run:
        print('PASS_SOURCE_ONLY_NO_REMINDER_QUEUED')
        return
    try:
        run(config, args.source_sha256)
    except Exception as error:
        atomic(HERE / 'HOLD.json', dict(scope=SCOPE, at=time.time(), error_type=type(error).__name__,
               error=str(error), automatic_retry=False, origin_window=config['origin_window']))
        raise


if __name__ == '__main__':
    main()
