#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512vnni,avx512f"))) static int run(void){uint8_t a[64],b[64];int32_t c[16],o[16];for(int i=0;i<64;i++){a[i]=(uint8_t)(i+1);b[i]=(uint8_t)(i&7);}for(int i=0;i<16;i++)c[i]=i*3;__m512i va=_mm512_loadu_si512(a),vb=_mm512_loadu_si512(b),vc=_mm512_loadu_si512(c);_mm512_storeu_si512(o,_mm512_dpbusd_epi32(vc,va,vb));for(int i=0;i<16;i++){int w=c[i];for(int j=0;j<4;j++)w+=(int)a[i*4+j]*(int8_t)b[i*4+j];if(o[i]!=w)return 0;}return 1;}
int main(void){int valid=run();printf("lanes=16 bytes=64 vpdpbusd=1 unsigned8_signed8=1 non_saturating=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
