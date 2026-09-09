#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/private-map-XXXXXX";
    int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char original[64], modified[64], observed[64];
    for (size_t i = 0; i < 64; ++i) { original[i] = (unsigned char)i; modified[i] = (unsigned char)(0xa0u + i); }
    if (write(fd, original, sizeof(original)) != (ssize_t)sizeof(original)) return EXIT_FAILURE;
    unsigned char *p = mmap(NULL, 64, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    if (p == MAP_FAILED) return EXIT_FAILURE;
    memcpy(p, modified, sizeof(modified));
    size_t mapped_bad = 64; for (size_t i = 0; i < 64; ++i) if (p[i] != modified[i]) { mapped_bad = i; break; }
    if (munmap(p, 64) != 0 || lseek(fd, 0, SEEK_SET) < 0 || read(fd, observed, 64) != 64) return EXIT_FAILURE;
    size_t file_bad = 64; for (size_t i = 0; i < 64; ++i) if (observed[i] != original[i]) { file_bad = i; break; }
    printf("mapped_bad=%zu file_bad=%zu\n", mapped_bad, file_bad);
    close(fd); unlink(path);
    return (mapped_bad == 64 && file_bad == 64) ? EXIT_SUCCESS : EXIT_FAILURE;
}
