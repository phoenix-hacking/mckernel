#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { N = 65537 };
static uint64_t rolling(const unsigned char *b, size_t n, size_t chunk) { uint64_t h = 0; for (size_t off = 0; off < n;) { size_t take = chunk < n - off ? chunk : n - off; for (size_t i = 0; i < take; ++i) h = h * UINT64_C(131) + b[off + i]; off += take; } return h; }
int main(void) {
    unsigned char *bytes = malloc(N); if (!bytes) return EXIT_FAILURE;
    for (size_t i = 0; i < N; ++i) bytes[i] = (unsigned char)((i * 37u + 11u) & 255u);
    uint64_t h1 = rolling(bytes, N, 1), h7 = rolling(bytes, N, 7), h64 = rolling(bytes, N, 64), h1023 = rolling(bytes, N, 1023), h4096 = rolling(bytes, N, 4096);
    int stable = h1 == h7 && h7 == h64 && h64 == h1023 && h1023 == h4096; uint64_t expected = UINT64_C(0);
    for (size_t i = 0; i < N; ++i) expected = expected * UINT64_C(131) + bytes[i];
    int valid = stable && h1 == expected && bytes[0] == 11 && bytes[N - 1] == (unsigned char)(((N - 1) * 37u + 11u) & 255u);
    printf("bytes=%d hash=%llu chunks=1,7,64,1023,4096 stable=%d unchanged=%d valid=%d\n", N, (unsigned long long)h1, stable, bytes[0] == 11, valid);
    free(bytes); return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
