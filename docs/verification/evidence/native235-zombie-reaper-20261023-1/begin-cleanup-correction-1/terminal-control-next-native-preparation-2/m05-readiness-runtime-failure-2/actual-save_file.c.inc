static int save_file(const char *path, const void *p, size_t n)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    int bad = write_all(fd, p, n);
    if (close(fd)) bad = -1;
    return bad;
}
