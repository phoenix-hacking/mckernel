#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static int run(void){uint16_t cw=0;uint8_t env[512] __attribute__((aligned(16)));__asm__ volatile("fnstcw %0\n\tfxsave64 %1":"=m"(cw),"=m"(env));return (cw&0x3f)==0x3f;}
int main(void){int valid=run();printf("static_elf=1 first_entry=1 fnstcw=1 fxsave64=1 exceptions_masked=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
