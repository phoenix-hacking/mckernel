#!/usr/bin/env python3
"""Fixed entry point for the explicit isolated UID0 collector infrastructure plan."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import traceback

ROOT = Path("/work")
INPUTS = Path("/inputs")
SHA_STDOUT = (b"PASS empty\nPASS abc\nPASS multi-56\nPASS boundary-55\nPASS boundary-56\n"
              b"PASS boundary-63\nPASS boundary-64\nPASS boundary-65\nPASS rejected-update-preserves-state\n")


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())


def check(condition, message):
    if not condition: raise AssertionError(message)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def verify_inputs(manifest):
    expected = {"linux-collector", "fixture", "sha256-harness", "root_inside.py", "run_collector_tests.py", "supervisor.py"}
    check(set(manifest["files"]) == expected, "exact root-profile input set")
    for name, item in manifest["files"].items():
        path = INPUTS / name
        before = path.stat()
        check(not path.is_symlink() and stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= 4 * 1024 * 1024, "root input type/size")
        raw = path.read_bytes()
        check(len(raw) == item["size_bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], "root input exact bytes")
        check(stat.S_IMODE(before.st_mode) == item["mode"], "root input mode")


def check_collection(report, attempt, expected_stdout):
    check(report.get("status") == "COMPLETED" and report.get("cleanup_complete") is True, "actual subprocess collection/cleanup")
    raw = report.get("raw_wait_status")
    check(type(raw) is int and os.WIFEXITED(raw) and os.WEXITSTATUS(raw) == 0, "actual subprocess raw zero exit")
    if expected_stdout is not None: check((attempt / "stdout.bin").read_bytes() == expected_stdout, "literal subprocess stdout")
    check((attempt / "stderr.bin").read_bytes() == b"", "literal empty subprocess stderr")
    for name in ("stdout", "stderr"):
        entry = report["streams"][name]
        check(entry.get("eof") is True and entry.get("discarded_observed_bytes") == 0, "complete subprocess streams")


def main():
    record = {"schema_version": 1, "kind": "linux-sealed-root-profile-actual-collection", "status": "FAIL",
              "application_acceptance": False, "backend_enabled": False}
    try:
        manifest_fd = os.open(str(INPUTS / "inputs.json"), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(manifest_fd)
            check(stat.S_ISREG(metadata.st_mode) and 0 <= metadata.st_size <= 65536, "profile manifest type/size")
            with os.fdopen(manifest_fd, "rb", closefd=False) as stream: raw_manifest = stream.read(65537)
            check(len(raw_manifest) == metadata.st_size, "profile manifest bound")
        finally:
            os.close(manifest_fd)
        manifest = strict_json(raw_manifest)
        record["inputs_manifest_sha256"] = hashlib.sha256(raw_manifest).hexdigest()
        record["profile_nonce"] = manifest["profile_nonce"]
        check(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1 and manifest["kind"] == "linux-sealed-root-profile-inputs" and
              manifest["application_acceptance"] is False and manifest["backend_enabled"] is False, "profile manifest kind")
        verify_inputs(manifest)
        for path, key in ((ROOT, "work_directory"), (INPUTS, "inputs_directory")):
            value = path.stat()
            actual = {"device": value.st_dev, "inode": value.st_ino, "uid": value.st_uid, "gid": value.st_gid,
                      "mode": stat.S_IMODE(value.st_mode)}
            check(stat.S_ISDIR(value.st_mode) and actual == manifest[key], "actual mounted directory identity: " + key)
        status_raw = Path("/proc/self/status").read_bytes()
        with (ROOT / "actual-proc-status.bin").open("xb") as stream:
            check(stream.write(status_raw) == len(status_raw), "complete exclusive proc-status write")
            stream.flush(); os.fsync(stream.fileno())
        rows = {}
        for line in status_raw.decode("ascii").splitlines():
            if ":" in line:
                key, value = line.split(":", 1); rows[key] = value.strip()
        record["uid"] = os.getuid(); record["euid"] = os.geteuid()
        record["gid"] = os.getgid(); record["egid"] = os.getegid(); record["groups"] = os.getgroups()
        check(record["uid"] == record["euid"] == record["gid"] == record["egid"] == 0 and record["groups"] == [0], "actual root identity/group profile")
        for key in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
            check(int(rows[key], 16) == 0, "actual empty " + key)
        check(rows["NoNewPrivs"] == "1", "actual no-new-privileges")
        for path in (Path("/"), INPUTS, Path("/workspace")):
            check(os.statvfs(path).f_flag & os.ST_RDONLY, "actual readonly filesystem: " + str(path))
        check(not (os.statvfs(ROOT).f_flag & os.ST_RDONLY), "actual dedicated writable work mount")
        save(ROOT / "observed-profile.json", {**record, "proc_status_rows": rows})
        spec = importlib.util.spec_from_file_location("root_profile_supervisor", INPUTS / "supervisor.py")
        supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
        sha_attempt = ROOT / "sha-collection"
        sha = supervisor.run_supervised([str(INPUTS / "sha256-harness")], cwd=str(ROOT), env={}, attempt_dir=sha_attempt,
                                        timeout_seconds=10, cleanup_timeout_seconds=15, stdout_limit_bytes=65536, stderr_limit_bytes=65536)
        save(ROOT / "sha-returned.json", sha)
        check_collection(sha, sha_attempt, SHA_STDOUT)
        driver_attempt = ROOT / "driver-collection"
        command = ["/usr/bin/python3", str(INPUTS / "run_collector_tests.py"), "--collector", str(INPUTS / "linux-collector"),
                   "--fixture", str(INPUTS / "fixture"), "--supervisor", str(INPUTS / "supervisor.py"),
                   "--attempt-root", str(ROOT / "cases"), "--root-infrastructure"]
        driver = supervisor.run_supervised(command, cwd=str(ROOT), env={"TMPDIR": "/work/tmp", "PYTHONDONTWRITEBYTECODE": "1"},
                                           attempt_dir=driver_attempt, timeout_seconds=180, cleanup_timeout_seconds=15,
                                           stdout_limit_bytes=65536, stderr_limit_bytes=65536)
        save(ROOT / "driver-returned.json", driver)
        check_collection(driver, driver_attempt, None)
        result = strict_json((ROOT / "cases/result.json").read_bytes())
        check(result.get("status") == "PASS_INFRASTRUCTURE_ONLY" and len(result.get("cases", [])) == 25 and
              result.get("application_acceptance") is False and result.get("backend_enabled") is False, "actual inner assertions")
        verify_inputs(manifest)
        record["status"] = "PASS_LINUX_INFRASTRUCTURE_ONLY"
    except BaseException as error:
        record["first_failure"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        print(record["first_failure"]["traceback"], file=sys.stderr, flush=True)
    finally:
        save(ROOT / "root-result.json", record)
    return 0 if record["status"] == "PASS_LINUX_INFRASTRUCTURE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
