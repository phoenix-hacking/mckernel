#include <memobj.h>
#include <ihk/mm.h>
#include <kmsg.h>
#include <kmalloc.h>
#include <object_helpers.h>
#include <string.h>
#include <ihk/debug.h>

#if DEBUG_HUGEFILEOBJ
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

struct hugefileobj {
	struct memobj memobj;
	size_t pgsize;
	uintptr_t handle;
	unsigned int pgshift;
	size_t nr_pages;
	void **pages;
	ihk_spinlock_t lock;
	struct list_head obj_list;
};

static ihk_spinlock_t hugefileobj_list_lock;
static struct list_head hugefileobj_list = { &(hugefileobj_list), &(hugefileobj_list) };

static struct hugefileobj *to_hugefileobj(struct memobj *memobj)
{
	return (struct hugefileobj *)memobj;
}

static struct memobj *to_memobj(struct hugefileobj *obj)
{
	return &obj->memobj;
}

static struct hugefileobj *hugefileobj_lookup(uintptr_t handle);

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
static void hugefileobj_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void hugefileobj_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static void *hugefileobj_page_at_bridge(void *obj, long index)
{
	return ((struct hugefileobj *)obj)->pages[index];
}

static void hugefileobj_set_page_bridge(void *obj, long index, void *page)
{
	((struct hugefileobj *)obj)->pages[index] = page;
}

static void *hugefileobj_alloc_user_bridge(int npages, int p2align,
					   unsigned long flags,
					   uintptr_t virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flags, -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
}

