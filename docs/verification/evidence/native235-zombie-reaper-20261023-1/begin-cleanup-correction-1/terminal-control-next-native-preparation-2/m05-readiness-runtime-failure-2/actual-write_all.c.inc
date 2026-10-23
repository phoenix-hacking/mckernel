static int write_all(int fd, const void *data, size_t len)
{
    const unsigned char *p = data;
    uint64_t start = now_ns();
    if (!start) return -1;
    uint64_t deadline = bounded_deadline(start + 2000 * MS, 0);
    while (len) {
        uint64_t current = now_ns();
        if (!current || current >= deadline) break;
        ssize_t n = write(fd, p, len);
        if (n > 0) { p += n; len -= (size_t)n; }
        else if (n < 0 && (errno == EINTR || errno == EAGAIN)) {
            struct pollfd f = {fd, POLLOUT, 0};
            if (poll(&f, 1, 5) < 0 && errno != EINTR) return -1;
        } else return -1;
    }
    return len ? -1 : 0;
}
