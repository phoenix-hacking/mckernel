#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    char first[] = "/case/work/hard-first-XXXXXX", second[] = "/case/work/hard-second-026";
    int fd = mkstemp(first); if (fd < 0) return EXIT_FAILURE; unlink(second);
    if (write(fd, "HARDLINK", 8) != 8 || close(fd) != 0 || link(first, second) != 0) return EXIT_FAILURE;
    struct stat a, b; if (stat(first, &a) != 0 || stat(second, &b) != 0) return EXIT_FAILURE;
    int same = a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_nlink == 2 && b.st_nlink == 2;
    int gone = unlink(first) == 0 && access(first, F_OK) != 0; int keep = stat(second, &b) == 0 && b.st_nlink == 1;
    int check = open(second, O_RDONLY); char out[9] = {0}; ssize_t n = check < 0 ? -1 : read(check, out, 8); int exact = n == 8 && memcmp(out, "HARDLINK", 8) == 0;
    printf("initial_shared=%d first_gone=%d remaining_links_one=%d read=%zd exact=%d\n", same, gone, keep, n, exact);
    if (check >= 0) close(check); unlink(second); return (same && gone && keep && exact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