static void hugefileobj_free_user_bridge(void *page, int npages)
{
	_ihk_mc_free_pages(page, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
}

static void *hugefileobj_kmalloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void hugefileobj_kfree_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static void *hugefileobj_memcpy_bridge(void *dst, const void *src, size_t len)
{
	return memcpy(dst, src, len);
}

static void *hugefileobj_memset_bridge(void *dst, int value, size_t len)
{
	return memset(dst, value, len);
}

static uintptr_t hugefileobj_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

static void hugefileobj_clear_path_bridge(void *obj)
{
	((struct hugefileobj *)obj)->memobj.path = NULL;
}

static void hugefileobj_set_nr_pages_bridge(void *obj, size_t nr_pages)
{
	((struct hugefileobj *)obj)->nr_pages = nr_pages;
}

static void hugefileobj_set_pages_bridge(void *obj, void *pages)
{
	((struct hugefileobj *)obj)->pages = pages;
}

static void hugefileobj_set_size_bridge(void *obj, size_t size)
{
	((struct hugefileobj *)obj)->memobj.size = size;
}

static void *hugefileobj_to_memobj_bridge(void *obj)
{
	return to_memobj((struct hugefileobj *)obj);
}

static void hugefileobj_set_handle_bridge(void *obj, uintptr_t handle)
{
	((struct hugefileobj *)obj)->handle = handle;
}

static void hugefileobj_set_pgsize_bridge(void *obj, size_t pgsize)
{
	((struct hugefileobj *)obj)->pgsize = pgsize;
}

static void hugefileobj_set_pgshift_bridge(void *obj, int pgshift)
{
	((struct hugefileobj *)obj)->pgshift = pgshift;
}

static void hugefileobj_init_obj_lock_bridge(void *obj)
{
	ihk_mc_spinlock_init(&((struct hugefileobj *)obj)->lock);
}

static void hugefileobj_set_flags_bridge(void *obj, unsigned int flags)
{
	((struct hugefileobj *)obj)->memobj.flags = flags;
}

static void hugefileobj_set_status_bridge(void *obj, int status)
{
	((struct hugefileobj *)obj)->memobj.status = status;
}

static void hugefileobj_set_ops_bridge(void *obj, void *ops)
{
	((struct hugefileobj *)obj)->memobj.ops = ops;
}

static void hugefileobj_set_refcnt_bridge(void *obj, int refcnt)
{
	ihk_atomic_set(&((struct hugefileobj *)obj)->memobj.refcnt, refcnt);
}

static void hugefileobj_set_path_bridge(void *obj, void *path)
{
	((struct hugefileobj *)obj)->memobj.path = path;
}

static void hugefileobj_copy_path_bridge(void *dst, const void *src,
					 size_t len)
{
	strncpy(dst, src, len);
}

static void hugefileobj_list_add_bridge(void *obj)
{
	list_add(&((struct hugefileobj *)obj)->obj_list, &hugefileobj_list);
}

static void hugefileobj_pre_create_log_bridge(int event, void *objp)
{
	struct hugefileobj *obj = objp;

	switch (event) {
	case HUGEFILEOBJ_LOG_PRE_CREATE_FOUND:
		dkprintf("%s: found obj: 0x%lx %s (ino: %lu)\n",
			 "hugefileobj_pre_create",
			 (unsigned long)to_memobj(obj),
			 obj->memobj.path ? obj->memobj.path : "(unknown)",
			 obj->handle);
		break;
	case HUGEFILEOBJ_LOG_PRE_CREATE_CREATED:
		dkprintf("%s: created obj: 0x%lx %s (ino: %lu)\n",
			 "hugefileobj_pre_create",
			 (unsigned long)to_memobj(obj),
			 obj->memobj.path ? obj->memobj.path : "(unknown)",
			 obj->handle);
		break;
	}
}

static void hugefileobj_pre_create_alloc_error_bridge(int stage)
{
	switch (stage) {
	case HUGEFILEOBJ_PRE_CREATE_ALLOC_OBJ:
		kprintf("%s: error: allocating hugefileobj\n",
			"hugefileobj_pre_create");
		break;
	case HUGEFILEOBJ_PRE_CREATE_ALLOC_PATH:
		kprintf("%s: error: allocating path\n",
			"hugefileobj_pre_create");
		break;
	}
}

static void hugefileobj_log_bridge(int event, void *obj, off_t off,
				   long index, size_t pgsize,
				   uintptr_t virt_addr)
{
	switch (event) {
	case HUGEFILEOBJ_LOG_GET_P2ALIGN_ERROR:
		kprintf("%s: p2align %ld but expected %ld\n",
			"hugefileobj_get_page", index, (long)virt_addr);
		break;
	case HUGEFILEOBJ_LOG_GET_ALLOC_ERROR:
		kprintf("%s: error: could not allocate page for off: "
			"%lu, page size: %lu\n",
			"hugefileobj_get_page", off, pgsize);
		break;
	case HUGEFILEOBJ_LOG_GET_ALLOCATED:
		dkprintf("%s: obj: 0x%lx, allocated page for off: %lu"
			 " (ind: %ld), page size: %lu\n",
			 "hugefileobj_get_page", (unsigned long)obj, off,
			 index, pgsize);
		break;
	case HUGEFILEOBJ_LOG_FREE_PAGE:
		dkprintf("%s: obj: 0x%lx, freed page at ind: %ld\n",
			 "__hugefileobj_free", (unsigned long)obj, index);
		break;
	case HUGEFILEOBJ_LOG_CREATE_ARRAY:
#ifndef ENABLE_FUGAKU_HACKS
		dkprintf("%s: obj: 0x%lx, VA: 0x%lx, page array allocated"
#else
		kprintf("%s: obj: 0x%lx, VA: 0x%lx, page array allocated"
#endif
			" for %ld pages, pagesize: %lu\n",
			"hugefileobj_create", (unsigned long)obj, virt_addr,
			index, pgsize);
		break;
	}
}
#endif

static struct hugefileobj *hugefileobj_lookup(uintptr_t handle)
{
	struct hugefileobj *p;

	for (p = ((typeof(*p) *)((char *)((&hugefileobj_list)->next) - offsetof(typeof(*p), obj_list))); &p->obj_list != (&hugefileobj_list); p = ((typeof(*p) *)((char *)(p->obj_list.next) - offsetof(typeof(*p), obj_list)))) {
		if (p->handle == handle) {
			/* for the interval between last put and fileobj_free
			 * taking list_lock
			 */
			if (!fileobj_lookup_ref_keep_result(
				    memobj_ref(&p->memobj))) {
				ihk_atomic_dec(&p->memobj.refcnt);
				continue;
			}
			return p;
		}
	}

	return NULL;
}

static int hugefileobj_get_page(struct memobj *memobj, off_t off,
				int p2align, uintptr_t *physp,
				unsigned long *pflag, uintptr_t virt_addr)
{
	struct hugefileobj *obj = to_hugefileobj(memobj);
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)pflag;
	return hugefileobj_get_page_body_result(
		obj, &obj->lock, off, p2align, obj->pgshift, obj->pgsize,
		virt_addr, physp, hugefileobj_lock_bridge,
		hugefileobj_unlock_bridge, hugefileobj_page_at_bridge,
		hugefileobj_set_page_bridge, hugefileobj_alloc_user_bridge,
		hugefileobj_memset_bridge, hugefileobj_virt_to_phys_bridge,
		hugefileobj_log_bridge);
#else
	off_t pgind;
	int ret = 0;
	int npages;

	(void)pflag;

	ret = hugefileobj_validate_p2align_result(p2align, obj->pgshift);
	if (ret) {
		kprintf("%s: p2align %d but expected %d\n",
			__func__, p2align,
			hugefileobj_expected_p2align_result(obj->pgshift));
		return ret;
	}

	pgind = hugefileobj_page_index_result(off, obj->pgshift);
	npages = hugefileobj_npages_per_page_result(obj->pgsize);
	ihk_mc_spinlock_lock_noirq(&obj->lock);
	if (!hugefileobj_page_present_result((uintptr_t)obj->pages[pgind])) {
		obj->pages[pgind] = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT | IHK_MC_AP_USER, -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
		if (!obj->pages[pgind]) {
			kprintf("%s: error: could not allocate page for off: "
				"%lu, page size: %lu\n", __func__, off,
				obj->pgsize);
			ret = -EIO;
			goto out;
		}

		memset(obj->pages[pgind], 0, obj->pgsize);
		dkprintf("%s: obj: 0x%lx, allocated page for off: %lu"
				" (ind: %d), page size: %lu\n",
				__func__, obj, off, pgind, obj->pgsize);
	}

	*physp = virt_to_phys(obj->pages[pgind]);

out:
	ihk_mc_spinlock_unlock_noirq(&obj->lock);

	return ret;
#endif
}

static void __hugefileobj_free(struct memobj *memobj)
{
	struct hugefileobj *obj = to_hugefileobj(memobj);

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)hugefileobj_inner_free_body_result(
		obj, &obj->lock, memobj->path, obj->pages, obj->nr_pages,
		obj->pgsize, hugefileobj_lock_bridge,
		hugefileobj_unlock_bridge, hugefileobj_kfree_bridge,
		hugefileobj_free_user_bridge, hugefileobj_page_at_bridge,
		hugefileobj_clear_path_bridge, hugefileobj_log_bridge);
#else
	ihk_mc_spinlock_lock_noirq(&obj->lock);
	if (hugefileobj_pointer_present_result((uintptr_t)memobj->path)) {
		kfree_tracked(memobj->path, __FILE__, __LINE__);
		memobj->path = NULL;
	}

	if (hugefileobj_pointer_present_result((uintptr_t)obj->pages)) {
		int i;

		for (i = 0; i < obj->nr_pages; ++i) {
			if (hugefileobj_page_present_result(
				    (uintptr_t)obj->pages[i])) {
				_ihk_mc_free_pages(obj->pages[i], hugefileobj_npages_per_page_result(
							obj->pgsize), IHK_MC_PG_USER, __FILE__, __LINE__);
				dkprintf("%s: obj: 0x%lx, freed page at "
					 "ind: %d\n", __func__, obj, i);
			}
		}

		kfree_tracked(obj->pages, __FILE__, __LINE__);
	}

	ihk_mc_spinlock_unlock_noirq(&obj->lock);
	kfree_tracked(obj, __FILE__, __LINE__);
#endif
}

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
static void hugefileobj_list_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void hugefileobj_list_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static int hugefileobj_list_empty_bridge(void *head)
{
	return list_empty((struct list_head *)head);
}

