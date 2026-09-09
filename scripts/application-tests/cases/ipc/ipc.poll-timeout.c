#define _GNU_SOURCE

#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE; struct pollfd fd = {.fd = p[0], .events = POLLIN};
    int rc = poll(&fd, 1, 20); int no_events = rc == 0 && fd.revents == 0;
    if (write(p[1], "Z", 1) != 1) return EXIT_FAILURE; char byte = 0; ssize_t n = read(p[0], &byte, 1);
    close(p[0]); close(p[1]);
    printf("timeout_rc=%d no_events=%d post_read=%c usable=%d\n", rc, no_events, byte, n == 1 && byte == 'Z');
    return (rc == 0 && no_events && n == 1 && byte == 'Z') ? EXIT_SUCCESS : EXIT_FAILURE;
}
