#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted nine-command F01 HOST diagnostic, exact current81 object reused.
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
RECIPE = ROOT / 'EXACT-NINE-HOST-F01-TU-REUSE.NOT-GRANTED.json'
RECIPE_SHA = '780064ea0f082501469ac58a0e7a7ce28e982da7f57aa714f5fba8b80850a4e0'
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
OUTPUT = ROOT / 'output-1'
CAPTURE = ROOT / 'actual-nine-HOST-1'
RESULT = ROOT / 'ACTUAL-NINE-HOST-RESULT.json'

def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def identity(path):
    before = path.stat()
    bound = pin(path)
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise RuntimeError('input identity changed during source read: ' + str(path))
    return dict(binding=bound, metadata={key: getattr(after, key) for key in fields})

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
    begin = time.monotonic()
    started = False
    try:
        if any(path.exists() for path in (OUTPUT, CAPTURE, RESULT)):
            raise RuntimeError('existing attempt retained; no replay')
        if pin(RECIPE)['sha256'] != RECIPE_SHA:
            raise RuntimeError('root-granted recipe changed')
        recipe = json.loads(RECIPE.read_text())
        reuse = json.loads((ROOT / 'EXACT81-RUST-OBJECT-REUSE.json').read_text())
        frozen81 = [dict(path=row['F01_private_path'], sha256=row['sha256'], bytes=Path(row['F01_private_path']).stat().st_size) for row in reuse['exact_Rust_matches']]
        bindings = recipe['source_bindings'] + recipe['header_bindings'] + list(recipe['tools'].values()) + frozen81 + [recipe['retained_Rust_object']]
        identities = {}
        for row in bindings:
            bound = identity(Path(row['path']))
            if bound['binding'] != row:
                raise RuntimeError('bound input differs: ' + row['path'])
            identities[row['path']] = bound
        if os.getuid() != 1000 or os.geteuid() != 1000 or 6 not in os.sched_getaffinity(0):
            raise RuntimeError('ordinary UID1000/available CPU6 required')
        raw = HELPER.read_bytes()
        if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
            raise RuntimeError('h990 helper binding changed')
        functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
        assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
        nodes = [node for node in ast.parse(raw).body if isinstance(node, (ast.Import, ast.ImportFrom)) or isinstance(node, ast.FunctionDef) and node.name in functions or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in assignments for target in node.targets)]
        namespace = {'__file__': str(HELPER)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HELPER), 'exec'), namespace)
        used = set()
        for name in functions:
            used.update(dependencies(namespace[name].__code__))
        if used - set(namespace) - set(vars(builtins)):
            raise RuntimeError('h990 extraction dependency missing')
        mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
        host = os.statvfs('/home/holden')
        scratch = os.statvfs('/home/holden/mckernel-work/scratch')
        if mem < 2 << 30 or host.f_bavail * host.f_frsize < (16 << 30) + (64 << 20) or scratch.f_bavail * scratch.f_frsize < 12 << 30:
            raise RuntimeError('ordinary resource headroom floor')
        OUTPUT.mkdir(mode=0o700)
        CAPTURE.mkdir(mode=0o700)
        os.chdir(OUTPUT)
        os.sched_setaffinity(0, {6})
        os.environ['RUST_MIN_STACK'] = '2097152'
        os.environ['LC_ALL'] = 'C'
        os.environ['OMP_NUM_THREADS'] = os.environ['RAYON_NUM_THREADS'] = '1'
        for number in namespace['STOP_SIGNALS']:
            signal.signal(number, namespace['stop'])
        for key, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)):
            resource.setrlimit(key, (value, value))
        write(CAPTURE / 'profile.json', dict(scope=SCOPE, CPU=6, jobs=1, AS=2 << 30, shared_CPU=60, wall=90, retirement=6, FSIZE=32 << 20, NOFILE=256, stack=2 << 20, core=0, root_authority='Parent explicit F01source4 nine HOST GCC9 diagnostic grant; no Rust compile/SDK/default/native claim', recipe=pin(RECIPE), helper=pin(HELPER), headroom=dict(MemAvailable=mem, host_free=host.f_bavail*host.f_frsize, scratch_free=scratch.f_bavail*scratch.f_frsize)))
        write(CAPTURE / 'input-identities-before.json', identities)
        signal.setitimer(signal.ITIMER_REAL, max(0.1, 96 - (time.monotonic() - begin)))
        started = True
        symbols = {}
        for command in recipe['commands']:
            remaining_wall = 90 - (time.monotonic() - begin)
            remaining_cpu = int(60 - namespace['cpu_used']())
            if remaining_wall <= 0 or remaining_cpu < 1:
                raise RuntimeError('shared whole budget exhausted')
            capture = CAPTURE / command['name']
            capture.mkdir(mode=0o700)
            write(capture / 'command.json', command)
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU, (remaining_cpu, remaining_cpu))
            joined = namespace['owned_capture'](command, capture, remaining_wall, limits)
            write(capture / 'whole-join.json', joined)
            records.append(dict(command=command, join=joined))
            if joined['returncode'] != 0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error'] or joined['timed_out']:
                raise RuntimeError('first unexpected command result; preserve prefix')
            if command['name'] in ('03-selected-mem-symbols', '06-partial-provider-symbols', '08-fallback-mem-symbols'):
                rows = [line.split() for line in (capture / 'stdout').read_text().splitlines() if line.split()]
                if any(row[-1] == 'mem_get_this_cpu_local_var_bridge' for row in rows):
                    raise RuntimeError('dead callback remains')
                if command['name'] == '03-selected-mem-symbols':
                    text = [row for row in rows if len(row)>1 and row[-2] in ('t', 'T', 'w', 'W')]
                    if text:
                        raise RuntimeError('unexpected selected C executable definition: '+repr(text))
                if command['name'] == '06-partial-provider-symbols':
                    for name in ('kmalloc_init', 'virtual_allocator_init', 'phys_to_page_insert_hash'):
                        found = [row for row in rows if row[-1] == name]
                        if len(found)!=1 or found[0][-2]!='T':
                            raise RuntimeError('Rust target provider mismatch: '+name+repr(found))
                if command['name'] == '08-fallback-mem-symbols':
                    found=[row for row in rows if row[-1]=='kmalloc_init']
                    if len(found)!=1 or found[0][-2]!='T':
                        raise RuntimeError('fallback kmalloc_init not retained')
                symbols[command['name']] = dict(all_rows=rows, unresolved=sorted({row[-1] for row in rows if len(row)>1 and row[-2]=='U'}))
        after = {path: identity(Path(path)) for path in identities}
        write(CAPTURE / 'input-identities-after.json', after)
        if after != identities:
            raise RuntimeError('input identity changed during sequence')
        if namespace['cpu_used']() > 60:
            raise RuntimeError('shared CPU budget exceeded')
        objects = {name: namespace['hashed'](OUTPUT/name,32<<20) for name in ('mem.c.o','mem-rust-partial.o','mem.fallback.c.o','mem.c.o.d','mem.fallback.c.o.d','mem.selected.i')}
        result = dict(scope=SCOPE, status='PASS_NINE_HOST_F01_CURRENT81_OBJECT_REUSE', records=records, symbols=symbols, objects=objects, reused_Rust_object=recipe['retained_Rust_object'], no_Rust_compile=True, seconds=time.monotonic()-begin, CPU_seconds=namespace['cpu_used'](), CPU6_released=True, canonical_mutations=0, native=False, pinned_SDK=False, production_default_image=False, header_dependency_reconciliation='Actual dependency files retained; independent join to current-header bindings remains separate', recipe=pin(RECIPE))
        write(RESULT, result)
        print(json.dumps(dict(status=result['status'], result=pin(RESULT), seconds=result['seconds'], CPU_seconds=result['CPU_seconds'])))
        return 0
    except BaseException as error:
        if not RESULT.exists():
            write(RESULT, dict(scope=SCOPE,status='FAIL_STOP_PRESERVE_PREFIX_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,seconds=time.monotonic()-begin,canonical_mutations=0))
        raise
    finally:
        if started:
            signal.setitimer(signal.ITIMER_REAL,0)

if __name__=='__main__':
    sys.exit(main())
