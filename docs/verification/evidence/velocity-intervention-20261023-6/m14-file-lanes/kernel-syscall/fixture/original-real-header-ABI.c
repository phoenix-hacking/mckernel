#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/preimage/syscall.c"
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(unsigned long)==8,"supported LP64 scalar ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_signalfd_create_bridge),long(*)(int,int)),"actual complete callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&do_syscall),long(*)(struct syscall_request*,int)),"existing synchronous request ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_get_processor_id),int(*)(void)),"existing currentCPU ABI");
_Static_assert(sizeof(struct syscall_request)==72 && _Alignof(struct syscall_request)==8,"reprC request extent/alignment");
_Static_assert(__builtin_offsetof(struct syscall_request,rtid)==0 && __builtin_offsetof(struct syscall_request,ttid)==4 && __builtin_offsetof(struct syscall_request,valid)==8 && __builtin_offsetof(struct syscall_request,number)==16 && __builtin_offsetof(struct syscall_request,args)==24,"reprC request offsets");
struct F03_DMA_REQUEST_WITNESS {struct syscall_request request IHK_DMA_ALIGN;};
_Static_assert(_Alignof(struct F03_DMA_REQUEST_WITNESS)==8 && sizeof(struct F03_DMA_REQUEST_WITNESS)==72,"supported actual x86 emptyDMAalignment macro");
