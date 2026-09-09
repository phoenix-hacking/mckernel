#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/eventfd.h>
#include <unistd.h>

int main(void) {
    int fd = eventfd(3, EFD_SEMAPHORE | EFD_NONBLOCK);
    if (fd < 0) return EXIT_FAILURE;

    uint64_t value = 0;
    ssize_t r1 = read(fd, &value, sizeof(value));
    int v1 = value == 1 && r1 == (ssize_t)sizeof(value);
    value = 0;
    ssize_t r2 = read(fd, &value, sizeof(value));
    int v2 = value == 1 && r2 == (ssize_t)sizeof(value);
    value = 0;
    ssize_t r3 = read(fd, &value, sizeof(value));
    int v3 = value == 1 && r3 == (ssize_t)sizeof(value);
    errno = 0;
    ssize_t r4 = read(fd, &value, sizeof(value));
    int fourth_errno = errno;
    close(fd);
    int valid = v1 && v2 && v3 && r4 == -1 && fourth_errno == EAGAIN;
    printf("reads=%d,%d,%d fourth_read=%zd fourth_errno=%d valid=%d\n",
           v1, v2, v3, r4, fourth_errno, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
