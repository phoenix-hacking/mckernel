#ifndef _LWK_STDDEF_H
#define _LWK_STDDEF_H

#include <lwk/compiler.h>

#undef NULL
#if defined(__cplusplus)
#define NULL 0
#else
#define NULL ((void *)0)
#endif

#ifdef __KERNEL__
#define false 0
#define true  1
#endif

#undef offsetof
#ifdef __compiler_offsetof
#define offsetof __compiler_offsetof
#else
#define offsetof __builtin_offsetof
#endif

#endif
