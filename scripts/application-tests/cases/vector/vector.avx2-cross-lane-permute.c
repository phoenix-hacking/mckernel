#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

__attribute__((target("avx2"))) static int run(void){
  int32_t in[8]={10,21,32,43,104,115,126,137}, idx[8]={7,0,6,1,5,2,4,3}, out[8];
  uint8_t bytes[32], mask[32], shuffled[32]; for(int i=0;i<32;i++){bytes[i]=(uint8_t)(i<16?0x10+i:0xA0+i); mask[i]=(uint8_t)(15-(i&15));}
  __m256i v=_mm256_loadu_si256((const __m256i*)in), vi=_mm256_loadu_si256((const __m256i*)idx);
  _mm256_storeu_si256((__m256i*)out,_mm256_permutevar8x32_epi32(v,vi));
  for(int i=0;i<8;i++) if(out[i]!=in[idx[i]]) return 0;
  __m256i vb=_mm256_loadu_si256((const __m256i*)bytes), vm=_mm256_loadu_si256((const __m256i*)mask);
  _mm256_storeu_si256((__m256i*)shuffled,_mm256_shuffle_epi8(vb,vm));
  for(int i=0;i<32;i++) if(shuffled[i]!=bytes[(i/16)*16+(15-(i&15))]) return 0;
  return 1;
}
int main(void){int valid=run(); printf("lanes32=8 byte_lanes=32 halves=2 vpermd=1 vpshufb=1 valid=%d\n",valid); return valid?EXIT_SUCCESS:EXIT_FAILURE;}
