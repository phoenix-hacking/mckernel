"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Capture actual held-resource facts and bind the existing three-command packet.
No grant, review decision, Docker workload, cleanup or policy mutation occurs.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, time
A = Path(__file__).resolve().parent
E = A.parent
B = E / 'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3'
def read(path):
    return json.loads(path.read_bytes())
def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
policy = E / 'scratch-growth-final-copy-close-source-1/recover_growth_custody.py'
assert reference(policy)['sha256'] == '04b5c6af885baca472e99e590bf07ae360dacad95487709477cf3d2bf8d6c90a'
spec = importlib.util.spec_from_file_location('accepted_account_guard', policy)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
state = read(Path('/home/holden/mckernel/.git/os-autopilot/state.json'))
guard.check_account_state(state, time.time())
clocks = [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)]
assert all(now < cutoff for now, cutoff in zip(clocks, guard.CUTOFFS))
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == guard.BOOT
ready = read(A / 'HOLDER/HOLDER.READY.json')
bootstrap = read(A / 'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
assert ready['nonce'] == bootstrap['nonce']
holder = ready['holder']
assert (holder['device'], holder['inode']) == (27, 4)
actual_start = int((Path('/proc') / str(holder['pid']) / 'stat').read_text().rsplit(')', 1)[1].split()[19])
assert actual_start == holder['starttime']
lock_rows = Path('/proc/locks').read_text()
assert any(len(v) >= 8 and v[1:4] == ['FLOCK', 'ADVISORY', 'WRITE'] and v[4] == str(holder['pid']) and v[5:8] == ['00:1b:4', '0', 'EOF'] for v in (line.split() for line in lock_rows.splitlines()))
argv = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'ps', '-q', '--no-trunc']
query = subprocess.run(argv, capture_output=True, text=True, timeout=15)
assert query.returncode == 0 and not query.stdout.strip() and not query.stderr
cgroup_paths = ['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us', '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us', '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes', '/sys/fs/cgroup/pids/mckernel-dev/pids.max']
cgroups = {p: Path(p).read_text().strip() for p in cgroup_paths}
assert list(cgroups.values()) == ['100000', '400000', '12884901888', '512']
assert int(Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text()) == 0
memory = {line.split(':')[0]: int(line.split(':')[1].strip().split()[0]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:', 'MemAvailable:'))}
assert memory['MemAvailable'] >= 22 * 2**30
capacity = {str(p): os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in [Path('/home/holden/mckernel'), Path('/home/holden/mckernel-work/scratch')]}
assert capacity['/home/holden/mckernel'] >= 16 * 2**30 and capacity['/home/holden/mckernel-work/scratch'] >= 14091616256
assert not (A / 'OUTPUT').exists()
resource = read(B / 'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json')
resource.update(nonce=ready['nonce'], observed_at_epoch=clocks[0], observed_clocks=clocks, reservation_owner=ready['nonce'], reservation_holder=holder, fresh_output_root=str(A / 'OUTPUT'), native_custody_clearance=bootstrap['native_custody_clearance'], reservation_ready_record=reference(A / 'HOLDER/HOLDER.READY.json'), aggregate_memory_budget_bytes=23085449216)
assert resource['aggregate_memory_budget_bytes'] <= int(21.7531 * 2**30)
resource['actual_observations'] = dict(memory=memory, capacity=capacity, cgroups=cgroups, no_running_containers=dict(argv=argv, returncode=query.returncode, stdout=query.stdout, stderr=query.stderr), lock_rows=lock_rows, host_threads=int(Path('/proc/loadavg').read_text().split()[3].split('/')[1]), thread_limit=int(Path('/proc/sys/kernel/threads-max').read_text()), canonical_account_guard=reference(policy))
write(A / 'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json', resource)
grant = read(B / 'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json')
grant.update(nonce=ready['nonce'], runner=reference(A / 'run_build_only.py'), worker=reference(A / 'build_only_worker.py'), profile=reference(A / 'PROFILE.SOURCE-ONLY.json'), review=None, resource_authority=reference(A / 'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json'), input_export_authority=reference(A / 'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'), fresh_output_root=str(A / 'OUTPUT'), native_custody_clearance=bootstrap['native_custody_clearance'])
write(A / 'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json', grant)
print(json.dumps(dict(status='ACTUAL_HELD_RESOURCE_PACKET_PENDING_INDEPENDENT_EXECUTION_REVIEW', packet=reference(A / 'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json'), observed_clocks=clocks, nonce=ready['nonce'], runtime_authority=False)))
