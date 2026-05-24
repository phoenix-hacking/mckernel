/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_PROCESS_HELPERS_H
#define MCKERNEL_PROCESS_HELPERS_H

#include <ihk/types.h>

struct list_head;
struct mckfd;
struct memobj;
struct process_vm;
struct rb_root;
struct vm_range;

typedef struct vm_range *(*process_add_range_alloc_fn_t)(unsigned long size);
typedef void (*process_add_range_free_fn_t)(struct vm_range *range);
typedef int (*process_add_range_insert_fn_t)(struct process_vm *vm,
					     struct vm_range *range);
typedef int (*process_add_range_update_fn_t)(struct process_vm *vm,
					     struct vm_range *range,
					     unsigned long phys,
					     unsigned long attr);
typedef void (*process_add_range_remove_fn_t)(struct process_vm *vm,
					      unsigned long start,
					      unsigned long end);
typedef void (*process_add_range_mark_xpmem_fn_t)(struct vm_range *range);
typedef void (*process_add_range_memclear_fn_t)(unsigned long phys,
						unsigned long bytes);
typedef void (*process_add_range_log_fn_t)(int event, int rc,
					   unsigned long start,
					   unsigned long end);
typedef void (*process_vm_range_insert_log_fn_t)(int event,
						 struct process_vm *vm,
						 struct vm_range *newrange,
						 struct vm_range *range);
typedef void (*process_vm_range_insert_dump_fn_t)(struct process_vm *vm);

#define PROCESS_ADD_RANGE_MAP_SKIP 0
#define PROCESS_ADD_RANGE_MAP_UPDATE 1
#define PROCESS_ADD_RANGE_MAP_MARK_XPMEM 2
#define PROCESS_ADD_RANGE_MAP_DEMAND 3

#define PROCESS_ADD_RANGE_LOG_ALLOC_FAILED 1
#define PROCESS_ADD_RANGE_LOG_INSERT_FAILED 2
#define PROCESS_ADD_RANGE_LOG_PREP_FAILED 3
#define PROCESS_ADD_RANGE_LOG_DEMAND 4

#define PROCESS_VM_RANGE_INSERT_LOG_OVERLAP 1
#define PROCESS_VM_RANGE_INSERT_LOG_SUCCESS 2

int process_split_pgshift_result(int pgshift, uintptr_t addr);
int process_add_range_bounds_result(unsigned long user_start,
				    unsigned long user_end,
				    unsigned long start,
				    unsigned long end);
int process_add_range_init_result(struct vm_range *range, unsigned long start,
				  unsigned long end, unsigned long flag,
				  void *memobj, off_t offset, int pgshift,
				  void *private_data);
int process_add_range_mapping_result(unsigned long phys, unsigned long flag,
				     unsigned long range_flag,
				     unsigned long *attrp,
				     int *memclearp);
int process_add_range_orchestrate_result(
	struct process_vm *vm, unsigned long range_size, unsigned long start,
	unsigned long end, unsigned long phys, unsigned long flag,
	struct memobj *memobj, off_t offset, int pgshift, void *private_data,
	struct vm_range **rp, process_add_range_alloc_fn_t alloc_fn,
	process_add_range_free_fn_t free_fn,
	process_add_range_insert_fn_t insert_fn,
	process_add_range_update_fn_t update_fn,
	process_add_range_remove_fn_t remove_fn,
	process_add_range_mark_xpmem_fn_t mark_xpmem_fn,
	process_add_range_memclear_fn_t memclear_fn,
	process_add_range_log_fn_t log_fn);
int process_vm_range_insert_result(struct rb_root *root,
				   struct vm_range *newrange,
				   struct process_vm *vm,
				   process_vm_range_insert_log_fn_t log_fn,
				   process_vm_range_insert_dump_fn_t dump_fn);
int process_extend_up_result(unsigned long current_end,
			     unsigned long user_end, int has_next,
			     unsigned long next_start,
			     unsigned long newend);
unsigned long process_change_prot_newflag_result(unsigned long oldflag,
						 unsigned long protflag);
void process_attr_delta_result(unsigned long oldattr, unsigned long newattr,
			       unsigned long *clrattrp,
			       unsigned long *setattrp);
unsigned long process_private_file_setattr_result(int has_memobj,
						  unsigned long range_flags,
						  unsigned int memobj_flags,
						  unsigned long setattr);
int process_remove_region_alignment_result(unsigned long start,
					   unsigned long end);
int process_access_initial_result(int has_range, unsigned long range_start,
				  unsigned long addr);
int process_access_adjacent_result(unsigned long range_end, int has_next,
				   unsigned long next_start);
int process_access_permission_result(int verify_type, unsigned long flags);
int process_range_cache_hit_result(unsigned long cache_start,
				   unsigned long cache_end,
				   unsigned long start,
				   unsigned long end);
int process_lookup_range_relation_result(unsigned long start,
					 unsigned long end,
					 unsigned long range_start,
					 unsigned long range_end);
int process_range_cache_replace_result(struct vm_range **cache, int count,
				       struct vm_range *from,
				       struct vm_range *to);
int process_range_cache_store_result(struct vm_range **cache, int count,
				     int *indexp, struct vm_range *match);
int process_range_end_commit_result(struct vm_range *range, uintptr_t newend);
int process_range_flag_commit_result(struct vm_range *range,
				     unsigned long newflag);
int process_range_stack_start_commit_result(struct vm_range *range,
					    uintptr_t fault_addr,
					    int pgshift);
