/* SPDX-License-Identifier: GPL-2.0 */
#ifndef HEADER_X86_MEMORY_HELPERS_H
#define HEADER_X86_MEMORY_HELPERS_H

#include <ihk/types.h>

struct ikc_scd_packet;

#define X86_VISIT_PTE_SKIP		0
#define X86_VISIT_PTE_DIRECT		1
#define X86_VISIT_PTE_ALLOC_AND_WALK	2
#define X86_VISIT_PTE_WALK		3
#define X86_VISIT_PTE_SPLIT_ERROR	4
#define X86_VISIT_PTE_LOG_SPLIT	1

#define X86_CLEAR_RANGE_SKIP		0
#define X86_CLEAR_RANGE_SPLIT_ERROR	1
#define X86_CLEAR_RANGE_CLEAR_LARGE	2
#define X86_CLEAR_RANGE_WALK		3

#define X86_CLEAR_OLD_FLUSH_MEMOBJ	0x01
#define X86_CLEAR_OLD_FREE_ANON		0x02
#define X86_CLEAR_OLD_XPMEM_KEEP	0x04
#define X86_CLEAR_OLD_TRY_UNMAP		0x08

#define X86_CLEAR_EFFECT_FLUSH_MEMOBJ	1
#define X86_CLEAR_EFFECT_FREE_ANON	2
#define X86_CLEAR_EFFECT_XPMEM_KEEP	3
#define X86_CLEAR_EFFECT_FREE_UNMAPPED	4
#define X86_CLEAR_EFFECT_CHILD_FREE	5
#define X86_CLEAR_TOP_LOG_INVALID	6
#define X86_CLEAR_TOP_LOG_ALLOC_FAILED	7
#define X86_CLEAR_RANGE_LOG_SPLIT	8
#define X86_CLEAR_RANGE_LOG_LARGE_PHYS	9

#define X86_CHANGE_ATTR_ENOENT		0
#define X86_CHANGE_ATTR_APPLY		1
#define X86_CHANGE_ATTR_SPLIT_ERROR	2
#define X86_CHANGE_ATTR_WALK		3

#define X86_SET_RANGE_APPLY		0
#define X86_SET_RANGE_ALLOC_AND_WALK	1
#define X86_SET_RANGE_MAP_LARGE		2
#define X86_SET_RANGE_BUSY		3
#define X86_SET_RANGE_WALK		4

#define X86_SET_RANGE_LOG_BUSY		1
#define X86_SET_RANGE_LOG_ALLOC_FAILED	2
#define X86_SET_RANGE_LOG_WALK_FAILED	3
#define X86_SET_RANGE_LOG_MAP_LARGE	4
#define X86_SET_RANGE_LOG_RSS_ADD	5
#define X86_SET_RANGE_LOG_RSS_SKIP	6

#define X86_LOOKUP_PTE_MISS		0
#define X86_LOOKUP_PTE_WALK		1
#define X86_LOOKUP_PTE_HIT		2

#define X86_VTOP_MISS			0
#define X86_VTOP_WALK			1
#define X86_VTOP_HIT			2

#define X86_DESTROY_PT_SKIP		0
#define X86_DESTROY_PT_DESCEND		1

#define X86_PT_DESTROY_PANIC_LEVEL	1
#define X86_PT_DESTROY_PANIC_NULL	2

#define X86_PT_SET_PTE_LOG_L2_ALIGN	1
#define X86_PT_SET_PTE_LOG_L3_ALIGN	2
#define X86_PT_SET_PTE_LOG_PAGE_SIZE	3

#define X86_USER_COPY_READ		0
#define X86_USER_COPY_WRITE		1
#define X86_USER_COPY_LOG_RANGE		1
#define X86_USER_COPY_LOG_PF		2
#define X86_USER_COPY_LOG_VTOP		3
#define X86_USER_COPY_LOG_EXTERNAL	4
#define X86_USER_COPY_LOG_PATCH_START	5
#define X86_USER_COPY_LOG_PATCH_RANGE	6
#define X86_USER_COPY_LOG_PATCH_PF	7
#define X86_USER_COPY_LOG_PATCH_VTOP	8
#define X86_USER_COPY_LOG_PATCH_DONE	9

#define X86_INIT_NORMAL_LOG_RANGE	1
#define X86_INIT_NORMAL_LOG_SET_FAILED	2
#define X86_INIT_TEXT_LOG_LPAGES	1
#define X86_INIT_TEXT_LOG_BASE		2
#define X86_INIT_LINUX_LOG_FULL		1
#define X86_INIT_LINUX_LOG_FULL_RANGE	2
#define X86_INIT_LINUX_LOG_FULL_SET_FAILED	3
#define X86_INIT_LINUX_LOG_CHUNKS	4
#define X86_INIT_LINUX_LOG_NO_CHUNK	5
#define X86_INIT_LINUX_LOG_BAD_CHUNK	6
#define X86_INIT_LINUX_LOG_CHUNK_RANGE	7
#define X86_INIT_LINUX_LOG_CHUNK_SET_FAILED	8
#define X86_ADDR_LOG_KERNEL		1
#define X86_ADDR_LOG_STRAIGHT		2
#define X86_PT_PRINT_LOG_TABLE		1
#define X86_PT_PRINT_LOG_NOT_PRESENT	2
#define X86_PT_PRINT_LOG_ENTRY		3
#define X86_PT_PRINT_LOG_LARGE		4

typedef int (*x86_walk_pte_callback_t)(void *args, unsigned long *ptep,
				       uint64_t base, uint64_t start,
				       uint64_t end);
typedef int (*x86_visit_pte_fn_t)(void *arg, void *pt,
				  unsigned long *ptep, void *base,
				  int pgshift);
typedef int (*x86_visit_pte_walk_fn_t)(void *pt, unsigned long base,
				       unsigned long start,
				       unsigned long end, void *args);
