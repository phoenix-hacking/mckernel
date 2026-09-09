#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/truncate-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char original[32], retained[7], extra; for (size_t i = 0; i < 32; ++i) original[i] = (unsigned char)(0x60u + i);
    if (write(fd, original, 32) != 32 || ftruncate(fd, 7) != 0 || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    ssize_t n = read(fd, retained, 7); ssize_t eof = read(fd, &extra, 1); size_t bad = 7;
    for (size_t i = 0; i < 7; ++i) if (retained[i] != original[i]) { bad = i; break; }
    off_t size = lseek(fd, 0, SEEK_END); printf("read=%zd bad_index=%zu size=%lld eof=%zd\n", n, bad, (long long)size, eof);
    close(fd); unlink(path); return (n == 7 && bad == 7 && size == 7 && eof == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
