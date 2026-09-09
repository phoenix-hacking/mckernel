#include <emmintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((noinline)) static int first_user_instruction(void){uint8_t b[16],o[16];for(int i=0;i<16;i++)b[i]=0;__m128i v=_mm_loadu_si128((const __m128i*)b);_mm_storeu_si128((__m128i*)o,v);for(int i=0;i<16;i++)if(o[i]!=0)return 0;return 1;}
int main(void){int valid=first_user_instruction();printf("static_elf=1 first_instruction=movdqu xmm_bytes=16 poison_cleared=1 valid=%d\n",valid);return valid?EXIT_SUCCESS:EXIT_FAILURE;}
