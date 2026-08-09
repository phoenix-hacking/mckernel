/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_HOST_HELPERS_H
#define MCKERNEL_HOST_HELPERS_H

struct ikc_scd_packet;
struct ihk_ikc_channel_desc;
struct ihk_ikc_connect_param;
struct perf_ctrl_desc;
struct program_load_desc;

typedef void (*host_ikc_packet_send_fn_t)(void *channel,
					  struct ikc_scd_packet *packet);
typedef int (*host_ikc_packet_handler_fn_t)(
		struct ihk_ikc_channel_desc *channel, void *packet, void *os);
typedef int (*host_ikc_connect_fn_t)(struct ihk_ikc_connect_param *param);
typedef void (*host_delay_fn_t)(unsigned long usec);
typedef void (*host_set_current_ikc2linux_fn_t)(void *channel);
typedef void (*host_ikc_set_regular_channel_fn_t)(void *channel, int cpu);
typedef void (*host_init_ikc_log_fn_t)(int event);
typedef void (*host_panic_fn_t)(void);
typedef int (*host_monitor_status_fn_t)(int cpu);
typedef int (*host_prepare_process_fn_t)(unsigned long rphys);
typedef int (*host_perf_init_raw_fn_t)(int counter, unsigned int config,
				       int mode);
typedef int (*host_perf_stop_fn_t)(unsigned long counter_mask, int flags);
typedef int (*host_perf_reset_fn_t)(int counter);
typedef int (*host_perf_start_fn_t)(unsigned long counter_mask);
typedef unsigned long (*host_perf_read_fn_t)(int counter);
typedef void (*host_perf_unexpected_fn_t)(void);
typedef unsigned long (*host_map_memory_fn_t)(void *os, unsigned long phys,
					      unsigned long size);
typedef void *(*host_map_virtual_fn_t)(unsigned long phys, int npages,
				       int attr);
typedef void *(*host_prepare_map_virtual_fn_t)(unsigned long phys, int npages,
					       unsigned long attr);
typedef void (*host_unmap_virtual_fn_t)(void *addr, int npages);
typedef void (*host_unmap_memory_fn_t)(void *os, unsigned long phys,
				       unsigned long size);
typedef int (*host_cpu_rw_register_fn_t)(void *desc, int op);
typedef int (*host_cleanup_process_fn_t)(int pid);
typedef void (*host_terminate_host_fn_t)(int pid, void *thread);
typedef void (*host_cleanup_process_log_fn_t)(int pid,
					      unsigned long thread_arg);
typedef int (*host_cleanup_fd_fn_t)(int pid, int fd);
typedef void (*host_cleanup_fd_log_fn_t)(int pid, unsigned long fd, int err);
typedef unsigned long (*host_do_kill_fn_t)(int pid, int tid, int sig,
					   void *info);
typedef void (*host_send_signal_log_fn_t)(int pid, int tid, int sig, int rc);
typedef void *(*host_find_thread_fn_t)(int pid, int tid);
typedef void (*host_wakeup_thread_fn_t)(void *thread);
typedef void (*host_thread_unlock_fn_t)(void *thread);
typedef void (*host_wake_syscall_log_fn_t)(int tid, int found);
typedef void (*host_debug_log_fn_t)(unsigned long code);
typedef void (*host_debug_log_print_fn_t)(unsigned long code);
typedef int (*host_thread_profile_enabled_fn_t)(void *thread);
typedef unsigned long (*host_timestamp_fn_t)(void);
typedef void (*host_preempt_fn_t)(void);
typedef void (*host_remote_page_fault_fn_t)(void *thread,
					    unsigned long fault_address,
					    unsigned long fault_reason);
typedef void (*host_profile_event_fn_t)(int event, unsigned long delta);
typedef void (*host_remote_page_fault_log_fn_t)(void *thread,
						unsigned long fault_address,
						unsigned long fault_reason);
typedef void (*host_remote_page_fault_body_fn_t)(struct ikc_scd_packet *request,
						 int err);
typedef void *(*host_alloc_fn_t)(unsigned long size, unsigned long flags);
typedef void (*host_free_fn_t)(void *ptr);
typedef void (*host_packet_copy_fn_t)(void *dst,
				      struct ikc_scd_packet *src,
				      unsigned long size);
typedef void (*host_copy_long_fn_t)(void *dst, const void *src,
				    unsigned long size);
typedef void *(*host_create_thread_fn_t)(unsigned long entry,
					 unsigned long *cpu_set,
					 unsigned long cpu_set_size);
typedef void (*host_destroy_thread_fn_t)(void *thread);
typedef int (*host_prepare_ranges_fn_t)(void *thread,
					struct program_load_desc *pn,
					struct program_load_desc *p,
					unsigned long attr, char *args, int args_len,
					char *envs, int envs_len);
