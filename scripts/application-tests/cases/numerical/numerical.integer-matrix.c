#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { D = 64 };
static int64_t a[D][D], b[D][D], scalar[D][D], parallel[D][D];
struct rows { int first, last; };
static void *multiply(void *arg) { struct rows *r = arg; for (int i = r->first; i < r->last; ++i) for (int j = 0; j < D; ++j) { int64_t s = 0; for (int k = 0; k < D; ++k) s += a[i][k] * b[k][j]; parallel[i][j] = s; } return NULL; }
int main(void) {
    for (int i = 0; i < D; ++i) for (int j = 0; j < D; ++j) { a[i][j] = (int64_t)(i + 1) * (j + 2); b[i][j] = i == j ? 3 : 1; }
    int64_t checksum = 0; for (int i = 0; i < D; ++i) for (int j = 0; j < D; ++j) { int64_t s = 0; for (int k = 0; k < D; ++k) s += a[i][k] * b[k][j]; scalar[i][j] = s; checksum += s; }
    pthread_t ids[4]; struct rows rs[4]; for (int t = 0; t < 4; ++t) { rs[t].first = t * 16; rs[t].last = (t + 1) * 16; if (pthread_create(&ids[t], NULL, multiply, &rs[t]) != 0) return EXIT_FAILURE; } for (int t = 0; t < 4; ++t) pthread_join(ids[t], NULL);
    int equal = 1; for (int i = 0; i < D; ++i) for (int j = 0; j < D; ++j) if (scalar[i][j] != parallel[i][j]) equal = 0;
    int valid = equal && scalar[0][0] == 2148 && scalar[63][63] == 145536 && checksum == 294328320;
    printf("dimension=64x64 corner=%lld,%lld checksum=%lld equal=%d valid=%d\n", (long long)scalar[0][0], (long long)scalar[63][63], (long long)checksum, equal, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
