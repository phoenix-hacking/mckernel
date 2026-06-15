/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_PROCESS_HELPERS_H
#define MCKERNEL_PROCESS_HELPERS_H

#include <ihk/types.h>

struct list_head;
struct mckfd;
struct memobj;
struct program_load_desc;
struct process_vm;
struct process;
struct rb_root;
struct thread;
struct vm_range;

#define PROCESS_CREATE_CPU_LOG_INVALID 1
#define PROCESS_CREATE_CPU_LOG_REQUESTED 2
#define PROCESS_PTRACE_TRACEME_LOG_ENTER 1
#define PROCESS_PTRACE_TRACEME_LOG_PARENT 2
#define PROCESS_PTRACE_TRACEME_LOG_RETURN 3

struct process_init_state_offsets {
	unsigned long pid_offset;
	unsigned long status_offset;
	unsigned long parent_offset;
	unsigned long ppid_parent_offset;
	unsigned long pgid_offset;
	unsigned long ruid_offset;
	unsigned long euid_offset;
	unsigned long suid_offset;
	unsigned long fsuid_offset;
	unsigned long rgid_offset;
	unsigned long egid_offset;
	unsigned long sgid_offset;
	unsigned long fsgid_offset;
	unsigned long mpol_flags_offset;
	unsigned long mpol_threshold_offset;
	unsigned long thp_disable_offset;
	unsigned long rlimit_offset;
	unsigned long rlimit_size;
	unsigned long cpu_set_offset;
	unsigned long cpu_set_size;
	unsigned long enable_uti_offset;
};

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
typedef void (*process_range_public_log_fn_t)(int event,
					      struct process_vm *vm,
					      struct vm_range *range,
					      unsigned long start,
					      unsigned long end,
					      int error);
typedef void (*process_range_memobj_ref_fn_t)(struct memobj *memobj);
typedef int (*process_split_range_insert_fn_t)(struct process_vm *vm,
					       struct vm_range *range);
typedef struct vm_range *(*process_split_range_alloc_fn_t)(
	unsigned long size, unsigned long flags);
typedef void (*process_split_range_alloc_log_fn_t)(
	struct process_vm *vm, struct vm_range *range,
	unsigned long addr, void *splitp);
typedef int (*process_split_range_pt_split_fn_t)(void *page_table,
						 struct process_vm *vm,
						 struct vm_range *range,
						 void *addr);
typedef void (*process_split_range_pt_log_fn_t)(int error);
typedef void (*process_split_range_publish_log_fn_t)(int error);
typedef int (*process_split_shm_lookup_page_fn_t)(struct memobj *obj,
						  long off, int p2align,
						  uintptr_t *physp,
						  unsigned long *pflag);
typedef void *(*process_split_shm_phys_to_page_fn_t)(unsigned long phys);
typedef int (*process_split_shm_update_page_fn_t)(struct memobj *obj,
						  void *page_table,
						  void *page, void *vaddr);
typedef void (*process_split_shm_log_fn_t)(int event, int error);
typedef void (*process_join_range_free_fn_t)(struct vm_range *range);
typedef int (*process_join_range_tofu_fn_t)(struct process_vm *vm,
					    struct vm_range *surviving,
					    struct vm_range *merging);
typedef int (*process_free_range_page_size_fn_t)(size_t current,
						 size_t *nextp);
typedef void *(*process_free_range_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*process_free_range_pages_fn_t)(void *addr,
					      unsigned long pages);
typedef int (*process_free_range_clear_main_fn_t)(struct process_vm *vm,
						  unsigned long start,
						  unsigned long end);
typedef void (*process_free_range_free_fn_t)(struct vm_range *range);
typedef int (*process_free_range_pt_free_fn_t)(void *page_table,
					       struct process_vm *vm,
					       unsigned long start,
					       unsigned long end,
					       void *memobj);
typedef int (*process_free_range_pt_clear_fn_t)(void *page_table,
						struct process_vm *vm,
						unsigned long start,
						unsigned long end);
typedef int (*process_free_range_tofu_remove_fn_t)(struct process_vm *vm,
						   struct vm_range *range);
typedef void (*process_free_range_log_fn_t)(int event,
					    struct process_vm *vm,
					    struct vm_range *range,
					    unsigned long start,
					    unsigned long end,
					    int error);
typedef int (*process_visit_pte_range_fn_t)(void *page_table,
					    unsigned long start,
					    unsigned long end, int pgshift,
					    int flags, void *visit_fn,
					    void *arg);
typedef struct vm_range *(*process_copy_range_lookup_fn_t)(
	struct process_vm *vm, unsigned long start, unsigned long end);
typedef struct vm_range *(*process_copy_range_next_fn_t)(
	struct process_vm *vm, struct vm_range *range);
typedef void (*process_copy_user_ranges_log_fn_t)(
	struct process_vm *orgvm, struct vm_range *range, long fault_addr);
typedef void *(*process_lookup_pte_fn_t)(void *page_table,
					 unsigned long addr, int pgshift,
					 size_t *pgsizep);
typedef int (*process_pte_test_fn_t)(void *ptep);
typedef int (*process_pte_pgsize_test_fn_t)(void *ptep, size_t pgsize);
typedef int (*process_split_contiguous_pages_fn_t)(void *ptep,
						   size_t pgsize,
						   unsigned int memobj_flags);
typedef uintptr_t (*process_pte_get_phys_fn_t)(void *ptep);
typedef void *(*process_phys_to_page_fn_t)(uintptr_t phys);
typedef long (*process_page_offset_fn_t)(void *page);
typedef void (*process_pte_make_fileoff_fn_t)(long off, size_t pgsize,
					      void *ptep);
typedef void (*process_pte_xchg_fn_t)(void *ptep, void *valp);
typedef void (*process_flush_tlb_single_fn_t)(unsigned long addr);
typedef int (*process_pgsize_to_tbllv_fn_t)(size_t pgsize);
typedef size_t (*process_tbllv_to_contpgsize_fn_t)(int level);
typedef int (*process_page_unmap_fn_t)(void *page);
typedef void (*process_panic_fn_t)(const char *message);
typedef int (*process_memobj_invalidate_page_fn_t)(struct memobj *memobj,
						   uintptr_t phys,
						   size_t pgsize);
typedef void (*process_invalidate_one_page_log_fn_t)(void *arg,
						     void *page_table,
						     void *ptep,
						     unsigned long pte_value,
						     void *pgaddr,
						     int pgshift,
						     int error);
typedef void (*process_sync_range_log_fn_t)(struct process_vm *vm,
					    struct vm_range *range,
					    unsigned long start,
					    unsigned long end,
					    int error);
typedef void (*process_remap_range_log_fn_t)(int event,
					     struct process_vm *vm,
					     struct vm_range *range,
					     unsigned long start,
					     unsigned long end,
					     long off,
					     int old_pgshift,
					     int error);
typedef int (*process_memory_range_free_fn_t)(struct process_vm *vm,
					      struct vm_range *range);
typedef void (*process_memory_range_log_fn_t)(struct process_vm *vm,
					      struct vm_range *range,
					      int error);
typedef void (*process_mckfd_free_fn_t)(struct mckfd *fdp);
typedef int (*process_mckfd_dup_fn_t)(struct mckfd *fdp, void *ctx);
typedef void (*process_policy_free_fn_t)(void *policy);
typedef void (*process_detach_address_space_fn_t)(void *address_space,
						  int pid);
typedef void (*process_release_process_fn_t)(void *process);
typedef void (*process_optional_free_fn_t)(void *ptr);
typedef void (*process_release_fp_regs_fn_t)(struct thread *thread);
typedef void (*process_ref_inc_fn_t)(void *object, unsigned long ref_offset);
typedef int (*process_ref_dec_and_test_fn_t)(void *object,
					     unsigned long ref_offset);
typedef int (*process_default_ncpus_fn_t)(void);
typedef void (*process_create_cpu_log_fn_t)(int event, int pid, int cpu);
typedef void (*process_hold_thread_warn_fn_t)(void *thread);
typedef void *(*process_current_resource_set_fn_t)(void);
typedef void (*process_resource_process_action_fn_t)(void *resource_set,
						     void *process);
