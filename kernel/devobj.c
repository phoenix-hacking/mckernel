/* devobj.c COPYRIGHT FUJITSU LIMITED 2015-2017 */
/**
 * \file devobj.c
 *  License details are found in the file LICENSE.
 * \brief
 *  memory mapped device pager client
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2014  RIKEN AICS
 */
/*
 * HISTORY:
 */

#include <ihk/lock.h>
#include <kmalloc.h>
#include <memobj.h>
#include <page.h>	/* for allocate_pages() */
#include <pager.h>
#include <string.h>
#include <syscall.h>
#include <process.h>
#include <rusage_private.h>
#include <ihk/debug.h>
#include <object_helpers.h>

//#define DEBUG_PRINT_DEVOBJ

#ifdef DEBUG_PRINT_DEVOBJ
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif


struct devobj {
	struct memobj	memobj;		/* must be first */
	long		ref;
	uintptr_t	handle;
	off_t		pfn_pgoff;
	uintptr_t *	pfn_table;
	ihk_spinlock_t  pfn_table_lock;
	size_t		npages;
};

static memobj_free_func_t devobj_free;
static memobj_get_page_func_t devobj_get_page;

static struct memobj_ops devobj_ops = {
	.free =		&devobj_free,
	.get_page =	&devobj_get_page,
};

static struct devobj *to_devobj(struct memobj *memobj)
{
	return (struct devobj *)memobj;
}

static struct memobj *to_memobj(struct devobj *devobj)
{
	return &devobj->memobj;
}

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
static int devobj_unmap_bridge(uintptr_t handle)
{
	ihk_mc_user_context_t ctx;

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_UNMAP);
	ihk_mc_syscall_set_arg1(&ctx, handle);
	ihk_mc_syscall_set_arg2(&ctx, 1);

	return syscall_generic_forwarding(__NR_mmap, &ctx);
}

static void devobj_free_pages_bridge(void *addr, size_t npages)
{
	_ihk_mc_free_pages(addr, npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

static void devobj_free_bridge(void *addr)
{
	kfree_tracked(addr, __FILE__, __LINE__);
}

static void devobj_profile_bridge(void)
{
#ifdef PROFILE_ENABLE
	profile_event_add(PROFILE_page_fault_dev_file, PAGE_SIZE);
#endif
}

static unsigned long devobj_lock_bridge(void *lock)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock);
}

static void devobj_unlock_bridge(void *lock, unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock, irqstate);
}

static uintptr_t devobj_pfn_load_bridge(void *obj, int ix)
{
	return ((struct devobj *)obj)->pfn_table[ix];
}

static int devobj_fetch_pfn_bridge(void *memobj, void *obj, uintptr_t handle,
				   off_t off, int p2align, uintptr_t *pfnp)
{
	ihk_mc_user_context_t ctx;
	(void)memobj;
	(void)obj;
	(void)p2align;

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_PFN);
	ihk_mc_syscall_set_arg1(&ctx, handle);
	ihk_mc_syscall_set_arg2(&ctx, devobj_pfn_request_offset_result(off));
	ihk_mc_syscall_set_arg3(&ctx, virt_to_phys(pfnp));

	return syscall_generic_forwarding(__NR_mmap, &ctx);
}

static int devobj_write_combined_bridge(uintptr_t pfn)
{
	return pfn_is_write_combined(pfn);
}

static uintptr_t devobj_map_memory_bridge(uintptr_t phys, size_t size)
{
	return ihk_mc_map_memory(NULL, phys, size);
}

static void devobj_pfn_store_bridge(void *obj, int ix, uintptr_t pfn)
{
	struct devobj *devobj = obj;

	if (devobj_should_store_pfn_result(devobj->pfn_table[ix])) {
		devobj->pfn_table[ix] = pfn;
	}
}

