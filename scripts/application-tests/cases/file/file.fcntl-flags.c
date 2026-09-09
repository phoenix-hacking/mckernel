#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/fcntl-XXXXXX"; int seed = mkstemp(path); if (seed < 0) return EXIT_FAILURE; close(seed);
    int fd = open(path, O_RDONLY); if (fd < 0) return EXIT_FAILURE; int before = fcntl(fd, F_GETFL); if (before < 0) return EXIT_FAILURE;
    int set_rc = fcntl(fd, F_SETFL, before | O_NONBLOCK); int after = fcntl(fd, F_GETFL); int access_same = (before & O_ACCMODE) == (after & O_ACCMODE); int enabled = (after & O_NONBLOCK) != 0;
    int restore_rc = fcntl(fd, F_SETFL, before); int restored = fcntl(fd, F_GETFL) == before;
    printf("set=%d enabled=%d access_same=%d restore=%d restored=%d\n", set_rc, enabled, access_same, restore_rc, restored);
    close(fd); unlink(path); return (set_rc == 0 && enabled && access_same && restore_rc == 0 && restored) ? EXIT_SUCCESS : EXIT_FAILURE;
}