typedef void (*process_process_action_fn_t)(void *process);
typedef void (*process_resource_set_action_fn_t)(void *resource_set);
typedef void (*process_tid_log_fn_t)(int tid, void *thread, int new_tid);
typedef void (*process_thread_profile_fn_t)(void *thread, void *process);
typedef void (*process_thread_action_fn_t)(void *thread);
typedef void (*process_thread_proc_action_fn_t)(void *process, void *thread);
typedef void (*process_thread_tid_action_fn_t)(void *process, void *thread,
					       int new_tid);
typedef void (*process_vm_action_fn_t)(void *vm);
typedef void (*process_mcs_rwlock_fn_t)(unsigned long lock_addr, void *node);
typedef int (*process_alloc_debugreg_fn_t)(void *thread);
typedef void (*process_ptrace_traceme_log_fn_t)(int event, int pid,
						unsigned long value,
						int error);
typedef unsigned long (*process_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*process_spin_unlock_fn_t)(unsigned long lock_addr,
					 unsigned long irqstate);
typedef void (*process_free_fn_t)(void *ptr);
typedef void (*process_address_space_free_cb_fn_t)(void *address_space,
						   void *opt);
typedef void (*process_address_space_action_fn_t)(void *address_space);
typedef void (*process_vm_free_cb_fn_t)(void *vm, void *opt);
typedef void (*process_pt_destroy_fn_t)(void *page_table);
typedef void *(*process_alloc_fn_t)(unsigned long size, unsigned long flags);
typedef void *(*process_pt_create_fn_t)(unsigned long flags);
typedef void (*process_ref_set_fn_t)(void *object, unsigned long ref_offset,
				     int value);
typedef void (*process_spin_init_fn_t)(unsigned long lock_addr);
typedef void (*process_rwlock_init_fn_t)(unsigned long lock_addr);
typedef void (*process_vm_init_numa_log_fn_t)(int numa_id);
typedef void (*process_waitq_init_fn_t)(unsigned long waitq_addr);
typedef void (*process_mcs_lock_init_fn_t)(unsigned long lock_addr);
typedef void *(*process_alloc_pages_fn_t)(int npages, unsigned long flags);
typedef void *(*process_create_address_space_fn_t)(int nslots);
typedef void (*process_release_address_space_fn_t)(void *address_space);
typedef int (*process_init_process_fn_t)(void *process, void *parent);
typedef int (*process_init_process_vm_fn_t)(void *owner, void *address_space,
					    void *vm);
typedef void (*process_init_user_process_fn_t)(void *thread,
					       unsigned long stack_top,
					       unsigned long user_pc,
					       unsigned long user_sp);
typedef void (*process_sched_init_context_fn_t)(void *thread);
typedef int (*process_sched_save_fp_fn_t)(void *thread);
typedef void (*process_sched_timer_init_fn_t)(int cpu);
typedef unsigned long (*process_virt_to_phys_fn_t)(void *addr);
typedef void *(*process_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*process_memset_fn_t)(void *addr, int value, size_t len);
typedef void (*process_memset_smp_log_fn_t)(int event, int cpu_index,
					    int nr_cpus, unsigned long phys,
					    size_t len, unsigned long start,
					    unsigned long end);
typedef int (*process_smp_call_fn_t)(void *cpu_set, void *handler,
				     void *arg);
typedef unsigned long (*process_attr_from_vrflag_fn_t)(unsigned long flag,
						       unsigned long fault,
						       void *ptep);
typedef void (*process_noirq_lock_fn_t)(unsigned long lock_addr);
typedef void (*process_noirq_unlock_fn_t)(unsigned long lock_addr);
typedef int (*process_pt_change_attr_fn_t)(void *page_table,
					   unsigned long start,
					   unsigned long end,
					   unsigned long clrattr,
					   unsigned long setattr);
typedef int (*process_pt_set_range_fn_t)(void *page_table,
					  struct process_vm *vm,
					  unsigned long start,
					  unsigned long end,
					  unsigned long phys,
					  unsigned long attr,
					  int pgshift,
					  struct vm_range *range,
					  int flags);
typedef void (*process_update_page_table_log_fn_t)(int error);
typedef void (*process_change_prot_public_log_fn_t)(int event,
						    struct process_vm *vm,
						    struct vm_range *range,
						    unsigned long protflag,
						    int error);
typedef void (*process_access_ok_log_fn_t)(struct process_vm *vm,
					   int verify_type, unsigned long addr,
					   size_t len, int error);
typedef int (*process_fault_range_fn_t)(struct process_vm *vm,
					struct vm_range *range,
					unsigned long fault_addr,
					unsigned long reason);
typedef int (*process_zeroobj_match_fn_t)(void *memobj);
typedef int (*process_page_fault_vm_fn_t)(struct process_vm *vm,
					  unsigned long fault_addr,
					  unsigned long reason);
typedef void (*process_preempt_fn_t)(void);
typedef void (*process_pgio_dispatch_fn_t)(void *fp, void *arg);
typedef void (*process_populate_warn_fn_t)(struct process_vm *vm,
					   unsigned long addr,
					   unsigned long reason,
					   unsigned long off,
					   size_t len, int error);
typedef int (*process_remove_range_split_fn_t)(struct process_vm *vm,
					       struct vm_range *range,
					       unsigned long addr,
					       struct vm_range **splitp);
typedef void (*process_remove_range_xpmem_fn_t)(struct process_vm *vm,
						struct vm_range *range);
typedef void (*process_remove_range_log_fn_t)(int event,
					      struct process_vm *vm,
					      unsigned long start,
					      unsigned long end,
					      struct vm_range *range,
					      int error);
typedef int (*process_remove_region_clear_fn_t)(void *page_table,
						struct process_vm *vm,
						unsigned long start,
						unsigned long end);
typedef void (*process_remove_region_log_fn_t)(struct process_vm *vm,
					       unsigned long start,
					       unsigned long end);
typedef void *(*process_init_stack_alloc_aligned_fn_t)(int npages,
						       int p2align,
						       unsigned long flags,
						       unsigned long virt_addr);
typedef void (*process_init_stack_free_pages_fn_t)(void *addr, int npages);
typedef int (*process_init_stack_add_range_fn_t)(struct process_vm *vm,
						 unsigned long start,
						 unsigned long end,
						 unsigned long phys,
						 unsigned long flag,
						 int pgshift,
						 struct vm_range **rangep);
typedef unsigned long (*process_init_stack_virt_to_phys_fn_t)(void *addr);
typedef int (*process_init_stack_pt_set_range_fn_t)(void *page_table,
						    struct process_vm *vm,
						    unsigned long start,
						    unsigned long end,
						    unsigned long phys,
						    unsigned long attr,
						    int pgshift,
						    struct vm_range *range,
						    int flags);
typedef unsigned long (*process_init_stack_hwcap_fn_t)(void);
typedef void (*process_init_stack_modify_context_fn_t)(void *uctx, int reg,
						       unsigned long value);
typedef void (*process_init_stack_log_fn_t)(int event,
					    const unsigned long *args);

#define PROCESS_ADD_RANGE_MAP_SKIP 0
#define PROCESS_ADD_RANGE_MAP_UPDATE 1
#define PROCESS_ADD_RANGE_MAP_MARK_XPMEM 2
#define PROCESS_ADD_RANGE_MAP_DEMAND 3

#define PROCESS_ADD_RANGE_LOG_ALLOC_FAILED 1
#define PROCESS_ADD_RANGE_LOG_INSERT_FAILED 2
#define PROCESS_ADD_RANGE_LOG_PREP_FAILED 3
#define PROCESS_ADD_RANGE_LOG_DEMAND 4
#define PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED 5

#define PROCESS_VM_RANGE_INSERT_LOG_OVERLAP 1
#define PROCESS_VM_RANGE_INSERT_LOG_SUCCESS 2

#define PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER 1
#define PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT 2
#define PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER 3
#define PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT 4
#define PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER 5
#define PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT 6
#define PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER 7
#define PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT 8

#define PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER 1
#define PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR 2
#define PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT 3

#define PROCESS_FREE_RANGE_PT_SKIP 0
#define PROCESS_FREE_RANGE_PT_FREE 1
#define PROCESS_FREE_RANGE_PT_CLEAR 2

#define PROCESS_REMOVE_STRAIGHT_NO_CONVERT 0
#define PROCESS_REMOVE_STRAIGHT_NEED_RANGE 1
#define PROCESS_REMOVE_STRAIGHT_CONVERTED 2

