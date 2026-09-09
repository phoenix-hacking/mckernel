#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

int main(void) {
    const size_t sizes[] = {1, 4095, 4096, 4097, 65553, 1048576};
    for (size_t s = 0; s < sizeof(sizes) / sizeof(sizes[0]); ++s) {
        size_t n = sizes[s];
        unsigned char *p = mmap(NULL, n, PROT_READ | PROT_WRITE,
                                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (p == MAP_FAILED) return EXIT_FAILURE;
        size_t zero_bad = n;
        for (size_t i = 0; i < n; ++i) if (p[i] != 0) { zero_bad = i; break; }
        for (size_t i = 0; i < n; ++i) p[i] = (unsigned char)((i * 19u + 7u) & 0xffu);
        size_t fill_bad = n;
        for (size_t i = 0; i < n; ++i)
            if (p[i] != (unsigned char)((i * 19u + 7u) & 0xffu)) { fill_bad = i; break; }
        int unmap_rc = munmap(p, n);
        printf("bytes=%zu zero_bad=%zu fill_bad=%zu munmap=%d\n", n, zero_bad, fill_bad, unmap_rc);
        if (unmap_rc != 0) return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
