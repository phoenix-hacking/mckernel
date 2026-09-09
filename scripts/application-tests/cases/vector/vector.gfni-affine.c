#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("gfni"))) static int run(void){ uint64_t x[2]={0x0123456789abcdefULL,0xfedcba9876543210ULL},m[2]={0x8040201008040201ULL,0x1b1b1b1b1b1b1b1bULL}; __m128i a=_mm_loadu_si128((const __m128i*)x),b=_mm_loadu_si128((const __m128i*)m),r=_mm_gf2p8affine_epi64_epi8(a,b,0x63); uint64_t o[2]; _mm_storeu_si128((__m128i*)o,r); return o[0]!=x[0] || o[1]!=x[1]; }
int main(void){int valid=run();printf("bytes=16 matrices=2 imm=0x63 gf2p8affineqb=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
