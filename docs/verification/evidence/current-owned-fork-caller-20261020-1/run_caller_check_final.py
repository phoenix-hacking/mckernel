from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, time

P = Path(__file__).resolve().parent
E = P / 'check-3'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
HELPER = Path('/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/guest-control-consumer-1/current-fullcrate-owner-1/owned_capture_helpers.py')
CENSUS = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py')
COMMANDS = [
    ['compile-caller', [RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings',
        str(P / 'fixture-final/actual-child-credits.rs'), '-C', 'link-arg=' + str(P / 'check-1/caller_branch.o'), '-o', str(E / 'actual-caller')]],
    ['caller-test', [str(E / 'actual-caller'), 'caller_tests::caller_', '--test-threads=1', '--nocapture']],
    ['compile-owned-regression', [RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings',
        str(P / 'fixture-owned-final/actual-child-credits.rs'), '-o', str(E / 'actual-owned')]],
    ['owned-regression-test', [str(E / 'actual-owned'), 'offload_tests::owned_request_', '--test-threads=1', '--nocapture']],
    ['compile-borrowed-regression', [RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings',
        str(P / 'fixture-borrowed-final/actual-child-credits.rs'), '-o', str(E / 'actual-borrowed')]],
    ['borrowed-regression-test', [str(E / 'actual-borrowed'), 'offload_tests::owned_offload_', '--test-threads=1', '--nocapture']],
]



def main():
    assert os.sched_getaffinity(0) == {6}
    limits = {resource.RLIMIT_AS: 1 << 30, resource.RLIMIT_CPU: 30,
              resource.RLIMIT_FSIZE: 32 << 20, resource.RLIMIT_NOFILE: 256, resource.RLIMIT_CORE: 0}
    assert all(resource.getrlimit(k) == (v, v) for k, v in limits.items())
    assert not E.exists()
    pins = json.loads((P / 'CHECK-INPUT-PINS-FINAL.json').read_bytes())
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
    for label,count in [('caller-test',6),('owned-regression-test',6),('borrowed-regression-test',4)]:
        assert str(count) + ' passed; 0 failed' in (E / label / 'stdout').read_text()
    capture.write(E / 'result.json', {'status': 'PASS_ACTUAL_CURRENT_OWNED_CALLER_SELECTED_BRANCH',
        'commands': 6, 'unchanged_selected_C_object_reused': True, 'new_caller_tests': 6, 'unchanged_owned_tests': 6, 'unchanged_borrowed_tests': 4,
        'whole_direct_joined': True, 'groups_absent': True,
        'actual_Rust_C_ABI_and_exact_selected_C_proposal_branch': True,
        'actual_initializer_child_cpu_zero_and_reserved_cpu_one': True,
        'exact_VM_geometry_and_owned_request': True,
        'pretransfer_allocation_and_credit_refusal_use_C_cleanup_edge': True,
        'posttransfer_retained_paths_bypass_C_cleanup_and_chain_runq_edge': True,
        'full_production_C_selected_fallback_GCC14_proof': False,
        'actual_C_destructor_scheduler_native_or_default_activation': False,
        'default_provider_taskMM_response_revoke_ACK_holds_unchanged': True})



if __name__ == '__main__': main()
