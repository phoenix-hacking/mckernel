"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One unchanged c252 read-only census using the existing h990 capture functions.
Run ONLY in root's already admitted observer context including CPUs2-5; never
changes affinity, opens the permanent mutex, imports an owner or builds code.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import time

D = Path(__file__).resolve().parent
CALLER = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-corrected-driver-successor-binding-source-1/frontend-source-1/run_frozen_current290_image_entry.ATTEMPT5.READONLY-SEED.py')
assert hashlib.sha256(CALLER.read_bytes()).hexdigest() == '9ee96b818705a2519f2bd7186d152a41a109342d54959e16d20e2de6645c3e95'
spec = importlib.util.spec_from_file_location('current230_metadata_functions_only', CALLER)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.digest(m.CONFIG) == m.CONFIG_SHA
cfg = m.strict(m.CONFIG)
root = Path(cfg['capture_root'])
ready = m.strict(root / 'CENSUS-READY.json')
assert os.getuid() == os.geteuid() == 1000 and {2, 3, 4, 5} <= set(os.sched_getaffinity(0))
assert time.time() < ready['deadline_epoch'] and 0 <= time.time() - ready['five_end_epoch'] <= 120
command = ready['argv']
expected = list(cfg['commands']['compact_census']['argv'])
expected[-1] = m.digest(m.authenticate(ready['compact_request']))
assert command == expected
m.authenticate(cfg['commands']['compact_census']['source'])
SOURCE = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start',
             'terminal_unreaped', 'wait_terminal', 'owned_capture'}
assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
body = []
for node in ast.parse(raw, str(SOURCE)).body:
    if (isinstance(node, (ast.Import, ast.ImportFrom)) or
        isinstance(node, ast.FunctionDef) and node.name in functions or
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets)):
        body.append(node)
ns = {'__file__': str(SOURCE)}
exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), 'exec'), ns)
for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(signum, ns['stop'])
capture = root / 'census-observer-capture-1'
capture.mkdir(mode=0o700)
ns['write'](capture / 'command.json', {'argv': command})
started = time.time()
cpu = ns['cpu_used']()
def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 << 20, 32 << 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_STACK, (2 << 20, 2 << 20))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
result = ns['owned_capture']({'argv': command}, capture, 60, limits)
finished = time.time()
ns['write'](capture / 'receipt.json', result)
ns['need'](result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent'] and
           result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and
           result['captures']['stderr']['size'] == 0, 'stop failed census; no replay')
m.publish(root / 'ROOT-CENSUS-CLOSED.json', dict(author='/root', scope=m.SCOPE,
          argv=command, source=cfg['commands']['compact_census']['source'],
          observer_source=m.reference(__file__), receipt=m.reference(capture / 'receipt.json'),
          stdout=m.reference(capture / 'stdout'), stderr=m.reference(capture / 'stderr'),
          started_at_epoch=started, finished_at_epoch=finished,
          CPU_seconds=ns['cpu_used']() - cpu, actual_inherited_affinity=sorted(os.sched_getaffinity(0))))
print(json.dumps({'status': 'PASS_READONLY_CENSUS_CAPTURE_ONLY', 'closed': str(root / 'ROOT-CENSUS-CLOSED.json')}, sort_keys=True))
