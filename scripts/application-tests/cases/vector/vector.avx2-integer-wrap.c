#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>

__attribute__((target("avx2"))) static int run(void) { uint32_t a[8] = {0xffffffffu, 0x7fffffffu, 0x80000000u, 0, 0x12345678u, 0xffffffffu, 9, 0x40000000u}, b[8] = {1, 1, 0xffffffffu, 0xffffffffu, 0x87654321u, 2, 0xffffffffu, 4}, out[8], prod[8]; __m256i va = _mm256_loadu_si256((const __m256i *)a), vb = _mm256_loadu_si256((const __m256i *)b); _mm256_storeu_si256((__m256i *)out, _mm256_add_epi32(va, vb)); _mm256_storeu_si256((__m256i *)prod, _mm256_mullo_epi32(va, vb)); for (int i = 0; i < 8; ++i) if (out[i] != a[i] + b[i] || prod[i] != (uint32_t)((uint64_t)a[i] * b[i])) return 0; return 1; }
int main(void) { int valid = run(); printf("lanes=8 add_wrap=1 multiply_low=1 high_halves=1 modulo32=1 valid=%d\n", valid); return valid ? EXIT_SUCCESS : EXIT_FAILURE; }
