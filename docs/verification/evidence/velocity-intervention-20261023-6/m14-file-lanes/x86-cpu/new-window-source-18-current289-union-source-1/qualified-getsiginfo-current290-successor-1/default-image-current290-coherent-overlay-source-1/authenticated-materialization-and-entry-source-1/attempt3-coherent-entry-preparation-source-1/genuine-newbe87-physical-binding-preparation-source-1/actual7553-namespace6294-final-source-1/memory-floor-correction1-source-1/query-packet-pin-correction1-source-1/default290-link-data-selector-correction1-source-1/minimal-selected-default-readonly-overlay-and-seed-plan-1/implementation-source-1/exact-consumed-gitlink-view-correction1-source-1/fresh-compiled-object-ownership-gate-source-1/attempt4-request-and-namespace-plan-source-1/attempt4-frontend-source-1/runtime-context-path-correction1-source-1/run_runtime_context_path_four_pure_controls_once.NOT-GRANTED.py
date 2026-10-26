#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast
import hashlib
import json
import math
import os
import resource
import signal
import time

HERE = Path(__file__).resolve().parent
RECIPE = {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/runtime-context-path-correction1-source-1/EXACT-RUNTIME-CONTEXT-PATH-FOUR-PURE-CONTROLS.NOT-EXECUTED.json', 'sha256': '044071e29f37c509706045d6670035d812dc410528faf45fa35a773cee146b96', 'bytes': 28998}
def ref(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
def need(condition, message):
    if not condition:
        raise RuntimeError(message)
def auth(row):
    need(ref(row['path']) == row, 'exact source binding differs')
    return Path(row['path'])
recipe = json.loads(auth(RECIPE).read_text())
grant_path = HERE / 'ROOT-ORDINARY-RUNTIME-CONTEXT-PATH-FOUR-PURE-CONTROLS-GRANT.json'
grant = json.loads(grant_path.read_text())
need(grant.get('authorized_by') == '/root' and grant.get('maximum_invocations') == 1 and grant.get('recipe') == RECIPE and grant.get('CPU0_exclusively_released') is True and grant.get('no_live_query_owner_or_build') is True, 'exact ordinary CPU0 grant required')
inputs = [RECIPE, recipe['fixture'], recipe['h990'], *recipe['inputs']]
for row in inputs:
    auth(row)
need(os.getuid() == os.geteuid() == 1000 and os.environ.get('MCKERNEL_OS_MEMORY_GIB') == '22.0485', 'ordinary UID/environment')
host = os.statvfs('/home/holden')
scratch = os.statvfs('/home/holden/mckernel-work/scratch')
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
need(host.f_bavail * host.f_frsize >= (16 << 30) + (32 << 20) and scratch.f_bavail * scratch.f_frsize >= 14091616256 and mem >= 6 << 30, 'ordinary resource floors')
source = auth(recipe['h990'])
functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
nodes = [node for node in ast.parse(source.read_text(), str(source)).body if isinstance(node, (ast.Import, ast.ImportFrom)) or isinstance(node, ast.FunctionDef) and node.name in functions or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in assignments for target in node.targets)]
namespace = {'__file__': str(source)}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGALRM]:
    signal.signal(sig, namespace['stop'])
capture = Path(recipe['capture_root'])
need(not os.path.lexists(capture), 'capture must remain fresh; consumed test cannot replay')
capture.mkdir(mode=0o700)
namespace['write'](capture / 'STARTED.json', dict(scope=__doc__, recipe=RECIPE, authority=ref(grant_path), inputs=inputs, profile=recipe['profile']))
start = time.monotonic()
cpu = namespace['cpu_used']()
def limits():
    os.sched_setaffinity(0, {0})
    for key, value in [(resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_STACK, 2 << 20), (resource.RLIMIT_CORE, 0)]:
        resource.setrlimit(key, (value, value))
joined = namespace['owned_capture']({'argv': recipe['argv']}, capture, 90, limits)
namespace['write'](capture / 'WHOLE-JOIN.json', joined)
clean = all(joined[key] is True for key in ['direct_child_joined', 'group_absent', 'closed_streams']) and joined['error'] is None and joined['retirement_error'] is None
stable = all(ref(row['path']) == row for row in inputs)
record = dict(scope=__doc__, status='PASS' if clean and stable and joined['returncode'] == 0 else 'FAIL_STOP_NO_REPLAY', recipe=RECIPE, returncode=joined['returncode'], joined=joined, all_inputs_stable=stable, stdout=ref(capture / 'stdout'), stderr=ref(capture / 'stderr'), wall_seconds=time.monotonic() - start, CPU_seconds=namespace['cpu_used']() - cpu, child_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, root_query_owner_build=False)
namespace['write'](capture / 'RESULT.json', record)
print(json.dumps(record, sort_keys=True))
raise SystemExit(0 if record['status'] == 'PASS' else 1)
