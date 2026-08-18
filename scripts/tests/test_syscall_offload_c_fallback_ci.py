#!/usr/bin/env python3
"""Focused tests for the non-production syscall-offload C fallback lane."""

import json
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts/check-syscall-offload-c-fallback.sh"
WORKFLOW = REPO_ROOT / ".github/workflows/rust-x86_64-validation.yml"


class SyscallOffloadCFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.build = pathlib.Path(self.temporary.name) / "build"
        self.kernel = self.build / "kernel"
        self.kernel.mkdir(parents=True)
        self.evidence = self.kernel / "fallback.txt"

    def _write_fixture(self, rust_symbol=False):
        source = pathlib.Path(self.temporary.name) / "fallback.c"
        rust_definition = ""
        if rust_symbol:
            rust_definition = "void syscall_offload_wait_reply(void) {}\n"
        source.write_text(
            """
static const char fallback_marker[] __attribute__((used)) =
    "mcexec_v10: send_syscall cpu=%d";
static void __attribute__((used, noinline)) send_syscall(void) {}
long do_syscall(void) { send_syscall(); return fallback_marker[0]; }
long syscall_generic_forwarding(void) { return do_syscall(); }
"""
            + rust_definition,
            encoding="utf-8",
        )
        syscall_object = self.kernel / "syscall.c-fallback.o"
        subprocess.run(
            ["cc", "-O2", "-ffreestanding", "-c", str(source), "-o", str(syscall_object)],
            check=True,
        )
        (self.build / "CMakeCache.txt").write_text(
            "ENABLE_RUST_KERNEL:BOOL=ON\n",
            encoding="utf-8",
        )
        production_arguments = [
            "cc",
            "-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS",
            "-DMCKERNEL_RUST_SYSCALL_OFFLOAD",
            "-c",
            str(REPO_ROOT / "kernel/syscall.c"),
            "-o",
            "/production/syscall.c.o",
        ]
        fallback_arguments = [
            argument
            for argument in production_arguments
            if argument != "-DMCKERNEL_RUST_SYSCALL_OFFLOAD"
        ]
        (self.build / "compile_commands.json").write_text(
            json.dumps(
                [
                    {
                        "directory": str(REPO_ROOT),
                        "file": str(REPO_ROOT / "kernel/syscall.c"),
                        "arguments": production_arguments,
                    }
                ]
            ),
            encoding="utf-8",
        )
        (self.kernel / "mckernel-syscall-offload-c-fallback.compile.json").write_text(
            json.dumps(
                {
                    "schema": "mckernel-syscall-offload-c-fallback-compile-v2",
                    "source": str(REPO_ROOT / "kernel/syscall.c"),
                    "production_directory": str(REPO_ROOT),
                    "production_arguments": production_arguments,
                    "fallback_arguments": fallback_arguments,
                    "removed_defines": ["MCKERNEL_RUST_SYSCALL_OFFLOAD"],
                    "retained_defines": [
                        "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS"
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _run(self):
        return subprocess.run(
            [
                "bash",
                str(CHECKER),
                "--verify-only",
                "--build-dir",
                str(self.build),
                "--evidence",
                str(self.evidence),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def _prepare_replay_fixture(self):
        self._write_fixture()
        syscall_object = self.kernel / "syscall.c-fallback.o"
        template_object = pathlib.Path(self.temporary.name) / "template.o"
        syscall_object.replace(template_object)
        (
            self.kernel / "mckernel-syscall-offload-c-fallback.compile.json"
        ).unlink()

        fake_compiler = pathlib.Path(self.temporary.name) / "fake-cc.py"
        fake_compiler.write_text(
            """#!/usr/bin/env python3
import shutil
import sys

arguments = sys.argv[1:]
if "-DMCKERNEL_RUST_SYSCALL_OFFLOAD" in arguments:
    raise SystemExit(91)
if "-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS" not in arguments:
    raise SystemExit(92)
if any(argument in ("-MD", "-MMD", "-MF", "-MT", "-MQ")
       for argument in arguments):
    raise SystemExit(93)
if arguments.count("-o") != 1:
    raise SystemExit(94)
output = arguments[arguments.index("-o") + 1]
shutil.copyfile(%r, output)
"""
            % str(template_object),
            encoding="utf-8",
        )
        fake_compiler.chmod(0o755)

        database_path = self.build / "compile_commands.json"
        database = json.loads(database_path.read_text(encoding="utf-8"))
        database[0]["arguments"][0] = str(fake_compiler)
        database[0]["arguments"][1:1] = [
            "-MD",
            "-MP",
            "-MF",
            "/forbidden/fallback.d",
            "-MT",
            "/forbidden/syscall.c.o",
        ]
        database_path.write_text(json.dumps(database), encoding="utf-8")
        return database_path

    def _run_replay(self):
        return subprocess.run(
            [
                "bash",
                str(CHECKER),
                "--build-dir",
                str(self.build),
                "--production-build-dir",
                str(self.build),
                "--evidence",
                str(self.evidence),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def test_synthetic_c_fallback_fixture_passes(self):
        self._write_fixture()
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.evidence.read_text(encoding="utf-8")
        self.assertIn("mode=compile-object-oracle-only", report)
        self.assertIn("production_selection=unchanged", report)
        self.assertIn("production_rust_kernel=ON", report)
        self.assertIn("replayed_from_production_compile=true", report)
        self.assertIn("fallback_scope=kernel/syscall.c-only", report)
        self.assertIn("rust_policy_helpers=enabled", report)
        self.assertIn("final_image_link_claimed=false", report)
        self.assertIn("runtime_equivalence_claimed=false", report)
        self.assertIn("symbol.send_syscall=t", report)
        self.assertIn("symbol.syscall_offload_wait_reply=absent", report)
        self.assertTrue(report.endswith("status=PASS\n"))

    def test_production_argv_replay_removes_only_the_offload_selection(self):
        self._prepare_replay_fixture()
        result = self._run_replay()
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = json.loads(
            (
                self.kernel
                / "mckernel-syscall-offload-c-fallback.compile.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn(
            "-DMCKERNEL_RUST_SYSCALL_OFFLOAD",
            metadata["production_arguments"],
        )
        self.assertNotIn(
            "-DMCKERNEL_RUST_SYSCALL_OFFLOAD",
            metadata["fallback_arguments"],
        )
        self.assertIn(
            "-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS",
            metadata["fallback_arguments"],
        )
        self.assertNotIn("-MD", metadata["fallback_arguments"])
        self.assertNotIn("-MP", metadata["fallback_arguments"])
        self.assertNotIn("-MF", metadata["fallback_arguments"])

    def test_replay_rejects_missing_or_duplicate_production_selection(self):
        for count in (0, 2):
            with self.subTest(count=count):
                database_path = self._prepare_replay_fixture()
                database = json.loads(
                    database_path.read_text(encoding="utf-8")
                )
                database[0]["arguments"] = [
                    argument
                    for argument in database[0]["arguments"]
                    if argument != "-DMCKERNEL_RUST_SYSCALL_OFFLOAD"
                ]
                database[0]["arguments"].extend(
                    ["-DMCKERNEL_RUST_SYSCALL_OFFLOAD"] * count
                )
                database_path.write_text(
                    json.dumps(database), encoding="utf-8"
                )
                result = self._run_replay()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "expected exactly one production syscall-offload define",
                    result.stderr,
                )

    def test_replay_rejects_duplicate_syscall_source_argument(self):
        database_path = self._prepare_replay_fixture()
        database = json.loads(database_path.read_text(encoding="utf-8"))
        database[0]["arguments"].append(
            str(REPO_ROOT / "kernel/syscall.c")
        )
        database_path.write_text(json.dumps(database), encoding="utf-8")
        result = self._run_replay()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "expected exactly one kernel/syscall.c source argument",
            result.stderr,
        )

    def test_rust_compile_define_fails_closed(self):
        self._write_fixture()
        metadata_path = (
            self.kernel / "mckernel-syscall-offload-c-fallback.compile.json"
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["fallback_arguments"].append(
            "-DMCKERNEL_RUST_SYSCALL_OFFLOAD"
        )
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden Rust syscall-offload define", result.stderr)

    def test_missing_policy_helper_define_fails_closed(self):
        self._write_fixture()
        metadata_path = (
            self.kernel / "mckernel-syscall-offload-c-fallback.compile.json"
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["fallback_arguments"] = [
            argument
            for argument in metadata["fallback_arguments"]
            if argument != "-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS"
        ]
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("syscall-policy-helper define missing", result.stderr)

    def test_production_selection_must_be_exactly_one_offload_define(self):
        for replacement in ([], [
            "-DMCKERNEL_RUST_SYSCALL_OFFLOAD",
            "-DMCKERNEL_RUST_SYSCALL_OFFLOAD",
        ]):
            with self.subTest(replacement=replacement):
                self._write_fixture()
                metadata_path = (
                    self.kernel
                    / "mckernel-syscall-offload-c-fallback.compile.json"
                )
                metadata = json.loads(
                    metadata_path.read_text(encoding="utf-8")
                )
                metadata["production_arguments"] = [
                    argument
                    for argument in metadata["production_arguments"]
                    if argument != "-DMCKERNEL_RUST_SYSCALL_OFFLOAD"
                ] + replacement
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                result = self._run()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "production compile selection is not Rust offload",
                    result.stderr,
                )

    def test_rust_seam_symbol_fails_closed(self):
        self._write_fixture(rust_symbol=True)
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden Rust syscall-offload symbol", result.stderr)

    def test_workflow_runs_the_bounded_oracle_and_preserves_evidence(self):
        checker = CHECKER.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("ENABLE_RUST_KERNEL ON", checker)
        self.assertNotIn("-DENABLE_RUST_KERNEL=OFF", checker)
        self.assertNotIn("--target mckernel.img", checker)
        self.assertIn("production_arguments", checker)
        self.assertIn("fallback_arguments", checker)
        self.assertIn("subprocess.call(fallback_arguments", checker)
        self.assertNotIn("mcreboot", checker)
        self.assertNotIn("qemu", checker.lower())
        self.assertIn("Build and inspect C syscall-offload fallback oracle", workflow)
        self.assertIn("scripts/check-syscall-offload-c-fallback.sh", workflow)
        self.assertIn('--production-build-dir "$PRODUCTION_BUILD_DIR"', workflow)
        self.assertIn("evidence/syscall-offload-c-fallback.log", workflow)
        self.assertIn("mckernel-syscall-offload-c-fallback.txt", workflow)
        self.assertLess(
            workflow.index("Build Rust McKernel, IHK modules, and mcexec"),
            workflow.index("Build and inspect C syscall-offload fallback oracle"),
        )


if __name__ == "__main__":
    unittest.main()
