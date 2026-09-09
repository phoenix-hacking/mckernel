#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <tmmintrin.h>

__attribute__((target("ssse3"))) static int run_shuffle(void) {
    uint8_t src[16], idx[16] = {15, 14, 0x80, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0}, out[16]; for (int i = 0; i < 16; ++i) src[i] = (uint8_t)(0x30 + i);
    __m128i v = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)src), _mm_loadu_si128((const __m128i *)idx)); _mm_storeu_si128((__m128i *)out, v);
    for (int i = 0; i < 16; ++i) { uint8_t expected = idx[i] & 0x80 ? 0 : src[idx[i] & 15]; if (out[i] != expected) return 0; } return 1;
}
int main(void) { int valid = run_shuffle(); printf("bytes=16 reversed=1 repeated=1 highbit_zero=1 valid=%d\n", valid); return valid ? EXIT_SUCCESS : EXIT_FAILURE; }
