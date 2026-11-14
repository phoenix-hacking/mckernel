"""Compile exact production allocate body with distinct Arc allocator/kernel errors."""
from pathlib import Path
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'host-kernel/native-rust/smp_memory.rs'
FIXTURE = ROOT / 'scripts/tests/fixtures/native_boot_epoch_allocate_error_20261017.rs'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


class BootEpochAllocateTests(unittest.TestCase):
    def test_actual_allocate_and_original_type_mismatch(self):
        directory = Path(os.environ['MCKERNEL_BOOT_EPOCH_ALLOCATE_OUTPUT'])
        directory.mkdir(exist_ok=False)
        body = balanced_item(SOURCE.read_text(), 'fn allocate() -> Result<Arc<Self>> {')
        source = FIXTURE.read_text().replace('// PRODUCTION_ALLOCATE', body)
        self.assertNotIn('// PRODUCTION_', source)
        for name, content, expected in [('actual', source, 0), ('original', source.replace(
                'Ok(Arc::new(Self { id, shutdown: AtomicU32::new(SHUTDOWN_OPEN) }, GFP_KERNEL)?)',
                'Arc::new(Self { id, shutdown: AtomicU32::new(SHUTDOWN_OPEN) }, GFP_KERNEL)', 1), 1)]:
            with self.subTest(variant=name):
                if name == 'original':
                    self.assertNotEqual(source, content)
                path = directory / f'{name}.rs'
                path.write_text(content)
                command = [RUSTC, '--edition=2021', '--test', '-W', 'rust_2018_idioms', '-Dwarnings',
                           str(path), '-o', str(directory / name)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                for stream in ('stdout', 'stderr'):
                    (directory / f'{name}.compile.{stream}').write_text(getattr(result, stream))
                (directory / f'{name}.compile.status').write_text(str(result.returncode) + '\n')
                self.assertEqual(result.returncode, expected, result.stderr)
                if name == 'original':
                    self.assertIn('error[E0308]', result.stderr)
                    self.assertIn('AllocError', result.stderr)
                    print(result.stderr)
                    continue
                run = subprocess.run([str(directory / name), '--test-threads=1'],
                                     capture_output=True, text=True, timeout=20)
                for stream in ('stdout', 'stderr'):
                    (directory / f'{name}.run.{stream}').write_text(getattr(run, stream))
                (directory / f'{name}.run.status').write_text(str(run.returncode) + '\n')
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertIn('3 passed; 0 failed', run.stdout)
                print(run.stdout)


if __name__ == '__main__':
    unittest.main()
