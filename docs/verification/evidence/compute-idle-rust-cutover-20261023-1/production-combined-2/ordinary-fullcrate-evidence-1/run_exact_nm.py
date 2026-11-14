"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One separately granted read-only nm observation of the retained full Rust object.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys

D = Path(__file__).resolve().parent
H = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/ordinary-fullcrate-evidence-1')
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
DRIVER = H.parent / 'correction1/native_rust_exact_mckernel_image_offline.py'

def main():
    assert os.sched_getaffinity(0) == {0}
    for kind, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 30), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)):
        assert resource.getrlimit(kind) == (value, value)
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
    spec = importlib.util.spec_from_file_location('accepted_capture_nm', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = json.loads((H / 'result.json').read_bytes())
    obj = Path(result['object']['path'])
    assert helper.hashed(obj, 32 << 20) == result['object']
    driver_raw = DRIVER.read_bytes()
    assert hashlib.sha256(driver_raw).hexdigest() == '1d1d600cdd1f3a1236c89b736c0d57f4c52b148b2dda30b99afe00b4fcf2724c'
    tree = ast.parse(driver_raw, str(DRIVER))
    names = {'M14_IDLE_IMPORTS', 'M14_MEMORY_IMPORTS', 'M14_RUST_EXPORTS'}
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names]
    assert len(assignments) == 3
    namespace = {}
    exec(compile(ast.Module(body=assignments, type_ignores=[]), str(DRIVER), 'exec'), {'__builtins__': {}}, namespace)
    expected = namespace['M14_RUST_EXPORTS']
    assert len(expected) == len(set(expected)) == 10
    capture = H / 'nm-capture-1'
    capture.mkdir(mode=0o700)
    command = {'argv': ['/usr/bin/nm', '--defined-only', '-g', str(obj)], 'purpose': result['scope']}
    nm_raw = Path('/usr/bin/nm').read_bytes()
    helper.write(H / 'nm-command.json', dict(command=command, nm_sha256=hashlib.sha256(nm_raw).hexdigest(), expected_from_driver=dict(path=str(DRIVER), sha256=hashlib.sha256(driver_raw).hexdigest(), names=list(expected))))
    joined = helper.owned_capture(command, capture, 35, lambda: None)
    helper.write(H / 'nm-whole-join.json', joined)
    transport = joined['returncode'] == 0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None
    matches = {name: [] for name in expected}
    if transport:
        for line in (capture / 'stdout').read_text().splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[2] in matches:
                matches[parts[2]].append(dict(address=parts[0], type=parts[1], name=parts[2], raw=line))
    unchanged = helper.hashed(obj, 32 << 20) == result['object']
    passed = transport and unchanged and all(len(rows) == 1 and rows[0]['type'] == 'T' for rows in matches.values())
    proof = dict(scope=result['scope'], status='PASS_10_UNIQUE_ACTUAL_FULLCRATE_EXPORTS' if passed else 'FAIL_STOP_NO_RETRY', expected_source=dict(path=str(DRIVER), sha256=hashlib.sha256(driver_raw).hexdigest()), object=result['object'], object_unchanged=unchanged, symbols=matches, whole_join=joined, default_C_consumer_or_final_link_proven=False, native_proven=False, retirement_proven=False, no_automatic_retry=True)
    helper.write(H / 'nm-result.json', proof)
    for name in ('nm-command.json', 'nm-whole-join.json', 'nm-result.json'):
        with (D / name).open('xb') as stream:
            stream.write((H / name).read_bytes())
    for name in ('stdout', 'stderr'):
        with (D / ('nm.' + name)).open('xb') as stream:
            stream.write((capture / name).read_bytes())
    print(json.dumps(dict(status=proof['status'], command=command, object_unchanged=unchanged, exports={k: v for k, v in matches.items()}, seconds=joined['seconds']), sort_keys=True), flush=True)
    return 0 if passed else 1

if __name__ == '__main__':
    sys.exit(main())
