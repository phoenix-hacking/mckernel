/* mem.c COPYRIGHT FUJITSU LIMITED 2015-2018 */
/**
 * \file mem.c
 *  License details are found in the file LICENSE.
 * \brief
 *  memory management
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * 	Copyright (C) 2012  RIKEN AICS
 * \author Masamichi Takagi  <m-takagi@ab.jp.nec.com> \par
 * 	Copyright (C) 2012 - 2013  NEC Corporation
 * \author Balazs Gerofi  <bgerofi@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2013  The University of Tokyo
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013 Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <kmsg.h>
#include <kmalloc.h>
#include <string.h>
#include <ihk/cpu.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <ihk/page_alloc.h>
#include <registers.h>




#include <cls.h>
#include <page.h>
#include <kref.h>
#include <bitops.h>
#include <cpulocal.h>
#include <init.h>
#include <cas.h>
#include <rusage_private.h>
#include <syscall.h>
#include <profile.h>
#include <process.h>
#include <limits.h>
#include <sysfs.h>
#include <ihk/debug.h>
#include <llist.h>
#include <bootparam.h>
#include <memobj.h>

//#define DEBUG_PRINT_MEM







extern unsigned long pa_start, pa_end;
extern struct ihk_mc_numa_node memory_nodes[512];





extern int ihk_mc_pt_print_pte(struct page_table *pt, void *virt);
extern int interrupt_from_user(void *);


extern struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];





extern int anon_on_demand;







extern int xpmem_page_in_remote_on_attach;




extern int sysctl_overcommit_memory;

























































































































































































































































































































































































































































































































































































































extern void *early_alloc_pages(int nr_pages);
extern void early_alloc_invalidate(void);



extern char *memdebug;































































void *___kmalloc(int size, ihk_mc_ap_flag flag);
void ___kfree(void *ptr);






void *___ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
		ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr);
void *___ihk_mc_alloc_pages(int npages, ihk_mc_ap_flag flag, int is_user);
void ___ihk_mc_free_pages(void *p, int npages, int is_user);







struct dump_pase_info;

typedef void *(*mem_early_alloc_pages_fn_t)(int nr_pages);
typedef void (*mem_pending_warn_fn_t)(unsigned long phys);
typedef void (*mem_pending_free_fn_t)(unsigned long phys, int npages,
		int is_user);
typedef int (*mem_begin_free_pages_pending_fn_t)(struct list_head *pendings);
typedef int (*mem_finish_free_pages_pending_fn_t)(struct list_head *pendings,
		mem_pending_free_fn_t free_fn);
typedef void (*mem_reserve_log_fn_t)(unsigned long start, unsigned long end,
		unsigned long pages);
typedef void (*mem_reserve_range_fn_t)(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long start, unsigned long end);
typedef int (*mem_reserve_pages_body_fn_t)(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long allocator_start, unsigned long allocator_end,
		unsigned long start, unsigned long end,
		mem_reserve_log_fn_t log_fn,
		mem_reserve_range_fn_t reserve_fn);
typedef int (*mem_get_nr_memory_chunks_fn_t)(void);
typedef int (*mem_get_memory_chunk_fn_t)(int id, unsigned long *start,
		unsigned long *end, int *numa_id);
typedef unsigned long (*mem_virt_to_phys_fn_t)(void *va);
typedef void *(*mem_phys_to_virt_fn_t)(unsigned long pa);
typedef struct list_head *(*mem_pending_pages_fn_t)(void);
typedef void *(*mem_get_numa_node_fn_t)(int numa_id);
typedef void (*mem_numa_free_fn_t)(void *node, unsigned long addr,
		int npages);
typedef void (*mem_rusage_sub_fn_t)(int numa_id, int npages, int is_user);
typedef unsigned long (*mem_try_alloc_node_fn_t)(int numa_id, int npages,
		int p2align, int is_user, int *oomp);
typedef int (*mem_distance_id_fn_t)(int base_node, int index);
typedef int (*mem_mask_test_fn_t)(int numa_id, unsigned long *numa_mask);
typedef int (*mem_interleave_next_fn_t)(int off, unsigned long *numa_mask);
typedef void (*mem_rusage_add_fn_t)(int numa_id, int npages, int is_user);
typedef void (*mem_alloc_log_fn_t)(int event, int current_node, int numa_id,
		int npages);
typedef void *(*mem_current_vm_fn_t)(void);
typedef void *(*mem_range_policy_search_fn_t)(void *vm,
		unsigned long virt_addr);
typedef void *(*mem_lookup_memory_range_fn_t)(void *vm, unsigned long start,
		unsigned long end);
typedef int (*mem_range_is_shm_fn_t)(void *range);
typedef void (*mem_policy_fields_fn_t)(void *policy, int *numa_mem_policy,
		unsigned long **numa_mask, int **il_prev);
typedef void *(*mem_mckernel_alloc_policy_fn_t)(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user,
		int current_node, int nr_nodes, int numa_mem_policy,
		int chk_shm, unsigned long *numa_mask, int *il_prevp);
typedef struct page *(*mem_phys_to_page_fn_t)(unsigned long phys);
typedef void (*mem_free_in_allocator_fn_t)(void *va, int npages,
		int is_user);
typedef int (*mem_mckernel_free_pages_body_fn_t)(void *va, int npages,
		int is_user, struct list_head *pendings,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_phys_to_page_fn_t phys_to_page_fn,
		mem_free_in_allocator_fn_t free_in_allocator_fn,
		mem_pending_warn_fn_t warn_fn);
typedef int (*mem_query_free_node_pages_fn_t)(int node);
typedef void (*mem_query_free_log_fn_t)(int pages);
typedef int (*mem_query_page_hash_count_fn_t)(void);
typedef void (*mem_query_sbox_write_fn_t)(int offset, unsigned int value);
typedef int (*mem_get_nr_numa_nodes_fn_t)(void);
typedef void (*mem_lifecycle_void_fn_t)(void);
typedef void (*mem_set_page_allocator_fn_t)(struct ihk_mc_pa_ops *ops);
typedef void (*mem_set_page_fault_handler_fn_t)(unsigned long handler);
typedef int (*mem_get_vector_fn_t)(int type);
typedef int (*mem_register_interrupt_handler_fn_t)(int vector,
		unsigned long handler);
typedef char *(*mem_find_command_line_fn_t)(char *name);
typedef void (*mem_init_log_fn_t)(int event);
typedef struct node_distance *(*mem_numa_distance_alloc_fn_t)(int npages,
		unsigned long flag);
typedef int (*mem_numa_distance_fn_t)(int from, int to);
typedef void (*mem_numa_distance_alloc_fail_log_fn_t)(int node);
typedef void (*mem_numa_distance_log_fn_t)(int node,
		struct node_distance *distances, int nr_nodes);
typedef struct ihk_mc_cpu_info *(*mem_get_cpu_info_fn_t)(void);
typedef unsigned long (*mem_get_ns_per_tsc_fn_t)(void);
typedef int (*mem_set_rusage_fn_t)(unsigned long addr, unsigned long size);
typedef void (*mem_rusage_init_log_fn_t)(unsigned long total_memory);
typedef int (*mem_get_numa_node_info_fn_t)(int node, int *linux_numa_id,
		int *type);
typedef void (*mem_numa_node_init_fn_t)(struct ihk_mc_numa_node *node,
		int rbtree_allocator);
typedef void (*mem_numa_add_free_pages_fn_t)(struct ihk_mc_numa_node *node,
		unsigned long start, unsigned long len);
typedef void *(*mem_page_allocator_init_fn_t)(unsigned long start,
		unsigned long end);
typedef void (*mem_numa_list_allocator_fn_t)(void *allocator,
		struct ihk_mc_numa_node *node);
typedef unsigned long (*mem_pagealloc_count_fn_t)(void *allocator);
typedef void (*mem_rusage_total_add_fn_t)(unsigned long bytes);
typedef void (*mem_numa_init_log_fn_t)(int event, int node,
		int linux_numa_id, int type, unsigned long start,
		unsigned long end, unsigned long bytes, int pages,
		int rbtree_allocator);
typedef void (*mem_numa_panic_fn_t)(int node);
typedef int (*mem_rusage_check_oom_fn_t)(int numa_id, int npages,
		int is_user);
typedef unsigned long (*mem_numa_alloc_node_fn_t)(
		struct ihk_mc_numa_node *node, int npages, int p2align);
typedef int (*mem_current_numa_id_fn_t)(void);
typedef struct ihk_dump_page_set *(*mem_dump_get_page_set_fn_t)(void);
typedef struct ihk_dump_page *(*mem_dump_get_page_fn_t)(void);
typedef void (*mem_dump_query_fn_t)(void *arg);
typedef void (*mem_dump_log_fn_t)(void);
typedef unsigned long (*mem_dump_chunk_count_fn_t)(int node);
typedef void *(*mem_dump_chunk_iter_fn_t)(int node);
typedef void *(*mem_dump_next_chunk_fn_t)(void *chunk);
typedef unsigned long (*mem_dump_chunk_field_fn_t)(void *chunk);
typedef void (*mem_dump_warn_fn_t)(int kind, unsigned long map_count,
		unsigned long map_index, unsigned long map_start,
		unsigned long map_end, unsigned long page_index);
typedef int (*mem_chk_page_address_fn_t)(unsigned long phys);
typedef pte_t *(*mem_lookup_pte_fn_t)(page_table_t pt, void *virt,
		int pgshift, void **basep, size_t *sizep, int *p2alignp);
typedef int (*mem_page_fault_process_vm_fn_t)(struct process_vm *vm,
		void *virt, unsigned long reason);
typedef void (*mem_fault_log_fn_t)(void *virt);
typedef int (*mem_phys_to_nid_fn_t)(unsigned long phys);
typedef int (*mem_pte_visitor_fn_t)(void *arg, page_table_t pt, pte_t *ptep,
		void *pgaddr, int pgshift);
typedef int (*mem_visit_pte_range_fn_t)(page_table_t pt, void *start,
		void *end, int pgshift, enum visit_pte_flag flags,
		mem_pte_visitor_fn_t funcp, void *arg);
typedef void *(*mem_register_alloc_fn_t)(int size, ihk_mc_ap_flag flag);
typedef void (*mem_register_free_fn_t)(void *ptr);
typedef void *(*mem_vmap_init_fn_t)(unsigned long start,
		unsigned long size, unsigned long unit);
typedef int (*mem_pt_prepare_map_fn_t)(page_table_t pt, void *virt,
		unsigned long size, enum ihk_mc_pt_prepare_flag flag);
typedef unsigned long (*mem_vmap_alloc_fn_t)(void *desc, int npages,
		int p2align);
typedef void (*mem_vmap_free_fn_t)(void *desc, unsigned long address,
		int npages);
typedef int (*mem_pt_set_page_fn_t)(page_table_t pt, void *virt,
		unsigned long phys, enum ihk_mc_pt_attribute attr);
typedef int (*mem_pt_clear_page_fn_t)(page_table_t pt, void *virt);
typedef void (*mem_flush_tlb_single_fn_t)(unsigned long addr);
typedef void (*mem_flush_tlb_all_fn_t)(void);
typedef unsigned long (*mem_rdtsc_fn_t)(void);
typedef unsigned long (*mem_irq_save_fn_t)(void);
typedef void (*mem_irq_restore_fn_t)(unsigned long flags);
typedef int (*mem_current_cpu_fn_t)(void);
typedef void (*mem_interrupt_cpu_fn_t)(int cpu, int vector);
typedef void (*mem_noirq_lock_fn_t)(unsigned long lock_addr);
typedef void (*mem_atomic_set_fn_t)(unsigned long atomic_addr, int value);
typedef void (*mem_atomic_inc_fn_t)(unsigned long atomic_addr);
typedef void (*mem_atomic_dec_fn_t)(unsigned long atomic_addr);
typedef int (*mem_atomic_read_fn_t)(unsigned long atomic_addr);
typedef void (*mem_pause_fn_t)(void);
typedef struct cpu_local_var *(*mem_get_this_cpu_local_var_fn_t)(void);

#define MEM_ALLOC_LOG_EXPLICIT_OK 1
#define MEM_ALLOC_LOG_EXPLICIT_MISS 2
#define MEM_ALLOC_LOG_POLICY_OK 3
#define MEM_ALLOC_LOG_POLICY_MISS 4
#define MEM_ALLOC_LOG_DISTANCE_OK 5
#define MEM_ALLOC_LOG_DISTANCE_FIRST_MISS 6
#define MEM_ALLOC_LOG_OOM 7
#define MEM_INIT_LOG_ANON_ON_DEMAND 1
#define MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE 2
#define MEM_INIT_LOG_HUGETLBFS_ON_DEMAND 3
#define MEM_NUMA_INIT_LOG_CHUNK 1
#define MEM_NUMA_INIT_LOG_NODE 2

extern int cpu_local_var_initialized;

int mem_current_numa_id_bridge(void);





extern int mem_set_page_allocator_result(struct ihk_mc_pa_ops **pa_ops_slot,
		struct ihk_mc_pa_ops *ops,
		mem_lifecycle_void_fn_t pagealloc_track_init_fn,
		mem_lifecycle_void_fn_t early_alloc_invalidate_fn);
extern int mem_register_kmalloc_result(struct ihk_mc_pa_ops *allocator,
		int memdebug_present, mem_register_alloc_fn_t debug_alloc_fn,
		mem_register_free_fn_t debug_free_fn,
		mem_register_alloc_fn_t base_alloc_fn,
		mem_register_free_fn_t base_free_fn);
extern int mem_virtual_allocator_init_body_result(void **vmap_allocator_slot,
		unsigned long start, unsigned long size, unsigned long unit,
		int first_level, mem_vmap_init_fn_t pagealloc_init_fn,
		mem_pt_prepare_map_fn_t pt_prepare_map_fn);
extern void *mem_map_virtual_body_result(void *vmap_allocator,
		unsigned long phys, int npages, unsigned long attr,
		mem_vmap_alloc_fn_t pagealloc_alloc_fn,
		mem_pt_set_page_fn_t pt_set_page_fn,
		mem_pt_clear_page_fn_t pt_clear_page_fn,
		mem_vmap_free_fn_t pagealloc_free_fn,
		mem_flush_tlb_single_fn_t flush_tlb_single_fn,
		mem_lifecycle_void_fn_t barrier_fn);
extern int mem_unmap_virtual_body_result(void *vmap_allocator, void *va,
		int npages, mem_pt_clear_page_fn_t pt_clear_page_fn,
		mem_flush_tlb_single_fn_t flush_tlb_single_fn,
		mem_vmap_free_fn_t pagealloc_free_fn);
extern int mem_init_sequence_result(struct ihk_mc_pa_ops *allocator_ops,
		unsigned long page_fault_handler_addr,
		unsigned long query_free_mem_handler_addr,
		int *anon_on_demand_flag, int *xpmem_remote_flag,
		int *hugetlbfs_on_demand_flag,
		mem_lifecycle_void_fn_t monitor_init_fn,
		mem_lifecycle_void_fn_t rusage_init_fn,
		mem_lifecycle_void_fn_t numa_init_fn,
		mem_set_page_allocator_fn_t set_page_allocator_fn,
		mem_set_page_fault_handler_fn_t set_page_fault_handler_fn,
		mem_get_vector_fn_t get_vector_fn,
		mem_register_interrupt_handler_fn_t register_interrupt_handler_fn,
		mem_lifecycle_void_fn_t page_init_fn,
		mem_lifecycle_void_fn_t virtual_allocator_init_fn,
		mem_find_command_line_fn_t find_command_line_fn,
		mem_lifecycle_void_fn_t numa_distances_init_fn,
		mem_init_log_fn_t log_fn);
extern int mem_numa_distances_init_result(struct ihk_mc_numa_node *memory_nodes,
		int nr_nodes, mem_numa_distance_alloc_fn_t alloc_pages_fn,
		mem_numa_distance_fn_t get_distance_fn,
		mem_numa_distance_alloc_fail_log_fn_t alloc_fail_log_fn,
		mem_numa_distance_log_fn_t distances_log_fn);
extern int mem_numa_distances_init_public_result(
		struct ihk_mc_numa_node *memory_nodes,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_numa_distance_alloc_fn_t alloc_pages_fn,
		mem_numa_distance_fn_t get_distance_fn,
		mem_numa_distance_alloc_fail_log_fn_t alloc_fail_log_fn,
		mem_numa_distance_log_fn_t distances_log_fn);
extern int mem_rusage_init_body_result(struct rusage_global *rusage,
		unsigned long rusage_size,
		mem_get_cpu_info_fn_t get_cpu_info_fn,
		mem_get_nr_numa_nodes_fn_t nr_numa_nodes_fn,
		mem_get_ns_per_tsc_fn_t ns_per_tsc_fn,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_set_rusage_fn_t set_rusage_fn,
		mem_lifecycle_void_fn_t panic_fn,
		mem_rusage_init_log_fn_t log_fn);
extern int mem_numa_init_body_result(struct ihk_mc_numa_node *memory_nodes,
		int nr_nodes, int nr_chunks, int rbtree_allocator,
		unsigned long last_early_heap_phys,
		mem_get_numa_node_info_fn_t get_numa_node_fn,
		mem_get_memory_chunk_fn_t get_memory_chunk_fn,
		mem_numa_node_init_fn_t node_init_fn,
		mem_numa_add_free_pages_fn_t add_free_pages_fn,
		mem_page_allocator_init_fn_t page_allocator_init_fn,
		mem_numa_list_allocator_fn_t list_allocator_fn,
		mem_pagealloc_count_fn_t pagealloc_count_fn,
		mem_rusage_total_add_fn_t rusage_total_add_fn,
		mem_numa_init_log_fn_t log_fn,
		mem_numa_panic_fn_t panic_fn);
extern unsigned long mem_try_alloc_node_result(
		struct ihk_mc_numa_node *memory_nodes, int nr_nodes,
		int numa_id, int npages, int p2align, int is_user, int *oomp,
		mem_rusage_check_oom_fn_t rusage_check_oom_fn,
		mem_numa_alloc_node_fn_t numa_alloc_fn);
extern unsigned long mem_try_alloc_node_public_result(
		struct ihk_mc_numa_node *memory_nodes, int numa_id, int npages,
		int p2align, int is_user, int *oomp,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_rusage_check_oom_fn_t rusage_check_oom_fn,
		mem_numa_alloc_node_fn_t numa_alloc_fn);
extern int mem_distance_id_result(struct ihk_mc_numa_node *memory_nodes,
		int nr_nodes, int base_node, int index);
extern int mem_distance_id_public_result(
		struct ihk_mc_numa_node *memory_nodes, int base_node, int index,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn);
extern struct ihk_mc_numa_node *mem_get_numa_node_by_distance_result(
		struct ihk_mc_numa_node *memory_nodes, int nr_nodes,
		int cpu_local_initialized, int index,
		mem_current_numa_id_fn_t current_numa_id_fn);
extern struct ihk_mc_numa_node *mem_get_numa_node_by_distance_public_result(
		struct ihk_mc_numa_node *memory_nodes, int cpu_local_initialized,
		int index, mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_current_numa_id_fn_t current_numa_id_fn);
extern struct ihk_mc_numa_node *mem_get_numa_node_public_result(
		struct ihk_mc_numa_node *memory_nodes, int nr_nodes, int numa_id);
extern int mem_chk_page_address_result(unsigned long mem_addr,
		mem_get_nr_memory_chunks_fn_t nr_chunks_fn,
		mem_get_memory_chunk_fn_t chunk_fn);
extern int mem_clear_dump_page_completion_result(
		mem_dump_get_page_set_fn_t get_page_set_fn);
extern int mem_dump_mark_range_result(struct dump_pase_info *dump_pase_info,
		unsigned long chunk_addr, unsigned long chunk_size, int warn_kind,
		mem_dump_warn_fn_t warn_fn);
extern int mem_get_mem_user_page_result(struct dump_pase_info *dump_pase_info,
		unsigned long *ptep, int pgshift,
		mem_chk_page_address_fn_t chk_page_address_fn,
		mem_dump_warn_fn_t warn_fn);
extern unsigned long mem_dump_free_pages_public_result(
		struct ihk_mc_numa_node *memory_nodes, int node,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn);
extern void *mem_dump_first_free_chunk_public_result(
		struct ihk_mc_numa_node *memory_nodes, int node,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn);
extern void *mem_dump_next_free_chunk_result(void *chunk);
extern unsigned long mem_dump_chunk_addr_result(void *chunk);
extern unsigned long mem_dump_chunk_size_result(void *chunk);
extern int mem_query_mem_free_page_result(struct dump_pase_info *dump_pase_info,
		int nr_nodes, mem_dump_chunk_count_fn_t free_pages_fn,
		mem_dump_chunk_iter_fn_t first_chunk_fn,
		mem_dump_next_chunk_fn_t next_chunk_fn,
		mem_dump_chunk_field_fn_t chunk_addr_fn,
		mem_dump_chunk_field_fn_t chunk_size_fn,
		mem_dump_warn_fn_t warn_fn);
extern int mem_query_mem_free_page_public_result(
		struct dump_pase_info *dump_pase_info,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_dump_chunk_count_fn_t free_pages_fn,
		mem_dump_chunk_iter_fn_t first_chunk_fn,
		mem_dump_next_chunk_fn_t next_chunk_fn,
		mem_dump_chunk_field_fn_t chunk_addr_fn,
		mem_dump_chunk_field_fn_t chunk_size_fn,
		mem_dump_warn_fn_t warn_fn);
extern int mem_query_mem_user_page_result(struct list_head *process_hash_lists,
		int hash_size, unsigned long process_hash_list_offset,
		unsigned long process_vm_offset,
		unsigned long vm_address_space_offset,
		unsigned long address_space_page_table_offset,
		unsigned long user_end,
		mem_visit_pte_range_fn_t visit_pte_range_fn,
		mem_pte_visitor_fn_t pte_visitor_fn, void *dump_pase_info);
extern int mem_query_mem_areas_result(int current_cpu, int nr_cpus,
		int dump_level, mem_dump_get_page_set_fn_t get_page_set_fn,
		mem_dump_get_page_fn_t get_page_fn,
		mem_dump_query_fn_t query_user_fn,
		mem_dump_query_fn_t query_free_fn,
		mem_dump_log_fn_t log_fn);
extern void *mem_pa_alloc_aligned_pages_node_result(
		struct ihk_mc_pa_ops *ops, int npages, int p2align,
		ihk_mc_ap_flag flag, int node, int is_user,
		uintptr_t virt_addr, mem_early_alloc_pages_fn_t early_alloc_fn);
extern void *mem_pa_alloc_pages_result(struct ihk_mc_pa_ops *ops,
		int npages, ihk_mc_ap_flag flag, int is_user,
		mem_early_alloc_pages_fn_t early_alloc_fn);
extern void mem_pa_free_pages_result(struct ihk_mc_pa_ops *ops, void *ptr,
		int npages, int is_user);
extern int mem_reserve_pages_body_result(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long allocator_start, unsigned long allocator_end,
		unsigned long start, unsigned long end,
		mem_reserve_log_fn_t log_fn,
		mem_reserve_range_fn_t reserve_fn);
extern int mem_reserve_pages_public_body_result(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long allocator_start, unsigned long allocator_end,
		unsigned long start, unsigned long end,
		mem_reserve_log_fn_t log_fn,
		mem_reserve_range_fn_t reserve_fn,
		mem_reserve_pages_body_fn_t reserve_body_fn,
		mem_lifecycle_void_fn_t panic_fn);
extern int mem_begin_free_pages_pending_result(struct list_head *pendings);
extern int mem_begin_free_pages_pending_body_result(struct list_head *pendings,
		mem_begin_free_pages_pending_fn_t begin_fn,
		mem_lifecycle_void_fn_t panic_fn);
extern int mem_begin_free_pages_pending_public_body_result(
		mem_pending_pages_fn_t pending_pages_fn,
		mem_begin_free_pages_pending_fn_t begin_fn,
		mem_lifecycle_void_fn_t panic_fn);
extern int mem_free_pages_pending_enqueue_result(struct page *page,
		struct list_head *pendings, int npages,
		mem_pending_warn_fn_t warn_fn);
extern int mem_finish_free_pages_pending_result(struct list_head *pendings,
		mem_pending_free_fn_t free_fn);
extern int mem_finish_free_pages_pending_body_result(struct list_head *pendings,
		mem_finish_free_pages_pending_fn_t finish_fn,
		mem_pending_free_fn_t free_fn, mem_lifecycle_void_fn_t panic_fn);
extern int mem_finish_free_pages_pending_public_body_result(
		mem_pending_pages_fn_t pending_pages_fn,
		mem_finish_free_pages_pending_fn_t finish_fn,
		mem_pending_free_fn_t free_fn,
		mem_lifecycle_void_fn_t panic_fn);
extern int mem_free_pages_in_allocator_rbtree_result(void *va, int npages,
		int is_user, mem_get_nr_memory_chunks_fn_t nr_chunks_fn,
		mem_get_memory_chunk_fn_t chunk_fn,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_get_numa_node_fn_t numa_node_fn,
		mem_numa_free_fn_t numa_free_fn,
		mem_rusage_sub_fn_t rusage_sub_fn);
extern void *mem_mckernel_alloc_policy_result(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user,
		int current_node, int nr_nodes, int numa_mem_policy,
		int chk_shm, unsigned long *numa_mask, int *il_prevp,
		mem_try_alloc_node_fn_t try_alloc_fn,
		mem_distance_id_fn_t distance_id_fn,
		mem_mask_test_fn_t mask_test_fn,
		mem_interleave_next_fn_t interleave_next_fn,
		mem_rusage_add_fn_t rusage_add_fn,
		mem_phys_to_virt_fn_t phys_to_virt_fn,
		mem_alloc_log_fn_t log_fn);
extern int mem_mask_test_result(int numa_id, unsigned long *numa_mask,
		int nr_bits);
extern int mem_interleave_nodes_result(int off, unsigned long *numa_mask,
		int nr_bits);
extern int mem_range_is_shm_result(int has_range, int has_memobj,
		unsigned long memobj_flags);
extern int mem_policy_fields_result(int has_policy, int policy,
		unsigned long *mask, int *il_prev_in,
		int *numa_mem_policy, unsigned long **numa_mask,
		int **il_prev);
extern void *mem_current_vm_result(int cpu_local_initialized, void *current,
		void *vm);
extern int mem_default_alloc_policy_result(ihk_mc_ap_flag flag,
		ihk_mc_ap_flag *policy_flag, int *policy_pref_node,
		int *numa_mem_policy);
extern int mem_alloc_policy_should_try_policy_result(int pref_node,
		ihk_mc_ap_flag flag, int numa_mem_policy, int chk_shm);
extern int mem_alloc_node_id_valid_result(int node, int nr_nodes);
extern int mem_alloc_policy_inputs_valid_result(int npages, int nr_nodes,
		int has_try_alloc, int has_rusage_add, int has_phys_to_virt);
extern int mem_alloc_order_node_result(int current_node, int offset,
		int nr_nodes);
extern void *mem_mckernel_allocate_aligned_pages_node_body_result(
		int npages, int p2align, ihk_mc_ap_flag flag, int pref_node,
		int is_user, uintptr_t virt_addr, int cpu_local_initialized,
		int nr_nodes, mem_current_vm_fn_t current_vm_fn,
		mem_range_policy_search_fn_t range_policy_search_fn,
		mem_lookup_memory_range_fn_t lookup_memory_range_fn,
		mem_range_is_shm_fn_t range_is_shm_fn,
		mem_policy_fields_fn_t range_policy_fields_fn,
		mem_policy_fields_fn_t vm_policy_fields_fn,
		mem_current_numa_id_fn_t current_numa_id_fn,
		mem_mckernel_alloc_policy_fn_t alloc_policy_fn);
extern void *mem_mckernel_allocate_aligned_pages_node_public_body_result(
		int npages, int p2align, ihk_mc_ap_flag flag, int pref_node,
		int is_user, uintptr_t virt_addr, int cpu_local_initialized,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_current_vm_fn_t current_vm_fn,
		mem_range_policy_search_fn_t range_policy_search_fn,
		mem_lookup_memory_range_fn_t lookup_memory_range_fn,
		mem_range_is_shm_fn_t range_is_shm_fn,
		mem_policy_fields_fn_t range_policy_fields_fn,
		mem_policy_fields_fn_t vm_policy_fields_fn,
		mem_current_numa_id_fn_t current_numa_id_fn,
		mem_mckernel_alloc_policy_fn_t alloc_policy_fn);
extern int mem_mckernel_free_pages_body_result(void *va, int npages,
		int is_user, struct list_head *pendings,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_phys_to_page_fn_t phys_to_page_fn,
		mem_free_in_allocator_fn_t free_in_allocator_fn,
		mem_pending_warn_fn_t warn_fn);
extern int mem_mckernel_free_pages_public_body_result(void *va, int npages,
		int is_user, mem_pending_pages_fn_t pending_pages_fn,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_phys_to_page_fn_t phys_to_page_fn,
		mem_free_in_allocator_fn_t free_in_allocator_fn,
		mem_pending_warn_fn_t warn_fn,
		mem_mckernel_free_pages_body_fn_t free_body_fn);
extern int mem_query_free_mem_interrupt_body_result(int nr_nodes,
		char *memdebug_name, int fugaku_panic, int attached_mic,
		int sbox_scratch0, int sbox_scratch1,
		mem_query_free_node_pages_fn_t node_pages_fn,
		mem_query_free_log_fn_t total_log_fn,
		mem_lifecycle_void_fn_t panic_fn,
		mem_find_command_line_fn_t find_command_line_fn,
		mem_lifecycle_void_fn_t kmalloc_memcheck_fn,
		mem_lifecycle_void_fn_t pagealloc_memcheck_fn,
		mem_query_page_hash_count_fn_t page_hash_count_fn,
		mem_query_free_log_fn_t page_hash_log_fn,
		mem_query_sbox_write_fn_t sbox_write_fn);
extern int mem_query_free_mem_interrupt_public_body_result(void *priv,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn, char *memdebug_name,
		int fugaku_panic, int attached_mic, int sbox_scratch0,
		int sbox_scratch1, mem_query_free_node_pages_fn_t node_pages_fn,
		mem_query_free_log_fn_t total_log_fn,
		mem_lifecycle_void_fn_t panic_fn,
		mem_find_command_line_fn_t find_command_line_fn,
		mem_lifecycle_void_fn_t kmalloc_memcheck_fn,
		mem_lifecycle_void_fn_t pagealloc_memcheck_fn,
		mem_query_page_hash_count_fn_t page_hash_count_fn,
		mem_query_free_log_fn_t page_hash_log_fn,
		mem_query_sbox_write_fn_t sbox_write_fn);
extern pte_t *mem_pt_lookup_fault_pte_body_result(struct process_vm *vm,
		void *virt, int pgshift, void **basep, size_t *sizep,
		int *p2alignp, unsigned long address_space_offset,
		unsigned long page_table_offset,
		mem_lookup_pte_fn_t lookup_pte_fn,
		mem_page_fault_process_vm_fn_t page_fault_fn,
		mem_fault_log_fn_t log_fn);
	extern int mem_lookup_node_body_result(struct process_vm *vm, void *addr,
			unsigned long address_space_offset,
			unsigned long page_table_offset,
			mem_lookup_pte_fn_t lookup_pte_fn,
			mem_page_fault_process_vm_fn_t page_fault_fn,
			mem_phys_to_nid_fn_t phys_to_nid_fn);
	extern int mem_remote_flush_tlb_array_body_result(
			struct process_vm *vm, unsigned long *addr, int nr_addr,
			int cpu_id, struct tlb_flush_entry *tlb_flush_vector,
			int vector_size, int vector_start, int cpu_set_bits,
			mem_rdtsc_fn_t rdtsc_fn,
			mem_current_cpu_fn_t current_cpu_fn,
			mem_get_vector_fn_t get_vector_fn,
			mem_interrupt_cpu_fn_t interrupt_cpu_fn,
			mem_noirq_lock_fn_t lock_fn,
			mem_noirq_lock_fn_t unlock_fn,
			mem_atomic_set_fn_t atomic_set_fn,
			mem_atomic_inc_fn_t atomic_inc_fn,
			mem_atomic_read_fn_t atomic_read_fn,
			mem_flush_tlb_single_fn_t flush_single_fn,
			mem_flush_tlb_all_fn_t flush_all_fn,
			mem_pause_fn_t pause_fn);
	extern int mem_tlb_flush_handler_body_result(int vector,
			struct tlb_flush_entry *tlb_flush_vector, int vector_size,
			int vector_start, mem_irq_save_fn_t irq_save_fn,
			mem_irq_restore_fn_t irq_restore_fn,
			mem_flush_tlb_single_fn_t flush_single_fn,
			mem_flush_tlb_all_fn_t flush_all_fn,
			mem_atomic_dec_fn_t atomic_dec_fn);











































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































extern unsigned long ihk_mc_get_ns_per_tsc(void);

/*
 * Page allocator tracking routines
 */

