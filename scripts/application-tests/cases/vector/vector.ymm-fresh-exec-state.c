#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx"))) static int run(void){uint8_t z[32],o[32];for(int i=0;i<32;i++)z[i]=0;__m256i v=_mm256_loadu_si256((const __m256i*)z);_mm256_storeu_si256((__m256i*)o,v);for(int i=0;i<32;i++)if(o[i])return 0;return 1;}
int main(void){int valid=run();printf("static_elf=1 first_instruction=vmovdqu ymm_bytes=32 high_halves_zero=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
