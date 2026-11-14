#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx2"))) static int run(void){ int32_t b[8]={11,22,33,44,55,66,77,88},m[8]={-1,-1,0,0,-1,0,-1,0},o[8]; __m256i v=_mm256_maskload_epi32(b,_mm256_loadu_si256((const __m256i*)m)); _mm256_storeu_si256((__m256i*)o,v); for(int i=0;i<8;i++)if(o[i]!=(m[i]?b[i]:0))return 0; return 1; }
int main(void){int valid=run();printf("lanes=8 active=4 masked=4 guard=1 vpmaskmovd=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
