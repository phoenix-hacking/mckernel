/* SPDX-License-Identifier: GPL-2.0 */
#ifndef HEADER_X86_MEMORY_HELPERS_H
#define HEADER_X86_MEMORY_HELPERS_H

#include <ihk/types.h>

#define X86_VISIT_PTE_SKIP		0
#define X86_VISIT_PTE_DIRECT		1
#define X86_VISIT_PTE_ALLOC_AND_WALK	2
#define X86_VISIT_PTE_WALK		3
#define X86_VISIT_PTE_SPLIT_ERROR	4

#define X86_CLEAR_RANGE_SKIP		0
#define X86_CLEAR_RANGE_SPLIT_ERROR	1
#define X86_CLEAR_RANGE_CLEAR_LARGE	2
#define X86_CLEAR_RANGE_WALK		3

#define X86_CLEAR_OLD_FLUSH_MEMOBJ	0x01
#define X86_CLEAR_OLD_FREE_ANON		0x02
#define X86_CLEAR_OLD_XPMEM_KEEP	0x04
#define X86_CLEAR_OLD_TRY_UNMAP		0x08

#define X86_CHANGE_ATTR_ENOENT		0
#define X86_CHANGE_ATTR_APPLY		1
#define X86_CHANGE_ATTR_SPLIT_ERROR	2
#define X86_CHANGE_ATTR_WALK		3

#define X86_SET_RANGE_APPLY		0
#define X86_SET_RANGE_ALLOC_AND_WALK	1
#define X86_SET_RANGE_MAP_LARGE		2
#define X86_SET_RANGE_BUSY		3
#define X86_SET_RANGE_WALK		4

#define X86_LOOKUP_PTE_MISS		0
#define X86_LOOKUP_PTE_WALK		1
#define X86_LOOKUP_PTE_HIT		2

#define X86_VTOP_MISS			0
#define X86_VTOP_WALK			1
#define X86_VTOP_HIT			2

#define X86_DESTROY_PT_SKIP		0
#define X86_DESTROY_PT_DESCEND		1

#define X86_PT_SET_PTE_LOG_L2_ALIGN	1
#define X86_PT_SET_PTE_LOG_L3_ALIGN	2
#define X86_PT_SET_PTE_LOG_PAGE_SIZE	3

typedef int (*x86_walk_pte_callback_t)(void *args, unsigned long *ptep,
				       uint64_t base, uint64_t start,
				       uint64_t end);
typedef int (*x86_walk_phys_check_fn_t)(unsigned long phys);
typedef void *(*x86_pt_alloc_pages_fn_t)(int nr_pages, int ap_flag);
typedef void (*x86_pt_destroy_fn_t)(int level, void *pt);
typedef unsigned long (*x86_pt_virt_to_phys_fn_t)(void *addr);
typedef int (*x86_pt_set_page_fn_t)(void *pt, unsigned long virt,
				    unsigned long phys, unsigned long attr);
typedef void (*x86_pt_set_pte_log_fn_t)(int event, void *pt,
					unsigned long *ptep, size_t pgsize,
					unsigned long phys, unsigned long attr,
					int error, unsigned long current);
typedef void (*x86_pt_set_pte_panic_fn_t)(void);

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
unsigned long x86_clear_pt_page_aligned_addr_result(unsigned long virt,
						    int largepage);
int x86_clear_pt_page_target_result(unsigned long l2_entry, int largepage,
				    int *clear_l2p);
int x86_visit_pte_action_result(unsigned long entry, int skip_null,
				unsigned long start, unsigned long end,
				unsigned long base, unsigned long level_size,
				int target_shift, int pgshift,
				unsigned long size_flag,
				int direct_requires_size,
				int direct_enabled, int can_allocate);
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
int x86_change_attr_leaf_action_result(unsigned long entry,
				       unsigned long fileoff_flag);
int x86_change_attr_entry_action_result(unsigned long entry,
					unsigned long base,
					unsigned long start,
					unsigned long end,
					unsigned long level_size,
					unsigned long size_flag,
					unsigned long fileoff_flag);
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
int x86_pte_store_result(unsigned long *ptep, unsigned long entry);
unsigned long x86_pte_publish_table_result(unsigned long *ptep,
					   unsigned long entry);
unsigned long x86_pte_clear_result(unsigned long *ptep);
unsigned long x86_pte_apply_attr_result(unsigned long *ptep,
					unsigned long clrpte,
					unsigned long setpte);
int x86_lookup_default_pgshift_result(int pgshift, int use_1gb_page);
int x86_lookup_l4_empty_pgshift_result(int pgshift);
int x86_lookup_level_action_result(unsigned long entry, int pgshift,
				   int level_shift, unsigned long size_flag);
void x86_lookup_shape_result(unsigned long virt, int pgshift,
			     unsigned long *basep, size_t *sizep,
			     int *p2alignp);
int x86_move_pte_preflight_result(unsigned long entry, size_t pgsize,
				  unsigned long src, unsigned long dest,
				  unsigned long pgaddr,
				  unsigned long *mapped_destp);
void x86_move_pte_entry_parts_result(unsigned long entry,
				     unsigned long *physp,
				     unsigned long *attrp);
int x86_destroy_pt_entry_action_result(int level, unsigned long entry,
				       unsigned long *lower_physp);
void *x86_pt_create_result(void *init_pt, int ap_flag,
			   x86_pt_alloc_pages_fn_t alloc_fn);
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

#endif /* HEADER_X86_MEMORY_HELPERS_H */
