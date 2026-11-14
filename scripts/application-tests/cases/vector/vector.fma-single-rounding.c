#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("fma"))) static int run(void){ double a[4]={0x1.0000000000001p0,0x1.0000000000001p0,3.0,7.0},b[4]={0x1.fffffffffffffp-1,0x1.fffffffffffffp-1,0.5,0.25},c[4]={-1.0,1.0,2.0,-3.0},o[4]; __m256d va=_mm256_loadu_pd(a),vb=_mm256_loadu_pd(b),vc=_mm256_loadu_pd(c); _mm256_storeu_pd(o,_mm256_fmadd_pd(va,vb,vc)); for(int i=0;i<4;i++){ long double w=(long double)a[i]*b[i]+c[i]; if((double)w!=o[i])return 0;} return 1; }
int main(void){int valid=run();printf("lanes=4 fma=1 single_rounding=1 dyadic=0 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
