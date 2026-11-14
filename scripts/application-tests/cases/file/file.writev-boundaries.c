#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/uio.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/writev-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char a[3] = {0x00, 0x01, 0x00}, b[5] = {0xff, 0x00, 0x7f, 0x00, 0x80}, c[4] = {0x42, 0x00, 0x43, 0x00}, output[12];
    struct iovec v[3] = {{a, sizeof(a)}, {b, sizeof(b)}, {c, sizeof(c)}};
    ssize_t wrote = writev(fd, v, 3); if (lseek(fd, 0, SEEK_SET) != 0 || read(fd, output, sizeof(output)) != (ssize_t)sizeof(output)) return EXIT_FAILURE;
    unsigned char expected[12]; for (size_t i = 0; i < 3; ++i) expected[i] = a[i]; for (size_t i = 0; i < 5; ++i) expected[3 + i] = b[i]; for (size_t i = 0; i < 4; ++i) expected[8 + i] = c[i];
    size_t bad = 12; for (size_t i = 0; i < 12; ++i) if (output[i] != expected[i]) { bad = i; break; }
    printf("written=%zd bad_index=%zu\n", wrote, bad);
    close(fd); unlink(path); return (wrote == 12 && bad == 12) ? EXIT_SUCCESS : EXIT_FAILURE;
}
