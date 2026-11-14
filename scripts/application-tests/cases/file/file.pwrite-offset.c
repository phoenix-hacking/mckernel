#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/pwrite-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char original[32], patch[4], observed[32]; for (size_t i = 0; i < 32; ++i) original[i] = (unsigned char)(0x20u + i);
    for (size_t i = 0; i < 4; ++i) patch[i] = (unsigned char)(0xe0u + i);
    if (write(fd, original, 32) != 32 || lseek(fd, 7, SEEK_SET) != 7) return EXIT_FAILURE;
    ssize_t wrote = pwrite(fd, patch, 4, 20); off_t offset = lseek(fd, 0, SEEK_CUR);
    if (lseek(fd, 0, SEEK_SET) != 0 || read(fd, observed, 32) != 32) return EXIT_FAILURE;
    size_t bad = 32; for (size_t i = 0; i < 32; ++i) { unsigned char want = (i >= 20 && i < 24) ? patch[i - 20] : original[i]; if (observed[i] != want) { bad = i; break; } }
    printf("written=%zd offset=%lld bad_index=%zu\n", wrote, (long long)offset, bad);
    close(fd); unlink(path); return (wrote == 4 && offset == 7 && bad == 32) ? EXIT_SUCCESS : EXIT_FAILURE;
}
