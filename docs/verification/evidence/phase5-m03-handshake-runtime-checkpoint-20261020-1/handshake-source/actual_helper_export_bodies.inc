static unsigned helper_timeout_ms(const char *path)
{
    return !strcmp(path, "/bin/native-boot") ? BOOT_TIMEOUT_MS : HELPER_TIMEOUT_MS;
}

static int append(char *b, size_t *n, const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    int z = vsnprintf(b + *n, FRAME_LIMIT - *n, fmt, ap); va_end(ap);
    if (z < 0 || (size_t)z >= FRAME_LIMIT - *n) return -1;
    *n += (size_t)z; return 0;
}

static int stream_json(char *b, size_t *n, const struct stream *s)
{
    char h[STREAM_LIMIT * 2 + 1];
    const char *hex = "0123456789abcdef";
    for (size_t i = 0; i != s->kept; ++i) {
        h[2*i] = hex[s->data[i] >> 4]; h[2*i+1] = hex[s->data[i] & 15];
    }
    h[2*s->kept] = 0;
    return append(b, n, "{\"hex\":\"%s\",\"eof\":%s,\"truncated\":%s,"
                  "\"observed\":%llu,\"retained\":%zu,\"discarded\":%llu,"
                  "\"limit\":%u,\"eof_ns\":%llu}", h, s->eof ? "true" : "false",
                  s->observed != s->kept ? "true" : "false",
                  (unsigned long long)s->observed, s->kept,
                  (unsigned long long)(s->observed - s->kept), STREAM_LIMIT,
                  (unsigned long long)s->eof_ns);
}

static int frame(char *b, const struct result *r, int empty)
{
    size_t n = 0;
#if defined(ND_CORE_MEMORY) || defined(ND_CORE_FILES) || \
    defined(ND_CORE_THREADS) || defined(ND_CORE_SIGNALS)
    const char *const argv_case = nd_core_case;
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\","
               "\"app\",\"%s\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", argv_case, r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
#elif defined(ND_FUTEX) || defined(ND_PROCESS_EXEC_WAIT) || defined(ND_M03_MPROTECT_UNALIGNED)
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\",\"/apps/app\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
#else
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\","
               "\"app\",\"A\",\"\",\"B\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
#endif
        stream_json(b, &n, &r->out) || append(b, &n, ",\"stderr\":") ||
        stream_json(b, &n, &r->err) ||
        append(b, &n, "},\"procfs_empty\":%s}\n",
               empty && r->clean && !r->fault && !r->timeout ? "true" : "false")) return -1;
    return (int)n;
}


static int publish(int fd, const struct result *r, int empty)
{
    char b[FRAME_LIMIT];
    int n = frame(b, r, empty);
    if (n < 0) {
        struct result failed = *r;
        failed.fault = 1; failed.out.kept = 0; failed.err.kept = 0;
        n = frame(b, &failed, 0);
    }
#if defined(ND_FUTEX)
    if (n <= 0 || (unsigned)n > FRAME_LIMIT) return -1;
    return write_all(fd, b, (size_t)n);
#else
    if (n <= 0 || n > (int)PIPE_BUF) return -1;
    ssize_t written;
    do { written = write(fd, b, (size_t)n); } while (written < 0 && errno == EINTR);
    return written == n ? 0 : -1;
#endif
}

static int helper_failure_tag(const char *tag)
{
    return tag && (!strcmp(tag, "load-ihk") || !strcmp(tag, "load-smp") ||
                   !strcmp(tag, "load-mcctrl") || !strcmp(tag, "boot"));
}

static void remember_helper_failure(const char *tag, const struct result *r,
                                    int evidence_fault)
{
    if (failed_helper.ready || !helper_failure_tag(tag)) return;
    failed_helper.tag = tag;
    failed_helper.actual = *r;
    failed_helper.evidence_fault = evidence_fault;
    failed_helper.ready = 1;
}

