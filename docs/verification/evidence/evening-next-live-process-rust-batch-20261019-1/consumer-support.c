typedef void (*process_mckfd_free_fn_t)(struct mckfd *fdp);
typedef int (*process_ref_dec_and_test_fn_t)(void *object,
					     unsigned long ref_offset);
typedef void *(*process_current_resource_set_fn_t)(void);
typedef void (*process_resource_process_action_fn_t)(void *resource_set,
						     void *process);
typedef void (*process_process_action_fn_t)(void *process);
typedef void (*process_resource_set_action_fn_t)(void *resource_set);
typedef void (*process_thread_action_fn_t)(void *thread);
typedef unsigned long (*process_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*process_spin_unlock_fn_t)(unsigned long lock_addr,
					 unsigned long irqstate);
typedef void (*process_free_fn_t)(void *ptr);
int process_release_process_body_result(
	void *proc, unsigned long refcount_offset, unsigned long tids_offset,
	unsigned long main_thread_offset, unsigned long mckfd_offset,
	unsigned long mckfd_lock_offset, unsigned long mckfd_next_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_current_resource_set_fn_t current_resource_set_fn,
	process_resource_process_action_fn_t hash_detach_fn,
	process_process_action_fn_t sibling_detach_fn,
	process_process_action_fn_t profile_fn,
	process_thread_action_fn_t free_thread_pages_fn,
	process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
	process_mckfd_free_fn_t mckfd_free_fn, process_free_fn_t free_fn,
	process_resource_set_action_fn_t final_cleanup_fn);
void *process_current_resource_set_bridge(void);
void process_release_profile_bridge(void *proc_arg);
void process_free_thread_pages_bridge(void *thread);
unsigned long process_spin_lock_bridge(unsigned long lock_addr);
void process_spin_unlock_bridge(unsigned long lock_addr, unsigned long flags);
void process_mckfd_free_bridge(struct mckfd *fdp);
void process_optional_free_bridge(void *ptr);
void process_release_final_cleanup_bridge(void *resource_set_arg);
