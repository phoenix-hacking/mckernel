/* Assertions only; actual TU already includes its production headers. */
_Static_assert(sizeof(unsigned long)==8,"LP64");
_Static_assert(sizeof(struct rb_node)==24,"rb node ABI");
_Static_assert(sizeof(struct vm_range_numa_policy)==80,"NUMA policy ABI");
_Static_assert(__builtin_offsetof(struct vm_range_numa_policy,policy_rb_node)==0,"policy node offset");
_Static_assert(__builtin_offsetof(struct vm_range_numa_policy,start)==24,"policy start offset");
_Static_assert(__builtin_offsetof(struct vm_range_numa_policy,numa_mask)==40,"policy mask offset");
_Static_assert(__builtin_offsetof(struct process_vm,vm_range_numa_policy_tree)==248,"policy root offset");
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
typedef int (*insert_signature_t)(struct process_vm *,struct vm_range_numa_policy *,
 void (*)(struct rb_node *,struct rb_node *,struct rb_node **),
 void (*)(struct rb_node *,struct rb_root *),
 void (*)(struct process_vm *,struct vm_range_numa_policy *,struct vm_range_numa_policy *));
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_vm_policy_insert_body_result),insert_signature_t),"Rust insertion callback ABI");
#endif
