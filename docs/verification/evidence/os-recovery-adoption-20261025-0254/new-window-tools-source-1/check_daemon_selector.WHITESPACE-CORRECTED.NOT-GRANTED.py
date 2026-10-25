#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate miniature CMake consumers only. No daemon execution or Rust compilation.
CMake compiler detection may invoke the host C compiler, so root grant is required.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--cmake', default='/usr/bin/cmake')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit('Source only; explicit root ordinary grant required')
    args.output.mkdir(parents=True, exist_ok=False)
    selector = Path(__file__).with_name('ihkmond-selector.cmake').read_text()
    results = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='m15-daemon-selector-') as temporary:
        base = Path(temporary)
        source = base / 'source'
        nested = source / 'ihk'
        user = nested / 'linux/user'
        (user / 'rust').mkdir(parents=True)
        (nested / 'linux/include/ihk').mkdir(parents=True, exist_ok=True)
        for header in ('ihklib.h', 'ihklib_private.h', 'ihk_host_user.h'):
            (nested / 'linux/include/ihk' / header).write_text('/* fixture only */\n')
        (source / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.10)\n'
            'project(daemon_selection_fixture C)\n'
            'include(GNUInstallDirs)\nadd_subdirectory(ihk)\n')
        (nested / 'CMakeLists.txt').write_text(
            'project(nested_ihk_fixture C)\nset(ARCH x86_64)\n'
            'set(IHK_USER_RUSTC /bin/true)\n'
            'set(LIBUDEV "${CMAKE_CURRENT_SOURCE_DIR}/fixture-libudev.so")\n'
            'add_subdirectory(linux/user)\n')
        (nested / 'fixture-libudev.so').write_bytes(b'not linked: generation only\n')
        (user / 'ihkmond.c').write_text('int main(void) { return 0; }\n')
        (user / 'stub.c').write_text('int fixture_library(void) { return 0; }\n')
        (user / 'rust/ihkmond.rs').write_text('fn main() {}\n')
        (user / 'CMakeLists.txt').write_text('add_library(ihklib SHARED stub.c)\n' + selector)
        cases = [
            ('default', [], True),
            ('reference', ['-DENABLE_RUST_USER_TOOLS=OFF', '-DIHK_ALLOW_CLI_C_FALLBACK=ON'], True),
            ('no_implicit_C', ['-DENABLE_RUST_USER_TOOLS=OFF', '-DIHK_ALLOW_CLI_C_FALLBACK=OFF'], False),
        ]
        for name, options, success in cases:
            build = base / name
            command = [args.cmake, '-S', str(source), '-B', str(build), '-G', 'Unix Makefiles', *options]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=45, check=False)
            (args.output / (name + '.log')).write_text(result.stdout)
            if (result.returncode == 0) != success:
                raise RuntimeError(f'{name}: unexpected CMake status {result.returncode}')
            if name == 'default':
                rule = (build / 'ihk/linux/user/CMakeFiles/ihkmond.dir/build.make').read_text()
                if ': CMakeCache.txt\n' not in rule and str(build / 'CMakeCache.txt') not in rule:
                    raise RuntimeError('Missing actual top-level cache dependency')
                if str(build / 'ihk/CMakeCache.txt') in rule:
                    raise RuntimeError('Nonexistent nested cache dependency remains')
                if 'linker=/usr/bin/cc' not in rule and 'linker=/usr/bin/gcc' not in rule:
                    raise RuntimeError('Missing selected C linker binding')
                if '/bin/true' not in rule or 'ihkmond.c.o' in rule:
                    raise RuntimeError('Default daemon is not exclusively the selected Rust command')
                install = (build / 'ihk/linux/user/cmake_install.cmake').read_text()
                if '/sbin' not in install or 'TYPE PROGRAM' not in install:
                    raise RuntimeError('Missing daemon program installation in sbin')
                (args.output / 'default.build.make').write_text(rule)
                (args.output / 'default.install.cmake').write_text(install)
            if name == 'reference':
                rule = (build / 'ihk/linux/user/CMakeFiles/ihkmond.dir/build.make').read_text()
                if 'ihkmond.c.o' not in rule or 'linker=' in rule:
                    raise RuntimeError('Explicit C comparison selector is not preserved')
            if name == 'no_implicit_C' and 'no silent production C fallback' not in ' '.join(result.stdout.split()):
                raise RuntimeError('Wrong failure in non-Rust default profile')
            results.append({'case': name, 'argv': command, 'exit': result.returncode})
    record = {
        'scope': __doc__.splitlines()[0], 'cases': results,
        'wall_seconds': time.monotonic() - started,
        'actual_daemon_compiled': False, 'actual_daemon_executed': False,
        'native_or_retirement_credit': 0,
    }
    (args.output / 'RESULT.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