static void devobj_log_bridge(int event, void *memobj, void *obj, off_t off,
			      off_t pgoff, int p2align, int ix, int error,
			      uintptr_t pfn)
{
	(void)pgoff;
	(void)ix;

	switch (event) {
	case DEVOBJ_LOG_RELEASE_FAILED:
		dkprintf("%s(%p %lx): release failed. %d\n",
			 __func__, obj, pfn, error);
		break;
	case DEVOBJ_LOG_FREE_DONE:
		dkprintf("%s(%p %lx):free\n", __func__, obj, pfn);
		break;
	case DEVOBJ_LOG_OUT_OF_RANGE:
		kprintf("%s: error: out of range: off: %lu, page off: %lu obj->npages: %lu\n",
			"devobj_get_page", off, pgoff,
			((struct devobj *)obj)->npages);
		break;
	case DEVOBJ_LOG_FETCH_FAILED:
		kprintf("devobj_get_page(%p %lx,%lx,%d):PAGER_REQ_PFN failed. %d\n",
			memobj, ((struct devobj *)obj)->handle, off,
			p2align, error);
		break;
	case DEVOBJ_LOG_NOT_PRESENT:
		kprintf("devobj_get_page(%p %lx,%lx,%d):not present. %lx\n",
			memobj, ((struct devobj *)obj)->handle, off,
			p2align, pfn);
		break;
	}
}
#endif

/***********************************************************************
 * devobj
 */
