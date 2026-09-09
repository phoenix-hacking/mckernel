#include <immintrin.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
static stack_t ss; static volatile sig_atomic_t depth;
__attribute__((target("avx"))) static void inner(int s){uint8_t b[32];__m256i v=_mm256_set1_epi8((char)0x22);_mm256_storeu_si256((__m256i*)b,v);depth=2;}
static void outer(int s){struct sigaction a={0};a.sa_handler=inner;a.sa_flags=SA_ONSTACK;sigaction(SIGUSR2,&a,0);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR2);depth=depth==2?2:1;}
int main(void){uint8_t mem[65536];ss.ss_sp=mem;ss.ss_size=sizeof mem;sigaltstack(&ss,0);signal(SIGUSR1,outer);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR1);printf("altstack_bytes=65536 nested=2 ymm=32 depth_values=2 valid=%d\n",depth==2);return depth==2?EXIT_SUCCESS:EXIT_FAILURE;}
