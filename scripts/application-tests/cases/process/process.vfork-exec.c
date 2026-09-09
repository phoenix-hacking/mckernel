#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv, char **envp) {
    if (getenv("VFORK_STAGE")) { puts("vfork_stage=1"); fflush(stdout); _exit(23); }
    int parent_state = 0x3141; pid_t child = vfork();
    if (child < 0) return EXIT_FAILURE;
    if (child == 0) {
        char *args[] = {"/apps/process.vfork-exec", NULL};
        char *env[] = {"LANG=C", "LC_ALL=C", "VFORK_STAGE=1", NULL};
        execve("/proc/self/exe", args, env); _exit(24);
    }
    int status = 0; pid_t reaped = waitpid(child, &status, 0);
    printf("reaped=%d exited=%d code=%d parent_state_ok=%d\n", reaped == child,
           WIFEXITED(status), WIFEXITED(status) ? WEXITSTATUS(status) : -1, parent_state == 0x3141);
    (void)argc; (void)argv; (void)envp;
    return (reaped == child && WIFEXITED(status) && WEXITSTATUS(status) == 23 && parent_state == 0x3141)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