typedef int (*host_nr_numa_nodes_fn_t)(void);
typedef void (*host_flush_tlb_fn_t)(void);
typedef void (*host_tofu_finalize_fn_t)(void);
typedef void (*host_prepare_process_log_fn_t)(int event, unsigned long arg0,
					      unsigned long arg1,
					      unsigned long arg2);
typedef int (*host_prepare_add_range_fn_t)(void *vm, unsigned long start,
					   unsigned long end,
					   unsigned long phys,
					   unsigned long flag,
					   int pgshift, void **rangep);
typedef void *(*host_prepare_alloc_pages_user_fn_t)(int npages,
						    unsigned long flags,
						    unsigned long virt_addr);
typedef void (*host_prepare_free_pages_user_fn_t)(void *addr, int npages);
typedef unsigned long (*host_virt_to_phys_fn_t)(void *addr);
typedef unsigned long (*host_arch_vrflag_to_ptattr_fn_t)(unsigned long flag,
							 unsigned long fault,
							 void *ptep);
typedef int (*host_pt_set_range_fn_t)(void *page_table, void *vm,
				      unsigned long start, unsigned long end,
				      unsigned long phys, unsigned long attr,
				      int pgshift, void *range, int flags);
typedef void (*host_modify_user_context_fn_t)(void *uctx, int reg,
					      unsigned long value);
typedef void (*host_prepare_ranges_log_fn_t)(int event, unsigned long arg0,
					     unsigned long arg1,
					     unsigned long arg2);
typedef int (*host_arch_map_vdso_fn_t)(void *vm);
typedef int (*host_init_process_stack_fn_t)(void *thread,
					    struct program_load_desc *pn,
					    unsigned long at_base, int argc,
					    char **argv, int envc, char **env);
typedef void (*host_prepare_args_log_fn_t)(int event, unsigned long arg0,
					   unsigned long arg1,
					   unsigned long arg2);
typedef void (*host_backlog_fn_t)(void *arg);
typedef void (*host_remote_page_fault_defer_fn_t)(void *thread, void *arg,
						  host_backlog_fn_t backlog_fn);
typedef int (*host_sched_wakeup_fn_t)(void *thread, int valid_states);
typedef void (*host_remote_page_fault_missing_log_fn_t)(int tid);
typedef void *(*host_thread_proc_fn_t)(void *thread);
typedef int (*host_current_cpu_fn_t)(void);
typedef int (*host_thread_cpu_allowed_fn_t)(void *thread, int cpuid);
typedef int (*host_thread_obtain_cpuid_fn_t)(void *thread);
typedef int (*host_proc_pid_fn_t)(void *proc);
typedef unsigned long (*host_thread_reg_fn_t)(void *thread);
typedef void (*host_schedule_invalid_log_fn_t)(void *thread);
typedef void (*host_schedule_received_log_fn_t)(void *thread, int pid,
						unsigned long pc,
						unsigned long sp,
						int cpuid);
typedef void (*host_schedule_no_cpu_log_fn_t)(void);
typedef void (*host_thread_set_tid_fn_t)(void *thread, int tid);
typedef void (*host_status_set_fn_t)(void *object, int status);
typedef void (*host_chain_thread_fn_t)(void *thread);
typedef void (*host_chain_process_fn_t)(void *proc);
typedef void (*host_runq_add_thread_fn_t)(void *thread, int cpuid);
typedef void (*host_schedule_queued_log_fn_t)(int pid, int tid, int cpuid,
						      int status);
typedef void (*host_init_ack_log_fn_t)(void);
typedef void (*host_schedule_process_log_fn_t)(unsigned long arg);
typedef int (*host_response_packet_fn_t)(void *response_channel,
					 struct ikc_scd_packet *packet);
typedef int (*host_packet_dispatch_fn_t)(struct ikc_scd_packet *packet);
typedef int (*host_remote_page_fault_dispatch_fn_t)(
		struct ikc_scd_packet *packet, void *current_thread);
typedef int (*host_procfs_request_fn_t)(struct ikc_scd_packet *packet);
typedef void (*host_sysfs_packet_fn_t)(void *channel, int msg, int err,
				       long arg1, long arg2, long arg3);
typedef void (*host_unknown_packet_log_fn_t)(struct ikc_scd_packet *packet);
typedef void (*host_release_packet_fn_t)(struct ikc_scd_packet *packet);
typedef void *(*host_current_ptr_fn_t)(void);

#define HOST_INIT_IKC_LOG_ALLOC_ERROR	1
#define HOST_INIT_IKC_LOG_TRY_CONNECT	2
#define HOST_INIT_IKC_LOG_RETRY_DOT	3
#define HOST_INIT_IKC_LOG_CONNECTED	4

