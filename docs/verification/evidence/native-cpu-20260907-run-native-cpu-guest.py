"""Capture real CPU adapter behavior in a disposable four-vCPU TCG guest."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

repo = Path('/workspace')
build = Path('/work/native-build-base-24a151fe')
source = Path('/work/native-source/linux-6.12.0-211.44.1.el10_2')
base = Path('/work/native-runtime-cpu-adapter-20260907')
prior = Path('/work/native-runtime-local-base-24a151fe')
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
if Path('/work/native-cpu-adapter-prototype/build.phase').read_text().strip() != 'complete':
    raise SystemExit('Native adapter build is incomplete')
base.mkdir()
shutil.copytree(prior / 'root', base / 'root')
shutil.copyfile(repo / 'scripts/native-cpu-reservation-init.sh', base / 'root/init')
(base / 'root/init').chmod(0o755)
for name in ('ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko'):
    shutil.copyfile(build / 'drivers/misc/mckernel' / name, base / 'root/modules' / name)
bindings = (build / 'rust/bindings/bindings_generated.rs').read_text()
states = re.findall(r'pub const cpuhp_state_CPUHP_AP_ACTIVE: cpuhp_state = ([0-9]+);', bindings)
if len(states) != 1:
    raise SystemExit('No unique actual Linux CPUHP_AP_ACTIVE binding')
for bits, name in ((64, 'x86_64'), (32, 'i386')):
    command = ['cc', '-m' + str(bits), '-O2', '-Wall', '-Wextra', '-Werror',
               '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-fno-pie',
               '-nostdlib', '-static', '-no-pie', '-Wl,-e,_start', '-Wl,-z,noexecstack',
               '-DCPUHP_FAILURE_STATE=' + states[0],
               str(repo / 'scripts/tests/fixtures/native-cpu-reservation.c'),
               '-o', str(base / 'root/bin' / ('native-cpu-' + name))]
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

def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), size=len(data))

args = ['/usr/libexec/qemu-kvm', '-machine', 'q35', '-accel', 'tcg,thread=multi',
        '-cpu', 'max,la57=off', '-smp', '4', '-m', '8192',
        '-kernel', str(build / 'arch/x86/boot/bzImage'),
        '-initrd', str(base / 'initramfs.cpio.gz'),
        '-append', 'console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1',
        '-display', 'none', '-monitor', 'none', '-serial', 'file:' + str(base / 'serial.log'),
        '-no-reboot', '-nic', 'none']
inputs = [build / 'arch/x86/boot/bzImage', build / '.config', build / 'Module.symvers',
          source / 'drivers/base/core.c', Path(__file__), base / 'initramfs.cpio.gz']
inputs += [path for path in sorted((source / 'drivers/misc/mckernel').rglob('*')) if path.is_file()]
record = dict(kind='native-cpu-adapter-prototype', qemu_args=args,
              started_utc=datetime.now(timezone.utc).isoformat(), status='running',
              cpus=4, cpuset=sorted(os.sched_getaffinity(0)), memory_mib=8192,
              container_memory_mib=12288, network='none', acceleration='TCG',
              source_parent=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
              source_diff_sha256=hashlib.sha256(subprocess.check_output(['git', '-C', str(repo), 'diff', 'HEAD'])).hexdigest(),
              inputs=[identity(path) for path in inputs],
              initramfs_files=[identity(path) for path in sorted((base / 'root').rglob('*')) if path.is_file()],
              staging_lock_refreshed=False, production_gate_credit=False,
              memory_assignment_proven=False, mckernel_boot_proven=False)

def save():
    (base / 'local-run.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')

save()
with (base / 'qemu.log').open('wb') as output:
    result = subprocess.run(['/usr/bin/timeout', '--signal=TERM', '--kill-after=30s', '1200'] + args,
                            stdout=output, stderr=subprocess.STDOUT)
record.update(qemu_exit_code=result.returncode, finished_utc=datetime.now(timezone.utc).isoformat())
serial = (base / 'serial.log').read_text(errors='replace')
expected = ['NATIVE_CPU_GUEST CYCLE=' + str(cycle) + ' restored=0-3 unloaded=all PASS'
            for cycle in (1, 2)] + ['NATIVE_CPU_GUEST COMPLETE PASS']
for architecture in ('x86_64', 'i386'):
    for check in ('reserve-rollback=3', 'online-veto-and-closed-file-pin',
                  'release-rollback=3', 'concurrent=3x8', 'COMPLETE'):
        marker = 'NATIVE_CPU_RESERVATION ' + architecture + ' ' + check + ' PASS'
        if serial.count(marker) != 2:
            expected.append('MISSING_EXPECTED_DOUBLE_MARKER:' + marker)
errors = [pattern for pattern in ('NATIVE_CPU_GUEST FAIL', ' FAIL line=', 'BUG:',
          'WARNING:', 'Kernel panic', 'Oops:', 'scheduling while atomic') if pattern in serial]
record['missing_markers'] = [marker for marker in expected if marker not in serial]
record['error_markers'] = errors
record['status'] = 'technical-capture-passed' if result.returncode == 0 and not errors and not record['missing_markers'] else 'failed'
record['outputs'] = [identity(base / name) for name in ('serial.log', 'qemu.log')]
save()
print(json.dumps({key: record[key] for key in ('status', 'qemu_exit_code', 'missing_markers', 'error_markers')}))
raise SystemExit(0 if record['status'] == 'technical-capture-passed' else 1)
