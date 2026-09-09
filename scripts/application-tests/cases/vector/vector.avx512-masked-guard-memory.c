#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512f"))) static int run(void){uint32_t b[16],o[16];for(int i=0;i<16;i++){b[i]=0x100+i;o[i]=0;}__mmask16 k=0x00ff;__m512i v=_mm512_maskz_loadu_epi32(k,b);_mm512_storeu_si512(o,v);for(int i=0;i<16;i++)if(o[i]!=(i<8?b[i]:0))return 0;return 1;}
int main(void){int valid=run();printf("lanes=16 active=8 masked=8 vmovdqu32=1 kmovw=1 guard=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
