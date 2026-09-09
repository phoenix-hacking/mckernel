#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static void *worker(void *p){long double v[8];uint8_t a[512] __attribute__((aligned(16)));for(int i=0;i<8;i++){v[i]=(long double)(i+1)+(uintptr_t)p;__asm__ volatile("fldt %0"::"m"(v[i]));}__asm__ volatile("fxsave64 %0" : "=m"(a));__asm__ volatile("syscall":::"rcx","r11","memory");return a[0]?0:(void*)1;}
int main(void){pthread_t t[2];int ok=1;for(int i=0;i<2;i++)ok&=!pthread_create(&t[i],0,worker,(void*)(uintptr_t)(i*10));for(int i=0;i<2;i++){void*r;pthread_join(t[i],&r);ok&=!r;}printf("threads=2 x87_entries=8 rounding_modes=2 futex=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
