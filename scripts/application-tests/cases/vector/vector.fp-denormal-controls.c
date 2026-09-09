#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static int run(void){uint32_t old=_mm_getcsr();float a=0x1p-149f,b=2.0f;_mm_setcsr(old&~0x8040u);volatile float off=a*b;_mm_setcsr((old&~0x8040u)|0x8040u);volatile float on=a*b;_mm_setcsr(old);return off!=on || off==0.0f;}
int main(void){int valid=run();printf("inputs=2 ftz_daz=2 mulss=1 subnormal=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
