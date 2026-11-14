#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

int main(void) {
    mode_t old_umask = umask(022);
    const char *path = "startup.umask.testfile";

    int fd = open(path, O_CREAT | O_TRUNC | O_WRONLY, 0666);
    if (fd < 0) {
        return errno;
    }

    if (write(fd, "X", 1) < 0) {
        close(fd);
        unlink(path);
        umask(old_umask);
        return errno;
    }
    close(fd);

    struct stat st = {0};
    if (stat(path, &st) != 0) {
        unlink(path);
        umask(old_umask);
        return errno;
    }

    printf("old_umask=%04o\n", (unsigned)old_umask);
    printf("requested_mode=0666\n");
    printf("created_file_mode=%04o\n", (unsigned)(st.st_mode & 0777));

    unlink(path);
    umask(old_umask);
    return 0;
}
