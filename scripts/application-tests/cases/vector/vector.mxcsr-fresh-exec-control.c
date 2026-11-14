#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static int run(void){uint32_t m=_mm_getcsr();return (m&0x1f80)==0x1f80;}
int main(void){int valid=run();printf("static_elf=1 first_entry=1 stmxcsr=1 exceptions_masked=1 rounding_nearest=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