int devobj_create(int fd, size_t len, off_t off, struct memobj **objp, int *maxprotp,
	int prot, int populate_flags)
{
	ihk_mc_user_context_t ctx;
	struct pager_map_result result;	// XXX: assumes contiguous physical
	int error;
	struct devobj *obj  = NULL;
	const size_t npages = devobj_npages_result(len);
	const size_t pfn_npages = devobj_pfn_table_npages_result(npages);

	dkprintf("%s: fd: %d, len: %lu, off: %lu \n", __FUNCTION__, fd, len, off);

	obj = kmalloc_tracked(sizeof(*obj), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!obj) {
		error = -ENOMEM;
		kprintf("%s: error: fd: %d, len: %lu, off: %lu kmalloc failed.\n", 
			__FUNCTION__, fd, len, off);
		goto out;
	}
	memset(obj, 0, sizeof(*obj));

	obj->pfn_table = _ihk_mc_alloc_aligned_pages_node(pfn_npages, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (!obj->pfn_table) {
		error = -ENOMEM;
		kprintf("%s: error: fd: %d, len: %lu, off: %lu allocating PFN failed.\n", 
			__FUNCTION__, fd, len, off);
		goto out;
	}
	memset(obj->pfn_table, 0, devobj_pfn_table_bytes_result(pfn_npages));

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_MAP);
	ihk_mc_syscall_set_arg1(&ctx, fd);
	ihk_mc_syscall_set_arg2(&ctx, len);
	ihk_mc_syscall_set_arg3(&ctx, off);
	ihk_mc_syscall_set_arg4(&ctx, virt_to_phys(&result));
	ihk_mc_syscall_set_arg5(&ctx, prot | populate_flags);

	memset(&result, 0, sizeof(result));

	error = syscall_generic_forwarding(__NR_mmap, &ctx);
	if (error) {
		kprintf("%s: error: fd: %d, len: %lu, off: %lu map failed.\n", 
			__FUNCTION__, fd, len, off);
		goto out;
	}

	dkprintf("%s: fd: %d, len: %lu, off: %lu, handle: %p, maxprot: %x\n", 
		__FUNCTION__, fd, len, off, result.handle, result.maxprot);

	obj->memobj.ops = &devobj_ops;
	obj->memobj.flags = devobj_base_flags_result();
	obj->memobj.size = len;
	ihk_atomic_set(&obj->memobj.refcnt, devobj_initial_refcnt_result());
	obj->handle = result.handle;

	dkprintf("%s: path=%s\n", __FUNCTION__, result.path);
	if (devobj_path_present_result(result.path[0])) {
		obj->memobj.path = kmalloc_tracked(PATH_MAX, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!obj->memobj.path) {
			error = -ENOMEM;
			kprintf("%s: ERROR: Out of memory\n", __FUNCTION__);
			goto out;
		}
		strncpy(obj->memobj.path, result.path, PATH_MAX);
	}

	obj->pfn_pgoff = devobj_pgoff_result(off);
	obj->npages = npages;
	ihk_mc_spinlock_init(&obj->pfn_table_lock);

	error = 0;
	*objp = to_memobj(obj);
	*maxprotp = result.maxprot;

#ifdef ENABLE_FUGAKU_HACKS
	/* Pre-populate device file PFNs for PMIx shared mem */
	if (!strncmp(obj->memobj.path,
				"/var/opt/FJSVtcs/ple/daemonif", 29)) {
		off_t offset;
		uintptr_t phys;
		unsigned long flag;

		for (offset = 0; offset < obj->memobj.size; offset += PAGE_SIZE) {
			if (devobj_get_page(&obj->memobj, offset, PAGE_P2ALIGN,
						&phys, &flag, 0) < 0) {
				kprintf("%s: WARNING: failed to populate offset %lu in %s\n",
						__func__, offset, obj->memobj.path);
			}
		}
		dkprintf("%s: pre-populated PFNs for %s, len: %lu\n",
			__func__, obj->memobj.path, obj->memobj.size);
	}
#endif

	obj = NULL;

out:
	if (obj) {
		if (devobj_pfn_table_present_result((uintptr_t)obj->pfn_table)) {
			_ihk_mc_free_pages(obj->pfn_table, pfn_npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
		}
		kfree_tracked(obj, __FILE__, __LINE__);
	}
	dkprintf("%s: ret: %d, fd: %d, len: %lu, off: %lu, handle: %p, maxprot: %x \n", 
		__FUNCTION__, error, fd, len, off, result.handle, result.maxprot);
	return error;
}

static void devobj_free(struct memobj *memobj)
{
	struct devobj *obj = to_devobj(memobj);
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	dkprintf("%s(%p %lx)\n", __func__, obj, obj->handle);
	(void)devobj_free_body_result(
		obj, to_memobj(obj)->path, obj->pfn_table, obj->handle,
		obj->npages, devobj_unmap_bridge, devobj_free_pages_bridge,
		devobj_free_bridge, devobj_log_bridge);
	return;
#else
	uintptr_t handle;
	const size_t pfn_npages = devobj_pfn_table_npages_result(obj->npages);
	int error;
	ihk_mc_user_context_t ctx;

	dkprintf("%s(%p %lx)\n", __func__, obj, obj->handle);

	handle = obj->handle;

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_UNMAP);
	ihk_mc_syscall_set_arg1(&ctx, handle);
	ihk_mc_syscall_set_arg2(&ctx, 1);

	error = syscall_generic_forwarding(__NR_mmap, &ctx);
	if (error) {
		dkprintf("%s(%p %lx): release failed. %d\n",
			__func__, obj, handle, error);
		/* through */
	}

	if (devobj_pfn_table_present_result((uintptr_t)obj->pfn_table)) {
		// Don't call memory_stat_rss_sub() because devobj related
		// pages don't reside in main memory
		_ihk_mc_free_pages(obj->pfn_table, pfn_npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}

	if (devobj_path_present_result((uintptr_t)to_memobj(obj)->path)) {
		kfree_tracked(to_memobj(obj)->path, __FILE__, __LINE__);
	}

	kfree_tracked(obj, __FILE__, __LINE__);

	dkprintf("%s(%p %lx):free\n", __func__, obj, handle);
	return;
#endif
}

static int devobj_get_page(struct memobj *memobj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag, uintptr_t virt_addr)
{
	struct devobj *obj = to_devobj(memobj);
#if defined(MCKERNEL_RUST_OBJECT_HELPERS) && !defined(ENABLE_FUGAKU_HACKS)
	(void)virt_addr;
	dkprintf("devobj_get_page(%p %lx,%lx,%d)\n",
		 memobj, obj->handle, off, p2align);
	return devobj_get_page_body_result(
		memobj, obj, obj->handle, off, p2align, obj->pfn_pgoff,
		obj->npages, &obj->pfn_table_lock, physp, flag,
		devobj_profile_bridge, devobj_lock_bridge,
		devobj_unlock_bridge, devobj_pfn_load_bridge,
		devobj_fetch_pfn_bridge, devobj_write_combined_bridge,
		devobj_map_memory_bridge, devobj_pfn_store_bridge,
		devobj_log_bridge);
#else
	const off_t pgoff = devobj_pgoff_result(off);
	int error;
	uintptr_t pfn;
	uintptr_t attr;
	ihk_mc_user_context_t ctx;
	int ix;
	unsigned long irqstate;
#ifdef ENABLE_FUGAKU_HACKS
	int page_fault_attempts = 5;
#endif

	dkprintf("devobj_get_page(%p %lx,%lx,%d)\n", memobj, obj->handle, off, p2align);

	error = devobj_get_page_index_result(pgoff, obj->pfn_pgoff,
			obj->npages, &ix);
	if (error) {
		kprintf("%s: error: out of range: off: %lu, page off: %lu obj->npages: %d\n", __FUNCTION__, off, pgoff, obj->npages);
		goto out;
	}
	dkprintf("ix: %ld\n", ix);

#ifdef PROFILE_ENABLE
	profile_event_add(PROFILE_page_fault_dev_file, PAGE_SIZE);
#endif // PROFILE_ENABLE

	irqstate = ihk_mc_spinlock_lock(&obj->pfn_table_lock);
	pfn = obj->pfn_table[ix];
	ihk_mc_spinlock_unlock(&obj->pfn_table_lock, irqstate);

	if (devobj_cached_pfn_needs_fetch_result(pfn)) {
#ifdef ENABLE_FUGAKU_HACKS
pf_retry:
#endif
		ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_PFN);
		ihk_mc_syscall_set_arg1(&ctx, obj->handle);
		ihk_mc_syscall_set_arg2(&ctx, devobj_pfn_request_offset_result(off));
		ihk_mc_syscall_set_arg3(&ctx, virt_to_phys(&pfn));

		error = syscall_generic_forwarding(__NR_mmap, &ctx);
		if (error) {
			kprintf("devobj_get_page(%p %lx,%lx,%d):PAGER_REQ_PFN failed. %d\n", memobj, obj->handle, off, p2align, error);
			goto out;
		}

		if (devobj_pfn_present_result(pfn)) {
			/* convert remote physical into local physical */
			dkprintf("devobj_get_page(%p %lx,%lx,%d):PFN_PRESENT before %#lx\n", memobj, obj->handle, off, p2align, pfn);
			attr = devobj_pfn_attr_result(pfn);

			if (pfn_is_write_combined(pfn)) {
				*flag |= VR_WRITE_COMBINED;
			}

			pfn = ihk_mc_map_memory(NULL,
					devobj_pfn_phys_result(pfn),
					devobj_map_size_result());
			pfn = devobj_mapped_pfn_result(pfn, attr);
			dkprintf("devobj_get_page(%p %lx,%lx,%d):PFN_PRESENT after %#lx\n", memobj, obj->handle, off, p2align, pfn);
		}
#ifdef ENABLE_FUGAKU_HACKS
		else if (page_fault_attempts > 0) {
			kprintf("%s(): va: 0x%lx !PFN_PRESENT for offset %lu in %s, "
					"page_fault_attempts: %d\n",
					__func__, virt_addr, off,
					memobj->path ? memobj->path : "<unknown>",
					page_fault_attempts);
			--page_fault_attempts;
			goto pf_retry;
		}
#endif

		/* Update atomically if unset */
		irqstate = ihk_mc_spinlock_lock(&obj->pfn_table_lock);
		if (devobj_should_store_pfn_result(obj->pfn_table[ix])) {
			obj->pfn_table[ix] = pfn;
		}
		ihk_mc_spinlock_unlock(&obj->pfn_table_lock, irqstate);
		// Don't call memory_stat_rss_add() because devobj related pages don't reside in main memory
	}

	error = devobj_pfn_absent_error_result(pfn);
	if (error) {
		kprintf("devobj_get_page(%p %lx,%lx,%d):not present. %lx\n", memobj, obj->handle, off, p2align, pfn);
		goto out;
	}

	error = 0;
	*physp = devobj_pfn_phys_result(pfn);

out:
	dkprintf("devobj_get_page(%p %lx,%lx,%d): %d %lx\n", memobj, obj->handle, off, p2align, error, *physp);
	return error;
#endif
}
