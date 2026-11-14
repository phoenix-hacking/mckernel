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
