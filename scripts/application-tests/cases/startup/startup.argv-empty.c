#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    printf("[startup.argv-empty]\n");
    printf("argc=%d\n", argc);
    for (int i = 0; i <= argc; i++) {
        if (argv[i] == NULL) {
            printf("argv[%d]=NULL\n", i);
        } else {
            printf("argv[%d]=%s\n", i, argv[i]);
        }
    }

    const char *env_missing = getenv("APP_STARTUP_ENV_MISSING");
    if (env_missing == NULL) {
        puts("APP_STARTUP_ENV_MISSING=NULL");
    } else {
        printf("APP_STARTUP_ENV_MISSING=%s\n", env_missing);
    }

    return 0;
}
