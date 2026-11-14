/* Read-only readiness for the two frozen simple-process epochs. The existing
 * 5s loops remain the only polling/deadline owners; no shutdown retry occurs. */
static int reboot_snapshot(const char *name, unsigned char *bytes,
                            int *count, int *error);
static int save_file(const char *path, const void *bytes, size_t count);
extern int m05_begin_ready(const unsigned char *bytes, size_t count, uint64_t epoch);
static int begin_retired_at(const char *path, uint64_t epoch)
{
    static unsigned char previous[262144], current[262144];
    static size_t previous_n;
    static uint64_t previous_epoch;
    int count;
    if (epoch != 1 && epoch != 2) return -1;
    int state = retired_at(path);
    if (state != 1) return state;
    /* Polls only acquire a bounded read-only snapshot. Retain at most the
     * first and terminal snapshot for each epoch; every saved file is O_EXCL.
     * Reusing the first filename at poll two would fail with EEXIST. */
    errno = 0;
    count = klogctl(3, (char *)current, sizeof current);
    if (count <= 0 || (size_t)count >= sizeof current) return -1;
    if (previous_epoch && previous_epoch != epoch &&
        !(previous_epoch == 1 && epoch == 2)) return -1;
    if (previous_epoch && ((size_t)count < previous_n ||
        memcmp(current, previous, previous_n))) return -1;
    if (previous_epoch != epoch) {
        const char *first = epoch == 1 ? "/case/evidence/begin-readiness-1.kmsg" :
                                        "/case/evidence/begin-readiness-2.kmsg";
        if (save_file(first, current, (size_t)count)) return -1;
    }
    int ready = m05_begin_ready(current, (size_t)count, epoch);
    if (ready < 0) return -1;
    if (ready == 1) {
        const char *terminal = epoch == 1 ? "/case/evidence/begin-readiness-1-terminal.kmsg" :
                                           "/case/evidence/begin-readiness-2-terminal.kmsg";
        if (save_file(terminal, current, (size_t)count)) return -1;
    }
    memcpy(previous, current, (size_t)count);
    previous_n = (size_t)count; previous_epoch = epoch;
    return ready;
}

