#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

__attribute__((target("avx2"))) static int run(void) {
  int8_t a8[32], b8[32], out8[32]; int16_t a16[16], b16[16], out16[16];
  for (int i=0;i<32;i++) { a8[i]=(i&1)?127:-128; b8[i]=(i&1)?1:-1; }
  for (int i=0;i<16;i++) { a16[i]=(i&1)?32767:-32768; b16[i]=(i&1)?1:-1; }
  __m256i x8=_mm256_loadu_si256((const __m256i*)a8), y8=_mm256_loadu_si256((const __m256i*)b8);
  __m256i x16=_mm256_loadu_si256((const __m256i*)a16), y16=_mm256_loadu_si256((const __m256i*)b16);
  _mm256_storeu_si256((__m256i*)out8,_mm256_adds_epi8(x8,y8));
  for(int i=0;i<32;i++){ int v=(int)a8[i]+b8[i]; if(v>127)v=127; if(v<-128)v=-128; if(out8[i]!=v)return 0; }
  _mm256_storeu_si256((__m256i*)out16,_mm256_subs_epi16(x16,y16));
  for(int i=0;i<16;i++){ int v=(int)a16[i]-b16[i]; if(v>32767)v=32767; if(v<-32768)v=-32768; if(out16[i]!=v)return 0; }
  return 1;
}
int main(void){int valid=run(); printf("bytes=32 words=16 add_sat8=1 sub_sat16=1 endpoints=1 valid=%d\n",valid); return valid?EXIT_SUCCESS:EXIT_FAILURE;}
