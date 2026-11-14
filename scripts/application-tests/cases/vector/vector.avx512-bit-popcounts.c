#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512vpopcntdq,avx512f"))) static int run(void){uint32_t d[16],o[16];uint64_t q[8],r[8];for(int i=0;i<16;i++)d[i]=i?((1u<<i)-1):0;for(int i=0;i<8;i++)q[i]=(1ULL<<(i+1))-1;_mm512_storeu_si512(o,_mm512_popcnt_epi32(_mm512_loadu_si512(d)));_mm512_storeu_si512(r,_mm512_popcnt_epi64(_mm512_loadu_si512(q)));for(int i=0;i<16;i++)if(o[i]!=(uint32_t)i)return 0;for(int i=0;i<8;i++)if(r[i]!=(uint64_t)(i+1))return 0;return 1;}
int main(void){int valid=run();printf("dword_lanes=16 qword_lanes=8 vpopcntd=1 vpopcntq=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
