"""Exercise the adapted C main with real pthreads and injected join/destroy errors.

All generated sources, executables and raw captures stay in the caller's fresh
MUTEX_BOUNDARY_TEST_ROOT. No guest, collector or production build is invoked.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest


SOURCE = (Path(__file__).resolve().parents[2] /
          "scripts/application-tests/native_thread_mutex_counter_bounded_stacks.c")
FLAGS = ("-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror", "-static",
         "-fno-pie", "-no-pie", "-Wl,-z,noexecstack", "-pthread")
HARNESS = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>
static int wrapped_create(pthread_t *, const pthread_attr_t *,
                          void *(*)(void *), void *);
static int wrapped_join(pthread_t, void **);
static int wrapped_destroy(pthread_mutex_t *);
static int wrapped_attr_init(pthread_attr_t *);
#define pthread_create wrapped_create
#define pthread_join wrapped_join
#define pthread_mutex_destroy wrapped_destroy
#define pthread_attr_init wrapped_attr_init
#define main fixture_main
#include "@SOURCE@"
#undef main
#undef pthread_create
#undef pthread_join
#undef pthread_mutex_destroy
#undef pthread_attr_init
static int creates, joins, destroys;
static int wrapped_create(pthread_t *tid, const pthread_attr_t *attr,
                          void *(*fn)(void *), void *arg) {
    fprintf(stderr, "create=%d\n", ++creates);
    return pthread_create(tid, attr, fn, arg);
}
static int wrapped_join(pthread_t tid, void **value) {
    fprintf(stderr, "join=%d\n", ++joins);
    if (INJECT_JOIN) return EINVAL;
    return pthread_join(tid, value);
}
static int wrapped_destroy(pthread_mutex_t *value) {
    fprintf(stderr, "destroy=%d\n", ++destroys);
    if (INJECT_DESTROY) return EBUSY;
    return pthread_mutex_destroy(value);
}
static int wrapped_attr_init(pthread_attr_t *attr) {
    if (INJECT_ATTR_INIT) {
        fputs("attr-init-failure\n", stderr);
        return ENOMEM;
    }
    return pthread_attr_init(attr);
}
int main(void) { return fixture_main(); }
'''


class MutexBoundaryTests(unittest.TestCase):
    def run_boundary(self, name, *, join=0, destroy=0, attr_init=0):
        root = Path(os.environ["MUTEX_BOUNDARY_TEST_ROOT"])
        self.assertTrue(root.is_absolute() and root.is_dir())
        case = root / name
        case.mkdir()
        src = case / "harness.c"
        src.write_text(HARNESS.replace("@SOURCE@", str(SOURCE)))
        commands = []
        env = {key: os.environ[key] for key in
               ("PATH", "LC_ALL", "LANG", "TZ", "PYTHONDONTWRITEBYTECODE", "HOME", "TMPDIR")}

        def capture(label, argv, timeout):
            commands.append({"label": label, "argv": argv, "cwd": str(case)})
            (case / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            try:
                result = subprocess.run(argv, cwd=case, env=env, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                (case / (label + ".stdout")).write_bytes(exc.stdout or b"")
                (case / (label + ".stderr")).write_bytes(exc.stderr or b"")
                (case / (label + ".status")).write_text("TIMEOUT\n")
                commands[-1].update(failure="TIMEOUT", timeout_seconds=timeout)
                (case / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
                raise
            (case / (label + ".stdout")).write_bytes(result.stdout)
            (case / (label + ".stderr")).write_bytes(result.stderr)
            (case / (label + ".status")).write_text(str(result.returncode) + "\n")
            commands[-1].update(returncode=result.returncode,
                                stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                                stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
            (case / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            return result

        build = capture("compile", ["/usr/bin/gcc", *FLAGS,
                        "-DINJECT_JOIN=" + str(join), "-DINJECT_DESTROY=" + str(destroy),
                        "-DINJECT_ATTR_INIT=" + str(attr_init), str(src), "-o", str(case / "probe")], 30)
        self.assertEqual(build.returncode, 0, build.stderr.decode())
        return capture("probe", [str(case / "probe")], 10)

    def test_join_failure_exits_before_destroy_or_next_vector(self):
        result = self.run_boundary("join-failure", join=1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"create=1\ncreate=2\njoin=1\n")

    def test_mutex_destroy_failure_exits_before_next_vector(self):
        result = self.run_boundary("destroy-failure", destroy=1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"create=1\ncreate=2\njoin=1\njoin=2\ndestroy=1\n")

    def test_attr_init_cleanup_destroy_failure_exits_before_next_vector(self):
        result = self.run_boundary("attr-cleanup-destroy-failure", destroy=1, attr_init=1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"attr-init-failure\ndestroy=1\n")


if __name__ == "__main__":
    unittest.main()