#define PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT 1
#define PROCESS_REMOVE_RANGE_LOG_CONVERTED 2
#define PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED 3
#define PROCESS_REMOVE_RANGE_LOG_FREE_FAILED 4
#define PROCESS_REMOVE_RANGE_LOG_DONE 5

#define PROCESS_FREE_BODY_LOG_PLAN_FAILED 1
#define PROCESS_FREE_BODY_LOG_PT_FREE_FAILED 2
#define PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED 3
#define PROCESS_FREE_BODY_LOG_TOFU_REMOVED 4
#define PROCESS_FREE_BODY_LOG_FINALIZE_FAILED 5
#define PROCESS_FREE_BODY_LOG_DONE 6

#define PROCESS_REMAP_RANGE_LOG_PGSHIFT 1
#define PROCESS_REMAP_RANGE_LOG_VISIT_FAILED 2

#define PROCESS_INIT_STACK_LOG_SIZE 1
#define PROCESS_INIT_STACK_LOG_AP_USER 2
#define PROCESS_INIT_STACK_LOG_ALLOC_FAILED 3
#define PROCESS_INIT_STACK_LOG_ADD_FAILED 4
#define PROCESS_INIT_STACK_LOG_PT_FAILED 5
#define PROCESS_INIT_STACK_LOG_AUXV 6
#define PROCESS_INIT_STACK_LOG_SIZE_MISMATCH 7
#define PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH 8
#define PROCESS_INIT_STACK_LOG_INITIAL 9

#define PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED 1
#define PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED 2

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
struct vm_range *process_add_range_alloc_result(
	unsigned long range_size, process_add_range_alloc_fn_t alloc_fn);
int process_add_range_free_result(
	struct vm_range *range, process_add_range_free_fn_t free_fn);
int process_add_range_insert_result(
	struct process_vm *vm, struct vm_range *range,
	process_add_range_insert_fn_t insert_fn);
int process_add_range_update_result(
	struct process_vm *vm, struct vm_range *range, unsigned long phys,
	unsigned long attr, process_add_range_update_fn_t update_fn);
int process_add_range_remove_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_add_range_remove_fn_t remove_fn);
int process_add_range_mark_xpmem_result(
	struct vm_range *range,
	process_add_range_mark_xpmem_fn_t mark_xpmem_fn);
int process_add_range_memclear_result(
	unsigned long phys, unsigned long bytes,
	process_add_range_memclear_fn_t memclear_fn);
int process_add_range_log_result(
	int event, int rc, unsigned long start, unsigned long end,
	process_add_range_log_fn_t log_fn);
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
int process_add_range_public_body_result(
	struct process_vm *vm, unsigned long range_size,
	unsigned long user_start, unsigned long user_end,
	unsigned long start, unsigned long end, unsigned long phys,
	unsigned long flag, struct memobj *memobj, off_t offset,
	int pgshift, void *private_data, struct vm_range **rp,
	process_add_range_alloc_fn_t alloc_fn,
	process_add_range_free_fn_t free_fn,
	process_add_range_insert_fn_t insert_fn,
	process_add_range_update_fn_t update_fn,
	process_add_range_remove_fn_t remove_fn,
	process_add_range_mark_xpmem_fn_t mark_xpmem_fn,
	process_add_range_memclear_fn_t memclear_fn,
	process_add_range_log_fn_t log_fn);
int process_vm_range_insert_log_result(
	int event, struct process_vm *vm, struct vm_range *newrange,
	struct vm_range *range, process_vm_range_insert_log_fn_t log_fn);
int process_vm_range_insert_dump_result(
	struct process_vm *vm, process_vm_range_insert_dump_fn_t dump_fn);
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
int process_noirq_lock_result(unsigned long lock_addr,
			      process_noirq_lock_fn_t lock_fn);
int process_noirq_unlock_result(unsigned long lock_addr,
				process_noirq_unlock_fn_t unlock_fn);
int process_pt_change_attr_result(void *page_table, unsigned long start,
				  unsigned long end, unsigned long clrattr,
				  unsigned long setattr,
				  process_pt_change_attr_fn_t change_attr_fn);
int process_pt_set_range_result(void *page_table, struct process_vm *vm,
				unsigned long start, unsigned long end,
				unsigned long phys, unsigned long attr,
				int pgshift, struct vm_range *range, int flags,
				process_pt_set_range_fn_t pt_set_range_fn);
int process_update_page_table_log_result(
	int error, process_update_page_table_log_fn_t log_fn);
int process_zeroobj_match_result(void *memobj,
				 process_zeroobj_match_fn_t zeroobj_match_fn);
int process_fault_range_result(struct process_vm *vm, struct vm_range *range,
			       unsigned long fault_addr, unsigned long reason,
			       process_fault_range_fn_t fault_fn);
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
struct vm_range *process_lookup_memory_range_body_result(
	struct process_vm *vm, unsigned long start, unsigned long end);
struct vm_range *process_next_memory_range_body_result(struct vm_range *range);
struct vm_range *process_previous_memory_range_body_result(
	struct vm_range *range);
int process_extend_up_body_result(struct process_vm *vm,
				  struct vm_range *range,
				  unsigned long newend);
int process_range_public_log_result(
	int event, struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, int error,
	process_range_public_log_fn_t log_fn);
struct vm_range *process_lookup_memory_range_public_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_range_public_log_fn_t log_fn);
struct vm_range *process_next_memory_range_public_result(
	struct process_vm *vm, struct vm_range *range,
	process_range_public_log_fn_t log_fn);
struct vm_range *process_previous_memory_range_public_result(
	struct process_vm *vm, struct vm_range *range,
	process_range_public_log_fn_t log_fn);
int process_extend_up_public_result(struct process_vm *vm,
				    struct vm_range *range,
				    unsigned long newend,
				    process_range_public_log_fn_t log_fn);
int process_change_prot_body_result(struct process_vm *vm,
				    struct vm_range *range,
				    unsigned long protflag,
				    process_attr_from_vrflag_fn_t attr_fn,
				    process_noirq_lock_fn_t lock_fn,
				    process_noirq_unlock_fn_t unlock_fn,
				    process_pt_change_attr_fn_t change_attr_fn);
int process_change_prot_public_log_result(
	int event, struct process_vm *vm, struct vm_range *range,
	unsigned long protflag, int error,
	process_change_prot_public_log_fn_t log_fn);
int process_change_prot_public_result(
	struct process_vm *vm, struct vm_range *range, unsigned long protflag,
	process_attr_from_vrflag_fn_t attr_fn,
	process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_pt_change_attr_fn_t change_attr_fn,
	process_change_prot_public_log_fn_t log_fn);
int process_update_page_table_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long phys,
	unsigned long populate_fault, process_attr_from_vrflag_fn_t attr_fn,
	process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn,
	process_pt_set_range_fn_t pt_set_range_fn,
	process_update_page_table_log_fn_t log_fn);
int process_update_page_table_public_result(
	struct process_vm *vm, struct vm_range *range, unsigned long phys,
	unsigned long flag, process_attr_from_vrflag_fn_t attr_fn,
	process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn,
	process_pt_set_range_fn_t pt_set_range_fn,
	process_update_page_table_log_fn_t log_fn);
int process_access_ok_body_result(struct process_vm *vm, int verify_type,
				  unsigned long addr, size_t len);
int process_access_ok_log_result(
	struct process_vm *vm, int verify_type, unsigned long addr, size_t len,
	int error, process_access_ok_log_fn_t log_fn);
int process_access_ok_public_result(
	struct process_vm *vm, int verify_type, unsigned long addr, size_t len,
	process_access_ok_log_fn_t log_fn);
int process_do_page_fault_vm_body_result(
	struct process_vm *vm, struct process_vm *current_vm,
	unsigned long fault_addr, unsigned long reason, int current_cpu,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_noirq_lock_fn_t write_lock_fn,
	process_noirq_unlock_fn_t write_unlock_fn,
	process_zeroobj_match_fn_t zeroobj_match_fn,
	process_fault_range_fn_t normal_fault_fn,
	process_fault_range_fn_t xpmem_fault_fn);
int process_page_fault_vm_dispatch_result(
	struct process_vm *vm, unsigned long fault_addr, unsigned long reason,
	process_page_fault_vm_fn_t fault_fn);