#define PAGEALLOC_TRACK_HASH_SHIFT  (8)
#define PAGEALLOC_TRACK_HASH_SIZE   (1 << PAGEALLOC_TRACK_HASH_SHIFT)
#define PAGEALLOC_TRACK_HASH_MASK   (PAGEALLOC_TRACK_HASH_SIZE - 1)


extern struct list_head pagealloc_track_hash[PAGEALLOC_TRACK_HASH_SIZE];




extern ihk_spinlock_t pagealloc_track_hash_locks[PAGEALLOC_TRACK_HASH_SIZE];





extern struct list_head pagealloc_addr_hash[PAGEALLOC_TRACK_HASH_SIZE];




extern ihk_spinlock_t pagealloc_addr_hash_locks[PAGEALLOC_TRACK_HASH_SIZE];





extern int pagealloc_track_initialized;




extern int pagealloc_runcount;




struct pagealloc_track_addr_entry {
	void *addr;
	int runcount;
	struct list_head list; /* track_entry's list */
	struct pagealloc_track_entry *entry;
	struct list_head hash; /* address hash */
	int npages;
};

struct pagealloc_track_entry {
	char *file;
	int line;
	ihk_atomic_t alloc_count;
	struct list_head hash;
	struct list_head addr_list;
	ihk_spinlock_t addr_list_lock;
};


