#include <wmmintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("pclmul"))) static int run(void){ uint64_t a[2]={0x123456789abcdef0ULL,0x0f0e0d0c0b0a0908ULL},b[2]={0xfedcba9876543210ULL,0x0102030405060708ULL},o[2]; __m128i x=_mm_loadu_si128((const __m128i*)a),y=_mm_loadu_si128((const __m128i*)b); __m128i r=_mm_clmulepi64_si128(x,y,0x00); _mm_storeu_si128((__m128i*)o,r); return (o[0]|o[1])!=0; }
int main(void){int valid=run();printf("selectors=1 source_halves=4 pclmulqdq=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
