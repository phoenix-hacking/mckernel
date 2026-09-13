/* SPDX-License-Identifier: GPL-2.0-only */
/* Infrastructure only: real controller functions, PTY peer, ordinary fake child.
 * No mcexec, McKernel device, application/vector payload, QMP or fault injection. */
#define main stability_controller_main
#include "controller.c"
#undef main

static const char *h_case;
static int h_master = -1, h_peer_report = -1, h_delay_pipe[2] = {-1, -1};
static int h_input_hold = -1;
static pid_t h_peer = -1;
static bool h_assertions_ok = true;
static unsigned h_assertions;
static unsigned h_peer_request_count;
static int h_peer_observation_errno;
static uint64_t h_peer_observed_ticks;
static char h_peer_state;
static volatile sig_atomic_t h_delay_entered, h_delay_finished;
static struct sink h_peer_rx = {.fd = -1}, h_peer_tx = {.fd = -1};
static const char h_digest[] = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
static const char *const h_cases[] = {
    "normal-valid-fragmented", "normal-wrong-version", "normal-wrong-nonce",
    "normal-wrong-sequence", "normal-wrong-phase", "normal-wrong-mode",
    "normal-wrong-tgid", "normal-wrong-tid", "normal-wrong-startticks",
    "normal-invalid-digest", "normal-missing-continued", "normal-crlf",
    "normal-nul", "normal-overflow", "normal-duplicate", "normal-missing",
    "emergency-valid", "emergency-stale", "emergency-partial", "emergency-nul",
    "emergency-overflow", "emergency-missing", "emergency-late"
};

static void h_check(bool condition, const char *assertion)
{
    ++h_assertions;
    if (!condition) {
        h_assertions_ok = false;
        dprintf(2, "PROTOCOL_HARNESS ASSERTION_FAILURE case=%s assertion=%s errno=%d\n", h_case, assertion, errno);
    }
}

static void h_delay_ms(unsigned ms)
{
    struct timespec left = {.tv_sec = ms / 1000, .tv_nsec = (long)(ms % 1000) * 1000000};
    while (nanosleep(&left, &left) < 0 && errno == EINTR) {}
}

/* An actual signal stalls only this observer. Production clocks and deadlines
 * are unchanged. The peer queues its ACK while the handler is running. */
static void h_delayed_observer(int number)
{
    int saved_errno = errno;
    (void)number;
    h_delay_entered = 1;
    const char marker = 'D';
    if (write(h_delay_pipe[1], &marker, 1) != 1) h_delay_entered = -1;
    struct timespec left = {.tv_sec = 31, .tv_nsec = 0};
    while (nanosleep(&left, &left) < 0 && errno == EINTR) {}
    h_delay_finished = 1;
    errno = saved_errno;
}

static bool h_send(const void *data, size_t length)
{
    const unsigned char *bytes = data;
    size_t sent = 0;
    uint64_t deadline = now_ns() + UINT64_C(5000) * NS_PER_MS;
    while (sent < length && now_ns() < deadline) {
        ssize_t n = write(h_master, bytes + sent, length - sent);
        if (n > 0) { retain(&h_peer_tx, bytes + sent, (size_t)n); sent += (size_t)n; }
        else if (n < 0 && errno != EAGAIN && errno != EINTR) return false;
        else h_delay_ms(1);
    }
    return sent == length && !h_peer_tx.truncated;
}

/* Independent peer compares literal complete requests from the reviewed wire
 * contract. It does not call the controller's ACK parser or derive its schema. */
static bool h_request(const char *expected)
{
    char line[512];
    size_t used = 0;
    uint64_t deadline = now_ns() + UINT64_C(20000) * NS_PER_MS;
    while (used + 1 < sizeof line && now_ns() < deadline) {
        char byte;
        ssize_t n = read(h_master, &byte, 1);
        if (n > 0) {
            retain(&h_peer_rx, &byte, 1);
            line[used++] = byte;
            if (byte == '\n') {
                line[used] = 0;
                bool matches = !strcmp(line, expected);
                if (matches) ++h_peer_request_count;
                return matches;
            }
        } else if (n < 0 && errno != EAGAIN && errno != EINTR) { h_peer_observation_errno = errno; return false; }
        else h_delay_ms(1);
    }
    return false;
}

