"""Retain prototype memory evidence separately from exact-stage acceptance."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

scratch = Path('/work')
repo = Path('/workspace')
out = scratch / 'native-memory-retained-evidence-20260907'
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
out.mkdir()
rows = []

def retain(source, name, compress=False):
    data = source.read_bytes()
    blob = gzip.compress(data, mtime=0) if compress else data
    (out / name).write_bytes(blob)
    rows.append(dict(source_path=str(source), path='evidence/' + name,
                     sha256=hashlib.sha256(blob).hexdigest(), size=len(blob),
                     uncompressed_sha256=hashlib.sha256(data).hexdigest(), uncompressed_size=len(data)))

def archive(root, names, name):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for relative in sorted(names):
            path = root / relative
            if not path.is_file() or path.is_symlink():
                raise SystemExit('Unexpected archive input: ' + str(path))
            data = path.read_bytes()
            info = tarfile.TarInfo(relative)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
    data = stream.getvalue()
    blob = gzip.compress(data, mtime=0)
    (out / name).write_bytes(blob)
    rows.append(dict(source_path=str(root), path='evidence/' + name,
                     sha256=hashlib.sha256(blob).hexdigest(), size=len(blob),
                     uncompressed_sha256=hashlib.sha256(data).hexdigest(), uncompressed_size=len(data)))

guest_source = (scratch / 'run-native-memory-guest.py').read_text()
# The two earlier captures predate the additive OS coexistence probe. Recover
# those exact recipe bytes from the known edit, accepting them only when their
# hash matches the identity recorded before QEMU started. Never rewrite results.
earlier_source = guest_source.replace(
    "for architecture in ('x86_64', 'i386'):\n"
    "    name = 'native-rust-runtime-mcd0-ioctl-' + architecture + '.S'\n"
    "    shutil.copyfile(repo / 'scripts' / name, base / 'probe-source' / name)\n", '')
start = earlier_source.index('    reference_command = ')
end = earlier_source.index('    command = ', start)
earlier_source = earlier_source[:start] + earlier_source[end:]
earlier_source = earlier_source.replace("                    'unbooted-os-preserves-pool',\n", '')
runs = []
for label, directory, expect_pass in (
    ('interleaved', 'native-runtime-memory-prototype-20260907', False),
    ('memory', 'native-runtime-memory-prototype2-20260907', True),
    ('os-coexistence', 'native-runtime-memory-prototype3-20260907', True)):
    base = scratch / directory
    result = json.loads((base / 'local-run.json').read_text())
    if (result['status'] == 'technical-capture-passed') != expect_pass or result['qemu_exit_code'] != 0:
        raise SystemExit('Unexpected capture status: ' + directory)
    if expect_pass and (result['missing_markers'] or result['error_markers']):
        raise SystemExit('Capture reported missing or erroneous evidence')
    if result['staging_lock_refreshed'] or result['production_gate_credit']:
        raise SystemExit('Prototype must not claim exact-stage or production acceptance')
    prefix = 'native-memory-20260907-' + label
    expected_recipe = [row['sha256'] for row in result['inputs']
                       if row['path'] == '/work/run-native-memory-guest.py']
    matching = [candidate for candidate in (guest_source, earlier_source)
                if [hashlib.sha256(candidate.encode()).hexdigest()] == expected_recipe]
    if len(matching) != 1:
        raise SystemExit('Cannot retain the exact recorded run recipe: ' + directory)
    (base / 'run-helper.py').write_text(matching[0])
    retain(base / 'run-helper.py', prefix + '-run-helper.py')
    retain(base / 'local-run.json', prefix + '-runtime.json')
    retain(base / 'serial.log', prefix + '-serial.log.gz', True)
    retain(base / 'qemu.log', prefix + '-qemu.log.gz', True)
    retain(base / 'root/init', prefix + '-init.sh')
    archive(base / 'probe-source', [path.name for path in (base / 'probe-source').iterdir()], prefix + '-probes.tar.gz')
    runs.append(dict(label=label, status=result['status'], cpus=4, numa_nodes=2,
                     staging_lock_refreshed=False, runtime_record='evidence/' + prefix + '-runtime.json'))

compiled = scratch / 'native-memory-prototype-repair2-20260907'
if (compiled / 'build.phase').read_text().strip() != 'prototype-build-complete':
    raise SystemExit('Prototype module build did not finish')
stage = compiled / 'prototype-stage'
for name in ('ihk_smp_x86_64.rs', 'smp_cpu.rs', 'smp_resource.rs', 'smp_memory.rs', 'abi/x86_64.rs'):
    if (stage / name).read_bytes() != (repo / 'host-kernel/native-rust' / name).read_bytes():
        raise SystemExit('Production source changed after verified build: ' + name)
archive(stage, [str(path.relative_to(stage)) for path in stage.rglob('*') if path.is_file()],
        'native-memory-20260907-prototype-source.tar.gz')
names = ['resolved.config', 'Module.symvers', 'kernel.release', 'kernel-build.command',
         'module-build.command', 'build.phase', 'source-inputs.json', 'bindings_generated.rs',
         'memory_hotplug.c', 'show_mem.c', 'objtool-check.c']
names += ['0004-mm-export-memory-hotplug-read-exclusion.patch',
          '0024-objtool-recognize-rust-1.92-sort-and-vec-panics.patch', 'build-helper.py']
names += [str(path.relative_to(compiled)) for path in (compiled / 'module-build').rglob('*')
          if path.name.endswith(('.cmd', '.mod'))]
archive(compiled, names, 'native-memory-20260907-compiler-records.tar.gz')
checks = scratch / 'native-memory-objtool-checks-20260907'
results = json.loads((checks / 'results.json').read_text())
if len(results) != 5 or any(row['observed_failures'] != row['expected_failures'] for row in results):
    raise SystemExit('Objtool controls did not pass')
archive(checks, [path.name for path in checks.iterdir() if path.is_file()],
        'native-memory-20260907-objtool-controls.tar.gz')
review = scratch / 'native-memory-objtool-review-20260907'
retain(review / 'object.disassembly', 'native-memory-20260907-objtool-disassembly.gz', True)
for name in ('rustc-version.txt', 'undefined.raw'):
    retain(review / name, 'native-memory-20260907-' + name)
for filename in ('native-memory-prototype-build-20260907.log',
                 'native-memory-prototype-repair-20260907.log',
                 'native-memory-prototype-repair2-20260907.log',
                 'native-memory-policy-tests-20260907.log',
                 'native-memory-objtool-checks-20260907.log'):
    retain(scratch / filename, 'native-memory-20260907-' + filename + '.gz', True)
for filename in ('build-native-memory-prototype.py', 'repair-native-memory-prototype.py',
                 'run-native-memory-guest.py', 'inspect-native-memory-objtool.py',
                 'check-native-memory-objtool.py', 'retain-native-memory-evidence.py',
                 'run-native-memory-policy-tests.py'):
    retain(scratch / filename, 'native-memory-20260907-' + filename)
policy = scratch / 'native-memory-policy-20260907'
archive(policy, [str(path.relative_to(policy)) for path in policy.rglob('*')
                 if path.is_file() and path.suffix in ('.py', '.rs')],
        'native-memory-20260907-policy-test-source.tar.gz')

def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), size=len(data))

checkpoint = dict(
    schema='mckernel-local-native-memory-prototype-v1', created_utc=datetime.now(timezone.utc).isoformat(),
    source_parent=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
    scope='bounded native CPU/memory reservation and unbooted OS coexistence',
    isolation=dict(cpus=4, cpuset='2-5', container_memory_bytes=12884901888,
                   guest_memory_mib=8192, uid=1000, privileged=False, network='none', acceleration='TCG',
                   image='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94'),
    runs=runs, artifacts=rows,
    built_artifacts=[identity(compiled / name) for name in ('bzImage', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko', 'objtool')],
    rust_library_sources=[identity(review / name) for name in ('smallsort.rs', 'vec-mod.rs')],
    verification=dict(rust_policy_tests=45, python_policy_checks=9, objtool_cases=5,
                       final_capture_allocation_failures=96, final_capture_module_cycles=2,
                       abis=['x86_64', 'i386'], per_node_free_kib_tolerance=8192),
    reuse=dict(shared_abi=identity(stage / 'abi/x86_64.rs'),
               policy='existing MemoryMap/workspace/transactions with additive batch preflight',
               page_owner='adapts existing KmsgPages ownership to exact-node Linux allocation',
               module_pin='existing CPU resource pin',
               fixtures='unchanged CPU C probe and existing OS lifecycle assembly probes'),
    claims=dict(native_memory_reservation_proven=True, native_compat_memory_ioctls_proven=True,
                 bounded_allocation_rollback_proven=True, reserved_pool_survives_unbooted_os_lifecycle=True,
                 cpu_reservation_regressions_pass=True, native_mckernel_boot_proven=False,
                 memory_assignment_proven=False, hpc_workloads_proven=False,
                 staging_lock_refreshed=False, full_external_source_closure_proven=False,
                 current_full_repository_suite_pass=False, production_gate_credit=False))
(out / 'native-memory-checkpoint-20260907.json').write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + '\n')
print('Retained', len(rows), 'artifacts in', out)
