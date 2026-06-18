#ifndef MCCTRL_RUST_H
#define MCCTRL_RUST_H

#include <linux/types.h>
#include <linux/string.h>
#include <linux/kernel.h>

struct ikc_scd_packet;
struct mcctrl_wakeup_desc;
struct syscall_request;
struct sysfs_req_create_param;
struct sysfs_req_mkdir_param;
struct sysfs_req_symlink_param;
struct sysfs_req_lookup_param;
struct sysfs_req_unlink_param;

#ifndef FUTEX_WAIT
#define FUTEX_WAIT 0
#endif
#ifndef FUTEX_WAKE
#define FUTEX_WAKE 1
#endif
#ifndef FUTEX_REQUEUE
#define FUTEX_REQUEUE 3
#endif
#ifndef FUTEX_CMP_REQUEUE
#define FUTEX_CMP_REQUEUE 4
#endif
#ifndef FUTEX_WAKE_OP
#define FUTEX_WAKE_OP 5
#endif
#ifndef FUTEX_WAIT_BITSET
#define FUTEX_WAIT_BITSET 9
#endif
#ifndef FUTEX_WAKE_BITSET
#define FUTEX_WAKE_BITSET 10
#endif
#ifndef FUTEX_WAIT_REQUEUE_PI
#define FUTEX_WAIT_REQUEUE_PI 11
#endif
#ifndef FUTEX_CMD_MASK
#define FUTEX_CMD_MASK 0x7f
#endif
#ifndef FUTEX_PRIVATE_FLAG
#define FUTEX_PRIVATE_FLAG 128
#endif
#ifndef FUTEX_CLOCK_REALTIME
#define FUTEX_CLOCK_REALTIME 256
#endif
#ifndef IHK_OS_AUX_PERF_NUM
#define IHK_OS_AUX_PERF_NUM        0x11290100
#endif
#ifndef IHK_OS_AUX_PERF_SET
#define IHK_OS_AUX_PERF_SET        0x11290101
#endif
#ifndef IHK_OS_AUX_PERF_GET
#define IHK_OS_AUX_PERF_GET        0x11290102
#endif
#ifndef IHK_OS_AUX_PERF_ENABLE
#define IHK_OS_AUX_PERF_ENABLE     0x11290103
#endif
#ifndef IHK_OS_AUX_PERF_DISABLE
#define IHK_OS_AUX_PERF_DISABLE    0x11290104
#endif
#ifndef IHK_OS_AUX_PERF_DESTROY
#define IHK_OS_AUX_PERF_DESTROY    0x11290105
#endif
#ifndef SCD_MSG_SYSCALL_ONESIDE
#define SCD_MSG_SYSCALL_ONESIDE    0x4
#endif
#ifndef MCCTRL_IKC_INIT_LAST_CHANNEL_PORT
#define MCCTRL_IKC_INIT_LAST_CHANNEL_PORT 502
#endif

unsigned long mcctrl_align_wait_buf(unsigned long size);
int mcctrl_partition_list_evict(int len, int max_len);
int mcctrl_partition_count_mismatch(int existing, int requested);
int mcctrl_partition_join_allowed(int joined, int total);
int mcctrl_partition_last_process(int left);
int mcctrl_partition_wait_required(int left, int woke_any, int woke_self);
unsigned int mcctrl_partition_wait_timeout_msecs(int nr_processes);
int mcctrl_partition_wake_next(int left);
unsigned long mcctrl_release_user_space_len(unsigned long start,
					    unsigned long end);
int mcctrl_control_request_needs_root(unsigned int request);
int mcctrl_control_perm(unsigned int request, unsigned int euid);
int mcctrl_cpu_register_copyback(int op, int read_op);
int mcctrl_ikc_free_addrs_owner(int free_addrs_count);
int mcctrl_ikc_desc_free_at_put(int allocated_internally);
int mcctrl_ikc_wait_mode(long timeout);
unsigned long mcctrl_ikc_busy_timeout_msecs(long timeout);
int mcctrl_ikc_wait_abort_return(int wait_ret);
int mcctrl_ikc_release_packet_after_handler(int msg);
int mcctrl_ikc_cpu_nonnegative(int cpu);
int mcctrl_ikc_cpu_index_valid(int cpu, int num_channels);
int mcctrl_ikc_linux_cpu_valid(int linux_cpu, int nr_cpu_ids);
int mcctrl_ikc_init_uses_last_channel(int port);
int mcctrl_ikc_cpu_count_valid(int n_cpus);
int mcctrl_lwk_to_linux_index(const int *mapping, int count, int index);
int mcctrl_linux_to_lwk_index(const int *mapping, int count, int linux_id);
void mcctrl_fill_sequential_bitset(unsigned long *bits, int bit_count,
				   int word_count, int bits_per_word);
int mcctrl_read_buffer_status(char *buf, unsigned long size, long bytes_read);
int mcctrl_parse_long(const char *buf, long *value_out);
int mcctrl_pci_realpath_valid(const char *path);
int mcctrl_ptr_hash(const void *ptr, unsigned long mask);
int mcctrl_ptr_eq(const void *a, const void *b);
int mcctrl_file_to_pidfd_lookup_match(const void *entry_filp,
				      const void *filp,
				      const void *entry_group_leader,
				      const void *group_leader);
int mcctrl_file_to_pidfd_remove_match(const void *entry_filp,
				      const void *filp, const void *entry_os,
				      const void *os,
				      const void *entry_group_leader,
				      const void *group_leader, int entry_fd,
				      int fd);
int mcctrl_tofu_dev_path(const char *path);
unsigned long mcctrl_tofu_dev_tail_offset(void);
void mcctrl_tofu_dev_name_copy(char *dst, unsigned long dst_size,
			       const char *path);
int mcctrl_tofu_cq_path_parse(const char *path, int *tni_out, int *cq_out);
int mcctrl_sysfs_path_error(const char *path, long written,
			    unsigned long path_size);
int mcctrl_binfmt_skip_path(const char *path);
int mcctrl_path_allowed(const char *file, const char *list);
int mcctrl_pager_treat_as_device_path(const char *path);
int mcctrl_pager_should_populate_path(const char *path);
int mcctrl_fs_is_tmpfs(const char *name);
int mcctrl_fs_is_proc(const char *name);
int mcctrl_special_char_device(unsigned int major, unsigned int minor);
int mcctrl_format_mcos_name(char *buf, unsigned long buflen, int osnum);
int mcctrl_format_decimal_name(char *buf, unsigned long buflen, int value);
int mcctrl_futex_cmd(int op);
int mcctrl_futex_is_private(int op);
int mcctrl_futex_clock_realtime(int op);
int mcctrl_futex_realtime_cmd_valid(int cmd);
int mcctrl_futex_wait_uses_timeout(int cmd);
int mcctrl_futex_arg3_is_val2(int cmd);
const char *mcctrl_futex_op_label(int cmd);
int mcctrl_ikc_send_wait_array(void *os, int cpu,
			       struct ikc_scd_packet *pisp, long timeout,
			       struct mcctrl_wakeup_desc *desc,
			       int *do_frees, int free_addrs_count,
			       void **free_addrs);

#ifdef MCCTRL_RUST_HELPERS
unsigned long mcctrl_align_wait_buf_result(unsigned long size);
int mcctrl_partition_list_evict_result(int len, int max_len);
int mcctrl_partition_count_mismatch_result(int existing, int requested);
int mcctrl_partition_join_allowed_result(int joined, int total);
int mcctrl_partition_last_process_result(int left);
int mcctrl_partition_wait_required_result(int left, int woke_any, int woke_self);
unsigned int mcctrl_partition_wait_timeout_msecs_result(int nr_processes);
int mcctrl_partition_wake_next_result(int left);
unsigned long mcctrl_release_user_space_len_result(unsigned long start, unsigned long end);
int mcctrl_zero_mckernel_pages_step_result(unsigned long node_addr,
					   unsigned long to_zero_list_offset,
					   unsigned long zeroed_list_offset,
					   unsigned long nr_to_zero_pages_offset,
					   unsigned long free_chunk_addr_offset,
					   unsigned long free_chunk_size_offset,
					   unsigned long free_chunk_list_offset,
					   unsigned long free_chunk_sizeof,
					   unsigned long phys_to_virt_base,
					   unsigned int page_shift,
					   unsigned long *addr_out,
					   unsigned long *size_out);
void mcctrl_zero_mckernel_pages_finish_result(unsigned long node_addr,
					     unsigned long zeroing_workers_offset);
int mcctrl_control_request_needs_root_result(unsigned int request);
int mcctrl_control_perm_result(unsigned int request, unsigned int euid);
typedef long (*mcctrl_control_dispatch_fn_t)(unsigned long os,
					    unsigned long arg,
					    unsigned long file);
struct mcctrl_control_dispatch_ops {
	mcctrl_control_dispatch_fn_t prepare_image;
	mcctrl_control_dispatch_fn_t transfer_image;
	mcctrl_control_dispatch_fn_t start_image;
	mcctrl_control_dispatch_fn_t wait_syscall;
	mcctrl_control_dispatch_fn_t ret_syscall;
	mcctrl_control_dispatch_fn_t load_syscall;
	mcctrl_control_dispatch_fn_t send_signal;
	mcctrl_control_dispatch_fn_t get_cpu;
	mcctrl_control_dispatch_fn_t create_ppd;
	mcctrl_control_dispatch_fn_t get_nodes;
	mcctrl_control_dispatch_fn_t get_cpuset;
	mcctrl_control_dispatch_fn_t strncpy_from_user;
	mcctrl_control_dispatch_fn_t open_exec;
	mcctrl_control_dispatch_fn_t close_exec;
	mcctrl_control_dispatch_fn_t prepare_dma;
	mcctrl_control_dispatch_fn_t free_dma;
	mcctrl_control_dispatch_fn_t get_cred;
	mcctrl_control_dispatch_fn_t get_credv;
	mcctrl_control_dispatch_fn_t sys_mount;
	mcctrl_control_dispatch_fn_t sys_umount;
	mcctrl_control_dispatch_fn_t sys_unshare;
	mcctrl_control_dispatch_fn_t uti_get_ctx;
	mcctrl_control_dispatch_fn_t uti_switch_ctx;
	mcctrl_control_dispatch_fn_t sig_thread;
	mcctrl_control_dispatch_fn_t syscall_thread;
	mcctrl_control_dispatch_fn_t terminate_thread;
	mcctrl_control_dispatch_fn_t release_user_space;
	mcctrl_control_dispatch_fn_t get_num_pool_threads;
	mcctrl_control_dispatch_fn_t uti_attr;
	mcctrl_control_dispatch_fn_t debug_log;
	mcctrl_control_dispatch_fn_t perf_num;
	mcctrl_control_dispatch_fn_t perf_set;
	mcctrl_control_dispatch_fn_t perf_get;
	mcctrl_control_dispatch_fn_t perf_enable;
	mcctrl_control_dispatch_fn_t perf_disable;
	mcctrl_control_dispatch_fn_t perf_destroy;
	mcctrl_control_dispatch_fn_t getrusage;
};
long mcctrl_control_dispatch_body_result(
	unsigned long os, unsigned int request, unsigned long arg,
	unsigned long file, const struct mcctrl_control_dispatch_ops *ops);
typedef int (*mcctrl_control_ikc_send_fn_t)(unsigned long os, int cpu,
					    struct ikc_scd_packet *packet);
