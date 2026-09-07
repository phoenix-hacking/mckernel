#!/usr/bin/env python3
"""Reuse the existing memory/XPMEM equivalence cases without absent IHK crates.

The full historical harness also requires Rust sources absent from the pinned
IHK checkout. This bounded runner selects its exact fixtures and build commands;
it reports only memory/XPMEM equivalence, never full-harness completion.
"""

import argparse
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path


def fixture_block(source, name):
    pattern = r'^cat > "\$\{tmpdir\}/' + re.escape(name) + r'" <<\x27([^\x27]+)\x27\n'
    matches = list(re.finditer(pattern, source, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError('expected one existing fixture: ' + name)
    match = matches[0]
    end = source.index('\n' + match.group(1) + '\n', match.end())
    return source[match.start():end + len(match.group(1)) + 2]


def compiler_commands(source):
    commands = []
    lines = iter(source.splitlines(True))
    for line in lines:
        if not line.startswith('cc '):
            continue
        command = line
        while line.rstrip().endswith('\\'):
            line = next(lines)
            command += line
        commands.append(command)
    return commands


def output_command(commands, name):
    suffix = '-o "${tmpdir}/out/' + name + '"'
    matches = [command for command in commands if suffix in command]
    if len(matches) != 1:
        raise ValueError('expected one existing compiler command: ' + name)
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output_dir.resolve()
    output.mkdir()
    harness = repo / 'kernel/rust/tests/run_equivalence.sh'
    source = harness.read_text()
    commands = compiler_commands(source)
    pieces = ['#!/bin/bash\nset -euo pipefail\n',
              'cd ' + shlex.quote(str(repo)) + '\n',
              'tmpdir=' + shlex.quote(str(output)) + '\n']
    for name in ('mem_init_helpers_equiv.c', 'xpmem_helpers_equiv.c',
                 'pte_helpers_equiv.c', 'rust_stubs.c', 'config.h'):
        pieces.append(fixture_block(source, name))
    pieces.append('mkdir "${tmpdir}/out"\n')
    start = source.index('\ninc=(\n')
    end = source.index('\ncc ', start)
    pieces.append(source[start:end] + '\n')
    for name in ('rbtree_c.o', 'list_c.o', 'mem_c.o', 'init_c.o',
                 'string_c.o', 'pte_helpers_fallback_c.o', 'xpmem_helpers_c.o'):
        pieces.append(output_command(commands, name))
    start = source.index('MCKERNEL_RUST_VERSION=equiv-version \\\n')
    last = 'objcopy --weaken-symbol=main "${tmpdir}/out/mckernel_rust.o"'
    end = source.index(last, start) + len(last)
    pieces.append(source[start:end] + '\n')
    for family in ('mem_init_helpers', 'xpmem_helpers'):
        for language in ('c', 'rust'):
            name = family + '_' + language
            pieces.append(output_command(commands, name))
            pieces.append('"${tmpdir}/out/' + name + '" > "${tmpdir}/out/' + name + '.out"\n')
        pieces.append('diff -u "${tmpdir}/out/' + family + '_c.out" '
                      '"${tmpdir}/out/' + family + '_rust.out"\n')
        pieces.append('cat "${tmpdir}/out/' + family + '_rust.out"\n')
    pieces.append('echo MEMORY_XPMEM_EQUIVALENCE_PASS\n')
    script = '\n'.join(pieces)
    selected = output / 'selected-existing-cases.sh'
    selected.write_text(script)
    manifest = dict(scope='existing memory and XPMEM cases only',
                    source_harness=str(harness),
                    source_harness_sha256=hashlib.sha256(source.encode()).hexdigest(),
                    selected_script_sha256=hashlib.sha256(script.encode()).hexdigest(),
                    full_harness_pass=False)
    (output / 'selection.json').write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run(['bash', '-n', str(selected)], check=True)
    subprocess.run(['bash', str(selected)], check=True)


if __name__ == '__main__':
    main()
