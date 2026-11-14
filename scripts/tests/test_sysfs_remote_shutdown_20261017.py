"""Execute production sysfs Remote methods; std synchronization substitutes Linux.

No hardware, Linux sysfs drain, module or application acceptance is claimed.
"""
from pathlib import Path
import os
import subprocess
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
from scripts.tests.test_native_shutdown_epoch_source_20261017_1 import generated as epoch_generated

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'host-kernel/native-rust'
FIXTURE = ROOT / 'scripts/tests/fixtures/sysfs_remote_shutdown_20261017.rs'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
METHODS = ('pub(crate) fn shutdown_after_peer_stop(', 'pub(crate) fn shutdown_drained(',
           'pub(crate) fn publish(', 'pub(crate) fn queued(', 'pub(crate) fn reply(', 'fn call(')


def generated():
    source = (NATIVE / 'sysfs_remote.rs').read_text()
    client = balanced_item((NATIVE / 'abi/sysfs_request.rs').read_text(), 'pub(crate) struct Client {')
    peer = (balanced_item(source,"pub(crate) struct PeerStopped<'boot>") + '\n'
            + balanced_item(source,"impl<'boot> PeerStopped<'boot>"))
    remote = (FIXTURE.read_text().replace('#![allow(dead_code)]','')
            .replace('// PRODUCTION_CLIENT', '#[derive(Clone, Copy, Debug, Eq, PartialEq)]\n' + client)
            .replace('// PRODUCTION_RPC', (NATIVE / 'sysfs_rpc.rs').read_text().replace('//!', '//'))
            .replace('// PRODUCTION_STATE', peer + '\n' + balanced_item(source, 'struct State {'))
            .replace('// PRODUCTION_ERRNO', balanced_item(source, 'fn errno('))
            .replace('// PRODUCTION_METHODS', '\n'.join(balanced_item(source, marker) for marker in METHODS))
            .replace('// PRODUCTION_ATTRIBUTE', balanced_item(source, 'pub(crate) struct Attribute {'))
            .replace('// PRODUCTION_DROP', balanced_item(source, 'impl Drop for Attribute {')))
    epoch = epoch_generated()
    return epoch.replace(balanced_item(epoch,'mod sysfs_remote {'),'mod sysfs_remote {\n'+remote+'\n}')


class SysfsRemoteShutdownTests(unittest.TestCase):
    def test_actual_bodies(self):
        directory = Path(os.environ['MCKERNEL_SHUTDOWN_TEST_OUTPUT'])
        directory.mkdir(exist_ok=False)
        from scripts.tests.test_native_shutdown_integration_source_20261017_1 import generated as current_generated
        source = current_generated()
        self.assertNotIn('// PRODUCTION_', source)
        (directory / 'actual.rs').write_text(source)
        compile_result = subprocess.run([RUSTC, '--edition=2021', '--test', '-Wrust_2018_idioms', '-Dwarnings',
                                         str(directory / 'actual.rs'), '-o', str(directory / 'actual')],
                                        capture_output=True, text=True, timeout=30)
        for stream in ('stdout', 'stderr'):
            (directory / f'compile.{stream}').write_text(getattr(compile_result, stream))
        (directory / 'compile.status').write_text(str(compile_result.returncode) + '\n')
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
        result = subprocess.run([str(directory / 'actual'), '--test-threads=1', 'sysfs_remote::'],
                                capture_output=True, text=True, timeout=20)
        for stream in ('stdout', 'stderr'):
            (directory / f'run.{stream}').write_text(getattr(result, stream))
        (directory / 'run.status').write_text(str(result.returncode) + '\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('4 passed; 0 failed', result.stdout)
        print(result.stdout)


if __name__ == '__main__':
    unittest.main()
