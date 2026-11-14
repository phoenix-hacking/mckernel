#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Four fixed ordinary commands after exact root grant; no guest, root or Docker.
Reuses the reviewed h990 owned-capture/retirement implementation unchanged.
"""

import ast
import builtins
import dis
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time


ROOT = Path(__file__).resolve().parent
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/'
              'phase5-m03-handshake-runtime-checkpoint-20261020-1/'
              'sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
RECIPE = ROOT / 'EXACT-DEBUG-PARITY.NOT-GRANTED.json'
GRANT = ROOT / 'ROOT-GRANT.DEBUG-PARITY.json'
OUTPUT = ROOT / 'output-debug-parity-first-1'
CAPTURE = ROOT / 'actual-debug-parity-first-1'
FAILURE = ROOT / 'DEBUG-PARITY-FIRST-FAILURE.json'
SUCCESS = ROOT / 'DEBUG-PARITY-FIRST-WHOLE-JOIN.json'
FUNCTIONS = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start',
             'terminal_unreaped', 'wait_terminal', 'owned_capture'}
ASSIGNMENTS = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def globals_used(code):
    used = {item.argval for item in dis.get_instructions(code) if item.opname == 'LOAD_GLOBAL'}
    for value in code.co_consts:
        if isinstance(value, type(code)):
            used.update(globals_used(value))
    return used


def main():
    records = []
    started = False
    try:
        for path in (OUTPUT, CAPTURE, FAILURE, SUCCESS):
            if path.exists():
                raise RuntimeError('preserve existing attempt; no replay: ' + str(path))
        grant = json.loads(GRANT.read_text())
        required = {'scope': SCOPE, 'CPU': 0, 'ordinary_jobs': 1,
                    'aggregate_AS_bytes': 512 << 20,
                    'physical_clearance_accepted': True,
                    'recipe_sha256': pin(RECIPE)['sha256'],
                    'runner_sha256': pin(Path(__file__))['sha256']}
        if any(grant.get(key) != value for key, value in required.items()):
            raise RuntimeError('exact current root grant required')
        clearance = grant['physical_clearance']
        if pin(Path(clearance['path'])) != clearance:
            raise RuntimeError('root accepted physical clearance binding changed')
        recipe = json.loads(RECIPE.read_text())
        for row in recipe['inputs'] + list(recipe['tools'].values()):
            if pin(Path(row['path'])) != row:
                raise RuntimeError('frozen source/tool binding changed: ' + row['path'])
        if os.getuid() != 1000 or os.geteuid() != 1000 or 0 not in os.sched_getaffinity(0):
            raise RuntimeError('ordinary UID1000 / available CPU0 required')
        if sys.version_info[:2] != (3, 9):
            raise RuntimeError('reviewed Python3.9 required')
        raw = HELPER.read_bytes()
        if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
            raise RuntimeError('reviewed h990 capture helper changed')
        nodes = [node for node in ast.parse(raw).body
                 if isinstance(node, (ast.Import, ast.ImportFrom))
                 or isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS
                 or isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id in ASSIGNMENTS
                     for target in node.targets)]
        namespace = {'__file__': str(HELPER)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HELPER), 'exec'), namespace)
        dependencies = set()
        for name in FUNCTIONS:
            dependencies.update(globals_used(namespace[name].__code__))
        missing = dependencies - set(namespace) - set(vars(builtins))
        if missing:
            raise RuntimeError('h990 extraction dependencies missing: ' + repr(sorted(missing)))
        mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                       if line.startswith('MemAvailable:'))) * 1024
        host = os.statvfs('/home/holden')
        scratch = os.statvfs('/home/holden/mckernel-work/scratch')
        headroom = {'MemAvailable': mem, 'HOST_free': host.f_bavail * host.f_frsize,
                    'scratch_free': scratch.f_bavail * scratch.f_frsize}
        if (mem < (512 << 20) or headroom['HOST_free'] < (16 << 30) + (64 << 20)
                or headroom['scratch_free'] < (12 << 30)):
            raise RuntimeError('ordinary resource floor not satisfied: ' + repr(headroom))
        OUTPUT.mkdir(mode=0o700)
        CAPTURE.mkdir(mode=0o700)
        os.chdir(OUTPUT)
        os.sched_setaffinity(0, {0})
        os.environ['RUST_MIN_STACK'] = '2097152'
        os.environ['LC_ALL'] = 'C'
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['RAYON_NUM_THREADS'] = '1'
        for number in namespace['STOP_SIGNALS']:
            signal.signal(number, namespace['stop'])
        for key, value in ((resource.RLIMIT_AS, 64 << 20), (resource.RLIMIT_CPU, 40),
                           (resource.RLIMIT_FSIZE, 16 << 20), (resource.RLIMIT_NOFILE, 128),
                           (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)):
            # Preserve a child hard AS ceiling of448MiB, while the parent itself
            # is limited to64MiB. Only one child is admitted at any time.
            hard = 448 << 20 if key == resource.RLIMIT_AS else value
            resource.setrlimit(key, (value, hard))
        profile = dict(scope=SCOPE, CPU=0, ordinary_jobs=1, aggregate_AS_bytes=512 << 20,
                       parent_AS_bytes=64 << 20, child_AS_bytes=448 << 20,
                       CPU_seconds=40, whole_wall_seconds=60, retirement_seconds=6,
                       FSIZE_bytes=16 << 20, NOFILE=128, STACK_bytes=2 << 20,
                       core=0, CGU=1, grant=pin(GRANT), recipe=pin(RECIPE),
                       runner=pin(Path(__file__)), h990=pin(HELPER), headroom=headroom,
                       helper_missing_globals=[], cwd=str(OUTPUT))
        write(CAPTURE / 'actual-profile.json', profile)
        begin = time.monotonic()
        signal.setitimer(signal.ITIMER_REAL, 66)
        started = True
        for command in recipe['commands']:
            remaining = 60 - (time.monotonic() - begin)
            if remaining <= 0 or namespace['cpu_used']() >= 40:
                raise RuntimeError('whole ordinary time/CPU envelope exhausted')
            capture = CAPTURE / command['name']
            capture.mkdir(mode=0o700)
            write(capture / 'command.json', command)

            def limits():
                os.sched_setaffinity(0, {0})
                resource.setrlimit(resource.RLIMIT_AS, (448 << 20, 448 << 20))

            joined = namespace['owned_capture'](command, capture, min(20, remaining), limits)
            write(capture / 'whole-join.json', joined)
            records.append({'command': command, 'join': joined})
            if (joined['returncode'] != 0 or not joined['direct_child_joined']
                    or not joined['group_absent'] or not joined['closed_streams']
                    or joined['error'] or joined['retirement_error'] or joined['timed_out']):
                raise RuntimeError('first unexpected command result; retain failure, no retry')
        stdout = (CAPTURE / recipe['commands'][-1]['name'] / 'stdout').read_text()
        expected = 'PASS debug_log actual-C/Rust parity: 14 cases, output and lock order\n'
        if not stdout.endswith(expected) or stdout.count('\nREFERENCE_OUTPUT_BEGIN\n') != 14:
            raise RuntimeError('missing exact parity summary or original output records')
        for row in recipe['inputs']:
            if pin(Path(row['path'])) != row:
                raise RuntimeError('fixture source changed during command sequence')
        result = dict(scope=SCOPE, status='PASS_ACTUAL_C_RUST_DEBUG_PARITY_14_MOCK_LAYOUT',
                      actual_commands=4, actual_comparisons=14, records=records,
                      CPU0_released=True, canonical_mutations=0, production_ABI=False,
                      fullcrate_default_native_credit=False, recipe=pin(RECIPE),
                      seconds=time.monotonic() - begin, CPU_seconds=namespace['cpu_used']())
        write(SUCCESS, result)
        print(json.dumps({'status': result['status'], 'receipt': pin(SUCCESS)}))
        return 0
    except BaseException as error:
        write(FAILURE, dict(scope=SCOPE, status='FAIL_STOP_PRESERVE_NO_RETRY',
                            error=type(error).__name__ + ': ' + str(error), records=records,
                            canonical_mutations=0, started=started))
        raise
    finally:
        if started:
            signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    sys.exit(main())
