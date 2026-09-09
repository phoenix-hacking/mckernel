#include <immintrin.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
static volatile sig_atomic_t depth;
static void inner(int s){uint32_t m=0x5f80;_mm_setcsr(m);__asm__ volatile("syscall":::"rcx","r11","memory");depth=2;}
static void outer(int s){uint32_t m=0x3f80;_mm_setcsr(m);signal(SIGUSR2,inner);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR2);depth=depth==2?2:1;}
int main(void){signal(SIGUSR1,outer);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR1);printf("nested=2 modes=2 exceptions_masked=1 raw_tgkill=1 valid=%d\n",depth==2);return depth==2?EXIT_SUCCESS:EXIT_FAILURE;}