typedef void *(*mcctrl_control_get_ptr_fn_t)(unsigned long os);
typedef void *(*mcctrl_control_ptr_field_fn_t)(void *ptr);
typedef int (*mcctrl_control_ptr_int_fn_t)(void *ptr);
typedef void (*mcctrl_control_log_fn_t)(int stage);
long mcctrl_control_debug_log_body_result(
	unsigned long os, unsigned long arg,
	mcctrl_control_ikc_send_fn_t send);
long mcctrl_control_get_cpu_body_result(
	unsigned long os, mcctrl_control_get_ptr_fn_t get_cpu_info,
	mcctrl_control_ptr_int_fn_t cpu_info_n_cpus,
	mcctrl_control_log_fn_t log_error);
long mcctrl_control_get_nodes_body_result(
	unsigned long os, mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_ptr_field_fn_t usrdata_mem_info,
	mcctrl_control_ptr_int_fn_t mem_info_n_nodes,
	mcctrl_control_log_fn_t log_error);
typedef long (*mcctrl_in_kernel_req_fn_t)(unsigned long os,
					  struct syscall_request *req);
typedef long (*mcctrl_in_kernel_clear_pte_fn_t)(unsigned long start,
						unsigned long len);
typedef long (*mcctrl_in_kernel_remap_fn_t)(unsigned long start,
					    unsigned long len, int prot);
typedef void (*mcctrl_in_kernel_zero_pages_fn_t)(unsigned long arg);
typedef long (*mcctrl_in_kernel_writecore_fn_t)(unsigned long os,
						unsigned long rcoretable,
						int chunks,
						unsigned long offset,
						unsigned long filename);
typedef long (*mcctrl_in_kernel_sched_fn_t)(int arg);
typedef void (*mcctrl_in_kernel_return_fn_t)(unsigned long os,
					     struct ikc_scd_packet *packet,
					     long ret, int stid);
typedef void (*mcctrl_in_kernel_release_fn_t)(struct ikc_scd_packet *packet);
typedef long (*mcctrl_pager_create_fn_t)(unsigned long os, int fd,
					 unsigned long result_pa);
typedef long (*mcctrl_pager_release_fn_t)(unsigned long os,
					  unsigned long handle,
					  unsigned long sref);
typedef long (*mcctrl_pager_io_fn_t)(unsigned long os,
				     unsigned long handle,
				     unsigned long off,
				     unsigned long size,
				     unsigned long rpa);
typedef long (*mcctrl_pager_map_fn_t)(unsigned long os, int fd,
				      unsigned long len, unsigned long off,
				      unsigned long result_rpa,
				      int prot_and_flags);
typedef long (*mcctrl_pager_pfn_fn_t)(unsigned long os,
				      unsigned long handle,
				      unsigned long off,
				      unsigned long ppfn_rpa);
typedef long (*mcctrl_pager_unmap_fn_t)(unsigned long os,
					unsigned long handle);
typedef long (*mcctrl_pager_mlock_list_fn_t)(unsigned long os,
					     unsigned long start,
					     unsigned long end,
					     unsigned long addr,
					     int nent);
typedef void (*mcctrl_pager_unknown_fn_t)(unsigned long request, long ret);
struct mcctrl_pager_call_ops {
	mcctrl_pager_create_fn_t create;
	mcctrl_pager_release_fn_t release;
	mcctrl_pager_io_fn_t read;
	mcctrl_pager_io_fn_t write;
	mcctrl_pager_map_fn_t map;
	mcctrl_pager_pfn_fn_t pfn;
	mcctrl_pager_unmap_fn_t unmap;
	mcctrl_pager_mlock_list_fn_t mlock_list;
	mcctrl_pager_unknown_fn_t unknown;
};
long mcctrl_pager_call_irq_body_result(
	unsigned long os, struct syscall_request *req,
	const struct mcctrl_pager_call_ops *ops);
long mcctrl_pager_call_body_result(
	unsigned long os, struct syscall_request *req,
	const struct mcctrl_pager_call_ops *ops);
typedef int (*mcctrl_remote_page_fault_send_fn_t)(
	unsigned long os, int cpu, struct ikc_scd_packet *packet);
typedef void (*mcctrl_remote_page_fault_log_fn_t)(
	int stage, int pid, int error, unsigned long fault_addr,
	unsigned long reason);
int mcctrl_remote_page_fault_body_result(
	unsigned long os, void *fault_addr, unsigned long reason,
	struct ikc_scd_packet *packet,
	mcctrl_remote_page_fault_send_fn_t send_wait,
	mcctrl_remote_page_fault_log_fn_t log_event);
typedef void (*mcctrl_user_space_lock_fn_t)(void);
typedef void *(*mcctrl_user_space_find_vma_fn_t)(unsigned long addr);
typedef unsigned long (*mcctrl_user_space_vma_ulong_fn_t)(void *vma);
typedef void (*mcctrl_user_space_vma_void_fn_t)(void *vma);
typedef int (*mcctrl_user_space_vma_zap_fn_t)(
	void *vma, unsigned long addr, unsigned long len);
typedef void (*mcctrl_user_space_vma_zap_range_fn_t)(
	void *vma, unsigned long addr, unsigned long len);
typedef int (*mcctrl_user_space_munmap_fn_t)(
	unsigned long addr, unsigned long len);
typedef void (*mcctrl_user_space_error_log_fn_t)(int error);
struct mcctrl_clear_pte_range_ops {
	mcctrl_user_space_lock_fn_t read_lock;
	mcctrl_user_space_lock_fn_t read_unlock;
	mcctrl_user_space_find_vma_fn_t find_vma;
	mcctrl_user_space_vma_ulong_fn_t vma_start;
	mcctrl_user_space_vma_ulong_fn_t vma_end;
	mcctrl_user_space_vma_ulong_fn_t vma_flags;
	mcctrl_user_space_vma_void_fn_t set_rw_exec;
	mcctrl_user_space_vma_zap_fn_t zap_vma_ptes;
	mcctrl_user_space_vma_zap_range_fn_t zap_page_range;
};
int mcctrl_clear_pte_range_body_result(
	unsigned long start, unsigned long len, unsigned long vm_pfnmap,
	int legacy_zap, const struct mcctrl_clear_pte_range_ops *ops);
struct mcctrl_user_space_release_ops {
	mcctrl_user_space_find_vma_fn_t find_vma;
	mcctrl_user_space_vma_ulong_fn_t vma_start;
	mcctrl_user_space_vma_ulong_fn_t vma_end;
	mcctrl_user_space_munmap_fn_t munmap;
	mcctrl_user_space_error_log_fn_t log_error;
};
int mcctrl_user_space_release_body_result(
	unsigned long start, unsigned long len,
	const struct mcctrl_user_space_release_ops *ops);
struct mcctrl_in_kernel_syscall_ops {
	mcctrl_in_kernel_req_fn_t pager_irq;
	mcctrl_in_kernel_req_fn_t pager;
	mcctrl_in_kernel_clear_pte_fn_t clear_pte;
	mcctrl_in_kernel_remap_fn_t remap;
	mcctrl_in_kernel_zero_pages_fn_t zero_pages;
	mcctrl_in_kernel_writecore_fn_t writecore;
	mcctrl_in_kernel_sched_fn_t sched_same_owner;
	mcctrl_in_kernel_sched_fn_t sched_root;
	mcctrl_in_kernel_req_fn_t tofu_close;
	mcctrl_in_kernel_return_fn_t return_syscall;
	mcctrl_in_kernel_release_fn_t release_packet;
};
int mcctrl_in_kernel_irq_syscall_body_result(
	unsigned long os, struct ikc_scd_packet *packet,
	const struct mcctrl_in_kernel_syscall_ops *ops, long *ret_out);
int mcctrl_in_kernel_syscall_body_result(
	unsigned long os, struct ikc_scd_packet *packet,
	const struct mcctrl_in_kernel_syscall_ops *ops, long *ret_out);
int mcctrl_cpu_register_copyback_result(int op, int read_op);
typedef void *(*mcctrl_control_alloc_fn_t)(unsigned long size);
typedef void (*mcctrl_control_free_fn_t)(void *ptr);
typedef unsigned long (*mcctrl_control_virt_to_phys_fn_t)(void *ptr);
typedef int (*mcctrl_control_cpu_register_send_wait_fn_t)(
	unsigned long os, int cpu, struct ikc_scd_packet *packet,
	long timeout, int *do_free, void *desc);
typedef void (*mcctrl_control_cpu_register_error_log_fn_t)(
	int stage, int cpu, int ret);
typedef void (*mcctrl_control_cpu_register_done_log_fn_t)(
	int op, int is_read, int cpu, unsigned long addr_ext,
	unsigned long val);
int mcctrl_control_cpu_register_body_result(
	unsigned long os, int cpu, struct ihk_os_cpu_register *desc, int op,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_ptr_int_fn_t usrdata_cpu_count,
	mcctrl_control_alloc_fn_t alloc_desc,
	mcctrl_control_free_fn_t free_desc,
	mcctrl_control_virt_to_phys_fn_t virt_to_phys,
	mcctrl_control_cpu_register_send_wait_fn_t send_wait,
	mcctrl_control_cpu_register_error_log_fn_t log_error,
	mcctrl_control_cpu_register_done_log_fn_t log_done);
typedef int (*mcctrl_control_validate_os_fn_t)(unsigned long os);
typedef int (*mcctrl_control_current_int_fn_t)(void);
typedef void *(*mcctrl_control_current_task_fn_t)(void);
typedef void *(*mcctrl_control_get_ppd_fn_t)(void *usrdata, int pid);
typedef void *(*mcctrl_control_get_ptd_fn_t)(void *ppd, void *task);
typedef void (*mcctrl_control_put_fn_t)(void *ptr);
typedef int (*mcctrl_control_packet_ref_fn_t)(void *packet);
typedef int (*mcctrl_control_channel_read_cpu_fn_t)(void *usrdata,
						   int packet_ref);
typedef void (*mcctrl_control_request_cpu_error_log_fn_t)(
	int stage, unsigned long os, int pid, int tid);
typedef void (*mcctrl_control_request_cpu_ptd_log_fn_t)(
	int stage, int tid, void *ptd);
typedef void (*mcctrl_control_request_cpu_result_log_fn_t)(
	unsigned long os, int cpu);
int mcctrl_control_get_request_os_cpu_body_result(
	unsigned long os, int *ret_cpu,
	mcctrl_control_validate_os_fn_t validate_os,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_current_int_fn_t current_pid,
	mcctrl_control_current_int_fn_t current_tid,
	mcctrl_control_current_task_fn_t current_task,
	mcctrl_control_get_ppd_fn_t get_ppd,
	mcctrl_control_put_fn_t put_ppd,
	mcctrl_control_get_ptd_fn_t get_ptd,
	mcctrl_control_put_fn_t put_ptd,
	mcctrl_control_ptr_field_fn_t ptd_data,
	mcctrl_control_packet_ref_fn_t packet_ref,
	mcctrl_control_channel_read_cpu_fn_t channel_read_cpu,
	mcctrl_control_request_cpu_error_log_fn_t log_error,
	mcctrl_control_request_cpu_ptd_log_fn_t log_ptd,
	mcctrl_control_request_cpu_result_log_fn_t log_result);
typedef int (*mcctrl_control_copy_user_fn_t)(void *dst, const void *src,
					     unsigned long size);
typedef void *(*mcctrl_control_os_to_dev_fn_t)(unsigned long os);
typedef unsigned long (*mcctrl_control_map_memory_fn_t)(void *dev,
	unsigned long phys, unsigned long size);
typedef void *(*mcctrl_control_map_virtual_fn_t)(void *dev,
	unsigned long phys, unsigned long size);
