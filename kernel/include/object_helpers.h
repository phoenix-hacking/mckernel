/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_OBJECT_HELPERS_H
#define MCKERNEL_OBJECT_HELPERS_H

#include <ihk/types.h>

#define FILEOBJ_PAGE_ACTION_START_IO 1
#define FILEOBJ_PAGE_ACTION_MAP_DONE 2
#define FILEOBJ_PAGE_ACTION_USE_EXISTING 3
#define FILEOBJ_PAGE_ACTION_ERROR 4

#define SYSFS_SPECIAL_KIND_DIRECT 1
#define SYSFS_SPECIAL_KIND_STRING 2
#define SYSFS_SPECIAL_KIND_BITMAP 3
#define SYSFS_HANDLER_UNKNOWN 0
#define SYSFS_HANDLER_SHOW 1
#define SYSFS_HANDLER_STORE 2
#define SYSFS_HANDLER_RELEASE 3

#define PROCFS_STATUS_RUNNING 0
#define PROCFS_STATUS_STOPPED 1
#define PROCFS_STATUS_TRACED 2
#define PROCFS_STATUS_EXITED 3

#define PROCFS_MAPS_PATH_NONE 0
#define PROCFS_MAPS_PATH_VDSO 1
#define PROCFS_MAPS_PATH_VVAR 2
#define PROCFS_MAPS_PATH_STACK 3
#define PROCFS_MAPS_PATH_HEAP 4

#define PROCFS_LOCK_ACTION_BACKLOG 1
#define PROCFS_LOCK_ACTION_EAGAIN 2

#define PROCFS_ENTRY_UNKNOWN 0
#define PROCFS_ENTRY_MCKERNEL 1
#define PROCFS_ENTRY_STAT 2
#define PROCFS_ENTRY_CPUINFO 3
#define PROCFS_ENTRY_MEM 4
#define PROCFS_ENTRY_MAPS 5
#define PROCFS_ENTRY_PAGEMAP 6
#define PROCFS_ENTRY_STATUS 7
#define PROCFS_ENTRY_AUXV 8
#define PROCFS_ENTRY_CMDLINE 9
#define PROCFS_ENTRY_COMM 10

int memobj_unref_should_free_result(int refcnt);
int memobj_op_present_result(uintptr_t op);
int memobj_missing_page_op_result(void);
uintptr_t memobj_missing_copy_page_result(void);
int memobj_default_page_op_result(void);
int memobj_has_pager_flags_result(unsigned int flags);
int memobj_is_removable_flags_result(unsigned int flags);
int memobj_flushable_page_result(int has_page, int page_in_memobj);
int memobj_flushable_obj_result(int has_memobj, unsigned int flags);
int memobj_is_freeable_result(int has_memobj, unsigned int flags);
int memobj_callable_remap_file_pages_result(int has_memobj,
					    unsigned int flags);

int fileobj_page_hash_result(off_t off);
int fileobj_page_mode_valid_result(int mode);
int fileobj_lookup_ref_keep_result(int refcnt_after_inc);
int fileobj_create_base_flags_result(int mmap_flags);
int fileobj_apply_result_flags_result(int base_flags, int pager_flags);
int fileobj_status_from_flags_result(int flags);
int fileobj_hugetlbfs_result(int flags);
int fileobj_premap_zerofill_result(int flags);
int fileobj_premap_npages_result(size_t size);
int fileobj_validate_p2align_result(int p2align);
int fileobj_get_page_action_result(int has_page, int page_mode, int *errorp);
int fileobj_pageio_zero_result(int flags);
int fileobj_pageio_mode_after_read_result(ssize_t ssize, size_t pgsize);
int fileobj_flush_skip_result(int flags, int has_page);
int fileobj_initial_refcnt_result(void);
unsigned long fileobj_initial_sref_result(void);
int fileobj_premap_start_node_result(int nr_numa_nodes);
int fileobj_premap_next_node_result(int node, int nr_numa_nodes);
size_t fileobj_pages_bytes_result(int nr_pages);
int fileobj_premap_page_index_result(off_t off);
int fileobj_alloc_npages_result(int p2align);
unsigned long fileobj_alloc_flags_result(int flags);
size_t fileobj_alloc_size_result(int npages);
size_t fileobj_pageio_pgsize_result(int p2align);
int fileobj_pageio_should_schedule_result(int attempts);
int fileobj_new_page_mode_result(void);
int fileobj_mapped_mode_result(void);
int fileobj_path_present_result(unsigned long value);
int fileobj_invalid_page_count_result(int count);
int fileobj_should_free_hashed_page_result(int count, int page_unmap_result);
int fileobj_premap_page_present_result(uintptr_t page);
int fileobj_lookup_page_error_result(int has_page);
unsigned long fileobj_next_sref_result(unsigned long sref);
int fileobj_premap_interleave_result(unsigned long mpol_flags);

