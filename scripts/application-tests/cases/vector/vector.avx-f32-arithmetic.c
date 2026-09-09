#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>

__attribute__((target("avx"))) static int run(void) { float a[8] = {1,2,4,8,16,32,64,128}, b[8] = {2,3,5,7,11,13,17,19}, add[8], sub[8], mul[8]; __m256 va = _mm256_loadu_ps(a), vb = _mm256_loadu_ps(b); _mm256_storeu_ps(add, _mm256_add_ps(va, vb)); _mm256_storeu_ps(sub, _mm256_sub_ps(va, vb)); _mm256_storeu_ps(mul, _mm256_mul_ps(va, vb)); for (int i = 0; i < 8; ++i) if (add[i] != a[i] + b[i] || sub[i] != a[i] - b[i] || mul[i] != a[i] * b[i]) return 0; return 1; }
int main(void) { int valid = run(); printf("lanes=8 halves=2 add=1 subtract=1 multiply=1 dyadic=1 valid=%d\n", valid); return valid ? EXIT_SUCCESS : EXIT_FAILURE; }
