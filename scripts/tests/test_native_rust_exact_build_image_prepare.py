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
    def artifact(path, package):
        return {'path': path, 'target': path, 'owner': package,
                'rpm_nevra': packages[package], 'sha256': 'e' * 64}
    libraries = {}
    for name, spec in prep.LIBRARIES.items():
        package = spec['development_package']
        libraries[name] = {'development_package': package,
                           'linker': artifact(spec['linker']['path'], spec['linker']['owner']),
                           'headers': {header: artifact(header, owner)
                                       for header, owner in spec['headers'].items()}}
    return {'arch': 'x86_64', 'os_release': 'ID="rocky"\nVERSION_ID="10.2"\n',
            'rustc': prep.EXPECTED_RUST, 'packages': packages, 'tools': tools,
            'rpm_verify': {'exit_code': 0, 'stdout': '', 'stderr': ''},
            'rpm_inventory': '\n'.join(inventory), 'libraries': libraries}


class OfflineMismatchDocker(FakeDocker):
    """Use one observation for preparation and another for the offline probe."""
    def __init__(self):
        super().__init__()
        self.probe = probe_fixture()
        self.offline_probe = copy.deepcopy(self.probe)
        self.offline_probe['tools']['make']['sha256'] = 'e' * 64
        self.create_count = 0

    def call(self, args, timeout=120, check=True):
        if args[0] == 'create':
            self.create_count += 1
        if args[0] == 'exec' and self.create_count == 2:
            original, self.probe = self.probe, self.offline_probe
            try:
                return super().call(args, timeout, check)
            finally:
                self.probe = original
        return super().call(args, timeout, check)


class RecordingDocker(FakeDocker):
    instances = []

    def __init__(self, log, signals=None, sudo=False):
        super().__init__()
        self.probe = probe_fixture()
        self.log = log
        self.signals = signals
        self.sudo = sudo
        self.instances.append(self)


class OfflineProfileDocker(FakeDocker):
    def __init__(self):
        super().__init__()
        self.probe = probe_fixture()
        self.create_count = 0

    def call(self, args, timeout=120, check=True):
        result = super().call(args, timeout, check)
        if args[0] == 'create':
            self.create_count += 1
            if self.create_count == 2:
                self.mutate = lambda info: info['HostConfig'].update(NetworkMode='bridge')
        return result


