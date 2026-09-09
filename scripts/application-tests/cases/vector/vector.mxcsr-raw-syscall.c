#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((target("sse2"))) static int run(void){ uint32_t modes[4]={0x1f80,0x3f80,0x5f80,0x7f80},old=_mm_getcsr(),now; for(int i=0;i<4;i++){_mm_setcsr(modes[i]); __asm__ volatile("syscall" ::: "rcx","r11","memory"); now=_mm_getcsr(); if((now&0x6000)!=(modes[i]&0x6000))return 0;} _mm_setcsr(old); return 1; }
int main(void){int valid=run();printf("modes=4 exceptions_masked=1 raw_syscall=1 sse2=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
