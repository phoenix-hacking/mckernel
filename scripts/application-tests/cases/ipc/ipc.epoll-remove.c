#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/epoll.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE;
    int ep = epoll_create1(EPOLL_CLOEXEC); if (ep < 0) return EXIT_FAILURE;
    struct epoll_event add = {.events = EPOLLIN, .data.fd = p[0]};
    if (epoll_ctl(ep, EPOLL_CTL_ADD, p[0], &add) != 0 || epoll_ctl(ep, EPOLL_CTL_DEL, p[0], NULL) != 0 || write(p[1], "Y", 1) != 1) return EXIT_FAILURE;
    struct epoll_event got = {0}; int rc = epoll_wait(ep, &got, 1, 0); char byte = 0; ssize_t n = read(p[0], &byte, 1);
    int removed = rc == 0 && n == 1 && byte == 'Y';
    close(ep); close(p[0]); close(p[1]);
    printf("wait_rc=%d read=%zd data=%c removed=%d\n", rc, n, byte, removed);
    return removed ? EXIT_SUCCESS : EXIT_FAILURE;
}
