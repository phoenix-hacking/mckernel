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

HERE = Path(__file__).resolve().parent
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


def group_members(pgid, fixture):
    members = []
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        try:
            raw = (item / 'stat').read_text()
            fields = raw[raw.rfind(')') + 2:].split()
            if int(fields[2]) != pgid:
                continue
            if fields[0] == 'Z':
                members.append({'pid': int(item.name), 'start_ticks': int(fields[19]),
                                'exe': '<zombie>', 'rss': 0, 'allowed': True})
                continue
            exe = os.readlink(str(item / 'exe'))
            status = (item / 'status').read_text()
            rss = next((int(line.split()[1]) * 1024 for line in status.splitlines()
                        if line.startswith('VmRSS:')), 0)
            resolved = str(Path(exe).resolve())
            allowed = (resolved == str(Path(RUSTC).resolve()) or resolved == str(fixture.resolve()) or
                       (Path(resolved).name in HELPERS and
                        (resolved.startswith('/usr/bin/') or resolved.startswith('/usr/lib/gcc/'))))
            members.append({'pid': int(item.name), 'start_ticks': int(fields[19]),
                            'exe': resolved, 'rss': rss, 'allowed': allowed})
        except (FileNotFoundError, ProcessLookupError):
            continue
    return members


def stop_owned(process, deadline, reason):
    # Never signal an unrelated group. Keep the leader unreaped while signaling.
    if process.poll() is not None or os.getpgid(process.pid) != process.pid:
        return {'reason': reason, 'result': 'UNKNOWN_LEADER_NOT_LIVE'}
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=max(0.0, min(4.8, deadline - time.monotonic())))
        return {'reason': reason, 'result': 'TERM_JOINED', 'returncode': process.returncode}
    except subprocess.TimeoutExpired:
        if process.poll() is None and os.getpgid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGKILL)
            try:
                process.wait(timeout=max(0.0, deadline - time.monotonic()))
                return {'reason': reason, 'result': 'KILL_JOINED', 'returncode': process.returncode}
            except subprocess.TimeoutExpired:
                return {'reason': reason, 'result': 'UNKNOWN_KILL_SENT_NOT_JOINED'}
        return {'reason': reason, 'result': 'UNKNOWN_RETIREMENT'}


def run_one(name, argv, root, env, deadline, fixture):
    result = {'argv': argv, 'stage': name}
    with (root / (name + '.stdout')).open('xb') as stdout, (root / (name + '.stderr')).open('xb') as stderr:
        proc = subprocess.Popen(argv, cwd=str(REPO), env=env, stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr, start_new_session=True, close_fds=True)
        result.update({'pid': proc.pid, 'pgid': proc.pid})
        try:
            while proc.poll() is None:
                now = time.monotonic()
                members = group_members(proc.pid, fixture)
                reason = None
                if now >= deadline:
                    reason = 'OUTER_TIMEOUT'
                elif len(members) > 7:
                    reason = 'OWNED_PROCESS_COUNT_EXCEEDS_EIGHT_INCLUDING_CONTROLLER'
                elif any(not m['allowed'] for m in members):
                    reason = 'UNEXPECTED_OWNED_EXECUTABLE'
                elif sum(m['rss'] for m in members) > 2147483648:
                    reason = 'OWNED_CHILD_RSS_EXCEEDS_PLANNING_SHARE'
                if reason:
                    result['last_members'] = members
                    result['termination'] = stop_owned(proc, time.monotonic() + 5.0, reason)
                    break
                time.sleep(min(0.05, max(0.0, deadline - now)))
        except Exception as error:
            result['monitor_error'] = type(error).__name__ + ': ' + str(error)
            result['termination'] = stop_owned(proc, time.monotonic() + 5.0, 'MONITOR_ERROR')
        result['returncode'] = proc.poll()
        # A nonempty group after the leader joined is retained as UNKNOWN;
        # it is not evidence of cleanup and no reused PID/group is signaled.
        remaining = group_members(proc.pid, fixture)
        result['remaining_group'] = remaining
        result['joined'] = proc.returncode is not None and not remaining
    write_json(root / (name + '.json'), result)
    return result


def interrupted(signum, _frame):
    raise RuntimeError('controller received signal ' + str(signum))


def main():
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
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
    deadline = time.monotonic() + 180.0
    root = Path(tempfile.mkdtemp(prefix='native-cheap-20261017-', dir=str(SCRATCH)))
    os.chmod(root, 0o700)
    record = {'status': 'STAGING', 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
              'root': str(root), 'external_admission_required': True,
              'timeout_seconds': 180, 'rlimits_per_process': dict((str(k), v) for k, v in LIMITS)}
    try:
        record['inputs'] = {str(p): verified(p, h) for p, h in BINDINGS.items()}
        record['tools'] = {p: verified(p, h) for p, h in TOOLS.items()}
        result_binding = json.loads((HERE / 'RESULT.json').read_text())['binding']['inputs']
        record['provider_inputs'] = {p: verified(p, h) for p, h in result_binding.items()}
        source = (HERE / 'f03_perf_entry_candidate.rs').read_text()
        start = source.index('unsafe extern "C" fn perf_entry_counter_alloc_or_release(')
        end = source.index('\n}\n', start) + 3
        if source[start:end].encode() != (HERE / 'candidate-wrapper.rs').read_bytes():
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
        record['environment'] = env
        record['controller_affinity'] = sorted(os.sched_getaffinity(0))
        record['status'] = 'STAGED'
        write_json(root / 'run.json', record)
        executable = case / 'fixture'
        if time.monotonic() >= deadline:
            raise RuntimeError('outer deadline elapsed during staging')
        compiled = run_one('compile', [RUSTC, '--edition=2021', '--test', '-Dwarnings',
                                     str(case / 'fixture.rs'), '-o', str(executable)],
                           root, env, deadline, executable)
        record['compile'] = compiled
        if compiled['returncode'] != 0 or not compiled['joined'] or 'termination' in compiled:
            record['status'] = 'COMPILE_FAILED_OR_RETIREMENT_UNKNOWN'
        elif time.monotonic() >= deadline:
            record['status'] = 'OUTER_TIMEOUT_BEFORE_FIXTURE'
        else:
            tested = run_one('fixture', [str(executable), '--test-threads=1'],
                             root, env, deadline, executable)
            record['fixture'] = tested
            record['status'] = ('PASS_MICROTEST_ONLY' if tested['returncode'] == 0 and
                                tested['joined'] and 'termination' not in tested
                                else 'TEST_FAILED_OR_RETIREMENT_UNKNOWN')
    except Exception as error:
        record['status'] = 'STOPPED_ERROR'
        record['error'] = type(error).__name__ + ': ' + str(error)
    write_json(root / 'run.json', record)
    print(json.dumps({'root': str(root), 'status': record['status']}))
    return 0 if record['status'] == 'PASS_MICROTEST_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
