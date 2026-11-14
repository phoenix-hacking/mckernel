"""Bounded actual Linux utility/reference using accepted cancellation ownership."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

import harness

ROOT = Path(__file__).resolve().parent
APP = ROOT / "file-stream"
PAYLOAD = bytes(range(256)) * 40 + b"\x00tail\xff\n"
EXPECTED = b"file-stream: bytes=10247 fnv1a64=4cc9ef3c2e0e9a1c verified\n"
record = {"task": "practical-file-stream-app-20261018-1", "status": "RUNNING",
          "scope": "Useful file/stream application for functional OS scope; host Linux reference only",
          "native_acceptance": False, "guest_eligible": False,
          "toolchain": "Host Ubuntu GCC9.4/libc2.31; requires reviewed guest-profile recompilation",
          "environment": dict(os.environ), "affinity": sorted(os.sched_getaffinity(0)),
          "limits": {name: resource.getrlimit(getattr(resource, name)) for name in
                     ["RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_NOFILE", "RLIMIT_FSIZE", "RLIMIT_CORE"]},
          "commands": [], "artifacts": {}, "observations": [],
          "next_executable_observation": "Independent C utility/oracle review before guest-profile recompilation or staging"}


def identity(path):
    path = Path(path)
    data = path.read_bytes()
    return {"resolved": str(path.resolve()), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save():
    (ROOT / "report.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


def run(label, argv, expected_rc=0, expected_out=None, expected_err=None):
    entry = {"label": label, "argv": argv, "expected_returncode": expected_rc}
    record["commands"].append(entry)

    def checkpoint(name, child, result):
        if name == "finished":
            entry["process"] = result

    try:
        result = harness.run(ROOT, label, argv, checkpoint=checkpoint, wall_seconds=30)
        entry["returncode"] = result["returncode"]
    except BaseException as error:
        entry["exception"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        for suffix in ["stdout", "stderr"]:
            path = ROOT / (label + "." + suffix)
            if path.exists():
                entry[suffix] = identity(path)
        save()
    assert entry["returncode"] == expected_rc, label + ": wrong exit"
    if expected_out is not None:
        assert (ROOT / (label + ".stdout")).read_bytes() == expected_out, label + ": wrong stdout"
    if expected_err is not None:
        assert (ROOT / (label + ".stderr")).read_bytes() == expected_err, label + ": wrong stderr"


def main():
    assert record["affinity"] == [7]
    assert record["limits"]["RLIMIT_AS"] == (1073741824, 1073741824)
    assert identity(ROOT / "harness.py")["sha256"] == "ad74ec8c9d952643122dd4cd8e3af56052823c0896142fb8c225cac5ea13a6eb"
    assert identity("/usr/bin/gcc")["sha256"] == "6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f"
    assert identity(sys.executable)["sha256"] == "8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb"
    harness.install_handlers()
    run("compiler-version", ["/usr/bin/gcc", "--version"])
    run("build", ["/usr/bin/gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                  "-fno-pie", "-no-pie", str(ROOT / "file-stream.c"), "-o", str(APP)],
        expected_out=b"", expected_err=b"")
    (ROOT / "input.bin").write_bytes(PAYLOAD)
    run("linux-copy", [str(APP), "copy-check", str(ROOT / "input.bin"), str(ROOT / "output.bin")],
        0, EXPECTED, b"")
    assert (ROOT / "output.bin").read_bytes() == PAYLOAD
    assert (ROOT / "input.bin").read_bytes() == PAYLOAD
    record["observations"].append("10247-byte output byte-exact including embedded NUL/all byte values and multiple 4096-byte boundaries")
    (ROOT / "empty.bin").write_bytes(b"")
    run("linux-empty", [str(APP), "copy-check", str(ROOT / "empty.bin"), str(ROOT / "empty-copy.bin")],
        0, b"file-stream: bytes=0 fnv1a64=cbf29ce484222325 verified\n", b"")
    assert (ROOT / "empty-copy.bin").read_bytes() == b""
    run("linux-missing", [str(APP), "copy-check", str(ROOT / "missing.bin"), str(ROOT / "missing-output.bin")],
        65, b"", b"file-stream: input open failed: ENOENT\n")
    assert not (ROOT / "missing-output.bin").exists()
    sentinel = b"existing destination must remain\x00unchanged\n"
    (ROOT / "existing-output.bin").write_bytes(sentinel)
    run("linux-output-failure", [str(APP), "copy-check", str(ROOT / "input.bin"), str(ROOT / "existing-output.bin")],
        66, b"", b"file-stream: output open failed: EEXIST\n")
    assert (ROOT / "existing-output.bin").read_bytes() == sentinel
    (ROOT / "directory-input").mkdir()
    run("linux-read-failure-cleanup", [str(APP), "copy-check", str(ROOT / "directory-input"), str(ROOT / "incomplete-output.bin")],
        67, b"", b"file-stream: copy read failed: EISDIR\n")
    assert not (ROOT / "incomplete-output.bin").exists()
    record["observations"].append("Actual missing input/open failure, existing-output preservation, and read-error incomplete-output unlink verified")
    for path in list(ROOT.glob("*.py")) + list(ROOT.glob("*.sh")) + list(ROOT.glob("*.c")) + list(ROOT.glob("*.bin")) + [APP, Path(sys.executable),
                 Path("/usr/bin/gcc"), Path("/usr/lib/gcc/x86_64-linux-gnu/9/cc1"), Path("/usr/bin/ld"),
                 Path("/lib/x86_64-linux-gnu/libc.so.6"), Path("/lib64/ld-linux-x86-64.so.2"),
                 Path("/usr/bin/taskset"), Path("/usr/bin/prlimit"), Path("/usr/bin/timeout"), ROOT / "README.txt"]:
        record["artifacts"][str(path)] = identity(path)
    assert sum(path.stat().st_size for path in ROOT.rglob("*") if path.is_file()) < 900000
    record["status"] = "PASS_LINUX_FILE_STREAM_READY_FOR_REVIEW"


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        record["status"] = "FAIL_PRESERVED_STOP"
        record["failure"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        save()
