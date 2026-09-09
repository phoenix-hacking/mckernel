#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/tmp/mckernel-dup-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unlink(path); if (write(fd, "AB", 2) != 2 || lseek(fd, 0, SEEK_SET) != 0 || fcntl(fd, F_SETFD, 0) < 0) return EXIT_FAILURE;
    int dupfd = fcntl(fd, F_DUPFD_CLOEXEC, 0); if (dupfd < 0) return EXIT_FAILURE;
    int original_flags = fcntl(fd, F_GETFD), duplicate_flags = fcntl(dupfd, F_GETFD); char a = 0, b = 0;
    ssize_t first = read(fd, &a, 1), second = read(dupfd, &b, 1);
    int shared_offset = first == 1 && second == 1 && a == 'A' && b == 'B';
    int cloexec = (duplicate_flags & FD_CLOEXEC) != 0; int original_unchanged = (original_flags & FD_CLOEXEC) == 0;
    close(fd); close(dupfd); int valid = shared_offset && cloexec && original_unchanged;
    printf("shared_offset=%d cloexec=%d original_unchanged=%d valid=%d\n", shared_offset, cloexec, original_unchanged, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
