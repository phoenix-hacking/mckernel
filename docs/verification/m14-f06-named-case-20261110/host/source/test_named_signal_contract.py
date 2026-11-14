"""Seven HOST unit contracts only; never a native or executable guest manifest."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

SIGNAL = '/apps/signal.alternate-repeat'
PREFIX = ['/bin/mcexec', '-t', '1', '0']
ENV = {'PATH': '/usr/bin:/bin', 'COKERNEL_PATH': '/apps'}
SIGNAL_ENV = dict(ENV, LANG='C', LC_ALL='C', TZ='UTC')
NAMES = ('apps', 'case', 'case/work', 'init', 'apps/signal.alternate-repeat', 'bin/mcexec')


def load(name, path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('exact reviewed source bytes changed')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference_base():
    # Independent Linux newc fixture containing only the required bin parent.
    # No old native fixture, boot code, kernel, module or guest is executed.
    def row(name, mode, links):
        encoded = name.encode() + b'\0'
        fields = (0, mode, 0, 0, links, 0, 0, 0, 0, 0, 0, len(encoded), 0)
        value = b'070701' + ''.join('{:08x}'.format(x) for x in fields).encode() + encoded
        return value + b'\0' * (-len(value) % 4)
    raw = row('bin', stat.S_IFDIR | 0o755, 2) + row('TRAILER!!!', 0, 1)
    return raw + b'\0' * (-len(raw) % 512)


class ReachedStaging(Exception):
    pass


class NamedSignalContract(unittest.TestCase):
    def manifest(self, path, environment, tail=()):
        # _ref and _staging are isolated I/O boundaries in the payload unit
        # tests. These symbolic references are deliberately not valid artifacts
        # and never leave this unittest or become native admission evidence.
        return {'schema_version': 1, 'kind': 'native-diagnostic-manifest',
                'case_id': 'HOST_UNIT_ONLY_NOT_EXECUTABLE',
                'artifacts': {name: {'path': '/unit/' + name} for name in d.ARTIFACTS},
                'modules': [{'path': '/unit/' + name} for name in d.MODULE_NAMES],
                'staging': {}, 'profile': {'memory_mib': 8192, 'vcpus': 4, 'numa_nodes': 2},
                'payload': {'cwd': '/case/work', 'argv': PREFIX + [path] + list(tail),
                            'env': environment, 'oracle': {'stdout_hex': '', 'stderr_hex': '', 'exit_code': 0},
                            'stdout_limit_bytes': 1024, 'stderr_limit_bytes': 0}}

    def reaches_staging(self, manifest, member):
        with mock.patch.object(d, '_ref', side_effect=lambda value, name: value), \
                mock.patch.object(d, '_staging', side_effect=ReachedStaging) as staging:
            with self.assertRaises(ReachedStaging):
                d._validate_manifest(manifest)
            self.assertEqual(staging.call_args.kwargs['payload_member'], member)

    def rejects_payload(self, manifest):
        with mock.patch.object(d, '_ref', side_effect=lambda value, name: value), \
                mock.patch.object(d, '_staging', side_effect=AssertionError('invalid payload reached staging')):
            with self.assertRaises(d.DiagnosticError):
                d._validate_manifest(manifest)

    def test_exact_signal_argv_and_no_tail(self):
        self.assertEqual(d._validate_payload_argv(PREFIX + [SIGNAL]), PREFIX + [SIGNAL])
        with self.assertRaises(d.DiagnosticError):
            d._validate_payload_argv(PREFIX + [SIGNAL, 'extra'])
        with self.assertRaises(d.DiagnosticError):
            d._validate_payload_argv(PREFIX + ['/apps/other'])

    def test_exact_signal_environment_and_selected_member(self):
        self.reaches_staging(self.manifest(SIGNAL, SIGNAL_ENV), 'apps/signal.alternate-repeat')
        for key in ('LANG', 'LC_ALL', 'TZ'):
            missing = dict(SIGNAL_ENV)
            del missing[key]
            with self.subTest(missing=key):
                self.rejects_payload(self.manifest(SIGNAL, missing))
        self.rejects_payload(self.manifest(SIGNAL, dict(SIGNAL_ENV, LC_ALL='en_US.UTF-8')))
        self.rejects_payload(self.manifest(SIGNAL, dict(SIGNAL_ENV, EXTRA='1')))

    def test_legacy_paths_keep_legacy_environment(self):
        for path in ('app', '/apps/app'):
            with self.subTest(path=path):
                self.reaches_staging(self.manifest(path, ENV), 'apps/app')
                self.rejects_payload(self.manifest(path, SIGNAL_ENV))

    def overlay(self, member=None):
        temporary = tempfile.TemporaryDirectory(prefix='named-signal-host-', dir=args.work_root)
        self.addCleanup(temporary.cleanup)
        parent = Path(temporary.name)
        cpio = reference_base()
        packed = gzip.compress(cpio, mtime=0)
        base = parent / 'base.cpio.gz'
        base.write_bytes(packed)
        output = parent / 'derived.cpio.gz'
        pins = {'base_sha256': hashlib.sha256(packed).hexdigest(), 'base_size': len(packed),
                'base_cpio_sha256': hashlib.sha256(cpio).hexdigest(), 'base_cpio_size': len(cpio)}
        options = {} if member is None else {'payload_member': member}
        result = o.build_overlay(str(base), args.payload, args.collector, args.mcexec, str(output),
                                 collector_sha256=hashlib.sha256(Path(args.collector).read_bytes()).hexdigest(),
                                 mcexec_sha256=hashlib.sha256(Path(args.mcexec).read_bytes()).hexdigest(),
                                 payload_sha256='77e8dfe6f8089f18b22524ad474e057cb061d67501f9e9fdb4f391dd4790f45d',
                                 **pins, **options)
        raw = gzip.decompress(output.read_bytes())
        self.assertEqual(raw[:len(cpio)], cpio)
        return result, packed, raw[len(cpio):], pins

    def test_named_overlay_physical_member_and_replay(self):
        result, base, overlay, pins = self.overlay('apps/signal.alternate-repeat')
        records, _ = o.parse_newc(overlay)
        self.assertEqual(tuple(row['name'] for row in records), NAMES)
        self.assertNotIn('apps/app', result['final_map'])
        self.assertEqual(result['final_map']['apps/signal.alternate-repeat']['sha256'],
                         '77e8dfe6f8089f18b22524ad474e057cb061d67501f9e9fdb4f391dd4790f45d')
        self.assertEqual(o.replay(base, overlay, payload_member='apps/signal.alternate-repeat', **pins),
                         result['final_map'])
        with self.assertRaises(o.OverlayError):
            o.replay(base, overlay, **pins)

    def test_default_overlay_still_apps_app(self):
        result, base, overlay, pins = self.overlay()
        records, _ = o.parse_newc(overlay)
        self.assertEqual(tuple(row['name'] for row in records),
                         ('apps', 'case', 'case/work', 'init', 'apps/app', 'bin/mcexec'))
        self.assertNotIn('apps/signal.alternate-repeat', result['final_map'])
        self.assertEqual(o.replay(base, overlay, **pins), result['final_map'])

    def test_unsupported_overlay_member_rejected(self):
        with self.assertRaises(o.OverlayError):
            o._overlay_names('apps/other')

    def test_actual_c_serializer_literal_binding(self):
        raw = Path(args.serializer_report).read_bytes()
        self.assertTrue(raw.startswith(b'ND_PAYLOAD '))
        self.assertEqual(raw.count(b'\n'), 1)
        value = json.loads(raw[len(b'ND_PAYLOAD '):])
        self.assertEqual(value['argv'], PREFIX + [SIGNAL])
        self.assertEqual(value['cwd'], '/case/work')
        self.assertEqual(value['env'], SIGNAL_ENV)
        self.assertEqual(value['raw_wait_status'], 0)
        self.assertEqual(value['streams']['stdout']['observed'], 0)
        self.assertEqual(value['streams']['stderr']['observed'], 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('native_source', 'overlay_source', 'collector', 'mcexec', 'payload',
                 'serializer_report', 'work_root'):
        parser.add_argument('--' + name.replace('_', '-'), required=True)
    args = parser.parse_args()
    d = load('named_signal_native_contract', args.native_source,
             '7e4256eee51f7d50ef758c55579801d691d4ee2cee9155a60680701dba5c540b')
    o = load('named_signal_overlay_contract', args.overlay_source,
             '0891bc13a8750d09f7758d31031828f8270bc480fe5dc0c25d545528ab454640')
    unittest.main(argv=['named-signal-host-contract'], verbosity=2)
