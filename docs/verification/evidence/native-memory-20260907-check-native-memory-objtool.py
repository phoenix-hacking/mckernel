"""Exercise actual objtool on the emitted Rust object and unknown-callee mutations."""
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
review = Path('/work/native-memory-objtool-review-20260907')
out = Path('/work/native-memory-objtool-checks-20260907')
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
out.mkdir()
objtool = build / 'tools/objtool/objtool'
shutil.copyfile(objtool, out / 'objtool-before')
(out / 'objtool-before').chmod(0o755)
shutil.copyfile(source / 'tools/objtool/check.c', out / 'check-before.c')
shutil.copyfile(Path(__file__), out / 'check-helper.py')
patch = repo / 'host-kernel/rocky/patches/0024-objtool-recognize-rust-1.92-sort-and-vec-panics.patch'
shutil.copyfile(patch, out / patch.name)
symbols = (review / 'undefined.raw').read_text().splitlines()
panics = [line.split()[-1] for line in symbols if
          'panic_on_ord_violation' in line or 'E6remove13assert_failed' in line]
if len(panics) != 2:
    raise SystemExit('Expected two observed panic symbols')
saved = (build / 'drivers/misc/mckernel/.ihk-smp-x86_64.o.cmd').read_text().splitlines()[0]
arguments = shlex.split(saved.split(';', 1)[1])
if arguments[0] != './tools/objtool/objtool':
    raise SystemExit('Unexpected Kbuild objtool invocation')
flags = arguments[1:-1]
results = []

def check(label, tool, renamed, expected_failures):
    raw = out / (label + '.raw.o')
    shutil.copyfile(review / 'ihk_smp_x86_64.o', raw)
    for name in renamed:
        subprocess.run(['llvm-objcopy', '--redefine-sym', name + '=' + name + '_unknown_callee', str(raw)], check=True)
    linked = out / (label + '.o')
    subprocess.run(['ld.lld', '-m', 'elf_x86_64', '-z', 'noexecstack', '-r', '-o', str(linked), str(raw)], check=True)
    before = hashlib.sha256(linked.read_bytes()).hexdigest()
    command = [str(tool)] + flags + [str(linked)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (out / (label + '.log')).write_text(result.stdout)
    failures = result.stdout.count('falls through to next function')
    record = dict(label=label, command=command, input_sha256=before, returncode=result.returncode,
                  expected_failures=expected_failures, observed_failures=failures,
                  output_sha256=hashlib.sha256(linked.read_bytes()).hexdigest())
    results.append(record)
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    if failures != expected_failures or (result.returncode != 0) != (expected_failures != 0):
        raise SystemExit('Unexpected objtool result for ' + label + ': ' + result.stdout)

check('before', out / 'objtool-before', [], 5)
subprocess.run(['patch', '-d', str(source), '-p1', '--batch', '--forward', '--fuzz=0',
                '--no-backup-if-mismatch', '-i', str(patch)], check=True)
base = shlex.split(Path('/work/native-memory-prototype-20260907/module-build.command').read_text())[:-3]
subprocess.run(base + ['tools/objtool'], check=True)
shutil.copyfile(objtool, out / 'objtool-after')
(out / 'objtool-after').chmod(0o755)
shutil.copyfile(source / 'tools/objtool/check.c', out / 'check-after.c')
check('after', out / 'objtool-after', [], 0)
for index, name in enumerate(panics):
    expected = 4 if 'panic_on_ord_violation' in name else 1
    check('unknown-' + str(index), out / 'objtool-after', [name], expected)
check('unknown-both', out / 'objtool-after', panics, 5)
print('NATIVE_MEMORY_OBJTOOL_POSITIVE_AND_UNKNOWN_CALLEE_NEGATIVES_PASS')
