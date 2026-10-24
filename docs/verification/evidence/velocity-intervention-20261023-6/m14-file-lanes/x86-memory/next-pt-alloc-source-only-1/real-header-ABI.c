/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-pt-alloc-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_alloc_pages_bridge),x86_pt_alloc_pages_fn_t),"existing complete allocation callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),void*(*)(int,int,ihk_mc_ap_flag,int,int,uintptr_t,char*,int)),"real tracked allocator ABI");
_Static_assert(__builtin_types_compatible_p(ihk_mc_ap_flag,unsigned long) && sizeof(ihk_mc_ap_flag)==8,"C signed32 to unsigned64 conversion");
_Static_assert(PAGE_P2ALIGN==0 && IHK_MC_PG_KERNEL==0 && sizeof(int)==4 && sizeof(uintptr_t)==8,"actual geometry/constants");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(sizeof(x86_pt_alloc_pages_line)==4 && sizeof(x86_pt_alloc_pages_p2align)==4 && sizeof(x86_pt_alloc_pages_is_user)==4,"metadata ABI");
#endif
