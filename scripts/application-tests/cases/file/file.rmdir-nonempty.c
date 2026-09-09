#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    const char *dir = "/case/work/rmdir-nonempty-025", *file = "/case/work/rmdir-nonempty-025/item";
    rmdir(dir); unlink(file); if (mkdir(dir, 0700) != 0) return EXIT_FAILURE;
    int fd = open(file, O_WRONLY | O_CREAT | O_EXCL, 0600); if (fd < 0) return EXIT_FAILURE; if (write(fd, "x", 1) != 1) return EXIT_FAILURE; close(fd);
    errno = 71; int rc = rmdir(dir); int saved_errno = errno; struct stat ds, fs; int intact = stat(dir, &ds) == 0 && stat(file, &fs) == 0;
    printf("rc=%d errno=%d intact=%d\n", rc, saved_errno, intact && S_ISDIR(ds.st_mode) && S_ISREG(fs.st_mode));
    unlink(file); rmdir(dir); return (rc == -1 && saved_errno == ENOTEMPTY && intact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
