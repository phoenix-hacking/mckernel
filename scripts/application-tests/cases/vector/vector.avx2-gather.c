#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

__attribute__((target("avx2"))) static int run(void){
  int32_t table[16], idx[8]={0,5,-2,15,5,3,12,-1}, maskv[8]={-1,-1,-1,-1,0,-1,0,-1}, out[8];
  for(int i=0;i<16;i++) table[i]=1000+i*37;
  __m256i vi=_mm256_loadu_si256((const __m256i*)idx), vm=_mm256_loadu_si256((const __m256i*)maskv), seed=_mm256_set1_epi32(0x5a5a5a5a);
  _mm256_storeu_si256((__m256i*)out,_mm256_mask_i32gather_epi32(seed,table,vi,vm,4));
  for(int i=0;i<8;i++){int32_t want=maskv[i]?table[idx[i]]:0x5a5a5a5a; if(out[i]!=want)return 0;}
  return 1;
}
int main(void){int valid=run(); printf("table=16 lanes=8 scale=4 repeated=1 negative=1 masked_seed=1 valid=%d\n",valid); return valid?EXIT_SUCCESS:EXIT_FAILURE;}