static void *hugefileobj_list_first_bridge(void *head)
{
	if (list_empty((struct list_head *)head)) {
		return NULL;
	}
	return ((struct hugefileobj *)((char *)(((struct list_head *)head)->next) - offsetof(struct hugefileobj, obj_list)));
}

static void *hugefileobj_list_next_bridge(void *head, void *obj)
{
	struct list_head *next = ((struct hugefileobj *)obj)->obj_list.next;

	if (next == (struct list_head *)head) {
		return NULL;
	}
	return ((struct hugefileobj *)((char *)(next) - offsetof(struct hugefileobj, obj_list)));
}

static uintptr_t hugefileobj_handle_bridge(void *obj)
{
	return ((struct hugefileobj *)obj)->handle;
}

static int hugefileobj_ref_bridge(void *obj)
{
	return memobj_ref(&((struct hugefileobj *)obj)->memobj);
}

static void hugefileobj_dec_bridge(void *obj)
{
	ihk_atomic_dec(&((struct hugefileobj *)obj)->memobj.refcnt);
}

static void *hugefileobj_lookup_bridge(uintptr_t handle)
{
	return hugefileobj_lookup_body_result(
		handle, &hugefileobj_list, hugefileobj_list_first_bridge,
		hugefileobj_list_next_bridge, hugefileobj_handle_bridge,
		hugefileobj_ref_bridge, hugefileobj_dec_bridge);
}

