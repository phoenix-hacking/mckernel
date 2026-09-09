#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const char *alpha = getenv("APP_STARTUP_ENV_ALPHA");
    const char *beta = getenv("APP_STARTUP_ENV_BETA");
    const char *missing = getenv("APP_STARTUP_ENV_MISSING");

    printf("ENV_ALPHA=%s\n", alpha ? alpha : "NULL");
    printf("ENV_BETA=%s\n", beta ? beta : "NULL");
    printf("ENV_MISSING=%s\n", missing ? missing : "NULL");

    return 0;
}
