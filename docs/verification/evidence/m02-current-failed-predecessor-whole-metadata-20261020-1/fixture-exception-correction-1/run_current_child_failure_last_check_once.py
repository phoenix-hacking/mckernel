"""Exact existing990807 ordinary capture caller; external root grant required."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HELPER = Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
INPUT_SHA = '5057b68e57fd9b87a6b26a1fabd208e38dfcd4f05319d5b4f1380fad509be226'
CHECK_SHA = '6ed5ba19b0792f6cd71776205337c4ae1bf839c82721ebe923db7a3bb887c78c'

def main():
    assert len(sys.argv) == 1 and sys.version_info[:2] == (3, 8)
    assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
    for which, value in ((resource.RLIMIT_AS, 1 << 30), (resource.RLIMIT_CPU, 10), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NOFILE, 256)):
        assert resource.getrlimit(which) == (value, value)
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA and HELPER.stat().st_mode == 33152
    assert hashlib.sha256((HERE / 'CHECK-INPUTS.json').read_bytes()).hexdigest() == INPUT_SHA
    assert hashlib.sha256((HERE / 'check_current_child_failure_last_once.py').read_bytes()).hexdigest() == CHECK_SHA
    inputs = json.loads((HERE / 'CHECK-INPUTS.json').read_bytes())
    for ref in (inputs['candidate'], inputs['current_M02_snapshot']):
        assert hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest() == ref['sha256']
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
    used = state['last_rate_limits']['primary']['usedPercent']
    assert used < 100
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    assert available >= 6 << 30
    host, scratch = os.statvfs(HERE), os.statvfs('/home/holden/mckernel-work/scratch')
    host_free, scratch_free = host.f_bavail * host.f_frsize, scratch.f_bavail * scratch.f_frsize
    assert host_free >= (16 << 30) + (64 << 20) and scratch_free >= (12 << 30) + (1 << 20)
    capture = HERE / 'actual-current-child-failure-last-check-capture-1'
    assert not os.path.lexists(capture) and not os.path.lexists(inputs['fixture_output_namespace'])
    spec = importlib.util.spec_from_file_location('current_child_failure_exact_owned_capture_990807', HELPER)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    capture.mkdir(mode=0o700)
    engine.write(capture / 'admission.json', dict(cpu=6, usage_percent=used, MemAvailable=available, host_free=host_free, scratch_free=scratch_free, aggregate_code_bytes=2 << 30, reserve_bytes=4 << 30, external_fresh_CPU6_and_aggregate_grant_required=True))
    command = dict(argv=['/usr/bin/python3', '-I', '-B', str(HERE / 'check_current_child_failure_last_once.py'), str(HERE / 'CHECK-INPUTS.json'), INPUT_SHA])
    engine.write(capture / 'command.json', command)
    def limits():
        os.sched_setaffinity(0, {6})
        for which, value in ((resource.RLIMIT_AS, 1 << 30), (resource.RLIMIT_CPU, 10), (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NOFILE, 256)):
            resource.setrlimit(which, (value, value))
    record = engine.owned_capture(command, capture, wall_seconds=15, limits=limits)
    engine.write(capture / 'status.json', record)
    ok = record['returncode'] == 0 and record['direct_child_joined'] and record['group_absent'] and not record['timed_out'] and record['error'] is None and record['retirement_error'] is None and record['closed_streams'] and record['captures']['stderr']['size'] == 0
    engine.write(capture / 'whole.json', dict(status='PASS_CURRENT_CHILD_FAILURE_LAST_BODY_CHECK_ONLY' if ok else 'FAIL_PRESERVE_FIRST_FAILURE', record=record, CPU6_released_after_return=True, runtime_release=None, guest_runs=0))
    print(json.dumps(dict(returncode=record['returncode'], direct_child_joined=record['direct_child_joined'], group_absent=record['group_absent'], closed_streams=record['closed_streams'], capture=str(capture))))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