#define HOST_PREPARE_LOG_BROKEN_DESC	1
#define HOST_PREPARE_LOG_INVALID_SECTIONS 2
#define HOST_PREPARE_LOG_NUM_SECTIONS	3
#define HOST_PREPARE_LOG_NUMA_BIND_ERROR 4
#define HOST_PREPARE_LOG_NUMA_NODEMASK_ERROR 5
#define HOST_PREPARE_LOG_NUMA_POLICY	6
#define HOST_PREPARE_LOG_PID_FLAGS	7
#define HOST_PREPARE_LOG_RLIMIT		8
#define HOST_PREPARE_LOG_PREPARE_ERROR	9
#define HOST_PREPARE_LOG_NEW_PROCESS	10
#define HOST_PREPARE_RANGES_LOG_AP_USER		20
#define HOST_PREPARE_RANGES_LOG_ADD_FAILED	21
#define HOST_PREPARE_RANGES_LOG_ALLOC_FAILED	22
#define HOST_PREPARE_RANGES_LOG_PT_FAILED	23
#define HOST_PREPARE_RANGES_LOG_DATA_TOO_LARGE	24
#define HOST_PREPARE_ARGS_LOG_ALLOC_FAILED	25
#define HOST_PREPARE_ARGS_LOG_ADD_FAILED	26
#define HOST_PREPARE_ARGS_LOG_ARGS_MAP_FAILED	27
#define HOST_PREPARE_ARGS_LOG_ENVS_MAP_FAILED	28
#define HOST_PREPARE_ARGS_LOG_CMDLINE_ALLOC_FAILED 29
#define HOST_PREPARE_ARGS_LOG_VDSO_FAILED	30
#define HOST_PREPARE_ARGS_LOG_INIT_STACK_FAILED	31
#define HOST_PREPARE_ARGS_LOG_CMDLINE		32

struct host_scd_dispatch_ops {
	host_init_ack_log_fn_t init_ack_log_fn;
	host_response_packet_fn_t prepare_process_fn;
	host_packet_dispatch_fn_t schedule_process_fn;
	host_packet_dispatch_fn_t wake_syscall_thread_fn;
	host_remote_page_fault_dispatch_fn_t remote_page_fault_fn;
	host_response_packet_fn_t send_signal_fn;
	host_procfs_request_fn_t procfs_request_fn;
	host_response_packet_fn_t cleanup_process_fn;
	host_response_packet_fn_t cleanup_fd_fn;
	host_packet_dispatch_fn_t debug_log_fn;
	host_sysfs_packet_fn_t sysfs_packet_fn;
	host_response_packet_fn_t perf_ctrl_fn;
	host_response_packet_fn_t cpu_rw_reg_fn;
	host_unknown_packet_log_fn_t unknown_packet_log_fn;
	host_release_packet_fn_t release_packet_fn;
};

int host_ikc_packet_send_result(void *channel, struct ikc_scd_packet *packet,
				host_ikc_packet_send_fn_t send_fn);
int host_ikc_connect_result(struct ihk_ikc_connect_param *param,
			    host_ikc_connect_fn_t connect_fn);
int host_delay_result(unsigned long usec, host_delay_fn_t delay_fn);
int host_set_current_ikc2linux_result(
		void *channel,
		host_set_current_ikc2linux_fn_t set_current_fn);
int host_ikc_set_regular_channel_result(
			void *channel, int cpu,
			host_ikc_set_regular_channel_fn_t set_regular_fn);
int host_panic_result(host_panic_fn_t panic_fn);
int host_init_ikc_log_result(int event, host_init_ikc_log_fn_t log_fn);
void *host_current_ptr_result(host_current_ptr_fn_t current_fn);
int host_monitor_status_result(int cpu,
			       host_monitor_status_fn_t monitor_status_fn);
int host_tofu_finalize_result(host_tofu_finalize_fn_t tofu_finalize_fn);
int host_prepare_process_log_result(int event, unsigned long arg0,
				    unsigned long arg1, unsigned long arg2,
				    host_prepare_process_log_fn_t log_fn);
int host_prepare_ranges_log_result(int event, unsigned long arg0,
				   unsigned long arg1, unsigned long arg2,
				   host_prepare_ranges_log_fn_t log_fn);
int host_prepare_args_log_result(int event, unsigned long arg0,
				 unsigned long arg1, unsigned long arg2,
				 host_prepare_args_log_fn_t log_fn);
int host_prepare_process_result(unsigned long rphys,
				host_prepare_process_fn_t prepare_fn);
int host_prepare_ranges_result(void *thread, struct program_load_desc *pn,
			       struct program_load_desc *p, unsigned long attr,
			       char *args, int args_len, char *envs,
			       int envs_len, host_prepare_ranges_fn_t ranges_fn);