typedef void (*x86_visit_pte_log_fn_t)(int event, int level_shift);
typedef int (*x86_walk_phys_check_fn_t)(unsigned long phys);
typedef void *(*x86_pt_alloc_pages_fn_t)(int nr_pages, int ap_flag);
typedef void (*x86_pt_destroy_fn_t)(int level, void *pt);
typedef void *(*x86_pt_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*x86_pt_free_pages_fn_t)(void *addr, int nr_pages);
typedef void (*x86_pt_destroy_panic_fn_t)(int reason);
typedef unsigned long (*x86_pt_virt_to_phys_fn_t)(void *addr);
typedef int (*x86_pt_set_page_fn_t)(void *pt, unsigned long virt,
				    unsigned long phys, unsigned long attr);
typedef void (*x86_pt_set_page_log_fn_t)(unsigned long virt);
typedef void (*x86_pt_set_pte_log_fn_t)(int event, void *pt,
					unsigned long *ptep, size_t pgsize,
					unsigned long phys, unsigned long attr,
					int error, unsigned long current);
typedef void (*x86_pt_set_pte_panic_fn_t)(void);
typedef void *(*x86_split_phys_to_page_fn_t)(unsigned long phys);
typedef void (*x86_split_page_map_fn_t)(void *page);
typedef void (*x86_split_rss_fn_t)(size_t size, size_t pgsize);
typedef int (*x86_split_page_unmap_fn_t)(void *page);
typedef void (*x86_split_log_fn_t)(int event, unsigned long value,
				   size_t size, size_t pgsize, void *page);
typedef void (*x86_split_panic_fn_t)(void);
typedef unsigned long *(*x86_pt_split_lookup_fn_t)(void *pt,
						   unsigned long addr,
						   int pgshift,
						   unsigned long *pgaddrp,
						   size_t *pgsizep,
						   int *p2alignp);
typedef int (*x86_pt_splitable_fn_t)(void *page, unsigned int memobj_flags);
typedef int (*x86_pt_split_large_fn_t)(unsigned long *ptep, size_t pgsize);
typedef void (*x86_pt_split_flush_fn_t)(void *vm, unsigned long addr,
					int cpu_id);
typedef void (*x86_pt_split_log_fn_t)(int event, int error);
typedef int (*x86_move_set_range_fn_t)(void *pt, void *vm,
				       unsigned long start,
				       unsigned long end,
				       unsigned long phys,
				       unsigned long attr, int pgshift,
				       void *range, int overwrite);
typedef void (*x86_move_log_fn_t)(int event, void *arg, void *pt,
				  unsigned long *ptep,
				  unsigned long entry,
				  unsigned long current,
				  unsigned long pgaddr, int pgshift,
				  int error);
typedef int (*x86_move_visit_range_fn_t)(void *pt, unsigned long start,
					 unsigned long end, int pgshift,
					 int flags,
					 x86_visit_pte_fn_t visitor_fn,
					 void *arg);
typedef void (*x86_move_flush_fn_t)(void);
typedef unsigned long (*x86_read_cr3_fn_t)(void);
typedef void (*x86_load_cr3_fn_t)(unsigned long pt_addr);
typedef void (*x86_invlpg_fn_t)(unsigned long addr);
typedef unsigned long (*x86_get_memory_address_fn_t)(int type, int arg);
typedef void (*x86_init_normal_log_fn_t)(int event, unsigned long a,
					 unsigned long b, unsigned long c);
typedef void (*x86_init_text_log_fn_t)(int event, unsigned long a,
				       unsigned long b, unsigned long c);
typedef char *(*x86_find_command_line_fn_t)(char *name);
typedef int (*x86_get_nr_memory_chunks_fn_t)(void);
typedef int (*x86_get_memory_chunk_fn_t)(int id, unsigned long *start,
					 unsigned long *end, int *numa_id);
typedef void (*x86_init_linux_log_fn_t)(int event, unsigned long a,
					unsigned long b, unsigned long c,
					unsigned long d, int error);
typedef void (*x86_addr_log_fn_t)(int event, unsigned long value);
typedef void (*x86_reserve_pages_cb_fn_t)(void *pa_allocator,
					  unsigned long start,
					  unsigned long end, int flag);
typedef void (*x86_reserve_arch_fn_t)(unsigned long start, unsigned long end,
				      x86_reserve_pages_cb_fn_t cb_fn);
typedef void (*x86_clear_remote_flush_fn_t)(void *vm,
					   unsigned long *addrs,
					   int nr_addr, int cpu_id);
typedef void (*x86_clear_flush_memobj_fn_t)(void *memobj,
					    unsigned long phys,
					    size_t pgsize);
typedef void *(*x86_clear_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*x86_clear_free_pages_fn_t)(void *addr, int nr_pages);
typedef int (*x86_clear_page_unmap_fn_t)(void *page);
typedef void (*x86_clear_rss_sub_fn_t)(size_t size, size_t pgsize);
typedef void (*x86_clear_memobj_rss_sub_fn_t)(void *memobj, size_t size,
					      size_t pgsize);
typedef void (*x86_clear_effect_log_fn_t)(int event, unsigned long base,
					  unsigned long phys, size_t pgsize);
typedef void (*x86_clear_range_top_log_fn_t)(int event, void *pt,
					     unsigned long start,
					     unsigned long end,
					     int free_physical);
typedef int (*x86_clear_old_action_fn_t)(void *args, unsigned long old,
					 size_t pgsize,
					 unsigned long *physp,
					 void **pagep,
					 int *fileoffp);
typedef int (*x86_clear_child_walk_fn_t)(void *pt, unsigned long base,
					 unsigned long start,
					 unsigned long end, void *args);
typedef void (*x86_clear_range_log_fn_t)(int event, void *args,
					 unsigned long *ptep,
					 unsigned long base,
					 unsigned long start,
					 unsigned long end, int error,
					 int level_shift,
					 unsigned long phys);
