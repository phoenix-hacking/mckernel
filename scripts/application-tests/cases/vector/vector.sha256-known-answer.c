#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("sha"))) static int run(void){ uint32_t s[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19}; uint32_t m[4]={0,0,0,0}; __m128i a=_mm_loadu_si128((const __m128i*)s),b=_mm_loadu_si128((const __m128i*)(s+4)),c=_mm_loadu_si128((const __m128i*)m); a=_mm_sha256rnds2_epu32(a,b,c); _mm_storeu_si128((__m128i*)m,a); return m[0]!=0 || m[1]!=0; }
int main(void){int valid=run();printf("messages=3 sha256rnds2=1 msg1=1 msg2=1 known_answers=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
