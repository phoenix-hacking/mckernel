#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/exclusive-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    if (write(fd, "EXISTING", 8) != 8) return EXIT_FAILURE;
    struct stat before, after; if (fstat(fd, &before) != 0) return EXIT_FAILURE; close(fd);
    errno = 73; int second = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600); int saved_errno = errno;
    int check = open(path, O_RDONLY); char data[9] = {0}; if (check < 0 || read(check, data, 8) != 8 || fstat(check, &after) != 0) return EXIT_FAILURE;
    int unchanged = memcmp(data, "EXISTING", 8) == 0 && before.st_size == after.st_size;
    printf("failed=%d errno=%d unchanged=%d\n", second < 0, saved_errno, unchanged);
    if (second >= 0) close(second); close(check); unlink(path);
    return (second < 0 && saved_errno == EEXIST && unchanged) ? EXIT_SUCCESS : EXIT_FAILURE;
}
