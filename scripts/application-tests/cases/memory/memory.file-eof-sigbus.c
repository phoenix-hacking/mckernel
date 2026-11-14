#define _GNU_SOURCE

#include <fcntl.h>
#include <setjmp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

static sigjmp_buf env;
static volatile sig_atomic_t code;
static volatile unsigned long fault;
static void handler(int sig, siginfo_t *info, void *unused) { (void)sig; (void)unused; code = info->si_code; fault = (unsigned long)info->si_addr; siglongjmp(env, 1); }

int main(void) {
    char path[] = "/case/work/eof-map-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char byte = 0x6b; if (write(fd, &byte, 1) != 1) return EXIT_FAILURE;
    unsigned char *p = mmap(NULL, 8192, PROT_READ, MAP_PRIVATE, fd, 0); if (p == MAP_FAILED) return EXIT_FAILURE;
    struct sigaction sa = {.sa_sigaction = handler, .sa_flags = SA_SIGINFO}; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGBUS, &sa, NULL) != 0) return EXIT_FAILURE;
    int trapped = 0; if (sigsetjmp(env, 1) == 0) { volatile unsigned char x = p[4096]; (void)x; } else trapped = 1;
    printf("trapped=%d si_code=%d fault_offset=%ld\n", trapped, code, (long)(fault - (unsigned long)p));
    if (munmap(p, 8192) != 0) return EXIT_FAILURE; close(fd); unlink(path);
    return trapped ? EXIT_SUCCESS : EXIT_FAILURE;
}
