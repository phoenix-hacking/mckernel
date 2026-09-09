#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <time.h>

static volatile sig_atomic_t events;
static void handler(int sig) { (void)sig; ++events; }

int main(void) {
    struct sigaction sa = {.sa_handler = handler}; sigemptyset(&sa.sa_mask); if (sigaction(SIGALRM, &sa, NULL) != 0) return EXIT_FAILURE;
    struct itimerval timer = {{{0, 10000}, {0, 0}}, {{0, 10000}, {0, 0}}};
    struct timespec req = {1, 0}, rem = {0, 0}; if (setitimer(ITIMER_REAL, &timer, NULL) != 0) return EXIT_FAILURE;
    int rc = nanosleep(&req, &rem); int saved_errno = errno; struct itimerval disarm = {0}; setitimer(ITIMER_REAL, &disarm, NULL);
    int bounded = rem.tv_sec >= 0 && rem.tv_nsec >= 0 && rem.tv_nsec < 1000000000L && (rem.tv_sec < req.tv_sec || (rem.tv_sec == req.tv_sec && rem.tv_nsec <= req.tv_nsec));
    printf("rc=%d errno=%d events=%d rem_sec=%lld rem_nsec=%ld bounded=%d\n", rc, saved_errno, events, (long long)rem.tv_sec, rem.tv_nsec, bounded);
    return (rc == -1 && saved_errno == EINTR && events == 1 && bounded) ? EXIT_SUCCESS : EXIT_FAILURE;
}
