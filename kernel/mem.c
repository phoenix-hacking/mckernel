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
#ifdef ATTACHED_MIC
#include <sysdeps/mic/mic/micconst.h>
#include <sysdeps/mic/mic/micsboxdefine.h>
#endif
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

#ifdef DEBUG_PRINT_MEM
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

static unsigned long pa_start, pa_end;
static struct ihk_mc_numa_node memory_nodes[512];

extern int ihk_mc_pt_print_pte(struct page_table *pt, void *virt);
extern int interrupt_from_user(void *);

struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];

int anon_on_demand = 0;
#ifdef ENABLE_FUGAKU_HACKS
int hugetlbfs_on_demand;
#endif
int xpmem_page_in_remote_on_attach;
int sysctl_overcommit_memory = OVERCOMMIT_ALWAYS;

#ifndef MCKERNEL_RUST_RUSAGE_PRIVATE_HELPERS
#ifdef ENABLE_RUSAGE
int rusage_pgsize_to_pgtype(size_t pgsize)
{
	int ret = IHK_OS_PGSIZE_4KB;
	int pgshift = pgsize_to_pgshift(pgsize);

	switch (pgshift) {
	case 12:
		ret = IHK_OS_PGSIZE_4KB;
		break;
	case 21:
		ret = IHK_OS_PGSIZE_2MB;
		break;
	case 30:
		ret = IHK_OS_PGSIZE_1GB;
		break;
	default:
#if 0 /* 64KB page goes here when using mckernel_rusage-compatible ihk_os_rusage */
		kprintf("%s: Error: Unknown pgsize=%ld\n",
			__func__, pgsize);
#endif
		break;
	}

	return ret;
}

void rusage_total_memory_add(unsigned long size)
{
#ifdef RUSAGE_DEBUG
	kprintf("%s: total_memory=%ld,size=%ld\n",
		__FUNCTION__, rusage.total_memory, size);
#endif
	rusage.total_memory += size;
#ifdef RUSAGE_DEBUG
	kprintf("%s: total_memory=%ld\n", __FUNCTION__, rusage.total_memory);
#endif
}

unsigned long rusage_get_total_memory(void)
{
	return rusage.total_memory;
}

unsigned long rusage_get_free_memory(void)
{
	return rusage.total_memory - rusage.total_memory_usage;
}

unsigned long rusage_get_usage_memory(void)
{
	return rusage.total_memory_usage;
}

void rusage_rss_add(unsigned long size)
{
	unsigned long newval;
	unsigned long oldval;
	unsigned long retval;
	struct process_vm *vm;

	newval = __sync_add_and_fetch(&rusage.rss_current, size);
	oldval = rusage.memory_max_usage;
	while (newval > oldval) {
		retval = __sync_val_compare_and_swap(&rusage.memory_max_usage,
		                                     oldval, newval);
		if (retval == oldval) {
			break;
		}
		oldval = retval;
	}

	/* process rss */
	vm = get_this_cpu_local_var()->on_fork_vm;
	if (!vm) {
		vm = get_this_cpu_local_var()->current->vm;
	}

	vm->currss += size;
	if (vm->proc && vm->currss > vm->proc->maxrss) {
		vm->proc->maxrss = vm->currss;
	}
}

void rusage_rss_sub(unsigned long size)
{
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	__sync_sub_and_fetch(&rusage.rss_current, size);

	/* process rss */
	vm->currss -= size;
}

void memory_stat_rss_add(unsigned long size, int pgsize)
{
	ihk_atomic_add_long(size,
		&rusage.memory_stat_rss[rusage_pgsize_to_pgtype(pgsize)]);
}

void memory_stat_rss_sub(unsigned long size, int pgsize)
{
	ihk_atomic_add_long(-size,
		&rusage.memory_stat_rss[rusage_pgsize_to_pgtype(pgsize)]);
}

void rusage_memory_stat_mapped_file_add(unsigned long size, int pgsize)
{
	ihk_atomic_add_long(size,
		&rusage.memory_stat_mapped_file[
			rusage_pgsize_to_pgtype(pgsize)]);
}

void rusage_memory_stat_mapped_file_sub(unsigned long size, int pgsize)
{
	ihk_atomic_add_long(-size,
		&rusage.memory_stat_mapped_file[
			rusage_pgsize_to_pgtype(pgsize)]);
}

void rusage_memory_stat_sub(struct memobj *memobj, unsigned long size,
			    int pgsize)
{
	if (memobj->flags & MF_SHM) {
		memory_stat_rss_sub(size, pgsize);
	} else {
		rusage_memory_stat_mapped_file_sub(size, pgsize);
	}
}

int rusage_memory_stat_add(struct vm_range *range, uintptr_t phys,
			   unsigned long size, int pgsize)
{
	struct page *page;

	/* Is it resident in main memory? */
	if (range->flag & (VR_REMOTE | VR_IO_NOCACHE | VR_RESERVED)) {
		return 0;
	}
	/* Is it anonymous and pre-paging? */
	if (!range->memobj) {
		memory_stat_rss_add(size, pgsize);
		return 1;
	}
	/* Is it devobj or (fileobj and pre-map) or xpmem attachment? */
	if ((range->memobj->flags & MF_DEV_FILE) ||
	    (range->memobj->flags & MF_PREMAP) ||
	    (range->memobj->flags & MF_XPMEM)) {
		return 0;
	}
	/* Is it anonymous and demand-paging? */
	if (range->memobj->flags & MF_ZEROOBJ) {
		memory_stat_rss_add(size, pgsize);
		return 1;
	}

	page = phys_to_page(phys);

	/* Is It file map and cow page? */
	if ((range->memobj->flags & (MF_DEV_FILE | MF_REG_FILE |
				     MF_HUGETLBFS)) && !page) {
		memory_stat_rss_add(size, pgsize);
		return 1;
	}

	/* Is it a sharable page? */
	if (!page) {
		kprintf("%s: WARNING !page,phys=%lx\n", __FUNCTION__, phys);
		return 0;
	}
	/* Is this the first attempt to map the sharable page? */
	if (__sync_bool_compare_and_swap(&page->mapped.counter64, 0, 1)) {
		if (range->memobj->flags & MF_SHM) {
			memory_stat_rss_add(size, pgsize);
		} else {
			rusage_memory_stat_mapped_file_add(size, pgsize);
		}
		return 1;
	} else {
		return 0;
	}
	return 0;
}

int rusage_memory_stat_add_with_page(struct vm_range *range, uintptr_t phys,
				     unsigned long size, int pgsize,
				     struct page *page)
{
	/* Is it resident in main memory? */
	if (range->flag & (VR_REMOTE | VR_IO_NOCACHE | VR_RESERVED)) {
		return 0;
	}
	/* Is it anonymous and pre-paging? */
	if (!range->memobj) {
		memory_stat_rss_add(size, pgsize);
		return 1;
	}
	/* Is it devobj or (fileobj and pre-map) or xpmem attachment? */
	if ((range->memobj->flags & MF_DEV_FILE) ||
	    (range->memobj->flags & MF_PREMAP) ||
	    (range->memobj->flags & MF_XPMEM)) {
		return 0;
	}
	/* Is it anonymous and demand-paging? */
	if (range->memobj->flags & MF_ZEROOBJ) {
		memory_stat_rss_add(size, pgsize);
		return 1;
	}

	/* Is It file map and cow page? */
	if ((range->memobj->flags & (MF_DEV_FILE | MF_REG_FILE)) && !page) {
		memory_stat_rss_add(size, pgsize);
		return 1;
	}

	/* Is it a sharable page? */
	if (!page) {
		kprintf("%s: WARNING !page,phys=%lx\n", __FUNCTION__, phys);
		return 0;
	}
	/* Is this the first attempt to map the sharable page? */
	if (__sync_bool_compare_and_swap(&page->mapped.counter64, 0, 1)) {
		if (range->memobj->flags & MF_SHM) {
			memory_stat_rss_add(size, pgsize);
		} else {
			rusage_memory_stat_mapped_file_add(size, pgsize);
		}
		return 1;
	} else {
		return 0;
	}
	return 0;
}

void rusage_numa_add(int numa_id, unsigned long size)
{
	__sync_add_and_fetch(rusage.memory_numa_stat + numa_id, size);
	rusage_rss_add(size);
}

void rusage_numa_sub(int numa_id, unsigned long size)
{
	rusage_rss_sub(size);
	__sync_sub_and_fetch(rusage.memory_numa_stat + numa_id, size);
}

void rusage_page_add(int numa_id, unsigned long pages, int is_user)
{
	unsigned long size = pages * PAGE_SIZE;
	unsigned long newval;
	unsigned long oldval;
	unsigned long retval;

#ifdef RUSAGE_DEBUG
	if (numa_id < 0 || numa_id >= rusage.num_numa_nodes) {
		kprintf("%s: Error: invalid numa_id=%d\n", __FUNCTION__,
			numa_id);
		return;
	}
#endif
	if (is_user)
		rusage_numa_add(numa_id, size);
	else
		rusage_kmem_add(size);

	newval = __sync_add_and_fetch(&rusage.total_memory_usage, size);
	oldval = rusage.total_memory_max_usage;
	while (newval > oldval) {
		retval = __sync_val_compare_and_swap(
					&rusage.total_memory_max_usage,
					oldval, newval);
		if (retval == oldval) {
#ifdef RUSAGE_DEBUG
			if (rusage.total_memory_max_usage >
					rusage.total_memory_max_usage_old +
					(1 * (1ULL << 30))) {
				kprintf("%s: max(%ld) > old + 1GB,numa_id=%d\n",
					__FUNCTION__,
					rusage.total_memory_max_usage, numa_id);
				rusage.total_memory_max_usage_old =
					rusage.total_memory_max_usage;
			}
#endif
			break;
		}
		oldval = retval;
	}
}

void rusage_page_sub(int numa_id, unsigned long pages, int is_user)
{
	unsigned long size = pages * PAGE_SIZE;

#ifdef RUSAGE_DEBUG
	if (numa_id < 0 || numa_id >= rusage.num_numa_nodes) {
		kprintf("%s: Error: invalid numa_id=%d\n", __FUNCTION__,
			numa_id);
		return;
	}
	if (rusage.total_memory_usage < size) {
		kprintf("%s: Error, total_memory_usage=%ld,size=%ld\n",
			__FUNCTION__, rusage.total_memory_max_usage, size);
	}
#endif
	__sync_sub_and_fetch(&rusage.total_memory_usage, size);

	if (is_user)
		rusage_numa_sub(numa_id, size);
	else
		rusage_kmem_sub(size);
}

void rusage_kmem_add(unsigned long size)
{
	unsigned long newval;
	unsigned long oldval;
	unsigned long retval;

	newval = __sync_add_and_fetch(&rusage.memory_kmem_usage, size);
	oldval = rusage.memory_kmem_max_usage;
	while (newval > oldval) {
		retval = __sync_val_compare_and_swap(
					&rusage.memory_kmem_max_usage,
					oldval, newval);
		if (retval == oldval) {
			break;
		}
		oldval = retval;
	}
}

void rusage_kmem_sub(unsigned long size)
{
	__sync_sub_and_fetch(&rusage.memory_kmem_usage, size);
}

void rusage_num_threads_inc(void)
{
	unsigned long newval;
	unsigned long oldval;
	unsigned long retval;

	newval = __sync_add_and_fetch(&rusage.num_threads, 1);
	oldval = rusage.max_num_threads;
	while (newval > oldval) {
		retval = __sync_val_compare_and_swap(&rusage.max_num_threads,
		                                     oldval, newval);
		if (retval == oldval) {
			break;
		}
		oldval = retval;
	}
}

void rusage_num_threads_dec(void)
{
	__sync_sub_and_fetch(&rusage.num_threads, 1);
}

int rusage_check_oom(int numa_id, unsigned long pages, int is_user)
{
	unsigned long size = pages * PAGE_SIZE;

	if (rusage.total_memory_usage + size >
			rusage.total_memory - RUSAGE_OOM_MARGIN) {
		kprintf("%s: memory used:%ld available:%ld\n", __FUNCTION__,
			rusage.total_memory_usage, rusage.total_memory);
		eventfd(IHK_OS_EVENTFD_TYPE_OOM);
		if (is_user) {
			return -ENOMEM;
		}
	}

	return 0;
}

int rusage_check_overmap(size_t len, int pgshift)
{
	int npages = 0, remain_pages = 0;

	if (sysctl_overcommit_memory == OVERCOMMIT_ALWAYS)
		return 0;

	npages = (len + (1UL << pgshift) - 1) >> pgshift;
	remain_pages = (rusage.total_memory - rusage.total_memory_usage)
			>> pgshift;

	if (npages > remain_pages) {
		return 1;
	}

	return 0;
}
#else
void rusage_total_memory_add(unsigned long size)
{
	(void)size;
}

unsigned long rusage_get_total_memory(void)
{
	return 0;
}

unsigned long rusage_get_free_memory(void)
{
	return 0;
}

unsigned long rusage_get_usage_memory(void)
{
	return 0;
}

void rusage_rss_add(unsigned long size)
{
	(void)size;
}

void rusage_rss_sub(unsigned long size)
{
	(void)size;
}

void memory_stat_rss_add(unsigned long size, int pgsize)
{
	(void)size;
	(void)pgsize;
}

void memory_stat_rss_sub(unsigned long size, int pgsize)
{
	(void)size;
	(void)pgsize;
}

void rusage_memory_stat_mapped_file_add(unsigned long size, int pgsize)
{
	(void)size;
	(void)pgsize;
}

void rusage_memory_stat_mapped_file_sub(unsigned long size, int pgsize)
{
	(void)size;
	(void)pgsize;
}

void rusage_memory_stat_sub(struct memobj *memobj, unsigned long size,
			    int pgsize)
{
	(void)memobj;
	(void)size;
	(void)pgsize;
}

int rusage_memory_stat_add_with_page(struct vm_range *range, struct page *page,
				     unsigned long size, int pgsize)
{
	(void)range;
	(void)page;
	(void)size;
	(void)pgsize;
	return 0;
}

int rusage_memory_stat_add(struct vm_range *range, uintptr_t phys,
			   unsigned long size, int pgsize)
{
	(void)range;
	(void)phys;
	(void)size;
	(void)pgsize;
	return 0;
}

void rusage_numa_add(int numa_id, unsigned long size)
{
	(void)numa_id;
	(void)size;
}

void rusage_numa_sub(int numa_id, unsigned long size)
{
	(void)numa_id;
	(void)size;
}

void rusage_page_add(int numa_id, unsigned long pages, int is_user)
{
	(void)numa_id;
	(void)pages;
	(void)is_user;
}

void rusage_page_sub(int numa_id, unsigned long pages, int is_user)
{
	(void)numa_id;
	(void)pages;
	(void)is_user;
}

void rusage_kmem_add(unsigned long size)
{
	(void)size;
}

void rusage_kmem_sub(unsigned long size)
{
	(void)size;
}

void rusage_num_threads_inc(void)
{
}

void rusage_num_threads_dec(void)
{
}

int rusage_check_oom(int numa_id, unsigned long pages, int is_user)
{
	(void)numa_id;
	(void)pages;
	(void)is_user;
	return 0;
}

int rusage_check_overmap(size_t len, int pgshift)
{
	(void)len;
	(void)pgshift;
	return 0;
}
#endif
#endif /* MCKERNEL_RUST_RUSAGE_PRIVATE_HELPERS */

#ifndef MCKERNEL_RUST_MMAN_HELPERS
unsigned long round_up(unsigned long x, unsigned long y)
{
	return ((x - 1) | (y - 1)) + 1;
}

unsigned long round_down(unsigned long x, unsigned long y)
{
	return x & ~(y - 1);
}
#endif

#ifndef MCKERNEL_RUST_HASH_HELPERS
uint64_t hash_64(uint64_t val, unsigned int bits)
{
	uint64_t hash = val;
	uint64_t n = hash;

	n <<= 18;
	hash -= n;
	n <<= 33;
	hash -= n;
	n <<= 3;
	hash += n;
	n <<= 3;
	hash -= n;
	n <<= 4;
	hash += n;
	n <<= 2;
	hash += n;

	return hash >> (64 - bits);
}

uint32_t hash_32(uint32_t val, unsigned int bits)
{
	uint32_t hash = val * 0x9e370001UL;

	return hash >> (32 - bits);
}

unsigned long hash_long(unsigned long val, unsigned int bits)
{
	if (sizeof(long) == 8)
		return hash_64(val, bits);

	return hash_32(val, bits);
}

unsigned long hash_ptr(void *ptr, unsigned int bits)
{
	return hash_long((unsigned long)ptr, bits);
}
#endif

#ifndef MCKERNEL_RUST_MEM_HELPERS
static struct ihk_mc_pa_ops *pa_ops;
#endif

extern void *early_alloc_pages(int nr_pages);
extern void early_alloc_invalidate(void);

#ifdef MCKERNEL_RUST_MEM_HELPERS
char *memdebug = NULL;
#else
static char *memdebug = NULL;
#endif

#ifndef MCKERNEL_RUST_REFCOUNT_HELPERS
void
kref_init(struct kref *kref)
{
	ihk_atomic_set(&kref->refcount, MCKERNEL_KREF_MARK + 1);
}

unsigned int
kref_read(const struct kref *kref)
{
	return (ihk_atomic_read(&kref->refcount) & ~(MCKERNEL_KREF_MARK));
}

unsigned int
kref_is_mckernel(const struct kref *kref)
{
	return (ihk_atomic_read(&kref->refcount) & (MCKERNEL_KREF_MARK));
}

void
kref_get(struct kref *kref)
{
	ihk_atomic_inc(&kref->refcount);
}

int
kref_put(struct kref *kref, void (*release)(struct kref *kref))
{
	if (ihk_atomic_sub_return(1, &kref->refcount) == MCKERNEL_KREF_MARK) {
		release(kref);
		return 1;
	}
	return 0;
}

int
memobj_ref(struct memobj *obj)
{
	return ihk_atomic_inc_return(&obj->refcnt);
}

int
memobj_unref(struct memobj *obj)
{
	int cnt;

	cnt = ihk_atomic_dec_return(&obj->refcnt);
	if (memobj_unref_should_free_result(cnt)) {
		(*obj->ops->free)(obj);
	}

	return cnt;
}
#endif /* MCKERNEL_RUST_REFCOUNT_HELPERS */

static void *___kmalloc(int size, ihk_mc_ap_flag flag);
static void ___kfree(void *ptr);

#ifdef MCKERNEL_RUST_MEM_HELPERS
void *___ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
		ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr);
void *___ihk_mc_alloc_pages(int npages, ihk_mc_ap_flag flag, int is_user);
void ___ihk_mc_free_pages(void *p, int npages, int is_user);
#else
static void *___ihk_mc_alloc_aligned_pages_node(int npages,
		int p2align, ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr);
static void *___ihk_mc_alloc_pages(int npages, ihk_mc_ap_flag flag, int is_user);
static void ___ihk_mc_free_pages(void *p, int npages, int is_user);
#endif

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
static int mem_current_numa_id_bridge(void);

#ifdef MCKERNEL_RUST_MEM_HELPERS
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
		unsigned long phys, int npages, int attr,
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
#else
void *mem_pa_alloc_aligned_pages_node_result(struct ihk_mc_pa_ops *ops,
		int npages, int p2align, ihk_mc_ap_flag flag, int node,
		int is_user, uintptr_t virt_addr,
		mem_early_alloc_pages_fn_t early_alloc_fn)
{
	if (ops)
		return ops->alloc_page(npages, p2align, flag, node, is_user,
				virt_addr);

	return early_alloc_fn ? early_alloc_fn(npages) : NULL;
}

void *mem_pa_alloc_pages_result(struct ihk_mc_pa_ops *ops, int npages,
		ihk_mc_ap_flag flag, int is_user,
		mem_early_alloc_pages_fn_t early_alloc_fn)
{
	return mem_pa_alloc_aligned_pages_node_result(ops, npages,
			PAGE_P2ALIGN, flag, -1, is_user, -1, early_alloc_fn);
}

void mem_pa_free_pages_result(struct ihk_mc_pa_ops *ops, void *ptr,
		int npages, int is_user)
{
	if (ops && ops->free_page)
		ops->free_page(ptr, npages, is_user);
}

int mem_reserve_pages_body_result(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long allocator_start, unsigned long allocator_end,
		unsigned long start, unsigned long end,
		mem_reserve_log_fn_t log_fn,
		mem_reserve_range_fn_t reserve_fn)
{
	if (!pa_allocator || !log_fn || !reserve_fn)
		return -EINVAL;

	if (start < allocator_start)
		start = allocator_start;
	if (end > allocator_end)
		end = allocator_end;
	if (start >= end)
		return 0;

	log_fn(start, end, (end - start) >> PAGE_SHIFT);
	reserve_fn(pa_allocator, start, end);
	return 1;
}

int mem_reserve_pages_public_body_result(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long allocator_start, unsigned long allocator_end,
		unsigned long start, unsigned long end,
		mem_reserve_log_fn_t log_fn,
		mem_reserve_range_fn_t reserve_fn,
		mem_reserve_pages_body_fn_t reserve_body_fn,
		mem_lifecycle_void_fn_t panic_fn)
{
	int ret;

	ret = reserve_body_fn ? reserve_body_fn(pa_allocator, allocator_start,
			allocator_end, start, end, log_fn, reserve_fn) : -EINVAL;
	if (ret < 0 && panic_fn)
		panic_fn();

	return ret;
}

int mem_begin_free_pages_pending_result(struct list_head *pendings)
{
	if (!pendings || pendings->next)
		return -EINVAL;

	INIT_LIST_HEAD(pendings);
	return 0;
}

int mem_begin_free_pages_pending_body_result(struct list_head *pendings,
		mem_begin_free_pages_pending_fn_t begin_fn,
		mem_lifecycle_void_fn_t panic_fn)
{
	int ret;

	ret = begin_fn ? begin_fn(pendings) : -EINVAL;
	if (ret && panic_fn)
		panic_fn();

	return ret;
}

int mem_begin_free_pages_pending_public_body_result(
		mem_pending_pages_fn_t pending_pages_fn,
		mem_begin_free_pages_pending_fn_t begin_fn,
		mem_lifecycle_void_fn_t panic_fn)
{
	struct list_head *pendings;
	int ret;

	if (!pending_pages_fn) {
		if (panic_fn)
			panic_fn();
		return -EINVAL;
	}

	pendings = pending_pages_fn();
	if (!pendings) {
		if (panic_fn)
			panic_fn();
		return -EINVAL;
	}

	ret = begin_fn ? begin_fn(pendings) : -EINVAL;
	if (ret && panic_fn)
		panic_fn();

	return ret;
}

int mem_free_pages_pending_enqueue_result(struct page *page,
		struct list_head *pendings, int npages,
		mem_pending_warn_fn_t warn_fn)
{
	if (!page || !pendings)
		return 0;

	if (page->mode != PM_NONE && warn_fn)
		warn_fn(page->phys);

	if (!pendings->next)
		return 0;

	page->mode = PM_PENDING_FREE;
	page->offset = npages;
	list_add_tail(&page->list, pendings);
	return 1;
}

int mem_finish_free_pages_pending_result(struct list_head *pendings,
		mem_pending_free_fn_t free_fn)
{
	struct page *page;
	struct page *next;
	int count = 0;

	if (!pendings || !pendings->next)
		return 0;
	if (!free_fn)
		return -EINVAL;

	for (page = ((typeof(*page) *)((char *)((pendings)->next) - offsetof(typeof(*page), list))), next = ((typeof(*page) *)((char *)(page->list.next) - offsetof(typeof(*page), list))); &page->list != (pendings); page = next, next = ((typeof(*next) *)((char *)(next->list.next) - offsetof(typeof(*next), list)))) {
		if (page->mode != PM_PENDING_FREE)
			return -EINVAL;

		page->mode = PM_NONE;
		list_del(&page->list);
		free_fn(page->phys, page->offset, IHK_MC_PG_USER);
		count++;
	}

	pendings->next = pendings->prev = NULL;
	return count;
}

int mem_finish_free_pages_pending_body_result(struct list_head *pendings,
		mem_finish_free_pages_pending_fn_t finish_fn,
		mem_pending_free_fn_t free_fn, mem_lifecycle_void_fn_t panic_fn)
{
	int ret;

	ret = finish_fn ? finish_fn(pendings, free_fn) : -EINVAL;
	if (ret < 0 && panic_fn)
		panic_fn();

	return ret;
}

int mem_finish_free_pages_pending_public_body_result(
		mem_pending_pages_fn_t pending_pages_fn,
		mem_finish_free_pages_pending_fn_t finish_fn,
		mem_pending_free_fn_t free_fn,
		mem_lifecycle_void_fn_t panic_fn)
{
	struct list_head *pendings;
	int ret;

	if (!pending_pages_fn) {
		if (panic_fn)
			panic_fn();
		return -EINVAL;
	}

	pendings = pending_pages_fn();
	if (!pendings) {
		if (panic_fn)
			panic_fn();
		return -EINVAL;
	}

	ret = finish_fn ? finish_fn(pendings, free_fn) : -EINVAL;
	if (ret < 0 && panic_fn)
		panic_fn();

	return ret;
}

int mem_free_pages_in_allocator_rbtree_result(void *va, int npages,
		int is_user, mem_get_nr_memory_chunks_fn_t nr_chunks_fn,
		mem_get_memory_chunk_fn_t chunk_fn,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_get_numa_node_fn_t numa_node_fn,
		mem_numa_free_fn_t numa_free_fn,
		mem_rusage_sub_fn_t rusage_sub_fn)
{
	unsigned long pa_start, pa_end;
	int i;

	if (npages <= 0 || !nr_chunks_fn || !chunk_fn || !virt_to_phys_fn ||
			!numa_node_fn || !numa_free_fn || !rusage_sub_fn)
		return 0;

	pa_start = virt_to_phys_fn(va);
	pa_end = pa_start + (npages * PAGE_SIZE);

	for (i = 0; i < nr_chunks_fn(); ++i) {
		unsigned long start, end;
		int numa_id;
		void *node;

		chunk_fn(i, &start, &end, &numa_id);
		if (start > pa_start || end < pa_end)
			continue;

		node = numa_node_fn(numa_id);
		if (!node)
			continue;

		numa_free_fn(node, pa_start, npages);
		rusage_sub_fn(numa_id, npages, is_user);
		return 1;
	}

	return 0;
}

int mem_mask_test_result(int numa_id, unsigned long *numa_mask, int nr_bits)
{
	int word_bits = sizeof(unsigned long) * 8;

	if (!numa_mask || numa_id < 0 || nr_bits <= 0 || numa_id >= nr_bits)
		return 0;

	return !!(numa_mask[numa_id / word_bits] &
		  (1UL << (numa_id % word_bits)));
}

