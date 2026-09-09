#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512vbmi,avx512bw,avx512f"))) static int run(void){uint8_t in[64],idx[64],o[64];for(int i=0;i<64;i++){in[i]=(uint8_t)(0x80+i);idx[i]=(uint8_t)(63-i);}__m512i v=_mm512_loadu_si512(in),m=_mm512_loadu_si512(idx);_mm512_storeu_si512(o,_mm512_permutexvar_epi8(m,v));for(int i=0;i<64;i++)if(o[i]!=in[63-i])return 0;return 1;}
int main(void){int valid=run();printf("bytes=64 vpermb=1 boundaries=3 full_width=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