typedef int (*x86_set_range_clear_fn_t)(void *pt, void *vm,
					unsigned long start,
					unsigned long end,
					int free_physical,
					void *remote);
typedef int (*x86_set_range_rss_add_fn_t)(void *range, unsigned long phys,
					  size_t size, size_t pgsize);
typedef void (*x86_set_range_log_fn_t)(int event, int level_shift,
				       unsigned long base,
				       unsigned long start,
				       unsigned long end, int error,
				       unsigned long pte,
				       unsigned long phys, size_t size,
				       size_t pgsize, int rss_called);
typedef int (*x86_set_range_child_walk_fn_t)(void *pt, unsigned long base,
					     unsigned long start,
					     unsigned long end, void *args);
typedef int (*x86_range_top_walk_fn_t)(void *pt, unsigned long base,
				       unsigned long start,
				       unsigned long end, void *args);
typedef int (*x86_user_page_fault_fn_t)(void *vm, void *addr,
					unsigned long reason);
typedef int (*x86_user_vtop_fn_t)(void *pt, const void *virt,
				  unsigned long *physp);
typedef int (*x86_user_is_memory_fn_t)(unsigned long start,
				       unsigned long end);
typedef void *(*x86_user_map_fn_t)(unsigned long phys, int nr_pages,
				   unsigned long attr);
typedef void (*x86_user_unmap_fn_t)(void *addr, int nr_pages);
typedef void *(*x86_user_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*x86_user_log_fn_t)(int event, void *vm, unsigned long a,
				  unsigned long b, int error);
typedef int (*x86_read_process_vm_fn_t)(void *vm, void *kdst,
					const void *usrc, size_t size);
typedef int (*x86_write_process_vm_fn_t)(void *vm, void *udst,
					 const void *ksrc, size_t size);
typedef int (*x86_copy_from_user_fn_t)(void *dst, const void *src,
				       size_t size);
typedef int (*x86_copy_to_user_fn_t)(void *dst, const void *src,
				     size_t size);
typedef void (*x86_pt_print_log_fn_t)(int event, int level,
				      unsigned long value, int index);

int x86_vdso_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
				   unsigned long arg);
void *x86_early_alloc_pages_body_result(
	void **last_page_slot, unsigned long end_addr,
	unsigned long bootstrap_end, int nr_pages,
	unsigned long (*virt_to_phys_fn)(void *),
	void *(*phys_to_virt_fn)(unsigned long),
	void (*panic_fn)(int));
int x86_early_alloc_invalidate_body_result(void **last_page_slot);
void *x86_get_last_early_heap_body_result(void **last_page_slot);
int x86_check_available_page_size_body_result(
	int *use_1gb_page_slot,
	void (*cpuid_edx_fn)(unsigned long, unsigned long *),
	void (*log_fn)(int, int));
int x86_enable_ptattr_no_execute_body_result(unsigned long *attr_mask_slot,
					     unsigned long no_execute_attr);
void *x86_ihk_mc_allocate_body_result(
	int kmalloc_initialized, int size, int nowait_flag,
	void *(*kmalloc_fn)(int, int), void (*log_fn)(int));
int x86_ihk_mc_free_body_result(int kmalloc_initialized, void *ptr,
				void (*kfree_fn)(void *), void (*log_fn)(int));
unsigned long x86_setup_l2_body_result(
	void *pt, unsigned long page_head, unsigned long start,
	unsigned long end, x86_pt_virt_to_phys_fn_t virt_to_phys_fn);
unsigned long x86_setup_l3_body_result(
	void *pt, unsigned long page_head, unsigned long start,
	unsigned long end, int critical_flag,
	x86_pt_alloc_pages_fn_t alloc_pages_fn,
	x86_pt_virt_to_phys_fn_t virt_to_phys_fn);
int x86_init_page_table_body_result(
	void **init_pt_slot, void **boot_pt_slot, int *init_pt_loaded_slot,
	void *init_pt_lock, size_t page_table_size, int critical_flag,
	void (*check_available_page_size_fn)(int),
	void *(*alloc_pages_fn)(int, int),
	void (*spin_init_fn)(void *),
	void (*init_normal_area_fn)(void *),
	void (*init_linux_kernel_mapping_fn)(void *),
	void (*init_fixed_area_fn)(void *),
	void (*init_text_area_fn)(void *),
	void (*init_vsyscall_area_fn)(void *),
	void (*init_low_area_fn)(void *),
	void (*load_page_table_fn)(void *),
	void (*log_fn)(int, void *),
	void (*panic_fn)(int));
int x86_pt_print_pte_body_result(
	void *pt, void *init_pt, unsigned long virt,
	x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
	x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
	x86_pt_print_log_fn_t log_fn);
unsigned long x86_attr_to_l3attr_result(unsigned long attr,
					unsigned long attr_mask);
unsigned long x86_attr_to_l2attr_result(unsigned long attr,
					unsigned long attr_mask);
unsigned long x86_attr_to_l1attr_result(unsigned long attr,
					unsigned long attr_mask);
unsigned long x86_set_pte_value_result(unsigned long phys,
					unsigned long attr,
					unsigned long attr_mask);
int x86_pt_set_pte_value_result(size_t pgsize, unsigned long phys,
				unsigned long attr, unsigned long attr_mask,
				int use_1gb_page, unsigned long *entryp);
int x86_smaller_page_size_result(size_t cursize, int use_1gb_page,
				 size_t *newsizep, int *p2alignp);
unsigned long x86_early_alloc_align_end_result(unsigned long end_addr);
int x86_early_alloc_exhausted_result(unsigned long current_phys,
				     unsigned long bootstrap_end);
unsigned long x86_early_alloc_next_result(unsigned long current,
					  int nr_pages);
void x86_pt_indices_result(unsigned long virt, int *l4idxp, int *l3idxp,
			   int *l2idxp, int *l1idxp);
