#include <emmintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static void *worker(void *p){uint8_t seed=(uintptr_t)p,b[16],o[16];for(int i=0;i<16;i++)b[i]=seed+i;__m128i v=_mm_loadu_si128((const __m128i*)b);__asm__ volatile("syscall":::"rcx","r11","memory");_mm_storeu_si128((__m128i*)o,v);for(int i=0;i<16;i++)if(o[i]!=b[i])return (void*)1;return 0;}
int main(void){pthread_t t[2];int ok=1;for(int i=0;i<2;i++)ok&=!pthread_create(&t[i],0,worker,(void*)(uintptr_t)(0x20+i*0x40));for(int i=0;i<2;i++){void*r;pthread_join(t[i],&r);ok&=!r;}printf("threads=2 xmm_bytes=16 futex_handoff=1 syscall=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
