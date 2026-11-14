"""Run actual drain/open bodies with deterministic std/Linux-boundary substitutes.

No module, physical CPU release or native lifecycle acceptance is claimed.
"""
from pathlib import Path
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'host-kernel/native-rust'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


def generated():
    pager = (NATIVE / 'smp_file_pager.rs').read_text()
    procfs = (NATIVE / 'smp_procfs.rs').read_text()
    memory = (NATIVE / 'sysfs_memory.rs').read_text()
    template = (ROOT / 'scripts/tests/fixtures/native_shutdown_drain_helpers_20261017.rs').read_text()
    # Scope each duplicate method name to its own production implementation.
    replacements = {
        'PAGER_CHECK': balanced_item(pager[pager.index('impl Registry {'):], 'pub(crate) fn shutdown_quiescent('),
        'MEMORY_CHECK': balanced_item(memory[memory.index('impl Memory {'):], 'pub(super) fn shutdown_quiescent('),
        'LEDGER': balanced_item(memory, 'struct Ledger {'),
        'REMOTE_CHECK': balanced_item(procfs, 'pub(super) fn close_if_quiescent('),
        'REMOTE_OPEN': balanced_item(procfs, 'fn open('),
        'SLOT': balanced_item(procfs, 'struct Slot {'),
        'SLOT_DROP': balanced_item(procfs, 'impl Drop for Slot {'),
        'CONTEXT': balanced_item(procfs, 'struct Context {'),
        'SERVICE_CHECK': balanced_item(procfs[procfs.index('impl Service {'):], 'pub(super) fn shutdown_quiescent('),
    }
    for marker, body in sorted(replacements.items(), key=lambda item: -len(item[0])):
        template = template.replace('// PRODUCTION_' + marker, body)
    return template


class DrainHelperTests(unittest.TestCase):
    def test_actual_bodies(self):
        output = Path(os.environ['MCKERNEL_DRAIN_HELPERS_OUTPUT'])
        output.mkdir(exist_ok=False)
        source = generated()
        self.assertNotIn('// PRODUCTION_', source)
        (output / 'actual.rs').write_text(source)
        compile_result = subprocess.run([RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings', str(output / 'actual.rs'), '-o', str(output / 'actual')], capture_output=True, text=True, timeout=30)
        for stream in ('stdout', 'stderr'):
            (output / f'compile.{stream}').write_text(getattr(compile_result, stream))
        (output / 'compile.status').write_text(str(compile_result.returncode) + '\n')
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
        result = subprocess.run([str(output / 'actual'), '--test-threads=1'], capture_output=True, text=True, timeout=20)
        for stream in ('stdout', 'stderr'):
            (output / f'run.{stream}').write_text(getattr(result, stream))
        (output / 'run.status').write_text(str(result.returncode) + '\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('7 passed; 0 failed', result.stdout)
        print(result.stdout)


if __name__ == '__main__':
    unittest.main()