int process_preempt_result(process_preempt_fn_t preempt_fn);
int process_pgio_dispatch_pending_result(
	void *thread, unsigned long pgio_fp_offset,
	unsigned long pgio_arg_offset,
	process_pgio_dispatch_fn_t pgio_dispatch_fn);
int process_populate_warn_result(struct process_vm *vm, unsigned long addr,
				 unsigned long reason, unsigned long off,
				 size_t len, int error,
				 process_populate_warn_fn_t warn_fn);
int process_page_fault_vm_retry_body_result(
	struct process_vm *vm, unsigned long fault_addr, unsigned long reason,
	void *thread, unsigned long pgio_fp_offset,
	unsigned long pgio_arg_offset, process_page_fault_vm_fn_t do_fault_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_pgio_dispatch_fn_t pgio_dispatch_fn);
int process_page_fault_vm_public_result(
	struct process_vm *vm, struct process_vm *current_vm,
	unsigned long fault_addr, unsigned long reason, int current_cpu,
	void *thread, unsigned long pgio_fp_offset,
	unsigned long pgio_arg_offset,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_noirq_lock_fn_t write_lock_fn,
	process_noirq_unlock_fn_t write_unlock_fn,
	process_zeroobj_match_fn_t zeroobj_match_fn,
	process_fault_range_fn_t normal_fault_fn,
	process_fault_range_fn_t xpmem_fault_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_pgio_dispatch_fn_t pgio_dispatch_fn);
int process_populate_memory_body_result(
	struct process_vm *vm, unsigned long start, size_t len,
	unsigned long page_size, unsigned long reason,
	process_page_fault_vm_fn_t page_fault_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_populate_warn_fn_t warn_fn);
int process_populate_memory_public_result(
	struct process_vm *vm, struct process_vm *current_vm,
	unsigned long start, size_t len, unsigned long page_size,
	unsigned long reason, int current_cpu, void *thread,
	unsigned long pgio_fp_offset, unsigned long pgio_arg_offset,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_noirq_lock_fn_t write_lock_fn,
	process_noirq_unlock_fn_t write_unlock_fn,
	process_zeroobj_match_fn_t zeroobj_match_fn,
	process_fault_range_fn_t normal_fault_fn,
	process_fault_range_fn_t xpmem_fault_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_pgio_dispatch_fn_t pgio_dispatch_fn,
	process_populate_warn_fn_t warn_fn);
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
int process_memobj_ref_direct_result(struct memobj *memobj);
int process_memobj_unref_direct_result(struct memobj *memobj);
int process_range_memobj_ref_result(struct memobj *memobj,
				    process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_optional_memobj_ref_result(
	struct memobj *memobj,
	process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_memobj_ref_or_direct_result(
	struct memobj *memobj,
	process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_memobj_unref_or_direct_result(
	struct memobj *memobj,
	process_range_memobj_ref_fn_t memobj_unref_fn);
int process_range_optional_memobj_ref_or_direct_result(
	struct memobj *memobj,
	process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_optional_memobj_unref_or_direct_result(
	struct memobj *memobj,
	process_range_memobj_ref_fn_t memobj_unref_fn);
int process_split_range_insert_result(
	struct process_vm *vm, struct vm_range *range,
	process_split_range_insert_fn_t insert_fn);
int process_split_range_publish_result(
	struct process_vm *vm, struct vm_range *low, struct vm_range *high,
	uintptr_t addr, struct vm_range **splitp,
	process_range_memobj_ref_fn_t memobj_ref_fn,
	process_split_range_insert_fn_t insert_fn);
struct vm_range *process_split_range_alloc_init_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	void *splitp, unsigned long range_size, unsigned long alloc_flags,
	int *errorp, process_split_range_alloc_fn_t alloc_fn,
	process_split_range_alloc_log_fn_t log_fn);
int process_split_range_publish_body_result(
	struct process_vm *vm, struct vm_range *low, struct vm_range *high,
	uintptr_t addr, struct vm_range **splitp,
	process_range_memobj_ref_fn_t memobj_ref_fn,
	process_split_range_insert_fn_t insert_fn,
	process_split_range_publish_log_fn_t log_fn);
int process_split_range_pt_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	process_split_range_pt_split_fn_t split_fn,
	process_split_range_pt_log_fn_t log_fn);
int process_split_shm_update_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	unsigned long page_pgshift_offset,
	process_split_shm_lookup_page_fn_t lookup_page_fn,
	process_split_shm_phys_to_page_fn_t phys_to_page_fn,
	process_split_shm_update_page_fn_t update_page_fn,
	process_split_shm_log_fn_t log_fn);
int process_join_range_prepare_result(struct vm_range *surviving,
				      const struct vm_range *merging);
int process_join_range_free_result(struct vm_range *range,
				   process_join_range_free_fn_t free_fn);
int process_join_range_tofu_result(struct process_vm *vm,
				   struct vm_range *surviving,
				   struct vm_range *merging,
				   process_join_range_tofu_fn_t tofu_fn);
int process_join_range_body_result(
	struct process_vm *vm, struct rb_root *root, struct vm_range **cache,
	int cache_count, struct vm_range *surviving, struct vm_range *merging,
	process_range_memobj_ref_fn_t memobj_unref_fn,
	process_join_range_free_fn_t free_fn,
	process_join_range_tofu_fn_t tofu_fn);
int process_free_range_page_size_result(
	size_t current, size_t *nextp,
	process_free_range_page_size_fn_t page_size_fn);
int process_free_range_pt_plan_result(
	const struct vm_range *range, unsigned long straight_va, int has_prev,
	unsigned long prev_end, int has_next, unsigned long next_start,
	int has_memobj, unsigned int memobj_flags, unsigned long *startp,
	unsigned long *endp, int *actionp,
	process_free_range_page_size_fn_t page_size_fn);
int process_free_range_finalize_result(
	struct process_vm *vm, struct rb_root *root, struct vm_range **cache,
	int cache_count, struct vm_range *range, unsigned long straight_va,
	size_t *straight_lenp, unsigned long straight_pa,
	process_free_range_phys_to_virt_fn_t phys_to_virt_fn,
	process_free_range_pages_fn_t free_pages_fn,
	process_free_range_clear_main_fn_t clear_main_fn,
	process_free_range_free_fn_t free_fn);
void *process_free_range_phys_to_virt_result(
	unsigned long phys, process_free_range_phys_to_virt_fn_t phys_to_virt_fn);
int process_free_range_free_pages_result(
	void *addr, unsigned long pages,
	process_free_range_pages_fn_t free_pages_fn);
int process_free_range_clear_main_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_free_range_clear_main_fn_t clear_main_fn);
int process_free_range_free_result(struct vm_range *range,
				   process_free_range_free_fn_t free_fn);
int process_free_range_pt_free_result(
	void *page_table, struct process_vm *vm, unsigned long start,
	unsigned long end, void *memobj,
	process_free_range_pt_free_fn_t pt_free_fn);
int process_free_range_pt_clear_result(
	void *page_table, struct process_vm *vm, unsigned long start,
	unsigned long end, process_free_range_pt_clear_fn_t pt_clear_fn);
int process_free_range_tofu_remove_result(
	struct process_vm *vm, struct vm_range *range,
	process_free_range_tofu_remove_fn_t tofu_remove_fn);
int process_free_range_log_result(
	int event, struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, int error,
	process_free_range_log_fn_t log_fn);
int process_free_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long straight_va, size_t *straight_lenp,
	unsigned long straight_pa, int tofu_enabled,
	process_free_range_page_size_fn_t page_size_fn,
	process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_range_memobj_ref_fn_t memobj_ref_fn,
	process_range_memobj_ref_fn_t memobj_unref_fn,
	process_free_range_pt_free_fn_t pt_free_fn,
	process_free_range_pt_clear_fn_t pt_clear_fn,
	process_free_range_tofu_remove_fn_t tofu_remove_fn,
	process_free_range_phys_to_virt_fn_t phys_to_virt_fn,
	process_free_range_pages_fn_t free_pages_fn,
	process_free_range_clear_main_fn_t clear_main_fn,
	process_free_range_free_fn_t free_fn,
	process_free_range_log_fn_t log_fn);
int process_sync_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, void *arg,
	void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_sync_range_log_fn_t log_fn);
int process_remap_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, long off, void *arg,
	void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_remap_range_log_fn_t log_fn);