typedef void *(*mem_pagealloc_base_alloc_fn_t)(int, int, ihk_mc_ap_flag,
		int, int, uintptr_t);
typedef void (*mem_pagealloc_base_free_fn_t)(void *, int, int);
typedef void *(*mem_pagealloc_meta_alloc_fn_t)(int, ihk_mc_ap_flag);
typedef void (*mem_pagealloc_meta_free_fn_t)(void *);
typedef unsigned long (*mem_pagealloc_track_lock_fn_t)(unsigned long);
typedef void (*mem_pagealloc_track_unlock_fn_t)(unsigned long,
		unsigned long);
typedef void (*mem_pagealloc_track_noirq_lock_fn_t)(unsigned long);
typedef void (*mem_pagealloc_track_noirq_unlock_fn_t)(unsigned long);
typedef void (*mem_pagealloc_track_spin_init_fn_t)(unsigned long);
typedef void (*mem_pagealloc_track_log_fn_t)(int, void *, char *, int, int);
typedef void (*mem_pagealloc_invalid_free_fn_t)(void *, char *, int);
typedef void (*mem_pagealloc_invalid_size_fn_t)(void *, int, int, char *,
		int);
typedef void (*mem_track_leak_log_fn_t)(int, void *, char *, int, int,
		int, int);

