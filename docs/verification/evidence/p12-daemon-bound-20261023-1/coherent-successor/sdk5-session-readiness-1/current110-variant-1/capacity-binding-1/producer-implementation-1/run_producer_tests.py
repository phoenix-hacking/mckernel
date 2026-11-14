"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys
D = Path(__file__).resolve().parent
E = Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/producer-implementation-1')
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('accepted_capture', HELPER)
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
attempt = D/sys.argv[1]
assert sys.argv[1] in ('attempt-1', 'bounded-correction-1')
attempt.mkdir()
for name in ('pair_long_producer.rs', 'tests.rs', 'pair_long_producer.h', 'abi_witness.c', 'run_producer_tests.py'):
    (attempt/name).write_bytes((D/name).read_bytes())
os.sched_setaffinity(0, {6})
os.environ['RUST_MIN_STACK'] = '2097152'
for k, v in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)):
    resource.setrlimit(k, (v, v))
rust = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
commands = [('C-ABI-witness', ['/usr/bin/gcc-9', '-std=c11', '-Wall', '-Wextra', '-Werror', '-c', str(D/'abi_witness.c'), '-o', str(attempt/'abi_witness.o')]),
            ('Rust-actual-loop-tests-build', [rust, '--edition=2021', '--test', '-C', 'codegen-units=1', '-C', 'opt-level=1', '-C', 'debuginfo=0', '-C', 'linker=/usr/bin/gcc-9', str(D/'pair_long_producer.rs'), '-o', str(attempt/'producer-tests')]),
            ('actual-loop-tests', [str(attempt/'producer-tests'), '--test-threads=1'])]
results = []
for label, argv in commands:
    capture = attempt/label; capture.mkdir()
    command = dict(argv=argv, purpose=__doc__, shell=False)
    h.write(capture/'command.json', command)
    joined = h.owned_capture(command, capture, 90, lambda: None)
    h.write(capture/'result.json', joined)
    results.append(dict(label=label, whole_join=joined))
    if joined['returncode'] != 0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error']:
        break
h.write(attempt/'RESULT.json', dict(scope=__doc__, results=results, status='PASS' if len(results)==3 and all(r['whole_join']['returncode']==0 for r in results) else 'FAIL_STOP_FIRST_FAILURE'))
for q in D.rglob('*'):
    if q.is_file() and q.suffix != '.o' and q.name != 'producer-tests':
        out = E/q.relative_to(D); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(q.read_bytes())
print(json.dumps(dict(status=json.loads((attempt/'RESULT.json').read_text())['status'], commands=len(results), returns=[r['whole_join']['returncode'] for r in results])))