int process_invalidate_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, void *arg,
	void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_lookup_pte_fn_t lookup_pte_fn,
	process_pte_test_fn_t pte_contiguous_fn,
	process_pte_pgsize_test_fn_t pte_head_fn,
	process_pte_pgsize_test_fn_t pte_tail_fn,
	process_split_contiguous_pages_fn_t split_fn,
	process_free_range_pt_free_fn_t pt_free_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_sync_range_log_fn_t log_fn);
int process_invalidate_one_page_body_result(
	void *arg, void *page_table, void *ptep, void *pgaddr, int pgshift,
	process_pte_test_fn_t pte_null_fn,
	process_pte_pgsize_test_fn_t pte_fileoff_fn,
	process_pte_get_phys_fn_t pte_get_phys_fn,
	process_phys_to_page_fn_t phys_to_page_fn,
	process_page_offset_fn_t page_offset_fn,
	process_pte_make_fileoff_fn_t pte_make_fileoff_fn,
	process_pte_xchg_fn_t pte_xchg_fn,
	process_flush_tlb_single_fn_t flush_tlb_single_fn,
	process_pte_test_fn_t pte_contiguous_fn,
	process_pte_pgsize_test_fn_t pte_head_fn,
	process_pgsize_to_tbllv_fn_t pgsize_to_tbllv_fn,
	process_tbllv_to_contpgsize_fn_t tbllv_to_contpgsize_fn,
	process_page_unmap_fn_t page_unmap_fn,
	process_panic_fn_t panic_fn,
	process_memobj_invalidate_page_fn_t memobj_invalidate_page_fn,
	process_invalidate_one_page_log_fn_t log_fn);
int process_remove_straight_convert_result(
	unsigned long straight_va, size_t straight_len,
	const struct vm_range *range, unsigned long start, unsigned long end,
	unsigned long *new_startp, unsigned long *new_endp,
	unsigned long *lenp);
int process_remove_range_split_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	struct vm_range **splitp, process_remove_range_split_fn_t split_fn);
int process_remove_range_xpmem_result(
	struct process_vm *vm, struct vm_range *range,
	process_remove_range_xpmem_fn_t xpmem_remove_fn);
int process_remove_range_free_result(
	struct process_vm *vm, struct vm_range *range,
	process_memory_range_free_fn_t free_fn);
int process_remove_range_log_result(
	int event, struct process_vm *vm, unsigned long start,
	unsigned long end, struct vm_range *range, int error,
	process_remove_range_log_fn_t log_fn);
int process_remove_memory_range_body_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	int *ro_freedp, unsigned long straight_va, size_t straight_len,
	process_remove_range_split_fn_t split_fn,
	process_remove_range_xpmem_fn_t xpmem_remove_fn,
	process_memory_range_free_fn_t free_fn,
	process_remove_range_log_fn_t log_fn);
int process_remove_region_body_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_noirq_lock_fn_t lock_fn, process_noirq_unlock_fn_t unlock_fn,
	process_remove_region_clear_fn_t clear_fn,
	process_remove_region_log_fn_t log_fn);
int process_remove_region_clear_result(
	void *page_table, struct process_vm *vm, unsigned long start,
	unsigned long end, process_remove_region_clear_fn_t clear_fn);
int process_remove_region_log_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_remove_region_log_fn_t log_fn);
void *process_init_stack_alloc_aligned_result(
	int npages, int p2align, unsigned long flags, unsigned long virt_addr,
	process_init_stack_alloc_aligned_fn_t alloc_aligned_fn);
int process_init_stack_free_pages_result(
	void *addr, int npages, process_init_stack_free_pages_fn_t free_pages_fn);
int process_init_stack_add_range_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	unsigned long phys, unsigned long flag, int pgshift,
	struct vm_range **rangep,
	process_init_stack_add_range_fn_t add_range_fn);
unsigned long process_init_stack_virt_to_phys_result(
	void *addr, process_init_stack_virt_to_phys_fn_t virt_to_phys_fn);
unsigned long process_attr_from_vrflag_result(
	unsigned long flag, unsigned long fault, void *ptep,
	process_attr_from_vrflag_fn_t attr_fn);
int process_init_stack_pt_set_range_result(
	void *page_table, struct process_vm *vm, unsigned long start,
	unsigned long end, unsigned long phys, unsigned long attr, int pgshift,
	struct vm_range *range, int flags,
	process_init_stack_pt_set_range_fn_t pt_set_range_fn);
unsigned long process_init_stack_hwcap_result(
	process_init_stack_hwcap_fn_t hwcap_fn);
int process_init_stack_modify_context_result(
	void *uctx, int reg, unsigned long value,
	process_init_stack_modify_context_fn_t modify_context_fn);
int process_init_stack_log_result(int event, const unsigned long *args,
				  process_init_stack_log_fn_t log_fn);
int process_init_stack_body_result(
	struct thread *thread, struct program_load_desc *pn,
	unsigned long at_base, int argc, char **argv, int envc, char **env,
	unsigned long page_size, int page_shift,
	unsigned long user_stack_page_mask, int user_stack_page_shift,
	unsigned long user_stack_prepage_size,
	unsigned long stack_alloc_size_override, int user_stack_page_p2align,
	unsigned long alloc_nowait, unsigned long alloc_user,
	unsigned long mpol_no_stack, int user_context_sp_reg,
	unsigned long pf_populate,
	process_init_stack_alloc_aligned_fn_t alloc_aligned_fn,
	process_init_stack_free_pages_fn_t free_pages_fn,
	process_init_stack_add_range_fn_t add_range_fn,
	process_init_stack_virt_to_phys_fn_t virt_to_phys_fn,
	process_attr_from_vrflag_fn_t attr_fn,
	process_init_stack_pt_set_range_fn_t pt_set_range_fn,
	process_init_stack_hwcap_fn_t hwcap_fn,
	process_init_stack_modify_context_fn_t modify_context_fn,
	process_init_stack_log_fn_t log_fn);
int process_ref_release_should_destroy_result(int dec_and_test);
int process_release_address_space_should_destroy_result(int dec_and_test);
int process_release_address_space_should_run_free_cb_result(
	unsigned long free_cb_addr);
int process_ref_dec_and_test_result(
	void *object, unsigned long ref_offset,
	process_ref_dec_and_test_fn_t dec_fn);
int process_ref_set_result(void *object, unsigned long ref_offset, int value,
			   process_ref_set_fn_t ref_set_fn);
int process_ref_inc_direct_result(void *object, unsigned long ref_offset);
int process_ref_dec_and_test_direct_result(void *object,
					   unsigned long ref_offset);
int process_ref_set_direct_result(void *object, unsigned long ref_offset,
				  int value);
void *process_alloc_result(unsigned long size, unsigned long flags,
			   process_alloc_fn_t alloc_fn);
int process_free_callback_result(void *ptr, process_free_fn_t free_fn);
void *process_pt_create_result(unsigned long flags,
			       process_pt_create_fn_t pt_create_fn);
int process_pt_destroy_result(void *page_table,
			      process_pt_destroy_fn_t pt_destroy_fn);
int process_spin_init_result(unsigned long lock_addr,
			     process_spin_init_fn_t spin_init_fn);
int process_address_space_free_cb_result(
	void *asp, void *opt, process_address_space_free_cb_fn_t free_cb);
int process_address_space_action_result(
	void *asp, process_address_space_action_fn_t action_fn);
int process_release_address_space_body_result(
	void *asp, unsigned long refcount_offset, unsigned long free_cb_offset,
	unsigned long opt_offset, unsigned long page_table_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_pt_destroy_fn_t pt_destroy_fn, process_free_fn_t free_fn);
int process_hold_address_space_public_result(
	void *asp, unsigned long refcount_offset, process_ref_inc_fn_t inc_fn);
int process_release_address_space_public_result(
	void *asp, unsigned long refcount_offset, unsigned long free_cb_offset,
	unsigned long opt_offset, unsigned long page_table_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_pt_destroy_fn_t pt_destroy_fn, process_free_fn_t free_fn);
int process_detach_address_space_body_result(
	void *asp, int pid, unsigned long pids_offset,
	unsigned long nslots_offset, process_address_space_action_fn_t release_fn);
int process_detach_address_space_public_result(
	void *asp, int pid, unsigned long pids_offset,
	unsigned long nslots_offset, process_address_space_action_fn_t release_fn);