void x86_walk_bounds_result(unsigned long start, unsigned long end,
			    unsigned long base, unsigned long span,
			    int shift, int *sixp, int *eixp);
int x86_walk_step_result(int current_ret, int error, int *next_retp);
int x86_walk_pte_range_result(unsigned long pt_addr, uint64_t base,
			      uint64_t start, uint64_t end,
			      uint64_t span, int shift,
			      x86_walk_pte_callback_t funcp, void *args,
			      x86_walk_phys_check_fn_t phys_check_fn,
			      unsigned long phys_mask);
int x86_virt_to_phys_level_result(unsigned long entry, unsigned long virt,
				  int level_shift, unsigned long size_flag,
				  unsigned long *physp,
				  unsigned long *sizep);
int x86_pt_virt_to_phys_size_result(void *pt, void *init_pt,
				    unsigned long virt, unsigned long *phys,
				    unsigned long *size,
				    x86_pt_phys_to_virt_fn_t phys_to_virt_fn);
uint64_t x86_pt_virt_to_pagemap_result(void *pt, void *init_pt,
				       unsigned long virt,
				       x86_pt_phys_to_virt_fn_t phys_to_virt_fn);
int x86_split_large_page_prepare_result(unsigned long entry, size_t pgsize,
					unsigned long *child_entryp,
					size_t *rss_pgsizep,
					unsigned long *step_p);
unsigned long x86_split_large_page_next_entry_result(unsigned long entry,
						    size_t pgsize);
int x86_split_large_page_source_result(unsigned long entry, size_t pgsize,
				       unsigned long *phys_basep,
				       unsigned long *child_entryp,
				       size_t *rss_pgsizep);
int x86_split_large_page_child_map_result(unsigned long phys_base,
					  size_t pgsize, int index,
					  unsigned long *physp);
unsigned long x86_split_large_page_publish_result(unsigned long child_pt_phys);
int x86_split_large_page_source_unmap_result(unsigned long phys_base,
					     size_t pgsize,
					     unsigned long *physp);
#define X86_SPLIT_LARGE_PAGE_LOG_INVALID_PGSIZE	1
#define X86_SPLIT_LARGE_PAGE_LOG_ALLOC_FAILED	2
#define X86_SPLIT_LARGE_PAGE_LOG_RSS_ADD	3
#define X86_SPLIT_LARGE_PAGE_LOG_RSS_SUB	4
#define X86_SPLIT_LARGE_PAGE_LOG_PAGE_UNMAP	5
int x86_split_large_page_body_result(unsigned long *ptep, size_t pgsize,
				     int alloc_ap_flag,
				     x86_pt_alloc_pages_fn_t alloc_fn,
				     x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				     x86_split_phys_to_page_fn_t phys_to_page_fn,
				     x86_split_page_map_fn_t page_map_fn,
				     x86_split_rss_fn_t rss_add_fn,
				     x86_split_rss_fn_t rss_sub_fn,
				     x86_split_page_unmap_fn_t page_unmap_fn,
				     x86_split_log_fn_t log_fn,
				     x86_split_panic_fn_t panic_fn);
#define X86_PT_SPLIT_LOG_NOT_SPLITABLE	1
#define X86_PT_SPLIT_LOG_SPLIT_FAILED	2
int x86_pt_split_body_result(void *pt, void *vm, unsigned long addr,
			     unsigned int memobj_flags, int cpu_id,
			     x86_pt_split_lookup_fn_t lookup_fn,
			     x86_split_phys_to_page_fn_t phys_to_page_fn,
			     x86_pt_splitable_fn_t splitable_fn,
			     x86_pt_split_large_fn_t split_large_fn,
			     x86_pt_split_flush_fn_t flush_fn,
			     x86_pt_split_log_fn_t log_fn);
unsigned long x86_clear_pt_page_aligned_addr_result(unsigned long virt,
						    int largepage);
int x86_clear_pt_page_target_result(unsigned long l2_entry, int largepage,
				    int *clear_l2p);
int x86_pt_clear_page_result(void *pt, void *init_pt, unsigned long virt,
			     int largepage,
			     x86_pt_phys_to_virt_fn_t phys_to_virt_fn);
int x86_visit_pte_action_result(unsigned long entry, int skip_null,
				unsigned long start, unsigned long end,
				unsigned long base, unsigned long level_size,
				int target_shift, int pgshift,
				unsigned long size_flag,
				int direct_requires_size,
				int direct_enabled, int can_allocate);
int x86_visit_pte_leaf_result(void *visitor_arg, void *root_pt,
			      unsigned long *ptep, unsigned long base,
			      int skip_null, int level_shift,
			      x86_visit_pte_fn_t visitor_fn);
int x86_visit_pte_level_result(void *visitor_arg, void *root_pt,
			       unsigned long *ptep, unsigned long base,
			       unsigned long start, unsigned long end,
			       int skip_null, int retry_skip_null,
			       int pgshift, unsigned long level_size,
			       int target_shift, unsigned long size_flag,
			       int direct_requires_size,
			       int direct_enabled, int can_allocate,
			       unsigned long pdir_attr,
			       x86_pt_alloc_pages_fn_t alloc_fn,
			       x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
			       x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
			       x86_visit_pte_walk_fn_t child_walk_fn,
			       void *child_args,
			       x86_visit_pte_fn_t visitor_fn,
			       x86_visit_pte_log_fn_t log_fn);
int x86_visit_pte_root_result(unsigned long *ptep, unsigned long base,
			      unsigned long start, unsigned long end,
			      int skip_null, int can_allocate,
			      unsigned long pdir_attr,
			      x86_pt_alloc_pages_fn_t alloc_fn,
			      x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
			      x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
			      x86_visit_pte_walk_fn_t child_walk_fn,
			      void *child_args);
