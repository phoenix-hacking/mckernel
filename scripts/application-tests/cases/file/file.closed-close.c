#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    int fd = open("/dev/null", O_RDONLY);
    if (fd < 0) {
        printf("open-fail errno=%d\n", errno);
        return 1;
    }

    if (close(fd) != 0) {
        printf("close-fail errno=%d\n", errno);
        return 1;
    }

    errno = 0;
    int rc = close(fd);
    int last_errno = errno;

    printf("close-return=%d errno=%d\n", rc, last_errno);
    return (rc == -1 && last_errno == EBADF) ? 0 : 1;
}