void *process_create_address_space_body_result(
	int nslots, unsigned long address_space_size,
	unsigned long pid_slot_size, unsigned long nowait_flag,
	unsigned long page_table_offset, unsigned long refcount_offset,
	unsigned long cpu_set_offset, unsigned long cpu_set_size,
	unsigned long cpu_set_lock_offset, unsigned long nslots_offset,
	process_alloc_fn_t alloc_fn, process_free_fn_t free_fn,
	process_pt_create_fn_t pt_create_fn, process_ref_set_fn_t ref_set_fn,
	process_spin_init_fn_t spin_init_fn);
int process_create_cpu_allowed_result(int cpu, int num_processors);
int process_create_use_default_cpu_set_result(int cpu_set_empty);
int process_create_cpu_sets_body_result(
	unsigned long requested_cpu_set_addr, unsigned long requested_bits,
	unsigned long thread_cpu_set_addr, unsigned long proc_cpu_set_addr,
	int output_cpu_set_bits, int num_processors, int pid,
	process_default_ncpus_fn_t default_ncpus_fn,
	process_create_cpu_log_fn_t log_fn);
int process_allocated_object_zero_body_result(void *object,
					      unsigned long object_size);
int process_vm_init_body_result(
	struct process_vm *vm, struct process *owner, void *asp,
	int nr_numa_nodes, process_rwlock_init_fn_t memory_lock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_vm_init_numa_log_fn_t numa_log_fn);
void *process_new_resource_set_body_result(
	unsigned long resource_set_size, unsigned long process_hash_size,
	unsigned long thread_hash_size, unsigned long process_size,
	unsigned long nowait_flag, int hash_size, int init_pid,
	process_alloc_fn_t alloc_fn, process_free_fn_t free_fn,
	process_init_process_fn_t init_process_fn,
	process_rwlock_init_fn_t rwlock_init_fn);
int process_memset_smp_handler_body_result(
	int cpu_index, int nr_cpus, unsigned long phys, size_t len, int value,
	process_phys_to_virt_fn_t phys_to_virt_fn,
	process_memset_fn_t memset_fn,
	process_memset_smp_log_fn_t log_fn);
int process_memset_smp_body_result(
	void *cpu_set, void *addr, int value, size_t len,
	unsigned long *phys_slot, size_t *len_slot, int *value_slot,
	void *handler, void *request,
	process_virt_to_phys_fn_t virt_to_phys_fn,
	process_smp_call_fn_t smp_call_fn);
int process_proc_init_body_result(
	void *resource_set, struct list_head *resource_set_list,
	unsigned long resource_set_lock_addr, int num_processors,
	int cpu_set_bits, unsigned long path_size, unsigned long nowait_flag,
	process_alloc_fn_t alloc_fn, process_rwlock_init_fn_t rwlock_init_fn);
int process_sched_init_body_result(
	unsigned long cpu_local_addr, struct list_head *resource_set_list,
	int current_cpu, process_init_process_fn_t init_process_fn,
	process_rwlock_init_fn_t memory_lock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_sched_init_context_fn_t init_context_fn,
	process_sched_save_fp_fn_t save_fp_fn,
	process_sched_timer_init_fn_t timer_init_fn);
int process_init_state_body_result(
	void *process, const void *parent,
	const struct process_init_state_offsets *offsets,
	int initial_pid, int running_status);
int process_init_links_body_result(
	void *process, unsigned long hash_list_offset,
	unsigned long siblings_list_offset,
	unsigned long ptraced_siblings_list_offset,
	unsigned long update_lock_offset,
	unsigned long report_threads_list_offset,
	unsigned long threads_list_offset,
	unsigned long children_list_offset,
	unsigned long ptraced_children_list_offset,
	unsigned long threads_lock_offset,
	unsigned long children_lock_offset,
	unsigned long coredump_lock_offset,
	unsigned long mckfd_lock_offset,
	unsigned long waitpid_q_offset,
	unsigned long refcount_offset,
	unsigned long monitoring_event_offset,
	process_rwlock_init_fn_t rwlock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_waitq_init_fn_t waitq_init_fn,
	process_ref_set_fn_t ref_set_fn);
int process_init_profile_body_result(
	void *process, unsigned long profile_lock_offset,
	unsigned long profile_events_offset,
	process_mcs_lock_init_fn_t lock_init_fn);
int process_clone_thread_base_state_body_result(
	void *thread, const void *origin, unsigned long cpu_set_offset,
	unsigned long cpu_set_size, unsigned long in_kernel_offset);
int process_clone_thread_sched_state_body_result(
	void *thread, const void *origin, unsigned long sched_policy_offset,
	unsigned long sched_priority_offset);
int process_thread_sched_default_body_result(
	void *thread, unsigned long sched_policy_offset, int default_policy);
int process_create_thread_link_state_body_result(
	void *thread, void *process, void *vm, unsigned long thread_vm_offset,
	unsigned long thread_proc_offset, unsigned long process_vm_offset,
	unsigned long process_main_thread_offset);
int process_thread_exit_status_init_body_result(
	void *thread, unsigned long exit_status_offset, int exit_status);
int process_thread_spin_sleep_init_body_result(
	void *thread, unsigned long spin_sleep_lock_offset,
	unsigned long spin_sleep_offset, process_spin_init_fn_t spin_init_fn);
int process_thread_sigmask_copy_body_result(
	void *thread, const void *origin, unsigned long sigmask_offset,
	unsigned long sigmask_size);
int process_clone_profile_state_body_result(
	void *thread, const void *origin, const void *process,
	unsigned long thread_profile_offset, unsigned long process_profile_offset);
int process_clone_fork_process_termsig_body_result(
	void *process, unsigned long termsig_offset, int termsig);
int process_clone_fork_saved_cmdline_body_result(
	void *process, const void *origin_process,
	unsigned long saved_cmdline_len_offset,
	unsigned long saved_cmdline_offset, unsigned long nowait_flag,
	process_alloc_fn_t alloc_fn);
int process_clone_fork_vm_policy_body_result(
	void *dst_vm, const void *src_vm, unsigned long numa_mask_offset,
	unsigned long numa_mask_size, unsigned long numa_mem_policy_offset,
	unsigned long region_offset, unsigned long region_size);
int process_clone_thread_shared_vm_state_body_result(
	void *thread, void *process, void *vm, unsigned long thread_vm_offset,
	unsigned long thread_proc_offset);
int process_clone_sigcommon_share_body_result(
	void *thread, const void *origin, unsigned long sigcommon_offset,
	unsigned long sigcommon_use_offset, process_ref_inc_fn_t ref_inc_fn);
int process_clone_sigcommon_action_copy_body_result(
	void *dst_sigcommon, const void *src_sigcommon,
	unsigned long action_offset, unsigned long action_size);
int process_clone_user_context_body_result(
	void *thread, const void *origin, unsigned long uctx_offset,
	unsigned long uctx_size, int stack_pointer_reg, unsigned long sp,
	int program_counter_reg, unsigned long pc,
	process_init_stack_modify_context_fn_t modify_context_fn);
int process_clone_fork_profile_body_result(
	void *process, const void *origin_process, unsigned long profile_offset);
int process_clone_on_fork_vm_body_result(
	void *cpu_local, unsigned long on_fork_vm_offset, void *vm);
int process_mckfd_copy_body_result(void *dst, const void *src,
				   unsigned long mckfd_size);
int process_copy_user_range_metadata_body_result(
	struct vm_range *dst, const struct vm_range *src,
	process_range_memobj_ref_fn_t memobj_ref_fn);
int process_copy_user_pte_args_init_body_result(
	void *args, unsigned long new_vm_offset,
	unsigned long new_vrflag_offset, unsigned long range_offset,
	unsigned long fault_addr_offset, void *vm, unsigned long vrflag,
	void *range, long fault_addr);
int process_copy_user_pte_buffer_body_result(void *dst, const void *src,
					     size_t len, int wipe);
int process_copy_user_ranges_body_result(
	struct process_vm *vm, struct process_vm *orgvm,
	unsigned long range_size, unsigned long alloc_flags, void *copy_args,
	unsigned long new_vm_offset, unsigned long new_vrflag_offset,
	unsigned long range_offset, unsigned long fault_addr_offset,
	void *copy_pte_fn, int visit_flags,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_copy_range_lookup_fn_t lookup_fn,
	process_copy_range_next_fn_t next_fn,
	process_add_range_alloc_fn_t alloc_fn,
	process_add_range_free_fn_t free_fn,
	process_add_range_insert_fn_t insert_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_memory_range_free_fn_t free_range_fn,
	process_copy_user_ranges_log_fn_t log_fn);