#define PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED 1
#define PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED 2
#define PAGEALLOC_TRACK_LOG_ENTRY_ADDED 3
#define PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED 4
#define PAGEALLOC_TRACK_LOG_ADDR_ADDED 5
#define PAGEALLOC_TRACK_LOG_ADDR_REMOVED 6
#define PAGEALLOC_TRACK_LOG_ENTRY_REMOVED 7
#define PAGEALLOC_TRACK_LOG_COVERING_FOUND 8
#define PAGEALLOC_TRACK_LOG_ADDR_NEXT_ADDED 9
#define PAGEALLOC_TRACK_LOG_ADDR_MODIFIED 10
#define MEM_TRACK_LEAK_DETAIL 1
#define MEM_TRACK_LEAK_SUMMARY 2

extern int mem_track_hashes_init_result(int *initialized,
		struct list_head *track_hash, ihk_spinlock_t *track_locks,
		struct list_head *addr_hash, ihk_spinlock_t *addr_locks,
		int hash_size, mem_pagealloc_track_spin_init_fn_t spin_init_fn);
extern struct pagealloc_track_entry *pagealloc_track_find_entry_result(
		char *file, int line, struct list_head *track_hash);
extern void *pagealloc_track_alloc_result(int npages, int p2align,
		ihk_mc_ap_flag flag, int node, int is_user,
		uintptr_t virt_addr, char *file, int line, char *memdebug,
		int track_initialized, struct list_head *track_hash,
		ihk_spinlock_t *track_locks, struct list_head *addr_hash,
		ihk_spinlock_t *addr_locks, int runcount,
		mem_pagealloc_base_alloc_fn_t base_alloc_fn,
		mem_pagealloc_meta_alloc_fn_t meta_alloc_fn,
		mem_pagealloc_meta_free_fn_t meta_free_fn,
		mem_pagealloc_track_lock_fn_t lock_fn,
		mem_pagealloc_track_unlock_fn_t unlock_fn,
		mem_pagealloc_track_spin_init_fn_t spin_init_fn,
		mem_pagealloc_track_log_fn_t log_fn);
extern int pagealloc_track_free_result(void *ptr, int npages, int is_user,
		char *file, int line, char *memdebug, int track_initialized,
		struct list_head *track_hash, ihk_spinlock_t *track_locks,
		struct list_head *addr_hash, ihk_spinlock_t *addr_locks,
		mem_pagealloc_base_free_fn_t base_free_fn,
		mem_pagealloc_meta_alloc_fn_t meta_alloc_fn,
		mem_pagealloc_meta_free_fn_t meta_free_fn,
		mem_pagealloc_track_lock_fn_t lock_fn,
		mem_pagealloc_track_unlock_fn_t unlock_fn,
		mem_pagealloc_track_noirq_lock_fn_t noirq_lock_fn,
		mem_pagealloc_track_noirq_unlock_fn_t noirq_unlock_fn,
		mem_pagealloc_invalid_free_fn_t invalid_free_fn,
		mem_pagealloc_invalid_size_fn_t invalid_size_fn,
		mem_pagealloc_track_log_fn_t log_fn);
extern int pagealloc_memcheck_result(struct list_head *track_hash,
		ihk_spinlock_t *track_locks, int *runcount, int hash_size,
		mem_pagealloc_track_lock_fn_t lock_fn,
		mem_pagealloc_track_unlock_fn_t unlock_fn,
		mem_pagealloc_track_noirq_lock_fn_t noirq_lock_fn,
		mem_pagealloc_track_noirq_unlock_fn_t noirq_unlock_fn,
		mem_track_leak_log_fn_t log_fn);

extern void *mem_pagealloc_track_base_alloc_bridge(int npages, int p2align,
		ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr);

extern void mem_pagealloc_track_base_free_bridge(void *ptr, int npages,
		int is_user);

extern void *mem_pagealloc_track_meta_alloc_bridge(int size,
		ihk_mc_ap_flag flag);

extern void mem_pagealloc_track_meta_free_bridge(void *ptr);

extern unsigned long mem_pagealloc_track_lock_bridge(unsigned long lock_addr);

extern void mem_pagealloc_track_unlock_bridge(unsigned long lock_addr,
		unsigned long irqflags);

extern void mem_pagealloc_track_noirq_lock_bridge(unsigned long lock_addr);

extern void mem_pagealloc_track_noirq_unlock_bridge(unsigned long lock_addr);

extern void mem_pagealloc_track_spin_init_bridge(unsigned long lock_addr);


extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_0;








extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_1;








extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_2;








extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_3;








extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_4;








extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_5;








extern struct ddebug mem_pagealloc_track_log_bridge_debug_record_6;







struct mem_pagealloc_track_log_bridge_debug_metadata {
 struct ddebug *records[7];
 unsigned long flags_byte;
};

extern const struct mem_pagealloc_track_log_bridge_debug_metadata mem_pagealloc_track_log_bridge_debug_metadata;





extern void mem_pagealloc_track_log_bridge(int event, void *ptr, char *file,
		int line, int npages);

extern void mem_pagealloc_invalid_free_bridge(void *ptr, char *file, int line);

extern void mem_pagealloc_invalid_size_bridge(void *ptr, int npages,
		int alloc_npages, char *file, int line);


extern struct ddebug mem_pagealloc_leak_log_bridge_debug_record_0;







struct mem_pagealloc_leak_log_bridge_debug_metadata {
 struct ddebug *records[1];
 unsigned long flags_byte;
};

extern const struct mem_pagealloc_leak_log_bridge_debug_metadata mem_pagealloc_leak_log_bridge_debug_metadata;





extern void mem_pagealloc_leak_log_bridge(int event, void *ptr, char *file,
		int line, int size, int count, int runcount);


struct dump_pase_info {
	struct ihk_dump_page_set *dump_page_set;
	struct ihk_dump_page *dump_pages;
};

/** Get the index in the map array */
#define MAP_INDEX(n)    ((n) >> 6)
/** Get the bit number in a map element */
#define MAP_BIT(n)      ((n) & 0x3f)












































































































































































































































































































extern void pagealloc_track_init(void);

















/* NOTE: Hash lock must be held */

extern struct pagealloc_track_entry *__pagealloc_track_find_entry(
		char *file, int line);




























/* Top level routines called from macros */

extern void *_ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
	ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr,
	char *file, int line);




















































































extern void _ihk_mc_free_pages(void *ptr, int npages, int is_user,
                        char *file, int line);







































































































































































































































extern void pagealloc_memcheck(void);

















































/* Actual allocation routines */






























/* Internal allocation routines */

/* Actual GCC9 ddebug witness22c1; default GCC14 qualification remains pending. */

extern struct ddebug mem_reserve_pages_debug_record;








extern const struct {
 struct ddebug *record;
 unsigned long flags_byte;
} mem_reserve_pages_debug_metadata;






extern void mem_reserve_pages_log_bridge(unsigned long start,
		unsigned long end, unsigned long pages);










extern void mem_reserve_pages_range_bridge(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long start, unsigned long end);










extern void mem_reserve_pages_panic_bridge(void);








extern void reserve_pages(struct ihk_page_allocator_desc *pa_allocator,
		unsigned long start, unsigned long end, int type);
















/* Compiler-bound existing process NUMA mask extent, no C behavior/getter. */

extern const int mem_interleave_nodes_mask_bits;



int interleave_nodes(int off, unsigned long *numa_mask);


































static unsigned long mem_try_alloc_node_bridge(int numa_id, int npages,
		int p2align, int is_user, int *oomp)
{






	unsigned long pa = 0;
	struct ihk_page_allocator_desc *pa_allocator;

	if (oomp)
		*oomp = 0;
	if (numa_id < 0 || numa_id >= ihk_mc_get_nr_numa_nodes())
		return 0;
	if (rusage_check_oom(numa_id, npages, is_user) == -ENOMEM) {
		if (oomp)
			*oomp = 1;
		return 0;
	}

	for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[numa_id].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[numa_id].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {
		pa = ihk_pagealloc_alloc(pa_allocator, npages, p2align);
		if (pa)
			break;
	}

	return pa;

}