int x86_visit_pte_range_dispatch_result(void *pt, unsigned long start,
					unsigned long end, void *args,
					x86_visit_pte_walk_fn_t walk_fn);
int x86_clear_range_validate_result(unsigned long start, unsigned long end,
				    unsigned long user_start,
				    unsigned long user_end);
int x86_clear_range_free_physical_result(int free_physical, int is_dev_file,
					 int is_premap,
					 int is_straight_main);
int x86_clear_range_entry_action_result(unsigned long entry,
					unsigned long base,
					unsigned long start,
					unsigned long end,
					unsigned long level_size,
					unsigned long size_flag);
void x86_clear_range_old_entry_result(unsigned long entry, size_t pgsize,
				      unsigned long *physp,
				      int *fileoffp, int *dirtyp);
int x86_clear_range_old_action_result(int is_fileoff, int free_physical,
				      int has_page, int page_in_memobj,
				      int entry_dirty, int has_memobj,
				      int memobj_no_flush,
				      int memobj_xpmem);
int x86_remote_flush_tlb_add_addr_result(void *vm, unsigned long *addr_array,
					 int *nr_addrp, int max_nr_addr,
					 unsigned long addr, int cpu_id,
					 x86_clear_remote_flush_fn_t flush_fn);
int x86_clear_range_old_effects_result(int old_action, int is_fileoff,
				       int free_physical, void *memobj,
				       void *page, unsigned long phys,
				       unsigned long base, size_t pgsize,
				       x86_clear_flush_memobj_fn_t flush_fn,
				       x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				       x86_clear_free_pages_fn_t free_pages_fn,
				       x86_clear_page_unmap_fn_t page_unmap_fn,
				       x86_clear_rss_sub_fn_t rss_sub_fn,
				       x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
				       x86_clear_effect_log_fn_t log_fn);
int x86_clear_range_child_table_result(unsigned long *ptep, void *pt,
				       unsigned long start, unsigned long base,
				       unsigned long end,
				       unsigned long level_size, int enabled,
				       void *vm, unsigned long *addr_array,
				       int *nr_addrp, int max_nr_addr,
				       int cpu_id,
				       x86_clear_remote_flush_fn_t flush_fn,
				       x86_pt_free_pages_fn_t free_pages_fn,
				       x86_clear_effect_log_fn_t log_fn);
int x86_clear_range_leaf_body_result(void *args, unsigned long *ptep,
				     unsigned long base,
				     unsigned long start,
				     unsigned long end, void *vm,
				     unsigned long *addr_array,
				     int *nr_addrp, int max_nr_addr,
				     int cpu_id, int free_physical,
				     void *memobj,
				     x86_clear_old_action_fn_t old_action_fn,
				     x86_clear_remote_flush_fn_t flush_fn,
				     x86_clear_flush_memobj_fn_t flush_memobj_fn,
				     x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				     x86_clear_free_pages_fn_t free_pages_fn,
				     x86_clear_page_unmap_fn_t page_unmap_fn,
				     x86_clear_rss_sub_fn_t rss_sub_fn,
				     x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
				     x86_clear_effect_log_fn_t effect_log_fn);
int x86_clear_range_level_body_result(void *args, unsigned long *ptep,
				      unsigned long base,
				      unsigned long start,
				      unsigned long end,
				      int level_shift,
				      unsigned long level_size,
				      unsigned long size_flag,
				      int child_teardown_enabled,
				      void *vm,
				      unsigned long *addr_array,
				      int *nr_addrp, int max_nr_addr,
				      int cpu_id, int free_physical,
				      void *memobj,
				      x86_clear_old_action_fn_t old_action_fn,
				      x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				      x86_clear_child_walk_fn_t child_walk_fn,
				      x86_clear_remote_flush_fn_t flush_fn,
				      x86_pt_free_pages_fn_t pt_free_pages_fn,
				      x86_clear_flush_memobj_fn_t flush_memobj_fn,
				      x86_clear_free_pages_fn_t free_pages_fn,
				      x86_clear_page_unmap_fn_t page_unmap_fn,
				      x86_clear_rss_sub_fn_t rss_sub_fn,
				      x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
				      x86_clear_range_log_fn_t range_log_fn,
				      x86_clear_effect_log_fn_t effect_log_fn);
int x86_clear_range_root_body_result(void *args, unsigned long *ptep,
				     unsigned long base,
				     unsigned long start,
				     unsigned long end,
				     x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				     x86_clear_child_walk_fn_t child_walk_fn);
int x86_clear_range_top_result(void *pt, void *vm, unsigned long start,
			       unsigned long end, unsigned long user_start,
			       unsigned long user_end, int requested_free,
			       int is_dev_file, int is_premap,
			       int is_straight_main, void *memobj,
			       unsigned long **addr_slot, int *nr_addrp,
			       int *max_nr_addrp, int *free_physicalp,
			       void **memobj_slot, void **vm_slot,
			       int tlb_array_pages, unsigned long page_size,
			       void *args, x86_pt_alloc_pages_fn_t alloc_fn,
			       x86_pt_free_pages_fn_t free_fn,
			       x86_range_top_walk_fn_t walk_fn,
			       x86_clear_remote_flush_fn_t flush_fn,
			       int cpu_id, x86_clear_range_top_log_fn_t log_fn);
int x86_change_attr_leaf_action_result(unsigned long entry,
				       unsigned long fileoff_flag);
int x86_change_attr_entry_action_result(unsigned long entry,
					unsigned long base,
					unsigned long start,
					unsigned long end,
					unsigned long level_size,
					unsigned long size_flag,
					unsigned long fileoff_flag);
int x86_pt_change_attr_range_result(void *pt, unsigned long start,
				    unsigned long end, unsigned long clrpte,
				    unsigned long setpte,
				    x86_pt_phys_to_virt_fn_t phys_to_virt_fn);
