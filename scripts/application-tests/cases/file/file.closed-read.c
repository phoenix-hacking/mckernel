#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char buf[16];

    int fd = open("/dev/null", O_RDONLY);
    if (fd < 0) {
        printf("open-fail errno=%d\n", errno);
        return 1;
    }

    if (close(fd) != 0) {
        printf("close-fail errno=%d\n", errno);
        return 1;
    }

    memset(buf, 0xCC, sizeof(buf));
    errno = 0;
    ssize_t rc = read(fd, buf, sizeof(buf));
    int last_errno = errno;

    printf("read-return=%zd errno=%d\n", rc, last_errno);
    printf("buffer-first=%d last=%d\n", (int)buf[0], (int)buf[sizeof(buf)-1]);

    return (rc == -1 && last_errno == EBADF) ? 0 : 1;
}
