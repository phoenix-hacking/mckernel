"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time

root = Path(__file__).resolve().parent
helper = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw = helper.read_bytes()
if hashlib.sha256(raw).hexdigest() != '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8':
    raise ValueError('h990 source binding changed')
functions = {'need', 'write', 'hashed', 'stop', 'members', 'cpu_used', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
constants = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
nodes = []
for node in ast.parse(raw).body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        nodes.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in functions:
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets):
        nodes.append(node)
namespace = {'__file__': str(helper), '__name__': 'generation_h990'}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(helper), 'exec'), namespace)
if os.sched_getaffinity(0) != {0}:
    raise ValueError('CPU0 grant binding required')
for kind, bound in ((resource.RLIMIT_AS, 512 << 20), (resource.RLIMIT_CPU, 90),
                    (resource.RLIMIT_FSIZE, 16 << 20), (resource.RLIMIT_NOFILE, 256),
                    (resource.RLIMIT_CORE, 0)):
    if resource.getrlimit(kind) != (bound, bound):
        raise ValueError('exact root resource grant required')
ready = json.loads((root / 'READY.json').read_text())
capture = root / 'retained-evaluation-h990-capture-1'
capture.mkdir(mode=0o700)
command = {'argv': ['/usr/bin/python3', '-I', str(root / 'evaluate_retained_cmake.py')], 'cwd': str(Path.cwd()), 'scope': __doc__}
namespace['write'](capture / 'ROOT-GRANT.json', {
    'root_message': 'Actual COPY7 physicaldda45e/currentf37ff2 accepted. Ordinary CPU0/onejob<=512MiB,16MiB output,150s wall. Retained three-case evidence verification only. No CMake or compiler rerun; no actual daemon Rust compile/root/Docker/guest/heavy/canonical edit.',
    'argv': command['argv'], 'profile': ready['ordinary_check_profile'],
    'enforced': {'CPU': 0, 'AS': 512 << 20, 'CPU_seconds': 90, 'FSIZE': 16 << 20, 'NOFILE': 256, 'CORE': 0},
})
namespace['write'](capture / 'command.json', command)
for number in namespace['STOP_SIGNALS']:
    signal.signal(number, namespace['stop'])
start = time.monotonic()
signal.setitimer(signal.ITIMER_REAL, 144)
try:
    result = namespace['owned_capture'](command, capture, 143, lambda: None)
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
result['whole_seconds'] = time.monotonic() - start
result['total_cpu_seconds'] = namespace['cpu_used']()
result['aggregate_output_bytes'] = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
namespace['write'](capture / 'status.json', result)
actual = root / 'retained-evaluation-1'
if actual.exists():
    namespace['write'](actual / 'OUTER-CAPTURE.json', {'capture': str(capture), 'result': result})
    namespace['write'](actual / 'ROOT-GRANT.json', json.loads((capture / 'ROOT-GRANT.json').read_text()))
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent'] and not result['error'] and not result['retirement_error'] and result['aggregate_output_bytes'] < 16 << 20 else 1)
