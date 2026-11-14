#!/usr/bin/env python3
"""Compile controlled native fault-dispatch tests in the pinned native container."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys

assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
repo = Path('/workspace')
out = Path('/work/native-fault-protocol-20260909-' + sys.argv[1])
out.mkdir()
record = dict(status='RUNNING', commands=[], inputs=[],
              started_utc=datetime.now(timezone.utc).isoformat(),
              scope='Controlled exact-PC dispatcher and ordinary valid load; no actual McKernel trap delivery credit',
              actual_guest_fault_recovery_verified=False)


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())


def run(label, command):
    print('RUN', label, flush=True)
    (out / 'phase').write_text(label + '\n')
    with (out / (label + '.log')).open('wb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=90)
    record['commands'].append(dict(label=label, command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, (out / (label + '.log')).read_text()[-8000:])


try:
    shutil.copyfile(__file__, out / 'helper.py')
    for name in ['kernel/rust/abi.rs', 'kernel/rust/native_fault.rs',
                 'arch/x86_64/kernel/interrupt.S', 'kernel/CMakeLists.txt',
                 'kernel/rust/lib.rs', 'scripts/tests/fixtures/native-fault.rs']:
        saved = out / 'original-inputs' / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, saved)
        record['inputs'].append(identity(saved))
    for name in ['abi.rs', 'native_fault.rs']:
        shutil.copyfile(out / 'original-inputs/kernel/rust' / name, out / name)
    shutil.copyfile(out / 'original-inputs/scripts/tests/fixtures/native-fault.rs', out / 'test.rs')
    run('format', ['rustfmt', '--edition', '2021', '--config', 'skip_children=true,reorder_modules=false',
                   str(out / 'native_fault.rs'), str(out / 'test.rs')])
    run('compiler', ['rustc', '--version', '--verbose'])
    run('build', ['rustc', '--edition', '2021', '-D', 'warnings', '--test', str(out / 'test.rs'),
                  '-o', str(out / 'native-fault-tests')])
    run('tests', [str(out / 'native-fault-tests'), '--nocapture'])
    run('disassembly', ['objdump', '-d', str(out / 'native-fault-tests')])
    record['compiler_inputs'] = [identity(out / name) for name in ['abi.rs', 'native_fault.rs', 'test.rs']]
    record['status'] = 'PASS'
except BaseException as error:
    record.update(status='FAIL', error=str(error))
    raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    record['outputs'] = [identity(p) for p in sorted(out.iterdir()) if p.is_file() and p.name not in ('record.json', 'phase')]
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(record['status'], out, flush=True)
