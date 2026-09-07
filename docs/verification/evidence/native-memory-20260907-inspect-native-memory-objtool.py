"""Retain exact standard-library source and the rejected object's relocations."""
import os
from pathlib import Path
import shutil
import subprocess

if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
out = Path('/work/native-memory-objtool-review-20260907')
out.mkdir()
obj = Path('/work/native-build-base-24a151fe/drivers/misc/mckernel/ihk_smp_x86_64.o')
shutil.copyfile(obj, out / obj.name)
for args, name in ((['llvm-nm', '-u', str(obj)], 'undefined.raw'),
                   (['llvm-objdump', '-dr', '--no-show-raw-insn', str(obj)], 'object.disassembly'),
                   (['rustc', '--version', '--verbose'], 'rustc-version.txt')):
    with (out / name).open('wb') as stream:
        subprocess.run(args, stdout=stream, check=True)
root = Path(subprocess.check_output(['rustc', '--print', 'sysroot'], text=True).strip())
library = root / 'lib/rustlib/src/rust/library'
for relative, name in (('core/src/slice/sort/shared/smallsort.rs', 'smallsort.rs'),
                        ('alloc/src/vec/mod.rs', 'vec-mod.rs')):
    shutil.copyfile(library / relative, out / name)
print((out / 'undefined.raw').read_text())
print('Retained object, relocations and exact Rust library sources:', out)
