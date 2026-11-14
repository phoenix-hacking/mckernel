#!/home/holden/anaconda3/bin/python3
"""SOURCE-ONLY candidate; requires independent review and fresh admission.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Caller owns admission, controls, resources, tool versions and outer caller custody.
"""
import hashlib
import json
import os
import resource
import select
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / 'perf-counter-failure-source-1'
SCRATCH = Path('/home/holden/mckernel-work/scratch')
REPO = Path('/home/holden/mckernel')
PYTHON = '/home/holden/anaconda3/bin/python3.9'
TIMEOUT = '/usr/bin/timeout'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
INPUTS = {
    BASE / 'INDEPENDENT-OWNERSHIP-AND-MICROTEST-REVIEW.md': '95c0915a279f80f2424e2bb71b35877eed3680df54994cfbb159672f33e3c62a',
    BASE / 'RESULT.json': 'a66d430c6326a528d61769c54703a9d4157382c171f90b03c59c2627a6c1cf33',
    BASE / 'PREIMAGE.rs': 'a4d5450852b27bee664c7bf60ed5633c8dc463ed2ee91e0ca9c9856ca6383de1',
    BASE / 'f03_perf_entry_candidate.rs': '9f53dceac6e97cf7c961780362de729b13573f547634e9f98859a494fb651bf7',
    BASE / 'COUNTER-FAILURE.PRIVATE.patch': '86a71b0381d4471b15704fc9b3cfa1494c87173f2bb4a0cbca1502ca2be2c425',
    BASE / 'counter_wrapper_fixture.rs': 'afc8b3023230ca2bd7f3bccd344b3fbf77270e6aa5fe0f9ff2d5e441f621003f',
    BASE / 'candidate-wrapper.rs': '3450bede2497331ad47debc9f7568b962e4b319fff0b95aa680bda3bf9a90e94',
    REPO / 'docs/verification/evidence/native-cheap-profile-review-20261017.json': 'cd30aaf1caec5da84a7a34716d837181684f4e8be5a6c959f25bb557dd69309f',
}
TOOLS = {
    RUSTC: '028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1',
    '/usr/bin/cc': '6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f',
    TIMEOUT: '91db1e64064f0bf5ee99abda3a054cc6f05748dad2af5a145f890c9172d28d73',
    '/usr/bin/prlimit': '06a57e4767f1bdfcc8c5a39b4b58decb9366447b007a8bdd9d6b12d1e6698d8c',
    '/usr/bin/taskset': '28f2dd426247d7d1d794c0fb8a723efc6a1ae3c56393a238b180fe9a0dc32f1c',
    PYTHON: '8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb',
}
ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C',
       'PYTHONDONTWRITEBYTECODE': '1', 'MCKERNEL_RUSTC_1_92': RUSTC,
       'HOME': '/nonexistent', 'TMPDIR': '/nonexistent'}
LIMITS = ((resource.RLIMIT_AS, 2147483648), (resource.RLIMIT_CPU, 150),
          (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_FSIZE, 67108864),
          (resource.RLIMIT_CORE, 0))
HELPERS = {'cc', 'gcc', 'gcc-9', 'x86_64-linux-gnu-gcc', 'x86_64-linux-gnu-gcc-9',
           'collect2', 'ld', 'ld.bfd', 'x86_64-linux-gnu-ld', 'as', 'x86_64-linux-gnu-as'}
STOP = None


def stop(signum, _frame):
    global STOP
    STOP = signum


