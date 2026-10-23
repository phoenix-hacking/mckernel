    uint64_t begin_retirement = now_ns();
    uint64_t end = bounded_deadline(begin_retirement + 5000 * MS, 0);
    while (begin_retirement) {
        uint64_t current = now_ns();
        if (!current || current >= end) break;
        int state = begin_retired_at("/proc/mcos0", 1);
        if (state == 1) { empty = 1; break; }
        if (state < 0) break;
        struct timespec t = {0, 10000000}; nanosleep(&t, NULL);
    }
