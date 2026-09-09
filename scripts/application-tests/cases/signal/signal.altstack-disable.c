#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static volatile sig_atomic_t handled, handler_on_alt;
static unsigned char alternate[16384];
static void handler(int signo) {
    (void)signo; stack_t current;
    if (sigaltstack(NULL, &current) == 0 && (current.ss_flags & SS_ONSTACK)) handler_on_alt = 1;
    ++handled;
}

int main(void) {
    stack_t install = { .ss_sp = alternate, .ss_size = sizeof(alternate), .ss_flags = 0 }, current, disabled;
    struct sigaction sa = {0}; sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (sigaltstack(&install, NULL) != 0 || sigaltstack(NULL, &current) != 0 || sigaction(SIGUSR1, &sa, NULL) != 0) return EXIT_FAILURE;
    int installed_match = current.ss_sp == install.ss_sp && current.ss_size == install.ss_size && !(current.ss_flags & SS_DISABLE);
    stack_t off = {.ss_flags = SS_DISABLE};
    if (sigaltstack(&off, NULL) != 0 || sigaltstack(NULL, &disabled) != 0 || raise(SIGUSR1) != 0) return EXIT_FAILURE;
    int disabled_match = (disabled.ss_flags & SS_DISABLE) != 0;
    printf("installed_match=%d disabled=%d handled=%d handler_on_alt=%d\n", installed_match, disabled_match, handled, handler_on_alt);
    return (installed_match && disabled_match && handled == 1 && handler_on_alt == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
