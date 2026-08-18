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
        self.object_dir = self.kernel / "CMakeFiles/mckernel.img.dir"
        self.object_dir.mkdir(parents=True)
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
        syscall_object = self.object_dir / "syscall.c.o"
        subprocess.run(
            ["cc", "-O2", "-ffreestanding", "-c", str(source), "-o", str(syscall_object)],
            check=True,
        )
        subprocess.run(
            [
                "cc",
                "-O2",
                "-ffreestanding",
                "-nostdlib",
                "-static",
                "-Wl,-e,do_syscall",
                str(source),
                "-o",
                str(self.kernel / "mckernel.img"),
            ],
            check=True,
        )
        (self.kernel / "mckernel.img.map").write_text(
            " .text 0x0 0x10 CMakeFiles/mckernel.img.dir/syscall.c.o\n",
            encoding="utf-8",
        )
        (self.build / "CMakeCache.txt").write_text(
            "ENABLE_RUST_KERNEL:BOOL=OFF\n"
            "ENABLE_RUST_IHK_MODULE_HELPERS:BOOL=OFF\n"
            "ENABLE_RUST_USER_TOOLS:BOOL=OFF\n",
            encoding="utf-8",
        )
        compile_entry = {
            "directory": str(REPO_ROOT),
            "file": str(REPO_ROOT / "kernel/syscall.c"),
            "arguments": ["cc", "-c", str(REPO_ROOT / "kernel/syscall.c")],
        }
        (self.build / "compile_commands.json").write_text(
            json.dumps([compile_entry]), encoding="utf-8"
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

    def test_synthetic_c_fallback_fixture_passes(self):
        self._write_fixture()
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.evidence.read_text(encoding="utf-8")
        self.assertIn("mode=test-oracle-only", report)
        self.assertIn("production_selection=unchanged", report)
        self.assertIn("symbol.send_syscall=t", report)
        self.assertIn("symbol.syscall_offload_wait_reply=absent", report)
        self.assertTrue(report.endswith("status=PASS\n"))

    def test_rust_compile_define_fails_closed(self):
        self._write_fixture()
        database_path = self.build / "compile_commands.json"
        database = json.loads(database_path.read_text(encoding="utf-8"))
        database[0]["arguments"].append("-DMCKERNEL_RUST_SYSCALL_OFFLOAD")
        database_path.write_text(json.dumps(database), encoding="utf-8")
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden Rust syscall-offload define", result.stderr)

    def test_rust_link_object_fails_closed(self):
        for map_entry in (
            " .text 0x10 0x10 rust/mckernel_rust.o\n",
            " .text 0x10 0x10 libowners.a(mckernel_rust.o)\n",
        ):
            with self.subTest(map_entry=map_entry):
                self._write_fixture()
                with (self.kernel / "mckernel.img.map").open(
                    "a", encoding="utf-8"
                ) as stream:
                    stream.write(map_entry)
                result = self._run()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Rust kernel object leaked", result.stderr)

    def test_rust_seam_symbol_fails_closed(self):
        self._write_fixture(rust_symbol=True)
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden Rust syscall-offload symbol", result.stderr)

    def test_workflow_runs_the_bounded_oracle_and_preserves_evidence(self):
        checker = CHECKER.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("-DENABLE_RUST_KERNEL=OFF", checker)
        self.assertIn("-DENABLE_RUST_IHK_MODULE_HELPERS=OFF", checker)
        self.assertIn("-DENABLE_RUST_USER_TOOLS=OFF", checker)
        self.assertIn('--target mckernel.img -j"$JOBS"', checker)
        self.assertNotIn("mcreboot", checker)
        self.assertNotIn("qemu", checker.lower())
        self.assertIn("Build and inspect C syscall-offload fallback oracle", workflow)
        self.assertIn("scripts/check-syscall-offload-c-fallback.sh", workflow)
        self.assertIn("evidence/syscall-offload-c-fallback.log", workflow)
        self.assertIn("mckernel-syscall-offload-c-fallback.txt", workflow)
        self.assertLess(
            workflow.index("Build Rust McKernel, IHK modules, and mcexec"),
            workflow.index("Build and inspect C syscall-offload fallback oracle"),
        )


if __name__ == "__main__":
    unittest.main()
