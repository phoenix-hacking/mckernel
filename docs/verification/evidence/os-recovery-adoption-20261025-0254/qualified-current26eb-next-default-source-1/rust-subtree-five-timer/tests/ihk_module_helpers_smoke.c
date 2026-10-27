#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>

struct fake_smp_os_info_offsets;
struct fake_smp_special_addr_offsets;
struct fake_smp_query_status_offsets;

extern void ihk_core_pagealloc_reserve_padding_result(unsigned long *map,
		unsigned long mapsize, unsigned long mapaligned);
extern unsigned long ihk_core_pagealloc_large_alloc_result(unsigned long *map,
		unsigned long count, unsigned long last, int nblocks,
		unsigned long start, unsigned int shift);
extern unsigned long ihk_core_pagealloc_small_alloc_result(unsigned long *map,
		unsigned long count, unsigned long last, int npages,
		unsigned long start, unsigned int shift);
extern void ihk_core_pagealloc_free_blocks_result(unsigned long *map,
		unsigned long start, unsigned long address, int npages,
		unsigned int shift);
extern int ihk_core_open_ref_mode_result(int flags, int sharable_mask);
extern void *ihk_host_map_generic(void *dev, unsigned long phys, void *virt,
		unsigned long size, int flags);
extern int ihk_host_unmap_generic(void *dev, void *virt, unsigned long size);
extern void *ihk_pagealloc_init(unsigned long start, unsigned long size,
		unsigned long unit);
extern void ihk_pagealloc_destroy(void *desc);
extern unsigned long ihk_pagealloc_alloc(void *desc, int npages);
extern void ihk_pagealloc_free(void *desc, unsigned long address, int npages);
extern unsigned long ihk_pagealloc_alloc_size(void *desc, unsigned long size);
extern void ihk_pagealloc_free_size(void *desc, unsigned long address,
		unsigned long size);
extern void *ihk_ikc_get_master_channel(void *os);
extern void *ihk_ikc_alloc_queue(int qpages);
extern void ihk_ikc_free_queue(void *queue);
extern void *ihk_ikc_malloc(int size);
extern void ihk_ikc_free(void *ptr);
extern int ihk_ikc_send(void *channel, void *packet, int opt);
extern int call_arch_master_packet_handler(void *os, void *channel,
		void *packet);
extern void ihk_ikc_wait_init(void *wait);
extern int ihk_ikc_wait_master(void *wait);
extern void ihk_ikc_wake_master(void *wait);
extern void ihk_ikc_system_init(void *os);
extern void ihk_ikc_system_exit(void *os);
extern void *ihk_core_os_get_regular_channel_result(void *os, int cpu);
extern int ihk_core_os_set_regular_channel_result(void *os, void *channel,
		int cpu, int max_cpu);
extern void *ihk_core_host_os_get_ikc_handler_result(void *os);
extern void *ihk_core_ikc_get_listener_lock_result(void *os);
extern void *ihk_core_ikc_get_listener_entry_result(void *os, int port);
extern int ihk_core_ikc_call_master_packet_handler_result(void *os,
		void *channel, void *packet,
		int (*handler)(void *channel, void *packet, void *os));
extern void *ihk_core_ikc_get_master_wait_list_result(void *os);
extern void *ihk_core_ikc_get_master_wait_lock_result(void *os);
extern void *ihk_core_os_get_master_channel_result(void *os);
extern int ihk_core_os_get_unique_channel_id_result(void *channel_id,
		int (*atomic_inc_return_fn)(void *channel_id));
extern void *ihk_core_host_ikc_init_first_result(void *os,
		int (*handler)(void *channel, void *packet, void *os),
		unsigned long alloc_size,
		void (*system_init_fn)(void *os),
		int (*wait_for_status_fn)(void *os, int status,
			int sleepable, int timeout),
		void (*get_special_address_fn)(void *os, int type,
			unsigned long *addr, unsigned long *size),
		unsigned long (*map_memory_fn)(void *dev, unsigned long pa,
			unsigned long size),
		void *(*map_virtual_fn)(void *dev, unsigned long pa,
			unsigned long size, void *priv, int flags),
		void *(*alloc_fn)(unsigned long size),
		void (*init_desc_fn)(void *channel, void *os,
			void *recv_queue, void *send_queue),
		void (*set_cpu_fn)(void *channel, int cpu),
		void (*publish_queues_fn)(void *channel,
			unsigned long recv_phys, unsigned long send_phys,
			unsigned long recv_remote, unsigned long send_remote),
		void (*ready_failed_fn)(void *os));
extern int ihk_core_ikc_master_init_result(void *os,
		int (*handler)(void *channel, void *packet, void *os),
		void *(*init_first_fn)(void *os,
			int (*handler)(void *channel, void *packet, void *os)),
		void (*enable_fn)(void *channel),
		int (*send_fn)(void *channel, void *packet, int opt));
extern int ihk_core_ikc_master_finalize_result(void *os,
		void (*destroy_fn)(void *channel),
		void (*system_exit_fn)(void *os));
extern int ihk_core_ikc_linux_init_work_data_result(void *os,
		void (*work_fn)(void *work));
extern int ihk_core_ikc_linux_schedule_work_result(void *os,
		void *(*alloc_fn)(unsigned long size),
		void (*init_work_fn)(void *work, void (*work_fn)(void *work)),
		int (*current_cpu_fn)(void),
		void (*schedule_on_fn)(int cpu, void *work));
extern void *ihk_core_ikc_linux_get_os_from_work_result(void *work);
extern int ihk_core_ikc_send_interrupt_result(void *channel, int vector,
		void *(*remote_os_fn)(void *channel),
		int (*read_cpu_fn)(void *channel),
		int (*issue_interrupt_fn)(void *os, int cpu, int vector));
extern int ihk_core_os_boot_result(void *os, int flag,
		int (*index_fn)(void *os),
		unsigned long (*kmsg_lock_fn)(void),
		void *(*kmsg_find_fn)(int os_index),
		void (*kmsg_inc_fn)(void *container),
		void (*kmsg_unlock_fn)(unsigned long flags),
		int (*notifier_down_fn)(void),
		int (*os_boot_fn)(void *os, int flag),
		int (*master_init_fn)(void *os),
		int (*notify_boot_fn)(int os_index),
		void (*master_finalize_fn)(void *os),
		int (*os_shutdown_fn)(void *os, int flag),
		void (*notifier_up_fn)(void),
		void (*kmsg_dec_fn)(void *container));
extern int ihk_core_os_shutdown_result(void *os, int flag,
		int (*status_fn)(void *os),
		int (*index_fn)(void *os),
		int (*wait_for_status_fn)(void *os, int status,
			int sleepable, int timeout),
		int (*thaw_fn)(void *os),
		void (*send_nmi_delay_fn)(void *os, int mode,
			unsigned int delay_ms),
		int (*notifier_down_fn)(void),
		void (*notify_shutdown_fn)(int os_index),
		void (*notifier_up_fn)(void),
		void (*master_finalize_fn)(void *os),
		int (*os_shutdown_fn)(void *os, int flag),
		int (*release_kmsg_fn)(void *container),
		void (*log_fn)(int event, int value));
extern int ihk_core_os_set_kargs_body_result(void *os, void *kbuf,
		int (*call_fn)(void *os, void *kbuf));
extern int ihk_core_os_dump_body_result(void *os, void *args,
		int (*call_fn)(void *os, void *args));
extern long ihk_core_host_os_write_body_result(void *os,
		const void *buf, unsigned long size, long long *off,
		unsigned long max_size,
		void *(*alloc_fn)(unsigned long size),
		unsigned long (*copy_from_user_fn)(void *dst, const void *src,
			unsigned long size),
		int (*load_memory_fn)(void *os, void *buf, unsigned long size,
			unsigned long offset),
		void (*free_fn)(void *ptr));
extern long ihk_core_host_device_io_body_result(void *dev, void *buf,
		unsigned long size, long long *off, int mode,
		unsigned long (*map_memory_fn)(void *dev, unsigned long off,
			unsigned long size),
		void *(*map_virtual_fn)(void *dev, unsigned long pa,
			unsigned long size),
		unsigned long (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size),
		unsigned long (*copy_from_user_fn)(void *dst, const void *src,
			unsigned long size),
		void (*unmap_virtual_fn)(void *dev, void *va,
			unsigned long size));
extern int ihk_core_os_status_body_result(void *os,
		int (*status_fn)(void *os));
extern int ihk_core_os_freeze_body_result(void *os,
		int (*status_fn)(void *os), int (*freeze_fn)(void *os),
		void (*log_fn)(int event, int value));
extern int ihk_core_os_thaw_body_result(void *os,
		int (*status_fn)(void *os),
		int (*wait_for_status_fn)(void *os, int status,
			int sleepable, int timeout),
		int (*thaw_fn)(void *os), void (*log_fn)(int event, int value));
extern int ihk_core_os_get_usage_body_result(void *os, void *buf,
		void (*setup_monitor_fn)(void *os),
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size));
extern int ihk_core_os_get_cpu_usage_body_result(void *os, void *buf,
		void (*setup_monitor_fn)(void *os),
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size));
extern int ihk_core_os_read_kaddr_body_result(void *os, void *desc,
		int (*vtop_fn)(void *os, unsigned long kaddr,
			unsigned long *phys),
		const void *(*phys_to_virt_fn)(unsigned long phys),
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size));
extern int ihk_core_read_kmsg_body_result(unsigned long kmsg_buf_addr,
		char *buf, int shift, unsigned long lock_offset,
		unsigned long tail_offset, unsigned long len_offset,
		unsigned long head_offset, unsigned long str_offset,
		unsigned long (*irq_save_fn)(void),
		void (*irq_restore_fn)(unsigned long flags),
		void (*cpu_relax_fn)(void));
extern int ihk_core_clear_kmsg_body_result(unsigned long kmsg_buf_addr,
		unsigned long lock_offset, unsigned long tail_offset,
		unsigned long head_offset, unsigned long str_offset,
		unsigned long str_len, unsigned long (*irq_save_fn)(void),
		void (*irq_restore_fn)(unsigned long flags),
		void (*cpu_relax_fn)(void));
extern int ihk_core_os_read_kmsg_body_result(void *os, void *buf,
		void *(*alloc_fn)(unsigned long size),
		int (*read_kmsg_fn)(void *kmsg_buf, char *buf, int shift),
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size),
		void (*free_fn)(void *ptr));
extern int ihk_core_os_clear_kmsg_body_result(void *os,
		unsigned long lock_offset, unsigned long tail_offset,
		unsigned long head_offset, unsigned long str_offset,
		unsigned long str_len, unsigned long (*irq_save_fn)(void),
		void (*irq_restore_fn)(unsigned long flags),
		void (*cpu_relax_fn)(void));
extern int ihk_core_device_get_kmsg_buf_body_result(void *desc,
		unsigned long (*kmsg_lock_fn)(void),
		void *(*kmsg_find_fn)(int os_index),
		void (*kmsg_inc_fn)(void *container),
		void (*kmsg_unlock_fn)(unsigned long flags),
		unsigned long (*copy_from_user_fn)(void *dst, const void *src,
			unsigned long size),
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size));
extern int ihk_core_device_read_kmsg_buf_body_result(void *desc,
		void *(*alloc_fn)(unsigned long size),
		int (*read_kmsg_fn)(void *kmsg_buf, char *buf, int shift),
		unsigned long (*copy_from_user_fn)(void *dst, const void *src,
			unsigned long size),
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size),
		void (*free_fn)(void *ptr));
extern int ihk_core_device_release_kmsg_buf_body_result(void *handle,
		int (*release_kmsg_fn)(void *container));
extern int arch_symbols_init(void);
extern int reserve_user_space(void *usrdata, unsigned long *startp,
		unsigned long *endp);
extern void get_vdso_info(void *os, long vdso_rpa);
extern void *get_user_sp(void);
extern void set_user_sp(void *usp);
extern void restore_tls(unsigned long addr);
extern void save_tls_ctx(void *ctx);
extern unsigned long get_tls_ctx(void *ctx);
extern unsigned long get_rsp_ctx(void *ctx);
extern int translate_rva_to_rpa(void *os, unsigned long rpt,
		unsigned long rva, unsigned long *rpap,
		unsigned long *pgsizep);
extern long arch_switch_ctx(void *desc);
extern int load_elf(void *bprm);
extern void binfmt_mcexec_init(void);
extern void binfmt_mcexec_exit(void);
extern int ihk_core_open_exclusive_busy_result(int previous_refcount);
extern int ihk_core_open_callback_failed_result(int callback_ret);
extern int ihk_core_open_callback_present_result(unsigned long open_cb_addr);
extern int ihk_core_close_callback_present_result(unsigned long close_cb_addr);
extern int ihk_core_release_handler_present_result(unsigned long handler_addr);
extern int ihk_core_init_callback_present_result(unsigned long init_cb_addr);
extern int ihk_core_init_callback_failed_result(int init_ret);
extern int ihk_core_exit_callback_present_result(unsigned long exit_cb_addr);
extern int ihk_core_register_minor_action_result(int free_index,
		int current_max_minor, int max_minor);
extern int ihk_core_register_alloc_failed_result(unsigned long data_addr);
extern int ihk_core_register_should_shrink_minor_result(int minor,
		int current_max_minor);
extern int ihk_core_register_cdev_add_failed_result(int cdev_ret);
extern int ihk_core_register_device_create_failed_result(int is_error);
extern int ihk_core_refcount_busy_result(int refcount);
extern int ihk_core_kmsg_release_precheck_result(int refcount);
extern int ihk_core_kmsg_release_should_delete_result(int refcount_after_dec);
extern int ihk_core_kmsg_stray_delete_count_result(int nbufs, int max_bufs);
extern int ihk_core_destroy_callback_present_result(unsigned long destroy_cb_addr);
extern int ihk_core_destroy_callback_failed_result(int destroy_ret);
extern int ihk_core_destroy_os_pointer_invalid_result(unsigned long os_addr,
		unsigned long os_invalid_addr, unsigned long data_addr,
		unsigned long data_invalid_addr, unsigned long os_dev_data_addr);
extern int ihk_core_destroy_all_os_candidate_result(unsigned long os_addr,
		unsigned long os_invalid_addr, unsigned long os_dev_data_addr,
		unsigned long data_addr);
extern int ihk_core_destroy_all_os_should_restore_result(int destroy_ret);
extern int ihk_core_event_list_cleanup_needed_result(int list_empty);
extern int ihk_core_notifier_match_result(unsigned long entry_addr,
		unsigned long target_addr);
extern int ihk_core_notifier_should_add_result(int registered);
extern int ihk_core_notifier_should_remove_result(int registered);
extern int ihk_core_load_file_mode_result(unsigned long load_file_addr,
		unsigned long load_mem_addr);
extern int ihk_core_file_size_valid_result(long long size);
extern int ihk_core_kernel_read_failed_result(long read_ret);
extern int ihk_core_load_file_continue_result(int ret,
		unsigned long long done, unsigned long long size);
extern unsigned int ihk_core_shutdown_status_policy_result(int status);
extern void ihk_core_kmsg_buf_init_result(unsigned long buf_addr,
		unsigned long lock_offset, unsigned long tail_offset,
		unsigned long len_offset, unsigned long head_offset,
		unsigned long str_offset, unsigned long str_len);
extern void ihk_core_kmsg_buf_clear_result(unsigned long buf_addr,
		unsigned long tail_offset, unsigned long head_offset,
		unsigned long str_offset, unsigned long str_len);
extern void ihk_core_kmsg_container_init_result(unsigned long cont_addr,
		unsigned long os_index_offset, unsigned long kmsg_buf_offset,
		unsigned long order_offset, int os_index,
		unsigned long kmsg_buf_addr, unsigned int order);
extern void ihk_core_atomic_set_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset, int value);
extern int ihk_core_atomic_read_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern void ihk_core_atomic_inc_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern void ihk_core_atomic_dec_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern int ihk_core_atomic_dec_return_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset);
extern int ihk_core_atomic_cmpxchg_i32_result(unsigned long obj_addr,
		unsigned long atomic_offset, int old, int new);
extern unsigned long ihk_core_os_take_kmsg_container_result(
		unsigned long os_addr, unsigned long container_offset);
extern void ihk_core_list_add_tail_result(unsigned long entry_addr,
		unsigned long head_addr);
extern void ihk_core_list_del_result(unsigned long entry_addr,
		unsigned long poison_next, unsigned long poison_prev);
extern int ihk_core_list_contains_entry_result(unsigned long head_addr,
		unsigned long list_offset, unsigned long target_addr);
extern unsigned long ihk_core_list_next_entry_result(unsigned long head_addr,
		unsigned long list_offset, unsigned long cursor_addr);
extern unsigned long ihk_core_kmsg_find_by_os_index_reverse_result(
		unsigned long head_addr, unsigned long list_offset,
		unsigned long os_index_offset, int os_index);
extern int ihk_core_dma_request_result(void *channel, void *request);
extern int ihk_core_os_debug_request_body_result(void *os,
		unsigned int request, unsigned long arg,
		int (*present_fn)(void *os),
		int (*call_fn)(void *os, unsigned int request,
			unsigned long arg));
extern int ihk_core_device_debug_request_body_result(void *dev,
		unsigned int request, unsigned long arg,
		int (*present_fn)(void *dev),
		int (*call_fn)(void *dev, unsigned int request,
			unsigned long arg));
extern int ihk_core_os_resource_body_result(void *os, void *resource,
		int op, unsigned long first, unsigned long second,
		int (*alloc_resource_fn)(void *os, void *resource));
extern int ihk_core_device_get_buildid_body_result(void *user_addr,
		const char *buildid, unsigned long buildid_len,
		int (*copy_to_user_fn)(void *dst, const void *src,
			unsigned long size));
extern int ihk_core_device_op_body_result(void *dev, int op,
		unsigned long arg,
		int (*present_fn)(void *dev, int op),
		int (*call_fn)(void *dev, int op, unsigned long arg));
extern long ihk_core_os_ioctl_call_aux_result(void *os,
		unsigned int request, unsigned long arg, void *file);
extern int ihk_core_os_register_user_call_handlers_result(void *os,
		void *clist, unsigned long (*lock_fn)(void *os),
		void (*unlock_fn)(void *os, unsigned long flags));
extern void ihk_core_os_unregister_user_call_handlers_result(void *os,
		void *clist, unsigned long (*lock_fn)(void *os),
		void (*unlock_fn)(void *os, unsigned long flags));
extern int ihk_core_host_register_os_notifier_result(void *head,
		void *notifier, unsigned long list_offset,
		int (*down_fn)(void), void (*up_fn)(void),
		void (*log_fn)(int event));
extern int ihk_core_host_deregister_os_notifier_result(void *head,
		void *notifier, unsigned long list_offset,
		int (*down_fn)(void), void (*up_fn)(void),
		void (*log_fn)(int event));
extern int mcctrl_pte_is_write_combined_result(unsigned long flags);
extern int xchg4(int *ptr, int x);
extern int mcctrl_control_request_needs_root_result(unsigned int request);
extern int mcctrl_control_perm_result(unsigned int request, unsigned int euid);
extern int mcctrl_cpu_register_copyback_result(int op, int read_op);
extern int mcctrl_lwk_to_linux_index_result(const int *mapping, int count,
		int index);
extern int mcctrl_linux_to_lwk_index_result(const int *mapping, int count,
		int linux_id);
extern int mcctrl_translate_cpumap_result(const int *mapping, int count,
		const void *linmap, void *mckmap, int nr_cpu_ids);
extern int mckernel_cpu_2_linux_cpu(void *usrdata, int cpu_id);
extern int mckernel_cpu_2_hw_id(void *usrdata, int cpu_id);
extern int linux_cpu_2_mckernel_cpu(void *usrdata, int cpu_id);
extern int mckernel_numa_2_linux_numa(void *usrdata, int numa_id);
extern int linux_numa_2_mckernel_numa(void *usrdata, int numa_id);
extern void mcctrl_fill_sequential_bitset_result(unsigned long *bits,
		int bit_count, int word_count, int bits_per_word);
extern int mcctrl_read_buffer_status_result(char *buf, unsigned long size,
		long bytes_read);
extern int mcctrl_parse_long_result(const char *buf, long *value_out);
extern int mcctrl_pci_realpath_valid_result(const char *path);
extern int mcctrl_ptr_hash_result(unsigned long ptr, unsigned long mask);
extern int mcctrl_ptr_eq_result(unsigned long a, unsigned long b);
extern int mcctrl_file_to_pidfd_lookup_match_result(unsigned long entry_filp,
		unsigned long filp, unsigned long entry_group_leader,
		unsigned long group_leader);
extern int mcctrl_file_to_pidfd_remove_match_result(unsigned long entry_filp,
		unsigned long filp, unsigned long entry_os, unsigned long os,
		unsigned long entry_group_leader, unsigned long group_leader,
		int entry_fd, int fd);
extern void mc_plist_head_init(void *head, void *lock);
extern void mc_plist_head_init_raw(void *head, void *lock);
extern void mc_plist_node_init(void *node, int prio);
extern void mc_plist_add(void *node, void *head);
extern void mc_plist_del(void *node, void *head);
extern int mc_plist_head_empty(const void *head);
extern int mc_plist_node_empty(const void *node);
extern void *mc_plist_first(const void *head);
extern void ihk_mc_spinlock_init(void *lock);
extern void __ihk_mc_spinlock_lock_noirq(void *lock);
extern void __ihk_mc_spinlock_unlock_noirq(void *lock);
extern void mcs_rwlock_writer_lock_noirq(void *lock);
extern void mcs_rwlock_writer_unlock_noirq(void *lock);
extern void refcount_set(void *r, unsigned int n);
extern unsigned int refcount_read(const void *r);
extern bool refcount_add_not_zero(unsigned int i, void *r);
extern void refcount_add(unsigned int i, void *r);
extern bool refcount_inc_not_zero(void *r);
extern void refcount_inc(void *r);
extern bool refcount_sub_and_test(unsigned int i, void *r);
extern bool refcount_dec_and_test(void *r);
extern void refcount_dec(void *r);
extern int get_futex_value_locked(unsigned int *dest, unsigned int *from);
extern int futex_atomic_cmpxchg_inatomic(int *uaddr, int oldval, int newval);
extern int futex_atomic_op_inuser(int encoded_op, int *uaddr);
extern unsigned int mc_jhash2(const unsigned int *k, unsigned int length,
		unsigned int initval);
extern int mcctrl_tofu_dev_path_result(const char *path);
extern unsigned long mcctrl_tofu_dev_tail_offset_result(void);
extern void mcctrl_tofu_dev_name_copy_result(char *dst,
		unsigned long dst_size, const char *path);
extern int mcctrl_tofu_cq_path_parse_result(const char *path, int *tni_out,
		int *cq_out);
extern int is_special_sysfs_ops(void *ops);
extern int mcctrl_sysfs_inited_result(unsigned long sysfs_buf);
extern int mcctrl_sysfs_path_error_result(const char *path, long written,
		unsigned long path_size);