def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as out:
        json.dump(obj, out, sort_keys=True, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(path, wanted):
    value = digest(path)
    if value != wanted:
        raise RuntimeError('binding mismatch: ' + str(path))
    return value


def stat_pid(pid):
    raw = Path('/proc/%d/stat' % pid).read_text()
    f = raw[raw.rfind(')') + 2:].split()
    return {'pid': pid, 'state': f[0], 'ppid': int(f[1]), 'pgid': int(f[2]),
            'sid': int(f[3]), 'start': int(f[19])}


def census(group):
    result = []
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        try:
            s = stat_pid(int(item.name))
            if s['pgid'] != group:
                continue
            s['rss'] = 0
            s['exe'] = '<zombie>'
            if s['state'] != 'Z':
                s['exe'] = os.readlink(str(item / 'exe'))
                status = (item / 'status').read_text()
                s['rss'] = next((int(x.split()[1]) * 1024 for x in status.splitlines()
                                 if x.startswith('VmRSS:')), 0)
            result.append(s)
        except FileNotFoundError:
            continue
    return result


def unreaped(pid):
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def check_anchor(pid, born):
    # waitid also establishes that the owner has not reaped its direct child.
    unreaped(pid)
    s = stat_pid(pid)
    if s['start'] != born or s['pgid'] != pid or s['sid'] != pid:
        raise RuntimeError('unproven group anchor')
    return s


def check_handshake(anchor, worker, expected_pid, expected_start=None):
    if (anchor['pid'] != anchor['pgid'] or anchor['pid'] != anchor['sid'] or
            worker['pid'] != expected_pid or worker['ppid'] != anchor['pid'] or
            worker['pgid'] != anchor['pid'] or worker['sid'] != anchor['sid'] or
            worker['state'] == 'Z' or
            (expected_start is not None and worker['start'] != expected_start)):
        raise RuntimeError('unproven gated worker identity')


def read_message(fd, deadline):
    data = bytearray()
    while b'\n' not in data:
        left = deadline - time.monotonic()
        if left <= 0 or STOP is not None:
            raise RuntimeError('handshake deadline or stop')
        if not select.select([fd], [], [], min(left, 0.1))[0]:
            continue
        chunk = os.read(fd, 256)
        if not chunk:
            raise RuntimeError('handshake EOF')
        data.extend(chunk)
        if len(data) > 256:
            raise RuntimeError('handshake too long')
    if not data.endswith(b'\n') or data.count(b'\n') != 1:
        raise RuntimeError('malformed handshake')
    return bytes(data[:-1])


def retire_stage(proc, group, fixed_pids):
    """Keep direct child unreaped until no other family members remain.

    Owner's watchdog supplies the deadline. Any inability to observe proof raises;
    fixture never launches on failure. A zombie descendant is not retirement.
    """
    while True:
        finished = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        members = census(group)
        ids = {x['pid'] for x in members}
        if not fixed_pids.issubset(ids) or proc.pid not in ids:
            raise RuntimeError('UNKNOWN stage membership')
        outsiders = ids - fixed_pids - {proc.pid}
        if finished is not None and not outsiders:
            child = next(x for x in members if x['pid'] == proc.pid)
            if child['state'] != 'Z':
                raise RuntimeError('UNKNOWN child state')
            return proc.wait(), members
        time.sleep(0.05)


def guarded_stage(proc, group, fixed_pids):
    """A fixture caller must use this return value, never proc.wait alone."""
    return retire_stage(proc, group, fixed_pids)


def run_stages(root, env, group, fixed):
    case = root / 'case'
    executable = case / 'fixture'
    stages = [('compile', [RUSTC, '--edition=2021', '--test', '-Dwarnings',
                           str(case / 'fixture.rs'), '-o', str(executable)]),
              ('fixture', [str(executable), '--test-threads=1'])]
    for name, argv in stages:
        stage = {'argv': argv, 'status': 'LAUNCH_INTENT'}
        write_json(root / (name + '.json'), stage)
        with (root / (name + '.stdout')).open('xb') as out, (root / (name + '.stderr')).open('xb') as err:
            proc = subprocess.Popen(argv, cwd=str(REPO), env=env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, close_fds=True)
            stage.update({'pid': proc.pid, 'status': 'RUNNING'})
            write_json(root / (name + '.json'), stage)
            status, retired_members = guarded_stage(proc, group, fixed)
            stage.update({'returncode': status, 'status': 'FAMILY_RETIRED',
                          'group_before_join': retired_members})
            write_json(root / (name + '.json'), stage)
        if status != 0:
            return name
    return None


def gated_worker(root, gate_r, ready_w):
    # No source staging, compiler, or fixture before positive authorization.
    me = stat_pid(os.getpid())
    os.write(ready_w, (str(me['pid']) + '\n').encode())
    os.close(ready_w)
    if read_message(gate_r, time.monotonic() + 170) != b'GO':
        raise RuntimeError('GO not received')
    os.close(gate_r)
    record = {'status': 'STAGING'}
    try:
        record['inputs'] = {str(p): verify(p, h) for p, h in INPUTS.items()}
        record['tools'] = {p: verify(p, h) for p, h in TOOLS.items()}
        provider = json.loads((BASE / 'RESULT.json').read_text())['binding']['inputs']
        record['provider_inputs'] = {p: verify(p, h) for p, h in provider.items()}
        source = (BASE / 'f03_perf_entry_candidate.rs').read_text()
        start = source.index('unsafe extern "C" fn perf_entry_counter_alloc_or_release(')
        end = source.index('\n}\n', start) + 3
        wrapper = (BASE / 'candidate-wrapper.rs').read_bytes()
        if source[start:end].encode() != wrapper:
            raise RuntimeError('wrapper extraction mismatch')
        case, home, tmp = (root / x for x in ('case', 'home', 'tmp'))
        for path in (case, home, tmp):
            path.mkdir(mode=0o700)
        for original, dest in ((BASE / 'counter_wrapper_fixture.rs', case / 'fixture.rs'),
                               (BASE / 'candidate-wrapper.rs', case / 'candidate-wrapper.rs')):
            dest.write_bytes(original.read_bytes())
            os.chmod(dest, 0o400)
            verify(dest, INPUTS[original])
        env = dict(ENV, HOME=str(home), TMPDIR=str(tmp))
        record.update({'status': 'STAGED', 'environment': env})
        write_json(root / 'worker.json', record)
        group = os.getpgrp()
        fixed = {group, os.getpid()}  # timeout anchor and gated worker
        failed_stage = run_stages(root, env, group, fixed)
        if failed_stage is not None:
            record['status'] = failed_stage.upper() + '_FAILED'
            write_json(root / 'worker.json', record)
            return 1
        record['status'] = 'PASS_PENDING_GROUP_RETIREMENT'
        write_json(root / 'worker.json', record)
        return 0
    except Exception as error:
        record.update({'status': 'UNKNOWN_OR_FAILED', 'error': repr(error)})
        write_json(root / 'worker.json', record)
        return 1


def allowed_member(m, anchor, worker_pid, root):
    if m['state'] == 'Z':
        return True  # zombies still block retirement
    path = str(Path(m['exe']).resolve())
    if m['pid'] == anchor:
        return path == str(Path(TIMEOUT).resolve())
    if m['pid'] == worker_pid:
        return path == str(Path(PYTHON).resolve())
    if path in (str(Path(RUSTC).resolve()), str((root / 'case/fixture').resolve())):
        return True
    return (Path(path).name in HELPERS and
            (path.startswith('/usr/bin/') or path.startswith('/usr/lib/gcc/')))


def terminate_owned(pid, born, report):
    """Signals only while the direct group anchor remains pinned and verified."""
    check_anchor(pid, born)
    os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        members = census(pid)
        if unreaped(pid) is not None and all(m['pid'] == pid for m in members):
            return members
        time.sleep(0.05)
    check_anchor(pid, born)
    os.killpg(pid, signal.SIGKILL)
    deadline = time.monotonic() + 0.8
    while time.monotonic() < deadline:
        members = census(pid)
        if unreaped(pid) is not None and all(m['pid'] == pid for m in members):
            return members
        time.sleep(0.05)
    report['status'] = 'UNKNOWN_GROUP_RETIREMENT'
    return census(pid)


def owner():
    started = time.monotonic()
    if dict(os.environ) != ENV:
        raise RuntimeError('exact clean environment required')
    if 6 not in os.sched_getaffinity(0):
        raise RuntimeError('CPU6 unavailable')
    os.sched_setaffinity(0, {6})
    for kind, value in LIMITS:
        soft, hard = resource.getrlimit(kind)
        if ((hard != resource.RLIM_INFINITY and hard < value) or
                (soft != resource.RLIM_INFINITY and soft < value)):
            raise RuntimeError('cannot widen existing limit')
        resource.setrlimit(kind, (value, value))
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Verify executables before they can act. Other bindings are rechecked by
    # the gated worker after GO; external admission binds this script itself.
    verify(TIMEOUT, TOOLS[TIMEOUT])
    verify(PYTHON, TOOLS[PYTHON])
    root = Path(tempfile.mkdtemp(prefix='native-cheap-20261017-', dir=str(SCRATCH)))
    os.chmod(root, 0o700)
    report = {'status': 'STARTING', 'root': str(root), 'external_admission_required': True,
              'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'}
    write_json(root / 'owner.json', report)
    gate_r, gate_w = os.pipe()
    ready_r, ready_w = os.pipe()
    command = [TIMEOUT, '--signal=TERM', '--kill-after=4s', '175s', PYTHON, '-B',
               str(Path(__file__).resolve()), '--worker', str(root), str(gate_r), str(ready_w)]
    # timeout is the new session/group leader; both it and its worker remain in
    # the same group. The inherited gate blocks worker before any staged work.
    try:
        proc = subprocess.Popen(command, cwd=str(REPO), env=ENV, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                pass_fds=(gate_r, ready_w), start_new_session=True)
    except BaseException as error:
        for fd in (gate_r, gate_w, ready_r, ready_w):
            os.close(fd)
        report.update({'status': 'UNKNOWN_LAUNCH', 'error': repr(error), 'argv': command})
        write_json(root / 'owner.json', report)
        return 1
    os.close(gate_r)
    os.close(ready_w)
    pid, born, worker_pid = proc.pid, None, None
    report.update({'argv': command, 'anchor_pid': pid})
    try:
        leader = stat_pid(pid)
        born = leader['start']
        check_anchor(pid, born)
        raw = read_message(ready_r, min(started + 170, time.monotonic() + 10))
        worker_pid = int(raw.decode('ascii'))
        worker_stat = stat_pid(worker_pid)
        check_handshake(check_anchor(pid, born), worker_stat, worker_pid)
        if (os.readlink('/proc/%d/exe' % pid) != str(Path(TIMEOUT).resolve()) or
                os.readlink('/proc/%d/exe' % worker_pid) != str(Path(PYTHON).resolve())):
            raise RuntimeError('unexpected handshake executables')
        report.update({'status': 'GROUP_OWNED', 'anchor': leader, 'worker': worker_stat})
        write_json(root / 'owner.json', report)
        # Check again after evidence persistence and immediately before GO.
        check_handshake(check_anchor(pid, born), stat_pid(worker_pid), worker_pid,
                        worker_stat['start'])
        if (os.readlink('/proc/%d/exe' % pid) != str(Path(TIMEOUT).resolve()) or
                os.readlink('/proc/%d/exe' % worker_pid) != str(Path(PYTHON).resolve())):
            raise RuntimeError('handshake executables changed')
        if STOP is not None or time.monotonic() >= started + 175:
            raise RuntimeError('stop before authorization')
        os.write(gate_w, b'GO\n')
        os.close(gate_w)
        gate_w = None
        report['status'] = 'RUNNING'
        write_json(root / 'owner.json', report)
        unknown_since = {}
        reason = None
        while True:
            members = census(pid)
            finished = unreaped(pid)
            now = time.monotonic()
            bad = []
            for m in members:
                key = (m['pid'], m['start'])
                if not allowed_member(m, pid, worker_pid, root):
                    unknown_since.setdefault(key, now)
                    if now - unknown_since[key] > 2:
                        bad.append(m)
            if STOP is not None:
                reason = 'SIGNAL_%s' % STOP
            elif now - started >= 180:
                reason = 'OUTER_DEADLINE'
            elif len(members) + 1 > 8:
                reason = 'PROCESS_COUNT'
            elif sum(m['rss'] for m in members) > 2147483648:
                reason = 'RSS_PLANNING_LIMIT'
            elif bad:
                reason = 'UNEXPECTED_EXECUTABLE'
            elif finished is not None and any(m['pid'] != pid for m in members):
                reason = 'ANCHOR_EXIT_WITH_MEMBERS'
            if reason or (finished is not None and all(m['pid'] == pid for m in members)):
                break
            time.sleep(0.05)
        if reason:
            report.update({'reason': reason, 'before_termination': members})
            members = terminate_owned(pid, born, report)
        check_anchor(pid, born)
        finished = unreaped(pid)
        members = census(pid)
        if finished is None or any(m['pid'] != pid for m in members):
            report['status'] = 'UNKNOWN_GROUP_RETIREMENT'
        else:
            code = proc.wait()
            result_path = root / 'worker.json'
            result = json.loads(result_path.read_text()) if result_path.exists() else {}
            report.update({'anchor_returncode': code, 'worker_result': result,
                           'final_group': members})
            report['status'] = ('PASS_MICROTEST_ONLY' if not reason and code == 0 and
                                result.get('status') == 'PASS_PENDING_GROUP_RETIREMENT'
                                else 'STOPPED_OR_FAILED')
    except BaseException as error:
        report.update({'status': 'UNKNOWN_OWNER_OR_GROUP', 'error': repr(error)})
        if born is not None:
            try:
                terminate_owned(pid, born, report)
            except BaseException as cleanup_error:
                report['cleanup_error'] = repr(cleanup_error)
        # Preserve UNKNOWN; even a successful signal is not a retirement proof.
    finally:
        if gate_w is not None:
            os.close(gate_w)
        os.close(ready_r)
        write_json(root / 'owner.json', report)
    print(json.dumps({'root': str(root), 'status': report['status']}))
    return 0 if report['status'] == 'PASS_MICROTEST_ONLY' else 1


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--worker':
        raise SystemExit(gated_worker(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
    if len(sys.argv) != 1:
        raise SystemExit('invalid arguments')
    raise SystemExit(owner())