void *process_sigcommon_alloc_init_body_result(
	unsigned long sigcommon_size, unsigned long flags,
	unsigned long use_offset, unsigned long lock_offset,
	unsigned long sigpending_offset, process_alloc_fn_t alloc_fn,
	process_free_fn_t free_fn, process_ref_set_fn_t ref_set_fn,
	process_rwlock_init_fn_t rwlock_init_fn);
int process_thread_sigpending_init_body_result(
	void *thread, unsigned long lock_offset, unsigned long sigpending_offset,
	process_rwlock_init_fn_t rwlock_init_fn);
int process_thread_alloc_init_body_result(
	void *thread, unsigned long thread_size, unsigned long refcount_offset,
	unsigned long hash_list_offset, unsigned long siblings_list_offset,
	process_ref_set_fn_t ref_set_fn);
int process_thread_sigstack_disable_body_result(
	void *thread, unsigned long sigstack_offset, unsigned long sp_offset,
	unsigned long flags_offset, unsigned long size_offset, int disable_flag);
void *process_create_thread_body_result(
	unsigned long user_pc, unsigned long requested_cpu_set_addr,
	unsigned long requested_bits, unsigned long thread_pages,
	unsigned long thread_size, unsigned long process_size,
	unsigned long vm_size, unsigned long nowait_flag,
	unsigned long kernel_stack_bytes, int cpu_set_bits, int num_processors,
	int sched_normal, int ss_disable, int current_cpu,
	void *parent_process, unsigned long process_pid_offset,
	unsigned long thread_refcount_offset,
	unsigned long thread_hash_list_offset,
	unsigned long thread_siblings_list_offset,
	unsigned long thread_cpu_set_offset,
	unsigned long thread_sched_policy_offset,
	unsigned long thread_sigcommon_offset,
	unsigned long thread_sigpendinglock_offset,
	unsigned long thread_sigpending_offset,
	unsigned long thread_sigstack_offset,
	unsigned long sigstack_sp_offset,
	unsigned long sigstack_flags_offset,
	unsigned long sigstack_size_offset,
	unsigned long thread_vm_offset, unsigned long thread_proc_offset,
	unsigned long process_cpu_set_offset,
	unsigned long process_vm_offset,
	unsigned long process_main_thread_offset,
	unsigned long vm_address_space_offset,
	unsigned long address_space_cpu_set_offset,
	unsigned long address_space_cpu_set_lock_offset,
	unsigned long thread_exit_status_offset,
	unsigned long thread_spin_sleep_lock_offset,
	unsigned long thread_spin_sleep_offset,
	unsigned long sigcommon_size,
	unsigned long sigcommon_use_offset,
	unsigned long sigcommon_lock_offset,
	unsigned long sigcommon_sigpending_offset,
	process_alloc_pages_fn_t alloc_pages_fn,
	process_alloc_fn_t alloc_fn,
	process_free_fn_t free_fn,
	process_create_address_space_fn_t create_address_space_fn,
	process_release_address_space_fn_t release_address_space_fn,
	process_init_process_fn_t init_process_fn,
	process_init_process_vm_fn_t init_process_vm_fn,
	process_init_user_process_fn_t init_user_process_fn,
	process_default_ncpus_fn_t default_ncpus_fn,
	process_create_cpu_log_fn_t cpu_log_fn,
	process_rwlock_init_fn_t rwlock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_spin_lock_fn_t spin_lock_fn,
	process_spin_unlock_fn_t spin_unlock_fn,
	process_thread_action_fn_t free_thread_fn);
int process_address_space_pid_detach_result(int *pids, int nslots, int pid);
int process_clone_shares_vm_result(int clone_flags);
int process_clone_shares_sighand_result(int clone_flags);
int process_mckfd_should_dup_result(unsigned long dup_cb_addr);
int process_mckfd_dup_result(struct mckfd *fdp,
			     process_mckfd_dup_fn_t dup_fn);
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
int process_sigpending_drain_free_result(struct list_head *head,
					 unsigned long list_offset,
					 process_free_fn_t free_fn);
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
struct process_ptrace_traceme_offsets {
	unsigned long thread_proc_offset;
	unsigned long thread_report_proc_offset;
	unsigned long thread_report_siblings_list_offset;
	unsigned long thread_ptrace_offset;
	unsigned long thread_ptrace_debugreg_offset;
	unsigned long proc_pid_offset;
	unsigned long proc_parent_offset;
	unsigned long proc_main_thread_offset;
	unsigned long proc_children_lock_offset;
	unsigned long proc_threads_lock_offset;
	unsigned long proc_ptraced_siblings_list_offset;
	unsigned long proc_ptraced_children_list_offset;
	unsigned long proc_report_threads_list_offset;
};
struct process_ptrace_attach_offsets {
	unsigned long thread_proc_offset;
	unsigned long thread_report_proc_offset;
	unsigned long thread_report_siblings_list_offset;
	unsigned long thread_ptrace_debugreg_offset;
	unsigned long proc_pid_offset;
	unsigned long proc_parent_offset;
	unsigned long proc_main_thread_offset;
	unsigned long proc_children_lock_offset;
	unsigned long proc_threads_lock_offset;
	unsigned long proc_children_list_offset;
	unsigned long proc_siblings_list_offset;
	unsigned long proc_ptraced_siblings_list_offset;
	unsigned long proc_ptraced_children_list_offset;
	unsigned long proc_report_threads_list_offset;
};

struct process_find_thread_offsets {
	unsigned long thread_hash_list_offset;
	unsigned long thread_tid_offset;
	unsigned long thread_proc_offset;
	unsigned long proc_pid_offset;
};

struct process_find_process_offsets {
	unsigned long process_hash_list_offset;
	unsigned long process_pid_offset;
};
int process_ptrace_traceme_body_result(
	void *thread, void *proc, void *parent, void *pid1,
	const struct process_ptrace_traceme_offsets *offsets, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_alloc_debugreg_fn_t alloc_debugreg_fn,
	process_thread_action_fn_t clear_single_step_fn,
	process_thread_action_fn_t hold_thread_fn,
	process_ptrace_traceme_log_fn_t log_fn);
int process_ptrace_attach_thread_body_result(
	void *thread, void *proc,
	const struct process_ptrace_attach_offsets *offsets, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_alloc_debugreg_fn_t alloc_debugreg_fn,
	process_thread_action_fn_t clear_single_step_fn,
	process_thread_action_fn_t hold_thread_fn,
	process_ptrace_traceme_log_fn_t log_fn);
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
int process_mckfd_close_all_result(struct mckfd *head,
				   unsigned long next_offset,
				   unsigned long close_offset);
int process_mckfd_free_result(struct mckfd *fdp,
			      process_mckfd_free_fn_t free_fn);
int process_mckfd_drain_free_result(struct mckfd **headp,
				    unsigned long next_offset,
				    process_mckfd_free_fn_t free_fn);
int process_memory_range_free_result(
	struct process_vm *vm, struct vm_range *range,
	process_memory_range_free_fn_t free_fn);
int process_memory_range_log_result(
	struct process_vm *vm, struct vm_range *range, int error,
	process_memory_range_log_fn_t log_fn);
int process_memory_range_free_all_result(
	struct process_vm *vm, struct rb_root *root, unsigned long node_offset,
	process_memory_range_free_fn_t free_fn,
	process_memory_range_log_fn_t log_fn);
int process_flush_memory_body_result(
	struct process_vm *vm, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_memory_range_free_fn_t free_fn,
	process_memory_range_log_fn_t log_fn);
int process_free_all_memory_ranges_body_result(
	struct process_vm *vm, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_memory_range_free_fn_t free_fn,
	process_memory_range_log_fn_t log_fn);
int process_cpu_set_update_body_result(
	unsigned long cpu_set_addr, unsigned long lock_addr, int clear_cpu,
	int set_cpu, int cpu_set_bits, process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn);
int process_cpu_set_public_result(
	int cpu, unsigned long cpu_set_addr, unsigned long lock_addr,
	int cpu_set_bits, process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn);
