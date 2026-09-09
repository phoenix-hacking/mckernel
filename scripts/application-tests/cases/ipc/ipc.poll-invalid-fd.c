#define _GNU_SOURCE

#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE; close(p[0]);
    struct pollfd fd = {.fd = p[0], .events = POLLIN}; int rc = poll(&fd, 1, 0);
    close(p[1]);
    printf("rc=%d invalid=%d revents=%d pollnval=%d\n", rc, fd.fd >= 0, fd.revents, (fd.revents & POLLNVAL) != 0);
    return (rc == 1 && (fd.revents & POLLNVAL) && !(fd.revents & POLLIN)) ? EXIT_SUCCESS : EXIT_FAILURE;
}
