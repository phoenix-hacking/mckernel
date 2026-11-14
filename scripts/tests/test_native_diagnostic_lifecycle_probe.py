"""Source checks by default; compiled actual-main tests require dispatcher admission.

Opt in with NATIVE_LIFECYCLE_COMPILE=1 and NATIVE_LIFECYCLE_EVIDENCE pointing
at a fresh directory under the authorized scratch evidence root. No live device
is ever opened: the compiled harness replaces open/ioctl/close exclusively.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/application-tests/native_diagnostic_lifecycle_probe.c"
IHK_REV = "3114d9e7101ad52030eb3effa849a5c108972a1f"
HEADERS = ("ihk_host_user.h", "status.h", "ihk_monitor.h", "ihk_debug.h")


def header(name):
    return subprocess.run(
        ["/usr/bin/git", "-C", str(ROOT / "ihk"), "show",
         f"{IHK_REV}:linux/include/ihk/{name}"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
    ).stdout


HARNESS = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <ihk/ihk_host_user.h>
static int step, opens, closes;
static const char *scenario;
static int fake_open(const char *path, int flags);
static int fake_ioctl(int fd, unsigned long request, unsigned long argument);
static int fake_close(int fd);
#define LIFECYCLE_OPEN fake_open
#define LIFECYCLE_IOCTL fake_ioctl
#define LIFECYCLE_CLOSE fake_close
#define main lifecycle_probe_main
#include "PROBE_SOURCE"
#undef main
static int fake_open(const char *path, int flags)
{
    assert(++opens == 1 && step == 0);
    assert(strcmp(path, "/dev/mcos12") == 0);
    assert(flags == (O_RDWR | O_CLOEXEC | O_NOFOLLOW));
    assert(errno == 0);
    if (!strcmp(scenario, "open_errno")) { errno = ENOENT; return -1; }
    return 41;
}
static int fake_ioctl(int fd, unsigned long request, unsigned long argument)
{
    assert(fd == 41 && argument == 0 && errno == 0);
    step++;
    assert(step <= 3);
    assert(request == (step == 2 ? IHK_OS_SHUTDOWN : IHK_OS_QUERY_STATUS));
    if (step == 1) {
        if (!strcmp(scenario, "before_errno")) { errno = ENODEV; return -1; }
        if (!strcmp(scenario, "before_unknown")) return IHK_OS_STATUS_COUNT;
        if (!strcmp(scenario, "repeat")) return IHK_OS_STATUS_NOT_BOOTED;
        if (!strcmp(scenario, "ready")) return IHK_OS_STATUS_READY;
        if (!strcmp(scenario, "retry_shutdown")) return IHK_OS_STATUS_SHUTDOWN;
        return IHK_OS_STATUS_RUNNING;
    }
    if (step == 2) {
        if (!strcmp(scenario, "busy")) { errno = EBUSY; return -1; }
        if (!strcmp(scenario, "negative_errno")) { errno = EIO; return -1; }
        if (!strcmp(scenario, "unsupported")) { errno = ENOSYS; return -1; }
        if (!strcmp(scenario, "interrupted")) { errno = EINTR; return -1; }
        if (!strcmp(scenario, "positive_shutdown")) return 1;
        return 0;
    }
    if (!strcmp(scenario, "busy")) return IHK_OS_STATUS_RUNNING;
    if (!strcmp(scenario, "negative_errno")) return IHK_OS_STATUS_SHUTDOWN;
    if (!strcmp(scenario, "wrong_after")) return IHK_OS_STATUS_RUNNING;
    if (!strcmp(scenario, "after_errno")) { errno = EIO; return -1; }
    if (!strcmp(scenario, "after_unknown")) return IHK_OS_STATUS_COUNT;
    return IHK_OS_STATUS_NOT_BOOTED;
}
static int fake_close(int fd)
{
    assert(fd == 41 && ++closes == 1 && errno == 0);
    if (!strcmp(scenario, "close_errno")) { errno = EINTR; return -1; }
    return 0;
}
int main(int argc, char **argv)
{
    int rc;
    assert(argc >= 2);
    scenario = argv[1];
    rc = lifecycle_probe_main(argc - 1, argv + 1);
    if (rc == 2) assert(opens == 0 && step == 0 && closes == 0);
    else if (!strcmp(scenario, "open_errno"))
        assert(opens == 1 && step == 0 && closes == 0);
    else {
        assert(opens == 1 && closes == 1);
        assert(step == ((!strcmp(scenario, "before_errno") ||
                         !strcmp(scenario, "before_unknown")) ? 1 : 3));
    }
    return rc;
}
'''


class SourceContract(unittest.TestCase):
    def test_exact_pinned_requests_and_status_order(self):
        requests = header("ihk_host_user.h").decode()
        abi = (ROOT / "host-kernel/native-rust/abi/x86_64.rs").read_text()
        for name, expected in (("IHK_OS_SHUTDOWN", 0x112A02),
                               ("IHK_OS_QUERY_STATUS", 0x112A03)):
            self.assertEqual(int(re.search(r"#define\s+" + name + r"\s+(0x[0-9a-f]+)", requests)[1], 16), expected)
            self.assertEqual(int(re.search(r"pub const " + name + r": u32 = (0x[0-9a-f_]+)", abi)[1].replace("_", ""), 16), expected)
        enum = header("status.h").decode().split("enum ihk_os_status {", 1)[1].split("};", 1)[0]
        names = re.findall(r"\bIHK_OS_STATUS_[A-Z_]+\b", enum)
        for number, name in enumerate(names):
            self.assertIn(f"pub const {name}: i32 = {number};", abi)

    def test_injection_is_only_syscall_boundary(self):
        source = SOURCE.read_text()
        self.assertIn("#include <ihk/ihk_host_user.h>", source)
        self.assertIn("int main(int argc, char **argv)", source)
        self.assertEqual(source.count("LIFECYCLE_IOCTL("), 2)
        self.assertNotIn("system(", source)
        self.assertNotIn("IHK_DEVICE_DESTROY_OS", source)
        self.assertNotIn("reboot(", source)


@unittest.skipUnless(os.environ.get("NATIVE_LIFECYCLE_COMPILE") == "1",
                     "compiler execution requires explicit dispatcher admission")
class CompiledActualMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(os.environ["NATIVE_LIFECYCLE_EVIDENCE"])
        cls.out.mkdir(mode=0o700, parents=False, exist_ok=False)
        cls.sequence = 0
        cls.child_env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
        evidence_root = cls.out.parent.resolve(strict=True)
        for name in ("HOME", "TMPDIR"):
            private = Path(os.environ[name])
            if (not private.is_absolute() or private.resolve(strict=True) != private or
                    not private.is_relative_to(evidence_root) or not private.is_dir()):
                raise RuntimeError(f"{name} must be a canonical private directory under evidence root")
            info = private.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise RuntimeError(f"{name} must be caller-owned with no group/other permissions")
            cls.child_env[name] = str(private)
        include = cls.out / "include/ihk"
        include.mkdir(parents=True)
        for name in HEADERS:
            (include / name).write_bytes(header(name))
        probe = cls.out / "probe.c"
        probe.write_bytes(SOURCE.read_bytes())
        harness = cls.out / "harness.c"
        harness.write_text(HARNESS.replace("PROBE_SOURCE", str(probe)))
        cls.binary = cls.out / "harness"
        result = cls.capture(["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra",
                              "-Werror", "-I", str(cls.out / "include"), str(harness),
                              "-o", str(cls.binary)])
        if result.returncode:
            raise RuntimeError("compiler failed; retained evidence; stop and return to dispatcher")

    @classmethod
    def capture(cls, argv):
        cls.sequence += 1
        stem = cls.out / f"{cls.sequence:03d}"
        stem.with_suffix(".command.json").write_text(json.dumps({
            "argv": argv, "environment": cls.child_env,
        }, indent=2) + "\n")
        try:
            result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=20, env=cls.child_env)
        except subprocess.TimeoutExpired as error:
            stem.with_suffix(".stdout").write_bytes(error.stdout or b"")
            stem.with_suffix(".stderr").write_bytes(error.stderr or b"")
            stem.with_suffix(".json").write_text(json.dumps({"argv": argv, "timeout_seconds": 20}) + "\n")
            raise
        stem.with_suffix(".stdout").write_bytes(result.stdout)
        stem.with_suffix(".stderr").write_bytes(result.stderr)
        stem.with_suffix(".json").write_text(json.dumps({
            "argv": argv, "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        }, indent=2) + "\n")
        return result

    def test_actual_main_scenarios(self):
        # Sequential and fail-fast: any unexpected result stops this whole batch.
        failures = {"open_errno": ("open", 2), "before_errno": ("status_before", 19),
                    "busy": ("shutdown", 16), "negative_errno": ("shutdown", 5),
                    "unsupported": ("shutdown", 38), "interrupted": ("shutdown", 4),
                    "after_errno": ("status_after", 5), "close_errno": ("close", 4)}
        scenarios = ["running", "ready", "repeat", "retry_shutdown", *failures,
                     "before_unknown", "wrong_after", "after_unknown", "positive_shutdown"]
        for scenario in scenarios:
            run = self.capture([str(self.binary), scenario, "12"])
            success = scenario in ("running", "ready", "repeat", "retry_shutdown")
            self.assertEqual(run.returncode, 0 if success else 1, scenario)
            self.assertEqual(run.stderr, b"", scenario)
            rows = [json.loads(line) for line in run.stdout.splitlines()]
            passes = [row for row in rows if row.get("result") == "PASS"]
            self.assertEqual(len(passes), int(success), scenario)
            if success:
                self.assertEqual([row.get("operation") for row in rows[:-1]],
                                 ["open", "status_before", "shutdown", "status_after", "close"])
                self.assertEqual(passes[0]["transition_observed"], scenario != "repeat")
                self.assertFalse(passes[0]["resource_restoration_verified"])
            if scenario in failures:
                operation, error = failures[scenario]
                row = next(row for row in rows if row.get("operation") == operation)
                self.assertEqual((row["return"], row["errno"], row["linux_result"]),
                                 (-1, error, -error), scenario)
            if scenario in ("busy", "negative_errno", "unsupported", "interrupted"):
                self.assertEqual([row["operation"] for row in rows],
                                 ["open", "status_before", "shutdown", "status_after", "close"])
        for arguments in ([], [""], ["-1"], ["+1"], [" 1"], ["1x"],
                          ["../0"], ["2147483648"], ["999999999999999999999"], ["12", "12"]):
            run = self.capture([str(self.binary), "invalid", *arguments])
            self.assertEqual(run.returncode, 2, arguments)
            self.assertEqual(run.stdout, b"", arguments)
            self.assertIn(b"usage:", run.stderr)


if __name__ == "__main__":
    unittest.main(failfast=True)