int process_cpu_clear_public_result(
	int cpu, unsigned long cpu_set_addr, unsigned long lock_addr,
	int cpu_set_bits, process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn);
int process_cpu_clear_and_set_public_result(
	int clear_cpu, int set_cpu, unsigned long cpu_set_addr,
	unsigned long lock_addr, int cpu_set_bits,
	process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn);
int process_ref_inc_result(void *object, unsigned long ref_offset,
			   process_ref_inc_fn_t inc_fn);
int process_hold_thread_warn_result(void *thread,
				    process_hold_thread_warn_fn_t warn_fn);
int process_ref_hold_body_result(void *object, unsigned long ref_offset,
				 process_ref_inc_fn_t inc_fn);
int process_hold_thread_body_result(
	void *thread, unsigned long status_offset, unsigned long refcount_offset,
	process_ref_inc_fn_t inc_fn, process_hold_thread_warn_fn_t warn_fn);
void *process_current_resource_set_result(
	process_current_resource_set_fn_t current_resource_set_fn);
int process_resource_process_action_result(
	void *resource_set, void *process,
	process_resource_process_action_fn_t action_fn);
int process_process_action_result(void *process,
				  process_process_action_fn_t action_fn);
int process_resource_set_action_result(
	void *resource_set, process_resource_set_action_fn_t action_fn);
int process_thread_action_result(void *thread,
				 process_thread_action_fn_t action_fn);
int process_thread_profile_result(void *thread, void *process,
				  process_thread_profile_fn_t profile_fn);
int process_vm_action_result(void *vm, process_vm_action_fn_t action_fn);
int process_policy_free_result(void *policy,
			       process_policy_free_fn_t policy_free_fn);
int process_vm_free_cb_result(void *vm, void *opt,
			      process_vm_free_cb_fn_t free_cb);
unsigned long process_spin_lock_result(unsigned long lock_addr,
				       process_spin_lock_fn_t lock_fn);
int process_spin_unlock_result(unsigned long lock_addr,
			       unsigned long irqstate,
			       process_spin_unlock_fn_t unlock_fn);
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
int process_vm_policy_drain_free_result(struct rb_root *root,
					unsigned long node_offset,
					process_policy_free_fn_t free_fn);
int process_detach_address_space_pid_result(
	void *address_space, int pid, process_detach_address_space_fn_t detach_fn);
int process_release_process_action_result(
	void *process, process_release_process_fn_t release_fn);
int process_release_vm_detach_process_result(
	struct process_vm *vm, unsigned long address_space_offset,
	unsigned long proc_offset, unsigned long pid_offset,
	unsigned long proc_vm_offset,
	process_detach_address_space_fn_t detach_fn,
	process_release_process_fn_t release_fn);
int process_release_fp_regs_result(struct thread *thread,
				   process_release_fp_regs_fn_t release_fp_fn);
int process_destroy_thread_optional_cleanup_result(
	struct thread *thread, unsigned long debugreg_offset,
	unsigned long recvsig_offset, unsigned long sendsig_offset,
	unsigned long fp_regs_offset, unsigned long coredump_regs_offset,
	process_optional_free_fn_t free_fn,
	process_release_fp_regs_fn_t release_fp_fn);
int process_release_sigcommon_body_result(
	void *sigcommon, int dec_and_test, int sigpending_empty,
	unsigned long sigpending_offset, unsigned long pending_list_offset,
	process_free_fn_t free_fn);
int process_release_sigcommon_public_body_result(
	void *sigcommon, unsigned long use_offset,
	unsigned long sigpending_offset, unsigned long pending_list_offset,
	process_ref_dec_and_test_fn_t dec_fn, process_free_fn_t free_fn);
int process_release_tid_body_result(
	void *tids, int nr_tids, unsigned long tid_stride,
	unsigned long tid_thread_offset, void *thread, int thread_tid,
	process_tid_log_fn_t log_fn);
int process_tid_log_result(int old_tid, void *thread, int new_tid,
			   process_tid_log_fn_t log_fn);
int process_replace_tid_body_result(
	void *tids, int nr_tids, unsigned long tid_stride,
	unsigned long tid_offset, unsigned long tid_thread_offset,
	void *thread, int old_tid, int new_tid, process_tid_log_fn_t log_fn);
int process_chain_process_body_result(
	struct list_head *siblings_entry, struct list_head *children_head,
	unsigned long children_lock_addr, struct list_head *hash_entry,
	struct list_head *hash_head, unsigned long hash_lock_addr,
	void *lock_node, process_mcs_rwlock_fn_t lock_fn,
	process_mcs_rwlock_fn_t unlock_fn);
int process_chain_thread_body_result(
	struct list_head *siblings_entry, struct list_head *threads_head,
	unsigned long threads_lock_addr, struct list_head *hash_entry,
	struct list_head *hash_head, unsigned long hash_lock_addr, void *vm,
	unsigned long vm_refcount_offset, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_ref_inc_fn_t ref_inc_fn);
int process_destroy_thread_body_result(
	void *thread, unsigned long thread_proc_offset,
	unsigned long thread_vm_offset, unsigned long thread_cpu_id_offset,
	unsigned long thread_siblings_list_offset,
	unsigned long thread_uti_state_offset,
	unsigned long thread_uti_refill_tid_offset,
	unsigned long thread_sigpending_offset,
	unsigned long thread_sigcommon_offset,
	unsigned long proc_threads_lock_offset, unsigned long proc_tids_offset,
	unsigned long proc_main_thread_offset,
	unsigned long vm_address_space_offset,
	unsigned long address_space_cpu_set_offset,
	unsigned long address_space_cpu_set_lock_offset,
	unsigned long pending_list_offset,
	unsigned long debugreg_offset, unsigned long recvsig_offset,
	unsigned long sendsig_offset, unsigned long fp_regs_offset,
	unsigned long coredump_regs_offset, int cpu_set_bits, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_thread_action_fn_t hash_detach_fn,
	process_thread_action_fn_t time_account_fn,
	process_thread_proc_action_fn_t release_tid_fn,
	process_thread_tid_action_fn_t replace_tid_fn,
	process_spin_lock_fn_t cpu_lock_fn,
	process_spin_unlock_fn_t cpu_unlock_fn,
	process_optional_free_fn_t free_fn,
	process_release_fp_regs_fn_t release_fp_fn,
	process_thread_action_fn_t release_sigcommon_fn,
	process_thread_action_fn_t free_thread_pages_fn);
void *process_find_thread_body_result(
	struct list_head *hash_head, unsigned long hash_lock_addr, void *lock_node,
	int pid, int tid, const struct process_find_thread_offsets *offsets,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_thread_action_fn_t hold_fn);
void *process_find_process_body_result(
	struct list_head *hash_head, unsigned long hash_lock_addr, void *lock_node,
	int pid, const struct process_find_process_offsets *offsets,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn);
int process_unlock_found_process_result(
	void *process, unsigned long hash_lock_addr, void *lock_node,
	process_mcs_rwlock_fn_t unlock_fn);
int process_release_thread_body_result(
	void *thread, unsigned long refcount_offset, unsigned long vm_offset,
	unsigned long proc_offset, process_ref_dec_and_test_fn_t dec_fn,
	process_thread_profile_fn_t profile_fn,
	process_thread_action_fn_t procfs_delete_fn,
	process_thread_action_fn_t destroy_thread_fn,
	process_vm_action_fn_t release_vm_fn);
int process_release_vm_body_result(
	void *vm, unsigned long refcount_offset, unsigned long proc_offset,
	unsigned long proc_mckfd_offset, unsigned long proc_mckfd_lock_offset,
	unsigned long mckfd_next_offset, unsigned long mckfd_close_offset,
	unsigned long vm_free_cb_offset, unsigned long vm_opt_offset,
	unsigned long vm_address_space_offset, unsigned long proc_pid_offset,
	unsigned long proc_vm_offset, unsigned long vm_policy_tree_offset,
	unsigned long policy_node_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
	process_vm_action_fn_t flush_fn, process_vm_action_fn_t free_ranges_fn,
	process_detach_address_space_fn_t detach_fn,
	process_release_process_fn_t release_process_fn,
	process_policy_free_fn_t policy_free_fn, process_free_fn_t free_vm_fn);

#endif /* MCKERNEL_PROCESS_HELPERS_H */
