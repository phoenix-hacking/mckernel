"""Behavioral/changed-ABI witness for actual eligible C wait helpers.

Uses verbatim function bodies, callback typedefs, both siginfo declarations,
actual rusage declaration and actual x86 headers. Backends are fixture doubles.
This local executable is not a production/kernel/native acceptance result.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def c_function(source, name):
    match = re.search(r"^(?:SYSCALL_POLICY_HELPER_SCOPE\s+)?(?:unsigned long|long|int|void)\s+"
                      + name + r"\(", source, re.M)
    if match is None:
        raise ValueError("Missing actual C helper: " + name)
    opening = source.index("{", match.start())
    cursor, depth = opening + 1, 1
    while depth:
        depth += (source[cursor] == "{") - (source[cursor] == "}")
        cursor += 1
    return source[match.start():cursor]


class CWaitTests(unittest.TestCase):
    def test_actual_c_wait_helpers_and_declarations(self):
        compiler = os.environ.get("CC") or shutil.which("gcc")
        if compiler is None:
            self.skipTest("GCC unavailable")
        source = (ROOT / "kernel/syscall.c").read_text()
        header = (ROOT / "kernel/include/syscall.h").read_text()
        start = header.index("struct rusage {")
        usage = header[start:header.index("};", start) + 2]
        typedefs = []
        for name in ("syscall_copy_to_user_fn_t", "wait4_do_wait_fn_t", "wait_status_fn_t",
                     "wait_signal_flags_reap_fn_t", "wait_lock_unlock_fn_t",
                     "wait_thread_report_detach_fn_t", "wait_thread_side_effect_fn_t"):
            match = re.search(r"^typedef[^;]*\(\*" + name + r"\)[^;]*;", source, re.M)
            if match is None:
                raise ValueError("Missing actual callback typedef: " + name)
            typedefs.append(match.group(0))
        declarations = re.findall(
            r"^(?:extern|SYSCALL_POLICY_HELPER_PROTO)\s+(?:void|long)\s+"
            r"waitid_copy_siginfo_result\([^;]*;", source, re.M)
        if len(declarations) != 2:
            raise ValueError("Expected both actual siginfo helper C declarations")
        process = (ROOT / "kernel/include/process.h").read_text()
        macros = []
        for name in ("WNOHANG", "WUNTRACED", "WSTOPPED", "WEXITED", "WCONTINUED",
                     "WNOWAIT", "__WALL", "__WCLONE", "P_ALL", "P_PID", "P_PGID",
                     "PS_EXITED", "PS_ZOMBIE", "PS_STOPPED", "PS_TRACED", "PS_DELAY_TRACED",
                     "PT_TRACED", "SIGNAL_STOP_STOPPED", "SIGNAL_STOP_CONTINUED"):
            match = re.search(r"^#define\s+" + name + r"\s+[^\n]+", process, re.M)
            if match is None:
                raise ValueError("Missing actual process constant: " + name)
            macros.append(match.group(0))
        sentinel = re.search(r"^#define\s+WAIT_PGID_ONE\s+[^\n]+", source, re.M)
        if sentinel:
            macros.append(sentinel.group(0))
        macros.extend(re.findall(
            r"^#define\s+(?:WAIT_THREAD_REAP_ACTION_\w+|WAIT_STATUS_PTRACED_STOP)\s+[^\n]+",
            source, re.M))
        status_assert = re.search(r"^_Static_assert\(_NSIG[^;]+;", source, re.M)
        if status_assert:
            macros.append(status_assert.group(0))
        for name in ("wait_process_candidate_body_result", "wait_thread_candidate_body_result"):
            declaration = re.search(r"^extern int " + name + r"\([^;]+;", source, re.M)
            if declaration is None:
                raise ValueError("Missing actual candidate declaration: " + name)
            declarations.append(declaration.group(0))
        functions = ["timeval_to_jiffy", "wait4_options_result", "waitid_to_wait_pid_result",
                     "waitid_options_result", "wait_process_pid_matches_result",
                     "wait_should_scan_thread_result", "wait_status_copy_needed_result",
                     "wait_rusage_copy_needed_result", "waitid_siginfo_needed_result",
                     "wait_reap_needed_result", "wait_thread_reap_action_result",
                     "wait_thread_exited_candidate_result", "wait_nonptraced_stop_candidate_result",
                     "wait_ptraced_stop_candidate_result", "wait_continued_candidate_result",
                     "wait_reaped_signal_flags_result", "wait_stopped_status_result",
                     "wait_process_candidate_body_result", "wait_thread_candidate_body_result",
                     "waitid_status_code_result", "wait4_body_result",
                     "waitid_copy_siginfo_result", "waitid_body_result"]
        harness = r'''
#include <types.h>
#include "@TIME@"
#include <signal.h>
#include <errno.h>
#include <limits.h>
#define SYSCALL_POLICY_HELPER_SCOPE
#define SYSCALL_POLICY_HELPER_PROTO extern
extern void *memset(void *, int, size_t);
extern int printf(const char *, ...);
@MACROS@
@USAGE@
@TYPEDEFS@
@DECLARATIONS@
@FUNCTIONS@
static long (*const siginfo_abi)(int, unsigned long, int, long, long, long, long,
                                syscall_copy_to_user_fn_t) = waitid_copy_siginfo_result;
static int result = 42, status = 7 << 8, copies, waits, fail_at, group_mode;
static long failure = -EFAULT;
static union { siginfo_t info; unsigned char bytes[256]; } output[2];
static size_t copied_sizes[2];
static int observe_wait(int selector, int *out_status, int options, struct rusage *usage)
{
    (void)options;
    waits++;
    *out_status = status;
    usage->ru_utime.tv_sec = 3;
    usage->ru_stime.tv_sec = 5;
    if (group_mode) {
        if (wait_process_pid_matches_result(selector, 99, 2, 51))
            return 51;
        if (wait_process_pid_matches_result(selector, 99, 1, 42))
            return 42;
        return -ECHILD;
    }
    return result;
}
static long observe_copy(unsigned long address, const void *data, size_t bytes)
{
    (void)address;
    if (copies >= 2 || bytes > 256)
        return -EFAULT;
    copied_sizes[copies] = bytes;
    for (size_t index = 0; index < bytes; index++)
        output[copies].bytes[index] = ((const unsigned char *)data)[index];
    copies++;
    return copies == fail_at ? failure : 0;
}
#define CHECK(condition) do { if (!(condition)) { printf("line %d: %s\n", __LINE__, #condition); return 1; } } while (0)
/* Observation objects and callbacks model only the candidate's explicit effects.
 * Candidate C bodies, callback declarations and constants above are unchanged.
 * The offset-driven API deliberately accepts opaque objects; these are not a
 * substitute declaration of production struct thread/process or native locks. */
struct observed_proc { int pid, status; };
struct observed_thread { void *proc; int tid, status, ptrace, flags; };
static struct observed_proc candidate_proc;
static struct observed_thread candidate_thread;
static int candidate_current, parent_lock, parent_node, threads_lock, threads_node;
static int candidate_path, candidate_payload, candidate_return, candidate_found;
static int candidate_raw, callback_bad, trace_count, trace[8];
static void trace_event(int event) { if (trace_count < 8) trace[trace_count++] = event; else callback_bad = 1; }
static int candidate_stopped(void *thread, void *proc, void *child, int *out, int options)
{
    (void)options;
    if (thread != &candidate_current || proc != &candidate_proc ||
        child != (candidate_path ? (void *)&candidate_thread : NULL)) callback_bad = 1;
    trace_event(1);
    *out = wait_stopped_status_result(candidate_payload);
    return candidate_return;
}
static int candidate_continued(void *thread, void *proc, void *child, int *out, int options)
{
    (void)thread; (void)proc; (void)child; (void)out; (void)options;
    callback_bad = 1;
    return -EINVAL;
}
static int candidate_reap(void *thread, unsigned long offset, int options, int mask)
{
    if (thread != &candidate_thread || offset != __builtin_offsetof(struct observed_thread, flags) ||
        mask != SIGNAL_STOP_STOPPED) callback_bad = 1;
    trace_event(2);
    candidate_thread.flags = wait_reaped_signal_flags_result(options, candidate_thread.flags, mask);
    return candidate_thread.flags;
}
static void candidate_unlock(void *lock, void *node)
{
    if (lock == &parent_lock && node == &parent_node) trace_event(3);
    else if (lock == &threads_lock && node == &threads_node) trace_event(4);
    else callback_bad = 1;
}
static void unexpected_thread_effect(void *thread) { (void)thread; callback_bad = 1; }
static int candidate_wait(int selector, int *out, int options, struct rusage *usage)
{
    (void)usage;
    int ret;
    if (candidate_path) {
        ret = wait_thread_candidate_body_result(0, selector, out, options,
            &candidate_current, &candidate_thread, &threads_lock, &threads_node,
            __builtin_offsetof(struct observed_thread, proc),
            __builtin_offsetof(struct observed_thread, tid),
            __builtin_offsetof(struct observed_thread, status),
            __builtin_offsetof(struct observed_thread, ptrace),
            __builtin_offsetof(struct observed_thread, flags), candidate_stopped,
            candidate_continued, candidate_reap, candidate_unlock,
            unexpected_thread_effect, unexpected_thread_effect, unexpected_thread_effect,
            &candidate_found);
    } else {
        ret = wait_process_candidate_body_result(0, selector, out, options,
            &candidate_current, &candidate_proc, &candidate_thread,
            &parent_lock, &parent_node, &threads_lock, &threads_node,
            __builtin_offsetof(struct observed_proc, pid),
            __builtin_offsetof(struct observed_proc, status),
            __builtin_offsetof(struct observed_thread, tid),
            __builtin_offsetof(struct observed_thread, ptrace),
            __builtin_offsetof(struct observed_thread, flags), candidate_stopped,
            candidate_continued, candidate_reap, candidate_unlock, &candidate_found);
    }
    candidate_raw = *out;
    return ret;
}
static long candidate_copy(unsigned long address, const void *data, size_t bytes)
{
    trace_event(5);
    return observe_copy(address, data, bytes);
}
static int candidate_case(int thread_path, int traced, int payload, int waitid,
                          int nowait, int stopped_return)
{
    candidate_path = thread_path; candidate_payload = payload;
    candidate_proc.pid = 42; candidate_proc.status = traced ? PS_TRACED : PS_STOPPED;
    candidate_thread.proc = &candidate_proc; candidate_thread.tid = 43;
    candidate_thread.status = candidate_proc.status;
    candidate_thread.ptrace = traced ? PT_TRACED : 0;
    candidate_thread.flags = SIGNAL_STOP_STOPPED;
    candidate_return = stopped_return;
    candidate_found = callback_bad = trace_count = copies = fail_at = 0;
    candidate_raw = -999;
    int options = WSTOPPED | (nowait ? WNOWAIT : 0);
    long rc = waitid ? waitid_body_result(P_ALL, 0, 0x3000, options,
                                        candidate_wait, candidate_copy)
                     : wait4_body_result(-1, 0x1000, WUNTRACED, 0,
                                         candidate_wait, candidate_copy);
    CHECK(!callback_bad);
    int success = stopped_return == (thread_path ? 43 : 42);
    if (!success) {
        CHECK(rc == stopped_return && candidate_found == 0);
        CHECK(candidate_raw == wait_stopped_status_result(payload));
        CHECK((candidate_raw & 0xff) == 0x7f);
        CHECK(candidate_thread.flags == SIGNAL_STOP_STOPPED);
        CHECK(trace[0] == 1);
        CHECK(trace_count == (waitid && stopped_return == 0 ? 2 : 1));
        CHECK(copies == (waitid && stopped_return == 0 ? 1 : 0));
        if (copies) for (size_t i=0; i<sizeof(siginfo_t); i++) CHECK(output[0].bytes[i] == 0);
        return 0;
    }
    CHECK(rc == (waitid ? 0 : stopped_return) && candidate_found == 1 && copies == 1);
    CHECK(candidate_raw == ((payload << 8) | (traced ? 0x7e : 0x7f)));
    CHECK(candidate_thread.flags == (nowait ? SIGNAL_STOP_STOPPED : 0));
    CHECK(trace_count == (thread_path ? 4 : 5));
    CHECK(trace[0] == 1 && trace[1] == 2);
    if (thread_path) CHECK(trace[2] == 4 && trace[3] == 5);
    else CHECK(trace[2] == 3 && trace[3] == 4 && trace[4] == 5);
    if (waitid) {
        CHECK(output[0].info.si_code == (traced ? CLD_TRAPPED : CLD_STOPPED));
        CHECK(output[0].info._sifields._sigchld.si_status == payload);
        CHECK(output[0].info._sifields._sigchld.si_pid == stopped_return);
    } else {
        CHECK(copied_sizes[0] == sizeof(int));
        CHECK(*(int *)output[0].bytes == wait_stopped_status_result(payload));
        CHECK((*(int *)output[0].bytes & 0xff) == 0x7f);
    }
    return 0;
}
static long call_wait4(void) {
    return wait4_body_result(-1, 0x1000, WNOHANG, 0x2000, observe_wait, observe_copy);
}
static long call_waitid(void) {
    return waitid_body_result(P_ALL, 0, 0x3000, WEXITED | WNOHANG, observe_wait, observe_copy);
}
int main(int argc, char **argv)
{
    CHECK(argc == 2);
    CHECK(sizeof(int) == 4 && sizeof(long) == 8 && sizeof(siginfo_t) == 128);
    CHECK(sizeof(struct rusage) == 144 && siginfo_abi != NULL);
    switch (argv[1][0]) {
    case 'a':
        fail_at = 1;
        CHECK(call_wait4() == -EFAULT && copies == 1 && waits == 1);
        break;
    case 'b':
        fail_at = 2; failure = 1;
        CHECK(call_wait4() == -EFAULT && copies == 2);
        break;
    case 'c':
        result = -ECHILD;
        CHECK(call_wait4() == -ECHILD && copies == 0);
        result = 0;
        CHECK(call_wait4() == 0 && copies == 0);
        break;
    case 'd':
        CHECK(call_wait4() == 42 && copies == 2);
        CHECK(copied_sizes[0] == sizeof(int) && copied_sizes[1] == sizeof(struct rusage));
        CHECK(*(int *)output[0].bytes == (7 << 8));
        break;
    case 'e': {
        int raw[] = {7 << 8, 9, 11 | 0x80, (19 << 8) | 0x7f, 0xffff, 0x0004057f};
        int code[] = {CLD_EXITED, CLD_KILLED, CLD_DUMPED, CLD_STOPPED, CLD_CONTINUED, CLD_STOPPED};
        int decoded[] = {7, 9, 11, 19, SIGCONT, 0x405};
        for (int index = 0; index < 6; index++) {
            status = raw[index]; copies = 0;
            CHECK(call_waitid() == 0 && copies == 1);
            CHECK(output[0].info.si_signo == SIGCHLD && output[0].info.si_code == code[index]);
            CHECK(output[0].info._sifields._sigchld.si_status == decoded[index]);
            CHECK(output[0].info._sifields._sigchld.si_pid == 42);
        }
        break;
    }
    case 'f':
        fail_at = 1; failure = 1;
        CHECK(call_waitid() == -EFAULT && copies == 1);
        copies = 0; result = 0;
        CHECK(call_waitid() == -EFAULT && copies == 1);
        break;
    case 'g':
        result = 0;
        CHECK(call_waitid() == 0 && copies == 1);
        for (size_t index = 0; index < sizeof(siginfo_t); index++)
            CHECK(output[0].bytes[index] == 0);
        break;
    case 'h': {
        int translated = 123;
        CHECK(waitid_to_wait_pid_result(P_PID, 0, &translated) == -EINVAL && translated == 123);
        CHECK(waitid_to_wait_pid_result(P_PID, INT_MIN, &translated) == -EINVAL);
        CHECK(waitid_to_wait_pid_result(P_PGID, INT_MIN, &translated) == -EINVAL);
        CHECK(waitid_body_result(P_PID, -1, 0x3000, WEXITED, observe_wait, observe_copy) == -EINVAL);
        CHECK(waits == 0 && copies == 0);
        CHECK(waitid_to_wait_pid_result(P_PGID, 0, &translated) == 0 && translated == 0);
        CHECK(waitid_to_wait_pid_result(P_ALL, INT_MIN, &translated) == 0 && translated == -1);
        break;
    }
    case 'i': {
        int translated = 0;
        group_mode = 1;
        CHECK(waitid_body_result(P_PGID, 1, 0x3000, WEXITED, observe_wait, observe_copy) == 0);
        CHECK(output[0].info._sifields._sigchld.si_pid == 42);
        CHECK(waitid_to_wait_pid_result(P_PGID, 1, &translated) == 0 && translated == INT_MIN);
        CHECK(wait_process_pid_matches_result(translated, 99, 2, 51) == 0);
        CHECK(wait_process_pid_matches_result(translated, 99, 1, 42) == 1);
        CHECK(wait_should_scan_thread_result(translated, __WALL | __WCLONE) == 0);
        CHECK(wait_process_pid_matches_result(-1, 99, 2, 51) == 1);
        CHECK(wait_process_pid_matches_result(-2, 99, 2, 51) == 1);
        break;
    }
    case 'j':
        CHECK(wait4_body_result(INT_MIN, 0x1000, 0, 0x2000, observe_wait, observe_copy) == -ESRCH);
        CHECK(waits == 0 && copies == 0);
        break;
    case 'k':
        for (int path=0; path<2; path++) for (int id=0; id<2; id++) {
            CHECK(candidate_case(path,1,SIGSTOP,id,0,path ? 43 : 42) == 0);
            CHECK(candidate_case(path,0,SIGSTOP,id,0,path ? 43 : 42) == 0);
            CHECK(candidate_case(path,1,(4 << 8) | (SIGTRAP | 0x80),id,0,path ? 43 : 42) == 0);
        }
        break;
    case 'l':
        for (int path=0; path<2; path++) for (int traced=0; traced<2; traced++) {
            CHECK(candidate_case(path,traced,SIGSTOP,1,1,path ? 43 : 42) == 0);
        }
        break;
    case 'm':
        for (int path=0; path<2; path++) for (int id=0; id<2; id++) {
            CHECK(candidate_case(path,1,SIGSTOP,id,0,0) == 0);
            CHECK(candidate_case(path,1,SIGSTOP,id,0,-EINTR) == 0);
        }
        break;
    default: return 2;
    }
    return 0;
}
'''
        replacements = {
            "@TIME@": str(ROOT / "kernel/include/time.h"), "@USAGE@": usage,
            "@TYPEDEFS@": "\n".join(typedefs), "@DECLARATIONS@": "\n".join(declarations),
            "@MACROS@": "\n".join(macros),
            "@FUNCTIONS@": "\n".join(c_function(source, name) for name in functions),
        }
        for key, value in replacements.items():
            harness = harness.replace(key, value)
        with tempfile.TemporaryDirectory(prefix="m14-f03-wait-c-") as directory:
            path = Path(directory)
            (path / "fixture.c").write_text(harness)
            binary = path / "fixture"
            result = subprocess.run([
                compiler, "-std=gnu11", "-O0", "-fno-builtin", "-fsanitize=undefined",
                "-fno-sanitize-recover=undefined", "-Werror=incompatible-pointer-types",
                "-Werror=return-type", "-I", str(ROOT / "arch/x86_64/kernel/include"),
                "-I", str(ROOT / "lib/include"), "-I", str(ROOT / "kernel/include"),
                str(path / "fixture.c"), "-o", str(binary),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for case in "abcdefghijklm":
                with self.subTest(case=case):
                    result = subprocess.run([str(binary), case], capture_output=True,
                                            text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
