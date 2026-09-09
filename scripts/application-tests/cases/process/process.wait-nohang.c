#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    int gate[2]; if (pipe(gate) != 0) return EXIT_FAILURE;
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) { char token; read(gate[0], &token, 1); _exit(19); }
    int status = 0; pid_t early = waitpid(child, &status, WNOHANG);
    char token = 'x'; if (write(gate[1], &token, 1) != 1) return EXIT_FAILURE;
    pid_t late = waitpid(child, &status, 0); close(gate[0]); close(gate[1]);
    printf("early=%ld released=1 late_match=%d exited=%d code=%d\n", (long)early,
           late == child, WIFEXITED(status), WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    return (early == 0 && late == child && WIFEXITED(status) && WEXITSTATUS(status) == 19)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
