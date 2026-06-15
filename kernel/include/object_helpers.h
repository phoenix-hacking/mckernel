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

#define SYSFS_REQUEST_PHASE_NONE 0
#define SYSFS_REQUEST_PHASE_SEND 1
#define SYSFS_REQUEST_PHASE_RESPONSE 2

#define SYSFS_INIT_STAGE_NONE 0
#define SYSFS_INIT_STAGE_SIZE 1
#define SYSFS_INIT_STAGE_DATA_ALLOC 2
#define SYSFS_INIT_STAGE_PARAM_ALLOC 3
#define SYSFS_INIT_STAGE_REQUEST 4

#define SYSFS_REQUEST_LOG_SEND_ERROR 1
#define SYSFS_REQUEST_LOG_RESPONSE_ERROR 2

#define SYSFSS_REQ_LOG_CALLBACK_ERROR 1
#define SYSFSS_REQ_LOG_SEND_ERROR 2
#define SYSFSS_REQ_LOG_PACKET_ERROR 3
#define SYSFSS_REQ_LOG_DEBUG 4

#define PROCFS_STATUS_RUNNING 0
#define PROCFS_STATUS_STOPPED 1
#define PROCFS_STATUS_TRACED 2
#define PROCFS_STATUS_EXITED 3

#define PROCFS_MAPS_PATH_NONE 0
#define PROCFS_MAPS_PATH_VDSO 1
#define PROCFS_MAPS_PATH_VVAR 2
#define PROCFS_MAPS_PATH_STACK 3
#define PROCFS_MAPS_PATH_HEAP 4

#define HUGEFILEOBJ_LOG_GET_ALLOC_ERROR 1
#define HUGEFILEOBJ_LOG_GET_ALLOCATED 2
#define HUGEFILEOBJ_LOG_FREE_PAGE 3
#define HUGEFILEOBJ_LOG_CREATE_ARRAY 4
#define HUGEFILEOBJ_LOG_GET_P2ALIGN_ERROR 5
#define HUGEFILEOBJ_LOG_PRE_CREATE_FOUND 6
#define HUGEFILEOBJ_LOG_PRE_CREATE_CREATED 7
#define HUGEFILEOBJ_PRE_CREATE_ALLOC_OBJ 1
#define HUGEFILEOBJ_PRE_CREATE_ALLOC_PATH 2

#define ZEROOBJ_LOG_ALREADY 1
#define ZEROOBJ_LOG_KMALLOC_FAILED 2
#define ZEROOBJ_LOG_ALLOC_PAGES_FAILED 3

#define FILEOBJ_LOG_FLUSH_MISSING_PAGE 1
#define FILEOBJ_LOG_FLUSH_SHORT_WRITE 2
#define FILEOBJ_LOG_INVALIDATE_UNSUPPORTED 3
#define FILEOBJ_LOG_PAGEIO_SCHEDULE 4
#define FILEOBJ_LOG_PAGEIO_EOF 5
#define FILEOBJ_LOG_PAGEIO_READ_ERROR 6
#define FILEOBJ_LOG_FREE_INVALID_COUNT 7
#define FILEOBJ_LOG_FREE_RSS_SUB 8
#define FILEOBJ_LOG_FREE_RELEASE_ERROR 9
#define FILEOBJ_LOG_FREE_DONE 10
#define FILEOBJ_CREATE_LOG_PATH_ALLOC_FAILED 11
#define FILEOBJ_CREATE_LOG_PREMAP_START 12
#define FILEOBJ_CREATE_LOG_PREMAP_ARRAY_ALLOC_FAILED 13
#define FILEOBJ_CREATE_LOG_PREMAP_PAGE_ALLOC_FAILED 14
#define FILEOBJ_CREATE_LOG_PREMAP_RSS_ADD 15
#define FILEOBJ_CREATE_LOG_PREMAP_INTERLEAVED_DONE 16
#define FILEOBJ_GET_LOG_PREMAP_ALLOC_FAILED 17
#define FILEOBJ_GET_LOG_PREMAP_ALLOCATED 18
#define FILEOBJ_GET_LOG_PREMAP_RSS_ADD 19
#define FILEOBJ_GET_LOG_PREMAP_RESOLVED 20
#define FILEOBJ_GET_LOG_KMALLOC_FAILED 21
#define FILEOBJ_GET_LOG_ALLOC_FAILED 22
#define FILEOBJ_GET_LOG_NEW_PAGE 23
#define FILEOBJ_GET_LOG_MAP_DONE 24
#define FILEOBJ_GET_LOG_USE_PAGE 25
#define FILEOBJ_GET_LOG_RETURN 26

#define SHMOBJ_LOG_LOOKUP_INVALID 1
#define SHMOBJ_LOG_LOOKUP_RANGE 2
#define SHMOBJ_LOG_LOOKUP_MISSING 3
#define SHMOBJ_LOG_UPDATE_INVALID 4
#define SHMOBJ_LOG_UPDATE_PTE_MISSING 5
#define SHMOBJ_LOG_GET_INVALID 6
#define SHMOBJ_LOG_GET_RANGE 7
#define SHMOBJ_LOG_GET_TOO_LARGE 8
#define SHMOBJ_LOG_GET_ALLOC_FAILED 9
#define SHMOBJ_LOG_GET_PAGE_INVALID 10
#define SHMOBJ_LOG_GET_ALLOCATED 11
#define SHMOBJ_LOG_DESTROY_PAGE_COUNT_INVALID 12
#define SHMOBJ_LOG_DESTROY_RSS_SUB 13
#define SHMOBJ_LOG_FREE_MISSING_DEST 14
#define SHMOBJ_LOG_CREATE_ALLOC_FAILED 15

#define DEVOBJ_LOG_RELEASE_FAILED 1
#define DEVOBJ_LOG_FREE_DONE 2
#define DEVOBJ_LOG_OUT_OF_RANGE 3
#define DEVOBJ_LOG_FETCH_FAILED 4
#define DEVOBJ_LOG_NOT_PRESENT 5

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
typedef void *(*fileobj_phys_to_page_fn_t)(uintptr_t phys);
typedef off_t (*fileobj_page_offset_fn_t)(void *page);
typedef ssize_t (*fileobj_write_fn_t)(uintptr_t handle, off_t offset,
				      size_t pgsize, uintptr_t phys);
typedef void (*fileobj_log_fn_t)(int event, void *memobj, void *obj,
				 uintptr_t phys, size_t pgsize,
				 ssize_t result);
typedef void (*fileobj_lock_fn_t)(void *lock, void *node);
typedef void (*fileobj_unlock_fn_t)(void *lock, void *node);
typedef void *(*fileobj_lookup_fn_t)(void *obj, int hash, off_t off);
typedef uintptr_t (*fileobj_page_phys_fn_t)(void *page);
typedef void *(*fileobj_list_first_fn_t)(void *head);
typedef void *(*fileobj_list_next_fn_t)(void *head, void *obj);
typedef uintptr_t (*fileobj_handle_fn_t)(void *obj);
typedef int (*fileobj_ref_fn_t)(void *obj);
typedef void (*fileobj_dec_fn_t)(void *obj);
typedef int (*fileobj_page_mode_fn_t)(void *page);
typedef void (*fileobj_page_set_mode_fn_t)(void *page, int mode);
typedef void (*fileobj_pageio_zero_fn_t)(uintptr_t phys);
typedef ssize_t (*fileobj_pageio_read_fn_t)(uintptr_t handle, off_t off,
					    size_t pgsize, uintptr_t phys);
typedef void (*fileobj_void_fn_t)(void);
typedef void (*fileobj_pageio_log_fn_t)(int event, void *obj, off_t off,
					size_t pgsize, long value);
typedef void (*fileobj_pageio_panic_fn_t)(void *obj, off_t off,
					  size_t pgsize, int mode);