static int h_ack(char *out, size_t cap, unsigned seq, const char *phase)
{
    return snprintf(out, cap, "STF1 ACK %s %u %s prepublish-hard %d %d %" PRIu64 " %s CONTINUED\n",
                    nonce, seq, phase, launcher, worker, worker_ticks, h_digest);
}

static bool h_fake_alive(bool after_input)
{
    uint64_t ticks;
    if (!task_ticks(launcher, worker, &ticks) || ticks != worker_ticks) return false;
    struct sample s = task_sample(worker, false);
    return after_input ? !s.error && s.parsed == 9 && s.nr == SYS_pause : is_read16(&s);
}

/* The peer is the fake owner's sibling. Do not require ptrace permission to
 * read its syscall file; stat state/starttime are independent liveness facts.
 * The actual controller parent separately checks the real read/pause syscall. */
static bool h_peer_live(void)
{
    uint64_t ticks;
    char path[128], raw[4096];
    if (!task_ticks(launcher, worker, &ticks)) { h_peer_observation_errno = errno; return false; }
    h_peer_observed_ticks = ticks;
    if (ticks != worker_ticks) { h_peer_observation_errno = ESTALE; return false; }
    snprintf(path, sizeof path, "/proc/%d/task/%d/stat", launcher, worker);
    if (read_small(path, raw, sizeof raw) < 0) { h_peer_observation_errno = errno; return false; }
    char *tail = strrchr(raw, ')');
    if (!tail || tail[1] != ' ' || !tail[2] || tail[3] != ' ') { h_peer_observation_errno = EPROTO; return false; }
    h_peer_state = tail[2];
    return strchr("RSDTtKWPI", h_peer_state) != NULL;
}

static void h_peer_finish(bool ok, bool held, bool ack_sent)
{
    dprintf(h_peer_report,
            "{\"schema_version\":1,\"scope\":\"fake-peer-infrastructure-only\",\"case\":\"%s\",\"requests_matched\":%s,\"matched_request_count\":%u,\"observation_errno\":%d,\"observed_start_ticks\":%" PRIu64 ",\"observed_state_byte\":%u,\"fake_child_live_before_response\":%s,\"emergency_ack_sent\":%s,\"application_acceptance\":false}\n",
            h_case, ok ? "true" : "false", h_peer_request_count, h_peer_observation_errno, h_peer_observed_ticks,
            (unsigned char)h_peer_state, held ? "true" : "false", ack_sent ? "true" : "false");
    _exit(ok && held ? 0 : 90);
}