int mem_interleave_nodes_result(int off, unsigned long *numa_mask,
		int nr_bits)
{
	int start;
	int i;

	if (!numa_mask || nr_bits <= 0)
		return nr_bits;

	if (off < 0)
		start = 0;
	else if (off >= nr_bits)
		start = nr_bits;
	else
		start = off + 1;

	for (i = start; i < nr_bits; i++) {
		if (numa_mask[i / (int)(sizeof(unsigned long) * 8)] &
		    (1UL << (i % (int)(sizeof(unsigned long) * 8))))
			return i;
	}
	for (i = 0; i < nr_bits; i++) {
		if (numa_mask[i / (int)(sizeof(unsigned long) * 8)] &
		    (1UL << (i % (int)(sizeof(unsigned long) * 8))))
			return i;
	}

	return nr_bits;
}

int mem_range_is_shm_result(int has_range, int has_memobj,
		unsigned long memobj_flags)
{
	if (!has_range || !has_memobj)
		return 0;

	return memobj_flags == MF_SHM;
}

int mem_policy_fields_result(int has_policy, int policy,
		unsigned long *mask, int *il_prev_in,
		int *numa_mem_policy, unsigned long **numa_mask,
		int **il_prev)
{
	if (!has_policy)
		return 0;
	if (numa_mem_policy)
		*numa_mem_policy = policy;
	if (numa_mask)
		*numa_mask = mask;
	if (il_prev)
		*il_prev = il_prev_in;
	return 1;
}

void *mem_current_vm_result(int cpu_local_initialized, void *current, void *vm)
{
	if (!cpu_local_initialized || !current)
		return NULL;

	return vm;
}

int mem_default_alloc_policy_result(ihk_mc_ap_flag flag,
		ihk_mc_ap_flag *policy_flag, int *policy_pref_node,
		int *numa_mem_policy)
{
	if (numa_mem_policy)
		*numa_mem_policy = MPOL_DEFAULT;
	if (policy_pref_node)
		*policy_pref_node = -1;
	if (policy_flag)
		*policy_flag = flag & ~IHK_MC_AP_USER;
	return 1;
}

int mem_alloc_policy_should_try_policy_result(int pref_node,
		ihk_mc_ap_flag flag, int numa_mem_policy, int chk_shm)
{
	return !((pref_node == -1) && !(flag & IHK_MC_AP_USER) &&
		 (numa_mem_policy == MPOL_DEFAULT) && (chk_shm == 0));
}

int mem_alloc_node_id_valid_result(int node, int nr_nodes)
{
	return node >= 0 && node < nr_nodes;
}

int mem_alloc_policy_inputs_valid_result(int npages, int nr_nodes,
		int has_try_alloc, int has_rusage_add, int has_phys_to_virt)
{
	return npages > 0 && nr_nodes > 0 && has_try_alloc &&
		has_rusage_add && has_phys_to_virt;
}

int mem_alloc_order_node_result(int current_node, int offset, int nr_nodes)
{
	if (nr_nodes <= 0)
		return -1;

	return (current_node + offset) % nr_nodes;
}

void *mem_mckernel_alloc_policy_result(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user,
		int current_node, int nr_nodes, int numa_mem_policy,
		int chk_shm, unsigned long *numa_mask, int *il_prevp,
		mem_try_alloc_node_fn_t try_alloc_fn,
		mem_distance_id_fn_t distance_id_fn,
		mem_mask_test_fn_t mask_test_fn,
		mem_interleave_next_fn_t interleave_next_fn,
		mem_rusage_add_fn_t rusage_add_fn,
		mem_phys_to_virt_fn_t phys_to_virt_fn,
		mem_alloc_log_fn_t log_fn)
{
	unsigned long pa = 0;
	int numa_id;
	int i;

	if (!mem_alloc_policy_inputs_valid_result(npages, nr_nodes,
			!!try_alloc_fn, !!rusage_add_fn, !!phys_to_virt_fn))
		return NULL;

	if (mem_alloc_policy_should_try_policy_result(pref_node, flag,
			numa_mem_policy, chk_shm)) {
		if (mem_alloc_node_id_valid_result(pref_node, nr_nodes)) {
			int oom = 0;

			pa = try_alloc_fn(pref_node, npages, p2align,
					  is_user, &oom);
			if (pa) {
				rusage_add_fn(pref_node, npages, is_user);
				if (log_fn)
					log_fn(MEM_ALLOC_LOG_EXPLICIT_OK,
					       current_node, pref_node, npages);
				return phys_to_virt_fn(pa);
			}
			if (log_fn)
				log_fn(MEM_ALLOC_LOG_EXPLICIT_MISS,
				       current_node, pref_node, npages);
		}

		switch (numa_mem_policy) {
		case MPOL_BIND:
		case MPOL_PREFERRED:
			if (!distance_id_fn || !mask_test_fn || !numa_mask)
				break;
			for (i = 0; i < nr_nodes; ++i) {
				int oom = 0;

				numa_id = distance_id_fn(current_node, i);
				if (!mem_alloc_node_id_valid_result(numa_id,
						nr_nodes))
					continue;
				if (!mask_test_fn(numa_id, numa_mask))
					continue;
				pa = try_alloc_fn(numa_id, npages, p2align,
						  is_user, &oom);
				if (pa) {
					rusage_add_fn(numa_id, npages,
						      is_user);
					if (log_fn)
						log_fn(MEM_ALLOC_LOG_POLICY_OK,
						       current_node, numa_id,
						       npages);
					break;
				}
			}
			break;
		case MPOL_INTERLEAVE:
			if (!interleave_next_fn || !numa_mask || !il_prevp)
				break;
			{
				int il_start = *il_prevp;
				int looping = 0;
				int attempts = 0;

				while (attempts++ <= nr_nodes) {
					int oom = 0;

					numa_id = interleave_next_fn(*il_prevp,
								     numa_mask);
					*il_prevp = numa_id;
					if (il_start == *il_prevp && looping) {
						pa = 0;
						break;
					}
					looping = 1;
					pa = try_alloc_fn(numa_id, npages,
							  p2align, is_user,
							  &oom);
					if (pa) {
						rusage_add_fn(numa_id, npages,
							      is_user);
						if (log_fn)
							log_fn(MEM_ALLOC_LOG_POLICY_OK,
							       current_node,
							       numa_id,
							       npages);
						break;
					}
					if (!oom)
						break;
				}
			}
			break;
		default:
			break;
		}

		if (pa)
			return phys_to_virt_fn(pa);
		if (log_fn)
			log_fn(MEM_ALLOC_LOG_POLICY_MISS, current_node, -1,
			       npages);
	}

	if (distance_id_fn) {
		for (i = 0; i < nr_nodes; ++i) {
			int oom = 0;

			numa_id = distance_id_fn(current_node, i);
			if (!mem_alloc_node_id_valid_result(numa_id, nr_nodes))
				continue;
			pa = try_alloc_fn(numa_id, npages, p2align,
					  is_user, &oom);
			if (pa) {
				rusage_add_fn(numa_id, npages, is_user);
				if (log_fn)
					log_fn(MEM_ALLOC_LOG_DISTANCE_OK,
					       current_node, numa_id, npages);
				return phys_to_virt_fn(pa);
			}
			if (i == 0 && log_fn)
				log_fn(MEM_ALLOC_LOG_DISTANCE_FIRST_MISS,
				       current_node, numa_id, npages);
		}
	}

	for (i = 0; i < nr_nodes; ++i) {
		int oom = 0;

		numa_id = mem_alloc_order_node_result(current_node, i,
				nr_nodes);
		pa = try_alloc_fn(numa_id, npages, p2align, is_user, &oom);
		if (pa) {
			rusage_add_fn(numa_id, npages, is_user);
			return phys_to_virt_fn(pa);
		}
	}

	if (log_fn)
		log_fn(MEM_ALLOC_LOG_OOM, current_node, -1, npages);
	return NULL;
}

void *mem_mckernel_allocate_aligned_pages_node_body_result(int npages,
		int p2align, ihk_mc_ap_flag flag, int pref_node, int is_user,
		uintptr_t virt_addr, int cpu_local_initialized, int nr_nodes,
		mem_current_vm_fn_t current_vm_fn,
		mem_range_policy_search_fn_t range_policy_search_fn,
		mem_lookup_memory_range_fn_t lookup_memory_range_fn,
		mem_range_is_shm_fn_t range_is_shm_fn,
		mem_policy_fields_fn_t range_policy_fields_fn,
		mem_policy_fields_fn_t vm_policy_fields_fn,
		mem_current_numa_id_fn_t current_numa_id_fn,
		mem_mckernel_alloc_policy_fn_t alloc_policy_fn)
{
	int numa_mem_policy = -1;
	int chk_shm = 0;
	unsigned long *numa_mask = NULL;
	int *il_prev = NULL;
	void *vm = NULL;
	int policy_pref_node = pref_node;
	ihk_mc_ap_flag policy_flag = flag;

	if (npages <= 0 || !current_numa_id_fn || !alloc_policy_fn)
		return NULL;

	if (cpu_local_initialized && current_vm_fn)
		vm = current_vm_fn();

	if (!vm) {
		mem_default_alloc_policy_result(flag, &policy_flag,
				&policy_pref_node, &numa_mem_policy);
	} else if (virt_addr != (uintptr_t)-1) {
		void *range_policy = NULL;

		if (range_policy_search_fn)
			range_policy = range_policy_search_fn(vm, virt_addr);

		if (range_policy) {
			if (lookup_memory_range_fn) {
				void *range = lookup_memory_range_fn(vm, virt_addr,
						virt_addr + 1);

				if (range && range_is_shm_fn)
					chk_shm = range_is_shm_fn(range);
			}
			if (range_policy_fields_fn)
				range_policy_fields_fn(range_policy,
						&numa_mem_policy, &numa_mask,
						&il_prev);
		} else if (vm_policy_fields_fn) {
			vm_policy_fields_fn(vm, &numa_mem_policy, &numa_mask,
					&il_prev);
		}
	}

	return alloc_policy_fn(npages, p2align, policy_flag,
			policy_pref_node, is_user, current_numa_id_fn(),
			nr_nodes, numa_mem_policy, chk_shm, numa_mask, il_prev);
}

void *mem_mckernel_allocate_aligned_pages_node_public_body_result(int npages,
		int p2align, ihk_mc_ap_flag flag, int pref_node, int is_user,
		uintptr_t virt_addr, int cpu_local_initialized,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_current_vm_fn_t current_vm_fn,
		mem_range_policy_search_fn_t range_policy_search_fn,
		mem_lookup_memory_range_fn_t lookup_memory_range_fn,
		mem_range_is_shm_fn_t range_is_shm_fn,
		mem_policy_fields_fn_t range_policy_fields_fn,
		mem_policy_fields_fn_t vm_policy_fields_fn,
		mem_current_numa_id_fn_t current_numa_id_fn,
		mem_mckernel_alloc_policy_fn_t alloc_policy_fn)
{
	if (!nr_nodes_fn)
		return NULL;

	return mem_mckernel_allocate_aligned_pages_node_body_result(npages,
			p2align, flag, pref_node, is_user, virt_addr,
			cpu_local_initialized, nr_nodes_fn(), current_vm_fn,
			range_policy_search_fn, lookup_memory_range_fn,
			range_is_shm_fn, range_policy_fields_fn,
			vm_policy_fields_fn, current_numa_id_fn,
			alloc_policy_fn);
}

int mem_mckernel_free_pages_body_result(void *va, int npages, int is_user,
		struct list_head *pendings, mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_phys_to_page_fn_t phys_to_page_fn,
		mem_free_in_allocator_fn_t free_in_allocator_fn,
		mem_pending_warn_fn_t warn_fn)
{
	struct page *page;

	if (!virt_to_phys_fn || !phys_to_page_fn || !free_in_allocator_fn)
		return -EINVAL;

	page = phys_to_page_fn(virt_to_phys_fn(va));
	if (mem_free_pages_pending_enqueue_result(page, pendings, npages,
				warn_fn))
		return 1;

	free_in_allocator_fn(va, npages, is_user);
	return 0;
}

int mem_mckernel_free_pages_public_body_result(void *va, int npages,
		int is_user, mem_pending_pages_fn_t pending_pages_fn,
		mem_virt_to_phys_fn_t virt_to_phys_fn,
		mem_phys_to_page_fn_t phys_to_page_fn,
		mem_free_in_allocator_fn_t free_in_allocator_fn,
		mem_pending_warn_fn_t warn_fn,
		mem_mckernel_free_pages_body_fn_t free_body_fn)
{
	struct list_head *pendings;

	if (!pending_pages_fn || !free_body_fn)
		return -EINVAL;

	pendings = pending_pages_fn();
	if (!pendings)
		return -EINVAL;

	return free_body_fn(va, npages, is_user, pendings, virt_to_phys_fn,
			phys_to_page_fn, free_in_allocator_fn, warn_fn);
}

int mem_query_free_mem_interrupt_body_result(int nr_nodes, char *memdebug_name,
		int fugaku_panic, int attached_mic, int sbox_scratch0,
		int sbox_scratch1, mem_query_free_node_pages_fn_t node_pages_fn,
		mem_query_free_log_fn_t total_log_fn,
		mem_lifecycle_void_fn_t panic_fn,
		mem_find_command_line_fn_t find_command_line_fn,
		mem_lifecycle_void_fn_t kmalloc_memcheck_fn,
		mem_lifecycle_void_fn_t pagealloc_memcheck_fn,
		mem_query_page_hash_count_fn_t page_hash_count_fn,
		mem_query_free_log_fn_t page_hash_log_fn,
		mem_query_sbox_write_fn_t sbox_write_fn)
{
	int i;
	int pages = 0;

	if (nr_nodes < 0 || !node_pages_fn)
		return -EINVAL;

	for (i = 0; i < nr_nodes; ++i)
		pages += node_pages_fn(i);

	if (total_log_fn)
		total_log_fn(pages);

	if (fugaku_panic && panic_fn)
		panic_fn();

	if (memdebug_name && find_command_line_fn &&
			find_command_line_fn(memdebug_name)) {
		if (kmalloc_memcheck_fn)
			kmalloc_memcheck_fn();
		if (pagealloc_memcheck_fn)
			pagealloc_memcheck_fn();
	}

	if (page_hash_count_fn && page_hash_log_fn)
		page_hash_log_fn(page_hash_count_fn());

	if (attached_mic && sbox_write_fn) {
		sbox_write_fn(sbox_scratch0, pages);
		sbox_write_fn(sbox_scratch1, 1);
	}

	return pages;
}

int mem_query_free_mem_interrupt_public_body_result(void *priv,
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
		mem_query_sbox_write_fn_t sbox_write_fn)
{
	(void)priv;

	if (!nr_nodes_fn)
		return -EINVAL;

	return mem_query_free_mem_interrupt_body_result(nr_nodes_fn(),
			memdebug_name, fugaku_panic, attached_mic, sbox_scratch0,
			sbox_scratch1, node_pages_fn, total_log_fn, panic_fn,
			find_command_line_fn, kmalloc_memcheck_fn,
			pagealloc_memcheck_fn, page_hash_count_fn, page_hash_log_fn,
			sbox_write_fn);
}

int mem_numa_init_body_result(struct ihk_mc_numa_node *nodes, int nr_nodes,
		int nr_chunks, int rbtree_allocator,
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
		mem_numa_panic_fn_t panic_fn)
{
	int i;
	int node_free_pages[512] = { 0 };

	if (!nodes || nr_nodes < 0 || nr_nodes > 512 || nr_chunks < 0 ||
			!get_numa_node_fn || !get_memory_chunk_fn ||
			!node_init_fn || !rusage_total_add_fn) {
		return -EINVAL;
	}

	for (i = 0; i < nr_nodes; ++i) {
		int linux_numa_id = 0;
		int type = 0;

		if (get_numa_node_fn(i, &linux_numa_id, &type) != 0) {
			if (panic_fn)
				panic_fn(i);
			return -EINVAL;
		}

		nodes[i].id = i;
		nodes[i].linux_numa_id = linux_numa_id;
		nodes[i].type = type;
		INIT_LIST_HEAD(&nodes[i].allocators);
		nodes[i].nodes_by_distance = 0;
		node_init_fn(&nodes[i], rbtree_allocator);
	}

	for (i = 0; i < nr_chunks; ++i) {
		unsigned long start = 0;
		unsigned long end = 0;
		unsigned long available_bytes;
		int available_pages;
		int numa_id = 0;
		struct ihk_mc_numa_node *node;

		get_memory_chunk_fn(i, &start, &end, &numa_id);
		if (numa_id < 0 || numa_id >= nr_nodes)
			continue;

		if (last_early_heap_phys >= start && last_early_heap_phys < end)
			start = last_early_heap_phys;
		if (end < start)
			continue;

		node = &nodes[numa_id];
		available_bytes = end - start;
		available_pages = available_bytes >> PAGE_SHIFT;

		if (rbtree_allocator) {
			if (!add_free_pages_fn)
				return -EINVAL;
			add_free_pages_fn(node, start, available_bytes);
		} else {
			void *allocator;

			if (!page_allocator_init_fn || !list_allocator_fn ||
					!pagealloc_count_fn) {
				return -EINVAL;
			}

			allocator = page_allocator_init_fn(start, end);
			if (allocator) {
				list_allocator_fn(allocator, node);
				available_pages = pagealloc_count_fn(allocator);
				available_bytes = available_pages * PAGE_SIZE;
			} else {
				available_pages = 0;
				available_bytes = 0;
			}
		}

		if (log_fn)
			log_fn(MEM_NUMA_INIT_LOG_CHUNK, numa_id,
					node->linux_numa_id, node->type, start,
					end, available_bytes, available_pages,
					rbtree_allocator);
		node_free_pages[numa_id] += available_pages;
		rusage_total_add_fn(available_bytes);
	}

	for (i = 0; i < nr_nodes; ++i) {
		unsigned long available_bytes = 0;
		int available_pages = 0;

		if (rbtree_allocator) {
			available_pages = node_free_pages[i];
			available_bytes = available_pages * PAGE_SIZE;
		}

		if (log_fn)
			log_fn(MEM_NUMA_INIT_LOG_NODE, i,
					nodes[i].linux_numa_id, nodes[i].type, 0,
					0, available_bytes, available_pages,
					rbtree_allocator);
	}

	return 0;
}

static page_table_t mem_vm_page_table_fallback(struct process_vm *vm,
		unsigned long address_space_offset,
		unsigned long page_table_offset)
{
	struct address_space *as;

	if (!vm)
		return NULL;

	as = *(struct address_space **)((char *)vm + address_space_offset);
	if (!as)
		return NULL;

	return *(page_table_t *)((char *)as + page_table_offset);
}

pte_t *mem_pt_lookup_fault_pte_body_result(struct process_vm *vm, void *virt,
		int pgshift, void **basep, size_t *sizep, int *p2alignp,
		unsigned long address_space_offset,
		unsigned long page_table_offset,
		mem_lookup_pte_fn_t lookup_pte_fn,
		mem_page_fault_process_vm_fn_t page_fault_fn,
		mem_fault_log_fn_t log_fn)
{
	page_table_t pt;
	pte_t *ptep;

	if (!lookup_pte_fn || !page_fault_fn)
		return NULL;

	pt = mem_vm_page_table_fallback(vm, address_space_offset,
			page_table_offset);
	if (!pt)
		return NULL;

	ptep = lookup_pte_fn(pt, virt, pgshift, basep, sizep, p2alignp);
	if (!ptep || !pte_is_present(ptep)) {
		page_fault_fn(vm, virt, PF_POPULATE | PF_USER);
		ptep = lookup_pte_fn(pt, virt, pgshift, basep, sizep, p2alignp);
		if (ptep && pte_is_present(ptep) && log_fn)
			log_fn(virt);
	}

	return ptep;
}

int mem_lookup_node_body_result(struct process_vm *vm, void *addr,
		unsigned long address_space_offset,
		unsigned long page_table_offset,
		mem_lookup_pte_fn_t lookup_pte_fn,
		mem_page_fault_process_vm_fn_t page_fault_fn,
		mem_phys_to_nid_fn_t phys_to_nid_fn)
{
	page_table_t pt;
	pte_t *ptep;
	int err;

	if (!lookup_pte_fn || !page_fault_fn || !phys_to_nid_fn)
		return -EINVAL;

	err = page_fault_fn(vm, addr, PF_POPULATE | PF_USER);
	if (err)
		return err;

	pt = mem_vm_page_table_fallback(vm, address_space_offset,
			page_table_offset);
	if (!pt)
		return -ENOENT;

	ptep = lookup_pte_fn(pt, addr, 0, NULL, NULL, NULL);
	if (!ptep || !pte_is_present(ptep))
		return -ENOENT;

	return phys_to_nid_fn(pte_get_phys(ptep));
}

int mem_remote_flush_tlb_array_body_result(
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
		mem_pause_fn_t pause_fn)
{
	struct address_space *as;
	struct tlb_flush_entry *flush_entry;
	cpu_set_t cpu_set_copy;
	int flush_ind;
	int bits_per_word;
	int words;
	int word_index;
	(void)cpu_id;

	if (!vm || !addr || nr_addr <= 0 || !tlb_flush_vector ||
	    vector_size <= 0 || cpu_set_bits <= 0 || !rdtsc_fn ||
	    !current_cpu_fn || !get_vector_fn || !interrupt_cpu_fn ||
	    !lock_fn || !unlock_fn || !atomic_set_fn || !atomic_inc_fn ||
	    !atomic_read_fn || !flush_single_fn || !flush_all_fn || !pause_fn) {
		return -EINVAL;
	}

	as = vm->address_space;
	if (!as)
		return -EINVAL;

	if (addr[0])
		flush_ind = (addr[0] >> PAGE_SHIFT) % vector_size;
	else
		flush_ind = rdtsc_fn() % vector_size;
	flush_entry = &tlb_flush_vector[flush_ind];

	lock_fn((unsigned long)&as->cpu_set_lock);
	memcpy(&cpu_set_copy, &as->cpu_set, sizeof(cpu_set_copy));
	unlock_fn((unsigned long)&as->cpu_set_lock);

	lock_fn((unsigned long)&flush_entry->lock);
	flush_entry->vm = vm;
	flush_entry->addr = addr;
	flush_entry->nr_addr = nr_addr;
	atomic_set_fn((unsigned long)&flush_entry->pending, 0);

	bits_per_word = sizeof(unsigned long) * 8;
	words = (cpu_set_bits + bits_per_word - 1) / bits_per_word;
	if (words > (int)(sizeof(cpu_set_copy.__bits) /
			  sizeof(cpu_set_copy.__bits[0])))
		words = sizeof(cpu_set_copy.__bits) / sizeof(cpu_set_copy.__bits[0]);
	for (word_index = 0; word_index < words; word_index++) {
		unsigned long word = cpu_set_copy.__bits[word_index];
		while (word) {
			int bit = __builtin_ctzl(word);
			int cpu = word_index * bits_per_word + bit;

			if (cpu >= cpu_set_bits)
				break;
			if (current_cpu_fn() == cpu)
				goto next_cpu_bit;
			atomic_inc_fn((unsigned long)&flush_entry->pending);
			interrupt_cpu_fn(cpu,
					 get_vector_fn(flush_ind + vector_start));
next_cpu_bit:
			word &= word - 1;
		}
	}

	if (addr[0]) {
		int i;
		for (i = 0; i < nr_addr; ++i)
			flush_single_fn(addr[i] & PAGE_MASK);
	}
	else {
		flush_all_fn();
	}

	while (atomic_read_fn((unsigned long)&flush_entry->pending) != 0)
		pause_fn();

	unlock_fn((unsigned long)&flush_entry->lock);
	return flush_ind;
}

int mem_tlb_flush_handler_body_result(int vector,
		struct tlb_flush_entry *tlb_flush_vector, int vector_size,
		int vector_start, mem_irq_save_fn_t irq_save_fn,
		mem_irq_restore_fn_t irq_restore_fn,
		mem_flush_tlb_single_fn_t flush_single_fn,
		mem_flush_tlb_all_fn_t flush_all_fn,
		mem_atomic_dec_fn_t atomic_dec_fn)
{
	struct tlb_flush_entry *flush_entry;
	unsigned long flags;
	int index;

	if (!tlb_flush_vector || vector_size <= 0 || !irq_save_fn ||
	    !irq_restore_fn || !flush_single_fn || !flush_all_fn ||
	    !atomic_dec_fn)
		return -EINVAL;

	index = vector - vector_start;
	if (index < 0 || index >= vector_size)
		return -EINVAL;

	flags = irq_save_fn();
	flush_entry = &tlb_flush_vector[index];
	if (flush_entry->addr && flush_entry->addr[0]) {
		int i;
		for (i = 0; i < flush_entry->nr_addr; ++i)
			flush_single_fn(flush_entry->addr[i] & PAGE_MASK);
	}
	else {
		flush_all_fn();
	}
	atomic_dec_fn((unsigned long)&flush_entry->pending);
	irq_restore_fn(flags);
	return 0;
}

unsigned long mem_try_alloc_node_result(struct ihk_mc_numa_node *memory_nodes,
		int nr_nodes, int numa_id, int npages, int p2align,
		int is_user, int *oomp,
		mem_rusage_check_oom_fn_t rusage_check_oom_fn,
		mem_numa_alloc_node_fn_t numa_alloc_fn)
{
	if (oomp)
		*oomp = 0;
	if (!memory_nodes || numa_id < 0 || numa_id >= nr_nodes)
		return 0;
	if (!rusage_check_oom_fn || !numa_alloc_fn)
		return 0;
	if (rusage_check_oom_fn(numa_id, npages, is_user) == -ENOMEM) {
		if (oomp)
			*oomp = 1;
		return 0;
	}

	return numa_alloc_fn(&memory_nodes[numa_id], npages, p2align);
}

unsigned long mem_try_alloc_node_public_result(
		struct ihk_mc_numa_node *memory_nodes, int numa_id, int npages,
		int p2align, int is_user, int *oomp,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_rusage_check_oom_fn_t rusage_check_oom_fn,
		mem_numa_alloc_node_fn_t numa_alloc_fn)
{
	if (!nr_nodes_fn) {
		if (oomp)
			*oomp = 0;
		return 0;
	}

	return mem_try_alloc_node_result(memory_nodes, nr_nodes_fn(), numa_id,
			npages, p2align, is_user, oomp, rusage_check_oom_fn,
			numa_alloc_fn);
}

int mem_distance_id_result(struct ihk_mc_numa_node *memory_nodes, int nr_nodes,
		int base_node, int index)
{
	if (!memory_nodes || base_node < 0 || base_node >= nr_nodes ||
			index < 0 || index >= nr_nodes)
		return -1;
	if (!memory_nodes[base_node].nodes_by_distance)
		return -1;

	return memory_nodes[base_node].nodes_by_distance[index].id;
}

int mem_distance_id_public_result(struct ihk_mc_numa_node *memory_nodes,
		int base_node, int index, mem_get_nr_numa_nodes_fn_t nr_nodes_fn)
{
	if (!nr_nodes_fn)
		return -1;

	return mem_distance_id_result(memory_nodes, nr_nodes_fn(), base_node,
			index);
}

