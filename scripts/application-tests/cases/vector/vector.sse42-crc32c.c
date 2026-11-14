#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <nmmintrin.h>

static uint32_t scalar_crc(const uint8_t *p, size_t n) { uint32_t c = 0xffffffffu; for (size_t i = 0; i < n; ++i) { c ^= p[i]; for (int b = 0; b < 8; ++b) c = (c >> 1) ^ (0x82f63b78u & (uint32_t)-(int)(c & 1)); } return c ^ 0xffffffffu; }
__attribute__((target("sse4.2"))) static uint32_t hw_crc(const uint8_t *p, size_t n) { uint64_t c = 0xffffffffu; for (size_t i = 0; i < n; ++i) c = _mm_crc32_u8((uint32_t)c, p[i]); return (uint32_t)c ^ 0xffffffffu; }
int main(void) { const uint8_t msg[] = "123456789"; uint32_t expected = scalar_crc(msg, 9), hw = hw_crc(msg, 9); int valid = expected == 0xe3069283u && hw == expected; printf("bytes=9 expected=0xe3069283 hardware=0x%08x scalar=0x%08x chunked=1 valid=%d\n", hw, expected, valid); return valid ? EXIT_SUCCESS : EXIT_FAILURE; }
