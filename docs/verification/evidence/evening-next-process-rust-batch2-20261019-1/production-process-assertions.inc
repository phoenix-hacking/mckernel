/* UNRUN: include after ACTUAL production process/cls/list/lock headers in GCC14 profile. */
#ifdef ENABLE_TOFU
_Static_assert(__builtin_offsetof(struct cpu_local_var, resource_set) == 24368, "TOFU cpu.resource_set");
#else
_Static_assert(__builtin_offsetof(struct cpu_local_var, resource_set) == 7912, "cpu.resource_set");
#endif
_Static_assert(__builtin_offsetof(struct resource_set, pid1) == 320, "resource_set.pid1");
_Static_assert(__builtin_offsetof(struct process, children_list) == 288, "process.children_list");
_Static_assert(__builtin_offsetof(struct process, children_lock) == 320, "process.children_lock");
_Static_assert(sizeof(((struct cpu_local_var *)0)->resource_set) == 8, "resource_set pointer size");
_Static_assert(sizeof(((struct resource_set *)0)->pid1) == 8, "pid1 pointer size");
_Static_assert(sizeof(struct list_head) == 16, "list head size");
_Static_assert(__builtin_offsetof(struct list_head, next) == 0, "list next offset");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave) == 64, "reader node size");
_Static_assert(__alignof__(struct mcs_rwlock_node_irqsave) == 64, "reader node alignment");