typedef void (*mcctrl_control_unmap_virtual_fn_t)(void *dev, void *virt,
	unsigned long size);
typedef void (*mcctrl_control_unmap_memory_fn_t)(void *dev,
	unsigned long phys, unsigned long size);
typedef void (*mcctrl_control_transfer_log_fn_t)(int stage);
typedef void (*mcctrl_control_load_log_fn_t)(void *rpm, unsigned long size);
typedef int (*mcctrl_control_cred_value_fn_t)(void);
typedef void *(*mcctrl_control_alloc_page_fn_t)(void);
typedef void (*mcctrl_control_free_page_fn_t)(void *ptr);
typedef long (*mcctrl_control_strncpy_from_user_fn_t)(
	void *dst, const void *src, unsigned long size);
typedef int (*mcctrl_control_drop_exec_fn_t)(unsigned long os, int pid);
typedef void (*mcctrl_control_destroy_ppd_log_fn_t)(
	int stage, int pid, void *ppd);
typedef void *(*mcctrl_control_new_info_fn_t)(unsigned long os, void *file);
typedef void (*mcctrl_control_set_info_pid_fn_t)(void *info, int pid);
typedef void (*mcctrl_control_register_release_fn_t)(void *file, void *info);
typedef void (*mcctrl_control_set_private_fn_t)(void *file, void *info);
typedef void *(*mcctrl_control_file_ptr_fn_t)(void *file);
typedef int (*mcctrl_control_desc_int_fn_t)(void *desc);
typedef unsigned long (*mcctrl_control_desc_ulong_fn_t)(void *desc);
typedef unsigned long (*mcctrl_control_info_ulong_fn_t)(void *info);
typedef void (*mcctrl_control_set_start_info_fn_t)(
	void *info, int pid, int cpu, unsigned long user_start,
	unsigned long user_end, unsigned long prepare_thread);
typedef void (*mcctrl_control_ptr_ulong_fn_t)(void *ptr, unsigned long value);
typedef void (*mcctrl_control_os_cpu_void_fn_t)(unsigned long os, int cpu);
typedef int (*mcctrl_control_schedule_send_fn_t)(
	unsigned long os, int cpu, unsigned long rprocess);
typedef void (*mcctrl_control_start_log_fn_t)(int stage, int ret);
typedef void (*mcctrl_control_signal_log_fn_t)(int stage, int ret);
typedef void (*mcctrl_control_return_syscall_fn_t)(
	unsigned long os, void *ppd, void *packet, long ret, int tid);
typedef void (*mcctrl_control_ret_syscall_log_fn_t)(
	int stage, int pid, int tid);
typedef void (*mcctrl_control_terminate_thread_log_fn_t)(
	int stage, int pid, int tid, void *ptr, int value);
typedef unsigned long (*mcctrl_control_current_ulong_fn_t)(void);
typedef void (*mcctrl_control_uti_log_fn_t)(int stage);
typedef int (*mcctrl_control_get_order_fn_t)(unsigned long size);
typedef unsigned long (*mcctrl_control_alloc_pages_fn_t)(int order);
typedef void (*mcctrl_control_free_pages_fn_t)(unsigned long addr, int order);
typedef unsigned long (*mcctrl_control_phys_to_virt_fn_t)(unsigned long phys);
typedef void *(*mcctrl_control_prepare_creds_fn_t)(void);
typedef void (*mcctrl_control_cap_raise_admin_fn_t)(void *cred);
typedef const void *(*mcctrl_control_override_creds_fn_t)(void *cred);
typedef void (*mcctrl_control_revert_creds_fn_t)(const void *cred);
typedef int (*mcctrl_control_mount_fn_t)(char *dev_name, char *dir_name,
					 char *type, unsigned long flags,
					 void *data);
typedef int (*mcctrl_control_umount_fn_t)(char *dir_name, int flags);
typedef int (*mcctrl_control_unshare_fn_t)(unsigned long flags);
typedef long (*mcctrl_control_clear_pte_range_fn_t)(unsigned long start,
						    unsigned long len);
typedef void (*mcctrl_control_perf_set_num_fn_t)(void *usrdata,
						 unsigned long value);
typedef int (*mcctrl_control_perf_event_num_fn_t)(void *usrdata);
typedef void *(*mcctrl_control_perf_alloc_set_desc_fn_t)(
	const void *arg, int index, unsigned int target_cntr, int *error);
typedef void (*mcctrl_control_perf_init_desc_fn_t)(void *desc,
						   unsigned int target_cntr);
typedef void (*mcctrl_control_perf_init_mask_desc_fn_t)(
	void *desc, int ctrl_type, unsigned long cntr_mask);
typedef int (*mcctrl_control_perf_send_wait_fn_t)(unsigned long os, int cpu,
						  void *desc, long timeout,
						  int *need_free);
typedef int (*mcctrl_control_perf_desc_err_fn_t)(void *desc);
typedef unsigned long (*mcctrl_control_perf_desc_read_value_fn_t)(void *desc);
typedef long (*mcctrl_control_long_fn_t)(unsigned long os);
typedef void (*mcctrl_control_getrusage_log_fn_t)(
	int stage, unsigned long size, unsigned long max_size);
long mcctrl_control_transfer_image_body_result(
	unsigned long os, const void *arg, unsigned long desc_size,
	int to_remote, int from_remote,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_os_to_dev_fn_t os_to_dev,
	mcctrl_control_map_memory_fn_t map_memory,
	mcctrl_control_map_virtual_fn_t map_virtual,
	mcctrl_control_unmap_virtual_fn_t unmap_virtual,
	mcctrl_control_unmap_memory_fn_t unmap_memory,
	mcctrl_control_transfer_log_fn_t log_error);
long mcctrl_control_load_syscall_body_result(
	unsigned long os, const void *arg, unsigned long desc_size,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_os_to_dev_fn_t os_to_dev,
	mcctrl_control_map_memory_fn_t map_memory,
	mcctrl_control_map_virtual_fn_t map_virtual,
	mcctrl_control_unmap_virtual_fn_t unmap_virtual,
	mcctrl_control_unmap_memory_fn_t unmap_memory,
	mcctrl_control_load_log_fn_t log_map);
int mcctrl_control_getcred_body_result(
	unsigned long phys, mcctrl_control_phys_to_virt_fn_t phys_to_virt,
	mcctrl_control_cred_value_fn_t current_uid,
	mcctrl_control_cred_value_fn_t current_euid,
	mcctrl_control_cred_value_fn_t current_suid,
	mcctrl_control_cred_value_fn_t current_fsuid,
	mcctrl_control_cred_value_fn_t current_gid,
	mcctrl_control_cred_value_fn_t current_egid,
	mcctrl_control_cred_value_fn_t current_sgid,
	mcctrl_control_cred_value_fn_t current_fsgid);
int mcctrl_control_getcredv_body_result(
	int *virt, mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_cred_value_fn_t current_uid,
	mcctrl_control_cred_value_fn_t current_euid,
	mcctrl_control_cred_value_fn_t current_suid,
	mcctrl_control_cred_value_fn_t current_fsuid,
	mcctrl_control_cred_value_fn_t current_gid,
	mcctrl_control_cred_value_fn_t current_egid,
	mcctrl_control_cred_value_fn_t current_sgid,
	mcctrl_control_cred_value_fn_t current_fsgid);
long mcctrl_control_strncpy_from_user_body_result(
	struct strncpy_from_user_desc *arg, unsigned long page_size,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_alloc_page_fn_t alloc_page,
	mcctrl_control_free_page_fn_t free_page,
	mcctrl_control_strncpy_from_user_fn_t strncpy_from_user);
int mcctrl_control_destroy_ppd_body_result(
	unsigned long os, int pid, mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_get_ppd_fn_t get_ppd, mcctrl_control_put_fn_t put_ppd,
	mcctrl_control_destroy_ppd_log_fn_t log_event);
int mcctrl_control_close_exec_body_result(
	unsigned long os, int pid, mcctrl_control_validate_os_fn_t os_index,
	mcctrl_control_drop_exec_fn_t drop_exec);
long mcctrl_control_newprocess_body_result(
	unsigned long os, void *file, mcctrl_control_current_int_fn_t current_pid,
	mcctrl_control_new_info_fn_t new_info,
	mcctrl_control_set_info_pid_fn_t set_info_pid,
	mcctrl_control_register_release_fn_t register_release,
	mcctrl_control_set_private_fn_t set_private);
long mcctrl_control_start_image_body_result(
	unsigned long os, const void *udesc, void *file,
	unsigned long desc_size,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_alloc_fn_t alloc_desc,
	mcctrl_control_free_fn_t free_desc,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_file_ptr_fn_t get_private,
	mcctrl_control_new_info_fn_t new_info,
	mcctrl_control_desc_int_fn_t desc_cpu,
	mcctrl_control_desc_int_fn_t desc_pid,
	mcctrl_control_desc_ulong_fn_t desc_user_start,
	mcctrl_control_desc_ulong_fn_t desc_user_end,
	mcctrl_control_desc_ulong_fn_t desc_rprocess,
	mcctrl_control_info_ulong_fn_t info_prepare_thread,
	mcctrl_control_set_start_info_fn_t set_start_info,
	mcctrl_control_register_release_fn_t register_release,
	mcctrl_control_set_private_fn_t set_private,
	mcctrl_control_os_cpu_void_fn_t set_recv_cpu,
	mcctrl_control_ptr_ulong_fn_t set_last_thread_exec,
	mcctrl_control_schedule_send_fn_t send_schedule,
	mcctrl_control_put_fn_t clear_prepare_thread,
	mcctrl_control_start_log_fn_t log_event);
long mcctrl_control_send_signal_body_result(
	unsigned long os, const void *sigparam, unsigned long sig_size,
	unsigned long desc_size,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_alloc_fn_t alloc_desc,
	mcctrl_control_free_fn_t free_desc,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_virt_to_phys_fn_t virt_to_phys,
	mcctrl_control_cpu_register_send_wait_fn_t send_wait,
	mcctrl_control_signal_log_fn_t log_event);
long mcctrl_control_ret_syscall_body_result(
	unsigned long os, const void *arg, unsigned long desc_size,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_current_int_fn_t current_pid,
	mcctrl_control_current_int_fn_t current_tid,
	mcctrl_control_current_task_fn_t current_task,
	mcctrl_control_get_ppd_fn_t get_ppd,
	mcctrl_control_put_fn_t put_ppd,
	mcctrl_control_get_ptd_fn_t get_ptd,
	mcctrl_control_put_fn_t put_ptd,
	mcctrl_control_ptr_field_fn_t ptd_data,
	mcctrl_control_os_to_dev_fn_t os_to_dev,
	mcctrl_control_map_memory_fn_t map_memory,
	mcctrl_control_map_virtual_fn_t map_virtual,
	mcctrl_control_unmap_virtual_fn_t unmap_virtual,
	mcctrl_control_unmap_memory_fn_t unmap_memory,
	mcctrl_control_return_syscall_fn_t return_syscall,
	mcctrl_control_put_fn_t release_packet,
	mcctrl_control_ret_syscall_log_fn_t log_event);
long mcctrl_control_terminate_thread_unsafe_body_result(
	unsigned long os, int pid, int tid, long code, void *task,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_info_ulong_fn_t usrdata_os,
	mcctrl_control_get_ppd_fn_t get_ppd,
	mcctrl_control_put_fn_t put_ppd,
	mcctrl_control_get_ptd_fn_t get_ptd,
	mcctrl_control_put_fn_t put_ptd,
	mcctrl_control_ptr_int_fn_t ptd_tid,
	mcctrl_control_ptr_field_fn_t ptd_data,
	mcctrl_control_ptr_int_fn_t ptd_refcount,
	mcctrl_control_return_syscall_fn_t return_syscall,
	mcctrl_control_put_fn_t release_packet,
	mcctrl_control_terminate_thread_log_fn_t log_event);