struct ihk_mc_numa_node *mem_get_numa_node_by_distance_result(
		struct ihk_mc_numa_node *memory_nodes, int nr_nodes,
		int cpu_local_initialized, int index,
		mem_current_numa_id_fn_t current_numa_id_fn)
{
	int numa_id;
	int target_id;

	if (!cpu_local_initialized || !memory_nodes ||
			index < 0 || index >= nr_nodes || !current_numa_id_fn)
		return NULL;

	numa_id = current_numa_id_fn();
	if (numa_id < 0 || numa_id >= nr_nodes)
		return NULL;
	if (!memory_nodes[numa_id].nodes_by_distance)
		return NULL;

	target_id = memory_nodes[numa_id].nodes_by_distance[index].id;
	if (target_id < 0 || target_id >= nr_nodes)
		return NULL;

	return &memory_nodes[target_id];
}

struct ihk_mc_numa_node *mem_get_numa_node_by_distance_public_result(
		struct ihk_mc_numa_node *memory_nodes, int cpu_local_initialized,
		int index, mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_current_numa_id_fn_t current_numa_id_fn)
{
	if (!nr_nodes_fn)
		return NULL;

	return mem_get_numa_node_by_distance_result(memory_nodes, nr_nodes_fn(),
			cpu_local_initialized, index, current_numa_id_fn);
}

struct ihk_mc_numa_node *mem_get_numa_node_public_result(
		struct ihk_mc_numa_node *memory_nodes, int nr_nodes, int numa_id)
{
	if (!memory_nodes || numa_id < 0 || numa_id >= nr_nodes)
		return NULL;

	return &memory_nodes[numa_id];
}
#endif

extern unsigned long ihk_mc_get_ns_per_tsc(void);

/*
 * Page allocator tracking routines
 */

#define PAGEALLOC_TRACK_HASH_SHIFT  (8)
#define PAGEALLOC_TRACK_HASH_SIZE   (1 << PAGEALLOC_TRACK_HASH_SHIFT)
#define PAGEALLOC_TRACK_HASH_MASK   (PAGEALLOC_TRACK_HASH_SIZE - 1)

struct list_head pagealloc_track_hash[PAGEALLOC_TRACK_HASH_SIZE];
ihk_spinlock_t pagealloc_track_hash_locks[PAGEALLOC_TRACK_HASH_SIZE];

struct list_head pagealloc_addr_hash[PAGEALLOC_TRACK_HASH_SIZE];
ihk_spinlock_t pagealloc_addr_hash_locks[PAGEALLOC_TRACK_HASH_SIZE];

int pagealloc_track_initialized = 0;
int pagealloc_runcount = 0;

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

#ifdef MCKERNEL_RUST_MEM_HELPERS
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

void *mem_pagealloc_track_base_alloc_bridge(int npages, int p2align,
		ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr)
{
	return ___ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, node,
			is_user, virt_addr);
}

void mem_pagealloc_track_base_free_bridge(void *ptr, int npages,
		int is_user)
{
	___ihk_mc_free_pages(ptr, npages, is_user);
}

void *mem_pagealloc_track_meta_alloc_bridge(int size,
		ihk_mc_ap_flag flag)
{
	return ___kmalloc(size, flag);
}

void mem_pagealloc_track_meta_free_bridge(void *ptr)
{
	___kfree(ptr);
}

unsigned long mem_pagealloc_track_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

void mem_pagealloc_track_unlock_bridge(unsigned long lock_addr,
		unsigned long irqflags)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqflags);
}

void mem_pagealloc_track_noirq_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

void mem_pagealloc_track_noirq_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

void mem_pagealloc_track_spin_init_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock_addr);
}

void mem_pagealloc_track_log_bridge(int event, void *ptr, char *file,
		int line, int npages)
{
	switch (event) {
	case PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating tracking entry\n",
				"_ihk_mc_alloc_aligned_pages_node");
		break;
	case PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating file string\n",
				"_ihk_mc_alloc_aligned_pages_node");
		break;
	case PAGEALLOC_TRACK_LOG_ENTRY_ADDED:
		dkprintf("%s entry %s:%d npages: %d added\n",
				"_ihk_mc_alloc_aligned_pages_node",
				file, line, npages);
		break;
	case PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating addr entry\n",
				"_ihk_mc_alloc_aligned_pages_node");
		break;
	case PAGEALLOC_TRACK_LOG_ADDR_ADDED:
		dkprintf("%s addr_entry %p added\n",
				"_ihk_mc_alloc_aligned_pages_node", ptr);
		break;
	case PAGEALLOC_TRACK_LOG_ADDR_REMOVED:
		dkprintf("%s addr_entry %p removed\n", "_ihk_mc_free_pages",
				ptr);
		break;
	case PAGEALLOC_TRACK_LOG_ENTRY_REMOVED:
		dkprintf("%s entry %s:%d removed\n", "_ihk_mc_free_pages",
				file, line);
		break;
	case PAGEALLOC_TRACK_LOG_COVERING_FOUND:
		dkprintf("%s: found covering addr_entry: 0x%lx:%d\n",
				"_ihk_mc_free_pages", ptr, npages);
		break;
	case PAGEALLOC_TRACK_LOG_ADDR_NEXT_ADDED:
		dkprintf("%s: addr_entry_next: 0x%lx:%d\n",
				"_ihk_mc_free_pages", ptr, npages);
		break;
	case PAGEALLOC_TRACK_LOG_ADDR_MODIFIED:
		dkprintf("%s: modified addr_entry: 0x%lx:%d\n",
				"_ihk_mc_free_pages", ptr, npages);
		break;
	default:
		break;
	}
}

void mem_pagealloc_invalid_free_bridge(void *ptr, char *file, int line)
{
	kprintf("%s: ERROR: invalid deallocation for addr: 0x%lx @ %s:%d\n",
			"_ihk_mc_free_pages", ptr, file, line);
	panic("panic: invalid deallocation");
}

void mem_pagealloc_invalid_size_bridge(void *ptr, int npages,
		int alloc_npages, char *file, int line)
{
	kprintf("%s: ERROR: trying to deallocate %d pages"
			" for a %d pages allocation at %s:%d\n",
			"_ihk_mc_free_pages", npages, alloc_npages, file, line);
	panic("invalid deallocation");
}

void mem_pagealloc_leak_log_bridge(int event, void *ptr, char *file,
		int line, int size, int count, int runcount)
{
	(void)size;

	switch (event) {
	case MEM_TRACK_LEAK_DETAIL:
		dkprintf("%s memory leak: %p @ %s:%d runcount: %d\n",
				"pagealloc_memcheck", ptr, file, line, runcount);
		break;
	case MEM_TRACK_LEAK_SUMMARY:
		kprintf("%s memory leak: %s:%d cnt: %d, runcount: %d\n",
				"pagealloc_memcheck", file, line, count, runcount);
		break;
	default:
		break;
	}
}
#endif

struct dump_pase_info {
	struct ihk_dump_page_set *dump_page_set;
	struct ihk_dump_page *dump_pages;
};

/** Get the index in the map array */
#define MAP_INDEX(n)    ((n) >> 6)
/** Get the bit number in a map element */
#define MAP_BIT(n)      ((n) & 0x3f)

#ifndef MCKERNEL_RUST_MEM_HELPERS
int mem_chk_page_address_result(unsigned long mem_addr,
		mem_get_nr_memory_chunks_fn_t nr_chunks_fn,
		mem_get_memory_chunk_fn_t chunk_fn)
{
	int i, numa_id;
	unsigned long start, end;

	if (!nr_chunks_fn || !chunk_fn)
		return -1;

	for (i = 0; i < nr_chunks_fn(); i++) {
		chunk_fn(i, &start, &end, &numa_id);
		if ((mem_addr >= start) && (end >= mem_addr))
			return 0;
	}

	return -1;
}

int mem_clear_dump_page_completion_result(
		mem_dump_get_page_set_fn_t get_page_set_fn)
{
	struct ihk_dump_page_set *dump_page_set;

	if (!get_page_set_fn)
		return -EINVAL;
	dump_page_set = get_page_set_fn();
	if (!dump_page_set)
		return -EINVAL;

	dump_page_set->completion_flag = IHK_DUMP_PAGE_SET_INCOMPLETE;
	return 0;
}

int mem_dump_mark_range_result(struct dump_pase_info *dump_pase_info,
		unsigned long chunk_addr, unsigned long chunk_size, int warn_kind,
		mem_dump_warn_fn_t warn_fn)
{
	struct ihk_dump_page_set *dump_page_set;
	struct ihk_dump_page *dump_page;
	unsigned long phy_start, map_start, map_end, map_size, set_size, k;
	int i;
	int cleared = 0;

	if (!dump_pase_info || !chunk_size)
		return 0;

	dump_page_set = dump_pase_info->dump_page_set;
	dump_page = dump_pase_info->dump_pages;
	if (!dump_page_set || !dump_page)
		return 0;

	for (i = 0; i < dump_page_set->count; i++) {
		if (i) {
			dump_page = (struct ihk_dump_page *)
				((char *)dump_page +
				 ((dump_page->map_count * sizeof(unsigned long)) +
				  sizeof(struct ihk_dump_page)));
		}

		phy_start = dump_page->start;
		map_size = (dump_page->map_count << (PAGE_SHIFT + 6));

		if ((chunk_addr >= phy_start) &&
				((phy_start + map_size) >= chunk_addr)) {
			map_start = (chunk_addr - phy_start) >> PAGE_SHIFT;

			if ((phy_start + map_size) < (chunk_addr + chunk_size)) {
				set_size = map_size - (chunk_addr - phy_start);
				map_end = (map_start + (set_size >> PAGE_SHIFT));
				chunk_addr += set_size;
				chunk_size -= set_size;
			} else {
				map_end = (map_start + (chunk_size >> PAGE_SHIFT));
			}

			for (k = map_start; k < map_end; k++) {
				if (MAP_INDEX(k) >= dump_page->map_count) {
					if (warn_fn)
						warn_fn(warn_kind,
							dump_page->map_count,
							MAP_INDEX(k), map_start,
							map_end, k);
					break;
				}
				dump_page->map[MAP_INDEX(k)] &= ~(1UL << MAP_BIT(k));
				cleared++;
			}
		}
	}

	return cleared;
}

int mem_get_mem_user_page_result(struct dump_pase_info *dump_pase_info,
		unsigned long *ptep, int pgshift,
		mem_chk_page_address_fn_t chk_page_address_fn,
		mem_dump_warn_fn_t warn_fn)
{
	unsigned long phys;

	if (!ptep || pgshift < 0)
		return 0;

	if (((*ptep) & PTATTR_ACTIVE) && ((*ptep) & PTATTR_USER)) {
		phys = pte_get_phys((pte_t *)ptep);
		if (!chk_page_address_fn || chk_page_address_fn(phys) != -1) {
			mem_dump_mark_range_result(dump_pase_info, phys,
					1UL << pgshift, 1, warn_fn);
		}
	}

	return 0;
}

unsigned long mem_dump_free_pages_public_result(
		struct ihk_mc_numa_node *nodes, int node,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn)
{
	if (!nodes || !nr_nodes_fn || node < 0 || node >= nr_nodes_fn())
		return 0;

	return nodes[node].nr_free_pages;
}

void *mem_dump_first_free_chunk_public_result(
		struct ihk_mc_numa_node *nodes, int node,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn)
{
	struct rb_node *rbnode;

	if (!nodes || !nr_nodes_fn || node < 0 || node >= nr_nodes_fn())
		return NULL;

	rbnode = rb_first_safe(&nodes[node].free_chunks);
	return rbnode ? ((struct free_chunk *)((char *)(rbnode) - offsetof(struct free_chunk, node))) : NULL;
}

void *mem_dump_next_free_chunk_result(void *chunk)
{
	struct rb_node *rbnode;

	if (!chunk)
		return NULL;

	rbnode = rb_next_safe(&((struct free_chunk *)chunk)->node);
	return rbnode ? ((struct free_chunk *)((char *)(rbnode) - offsetof(struct free_chunk, node))) : NULL;
}

unsigned long mem_dump_chunk_addr_result(void *chunk)
{
	return chunk ? ((struct free_chunk *)chunk)->addr : 0;
}

unsigned long mem_dump_chunk_size_result(void *chunk)
{
	return chunk ? ((struct free_chunk *)chunk)->size : 0;
}

int mem_query_mem_free_page_result(struct dump_pase_info *dump_pase_info,
		int nr_nodes, mem_dump_chunk_count_fn_t free_pages_fn,
		mem_dump_chunk_iter_fn_t first_chunk_fn,
		mem_dump_next_chunk_fn_t next_chunk_fn,
		mem_dump_chunk_field_fn_t chunk_addr_fn,
		mem_dump_chunk_field_fn_t chunk_size_fn,
		mem_dump_warn_fn_t warn_fn)
{
	void *chunk;
	unsigned long free_page_cnt;
	int i;
	int cleared = 0;

	if (!free_pages_fn || !first_chunk_fn || !next_chunk_fn ||
			!chunk_addr_fn || !chunk_size_fn)
		return -EINVAL;

	for (i = 0; i < nr_nodes; i++) {
		for (free_page_cnt = 0, chunk = first_chunk_fn(i); chunk;
				free_page_cnt++, chunk = next_chunk_fn(chunk)) {
			if (free_page_cnt >= free_pages_fn(i))
				break;
			cleared += mem_dump_mark_range_result(dump_pase_info,
					chunk_addr_fn(chunk), chunk_size_fn(chunk),
					0, warn_fn);
		}
	}

	return cleared;
}

int mem_query_mem_free_page_public_result(
		struct dump_pase_info *dump_pase_info,
		mem_get_nr_numa_nodes_fn_t nr_nodes_fn,
		mem_dump_chunk_count_fn_t free_pages_fn,
		mem_dump_chunk_iter_fn_t first_chunk_fn,
		mem_dump_next_chunk_fn_t next_chunk_fn,
		mem_dump_chunk_field_fn_t chunk_addr_fn,
		mem_dump_chunk_field_fn_t chunk_size_fn,
		mem_dump_warn_fn_t warn_fn)
{
	if (!nr_nodes_fn)
		return -EINVAL;

	return mem_query_mem_free_page_result(dump_pase_info, nr_nodes_fn(),
			free_pages_fn, first_chunk_fn, next_chunk_fn,
			chunk_addr_fn, chunk_size_fn, warn_fn);
}

int mem_query_mem_user_page_result(struct list_head *process_hash_lists,
		int hash_size, unsigned long process_hash_list_offset,
		unsigned long process_vm_offset,
		unsigned long vm_address_space_offset,
		unsigned long address_space_page_table_offset,
		unsigned long user_end,
		mem_visit_pte_range_fn_t visit_pte_range_fn,
		mem_pte_visitor_fn_t pte_visitor_fn, void *dump_pase_info)
{
	struct list_head *head;
	struct list_head *node;
	struct list_head *next;
	int i;
	int dispatched = 0;

	if (!process_hash_lists || hash_size <= 0)
		return 0;
	if (!visit_pte_range_fn || !pte_visitor_fn)
		return -EINVAL;

	for (i = 0; i < hash_size; i++) {
		head = &process_hash_lists[i];
		for (node = head->next; node && node != head; node = next) {
			struct process *p;
			struct process_vm *vm;
			struct address_space *address_space;
			page_table_t page_table;

			next = node->next;
			p = (struct process *)((char *)node -
					process_hash_list_offset);
			vm = *(struct process_vm **)((char *)p +
					process_vm_offset);
			if (!vm)
				continue;

			address_space = *(struct address_space **)((char *)vm +
					vm_address_space_offset);
			if (!address_space)
				continue;

			page_table = *(page_table_t *)((char *)address_space +
					address_space_page_table_offset);
			if (!page_table)
				continue;

			visit_pte_range_fn(page_table, 0, (void *)user_end, 0,
					VPTEF_DEFAULT, pte_visitor_fn,
					dump_pase_info);
			dispatched++;
		}
	}

	return dispatched;
}

int mem_query_mem_areas_result(int current_cpu, int nr_cpus, int dump_level,
		mem_dump_get_page_set_fn_t get_page_set_fn,
		mem_dump_get_page_fn_t get_page_fn,
		mem_dump_query_fn_t query_user_fn,
		mem_dump_query_fn_t query_free_fn,
		mem_dump_log_fn_t log_fn)
{
	struct ihk_dump_page_set *dump_page_set;
	struct dump_pase_info dump_pase_info;

	if (nr_cpus <= 0 || current_cpu != nr_cpus - 1)
		return 0;
	if (!get_page_set_fn || !get_page_fn || !query_user_fn || !query_free_fn)
		return -EINVAL;

	dump_page_set = get_page_set_fn();
	if (!dump_page_set)
		return -EINVAL;

	if (DUMP_LEVEL_USER_UNUSED_EXCLUDE == dump_level && dump_page_set->count) {
		dump_pase_info.dump_page_set = dump_page_set;
		dump_pase_info.dump_pages = get_page_fn();
		query_user_fn((void *)&dump_pase_info);
		query_free_fn((void *)&dump_pase_info);
	}

	dump_page_set->completion_flag = IHK_DUMP_PAGE_SET_COMPLETED;
	if (log_fn)
		log_fn();
	return 1;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void pagealloc_track_init(void);
#else
void pagealloc_track_init(void)
{
	if (!pagealloc_track_initialized) {
		int i;

		pagealloc_track_initialized = 1;
		for (i = 0; i < PAGEALLOC_TRACK_HASH_SIZE; ++i) {
			ihk_mc_spinlock_init(&pagealloc_track_hash_locks[i]);
			INIT_LIST_HEAD(&pagealloc_track_hash[i]);
			ihk_mc_spinlock_init(&pagealloc_addr_hash_locks[i]);
			INIT_LIST_HEAD(&pagealloc_addr_hash[i]);
		}
	}
}
#endif

/* NOTE: Hash lock must be held */
#ifdef MCKERNEL_RUST_MEM_HELPERS
extern struct pagealloc_track_entry *__pagealloc_track_find_entry(
		char *file, int line);
#else
struct pagealloc_track_entry *__pagealloc_track_find_entry(
		char *file, int line)
{
	struct pagealloc_track_entry *entry_iter, *entry = NULL;
	int hash = (strlen(file) + line) & PAGEALLOC_TRACK_HASH_MASK;

	for (entry_iter = ((typeof(*entry_iter) *)((char *)((&pagealloc_track_hash[hash])->next) - offsetof(typeof(*entry_iter), hash))); &entry_iter->hash != (&pagealloc_track_hash[hash]); entry_iter = ((typeof(*entry_iter) *)((char *)(entry_iter->hash.next) - offsetof(typeof(*entry_iter), hash)))) {
		if (!strcmp(entry_iter->file, file) &&
				entry_iter->line == line) {
			entry = entry_iter;
			break;
		}
	}

	if (entry) {
		dkprintf("%s found entry %s:%d\n", __FUNCTION__,
				file, line);
	}
	else {
		dkprintf("%s couldn't find entry %s:%d\n", __FUNCTION__,
				file, line);
	}

	return entry;
}
#endif

/* Top level routines called from macros */
#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void *_ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
	ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr,
	char *file, int line);
#else
void *_ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
	ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr,
	char *file, int line)
{
	unsigned long irqflags;
	struct pagealloc_track_entry *entry;
	struct pagealloc_track_addr_entry *addr_entry;
	int hash, addr_hash;
	void *r = ___ihk_mc_alloc_aligned_pages_node(npages,
					p2align, flag, node, is_user, virt_addr);

	if (!memdebug || !pagealloc_track_initialized)
		return r;

	if (!r)
		return r;

	hash = (strlen(file) + line) & PAGEALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&pagealloc_track_hash_locks[hash]);

	entry = __pagealloc_track_find_entry(file, line);

	if (!entry) {
		entry = ___kmalloc(sizeof(*entry), IHK_MC_AP_NOWAIT);
		if (!entry) {
			kprintf("%s: ERROR: allocating tracking entry\n");
			goto out;
		}

		entry->line = line;
		ihk_atomic_set(&entry->alloc_count, 1);
		ihk_mc_spinlock_init(&entry->addr_list_lock);
		INIT_LIST_HEAD(&entry->addr_list);

		entry->file = ___kmalloc(strlen(file) + 1, IHK_MC_AP_NOWAIT);
		if (!entry->file) {
			kprintf("%s: ERROR: allocating file string\n");
			___kfree(entry);
			ihk_mc_spinlock_unlock(&pagealloc_track_hash_locks[hash], irqflags);
			goto out;
		}

		strcpy(entry->file, file);
		entry->file[strlen(file)] = 0;
		list_add(&entry->hash, &pagealloc_track_hash[hash]);
		dkprintf("%s entry %s:%d npages: %d added\n", __FUNCTION__,
			file, line, npages);
	}
	else {
		ihk_atomic_inc(&entry->alloc_count);
	}
	ihk_mc_spinlock_unlock(&pagealloc_track_hash_locks[hash], irqflags);

	/* Add new addr entry for this allocation entry */
	addr_entry = ___kmalloc(sizeof(*addr_entry), IHK_MC_AP_NOWAIT);
	if (!addr_entry) {
		kprintf("%s: ERROR: allocating addr entry\n");
		goto out;
	}

	addr_entry->addr = r;
	addr_entry->runcount = pagealloc_runcount;
	addr_entry->entry = entry;
	addr_entry->npages = npages;

	irqflags = ihk_mc_spinlock_lock(&entry->addr_list_lock);
	list_add(&addr_entry->list, &entry->addr_list);
	ihk_mc_spinlock_unlock(&entry->addr_list_lock, irqflags);

	/* Add addr entry to address hash */
	addr_hash = ((unsigned long)r >> 5) & PAGEALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&pagealloc_addr_hash_locks[addr_hash]);
	list_add(&addr_entry->hash, &pagealloc_addr_hash[addr_hash]);
	ihk_mc_spinlock_unlock(&pagealloc_addr_hash_locks[addr_hash], irqflags);

	dkprintf("%s addr_entry %p added\n", __FUNCTION__, r);

out:
	return r;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void _ihk_mc_free_pages(void *ptr, int npages, int is_user,
                        char *file, int line);
#else
void _ihk_mc_free_pages(void *ptr, int npages, int is_user,
                        char *file, int line)
{
	unsigned long irqflags;
	struct pagealloc_track_entry *entry;
	struct pagealloc_track_addr_entry *addr_entry_iter, *addr_entry = NULL;
	struct pagealloc_track_addr_entry *addr_entry_next = NULL;
	int hash;
	int rehash_addr_entry = 0;

	if (!memdebug || !pagealloc_track_initialized) {
		goto out;
	}

	hash = ((unsigned long)ptr >> 5) & PAGEALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&pagealloc_addr_hash_locks[hash]);
	for (addr_entry_iter = ((typeof(*addr_entry_iter) *)((char *)((&pagealloc_addr_hash[hash])->next) - offsetof(typeof(*addr_entry_iter), hash))); &addr_entry_iter->hash != (&pagealloc_addr_hash[hash]); addr_entry_iter = ((typeof(*addr_entry_iter) *)((char *)(addr_entry_iter->hash.next) - offsetof(typeof(*addr_entry_iter), hash)))) {
		if (addr_entry_iter->addr == ptr) {
			addr_entry = addr_entry_iter;
			break;
		}
	}

	if (addr_entry) {
		if (npages > addr_entry->npages) {
			kprintf("%s: ERROR: trying to deallocate %d pages"
					" for a %d pages allocation at %s:%d\n",
					__FUNCTION__,
					npages, addr_entry->npages,
					file, line);
			panic("invalid deallocation");
		}

		if (addr_entry->npages > npages) {
			addr_entry->addr += (npages * PAGE_SIZE);
			addr_entry->npages -= npages;

			/* Only rehash if haven't freed all pages yet */
			if (addr_entry->npages) {
				rehash_addr_entry = 1;
			}
		}

		list_del(&addr_entry->hash);
	}
	ihk_mc_spinlock_unlock(&pagealloc_addr_hash_locks[hash], irqflags);

	if (!addr_entry) {
		/*
		 * Deallocations that don't start at the allocated address are
		 * valid but can't be found in addr hash, scan the entire table
		 * and split the matching entry
		 */
		for (hash = 0; hash < PAGEALLOC_TRACK_HASH_SIZE; ++hash) {
			irqflags = ihk_mc_spinlock_lock(&pagealloc_addr_hash_locks[hash]);
			for (addr_entry_iter = ((typeof(*addr_entry_iter) *)((char *)((&pagealloc_addr_hash[hash])->next) - offsetof(typeof(*addr_entry_iter), hash))); &addr_entry_iter->hash != (&pagealloc_addr_hash[hash]); addr_entry_iter = ((typeof(*addr_entry_iter) *)((char *)(addr_entry_iter->hash.next) - offsetof(typeof(*addr_entry_iter), hash)))) {
				if (addr_entry_iter->addr < ptr &&
					(addr_entry_iter->addr + addr_entry_iter->npages * PAGE_SIZE)
					>= ptr + (npages * PAGE_SIZE)) {
					addr_entry = addr_entry_iter;
					break;
				}
			}

			if (addr_entry) {
				list_del(&addr_entry->hash);
			}
			ihk_mc_spinlock_unlock(&pagealloc_addr_hash_locks[hash], irqflags);

			if (addr_entry) break;
		}

		/* Still not? Invalid deallocation */
		if (!addr_entry) {
			kprintf("%s: ERROR: invalid deallocation for addr: 0x%lx @ %s:%d\n",
				__FUNCTION__, ptr, file, line);
			panic("panic: invalid deallocation");
		}

		dkprintf("%s: found covering addr_entry: 0x%lx:%d\n", __FUNCTION__,
			addr_entry->addr, addr_entry->npages);

		entry = addr_entry->entry;

		/*
		 * Now split, allocate new entry and rehash.
		 * Is there a remaining piece after the deallocation?
		 */
		if ((ptr + (npages * PAGE_SIZE)) <
				(addr_entry->addr + (addr_entry->npages * PAGE_SIZE))) {
			int addr_hash;

			addr_entry_next =
				___kmalloc(sizeof(*addr_entry_next), IHK_MC_AP_NOWAIT);
			if (!addr_entry_next) {
				kprintf("%s: ERROR: allocating addr entry prev\n", __FUNCTION__);
				goto out;
			}

			addr_entry_next->addr = ptr + (npages * PAGE_SIZE);
			addr_entry_next->npages = ((addr_entry->addr +
				(addr_entry->npages * PAGE_SIZE)) -
				(ptr + npages * PAGE_SIZE)) / PAGE_SIZE;
			addr_entry_next->runcount = addr_entry->runcount;

			addr_hash = ((unsigned long)addr_entry_next->addr >> 5) &
				PAGEALLOC_TRACK_HASH_MASK;
			irqflags = ihk_mc_spinlock_lock(&pagealloc_addr_hash_locks[addr_hash]);
			list_add(&addr_entry_next->hash, &pagealloc_addr_hash[addr_hash]);
			ihk_mc_spinlock_unlock(&pagealloc_addr_hash_locks[addr_hash], irqflags);

			/* Add to allocation entry */
			addr_entry_next->entry = entry;
			ihk_atomic_inc(&entry->alloc_count);
			ihk_mc_spinlock_lock_noirq(&entry->addr_list_lock);
			list_add(&addr_entry_next->list, &entry->addr_list);
			ihk_mc_spinlock_unlock_noirq(&entry->addr_list_lock);

			dkprintf("%s: addr_entry_next: 0x%lx:%d\n", __FUNCTION__,
					addr_entry_next->addr, addr_entry_next->npages);
		}

		/*
		 * We know that addr_entry->addr != ptr, addr_entry will cover
		 * the region before the deallocation.
		 */
		addr_entry->npages = (ptr - addr_entry->addr) / PAGE_SIZE;
		rehash_addr_entry = 1;

		dkprintf("%s: modified addr_entry: 0x%lx:%d\n", __FUNCTION__,
			addr_entry->addr, addr_entry->npages);
	}

	entry = addr_entry->entry;

	if (rehash_addr_entry) {
		int addr_hash = ((unsigned long)addr_entry->addr >> 5) &
			PAGEALLOC_TRACK_HASH_MASK;
		irqflags = ihk_mc_spinlock_lock(&pagealloc_addr_hash_locks[addr_hash]);
		list_add(&addr_entry->hash, &pagealloc_addr_hash[addr_hash]);
		ihk_mc_spinlock_unlock(&pagealloc_addr_hash_locks[addr_hash], irqflags);
		goto out;
	}

	irqflags = ihk_mc_spinlock_lock(&entry->addr_list_lock);
	list_del(&addr_entry->list);
	ihk_mc_spinlock_unlock(&entry->addr_list_lock, irqflags);

	dkprintf("%s addr_entry %p removed\n", __FUNCTION__, addr_entry->addr);
	___kfree(addr_entry);

	/* Do we need to remove tracking entry as well? */
	hash = (strlen(entry->file) + entry->line) &
		PAGEALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&pagealloc_track_hash_locks[hash]);

	if (!ihk_atomic_dec_and_test(&entry->alloc_count)) {
		ihk_mc_spinlock_unlock(&pagealloc_track_hash_locks[hash], irqflags);
		goto out;
	}

	list_del(&entry->hash);
	ihk_mc_spinlock_unlock(&pagealloc_track_hash_locks[hash], irqflags);

	dkprintf("%s entry %s:%d removed\n", __FUNCTION__,
			entry->file, entry->line);
	___kfree(entry->file);
	___kfree(entry);

