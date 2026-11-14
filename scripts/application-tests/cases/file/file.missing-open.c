#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    const char *path = "/case/work/this-path-must-not-exist-021";
    unlink(path); errno = 91; int fd = open(path, O_RDONLY); int saved_errno = errno;
    printf("fd_negative=%d errno=%d still_missing=%d\n", fd < 0, saved_errno, access(path, F_OK) != 0);
    if (fd >= 0) close(fd); return (fd < 0 && saved_errno == ENOENT && access(path, F_OK) != 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
