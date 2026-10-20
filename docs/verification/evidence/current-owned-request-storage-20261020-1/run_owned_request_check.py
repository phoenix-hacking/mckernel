from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, time

P = Path(__file__).resolve().parent
E = P / 'check-1'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
HELPER = Path('/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/guest-control-consumer-1/current-fullcrate-owner-1/owned_capture_helpers.py')
CENSUS = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py')
COMMANDS = [
    ['compile-owned', [RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings',
        str(P / 'fixture/actual-child-credits.rs'), '-o', str(E / 'actual-owned')]],
    ['owned-test', [str(E / 'actual-owned'), 'offload_tests::owned_request_', '--test-threads=1', '--nocapture']],
    ['compile-borrowed', [RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings',
        str(P / 'fixture-borrowed/actual-child-credits.rs'), '-o', str(E / 'actual-borrowed')]],
    ['borrowed-test', [str(E / 'actual-borrowed'), 'offload_tests::owned_offload_', '--test-threads=1', '--nocapture']],
]



def main():
    assert os.sched_getaffinity(0) == {6}
    limits = {resource.RLIMIT_AS: 1 << 30, resource.RLIMIT_CPU: 30,
              resource.RLIMIT_FSIZE: 32 << 20, resource.RLIMIT_NOFILE: 256, resource.RLIMIT_CORE: 0}
    assert all(resource.getrlimit(k) == (v, v) for k, v in limits.items())
    assert not E.exists()
    pins = json.loads((P / 'CHECK-INPUT-PINS.json').read_bytes())
    for row in pins['rows']:
        b = Path(row['path']).read_bytes()
        assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256'], row['path']
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
    usage = ((state.get('last_rate_limits') or {}).get('primary') or {}).get('usedPercent')
    selected = {'phase': state.get('phase'), 'pause_reason': state.get('pause_reason'), 'usedPercent': usage}
    assert selected['phase'] == 'running' and not selected['pause_reason']
    assert type(usage) in (int, float) and 0 <= usage < 100
    memory = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    assert memory >= 2 << 30
    capacity = []
    for name, floor in [('/home/holden/mckernel', 16 << 30), ('/home/holden/mckernel-work/scratch', 12 << 30)]:
        st = os.statvfs(name); available = st.f_bavail * st.f_frsize
        required = floor + (640 << 20) + (160 << 20)
        assert available >= required
        capacity.append({'path': name, 'available': available, 'required': required})
    spec = importlib.util.spec_from_file_location('accepted_owned_capture', HELPER)
    capture = importlib.util.module_from_spec(spec); spec.loader.exec_module(capture)
    capture.CENSUS_SOURCE = CENSUS
    for signum in capture.STOP_SIGNALS: signal.signal(signum, capture.stop)
    E.mkdir()
    capture.write(E / 'admission.json', {'usage_selected': selected, 'at': time.time(),
        'MemAvailable': memory, 'capacity': capacity, 'affinity': [6],
        'rlimits': {str(k): [v, v] for k, v in limits.items()}, 'jobs': 1})
    os.chdir(P)
    deadline = time.monotonic() + 28
    rows = []
    for label, argv in COMMANDS:
        remaining = deadline - time.monotonic()
        assert remaining > 5
        dest = E / label; dest.mkdir()
        command = {'argv': argv, 'cwd': str(P)}
        capture.write(dest / 'command.json', command)
        def child_limits():
            for k, v in limits.items(): resource.setrlimit(k, (v, v))
        row = capture.owned_capture(command, dest, remaining - 5, child_limits)
        rows.append(row)
        capture.write(dest / 'status.json', row)
        assert row['direct_child_joined'] and row['group_absent'] and row['returncode'] == 0
        assert not row['error'] and not row['retirement_error'] and not row['timed_out']
        assert row['captures']['stderr']['size'] == 0
    assert '6 passed; 0 failed' in (E / 'owned-test/stdout').read_text()
    assert '4 passed; 0 failed' in (E / 'borrowed-test/stdout').read_text()
    capture.write(E / 'result.json', {'status': 'PASS_ACTUAL_CURRENT_OWNED_REQUEST_STORAGE',
        'commands': 4, 'new_tests': 6, 'unchanged_borrowed_API_tests': 4,
        'whole_direct_joined': True, 'groups_absent': True,
        'same_owned_request_pointer': True, 'owned_request_retained_after_begin': True,
        'private_cancel_frees_after_detach': True, 'allocation_failure_cleanup': True,
        'private_begin_busy_returns_owner': True, 'actual_parent_counter_CAS_and_release_bodies': True,
        'child_VM_CPU_obligations_unchanged': True, 'actual_offload_adapter_calls': 6,
        'actual_scheduler_reservation_or_native_claim': False,
        'new_current_do_fork_callers': 0, 'activation_or_ACK_authority': False})



if __name__ == '__main__': main()
