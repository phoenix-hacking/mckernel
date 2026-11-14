"""Refresh source-bound staging and preserve the earlier passing prototype."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess

repo = Path('/workspace')
source = Path('/work/native-source/linux-6.12.0-211.44.1.el10_2')
build = Path('/work/native-build-base-24a151fe')
evidence = Path('/work/native-cpu-exact-stage-20260907')
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
evidence.mkdir()
(evidence / 'build.phase').write_text('preserving-prototype\n')
stage = source / 'drivers/misc/mckernel'
module_root = build / 'drivers/misc/mckernel'
shutil.copytree(module_root, evidence / 'prototype-module-build')
shutil.copytree(stage, evidence / 'prototype-stage')
# Keep the complete tested prototype before moving the obsolete stage aside.
stage.rename(source / 'drivers/misc/mckernel-prototype-20260907')
(evidence / 'build.phase').write_text('staging\n')
for action in ('--stage-for-evidence', '--verify-evidence-stage'):
    subprocess.run(['/usr/bin/python3', str(repo / 'scripts/rocky_rust_staging.py'),
                    '--repo', str(repo), action, str(source)], check=True)
subprocess.run(['patch', '-d', str(source), '-p1', '--batch', '--reverse',
                '--dry-run', '--fuzz=0', '-i', str(repo / 'host-kernel/kbuild/patches/0003-driver-core-export-device-hotplug-transactions.patch')], check=True)
command = shlex.split(Path('/work/native-cpu-adapter-prototype/module-build.command').read_text())
(evidence / 'module-build.command').write_text(shlex.join(command) + '\n')
(evidence / 'build.phase').write_text('building-modules\n')
subprocess.run(command, check=True)
records = ['.ihk-smp-x86_64.ko.cmd', '.ihk-smp-x86_64.mod.cmd',
           '.ihk-smp-x86_64.mod.o.cmd', '.ihk-smp-x86_64.o.cmd',
           '.ihk.ko.cmd', '.ihk.mod.cmd', '.ihk.mod.o.cmd', '.ihk.o.cmd',
           '.ihk_smp_x86_64.o.cmd', '.mcctrl.ko.cmd', '.mcctrl.mod.cmd',
           '.mcctrl.mod.o.cmd', '.mcctrl.o.cmd', 'ihk-smp-x86_64.mod',
           'ihk.mod', 'mcctrl.mod', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko']
for name in records:
    shutil.copyfile(module_root / name, evidence / name)
for src, name in ((stage / 'stage-lock.json', 'stage-lock.json'),
                  (build / '.config', 'resolved.config'),
                  (build / 'arch/x86/boot/bzImage', 'bzImage'),
                  (build / 'Module.symvers', 'Module.symvers'),
                  (build / 'include/config/kernel.release', 'kernel.release')):
    shutil.copyfile(src, evidence / name)
shutil.copytree(stage, evidence / 'staged-source')
(evidence / 'build.phase').write_text('validating-link-closure\n')
for action in ('--output', '--check-output'):
    subprocess.run(['/usr/bin/python3', str(repo / 'scripts/native_rust_kbuild_link_closure.py'),
                    '--records-dir', str(evidence), '--stage-lock', str(evidence / 'stage-lock.json'),
                    action, str(evidence / 'kbuild-link-closure.json')], check=True)
(evidence / 'build.phase').write_text('complete\n')
print('NATIVE_CPU_EXACT_STAGE_BUILD_AND_LINK_COMPLETE')