typedef void (*fileobj_ptr_void_fn_t)(void *ptr);
typedef void *(*fileobj_ptr_result_fn_t)(void *ptr);
typedef void *(*fileobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef void (*fileobj_copy_fn_t)(void *dst, const void *src, size_t len);
typedef void (*fileobj_ptr_set_fn_t)(void *ptr, void *value);
typedef void (*fileobj_size_set_fn_t)(void *ptr, size_t value);
typedef int (*fileobj_int_get_fn_t)(void *ptr);
typedef void (*fileobj_int_set_fn_t)(void *ptr, int value);
typedef unsigned long (*fileobj_ulong_get_fn_t)(void *ptr);
typedef void (*fileobj_ulong_set_fn_t)(void *ptr, unsigned long value);
typedef void (*fileobj_create_log_fn_t)(int event, void *obj,
					const void *path, long value);
typedef void (*fileobj_memzero_fn_t)(void *ptr, size_t len);
typedef void *(*fileobj_alloc_pages_node_fn_t)(int npages, int p2align,
					       unsigned long flags, int node,
					       uintptr_t virt_addr);
typedef void *(*fileobj_alloc_pages_fn_t)(int npages, unsigned long flags,
					  uintptr_t virt_addr);
typedef void (*fileobj_page_array_set_fn_t)(void *pages, int index,
					    void *page);
typedef void *(*fileobj_page_array_cmpxchg_fn_t)(void *pages, int index,
						 void *old, void *new_value);
typedef void (*fileobj_rss_add_fn_t)(size_t size, size_t pgsize);
typedef void (*fileobj_create_premap_log_fn_t)(int event, void *obj,
					       void *page, long value);
typedef void (*fileobj_get_log_fn_t)(int event, void *obj, off_t off,
				     int p2align, uintptr_t virt_addr,
				     uintptr_t physp_addr, void *page,
				     uintptr_t phys, long value);
typedef uintptr_t (*fileobj_ptr_phys_fn_t)(void *ptr);
typedef void *(*fileobj_phys_to_page_insert_fn_t)(uintptr_t phys);
typedef void (*fileobj_page_offset_set_fn_t)(void *page, off_t off);
typedef void (*fileobj_long_set_fn_t)(void *page, long value);
typedef void (*fileobj_page_hash_insert_fn_t)(void *obj, void *page,
					      int hash);
typedef void (*fileobj_pageio_args_set_fn_t)(void *args, void *obj,
					     off_t off, size_t pgsize);
typedef void (*fileobj_pgio_set_fn_t)(void *thread, void *pageio_fn,
				      void *args);
typedef void (*fileobj_get_regular_log_fn_t)(int event, void *obj, off_t off,
					     int p2align, uintptr_t virt_addr,
					     uintptr_t physp_addr, void *page,
					     uintptr_t phys, uintptr_t value,
					     size_t size, int mode, int count);
typedef void (*fileobj_get_regular_panic_fn_t)(void *obj, off_t off,
					       void *page, int mode);
typedef void *(*fileobj_phys_to_virt_fn_t)(uintptr_t phys);
typedef int (*fileobj_int_fn_t)(void *ptr);
typedef void (*fileobj_free_pages_fn_t)(void *addr, int npages);
typedef void (*fileobj_rss_sub_fn_t)(size_t size, size_t pgsize);
typedef int (*fileobj_release_fn_t)(uintptr_t handle, unsigned long sref);
typedef void *(*fileobj_page_array_at_fn_t)(void *pages, int index);
typedef void (*fileobj_free_log_fn_t)(int event, void *obj, void *page,
				      uintptr_t phys, long value,
				      unsigned long flags);
int fileobj_flush_page_body_result(
	void *memobj, void *obj, int flags, uintptr_t handle, uintptr_t phys,
	size_t pgsize, fileobj_phys_to_page_fn_t phys_to_page_fn,
	fileobj_page_offset_fn_t page_offset_fn, fileobj_write_fn_t write_fn,
	fileobj_log_fn_t log_fn);
int fileobj_invalidate_page_body_result(void *memobj, uintptr_t phys,
					size_t pgsize,
					fileobj_log_fn_t log_fn);
int fileobj_lookup_page_body_result(
	void *obj, off_t off, int p2align, uintptr_t *physp, void *lock,
	void *lock_node, fileobj_lock_fn_t lock_fn,
	fileobj_unlock_fn_t unlock_fn, fileobj_lookup_fn_t lookup_fn,
	fileobj_page_phys_fn_t page_phys_fn);
void *fileobj_obj_list_lookup_body_result(
	uintptr_t handle, void *list_head,
	fileobj_list_first_fn_t first_fn,
	fileobj_list_next_fn_t next_fn,
	fileobj_handle_fn_t handle_fn,
	fileobj_ref_fn_t ref_fn,
	fileobj_dec_fn_t dec_fn);
int fileobj_create_publish_body_result(
	void *obj, int is_new, int mmap_flags, int pager_flags,
	size_t result_size, fileobj_ptr_void_fn_t list_insert_fn,
	fileobj_size_set_fn_t size_set_fn,
	fileobj_int_set_fn_t flags_set_fn,
	fileobj_int_set_fn_t status_set_fn,
	fileobj_int_set_fn_t refcnt_set_fn,
	fileobj_ulong_get_fn_t sref_get_fn,
	fileobj_ulong_set_fn_t sref_set_fn);
int fileobj_create_path_body_result(
	void *obj, int path_first, const void *path_src, size_t path_len,
	unsigned long alloc_flags, fileobj_alloc_fn_t alloc_fn,
	fileobj_copy_fn_t copy_fn, fileobj_ptr_set_fn_t path_set_fn,
	fileobj_create_log_fn_t log_fn);
int fileobj_create_premap_body_result(
	void *obj, int flags, size_t result_size, unsigned long mpol_flags,
	int nr_numa_nodes, uintptr_t virt_addr, unsigned long alloc_flags,
	fileobj_alloc_fn_t alloc_fn, fileobj_ptr_set_fn_t pages_set_fn,
	fileobj_int_set_fn_t nr_pages_set_fn,
	fileobj_memzero_fn_t zero_fn,
	fileobj_alloc_pages_node_fn_t alloc_pages_node_fn,
	fileobj_page_array_set_fn_t page_set_fn,
	fileobj_rss_add_fn_t rss_add_fn,
	fileobj_create_premap_log_fn_t log_fn);
int fileobj_get_premap_body_result(
	void *obj, void *pages, off_t off, int p2align, uintptr_t virt_addr,
	uintptr_t *physp, unsigned long alloc_flags,
	fileobj_alloc_pages_fn_t alloc_pages_fn,
	fileobj_memzero_fn_t zero_fn,
	fileobj_page_array_at_fn_t page_at_fn,
	fileobj_page_array_cmpxchg_fn_t cmpxchg_fn,
	fileobj_free_pages_fn_t free_pages_fn,
	fileobj_ptr_phys_fn_t phys_fn,
	fileobj_rss_add_fn_t rss_add_fn,
	fileobj_get_log_fn_t log_fn);
int fileobj_get_regular_body_result(
	void *obj, int flags, off_t off, int p2align, uintptr_t virt_addr,
	uintptr_t *physp, void *thread, void *pageio_fn, void *lock,
	void *lock_node, size_t args_size, unsigned long args_alloc_flags,
	fileobj_lock_fn_t lock_fn, fileobj_unlock_fn_t unlock_fn,
	fileobj_lookup_fn_t lookup_fn, fileobj_alloc_fn_t alloc_fn,
	fileobj_ptr_void_fn_t free_fn, fileobj_alloc_pages_fn_t alloc_pages_fn,
	fileobj_ptr_phys_fn_t phys_fn,
	fileobj_phys_to_page_insert_fn_t page_insert_lookup_fn,
	fileobj_page_mode_fn_t page_mode_fn,
	fileobj_page_offset_set_fn_t page_offset_set_fn,
	fileobj_long_set_fn_t page_count_set_fn,
	fileobj_long_set_fn_t page_mapped_set_fn,
	fileobj_page_hash_insert_fn_t hash_insert_fn,
	fileobj_page_set_mode_fn_t page_mode_set_fn,
	fileobj_ref_fn_t memobj_ref_fn,
	fileobj_pageio_args_set_fn_t args_set_fn,
	fileobj_pgio_set_fn_t pgio_set_fn,
	fileobj_ptr_void_fn_t page_count_inc_fn,
	fileobj_page_phys_fn_t page_phys_fn,
	fileobj_int_fn_t page_count_fn,
	fileobj_ptr_void_fn_t page_remove_fn,
	fileobj_phys_to_virt_fn_t phys_to_virt_fn,
	fileobj_int_fn_t page_unmap_fn,
	fileobj_free_pages_fn_t free_pages_fn,
	fileobj_get_regular_log_fn_t log_fn,
	fileobj_get_regular_panic_fn_t panic_fn);
int fileobj_do_pageio_body_result(
	void *obj, int flags, uintptr_t handle, off_t off, size_t pgsize,
	void *lock, void *lock_node, fileobj_lock_fn_t lock_fn,
	fileobj_unlock_fn_t unlock_fn, fileobj_lookup_fn_t lookup_fn,
	fileobj_page_mode_fn_t page_mode_fn,
	fileobj_page_set_mode_fn_t page_set_mode_fn,
	fileobj_page_phys_fn_t page_phys_fn,
	fileobj_pageio_zero_fn_t zero_fn,
	fileobj_pageio_read_fn_t read_fn,
	fileobj_void_fn_t schedule_fn,
	fileobj_void_fn_t pause_fn,
	fileobj_pageio_log_fn_t log_fn,
	fileobj_pageio_panic_fn_t panic_fn);
int fileobj_free_body_result(
	void *obj, int flags, uintptr_t handle, unsigned long sref,
	void *pages, int nr_pages, void *path, void *list_lock,
	void *lock_node, fileobj_lock_fn_t lock_fn,
	fileobj_unlock_fn_t unlock_fn, fileobj_ptr_void_fn_t list_remove_fn,
	fileobj_ptr_result_fn_t page_first_fn,
	fileobj_ptr_void_fn_t page_remove_fn,
	fileobj_page_phys_fn_t page_phys_fn,
	fileobj_phys_to_virt_fn_t phys_to_virt_fn,
	fileobj_int_fn_t page_count_fn,
	fileobj_int_fn_t page_unmap_fn,
	fileobj_free_pages_fn_t free_pages_fn,
	fileobj_rss_sub_fn_t rss_sub_fn,
	fileobj_ptr_void_fn_t free_fn,
	fileobj_release_fn_t release_fn,
	fileobj_page_array_at_fn_t page_at_fn,
	fileobj_free_log_fn_t log_fn);

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
typedef int (*devobj_unmap_fn_t)(uintptr_t handle);
typedef void (*devobj_free_pages_fn_t)(void *addr, size_t npages);
typedef void (*devobj_free_fn_t)(void *addr);
typedef void (*devobj_log_fn_t)(int event, void *memobj, void *obj,
				off_t off, off_t pgoff, int p2align,
				int ix, int error, uintptr_t pfn);
typedef void (*devobj_profile_fn_t)(void);
typedef unsigned long (*devobj_lock_fn_t)(void *lock);
typedef void (*devobj_unlock_fn_t)(void *lock, unsigned long irqstate);
typedef uintptr_t (*devobj_pfn_load_fn_t)(void *obj, int ix);
typedef int (*devobj_fetch_pfn_fn_t)(void *memobj, void *obj,
				     uintptr_t handle, off_t off,
				     int p2align, uintptr_t *pfnp);
typedef int (*devobj_pfn_write_combined_fn_t)(uintptr_t pfn);
typedef uintptr_t (*devobj_map_memory_fn_t)(uintptr_t phys, size_t size);
typedef void (*devobj_pfn_store_fn_t)(void *obj, int ix, uintptr_t pfn);
int devobj_free_body_result(void *obj, void *path, void *pfn_table,
			    uintptr_t handle, size_t npages,
			    devobj_unmap_fn_t unmap_fn,
			    devobj_free_pages_fn_t free_pages_fn,
			    devobj_free_fn_t free_fn,
			    devobj_log_fn_t log_fn);
int devobj_get_page_body_result(
	void *memobj, void *obj, uintptr_t handle, off_t off, int p2align,
	off_t pfn_pgoff, size_t npages, void *pfn_table_lock,
	uintptr_t *physp, unsigned long *flagp, devobj_profile_fn_t profile_fn,
	devobj_lock_fn_t lock_fn, devobj_unlock_fn_t unlock_fn,
	devobj_pfn_load_fn_t pfn_load_fn, devobj_fetch_pfn_fn_t fetch_pfn_fn,
	devobj_pfn_write_combined_fn_t write_combined_fn,
	devobj_map_memory_fn_t map_memory_fn,
	devobj_pfn_store_fn_t pfn_store_fn,
	devobj_log_fn_t log_fn);

struct ikc_scd_packet;
typedef unsigned long (*procfs_thread_phys_fn_t)(void *addr);
typedef int (*procfs_thread_send_fn_t)(void *channel,
				       struct ikc_scd_packet *packet);
typedef void (*procfs_thread_pause_fn_t)(void);
int procfs_thread_ctl_result(void *channel, struct ikc_scd_packet *packet,
			     int *donep, int msg, int osnum, int cpu_id,
			     int pid, int tid,
			     procfs_thread_phys_fn_t phys_fn,
			     procfs_thread_send_fn_t send_fn,
			     procfs_thread_pause_fn_t pause_fn);
typedef void (*procfs_answer_send_fn_t)(void *channel,
					struct ikc_scd_packet *packet);
int procfs_answer_result(void *channel, struct ikc_scd_packet *request,
			 int err, procfs_answer_send_fn_t send_fn);
struct mckernel_procfs_buffer;
struct procfs_read;
typedef struct mckernel_procfs_buffer *(*procfs_buf_alloc_fn_t)(
		unsigned long *phys, long pos);
typedef void (*procfs_buf_free_top_fn_t)(
		struct mckernel_procfs_buffer *top);
typedef void *(*procfs_buf_copy_fn_t)(void *dst, const void *src,
				      size_t len);
typedef struct mckernel_procfs_buffer *(*procfs_buf_phys_to_virt_fn_t)(
		unsigned long phys);
typedef void (*procfs_buf_free_page_fn_t)(
		struct mckernel_procfs_buffer *pbuf);
typedef unsigned long (*procfs_buf_phys_fn_t)(
		struct mckernel_procfs_buffer *pbuf);
typedef void *(*procfs_buf_page_alloc_fn_t)(int npages,
					    unsigned long flags);
typedef int (*procfs_mem_page_fault_fn_t)(void *vm, unsigned long offset,
					  unsigned long reason);
typedef int (*procfs_mem_virt_to_phys_fn_t)(void *page_table,
					    unsigned long offset,
					    unsigned long *physp);
typedef int (*procfs_mem_is_memory_fn_t)(unsigned long start,
					 unsigned long end);
typedef void *(*procfs_mem_phys_to_virt_fn_t)(unsigned long phys);
typedef void *(*procfs_mem_copy_fn_t)(void *dst, const void *src, size_t len);
typedef unsigned long (*procfs_pagemap_value_fn_t)(void *page_table,
						   unsigned long addr);
typedef unsigned long (*procfs_range_ulong_fn_t)(void *range, int field);
typedef const char *(*procfs_range_path_fn_t)(void *range);
typedef void *(*procfs_range_next_fn_t)(void *vm, void *range);
typedef int (*procfs_backlog_fn_t)(void *arg);
typedef void *(*procfs_backlog_alloc_fn_t)(unsigned long size,
					   unsigned long flags);
typedef void (*procfs_backlog_copy_fn_t)(void *dst,
					 struct ikc_scd_packet *src,
					 unsigned long size);
typedef int (*procfs_backlog_add_fn_t)(procfs_backlog_fn_t backlog_fn,
				       void *arg);
typedef void (*procfs_backlog_free_fn_t)(void *arg);
int procfs_buf_release_result(unsigned long phys,
			      procfs_buf_phys_to_virt_fn_t phys_to_virt_fn,
			      procfs_buf_free_page_fn_t free_page_fn);
struct mckernel_procfs_buffer *procfs_buf_alloc_result(
		unsigned long *phys, long pos,
		procfs_buf_page_alloc_fn_t alloc_fn,
		procfs_buf_phys_fn_t phys_fn, unsigned long alloc_flags);
int procfs_buf_add_result(struct mckernel_procfs_buffer **top,
			  struct mckernel_procfs_buffer **cur,
			  const void *buf, int len,
			  procfs_buf_alloc_fn_t alloc_fn,
			  procfs_buf_free_top_fn_t free_top_fn,
			  procfs_buf_copy_fn_t copy_fn);
int procfs_release_request_result(struct procfs_read *request,
				  procfs_buf_phys_to_virt_fn_t phys_to_virt_fn,
				  procfs_buf_free_page_fn_t free_page_fn);
int procfs_finish_request_result(struct procfs_read *request, int ret, int eof,
				 struct mckernel_procfs_buffer *buf_top,
				 procfs_buf_phys_fn_t phys_fn);
int procfs_backlog_result(struct ikc_scd_packet *request,
			  procfs_backlog_fn_t backlog_fn,
			  procfs_backlog_alloc_fn_t alloc_fn,
			  procfs_backlog_copy_fn_t copy_fn,
			  procfs_backlog_add_fn_t add_fn,
			  procfs_backlog_free_fn_t free_fn,
			  unsigned long packet_size,
			  unsigned long alloc_flags);
int procfs_root_entry_body_result(int entry_kind, const char *version,
				  const char *buildid, int num_processors,
				  int count,
				  struct mckernel_procfs_buffer **top,
				  struct mckernel_procfs_buffer **cur,
				  procfs_buf_alloc_fn_t alloc_fn,
				  procfs_buf_free_top_fn_t free_top_fn,
				  procfs_buf_copy_fn_t copy_fn);
int procfs_pid_simple_entry_body_result(int entry_kind, const void *saved_auxv,
					const char *saved_cmdline,
					unsigned int saved_cmdline_len,
					const char *comm_fallback,
					struct mckernel_procfs_buffer **top,
					struct mckernel_procfs_buffer **cur,
					procfs_buf_alloc_fn_t alloc_fn,
					procfs_buf_free_top_fn_t free_top_fn,
					procfs_buf_copy_fn_t copy_fn);
int procfs_maps_body_result(void *vm, void *range, unsigned long vdso_addr,
			    unsigned long vvar_addr, unsigned long brk_start,
			    unsigned long brk_end_allocated, int count,
			    struct mckernel_procfs_buffer **top,
			    struct mckernel_procfs_buffer **cur,
			    procfs_buf_alloc_fn_t alloc_fn,
			    procfs_buf_free_top_fn_t free_top_fn,
			    procfs_buf_copy_fn_t copy_fn,
			    procfs_range_ulong_fn_t range_ulong_fn,
			    procfs_range_path_fn_t range_path_fn,
			    procfs_range_next_fn_t range_next_fn);
unsigned long procfs_locked_size_body_result(
		void *vm, void *range, procfs_range_ulong_fn_t range_ulong_fn,
		procfs_range_next_fn_t range_next_fn);
struct procfs_status_body_input {
	int pid;
	int ruid;
	int euid;
	int suid;
	int fsuid;
	int rgid;
	int egid;
	int sgid;
	int fsgid;
	int status;
	int nr_threads;
	unsigned long lockedsize;
	const char *cpu_bitmask;
	const char *cpu_list;
	const char *numa_bitmask;
	const char *numa_list;
};
int procfs_status_body_result(const struct procfs_status_body_input *input,
			      int count, struct mckernel_procfs_buffer **top,
			      struct mckernel_procfs_buffer **cur,
			      procfs_buf_alloc_fn_t alloc_fn,
			      procfs_buf_free_top_fn_t free_top_fn,
			      procfs_buf_copy_fn_t copy_fn);
struct procfs_stat_body_input {
	int tid;
	const char *comm;
	char state;
	int ppid;
	int pid;
	int nr_threads;
	int cpu_id;
};
int procfs_stat_body_result(const struct procfs_stat_body_input *input,
			    int count, struct mckernel_procfs_buffer **top,
			    struct mckernel_procfs_buffer **cur,
			    procfs_buf_alloc_fn_t alloc_fn,
			    procfs_buf_free_top_fn_t free_top_fn,
			    procfs_buf_copy_fn_t copy_fn);

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
int sysfss_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
				 int err, long arg1, long arg2);
