#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("vaes,avx2"))) static int run(void){ uint8_t in[32],key[32],o[32]; for(int i=0;i<32;i++){in[i]=(uint8_t)i;key[i]=(uint8_t)(0xa0+i);} __m256i x=_mm256_loadu_si256((const __m256i*)in),k=_mm256_loadu_si256((const __m256i*)key); x=_mm256_aesenc_epi128(x,k); x=_mm256_aesenclast_epi128(x,k); _mm256_storeu_si256((__m256i*)o,x); return o[0]!=o[16] || o[1]!=o[17]; }
int main(void){int valid=run();printf("blocks=2 bytes_per_block=16 vaesenc=1 vaesenclast=1 distinct=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
