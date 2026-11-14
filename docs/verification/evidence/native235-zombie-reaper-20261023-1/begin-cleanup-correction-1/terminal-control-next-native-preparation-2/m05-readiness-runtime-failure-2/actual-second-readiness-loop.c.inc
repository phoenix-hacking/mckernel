    uint64_t begin = now_ns(), end = bounded_deadline(begin + 5000 * MS, 0);
    while (begin) {
        uint64_t now = now_ns();
        if (!now || now >= end) break;
        int state = begin_retired_at("/proc/mcos0", 2);
        if (state == 1) { *empty = 1; break; }
        if (state < 0) break;
        struct timespec pause = {0, 10000000}; nanosleep(&pause, NULL);
    }
