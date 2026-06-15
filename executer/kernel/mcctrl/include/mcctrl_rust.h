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
void *mcctrl_rva_to_rpa_cache_search_body_result(void *root,
						 unsigned long rva);
int mcctrl_rva_to_rpa_cache_insert_body_result(
	void *root, void *cache_node,
	void (*link_node)(void *, void *, void *),
	void (*insert_color)(void *, void *));
int mcctrl_futex_remove_process_body_result(
	void *root, void *(*rb_first)(void *),
	void (*rb_erase)(void *, void *), void (*free_node)(void *));
int mcctrl_procfs_packet_handler_body_result(void *os, int msg, int pid,
					     unsigned long arg,
					     unsigned long resp_pa,
					     unsigned long work_size,
					     void *(*alloc)(unsigned long),
					     void (*init_schedule)(void *),
					     void (*alloc_failed)(void));
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

	#endif /* MCCTRL_RUST_HELPERS */

#endif /* MCCTRL_RUST_H */
