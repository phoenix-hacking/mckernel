#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char payload[] = "hello";

    int fd = open("/dev/null", O_WRONLY);
    if (fd < 0) {
        printf("open-fail errno=%d\n", errno);
        return 1;
    }

    if (close(fd) != 0) {
        printf("close-fail errno=%d\n", errno);
        return 1;
    }

    errno = 0;
    ssize_t rc = write(fd, payload, strlen(payload));
    int last_errno = errno;

    printf("write-return=%zd errno=%d\n", rc, last_errno);
    return (rc == -1 && last_errno == EBADF) ? 0 : 1;
}