out:
	___ihk_mc_free_pages(ptr, npages, is_user);
}
#endif

#ifndef MCKERNEL_RUST_MEM_HELPERS
void *ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
		ihk_mc_ap_flag flag, int node)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, node,
			IHK_MC_PG_KERNEL, -1, "lib/include/ihk/mm.h", 0);
}

void *ihk_mc_alloc_aligned_pages_node_user(int npages, int p2align,
		ihk_mc_ap_flag flag, int node, uintptr_t virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, node,
			IHK_MC_PG_USER, virt_addr, "lib/include/ihk/mm.h", 0);
}

void *ihk_mc_alloc_aligned_pages(int npages, int p2align,
		ihk_mc_ap_flag flag)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, -1,
			IHK_MC_PG_KERNEL, -1, "lib/include/ihk/mm.h", 0);
}

void *ihk_mc_alloc_aligned_pages_user(int npages, int p2align,
		ihk_mc_ap_flag flag, uintptr_t virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, -1,
			IHK_MC_PG_USER, virt_addr, "lib/include/ihk/mm.h", 0);
}

void *ihk_mc_alloc_pages(int npages, ihk_mc_ap_flag flag)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flag, -1,
			IHK_MC_PG_KERNEL, -1, "lib/include/ihk/mm.h", 0);
}

void *ihk_mc_alloc_pages_user(int npages, ihk_mc_ap_flag flag,
		uintptr_t virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flag, -1,
			IHK_MC_PG_USER, virt_addr, "lib/include/ihk/mm.h", 0);
}

void ihk_mc_free_pages(void *ptr, int npages)
{
	_ihk_mc_free_pages(ptr, npages, IHK_MC_PG_KERNEL,
			"lib/include/ihk/mm.h", 0);
}

void ihk_mc_free_pages_user(void *ptr, int npages)
{
	_ihk_mc_free_pages(ptr, npages, IHK_MC_PG_USER,
			"lib/include/ihk/mm.h", 0);
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void pagealloc_memcheck(void);
#else
void pagealloc_memcheck(void)
{
	int i;
	unsigned long irqflags;
	struct pagealloc_track_entry *entry = NULL;

	for (i = 0; i < PAGEALLOC_TRACK_HASH_SIZE; ++i) {
		irqflags = ihk_mc_spinlock_lock(&pagealloc_track_hash_locks[i]);
		for (entry = ((typeof(*entry) *)((char *)((&pagealloc_track_hash[i])->next) - offsetof(typeof(*entry), hash))); &entry->hash != (&pagealloc_track_hash[i]); entry = ((typeof(*entry) *)((char *)(entry->hash.next) - offsetof(typeof(*entry), hash)))) {
			struct pagealloc_track_addr_entry *addr_entry = NULL;
			int cnt = 0;

			ihk_mc_spinlock_lock_noirq(&entry->addr_list_lock);
			for (addr_entry = ((typeof(*addr_entry) *)((char *)((&entry->addr_list)->next) - offsetof(typeof(*addr_entry), list))); &addr_entry->list != (&entry->addr_list); addr_entry = ((typeof(*addr_entry) *)((char *)(addr_entry->list.next) - offsetof(typeof(*addr_entry), list)))) {

			dkprintf("%s memory leak: %p @ %s:%d runcount: %d\n",
				__FUNCTION__,
				addr_entry->addr,
				entry->file,
				entry->line,
				addr_entry->runcount);

				if (pagealloc_runcount != addr_entry->runcount)
					continue;

				cnt++;
			}
			ihk_mc_spinlock_unlock_noirq(&entry->addr_list_lock);

			if (!cnt)
				continue;

			kprintf("%s memory leak: %s:%d cnt: %d, runcount: %d\n",
				__FUNCTION__,
				entry->file,
				entry->line,
				cnt,
				pagealloc_runcount);
		}
		ihk_mc_spinlock_unlock(&pagealloc_track_hash_locks[i], irqflags);
	}

	++pagealloc_runcount;
}
#endif



/* Actual allocation routines */
#ifndef MCKERNEL_RUST_MEM_HELPERS
static void *___ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
	ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr)
{
	if (pa_ops)
		return pa_ops->alloc_page(npages, p2align, flag, node, is_user, virt_addr);
	else
		return early_alloc_pages(npages);
}

static void *___ihk_mc_alloc_pages(int npages, ihk_mc_ap_flag flag,
	int is_user)
{
	return ___ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flag, -1, is_user, -1);
}

static void ___ihk_mc_free_pages(void *p, int npages, int is_user)
{
	if (pa_ops)
		pa_ops->free_page(p, npages, is_user);
}

void ihk_mc_set_page_allocator(struct ihk_mc_pa_ops *ops)
{
	pagealloc_track_init();
	early_alloc_invalidate();
	pa_ops = ops;
}
#endif

/* Internal allocation routines */
static void mem_reserve_pages_log_bridge(unsigned long start,
		unsigned long end, unsigned long pages)
{
	dkprintf("reserve: %016lx - %016lx (%ld pages)\n", start, end,
	        pages);
}

static void mem_reserve_pages_range_bridge(
		struct ihk_page_allocator_desc *pa_allocator,
		unsigned long start, unsigned long end)
{
	ihk_pagealloc_reserve(pa_allocator, start, end);
}

static void mem_reserve_pages_panic_bridge(void)
{
	panic("reserve_pages: helper failed");
}

static void reserve_pages(struct ihk_page_allocator_desc *pa_allocator,
		unsigned long start, unsigned long end, int type)
{
	(void)type;
	mem_reserve_pages_public_body_result(pa_allocator,
			pa_allocator ? pa_allocator->start : 0,
			pa_allocator ? pa_allocator->end : 0,
			start, end, mem_reserve_pages_log_bridge,
			mem_reserve_pages_range_bridge,
			mem_reserve_pages_body_result,
			mem_reserve_pages_panic_bridge);
}

static int interleave_nodes(int off, unsigned long *numa_mask)
{
	return mem_interleave_nodes_result(off, numa_mask,
			PROCESS_NUMA_MASK_BITS);
}

#ifdef IHK_RBTREE_ALLOCATOR
static int mem_rusage_check_oom_bridge(int numa_id, int npages, int is_user)
{
	return rusage_check_oom(numa_id, npages, is_user);
}

static unsigned long mem_numa_alloc_node_bridge(
		struct ihk_mc_numa_node *node, int npages, int p2align)
{
	return ihk_numa_alloc_pages(node, npages, p2align);
}
#endif

static unsigned long mem_try_alloc_node_bridge(int numa_id, int npages,
		int p2align, int is_user, int *oomp)
{
#ifdef IHK_RBTREE_ALLOCATOR
	return mem_try_alloc_node_public_result(memory_nodes, numa_id, npages,
			p2align, is_user, oomp, ihk_mc_get_nr_numa_nodes,
			mem_rusage_check_oom_bridge,
			mem_numa_alloc_node_bridge);
#else
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
#endif
}

static int mem_distance_id_bridge(int base_node, int index)
{
	return mem_distance_id_public_result(memory_nodes, base_node, index,
			ihk_mc_get_nr_numa_nodes);
}

static int mem_mask_test_bridge(int numa_id, unsigned long *numa_mask)
{
	return mem_mask_test_result(numa_id, numa_mask,
			PROCESS_NUMA_MASK_BITS);
}

static void mem_rusage_page_add_bridge(int numa_id, int npages, int is_user)
{
	rusage_page_add(numa_id, npages, is_user);
}

static void *mem_phys_to_virt_bridge(unsigned long pa)
{
	return phys_to_virt(pa);
}

static void mem_mckernel_alloc_log_bridge(int event, int current_node,
		int numa_id, int npages)
{
	switch (event) {
	case MEM_ALLOC_LOG_EXPLICIT_OK:
		dkprintf("%s: explicit (node: %d) CPU @ node %d allocated "
				"%d pages from node %d\n",
				"mckernel_allocate_aligned_pages_node",
				numa_id, current_node, npages, current_node);
		break;
	case MEM_ALLOC_LOG_EXPLICIT_MISS:
#ifdef PROFILE_ENABLE
		profile_event_add(PROFILE_mpol_alloc_missed,
				  npages * PAGE_SIZE);
#endif
		dkprintf("%s: couldn't fulfill explicit NUMA request for %d pages\n",
				"mckernel_allocate_aligned_pages_node", npages);
		break;
	case MEM_ALLOC_LOG_POLICY_OK:
		dkprintf("%s: policy: CPU @ node %d allocated "
				"%d pages from node %d\n",
				"mckernel_allocate_aligned_pages_node",
				current_node, npages, current_node);
		break;
	case MEM_ALLOC_LOG_POLICY_MISS:
#ifdef PROFILE_ENABLE
		profile_event_add(PROFILE_mpol_alloc_missed,
				  npages * PAGE_SIZE);
#endif
		dkprintf("%s: couldn't fulfill user policy for %d pages\n",
			"mckernel_allocate_aligned_pages_node", npages);
		break;
	case MEM_ALLOC_LOG_DISTANCE_OK:
		dkprintf("%s: distance: CPU @ node %d allocated "
				"%d pages from node %d\n",
				"mckernel_allocate_aligned_pages_node",
				current_node, npages, numa_id);
		break;
	case MEM_ALLOC_LOG_DISTANCE_FIRST_MISS:
#ifndef ENABLE_FUGAKU_HACKS
		kprintf("%s: distance: CPU @ node %d failed to allocate "
#else
		dkprintf("%s: distance: CPU @ node %d failed to allocate "
#endif
				"%d pages from node %d\n",
				"mckernel_allocate_aligned_pages_node",
				current_node, npages, numa_id);
		break;
	case MEM_ALLOC_LOG_OOM:
		dkprintf("OOM\n", "mckernel_allocate_aligned_pages_node");
		break;
	default:
		break;
	}
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
static void *mem_current_vm_bridge(void)
{
	struct thread *thread = NULL;
	void *vm = NULL;

	if (cpu_local_var_initialized) {
		thread = get_this_cpu_local_var()->current;
		if (thread)
			vm = thread->vm;
	}

	return mem_current_vm_result(cpu_local_var_initialized, thread, vm);
}

static void *mem_range_policy_search_bridge(void *vm, unsigned long virt_addr)
{
	return vm_range_policy_search((struct process_vm *)vm, virt_addr);
}

static void *mem_lookup_memory_range_bridge(void *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range((struct process_vm *)vm, start, end);
}

static int mem_range_is_shm_bridge(void *range)
{
	struct vm_range *vm_range = range;

	if (!vm_range)
		return mem_range_is_shm_result(0, 0, 0);
	if (!vm_range->memobj)
		return mem_range_is_shm_result(1, 0, 0);

	return mem_range_is_shm_result(1, 1, vm_range->memobj->flags);
}

static void mem_range_policy_fields_bridge(void *policy,
		int *numa_mem_policy, unsigned long **numa_mask, int **il_prev)
{
	struct vm_range_numa_policy *range_policy = policy;

	mem_policy_fields_result(!!range_policy,
			range_policy ? range_policy->numa_mem_policy : -1,
			range_policy ? range_policy->numa_mask : NULL,
			range_policy ? &range_policy->il_prev : NULL,
			numa_mem_policy, numa_mask, il_prev);
}

static void mem_vm_policy_fields_bridge(void *vm, int *numa_mem_policy,
		unsigned long **numa_mask, int **il_prev)
{
	struct process_vm *process_vm = vm;

	mem_policy_fields_result(!!process_vm,
			process_vm ? process_vm->numa_mem_policy : -1,
			process_vm ? process_vm->numa_mask : NULL,
			process_vm ? &process_vm->il_prev : NULL,
			numa_mem_policy, numa_mask, il_prev);
}

static void *mem_mckernel_alloc_policy_bridge(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user,
		int current_node, int nr_nodes, int numa_mem_policy,
		int chk_shm, unsigned long *numa_mask, int *il_prevp)
{
	return mem_mckernel_alloc_policy_result(npages, p2align, flag,
			pref_node, is_user, current_node, nr_nodes,
			numa_mem_policy, chk_shm, numa_mask, il_prevp,
			mem_try_alloc_node_bridge, mem_distance_id_bridge,
			mem_mask_test_bridge, interleave_nodes,
			mem_rusage_page_add_bridge, mem_phys_to_virt_bridge,
			mem_mckernel_alloc_log_bridge);
}
#endif

static void *mckernel_allocate_aligned_pages_node(int npages, int p2align,
		ihk_mc_ap_flag flag, int pref_node, int is_user, uintptr_t virt_addr)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return mem_mckernel_allocate_aligned_pages_node_public_body_result(npages,
			p2align, flag, pref_node, is_user, virt_addr,
			cpu_local_var_initialized, ihk_mc_get_nr_numa_nodes,
			mem_current_vm_bridge, mem_range_policy_search_bridge,
			mem_lookup_memory_range_bridge, mem_range_is_shm_bridge,
			mem_range_policy_fields_bridge,
			mem_vm_policy_fields_bridge, mem_current_numa_id_bridge,
			mem_mckernel_alloc_policy_bridge);
#else
	struct vm_range_numa_policy *range_policy_iter = NULL;
	int numa_mem_policy = -1;
	struct process_vm *vm;
	struct thread *thread = NULL;
	struct vm_range *range = NULL;
	int chk_shm = 0;
	int *il_prev = NULL;
	unsigned long *numa_mask = NULL;
	int node;
	int policy_pref_node = pref_node;
	ihk_mc_ap_flag policy_flag = flag;

	if(npages <= 0)
		return NULL;

	if (cpu_local_var_initialized)
		thread = get_this_cpu_local_var()->current;
	vm = mem_current_vm_result(cpu_local_var_initialized, thread,
			thread ? thread->vm : NULL);

	/* Not yet initialized or idle process */
	if (!vm) {
		mem_default_alloc_policy_result(flag, &policy_flag,
				&policy_pref_node, &numa_mem_policy);
		goto allocate;
	}

	/* Get mempolicy user requested */
	if (virt_addr != -1) {
		range_policy_iter = vm_range_policy_search(vm, virt_addr);

		if (range_policy_iter) {
			range = lookup_process_memory_range(vm,
					(uintptr_t)virt_addr,
					((uintptr_t)virt_addr) + 1);
			if (mem_range_is_shm_result(!!range,
					range && range->memobj ? 1 : 0,
					range && range->memobj ?
					range->memobj->flags : 0)) {
				chk_shm = 1;
			}

			/* Use range policy */
			mem_policy_fields_result(1,
					range_policy_iter->numa_mem_policy,
					range_policy_iter->numa_mask,
					&range_policy_iter->il_prev,
					&numa_mem_policy, &numa_mask,
					&il_prev);
		} else {
			/* Use process policy */
			mem_policy_fields_result(1, vm->numa_mem_policy,
					vm->numa_mask, &vm->il_prev,
					&numa_mem_policy, &numa_mask,
					&il_prev);
		}
	}

allocate:
	node = ihk_mc_get_numa_id();
	return mem_mckernel_alloc_policy_result(npages, p2align, policy_flag,
			policy_pref_node, is_user, node, ihk_mc_get_nr_numa_nodes(),
			numa_mem_policy, chk_shm, numa_mask, il_prev,
			mem_try_alloc_node_bridge, mem_distance_id_bridge,
			mem_mask_test_bridge, interleave_nodes,
			mem_rusage_page_add_bridge, mem_phys_to_virt_bridge,
			mem_mckernel_alloc_log_bridge);
#endif
}

static int mem_current_numa_id_bridge(void)
{
	return ihk_mc_get_numa_id();
}

/*
 * Get NUMA node structure offsetted by index in the order of distance
 */
struct ihk_mc_numa_node *ihk_mc_get_numa_node_by_distance(int i)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return mem_get_numa_node_by_distance_public_result(memory_nodes,
			cpu_local_var_initialized, i, ihk_mc_get_nr_numa_nodes,
			mem_current_numa_id_bridge);
#else
	return mem_get_numa_node_by_distance_result(memory_nodes,
			ihk_mc_get_nr_numa_nodes(), cpu_local_var_initialized,
			i, mem_current_numa_id_bridge);
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
static unsigned long mem_virt_to_phys_bridge(void *va)
{
	return virt_to_phys(va);
}

static void *mem_get_numa_node_bridge(int numa_id)
{
	return mem_get_numa_node_public_result(memory_nodes,
			ihk_mc_get_nr_numa_nodes(), numa_id);
}

static void mem_numa_free_bridge(void *node, unsigned long addr, int npages)
{
	ihk_numa_free_pages((struct ihk_mc_numa_node *)node, addr, npages);
}

static void mem_rusage_page_sub_bridge(int numa_id, int npages, int is_user)
{
	rusage_page_sub(numa_id, npages, is_user);
}
#endif

static void __mckernel_free_pages_in_allocator(void *va, int npages,
                                               int is_user)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_free_pages_in_allocator_rbtree_result(va, npages, is_user,
			ihk_mc_get_nr_memory_chunks, ihk_mc_get_memory_chunk,
			mem_virt_to_phys_bridge, mem_get_numa_node_bridge,
			mem_numa_free_bridge, mem_rusage_page_sub_bridge);
#else
	int i;
	unsigned long pa_start = virt_to_phys(va);
	unsigned long pa_end = pa_start + (npages * PAGE_SIZE);

#ifdef IHK_RBTREE_ALLOCATOR
	for (i = 0; i < ihk_mc_get_nr_memory_chunks(); ++i) {
		unsigned long start, end;
		int numa_id;

		ihk_mc_get_memory_chunk(i, &start, &end, &numa_id);
		if (start > pa_start || end < pa_end) {
			continue;
		}

		ihk_numa_free_pages(&memory_nodes[numa_id], pa_start, npages);
		rusage_page_sub(numa_id, npages, is_user);
		break;
	}
#else
	struct ihk_page_allocator_desc *pa_allocator;

	/* Find corresponding memory allocator */
	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {

		for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[i].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[i].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {

			if (pa_start >= pa_allocator->start &&
					pa_end <= pa_allocator->end) {
				ihk_pagealloc_free(pa_allocator, pa_start, npages);
				rusage_page_sub(i, npages, is_user);
				return;
			}
		}
	}
#endif
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
static void mem_pending_free_warn_bridge(unsigned long phys)
{
	kprintf("%s: WARNING: page phys 0x%lx is not PM_NONE",
			"mckernel_free_pages", phys);
}

static struct page *mem_phys_to_page_bridge(unsigned long phys)
{
	return phys_to_page(phys);
}

static void mem_free_in_allocator_bridge(void *va, int npages, int is_user)
{
	__mckernel_free_pages_in_allocator(va, npages, is_user);
}

struct list_head *mem_pending_free_pages_bridge(void)
{
	return &get_this_cpu_local_var()->pending_free_pages;
}
#endif

static void mckernel_free_pages(void *va, int npages, int is_user)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_mckernel_free_pages_public_body_result(va, npages, is_user,
			mem_pending_free_pages_bridge,
			mem_virt_to_phys_bridge, mem_phys_to_page_bridge,
			mem_free_in_allocator_bridge,
			mem_pending_free_warn_bridge,
			mem_mckernel_free_pages_body_result);
#else
	struct list_head *pendings = &get_this_cpu_local_var()->pending_free_pages;
	struct page *page;

	page = phys_to_page(virt_to_phys(va));
	if (page) {
		if (page->mode != PM_NONE) {
			kprintf("%s: WARNING: page phys 0x%lx is not PM_NONE",
					__FUNCTION__, page->phys);
		}
		if (pendings->next != NULL) {
			page->mode = PM_PENDING_FREE;
			page->offset = npages;
			list_add_tail(&page->list, pendings);
			return;
		}
	}

	__mckernel_free_pages_in_allocator(va, npages, is_user);
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
void mem_begin_free_pages_pending_panic_bridge(void);
void mem_finish_free_pages_pending_panic_bridge(void);
#else
void begin_free_pages_pending(void) {
	struct list_head *pendings = &get_this_cpu_local_var()->pending_free_pages;

	if (pendings->next != NULL) {
		panic("begin_free_pages_pending");
	}
	INIT_LIST_HEAD(pendings);
	return;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
void mem_begin_free_pages_pending_panic_bridge(void)
{
	panic("begin_free_pages_pending");
}

void mem_pending_free_bridge(unsigned long phys, int npages,
		int is_user)
{
	__mckernel_free_pages_in_allocator(phys_to_virt(phys), npages,
			is_user);
}

void mem_finish_free_pages_pending_panic_bridge(void)
{
	panic("free_pending_pages:not PM_PENDING_FREE");
}
#else
void finish_free_pages_pending(void)
{
	struct list_head *pendings = &get_this_cpu_local_var()->pending_free_pages;
	struct page *page;
	struct page *next;

	if (pendings->next == NULL) {
		return;
	}

	for (page = ((typeof(*page) *)((char *)((pendings)->next) - offsetof(typeof(*page), list))), next = ((typeof(*page) *)((char *)(page->list.next) - offsetof(typeof(*page), list))); &page->list != (pendings); page = next, next = ((typeof(*next) *)((char *)(next->list.next) - offsetof(typeof(*next), list)))) {
		if (page->mode != PM_PENDING_FREE) {
			panic("free_pending_pages:not PM_PENDING_FREE");
		}
		page->mode = PM_NONE;
		list_del(&page->list);
		__mckernel_free_pages_in_allocator(phys_to_virt(page_to_phys(page)),
				page->offset, IHK_MC_PG_USER);
	}

	pendings->next = pendings->prev = NULL;
	return;
}
#endif

static struct ihk_mc_pa_ops allocator = {
	.alloc_page = mckernel_allocate_aligned_pages_node,
	.free_page = mckernel_free_pages,
};

void sbox_write(int offset, unsigned int value);

static int page_hash_count_pages(void);
#ifdef MCKERNEL_RUST_MEM_HELPERS
static int mem_query_free_node_pages_bridge(int node)
{
	int pages = 0;

	if (node < 0 || node >= ihk_mc_get_nr_numa_nodes())
		return 0;

#ifdef IHK_RBTREE_ALLOCATOR
	pages = memory_nodes[node].nr_free_pages;
#else
	{
		struct ihk_page_allocator_desc *pa_allocator;

		for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[node].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[node].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {
			int __pages = ihk_pagealloc_query_free(pa_allocator);

			kprintf("McKernel free pages in (0x%lx - 0x%lx): %d\n",
					pa_allocator->start, pa_allocator->end, __pages);
			pages += __pages;
		}
	}
#endif

	return pages;
}

static void mem_query_free_total_log_bridge(int pages)
{
	kprintf("McKernel free pages in total: %d\n", pages);
}

static void mem_query_free_panic_bridge(void)
{
	panic("PANIC");
}

static void mem_query_free_kmalloc_memcheck_bridge(void)
{
	extern void kmalloc_memcheck(void);

	kmalloc_memcheck();
}

static void mem_query_free_page_hash_log_bridge(int pages)
{
	kprintf("Page hash: %d pages active\n", pages);
}

static void mem_query_free_sbox_write_bridge(int offset, unsigned int value)
{
#ifdef ATTACHED_MIC
	sbox_write(offset, value);
#else
	(void)offset;
	(void)value;
#endif
}
#endif

static void query_free_mem_interrupt_handler(void *priv)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	int fugaku_panic = 0;
	int attached_mic = 0;
	int sbox_scratch0 = 0;
	int sbox_scratch1 = 0;

	(void)priv;
#ifdef ENABLE_FUGAKU_HACKS
	fugaku_panic = 1;
#endif
#ifdef ATTACHED_MIC
	attached_mic = 1;
	sbox_scratch0 = SBOX_SCRATCH0;
	sbox_scratch1 = SBOX_SCRATCH1;
	#endif

	mem_query_free_mem_interrupt_public_body_result(priv,
			ihk_mc_get_nr_numa_nodes, "memdebug", fugaku_panic,
			attached_mic, sbox_scratch0, sbox_scratch1,
			mem_query_free_node_pages_bridge,
			mem_query_free_total_log_bridge,
			mem_query_free_panic_bridge, find_command_line,
			mem_query_free_kmalloc_memcheck_bridge, pagealloc_memcheck,
			page_hash_count_pages, mem_query_free_page_hash_log_bridge,
			mem_query_free_sbox_write_bridge);
#else
	int i, pages = 0;

	(void)priv;

	/* Iterate memory allocators */
	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {
#ifdef IHK_RBTREE_ALLOCATOR
		pages += memory_nodes[i].nr_free_pages;
#else
		struct ihk_page_allocator_desc *pa_allocator;

		for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[i].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[i].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {
			int __pages = ihk_pagealloc_query_free(pa_allocator);
			kprintf("McKernel free pages in (0x%lx - 0x%lx): %d\n",
					pa_allocator->start, pa_allocator->end, __pages);
			pages += __pages;
		}
#endif
	}

	kprintf("McKernel free pages in total: %d\n", pages);
#ifdef ENABLE_FUGAKU_HACKS
	panic("PANIC");
#endif

	if (find_command_line("memdebug")) {
		extern void kmalloc_memcheck(void);

		kmalloc_memcheck();
		pagealloc_memcheck();
	}

	kprintf("Page hash: %d pages active\n", page_hash_count_pages());

#ifdef ATTACHED_MIC
	sbox_write(SBOX_SCRATCH0, pages);
	sbox_write(SBOX_SCRATCH1, 1);
#endif
#endif
}

static struct ihk_mc_interrupt_handler query_free_mem_handler = {
	.func = query_free_mem_interrupt_handler,
	.priv = NULL,
};

int gencore(struct process *proc, struct coretable **coretable,
	    int *chunks, char *cmdline, int sig);
void freecore(struct coretable **);
struct siginfo;
typedef struct siginfo siginfo_t;
unsigned long do_kill(struct thread *thread, int pid, int tid,
			int sig, siginfo_t *info, int ptracecont);

void coredump_wait(struct thread *thread)
{
	unsigned long flags;
	waitq_entry_t coredump_wq_entry;

	waitq_init_entry(&coredump_wq_entry, get_this_cpu_local_var()->current);

	if (__sync_bool_compare_and_swap(&thread->coredump_status,
					 COREDUMP_RUNNING,
					 COREDUMP_DESCHEDULED)) {
		flags = cpu_disable_interrupt_save();
		dkprintf("%s: sleeping,tid=%d\n", __func__, thread->tid);
		waitq_init(&thread->coredump_wq);
		waitq_prepare_to_wait(&thread->coredump_wq, &coredump_wq_entry,
				      PS_INTERRUPTIBLE);
		cpu_restore_interrupt(flags);
		schedule();
		waitq_finish_wait(&thread->coredump_wq, &coredump_wq_entry);
		thread->coredump_status = COREDUMP_RUNNING;
		dkprintf("%s: woken up,tid=%d\n", __func__, thread->tid);
	}
}

void coredump_wakeup(struct thread *thread)
{
	if (__sync_bool_compare_and_swap(&thread->coredump_status,
					 COREDUMP_DESCHEDULED,
					 COREDUMP_TO_BE_WOKEN)) {
		dkprintf("%s: waking up tid %d\n", __func__, thread->tid);
		waitq_wakeup(&thread->coredump_wq);
	}
}

/**
 * \brief Generate a core file and tell the host to write it out.
 *
 * \param proc A current process structure.
 * \param regs A pointer to a x86_regs structure.
 */

int coredump(struct thread *thread, void *regs, int sig)
{
	struct process *proc = thread->proc;
	struct syscall_request request IHK_DMA_ALIGN;
	int ret;
	struct coretable *coretable;
	int chunks;
	struct mcs_rwlock_node_irqsave lock, lock_dump;
	struct thread *thread_iter;
	int i, n, rank;
	int *ids = NULL;

	dkprintf("%s: pid=%d,tid=%d,coredump_barrier_count=%d\n",
		__func__, proc->pid, thread->tid, proc->coredump_barrier_count);

	if (proc->rlimit[MCK_RLIMIT_CORE].rlim_cur == 0) {
		ret = -EBUSY;
		goto out;
	}

	/* Wait until all threads save its register. */
	/* mutex coredump */
	mcs_rwlock_reader_lock(&proc->coredump_lock, &lock_dump);
	rank = __sync_fetch_and_add(&proc->coredump_barrier_count, 1);
	if (rank == 0) {
		n = 0;

		mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
		for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
			if (thread_iter != thread) {
				n++;
			}
		}
		if (n) {
			ids = kmalloc_tracked(sizeof(int) * n,
					IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!ids) {
				mcs_rwlock_reader_unlock(&proc->threads_lock,
							 &lock);
				kprintf("%s: ERROR: allocating tid table\n",
					__func__);
				ret = -ENOMEM;
				goto out;
			}
			i = 0;
			for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
				if (thread_iter != thread) {
					ids[i] = thread_iter->tid;
					i++;
				}
			}
		}
		mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);
		/* Note that when the target is sleeping on the source CPU,
		 * it will wake up and handle the signal when this thread yields
		 * in coredump_wait()
		 */
		for (i = 0; i < n; i++) {
			dkprintf("%s: calling do_kill, target tid=%d\n",
				__func__, ids[i]);
			do_kill(thread, proc->pid, ids[i], sig, NULL, 0);
		}
	}
	mcs_rwlock_reader_unlock(&proc->coredump_lock, &lock_dump);

	while (1) {
		n = 0;
		mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
		for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
			n++;
		}
		mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);
		if (n == proc->coredump_barrier_count) {
			for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
				coredump_wakeup(thread_iter);
			}
			break;
		}
		coredump_wait(thread);
	}

	/* Followers wait until dump is done to keep struct thread alive */
	if (rank != 0) {
		ret = 0;
		goto skip;
	}

	if ((ret = gencore(proc, &coretable, &chunks,
			proc->saved_cmdline, sig))) {
		kprintf("%s: ERROR: gencore returned %d\n", __func__, ret);
		goto skip;
	}

	request.number = __NR_coredump;
	request.args[0] = chunks;
	request.args[1] = virt_to_phys(coretable);
	request.args[2] = virt_to_phys(thread->proc->saved_cmdline);
	request.args[3] = (unsigned long)thread->proc->saved_cmdline_len;

	/* no data for now */
	ret = do_syscall(&request, thread->cpu_id);
	if (ret == 0) {
		kprintf("%s: INFO: coredump done\n", __func__);
	} else {
		kprintf("%s: ERROR: do_syscall failed (%d)\n",
			__func__, ret);
	}
	freecore(&coretable);

 skip:
	__sync_fetch_and_add(&proc->coredump_barrier_count2, 1);
	while (1) {
		if (n == proc->coredump_barrier_count2) {
			for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
				coredump_wakeup(thread_iter);
			}
			break;
		}
		coredump_wait(thread);
	}

 out:
	kfree_tracked(ids, __FILE__, __LINE__);
	return ret;
}

