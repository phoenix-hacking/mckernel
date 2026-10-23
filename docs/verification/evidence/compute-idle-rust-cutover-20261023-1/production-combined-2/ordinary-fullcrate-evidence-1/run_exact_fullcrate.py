"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One root-granted ordinary pinned full-crate invocation; no retries or linking.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

REPO = Path(__file__).resolve().parent
BASE = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')
OUT = BASE / 'ordinary-fullcrate-evidence-1'
DESCRIPTOR = REPO.parent / 'EXACT-PINNED-HOST-RUST-CANDIDATE.CORRECTED.NOT-RELEASED.json'
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stable(path, maximum):
    before = path.stat()
    need(before.st_size <= maximum, 'bounded input: ' + str(path))
    raw = path.read_bytes()
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    need(all(getattr(before, k) == getattr(after, k) for k in fields) and len(raw) == after.st_size, 'stable input: ' + str(path))
    return raw, dict(path=str(path), sha256=sha(raw), **{k: getattr(after, k) for k in fields})

def main():
    start = time.monotonic()
    need(os.sched_getaffinity(0) == {0}, 'CPU0 only')
    for kind, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)):
        need(resource.getrlimit(kind) == (value, value), 'exact inherited profile')
    need(os.environ.get('RUST_MIN_STACK') == '2097152', 'exact Rust stack environment')
    desc_raw, desc_ref = stable(DESCRIPTOR, 32768)
    need(desc_ref['sha256'] == 'cdfb8330d97dcbbac78afa1881f0ae316914606fec44bc7594290da8d7a3261b', 'descriptor hash')
    desc = json.loads(desc_raw)
    argv = desc['argv_without_shell']
    need(len(argv) == 46 and desc['shell_execution'] is False, 'exact shell-free compiler argv')
    compiler = Path(argv[6])
    _, compiler_ref = stable(compiler, 32 << 20)
    need(compiler_ref['sha256'] == '70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09', 'pinned nightly compiler')
    source_manifest = BASE / 'source-materialization-attempt-2/source-inputs.json'
    manifest_raw, manifest_ref = stable(source_manifest, 16 << 20)
    need(manifest_ref['sha256'] == '9b86c84a92133678171b3e476560bcdfc99070f727b9c11c764de7092de8b88c', 'accepted source manifest')
    manifest = json.loads(manifest_raw)
    source_root = BASE / 'source-materialization-attempt-2/materialized-source'
    source_refs = {}
    for name, expected in manifest['materialized_repository_files'].items():
        if name.startswith('kernel/rust/') and name.endswith('.rs'):
            _, row = stable(source_root / name, 2 << 20)
            need(row['sha256'] == expected, 'Rust source input: ' + name)
            source_refs[name] = row
    need(len(source_refs) == 80 and Path(argv[-1]) == source_root / 'kernel/rust/lib.rs', 'production crate input closure')
    helper_raw, helper_ref = stable(HELPER, 1 << 20)
    need(helper_ref['sha256'] == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8', 'accepted owned capture helper')
    spec = importlib.util.spec_from_file_location('accepted_owned_capture', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    need(sha(HELPER.read_bytes()) == sha(helper_raw), 'helper stable during import')
    cwd = Path(desc['explicit_fresh_HOST_cwd'])
    output = Path(desc['required_new_output'])
    need(not cwd.exists() and not OUT.exists(), 'fresh ordinary output and evidence namespaces')
    cwd.mkdir(mode=0o700)
    OUT.mkdir(mode=0o700)
    capture = OUT / 'capture'
    capture.mkdir(mode=0o700)
    command = dict(argv=argv, cwd=str(cwd), purpose=SCOPE, shell=False, extra_environment=desc['compiler_environment_extra'])
    helper.write(OUT / 'command.json', command)
    helper.write(OUT / 'input-bindings.json', dict(scope=SCOPE, descriptor=desc_ref, compiler=compiler_ref, helper=helper_ref, source_manifest=manifest_ref, rust_source_inputs=source_refs, semantic_diff=desc['semantic_diff'], original_recipe=desc['original_recipe'], source_derivative_sha256=manifest['source_derivative_sha256'], materialization_sha256=manifest['materialization_sha256']))
    os.chdir(cwd)
    joined = helper.owned_capture(command, capture, 90, lambda: None)
    helper.write(OUT / 'whole-join.json', joined)
    passed = joined['returncode'] == 0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None
    artifact = helper.hashed(output, 32 << 20) if passed else None
    result = dict(scope=SCOPE, status='PASS_ACTUAL_HOST_PRODUCTION_FULLCRATE' if passed else 'FAIL_STOP_NO_RETRY', command=command, descriptor=desc_ref, compiler=compiler_ref, source_manifest=manifest_ref, object=artifact, whole_join=joined, elapsed_seconds=time.monotonic()-start, production_default_link_proven=False, native_proven=False, C_retirement_proven=False, no_automatic_retry=True)
    helper.write(OUT / 'result.json', result)
    for name in ('command.json', 'input-bindings.json', 'whole-join.json', 'result.json'):
        with (REPO / name).open('xb') as stream:
            stream.write((OUT / name).read_bytes())
    for name in ('stdout', 'stderr'):
        with (REPO / ('compiler.' + name)).open('xb') as stream:
            stream.write((capture / name).read_bytes())
    print(json.dumps(dict(status=result['status'], returncode=joined['returncode'], seconds=result['elapsed_seconds'], object=artifact, whole_join=str(OUT / 'whole-join.json')), sort_keys=True), flush=True)
    return 0 if passed else 1

if __name__ == '__main__':
    sys.exit(main())