long mcctrl_control_uti_get_ctx_body_result(
	unsigned long os, void *udesc, unsigned long desc_size,
	unsigned long ctx_size, unsigned long key_offset,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_os_to_dev_fn_t os_to_dev,
	mcctrl_control_map_memory_fn_t map_memory,
	mcctrl_control_map_virtual_fn_t map_virtual,
	mcctrl_control_unmap_virtual_fn_t unmap_virtual,
	mcctrl_control_unmap_memory_fn_t unmap_memory,
	mcctrl_control_current_ulong_fn_t current_key,
	mcctrl_control_uti_log_fn_t log_event);
long mcctrl_control_pin_region_body_result(
	const void *arg, int pin_shift, int page_shift,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_get_order_fn_t get_order,
	mcctrl_control_alloc_pages_fn_t alloc_pages,
	mcctrl_control_virt_to_phys_fn_t virt_to_phys,
	mcctrl_control_copy_user_fn_t copy_to_user);
long mcctrl_control_free_region_body_result(
	const void *arg, int pin_shift, int page_shift,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_get_order_fn_t get_order,
	mcctrl_control_phys_to_virt_fn_t phys_to_virt,
	mcctrl_control_free_pages_fn_t free_pages);
long mcctrl_control_sys_mount_body_result(
	const void *arg, mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_prepare_creds_fn_t prepare_creds,
	mcctrl_control_cap_raise_admin_fn_t cap_raise_admin,
	mcctrl_control_override_creds_fn_t override_creds,
	mcctrl_control_mount_fn_t mount,
	mcctrl_control_revert_creds_fn_t revert_creds,
	mcctrl_control_put_fn_t put_cred);
long mcctrl_control_sys_umount_body_result(
	const void *arg, int force,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_prepare_creds_fn_t prepare_creds,
	mcctrl_control_cap_raise_admin_fn_t cap_raise_admin,
	mcctrl_control_override_creds_fn_t override_creds,
	mcctrl_control_umount_fn_t umount,
	mcctrl_control_revert_creds_fn_t revert_creds,
	mcctrl_control_put_fn_t put_cred);
long mcctrl_control_sys_unshare_body_result(
	const void *arg, mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_prepare_creds_fn_t prepare_creds,
	mcctrl_control_cap_raise_admin_fn_t cap_raise_admin,
	mcctrl_control_override_creds_fn_t override_creds,
	mcctrl_control_unshare_fn_t unshare,
	mcctrl_control_revert_creds_fn_t revert_creds,
	mcctrl_control_put_fn_t put_cred);
long mcctrl_control_release_user_space_body_result(
	const void *arg, mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_clear_pte_range_fn_t clear_pte_range);
long mcctrl_control_perf_num_body_result(
	unsigned long os, unsigned long value,
	mcctrl_control_validate_os_fn_t validate_os,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_perf_set_num_fn_t set_perf_event_num,
	mcctrl_control_log_fn_t log_error);
long mcctrl_control_perf_destroy_body_result(
	unsigned long os, mcctrl_control_long_fn_t perf_disable,
	mcctrl_control_long_fn_t perf_num_zero);
long mcctrl_control_perf_set_body_result(
	unsigned long os, const void *arg, unsigned int counter_start,
	unsigned long desc_size, mcctrl_control_validate_os_fn_t validate_os,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_perf_event_num_fn_t get_perf_event_num,
	mcctrl_control_get_ptr_fn_t get_cpu_info,
	mcctrl_control_ptr_int_fn_t cpu_info_n_cpus,
	mcctrl_control_free_fn_t free_desc,
	mcctrl_control_perf_alloc_set_desc_fn_t alloc_set_desc,
	mcctrl_control_perf_send_wait_fn_t send_wait,
	mcctrl_control_perf_desc_err_fn_t desc_err,
	mcctrl_control_perf_set_num_fn_t set_perf_event_num,
	mcctrl_control_log_fn_t log_error);
long mcctrl_control_perf_get_body_result(
	unsigned long os, void *arg, unsigned int counter_start,
	unsigned long desc_size, unsigned long value_size,
	mcctrl_control_validate_os_fn_t validate_os,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_perf_event_num_fn_t get_perf_event_num,
	mcctrl_control_get_ptr_fn_t get_cpu_info,
	mcctrl_control_ptr_int_fn_t cpu_info_n_cpus,
	mcctrl_control_alloc_fn_t alloc_desc,
	mcctrl_control_free_fn_t free_desc,
	mcctrl_control_perf_init_desc_fn_t init_desc,
	mcctrl_control_perf_send_wait_fn_t send_wait,
	mcctrl_control_perf_desc_err_fn_t desc_err,
	mcctrl_control_perf_desc_read_value_fn_t desc_read_value,
	mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_log_fn_t log_error);
long mcctrl_control_perf_enable_disable_body_result(
	unsigned long os, int ctrl_type, unsigned int counter_start,
	unsigned long desc_size, mcctrl_control_validate_os_fn_t validate_os,
	mcctrl_control_get_ptr_fn_t get_usrdata,
	mcctrl_control_perf_event_num_fn_t get_perf_event_num,
	mcctrl_control_get_ptr_fn_t get_cpu_info,
	mcctrl_control_ptr_int_fn_t cpu_info_n_cpus,
	mcctrl_control_alloc_fn_t alloc_desc,
	mcctrl_control_free_fn_t free_desc,
	mcctrl_control_perf_init_mask_desc_fn_t init_mask_desc,
	mcctrl_control_perf_send_wait_fn_t send_wait,
	mcctrl_control_perf_desc_err_fn_t desc_err,
	mcctrl_control_log_fn_t log_error);
long mcctrl_control_getrusage_body_result(
	unsigned long os, const void *arg, unsigned long desc_size,
	unsigned long rusage_size, unsigned long max_pgsizes,
	unsigned long max_numa_nodes, unsigned long max_cpus,
	mcctrl_control_validate_os_fn_t validate_os,
	mcctrl_control_get_ptr_fn_t get_rusage,
	mcctrl_control_copy_user_fn_t copy_from_user,
	mcctrl_control_copy_user_fn_t copy_to_user,
	mcctrl_control_alloc_fn_t alloc_rusage,
	mcctrl_control_free_fn_t free_rusage,
	mcctrl_control_getrusage_log_fn_t log_error);
typedef long (*mcctrl_driver_control_fn_t)(unsigned long os,
					   unsigned int request,
					   unsigned long arg,
					   unsigned long file);
typedef void *(*mcctrl_driver_os_get_fn_t)(int index);
typedef void (*mcctrl_driver_os_set_fn_t)(int index, void *os);
typedef void (*mcctrl_driver_void_fn_t)(void);
typedef int (*mcctrl_driver_int_fn_t)(void);
typedef int (*mcctrl_driver_os_int_fn_t)(void *os);
typedef void (*mcctrl_driver_os_void_fn_t)(void *os);
typedef void (*mcctrl_driver_index_void_fn_t)(int index);
typedef int (*mcctrl_driver_os_index_int_fn_t)(void *os, int index);
typedef void (*mcctrl_driver_os_index_void_fn_t)(void *os, int index);
typedef void (*mcctrl_driver_log_fn_t)(int stage, int index);
typedef void *(*mcctrl_driver_lookup_fn_t)(void);
typedef void (*mcctrl_driver_publish_fn_t)(void *ptr);
typedef int (*mcctrl_driver_warn_missing_fn_t)(void *ptr);
struct mcctrl_driver_boot_ops {
	mcctrl_driver_os_get_fn_t find_os;
	mcctrl_driver_os_set_fn_t set_os;
	mcctrl_driver_os_int_fn_t prepare_channels;
	mcctrl_driver_index_void_fn_t copy_user_call_proto;
	mcctrl_driver_os_int_fn_t set_kernel_handlers;
	mcctrl_driver_os_index_int_fn_t register_user_handlers;
	mcctrl_driver_index_void_fn_t procfs_init;
	mcctrl_driver_os_void_fn_t clear_kernel_handlers;
	mcctrl_driver_os_void_fn_t destroy_channels;
	mcctrl_driver_log_fn_t log;
};
struct mcctrl_driver_shutdown_ops {
	mcctrl_driver_os_get_fn_t get_os;
	mcctrl_driver_os_set_fn_t set_os;
	mcctrl_driver_void_fn_t pager_cleanup;
	mcctrl_driver_os_void_fn_t sysfs_cleanup;
	mcctrl_driver_os_void_fn_t free_topology_info;
	mcctrl_driver_os_index_void_fn_t unregister_user_handlers;
	mcctrl_driver_os_void_fn_t clear_kernel_handlers;
	mcctrl_driver_os_void_fn_t destroy_channels;
	mcctrl_driver_index_void_fn_t procfs_exit;
	mcctrl_driver_log_fn_t log;
};
struct mcctrl_driver_symbols_ops {
	mcctrl_driver_lookup_fn_t lookup_mount;
	mcctrl_driver_publish_fn_t set_mount;
	mcctrl_driver_lookup_fn_t lookup_umount;
	mcctrl_driver_publish_fn_t set_umount;
	mcctrl_driver_lookup_fn_t lookup_unshare;
	mcctrl_driver_publish_fn_t set_unshare;
	mcctrl_driver_lookup_fn_t lookup_sched_setaffinity;
	mcctrl_driver_publish_fn_t set_sched_setaffinity;
	mcctrl_driver_lookup_fn_t lookup_sched_setscheduler_nocheck;
	mcctrl_driver_publish_fn_t set_sched_setscheduler_nocheck;
	mcctrl_driver_lookup_fn_t lookup_readlinkat;
	mcctrl_driver_publish_fn_t set_readlinkat;
	mcctrl_driver_lookup_fn_t lookup_zap_page_range;
	mcctrl_driver_publish_fn_t set_zap_page_range;
	mcctrl_driver_lookup_fn_t lookup_hugetlbfs_inode_operations;
	mcctrl_driver_publish_fn_t set_hugetlbfs_inode_operations;
	mcctrl_driver_warn_missing_fn_t warn_missing;
	mcctrl_driver_int_fn_t arch_symbols_init;
};
struct mcctrl_driver_module_ops {
	mcctrl_driver_void_fn_t syscall_init;
	mcctrl_driver_os_set_fn_t set_os;
	mcctrl_driver_void_fn_t binfmt_init;
	mcctrl_driver_void_fn_t tofu_hash_init;
	mcctrl_driver_int_fn_t symbols_init;
	mcctrl_driver_void_fn_t tofu_hijack;
	mcctrl_driver_int_fn_t register_notifier;
	mcctrl_driver_void_fn_t binfmt_exit;
	mcctrl_driver_int_fn_t deregister_notifier;
	mcctrl_driver_void_fn_t uti_finalize;
	mcctrl_driver_void_fn_t tofu_restore;
	mcctrl_driver_log_fn_t log;
};
long mcctrl_driver_ioctl_body_result(
	unsigned long os, unsigned int request, unsigned long arg,
	unsigned long file, mcctrl_driver_control_fn_t dispatch);
unsigned long mcctrl_driver_osnum_to_os_body_result(
	int index, mcctrl_driver_os_get_fn_t get_os);
int mcctrl_driver_os_alive_body_result(
	int limit, mcctrl_driver_os_get_fn_t get_os);
