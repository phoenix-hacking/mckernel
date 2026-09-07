"""Check retained bytes and native module architecture without running host code."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

repo = Path('/workspace')
root = repo / 'docs/verification'
out = Path('/work/native-memory-checkpoint-checks-20260907.json')
if os.getuid() != 1000 or os.sched_getaffinity(0) != {2, 3, 4, 5}:
    raise SystemExit('Use the fixed unprivileged four-CPU runner')
subprocess.run(['git', '-C', str(repo), 'diff', '--check'], check=True)
subprocess.run(['rustfmt', '--check', '--edition', '2021', '--config', 'skip_children=true',
                str(repo / 'host-kernel/native-rust/smp_memory.rs')], check=True)
for relative in ('host-kernel/native-rust/smp_memory.rs',
                 'scripts/tests/fixtures/native-memory-reservation.c',
                 'scripts/native-memory-reservation-init.sh'):
    text = (repo / relative).read_text()
    if not text.endswith('\n') or any(line != line.rstrip() for line in text.splitlines()):
        raise SystemExit('Source whitespace violation: ' + relative)
checkpoint = json.loads((root / 'native-memory-checkpoint-20260907.json').read_text())
for row in checkpoint['artifacts']:
    path = (root / row['path']).resolve()
    if root not in path.parents:
        raise SystemExit('Artifact escapes evidence directory')
    data = path.read_bytes()
    if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise SystemExit('Retained artifact identity differs: ' + str(path))
    plain = gzip.decompress(data) if path.name.endswith(('.gz', '.tar.gz')) else data
    if len(plain) != row['uncompressed_size'] or hashlib.sha256(plain).hexdigest() != row['uncompressed_sha256']:
        raise SystemExit('Uncompressed artifact identity differs: ' + str(path))
modules = []
for row in checkpoint['built_artifacts']:
    path = Path(row['path'])
    data = path.read_bytes()
    if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise SystemExit('Built artifact identity differs: ' + str(path))
    if path.suffix != '.ko':
        continue
    header = subprocess.check_output(['llvm-readelf', '-h', str(path)], text=True)
    if 'ELF64' not in header or 'Advanced Micro Devices X86-64' not in header:
        raise SystemExit('Unexpected native module architecture')
    assembly = subprocess.check_output(['llvm-objdump', '-d', '--no-show-raw-insn', str(path)], text=True)
    instructions = []
    for line in assembly.splitlines():
        match = re.match(r'^\s*[0-9a-f]+:\s+(.+)$', line)
        if match:
            instructions.append(match.group(1))
    unexpected = []
    for instruction in instructions:
        mnemonic = instruction.split()[0]
        if (re.search(r'%(?:[xyz]mm[0-9]+|mm[0-7])\b', instruction)
                or mnemonic.startswith(('f', 'xsave', 'xrstor'))
                or mnemonic in ('vzeroupper', 'vzeroall', 'emms', 'ldmxcsr', 'stmxcsr')):
            unexpected.append(instruction)
    if unexpected:
        raise SystemExit('Unexpected SIMD/x87 instructions: ' + repr(unexpected[:10]))
    modules.append(dict(path=str(path), sha256=row['sha256'], architecture='ELF64 x86-64',
                        instruction_count=len(instructions), simd_x87_instructions=unexpected))
result = dict(status='passed', artifact_count=len(checkpoint['artifacts']), modules=modules,
              formatting='new memory adapter passes rustfmt; tracked diff/new source whitespace clean',
              full_repository_suite_run=False, production_gate_credit=False)
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
