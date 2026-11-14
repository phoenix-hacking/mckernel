#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static void *worker(void *p){__mmask16 k=(__mmask16)(uintptr_t)p;__asm__ volatile("kmovw %0, %%k1\n\tsyscall"::"r"((unsigned)k):"rcx","r11","memory");return 0;}
int main(void){pthread_t t[2];int ok=!pthread_create(&t[0],0,worker,(void*)0x55aa)&&!pthread_create(&t[1],0,worker,(void*)0xaa55);pthread_join(t[0],0);pthread_join(t[1],0);printf("threads=2 masks=8 kmovw=1 raw_syscall=1 futex=1 valid=%d\n",ok);return ok?EXIT_SUCCESS:EXIT_FAILURE;}