static unsigned long mem_tlb_rdtsc_bridge(void)
{
	return rdtsc();
}

static int mem_tlb_current_cpu_bridge(void)
{
	return ihk_mc_get_processor_id();
}

static void mem_tlb_noirq_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

static void mem_tlb_noirq_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

static void mem_tlb_atomic_set_bridge(unsigned long atomic_addr, int value)
{
	ihk_atomic_set((ihk_atomic_t *)atomic_addr, value);
}

static void mem_tlb_atomic_inc_bridge(unsigned long atomic_addr)
{
	ihk_atomic_inc((ihk_atomic_t *)atomic_addr);
}

static void mem_tlb_atomic_dec_bridge(unsigned long atomic_addr)
{
	ihk_atomic_dec((ihk_atomic_t *)atomic_addr);
}

static int mem_tlb_atomic_read_bridge(unsigned long atomic_addr)
{
	return ihk_atomic_read((ihk_atomic_t *)atomic_addr);
}

static int mem_tlb_get_vector_bridge(int type)
{
	return ihk_mc_get_vector(type);
}

static void mem_tlb_interrupt_cpu_bridge(int cpu, int vector)
{
	ihk_mc_interrupt_cpu(cpu, vector);
}

static void mem_tlb_flush_single_bridge(unsigned long addr)
{
	flush_tlb_single(addr);
}

static void mem_tlb_flush_all_bridge(void)
{
	flush_tlb();
}

static void mem_tlb_pause_bridge(void)
{
	cpu_pause();
}

void remote_flush_tlb_cpumask(struct process_vm *vm,
		unsigned long addr, int cpu_id)
{
	unsigned long __addr = addr;
	return remote_flush_tlb_array_cpumask(vm, &__addr, 1, cpu_id);
}

void remote_flush_tlb_array_cpumask(struct process_vm *vm,
		unsigned long *addr,
		int nr_addr,
		int cpu_id)
{
	(void)mem_remote_flush_tlb_array_body_result(vm, addr, nr_addr, cpu_id,
			tlb_flush_vector, IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,
			IHK_TLB_FLUSH_IRQ_VECTOR_START, CPU_SETSIZE,
			mem_tlb_rdtsc_bridge, mem_tlb_current_cpu_bridge,
			mem_tlb_get_vector_bridge, mem_tlb_interrupt_cpu_bridge,
			mem_tlb_noirq_lock_bridge, mem_tlb_noirq_unlock_bridge,
			mem_tlb_atomic_set_bridge, mem_tlb_atomic_inc_bridge,
			mem_tlb_atomic_read_bridge, mem_tlb_flush_single_bridge,
			mem_tlb_flush_all_bridge, mem_tlb_pause_bridge);
}

void tlb_flush_handler(int vector)
{
#ifdef PROFILE_ENABLE
	unsigned long t_s = 0;
	if (get_this_cpu_local_var()->current->profile) {
		t_s = rdtsc();
	}
#endif // PROFILE_ENABLE
	(void)mem_tlb_flush_handler_body_result(vector, tlb_flush_vector,
			IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,
			IHK_TLB_FLUSH_IRQ_VECTOR_START,
			cpu_disable_interrupt_save, cpu_restore_interrupt,
			mem_tlb_flush_single_bridge, mem_tlb_flush_all_bridge,
			mem_tlb_atomic_dec_bridge);
#ifdef PROFILE_ENABLE
	{
		if (get_this_cpu_local_var()->current->profile) {
			unsigned long t_e = rdtsc();
			profile_event_add(PROFILE_tlb_invalidate, (t_e - t_s));
			get_this_cpu_local_var()->current->profile_elapsed_ts +=
				(t_e - t_s);
		}
	}
#endif // PROFILE_ENABLE
}
#ifdef ENABLE_FUGAKU_HACKS
extern unsigned long arch_get_instruction_address(const void *reg);
#endif

static void unhandled_page_fault(struct thread *thread, void *fault_addr,
				 uint64_t reason, void *regs)
{
	const uintptr_t address = (uintptr_t)fault_addr;
	struct process_vm *vm = thread->vm;
	struct vm_range *range;
	unsigned long irqflags;

	irqflags = kprintf_lock();
	__kprintf("Page fault for 0x%lx\n", address);
	__kprintf("%s for %s access in %s mode (reserved bit %s set), "
			"it %s an instruction fetch\n",
			(reason & PF_PROT ? "protection fault" :
			 "no page found"),
			(reason & PF_WRITE ? "write" : "read"),
			(reason & PF_USER ? "user" : "kernel"),
			(reason & PF_RSVD ? "was" : "wasn't"),
			(reason & PF_INSTR ? "was" : "wasn't"));

	range = lookup_process_memory_range(vm, address, address+1);
	if (range) {
		__kprintf("address is in range, flag: 0x%lx (%s)\n",
				range->flag,
				range->memobj ? range->memobj->path : "");
		ihk_mc_pt_print_pte(vm->address_space->page_table,
				    (void *)address);
	} else {
		__kprintf("address is out of range!\n");
	}

#ifdef ENABLE_FUGAKU_HACKS
	{
		unsigned long pc = arch_get_instruction_address(regs);
		range = lookup_process_memory_range(vm, pc, pc + 1);
		if (range) {
			__kprintf("PC: 0x%lx (%lx in %s)\n",
					pc,
					(range->memobj && range->memobj->flags & MF_REG_FILE) ?
					pc - range->start + range->objoff :
					pc - range->start,
					(range->memobj && range->memobj->path) ?
						range->memobj->path : "(unknown)");
		}
	}
#endif

	kprintf_unlock(irqflags);

	/* TODO */
	ihk_mc_debug_show_interrupt_context(regs);

	if (!(reason & PF_USER)) {
		get_this_cpu_local_var()->kernel_mode_pf_regs = regs;
#ifndef ENABLE_FUGAKU_HACKS
		panic("panic: kernel mode PF");
#else
		kprintf("panic: kernel mode PF");
		for (;;) cpu_pause();
		//panic("panic: kernel mode PF");
#endif
	}

	//dkprintf("now dump a core file\n");
	//coredump(proc, regs);

#ifdef DEBUG_PRINT_MEM
	{
		uint64_t *sp = (void *)REGS_GET_STACK_POINTER(regs);

		kprintf("*rsp:%lx,*rsp+8:%lx,*rsp+16:%lx,*rsp+24:%lx,\n",
				sp[0], sp[1], sp[2], sp[3]);
	}
#endif
}


static void mcexec_v10_dump_user_bytes(const char *name, unsigned long addr)
{
	unsigned char bytes[16];
	char ascii[17];
	int rc;
	int i;

	if (addr < PAGE_SIZE || addr >= MAP_KERNEL_START) {
		return;
	}

	rc = copy_from_user(bytes, (void *)addr, sizeof(bytes));
	if (rc) {
		kprintf("mcexec_v10: fatal_user_bytes %s=0x%lx copy_failed=%d\n",
			name, addr, rc);
		return;
	}

	for (i = 0; i < (int)sizeof(bytes); i++) {
		ascii[i] = (bytes[i] >= 0x20 && bytes[i] <= 0x7e) ?
			bytes[i] : '.';
	}
	ascii[sizeof(bytes)] = '\0';

	kprintf("mcexec_v10: fatal_user_bytes %s=0x%lx "
		"b=%02x %02x %02x %02x %02x %02x %02x %02x "
		"%02x %02x %02x %02x %02x %02x %02x %02x ascii=\"%s\"\n",
		name, addr,
		bytes[0], bytes[1], bytes[2], bytes[3],
		bytes[4], bytes[5], bytes[6], bytes[7],
		bytes[8], bytes[9], bytes[10], bytes[11],
		bytes[12], bytes[13], bytes[14], bytes[15],
		ascii);
}

static void page_fault_handler(void *fault_addr, uint64_t reason, void *regs)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	static int mcexec_v10_page_fault_logs;
	static int mcexec_v10_page_fault_pid = -1;
#ifdef ENABLE_TOFU
	unsigned long addr = (unsigned long)fault_addr;
#endif
	int error;
	int pid = thread && thread->proc ? thread->proc->pid : -1;
#ifdef PROFILE_ENABLE
	uint64_t t_s = 0;
	if (thread && thread->profile)
		t_s = rdtsc();
#endif // PROFILE_ENABLE

	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
	dkprintf("%s: addr: %p, reason: %lx, regs: %p\n",
			__FUNCTION__, fault_addr, reason, regs);

	if (pid != mcexec_v10_page_fault_pid) {
		mcexec_v10_page_fault_pid = pid;
		mcexec_v10_page_fault_logs = 0;
	}
	if ((reason & PF_USER) && mcexec_v10_page_fault_logs < 128) {
		ihk_mc_user_context_t *uctx = regs;

		kprintf("mcexec_v10: page_fault cpu=%d pid=%d tid=%d addr=0x%lx reason=0x%lx rip=0x%lx sp=0x%lx error=0x%lx\n",
			ihk_mc_get_processor_id(),
			pid,
			thread ? thread->tid : -1,
			(unsigned long)fault_addr, reason,
			uctx ? uctx->gpr.rip : 0UL,
			uctx ? uctx->gpr.rsp : 0UL,
			uctx ? uctx->gpr.error : 0UL);
		mcexec_v10_page_fault_logs++;
	}

	preempt_disable();
	++get_this_cpu_local_var()->in_page_fault;
	if (get_this_cpu_local_var()->in_page_fault > 1) {
		kprintf("%s: PF in PF??\n", __func__);
		cpu_disable_interrupt();
		if (!(reason & PF_USER)) {
			get_this_cpu_local_var()->kernel_mode_pf_regs = regs;
			panic("panic: kernel mode PF in PF");
		}
		while (1) {
			panic("PANIC");
		}
	}

	cpu_enable_interrupt();

#ifdef ENABLE_TOFU
	if (!(reason & PF_USER) &&
			(addr > 0xffff000000000000 &&
			 addr < 0xffff800000000000)) {
		int error;
		int ihk_mc_linux_pt_virt_to_phys_size(struct page_table *pt,
				const void *virt,
				unsigned long *phys,
				unsigned long *size);

		unsigned long phys, size;
		enum ihk_mc_pt_attribute attr = PTATTR_WRITABLE | PTATTR_ACTIVE;

		if (ihk_mc_linux_pt_virt_to_phys_size(ihk_mc_get_linux_kernel_pgt(),
					fault_addr, &phys, &size) < 0) {
			kprintf("%s: failed to resolve 0x%lx from Linux PT..\n",
				__func__, addr);
			goto out_linux;	
		}

retry_linux:
		if ((error = ihk_mc_pt_set_page(NULL, fault_addr, phys, attr)) < 0) {
			if (error == -EBUSY) {
				kprintf("%s: WARNING: updating 0x%lx -> 0x%lx"
						" to reflect Linux kernel mapping..\n",
						__func__, addr, phys);
				ihk_mc_clear_kernel_range(fault_addr, fault_addr + PAGE_SIZE);
				goto retry_linux;
			}
			else {
				kprintf("%s: failed to set up 0x%lx -> 0x%lx Linux kernel mapping..\n",
						__func__, addr, phys);
				goto out_linux;
			}
		}

		dkprintf("%s: Linux kernel mapping 0x%lx -> 0x%lx set\n",
				__func__, addr, phys);
		goto out_ok;
	}
out_linux:
#endif

	if ((uintptr_t)fault_addr < PAGE_SIZE || !thread) {
		error = -EINVAL;
	} else {
		error = page_fault_process_vm(thread->vm, fault_addr, reason);
	}
	if (error) {
		struct siginfo info;

		if (error == -ECANCELED) {
			dkprintf("process is exiting, terminate.\n");

			preempt_enable();
			terminate(0, SIGSEGV);
			// no return
		}

		kprintf("%s fault VM failed for TID: %d, addr: 0x%lx, reason: %d, error: %d\n",
			__func__, thread ? thread->tid : -1, fault_addr,
			reason, error);
		if (reason & PF_USER) {
			ihk_mc_user_context_t *uctx = regs;
			unsigned long stack_words[8];
			int stack_rc = -EINVAL;
			static const char *stack_labels[8] = {
				"q0", "q1", "q2", "q3",
				"q4", "q5", "q6", "q7",
			};
			int i;

			kprintf("mcexec_v10: fatal_page_fault cpu=%d pid=%d tid=%d addr=0x%lx reason=0x%lx fault_error=%d rip=0x%lx sp=0x%lx rax=0x%lx rdi=0x%lx rsi=0x%lx rdx=0x%lx r10=0x%lx\n",
				ihk_mc_get_processor_id(),
				pid,
				thread ? thread->tid : -1,
				(unsigned long)fault_addr, reason, error,
				uctx ? uctx->gpr.rip : 0UL,
				uctx ? uctx->gpr.rsp : 0UL,
				uctx ? uctx->gpr.rax : 0UL,
				uctx ? uctx->gpr.rdi : 0UL,
				uctx ? uctx->gpr.rsi : 0UL,
				uctx ? uctx->gpr.rdx : 0UL,
				uctx ? uctx->gpr.r10 : 0UL);
			if (uctx) {
				kprintf("mcexec_v10: fatal_regs2 cpu=%d pid=%d tid=%d rbx=0x%lx rcx=0x%lx r8=0x%lx r9=0x%lx r11=0x%lx r12=0x%lx r13=0x%lx r14=0x%lx r15=0x%lx\n",
					ihk_mc_get_processor_id(),
					pid,
					thread ? thread->tid : -1,
					uctx->gpr.rbx,
					uctx->gpr.rcx,
					uctx->gpr.r8,
					uctx->gpr.r9,
					uctx->gpr.r11,
					uctx->gpr.r12,
					uctx->gpr.r13,
					uctx->gpr.r14,
					uctx->gpr.r15);
				mcexec_v10_dump_user_bytes("rsi", uctx->gpr.rsi);
				mcexec_v10_dump_user_bytes("rdx", uctx->gpr.rdx);
				mcexec_v10_dump_user_bytes("r10", uctx->gpr.r10);
				mcexec_v10_dump_user_bytes("r11", uctx->gpr.r11);
			}
			if (uctx && uctx->gpr.rsp >= PAGE_SIZE &&
			    uctx->gpr.rsp < MAP_KERNEL_START) {
				stack_rc = copy_from_user(stack_words,
							  (void *)uctx->gpr.rsp,
							  sizeof(stack_words));
				if (!stack_rc) {
					kprintf("mcexec_v10: fatal_stack sp=0x%lx q0=0x%lx q1=0x%lx q2=0x%lx q3=0x%lx q4=0x%lx q5=0x%lx q6=0x%lx q7=0x%lx\n",
						uctx->gpr.rsp,
						stack_words[0], stack_words[1],
						stack_words[2], stack_words[3],
						stack_words[4], stack_words[5],
						stack_words[6], stack_words[7]);
					for (i = 0; i < 8; i++) {
						mcexec_v10_dump_user_bytes(
							stack_labels[i],
							stack_words[i]);
					}
				}
				else {
					kprintf("mcexec_v10: fatal_stack sp=0x%lx copy_failed=%d\n",
						uctx->gpr.rsp, stack_rc);
				}
			}
		}
		unhandled_page_fault(thread, fault_addr, reason, regs);
		--get_this_cpu_local_var()->in_page_fault;
		preempt_enable();

#ifdef ENABLE_FUGAKU_DEBUG
		kprintf("%s: sending SIGSTOP to TID: %d\n", __func__, thread->tid);
		do_kill(thread, thread->proc->pid, thread->tid, SIGSTOP, NULL, 0);
		goto out;
#endif

		memset(&info, '\0', sizeof info);
		if (error == -ERANGE) {
			info.si_signo = SIGBUS;
			info.si_code = BUS_ADRERR;
			info._sifields._sigfault.si_addr = fault_addr;
			set_signal(SIGBUS, regs, &info);
		}
		else {
			struct vm_range *range = NULL;

			info.si_signo = SIGSEGV;
			info.si_code = SEGV_MAPERR;
			if (thread)
				range = lookup_process_memory_range(thread->vm,
						(uintptr_t)fault_addr,
						((uintptr_t)fault_addr) + 1);
			if (range)
				info.si_code = SEGV_ACCERR;
			info._sifields._sigfault.si_addr = fault_addr;
			set_signal(SIGSEGV, regs, &info);
		}
		goto out;
	}

#ifdef ENABLE_TOFU
out_ok:
#endif
	error = 0;
	--get_this_cpu_local_var()->in_page_fault;
	preempt_enable();
out:
	dkprintf("%s: addr: %p, reason: %lx, regs: %p -> error: %d\n",
			__FUNCTION__, fault_addr, reason, regs, error);
	if(interrupt_from_user(regs)){
		cpu_enable_interrupt();
		check_need_resched();
		check_signal(0, regs, -1);
	}
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
#ifdef PROFILE_ENABLE
	if (thread && thread->profile)
		profile_event_add(PROFILE_page_fault, (rdtsc() - t_s));
#endif // PROFILE_ENABLE
	return;
}

