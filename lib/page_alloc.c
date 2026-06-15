/**
 * \file page_alloc.c
 *  License details are found in the file LICENSE.
 * \brief
 *  IHK - Generic page allocator (manycore version)
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY
 */

#include <types.h>
#include <string.h>
#include <ihk/debug.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <ihk/page_alloc.h>
#include <memory.h>
#include <bitops.h>
#include <errno.h>
#include <cls.h>

//#define DEBUG_PRINT_PAGE_ALLOC

#ifdef DEBUG_PRINT_PAGE_ALLOC
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

void free_pages(void *, int npages);

typedef unsigned long (*page_alloc_irq_save_fn_t)(void);
typedef void (*page_alloc_irq_restore_fn_t)(unsigned long irqstate);
typedef void *(*page_alloc_alloc_pages_fn_t)(int npages, int flag);
typedef void (*page_alloc_free_pages_fn_t)(void *ptr, int npages);
typedef void (*page_alloc_mcs_lock_init_fn_t)(unsigned long lock_addr);
typedef void (*page_alloc_mcs_lock_fn_t)(unsigned long lock_addr,
		unsigned long lock_node_addr);
typedef void (*page_alloc_mcs_unlock_fn_t)(unsigned long lock_addr,
		unsigned long lock_node_addr);
typedef int (*page_alloc_zero_send_fn_t)(unsigned long packet_addr);
typedef void (*page_alloc_alloc_log_fn_t)(int event, unsigned long node_addr,
		unsigned long addr, int npages, int source);
typedef void (*page_alloc_add_free_log_fn_t)(int event,
		unsigned long node_addr, unsigned long addr,
		unsigned long size, int rc);
typedef void (*page_alloc_free_log_fn_t)(int event, unsigned long node_addr,
		unsigned long addr, int npages, int zero_at_free_value,
		int detail);
typedef void (*page_alloc_init_fail_log_fn_t)(unsigned long start,
		unsigned long size, unsigned long unit);
typedef void (*page_alloc_free_error_fn_t)(unsigned long bad_address);
typedef void (*page_alloc_zero_log_fn_t)(int event);

#define IHK_NUMA_ALLOC_LOG_CACHE_HIT 1
#define IHK_NUMA_ALLOC_LOG_DIRECT_OK 2
#define IHK_NUMA_ADD_FREE_LOG_ERROR 1
#define IHK_NUMA_ADD_FREE_LOG_OK 2

#define IHK_NUMA_FREE_DIRECT 0
#define IHK_NUMA_FREE_DEFERRED 1
#define IHK_NUMA_FREE_IGNORED 2

#define IHK_NUMA_FREE_LOG_DIRECT_ERROR 1
#define IHK_NUMA_FREE_LOG_DIRECT_OK 2
#define IHK_NUMA_FREE_LOG_DEFER_ERROR 3
#define IHK_NUMA_FREE_LOG_ZERO_SKIP 4
#define IHK_NUMA_FREE_LOG_SEND_FAIL 5
#define IHK_NUMA_FREE_LOG_SEND_OK 6
#define IHK_NUMA_FREE_LOG_UNEXPECTED 7
#define IHK_NUMA_FREE_LOG_CPU_CACHE_OK 8
#define IHK_NUMA_FREE_LOG_CPU_CACHE_FAILED 9

#define PAGEALLOC_ZERO_LOG_BEGIN 1
#define PAGEALLOC_ZERO_LOG_DONE 2

static void *page_alloc_alloc_pages_bridge(int npages, int flag)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

