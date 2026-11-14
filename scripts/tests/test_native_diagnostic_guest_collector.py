"""Host-only executable checks of the actual collector supervisor/serializer.

PID1 main is renamed and never invoked. No mounts, modules, guest or root.
"""
import json
import importlib.util
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/application-tests/native_diagnostic_guest_collector.c"
_SPEC = importlib.util.spec_from_file_location("native_diagnostic", ROOT / "scripts/application-tests/native_diagnostic.py")
_DIAGNOSTIC = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DIAGNOSTIC)
EXPECTED = b'{"case":"startup.argv-empty","argc":4,"argv":["app","A","","B"],"terminator_is_null":true}\n'
HARNESS = r'''
#define _GNU_SOURCE
#include <time.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>
#if defined(ND_FUTEX)
#include <sys/syscall.h>
static int track_writes;
static unsigned tracked_short, tracked_eagain;
static ssize_t tracked_write(int fd, const void *data, size_t len) {
    ssize_t rc = syscall(SYS_write, fd, data, len);
    if (track_writes) {
        if (rc < 0 && errno == EAGAIN) ++tracked_eagain;
        if (rc >= 0 && (size_t)rc < len) ++tracked_short;
    }
    return rc;
}
#define write tracked_write
#endif
/* Only this host harness accelerates CLOCK_MONOTONIC. Real subprocess waits
 * and signals still execute; the production collector has no test mode. */
static unsigned test_clock_scale = 1;
static int accelerated_clock_gettime(clockid_t id, struct timespec *t) {
    int rc = clock_gettime(id, t);
    if (!rc && id == CLOCK_MONOTONIC) {
        unsigned long long ns = (unsigned long long)t->tv_nsec * test_clock_scale;
        t->tv_sec = t->tv_sec * test_clock_scale + ns / 1000000000ull;
        t->tv_nsec = ns % 1000000000ull;
    }
    return rc;
}
#define clock_gettime accelerated_clock_gettime
#define main guest_init_main
#include "COLLECTOR_SOURCE"
#undef main
#undef clock_gettime
#if defined(ND_FUTEX)
#undef write
#endif
#include <stdlib.h>
int main(int argc, char **argv) {
#if defined(ND_FUTEX)
    if (argc == 2 && !strcmp(argv[1], "partial-publication")) {
        struct result r;
        int p[2];
        memset(&r, 0, sizeof r); r.status = 37 << 8; r.clean = 1;
        r.started = r.reaped = r.finished = 1;
        memset(r.out.data, 'o', sizeof r.out.data); memset(r.err.data, 'e', sizeof r.err.data);
        r.out.kept = r.err.kept = 1200; r.out.observed = r.err.observed = 1200;
        r.out.eof = r.err.eof = 1;
        if (pipe(p) || fcntl(p[1], F_SETPIPE_SZ, 4096) < 0) return 107;
        int flags = fcntl(p[1], F_GETFL); if (flags < 0 || fcntl(p[1], F_SETFL, flags | O_NONBLOCK)) return 108;
        char expected[FRAME_LIMIT]; int expected_n = frame(expected, &r, 1);
        if (expected_n <= 4096 || expected_n > (int)FRAME_LIMIT) return 109;
        pid_t reader = fork(); if (reader < 0) return 110;
        if (!reader) {
            char b[FRAME_LIMIT]; size_t got = 0; ssize_t n; close(p[1]); usleep(5000);
            while ((n = read(p[0], b + got, sizeof b - got)) > 0) got += (size_t)n;
            _exit(got == (size_t)expected_n && !memcmp(b, expected, got) ? 0 : 111);
        }
        track_writes = 1;
        int rc = publish(p[1], &r, 1); track_writes = 0;
        close(p[1]); close(p[0]); int status; waitpid(reader, &status, 0);
        return rc || !WIFEXITED(status) || WEXITSTATUS(status) != 0 ||
               tracked_short == 0 || tracked_eagain == 0 ? 112 : 0;
    }
    if (argc == 2 && !strcmp(argv[1], "futex")) {
        struct result r;
        char *const av[] = {"/bin/mcexec", "-t", "1", "0", "/apps/app", NULL};
        supervise("/proc/self/exe", av, payload_env, NULL, 100, &r);
        return publish(1, &r, 1) ? 106 : 0;
    }
    if (argc == 5 && !strcmp(argv[0], "/bin/mcexec") &&
        !strcmp(argv[1], "-t") && !strcmp(argv[2], "1") &&
        !strcmp(argv[3], "0") && !strcmp(argv[4], "/apps/app") && !argv[5]) {
        const char out[] = "NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n";
        if (write(1, out, sizeof out - 1) != sizeof out - 1) return 91;
        static const char *const ids[] = {"wait_mismatch", "wait_relative_zero", "wait_relative_10ms",
            "wait_bitset_expired", "wait_bitset_future", "wait_null_word", "wait_unaligned_word",
            "timeout_protected", "timeout_cross_page", "timeout_negative_seconds",
            "timeout_negative_nanoseconds", "timeout_large_nanoseconds", "wait_bitset_zero",
            "wake_empty", "wake_unmapped_private", "wait_relative_runnable"};
        static const int results[] = {-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,0,0,-1};
        static const int errors[] = {11,110,110,110,110,14,22,14,14,22,22,22,22,0,0,110};
        for (int i = 0; i != 16; ++i) {
            char line[256];
            unsigned long long elapsed = (i == 2 || i == 4 || i == 15) ? 10000000ull : 1000ull;
            unsigned long long before = 100000ull + i * 2000000ull;
            unsigned long long after = before + elapsed;
            unsigned long long deadline = i == 4 ? after - 5000000ull : 0ull;
            int n = snprintf(line, sizeof line, "NATIVE_ULTRA_FUTEX_CASE id=%s result=%d errno=%d elapsed_ns=%llu before_ns=%llu after_ns=%llu deadline_ns=%llu\n",
                             ids[i], results[i], errors[i], elapsed, before, after, deadline);
            if (n <= 0 || write(2, line, (size_t)n) != n) return 93;
        }
        const char threads[] = "NATIVE_ULTRA_FUTEX_THREADS joined=2 parent_tid=319 tid0=322 tid1=321 count0=217233 count1=241664 token0=1 token1=2 stack_bytes=262144 elapsed_ns=112287456\n";
        const char clone[] = "NATIVE_ULTRA_FUTEX_CLONE parent_tid=319 child_tid=322 entry_tid=322 stored_tid=322 cleared_tid=0 entered=1 wait_calls=0 elapsed_ns=8354973 flags=1250f00 stack_bytes=262144\n";
        if (write(2, threads, sizeof threads - 1) != (ssize_t)(sizeof threads - 1) ||
            write(2, clone, sizeof clone - 1) != (ssize_t)(sizeof clone - 1)) return 93;
        return 37;
    }
#elif defined(ND_CORE_MEMORY) || defined(ND_CORE_FILES) || defined(ND_CORE_THREADS) || defined(ND_CORE_SIGNALS)
    if (argc == 6) {
        if (strcmp(argv[0], "/bin/mcexec") || strcmp(argv[1], "-t") ||
            strcmp(argv[2], "1") || strcmp(argv[3], "0") ||
            strcmp(argv[4], "app") || strcmp(argv[5], nd_core_case) || argv[6]) return 90;
        char s[128];
        int n = snprintf(s, sizeof s, "{\"case\":\"%s\"}\n", nd_core_case);
        return write(1, s, (size_t)n) == n ? 0 : 91;
    }
#else
    if (argc == 8) {
        if (strcmp(argv[0], "/bin/mcexec") || strcmp(argv[1], "-t") ||
            strcmp(argv[2], "1") || strcmp(argv[3], "0") ||
            strcmp(argv[4], "app") || strcmp(argv[5], "A") ||
            strcmp(argv[6], "") || strcmp(argv[7], "B") || argv[8]) return 90;
        const char s[] = "{\"case\":\"startup.argv-empty\",\"argc\":4,\"argv\":[\"app\",\"A\",\"\",\"B\"],\"terminator_is_null\":true}\n";
        return write(1, s, sizeof s - 1) == sizeof s - 1 ? 0 : 91;
    }
#endif
    if (argc == 3 && !strcmp(argv[1], "child")) {
        if (!strcmp(argv[2], "bytes")) {
            unsigned char out[] = {0, 255, 65, 10}, err[] = {66, 0, 254};
            if (write(1, out, sizeof out) != sizeof out || write(2, err, sizeof err) != sizeof err) return 92;
            return 37;
        }
        if (!strcmp(argv[2], "descendant")) {
            pid_t p = fork(); if (p < 0) return 93;
            if (p) return 0;
            signal(SIGTERM, SIG_IGN); for (;;) pause();
        }
        if (!strcmp(argv[2], "flood")) {
            signal(SIGTERM, SIG_IGN); char b[512]; memset(b, 'x', sizeof b);
            for (;;) if (write(1, b, sizeof b) < 0 || write(2, b, sizeof b) < 0) return 94;
        }
        if (!strcmp(argv[2], "fds")) {
            for (int fd = 3; fd < 256; ++fd) if (fcntl(fd, F_GETFD) >= 0) return 95;
            return 0;
        }
        if (!strcmp(argv[2], "sleep")) {
            signal(SIGTERM, SIG_IGN);
            struct timespec t = {0, 350000000};
            while (nanosleep(&t, &t) && errno == EINTR) {}
            return 0;
        }
        if (!strcmp(argv[2], "hang")) {
            signal(SIGTERM, SIG_IGN);
            for (;;) pause();
        }
        return 96;
    }
    if (argc != 3 || prctl(PR_SET_CHILD_SUBREAPER, 1)) return 97;
    if (!strcmp(argv[1], "retired")) { printf("%d\n", retired_at(argv[2])); return 0; }
    if (!strcmp(argv[1], "pipes")) {
        close(0); close(1); close(2); int p[3][2];
        for (int i = 0; i < 3; ++i) if (make_pipe(p[i])) return 98;
        for (int i = 0; i < 6; ++i) {
            int fd = p[i/2][i%2];
            if (fd < 3 || !(fcntl(fd, F_GETFD) & FD_CLOEXEC)) return 99;
            if (!(i%2) && !(fcntl(fd, F_GETFL) & O_NONBLOCK)) return 100;
            for (int j = 0; j < i; ++j) if (fd == p[j/2][j%2]) return 101;
        }
        return 0;
    }
    struct result r;
    if (!strncmp(argv[1], "boot-", 5)) {
        test_clock_scale = 100;
        unsigned selected = helper_timeout_ms(!strcmp(argv[1], "boot-old") ?
                                              "/sbin/insmod" : "/bin/native-boot");
        if (!strcmp(argv[1], "boot-outer")) collector_deadline = now_ns() + 15000 * MS;
        char *av[] = {argv[0], "child", argv[2], NULL};
        supervise("/proc/self/exe", av, helper_env, NULL, selected, &r);
        fprintf(stderr, "selected=%u timeout=%d clean=%d elapsed_ms=%llu\n", selected,
                r.timeout, r.clean, (unsigned long long)((r.finished-r.started)/MS));
        return publish(1, &r, 1) ? 105 : 0;
    }
    if (!strcmp(argv[1], "closed-publication")) {
        memset(&r, 0, sizeof r);
        return publish(-1, &r, 0) == -1 ? 0 : 104;
    }
    if (!strcmp(argv[1], "oversize")) {
        memset(&r, 0, sizeof r); r.status = 0; r.clean = 1;
        r.started = r.reaped = r.finished = 1;
        r.out.kept = r.err.kept = STREAM_LIMIT; r.out.observed = r.err.observed = STREAM_LIMIT;
        r.out.eof = r.err.eof = 1;
        return publish(1, &r, 1) ? 102 : 0;
    }
    char *av[] = {argv[0], "child", argv[2], NULL};
    const char *path = "/proc/self/exe", *cwd = NULL; char *const *actual = av;
    if (!strcmp(argv[1], "argv")) actual = payload_argv;
    if (!strcmp(argv[1], "exec")) path = "/definitely-not-a-collector-test-executable";
    if (!strcmp(argv[1], "cwd")) cwd = "/definitely-not-a-collector-test-directory";
    supervise(path, actual, payload_env, cwd, 100, &r);
    fprintf(stderr, "status=%d fault=%d timeout=%d clean=%d stage=%d errno=%d\n",
            r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
    return publish(1, &r, 1) ? 103 : 0;
}
'''


class CollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="nd-collector-")
        cls.root = Path(cls.temp.name)
        cls.binary = cls.build(SOURCE, "normal")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def build(cls, source, name, profile=None):
        harness = cls.root / (name + ".c")
        harness.write_text(HARNESS.replace("COLLECTOR_SOURCE", str(source)))
        binary = cls.root / name
        command = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2"]
        if profile == "futex":
            command.append("-DND_FUTEX=1")
        elif profile:
            command.append("-DND_CORE_" + profile.upper() + "=1")
        p = subprocess.run(command + [str(harness), "-o", str(binary)], capture_output=True, timeout=20)
        if p.returncode:
            raise AssertionError(p.stderr.decode()[:4000])
        return binary

    def run_case(self, mode, child="bytes", binary=None):
        p = subprocess.run([str(binary or self.binary), mode, child], capture_output=True,
                           timeout=4, check=True)
        self.assertLessEqual(len(p.stdout), 4096)
        self.assertEqual(p.stdout.count(b"ND_PAYLOAD "), 1)
        return json.loads(p.stdout[len(b"ND_PAYLOAD "):]), p.stderr

    def test_exact_payload_argv_empty_argument_and_exit_zero(self):
        r, status = self.run_case("argv")
        self.assertEqual(r["raw_wait_status"], 0)
        self.assertEqual(bytes.fromhex(r["streams"]["stdout"]["hex"]), EXPECTED)
        self.assertTrue(r["procfs_empty"])
        self.assertIn(b"fault=0 timeout=0 clean=1", status)
        self.assertEqual(r["argv"], ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"])

    def test_memory_profile_payload_and_exact_report(self):
        binary = self.build(SOURCE, "memory", "memory")
        r, status = self.run_case("argv", binary=binary)
        self.assertEqual(r["raw_wait_status"], 0)
        self.assertEqual(r["argv"], ["/bin/mcexec", "-t", "1", "0", "app", "memory"])
        self.assertEqual(bytes.fromhex(r["streams"]["stdout"]["hex"]), b'{"case":"memory"}\n')
        self.assertIn(b"fault=0 timeout=0 clean=1", status)

    def test_core_profiles_compile_and_reject_unknown_profile(self):
        for profile in ("memory", "files", "threads", "signals"):
            self.build(SOURCE, "profile-" + profile, profile)
        for defines in (("ND_CORE_MEMORY", "ND_CORE_FILES"), ("ND_CORE_CASE=unsafe",),
                        ("ND_FUTEX", "ND_CORE_MEMORY"),
                        ("ND_CORE_CASE=memory+1",), ("ND_CORE_CASE=memory\\\"x\\\"",)):
            label = "-".join(d.replace("=", "-").replace("+", "-") for d in defines)
            harness = self.root / ("bad-" + label + ".c")
            harness.write_text(HARNESS.replace("COLLECTOR_SOURCE", str(SOURCE)))
            flags = ["-D" + d + ("=1" if "=" not in d else "") for d in defines]
            p = subprocess.run(["cc", "-std=c11", "-Werror", *flags, str(harness), "-o", str(self.root / ("bad-" + label))],
                               capture_output=True, timeout=20)
            self.assertNotEqual(p.returncode, 0)

    def test_futex_profile_compile_shape_and_exact_contract(self):
        self.build(SOURCE, "profile-futex", "futex")
        source = SOURCE.read_text()
        self.assertIn("/apps/app", source)
        self.assertIn('"hidos", "allow_oversubscribe"', source)
        self.assertIn("#define STREAM_LIMIT 4096u", source)
        self.assertIn("#define FRAME_LIMIT 8192u", source)
        self.assertIn("ND_FUTEX is mutually exclusive", source)
        self.assertIn("NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\\n", HARNESS)

    def test_futex_publication_is_complete_and_typed_oracle_accepts_dynamic_fields(self):
        binary = self.build(SOURCE, "futex-publication", "futex")
        subprocess.run([str(binary), "partial-publication"], capture_output=True, timeout=4, check=True)
        p = subprocess.run([str(binary), "futex"], capture_output=True, timeout=4, check=True)
        self.assertEqual(p.stderr, b"")
        self.assertEqual(p.stdout.count(b"ND_PAYLOAD "), 1)
        report = json.loads(p.stdout[len(b"ND_PAYLOAD "):])
        self.assertEqual(bytes.fromhex(report["streams"]["stdout"]["hex"]),
                         b"NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n")
        raw_stderr = bytes.fromhex(report["streams"]["stderr"]["hex"])
        oracle = {"kind": "native-ultra-futex-v1", "record_order": "current-source-v1", "line_count": 18,
                  "case_ids": [row[0] for row in _DIAGNOSTIC._FUTEX_CASES],
                  "thread_count": 2, "clone": True}
        _DIAGNOSTIC._check_typed_futex_stderr(raw_stderr, oracle)
        self.assertEqual(report["streams"]["stderr"]["observed"], len(raw_stderr))
        self.assertFalse(report["streams"]["stderr"]["truncated"])

    def test_typed_futex_oracle_rejects_mutation_and_overflow(self):
        oracle = {"kind": "native-ultra-futex-v1", "record_order": "current-source-v1", "line_count": 18,
                  "case_ids": [row[0] for row in _DIAGNOSTIC._FUTEX_CASES],
                  "thread_count": 2, "clone": True}
        binary = self.build(SOURCE, "futex-overflow", "futex")
        p = subprocess.run([str(binary), "oversize", "unused"], capture_output=True, timeout=4, check=True)
        report = json.loads(p.stdout[len(b"ND_PAYLOAD "):])
        self.assertTrue(report["streams"]["stderr"]["truncated"])
        bad = (b"NATIVE_ULTRA_FUTEX_CASE id=wait_mismatch result=-1 errno=11 "
               b"elapsed_ns=1 before_ns=2 after_ns=1 deadline_ns=0\n")
        with self.assertRaises(_DIAGNOSTIC.DiagnosticError):
            _DIAGNOSTIC._check_typed_futex_stderr(bad, oracle)
        binary = self.build(SOURCE, "futex-mutations", "futex")
        p = subprocess.run([str(binary), "futex"], capture_output=True, timeout=4, check=True)
        raw = bytes.fromhex(json.loads(p.stdout[len(b"ND_PAYLOAD "):])["streams"]["stderr"]["hex"])
        mutations = (
            (b"elapsed_ns=1000 before_ns=100000 after_ns=101000", b"elapsed_ns=999 before_ns=100000 after_ns=101000"),
            (b"elapsed_ns=1000 before_ns=100000 after_ns=101000", b"elapsed_ns=2000000001 before_ns=100000 after_ns=2000100001"),
            (b"deadline_ns=0\n", b"deadline_ns=1\n"),
            (b"id=wait_mismatch", b"id=wait_relative_zero"),
            (b"parent_tid=319 child_tid=322", b"parent_tid=322 child_tid=322"),
            (b"wait_calls=0", b"wait_calls=257"),
            (b"parent_tid=319 child_tid=322", b"parent_tid=2147483648 child_tid=322"),
        )
        for old, new in mutations:
            self.assertIn(old, raw)
            with self.assertRaises(_DIAGNOSTIC.DiagnosticError):
                _DIAGNOSTIC._check_typed_futex_stderr(raw.replace(old, new, 1), oracle)
        clone_slow = raw.replace(b"elapsed_ns=8354973 flags=1250f00",
                                 b"elapsed_ns=2000000001 flags=1250f00", 1)
        with self.assertRaises(_DIAGNOSTIC.DiagnosticError):
            _DIAGNOSTIC._check_typed_futex_stderr(clone_slow, oracle)
        thread_six = raw.replace(b"elapsed_ns=112287456\n",
                                 b"elapsed_ns=3000000000\n", 1)
        _DIAGNOSTIC._check_typed_futex_stderr(thread_six, oracle)

    def test_retained_current_order_archive_replay_and_legacy_order_rejection(self):
        oracle = {"kind": "native-ultra-futex-v1", "record_order": "historical-split-v1", "line_count": 18,
                  "case_ids": [row[0] for row in _DIAGNOSTIC._FUTEX_CASES],
                  "thread_count": 2, "clone": True}
        archive = ROOT / "docs/verification/evidence/native-ultra-futex-guest-20260909-2.tar.gz"
        members = (("linux-futex-payload-stderr.bin", "4aff87fd63e9e1f97b92082311d8a8bc31b13c5257ef205a82720047f36d45d6"),
                   ("mckernel-futex-payload-stderr.bin", "85f59a080a5dbc7c620d22910ff6524d4184c0ab93a9df5c3bbff70f5131e67f"))
        payloads = []
        for name, digest in members:
            member = "native-ultra-futex-guest-20260909-2/" + name
            p = subprocess.run(["tar", "-xOf", str(archive), member], capture_output=True, check=True, timeout=5)
            self.assertEqual(hashlib.sha256(p.stdout).hexdigest(), digest)
            _DIAGNOSTIC._check_typed_futex_stderr(p.stdout, oracle)
            payloads.append(p.stdout)
        current_oracle = dict(oracle, record_order="current-source-v1")
        with self.assertRaises(_DIAGNOSTIC.DiagnosticError):
            _DIAGNOSTIC._check_typed_futex_stderr(payloads[1], current_oracle)
        lines = payloads[1].splitlines(keepends=True)
        current = b"".join(lines[:15] + [lines[16], lines[17], lines[15]])
        _DIAGNOSTIC._check_typed_futex_stderr(current, current_oracle)
        with self.assertRaises(_DIAGNOSTIC.DiagnosticError):
            _DIAGNOSTIC._check_typed_futex_stderr(current, oracle)

    def test_binary_streams_raw_wait_and_eof(self):
        r, _ = self.run_case("run")
        self.assertEqual(r["raw_wait_status"], 37 << 8)
        for name, expected in (("stdout", b"\0\xffA\n"), ("stderr", b"B\0\xfe")):
            s = r["streams"][name]
            self.assertEqual(bytes.fromhex(s["hex"]), expected)
            self.assertTrue(s["eof"])
            self.assertFalse(s["truncated"])
            self.assertEqual(s["observed"], len(expected))
            self.assertLessEqual(r["started_ns"], s["eof_ns"])
            self.assertLessEqual(s["eof_ns"], r["finished_ns"])

    def test_setup_channel_exec_and_chdir_failures(self):
        for mode, stage in (("exec", 5), ("cwd", 4)):
            r, status = self.run_case(mode)
            self.assertFalse(r["procfs_empty"])
            self.assertEqual(r["raw_wait_status"], 126 << 8)
            self.assertIn(f"stage={stage} errno=2".encode(), status)

    def test_fair_flood_deadline_term_kill_and_reap(self):
        r, status = self.run_case("run", "flood")
        self.assertIn(b"timeout=1 clean=1", status)
        self.assertEqual(r["raw_wait_status"], 9)
        self.assertFalse(r["procfs_empty"])
        for name in ("stdout", "stderr"):
            self.assertGreater(r["streams"][name]["observed"], 1024)

    def test_orphan_writer_group_killed_and_reaped(self):
        r, status = self.run_case("run", "descendant")
        self.assertTrue(r["streams"]["stdout"]["eof"])
        self.assertTrue(r["streams"]["stderr"]["eof"])
        self.assertIn(b"clean=1", status)

    def test_cloexec_and_closed_standard_descriptors(self):
        r, _ = self.run_case("run", "fds")
        self.assertEqual(r["raw_wait_status"], 0)
        subprocess.run([str(self.binary), "pipes", "unused"], check=True,
                       capture_output=True, timeout=3)

    def test_retirement_requires_readable_procfs(self):
        directory = self.root / "procfs"
        directory.mkdir()
        for expected in (1, 0):
            p = subprocess.run([str(self.binary), "retired", str(directory)],
                               capture_output=True, check=True, timeout=3)
            self.assertEqual(int(p.stdout), expected)
            if expected:
                (directory / "123").mkdir()
        p = subprocess.run([str(self.binary), "retired", str(directory / "missing")],
                           capture_output=True, check=True, timeout=3)
        self.assertEqual(int(p.stdout), -1)

    def test_oversize_publication_single_bounded_rejected_record(self):
        r, _ = self.run_case("oversize")
        self.assertFalse(r["procfs_empty"])
        self.assertTrue(r["streams"]["stdout"]["truncated"])
        self.assertEqual(r["streams"]["stdout"]["discarded"], 1024)

    def test_mutated_argv_detected_by_independent_child(self):
        source = self.root / "bad-argv-source.c"
        text = SOURCE.read_text()
        changed = text.replace('"0", "app", "A", "", "B", NULL',
                               '"0", "app", "A", "WRONG", "B", NULL', 1)
        self.assertNotEqual(text, changed)
        source.write_text(changed)
        r, _ = self.run_case("argv", binary=self.build(source, "bad-argv"))
        self.assertEqual(r["raw_wait_status"], 90 << 8)
        self.assertNotEqual(bytes.fromhex(r["streams"]["stdout"]["hex"]), EXPECTED)

    def test_mutated_pipe_routing_is_observably_rejected(self):
        text = SOURCE.read_text()
        changed = text.replace('dup2(pipes[1][1], 2)', 'dup2(pipes[0][1], 2)', 1)
        self.assertNotEqual(text, changed)
        source = self.root / "bad-pipe-source.c"
        source.write_text(changed)
        r, _ = self.run_case("run", binary=self.build(source, "bad-pipe"))
        self.assertNotEqual(bytes.fromhex(r["streams"]["stdout"]["hex"]), b"\0\xffA\n")
        self.assertNotEqual(bytes.fromhex(r["streams"]["stderr"]["hex"]), b"B\0\xfe")

    def test_mutated_deadline_is_detected_by_sleep_control(self):
        r, _ = self.run_case("run", "sleep")
        self.assertEqual(r["raw_wait_status"], 9)
        text = SOURCE.read_text()
        changed = text.replace('(uint64_t)timeout_ms * MS', '(uint64_t)timeout_ms * MS + 500 * MS', 1)
        self.assertNotEqual(text, changed)
        source = self.root / "bad-deadline-source.c"
        source.write_text(changed)
        r, _ = self.run_case("run", "sleep", self.build(source, "bad-deadline"))
        self.assertNotEqual(r["raw_wait_status"], 9)

    def test_publication_write_failure_is_checked(self):
        subprocess.run([str(self.binary), "closed-publication", "unused"], check=True,
                       capture_output=True, timeout=3)

    def test_boot_timeout_allows_two_pause_equivalent_and_old_limit_rejects(self):
        # 350 ms real child sleep becomes 35 s in the supervisor's clock.
        # The exact selector used by helper() chooses 60 s only for native-boot.
        r, diagnostic = self.run_case("boot-current", "sleep")
        self.assertEqual(r["raw_wait_status"], 0)
        self.assertTrue(r["procfs_empty"])
        self.assertIn(b"selected=60000 timeout=0 clean=1", diagnostic)
        self.assertGreater(r["finished_ns"] - r["started_ns"], 20000000000)
        old, diagnostic = self.run_case("boot-old", "sleep")
        self.assertEqual(old["raw_wait_status"], 9)
        self.assertIn(b"selected=10000 timeout=1 clean=1", diagnostic)

    def test_boot_permanent_hang_term_kill_reaped_at_selected_deadline(self):
        r, diagnostic = self.run_case("boot-current", "hang")
        self.assertEqual(r["raw_wait_status"], 9)
        self.assertFalse(r["procfs_empty"])
        self.assertIn(b"selected=60000 timeout=1 clean=1", diagnostic)
        self.assertGreaterEqual(r["finished_ns"] - r["started_ns"], 60000000000)
        self.assertLess(r["finished_ns"] - r["started_ns"], 62000000000)

    def test_outer_budget_caps_boot_before_starting_another_phase(self):
        r, diagnostic = self.run_case("boot-outer", "hang")
        self.assertEqual(r["raw_wait_status"], 9)
        self.assertIn(b"selected=60000 timeout=1 clean=1", diagnostic)
        self.assertLess(r["finished_ns"] - r["started_ns"], 15000000000)


if __name__ == "__main__":
    unittest.main()
