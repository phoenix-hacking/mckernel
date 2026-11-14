#ifndef _ASM_X86_STRING_H
#define _ASM_X86_STRING_H

#define ARCH_FAST_MEMCPY

void *__inline_memcpy(void *to, const void *from, size_t n);

#define ARCH_FAST_MEMSET

void *__inline_memset(void *s, unsigned long c, size_t count);

#endif
