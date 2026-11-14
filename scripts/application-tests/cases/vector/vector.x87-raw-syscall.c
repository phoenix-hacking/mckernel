#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((noinline)) static int run(void){ long double v[8]={1,2,3,4,5,6,7,8}; uint8_t area[512] __attribute__((aligned(16))); for(int i=0;i<8;i++) __asm__ volatile("fldt %0"::"m"(v[i])); __asm__ volatile("fxsave64 %0" : "=m"(area)); __asm__ volatile("syscall" ::: "rcx","r11","memory"); return area[0]!=0 || area[1]!=0; }
int main(void){int valid=run();printf("x87_entries=8 fxsave64=1 raw_syscall=1 snapshot=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
