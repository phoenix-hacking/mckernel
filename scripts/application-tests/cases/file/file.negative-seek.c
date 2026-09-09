#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/negative-seek-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    if (write(fd, "0123456789", 10) != 10 || lseek(fd, 5, SEEK_SET) != 5) return EXIT_FAILURE;
    errno = 66; off_t result = lseek(fd, -1, SEEK_SET); int saved_errno = errno; off_t current = lseek(fd, 0, SEEK_CUR);
    printf("result=%lld errno=%d current=%lld\n", (long long)result, saved_errno, (long long)current);
    close(fd); unlink(path); return (result == (off_t)-1 && saved_errno == EINVAL && current == 5) ? EXIT_SUCCESS : EXIT_FAILURE;
}
