"""Actual scheduler FPU admission Rust body versus the corrected C prelude.

Retains every command and stream. This is source-bound cheap object/behavior
verification; full image linking and native runtime remain separate gates.
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
FIXTURE = ROOT / 'scripts/tests/fixtures/rust_scheduler_fp_admission_20261018.rs'


class RustSchedulerFpAdmissionTests(unittest.TestCase):
    def test_actual_admission_and_default_selection(self):
        out = Path(os.environ['MCKERNEL_RUST_SCHED_ADMISSION_OUTPUT'])
        out.mkdir(exist_ok=False)
        commands = []

        def run(label, argv, expected=0):
            commands.append({'label': label, 'argv': argv, 'expected_status': expected})
            (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            for stream in ['stdout', 'stderr']:
                (out / (label + '.' + stream)).write_text(getattr(result, stream))
            (out / (label + '.status')).write_text(str(result.returncode) + '\n')
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            return result

        paths = ['kernel/process.c', 'kernel/rust/sched_helpers.rs', 'kernel/rust/abi.rs',
                 'kernel/rust/atomic_helpers.rs', 'kernel/rust/process_helpers.rs',
                 'kernel/rust/abort.rs', 'lib/include/ihk/debug.h', 'kernel/include/process.h',
                 'kernel/rust/lib.rs', 'kernel/CMakeLists.txt',
                 'kernel/rust/tests/run_equivalence.sh', str(FIXTURE.relative_to(ROOT)),
                 'scripts/tests/test_rust_scheduler_fp_admission_20261018.py']
        hashes = {}
        for relative in paths:
            data = (ROOT / relative).read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            target = out / 'sources' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / 'source-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
        process = (out / 'sources/kernel/process.c').read_text()
        rust = (out / 'sources/kernel/rust/sched_helpers.rs').read_text()
        abi = out / 'sources/kernel/rust/abi.rs'
        cmake = (out / 'sources/kernel/CMakeLists.txt').read_text()
        self.assertIn('option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)', cmake)
        self.assertIn('set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/process.c"\n\t\tPROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_HELPERS)', cmake)
        self.assertIn('mod sched_helpers;', (out / 'sources/kernel/rust/lib.rs').read_text())
        self.assertIn('fn panic(message: *const i8) -> !;', rust)
        self.assertIn('fn save_fp_regs(thread: *mut core::ffi::c_void) -> CInt;', rust)
        self.assertIn('fn process_sched_irq_save_bridge() -> CULong;', rust)
        atomic = (out / 'sources/kernel/rust/atomic_helpers.rs').read_text()
        self.assertIn('(*v).counter.load(Ordering::SeqCst)',
                      balanced_item(atomic, 'pub unsafe extern "C" fn ihk_atomic_read('))
        schedule = balanced_item(process, 'void schedule(void)')
        start = schedule.index('#ifdef MCKERNEL_RUST_PROCESS_HELPERS')
        end = schedule.index('\n#endif', start) + len('\n#endif')
        selection = schedule[start:end]
        fallback = selection.split('#else\n', 1)[1].removesuffix('\n#endif')
        # Frozen corrected production prelude; no edited/reimplemented oracle.
        self.assertEqual(hashlib.sha256(fallback.encode()).hexdigest(), 'f42dcd3065a0c5f56bfd780b06579085db6629b47344084092b3d6fc8c12a2f3')
        self.assertEqual(schedule.count('sched_schedule_fp_admit(PS_EXITED)'), 1)
        self.assertLess(schedule.index('sched_schedule_fp_admit(PS_EXITED)'), schedule.index('sched_schedule_prepare_body_result('))
        self.assertIn('cpu_restore_interrupt(irqstate);\n\t\treturn;', schedule)
        self.assertIn('v->runq_irqstate = irqstate;', schedule)
        statuses = (out / 'sources/kernel/include/process.h').read_text()
        self.assertRegex(statuses, r'#define\s+PS_EXITED\s+0x10\b')
        panic_header = (out / 'sources/lib/include/ihk/debug.h').read_text()
        self.assertIn('void panic(const char *);', panic_header)
        c_source = '''#include <stddef.h>
#define PS_EXITED 0x10
struct thread { unsigned char prefix[4184]; int status; unsigned char suffix[1380]; } __attribute__((aligned(64)));
struct atomic_count { int counter; };
struct cpu_local_var { unsigned char prefix[64]; struct thread idle; unsigned char middle[2216]; struct thread *current; unsigned char gap[120]; struct atomic_count no_preempt; unsigned char suffix[148]; } __attribute__((aligned(64)));
_Static_assert(sizeof(struct thread)==5568, "Thread size");
_Static_assert(sizeof(struct cpu_local_var)==8128, "CpuLocalVar size");
_Static_assert(offsetof(struct cpu_local_var,current)==7848, "current offset");
_Static_assert(offsetof(struct cpu_local_var,no_preempt)==7976, "no_preempt offset");
extern unsigned long cpu_disable_interrupt_save(void);
extern struct cpu_local_var *get_this_cpu_local_var(void);
extern int save_fp_regs(struct thread *);
extern void panic(const char *) __attribute__((noreturn));
extern void observe_prepare(void);
extern unsigned long sched_schedule_fp_admit(int exited_status);
static int ihk_atomic_read(const struct atomic_count *v) { return __atomic_load_n(&v->counter,__ATOMIC_SEQ_CST); }
unsigned long reference_admit(void) { struct thread *prev; unsigned long irqstate;
'''
        c_source += fallback + '\nobserve_prepare(); return irqstate; }\n'
        c_source += 'unsigned long selected_admit(void) { struct thread *prev; unsigned long irqstate; (void)prev;\n'
        c_source += selection + '\nobserve_prepare(); return irqstate; }\n'
        (out / 'actual_admission.c').write_text(c_source)
        body = balanced_item(rust, 'pub unsafe extern "C" fn sched_schedule_fp_admit(')
        rust_source = '#![no_std]\n#[path=' + json.dumps(str(abi)) + '] mod abi;\n'
        rust_source += '''use abi::{CpuLocalVar,CInt,CULong};
use core::ptr::read_volatile;
use core::sync::atomic::{AtomicI32,Ordering};
extern "C" {
 fn process_sched_irq_save_bridge()->CULong;
 fn ihk_mc_get_processor_id()->CInt;
 fn process_sched_cpu_local_bridge(cpu:CInt)->usize;
 fn save_fp_regs(thread:*mut core::ffi::c_void)->CInt;
 fn panic(message:*const i8)->!;
}
#[no_mangle]
'''
        rust_source += body + '\n'
        (out / 'actual_admission.rs').write_text(rust_source)
        version = run('rust-version', [RUSTC, '--version'])
        self.assertTrue(version.stdout.startswith('rustc 1.92.0 '))
        flags = ['panic=abort', 'opt-level=2', 'debuginfo=2', 'code-model=large',
                 'relocation-model=static', 'no-redzone=yes', 'force-frame-pointers=yes',
                 'overflow-checks=off', 'force-unwind-tables=no', 'no-vectorize-loops',
                 'no-vectorize-slp', 'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        recipe = (out / 'sources/kernel/rust/tests/run_equivalence.sh').read_text()
        for flag in flags:
            self.assertIn('-C ' + flag, recipe)
        kernel_flags = [part for flag in flags for part in ['-C', flag]]
        run('rust-object', [RUSTC, '--edition=2021', '--crate-type=lib'] + kernel_flags +
            ['--emit=obj', str(out / 'actual_admission.rs'), '-o', str(out / 'actual_admission.o')])
        for name, defines in [('selected', ['-DMCKERNEL_RUST_PROCESS_HELPERS']), ('fallback', [])]:
            run(name + '-object', ['/usr/bin/gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-c'] +
                defines + [str(out / 'actual_admission.c'), '-o', str(out / (name + '.o'))])
        selected_nm = run('selected-symbols', ['/usr/bin/nm', str(out / 'selected.o')]).stdout
        fallback_nm = run('fallback-symbols', ['/usr/bin/nm', str(out / 'fallback.o')]).stdout
        self.assertRegex(selected_nm, r'\bU sched_schedule_fp_admit\b')
        self.assertNotIn('sched_schedule_fp_admit', fallback_nm)
        disassembly = run('rust-disassembly', ['/usr/bin/objdump', '-dr', str(out / 'actual_admission.o')]).stdout
        self.assertNotRegex(disassembly, r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b')
        fixture = FIXTURE.read_text().replace('// REAL_SCHED_ABI', '#[path=' + json.dumps(str(abi)) + '] mod abi;')
        (out / 'fixture.rs').write_text(fixture)
        run('fixture-compile', [RUSTC, '--edition=2021', '-C', 'panic=abort', '-C', 'opt-level=1',
            '-C', 'link-arg=-no-pie', '-C', 'link-arg=' + str(out / 'selected.o'),
            '-C', 'link-arg=' + str(out / 'actual_admission.o'), str(out / 'fixture.rs'), '-o', str(out / 'fixture')])
        for case in range(8):
            for enabled in [0, 1]:
                results = []
                for variant in ['c', 'rust']:
                    result = run(f'case-{case}-{enabled}-{variant}', [str(out / 'fixture'), variant, str(case), str(enabled)], 77 if case == 6 else 0)
                    self.assertEqual(result.stderr, '')
                    results.append(result.stdout)
                self.assertEqual(*results)
        manifest = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
        (out / 'artifact-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('PASS 16 C/Rust parity cases, including 2 fail-stop children; actual Thread/CpuLocalVar ABI; default C selection')


if __name__ == '__main__':
    unittest.main()
