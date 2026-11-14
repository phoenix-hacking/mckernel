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
    unsigned char *p = mmap(NULL, 12288, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED || mprotect(p + 4096, 4096, PROT_READ) != 0) return EXIT_FAILURE;
    p[0] = 0x11; p[8192] = 0x33;
    int trapped = 0;
    if (sigsetjmp(env, 1) == 0) { volatile unsigned char *q = p + 4096; *q = 0x22; }
    else trapped = 1;
    int outer_ok = (p[0] == 0x11 && p[8192] == 0x33);
    printf("trapped=%d si_code=%d fault_offset=%ld outer_ok=%d\n", trapped, code, (long)(fault - (unsigned long)p), outer_ok);
    if (munmap(p, 12288) != 0) return EXIT_FAILURE;
    return (trapped && outer_ok) ? EXIT_SUCCESS : EXIT_FAILURE;
}
