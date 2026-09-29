import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_rust_exact_build_input_manifest as generator
from scripts import native_rust_exact_build_offline as offline


def git(cwd, *args):
    return subprocess.check_output(['/usr/bin/git', '-C', str(cwd)] + list(args))


class ManifestGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = root / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo / 'scripts').mkdir()
        shutil.copy(Path(__file__).parents[1] / 'native_rust_exact_build_offline.py',
                    self.repo / 'scripts/native_rust_exact_build_offline.py')
        (self.repo / 'scripts/native_rust_exact_build_offline.py').chmod(0o644)
        (self.repo / 'tracked').write_bytes(b'input')
        (self.repo / 'tracked').chmod(0o644)
        (self.repo / 'link').symlink_to('tracked')
        git(self.repo, 'add', '.')
        self.ihk = self.repo / 'ihk'
        self.ihk.mkdir()
        git(self.ihk, 'init', '-q')
        (self.ihk / 'nested').write_bytes(b'ihk')
        (self.ihk / 'nested').chmod(0o644)
        (self.ihk / 'nested-link').symlink_to('nested')
        git(self.ihk, 'add', '.')
        git(self.ihk, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'ihk')
        self.ihk_head = git(self.ihk, 'rev-parse', 'HEAD').decode().strip()
        git(self.repo, '-c', 'advice.addEmbeddedRepo=false', 'add', 'ihk')
        git(self.repo, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'main')
        self.candidate = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        self.assets = root / 'assets'
        self.assets.mkdir()
        self.asset_hashes = {}
        for name in generator.ASSET_HASHES:
            path = self.assets / name
            path.write_bytes(('asset-' + name).encode())
            self.asset_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def generate(self, output=None):
        output = output or Path(self.temp.name) / 'manifest.json'
        with patch.object(generator, 'EXPECTED_IHK_HEAD', self.ihk_head), \
                patch.object(generator, 'ASSET_HASHES', self.asset_hashes):
            generator.generate(self.repo, self.assets, output, self.candidate)
        return json.loads(output.read_text())

    def verify(self, data):
        with patch.object(offline, 'EXPECTED_IHK_HEAD', self.ihk_head), \
                patch.object(offline, 'ASSET_HASHES', self.asset_hashes):
            offline.verify_inputs(self.repo, self.candidate, self.assets, data,
                                  offline.Runner())

    def assert_rejected_by_both(self, data, reason):
        with self.assertRaisesRegex(generator.ManifestError, reason):
            self.generate(Path(self.temp.name) / 'rejected.json')
        with self.assertRaisesRegex(offline.BuildError, reason):
            self.verify(data)

    def commit_fixture_paths(self):
        git(self.ihk, 'add', '.')
        git(self.ihk, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'pathname fixture')
        self.ihk_head = git(self.ihk, 'rev-parse', 'HEAD').decode('ascii').strip()
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'pathname fixture')
        self.candidate = git(self.repo, 'rev-parse', 'HEAD').decode('ascii').strip()

    def test_positive_manifest_is_canonical_and_complete(self):
        old_head, old_hashes = generator.EXPECTED_IHK_HEAD, generator.ASSET_HASHES
        try:
            generator.EXPECTED_IHK_HEAD = self.ihk_head
            generator.ASSET_HASHES = self.asset_hashes
            output = Path(self.temp.name) / 'manifest.json'
            generator.generate(self.repo, self.assets, output, self.candidate)
            raw = output.read_text()
            self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                             separators=(',', ':')) + '\n')
            data = json.loads(raw)
            self.assertEqual(data['candidate_sha'], self.candidate)
            self.assertEqual(data['schema'], 'mckernel.native-exact-build-inputs.v1')
            self.assertEqual(data['ihk_sha'], self.ihk_head)
            self.assertEqual(data['gitlinks'], {'ihk': self.ihk_head})
            self.assertIn('ihk/nested', data['repository_files'])
            self.assertIn('link', data['repository_files'])
            self.assertEqual(data['repository_files']['link'],
                             hashlib.sha256(b'tracked').hexdigest())
            self.assertNotEqual(data['repository_files']['link'],
                                hashlib.sha256(b'input').hexdigest())
            old_offline_head, old_offline_assets = offline.EXPECTED_IHK_HEAD, offline.ASSET_HASHES
            try:
                offline.EXPECTED_IHK_HEAD = self.ihk_head
                offline.ASSET_HASHES = self.asset_hashes
                offline.verify_inputs(self.repo, self.candidate, self.assets, data,
                                      offline.Runner())
            finally:
                offline.EXPECTED_IHK_HEAD, offline.ASSET_HASHES = old_offline_head, old_offline_assets
        finally:
            generator.EXPECTED_IHK_HEAD, generator.ASSET_HASHES = old_head, old_hashes

    def test_dirty_checkout_rejected(self):
        (self.repo / 'new').write_text('untracked')
        old_head, old_hashes = generator.EXPECTED_IHK_HEAD, generator.ASSET_HASHES
        try:
            generator.EXPECTED_IHK_HEAD = self.ihk_head
            generator.ASSET_HASHES = self.asset_hashes
            with self.assertRaisesRegex(generator.ManifestError, 'dirty'):
                generator.generate(self.repo, self.assets, Path(self.temp.name) / 'x',
                                   self.candidate)
        finally:
            generator.EXPECTED_IHK_HEAD, generator.ASSET_HASHES = old_head, old_hashes

    def test_existing_output_rejected(self):
        output = Path(self.temp.name) / 'x'
        output.write_text('old')
        with self.assertRaises(generator.ManifestError):
            generator.generate(self.repo, self.assets, output, self.candidate)

    def test_wrong_heads_and_asset_rejected(self):
        old_head, old_hashes = generator.EXPECTED_IHK_HEAD, generator.ASSET_HASHES
        try:
            generator.EXPECTED_IHK_HEAD = self.ihk_head
            generator.ASSET_HASHES = self.asset_hashes
            with self.assertRaises(generator.ManifestError):
                generator.generate(self.repo, self.assets, Path(self.temp.name) / 'x', '0' * 40)
            generator.EXPECTED_IHK_HEAD = '0' * 40
            with self.assertRaises(generator.ManifestError):
                generator.generate(self.repo, self.assets, Path(self.temp.name) / 'ihk-wrong', self.candidate)
            generator.EXPECTED_IHK_HEAD = self.ihk_head
            (self.assets / next(iter(self.asset_hashes))).write_bytes(b'wrong')
            with self.assertRaises(generator.ManifestError):
                generator.generate(self.repo, self.assets, Path(self.temp.name) / 'y', self.candidate)
        finally:
            generator.EXPECTED_IHK_HEAD, generator.ASSET_HASHES = old_head, old_hashes

    def test_output_symlink_rejected(self):
        output = Path(self.temp.name) / 'x'
        output.symlink_to(self.temp.name + '/elsewhere')
        with self.assertRaises(generator.ManifestError):
            generator.generate(self.repo, self.assets, output, self.candidate)
        target = Path(self.temp.name) / 'target'
        target.mkdir()
        parent_link = Path(self.temp.name) / 'parent-link'
        parent_link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(generator.ManifestError, 'contains a symlink'):
            generator.generate(self.repo, self.assets, parent_link / 'new' / 'manifest',
                               self.candidate)

    def test_index_rows_reject_untrusted_parser_bytes(self):
        def row(path, mode=b'100644', object_id=b'a' * 40, stage=b'0'):
            return mode + b' ' + object_id + b' ' + stage + b'\t' + path + b'\0'

        cases = (
            ('malformed', b'100644 only-two-fields\tfile\0'),
            ('duplicate', row(b'file') + row(b'file')),
            ('non-stage-0', row(b'file', stage=b'1')),
            ('parent-escape', row(b'../escape')),
            ('embedded-parent-escape', row(b'directory/../escape')),
            ('absolute', row(b'/escape')),
            ('unsupported-mode', row(b'file', mode=b'040000')),
        )
        for name, output in cases:
            with self.subTest(name=name), patch.object(generator, '_git', return_value=output):
                with self.assertRaises(generator.ManifestError):
                    generator._index_rows(self.repo)

    def test_inventory_rejects_main_ihk_collision(self):
        def row(path):
            return b'100644 ' + b'a' * 40 + b' 0\t' + path + b'\0'

        def index_output(root, *args):
            if args == ('ls-files', '--others', '--exclude-standard', '-z'):
                return b''
            if Path(root) == self.repo:
                result = row(b'ihk/nested')
            elif Path(root) == self.ihk:
                result = row(b'nested')
            else:
                self.fail('unexpected index root: ' + str(root))
            if args == ('ls-tree', '-r', '-z', '--full-tree', 'HEAD'):
                return result.replace(b'100644 ', b'100644 blob ').replace(b' 0\t', b'\t')
            self.assertEqual(args, ('ls-files', '-s', '-z'))
            return result

        with patch.object(generator, '_git', side_effect=index_output):
            with self.assertRaisesRegex(generator.ManifestError, 'inventory collision'):
                generator._inventory(self.repo)

    def test_git_drops_ambient_git_locations_and_disables_hooks(self):
        prior = os.environ.get('GIT_DIR')
        try:
            os.environ['GIT_DIR'] = '/untrusted/git-dir'
            completed = subprocess.CompletedProcess([], 0, b'', b'')
            with patch.object(generator.subprocess, 'run', return_value=completed) as run:
                self.assertEqual(generator._git(self.repo, 'status'), b'')
            command = run.call_args[0][0]
            environment = run.call_args[1]['env']
            self.assertNotIn('GIT_DIR', environment)
            self.assertEqual(environment['GIT_CONFIG_NOSYSTEM'], '1')
            self.assertEqual(environment['GIT_CONFIG_GLOBAL'], os.devnull)
            self.assertIn('core.fsmonitor=false', command)
            self.assertIn('core.hooksPath=/dev/null', command)
        finally:
            if prior is None:
                os.environ.pop('GIT_DIR', None)
            else:
                os.environ['GIT_DIR'] = prior

    def test_symlink_substitution_with_core_symlinks_false(self):
        data = self.generate()
        for root, name, target in ((self.repo, 'link', 'tracked'),
                                   (self.ihk, 'nested-link', 'nested')):
            with self.subTest(root=str(root)):
                git(root, 'config', 'core.symlinks', 'false')
                (root / name).unlink()
                (root / name).write_bytes(target.encode())
                self.assertEqual(git(root, 'status', '--porcelain'), b'')
                self.assert_rejected_by_both(data, 'symlink type differs')
                (root / name).unlink()
                (root / name).symlink_to(target)

    def test_assume_unchanged_main_and_ihk_bytes_cannot_be_self_blessed(self):
        data = self.generate()
        for root, name, relative in ((self.repo, 'tracked', 'tracked'),
                                     (self.ihk, 'nested', 'ihk/nested')):
            with self.subTest(relative=relative):
                path = root / name
                original = path.read_bytes()
                git(root, 'update-index', '--assume-unchanged', name)
                path.write_bytes(b'forged source')
                self.assertEqual(git(root, 'status', '--porcelain'), b'')
                forged = dict(data, repository_files=dict(data['repository_files']))
                forged['repository_files'][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assert_rejected_by_both(forged, 'Git blob bytes differ')
                path.write_bytes(original)
                git(root, 'update-index', '--no-assume-unchanged', name)

    def test_exec_mode_drift_is_rejected_despite_core_filemode_false(self):
        data = self.generate()
        for root, name in ((self.repo, 'tracked'), (self.ihk, 'nested')):
            with self.subTest(root=str(root)):
                git(root, 'config', 'core.filemode', 'false')
                path = root / name
                original = path.stat().st_mode
                path.chmod(original | 0o100)
                self.assertEqual(git(root, 'status', '--porcelain'), b'')
                self.assert_rejected_by_both(data, 'executable mode differs')
                path.chmod(original)

    def test_complete_regular_permission_mode_is_exact_for_main_and_ihk(self):
        data = self.generate()
        for root, name, bad_mode in ((self.repo, 'tracked', 0o600),
                                     (self.ihk, 'nested', 0o700)):
            with self.subTest(root=str(root), mode=oct(bad_mode)):
                path = root / name
                path.chmod(bad_mode)
                with self.assertRaisesRegex(generator.ManifestError,
                                             'indexed executable mode differs'):
                    self.generate(Path(self.temp.name) / ('bad-' + name + '.json'))
                with self.assertRaisesRegex(offline.BuildError,
                                             'indexed executable mode differs'):
                    self.verify(data)
                path.chmod(0o644)
        self.verify(data)

    def test_index_oid_and_mode_must_equal_head_in_both_repositories(self):
        data = self.generate()
        for root, name in ((self.repo, 'tracked'), (self.ihk, 'nested')):
            for mutation in ('oid', 'mode'):
                with self.subTest(root=str(root), mutation=mutation):
                    if mutation == 'oid':
                        (root / name).write_bytes(b'changed and staged')
                        git(root, 'add', name)
                        self.assert_rejected_by_both(data, 'index differs from HEAD tree')
                    else:
                        git(root, 'update-index', '--chmod=+x', name)
                        with self.assertRaisesRegex(generator.ManifestError,
                                                     'indexed executable mode differs'):
                            self.generate(Path(self.temp.name) / 'rejected-mode.json')
                        with self.assertRaisesRegex(offline.BuildError,
                                                     'index differs from HEAD tree'):
                            self.verify(data)
                    git(root, 'restore', '--source=HEAD', '--staged', '--worktree', name)
                    (root / name).chmod(0o644)

    def test_racing_output_is_preserved_and_temporary_removed(self):
        output = Path(self.temp.name) / 'race.json'
        real_link = os.link

        def competing_writer(source, destination):
            output.write_bytes(b'competing writer bytes')
            return real_link(source, destination)

        with patch.object(generator.os, 'link', side_effect=competing_writer):
            with self.assertRaisesRegex(generator.ManifestError, 'output already exists'):
                self.generate(output)
        self.assertEqual(output.read_bytes(), b'competing writer bytes')
        self.assertEqual(list(output.parent.glob('race.json.tmp-*')), [])

    def test_python36_syntax_and_no_newer_subprocess_api(self):
        for module in (generator, offline):
            source = Path(module.__file__).read_text()
            tree = ast.parse(source, feature_version=(3, 6))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess':
                        self.assertFalse({'text', 'capture_output'} & {kw.arg for kw in node.keywords})

    def test_positive_executable_and_absent_unconsumed_gitlink(self):
        (self.repo / 'tracked').chmod(0o755)
        git(self.repo, 'add', 'tracked')
        git(self.repo, 'update-index', '--add', '--cacheinfo',
            '160000,' + self.ihk_head + ',vendor/unconsumed')
        git(self.repo, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'executable and unconsumed gitlink')
        self.candidate = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        data = self.generate()
        self.verify(data)
        self.assertEqual(data['gitlinks']['vendor/unconsumed'], self.ihk_head)
        (self.repo / 'tracked').chmod(0o644)
        git(self.repo, 'config', 'core.filemode', 'false')
        self.assert_rejected_by_both(data, 'executable mode differs')

    def test_nested_ihk_gitlink_is_forbidden(self):
        git(self.ihk, 'update-index', '--add', '--cacheinfo',
            '160000,' + self.ihk_head + ',child')
        git(self.ihk, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'nested child')
        self.ihk_head = git(self.ihk, 'rev-parse', 'HEAD').decode().strip()
        git(self.repo, 'add', 'ihk')
        git(self.repo, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'update ihk')
        self.candidate = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        with self.assertRaisesRegex(generator.ManifestError, 'nested IHK gitlink'):
            self.generate()
        data = {'schema': offline.INPUT_SCHEMA, 'candidate_sha': self.candidate,
                'ihk_sha': self.ihk_head}
        with self.assertRaisesRegex(offline.BuildError, 'nested IHK gitlink'):
            self.verify(data)

    def test_present_gitlink_must_be_a_real_directory(self):
        git(self.repo, 'update-index', '--add', '--cacheinfo',
            '160000,' + self.ihk_head + ',vendor')
        git(self.repo, '-c', 'user.name=test', '-c', 'user.email=test@example',
            'commit', '-qm', 'vendor gitlink')
        self.candidate = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        data = self.generate()
        vendor = self.repo / 'vendor'
        for kind in ('regular', 'symlink'):
            with self.subTest(kind=kind):
                if kind == 'regular':
                    vendor.write_bytes(b'not a directory')
                else:
                    vendor.symlink_to('ihk', target_is_directory=True)
                self.assert_rejected_by_both(data, 'gitlink type differs')
                vendor.unlink()

    def test_filter_and_ambient_git_settings_cannot_change_byte_authority(self):
        data = self.generate()
        # Installing a clean filter must neither execute it nor let it normalize
        # altered bytes back to the HEAD blob during provenance verification.
        info = self.repo / '.git/info/attributes'
        info.write_text('tracked filter=hostile\n')
        git(self.repo, 'config', 'filter.hostile.clean', 'touch FILTER_EXECUTED; printf input')
        git(self.repo, 'config', 'filter.hostile.required', 'true')
        (self.repo / 'tracked').write_bytes(b'altered')
        with patch.dict(os.environ, {'GIT_DIR': '/absent/hostile-dir',
                                    'GIT_WORK_TREE': '/absent/hostile-tree',
                                    'GIT_INDEX_FILE': '/absent/hostile-index',
                                    'GIT_CONFIG_COUNT': '1',
                                    'GIT_CONFIG_KEY_0': 'core.worktree',
                                    'GIT_CONFIG_VALUE_0': '/absent'}):
            self.assert_rejected_by_both(data, 'Git blob bytes differ')
        self.assertFalse((self.repo / 'FILTER_EXECUTED').exists())

    def test_tree_parser_rejects_malformed_types_duplicates_and_paths(self):
        good = b'100644 blob ' + b'a' * 40 + b'\ttracked\0'
        for raw in (good + good, good[:-1], good.replace(b'blob', b'commit'),
                    good.replace(b'tracked', b'../escape'),
                    good.replace(b'tracked', b'\xff'), good.replace(b'100644', b'040000')):
            with self.subTest(raw=raw), self.assertRaises(offline.BuildError):
                offline.git_rows(raw, tree=True)

    def test_real_git_preserves_distinct_cr_crlf_and_lf_paths(self):
        names = ('line\rname', 'line\r\nname', 'line\nname')
        for root in (self.repo, self.ihk):
            for i, name in enumerate(names):
                (root / name).write_bytes(('distinct source %d' % i).encode('ascii'))
                (root / name).chmod(0o644)
        self.commit_fixture_paths()
        data = self.generate()
        self.verify(data)
        for prefix in ('', 'ihk/'):
            self.assertEqual({prefix + name for name in names},
                             {p for p in data['repository_files'] if p.startswith(prefix + 'line')})
            self.assertEqual(len({data['repository_files'][prefix + name] for name in names}), 3)

    def test_real_git_cr_and_crlf_cannot_alias_ignored_lf_decoys(self):
        # Retained reviewer finding: universal_newlines transformed a tracked
        # CR/CRLF path into LF, allowing a forged manifest to bind a clean LF
        # decoy while the actual tracked file contained changed source bytes.
        names = ('carriage\rname', 'crlf\r\nname')
        for root in (self.repo, self.ihk):
            for name in names:
                (root / name).write_bytes(b'original tracked bytes')
                (root / name).chmod(0o644)
        self.commit_fixture_paths()
        for root in (self.repo, self.ihk):
            (root / '.git/info/exclude').write_text('carriage*name\ncrlf*name\n')
            for name in names:
                decoy = name.replace('\r\n', '\n').replace('\r', '\n')
                (root / decoy).write_bytes(b'original tracked bytes')
                self.assertEqual(git(root, 'ls-files', '--others', '--exclude-standard', '-z'), b'')
        data = self.generate()
        self.verify(data)
        for root, prefix in ((self.repo, ''), (self.ihk, 'ihk/')):
            for name in names:
                with self.subTest(prefix=prefix, name=name):
                    path = root / name
                    path.write_bytes(b'changed tracked source')
                    forged = dict(data, repository_files=dict(data['repository_files']))
                    expected = forged['repository_files'].pop(prefix + name)
                    decoy = name.replace('\r\n', '\n').replace('\r', '\n')
                    forged['repository_files'][prefix + decoy] = expected
                    self.assert_rejected_by_both(forged, 'Git blob bytes differ')
                    path.write_bytes(b'original tracked bytes')

    def test_git_path_parser_requires_bytes_and_head_requires_exact_ascii_lf(self):
        with self.assertRaisesRegex(offline.BuildError, 'raw bytes'):
            offline.git_rows('100644 blob ' + 'a' * 40 + '\tline\rname\0', tree=True)
        self.assertEqual(offline.git_head(b'a' * 40 + b'\n'), 'a' * 40)
        for raw in (b'a' * 40, b'a' * 40 + b'\r\n', b'a' * 40 + b'\n\n',
                    b' ' + b'a' * 40 + b'\n', b'\xff' * 40 + b'\n', 'a' * 40 + '\n'):
            with self.subTest(raw=raw), self.assertRaises(offline.BuildError):
                offline.git_head(raw)


if __name__ == '__main__':
    unittest.main()