static struct ihk_page_allocator_desc *page_allocator_init(uint64_t start, 
		uint64_t end)
{
	struct ihk_page_allocator_desc *pa_allocator;
	unsigned long page_map_pa, pages;
	void *page_map;
	unsigned int i;
	extern char _end[];
	unsigned long phys_end = virt_to_phys(_end);

	start &= PAGE_MASK;
	pa_start = (start + PAGE_SIZE - 1) & PAGE_MASK;
	pa_end = end & PAGE_MASK;

#ifdef ATTACHED_MIC
	/* 
	 * Can't allocate in reserved area 
	 * TODO: figure this out automatically! 
	*/
	page_map_pa = 0x100000;
#else
	if (pa_start <= phys_end && phys_end <= pa_end) {
		page_map_pa = virt_to_phys(get_last_early_heap());
	}
	else {
		page_map_pa = pa_start;
	}
#endif

	page_map = phys_to_virt(page_map_pa);

	pa_allocator = __ihk_pagealloc_init(pa_start, pa_end - pa_start,
	                                    PAGE_SIZE, page_map, &pages);

	reserve_pages(pa_allocator, page_map_pa,
			page_map_pa + pages * PAGE_SIZE, 0);

	if (pa_start < start) {
		reserve_pages(pa_allocator, pa_start, start, 0);
	}

	/* BIOS reserved ranges */
	for (i = 1; i <= ihk_mc_get_memory_address(IHK_MC_NR_RESERVED_AREAS, 0);
	     ++i) {
		reserve_pages(pa_allocator,
				ihk_mc_get_memory_address(IHK_MC_RESERVED_AREA_START, i),
				ihk_mc_get_memory_address(IHK_MC_RESERVED_AREA_END, i), 0);
	}

	ihk_mc_reserve_arch_pages(pa_allocator, pa_start, pa_end, reserve_pages);

	return pa_allocator;
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
static int mem_numa_get_node_info_bridge(int node, int *linux_numa_id,
		int *type)
{
	return ihk_mc_get_numa_node(node, linux_numa_id, type);
}

static void mem_numa_node_init_bridge(struct ihk_mc_numa_node *node,
		int rbtree_allocator)
{
	(void)node;
	(void)rbtree_allocator;
#ifdef IHK_RBTREE_ALLOCATOR
	if (rbtree_allocator) {
		ihk_atomic_set(&node->zeroing_workers, 0);
		ihk_atomic_set(&node->nr_to_zero_pages, 0);
		node->free_chunks.rb_node = 0;
		init_llist_head(&node->zeroed_list);
		init_llist_head(&node->to_zero_list);
		mcs_lock_init(&node->lock);
		node->min_addr = 0xFFFFFFFFFFFFFFFF;
		node->max_addr = 0;
		node->nr_pages = 0;
		node->nr_free_pages = 0;
	}
#endif
}

static void mem_numa_add_free_pages_bridge(struct ihk_mc_numa_node *node,
		unsigned long start, unsigned long len)
{
#ifdef IHK_RBTREE_ALLOCATOR
	ihk_numa_add_free_pages(node, start, len);
#else
	(void)node;
	(void)start;
	(void)len;
#endif
}

static void *mem_numa_page_allocator_init_bridge(unsigned long start,
		unsigned long end)
{
	return page_allocator_init(start, end);
}

static void mem_numa_list_allocator_bridge(void *allocator,
		struct ihk_mc_numa_node *node)
{
	struct ihk_page_allocator_desc *desc = allocator;

	if (desc && node)
		list_add_tail(&desc->list, &node->allocators);
}

static unsigned long mem_numa_pagealloc_count_bridge(void *allocator)
{
	return allocator ? ihk_pagealloc_count(allocator) : 0;
}

static void mem_numa_rusage_total_add_bridge(unsigned long bytes)
{
	rusage_total_memory_add(bytes);
}

static void mem_numa_init_log_bridge(int event, int node, int linux_numa_id,
		int type, unsigned long start, unsigned long end,
		unsigned long bytes, int pages, int rbtree_allocator)
{
	switch (event) {
	case MEM_NUMA_INIT_LOG_CHUNK:
		kprintf("Physical memory: 0x%lx - 0x%lx, %lu bytes, "
				"%d pages available @ NUMA: %d\n",
				start, end, bytes, pages, node);
		break;
	case MEM_NUMA_INIT_LOG_NODE:
#ifdef IHK_RBTREE_ALLOCATOR
		if (rbtree_allocator) {
			kprintf("NUMA: %d, Linux NUMA: %d, type: %d, "
					"available bytes: %lu, pages: %d\n",
					node, linux_numa_id, type, bytes, pages);
			break;
		}
#endif
		(void)rbtree_allocator;
		kprintf("NUMA: %d, Linux NUMA: %d, type: %d\n",
				node, linux_numa_id, type);
		break;
	default:
		break;
	}
}

static void mem_numa_panic_bridge(int node)
{
	kprintf("%s: error: obtaining NUMA info for node %d\n",
			"numa_init", node);
	panic("");
}
#endif

static void numa_init(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	int rbtree_allocator = 0;

#ifdef IHK_RBTREE_ALLOCATOR
	rbtree_allocator = 1;
#endif

	mem_numa_init_body_result(memory_nodes, ihk_mc_get_nr_numa_nodes(),
			ihk_mc_get_nr_memory_chunks(), rbtree_allocator,
			virt_to_phys(get_last_early_heap()),
			mem_numa_get_node_info_bridge, ihk_mc_get_memory_chunk,
			mem_numa_node_init_bridge, mem_numa_add_free_pages_bridge,
			mem_numa_page_allocator_init_bridge,
			mem_numa_list_allocator_bridge,
			mem_numa_pagealloc_count_bridge,
			mem_numa_rusage_total_add_bridge,
			mem_numa_init_log_bridge, mem_numa_panic_bridge);
#else
	int i, j;

	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {
		int linux_numa_id, type;

		if (ihk_mc_get_numa_node(i, &linux_numa_id, &type) != 0) {
			kprintf("%s: error: obtaining NUMA info for node %d\n",
					__FUNCTION__, i);
			panic("");
		}

		memory_nodes[i].id = i;
		memory_nodes[i].linux_numa_id = linux_numa_id;
		memory_nodes[i].type = type;
		INIT_LIST_HEAD(&memory_nodes[i].allocators);
		memory_nodes[i].nodes_by_distance = 0;
#ifdef IHK_RBTREE_ALLOCATOR
		ihk_atomic_set(&memory_nodes[i].zeroing_workers, 0);
		ihk_atomic_set(&memory_nodes[i].nr_to_zero_pages, 0);
		memory_nodes[i].free_chunks.rb_node = 0;
		init_llist_head(&memory_nodes[i].zeroed_list);
		init_llist_head(&memory_nodes[i].to_zero_list);
		mcs_lock_init(&memory_nodes[i].lock);
		memory_nodes[i].min_addr = 0xFFFFFFFFFFFFFFFF;
		memory_nodes[i].max_addr = 0;
		memory_nodes[i].nr_pages = 0;
		memory_nodes[i].nr_free_pages = 0;
#endif
	}

	for (j = 0; j < ihk_mc_get_nr_memory_chunks(); ++j) {
		unsigned long start, end;
		int numa_id;
#ifndef IHK_RBTREE_ALLOCATOR
		struct ihk_page_allocator_desc *allocator;
#endif

		ihk_mc_get_memory_chunk(j, &start, &end, &numa_id);

		if (virt_to_phys(get_last_early_heap()) >= start &&
				virt_to_phys(get_last_early_heap()) < end) {
			dkprintf("%s: start from 0x%lx\n",
					__FUNCTION__, virt_to_phys(get_last_early_heap()));
			start = virt_to_phys(get_last_early_heap());
		}

#ifdef IHK_RBTREE_ALLOCATOR
		ihk_numa_add_free_pages(&memory_nodes[numa_id], start, end - start);
#else
		allocator = page_allocator_init(start, end);
		list_add_tail(&allocator->list, &memory_nodes[numa_id].allocators);
#endif

#ifdef IHK_RBTREE_ALLOCATOR
		kprintf("Physical memory: 0x%lx - 0x%lx, %lu bytes, %d pages available @ NUMA: %d\n",
				start, end,
				end - start,
				(end - start) >> PAGE_SHIFT,
				numa_id);
#else
		kprintf("Physical memory: 0x%lx - 0x%lx, %lu bytes, %d pages available @ NUMA: %d\n",
				start, end,
				ihk_pagealloc_count(allocator) * PAGE_SIZE,
				ihk_pagealloc_count(allocator),
				numa_id);
#endif
#ifdef IHK_RBTREE_ALLOCATOR
		rusage_total_memory_add(end - start);
#else
		rusage_total_memory_add(ihk_pagealloc_count(allocator) *
				PAGE_SIZE);
#endif
	}

	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {
#ifdef IHK_RBTREE_ALLOCATOR
		kprintf("NUMA: %d, Linux NUMA: %d, type: %d, "
				"available bytes: %lu, pages: %d\n",
				i, memory_nodes[i].linux_numa_id, memory_nodes[i].type,
				memory_nodes[i].nr_free_pages * PAGE_SIZE,
				memory_nodes[i].nr_free_pages);
#else
		kprintf("NUMA: %d, Linux NUMA: %d, type: %d\n",
				i, memory_nodes[i].linux_numa_id, memory_nodes[i].type);
#endif
	}
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
static struct node_distance *mem_numa_distances_alloc_bridge(int npages,
		unsigned long flag)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

static void mem_numa_distances_alloc_fail_log_bridge(int node)
{
	kprintf("%s: error: allocating nodes_by_distance\n",
			"numa_distances_init");
}

static void mem_numa_distances_log_bridge(int node,
		struct node_distance *distances, int nr_nodes)
{
	char buf[1024];
	char *pbuf = buf;
	int j;

	pbuf += snprintf(pbuf, 1024, "NUMA %d distances: ", node);
	for (j = 0; j < nr_nodes; ++j) {
		pbuf += snprintf(pbuf, 1024 - (pbuf - buf),
				"%d (%d), ",
				distances[j].id,
				distances[j].distance);
	}
	kprintf("%s\n", buf);
}
#endif

static void numa_distances_init()
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_numa_distances_init_public_result(memory_nodes,
			ihk_mc_get_nr_numa_nodes, mem_numa_distances_alloc_bridge,
			ihk_mc_get_numa_distance,
			mem_numa_distances_alloc_fail_log_bridge,
			mem_numa_distances_log_bridge);
#else
	int i, j, swapped;

	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {
		/* TODO: allocate on target node */
		memory_nodes[i].nodes_by_distance =
			_ihk_mc_alloc_aligned_pages_node((sizeof(struct node_distance) *
						ihk_mc_get_nr_numa_nodes() + PAGE_SIZE - 1)
					>> PAGE_SHIFT, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);

		if (!memory_nodes[i].nodes_by_distance) {
			kprintf("%s: error: allocating nodes_by_distance\n",
				__FUNCTION__);
			continue;
		}

		for (j = 0; j < ihk_mc_get_nr_numa_nodes(); ++j) {
			memory_nodes[i].nodes_by_distance[j].id = j;
			memory_nodes[i].nodes_by_distance[j].distance =
				ihk_mc_get_numa_distance(i, j);
		}

		/* Sort by distance and node ID */
		swapped = 1;
		while (swapped) {
			swapped = 0;
			for (j = 1; j < ihk_mc_get_nr_numa_nodes(); ++j) {
				if ((memory_nodes[i].nodes_by_distance[j - 1].distance >
							memory_nodes[i].nodes_by_distance[j].distance) ||
						((memory_nodes[i].nodes_by_distance[j - 1].distance ==
						  memory_nodes[i].nodes_by_distance[j].distance) &&
						 (memory_nodes[i].nodes_by_distance[j - 1].id >
						  memory_nodes[i].nodes_by_distance[j].id))) {
					memory_nodes[i].nodes_by_distance[j - 1].id ^=
						memory_nodes[i].nodes_by_distance[j].id;
					memory_nodes[i].nodes_by_distance[j].id ^=
						memory_nodes[i].nodes_by_distance[j - 1].id;
					memory_nodes[i].nodes_by_distance[j - 1].id ^=
						memory_nodes[i].nodes_by_distance[j].id;

					memory_nodes[i].nodes_by_distance[j - 1].distance ^=
						memory_nodes[i].nodes_by_distance[j].distance;
					memory_nodes[i].nodes_by_distance[j].distance ^=
						memory_nodes[i].nodes_by_distance[j - 1].distance;
					memory_nodes[i].nodes_by_distance[j - 1].distance ^=
						memory_nodes[i].nodes_by_distance[j].distance;
					swapped = 1;
				}
			}
		}
		{
			char buf[1024];
			char *pbuf = buf;

			pbuf += snprintf(pbuf, 1024, "NUMA %d distances: ", i);
			for (j = 0; j < ihk_mc_get_nr_numa_nodes(); ++j) {
				pbuf += snprintf(pbuf, 1024 - (pbuf - buf),
						"%d (%d), ",
						memory_nodes[i].nodes_by_distance[j].id,
						memory_nodes[i].nodes_by_distance[j].distance);
			}
			kprintf("%s\n", buf);
		}
	}
#endif
}

static ssize_t numa_sysfs_show_meminfo(struct sysfs_ops *ops,
		void *instance, void *buf, size_t size)
{
#ifdef IHK_RBTREE_ALLOCATOR
	struct ihk_mc_numa_node *node =
		(struct ihk_mc_numa_node *)instance;
	char *sbuf = (char *)buf;
#endif
	int len = 0;

#ifdef IHK_RBTREE_ALLOCATOR
	len += snprintf(&sbuf[len], size - len, "Node %d MemTotal:%15d kB\n",
			node->id,
			node->nr_pages << (PAGE_SHIFT - 10));
	len += snprintf(&sbuf[len], size - len, "Node %d MemFree:%16d kB\n",
			node->id,
			node->nr_free_pages << (PAGE_SHIFT - 10));
	len += snprintf(&sbuf[len], size - len, "Node %d MemUsed:%16d kB\n",
			node->id,
			(node->nr_pages - node->nr_free_pages)
				<< (PAGE_SHIFT - 10));
#endif

	return len;
}

struct sysfs_ops numa_sysfs_meminfo = {
	.show = &numa_sysfs_show_meminfo,
};

void numa_sysfs_setup(void) {
	int i;
	int error;
	char path[PATH_MAX];

	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {
		snprintf(path, PATH_MAX,
			 "/sys/devices/system/node/node%d/meminfo", i);

		error = sysfs_createf(&numa_sysfs_meminfo, &memory_nodes[i],
				0444, path);
		if (error) {
			kprintf("%s: ERROR: creating %s\n", __FUNCTION__, path);
		}
	}
}

#define PHYS_PAGE_HASH_SHIFT	(10)
#define PHYS_PAGE_HASH_SIZE     (1 << PHYS_PAGE_HASH_SHIFT)
#define PHYS_PAGE_HASH_MASK     (PHYS_PAGE_HASH_SIZE - 1)

/*
 * Page hash only tracks pages that are mapped in non-anymous mappings
 * and thus it is initially empty.
 */
struct list_head page_hash[PHYS_PAGE_HASH_SIZE];
ihk_spinlock_t page_hash_locks[PHYS_PAGE_HASH_SIZE];

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

static unsigned long page_hash_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void page_hash_unlock_bridge(unsigned long lock_addr,
		unsigned long flags)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, flags);
}

static void page_hash_lock_init_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock_addr);
}

static struct page *page_hash_alloc_bridge(unsigned long size, int flag)
{
	return kmalloc_tracked(size, flag, __FILE__, __LINE__);
}

static void page_init(void)
{
	page_hash_tables_init_body_result((unsigned long)page_hash,
			(unsigned long)page_hash_locks, PHYS_PAGE_HASH_SIZE,
			sizeof(page_hash[0]), sizeof(page_hash_locks[0]),
			page_hash_lock_init_bridge, page_hash_bucket_init_result);
}

static int page_hash_count_pages(void)
{
	return page_hash_count_pages_body_result((unsigned long)page_hash,
			(unsigned long)page_hash_locks, PHYS_PAGE_HASH_SIZE,
			sizeof(page_hash[0]), sizeof(page_hash_locks[0]),
			page_hash_lock_bridge, page_hash_unlock_bridge,
			page_hash_count_all_result);
}

struct page *phys_to_page(uintptr_t phys)
{
	return phys_to_page_lookup_body_result(phys,
			(unsigned long)page_hash, (unsigned long)page_hash_locks,
			PAGE_SHIFT, PHYS_PAGE_HASH_MASK, sizeof(page_hash[0]),
			sizeof(page_hash_locks[0]), page_hash_lock_bridge,
			page_hash_unlock_bridge,
			phys_to_page_lookup_orchestrate_result);
}

#ifdef MCKERNEL_RUST_PAGE_HELPERS
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
#else
uintptr_t page_to_phys(struct page *page)
{
	return page ? page->phys : 0;
}

void page_map_count_inc_result(struct page *page)
{
	ihk_atomic_inc(&page->count);
}

void page_map_body_result(struct page *page,
		page_map_count_inc_fn_t count_inc_fn)
{
	if (count_inc_fn) {
		count_inc_fn(page);
	}
}

int page_is_in_memobj_body_result(struct page *page)
{
	return page ? page_mode_in_memobj_result(page->mode) : 0;
}

int page_is_multi_mapped_body_result(struct page *page)
{
	return page ? page_multi_mapped_result(ihk_atomic_read(&page->count)) : 0;
}

void page_map(struct page *page)
{
	page_map_body_result(page, page_map_count_inc_result);
}

int page_is_in_memobj(struct page *page)
{
	return page_is_in_memobj_body_result(page);
}

int page_is_multi_mapped(struct page *page)
{
	return page_is_multi_mapped_body_result(page);
}

int page_unmap_locked_result(struct page *page)
{
	if (ihk_atomic_sub_return(1, &page->count) > 0) {
		return 0;
	}

	list_del(&page->hash);
	return 1;
}

int page_insert_hash_init_result(struct page *page, struct list_head *hash_head,
		uint64_t phys)
{
	if (!page || !hash_head) {
		return 0;
	}

	list_add(&page->hash, hash_head);
	page->phys = phys;
	page->mode = PM_NONE;
	INIT_LIST_HEAD(&page->list);
	ihk_atomic_set(&page->count, 0);
	return 1;
}

struct page *page_hash_lookup_result(struct list_head *hash_head,
		uint64_t phys)
{
	struct page *page_iter;

	if (!hash_head) {
		return NULL;
	}

	for (page_iter = ((typeof(*page_iter) *)((char *)((hash_head)->next) - offsetof(typeof(*page_iter), hash))); &page_iter->hash != (hash_head); page_iter = ((typeof(*page_iter) *)((char *)(page_iter->hash.next) - offsetof(typeof(*page_iter), hash)))) {
		if (page_iter->phys == phys) {
			return page_iter;
		}
	}

	return NULL;
}

int page_hash_bucket_init_result(struct list_head *hash_head)
{
	if (!hash_head) {
		return 0;
	}

	INIT_LIST_HEAD(hash_head);
	return 1;
}

int page_hash_tables_init_body_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_init_fn_t lock_init_fn,
		page_hash_bucket_init_fn_t bucket_init_fn)
{
	int i, initialized = 0;

	if (!hash_heads_addr || !locks_addr || bucket_count < 0 ||
			!hash_head_stride || !lock_stride ||
			!lock_init_fn || !bucket_init_fn) {
		return -EINVAL;
	}

	for (i = 0; i < bucket_count; ++i) {
		struct list_head *hash_head = (struct list_head *)
			(hash_heads_addr + hash_head_stride * i);
		unsigned long lock_addr = locks_addr + lock_stride * i;

		lock_init_fn(lock_addr);
		initialized += bucket_init_fn(hash_head) ? 1 : 0;
	}

	return initialized;
}

int page_hash_count_bucket_result(struct list_head *hash_head)
{
	struct page *page_iter;
	int count = 0;

	if (!hash_head) {
		return 0;
	}

	for (page_iter = ((typeof(*page_iter) *)((char *)((hash_head)->next) - offsetof(typeof(*page_iter), hash))); &page_iter->hash != (hash_head); page_iter = ((typeof(*page_iter) *)((char *)(page_iter->hash.next) - offsetof(typeof(*page_iter), hash)))) {
		++count;
	}

	return count;
}

int page_hash_count_all_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn)
{
	int i, count = 0;

	if (!hash_heads_addr || !locks_addr || bucket_count < 0 ||
			!hash_head_stride || !lock_stride ||
			!lock_fn || !unlock_fn) {
		return -EINVAL;
	}

	for (i = 0; i < bucket_count; ++i) {
		struct list_head *hash_head = (struct list_head *)
			(hash_heads_addr + hash_head_stride * i);
		unsigned long lock_addr = locks_addr + lock_stride * i;
		unsigned long flags = lock_fn(lock_addr);

		count += page_hash_count_bucket_result(hash_head);
		unlock_fn(lock_addr, flags);
	}

	return count;
}

int page_hash_count_pages_body_result(unsigned long hash_heads_addr,
		unsigned long locks_addr, int bucket_count,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_count_all_fn_t count_all_fn)
{
	if (!count_all_fn) {
		return -EINVAL;
	}

	return count_all_fn(hash_heads_addr, locks_addr, bucket_count,
			hash_head_stride, lock_stride, lock_fn, unlock_fn);
}

struct page *phys_to_page_lookup_orchestrate_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn)
{
	unsigned long hash_head_addr, lock_addr, flags;
	unsigned long hash;
	struct page *page;

	if (!hash_heads_addr || !locks_addr || hash_shift < 0 ||
			hash_shift >= 64 || !hash_head_stride || !lock_stride ||
			!lock_fn || !unlock_fn) {
		return NULL;
	}

	hash = (phys >> hash_shift) & hash_mask;
	hash_head_addr = hash_heads_addr + hash_head_stride * hash;
	lock_addr = locks_addr + lock_stride * hash;
	flags = lock_fn(lock_addr);
	page = page_hash_lookup_result((struct list_head *)hash_head_addr, phys);
	unlock_fn(lock_addr, flags);

	return page;
}

struct page *phys_to_page_insert_hash_orchestrate_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn)
{
	unsigned long hash_head_addr, lock_addr, flags;
	unsigned long hash;
	struct page *page;

	if (!hash_heads_addr || !locks_addr || hash_shift < 0 ||
			hash_shift >= 64 || !hash_head_stride || !lock_stride ||
			!lock_fn || !unlock_fn || !alloc_fn) {
		return NULL;
	}

	hash = (phys >> hash_shift) & hash_mask;
	hash_head_addr = hash_heads_addr + hash_head_stride * hash;
	lock_addr = locks_addr + lock_stride * hash;
	flags = lock_fn(lock_addr);
	page = page_hash_lookup_result((struct list_head *)hash_head_addr, phys);
	if (!page) {
		page = alloc_fn(page_size, alloc_flag);
		if (page) {
			page_insert_hash_init_result(page,
					(struct list_head *)hash_head_addr, phys);
		}
	}
	unlock_fn(lock_addr, flags);

	return page;
}

struct page *phys_to_page_lookup_body_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		phys_to_page_lookup_orchestrate_fn_t lookup_fn)
{
	if (!lookup_fn) {
		return NULL;
	}

	return lookup_fn(phys, hash_heads_addr, locks_addr, hash_shift,
			hash_mask, hash_head_stride, lock_stride, lock_fn,
			unlock_fn);
}

struct page *phys_to_page_insert_hash_body_result(uint64_t phys,
		unsigned long hash_heads_addr, unsigned long locks_addr,
		int hash_shift, uint64_t hash_mask,
		unsigned long hash_head_stride, unsigned long lock_stride,
		unsigned long page_size, int alloc_flag,
		page_hash_lock_fn_t lock_fn, page_hash_unlock_fn_t unlock_fn,
		page_hash_alloc_fn_t alloc_fn,
		phys_to_page_insert_orchestrate_fn_t insert_fn,
		phys_to_page_insert_log_fn_t log_fn)
{
	struct page *page;

	if (!insert_fn) {
		return NULL;
	}

	page = insert_fn(phys, hash_heads_addr, locks_addr, hash_shift,
			hash_mask, hash_head_stride, lock_stride, page_size,
			alloc_flag, lock_fn, unlock_fn, alloc_fn);
	if (!page && log_fn) {
		log_fn(phys);
	}

	return page;
}

int page_unmap_orchestrate_result(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn)
{
	unsigned long lock_addr, flags;
	unsigned long hash;
	int ret;

	if (!page || !locks_addr || hash_shift < 0 || hash_shift >= 64 ||
			!lock_stride || !lock_fn || !unlock_fn) {
		return 0;
	}

	hash = (page->phys >> hash_shift) & hash_mask;
	lock_addr = locks_addr + lock_stride * hash;
	flags = lock_fn(lock_addr);
	ret = page_unmap_locked_result(page);
	unlock_fn(lock_addr, flags);

	return ret;
}

int page_unmap_body_result(struct page *page,
		unsigned long locks_addr, int hash_shift, uint64_t hash_mask,
		unsigned long lock_stride, page_hash_lock_fn_t lock_fn,
		page_hash_unlock_fn_t unlock_fn,
		page_unmap_orchestrate_fn_t orchestrate_fn,
		page_unmap_log_fn_t log_fn)
{
	int ret;

	if (!page || !orchestrate_fn) {
		return 0;
	}

	if (log_fn) {
		log_fn(PAGE_UNMAP_LOG_ENTER, page, 0);
	}

	ret = orchestrate_fn(page, locks_addr, hash_shift, hash_mask,
			lock_stride, lock_fn, unlock_fn);
	if (!ret) {
		if (log_fn) {
			log_fn(PAGE_UNMAP_LOG_STILL_MAPPED, page, ret);
		}
		return 0;
	}

	if (log_fn) {
		log_fn(PAGE_UNMAP_LOG_UNMAPPED, page, ret);
	}

	return 1;
}
#endif /* MCKERNEL_RUST_PAGE_HELPERS */

/*
 * Allocate page and add to hash if it doesn't exist yet.
 * NOTE: page->count is zero for new pages and the caller
 * is responsible to increase it.
 */
static void phys_to_page_insert_hash_log_bridge(uint64_t phys)
{
	(void)phys;
	kprintf("%s: error allocating page\n", "phys_to_page_insert_hash");
}

struct page *phys_to_page_insert_hash(uint64_t phys)
{
	return phys_to_page_insert_hash_body_result(phys,
			(unsigned long)page_hash, (unsigned long)page_hash_locks,
			PAGE_SHIFT, PHYS_PAGE_HASH_MASK, sizeof(page_hash[0]),
			sizeof(page_hash_locks[0]), sizeof(struct page),
			IHK_MC_AP_CRITICAL, page_hash_lock_bridge,
			page_hash_unlock_bridge, page_hash_alloc_bridge,
			phys_to_page_insert_hash_orchestrate_result,
			phys_to_page_insert_hash_log_bridge);
}

static void page_unmap_log_bridge(int event, struct page *page, int ret)
{
	switch (event) {
	case PAGE_UNMAP_LOG_ENTER:
		dkprintf("page_unmap(%p %x %d)\n",
				page, page->mode, page->count);
		break;
	case PAGE_UNMAP_LOG_STILL_MAPPED:
		/* other mapping exist */
		dkprintf("page_unmap(%p %x %d): 0\n",
				page, page->mode, page->count);
		break;
	case PAGE_UNMAP_LOG_UNMAPPED:
		dkprintf("page_unmap(%p %x %d): %d\n",
				page, page->mode, page->count, ret);
		break;
	default:
		break;
	}
}

int page_unmap(struct page *page)
{
	return page_unmap_body_result(page,
			(unsigned long)page_hash_locks, PAGE_SHIFT,
			PHYS_PAGE_HASH_MASK, sizeof(page_hash_locks[0]),
			page_hash_lock_bridge, page_hash_unlock_bridge,
			page_unmap_orchestrate_result, page_unmap_log_bridge);
}

void register_kmalloc(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_register_kmalloc_result(&allocator, memdebug != NULL,
			__kmalloc, __kfree, ___kmalloc, ___kfree);
#else
	if(memdebug){
		allocator.alloc = __kmalloc;
		allocator.free = __kfree;
	}
	else{
		allocator.alloc = ___kmalloc;
		allocator.free = ___kfree;
	}
#endif
}

static struct ihk_page_allocator_desc *vmap_allocator;

#ifdef MCKERNEL_RUST_MEM_HELPERS
void *mem_vmap_allocator_bridge(void)
{
	return vmap_allocator;
}

static void *mem_vmap_init_bridge(unsigned long start, unsigned long size,
		unsigned long unit)
{
	return ihk_pagealloc_init(start, size, unit);
}

static int mem_pt_prepare_map_bridge(page_table_t pt, void *virt,
		unsigned long size, enum ihk_mc_pt_prepare_flag flag)
{
	return ihk_mc_pt_prepare_map(pt, virt, size, flag);
}

unsigned long mem_vmap_alloc_bridge(void *desc, int npages,
		int p2align)
{
	return ihk_pagealloc_alloc(desc, npages, p2align);
}

void mem_vmap_free_bridge(void *desc, unsigned long address,
		int npages)
{
	ihk_pagealloc_free(desc, address, npages);
}

int mem_pt_set_page_bridge(page_table_t pt, void *virt,
		unsigned long phys, enum ihk_mc_pt_attribute attr)
{
	return ihk_mc_pt_set_page(pt, virt, phys, attr);
}

int mem_pt_clear_page_bridge(page_table_t pt, void *virt)
{
	return ihk_mc_pt_clear_page(pt, virt);
}

void mem_flush_tlb_single_bridge(unsigned long addr)
{
	flush_tlb_single(addr);
}

void mem_barrier_bridge(void)
{
	barrier();
}
#endif

