"""Resume module compilation after the preserved debug-kernel build succeeds.

Invoke only after observing termination of the preceding build and recording
its actual first failure. This does not rerun or alter the completed kernel.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit('Usage: repair-native-memory-prototype.py NEW_EVIDENCE_DIRECTORY')
repo = Path('/workspace')
source = Path('/work/native-source/linux-6.12.0-211.44.1.el10_2')
build = Path('/work/native-build-base-24a151fe')
prior = Path('/work/native-memory-prototype-20260907')
evidence = Path(sys.argv[1]).resolve()
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
if not str(evidence).startswith('/work/'):
    raise SystemExit('Use the dedicated scratch filesystem')
if (prior / 'build.phase').read_text().strip() != 'building-modules':
    raise SystemExit('The first build did not reach module compilation')
if (prior / 'resolved.config').read_bytes() != (build / '.config').read_bytes():
    raise SystemExit('Debug-kernel configuration changed since the first build')
evidence.mkdir()
(evidence / 'build.phase').write_text('preserving-inputs\n')
stage = source / 'drivers/misc/mckernel'
shutil.copytree(stage, evidence / 'preceding-stage')
for name in ('ihk_smp_x86_64.rs', 'smp_cpu.rs', 'smp_resource.rs', 'smp_memory.rs'):
    shutil.copyfile(repo / 'host-kernel/native-rust' / name, stage / name)
subprocess.run(['rustfmt', '--edition', '2021', '--config', 'skip_children=true',
                str(stage / 'smp_memory.rs')], check=True)
shutil.copyfile(stage / 'smp_memory.rs', evidence / 'formatted-smp_memory.rs')
shutil.copytree(stage, evidence / 'prototype-stage')
for path, name in ((build / '.config', 'resolved.config'),
                   (build / 'rust/bindings/bindings_generated.rs', 'bindings_generated.rs'),
                   (build / 'arch/x86/boot/bzImage', 'bzImage'),
                   (build / 'include/config/kernel.release', 'kernel.release'),
                   (source / 'mm/memory_hotplug.c', 'memory_hotplug.c'),
                   (source / 'mm/show_mem.c', 'show_mem.c'),
                   (source / 'tools/objtool/check.c', 'objtool-check.c'),
                   (build / 'tools/objtool/objtool', 'objtool'),
                   (prior / 'kernel-build.command', 'kernel-build.command'),
                   (prior / 'module-build.command', 'module-build.command'),
                   (Path(__file__), 'build-helper.py')):
    shutil.copyfile(path, evidence / name)
patch = repo / 'host-kernel/kbuild/patches/0004-mm-export-memory-hotplug-read-exclusion.patch'
shutil.copyfile(patch, evidence / patch.name)
objtool_patch = repo / 'host-kernel/rocky/patches/0024-objtool-recognize-rust-1.92-sort-and-vec-panics.patch'
shutil.copyfile(objtool_patch, evidence / objtool_patch.name)
identities = []
for path in sorted(stage.rglob('*')):
    if path.is_file():
        data = path.read_bytes()
        identities.append(dict(path=str(path.relative_to(stage)),
                               sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
(evidence / 'source-inputs.json').write_text(json.dumps(identities, indent=2) + '\n')
command = shlex.split((evidence / 'module-build.command').read_text())
(evidence / 'build.phase').write_text('building-modules\n')
try:
    subprocess.run(command, check=True)
except BaseException:
    (evidence / 'build.phase').write_text('module-build-failed\n')
    raise
shutil.copyfile(build / 'Module.symvers', evidence / 'Module.symvers')
for name in ('ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko'):
    shutil.copyfile(build / 'drivers/misc/mckernel' / name, evidence / name)
shutil.copytree(build / 'drivers/misc/mckernel', evidence / 'module-build')
(evidence / 'build.phase').write_text('prototype-build-complete\n')
print('NATIVE_MEMORY_PROTOTYPE_KERNEL_AND_MODULE_BUILD_PASS')
