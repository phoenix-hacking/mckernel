"""Target-export-surface regression for the actual shutdown post-effect helper."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest

from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = ROOT / "host-kernel/native-rust/ihk_smp_x86_64.rs"
TARGET_KERNEL = Path("/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority1-output/source/linux-6.12.0-211.44.1.el10_2/rust/kernel")
RUSTC = "/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc"
TARGET_HASHES = {
    "lib.rs": "cde3e1e9608006f36c3a44ee11be848d8481c665f75b6d29937c9e9d9f76b0b6",
    "error.rs": "50181273de10264d9aa181ba573ef859945808ebf59b01453939de75f9b47ff2",
}


def generated():
    provider = PROVIDER.read_text()
    error = (TARGET_KERNEL / "error.rs").read_text()
    declaration = next(line for line in error.splitlines() if line.startswith("pub struct Error("))
    method = balanced_item(error, "pub fn to_errno(")
    function = balanced_item(provider, "fn shutdown_v6_post_effect(")
    constant = next(line for line in provider.splitlines() if line.startswith("const IHK_SMP_SHUTDOWN_V6_POST_EFFECT:"))
    # This complete local export surface intentionally has NO kernel::Error.
    # Struct and errno method bytes come from the actual selected Linux crate.
    return "\n".join([
        "mod kernel { pub mod error {", declaration, "impl Error {",
        "pub fn fixture_errno(value: i32) -> Self { Self(value) }", method, "} } }",
        constant, function,
        "#[test] fn every_linux_errno_retains_exact_post_effect_bits() {",
        "for errno in -4095..0 {",
        "let actual = shutdown_v6_post_effect(kernel::error::Error::fixture_errno(errno));",
        "assert_eq!(actual, (1_i64 << 62) | i64::from(errno as u32));",
        "assert!(actual > 0); assert_eq!(actual as u32 as i32, errno);",
        "} }",
    ])


class ShutdownNativeErrorPathTests(unittest.TestCase):
    def test_target_exports_and_actual_helper_are_exact(self):
        for name, expected in TARGET_HASHES.items():
            self.assertEqual(hashlib.sha256((TARGET_KERNEL / name).read_bytes()).hexdigest(), expected)
        lib = (TARGET_KERNEL / "lib.rs").read_text()
        self.assertIn("pub mod error;", lib)
        self.assertNotIn("pub use error::Error;", lib)
        self.assertNotIn("pub use error::{", lib)
        self.assertIn("fn shutdown_v6_post_effect(error: kernel::error::Error) -> i64", PROVIDER.read_text())
        fixture = generated()
        self.assertIn(balanced_item((TARGET_KERNEL / "error.rs").read_text(), "pub fn to_errno("), fixture)
        self.assertNotIn("pub use", fixture)

    def test_actual_helper_compiles_against_only_target_error_export(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92", RUSTC)
        self.assertIn("rustc 1.92.0", subprocess.run([rustc, "--version"], capture_output=True, text=True, check=True, timeout=10).stdout)
        directory = Path(tempfile.mkdtemp(prefix="shutdown-native-error-path-"))
        source = generated()
        print(f"retained_fixture_root={directory}", flush=True)
        variants = (("repaired", source), ("old_root_export", source.replace(
            "fn shutdown_v6_post_effect(error: kernel::error::Error)",
            "fn shutdown_v6_post_effect(error: kernel::Error)", 1)))
        for label, content in variants:
            path, binary = directory / (label + ".rs"), directory / label
            path.write_text(content)
            result = subprocess.run([rustc, "--edition=2021", "--test", "-Dwarnings", str(path), "-o", str(binary)],
                                    capture_output=True, text=True, timeout=30)
            for stream in ("stdout", "stderr"):
                (directory / (label + ".compile." + stream)).write_text(getattr(result, stream))
            (directory / (label + ".compile.status")).write_text(str(result.returncode) + "\n")
            print(f"{label} source_sha256={hashlib.sha256(content.encode()).hexdigest()} compile_status={result.returncode}", flush=True)
            if label == "old_root_export":
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error[E0412]", result.stderr)
                self.assertIn("cannot find type `Error` in module `kernel`", result.stderr)
                continue
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run = subprocess.run([str(binary), "--test-threads=1"], capture_output=True, text=True, timeout=10)
            for stream in ("stdout", "stderr"):
                (directory / (label + ".run." + stream)).write_text(getattr(run, stream))
            (directory / (label + ".run.status")).write_text(str(run.returncode) + "\n")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("1 passed; 0 failed", run.stdout)
            print(run.stdout, end="", flush=True)


if __name__ == "__main__":
    unittest.main()