static void page_alloc_free_pages_bridge(void *ptr, int npages)
{
	_ihk_mc_free_pages(ptr, npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

#ifndef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
void ihk_mc_page_cache_free(struct ihk_mc_page_cache_header *cache, void *page)
{
	struct ihk_mc_page_cache_header *current = NULL;
	struct ihk_mc_page_cache_header *new =
		(struct ihk_mc_page_cache_header *)page;

	if (unlikely(!page))
		return;

retry:
	current = cache->next;
	new->next = current;

	if (!__sync_bool_compare_and_swap(&cache->next, current, new)) {
		goto retry;
	}
}

void ihk_mc_page_cache_prealloc(struct ihk_mc_page_cache_header *cache,
		int nr_pages, int nr_elem)
{
	int i;

	if (unlikely(cache->next))
		return;

	for (i = 0; i < nr_elem; ++i) {
		void *pages;

		pages = _ihk_mc_alloc_aligned_pages_node(nr_pages, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);

		if (!pages) {
			kprintf("%s: ERROR: allocating pages..\n", __func__);
			continue;
		}

		ihk_mc_page_cache_free(cache, pages);
	}
}

void *ihk_mc_page_cache_alloc(struct ihk_mc_page_cache_header *cache,
		int nr_pages)
{
	register struct ihk_mc_page_cache_header *first, *next;

retry:
	next = NULL;
	first = cache->next;

	if (first) {
		next = first->next;

		if (!__sync_bool_compare_and_swap(&cache->next, first, next)) {
			goto retry;
		}
	} else {
		kprintf("%s: calling pre-alloc for 0x%lx...\n", __func__, cache);

		ihk_mc_page_cache_prealloc(cache, nr_pages, 256);
		goto retry;
	}

	return (void *)first;
}
#endif

static void page_alloc_mcs_lock_init_bridge(unsigned long lock_addr)
{
	mcs_lock_init((mcs_lock_t *)lock_addr);
}

static void page_alloc_mcs_lock_bridge(unsigned long lock_addr,
		unsigned long lock_node_addr)
{
	mcs_lock_lock((mcs_lock_t *)lock_addr,
			(mcs_lock_node_t *)lock_node_addr);
}

static void page_alloc_mcs_unlock_bridge(unsigned long lock_addr,
		unsigned long lock_node_addr)
{
	mcs_lock_unlock((mcs_lock_t *)lock_addr,
			(mcs_lock_node_t *)lock_node_addr);
}

#define IHK_NUMA_CPU_CACHE_FREE_NOT_TRIED 0
#define IHK_NUMA_CPU_CACHE_FREE_SUCCESS 1
#define IHK_NUMA_CPU_CACHE_FREE_FAILED 2

#define MAP_INDEX(n)    ((n) >> 6)
#define MAP_BIT(n)      ((n) & 0x3f)
#define ADDRESS(desc, index, bit)    \
	((desc)->start + (((uintptr_t)(index) * 64 + (bit)) << ((desc)->shift)))

#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
int pagealloc_init_layout_result(unsigned long size, unsigned long unit,
		unsigned long desc_struct_size, int *page_shiftp,
		int *mapsizep, int *mapalignedp, int *desc_pagesp);
void pagealloc_reserve_tail_result(unsigned long *map, int first,
		int limit);
unsigned long pagealloc_init_end_result(unsigned long start,
		unsigned long size);
int pagealloc_init_count_result(int mapaligned);
int pagealloc_destroy_pages_result(int flag);
int pagealloc_destroy_result(struct ihk_page_allocator_desc *desc,
		page_alloc_free_pages_fn_t free_pages_fn);
struct ihk_page_allocator_desc *pagealloc_init_result(
		unsigned long start, unsigned long size, unsigned long unit,
		void *initial, unsigned long *pdescsize,
		unsigned long desc_struct_size, int alloc_flag,
		unsigned long page_size, unsigned long lock_offset,
		page_alloc_alloc_pages_fn_t alloc_pages_fn,
		page_alloc_mcs_lock_init_fn_t lock_init_fn, int *statusp);
void pagealloc_desc_reset_result(struct ihk_page_allocator_desc *desc,
		int desc_pages, unsigned long page_size);
void pagealloc_desc_init_result(struct ihk_page_allocator_desc *desc,
		unsigned long start, unsigned long size, int page_shift,
		int mapaligned, int flag);
unsigned long __ihk_pagealloc_large_nolock(
		struct ihk_page_allocator_desc *desc, int npages, int p2align);
unsigned long __ihk_pagealloc_alloc_nolock(
		struct ihk_page_allocator_desc *desc, int npages, int p2align);
void __ihk_pagealloc_reserve_nolock(
		struct ihk_page_allocator_desc *desc,
		unsigned long start, unsigned long end);
int __ihk_pagealloc_free_nolock(
		struct ihk_page_allocator_desc *desc,
		unsigned long address, int npages, unsigned long *bad_address);
unsigned long __ihk_pagealloc_count_nolock(
		struct ihk_page_allocator_desc *desc);
int __ihk_pagealloc_query_free_nolock(
		struct ihk_page_allocator_desc *desc);
void __ihk_pagealloc_zero_free_pages_nolock(
		struct ihk_page_allocator_desc *desc);
unsigned long __ihk_pagealloc_alloc_locked_result(
		struct ihk_page_allocator_desc *desc, int npages, int p2align,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int __ihk_pagealloc_reserve_locked_result(
		struct ihk_page_allocator_desc *desc,
		unsigned long start, unsigned long end,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int __ihk_pagealloc_free_locked_result(
		struct ihk_page_allocator_desc *desc,
		unsigned long address, int npages, unsigned long *bad_address,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
unsigned long __ihk_pagealloc_count_locked_result(
		struct ihk_page_allocator_desc *desc,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int __ihk_pagealloc_query_free_locked_result(
		struct ihk_page_allocator_desc *desc,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int __ihk_pagealloc_zero_free_pages_locked_result(
		struct ihk_page_allocator_desc *desc,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
void *pagealloc_public_init_result(unsigned long start, unsigned long size,
		unsigned long unit, void *initial, unsigned long *pdescsize,
		unsigned long desc_struct_size, int alloc_flag,
		unsigned long page_size, unsigned long lock_offset,
		page_alloc_alloc_pages_fn_t alloc_pages_fn,
		page_alloc_mcs_lock_init_fn_t lock_init_fn,
		page_alloc_init_fail_log_fn_t init_fail_log_fn);
unsigned long pagealloc_public_alloc_result(void *desc, int npages,
		int p2align, unsigned long lock_offset,
		unsigned long lock_node_addr, page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int pagealloc_public_reserve_result(void *desc, unsigned long start,
		unsigned long end, unsigned long lock_offset,
		unsigned long lock_node_addr, page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int pagealloc_public_free_result(void *desc, unsigned long address,
		int npages, unsigned long lock_offset,
		unsigned long lock_node_addr, page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn,
		page_alloc_free_error_fn_t error_fn);
unsigned long pagealloc_public_count_result(void *desc,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int pagealloc_public_query_free_result(void *desc, unsigned long lock_offset,
		unsigned long lock_node_addr, page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn);
int pagealloc_public_zero_free_pages_result(void *desc,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn,
		page_alloc_zero_log_fn_t log_fn);
#else
static int pagealloc_init_layout_result(unsigned long size, unsigned long unit,
		unsigned long desc_struct_size, int *page_shiftp,
		int *mapsizep, int *mapalignedp, int *desc_pagesp)
{
	int page_shift;
	int mapsize;
	int mapaligned;
	int descsize;

	if (!unit)
		return -EINVAL;

	page_shift = fls(unit) - 1;
	mapsize = size >> page_shift;
	mapaligned = ((mapsize + 63) >> 6) << 3;
	descsize = desc_struct_size + mapaligned;
	descsize = (descsize + PAGE_SIZE - 1) >> PAGE_SHIFT;

	*page_shiftp = page_shift;
	*mapsizep = mapsize;
	*mapalignedp = mapaligned;
	*desc_pagesp = descsize;
	return 0;
}

static void pagealloc_reserve_tail_result(unsigned long *map, int first,
		int limit)
{
	int i;

	for (i = first; i < limit; i++)
		map[MAP_INDEX(i)] |= (1UL << MAP_BIT(i));
}

static unsigned long pagealloc_init_end_result(unsigned long start,
		unsigned long size)
{
	return start + size;
}

static int pagealloc_init_count_result(int mapaligned)
{
	return mapaligned >> 3;
}

static int pagealloc_destroy_pages_result(int flag)
{
	return flag;
}

static int pagealloc_destroy_result(struct ihk_page_allocator_desc *desc,
		page_alloc_free_pages_fn_t free_pages_fn)
{
	int pages;

	if (!desc || !free_pages_fn)
		return 0;

	pages = pagealloc_destroy_pages_result(desc->flag);
	free_pages_fn(desc, pages);
	return pages;
}

static void pagealloc_desc_reset_result(struct ihk_page_allocator_desc *desc,
		int desc_pages, unsigned long page_size)
{
	if (!desc || desc_pages <= 0 || !page_size)
		return;

	memset(desc, 0, desc_pages * page_size);
}

static void pagealloc_desc_init_result(struct ihk_page_allocator_desc *desc,
		unsigned long start, unsigned long size, int page_shift,
		int mapaligned, int flag)
{
	if (!desc)
		return;

	desc->start = start;
	desc->end = pagealloc_init_end_result(start, size);
	desc->last = 0;
	desc->count = pagealloc_init_count_result(mapaligned);
	desc->shift = page_shift;
	desc->flag = flag;
}
#endif

#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
static void pagealloc_init_fail_log_bridge(unsigned long start,
		unsigned long size, unsigned long unit)
{
	kprintf("IHK: failed to allocate page-allocator-desc "\
	        "(%lx, %lx, %lx)\n", start, size, unit);
}
#endif

void *__ihk_pagealloc_init(unsigned long start, unsigned long size,
                           unsigned long unit, void *initial,
                           unsigned long *pdescsize)
{
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	return pagealloc_public_init_result(start, size, unit, initial, pdescsize,
			sizeof(struct ihk_page_allocator_desc),
			IHK_MC_AP_CRITICAL, PAGE_SIZE,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			page_alloc_alloc_pages_bridge,
			page_alloc_mcs_lock_init_bridge,
			pagealloc_init_fail_log_bridge);
#else
	/* Unit must be power of 2, and size and start must be unit-aligned */
	struct ihk_page_allocator_desc *desc;
	int page_shift, descsize, mapsize, mapaligned;
	int flag = 0;

	if (pagealloc_init_layout_result(size, unit, sizeof(*desc),
				&page_shift, &mapsize, &mapaligned,
				&descsize)) {
		return NULL;
	}

	if (initial) {
		desc = initial;
		*pdescsize = descsize;
	} else {
		desc = (void *)_ihk_mc_alloc_aligned_pages_node(descsize, PAGE_P2ALIGN, IHK_MC_AP_CRITICAL, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	}
	if (!desc) {
		kprintf("IHK: failed to allocate page-allocator-desc "\
		        "(%lx, %lx, %lx)\n", start, size, unit);
		return NULL;
	}

	flag = descsize;
	pagealloc_desc_reset_result(desc, descsize, PAGE_SIZE);
	pagealloc_desc_init_result(desc, start, size, page_shift, mapaligned,
			flag);

	//kprintf("page allocator @ %lx - %lx (%d)\n", start, start + size,
	//        page_shift);

	mcs_lock_init(&desc->lock);

	/* Reserve align padding area */
	pagealloc_reserve_tail_result(desc->map, mapsize, mapaligned * 8);

	return desc;
#endif
}

void *ihk_pagealloc_init(unsigned long start, unsigned long size,
                         unsigned long unit)
{
	return __ihk_pagealloc_init(start, size, unit, NULL, NULL);
}

void ihk_pagealloc_destroy(void *__desc)
{
	struct ihk_page_allocator_desc *desc = __desc;

	pagealloc_destroy_result(desc, page_alloc_free_pages_bridge);
}

static unsigned long __ihk_pagealloc_large(struct ihk_page_allocator_desc *desc,
                                           int npages, int p2align)
{
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	mcs_lock_node_t node;
	unsigned long address;

	mcs_lock_lock(&desc->lock, &node);
	address = __ihk_pagealloc_large_nolock(desc, npages, p2align);
	mcs_lock_unlock(&desc->lock, &node);

	return address;
#else
	unsigned int i, j, mi;
	int nblocks;
	int nfrags;
	unsigned long mask;
	unsigned long align_mask = ((PAGE_SIZE << p2align) - 1);
	mcs_lock_node_t node;

	nblocks = (npages / 64);
	mask = -1;
	nfrags = (npages % 64);
	if (nfrags > 0) {
		++nblocks;
		mask = (1UL << nfrags) - 1;
	}

	mcs_lock_lock(&desc->lock, &node);
	for (i = 0, mi = desc->last; i < desc->count; i++, mi++) {
		if (mi >= desc->count) {
			mi = 0;
		}
		if ((mi + nblocks >= desc->count) || (ADDRESS(desc, mi, 0) & align_mask)) {
			continue;
		}
		for (j = mi; j < mi + nblocks - 1; j++) {
			if (desc->map[j]) {
				break;
			}
		}
		if ((j == (mi + nblocks - 1)) && !(desc->map[j] & mask)) {
			for (j = mi; j < mi + nblocks - 1; j++) {
				desc->map[j] = (unsigned long)-1;
			}
			desc->map[j] |= mask;
			mcs_lock_unlock(&desc->lock, &node);
			return ADDRESS(desc, mi, 0);
		}
	}
	mcs_lock_unlock(&desc->lock, &node);

	return 0;
#endif
}

unsigned long ihk_pagealloc_alloc(void *__desc, int npages, int p2align)
{
	struct ihk_page_allocator_desc *desc = __desc;
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	mcs_lock_node_t node;

	return pagealloc_public_alloc_result(desc, npages, p2align,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			(unsigned long)&node, page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge);
#else
	unsigned int i, mi;
	int j;
	unsigned long v, mask;
	int jalign;
	mcs_lock_node_t node;

	if ((npages >= 32) || (p2align >= 5)) {
		return __ihk_pagealloc_large(desc, npages, p2align);
	}

	mask = (1UL << npages) - 1;
	jalign = (p2align <= 0)? 1: (1 << p2align);

	mcs_lock_lock(&desc->lock, &node);
	for (i = 0, mi = desc->last; i < desc->count; i++, mi++) {
		if (mi >= desc->count) {
			mi = 0;
		}
		
		v = desc->map[mi];
		if (v == (unsigned long)-1)
			continue;
		
		for (j = 0; j <= 64 - npages; j++) {
			if (j % jalign) {
				continue;
			}
			if (!(v & (mask << j))) { /* free */
				desc->map[mi] |= (mask << j);

				mcs_lock_unlock(&desc->lock, &node);
				return ADDRESS(desc, mi, j);
			}
		}
	}
	mcs_lock_unlock(&desc->lock, &node);

	/* We use null pointer for failure */
	return 0;
#endif
}

void ihk_pagealloc_reserve(void *__desc, unsigned long start, unsigned long end)
{
	struct ihk_page_allocator_desc *desc = __desc;
	mcs_lock_node_t node;
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	pagealloc_public_reserve_result(desc, start, end,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			(unsigned long)&node, page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge);
#else
	int i, n;

	n = (end + (1 << desc->shift) - 1 - desc->start) >> desc->shift;
	i = ((start - desc->start) >> desc->shift);
	if (i < 0 || n < 0) {
		return;
	}

	mcs_lock_lock(&desc->lock, &node);
	for (; i < n; i++) {
		if (!(i & 63) && i + 63 < n) {
			desc->map[MAP_INDEX(i)] = (unsigned long)-1L;
			i += 63;
		} else {
			desc->map[MAP_INDEX(i)] |= (1UL << MAP_BIT(i));
		}
	}
	mcs_lock_unlock(&desc->lock, &node);
#endif
}

#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
static void pagealloc_free_error_bridge(unsigned long bad_address)
{
	kprintf("%s: double-freeing page 0x%lx\n",
		"ihk_pagealloc_free", bad_address);
	panic("panic");
}
#endif

void ihk_pagealloc_free(void *__desc, unsigned long address, int npages)
{
	struct ihk_page_allocator_desc *desc = __desc;
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	mcs_lock_node_t node;

	pagealloc_public_free_result(desc, address, npages,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			(unsigned long)&node, page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge,
			pagealloc_free_error_bridge);
#else
	int i;
	unsigned mi;
	mcs_lock_node_t node;

	/* XXX: Parameter check */
	mcs_lock_lock(&desc->lock, &node);
	mi = (address - desc->start) >> desc->shift;
	for (i = 0; i < npages; i++, mi++) {
		if (!(desc->map[MAP_INDEX(mi)] & (1UL << MAP_BIT(mi)))) {
			kprintf("%s: double-freeing page 0x%lx\n",
				__FUNCTION__, address + i * PAGE_SIZE);
			panic("panic");
		}
		else {
			desc->map[MAP_INDEX(mi)] &= ~(1UL << MAP_BIT(mi));
		}
	}
	mcs_lock_unlock(&desc->lock, &node);
#endif
}

unsigned long ihk_pagealloc_count(void *__desc)
{
	struct ihk_page_allocator_desc *desc = __desc;
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	mcs_lock_node_t node;

	return pagealloc_public_count_result(desc,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			(unsigned long)&node, page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge);
#else
	unsigned long i, j, n = 0;
	mcs_lock_node_t node;

	mcs_lock_lock(&desc->lock, &node);
	/* XXX: Very silly counting */
	for (i = 0; i < desc->count; i++) {
		for (j = 0; j < 64; j++) {
			if (!(desc->map[i] & (1UL << j))) {
				n++;
			}
		}
	}
	mcs_lock_unlock(&desc->lock, &node);

	return n;
#endif
}

int ihk_pagealloc_query_free(void *__desc)
{
	struct ihk_page_allocator_desc *desc = __desc;
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	mcs_lock_node_t node;

	return pagealloc_public_query_free_result(desc,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			(unsigned long)&node, page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge);
#else
	unsigned int mi;
	int j;
	unsigned long v;
	int npages = 0;
	mcs_lock_node_t node;

	mcs_lock_lock(&desc->lock, &node);
	for (mi = 0; mi < desc->count; mi++) {
		
		v = desc->map[mi];
		if (v == (unsigned long)-1)
			continue;
		
		for (j = 0; j < 64; j++) {
			if (!(v & ((unsigned long)1 << j))) { /* free */
				npages++;
			}
		}
	}
	mcs_lock_unlock(&desc->lock, &node);

	return npages;
#endif
}

#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
static void pagealloc_zero_log_bridge(int event)
{
	switch (event) {
	case PAGEALLOC_ZERO_LOG_BEGIN:
		kprintf("zeroing free memory... ");
		break;
	case PAGEALLOC_ZERO_LOG_DONE:
		kprintf("\nzeroing done\n");
		break;
	}
}
#endif

void __ihk_pagealloc_zero_free_pages(void *__desc)
{
	struct ihk_page_allocator_desc *desc = __desc;
#ifdef MCKERNEL_RUST_PAGEALLOC_BITMAP
	mcs_lock_node_t node;

	pagealloc_public_zero_free_pages_result(desc,
			__builtin_offsetof(struct ihk_page_allocator_desc, lock),
			(unsigned long)&node, page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge,
			pagealloc_zero_log_bridge);
#else
	unsigned int mi;
	int j;
	unsigned long v;
	mcs_lock_node_t node;

kprintf("zeroing free memory... ");

	mcs_lock_lock(&desc->lock, &node);
	for (mi = 0; mi < desc->count; mi++) {
		
		v = desc->map[mi];
		if (v == (unsigned long)-1)
			continue;
		
		for (j = 0; j < 64; j++) {
			if (!(v & ((unsigned long)1 << j))) { /* free */

				memset(phys_to_virt(ADDRESS(desc, mi, j)), 0, PAGE_SIZE); 
			}
		}
	}
	mcs_lock_unlock(&desc->lock, &node);

kprintf("\nzeroing done\n");
#endif
}


#ifdef IHK_RBTREE_ALLOCATOR

int zero_at_free = 1;
int deferred_zero_at_free = 1;

/*
 * Simple red-black tree based physical memory management routines.
 *
 * Allocation grabs first suitable chunk (splits chunk if alignment requires it).
 * Deallocation merges with immediate neighbours.
 *
 * NOTE: invariant property: free_chunk structures are placed in the very front
 * of their corresponding memory (i.e., they are on the free memory chunk itself).
 */

#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
int __page_alloc_rbtree_free_range(struct rb_root *root,
		unsigned long addr, unsigned long size);
unsigned long __page_alloc_rbtree_alloc_pages(struct rb_root *root,
		int npages, int p2align);
unsigned long __page_alloc_rbtree_reserve_pages(struct rb_root *root,
		unsigned long aligned_addr, int npages);
struct free_chunk *__page_alloc_rbtree_get_root_chunk(
		struct rb_root *root);
int __ihk_numa_add_free_pages(struct ihk_mc_numa_node *node,
		unsigned long addr, unsigned long size);
int __ihk_numa_zero_free_pages_node(struct ihk_mc_numa_node *node,
		int nr_pages);
int __ihk_numa_zero_free_pages_dispatch(struct ihk_mc_numa_node *node,
		int nr_pages);
int ihk_numa_add_free_pages_result(struct ihk_mc_numa_node *node,
		unsigned long addr, unsigned long size,
		page_alloc_add_free_log_fn_t log_fn);
void ihk_numa_zero_free_pages_result(struct ihk_mc_numa_node *node);
unsigned long __ihk_numa_alloc_pages_nolock(
		struct ihk_mc_numa_node *node, int npages, int p2align);
int __ihk_numa_free_pages_to_tree_nolock(
		struct ihk_mc_numa_node *node, unsigned long addr, int npages);
int __ihk_numa_defer_zero_free_pages(
		struct ihk_mc_numa_node *node, unsigned long addr, int npages);
int __ihk_numa_free_pages_prepare(
		struct ihk_mc_numa_node *node, unsigned long addr, int npages,
		int defer_zero_at_free);
int __ihk_numa_cpu_cache_try_result(int cpu_initialized);
int __ihk_numa_cpu_cache_alloc_hit_result(unsigned long addr);
int __ihk_numa_cpu_cache_free_success_result(int free_rc);
	unsigned long __ihk_numa_cpu_cache_alloc_nolock(struct rb_root *root,
			int npages, int p2align);
	int __ihk_numa_cpu_cache_free_nolock(struct rb_root *root,
			unsigned long addr, int npages);
	unsigned long __ihk_numa_cpu_cache_alloc_try_result(int cpu_initialized,
			struct rb_root *root, int npages, int p2align,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn);
	int __ihk_numa_cpu_cache_free_try_result(int cpu_initialized,
			struct rb_root *root, unsigned long addr, int npages,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn);
	unsigned long __ihk_numa_alloc_pages_locked_result(
			struct ihk_mc_numa_node *node, int npages, int p2align,
			unsigned long lock_offset, unsigned long lock_node_addr,
			page_alloc_mcs_lock_fn_t lock_fn,
			page_alloc_mcs_unlock_fn_t unlock_fn);
	unsigned long ihk_numa_alloc_pages_orchestrate_result(
			struct ihk_mc_numa_node *node, int cpu_initialized,
			struct rb_root *cache_root, int npages, int p2align,
			unsigned long lock_offset, unsigned long lock_node_addr,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn,
			page_alloc_mcs_lock_fn_t lock_fn,
			page_alloc_mcs_unlock_fn_t unlock_fn, int *sourcep);
	unsigned long ihk_numa_alloc_pages_result(
			struct ihk_mc_numa_node *node, int cpu_initialized,
			struct rb_root *cache_root, int npages, int p2align,
			unsigned long lock_offset, unsigned long lock_node_addr,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn,
			page_alloc_mcs_lock_fn_t lock_fn,
			page_alloc_mcs_unlock_fn_t unlock_fn,
			page_alloc_alloc_log_fn_t log_fn);
	int __ihk_numa_free_pages_direct_locked_result(
			struct ihk_mc_numa_node *node, unsigned long addr,
			int npages, unsigned long lock_offset,
			unsigned long lock_node_addr,
			page_alloc_mcs_lock_fn_t lock_fn,
			page_alloc_mcs_unlock_fn_t unlock_fn);
	int ihk_numa_free_pages_orchestrate_result(
			struct ihk_mc_numa_node *node, unsigned long addr,
			int npages, int defer_zero_at_free,
			struct ikc_scd_packet *packet, int cpu_initialized,
			unsigned long current_thread, unsigned long idle_thread,
			unsigned long thread_proc_offset,
			unsigned long proc_nohost_offset,
			unsigned long proc_pid_offset, int cpu_ref,
			unsigned long syscall_number, unsigned long lock_offset,
			unsigned long lock_node_addr,
			page_alloc_mcs_lock_fn_t lock_fn,
			page_alloc_mcs_unlock_fn_t unlock_fn, int *direct_rcp,
			int *zero_request_actionp);
	int __ihk_numa_linux_zero_request_action(int cpu_initialized,
			int has_current, int is_idle, int nohost, int zeroing_workers);
void __ihk_numa_zeroing_worker_inc(struct ihk_mc_numa_node *node);
void __ihk_numa_zero_request_packet_fill(struct ikc_scd_packet *packet,
		unsigned long node_addr, int cpu_ref, int pid,
		unsigned long syscall_number);
	int __ihk_numa_linux_zero_request_prepare(struct ihk_mc_numa_node *node,
		struct ikc_scd_packet *packet, int cpu_initialized,
		unsigned long current_thread, unsigned long idle_thread,
		unsigned long thread_proc_offset,
		unsigned long proc_nohost_offset,
		unsigned long proc_pid_offset, int cpu_ref,
		unsigned long syscall_number);
	int __ihk_numa_free_pages_deferred_result(
			struct ihk_mc_numa_node *node, unsigned long addr,
			int npages, struct ikc_scd_packet *packet,
			int cpu_initialized, unsigned long current_thread,
			unsigned long idle_thread, unsigned long thread_proc_offset,
			unsigned long proc_nohost_offset,
			unsigned long proc_pid_offset, int cpu_ref,
			unsigned long syscall_number);
	int ihk_numa_free_pages_finish_result(int free_action,
			int direct_rc, int zero_request_action,
			unsigned long node_addr, unsigned long addr, int npages,
			int zero_at_free_value, unsigned long packet_addr,
			page_alloc_zero_send_fn_t send_fn,
			page_alloc_free_log_fn_t log_fn);
	int ihk_numa_free_pages_result(
			struct ihk_mc_numa_node *node, unsigned long addr,
			int npages, int defer_zero_at_free_value,
			int zero_at_free_value, struct ikc_scd_packet *packet,
			int cpu_initialized, struct rb_root *cache_root,
			unsigned long current_thread, unsigned long idle_thread,
			unsigned long thread_proc_offset,
			unsigned long proc_nohost_offset,
			unsigned long proc_pid_offset, int cpu_ref,
			unsigned long syscall_number, unsigned long lock_offset,
			unsigned long lock_node_addr,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn,
			page_alloc_mcs_lock_fn_t lock_fn,
			page_alloc_mcs_unlock_fn_t unlock_fn,
			page_alloc_zero_send_fn_t send_fn,
			page_alloc_free_log_fn_t log_fn);
#else

static int __page_alloc_rbtree_free_range(struct rb_root *root,
		unsigned long addr, unsigned long size);
static unsigned long __page_alloc_rbtree_alloc_pages(struct rb_root *root,
		int npages, int p2align);

int __ihk_numa_cpu_cache_try_result(int cpu_initialized)
{
	return cpu_initialized ? 1 : 0;
}

int __ihk_numa_cpu_cache_alloc_hit_result(unsigned long addr)
{
	return addr ? 1 : 0;
}

int __ihk_numa_cpu_cache_free_success_result(int free_rc)
{
	return free_rc ? 0 : 1;
}

unsigned long __ihk_numa_cpu_cache_alloc_nolock(struct rb_root *root,
		int npages, int p2align)
{
	if (!root)
		return 0;

	return __page_alloc_rbtree_alloc_pages(root, npages, p2align);
}

	int __ihk_numa_cpu_cache_free_nolock(struct rb_root *root,
			unsigned long addr, int npages)
	{
		if (!root || npages <= 0)
			return EINVAL;

		return __page_alloc_rbtree_free_range(root, addr,
				npages << PAGE_SHIFT);
	}

	unsigned long __ihk_numa_cpu_cache_alloc_try_result(int cpu_initialized,
			struct rb_root *root, int npages, int p2align,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn)
	{
		unsigned long irqflags;
		unsigned long addr;

		if (!cpu_initialized || !irq_save_fn || !irq_restore_fn) {
			return 0;
		}

		irqflags = irq_save_fn();
		addr = __ihk_numa_cpu_cache_alloc_nolock(root, npages, p2align);
		irq_restore_fn(irqflags);

		return addr;
	}

	int __ihk_numa_cpu_cache_free_try_result(int cpu_initialized,
			struct rb_root *root, unsigned long addr, int npages,
			page_alloc_irq_save_fn_t irq_save_fn,
			page_alloc_irq_restore_fn_t irq_restore_fn)
	{
		unsigned long irqflags;
		int rc;

		if (!cpu_initialized || !irq_save_fn || !irq_restore_fn) {
			return IHK_NUMA_CPU_CACHE_FREE_NOT_TRIED;
		}

		irqflags = irq_save_fn();
		rc = __ihk_numa_cpu_cache_free_nolock(root, addr, npages);
		irq_restore_fn(irqflags);

		return rc == 0 ? IHK_NUMA_CPU_CACHE_FREE_SUCCESS :
				IHK_NUMA_CPU_CACHE_FREE_FAILED;
	}

	int __ihk_numa_linux_zero_request_action(int cpu_initialized,
			int has_current, int is_idle, int nohost, int zeroing_workers)
{
	if (!cpu_initialized || !has_current || is_idle || nohost)
		return 0;
	if (zeroing_workers > 0)
		return 2;
	return 1;
}

void __ihk_numa_zeroing_worker_inc(struct ihk_mc_numa_node *node)
{
	ihk_atomic_inc(&node->zeroing_workers);
}

void __ihk_numa_zero_request_packet_fill(struct ikc_scd_packet *packet,
		unsigned long node_addr, int cpu_ref, int pid,
		unsigned long syscall_number)
{
	memset(packet, 0, sizeof(*packet));
	packet->req.number = syscall_number;
	packet->req.args[0] = node_addr;

	barrier();
	smp_store_release_ulong(&packet->req.valid, 1);
	packet->msg = SCD_MSG_SYSCALL_ONESIDE;
	packet->ref = cpu_ref;
	packet->pid = pid;
	packet->resp_pa = 0;
}

int __ihk_numa_linux_zero_request_prepare(struct ihk_mc_numa_node *node,
		struct ikc_scd_packet *packet, int cpu_initialized,
		unsigned long current_thread, unsigned long idle_thread,
		unsigned long thread_proc_offset,
		unsigned long proc_nohost_offset,
		unsigned long proc_pid_offset, int cpu_ref,
		unsigned long syscall_number)
{
	unsigned long proc;
	int action;

	if (!node || !packet || !cpu_initialized || !current_thread)
		return 0;
	if (current_thread == idle_thread)
		return 0;

	proc = *(unsigned long *)(current_thread + thread_proc_offset);
	if (!proc)
		return 0;

	action = __ihk_numa_linux_zero_request_action(cpu_initialized, 1, 0,
			*(int *)(proc + proc_nohost_offset),
			ihk_atomic_read(&node->zeroing_workers));
	if (action != 1)
		return action;

	__ihk_numa_zeroing_worker_inc(node);
	__ihk_numa_zero_request_packet_fill(packet, (unsigned long)node,
			cpu_ref, *(int *)(proc + proc_pid_offset),
			syscall_number);
	return 1;
}

int __ihk_numa_free_pages_deferred_result(
		struct ihk_mc_numa_node *node, unsigned long addr,
		int npages, struct ikc_scd_packet *packet,
		int cpu_initialized, unsigned long current_thread,
		unsigned long idle_thread, unsigned long thread_proc_offset,
		unsigned long proc_nohost_offset,
		unsigned long proc_pid_offset, int cpu_ref,
		unsigned long syscall_number)
{
	struct free_chunk *chunk;

	if (!node || npages <= 0)
		return -EINVAL;

	chunk = (struct free_chunk *)phys_to_virt(addr);
	chunk->addr = addr;
	chunk->size = npages << PAGE_SHIFT;
	ihk_atomic_add(npages, &node->nr_to_zero_pages);
	barrier();
	llist_add(&chunk->list, &node->to_zero_list);

	return __ihk_numa_linux_zero_request_prepare(node, packet,
			cpu_initialized, current_thread, idle_thread,
			thread_proc_offset, proc_nohost_offset,
			proc_pid_offset, cpu_ref, syscall_number);
}

int ihk_numa_add_free_pages_result(struct ihk_mc_numa_node *node,
		unsigned long addr, unsigned long size,
		page_alloc_add_free_log_fn_t log_fn)
{
	int rc;

	if (zero_at_free) {
		memset(phys_to_virt(addr), 0, size);
	}

	rc = __page_alloc_rbtree_free_range(&node->free_chunks, addr, size);
	if (rc) {
		if (log_fn)
			log_fn(IHK_NUMA_ADD_FREE_LOG_ERROR,
					(unsigned long)node, addr, size,
					EINVAL);
		return EINVAL;
	}

	if (addr < node->min_addr)
		node->min_addr = addr;

	if (addr + size > node->max_addr)
		node->max_addr = addr + size;

	node->nr_pages += (size >> PAGE_SHIFT);
	node->nr_free_pages += (size >> PAGE_SHIFT);

	if (log_fn)
		log_fn(IHK_NUMA_ADD_FREE_LOG_OK, (unsigned long)node,
				addr, size, 0);

	return 0;
}

unsigned long ihk_numa_alloc_pages_orchestrate_result(
		struct ihk_mc_numa_node *node, int cpu_initialized,
		struct rb_root *cache_root, int npages, int p2align,
		unsigned long lock_offset, unsigned long lock_node_addr,
		page_alloc_irq_save_fn_t irq_save_fn,
		page_alloc_irq_restore_fn_t irq_restore_fn,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn, int *sourcep)
{
	unsigned long addr;

	if (sourcep)
		*sourcep = 0;

	addr = __ihk_numa_cpu_cache_alloc_try_result(cpu_initialized,
			cache_root, npages, p2align, irq_save_fn,
			irq_restore_fn);
	if (__ihk_numa_cpu_cache_alloc_hit_result(addr)) {
		if (sourcep)
			*sourcep = 1;
		return addr;
	}

	if (!node || !lock_fn || !unlock_fn)
		return 0;

	lock_fn((unsigned long)node + lock_offset, lock_node_addr);
	addr = __page_alloc_rbtree_alloc_pages(&node->free_chunks,
			npages, p2align);
	if (addr)
		node->nr_free_pages -= npages;
	unlock_fn((unsigned long)node + lock_offset, lock_node_addr);

	if (addr && sourcep)
		*sourcep = 2;

	return addr;
}

unsigned long ihk_numa_alloc_pages_result(struct ihk_mc_numa_node *node,
		int cpu_initialized, struct rb_root *cache_root, int npages,
		int p2align, unsigned long lock_offset,
		unsigned long lock_node_addr,
		page_alloc_irq_save_fn_t irq_save_fn,
		page_alloc_irq_restore_fn_t irq_restore_fn,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn,
		page_alloc_alloc_log_fn_t log_fn)
{
	unsigned long addr;
	int source = 0;

	addr = ihk_numa_alloc_pages_orchestrate_result(node, cpu_initialized,
			cache_root, npages, p2align, lock_offset, lock_node_addr,
			irq_save_fn, irq_restore_fn, lock_fn, unlock_fn,
			&source);
	if (log_fn) {
		if (source == 1) {
			log_fn(IHK_NUMA_ALLOC_LOG_CACHE_HIT,
					(unsigned long)node, addr, npages,
					source);
		} else if (addr) {
			log_fn(IHK_NUMA_ALLOC_LOG_DIRECT_OK,
					(unsigned long)node, addr, npages,
					source);
		}
	}

	return addr;
}

int ihk_numa_free_pages_orchestrate_result(
		struct ihk_mc_numa_node *node, unsigned long addr,
		int npages, int defer_zero_at_free,
		struct ikc_scd_packet *packet, int cpu_initialized,
		unsigned long current_thread, unsigned long idle_thread,
		unsigned long thread_proc_offset,
		unsigned long proc_nohost_offset,
		unsigned long proc_pid_offset, int cpu_ref,
		unsigned long syscall_number, unsigned long lock_offset,
		unsigned long lock_node_addr,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn, int *direct_rcp,
		int *zero_request_actionp)
{
	int free_action;
	int rc;
	unsigned long size;

	if (direct_rcp)
		*direct_rcp = 0;
	if (zero_request_actionp)
		*zero_request_actionp = 0;

	if (!node || npages <= 0)
		return IHK_NUMA_FREE_IGNORED;

	size = npages << PAGE_SHIFT;
	if (addr < node->min_addr || addr + size > node->max_addr)
		return IHK_NUMA_FREE_IGNORED;

	if (zero_at_free && !defer_zero_at_free)
		memset(phys_to_virt(addr), 0, size);

	free_action = (!zero_at_free || !defer_zero_at_free) ?
		IHK_NUMA_FREE_DIRECT : IHK_NUMA_FREE_DEFERRED;
	if (free_action == IHK_NUMA_FREE_IGNORED)
		return free_action;

	if (free_action == IHK_NUMA_FREE_DIRECT) {
		if (!node || npages <= 0 || !lock_fn || !unlock_fn) {
			rc = EINVAL;
		} else {
			lock_fn((unsigned long)node + lock_offset,
					lock_node_addr);
			rc = __page_alloc_rbtree_free_range(&node->free_chunks,
					addr, npages << PAGE_SHIFT);
			if (!rc)
				node->nr_free_pages += npages;
			unlock_fn((unsigned long)node + lock_offset,
					lock_node_addr);
		}
		if (direct_rcp)
			*direct_rcp = rc;
		return free_action;
	}

	if (free_action == IHK_NUMA_FREE_DEFERRED) {
		rc = __ihk_numa_free_pages_deferred_result(node, addr, npages,
				packet, cpu_initialized, current_thread, idle_thread,
				thread_proc_offset, proc_nohost_offset,
				proc_pid_offset, cpu_ref, syscall_number);
		if (zero_request_actionp)
			*zero_request_actionp = rc;
	}

	return free_action;
}

int ihk_numa_free_pages_finish_result(int free_action, int direct_rc,
		int zero_request_action, unsigned long node_addr,
		unsigned long addr, int npages, int zero_at_free_value,
		unsigned long packet_addr, page_alloc_zero_send_fn_t send_fn,
		page_alloc_free_log_fn_t log_fn)
{
	int send_rc;

	if (free_action == IHK_NUMA_FREE_IGNORED)
		return 0;

	if (free_action == IHK_NUMA_FREE_DIRECT) {
		if (direct_rc) {
			if (log_fn) {
				log_fn(IHK_NUMA_FREE_LOG_DIRECT_ERROR,
						node_addr, addr, npages,
						zero_at_free_value, direct_rc);
			}
		}
		else if (log_fn) {
			log_fn(IHK_NUMA_FREE_LOG_DIRECT_OK, node_addr, addr,
					npages, zero_at_free_value, 0);
		}
		return 0;
	}

	if (free_action == IHK_NUMA_FREE_DEFERRED) {
		if (zero_request_action < 0) {
			if (log_fn) {
				log_fn(IHK_NUMA_FREE_LOG_DEFER_ERROR,
						node_addr, addr, npages,
						zero_at_free_value,
						zero_request_action);
			}
			return 0;
		}
		if (zero_request_action == 2) {
			if (log_fn) {
				log_fn(IHK_NUMA_FREE_LOG_ZERO_SKIP,
						node_addr, addr, npages,
						zero_at_free_value,
						zero_request_action);
			}
			return 0;
		}
		if (zero_request_action == 1) {
			if (!send_fn)
				send_rc = -EINVAL;
			else
				send_rc = send_fn(packet_addr);
			if (log_fn) {
				log_fn(send_rc < 0 ? IHK_NUMA_FREE_LOG_SEND_FAIL :
						IHK_NUMA_FREE_LOG_SEND_OK,
						node_addr, addr, npages,
						zero_at_free_value, send_rc);
			}
		}
		return 0;
	}

	if (log_fn) {
		log_fn(IHK_NUMA_FREE_LOG_UNEXPECTED, node_addr, addr, npages,
				zero_at_free_value, free_action);
	}
	return 0;
}

int ihk_numa_free_pages_result(struct ihk_mc_numa_node *node,
		unsigned long addr, int npages, int defer_zero_at_free_value,
		int zero_at_free_value, struct ikc_scd_packet *packet,
		int cpu_initialized, struct rb_root *cache_root,
		unsigned long current_thread, unsigned long idle_thread,
		unsigned long thread_proc_offset,
		unsigned long proc_nohost_offset,
		unsigned long proc_pid_offset, int cpu_ref,
		unsigned long syscall_number, unsigned long lock_offset,
		unsigned long lock_node_addr,
		page_alloc_irq_save_fn_t irq_save_fn,
		page_alloc_irq_restore_fn_t irq_restore_fn,
		page_alloc_mcs_lock_fn_t lock_fn,
		page_alloc_mcs_unlock_fn_t unlock_fn,
		page_alloc_zero_send_fn_t send_fn,
		page_alloc_free_log_fn_t log_fn)
{
	int cache_action;
	int free_action;
	int direct_rc = 0;
	int zero_request_action = 0;

	cache_action = __ihk_numa_cpu_cache_free_try_result(cpu_initialized,
			cache_root, addr, npages, irq_save_fn, irq_restore_fn);
	if (cache_action == IHK_NUMA_CPU_CACHE_FREE_SUCCESS) {
		if (log_fn) {
			log_fn(IHK_NUMA_FREE_LOG_CPU_CACHE_OK,
					(unsigned long)node, addr, npages,
					zero_at_free_value, 0);
		}
		return 0;
	}
	if (cache_action == IHK_NUMA_CPU_CACHE_FREE_FAILED && log_fn) {
		log_fn(IHK_NUMA_FREE_LOG_CPU_CACHE_FAILED,
				(unsigned long)node, addr, npages,
				zero_at_free_value, cache_action);
	}

	free_action = ihk_numa_free_pages_orchestrate_result(node, addr,
			npages, defer_zero_at_free_value, packet, cpu_initialized,
			current_thread, idle_thread, thread_proc_offset,
			proc_nohost_offset, proc_pid_offset, cpu_ref,
			syscall_number, lock_offset, lock_node_addr, lock_fn,
			unlock_fn, &direct_rc, &zero_request_action);
	return ihk_numa_free_pages_finish_result(free_action, direct_rc,
			zero_request_action, (unsigned long)node, addr, npages,
			zero_at_free_value, (unsigned long)packet, send_fn,
			log_fn);
}

#ifdef ENABLE_FUGAKU_HACKS
size_t __count_free_bytes(struct rb_root *root)
{
	struct free_chunk *chunk;
	struct rb_node *node;
	size_t size = 0;

	for (node = rb_first(root); node; node = rb_next(node)) {
		chunk = ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));

		size += chunk->size;
	}

	return size;
}
#endif

/*
 * Free pages.
 * NOTE: locking must be managed by the caller.
 */
static int __page_alloc_rbtree_free_range(struct rb_root *root,
		unsigned long addr, unsigned long size)
{
	struct rb_node **iter = &(root->rb_node), *parent = NULL;
	struct free_chunk *new_chunk;

	/* Figure out where to put new node */
	while (*iter) {
		struct free_chunk *ichunk = ((struct free_chunk *)((char *)(*iter) - offsetof(struct free_chunk, node)));
		parent = *iter;

		if ((addr >= ichunk->addr) && (addr < ichunk->addr + ichunk->size)) {
			kprintf("%s: ERROR: free memory chunk: 0x%lx:%lu"
					" and requested range to be freed: 0x%lx:%lu are "
					"overlapping (double-free?)\n",
					__FUNCTION__,
					ichunk->addr, ichunk->size, addr, size);
			return EINVAL;
		}

		/* Is ichunk contigous from the left? */
		if (ichunk->addr + ichunk->size == addr) {
			struct rb_node *right;

			/* Extend it to the right */
			ichunk->size += size;
			dkprintf("%s: chunk extended to right: 0x%lx:%lu\n",
					__FUNCTION__, ichunk->addr, ichunk->size);

			/* Have the right chunk of ichunk and ichunk become contigous? */
			right = rb_next(*iter);
			if (right) {
				struct free_chunk *right_chunk =
					((struct free_chunk *)((char *)(right) - offsetof(struct free_chunk, node)));

				if (ichunk->addr + ichunk->size == right_chunk->addr) {
					ichunk->size += right_chunk->size;
					rb_erase(right, root);

					/* Clear old structure */
					memset(right_chunk, 0, sizeof(*right_chunk));

					dkprintf("%s: chunk merged to right: 0x%lx:%lu\n",
							__FUNCTION__, ichunk->addr, ichunk->size);
				}
			}

			return 0;
		}

		/* Is ichunk contigous from the right? */
		if (addr + size == ichunk->addr) {
			struct rb_node *left;

			/* Extend it to the left */
			ichunk->addr -= size;
			ichunk->size += size;
			dkprintf("%s: chunk extended to left: 0x%lx:%lu\n",
					__FUNCTION__, ichunk->addr, ichunk->size);

			/* Have the left chunk of ichunk and ichunk become contigous? */
			left = rb_prev(*iter);
			if (left) {
				struct free_chunk *left_chunk =
					((struct free_chunk *)((char *)(left) - offsetof(struct free_chunk, node)));

				if (left_chunk->addr + left_chunk->size == ichunk->addr) {
					ichunk->addr -= left_chunk->size;
					ichunk->size += left_chunk->size;
					rb_erase(left, root);

					/* Clear old structure */
					memset(left_chunk, 0, sizeof(*left_chunk));

					dkprintf("%s: chunk merged to left: 0x%lx:%lu\n",
							__FUNCTION__, ichunk->addr, ichunk->size);
				}
			}

			/* Move chunk structure to the front */
			new_chunk = (struct free_chunk *)phys_to_virt(ichunk->addr);
			*new_chunk = *ichunk;
			rb_replace_node(&ichunk->node, &new_chunk->node, root);

			/* Clear old structure */
			memset(ichunk, 0, sizeof(*ichunk));

			dkprintf("%s: chunk moved to front: 0x%lx:%lu\n",
					__FUNCTION__, new_chunk->addr, new_chunk->size);

			return 0;
		}

		if (addr < ichunk->addr)
			iter = &((*iter)->rb_left);
		else
			iter = &((*iter)->rb_right);
	}

	new_chunk = (struct free_chunk *)phys_to_virt(addr);
	new_chunk->addr = addr;
	new_chunk->size = size;
	dkprintf("%s: new chunk: 0x%lx:%lu\n",
		__FUNCTION__, new_chunk->addr, new_chunk->size);

	/* Add new node and rebalance tree. */
	rb_link_node(&new_chunk->node, parent, iter);
	rb_insert_color(&new_chunk->node, root);

	return 0;
}

/*
 * Mark address range as used (i.e., allocated).
 *
 * chunk is the free memory chunk in which
 * [aligned_addr, aligned_addr + size] resides.
 *
 * NOTE: locking must be managed by the caller.
 */
static int __page_alloc_rbtree_mark_range_allocated(struct rb_root *root,
		struct free_chunk *chunk,
		unsigned long aligned_addr, unsigned long size)
{
	struct free_chunk *left_chunk = NULL, *right_chunk = NULL;

	/* Is there leftover on the right? */
	if ((aligned_addr + size) < (chunk->addr + chunk->size)) {
		right_chunk = (struct free_chunk *)phys_to_virt(aligned_addr + size);
		right_chunk->addr = aligned_addr + size;
		right_chunk->size = (chunk->addr + chunk->size) - (aligned_addr + size);
	}

	/* Is there leftover on the left? */
	if (aligned_addr != chunk->addr) {
		left_chunk = chunk;
	}

	/* Update chunk's size, possibly becomes zero */
	chunk->size = (aligned_addr - chunk->addr);

	if (left_chunk) {
		/* Left chunk reuses chunk, add right chunk */
		if (right_chunk) {
			dkprintf("%s: adding right chunk: 0x%lx:%lu\n",
					__FUNCTION__, right_chunk->addr, right_chunk->size);
			if (__page_alloc_rbtree_free_range(root,
					right_chunk->addr, right_chunk->size)) {
				kprintf("%s: ERROR: adding right chunk: 0x%lx:%lu\n",
						__FUNCTION__, right_chunk->addr, right_chunk->size);
				return EINVAL;
			}
		}
	}
	else {
		/* Replace left with right */
		if (right_chunk) {
			rb_replace_node(&chunk->node, &right_chunk->node, root);
			dkprintf("%s: chunk replaced with right: 0x%lx:%lu\n",
					__FUNCTION__, right_chunk->addr, right_chunk->size);
		}
		/* No left chunk and no right chunk => chunk was exact match, delete it */
		else {
			rb_erase(&chunk->node, root);
			dkprintf("%s: chunk deleted: 0x%lx:%lu\n",
					__FUNCTION__, chunk->addr, chunk->size);
		}
	}

	return 0;
}

/*
 * Allocate pages.
 *
 * NOTE: locking must be managed by the caller.
 */
struct chunk_fits_arg {
	unsigned long size;
	unsigned long align_size;
	unsigned long align_mask;
};

bool chunk_fits(struct rb_node *node, void *arg)
{
	struct free_chunk *chunk;
	unsigned long aligned_addr = 0;
	struct chunk_fits_arg *cfa = (struct chunk_fits_arg *)arg;

	chunk = ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));
	aligned_addr = (chunk->addr + (cfa->align_size - 1)) & cfa->align_mask;

	/* Is this a suitable chunk? */
	if ((aligned_addr + cfa->size) <= (chunk->addr + chunk->size)) {
		return true;
	}

	return false;
}


static unsigned long __page_alloc_rbtree_alloc_pages(struct rb_root *root,
		int npages, int p2align)
{
	struct free_chunk *chunk;
	struct rb_node *node;
	unsigned long size = PAGE_SIZE * npages;
	unsigned long align_size = (PAGE_SIZE << p2align);
	unsigned long align_mask = ~(align_size - 1);
	unsigned long aligned_addr = 0;

#if 0
	struct chunk_fits_arg cfa = {
		.size = size,
		.align_size = align_size,
		.align_mask = align_mask
	};

	/* Find first maching chunk */
	node = rb_preorder_dfs_search(root, chunk_fits, &cfa);

	chunk = ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));
	aligned_addr = (chunk->addr + (align_size - 1)) & align_mask;
#else
	for (node = rb_first(root); node; node = rb_next(node)) {
		chunk = ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));
		aligned_addr = (chunk->addr + (align_size - 1)) & align_mask;

		/* Is this a suitable chunk? */
		if ((aligned_addr + size) <= (chunk->addr + chunk->size)) {
			break;
		}
	}

	/* No matching chunk at all? */
	if (!node) {
		return 0;
	}
#endif

	dkprintf("%s: allocating: 0x%lx:%lu\n",
			__FUNCTION__, aligned_addr, size);
	if (__page_alloc_rbtree_mark_range_allocated(root, chunk,
			aligned_addr, size)) {
		kprintf("%s: ERROR: allocating 0x%lx:%lu\n",
			__FUNCTION__, aligned_addr, size);
		return 0;
	}

	if (zero_at_free) {
		memset(phys_to_virt(aligned_addr),
				0, sizeof(struct free_chunk));
	}

	return aligned_addr;
}

/*
 * Reserve pages.
 *
 * NOTE: locking must be managed by the caller.
 */
static unsigned long __page_alloc_rbtree_reserve_pages(struct rb_root *root,
		unsigned long aligned_addr, int npages)
{
	struct free_chunk *chunk;
	struct rb_node *node;
	unsigned long size = PAGE_SIZE * npages;

	for (node = rb_first(root); node; node = rb_next(node)) {
		chunk = ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));

		/* Is this the containing chunk? */
		if (aligned_addr >= chunk->addr &&
				(aligned_addr + size) <= (chunk->addr + chunk->size)) {
			break;
		}
	}

	/* No matching chunk at all? */
	if (!node) {
		kprintf("%s: WARNING: attempted to reserve non-free"
				" physical range: 0x%lx:%lu\n",
				__FUNCTION__,
				aligned_addr, size);
		return 0;
	}

	dkprintf("%s: reserving: 0x%lx:%lu\n",
			__FUNCTION__, aligned_addr, size);
	if (__page_alloc_rbtree_mark_range_allocated(root, chunk,
			aligned_addr, size)) {
		kprintf("%s: ERROR: reserving 0x%lx:%lu\n",
			__FUNCTION__, aligned_addr, size);
		return 0;
	}

	return aligned_addr;
}

static struct free_chunk *__page_alloc_rbtree_get_root_chunk(
	struct rb_root *root)
{
	struct rb_node *node = root->rb_node;
	if (!node) {
		return NULL;
	}

	rb_erase(node, root);
	return ((struct free_chunk *)((char *)(node) - offsetof(struct free_chunk, node)));
}
#endif /* MCKERNEL_RUST_PAGE_ALLOC_RBTREE */

/*
 * External routines.
 */
static void page_alloc_add_free_log_bridge(int event, unsigned long node_addr,
		unsigned long addr, unsigned long size, int rc)
{
	(void)node_addr;

	switch (event) {
	case IHK_NUMA_ADD_FREE_LOG_ERROR:
		kprintf("%s: ERROR: adding 0x%lx:%lu\n",
				"ihk_numa_add_free_pages", addr, size);
		break;
	case IHK_NUMA_ADD_FREE_LOG_OK:
		(void)rc;
		dkprintf("%s: added free pages 0x%lx:%lu\n",
				"ihk_numa_add_free_pages", addr, size);
		break;
	}
}

int ihk_numa_add_free_pages(struct ihk_mc_numa_node *node,
		unsigned long addr, unsigned long size)
{
	return ihk_numa_add_free_pages_result(node, addr, size,
			page_alloc_add_free_log_bridge);
}

#define IHK_NUMA_ALL_PAGES	(0)

int __ihk_numa_zero_free_pages(struct ihk_mc_numa_node *__node, int nr_pages)
{
#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
	return __ihk_numa_zero_free_pages_dispatch(__node, nr_pages);
#else
	int i, max_i;
	int nr_zeroed_pages = 0;

	if (!zero_at_free)
		return 0;

	/* If explicitly specified, zero only in __node */
	max_i = __node ? 1 : ihk_mc_get_nr_numa_nodes();

	/* Look at NUMA nodes in the order of distance */
	for (i = 0; i < max_i; ++i) {
		struct ihk_mc_numa_node *node;
		struct llist_node *llnode;

		/* Unless explicitly specified.. */
		node = __node ? __node : ihk_mc_get_numa_node_by_distance(i);
		if (!node) {
			break;
		}

		/*
		 * If number of pages specified, look for a big enough chunk
		 */
		if (nr_pages) {
			struct llist_head tmp;

			init_llist_head(&tmp);

			/* Look for a suitable chunk */
			while ((llnode = llist_del_first(&node->to_zero_list))) {
				unsigned long addr;
				unsigned long size;
				struct free_chunk *chunk =
					((struct free_chunk *)((char *)(llnode) - offsetof(struct free_chunk, list)));

				addr = chunk->addr;
				size = chunk->size;

				if (size < (nr_pages << PAGE_SHIFT)) {
					llist_add(llnode, &tmp);
					continue;
				}

				memset(phys_to_virt(addr) + sizeof(*chunk), 0,
						size - sizeof(*chunk));
				llist_add(&chunk->list, &node->zeroed_list);
				barrier();
				ihk_atomic_sub((int)(size >> PAGE_SHIFT),
						&node->nr_to_zero_pages);
				nr_zeroed_pages += (chunk->size >> PAGE_SHIFT);
				kprintf("%s: zeroed chunk 0x%lx:%lu in allocate path\n",
						__func__, addr, size);
				break;
			}

			/* Add back the ones that didn't match */
			while ((llnode = llist_del_first(&tmp))) {
				llist_add(llnode, &node->to_zero_list);
			}
		}
		/* Otherwise iterate all to_zero chunks */
		else {
			while ((llnode = llist_del_first(&node->to_zero_list))) {
				unsigned long addr;
				unsigned long size;
				struct free_chunk *chunk =
					((struct free_chunk *)((char *)(llnode) - offsetof(struct free_chunk, list)));

				addr = chunk->addr;
				size = chunk->size;

				memset(phys_to_virt(addr) + sizeof(*chunk), 0,
						size - sizeof(*chunk));
				llist_add(&chunk->list, &node->zeroed_list);
				barrier();
				ihk_atomic_sub((int)(size >> PAGE_SHIFT),
						&node->nr_to_zero_pages);
				nr_zeroed_pages += (chunk->size >> PAGE_SHIFT);
			}
		}
	}

	return nr_zeroed_pages;
#endif
}

void ihk_numa_zero_free_pages(struct ihk_mc_numa_node *__node)
{
#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
	ihk_numa_zero_free_pages_result(__node);
#else
	__ihk_numa_zero_free_pages(__node, IHK_NUMA_ALL_PAGES);
#endif
}

static void page_alloc_alloc_log_bridge(int event, unsigned long node_addr,
		unsigned long addr, int npages, int source)
{
	(void)node_addr;
	(void)source;

	switch (event) {
	case IHK_NUMA_ALLOC_LOG_CACHE_HIT:
		dkprintf("%s: 0x%lx:%d allocated from cache\n",
				"ihk_numa_alloc_pages", addr, npages);
		break;
	case IHK_NUMA_ALLOC_LOG_DIRECT_OK:
		dkprintf("%s: allocated pages 0x%lx:%lu\n",
				"ihk_numa_alloc_pages", addr,
				npages << PAGE_SHIFT);
		break;
	}
}

static int page_alloc_zero_send_bridge(unsigned long packet_addr)
{
	struct ihk_ikc_channel_desc *syscall_channel =
		get_this_cpu_local_var()->ikc2linux;

	return ihk_ikc_send(syscall_channel, (void *)packet_addr, 0);
}

static void page_alloc_free_log_bridge(int event, unsigned long node_addr,
		unsigned long addr, int npages, int zero_at_free_value,
		int detail)
{
	struct ihk_mc_numa_node *node = (struct ihk_mc_numa_node *)node_addr;
	const char *func = "ihk_numa_free_pages";

	switch (event) {
	case IHK_NUMA_FREE_LOG_DIRECT_ERROR:
		kprintf("%s: ERROR: freeing 0x%lx:%lu\n",
				func, addr, npages << PAGE_SHIFT);
		break;
	case IHK_NUMA_FREE_LOG_DIRECT_OK:
		dkprintf("%s: freed%s chunk 0x%lx:%lu\n",
				func, zero_at_free_value ?
				" and zeroed" : "", addr, npages << PAGE_SHIFT);
		break;
	case IHK_NUMA_FREE_LOG_DEFER_ERROR:
		kprintf("%s: ERROR: deferring free 0x%lx:%lu\n",
				func, addr, npages << PAGE_SHIFT);
		break;
	case IHK_NUMA_FREE_LOG_ZERO_SKIP:
		dkprintf("%s: skipping Linux zero request..\n", func);
		break;
	case IHK_NUMA_FREE_LOG_SEND_FAIL:
		kprintf("%s: WARNING: failed to send memory clear"
				" send IKC req..\n", func);
		break;
	case IHK_NUMA_FREE_LOG_SEND_OK:
		dkprintf("%s: clear mem req for NUMA %d sent in req"
				" for addr: 0x%lx\n",
				func, node ? node->id : -1, addr);
		break;
	case IHK_NUMA_FREE_LOG_UNEXPECTED:
		kprintf("%s: ERROR: unexpected Rust free action %d for 0x%lx:%lu\n",
				func, detail, addr, npages << PAGE_SHIFT);
		break;
	case IHK_NUMA_FREE_LOG_CPU_CACHE_OK:
		dkprintf("%s: 0x%lx:%d freed to cache\n",
				func, addr, npages);
		break;
	case IHK_NUMA_FREE_LOG_CPU_CACHE_FAILED:
		kprintf("%s: ERROR: freeing 0x%lx:%lu to CPU local cache\n",
				func, addr, npages << PAGE_SHIFT);
		break;
	}
}

unsigned long ihk_numa_alloc_pages(struct ihk_mc_numa_node *node,
	int npages, int p2align)
{
	mcs_lock_node_t mcs_node;

#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
	struct rb_root *cache_root = NULL;
	page_alloc_irq_save_fn_t irq_save_fn = NULL;
	page_alloc_irq_restore_fn_t irq_restore_fn = NULL;

#ifdef ENABLE_PER_CPU_ALLOC_CACHE
	if (cpu_local_var_initialized) {
		cache_root = &get_this_cpu_local_var()->free_chunks;
	}
	irq_save_fn = cpu_disable_interrupt_save;
	irq_restore_fn = cpu_restore_interrupt;
#endif
	return ihk_numa_alloc_pages_result(node, cpu_local_var_initialized,
			cache_root, npages, p2align,
			__builtin_offsetof(struct ihk_mc_numa_node, lock),
			(unsigned long)&mcs_node, irq_save_fn, irq_restore_fn,
			page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge,
			page_alloc_alloc_log_bridge);
#else
	unsigned long addr = 0;
#ifdef ENABLE_PER_CPU_ALLOC_CACHE
	/* Check CPU local cache first */
	addr = __ihk_numa_cpu_cache_alloc_try_result(
			cpu_local_var_initialized,
			cpu_local_var_initialized ?
				&get_this_cpu_local_var()->free_chunks : NULL,
			npages, p2align, cpu_disable_interrupt_save,
			cpu_restore_interrupt);
	if (__ihk_numa_cpu_cache_alloc_hit_result(addr)) {
		dkprintf("%s: 0x%lx:%d allocated from cache\n",
			__func__, addr, npages);
		return addr;
	}
#endif

	mcs_lock_lock(&node->lock, &mcs_node);
retry:
	if (zero_at_free) {
		struct llist_node *llnode;

		/*
		 * Process zeroed chunks that are not
		 * on the free tree yet.
		 */
		while ((llnode = llist_del_first(&node->zeroed_list))) {
			unsigned long addr;
			unsigned long size;
			struct free_chunk *chunk =
				((struct free_chunk *)((char *)(llnode) - offsetof(struct free_chunk, list)));

			addr = chunk->addr;
			size = chunk->size;

			if (__page_alloc_rbtree_free_range(&node->free_chunks,
						addr, size)) {
				kprintf("%s: ERROR: freeing zeroed chunk 0x%lx:%lu\n",
						__FUNCTION__, addr, npages << PAGE_SHIFT);
			}
			else {
				node->nr_free_pages += (size >> PAGE_SHIFT);
				dkprintf("%s: freed zeroed chunk 0x%lx:%lu\n",
						__FUNCTION__, addr, size);
			}
		}

		/* Not enough? Check if we can zero pages now */
		if (node->nr_free_pages < npages) {
			if (__ihk_numa_zero_free_pages(node, npages) >= npages) {
				goto retry;
			}
		}
	}

	/* Not enough pages? Give up.. */
	if (node->nr_free_pages < npages) {
		goto unlock_out;
	}

	addr = __page_alloc_rbtree_alloc_pages(&node->free_chunks,
			npages, p2align);

	/* Does not necessarily succeed due to alignment */
	if (addr) {
		node->nr_free_pages -= npages;
#if 0
		{
			size_t free_bytes = __count_free_bytes(&node->free_chunks);
			if (free_bytes != node->nr_free_pages * PAGE_SIZE) {
				kprintf("%s: inconsistent free count? node: %lu vs. cnt: %lu\n",
						__func__, node->nr_free_pages * PAGE_SIZE, free_bytes);
				panic("");
			}
		}
#endif
		dkprintf("%s: allocated pages 0x%lx:%lu\n",
				__FUNCTION__, addr, npages << PAGE_SHIFT);
	}

unlock_out:
	mcs_lock_unlock(&node->lock, &mcs_node);

	return addr;
#endif
}

void ihk_numa_free_pages(struct ihk_mc_numa_node *node,
	unsigned long addr, int npages)
{
	mcs_lock_node_t mcs_node;
	int defer_zero_at_free = deferred_zero_at_free;
#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
	struct thread *current_thread = NULL;
	struct thread *idle_thread = NULL;
	struct ikc_scd_packet packet IHK_DMA_ALIGN;
	struct rb_root *cache_root = NULL;
	page_alloc_irq_save_fn_t irq_save_fn = NULL;
	page_alloc_irq_restore_fn_t irq_restore_fn = NULL;
#ifdef ENABLE_PER_CPU_ALLOC_CACHE
	if (cpu_local_var_initialized) {
		cache_root = &get_this_cpu_local_var()->free_chunks;
	}
	irq_save_fn = cpu_disable_interrupt_save;
	irq_restore_fn = cpu_restore_interrupt;
#endif
	if (cpu_local_var_initialized) {
		current_thread = get_this_cpu_local_var()->current;
		idle_thread = &get_this_cpu_local_var()->idle;
	}

	ihk_numa_free_pages_result(node, addr, npages, defer_zero_at_free,
			zero_at_free, &packet, cpu_local_var_initialized,
			cache_root, (unsigned long)current_thread,
			(unsigned long)idle_thread,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, nohost),
			__builtin_offsetof(struct process, pid),
			ihk_mc_get_processor_id(), __NR_move_pages,
			__builtin_offsetof(struct ihk_mc_numa_node, lock),
			(unsigned long)&mcs_node, irq_save_fn, irq_restore_fn,
			page_alloc_mcs_lock_bridge,
			page_alloc_mcs_unlock_bridge,
			page_alloc_zero_send_bridge,
			page_alloc_free_log_bridge);
	return;
#else
#ifdef ENABLE_PER_CPU_ALLOC_CACHE
	/* CPU local cache */
	{
		int cache_action = __ihk_numa_cpu_cache_free_try_result(
				cpu_local_var_initialized,
				cpu_local_var_initialized ?
					&get_this_cpu_local_var()->free_chunks : NULL,
				addr, npages, cpu_disable_interrupt_save,
				cpu_restore_interrupt);

		if (cache_action == IHK_NUMA_CPU_CACHE_FREE_SUCCESS) {
			dkprintf("%s: 0x%lx:%d freed to cache\n",
				__func__, addr, npages);
			return;
		}
		if (cache_action == IHK_NUMA_CPU_CACHE_FREE_FAILED) {
			kprintf("%s: ERROR: freeing 0x%lx:%lu to CPU local cache\n",
					__FUNCTION__, addr, npages << PAGE_SHIFT);
		}
	}
#endif
	if (addr < node->min_addr ||
			(addr + (npages << PAGE_SHIFT)) > node->max_addr) {
		return;
	}

	if (npages <= 0) {
		return;
	}

#if 0
	/* Do not defer zeroing when the number of free pages is low */
	if (zero_at_free && defer_zero_at_free) {
		mcs_lock_lock(&node->lock, &mcs_node);
		if (node->nr_free_pages < (node->nr_pages * 3 / 100))
			defer_zero_at_free = 0;
		mcs_lock_unlock(&node->lock, &mcs_node);
	}
#endif


	/* Zero chunk right here if needed */
	if (zero_at_free && !defer_zero_at_free) {
		memset(phys_to_virt(addr), 0, npages << PAGE_SHIFT);
	}

	/*
	 * If we don't zero at free() or we zeroed the chunk
	 * already, simply add it to the free tree.
	 */
	if (!zero_at_free ||
			(zero_at_free && !defer_zero_at_free)) {
		mcs_lock_lock(&node->lock, &mcs_node);

#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
		if (__ihk_numa_free_pages_to_tree_nolock(node, addr, npages)) {
			kprintf("%s: ERROR: freeing 0x%lx:%lu\n",
					__FUNCTION__, addr, npages << PAGE_SHIFT);
		}
		else {
			dkprintf("%s: freed%s chunk 0x%lx:%lu\n",
					__FUNCTION__,
					zero_at_free ? " and zeroed" : "",
					addr, npages << PAGE_SHIFT);
		}
#else
		if (__page_alloc_rbtree_free_range(&node->free_chunks, addr,
					npages << PAGE_SHIFT)) {
			kprintf("%s: ERROR: freeing 0x%lx:%lu\n",
					__FUNCTION__, addr, npages << PAGE_SHIFT);
		}
		else {
			node->nr_free_pages += npages;
#if 0
			{
				size_t free_bytes = __count_free_bytes(&node->free_chunks);
				if (free_bytes != node->nr_free_pages * PAGE_SIZE) {
					kprintf("%s: inconsistent free count? node: %lu vs. cnt: %lu\n",
							__func__, node->nr_free_pages * PAGE_SIZE, free_bytes);
					panic("");
				}
			}
#endif
			dkprintf("%s: freed%s chunk 0x%lx:%lu\n",
					__FUNCTION__,
					zero_at_free ? " and zeroed" : "",
					addr, npages << PAGE_SHIFT);
		}
#endif
		mcs_lock_unlock(&node->lock, &mcs_node);
	}
	/*
	 * Deferred zeroing.
	 * Put the chunk to the to_zero list.
	 */
	else {
#ifdef MCKERNEL_RUST_PAGE_ALLOC_RBTREE
		if (__ihk_numa_defer_zero_free_pages(node, addr, npages)) {
			kprintf("%s: ERROR: deferring free 0x%lx:%lu\n",
					__FUNCTION__, addr, npages << PAGE_SHIFT);
			return;
		}
#else
		struct free_chunk *chunk =
			(struct free_chunk *)phys_to_virt(addr);
		chunk->addr = addr;
		chunk->size = npages << PAGE_SHIFT;
		ihk_atomic_add(npages, &node->nr_to_zero_pages);
		barrier();
		llist_add(&chunk->list, &node->to_zero_list);
#endif

		/* Ask Linux to clear memory */
		if (cpu_local_var_initialized &&
				get_this_cpu_local_var()->current &&
				get_this_cpu_local_var()->current != &get_this_cpu_local_var()->idle &&
				!get_this_cpu_local_var()->current->proc->nohost) {
			struct ihk_ikc_channel_desc *syscall_channel =
				get_this_cpu_local_var()->ikc2linux;
			struct ikc_scd_packet packet IHK_DMA_ALIGN;

			if (ihk_atomic_read(&node->zeroing_workers) > 0) {
				dkprintf("%s: skipping Linux zero request..\n", __func__);
				return;
			}

			ihk_atomic_inc(&node->zeroing_workers);

			__ihk_numa_zero_request_packet_fill(&packet,
					(unsigned long)node,
					ihk_mc_get_processor_id(),
					get_this_cpu_local_var()->current->proc->pid,
					__NR_move_pages);

			if (ihk_ikc_send(syscall_channel, &packet, 0) < 0) {
				kprintf("%s: WARNING: failed to send memory clear"
						" send IKC req..\n", __func__);
			}
			else {
				dkprintf("%s: clear mem req for NUMA %d sent in req"
						" for addr: 0x%lx\n",
						__func__, node->id, addr);
			}
		}
	}
#endif
}

#endif // IHK_RBTREE_ALLOCATOR