static void hugefileobj_list_del_bridge(void *obj)
{
	list_del(&((struct hugefileobj *)obj)->obj_list);
}

static void hugefileobj_free_obj_bridge(void *obj)
{
	__hugefileobj_free(to_memobj((struct hugefileobj *)obj));
}
#endif

static void hugefileobj_free(struct memobj *memobj)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)hugefileobj_free_body_result(
		to_hugefileobj(memobj), &hugefileobj_list_lock,
		hugefileobj_list_lock_bridge, hugefileobj_list_unlock_bridge,
		hugefileobj_list_del_bridge, hugefileobj_free_obj_bridge);
#else
	struct hugefileobj *obj = to_hugefileobj(memobj);

	ihk_mc_spinlock_lock_noirq(&hugefileobj_list_lock);
	list_del(&obj->obj_list);
	ihk_mc_spinlock_unlock_noirq(&hugefileobj_list_lock);

	__hugefileobj_free(memobj);
#endif
}

struct memobj_ops hugefileobj_ops = {
	.free = hugefileobj_free,
	.get_page = hugefileobj_get_page,
};

void hugefileobj_cleanup(void)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)hugefileobj_cleanup_body_result(
		&hugefileobj_list_lock, &hugefileobj_list,
		hugefileobj_list_lock_bridge, hugefileobj_list_unlock_bridge,
		hugefileobj_list_empty_bridge, hugefileobj_list_first_bridge,
		hugefileobj_list_del_bridge, hugefileobj_free_obj_bridge);
#else
	struct hugefileobj *obj;

	while (true) {
		ihk_mc_spinlock_lock_noirq(&hugefileobj_list_lock);
		if (list_empty(&hugefileobj_list)) {
			ihk_mc_spinlock_unlock_noirq(&hugefileobj_list_lock);
			break;
		}
		obj = ((struct hugefileobj *)((char *)((&hugefileobj_list)->next) - offsetof(struct hugefileobj, obj_list)));
		list_del(&obj->obj_list);
		ihk_mc_spinlock_unlock_noirq(&hugefileobj_list_lock);

		__hugefileobj_free(to_memobj(obj));
	}
#endif
}