int mcctrl_driver_boot_notifier_body_result(
	int os_index, const struct mcctrl_driver_boot_ops *ops);
int mcctrl_driver_shutdown_notifier_body_result(
	int os_index, const struct mcctrl_driver_shutdown_ops *ops);
int mcctrl_driver_symbols_init_body_result(
	const struct mcctrl_driver_symbols_ops *ops);
int mcctrl_driver_init_body_result(
	int os_limit, const struct mcctrl_driver_module_ops *ops);
void mcctrl_driver_exit_body_result(
	const struct mcctrl_driver_module_ops *ops);
int mcctrl_ikc_free_addrs_owner_result(int free_addrs_count);
int mcctrl_ikc_desc_free_at_put_result(int allocated_internally);
int mcctrl_ikc_wait_mode_result(long timeout);
unsigned long mcctrl_ikc_busy_timeout_msecs_result(long timeout);
int mcctrl_ikc_wait_abort_return_result(int wait_ret);
int mcctrl_ikc_release_packet_after_handler_result(int msg);
int mcctrl_ikc_cpu_nonnegative_result(int cpu);
int mcctrl_ikc_cpu_index_valid_result(int cpu, int num_channels);
int mcctrl_ikc_linux_cpu_valid_result(int linux_cpu, int nr_cpu_ids);
int mcctrl_ikc_init_uses_last_channel_result(int port);
int mcctrl_ikc_cpu_count_valid_result(int n_cpus);
int mcctrl_lwk_to_linux_index_result(const int *mapping, int count, int index);
int mcctrl_linux_to_lwk_index_result(const int *mapping, int count, int linux_id);
int mcctrl_translate_cpumap_result(const int *mapping, int count,
				   const void *linmap, void *mckmap,
				   int nr_cpu_ids);
void mcctrl_fill_sequential_bitset_result(unsigned long *bits, int bit_count,
					  int word_count, int bits_per_word);
int mcctrl_read_buffer_status_result(char *buf, unsigned long size,
				     long bytes_read);
int mcctrl_parse_long_result(const char *buf, long *value_out);
int mcctrl_pci_realpath_valid_result(const char *path);
int mcctrl_ptr_hash_result(unsigned long ptr, unsigned long mask);
int mcctrl_ptr_eq_result(unsigned long a, unsigned long b);
int mcctrl_file_to_pidfd_lookup_match_result(unsigned long entry_filp,
					     unsigned long filp,
					     unsigned long entry_group_leader,
					     unsigned long group_leader);
int mcctrl_file_to_pidfd_remove_match_result(unsigned long entry_filp,
					    unsigned long filp,
					    unsigned long entry_os,
					    unsigned long os,
					    unsigned long entry_group_leader,
					    unsigned long group_leader,
					    int entry_fd, int fd);
int mcctrl_tofu_dev_path_result(const char *path);
unsigned long mcctrl_tofu_dev_tail_offset_result(void);
void mcctrl_tofu_dev_name_copy_result(char *dst, unsigned long dst_size,
				      const char *path);
int mcctrl_tofu_cq_path_parse_result(const char *path, int *tni_out,
				     int *cq_out);
int mcctrl_sysfs_inited_result(unsigned long sysfs_buf);
int mcctrl_sysfs_path_error_result(const char *path, long written,
				   unsigned long path_size);
int mcctrl_binfmt_skip_path_result(const char *path);
int mcctrl_path_allowed_result(const char *file, const char *list);
int mcctrl_pager_treat_as_device_path_result(const char *path);
int mcctrl_pager_should_populate_path_result(const char *path);
int mcctrl_fs_is_tmpfs_result(const char *name);
int mcctrl_fs_is_proc_result(const char *name);
int mcctrl_special_char_device_result(unsigned int major, unsigned int minor);
int mcctrl_format_mcos_name_result(char *buf, unsigned long buflen, int osnum);
int mcctrl_format_decimal_name_result(char *buf, unsigned long buflen, int value);
int mcctrl_futex_cmd_result(int op);
int mcctrl_futex_is_private_result(int op);
int mcctrl_futex_clock_realtime_result(int op);
int mcctrl_futex_realtime_cmd_valid_result(int cmd);
int mcctrl_futex_wait_uses_timeout_result(int cmd);
int mcctrl_futex_arg3_is_val2_result(int cmd);
const char *mcctrl_futex_op_label_result(int cmd);
struct mcctrl_syscall_ptd_offsets {
	unsigned long ppd_thread_hash;
	unsigned long ppd_thread_lock;
	unsigned long ptd_ppd;
	unsigned long ptd_hash;
	unsigned long ptd_task;
	unsigned long ptd_data;
	unsigned long ptd_tid;
	unsigned long ptd_refcount;
	unsigned long list_head_size;
	unsigned long rwlock_size;
};
typedef void *(*mcctrl_syscall_ptd_alloc_fn_t)(unsigned long size);
typedef void (*mcctrl_syscall_ptd_free_fn_t)(void *ptr);
typedef unsigned long (*mcctrl_syscall_ptd_lock_fn_t)(void *lock);
typedef void (*mcctrl_syscall_ptd_unlock_fn_t)(void *lock,
					       unsigned long flags);
typedef void (*mcctrl_syscall_ptd_log_fn_t)(int stage, int value,
					    void *ptd);
int mcctrl_syscall_ptd_hash_result(void *task, int mask);
int mcctrl_syscall_put_ptd_unsafe_body_result(
	void *ptd, const struct mcctrl_syscall_ptd_offsets *offsets,
	mcctrl_syscall_ptd_free_fn_t free_fn,
	mcctrl_syscall_ptd_log_fn_t log);
int mcctrl_syscall_put_ptd_body_result(
	void *ptd, int mask, const struct mcctrl_syscall_ptd_offsets *offsets,
	mcctrl_syscall_ptd_free_fn_t free_fn,
	mcctrl_syscall_ptd_lock_fn_t write_lock,
	mcctrl_syscall_ptd_unlock_fn_t write_unlock,
	mcctrl_syscall_ptd_log_fn_t log);
int mcctrl_syscall_add_ptd_body_result(
	void *ppd, void *data, void *current_task, int tid,
	unsigned long ptd_size, int mask,
	const struct mcctrl_syscall_ptd_offsets *offsets,
	mcctrl_syscall_ptd_alloc_fn_t alloc_fn,
	mcctrl_syscall_ptd_free_fn_t free_fn,
	mcctrl_syscall_ptd_lock_fn_t write_lock,
	mcctrl_syscall_ptd_unlock_fn_t write_unlock,
	mcctrl_syscall_ptd_log_fn_t log);
void *mcctrl_syscall_get_ptd_body_result(
	void *ppd, void *task, int mask,
	const struct mcctrl_syscall_ptd_offsets *offsets,
	mcctrl_syscall_ptd_lock_fn_t read_lock,
	mcctrl_syscall_ptd_unlock_fn_t read_unlock,
	mcctrl_syscall_ptd_log_fn_t log);
struct mcctrl_syscall_pidfd_offsets {
	unsigned long entry_filp;
	unsigned long entry_os;
	unsigned long entry_group_leader;
	unsigned long entry_pid;
	unsigned long entry_fd;
	unsigned long entry_hash;
	unsigned long entry_tofu_dev_path;
	unsigned long entry_pde_data;
	unsigned long list_head_size;
	unsigned long tofu_dev_path_size;
};
typedef void *(*mcctrl_syscall_pidfd_alloc_fn_t)(unsigned long size);
typedef void (*mcctrl_syscall_pidfd_free_fn_t)(void *ptr);
typedef void (*mcctrl_syscall_pidfd_lock_init_fn_t)(void *lock);
typedef unsigned long (*mcctrl_syscall_pidfd_lock_fn_t)(void *lock);
typedef void (*mcctrl_syscall_pidfd_unlock_fn_t)(void *lock,
						 unsigned long flags);
typedef void (*mcctrl_syscall_pidfd_log_fn_t)(int stage, void *filp,
					      int pid, int fd);
int mcctrl_syscall_pidfd_hash_init_body_result(
	void *table, unsigned long hash_size, unsigned long list_head_size,
	void *lock, mcctrl_syscall_pidfd_lock_init_fn_t lock_init);
int mcctrl_syscall_pidfd_hash_insert_body_result(
	void *table, void *lock, void *filp, unsigned long os, int pid,
	void *group_leader, int fd, const char *path, void *pde_data,
	unsigned long entry_size, unsigned long mask,
	const struct mcctrl_syscall_pidfd_offsets *offsets,
	mcctrl_syscall_pidfd_alloc_fn_t alloc_fn,
	mcctrl_syscall_pidfd_free_fn_t free_fn,
	mcctrl_syscall_pidfd_lock_fn_t lock_fn,
	mcctrl_syscall_pidfd_unlock_fn_t unlock_fn,
	mcctrl_syscall_pidfd_log_fn_t log);
void *mcctrl_syscall_pidfd_hash_lookup_body_result(
	void *table, void *lock, void *filp, void *group_leader,
	unsigned long mask,
	const struct mcctrl_syscall_pidfd_offsets *offsets,
	mcctrl_syscall_pidfd_lock_fn_t lock_fn,
	mcctrl_syscall_pidfd_unlock_fn_t unlock_fn,
	mcctrl_syscall_pidfd_log_fn_t log);
int mcctrl_syscall_pidfd_hash_remove_body_result(
	void *table, void *lock, void *filp, unsigned long os,
	void *group_leader, int fd, unsigned long mask,
	const struct mcctrl_syscall_pidfd_offsets *offsets,
	mcctrl_syscall_pidfd_free_fn_t free_fn,
	mcctrl_syscall_pidfd_lock_fn_t lock_fn,
	mcctrl_syscall_pidfd_unlock_fn_t unlock_fn,
	mcctrl_syscall_pidfd_log_fn_t log);
struct mcctrl_syscall_pager_offsets {
	unsigned long ppd_devobj_pager_list;
	unsigned long ppd_devobj_pager_lock;
	unsigned long pager_list;
	unsigned long pager_rofile;
	unsigned long pager_rwfile;
};
typedef unsigned long (*mcctrl_syscall_pager_lock_fn_t)(void *lock);
typedef void (*mcctrl_syscall_pager_unlock_fn_t)(void *lock,
						 unsigned long flags);
typedef int (*mcctrl_syscall_pager_predicate_fn_t)(void);
typedef int (*mcctrl_syscall_pager_sem_down_fn_t)(void *sem);
typedef void (*mcctrl_syscall_pager_sem_up_fn_t)(void *sem);
typedef void (*mcctrl_syscall_pager_ptr_fn_t)(void *ptr);
typedef void (*mcctrl_syscall_pager_log_fn_t)(int stage, void *pager,
					      int value);
int mcctrl_syscall_pager_add_process_body_result(
	int *nr_processes, void *lock,
	mcctrl_syscall_pager_lock_fn_t lock_fn,
	mcctrl_syscall_pager_unlock_fn_t unlock_fn);
int mcctrl_syscall_pager_remove_process_body_result(
	void *ppd, int *nr_processes, void *pager_lock,
	const struct mcctrl_syscall_pager_offsets *offsets,
	mcctrl_syscall_pager_predicate_fn_t in_atomic_fn,
	mcctrl_syscall_pager_predicate_fn_t in_interrupt_fn,
	mcctrl_syscall_pager_sem_down_fn_t down_fn,
	mcctrl_syscall_pager_sem_up_fn_t up_fn,
	mcctrl_syscall_pager_ptr_fn_t free_fn,
	mcctrl_syscall_pager_lock_fn_t lock_fn,
	mcctrl_syscall_pager_unlock_fn_t unlock_fn,
	mcctrl_syscall_pager_log_fn_t log);
