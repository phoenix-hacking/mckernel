#ifndef M02_ADVERSE_TEST_ONLY
#error "adverse fixture requires explicit test-only guard"
#endif
#ifndef M02_ADVERSE_CASE
#error "adverse fixture requires explicit case selector"
#endif
#if M02_ADVERSE_CASE < 0 || M02_ADVERSE_CASE > 3
#error "unknown adverse case selector"
#endif

static int m02_adverse_child_boundary(int fd, const uint64_t *words)
{
    if (M02_ADVERSE_CASE == 0 || M02_ADVERSE_CASE == 3) return 0;
    if (M02_ADVERSE_CASE == 1) {
        const char witness[] = "M02_ADVERSE missing-setup READY-boundary\n";
        size_t left = sizeof witness - 1; const char *p = witness;
        while (left) { ssize_t n = write(STDERR_FILENO, p, left); if (n < 0 && errno == EINTR) continue; if (n <= 0) _exit(126); p += n; left -= (size_t)n; }
        _exit(0);
    }
    unsigned char bytes[SETUP_PACKET];
    for (size_t i = 0; i < SETUP_WORDS; ++i)
        for (unsigned j = 0; j < 8; ++j) bytes[i * 8 + j] = (unsigned char)(words[i] >> (8 * j));
    size_t left = 383, offset = 0;
    while (left) {
        ssize_t n = write(fd, bytes + offset, left);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) _exit(126);
        offset += (size_t)n; left -= (size_t)n;
    }
    {
        const char witness[] = "M02_ADVERSE partial-setup wrote=383\n";
        if (write(STDERR_FILENO, witness, sizeof witness - 1) != (ssize_t)(sizeof witness - 1)) _exit(126);
    }
    _exit(0);
}

static int m02_adverse_completed_wait_hook(bool waitable, bool unreaped, uint64_t completion,
                                           uint64_t deadline, const char *failure,
                                           volatile sig_atomic_t *interrupted_latch)
{
    if (M02_ADVERSE_CASE != 3 || !waitable || !unreaped || !completion || completion > deadline ||
        !failure || strcmp(failure, "none") != 0) return 0;
    const char witness[] = "M02_ADVERSE completed-wait boundary\n";
    size_t left = sizeof witness - 1; const char *p = witness;
    while (left) { ssize_t n = write(STDERR_FILENO, p, left); if (n < 0 && errno == EINTR) continue; if (n <= 0) return -1; p += n; left -= (size_t)n; }
    errno = 0;
    if (raise(SIGTERM) != 0 || interrupted_latch == NULL || *interrupted_latch != SIGTERM) return -1;
    return 1;
}
