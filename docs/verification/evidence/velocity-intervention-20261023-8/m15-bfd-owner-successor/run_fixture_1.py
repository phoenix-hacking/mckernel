#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ONE dispatcher-granted pure fixture; reuse accepted990 capture without changes.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import signal

HERE = Path(__file__).resolve().parent
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('accepted990_capture', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
capture = HERE / 'fixture-actual-1'
capture.mkdir(mode=0o700)
def limits():
    os.sched_setaffinity(0, {0})
    for number, value in ((resource.RLIMIT_AS, 512 << 20), (resource.RLIMIT_CPU, 10),
                          (resource.RLIMIT_FSIZE, 16 << 20), (resource.RLIMIT_NOFILE, 128),
                          (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(number, (value, value))
old_cwd = os.getcwd()
for number in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(number, h.stop)
signal.setitimer(signal.ITIMER_REAL, 35)
try:
    os.chdir(HERE)
    result = h.owned_capture({'argv':['/usr/bin/python3', '-I', '-B', str(HERE / 'test_compile_owner.py')]}, capture, 30, limits)
    h.write(capture / 'RESULT.json', result)
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    os.chdir(old_cwd)
okay = (result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent'] and
        result['closed_streams'] and result['error'] is None and result['retirement_error'] is None)
print(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                  'okay':okay,'capture':str(capture),'result':result},sort_keys=True))
raise SystemExit(0 if okay else 1)
