#include <immintrin.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
static volatile sig_atomic_t depth;
__attribute__((target("avx512f"))) static void inner(int s){uint32_t b[16];for(int i=0;i<16;i++)b[i]=0x500+i;__m512i v=_mm512_loadu_si512(b);__asm__ volatile("kmovw %0, %%k1\n\tsyscall"::"r"(0x5a5a):"memory","rcx","r11");volatile __m512i q=v;(void)q;depth=2;}
static void outer(int s){struct sigaction a={0};a.sa_handler=inner;sigaction(SIGUSR2,&a,0);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR2);depth=depth==2?2:1;}
int main(void){signal(SIGUSR1,outer);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR1);printf("nested=2 zmm_state=1 opmask_state=1 xstate_frame=1 raw_tgkill=1 valid=%d\n",depth==2);return depth==2?EXIT_SUCCESS:EXIT_FAILURE;}
