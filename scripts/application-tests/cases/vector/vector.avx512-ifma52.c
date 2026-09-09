#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512ifma,avx512f"))) static int run(void){uint64_t a[8],b[8],c[8],lo[8],hi[8];for(int i=0;i<8;i++){a[i]=(1+i)*0x12345;b[i]=(2+i)*0x23456;c[i]=i;}__m512i x=_mm512_loadu_si512(a),y=_mm512_loadu_si512(b),z=_mm512_loadu_si512(c);_mm512_storeu_si512(lo,_mm512_madd52lo_epu64(z,x,y));_mm512_storeu_si512(hi,_mm512_madd52hi_epu64(z,x,y));for(int i=0;i<8;i++){if(lo[i]==0&&hi[i]==0)return 0;}return 1;}
int main(void){int valid=run();printf("lanes=8 operand_bits=52 accum_bits=64 vpmadd52luq=1 vpmadd52huq=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
