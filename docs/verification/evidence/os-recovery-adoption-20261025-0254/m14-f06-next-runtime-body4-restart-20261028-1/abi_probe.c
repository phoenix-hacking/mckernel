/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <process.h>
#include <memory.h>
#include <errno.h>
#include <registers.h>

typedef int (*copy_from_user_abi)(void *, const void *, size_t);
typedef long (*bridge_abi)(unsigned long, unsigned long, size_t);
extern long arch_ptrace_xstate_copy_from_bridge(unsigned long, unsigned long, size_t);
_Static_assert(__builtin_types_compatible_p(__typeof__(&copy_from_user), copy_from_user_abi),
               "actual Rust user-copy provider has signed int32 result");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_ptrace_xstate_copy_from_bridge), bridge_abi),
               "selected public bridge LP64 ABI");
_Static_assert(sizeof(long) == 8 && sizeof(unsigned long) == 8 && sizeof(size_t) == 8,
               "supported LP64 widths");
_Static_assert(sizeof(int) == 4 && ENOMEM == 12, "original int32 error ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread *)0)->fp_regs), fp_regs_struct *),
               "real target field is borrowed xsave pointer");
_Static_assert(__builtin_offsetof(struct thread, fp_regs) == 4784,
               "supported Thread.fp_regs offset");
_Static_assert(sizeof(struct thread) == 5568 && __alignof__(struct thread) == 64,
               "supported Thread size/alignment");
_Static_assert(sizeof(fp_regs_struct) == 1088 && __alignof__(fp_regs_struct) == 64,
               "real selected regset xstate allocation ABI");
int f06_ptrace_xstate_copy_from_real_header_abi_witness;