size_t devobj_npages_result(size_t len);
size_t devobj_pfn_table_npages_result(size_t npages);
size_t devobj_pfn_table_bytes_result(size_t pfn_npages);
off_t devobj_pgoff_result(off_t off);
int devobj_get_page_index_result(off_t pgoff, off_t base_pgoff,
				 size_t npages, int *ixp);
int devobj_cached_pfn_needs_fetch_result(uintptr_t pfn);
int devobj_pfn_present_result(uintptr_t pfn);
uintptr_t devobj_pfn_attr_result(uintptr_t pfn);
uintptr_t devobj_pfn_phys_result(uintptr_t pfn);
int devobj_pfn_absent_error_result(uintptr_t pfn);
int devobj_base_flags_result(void);
int devobj_initial_refcnt_result(void);
off_t devobj_pfn_request_offset_result(off_t off);
int devobj_should_store_pfn_result(uintptr_t current_pfn);
size_t devobj_map_size_result(void);
int devobj_path_present_result(unsigned long value);
int devobj_pfn_table_present_result(uintptr_t pfn_table);
uintptr_t devobj_mapped_pfn_result(uintptr_t mapped_pfn, uintptr_t attr);

int sysfs_path_error_result(ssize_t n, int path_is_absolute, size_t capacity);
int sysfs_special_kind_result(long client_ops);
int sysfs_string_nbits_result(size_t len);
int sysfs_response_error_result(ssize_t ssize);
int sysfs_param_sizes_valid_result(size_t create_size, size_t mkdir_size,
				   size_t symlink_size, size_t lookup_size,
				   size_t unlink_size, size_t setup_size);
size_t sysfs_data_bufsize_result(void);
int sysfs_packet_error_result(int send_error, int packet_error);
int sysfs_request_busy_result(int busy);
int sysfs_handle_pointer_valid_result(uintptr_t handlep);
ssize_t sysfs_default_response_ssize_result(void);
int sysfs_release_response_error_result(void);
int sysfs_request_handler_kind_result(int msg);
int sysfs_pointer_missing_result(uintptr_t ptr);
int sysfs_should_call_show_result(uintptr_t show);
int sysfs_should_call_store_result(uintptr_t store);
int sysfs_should_call_release_result(uintptr_t release);

unsigned long procfs_mem_reason_result(int readwrite);
int procfs_mem_chunk_size_result(unsigned long offset, unsigned long left);
int procfs_pagemap_range_result(unsigned long offset, int count,
				unsigned long *startp, unsigned long *endp);
int procfs_status_state_result(int status);
char procfs_thread_stat_state_result(int status, int in_syscall_offload);
int procfs_default_count_result(void);
int procfs_remote_count_result(unsigned long mapped_addr, int count);
int procfs_remote_npages_result(int count);
int procfs_format_error_result(int ans, int count);
unsigned long procfs_locked_kb_result(unsigned long lockedsize);
char procfs_maps_read_char_result(unsigned long flags);
char procfs_maps_write_char_result(unsigned long flags);
char procfs_maps_exec_char_result(unsigned long flags);
char procfs_maps_private_char_result(unsigned long flags);
int procfs_maps_path_kind_result(unsigned long range_start,
				 unsigned long range_end,
				 unsigned long range_flags,
				 unsigned long vdso_addr,
				 unsigned long vvar_addr,
				 unsigned long brk_start,
				 unsigned long brk_end_allocated);