int sysfs_request_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
					long arg1);
int sysfs_request_handler_kind_result(int msg);
int sysfs_pointer_missing_result(uintptr_t ptr);
int sysfs_should_call_show_result(uintptr_t show);
int sysfs_should_call_store_result(uintptr_t store);
int sysfs_should_call_release_result(uintptr_t release);
typedef ssize_t (*sysfss_show_fn_t)(void *ops, void *instance, void *buf,
				    size_t bufsize);
typedef ssize_t (*sysfss_store_fn_t)(void *ops, void *instance, void *buf,
				     size_t size);
typedef void (*sysfss_release_fn_t)(void *ops, void *instance);
typedef int (*sysfss_send_fn_t)(int msg, int err, long arg1, long arg2);
typedef void (*sysfss_packet_show_fn_t)(long nodeh, void *ops,
					void *instance);
typedef void (*sysfss_packet_store_fn_t)(long nodeh, void *ops,
					 void *instance, size_t size);
typedef void (*sysfss_packet_release_fn_t)(long nodeh, void *ops,
					   void *instance);
typedef void (*sysfss_packet_unknown_fn_t)(int msg, int error, long arg1,
					   long arg2, long arg3);
typedef void (*sysfss_req_log_fn_t)(int event, long nodeh, void *ops,
				    void *instance, size_t size, int error,
				    int packet_err, ssize_t ssize);