static int helper_failure_frame(char *b, int omit_streams)
{
    const struct result *r = &failed_helper.actual;
    struct stream out = r->out, err = r->err;
    size_t n = 0;
    if (!failed_helper.ready || !helper_failure_tag(failed_helper.tag) ||
        out.kept > STREAM_LIMIT || err.kept > STREAM_LIMIT ||
        out.observed < out.kept || err.observed < err.kept) return -1;
    if (omit_streams) out.kept = err.kept = 0;
    if (append(b, &n, "ND_HELPER_FAIL {\"helper\":\"%s\",\"raw_wait_status\":%d,"
               "\"fault\":%d,\"timeout\":%d,\"clean\":%d,\"stage\":%d,\"errno\":%d,"
               "\"evidence_fault\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"captured_stdout_bytes\":%zu,\"captured_stderr_bytes\":%zu,"
               "\"frame_streams_omitted\":%s,\"streams\":{\"stdout\":",
               failed_helper.tag, r->status, r->fault, r->timeout, r->clean,
               r->child_stage, r->child_errno, failed_helper.evidence_fault,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished, r->out.kept, r->err.kept,
               omit_streams ? "true" : "false") ||
        stream_json(b, &n, &out) || append(b, &n, ",\"stderr\":") ||
        stream_json(b, &n, &err) || append(b, &n, "}}\n")) return -1;
    return (int)n;
}

static int publish_helper_failure(int fd)
{
    char b[FRAME_LIMIT];
    int n = helper_failure_frame(b, 0);
    if (n < 0) n = helper_failure_frame(b, 1);
#if defined(ND_FUTEX)
    if (n <= 0 || (unsigned)n > FRAME_LIMIT) return -1;
    return write_all(fd, b, (size_t)n);
#else
    if (n <= 0 || n > (int)PIPE_BUF) return -1;
    ssize_t written;
    do { written = write(fd, b, (size_t)n); } while (written < 0 && errno == EINTR);
    return written == n ? 0 : -1;
#endif
}

#if defined(ND_M03_MPROTECT_UNALIGNED)
static struct { const char *phase; int number; } startup_failure;
static int refuse_startup(const char *phase)
{
    startup_failure.phase = phase;
    startup_failure.number = errno;
    return -1;
}
#endif

static int publish_diagnostic(int fd, const struct result *payload, int empty, int safe)
{
    if (!safe) return -1;
    /* A failed helper precedes app execution. Its original evidence replaces
     * the unstarted-payload frame, using the same single-frame console budget. */
    if (failed_helper.ready && (!payload || !payload->started))
        return publish_helper_failure(fd);
#if defined(ND_M03_MPROTECT_UNALIGNED)
    if (startup_failure.phase && (!payload || !payload->started)) {
        char b[256];
        int n = snprintf(b, sizeof b,
                         "ND_STARTUP_FAIL {\"phase\":\"%s\",\"errno\":%d,"
                         "\"app_started\":false}\n",
                         startup_failure.phase, startup_failure.number);
        if (n <= 0 || (size_t)n >= sizeof b) return -1;
        ssize_t written;
        do { written = write(fd, b, (size_t)n); } while (written < 0 && errno == EINTR);
        return written == n ? 0 : -1;
    }
#endif
    if (!payload) return -1;
    return publish(fd, payload, empty);
}

static int helper(const char *tag, const char *path, char *const av[], int *safe)
{
    struct result r; char name[128], record[256]; int evidence_fault = 0;
    supervise(path, av, helper_env, NULL, helper_timeout_ms(path), &r);
    if (!r.clean) *safe = 0;
    int bad = r.fault || r.timeout || !r.clean || r.status != 0 ||
              !r.out.eof || !r.err.eof || r.out.observed != r.out.kept ||
              r.err.observed != r.err.kept;
    snprintf(name, sizeof name, "/case/evidence/%s.stdout", tag);
    if (save_file(name, r.out.data, r.out.kept)) bad = evidence_fault = 1;
    snprintf(name, sizeof name, "/case/evidence/%s.stderr", tag);
    if (save_file(name, r.err.data, r.err.kept)) bad = evidence_fault = 1;
    int n = snprintf(record, sizeof record, "status=%d fault=%d timeout=%d clean=%d stage=%d errno=%d\n",
                     r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
    snprintf(name, sizeof name, "/case/evidence/%s.status", tag);
    if (n < 0 || (size_t)n >= sizeof record || save_file(name, record, (size_t)n)) bad = evidence_fault = 1;
    if (bad) remember_helper_failure(tag, &r, evidence_fault);
    return bad ? -1 : 0;
}