static void virtual_allocator_init(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_virtual_allocator_init_body_result((void **)&vmap_allocator,
			MAP_VMAP_START, MAP_VMAP_SIZE, PAGE_SIZE,
			IHK_MC_PT_FIRST_LEVEL, mem_vmap_init_bridge,
			mem_pt_prepare_map_bridge);
#else
	vmap_allocator = ihk_pagealloc_init(MAP_VMAP_START,
	                                    MAP_VMAP_SIZE, PAGE_SIZE);
	/* Make sure that kernel first-level page table copying works */
	ihk_mc_pt_prepare_map(NULL, (void *)MAP_VMAP_START, MAP_VMAP_SIZE,
	                      IHK_MC_PT_FIRST_LEVEL);
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void *ihk_mc_map_virtual(unsigned long phys, int npages,
		enum ihk_mc_pt_attribute attr);
#else
void *ihk_mc_map_virtual(unsigned long phys, int npages,
                         enum ihk_mc_pt_attribute attr)
{
	void *va;
	unsigned long i, offset;

	offset = (phys & (PAGE_SIZE - 1));
	phys = phys & PAGE_MASK;

	va = (void *)ihk_pagealloc_alloc(vmap_allocator, npages, PAGE_P2ALIGN);
	if (!va) {
		return NULL;
	}
	for (i = 0; i < npages; i++) {
		if (ihk_mc_pt_set_page(NULL, (char *)va + (i << PAGE_SHIFT),
				       phys + (i << PAGE_SHIFT), attr) != 0) {
			int j;

			for (j = 0; j < i; j++) {
				ihk_mc_pt_clear_page(NULL, (char *)va +
						     (j << PAGE_SHIFT));
			}
			ihk_pagealloc_free(vmap_allocator, (unsigned long)va,
					   npages);
			return NULL;
		}

		flush_tlb_single((unsigned long)(va + (i << PAGE_SHIFT)));
	}
	barrier();	/* Temporary fix for Thunder-X */
	return (char *)va + offset;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void ihk_mc_unmap_virtual(void *va, int npages);
#else
void ihk_mc_unmap_virtual(void *va, int npages)
{
	unsigned long i;

	va = (void *)((unsigned long)va & PAGE_MASK);
	for (i = 0; i < npages; i++) {
		ihk_mc_pt_clear_page(NULL, (char *)va + (i << PAGE_SHIFT));
		flush_tlb_single((unsigned long)(va + (i << PAGE_SHIFT)));
	}

	ihk_pagealloc_free(vmap_allocator, (unsigned long)va, npages);
}
#endif

#ifdef ATTACHED_MIC
/* moved from ihk_knc/manycore/mic/setup.c */
/*static*/ void *sbox_base = (void *)SBOX_BASE;
void sbox_write(int offset, unsigned int value)
{
	*(volatile unsigned int *)(sbox_base + offset) = value;
}
unsigned int sbox_read(int offset)
{
	return *(volatile unsigned int *)(sbox_base + offset);
}

/* insert entry into map which maps mic physical address to host physical address */

unsigned int free_bitmap_micpa = ((~((1ULL<<(NUM_SMPT_ENTRIES_IN_USE - NUM_SMPT_ENTRIES_MICPA))-1))&((1ULL << NUM_SMPT_ENTRIES_IN_USE) - 1));

void ihk_mc_map_micpa(unsigned long host_pa, unsigned long* mic_pa) {
    int i;
    for(i = NUM_SMPT_ENTRIES_IN_USE - 1; i >= NUM_SMPT_ENTRIES_IN_USE - NUM_SMPT_ENTRIES_MICPA; i--) {
        if((free_bitmap_micpa >> i) & 1) {
            free_bitmap_micpa &= ~(1ULL << i);
            *mic_pa = MIC_SYSTEM_BASE + MIC_SYSTEM_PAGE_SIZE * i;
            break;
        }
    }
    kprintf("ihk_mc_map_micpa,1,i=%d,host_pa=%lx,mic_pa=%llx\n", i, host_pa, *mic_pa);
    if(i == NUM_SMPT_ENTRIES_IN_USE - NUM_SMPT_ENTRIES_MICPA - 1) {
        *mic_pa = 0;
        return; 
    }
    sbox_write(SBOX_SMPT00 + ((*mic_pa - MIC_SYSTEM_BASE) >> MIC_SYSTEM_PAGE_SHIFT) * 4, BUILD_SMPT(SNOOP_ON, host_pa >> MIC_SYSTEM_PAGE_SHIFT));
    *mic_pa += (host_pa & (MIC_SYSTEM_PAGE_SIZE-1));
}

int ihk_mc_free_micpa(unsigned long mic_pa) {
    int smpt_ndx = ((mic_pa - MIC_SYSTEM_BASE) >> MIC_SYSTEM_PAGE_SHIFT);
    if(smpt_ndx >= NUM_SMPT_ENTRIES_IN_USE || 
       smpt_ndx <  NUM_SMPT_ENTRIES_IN_USE - NUM_SMPT_ENTRIES_MICPA) {
        dkprintf("ihk_mc_free_micpa,mic_pa=%llx,out of range\n", mic_pa); 
        return -1;
    }
    free_bitmap_micpa |= (1ULL << smpt_ndx);
    kprintf("ihk_mc_free_micpa,index=%d,freed\n", smpt_ndx);
    return 0;
}

void ihk_mc_clean_micpa(void){
	free_bitmap_micpa = ((~((1ULL<<(NUM_SMPT_ENTRIES_IN_USE - NUM_SMPT_ENTRIES_MICPA))-1))&((1ULL << NUM_SMPT_ENTRIES_IN_USE) - 1));
	kprintf("ihk_mc_clean_micpa\n");
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
static void mem_rusage_init_panic_bridge(void)
{
	panic("rusage_init: PANIC: ihk_mc_get_cpu_info returned NULL");
}

static void mem_rusage_init_log_bridge(unsigned long total_memory)
{
	dkprintf("%s: rusage.total_memory=%ld\n", "rusage_init", total_memory);
}
#endif

static void rusage_init()
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_rusage_init_body_result(&rusage, sizeof(struct rusage_global),
			ihk_mc_get_cpu_info, ihk_mc_get_nr_numa_nodes,
			ihk_mc_get_ns_per_tsc, virt_to_phys, ihk_set_rusage,
			mem_rusage_init_panic_bridge,
			mem_rusage_init_log_bridge);
#else
	unsigned long phys;
	const struct ihk_mc_cpu_info *cpu_info = ihk_mc_get_cpu_info();

	if (!cpu_info) {
		panic("rusage_init: PANIC: ihk_mc_get_cpu_info returned NULL");
	}

	memset(&rusage, 0, sizeof(rusage));
	rusage.num_processors = cpu_info->ncpus;
	rusage.num_numa_nodes = ihk_mc_get_nr_numa_nodes();
	rusage.ns_per_tsc = ihk_mc_get_ns_per_tsc();
	phys = virt_to_phys(&rusage);
	ihk_set_rusage(phys, sizeof(struct rusage_global));
	dkprintf("%s: rusage.total_memory=%ld\n", __FUNCTION__, rusage.total_memory);
#endif
}

extern void monitor_init(void);

#ifdef MCKERNEL_RUST_MEM_HELPERS
struct ihk_mc_pa_ops *mem_init_allocator_bridge(void)
{
	return &allocator;
}

unsigned long mem_init_page_fault_handler_bridge(void)
{
	return (unsigned long)page_fault_handler;
}

unsigned long mem_init_query_free_handler_bridge(void)
{
	return (unsigned long)&query_free_mem_handler;
}

int *mem_init_anon_on_demand_bridge(void)
{
	return &anon_on_demand;
}

int *mem_init_xpmem_remote_bridge(void)
{
	return &xpmem_page_in_remote_on_attach;
}

int *mem_init_hugetlbfs_on_demand_bridge(void)
{
#ifdef ENABLE_FUGAKU_HACKS
	return &hugetlbfs_on_demand;
#else
	return NULL;
#endif
}

void mem_monitor_init_bridge(void)
{
	monitor_init();
}

void mem_rusage_init_bridge(void)
{
	rusage_init();
}

void mem_numa_init_bridge(void)
{
	numa_init();
}

void mem_page_init_bridge(void)
{
	page_init();
}

void mem_virtual_allocator_init_bridge(void)
{
	virtual_allocator_init();
}

char *mem_find_command_line_bridge(char *name)
{
	return find_command_line(name);
}

void mem_numa_distances_init_bridge(void)
{
	numa_distances_init();
}

void mem_set_page_fault_handler_bridge(unsigned long handler)
{
	ihk_mc_set_page_fault_handler(
			(void (*)(void *, uint64_t, void *))handler);
}

int mem_get_vector_bridge(int type)
{
	return ihk_mc_get_vector((enum ihk_mc_gv_type)type);
}

int mem_register_interrupt_handler_bridge(int vector,
		unsigned long handler)
{
	return ihk_mc_register_interrupt_handler(vector,
			(struct ihk_mc_interrupt_handler *)handler);
}

void mem_init_log_bridge(int event)
{
	switch (event) {
	case MEM_INIT_LOG_ANON_ON_DEMAND:
		kprintf("Demand paging on ANONYMOUS mappings enabled.\n");
		break;
	case MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE:
		kprintf("Demand paging on XPMEM remote mappings enabled.\n");
		break;
	case MEM_INIT_LOG_HUGETLBFS_ON_DEMAND:
		kprintf("Demand paging on hugetlbfs mappings enabled.\n");
		break;
	default:
		break;
	}
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
void mem_init(void);
#else
void mem_init(void)
{
	monitor_init();

	/* It must precedes numa_init() because rusage.total_memory is initialized in numa_init() */
	rusage_init();

	/* Initialize NUMA information and memory allocator bitmaps */
	numa_init();

	/* Notify the ihk to use my page allocator */
	ihk_mc_set_page_allocator(&allocator);

	/* And prepare some exception handlers */
	ihk_mc_set_page_fault_handler(page_fault_handler);

	/* Register query free mem handler */
	ihk_mc_register_interrupt_handler(ihk_mc_get_vector(IHK_GV_QUERY_FREE_MEM),
			&query_free_mem_handler);

	/* Init page frame hash */
	page_init();

	/* Prepare the kernel virtual map space */
	virtual_allocator_init();

	if (find_command_line("anon_on_demand")) {
		kprintf("Demand paging on ANONYMOUS mappings enabled.\n");
		anon_on_demand = 1;
	}

	if (find_command_line("xpmem_page_in_remote_on_attach")) {
		kprintf("Demand paging on XPMEM remote mappings enabled.\n");
		xpmem_page_in_remote_on_attach = 1;
	}
	
#ifdef ENABLE_FUGAKU_HACKS
	if (find_command_line("hugetlbfs_on_demand")) {
		kprintf("Demand paging on hugetlbfs mappings enabled.\n");
		hugetlbfs_on_demand = 1;
	}
#endif

	/* Init distance vectors */
	numa_distances_init();
}
#endif

#define KMALLOC_TRACK_HASH_SHIFT	(8)
#define KMALLOC_TRACK_HASH_SIZE     (1 << KMALLOC_TRACK_HASH_SHIFT)
#define KMALLOC_TRACK_HASH_MASK     (KMALLOC_TRACK_HASH_SIZE - 1)

struct list_head kmalloc_track_hash[KMALLOC_TRACK_HASH_SIZE];
ihk_spinlock_t kmalloc_track_hash_locks[KMALLOC_TRACK_HASH_SIZE];

struct list_head kmalloc_addr_hash[KMALLOC_TRACK_HASH_SIZE];
ihk_spinlock_t kmalloc_addr_hash_locks[KMALLOC_TRACK_HASH_SIZE];

int kmalloc_track_initialized = 0;
int kmalloc_runcount = 0;

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

#ifdef MCKERNEL_RUST_MEM_HELPERS
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

void *mem_kmalloc_track_base_alloc_bridge(int size, ihk_mc_ap_flag flag)
{
	return ___kmalloc(size, flag);
}

void mem_kmalloc_track_base_free_bridge(void *ptr)
{
	___kfree(ptr);
}

unsigned long mem_kmalloc_track_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

void mem_kmalloc_track_unlock_bridge(unsigned long lock_addr,
		unsigned long irqflags)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqflags);
}

void mem_kmalloc_track_spin_init_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock_addr);
}

void mem_kmalloc_track_log_bridge(int event, void *ptr, char *file,
		int line, int size)
{
	switch (event) {
	case KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating tracking entry\n", "_kmalloc");
		break;
	case KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating file string\n", "_kmalloc");
		break;
	case KMALLOC_TRACK_LOG_ENTRY_ADDED:
		dkprintf("%s entry %s:%d size: %d added\n", "_kmalloc",
				file, line, size);
		break;
	case KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating addr entry\n", "_kmalloc");
		break;
	case KMALLOC_TRACK_LOG_ADDR_ADDED:
		dkprintf("%s addr_entry %p added\n", "_kmalloc", ptr);
		break;
	case KMALLOC_TRACK_LOG_ADDR_REMOVED:
		dkprintf("%s addr_entry %p removed\n", "_kfree", ptr);
		break;
	case KMALLOC_TRACK_LOG_ENTRY_REMOVED:
		dkprintf("%s entry %s:%d size: %d removed\n", "_kfree",
				file, line, size);
		break;
	default:
		break;
	}
}

void mem_kmalloc_invalid_free_bridge(void *ptr, char *file, int line)
{
	kprintf("%s: ERROR: kfree()ing invalid pointer at %s:%d\n",
			"_kfree", file, line);
	panic("panic");
}

void mem_kmalloc_leak_log_bridge(int event, void *ptr, char *file,
		int line, int size, int count, int runcount)
{
	switch (event) {
	case MEM_TRACK_LEAK_DETAIL:
		(void)count;
		dkprintf("%s memory leak: %p @ %s:%d size: %d runcount: %d\n",
				"kmalloc_memcheck", ptr, file, line, size,
				runcount);
		break;
	case MEM_TRACK_LEAK_SUMMARY:
		(void)ptr;
		kprintf("%s memory leak: %s:%d size: %d cnt: %d, runcount: %d\n",
				"kmalloc_memcheck", file, line, size, count,
				runcount);
		break;
	default:
		break;
	}
}

static struct cpu_local_var *mem_get_this_cpu_local_var_bridge(void)
{
	return get_this_cpu_local_var();
}
#endif

void kmalloc_init(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_kmalloc_init_body_result(&memdebug, &kmalloc_track_initialized,
			kmalloc_track_hash, kmalloc_track_hash_locks,
			kmalloc_addr_hash, kmalloc_addr_hash_locks,
			KMALLOC_TRACK_HASH_SIZE,
			mem_get_this_cpu_local_var_bridge, register_kmalloc,
			find_command_line, mem_kmalloc_track_spin_init_bridge);
#else
	struct cpu_local_var *v = get_this_cpu_local_var();

	register_kmalloc();

	INIT_LIST_HEAD(&v->free_list);
	INIT_LIST_HEAD(&v->remote_free_list);
	ihk_mc_spinlock_init(&v->remote_free_list_lock);

	v->kmalloc_initialized = 1;

	if (!kmalloc_track_initialized) {
		int i;

		memdebug = find_command_line("memdebug");

		kmalloc_track_initialized = 1;
		for (i = 0; i < KMALLOC_TRACK_HASH_SIZE; ++i) {
			ihk_mc_spinlock_init(&kmalloc_track_hash_locks[i]);
			INIT_LIST_HEAD(&kmalloc_track_hash[i]);
			ihk_mc_spinlock_init(&kmalloc_addr_hash_locks[i]);
			INIT_LIST_HEAD(&kmalloc_addr_hash[i]);
		}
	}
#endif
}

/* NOTE: Hash lock must be held */
#ifdef MCKERNEL_RUST_MEM_HELPERS
extern struct kmalloc_track_entry *__kmalloc_track_find_entry(
		int size, char *file, int line);
#else
struct kmalloc_track_entry *__kmalloc_track_find_entry(
		int size, char *file, int line)
{
	struct kmalloc_track_entry *entry_iter, *entry = NULL;
	int hash = (strlen(file) + line + size) & KMALLOC_TRACK_HASH_MASK;

	for (entry_iter = ((typeof(*entry_iter) *)((char *)((&kmalloc_track_hash[hash])->next) - offsetof(typeof(*entry_iter), hash))); &entry_iter->hash != (&kmalloc_track_hash[hash]); entry_iter = ((typeof(*entry_iter) *)((char *)(entry_iter->hash.next) - offsetof(typeof(*entry_iter), hash)))) {
		if (!strcmp(entry_iter->file, file) &&
				entry_iter->size == size &&
				entry_iter->line == line) {
			entry = entry_iter;
			break;
		}
	}

	if (entry) {
		dkprintf("%s found entry %s:%d size: %d\n", __FUNCTION__,
				file, line, size);
	}
	else {
		dkprintf("%s couldn't find entry %s:%d size: %d\n", __FUNCTION__,
				file, line, size);
	}

	return entry;
}
#endif

/* Top level routines called from macro */
#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void *_kmalloc(int size, ihk_mc_ap_flag flag, char *file, int line);
#else
void *_kmalloc(int size, ihk_mc_ap_flag flag, char *file, int line)
{
	unsigned long irqflags;
	struct kmalloc_track_entry *entry;
	struct kmalloc_track_addr_entry *addr_entry;
	int hash, addr_hash;
	void *r = ___kmalloc(size, flag);

	if (!memdebug)
		return r;

	if (!r)
		return r;

	hash = (strlen(file) + line + size) & KMALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&kmalloc_track_hash_locks[hash]);

	entry = __kmalloc_track_find_entry(size, file, line);

	if (!entry) {
		entry = ___kmalloc(sizeof(*entry), IHK_MC_AP_NOWAIT);
		if (!entry) {
			ihk_mc_spinlock_unlock(&kmalloc_track_hash_locks[hash], irqflags);
			kprintf("%s: ERROR: allocating tracking entry\n");
			goto out;
		}

		entry->line = line;
		entry->size = size;
		ihk_atomic_set(&entry->alloc_count, 1);
		ihk_mc_spinlock_init(&entry->addr_list_lock);
		INIT_LIST_HEAD(&entry->addr_list);

		entry->file = ___kmalloc(strlen(file) + 1, IHK_MC_AP_NOWAIT);
		if (!entry->file) {
			kprintf("%s: ERROR: allocating file string\n");
			___kfree(entry);
			ihk_mc_spinlock_unlock(&kmalloc_track_hash_locks[hash], irqflags);
			goto out;
		}

		strcpy(entry->file, file);
		entry->file[strlen(file)] = 0;
		INIT_LIST_HEAD(&entry->hash);
		list_add(&entry->hash, &kmalloc_track_hash[hash]);
		dkprintf("%s entry %s:%d size: %d added\n", __FUNCTION__,
			file, line, size);
	}
	else {
		ihk_atomic_inc(&entry->alloc_count);
	}
	ihk_mc_spinlock_unlock(&kmalloc_track_hash_locks[hash], irqflags);

	/* Add new addr entry for this allocation entry */
	addr_entry = ___kmalloc(sizeof(*addr_entry), IHK_MC_AP_NOWAIT);
	if (!addr_entry) {
		kprintf("%s: ERROR: allocating addr entry\n");
		goto out;
	}

	addr_entry->addr = r;
	addr_entry->runcount = kmalloc_runcount;
	addr_entry->entry = entry;

	irqflags = ihk_mc_spinlock_lock(&entry->addr_list_lock);
	list_add(&addr_entry->list, &entry->addr_list);
	ihk_mc_spinlock_unlock(&entry->addr_list_lock, irqflags);

	/* Add addr entry to address hash */
	addr_hash = ((unsigned long)r >> 5) & KMALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&kmalloc_addr_hash_locks[addr_hash]);
	list_add(&addr_entry->hash, &kmalloc_addr_hash[addr_hash]);
	ihk_mc_spinlock_unlock(&kmalloc_addr_hash_locks[addr_hash], irqflags);

	dkprintf("%s addr_entry %p added\n", __FUNCTION__, r);

out:
	return r;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void _kfree(void *ptr, char *file, int line);
#else
void _kfree(void *ptr, char *file, int line)
{
	unsigned long irqflags;
	struct kmalloc_track_entry *entry;
	struct kmalloc_track_addr_entry *addr_entry_iter, *addr_entry = NULL;
	int hash;

	if (!ptr) {
		return;
	}

	if (!memdebug) {
		goto out;
	}

	hash = ((unsigned long)ptr >> 5) & KMALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&kmalloc_addr_hash_locks[hash]);
	for (addr_entry_iter = ((typeof(*addr_entry_iter) *)((char *)((&kmalloc_addr_hash[hash])->next) - offsetof(typeof(*addr_entry_iter), hash))); &addr_entry_iter->hash != (&kmalloc_addr_hash[hash]); addr_entry_iter = ((typeof(*addr_entry_iter) *)((char *)(addr_entry_iter->hash.next) - offsetof(typeof(*addr_entry_iter), hash)))) {
		if (addr_entry_iter->addr == ptr) {
			addr_entry = addr_entry_iter;
			break;
		}
	}

	if (addr_entry) {
		list_del(&addr_entry->hash);
	}
	ihk_mc_spinlock_unlock(&kmalloc_addr_hash_locks[hash], irqflags);

	if (!addr_entry) {
		kprintf("%s: ERROR: kfree()ing invalid pointer at %s:%d\n",
			__FUNCTION__, file, line);
		panic("panic");
	}

	entry = addr_entry->entry;

	irqflags = ihk_mc_spinlock_lock(&entry->addr_list_lock);
	list_del(&addr_entry->list);
	ihk_mc_spinlock_unlock(&entry->addr_list_lock, irqflags);

	dkprintf("%s addr_entry %p removed\n", __FUNCTION__, addr_entry->addr);
	___kfree(addr_entry);

	/* Do we need to remove tracking entry as well? */
	hash = (strlen(entry->file) + entry->line + entry->size) &
		KMALLOC_TRACK_HASH_MASK;
	irqflags = ihk_mc_spinlock_lock(&kmalloc_track_hash_locks[hash]);

	if (!ihk_atomic_dec_and_test(&entry->alloc_count)) {
		ihk_mc_spinlock_unlock(&kmalloc_track_hash_locks[hash], irqflags);
		goto out;
	}

	list_del(&entry->hash);
	ihk_mc_spinlock_unlock(&kmalloc_track_hash_locks[hash], irqflags);

	dkprintf("%s entry %s:%d size: %d removed\n", __FUNCTION__,
			entry->file, entry->line, entry->size);
	___kfree(entry->file);
	___kfree(entry);

out:
	___kfree(ptr);
}
#endif

#ifndef MCKERNEL_RUST_MEM_HELPERS
void *kmalloc_tracked(int size, ihk_mc_ap_flag flag, char *file, int line)
{
	void *r = _kmalloc(size, flag, file, line);

	if (r == NULL) {
		kprintf("kmalloc: out of memory %s:%d no_preempt=%d\n",
				file, line,
				ihk_atomic_read(&get_this_cpu_local_var()->no_preempt));
	}

	return r;
}

void kfree_tracked(void *ptr, char *file, int line)
{
	_kfree(ptr, file, line);
}

void *kmalloc(int size, ihk_mc_ap_flag flag)
{
	return kmalloc_tracked(size, flag, "kernel/include/kmalloc.h", 0);
}

void kfree(void *ptr)
{
	kfree_tracked(ptr, "kernel/include/kmalloc.h", 0);
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern void kmalloc_memcheck(void);
#else
void kmalloc_memcheck(void)
{
	int i;
	unsigned long irqflags;
	struct kmalloc_track_entry *entry = NULL;

	for (i = 0; i < KMALLOC_TRACK_HASH_SIZE; ++i) {
		irqflags = ihk_mc_spinlock_lock(&kmalloc_track_hash_locks[i]);
		for (entry = ((typeof(*entry) *)((char *)((&kmalloc_track_hash[i])->next) - offsetof(typeof(*entry), hash))); &entry->hash != (&kmalloc_track_hash[i]); entry = ((typeof(*entry) *)((char *)(entry->hash.next) - offsetof(typeof(*entry), hash)))) {
			struct kmalloc_track_addr_entry *addr_entry = NULL;
			int cnt = 0;

			ihk_mc_spinlock_lock_noirq(&entry->addr_list_lock);
			for (addr_entry = ((typeof(*addr_entry) *)((char *)((&entry->addr_list)->next) - offsetof(typeof(*addr_entry), list))); &addr_entry->list != (&entry->addr_list); addr_entry = ((typeof(*addr_entry) *)((char *)(addr_entry->list.next) - offsetof(typeof(*addr_entry), list)))) {

			dkprintf("%s memory leak: %p @ %s:%d size: %d runcount: %d\n",
				__FUNCTION__,
				addr_entry->addr,
				entry->file,
				entry->line,
				entry->size,
				addr_entry->runcount);

				if (kmalloc_runcount != addr_entry->runcount)
					continue;

				cnt++;
			}
			ihk_mc_spinlock_unlock_noirq(&entry->addr_list_lock);

			if (!cnt)
				continue;

			kprintf("%s memory leak: %s:%d size: %d cnt: %d, runcount: %d\n",
				__FUNCTION__,
				entry->file,
				entry->line,
				entry->size,
				cnt,
				kmalloc_runcount);
		}
		ihk_mc_spinlock_unlock(&kmalloc_track_hash_locks[i], irqflags);
	}

	++kmalloc_runcount;
}
#endif

/* Redirection routines registered in alloc structure */
void *__kmalloc(int size, ihk_mc_ap_flag flag)
{
	return kmalloc_tracked(size, flag, __FILE__, __LINE__);
}

void __kfree(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}


#ifdef MCKERNEL_RUST_MEM_HELPERS
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
#else
static void ___kmalloc_insert_chunk(struct list_head *free_list,
		struct kmalloc_header *chunk)
{
	struct kmalloc_header *chunk_iter, *next_chunk = NULL;

	/* Find out where to insert */
	for (chunk_iter = ((typeof(*chunk_iter) *)((char *)((free_list)->next) - offsetof(typeof(*chunk_iter), list))); &chunk_iter->list != (free_list); chunk_iter = ((typeof(*chunk_iter) *)((char *)(chunk_iter->list.next) - offsetof(typeof(*chunk_iter), list)))) {
		if ((void *)chunk < (void *)chunk_iter) {
			next_chunk = chunk_iter;
			break;
		}
	}

	/* Add in front of next */
	if (next_chunk) {
		list_add_tail(&chunk->list, &next_chunk->list);
	}
	/* Add tail */
	else {
		list_add_tail(&chunk->list, free_list);
	}

	return;
}

static void ___kmalloc_init_chunk(struct kmalloc_header *h, int size)
{
	h->size = size;
	h->front_magic = 0x5c5c5c5c;
	h->end_magic = 0x6d6d6d6d;
	h->cpu_id = ihk_mc_get_processor_id();
}

static void ___kmalloc_consolidate_list(struct list_head *list)
{
	struct kmalloc_header *chunk_iter, *chunk, *next_chunk;

reiterate:
	chunk_iter = NULL;
	chunk = NULL;

	for (next_chunk = ((typeof(*next_chunk) *)((char *)((list)->next) - offsetof(typeof(*next_chunk), list))); &next_chunk->list != (list); next_chunk = ((typeof(*next_chunk) *)((char *)(next_chunk->list.next) - offsetof(typeof(*next_chunk), list)))) {

		if (chunk_iter && (((void *)chunk_iter + sizeof(struct kmalloc_header)
						+ chunk_iter->size) == (void *)next_chunk)) {
			chunk = chunk_iter;
			break;
		}

		chunk_iter = next_chunk;
	}

	if (!chunk) {
		return;
	}

	chunk->size += (next_chunk->size + sizeof(struct kmalloc_header));
	list_del(&next_chunk->list);
	goto reiterate;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
static unsigned long mem_kmalloc_irq_save_bridge(void)
{
	return cpu_disable_interrupt_save();
}

static void mem_kmalloc_irq_restore_bridge(unsigned long flags)
{
	cpu_restore_interrupt(flags);
}

static void *mem_kmalloc_alloc_pages_bridge(int npages, ihk_mc_ap_flag flag,
		int is_user)
{
	return ___ihk_mc_alloc_pages(npages, flag, is_user);
}

static void *mem_kmalloc_get_cpu_local_var_bridge(int cpu)
{
	return get_cpu_local_var(cpu);
}

static unsigned long mem_kmalloc_remote_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void mem_kmalloc_remote_unlock_bridge(unsigned long lock_addr,
		unsigned long flags)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, flags);
}