int mcctrl_syscall_pager_cleanup_body_result(
	void *pager_list, void *pager_lock,
	const struct mcctrl_syscall_pager_offsets *offsets,
	mcctrl_syscall_pager_ptr_fn_t fput_fn,
	mcctrl_syscall_pager_ptr_fn_t free_fn,
	mcctrl_syscall_pager_lock_fn_t lock_fn,
	mcctrl_syscall_pager_unlock_fn_t unlock_fn,
	mcctrl_syscall_pager_log_fn_t log);
void *mcctrl_rva_to_rpa_cache_search_body_result(void *root,
						 unsigned long rva);
int mcctrl_rva_to_rpa_cache_insert_body_result(
	void *root, void *cache_node,
	void (*link_node)(void *, void *, void *),
	void (*insert_color)(void *, void *));
int mcctrl_futex_remove_process_body_result(
	void *root, void *(*rb_first)(void *),
	void (*rb_erase)(void *, void *), void (*free_node)(void *));
typedef int (*mcctrl_futex_wait_fn_t)(u32 *uaddr, int fshared,
				      u32 val, u64 timeout,
				      u32 bitset, int clockrt,
				      void *uti_info);
typedef int (*mcctrl_futex_wake_fn_t)(u32 *uaddr, int fshared,
				      int nr_wake, u32 bitset,
				      void *uti_info);
typedef int (*mcctrl_futex_requeue_fn_t)(u32 *uaddr1, int fshared,
					 u32 *uaddr2, int nr_wake,
					 int nr_requeue, u32 *cmpval,
					 int requeue_pi, void *uti_info);
typedef int (*mcctrl_futex_wake_op_fn_t)(u32 *uaddr1, int fshared,
					 u32 *uaddr2, int nr_wake,
					 int nr_wake2, int op,
					 void *uti_info);
typedef void (*mcctrl_futex_warn_fn_t)(int cmd);
int mcctrl_futex_dispatch_body_result(
	u32 *uaddr, int op, u32 val, u64 timeout,
	u32 *uaddr2, u32 val2, u32 val3, int fshared,
	void *uti_info, mcctrl_futex_wait_fn_t wait,
	mcctrl_futex_wake_fn_t wake, mcctrl_futex_requeue_fn_t requeue,
	mcctrl_futex_wake_op_fn_t wake_op, mcctrl_futex_warn_fn_t warn);
typedef void *(*mcctrl_futex_info_ptr_fn_t)(void *uti_info);
typedef int (*mcctrl_futex_current_cpu_fn_t)(void);
typedef void (*mcctrl_futex_prepare_wait_q_fn_t)(void *q, u32 bitset,
						void *resp, int linux_cpu);
typedef int (*mcctrl_futex_wait_setup_fn_t)(u32 *uaddr, u32 val,
					   int fshared, void *q, void **hb,
					   void *uti_info);
typedef s64 (*mcctrl_futex_wait_queue_fn_t)(void *hb, void *q, u64 timeout,
					    void *uti_info);
typedef int (*mcctrl_futex_unqueue_fn_t)(void *q);
typedef void (*mcctrl_futex_put_q_key_fn_t)(int fshared, void *q);
typedef void (*mcctrl_futex_wait_log_fn_t)(int stage, void *uti_info);
int mcctrl_futex_wait_body_result(
	u32 *uaddr, int fshared, u32 val, u64 timeout, u32 bitset,
	void *uti_info, mcctrl_futex_info_ptr_fn_t get_q,
	mcctrl_futex_info_ptr_fn_t get_resp,
	mcctrl_futex_current_cpu_fn_t get_cpu,
	mcctrl_futex_prepare_wait_q_fn_t prepare_q,
	mcctrl_futex_wait_setup_fn_t wait_setup,
	mcctrl_futex_wait_queue_fn_t wait_queue,
	mcctrl_futex_unqueue_fn_t unqueue,
	mcctrl_futex_put_q_key_fn_t put_q_key,
	mcctrl_futex_wait_log_fn_t log_event);
typedef int (*mcctrl_futex_get_key_fn_t)(unsigned long uaddr, int fshared,
					 unsigned long key_addr,
					 unsigned long ctx_addr);
typedef unsigned long (*mcctrl_futex_hash_key_fn_t)(
	unsigned long key_addr, unsigned long queue_addr);
typedef unsigned long (*mcctrl_futex_wake_lock_fn_t)(unsigned long lock_addr);
typedef void (*mcctrl_futex_wake_unlock_fn_t)(unsigned long lock_addr,
					      unsigned long flags);
typedef void (*mcctrl_futex_hb_lock_fn_t)(unsigned long lock_addr);
typedef void (*mcctrl_futex_hb_unlock_fn_t)(unsigned long lock_addr);
typedef void (*mcctrl_futex_put_key_fn_t)(int fshared,
					  unsigned long key_addr);
typedef void (*mcctrl_futex_wake_entry_fn_t)(unsigned long q_addr,
					     unsigned long ctx_addr);
typedef int (*mcctrl_futex_atomic_op_fn_t)(int op, unsigned long uaddr);
typedef int (*mcctrl_futex_get_value_fn_t)(unsigned long value_addr,
					   unsigned long uaddr);
typedef void (*mcctrl_futex_drop_key_refs_fn_t)(unsigned long key_addr);
typedef void (*mcctrl_futex_requeue_entry_fn_t)(unsigned long q_addr,
						unsigned long ctx_addr);
int mcctrl_futex_wake_body_result(
	unsigned long uaddr, int fshared, int nr_wake, u32 bitset,
	unsigned long key_addr, unsigned long futex_queue_addr,
	unsigned long ctx_addr, unsigned long hb_lock_offset,
	unsigned long hb_chain_offset, unsigned long q_list_offset,
	unsigned long q_key_offset, unsigned long q_bitset_offset,
	unsigned long key_word_offset, unsigned long key_ptr_offset,
	unsigned long key_offset_offset,
	mcctrl_futex_get_key_fn_t get_key,
	mcctrl_futex_hash_key_fn_t hash_key,
	mcctrl_futex_wake_lock_fn_t lock_fn,
	mcctrl_futex_wake_unlock_fn_t unlock_fn,
	mcctrl_futex_put_key_fn_t put_key,
	mcctrl_futex_wake_entry_fn_t wake_fn);
int mcctrl_futex_wake_op_body_result(
	unsigned long uaddr1, int fshared, unsigned long uaddr2,
	int nr_wake, int nr_wake2, int op, unsigned long key1_addr,
	unsigned long key2_addr, unsigned long futex_queue_addr,
	unsigned long ctx_addr, unsigned long hb_lock_offset,
	unsigned long hb_chain_offset, unsigned long q_list_offset,
	unsigned long q_key_offset, unsigned long q_bitset_offset,
	unsigned long key_word_offset, unsigned long key_ptr_offset,
	unsigned long key_offset_offset,
	mcctrl_futex_get_key_fn_t get_key,
	mcctrl_futex_hash_key_fn_t hash_key,
	mcctrl_futex_hb_lock_fn_t lock_fn,
	mcctrl_futex_hb_unlock_fn_t unlock_fn,
	mcctrl_futex_atomic_op_fn_t atomic_op,
	mcctrl_futex_put_key_fn_t put_key,
	mcctrl_futex_wake_entry_fn_t wake_fn);
int mcctrl_futex_requeue_body_result(
	unsigned long uaddr1, int fshared, unsigned long uaddr2,
	int nr_wake, int nr_requeue, unsigned long cmpval_addr,
	unsigned long key1_addr, unsigned long key2_addr,
	unsigned long ctx_addr, unsigned long futex_queue_addr,
	unsigned long hb_lock_offset, unsigned long hb_chain_offset,
	unsigned long q_list_offset, unsigned long q_key_offset,
	unsigned long key_word_offset, unsigned long key_ptr_offset,
	unsigned long key_offset_offset, unsigned long ctx_hb1_offset,
	unsigned long ctx_hb2_offset, unsigned long ctx_key2_offset,
	mcctrl_futex_get_key_fn_t get_key,
	mcctrl_futex_hash_key_fn_t hash_key,
	mcctrl_futex_hb_lock_fn_t lock_fn,
	mcctrl_futex_hb_unlock_fn_t unlock_fn,
	mcctrl_futex_get_value_fn_t get_value,
	mcctrl_futex_put_key_fn_t put_key,
	mcctrl_futex_drop_key_refs_fn_t drop_key_refs,
	mcctrl_futex_requeue_entry_fn_t wake_fn,
	mcctrl_futex_requeue_entry_fn_t requeue_fn);
int mcctrl_procfs_packet_handler_body_result(void *os, int msg, int pid,
					     unsigned long arg,
					     unsigned long resp_pa,
					     unsigned long work_size,
					     void *(*alloc)(unsigned long),
					     void (*init_schedule)(void *),
					     void (*alloc_failed)(void));
typedef const char *(*mcctrl_procfs_entry_name_fn_t)(const void *entry);
typedef void *(*mcctrl_procfs_entry_parent_fn_t)(const void *entry);
typedef unsigned int (*mcctrl_procfs_entry_mode_fn_t)(const void *entry);
typedef const void *(*mcctrl_procfs_entry_fops_fn_t)(const void *entry);
typedef const void *(*mcctrl_procfs_entry_next_fn_t)(const void *entry,
						     unsigned long size);
typedef void (*mcctrl_procfs_add_entry_with_ids_fn_t)(
	void *parent, const char *name, unsigned int mode, const void *fops,
	const void *uid, const void *gid);
typedef void *(*mcctrl_procfs_first_entry_fn_t)(void *parent);
typedef void *(*mcctrl_procfs_next_entry_fn_t)(void *parent, void *entry);
typedef void *(*mcctrl_procfs_find_entry_fn_t)(void *parent,
					       const char *name);
typedef void (*mcctrl_procfs_delete_entry_fn_t)(void *entry);
typedef void *(*mcctrl_procfs_alloc_entry_fn_t)(unsigned long size);
typedef void (*mcctrl_procfs_init_entry_fn_t)(void *entry,
					     const char *name);
typedef void *(*mcctrl_procfs_create_pde_fn_t)(
	void *parent, const char *name, unsigned int mode,
	const void *uid, const void *gid, const void *opaque, void *entry);
typedef void (*mcctrl_procfs_commit_entry_fn_t)(
	void *entry, void *parent, void *pde, const void *uid,
	const void *gid);
typedef void (*mcctrl_procfs_entry_log_fn_t)(const char *name);
typedef void (*mcctrl_procfs_entry_void_fn_t)(void *entry);
typedef void *(*mcctrl_procfs_entry_data_fn_t)(void *entry);
typedef void (*mcctrl_procfs_void_fn_t)(void);
typedef void *(*mcctrl_procfs_find_vpid_fn_t)(int pid);
typedef void *(*mcctrl_procfs_pid_task_fn_t)(void *pid, int type);
typedef void *(*mcctrl_procfs_task_cred_fn_t)(void *task);
char *mcctrl_procfs_getpath_body_result(
	void *entry, char *buf, unsigned long bufsize,
	mcctrl_procfs_entry_name_fn_t entry_name,
	mcctrl_procfs_entry_parent_fn_t entry_parent);
