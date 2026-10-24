/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/kernel/mem.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_current_cpu_bridge),int(*)(void)),"currentCPU completecallback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_get_vector_bridge),int(*)(int)),"vector completecallback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_interrupt_cpu_bridge),void(*)(int,int)),"interrupt completevoidcallback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_get_processor_id),int(*)(void)),"existingIHKCPU provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_interrupt_cpu),int(*)(int,int)),"existingIHKinterrupt ignoredreturn ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_get_vector),int(*)(enum ihk_mc_gv_type)),"exactexistingIHKvector enumprototype");
_Static_assert(sizeof(enum ihk_mc_gv_type)==sizeof(int) && sizeof(int)==4,"RustexistingCInt vectorABIwidth");
_Static_assert((unsigned int)(enum ihk_mc_gv_type)-1==~0U,"enum argument preserves all32signedinputbits");
_Static_assert(__builtin_offsetof(ihk_atomic_t,counter)==0 && sizeof(ihk_atomic_t)==4,"controlledcompletion counterABI");
_Static_assert(sizeof(struct tlb_flush_entry)==64 && __alignof__(struct tlb_flush_entry)==64,"actualvectorentry geometry");
