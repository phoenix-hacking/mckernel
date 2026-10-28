/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <kmalloc.h>
#include <memory.h>
#include <ihk/mm.h>
#include <errno.h>
typedef void *(*allocate_abi)(int,unsigned long,char *,int);
typedef void (*free_abi)(void *,char *,int);
typedef int (*copy_abi)(void *,const void *,size_t);
_Static_assert(__builtin_types_compatible_p(__typeof__(&kmalloc_tracked),allocate_abi),"real tracked alloc ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kfree_tracked),free_abi),"real tracked free ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&copy_from_user),copy_abi),"real copy ABI");
_Static_assert(sizeof(long)==8 && sizeof(unsigned long)==8 && sizeof(size_t)==8,"LP64 widths");
_Static_assert(sizeof(int)==4 && sizeof(unsigned int)==4,"int32 widths");
_Static_assert(IHK_MC_AP_NOWAIT==2 && ENOMEM==12 && EFAULT==14,"real flags and errno");
int f06_signal_restore_fp_real_header_abi_witness;
