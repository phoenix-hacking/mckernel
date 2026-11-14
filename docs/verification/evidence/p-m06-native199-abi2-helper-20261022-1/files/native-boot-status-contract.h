/* Explicit full-readiness callback ABI2 profile; existing ABI1 stays default. */
#ifndef NATIVE_BOOT_CALLBACK_ABI2
#define NATIVE_BOOT_CALLBACK_ABI2 0
#endif
#if NATIVE_BOOT_CALLBACK_ABI2 != 0 && NATIVE_BOOT_CALLBACK_ABI2 != 1
#error NATIVE_BOOT_CALLBACK_ABI2 must be boolean
#endif