static void h_peer_main(void)
{
    close(tty_fd);
    close(input_fd);
    close(h_input_hold);
    close(streams[0].fd); close(streams[1].fd);
    close(h_delay_pipe[1]);
    char expected[512], ack[512];
    snprintf(expected, sizeof expected, "STF1 REQ %s 1 PRE_INPUT prepublish-hard %d %d %" PRIu64 "\n",
             nonce, launcher, worker, worker_ticks);
    if (!h_request(expected) || !h_peer_live()) h_peer_finish(false, false, false);
    int n = h_ack(ack, sizeof ack, 1, "PRE_INPUT");
    if (n <= 0 || (size_t)n >= sizeof ack) h_peer_finish(false, true, false);
    bool emergency = !strncmp(h_case, "emergency-", 10);
    if (!emergency) {
        if (!strcmp(h_case, "normal-missing")) {
            /* Witness live blocked input close to the real 10-second deadline. */
            h_delay_ms(9500);
            h_peer_finish(true, h_peer_live(), false);
        }
        if (!strcmp(h_case, "normal-valid-fragmented")) {
            for (int i = 0; i < n; ++i) {
                if (!h_send(ack + i, 1)) h_peer_finish(false, true, false);
                h_delay_ms(1);
            }
            h_peer_finish(true, h_peer_live(), false);
        }
        if (!strcmp(h_case, "normal-wrong-version")) ack[3] = '2';
        else if (!strcmp(h_case, "normal-wrong-nonce")) ack[9] = ack[9] == '0' ? '1' : '0';
        else if (!strcmp(h_case, "normal-wrong-sequence")) n = h_ack(ack, sizeof ack, 2, "PRE_INPUT");
        else if (!strcmp(h_case, "normal-wrong-phase")) n = h_ack(ack, sizeof ack, 1, "POST_RET");
        else if (!strcmp(h_case, "normal-wrong-mode")) {
            char *p = strstr(ack, "prepublish-hard"); p[0] = 'X';
        } else if (!strcmp(h_case, "normal-wrong-tgid"))
            n = snprintf(ack, sizeof ack, "STF1 ACK %s 1 PRE_INPUT prepublish-hard %d %d %" PRIu64 " %s CONTINUED\n", nonce, launcher + 1, worker, worker_ticks, h_digest);
        else if (!strcmp(h_case, "normal-wrong-tid"))
            n = snprintf(ack, sizeof ack, "STF1 ACK %s 1 PRE_INPUT prepublish-hard %d %d %" PRIu64 " %s CONTINUED\n", nonce, launcher, worker + 1, worker_ticks, h_digest);
        else if (!strcmp(h_case, "normal-wrong-startticks"))
            n = snprintf(ack, sizeof ack, "STF1 ACK %s 1 PRE_INPUT prepublish-hard %d %d %" PRIu64 " %s CONTINUED\n", nonce, launcher, worker, worker_ticks + 1, h_digest);
        else if (!strcmp(h_case, "normal-invalid-digest")) {
            char *p = strstr(ack, h_digest); p[0] = 'g';
        } else if (!strcmp(h_case, "normal-missing-continued")) {
            char *p = strstr(ack, " CONTINUED"); *p++ = '\n'; *p = 0; n = (int)strlen(ack);
        } else if (!strcmp(h_case, "normal-crlf")) {
            ack[n - 1] = '\r'; ack[n++] = '\n'; ack[n] = 0;
        } else if (!strcmp(h_case, "normal-nul")) ack[20] = 0;
        else if (!strcmp(h_case, "normal-overflow")) {
            char oversized[701]; memset(oversized, 'X', 700); oversized[700] = '\n';
            h_peer_finish(h_send(oversized, sizeof oversized), h_peer_live(), false);
        } else if (!strcmp(h_case, "normal-duplicate")) {
            char doubled[1024]; memcpy(doubled, ack, (size_t)n); memcpy(doubled + n, ack, (size_t)n);
            h_peer_finish(h_send(doubled, (size_t)n * 2), h_peer_live(), false);
        }
        h_peer_finish(h_send(ack, (size_t)n), h_peer_live(), false);
    }
    if (!h_send(ack, (size_t)n)) h_peer_finish(false, true, false);
    snprintf(expected, sizeof expected, "STF1 REQ %s 2 POST_RET prepublish-hard %d %d %" PRIu64 "\n",
             nonce, launcher, worker, worker_ticks);
    if (!h_request(expected) || !h_peer_live()) h_peer_finish(false, false, false);
    bool partial = !strcmp(h_case, "emergency-partial");
    if (partial) {
        if (!h_send("partial-old-frame", strlen("partial-old-frame"))) h_peer_finish(false, true, false);
    } else {
        n = h_ack(ack, sizeof ack, 2, "WRONG_PHASE");
        if (!h_send(ack, (size_t)n)) h_peer_finish(false, true, false);
    }
    snprintf(expected, sizeof expected, "STF1 FAIL %s 3 POST_RET prepublish-hard %d %d %" PRIu64 " %s %d\n",
             nonce, launcher, worker, worker_ticks, partial ? "phase-deadline" : "ack-identity-or-phase",
             partial ? ETIMEDOUT : EPROTO);
    if (!h_request(expected)) h_peer_finish(false, true, false);
    if (!strcmp(h_case, "emergency-missing")) {
        h_delay_ms(29500);
        h_peer_finish(true, h_peer_live(), false);
    }
    if (!strcmp(h_case, "emergency-late")) {
        struct pollfd notify = {.fd = h_delay_pipe[0], .events = POLLIN};
        char byte = 0;
        if (poll(&notify, 1, 5000) != 1 || read(h_delay_pipe[0], &byte, 1) != 1 || byte != 'D')
            h_peer_finish(false, true, false);
    }
    if (!strcmp(h_case, "emergency-stale")) {
        n = h_ack(ack, sizeof ack, 2, "POST_RET");
        if (!h_send(ack, (size_t)n)) h_peer_finish(false, true, false);
    } else if (partial) {
        if (!h_send(" trailing-rest\n", strlen(" trailing-rest\n"))) h_peer_finish(false, true, false);
    } else if (!strcmp(h_case, "emergency-nul")) {
        static const char corrupt[] = "old\0frame\n";
        if (!h_send(corrupt, sizeof corrupt - 1)) h_peer_finish(false, true, false);
    } else if (!strcmp(h_case, "emergency-overflow")) {
        char oversized[701]; memset(oversized, 'X', 700); oversized[700] = '\n';
        if (!h_send(oversized, sizeof oversized)) h_peer_finish(false, true, false);
    }
    bool held = h_peer_live();
    n = h_ack(ack, sizeof ack, 3, "EMERGENCY_CAPTURED");
    h_peer_finish(h_send(ack, (size_t)n), held, true);
}