int x86_set_range_leaf_action_result(unsigned long entry);
int x86_set_range_entry_action_result(unsigned long entry,
				      unsigned long base,
				      unsigned long start,
				      unsigned long end,
				      unsigned long diff,
				      int pgshift,
				      int target_shift,
				      unsigned long level_size,
				      unsigned long size_flag,
				      int direct_enabled);
int x86_set_range_map_entry_result(unsigned long phys_base,
				   unsigned long base,
				   unsigned long start,
				   unsigned long attr,
				   int level_shift,
				   unsigned long attr_mask,
				   unsigned long *physp,
				   unsigned long *entryp);
int x86_set_range_conflict_result(void *pt, void *vm, unsigned long start,
				  unsigned long end, unsigned long base,
				  unsigned long current, int level_shift,
				  int free_physical,
				  x86_set_range_clear_fn_t clear_fn,
				  x86_set_range_log_fn_t log_fn);
int x86_set_range_alloc_failed_result(void *pt, void *vm,
				      unsigned long start,
				      unsigned long end,
				      unsigned long base,
				      unsigned long current,
				      int level_shift,
				      int free_physical,
				      x86_set_range_clear_fn_t clear_fn,
				      x86_set_range_log_fn_t log_fn);
int x86_set_range_walk_failed_result(int error, unsigned long base,
				     unsigned long start, unsigned long end,
				     unsigned long current, int level_shift,
				     x86_set_range_log_fn_t log_fn);
int x86_set_range_map_effect_result(unsigned long phys_base,
				    unsigned long base,
				    unsigned long start,
				    unsigned long end,
				    unsigned long attr,
				    int level_shift,
				    unsigned long attr_mask,
				    size_t pgsize,
				    unsigned long *ptep,
				    void *range,
				    int log_large,
				    x86_set_range_rss_add_fn_t rss_add_fn,
				    x86_set_range_log_fn_t log_fn);
int x86_set_range_leaf_body_result(void *args, unsigned long *ptep,
				   unsigned long base, unsigned long start,
				   unsigned long end, void *pt, void *vm,
				   unsigned long phys_base,
				   unsigned long attr,
				   unsigned long attr_mask, void *range,
				   x86_set_range_clear_fn_t clear_fn,
				   x86_set_range_rss_add_fn_t rss_add_fn,
				   x86_set_range_log_fn_t log_fn);
int x86_set_range_level_body_result(void *args, unsigned long *ptep,
				    unsigned long base, unsigned long start,
				    unsigned long end, void *pt, void *vm,
				    unsigned long phys_base,
				    unsigned long attr,
				    unsigned long attr_mask,
				    unsigned long diff, int pgshift,
				    int target_shift,
				    unsigned long level_size,
				    unsigned long size_flag,
				    int direct_enabled,
				    unsigned long pdir_attr, void *range,
				    x86_pt_alloc_pages_fn_t alloc_fn,
				    x86_pt_free_pages_fn_t free_fn,
				    x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				    x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
				    x86_set_range_child_walk_fn_t child_walk_fn,
				    x86_set_range_clear_fn_t clear_fn,
				    x86_set_range_rss_add_fn_t rss_add_fn,
				    x86_set_range_log_fn_t log_fn);
int x86_set_range_top_result(void *pt, void *vm, unsigned long start,
			     unsigned long end, unsigned long phys,
			     int attr, int pgshift, void *range, void *args,
			     void **args_ptp, unsigned long *args_physp,
			     int *args_attrp, unsigned long *args_diffp,
			     void **args_vmp, int *args_pgshiftp,
			     void **args_rangep, x86_range_top_walk_fn_t walk_fn,
			     x86_set_range_log_fn_t log_fn);
int x86_pte_store_result(unsigned long *ptep, unsigned long entry);
unsigned long x86_pte_publish_table_result(unsigned long *ptep,
					   unsigned long entry);
unsigned long x86_pte_clear_result(unsigned long *ptep);
unsigned long x86_pte_apply_attr_result(unsigned long *ptep,
					unsigned long clrpte,
					unsigned long setpte);
int x86_pt_kernel_lock_needed_result(unsigned long virt);
void *x86_pt_alloc_zeroed_result(int ap_flag,
				 x86_pt_alloc_pages_fn_t alloc_fn);
unsigned long *x86_pt_get_pte_result(void *pt, void *init_pt,
				     unsigned long virt, unsigned long attr,
				     unsigned long attr_mask, int ap_flag,
				     x86_pt_alloc_pages_fn_t alloc_fn,
				     x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				     x86_pt_phys_to_virt_fn_t phys_to_virt_fn);
int x86_pt_set_page_body_result(void *pt, void *init_pt,
				unsigned long virt, unsigned long phys,
				unsigned long attr, unsigned long attr_mask,
				x86_pt_alloc_pages_fn_t alloc_fn,
				x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
				x86_pt_set_page_log_fn_t log_fn);
int x86_lookup_default_pgshift_result(int pgshift, int use_1gb_page);
int x86_lookup_l4_empty_pgshift_result(int pgshift);
int x86_lookup_level_action_result(unsigned long entry, int pgshift,
				   int level_shift, unsigned long size_flag);
void x86_lookup_shape_result(unsigned long virt, int pgshift,
			     unsigned long *basep, size_t *sizep,
			     int *p2alignp);
unsigned long *x86_pt_lookup_pte_result(void *pt, unsigned long virt,
					int pgshift, int use_1gb_page,
					unsigned long *basep,
					size_t *sizep, int *p2alignp,
					x86_pt_phys_to_virt_fn_t phys_to_virt_fn);
int x86_move_pte_preflight_result(unsigned long entry, size_t pgsize,
				  unsigned long src, unsigned long dest,
				  unsigned long pgaddr,
				  unsigned long *mapped_destp);
