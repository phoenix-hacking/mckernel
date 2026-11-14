/* Pending: compile against ACTUAL production C headers under existing GCC14 profile. */
_Static_assert(__builtin_offsetof(struct process, hash_list) == 0, "process.hash_list");
_Static_assert(__builtin_offsetof(struct process, parent) == 272, "process.parent");
_Static_assert(__builtin_offsetof(struct process, children_lock) == 320, "process.children_lock");
_Static_assert(__builtin_offsetof(struct process, siblings_list) == 384, "process.siblings_list");
_Static_assert(__builtin_offsetof(struct process, pid) == 456, "process.pid");
_Static_assert(__builtin_offsetof(struct resource_set, process_hash) == 24, "resource_set.process_hash");
_Static_assert(__builtin_offsetof(struct process_hash, lock) == 1216, "process_hash.lock");
_Static_assert(sizeof(((struct process_hash *)0)->lock[0]) == 64, "hash lock size");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave) == 64, "writer node size");
_Static_assert(__alignof__(struct mcs_rwlock_node_irqsave) == 64, "writer node alignment");
_Static_assert(HASH_SIZE == 73, "hash bucket count");
