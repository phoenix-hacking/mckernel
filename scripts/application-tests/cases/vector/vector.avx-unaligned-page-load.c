#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx"))) static int run(void){ uint8_t b[96],o[32]; for(int i=0;i<96;i++)b[i]=(uint8_t)(i*13u+7u); for(int off=0;off<32;off++){ __m256i v=_mm256_loadu_si256((const __m256i*)(b+off)); _mm256_storeu_si256((__m256i*)o,v); for(int j=0;j<32;j++)if(o[j]!=b[off+j])return 0;} return 1; }
int main(void){int valid=run();printf("offsets=32 bytes=32 straddle=1 vmovdqu=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
