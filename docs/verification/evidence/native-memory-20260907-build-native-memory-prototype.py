"""Build the native memory adapter with guest-only allocation fault injection."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

repo = Path('/workspace')
source = Path('/work/native-source/linux-6.12.0-211.44.1.el10_2')
build = Path('/work/native-build-base-24a151fe')
evidence = Path('/work/native-memory-prototype-20260907')
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
evidence.mkdir()
(evidence / 'build.phase').write_text('preserving-cpu-checkpoint\n')
stage = source / 'drivers/misc/mckernel'
shutil.copytree(stage, evidence / 'prior-stage')
shutil.copytree(build / 'drivers/misc/mckernel', evidence / 'prior-module-build')
for path, name in ((build / '.config', 'prior.config'),
                   (build / 'arch/x86/boot/bzImage', 'prior-bzImage'),
                   (build / 'Module.symvers', 'prior-Module.symvers'),
                   (source / 'mm/memory_hotplug.c', 'prior-memory_hotplug.c'),
                   (source / 'mm/show_mem.c', 'prior-show_mem.c')):
    shutil.copyfile(path, evidence / name)
for name in ('ihk_smp_x86_64.rs', 'smp_cpu.rs', 'smp_resource.rs', 'smp_memory.rs'):
    shutil.copyfile(repo / 'host-kernel/native-rust' / name, stage / name)
subprocess.run(['rustfmt', '--edition', '2021', '--config', 'skip_children=true', str(stage / 'smp_memory.rs')], check=True)
shutil.copyfile(stage / 'smp_memory.rs', evidence / 'formatted-smp_memory.rs')
patch = repo / 'host-kernel/kbuild/patches/0004-mm-export-memory-hotplug-read-exclusion.patch'
subprocess.run(['patch', '-d', str(source), '-p1', '--batch', '--forward', '--fuzz=0',
                '--no-backup-if-mismatch', '-i', str(patch)], check=True)
command = shlex.split(Path('/work/native-cpu-exact-stage-20260907/module-build.command').read_text())
targets = command[-3:]
base = command[:-3]
subprocess.run([str(source / 'scripts/config'), '--file', str(build / '.config'),
                '-e', 'FAULT_INJECTION', '-e', 'FAIL_PAGE_ALLOC', '-e', 'FAULT_INJECTION_DEBUG_FS'], check=True)
(evidence / 'build.phase').write_text('configuring-fault-injection\n')
subprocess.run(base + ['olddefconfig'], check=True)
shutil.copyfile(build / '.config', evidence / 'resolved.config')
for symbol in ('FAULT_INJECTION', 'FAIL_PAGE_ALLOC', 'FAULT_INJECTION_DEBUG_FS'):
    if 'CONFIG_' + symbol + '=y\n' not in (build / '.config').read_text():
        raise SystemExit('Missing requested fault injection symbol: ' + symbol)
shutil.copytree(stage, evidence / 'prototype-stage')
identities = []
for name in ('ihk_smp_x86_64.rs', 'smp_cpu.rs', 'smp_resource.rs', 'smp_memory.rs', 'abi/x86_64.rs'):
    data = (stage / name).read_bytes()
    identities.append(dict(path=name, sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
(evidence / 'source-inputs.json').write_text(json.dumps(identities, indent=2) + '\n')
(evidence / 'kernel-build.command').write_text(shlex.join(base + ['bzImage']) + '\n')
(evidence / 'module-build.command').write_text(shlex.join(base + targets) + '\n')
(evidence / 'build.phase').write_text('building-debug-kernel\n')
subprocess.run(base + ['bzImage'], check=True)
(evidence / 'build.phase').write_text('building-modules\n')
subprocess.run(base + targets, check=True)
for path, name in ((build / 'arch/x86/boot/bzImage', 'bzImage'),
                   (build / 'Module.symvers', 'Module.symvers'),
                   (build / 'include/config/kernel.release', 'kernel.release')):
    shutil.copyfile(path, evidence / name)
for name in targets:
    shutil.copyfile(build / name, evidence / Path(name).name)
(evidence / 'build.phase').write_text('prototype-build-complete\n')
print('NATIVE_MEMORY_PROTOTYPE_KERNEL_AND_MODULE_BUILD_PASS')
