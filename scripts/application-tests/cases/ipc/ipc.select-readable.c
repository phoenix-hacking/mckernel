#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0 || write(p[1], "Q", 1) != 1) return EXIT_FAILURE;
    fd_set set; FD_ZERO(&set); FD_SET(p[0], &set); struct timeval timeout = {.tv_sec = 1, .tv_usec = 0};
    int rc = select(p[0] + 1, &set, NULL, NULL, &timeout); char byte = 0; ssize_t n = read(p[0], &byte, 1);
    close(p[0]); close(p[1]);
    printf("rc=%d selected=%d read=%zd byte=%c exact=%d\n", rc, FD_ISSET(p[0], &set), n, byte, n == 1 && byte == 'Q');
    return (rc == 1 && FD_ISSET(p[0], &set) && n == 1 && byte == 'Q') ? EXIT_SUCCESS : EXIT_FAILURE;
}