typedef int (*sysfs_request_send_fn_t)(int msg, long arg1);
typedef void (*sysfs_request_pause_fn_t)(void);
typedef void (*sysfs_request_barrier_fn_t)(void);
typedef void (*sysfs_request_log_fn_t)(int event, int msg, int error);
typedef void *(*sysfs_init_alloc_fn_t)(int npages, unsigned long flags);
typedef void (*sysfs_init_free_fn_t)(void *addr, int npages);
typedef long (*sysfs_init_phys_fn_t)(void *addr);
struct sysfs_req_create_param;
struct sysfs_bitmap_param;
int sysfs_setup_special_create_result(struct sysfs_req_create_param *param,
				      struct sysfs_bitmap_param *pbp,
				      sysfs_init_phys_fn_t phys_fn);
int sysfs_request_body_result(int msg, void *param, long param_rpa,
			      sysfs_request_send_fn_t send_fn,
			      sysfs_request_pause_fn_t pause_fn,
			      sysfs_request_barrier_fn_t barrier_fn,
			      long *handlep, int *phasep);
int sysfs_request_logged_result(int msg, void *param, long param_rpa,
				sysfs_request_send_fn_t send_fn,
				sysfs_request_pause_fn_t pause_fn,
				sysfs_request_barrier_fn_t barrier_fn,
				long *handle_dstp,
				sysfs_request_log_fn_t log_fn,
				int *phasep);
int sysfs_init_body_result(size_t create_size, size_t mkdir_size,
			   size_t symlink_size, size_t lookup_size,
			   size_t unlink_size, size_t setup_size,
			   void **data_bufp, size_t *data_bufsizep,
			   sysfs_init_alloc_fn_t alloc_fn,
			   sysfs_init_free_fn_t free_fn,
			   sysfs_init_phys_fn_t phys_fn,
			   sysfs_request_send_fn_t send_fn,
			   sysfs_request_pause_fn_t pause_fn,
			   sysfs_request_barrier_fn_t barrier_fn,
			   int *stagep, int *phasep);
int sysfss_req_show_body_result(long nodeh, void *ops, void *instance,
				void *data_buf, size_t data_bufsize,
				sysfss_show_fn_t show_fn,
				sysfss_send_fn_t send_fn, ssize_t *ssizep,
				int *packet_errp);
