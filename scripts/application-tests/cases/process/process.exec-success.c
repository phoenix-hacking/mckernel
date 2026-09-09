#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv, char **envp) {
    const char *stage = getenv("EXEC_STAGE");
    if (stage && strcmp(stage, "1") == 0) {
        int env_ok = getenv("LANG") && strcmp(getenv("LANG"), "C") == 0 && getenv("LC_ALL") && strcmp(getenv("LC_ALL"), "C") == 0;
        printf("argc=%d argv0=%s argv1=%s argv2_len=%zu argv3=%s env_ok=%d\n", argc, argv[0], argv[1], strlen(argv[2]), argv[3], env_ok);
        return (argc == 4 && strcmp(argv[1], "argA") == 0 && argv[2][0] == '\0' && strcmp(argv[3], "argB") == 0 && env_ok) ? 23 : 24;
    }
    char *args[] = {"/apps/process.exec-success", "argA", "", "argB", NULL};
    char *env[] = {"LANG=C", "LC_ALL=C", "EXEC_STAGE=1", NULL};
    execve("/proc/self/exe", args, env);
    (void)argc; (void)argv; (void)envp; return EXIT_FAILURE;
}
