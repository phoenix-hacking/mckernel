"""One actual Linux fork/exec/wait reference; no McKernel capability credit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/application-tests/practical_process_exec_wait.c"
# Frozen independently before compilation; never learned from observed output.
EXPECTED = b"process-exec-wait child=37 output=verified eof=1 echild=1\n"


class ProcessExecWaitReference(unittest.TestCase):
    def test_real_linux_process_roundtrip(self):
        out = Path(os.environ["PRACTICAL_PROCESS_EXEC_EVIDENCE"])
        out.mkdir(mode=0o700, exist_ok=False)
        env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
        for name in ("HOME", "TMPDIR"):
            private = Path(os.environ[name])
            private.relative_to(out.parent.resolve(strict=True))
            self.assertEqual(private.resolve(strict=True), private)
            self.assertTrue(private.is_dir())
            self.assertEqual(private.stat().st_uid, os.getuid())
            self.assertEqual(private.stat().st_mode & 0o077, 0)
            env[name] = str(private)
        (out / "expected.stdout").write_bytes(EXPECTED)
        (out / "expected.stderr").write_bytes(b"")
        (out / "oracle.json").write_text(json.dumps({
            "freeze": "Written before first compiler invocation",
            "stdout_hex": EXPECTED.hex(), "stderr_hex": "", "exit_code": 0,
            "child_expected": "PRACTICAL_PROCESS_EXEC_CHILD\n, exit37",
            "meaning": "Actual parent verifies fork child, successful execve control flow, exact captured marker/EOF, exact child waitPID/exited37 and second wait ECHILD.",
        }, indent=2) + "\n")
        snapshot = out / "executed.c"
        snapshot.write_bytes(SOURCE.read_bytes())
        binary = out / "app"
        sequence = 0

        def capture(label, argv, cwd=out):
            nonlocal sequence
            sequence += 1
            stem = out / f"{sequence:02d}-{label}"
            stem.with_suffix(".command.json").write_text(json.dumps({
                "argv": argv, "environment": env, "cwd": str(cwd),
            }, indent=2) + "\n")
            try:
                result = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=15)
            except subprocess.TimeoutExpired as error:
                stem.with_suffix(".stdout").write_bytes(error.stdout or b"")
                stem.with_suffix(".stderr").write_bytes(error.stderr or b"")
                stem.with_suffix(".result.json").write_text(json.dumps({"timeout_seconds": 15}) + "\n")
                raise
            stem.with_suffix(".stdout").write_bytes(result.stdout)
            stem.with_suffix(".stderr").write_bytes(result.stderr)
            stem.with_suffix(".result.json").write_text(json.dumps({
                "returncode": result.returncode,
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            }, indent=2) + "\n")
            return result

        compiled = capture("compile", [
            "/usr/bin/gcc", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
            "-static", "-fno-pie", "-no-pie", "-Wl,-z,noexecstack", "-MD", "-MF",
            str(out / "app.d"), str(snapshot), "-o", str(binary),
        ])
        self.assertEqual(compiled.returncode, 0, compiled.stderr.decode())
        inspected = capture("readelf", ["/usr/bin/readelf", "-W", "-h", "-l", str(binary)])
        self.assertEqual(inspected.returncode, 0, inspected.stderr.decode())
        text = inspected.stdout.decode()
        self.assertIn("EXEC (Executable file)", text)
        self.assertIn("Advanced Micro Devices X86-64", text)
        headers = [line.split() for line in text.splitlines() if line.split() and
                   line.split()[0] in ("LOAD", "GNU_STACK", "INTERP", "DYNAMIC")]
        self.assertFalse(any(row[0] in ("INTERP", "DYNAMIC") for row in headers))
        self.assertFalse(any(row[0] == "LOAD" and "W" in "".join(row[6:-1]) and
                             "E" in "".join(row[6:-1]) for row in headers))
        self.assertTrue(any(row[0] == "GNU_STACK" and "E" not in "".join(row[6:-1])
                            for row in headers))
        cwd = out / "case/work"
        cwd.mkdir(parents=True)
        reference = capture("linux-reference", ["/usr/bin/timeout", "-k", "1s", "9s", str(binary)], cwd)
        self.assertEqual(reference.returncode, 0, reference.stderr.decode())
        self.assertEqual(reference.stdout, EXPECTED)
        self.assertEqual(reference.stderr, b"")


if __name__ == "__main__":
    unittest.main(failfast=True)
