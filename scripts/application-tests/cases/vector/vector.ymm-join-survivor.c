#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
__attribute__((target("avx"))) static void *survivor(void *p){uint8_t b[32],o[32];for(int i=0;i<32;i++)b[i]=(uint8_t)(0x40+i);__m256i v=_mm256_loadu_si256((const __m256i*)b);__asm__ volatile("syscall":::"rcx","r11","memory");_mm256_storeu_si256((__m256i*)o,v);for(int i=0;i<32;i++)if(o[i]!=b[i])return (void*)1;return 0;}
static void *shortlived(void*p){__asm__ volatile("syscall":::"rcx","r11","memory");return 0;}
int main(void){pthread_t a,b;int ok=!pthread_create(&a,0,survivor,0)&&!pthread_create(&b,0,shortlived,0);void*r=0;if(ok){pthread_join(b,0);pthread_join(a,&r);ok=!r;}printf("survivor_ymm=32 coordinator_join=1 futex=1 syscall=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
