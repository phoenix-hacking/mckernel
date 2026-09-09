#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/dup-offset-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char source[8], out[8]; for (size_t i = 0; i < 8; ++i) source[i] = (unsigned char)(0x50u + i);
    if (write(fd, source, 8) != 8 || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    int dupfd = dup(fd); if (dupfd < 0) return EXIT_FAILURE;
    ssize_t a = read(fd, out, 1), b = read(dupfd, out + 1, 1); ssize_t total = a + b;
    for (size_t i = 2; i < 8; ++i) { ssize_t r = (i & 1) ? read(dupfd, out + i, 1) : read(fd, out + i, 1); if (r != 1) return EXIT_FAILURE; ++total; }
    size_t bad = 8; for (size_t i = 0; i < 8; ++i) if (out[i] != source[i]) { bad = i; break; }
    off_t offset = lseek(fd, 0, SEEK_CUR); printf("read_total=%zd bad_index=%zu shared_offset=%lld\n", total, bad, (long long)offset);
    close(dupfd); close(fd); unlink(path); return (total == 8 && bad == 8 && offset == 8) ? EXIT_SUCCESS : EXIT_FAILURE;
}
