    uint64_t begin_retirement = now_ns();
    uint64_t end = bounded_deadline(begin_retirement + 5000 * MS, 0);
    while (begin_retirement) {
        uint64_t current = now_ns();
        if (!current || current >= end) break;
        int state = retired_at("/proc/mcos0");
        /* Procfs deletion can precede the continuing service's retirement
         * retry. Keep the existing bounded window available to that service;
         * only the unchanged host evaluator can accept final ACK/release. */
        empty = state == 1;
        if (state < 0) break;
        struct timespec t = {0, 10000000}; nanosleep(&t, NULL);
    }
