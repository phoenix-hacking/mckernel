"""Actual Rust FPU-copy body versus original C, including default caller routing.

Run only in the dispatcher's reviewed cheap host profile. Set
MCKERNEL_RUST_FPU_COPY_OUTPUT to a fresh evidence directory; every command,
stream, return code, generated input and output hash is retained there.
This is a source-bound object/behavior check, never native image acceptance.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest

from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
FIXTURE = ROOT / 'scripts/tests/fixtures/rust_fpu_copy_cutover_20261018.rs'
ORIGINAL_CPU_SHA256 = '5d93923119ac07f898849977463dc6e13349aa68831ae20e7aa1a6add92736be'


class RustFpuCopyCutoverTests(unittest.TestCase):
    def test_actual_copy_and_default_consumer(self):
        out = Path(os.environ['MCKERNEL_RUST_FPU_COPY_OUTPUT'])
        out.mkdir(exist_ok=False)
        commands = []

        def run(label, argv):
            commands.append({'label': label, 'argv': argv})
            (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            for stream in ['stdout', 'stderr']:
                (out / (label + '.' + stream)).write_text(getattr(result, stream))
            (out / (label + '.status')).write_text(str(result.returncode) + '\n')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result

        sources = ['arch/x86_64/kernel/cpu.c', 'kernel/rust/x86_cpu_helpers.rs',
                   'kernel/rust/abi.rs', 'kernel/rust/lib.rs', 'kernel/CMakeLists.txt',
                   'kernel/process.c', 'kernel/rust/tests/run_equivalence.sh',
                   'scripts/tests/test_rust_fpu_copy_cutover_20261018.py',
                   'scripts/tests/fixtures/rust_fpu_copy_cutover_20261018.rs']
        hashes = {}
        for relative in sources:
            data = (ROOT / relative).read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            target = out / 'sources' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / 'source-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cpu = (out / 'sources/arch/x86_64/kernel/cpu.c').read_text()
        rust = (out / 'sources/kernel/rust/x86_cpu_helpers.rs').read_text()
        abi_path = out / 'sources/kernel/rust/abi.rs'
        cmake = (out / 'sources/kernel/CMakeLists.txt').read_text()
        self.assertIn('option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)', cmake)
        self.assertIn('if (RUST_KERNEL_ENABLED)', cmake)
        selection_cmake = ('set_source_files_properties("${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpu.c"\n'
                           '\t\tPROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_X86_CPU_HELPERS)')
        self.assertIn(selection_cmake, cmake)
        self.assertIn('mod x86_cpu_helpers;', (out / 'sources/kernel/rust/lib.rs').read_text())
        process = (out / 'sources/kernel/process.c').read_text()
        self.assertIn('if (copy_fp_regs(org, thread)) {\n\t\tgoto free_fp_regs;\n\t}', process)

        marker = '#ifdef MCKERNEL_RUST_X86_CPU_HELPERS\nextern int rust_x86_copy_fp_regs('
        start = cpu.index(marker)
        end = cpu.index('\n#endif', start) + len('\n#endif')
        selection = cpu[start:end]
        fallback = selection.split('#else\n', 1)[1].removesuffix('\n#endif')
        # Bind the complete pre-cutover CPU reference, preserving the accepted
        # full-XSAVE memcpy fix and every unrelated production byte.
        original_cpu = cpu[:start] + fallback + cpu[end:]
        self.assertEqual(hashlib.sha256(original_cpu.encode()).hexdigest(), ORIGINAL_CPU_SHA256)
        (out / 'original-cpu.c').write_text(original_cpu)
        allocation = 'static int\n' + balanced_item(cpu, 'check_and_allocate_fp_regs(struct thread *thread)')
        c_source = '''#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define PAGE_SIZE 4096
#define PAGE_SHIFT 12
#define PAGE_P2ALIGN 0
#define IHK_MC_AP_NOWAIT 2
#define IHK_MC_PG_KERNEL 0
#define ENOMEM 12
#define dkprintf(...) ((void)0)
#define kprintf(...) ((void)0)
#define _ihk_mc_alloc_aligned_pages_node x86_alloc_aligned_pages_node_bridge
struct thread { unsigned char prefix[4784]; void *fp_regs; unsigned char suffix[776]; } __attribute__((aligned(64)));
_Static_assert(sizeof(struct thread) == 5568, "Thread size");
_Static_assert(offsetof(struct thread, fp_regs) == 4784, "Thread fp_regs offset");
extern void *x86_alloc_aligned_pages_node_bridge(int,int,unsigned long,int,int,unsigned long,char *,int);
static int xsave_available, xsave_size;
void configure_copy(int available, int size) { xsave_available=available; xsave_size=size; }
#line 3230 "arch/x86_64/kernel/cpu.c"
'''
        c_source += allocation + '\n' + fallback.replace('int copy_fp_regs(', 'int reference_copy_fp_regs(', 1)
        c_source += '\n' + selection + '\n'
        (out / 'actual_copy.c').write_text(c_source)
        body = balanced_item(rust, 'pub unsafe extern "C" fn rust_x86_copy_fp_regs(')
        constants = []
        for name in ['EINVAL', 'ENOMEM', 'PAGE_SIZE', 'PAGE_P2ALIGN', 'IHK_MC_AP_NOWAIT', 'IHK_MC_PG_KERNEL']:
            constants.append(re.search(r'^const ' + name + r':.*;$', rust, re.M).group())
        constants.append(re.search(r'^static CPU_FILE:.*;$', rust, re.M).group())
        # The only production body tested is extracted verbatim. The complete
        # production ABI module executes all its existing compile-time checks.
        rust_source = '#![no_std]\n#[path=' + json.dumps(str(abi_path)) + '] mod abi;\n'
        rust_source += 'use abi::{CInt,CULong,Thread}; use core::ffi::c_void;\n'
        rust_source += '\n'.join(constants)
        rust_source += '''
extern "C" { fn x86_alloc_aligned_pages_node_bridge(
    pages:CInt,align:CInt,flags:CULong,node:CInt,is_user:CInt,
    address:CULong,file:*mut i8,line:CInt)->*mut c_void; }
#[no_mangle]
'''
        rust_source += body + '\n'
        (out / 'actual_copy.rs').write_text(rust_source)
        version = run('rust-version', [RUSTC, '--version'])
        self.assertTrue(version.stdout.startswith('rustc 1.92.0 '))
        # Exact retained kernel equivalence flags; no host-derived/guessed rlib.
        kernel_flags = ['-C', 'panic=abort', '-C', 'opt-level=2', '-C', 'debuginfo=2',
                        '-C', 'code-model=large', '-C', 'relocation-model=static',
                        '-C', 'no-redzone=yes', '-C', 'force-frame-pointers=yes',
                        '-C', 'overflow-checks=off', '-C', 'force-unwind-tables=no',
                        '-C', 'no-vectorize-loops', '-C', 'no-vectorize-slp',
                        '-C', 'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        retained_recipe = (out / 'sources/kernel/rust/tests/run_equivalence.sh').read_text()
        for index in range(0, len(kernel_flags), 2):
            self.assertIn(' '.join(kernel_flags[index:index + 2]), retained_recipe)
        run('rust-kernel-object', [RUSTC, '--edition=2021', '--crate-type=lib'] + kernel_flags +
            ['--emit=obj', str(out / 'actual_copy.rs'), '-o', str(out / 'actual_copy.o')])
        for variant, flags in [('selected', ['-DMCKERNEL_RUST_X86_CPU_HELPERS']), ('fallback', [])]:
            run(variant + '-c-object', ['/usr/bin/gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra',
                '-Werror', '-fno-pie', '-c'] + flags + [str(out / 'actual_copy.c'), '-o', str(out / (variant + '.o'))])
        selected_nm = run('selected-symbols', ['/usr/bin/nm', str(out / 'selected.o')]).stdout
        fallback_nm = run('fallback-symbols', ['/usr/bin/nm', str(out / 'fallback.o')]).stdout
        rust_nm = run('rust-symbols', ['/usr/bin/nm', str(out / 'actual_copy.o')]).stdout
        self.assertRegex(selected_nm, r'\bU rust_x86_copy_fp_regs\b')
        self.assertRegex(selected_nm, r'\bT copy_fp_regs\b')
        self.assertNotIn('rust_x86_copy_fp_regs', fallback_nm)
        self.assertRegex(fallback_nm, r'\bT copy_fp_regs\b')
        self.assertRegex(rust_nm, r'\bT rust_x86_copy_fp_regs\b')
        disassembly = run('rust-disassembly', ['/usr/bin/objdump', '-dr', str(out / 'actual_copy.o')]).stdout
        self.assertNotRegex(disassembly, r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b')
        template = FIXTURE.read_text()
        fixture = template.replace('// REAL_THREAD_ABI', '#[path=' + json.dumps(str(abi_path)) + '] mod abi;')
        (out / 'fixture.rs').write_text(fixture)
        run('fixture-compile', [RUSTC, '--edition=2021', '-C', 'panic=abort', '-C', 'opt-level=1',
            '-C', 'codegen-units=1', '-C', 'link-arg=-no-pie',
            '-C', 'link-arg=' + str(out / 'selected.o'), '-C', 'link-arg=' + str(out / 'actual_copy.o'),
            str(out / 'fixture.rs'), '-o', str(out / 'fixture')])
        result = run('fixture-run', [str(out / 'fixture')])
        self.assertEqual(result.stderr, '')
        self.assertEqual(len(result.stdout.splitlines()), 65)
        self.assertTrue(result.stdout.endswith('PASS 64 C/Rust parity cases; 8 invalid configurations; 2 invalid pointers; real Thread ABI\n'))
        manifest = {}
        for path in sorted(out.rglob('*')):
            if path.is_file():
                manifest[str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()
        (out / 'artifact-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(result.stdout, end='')


if __name__ == '__main__':
    unittest.main()
