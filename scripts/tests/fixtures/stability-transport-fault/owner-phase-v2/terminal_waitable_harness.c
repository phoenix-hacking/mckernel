/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual Linux fork/pipe/clock checks only. Root compiles and runs this file.
 * Include the exact reviewed controller: no syscall, clock, waitid, pump or
 * terminal-method substitutions. Its renamed CLI main is never called. */
#define main stability_controller_uninvoked_main
#include "controller.c"
#undef main

enum th_case { TH_EXIT, TH_ALIVE, TH_STDOUT, TH_STDERR, TH_TICKS,
               TH_NONZERO, TH_EXPIRED, TH_OVERALL };
static const char *const th_names[] = {
    "exit-eof", "alive-eof", "descendant-stdout", "descendant-stderr",
    "ticks-mismatch", "nonzero-exit", "expired-ready", "overall-deadline"
};
static const unsigned char th_out[] = "TERMINAL_FIXTURE_STDOUT\n";
static const unsigned char th_err[] = "TERMINAL_FIXTURE_STDERR\n";
static unsigned th_failures, th_reaped;
static pid_t th_descendant = -1;
static int th_launcher_wait = -1, th_descendant_wait = -1;

static void th_alarm(int number) { interrupted = number; }

static void th_check(bool condition, const char *name)
{
    event("\"event\":\"harness-assertion\",\"name\":\"%s\",\"ok\":%s",
          name, condition ? "true" : "false");
    if (!condition) {
        ++th_failures;
        dprintf(2, "TERMINAL_WAITABLE_ASSERTION_FAILURE %s\n", name);
    }
}

static bool th_artifact(const char *name, const void *data, size_t size)
{
    int fd = new_file(name);
    if (fd < 0) return false;
    bool ok = put_all(fd, data, size) && fsync(fd) == 0;
    if (close(fd) < 0) ok = false;
    return ok;
}

struct th_ready { pid_t pid, descendant; int error; };

static void th_fixture(enum th_case which, int out_pipe[2], int err_pipe[2], int ready_pipe[2])
{
    close(out_pipe[0]); close(err_pipe[0]); close(ready_pipe[0]);
    close(attempt_fd); close(events.fd);
    close(streams[0].sink.fd); close(streams[1].sink.fd);
    close(0); close(1); close(2);
    struct th_ready message = {.pid = getpid(), .descendant = -1, .error = 0};
    if (setsid() < 0) message.error = errno;
    if (!message.error && (!put_all(out_pipe[1], th_out, sizeof th_out - 1) ||
                          !put_all(err_pipe[1], th_err, sizeof th_err - 1))) message.error = errno ? errno : EIO;
    if (!message.error && (which == TH_STDOUT || which == TH_STDERR)) {
        pid_t descendant = fork();
        if (descendant < 0) message.error = errno;
        else if (!descendant) {
            close(ready_pipe[1]);
            close(which == TH_STDOUT ? err_pipe[1] : out_pipe[1]);
            /* Retain exactly one real writer until the parent harness's owned
             * cleanup. No synthetic EOF flag or sleep duration decides it. */
            for (;;) pause();
        } else message.descendant = descendant;
    }
    close(out_pipe[1]); close(err_pipe[1]);
    bool sent = put_all(ready_pipe[1], &message, sizeof message);
    close(ready_pipe[1]);
    if (!sent || message.error) _exit(123);
    if (which == TH_ALIVE || which == TH_OVERALL) for (;;) pause();
    _exit(which == TH_NONZERO ? 23 : 0);
}

