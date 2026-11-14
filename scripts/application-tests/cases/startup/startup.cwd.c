#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char cwd[256];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        return errno;
    }

    printf("cwd=%s\n", cwd);
    return 0;
}
