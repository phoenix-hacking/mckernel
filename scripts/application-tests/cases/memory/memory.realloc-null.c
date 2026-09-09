#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const size_t sizes[] = {1, 4095, 4096, 4097, 65553, 1048576};
    for (size_t s = 0; s < sizeof(sizes) / sizeof(sizes[0]); ++s) {
        size_t n = sizes[s];
        unsigned char *p = (unsigned char *)realloc(NULL, n);
        if (p == NULL) return EXIT_FAILURE;
        for (size_t i = 0; i < n; ++i) p[i] = (unsigned char)((i * 37u + 11u) & 0xffu);
        size_t bad = n;
        for (size_t i = 0; i < n; ++i) {
            if (p[i] != (unsigned char)((i * 37u + 11u) & 0xffu)) { bad = i; break; }
        }
        printf("bytes=%zu bad_index=%zu\n", n, bad);
        free(p);
    }
    return EXIT_SUCCESS;
}
