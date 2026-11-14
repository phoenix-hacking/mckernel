#include <emmintrin.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
static volatile sig_atomic_t seen;
static void handler(int s){__m128i z=_mm_set1_epi8((char)0xa5);volatile __m128i q=z; (void)q;seen++;}
static int run(void){signal(SIGUSR1,handler);uint8_t b[16],o[16];for(int i=0;i<16;i++)b[i]=(uint8_t)(0x20+i);__m128i v=_mm_loadu_si128((const __m128i*)b);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR1);_mm_storeu_si128((__m128i*)o,v);for(int i=0;i<16;i++)if(o[i]!=b[i])return 0;return seen==1;}
int main(void){int valid=run();printf("xmm_bytes=16 handler_overwrite=1 raw_tgkill=1 restored=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
