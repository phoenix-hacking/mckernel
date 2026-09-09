#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

int main(void) {
    const size_t sizes[] = {1, 4095, 4096, 4097, 65553, 1048576};
    for (size_t s = 0; s < sizeof(sizes) / sizeof(sizes[0]); ++s) {
        size_t n = sizes[s], bad = 0;
        for (unsigned round = 0; round < 16; ++round) {
            unsigned char *p = mmap(NULL, n, PROT_READ | PROT_WRITE,
                                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (p == MAP_FAILED) return EXIT_FAILURE;
            for (size_t i = 0; i < n; ++i) if (p[i] != 0) { bad = round + 1; break; }
            for (size_t i = 0; i < n; ++i) p[i] = (unsigned char)(0xa5u ^ (round + i));
            if (munmap(p, n) != 0) return EXIT_FAILURE;
        }
        printf("bytes=%zu rounds=16 first_nonzero_round=%zu\n", n, bad);
    }
    return EXIT_SUCCESS;
}
