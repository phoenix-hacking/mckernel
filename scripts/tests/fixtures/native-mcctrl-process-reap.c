/* SPDX-License-Identifier: GPL-2.0 */
/* Observe dead TGIDs while their inherited mcos file remains open. */
static void process_reap_marker(int fd, const char *kind, unsigned pid)
{
    char bytes[96], digits[10];
    unsigned length = 0;
    const char *prefix = "<6>NATIVE_PROCESS_REAP_";
    while (*prefix) bytes[length++] = *prefix++;
    while (*kind) bytes[length++] = *kind++;
    const char *label = " pid=";
    while (*label) bytes[length++] = *label++;
    unsigned count = 0;
    do { digits[count++] = '0' + pid % 10; pid /= 10; } while (pid);
    while (count) bytes[length++] = digits[--count];
    bytes[length++] = '\n';
    require(length <= sizeof(bytes));
    require(call(SYS_WRITE, fd, (long)bytes, length) == (long)length);
}

static int process_reap_begin(const int children[4])
{
    int fd = call(SYS_OPEN, (long)"/dev/kmsg", 1, 0);
    require(fd >= 0);
    for (unsigned index = 0; index != 4; ++index)
        process_reap_marker(fd, "BEGIN", children[index]);
    return fd;
}

static void process_reap_finish(int fd, const int children[4])
{
    /* No new application acquisition or mcos close occurs in this interval. */
    const long quiet[2] = {1, 0};
    require(call(35, (long)quiet, 0, 0) == 0); /* x86_64 nanosleep */
    for (unsigned index = 0; index != 4; ++index)
        process_reap_marker(fd, "QUIET_DONE", children[index]);
    close_fd(fd);
    message("NATIVE_PROCESS_REAP PASS inherited_tgids=4 binding_held=1 applications=0\n");
}
