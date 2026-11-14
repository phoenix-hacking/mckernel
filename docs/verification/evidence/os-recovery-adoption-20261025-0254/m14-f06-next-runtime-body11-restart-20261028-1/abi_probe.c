/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <prctl.h>
#include <ihk/debug.h>
typedef int (*print_abi)(const char *,...);
typedef void (*log_abi)(int,int,unsigned long);
extern void arch_prctl_log_bridge(int,int,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),print_abi),"genuine existing printer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_prctl_log_bridge),log_abi),"original public logger ABI");
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8 && sizeof(void *)==8,"int32/unsigned LP64");
_Static_assert(ARCH_SET_FS==0x1002 && ARCH_GET_FS==0x1003,"actual architecture event values");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual descriptor size/alignment");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0 && __builtin_offsetof(struct ddebug,func)==8 && __builtin_offsetof(struct ddebug,fmt)==16,"actual descriptor pointer fields");
int f06_prctl_logger_real_header_abi_witness;
