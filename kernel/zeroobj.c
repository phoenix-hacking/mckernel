/**
 * \file zeroobj.c
 *  License details are found in the file LICENSE.
 * \brief
 *  read-only zeroed page object
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2014  RIKEN AICS
 */
/*
 * HISTORY:
 */

#include <ihk/atomic.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <errno.h>
#include <kmalloc.h>
#include <list.h>
#include <memobj.h>
#include <memory.h>
#include <page.h>
#include <string.h>
#include <ihk/debug.h>
#include <object_helpers.h>

struct zeroobj {
	struct memobj		memobj;		/* must be first */
	struct list_head	page_list;
};

static ihk_spinlock_t the_zeroobj_lock = SPIN_LOCK_UNLOCKED;
static struct zeroobj *the_zeroobj = NULL;	/* singleton */

static memobj_get_page_func_t zeroobj_get_page;
static memobj_free_func_t zeroobj_free;
static int alloc_zeroobj(void);

static struct memobj_ops zeroobj_ops = {
	.get_page =	&zeroobj_get_page,
	.free = &zeroobj_free,
};

static struct zeroobj *to_zeroobj(struct memobj *memobj)
{
	return (struct zeroobj *)memobj;
}

static struct memobj *to_memobj(struct zeroobj *zeroobj)
{
	return &zeroobj->memobj;
}

/***********************************************************************
 * page_list
 */
static void page_list_init(struct zeroobj *obj)
{
	INIT_LIST_HEAD(&obj->page_list);
	return;
}

static void page_list_insert(struct zeroobj *obj, struct page *page)
{
	list_add(&page->list, &obj->page_list);
	return;
}

static struct page *page_list_first(struct zeroobj *obj)
{
	if (list_empty(&obj->page_list)) {
		return NULL;
	}

	return ((struct page *)((char *)((&obj->page_list)->next) - offsetof(struct page, list)));
}

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
static void zeroobj_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void zeroobj_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static void *zeroobj_alloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void zeroobj_free_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static void *zeroobj_memset_bridge(void *dst, int value, size_t len)
{
	return memset(dst, value, len);
}

static void zeroobj_init_object_bridge(void *objp, void *ops)
{
	struct zeroobj *obj = objp;

	obj->memobj.ops = ops;
	obj->memobj.flags = zeroobj_initial_flags_result();
	obj->memobj.size = 0;
	ihk_atomic_set(&obj->memobj.refcnt,
		       zeroobj_initial_refcnt_result());
	page_list_init(obj);
}

static void *zeroobj_alloc_pages_bridge(int npages, unsigned long flags)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