int sysfss_req_show_logged_result(long nodeh, void *ops, void *instance,
				  void *data_buf, size_t data_bufsize,
				  uintptr_t show, sysfss_show_fn_t show_fn,
				  sysfss_send_fn_t send_fn,
				  sysfss_req_log_fn_t log_fn,
				  ssize_t *ssizep, int *packet_errp);
int sysfss_req_store_body_result(long nodeh, void *ops, void *instance,
				 void *data_buf, size_t size,
				 sysfss_store_fn_t store_fn,
				 sysfss_send_fn_t send_fn, ssize_t *ssizep,
				 int *packet_errp);
int sysfss_req_store_logged_result(long nodeh, void *ops, void *instance,
				   void *data_buf, size_t size,
				   uintptr_t store, sysfss_store_fn_t store_fn,
				   sysfss_send_fn_t send_fn,
				   sysfss_req_log_fn_t log_fn,
				   ssize_t *ssizep, int *packet_errp);
int sysfss_req_release_body_result(long nodeh, void *ops, void *instance,
				   sysfss_release_fn_t release_fn,
				   sysfss_send_fn_t send_fn,
				   int *packet_errp);
int sysfss_req_release_logged_result(long nodeh, void *ops, void *instance,
				     uintptr_t release,
				     sysfss_release_fn_t release_fn,
				     sysfss_send_fn_t send_fn,
				     sysfss_req_log_fn_t log_fn,
				     int *packet_errp);
int sysfss_packet_handler_body_result(int msg, int error, long arg1,
				      long arg2, long arg3,
				      sysfss_packet_show_fn_t show_fn,
				      sysfss_packet_store_fn_t store_fn,
				      sysfss_packet_release_fn_t release_fn,
				      int *kindp);
int sysfss_packet_handler_logged_result(int msg, int error, long arg1,
					long arg2, long arg3,
					sysfss_packet_show_fn_t show_fn,
					sysfss_packet_store_fn_t store_fn,
					sysfss_packet_release_fn_t release_fn,
					sysfss_packet_unknown_fn_t unknown_fn,
					int *kindp);

unsigned long procfs_mem_reason_result(int readwrite);
int procfs_mem_chunk_size_result(unsigned long offset, unsigned long left);
int procfs_mem_copy_body_result(void *vm, void *page_table, void *buf,
				unsigned long offset, unsigned long count,
				int readwrite,
				procfs_mem_page_fault_fn_t page_fault_fn,
				procfs_mem_virt_to_phys_fn_t virt_to_phys_fn,
				procfs_mem_is_memory_fn_t is_memory_fn,
				procfs_mem_phys_to_virt_fn_t phys_to_virt_fn,
				procfs_mem_copy_fn_t copy_fn);
int procfs_pagemap_range_result(unsigned long offset, int count,
				unsigned long *startp, unsigned long *endp);
int procfs_pagemap_body_result(void *page_table, unsigned long *buf,
			       unsigned long start, unsigned long end, int count,
			       procfs_pagemap_value_fn_t value_fn);
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
#define PROCFS_RANGE_FIELD_START 1
#define PROCFS_RANGE_FIELD_END 2
#define PROCFS_RANGE_FIELD_FLAG 3
int procfs_maps_path_kind_result(unsigned long range_start,
				 unsigned long range_end,
				 unsigned long range_flags,
				 unsigned long vdso_addr,
				 unsigned long vvar_addr,
				 unsigned long brk_start,
				 unsigned long brk_end_allocated);
