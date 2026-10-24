#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ONE dispatcher-granted ordinary-host mcps one bounded signal-correction fixture; reuse accepted990 capture without changes.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import signal

HERE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-mcps/signal-diagnostic-correction-1')
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('accepted990_capture', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
capture = Path(__file__).resolve().parent
def limits():
    os.sched_setaffinity(0, {0})
    for number, value in ((resource.RLIMIT_AS, 1 << 30), (resource.RLIMIT_CPU, 120),
                          (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
                          (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(number, (value, value))
os.sched_setaffinity(0, {0})
old_cwd = os.getcwd()
for number in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(number, h.stop)
signal.setitimer(signal.ITIMER_REAL, 130)
try:
    os.chdir(HERE)
    result = h.owned_capture({'argv': ['/usr/bin/python3', '-I', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-mcps/signal-diagnostic-correction-1/fixture/run_equivalence.py', '--execute', '--cc', '/usr/bin/cc', '--rustc', '/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc']}, capture, 126, limits)
    h.write(capture / 'RESULT.json', result)
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    os.chdir(old_cwd)
okay = (result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent'] and
        result['closed_streams'] and result['error'] is None and result['retirement_error'] is None)
print(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                  'okay':okay,'capture':str(capture),'result':result},sort_keys=True))
raise SystemExit(0 if okay else 1)
