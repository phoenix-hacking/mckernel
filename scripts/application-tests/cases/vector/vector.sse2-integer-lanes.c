#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <emmintrin.h>

__attribute__((target("sse2"))) static int run_sse2(void) {
    uint32_t a[4] = {0u, 0xffffffffu, 0x80000000u, 0xaaaaaaaa}, b[4] = {0u, 1u, 0x80000000u, 0x55555555u}, out[4];
    __m128i va = _mm_loadu_si128((const __m128i *)a), vb = _mm_loadu_si128((const __m128i *)b);
    __m128i sum = _mm_add_epi32(va, vb), x = _mm_xor_si128(va, vb), sh = _mm_slli_epi32(va, 1);
    _mm_storeu_si128((__m128i *)out, sum); uint32_t sx[4], ss[4]; _mm_storeu_si128((__m128i *)sx, x); _mm_storeu_si128((__m128i *)ss, sh);
    for (int i = 0; i < 4; ++i) if (out[i] != a[i] + b[i] || sx[i] != (a[i] ^ b[i]) || ss[i] != (a[i] << 1)) return 0;
    return 1;
}
int main(void) { int valid = run_sse2(); printf("lanes=4 add_xor_shift=1 highbit=1 alternating=1 valid=%d\n", valid); return valid ? EXIT_SUCCESS : EXIT_FAILURE; }