int host_cleanup_process_result(int pid, host_cleanup_process_fn_t cleanup_fn);
int host_cleanup_fd_result(int pid, int fd, host_cleanup_fd_fn_t cleanup_fn);
unsigned long host_map_memory_result(void *os, unsigned long phys,
				     unsigned long size,
				     host_map_memory_fn_t map_memory_fn);
void *host_map_virtual_result(unsigned long phys, int npages, int attr,
			      host_map_virtual_fn_t map_virtual_fn);
void *host_prepare_map_virtual_result(unsigned long phys, int npages,
				      unsigned long attr,
				      host_prepare_map_virtual_fn_t map_virtual_fn);
int host_unmap_virtual_result(void *addr, int npages,
			      host_unmap_virtual_fn_t unmap_virtual_fn);
int host_unmap_memory_result(void *os, unsigned long phys,
			     unsigned long size,
			     host_unmap_memory_fn_t unmap_memory_fn);
int host_prepare_add_range_result(void *vm, unsigned long start,
				  unsigned long end, unsigned long phys,
				  unsigned long flag, int pgshift,
				  void **rangep,
				  host_prepare_add_range_fn_t add_range_fn);
void *host_prepare_alloc_pages_user_result(
		int npages, unsigned long flags, unsigned long virt_addr,
		host_prepare_alloc_pages_user_fn_t alloc_pages_fn);
int host_prepare_free_pages_user_result(
		void *addr, int npages,
		host_prepare_free_pages_user_fn_t free_pages_fn);
unsigned long host_virt_to_phys_result(void *addr,
				       host_virt_to_phys_fn_t virt_to_phys_fn);
unsigned long host_arch_vrflag_to_ptattr_result(
		unsigned long flag, unsigned long fault, void *ptep,
		host_arch_vrflag_to_ptattr_fn_t attr_fn);
int host_pt_set_range_result(void *page_table, void *vm,
			     unsigned long start, unsigned long end,
			     unsigned long phys, unsigned long attr, int pgshift,
			     void *range, int flags,
			     host_pt_set_range_fn_t pt_set_range_fn);
int host_modify_user_context_result(void *uctx, int reg, unsigned long value,
				    host_modify_user_context_fn_t modify_fn);
void *host_prepare_alloc_result(unsigned long size, unsigned long flags,
				host_alloc_fn_t alloc_fn);
int host_prepare_free_result(void *ptr, host_free_fn_t free_fn);
int host_prepare_copy_long_result(void *dst, const void *src,
				  unsigned long size, host_copy_long_fn_t copy_fn);
void *host_create_thread_result(unsigned long entry, unsigned long *cpu_set,
				unsigned long cpu_set_size,
				host_create_thread_fn_t create_fn);
int host_destroy_thread_result(void *thread, host_destroy_thread_fn_t destroy_fn);
int host_nr_numa_nodes_result(host_nr_numa_nodes_fn_t nr_numa_nodes_fn);
int host_flush_tlb_result(host_flush_tlb_fn_t flush_tlb_fn);
int host_arch_map_vdso_result(void *vm,
			      host_arch_map_vdso_fn_t arch_map_vdso_fn);
int host_init_process_stack_result(
		void *thread, struct program_load_desc *pn,
		unsigned long at_base, int argc, char **argv, int envc,
		char **env, host_init_process_stack_fn_t init_stack_fn);
void *host_thread_proc_result(void *thread,
			      host_thread_proc_fn_t thread_proc_fn);
int host_current_cpu_result(host_current_cpu_fn_t current_cpu_fn);
int host_thread_cpu_allowed_result(void *thread, int cpuid,
				   host_thread_cpu_allowed_fn_t cpu_allowed_fn);
int host_thread_obtain_cpuid_result(
		void *thread, host_thread_obtain_cpuid_fn_t obtain_cpuid_fn);
int host_proc_pid_result(void *proc, host_proc_pid_fn_t proc_pid_fn);
unsigned long host_thread_reg_result(void *thread,
				     host_thread_reg_fn_t thread_reg_fn);
int host_schedule_invalid_log_result(
		void *thread, host_schedule_invalid_log_fn_t log_fn);
int host_schedule_received_log_result(
		void *thread, int pid, unsigned long pc, unsigned long sp,
		int cpuid, host_schedule_received_log_fn_t log_fn);
int host_schedule_no_cpu_log_result(host_schedule_no_cpu_log_fn_t log_fn);
int host_thread_set_tid_result(void *thread, int tid,
			       host_thread_set_tid_fn_t set_tid_fn);
int host_status_set_result(void *object, int status,
			   host_status_set_fn_t status_set_fn);
int host_chain_thread_result(void *thread,
			     host_chain_thread_fn_t chain_thread_fn);
int host_chain_process_result(void *proc,
			      host_chain_process_fn_t chain_process_fn);
int host_runq_add_thread_result(void *thread, int cpuid,
				host_runq_add_thread_fn_t runq_add_fn);
