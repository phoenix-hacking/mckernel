#include <stdio.h>
#include <stdlib.h>

enum { N = 4096 };
static int cmp(const void *x, const void *y) { int a = *(const int *)x, b = *(const int *)y; return (a > b) - (a < b); }
int main(void) {
    int values[N]; for (int i = 0; i < N; ++i) values[i] = (i * 73 + 19) % 257;
    qsort(values, N, sizeof(values[0]), cmp); int ordered = 1, counts = 1;
    for (int i = 1; i < N; ++i) { if (values[i] < values[i - 1]) ordered = 0; if (values[i] != values[i - 1]) counts += 1; }
    int expected_distinct = 257; int valid = ordered && counts == expected_distinct && values[0] == 0 && values[N - 1] == 256;
    printf("count=%d distinct=%d first=%d last=%d ordered=%d permutation=%d valid=%d\n", N, counts, values[0], values[N - 1], ordered, counts == expected_distinct, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
