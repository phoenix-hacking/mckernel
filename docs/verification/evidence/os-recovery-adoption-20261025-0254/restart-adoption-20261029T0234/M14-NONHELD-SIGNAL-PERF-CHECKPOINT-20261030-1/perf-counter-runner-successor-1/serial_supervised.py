#!/home/holden/anaconda3/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only runner awaiting independent inspection and fresh dispatcher admission.
The caller must perform the review's control, tool-version, resource and floor checks.
"""
import hashlib
import json
import os
import resource
import signal
import subprocess
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "perf-counter-failure-source-1"
REPO = Path('/home/holden/mckernel')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
PARENT = REPO / 'docs/verification/evidence/native-cheap-profile-review-20261017.json'
BINDINGS = {
    HERE / 'INDEPENDENT-OWNERSHIP-AND-MICROTEST-REVIEW.md': '95c0915a279f80f2424e2bb71b35877eed3680df54994cfbb159672f33e3c62a',
    HERE / 'RESULT.json': 'a66d430c6326a528d61769c54703a9d4157382c171f90b03c59c2627a6c1cf33',
    HERE / 'PREIMAGE.rs': 'a4d5450852b27bee664c7bf60ed5633c8dc463ed2ee91e0ca9c9856ca6383de1',
    HERE / 'f03_perf_entry_candidate.rs': '9f53dceac6e97cf7c961780362de729b13573f547634e9f98859a494fb651bf7',
    HERE / 'COUNTER-FAILURE.PRIVATE.patch': '86a71b0381d4471b15704fc9b3cfa1494c87173f2bb4a0cbca1502ca2be2c425',
    HERE / 'counter_wrapper_fixture.rs': 'afc8b3023230ca2bd7f3bccd344b3fbf77270e6aa5fe0f9ff2d5e441f621003f',
    HERE / 'candidate-wrapper.rs': '3450bede2497331ad47debc9f7568b962e4b319fff0b95aa680bda3bf9a90e94',
    PARENT: 'cd30aaf1caec5da84a7a34716d837181684f4e8be5a6c959f25bb557dd69309f',
}
TOOLS = {
    RUSTC: '028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1',
    '/usr/bin/cc': '6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f',
    '/usr/bin/timeout': '91db1e64064f0bf5ee99abda3a054cc6f05748dad2af5a145f890c9172d28d73',
    '/usr/bin/prlimit': '06a57e4767f1bdfcc8c5a39b4b58decb9366447b007a8bdd9d6b12d1e6698d8c',
    '/usr/bin/taskset': '28f2dd426247d7d1d794c0fb8a723efc6a1ae3c56393a238b180fe9a0dc32f1c',
    '/home/holden/anaconda3/bin/python3.9': '8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb',
}
INITIAL_ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C',
               'PYTHONDONTWRITEBYTECODE': '1', 'MCKERNEL_RUSTC_1_92': RUSTC,
               'HOME': '/nonexistent', 'TMPDIR': '/nonexistent'}
LIMITS = ((resource.RLIMIT_AS, 2147483648), (resource.RLIMIT_CPU, 150),
          (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_FSIZE, 67108864),
          (resource.RLIMIT_CORE, 0))
HELPERS = {'cc', 'gcc', 'gcc-9', 'x86_64-linux-gnu-gcc', 'x86_64-linux-gnu-gcc-9',
           'collect2', 'ld', 'ld.bfd', 'x86_64-linux-gnu-ld', 'as', 'x86_64-linux-gnu-as'}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verified(path, wanted):
    actual = digest(path)
    if actual != wanted:
        raise RuntimeError('hash mismatch: ' + str(path))
    return actual


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


# One supervisor owns the worker's process group; the worker and both command
# families inherit it. The leader remains unreaped while any group signal is sent.
STOP = None

def stop_request(signum, _frame):
    global STOP
    STOP = signum


def census(group):
    members = []
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        try:
            raw = (item / 'stat').read_text()
            stat = raw[raw.rfind(')') + 2:].split()
            if int(stat[2]) != group:
                continue
            info = {'pid': int(item.name), 'state': stat[0], 'ppid': int(stat[1]),
                    'start_ticks': int(stat[19]), 'rss': 0, 'exe': '<zombie>'}
            if stat[0] != 'Z':
                info['exe'] = os.readlink(str(item / 'exe'))
                status = (item / 'status').read_text()
                info['rss'] = next((int(x.split()[1]) * 1024 for x in status.splitlines()
                                    if x.startswith('VmRSS:')), 0)
            members.append(info)
        except FileNotFoundError:
            continue
    return members


def worker(root):
    # The supervisor handles all deadline/termination actions. Default signals
    # avoid a Python exception stranding a child in the Popen launch window.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    record = {'status': 'STAGING', 'external_admission_required': True}
    try:
        record['inputs'] = {str(p): verified(p, h) for p, h in BINDINGS.items()}
        record['tools'] = {p: verified(p, h) for p, h in TOOLS.items()}
        binding = json.loads((HERE / 'RESULT.json').read_text())['binding']['inputs']
        record['provider_inputs'] = {p: verified(p, h) for p, h in binding.items()}
        source = (HERE / 'f03_perf_entry_candidate.rs').read_text()
        start = source.index('unsafe extern "C" fn perf_entry_counter_alloc_or_release(')
        end = source.index('\n}\n', start) + 3
        wrapper = (HERE / 'candidate-wrapper.rs').read_bytes()
        if source[start:end].encode() != wrapper:
            raise RuntimeError('wrapper is not exact complete candidate extraction')
        case = root / 'case'; case.mkdir(mode=0o700)
        home = root / 'home'; home.mkdir(mode=0o700)
        tmp = root / 'tmp'; tmp.mkdir(mode=0o700)
        for original, dest in ((HERE / 'counter_wrapper_fixture.rs', case / 'fixture.rs'),
                               (HERE / 'candidate-wrapper.rs', case / 'candidate-wrapper.rs')):
            dest.write_bytes(original.read_bytes()); os.chmod(dest, 0o400)
            verified(dest, BINDINGS[original])
        if source[start:end].encode() != (case / 'candidate-wrapper.rs').read_bytes():
            raise RuntimeError('staged wrapper mismatch')
        env = dict(INITIAL_ENV, HOME=str(home), TMPDIR=str(tmp))
        os.environ.clear(); os.environ.update(env)
        record.update({'status': 'STAGED', 'environment': env,
                       'affinity': sorted(os.sched_getaffinity(0))})
        write_json(root / 'worker.json', record)
        executable = case / 'fixture'
        stages = [
            ('compile', [RUSTC, '--edition=2021', '--test', '-Dwarnings',
                         str(case / 'fixture.rs'), '-o', str(executable)]),
            ('fixture', [str(executable), '--test-threads=1']),
        ]
        for name, argv in stages:
            # Intent is persisted before entering Popen; interrupted launch is
            # not counted as a result and the supervisor retains the whole group.
            stage = {'argv': argv, 'status': 'LAUNCH_INTENT'}
            write_json(root / (name + '.json'), stage)
            with (root / (name + '.stdout')).open('xb') as out, (root / (name + '.stderr')).open('xb') as err:
                proc = subprocess.Popen(argv, cwd=str(REPO), env=env, stdin=subprocess.DEVNULL,
                                        stdout=out, stderr=err, close_fds=True)
                stage.update({'pid': proc.pid, 'status': 'RUNNING'})
                write_json(root / (name + '.json'), stage)
                stage['returncode'] = proc.wait()
                stage['status'] = 'LEADER_JOINED'
                write_json(root / (name + '.json'), stage)
            if stage['returncode'] != 0:
                record['status'] = name.upper() + '_FAILED'
                write_json(root / 'worker.json', record)
                return 1
        record['status'] = 'PASS_MICROTEST_PENDING_GROUP_RETIREMENT'
        write_json(root / 'worker.json', record)
        return 0
    except Exception as error:
        record['status'] = 'STOPPED_ERROR'
        record['error'] = type(error).__name__ + ': ' + str(error)
        write_json(root / 'worker.json', record)
        return 1


def leader_state(pid):
    # waitid WNOWAIT leaves the group-leader PID pinned until explicit waitpid.
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def decision(now, started, signal_number, members, finished, bad_executable):
    # Independent supervisor remains runnable while staging or Popen is blocked.
    live = [x for x in members if x['state'] != 'Z']
    if signal_number is not None:
        return 'SUPERVISOR_SIGNAL_%s' % signal_number
    if now - started >= 180:
        return 'OUTER_DEADLINE'
    if len(members) + 1 > 8:
        return 'PROCESS_COUNT'
    if sum(x['rss'] for x in members) > 2147483648:
        return 'CHILD_RSS_PLANNING_LIMIT'
    if bad_executable:
        return 'UNEXPECTED_EXECUTABLE_AFTER_GRACE'
    if finished is not None and live:
        return 'WORKER_EXIT_WITH_LIVE_GROUP'
    return None


def group_retirement_state(leader_finished, other_members):
    return 'JOINABLE' if leader_finished and not other_members else 'UNKNOWN_GROUP_RETIREMENT'


def main():
    started = time.monotonic()
    if dict(os.environ) != INITIAL_ENV:
        raise RuntimeError('runner requires exact env -i launcher environment')
    if 6 not in os.sched_getaffinity(0):
        raise RuntimeError('CPU6 not in allowed affinity')
    os.sched_setaffinity(0, {6})
    for kind, value in LIMITS:
        soft, hard = resource.getrlimit(kind)
        if ((hard != resource.RLIM_INFINITY and hard < value) or
                (soft != resource.RLIM_INFINITY and soft < value)):
            raise RuntimeError('existing rlimit lower than reviewed limit; no widening')
        resource.setrlimit(kind, (value, value))
    signal.signal(signal.SIGTERM, stop_request)
    signal.signal(signal.SIGINT, stop_request)
    root = Path(tempfile.mkdtemp(prefix='native-cheap-20261017-', dir=str(SCRATCH)))
    os.chmod(root, 0o700)
    report = {'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
              'status': 'SUPERVISOR_START', 'root': str(root), 'deadline_seconds': 180,
              'external_watchdog_required': True, 'external_admission_required': True}
    write_json(root / 'supervisor.json', report)
    if time.monotonic() - started >= 180 or STOP is not None:
        report['status'] = 'STOP_BEFORE_FORK'
        write_json(root / 'supervisor.json', report)
        return 1
    # Block cancellation around fork/PGID publication: once unblocked the
    # supervisor has the real child PID and may address its anchored group.
    blocked = {signal.SIGTERM, signal.SIGINT}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    pid = os.fork()
    if pid == 0:
        try:
            os.setpgid(0, 0)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_SETMASK, previous)
            os._exit(worker(root))
        except BaseException:
            os._exit(127)
    report.update({'worker_pid': pid, 'expected_pgid': pid})
    try:
        try:
            os.setpgid(pid, pid)
        except PermissionError:
            pass  # child may already have entered its own group
        if os.getpgid(pid) != pid:
            raise RuntimeError('worker did not establish exclusive process group')
        raw = Path('/proc/%d/stat' % pid).read_text()
        report['worker_start_ticks'] = int(raw[raw.rfind(')') + 2:].split()[19])
        report['status'] = 'GROUP_OWNED'
        write_json(root / 'supervisor.json', report)
    except Exception as error:
        # No unverified PID or process group is signaled. Preserve UNKNOWN.
        report.update({'status': 'UNKNOWN_GROUP_ESTABLISHMENT', 'error': str(error)})
        write_json(root / 'supervisor.json', report)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)
        return 1
    signal.pthread_sigmask(signal.SIG_SETMASK, previous)
    reason = None
    unknown_first = {}
    last = []
    try:
        while True:
            now = time.monotonic()
            last = census(pid)
            finished = leader_state(pid)
            live = [x for x in last if x['state'] != 'Z']
            bad = []
            for entry in live:
                path = str(Path(entry['exe']).resolve())
                name = Path(path).name
                allowed = (entry['pid'] == pid and path == '/home/holden/anaconda3/bin/python3.9') or path == str(Path(RUSTC).resolve()) or path == str((root / 'case/fixture').resolve()) or (name in HELPERS and (path.startswith('/usr/bin/') or path.startswith('/usr/lib/gcc/')))
                key = (entry['pid'], entry['start_ticks'])
                if not allowed:
                    unknown_first.setdefault(key, now)
                    if now - unknown_first[key] > 2.0:
                        bad.append(entry)
            reason = decision(now, started, STOP, last, finished, bad)
            if reason:
                break
            if finished is not None and not live:
                break
            time.sleep(0.05)
        if reason:
            report.update({'reason': reason, 'pre_termination_group': last})
            # Leader is still an unreaped child: its PID anchors this group.
            os.killpg(pid, signal.SIGTERM)
            stop_deadline = time.monotonic() + 4.0
            while time.monotonic() < stop_deadline:
                last = census(pid)
                if leader_state(pid) is not None and not [x for x in last if x['state'] != 'Z']:
                    break
                time.sleep(0.05)
            if [x for x in last if x['state'] != 'Z']:
                os.killpg(pid, signal.SIGKILL)
                kill_deadline = time.monotonic() + 0.8
                while time.monotonic() < kill_deadline:
                    last = census(pid)
                    if leader_state(pid) is not None and not [x for x in last if x['state'] != 'Z']:
                        break
                    time.sleep(0.05)
        # Other zombies cannot be reaped by us; they prevent a retirement claim.
        last = census(pid)
        state = leader_state(pid)
        others = [x for x in last if x['pid'] != pid]
        report['final_group_before_join'] = last
        if group_retirement_state(state is not None, others) != 'JOINABLE':
            report['status'] = 'UNKNOWN_GROUP_RETIREMENT'
        else:
            joined, status = os.waitpid(pid, 0)
            report['joined'] = {'pid': joined, 'wait_status': status}
            record_path = root / 'worker.json'
            worker_result = json.loads(record_path.read_text()) if record_path.exists() else {}
            report['worker_result'] = worker_result
            report['status'] = ('PASS_MICROTEST_ONLY' if not reason and os.WIFEXITED(status) and
                                os.WEXITSTATUS(status) == 0 and
                                worker_result.get('status') == 'PASS_MICROTEST_PENDING_GROUP_RETIREMENT'
                                else 'STOPPED_OR_FAILED')
    except BaseException as error:
        # Only an unreaped child with the recorded birth and group may anchor
        # cleanup. If any check fails, signal nobody and retain UNKNOWN.
        report.update({'status': 'UNKNOWN_MONITOR_ERROR', 'error': repr(error), 'last_group': last})
        try:
            leader_state(pid)  # fails if the child was already reaped
            stat = Path('/proc/%d/stat' % pid).read_text()
            fields = stat[stat.rfind(')') + 2:].split()
            if int(fields[2]) != pid or int(fields[19]) != report['worker_start_ticks']:
                raise RuntimeError('group anchor identity changed')
            os.killpg(pid, signal.SIGTERM)
            time.sleep(4.0)
            leader_state(pid)
            stat = Path('/proc/%d/stat' % pid).read_text()
            fields = stat[stat.rfind(')') + 2:].split()
            if int(fields[2]) == pid and int(fields[19]) == report['worker_start_ticks']:
                os.killpg(pid, signal.SIGKILL)
                report['exception_cleanup'] = 'TERM_AND_KILL_SENT_RETIREMENT_UNKNOWN'
            else:
                report['exception_cleanup'] = 'ANCHOR_CHANGED_RETIREMENT_UNKNOWN'
        except BaseException as cleanup_error:
            report['exception_cleanup'] = 'UNKNOWN: ' + repr(cleanup_error)
    write_json(root / 'supervisor.json', report)
    print(json.dumps({'root': str(root), 'status': report['status']}))
    return 0 if report['status'] == 'PASS_MICROTEST_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