int host_schedule_queued_log_result(
		int pid, int tid, int cpuid, int status,
		host_schedule_queued_log_fn_t log_fn);
int host_init_ack_log_result(host_init_ack_log_fn_t log_fn);
int host_schedule_process_log_result(struct ikc_scd_packet *request,
				     host_schedule_process_log_fn_t log_fn);
int host_thread_profile_enabled_result(
		void *thread,
		host_thread_profile_enabled_fn_t profile_enabled_fn);
unsigned long host_timestamp_result(host_timestamp_fn_t timestamp_fn);
int host_preempt_result(host_preempt_fn_t preempt_fn);
int host_remote_page_fault_process_result(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason,
		host_remote_page_fault_fn_t page_fault_fn);
int host_profile_event_result(int event, unsigned long delta,
			      host_profile_event_fn_t profile_event_fn);
int host_remote_page_fault_log_result(
		void *thread, unsigned long fault_address,
		unsigned long fault_reason,
		host_remote_page_fault_log_fn_t log_fn);
void *host_alloc_result(unsigned long size, unsigned long flags,
			host_alloc_fn_t alloc_fn);
int host_packet_copy_result(void *dst, struct ikc_scd_packet *src,
			    unsigned long size, host_packet_copy_fn_t copy_fn);
int host_remote_page_fault_defer_result(
		void *thread, void *arg, host_backlog_fn_t backlog_fn,
		host_remote_page_fault_defer_fn_t defer_fn);
int host_sched_wakeup_result(void *thread, int valid_states,
			     host_sched_wakeup_fn_t wakeup_fn);
int host_remote_page_fault_missing_log_result(
		int tid, host_remote_page_fault_missing_log_fn_t log_fn);
int host_cpu_rw_register_result(void *desc, int op,
				host_cpu_rw_register_fn_t rw_register_fn);
int host_cleanup_process_log_result(
		int pid, unsigned long thread_arg,
		host_cleanup_process_log_fn_t log_fn);
int host_terminate_host_result(int pid, void *thread,
			       host_terminate_host_fn_t terminate_fn);
int host_cleanup_fd_log_result(int pid, unsigned long fd, int err,
			       host_cleanup_fd_log_fn_t log_fn);
unsigned long host_do_kill_result(
		int pid, int tid, int sig, void *info,
		host_do_kill_fn_t do_kill_fn);
int host_send_signal_log_result(int pid, int tid, int sig, int rc,
				host_send_signal_log_fn_t log_fn);
void *host_find_thread_result(int pid, int tid,
			      host_find_thread_fn_t find_thread_fn);
int host_wakeup_thread_result(void *thread,
			      host_wakeup_thread_fn_t wakeup_fn);
int host_thread_unlock_result(void *thread,
			      host_thread_unlock_fn_t unlock_fn);
int host_wake_syscall_log_result(int tid, int found,
				 host_wake_syscall_log_fn_t log_fn);
int host_debug_log_result(unsigned long code,
			  host_debug_log_fn_t debug_fn);
int host_debug_log_print_result(unsigned long code,
				host_debug_log_print_fn_t print_fn);
int host_perf_init_raw_result(int counter, unsigned int config, int mode,
			      host_perf_init_raw_fn_t init_raw_fn);
int host_perf_stop_result(unsigned long counter_mask, int flags,
			  host_perf_stop_fn_t stop_fn);
int host_perf_reset_result(int counter, host_perf_reset_fn_t reset_fn);
int host_perf_start_result(unsigned long counter_mask,
			   host_perf_start_fn_t start_fn);
unsigned long host_perf_read_result(int counter, host_perf_read_fn_t read_fn);
int host_perf_unexpected_result(host_perf_unexpected_fn_t unexpected_fn);
int host_prepare_process_body_result(
		unsigned long rphys, int num_processors, unsigned long attr,
		unsigned long page_size, unsigned long alloc_flags,
		unsigned long user_end, unsigned long ld_task_unmapped_base,
		int sigchld, int mpol_max, int mpol_bind,
		host_monitor_status_fn_t monitor_status_fn,
		host_map_memory_fn_t map_memory_fn,
		host_prepare_map_virtual_fn_t map_virtual_fn,
		host_unmap_virtual_fn_t unmap_virtual_fn,
		host_unmap_memory_fn_t unmap_memory_fn,
		host_alloc_fn_t alloc_fn, host_free_fn_t free_fn,
		host_copy_long_fn_t copy_long_fn,
		host_create_thread_fn_t create_thread_fn,
		host_destroy_thread_fn_t destroy_thread_fn,
		host_prepare_ranges_fn_t prepare_ranges_fn,
		host_nr_numa_nodes_fn_t nr_numa_nodes_fn,
		host_flush_tlb_fn_t flush_tlb_fn,
		host_tofu_finalize_fn_t tofu_finalize_fn,
		host_prepare_process_log_fn_t log_fn);
