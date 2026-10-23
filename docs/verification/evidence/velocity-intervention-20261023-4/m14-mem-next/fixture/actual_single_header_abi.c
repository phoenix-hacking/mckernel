/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <kmsg.h>
#include <kmalloc.h>
#include <string.h>
#include <ihk/cpu.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <ihk/page_alloc.h>
#include <registers.h>
#ifdef ATTACHED_MIC
#include <sysdeps/mic/mic/micconst.h>
#include <sysdeps/mic/mic/micsboxdefine.h>
#endif
#include <cls.h>
#include <page.h>
#include <kref.h>
#include <bitops.h>
#include <cpulocal.h>
#include <init.h>
#include <cas.h>
#include <rusage_private.h>
#include <syscall.h>
#include <profile.h>
#include <process.h>
#include <limits.h>
#include <sysfs.h>
#include <ihk/debug.h>
#include <llist.h>
#include <bootparam.h>
#include <memobj.h>

//#define DEBUG_PRINT_MEM

#ifdef DEBUG_PRINT_MEM
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_cpumask),void(*)(struct process_vm*,unsigned long,int)),"actual single-entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual array-entry ABI");
_Static_assert(sizeof(unsigned long)==8 && _Alignof(unsigned long)==8 && sizeof(int)==4,"actual x86_64 scalar ABI");
const unsigned long M14_C_SINGLE_ABI[5]={
 sizeof(int),sizeof(unsigned long),_Alignof(unsigned long),sizeof(struct process_vm*),sizeof(unsigned long*)
};
