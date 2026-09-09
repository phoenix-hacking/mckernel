#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>

static volatile sig_atomic_t handled;
static void handler(int signo) { (void)signo; ++handled; }

int main(void) {
    struct sigaction sa = {0}; sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0) return 1;
    printf("ready pid=%ld tid=%ld\n", (long)getpid(), (long)syscall(SYS_gettid)); fflush(stdout);
    while (!handled) pause();
    printf("handled=%d\n", handled); fflush(stdout);
    return handled == 1 ? 0 : 1;
}
