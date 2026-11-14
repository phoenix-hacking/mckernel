#define _GNU_SOURCE

#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

static sigjmp_buf jump;
static volatile sig_atomic_t seen_code;
static volatile uintptr_t seen_addr;

static void on_fault(int sig, siginfo_t *info, void *unused) {
    (void)sig; (void)unused;
    seen_code = info->si_code;
    seen_addr = (uintptr_t)info->si_addr;
    siglongjmp(jump, 1);
}

int main(void) {
    struct sigaction sa = {.sa_sigaction = on_fault, .sa_flags = SA_SIGINFO};
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGSEGV, &sa, NULL) != 0) return EXIT_FAILURE;
    const size_t page = 4096;
    unsigned char *p = mmap(NULL, page * 3, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED || munmap(p + page, page) != 0) return EXIT_FAILURE;
    p[0] = 0x11; p[2 * page] = 0x33;
    int faulted = 0;
    if (sigsetjmp(jump, 1) == 0) {
        volatile unsigned char value = p[page];
        (void)value;
    } else faulted = 1;
    printf("first=%02x third=%02x faulted=%d si_code=%d fault_offset=%lld\n",
           p[0], p[2 * page], faulted, seen_code,
           (long long)(seen_addr - (uintptr_t)(p + page)));
    int retained = (p[0] == 0x11 && p[2 * page] == 0x33);
    if (munmap(p, page) != 0 || munmap(p + 2 * page, page) != 0) return EXIT_FAILURE;
    return (faulted && retained) ? EXIT_SUCCESS : EXIT_FAILURE;
}
