#include <immintrin.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
static volatile sig_atomic_t seen;
__attribute__((target("avx"))) static void handler(int s){__m256i z=_mm256_set1_epi8((char)0x5a);volatile __m256i q=z;(void)q;seen++;}
__attribute__((target("avx"))) static int run(void){signal(SIGUSR1,handler);uint8_t b[32],o[32];for(int i=0;i<32;i++)b[i]=(uint8_t)(0x40+i);__m256i v=_mm256_loadu_si256((const __m256i*)b);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR1);_mm256_storeu_si256((__m256i*)o,v);for(int i=0;i<32;i++)if(o[i]!=b[i])return 0;return seen==1;}
int main(void){int valid=run();printf("ymm_bytes=32 halves=2 handler_overwrite=1 raw_tgkill=1 restored=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
