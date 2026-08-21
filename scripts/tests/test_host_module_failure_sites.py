#!/usr/bin/env python3
"""Synthetic tests for compiler-backed host-module failure-site capture."""

import ast
import json
import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_failure_sites as capture  # noqa: E402
import record_compiler_argv as recorder  # noqa: E402


class GitIdentityTests(unittest.TestCase):
    def test_repository_head_ignores_hostile_inherited_git_environment(self):
        expected = capture.git_head(REPO_ROOT)
        hostile = {
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/definitely/not/objects",
            "GIT_CEILING_DIRECTORIES": str(REPO_ROOT.parent),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.useReplaceRefs",
            "GIT_CONFIG_VALUE_0": "true",
            "GIT_DIR": "/definitely/not/the/repository",
            "GIT_OBJECT_DIRECTORY": "/definitely/not/objects",
            "GIT_WORK_TREE": "/definitely/not/the/worktree",
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            self.assertEqual(capture.git_head(REPO_ROOT), expected)

    def test_rejects_inherited_repository_controlled_stdlib_module(self):
        fake = mock.Mock()
        fake.__spec__ = None
        fake.__file__ = str(REPO_ROOT / "scripts/hashlib.py")
        with mock.patch.dict(sys.modules, {"hashlib": fake}, clear=False):
            with self.assertRaisesRegex(
                capture.CaptureError, "untrusted hashlib module"
            ):
                capture.reject_untrusted_inherited_modules()

    def test_legacy_spec_less_sys_requires_exact_interpreter_entry_module(self):
        missing = object()
        real_spec = getattr(capture._fp0006_entry_sys, "__spec__", missing)
        with mock.patch.object(
            capture._fp0006_entry_sys, "__spec__", None, create=True
        ):
            self.assertTrue(
                capture._module_origin_is_stdlib(
                    "sys", capture._fp0006_entry_sys
                )
            )
            for origin in (None, "built-in", "frozen"):
                fake = types.ModuleType("sys")
                if origin is None:
                    fake.__spec__ = None
                else:
                    fake.__spec__ = types.SimpleNamespace(origin=origin)
                with self.subTest(origin=origin), mock.patch.dict(
                    sys.modules, {"sys": fake}, clear=False
                ):
                    with self.assertRaisesRegex(
                        capture.CaptureError, "untrusted sys module"
                    ):
                        capture.reject_untrusted_inherited_modules()
        self.assertIs(
            getattr(capture._fp0006_entry_sys, "__spec__", missing), real_spec
        )


class ArgvRecorderTests(unittest.TestCase):
    def test_writes_canonical_argv_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "nested/argv.json"
            command = ["rustc", "--crate-name", "a name", "source.rs"]
            recorder.write_argv(output, command)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), command)
            self.assertEqual(
                recorder.parse_args(["--output", str(output), "--"] + command).command,
                command,
            )


class KbuildCommandTests(unittest.TestCase):
    def test_parses_continuation_without_evaluating_shell_suffix(self):
        data = b"""cmd_/build/demo.o := /usr/bin/gcc -DMODULE \\
  -Wp,-MMD,/build/.demo.o.d -c -o /build/demo.o '/src/a file.c' ; touch /tmp/not-run
source_/build/demo.o := '/src/a file.c'
deps_/build/demo.o := \\
  /src/a\\ file.c
"""
        parsed = capture.parse_kbuild_cmd_bytes(data)
        self.assertEqual(parsed["compile_argv"][0], "/usr/bin/gcc")
        self.assertEqual(parsed["compile_argv"][-1], "/src/a file.c")
        self.assertEqual(parsed["declared_source"], "/src/a file.c")
        self.assertGreater(parsed["post_compile_token_count"], 0)

    def test_reconstructs_read_only_preprocessor_argv(self):
        command = {
            "compile_argv": [
                "gcc",
                "-DMODULE",
                "-Wp,-MMD,/build/.demo.o.d",
                "-MF",
                "/build/demo.d",
                "-MT",
                "/build/demo.o",
                "-c",
                "-o",
                "/build/demo.o",
                "/src/demo.c",
            ]
        }
        argv = capture.reconstruct_preprocess_argv(command, 10)
        self.assertEqual(argv[0], "gcc")
        self.assertIn("-DMODULE", argv)
        self.assertEqual(argv[-3:], ["-E", "-fdirectives-only", "/src/demo.c"])
        for removed in ("-c", "-o", "-MF", "-MT", "-Wp,-MMD,/build/.demo.o.d"):
            self.assertNotIn(removed, argv)

    def test_rejects_shell_substitution_and_conditional_chains(self):
        substitutions = b"""cmd_x := gcc -c /src/demo.c $(touch /tmp/bad)
source_x := /src/demo.c
"""
        with self.assertRaises(capture.CaptureError):
            capture.parse_kbuild_cmd_bytes(substitutions)

        conditional = b"""cmd_x := gcc -c /src/demo.c && touch /tmp/bad
source_x := /src/demo.c
"""
        with self.assertRaises(capture.CaptureError):
            capture.parse_kbuild_cmd_bytes(conditional)

    def test_rejects_response_files_duplicate_or_mismatched_assignments(self):
        response = b"""cmd_x := gcc @args -c /src/demo.c
source_x := /src/demo.c
"""
        with self.assertRaises(capture.CaptureError):
            capture.parse_kbuild_cmd_bytes(response)

        duplicate = b"""cmd_x := gcc -c /src/demo.c
cmd_x := gcc -c /src/demo.c
source_x := /src/demo.c
"""
        with self.assertRaises(capture.CaptureError):
            capture.parse_kbuild_cmd_bytes(duplicate)

        mismatch = b"""cmd_x := gcc -c /src/demo.c
source_y := /src/demo.c
"""
        with self.assertRaises(capture.CaptureError):
            capture.parse_kbuild_cmd_bytes(mismatch)

    def test_recorded_rust_argv_is_exact_json_and_rejects_controls(self):
        self.assertEqual(
            capture.parse_recorded_compile_argv_bytes(
                b'["rustc","--emit=obj=/tmp/a.o","/src/a.rs"]\n'
            ),
            ["rustc", "--emit=obj=/tmp/a.o", "/src/a.rs"],
        )
        for invalid in (
            b"[]",
            b'{"argv":[]}',
            b'["rustc",";"]',
            b'["rustc",1]',
        ):
            with self.assertRaises(capture.CaptureError):
                capture.parse_recorded_compile_argv_bytes(invalid)


class LineFilteringTests(unittest.TestCase):
    def test_keeps_only_target_marker_lines_and_original_line_numbers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.c"
            header = root / "header.h"
            target.write_text("placeholder\n", encoding="utf-8")
            header.write_text("placeholder\n", encoding="utf-8")
            output = (
                '# 1 "<built-in>"\n'
                '#define BUILTIN_FAILURE -ENOMEM\n'
                '# 10 "{0}" 1\n'
                'return -EINVAL;\n'
                '# 1 "{1}" 1\n'
                'return -EIO;\n'
                '# 20 "{0}" 2\n'
                'return -EFAULT;\n'
            ).format(target, header).encode("utf-8")
            rows = capture.filter_target_lines(output, target, root)
            self.assertEqual(rows, [(10, "return -EINVAL;\n"), (20, "return -EFAULT;\n")])

    def test_requires_a_target_line_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.c"
            target.write_text("return -EINVAL;\n", encoding="utf-8")
            with self.assertRaises(capture.CaptureError):
                capture.filter_target_lines(b'# 1 "other.c"\nreturn -EINVAL;\n', target, root)


