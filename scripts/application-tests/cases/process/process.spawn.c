#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <spawn.h>

extern char **environ;
int main(void) {
    if (getenv("SPAWN_STAGE")) { puts("spawn_stage=1"); fflush(stdout); return 23; }
    char *args[] = {"/apps/process.spawn", NULL}; char *env[] = {"LANG=C", "LC_ALL=C", "SPAWN_STAGE=1", NULL};
    pid_t child; int spawn_rc = posix_spawn(&child, "/proc/self/exe", NULL, NULL, args, env);
    if (spawn_rc != 0) return EXIT_FAILURE;
    int status = 0; pid_t reaped = waitpid(child, &status, 0);
    printf("spawn_rc=%d reaped=%d exited=%d code=%d\n", spawn_rc, reaped == child, WIFEXITED(status),
           WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    return (reaped == child && WIFEXITED(status) && WEXITSTATUS(status) == 23) ? EXIT_SUCCESS : EXIT_FAILURE;
}
