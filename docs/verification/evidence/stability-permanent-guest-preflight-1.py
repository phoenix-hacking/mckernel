from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, shutil
assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
out = Path('/work/stability-fault-guest-preflight-20260913-permanent-1')
out.mkdir(); (out / 'tmp').mkdir()
record = dict(status='RUNNING', inputs=[], commands=[], started_utc=datetime.now(timezone.utc).isoformat(),
              guest_execution=False, application_acceptance=False, transport_acceptance=False)
def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())
def save():
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
try:
    shutil.copyfile(__file__, out / 'helper.py')
    src = Path('/workspace/scripts/application-tests/supervisor.py')
    assert identity(src)['sha256'] == '8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873'
    shutil.copyfile(src, out / 'supervisor.py')
    spec = importlib.util.spec_from_file_location('preflight_supervisor', out / 'supervisor.py')
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    prepared = Path('/work/stability-fault-guest-root-20260913-permanent-backpressure-1')
    built = json.loads((prepared / 'record.json').read_text()); assert built['status'] == 'PREPARED_NOT_EXECUTED'
    for relative in ('case', 'case/work'):
        path = prepared / 'root' / relative
        assert path.is_dir() and not path.is_symlink() and path.stat().st_mode & 0o777 == 0o755
    assert not list((prepared / 'root/case/work').iterdir())
    record['controller_cwd'] = dict(path='/case/work', directory=True, empty=True, mode_octal='0755')
    assert built['payload_profile'] == 'runnable-thread-v1'
    payload = json.loads(Path('/work/stability-runnable-thread-payload-build-20260913-1/record.json').read_text())
    actual = identity(prepared / 'root/bin/fault-payload')
    assert any(row['sha256'] == actual['sha256'] and row['size'] == actual['size'] for row in payload['compiled_outputs'])
    record['payload'] = actual
    assert built['controller_profile'] == 'owner-phase-v2'
    controller = json.loads(Path('/work/stability-owner-terminal-controller-build-20260913-1/record.json').read_text())
    actual = identity(prepared / 'root/bin/fault-controller')
    assert any(row['sha256'] == actual['sha256'] and row['size'] == actual['size'] for row in controller['compiled_outputs'])
    record['controller'] = actual
    init = prepared / 'root/init'
    assert identity(init) == built['init']
    coreutils = prepared / 'root/usr/bin/coreutils'
    assert any(r.get('path') == 'usr/bin/coreutils' and r['sha256'] == identity(coreutils)['sha256']
               for r in built['root_inventory'])
    qemu = Path('/usr/libexec/qemu-kvm')
    record['inputs'] += [identity(p) for p in (src, prepared / 'record.json', init, coreutils, qemu)]
    env = dict(PATH='/usr/local/bin:/usr/bin:/bin', LANG='C', LC_ALL='C', TZ='UTC', TMPDIR=str(out / 'tmp'))
    prior = Path('/work/stability-fault-guest-preflight-20260913-1/record.json')
    old = json.loads(prior.read_text()); assert old['status'] == 'PASS_PREFLIGHT_NO_GUEST_EXECUTION'
    for p in (coreutils, qemu):
        actual = identity(p)
        assert any(row['size'] == actual['size'] and row['sha256'] == actual['sha256'] for row in old['inputs'])
    record['reused_unchanged_tool_preflight'] = identity(prior)
    record['reused_checks'] = ['inherited-coreutils-sleep', 'qemu-virtio-serial-properties', 'qemu-virtserialport-properties']
    jobs = [('prepared-init-syntax', ['/bin/bash', '-n', str(init)])]
    for label, argv in jobs:
        record['phase'] = label; save()
        result = supervisor.run_supervised(argv, cwd=str(out), env=env, attempt_dir=str(out / label),
            timeout_seconds=15, cleanup_timeout_seconds=15, stdout_limit_bytes=1024**2, stderr_limit_bytes=1024**2)
        record['commands'].append(dict(label=label, argv=argv, environment=env, collection=result)); save()
        assert result['status'] == 'COMPLETED' and result['raw_wait_status'] == 0 and result['cleanup_complete'], label
    record['status'] = 'PASS_PREFLIGHT_NO_GUEST_EXECUTION'
except BaseException as error:
    record.update(status='FAIL', error_type=type(error).__name__, error=str(error)); raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat(); save(); print(record['status'], out, flush=True)
