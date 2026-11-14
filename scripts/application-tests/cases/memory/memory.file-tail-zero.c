#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/tail-map-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char input[5000]; for (size_t i = 0; i < sizeof(input); ++i) input[i] = (unsigned char)((i * 29u + 5u) & 0xffu);
    if (write(fd, input, sizeof(input)) != (ssize_t)sizeof(input)) return EXIT_FAILURE;
    unsigned char *p = mmap(NULL, 8192, PROT_READ, MAP_PRIVATE, fd, 0); if (p == MAP_FAILED) return EXIT_FAILURE;
    size_t data_bad = 5000, tail_bad = 8192;
    for (size_t i = 0; i < 5000; ++i) if (p[i] != input[i]) { data_bad = i; break; }
    for (size_t i = 5000; i < 8192; ++i) if (p[i] != 0) { tail_bad = i; break; }
    printf("data_bad=%zu tail_bad=%zu\n", data_bad, tail_bad);
    if (munmap(p, 8192) != 0) return EXIT_FAILURE; close(fd); unlink(path);
    return (data_bad == 5000 && tail_bad == 8192) ? EXIT_SUCCESS : EXIT_FAILURE;
}