int host_prepare_ranges_sections_result(
		void *thread, struct program_load_desc *pn,
		struct program_load_desc *p, unsigned long *at_basep,
		unsigned long page_size, unsigned long page_mask,
		unsigned long large_page_size, unsigned long large_page_mask,
		unsigned long task_unmapped_base, int page_shift,
		int large_page_shift, unsigned long alloc_nowait,
		unsigned long alloc_user, unsigned long mpol_no_bss,
		unsigned long pf_populate, int user_context_pc_reg,
		host_prepare_add_range_fn_t add_range_fn,
		host_prepare_alloc_pages_user_fn_t alloc_pages_fn,
		host_prepare_free_pages_user_fn_t free_pages_fn,
		host_virt_to_phys_fn_t virt_to_phys_fn,
		host_arch_vrflag_to_ptattr_fn_t arch_vrflag_to_ptattr_fn,
		host_pt_set_range_fn_t pt_set_range_fn,
		host_modify_user_context_fn_t modify_context_fn,
		host_prepare_ranges_log_fn_t log_fn);
int host_prepare_ranges_args_envs_result(
		void *thread, struct program_load_desc *pn,
		struct program_load_desc *p, unsigned long attr,
		char *args, int args_len, char *envs, int envs_len,
		unsigned long at_base, unsigned long page_size,
		unsigned long page_mask, int page_shift,
		unsigned long alloc_nowait,
		host_prepare_add_range_fn_t add_range_fn,
		host_prepare_alloc_pages_user_fn_t alloc_pages_fn,
		host_prepare_free_pages_user_fn_t free_pages_fn,
		host_virt_to_phys_fn_t virt_to_phys_fn,
		host_map_memory_fn_t map_memory_fn,
		host_prepare_map_virtual_fn_t map_virtual_fn,
		host_unmap_virtual_fn_t unmap_virtual_fn,
		host_unmap_memory_fn_t unmap_memory_fn,
		host_copy_long_fn_t copy_long_fn,
		host_alloc_fn_t alloc_fn, host_free_fn_t free_fn,
		host_flush_tlb_fn_t flush_tlb_fn,
		host_arch_map_vdso_fn_t arch_map_vdso_fn,
		host_init_process_stack_fn_t init_stack_fn,
		host_prepare_args_log_fn_t log_fn);
int host_schedule_process_request_result(struct ikc_scd_packet *request,
					 host_thread_proc_fn_t proc_fn,
					 host_current_cpu_fn_t current_cpu_fn,
					 host_thread_cpu_allowed_fn_t cpu_allowed_fn,
					 host_thread_obtain_cpuid_fn_t obtain_cpuid_fn,
					 host_proc_pid_fn_t proc_pid_fn,
					 host_thread_reg_fn_t pc_fn,
					 host_thread_reg_fn_t sp_fn,
					 host_schedule_invalid_log_fn_t invalid_log_fn,
					 host_schedule_received_log_fn_t received_log_fn,
					 host_schedule_no_cpu_log_fn_t no_cpu_log_fn,
					 host_thread_set_tid_fn_t set_tid_fn,
					 host_status_set_fn_t set_proc_status_fn,
					 host_status_set_fn_t set_thread_status_fn,
					 host_chain_thread_fn_t chain_thread_fn,
					 host_chain_process_fn_t chain_process_fn,
					 host_runq_add_thread_fn_t runq_add_fn,
					 host_schedule_queued_log_fn_t queued_log_fn,
					 int running_status);
int host_remote_page_fault_answer_result(void *channel,
					 struct ikc_scd_packet *request,
					 int err,
					 host_ikc_packet_send_fn_t send_fn);
int host_remote_page_fault_body_result(void *channel,
				       struct ikc_scd_packet *request,
				       int err, void *current_thread,
				       unsigned long populate_flag,
				       int profile_event,
				       host_thread_profile_enabled_fn_t profile_enabled_fn,
				       host_timestamp_fn_t timestamp_fn,
				       host_preempt_fn_t preempt_disable_fn,
				       host_remote_page_fault_fn_t page_fault_fn,
				       host_preempt_fn_t preempt_enable_fn,
				       host_profile_event_fn_t profile_event_fn,
				       host_remote_page_fault_log_fn_t log_fn,
				       host_ikc_packet_send_fn_t send_fn);
int host_remote_page_fault_current_result(
		struct ikc_scd_packet *request, int err,
		unsigned long populate_flag, int profile_event,
		host_current_ptr_fn_t response_channel_fn,
		host_current_ptr_fn_t current_thread_fn,
		host_thread_profile_enabled_fn_t profile_enabled_fn,
		host_timestamp_fn_t timestamp_fn,
		host_preempt_fn_t preempt_disable_fn,
		host_remote_page_fault_fn_t page_fault_fn,
		host_preempt_fn_t preempt_enable_fn,
		host_profile_event_fn_t profile_event_fn,
		host_remote_page_fault_log_fn_t log_fn,
		host_ikc_packet_send_fn_t send_fn);
