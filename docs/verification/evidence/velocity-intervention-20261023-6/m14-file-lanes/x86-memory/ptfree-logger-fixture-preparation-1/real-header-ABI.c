/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/ptfree-logger-fixture-preparation-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_free_pages_bridge),x86_pt_free_pages_fn_t),"exact existing PTfree callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void(*)(void*,int,int,char*,int)),"actual tracked allocator ABI");
_Static_assert(sizeof(int)==4 && sizeof(void*)==8 && IHK_MC_PG_KERNEL==0,"actual page flag and argument widths");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(sizeof(x86_pt_free_pages_line)==4 && sizeof(x86_pt_free_pages_flag)==4,"immutable tracing integer ABI");
_Static_assert(sizeof(x86_pt_free_pages_file)>1,"actual C compilation-unit path bytes");
#endif

_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_effect_log_bridge),x86_clear_effect_log_fn_t),"actual complete effect logger ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_log_bridge),x86_clear_range_log_fn_t),"actual complete range logger ABI");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual descriptor ABI");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0 && __builtin_offsetof(struct ddebug,func)==8 && __builtin_offsetof(struct ddebug,fmt)==16,"actual debug pointer fields");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"retained immutable effect identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"retained immutable range identity");
#endif

