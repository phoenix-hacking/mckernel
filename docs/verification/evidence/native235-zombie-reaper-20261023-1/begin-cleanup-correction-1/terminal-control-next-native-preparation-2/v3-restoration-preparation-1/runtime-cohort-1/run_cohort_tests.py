"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys
D = Path(__file__).resolve().parent
E = Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/v3-restoration-preparation-1/runtime-cohort-1')
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('accepted_capture', HELPER)
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
capture = D/sys.argv[1]
assert sys.argv[1] in ('cohort-fixtures-1', 'cohort-fixtures-correction-1')
capture.mkdir()
for name in ('test_cohort.py', 'run_cohort_tests.py', 'native_diagnostic_container_owner.py', 'native_diagnostic_runner.py', 'EXACT-M05-RUNTIME-COHORT.json'):
    (capture/name).write_bytes((D/name).read_bytes())
os.sched_setaffinity(0, {0})
for k, v in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)):
    resource.setrlimit(k, (v, v))
command = dict(argv=['/home/holden/anaconda3/bin/python3', '-I', '-B', str(D/'test_cohort.py')], purpose=__doc__, shell=False)
h.write(capture/'command.json', command)
joined = h.owned_capture(command, capture, 90, lambda: None)
h.write(capture/'result.json', joined)
for q in capture.iterdir():
    if q.is_file():
        target = E/capture.name/q.name; target.parent.mkdir(exist_ok=True); target.write_bytes(q.read_bytes())
print(json.dumps(joined, sort_keys=True))