class OfflineUnretirableDocker(FakeDocker):
    def __init__(self):
        super().__init__()
        self.probe = probe_fixture()
        self.create_count = 0

    def call(self, args, timeout=120, check=True):
        result = super().call(args, timeout, check)
        if args[0] == 'create':
            self.create_count += 1
            if self.create_count == 2:
                self.unretirable = self.timeout = True
        return result


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
        self.assertEqual(len(creates), 2)
        self.assertEqual(creates[0][creates[0].index('--name') + 1],
                         creates[1][creates[1].index('--name') + 1])
        self.assertNotIn('--mount', creates[0])
        self.assertIn('--network=bridge', creates[0])
        self.assertIn('--cap-add=' + prep.PREP_CAPS[0], creates[0])
        self.assertIn('--network=none', creates[1])
        self.assertIn('--read-only', creates[1])
        self.assertIn('--user', creates[1])
        self.assertIn('--tmpfs', creates[1])
        self.assertNotIn('--mount', creates[1])
        self.assertFalse(any(arg.startswith('--cap-add=') for arg in creates[1]))
        self.assertEqual(fake.commands[-1], ['rm', creates[1][creates[1].index('--name') + 1]])
        self.assertEqual(json.loads((self.root / 'ev' / 'offline-tool-observation.json').read_text()),
                         fake.probe)
        self.assertTrue((self.root / 'ev' / 'offline-inspect-terminal.json').exists())

    def test_coreutils_single_package_and_dd_owner_contract(self):
        self.assertIn('coreutils-single', prep.PACKAGES)
        self.assertNotIn('coreutils', prep.PACKAGES)
        self.assertEqual(prep.TOOLS['dd'], 'coreutils-single')

    def test_coreutils_substitution_and_dd_owner_drift_fail_closed(self):
        probe = probe_fixture()
        probe['packages']['coreutils'] = probe['packages'].pop('coreutils-single')
        with self.assertRaises(prep.PreparationError):
            prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

        probe = probe_fixture()
        probe['tools']['dd']['owner'] = 'coreutils'
        with self.assertRaises(prep.PreparationError):
            prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

    def test_production_docker_uses_reviewed_sudo_client(self):
        RecordingDocker.instances.clear()
        with mock.patch.object(prep, 'Docker', RecordingDocker):
            result = self.execute(None)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(len(RecordingDocker.instances), 1)
        self.assertTrue(RecordingDocker.instances[0].sudo)

    def test_offline_observation_mismatch_fails_and_preserves_container_log(self):
        fake = OfflineMismatchDocker()
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['retired'])
        self.assertIn('offline tool observation differs', result['error'])
        self.assertTrue((self.root / 'ev' / 'offline-container.log').exists())
        self.assertEqual(sum(command[0] == 'rm' for command in fake.commands), 1)
        self.assertIsNotNone(fake.info)

    def test_offline_profile_mutation_blocks_probe_and_preserves_container(self):
        fake = OfflineProfileDocker()
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('effective limit mismatch: NetworkMode', result['error'])
        starts = [command for command in fake.commands if command[0] == 'start']
        self.assertEqual(len(starts), 1)
        self.assertTrue((self.root / 'ev' / 'offline-container.log').exists())
        self.assertEqual(sum(command[0] == 'rm' for command in fake.commands), 1)

    def test_offline_unproven_retirement_keeps_matching_owner_lease(self):
        fake = OfflineUnretirableDocker()
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['retired'])
        lease = json.loads((self.root / 'lease').read_text())
        self.assertEqual(lease['container_name'], result['owner']['container_name'])
        self.assertEqual(fake.info['Name'], '/' + lease['container_name'])
        creates = [command for command in fake.commands if command[0] == 'create']
        self.assertEqual(creates[0][creates[0].index('--name') + 1],
                         creates[1][creates[1].index('--name') + 1])
        self.assertEqual(sum(command[0] == 'rm' for command in fake.commands), 1)

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
                     lambda p: p['tools']['make'].__setitem__('path', '/tmp/make'),
                     lambda p: p['tools']['make'].__setitem__('target', '/tmp/make'),
                     lambda p: p['libraries'].pop('libudev'),
                     lambda p: p['libraries']['libnuma']['linker'].__setitem__('sha256', '0' * 64),
                     lambda p: p['libraries']['libnuma']['linker'].__setitem__('path', '/usr/bin/cc'),
                     lambda p: p['libraries']['libbfd']['headers'].pop('/usr/include/bfd.h'),
                     lambda p: p['libraries']['libbfd']['headers'].__setitem__('/usr/include/numa.h', {'path': '/usr/include/numa.h', 'target': '/usr/include/numa.h', 'owner': 'numactl-devel', 'rpm_nevra': p['packages']['numactl-devel'], 'sha256': 'e' * 64})]
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

    def test_gpg_pubkey_inventory_identity_allows_none_architecture(self):
        probe = probe_fixture()
        probe['rpm_inventory'] += '\ngpg-pubkey-0:6fedfc85-682ae1a9.(none)'
        prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

    def test_inventory_none_architecture_is_bounded(self):
        for suffix in ('(none', '(none)!', 'none)', '[none]'):
            probe = probe_fixture()
            probe['rpm_inventory'] += '\ngpg-pubkey-0:6fedfc85-682ae1a9.' + suffix
            with self.subTest(suffix=suffix), self.assertRaises(prep.PreparationError):
                prep.validate_probe(probe, {'rust': 'rust-0:1.92.0-1.el10.x86_64'})

    def test_probe_versions_preserve_lookup_argv0_for_multicall_tools(self):
        # ld.lld is commonly a symlink to the generic lld dispatcher.  RPM
        # ownership/hash/NEVRA must use the canonical target, while --version
        # must execute the lookup spelling so argv[0] selects ld.lld mode.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'lld'
            lookup = root / 'ld.lld'
            target.write_text('#!/bin/sh\n')
            lookup.symlink_to(target.name)
            self.assertNotEqual(str(lookup), str(lookup.resolve()))
        self.assertIn("'executable_version':output([path,'--version'])", prep.PROBE)
        self.assertIn("'version':output([path,'--version'])", prep.PROBE)
        self.assertNotIn("'executable_version':output([str(target),'--version'])", prep.PROBE)
        self.assertNotIn("'version':output([str(target),'--version'])", prep.PROBE)

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
