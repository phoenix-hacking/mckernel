/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <kmsg.h>
#include "selected-body.inc"
typedef void (*M14LogFn)(int,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_cpu_ulong_log_bridge),M14LogFn),"actual two-argument callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int(*)(const char*,...)),"existing variadic kprintf ABI");
_Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"real x86_64 int long pointer widths");
M14LogFn M14_CPU_LOG_CONSUMER=x86_cpu_ulong_log_bridge;
const unsigned long M14_CPU_LOG_ABI[4]={sizeof(int),sizeof(unsigned long),sizeof(void*),sizeof(M14LogFn)};
