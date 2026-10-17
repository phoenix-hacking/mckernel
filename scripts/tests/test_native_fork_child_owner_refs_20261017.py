"""Execute complete production ForkChildOwner acquisition and Drop with fake Linux refs."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = ROOT / "host-kernel/native-rust/smp_application.rs"
TEMPLATE = ROOT / "scripts/tests/fixtures/native_fork_child_owner_refs_20261017.rs"
RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/"
             "1.92.0-x86_64-unknown-linux-gnu/bin/rustc")


def owner_body():
    source = PRODUCTION.read_text()
    begin = source.index("// Structural MM and referenced TGID ownership")
    end = source.index("// BEGIN FORK BACKEND RESERVATION", begin)
    return source[begin:end]


def generated_source():
    actual = owner_body()
    missing_put = "            unsafe { bindings::put_pid(pid.as_ptr()) };"
    decrement = "let old = count.fetch_sub(1, Ordering::SeqCst);"
    assert actual.count(missing_put) == 2
    assert actual.count(decrement) == 1
    replacements = {
        "ACTUAL_OWNER": actual,
        "MISSING_PUT_MUTANT": actual.replace(missing_put, "            // Deliberately removed put_pid mutation.", 1),
        "CORRUPT_DROP_MUTANT": actual.replace(decrement, "let old = count.fetch_add(1, Ordering::SeqCst);"),
    }
    source = TEMPLATE.read_text()
    for marker, value in replacements.items():
        assert source.count("@" + marker + "@") == 1
        source = source.replace("@" + marker + "@", value)
    return source


class NativeForkChildOwnerRefTests(unittest.TestCase):
    def test_complete_actual_owner_is_extracted(self):
        actual = owner_body()
        self.assertEqual(generated_source().count(actual), 1)
        self.assertIn("unsafe impl Send for ForkChildOwner", actual)
        self.assertIn("unsafe impl Sync for ForkChildOwner", actual)
        self.assertIn("impl Drop for ForkChildOwner", actual)

    def test_template_has_six_runtime_controls_and_no_unexpanded_markers(self):
        self.assertEqual(TEMPLATE.read_text().count("#[test]"), 6)
        self.assertNotIn("@ACTUAL_OWNER@", generated_source())
        self.assertNotIn("@MISSING_PUT_MUTANT@", generated_source())
        self.assertNotIn("@CORRUPT_DROP_MUTANT@", generated_source())

    def test_actual_owner_reference_vectors(self):
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-child-owner-refs-20261017-"))
        print("fork_child_owner_refs_evidence=" + str(attempt), flush=True)
        source, binary = attempt / "generated.rs", attempt / "test"
        source.write_text(generated_source())

        def captured(label, command, timeout):
            (attempt / (label + ".command.json")).write_text(json.dumps(command) + "\n")
            try:
                result = subprocess.run(command, capture_output=True, timeout=timeout,
                                        env={**os.environ, "RUST_TEST_THREADS": "1"})
            except subprocess.TimeoutExpired as error:
                (attempt / (label + ".stdout")).write_bytes(error.stdout or b"")
                (attempt / (label + ".stderr")).write_bytes(error.stderr or b"")
                (attempt / (label + ".status.json")).write_text(json.dumps({"timeout_seconds": timeout, "returncode": None}) + "\n")
                raise
            (attempt / (label + ".stdout")).write_bytes(result.stdout)
            (attempt / (label + ".stderr")).write_bytes(result.stderr)
            (attempt / (label + ".status.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result

        version = captured("version", [str(RUSTC), "--version"], 15)
        self.assertTrue(version.stdout.startswith(b"rustc 1.92.0 "), version.stdout)
        captured("compile", [str(RUSTC), "--edition=2021", "--test", str(source), "-o", str(binary)], 60)
        result = captured("run", [str(binary), "--test-threads=1"], 30)
        self.assertIn(b"6 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
