#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/dup-close-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    if (write(fd, "abc", 3) != 3) return EXIT_FAILURE;
    int dupfd = dup(fd); if (dupfd < 0 || close(fd) != 0) return EXIT_FAILURE;
    if (write(dupfd, "XYZ", 3) != 3 || lseek(dupfd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    char output[7] = {0}; ssize_t got = read(dupfd, output, 6); int exact = got == 6 && memcmp(output, "abcXYZ", 6) == 0;
    printf("read=%zd exact=%d\n", got, exact); close(dupfd); unlink(path); return exact ? EXIT_SUCCESS : EXIT_FAILURE;
}
