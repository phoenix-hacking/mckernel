/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Fragment only: include the actual complete candidate C TU using accepted
 * PUBLIC flags. No new driver, argv or executable cohort.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-pt-free-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_free_pages_bridge),x86_pt_free_pages_fn_t),"exact existing PTfree callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void(*)(void*,int,int,char*,int)),"actual tracked allocator ABI");
_Static_assert(sizeof(int)==4 && sizeof(void*)==8 && IHK_MC_PG_KERNEL==0,"actual page flag and argument widths");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(sizeof(x86_pt_free_pages_line)==4 && sizeof(x86_pt_free_pages_flag)==4,"immutable tracing integer ABI");
_Static_assert(sizeof(x86_pt_free_pages_file)>1,"actual C compilation-unit path bytes");
#endif