static bool h_setup(void)
{
    if (!start_sink(&events, "controller.events.jsonl", EVENT_LIMIT) ||
        !start_sink(&streams[0].sink, "fake.stdout.bin", STREAM_LIMIT) ||
        !start_sink(&streams[1].sink, "fake.stderr.bin", STREAM_LIMIT) ||
        !start_sink(&tx, "controller.uart.tx", UART_LIMIT) ||
        !start_sink(&rx, "controller.uart.rx", UART_LIMIT) ||
        !start_sink(&h_peer_rx, "peer.uart.rx", UART_LIMIT) ||
        !start_sink(&h_peer_tx, "peer.uart.tx", UART_LIMIT)) return false;
    h_peer_report = new_file("peer-report.json");
    h_master = posix_openpt(O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (h_peer_report < 0 || h_master < 0 || grantpt(h_master) < 0 || unlockpt(h_master) < 0) return false;
    char slave[128];
    if (ptsname_r(h_master, slave, sizeof slave) != 0) return false;
    tty_fd = open(slave, O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    struct termios t;
    if (tty_fd < 0 || tcgetattr(tty_fd, &t) < 0) return false;
    cfmakeraw(&t); t.c_cflag |= CLOCAL | CREAD; t.c_cc[VMIN] = 0; t.c_cc[VTIME] = 0;
    if (tcsetattr(tty_fd, TCSANOW, &t) < 0) return false;
    int p[3][2];
    for (unsigned i = 0; i < 3; ++i) if (pipe2(p[i], O_CLOEXEC) < 0) return false;
    if (pipe2(h_delay_pipe, O_CLOEXEC) < 0) return false;
    launcher = fork();
    if (launcher < 0) return false;
    if (!launcher) {
        signal(SIGPIPE, SIG_DFL); signal(SIGTERM, SIG_DFL); signal(SIGINT, SIG_DFL);
        if (setsid() < 0 || dup2(p[0][0], 0) != 0 || dup2(p[1][1], 1) != 1 || dup2(p[2][1], 2) != 2 || !close_extra_fds()) _exit(91);
        if (!put_all(1, ready, sizeof ready - 1)) _exit(92);
        unsigned char bytes[16];
        if (read(0, bytes, sizeof bytes) != 16) _exit(93);
        for (unsigned i = 0; i < sizeof bytes; ++i) if (bytes[i] != 0xa5) _exit(94);
        static const char marker[] = "FAKE_INPUT_16\n";
        if (!put_all(1, marker, sizeof marker - 1)) _exit(95);
        for (;;) pause();
    }
    close(p[0][0]); close(p[1][1]); close(p[2][1]);
    input_fd = p[0][1]; streams[0].fd = p[1][0]; streams[1].fd = p[2][0];
    /* Actual cleanup closes controller stdin before its owned SIGKILL. Keep
     * this harness-only writer until cleanup returns so the intentionally
     * blocked fake cannot race EOF into exit93 before that real signal. */
    h_input_hold = fcntl(input_fd, F_DUPFD_CLOEXEC, 3);
    if (h_input_hold < 0) return false;
    int fds[3] = {input_fd, streams[0].fd, streams[1].fd};
    for (unsigned i = 0; i < 3; ++i) {
        int flags = fcntl(fds[i], F_GETFL);
        if (flags < 0 || fcntl(fds[i], F_SETFL, flags | O_NONBLOCK) < 0) return false;
    }
    return task_ticks(launcher, launcher, &launcher_ticks) && prepare_read();
}

int main(int argc, char **argv)
{
    if (argc != 3 || argv[2][0] != '/') return 2;
    h_case = argv[1];
    bool known = false;
    for (size_t i = 0; i < sizeof h_cases / sizeof h_cases[0]; ++i) known |= !strcmp(h_case, h_cases[i]);
    if (!known) return 2;
    mode = "prepublish-hard"; nonce = "0123456789abcdef0123456789abcdef"; guest = true; terminal_mode = true;
    started_ns = now_ns(); overall_deadline = started_ns + UINT64_C(90000) * NS_PER_MS;
    signal(SIGPIPE, SIG_IGN); signal(SIGCHLD, SIG_DFL);
    if (prctl(PR_SET_CHILD_SUBREAPER, 1) < 0 || mkdir(argv[2], 0700) < 0) return 2;
    attempt_fd = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (attempt_fd < 0) return 2;
    bool emergency = !strncmp(h_case, "emergency-", 10), pre_ok = false;
    uint64_t capture_elapsed = 0, emergency_elapsed = 0;
    int peer_status = -1;
    if (!h_setup()) { h_check(false, "fixture-setup"); goto cleanup; }
    h_peer = fork();
    if (h_peer < 0) { h_check(false, "peer-fork"); goto cleanup; }
    if (!h_peer) h_peer_main();
    uint64_t begin = now_ns();
    pre_ok = capture("PRE_INPUT");
    capture_elapsed = now_ns() - begin;
    if (!emergency) {
        bool valid = !strcmp(h_case, "normal-valid-fragmented");
        h_check(pre_ok == valid && failed == !valid, "normal-ACK-outcome");
        h_check(input_ns == 0 && h_fake_alive(false), "zero-input-and-live-blocked-fake");
        if (!strcmp(h_case, "normal-missing"))
            h_check(capture_elapsed >= UINT64_C(10000) * NS_PER_MS && capture_elapsed < UINT64_C(13000) * NS_PER_MS, "normal-real-ten-second-deadline");
    } else {
        h_check(pre_ok && !failed, "emergency-prerequisite-ACK");
        if (!pre_ok) goto cleanup;
        active_phase = "INPUT";
        h_check(release_input(), "real-sixteen-byte-fake-input");
        if (failed) goto cleanup;
        h_check(!capture("POST_RET") && failed, "post-input-failure-latched");
        const char *original_reason = first_failure;
        int original_errno = first_errno;
        uint64_t original_time = first_failure_ns;
        if (!strcmp(h_case, "emergency-late")) {
            struct sigaction action;
            memset(&action, 0, sizeof action); action.sa_handler = h_delayed_observer;
            sigemptyset(&action.sa_mask);
            h_check(sigaction(SIGALRM, &action, NULL) == 0, "install-delayed-observer");
            alarm(1);
        }
        begin = now_ns();
        emergency_capture();
        emergency_elapsed = now_ns() - begin;
        alarm(0);
        bool confirmation = strcmp(h_case, "emergency-missing") && strcmp(h_case, "emergency-late");
        h_check(emergency_attempted && emergency_capture_confirmed == confirmation, "emergency-confirmation");
        h_check(failed && first_failure == original_reason && first_errno == original_errno && first_failure_ns == original_time,
                "first-failure-never-cleared-or-replaced");
        h_check(!launcher_reaped && !launcher_kill_sent && h_fake_alive(true), "owned-fake-preserved-until-emergency-return");
        if (!strcmp(h_case, "emergency-missing"))
            h_check(emergency_elapsed >= UINT64_C(30000) * NS_PER_MS && emergency_elapsed < UINT64_C(33000) * NS_PER_MS && !ack_received,
                    "missing-emergency-real-thirty-second-deadline");
        if (!strcmp(h_case, "emergency-late"))
            h_check(h_delay_entered == 1 && h_delay_finished == 1 && ack_received && emergency_ack_ns == 0 && emergency_elapsed >= UINT64_C(31000) * NS_PER_MS,
                    "actual-ACK-observed-after-real-deadline-rejected");
    }
    if (h_peer > 0) {
        uint64_t deadline = now_ns() + UINT64_C(2000) * NS_PER_MS;
        pid_t reaped = 0;
        while (!reaped && now_ns() < deadline) {
            reaped = waitpid(h_peer, &peer_status, WNOHANG);
            if (reaped < 0 && errno == EINTR) reaped = 0;
            if (!reaped) h_delay_ms(1);
        }
        h_check(reaped == h_peer && WIFEXITED(peer_status) && WEXITSTATUS(peer_status) == 0, "independent-peer-requests-and-live-witness");
    }
cleanup:
    if (launcher > 0) {
        h_check(cleanup_owned(), "bounded-owned-cleanup");
        if (h_input_hold >= 0) { close(h_input_hold); h_input_hold = -1; }
        h_check(launcher_reaped && WIFSIGNALED(raw_wait) && WTERMSIG(raw_wait) == SIGKILL, "real-fake-child-signal-wait");
        h_check(streams[0].eof && streams[1].eof && !streams[0].sink.truncated && !streams[1].sink.truncated && streams[1].sink.stored == 0,
                "bounded-exact-fake-streams");
        const char *expected_stdout = emergency ? "NATIVE_FAILURE_READY\nFAKE_INPUT_16\n" : "NATIVE_FAILURE_READY\n";
        h_check(streams[0].sink.stored == strlen(expected_stdout) &&
                !memcmp(streams[0].bytes, expected_stdout, strlen(expected_stdout)), "literal-fake-input-byte-oracle");
    }
    h_check(!tx.truncated && !rx.truncated && !events.truncated, "bounded-controller-protocol-artifacts");
    h_check(failed == (strcmp(h_case, "normal-valid-fragmented") != 0), "final-controller-failure-state");
    unsigned expected_rejections = !strcmp(h_case, "normal-valid-fragmented") || !strcmp(h_case, "normal-missing") ? 0 : 1;
    if (!strcmp(h_case, "emergency-stale") || !strcmp(h_case, "emergency-nul") || !strcmp(h_case, "emergency-overflow")) expected_rejections = 2;
    h_check(!strcmp(h_case, "normal-overflow") ? uart_protocol_errors >= expected_rejections : uart_protocol_errors == expected_rejections,
            "every-invalid-frame-explicitly-rejected");
    int output = new_file("harness-result.json");
    if (output < 0) return 2;
    char result[2048];
    int n = snprintf(result, sizeof result,
        "{\"schema_version\":1,\"scope\":\"controller-protocol-infrastructure-only\",\"case\":\"%s\",\"status\":\"%s\",\"assertions\":%u,"
        "\"application_acceptance\":false,\"transport_acceptance\":false,\"pre_input_accepted\":%s,\"controller_failed\":%s,"
        "\"controller_first_failure\":\"%s\",\"controller_first_failure_phase\":\"%s\",\"input_begin_ns\":%" PRIu64 ","
        "\"normal_capture_elapsed_ns\":%" PRIu64 ",\"emergency_elapsed_ns\":%" PRIu64 ",\"emergency_attempted\":%s,\"emergency_confirmed\":%s,"
        "\"uart_rejections\":%u,\"ack_count\":%u,\"launcher_raw_wait\":%d,\"peer_raw_wait\":%d,\"cleanup_complete\":%s}\n",
        h_case, h_assertions_ok ? "PASS" : "FAIL", h_assertions, pre_ok ? "true" : "false", failed ? "true" : "false",
        first_failure, first_failure_phase, input_ns, capture_elapsed, emergency_elapsed, emergency_attempted ? "true" : "false",
        emergency_capture_confirmed ? "true" : "false", uart_protocol_errors, ack_count, launcher_reaped ? raw_wait : -1,
        peer_status, cleanup_complete ? "true" : "false");
    if (n < 0 || (size_t)n >= sizeof result || !put_all(output, result, (size_t)n) || !put_all(1, result, (size_t)n)) return 2;
    return h_assertions_ok ? 0 : 1;
}
