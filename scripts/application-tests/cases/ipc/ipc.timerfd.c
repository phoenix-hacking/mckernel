#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/timerfd.h>
#include <poll.h>
#include <unistd.h>

int main(void) {
    int fd = timerfd_create(CLOCK_MONOTONIC, TFD_NONBLOCK | TFD_CLOEXEC);
    if (fd < 0) return EXIT_FAILURE;
    struct itimerspec timer = {0};
    timer.it_value.tv_nsec = 20000000;
    if (timerfd_settime(fd, 0, &timer, NULL) != 0) { close(fd); return EXIT_FAILURE; }
    struct pollfd pfd = {.fd = fd, .events = POLLIN};
    int poll_rc = poll(&pfd, 1, 1000);
    uint64_t expirations = 0;
    ssize_t n = read(fd, &expirations, sizeof(expirations));
    struct itimerspec disarm = {0};
    int disarm_rc = timerfd_settime(fd, 0, &disarm, NULL);
    pfd.revents = 0;
    int quiet_rc = poll(&pfd, 1, 0);
    int quiet = quiet_rc == 0 && pfd.revents == 0;
    close(fd);
    int valid = poll_rc == 1 && (pfd.revents == 0 || quiet) && n == (ssize_t)sizeof(expirations) && expirations >= 1 && disarm_rc == 0 && quiet;
    printf("poll_rc=%d expirations=%llu disarm_rc=%d quiet=%d valid=%d\n",
           poll_rc, (unsigned long long)expirations, disarm_rc, quiet, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
