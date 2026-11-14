/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual complete canonical memory.c and real headers. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-l1-source-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_public_body),int(*)(void*,struct process_vm*,unsigned long,unsigned long,int,struct memobj*)),"six-input Rust entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_set_range_clear_bridge),int(*)(void*,void*,unsigned long,unsigned long,int,void*)),"six-input actual set-range adapter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_clear_range),int(*)(page_table_t,struct process_vm*,void*,void*)),"public clear ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_free_range),int(*)(page_table_t,struct process_vm*,void*,void*,struct memobj*)),"public free ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual C remote-flush header ABI");
_Static_assert(__builtin_types_compatible_p(x86_clear_remote_flush_fn_t,void(*)(void*,unsigned long*,int,int)),"actual erased Rust flush callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_top_log_bridge),void(*)(int,void*,unsigned long,unsigned long,int)),"actual Rust top-log export ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l4_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"actual C walker provider ABI");

_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l4_callback),int(*const)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"exact immutable retained callback ABI");

_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_l4_body),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"exact complete L4 Rust callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l3_callback),int(*const)(void*,unsigned long,unsigned long,unsigned long,void*)),"exact retained L3 callback ABI");

/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l3),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L3 callback ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_child_walk),x86_clear_child_walk_fn_t const),"x86_clear_l3_child_walk ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"x86_clear_l3_memobj_flush ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"x86_clear_l3_rss_sub ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"x86_clear_l3_memobj_rss_sub ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"x86_clear_l3_range_log ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"x86_clear_l3_effect_log ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_use_1gb_page),const int *const),"live use1GB borrowed address ABI");
#endif

_Static_assert(PFL3_SIZE == ((pte_t)0x80),"exact C PFL3_SIZE1GB bit matches Rust");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"PFL3_SIZE actual x86 ABI width");

/* Additive full L2/L1 and retained L1 walker identity real-header witnesses. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l2),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L2 callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l1),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L1 callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"immutable L1 walker identity ABI");
_Static_assert(PTL2_SHIFT==21 && PTL2_SIZE==(1UL<<21) && PFL2_SIZE==((pte_t)0x80),"L2 geometry");
_Static_assert(PTL1_SHIFT==12 && PTL1_SIZE==(1UL<<12),"L1 geometry");
