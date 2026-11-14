/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#error selected Rust policy required
#endif
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-entries-source-1/candidate/syscall.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&sys_execve),long(*)(int,ihk_mc_user_context_t*)), "execve public ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&sys_execveat),long(*)(int,ihk_mc_user_context_t*)), "execveat public ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_execveat_bridge),int(*)(void*,int,const char*,char**,char**,int)), "existing provider ABI");
_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(void*)==8, "x86_64 widths");
_Static_assert((char)0xff<0, "original filename char promotion");
