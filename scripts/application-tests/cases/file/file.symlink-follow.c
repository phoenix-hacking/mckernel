#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    const char *target = "/case/work/link-target-025", *link = "/case/work/link-name-025"; unlink(target); unlink(link);
    int fd = open(target, O_WRONLY | O_CREAT | O_EXCL, 0600); if (fd < 0) return EXIT_FAILURE; if (write(fd, "LINKDATA", 8) != 8) return EXIT_FAILURE; close(fd);
    if (symlink("link-target-025", link) != 0) return EXIT_FAILURE;
    struct stat ls, ts; if (lstat(link, &ls) != 0 || stat(link, &ts) != 0) return EXIT_FAILURE;
    fd = open(link, O_RDONLY); char data[9] = {0}; ssize_t n = fd < 0 ? -1 : read(fd, data, 8); int exact = n == 8 && memcmp(data, "LINKDATA", 8) == 0;
    printf("is_symlink=%d target_regular=%d read=%zd exact=%d\n", S_ISLNK(ls.st_mode), S_ISREG(ts.st_mode), n, exact);
    if (fd >= 0) close(fd); unlink(link); unlink(target); return (S_ISLNK(ls.st_mode) && S_ISREG(ts.st_mode) && exact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