long mcctrl_procfs_add_entries_body_result(
	void *parent, const void *entries, unsigned long entry_size,
	const void *uid, const void *gid,
	mcctrl_procfs_entry_name_fn_t entry_name,
	mcctrl_procfs_entry_mode_fn_t entry_mode,
	mcctrl_procfs_entry_fops_fn_t entry_fops,
	mcctrl_procfs_entry_next_fn_t entry_next,
	mcctrl_procfs_add_entry_with_ids_fn_t add_entry);
void *mcctrl_procfs_find_entry_body_result(
	void *parent, const char *name,
	mcctrl_procfs_first_entry_fn_t first_entry,
	mcctrl_procfs_next_entry_fn_t next_entry,
	mcctrl_procfs_entry_name_fn_t entry_name);
void *mcctrl_procfs_add_entry_body_result(
	void *parent, const char *name, unsigned int mode,
	const void *uid, const void *gid, const void *opaque,
	unsigned long entry_size,
	mcctrl_procfs_find_entry_fn_t find_entry,
	mcctrl_procfs_delete_entry_fn_t delete_entry,
	mcctrl_procfs_alloc_entry_fn_t alloc_entry,
	mcctrl_procfs_init_entry_fn_t init_entry,
	mcctrl_procfs_create_pde_fn_t create_pde,
	mcctrl_procfs_commit_entry_fn_t commit_entry,
	mcctrl_procfs_entry_void_fn_t free_entry,
	mcctrl_procfs_void_fn_t alloc_failed,
	mcctrl_procfs_entry_log_fn_t create_failed);
int mcctrl_procfs_delete_entries_body_result(
	void *top, mcctrl_procfs_first_entry_fn_t first_child,
	mcctrl_procfs_delete_entry_fn_t delete_entry,
	mcctrl_procfs_entry_void_fn_t unlink_entry,
	mcctrl_procfs_entry_void_fn_t remove_proc,
	mcctrl_procfs_entry_data_fn_t entry_data,
	mcctrl_procfs_entry_void_fn_t free_ptr);
void *mcctrl_procfs_get_pid_cred_body_result(
	int pid, int pid_type, mcctrl_procfs_void_fn_t rcu_lock,
	mcctrl_procfs_void_fn_t rcu_unlock,
	mcctrl_procfs_find_vpid_fn_t find_vpid_fn,
	mcctrl_procfs_pid_task_fn_t pid_task_fn,
	mcctrl_procfs_task_cred_fn_t task_cred);
void *mcctrl_procfs_find_base_entry_body_result(
	int osnum, int (*format_mcos)(char *, unsigned long, int),
	void *(*find_entry)(void *, const char *));
void *mcctrl_procfs_find_pid_entry_body_result(
	int osnum, int pid, int (*format_mcos)(char *, unsigned long, int),
	int (*format_decimal)(char *, unsigned long, int),
	void *(*find_entry)(void *, const char *));
void *mcctrl_procfs_find_tid_entry_body_result(
	int osnum, int pid, int tid,
	int (*format_mcos)(char *, unsigned long, int),
	int (*format_decimal)(char *, unsigned long, int),
	void *(*find_entry)(void *, const char *));
void *mcctrl_procfs_get_base_entry_body_result(
	int osnum, int (*format_mcos)(char *, unsigned long, int),
	void *(*find_entry)(void *, const char *),
	void *(*add_entry)(void *, const char *, int),
	void (*set_osnum)(void *, int));
void *mcctrl_procfs_get_pid_entry_body_result(
	int osnum, int pid, int (*format_mcos)(char *, unsigned long, int),
	int (*format_decimal)(char *, unsigned long, int),
	void *(*find_entry)(void *, const char *),
	void *(*add_entry)(void *, const char *, int));
void *mcctrl_procfs_get_tid_entry_body_result(
	int osnum, int pid, int tid,
	int (*format_mcos)(char *, unsigned long, int),
	int (*format_decimal)(char *, unsigned long, int),
	void *(*find_entry)(void *, const char *),
	void *(*add_entry)(void *, const char *, int));
int mcctrl_procfs_add_tid_entry_body_result(
	int osnum, int pid, int tid, void *(*get_cred)(int),
	void (*lock)(void), void (*unlock)(void),
	void *(*find_pid)(int, int), void *(*get_pid)(int, int),
	void (*add_pid_entries)(void *, void *),
	void (*add_tid)(int, int, int, void *));
int mcctrl_procfs_add_tid_with_cred_body_result(
	int osnum, int pid, int tid, void *cred,
	void *(*get_tid)(int, int, int),
	void (*add_tid_entries)(void *, void *),
	void *(*find_exe_data)(void *),
	void (*add_exe_link)(void *, void *, void *));
int mcctrl_procfs_add_pid_entry_body_result(
	int osnum, int pid, void *(*get_cred)(int), void (*lock)(void),
	void (*unlock)(void), void *(*get_pid)(int, int),
	void (*add_pid_entries)(void *, void *),
	void (*add_tid)(int, int, int, void *));
int mcctrl_procfs_delete_tid_entry_body_result(
	int osnum, int pid, int tid, void (*lock)(void), void (*unlock)(void),
	void *(*find_tid)(int, int, int), void (*delete_entry)(void *));
int mcctrl_procfs_delete_pid_entry_body_result(
	int osnum, int pid, void (*lock)(void), void (*unlock)(void),
	void *(*find_pid)(int, int), void (*delete_entry)(void *));
int mcctrl_procfs_init_body_result(int osnum, void (*lock)(void),
				   void (*unlock)(void),
				   void *(*get_base)(int),
				   void (*add_base_entries)(void *));
int mcctrl_procfs_exit_body_result(int osnum, void (*lock)(void),
				   void (*unlock)(void),
				   void *(*find_base)(int),
				   void (*delete_entry)(void *));
int mcctrl_procfs_exe_link_body_result(
	int osnum, int pid, const char *path, void (*lock)(void),
	void (*unlock)(void), void *(*find_pid)(int, int),
	void *(*add_pid_exe)(void *, const char *),
	void (*store_exe_path)(void *, const char *),
	void (*add_task_exe_links)(void *, const char *));
long mcctrl_procfs_lseek_body_result(long current_pos, long offset, int orig,
				     long *new_pos);
long mcctrl_procfs_read_write_body_result(
	void *entry, void *ubuf, unsigned long nbytes, long *ppos,
	int read_write, char *path_buf, unsigned long path_size,
	unsigned long page_size, int (*entry_osnum)(void *),
	const char *(*get_path)(void *, char *, unsigned long),
	void *(*lookup_os)(int), void *(*get_usrdata)(void *),
	void *(*get_per_proc)(void *, int), void (*put_per_proc)(void *),
	int (*ppd_cpu)(void *), int (*get_order_fn)(unsigned long),
	void *(*alloc_pages_fn)(int),
	void (*free_pages_fn)(void *, int),
	unsigned long (*virt_to_phys_fn)(void *), void *(*alloc_read)(void),
	void (*init_read)(void *, unsigned long, long, int, int,
			  const char *),
	int (*send_request)(void *, int, int, void *, int *),
	int (*read_ret)(void *), int (*read_eof)(void *),
	void (*free_fn)(void *),
	int (*copy_to_user_fn)(void *, void *, unsigned long),
	void (*bad_osnum_log)(void),
	void (*osnum_mismatch_log)(int, int),
	void (*no_os_log)(int), void (*no_usrdata_log)(int),
	void (*no_ppd_log)(int), void (*alloc_error_log)(void),
	void (*copy_error_log)(void), void (*timeout_log)(void));
int mcctrl_procfs_buff_open_body_result(
	void *entry, void *file, unsigned long path_size,
	unsigned long info_base_size, unsigned long pa_null,
	int (*entry_osnum)(void *), void *(*lookup_os)(int),
	void *(*alloc)(unsigned long), void (*free_fn)(void *),
	const char *(*get_path)(void *, char *, unsigned long),
	void (*init_info)(void *, void *, int, unsigned long, const char *),
	void (*set_file_private)(void *, void *));
int mcctrl_procfs_buff_release_body_result(
	void *file, unsigned long pa_null, void *(*get_file_private)(void *),
	void (*set_file_private)(void *, void *),
	unsigned long (*info_top_pa)(void *), void *(*info_os)(void *),
	void *(*alloc_read)(void),
	void (*init_release_read)(void *, unsigned long),
	int (*send_release)(void *, void *, int *),
	int (*read_ret)(void *), void (*free_fn)(void *),
	void (*timeout_log)(void));