static void zeroobj_free_pages_bridge(void *virt, int npages)
{
	_ihk_mc_free_pages(virt, npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

static uintptr_t zeroobj_phys_bridge(void *virt)
{
	return virt_to_phys(virt);
}

static void *zeroobj_page_insert_bridge(uintptr_t phys)
{
	return phys_to_page_insert_hash(phys);
}

static int zeroobj_page_mode_bridge(void *page)
{
	return ((struct page *)page)->mode;
}

static void zeroobj_duplicate_page_bridge(void *pagep)
{
	struct page *page = pagep;

	ekprintf("alloc_zeroobj():"
			"page %p %#lx %d %d %#lx\n",
			page, page_to_phys(page), page->mode,
			page->count, page->offset);
	panic("alloc_zeroobj:dup alloc");
}

static void zeroobj_init_page_bridge(void *pagep)
{
	struct page *page = pagep;

	page->mode = zeroobj_initial_page_mode_result();
	page->offset = zeroobj_initial_page_offset_result();
	ihk_atomic_set(&page->count, 1);
	ihk_atomic64_set(&page->mapped, 0);
}

static void zeroobj_page_list_insert_bridge(void *obj, void *page)
{
	page_list_insert(obj, page);
}

static void zeroobj_publish_bridge(void *obj)
{
	the_zeroobj = obj;
}

static int zeroobj_alloc_singleton_bridge(void)
{
	return alloc_zeroobj();
}

static void *zeroobj_get_singleton_bridge(void)
{
	return the_zeroobj;
}

static void zeroobj_ref_bridge(void *memobj)
{
	memobj_ref(memobj);
}

static void zeroobj_log_bridge(int event, int error, void *obj, void *page,
			       uintptr_t phys)
{
	(void)obj;
	(void)page;
	(void)phys;

	switch (event) {
	case ZEROOBJ_LOG_ALREADY:
		dkprintf("alloc_zeroobj():already. %d\n", error);
		break;
	case ZEROOBJ_LOG_KMALLOC_FAILED:
		ekprintf("alloc_zeroobj():kmalloc failed. %d\n", error);
		break;
	case ZEROOBJ_LOG_ALLOC_PAGES_FAILED:
		ekprintf("alloc_zeroobj():alloc pages failed. %d\n", error);
		break;
	}
}
#endif

/***********************************************************************
 * zeroobj
 */

static void zeroobj_free(struct memobj *obj)
{
	kprintf("trying to free zeroobj, this should never happen\n");
}

static int alloc_zeroobj(void)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	int error;

	dkprintf("alloc_zeroobj()\n");
	error = zeroobj_alloc_body_result(
		the_zeroobj, sizeof(struct zeroobj), &zeroobj_ops,
		&the_zeroobj_lock, zeroobj_log_bridge, zeroobj_lock_bridge,
		zeroobj_unlock_bridge, zeroobj_alloc_bridge,
		zeroobj_free_bridge, zeroobj_memset_bridge,
		zeroobj_init_object_bridge, zeroobj_alloc_pages_bridge,
		zeroobj_free_pages_bridge, zeroobj_phys_bridge,
		zeroobj_page_insert_bridge, zeroobj_page_mode_bridge,
		zeroobj_duplicate_page_bridge, zeroobj_init_page_bridge,
		zeroobj_page_list_insert_bridge, zeroobj_publish_bridge);
	dkprintf("alloc_zeroobj():%d %p\n", error, the_zeroobj);
	return error;
#else
	int error;
	struct zeroobj *obj = NULL;
	void *virt = NULL;
	uintptr_t phys;
	struct page *page;

	dkprintf("alloc_zeroobj()\n");
	ihk_mc_spinlock_lock_noirq(&the_zeroobj_lock);
	if (the_zeroobj) {
		error = 0;
		dkprintf("alloc_zeroobj():already. %d\n", error);
		goto out;
	}

	obj = kmalloc_tracked(sizeof(*obj), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!obj) {
		error = -ENOMEM;
		ekprintf("alloc_zeroobj():kmalloc failed. %d\n", error);
		goto out;
	}

	memset(obj, 0, sizeof(*obj));
	obj->memobj.ops = &zeroobj_ops;
	obj->memobj.flags = zeroobj_initial_flags_result();
	obj->memobj.size = 0;
	ihk_atomic_set(&obj->memobj.refcnt,
			zeroobj_initial_refcnt_result()); // never reaches 0
	page_list_init(obj);

	virt = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);	/* XXX:NYI:large page */
	if (!virt) {
		error = -ENOMEM;
		ekprintf("alloc_zeroobj():alloc pages failed. %d\n", error);
		goto out;
	}
	phys = virt_to_phys(virt);
	page = phys_to_page_insert_hash(phys);

	if (page->mode != PM_NONE) {
		ekprintf("alloc_zeroobj():"
				"page %p %#lx %d %d %#lx\n",
				page, page_to_phys(page), page->mode,
				page->count, page->offset);
		panic("alloc_zeroobj:dup alloc");
	}

	memset(virt, 0, PAGE_SIZE);
	page->mode = zeroobj_initial_page_mode_result();
	page->offset = zeroobj_initial_page_offset_result();
	ihk_atomic_set(&page->count, 1);
	ihk_atomic64_set(&page->mapped, 0);
	page_list_insert(obj, page);
	virt = NULL;

	error = 0;
	the_zeroobj = obj;
	obj = NULL;

out:
	ihk_mc_spinlock_unlock_noirq(&the_zeroobj_lock);
	if (virt) {
		_ihk_mc_free_pages(virt, 1, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	if (obj) {
		kfree_tracked(obj, __FILE__, __LINE__);
	}
	dkprintf("alloc_zeroobj():%d %p\n", error, the_zeroobj);
	return error;
#endif
}

int zeroobj_create(struct memobj **objp)
{
	int error;

	dkprintf("zeroobj_create(%p)\n", objp);
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	error = zeroobj_create_body_result((void **)objp, the_zeroobj,
					   zeroobj_alloc_singleton_bridge,
					   zeroobj_get_singleton_bridge,
					   zeroobj_ref_bridge,
					   zeroobj_log_bridge);
	dkprintf("zeroobj_create(%p):%d %p\n", objp, error,
		 error ? NULL : *objp);
	return error;
#else
	if (!the_zeroobj) {
		error = alloc_zeroobj();
		if (error) {
			goto out;
		}
	}

	error = 0;
	*objp = to_memobj(the_zeroobj);
	memobj_ref(*objp);

out:
	dkprintf("zeroobj_create(%p):%d %p\n", objp, error, *objp);
	return error;
#endif
}

static int zeroobj_get_page(struct memobj *memobj, off_t off, int p2align,
		uintptr_t *physp, unsigned long *pflag, uintptr_t virt_addr)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)memobj;
	(void)off;
	(void)p2align;
	(void)physp;
	(void)pflag;
	(void)virt_addr;
	return zeroobj_get_page_body_result();
#else
	int error;
	struct zeroobj *obj = to_zeroobj(memobj);
	struct page *page;

	/* Don't bother about zero page, page fault handler will
	 * allocate and clear pages */
	return 0;

	dkprintf("zeroobj_get_page(%p,%#lx,%d,%p)\n",
			memobj, off, p2align, physp);
	error = zeroobj_get_page_validate_result(off, p2align, 1);
	if (error == -EINVAL) {
		ekprintf("zeroobj_get_page(%p,%#lx,%d,%p):invalid argument. %d\n",
				memobj, off, p2align, physp, error);
		goto out;
	}
	if (error == -ENOMEM) {		/* XXX:NYI:large pages */
		dkprintf("zeroobj_get_page(%p,%#lx,%d,%p):large page. %d\n",
				memobj, off, p2align, physp, error);
		goto out;
	}

	page = page_list_first(obj);
	error = zeroobj_get_page_validate_result(off, p2align, !!page);
	if (error) {
		ekprintf("zeroobj_get_page(%p,%#lx,%d,%p):page not found. %d\n",
				memobj, off, p2align, physp, error);
		goto out;
	}

	ihk_atomic_inc(&page->count);

	error = 0;
	*physp = page_to_phys(page);

out:
	dkprintf("zeroobj_get_page(%p,%#lx,%d,%p):%d\n",
			memobj, off, p2align, physp, error);
	return error;
#endif
}
