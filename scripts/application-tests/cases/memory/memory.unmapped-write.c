#define _GNU_SOURCE

#include <setjmp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

static sigjmp_buf env;
static volatile sig_atomic_t code;
static volatile unsigned long fault;
static void handler(int sig, siginfo_t *info, void *unused) { (void)sig; (void)unused; code = info->si_code; fault = (unsigned long)info->si_addr; siglongjmp(env, 1); }

int main(void) {
    struct sigaction sa = {.sa_sigaction = handler, .sa_flags = SA_SIGINFO}; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGSEGV, &sa, NULL) != 0) return EXIT_FAILURE;
    unsigned char *mapped = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (mapped == MAP_FAILED) return EXIT_FAILURE;
    mapped[0] = 0x42;
    unsigned char *stale = mapped;
    if (munmap(mapped, 4096) != 0) return EXIT_FAILURE;
    int trapped = 0;
    if (sigsetjmp(env, 1) == 0) { volatile unsigned char *q = stale; *q = 0x99; }
    else trapped = 1;
    printf("trapped=%d si_code=%d fault_offset=%ld\n", trapped, code, (long)(fault - (unsigned long)stale));
    return trapped ? EXIT_SUCCESS : EXIT_FAILURE;
}