class SiteScannerTests(unittest.TestCase):
    def test_resolves_logical_continued_macro_token_to_physical_spelling(self):
        text = (
            "#define DEMO_FAILURE(value) \\\n"
            "\tuse(value, \\\n"
            "\t    -EFAULT)\n"
        )
        logical = "#define DEMO_FAILURE(value) \tuse(value, \t    -EFAULT)"
        resolved = capture.resolve_spliced_c_token(
            text, 1, logical.index("-EFAULT") + 1, "-EFAULT"
        )
        self.assertEqual(
            resolved,
            {
                "expression": "-EFAULT",
                "logical_column": logical.index("-EFAULT") + 1,
                "logical_line": 1,
                "macro_name": "DEMO_FAILURE",
                "physical_column": 6,
                "physical_end_column": 13,
                "physical_line": 3,
                "source_logical_column": logical.index("-EFAULT") + 1,
            },
        )
        with self.assertRaisesRegex(capture.CaptureError, "unique source spelling"):
            capture.resolve_spliced_c_token(
                text, 1, logical.index("-EFAULT") + 1, "-EINVAL"
            )

    def test_masks_comments_strings_chars_and_nested_rust_comments(self):
        rows = [
            (7, 'let text = r#"-ENOMEM"#; // -EIO\n'),
            (8, "/* outer -EPERM /* inner -ENOSYS */ done */\n"),
            (9, "let byte = b'-'; let result = -EINVAL;\n"),
            (10, 'let string = "-EFAULT";\n'),
            (11, "return -(ENOSPC as c_long);\n"),
            (12, "if result == -(EINTR as c_long) { retry(); }\n"),
        ]
        digest = capture.rows_digest(rows)
        sites = capture.scan_rows("mcctrl", "rust", "helper.rs", "a" * 64, digest, rows)
        self.assertEqual(
            [(site["errno"], site["line"]) for site in sites],
            [("EINVAL", 9), ("ENOSPC", 11), ("EINTR", 12)],
        )

    def test_site_id_is_stable_and_bound_to_source_hash(self):
        rows = [(100, "return -EINVAL;\n")]
        active = capture.rows_digest(rows)
        first = capture.scan_rows("ihk", "c", "a.c", "1" * 64, active, rows)[0]
        second = capture.scan_rows("ihk", "c", "a.c", "1" * 64, active, rows)[0]
        changed = capture.scan_rows("ihk", "c", "a.c", "2" * 64, active, rows)[0]
        self.assertEqual(first["id"], second["id"])
        self.assertNotEqual(first["id"], changed["id"])


class RepositoryAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.ihk = self.repo / "ihk"
        self.ihk.mkdir(parents=True)
        (self.repo / "scripts/patches").mkdir(parents=True)
        (self.repo / "host-kernel/reference").mkdir(parents=True)
        (self.repo / "scripts/host_module_failure_sites.py").write_text(
            "AUTHORITY = True\n", encoding="utf-8"
        )
        (self.repo / "host-kernel/reference/inventory.json").write_text(
            "{}\n", encoding="utf-8"
        )
        (self.repo / "tracked-link").symlink_to(
            "scripts/host_module_failure_sites.py"
        )
        (self.ihk / "linux").mkdir()
        (self.ihk / "linux/demo.c").write_text(
            "int demo(void) { return -EINVAL; }\n", encoding="utf-8"
        )
        (self.ihk / "linux/other.c").write_text(
            "int other(void) { return 0; }\n", encoding="utf-8"
        )
        self.overlay = self.repo / "scripts/patches/ihk-linux-compat.patch"
        self.overlay.write_text(
            """diff --git a/linux/demo.c b/linux/demo.c
--- a/linux/demo.c
+++ b/linux/demo.c
@@ -1 +1 @@
-int demo(void) { return -EINVAL; }
+int demo(void) { return -EFAULT; }
""",
            encoding="utf-8",
        )
        self._init_and_commit(self.ihk, "IHK baseline")
        self._init_and_commit(self.repo, "main baseline")
        self.main_paths = (
            "host-kernel/reference/inventory.json",
            "scripts/host_module_failure_sites.py",
            "scripts/patches/ihk-linux-compat.patch",
        )
        self.expected_sources = (
            ("ihk", "c", "ihk/linux/demo.c", "ihk/linux/.demo.o.cmd"),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _git(self, repository, *arguments):
        environment = capture.git_environment()
        completed = subprocess.run(
            [capture.GIT_EXECUTABLE] + list(arguments),
            cwd=str(repository),
            check=False,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            self.fail(completed.stderr.decode("utf-8", errors="replace"))
        return completed.stdout

    def _init_and_commit(self, repository, message):
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.email", "audit@example.invalid")
        self._git(repository, "config", "user.name", "authority audit")
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-qm", message)

    def _authority(self):
        with mock.patch.object(
            capture, "FRESH_MAIN_AUTHORITY_PATHS", self.main_paths
        ), mock.patch.object(capture, "EXPECTED_SOURCES", self.expected_sources):
            return capture.capture_repository_authority(
                self.repo, expected_head=capture.git_head(self.repo)
            )

    def _apply_overlay(self):
        self._git(self.ihk, "apply", str(self.overlay))

    def _forging_git_wrapper(self):
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        sentinel = self.root / "fake-git.executed"
        wrapper = fake_bin / "git"
        wrapper.write_text(
            "#!/usr/bin/python3\n"
            "import subprocess\n"
            "import sys\n"
            "open({0!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
            "arguments = sys.argv[1:]\n"
            "if 'cat-file' in arguments and '--batch' in arguments:\n"
            "    data = sys.stdin.buffer.read()\n"
            "    completed = subprocess.run(['/usr/bin/git'] + arguments, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)\n"
            "    output = bytearray(completed.stdout)\n"
            "    newline = output.find(b'\\n')\n"
            "    if newline >= 0:\n"
            "        header = bytes(output[:newline]).split(b' ')\n"
            "        if len(header) == 3 and header[2].isdigit() and int(header[2]) > 0:\n"
            "            output[newline + 1] ^= 1\n"
            "    sys.stdout.buffer.write(output)\n"
            "    sys.stderr.buffer.write(completed.stderr)\n"
            "    raise SystemExit(completed.returncode)\n"
            "if any(name in arguments for name in ('status', 'ls-files', 'apply', 'check-attr')):\n"
            "    raise SystemExit(0)\n"
            "completed = subprocess.run(['/usr/bin/git'] + arguments)\n"
            "raise SystemExit(completed.returncode)\n".format(str(sentinel)),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        for name in (
            "git-cat-file",
            "git-status",
            "git-ls-files",
            "git-apply",
            "git-check-attr",
        ):
            (fake_bin / name).symlink_to("git")
        return fake_bin, wrapper, sentinel

    def test_exact_committed_overlay_is_the_only_allowed_ihk_delta(self):
        self._apply_overlay()
        authority = self._authority()
        self.assertEqual(authority["main_head"], capture.git_head(self.repo))
        self.assertEqual(authority["ihk_head"], capture.git_head(self.ihk))
        self.assertEqual(
            authority["ihk_snapshots"]["linux/demo.c"]["data"],
            b"int demo(void) { return -EFAULT; }\n",
        )
        with mock.patch.object(
            capture, "FRESH_MAIN_AUTHORITY_PATHS", self.main_paths
        ), mock.patch.object(capture, "EXPECTED_SOURCES", self.expected_sources):
            capture.recheck_repository_authority(self.repo, authority)

    def test_capture_rejects_bootstrap_expected_head_mismatch(self):
        self._apply_overlay()
        expected = "0" * 40
        if capture.git_head(self.repo) == expected:
            expected = "1" * 40
        with mock.patch.object(
            capture, "FRESH_MAIN_AUTHORITY_PATHS", self.main_paths
        ), mock.patch.object(capture, "EXPECTED_SOURCES", self.expected_sources):
            with self.assertRaisesRegex(
                capture.CaptureError, "bootstrap expected commit"
            ):
                capture.capture_repository_authority(
                    self.repo, expected_head=expected
                )

    def test_dirty_or_staged_main_authority_fails_closed(self):
        self._apply_overlay()
        authority_path = self.repo / "scripts/host_module_failure_sites.py"
        sentinel = self.root / "staged-launcher.executed"
        authority_path.write_text(
            "open({0!r}, 'w').write('executed')\n"
            "__import__('os').unlink(__file__)\n".format(str(sentinel)),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(capture.CaptureError, "main authority worktree"):
            self._authority()
        self._git(self.repo, "add", "scripts/host_module_failure_sites.py")
        with self.assertRaisesRegex(capture.CaptureError, "main repository index"):
            self._authority()
        self.assertFalse(sentinel.exists())
        self.assertTrue(authority_path.exists())

    def test_deleted_authority_launcher_fails_closed(self):
        self._apply_overlay()
        launcher = self.repo / "scripts/host_module_failure_sites.py"
        launcher.unlink()
        with self.assertRaisesRegex(
            capture.CaptureError, "main worktree file closure"
        ):
            self._authority()

    def test_self_hiding_modified_authority_launcher_never_executes(self):
        self._apply_overlay()
        launcher = self.repo / "scripts/host_module_failure_sites.py"
        sentinel = self.root / "modified-launcher.executed"
        launcher.write_text(
            "open({0!r}, 'w').write('executed')\n"
            "__import__('os').unlink(__file__)\n".format(str(sentinel)),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            capture.CaptureError, "main authority worktree"
        ):
            self._authority()
        self.assertFalse(sentinel.exists())
        self.assertTrue(launcher.exists())

    def test_missing_wrong_or_unexpected_ihk_delta_fails_closed(self):
        with self.assertRaisesRegex(capture.CaptureError, "exact overlay"):
            self._authority()
        self._apply_overlay()
        (self.ihk / "linux/other.c").write_text(
            "int other(void) { return -EPERM; }\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(capture.CaptureError, "exact overlay"):
            self._authority()
        (self.ihk / "linux/other.c").write_bytes(
            self._git(self.ihk, "show", "HEAD:linux/other.c")
        )
        (self.ihk / "untracked.c").write_text("untracked\n", encoding="utf-8")
        with self.assertRaisesRegex(capture.CaptureError, "file closure"):
            self._authority()

    def test_staged_ihk_delta_fails_closed(self):
        self._apply_overlay()
        self._git(self.ihk, "add", "linux/demo.c")
        with self.assertRaisesRegex(capture.CaptureError, "IHK index"):
            self._authority()

    def test_ihk_symlink_fails_closed(self):
        self._apply_overlay()
        (self.ihk / "linux/other.c").unlink()
        (self.ihk / "linux/other.c").symlink_to("demo.c")
        with self.assertRaisesRegex(capture.CaptureError, "symlink"):
            self._authority()

    def test_ihk_root_symlink_fails_closed(self):
        self._apply_overlay()
        real_ihk = self.repo / "ihk-real"
        os.rename(str(self.ihk), str(real_ihk))
        self.ihk.symlink_to(real_ihk, target_is_directory=True)
        with self.assertRaisesRegex(capture.CaptureError, "real directory"):
            self._authority()

    def test_end_recheck_rejects_head_and_identity_races(self):
        self._apply_overlay()
        authority = self._authority()
        (self.repo / "unrelated.txt").write_text("new commit\n", encoding="utf-8")
        self._git(self.repo, "add", "unrelated.txt")
        self._git(self.repo, "commit", "-qm", "move HEAD")
        with mock.patch.object(
            capture, "FRESH_MAIN_AUTHORITY_PATHS", self.main_paths
        ), mock.patch.object(capture, "EXPECTED_SOURCES", self.expected_sources):
            with self.assertRaisesRegex(capture.CaptureError, "changed during"):
                capture.recheck_repository_authority(self.repo, authority)

    def test_end_recheck_rejects_same_bytes_inode_identity_race(self):
        self._apply_overlay()
        authority = self._authority()
        authority_path = self.repo / "scripts/host_module_failure_sites.py"
        original = authority_path.read_bytes()
        replacement = self.repo / "scripts/authority.replacement"
        replacement.write_bytes(original)
        os.replace(str(replacement), str(authority_path))
        with mock.patch.object(
            capture, "FRESH_MAIN_AUTHORITY_PATHS", self.main_paths
        ), mock.patch.object(capture, "EXPECTED_SOURCES", self.expected_sources):
            with self.assertRaisesRegex(capture.CaptureError, "changed during"):
                capture.recheck_repository_authority(self.repo, authority)

    def test_hostile_git_environment_cannot_retarget_authority(self):
        self._apply_overlay()
        expected = self._authority()
        hostile = {
            "GIT_DIR": "/definitely/not/a/repository",
            "GIT_INDEX_FILE": "/definitely/not/an/index",
            "GIT_OBJECT_DIRECTORY": "/definitely/not/objects",
            "GIT_WORK_TREE": "/definitely/not/a/worktree",
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            actual = self._authority()
        self.assertEqual(actual, expected)

    def test_path_first_forging_git_and_exec_variants_never_run(self):
        fake_bin, wrapper, sentinel = self._forging_git_wrapper()
        self._git(self.repo, "config", "core.fsmonitor", str(wrapper))
        self._git(self.repo, "config", "core.hooksPath", str(fake_bin))
        self._git(self.repo, "config", "core.attributesFile", str(wrapper))
        self._apply_overlay()
        hostile = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": str(wrapper),
            "GIT_EXEC_PATH": str(fake_bin),
            "LD_LIBRARY_PATH": str(fake_bin),
            "PATH": str(fake_bin) + os.pathsep + "/usr/bin:/bin",
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            authority = self._authority()
            self.assertEqual(authority["main_head"], capture.git_head(self.repo))
            capture.run_git(
                self.repo, ["status", "--porcelain=v1"], "read status"
            )
            capture.run_git(
                self.repo,
                [
                    "check-attr",
                    "-a",
                    "--",
                    "scripts/host_module_failure_sites.py",
                ],
                "read attributes",
            )
        self.assertFalse(sentinel.exists())
        environment = capture.git_environment()
        self.assertEqual(environment["PATH"], "/usr/bin:/bin")
        for name in ("GIT_EXEC_PATH", "LD_LIBRARY_PATH", "LD_PRELOAD"):
            self.assertNotIn(name, environment)

    def test_untracked_stdlib_shadows_never_execute_or_self_hide(self):
        self._apply_overlay()
        for name in ("hashlib", "os", "json", "pathlib"):
            with self.subTest(name=name):
                shadow = self.repo / "scripts/{0}.py".format(name)
                sentinel = self.root / "{0}.executed".format(name)
                shadow.write_text(
                    "open({0!r}, 'w').write('executed')\n"
                    "__import__('os').unlink(__file__)\n".format(str(sentinel)),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    capture.CaptureError, "main worktree file closure"
                ):
                    self._authority()
                self.assertFalse(sentinel.exists())
                self.assertTrue(shadow.exists())
                shadow.unlink()

    def test_staged_stdlib_shadow_is_rejected_before_execution(self):
        self._apply_overlay()
        shadow = self.repo / "scripts/json.py"
        sentinel = self.root / "staged-shadow.executed"
        shadow.write_text(
            "open({0!r}, 'w').write('executed')\n"
            "__import__('os').unlink(__file__)\n".format(str(sentinel)),
            encoding="utf-8",
        )
        self._git(self.repo, "add", "scripts/json.py")
        with self.assertRaisesRegex(capture.CaptureError, "main repository index"):
            self._authority()
        self.assertFalse(sentinel.exists())
        self.assertTrue(shadow.exists())


class IsolatedEntrypointTests(unittest.TestCase):
    SHADOW_NAMES = ("hashlib", "os", "json", "pathlib")

    def _write_shadows(self, directory):
        sentinels = []
        for name in self.SHADOW_NAMES:
            sentinel = directory / "{0}.executed".format(name)
            (directory / "{0}.py".format(name)).write_text(
                "open({0!r}, 'w').write('executed')\n"
                "__import__('os').unlink(__file__)\n".format(str(sentinel)),
                encoding="utf-8",
            )
            sentinels.append(sentinel)
        return sentinels

    def _workflow_bootstrap_code(self):
        workflow = (
            REPO_ROOT / ".github/workflows/rust-x86_64-validation.yml"
        ).read_text(encoding="utf-8")
        matches = capture.re.findall(
            r'/usr/bin/python3 -I -S -B -c "((?:\\.|[^\"])*)" "\$@"',
            workflow,
            flags=capture.re.DOTALL,
        )
        self.assertEqual(len(matches), 6)
        self.assertEqual(len(set(matches)), 1)
        return matches[0].replace('\\"', '"')

    def _git(self, repo, *arguments):
        completed = subprocess.run(
            [capture.GIT_EXECUTABLE] + list(arguments),
            cwd=str(repo),
            check=False,
            env=capture.git_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.decode("ascii", errors="replace").strip()

    def _initialize_repository(self, repo):
        repo.mkdir(parents=True)
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "audit@example.invalid")
        self._git(repo, "config", "user.name", "authority audit")

    def _commit_launcher(self, repo, source, message):
        launcher = repo / "scripts/host_module_failure_sites.py"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(source, encoding="utf-8")
        self._git(repo, "add", "scripts/host_module_failure_sites.py")
        self._git(repo, "commit", "-qm", message)
        return self._git(repo, "rev-parse", "HEAD")

    def _bootstrap_process(self, repo, expected_head=None):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(repo / "scripts")
        environment["FP_AUTHORITY_EXPECTED_HEAD"] = (
            expected_head or self._git(repo, "rev-parse", "HEAD")
        )
        return subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "-c",
                self._workflow_bootstrap_code(),
                str(repo),
                "--repo",
                str(repo),
            ],
            cwd=str(repo),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _wait_for_sentinel(self, process, sentinel):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if sentinel.exists():
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    "bootstrap exited before sentinel: stdout={0!r}, stderr={1!r}".format(
                        stdout, stderr
                    )
                )
            time.sleep(0.01)
        process.kill()
        stdout, stderr = process.communicate()
        self.fail(
            "timed out waiting for sentinel: stdout={0!r}, stderr={1!r}".format(
                stdout, stderr
            )
        )

    def _pausing_launcher(self, loaded, gate, entered):
        return (
            "import os\n"
            "import time\n"
            "open({0!r}, 'w').write('loaded')\n"
            "for unused in range(1500):\n"
            "    if os.path.exists({1!r}):\n"
            "        break\n"
            "    time.sleep(0.01)\n"
            "else:\n"
            "    raise RuntimeError('race gate timed out')\n"
            "def isolated_authority_main(argv, expected_head=None):\n"
            "    open({2!r}, 'w').write('entered')\n"
            "    return 0\n"
        ).format(str(loaded), str(gate), str(entered))

    def _assert_pre_entry_head_race_rejected(self, start_at_newer):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            self._initialize_repository(repo)
            loaded = root / "launcher.loaded"
            gate = root / "launcher.gate"
            entered = root / "launcher.entered"
            quiet = (
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    return 0\n"
            )
            if start_at_newer:
                older = self._commit_launcher(repo, quiet, "older launcher")
                newer = self._commit_launcher(
                    repo,
                    self._pausing_launcher(loaded, gate, entered),
                    "newer pausing launcher",
                )
                self.assertEqual(self._git(repo, "rev-parse", "HEAD"), newer)
                target = older
            else:
                older = self._commit_launcher(
                    repo,
                    self._pausing_launcher(loaded, gate, entered),
                    "older pausing launcher",
                )
                newer = self._commit_launcher(repo, quiet, "newer launcher")
                self._git(repo, "checkout", "-q", older)
                target = newer
            process = self._bootstrap_process(repo)
            self._wait_for_sentinel(process, loaded)
            self._git(repo, "checkout", "-q", target)
            gate.write_text("continue\n", encoding="utf-8")
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 2, (stdout, stderr))
            self.assertIn(b"HEAD changed before checker entry", stderr)
            self.assertFalse(entered.exists())

    def test_bootstrap_rejects_newer_to_older_head_race(self):
        self._assert_pre_entry_head_race_rejected(start_at_newer=True)

    def test_bootstrap_rejects_older_to_newer_head_race(self):
        self._assert_pre_entry_head_race_rejected(start_at_newer=False)

    def test_bootstrap_rejects_checkout_different_from_job_pin_before_blob(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            self._initialize_repository(repo)
            pinned = self._commit_launcher(
                repo,
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    return 0\n",
                "pinned launcher",
            )
            loaded = root / "unpinned.loaded"
            self._commit_launcher(
                repo,
                "open({0!r}, 'w').write('loaded')\n"
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    return 0\n".format(str(loaded)),
                "unpinned launcher",
            )
            process = self._bootstrap_process(repo, expected_head=pinned)
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 2, (stdout, stderr))
            self.assertIn(b"checkout differs from expected commit", stderr)
            self.assertFalse(loaded.exists())

    def test_bootstrap_rejects_head_change_after_loaded_main_returns(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            self._initialize_repository(repo)
            returned = root / "launcher.returned"
            launcher = (
                "import os\n"
                "import subprocess\n"
                "trusted_run = subprocess.run\n"
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    completed = trusted_run([\"/usr/bin/git\", \"-C\", {0!r}, \"checkout\", \"-q\", \"race-target\"])\n"
                "    if completed.returncode != 0:\n"
                "        raise RuntimeError('cannot move race HEAD')\n"
                "    open({1!r}, 'w').write('returned')\n"
                "    subprocess.run = lambda *args, **kwargs: None\n"
                "    os.waitpid = lambda *args, **kwargs: (0, 0)\n"
                "    os.read = lambda *args, **kwargs: b''\n"
                "    return 0\n"
            ).format(str(repo), str(returned))
            older = self._commit_launcher(repo, launcher, "returning launcher")
            newer = self._commit_launcher(
                repo,
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    return 0\n",
                "race target launcher",
            )
            self._git(repo, "branch", "race-target", newer)
            self._git(repo, "checkout", "-q", older)
            process = self._bootstrap_process(repo)
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 2, (stdout, stderr))
            self.assertTrue(returned.exists())
            self.assertIn(b"HEAD changed during checker execution", stderr)
            self.assertEqual(self._git(repo, "rev-parse", "HEAD"), newer)

    def test_bootstrap_never_coerces_hostile_return_status_after_recheck(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            self._initialize_repository(repo)
            returned = root / "launcher.returned"
            converted = root / "status.converted"
            launcher = (
                "class ExitStatus(object):\n"
                "    def __index__(self):\n"
                "        open({0!r}, 'w').write('converted')\n"
                "        return 0\n"
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    open({1!r}, 'w').write('returned')\n"
                "    return ExitStatus()\n"
            ).format(str(converted), str(returned))
            self._commit_launcher(repo, launcher, "hostile return status")
            process = self._bootstrap_process(repo)
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 125, (stdout, stderr))
            self.assertTrue(returned.exists())
            self.assertFalse(converted.exists())

    def test_workflow_bootstrap_executes_head_blob_not_worktree_launcher(self):
        bootstrap = self._workflow_bootstrap_code()
        for mutation in ("modified", "staged", "deleted"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                repo = Path(temporary) / "repo"
                script = repo / "scripts/host_module_failure_sites.py"
                script.parent.mkdir(parents=True)
                committed_sentinel = repo.parent / "committed.executed"
                malicious_sentinel = repo.parent / "malicious.executed"
                script.write_text(
                    "def isolated_authority_main(argv, expected_head=None):\n"
                    "    open(argv[-1], 'w').write('committed')\n"
                    "    return 0\n",
                    encoding="utf-8",
                )
                for arguments in (
                    ["init", "-q"],
                    ["config", "user.email", "audit@example.invalid"],
                    ["config", "user.name", "authority audit"],
                    ["add", "scripts/host_module_failure_sites.py"],
                    ["commit", "-qm", "trusted launcher"],
                ):
                    completed = subprocess.run(
                        [capture.GIT_EXECUTABLE] + arguments,
                        cwd=str(repo),
                        check=False,
                        env=capture.git_environment(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                if mutation == "deleted":
                    script.unlink()
                else:
                    script.write_text(
                        "open({0!r}, 'w').write('malicious')\n"
                        "__import__('os').unlink(__file__)\n".format(
                            str(malicious_sentinel)
                        ),
                        encoding="utf-8",
                    )
                    if mutation == "staged":
                        completed = subprocess.run(
                            [
                                capture.GIT_EXECUTABLE,
                                "add",
                                "scripts/host_module_failure_sites.py",
                            ],
                            cwd=str(repo),
                            check=False,
                            env=capture.git_environment(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                environment = dict(os.environ)
                environment["PYTHONPATH"] = str(repo / "scripts")
                environment["FP_AUTHORITY_EXPECTED_HEAD"] = self._git(
                    repo, "rev-parse", "HEAD"
                )
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "-B",
                        "-c",
                        bootstrap,
                        str(repo),
                        "--repo",
                        str(repo),
                        str(committed_sentinel),
                    ],
                    cwd=str(repo),
                    check=False,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(
                    committed_sentinel.read_text(encoding="utf-8"), "committed"
                )
                self.assertFalse(malicious_sentinel.exists())
                if mutation != "deleted":
                    self.assertTrue(script.exists())

    def test_workflow_bootstrap_ignores_path_git_and_exec_forgery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            self._initialize_repository(repo)
            executed = root / "committed.executed"
            expected_head = self._commit_launcher(
                repo,
                "def isolated_authority_main(argv, expected_head=None):\n"
                "    open(argv[-1], 'w').write(expected_head)\n"
                "    return 0\n",
                "trusted launcher",
            )
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            sentinel = root / "fake-git.executed"
            fake_git = fake_bin / "git"
            fake_git.write_text(
                "#!/usr/bin/python3\n"
                "open({0!r}, 'w').write('executed')\n"
                "raise SystemExit(99)\n".format(str(sentinel)),
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            for name in (
                "git-cat-file",
                "git-status",
                "git-ls-files",
                "git-apply",
                "git-check-attr",
            ):
                (fake_bin / name).symlink_to("git")
            environment = dict(os.environ)
            environment.update(
                {
                    "FP_AUTHORITY_EXPECTED_HEAD": expected_head,
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "core.fsmonitor",
                    "GIT_CONFIG_VALUE_0": str(fake_git),
                    "GIT_EXEC_PATH": str(fake_bin),
                    "LD_LIBRARY_PATH": str(fake_bin),
                    "PATH": str(fake_bin) + os.pathsep + "/usr/bin:/bin",
                    "PYTHONPATH": str(repo / "scripts"),
                }
            )
            completed = subprocess.run(
                [
                    "/usr/bin/python3",
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    self._workflow_bootstrap_code(),
                    str(repo),
                    "--repo",
                    str(repo),
                    str(executed),
                ],
                cwd=str(repo),
                check=False,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                executed.read_text(encoding="utf-8"), expected_head
            )
            self.assertFalse(sentinel.exists())

    def test_fresh_and_historical_entry_lanes_are_explicitly_separate(self):
        repo, target, target_argv, historical = (
            capture.parse_authority_entry_arguments(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--authority-target",
                    "failure-flows-v2",
                    "--",
                    "--repo",
                    str(REPO_ROOT),
                    "--failure-sites",
                    "hfs.json",
                    "--failure-flows",
                    "v1.json",
                    "--output",
                    "v2.json",
                ]
            )
        )
        self.assertEqual(repo, REPO_ROOT)
        self.assertEqual(target, "failure-flows-v2")
        self.assertFalse(historical)
        self.assertNotIn("--historical-ef58", target_argv)

        _, historical_target, historical_argv, historical = (
            capture.parse_authority_entry_arguments(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--authority-target",
                    "failure-flows-v2",
                    "--authority-historical",
                    "--",
                    "--repo",
                    str(REPO_ROOT),
                    "--failure-sites",
                    "hfs.json",
                    "--failure-flows",
                    "v1.json",
                    "--historical-ef58",
                    "--output",
                    "v2.json",
                ]
            )
        )
        self.assertEqual(historical_target, "failure-flows-v2")
        self.assertTrue(historical)
        self.assertIn("--historical-ef58", historical_argv)

        for v3_target in (
            "failure-semantics-v3",
            "failure-contract-review-v3",
        ):
            _, parsed_target, parsed_argv, parsed_historical = (
                capture.parse_authority_entry_arguments(
                    [
                        "--repo",
                        str(REPO_ROOT),
                        "--authority-target",
                        v3_target,
                        "--authority-historical",
                        "--",
                        "--repo",
                        str(REPO_ROOT),
                        "--historical-ef58",
                        "--output",
                        "v3.json",
                    ]
                )
            )
            self.assertEqual(parsed_target, v3_target)
            self.assertTrue(parsed_historical)
            self.assertIn("--historical-ef58", parsed_argv)

    def test_v3_generators_and_tests_are_in_commit_bound_authority_closure(self):
        expected = {
            "host_module_failure_semantics_v3": "scripts/host_module_failure_semantics_v3.py",
            "host_module_failure_contract_review_v3": "scripts/host_module_failure_contract_review_v3.py",
            "scripts.tests.test_host_module_failure_semantics_v3": "scripts/tests/test_host_module_failure_semantics_v3.py",
            "scripts.tests.test_host_module_failure_contract_review_v3": "scripts/tests/test_host_module_failure_contract_review_v3.py",
        }
        for module, relative in expected.items():
            self.assertEqual(capture.AUTHORITY_MODULE_PATHS.get(module), relative)
            self.assertIn(relative, capture.FRESH_MAIN_AUTHORITY_PATHS)
        self.assertEqual(
            capture.AUTHORITY_TARGET_MODULES["failure-semantics-v3"],
            "host_module_failure_semantics_v3",
        )
        self.assertEqual(
            capture.AUTHORITY_TARGET_MODULES["failure-contract-review-v3"],
            "host_module_failure_contract_review_v3",
        )

    def test_fresh_authority_rechecks_even_when_target_raises(self):
        authority = {"main_snapshots": {}}
        finder = object()
        original_path = list(sys.path)
        with mock.patch.object(
            capture,
            "parse_authority_entry_arguments",
            return_value=(REPO_ROOT, "failure-sites", [], False),
        ), mock.patch.object(
            capture, "require_isolated_authority_runtime"
        ), mock.patch.object(
            capture, "capture_repository_authority", return_value=authority
        ), mock.patch.object(
            capture,
            "_prepare_authority_imports",
            return_value=(finder, original_path),
        ), mock.patch.object(
            capture, "_run_authority_target", side_effect=RuntimeError("target failed")
        ), mock.patch.object(
            capture, "_restore_authority_imports"
        ) as restore, mock.patch.object(
            capture, "recheck_repository_authority"
        ) as recheck:
            with self.assertRaisesRegex(RuntimeError, "target failed"):
                capture.isolated_authority_main(
                    ["ignored"], expected_head=capture.git_head(REPO_ROOT)
                )
        restore.assert_called_once_with(finder, original_path)
        recheck.assert_called_once_with(REPO_ROOT.resolve(), authority)

    def test_fresh_authority_rechecks_before_rejecting_hostile_status(self):
        authority = {"main_snapshots": {}}
        finder = object()
        original_path = list(sys.path)
        expected_head = capture.git_head(REPO_ROOT)
        with mock.patch.object(
            capture,
            "parse_authority_entry_arguments",
            return_value=(REPO_ROOT, "failure-sites", [], False),
        ), mock.patch.object(
            capture, "require_isolated_authority_runtime"
        ), mock.patch.object(
            capture, "git_head", return_value=expected_head
        ), mock.patch.object(
            capture, "capture_repository_authority", return_value=authority
        ), mock.patch.object(
            capture,
            "_prepare_authority_imports",
            return_value=(finder, original_path),
        ), mock.patch.object(
            capture, "_run_authority_target", return_value=object()
        ), mock.patch.object(
            capture, "_restore_authority_imports"
        ) as restore, mock.patch.object(
            capture, "recheck_repository_authority"
        ) as recheck:
            self.assertEqual(
                capture.isolated_authority_main(
                    ["ignored"], expected_head=expected_head
                ),
                2,
            )
        restore.assert_called_once_with(finder, original_path)
        recheck.assert_called_once_with(REPO_ROOT.resolve(), authority)

    def test_unsafe_direct_entry_rejects_before_sibling_shadows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "host_module_failure_sites.py"
            script.write_bytes(
                (REPO_ROOT / "scripts/host_module_failure_sites.py").read_bytes()
            )
            sentinels = self._write_shadows(root)
            completed = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=str(root),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn(b"requires the commit-bound isolated", completed.stderr)
            self.assertTrue(all(not path.exists() for path in sentinels))

    def test_isolated_entry_ignores_cwd_pythonpath_and_pythonhome_shadows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinels = self._write_shadows(root)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(root)
            environment["PYTHONHOME"] = str(root)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    str(REPO_ROOT / "scripts/host_module_failure_sites.py"),
                    "--repo",
                    str(root / "not-a-repository"),
                    "--check-repository-authority",
                ],
                cwd=str(root),
                check=False,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn(b"requires the commit-bound isolated", completed.stderr)
            self.assertTrue(all(not path.exists() for path in sentinels))

    def test_snapshot_loader_executes_captured_bytes_not_self_hiding_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "scripts").mkdir()
            sentinel = repo / "executed"
            shadow = repo / "scripts/authority_demo.py"
            shadow.write_text(
                "open({0!r}, 'w').write('executed')\n"
                "__import__('os').unlink(__file__)\n".format(str(sentinel)),
                encoding="utf-8",
            )
            snapshots = {
                "scripts/authority_demo.py": {
                    "data": b"VALUE = 7\n",
                    "path": "scripts/authority_demo.py",
                    "sha256": capture.sha256_bytes(b"VALUE = 7\n"),
                }
            }
            with mock.patch.dict(
                capture.AUTHORITY_MODULE_PATHS,
                {"authority_demo": "scripts/authority_demo.py"},
                clear=True,
            ):
                finder = capture._AuthoritySnapshotFinder(snapshots, repo)
                spec = finder.find_spec("authority_demo")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            self.assertEqual(module.VALUE, 7)
            self.assertFalse(sentinel.exists())
            self.assertTrue(shadow.exists())

    def test_isolated_snapshot_loader_resolves_full_checker_dependency_graph(self):
        program = r'''
import os
import sys
import types

repo = os.path.realpath(sys.argv[1])
# Reproduce Rocky 8/Python 3.6's spec-less built-in sys module on newer
# interpreters before the exact launcher captures its entry-module identity.
if sys.argv[2] == "missing":
    if hasattr(sys, "__spec__"):
        del sys.__spec__
else:
    sys.__spec__ = None
sites_path = os.path.join(repo, "scripts", "host_module_failure_sites.py")
module = types.ModuleType("host_module_failure_sites")
module.__file__ = sites_path
module.__package__ = ""
sys.modules[module.__name__] = module
with open(sites_path, "rb") as handle:
    exec(compile(handle.read(), sites_path, "exec", dont_inherit=True), module.__dict__)
authority_repo = module.Path(repo)
module.require_isolated_authority_runtime(authority_repo)
snapshots = {}
for relative in set(module.AUTHORITY_MODULE_PATHS.values()):
    with open(os.path.join(repo, relative), "rb") as handle:
        data = handle.read()
    snapshots[relative] = {"data": data, "path": relative}
finder, original_path = module._prepare_authority_imports(authority_repo, snapshots)
try:
    module._load_authority_module("host_module_failure_contract_review_v2")
    for name in sorted(module.AUTHORITY_TEST_MODULES):
        module._load_authority_module(name)
finally:
    module._restore_authority_imports(finder, original_path)
'''
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPO_ROOT / "scripts")
        for mode in ("missing", "none"):
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    program,
                    str(REPO_ROOT),
                    mode,
                ],
                cwd=str(REPO_ROOT),
                check=False,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with self.subTest(mode=mode):
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_authority_import_surface_is_python_3_6_runtime_compatible(self):
        for relative in sorted(set(capture.AUTHORITY_MODULE_PATHS.values())):
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            try:
                tree = ast.parse(
                    source, filename=relative, feature_version=(3, 6)
                )
            except TypeError:
                tree = ast.parse(source, filename=relative)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    self.assertNotIn(
                        "annotations",
                        {entry.name for entry in node.names},
                        relative,
                    )
                if isinstance(node, ast.Subscript) and isinstance(
                    node.value, ast.Name
                ):
                    self.assertNotIn(
                        node.value.id,
                        {"dict", "frozenset", "list", "set", "tuple", "type"},
                        relative,
                    )

    def test_locked_sys_path_ignores_repo_insertion_and_rejects_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            locked = capture._AuthoritySysPath(["/trusted/stdlib"], repo)
            locked.insert(0, str(repo / "scripts"))
            self.assertEqual(locked, ["/trusted/stdlib"])
            with self.assertRaisesRegex(
                capture.CaptureError, "attempted to extend sys.path"
            ):
                locked.insert(0, str(repo.parent))


class SyntheticCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.build = self.root / "build"
        self.kernel = self.root / "kernel"
        self.repo.mkdir()
        self.build.mkdir()
        (self.kernel / "include/generated").mkdir(parents=True)
        (self.kernel / "include/config").mkdir(parents=True)
        (self.kernel / ".config").write_text("CONFIG_X86_64=y\n", encoding="utf-8")
        (self.kernel / "include/generated/autoconf.h").write_text(
            "#define CONFIG_X86_64 1\n", encoding="utf-8"
        )
        (self.kernel / "include/config/auto.conf").write_text(
            "CONFIG_X86_64=y\n", encoding="utf-8"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def make_fake_compiler(self, target, header, sentinel):
        compiler = self.root / "fake-gcc"
        program = """#!/usr/bin/env python3
import pathlib
import sys

if sys.argv[1:] == ["--version"]:
    print("fake-gcc 1.0")
    sys.exit(0)
if sys.argv.count("-E") != 1 or sys.argv.count("-fdirectives-only") != 1:
    sys.exit(40)
for forbidden in ("-c", "-o", "-MF", "-MT"):
    if forbidden in sys.argv:
        sys.exit(41)
target = pathlib.Path(sys.argv[-1])
header = pathlib.Path({header!r})
print('# 1 "<built-in>"')
print('#define BUILTIN_FAILURE -ENOMEM')
print('# 10 "{{}}" 1'.format(target))
print('return -EINVAL;')
print('const char *ignored = "-EPERM";')
print('/* -ENOSYS */')
print('# 1 "{{}}" 1'.format(header))
print('return -EIO;')
print('# 20 "{{}}" 2'.format(target))
print('return -EFAULT;')
""".format(header=str(header), sentinel=str(sentinel))
        compiler.write_text(program, encoding="utf-8")
        compiler.chmod(0o755)
        return compiler

    def write_command(self, path, compiler, source, sentinel):
        path.parent.mkdir(parents=True, exist_ok=True)
        key = str(path.parent / "demo.o")
        command = (
            "cmd_{key} := {compiler} -DMODULE -Wp,-MMD,{dep} "
            "-MF {dep2} -MT {obj} -c -o {obj} {source} ; touch {sentinel}\n"
            "source_{key} := {source}\n"
        ).format(
            key=key,
            compiler=shlex.quote(str(compiler)),
            dep=shlex.quote(str(path.parent / ".demo.o.d")),
            dep2=shlex.quote(str(path.parent / "demo.d")),
            obj=shlex.quote(str(path.parent / "demo.o")),
            source=shlex.quote(str(source)),
            sentinel=shlex.quote(str(sentinel)),
        )
        path.write_text(command, encoding="utf-8")

    def test_compiler_capture_is_filtered_digested_stable_and_shell_free(self):
        source = self.repo / "module.c"
        header = self.repo / "header.h"
        command_path = self.build / "module/.module.o.cmd"
        sentinel = self.root / "shell-was-run"
        source.write_text("return -EINVAL;\nreturn -EFAULT;\n", encoding="utf-8")
        header.write_text("return -EIO;\n", encoding="utf-8")
        compiler = self.make_fake_compiler(source, header, sentinel)
        self.write_command(command_path, compiler, source, sentinel)
        config = capture.config_provenance(self.kernel)

        first_record, first_sites = capture.capture_c_source(
            "ihk",
            "module.c",
            "module/.module.o.cmd",
            self.repo,
            self.build,
            self.kernel,
            config,
        )
        second_record, second_sites = capture.capture_c_source(
            "ihk",
            "module.c",
            "module/.module.o.cmd",
            self.repo,
            self.build,
            self.kernel,
            config,
        )

        self.assertFalse(sentinel.exists(), "the ignored .cmd shell suffix executed")
        self.assertEqual(
            [(site["errno"], site["line"]) for site in first_sites],
            [("EINVAL", 10), ("EFAULT", 20)],
        )
        self.assertEqual([site["id"] for site in first_sites], [site["id"] for site in second_sites])
        self.assertEqual(first_record["digests"], second_record["digests"])
        for required in (
            "command_file_sha256",
            "compiler_sha256",
            "config_sha256",
            "effective_source_sha256",
            "preprocessed_sha256",
            "preprocessing_argv_sha256",
            "target_preprocessed_sha256",
        ):
            self.assertRegex(first_record["digests"][required], r"^[0-9a-f]{64}$")

    def test_source_assignment_mismatch_fails_closed(self):
        source = self.repo / "module.c"
        other = self.repo / "other.c"
        header = self.repo / "header.h"
        command_path = self.build / "module/.module.o.cmd"
        sentinel = self.root / "shell-was-run"
        source.write_text("return -EINVAL;\n", encoding="utf-8")
        other.write_text("return -EFAULT;\n", encoding="utf-8")
        header.write_text("", encoding="utf-8")
        compiler = self.make_fake_compiler(source, header, sentinel)
        self.write_command(command_path, compiler, other, sentinel)
        with self.assertRaises(capture.CaptureError):
            capture.capture_c_source(
                "ihk",
                "module.c",
                "module/.module.o.cmd",
                self.repo,
                self.build,
                self.kernel,
                capture.config_provenance(self.kernel),
            )

    def test_rust_helper_scans_exact_source_and_retains_provenance(self):
        source = self.repo / "helper.rs"
        command_path = self.build / "rust/.helper.o.cmd"
        launcher_dir = self.root / "bin"
        actual_sysroot = self.root / "rust-sysroot"
        launcher_dir.mkdir()
        (actual_sysroot / "bin").mkdir(parents=True)
        fake_rustc = launcher_dir / "rustc"
        fake_rustc.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if sys.argv[1:] == ['--print', 'sysroot']:\n"
            "    print({0!r})\n"
            "elif sys.argv[1:] == ['-Vv']:\n"
            "    print('rustc synthetic')\n"
            "else:\n"
            "    sys.exit(2)\n".format(str(actual_sysroot)),
            encoding="utf-8",
        )
        fake_rustc.chmod(0o755)
        actual_compiler = actual_sysroot / "bin/rustc"
        actual_compiler.write_text("actual compiler bytes\n", encoding="utf-8")
        source.write_text(
            "const A: i32 = -EINVAL;\n"
            "const TEXT: &str = r#\"-ENOMEM\"#;\n"
            "// -EIO\n"
            "fn value<'a>() -> i32 { -EFAULT }\n",
            encoding="utf-8",
        )
        command_path.parent.mkdir(parents=True)
        key = str(command_path.parent / "helper.o")
        command_path.write_text(
            "cmd_{0} := {1} --emit=obj={0} {2}\nsource_{0} := {2}\n".format(
                key, shlex.quote(str(fake_rustc)), shlex.quote(str(source))
            ),
            encoding="utf-8",
        )
        (command_path.parent / (command_path.name + ".argv.json")).write_text(
            json.dumps(
                [
                    str(fake_rustc),
                    "--crate-name",
                    "helper",
                    "--emit=obj={0}".format(command_path.parent / "helper.o"),
                    str(source),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        record, sites = capture.capture_rust_source(
            "mcctrl",
            "helper.rs",
            "rust/.helper.o.cmd",
            self.repo,
            self.build,
            self.kernel,
            capture.config_provenance(self.kernel),
        )
        self.assertEqual([(site["errno"], site["line"]) for site in sites], [("EINVAL", 1), ("EFAULT", 4)])
        self.assertEqual(record["preprocess_argv"], [])
        self.assertEqual(
            record["digests"]["preprocessed_sha256"],
            record["digests"]["effective_source_sha256"],
        )
        self.assertRegex(record["digests"]["command_file_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(record["digests"]["compiler_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(record["recorded_compiler"]["resolved_path"], str(actual_compiler))
        self.assertIn("launcher", record["recorded_compiler"])
        self.assertEqual(record["recorded_compiler"]["version_first_line"], "rustc synthetic")
        self.assertRegex(record["recorded_compiler"]["version_stdout_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(
            record["digests"]["recorded_compile_argv_sha256"], r"^[0-9a-f]{64}$"
        )

    def test_rust_helper_requires_exact_recorded_argv(self):
        source = self.repo / "helper.rs"
        command_path = self.build / "rust/.helper.o.cmd"
        fake_rustc = self.root / "fake-rustc"
        fake_rustc.write_text("compiler bytes\n", encoding="utf-8")
        fake_rustc.chmod(0o755)
        source.write_text("const A: i32 = -EINVAL;\n", encoding="utf-8")
        command_path.parent.mkdir(parents=True)
        key = str(command_path.parent / "helper.o")
        command_path.write_text(
            "cmd_{0} := {1} --emit=obj={0} {2}\nsource_{0} := {2}\n".format(
                key, shlex.quote(str(fake_rustc)), shlex.quote(str(source))
            ),
            encoding="utf-8",
        )
        with self.assertRaises(capture.CaptureError):
            capture.capture_rust_source(
                "mcctrl",
                "helper.rs",
                "rust/.helper.o.cmd",
                self.repo,
                self.build,
                self.kernel,
                capture.config_provenance(self.kernel),
            )

    def test_rust_cmd_and_recorded_argv_compilers_must_match(self):
        source = self.repo / "helper.rs"
        command_path = self.build / "rust/.helper.o.cmd"
        first = self.root / "first-rustc"
        second = self.root / "second-rustc"
        source.write_text("const A: i32 = -EINVAL;\n", encoding="utf-8")
        for compiler, version in ((first, "one"), (second, "two")):
            compiler.write_text(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "  --version) printf '%s\\n' 'rustc {0}' ;;\n"
                "  *) exit 2 ;;\n"
                "esac\n".format(version),
                encoding="utf-8",
            )
            compiler.chmod(0o755)
        command_path.parent.mkdir(parents=True)
        key = str(command_path.parent / "helper.o")
        command_path.write_text(
            "cmd_{0} := {1} --emit=obj={0} {2}\nsource_{0} := {2}\n".format(
                key, shlex.quote(str(first)), shlex.quote(str(source))
            ),
            encoding="utf-8",
        )
        (command_path.parent / (command_path.name + ".argv.json")).write_text(
            json.dumps([str(second), "--emit=obj={0}".format(key), str(source)])
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(capture.CaptureError, "different compiler"):
            capture.capture_rust_source(
                "mcctrl",
                "helper.rs",
                "rust/.helper.o.cmd",
                self.repo,
                self.build,
                self.kernel,
                capture.config_provenance(self.kernel),
            )

    def test_configuration_requires_primary_and_generated_inputs(self):
        (self.kernel / "include/generated/autoconf.h").unlink()
        with self.assertRaises(capture.CaptureError):
            capture.config_provenance(self.kernel)

    def test_atomic_json_writer_produces_sorted_valid_capture(self):
        output = self.root / "evidence/capture.json"
        capture.write_capture(output, {"z": 2, "a": 1})
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"a": 1, "z": 2})
        self.assertTrue(output.read_text(encoding="utf-8").startswith('{\n  "a"'))


if __name__ == "__main__":
    unittest.main()