int host_remote_page_fault_body_dispatch_result(
		struct ikc_scd_packet *request, int err,
		host_remote_page_fault_body_fn_t body_fn);
int host_remote_page_fault_request_result(struct ikc_scd_packet *request,
					  host_find_thread_fn_t find_thread_fn,
					  void *current_thread,
					  host_remote_page_fault_body_fn_t body_fn,
					  host_alloc_fn_t alloc_fn,
					  host_packet_copy_fn_t copy_fn,
					  host_remote_page_fault_defer_fn_t defer_fn,
					  host_sched_wakeup_fn_t wakeup_fn,
					  host_thread_unlock_fn_t unlock_fn,
					  host_remote_page_fault_missing_log_fn_t log_fn,
					  host_backlog_fn_t backlog_fn,
					  unsigned long packet_size,
					  unsigned long alloc_flags,
					  int interruptible_state);
int host_traditional_reply_result(void *channel,
				  struct ikc_scd_packet *request,
				  int msg, int err,
				  host_ikc_packet_send_fn_t send_fn);
int host_arg_reply_result(void *channel,
			  struct ikc_scd_packet *request,
			  int msg, int err,
			  host_ikc_packet_send_fn_t send_fn);
int host_reply_only_result(void *channel,
			   struct ikc_scd_packet *request,
			   int msg, int err,
			   host_ikc_packet_send_fn_t send_fn);
int host_perf_ctrl_result(struct perf_ctrl_desc *desc,
			  host_perf_init_raw_fn_t init_raw_fn,
			  host_perf_stop_fn_t stop_fn,
			  host_perf_reset_fn_t reset_fn,
			  host_perf_start_fn_t start_fn,
			  host_perf_read_fn_t read_fn,
			  host_perf_unexpected_fn_t unexpected_fn);
int host_perf_ctrl_request_result(void *channel,
				  struct ikc_scd_packet *request,
				  host_map_memory_fn_t map_memory_fn,
				  host_map_virtual_fn_t map_virtual_fn,
				  host_unmap_virtual_fn_t unmap_virtual_fn,
				  host_unmap_memory_fn_t unmap_memory_fn,
				  host_perf_init_raw_fn_t init_raw_fn,
				  host_perf_stop_fn_t stop_fn,
				  host_perf_reset_fn_t reset_fn,
				  host_perf_start_fn_t start_fn,
				  host_perf_read_fn_t read_fn,
				  host_perf_unexpected_fn_t unexpected_fn,
				  host_ikc_packet_send_fn_t send_fn);
int host_cpu_rw_reg_request_result(void *channel,
				   struct ikc_scd_packet *request,
				   host_map_memory_fn_t map_memory_fn,
				   host_map_virtual_fn_t map_virtual_fn,
				   host_unmap_virtual_fn_t unmap_virtual_fn,
				   host_unmap_memory_fn_t unmap_memory_fn,
				   host_cpu_rw_register_fn_t rw_register_fn,
				   host_ikc_packet_send_fn_t send_fn);
int host_cleanup_process_request_result(void *channel,
					struct ikc_scd_packet *request,
					host_cleanup_process_fn_t cleanup_fn,
					host_terminate_host_fn_t terminate_fn,
					host_cleanup_process_log_fn_t log_fn,
					host_ikc_packet_send_fn_t send_fn);
int host_cleanup_fd_request_result(void *channel,
				   struct ikc_scd_packet *request,
				   host_cleanup_fd_fn_t cleanup_fn,
				   host_cleanup_fd_log_fn_t log_fn,
				   host_ikc_packet_send_fn_t send_fn);
int host_send_signal_request_result(void *channel,
				    struct ikc_scd_packet *request,
				    host_map_memory_fn_t map_memory_fn,
				    host_map_virtual_fn_t map_virtual_fn,
				    host_unmap_virtual_fn_t unmap_virtual_fn,
				    host_unmap_memory_fn_t unmap_memory_fn,
				    host_do_kill_fn_t do_kill_fn,
				    host_send_signal_log_fn_t log_fn,
				    host_ikc_packet_send_fn_t send_fn);
int host_wake_syscall_thread_request_result(struct ikc_scd_packet *request,
					    host_find_thread_fn_t find_thread_fn,
					    host_wakeup_thread_fn_t wakeup_fn,
					    host_thread_unlock_fn_t unlock_fn,
					    host_wake_syscall_log_fn_t log_fn);
int host_debug_log_request_result(struct ikc_scd_packet *request,
				  host_debug_log_fn_t debug_fn,
				  host_debug_log_print_fn_t print_fn);
