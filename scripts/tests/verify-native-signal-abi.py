#!/usr/bin/env python3
"""Pinned-container benign native signal protocol and Linux payload reference.

This is a build/reference step, not McKernel execution. Run only inside the
established native container; root serializes it with the other validation.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import time

assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
repo = Path('/workspace')
out = Path('/work/native-signal-abi-protocol-20260909-' + sys.argv[1])
out.mkdir()
record = dict(status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
              commands=[], inputs=[], runtime_libraries=[],
              scope='Actual native signal module with controlled FP callback; benign ordinary libc signal payload on Linux. No McKernel runtime credit.',
              mckernel_application_executed=False)


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())


def run(label, args, expected=0, timeout=90):
    print('RUN', label, flush=True)
    (out / 'phase').write_text(label + '\n')
    with (out / (label + '.log')).open('wb') as stream:
        result = subprocess.run(args, cwd=out, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    record['commands'].append(dict(label=label, command=args, expected=expected, exit_code=result.returncode))
    assert result.returncode == expected, (label, (out / (label + '.log')).read_text()[-8000:])
    return (out / (label + '.log')).read_text()


def read_marker(stream, expected, deadline, capture):
    data = bytearray()
    while len(data) < len(expected):
        remaining = deadline - time.monotonic()
        assert remaining > 0, ('marker timeout', expected, bytes(data))
        ready, _, _ = select.select([stream], [], [], min(remaining, 1))
        if not ready:
            continue
        byte = os.read(stream.fileno(), 1)
        assert byte, ('EOF before marker', expected, bytes(data))
        data.extend(byte)
        capture.write(byte)
        capture.flush()
    assert bytes(data) == expected, (expected, bytes(data))


def restart_reference(binary):
    label = 'linux-reference-fp-restart'
    (out / 'phase').write_text(label + '\n')
    command = [str(binary), 'fp-restart']
    child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, bufsize=0)
    deadline = time.monotonic() + 30
    try:
        with (out / (label + '.stdout')).open('wb') as stdout, (out / (label + '.stderr')).open('wb') as stderr:
            read_marker(child.stdout, b'NATIVE_SIGNAL_RESTART_READY\n', deadline, stdout)
            blocked = None
            while time.monotonic() < deadline:
                assert child.poll() is None, 'reference exited before blocked read'
                current = Path('/proc/' + str(child.pid) + '/syscall').read_text().strip()
                parts = current.split()
                if len(parts) >= 4 and parts[0] == '0' and int(parts[1], 0) == 0 and int(parts[3], 0) == 1:
                    blocked = current
                    break
                time.sleep(0.01)
            assert blocked is not None, 'reference did not enter stdin read'
            os.kill(child.pid, signal.SIGUSR1)
            read_marker(child.stderr, b'NATIVE_SIGNAL_RESTART_HANDLED\n', deadline, stderr)
            child.stdin.write(b'\xa5')
            child.stdin.close()
            child.stdin = None
            remaining_stdout, remaining_stderr = child.communicate(timeout=max(1, deadline - time.monotonic()))
            stdout.write(remaining_stdout)
            stderr.write(remaining_stderr)
            assert remaining_stdout == b'NATIVE_SIGNAL_ABI PASS fp-restart\n', remaining_stdout
            assert remaining_stderr == b'', remaining_stderr
            assert child.returncode == 37, child.returncode
            record['commands'].append(dict(label=label, command=command, expected=37,
                                           exit_code=child.returncode, controller_signal='SIGUSR1',
                                           blocked_syscall=blocked, input_hex='a5',
                                           handler_ack_before_input=True))
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


try:
    shutil.copyfile(__file__, out / 'helper.py')
    record['source_parent'] = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    names = ['kernel/rust/native_signal.rs', 'kernel/rust/abi.rs',
             'kernel/rust/syscall_policy.rs', 'arch/x86_64/kernel/syscall.c',
             'scripts/tests/fixtures/native-signal-abi.rs',
             'scripts/tests/fixtures/native-signal-abi.c']
    for name in names:
        target = out / 'original-inputs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, target)
        record['inputs'].append(identity(target))
    for name in ['native_signal.rs', 'abi.rs']:
        shutil.copyfile(out / 'original-inputs/kernel/rust' / name, out / name)
    for name in ['native-signal-abi.rs', 'native-signal-abi.c']:
        shutil.copyfile(out / 'original-inputs/scripts/tests/fixtures' / name, out / name)
    run('diff-check', ['git', '-C', str(repo), 'diff', '--check'])
    run('rust-compiler', ['rustc', '--version', '--verbose'])
    run('c-compiler', ['cc', '--version'])
    run('kernel', ['uname', '-a'])
    run('format', ['rustfmt', '--edition', '2021', '--config', 'skip_children=true,reorder_modules=false',
                   str(out / 'native_signal.rs'), str(out / 'native-signal-abi.rs')])
    run('native-rust-build', ['rustc', '--edition', '2021', '-D', 'warnings', '--cfg',
                              'native_linux_irq_work_v6_12', '--test', str(out / 'native-signal-abi.rs'),
                              '-o', str(out / 'native-tests')])
    run('native-rust-tests', [str(out / 'native-tests'), '--nocapture'])
    binary = out / 'native-signal-abi'
    run('payload-build', ['cc', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-no-pie',
                          '-Wl,-z,noexecstack', '-MD', '-MF', str(out / 'compiler.d'),
                          str(out / 'native-signal-abi.c'), '-o', str(binary)])
    header = run('elf', ['readelf', '-h', '-l', str(binary)])
    assert 'ELF64' in header and 'EXEC' in header and 'INTERP' in header
    run('disassembly', ['objdump', '-d', str(binary)])
    libraries = run('libraries', ['ldd', str(binary)])
    assert 'not found' not in libraries
    for name in sorted(set(re.findall(r'(/[^\s()]+)\s+\(0x[0-9a-f]+\)', libraries))):
        original = Path(name)
        target = out / 'runtime' / name.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        record['runtime_libraries'].append(dict(original=identity(original), captured=identity(target)))
    for case in ['mask-context', 'fp-return']:
        output = run('linux-reference-' + case, [str(binary), case], 37, 30)
        assert output == 'NATIVE_SIGNAL_ABI PASS ' + case + '\n', repr(output)
    restart_reference(binary)
    record['compiler_dependencies'] = []
    for name in (out / 'compiler.d').read_text().replace('\\\n', ' ').split()[1:]:
        dependency = Path(name)
        if dependency.is_absolute() and dependency.is_file():
            record['compiler_dependencies'].append(identity(dependency))
    assert record['compiler_dependencies']
    record['compiler_inputs'] = [identity(out / name) for name in
                                ['native_signal.rs', 'abi.rs', 'native-signal-abi.rs', 'native-signal-abi.c']]
    record.update(status='PASS', binary=identity(binary))
except BaseException as error:
    record.update(status='FAIL', error=str(error))
    raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    record['outputs'] = [identity(path) for path in sorted(out.iterdir())
                         if path.is_file() and path.name not in ('record.json', 'phase')]
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(record['status'], out, flush=True)
