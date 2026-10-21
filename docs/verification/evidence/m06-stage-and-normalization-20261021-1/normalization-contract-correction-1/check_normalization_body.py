"""Finite actual normalizer-body fixture; execute only after exact review/grant."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import time

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def put(path, raw):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

def forbidden(*args, **kwargs):
    raise AssertionError('fixture forbids process/socket/clock/root effects')

def main():
    assert os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000
    cfg = json.loads((HERE/'FIXTURE-SETTINGS.json').read_bytes())
    expected_settings = json.loads((HERE/'SETTINGS.json').read_bytes())
    raw = Path(expected_settings['source_manifest']['path']).read_bytes()
    manifest = json.loads(raw)
    assert len(manifest) == 8 and manifest['case_id'] == 'practical.process.clone3-io-unsupported'
    assert manifest['payload']['oracle'] == dict(exit_code=0, stderr_hex='', stdout_hex='72633d2d31206572726e6f3d393520656f706e6f74737570703d31206368696c645f637265617465643d300a')
    root = Path(cfg['fixture_output'])
    assert not os.path.lexists(root)
    runtime = Path(expected_settings['runtime_source_directory'])
    verifier = load('fixture_actual_verifier', runtime/'native_owner_binding.py')
    diagnostic = load('fixture_actual_diagnostic', runtime/'native_diagnostic.py')
    # Every nonce and real QMP pathname must pass existing API before effects.
    for item in cfg['vectors']:
        plan = verifier.paths(item['attempt_parent'], item['nonce'])
        assert not os.path.lexists(Path(item['attempt_parent']).parent)
        assert not os.path.lexists(item['manifest_directory'])
        assert plan['qmp_socket_bytes'] <= 107
        assert diagnostic.expected_qemu_argv(manifest, Path(plan['attempt'])) == item['proposed_full_qemu_argv']
    subprocess.Popen = forbidden
    os.execve = forbidden
    socket.socket = forbidden
    time.monotonic = forbidden
    time.time = forbidden
    root.mkdir(mode=0o700)
    results = []
    for item in cfg['vectors']:
        vector_dir = root/item['name']
        vector_dir.mkdir(mode=0o700)
        settings = dict(expected_settings)
        for key in ('attempt_parent', 'manifest_directory', 'nonce', 'proposed_full_qemu_argv'):
            settings[key] = item[key]
        put(vector_dir/'SETTINGS.json', encode(settings))
        put(vector_dir/'INPUT-PINS.json', (HERE/'INPUT-PINS.json').read_bytes())
        put(vector_dir/'prepare_native.py', (HERE/'prepare_native.py').read_bytes())
        body = load('actual_normalizer_'+item['name'], vector_dir/'prepare_native.py')
        baseline_load = body.load
        consumed = []
        owner_rows = []
        def observed_load(name, path):
            module = baseline_load(name, path)
            if str(path) == str(runtime/'native_diagnostic_container_owner.py'):
                # Negative vector drops one exact added file mapping, never a validator.
                if item['negative']:
                    assert cfg['missing_mapping'] in module.EXTRA_READONLY
                    module.EXTRA_READONLY = [x for x in module.EXTRA_READONLY if x != cfg['missing_mapping']]
                owner_rows.append(module)
            return module
        body.load = observed_load
        failure = None
        try:
            body.main()
        except AssertionError as exc:
            failure = str(exc)
        parent = Path(item['attempt_parent'])
        normalized = Path(item['manifest_directory'])/'manifest.json'
        assert normalized.read_bytes() == raw
        assert parent.is_dir() and parent.stat().st_mode & 0o777 == 0o700
        assert not list(parent.iterdir())
        assert not os.path.lexists(parent/('attempt-'+item['nonce']))
        owner = owner_rows[0]
        roots = [Path(owner.REPO), Path(owner.SCRATCH), *map(Path, owner.EXTRA_READONLY)]
        # Enumerate the exact body-consumed table, preserving duplicate references.
        consumed = [str(normalized), *owner.SOURCE_HASHES,
                    str(runtime/'native_owner_binding.py'), str(runtime/'native_diagnostic_container_owner.py')]
        for table in (manifest['artifacts'].values(), manifest['modules'], manifest['staging'].values()):
            for row in table:
                if isinstance(row, dict) and 'path' in row:
                    consumed.append(row['path'])
        overlay = json.loads(Path(manifest['staging']['overlay_manifest']['path']).read_bytes())
        for row in overlay['sources'].values():
            if isinstance(row, dict) and 'path' in row:
                consumed.append(row['path'])
        missing = sorted({p for p in consumed if not any(Path(p) == r or (r.is_dir() and r in Path(p).parents) for r in roots)})
        assert len(owner.SOURCE_HASHES) == cfg['source_pin_count']
        assert len(consumed) == cfg['consumed_reference_count']
        if item['negative']:
            assert failure == cfg['missing_mapping'] and missing == [cfg['missing_mapping']]
            assert set(p.name for p in vector_dir.iterdir()) == {'SETTINGS.json', 'INPUT-PINS.json', 'prepare_native.py'}
        else:
            assert failure is None and missing == []
            assert set(p.name for p in vector_dir.iterdir()) == {'SETTINGS.json', 'INPUT-PINS.json', 'prepare_native.py', 'ACTUAL-BINDING.json', 'ACTUAL-NATIVE-PREFLIGHT.json'}
            actual = json.loads((vector_dir/'ACTUAL-NATIVE-PREFLIGHT.json').read_bytes())
            assert actual['normalized_manifest_byte_exact'] and actual['parent_empty'] and actual['attempt_absent']
            assert actual['qemu_argv'] == item['proposed_full_qemu_argv']
            assert actual['guest_runs'] == actual['root_operations'] == actual['clocks_or_host_effects'] == 0
            assert actual['consumed_paths'] == sorted(set(consumed))
            assert actual['runtime_release'] is None and actual['native_execution_release'] is None
        results.append(dict(name=item['name'], expected_negative=item['negative'], failure=failure,
                            references=len(consumed), unique_paths=len(set(consumed)), missing=missing,
                            source_pins=len(owner.SOURCE_HASHES), parent_empty=True, attempt_absent=True,
                            manifest_byte_exact=True, outputs=sorted(p.name for p in vector_dir.iterdir())))
    result = dict(schema='mckernel.m06.actual-normalizer-body-fixture.v1', status='PASS', vectors=results,
                  production_acceptance=False, native_release=None, root_operations=0, guest_runs=0)
    put(root/'FIXTURE-RESULT.json', encode(result))
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
