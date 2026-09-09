#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
__attribute__((target("avx512f"))) static void *worker(void *p){uint32_t b[16],o[16];for(int i=0;i<16;i++)b[i]=(uint32_t)(uintptr_t)p+i;__m512i v=_mm512_loadu_si512(b);__asm__ volatile("syscall":::"rcx","r11","memory");_mm512_storeu_si512(o,v);for(int i=0;i<16;i++)if(o[i]!=b[i])return (void*)1;return 0;}
int main(void){pthread_t t[2];int ok=!pthread_create(&t[0],0,worker,(void*)0x100)&&!pthread_create(&t[1],0,worker,(void*)0x200);void*r=0;pthread_join(t[0],&r);ok&=!r;pthread_join(t[1],&r);ok&=!r;printf("threads=2 zmm_registers=32 lanes=16 raw_syscall=1 one_cpu=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