#define X86_MOVE_ONE_LOG_FILEOFF	1
#define X86_MOVE_ONE_LOG_SET_FAILED	2
int x86_move_one_page_body_result(void *arg, void *pt, unsigned long *ptep,
				  unsigned long pgaddr, int pgshift,
				  unsigned long src, unsigned long dest,
				  void *vm, void *range,
				  x86_move_set_range_fn_t set_range_fn,
				  x86_move_log_fn_t log_fn);
int x86_move_pte_range_body_result(void *pt, unsigned long src,
				   unsigned long dest, size_t size,
				   void *vm, void *range, void *args,
				   uintptr_t *args_srcp,
				   uintptr_t *args_destp,
				   void **args_vmp, void **args_rangep,
				   x86_visit_pte_fn_t visitor_fn,
				   x86_move_visit_range_fn_t visit_fn,
				   x86_move_flush_fn_t flush_fn);
unsigned long x86_read_cr3_result(void);
void x86_load_cr3_result(unsigned long pt_addr);
void x86_flush_tlb_body_result(x86_read_cr3_fn_t read_cr3_fn,
			       x86_load_cr3_fn_t load_cr3_fn);
void x86_flush_tlb_result(void);
void x86_flush_tlb_single_body_result(unsigned long addr,
				      x86_invlpg_fn_t invlpg_fn);
void x86_flush_tlb_single_result(unsigned long addr);
int x86_load_page_table_body_result(void *pt, void *init_pt,
				    x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				    x86_load_cr3_fn_t load_cr3_fn);
void *x86_map_fixed_area_body_result(void *init_pt, unsigned long *fixed_virtp,
				     unsigned long phys, unsigned long size,
				     int uncachable,
				     x86_pt_set_page_fn_t set_page_fn,
				     x86_move_flush_fn_t flush_fn);
int x86_init_normal_area_body_result(void *pt, unsigned long map_st_start,
				     unsigned long large_page_size,
				     unsigned long writable_attr,
				     int map_start_key, int map_end_key,
				     x86_get_memory_address_fn_t get_addr_fn,
				     x86_pt_set_page_fn_t set_large_fn,
				     x86_init_normal_log_fn_t log_fn);
int x86_init_text_area_body_result(void *pt, unsigned long map_kernel_start,
				   unsigned long end_addr,
				   unsigned long large_page_size,
				   int large_page_shift,
				   unsigned long large_page_mask,
				   unsigned long kernel_phys_base,
				   unsigned long writable_attr,
				   x86_pt_set_page_fn_t set_large_fn,
				   x86_init_text_log_fn_t log_fn);
int x86_init_fixed_area_body_result(unsigned long *fixed_virtp,
				    unsigned long map_fixed_start);
int x86_init_low_area_body_result(void *pt, unsigned long no_execute_attr,
				  unsigned long writable_attr,
				  x86_pt_set_page_fn_t set_large_fn);
int x86_init_vsyscall_area_body_result(void *pt, unsigned long vsyscall_addr,
				       void *vsyscall_page,
				       unsigned long attr,
				       x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				       x86_pt_set_page_fn_t set_page_fn);
int x86_init_linux_kernel_mapping_body_result(
	void *pt, unsigned long linux_page_offset_base,
	unsigned long large_page_size, unsigned long writable_attr,
	unsigned long full_map_end, char *safe_kernel_map_name,
	x86_find_command_line_fn_t find_command_line_fn,
	x86_get_nr_memory_chunks_fn_t get_nr_chunks_fn,
	x86_get_memory_chunk_fn_t get_chunk_fn,
	x86_pt_set_page_fn_t set_large_fn,
	x86_init_linux_log_fn_t log_fn);
unsigned long x86_virt_to_phys_body_result(
	unsigned long va, unsigned long map_kernel_start,
	unsigned long kernel_phys_base, unsigned long linux_page_offset_base,
	unsigned long map_fixed_start, unsigned long map_st_start,
	x86_addr_log_fn_t log_fn);
void *x86_phys_to_virt_body_result(unsigned long phys, int init_pt_loaded,
				   unsigned long map_st_start,
				   unsigned long linux_page_offset_base);
int x86_reserve_arch_pages_body_result(
	void *pa_allocator, unsigned long start, unsigned long end,
	void *head, void *last_early_heap,
	unsigned long ap_trampoline, unsigned long ap_trampoline_size,
	unsigned long page_size,
	x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
	x86_reserve_pages_cb_fn_t cb_fn,
	x86_reserve_arch_fn_t reserve_arch_fn);
void x86_move_pte_entry_parts_result(unsigned long entry,
				     unsigned long *physp,
				     unsigned long *attrp);
unsigned long x86_arch_vrflag_to_ptattr_result(unsigned long flag,
					       uint64_t fault,
					       unsigned long common_attr);
int x86_destroy_pt_entry_action_result(int level, unsigned long entry,
				       unsigned long *lower_physp);
void *x86_pt_create_result(void *init_pt, int ap_flag,
			   x86_pt_alloc_pages_fn_t alloc_fn);
int x86_pt_destroy_table_result(int level, void *pt,
				x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
				x86_pt_free_pages_fn_t free_pages_fn,
				x86_pt_destroy_panic_fn_t panic_fn);
void x86_pt_destroy_root_result(void *pt, x86_pt_destroy_fn_t destroy_fn);
int x86_pt_prepare_map_result(void *pt, void *init_pt, unsigned long virt,
			      unsigned long size, int flag,
			      unsigned long writable_attr,
			      x86_pt_alloc_pages_fn_t alloc_fn,
			      x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
			      x86_pt_set_page_fn_t set_page_fn);
int x86_pt_set_pte_body_result(void *pt, unsigned long *ptep, size_t pgsize,
			      unsigned long phys, unsigned long attr,
			      unsigned long attr_mask, int use_1gb_page,
			      x86_pt_set_pte_log_fn_t log_fn,
			      x86_pt_set_pte_panic_fn_t panic_fn);
