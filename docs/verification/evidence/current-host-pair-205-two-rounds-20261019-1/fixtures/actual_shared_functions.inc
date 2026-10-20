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

static int save_file(const char *path, const void *p, size_t n)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    int bad = write_all(fd, p, n);
    if (close(fd)) bad = -1;
    return bad;
}

