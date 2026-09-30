import copy
import json
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_build_image_prepare as prep
import native_rust_exact_build_container_owner as owner
from scripts.tests.test_native_rust_exact_build_container_owner import FakeDocker, IMAGE, signal_regression


def probe_fixture():
    packages = {p: p + '-0:1-1.el10.x86_64' for p in prep.PACKAGES}
    packages.update(cmake=prep.PINNED_CMAKE, rust='rust-0:1.92.0-1.el10.x86_64',
                    kmod='kmod-0:31-13.el10.x86_64')
    inventory = list(packages.values()) + ['rpm-0:4.19.1.1-23.el10.x86_64']
    tools = {n: {'path': '/usr/bin/' + n, 'target': '/usr/bin/' + n,
                 'owner': p, 'rpm_nevra': next(x for x in inventory if x.startswith(p + '-0:')),
                 'executable_version': n + ' fixture --version',
                 'sha256': 'd' * 64} for n, p in prep.TOOLS.items()}
    tools['kmod']['sha256'] = prep.KMOD_SHA
    return {'arch': 'x86_64', 'os_release': 'ID="rocky"\nVERSION_ID="10.2"\n',
            'rustc': prep.EXPECTED_RUST, 'packages': packages, 'tools': tools,
            'rpm_verify': {'exit_code': 0, 'stdout': '', 'stderr': ''},
            'rpm_inventory': '\n'.join(inventory)}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lock = self.root / 'toolchain.json'
        self.lock.write_text(json.dumps({'direct_artifacts': [
            {'name': 'rust', 'nevra': 'rust-0:1.92.0-1.el10.x86_64'}]}))
        self.args = dict(candidate_sha='a' * 40, output_root=self.root / 'out',
                         evidence_root=self.root / 'ev', lease_path=self.root / 'lease',
                         toolchain_lock=self.lock)

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, fake):
        original = owner.Path.read_text
        with mock.patch.object(owner.shutil, 'disk_usage', return_value=SimpleNamespace(free=64 * 2**30)), \
             mock.patch.object(owner.Path, 'read_text', lambda p, *a, **kw:
                 'MemAvailable: 33554432 kB\n' if str(p) == '/proc/meminfo' else original(p, *a, **kw)):
            path = prep.prepare(**self.args, runner=fake)
        return json.loads(path.read_text())

    def test_positive_source_free_image_actual_readbacks(self):
        fake = FakeDocker()
        fake.probe = probe_fixture()
        result = self.execute(fake)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['image_id'], IMAGE)
        self.assertTrue(result['source_free'])
        self.assertFalse((self.root / 'lease').exists())
        creates = [c for c in fake.commands if c[0] == 'create']
        self.assertEqual(len(creates), 1)
        self.assertNotIn('--mount', creates[0])
        self.assertEqual(fake.commands[-1][0], 'rm')

    def test_wrong_runtime_evidence_fails_closed(self):
        for key, value in [('arch', 'aarch64'), ('rustc', 'rustc 1.92.0 forged'),
                           ('os_release', 'ID=fedora\nVERSION_ID=10.2')]:
            probe = probe_fixture()
            probe[key] = value
            with self.subTest(key=key), self.assertRaises(prep.PreparationError):
                prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

    def test_rpm_tool_and_inventory_mutations(self):
        mutations = [lambda p: p['packages'].pop('make'),
                     lambda p: p['rpm_verify'].__setitem__('exit_code', 1),
                     lambda p: p['packages'].__setitem__('rust', 'rust-0:1.91.0-1.el10.x86_64'),
                     lambda p: p.__setitem__('rpm_inventory', ''),
                     lambda p: p.__setitem__('rpm_inventory', p['rpm_inventory'] + '\n' + next(iter(p['packages'].values()))),
                     lambda p: p['tools']['rustc'].__setitem__('owner', 'wrong'),
                     lambda p: p['tools']['cmake'].__setitem__('rpm_nevra', 'cmake-1:3.31.8-1.el10.x86_64'),
                     lambda p: p['tools']['cmake'].__setitem__('executable_version', ''),
                     lambda p: p['tools']['kmod'].__setitem__('sha256', '0' * 64),
                     lambda p: p['tools']['make'].__setitem__('path', '/tmp/make')]
        for mutation in mutations:
            probe = probe_fixture()
            mutation(probe)
            with self.assertRaises(prep.PreparationError):
                prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

    def test_nonzero_epoch_nevra_is_parsed_and_bound(self):
        probe = probe_fixture()
        probe['packages']['cmake'] = prep.PINNED_CMAKE.replace('-0:', '-7:')
        probe['rpm_inventory'] = probe['rpm_inventory'].replace(prep.PINNED_CMAKE,
                                                                  probe['packages']['cmake'])
        probe['tools']['cmake']['rpm_nevra'] = probe['packages']['cmake']
        prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

    def test_failed_probe_retired_and_preserved(self):
        fake = FakeDocker()
        fake.probe = probe_fixture()
        fake.probe['rustc'] = 'wrong'
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['retired'])
        self.assertIsNotNone(fake.info)
        self.assertFalse(any(c[0] == 'commit' for c in fake.commands))

    def test_unproven_retirement_keeps_lease(self):
        fake = FakeDocker()
        fake.probe = probe_fixture()
        fake.unretirable = fake.timeout = True
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['retired'])
        self.assertTrue((self.root / 'lease').exists())

    def test_profile_mount_mutation_blocks_bootstrap(self):
        fake = FakeDocker()
        fake.mutate = lambda info: info['Mounts'].append({'Source': '/src'})
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(any(c[0] == 'start' for c in fake.commands))

    def test_wrong_base_rejected_without_docker(self):
        with self.assertRaises(prep.PreparationError):
            prep.prepare(**self.args, base_image='rocky:latest')

    def test_real_preparation_sigterm_preserves_dnf_bytes_and_receipt(self):
        signal_regression(self, self.root, 'prepare',
                          {k: str(v) for k, v in self.args.items()}, signal.SIGTERM)

    def test_real_preparation_sigint_preserves_dnf_bytes_and_receipt(self):
        signal_regression(self, self.root, 'prepare',
                          {k: str(v) for k, v in self.args.items()}, signal.SIGINT)

    def test_real_preparation_sigkill_preserves_emitted_bytes(self):
        signal_regression(self, self.root, 'prepare',
                          {k: str(v) for k, v in self.args.items()}, signal.SIGKILL)

    def test_real_preparation_signal_retains_unproven_lease(self):
        signal_regression(self, self.root, 'prepare-hold',
                          {k: str(v) for k, v in self.args.items()}, signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
