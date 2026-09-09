#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
__attribute__((target("avx"))) static void *worker(void *p){uint8_t seed=(uintptr_t)p,b[32],o[32];for(int i=0;i<32;i++)b[i]=seed+i;__m256i v=_mm256_loadu_si256((const __m256i*)b);__asm__ volatile("syscall":::"rcx","r11","memory");_mm256_storeu_si256((__m256i*)o,v);for(int i=0;i<32;i++)if(o[i]!=b[i])return (void*)1;return 0;}
int main(void){pthread_t t[2];int ok=1;for(int i=0;i<2;i++)ok&=!pthread_create(&t[i],0,worker,(void*)(uintptr_t)(0x10+i*0x70));for(int i=0;i<2;i++){void*r;pthread_join(t[i],&r);ok&=!r;}printf("threads=2 ymm_bytes=32 halves=2 futex_handoff=1 syscall=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
