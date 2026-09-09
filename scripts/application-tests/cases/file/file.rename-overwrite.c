#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char src[] = "/case/work/rename-over-src-XXXXXX", dst[] = "/case/work/rename-over-dst-XXXXXX";
    int source = mkstemp(src), target = mkstemp(dst); if (source < 0 || target < 0) return EXIT_FAILURE;
    if (write(source, "SOURCE", 6) != 6 || write(target, "TARGET", 6) != 6 || lseek(target, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    int old_target = dup(target); if (old_target < 0 || rename(src, dst) != 0) return EXIT_FAILURE;
    char path_data[7] = {0}, fd_data[7] = {0}; int pathfd = open(dst, O_RDONLY); if (pathfd < 0) return EXIT_FAILURE;
    ssize_t path_n = read(pathfd, path_data, 6), fd_n = read(old_target, fd_data, 6);
    int path_source = path_n == 6 && memcmp(path_data, "SOURCE", 6) == 0; int fd_target = fd_n == 6 && memcmp(fd_data, "TARGET", 6) == 0;
    printf("path_source=%d old_fd_target=%d\n", path_source, fd_target);
    close(pathfd); close(old_target); close(target); unlink(dst); return (path_source && fd_target) ? EXIT_SUCCESS : EXIT_FAILURE;
}
