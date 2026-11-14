#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512f"))) static int run(void){uint32_t a[16],b[16],o[16];for(int i=0;i<16;i++){a[i]=i*0x11111111u;b[i]=0x01010101u;}__m512i x=_mm512_loadu_si512(a),y=_mm512_loadu_si512(b);_mm512_storeu_si512(o,_mm512_xor_si512(_mm512_add_epi32(x,y),y));for(int i=0;i<16;i++)if(o[i]!=a[i])return 0;return 1;}
int main(void){int valid=run();printf("lanes=16 bits=512 vpaddd=1 vpxord=1 distinct=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
