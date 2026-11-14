#define _GNU_SOURCE

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    const size_t sizes[] = {1, 4095, 4096, 4097, 65553, 1048576};
    for (size_t s = 0; s < sizeof(sizes) / sizeof(sizes[0]); ++s) {
        char path[] = "/case/work/write-read-XXXXXX"; int fd = mkstemp(path); if (fd < 0) return EXIT_FAILURE;
        size_t n = sizes[s]; unsigned char *input = malloc(n), *output = malloc(n); if (!input || !output) return EXIT_FAILURE;
        for (size_t i = 0; i < n; ++i) input[i] = (unsigned char)((i * 31u + 17u) & 0xffu);
        ssize_t written = write(fd, input, n); if (written != (ssize_t)n || lseek(fd, 0, SEEK_SET) != 0) return EXIT_FAILURE;
        ssize_t got = 0; while (got < (ssize_t)n) { ssize_t r = read(fd, output + got, n - (size_t)got); if (r <= 0) return EXIT_FAILURE; got += r; }
        unsigned char extra; ssize_t eof = read(fd, &extra, 1); struct stat st; if (fstat(fd, &st) != 0) return EXIT_FAILURE;
        size_t bad = n; for (size_t i = 0; i < n; ++i) if (input[i] != output[i]) { bad = i; break; }
        printf("bytes=%zu written=%zd read=%zd bad_index=%zu size=%lld eof=%zd\n", n, written, got, bad, (long long)st.st_size, eof);
        free(input); free(output); close(fd); unlink(path);
    }
    return EXIT_SUCCESS;
}
