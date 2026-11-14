"""Actual production worker entry/run/activation/join/drop with mock task boundary."""
from pathlib import Path
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'host-kernel/native-rust/smp_service.rs'
FIXTURE = ROOT / 'scripts/tests/fixtures/native_service_worker_stop_20261017.rs'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


def generated():
    source = SOURCE.read_text()
    items = ['#[derive(Clone, Copy)]\n' + balanced_item(source, 'enum Role {')]
    for marker in ('struct Entry {', 'unsafe extern "C" fn run(', 'struct Thread {',
                   'unsafe impl Send for Thread {}', 'unsafe impl Sync for Thread {}', 'impl Drop for Thread {'):
        items.append(balanced_item(source, marker))
    items += [line for line in source.splitlines() if line.startswith('const THREAD_')]
    return FIXTURE.read_text().replace('// PRODUCTION_ITEMS', '\n'.join(items)).replace(
        '// PRODUCTION_METHODS', '\n'.join(balanced_item(source, marker) for marker in ('fn activate(&self)', 'fn stop_join(&self)')))


class WorkerStopTests(unittest.TestCase):
    def test_actual_worker_bodies(self):
        directory = Path(os.environ['MCKERNEL_WORKER_STOP_OUTPUT'])
        directory.mkdir(exist_ok=False)
        source = generated()
        self.assertNotIn('// PRODUCTION_', source)
        (directory / 'actual.rs').write_text(source)
        commands = [('compile', [RUSTC, '--edition=2021', '--test', '-Dwarnings', str(directory / 'actual.rs'), '-o', str(directory / 'actual')]),
                    ('run', [str(directory / 'actual'), '--test-threads=1'])]
        for name, command in commands:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            for stream in ('stdout', 'stderr'):
                (directory / f'{name}.{stream}').write_text(getattr(result, stream))
            (directory / f'{name}.status').write_text(str(result.returncode) + '\n')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            if name == 'run':
                self.assertIn('5 passed; 0 failed', result.stdout)
                print(result.stdout)


if __name__ == '__main__':
    unittest.main()