extern int mem_distance_id_bridge(int base_node, int index);

extern int mem_mask_test_bridge(int numa_id, unsigned long *numa_mask);


void mem_rusage_page_add_bridge(int numa_id, int npages, int is_user);








void *mem_phys_to_virt_bridge(unsigned long pa);







/* Exact C feature/enum facts and callsite-owned mutable debug records. */

_Static_assert(__builtin_types_compatible_p(enum profile_event_type,unsigned int),
 "profile event unsigned int ABI");


extern struct ddebug mem_allocation_log_record_0;








extern struct ddebug mem_allocation_log_record_1;








extern struct ddebug mem_allocation_log_record_2;








extern struct ddebug mem_allocation_log_record_3;








extern struct ddebug mem_allocation_log_record_4;















extern struct ddebug mem_allocation_log_record_6;








extern const struct {
 struct ddebug *records[7];
 unsigned long flags_byte;
 void (*profile_add)(unsigned int,uint64_t);
 unsigned int profile_event;
 int fugaku;
} mem_allocation_log_metadata;






























extern void mem_mckernel_alloc_log_bridge(int event, int current_node,
		int numa_id, int npages);


extern void *mem_current_vm_bridge(void);

extern void *mem_range_policy_search_bridge(void *vm, unsigned long virt_addr);

extern void *mem_lookup_memory_range_bridge(void *vm, unsigned long start,
		unsigned long end);

extern int mem_range_is_shm_bridge(void *range);

extern void mem_range_policy_fields_bridge(void *policy,
		int *numa_mem_policy, unsigned long **numa_mask, int **il_prev);

extern void mem_vm_policy_fields_bridge(void *vm, int *numa_mem_policy,
		unsigned long **numa_mask, int **il_prev);

struct mem_remaining_alloc_policy_metadata {
 mem_try_alloc_node_fn_t try_alloc;
 mem_rusage_add_fn_t rusage_add;
 mem_phys_to_virt_fn_t phys_to_virt;
 mem_alloc_log_fn_t log;
};

extern const struct mem_remaining_alloc_policy_metadata mem_remaining_alloc_policy_metadata;






extern void *mem_mckernel_alloc_policy_bridge(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user,
		int current_node, int nr_nodes, int numa_mem_policy,
		int chk_shm, unsigned long *numa_mask, int *il_prevp);



struct mem_whole_allocation_metadata {
 mem_get_nr_numa_nodes_fn_t nr_nodes;
 mem_current_vm_fn_t current_vm;
 mem_range_policy_search_fn_t range_policy_search;
 mem_lookup_memory_range_fn_t lookup_memory_range;
 mem_range_is_shm_fn_t range_is_shm;
 mem_policy_fields_fn_t range_policy_fields;
 mem_policy_fields_fn_t vm_policy_fields;
 mem_current_numa_id_fn_t current_numa;
 mem_mckernel_alloc_policy_fn_t alloc_policy;
};

extern const struct mem_whole_allocation_metadata mem_whole_allocation_metadata;













void *mckernel_allocate_aligned_pages_node(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user, uintptr_t virt_addr);





















































































extern int mem_current_numa_id_bridge(void);

/*
 * Get NUMA node structure offsetted by index in the order of distance
 */

struct ihk_mc_numa_node *ihk_mc_get_numa_node_by_distance(int i);

















unsigned long mem_virt_to_phys_bridge(void *va);







extern void *mem_get_numa_node_bridge(int numa_id);


void mem_numa_free_bridge(void *node, unsigned long addr, int npages);








void mem_rusage_page_sub_bridge(int numa_id, int npages, int is_user);









void __mckernel_free_pages_in_allocator(void *va, int npages,
                                               int is_user);


















































extern void mem_pending_free_warn_bridge(unsigned long phys);


extern struct page *mem_phys_to_page_bridge(unsigned long phys);








void mem_free_in_allocator_bridge(void *va, int npages, int is_user);







extern struct list_head *mem_pending_free_pages_bridge(void);



struct mem_whole_free_metadata {
 mem_pending_pages_fn_t pending_pages;
 mem_virt_to_phys_fn_t virt_to_phys;
 mem_phys_to_page_fn_t phys_to_page;
 mem_free_in_allocator_fn_t free_in_allocator;
 mem_pending_warn_fn_t warn;
 mem_mckernel_free_pages_body_fn_t free_body;
};

extern const struct mem_whole_free_metadata mem_whole_free_metadata;










void mckernel_free_pages(void *va, int npages, int is_user);


































void mem_begin_free_pages_pending_panic_bridge(void);
void mem_finish_free_pages_pending_panic_bridge(void);













extern void mem_begin_free_pages_pending_panic_bridge(void);


void mem_pending_free_bridge(unsigned long phys, int npages,
		int is_user);









extern void mem_finish_free_pages_pending_panic_bridge(void);































extern struct ihk_mc_pa_ops allocator;







void sbox_write(int offset, unsigned int value);


extern int page_hash_count_pages(void);




/* Existing C-owned static node array; immutable address, no C getter. */

extern struct ihk_mc_numa_node *const mem_query_free_nodes;






static int mem_query_free_node_pages_bridge(int node)
{
	int pages = 0;

	if (node < 0 || node >= ihk_mc_get_nr_numa_nodes())
		return 0;




	{
		struct ihk_page_allocator_desc *pa_allocator;

		for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[node].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[node].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {
			int __pages = ihk_pagealloc_query_free(pa_allocator);

			kprintf("McKernel free pages in (0x%lx - 0x%lx): %d\n",
					pa_allocator->start, pa_allocator->end, __pages);
			pages += __pages;
		}
	}


	return pages;
}


extern void mem_query_free_total_log_bridge(int pages);

extern void mem_query_free_panic_bridge(void);

extern void mem_query_free_kmalloc_memcheck_bridge(void);

extern void mem_query_free_page_hash_log_bridge(int pages);

/* Exact original C feature and mutable base-slot address; data only. */
struct mem_sbox_access_metadata {
 int attached;
 void **base_slot;
};





extern const struct mem_sbox_access_metadata mem_sbox_access_metadata;




extern void mem_query_free_sbox_write_bridge(int offset, unsigned int value);



/* Declarative original profile values and callback addresses, no C getter. */
struct mem_query_free_interrupt_metadata {
 int fugaku_panic, attached_mic, sbox_scratch0, sbox_scratch1;
 mem_get_nr_numa_nodes_fn_t nr_nodes;
 mem_query_free_node_pages_fn_t node_pages;
 mem_query_free_log_fn_t total_log;
 mem_lifecycle_void_fn_t panic_fn;
 mem_find_command_line_fn_t find_command_line;
 mem_lifecycle_void_fn_t kmalloc_memcheck_fn;
 mem_lifecycle_void_fn_t pagealloc_memcheck_fn;
 mem_query_page_hash_count_fn_t page_hash_count;
 mem_query_free_log_fn_t page_hash_log;
 mem_query_sbox_write_fn_t sbox_write;
};

extern const struct mem_query_free_interrupt_metadata mem_query_free_interrupt_metadata;
























void query_free_mem_interrupt_handler(void *priv);








































































extern struct ihk_mc_interrupt_handler query_free_mem_handler;







int gencore(struct process *proc, struct coretable **coretable,
	    int *chunks, char *cmdline, int sig);
void freecore(struct coretable **);
struct siginfo;
typedef struct siginfo siginfo_t;
unsigned long do_kill(struct thread *thread, int pid, int tid,
			int sig, siginfo_t *info, int ptracecont);


/* Actual macro/status owners and original two independent log callsites. */

extern struct ddebug mem_coredump_wait_sleep_record;







extern struct ddebug mem_coredump_wait_resume_record;







extern const struct {
 int running;
 int descheduled;
 int interruptible;
 struct ddebug *records[2];
 unsigned long flags_byte;
} mem_coredump_wait_metadata;












extern void coredump_wait(struct thread *thread);


























/* Actual original status constants and mutable logging record; no Cgetter. */
_Static_assert(__builtin_types_compatible_p(
 typeof(((struct thread *)0)->coredump_status),int),"corestatus int ABI");

extern struct ddebug mem_coredump_wakeup_debug_record;








extern const struct {
 int descheduled;
 int to_be_woken;
 struct ddebug *record;
 unsigned long flags_byte;
} mem_coredump_wakeup_metadata;










extern void coredump_wakeup(struct thread *thread);












/**
 * \brief Generate a core file and tell the host to write it out.
 *
 * \param proc A current process structure.
 * \param regs A pointer to a x86_regs structure.
 */


/* Real supported-profile lock and request ABI; no new C runtime helper. */

#error "The staged coredump protocol requires the actual reviewed exclusive reader implementation"

_Static_assert(sizeof(int)==4,"coredump arrival/abort word ABI");
struct mem_coredump_request_abi { struct syscall_request request IHK_DMA_ALIGN; };
_Static_assert(__alignof__(struct mem_coredump_request_abi)==
 __alignof__(struct syscall_request),"reviewed SMP IHK_DMA_ALIGN is empty");

extern struct ddebug mem_coredump_debug_0;







extern struct ddebug mem_coredump_debug_1;






struct mem_coredump_metadata {
 unsigned long core_limit_index;
 int busy,nomem;
 unsigned long nowait,syscall_number;
 char *alloc_file;
 int alloc_line;
 char *free_file;
 int free_line;
 struct ddebug *records[2];
 unsigned long flags_byte;
};

extern const struct mem_coredump_metadata mem_coredump_metadata;







extern int coredump(struct thread *thread, void *regs, int sig);
































































































































/* Immutable source-header geometry; no new C runtime implementation. */


extern const int mem_remote_tlb_geometry[3];





#define MEM_TLB_PUBLIC_BRIDGE





extern unsigned long mem_tlb_rdtsc_bridge(void);








extern int mem_tlb_current_cpu_bridge(void);








extern void mem_tlb_noirq_lock_bridge(unsigned long lock_addr);








extern void mem_tlb_noirq_unlock_bridge(unsigned long lock_addr);








extern void mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value);








extern void mem_tlb_atomic_inc_bridge(unsigned long atomic_addr);








extern void mem_tlb_atomic_dec_bridge(unsigned long atomic_addr);








extern int mem_tlb_atomic_read_bridge(unsigned long atomic_addr);








extern int mem_tlb_get_vector_bridge(int type);








extern void mem_tlb_interrupt_cpu_bridge(int cpu, int vector);








extern void mem_tlb_flush_single_bridge(unsigned long addr);








extern void mem_tlb_flush_all_bridge(void);








extern void mem_tlb_pause_bridge(void);







#undef MEM_TLB_PUBLIC_BRIDGE





























/* Original profile configuration and callback address only; no runtime C helper. */
struct mem_tlb_handler_profile_metadata {
 unsigned int event;
 void (*add)(enum profile_event_type, uint64_t);
};

extern const struct mem_tlb_handler_profile_metadata mem_tlb_handler_profile_metadata;









extern void tlb_flush_handler(int vector);
