long mcctrl_procfs_buff_read_body_result(
	void *file, void *ubuf, unsigned long nbytes, long *ppos,
	unsigned long pa_null, unsigned long page_size,
	void *(*get_file_private)(void *), void *(*info_os)(void *),
	int (*info_pid)(void *), unsigned long (*info_top_pa)(void *),
	unsigned long (*info_cur_pa)(void *),
	const char *(*info_path)(void *),
	void (*info_set_top_cur)(void *, unsigned long, unsigned long),
	void (*info_set_cur)(void *, unsigned long),
	void *(*get_usrdata)(void *),
	void *(*get_per_proc)(void *, int),
	void (*put_per_proc)(void *), int (*ppd_cpu)(void *),
	void *(*alloc_read)(void),
	void (*init_request_read)(void *, unsigned long, const char *),
	int (*send_request)(void *, int, int, void *, int *),
	int (*read_ret)(void *), unsigned long (*read_pbuf)(void *),
	void (*free_fn)(void *), void *(*os_to_dev)(void *),
	unsigned long (*map_memory)(void *, unsigned long, unsigned long),
	void *(*map_virtual)(void *, unsigned long, unsigned long, void *, int),
	void (*unmap_virtual)(void *, void *, unsigned long),
	void (*unmap_memory)(void *, unsigned long, unsigned long),
	unsigned long (*buffer_pos)(void *),
	unsigned long (*buffer_size)(void *),
	unsigned long (*buffer_next_pa)(void *),
	int (*copy_to_user)(void *, void *, unsigned long, unsigned long),
	void (*no_usrdata_log)(void), void (*no_ppd_log)(int),
	void (*timeout_log)(void));
	int mcctrl_procfs_work_main_body_result(void *work, unsigned long int_size,
						int (*get_index)(void *),
						void (*add_tid)(int, int, int),
					void (*delete_tid)(int, int, int),
					void *(*os_to_dev)(void *),
					unsigned long (*map_memory)(void *,
								    unsigned long,
								    unsigned long),
					void *(*map_virtual)(void *,
							     unsigned long,
							     unsigned long,
							     void *, int),
					void (*unmap_virtual)(void *, void *,
							      unsigned long),
					void (*unmap_memory)(void *,
							     unsigned long,
							     unsigned long),
						void (*unknown_work)(int, int,
								     unsigned long),
						void (*free_work)(void *));
	int mcctrl_sysfs_packet_handler_body_result(void *os, int msg, int err,
						    long arg1, long arg2,
						    unsigned long work_size,
						    void *(*alloc)(unsigned long),
						    void (*init_schedule)(void *),
						    void (*alloc_failed)(void));
	int mcctrl_sysfs_work_main_body_result(void *work,
					       void (*req_setup)(void *, long),
					       void (*req_create)(void *, long),
					       void (*req_mkdir)(void *, long),
					       void (*req_symlink)(void *, long),
					       void (*req_lookup)(void *, long),
					       void (*req_unlink)(void *, long),
					       void (*resp_show)(void *, void *,
								 long),
					       void (*resp_store)(void *, void *,
								  long),
					       void (*resp_release)(void *, void *,
								    int),
					       void (*unknown_work)(int, void *,
								    long, long),
					       void (*free_work)(void *));
	int mcctrl_sysfs_resp_body_result(
		void *node, long result, void *(*get_req)(void *),
		void (*complete_req)(void *, long));
	long mcctrl_sysfs_remote_show_body_result(
		void *node, void *buf, unsigned long bufsize,
		void *sysfs_buf, void *sysfs_os, void *sem, void *req,
		long client_ops, long client_instance, int *stage_out,
		int (*down)(void *), void (*up)(void *),
		int (*wait_ready)(void *), void (*set_busy)(void *, int),
		int (*send)(void *, int, int, long, long, long, int),
		long (*req_lresult)(void *),
		void (*copy)(void *, const void *, unsigned long));
	long mcctrl_sysfs_remote_store_body_result(
		void *node, const void *buf, unsigned long bufsize,
		void *sysfs_buf, unsigned long sysfs_bufsize,
		void *sysfs_os, void *sem, void *req, long client_ops,
		long client_instance, int *stage_out, int (*down)(void *),
		void (*up)(void *), int (*wait_ready)(void *),
		void (*set_busy)(void *, int),
		int (*send)(void *, int, int, long, long, long, int),
		long (*req_lresult)(void *),
		void (*copy)(void *, const void *, unsigned long));
		int mcctrl_sysfs_remote_release_body_result(
			void *node, int node_type, void *sysfs_buf, void *sysfs_os,
			void *sem, void *req, long client_ops, long client_instance,
			int snt_file, int *stage_out, int (*down)(void *),
			void (*up)(void *), int (*wait_ready)(void *),
			void (*set_busy)(void *, int),
			int (*send)(void *, int, int, long, long, long, int));
		typedef int (*mcctrl_sysfs_node_type_fn_t)(void *node);
		typedef const char *(*mcctrl_sysfs_node_name_fn_t)(void *node);
		typedef void *(*mcctrl_sysfs_node_ptr_fn_t)(void *node);
		typedef void *(*mcctrl_sysfs_node_next_fn_t)(void *parent,
							     void *node);
		typedef void *(*mcctrl_sysfs_err_ptr_fn_t)(int error);
		void *mcctrl_sysfs_lookup_i_body_result(
			void *dirp, const char *name, int snt_dir,
			mcctrl_sysfs_node_type_fn_t node_type,
			mcctrl_sysfs_node_name_fn_t node_name,
			mcctrl_sysfs_node_ptr_fn_t first_child,
			mcctrl_sysfs_node_next_fn_t next_child,
			mcctrl_sysfs_err_ptr_fn_t err_ptr);
		long mcctrl_sysfs_local_show_body_result(
			void *instance, void *buf, unsigned long bufsize,
			unsigned long page_size,
		long (*get_client_ops)(void *),
		long (*get_client_instance)(void *));
	long mcctrl_sysfs_local_store_body_result(
		void *instance, const void *buf, unsigned long bufsize,
		long (*get_client_ops)(void *),
		long (*get_client_instance)(void *));
	int mcctrl_sysfs_local_release_body_result(
		void *instance, int snt_file,
		int (*get_node_type)(void *),
		long (*get_client_ops)(void *),
		long (*get_client_instance)(void *));
	long mcctrl_sysfs_show_body_result(
		void *node, void *buf, unsigned long page_size,
		long (*get_server_ops)(void *));
	long mcctrl_sysfs_store_body_result(
		void *node, const void *buf, unsigned long bufsize,
		long (*get_server_ops)(void *));
	int mcctrl_sysfs_release_body_result(
		void *node, long (*get_server_ops)(void *));
	long mcctrl_sysfs_snooping_show_i32_body_result(
		void *instance, void *buf, unsigned long bufsize);
	long mcctrl_sysfs_snooping_show_i64_body_result(
		void *instance, void *buf, unsigned long bufsize);
	long mcctrl_sysfs_snooping_show_u32_body_result(
		void *instance, void *buf, unsigned long bufsize);
	long mcctrl_sysfs_snooping_show_u64_body_result(
		void *instance, void *buf, unsigned long bufsize);
	long mcctrl_sysfs_snooping_show_string_body_result(
		void *instance, void *buf, unsigned long bufsize);
	long mcctrl_sysfs_snooping_show_u32k_body_result(
		void *instance, void *buf, unsigned long bufsize);
	typedef unsigned long (*mcctrl_sysfs_bitmap_format_fn_t)(
		void *buf, unsigned long bufsize, void *ptr, int nbits);
	long mcctrl_sysfs_snooping_show_bitmap_body_result(
		void *instance, void *buf, unsigned long bufsize,
		mcctrl_sysfs_bitmap_format_fn_t format);
	int mcctrl_sysfs_cleanup_special_local_create_body_result(
		void *instance, void (*free)(void *));
	int mcctrl_sysfs_setup_special_local_create_body_result(
		struct sysfs_req_create_param *param,
		void * const *local_ops_table,
		unsigned long bitmap_size,
		void *(*alloc)(unsigned long),
		void (*copy)(void *, const void *, unsigned long),
		void (*unknown_ops)(long));
	int mcctrl_sysfs_createf_post_path_body_result(
		void *os,
		struct sysfs_req_create_param *param,
		void * const *local_ops_table,
		unsigned long bitmap_size,
		void *(*alloc)(unsigned long),
		void (*copy)(void *, const void *, unsigned long),
		void (*unknown_ops)(long),
		int (*create_local)(void *, struct sysfs_req_create_param *),
		void (*cleanup_special)(void *, void *),
		void (*setup_failed)(int));
	int mcctrl_sysfs_mkdirf_post_path_body_result(
		void *os,
		struct sysfs_req_mkdir_param *param,
		int (*mkdir_local)(void *, struct sysfs_req_mkdir_param *));
	int mcctrl_sysfs_symlinkf_post_path_body_result(
		void *os,
		struct sysfs_req_symlink_param *param,
		int (*symlink_local)(void *, struct sysfs_req_symlink_param *));
	int mcctrl_sysfs_lookupf_post_path_body_result(
		void *os,
		struct sysfs_req_lookup_param *param,
		int (*lookup_local)(void *, struct sysfs_req_lookup_param *));
	int mcctrl_sysfs_unlinkf_post_path_body_result(
		void *os,
		struct sysfs_req_unlink_param *param,
		int (*unlink_local)(void *, struct sysfs_req_unlink_param *));
	typedef void *(*mcctrl_sysfs_os_to_dev_fn_t)(void *os);
	typedef unsigned long (*mcctrl_sysfs_map_memory_fn_t)(
		void *dev, unsigned long rpa, unsigned long size);
	typedef void *(*mcctrl_sysfs_map_virtual_fn_t)(
		void *dev, unsigned long pa, unsigned long size);
	typedef void (*mcctrl_sysfs_unmap_virtual_fn_t)(
		void *dev, void *virt, unsigned long size);
	typedef void (*mcctrl_sysfs_unmap_memory_fn_t)(
		void *dev, unsigned long pa, unsigned long size);
	typedef void (*mcctrl_sysfs_wmb_fn_t)(void);
	typedef int (*mcctrl_sysfs_req_setup_local_fn_t)(
		void *os, void *buf, unsigned long buf_pa,
		unsigned long bufsize);
	typedef int (*mcctrl_sysfs_req_create_local_fn_t)(
		void *os, struct sysfs_req_create_param *param);
	typedef int (*mcctrl_sysfs_req_mkdir_local_fn_t)(
		void *os, struct sysfs_req_mkdir_param *param);
	typedef int (*mcctrl_sysfs_req_symlink_local_fn_t)(
		void *os, struct sysfs_req_symlink_param *param);
	typedef int (*mcctrl_sysfs_req_lookup_local_fn_t)(
		void *os, struct sysfs_req_lookup_param *param);
	typedef int (*mcctrl_sysfs_req_unlink_local_fn_t)(
		void *os, struct sysfs_req_unlink_param *param);
	int mcctrl_sysfs_req_setup_body_result(
		void *os, unsigned long param_rpa, unsigned long param_size,
		mcctrl_sysfs_os_to_dev_fn_t os_to_dev,
		mcctrl_sysfs_map_memory_fn_t map_memory,
		mcctrl_sysfs_map_virtual_fn_t map_virtual,
		mcctrl_sysfs_unmap_virtual_fn_t unmap_virtual,
		mcctrl_sysfs_unmap_memory_fn_t unmap_memory,
		mcctrl_sysfs_req_setup_local_fn_t setup_local,
		mcctrl_sysfs_wmb_fn_t wmb);
	int mcctrl_sysfs_req_create_body_result(
		void *os, unsigned long param_rpa, unsigned long param_size,
		mcctrl_sysfs_os_to_dev_fn_t os_to_dev,
		mcctrl_sysfs_map_memory_fn_t map_memory,
		mcctrl_sysfs_map_virtual_fn_t map_virtual,
		mcctrl_sysfs_unmap_virtual_fn_t unmap_virtual,
		mcctrl_sysfs_unmap_memory_fn_t unmap_memory,
		mcctrl_sysfs_req_create_local_fn_t create_local,
		mcctrl_sysfs_wmb_fn_t wmb);
	int mcctrl_sysfs_req_mkdir_body_result(
		void *os, unsigned long param_rpa, unsigned long param_size,
		mcctrl_sysfs_os_to_dev_fn_t os_to_dev,
		mcctrl_sysfs_map_memory_fn_t map_memory,
		mcctrl_sysfs_map_virtual_fn_t map_virtual,
		mcctrl_sysfs_unmap_virtual_fn_t unmap_virtual,
		mcctrl_sysfs_unmap_memory_fn_t unmap_memory,
		mcctrl_sysfs_req_mkdir_local_fn_t mkdir_local,
		mcctrl_sysfs_wmb_fn_t wmb);
	int mcctrl_sysfs_req_symlink_body_result(
		void *os, unsigned long param_rpa, unsigned long param_size,
		mcctrl_sysfs_os_to_dev_fn_t os_to_dev,
		mcctrl_sysfs_map_memory_fn_t map_memory,
		mcctrl_sysfs_map_virtual_fn_t map_virtual,
		mcctrl_sysfs_unmap_virtual_fn_t unmap_virtual,
		mcctrl_sysfs_unmap_memory_fn_t unmap_memory,
		mcctrl_sysfs_req_symlink_local_fn_t symlink_local,
		mcctrl_sysfs_wmb_fn_t wmb);
	int mcctrl_sysfs_req_lookup_body_result(
		void *os, unsigned long param_rpa, unsigned long param_size,
		mcctrl_sysfs_os_to_dev_fn_t os_to_dev,
		mcctrl_sysfs_map_memory_fn_t map_memory,
		mcctrl_sysfs_map_virtual_fn_t map_virtual,
		mcctrl_sysfs_unmap_virtual_fn_t unmap_virtual,
		mcctrl_sysfs_unmap_memory_fn_t unmap_memory,
		mcctrl_sysfs_req_lookup_local_fn_t lookup_local,
		mcctrl_sysfs_wmb_fn_t wmb);
	int mcctrl_sysfs_req_unlink_body_result(
		void *os, unsigned long param_rpa, unsigned long param_size,
		mcctrl_sysfs_os_to_dev_fn_t os_to_dev,
		mcctrl_sysfs_map_memory_fn_t map_memory,
		mcctrl_sysfs_map_virtual_fn_t map_virtual,
		mcctrl_sysfs_unmap_virtual_fn_t unmap_virtual,
		mcctrl_sysfs_unmap_memory_fn_t unmap_memory,
		mcctrl_sysfs_req_unlink_local_fn_t unlink_local,
		mcctrl_sysfs_wmb_fn_t wmb);

	#endif /* MCCTRL_RUST_HELPERS */

#endif /* MCCTRL_RUST_H */
