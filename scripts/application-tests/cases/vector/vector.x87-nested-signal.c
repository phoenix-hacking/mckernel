#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <sys/syscall.h>
static volatile sig_atomic_t depth;
static void inner(int s){long double x[8]={1,2,3,4,5,6,7,8};uint8_t a[512] __attribute__((aligned(16)));for(int i=0;i<8;i++)__asm__ volatile("fldt %0"::"m"(x[i]));__asm__ volatile("fxsave64 %0":"=m"(a));depth=2;}
static void outer(int s){signal(SIGUSR2,inner);depth=1;syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR2);}
static int run(void){signal(SIGUSR1,outer);syscall(SYS_tgkill,getpid(),syscall(SYS_gettid),SIGUSR1);return depth==2;}
int main(void){int valid=run();printf("nested_handlers=2 x87_entries=8 fxsave64=1 raw_tgkill=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
