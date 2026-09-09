#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("vpclmulqdq,avx2"))) static int run(void){ uint64_t a[4]={1,2,3,4},b[4]={5,6,7,8},o[4]; __m256i x=_mm256_loadu_si256((const __m256i*)a),y=_mm256_loadu_si256((const __m256i*)b); __m256i r=_mm256_clmulepi64_epi128(x,y,0x00); _mm256_storeu_si256((__m256i*)o,r); return o[0]==5 && o[2]==21; }
int main(void){int valid=run();printf("products=2 lanes=4 vpclmulqdq=1 independent=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