unsigned long procfs_pagemap_next_result(unsigned long start);
unsigned int procfs_auxv_limit_result(void);
int procfs_is_release_result(int msg);
int procfs_root_matched_result(int sscanf_ret);
int procfs_osnum_match_result(int osnum, int requested_osnum);
int procfs_zero_length_result(unsigned long left);
unsigned long procfs_locked_size_add_result(unsigned long lockedsize,
					    unsigned long range_start,
					    unsigned long range_end,
					    unsigned long flags);
int procfs_bitmask_next_offset_result(int offset, int written);
int procfs_pbuf_is_empty_result(unsigned long pbuf);
int procfs_backlog_needed_result(uintptr_t resultp);
int procfs_lock_failed_action_result(uintptr_t resultp);
int procfs_lock_retry_result(void);
int procfs_thread_tid_result(int task_match, int parsed_tid, int pid);
int procfs_task_missing_terminal_result(int task_match);
int procfs_pointer_present_result(uintptr_t ptr);
int procfs_buffer_chain_attach_result(unsigned long pbuf, uintptr_t buf_top);
int procfs_entry_kind_result(const char *name);
uintptr_t procfs_comm_basename_result(uintptr_t saved_cmdline);

int pager_linux_io_retry_result(ssize_t ret);
int pager_linux_io_stop_result(ssize_t ret);
int pager_linux_io_first_result(ssize_t done);
ssize_t pager_linux_io_advance_result(ssize_t done, ssize_t ret);
size_t pager_linux_io_remaining_result(size_t remaining, ssize_t ret);
uintptr_t pager_linux_io_next_buf_result(uintptr_t buf, ssize_t ret);
int pager_linux_io_complete_result(ssize_t done, size_t target);
int pager_copy_fault_retry_result(int faulted);
int pager_copy_fault_error_result(int ret);
int pager_myalloc_fits_result(size_t allocated, size_t request, size_t size);
size_t pager_myalloc_next_alloced_result(size_t allocated, size_t request);
int pager_copy_size_error_result(size_t size);
unsigned long pager_fault_addr_result(unsigned long addr);
size_t pager_read_chunk_size_result(size_t off, size_t size);
int pager_arealist_tail_room_result(int tail_count);
int pager_arealist_count_add_result(int count, int add);
ssize_t pager_addrpair_size_result(unsigned long start, unsigned long end);
ssize_t pager_file_pos_result(ssize_t off, ssize_t total_size);
ssize_t pager_arealist_write_result(ssize_t written, int count,
				    size_t entry_size);
int pager_mlock_more_result(unsigned long start);
unsigned long pager_mlock_next_start_result(unsigned long end);
int pager_mlock_container_empty_result(uintptr_t from, uintptr_t tail,
				       int ccount, int tail_count);
int pager_mlock_needs_next_result(int ccount, int cur_count);
int pager_mlock_reset_count_result(void);
int pager_mlock_next_count_result(int count);
ssize_t pager_pagein_data_pos_result(unsigned int swap_count,
				     unsigned int mlock_count,
				     size_t header_size, size_t area_size);
int pager_pageout_args_result(uintptr_t fname, uintptr_t buf, size_t size,
			      unsigned long user_start, unsigned long user_end);
int pager_skip_anon_range_result(int has_memobj, unsigned long start,
				 unsigned long text_start,
				 unsigned long stack_start,
				 unsigned long user_start,
				 unsigned long user_end,
				 unsigned long flags);
int pager_range_locked_result(unsigned long flags);
int pager_skip_physical_removal_result(int flags);
int pager_fd_valid_result(int fd);
int pager_should_unlink_swap_result(long result);
long pager_io_short_result(long result);