int host_response_packet_result(void *response_channel,
				struct ikc_scd_packet *packet,
				host_response_packet_fn_t response_fn);
int host_packet_dispatch_result(struct ikc_scd_packet *packet,
				host_packet_dispatch_fn_t dispatch_fn);
int host_remote_page_fault_dispatch_result(
		struct ikc_scd_packet *packet, void *current_thread,
		host_remote_page_fault_dispatch_fn_t dispatch_fn);
int host_procfs_packet_dispatch_result(struct ikc_scd_packet *packet,
				       host_procfs_request_fn_t request_fn);
int host_scd_packet_dispatch_result(void *channel,
				    struct ikc_scd_packet *packet,
				    void *response_channel,
				    void *current_thread,
				    const struct host_scd_dispatch_ops *ops,
				    unsigned long populate_flag,
				    int profile_event,
				    unsigned long packet_size,
				    unsigned long alloc_flags,
				    int interruptible_state,
				    int running_status);
int host_prepare_process_request_result(
		void *channel, struct ikc_scd_packet *request,
		host_prepare_process_fn_t prepare_fn,
		host_ikc_packet_send_fn_t send_fn);
int host_procfs_request_result(struct ikc_scd_packet *request,
			       host_procfs_request_fn_t procfs_request_fn);
int host_sysfs_packet_result(void *channel, int msg, int err,
			     long arg1, long arg2, long arg3,
			     host_sysfs_packet_fn_t sysfs_packet_fn);
int host_unknown_packet_log_result(struct ikc_scd_packet *packet,
				   host_unknown_packet_log_fn_t log_fn);
int host_release_packet_result(struct ikc_scd_packet *packet,
			       host_release_packet_fn_t release_packet_fn);
int host_release_packet_dispatch_result(
		struct ikc_scd_packet *packet,
		host_release_packet_fn_t release_packet_fn);
int host_syscall_packet_handler_result(void *channel, void *packet, void *os,
				       const struct host_scd_dispatch_ops *ops,
				       host_current_ptr_fn_t response_channel_fn,
				       host_current_ptr_fn_t current_thread_fn,
				       unsigned long populate_flag,
				       int profile_event,
				       unsigned long packet_size,
				       unsigned long alloc_flags,
				       int interruptible_state,
				       int running_status);
int host_dummy_packet_handler_result(void *channel, void *packet, void *os,
				     host_release_packet_fn_t release_packet_fn);
int host_procfs_answer_current_result(
		struct ikc_scd_packet *request, int err,
		host_current_ptr_fn_t response_channel_fn,
		host_ikc_packet_send_fn_t send_fn);
int host_init_ikc2linux_result(int linux_cpu,
			       struct ihk_ikc_channel_desc ***ikc2linuxsp,
			       int nr_linux_cores, int num_processors,
			       unsigned long packet_size,
			       unsigned long page_size,
			       unsigned long alloc_flags,
			       host_alloc_fn_t alloc_fn,
			       host_ikc_connect_fn_t connect_fn,
			       host_delay_fn_t delay_fn,
			       host_set_current_ikc2linux_fn_t set_current_fn,
			       host_ikc_packet_handler_fn_t dummy_handler_fn,
			       host_init_ikc_log_fn_t log_fn,
			       host_panic_fn_t panic_fn);
int host_init_ikc2mckernel_result(unsigned long packet_size,
				  unsigned long page_size, int processor_id,
				  host_ikc_packet_handler_fn_t handler_fn,
				  host_ikc_connect_fn_t connect_fn,
				  host_delay_fn_t delay_fn,
				  host_ikc_set_regular_channel_fn_t set_regular_fn,
				  host_init_ikc_log_fn_t log_fn);
int host_init_ikc2linux_public_result(
		int linux_cpu, struct ihk_ikc_channel_desc ***ikc2linuxsp,
		int nr_linux_cores, int num_processors,
		unsigned long packet_size, unsigned long page_size,
		unsigned long alloc_flags, host_alloc_fn_t alloc_fn,
		host_ikc_connect_fn_t connect_fn, host_delay_fn_t delay_fn,
		host_set_current_ikc2linux_fn_t set_current_fn,
		host_ikc_packet_handler_fn_t dummy_handler_fn,
		host_init_ikc_log_fn_t log_fn, host_panic_fn_t panic_fn);
int host_init_ikc2mckernel_public_result(
		unsigned long packet_size, unsigned long page_size,
		int processor_id, host_ikc_packet_handler_fn_t handler_fn,
		host_ikc_connect_fn_t connect_fn, host_delay_fn_t delay_fn,
		host_ikc_set_regular_channel_fn_t set_regular_fn,
		host_init_ikc_log_fn_t log_fn, host_panic_fn_t panic_fn);

#endif
