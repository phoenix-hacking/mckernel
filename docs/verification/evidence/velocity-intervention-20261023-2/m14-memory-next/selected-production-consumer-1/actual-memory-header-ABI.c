/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual complete canonical memory.c and real headers. */
#include "/home/holden/mckernel/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_public_body),int(*)(void*,struct process_vm*,unsigned long,unsigned long,int,struct memobj*)),"six-input Rust entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_set_range_clear_bridge),int(*)(void*,void*,unsigned long,unsigned long,int,void*)),"six-input actual set-range adapter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_clear_range),int(*)(page_table_t,struct process_vm*,void*,void*)),"public clear ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_free_range),int(*)(page_table_t,struct process_vm*,void*,void*,struct memobj*)),"public free ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual C remote-flush header ABI");
_Static_assert(__builtin_types_compatible_p(x86_clear_remote_flush_fn_t,void(*)(void*,unsigned long*,int,int)),"actual erased Rust flush callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_top_log_bridge),void(*)(int,void*,unsigned long,unsigned long,int)),"actual C top-log provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l4_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"actual C walker provider ABI");
