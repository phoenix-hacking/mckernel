#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { N = 4096 };
int main(void) {
    int64_t prefix[N]; int64_t total = 0;
    for (int i = 0; i < N; ++i) { prefix[i] = total; total += (i % 17) - 8; }
    int valid = prefix[0] == 0 && prefix[1] == -8 && prefix[N - 1] == -15 && total == -8;
    printf("count=%d first=%lld second=%lld last=%lld total=%lld valid=%d\n", N, (long long)prefix[0], (long long)prefix[1], (long long)prefix[N - 1], (long long)total, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
