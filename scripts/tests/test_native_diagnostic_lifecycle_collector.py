"""Cheap actual-body tests; PID1 main and native helper are never executed.

Only supervise/save_file/write_all definitions are renamed in a retained copy.
Their call boundaries inject deterministic captures; lifecycle gating, helper
validation/evidence ordering and lifecycle serialization execute actual C.
The unchanged supervisor remains separately covered by its existing suite.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/application-tests/native_diagnostic_lifecycle_collector.c"
BASE = ROOT / "scripts/application-tests/native_diagnostic_guest_collector.c"
HARNESS = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
struct result;
static void supervise(const char *, char *const[], char *const[], const char *, unsigned, struct result *);
static int save_file(const char *, const void *, size_t);
static int write_all(int, const void *, size_t);
#define main unused_guest_init_main
#include "INJECTED_COLLECTOR"
#undef main
static const char *scenario;
static unsigned supervised, saved, written;
static char exported[16384];
static size_t exported_n;
static const unsigned char out_bytes[] = {0, 255, 'A', '\n'};
static const unsigned char err_bytes[] = {'B', 0, 254};
static void supervise(const char *path, char *const av[], char *const env[],
                      const char *cwd, unsigned timeout, struct result *r)
{
    assert(++supervised == 1 && saved == 0 && written == 0);
    assert(!strcmp(path, "/bin/native-lifecycle-probe"));
    assert(!strcmp(av[0], path) && !strcmp(av[1], "0") && av[2] == NULL);
    assert(env == helper_env && !strcmp(env[0], "PATH=/bin:/sbin:/usr/bin:/usr/sbin"));
    assert(!strcmp(env[1], "LC_ALL=C") && env[2] == NULL && cwd == NULL);
    assert(timeout == 10000 && helper_timeout_ms(path) == HELPER_TIMEOUT_MS);
    memset(r, 0, sizeof *r);
    r->clean = 1; r->out.eof = r->err.eof = 1;
    r->started = 10; r->reaped = 20; r->finished = 30;
    r->out.eof_ns = 21; r->err.eof_ns = 22;
    memcpy(r->out.data, out_bytes, sizeof out_bytes);
    memcpy(r->err.data, err_bytes, sizeof err_bytes);
    r->out.kept = r->out.observed = sizeof out_bytes;
    r->err.kept = r->err.observed = sizeof err_bytes;
    if (!strcmp(scenario, "helper_exit")) r->status = 1 << 8;
    if (!strcmp(scenario, "helper_signal")) r->status = 9;
    if (!strcmp(scenario, "helper_timeout")) r->timeout = 1;
    if (!strcmp(scenario, "helper_fault")) { r->fault = 1; r->child_stage = 5; r->child_errno = 2; }
    if (!strcmp(scenario, "helper_unclean")) r->clean = 0;
    if (!strcmp(scenario, "helper_out_eof")) r->out.eof = 0;
    if (!strcmp(scenario, "helper_err_eof")) r->err.eof = 0;
    if (!strcmp(scenario, "helper_out_truncated")) r->out.observed++;
    if (!strcmp(scenario, "helper_err_truncated")) r->err.observed++;
    if (!strcmp(scenario, "max_streams")) {
        memset(r->out.data, 255, STREAM_LIMIT); memset(r->err.data, 0, STREAM_LIMIT);
        r->out.kept = r->out.observed = STREAM_LIMIT;
        r->err.kept = r->err.observed = STREAM_LIMIT;
    }
}
static int save_file(const char *path, const void *bytes, size_t count)
{
    static const char *const paths[] = {"/case/evidence/lifecycle.stdout",
        "/case/evidence/lifecycle.stderr", "/case/evidence/lifecycle.status"};
    assert(supervised == 1 && saved < 3 && written == 0);
    assert(!strcmp(path, paths[saved]));
    if (saved == 0 && strcmp(scenario, "max_streams"))
        assert(count == sizeof out_bytes && !memcmp(bytes, out_bytes, count));
    if (saved == 1 && strcmp(scenario, "max_streams"))
        assert(count == sizeof err_bytes && !memcmp(bytes, err_bytes, count));
    if (saved == 2) assert(count > 0 && !memcmp(bytes, "status=", 7));
    saved++;
    return ((!strcmp(scenario, "save_out") && saved == 1) ||
            (!strcmp(scenario, "save_err") && saved == 2) ||
            (!strcmp(scenario, "save_status") && saved == 3)) ? -1 : 0;
}
static int write_all(int fd, const void *bytes, size_t count)
{
    assert(fd == 71 && supervised == 1 && saved == 3 && count <= PIPE_BUF);
    written++;
    if ((!strcmp(scenario, "publish_metadata") && written == 1) ||
        (!strcmp(scenario, "publish_out") && written == 2) ||
        (!strcmp(scenario, "publish_err") && written == 3)) return -1;
    assert(count < sizeof exported - exported_n);
    memcpy(exported + exported_n, bytes, count); exported_n += count;
    return 0;
}
int main(int argc, char **argv)
{
    struct result payload, capture;
    int good = 1, safe = 1, empty = 1, attempted = 99, rc, publication = 99;
    assert(argc == 2); scenario = argv[1];
    /* Keep the real functions compiled and referenced; they are never called. */
    (void)real_supervise; (void)real_save_file; (void)real_write_all;
    memset(&payload, 0, sizeof payload); memset(&capture, 0, sizeof capture);
    payload.clean = payload.out.eof = payload.err.eof = 1;
    if (!strcmp(scenario, "gate_good")) good = 0;
    if (!strcmp(scenario, "gate_safe")) safe = 0;
    if (!strcmp(scenario, "gate_empty")) empty = 0;
    if (!strcmp(scenario, "gate_unreadable")) empty = -1;
    if (!strcmp(scenario, "gate_clean")) payload.clean = 0;
    if (!strcmp(scenario, "gate_fault")) payload.fault = 1;
    if (!strcmp(scenario, "gate_timeout")) payload.timeout = 1;
    if (!strcmp(scenario, "gate_exit")) payload.status = 1 << 8;
    if (!strcmp(scenario, "gate_signal")) payload.status = 9;
    if (!strcmp(scenario, "gate_out_eof")) payload.out.eof = 0;
    if (!strcmp(scenario, "gate_err_eof")) payload.err.eof = 0;
    if (!strcmp(scenario, "gate_out_truncated")) payload.out.observed = 1;
    if (!strcmp(scenario, "gate_err_truncated")) payload.err.observed = 1;
    rc = lifecycle_after_payload(&payload, good, &safe, empty, &attempted, &capture);
    if (attempted && safe) publication = publish_lifecycle(71, &capture, rc);
    if (!strncmp(scenario, "gate_", 5)) assert(!attempted && !supervised && !saved && !written);
    else assert(attempted && supervised == 1 && saved == 3);
    if (!strcmp(scenario, "helper_unclean")) assert(!safe && !written);
    printf("RESULT {\"helper_rc\":%d,\"safe\":%d,\"attempted\":%d,"
           "\"supervised\":%u,\"saved\":%u,\"written\":%u,\"publication\":%d}\n",
           rc, safe, attempted, supervised, saved, written, publication);
    if (exported_n) assert(fwrite(exported, 1, exported_n, stdout) == exported_n);
    return 0;
}
'''


class LifecycleCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(os.environ["NATIVE_LIFECYCLE_COLLECTOR_EVIDENCE"])
        cls.out.mkdir(mode=0o700, exist_ok=False)
        cls.env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
        for name in ("HOME", "TMPDIR"):
            private = Path(os.environ[name])
            private.relative_to(cls.out.parent.resolve(strict=True))
            if private.resolve(strict=True) != private or not private.is_dir():
                raise RuntimeError("private child directory is not canonical")
            info = private.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise RuntimeError("private child directory must be caller-owned and private")
            cls.env[name] = str(private)
        cls.sequence = 0
        original = SOURCE.read_text()
        (cls.out / "collector.c").write_text(original)
        injected = original
        for old, new in (
            ("static void supervise(", "static void real_supervise("),
            ("static int save_file(", "static int real_save_file("),
            ("static int write_all(int fd, const void *data, size_t len)\n{",
             "static int real_write_all(int fd, const void *data, size_t len)\n{"),
        ):
            if injected.count(old) != 1:
                raise RuntimeError("exact syscall boundary anchor changed: " + old)
            injected = injected.replace(old, new, 1)
        staged = cls.out / "collector-injected.c"
        staged.write_text(injected)
        harness = cls.out / "harness.c"
        harness.write_text(HARNESS.replace("INJECTED_COLLECTOR", str(staged)))
        cls.binary = cls.out / "harness"
        result = cls.capture(["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra",
                              "-Werror", str(harness), "-o", str(cls.binary)])
        if result.returncode:
            raise RuntimeError("compile failed; retained evidence; stop for dispatcher")

    @classmethod
    def capture(cls, argv):
        cls.sequence += 1
        stem = cls.out / f"{cls.sequence:03d}"
        stem.with_suffix(".command.json").write_text(json.dumps({
            "argv": argv, "environment": cls.env,
        }, indent=2) + "\n")
        try:
            result = subprocess.run(argv, env=cls.env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=20)
        except subprocess.TimeoutExpired as error:
            stem.with_suffix(".stdout").write_bytes(error.stdout or b"")
            stem.with_suffix(".stderr").write_bytes(error.stderr or b"")
            stem.with_suffix(".json").write_text(json.dumps({"timeout_seconds": 20}) + "\n")
            raise
        stem.with_suffix(".stdout").write_bytes(result.stdout)
        stem.with_suffix(".stderr").write_bytes(result.stderr)
        stem.with_suffix(".json").write_text(json.dumps({
            "argv": argv, "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        }, indent=2) + "\n")
        return result

    def test_actual_lifecycle_gate_helper_and_transport(self):
        gates = ["good", "safe", "empty", "unreadable", "clean", "fault", "timeout",
                 "exit", "signal", "out_eof", "err_eof", "out_truncated", "err_truncated"]
        failures = ["helper_exit", "helper_signal", "helper_timeout", "helper_fault",
                    "helper_unclean", "helper_out_eof", "helper_err_eof",
                    "helper_out_truncated", "helper_err_truncated",
                    "save_out", "save_err", "save_status"]
        publications = ["publish_metadata", "publish_out", "publish_err"]
        for scenario in ["success", "max_streams", *failures, *publications,
                         *("gate_" + name for name in gates)]:
            result = self.capture([str(self.binary), scenario])
            self.assertEqual(result.returncode, 0, scenario)
            self.assertEqual(result.stderr, b"", scenario)
            lines = result.stdout.splitlines()
            summary = json.loads(lines[0].split(b" ", 1)[1])
            self.assertEqual(summary["helper_rc"], -1 if scenario in failures or scenario.startswith("gate_") else 0, scenario)
            if scenario.startswith("gate_") or scenario == "helper_unclean":
                self.assertEqual(summary["written"], 0, scenario)
                self.assertEqual(len(lines), 1, scenario)
                continue
            self.assertEqual(summary["publication"], -1 if scenario in publications else 0, scenario)
            if scenario in publications:
                continue
            self.assertEqual([line.split(b" ", 1)[0] for line in lines[1:]],
                             [b"ND_LIFECYCLE", b"ND_LIFECYCLE_STREAM", b"ND_LIFECYCLE_STREAM"])
            status, out, err = [json.loads(line.split(b" ", 1)[1]) for line in lines[1:]]
            self.assertEqual(status["argv"], ["/bin/native-lifecycle-probe", "0"])
            self.assertEqual(status["helper_result"], summary["helper_rc"])
            self.assertEqual([out["name"], err["name"]], ["stdout", "stderr"])
            expected_out, expected_err = ((b"\xff" * 1024, b"\x00" * 1024)
                                         if scenario == "max_streams" else (b"\x00\xffA\n", b"B\x00\xfe"))
            self.assertEqual(bytes.fromhex(out["capture"]["hex"]), expected_out)
            self.assertEqual(bytes.fromhex(err["capture"]["hex"]), expected_err)
            if scenario == "helper_out_truncated":
                self.assertTrue(out["capture"]["truncated"])
            if scenario == "helper_err_truncated":
                self.assertTrue(err["capture"]["truncated"])

    def test_main_order_and_preserved_bodies(self):
        base, source = BASE.read_text(), SOURCE.read_text()
        # Exact bodies remain shared, including all supervisor timeout/reap logic.
        def body(text, start, end):
            return text.split(start, 1)[1].split(end, 1)[0]
        for start, end in (("static void supervise(", "static int retired_at("),
                           ("static int frame(", "static int write_all("),
                           ("static void poweroff_forever(", "int main(void)")):
            self.assertEqual(body(base, start, end), body(source, start, end))
        main = source.split("int main(void)", 1)[1]
        self.assertLess(main.index('supervise("/bin/mcexec"'), main.index('retired_at("/proc/mcos0")'))
        self.assertLess(main.index('retired_at("/proc/mcos0")'), main.index("lifecycle_after_payload(&payload"))
        self.assertLess(main.index("lifecycle_after_payload(&payload"), main.index("finish:;"))
        self.assertLess(main.index("publish_lifecycle(console"), main.index("publish(console, &payload"))
        self.assertLess(main.index("publish(console, &payload"), main.index("poweroff_forever(console)"))
        self.assertIn("if (lifecycle_rc) good = 0;", main)
        self.assertIn("if (!good || !safe) payload.fault = 1;", main)
        self.assertIn("if (console >= 0 && safe)", main)
        self.assertNotIn('"/sbin/rmmod"', source)


if __name__ == "__main__":
    unittest.main(failfast=True)