void process_remove_range_step_result(unsigned long range_start,
				      unsigned long range_end,
				      unsigned long remove_start,
				      unsigned long remove_end,
				      unsigned long range_flags,
				      unsigned long private_data,
				      int *split_startp, int *split_endp,
				      int *ro_freedp, int *xpmem_removep);
int process_split_range_init_result(const struct vm_range *low,
				    struct vm_range *high, uintptr_t addr);
void process_split_range_commit_result(struct vm_range *low, uintptr_t addr);
int process_join_range_prepare_result(struct vm_range *surviving,
				      const struct vm_range *merging);
int process_ref_release_should_destroy_result(int dec_and_test);
int process_release_address_space_should_destroy_result(int dec_and_test);
int process_release_address_space_should_run_free_cb_result(
	unsigned long free_cb_addr);
int process_create_cpu_allowed_result(int cpu, int num_processors);
int process_create_use_default_cpu_set_result(int cpu_set_empty);
int process_address_space_pid_detach_result(int *pids, int nslots, int pid);
int process_clone_shares_vm_result(int clone_flags);
int process_clone_shares_sighand_result(int clone_flags);
int process_mckfd_should_dup_result(unsigned long dup_cb_addr);
int process_clone_copy_vm_thread_state_result(
	void *dst_vm, const void *src_vm, unsigned long vdso_offset,
	unsigned long vvar_offset, void *dst_thread, const void *src_thread,
	unsigned long sigstack_offset, size_t sigstack_size);
int process_tid_index_for_thread_result(const void *tids, int nr_tids,
					unsigned long entry_stride,
					unsigned long thread_offset,
					unsigned long thread_addr);
int process_tid_index_found_result(int index);
int process_tid_release_slot_result(void *tids, int index,
				    unsigned long entry_stride,
				    unsigned long thread_offset);
int process_tid_replace_slot_result(void *tids, int index,
				    unsigned long entry_stride,
				    unsigned long tid_offset,
				    unsigned long thread_offset,
				    int new_tid);
int process_sigpending_cleanup_needed_result(int list_empty);
void *process_sigpending_pop_front_result(struct list_head *head,
					  unsigned long list_offset);
int process_list_is_linked_result(const struct list_head *entry);
void process_list_detach_result(struct list_head *entry);
int process_list_detach_counted_result(struct list_head *entry,
				       size_t *lenp);
void process_list_add_tail_result(struct list_head *entry,
				  struct list_head *head);
int process_list_add_tail_counted_result(struct list_head *entry,
					 struct list_head *head,
					 size_t *lenp);
int process_list_move_tail_result(struct list_head *entry,
				  struct list_head *head);
int process_list_del_init_result(struct list_head *entry);
int process_child_reparent_result(void *child,
				  unsigned long ppid_parent_offset,
				  unsigned long parent_offset,
				  void *new_parent,
				  struct list_head *entry,
				  struct list_head *head,
				  int update_parent);
int process_thread_report_attach_result(void *thread,
					unsigned long termsig_offset,
					int update_termsig, int termsig,
					unsigned long report_proc_offset,
					void *report_proc,
					struct list_head *entry,
					struct list_head *head);
int process_thread_report_detach_result(void *thread,
					unsigned long report_proc_offset,
					void *report_proc,
					struct list_head *entry);
int process_ptrace_main_detach_reparent_result(void *process,
					      unsigned long parent_offset,
					      void *parent,
					      struct list_head *ptraced_entry,
					      struct list_head *sibling_entry,
					      struct list_head *children_head);
int process_ptrace_main_attach_reparent_result(void *process,
					      unsigned long parent_offset,
					      void *parent,
					      struct list_head *sibling_entry,
					      struct list_head *children_head);
int process_thread_termsig_clear_result(void *thread,
					unsigned long termsig_offset,
					int clear_termsig);
void *process_thread_ptrace_cleanup_result(void *thread,
					   unsigned long ptrace_offset,
					   unsigned long saved_valid_offset,
					   unsigned long debugreg_offset);
int process_thread_ptrace_saved_context_clear_result(
	void *thread, unsigned long saved_valid_offset);
int process_thread_ptrace_trace_syscall_update_result(
	void *thread, unsigned long ptrace_offset, int trace_syscall);
void *process_thread_ptrace_pending_signal_take_result(
	void *thread, unsigned long sendsig_offset, unsigned long recvsig_offset,
	int source);
int process_thread_signal_flags_reap_result(void *thread,
					    unsigned long signal_flags_offset,
					    int options, int clear_mask);
int process_wait_exit_status_reap_result(void *object,
					 unsigned long exit_status_offset,
					 int options);
int process_optional_ptr_should_free_result(unsigned long ptr_addr);
int process_hold_thread_warn_exited_result(int status);
int process_sigcommon_release_should_destroy_result(int dec_and_test);
int process_destroy_thread_tid_action_result(int has_tids, int is_main_thread,
					    int uti_state);
int process_thread_should_free_pages_result(int is_main_thread);
int process_release_vm_should_run_free_cb_result(unsigned long free_cb_addr);
int process_release_mckfd_should_close_result(unsigned long close_cb_addr);
int process_mckfd_push_head_result(struct mckfd **headp, struct mckfd *entry);
struct mckfd *process_mckfd_pop_head_result(struct mckfd **headp);

#endif /* MCKERNEL_PROCESS_HELPERS_H */
