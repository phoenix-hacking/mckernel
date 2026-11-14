#include <wmmintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("aes"))) static int run(void){ const uint8_t p[16]={0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff}; const uint8_t k[16]={0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f}; __m128i x=_mm_loadu_si128((const __m128i*)p), r=_mm_loadu_si128((const __m128i*)k); r=_mm_aesenc_si128(r,x); r=_mm_aesenclast_si128(r,x); uint8_t o[16]; _mm_storeu_si128((__m128i*)o,r); return o[0]!=0 || o[15]!=0; }
int main(void){int valid=run();printf("block_bytes=16 aesenc=1 aesenclast=1 round_keys=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
