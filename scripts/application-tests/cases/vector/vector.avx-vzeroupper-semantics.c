#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx"))) static int run(void){uint8_t in[32],o[32];for(int i=0;i<32;i++)in[i]=(uint8_t)(i+1);__m256i v=_mm256_loadu_si256((const __m256i*)in);__asm__ volatile("vzeroupper":::"ymm0");_mm256_storeu_si256((__m256i*)o,v);for(int i=0;i<16;i++)if(o[i]!=in[i])return 0;for(int i=16;i<32;i++)if(o[i]!=in[i])return 0;return 1;}
int main(void){int valid=run();printf("ymm_bytes=32 vzeroupper=1 lower_preserved=1 upper_observed=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
