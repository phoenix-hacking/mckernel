#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/close-map-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char input[4096]; for (size_t i = 0; i < sizeof(input); ++i) input[i] = (unsigned char)(0x80u ^ i);
    if (write(fd, input, sizeof(input)) != (ssize_t)sizeof(input)) return EXIT_FAILURE;
    unsigned char *p = mmap(NULL, sizeof(input), PROT_READ, MAP_PRIVATE, fd, 0); if (p == MAP_FAILED) return EXIT_FAILURE;
    if (close(fd) != 0) return EXIT_FAILURE;
    size_t bad = sizeof(input); for (size_t i = 0; i < sizeof(input); ++i) if (p[i] != input[i]) { bad = i; break; }
    printf("bad_index=%zu\n", bad);
    if (munmap(p, sizeof(input)) != 0) return EXIT_FAILURE; unlink(path);
    return bad == sizeof(input) ? EXIT_SUCCESS : EXIT_FAILURE;
}
