"""Real local Git fixtures; no Docker, root, production preparation or network."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-3.sh'
OBSERVER = ROOT / 'scripts/native_exact_candidate_placement_observer_20260929.py'
spec = importlib.util.spec_from_file_location('placement', OBSERVER)
placement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(placement)


class PlacementRealGit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.ihk_source = self.root / 'ihk-source'
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()
        self.c = self.scratch / 'candidate'
        self.b = self.scratch / 'backup'
        for repo in (self.source, self.ihk_source):
            repo.mkdir()
            self.git(repo, 'init', '-q')
            self.git(repo, 'config', 'user.name', 'Fixture')
            self.git(repo, 'config', 'user.email', 'fixture@example.invalid')
        f = self.ihk_source / placement.OVERLAY_FILE
        f.parent.mkdir(parents=True)
        f.write_text('original\n')
        self.git(self.ihk_source, 'add', '.')
        self.git(self.ihk_source, 'commit', '-qm', 'ihk')
        self.ihk_sha = self.git(self.ihk_source, 'rev-parse', 'HEAD').decode().strip()
        (self.source / 'main').write_text('main\n')
        (self.source / 'link').symlink_to('main')
        self.git(self.source, 'add', '.')
        self.git(self.source, 'update-index', '--add', '--cacheinfo', '160000,' + self.ihk_sha + ',ihk')
        self.optional_links = {
            'executer/user/lib/libdwarf/libdwarf': 'ab9230b2b8aa66a3d1d52e4be11fca17a3b63753',
            'executer/user/lib/syscall_intercept': '66a47ceb1c5c05e1d613ab3f1f7164f42d5aca6f',
            'executer/user/lib/uti': '8c5a556814efe1f57e5eb58b72318069dd7738b5',
        }
        for name, oid in self.optional_links.items():
            self.git(self.source, 'update-index', '--add', '--cacheinfo', '160000,' + oid + ',' + name)
        self.git(self.source, 'commit', '-qm', 'main')
        self.main_sha = self.git(self.source, 'rev-parse', 'HEAD').decode().strip()
        self.git(self.root, 'clone', '--no-hardlinks', str(self.source), str(self.c))
        (self.c / 'ihk').rmdir()
        self.git(self.root, 'clone', '--no-hardlinks', str(self.ihk_source), str(self.c / 'ihk'))
        # Populate the live source submodule for nested identity checks, but its
        # HEAD/content is deliberately not an input to committed-object binding.
        self.git(self.root, 'clone', '--no-hardlinks', str(self.ihk_source), str(self.source / 'ihk'))
        self.table = [(self.scratch, 'ext4')]
        self.host = self.scratch.stat().st_dev + 1

    @staticmethod
    def git(repo, *args):
        return placement.git(repo, *args)

    def observe(self, phase='clean', **overrides):
        args = dict(candidate=self.c, backup=self.b, source=self.source, scratch=self.scratch,
                    main_sha=self.main_sha, ihk_sha=self.ihk_sha, phase=phase,
                    table=self.table, host_device=self.host)
        args.update(overrides)
        return placement.observe(**args)

    def overlay(self):
        self.b.mkdir()
        shutil.copytree(self.c / '.git', self.b / 'main.git')
        shutil.copytree(self.c / 'ihk/.git', self.b / 'ihk.git')
        result = self.c / 'ihk' / placement.OVERLAY_FILE
        result.write_text('reviewed overlay\n')
        return dict(overlay_sha=hashlib.sha256(self.git(self.c / 'ihk', 'diff', '--binary')).hexdigest(),
                    result_sha=hashlib.sha256(result.read_bytes()).hexdigest())

    def test_clean_real_git_and_separate_ihk_accounting(self):
        result = self.observe()
        self.assertEqual(result['main_tracked_files'], 1)
        self.assertEqual(result['ihk_tracked_files'], 1)
        self.assertEqual(len(result['main_gitlinks']), 4)
        for name, oid in self.optional_links.items():
            self.assertEqual(result['main_gitlinks'][name], {'mode': '160000', 'object_id': oid})
        self.assertEqual(result['memory_backed_bytes'], 0)
        self.assertEqual(result['backup_allocated_bytes'], 0)
        self.assertGreater(result['ihk_allocated_bytes'], 0)
        self.assertEqual(result['candidate_allocated_bytes'], placement.allocation(self.c, self.c.stat().st_dev))

    def test_overlay_backup_is_metadata_not_checkout(self):
        result = self.observe('overlay', **self.overlay())
        self.assertGreater(result['backup_allocated_bytes'], 0)
        self.assertFalse((self.b / '.git').exists())

    def test_dirty_live_tree_is_not_source_input(self):
        (self.source / 'main').write_text('unrelated work\n')
        (self.source / 'ihk' / placement.OVERLAY_FILE).write_text('unrelated nested work\n')
        self.assertEqual(self.observe()['status'], 'PASS_PLACEMENT')

    def test_optional_gitlinks_need_no_nested_checkout(self):
        for name in self.optional_links:
            self.assertEqual(list((self.c / name).iterdir()), [])
            self.assertFalse((self.c / name / '.git').exists())
        self.assertEqual(len(self.observe()['main_gitlinks']), 4)

    def test_unexpected_index_gitlink_rejected(self):
        self.git(self.c, 'update-index', '--add', '--cacheinfo', '160000,' + self.ihk_sha + ',unexpected')
        with self.assertRaisesRegex(RuntimeError, 'indexed gitlink'):
            self.observe()

    def test_mismatched_index_gitlink_oid_rejected(self):
        name = next(iter(self.optional_links))
        self.git(self.c, 'update-index', '--cacheinfo', '160000,' + self.ihk_sha + ',' + name)
        with self.assertRaisesRegex(RuntimeError, 'indexed gitlink'):
            self.observe()

    def test_missing_index_gitlink_rejected(self):
        self.git(self.c, 'update-index', '--force-remove', next(iter(self.optional_links)))
        with self.assertRaisesRegex(RuntimeError, 'gitlink set'):
            self.observe()

    def test_changed_index_gitlink_mode_rejected(self):
        name = next(iter(self.optional_links))
        (self.c / name).rmdir(); (self.c / name).write_text('replacement')
        self.git(self.c, 'add', name)
        with self.assertRaisesRegex(RuntimeError, 'gitlink set or mode'):
            self.observe()

    def test_dirty_source_gitlink_index_does_not_rebind_expected(self):
        name = next(iter(self.optional_links))
        self.git(self.source, 'update-index', '--cacheinfo', '160000,' + self.ihk_sha + ',' + name)
        self.assertEqual(self.observe()['main_gitlinks'][name]['object_id'], self.optional_links[name])

    def test_existing_backup_rejected_before_conversion(self):
        self.b.mkdir()
        with self.assertRaisesRegex(RuntimeError, 'backup exists'):
            self.observe()

    def test_overlay_before_conversion_rejected(self):
        (self.c / 'ihk' / placement.OVERLAY_FILE).write_text('premature overlay\n')
        with self.assertRaisesRegex(RuntimeError, 'IHK is dirty'):
            self.observe()

    def test_main_dirty_rejected(self):
        (self.c / 'main').write_text('changed\n')
        with self.assertRaisesRegex(RuntimeError, 'main candidate dirty'):
            self.observe()

    def test_nested_hardlink_rejected(self):
        p = self.c / 'ihk' / placement.OVERLAY_FILE
        p.unlink()
        os.link(self.source / 'ihk' / placement.OVERLAY_FILE, p)
        with self.assertRaisesRegex(RuntimeError, 'inode shared'):
            self.observe()

    def test_nested_mount_same_device_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'nested mount'):
            self.observe(table=self.table + [(self.c / 'ihk', 'ext4')])

    def test_backup_tmpfs_submount_rejected(self):
        args = self.overlay()
        with self.assertRaisesRegex(RuntimeError, 'nested mount'):
            self.observe('overlay', table=self.table + [(self.b / 'main.git', 'tmpfs')], **args)

    def test_memory_backed_scratch_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'disk-backed'):
            self.observe(table=[(self.scratch, 'tmpfs')])

    def test_host_filesystem_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'distinct from host'):
            self.observe(host_device=self.scratch.stat().st_dev)

    def test_wrong_head_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'HEAD mismatch'):
            self.observe(main_sha='0' * 40)

    def test_overlay_diff_hash_rejected(self):
        args = self.overlay(); args['overlay_sha'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'diff mismatch'):
            self.observe('overlay', **args)

    def test_overlay_result_hash_rejected(self):
        args = self.overlay(); args['result_sha'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'result mismatch'):
            self.observe('overlay', **args)

    def test_extra_overlay_change_rejected(self):
        args = self.overlay()
        (self.c / 'ihk' / 'unexpected').write_text('unexpected')
        with self.assertRaisesRegex(RuntimeError, 'status mismatch'):
            self.observe('overlay', **args)

    def test_backup_shape_rejected(self):
        args = self.overlay(); (self.b / 'unexpected').write_text('x')
        with self.assertRaisesRegex(RuntimeError, 'backup shape'):
            self.observe('overlay', **args)

    def test_backup_head_rejected(self):
        args = self.overlay(); (self.b / 'ihk.git' / 'HEAD').write_text('0' * 40 + '\n')
        with self.assertRaisesRegex(RuntimeError, 'backup HEAD'):
            self.observe('overlay', **args)

    def test_symlinked_nested_root_rejected(self):
        (self.c / 'ihk').rename(self.scratch / 'nested')
        (self.c / 'ihk').symlink_to(self.scratch / 'nested', target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'symlink path'):
            self.observe()

    def release_fixture(self):
        for file in (PACKET, OBSERVER):
            target = self.source / file.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
        self.git(self.source, 'add', 'docs', 'scripts')
        self.git(self.source, 'commit', '-qm', 'release template')
        release = self.git(self.source, 'rev-parse', 'HEAD').decode().strip()
        self.git(self.source, 'update-ref', 'refs/remotes/origin/released', release)
        section = PACKET.read_text().split('# Validate the later packet/helper release separately from the candidate source.\n', 1)[1].split('\ntopology_check() {', 1)[0]
        prefix = ('set -Eeuo pipefail\nSOURCE=$1; SOURCE_GIT=$1/.git; SHA=$2; RELEASE=$3; '
                  'RELEASE_REF=refs/remotes/origin/released\n'
                  'GIT_ENV=(/usr/bin/git)\n')
        return ['/bin/bash', '-c', prefix + section,
                str(self.source / PACKET.relative_to(ROOT)), str(self.source), self.main_sha, release]

    def test_fetched_release_binds_packet_helper_not_dirty_source(self):
        command = self.release_fixture()
        (self.source / 'main').write_text('unrelated live change\n')
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fetched_release_rejects_mutated_helper(self):
        command = self.release_fixture()
        (self.source / OBSERVER.relative_to(ROOT)).write_text('# substituted\n')
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_fetched_release_rejects_unfetched_commit(self):
        command = self.release_fixture()
        self.git(self.source, 'update-ref', 'refs/remotes/origin/released', self.main_sha)
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


class PacketAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PACKET.read_text()

    def test_shell_syntax(self):
        subprocess.run(['/bin/bash', '-n', str(PACKET)], check=True)

    def test_inline_python_compiles(self):
        for index, code in enumerate(re.findall(r"<<'PY'\n(.*?)\nPY", self.text, re.S)):
            compile(code, 'packet-heredoc-' + str(index), 'exec')
        for index, code in enumerate(re.findall(r"-c '\n(.*?)\n'", self.text, re.S)):
            if code.startswith('import '):
                compile(code, 'packet-inline-' + str(index), 'exec')

    def test_preserved_sequence_and_no_destructive_trap(self):
        self.assertGreater(len(self.text.splitlines()), 373)
        self.assertNotIn('rm -rf', self.text)
        self.assertNotIn('trap - ERR', self.text)
        converter = self.text.index('--backup "$B" --evidence "$ME"')
        overlay = self.text.index('/usr/bin/git -C "$C/ihk" apply "$OVERLAY"')
        self.assertLess(converter, overlay)
        self.assertIn('test ! -e "$B" && test ! -L "$B"', self.text[:converter])
        self.assertIn('test ! -e "$ME" && test ! -L "$ME"', self.text[:converter])
        self.assertIn('instance.validate()', self.text)
        self.assertIn('memory_allocation_memory_backed_bytes', self.text)
        self.assertIn('"$SOURCE_IHK_GIT" "$IHK_SHA"', self.text)

    def test_helper_hash(self):
        expected = re.search(r'readonly PLACEMENT_SHA=([a-f0-9]{64})', self.text)[1]
        self.assertEqual(expected, hashlib.sha256(OBSERVER.read_bytes()).hexdigest())

    def test_request_writer_actual_output(self):
        code = next(code for code in re.findall(r"<<'PY'\n(.*?)\nPY", self.text, re.S) if 'request = {' in code)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / 'manifest'; manifest.write_text('{}')
            image = root / 'image'; image.write_text('{}')
            out = root / 'request'
            args = [str(out), str(root), '1'*40, str(manifest), 'assets', 'output', 'evidence', 'lease', 'backup',
                    str(image), 'image-id', 'd'*64, 'overlay', 'o'*64, 'b'*40, 'r'*40, 'b'*64, 'r'*64, 'exclusion', 'a'*64]
            command = ['/usr/bin/python3', '-I', '-B', '-c', code] + args
            subprocess.run(command, check=True, capture_output=True)
            request = json.loads(out.read_text())
            self.assertEqual(request['limits']['CpusetCpus'], '2-5')
            self.assertEqual(request['memory_allocation_roots'], [str(root), 'backup'])
            self.assertEqual(request['provenance_path_sha256'], 'd'*64)
            self.assertEqual(request['owner_path_sha256'], 'a'*64)
            self.assertEqual(request['input_manifest_sha256'], hashlib.sha256(b'{}').hexdigest())
            self.assertEqual(request['operational_exclusion_path'], 'exclusion')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_selftest(self):
        subprocess.run(['/usr/bin/python3', '-I', '-B', str(OBSERVER), '--self-test'], check=True, capture_output=True)

    def test_terminal_writer_preserves_failure_and_is_exclusive(self):
        code = next(code for code in re.findall(r"<<'PY'\n(.*?)\nPY", self.text, re.S) if "returncode=int(rc)" in code)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'log'; log.write_bytes(b'original failure\n')
            terminal = root / 'terminal'
            command = ['/usr/bin/python3', '-I', '-B', '-c', code, str(terminal), '9', str(os.getpid()), str(log)]
            subprocess.run(command, check=True, capture_output=True)
            record = json.loads(terminal.read_text())
            self.assertEqual(record['returncode'], 9)
            self.assertEqual(record['log_sha256'], hashlib.sha256(log.read_bytes()).hexdigest())
            self.assertEqual(log.read_bytes(), b'original failure\n')
            original = terminal.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(terminal.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
