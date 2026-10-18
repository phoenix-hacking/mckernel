"""Bounded actual-body parity for scheduler debug-register handoff; no image/runtime claim."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
FIXTURE = ROOT / 'scripts/tests/fixtures/test_rust_scheduler_debug_handoff_20261018.rs'


class DebugHandoffTests(unittest.TestCase):
    def test_actual_body_and_selected_consumer(self):
        out = Path(os.environ['MCKERNEL_RUST_SCHED_DEBUG_OUTPUT'])
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
            return result.stdout

        files = ['kernel/process.c', 'kernel/rust/sched_helpers.rs', 'kernel/rust/abi.rs',
                 'kernel/CMakeLists.txt', 'kernel/rust/lib.rs', 'kernel/rust/tests/run_equivalence.sh',
                 'kernel/include/process.h', 'arch/x86_64/kernel/syscall.c',
                 str(FIXTURE.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))]
        hashes = {}
        for path in files:
            data = (ROOT / path).read_bytes()
            hashes[path] = hashlib.sha256(data).hexdigest()
            target = out / 'sources' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / 'source-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
        process = (out / 'sources/kernel/process.c').read_text()
        rust = (out / 'sources/kernel/rust/sched_helpers.rs').read_text()
        abi = out / 'sources/kernel/rust/abi.rs'
        schedule = balanced_item(process, 'void schedule(void)')
        start = schedule.index('\t\tif (prev && prev->ptrace_debugreg)')
        end = schedule.index('\n\n', start)
        fallback = '\n'.join(line[1:] for line in schedule[start:end].splitlines())
        self.assertEqual(hashlib.sha256(fallback.encode()).hexdigest(),
                         '2528a59dbb9237c6d35cc4a4fd36bbeced10c508c1864f82d3b9bd4fc4957455')
        selected = '\tsched_schedule_debug_handoff(prev, next);'
        self.assertEqual(schedule.count(selected), 1)
        call = schedule.index(selected)
        self.assertLess(schedule.index('sched_schedule_prepare_body_result('), call)
        self.assertLess(schedule.index('next = (struct thread *)schedule_result.next_thread_addr;'), call)
        self.assertLess(call, schedule.index('restore_fp_regs(next);'))
        self.assertLess(call, schedule.index('arch_switch_context('))
        cmake = (out / 'sources/kernel/CMakeLists.txt').read_text()
        self.assertIn('option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)', cmake)
        self.assertIn('set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/process.c"\n\t\tPROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_HELPERS)', cmake)
        self.assertIn('mod sched_helpers;', (out / 'sources/kernel/rust/lib.rs').read_text())
        for decl in ['fn save_debugreg(debugreg: *mut CULong);', 'fn clear_debugreg();',
                     'fn restore_debugreg(debugreg: *mut CULong);']:
            self.assertIn(decl, rust)
        body = balanced_item(rust, 'pub unsafe extern "C" fn sched_schedule_debug_handoff(')
        (out / 'selected-body.rs').write_text(body + '\n')
        (out / 'frozen-reference.c').write_text(fallback + '\n')
        prefix = '#![no_std]\n#[path=' + json.dumps(str(abi)) + '] mod abi;\n'
        prefix += 'use abi::{Thread,CULong}; use core::ptr::read_volatile;\nextern "C" { fn save_debugreg(p:*mut CULong); fn clear_debugreg(); fn restore_debugreg(p:*mut CULong); }\n#[no_mangle]\n'
        (out / 'actual.rs').write_text(prefix + body + '\n')
        self.assertTrue(run('rust-version', [RUSTC, '--version']).startswith('rustc 1.92.0 '))
        # Determine the real binding offset, then compile the unchanged C block
        # against a layout-checked view of that exact field in the full Thread.
        (out / 'layout.rs').write_text('#[path=' + json.dumps(str(abi)) + '] mod abi;\nfn main(){println!("{} {}",core::mem::offset_of!(abi::Thread,ptrace_debugreg),core::mem::size_of::<abi::Thread>());}\n')
        run('layout-compile', [RUSTC, '--edition=2021', '-Awarnings', str(out / 'layout.rs'), '-o', str(out / 'layout')])
        offset, size = map(int, run('layout', [str(out / 'layout')]).split())
        c = '#include <stddef.h>\nstruct thread { unsigned char prefix[' + str(offset) + ']; unsigned long *ptrace_debugreg; };\n'
        c += '_Static_assert(offsetof(struct thread,ptrace_debugreg)==' + str(offset) + ',"debugreg offset");\n'
        c += 'extern void save_debugreg(unsigned long *); extern void clear_debugreg(void); extern void restore_debugreg(unsigned long *);\nextern void sched_schedule_debug_handoff(struct thread *,struct thread *);\nextern void observe_prepare(void); extern void observe_fp_restore(void);\n'
        c += 'void reference(struct thread *prev,struct thread *next) {\n' + fallback + '\n}\n'
        c += 'void consumer(struct thread *prev,struct thread *next) { observe_prepare();\n#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n' + selected + '\n#else\n' + fallback + '\n#endif\nobserve_fp_restore();\n}\n'
        (out / 'consumer.c').write_text(c)
        flags = ['panic=abort', 'opt-level=2', 'debuginfo=2', 'code-model=large',
                 'relocation-model=static', 'no-redzone=yes', 'force-frame-pointers=yes',
                 'overflow-checks=off', 'force-unwind-tables=no', 'no-vectorize-loops',
                 'no-vectorize-slp', 'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        recipe = (out / 'sources/kernel/rust/tests/run_equivalence.sh').read_text()
        for flag in flags:
            self.assertIn('-C ' + flag, recipe)
        run('rust-object', [RUSTC, '--edition=2021', '--crate-type=lib', '-Awarnings'] +
            [part for flag in flags for part in ['-C', flag]] +
            ['--emit=obj', str(out / 'actual.rs'), '-o', str(out / 'actual.o')])
        for name, defines in [('selected', ['-DMCKERNEL_RUST_PROCESS_HELPERS']), ('fallback', [])]:
            run(name + '-object', ['/usr/bin/gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-c'] +
                defines + [str(out / 'consumer.c'), '-o', str(out / (name + '.o'))])
            symbols = run(name + '-nm', ['/usr/bin/nm', str(out / (name + '.o'))])
            if name == 'selected':
                self.assertRegex(symbols, r'\bU sched_schedule_debug_handoff\b')
            else:
                self.assertNotIn('sched_schedule_debug_handoff', symbols)
            run(name + '-disassembly', ['/usr/bin/objdump', '-dr', str(out / (name + '.o'))])
        run('rust-nm', ['/usr/bin/nm', str(out / 'actual.o')])
        dis = run('rust-disassembly', ['/usr/bin/objdump', '-dr', str(out / 'actual.o')])
        self.assertNotRegex(dis, r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b')
        fixture = FIXTURE.read_text().replace('// REAL_SCHED_ABI', '#[path=' + json.dumps(str(abi)) + '] mod abi;')
        (out / 'fixture.rs').write_text(fixture)
        for name in ['selected', 'fallback']:
            run(name + '-fixture-compile', [RUSTC, '--edition=2021', '-Awarnings', '-C', 'panic=abort', '-C', 'opt-level=1',
                '-C', 'link-arg=-no-pie', '-C', 'link-arg=' + str(out / (name + '.o')),
                '-C', 'link-arg=' + str(out / 'actual.o'), str(out / 'fixture.rs'), '-o', str(out / (name + '-fixture'))])
            result = run(name + '-parity', [str(out / (name + '-fixture'))])
            self.assertIn('PASS 216 cases', result)
        (out / 'layout.json').write_text(json.dumps({'ptrace_debugreg_offset': offset, 'thread_size': size}) + '\n')
        manifest = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
        (out / 'artifact-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('PASS actual-body C/Rust parity, selected/fallback consumers; source-only')


if __name__ == '__main__':
    unittest.main()
