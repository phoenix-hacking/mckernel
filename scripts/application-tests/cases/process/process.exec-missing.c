#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    int private_state = 37; char *const args[] = {"/missing/frozen-executable", NULL};
    errno = 0; int rc = execve("/missing/frozen-executable", args, NULL); int saved_errno = errno;
    printf("rc=%d errno=%d enoent=%d state=%d unchanged=%d\n", rc, saved_errno, saved_errno == ENOENT,
           private_state, private_state == 37);
    return (rc == -1 && saved_errno == ENOENT && private_state == 37) ? EXIT_SUCCESS : EXIT_FAILURE;
}
