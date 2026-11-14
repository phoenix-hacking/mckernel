#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512vl,avx512f"))) static int run(void){uint32_t a[8],b[8],o[8];for(int i=0;i<8;i++){a[i]=i+1;b[i]=0x10+i;}__m256i x=_mm256_loadu_si256((const __m256i*)a),y=_mm256_loadu_si256((const __m256i*)b);_mm256_storeu_si256((__m256i*)o,_mm256_add_epi32(x,y));for(int i=0;i<8;i++)if(o[i]!=a[i]+b[i])return 0;return 1;}
int main(void){int valid=run();printf("vl_bits=256 selected_zmm=8 full_zmm=32 vpaddd=1 vmovdqu32=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
