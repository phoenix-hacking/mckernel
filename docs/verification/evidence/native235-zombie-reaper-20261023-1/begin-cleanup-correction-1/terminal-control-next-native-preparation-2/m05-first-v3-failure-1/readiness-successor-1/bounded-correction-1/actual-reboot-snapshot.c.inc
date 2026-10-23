static int reboot_snapshot(const char *name, unsigned char *bytes,
                            int *count, int *error)
{
    errno = 0;
    *count = klogctl(3, (char *)bytes, REBOOT_LOG_LIMIT);
    *error = errno;
    if (*count < 0 || *count > (int)REBOOT_LOG_LIMIT) return -1;
    int bad = *count == (int)REBOOT_LOG_LIMIT;
    if (save_file(name, bytes, (size_t)*count)) bad = 1;
    return bad ? -1 : 0;
}