unsigned long procfs_pagemap_next_result(unsigned long start);
unsigned int procfs_auxv_limit_result(void);
unsigned int procfs_cmdline_limit_result(uintptr_t saved_cmdline,
					 unsigned int saved_cmdline_len);
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
uintptr_t procfs_comm_name_result(uintptr_t fallback, uintptr_t basename);

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
typedef void *(*zeroobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef void *(*zeroobj_page_alloc_fn_t)(int npages, unsigned long flags);
typedef void (*zeroobj_free_page_fn_t)(void *virt, int npages);
typedef void *(*zeroobj_memset_fn_t)(void *dst, int value, size_t len);
typedef uintptr_t (*zeroobj_phys_fn_t)(void *addr);
typedef void *(*zeroobj_page_insert_fn_t)(uintptr_t phys);
typedef int (*zeroobj_page_mode_fn_t)(void *page);
typedef void (*zeroobj_obj_init_fn_t)(void *obj, void *ops);
typedef void (*zeroobj_page_init_fn_t)(void *page);
typedef void (*zeroobj_page_list_insert_fn_t)(void *obj, void *page);
typedef void (*zeroobj_publish_fn_t)(void *obj);
typedef int (*zeroobj_alloc_singleton_fn_t)(void);
typedef void *(*zeroobj_get_singleton_fn_t)(void);
typedef void (*zeroobj_ref_fn_t)(void *memobj);
typedef void (*zeroobj_void_fn_t)(void *arg);
typedef void (*zeroobj_log_fn_t)(int event, int error, void *obj,
				 void *page, uintptr_t phys);
int zeroobj_alloc_body_result(
	void *existing_obj, size_t obj_size, void *ops, void *lock,
	zeroobj_log_fn_t log_fn, zeroobj_void_fn_t lock_fn,
	zeroobj_void_fn_t unlock_fn, zeroobj_alloc_fn_t alloc_fn,
	zeroobj_void_fn_t free_fn, zeroobj_memset_fn_t memset_fn,
	zeroobj_obj_init_fn_t obj_init_fn,
	zeroobj_page_alloc_fn_t page_alloc_fn,
	zeroobj_free_page_fn_t page_free_fn,
	zeroobj_phys_fn_t phys_fn,
	zeroobj_page_insert_fn_t page_insert_fn,
	zeroobj_page_mode_fn_t page_mode_fn,
	zeroobj_void_fn_t duplicate_page_fn,
	zeroobj_page_init_fn_t page_init_fn,
	zeroobj_page_list_insert_fn_t page_list_insert_fn,
	zeroobj_publish_fn_t publish_fn);
int zeroobj_create_body_result(void **objp, void *existing_obj,
			       zeroobj_alloc_singleton_fn_t alloc_fn,
			       zeroobj_get_singleton_fn_t get_singleton_fn,
			       zeroobj_ref_fn_t ref_fn,
			       zeroobj_log_fn_t log_fn);
int zeroobj_get_page_body_result(void);

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
typedef void (*shmobj_ref_fn_t)(void *memobj);
typedef void (*shmobj_unref_fn_t)(void *memobj);
typedef void (*shmobj_page_list_lock_fn_t)(void *obj);
typedef void (*shmobj_page_list_unlock_fn_t)(void *obj);
typedef void *(*shmobj_page_lookup_fn_t)(void *obj, off_t off);
typedef uintptr_t (*shmobj_page_phys_fn_t)(void *page);
typedef void (*shmobj_lookup_log_fn_t)(int event, void *memobj,
				       off_t off, int p2align, void *physp,
				       int error, uintptr_t phys);
int shmobj_lookup_page_body_result(
	void *memobj, void *obj, size_t real_segsz, off_t off, int p2align,
	uintptr_t *physp, uintptr_t *resolved_physp, shmobj_ref_fn_t ref_fn,
	shmobj_unref_fn_t unref_fn, shmobj_page_list_lock_fn_t lock_fn,
	shmobj_page_list_unlock_fn_t unlock_fn,
	shmobj_page_lookup_fn_t lookup_fn, shmobj_page_phys_fn_t page_phys_fn,
	shmobj_lookup_log_fn_t log_fn);
int shmobj_update_args_result(int has_pt, int has_orig_page, int has_vaddr);
size_t shmobj_update_orig_pgsize_result(int pgshift);
uintptr_t shmobj_update_page_phys_result(uintptr_t base_phys, size_t page_off);
off_t shmobj_update_page_offset_result(off_t orig_offset, size_t page_off);
int shmobj_pte_missing_result(uintptr_t pte);
int shmobj_update_has_more_pages_result(size_t page_off, size_t orig_pgsize);
size_t shmobj_update_next_page_off_result(size_t page_off, size_t pte_size);
typedef void *(*shmobj_pte_lookup_fn_t)(void *pt, void *vaddr,
					size_t *pte_sizep, int *p2alignp);
typedef int (*shmobj_page_pgshift_fn_t)(void *page);
typedef void (*shmobj_page_set_pgshift_fn_t)(void *page, int pgshift);
typedef int (*shmobj_page_mode_fn_t)(void *page);
typedef void (*shmobj_page_set_mode_fn_t)(void *page, int mode);
typedef off_t (*shmobj_page_offset_fn_t)(void *page);
typedef void (*shmobj_page_set_offset_fn_t)(void *page, off_t offset);
typedef int (*shmobj_page_count_fn_t)(void *page);
typedef void (*shmobj_page_set_count_fn_t)(void *page, int count);
typedef long (*shmobj_page_mapped_fn_t)(void *page);
typedef void (*shmobj_page_set_mapped_fn_t)(void *page, long mapped);
typedef void *(*shmobj_page_insert_hash_fn_t)(uintptr_t phys);
typedef void (*shmobj_page_list_insert_fn_t)(void *obj, void *page);
typedef void (*shmobj_update_log_fn_t)(int event, void *memobj, void *pt,
				       void *orig_page, void *vaddr,
				       int error);
int shmobj_update_page_body_result(
	void *memobj, void *obj, void *pt, void *orig_page, void *vaddr,
	shmobj_ref_fn_t ref_fn, shmobj_unref_fn_t unref_fn,
	shmobj_page_phys_fn_t page_phys_fn,
	shmobj_pte_lookup_fn_t pte_lookup_fn,
	shmobj_page_pgshift_fn_t page_pgshift_fn,
	shmobj_page_set_pgshift_fn_t page_set_pgshift_fn,
	shmobj_page_mode_fn_t page_mode_fn,
	shmobj_page_set_mode_fn_t page_set_mode_fn,
	shmobj_page_offset_fn_t page_offset_fn,
	shmobj_page_set_offset_fn_t page_set_offset_fn,
	shmobj_page_count_fn_t page_count_fn,
	shmobj_page_set_count_fn_t page_set_count_fn,
	shmobj_page_mapped_fn_t page_mapped_fn,
	shmobj_page_set_mapped_fn_t page_set_mapped_fn,
	shmobj_page_insert_hash_fn_t page_insert_hash_fn,
	shmobj_page_list_insert_fn_t page_list_insert_fn,
	shmobj_update_log_fn_t log_fn);
typedef void *(*shmobj_alloc_page_fn_t)(int npages, int p2align,
					unsigned long flags,
					uintptr_t virt_addr);
typedef void (*shmobj_free_page_fn_t)(void *virt, int npages);
typedef uintptr_t (*shmobj_virt_to_phys_fn_t)(void *virt);
typedef void *(*shmobj_memset_fn_t)(void *dst, int value, size_t len);
typedef void (*shmobj_page_count_inc_fn_t)(void *page);
typedef void (*shmobj_panic_fn_t)(void);
typedef void (*shmobj_get_log_fn_t)(int event, void *memobj, off_t off,
				    int p2align, void *physp, int error,
				    void *page, uintptr_t phys);
int shmobj_get_page_body_result(
	void *memobj, void *obj, size_t real_segsz, off_t off, int p2align,
	uintptr_t *physp, uintptr_t virt_addr, shmobj_ref_fn_t ref_fn,
	shmobj_unref_fn_t unref_fn, shmobj_page_list_lock_fn_t lock_fn,
	shmobj_page_list_unlock_fn_t unlock_fn,
	shmobj_page_lookup_fn_t lookup_fn,
	shmobj_alloc_page_fn_t alloc_page_fn,
	shmobj_free_page_fn_t free_page_fn,
	shmobj_virt_to_phys_fn_t virt_to_phys_fn,
	shmobj_page_insert_hash_fn_t page_insert_hash_fn,
	shmobj_page_mode_fn_t page_mode_fn,
	shmobj_page_set_mode_fn_t page_set_mode_fn,
	shmobj_page_set_offset_fn_t page_set_offset_fn,
	shmobj_page_set_pgshift_fn_t page_set_pgshift_fn,
	shmobj_page_set_count_fn_t page_set_count_fn,
	shmobj_page_set_mapped_fn_t page_set_mapped_fn,
	shmobj_page_list_insert_fn_t page_list_insert_fn,
	shmobj_page_count_inc_fn_t page_count_inc_fn,
	shmobj_page_phys_fn_t page_phys_fn, shmobj_memset_fn_t memset_fn,
	shmobj_panic_fn_t panic_fn, shmobj_get_log_fn_t log_fn);
typedef void (*shmobj_user_clear_fn_t)(void *obj);
typedef size_t (*shmobj_user_locked_fn_t)(void *user);
typedef void (*shmobj_user_set_locked_fn_t)(void *user, size_t locked);
typedef void (*shmobj_user_free_fn_t)(void *user);
typedef void *(*shmobj_page_first_fn_t)(void *obj);
typedef void (*shmobj_page_remove_fn_t)(void *obj, void *page);
typedef void *(*shmobj_phys_to_virt_fn_t)(uintptr_t phys);
typedef int (*shmobj_page_unmap_fn_t)(void *page);
typedef void (*shmobj_rss_sub_fn_t)(size_t size, size_t pgsize);
typedef void (*shmobj_free_fn_t)(void *ptr);
typedef void (*shmobj_indexed_free_fn_t)(void *obj, int word,
					 unsigned long mask);
typedef void (*shmobj_destroy_log_fn_t)(int event, void *obj, void *page,
					uintptr_t phys, size_t size,
					size_t pgsize);
typedef void (*shmobj_destroy_fn_t)(void *obj);
typedef void (*shmobj_free_log_fn_t)(int event, void *memobj);
typedef void *(*shmobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef int (*shmobj_next_seq_fn_t)(void);
typedef void *(*shmobj_create_init_fn_t)(void *obj, void *ds, int pgshift,
					 size_t pgsize, size_t real_segsz,
					 int seq);
typedef void (*shmobj_create_log_fn_t)(int event, void *ds, void *objp,
				       int error);
typedef int (*shmobj_create_fn_t)(void *ds, void **objp);
typedef int (*shmobj_memobj_flags_fn_t)(void *memobj);
typedef void (*shmobj_memobj_set_flags_fn_t)(void *memobj, int flags);
typedef void *(*shmobj_to_shmobj_fn_t)(void *memobj);
typedef void *(*shmlock_user_first_fn_t)(void);
typedef void *(*shmlock_user_next_fn_t)(void *user);
typedef int (*shmlock_user_ruid_fn_t)(void *user);
typedef void (*shmlock_user_init_fn_t)(void *user, int ruid);
typedef void (*shmlock_user_list_fn_t)(void *user);
int shmobj_destroy_body_result(
	void *obj, void *user, size_t real_segsz, int index,
	shmobj_user_clear_fn_t user_clear_fn, shmobj_user_locked_fn_t user_locked_fn,
	shmobj_user_set_locked_fn_t user_set_locked_fn,
	shmobj_page_list_lock_fn_t users_lock_fn,
	shmobj_page_list_unlock_fn_t users_unlock_fn,
	shmobj_user_free_fn_t user_free_fn,
	shmobj_page_first_fn_t page_first_fn,
	shmobj_page_remove_fn_t page_remove_fn,
	shmobj_page_phys_fn_t page_phys_fn,
	shmobj_phys_to_virt_fn_t phys_to_virt_fn,
	shmobj_page_pgshift_fn_t page_pgshift_fn,
	shmobj_page_count_fn_t page_count_fn,
	shmobj_page_unmap_fn_t page_unmap_fn,
	shmobj_free_page_fn_t free_page_fn,
	shmobj_rss_sub_fn_t rss_sub_fn,
	shmobj_free_fn_t free_fn,
	shmobj_indexed_free_fn_t indexed_free_fn,
	shmobj_destroy_log_fn_t log_fn);
int shmobj_free_body_result(void *memobj, void *obj, int mode,
			    shmobj_page_list_lock_fn_t list_lock_fn,
			    shmobj_page_list_unlock_fn_t list_unlock_fn,
			    shmobj_destroy_fn_t destroy_fn,
			    shmobj_free_log_fn_t log_fn);
int shmobj_create_body_result(
	void *ds, void **objp, size_t segsz, int init_pgshift, size_t obj_size,
	shmobj_alloc_fn_t alloc_fn, shmobj_free_fn_t free_fn,
	shmobj_memset_fn_t memset_fn, shmobj_next_seq_fn_t next_seq_fn,
	shmobj_create_init_fn_t init_fn, shmobj_create_log_fn_t log_fn);
int shmobj_create_indexed_body_result(
	void *ds, void **objp, shmobj_create_fn_t create_fn,
	shmobj_memobj_flags_fn_t flags_fn,
	shmobj_memobj_set_flags_fn_t set_flags_fn,
	shmobj_to_shmobj_fn_t to_shmobj_fn);
int shmlock_user_free_body_result(
	void *user, shmobj_user_locked_fn_t user_locked_fn,
	shmlock_user_list_fn_t list_del_fn, shmobj_free_fn_t free_fn,
	shmobj_panic_fn_t panic_fn);
int shmlock_user_get_body_result(
	int ruid, void **userp, size_t user_size,
	shmlock_user_first_fn_t first_fn, shmlock_user_next_fn_t next_fn,
	shmlock_user_ruid_fn_t ruid_fn, shmobj_alloc_fn_t alloc_fn,
	shmlock_user_init_fn_t init_fn, shmlock_user_list_fn_t list_add_fn);

size_t gencore_align32_result(size_t value);
size_t gencore_alignpage_result(size_t value);
int gencore_range_inaccessible_result(unsigned long flags);
int gencore_prstatus_size_result(void);
int gencore_prpsinfo_size_result(void);
int gencore_auxv_size_result(void);
int gencore_fill_elf_header_body_result(void *eh, int segs);
typedef void (*gencore_arch_fill_prstatus_fn_t)(void *prstatus, void *thread,
						void *regs, int sig);
int gencore_fill_prstatus_body_result(
	void *head, void *thread, void *regs, int sig,
	gencore_arch_fill_prstatus_fn_t arch_fill_prstatus_fn);
int gencore_fill_prpsinfo_body_result(void *head, int status, int pid,
				      const char *cmdline);
int gencore_fill_auxv_body_result(void *head, const unsigned long *saved_auxv);
int gencore_fill_note_phdr_body_result(void *ph, unsigned long offset,
				       long notesize);
int gencore_fill_load_phdr_body_result(void *ph, unsigned long flags,
				       unsigned long offset,
				       unsigned long start,
				       unsigned long size);
int gencore_fill_initial_coretable_body_result(
	void *ct, unsigned long eh_phys, unsigned long ph_phys,
	unsigned long note_phys, long phsize, long alignednotesize);
typedef int (*gencore_pt_virt_to_phys_fn_t)(void *page_table,
					    unsigned long vaddr,
					    unsigned long *phys);
typedef unsigned long (*gencore_virt_to_phys_fn_t)(unsigned long vaddr);
typedef void (*gencore_coretable_log_fn_t)(int index, long len,
					   unsigned long addr,
					   unsigned long start);
typedef void *(*gencore_lookup_range_fn_t)(void *vm);
typedef void *(*gencore_next_range_fn_t)(void *vm, void *range);
typedef unsigned long (*gencore_range_ulong_fn_t)(void *range);
typedef long (*gencore_range_offset_fn_t)(void *range);
typedef void (*gencore_range_log_fn_t)(unsigned long start,
				       unsigned long end, unsigned long flags,
				       long objoff);
int gencore_count_range_chunks_body_result(
	unsigned long start, unsigned long end, unsigned long flags,
	void *page_table, int *chunks,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn);
int gencore_scan_ranges_for_counts_body_result(
	void *vm, void *page_table, int *chunks, int *segs,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn,
	gencore_range_offset_fn_t objoff_fn,
	gencore_range_log_fn_t log_fn,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn);
int gencore_fill_load_phdrs_body_result(
	void *vm, void *ph, int *indexp, unsigned long *offsetp,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn);
int gencore_emit_demand_coretable_body_result(
	void *ct, int *indexp, unsigned long start, unsigned long end,
	void *page_table, gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_coretable_log_fn_t log_fn);
int gencore_emit_linear_coretable_body_result(
	void *ct, int *indexp, unsigned long start, unsigned long end,
	unsigned long user_start, unsigned long user_end, void *page_table,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_virt_to_phys_fn_t virt_to_phys_fn,
	gencore_coretable_log_fn_t log_fn);
int gencore_emit_coretable_ranges_body_result(
	void *vm, void *ct, int *indexp, unsigned long user_start,
	unsigned long user_end, void *page_table, unsigned long *error_startp,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_virt_to_phys_fn_t virt_to_phys_fn,
	gencore_coretable_log_fn_t log_fn);
typedef void *(*gencore_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*gencore_free_fn_t)(void *ptr);
typedef void *(*gencore_alloc_fn_t)(size_t size, unsigned long flags);
typedef void (*gencore_zero_fn_t)(void *ptr, size_t size);
typedef int (*gencore_get_note_size_fn_t)(void *proc);
typedef void (*gencore_fill_note_fn_t)(void *note, void *proc,
				       char *cmdline, int sig);
typedef void (*gencore_alloc_error_log_fn_t)(int stage);
typedef void (*gencore_pt_error_log_fn_t)(unsigned long start, int error);
typedef void *(*gencore_first_thread_fn_t)(void *proc);
typedef void *(*gencore_next_thread_fn_t)(void *proc, void *thread);
typedef int (*gencore_thread_tid_fn_t)(void *thread);
typedef void *(*gencore_thread_regs_fn_t)(void *thread);
typedef int (*gencore_arch_thread_info_size_fn_t)(void);
typedef void (*gencore_fill_prstatus_note_fn_t)(void *note,
						void *thread, int sig);
typedef void (*gencore_arch_fill_thread_info_fn_t)(void *note,
						   void *thread, void *regs);
typedef void (*gencore_fill_proc_note_fn_t)(void *note, void *proc,
					    char *cmdline);
typedef void (*gencore_fill_auxv_note_fn_t)(void *note, void *proc);
int gencore_freecore_body_result(void **coretablep,
				 gencore_phys_to_virt_fn_t phys_to_virt_fn,
				 gencore_free_fn_t free_fn);
int gencore_generate_image_body_result(
	void *proc, void *vm, void *page_table, void **coretablep,
	int *chunks, int segs, unsigned long user_start,
	unsigned long user_end, char *cmdline, int sig,
	size_t eh_size, size_t phdr_size, size_t coretable_size,
	gencore_alloc_fn_t alloc_fn, gencore_zero_fn_t zero_fn,
	gencore_free_fn_t free_fn,
	gencore_get_note_size_fn_t get_note_size_fn,
	gencore_fill_note_fn_t fill_note_fn,
	gencore_virt_to_phys_fn_t virt_to_phys_fn,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_coretable_log_fn_t coretable_log_fn,
	gencore_alloc_error_log_fn_t alloc_error_log_fn,
	gencore_pt_error_log_fn_t pt_error_log_fn);
int gencore_note_size_threads_body_result(
	void *proc, int pid, gencore_first_thread_fn_t first_fn,
	gencore_next_thread_fn_t next_fn,
	gencore_thread_tid_fn_t tid_fn,
	gencore_arch_thread_info_size_fn_t arch_size_fn);
int gencore_fill_note_threads_body_result(
	void *note, void *proc, char *cmdline, int sig, int pid,
	void **end_notep, gencore_first_thread_fn_t first_fn,
	gencore_next_thread_fn_t next_fn,
	gencore_thread_tid_fn_t tid_fn,
	gencore_thread_regs_fn_t regs_fn,
	gencore_arch_thread_info_size_fn_t arch_size_fn,
	gencore_fill_prstatus_note_fn_t fill_prstatus_fn,
	gencore_arch_fill_thread_info_fn_t arch_fill_fn,
	gencore_fill_proc_note_fn_t fill_prpsinfo_fn,
	gencore_fill_auxv_note_fn_t fill_auxv_fn);

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
typedef void (*hugefileobj_void_fn_t)(void *arg);
typedef int (*hugefileobj_bool_fn_t)(void *arg);
typedef void *(*hugefileobj_first_fn_t)(void *arg);
typedef void *(*hugefileobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef void *(*hugefileobj_alloc_page_fn_t)(int npages, int p2align,
					     unsigned long flags,
					     uintptr_t virt_addr);
typedef void (*hugefileobj_free_page_fn_t)(void *page, int npages);
typedef void *(*hugefileobj_memcpy_fn_t)(void *dst, const void *src,
					 size_t len);
typedef void *(*hugefileobj_memset_fn_t)(void *dst, int value,
					 size_t len);
typedef uintptr_t (*hugefileobj_phys_fn_t)(void *addr);
typedef void *(*hugefileobj_page_at_fn_t)(void *obj, long index);
typedef void (*hugefileobj_set_page_fn_t)(void *obj, long index,
					  void *page);
typedef void *(*hugefileobj_lookup_fn_t)(uintptr_t handle);
typedef void *(*hugefileobj_to_memobj_fn_t)(void *obj);
typedef void *(*hugefileobj_next_fn_t)(void *head, void *obj);
typedef uintptr_t (*hugefileobj_handle_fn_t)(void *obj);
typedef int (*hugefileobj_ref_fn_t)(void *obj);
typedef void (*hugefileobj_set_handle_fn_t)(void *obj, uintptr_t handle);
typedef void (*hugefileobj_set_pgsize_fn_t)(void *obj, size_t pgsize);
typedef void (*hugefileobj_set_pgshift_fn_t)(void *obj, int pgshift);
typedef void (*hugefileobj_set_flags_fn_t)(void *obj, unsigned int flags);
typedef void (*hugefileobj_set_status_fn_t)(void *obj, int status);
typedef void (*hugefileobj_set_ops_fn_t)(void *obj, void *ops);
typedef void (*hugefileobj_set_refcnt_fn_t)(void *obj, int refcnt);
typedef void (*hugefileobj_set_path_fn_t)(void *obj, void *path);
typedef void (*hugefileobj_copy_path_fn_t)(void *dst, const void *src,
					   size_t len);
typedef void (*hugefileobj_dec_fn_t)(void *obj);
typedef void (*hugefileobj_pre_create_log_fn_t)(int event, void *obj);
typedef void (*hugefileobj_alloc_error_fn_t)(int stage);
typedef void (*hugefileobj_set_size_fn_t)(void *obj, size_t size);
typedef void (*hugefileobj_set_nr_pages_fn_t)(void *obj, size_t nr_pages);
typedef void (*hugefileobj_set_pages_fn_t)(void *obj, void *pages);
typedef void (*hugefileobj_log_fn_t)(int event, void *obj, off_t off,
				     long index, size_t pgsize,
				     uintptr_t virt_addr);
int hugefileobj_free_body_result(void *obj, void *lock,
				 hugefileobj_void_fn_t lock_fn,
				 hugefileobj_void_fn_t unlock_fn,
				 hugefileobj_void_fn_t list_del_fn,
				 hugefileobj_void_fn_t free_fn);
int hugefileobj_cleanup_body_result(void *lock, void *list_head,
				    hugefileobj_void_fn_t lock_fn,
				    hugefileobj_void_fn_t unlock_fn,
				    hugefileobj_bool_fn_t list_empty_fn,
				    hugefileobj_first_fn_t first_fn,
				    hugefileobj_void_fn_t list_del_fn,
				    hugefileobj_void_fn_t free_fn);
int hugefileobj_inner_free_body_result(
	void *obj, void *lock, void *path, void *pages, size_t nr_pages,
	size_t pgsize, hugefileobj_void_fn_t lock_fn,
	hugefileobj_void_fn_t unlock_fn, hugefileobj_void_fn_t free_fn,
	hugefileobj_free_page_fn_t free_page_fn,
	hugefileobj_page_at_fn_t page_at_fn,
	hugefileobj_void_fn_t clear_path_fn,
	hugefileobj_log_fn_t log_fn);
int hugefileobj_get_page_body_result(
	void *obj, void *lock, off_t off, int p2align, int pgshift,
	size_t pgsize, uintptr_t virt_addr, uintptr_t *physp,
	hugefileobj_void_fn_t lock_fn, hugefileobj_void_fn_t unlock_fn,
	hugefileobj_page_at_fn_t page_at_fn,
	hugefileobj_set_page_fn_t set_page_fn,
	hugefileobj_alloc_page_fn_t alloc_page_fn,
	hugefileobj_memset_fn_t memset_fn, hugefileobj_phys_fn_t phys_fn,
	hugefileobj_log_fn_t log_fn);
int hugefileobj_create_body_result(
	void *obj, void *lock, size_t len, off_t off, int pgshift,
	size_t pgsize, size_t current_nr_pages, void *current_pages,
	int *pgshiftp, uintptr_t virt_addr, unsigned long alloc_flags,
	hugefileobj_void_fn_t lock_fn, hugefileobj_void_fn_t unlock_fn,
	hugefileobj_alloc_fn_t alloc_fn, hugefileobj_void_fn_t free_fn,
	hugefileobj_memcpy_fn_t memcpy_fn,
	hugefileobj_memset_fn_t memset_fn,
	hugefileobj_set_nr_pages_fn_t set_nr_pages_fn,
	hugefileobj_set_pages_fn_t set_pages_fn,
	hugefileobj_set_size_fn_t set_size_fn,
	hugefileobj_log_fn_t log_fn);
int hugefileobj_pre_create_body_result(
	void *lock, uintptr_t handle, int maxprot, unsigned int flags,
	int pgshift, const char *path, size_t obj_size, size_t path_size,
	void *ops, void **objp, int *maxprotp,
	hugefileobj_void_fn_t lock_fn,
	hugefileobj_void_fn_t unlock_fn,
	hugefileobj_lookup_fn_t lookup_fn,
	hugefileobj_alloc_fn_t alloc_fn,
	hugefileobj_void_fn_t free_fn,
	hugefileobj_to_memobj_fn_t to_memobj_fn,
	hugefileobj_set_handle_fn_t set_handle_fn,
	hugefileobj_set_pgsize_fn_t set_pgsize_fn,
	hugefileobj_set_pgshift_fn_t set_pgshift_fn,
	hugefileobj_set_pages_fn_t set_pages_fn,
	hugefileobj_set_nr_pages_fn_t set_nr_pages_fn,
	hugefileobj_void_fn_t init_lock_fn,
	hugefileobj_set_flags_fn_t set_flags_fn,
	hugefileobj_set_status_fn_t set_status_fn,
	hugefileobj_set_ops_fn_t set_ops_fn,
	hugefileobj_set_refcnt_fn_t set_refcnt_fn,
	hugefileobj_set_path_fn_t set_path_fn,
	hugefileobj_copy_path_fn_t copy_path_fn,
	hugefileobj_void_fn_t list_add_fn,
	hugefileobj_pre_create_log_fn_t log_fn,
	hugefileobj_alloc_error_fn_t alloc_error_fn);
void *hugefileobj_lookup_body_result(
	uintptr_t handle, void *list_head,
	hugefileobj_first_fn_t first_fn,
	hugefileobj_next_fn_t next_fn,
	hugefileobj_handle_fn_t handle_fn,
	hugefileobj_ref_fn_t ref_fn,
	hugefileobj_dec_fn_t dec_fn);

#endif /* MCKERNEL_OBJECT_HELPERS_H */
