#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    uint64_t count = 0;
    uint32_t hash = 2166136261u;
    unsigned char buffer[257];
    size_t n;

    while ((n = fread(buffer, 1, sizeof(buffer), stdin)) != 0) {
        for (size_t i = 0; i < n; ++i) {
            hash ^= buffer[i];
            hash *= 16777619u;
            ++count;
        }
    }
    if (ferror(stdin)) {
        return EXIT_FAILURE;
    }
    printf("count=%llu\n", (unsigned long long)count);
    printf("fnv1a32=%08x\n", hash);
    printf("eof=0\n");
    return EXIT_SUCCESS;
}
