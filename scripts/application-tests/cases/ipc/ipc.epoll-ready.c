#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/epoll.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE;
    int ep = epoll_create1(EPOLL_CLOEXEC); if (ep < 0) return EXIT_FAILURE;
    struct epoll_event add = {.events = EPOLLIN, .data.u64 = UINT64_C(0x1234)};
    if (epoll_ctl(ep, EPOLL_CTL_ADD, p[0], &add) != 0 || write(p[1], "X", 1) != 1) return EXIT_FAILURE;
    struct epoll_event got = {0}; int rc = epoll_wait(ep, &got, 1, 1000); char byte = 0;
    ssize_t n = read(p[0], &byte, 1); int exact = rc == 1 && (got.events & EPOLLIN) != 0 && got.data.u64 == UINT64_C(0x1234) && n == 1 && byte == 'X';
    close(ep); close(p[0]); close(p[1]);
    printf("rc=%d pollin=%d token=%llu read=%zd data=%c valid=%d\n", rc, (got.events & EPOLLIN) != 0, (unsigned long long)got.data.u64, n, byte, exact);
    return exact ? EXIT_SUCCESS : EXIT_FAILURE;
}
