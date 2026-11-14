#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0 || signal(SIGPIPE, SIG_IGN) == SIG_ERR) return EXIT_FAILURE;
    close(p[0]); errno = 0; int rc = (int)write(p[1], "X", 1); int saved_errno = errno; close(p[1]);
    printf("rc=%d errno=%d epipe=%d sigpipe=0\n", rc, saved_errno, saved_errno == EPIPE);
    return (rc == -1 && saved_errno == EPIPE) ? EXIT_SUCCESS : EXIT_FAILURE;
}
