#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/eventfd.h>
#include <unistd.h>

int main(void) {
    int fd = eventfd(0, EFD_NONBLOCK);
    if (fd < 0) return EXIT_FAILURE;

    uint64_t two = 2, three = 3, value = 0;
    if (write(fd, &two, sizeof(two)) != (ssize_t)sizeof(two) ||
        write(fd, &three, sizeof(three)) != (ssize_t)sizeof(three) ||
        read(fd, &value, sizeof(value)) != (ssize_t)sizeof(value)) {
        close(fd);
        return EXIT_FAILURE;
    }

    errno = 0;
    uint64_t unused = 0;
    ssize_t second = read(fd, &unused, sizeof(unused));
    int second_errno = errno;
    close(fd);
    int valid = value == 5 && second == -1 && second_errno == EAGAIN;
    printf("value=%llu second_read=%zd second_errno=%d valid=%d\n",
           (unsigned long long)value, second, second_errno, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