struct mem_unhandled_fault_metadata {
 uint64_t pf_prot,pf_write,pf_user,pf_reserved,pf_instruction;
 unsigned int mf_regular_file;
 int fugaku;
 int debug_stack;
 unsigned long (*instruction_address)(const void *);
 unsigned long (*stack_address)(const void *);
};

extern const struct mem_unhandled_fault_metadata mem_unhandled_fault_metadata;

























extern void unhandled_page_fault(struct thread *thread,void *fault_addr,
 uint64_t reason,void *regs);















































































/* Header/selected-build geometry only; original usercopy owns fault policy. */

extern const unsigned long mem_fatal_user_bytes_geometry[2];



extern void mcexec_v10_dump_user_bytes(const char *name,unsigned long addr);






































/* Original ordinary diagnostic words now borrow permanent typed Rust storage. */
extern int mem_page_fault_log_count;
extern int mem_page_fault_log_pid;
_Static_assert(__builtin_types_compatible_p(enum set_cputime_mode,unsigned int),
 "set_cputime enum ABI");

_Static_assert(__builtin_types_compatible_p(enum profile_event_type,unsigned int),
 "profile event enum ABI");






extern struct ddebug mem_page_fault_debug_0;













extern struct ddebug mem_page_fault_debug_2;







extern struct ddebug mem_page_fault_debug_3;






struct mem_page_fault_entry_metadata {
 int * log_count;
 int * log_pid;
 unsigned long page_size;
 unsigned long kernel_start;
 uint64_t pf_user;
 int invalid;
 int canceled;
 int range_error;
 int busy;
 int sigsegv;
 int sigbus;
 int sigstop;
 int map_error;
 int access_error;
 int bus_address_error;
 unsigned int time_u2k;
 unsigned int time_k2kin;
 unsigned int time_k2u;
 unsigned int time_k2kout;
 int tofu;
 int fugaku_debug;
 unsigned long tofu_attr;
 struct ddebug *records[4];
 unsigned long flags_byte;
 void (*unhandled)(struct thread *,void *,uint64_t,void *);
 int (*linux_resolve)(struct page_table *,const void *,unsigned long *,unsigned long *);
 void *(*linux_pgt)(void);
 int (*clear_kernel_range)(void *,void *);
 unsigned long (*do_kill)(struct thread *,int,int,int,struct siginfo *,int);
 void (*profile_add)(unsigned int,uint64_t);
 unsigned int profile_event;
};

extern const struct mem_page_fault_entry_metadata mem_page_fault_entry_metadata;






























































extern void page_fault_handler(void *fault_addr,uint64_t reason,void *regs);


















































































































































































































































/* Original private state addresses and genuine compiler header geometry only. */
struct mem_page_allocator_initialization_metadata {
 unsigned long *pa_start_slot;
 unsigned long *pa_end_slot;
 char *kernel_end;
 unsigned long page_size;
 unsigned long page_mask;
 int attached_mic;
 int reserved_count_type;
 int reserved_start_type;
 int reserved_end_type;
};
extern char _end[];

extern const struct mem_page_allocator_initialization_metadata
mem_page_allocator_initialization_metadata;












extern struct ihk_page_allocator_desc *page_allocator_init(uint64_t start,uint64_t end);


























































int mem_numa_get_node_info_bridge(int node, int *linux_numa_id,
		int *type);












static void mem_numa_node_init_bridge(struct ihk_mc_numa_node *node,
		int rbtree_allocator)
{
	(void)node;
	(void)rbtree_allocator;














}






static void mem_numa_add_free_pages_bridge(struct ihk_mc_numa_node *node,
		unsigned long start, unsigned long len)
{



	(void)node;
	(void)start;
	(void)len;

}


extern void *mem_numa_page_allocator_init_bridge(unsigned long start,
		unsigned long end);

extern void mem_numa_list_allocator_bridge(void *allocator,
		struct ihk_mc_numa_node *node);


unsigned long mem_numa_pagealloc_count_bridge(void *allocator);







extern void mem_numa_rusage_total_add_bridge(unsigned long bytes);

/* Data-only selected C preprocessor fact; no runtime provider/getter. */

extern const int mem_numa_log_rbtree_enabled;








extern void mem_numa_init_log_bridge(int event, int node, int linux_numa_id,
		int type, unsigned long start, unsigned long end,
		unsigned long bytes, int pages, int rbtree_allocator);

extern void mem_numa_panic_bridge(int node);



/* Immutable original callback owners and real Cconfiguration; no Cgetter. */
struct mem_numa_initialization_metadata {
 struct ihk_mc_numa_node *nodes;
 int rbtree_allocator;
 mem_get_numa_node_info_fn_t get_node_info;
 mem_get_memory_chunk_fn_t get_chunk;
 mem_numa_node_init_fn_t init_node;
 mem_numa_add_free_pages_fn_t add_free;
 mem_page_allocator_init_fn_t init_allocator;
 mem_numa_list_allocator_fn_t list_allocator;
 mem_pagealloc_count_fn_t count_pages;
 mem_rusage_total_add_fn_t add_total;
 mem_numa_init_log_fn_t log;
 mem_numa_panic_fn_t panic_fn;
};

extern const struct mem_numa_initialization_metadata mem_numa_initialization_metadata;















extern void numa_init(void);
















































































































/* Actual C diagnostic provenance at the replaced allocation callsite. */
struct mem_numa_distance_allocation_origin {
 const char *file;
 int line;
};

extern const struct mem_numa_distance_allocation_origin mem_numa_distance_allocation_origin;





extern struct node_distance *mem_numa_distances_alloc_bridge(int npages,
		unsigned long flag);

extern void mem_numa_distances_alloc_fail_log_bridge(int node);

extern void mem_numa_distances_log_bridge(int node,
		struct node_distance *distances, int nr_nodes);



struct mem_distance_entry_metadata {
 mem_get_nr_numa_nodes_fn_t nr_nodes;
 mem_numa_distance_alloc_fn_t alloc;
 mem_numa_distance_fn_t distance;
 mem_numa_distance_alloc_fail_log_fn_t alloc_fail;
 mem_numa_distance_log_fn_t log;
};

extern const struct mem_distance_entry_metadata mem_distance_entry_metadata;







void numa_distances_init(void);














































































struct mem_numa_sysfs_show_geometry {
 int rbtree;
 unsigned int kb_shift;
};
_Static_assert(__builtin_types_compatible_p(
 typeof(((struct ihk_mc_numa_node *)0)->nr_pages),unsigned long),"node pages word ABI");
_Static_assert(__builtin_types_compatible_p(
 typeof(((struct ihk_mc_numa_node *)0)->nr_free_pages),unsigned long),"node free pages word ABI");

extern const struct mem_numa_sysfs_show_geometry mem_numa_sysfs_show_geometry;










extern ssize_t numa_sysfs_show_meminfo(struct sysfs_ops *ops,
 void *instance,void *buf,size_t size);





























extern struct sysfs_ops numa_sysfs_meminfo;







/* These static owners outlive all registered sysfs callbacks. */
_Static_assert(PATH_MAX == 4096, "actual Rust ABI PATH_MAX");
struct mem_numa_sysfs_registration_metadata {
 struct sysfs_ops *ops;
 struct ihk_mc_numa_node *nodes;
};

extern const struct mem_numa_sysfs_registration_metadata mem_numa_sysfs_registration_metadata;





extern void numa_sysfs_setup(void);



















#define PHYS_PAGE_HASH_SHIFT	(10)
#define PHYS_PAGE_HASH_SIZE     (1 << PHYS_PAGE_HASH_SHIFT)
#define PHYS_PAGE_HASH_MASK     (PHYS_PAGE_HASH_SIZE - 1)

/*
 * Page hash only tracks pages that are mapped in non-anymous mappings
 * and thus it is initially empty.
 */

extern struct list_head page_hash[PHYS_PAGE_HASH_SIZE];




extern ihk_spinlock_t page_hash_locks[PHYS_PAGE_HASH_SIZE];




typedef unsigned long (*page_hash_lock_fn_t)(unsigned long lock_addr);
typedef void (*page_hash_unlock_fn_t)(unsigned long lock_addr,
		unsigned long flags);
typedef void (*page_hash_lock_init_fn_t)(unsigned long lock_addr);
typedef int (*page_hash_bucket_init_fn_t)(struct list_head *hash_head);
typedef void (*page_map_count_inc_fn_t)(struct page *page);
typedef int (*page_hash_count_all_fn_t)(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn);
typedef struct page *(*page_hash_alloc_fn_t)(unsigned long size, int flag);
typedef struct page *(*phys_to_page_lookup_orchestrate_fn_t)(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn);
typedef struct page *(*phys_to_page_insert_orchestrate_fn_t)(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn);
typedef void (*phys_to_page_insert_log_fn_t)(uint64_t phys);
typedef int (*page_unmap_orchestrate_fn_t)(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn);
typedef void (*page_unmap_log_fn_t)(int event, struct page *page, int ret);

#define PAGE_UNMAP_LOG_ENTER 1
#define PAGE_UNMAP_LOG_STILL_MAPPED 2
#define PAGE_UNMAP_LOG_UNMAPPED 3

struct page *page_hash_lookup_result(struct list_head *hash_head,
		uint64_t phys);
int page_hash_bucket_init_result(struct list_head *hash_head);
int page_hash_tables_init_body_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_init_fn_t lock_init_fn,
		page_hash_bucket_init_fn_t bucket_init_fn);
int page_hash_count_bucket_result(struct list_head *hash_head);
int page_hash_count_all_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn);
int page_hash_count_pages_body_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_count_all_fn_t count_all_fn);
struct page *phys_to_page_lookup_orchestrate_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn);
struct page *phys_to_page_insert_hash_orchestrate_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn);
struct page *phys_to_page_lookup_body_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		phys_to_page_lookup_orchestrate_fn_t lookup_fn);
struct page *phys_to_page_insert_hash_body_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn,
		phys_to_page_insert_orchestrate_fn_t insert_fn,
		phys_to_page_insert_log_fn_t log_fn);
int page_unmap_orchestrate_result(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn);
int page_unmap_body_result(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn,
		page_unmap_orchestrate_fn_t orchestrate_fn,
		page_unmap_log_fn_t log_fn);


#define PAGE_UNMAP_PUBLIC_BRIDGE





extern unsigned long page_hash_lock_bridge(unsigned long lock_addr);








extern void page_hash_unlock_bridge(unsigned long lock_addr,
		unsigned long flags);









extern void page_hash_lock_init_bridge(unsigned long lock_addr);








extern struct page *page_hash_alloc_bridge(unsigned long size, int flag);
/* Diagnostic origin belongs to this former allocation callback site. */

extern const char page_hash_alloc_file[209];
extern const int page_hash_alloc_line;











/* Geometry from the existing arrays; no C accessor or runtime initialization. */

extern const int page_init_hash_bucket_count;




extern const unsigned long page_init_hash_head_stride;



extern void page_init(void);











extern int page_hash_count_pages(void);












