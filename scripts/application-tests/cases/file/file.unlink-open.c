#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/unlink-open-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char input[16], output[16]; for (size_t i = 0; i < 16; ++i) input[i] = (unsigned char)(0x90u + i);
    if (write(fd, input, 16) != 16 || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    if (unlink(path) != 0) return EXIT_FAILURE; int missing = access(path, F_OK) != 0;
    ssize_t n = read(fd, output, 16); int exact = n == 16 && memcmp(input, output, 16) == 0;
    printf("path_missing=%d read=%zd exact=%d\n", missing, n, exact); close(fd);
    return (missing && exact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
