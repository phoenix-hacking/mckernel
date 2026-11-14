"""Capture memory ownership and CPU regressions in the bounded offline guest."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

repo = Path('/workspace')
build = Path('/work/native-build-base-24a151fe')
source = Path('/work/native-source/linux-6.12.0-211.44.1.el10_2')
if len(sys.argv) != 3:
    raise SystemExit('Usage: run-native-memory-guest.py BUILD_EVIDENCE NEW_CAPTURE_DIRECTORY')
compiled, base = (Path(arg).resolve() for arg in sys.argv[1:])
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
if not str(compiled).startswith('/work/') or not str(base).startswith('/work/'):
    raise SystemExit('Use the dedicated scratch filesystem')
if (compiled / 'build.phase').read_text().strip() != 'prototype-build-complete':
    raise SystemExit('Native memory module build is incomplete')
config = (compiled / 'resolved.config').read_text()
for name in ('FAULT_INJECTION', 'FAIL_PAGE_ALLOC', 'FAULT_INJECTION_DEBUG_FS'):
    if 'CONFIG_' + name + '=y\n' not in config:
        raise SystemExit('Missing actual fault-injection configuration: ' + name)

def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), size=len(data))

base.mkdir()
shutil.copytree(Path('/work/native-runtime-local-base-24a151fe/root'), base / 'root')
shutil.copyfile(repo / 'scripts/native-memory-reservation-init.sh', base / 'root/init')
(base / 'root/init').chmod(0o755)
subprocess.run(['bash', '-n', str(base / 'root/init')], check=True)
for name in ('ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko'):
    shutil.copyfile(compiled / name, base / 'root/modules' / name)
(base / 'probe-source').mkdir()
for name in ('native-memory-reservation.c', 'native-cpu-reservation.c'):
    shutil.copyfile(repo / 'scripts/tests/fixtures' / name, base / 'probe-source' / name)
for architecture in ('x86_64', 'i386'):
    name = 'native-rust-runtime-mcd0-ioctl-' + architecture + '.S'
    shutil.copyfile(repo / 'scripts' / name, base / 'probe-source' / name)
bindings_path = compiled / 'bindings_generated.rs'
bindings = bindings_path.read_text()
states = re.findall(r'pub const cpuhp_state_CPUHP_AP_ACTIVE: cpuhp_state = ([0-9]+);', bindings)
if len(states) != 1:
    raise SystemExit('No unique actual CPUHP_AP_ACTIVE binding')
probe_commands = []
for bits, name in ((64, 'x86_64'), (32, 'i386')):
    reference_command = ['cc', '-m' + str(bits), '-nostdlib', '-static', '-no-pie',
                         '-Wl,-e,_start', '-Wl,-z,noexecstack',
                         str(base / 'probe-source' / ('native-rust-runtime-mcd0-ioctl-' + name + '.S')),
                         '-o', str(base / 'root/bin' / ('mcd0-ioctl-' + name))]
    probe_commands.append(reference_command)
    subprocess.run(reference_command, check=True)
    command = ['cc', '-m' + str(bits), '-O2', '-Wall', '-Wextra', '-Werror',
               '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-fno-pie',
               '-nostdlib', '-static', '-no-pie', '-Wl,-e,_start', '-Wl,-z,noexecstack',
               '-DCPUHP_FAILURE_STATE=' + states[0],
               str(base / 'probe-source/native-memory-reservation.c'),
               '-o', str(base / 'root/bin' / ('native-memory-' + name))]
    probe_commands.append(command)
    subprocess.run(command, check=True)
environment = dict(os.environ, RUNTIME_EVIDENCE=str(base), INITRAMFS_ROOT=str(base / 'root'))
subprocess.run(['python3', '/work/write-native-cpio-spec.py'], env=environment, check=True)
with (base / 'initramfs.cpio.gz').open('wb') as raw:
    with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as output:
        process = subprocess.Popen(['/work/native-runtime-24a151fe/gen_init_cpio',
                                    '-t', '0', str(base / 'initramfs.list')], stdout=subprocess.PIPE)
        shutil.copyfileobj(process.stdout, output)
        process.stdout.close()
        if process.wait() != 0:
            raise SystemExit('Initramfs generation failed')

args = ['/usr/libexec/qemu-kvm', '-machine', 'q35', '-accel', 'tcg,thread=multi',
        '-cpu', 'max,la57=off', '-smp', '4,sockets=2,cores=2,threads=1', '-m', '8192',
        '-object', 'memory-backend-ram,size=4G,id=ram-node0',
        '-object', 'memory-backend-ram,size=4G,id=ram-node1',
        '-numa', 'node,nodeid=0,cpus=0-1,memdev=ram-node0',
        '-numa', 'node,nodeid=1,cpus=2-3,memdev=ram-node1',
        '-kernel', str(compiled / 'bzImage'), '-initrd', str(base / 'initramfs.cpio.gz'),
        '-append', 'console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1',
        '-display', 'none', '-monitor', 'none', '-serial', 'file:' + str(base / 'serial.log'),
        '-no-reboot', '-nic', 'none']
inputs = [Path(__file__), base / 'initramfs.cpio.gz',
          Path('/work/write-native-cpio-spec.py'), Path('/work/native-runtime-24a151fe/gen_init_cpio'),
          Path('/usr/bin/cc').resolve()]
inputs += [path for path in sorted(compiled.rglob('*')) if path.is_file()]
inputs += [path for path in sorted((base / 'probe-source').rglob('*')) if path.is_file()]
record = dict(kind='native-memory-prototype-two-numa-nodes', qemu_args=args,
              started_utc=datetime.now(timezone.utc).isoformat(), status='running',
              cpus=4, cpuset=sorted(os.sched_getaffinity(0)), memory_mib=8192,
              container_memory_mib=12288, network='none', acceleration='TCG',
              source_parent=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
              inputs=[identity(path) for path in inputs], probe_compile_commands=probe_commands,
              compiler_version=subprocess.check_output(['cc', '--version'], text=True),
              initramfs_files=[identity(path) for path in sorted((base / 'root').rglob('*')) if path.is_file()],
              staging_lock_refreshed=False, numa_nodes=2, production_gate_credit=False,
              memory_reservation_proven=False, memory_assignment_proven=False, mckernel_boot_proven=False)

def save():
    (base / 'local-run.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')

save()
with (base / 'qemu.log').open('wb') as output:
    result = subprocess.run(['/usr/bin/timeout', '--signal=TERM', '--kill-after=30s', '1200'] + args,
                            stdout=output, stderr=subprocess.STDOUT)
record.update(qemu_exit_code=result.returncode, finished_utc=datetime.now(timezone.utc).isoformat())
serial = (base / 'serial.log').read_text(errors='replace')
expected = ['NATIVE_MEMORY_GUEST CYCLE=' + str(cycle) + ' restored=0-3 unloaded=all PASS'
            for cycle in (1, 2)] + ['NATIVE_MEMORY_GUEST COMPLETE PASS',
                                   'NATIVE_MEMORY_GUEST NUMA nodes=0-1 cpu-map=0-1/2-3 PASS']
missing = [marker for marker in expected if serial.count(marker) != 1]
for architecture in ('x86_64', 'i386'):
    for category, checks in (
        ('CPU', ('reserve-rollback=3', 'online-veto-and-closed-file-pin',
                 'release-rollback=3', 'concurrent=3x8', 'COMPLETE')),
        ('MEMORY', ('malformed-copyfaults', 'numa-query-closed-file-pin',
                    'unbooted-os-preserves-pool',
                    'release-preflight-partial-rounding', 'allocation-rollback=8x3-no-leak',
                    'allocation-order-fallback', 'bounded-all-request', 'concurrent=3x8', 'COMPLETE'))):
        for check in checks:
            marker = 'NATIVE_' + category + '_RESERVATION ' + architecture + ' ' + check + ' PASS'
            if serial.count(marker) != 2:
                missing.append('Expected exactly twice: ' + marker)
errors = [pattern for pattern in ('NATIVE_MEMORY_GUEST FAIL', 'NATIVE_MEMORY_RESERVATION ' + 'x86_64 FAIL',
          'NATIVE_MEMORY_RESERVATION i386 FAIL', ' FAIL line=', 'BUG:', 'WARNING:',
          'Kernel panic', 'Oops:', 'scheduling while atomic') if pattern in serial]
record['missing_markers'] = missing
record['error_markers'] = errors
passed = result.returncode == 0 and not errors and not missing
record['status'] = 'technical-capture-passed' if passed else 'failed'
record['memory_reservation_proven'] = passed
record['outputs'] = [identity(base / name) for name in ('serial.log', 'qemu.log')]
save()
print(json.dumps({key: record[key] for key in ('status', 'qemu_exit_code', 'missing_markers', 'error_markers')}))
raise SystemExit(0 if passed else 1)
