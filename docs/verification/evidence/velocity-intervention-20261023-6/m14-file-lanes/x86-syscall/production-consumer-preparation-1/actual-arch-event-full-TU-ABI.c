/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "source/arch/x86_64/kernel/syscall.c"
_Static_assert(sizeof(long)==8 && sizeof(int)==4 && sizeof(void *)==8,"x86LP64");
_Static_assert(sizeof(ihk_mc_user_context_t)==224,"actual context size");
_Static_assert(__builtin_offsetof(ihk_mc_user_context_t,gpr.rax)==136,"actual RAX offset");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_ptrace_syscall_event),long (*)(struct thread *,ihk_mc_user_context_t *,long)),"actual public declaration ABI");
