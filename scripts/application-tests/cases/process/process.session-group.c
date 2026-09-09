#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

static pid_t child(void) { pid_t p = fork(); if (p == 0) { setpgid(0, 0); for (;;) pause(); } return p; }
int main(void) {
    pid_t a = child(), b = child(); if (a < 0 || b < 0) return EXIT_FAILURE;
    if (setpgid(a, a) != 0 || setpgid(b, b) != 0) return EXIT_FAILURE;
    pid_t ga = getpgid(a), gb = getpgid(b);
    int target_kill = kill(-ga, SIGTERM); int sa = 0; waitpid(a, &sa, 0);
    int target_sig = WIFSIGNALED(sa) && WTERMSIG(sa) == SIGTERM;
    int untouched_before = kill(b, 0) == 0; int other_kill = kill(-gb, SIGTERM); int sb = 0; waitpid(b, &sb, 0);
    int other_sig = WIFSIGNALED(sb) && WTERMSIG(sb) == SIGTERM;
    printf("groups_distinct=%d target_kill=%d target_sigterm=%d other_alive_before=%d other_kill=%d other_sigterm=%d\n",
           ga > 0 && gb > 0 && ga != gb, target_kill, target_sig, untouched_before, other_kill, other_sig);
    return (ga > 0 && gb > 0 && ga != gb && target_kill == 0 && target_sig && untouched_before && other_kill == 0 && other_sig)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
