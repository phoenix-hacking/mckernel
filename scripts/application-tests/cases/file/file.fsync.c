#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/fsync-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char input[128], output[128]; for (size_t i = 0; i < 128; ++i) input[i] = (unsigned char)(0xd0u ^ i);
    if (write(fd, input, 128) != 128) return EXIT_FAILURE; int sync_rc = fsync(fd); if (sync_rc != 0 || close(fd) != 0) return EXIT_FAILURE;
    fd = open(path, O_RDONLY); if (fd < 0 || read(fd, output, 128) != 128) return EXIT_FAILURE;
    int exact = memcmp(input, output, 128) == 0; printf("fsync=%d exact=%d\n", sync_rc, exact); close(fd); unlink(path);
    return (sync_rc == 0 && exact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
