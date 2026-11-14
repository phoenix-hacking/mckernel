#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/uio.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/readv-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char source[24], a[3], b[9], c[18]; for (size_t i = 0; i < 24; ++i) source[i] = (unsigned char)(0x30u + i);
    if (write(fd, source, 24) != 24 || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    for (size_t i = 0; i < sizeof(a); ++i) a[i] = 0xcc; for (size_t i = 0; i < sizeof(b); ++i) b[i] = 0xcc; for (size_t i = 0; i < sizeof(c); ++i) c[i] = 0xcc;
    struct iovec v[3] = {{a + 1, 1}, {b + 1, 7}, {c + 1, 16}};
    ssize_t got = readv(fd, v, 3); size_t bad = 24;
    for (size_t i = 0; i < 1; ++i) if (a[1 + i] != source[i]) bad = i;
    for (size_t i = 0; i < 7 && bad == 24; ++i) if (b[1 + i] != source[1 + i]) bad = 1 + i;
    for (size_t i = 0; i < 16 && bad == 24; ++i) if (c[1 + i] != source[8 + i]) bad = 8 + i;
    int guards = (a[0] == 0xcc && a[2] == 0xcc && b[0] == 0xcc && b[8] == 0xcc && c[0] == 0xcc && c[17] == 0xcc);
    printf("read=%zd bad_index=%zu guards=%d\n", got, bad, guards);
    close(fd); unlink(path); return (got == 24 && bad == 24 && guards) ? EXIT_SUCCESS : EXIT_FAILURE;
}