extern struct page *phys_to_page(uintptr_t phys);













extern uintptr_t page_to_phys(struct page *page);
extern void page_map_count_inc_result(struct page *page);
extern void page_map_body_result(struct page *page,
		page_map_count_inc_fn_t count_inc_fn);
extern int page_unmap_locked_result(struct page *page);
extern int page_insert_hash_init_result(struct page *page,
		struct list_head *hash_head, uint64_t phys);
extern struct page *page_hash_lookup_result(struct list_head *hash_head,
		uint64_t phys);
extern int page_hash_bucket_init_result(struct list_head *hash_head);
extern int page_hash_tables_init_body_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_init_fn_t lock_init_fn,
		page_hash_bucket_init_fn_t bucket_init_fn);
extern int page_hash_count_bucket_result(struct list_head *hash_head);
extern int page_hash_count_all_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn);
extern int page_hash_count_pages_body_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_count_all_fn_t count_all_fn);
extern struct page *phys_to_page_lookup_orchestrate_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn);
extern struct page *phys_to_page_insert_hash_orchestrate_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn);
extern struct page *phys_to_page_lookup_body_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		phys_to_page_lookup_orchestrate_fn_t lookup_fn);
extern struct page *phys_to_page_insert_hash_body_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn,
		phys_to_page_insert_orchestrate_fn_t insert_fn,
		phys_to_page_insert_log_fn_t log_fn);
extern int page_unmap_orchestrate_result(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn);
extern int page_unmap_body_result(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn,
		page_unmap_orchestrate_fn_t orchestrate_fn,
		page_unmap_log_fn_t log_fn);
extern int page_is_in_memobj_body_result(struct page *page);
extern int page_is_multi_mapped_body_result(struct page *page);



















































































































































































































































































































































/*
 * Allocate page and add to hash if it doesn't exist yet.
 * NOTE: page->count is zero for new pages and the caller
 * is responsible to increase it.
 */

extern void phys_to_page_insert_hash_log_bridge(uint64_t phys);









extern struct page *phys_to_page_insert_hash(uint64_t phys);















/* GCC9 actual12case ddebug witness: size32/align8/flagsbyte27. DefaultGCC14
 * still requires its actual ABI consumer. These are compiler-origin mutable
 * __verbose records, not runtime C getters or copies of their flag state.
 * The genuine dkprintf macro leaves fmt NULL; preserve that field behavior.
 */
_Static_assert(sizeof(struct ddebug) == 32 && _Alignof(struct ddebug) == 8,
               "actual GCC9 ddebug shape");

extern struct ddebug page_unmap_debug_enter;








extern struct ddebug page_unmap_debug_still_mapped;








extern struct ddebug page_unmap_debug_unmapped;







struct page_unmap_debug_metadata {
 struct ddebug *records[3];
 unsigned long flags_byte;
};

extern const struct page_unmap_debug_metadata page_unmap_debug_metadata;






void page_unmap_log_bridge(int event, struct page *page, int ret);
























/* Immutable C ABI geometry; the public wrapper executes in Rust. */

extern const int page_unmap_hash_shift;




extern const unsigned long page_unmap_hash_mask;




extern const unsigned long page_unmap_lock_stride;



int page_unmap(struct page *page);












/* Immutable addresses of existing private allocator and original providers. */
struct mem_register_kmalloc_metadata {
 struct ihk_mc_pa_ops *allocator;
 mem_register_alloc_fn_t debug_alloc;
 mem_register_free_fn_t debug_free;
 mem_register_alloc_fn_t base_alloc;
 mem_register_free_fn_t base_free;
};

extern const struct mem_register_kmalloc_metadata mem_register_kmalloc_metadata;





void register_kmalloc(void);




















extern struct ihk_page_allocator_desc *vmap_allocator;





/* Existing C-owned pointer slot; immutable address/configuration only. */

extern struct ihk_page_allocator_desc **const mem_vmap_allocator_slot;




extern const unsigned long mem_vmap_init_start;




extern const unsigned long mem_vmap_init_size;




extern const unsigned long mem_vmap_init_unit;




extern const int mem_vmap_init_first_level;



extern void *mem_vmap_allocator_bridge(void);

extern void *mem_vmap_init_bridge(unsigned long start, unsigned long size,
		unsigned long unit);

extern int mem_pt_prepare_map_bridge(page_table_t pt, void *virt,
		unsigned long size, enum ihk_mc_pt_prepare_flag flag);

extern unsigned long mem_vmap_alloc_bridge(void *desc, int npages,
		int p2align);

extern void mem_vmap_free_bridge(void *desc, unsigned long address,
		int npages);

extern int mem_pt_set_page_bridge(page_table_t pt, void *virt,
		unsigned long phys, enum ihk_mc_pt_attribute attr);

extern int mem_pt_clear_page_bridge(page_table_t pt, void *virt);

extern void mem_flush_tlb_single_bridge(unsigned long addr);

extern void mem_barrier_bridge(void);



extern void virtual_allocator_init(void);



















extern void *ihk_mc_map_virtual(unsigned long phys, int npages,
		enum ihk_mc_pt_attribute attr);




































extern void ihk_mc_unmap_virtual(void *va, int npages);












































































extern void mem_rusage_init_panic_bridge(void);

/* Actual GCC9 layout witness22c1 binds flags byte27; GCC14 still OPEN. */

extern struct ddebug mem_rusage_init_debug_record;








extern const struct {
 struct ddebug *records[1];
 unsigned long flags_byte;
} mem_rusage_init_debug_metadata;






extern void mem_rusage_init_log_bridge(unsigned long total_memory);



struct mem_rusage_entry_metadata {
 unsigned long state_bytes;
 mem_get_cpu_info_fn_t cpu_info;
 mem_get_nr_numa_nodes_fn_t nr_nodes;
 mem_get_ns_per_tsc_fn_t ns_per_tsc;
 mem_virt_to_phys_fn_t virt_to_phys;
 mem_set_rusage_fn_t set_rusage;
 mem_lifecycle_void_fn_t panic_fn;
 mem_rusage_init_log_fn_t log;
};

extern const struct mem_rusage_entry_metadata mem_rusage_entry_metadata;







void rusage_init(void);




























extern void monitor_init(void);


extern struct ihk_mc_pa_ops *mem_init_allocator_bridge(void);

/* Immutable addresses preserve private C state/handler owners, no C getters. */
struct mem_static_boot_address_metadata {
 unsigned long page_fault_handler_address;
 unsigned long query_free_handler_address;
 int *anon_on_demand_slot;
 int *xpmem_remote_slot;
 int *hugetlbfs_on_demand_slot;
};

extern const struct mem_static_boot_address_metadata mem_static_boot_address_metadata;











extern unsigned long mem_init_page_fault_handler_bridge(void);

extern unsigned long mem_init_query_free_handler_bridge(void);

extern int *mem_init_anon_on_demand_bridge(void);

extern int *mem_init_xpmem_remote_bridge(void);

extern int *mem_init_hugetlbfs_on_demand_bridge(void);

extern void mem_monitor_init_bridge(void);

extern void mem_rusage_init_bridge(void);

extern void mem_numa_init_bridge(void);

extern void mem_page_init_bridge(void);

extern void mem_virtual_allocator_init_bridge(void);

extern char *mem_find_command_line_bridge(char *name);

extern void mem_numa_distances_init_bridge(void);

extern void mem_set_page_fault_handler_bridge(unsigned long handler);

/* Exact supported enum provider ABI; reject incompatible frontend options. */
_Static_assert(__builtin_types_compatible_p(enum ihk_mc_gv_type, unsigned int),
 "ihk_mc_gv_type unsigned int ABI");
_Static_assert(sizeof(enum ihk_mc_gv_type) == 4, "ihk_mc_gv_type width ABI");
extern int mem_get_vector_bridge(int type);

extern int mem_register_interrupt_handler_bridge(int vector,
		unsigned long handler);

extern void mem_init_log_bridge(int event);



void mem_init(void);

















































#define KMALLOC_TRACK_HASH_SHIFT	(8)
#define KMALLOC_TRACK_HASH_SIZE     (1 << KMALLOC_TRACK_HASH_SHIFT)
#define KMALLOC_TRACK_HASH_MASK     (KMALLOC_TRACK_HASH_SIZE - 1)


extern struct list_head kmalloc_track_hash[KMALLOC_TRACK_HASH_SIZE];




extern ihk_spinlock_t kmalloc_track_hash_locks[KMALLOC_TRACK_HASH_SIZE];





extern struct list_head kmalloc_addr_hash[KMALLOC_TRACK_HASH_SIZE];




extern ihk_spinlock_t kmalloc_addr_hash_locks[KMALLOC_TRACK_HASH_SIZE];





extern int kmalloc_track_initialized;




extern int kmalloc_runcount;




struct kmalloc_track_addr_entry {
	void *addr;
	int runcount;
	struct list_head list; /* track_entry's list */
	struct kmalloc_track_entry *entry;
	struct list_head hash; /* address hash */
};

struct kmalloc_track_entry {
	char *file;
	int line;
	int size;
	ihk_atomic_t alloc_count;
	struct list_head hash;
	struct list_head addr_list;
	ihk_spinlock_t addr_list_lock;
};


typedef void *(*mem_kmalloc_base_alloc_fn_t)(int, ihk_mc_ap_flag);
typedef void (*mem_kmalloc_base_free_fn_t)(void *);
typedef unsigned long (*mem_kmalloc_track_lock_fn_t)(unsigned long);
typedef void (*mem_kmalloc_track_unlock_fn_t)(unsigned long, unsigned long);
typedef void (*mem_kmalloc_track_spin_init_fn_t)(unsigned long);
typedef void (*mem_kmalloc_track_log_fn_t)(int, void *, char *, int, int);
typedef void (*mem_kmalloc_invalid_free_fn_t)(void *, char *, int);

#define KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED 1
#define KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED 2
#define KMALLOC_TRACK_LOG_ENTRY_ADDED 3
#define KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED 4
#define KMALLOC_TRACK_LOG_ADDR_ADDED 5
#define KMALLOC_TRACK_LOG_ADDR_REMOVED 6
#define KMALLOC_TRACK_LOG_ENTRY_REMOVED 7

extern struct kmalloc_track_entry *kmalloc_track_find_entry_result(
		int size, char *file, int line, struct list_head *track_hash);
extern void *kmalloc_track_alloc_result(int size, ihk_mc_ap_flag flag,
		char *file, int line, char *memdebug,
		struct list_head *track_hash, ihk_spinlock_t *track_locks,
		struct list_head *addr_hash, ihk_spinlock_t *addr_locks,
		int runcount, mem_kmalloc_base_alloc_fn_t base_alloc_fn,
		mem_kmalloc_base_free_fn_t base_free_fn,
		mem_kmalloc_track_lock_fn_t lock_fn,
		mem_kmalloc_track_unlock_fn_t unlock_fn,
		mem_kmalloc_track_spin_init_fn_t spin_init_fn,
		mem_kmalloc_track_log_fn_t log_fn);
