"""Changed complete-exec ownership and HOST lifetime/error qualification.

Compile the actual new Rust module against the existing real ABI source. The
observation providers exercise request/context/buffer lifetimes and original
success/error order; they are never production provider or native evidence.
The separate full-object C/Rust ABI/readback and genuine provider image checks
remain required at integration. No test in this file accesses a device/service.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUST = ROOT / "kernel/rust"
SELECT = "MCKERNEL_RUST_F03_EXECVEAT_COMPLETE"
PROVIDER_MACROS = (
    "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS", "MCKERNEL_RUST_F03_EXEC_DEFINED_TAIL",
    "MCKERNEL_RUST_DO_SYSCALL_OUTER", "MCKERNEL_RUST_F03_PERF_OWNER_PROTOCOL",
)
RUST_CFGS = (
    "native_linux_irq_work_v6_12", "enable_profile", "enable_perf", "enable_rusage",
    "f03_do_syscall_outer_candidate", "f03_perf_owner_protocol",
    "f03_execveat_complete_candidate",
)


class CompleteExecTests(unittest.TestCase):
    def checked(self, command, **kwargs):
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, **kwargs)
        self.assertEqual(result.returncode, 0,
                         "command failed: " + repr(command) + "\n" + result.stdout + result.stderr)
        return result.stdout

    def test_selected_c_bodies_are_excluded_atomically_and_fallback_is_retained(self):
        compiler = os.environ.get("CC") or shutil.which("cc")
        self.assertIsNotNone(compiler, "HOST C preprocessor is required")
        source = (ROOT / "kernel/syscall.c").read_text()
        start = source.index("/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n"
                             " * Complete Rust exec and its exact callback are selected atomically.")
        end = source.index("#line 7721", start)
        body = source[start:end]
        for selected in (False, True):
            with self.subTest(selected=selected):
                command = [compiler, "-E", "-P", "-x", "c", "-"]
                command += ["-D" + macro + "=1" for macro in PROVIDER_MACROS]
                if selected:
                    command.append("-D" + SELECT + "=1")
                output = self.checked(command, input=body)
                self.assertEqual(len(re.findall(r"static int do_execveat\([^;]*?\)\s*\{", output)),
                                 0 if selected else 1)
                self.assertEqual(len(re.findall(r"(?m)^syscall_execveat_bridge\([^;]*?\)\s*\{", output)),
                                 0 if selected else 1)
                if selected:
                    self.assertIn("extern int syscall_execveat_bridge", output)
                    self.assertIn("f03_execveat_complete_c_abi_words", output)
        rejected = subprocess.run([compiler, "-E", "-P", "-x", "c", "-", "-D" + SELECT + "=1"],
                                  input=body, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("complete Rust exec requires its paired ordinary x86/provider cohort", rejected.stderr)
        # The actual production predicate must select the matching module and C
        # exclusion together; broad profile conditions are inherited unchanged.
        cmake = (ROOT / "kernel/CMakeLists.txt").read_text()
        self.assertIn('if (MCKERNEL_PERF_OWNER_PROTOCOL_SELECTED)\n'
                      '            set(MCKERNEL_EXECVEAT_COMPLETE_SELECTED ON)', cmake)
        self.assertIn('"--cfg" "f03_execveat_complete_candidate"', cmake)
        self.assertIn('if (MCKERNEL_EXECVEAT_COMPLETE_SELECTED)\n'
                      '    set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY\n'
                      '        COMPILE_DEFINITIONS ' + SELECT + ')', cmake)
        policy = (RUST / "syscall_policy.rs").read_text()
        self.assertIn('#[link_name = "syscall_execveat_bridge"]\n'
                      '    fn f03_execveat_selected_provider(', policy)
        self.assertEqual(policy.count("Some(f03_execveat_selected_provider)"), 2)

    def test_actual_rust_exec_module_preserves_error_and_lifetime_contracts(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        self.assertIsNotNone(compiler, "HOST Rust compiler is required")
        fixture = (ROOT / "scripts/tests/fixtures/f03_execveat_complete_observer.rs").read_text()
        fixture = fixture.replace("@ABI@", str(RUST / "abi.rs")) \
                         .replace("@MODULE@", str(RUST / "f03_execveat_complete.rs"))
        environment = dict(os.environ)
        environment["MCKERNEL_DO_SYSCALL_C_FILE"] = str(ROOT / "kernel/syscall.c")
        environment["MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS"] = "0"
        with tempfile.TemporaryDirectory(prefix="f03-exec-complete-") as temporary:
            directory = Path(temporary)
            source, binary = directory / "observer.rs", directory / "observer"
            source.write_text(fixture)
            command = [compiler, "--edition=2021", "-C", "opt-level=2", str(source), "-o", str(binary)]
            for cfg in RUST_CFGS:
                command += ["--cfg", cfg]
            self.checked(command, env=environment)
            output = self.checked([str(binary)])
            self.assertIn("PASS 29 complete exec cases\n", output)


if __name__ == "__main__":
    unittest.main()
