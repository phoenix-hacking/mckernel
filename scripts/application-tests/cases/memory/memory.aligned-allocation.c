#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const size_t aligns[] = {16, 64, 4096};
    const size_t sizes[] = {4096, 65536};
    for (size_t a = 0; a < 3; ++a) {
        for (size_t s = 0; s < 2; ++s) {
            void *raw = NULL;
            int rc = posix_memalign(&raw, aligns[a], sizes[s]);
            size_t bad = sizes[s];
            if (rc == 0 && raw != NULL) {
                unsigned char *p = raw;
                for (size_t i = 0; i < sizes[s]; ++i) p[i] = (unsigned char)((i ^ 0xa5u) & 0xffu);
                for (size_t i = 0; i < sizes[s]; ++i)
                    if (p[i] != (unsigned char)((i ^ 0xa5u) & 0xffu)) { bad = i; break; }
            }
            printf("alignment=%zu bytes=%zu rc=%d modulo=%zu bad_index=%zu\n",
                   aligns[a], sizes[s], rc, raw == NULL ? aligns[a] : (size_t)((uintptr_t)raw % aligns[a]), bad);
            if (rc == 0) free(raw);
            else if (raw != NULL) return EXIT_FAILURE;
        }
    }
    return EXIT_SUCCESS;
}
