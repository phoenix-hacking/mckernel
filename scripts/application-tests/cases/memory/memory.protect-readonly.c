#define _GNU_SOURCE

#include <setjmp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

static sigjmp_buf env;
static volatile sig_atomic_t code;
static volatile unsigned long fault;
static void handler(int sig, siginfo_t *info, void *unused) {
    (void)sig; (void)unused; code = info->si_code; fault = (unsigned long)info->si_addr; siglongjmp(env, 1);
}

int main(void) {
    struct sigaction sa = {.sa_sigaction = handler, .sa_flags = SA_SIGINFO};
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGSEGV, &sa, NULL) != 0) return EXIT_FAILURE;
    unsigned char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return EXIT_FAILURE;
    *p = 0x5a;
    if (mprotect(p, 4096, PROT_READ) != 0) return EXIT_FAILURE;
    int trapped = 0;
    if (sigsetjmp(env, 1) == 0) { volatile unsigned char *q = p; *q = 0xa5; }
    else trapped = 1;
    int unchanged = (*p == 0x5a);
    printf("trapped=%d si_code=%d fault_offset=%ld unchanged=%d\n", trapped, code, (long)(fault - (unsigned long)p), unchanged);
    if (mprotect(p, 4096, PROT_READ | PROT_WRITE) != 0 || munmap(p, 4096) != 0) return EXIT_FAILURE;
    return (trapped && unchanged) ? EXIT_SUCCESS : EXIT_FAILURE;
}
