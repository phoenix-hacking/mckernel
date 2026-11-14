#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Exact root-granted six-command ordinary CPU0 fullcrate/real-ABI check.
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
RECIPE = ROOT / 'EXACT-CORRECTED-FULLCRATE-REAL-ABI.NOT-GRANTED.json'
RECIPE_SHA = 'b6b8c62cd9b6268168ac3aa44bd6cf238867055a69f1848632be683dcdae6d82'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/'
              'phase5-m03-handshake-runtime-checkpoint-20261020-1/'
              'sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
OUTPUT = ROOT / 'output-real-abi-first-1'
CAPTURE = ROOT / 'actual-real-abi-first-1'
RESULT = ROOT / 'ACTUAL-REAL-ABI-FIRST-RESULT.json'


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


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
        sources = json.loads(Path(recipe['input_bindings']['path']).read_text())
        bindings = [recipe['input_bindings'], *recipe['fixture_bindings'],
                    *recipe['current_header_bindings'].values(), *recipe['tools'].values()]
        for row in sources['sources']:
            bindings.extend([row['canonical'], row['private']])
        bindings.extend([sources['canonical_C'], sources['candidate_C'],
                         sources['corrected_body'], sources['bridge_semantics']])
        for row in bindings:
            if pin(Path(row['path'])) != row:
                raise RuntimeError('input/tool/header binding changed: ' + row['path'])
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
        if (mem < 2 << 30 or host.f_bavail * host.f_frsize < (16 << 30) + (64 << 20)
                or scratch.f_bavail * scratch.f_frsize < 12 << 30):
            raise RuntimeError('ordinary resource headroom floor')
        OUTPUT.mkdir(mode=0o700)
        CAPTURE.mkdir(mode=0o700)
        os.chdir(OUTPUT)
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
              authority='Parent /root explicit execution task for b6b8c62c, physical dda45e/current f37ff2 accepted; CPU0 only; no mock replay.'))
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
        if namespace['cpu_used']() > 60:
            raise RuntimeError('shared whole CPU budget exceeded')
        cbytes = (OUTPUT / 'C.abi').read_bytes()
        rustbytes = (OUTPUT / 'Rust.abi').read_bytes()
        labels = json.loads((ROOT / 'fixture/ABI-ROW-LABELS.json').read_text())
        if cbytes != rustbytes or len(cbytes) != 8 * len(labels):
            raise RuntimeError('actual ABI geometry unequal or incomplete')
        rows = {name: int.from_bytes(cbytes[8*i:8*i+8], 'little')
                for i, name in enumerate(labels)}
        result = dict(scope=SCOPE, status='PASS_CURRENT_FULLCRATE_METADATA_ACTUAL_ABI_29',
                      records=records, actual_ABI=rows, seconds=time.monotonic()-begin,
                      CPU_seconds=namespace['cpu_used'](), CPU0_released=True,
                      canonical_mutations=0, fullcrate_object=False, native=False,
                      recipe=pin(RECIPE), corrected_body=sources['corrected_body'])
        write(RESULT, result)
        print(json.dumps(dict(status=result['status'], result=pin(RESULT), actual_ABI=rows)))
        return 0
    except BaseException as error:
        write(RESULT, dict(scope=SCOPE, status='FAIL_STOP_PRESERVE_PREFIX_NO_RETRY',
                          error=type(error).__name__+': '+str(error), records=records,
                          seconds=time.monotonic()-begin, canonical_mutations=0))
        raise
    finally:
        if started:
            signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    sys.exit(main())
