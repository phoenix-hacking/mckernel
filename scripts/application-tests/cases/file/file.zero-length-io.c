#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/zero-io-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char original[8] = {0, 1, 2, 3, 4, 5, 6, 7}, observed[8];
    if (write(fd, original, sizeof(original)) != 8 || lseek(fd, 3, SEEK_SET) != 3) return EXIT_FAILURE;
    unsigned char buffer[1] = {0xff}; ssize_t read_zero = read(fd, buffer, 0); ssize_t write_zero = write(fd, buffer, 0); off_t offset = lseek(fd, 0, SEEK_CUR);
    if (lseek(fd, 0, SEEK_SET) != 0 || read(fd, observed, 8) != 8) return EXIT_FAILURE;
    int unchanged = memcmp(original, observed, 8) == 0;
    printf("read_zero=%zd write_zero=%zd offset=%lld unchanged=%d\n", read_zero, write_zero, (long long)offset, unchanged);
    close(fd); unlink(path); return (read_zero == 0 && write_zero == 0 && offset == 3 && unchanged) ? EXIT_SUCCESS : EXIT_FAILURE;
}
