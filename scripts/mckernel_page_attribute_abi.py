#!/usr/bin/env python3
"""Run a userspace ABI regression against a built McKernel Rust object.

Only the mapping/permission entry points execute; their hardware effects are
replaced by test callbacks. This is not a kernel boot or live PTE test.
"""

import argparse
import json
import shlex
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    build = args.build_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir()
    source = Path(__file__).resolve().parent / 'tests/fixtures/mckernel-page-attribute-abi.c'
    commands = json.loads((build / 'compile_commands.json').read_text())
    rows = [row for row in commands if row['file'].endswith('/kernel/rust/abi_checks.c')]
    if len(rows) != 1:
        raise ValueError('expected one actual kernel ABI compilation command')
    row = rows[0]
    command = shlex.split(row['command'])
    output_index = command.index('-o') + 1
    source_index = command.index('-c') + 1
    command[output_index] = str(output / 'probe.o')
    command[source_index] = str(source)
    subprocess.run(command, cwd=row['directory'], check=True)
    rust = output / 'mckernel_rust.o'
    shutil.copyfile(build / 'kernel/rust/mckernel_rust.o', rust)
    # Reuse the existing equivalence harness convention: the C probe owns main.
    subprocess.run(['objcopy', '--weaken-symbol=main', str(rust)], check=True)
    executable = output / 'probe'
    subprocess.run(['ld', '-e', '_start', '--gc-sections',
                    str(output / 'probe.o'), str(rust), '-o', str(executable)], check=True)
    return subprocess.run([str(executable)], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