int hugefileobj_pre_create(struct pager_create_result *result,
			   struct memobj **objp, int *maxprotp)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	return hugefileobj_pre_create_body_result(
		&hugefileobj_list_lock, result->handle, result->maxprot,
		result->flags, result->pgshift, result->path,
		sizeof(struct hugefileobj), PATH_MAX, &hugefileobj_ops,
		(void **)objp, maxprotp,
		hugefileobj_list_lock_bridge,
		hugefileobj_list_unlock_bridge, hugefileobj_lookup_bridge,
		hugefileobj_kmalloc_bridge, hugefileobj_kfree_bridge,
		hugefileobj_to_memobj_bridge, hugefileobj_set_handle_bridge,
		hugefileobj_set_pgsize_bridge, hugefileobj_set_pgshift_bridge,
		hugefileobj_set_pages_bridge, hugefileobj_set_nr_pages_bridge,
		hugefileobj_init_obj_lock_bridge, hugefileobj_set_flags_bridge,
		hugefileobj_set_status_bridge, hugefileobj_set_ops_bridge,
		hugefileobj_set_refcnt_bridge, hugefileobj_set_path_bridge,
		hugefileobj_copy_path_bridge, hugefileobj_list_add_bridge,
		hugefileobj_pre_create_log_bridge,
		hugefileobj_pre_create_alloc_error_bridge);
#else
	struct hugefileobj *obj;
	int ret = 0;

	ihk_mc_spinlock_lock_noirq(&hugefileobj_list_lock);
	obj = hugefileobj_lookup(result->handle);
	if (hugefileobj_pointer_present_result((uintptr_t)obj)) {
		dkprintf("%s: found obj: 0x%lx %s (ino: %lu)\n",
			 __func__,
			 obj->memobj,
			 obj->memobj.path ? obj->memobj.path : "(unknown)",
			 obj->handle);

		*maxprotp = result->maxprot;
		*objp = to_memobj(obj);
		ret = 0;

		goto out_unlock;
	}

	obj = kmalloc_tracked(sizeof(*obj), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!obj) {
		kprintf("%s: error: allocating hugefileobj\n", __func__);
		ret = -ENOMEM;
		goto out_unlock;
	}

	obj->handle = result->handle;
	obj->pgsize = hugefileobj_pgsize_result(result->pgshift);
	obj->pgshift = result->pgshift;
	obj->pages = NULL;
	obj->nr_pages = 0;
	ihk_mc_spinlock_init(&obj->lock);
	obj->memobj.flags = result->flags;
	obj->memobj.status = hugefileobj_initial_status_result();
	obj->memobj.ops = &hugefileobj_ops;

	/* keep mapping around when process is gone */
	ihk_atomic_set(&obj->memobj.refcnt,
		       hugefileobj_initial_refcnt_result());

	if (hugefileobj_pointer_present_result(result->path[0])) {
		obj->memobj.path = kmalloc_tracked(PATH_MAX, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!obj->memobj.path) {
			kprintf("%s: error: allocating path\n", __func__);
			kfree_tracked(obj, __FILE__, __LINE__);
			ret = -ENOMEM;
			goto out_unlock;
		}
		strncpy(obj->memobj.path, result->path, PATH_MAX);
	}

	list_add(&obj->obj_list, &hugefileobj_list);
	dkprintf("%s: created obj: 0x%lx %s (ino: %lu)\n",
		__func__,
		obj->memobj,
		obj->memobj.path ? obj->memobj.path : "(unknown)",
		obj->handle);

	*maxprotp = result->maxprot;
	*objp = to_memobj(obj);
	ret = 0;

out_unlock:
	ihk_mc_spinlock_unlock_noirq(&hugefileobj_list_lock);

	return ret;
#endif
}

