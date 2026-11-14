#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <smmintrin.h>

__attribute__((target("sse4.1"))) static int run_blends(void) {
    uint16_t a[8] = {0,1,2,3,4,5,6,7}, b[8] = {100,101,102,103,104,105,106,107}, out[8];
    const int masks[4] = {0x00, 0x55, 0xaa, 0xff};
    for (int m = 0; m < 4; ++m) { __m128i v = _mm_blend_epi16(_mm_loadu_si128((const __m128i *)a), _mm_loadu_si128((const __m128i *)b), masks[m]); _mm_storeu_si128((__m128i *)out, v); for (int i = 0; i < 8; ++i) { uint16_t e = (masks[m] & (1 << i)) ? b[i] : a[i]; if (out[i] != e) return 0; } } return 1;
}
int main(void) { int valid = run_blends(); printf("lanes=8 masks=0,85,170,255 selected=1 unselected=1 valid=%d\n", valid); return valid ? EXIT_SUCCESS : EXIT_FAILURE; }
