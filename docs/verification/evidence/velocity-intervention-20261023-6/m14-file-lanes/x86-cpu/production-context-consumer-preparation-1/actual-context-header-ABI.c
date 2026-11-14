/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <ihk/debug.h>
#include "selected-body.inc"
typedef void(*M14ContextLogFn)(int,unsigned long,unsigned long,unsigned long,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_context_line_log_bridge),M14ContextLogFn),"exact five-argument context callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int(*)(const char*,...)),"existing ordinary variadic provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__kprintf),int(*)(const char*,...)),"existing unlocked variadic provider ABI");
_Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"actual int/long/pointer widths");
M14ContextLogFn M14_CONTEXT_LOG_CONSUMER=x86_context_line_log_bridge;

/* Exact unchanged C outer-lock provider signatures from current cpu.c. */
extern unsigned long x86_kprintf_lock_bridge(void);
extern void x86_kprintf_unlock_bridge(unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_kprintf_lock_bridge),unsigned long(*)(void)),"outer lock ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_kprintf_unlock_bridge),void(*)(unsigned long)),"outer unlock ABI");
