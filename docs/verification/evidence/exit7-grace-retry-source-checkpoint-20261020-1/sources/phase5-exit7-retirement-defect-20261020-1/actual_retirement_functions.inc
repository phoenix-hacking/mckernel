static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

static uint64_t bounded_deadline(uint64_t deadline, uint64_t reserve)
{
    if (collector_deadline && deadline > collector_deadline - reserve)
        return collector_deadline - reserve;
    return deadline;
}

static int retired_at(const char *path)
{
    DIR *d = opendir(path);
    if (!d) return -1; /* A missing/unreadable procfs is not retirement. */
    struct dirent *e; int empty = 1;
    errno = 0;
    while ((e = readdir(d))) {
        if (e->d_name[0] >= '0' && e->d_name[0] <= '9') empty = 0;
    }
    if (errno) empty = -1;
    if (closedir(d)) empty = -1;
    return empty;
}
