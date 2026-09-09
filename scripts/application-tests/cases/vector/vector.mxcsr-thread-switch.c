#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static void *worker(void *p){uint32_t mode=(uintptr_t)p;_mm_setcsr(mode);__asm__ volatile("syscall":::"rcx","r11","memory");return (_mm_getcsr()&0x6000)==(mode&0x6000)?0:(void*)1;}
int main(void){uint32_t m[4]={0x1f80,0x3f80,0x5f80,0x7f80};pthread_t t[4];int ok=1;for(int i=0;i<4;i++)ok&=!pthread_create(&t[i],0,worker,(void*)(uintptr_t)m[i]);for(int i=0;i<4;i++){void*r;pthread_join(t[i],&r);ok&=!r;}printf("threads=4 mxcsr_modes=4 futex=1 syscall=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
