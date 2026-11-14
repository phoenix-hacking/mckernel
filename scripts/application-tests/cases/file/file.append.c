#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/append-XXXXXX"; int seed = mkstemp(path); if (seed < 0) return EXIT_FAILURE;
    if (write(seed, "BASE", 4) != 4) return EXIT_FAILURE; close(seed);
    int fd = open(path, O_WRONLY | O_APPEND); if (fd < 0) return EXIT_FAILURE;
    if (lseek(fd, 0, SEEK_SET) != 0 || write(fd, "SUFFIX", 6) != 6) return EXIT_FAILURE;
    close(fd); fd = open(path, O_RDONLY); char data[11] = {0}; ssize_t n = read(fd, data, 10); int exact = n == 10 && memcmp(data, "BASESUFFIX", 10) == 0;
    printf("read=%zd exact=%d\n", n, exact); close(fd); unlink(path); return exact ? EXIT_SUCCESS : EXIT_FAILURE;
}
