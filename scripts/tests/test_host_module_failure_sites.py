#!/usr/bin/env python3
"""Synthetic tests for compiler-backed host-module failure-site capture."""

import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_failure_sites as capture  # noqa: E402
import record_compiler_argv as recorder  # noqa: E402


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
