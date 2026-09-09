#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned char original[16384], replacement[16384];
static volatile sig_atomic_t handled, change_rc, change_errno;
static void handler(int signo) {
    (void)signo; stack_t requested = {.ss_sp = replacement, .ss_size = sizeof(replacement), .ss_flags = 0};
    errno = 0; change_rc = sigaltstack(&requested, NULL); change_errno = errno; handled = 1;
}

int main(void) {
    stack_t install = {.ss_sp = original, .ss_size = sizeof(original), .ss_flags = 0}, current;
    struct sigaction sa = {0}; sa.sa_handler = handler; sa.sa_flags = SA_ONSTACK; sigemptyset(&sa.sa_mask);
    if (sigaltstack(&install, NULL) != 0 || sigaction(SIGUSR1, &sa, NULL) != 0 || raise(SIGUSR1) != 0 || sigaltstack(NULL, &current) != 0) return EXIT_FAILURE;
    int original_valid = current.ss_sp == original && current.ss_size == sizeof(original) && !(current.ss_flags & SS_DISABLE);
    printf("change_rc=%d errno=%d eperm=%d handled=%d original_valid=%d\n", change_rc, change_errno,
           change_errno == EPERM, handled, original_valid);
    stack_t off = {.ss_flags = SS_DISABLE}; sigaltstack(&off, NULL);
    return (change_rc == -1 && change_errno == EPERM && handled == 1 && original_valid) ? EXIT_SUCCESS : EXIT_FAILURE;
}
