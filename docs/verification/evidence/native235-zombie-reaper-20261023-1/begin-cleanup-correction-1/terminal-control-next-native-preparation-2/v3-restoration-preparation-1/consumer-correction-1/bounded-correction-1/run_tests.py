"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys

D = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')
E = REPO/'docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/v3-restoration-preparation-1/consumer-correction-1'
HELPER = REPO/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('accepted_capture', HELPER)
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
assert hashlib.sha256((D/'test_full_nested.py').read_bytes()).hexdigest() == 'da2fe5a2b542e6b7993279696a0a254a9f7d4a01afd892f0c24304a7b31a111f'
attempt = sys.argv[1]
assert attempt in ('attempt-1', 'bounded-correction-1')
capture = D/attempt
capture.mkdir()
for name in ('run_tests.py', 'test_full_nested.py', 'reboot_workload_capture.py', 'second_stop_capture.py', 'case_evaluator.py'):
    (capture/name).write_bytes((D/name).read_bytes())
os.sched_setaffinity(0, {6})
for k, v in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)):
    resource.setrlimit(k, (v, v))
command = dict(argv=['/home/holden/anaconda3/bin/python3', '-I', '-B', str(D/'test_full_nested.py')], purpose=__doc__, shell=False)
h.write(capture/'command.json', command)
result = h.owned_capture(command, capture, 90, lambda: None)
h.write(capture/'result.json', result)
for q in capture.iterdir():
    if q.is_file():
        out = E/attempt/q.name; out.parent.mkdir(exist_ok=True); out.write_bytes(q.read_bytes())
print(json.dumps(result, sort_keys=True))