int zeroobj_initial_flags_result(void);
int zeroobj_initial_refcnt_result(void);
int zeroobj_initial_page_mode_result(void);
off_t zeroobj_initial_page_offset_result(void);
int zeroobj_get_page_validate_result(off_t off, int p2align, int has_page);

int shmobj_init_pgshift_result(int init_pgshift);
size_t shmobj_pgsize_result(int pgshift);
int shmobj_initial_flags_result(void);
int shmobj_indexed_flags_result(int flags);
size_t shmobj_real_segsz_result(size_t segsz, size_t pgsize);
int shmobj_page_contains_offset_result(off_t page_offset, int pgshift,
				       off_t off);
int shmobj_destroy_page_npages_result(int pgshift);
size_t shmobj_destroy_page_size_result(int pgshift);
int shmobj_destroy_index_word_result(int index);
unsigned long shmobj_destroy_index_mask_result(int index);
int shmlock_user_locked_result(size_t locked);
int shmlock_user_match_result(int user_ruid, int ruid);
int shmlock_user_is_list_head_result(uintptr_t chain, uintptr_t head);
size_t shmlock_user_after_unlock_result(size_t locked, size_t size);
int shmlock_user_should_free_result(size_t locked);
int shmobj_has_user_result(uintptr_t user);
int shmobj_destroy_page_count_invalid_result(int count);
int shmobj_destroy_page_should_free_result(int count, int page_unmap_result);
int shmobj_should_free_direct_result(int index);
int shmobj_destroy_missing_flag_result(int mode);
int shmobj_initial_refcnt_result(void);
int shmobj_initial_index_result(void);
int shmobj_initial_ds_pgshift_result(void);
int shmobj_get_page_validate_result(size_t real_segsz, off_t off,
				    int p2align);
int shmobj_lookup_page_validate_result(size_t real_segsz, off_t off);
int shmobj_page_npages_result(int p2align);
int shmobj_page_pgshift_result(int p2align);
int shmobj_need_alloc_page_result(uintptr_t page);
int shmobj_new_page_mode_result(void);
int shmobj_new_page_count_result(void);
long shmobj_new_page_mapped_result(void);
int shmobj_page_mode_valid_for_new_result(int mode);
int shmobj_lookup_page_missing_error_result(uintptr_t page);
int shmobj_lookup_should_store_phys_result(uintptr_t physp);
int shmobj_update_args_result(int has_pt, int has_orig_page, int has_vaddr);
size_t shmobj_update_orig_pgsize_result(int pgshift);
uintptr_t shmobj_update_page_phys_result(uintptr_t base_phys, size_t page_off);
off_t shmobj_update_page_offset_result(off_t orig_offset, size_t page_off);
int shmobj_pte_missing_result(uintptr_t pte);
int shmobj_update_has_more_pages_result(size_t page_off, size_t orig_pgsize);
size_t shmobj_update_next_page_off_result(size_t page_off, size_t pte_size);

int hugefileobj_expected_p2align_result(int pgshift);
int hugefileobj_validate_p2align_result(int p2align, int pgshift);
off_t hugefileobj_page_index_result(off_t off, int pgshift);
int hugefileobj_npages_per_page_result(size_t pgsize);
size_t hugefileobj_pgsize_result(int pgshift);
int hugefileobj_initial_status_result(void);
int hugefileobj_initial_refcnt_result(void);
int hugefileobj_pointer_present_result(uintptr_t ptr);
int hugefileobj_pointer_missing_result(uintptr_t ptr);
int hugefileobj_page_present_result(uintptr_t page);
size_t hugefileobj_page_array_bytes_result(size_t nr_pages);
int hugefileobj_create_nr_pages_result(off_t off, size_t len, int pgshift);
int hugefileobj_needs_grow_result(size_t current_nr_pages,
				  int needed_nr_pages);
size_t hugefileobj_copy_bytes_result(size_t current_nr_pages);
size_t hugefileobj_zero_bytes_result(size_t old_nr_pages,
				     size_t new_nr_pages);
size_t hugefileobj_zero_start_index_result(size_t old_nr_pages);

#endif /* MCKERNEL_OBJECT_HELPERS_H */
