#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    char src[] = "/case/work/rename-src-XXXXXX", dst[] = "/case/work/rename-dst-021";
    int fd = mkstemp(src); if (fd < 0) return EXIT_FAILURE; unlink(dst);
    unsigned char data[32], out[32]; for (size_t i = 0; i < 32; ++i) data[i] = (unsigned char)(0x20u + i);
    if (write(fd, data, 32) != 32 || close(fd) != 0 || rename(src, dst) != 0) return EXIT_FAILURE;
    int readfd = open(dst, O_RDONLY); if (readfd < 0) return EXIT_FAILURE; ssize_t n = read(readfd, out, 32); struct stat st; int stat_rc = fstat(readfd, &st);
    int exact = n == 32 && memcmp(data, out, 32) == 0; int old_missing = access(src, F_OK) != 0;
    printf("old_missing=%d read=%zd exact=%d size=%lld\n", old_missing, n, exact, (long long)st.st_size);
    close(readfd); unlink(dst); return (old_missing && exact && stat_rc == 0 && st.st_size == 32) ? EXIT_SUCCESS : EXIT_FAILURE;
}
