#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx"))) static int run(void){ double a[8]={1,2,4,8,16,32,64,128}; __m256d lo=_mm256_loadu_pd(a),hi=_mm256_loadu_pd(a+4); __m256d s=_mm256_add_pd(lo,hi); __m128d l=_mm256_extractf128_pd(s,0),h=_mm256_extractf128_pd(s,1); double x[2]; _mm_storeu_pd(x,_mm_add_pd(l,h)); double want=((a[0]+a[4])+(a[1]+a[5]))+((a[2]+a[6])+(a[3]+a[7])); return x[0]+x[1]==want; }
int main(void){int valid=run();printf("lanes=8 halves=2 tree=pairwise dyadic=1 vaddpd=1 vextractf128=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
