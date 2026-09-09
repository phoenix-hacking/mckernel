#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("avx512cd,avx512f"))) static int run(void){uint32_t d[16]={1,2,1,3,2,4,3,1,5,4,6,5,6,7,7,8},o[16];uint64_t q[8]={1,2,1,3,2,4,3,1},r[8];_mm512_storeu_si512(o,_mm512_conflict_epi32(_mm512_loadu_si512(d)));_mm512_storeu_si512(r,_mm512_conflict_epi64(_mm512_loadu_si512(q)));for(int i=0;i<16;i++){uint32_t m=0;for(int j=0;j<i;j++)if(d[j]==d[i])m|=1u<<j;if(o[i]!=m)return 0;}for(int i=0;i<8;i++){uint64_t m=0;for(int j=0;j<i;j++)if(q[j]==q[i])m|=1ULL<<j;if(r[i]!=m)return 0;}return 1;}
int main(void){int valid=run();printf("dword_lanes=16 qword_lanes=8 vpconflictd=1 vpconflictq=1 prior_sets=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
