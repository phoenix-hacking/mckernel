#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    char path[] = "/case/work/grow-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
    unsigned char prefix[7] = {1, 3, 5, 7, 9, 11, 13}; if (write(fd, prefix, 7) != 7 || ftruncate(fd, 8192) != 0 || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
    unsigned char *data = calloc(1, 8192); if (!data || read(fd, data, 8192) != 8192) return EXIT_FAILURE;
    size_t prefix_bad = 7, zero_bad = 8192; for (size_t i = 0; i < 7; ++i) if (data[i] != prefix[i]) { prefix_bad = i; break; }
    for (size_t i = 7; i < 8192; ++i) if (data[i] != 0) { zero_bad = i; break; }
    struct stat st; if (fstat(fd, &st) != 0) return EXIT_FAILURE;
    printf("size=%lld prefix_bad=%zu zero_bad=%zu\n", (long long)st.st_size, prefix_bad, zero_bad);
    free(data); close(fd); unlink(path); return (st.st_size == 8192 && prefix_bad == 7 && zero_bad == 8192) ? EXIT_SUCCESS : EXIT_FAILURE;
}
