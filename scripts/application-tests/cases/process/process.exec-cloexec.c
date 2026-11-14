#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    const char *stage = getenv("CLOEXEC_STAGE");
    if (stage && strcmp(stage, "1") == 0) {
        char data[5] = {0}; int keep = fcntl(90, F_GETFD); errno = 0; int closed = fcntl(91, F_GETFD); int closed_errno = errno;
        lseek(90, 0, SEEK_SET); int n = (int)read(90, data, 4);
        int keep_ok = keep >= 0 && n == 4 && memcmp(data, "KEEP", 4) == 0;
        printf("keep_ok=%d cloexec_ebadf=%d data=%s\n", keep_ok, closed == -1 && closed_errno == EBADF, data);
        return (keep_ok && closed == -1 && closed_errno == EBADF) ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    int fd = open("/tmp/mckernel-exec-cloexec", O_CREAT | O_RDWR | O_TRUNC, 0600);
    if (fd < 0 || write(fd, "KEEP", 4) != 4 || dup2(fd, 90) != 90 || dup2(fd, 91) != 91) return EXIT_FAILURE;
    close(fd); if (fcntl(91, F_SETFD, FD_CLOEXEC) != 0) return EXIT_FAILURE;
    char *args[] = {"/apps/process.exec-cloexec", NULL}; char *env[] = {"LANG=C", "LC_ALL=C", "CLOEXEC_STAGE=1", NULL};
    execve("/proc/self/exe", args, env); return EXIT_FAILURE;
}