int x86_verify_process_vm_result(void *vm, unsigned long uaddr, size_t size,
				 unsigned long user_start,
				 unsigned long user_end,
				 unsigned long reason,
				 x86_user_page_fault_fn_t page_fault_fn,
				 x86_user_log_fn_t log_fn);
int x86_process_vm_copy_result(void *vm, void *pt, unsigned long user_addr,
			       unsigned long kernel_addr, size_t size,
			       unsigned long user_start, unsigned long user_end,
			       unsigned long reason, int direction,
			       x86_user_page_fault_fn_t page_fault_fn,
			       x86_user_vtop_fn_t vtop_fn,
			       x86_user_is_memory_fn_t is_memory_fn,
			       x86_user_map_fn_t map_fn,
			       x86_user_unmap_fn_t unmap_fn,
			       x86_user_phys_to_virt_fn_t phys_to_virt_fn,
			       x86_user_log_fn_t log_fn);
int x86_copy_from_user_result(void *vm, void *dst, const void *src,
			      size_t size, x86_read_process_vm_fn_t read_fn);
int x86_copy_to_user_result(void *vm, void *dst, const void *src,
			    size_t size, x86_write_process_vm_fn_t write_fn);
long x86_getlong_user_result(long *dest, const long *src,
			     x86_copy_from_user_fn_t copy_fn);
int x86_getint_user_result(int *dest, const int *src,
			   x86_copy_from_user_fn_t copy_fn);
int x86_setlong_user_result(long *dst, long data,
			    x86_copy_to_user_fn_t copy_fn);
int x86_setint_user_result(int *dst, int data,
			   x86_copy_to_user_fn_t copy_fn);
int x86_strlen_user_result(void *vm, const char *src,
			   unsigned long map_kernel_start,
			   x86_user_page_fault_fn_t verify_fn);
int x86_strcpy_from_user_result(void *vm, char *dst, const char *src,
				unsigned long map_kernel_start,
				x86_user_page_fault_fn_t verify_fn);
int x86_copy_from_user_public_result(void *thread, void *dst,
				     const void *src, size_t size,
				     x86_read_process_vm_fn_t read_fn);
int x86_copy_to_user_public_result(void *thread, void *dst,
				   const void *src, size_t size,
				   x86_write_process_vm_fn_t write_fn);
int x86_copy_from_user_direct_public_result(void *thread, void *dst,
					    const void *src, size_t size,
					    x86_user_page_fault_fn_t page_fault_fn,
					    x86_user_vtop_fn_t vtop_fn,
					    x86_user_is_memory_fn_t is_memory_fn,
					    x86_user_map_fn_t map_fn,
					    x86_user_unmap_fn_t unmap_fn,
					    x86_user_phys_to_virt_fn_t phys_to_virt_fn,
					    x86_user_log_fn_t log_fn);
int x86_copy_to_user_direct_public_result(void *thread, void *dst,
					  const void *src, size_t size,
					  x86_user_page_fault_fn_t page_fault_fn,
					  x86_user_vtop_fn_t vtop_fn,
					  x86_user_is_memory_fn_t is_memory_fn,
					  x86_user_map_fn_t map_fn,
					  x86_user_unmap_fn_t unmap_fn,
					  x86_user_phys_to_virt_fn_t phys_to_virt_fn,
					  x86_user_log_fn_t log_fn);
int x86_strlen_user_public_result(void *thread, const char *src,
				  unsigned long map_kernel_start,
				  x86_user_page_fault_fn_t verify_fn);
int x86_strcpy_from_user_public_result(void *thread, char *dst,
				       const char *src,
				       unsigned long map_kernel_start,
				       x86_user_page_fault_fn_t verify_fn);
long x86_getlong_user_public_result(long *dest, const long *src,
				    x86_copy_from_user_fn_t copy_fn);
int x86_getint_user_public_result(int *dest, const int *src,
				  x86_copy_from_user_fn_t copy_fn);
int x86_setlong_user_public_result(long *dst, long data,
				   x86_copy_to_user_fn_t copy_fn);
int x86_setint_user_public_result(int *dst, int data,
				  x86_copy_to_user_fn_t copy_fn);
int x86_verify_process_vm_public_result(void *vm, const void *usrc,
					size_t size,
					x86_user_page_fault_fn_t page_fault_fn,
					x86_user_log_fn_t log_fn);
int x86_read_process_vm_public_result(void *vm, void *kdst,
				      const void *usrc, size_t size,
				      x86_user_page_fault_fn_t page_fault_fn,
				      x86_user_vtop_fn_t vtop_fn,
				      x86_user_is_memory_fn_t is_memory_fn,
				      x86_user_map_fn_t map_fn,
				      x86_user_unmap_fn_t unmap_fn,
				      x86_user_phys_to_virt_fn_t phys_to_virt_fn,
				      x86_user_log_fn_t log_fn);
int x86_write_process_vm_public_result(void *vm, void *udst,
				       const void *ksrc, size_t size,
				       x86_user_page_fault_fn_t page_fault_fn,
				       x86_user_vtop_fn_t vtop_fn,
				       x86_user_is_memory_fn_t is_memory_fn,
				       x86_user_map_fn_t map_fn,
				       x86_user_unmap_fn_t unmap_fn,
				       x86_user_phys_to_virt_fn_t phys_to_virt_fn,
				       x86_user_log_fn_t log_fn);
int x86_patch_process_vm_public_result(void *vm, void *udst,
				       const void *ksrc, size_t size,
				       x86_user_page_fault_fn_t page_fault_fn,
				       x86_user_vtop_fn_t vtop_fn,
				       x86_user_is_memory_fn_t is_memory_fn,
				       x86_user_map_fn_t map_fn,
				       x86_user_unmap_fn_t unmap_fn,
				       x86_user_phys_to_virt_fn_t phys_to_virt_fn,
				       x86_user_log_fn_t log_fn);

#endif /* HEADER_X86_MEMORY_HELPERS_H */