static bool th_start(enum th_case which)
{
    int output[2], error[2], ready_fd[2];
    if (pipe2(output, O_CLOEXEC) < 0) return false;
    if (pipe2(error, O_CLOEXEC) < 0) { close(output[0]); close(output[1]); return false; }
    if (pipe2(ready_fd, O_CLOEXEC | O_NONBLOCK) < 0) {
        close(output[0]); close(output[1]); close(error[0]); close(error[1]); return false;
    }
    launcher = fork();
    if (!launcher) th_fixture(which, output, error, ready_fd);
    close(output[1]); close(error[1]); close(ready_fd[1]);
    if (launcher < 0) { close(output[0]); close(error[0]); close(ready_fd[0]); return false; }
    streams[0].fd = output[0]; streams[1].fd = error[0];
    bool ok = true;
    for (unsigned i = 0; i < 2; ++i) {
        int flags = fcntl(streams[i].fd, F_GETFL);
        if (flags < 0 || fcntl(streams[i].fd, F_SETFL, flags | O_NONBLOCK) < 0) ok = false;
    }
    struct th_ready message = {0};
    size_t used = 0;
    uint64_t deadline = now_ns() + UINT64_C(3000000000);
    while (ok && used < sizeof message && now_ns() < deadline && !interrupted) {
        ssize_t got = read(ready_fd[0], (unsigned char *)&message + used, sizeof message - used);
        if (got > 0) used += (size_t)got;
        else if (!got) { ok = false; break; }
        else if (errno != EAGAIN && errno != EINTR) { ok = false; break; }
        else { struct pollfd p = {.fd = ready_fd[0], .events = POLLIN}; (void)poll(&p, 1, 5); }
    }
    close(ready_fd[0]);
    th_descendant = message.descendant;
    ok = th_artifact("fixture-ready.bin", &message, used) && ok;
    return ok && used == sizeof message && !message.error && message.pid == launcher &&
           getpgid(launcher) == launcher && task_ticks(launcher, launcher, &launcher_ticks);
}

static bool th_prime(enum th_case which)
{
    uint64_t deadline = now_ns() + UINT64_C(3000000000);
    while (now_ns() < deadline && !failed && !interrupted) {
        pump(5);
        bool expected_done = which != TH_ALIVE && which != TH_OVERALL;
        bool expected_out = which != TH_STDOUT, expected_err = which != TH_STDERR;
        if (launcher_done == expected_done && streams[0].eof == expected_out && streams[1].eof == expected_err &&
            streams[0].sink.stored == sizeof th_out - 1 && streams[1].sink.stored == sizeof th_err - 1) return true;
    }
    return false;
}

static bool th_peek(siginfo_t *info)
{
    memset(info, 0, sizeof *info);
    return waitid(P_PID, (id_t)launcher, info, WEXITED | WNOHANG | WNOWAIT) == 0;
}

static bool th_cleanup(void)
{
    if (launcher <= 0) return true;
    /* The unreaped launcher retains its PID; the confirmed setsid group was
     * created by our direct child. Never signal the harness's own group. */
    pid_t group = getpgid(launcher);
    errno = 0;
    int sent = group == launcher ? kill(-launcher, SIGKILL) : kill(launcher, SIGKILL);
    int error = sent < 0 ? errno : 0;
    event("\"event\":\"harness-cleanup-signal\",\"launcher\":%d,\"group\":%d,\"group_signal\":%s,\"result\":%d,\"errno\":%d",
          launcher, group, group == launcher ? "true" : "false", sent, error);
    bool ok = sent == 0 || error == ESRCH;
    uint64_t deadline = now_ns() + UINT64_C(2000000000);
    while (now_ns() < deadline) {
        int status;
        pid_t got = waitpid(-1, &status, WNOHANG);
        if (got > 0) {
            ++th_reaped;
            if (got == launcher) { th_launcher_wait = status; launcher_reaped = true; }
            else if (got == th_descendant) th_descendant_wait = status;
            else ok = false;
            event("\"event\":\"harness-cleanup-reap\",\"pid\":%d,\"raw_wait_status\":%d", got, status);
        } else if (got < 0 && errno == ECHILD) {
            drain_stream(&streams[0]); drain_stream(&streams[1]);
            uint64_t observed_ns = now_ns();
            bool complete = ok && launcher_reaped && (th_descendant <= 0 || th_descendant_wait >= 0) &&
                            streams[0].eof && streams[1].eof && observed_ns < deadline;
            event("\"event\":\"harness-cleanup-observed\",\"monotonic_observed_ns\":%" PRIu64 ",\"deadline_ns\":%" PRIu64 ",\"stdout_eof\":%s,\"stderr_eof\":%s,\"complete\":%s",
                  observed_ns, deadline, streams[0].eof ? "true" : "false", streams[1].eof ? "true" : "false", complete ? "true" : "false");
            return complete;
        } else if (got < 0 && errno != EINTR) return false;
        else { struct timespec delay = {.tv_nsec = 5000000}; (void)nanosleep(&delay, NULL); }
    }
    return false;
}

