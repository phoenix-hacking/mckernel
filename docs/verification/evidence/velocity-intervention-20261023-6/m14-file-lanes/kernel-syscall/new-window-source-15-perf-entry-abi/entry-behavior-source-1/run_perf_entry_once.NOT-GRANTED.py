#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source15 genuine perf entry/helper13 controlled functional fixture frozen source-only. Requires independent source review and fresh root ordinary CPU0 grant before execution.
"""
import ast
import datetime
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
BASE = ROOT.parent
RECIPE = ROOT / 'EXACT-PERF-ENTRY-COMMANDS.NOT-GRANTED.json'
RECIPE_SHA = 'a9ee7de7cda8297bb0630bb67a7ac2a4f17e1ae90d631d3b0b1d1003af531cd6'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/'
              'phase5-m03-handshake-runtime-checkpoint-20261020-1/'
              'sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
OUTPUT = ROOT / 'output-1'
CAPTURE = ROOT / 'actual-parity-capture-first-1'
RESULT = ROOT / 'ACTUAL-PERF-ENTRY-FIRST-RESULT.json'


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def identity(path):
    value = path.stat()
    return dict(**pin(path), device=value.st_dev, inode=value.st_ino,
                uid=value.st_uid, gid=value.st_gid, mode=oct(value.st_mode & 0o7777),
                nlink=value.st_nlink, mtime_ns=value.st_mtime_ns, ctime_ns=value.st_ctime_ns)


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def dependencies(code):
    used = {item.argval for item in dis.get_instructions(code) if item.opname == 'LOAD_GLOBAL'}
    for constant in code.co_consts:
        if isinstance(constant, type(code)):
            used.update(dependencies(constant))
    return used


def main():
    records = []
    started = False
    begin = time.monotonic()
    try:
        if any(path.exists() for path in (OUTPUT, CAPTURE, RESULT)):
            raise RuntimeError('existing attempt retained; no replay')
        if pin(RECIPE)['sha256'] != RECIPE_SHA:
            raise RuntimeError('exact root-granted recipe changed')
        recipe = json.loads(RECIPE.read_text())
        bindings = recipe['inputs'] + recipe['sources'] + recipe['canonical_origins'] + recipe['header_bindings'] + list(recipe['tools'].values()) + list(recipe['fixture_tools'].values())
        for row in bindings:
            if pin(Path(row['path'])) != row:
                raise RuntimeError('input/tool/header binding changed: ' + row['path'])
        for row in recipe.get('retained_identity', []):
            if identity(Path(row['path'])) != row:
                raise RuntimeError('retained prefix identity changed: ' + row['path'])
        if os.getuid() != 1000 or os.geteuid() != 1000 or 0 not in os.sched_getaffinity(0):
            raise RuntimeError('ordinary UID1000/available CPU0 required')
        raw = HELPER.read_bytes()
        if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
            raise RuntimeError('h990 helper binding changed')
        functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start',
                     'terminal_unreaped', 'wait_terminal', 'owned_capture'}
        assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
        nodes = [node for node in ast.parse(raw).body
                 if isinstance(node, (ast.Import, ast.ImportFrom))
                 or isinstance(node, ast.FunctionDef) and node.name in functions
                 or isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id in assignments
                     for target in node.targets)]
        namespace = {'__file__': str(HELPER)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HELPER), 'exec'), namespace)
        used = set()
        for name in functions:
            used.update(dependencies(namespace[name].__code__))
        if used - set(namespace) - set(vars(builtins)):
            raise RuntimeError('h990 extraction dependency missing')
        mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                       if line.startswith('MemAvailable:'))) * 1024
        host = os.statvfs('/home/holden')
        scratch = os.statvfs('/home/holden/mckernel-work/scratch')
        if (mem < 25501368320 or host.f_bavail * host.f_frsize < (16 << 30) + (64 << 20)
                or scratch.f_bavail * scratch.f_frsize < 12 << 30):
            raise RuntimeError('ordinary resource headroom floor')
        OUTPUT.mkdir(mode=0o700)
        CAPTURE.mkdir(mode=0o700)
        os.chdir(Path('/home/holden/mckernel'))
        os.sched_setaffinity(0, {0})
        os.environ['RUST_MIN_STACK'] = '2097152'
        os.environ['LC_ALL'] = 'C'
        os.environ['OMP_NUM_THREADS'] = os.environ['RAYON_NUM_THREADS'] = '1'
        for number in namespace['STOP_SIGNALS']:
            signal.signal(number, namespace['stop'])
        for key, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60),
                           (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
                           (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)):
            resource.setrlimit(key, (value, value))
        write(CAPTURE / 'profile.json', dict(scope=SCOPE, CPU=0, ordinary_jobs=1,
              AS_bytes=2 << 30, whole_CPU_seconds=60, whole_wall_seconds=90,
              retirement_seconds=6, recipe=pin(RECIPE), helper=pin(HELPER),
              authority='Source-only until independent source review and exact root CPU0 grant. Genuine perf entry/helper ABI and controlled-provider behavior only; no real perf/native/default acceptance.'))
        signal.setitimer(signal.ITIMER_REAL, max(0.1, 96 - (time.monotonic() - begin)))
        started = True
        for command in recipe['commands']:
            wall_remaining = 90 - (time.monotonic() - begin)
            cpu_remaining = int(60 - namespace['cpu_used']())
            if wall_remaining <= 0 or cpu_remaining < 1:
                raise RuntimeError('shared whole wall/CPU budget exhausted')
            capture = CAPTURE / command['name']
            capture.mkdir(mode=0o700)
            write(capture / 'command.json', command)

            def limits():
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_remaining, cpu_remaining))

            write(capture / 'enqueue-observation.json', dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic_seconds=time.monotonic(), argv=command['argv'], argc=len(command['argv']), scope=SCOPE))
            joined = namespace['owned_capture'](command, capture, wall_remaining, limits)
            write(capture / 'whole-join.json', joined)
            records.append(dict(command=command, join=joined))
            if (joined['returncode'] != 0 or not joined['direct_child_joined']
                    or not joined['group_absent'] or not joined['closed_streams']
                    or joined['error'] or joined['retirement_error'] or joined['timed_out']):
                raise RuntimeError('first unexpected result; STOP preserve prefix, no retry')
        for row in bindings:
            if pin(Path(row['path'])) != row:
                raise RuntimeError('bound input changed during sequence: ' + row['path'])
        for row in recipe.get('retained_identity', []):
            if identity(Path(row['path'])) != row:
                raise RuntimeError('retained prefix identity changed after suffix: ' + row['path'])
        if namespace['cpu_used']() > 60:
            raise RuntimeError('shared whole CPU budget exceeded')
        actual_stdout = (CAPTURE / recipe['commands'][2]['name'] / 'stdout').read_text()
        if actual_stdout != recipe['expected_stdout']:
            raise RuntimeError('actual perf entry3600/ABI56 fixture stdout differs')
        result = dict(scope=SCOPE, status='PASS_ACTUAL_PERF_ENTRY3600_ABI56_CONTROLLED_ONLY',
                      records=records, seconds=time.monotonic()-begin,
                      CPU_seconds=namespace['cpu_used'](), CPU0_released=True,
                      fresh_batch_max_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                      canonical_mutations=0, native=False, production_default=False,
                      recipe=pin(RECIPE), cases=3600, ABI_words=56, scenarios=18, controlled_providers=13,
                      fullcrate_compilations=0, real_perf_lifecycle=False,
                      actual_stdout=actual_stdout)
        write(RESULT, result)
        print(json.dumps(dict(status=result['status'], result=pin(RESULT))))
        return 0
    except BaseException as error:
        write(RESULT, dict(scope=SCOPE, status='FAIL_STOP_PRESERVE_PREFIX_NO_RETRY',
                          error=type(error).__name__+': '+str(error), records=records,
                          seconds=time.monotonic()-begin, canonical_mutations=0,
                          fresh_batch_max_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                          CPU_seconds=namespace['cpu_used']() if 'namespace' in locals() and 'cpu_used' in namespace else None))
        raise
    finally:
        if started:
            signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    sys.exit(main())
