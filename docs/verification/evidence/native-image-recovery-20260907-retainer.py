"""Retain the recovered source-bound image-load checkpoint without replacing evidence."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

repo = Path('/home/holden/mckernel')
work = Path('/home/holden/mckernel-work')
scratch = work / 'scratch'
verification = repo / 'docs/verification'
evidence = verification / 'evidence'
compiled = scratch / 'native-image-loader-prototype-20260907-2'
recovery = scratch / 'recovery-cJDpVLRT'
guest = scratch / 'native-image-loader-guest-recovery-20260907-1'
checkpoint = verification / 'native-image-loader-checkpoint-20260907.json'
prefix = 'native-image-recovery-20260907-'
rows = []


def digest(data):
    return hashlib.sha256(data).hexdigest()


def keep(name, data, compressed=True):
    payload = gzip.compress(data, mtime=0) if compressed else data
    target = evidence / (prefix + name)
    with target.open('xb') as output:
        output.write(payload)
    rows.append(dict(path=str(target.relative_to(repo)), size=len(payload),
                     sha256=digest(payload), encoding='gzip' if compressed else 'identity',
                     source_size=len(data), source_sha256=digest(data)))


def retain(name, path, compressed=True):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('Expected a regular retained input: ' + str(path))
    keep(name, path.read_bytes(), compressed)


def archive(name, entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as output:
        for relative, path in sorted(entries):
            if path.is_symlink() or not path.is_file():
                raise RuntimeError('Invalid archive input: ' + str(path))
            data = path.read_bytes()
            item = tarfile.TarInfo(relative)
            item.size, item.mode, item.mtime = len(data), 0o644, 0
            output.addfile(item, io.BytesIO(data))
    keep(name, buffer.getvalue())


if checkpoint.exists():
    raise RuntimeError('Refuse to replace an existing checkpoint')
build_record = json.loads((compiled / 'record.json').read_text())
guest_record = json.loads((guest / 'local-run.json').read_text())
module_record = json.loads((recovery / 'native-image-loader-module-checks.json').read_text())
assert build_record['status'] == module_record['status'] == 'PASS'
assert guest_record['status'] == 'technical-capture-passed'
assert guest_record['qemu_exit_code'] == 0
assert not guest_record['missing_markers'] and not guest_record['error_markers']
assert guest_record['image_loading_proven'] and len(guest_record['physical_image_readbacks']) == 24
assert not guest_record['mckernel_boot_proven'] and not guest_record['staging_lock_refreshed']
assert (recovery / 'result.txt').read_text() == 'stage=preflight-complete\nexit_code=0\n'
for item in build_record['overlay'] + build_record['outputs']:
    original = item['path']
    path = Path(original.replace('/workspace/', str(repo) + '/').replace('/work/', str(scratch) + '/'))
    data = path.read_bytes()
    assert len(data) == item['size'] and digest(data) == item['sha256'], original

for name in ('native-isolation.log', 'compat-isolation.log', 'native-image-tests.log',
             'result.txt', 'native-image-loader-module-checks.json', 'native-module-checks.log',
             'check-native-image-loader-modules.py', 'continue-image-verification.py'):
    retain('preflight-' + name + '.gz', recovery / name)
first = scratch / 'native-image-loader-prototype-20260907'
for name in ('record.json', 'module-build.log', 'build-helper.py'):
    retain('first-build-failure-' + name + '.gz', first / name)
for name in ('record.json', 'module-build.log', 'module-build.command', 'build-helper.py',
             'ihk-defined-symbols.txt', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko', 'bzImage'):
    retain('build-' + name + '.gz', compiled / name)
entries = [(str(path.relative_to(compiled)), path)
           for path in (compiled / 'staged-source').rglob('*') if path.is_file()]
entries += [(str(path.relative_to(compiled)), path)
            for path in (compiled / 'module-build').iterdir()
            if path.name.endswith(('.cmd', '.mod', '.mod.c'))]
entries += [(name, compiled / name) for name in
            ('Module.symvers', 'bindings_generated.rs', '.config', 'resolved.config')]
archive('build-source-compiler.tar.gz', entries)

interrupted = scratch / 'native-image-loader-guest-20260907'
for name in ('local-run.json', 'serial.log', 'qemu.log', 'run-helper.py'):
    retain('interrupted-guest-' + name + '.gz', interrupted / name)
for name in ('local-run.json', 'serial.log', 'qemu.log', 'probe-build.log', 'run-helper.py',
             'image-model.json', 'initramfs.list'):
    retain('guest-' + name + '.gz', guest / name)
retain('guest-initramfs.cpio.gz', guest / 'initramfs.cpio.gz', compressed=False)
entries = [(str(path.relative_to(guest)), path)
           for path in (guest / 'probe-source').rglob('*') if path.is_file()]
entries += [(name, guest / name) for name in
            ('root/init', 'root/bin/native-memory-x86_64', 'root/bin/native-memory-i386',
             'root/bin/mcd0-ioctl-x86_64', 'root/bin/mcd0-ioctl-i386')]
archive('guest-probes.tar.gz', entries)
retain('mckernel.img.gz', guest / 'root/images/mckernel.img')
archive('local-setup-recipes.tar.gz', [(name, work / name) for name in
        ('README.md', 'env.sh', 'setup-status.json', 'setup/setup-host.sh',
         'setup/container-run.py', 'setup/check-isolation.py', 'setup/install-rust.sh',
         'setup/install-rocky-builders.sh', 'setup/docker/Dockerfile.native',
         'setup/docker/Dockerfile.compat', 'bin/mckernel-container', 'bin/mckernel-limited')])

record = dict(
    schema_version=1, kind='native-image-loader-recovery-prototype',
    recorded_utc=datetime.now(timezone.utc).isoformat(),
    source_commit=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
    original_build_parent=build_record['source_parent'],
    scope='Recovered source-bound image loader and isolated four-vCPU/two-NUMA guest; declared staging pending',
    production_gate_credit=False, full_repository_suite_run=False,
    native_mckernel_boot_proven=False, complete_rust_unification_claimed=False,
    environment_restored=True, pinned_native_and_compat_isolation_passed=True,
    focused_native_python_tests=3, cpu_hotplug_failure_state_from_exact_bindings=234,
    compiled_overlay=build_record['overlay'], build_outputs=build_record['outputs'],
    physical_image_readbacks=guest_record['physical_image_readbacks'],
    guest={key: guest_record[key] for key in
           ('status', 'started_utc', 'finished_utc', 'cpus', 'numa_nodes', 'memory_mib',
            'container_memory_mib', 'qemu_exit_code', 'missing_markers', 'error_markers',
            'cpu_assignment_proven', 'memory_assignment_proven', 'image_loading_proven',
            'staging_lock_refreshed')},
    artifacts=rows,
    remaining=['Declared staging, lifecycle and unsafe/FFI integration and verification identity updates',
               'Fresh declared-stage module build, guest replay and repository suite',
               'Native McKernel AP startup, IKC and native mcctrl workloads',
               'McKernel Rust/assembly-only completion and production acceptance'])
with checkpoint.open('x') as output:
    output.write(json.dumps(record, indent=2, sort_keys=True) + '\n')
for row in rows:
    payload = (repo / row['path']).read_bytes()
    assert len(payload) == row['size'] and digest(payload) == row['sha256']
    original = gzip.decompress(payload) if row['encoding'] == 'gzip' else payload
    assert len(original) == row['source_size'] and digest(original) == row['source_sha256']
print('Retained and round-trip verified', len(rows), 'recovery artifacts.')