int main(int argc, char **argv)
{
    if (argc != 3 || argv[2][0] != '/' || strlen(argv[2]) >= PATH_MAX) return 2;
    unsigned index;
    for (index = 0; index < sizeof th_names / sizeof th_names[0]; ++index)
        if (!strcmp(argv[1], th_names[index])) break;
    if (index == sizeof th_names / sizeof th_names[0]) return 2;
    enum th_case which = (enum th_case)index;
    if (mkdir(argv[2], 0700) < 0) return 2;
    attempt_fd = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (attempt_fd < 0) return 2;
    int argv_fd = new_file("argv.nul");
    if (argv_fd < 0) return 2;
    for (int i = 0; i < argc; ++i) if (!put_all(argv_fd, argv[i], strlen(argv[i]) + 1)) return 2;
    if (fsync(argv_fd) < 0 || close(argv_fd) < 0) return 2;
    if (!start_sink(&events, "events.jsonl", EVENT_LIMIT) ||
        !start_sink(&streams[0].sink, "stdout.bin", STREAM_LIMIT) ||
        !start_sink(&streams[1].sink, "stderr.bin", STREAM_LIMIT)) return 2;
    sigset_t unblocked; sigemptyset(&unblocked);
    struct sigaction action = {.sa_handler = th_alarm}; sigemptyset(&action.sa_mask);
    if (sigprocmask(SIG_SETMASK, &unblocked, NULL) < 0 || sigaction(SIGALRM, &action, NULL) < 0 ||
        signal(SIGCHLD, SIG_DFL) == SIG_ERR || signal(SIGPIPE, SIG_IGN) == SIG_ERR ||
        prctl(PR_SET_CHILD_SUBREAPER, 1) < 0) return 2;
    alarm(10); /* Independent fail-stop signal; the controller's clocks stay real. */
    /* The positive exit case deliberately lets the method's own pump discover
     * exit/EOF. Other cases establish independent real boundary preconditions. */
    bool setup = th_start(which) && (which == TH_EXIT || th_prime(which));
    th_check(setup, "real-child-and-scenario-preconditions");
    bool observed = false;
    uint64_t begin = 0, end = 0, deadline = 0, original_ticks = launcher_ticks;
    siginfo_t first = {0}, second = {0};
    bool first_ok = false, second_ok = false;
    if (setup) {
        uint64_t sampled = now_ns();
        /* Seed origin fields, not the clock/deadline function. Preserve the
         * actual method expression min(input+15s, started+90s). */
        if (sampled < UINT64_C(91000000000) || launcher_ticks == UINT64_MAX) setup = false;
        else {
            started_ns = sampled;
            input_ns = sampled - UINT64_C(15000000000) + UINT64_C(200000000);
            if (which == TH_EXIT || which == TH_TICKS || which == TH_NONZERO)
                input_ns = sampled - UINT64_C(15000000000) + UINT64_C(1000000000);
            if (which == TH_EXPIRED) input_ns = sampled - UINT64_C(15000000000) - UINT64_C(1000000);
            if (which == TH_OVERALL) { input_ns = sampled; started_ns = sampled - UINT64_C(90000000000) + UINT64_C(200000000); }
            overall_deadline = started_ns + UINT64_C(90000000000);
            deadline = input_ns + UINT64_C(15000000000);
            if (overall_deadline < deadline) deadline = overall_deadline;
            if (which == TH_TICKS) ++launcher_ticks;
            char seed[1536];
            int length = snprintf(seed, sizeof seed,
                "{\"case\":\"%s\",\"clock\":\"actual CLOCK_MONOTONIC\",\"seeded_origin_fields_only\":true,\"sampled_ns\":%" PRIu64 ",\"input_ns\":%" PRIu64 ",\"input_limit_ns\":15000000000,\"started_ns\":%" PRIu64 ",\"overall_limit_ns\":90000000000,\"overall_deadline_ns\":%" PRIu64 ",\"effective_deadline_ns\":%" PRIu64 ",\"original_ticks\":%" PRIu64 ",\"method_expected_ticks\":%" PRIu64 ",\"launcher\":%d,\"descendant\":%d,\"launcher_waitable\":%s,\"stdout_eof\":%s,\"stderr_eof\":%s,\"application_acceptance\":false}\n",
                argv[1], sampled, input_ns, started_ns, overall_deadline, deadline, original_ticks,
                launcher_ticks, launcher, th_descendant, launcher_done ? "true" : "false",
                streams[0].eof ? "true" : "false", streams[1].eof ? "true" : "false");
            setup = length > 0 && (size_t)length < sizeof seed && th_artifact("seed.json", seed, (size_t)length);
        }
    }
    if (setup) {
        /* No logging or filesystem call spans this entry-budget check and the
         * actual method. A delayed seed fsync cannot turn a live-condition
         * scenario into an accepted already-expired-deadline scenario. */
        begin = now_ns();
        bool entry_budget = which == TH_EXPIRED ? begin >= deadline :
                            begin < deadline && deadline - begin >= UINT64_C(20000000);
        if (entry_budget) observed = owner_terminal_launcher_waitable();
        end = now_ns();
        first_ok = th_peek(&first); second_ok = th_peek(&second);
        char result[2048];
        int length = snprintf(result, sizeof result,
            "{\"case\":\"%s\",\"method_called\":%s,\"entry_budget_valid\":%s,\"minimum_nonexpired_entry_budget_ns\":20000000,\"method_result\":%s,\"failed\":%s,\"failure\":\"%s\",\"errno\":%d,\"first_failure_ns\":%" PRIu64 ",\"begin_ns\":%" PRIu64 ",\"end_ns\":%" PRIu64 ",\"deadline_ns\":%" PRIu64 ",\"launcher_done\":%s,\"launcher_reaped\":%s,\"launcher_kill_sent\":%s,\"stdout_eof\":%s,\"stderr_eof\":%s,\"peek1\":{\"ok\":%s,\"pid\":%d,\"code\":%d,\"status\":%d},\"peek2\":{\"ok\":%s,\"pid\":%d,\"code\":%d,\"status\":%d},\"application_acceptance\":false,\"transport_acceptance\":false}\n",
            argv[1], entry_budget ? "true" : "false", entry_budget ? "true" : "false", observed ? "true" : "false", failed ? "true" : "false", first_failure, first_errno,
            first_failure_ns, begin, end, deadline, launcher_done ? "true" : "false",
            launcher_reaped ? "true" : "false", launcher_kill_sent ? "true" : "false",
            streams[0].eof ? "true" : "false", streams[1].eof ? "true" : "false",
            first_ok ? "true" : "false", first.si_pid, first.si_code, first.si_status,
            second_ok ? "true" : "false", second.si_pid, second.si_code, second.si_status);
        /* Preserve the original observation before assertion reporting/signals/reaping. */
        th_check(length > 0 && (size_t)length < sizeof result && th_artifact("observation-before-cleanup.json", result, (size_t)length), "original-observation-retained");
        th_check(entry_budget, "real-method-entry-budget-not-consumed-by-seed-retention");
        bool expects_success = which == TH_EXIT || which == TH_NONZERO;
        th_check(observed == expects_success, "method-result");
        th_check(first_ok && second_ok && first.si_pid == second.si_pid && first.si_code == second.si_code && first.si_status == second.si_status, "repeat-WNOWAIT-does-not-reap");
        th_check(!launcher_reaped && !launcher_kill_sent, "method-neither-reaped-nor-killed-launcher");
        th_check(!memcmp(streams[0].bytes, th_out, sizeof th_out - 1) && !memcmp(streams[1].bytes, th_err, sizeof th_err - 1) &&
                 streams[0].sink.stored == sizeof th_out - 1 && streams[1].sink.stored == sizeof th_err - 1 &&
                 !streams[0].sink.truncated && !streams[1].sink.truncated, "exact-real-pipe-bytes");
        if (expects_success) {
            th_check(!failed && end < deadline && streams[0].eof && streams[1].eof, "timely-complete-boundary");
            th_check(first.si_pid == launcher && first.si_code == CLD_EXITED && first.si_status == (which == TH_NONZERO ? 23 : 0), "actual-exit-is-boundary-not-payload-acceptance");
        } else if (which == TH_TICKS) {
            th_check(failed && first_errno == ESTALE && !strcmp(first_failure, "owner-terminal-launcher-identity") && original_ticks + 1 == launcher_ticks,
                     "original-start-tick-mismatch-ESTALE");
        } else {
            th_check(failed && first_errno == ETIMEDOUT && !strcmp(first_failure, "phase-deadline") && end >= deadline && first_failure_ns >= deadline,
                     "original-effective-deadline-enforced");
            if (which == TH_EXPIRED) th_check(begin >= deadline && first.si_pid == launcher && streams[0].eof && streams[1].eof, "ready-after-deadline-cannot-pass");
            if (which == TH_ALIVE || which == TH_OVERALL)
                th_check(first.si_pid == 0 && !launcher_done && streams[0].eof && streams[1].eof, "EOF-does-not-substitute-for-exit");
            if (which == TH_OVERALL) th_check(deadline == overall_deadline && deadline < input_ns + UINT64_C(15000000000), "original-overall90s-minimum-selected");
            if (which == TH_STDOUT || which == TH_STDERR)
                th_check(first.si_pid == launcher && first.si_code == CLD_EXITED && th_descendant > 0 && kill(th_descendant, 0) == 0 &&
                         streams[0].eof == (which != TH_STDOUT) && streams[1].eof == (which != TH_STDERR), "waitable-with-live-descendant-writer-is-incomplete");
        }
    } else th_check(false, "fixture-setup-or-origin-arithmetic");
    if (fsync(events.fd) < 0 || fsync(streams[0].sink.fd) < 0 || fsync(streams[1].sink.fd) < 0)
        th_check(false, "pre-cleanup-captures-sync");
    bool cleaned = th_cleanup();
    th_check(cleaned, "owned-cleanup-complete");
    if (setup && cleaned) {
        th_check(th_reaped == (th_descendant > 0 ? 2u : 1u), "exact-owned-child-count-reaped");
        int expected_wait = (which == TH_ALIVE || which == TH_OVERALL) ? SIGKILL : (which == TH_NONZERO ? 23 << 8 : 0);
        th_check(th_launcher_wait == expected_wait, "actual-launcher-raw-wait");
        if (th_descendant > 0) th_check(th_descendant_wait == SIGKILL, "actual-descendant-cleanup-raw-wait");
    }
    th_check(events.seen == events.stored && !events.truncated &&
             streams[0].sink.seen == streams[0].sink.stored && !streams[0].sink.truncated &&
             streams[1].sink.seen == streams[1].sink.stored && !streams[1].sink.truncated,
             "complete-untruncated-retained-artifacts");
    alarm(0);
    char final[1024];
    int length = snprintf(final, sizeof final,
        "{\"schema_version\":1,\"scope\":\"actual Linux terminal-boundary harness only\",\"case\":\"%s\",\"status\":\"%s\",\"assertion_failures\":%u,\"setup_complete\":%s,\"cleanup_complete\":%s,\"reaped\":%u,\"launcher_raw_wait\":%d,\"descendant_raw_wait\":%d,\"application_acceptance\":false,\"transport_acceptance\":false,\"guest_execution\":false}\n",
        argv[1], th_failures ? "FAIL" : "PASS", th_failures, setup ? "true" : "false", cleaned ? "true" : "false", th_reaped, th_launcher_wait, th_descendant_wait);
    if (length <= 0 || (size_t)length >= sizeof final || !th_artifact("harness-result.json", final, (size_t)length)) return 1;
    if (fsync(events.fd) < 0 || fsync(streams[0].sink.fd) < 0 || fsync(streams[1].sink.fd) < 0 || fsync(attempt_fd) < 0) return 1;
    return th_failures ? 1 : 0;
}
