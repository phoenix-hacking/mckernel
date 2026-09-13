from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, shutil
assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
repo, work = Path('/workspace'), Path('/work')
out = work / 'stability-transport-fault-run-20260913-prepublish-hard-5'
out.mkdir(); (out / 'tmp').mkdir()
record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(), inputs=[],
              application_acceptance=False, transport_acceptance=False, production_gate_credit=False,
              new_catalog_payloads_executed=0, mode='prepublish-hard')
def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024**2), b''):
            digest.update(data)
    return dict(path=str(path), size=path.stat().st_size, sha256=digest.hexdigest())
def save():
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
try:
    assert shutil.disk_usage(work).free > 11 * 1024**3
    shutil.copyfile(__file__, out / 'helper.py')
    hashes = {
        'scripts/tests/run_stability_transport_guest.py': 'c047955e27903fa8ee2c5cb571a83d4438c11f8c9d349912acc110f78d3fa5f6',
        'scripts/tests/prepare_stability_fault_guest.py': '922f0b4d60edae9bdec36c960cacb50ef6c11cd31b216c0e89b5279ff36af0c8',
        'scripts/application-tests/owner_observations.py': '97466f94dff53fc250509859d164a9858a4f361405ad62b82bb59ab621f77bcf',
        'scripts/application-tests/phase_observations.py': '589694ee603b096743682225ff964b39612439a3082ae7f6a80707c4755f7102',
        'scripts/application-tests/fault_control.py': 'b7ed7c6b131ff2106a1317a0d535d3a032c6c1117210a9bac4d10eebea9f68fc',
        'scripts/application-tests/qmp_capture.py': '5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741',
        'scripts/application-tests/supervisor.py': '8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873',
        'scripts/application-tests/contracts/stability-prepublish-hard-20260913-v1.json': '025ffc1bb8722c321912169825ef7c4ff0dc452c9f14dd8f82667778a29cc665',
        'scripts/tests/fixtures/stability-artifact-export/receiver.py': 'aa9e165044e9567c992a0354dacdc49b884794b31841a3871d977eeae9c8c5d9'}
    for relative, digest in hashes.items():
        source = repo / relative
        assert identity(source)['sha256'] == digest, relative
        target = out / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert identity(target)['sha256'] == digest
        record['inputs'].append(dict(original=identity(source), retained=identity(target)))
    for name, status in (
            ('stability-runnable-thread-payload-build-20260913-1', 'PASS_BUILD_ONLY'),
            ('stability-physical-comparator-tests-20260913-1', 'PASS_SYNTHETIC_PHYSICAL_COMPARATOR_ONLY'),
            ('stability-export-ack-gate-tests-20260913-1', 'PASS_ACTUAL_RECEIVER_GATE_INFRASTRUCTURE_ONLY'),
            ('stability-fault-guest-root-20260913-prepublish-hard-4', 'PREPARED_NOT_EXECUTED'),
            ('stability-fault-guest-preflight-20260913-4', 'PASS_PREFLIGHT_NO_GUEST_EXECUTION'),
            ('stability-phase-parser-tests-20260913-1', 'PASS_SYNTHETIC_PHASE_PARSER_ONLY'),
            ('stability-fault-control-tests-20260913-1', 'PASS_SYNTHETIC_FAULT_CONTROL_ONLY'),
            ('stability-artifact-pty-tests-20260913-1', 'PASS_ACTUAL_C_PTY_INFRASTRUCTURE_ONLY')):
        path = work / name / 'record.json'
        assert json.loads(path.read_text())['status'] == status
        record.setdefault('prerequisites', []).append(identity(path))
    built_payload = json.loads((work / 'stability-runnable-thread-payload-build-20260913-1/record.json').read_text())
    assert built_payload['payload_profile'] == 'runnable-thread-v1'
    assert json.loads((work / 'stability-fault-guest-root-20260913-prepublish-hard-4/record.json').read_text())['payload_profile'] == 'runnable-thread-v1'
    for row in built_payload['compiler_dependencies'] + built_payload['compiled_outputs'] + built_payload['loader_dependencies']:
        assert identity(Path(row['path'])) == row
    binding = work / 'stability-service-failure-inputs-20260913-1/record.json'
    bound = json.loads(binding.read_text()); assert bound['status'] == 'INPUTS_MATCH'
    for row in bound['checked']:
        assert identity(Path(row['path'])) == row, row['path']
    record['production_binding'] = identity(binding)
    record['production_inputs_rechecked'] = len(bound['checked'])
    compiled = work / 'stability-transport-fault-module-20260913-prepublish-hard-3/record.json'
    module = json.loads(compiled.read_text()); assert module['status'] == 'PASS_BUILD_ONLY'
    for row in module['compiled_modules'] + module['fixture_inputs'] + module['parent_inputs']:
        assert identity(Path(row['path'])) == row, row['path']
    for row in module['retained_compiler_bindings']:
        assert identity(Path(row['retained']['path'])) == row['retained']
    record['verification_module'] = identity(compiled)
    supervisor_path = out / 'scripts/application-tests/supervisor.py'
    spec = importlib.util.spec_from_file_location('fault_guest_supervisor', supervisor_path)
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    guest = work / 'stability-transport-fault-guest-20260913-prepublish-hard-5'
    argv = ['/usr/bin/python3', '-B', str(out / 'scripts/tests/run_stability_transport_guest.py'),
            '--prepared', '/work/stability-fault-guest-root-20260913-prepublish-hard-4', '--output', str(guest)]
    env = dict(PATH='/usr/local/bin:/usr/bin:/bin', LANG='C', LC_ALL='C', TZ='UTC', TMPDIR=str(out / 'tmp'))
    record.update(command=argv, environment=env, phase='guest'); save()
    result = supervisor.run_supervised(argv, cwd=str(out), env=env, attempt_dir=str(out / 'collection'),
        timeout_seconds=340, cleanup_timeout_seconds=15, stdout_limit_bytes=8*1024**2, stderr_limit_bytes=8*1024**2)
    record['collection'] = result; save()
    assert result['status'] == 'COMPLETED' and result['raw_wait_status'] == 0 and result['cleanup_complete']
    observed = json.loads((guest / 'record.json').read_text())
    record['guest_record'] = identity(guest / 'record.json')
    assert observed['status'] == 'COLLECTED_REQUIRES_CONTRACT_REVIEW'
    assert observed['qemu_exit_code'] == 0 and not observed['cleanup_errors'] and observed['export_thread_finished']
    for row in record['inputs']:
        assert identity(Path(row['original']['path'])) == row['original']
        assert identity(Path(row['retained']['path'])) == row['retained']
    record['status'] = 'COLLECTED_REQUIRES_INDEPENDENT_FAULT_REVIEW'
except BaseException as error:
    record.update(status='FAIL', error_type=type(error).__name__, error=str(error)); raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat(); save(); print(record['status'], out, flush=True)
