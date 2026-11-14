#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

PREPARED ONLY: run only after dispatcher grants this exact ordinary CPU0 check.
Actual selected memory.c ABI/preprocessor/relocation check with host GCC9.
This is not the pinned GCC14 production compile, full Rust crate or image link.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
HOST = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def main():
    if os.getuid() != 1000 or os.geteuid() != 1000 or os.sched_getaffinity(0) != {0}:
        raise RuntimeError('exact ordinary CPU0 one-job grant required')
    commands = json.loads((HERE/'NEXT-CONSUMER-COMMANDS.json').read_text())
    work = HOST/'ordinary-selected-memory-tuple-attempt-1'
    work.mkdir()
    begin = time.monotonic()
    result = dict(scope=SCOPE, status='FAIL_RETAIN_FIRST_FAILED_COMMAND',
        production_GCC14_compile=False, production_fullcrate=False, image_link=False,
        native=False, actual_case_vectors_not_repeated=129888, command_statuses=[])
    def run(label, argv):
        (work/(label+'.argv.json')).write_text(json.dumps(argv, indent=2)+'\n')
        start = time.monotonic()
        p = subprocess.run(argv, capture_output=True, timeout=35, env=dict(os.environ, RUST_MIN_STACK='2097152'))
        (work/(label+'.stdout')).write_bytes(p.stdout)
        (work/(label+'.stderr')).write_bytes(p.stderr)
        result['command_statuses'].append(dict(label=label, returncode=p.returncode,
            seconds=time.monotonic()-start, direct_child_joined=True))
        if p.returncode != 0:
            raise RuntimeError('first failed command: '+label)
        return p.stdout.decode()
    try:
        memory = HOST/'materialized-source/arch/x86_64/kernel/memory.c'
        if hashlib.sha256(memory.read_bytes()).hexdigest() != '4818be5c7277621ce41dae1d261dec97e7e0c65b6054a6e8511a4d64d555c68f':
            raise RuntimeError('accepted memory postimage drift')
        version = run('compiler-version', ['/usr/bin/gcc-9','--version'])
        if not version.startswith('gcc-9 ') or ' 9.' not in version.splitlines()[0]:
            raise RuntimeError('ordinary GCC9 profile mismatch')
        pp = run('selected-memory-preprocess', commands['ordinary_host_only']['preprocessor_argv'])
        if 'extern int x86_clear_old_action_bridge' not in pp:
            raise RuntimeError('selected external Rust callback declaration absent')
        for name in ('clear_range_old_action','x86_clear_old_action_bridge'):
            if re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{', pp, re.S):
                raise RuntimeError('selected old C implementation remained: '+name)
        run('selected-memory-whole-TU', commands['ordinary_host_only']['whole_TU_argv'])
        obj = str(work/'memory.c.o')
        undefined = run('selected-memory-imports', ['/usr/bin/nm','-u',obj])
        if sum(line.split()[-1:] == ['x86_clear_old_action_bridge'] for line in undefined.splitlines()) != 1:
            raise RuntimeError('expected unique selected Rust callback import')
        symbols = run('selected-memory-all-symbols', ['/usr/bin/nm','-a',obj])
        if any(line.split()[-1:] == ['clear_range_old_action'] or
               (line.split()[-1:] == ['x86_clear_old_action_bridge'] and line.split()[-2] != 'U')
               for line in symbols.splitlines()):
            raise RuntimeError('selected old C callback/body is still defined')
        relocations = run('selected-memory-relocations', ['/usr/bin/readelf','-rW',obj])
        if not any('x86_clear_old_action_bridge' in line for line in relocations.splitlines()):
            raise RuntimeError('actual selected callback relocation absent')
        result.update(status='PASS_ORDINARY_ACTUAL_SELECTED_MEMORY_TU_ABI_AND_RUST_CALLBACK_RELOCATION_ONLY',
            selected_C_layout_and_flag_assertions_compiled=True,
            selected_C_original_body_and_adapter_preprocessed_out=True,
            selected_Rust_callback_import_unique=True,
            selected_Rust_callback_relocation_present=True,
            object_sha256=hashlib.sha256(Path(obj).read_bytes()).hexdigest())
    except BaseException as error:
        result['error'] = repr(error)
    result['seconds'] = time.monotonic()-begin
    (work/'result.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
