#!/usr/bin/env python3
"""Inspect actual F06 C ownership with real CMake selection and project headers.

This ordinary HOST check compiles only the architecture syscall C object and
isolated complete Rust replacement modules. It does not rewrite source, retrieve
uncommitted objects, build or deploy a full kernel, or perform native operations.
The final image and original supported native qualification remain separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(argv, **kwargs):
    result = subprocess.run([str(arg) for arg in argv], cwd=ROOT, text=True,
                            capture_output=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{argv[0]} failed ({result.returncode})\n{result.stdout[-10000:]}\n{result.stderr[-10000:]}')
    return result.stdout


def symbol_bytes(obj, name, directory):
    """Read a defined object symbol from its actual ELF section, not a model."""
    symbols = [line.split() for line in run(['nm', '-S', '--defined-only', '--format=posix', obj]).splitlines()
               if line.split() and line.split()[0] == name]
    if len(symbols) != 1 or len(symbols[0]) != 4:
        raise ValueError('expected one sized object symbol: ' + name)
    row = symbols[0]
    offset, size = int(row[2], 16), int(row[3], 16)
    sections = [line.split()[-3] for line in run(['objdump', '-t', obj]).splitlines()
                if line.split() and line.split()[-1] == name]
    if len(sections) != 1 or not sections[0].startswith('.'):
        raise ValueError('expected one concrete section for ' + name)
    dumped = directory / (obj.name + '.symbol-section')
    run(['objcopy', '--dump-section', sections[0] + '=' + str(dumped), obj])
    data = dumped.read_bytes()
    if offset + size > len(data):
        raise ValueError('symbol extends beyond its file-backed section')
    return data[offset:offset + size]


def inherited_definitions():
    """Retain the actual top-level C defines that the kernel subdir inherits."""
    source = (ROOT / 'CMakeLists.txt').read_text()
    profile = json.loads((ROOT / 'scripts/f06_origin_command_profile.json').read_text())
    commands = [row for row in profile['exact_commands'] if row['stage'] == 'selected x86 syscall object']
    if len(commands) != 1:
        raise ValueError('missing exact reference C profile')
    definitions = ('-DPROFILE_ENABLE', '-DIHK_IKC_USE_LINUX_WORK_IRQ')
    for definition in definitions:
        if source.count('add_definitions(' + definition + ')') != 1 or definition not in commands[0]['argv']:
            raise ValueError('top-level inherited ABI definition drift: ' + definition)
    return definitions


def inspect_c(ihk, output):
    cc, cmake, rustc = (os.environ.get(name, fallback) for name, fallback in
                        (('CC', 'gcc'), ('CMAKE', 'cmake'), ('RUSTC', 'rustc')))
    if run(['git', '-C', ihk, 'status', '--porcelain']).strip():
        raise ValueError('IHK header source must have a clean working tree')
    inherited = inherited_definitions()
    source_paths = ('CMakeLists.txt', 'arch/x86_64/kernel/syscall.c', 'kernel/CMakeLists.txt',
                    'kernel/rust/abi.rs', 'kernel/rust/f06_rt_sigreturn_xrstor.rs',
                    'kernel/rust/f06_signal_tail.rs', 'kernel/rust/x86_cpu_helpers.rs',
                    'scripts/derive_f06_origin.py', 'scripts/derive_f06_signal_metadata.py',
                    'scripts/f06_origin_source_binding.json', 'scripts/m14_f06_qualify.py')
    report = {'scope': 'SUPPLEMENTAL_HOST_F06_C_OWNERSHIP_AND_DEBUG_DATA_ABI',
              'file_accepted': False, 'native_qualified': False,
              'selector_default': 'OFF', 'compiler': run([cc, '--version']).splitlines()[0],
              'rustc': run([rustc, '--version']).strip(),
              'inherited_abi_definitions': list(inherited),
              'ihk_commit': run(['git', '-C', ihk, 'rev-parse', 'HEAD']).strip(),
              'source_base_commit': run(['git', 'rev-parse', 'HEAD']).strip(),
              'source_files_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                      for name in source_paths},
              'profiles': {},
              'limitations': ['Explicit HOST macro-prefix mapping is not the frozen production SDK command.',
                              'Rust provider linkage, final image and native execution are not established.']}
    with tempfile.TemporaryDirectory(prefix='m14-f06-') as temporary:
        root = Path(temporary)
        fixture = root / 'source'
        fixture.mkdir()
        driver = '''cmake_minimum_required(VERSION 3.20)
project(f06_ownership LANGUAGES C ASM)
set(PROJECT_SOURCE_DIR "@ROOT@")
set(ARCH x86_64)
set(BUILD_TARGET smp-x86)
set(IHK_FULL_SOURCE_DIR "@IHK@")
set(MAP_KERNEL_START 0xfffffffffe800000)
set(MCKERNEL_VERSION 1.8.0)
set(BUILDID f06-host-ownership)
set(MCKERNELDIR lib/mckernel)
set(ENABLE_PERF ON)
set(ENABLE_RUSAGE ON)
set(ENABLE_MEMDUMP ON)
set(PROFILE_ENABLE ON)
add_definitions(@INHERITED@)
set(MCKERNEL_HOST_IRQ_ABI linux-6.12 CACHE STRING "")
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
configure_file("@ROOT@/config.h.in" "${PROJECT_BINARY_DIR}/config.h")
add_subdirectory("@ROOT@/kernel" "${PROJECT_BINARY_DIR}/kernel")
'''.replace('@ROOT@', str(ROOT)).replace('@IHK@', str(ihk)).replace('@INHERITED@', ' '.join(inherited))
        (fixture / 'CMakeLists.txt').write_text(driver)
        controls = []
        for selected in (False, True):
            build = root / ('selected' if selected else 'default')
            options = [f'-DRUSTC={rustc}', f'-DCMAKE_C_COMPILER={cc}']
            if selected:
                options.append('-DENABLE_RUST_F06_SYSCALL_WHOLE=ON')
            run([cmake, '-S', fixture, '-B', build, *options])
            commands = json.loads((build / 'compile_commands.json').read_text())
            matches = [row for row in commands if Path(row['file']) == ROOT / 'arch/x86_64/kernel/syscall.c']
            if len(matches) != 1:
                raise ValueError('expected one actual F06 compile command')
            original = shlex.split(matches[0]['command'])
            if any(definition not in original for definition in inherited):
                raise ValueError('actual F06 command lost its inherited ABI definitions')
            row_results = {}
            for level in ('O0', 'O2'):
                obj = root / f'{selected}-{level}.o'
                argv = [arg for arg in original if not re.fullmatch('-O[0-9sg]', arg)]
                argv[argv.index('-o') + 1] = str(obj)
                argv += ['-' + level, '-fno-lto', f'-fmacro-prefix-map={ROOT}=/src']
                run(argv)
                defined = run(['nm', '--defined-only', '--format=posix', obj]).splitlines()
                undefined = run(['nm', '--undefined-only', '--format=posix', obj]).splitlines()
                allocated = []
                for line in run(['readelf', '-SW', obj]).splitlines():
                    match = re.match(r'\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+[0-9a-f]+\s+[0-9a-f]+\s+([0-9a-f]+)\s+[0-9a-f]+\s+(\S+)', line)
                    if match and 'A' in match[3] and int(match[2], 16) and not match[1].startswith('.note'):
                        allocated.append({'name': match[1], 'bytes': int(match[2], 16)})
                row_results[level] = {'defined_symbols': defined, 'undefined_symbols': undefined,
                                      'allocated_runtime_sections': allocated,
                                      'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest()}
                if selected and (defined or undefined or allocated):
                    raise ValueError('F06 candidate still emits C runtime ownership: ' + json.dumps(row_results[level]))
                if not selected:
                    if not any(line.startswith('do_signal ') for line in defined):
                        raise ValueError('default negative control lost its C do_signal owner')
                    controls.append(symbol_bytes(obj, 'debug_constants', root))
            report['profiles']['candidate' if selected else 'default_control'] = row_results
        sys.path.insert(0, str(ROOT))
        from scripts.tests.test_m14_f06_tail_codegen import build_fixture
        rust_dir = root / 'rust-debug-abi'
        rust_dir.mkdir()
        source, metadata = build_fixture(rust_dir, native=True)
        rust_obj = rust_dir / 'replacement.o'
        args = [rustc, '--edition=2021', '--crate-type=lib', '-Awarnings',
                '-C', 'panic=abort', '-C', 'opt-level=2', '-C', 'code-model=large',
                '-C', 'relocation-model=static', '-C', 'no-redzone=yes',
                '-C', 'no-vectorize-loops', '-C', 'no-vectorize-slp',
                '-C', 'target-feature=-sse,-sse2,-avx,-avx2',
                '--emit=obj', '-o', rust_obj, source]
        for cfg in ('f06_signal_context_candidate', 'f06_do_signal_whole_candidate',
                    'f06_do_signal_reuse_qualified_context', 'f06_signal_trap_info_candidate',
                    'f06_rt_sigreturn_xrstor_candidate', 'f06_debug_constants_candidate',
                    'native_linux_irq_work_v6_12', 'enable_profile', 'enable_perf', 'enable_rusage'):
            args += ['--cfg', cfg]
        run(args, env=dict(os.environ, MCKERNEL_F06_SIGNAL_METADATA_RS=str(metadata)))
        rust_data = symbol_bytes(rust_obj, 'debug_constants', root)
        if len(rust_data) != 96 or any(data != rust_data for data in controls):
            raise ValueError('debug_constants mismatch: ' + json.dumps({
                'C': [list(struct.unpack('<' + 'Q' * (len(data) // 8), data)) for data in controls],
                'Rust': list(struct.unpack('<' + 'Q' * (len(rust_data) // 8), rust_data))}))
        report['debug_constants'] = {'matches_C_O0_and_O2': True, 'bytes': len(rust_data),
                                     'values': list(struct.unpack('<12Q', rust_data))}
        report['status'] = 'PASS'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ihk-source', type=Path, required=True,
                        help='clean exact IHK checkout restored by restore_ihk_source.py')
    parser.add_argument('--output', type=Path, default=Path('/tmp/m14-f06-ownership.json'))
    args = parser.parse_args()
    inspect_c(args.ihk_source.resolve(), args.output)


if __name__ == '__main__':
    main()