static void mem_kmalloc_corruption_bridge(void *ptr)
{
	kprintf("%s: memory corruption at address 0x%p\n", "___kfree", ptr);
	panic("panic");
}
#endif

#define KMALLOC_CACHE_LOG_NO_CACHE 1
#define KMALLOC_CACHE_LOG_ALLOC_FAILED 2
#define KMALLOC_CACHE_LOG_PREALLOC 3

#ifdef MCKERNEL_RUST_MEM_HELPERS
void *kmalloc_cache_alloc_bridge(size_t size, ihk_mc_ap_flag flag)
{
	return kmalloc_tracked(size, flag, __FILE__, __LINE__);
}

void kmalloc_cache_log(int event, void *ptr)
{
	switch (event) {
	case KMALLOC_CACHE_LOG_NO_CACHE:
		kprintf("%s: WARNING: no cache for 0x%lx\n",
				"kmalloc_cache_free", ptr);
		break;
	case KMALLOC_CACHE_LOG_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating cache element\n",
				"kmalloc_cache_prealloc");
		break;
	case KMALLOC_CACHE_LOG_PREALLOC:
		kprintf("%s: calling pre-alloc for 0x%lx...\n",
				"kmalloc_cache_alloc", ptr);
		break;
	default:
		break;
	}
}
#else
void kmalloc_cache_free(void *elem)
{
	struct kmalloc_cache_header *current = NULL;
	struct kmalloc_cache_header *new =
		(struct kmalloc_cache_header *)elem;
	struct kmalloc_header *header;
	register struct kmalloc_cache_header *cache;

	if (unlikely(!elem))
		return;

	/* Get cache pointer from kmalloc header */
	header = (struct kmalloc_header *)((void *)elem -
				sizeof(struct kmalloc_header));
	if (unlikely(!header->cache)) {
		kprintf("%s: WARNING: no cache for 0x%lx\n",
				__func__, elem);
		return;
	}

	cache = header->cache;

retry:
	current = cache->next;
	new->next = current;

	if (!__sync_bool_compare_and_swap(&cache->next, current, new)) {
		goto retry;
	}
}

void kmalloc_cache_prealloc(struct kmalloc_cache_header *cache,
		size_t size, int nr_elem)
{
	struct kmalloc_cache_header *elem;
	int i;

	if (unlikely(cache->next))
		return;

	for (i = 0; i < nr_elem; ++i) {
		struct kmalloc_header *header;

		elem = (struct kmalloc_cache_header *)
			kmalloc_tracked(size, IHK_MC_AP_NOWAIT,
					__FILE__, __LINE__);

		if (!elem) {
			kprintf("%s: ERROR: allocating cache element\n", __func__);
			continue;
		}

		/* Store cache pointer in kmalloc_header */
		header = (struct kmalloc_header *)((void *)elem -
				sizeof(struct kmalloc_header));
		header->cache = cache;

		kmalloc_cache_free(elem);
	}
}

void *kmalloc_cache_alloc(struct kmalloc_cache_header *cache, size_t size)
{
	register struct kmalloc_cache_header *first, *next;

retry:
	next = NULL;
	first = cache->next;

	if (first) {
		next = first->next;

		if (!__sync_bool_compare_and_swap(&cache->next,
					first, next)) {
			goto retry;
		}
	}
	else {
		kprintf("%s: calling pre-alloc for 0x%lx...\n", __func__, cache);

		kmalloc_cache_prealloc(cache, size, 384);
		goto retry;
	}

	return (void *)first;
}
#endif


void kmalloc_consolidate_free_list(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	kmalloc_consolidate_free_list_result(&get_this_cpu_local_var()->remote_free_list,
			&get_this_cpu_local_var()->free_list,
			&get_this_cpu_local_var()->remote_free_list_lock,
			mem_kmalloc_remote_lock_bridge,
			mem_kmalloc_remote_unlock_bridge);
#else
	struct kmalloc_header *chunk, *tmp;
	unsigned long irqflags =
		ihk_mc_spinlock_lock(&get_this_cpu_local_var()->remote_free_list_lock);

	/* Clean up remotely deallocated chunks */
	for (chunk = ((typeof(*chunk) *)((char *)((&get_this_cpu_local_var()->remote_free_list)->next) - offsetof(typeof(*chunk), list))), tmp = ((typeof(*chunk) *)((char *)(chunk->list.next) - offsetof(typeof(*chunk), list))); &chunk->list != (&get_this_cpu_local_var()->remote_free_list); chunk = tmp, tmp = ((typeof(*tmp) *)((char *)(tmp->list.next) - offsetof(typeof(*tmp), list)))) {

		list_del(&chunk->list);
		___kmalloc_insert_chunk(&get_this_cpu_local_var()->free_list, chunk);
	}

	/* Free list lock ensures IRQs are disabled */
	___kmalloc_consolidate_list(&get_this_cpu_local_var()->free_list);

	ihk_mc_spinlock_unlock(&get_this_cpu_local_var()->remote_free_list_lock, irqflags);
#endif
}

#define KMALLOC_MIN_SHIFT   (5)
#define KMALLOC_MIN_SIZE    (1 << KMALLOC_MIN_SHIFT)
#define KMALLOC_MIN_MASK    (KMALLOC_MIN_SIZE - 1)

/* Actual low-level allocation routines */
static void *___kmalloc(int size, ihk_mc_ap_flag flag)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return ___kmalloc_body_result(size, flag, &get_this_cpu_local_var()->free_list,
			mem_kmalloc_irq_save_bridge,
			mem_kmalloc_irq_restore_bridge,
			mem_kmalloc_alloc_pages_bridge);
#else
	struct kmalloc_header *chunk_iter;
	struct kmalloc_header *chunk = NULL;
	int npages;
	unsigned long kmalloc_irq_flags = cpu_disable_interrupt_save();

	/* KMALLOC_MIN_SIZE bytes aligned size. */
	if (size & KMALLOC_MIN_MASK) {
		size = ((size + KMALLOC_MIN_SIZE - 1) & ~(KMALLOC_MIN_MASK));
	}

	chunk = NULL;
	/* Find a chunk that is big enough */
	for (chunk_iter = ((typeof(*chunk_iter) *)((char *)((&get_this_cpu_local_var()->free_list)->next) - offsetof(typeof(*chunk_iter), list))); &chunk_iter->list != (&get_this_cpu_local_var()->free_list); chunk_iter = ((typeof(*chunk_iter) *)((char *)(chunk_iter->list.next) - offsetof(typeof(*chunk_iter), list)))) {
		if (chunk_iter->size >= size) {
			chunk = chunk_iter;
			break;
		}
	}

split_and_return:
	/* Did we find one? */
	if (chunk) {
		/* Do we need to split it? Only if there is enough space for
		 * another header and some actual content */
		if (chunk->size > (size + sizeof(struct kmalloc_header))) {
			struct kmalloc_header *leftover;

			leftover = (struct kmalloc_header *)
				((void *)chunk + sizeof(struct kmalloc_header) + size);
			___kmalloc_init_chunk(leftover,
				(chunk->size - size - sizeof(struct kmalloc_header)));
			list_add(&leftover->list, &chunk->list);
			chunk->size = size;
		}

		list_del(&chunk->list);
		cpu_restore_interrupt(kmalloc_irq_flags);
		return ((void *)chunk + sizeof(struct kmalloc_header));
	}


	/* Allocate new memory and add it to free list */
	npages = (size + sizeof(struct kmalloc_header) + (PAGE_SIZE - 1))
		>> PAGE_SHIFT;
	/* Use low-level page allocator to avoid tracking */
	chunk = ___ihk_mc_alloc_pages(npages, flag, IHK_MC_PG_KERNEL);

	if (!chunk) {
		cpu_restore_interrupt(kmalloc_irq_flags);
		return NULL;
	}

	___kmalloc_init_chunk(chunk,
			(npages * PAGE_SIZE - sizeof(struct kmalloc_header)));
	___kmalloc_insert_chunk(&get_this_cpu_local_var()->free_list, chunk);

	goto split_and_return;
#endif
}

static void ___kfree(void *ptr)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	___kfree_body_result(ptr, &get_this_cpu_local_var()->free_list,
			__builtin_offsetof(struct cpu_local_var,
					   remote_free_list_lock),
			__builtin_offsetof(struct cpu_local_var,
					   remote_free_list),
			mem_kmalloc_irq_save_bridge,
			mem_kmalloc_irq_restore_bridge,
			mem_kmalloc_get_cpu_local_var_bridge,
			mem_kmalloc_remote_lock_bridge,
			mem_kmalloc_remote_unlock_bridge,
			mem_kmalloc_corruption_bridge);
#else
	struct kmalloc_header *chunk;
	unsigned long kmalloc_irq_flags;

	if (!ptr)
		return;

	chunk = (struct kmalloc_header*)(ptr - sizeof(struct kmalloc_header));
	kmalloc_irq_flags = cpu_disable_interrupt_save();

	/* Sanity check */
	if (chunk->front_magic != 0x5c5c5c5c || chunk->end_magic != 0x6d6d6d6d) {
		kprintf("%s: memory corruption at address 0x%p\n", __FUNCTION__, ptr);
		panic("panic");
	}

	/* Does this chunk belong to this CPU? */
	if (chunk->cpu_id == ihk_mc_get_processor_id()) {

		___kmalloc_insert_chunk(&get_this_cpu_local_var()->free_list, chunk);
		___kmalloc_consolidate_list(&get_this_cpu_local_var()->free_list);
	}
	else {
		struct cpu_local_var *v = get_cpu_local_var(chunk->cpu_id);
		unsigned long irqflags;

		irqflags = ihk_mc_spinlock_lock(&v->remote_free_list_lock);
		list_add(&chunk->list, &v->remote_free_list);
		ihk_mc_spinlock_unlock(&v->remote_free_list_lock, irqflags);
	}

	cpu_restore_interrupt(kmalloc_irq_flags);
#endif
}


void ___kmalloc_print_free_list(struct list_head *list)
{
	struct kmalloc_header *chunk_iter;
	unsigned long irqflags = kprintf_lock();

	__kprintf("%s: [ \n", __FUNCTION__);
	for (chunk_iter = ((typeof(*chunk_iter) *)((char *)((&get_this_cpu_local_var()->free_list)->next) - offsetof(typeof(*chunk_iter), list))); &chunk_iter->list != (&get_this_cpu_local_var()->free_list); chunk_iter = ((typeof(*chunk_iter) *)((char *)(chunk_iter->list.next) - offsetof(typeof(*chunk_iter), list)))) {
		__kprintf("%s: 0x%lx:%d (VA PFN: %lu, off: %lu)\n", __FUNCTION__,
			(unsigned long)chunk_iter,
			chunk_iter->size,
			(unsigned long)chunk_iter >> PAGE_SHIFT,
			(unsigned long)chunk_iter % PAGE_SIZE);
	}
	__kprintf("%s: ] \n", __FUNCTION__);
	kprintf_unlock(irqflags);
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern int is_mckernel_memory(unsigned long start, unsigned long end);
#else
#ifdef IHK_RBTREE_ALLOCATOR
int is_mckernel_memory(unsigned long start, unsigned long end)
{
	int i;

	for (i = 0; i < ihk_mc_get_nr_memory_chunks(); ++i) {
		unsigned long chunk_start, chunk_end;
		int numa_id;

		ihk_mc_get_memory_chunk(i, &chunk_start, &chunk_end, &numa_id);
		if ((chunk_start <= start && start < chunk_end) &&
		    (chunk_start <= end && end <= chunk_end)) {
			return 1;
		}
	}
	return 0;
}
#else /* IHK_RBTREE_ALLOCATOR */
int is_mckernel_memory(unsigned long start, unsigned long end)
{
	int i;

	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); ++i) {
		struct ihk_page_allocator_desc *pa_allocator;
		unsigned long area_start = pa_allocator->start;
		unsigned long area_end = pa_allocator->end;

		for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[i].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[i].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {
			if ((area_start <= start && start < area_end) &&
			    (area_start <= end && end <= area_end)) {
				return 1;
			}
		}
	}
	return 0;
}
#endif /* IHK_RBTREE_ALLOCATOR */
#endif /* MCKERNEL_RUST_MEM_HELPERS */

#ifdef MCKERNEL_RUST_MEM_HELPERS
int mem_num_processors_bridge(void)
{
	return num_processors;
}

int mem_dump_level_bridge(void)
{
	return ihk_mc_get_dump_level();
}

struct ihk_dump_page_set *mem_get_dump_page_set_bridge(void)
{
	return ihk_mc_get_dump_page_set();
}

struct ihk_dump_page *mem_get_dump_page_bridge(void)
{
	return ihk_mc_get_dump_page();
}

struct list_head *mem_process_hash_lists_bridge(void)
{
	struct resource_set *rset = get_this_cpu_local_var()->resource_set;
	struct process_hash *phash = rset->process_hash;

	return phash ? phash->list : NULL;
}

void mem_dump_complete_log_bridge(void)
{
	dkprintf("%s: IHK_DUMP_PAGE_SET_COMPLETED\n",
			"ihk_mc_query_mem_areas");
}

void mem_dump_warn_bridge(int kind, unsigned long map_count,
		unsigned long map_index, unsigned long map_start,
		unsigned long map_end, unsigned long page_index)
{
	if (kind == 0) {
		kprintf("%s:free page is out of range(max:%d): %ld "
				"(map_start:0x%lx, map_end:0x%lx) k(0x%lx)\n",
				"ihk_mc_query_mem_free_page", (int)map_count,
				map_index, map_start, map_end, page_index);
	} else {
		kprintf("%s:user page is out of range(max:%d): %ld "
				"(map_start:0x%lx, map_end:0x%lx) j(0x%lx)\n",
				"ihk_mc_get_mem_user_page", (int)map_count,
				map_index, map_start, map_end, page_index);
	}
}

#ifdef IHK_RBTREE_ALLOCATOR
unsigned long mem_dump_free_pages_bridge(int node)
{
	return mem_dump_free_pages_public_result(memory_nodes, node,
			ihk_mc_get_nr_numa_nodes);
}

void *mem_dump_first_free_chunk_bridge(int node)
{
	return mem_dump_first_free_chunk_public_result(memory_nodes, node,
			ihk_mc_get_nr_numa_nodes);
}

void *mem_dump_next_free_chunk_bridge(void *chunk)
{
	return mem_dump_next_free_chunk_result(chunk);
}

unsigned long mem_dump_chunk_addr_bridge(void *chunk)
{
	return mem_dump_chunk_addr_result(chunk);
}

unsigned long mem_dump_chunk_size_bridge(void *chunk)
{
	return mem_dump_chunk_size_result(chunk);
}
#endif
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
void ihk_mc_query_mem_areas(void);
#else
void ihk_mc_query_mem_areas(void){
	int cpu_id;
	struct ihk_dump_page_set *dump_page_set;
	struct dump_pase_info dump_pase_info;

	/*
	 * Performed only on the last CPU to make sure
	 * all other cores are already stopped.
	 */
	cpu_id = ihk_mc_get_processor_id();

	if (num_processors - 1 != cpu_id)
		return;

	dump_page_set = ihk_mc_get_dump_page_set();
	
	if (DUMP_LEVEL_USER_UNUSED_EXCLUDE == ihk_mc_get_dump_level()) {
		if (dump_page_set->count) {

			dump_pase_info.dump_page_set = dump_page_set;
			dump_pase_info.dump_pages = ihk_mc_get_dump_page();

			/* Get user page information */
			ihk_mc_query_mem_user_page((void *)&dump_pase_info);
			/* Get unused page information */
			ihk_mc_query_mem_free_page((void *)&dump_pase_info);
		}
	}

	dump_page_set->completion_flag = IHK_DUMP_PAGE_SET_COMPLETED;
	dkprintf("%s: IHK_DUMP_PAGE_SET_COMPLETED\n", __func__);

	return;
}
#endif

void ihk_mc_clear_dump_page_completion(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_clear_dump_page_completion_result(ihk_mc_get_dump_page_set);
#else
	struct ihk_dump_page_set *dump_page_set;

	dump_page_set = ihk_mc_get_dump_page_set();
	dump_page_set->completion_flag = IHK_DUMP_PAGE_SET_INCOMPLETE;
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
void ihk_mc_query_mem_user_page(void *dump_pase_info);
#else
void ihk_mc_query_mem_user_page(void *dump_pase_info) {
	struct resource_set *rset = get_this_cpu_local_var()->resource_set;
	struct process_hash *phash = rset->process_hash;
	struct process *p; 
	struct process_vm *vm;
	int i;

	for (i=0; i<HASH_SIZE; i++) {

		for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
			vm = p->vm;
			if (vm) {
				if(vm->address_space->page_table) {
					visit_pte_range_safe(vm->address_space->page_table, 0,
					(void *)USER_END, 0, 0,
					&ihk_mc_get_mem_user_page, (void *)dump_pase_info);
				}
			}
		}
	}

	return;
}
#endif

#ifdef MCKERNEL_RUST_MEM_HELPERS
void ihk_mc_query_mem_free_page(void *dump_pase_info);
#else
void ihk_mc_query_mem_free_page(void *dump_pase_info) {
#ifdef IHK_RBTREE_ALLOCATOR
	struct free_chunk *chunk;
	struct rb_node *node;
	struct rb_root *free_chunks;
	unsigned long phy_start, map_start, map_end, free_pages, free_page_cnt, map_size, set_size, k;
	int i, j;
	struct ihk_dump_page_set *dump_page_set;
	struct ihk_dump_page *dump_page;
	struct dump_pase_info *dump_pase_in;
	unsigned long chunk_addr, chunk_size;

	dump_pase_in = (struct dump_pase_info *)dump_pase_info;
	dump_page_set = dump_pase_in->dump_page_set;

	/* Search all NUMA nodes */
	for (i = 0; i < ihk_mc_get_nr_numa_nodes(); i++) {

		free_chunks = &memory_nodes[i].free_chunks;
		free_pages = memory_nodes[i].nr_free_pages;

		/* rb-tree search */
		for (free_page_cnt = 0, node = rb_first_safe(free_chunks); node; free_page_cnt++, node = rb_next_safe(node)) {

			if (free_page_cnt >= free_pages)
				break;

			/* Get chunk information */
			chunk = ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));

			dump_page = dump_pase_in->dump_pages;
			chunk_addr = chunk->addr;
			chunk_size = chunk->size;

			for (j = 0; j < dump_page_set->count; j++) {

				if (j) {
					dump_page = (struct ihk_dump_page *)((char *)dump_page + ((dump_page->map_count * sizeof(unsigned long)) + sizeof(struct ihk_dump_page)));
				}

				phy_start = dump_page->start;
				map_size = (dump_page->map_count << (PAGE_SHIFT+6));

				if ((chunk_addr >= phy_start)
					&& ((phy_start + map_size) >= chunk_addr)) {

					/* Set free page to page map */
					map_start = (chunk_addr - phy_start) >> PAGE_SHIFT;

					if ((phy_start + map_size) < (chunk_addr + chunk_size)) {
						set_size = map_size - (chunk_addr - phy_start);
						map_end = (map_start + (set_size >> PAGE_SHIFT));
						chunk_addr += set_size;
						chunk_size -= set_size;
					} else {
						map_end = (map_start + (chunk_size >> PAGE_SHIFT));
					}

					for (k = map_start; k < map_end; k++) {

						if (MAP_INDEX(k) >= dump_page->map_count) {
							kprintf("%s:free page is out of range(max:%d): %ld (map_start:0x%lx, map_end:0x%lx) k(0x%lx)\n", __FUNCTION__, dump_page->map_count, MAP_INDEX(k), map_start, map_end, k);
							break;
						}

						dump_page->map[MAP_INDEX(k)] &= ~(1UL << MAP_BIT(k));
					}
				}
			}
		}
	}
#endif
	return;
}
#endif

int ihk_mc_chk_page_address(pte_t mem_addr){
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return mem_chk_page_address_result(mem_addr, ihk_mc_get_nr_memory_chunks,
			ihk_mc_get_memory_chunk);
#else
	int i, numa_id;;
	unsigned long start, end;

	/* Search all NUMA nodes */
	for (i = 0; i < ihk_mc_get_nr_memory_chunks(); i++) {
		ihk_mc_get_memory_chunk(i, &start, &end, &numa_id);
		if ((mem_addr >= start) && (end >= mem_addr))
			return 0;
	}

	return -1;
#endif
}

int ihk_mc_get_mem_user_page(void *arg0, page_table_t pt, pte_t *ptep, void *pgaddr, int pgshift)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	(void)pt;
	(void)pgaddr;
	return mem_get_mem_user_page_result((struct dump_pase_info *)arg0,
			(unsigned long *)ptep, pgshift, ihk_mc_chk_page_address,
			mem_dump_warn_bridge);
#else
	struct ihk_dump_page_set *dump_page_set;
	int i;
	unsigned long j, phy_start, phys, map_start, map_end, map_size, set_size;
	struct ihk_dump_page *dump_page;
	struct dump_pase_info *dump_pase_in;
	unsigned long chunk_addr, chunk_size;

	if (((*ptep) & PTATTR_ACTIVE) && ((*ptep) & PTATTR_USER)) {
		phys = pte_get_phys(ptep);
		/* Confirm accessible address */
		if (-1 != ihk_mc_chk_page_address(phys)) {

			dump_pase_in = (struct dump_pase_info *)arg0;
			dump_page_set = dump_pase_in->dump_page_set;
			dump_page = dump_pase_in->dump_pages;

			chunk_addr = phys;
			chunk_size = (1UL << pgshift);

			for (i = 0; i < dump_page_set->count; i++) {

				if (i) {
					dump_page = (struct ihk_dump_page *)((char *)dump_page + ((dump_page->map_count * sizeof(unsigned long)) + sizeof(struct ihk_dump_page)));
				}

				phy_start = dump_page->start;
				map_size = (dump_page->map_count << (PAGE_SHIFT+6));

				if ((chunk_addr >= phy_start)
					&& ((phy_start + map_size) >= chunk_addr)) {

					/* Set user page to page map */
					map_start = (chunk_addr - phy_start) >> PAGE_SHIFT;

					if ((phy_start + map_size) < (chunk_addr + chunk_size)) {
						set_size = map_size - (chunk_addr - phy_start);
						map_end = (map_start + (set_size >> PAGE_SHIFT));
						chunk_addr += set_size;
						chunk_size -= set_size;
					} else {
						map_end = (map_start + (chunk_size >> PAGE_SHIFT));
					}

					for (j = map_start; j < map_end; j++) {

						if (MAP_INDEX(j) >= dump_page->map_count) {
							kprintf("%s:user page is out of range(max:%d): %ld (map_start:0x%lx, map_end:0x%lx) j(0x%lx)\n", __FUNCTION__, dump_page->map_count, MAP_INDEX(j), map_start, map_end, j);
							break;
						}
						dump_page->map[MAP_INDEX(j)] &= ~(1UL << MAP_BIT(j));
					}
				}
			}
		}
	}

	return 0;
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
static pte_t *mem_lookup_fault_pte_bridge(page_table_t pt, void *virt,
		int pgshift, void **basep, size_t *sizep, int *p2alignp)
{
	return ihk_mc_pt_lookup_pte(pt, virt, pgshift, basep, sizep, p2alignp);
}

static int mem_page_fault_process_vm_bridge(struct process_vm *vm,
		void *virt, unsigned long reason)
{
	return page_fault_process_vm(vm, virt, reason);
}

static void mem_lookup_fault_log_bridge(void *virt)
{
	kprintf("%s: successfully faulted 0x%lx\n",
			"ihk_mc_pt_lookup_fault_pte", (unsigned long)virt);
}
#endif

pte_t *ihk_mc_pt_lookup_fault_pte(struct process_vm *vm, void *virt,
		int pgshift, void **basep, size_t *sizep, int *p2alignp)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return mem_pt_lookup_fault_pte_body_result(vm, virt, pgshift, basep,
			sizep, p2alignp,
			__builtin_offsetof(struct process_vm, address_space),
			__builtin_offsetof(struct address_space, page_table),
			mem_lookup_fault_pte_bridge,
			mem_page_fault_process_vm_bridge,
			mem_lookup_fault_log_bridge);
#else
	int faulted = 0;
	pte_t *ptep;

retry:
	ptep = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
			virt, pgshift, basep, sizep, p2alignp);
	if (!faulted && (!ptep || !pte_is_present(ptep))) {
		page_fault_process_vm(vm, virt, PF_POPULATE | PF_USER);
		faulted = 1;
		goto retry;
	}

	if (faulted && ptep && pte_is_present(ptep)) {
		kprintf("%s: successfully faulted 0x%lx\n", __FUNCTION__, virt);
	}

	return ptep;
#endif
}

#ifdef MCKERNEL_RUST_MEM_HELPERS
extern int phys_to_nid(unsigned long p);
#else
int phys_to_nid(unsigned long p)
{
   int i, numa_id = -1, _numa_id;
   unsigned long _start, _end;

   for (i = 0; i < ihk_mc_get_nr_memory_chunks(); i++) {
	   ihk_mc_get_memory_chunk(i, &_start, &_end, &_numa_id);

	   if (p >= _start && p < _end) {
		   numa_id = _numa_id;
		   goto out;
	   }
   }

out:
   return numa_id;
}
#endif /* MCKERNEL_RUST_MEM_HELPERS */

int lookup_node(struct process_vm *vm, void *addr)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return mem_lookup_node_body_result(vm, addr,
			__builtin_offsetof(struct process_vm, address_space),
			__builtin_offsetof(struct address_space, page_table),
			mem_lookup_fault_pte_bridge,
			mem_page_fault_process_vm_bridge, phys_to_nid);
#else
	int node, err, reason = PF_POPULATE | PF_USER;
	pte_t *ptep;

	err = page_fault_process_vm(vm, (void *)addr, reason);
	if (err) {
		node = err;
		goto out;
	}

	ptep = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
			(void *)addr, 0, NULL, NULL, NULL);
	if (!ptep || !pte_is_present(ptep)) {
		node = -ENOENT;
		goto out;
	}

	node = phys_to_nid(pte_get_phys(ptep));
out:
	return node;
#endif
}

#ifdef MCKERNEL_RUST_PAGE_HELPERS
extern int is_splitable(struct page *page, uint32_t memobj_flags);
#else
int page_mode_in_memobj_result(int mode)
{
	return mode == PM_MAPPED || mode == PM_PAGEIO ||
		mode == PM_WILL_PAGEIO || mode == PM_DONE_PAGEIO ||
		mode == PM_PAGEIO_EOF || mode == PM_PAGEIO_ERROR;
}

int page_multi_mapped_result(int count)
{
	return count > 1;
}

int is_splitable(struct page *page, uint32_t memobj_flags)
{
	int ret = 1;

	if (page && (page_is_in_memobj(page)
			|| page_is_multi_mapped(page))) {
		if (memobj_flags & MF_SHM) {
			goto out;
		}
		ret = 0;
	}
out:
	return ret;
}
#endif /* MCKERNEL_RUST_PAGE_HELPERS */
