#include <immintrin.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("f16c"))) static int run(void){ float in[8]={1.0f,-2.5f,65504.0f,1.0009765625f,0.00006103515625f,3.1415927f,-0.0f,INFINITY}; uint16_t h[8]; float out[8]; __m256 v=_mm256_loadu_ps(in); __m128i x=_mm256_cvtps_ph(v,0); _mm_storeu_si128((__m128i*)h,x); _mm256_storeu_ps(out,_mm256_cvtph_ps(x)); return h[0]==0x3c00 && h[1]==0xc100 && h[2]==0x7bff && h[6]==0x8000 && h[7]==0x7c00; }
int main(void){int valid=run();printf("lanes=8 modes=4 roundtrip=1 specials=1 vcvtps2ph=1 vcvtph2ps=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