int hugefileobj_create(struct memobj *memobj, size_t len, off_t off,
		       int *pgshiftp, uintptr_t virt_addr)
{
	struct hugefileobj *obj = to_hugefileobj(memobj);
#if defined(MCKERNEL_RUST_OBJECT_HELPERS) && !defined(ENABLE_FUGAKU_HACKS)
	dkprintf("%s: obj: 0x%lx, VA: 0x%lx, path: \"%s\","
			" len: %lu, off: %lu, pgshift: %d\n",
			__func__,
			obj,
			virt_addr,
			memobj->path ? memobj->path : "(unknown)",
			len,
			off,
			obj->pgshift);

	return hugefileobj_create_body_result(
		obj, &obj->lock, len, off, obj->pgshift, obj->pgsize,
		obj->nr_pages, obj->pages, pgshiftp, virt_addr,
		IHK_MC_AP_NOWAIT, hugefileobj_lock_bridge,
		hugefileobj_unlock_bridge, hugefileobj_kmalloc_bridge,
		hugefileobj_kfree_bridge, hugefileobj_memcpy_bridge,
		hugefileobj_memset_bridge, hugefileobj_set_nr_pages_bridge,
		hugefileobj_set_pages_bridge, hugefileobj_set_size_bridge,
		hugefileobj_log_bridge);
#else
	int nr_pages;
	int ret;

	dkprintf("%s: obj: 0x%lx, VA: 0x%lx, path: \"%s\","
			" len: %lu, off: %lu, pgshift: %d\n",
			__func__,
			obj,
			virt_addr,
			memobj->path ? memobj->path : "(unknown)",
			len,
			off,
			obj->pgshift);

	nr_pages = hugefileobj_create_nr_pages_result(off, len, obj->pgshift);

	ihk_mc_spinlock_lock_noirq(&obj->lock);
	/* Expand or allocate if needed */
	if (hugefileobj_needs_grow_result(obj->nr_pages, nr_pages)) {
		void **pages = kmalloc_tracked(hugefileobj_page_array_bytes_result(
					       nr_pages), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);

		if (hugefileobj_pointer_missing_result((uintptr_t)pages)) {
			ret = -ENOMEM;
			goto out;
		}

		if (hugefileobj_pointer_present_result(obj->nr_pages)) {
			memcpy(pages, obj->pages,
			       hugefileobj_copy_bytes_result(obj->nr_pages));
		}

		memset(pages + hugefileobj_zero_start_index_result(
			       obj->nr_pages), 0,
		       hugefileobj_zero_bytes_result(obj->nr_pages, nr_pages));

		if (hugefileobj_pointer_present_result(obj->nr_pages)) {
			kfree_tracked(obj->pages, __FILE__, __LINE__);
		}

		obj->nr_pages = nr_pages;
		obj->pages = pages;
#ifndef ENABLE_FUGAKU_HACKS
		dkprintf("%s: obj: 0x%lx, VA: 0x%lx, page array allocated"
#else
		kprintf("%s: obj: 0x%lx, VA: 0x%lx, page array allocated"
#endif
				" for %d pages, pagesize: %lu\n",
				__func__,
				obj,
				virt_addr,
				nr_pages,
				obj->pgsize);

#ifdef ENABLE_FUGAKU_HACKS
		if (!hugetlbfs_on_demand) {
			int pgind;
			int npages;

#ifndef ENABLE_FUGAKU_HACKS
			for (pgind = 0; pgind < obj->nr_pages; ++pgind) {
#else
			/* Map in only the last 8 pages */
			for (pgind = ((obj->nr_pages > 8) ? (obj->nr_pages - 8) : 0);
					pgind < obj->nr_pages; ++pgind) {
#endif
				if (hugefileobj_page_present_result(
					    (uintptr_t)obj->pages[pgind])) {
					continue;
				}

				npages = hugefileobj_npages_per_page_result(
					obj->pgsize);
				obj->pages[pgind] = _ihk_mc_alloc_aligned_pages_node(npages, hugefileobj_expected_p2align_result(
							obj->pgshift), IHK_MC_AP_NOWAIT | IHK_MC_AP_USER, -1, IHK_MC_PG_USER, 0, __FILE__, __LINE__);
				if (!obj->pages[pgind]) {
					kprintf("%s: error: could not allocate page for off: %lu"
							", page size: %lu\n", __func__, off, obj->pgsize);
					continue;
				}

				memset(obj->pages[pgind], 0, obj->pgsize);
				dkprintf("%s: obj: 0x%lx, pre-allocated page for off: %lu"
						" (ind: %d), page size: %lu\n",
						__func__, obj, off, pgind, obj->pgsize);
			}
		}
#endif
	}

	obj->memobj.size = len;
	*pgshiftp = obj->pgshift;
	ret = 0;

out:
	ihk_mc_spinlock_unlock_noirq(&obj->lock);

	return ret;
#endif
}
