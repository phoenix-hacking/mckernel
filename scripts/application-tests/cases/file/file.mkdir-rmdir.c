#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    const char *path = "/case/work/mkdir-rmdir-023"; rmdir(path); errno = 0;
    int make = mkdir(path, 0700); struct stat st; int is_dir = stat(path, &st) == 0 && S_ISDIR(st.st_mode);
    int remove = rmdir(path); int missing = access(path, F_OK) != 0;
    printf("mkdir=%d is_dir=%d rmdir=%d missing=%d\n", make, is_dir, remove, missing);
    return (make == 0 && is_dir && remove == 0 && missing) ? EXIT_SUCCESS : EXIT_FAILURE;
}