extern int mcctrl_zero_mckernel_pages_step_result(unsigned long node_addr,
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
extern void mcctrl_zero_mckernel_pages_finish_result(unsigned long node_addr,
		unsigned long zeroing_workers_offset);
extern int ihk_smp_pack_available_cpus_result(const void *cpus, int cpu_count,
		unsigned long stride, unsigned long status_offset,
		int available_status, int *out, int capacity, int *needed);
extern int ihk_smp_pack_assigned_ikc_map_result(const void *cpus,
		int cpu_count, unsigned long stride, unsigned long status_offset,
		unsigned long os_offset, unsigned long ikc_offset,
		unsigned long target_os, int assigned_status, int *src_out,
		int *dst_out, int capacity, int *needed);
extern int ihk_smp_assign_scan_action_result(int chunk_numa,
		int requested_numa, unsigned long chunk_size,
		unsigned long requested_size, int has_max,
		unsigned long current_max_size, int has_match);
extern int ihk_smp_assign_no_chunk_action_result(unsigned long want,
		unsigned long all_marker, unsigned long size_left,
		unsigned long fake_chunk_size);
extern int ihk_smp_used_chunk_insert_before_result(unsigned long new_addr,
		unsigned long iter_addr);
extern int ihk_smp_validate_cpu_req_body_result(int num_cpus, int has_cpus,
		int max_cpus, void (*log_fn)(int event, int value));
extern int ihk_smp_validate_ikc_req_body_result(int num_cpus,
		int has_src_cpus, int has_dst_cpus, int max_cpus,
		void (*log_fn)(int event, int value));
extern int ihk_smp_validate_mem_req_body_result(int num_chunks,
		int has_sizes, int has_numa_ids, int min_chunk_size,
		int max_size_ratio_all, int max_size_ratio_limit,
		void (*log_fn)(int event, int value));
extern int ihk_smp_set_status_body_result(unsigned long object,
		unsigned long lock_offset, unsigned long status_offset,
		int status, unsigned long (*lock_fn)(unsigned long lock_addr),
		void (*unlock_fn)(unsigned long lock_addr, unsigned long flags));
extern void ihk_smp_core_set(int n, void *p);
extern void ihk_smp_core_clear(int n, void *p);
extern int ihk_smp_core_isset(int n, const void *p);
extern void ihk_smp_core_zero(void *p);
extern int ihk_smp_core_isset_any(const void *p);
extern int ihk_smp_build_os_info_body_result(unsigned long os,
		const struct fake_smp_os_info_offsets *offsets);
extern int ihk_smp_get_special_addr_body_result(unsigned long param,
		int special_type,
		const struct fake_smp_special_addr_offsets *offsets,
		unsigned long master_ikcq_size, unsigned long int_size,
		unsigned long *addr, unsigned long *size);
extern int ihk_smp_wait_for_status_body_result(unsigned long ihk_os,
		unsigned long priv_data, int wanted_status, int sleepable,
		int timeout,
		int (*query_fn)(unsigned long ihk_os, unsigned long priv_data),
		void (*delay_fn)(unsigned long msecs),
		void (*log_fn)(int wanted_status, int current_status));
extern int ihk_smp_query_status_body_result(int status, long param_status,
		unsigned long data,
		const struct fake_smp_query_status_offsets *offsets,
		void (*setup_monitor_fn)(unsigned long data),
		void (*restore_trampoline_fn)(void),
		void (*log_fn)(int event, int value0, int value1));
extern int ihk_smp_set_mode_body_result(unsigned long ihk_os,
		unsigned long priv_data, int special_type, int mode,
		unsigned long page_size,
		int (*get_special_addr_fn)(unsigned long ihk_os,
			unsigned long priv_data, int special_type,
			unsigned long *addr, unsigned long *size),
		unsigned long (*map_memory_fn)(unsigned long ihk_os,
			unsigned long priv_data, unsigned long phys,
			unsigned long size),
		unsigned long (*map_virtual_fn)(unsigned long ihk_os,
			unsigned long priv_data, unsigned long phys,
			unsigned long size),
		int (*unmap_virtual_fn)(unsigned long ihk_os,
			unsigned long priv_data, unsigned long virt,
			unsigned long size),
		int (*unmap_memory_fn)(unsigned long ihk_os,
			unsigned long priv_data, unsigned long phys,
			unsigned long size));

#define BASE 0x100000UL
#define SHIFT 12U
#define OPEN_REF_INC 1
#define OPEN_REF_CMPXCHG 2
#define MINOR_FULL -1
#define MINOR_REUSE 0
#define MINOR_EXTEND 1
#define LOAD_FILE_NONE 0
#define LOAD_FILE_DIRECT 1
#define LOAD_FILE_MEM 2
#define RESOURCE_FLAG_CPU_SPECIFIED 0x1
#define RESOURCE_FLAG_MEM_SPECIFIED 0x2
#define OS_RESOURCE_ALLOC_MEM 1
#define OS_RESOURCE_ALLOC_CPU 2
#define OS_RESOURCE_RESERVE_CPU 3
#define OS_RESOURCE_RESERVE_MEM 4
#define DEVICE_IO_READ 1
#define DEVICE_IO_WRITE 2
#define HOST_KMSG_ALLOC_SIZE ((4UL << 20) - 4096)
#define OS_FREEZE_LOG_INVALID 1
#define OS_THAW_LOG_INVALID 1
#define OS_THAW_LOG_WAIT_FROZEN 2
#define OS_THAW_LOG_WAIT_TIMEOUT 3
#define READ_KADDR_PHYS 1
#define DEVICE_OP_RESERVE_CPU 1
#define DEVICE_OP_RELEASE_CPU 2
#define DEVICE_OP_RESERVE_MEM 3
#define DEVICE_OP_RELEASE_MEM 4
#define DEVICE_OP_RELEASE_MEM_PARTIAL 5
#define DEVICE_OP_GET_NUM_CPUS 6
#define DEVICE_OP_QUERY_CPU 7
#define DEVICE_OP_QUERY_MEM 8
#define OS_STATUS_NOT_BOOTED 0
#define OS_STATUS_LOADING 1
#define OS_STATUS_BOOTING 2
#define OS_STATUS_BOOTED 3
#define OS_STATUS_READY 4
#define OS_STATUS_RUNNING 5
#define OS_STATUS_FREEZING 6
#define OS_STATUS_FROZEN 7
#define OS_STATUS_SHUTDOWN 8
#define OS_STATUS_FAILED 9
#define OS_STATUS_HUNGUP 10
#define IHK_IKC_MASTER_MSG_INIT_ACK 0x10203010U
#define IHK_SPADDR_KMSG 1
#define IHK_SPADDR_MIKC_QUEUE_RECV 2
#define IHK_SPADDR_MIKC_QUEUE_SEND 3
#define IHK_SPADDR_MONITOR 4
#define IHK_SPADDR_RUSAGE 5
#define IHK_SPADDR_NMI_MODE 6
#define IHK_SPADDR_MCKERNEL_DO_FUTEX 7
#define IHK_SPADDR_MULTI_INTR_MODE 8
#define IHK_OS_AUX_CALL_START 0x10000000U
#define IHK_OS_AUX_CALL_END 0x7fffffffU
#define SHUTDOWN_WAIT_FROZEN 0x1U
#define SHUTDOWN_THAW 0x2U
#define SHUTDOWN_WAIT_READY 0x4U
#define SHUTDOWN_WAIT_RUNNING 0x8U
#define SHUTDOWN_NOT_BOOTED 0x10U
#define SHUTDOWN_BUSY 0x20U
#define SHUTDOWN_WARN_LOADING 0x40U
#define SHUTDOWN_LOG_BUSY 1
#define SHUTDOWN_LOG_WAIT_FROZEN 2
#define SHUTDOWN_LOG_WAIT_FROZEN_TIMEOUT 3
#define SHUTDOWN_LOG_THAW 4
#define SHUTDOWN_LOG_THAW_ERROR 5
#define SHUTDOWN_LOG_WAIT_READY 6
#define SHUTDOWN_LOG_WAIT_READY_TIMEOUT 7
#define SHUTDOWN_LOG_WAIT_RUNNING 8
#define SHUTDOWN_LOG_WAIT_RUNNING_TIMEOUT 9
#define SHUTDOWN_LOG_NOT_BOOTED 10
#define SHUTDOWN_LOG_WARN_LOADING 11
#define SHUTDOWN_LOG_SHUTDOWN_ERROR 12
#define SHUTDOWN_LOG_RELEASE_ERROR 13
#define SHUTDOWN_LOG_OK 14
#define NOTIFIER_LOG_ADDED 1
#define NOTIFIER_LOG_REMOVED 2
#define ASSIGN_SCAN_SKIP 0
#define ASSIGN_SCAN_UPDATE_MAX 1
#define ASSIGN_SCAN_EXACT 2
#define ASSIGN_NO_CHUNK_ERROR 0
#define ASSIGN_NO_CHUNK_ALL_DONE 1
#define ASSIGN_NO_CHUNK_FAKE_DONE 2
#define SMP_VALIDATE_LENGTH 1
#define SMP_VALIDATE_NULL 2
#define SMP_VALIDATE_MIN_CHUNK 3
#define SMP_VALIDATE_RATIO 4
#define SMP_QUERY_LOG_UNKNOWN_STATUS 1
#define SMP_QUERY_LOG_BEFORE_MONITOR 2
#define SMP_QUERY_LOG_PANIC_CPU 3
#define SMP_QUERY_LOG_AFTER_MONITOR 4
#define IHK_OS_MONITOR_IDLE 1
#define IHK_OS_MONITOR_KERNEL_FREEZING 8
#define IHK_OS_MONITOR_KERNEL_FROZEN 9
#define IHK_OS_MONITOR_PANIC 99
#define SMP_MEM_ALL (~0UL)
#define LIST_POISON_NEXT 0x11111111UL
#define LIST_POISON_PREV 0x22222222UL
#define STATUS_AVAILABLE 2
#define STATUS_ASSIGNED 3
#define OS_DATA_SIZE 4584
#define OS_OFF_DEV_DATA 0
#define OS_OFF_LOCK 8
#define OS_OFF_MINOR 160
#define OS_OFF_KMSG_CONTAINER 232
#define OS_OFF_IKC_INITIALIZED 288
#define OS_OFF_IKC_HANDLER 312
#define OS_OFF_PACKET_HANDLER 4488
#define OS_OFF_MCHANNEL 368
#define OS_OFF_REGULAR_CHANNELS 376
#define OS_OFF_LISTENER_LOCK 384
#define OS_OFF_LISTENERS 392
#define OS_OFF_WORK_FUNCTION 360
#define OS_OFF_CHANNEL_ID 4496
#define OS_OFF_WAIT_LOCK 4500
#define OS_OFF_WAIT_LIST 4504
#define OS_OFF_AUX_CALL_LIST 4520
#define IKC_WORK_SIZE 72
#define IKC_WORK_OS_OFFSET 64
#define FAKE_MASTER_CHANNEL_ALLOC_SIZE 344

struct fake_smp_cpu {
	int id;
	int hw_id;
	int status;
	unsigned long os;
	int ikc_map_cpu;
};

struct fake_smp_monitor_cpu {
	int status;
	int status_bak;
	unsigned long counter;
	unsigned long ocounter;
};

struct fake_smp_monitor {
	unsigned long num_processors;
	unsigned long reserve[128];
	struct fake_smp_monitor_cpu cpu[4];
};

struct fake_smp_host_os {
	unsigned char prefix[240];
	struct fake_smp_monitor *monitor;
};

struct fake_smp_status_object {
	int lock;
	int status;
};

struct fake_ihk_resource {
	int flags;
	int cpu_cores;
	unsigned long mem_size;
	unsigned long mem_start;
	int cores[4];
};

struct fake_os_read_kaddr_desc {
	unsigned long kaddr;
	unsigned long len;
	void *ubuf;
	int flags;
};

struct fake_ihk_mem_region {
	unsigned long start;
	unsigned long size;
};

struct fake_ihk_mem_info {
	int n_available;
	int n_fixed;
	int n_mappable;
	struct fake_ihk_mem_region *available;
	struct fake_ihk_mem_region *fixed;
	struct fake_ihk_mem_region *mappable;
	int n_numa_nodes;
	int *numa_mapping;
};

struct fake_ihk_cpu_info {
	int n_cpus;
	int *mapping;
	int *hw_ids;
	int *ikc_map;
	int ikc_mapped;
};

struct fake_smp_os_info {
	int lock;
	int status;
	struct fake_ihk_mem_info mem_info;
	struct fake_ihk_mem_region mem_region;
	unsigned long mem_start;
	unsigned long mem_end;
	int nr_numa_nodes;
	int *numa_mapping;
	struct fake_ihk_cpu_info cpu_info;
	int nr_cpus;
	int cpu_mapping[4];
	int cpu_hw_ids[4];
	int cpu_ikc_map[4];
	int cpu_ikc_mapped;
};

struct fake_smp_os_info_offsets {
	unsigned long os_mem_info;
	unsigned long os_mem_region;
	unsigned long os_mem_start;
	unsigned long os_mem_end;
	unsigned long os_nr_numa_nodes;
	unsigned long os_numa_mapping;
	unsigned long os_cpu_info;
	unsigned long os_nr_cpus;
	unsigned long os_cpu_mapping;
	unsigned long os_cpu_hw_ids;
	unsigned long os_cpu_ikc_map;
	unsigned long os_cpu_ikc_mapped;
	unsigned long mem_info_n_available;
	unsigned long mem_info_n_fixed;
	unsigned long mem_info_n_mappable;
	unsigned long mem_info_available;
	unsigned long mem_info_fixed;
	unsigned long mem_info_mappable;
	unsigned long mem_info_n_numa_nodes;
	unsigned long mem_info_numa_mapping;
	unsigned long mem_region_start;
	unsigned long mem_region_size;
	unsigned long cpu_info_n_cpus;
	unsigned long cpu_info_mapping;
	unsigned long cpu_info_hw_ids;
	unsigned long cpu_info_ikc_map;
	unsigned long cpu_info_ikc_mapped;
};

struct fake_smp_boot_param {
	unsigned long msg_buffer;
	unsigned long msg_buffer_size;
	unsigned long mikc_queue_recv;
	unsigned long mikc_queue_send;
	unsigned long monitor;
	unsigned long monitor_size;
	unsigned long rusage;
	unsigned long rusage_size;
	unsigned long nmi_mode_addr;
	unsigned long multi_intr_mode_addr;
	unsigned long mckernel_do_futex;
};

struct fake_smp_special_addr_offsets {
	unsigned long msg_buffer;
	unsigned long msg_buffer_size;
	unsigned long mikc_queue_recv;
	unsigned long mikc_queue_send;
	unsigned long monitor;
	unsigned long monitor_size;
	unsigned long rusage;
	unsigned long rusage_size;
	unsigned long nmi_mode_addr;
	unsigned long multi_intr_mode_addr;
	unsigned long mckernel_do_futex;
};

struct fake_smp_query_status_offsets {
	unsigned long host_monitor;
	unsigned long monitor_num_processors;
	unsigned long monitor_cpu;
	unsigned long cpu_status;
	unsigned long cpu_stride;
};

struct fake_kmsg_buf {
	int lock;
	int tail;
	int len;
	int head;
	char padding[16];
	char str[8];
};

struct fake_kmsg_container {
	char list[16];
	int os_index;
	int count;
	void *kmsg_buf;
	unsigned int order;
};

struct fake_device_get_kmsg_buf_desc {
	int os_index;
	void *handle;
};

struct fake_device_read_kmsg_buf_desc {
	void *handle;
	int shift;
	char *buf;
};

struct fake_os_data {
	char prefix[24];
	void *kmsg_buf_container;
};

struct fake_list_head {
	struct fake_list_head *next;
	struct fake_list_head *prev;
};

struct fake_llist_node {
	struct fake_llist_node *next;
};

struct fake_llist_head {
	struct fake_llist_node *first;
};

struct fake_zero_node {
	int id;
	int linux_numa_id;
	int type;
	int zeroing_workers;
	int nr_to_zero_pages;
	struct fake_llist_head zeroed_list;
	struct fake_llist_head to_zero_list;
};

struct fake_zero_chunk {
	unsigned long addr;
	unsigned long size;
	unsigned long rb_node[3];
	struct fake_llist_node list;
};

struct fake_kmsg_node {
	struct fake_list_head list;
	int os_index;
};

struct fake_dma_ops {
	int (*request)(void *channel, void *request);
	void (*get_info)(void *channel, void *info);
};

struct fake_dma_channel {
	void *dev;
	void *priv;
	int channel;
	struct fake_dma_ops *ops;
};

struct fake_user_call_handler {
	unsigned int request;
	void *priv;
	long (*func)(void *os, unsigned int request, void *priv,
			unsigned long arg, void *file);
};

struct fake_user_call {
	struct fake_list_head list;
	int num_handlers;
	struct fake_user_call_handler *handlers;
};

struct fake_notifier {
	struct fake_list_head nlist;
	void *ops;
};

struct fake_master_packet {
	void *channel;
	unsigned int msg;
	unsigned int ref;
	unsigned long long param[5];
};

struct fake_ikc_queue_head {
	unsigned int id;
	unsigned short type;
	unsigned short pktsize;
	unsigned int pktcount;
	unsigned int flag;
	unsigned long long read_off;
	unsigned long long max_read_off;
	unsigned long long write_off;
	unsigned long long queue_size;
	unsigned int channel_id;
	unsigned int read_cpu;
	unsigned int write_cpu;
	unsigned int dummy2;
};

struct fake_ikc_queue_desc {
	struct fake_ikc_queue_head *queue;
	struct fake_ikc_queue_head cache;
	unsigned long qrphys;
	unsigned long qphys;
	int lock;
	unsigned int intr_cpu;
};

struct fake_ikc_channel_desc {
	struct fake_list_head list_all;
	void *remote_os;
	int remote_channel_id;
	unsigned long long remote_channel_va;
	void *master;
	int port;
	int channel_id;
	struct fake_ikc_queue_desc recv;
	struct fake_ikc_queue_desc send;
	int lock;
	int flag;
	int (*handler)(void *channel, void *packet, void *os);
	struct fake_list_head packet_pool;
	int packet_pool_lock;
};

struct fake_mcctrl_vdso {
	long busy;
	int vdso_npages;
	char vvar_is_global;
	char hpet_is_global;
	char pvti_is_global;
	char padding;
	long vdso_physlist[2];
	void *vvar_virt;
	long vvar_phys;
	void *hpet_virt;
	long hpet_phys;
	void *pvti_virt;
	long pvti_phys;
	void *vgtod_virt;
};

struct fake_trans_uctx {
	int cond;
	int fregsize;
	unsigned long rax;
	unsigned long rbx;
	unsigned long rcx;
	unsigned long rdx;
	unsigned long rsi;
	unsigned long rdi;
	unsigned long rbp;
	unsigned long r8;
	unsigned long r9;
	unsigned long r10;
	unsigned long r11;
	unsigned long r12;
	unsigned long r13;
	unsigned long r14;
	unsigned long r15;
	unsigned long rflags;
	unsigned long rip;
	unsigned long rsp;
	unsigned long fs;
};

struct fake_mc_plist_head {
	struct fake_list_head prio_list;
	struct fake_list_head node_list;
};

struct fake_mc_plist_node {
	int prio;
	struct fake_mc_plist_head plist;
};

struct fake_mcctrl_spinlock {
	union {
		unsigned int head_tail;
		struct {
			unsigned short head;
			unsigned short tail;
		} tickets;
	};
};

struct fake_mcctrl_mcs_rwlock {
	struct fake_mcctrl_spinlock slock;
} __attribute__((aligned(64)));

struct fake_mcctrl_refcount {
	int refs;
};

static void *expected_dma_channel;
static void *expected_dma_request;
static int dma_callback_count;
static void *expected_packet_os;
static void *expected_packet_channel;
static void *expected_packet;
static int packet_callback_count;
static void *fake_master_channel;
static int master_init_first_calls;
static int master_init_first_fail;
static int master_init_handler_matches;
static int master_enable_calls;
static int master_send_calls;
static unsigned int master_send_last_msg;
static int master_send_last_opt;
static int master_destroy_calls;
static int master_system_exit_calls;
static unsigned char fake_master_channel_storage[FAKE_MASTER_CHANNEL_ALLOC_SIZE]
		__attribute__((aligned(8)));
static void *fake_master_dev;
static int host_ikc_system_init_calls;
static int host_ikc_wait_calls;
static int host_ikc_wait_status;
static int host_ikc_wait_sleepable;
static int host_ikc_wait_timeout;
static int host_ikc_wait_ret;
static int host_ikc_special_calls;
static int host_ikc_last_special_type;
static int host_ikc_map_memory_calls;
static unsigned long host_ikc_last_map_memory_pa;
static unsigned long host_ikc_last_map_memory_size;
static int host_ikc_map_virtual_calls;
static unsigned long host_ikc_last_map_virtual_pa;
static unsigned long host_ikc_last_map_virtual_size;
static int host_ikc_alloc_calls;
static int host_ikc_alloc_fail;
static unsigned long host_ikc_alloc_last_size;
static int host_ikc_init_desc_calls;
static void *host_ikc_init_desc_recv_queue;
static void *host_ikc_init_desc_send_queue;
static int host_ikc_set_cpu_calls;
static int host_ikc_last_cpu;
static int host_ikc_publish_calls;
static unsigned long host_ikc_publish_recv_phys;
static unsigned long host_ikc_publish_send_phys;
static unsigned long host_ikc_publish_recv_remote;
static unsigned long host_ikc_publish_send_remote;
static int host_ikc_ready_failed_calls;
static void *fake_boot_kmsg_container;
static int fake_boot_find_miss;
static int fake_cpumap_clear_calls;
static int boot_index_calls;
static int boot_kmsg_lock_calls;
static int boot_kmsg_find_calls;
static int boot_kmsg_find_last_index;
static int boot_kmsg_inc_calls;
static int boot_kmsg_unlock_calls;
static unsigned long boot_kmsg_unlock_last_flags;
static int boot_kmsg_dec_calls;
static int boot_notifier_down_calls;
static int boot_notifier_down_ret;
static int boot_notifier_up_calls;
static int boot_ops_calls;
static int boot_ops_last_flag;
static int boot_ops_ret;
static int boot_master_init_calls;
static int boot_master_init_ret;
static int boot_notify_calls;
static int boot_notify_last_index;
static int boot_notify_ret;
static int boot_master_finalize_calls;
static int boot_shutdown_calls;
static int boot_shutdown_last_flag;
static int shutdown_status_value;
static int shutdown_status_calls;
static int shutdown_wait_calls;
static int shutdown_wait_status[4];
static int shutdown_wait_ret[4];
static int shutdown_thaw_calls;
static int shutdown_thaw_ret;
static int shutdown_nmi_calls;
static int shutdown_nmi_last_mode;
static unsigned int shutdown_nmi_last_delay;
static int shutdown_notify_calls;
static int shutdown_notify_last_index;
static int shutdown_release_calls;
static int shutdown_release_ret;
static int shutdown_log_calls;
static int shutdown_last_log_event;
static int shutdown_last_log_value;
static int user_call_lock_calls;
static int user_call_unlock_calls;
static unsigned long user_call_unlock_last_flags;
static int user_call_handler_calls;
static unsigned int user_call_last_request;
static unsigned long user_call_last_arg;
static void *user_call_last_os;
static void *user_call_last_priv;
static void *user_call_last_file;
static int notifier_down_calls;
static int notifier_down_ret;
static int notifier_up_calls;
static int notifier_log_calls;
static int notifier_last_log_event;
static unsigned char fake_work_storage[IKC_WORK_SIZE]
		__attribute__((aligned(8)));
static int fake_work_alloc_fail;
static int fake_work_alloc_calls;
static unsigned long fake_work_alloc_last_size;
static int fake_work_init_calls;
static void *fake_work_init_last_work;
static void *fake_work_init_last_fn;
static int fake_work_current_cpu_calls;
static int fake_work_schedule_calls;
static int fake_work_schedule_last_cpu;
static void *fake_work_schedule_last_work;
static void *fake_interrupt_remote_os;
static int fake_interrupt_read_cpu;
static int fake_interrupt_remote_calls;
static int fake_interrupt_read_cpu_calls;
static int fake_interrupt_issue_calls;
static void *fake_interrupt_last_os;
static int fake_interrupt_last_cpu;
static int fake_interrupt_last_vector;
static int host_pagealloc_kzalloc_calls;
static unsigned long host_pagealloc_kzalloc_last_size;
static int host_pagealloc_get_pages_calls;
static unsigned int host_pagealloc_get_pages_last_order;
static int host_pagealloc_kfree_calls;
static void *host_pagealloc_kfree_last_ptr;
static int host_pagealloc_free_pages_calls;
static void *host_pagealloc_free_pages_last_ptr;
static unsigned int host_pagealloc_free_pages_last_order;
static int host_pagealloc_alloc_fail;
static unsigned char fake_vdso_data[8192] __attribute__((aligned(4096)));
static void *fake_vdso_image = (void *)0x810000;
static long fake_hpet_address_value = 0x12345000;
static void *fake_hv_clock_value = (void *)0x45678000;
static void *fake_vvar_page = (void *)0x34567000;
static void *fake_user_sp;
static unsigned long fake_restored_tls;
static unsigned long fake_fs_base = 0xfeedfaceUL;
static int fake_copy_from_user_fail;
static int fake_copy_from_user_errors;
static int fake_reserve_lock_calls;
static int fake_reserve_unlock_calls;
static int fake_mmap_lock_calls;
static int fake_mmap_unlock_calls;
static unsigned long fake_first_vma_start;
static unsigned long fake_reserved_start;
static unsigned long fake_reserved_end;
static unsigned long fake_reserve_common_result;
static struct fake_mcctrl_vdso fake_vdso_remote;
static unsigned long fake_pt_pml4[512] __attribute__((aligned(4096)));
static unsigned long fake_pt_pdpt[512] __attribute__((aligned(4096)));
static unsigned long fake_pt_pdt[512] __attribute__((aligned(4096)));
static unsigned long fake_pt_pt[512] __attribute__((aligned(4096)));
static int fake_map_memory_calls;
static int fake_map_virtual_calls;
static int fake_unmap_virtual_calls;
static int fake_unmap_memory_calls;
static unsigned char fake_binfmt_buf[256];
static unsigned char fake_binfmt_user_page[4096];
static char fake_binfmt_pbuf[1024];
static char fake_binfmt_env_value[128];
static int fake_binfmt_insert_calls;
static int fake_binfmt_unregister_calls;
static int fake_binfmt_os_alive_value;
static int fake_binfmt_envc;
static int fake_binfmt_argc;
static unsigned long fake_binfmt_p;
static const char *fake_binfmt_path;
static int fake_binfmt_alloc_kernel_fail;
static int fake_binfmt_alloc_atomic_calls;
static int fake_binfmt_alloc_kernel_calls;
static int fake_binfmt_free_calls;
static int fake_binfmt_pr_alloc_calls;
static int fake_binfmt_get_page_calls;
static int fake_binfmt_kmap_calls;
static int fake_binfmt_kunmap_calls;
static int fake_binfmt_put_page_calls;
static void *fake_binfmt_open_file;
static void *fake_binfmt_err_file;
static int fake_binfmt_open_exec_calls;
static int fake_binfmt_fput_calls;
static int fake_binfmt_remove_arg_zero_calls;
static int fake_binfmt_remove_arg_zero_ret;
static int fake_binfmt_copy_interp_calls;
static int fake_binfmt_copy_interp_ret;
static int fake_binfmt_copy_mcexec_calls;
static int fake_binfmt_copy_mcexec_ret;
static int fake_binfmt_change_interp_calls;
static int fake_binfmt_change_interp_ret;
static int fake_binfmt_dispatch_calls;
static int fake_binfmt_dispatch_ret;
static void *fake_binfmt_dispatch_file;
static int mcctrl_preempt_disable_calls;
static int mcctrl_preempt_enable_calls;
static int mcctrl_futex_pagefault_disable_calls;
static int mcctrl_futex_pagefault_enable_calls;
static int mcctrl_futex_get_user_calls;
static int mcctrl_futex_get_user_ret;
static int mcctrl_futex_access_ok_calls;
static int mcctrl_futex_cmpxchg_calls;
static int mcctrl_futex_op_calls;
static int fake_sysfs_cpu_mapping[] = { 4, 2, 7 };
static int fake_sysfs_cpu_hw_ids[] = { 40, 20, 70 };
static int fake_sysfs_numa_mapping[] = { 1, 3 };
static void *fake_sysfs_usrdata = (void *)0x1000;
static void *host_driver_fake_os = (void *)0x8800;
static void *host_driver_fake_dev = (void *)0x8900;
static int host_debug_present_value;
static int host_os_debug_present_calls;
static int host_os_debug_call_calls;
static int host_device_debug_present_calls;
static int host_device_debug_call_calls;
static unsigned int host_debug_last_request;
static unsigned long host_debug_last_arg;
static void *host_debug_last_ptr;
static int host_debug_ret;
static int host_copy_to_user_calls;
static int host_copy_to_user_fail;
static void *host_copy_to_user_dst;
static const void *host_copy_to_user_src;
static unsigned long host_copy_to_user_size;
static int host_os_resource_calls;
static int host_os_resource_ret;
static void *host_os_resource_last_os;
static int host_os_resource_flags;
static int host_os_resource_cpu_cores;
static unsigned long host_os_resource_mem_size;
static unsigned long host_os_resource_mem_start;
static int host_os_resource_core0;
static int host_os_resource_core1;
static int host_device_op_present_calls;
static int host_device_op_call_calls;
static int host_device_op_present_value[9];
static int host_device_op_ret[9];
static int host_device_op_last_op;
static unsigned long host_device_op_last_arg;
static void *host_device_op_last_dev;
static int host_os_buffer_calls;
static int host_os_buffer_ret;
static void *host_os_buffer_last_os;
static void *host_os_buffer_last_arg;
static int host_alloc_calls;
static int host_alloc_fail;
static unsigned long host_alloc_size;
static unsigned char host_alloc_storage[128];
static int host_free_calls;
static void *host_free_last_ptr;
static int host_copy_from_count_calls;
static unsigned long host_copy_from_not_copied;
static const void *host_copy_from_src;
static void *host_copy_from_dst;
static unsigned long host_copy_from_size;
static int host_copy_to_count_calls;
static unsigned long host_copy_to_not_copied;
static const void *host_copy_to_src;
static void *host_copy_to_dst;
static unsigned long host_copy_to_size;
static int host_os_load_memory_calls;
static int host_os_load_memory_ret;
static void *host_os_load_memory_last_os;
static void *host_os_load_memory_last_buf;
static unsigned long host_os_load_memory_last_size;
static unsigned long host_os_load_memory_last_offset;
static int host_device_map_memory_calls;
static unsigned long host_device_map_memory_ret;
static unsigned long host_device_map_memory_last_off;
static unsigned long host_device_map_memory_last_size;
static int host_device_map_virtual_calls;
static int host_device_map_virtual_fail;
static unsigned long host_device_map_virtual_last_pa;
static unsigned long host_device_map_virtual_last_size;
static unsigned char host_device_va[128];
static int host_device_unmap_virtual_calls;
static void *host_device_unmap_virtual_last_va;
static unsigned long host_device_unmap_virtual_last_size;
static int host_os_status_calls;
static int host_os_status_ret;
static int host_os_simple_calls;
static int host_os_simple_ret;
static int host_os_wait_calls;
static int host_os_wait_ret;
static int host_os_wait_status;
static int host_os_wait_sleepable;
static int host_os_wait_timeout;
static int host_os_log_calls;
static int host_os_last_log_event;
static int host_os_last_log_value;
static int host_setup_monitor_calls;
static int host_setup_monitor_publish;
static struct fake_smp_monitor *host_setup_monitor_value;
static int host_os_vtop_calls;
static int host_os_vtop_ret;
static unsigned long host_os_vtop_last_kaddr;
static unsigned long host_os_vtop_phys;
static int host_phys_to_virt_calls;
static unsigned long host_phys_to_virt_last_phys;
static unsigned char host_phys_to_virt_storage[64];
static int host_irq_save_calls;
static int host_irq_restore_calls;
static unsigned long host_irq_restore_last_flags;
static int host_cpu_relax_calls;
static int host_kmsg_alloc_calls;
static int host_kmsg_alloc_fail;
static unsigned long host_kmsg_alloc_size;
static unsigned char host_kmsg_alloc_storage[64];
static int host_kmsg_free_calls;
static void *host_kmsg_free_last_ptr;
static int host_read_kmsg_calls;
static int host_read_kmsg_ret;
static void *host_read_kmsg_last_buf;
static int host_read_kmsg_last_shift;
static void *host_read_kmsg_last_kmsg;
static int host_release_kmsg_calls;
static int host_release_kmsg_ret;
static void *host_release_kmsg_last_handle;

static void require_line(int condition, int line);
#define require(condition) require_line((condition), __LINE__)

static void reset_host_driver_wrapper_state(void)
{
	int i;

	host_debug_present_value = 1;
	host_os_debug_present_calls = 0;
	host_os_debug_call_calls = 0;
	host_device_debug_present_calls = 0;
	host_device_debug_call_calls = 0;
	host_debug_last_request = 0;
	host_debug_last_arg = 0;
	host_debug_last_ptr = NULL;
	host_debug_ret = 321;
	host_copy_to_user_calls = 0;
	host_copy_to_user_fail = 0;
	host_copy_to_user_dst = NULL;
	host_copy_to_user_src = NULL;
	host_copy_to_user_size = 0;
	host_os_resource_calls = 0;
	host_os_resource_ret = 777;
	host_os_resource_last_os = NULL;
	host_os_resource_flags = -1;
	host_os_resource_cpu_cores = -1;
	host_os_resource_mem_size = 0;
	host_os_resource_mem_start = 0;
	host_os_resource_core0 = -1;
	host_os_resource_core1 = -1;
	host_device_op_present_calls = 0;
	host_device_op_call_calls = 0;
	host_device_op_last_op = 0;
	host_device_op_last_arg = 0;
	host_device_op_last_dev = NULL;
	host_os_buffer_calls = 0;
	host_os_buffer_ret = 731;
	host_os_buffer_last_os = NULL;
	host_os_buffer_last_arg = NULL;
	host_alloc_calls = 0;
	host_alloc_fail = 0;
	host_alloc_size = 0;
	memset(host_alloc_storage, 0, sizeof(host_alloc_storage));
	host_free_calls = 0;
	host_free_last_ptr = NULL;
	host_copy_from_count_calls = 0;
	host_copy_from_not_copied = 0;
	host_copy_from_src = NULL;
	host_copy_from_dst = NULL;
	host_copy_from_size = 0;
	host_copy_to_count_calls = 0;
	host_copy_to_not_copied = 0;
	host_copy_to_src = NULL;
	host_copy_to_dst = NULL;
	host_copy_to_size = 0;
	host_os_load_memory_calls = 0;
	host_os_load_memory_ret = 0;
	host_os_load_memory_last_os = NULL;
	host_os_load_memory_last_buf = NULL;
	host_os_load_memory_last_size = 0;
	host_os_load_memory_last_offset = 0;
	host_device_map_memory_calls = 0;
	host_device_map_memory_ret = 0x9000UL;
	host_device_map_memory_last_off = 0;
	host_device_map_memory_last_size = 0;
	host_device_map_virtual_calls = 0;
	host_device_map_virtual_fail = 0;
	host_device_map_virtual_last_pa = 0;
	host_device_map_virtual_last_size = 0;
	memset(host_device_va, 0, sizeof(host_device_va));
	host_device_unmap_virtual_calls = 0;
	host_device_unmap_virtual_last_va = NULL;
	host_device_unmap_virtual_last_size = 0;
	host_os_status_calls = 0;
	host_os_status_ret = OS_STATUS_RUNNING;
	host_os_simple_calls = 0;
	host_os_simple_ret = 0;
	host_os_wait_calls = 0;
	host_os_wait_ret = 0;
	host_os_wait_status = 0;
	host_os_wait_sleepable = 0;
	host_os_wait_timeout = 0;
	host_os_log_calls = 0;
	host_os_last_log_event = 0;
	host_os_last_log_value = 0;
	host_setup_monitor_calls = 0;
	host_setup_monitor_publish = 1;
	host_setup_monitor_value = NULL;
	host_os_vtop_calls = 0;
	host_os_vtop_ret = 0;
	host_os_vtop_last_kaddr = 0;
	host_os_vtop_phys = 0x40;
	host_phys_to_virt_calls = 0;
	host_phys_to_virt_last_phys = 0;
	memset(host_phys_to_virt_storage, 0, sizeof(host_phys_to_virt_storage));
	host_irq_save_calls = 0;
	host_irq_restore_calls = 0;
	host_irq_restore_last_flags = 0;
	host_cpu_relax_calls = 0;
	host_kmsg_alloc_calls = 0;
	host_kmsg_alloc_fail = 0;
	host_kmsg_alloc_size = 0;
	memset(host_kmsg_alloc_storage, 0, sizeof(host_kmsg_alloc_storage));
	host_kmsg_free_calls = 0;
	host_kmsg_free_last_ptr = NULL;
	host_read_kmsg_calls = 0;
	host_read_kmsg_ret = 5;
	host_read_kmsg_last_buf = NULL;
	host_read_kmsg_last_shift = -1;
	host_read_kmsg_last_kmsg = NULL;
	host_release_kmsg_calls = 0;
	host_release_kmsg_ret = 0;
	host_release_kmsg_last_handle = NULL;
	for (i = 0; i < 9; i++) {
		host_device_op_present_value[i] = i > 0;
		host_device_op_ret[i] = 200 + i;
	}
}

static int fake_os_debug_present(void *os)
{
	require(os == host_driver_fake_os);
	host_os_debug_present_calls++;
	return host_debug_present_value;
}

static int fake_os_debug_call(void *os, unsigned int request,
		unsigned long arg)
{
	require(os == host_driver_fake_os);
	host_os_debug_call_calls++;
	host_debug_last_ptr = os;
	host_debug_last_request = request;
	host_debug_last_arg = arg;
	return host_debug_ret;
}

static int fake_device_debug_present(void *dev)
{
	require(dev == host_driver_fake_dev);
	host_device_debug_present_calls++;
	return host_debug_present_value;
}

static int fake_device_debug_call(void *dev, unsigned int request,
		unsigned long arg)
{
	require(dev == host_driver_fake_dev);
	host_device_debug_call_calls++;
	host_debug_last_ptr = dev;
	host_debug_last_request = request;
	host_debug_last_arg = arg;
	return host_debug_ret;
}

static int fake_host_copy_to_user(void *dst, const void *src,
		unsigned long size)
{
	host_copy_to_user_calls++;
	host_copy_to_user_dst = dst;
	host_copy_to_user_src = src;
	host_copy_to_user_size = size;
	if (host_copy_to_user_fail)
		return 1;
	memcpy(dst, src, size);
	return 0;
}

static int fake_os_alloc_resource(void *os, void *resource)
{
	struct fake_ihk_resource *res = resource;

	require(os == host_driver_fake_os);
	host_os_resource_calls++;
	host_os_resource_last_os = os;
	host_os_resource_flags = res->flags;
	host_os_resource_cpu_cores = res->cpu_cores;
	host_os_resource_mem_size = res->mem_size;
	host_os_resource_mem_start = res->mem_start;
	if ((res->flags & RESOURCE_FLAG_CPU_SPECIFIED) && res->cpu_cores > 0) {
		host_os_resource_core0 = res->cores[0];
		if (res->cpu_cores > 1)
			host_os_resource_core1 = res->cores[1];
	}
	return host_os_resource_ret;
}

static int fake_device_op_present(void *dev, int op)
{
	require(dev == host_driver_fake_dev);
	host_device_op_present_calls++;
	host_device_op_last_dev = dev;
	host_device_op_last_op = op;
	if (op < 1 || op >= 9)
		return 0;
	return host_device_op_present_value[op];
}

static int fake_device_op_call(void *dev, int op, unsigned long arg)
{
	require(dev == host_driver_fake_dev);
	host_device_op_call_calls++;
	host_device_op_last_dev = dev;
	host_device_op_last_op = op;
	host_device_op_last_arg = arg;
	if (op < 1 || op >= 9)
		return -99;
	return host_device_op_ret[op];
}

static int fake_os_buffer_call(void *os, void *arg)
{
	require(os == host_driver_fake_os);
	host_os_buffer_calls++;
	host_os_buffer_last_os = os;
	host_os_buffer_last_arg = arg;
	return host_os_buffer_ret;
}

static void *fake_host_alloc(unsigned long size)
{
	host_alloc_calls++;
	host_alloc_size = size;
	if (host_alloc_fail)
		return NULL;
	require(size <= sizeof(host_alloc_storage));
	return host_alloc_storage;
}

static void fake_host_free(void *ptr)
{
	host_free_calls++;
	host_free_last_ptr = ptr;
	require(ptr == host_alloc_storage);
}

static unsigned long fake_host_irq_save(void)
{
	host_irq_save_calls++;
	return 0x88;
}

static void fake_host_irq_restore(unsigned long flags)
{
	host_irq_restore_calls++;
	host_irq_restore_last_flags = flags;
}

static void fake_host_cpu_relax(void)
{
	host_cpu_relax_calls++;
}

static void *fake_host_kmsg_alloc(unsigned long size)
{
	host_kmsg_alloc_calls++;
	host_kmsg_alloc_size = size;
	if (host_kmsg_alloc_fail)
		return NULL;
	require(size == HOST_KMSG_ALLOC_SIZE);
	return host_kmsg_alloc_storage;
}

static void fake_host_kmsg_free(void *ptr)
{
	host_kmsg_free_calls++;
	host_kmsg_free_last_ptr = ptr;
	require(ptr == host_kmsg_alloc_storage);
}

static int fake_host_read_kmsg(void *kmsg_buf, char *buf, int shift)
{
	host_read_kmsg_calls++;
	host_read_kmsg_last_kmsg = kmsg_buf;
	host_read_kmsg_last_buf = buf;
	host_read_kmsg_last_shift = shift;
	memcpy(buf, "kmsg!", 5);
	return host_read_kmsg_ret;
}

static int fake_host_release_kmsg(void *handle)
{
	host_release_kmsg_calls++;
	host_release_kmsg_last_handle = handle;
	return host_release_kmsg_ret;
}

static unsigned long fake_host_copy_from_count(void *dst, const void *src,
		unsigned long size)
{
	unsigned long copied = size - host_copy_from_not_copied;

	host_copy_from_count_calls++;
	host_copy_from_dst = dst;
	host_copy_from_src = src;
	host_copy_from_size = size;
	require(host_copy_from_not_copied <= size);
	memcpy(dst, src, copied);
	return host_copy_from_not_copied;
}

static unsigned long fake_host_copy_to_count(void *dst, const void *src,
		unsigned long size)
{
	unsigned long copied = size - host_copy_to_not_copied;

	host_copy_to_count_calls++;
	host_copy_to_dst = dst;
	host_copy_to_src = src;
	host_copy_to_size = size;
	require(host_copy_to_not_copied <= size);
	memcpy(dst, src, copied);
	return host_copy_to_not_copied;
}

static int fake_host_os_load_memory(void *os, void *buf,
		unsigned long size, unsigned long offset)
{
	require(os == host_driver_fake_os);
	host_os_load_memory_calls++;
	host_os_load_memory_last_os = os;
	host_os_load_memory_last_buf = buf;
	host_os_load_memory_last_size = size;
	host_os_load_memory_last_offset = offset;
	return host_os_load_memory_ret;
}

static unsigned long fake_host_device_map_memory(void *dev,
		unsigned long off, unsigned long size)
{
	require(dev == host_driver_fake_dev);
	host_device_map_memory_calls++;
	host_device_map_memory_last_off = off;
	host_device_map_memory_last_size = size;
	return host_device_map_memory_ret;
}

static void *fake_host_device_map_virtual(void *dev, unsigned long pa,
		unsigned long size)
{
	require(dev == host_driver_fake_dev);
	host_device_map_virtual_calls++;
	host_device_map_virtual_last_pa = pa;
	host_device_map_virtual_last_size = size;
	require(size <= sizeof(host_device_va));
	if (host_device_map_virtual_fail)
		return NULL;
	return host_device_va;
}

static void fake_host_device_unmap_virtual(void *dev, void *va,
		unsigned long size)
{
	require(dev == host_driver_fake_dev);
	require(va == host_device_va);
	host_device_unmap_virtual_calls++;
	host_device_unmap_virtual_last_va = va;
	host_device_unmap_virtual_last_size = size;
}

static int fake_host_os_status(void *os)
{
	require(os == host_driver_fake_os || os != NULL);
	host_os_status_calls++;
	return host_os_status_ret;
}

static int fake_host_os_simple(void *os)
{
	require(os == host_driver_fake_os || os != NULL);
	host_os_simple_calls++;
	return host_os_simple_ret;
}

static int fake_host_os_wait(void *os, int status, int sleepable, int timeout)
{
	require(os == host_driver_fake_os || os != NULL);
	host_os_wait_calls++;
	host_os_wait_status = status;
	host_os_wait_sleepable = sleepable;
	host_os_wait_timeout = timeout;
	return host_os_wait_ret;
}

static void fake_host_os_log(int event, int value)
{
	host_os_log_calls++;
	host_os_last_log_event = event;
	host_os_last_log_value = value;
}

static void fake_host_setup_monitor(void *os)
{
	struct fake_smp_host_os *host_os = os;

	host_setup_monitor_calls++;
	if (host_setup_monitor_publish)
		host_os->monitor = host_setup_monitor_value;
}

static int fake_host_os_vtop(void *os, unsigned long kaddr,
		unsigned long *phys)
{
	require(os == host_driver_fake_os);
	host_os_vtop_calls++;
	host_os_vtop_last_kaddr = kaddr;
	*phys = host_os_vtop_phys;
	return host_os_vtop_ret;
}

static const void *fake_host_phys_to_virt(unsigned long phys)
{
	host_phys_to_virt_calls++;
	host_phys_to_virt_last_phys = phys;
	return host_phys_to_virt_storage;
}

void mcctrl_cpumap_clear_bridge(void *mask)
{
	unsigned long *bits = mask;

	fake_cpumap_clear_calls++;
	*bits = 0;
}

int mcctrl_cpumap_test_cpu_bridge(int cpu, const void *mask)
{
	const unsigned long *bits = mask;

	return (*bits & (1UL << cpu)) != 0;
}

void mcctrl_cpumap_set_cpu_bridge(int cpu, void *mask)
{
	unsigned long *bits = mask;

	*bits |= 1UL << cpu;
}

const int *mcctrl_usrdata_cpu_mapping_bridge(void *usrdata)
{
	require(usrdata == fake_sysfs_usrdata);
	return fake_sysfs_cpu_mapping;
}

const int *mcctrl_usrdata_cpu_hw_ids_bridge(void *usrdata)
{
	require(usrdata == fake_sysfs_usrdata);
	return fake_sysfs_cpu_hw_ids;
}

int mcctrl_usrdata_cpu_count_bridge(void *usrdata)
{
	require(usrdata == fake_sysfs_usrdata);
	return 3;
}

const int *mcctrl_usrdata_numa_mapping_bridge(void *usrdata)
{
	require(usrdata == fake_sysfs_usrdata);
	return fake_sysfs_numa_mapping;
}

int mcctrl_usrdata_numa_count_bridge(void *usrdata)
{
	require(usrdata == fake_sysfs_usrdata);
	return 2;
}

static int fake_dma_request(void *channel, void *request)
{
	if (channel != expected_dma_channel || request != expected_dma_request)
		return -5;
	dma_callback_count++;
	return 1234;
}

static int fake_packet_handler(void *channel, void *packet, void *os)
{
	if (channel != expected_packet_channel ||
			packet != expected_packet ||
			os != expected_packet_os) {
		return -6;
	}
	packet_callback_count++;
	return 321;
}

static void *fake_master_init_first(void *os,
		int (*handler)(void *channel, void *packet, void *os))
{
	master_init_first_calls++;
	expected_packet_os = os;
	master_init_handler_matches = handler == fake_packet_handler;
	if (master_init_first_fail)
		return NULL;
	return fake_master_channel;
}

static void fake_master_enable(void *channel)
{
	require(channel == fake_master_channel);
	master_enable_calls++;
}

static int fake_master_send(void *channel, void *packet, int opt)
{
	struct fake_master_packet *master_packet = packet;

	require(channel == fake_master_channel);
	master_send_calls++;
	master_send_last_msg = master_packet->msg;
	master_send_last_opt = opt;
	return 0;
}

static void fake_master_destroy(void *channel)
{
	require(channel == fake_master_channel);
	master_destroy_calls++;
}

static void fake_master_system_exit(void *os)
{
	require(os != NULL);
	master_system_exit_calls++;
}

static void reset_fake_master(void)
{
	fake_master_channel = (void *)0x7200;
	master_init_first_calls = 0;
	master_init_first_fail = 0;
	master_init_handler_matches = 0;
	master_enable_calls = 0;
	master_send_calls = 0;
	master_send_last_msg = 0;
	master_send_last_opt = -1;
	master_destroy_calls = 0;
	master_system_exit_calls = 0;
}

static void reset_fake_host_ikc(void)
{
	int i;

	for (i = 0; i < FAKE_MASTER_CHANNEL_ALLOC_SIZE; i++)
		fake_master_channel_storage[i] = 0;
	fake_master_dev = (void *)0x9100;
	host_ikc_system_init_calls = 0;
	host_ikc_wait_calls = 0;
	host_ikc_wait_status = -1;
	host_ikc_wait_sleepable = -1;
	host_ikc_wait_timeout = -1;
	host_ikc_wait_ret = 0;
	host_ikc_special_calls = 0;
	host_ikc_last_special_type = -1;
	host_ikc_map_memory_calls = 0;
	host_ikc_last_map_memory_pa = 0;
	host_ikc_last_map_memory_size = 0;
	host_ikc_map_virtual_calls = 0;
	host_ikc_last_map_virtual_pa = 0;
	host_ikc_last_map_virtual_size = 0;
	host_ikc_alloc_calls = 0;
	host_ikc_alloc_fail = 0;
	host_ikc_alloc_last_size = 0;
	host_ikc_init_desc_calls = 0;
	host_ikc_init_desc_recv_queue = NULL;
	host_ikc_init_desc_send_queue = NULL;
	host_ikc_set_cpu_calls = 0;
	host_ikc_last_cpu = -1;
	host_ikc_publish_calls = 0;
	host_ikc_publish_recv_phys = 0;
	host_ikc_publish_send_phys = 0;
	host_ikc_publish_recv_remote = 0;
	host_ikc_publish_send_remote = 0;
	host_ikc_ready_failed_calls = 0;
}

static void init_fake_list_head(struct fake_list_head *head)
{
	head->next = head;
	head->prev = head;
}

static void init_fake_mc_plist_head(struct fake_mc_plist_head *head)
{
	init_fake_list_head(&head->prio_list);
	init_fake_list_head(&head->node_list);
}

static void init_fake_mc_plist_node(struct fake_mc_plist_node *node, int prio)
{
	node->prio = prio;
	init_fake_mc_plist_head(&node->plist);
}

static struct fake_list_head smoke_ikc_channel_list = {
	&smoke_ikc_channel_list,
	&smoke_ikc_channel_list,
};
static struct fake_list_head smoke_master_wait_list = {
	&smoke_master_wait_list,
	&smoke_master_wait_list,
};
static int smoke_ikc_channel_lock;
static int smoke_listener_lock;
static int smoke_master_wait_lock;
static int smoke_unique_channel_id;
static void *smoke_regular_channels[16];
static void *smoke_listener_entries[512];

unsigned long ihk_core_ikc_spin_lock_irqsave_bridge(void *lock)
{
	(void)lock;
	return 0;
}

void ihk_core_ikc_spin_unlock_irqrestore_bridge(void *lock,
		unsigned long flags)
{
	(void)lock;
	(void)flags;
}

void ihk_core_ikc_spin_lock_init_bridge(void *lock)
{
	if (lock)
		*(int *)lock = 0;
}

unsigned long ihk_core_ikc_local_irq_save_bridge(void)
{
	return 0;
}

void ihk_core_ikc_local_irq_restore_bridge(unsigned long flags)
{
	(void)flags;
}

void mcctrl_preempt_disable_bridge(void)
{
	mcctrl_preempt_disable_calls++;
}

void mcctrl_preempt_enable_bridge(void)
{
	mcctrl_preempt_enable_calls++;
}

void mcctrl_futex_pagefault_disable_bridge(void)
{
	mcctrl_futex_pagefault_disable_calls++;
}

void mcctrl_futex_pagefault_enable_bridge(void)
{
	mcctrl_futex_pagefault_enable_calls++;
}

int mcctrl_futex_get_user_u32_bridge(unsigned int *dest, unsigned int *from)
{
	mcctrl_futex_get_user_calls++;
	if (mcctrl_futex_get_user_ret)
		return mcctrl_futex_get_user_ret;
	*dest = *from;
	return 0;
}

int mcctrl_futex_atomic_access_ok_bridge(int *uaddr, unsigned long size)
{
	(void)size;
	mcctrl_futex_access_ok_calls++;
	return uaddr != NULL;
}

int mcctrl_futex_atomic_cmpxchg_inatomic_bridge(int *uaddr, int oldval,
		int newval)
{
	int current;

	mcctrl_futex_cmpxchg_calls++;
	if (!uaddr)
		return -14;
	current = *uaddr;
	if (current == oldval)
		*uaddr = newval;
	return current;
}

int mcctrl_futex_atomic_op_inuser_bridge(int op, int *uaddr, int oparg,
		int *oldval)
{
	int old;

	mcctrl_futex_op_calls++;
	if (!uaddr)
		return -14;
	old = *uaddr;
	switch (op) {
	case 0:
		*uaddr = oparg;
		break;
	case 1:
		*uaddr = old + oparg;
		break;
	case 2:
		*uaddr = old | oparg;
		break;
	case 3:
		*uaddr = old & oparg;
		break;
	case 4:
		*uaddr = old ^ oparg;
		break;
	default:
		return -38;
	}
	*oldval = old;
	return 0;
}

int ihk_core_ikc_get_processor_id_bridge(void)
{
	return 0;
}

unsigned long ihk_core_ikc_virt_to_phys_bridge(void *ptr)
{
	return (unsigned long)ptr;
}

static int smoke_streq(const char *a, const char *b)
{
	while (*a && *b && *a == *b) {
		a++;
		b++;
	}
	return *a == *b;
}

void *mcctrl_arch_kallsyms_lookup_bridge(const char *name)
{
	if (smoke_streq(name, "vdso_image_64"))
		return fake_vdso_image;
	if (smoke_streq(name, "__vvar_page"))
		return fake_vvar_page;
	if (smoke_streq(name, "hpet_address"))
		return &fake_hpet_address_value;
	if (smoke_streq(name, "hv_clock"))
		return &fake_hv_clock_value;
	return NULL;
}

unsigned long mcctrl_arch_vdso_size_bridge(void *image)
{
	require(image == fake_vdso_image);
	return sizeof(fake_vdso_data);
}

void *mcctrl_arch_vdso_data_bridge(void *image)
{
	require(image == fake_vdso_image);
	return fake_vdso_data;
}

void *mcctrl_arch_vgtod_virt_bridge(void)
{
	return NULL;
}

unsigned long mcctrl_arch_virt_to_phys_bridge(void *ptr)
{
	return (unsigned long)ptr;
}

void mcctrl_arch_wmb_bridge(void)
{
}

int mcctrl_arch_mutex_lock_reserve_bridge(void *usrdata)
{
	require(usrdata != NULL);
	fake_reserve_lock_calls++;
	return 0;
}

void mcctrl_arch_mutex_unlock_reserve_bridge(void *usrdata)
{
	require(usrdata != NULL);
	fake_reserve_unlock_calls++;
}

void mcctrl_arch_mmap_write_lock_bridge(void)
{
	fake_mmap_lock_calls++;
}

void mcctrl_arch_mmap_write_unlock_bridge(void)
{
	fake_mmap_unlock_calls++;
}

unsigned long mcctrl_arch_first_vma_start_bridge(void)
{
	return fake_first_vma_start;
}

unsigned long mcctrl_arch_reserve_user_space_common_bridge(
		void *usrdata, unsigned long start, unsigned long end)
{
	require(usrdata != NULL);
	fake_reserved_start = start;
	fake_reserved_end = end;
	return fake_reserve_common_result;
}

int mcctrl_arch_is_err_value_bridge(unsigned long value)
{
	return value >= (unsigned long)-4095L;
}

void *mcctrl_arch_os_to_dev_bridge(void *os)
{
	(void)os;
	return fake_master_dev;
}

unsigned long mcctrl_arch_device_map_memory_bridge(
		void *dev, unsigned long phys, unsigned long size)
{
	require(dev == fake_master_dev);
	(void)size;
	fake_map_memory_calls++;
	return phys;
}

void *mcctrl_arch_device_map_virtual_bridge(
		void *dev, unsigned long phys, unsigned long size)
{
	require(dev == fake_master_dev);
	fake_map_virtual_calls++;
	if (size == sizeof(fake_vdso_remote))
		return &fake_vdso_remote;
	if (phys == 0x1000)
		return fake_pt_pml4;
	if (phys == 0x2000)
		return fake_pt_pdpt;
	if (phys == 0x3000)
		return fake_pt_pdt;
	if (phys == 0x4000)
		return fake_pt_pt;
	return NULL;
}

void mcctrl_arch_device_unmap_virtual_bridge(
		void *dev, void *virt, unsigned long size)
{
	require(dev == fake_master_dev);
	require(virt != NULL);
	(void)size;
	fake_unmap_virtual_calls++;
}

void mcctrl_arch_device_unmap_memory_bridge(
		void *dev, unsigned long phys, unsigned long size)
{
	require(dev == fake_master_dev);
	(void)phys;
	(void)size;
	fake_unmap_memory_calls++;
}

void *mcctrl_arch_get_user_sp_bridge(void)
{
	return fake_user_sp;
}

void mcctrl_arch_set_user_sp_bridge(void *usp)
{
	fake_user_sp = usp;
}

void mcctrl_arch_restore_tls_bridge(unsigned long addr)
{
	fake_restored_tls = addr;
}

int mcctrl_arch_copy_from_user_bridge(void *dst, const void *src,
		unsigned long size)
{
	unsigned long i;

	if (fake_copy_from_user_fail)
		return 1;
	for (i = 0; i < size; i++)
		((char *)dst)[i] = ((const char *)src)[i];
	return 0;
}

unsigned long mcctrl_arch_read_fs_base_bridge(void)
{
	return fake_fs_base;
}

void mcctrl_arch_pr_err_copy_from_user_bridge(const char *func)
{
	(void)func;
	fake_copy_from_user_errors++;
}

static unsigned long smoke_put_string(unsigned char *dst, unsigned long off,
		const char *src)
{
	while (*src)
		dst[off++] = (unsigned char)*src++;
	dst[off++] = 0;
	return off;
}

static void reset_fake_binfmt(void)
{
	int i;
	unsigned long off = 0;

	for (i = 0; i < (int)sizeof(fake_binfmt_buf); i++)
		fake_binfmt_buf[i] = 0;
	for (i = 0; i < (int)sizeof(fake_binfmt_user_page); i++)
		fake_binfmt_user_page[i] = 0;
	for (i = 0; i < (int)sizeof(fake_binfmt_pbuf); i++)
		fake_binfmt_pbuf[i] = 0;
	for (i = 0; i < (int)sizeof(fake_binfmt_env_value); i++)
		fake_binfmt_env_value[i] = 0;

	fake_binfmt_buf[0] = 0x7f;
	fake_binfmt_buf[1] = 'E';
	fake_binfmt_buf[2] = 'L';
	fake_binfmt_buf[3] = 'F';
	fake_binfmt_buf[4] = 2;
	fake_binfmt_buf[16] = 2;
	fake_binfmt_buf[17] = 0;

	off = smoke_put_string(fake_binfmt_user_page, off, "argv0");
	off = smoke_put_string(fake_binfmt_user_page, off,
			"MCEXEC_WL=/bin:/usr");
	(void)off;

	fake_binfmt_os_alive_value = 0;
	fake_binfmt_envc = 1;
	fake_binfmt_argc = 1;
	fake_binfmt_p = 0;
	fake_binfmt_path = "/bin/app";
	fake_binfmt_insert_calls = 0;
	fake_binfmt_unregister_calls = 0;
	fake_binfmt_alloc_kernel_fail = 0;
	fake_binfmt_alloc_atomic_calls = 0;
	fake_binfmt_alloc_kernel_calls = 0;
	fake_binfmt_free_calls = 0;
	fake_binfmt_pr_alloc_calls = 0;
	fake_binfmt_get_page_calls = 0;
	fake_binfmt_kmap_calls = 0;
	fake_binfmt_kunmap_calls = 0;
	fake_binfmt_put_page_calls = 0;
	fake_binfmt_open_file = (void *)0x51515151UL;
	fake_binfmt_err_file = (void *)-2L;
	fake_binfmt_open_exec_calls = 0;
	fake_binfmt_fput_calls = 0;
	fake_binfmt_remove_arg_zero_calls = 0;
	fake_binfmt_remove_arg_zero_ret = 0;
	fake_binfmt_copy_interp_calls = 0;
	fake_binfmt_copy_interp_ret = 0;
	fake_binfmt_copy_mcexec_calls = 0;
	fake_binfmt_copy_mcexec_ret = 0;
	fake_binfmt_change_interp_calls = 0;
	fake_binfmt_change_interp_ret = 0;
	fake_binfmt_dispatch_calls = 0;
	fake_binfmt_dispatch_ret = 77;
	fake_binfmt_dispatch_file = NULL;
}

void mcctrl_binfmt_insert_bridge(void)
{
	fake_binfmt_insert_calls++;
}

void mcctrl_binfmt_unregister_bridge(void)
{
	fake_binfmt_unregister_calls++;
}

int mcctrl_binfmt_os_alive_bridge(void)
{
	return fake_binfmt_os_alive_value;
}

int mcctrl_binfmt_envc_bridge(void *bprm)
{
	(void)bprm;
	return fake_binfmt_envc;
}

int mcctrl_binfmt_argc_bridge(void *bprm)
{
	(void)bprm;
	return fake_binfmt_argc;
}

void mcctrl_binfmt_inc_argc_bridge(void *bprm)
{
	(void)bprm;
	fake_binfmt_argc++;
}

unsigned long mcctrl_binfmt_p_bridge(void *bprm)
{
	(void)bprm;
	return fake_binfmt_p;
}

void *mcctrl_binfmt_buf_bridge(void *bprm)
{
	(void)bprm;
	return fake_binfmt_buf;
}

void *mcctrl_binfmt_alloc_atomic_bridge(unsigned long size)
{
	fake_binfmt_alloc_atomic_calls++;
	require(size <= sizeof(fake_binfmt_pbuf));
	return fake_binfmt_pbuf;
}

void *mcctrl_binfmt_alloc_kernel_bridge(unsigned long size)
{
	fake_binfmt_alloc_kernel_calls++;
	require(size <= sizeof(fake_binfmt_env_value));
	if (fake_binfmt_alloc_kernel_fail)
		return NULL;
	return fake_binfmt_env_value;
}

void mcctrl_binfmt_free_bridge(void *ptr)
{
	require(ptr == fake_binfmt_pbuf || ptr == fake_binfmt_env_value);
	fake_binfmt_free_calls++;
}

void mcctrl_binfmt_pr_alloc_pbuf_bridge(void)
{
	fake_binfmt_pr_alloc_calls++;
}

const char *mcctrl_binfmt_path_bridge(void *bprm, char *pbuf,
		unsigned long size)
{
	(void)bprm;
	require(pbuf == fake_binfmt_pbuf);
	require(size == sizeof(fake_binfmt_pbuf));
	return fake_binfmt_path;
}

int mcctrl_binfmt_get_user_arg_page_bridge(void *bprm, void **page_out)
{
	(void)bprm;
	fake_binfmt_get_page_calls++;
	*page_out = fake_binfmt_user_page;
	return 1;
}

void *mcctrl_binfmt_kmap_atomic_bridge(void *page)
{
	require(page == fake_binfmt_user_page);
	fake_binfmt_kmap_calls++;
	return fake_binfmt_user_page;
}

void mcctrl_binfmt_kunmap_atomic_bridge(void *addr)
{
	require(addr == fake_binfmt_user_page);
	fake_binfmt_kunmap_calls++;
}

void mcctrl_binfmt_put_page_bridge(void *page)
{
	require(page == fake_binfmt_user_page);
	fake_binfmt_put_page_calls++;
}

void *mcctrl_binfmt_open_exec_bridge(void)
{
	fake_binfmt_open_exec_calls++;
	return fake_binfmt_open_file;
}

int mcctrl_binfmt_ptr_is_err_bridge(const void *ptr)
{
	return ptr == fake_binfmt_err_file;
}

void mcctrl_binfmt_fput_bridge(void *file)
{
	require(file == fake_binfmt_open_file);
	fake_binfmt_fput_calls++;
}

int mcctrl_binfmt_remove_arg_zero_bridge(void *bprm)
{
	(void)bprm;
	fake_binfmt_remove_arg_zero_calls++;
	return fake_binfmt_remove_arg_zero_ret;
}

int mcctrl_binfmt_copy_interp_bridge(void *bprm)
{
	(void)bprm;
	fake_binfmt_copy_interp_calls++;
	return fake_binfmt_copy_interp_ret;
}

int mcctrl_binfmt_copy_mcexec_bridge(void *bprm)
{
	(void)bprm;
	fake_binfmt_copy_mcexec_calls++;
	return fake_binfmt_copy_mcexec_ret;
}

int mcctrl_binfmt_change_interp_bridge(void *bprm)
{
	(void)bprm;
	fake_binfmt_change_interp_calls++;
	return fake_binfmt_change_interp_ret;
}

int mcctrl_binfmt_dispatch_bridge(void *bprm, void *file)
{
	(void)bprm;
	fake_binfmt_dispatch_calls++;
	fake_binfmt_dispatch_file = file;
	return fake_binfmt_dispatch_ret;
}

int ihk_core_ikc_smp_processor_id_bridge(void)
{
	return 0;
}

void *ihk_core_ikc_get_free_pages_bridge(unsigned int order)
{
	return calloc(1, (size_t)4096 << order);
}

void ihk_core_ikc_free_pages_bridge(void *ptr, unsigned int order)
{
	(void)order;
	free(ptr);
}

void *ihk_core_ikc_kmalloc_bridge(int size)
{
	return calloc(1, (size_t)size);
}

void ihk_core_ikc_kfree_bridge(void *ptr)
{
	free(ptr);
}

void ihk_core_ikc_wait_init_bridge(void *wait)
{
	(void)wait;
}

int ihk_core_ikc_wait_master_bridge(void *wait)
{
	(void)wait;
	return 0;
}

void ihk_core_ikc_wake_master_bridge(void *wait)
{
	(void)wait;
}

int ihk_core_ikc_register_interrupt_handler_bridge(void *os, void *handler)
{
	(void)os;
	(void)handler;
	return 0;
}

int ihk_core_ikc_unregister_interrupt_handler_bridge(void *os,
		void *handler)
{
	(void)os;
	(void)handler;
	return 0;
}

void *ihk_core_pagealloc_get_free_pages_bridge(unsigned int order)
{
	host_pagealloc_get_pages_calls++;
	host_pagealloc_get_pages_last_order = order;
	if (host_pagealloc_alloc_fail)
		return NULL;
	return calloc(1, (size_t)4096 << order);
}

void *ihk_core_pagealloc_kzalloc_bridge(unsigned long size)
{
	host_pagealloc_kzalloc_calls++;
	host_pagealloc_kzalloc_last_size = size;
	if (host_pagealloc_alloc_fail)
		return NULL;
	return calloc(1, (size_t)size);
}

void ihk_core_pagealloc_free_pages_bridge(void *ptr, unsigned int order)
{
	host_pagealloc_free_pages_calls++;
	host_pagealloc_free_pages_last_ptr = ptr;
	host_pagealloc_free_pages_last_order = order;
	free(ptr);
}

void ihk_core_pagealloc_kfree_bridge(void *ptr)
{
	host_pagealloc_kfree_calls++;
	host_pagealloc_kfree_last_ptr = ptr;
	free(ptr);
}

void *ihk_os_get_ikc_channel_list(void *os)
{
	(void)os;
	return &smoke_ikc_channel_list;
}

void *ihk_os_get_ikc_channel_lock(void *os)
{
	(void)os;
	return &smoke_ikc_channel_lock;
}

int ihk_os_get_unique_channel_id(void *os)
{
	(void)os;
	return ++smoke_unique_channel_id;
}

void ihk_os_set_regular_channel(void *os, void *channel, int cpu)
{
	(void)os;
	if (cpu >= 0 && cpu < (int)(sizeof(smoke_regular_channels) /
			sizeof(smoke_regular_channels[0])))
		smoke_regular_channels[cpu] = channel;
}

void *ihk_ikc_get_listener_lock(void *os)
{
	(void)os;
	return &smoke_listener_lock;
}

void **ihk_ikc_get_listener_entry(void *os, int port)
{
	(void)os;
	if (port < 0 || port >= (int)(sizeof(smoke_listener_entries) /
			sizeof(smoke_listener_entries[0])))
		return NULL;
	return &smoke_listener_entries[port];
}

void *ihk_ikc_get_master_wait_list(void *os)
{
	(void)os;
	return &smoke_master_wait_list;
}

void *ihk_ikc_get_master_wait_lock(void *os)
{
	(void)os;
	return &smoke_master_wait_lock;
}

void *ihk_os_get_master_channel(void *os)
{
	(void)os;
	return fake_master_channel;
}

void *ihk_os_get_regular_channel(void *os, int cpu)
{
	(void)os;
	if (cpu < 0 || cpu >= (int)(sizeof(smoke_regular_channels) /
			sizeof(smoke_regular_channels[0])))
		return NULL;
	return smoke_regular_channels[cpu];
}

void *ihk_host_os_get_ikc_handler(void *os)
{
	if (!os)
		return NULL;
	return (char *)os + OS_OFF_IKC_HANDLER;
}

int ihk_ikc_call_master_packet_handler(void *os, void *channel,
		void *packet)
{
	int (*handler)(void *channel, void *packet, void *os);

	if (!os)
		return 0;

	handler = (int (*)(void *, void *, void *))
			*(void **)((char *)os + OS_OFF_PACKET_HANDLER);
	if (!handler)
		return 0;
	return handler(channel, packet, os);
}

void ihk_ikc_linux_init_work_data(void *os, void (*work_fn)(void *work))
{
	if (os)
		*(void **)((char *)os + OS_OFF_WORK_FUNCTION) = work_fn;
}

void *ihk_ikc_linux_get_os_from_work(void *work)
{
	if (!work)
		return NULL;
	return *(void **)((char *)work + IKC_WORK_OS_OFFSET);
}

void *ihk_os_to_dev(void *os)
{
	(void)os;
	return fake_master_dev;
}

unsigned long ihk_os_map_memory(void *os, unsigned long phys,
		unsigned long size)
{
	(void)os;
	(void)size;
	return phys + 0x10000000;
}

void ihk_os_unmap_memory(void *os, unsigned long phys, int qpages)
{
	(void)os;
	(void)phys;
	(void)qpages;
}

void *ihk_device_map_virtual(void *dev, unsigned long phys,
		unsigned long size, void *priv, int flags)
{
	(void)dev;
	(void)size;
	(void)priv;
	(void)flags;
	return (void *)(phys + 0x1000);
}

void ihk_device_unmap_virtual(void *dev, void *virt, int qpages)
{
	(void)dev;
	(void)virt;
	(void)qpages;
}

int ihk_ikc_send_interrupt(void *channel)
{
	(void)channel;
	return 0;
}

int printk(const char *fmt, ...)
{
	(void)fmt;
	return 0;
}

static void fake_host_ikc_system_init(void *os)
{
	require(os != NULL);
	host_ikc_system_init_calls++;
}

static int fake_host_ikc_wait_for_status(void *os, int status,
		int sleepable, int timeout)
{
	require(os != NULL);
	host_ikc_wait_calls++;
	host_ikc_wait_status = status;
	host_ikc_wait_sleepable = sleepable;
	host_ikc_wait_timeout = timeout;
	return host_ikc_wait_ret;
}

static void fake_host_ikc_get_special_address(void *os, int type,
		unsigned long *addr, unsigned long *size)
{
	require(os != NULL);
	require(addr != NULL);
	require(size != NULL);
	host_ikc_special_calls++;
	host_ikc_last_special_type = type;
	if (type == IHK_SPADDR_MIKC_QUEUE_RECV) {
		*addr = 0x100000;
		*size = 0x1000;
	} else if (type == IHK_SPADDR_MIKC_QUEUE_SEND) {
		*addr = 0x200000;
		*size = 0x2000;
	} else {
		*addr = 0;
		*size = 0;
	}
}

static unsigned long fake_host_ikc_map_memory(void *dev,
		unsigned long pa, unsigned long size)
{
	require(dev == fake_master_dev);
	host_ikc_map_memory_calls++;
	host_ikc_last_map_memory_pa = pa;
	host_ikc_last_map_memory_size = size;
	return pa + 0x10000000;
}

static void *fake_host_ikc_map_virtual(void *dev, unsigned long pa,
		unsigned long size, void *priv, int flags)
{
	require(dev == fake_master_dev);
	require(priv == NULL);
	require(flags == 0);
	host_ikc_map_virtual_calls++;
	host_ikc_last_map_virtual_pa = pa;
	host_ikc_last_map_virtual_size = size;
	return (void *)(pa + 0x1000);
}

static void *fake_host_ikc_alloc(unsigned long size)
{
	host_ikc_alloc_calls++;
	host_ikc_alloc_last_size = size;
	if (host_ikc_alloc_fail)
		return NULL;
	return fake_master_channel_storage;
}

static void fake_host_ikc_init_desc(void *channel, void *os,
		void *recv_queue, void *send_queue)
{
	require(channel == fake_master_channel_storage);
	require(os != NULL);
	host_ikc_init_desc_calls++;
	host_ikc_init_desc_recv_queue = recv_queue;
	host_ikc_init_desc_send_queue = send_queue;
}

static void fake_host_ikc_set_cpu(void *channel, int cpu)
{
	require(channel == fake_master_channel_storage);
	host_ikc_set_cpu_calls++;
	host_ikc_last_cpu = cpu;
}

static void fake_host_ikc_publish_queues(void *channel,
		unsigned long recv_phys, unsigned long send_phys,
		unsigned long recv_remote, unsigned long send_remote)
{
	require(channel == fake_master_channel_storage);
	host_ikc_publish_calls++;
	host_ikc_publish_recv_phys = recv_phys;
	host_ikc_publish_send_phys = send_phys;
	host_ikc_publish_recv_remote = recv_remote;
	host_ikc_publish_send_remote = send_remote;
}

static void fake_host_ikc_ready_failed(void *os)
{
	require(os != NULL);
	host_ikc_ready_failed_calls++;
}

static void reset_fake_boot(void)
{
	fake_boot_kmsg_container = (void *)0xa100;
	fake_boot_find_miss = 0;
	boot_index_calls = 0;
	boot_kmsg_lock_calls = 0;
	boot_kmsg_find_calls = 0;
	boot_kmsg_find_last_index = -1;
	boot_kmsg_inc_calls = 0;
	boot_kmsg_unlock_calls = 0;
	boot_kmsg_unlock_last_flags = 0;
	boot_kmsg_dec_calls = 0;
	boot_notifier_down_calls = 0;
	boot_notifier_down_ret = 0;
	boot_notifier_up_calls = 0;
	boot_ops_calls = 0;
	boot_ops_last_flag = -1;
	boot_ops_ret = 0;
	boot_master_init_calls = 0;
	boot_master_init_ret = 0;
	boot_notify_calls = 0;
	boot_notify_last_index = -1;
	boot_notify_ret = 0;
	boot_master_finalize_calls = 0;
	boot_shutdown_calls = 0;
	boot_shutdown_last_flag = -1;
}

static int fake_boot_index(void *os)
{
	require(os != NULL);
	boot_index_calls++;
	return 3;
}

static unsigned long fake_boot_kmsg_lock(void)
{
	boot_kmsg_lock_calls++;
	return 0x55;
}

static void *fake_boot_kmsg_find(int os_index)
{
	boot_kmsg_find_calls++;
	boot_kmsg_find_last_index = os_index;
	if (fake_boot_find_miss)
		return NULL;
	return fake_boot_kmsg_container;
}

static void fake_boot_kmsg_inc(void *container)
{
	require(container == fake_boot_kmsg_container);
	boot_kmsg_inc_calls++;
}

static void fake_boot_kmsg_unlock(unsigned long flags)
{
	boot_kmsg_unlock_calls++;
	boot_kmsg_unlock_last_flags = flags;
}

static int fake_boot_notifier_down(void)
{
	boot_notifier_down_calls++;
	return boot_notifier_down_ret;
}

static void fake_boot_notifier_up(void)
{
	boot_notifier_up_calls++;
}

static int fake_boot_ops(void *os, int flag)
{
	require(os != NULL);
	boot_ops_calls++;
	boot_ops_last_flag = flag;
	return boot_ops_ret;
}

static int fake_boot_master_init(void *os)
{
	require(os != NULL);
	boot_master_init_calls++;
	return boot_master_init_ret;
}

static int fake_boot_notify(int os_index)
{
	boot_notify_calls++;
	boot_notify_last_index = os_index;
	return boot_notify_ret;
}

static void fake_boot_master_finalize(void *os)
{
	require(os != NULL);
	boot_master_finalize_calls++;
}

static int fake_boot_shutdown(void *os, int flag)
{
	require(os != NULL);
	boot_shutdown_calls++;
	boot_shutdown_last_flag = flag;
	return 0;
}

static void fake_boot_kmsg_dec(void *container)
{
	require(container == fake_boot_kmsg_container);
	boot_kmsg_dec_calls++;
}

static void reset_fake_shutdown(void)
{
	int i;

	shutdown_status_value = OS_STATUS_RUNNING;
	shutdown_status_calls = 0;
	shutdown_wait_calls = 0;
	for (i = 0; i < 4; i++) {
		shutdown_wait_status[i] = -1;
		shutdown_wait_ret[i] = 0;
	}
	shutdown_thaw_calls = 0;
	shutdown_thaw_ret = 0;
	shutdown_nmi_calls = 0;
	shutdown_nmi_last_mode = -1;
	shutdown_nmi_last_delay = 0;
	shutdown_notify_calls = 0;
	shutdown_notify_last_index = -1;
	shutdown_release_calls = 0;
	shutdown_release_ret = 0;
	shutdown_log_calls = 0;
	shutdown_last_log_event = -1;
	shutdown_last_log_value = 0;
	boot_notifier_down_calls = 0;
	boot_notifier_down_ret = 0;
	boot_notifier_up_calls = 0;
	boot_master_finalize_calls = 0;
	boot_shutdown_calls = 0;
	boot_shutdown_last_flag = -1;
}

static int fake_shutdown_status(void *os)
{
	require(os != NULL);
	shutdown_status_calls++;
	return shutdown_status_value;
}

static int fake_shutdown_wait_for_status(void *os, int status,
		int sleepable, int timeout)
{
	int slot = shutdown_wait_calls;

	require(os != NULL);
	require(sleepable == 0);
	require(timeout == 100 || timeout == 200);
	require(slot >= 0 && slot < 4);
	shutdown_wait_status[slot] = status;
	shutdown_wait_calls++;
	return shutdown_wait_ret[slot];
}

static int fake_shutdown_thaw(void *os)
{
	require(os != NULL);
	shutdown_thaw_calls++;
	return shutdown_thaw_ret;
}

static void fake_shutdown_send_nmi_delay(void *os, int mode,
		unsigned int delay_ms)
{
	require(os != NULL);
	shutdown_nmi_calls++;
	shutdown_nmi_last_mode = mode;
	shutdown_nmi_last_delay = delay_ms;
}

static void fake_shutdown_notify(int os_index)
{
	shutdown_notify_calls++;
	shutdown_notify_last_index = os_index;
}

static int fake_shutdown_release_kmsg(void *container)
{
	require(container == fake_boot_kmsg_container);
	shutdown_release_calls++;
	return shutdown_release_ret;
}

static void fake_shutdown_log(int event, int value)
{
	shutdown_log_calls++;
	shutdown_last_log_event = event;
	shutdown_last_log_value = value;
}

static int call_fake_shutdown(void *os, int flag)
{
	return ihk_core_os_shutdown_result(os, flag,
			fake_shutdown_status,
			fake_boot_index,
			fake_shutdown_wait_for_status,
			fake_shutdown_thaw,
			fake_shutdown_send_nmi_delay,
			fake_boot_notifier_down,
			fake_shutdown_notify,
			fake_boot_notifier_up,
			fake_boot_master_finalize,
			fake_boot_shutdown,
			fake_shutdown_release_kmsg,
			fake_shutdown_log);
}

static void reset_user_call_state(void)
{
	user_call_lock_calls = 0;
	user_call_unlock_calls = 0;
	user_call_unlock_last_flags = 0;
	user_call_handler_calls = 0;
	user_call_last_request = 0;
	user_call_last_arg = 0;
	user_call_last_os = NULL;
	user_call_last_priv = NULL;
	user_call_last_file = NULL;
}

static unsigned long fake_user_call_lock(void *os)
{
	require(os != NULL);
	user_call_lock_calls++;
	return 0x77;
}

static void fake_user_call_unlock(void *os, unsigned long flags)
{
	require(os != NULL);
	user_call_unlock_calls++;
	user_call_unlock_last_flags = flags;
}

static long fake_user_call_handler(void *os, unsigned int request, void *priv,
		unsigned long arg, void *file)
{
	user_call_handler_calls++;
	user_call_last_os = os;
	user_call_last_request = request;
	user_call_last_priv = priv;
	user_call_last_arg = arg;
	user_call_last_file = file;
	return 0x345;
}

static void reset_notifier_state(void)
{
	notifier_down_calls = 0;
	notifier_down_ret = 0;
	notifier_up_calls = 0;
	notifier_log_calls = 0;
	notifier_last_log_event = -1;
}

static int fake_notifier_down(void)
{
	notifier_down_calls++;
	return notifier_down_ret;
}

static void fake_notifier_up(void)
{
	notifier_up_calls++;
}

static void fake_notifier_log(int event)
{
	notifier_log_calls++;
	notifier_last_log_event = event;
}

static void fake_work_function(void *work)
{
	(void)work;
}

static void *fake_work_alloc(unsigned long size)
{
	fake_work_alloc_calls++;
	fake_work_alloc_last_size = size;
	if (fake_work_alloc_fail)
		return NULL;
	return fake_work_storage;
}

static void fake_work_init(void *work, void (*work_fn)(void *work))
{
	fake_work_init_calls++;
	fake_work_init_last_work = work;
	fake_work_init_last_fn = work_fn;
}

static int fake_work_current_cpu(void)
{
	fake_work_current_cpu_calls++;
	return 6;
}

static void fake_work_schedule_on(int cpu, void *work)
{
	fake_work_schedule_calls++;
	fake_work_schedule_last_cpu = cpu;
	fake_work_schedule_last_work = work;
}

static void reset_fake_work(void)
{
	int i;

	for (i = 0; i < IKC_WORK_SIZE; i++)
		fake_work_storage[i] = 0;
	fake_work_alloc_fail = 0;
	fake_work_alloc_calls = 0;
	fake_work_alloc_last_size = 0;
	fake_work_init_calls = 0;
	fake_work_init_last_work = NULL;
	fake_work_init_last_fn = NULL;
	fake_work_current_cpu_calls = 0;
	fake_work_schedule_calls = 0;
	fake_work_schedule_last_cpu = -1;
	fake_work_schedule_last_work = NULL;
}

static void *fake_interrupt_remote_os_fn(void *channel)
{
	require(channel == fake_master_channel);
	fake_interrupt_remote_calls++;
	return fake_interrupt_remote_os;
}

static int fake_interrupt_read_cpu_fn(void *channel)
{
	require(channel == fake_master_channel);
	fake_interrupt_read_cpu_calls++;
	return fake_interrupt_read_cpu;
}

static int fake_interrupt_issue_fn(void *os, int cpu, int vector)
{
	fake_interrupt_issue_calls++;
	fake_interrupt_last_os = os;
	fake_interrupt_last_cpu = cpu;
	fake_interrupt_last_vector = vector;
	return 77;
}

void *ihk_core_ikc_remote_os_bridge(void *channel)
{
	(void)channel;
	fake_interrupt_remote_calls++;
	return fake_interrupt_remote_os;
}

int ihk_core_ikc_send_read_cpu_bridge(void *channel)
{
	(void)channel;
	fake_interrupt_read_cpu_calls++;
	return fake_interrupt_read_cpu;
}

int ihk_core_ikc_issue_interrupt_bridge(void *os, int cpu, int vector)
{
	return fake_interrupt_issue_fn(os, cpu, vector);
}

static void reset_fake_interrupt(void)
{
	fake_interrupt_remote_os = (void *)0x8100;
	fake_interrupt_read_cpu = 5;
	fake_interrupt_remote_calls = 0;
	fake_interrupt_read_cpu_calls = 0;
	fake_interrupt_issue_calls = 0;
	fake_interrupt_last_os = NULL;
	fake_interrupt_last_cpu = -1;
	fake_interrupt_last_vector = -1;
}

static void reset_host_pagealloc(void)
{
	host_pagealloc_kzalloc_calls = 0;
	host_pagealloc_kzalloc_last_size = 0;
	host_pagealloc_get_pages_calls = 0;
	host_pagealloc_get_pages_last_order = 0;
	host_pagealloc_kfree_calls = 0;
	host_pagealloc_kfree_last_ptr = NULL;
	host_pagealloc_free_pages_calls = 0;
	host_pagealloc_free_pages_last_ptr = NULL;
	host_pagealloc_free_pages_last_order = 0;
	host_pagealloc_alloc_fail = 0;
}

static int fake_atomic_inc_return(void *channel_id)
{
	int *counter = channel_id;

	(*counter)++;
	return *counter;
}

static int smp_validate_log_calls;
static int smp_validate_last_event;
static int smp_validate_last_value;
static int smp_status_lock_calls;
static int smp_status_unlock_calls;
static unsigned long smp_status_last_lock_addr;
static unsigned long smp_status_last_unlock_addr;
static unsigned long smp_status_last_unlock_flags;
static int smp_wait_query_calls;
static int smp_wait_delay_calls;
static int smp_wait_log_calls;
static int smp_wait_last_wanted;
static int smp_wait_last_current;
static int smp_wait_query_values[8];
static unsigned long smp_wait_last_ihk_os;
static unsigned long smp_wait_last_priv;
static int smp_mode_get_calls;
static int smp_mode_get_ret;
static int smp_mode_get_last_type;
static int smp_mode_map_memory_calls;
static int smp_mode_map_virtual_calls;
static int smp_mode_unmap_virtual_calls;
static int smp_mode_unmap_memory_calls;
static int smp_mode_value;
static unsigned long smp_mode_last_ihk_os;
static unsigned long smp_mode_last_priv;
static unsigned long smp_mode_last_remote_phys;
static unsigned long smp_mode_last_local_phys;
static unsigned long smp_mode_last_size;
static unsigned long smp_mode_last_virt;
static int smp_query_setup_calls;
static int smp_query_restore_calls;
static int smp_query_log_calls;
static int smp_query_last_event;
static int smp_query_last_value0;
static int smp_query_last_value1;
static unsigned long smp_query_last_data;

static void reset_smp_validate_log(void)
{
	smp_validate_log_calls = 0;
	smp_validate_last_event = 0;
	smp_validate_last_value = 0;
}

static void fake_smp_validate_log(int event, int value)
{
	smp_validate_log_calls++;
	smp_validate_last_event = event;
	smp_validate_last_value = value;
}

static void reset_smp_status_lock(void)
{
	smp_status_lock_calls = 0;
	smp_status_unlock_calls = 0;
	smp_status_last_lock_addr = 0;
	smp_status_last_unlock_addr = 0;
	smp_status_last_unlock_flags = 0;
}

static void reset_smp_wait_state(void)
{
	int i;

	smp_wait_query_calls = 0;
	smp_wait_delay_calls = 0;
	smp_wait_log_calls = 0;
	smp_wait_last_wanted = -1;
	smp_wait_last_current = -1;
	smp_wait_last_ihk_os = 0;
	smp_wait_last_priv = 0;
	for (i = 0; i < 8; i++)
		smp_wait_query_values[i] = OS_STATUS_LOADING;
}

static void reset_smp_mode_state(void)
{
	smp_mode_get_calls = 0;
	smp_mode_get_ret = 0;
	smp_mode_get_last_type = 0;
	smp_mode_map_memory_calls = 0;
	smp_mode_map_virtual_calls = 0;
	smp_mode_unmap_virtual_calls = 0;
	smp_mode_unmap_memory_calls = 0;
	smp_mode_value = -1;
	smp_mode_last_ihk_os = 0;
	smp_mode_last_priv = 0;
	smp_mode_last_remote_phys = 0;
	smp_mode_last_local_phys = 0;
	smp_mode_last_size = 0;
	smp_mode_last_virt = 0;
}

static void reset_smp_query_state(void)
{
	smp_query_setup_calls = 0;
	smp_query_restore_calls = 0;
	smp_query_log_calls = 0;
	smp_query_last_event = 0;
	smp_query_last_value0 = 0;
	smp_query_last_value1 = 0;
	smp_query_last_data = 0;
}

static unsigned long fake_smp_status_lock(unsigned long lock_addr)
{
	smp_status_lock_calls++;
	smp_status_last_lock_addr = lock_addr;
	return 0xbeefUL;
}

static void fake_smp_status_unlock(unsigned long lock_addr,
		unsigned long flags)
{
	smp_status_unlock_calls++;
	smp_status_last_unlock_addr = lock_addr;
	smp_status_last_unlock_flags = flags;
}

static int fake_smp_wait_query(unsigned long ihk_os, unsigned long priv_data)
{
	int slot = smp_wait_query_calls;

	require(slot >= 0 && slot < 8);
	smp_wait_query_calls++;
	smp_wait_last_ihk_os = ihk_os;
	smp_wait_last_priv = priv_data;
	return smp_wait_query_values[slot];
}

static void fake_smp_wait_delay(unsigned long msecs)
{
	require(msecs == 100);
	smp_wait_delay_calls++;
}

static void fake_smp_wait_log(int wanted_status, int current_status)
{
	smp_wait_log_calls++;
	smp_wait_last_wanted = wanted_status;
	smp_wait_last_current = current_status;
}

static int fake_smp_mode_get_special_addr(unsigned long ihk_os,
		unsigned long priv_data, int special_type, unsigned long *addr,
		unsigned long *size)
{
	smp_mode_get_calls++;
	smp_mode_last_ihk_os = ihk_os;
	smp_mode_last_priv = priv_data;
	smp_mode_get_last_type = special_type;
	if (smp_mode_get_ret)
		return smp_mode_get_ret;
	*addr = 0x9000;
	*size = 0x20;
	return 0;
}

static unsigned long fake_smp_mode_map_memory(unsigned long ihk_os,
		unsigned long priv_data, unsigned long phys,
		unsigned long size)
{
	require(ihk_os == smp_mode_last_ihk_os);
	require(priv_data == smp_mode_last_priv);
	smp_mode_map_memory_calls++;
	smp_mode_last_remote_phys = phys;
	smp_mode_last_size = size;
	return phys + 0x1000;
}

static unsigned long fake_smp_mode_map_virtual(unsigned long ihk_os,
		unsigned long priv_data, unsigned long phys,
		unsigned long size)
{
	require(ihk_os == smp_mode_last_ihk_os);
	require(priv_data == smp_mode_last_priv);
	smp_mode_map_virtual_calls++;
	smp_mode_last_local_phys = phys;
	smp_mode_last_size = size;
	smp_mode_last_virt = (unsigned long)&smp_mode_value;
	return smp_mode_last_virt;
}

static int fake_smp_mode_unmap_virtual(unsigned long ihk_os,
		unsigned long priv_data, unsigned long virt,
		unsigned long size)
{
	require(ihk_os == smp_mode_last_ihk_os);
	require(priv_data == smp_mode_last_priv);
	smp_mode_unmap_virtual_calls++;
	smp_mode_last_virt = virt;
	smp_mode_last_size = size;
	return 0;
}

static int fake_smp_mode_unmap_memory(unsigned long ihk_os,
		unsigned long priv_data, unsigned long phys,
		unsigned long size)
{
	require(ihk_os == smp_mode_last_ihk_os);
	require(priv_data == smp_mode_last_priv);
	smp_mode_unmap_memory_calls++;
	smp_mode_last_local_phys = phys;
	smp_mode_last_size = size;
	return 0;
}

static void fake_smp_query_setup_monitor(unsigned long data)
{
	smp_query_setup_calls++;
	smp_query_last_data = data;
}

static void fake_smp_query_restore_trampoline(void)
{
	smp_query_restore_calls++;
}

static void fake_smp_query_log(int event, int value0, int value1)
{
	smp_query_log_calls++;
	smp_query_last_event = event;
	smp_query_last_value0 = value0;
	smp_query_last_value1 = value1;
}

static void require_line(int condition, int line)
{
	if (!condition) {
		fprintf(stderr, "ihk module helper smoke assertion failed line=%d\n",
			line);
		exit(2);
	}
}

static void expected_mc_jhash_mix(unsigned int *a, unsigned int *b,
		unsigned int *c)
{
	*a -= *b; *a -= *c; *a ^= (*c >> 13);
	*b -= *c; *b -= *a; *b ^= (*a << 8);
	*c -= *a; *c -= *b; *c ^= (*b >> 13);
	*a -= *b; *a -= *c; *a ^= (*c >> 12);
	*b -= *c; *b -= *a; *b ^= (*a << 16);
	*c -= *a; *c -= *b; *c ^= (*b >> 5);
	*a -= *b; *a -= *c; *a ^= (*c >> 3);
	*b -= *c; *b -= *a; *b ^= (*a << 10);
	*c -= *a; *c -= *b; *c ^= (*b >> 15);
}

static unsigned int expected_mc_jhash2(const unsigned int *k,
		unsigned int length, unsigned int initval)
{
	unsigned int a, b, c, len;

	a = b = 0x9e3779b9U;
	c = initval;
	len = length;
	while (len >= 3) {
		a += k[0];
		b += k[1];
		c += k[2];
		expected_mc_jhash_mix(&a, &b, &c);
		k += 3;
		len -= 3;
	}
	c += length * 4;
	switch (len) {
	case 2:
		b += k[1];
	case 1:
		a += k[0];
	};
	expected_mc_jhash_mix(&a, &b, &c);
	return c;
}

static int smoke_futex_encode(int op, int oparg, int cmp, int cmparg)
{
	unsigned int encoded = (((unsigned int)op & 0x0f) << 28) |
		(((unsigned int)cmp & 0x0f) << 24) |
		(((unsigned int)oparg & 0x0fff) << 12) |
		((unsigned int)cmparg & 0x0fff);

	return (int)encoded;
}

static int bytes_are_zero(const char *buf, int len)
{
	int i;

	for (i = 0; i < len; i++) {
		if (buf[i] != 0)
			return 0;
	}
	return 1;
}

int main(void)
{
	unsigned long map[8] = { 0 };
	unsigned long padding[3] = { 0 };
	unsigned long bits[2] = { 0xaaaaaaaaaaaaaaaaUL, 0xbbbbbbbbbbbbbbbbUL };
	unsigned int jhash_words[] = {
		0x01234567U, 0x89abcdefU, 0xfedcba98U, 0x76543210U,
		0x13579bdfU
	};
	int mapping[] = { 4, 2, 7 };
	int xchg_value;
	int futex_word;
	char read_buf[8] = { 'a', 'b', 'c', 'd', 'e', 'f', 'g', '\0' };
	long parsed = 0;
	unsigned long a;
	unsigned long b;
	struct fake_smp_cpu cpus[5] = {
		{ 0, 10, STATUS_AVAILABLE, 0, 0 },
		{ 1, 11, STATUS_ASSIGNED, 0x1000, 7 },
		{ 2, 12, STATUS_ASSIGNED, 0x2000, 8 },
		{ 3, 13, STATUS_AVAILABLE, 0, 0 },
		{ 4, 14, STATUS_ASSIGNED, 0x1000, 9 },
	};
	struct fake_smp_status_object status_obj = {
		.lock = 17,
		.status = -1,
	};
	int smp_numa_mapping[2] = { 8, 9 };
	struct fake_smp_os_info osinfo = {
		.mem_start = 0x400000UL,
		.mem_end = 0x480000UL,
		.nr_numa_nodes = 2,
		.numa_mapping = smp_numa_mapping,
		.nr_cpus = 3,
		.cpu_mapping = { 4, 5, 6, -1 },
		.cpu_hw_ids = { 14, 15, 16, -1 },
		.cpu_ikc_map = { 24, 25, 26, -1 },
		.cpu_ikc_mapped = 1,
	};
	struct fake_smp_boot_param boot_param = {
		.msg_buffer = 0x1000,
		.msg_buffer_size = 0x80,
		.mikc_queue_recv = 0x2000,
		.mikc_queue_send = 0x3000,
		.monitor = 0x4000,
		.monitor_size = 0x180,
		.rusage = 0x5000,
		.rusage_size = 0x280,
		.nmi_mode_addr = 0x6000,
		.multi_intr_mode_addr = 0x7000,
		.mckernel_do_futex = 0x8000,
	};
	struct fake_smp_monitor smp_monitor = {
		.num_processors = 3,
		.cpu = {
			{ .status = IHK_OS_MONITOR_IDLE },
			{ .status = IHK_OS_MONITOR_IDLE },
			{ .status = IHK_OS_MONITOR_IDLE },
			{ .status = IHK_OS_MONITOR_IDLE },
		},
	};
	struct fake_smp_host_os smp_host = {
		.monitor = &smp_monitor,
	};
	const struct fake_smp_os_info_offsets osinfo_offsets = {
		.os_mem_info = offsetof(struct fake_smp_os_info, mem_info),
		.os_mem_region = offsetof(struct fake_smp_os_info, mem_region),
		.os_mem_start = offsetof(struct fake_smp_os_info, mem_start),
		.os_mem_end = offsetof(struct fake_smp_os_info, mem_end),
		.os_nr_numa_nodes = offsetof(struct fake_smp_os_info,
				nr_numa_nodes),
		.os_numa_mapping = offsetof(struct fake_smp_os_info,
				numa_mapping),
		.os_cpu_info = offsetof(struct fake_smp_os_info, cpu_info),
		.os_nr_cpus = offsetof(struct fake_smp_os_info, nr_cpus),
		.os_cpu_mapping = offsetof(struct fake_smp_os_info,
				cpu_mapping),
		.os_cpu_hw_ids = offsetof(struct fake_smp_os_info,
				cpu_hw_ids),
		.os_cpu_ikc_map = offsetof(struct fake_smp_os_info,
				cpu_ikc_map),
		.os_cpu_ikc_mapped = offsetof(struct fake_smp_os_info,
				cpu_ikc_mapped),
		.mem_info_n_available = offsetof(struct fake_ihk_mem_info,
				n_available),
		.mem_info_n_fixed = offsetof(struct fake_ihk_mem_info,
				n_fixed),
		.mem_info_n_mappable = offsetof(struct fake_ihk_mem_info,
				n_mappable),
		.mem_info_available = offsetof(struct fake_ihk_mem_info,
				available),
		.mem_info_fixed = offsetof(struct fake_ihk_mem_info, fixed),
		.mem_info_mappable = offsetof(struct fake_ihk_mem_info,
				mappable),
		.mem_info_n_numa_nodes = offsetof(struct fake_ihk_mem_info,
				n_numa_nodes),
		.mem_info_numa_mapping = offsetof(struct fake_ihk_mem_info,
				numa_mapping),
		.mem_region_start = offsetof(struct fake_ihk_mem_region,
				start),
		.mem_region_size = offsetof(struct fake_ihk_mem_region, size),
		.cpu_info_n_cpus = offsetof(struct fake_ihk_cpu_info, n_cpus),
		.cpu_info_mapping = offsetof(struct fake_ihk_cpu_info,
				mapping),
		.cpu_info_hw_ids = offsetof(struct fake_ihk_cpu_info, hw_ids),
		.cpu_info_ikc_map = offsetof(struct fake_ihk_cpu_info,
				ikc_map),
		.cpu_info_ikc_mapped = offsetof(struct fake_ihk_cpu_info,
				ikc_mapped),
	};
	const struct fake_smp_special_addr_offsets special_offsets = {
		.msg_buffer = offsetof(struct fake_smp_boot_param, msg_buffer),
		.msg_buffer_size = offsetof(struct fake_smp_boot_param,
				msg_buffer_size),
		.mikc_queue_recv = offsetof(struct fake_smp_boot_param,
				mikc_queue_recv),
		.mikc_queue_send = offsetof(struct fake_smp_boot_param,
				mikc_queue_send),
		.monitor = offsetof(struct fake_smp_boot_param, monitor),
		.monitor_size = offsetof(struct fake_smp_boot_param,
				monitor_size),
		.rusage = offsetof(struct fake_smp_boot_param, rusage),
		.rusage_size = offsetof(struct fake_smp_boot_param,
				rusage_size),
		.nmi_mode_addr = offsetof(struct fake_smp_boot_param,
				nmi_mode_addr),
		.multi_intr_mode_addr = offsetof(struct fake_smp_boot_param,
				multi_intr_mode_addr),
		.mckernel_do_futex = offsetof(struct fake_smp_boot_param,
				mckernel_do_futex),
	};
	const struct fake_smp_query_status_offsets query_offsets = {
		.host_monitor = offsetof(struct fake_smp_host_os, monitor),
		.monitor_num_processors = offsetof(struct fake_smp_monitor,
				num_processors),
		.monitor_cpu = offsetof(struct fake_smp_monitor, cpu),
		.cpu_status = offsetof(struct fake_smp_monitor_cpu, status),
		.cpu_stride = sizeof(struct fake_smp_monitor_cpu),
	};
	int out_cpus[3] = { -1, -1, -1 };
	int src_cpus[2] = { -1, -1 };
	int dst_cpus[2] = { -1, -1 };
	int needed = -1;
	unsigned long special_addr = 0;
	unsigned long special_size = 0;
	int tni = -1;
	int cq = -1;
	char tofu_name[10] = { 'x', 'x', 'x', 'x', 'x',
		'x', 'x', 'x', 'x', 'x' };
	struct fake_kmsg_buf fake_kmsg = {
		.lock = 9,
		.tail = 7,
		.len = 6,
		.head = 5,
		.str = { 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h' },
	};
	struct fake_kmsg_container fake_cont = {
		.os_index = -1,
		.count = 99,
		.kmsg_buf = NULL,
		.order = 0,
	};
	struct fake_os_data fake_os = {
		.kmsg_buf_container = &fake_cont,
	};
	struct fake_list_head list_head;
	struct fake_list_head list_a;
	struct fake_list_head list_b;
	struct fake_list_head kmsg_head;
	struct fake_kmsg_node kmsg_a;
	struct fake_kmsg_node kmsg_b;
	unsigned char zero_backing[8192] __attribute__((aligned(64)));
	struct fake_zero_node zero_node = {
		.id = 3,
		.zeroing_workers = 1,
		.nr_to_zero_pages = 2,
	};
	struct fake_zero_chunk *zero_chunk_a =
		(struct fake_zero_chunk *)zero_backing;
	struct fake_zero_chunk *zero_chunk_b =
		(struct fake_zero_chunk *)(zero_backing + 4096);
	struct fake_dma_ops dma_ops = {
		.request = fake_dma_request,
		.get_info = NULL,
	};
	struct fake_dma_ops dma_ops_no_request = {
		.request = NULL,
		.get_info = NULL,
	};
	struct fake_dma_channel dma_channel = {
		.dev = (void *)0x1111,
		.priv = (void *)0x2222,
		.channel = 5,
		.ops = &dma_ops,
	};
	struct fake_dma_channel dma_channel_no_request = {
		.dev = (void *)0x1111,
		.priv = (void *)0x2222,
		.channel = 5,
		.ops = &dma_ops_no_request,
	};
	struct fake_user_call_handler user_handlers[2] = {
		{
			.request = IHK_OS_AUX_CALL_START + 1,
			.priv = (void *)0x7001,
			.func = fake_user_call_handler,
		},
		{
			.request = IHK_OS_AUX_CALL_START + 2,
			.priv = (void *)0x7002,
			.func = fake_user_call_handler,
		},
	};
	struct fake_user_call user_call = {
		.num_handlers = 2,
		.handlers = user_handlers,
	};
	struct fake_user_call_handler bad_user_handler = {
		.request = IHK_OS_AUX_CALL_START - 1,
		.priv = NULL,
		.func = fake_user_call_handler,
	};
	struct fake_user_call bad_user_call = {
		.num_handlers = 1,
		.handlers = &bad_user_handler,
	};
	struct fake_notifier notifier_a;
	struct fake_notifier notifier_b;
	struct fake_list_head notifier_head;
	struct fake_mc_plist_head mc_plist_head;
	struct fake_mc_plist_node mc_plist_a;
	struct fake_mc_plist_node mc_plist_b;
	struct fake_mc_plist_node mc_plist_c;
	struct fake_mcctrl_spinlock mcctrl_lock;
	struct fake_mcctrl_mcs_rwlock mcctrl_rwlock;
	struct fake_mcctrl_refcount mcctrl_refcount;
	unsigned int mcctrl_futex_source;
	unsigned int mcctrl_futex_dest;
	int dma_request;
	unsigned long zero_phys_base = 0x400000UL;
	unsigned long zero_virt_base =
		(unsigned long)zero_backing - zero_phys_base;
	unsigned long zero_addr = 0;
	unsigned long zero_size = 0;
	unsigned long old_container;
	unsigned char os_backing[OS_DATA_SIZE] __attribute__((aligned(8))) = { 0 };
	struct fake_list_head *aux_head =
		(struct fake_list_head *)(os_backing + OS_OFF_AUX_CALL_LIST);
	void *fake_file = (void *)0xf11e;
	void *regular_channels[8] = { 0 };
	void *regular_channel = (void *)0x7100;
	void *master_channel = (void *)0x7200;
	void *packet = (void *)0x7300;
	void *host_desc;
	void *host_large_desc;
	unsigned long host_addr;
	unsigned char ikc_queue_storage[4096] __attribute__((aligned(8))) = { 0 };
	struct fake_ikc_queue_head *ikc_send_queue =
		(struct fake_ikc_queue_head *)ikc_queue_storage;
	struct fake_ikc_channel_desc ikc_channel = { 0 };
	struct fake_master_packet ikc_packet = { 0 };
	unsigned char ikc_wait_backing[112] __attribute__((aligned(8))) = { 0 };
	void *ikc_allocated_queue;
	void *ikc_mem;
	void *handler_addr;
	struct fake_trans_uctx trans_ctx = { 0 };
	unsigned long reserved_start = 0;
	unsigned long reserved_end = 0;
	unsigned long translated_rpa = 0;
	unsigned long translated_pgsize = 0;
	void *fake_bprm = (void *)0xb1f000;
	int i;

	list_head.next = &list_head;
	list_head.prev = &list_head;
	list_a.next = &list_a;
	list_a.prev = &list_a;
	list_b.next = &list_b;
	list_b.prev = &list_b;
	kmsg_head.next = &kmsg_head;
	kmsg_head.prev = &kmsg_head;
	kmsg_a.list.next = &kmsg_a.list;
	kmsg_a.list.prev = &kmsg_a.list;
	kmsg_a.os_index = 4;
	kmsg_b.list.next = &kmsg_b.list;
	kmsg_b.list.prev = &kmsg_b.list;
	kmsg_b.os_index = 5;
	aux_head->next = aux_head;
	aux_head->prev = aux_head;
	notifier_head.next = &notifier_head;
	notifier_head.prev = &notifier_head;
	notifier_a.nlist.next = &notifier_a.nlist;
	notifier_a.nlist.prev = &notifier_a.nlist;
	notifier_a.ops = NULL;
	notifier_b.nlist.next = &notifier_b.nlist;
	notifier_b.nlist.prev = &notifier_b.nlist;
	notifier_b.ops = NULL;
	for (i = 0; i < (int)sizeof(zero_backing); i++)
		zero_backing[i] = 0x5a;
	zero_chunk_a->addr = zero_phys_base;
	zero_chunk_a->size = 4096;
	zero_chunk_a->list.next = &zero_chunk_b->list;
	zero_chunk_b->addr = zero_phys_base + 4096;
	zero_chunk_b->size = 4096;
	zero_chunk_b->list.next = NULL;
	zero_node.to_zero_list.first = &zero_chunk_a->list;
	zero_node.zeroed_list.first = NULL;

	ihk_core_pagealloc_reserve_padding_result(padding, 130, 24);
	require(padding[0] == 0);
	require(padding[1] == 0);
	require(padding[2] == ~3UL);

	a = ihk_core_pagealloc_small_alloc_result(map, 8, 0, 3, BASE, SHIFT);
	require(a == BASE);
	require(map[0] == 0x7UL);

	b = ihk_core_pagealloc_small_alloc_result(map, 8, 0, 2, BASE, SHIFT);
	require(b == BASE + 3 * (1UL << SHIFT));
	require(map[0] == 0x1fUL);

	ihk_core_pagealloc_free_blocks_result(map, BASE, a, 3, SHIFT);
	require(map[0] == 0x18UL);

	a = ihk_core_pagealloc_large_alloc_result(map, 8, 0, 2, BASE, SHIFT);
	require(a == BASE + 64 * (1UL << SHIFT));
	require(map[1] == ~0UL);
	require(map[2] == ~0UL);
	require(ihk_core_pagealloc_large_alloc_result(map, 8, 0, 8,
			BASE, SHIFT) == 0);
	require(ihk_core_open_ref_mode_result(0x1, 0x1) == OPEN_REF_INC);
	require(ihk_core_open_ref_mode_result(0x0, 0x1) == OPEN_REF_CMPXCHG);
	require(ihk_host_map_generic((void *)0x1000, 0x2000,
			(void *)0x3000, 0x4000, 5) == NULL);
	require(ihk_host_unmap_generic((void *)0x1000,
			(void *)0x3000, 0x4000) == -38);
	reset_host_pagealloc();
	require(ihk_pagealloc_init(BASE, 4096, 0) == NULL);
	host_desc = ihk_pagealloc_init(BASE, 4096, 4096);
	require(host_desc != NULL);
	require(host_pagealloc_kzalloc_calls == 1);
	require(host_pagealloc_kzalloc_last_size == 64);
	host_addr = ihk_pagealloc_alloc(host_desc, 1);
	require(host_addr == BASE);
	require(ihk_pagealloc_alloc(host_desc, 1) == 0);
	ihk_pagealloc_free(host_desc, host_addr, 1);
	require(ihk_pagealloc_alloc_size(host_desc, 4096) == BASE);
	ihk_pagealloc_free_size(host_desc, BASE, 4096);
	ihk_pagealloc_destroy(host_desc);
	require(host_pagealloc_kfree_calls == 1);
	require(host_pagealloc_kfree_last_ptr == host_desc);
	reset_host_pagealloc();
	host_large_desc = ihk_pagealloc_init(BASE, 32705UL << SHIFT, 4096);
	require(host_large_desc != NULL);
	require(host_pagealloc_get_pages_calls == 1);
	require(host_pagealloc_get_pages_last_order == 1);
	ihk_pagealloc_destroy(host_large_desc);
	require(host_pagealloc_free_pages_calls == 1);
	require(host_pagealloc_free_pages_last_ptr == host_large_desc);
	require(host_pagealloc_free_pages_last_order == 1);
	reset_host_pagealloc();
	host_pagealloc_alloc_fail = 1;
	require(ihk_pagealloc_init(BASE, 4096, 4096) == NULL);
	require(host_pagealloc_kzalloc_calls == 1);
	fake_master_channel = master_channel;
	require(ihk_ikc_get_master_channel(os_backing) == master_channel);
	ikc_allocated_queue = ihk_ikc_alloc_queue(1);
	require(ikc_allocated_queue != NULL);
	((struct fake_ikc_queue_head *)ikc_allocated_queue)->queue_size =
			4096;
	ihk_ikc_free_queue(ikc_allocated_queue);
	ikc_mem = ihk_ikc_malloc(48);
	require(ikc_mem != NULL);
	ihk_ikc_free(ikc_mem);
	ihk_ikc_wait_init(ikc_wait_backing);
	require(ihk_ikc_wait_master(ikc_wait_backing) == 0);
	ihk_ikc_wake_master(ikc_wait_backing);
	expected_packet_os = os_backing;
	expected_packet_channel = regular_channel;
	expected_packet = packet;
	*(void **)(os_backing + OS_OFF_PACKET_HANDLER) = fake_packet_handler;
	require(call_arch_master_packet_handler(os_backing, regular_channel,
			packet) == 321);
	require(packet_callback_count == 1);
	*(void **)(os_backing + OS_OFF_PACKET_HANDLER) = NULL;
	packet_callback_count = 0;
	handler_addr = os_backing + OS_OFF_IKC_HANDLER;
	ihk_ikc_system_init(os_backing);
	require(*(void **)handler_addr == handler_addr);
	require(*(void **)((char *)handler_addr + 8) == handler_addr);
	require(*(void **)((char *)handler_addr + 16) != NULL);
	require(*(void **)((char *)handler_addr + 24) == os_backing);
	require(*(void **)(os_backing + OS_OFF_WORK_FUNCTION) != NULL);
	ihk_ikc_system_exit(os_backing);
	ikc_send_queue->pktsize = sizeof(ikc_packet);
	ikc_send_queue->pktcount = 2;
	ikc_send_queue->queue_size = sizeof(ikc_packet);
	ikc_channel.send.queue = ikc_send_queue;
	ikc_channel.flag = 1;
	require(ihk_ikc_send(&ikc_channel, &ikc_packet, 0x100) == 0);
	require(ikc_send_queue->write_off == 1);
	require(ikc_send_queue->max_read_off == 1);
	require(ihk_ikc_send(NULL, &ikc_packet, 0) == -22);
	ikc_channel.flag = 0;
	require(ihk_ikc_send(&ikc_channel, &ikc_packet, 0) == -22);
	fake_master_dev = (void *)0x9100;
	require(arch_symbols_init() == 0);
	fake_reserve_common_result = 0x600000000000UL;
	fake_first_vma_start = 0x700000000000UL;
	require(reserve_user_space(os_backing, &reserved_start,
			&reserved_end) == 0);
	require(fake_reserve_lock_calls == 1);
	require(fake_reserve_unlock_calls == 1);
	require(fake_mmap_lock_calls == 1);
	require(fake_mmap_unlock_calls == 1);
	require(fake_reserved_start == 0);
	require(fake_reserved_end == 0x6f8000000000UL);
	require(reserved_start == fake_reserve_common_result);
	require(reserved_end == fake_reserved_end);
	fake_vdso_remote.busy = 1;
	get_vdso_info(os_backing, 0xabc000);
	require(fake_vdso_remote.busy == 0);
	require(fake_vdso_remote.vdso_npages == 2);
	require(fake_vdso_remote.vdso_physlist[0] == (long)fake_vdso_data);
	require(fake_vdso_remote.vdso_physlist[1] ==
			(long)(fake_vdso_data + 4096));
	require(fake_vdso_remote.vvar_is_global == 0);
	require(fake_vdso_remote.vvar_virt == (void *)(-3L * 4096));
	require(fake_vdso_remote.vvar_phys == (long)fake_vvar_page);
	require(fake_vdso_remote.hpet_virt == (void *)(-2L * 4096));
	require(fake_vdso_remote.hpet_phys == fake_hpet_address_value);
	require(fake_vdso_remote.pvti_virt == (void *)(-1L * 4096));
	require(fake_vdso_remote.pvti_phys == (long)fake_hv_clock_value);
	set_user_sp((void *)0x12345678);
	require(get_user_sp() == (void *)0x12345678);
	restore_tls(0xdeadbeefUL);
	require(fake_restored_tls == 0xdeadbeefUL);
	trans_ctx.fs = 0x11112222UL;
	trans_ctx.rsp = 0x33334444UL;
	require(get_tls_ctx(&trans_ctx) == 0x11112222UL);
	require(get_rsp_ctx(&trans_ctx) == 0x33334444UL);
	save_tls_ctx(&trans_ctx);
	fake_copy_from_user_fail = 1;
	require(get_tls_ctx(&trans_ctx) == 0);
	require(fake_copy_from_user_errors == 1);
	fake_copy_from_user_fail = 0;
	for (i = 0; i < 512; i++) {
		fake_pt_pml4[i] = 0;
		fake_pt_pdpt[i] = 0;
		fake_pt_pdt[i] = 0;
		fake_pt_pt[i] = 0;
	}
	fake_pt_pml4[0] = 0x2000 | 0x1;
	fake_pt_pdpt[0] = 0x3000 | 0x1;
	fake_pt_pdt[0] = 0x4000 | 0x1;
	fake_pt_pt[2] = 0x5000 | 0x1;
	require(translate_rva_to_rpa(os_backing, 0x1000, 0x2345,
			&translated_rpa, &translated_pgsize) == 0);
	require(translated_rpa == 0x5345);
	require(translated_pgsize == 4096);
	fake_pt_pdt[1] = 0x800000 | 0x81;
	require(translate_rva_to_rpa(os_backing, 0x1000, 0x200123,
			&translated_rpa, &translated_pgsize) == 0);
	require(translated_rpa == 0x800123);
	require(translated_pgsize == 0x200000);
	require(translate_rva_to_rpa(os_backing, 0x1000, 0x3000,
			&translated_rpa, &translated_pgsize) == -14);
	require(arch_switch_ctx(&trans_ctx) == 0);
	reset_fake_binfmt();
	binfmt_mcexec_init();
	binfmt_mcexec_exit();
	require(fake_binfmt_insert_calls == 1);
	require(fake_binfmt_unregister_calls == 1);
	reset_fake_binfmt();
	require(load_elf(fake_bprm) == 77);
	require(smoke_streq(fake_binfmt_env_value, "/bin:/usr"));
	require(fake_binfmt_alloc_atomic_calls == 1);
	require(fake_binfmt_alloc_kernel_calls == 1);
	require(fake_binfmt_free_calls == 2);
	require(fake_binfmt_get_page_calls == 2);
	require(fake_binfmt_kmap_calls == 2);
	require(fake_binfmt_kunmap_calls == 2);
	require(fake_binfmt_put_page_calls == 2);
	require(fake_binfmt_open_exec_calls == 1);
	require(fake_binfmt_remove_arg_zero_calls == 1);
	require(fake_binfmt_copy_interp_calls == 1);
	require(fake_binfmt_copy_mcexec_calls == 1);
	require(fake_binfmt_change_interp_calls == 1);
	require(fake_binfmt_dispatch_calls == 1);
	require(fake_binfmt_dispatch_file == fake_binfmt_open_file);
	require(fake_binfmt_argc == 3);
	reset_fake_binfmt();
	fake_binfmt_path = "/opt/mcexec";
	require(load_elf(fake_bprm) == -8);
	require(fake_binfmt_free_calls == 1);
	require(fake_binfmt_open_exec_calls == 0);
	reset_fake_binfmt();
	fake_binfmt_path = "/bad/app";
	require(load_elf(fake_bprm) == -8);
	require(fake_binfmt_free_calls == 2);
	require(fake_binfmt_open_exec_calls == 0);
	*(void **)(os_backing + OS_OFF_REGULAR_CHANNELS) = regular_channels;
	require(ihk_core_os_set_regular_channel_result(os_backing,
			regular_channel, 2, 4) == 0);
	require(regular_channels[2] == regular_channel);
	require(ihk_core_os_get_regular_channel_result(os_backing, 2) ==
			regular_channel);
	require(ihk_core_os_set_regular_channel_result(os_backing,
			(void *)0x7400, -1, 4) == -22);
	require(ihk_core_os_set_regular_channel_result(os_backing,
			(void *)0x7400, 5, 4) == -22);
	require(regular_channels[2] == regular_channel);
	require(ihk_core_host_os_get_ikc_handler_result(os_backing) ==
			(void *)(os_backing + OS_OFF_IKC_HANDLER));
	require(ihk_core_ikc_get_listener_lock_result(os_backing) ==
			(void *)(os_backing + OS_OFF_LISTENER_LOCK));
	require(ihk_core_ikc_get_listener_entry_result(os_backing, 7) ==
			(void *)(os_backing + OS_OFF_LISTENERS +
					7 * sizeof(void *)));
	require(ihk_core_ikc_get_listener_entry_result(os_backing, 512) ==
			NULL);
	expected_packet_os = os_backing;
	expected_packet_channel = regular_channel;
	expected_packet = packet;
	require(ihk_core_ikc_call_master_packet_handler_result(os_backing,
			regular_channel, packet, fake_packet_handler) == 321);
	require(packet_callback_count == 1);
	require(ihk_core_ikc_call_master_packet_handler_result(os_backing,
			regular_channel, packet, NULL) == 0);
	require(ihk_core_ikc_get_master_wait_list_result(os_backing) ==
			(void *)(os_backing + OS_OFF_WAIT_LIST));
	require(ihk_core_ikc_get_master_wait_lock_result(os_backing) ==
			(void *)(os_backing + OS_OFF_WAIT_LOCK));
	*(void **)(os_backing + OS_OFF_MCHANNEL) = master_channel;
	require(ihk_core_os_get_master_channel_result(os_backing) ==
			master_channel);
	*(int *)(os_backing + OS_OFF_CHANNEL_ID) = 41;
	require(ihk_core_os_get_unique_channel_id_result(
			os_backing + OS_OFF_CHANNEL_ID,
			fake_atomic_inc_return) == 42);
	require(ihk_core_os_get_unique_channel_id_result(
			os_backing + OS_OFF_CHANNEL_ID,
			fake_atomic_inc_return) == 43);
	require(ihk_core_os_get_unique_channel_id_result(
			os_backing + OS_OFF_CHANNEL_ID, NULL) == -22);
	reset_fake_host_ikc();
	*(void **)(os_backing + OS_OFF_DEV_DATA) = fake_master_dev;
	*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) = 0;
	require(ihk_core_host_ikc_init_first_result(os_backing,
			fake_packet_handler, FAKE_MASTER_CHANNEL_ALLOC_SIZE,
			fake_host_ikc_system_init,
			fake_host_ikc_wait_for_status,
			fake_host_ikc_get_special_address,
			fake_host_ikc_map_memory,
			fake_host_ikc_map_virtual,
			fake_host_ikc_alloc,
			fake_host_ikc_init_desc,
			fake_host_ikc_set_cpu,
			fake_host_ikc_publish_queues,
			fake_host_ikc_ready_failed) == fake_master_channel_storage);
	require(host_ikc_system_init_calls == 1);
	require(*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) == 1);
	require(host_ikc_wait_calls == 1);
	require(host_ikc_wait_status == OS_STATUS_READY);
	require(host_ikc_wait_sleepable == 0);
	require(host_ikc_wait_timeout == 600);
	require(host_ikc_special_calls == 2);
	require(host_ikc_last_special_type == IHK_SPADDR_MIKC_QUEUE_SEND);
	require(host_ikc_map_memory_calls == 2);
	require(host_ikc_last_map_memory_pa == 0x200000);
	require(host_ikc_last_map_memory_size == 0x2000);
	require(host_ikc_map_virtual_calls == 2);
	require(host_ikc_last_map_virtual_pa == 0x10200000);
	require(host_ikc_last_map_virtual_size == 0x2000);
	require(host_ikc_alloc_calls == 1);
	require(host_ikc_alloc_last_size == FAKE_MASTER_CHANNEL_ALLOC_SIZE);
	require(host_ikc_init_desc_calls == 1);
	require(host_ikc_init_desc_recv_queue == (void *)0x10101000);
	require(host_ikc_init_desc_send_queue == (void *)0x10201000);
	require(host_ikc_set_cpu_calls == 1);
	require(host_ikc_last_cpu == 0);
	require(host_ikc_publish_calls == 1);
	require(host_ikc_publish_recv_phys == 0x10100000);
	require(host_ikc_publish_send_phys == 0x10200000);
	require(host_ikc_publish_recv_remote == 0x100000);
	require(host_ikc_publish_send_remote == 0x200000);
	require(*(void **)(os_backing + OS_OFF_PACKET_HANDLER) ==
			(void *)fake_packet_handler);
	require(host_ikc_ready_failed_calls == 0);
	reset_fake_host_ikc();
	*(void **)(os_backing + OS_OFF_DEV_DATA) = fake_master_dev;
	*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) = 0;
	host_ikc_wait_ret = -1;
	require(ihk_core_host_ikc_init_first_result(os_backing,
			fake_packet_handler, FAKE_MASTER_CHANNEL_ALLOC_SIZE,
			fake_host_ikc_system_init,
			fake_host_ikc_wait_for_status,
			fake_host_ikc_get_special_address,
			fake_host_ikc_map_memory,
			fake_host_ikc_map_virtual,
			fake_host_ikc_alloc,
			fake_host_ikc_init_desc,
			fake_host_ikc_set_cpu,
			fake_host_ikc_publish_queues,
			fake_host_ikc_ready_failed) == NULL);
	require(host_ikc_system_init_calls == 1);
	require(host_ikc_wait_calls == 1);
	require(*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) == 1);
	require(host_ikc_ready_failed_calls == 1);
	require(host_ikc_special_calls == 0);
	reset_fake_host_ikc();
	*(void **)(os_backing + OS_OFF_DEV_DATA) = fake_master_dev;
	host_ikc_alloc_fail = 1;
	require(ihk_core_host_ikc_init_first_result(os_backing,
			fake_packet_handler, FAKE_MASTER_CHANNEL_ALLOC_SIZE,
			fake_host_ikc_system_init,
			fake_host_ikc_wait_for_status,
			fake_host_ikc_get_special_address,
			fake_host_ikc_map_memory,
			fake_host_ikc_map_virtual,
			fake_host_ikc_alloc,
			fake_host_ikc_init_desc,
			fake_host_ikc_set_cpu,
			fake_host_ikc_publish_queues,
			fake_host_ikc_ready_failed) == NULL);
	require(host_ikc_alloc_calls == 1);
	require(host_ikc_init_desc_calls == 0);
	require(host_ikc_publish_calls == 0);
	reset_fake_host_ikc();
	require(ihk_core_host_ikc_init_first_result(os_backing,
			fake_packet_handler, FAKE_MASTER_CHANNEL_ALLOC_SIZE,
			NULL,
			fake_host_ikc_wait_for_status,
			fake_host_ikc_get_special_address,
			fake_host_ikc_map_memory,
			fake_host_ikc_map_virtual,
			fake_host_ikc_alloc,
			fake_host_ikc_init_desc,
			fake_host_ikc_set_cpu,
			fake_host_ikc_publish_queues,
			fake_host_ikc_ready_failed) == NULL);
	require(host_ikc_system_init_calls == 0);
	reset_fake_boot();
	*(int *)(os_backing + OS_OFF_MINOR) = 9;
	*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) = NULL;
	require(ihk_core_os_boot_result(os_backing, 12,
			fake_boot_index,
			fake_boot_kmsg_lock,
			fake_boot_kmsg_find,
			fake_boot_kmsg_inc,
			fake_boot_kmsg_unlock,
			fake_boot_notifier_down,
			fake_boot_ops,
			fake_boot_master_init,
			fake_boot_notify,
			fake_boot_master_finalize,
			fake_boot_shutdown,
			fake_boot_notifier_up,
			fake_boot_kmsg_dec) == 0);
	require(boot_index_calls == 1);
	require(boot_kmsg_lock_calls == 1);
	require(boot_kmsg_find_calls == 1);
	require(boot_kmsg_find_last_index == 9);
	require(boot_kmsg_inc_calls == 1);
	require(boot_kmsg_unlock_calls == 1);
	require(boot_kmsg_unlock_last_flags == 0x55);
	require(*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) ==
			fake_boot_kmsg_container);
	require(boot_notifier_down_calls == 1);
	require(boot_ops_calls == 1);
	require(boot_ops_last_flag == 12);
	require(boot_master_init_calls == 1);
	require(boot_notify_calls == 1);
	require(boot_notify_last_index == 3);
	require(boot_master_finalize_calls == 0);
	require(boot_shutdown_calls == 0);
	require(boot_notifier_up_calls == 1);
	require(boot_kmsg_dec_calls == 0);
	reset_fake_boot();
	fake_boot_find_miss = 1;
	*(int *)(os_backing + OS_OFF_MINOR) = 10;
	*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) = NULL;
	require(ihk_core_os_boot_result(os_backing, 12,
			fake_boot_index,
			fake_boot_kmsg_lock,
			fake_boot_kmsg_find,
			fake_boot_kmsg_inc,
			fake_boot_kmsg_unlock,
			fake_boot_notifier_down,
			fake_boot_ops,
			fake_boot_master_init,
			fake_boot_notify,
			fake_boot_master_finalize,
			fake_boot_shutdown,
			fake_boot_notifier_up,
			fake_boot_kmsg_dec) == -22);
	require(boot_kmsg_lock_calls == 1);
	require(boot_kmsg_unlock_calls == 1);
	require(boot_notifier_down_calls == 0);
	require(boot_kmsg_dec_calls == 0);
	reset_fake_boot();
	boot_notifier_down_ret = -1;
	require(ihk_core_os_boot_result(os_backing, 12,
			fake_boot_index,
			fake_boot_kmsg_lock,
			fake_boot_kmsg_find,
			fake_boot_kmsg_inc,
			fake_boot_kmsg_unlock,
			fake_boot_notifier_down,
			fake_boot_ops,
			fake_boot_master_init,
			fake_boot_notify,
			fake_boot_master_finalize,
			fake_boot_shutdown,
			fake_boot_notifier_up,
			fake_boot_kmsg_dec) == -512);
	require(boot_kmsg_inc_calls == 1);
	require(boot_notifier_down_calls == 1);
	require(boot_notifier_up_calls == 0);
	require(boot_ops_calls == 0);
	require(boot_kmsg_dec_calls == 1);
	reset_fake_boot();
	boot_notify_ret = -5;
	require(ihk_core_os_boot_result(os_backing, 12,
			fake_boot_index,
			fake_boot_kmsg_lock,
			fake_boot_kmsg_find,
			fake_boot_kmsg_inc,
			fake_boot_kmsg_unlock,
			fake_boot_notifier_down,
			fake_boot_ops,
			fake_boot_master_init,
			fake_boot_notify,
			fake_boot_master_finalize,
			fake_boot_shutdown,
			fake_boot_notifier_up,
			fake_boot_kmsg_dec) == -5);
	require(boot_ops_calls == 1);
	require(boot_master_init_calls == 1);
	require(boot_notify_calls == 1);
	require(boot_master_finalize_calls == 1);
	require(boot_shutdown_calls == 1);
	require(boot_shutdown_last_flag == 12);
	require(boot_notifier_up_calls == 1);
	require(boot_kmsg_dec_calls == 1);
	reset_fake_boot();
	boot_ops_ret = -9;
	require(ihk_core_os_boot_result(os_backing, 12,
			fake_boot_index,
			fake_boot_kmsg_lock,
			fake_boot_kmsg_find,
			fake_boot_kmsg_inc,
			fake_boot_kmsg_unlock,
			fake_boot_notifier_down,
			fake_boot_ops,
			fake_boot_master_init,
			fake_boot_notify,
			fake_boot_master_finalize,
			fake_boot_shutdown,
			fake_boot_notifier_up,
			fake_boot_kmsg_dec) == -9);
	require(boot_master_init_calls == 0);
	require(boot_notify_calls == 0);
	require(boot_notifier_up_calls == 1);
	require(boot_kmsg_dec_calls == 1);
	reset_fake_boot();
	reset_fake_shutdown();
	*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) =
			fake_boot_kmsg_container;
	require(call_fake_shutdown(os_backing, 14) == 0);
	require(shutdown_status_calls == 1);
	require(shutdown_wait_calls == 0);
	require(shutdown_thaw_calls == 0);
	require(boot_notifier_down_calls == 1);
	require(boot_index_calls == 1);
	require(shutdown_notify_calls == 1);
	require(shutdown_notify_last_index == 3);
	require(boot_notifier_up_calls == 1);
	require(boot_master_finalize_calls == 1);
	require(boot_shutdown_calls == 1);
	require(boot_shutdown_last_flag == 14);
	require(shutdown_release_calls == 1);
	require(*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) == NULL);
	require(shutdown_last_log_event == SHUTDOWN_LOG_OK);
	reset_fake_boot();
	reset_fake_shutdown();
	shutdown_status_value = OS_STATUS_FREEZING;
	shutdown_wait_ret[2] = -1;
	require(call_fake_shutdown(os_backing, 15) == 0);
	require(shutdown_wait_calls == 3);
	require(shutdown_wait_status[0] == OS_STATUS_FROZEN);
	require(shutdown_wait_status[1] == OS_STATUS_READY);
	require(shutdown_wait_status[2] == OS_STATUS_RUNNING);
	require(shutdown_thaw_calls == 1);
	require(shutdown_nmi_calls == 1);
	require(shutdown_nmi_last_mode == 3);
	require(shutdown_nmi_last_delay == 200);
	require(boot_master_finalize_calls == 1);
	require(boot_shutdown_calls == 1);
	reset_fake_boot();
	reset_fake_shutdown();
	shutdown_status_value = OS_STATUS_NOT_BOOTED;
	require(call_fake_shutdown(os_backing, 16) == 0);
	require(shutdown_last_log_event == SHUTDOWN_LOG_NOT_BOOTED);
	require(boot_notifier_down_calls == 0);
	require(boot_master_finalize_calls == 0);
	reset_fake_boot();
	reset_fake_shutdown();
	shutdown_status_value = OS_STATUS_SHUTDOWN;
	require(call_fake_shutdown(os_backing, 17) == -16);
	require(shutdown_last_log_event == SHUTDOWN_LOG_BUSY);
	require(boot_notifier_down_calls == 0);
	reset_fake_boot();
	reset_fake_shutdown();
	boot_notifier_down_ret = -1;
	require(call_fake_shutdown(os_backing, 18) == -512);
	require(boot_notifier_down_calls == 1);
	require(boot_notifier_up_calls == 0);
	require(boot_master_finalize_calls == 0);
	reset_fake_boot();
	reset_fake_shutdown();
	*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) =
			fake_boot_kmsg_container;
	shutdown_release_ret = -7;
	require(call_fake_shutdown(os_backing, 19) == -7);
	require(shutdown_release_calls == 1);
	require(shutdown_last_log_event == SHUTDOWN_LOG_RELEASE_ERROR);
	require(shutdown_last_log_value == -7);
	reset_fake_master();
	*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) = 1;
	require(ihk_core_ikc_master_init_result(os_backing,
			fake_packet_handler, fake_master_init_first,
			fake_master_enable, fake_master_send) == 0);
	require(*(void **)(os_backing + OS_OFF_MCHANNEL) ==
			fake_master_channel);
	require(master_init_first_calls == 1);
	require(master_init_handler_matches == 1);
	require(master_enable_calls == 1);
	require(master_send_calls == 1);
	require(master_send_last_msg == IHK_IKC_MASTER_MSG_INIT_ACK);
	require(master_send_last_opt == 0);
	require(ihk_core_ikc_master_finalize_result(os_backing,
			fake_master_destroy, fake_master_system_exit) == 0);
	require(master_destroy_calls == 1);
	require(master_system_exit_calls == 1);
	require(*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) == 0);
	reset_fake_master();
	master_init_first_fail = 1;
	require(ihk_core_ikc_master_init_result(os_backing,
			fake_packet_handler, fake_master_init_first,
			fake_master_enable, fake_master_send) == -22);
	require(master_init_first_calls == 1);
	require(master_enable_calls == 0);
	require(master_send_calls == 0);
	require(ihk_core_ikc_master_init_result(NULL,
			fake_packet_handler, fake_master_init_first,
			fake_master_enable, fake_master_send) == -22);
	require(ihk_core_ikc_master_init_result(os_backing,
			fake_packet_handler, NULL,
			fake_master_enable, fake_master_send) == -22);
	*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) = 0;
	require(ihk_core_ikc_master_finalize_result(os_backing,
			fake_master_destroy, fake_master_system_exit) == 0);
	require(master_destroy_calls == 0);
	require(master_system_exit_calls == 0);
	*(int *)(os_backing + OS_OFF_IKC_INITIALIZED) = 1;
	*(void **)(os_backing + OS_OFF_MCHANNEL) = NULL;
	require(ihk_core_ikc_master_finalize_result(os_backing,
			fake_master_destroy, fake_master_system_exit) == 0);
	require(master_destroy_calls == 0);
	require(master_system_exit_calls == 1);
	reset_fake_work();
	require(ihk_core_ikc_linux_init_work_data_result(os_backing,
			fake_work_function) == 0);
	require(*(void **)(os_backing + OS_OFF_WORK_FUNCTION) ==
			fake_work_function);
	require(ihk_core_ikc_linux_schedule_work_result(os_backing,
			fake_work_alloc, fake_work_init, fake_work_current_cpu,
			fake_work_schedule_on) == 0);
	require(fake_work_alloc_calls == 1);
	require(fake_work_alloc_last_size == IKC_WORK_SIZE);
	require(fake_work_init_calls == 1);
	require(fake_work_init_last_work == fake_work_storage);
	require(fake_work_init_last_fn == fake_work_function);
	require(*(void **)(fake_work_storage + IKC_WORK_OS_OFFSET) ==
			os_backing);
	require(fake_work_current_cpu_calls == 1);
	require(fake_work_schedule_calls == 1);
	require(fake_work_schedule_last_cpu == 6);
	require(fake_work_schedule_last_work == fake_work_storage);
	require(ihk_core_ikc_linux_get_os_from_work_result(fake_work_storage) ==
			os_backing);
	require(ihk_core_ikc_linux_get_os_from_work_result(NULL) == NULL);
	require(ihk_core_ikc_linux_init_work_data_result(os_backing, NULL) == 0);
	require(*(void **)(os_backing + OS_OFF_WORK_FUNCTION) == NULL);
	reset_fake_work();
	fake_work_alloc_fail = 1;
	require(ihk_core_ikc_linux_schedule_work_result(os_backing,
			fake_work_alloc, fake_work_init, fake_work_current_cpu,
			fake_work_schedule_on) == -12);
	require(fake_work_alloc_calls == 1);
	require(fake_work_init_calls == 0);
	require(fake_work_schedule_calls == 0);
	require(ihk_core_ikc_linux_schedule_work_result(NULL,
			fake_work_alloc, fake_work_init, fake_work_current_cpu,
			fake_work_schedule_on) == -22);
	require(ihk_core_ikc_linux_schedule_work_result(os_backing,
			NULL, fake_work_init, fake_work_current_cpu,
			fake_work_schedule_on) == -22);
	reset_fake_interrupt();
	require(ihk_core_ikc_send_interrupt_result(fake_master_channel, 0xd1,
			fake_interrupt_remote_os_fn,
			fake_interrupt_read_cpu_fn,
			fake_interrupt_issue_fn) == 77);
	require(fake_interrupt_remote_calls == 1);
	require(fake_interrupt_read_cpu_calls == 1);
	require(fake_interrupt_issue_calls == 1);
	require(fake_interrupt_last_os == fake_interrupt_remote_os);
	require(fake_interrupt_last_cpu == fake_interrupt_read_cpu);
	require(fake_interrupt_last_vector == 0xd1);
	require(ihk_core_ikc_send_interrupt_result(NULL, 0xd1,
			fake_interrupt_remote_os_fn,
			fake_interrupt_read_cpu_fn,
			fake_interrupt_issue_fn) == -22);
	require(ihk_core_ikc_send_interrupt_result(fake_master_channel, 0xd1,
			NULL, fake_interrupt_read_cpu_fn,
			fake_interrupt_issue_fn) == -22);
	require(ihk_core_open_exclusive_busy_result(0) == 0);
	require(ihk_core_open_exclusive_busy_result(2) == 1);
	require(ihk_core_open_callback_failed_result(0) == 0);
	require(ihk_core_open_callback_failed_result(-22) == 1);
	require(ihk_core_open_callback_present_result(0) == 0);
	require(ihk_core_open_callback_present_result(0x1000) == 1);
	require(ihk_core_close_callback_present_result(0) == 0);
	require(ihk_core_close_callback_present_result(0x1000) == 1);
	require(ihk_core_release_handler_present_result(0) == 0);
	require(ihk_core_release_handler_present_result(0x1000) == 1);
	require(ihk_core_init_callback_present_result(0) == 0);
	require(ihk_core_init_callback_present_result(0x1000) == 1);
	require(ihk_core_init_callback_failed_result(0) == 0);
	require(ihk_core_init_callback_failed_result(-1) == 1);
	require(ihk_core_exit_callback_present_result(0) == 0);
	require(ihk_core_exit_callback_present_result(0x1000) == 1);
	require(ihk_core_register_minor_action_result(1, 4, 8) == MINOR_REUSE);
	require(ihk_core_register_minor_action_result(4, 4, 8) == MINOR_EXTEND);
	require(ihk_core_register_minor_action_result(8, 8, 8) == MINOR_FULL);
	require(ihk_core_register_alloc_failed_result(0) == 1);
	require(ihk_core_register_alloc_failed_result(0x1000) == 0);
	require(ihk_core_register_should_shrink_minor_result(3, 4) == 1);
	require(ihk_core_register_should_shrink_minor_result(2, 4) == 0);
	require(ihk_core_register_cdev_add_failed_result(-1) == 1);
	require(ihk_core_register_cdev_add_failed_result(0) == 0);
	require(ihk_core_register_device_create_failed_result(1) == 1);
	require(ihk_core_register_device_create_failed_result(0) == 0);
	require(ihk_core_refcount_busy_result(0) == 0);
	require(ihk_core_refcount_busy_result(1) == 1);
	require(ihk_core_kmsg_release_precheck_result(0) == -22);
	require(ihk_core_kmsg_release_precheck_result(2) == 0);
	require(ihk_core_kmsg_release_should_delete_result(0) == 1);
	require(ihk_core_kmsg_release_should_delete_result(1) == 0);
	require(ihk_core_kmsg_stray_delete_count_result(0, 4) == 0);
	require(ihk_core_kmsg_stray_delete_count_result(3, 4) == 0);
	require(ihk_core_kmsg_stray_delete_count_result(5, 4) == 2);
	require(ihk_core_destroy_callback_present_result(0) == 0);
	require(ihk_core_destroy_callback_present_result(0x1000) == 1);
	require(ihk_core_destroy_callback_failed_result(0) == 0);
	require(ihk_core_destroy_callback_failed_result(-5) == 1);
	require(ihk_core_destroy_os_pointer_invalid_result(0x1000, ~0UL,
			0x2000, ~0UL, 0x2000) == 0);
	require(ihk_core_destroy_os_pointer_invalid_result(0, ~0UL,
			0x2000, ~0UL, 0x2000) == 1);
	require(ihk_core_destroy_os_pointer_invalid_result(0x1000, ~0UL,
			0x2000, ~0UL, 0x3000) == 1);
	require(ihk_core_destroy_all_os_candidate_result(0x1000, ~0UL,
			0x2000, 0x2000) == 1);
	require(ihk_core_destroy_all_os_candidate_result(0, ~0UL,
			0x2000, 0x2000) == 0);
	require(ihk_core_destroy_all_os_candidate_result(0x1000, ~0UL,
			0x3000, 0x2000) == 0);
	require(ihk_core_destroy_all_os_should_restore_result(0) == 0);
	require(ihk_core_destroy_all_os_should_restore_result(-16) == 1);
	require(ihk_core_event_list_cleanup_needed_result(0) == 1);
	require(ihk_core_event_list_cleanup_needed_result(1) == 0);
	require(ihk_core_notifier_match_result(0x1000, 0x1000) == 1);
	require(ihk_core_notifier_match_result(0x1000, 0x2000) == 0);
	require(ihk_core_notifier_should_add_result(0) == 1);
	require(ihk_core_notifier_should_add_result(1) == 0);
	require(ihk_core_notifier_should_remove_result(0) == 0);
	require(ihk_core_notifier_should_remove_result(1) == 1);
	require(ihk_core_load_file_mode_result(0x1000, 0x2000) ==
			LOAD_FILE_DIRECT);
	require(ihk_core_load_file_mode_result(0, 0x2000) == LOAD_FILE_MEM);
	require(ihk_core_load_file_mode_result(0, 0) == LOAD_FILE_NONE);
	require(ihk_core_file_size_valid_result(-1) == 0);
	require(ihk_core_file_size_valid_result(0) == 0);
	require(ihk_core_file_size_valid_result(1) == 1);
	require(ihk_core_kernel_read_failed_result(-5) == 1);
	require(ihk_core_kernel_read_failed_result(0) == 1);
	require(ihk_core_kernel_read_failed_result(7) == 0);
	require(ihk_core_load_file_continue_result(0, 0, 10) == 1);
	require(ihk_core_load_file_continue_result(0, 10, 10) == 0);
	require(ihk_core_load_file_continue_result(-1, 0, 10) == 0);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_SHUTDOWN) ==
			SHUTDOWN_BUSY);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_FREEZING) ==
			(SHUTDOWN_WAIT_FROZEN | SHUTDOWN_THAW |
			 SHUTDOWN_WAIT_READY | SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_FROZEN) ==
			(SHUTDOWN_THAW | SHUTDOWN_WAIT_READY |
			 SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_BOOTING) ==
			(SHUTDOWN_WAIT_READY | SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_BOOTED) ==
			(SHUTDOWN_WAIT_READY | SHUTDOWN_WAIT_RUNNING));
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_READY) ==
			SHUTDOWN_WAIT_RUNNING);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_NOT_BOOTED) ==
			SHUTDOWN_NOT_BOOTED);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_LOADING) ==
			SHUTDOWN_WARN_LOADING);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_RUNNING) == 0);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_FAILED) == 0);
	require(ihk_core_shutdown_status_policy_result(OS_STATUS_HUNGUP) == 0);
	require(ihk_core_shutdown_status_policy_result(999) == 0);
	ihk_core_kmsg_buf_init_result((unsigned long)&fake_kmsg,
			offsetof(struct fake_kmsg_buf, lock),
			offsetof(struct fake_kmsg_buf, tail),
			offsetof(struct fake_kmsg_buf, len),
			offsetof(struct fake_kmsg_buf, head),
			offsetof(struct fake_kmsg_buf, str),
			sizeof(fake_kmsg.str));
	require(fake_kmsg.lock == 0);
	require(fake_kmsg.tail == 0);
	require(fake_kmsg.len == (int)sizeof(fake_kmsg.str));
	require(fake_kmsg.head == 0);
	require(bytes_are_zero(fake_kmsg.str, sizeof(fake_kmsg.str)));
	fake_kmsg.lock = 1;
	fake_kmsg.tail = 4;
	fake_kmsg.head = 3;
	fake_kmsg.str[0] = 'z';
	fake_kmsg.str[7] = 'q';
	ihk_core_kmsg_buf_clear_result((unsigned long)&fake_kmsg,
			offsetof(struct fake_kmsg_buf, tail),
			offsetof(struct fake_kmsg_buf, head),
			offsetof(struct fake_kmsg_buf, str),
			sizeof(fake_kmsg.str));
	require(fake_kmsg.lock == 1);
	require(fake_kmsg.tail == 0);
	require(fake_kmsg.head == 0);
	require(fake_kmsg.len == (int)sizeof(fake_kmsg.str));
	require(bytes_are_zero(fake_kmsg.str, sizeof(fake_kmsg.str)));
	ihk_core_kmsg_container_init_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, os_index),
			offsetof(struct fake_kmsg_container, kmsg_buf),
			offsetof(struct fake_kmsg_container, order),
			12, (unsigned long)&fake_kmsg, 3);
	require(fake_cont.os_index == 12);
	require(fake_cont.count == 99);
	require(fake_cont.kmsg_buf == &fake_kmsg);
	require(fake_cont.order == 3);
	ihk_core_atomic_set_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count), 2);
	require(ihk_core_atomic_read_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count)) == 2);
	ihk_core_atomic_inc_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count));
	require(fake_cont.count == 3);
	ihk_core_atomic_dec_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count));
	require(fake_cont.count == 2);
	require(ihk_core_atomic_dec_return_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count)) == 1);
	require(fake_cont.count == 1);
	require(ihk_core_atomic_cmpxchg_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count), 1, 7) == 1);
	require(fake_cont.count == 7);
	require(ihk_core_atomic_cmpxchg_i32_result((unsigned long)&fake_cont,
			offsetof(struct fake_kmsg_container, count), 1, 9) == 7);
	require(fake_cont.count == 7);
	require(ihk_core_atomic_cmpxchg_i32_result(0,
			offsetof(struct fake_kmsg_container, count), 0, 1) == 0);
	old_container = ihk_core_os_take_kmsg_container_result(
			(unsigned long)&fake_os,
			offsetof(struct fake_os_data, kmsg_buf_container));
	require(old_container == (unsigned long)&fake_cont);
	require(fake_os.kmsg_buf_container == NULL);
	require(ihk_core_os_take_kmsg_container_result(0,
			offsetof(struct fake_os_data, kmsg_buf_container)) == 0);
	ihk_core_list_add_tail_result((unsigned long)&list_a,
			(unsigned long)&list_head);
	require(list_head.next == &list_a);
	require(list_head.prev == &list_a);
	require(list_a.next == &list_head);
	require(list_a.prev == &list_head);
	ihk_core_list_add_tail_result((unsigned long)&list_b,
			(unsigned long)&list_head);
	require(list_head.next == &list_a);
	require(list_head.prev == &list_b);
	require(list_a.next == &list_b);
	require(list_b.prev == &list_a);
	require(list_b.next == &list_head);
	require(ihk_core_list_contains_entry_result(
			(unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_a) == 1);
	require(ihk_core_list_contains_entry_result(
			(unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_b) == 1);
	require(ihk_core_list_contains_entry_result(
			(unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&kmsg_a) == 0);
	require(ihk_core_list_next_entry_result((unsigned long)&list_head,
			offsetof(struct fake_list_head, next), 0) ==
			(unsigned long)&list_a);
	require(ihk_core_list_next_entry_result((unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_a) == (unsigned long)&list_b);
	require(ihk_core_list_next_entry_result((unsigned long)&list_head,
			offsetof(struct fake_list_head, next),
			(unsigned long)&list_b) == 0);
	ihk_core_list_del_result((unsigned long)&list_a,
			LIST_POISON_NEXT, LIST_POISON_PREV);
	require(list_head.next == &list_b);
	require(list_b.prev == &list_head);
	require(list_a.next == (struct fake_list_head *)LIST_POISON_NEXT);
	require(list_a.prev == (struct fake_list_head *)LIST_POISON_PREV);
	ihk_core_list_del_result((unsigned long)&list_b,
			LIST_POISON_NEXT, LIST_POISON_PREV);
	require(list_head.next == &list_head);
	require(list_head.prev == &list_head);
	ihk_core_list_add_tail_result((unsigned long)&kmsg_a.list,
			(unsigned long)&kmsg_head);
	ihk_core_list_add_tail_result((unsigned long)&kmsg_b.list,
			(unsigned long)&kmsg_head);
	require(ihk_core_kmsg_find_by_os_index_reverse_result(
			(unsigned long)&kmsg_head,
			offsetof(struct fake_kmsg_node, list),
			offsetof(struct fake_kmsg_node, os_index), 5) ==
			(unsigned long)&kmsg_b);
	require(ihk_core_kmsg_find_by_os_index_reverse_result(
			(unsigned long)&kmsg_head,
			offsetof(struct fake_kmsg_node, list),
			offsetof(struct fake_kmsg_node, os_index), 4) ==
			(unsigned long)&kmsg_a);
	require(ihk_core_kmsg_find_by_os_index_reverse_result(
			(unsigned long)&kmsg_head,
			offsetof(struct fake_kmsg_node, list),
			offsetof(struct fake_kmsg_node, os_index), 9) == 0);
	expected_dma_channel = &dma_channel;
	expected_dma_request = &dma_request;
	require(ihk_core_dma_request_result(&dma_channel, &dma_request) == 1234);
	require(dma_callback_count == 1);
	require(ihk_core_dma_request_result(&dma_channel_no_request,
			&dma_request) == -22);

	reset_user_call_state();
	require(ihk_core_os_register_user_call_handlers_result(os_backing,
			&user_call, fake_user_call_lock,
			fake_user_call_unlock) == 0);
	require(user_call_lock_calls == 1);
	require(user_call_unlock_calls == 1);
	require(user_call_unlock_last_flags == 0x77);
	require(aux_head->next == &user_call.list);
	require(aux_head->prev == &user_call.list);
	require(user_call.list.next == aux_head);
	require(user_call.list.prev == aux_head);
	require(ihk_core_os_ioctl_call_aux_result(os_backing,
			IHK_OS_AUX_CALL_START + 2, 0xa55, fake_file) == 0x345);
	require(user_call_handler_calls == 1);
	require(user_call_last_os == os_backing);
	require(user_call_last_request == IHK_OS_AUX_CALL_START + 2);
	require(user_call_last_priv == (void *)0x7002);
	require(user_call_last_arg == 0xa55);
	require(user_call_last_file == fake_file);
	require(ihk_core_os_ioctl_call_aux_result(os_backing,
			IHK_OS_AUX_CALL_START + 3, 0, fake_file) == -22);
	ihk_core_os_unregister_user_call_handlers_result(os_backing,
			&user_call, fake_user_call_lock,
			fake_user_call_unlock);
	require(user_call_lock_calls == 2);
	require(user_call_unlock_calls == 2);
	require(aux_head->next == aux_head);
	require(aux_head->prev == aux_head);
	require(ihk_core_os_register_user_call_handlers_result(os_backing,
			&bad_user_call, fake_user_call_lock,
			fake_user_call_unlock) == -22);
	require(user_call_lock_calls == 2);

	reset_notifier_state();
	require(ihk_core_host_register_os_notifier_result(&notifier_head,
			&notifier_a, offsetof(struct fake_notifier, nlist),
			fake_notifier_down, fake_notifier_up,
			fake_notifier_log) == 0);
	require(notifier_down_calls == 1);
	require(notifier_up_calls == 1);
	require(notifier_log_calls == 1);
	require(notifier_last_log_event == NOTIFIER_LOG_ADDED);
	require(notifier_head.next == &notifier_a.nlist);
	require(notifier_head.prev == &notifier_a.nlist);
	require(ihk_core_host_register_os_notifier_result(&notifier_head,
			&notifier_a, offsetof(struct fake_notifier, nlist),
			fake_notifier_down, fake_notifier_up,
			fake_notifier_log) == 0);
	require(notifier_log_calls == 1);
	require(ihk_core_host_register_os_notifier_result(&notifier_head,
			&notifier_b, offsetof(struct fake_notifier, nlist),
			fake_notifier_down, fake_notifier_up,
			fake_notifier_log) == 0);
	require(notifier_log_calls == 2);
	require(notifier_last_log_event == NOTIFIER_LOG_ADDED);
	require(notifier_head.prev == &notifier_b.nlist);
	require(ihk_core_host_deregister_os_notifier_result(&notifier_head,
			&notifier_a, offsetof(struct fake_notifier, nlist),
			fake_notifier_down, fake_notifier_up,
			fake_notifier_log) == 0);
	require(notifier_log_calls == 3);
	require(notifier_last_log_event == NOTIFIER_LOG_REMOVED);
	require(notifier_head.next == &notifier_b.nlist);
	require(ihk_core_host_deregister_os_notifier_result(&notifier_head,
			&notifier_a, offsetof(struct fake_notifier, nlist),
			fake_notifier_down, fake_notifier_up,
			fake_notifier_log) == 0);
	require(notifier_log_calls == 3);
	notifier_down_ret = -1;
	require(ihk_core_host_register_os_notifier_result(&notifier_head,
			&notifier_a, offsetof(struct fake_notifier, nlist),
			fake_notifier_down, fake_notifier_up,
			fake_notifier_log) == -512);
	require(notifier_up_calls == 5);

	{
		struct fake_ihk_resource resource;
		struct fake_ihk_resource cpu_resource;

		reset_host_driver_wrapper_state();
		host_os_resource_ret = 701;
		memset(&resource, 0xff, sizeof(resource));
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				&resource, OS_RESOURCE_ALLOC_MEM, 0x12340UL, 0,
				fake_os_alloc_resource) == 701);
		require(host_os_resource_calls == 1);
		require(host_os_resource_last_os == host_driver_fake_os);
		require(host_os_resource_flags == 0);
		require(host_os_resource_cpu_cores == 0);
		require(host_os_resource_mem_size == 0x12340UL);
		require(host_os_resource_mem_start == 0);

		reset_host_driver_wrapper_state();
		host_os_resource_ret = 702;
		memset(&resource, 0xff, sizeof(resource));
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				&resource, OS_RESOURCE_ALLOC_CPU, 7, 0,
				fake_os_alloc_resource) == 702);
		require(host_os_resource_calls == 1);
		require(host_os_resource_flags == 0);
		require(host_os_resource_cpu_cores == 7);
		require(host_os_resource_mem_size == 0);
		require(host_os_resource_mem_start == 0);

		reset_host_driver_wrapper_state();
		host_os_resource_ret = 703;
		memset(&cpu_resource, 0xff, sizeof(cpu_resource));
		cpu_resource.cores[0] = 11;
		cpu_resource.cores[1] = 22;
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				&cpu_resource, OS_RESOURCE_RESERVE_CPU,
				2, 0, fake_os_alloc_resource) == 703);
		require(host_os_resource_calls == 1);
		require(host_os_resource_flags == RESOURCE_FLAG_CPU_SPECIFIED);
		require(host_os_resource_cpu_cores == 2);
		require(host_os_resource_mem_size == 0);
		require(host_os_resource_mem_start == 0);
		require(host_os_resource_core0 == 11);
		require(host_os_resource_core1 == 22);

		reset_host_driver_wrapper_state();
		host_os_resource_ret = 704;
		memset(&resource, 0xff, sizeof(resource));
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				&resource, OS_RESOURCE_RESERVE_MEM,
				0x500000UL, 0x8000UL,
				fake_os_alloc_resource) == 704);
		require(host_os_resource_calls == 1);
		require(host_os_resource_flags == RESOURCE_FLAG_MEM_SPECIFIED);
		require(host_os_resource_cpu_cores == 0);
		require(host_os_resource_mem_start == 0x500000UL);
		require(host_os_resource_mem_size == 0x8000UL);

		require(ihk_core_os_resource_body_result(NULL, &resource,
				OS_RESOURCE_ALLOC_MEM, 1, 0,
				fake_os_alloc_resource) == -22);
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				NULL, OS_RESOURCE_ALLOC_MEM, 1, 0,
				fake_os_alloc_resource) == -22);
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				&resource, 99, 1, 0,
				fake_os_alloc_resource) == -22);
		require(ihk_core_os_resource_body_result(host_driver_fake_os,
				&resource, OS_RESOURCE_ALLOC_MEM, 1, 0,
				NULL) == -22);
	}

	{
		char kbuf[] = "console=ttyS0";
		int dump_args = 41;
		char user_src[] = "abcdefgh";
		char user_dst[16];
		long long off;

		reset_host_driver_wrapper_state();
		host_os_buffer_ret = 741;
		require(ihk_core_os_set_kargs_body_result(host_driver_fake_os,
				kbuf, fake_os_buffer_call) == 741);
		require(host_os_buffer_calls == 1);
		require(host_os_buffer_last_os == host_driver_fake_os);
		require(host_os_buffer_last_arg == kbuf);
		require(ihk_core_os_set_kargs_body_result(NULL, kbuf,
				fake_os_buffer_call) == -22);
		require(ihk_core_os_set_kargs_body_result(host_driver_fake_os,
				NULL, fake_os_buffer_call) == -22);
		require(ihk_core_os_set_kargs_body_result(host_driver_fake_os,
				kbuf, NULL) == -22);

		reset_host_driver_wrapper_state();
		host_os_buffer_ret = -5;
		require(ihk_core_os_dump_body_result(host_driver_fake_os,
				&dump_args, fake_os_buffer_call) == -5);
		require(host_os_buffer_calls == 1);
		require(host_os_buffer_last_arg == &dump_args);
		require(ihk_core_os_dump_body_result(host_driver_fake_os,
				NULL, fake_os_buffer_call) == -22);

		reset_host_driver_wrapper_state();
		off = 9;
		require(ihk_core_host_os_write_body_result(host_driver_fake_os,
				user_src, 8, &off, 16, fake_host_alloc,
				fake_host_copy_from_count,
				fake_host_os_load_memory,
				fake_host_free) == 8);
		require(host_alloc_calls == 1);
		require(host_alloc_size == 8);
		require(host_copy_from_count_calls == 1);
		require(host_os_load_memory_calls == 1);
		require(host_os_load_memory_last_buf == host_alloc_storage);
		require(host_os_load_memory_last_size == 8);
		require(host_os_load_memory_last_offset == 9);
		require(memcmp(host_alloc_storage, user_src, 8) == 0);
		require(host_free_calls == 1);
		require(off == 17);

		reset_host_driver_wrapper_state();
		off = 3;
		require(ihk_core_host_os_write_body_result(host_driver_fake_os,
				user_src, 17, &off, 16, fake_host_alloc,
				fake_host_copy_from_count,
				fake_host_os_load_memory,
				fake_host_free) == -7);
		require(host_alloc_calls == 0);
		require(off == 3);

		reset_host_driver_wrapper_state();
		host_alloc_fail = 1;
		off = 3;
		require(ihk_core_host_os_write_body_result(host_driver_fake_os,
				user_src, 8, &off, 16, fake_host_alloc,
				fake_host_copy_from_count,
				fake_host_os_load_memory,
				fake_host_free) == -12);
		require(host_alloc_calls == 1);
		require(host_free_calls == 0);
		require(off == 3);

		reset_host_driver_wrapper_state();
		host_copy_from_not_copied = 2;
		off = 3;
		require(ihk_core_host_os_write_body_result(host_driver_fake_os,
				user_src, 8, &off, 16, fake_host_alloc,
				fake_host_copy_from_count,
				fake_host_os_load_memory,
				fake_host_free) == -14);
		require(host_copy_from_count_calls == 1);
		require(host_os_load_memory_calls == 0);
		require(host_free_calls == 1);
		require(off == 3);

		reset_host_driver_wrapper_state();
		host_os_load_memory_ret = -33;
		off = 3;
		require(ihk_core_host_os_write_body_result(host_driver_fake_os,
				user_src, 8, &off, 16, fake_host_alloc,
				fake_host_copy_from_count,
				fake_host_os_load_memory,
				fake_host_free) == -33);
		require(host_free_calls == 1);
		require(off == 3);

		reset_host_driver_wrapper_state();
		memcpy(host_device_va, "read-data", 9);
		memset(user_dst, 0, sizeof(user_dst));
		off = 4;
		require(ihk_core_host_device_io_body_result(
				host_driver_fake_dev, user_dst, 9, &off,
				DEVICE_IO_READ, fake_host_device_map_memory,
				fake_host_device_map_virtual,
				fake_host_copy_to_count,
				fake_host_copy_from_count,
				fake_host_device_unmap_virtual) == 9);
		require(host_device_map_memory_calls == 1);
		require(host_device_map_memory_last_off == 4);
		require(host_device_map_virtual_calls == 1);
		require(host_device_map_virtual_last_pa == 0x9000UL);
		require(host_copy_to_count_calls == 1);
		require(memcmp(user_dst, "read-data", 9) == 0);
		require(host_device_unmap_virtual_calls == 1);
		require(off == 13);

		reset_host_driver_wrapper_state();
		off = 10;
		host_copy_from_not_copied = 3;
		require(ihk_core_host_device_io_body_result(
				host_driver_fake_dev, user_src, 8, &off,
				DEVICE_IO_WRITE, fake_host_device_map_memory,
				fake_host_device_map_virtual,
				fake_host_copy_to_count,
				fake_host_copy_from_count,
				fake_host_device_unmap_virtual) == 5);
		require(host_copy_from_count_calls == 1);
		require(memcmp(host_device_va, user_src, 5) == 0);
		require(host_device_unmap_virtual_calls == 1);
		require(off == 15);

		reset_host_driver_wrapper_state();
		host_device_map_memory_ret = 0;
		off = 10;
		require(ihk_core_host_device_io_body_result(
				host_driver_fake_dev, user_src, 8, &off,
				DEVICE_IO_WRITE, fake_host_device_map_memory,
				fake_host_device_map_virtual,
				fake_host_copy_to_count,
				fake_host_copy_from_count,
				fake_host_device_unmap_virtual) == -22);
		require(host_device_map_virtual_calls == 0);
		require(host_device_unmap_virtual_calls == 0);
		require(off == 10);

		reset_host_driver_wrapper_state();
		host_device_map_virtual_fail = 1;
		off = 10;
		require(ihk_core_host_device_io_body_result(
				host_driver_fake_dev, user_src, 8, &off,
				DEVICE_IO_WRITE, fake_host_device_map_memory,
				fake_host_device_map_virtual,
				fake_host_copy_to_count,
				fake_host_copy_from_count,
				fake_host_device_unmap_virtual) == -12);
		require(host_device_unmap_virtual_calls == 0);
		require(off == 10);

		reset_host_driver_wrapper_state();
		off = 10;
		require(ihk_core_host_device_io_body_result(
				host_driver_fake_dev, user_dst, 4, &off,
				DEVICE_IO_READ, fake_host_device_map_memory,
				fake_host_device_map_virtual,
				NULL, fake_host_copy_from_count,
				fake_host_device_unmap_virtual) == -22);
		require(host_device_unmap_virtual_calls == 1);
		require(off == 10);
	}

	{
		struct fake_smp_host_os host_os;
		struct fake_smp_monitor monitor;
		char usage_dst[1200];
		char read_dst[16];
		char kmsg_out[16];
		char kmsg_user[16];
		struct fake_os_read_kaddr_desc read_desc;
		struct fake_device_get_kmsg_buf_desc get_kmsg_desc;
		struct fake_device_read_kmsg_buf_desc read_kmsg_desc;

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_RUNNING;
		require(ihk_core_os_status_body_result(host_driver_fake_os,
				fake_host_os_status) == OS_STATUS_RUNNING);
		require(host_os_status_calls == 1);

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_RUNNING;
		host_os_simple_ret = 812;
		require(ihk_core_os_freeze_body_result(host_driver_fake_os,
				fake_host_os_status, fake_host_os_simple,
				fake_host_os_log) == 812);
		require(host_os_status_calls == 1);
		require(host_os_simple_calls == 1);
		require(host_os_log_calls == 0);

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_FROZEN;
		require(ihk_core_os_freeze_body_result(host_driver_fake_os,
				fake_host_os_status, fake_host_os_simple,
				fake_host_os_log) == -16);
		require(host_os_simple_calls == 0);
		require(host_os_log_calls == 0);

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_READY;
		require(ihk_core_os_freeze_body_result(host_driver_fake_os,
				fake_host_os_status, fake_host_os_simple,
				fake_host_os_log) == -22);
		require(host_os_simple_calls == 0);
		require(host_os_log_calls == 1);
		require(host_os_last_log_event == OS_FREEZE_LOG_INVALID);
		require(host_os_last_log_value == OS_STATUS_READY);

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_FREEZING;
		host_os_simple_ret = 813;
		require(ihk_core_os_thaw_body_result(host_driver_fake_os,
				fake_host_os_status, fake_host_os_wait,
				fake_host_os_simple, fake_host_os_log) == 813);
		require(host_os_wait_calls == 1);
		require(host_os_wait_status == OS_STATUS_FROZEN);
		require(host_os_wait_sleepable == 0);
		require(host_os_wait_timeout == 100);
		require(host_os_simple_calls == 1);
		require(host_os_log_calls == 1);
		require(host_os_last_log_event == OS_THAW_LOG_WAIT_FROZEN);

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_FREEZING;
		host_os_wait_ret = -1;
		require(ihk_core_os_thaw_body_result(host_driver_fake_os,
				fake_host_os_status, fake_host_os_wait,
				fake_host_os_simple, fake_host_os_log) == 0);
		require(host_os_wait_calls == 1);
		require(host_os_log_calls == 2);
		require(host_os_last_log_event == OS_THAW_LOG_WAIT_TIMEOUT);

		reset_host_driver_wrapper_state();
		host_os_status_ret = OS_STATUS_READY;
		require(ihk_core_os_thaw_body_result(host_driver_fake_os,
				fake_host_os_status, fake_host_os_wait,
				fake_host_os_simple, fake_host_os_log) == -22);
		require(host_os_wait_calls == 0);
		require(host_os_simple_calls == 0);
		require(host_os_last_log_event == OS_THAW_LOG_INVALID);

		reset_host_driver_wrapper_state();
		memset(&host_os, 0, sizeof(host_os));
		memset(&monitor, 0, sizeof(monitor));
		monitor.num_processors = 2;
		monitor.cpu[0].status = 11;
		monitor.cpu[1].status = 22;
		host_setup_monitor_value = &monitor;
		memset(usage_dst, 0, sizeof(usage_dst));
		require(ihk_core_os_get_usage_body_result(&host_os,
				usage_dst, fake_host_setup_monitor,
				fake_host_copy_to_user) == 0);
		require(host_setup_monitor_calls == 1);
		require(host_copy_to_user_calls == 1);
		require(host_copy_to_user_src == &monitor);
		require(host_copy_to_user_size ==
				offsetof(struct fake_smp_monitor, cpu));
		require(((struct fake_smp_monitor *)usage_dst)->num_processors == 2);

		reset_host_driver_wrapper_state();
		memset(&host_os, 0, sizeof(host_os));
		host_setup_monitor_value = &monitor;
		memset(usage_dst, 0, sizeof(usage_dst));
		require(ihk_core_os_get_cpu_usage_body_result(&host_os,
				usage_dst, fake_host_setup_monitor,
				fake_host_copy_to_user) == 0);
		require(host_copy_to_user_src == monitor.cpu);
		require(host_copy_to_user_size ==
				sizeof(struct fake_smp_monitor_cpu) * 2);
		require(((struct fake_smp_monitor_cpu *)usage_dst)[1].status == 22);

		reset_host_driver_wrapper_state();
		memset(&host_os, 0, sizeof(host_os));
		host_setup_monitor_publish = 0;
		require(ihk_core_os_get_usage_body_result(&host_os,
				usage_dst, fake_host_setup_monitor,
				fake_host_copy_to_user) == -38);
		require(host_copy_to_user_calls == 0);

		reset_host_driver_wrapper_state();
		memset(&host_os, 0, sizeof(host_os));
		host_setup_monitor_value = &monitor;
		host_copy_to_user_fail = 1;
		require(ihk_core_os_get_cpu_usage_body_result(&host_os,
				usage_dst, fake_host_setup_monitor,
				fake_host_copy_to_user) == -14);

		reset_host_driver_wrapper_state();
		memcpy(host_phys_to_virt_storage, "kernel", 6);
		memset(read_dst, 0, sizeof(read_dst));
		read_desc.kaddr = 0x30;
		read_desc.len = 6;
		read_desc.ubuf = read_dst;
		read_desc.flags = READ_KADDR_PHYS;
		require(ihk_core_os_read_kaddr_body_result(host_driver_fake_os,
				&read_desc, fake_host_os_vtop,
				fake_host_phys_to_virt,
				fake_host_copy_to_user) == 0);
		require(host_os_vtop_calls == 0);
		require(host_phys_to_virt_last_phys == 0x30);
		require(memcmp(read_dst, "kernel", 6) == 0);

		reset_host_driver_wrapper_state();
		memcpy(host_phys_to_virt_storage, "virtio", 6);
		memset(read_dst, 0, sizeof(read_dst));
		host_os_vtop_phys = 0x44;
		read_desc.kaddr = 0x1234;
		read_desc.len = 6;
		read_desc.ubuf = read_dst;
		read_desc.flags = 0;
		require(ihk_core_os_read_kaddr_body_result(host_driver_fake_os,
				&read_desc, fake_host_os_vtop,
				fake_host_phys_to_virt,
				fake_host_copy_to_user) == 0);
		require(host_os_vtop_calls == 1);
		require(host_os_vtop_last_kaddr == 0x1234);
		require(host_phys_to_virt_last_phys == 0x44);
		require(memcmp(read_dst, "virtio", 6) == 0);

		reset_host_driver_wrapper_state();
		host_os_vtop_ret = -1;
		read_desc.flags = 0;
		require(ihk_core_os_read_kaddr_body_result(host_driver_fake_os,
				&read_desc, fake_host_os_vtop,
				fake_host_phys_to_virt,
				fake_host_copy_to_user) == -14);
		require(host_phys_to_virt_calls == 0);

		reset_host_driver_wrapper_state();
		memset(&fake_kmsg, 0, sizeof(fake_kmsg));
		fake_kmsg.len = sizeof(fake_kmsg.str);
		fake_kmsg.head = 6;
		fake_kmsg.tail = 3;
		memcpy(fake_kmsg.str, "abc", 3);
		memcpy(fake_kmsg.str + 6, "xy", 2);
		memset(kmsg_out, 0, sizeof(kmsg_out));
		require(ihk_core_read_kmsg_body_result((unsigned long)&fake_kmsg,
				kmsg_out, 1,
				offsetof(struct fake_kmsg_buf, lock),
				offsetof(struct fake_kmsg_buf, tail),
				offsetof(struct fake_kmsg_buf, len),
				offsetof(struct fake_kmsg_buf, head),
				offsetof(struct fake_kmsg_buf, str),
				fake_host_irq_save, fake_host_irq_restore,
				fake_host_cpu_relax) == 5);
		require(memcmp(kmsg_out, "xyabc", 5) == 0);
		require(fake_kmsg.head == 3);
		require(fake_kmsg.lock == 0);
		require(host_irq_save_calls == 1);
		require(host_irq_restore_calls == 1);
		require(host_irq_restore_last_flags == 0x88);

		reset_host_driver_wrapper_state();
		memset(&fake_kmsg, 'q', sizeof(fake_kmsg));
		fake_kmsg.lock = 0;
		fake_kmsg.len = sizeof(fake_kmsg.str);
		fake_kmsg.head = 2;
		fake_kmsg.tail = 5;
		require(ihk_core_clear_kmsg_body_result(
				(unsigned long)&fake_kmsg,
				offsetof(struct fake_kmsg_buf, lock),
				offsetof(struct fake_kmsg_buf, tail),
				offsetof(struct fake_kmsg_buf, head),
				offsetof(struct fake_kmsg_buf, str),
				sizeof(fake_kmsg.str),
				fake_host_irq_save, fake_host_irq_restore,
				fake_host_cpu_relax) == 0);
		require(fake_kmsg.lock == 0);
		require(fake_kmsg.head == 0);
		require(fake_kmsg.tail == 0);
		require(bytes_are_zero(fake_kmsg.str, sizeof(fake_kmsg.str)));

		reset_host_driver_wrapper_state();
		memset(os_backing, 0, sizeof(os_backing));
		memset(kmsg_user, 0, sizeof(kmsg_user));
		fake_cont.kmsg_buf = &fake_kmsg;
		*(void **)(os_backing + OS_OFF_KMSG_CONTAINER) = &fake_cont;
		require(ihk_core_os_read_kmsg_body_result(os_backing,
				kmsg_user, fake_host_kmsg_alloc,
				fake_host_read_kmsg, fake_host_copy_to_user,
				fake_host_kmsg_free) == 5);
		require(host_kmsg_alloc_calls == 1);
		require(host_kmsg_alloc_size == HOST_KMSG_ALLOC_SIZE);
		require(host_read_kmsg_calls == 1);
		require(host_read_kmsg_last_kmsg == &fake_kmsg);
		require(host_read_kmsg_last_shift == 0);
		require(memcmp(kmsg_user, "kmsg!", 5) == 0);
		require(host_kmsg_free_calls == 1);

		reset_host_driver_wrapper_state();
		host_kmsg_alloc_fail = 1;
		require(ihk_core_os_read_kmsg_body_result(os_backing,
				kmsg_user, fake_host_kmsg_alloc,
				fake_host_read_kmsg, fake_host_copy_to_user,
				fake_host_kmsg_free) == -12);
		require(host_read_kmsg_calls == 0);
		require(host_kmsg_free_calls == 0);

		reset_host_driver_wrapper_state();
		memset(&fake_kmsg, 'z', sizeof(fake_kmsg));
		fake_kmsg.lock = 0;
		fake_kmsg.len = sizeof(fake_kmsg.str);
		fake_kmsg.head = 3;
		fake_kmsg.tail = 6;
		require(ihk_core_os_clear_kmsg_body_result(os_backing,
				offsetof(struct fake_kmsg_buf, lock),
				offsetof(struct fake_kmsg_buf, tail),
				offsetof(struct fake_kmsg_buf, head),
				offsetof(struct fake_kmsg_buf, str),
				sizeof(fake_kmsg.str),
				fake_host_irq_save, fake_host_irq_restore,
				fake_host_cpu_relax) == 0);
		require(fake_kmsg.head == 0);
		require(fake_kmsg.tail == 0);
		require(bytes_are_zero(fake_kmsg.str, sizeof(fake_kmsg.str)));

		reset_host_driver_wrapper_state();
		reset_fake_boot();
		fake_boot_kmsg_container = &fake_cont;
		get_kmsg_desc.os_index = 4;
		get_kmsg_desc.handle = NULL;
		require(ihk_core_device_get_kmsg_buf_body_result(
				&get_kmsg_desc, fake_boot_kmsg_lock,
				fake_boot_kmsg_find, fake_boot_kmsg_inc,
				fake_boot_kmsg_unlock,
				fake_host_copy_from_count,
				fake_host_copy_to_user) == 0);
		require(boot_kmsg_find_last_index == 4);
		require(boot_kmsg_inc_calls == 1);
		require(get_kmsg_desc.handle == &fake_cont);

		reset_host_driver_wrapper_state();
		reset_fake_boot();
		fake_boot_find_miss = 1;
		get_kmsg_desc.os_index = 8;
		require(ihk_core_device_get_kmsg_buf_body_result(
				&get_kmsg_desc, fake_boot_kmsg_lock,
				fake_boot_kmsg_find, fake_boot_kmsg_inc,
				fake_boot_kmsg_unlock,
				fake_host_copy_from_count,
				fake_host_copy_to_user) == -2);
		require(boot_kmsg_inc_calls == 0);

		reset_host_driver_wrapper_state();
		memset(kmsg_user, 0, sizeof(kmsg_user));
		fake_cont.kmsg_buf = &fake_kmsg;
		read_kmsg_desc.handle = &fake_cont;
		read_kmsg_desc.shift = 1;
		read_kmsg_desc.buf = kmsg_user;
		require(ihk_core_device_read_kmsg_buf_body_result(
				&read_kmsg_desc, fake_host_kmsg_alloc,
				fake_host_read_kmsg, fake_host_copy_from_count,
				fake_host_copy_to_user,
				fake_host_kmsg_free) == 5);
		require(host_read_kmsg_last_kmsg == &fake_kmsg);
		require(host_read_kmsg_last_shift == 1);
		require(memcmp(kmsg_user, "kmsg!", 5) == 0);
		require(host_kmsg_free_calls == 1);

		reset_host_driver_wrapper_state();
		host_read_kmsg_ret = -7;
		require(ihk_core_device_read_kmsg_buf_body_result(
				&read_kmsg_desc, fake_host_kmsg_alloc,
				fake_host_read_kmsg, fake_host_copy_from_count,
				fake_host_copy_to_user,
				fake_host_kmsg_free) == -7);
		require(host_copy_to_user_calls == 0);
		require(host_kmsg_free_calls == 1);

		reset_host_driver_wrapper_state();
		host_release_kmsg_ret = -6;
		require(ihk_core_device_release_kmsg_buf_body_result(
				&fake_cont, fake_host_release_kmsg) == -6);
		require(host_release_kmsg_calls == 1);
		require(host_release_kmsg_last_handle == &fake_cont);
	}

	reset_host_driver_wrapper_state();
	host_debug_ret = 331;
	require(ihk_core_os_debug_request_body_result(host_driver_fake_os,
			0x122a01, 0xabcUL, fake_os_debug_present,
			fake_os_debug_call) == 331);
	require(host_os_debug_present_calls == 1);
	require(host_os_debug_call_calls == 1);
	require(host_debug_last_ptr == host_driver_fake_os);
	require(host_debug_last_request == 0x122a01);
	require(host_debug_last_arg == 0xabcUL);
	host_debug_present_value = 0;
	require(ihk_core_os_debug_request_body_result(host_driver_fake_os,
			0x122a02, 0xdefUL, fake_os_debug_present,
			fake_os_debug_call) == -22);
	require(host_os_debug_present_calls == 2);
	require(host_os_debug_call_calls == 1);
	require(ihk_core_os_debug_request_body_result(NULL, 0x122a02,
			0, fake_os_debug_present, fake_os_debug_call) == -22);
	require(ihk_core_os_debug_request_body_result(host_driver_fake_os,
			0x122a02, 0, NULL, fake_os_debug_call) == -22);

	reset_host_driver_wrapper_state();
	host_debug_ret = 654;
	require(ihk_core_device_debug_request_body_result(host_driver_fake_dev,
			0x122901, 0xaceUL, fake_device_debug_present,
			fake_device_debug_call) == 654);
	require(host_device_debug_present_calls == 1);
	require(host_device_debug_call_calls == 1);
	require(host_debug_last_ptr == host_driver_fake_dev);
	require(host_debug_last_request == 0x122901);
	require(host_debug_last_arg == 0xaceUL);
	host_debug_present_value = 0;
	require(ihk_core_device_debug_request_body_result(host_driver_fake_dev,
			0x122902, 0, fake_device_debug_present,
			fake_device_debug_call) == -22);
	require(host_device_debug_present_calls == 2);
	require(host_device_debug_call_calls == 1);
	require(ihk_core_device_debug_request_body_result(NULL, 0x122902,
			0, fake_device_debug_present,
			fake_device_debug_call) == -22);
	require(ihk_core_device_debug_request_body_result(host_driver_fake_dev,
			0x122902, 0, fake_device_debug_present, NULL) == -22);

	{
		char buildid_buf[16] = { 0 };
		const char buildid[] = "BUILD42";

		reset_host_driver_wrapper_state();
		require(ihk_core_device_get_buildid_body_result(buildid_buf,
				buildid, sizeof(buildid),
				fake_host_copy_to_user) == 0);
		require(host_copy_to_user_calls == 1);
		require(host_copy_to_user_dst == buildid_buf);
		require(host_copy_to_user_src == buildid);
		require(host_copy_to_user_size == sizeof(buildid));
		require(memcmp(buildid_buf, buildid, sizeof(buildid)) == 0);
		host_copy_to_user_fail = 1;
		require(ihk_core_device_get_buildid_body_result(buildid_buf,
				buildid, sizeof(buildid),
				fake_host_copy_to_user) == -14);
		require(ihk_core_device_get_buildid_body_result(NULL, buildid,
				sizeof(buildid), fake_host_copy_to_user) == -22);
		require(ihk_core_device_get_buildid_body_result(buildid_buf,
				NULL, sizeof(buildid), fake_host_copy_to_user) == -22);
		require(ihk_core_device_get_buildid_body_result(buildid_buf,
				buildid, 0, fake_host_copy_to_user) == -22);
		require(ihk_core_device_get_buildid_body_result(buildid_buf,
				buildid, sizeof(buildid), NULL) == -22);
	}

	{
		int op;
		const int device_ops[] = {
			DEVICE_OP_RESERVE_CPU,
			DEVICE_OP_RELEASE_CPU,
			DEVICE_OP_RESERVE_MEM,
			DEVICE_OP_RELEASE_MEM,
			DEVICE_OP_RELEASE_MEM_PARTIAL,
			DEVICE_OP_GET_NUM_CPUS,
			DEVICE_OP_QUERY_CPU,
			DEVICE_OP_QUERY_MEM,
		};

		for (op = 0; op < (int)(sizeof(device_ops) /
				sizeof(device_ops[0])); op++) {
			int id = device_ops[op];
			unsigned long arg = 0xabc0UL + id;

			reset_host_driver_wrapper_state();
			host_device_op_ret[id] = 300 + id;
			require(ihk_core_device_op_body_result(
					host_driver_fake_dev, id, arg,
					fake_device_op_present,
					fake_device_op_call) == 300 + id);
			require(host_device_op_present_calls == 1);
			require(host_device_op_call_calls == 1);
			require(host_device_op_last_dev == host_driver_fake_dev);
			require(host_device_op_last_op == id);
			require(host_device_op_last_arg == arg);
		}
		reset_host_driver_wrapper_state();
		host_device_op_present_value[DEVICE_OP_QUERY_MEM] = 0;
		require(ihk_core_device_op_body_result(host_driver_fake_dev,
				DEVICE_OP_QUERY_MEM, 0x77,
				fake_device_op_present,
				fake_device_op_call) == -1);
		require(host_device_op_present_calls == 1);
		require(host_device_op_call_calls == 0);
		require(ihk_core_device_op_body_result(NULL, DEVICE_OP_QUERY_MEM,
				0, fake_device_op_present,
				fake_device_op_call) == -1);
		require(ihk_core_device_op_body_result(host_driver_fake_dev, 99,
				0, fake_device_op_present,
				fake_device_op_call) == -1);
		require(ihk_core_device_op_body_result(host_driver_fake_dev,
				DEVICE_OP_QUERY_MEM, 0, NULL,
				fake_device_op_call) == -22);
		require(ihk_core_device_op_body_result(host_driver_fake_dev,
				DEVICE_OP_QUERY_MEM, 0, fake_device_op_present,
				NULL) == -22);
	}

	xchg_value = 7;
	require(xchg4(&xchg_value, 9) == 7);
	require(xchg_value == 9);
	require(mcctrl_pte_is_write_combined_result(1UL << 3) == 1);
	require(mcctrl_pte_is_write_combined_result((1UL << 3) | (1UL << 4)) == 0);
	require(mcctrl_pte_is_write_combined_result(0) == 0);
	require(mcctrl_control_request_needs_root_result(0x11290100) == 1);
	require(mcctrl_control_request_needs_root_result(0x11290105) == 1);
	require(mcctrl_control_request_needs_root_result(0x1234) == 0);
	require(mcctrl_control_perm_result(0x11290100, 1000) == -1);
	require(mcctrl_control_perm_result(0x11290100, 0) == 0);
	require(mcctrl_control_perm_result(0x1234, 1000) == 0);
	require(mcctrl_cpu_register_copyback_result(0, 0) == 1);
	require(mcctrl_cpu_register_copyback_result(1, 0) == 0);
	require(mcctrl_lwk_to_linux_index_result(mapping, 3, 1) == 2);
	require(mcctrl_lwk_to_linux_index_result(mapping, 3, -1) == -1);
	require(mcctrl_lwk_to_linux_index_result(mapping, 3, 3) == -1);
	require(mcctrl_linux_to_lwk_index_result(mapping, 3, 7) == 2);
	require(mcctrl_linux_to_lwk_index_result(mapping, 3, 5) == -1);
	require(mckernel_cpu_2_linux_cpu(fake_sysfs_usrdata, 0) == 4);
	require(mckernel_cpu_2_linux_cpu(fake_sysfs_usrdata, 2) == 7);
	require(mckernel_cpu_2_linux_cpu(fake_sysfs_usrdata, 3) == -1);
	require(mckernel_cpu_2_hw_id(fake_sysfs_usrdata, 1) == 20);
	require(linux_cpu_2_mckernel_cpu(fake_sysfs_usrdata, 2) == 1);
	require(linux_cpu_2_mckernel_cpu(fake_sysfs_usrdata, 9) == -1);
	require(mckernel_numa_2_linux_numa(fake_sysfs_usrdata, 1) == 3);
	require(mckernel_numa_2_linux_numa(fake_sysfs_usrdata, 2) == -1);
	require(linux_numa_2_mckernel_numa(fake_sysfs_usrdata, 1) == 0);
	require(linux_numa_2_mckernel_numa(fake_sysfs_usrdata, 2) == -1);
	{
		unsigned long linmap = (1UL << 2) | (1UL << 7) | (1UL << 9);
		unsigned long mckmap = ~0UL;

		fake_cpumap_clear_calls = 0;
		require(mcctrl_translate_cpumap_result(mapping, 3, &linmap,
				&mckmap, 10) == 0);
		require(fake_cpumap_clear_calls == 1);
		require(mckmap == ((1UL << 1) | (1UL << 2)));
	}

	mcctrl_fill_sequential_bitset_result(bits, 70, 2, 64);
	require(bits[0] == ~0UL);
	require(bits[1] == 0x3fUL);

	mcctrl_fill_sequential_bitset_result(bits, 3, 2, 64);
	require(bits[0] == 0x7UL);
	require(bits[1] == 0);

	require(mcctrl_read_buffer_status_result(read_buf, sizeof(read_buf), 3) == 0);
	require(read_buf[3] == '\0');
	require(mcctrl_read_buffer_status_result(read_buf, 3, 3) == -28);
	require(mcctrl_read_buffer_status_result(read_buf, sizeof(read_buf), -5) == -5);
	require(mcctrl_parse_long_result(" \t-42tail", &parsed) == 1);
	require(parsed == -42);
	require(mcctrl_parse_long_result("not-a-number", &parsed) == 0);
	require(mcctrl_pci_realpath_valid_result("../../../devices/pci0000:00") == 1);
	require(mcctrl_pci_realpath_valid_result("../../wrong") == 0);
	require(mcctrl_ptr_hash_result(0x1234, 0xff) == 0x34);
	require(mcctrl_ptr_eq_result(0x1234, 0x1234) == 1);
	require(mcctrl_ptr_eq_result(0x1234, 0x1235) == 0);
	require(mcctrl_file_to_pidfd_lookup_match_result(1, 1, 2, 2) == 1);
	require(mcctrl_file_to_pidfd_lookup_match_result(1, 1, 2, 3) == 0);
	require(mcctrl_file_to_pidfd_remove_match_result(1, 1, 2, 2, 3, 3,
			4, 4) == 1);
	require(mcctrl_file_to_pidfd_remove_match_result(1, 1, 2, 2, 3, 3,
			4, 5) == 0);
	mc_plist_head_init_raw(&mc_plist_head, NULL);
	require(mc_plist_head_empty(&mc_plist_head) == 1);
	mc_plist_head_init(&mc_plist_head, NULL);
	require(mc_plist_head_empty(&mc_plist_head) == 1);
	mc_plist_node_init(&mc_plist_a, 10);
	mc_plist_node_init(&mc_plist_b, 5);
	mc_plist_node_init(&mc_plist_c, 10);
	require(mc_plist_node_empty(&mc_plist_a) == 1);
	require(mc_plist_node_empty(&mc_plist_b) == 1);
	require(mc_plist_node_empty(&mc_plist_c) == 1);
	mc_plist_add(&mc_plist_a, &mc_plist_head);
	mc_plist_add(&mc_plist_b, &mc_plist_head);
	mc_plist_add(&mc_plist_c, &mc_plist_head);
	require(mc_plist_head_empty(&mc_plist_head) == 0);
	require(mc_plist_first(&mc_plist_head) == &mc_plist_b);
	require(mc_plist_head.node_list.next == &mc_plist_b.plist.node_list);
	require(mc_plist_b.plist.node_list.next == &mc_plist_a.plist.node_list);
	require(mc_plist_a.plist.node_list.next == &mc_plist_c.plist.node_list);
	require(mc_plist_c.plist.node_list.next == &mc_plist_head.node_list);
	require(mc_plist_head.prio_list.next == &mc_plist_b.plist.prio_list);
	require(mc_plist_b.plist.prio_list.next == &mc_plist_a.plist.prio_list);
	require(mc_plist_a.plist.prio_list.next == &mc_plist_head.prio_list);
	mc_plist_del(&mc_plist_a, &mc_plist_head);
	require(mc_plist_head.node_list.next == &mc_plist_b.plist.node_list);
	require(mc_plist_b.plist.node_list.next == &mc_plist_c.plist.node_list);
	require(mc_plist_c.plist.node_list.next == &mc_plist_head.node_list);
	require(mc_plist_head.prio_list.next == &mc_plist_b.plist.prio_list);
	require(mc_plist_b.plist.prio_list.next == &mc_plist_c.plist.prio_list);
	require(mc_plist_c.plist.prio_list.next == &mc_plist_head.prio_list);
	require(mc_plist_a.plist.node_list.next == &mc_plist_a.plist.node_list);
	require(mc_plist_a.plist.prio_list.next == &mc_plist_a.plist.prio_list);
	require(mc_plist_node_empty(&mc_plist_a) == 1);
	mc_plist_del(&mc_plist_b, &mc_plist_head);
	mc_plist_del(&mc_plist_c, &mc_plist_head);
	require(mc_plist_head_empty(&mc_plist_head) == 1);
	require(mc_plist_head.node_list.next == &mc_plist_head.node_list);
	require(mc_plist_head.prio_list.next == &mc_plist_head.prio_list);

	mcctrl_preempt_disable_calls = 0;
	mcctrl_preempt_enable_calls = 0;
	mcctrl_lock.head_tail = 0xffffffffU;
	ihk_mc_spinlock_init(&mcctrl_lock);
	require(mcctrl_lock.head_tail == 0);
	__ihk_mc_spinlock_lock_noirq(&mcctrl_lock);
	require(mcctrl_lock.tickets.head == 0);
	require(mcctrl_lock.tickets.tail == 2);
	require(mcctrl_preempt_disable_calls == 1);
	__ihk_mc_spinlock_unlock_noirq(&mcctrl_lock);
	require(mcctrl_lock.tickets.head == 2);
	require(mcctrl_lock.tickets.tail == 2);
	require(mcctrl_preempt_enable_calls == 1);
	mcctrl_rwlock.slock.head_tail = 0;
	mcs_rwlock_writer_lock_noirq(&mcctrl_rwlock);
	require(mcctrl_rwlock.slock.tickets.head == 0);
	require(mcctrl_rwlock.slock.tickets.tail == 2);
	mcs_rwlock_writer_unlock_noirq(&mcctrl_rwlock);
	require(mcctrl_rwlock.slock.tickets.head == 2);
	require(mcctrl_rwlock.slock.tickets.tail == 2);
	require(mcctrl_preempt_disable_calls == 2);
	require(mcctrl_preempt_enable_calls == 2);

	mcctrl_refcount.refs = -1;
	refcount_set(&mcctrl_refcount, 0);
	require(refcount_read(&mcctrl_refcount) == 0);
	require(refcount_add_not_zero(3, &mcctrl_refcount) == false);
	require(refcount_read(&mcctrl_refcount) == 0);
	refcount_set(&mcctrl_refcount, 2);
	require(refcount_add_not_zero(3, &mcctrl_refcount) == true);
	require(refcount_read(&mcctrl_refcount) == 5);
	refcount_add(7, &mcctrl_refcount);
	require(refcount_read(&mcctrl_refcount) == 12);
	require(refcount_inc_not_zero(&mcctrl_refcount) == true);
	require(refcount_read(&mcctrl_refcount) == 13);
	refcount_inc(&mcctrl_refcount);
	require(refcount_read(&mcctrl_refcount) == 14);
	require(refcount_sub_and_test(4, &mcctrl_refcount) == false);
	require(refcount_read(&mcctrl_refcount) == 10);
	require(refcount_sub_and_test(9, &mcctrl_refcount) == false);
	require(refcount_read(&mcctrl_refcount) == 1);
	require(refcount_dec_and_test(&mcctrl_refcount) == true);
	require(refcount_read(&mcctrl_refcount) == 0);
	refcount_set(&mcctrl_refcount, 2);
	refcount_dec(&mcctrl_refcount);
	require(refcount_read(&mcctrl_refcount) == 1);

	mcctrl_futex_pagefault_disable_calls = 0;
	mcctrl_futex_pagefault_enable_calls = 0;
	mcctrl_futex_get_user_calls = 0;
	mcctrl_futex_get_user_ret = 0;
	mcctrl_futex_source = 0x1234abcdU;
	mcctrl_futex_dest = 0;
	require(get_futex_value_locked(&mcctrl_futex_dest,
				&mcctrl_futex_source) == 0);
	require(mcctrl_futex_dest == 0x1234abcdU);
	require(mcctrl_futex_pagefault_disable_calls == 1);
	require(mcctrl_futex_pagefault_enable_calls == 1);
	require(mcctrl_futex_get_user_calls == 1);
	mcctrl_futex_get_user_ret = 7;
	mcctrl_futex_dest = 0;
	require(get_futex_value_locked(&mcctrl_futex_dest,
				&mcctrl_futex_source) == -14);
	require(mcctrl_futex_dest == 0);
	require(mcctrl_futex_pagefault_disable_calls == 2);
	require(mcctrl_futex_pagefault_enable_calls == 2);
	require(mcctrl_futex_get_user_calls == 2);
	mcctrl_futex_access_ok_calls = 0;
	mcctrl_futex_cmpxchg_calls = 0;
	mcctrl_futex_op_calls = 0;
	futex_word = 10;
	require(futex_atomic_cmpxchg_inatomic(&futex_word, 9, 22) == 10);
	require(futex_word == 10);
	require(mcctrl_futex_access_ok_calls == 1);
	require(mcctrl_futex_cmpxchg_calls == 1);
	require(futex_atomic_cmpxchg_inatomic(&futex_word, 10, 22) == 10);
	require(futex_word == 22);
	require(mcctrl_futex_access_ok_calls == 2);
	require(mcctrl_futex_cmpxchg_calls == 2);
	require(futex_atomic_cmpxchg_inatomic(NULL, 0, 1) == -14);
	require(mcctrl_futex_access_ok_calls == 3);
	require(mcctrl_futex_cmpxchg_calls == 2);
	futex_word = 6;
	require(futex_atomic_op_inuser(smoke_futex_encode(1, 3, 0, 6),
				&futex_word) == 1);
	require(futex_word == 9);
	require(mcctrl_futex_access_ok_calls == 4);
	require(mcctrl_futex_op_calls == 1);
	futex_word = 7;
	require(futex_atomic_op_inuser(smoke_futex_encode(3, 1, 4, 6),
				&futex_word) == 1);
	require(futex_word == 6);
	require(mcctrl_futex_access_ok_calls == 5);
	require(mcctrl_futex_op_calls == 2);
	futex_word = 8;
	require(futex_atomic_op_inuser(smoke_futex_encode(7, 1, 0, 8),
				&futex_word) == -38);
	require(futex_word == 8);
	require(mcctrl_futex_access_ok_calls == 6);
	require(mcctrl_futex_op_calls == 2);
	require(mc_jhash2(jhash_words, 0, 0x55aaU) ==
			expected_mc_jhash2(jhash_words, 0, 0x55aaU));
	require(mc_jhash2(jhash_words, 2, 0x10203040U) ==
			expected_mc_jhash2(jhash_words, 2, 0x10203040U));
	require(mc_jhash2(jhash_words, 5, 0xa5a5a5a5U) ==
			expected_mc_jhash2(jhash_words, 5, 0xa5a5a5a5U));

	require(mcctrl_tofu_dev_path_result("/proc/tofu/dev/tni1cq2") == 1);
	require(mcctrl_tofu_dev_path_result("/proc/other") == 0);
	require(mcctrl_tofu_dev_tail_offset_result() == 15);
	mcctrl_tofu_dev_name_copy_result(tofu_name, sizeof(tofu_name),
			"/proc/tofu/dev/a");
	require(tofu_name[0] == 'a');
	require(tofu_name[1] == '\0');
	require(tofu_name[9] == '\0');
	require(mcctrl_tofu_cq_path_parse_result("/proc/tofu/dev/tni12cq34",
			&tni, &cq) == 1);
	require(tni == 12 && cq == 34);
	require(mcctrl_tofu_cq_path_parse_result("/proc/tofu/dev/tni12xx34",
			&tni, &cq) == 0);
	require(is_special_sysfs_ops((void *)0) == 0);
	require(is_special_sysfs_ops((void *)1) == 1);
	require(is_special_sysfs_ops((void *)1000) == 1);
	require(is_special_sysfs_ops((void *)1001) == 0);
	require(mcctrl_sysfs_inited_result(0) == 0);
	require(mcctrl_sysfs_inited_result(0x1000) == 1);
	require(mcctrl_sysfs_path_error_result("/sys/test", 9, 32) == 0);
	require(mcctrl_sysfs_path_error_result("sys/test", 8, 32) == -2);
	require(mcctrl_sysfs_path_error_result("/sys/test", 32, 32) == -36);
	require(mcctrl_zero_mckernel_pages_step_result(
			(unsigned long)&zero_node,
			offsetof(struct fake_zero_node, to_zero_list),
			offsetof(struct fake_zero_node, zeroed_list),
			offsetof(struct fake_zero_node, nr_to_zero_pages),
			offsetof(struct fake_zero_chunk, addr),
			offsetof(struct fake_zero_chunk, size),
			offsetof(struct fake_zero_chunk, list),
			sizeof(*zero_chunk_a),
			zero_virt_base,
			SHIFT,
			&zero_addr,
			&zero_size) == 1);
	require(zero_addr == zero_phys_base);
	require(zero_size == 4096);
	require(zero_node.nr_to_zero_pages == 1);
	require(zero_node.to_zero_list.first == &zero_chunk_b->list);
	require(zero_node.zeroed_list.first == &zero_chunk_a->list);
	require(zero_chunk_a->list.next == NULL);
	require(bytes_are_zero((char *)zero_backing + sizeof(*zero_chunk_a),
			4096 - sizeof(*zero_chunk_a)));
	require(mcctrl_zero_mckernel_pages_step_result(
			(unsigned long)&zero_node,
			offsetof(struct fake_zero_node, to_zero_list),
			offsetof(struct fake_zero_node, zeroed_list),
			offsetof(struct fake_zero_node, nr_to_zero_pages),
			offsetof(struct fake_zero_chunk, addr),
			offsetof(struct fake_zero_chunk, size),
			offsetof(struct fake_zero_chunk, list),
			sizeof(*zero_chunk_b),
			zero_virt_base,
			SHIFT,
			&zero_addr,
			&zero_size) == 1);
	require(zero_addr == zero_phys_base + 4096);
	require(zero_size == 4096);
	require(zero_node.nr_to_zero_pages == 0);
	require(zero_node.to_zero_list.first == NULL);
	require(zero_node.zeroed_list.first == &zero_chunk_b->list);
	require(zero_chunk_b->list.next == &zero_chunk_a->list);
	require(bytes_are_zero((char *)zero_backing + 4096 +
			sizeof(*zero_chunk_b), 4096 - sizeof(*zero_chunk_b)));
	require(mcctrl_zero_mckernel_pages_step_result(
			(unsigned long)&zero_node,
			offsetof(struct fake_zero_node, to_zero_list),
			offsetof(struct fake_zero_node, zeroed_list),
			offsetof(struct fake_zero_node, nr_to_zero_pages),
			offsetof(struct fake_zero_chunk, addr),
			offsetof(struct fake_zero_chunk, size),
			offsetof(struct fake_zero_chunk, list),
			sizeof(*zero_chunk_b),
			zero_virt_base,
			SHIFT,
			&zero_addr,
			&zero_size) == 0);
	mcctrl_zero_mckernel_pages_finish_result((unsigned long)&zero_node,
			offsetof(struct fake_zero_node, zeroing_workers));
	require(zero_node.zeroing_workers == 0);

	reset_smp_validate_log();
	require(ihk_smp_validate_cpu_req_body_result(2, 1, 4,
			fake_smp_validate_log) == 0);
	require(smp_validate_log_calls == 0);
	require(ihk_smp_validate_cpu_req_body_result(-1, 1, 4,
			fake_smp_validate_log) == -22);
	require(smp_validate_log_calls == 1);
	require(smp_validate_last_event == SMP_VALIDATE_LENGTH);
	require(ihk_smp_validate_cpu_req_body_result(2, 0, 4,
			fake_smp_validate_log) == -22);
	require(smp_validate_log_calls == 2);
	require(smp_validate_last_event == SMP_VALIDATE_NULL);
	reset_smp_validate_log();
	require(ihk_smp_validate_ikc_req_body_result(2, 1, 1, 4,
			fake_smp_validate_log) == 0);
	require(smp_validate_log_calls == 0);
	require(ihk_smp_validate_ikc_req_body_result(5, 1, 1, 4,
			fake_smp_validate_log) == -22);
	require(smp_validate_last_event == SMP_VALIDATE_LENGTH);
	require(ihk_smp_validate_ikc_req_body_result(2, 1, 0, 4,
			fake_smp_validate_log) == -22);
	require(smp_validate_last_event == SMP_VALIDATE_NULL);
	reset_smp_validate_log();
	require(ihk_smp_validate_mem_req_body_result(1, 1, 1, 0, 50, 100,
			fake_smp_validate_log) == 0);
	require(smp_validate_log_calls == 0);
	require(ihk_smp_validate_mem_req_body_result(-1, 1, 1, 0, 50, 100,
			fake_smp_validate_log) == -22);
	require(smp_validate_last_event == SMP_VALIDATE_LENGTH);
	require(ihk_smp_validate_mem_req_body_result(1, 0, 1, 0, 50, 100,
			fake_smp_validate_log) == -22);
	require(smp_validate_last_event == SMP_VALIDATE_NULL);
	require(ihk_smp_validate_mem_req_body_result(1, 1, 1, -1, 50, 100,
			fake_smp_validate_log) == -22);
	require(smp_validate_last_event == SMP_VALIDATE_MIN_CHUNK);
	require(ihk_smp_validate_mem_req_body_result(1, 1, 1, 0, 101, 100,
			fake_smp_validate_log) == -22);
	require(smp_validate_last_event == SMP_VALIDATE_RATIO);
	require(smp_validate_last_value == 101);

	reset_smp_status_lock();
	require(ihk_smp_set_status_body_result((unsigned long)&status_obj,
			offsetof(struct fake_smp_status_object, lock),
			offsetof(struct fake_smp_status_object, status), 42,
			fake_smp_status_lock, fake_smp_status_unlock) == 0);
	require(status_obj.status == 42);
	require(smp_status_lock_calls == 1);
	require(smp_status_unlock_calls == 1);
	require(smp_status_last_lock_addr == (unsigned long)&status_obj.lock);
	require(smp_status_last_unlock_addr == (unsigned long)&status_obj.lock);
	require(smp_status_last_unlock_flags == 0xbeefUL);

	{
		unsigned long coreset[512 / (sizeof(unsigned long) * 8)] = { 0 };

		require(ihk_smp_core_isset_any(coreset) == 0);
		ihk_smp_core_set(7, coreset);
		ihk_smp_core_set(130, coreset);
		require(ihk_smp_core_isset(7, coreset) == 1);
		require(ihk_smp_core_isset(8, coreset) == 0);
		require(ihk_smp_core_isset(130, coreset) == 1);
		require(ihk_smp_core_isset_any(coreset) == 1);
		ihk_smp_core_clear(7, coreset);
		require(ihk_smp_core_isset(7, coreset) == 0);
		require(ihk_smp_core_isset(130, coreset) == 1);
		ihk_smp_core_zero(coreset);
		require(ihk_smp_core_isset(130, coreset) == 0);
		require(ihk_smp_core_isset_any(coreset) == 0);
	}

	require(ihk_smp_build_os_info_body_result((unsigned long)&osinfo,
			&osinfo_offsets) == 0);
	require(osinfo.mem_info.n_available == 1);
	require(osinfo.mem_info.n_fixed == 0);
	require(osinfo.mem_info.n_mappable == 1);
	require(osinfo.mem_info.available == &osinfo.mem_region);
	require(osinfo.mem_info.fixed == NULL);
	require(osinfo.mem_info.mappable == &osinfo.mem_region);
	require(osinfo.mem_region.start == osinfo.mem_start);
	require(osinfo.mem_region.size == osinfo.mem_end - osinfo.mem_start);
	require(osinfo.mem_info.n_numa_nodes == osinfo.nr_numa_nodes);
	require(osinfo.mem_info.numa_mapping == smp_numa_mapping);
	require(osinfo.cpu_info.n_cpus == osinfo.nr_cpus);
	require(osinfo.cpu_info.mapping == osinfo.cpu_mapping);
	require(osinfo.cpu_info.hw_ids == osinfo.cpu_hw_ids);
	require(osinfo.cpu_info.ikc_map == osinfo.cpu_ikc_map);
	require(osinfo.cpu_info.ikc_mapped == osinfo.cpu_ikc_mapped);

	special_addr = 0;
	special_size = 0;
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_KMSG,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.msg_buffer);
	require(special_size == boot_param.msg_buffer_size);
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_MIKC_QUEUE_RECV,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.mikc_queue_recv);
	require(special_size == 0x40);
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_MIKC_QUEUE_SEND,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.mikc_queue_send);
	require(special_size == 0x40);
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_MONITOR,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.monitor);
	require(special_size == boot_param.monitor_size);
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_RUSAGE,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.rusage);
	require(special_size == boot_param.rusage_size);
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_MULTI_INTR_MODE,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.multi_intr_mode_addr);
	require(special_size == sizeof(int));
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_NMI_MODE,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.nmi_mode_addr);
	require(special_size == sizeof(int));
	special_size = 0xdead;
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_MCKERNEL_DO_FUTEX,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == 0);
	require(special_addr == boot_param.mckernel_do_futex);
	require(special_size == 0xdead);
	boot_param.monitor = 0;
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, IHK_SPADDR_MONITOR,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == -22);
	boot_param.monitor = 0x4000;
	require(ihk_smp_get_special_addr_body_result(0, IHK_SPADDR_KMSG,
			&special_offsets, 0x40, sizeof(int), &special_addr,
			&special_size) == -22);
	require(ihk_smp_get_special_addr_body_result(
			(unsigned long)&boot_param, 99, &special_offsets,
			0x40, sizeof(int), &special_addr, &special_size) == -22);

	reset_smp_wait_state();
	smp_wait_query_values[0] = OS_STATUS_LOADING;
	smp_wait_query_values[1] = OS_STATUS_LOADING;
	smp_wait_query_values[2] = OS_STATUS_READY;
	require(ihk_smp_wait_for_status_body_result(0xabc, 0xdef,
			OS_STATUS_READY, 0, 5, fake_smp_wait_query,
			fake_smp_wait_delay, fake_smp_wait_log) == 0);
	require(smp_wait_query_calls == 3);
	require(smp_wait_delay_calls == 2);
	require(smp_wait_log_calls == 2);
	require(smp_wait_last_wanted == OS_STATUS_READY);
	require(smp_wait_last_current == OS_STATUS_LOADING);
	require(smp_wait_last_ihk_os == 0xabc);
	require(smp_wait_last_priv == 0xdef);
	reset_smp_wait_state();
	smp_wait_query_values[0] = OS_STATUS_LOADING;
	smp_wait_query_values[1] = OS_STATUS_LOADING;
	smp_wait_query_values[2] = OS_STATUS_LOADING;
	require(ihk_smp_wait_for_status_body_result(0xabc, 0xdef,
			OS_STATUS_READY, 0, 2, fake_smp_wait_query,
			fake_smp_wait_delay, fake_smp_wait_log) == -1);
	require(smp_wait_query_calls == 3);
	require(smp_wait_delay_calls == 2);
	require(smp_wait_log_calls == 2);
	reset_smp_wait_state();
	require(ihk_smp_wait_for_status_body_result(0xabc, 0xdef,
			OS_STATUS_READY, 1, 2, fake_smp_wait_query,
			fake_smp_wait_delay, fake_smp_wait_log) == -1);
	require(smp_wait_query_calls == 0);

	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(0, 0,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_NOT_BOOTED);
	require(smp_query_setup_calls == 0);
	require(smp_query_restore_calls == 0);
	require(smp_query_log_calls == 2);
	require(smp_query_last_event == SMP_QUERY_LOG_AFTER_MONITOR);
	require(smp_query_last_value0 == OS_STATUS_NOT_BOOTED);

	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(3, 2,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_READY);
	require(smp_query_restore_calls == 1);
	require(smp_query_setup_calls == 1);
	require(smp_query_last_data == (unsigned long)&smp_host);
	require(smp_query_last_event == SMP_QUERY_LOG_AFTER_MONITOR);
	require(smp_query_last_value0 == OS_STATUS_READY);

	smp_host.monitor = NULL;
	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(3, 2,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == -38);
	require(smp_query_setup_calls == 1);
	require(smp_query_last_value0 == -38);
	smp_host.monitor = &smp_monitor;

	smp_monitor.cpu[1].status = IHK_OS_MONITOR_PANIC;
	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(3, 2,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_FAILED);
	require(smp_query_last_event == SMP_QUERY_LOG_AFTER_MONITOR);
	require(smp_query_last_value0 == OS_STATUS_FAILED);
	smp_monitor.cpu[1].status = IHK_OS_MONITOR_IDLE;

	smp_monitor.cpu[0].status = IHK_OS_MONITOR_KERNEL_FROZEN;
	smp_monitor.cpu[1].status = IHK_OS_MONITOR_IDLE;
	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(3, 2,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_FREEZING);
	require(smp_query_last_value0 == OS_STATUS_FREEZING);

	smp_monitor.cpu[1].status = IHK_OS_MONITOR_KERNEL_FROZEN;
	smp_monitor.cpu[2].status = IHK_OS_MONITOR_KERNEL_FROZEN;
	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(3, 2,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_FROZEN);
	require(smp_query_last_value0 == OS_STATUS_FROZEN);

	smp_monitor.cpu[0].status = IHK_OS_MONITOR_IDLE;
	smp_monitor.cpu[1].status = IHK_OS_MONITOR_IDLE;
	smp_monitor.cpu[2].status = IHK_OS_MONITOR_IDLE;
	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(3, 3,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_RUNNING);
	require(smp_query_last_value0 == OS_STATUS_RUNNING);

	reset_smp_query_state();
	require(ihk_smp_query_status_body_result(99, 0,
			(unsigned long)&smp_host, &query_offsets,
			fake_smp_query_setup_monitor,
			fake_smp_query_restore_trampoline,
			fake_smp_query_log) == OS_STATUS_NOT_BOOTED);
	require(smp_query_log_calls == 3);

	reset_smp_mode_state();
	require(ihk_smp_set_mode_body_result(0x111, 0x222,
			IHK_SPADDR_MULTI_INTR_MODE, 7, 4096,
			fake_smp_mode_get_special_addr,
			fake_smp_mode_map_memory,
			fake_smp_mode_map_virtual,
			fake_smp_mode_unmap_virtual,
			fake_smp_mode_unmap_memory) == 0);
	require(smp_mode_get_calls == 1);
	require(smp_mode_get_last_type == IHK_SPADDR_MULTI_INTR_MODE);
	require(smp_mode_map_memory_calls == 1);
	require(smp_mode_map_virtual_calls == 1);
	require(smp_mode_unmap_virtual_calls == 1);
	require(smp_mode_unmap_memory_calls == 1);
	require(smp_mode_last_ihk_os == 0x111);
	require(smp_mode_last_priv == 0x222);
	require(smp_mode_last_remote_phys == 0x9000);
	require(smp_mode_last_local_phys == 0xa000);
	require(smp_mode_last_size == 4096);
	require(smp_mode_value == 7);
	reset_smp_mode_state();
	smp_mode_get_ret = -22;
	require(ihk_smp_set_mode_body_result(0x111, 0x222,
			IHK_SPADDR_NMI_MODE, 9, 4096,
			fake_smp_mode_get_special_addr,
			fake_smp_mode_map_memory,
			fake_smp_mode_map_virtual,
			fake_smp_mode_unmap_virtual,
			fake_smp_mode_unmap_memory) == -22);
	require(smp_mode_get_calls == 1);
	require(smp_mode_map_memory_calls == 0);

	require(ihk_smp_pack_available_cpus_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			STATUS_AVAILABLE, NULL, 0, &needed) == 0);
	require(needed == 2);
	require(ihk_smp_pack_available_cpus_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			STATUS_AVAILABLE, out_cpus, 3, &needed) == 0);
	require(needed == 2 && out_cpus[0] == 0 && out_cpus[1] == 3);
	require(ihk_smp_pack_available_cpus_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			STATUS_AVAILABLE, out_cpus, 1, &needed) == -22);
	require(needed == 2);
	require(ihk_smp_pack_assigned_ikc_map_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			offsetof(struct fake_smp_cpu, os),
			offsetof(struct fake_smp_cpu, ikc_map_cpu), 0x1000,
			STATUS_ASSIGNED, src_cpus, dst_cpus, 2, &needed) == 0);
	require(needed == 2 && src_cpus[0] == 1 && dst_cpus[0] == 7 &&
			src_cpus[1] == 4 && dst_cpus[1] == 9);
	require(ihk_smp_pack_assigned_ikc_map_result(cpus, 5,
			sizeof(cpus[0]), offsetof(struct fake_smp_cpu, status),
			offsetof(struct fake_smp_cpu, os),
			offsetof(struct fake_smp_cpu, ikc_map_cpu), 0x1000,
			STATUS_ASSIGNED, src_cpus, dst_cpus, 1, &needed) == -22);
	require(needed == 2);
	require(ihk_smp_assign_scan_action_result(0, 1, 4096, 4096,
			0, 0, 0) == ASSIGN_SCAN_SKIP);
	require(ihk_smp_assign_scan_action_result(1, 1, 4096, 4096,
			0, 0, 0) == ASSIGN_SCAN_EXACT);
	require(ihk_smp_assign_scan_action_result(1, 1, 8192, 4096,
			0, 0, 0) == ASSIGN_SCAN_UPDATE_MAX);
	require(ihk_smp_assign_scan_action_result(1, 1, 4096, 8192,
			1, 16384, 0) == ASSIGN_SCAN_SKIP);
	require(ihk_smp_assign_scan_action_result(1, 1, 32768, 8192,
			1, 16384, 0) == ASSIGN_SCAN_UPDATE_MAX);
	require(ihk_smp_assign_scan_action_result(1, 1, 8192, 8192,
			1, 16384, 1) == ASSIGN_SCAN_SKIP);
	require(ihk_smp_assign_no_chunk_action_result(SMP_MEM_ALL,
			SMP_MEM_ALL, 4096, 0) == ASSIGN_NO_CHUNK_ALL_DONE);
	require(ihk_smp_assign_no_chunk_action_result(8192,
			SMP_MEM_ALL, 4096, 8192) == ASSIGN_NO_CHUNK_FAKE_DONE);
	require(ihk_smp_assign_no_chunk_action_result(8192,
			SMP_MEM_ALL, 16384, 8192) == ASSIGN_NO_CHUNK_ERROR);
	require(ihk_smp_used_chunk_insert_before_result(0x1000, 0x2000) == 1);
	require(ihk_smp_used_chunk_insert_before_result(0x3000, 0x2000) == 0);

	printf("ihk_module_helpers ok map=%016lx bits=%016lx/%016lx\n",
	       map[0], bits[0], bits[1]);
	return 0;
}
