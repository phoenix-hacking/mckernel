/* Read-only readiness for the two frozen simple-process epochs. The existing
 * 5s loops remain the only polling/deadline owners; no shutdown retry occurs. */
static int reboot_snapshot(const char *name, unsigned char *bytes,
                            int *count, int *error);
extern int m05_begin_ready(const unsigned char *bytes, size_t count, uint64_t epoch);
static int begin_retired_at(const char *path, uint64_t epoch)
{
    static unsigned char previous[262144], current[262144];
    static size_t previous_n;
    static uint64_t previous_epoch;
    int count, error;
    if (epoch != 1 && epoch != 2) return -1;
    int state = retired_at(path);
    if (state != 1) return state;
    const char *name = epoch == 1 ? "/case/evidence/begin-readiness-1.kmsg" :
                                    "/case/evidence/begin-readiness-2.kmsg";
    if (reboot_snapshot(name, current, &count, &error)) return -1;
    if (previous_epoch && previous_epoch != epoch &&
        !(previous_epoch == 1 && epoch == 2)) return -1;
    if (previous_epoch && ((size_t)count < previous_n ||
        memcmp(current, previous, previous_n))) return -1;
    int ready = m05_begin_ready(current, (size_t)count, epoch);
    if (ready < 0) return -1;
    memcpy(previous, current, (size_t)count);
    previous_n = (size_t)count; previous_epoch = epoch;
    return ready;
}