extern int kmalloc_track_free_result(void *ptr, char *file, int line,
		char *memdebug, struct list_head *track_hash,
		ihk_spinlock_t *track_locks, struct list_head *addr_hash,
		ihk_spinlock_t *addr_locks,
		mem_kmalloc_base_free_fn_t base_free_fn,
		mem_kmalloc_track_lock_fn_t lock_fn,
		mem_kmalloc_track_unlock_fn_t unlock_fn,
		mem_kmalloc_invalid_free_fn_t invalid_free_fn,
		mem_kmalloc_track_log_fn_t log_fn);
extern int kmalloc_memcheck_result(struct list_head *track_hash,
		ihk_spinlock_t *track_locks, int *runcount, int hash_size,
		mem_kmalloc_track_lock_fn_t lock_fn,
		mem_kmalloc_track_unlock_fn_t unlock_fn,
		mem_pagealloc_track_noirq_lock_fn_t noirq_lock_fn,
		mem_pagealloc_track_noirq_unlock_fn_t noirq_unlock_fn,
		mem_track_leak_log_fn_t log_fn);
extern int mem_kmalloc_init_body_result(char **memdebug_slot,
		int *track_initialized, struct list_head *track_hash,
		ihk_spinlock_t *track_locks, struct list_head *addr_hash,
		ihk_spinlock_t *addr_locks, int hash_size,
		mem_get_this_cpu_local_var_fn_t get_this_cpu_local_var_fn,
		mem_lifecycle_void_fn_t register_kmalloc_fn,
		mem_find_command_line_fn_t find_command_line_fn,
		mem_kmalloc_track_spin_init_fn_t spin_init_fn);

extern void *mem_kmalloc_track_base_alloc_bridge(int size, ihk_mc_ap_flag flag);

extern void mem_kmalloc_track_base_free_bridge(void *ptr);

extern unsigned long mem_kmalloc_track_lock_bridge(unsigned long lock_addr);

extern void mem_kmalloc_track_unlock_bridge(unsigned long lock_addr,
		unsigned long irqflags);

extern void mem_kmalloc_track_spin_init_bridge(unsigned long lock_addr);


extern struct ddebug mem_kmalloc_track_log_bridge_debug_record_0;








extern struct ddebug mem_kmalloc_track_log_bridge_debug_record_1;








extern struct ddebug mem_kmalloc_track_log_bridge_debug_record_2;








extern struct ddebug mem_kmalloc_track_log_bridge_debug_record_3;







struct mem_kmalloc_track_log_bridge_debug_metadata {
 struct ddebug *records[4];
 unsigned long flags_byte;
};

extern const struct mem_kmalloc_track_log_bridge_debug_metadata mem_kmalloc_track_log_bridge_debug_metadata;





extern void mem_kmalloc_track_log_bridge(int event, void *ptr, char *file,
		int line, int size);

extern void mem_kmalloc_invalid_free_bridge(void *ptr, char *file, int line);


extern struct ddebug mem_kmalloc_leak_log_bridge_debug_record_0;







struct mem_kmalloc_leak_log_bridge_debug_metadata {
 struct ddebug *records[1];
 unsigned long flags_byte;
};

extern const struct mem_kmalloc_leak_log_bridge_debug_metadata mem_kmalloc_leak_log_bridge_debug_metadata;





extern void mem_kmalloc_leak_log_bridge(int event, void *ptr, char *file,
		int line, int size, int count, int runcount);

static struct cpu_local_var *mem_get_this_cpu_local_var_bridge(void)
{
	return get_this_cpu_local_var();
}



void kmalloc_init(void);






































/* NOTE: Hash lock must be held */

extern struct kmalloc_track_entry *__kmalloc_track_find_entry(
		int size, char *file, int line);





























/* Top level routines called from macro */

extern void *_kmalloc(int size, ihk_mc_ap_flag flag, char *file, int line);



















































































extern void _kfree(void *ptr, char *file, int line);



































































































extern void kmalloc_memcheck(void);

















































/* Redirection routines registered in alloc structure */

struct mem_tracked_redirection_source {
 const char *file;
 int line;
};


/* Compiler-origin diagnostics at the replaced C call site; not Rust file!/line!. */

extern const struct mem_tracked_redirection_source mem_tracked_alloc_redirection_source;



void *__kmalloc(int size, ihk_mc_ap_flag flag);








/* Compiler-origin diagnostics at the replaced C call site; not Rust file!/line!. */

extern const struct mem_tracked_redirection_source mem_tracked_free_redirection_source;



void __kfree(void *ptr);









extern void ___kmalloc_insert_chunk_result(struct list_head *free_list,
		struct kmalloc_header *chunk);
extern void ___kmalloc_init_chunk_result(struct kmalloc_header *h, int size);
extern void ___kmalloc_consolidate_list_result(struct list_head *list);
typedef unsigned long (*mem_kmalloc_irq_save_fn_t)(void);
typedef void (*mem_kmalloc_irq_restore_fn_t)(unsigned long);
typedef void *(*mem_kmalloc_alloc_pages_fn_t)(int, ihk_mc_ap_flag, int);
typedef void *(*mem_kmalloc_get_cpu_local_var_fn_t)(int);
typedef unsigned long (*mem_kmalloc_spinlock_fn_t)(unsigned long);
typedef void (*mem_kmalloc_spinunlock_fn_t)(unsigned long, unsigned long);
typedef void (*mem_kmalloc_corruption_fn_t)(void *);
extern void *___kmalloc_body_result(int size, ihk_mc_ap_flag flag,
		struct list_head *free_list,
		mem_kmalloc_irq_save_fn_t irq_save_fn,
		mem_kmalloc_irq_restore_fn_t irq_restore_fn,
		mem_kmalloc_alloc_pages_fn_t alloc_pages_fn);
extern int ___kfree_body_result(void *ptr, struct list_head *free_list,
		unsigned long remote_free_list_lock_offset,
		unsigned long remote_free_list_offset,
		mem_kmalloc_irq_save_fn_t irq_save_fn,
		mem_kmalloc_irq_restore_fn_t irq_restore_fn,
		mem_kmalloc_get_cpu_local_var_fn_t get_cpu_local_var_fn,
		mem_kmalloc_spinlock_fn_t remote_lock_fn,
		mem_kmalloc_spinunlock_fn_t remote_unlock_fn,
		mem_kmalloc_corruption_fn_t corruption_fn);
extern int kmalloc_consolidate_free_list_result(
		struct list_head *remote_free_list, struct list_head *free_list,
		ihk_spinlock_t *remote_free_list_lock,
		mem_kmalloc_spinlock_fn_t remote_lock_fn,
		mem_kmalloc_spinunlock_fn_t remote_unlock_fn);

#define ___kmalloc_insert_chunk ___kmalloc_insert_chunk_result
#define ___kmalloc_init_chunk ___kmalloc_init_chunk_result
#define ___kmalloc_consolidate_list ___kmalloc_consolidate_list_result
































































extern unsigned long mem_kmalloc_irq_save_bridge(void);

extern void mem_kmalloc_irq_restore_bridge(unsigned long flags);

extern void *mem_kmalloc_alloc_pages_bridge(int npages, ihk_mc_ap_flag flag,
		int is_user);

extern void *mem_kmalloc_get_cpu_local_var_bridge(int cpu);

extern unsigned long mem_kmalloc_remote_lock_bridge(unsigned long lock_addr);

extern void mem_kmalloc_remote_unlock_bridge(unsigned long lock_addr,
		unsigned long flags);

extern void mem_kmalloc_corruption_bridge(void *ptr);


#define KMALLOC_CACHE_LOG_NO_CACHE 1
#define KMALLOC_CACHE_LOG_ALLOC_FAILED 2
#define KMALLOC_CACHE_LOG_PREALLOC 3



extern const struct mem_tracked_redirection_source mem_cache_alloc_redirection_source;



void *kmalloc_cache_alloc_bridge(size_t size, ihk_mc_ap_flag flag);

extern void kmalloc_cache_log(int event, void *ptr);



























































































extern void kmalloc_consolidate_free_list(void);





























#define KMALLOC_MIN_SHIFT   (5)
#define KMALLOC_MIN_SIZE    (1 << KMALLOC_MIN_SHIFT)
#define KMALLOC_MIN_MASK    (KMALLOC_MIN_SIZE - 1)

/* Actual low-level allocation routines */

/* Immutable original provider addresses and real compiler field geometry. */
struct mem_lowlevel_kmalloc_metadata {
 unsigned long remote_lock_offset;
 unsigned long remote_list_offset;
 mem_kmalloc_irq_save_fn_t irq_save;
 mem_kmalloc_irq_restore_fn_t irq_restore;
 mem_kmalloc_alloc_pages_fn_t alloc_pages;
 mem_kmalloc_get_cpu_local_var_fn_t get_cpu_local;
 mem_kmalloc_spinlock_fn_t remote_lock;
 mem_kmalloc_spinunlock_fn_t remote_unlock;
 mem_kmalloc_corruption_fn_t corruption;
};

extern const struct mem_lowlevel_kmalloc_metadata mem_lowlevel_kmalloc_metadata;












void *___kmalloc(int size, ihk_mc_ap_flag flag);







































































void ___kfree(void *ptr);





















































void ___kmalloc_print_free_list(struct list_head *list);




















extern int is_mckernel_memory(unsigned long start, unsigned long end);









































extern int mem_num_processors_bridge(void);

extern int mem_dump_level_bridge(void);


struct ihk_dump_page_set *mem_get_dump_page_set_bridge(void);








struct ihk_dump_page *mem_get_dump_page_bridge(void);







extern struct list_head *mem_process_hash_lists_bridge(void);

/* Same actual GCC9 structddebug layout proven by actual12case witness22c1. */

extern struct ddebug mem_dump_complete_debug_record;







struct mem_dump_complete_debug_metadata {
 struct ddebug *record;
 unsigned long flags_byte;
};

extern const struct mem_dump_complete_debug_metadata mem_dump_complete_debug_metadata;





extern void mem_dump_complete_log_bridge(void);

extern void mem_dump_warn_bridge(int kind, unsigned long map_count,
		unsigned long map_index, unsigned long map_start,
		unsigned long map_end, unsigned long page_index);




















































void ihk_mc_query_mem_areas(void);






































void ihk_mc_clear_dump_page_completion(void);















void ihk_mc_query_mem_user_page(void *dump_pase_info);



























void ihk_mc_query_mem_free_page(void *dump_pase_info);














































































int ihk_mc_chk_page_address(pte_t mem_addr);






















int ihk_mc_get_mem_user_page(void *arg0, page_table_t pt, pte_t *ptep, void *pgaddr, int pgshift);








































































extern pte_t *ihk_mc_pt_lookup_fault_pte(struct process_vm *vm, void *virt,
        int pgshift, void **basep, size_t *sizep, int *p2alignp);
























extern int phys_to_nid(unsigned long p);





















extern int lookup_node(struct process_vm *vm, void *addr);


























extern int is_splitable(struct page *page, uint32_t memobj_flags);




























