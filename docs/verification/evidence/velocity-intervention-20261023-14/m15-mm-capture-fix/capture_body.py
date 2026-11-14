"""Source-bound ordinary HOST body capture; requires a fresh external root grant.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This HOST fixture supplies no production SDK/objtool/module/native acceptance.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import time

D = Path(__file__).resolve().parent
PROFILE_SHA = '228971c3de41a8f021706c84161b34297bb4f902d25a00dcd51e70f767f50de3'
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def pinned(ref):
    path = Path(ref['path'])
    raw = path.read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'source pin '+str(path))
    return raw


def inventory(root):
    total = count = 0
    if not root.exists():
        return 0
    for path in root.rglob('*'):
        count += 1
        need(count <= 1024, 'bounded private output inventory')
        row = path.lstat()
        need(stat.S_ISREG(row.st_mode) or stat.S_ISDIR(row.st_mode), 'private output special file')
        if stat.S_ISREG(row.st_mode):
            total += row.st_size
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-after-campaign-grant', action='store_true', required=True)
    parser.add_argument('--cpu', type=int, choices=(0, 6), required=True)
    args = parser.parse_args()
    started = time.monotonic()
    raw = (D/'CAPTURE-PROFILE.json').read_bytes()
    need(hashlib.sha256(raw).hexdigest() == PROFILE_SHA, 'frozen capture profile')
    profile = json.loads(raw)
    need(Path.cwd() == D, 'exact successor capture cwd')
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {args.cpu}, 'exact ordinary single CPU')
    for kind, limits in ((resource.RLIMIT_AS, (2 << 30, 2 << 30)),
                         (resource.RLIMIT_CPU, (60, 60)),
                         (resource.RLIMIT_FSIZE, (32 << 20, 32 << 20)),
                         (resource.RLIMIT_NOFILE, (256, 256)),
                         (resource.RLIMIT_CORE, (0, 0)),
                         (resource.RLIMIT_STACK, (2 << 20, 2 << 20))):
        need(resource.getrlimit(kind) == limits, 'exact inherited POSIX resource limit')
    need(os.environ.get('RUST_MIN_STACK') == '2097152', 'explicit inherited Rust stack environment')
    python = profile['python_interpreter']
    need(str(Path(sys.executable).resolve()) == python['resolved'], 'exact Python executable')
    pinned(dict(path=python['resolved'], bytes=python['bytes'], sha256=python['sha256']))
    for ref in profile['source_inputs'] + profile['capture_transport_tools']:
        pinned(ref)
    helper_raw = pinned(profile['owned_capture_helper'])
    need(hashlib.sha256(helper_raw).hexdigest() == HELPER_SHA, 'h990 ownership helper')
    # Import only these unchanged helper definitions and their required constants.
    # In particular, its unrelated historical main/profile/Docker transport is not run.
    tree = ast.parse(helper_raw, profile['owned_capture_helper']['path'])
    functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members',
                 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
    constants = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets):
            nodes.append(node)
    helper = {'__name__': 'source_bound_h990_capture'}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), profile['owned_capture_helper']['path'], 'exec'), helper)
    need(functions <= set(helper), 'complete unchanged h990 ownership dependencies')
    output = Path(profile['fresh_capture_root'])
    body = Path(profile['fresh_body_output'])
    need(not os.path.lexists(str(output)) and not os.path.lexists(str(body)), 'fresh attempt output absence')
    free = os.statvfs(D)
    need(free.f_bavail*free.f_frsize >= profile['required_free_bytes'], '64MiB aggregate reservation plus explicit reserve')
    output.mkdir(mode=0o700)

    def accounting():
        total = inventory(output) + inventory(body)
        need(total <= 64 << 20, '64MiB aggregate output acceptance cap exceeded')
        return total

    original_wait = helper['wait_terminal']

    def monitored_wait(process, seconds):
        # Keep h990 ownership and retirement unchanged. Apply the ordinary output
        # cap while waiting; retirement must remain possible after a cap failure.
        if helper['stopping']:
            return original_wait(process, seconds)
        deadline = time.monotonic() + seconds
        while not helper['terminal_unreaped'](process):
            accounting()
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.01, max(0, deadline-time.monotonic())))
        accounting()
        return True

    helper['wait_terminal'] = monitored_wait
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(number, helper['stop'])
    command = dict(role='M15_HOST_body_fixture_only', argv=profile['body_argv'])
    helper['write'](output/'command.json', dict(command=command, cpu=args.cpu, profile_sha256=PROFILE_SHA,
        root_execution_grant_required_externally=True, inherited_RUST_MIN_STACK=os.environ['RUST_MIN_STACK']))
    remaining = 90-(time.monotonic()-started)
    need(remaining > 0, 'whole90s work budget remains before launch')
    signal.setitimer(signal.ITIMER_REAL, remaining)
    record = None
    failure = None
    try:
        record = helper['owned_capture'](command, output, max(0.1, 90-(time.monotonic()-started)), lambda: None)
        need(record['returncode'] == 0 and record['direct_child_joined'] and record['group_absent'] and
             not record['unexpected_group_members'] and not record['timed_out'] and
             not record['error'] and not record['retirement_error'], 'first body capture failure; no retry')
        need(record['captures']['stderr']['size'] == 0, 'body outer stderr must be empty')
        need(helper['cpu_used']() <= 60, '60CPU whole-job measured acceptance bound')
        accounting()
        result = json.loads((body/'RESULT.json').read_text())
        need(result['status'] == 'PASS_PRIVATE_BODY_AND_MOCKED_WARNING_FIXTURE' and result['production_module_or_native_acceptance'] is False, 'actual HOST body fixture result')
    except BaseException as error:
        failure = type(error).__name__+': '+str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    aggregate = inventory(output) + inventory(body)
    result = dict(status='PASS_HOST_BODY_FIXTURE_ONLY' if failure is None else 'FAIL_STOPPED_PRESERVE_ALL',
                  error=failure, profile_sha256=PROFILE_SHA, record=record,
                  total_CPU_seconds=helper['cpu_used'](), elapsed_seconds=time.monotonic()-started,
                  aggregate_output_bytes_before_final_receipt=aggregate,
                  aggregate_output_limit_bytes=64 << 20, production_module_or_native_acceptance=False,
                  output_cap_kind='aggregate acceptance/monitor threshold; not an OS aggregate quota; RLIMIT_FSIZE32MiB is per file')
    if aggregate+len(json.dumps(result, sort_keys=True).encode())+1 > 64 << 20:
        failure = 'final receipt would exceed aggregate output acceptance cap'
        result.update(status='FAIL_STOPPED_PRESERVE_ALL', error=failure)
    helper['write'](output/'whole-result.json', result)
    need(inventory(output)+inventory(body) <= 64 << 20, 'final receipt inclusive aggregate cap')
    print(json.dumps({k: result[k] for k in ('status', 'error', 'elapsed_seconds', 'total_CPU_seconds')}))
    return 0 if failure is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
