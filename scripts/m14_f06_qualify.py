#!/usr/bin/env python3
"""Prepare or inspect the F06 source-ownership candidate on an ordinary HOST.

--prepare recovers exact source blobs from the interrupted public-repository
publication, merges only its CMake changes, and retains the whole selector OFF.
It never updates a branch, installs a kernel or touches native devices.

The verification uses the actual kernel CMake selection and real project/IHK
headers. Zero C output is a necessary ownership gate, not file acceptance.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = 'phoenix-hacking/mckernel'
RECOVERED = {
    'arch/x86_64/kernel/syscall.c': '54820e85b803b18b1a43848ecc0b9d1ea4fab717',
    'kernel/rust/f06_signal_tail.rs': 'fb054f4d502286f913c293488509902718b4aa91',
    'kernel/rust/f06_rt_sigreturn_xrstor.rs': 'fbdb173dca6b41a4c3cd7d80aa75bcb917a890a0',
    'kernel/rust/lib.rs': 'd9fdd046b48af96f3e57a6af86a11e732fd5d526',
}


def run(argv, **kwargs):
    result = subprocess.run([str(arg) for arg in argv], cwd=ROOT, text=True,
                            capture_output=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{argv[0]} failed ({result.returncode})\n{result.stdout}\n{result.stderr}')
    return result.stdout


def blob(sha):
    request = urllib.request.Request(f'https://api.github.com/repos/{REPO}/git/blobs/{sha}',
                                     headers={'Accept': 'application/vnd.github+json'})
    token = os.environ.get('GH_TOKEN')
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(request, timeout=45) as response:
        record = json.load(response)
    data = base64.b64decode(record['content'])
    observed = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if observed != sha:
        raise ValueError('recovered source does not match its Git object identity')
    return data


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f'expected exactly one source anchor: {before[:100]!r}')
    return text.replace(before, after, 1)


def item_end(text, start):
    opening = text.index('{', start)
    end, depth = opening + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return end


def prepare():
    for name, sha in RECOVERED.items():
        path = ROOT / name
        path.write_bytes(blob(sha))
    cmake_path = ROOT / 'kernel/CMakeLists.txt'
    with tempfile.TemporaryDirectory() as temporary:
        base, candidate, current = (Path(temporary) / name for name in ('base', 'candidate', 'current'))
        base.write_bytes(blob('051fce73aa3dc5c3be81dd605b24e01e85f1e52a'))
        proposal = blob('cc14ef45983b1226c55215a71e6b26576aa8315e').decode()
        # The newer branch quotes the compiler path. Preserve that repair while
        # inserting the adjacent F06 metadata environment variable.
        proposal = replace_once(proposal, '\t\t\t${RUSTC}\n\t\t\t--crate-name',
                                '\t\t\t"${RUSTC}"\n\t\t\t--crate-name')
        candidate.write_text(proposal)
        current.write_bytes(cmake_path.read_bytes())
        merged = run(['git', 'merge-file', '-p', current, base, candidate])
    # No default cutover without a matching production link and native proof.
    merged = replace_once(merged,
        'option(ENABLE_RUST_F06_SYSCALL_WHOLE "Select complete x86 syscall Rust/assembly ownership in the supported profile" ${MCKERNEL_RUST_F06_WHOLE_DEFAULT})',
        'option(ENABLE_RUST_F06_SYSCALL_WHOLE "Build the complete F06 ownership candidate; production qualification pending" OFF)')
    merged = replace_once(merged,
        '# Complete F06 source ownership defaults to Rust only in the existing supported\n# production profile. Native/image qualification remains a separate requirement.',
        '# Complete F06 candidate is opt-in until matched image/native qualification.\n# The supported profile is checked below; no new runtime authority is granted.')
    merged = replace_once(merged,
        'set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin.py")',
        'set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin.py")\n'
        '\t\t\t\tset_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS\n'
        '\t\t\t\t    "${PROJECT_SOURCE_DIR}/scripts/derive_f06_signal_metadata.py")')
    cmake_path.write_text(merged)
    policy_path = ROOT / 'kernel/rust/syscall_policy.rs'
    policy = policy_path.read_text()
    anchor = '// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n// Reuse existing context entry independently of unqualified whole-signal bodies.'
    start = policy.index(anchor)
    final_module = policy.index('mod f06_whole_signal_restart_provider {', start)
    end = item_end(policy, final_module)
    policy_path.write_text(policy[:start] + '#[path = "f06_signal_tail.rs"]\nmod f06_signal_tail;\n' + policy[end:])
    for name in ('test_m14_f06_signal_restart.py', 'test_m14_f06_signal_xsave_cleanup.py'):
        path = ROOT / 'scripts/tests' / name
        content = path.read_text()
        content = content.replace("(ROOT/'kernel/rust/syscall_policy.rs').read_text()",
                                  "(ROOT/'kernel/rust/f06_signal_tail.rs').read_text()")
        if name == 'test_m14_f06_signal_xsave_cleanup.py':
            old = "            (path/'test.rs').write_text(prefix+RUST+error+RUST_CASES+body)"
            new = "\n".join([
                "            from scripts.derive_f06_signal_metadata import derive_signal_metadata",
                "            origin = '/src/arch/x86_64/kernel/syscall.c'",
                "            fields = derive_signal_metadata((ROOT/'arch/x86_64/kernel/syscall.c').read_text(), origin)",
                "            prefix += f'const F06_SIGNAL_ORIGIN: &[u8] = b\"{origin}\\\\0\";\\n'",
                "            for name, value in fields.items():",
                "                kind = 'u32' if name.endswith('FLAGS') else 'i32'",
                "                prefix += f'const {name}: {kind} = {value};\\n'",
                old,
            ])
            content = replace_once(content, old, new)
        path.write_text(content)
    binding_path = ROOT / 'scripts/f06_origin_source_binding.json'
    binding = json.loads(binding_path.read_text())
    binding['current_arch_source_sha256'] = hashlib.sha256((ROOT / 'arch/x86_64/kernel/syscall.c').read_bytes()).hexdigest()
    binding_path.write_text(json.dumps(binding, indent=2) + '\n')
    origin_path = ROOT / 'scripts/derive_f06_origin.py'
    origin = origin_path.read_text()
    origin, count = re.subn(r'SOURCE_BINDING_SHA256 = "[0-9a-f]{64}"',
        'SOURCE_BINDING_SHA256 = "' + hashlib.sha256(binding_path.read_bytes()).hexdigest() + '"', origin)
    if count != 1:
        raise ValueError('source binding pin declaration changed')
    origin = replace_once(origin, '    clone_slots = derive_clone_cpuid(args.profile, args.source, origin)',
        '    clone_slots = derive_clone_cpuid(args.profile, args.source, origin)\n'
        '    if args.source_binding is not None:\n'
        '        from derive_f06_signal_metadata import write_signal_metadata\n'
        '        write_signal_metadata(args.source, origin, args.output)')
    origin_path.write_text(origin)
    runner_path = ROOT / 'scripts/run_m14_focused_checks.py'
    runner = runner_path.read_text()
    runner = replace_once(runner, 'SOURCE_PATHS = (',
        'SOURCE_PATHS = (\n    "kernel/rust/f06_signal_tail.rs", "kernel/rust/f06_rt_sigreturn_xrstor.rs",\n'
        '    "scripts/derive_f06_signal_metadata.py",')
    runner_path.write_text(runner)
    print('Prepared recovered F06 candidate; selector remains OFF.', flush=True)


def inspect_c(ihk, output):
    cc, cmake, rustc = (os.environ.get(name, fallback) for name, fallback in
                        (('CC', 'gcc'), ('CMAKE', 'cmake'), ('RUSTC', 'rustc')))
    report = {'scope': 'SUPPLEMENTAL_HOST_F06_C_OWNERSHIP_ONLY',
              'file_accepted': False, 'native_qualified': False,
              'selector_default': 'OFF', 'compiler': run([cc, '--version']).splitlines()[0],
              'ihk_commit': run(['git', '-C', ihk, 'rev-parse', 'HEAD']).strip(),
              'source_base_commit': run(['git', 'rev-parse', 'HEAD']).strip(), 'profiles': {}}
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
set(MCKERNEL_HOST_IRQ_ABI linux-6.12 CACHE STRING "")
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
configure_file("@ROOT@/config.h.in" "${PROJECT_BINARY_DIR}/config.h")
add_subdirectory("@ROOT@/kernel" "${PROJECT_BINARY_DIR}/kernel")
'''.replace('@ROOT@', str(ROOT)).replace('@IHK@', str(ihk))
        (fixture / 'CMakeLists.txt').write_text(driver)
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
            import shlex
            original = shlex.split(matches[0]['command'])
            row_results = {}
            for level in ('O0', 'O2'):
                obj = root / f'{selected}-{level}.o'
                argv = [arg for arg in original if not re.fullmatch('-O[0-9sg]', arg)]
                argv[argv.index('-o') + 1] = str(obj)
                argv += ['-' + level, '-fno-lto', f'-fmacro-prefix-map={ROOT}=/src']
                # HOST compiler/path mapping is explicit and does not alter the frozen SDK profile.
                run(argv)
                defined = run(['nm', '--defined-only', '--format=posix', obj]).splitlines()
                undefined = run(['nm', '--undefined-only', '--format=posix', obj]).splitlines()
                sections = run(['readelf', '-SW', obj])
                allocated = []
                for line in sections.splitlines():
                    match = re.match(r'\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+[0-9a-f]+\s+[0-9a-f]+\s+([0-9a-f]+)\s+[0-9a-f]+\s+(\S+)', line)
                    if match and 'A' in match[3] and int(match[2], 16) and not match[1].startswith('.note'):
                        allocated.append({'name': match[1], 'bytes': int(match[2], 16)})
                row_results[level] = {'defined_symbols': defined, 'undefined_symbols': undefined,
                                      'allocated_runtime_sections': allocated,
                                      'object_sha256': hashlib.sha256(obj.read_bytes()).hexdigest()}
                if selected and (defined or undefined or allocated):
                    raise ValueError('F06 candidate still emits C runtime ownership: ' + json.dumps(row_results[level]))
                if not selected and not any(line.startswith('do_signal ') for line in defined):
                    raise ValueError('default negative control lost its C do_signal owner')
            report['profiles']['candidate' if selected else 'default_control'] = row_results
        report['status'] = 'PASS'
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--ihk-source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('/tmp/m14-f06-ownership.json'))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.ihk_source:
        inspect_c(args.ihk_source.resolve(), args.output)


if __name__ == '__main__':
    main()
