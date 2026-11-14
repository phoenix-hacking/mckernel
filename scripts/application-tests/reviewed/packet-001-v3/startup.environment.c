#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    const char *alpha = getenv("APP_STARTUP_ENV_ALPHA");
    const char *beta = getenv("APP_STARTUP_ENV_BETA");
    const char *missing = getenv("APP_STARTUP_ENV_MISSING");
    if (alpha == NULL || strcmp(alpha, "ALPHA-STARTUP-VALUE") != 0 ||
        beta == NULL || strcmp(beta, "BETA-STARTUP-VALUE") != 0 ||
        missing != NULL) {
        fputs("unexpected environment values or presence\n", stderr);
        return 41;
    }
    if (printf("{\"case\":\"startup.environment\",\"alpha\":\"%s\","
               "\"beta\":\"%s\",\"missing_is_null\":true}\n", alpha, beta) < 0 ||
        fflush(stdout) != 0) {
        return 42;
    }
    return 0;
}
