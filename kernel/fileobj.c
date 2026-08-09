/* fileobj.c COPYRIGHT FUJITSU LIMITED 2015-2017 */
/**
 * \file fileobj.c
 *  License details are found in the file LICENSE.
 * \brief
 *  file back-ended pager client
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <ihk/cpu.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <ihk/types.h>
#include <cls.h>
#include <errno.h>
#include <kmalloc.h>
#include <kmsg.h>
#include <memobj.h>
#include <memory.h>
#include <page.h>
#include <pager.h>
#include <string.h>
#include <syscall.h>
#include <rusage_private.h>
#include <ihk/debug.h>
#include <mman.h>
#include <object_helpers.h>

//#define DEBUG_PRINT_FILEOBJ

#ifdef DEBUG_PRINT_FILEOBJ
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

mcs_lock_t fileobj_list_lock;
static struct list_head fileobj_list = { &(fileobj_list), &(fileobj_list) };

#define FILEOBJ_PAGE_HASH_SHIFT 9
#define FILEOBJ_PAGE_HASH_SIZE (1 << FILEOBJ_PAGE_HASH_SHIFT)
#define FILEOBJ_PAGE_HASH_MASK (FILEOBJ_PAGE_HASH_SIZE - 1)

struct fileobj {
	struct memobj memobj;		/* must be first */
	uint64_t sref;
	uintptr_t handle;
	struct list_head list;
	struct list_head page_hash[FILEOBJ_PAGE_HASH_SIZE];
	mcs_lock_t page_hash_locks[FILEOBJ_PAGE_HASH_SIZE];
};

static memobj_free_func_t fileobj_free;
static memobj_get_page_func_t fileobj_get_page;
static memobj_flush_page_func_t fileobj_flush_page;
static memobj_invalidate_page_func_t fileobj_invalidate_page;
static memobj_lookup_page_func_t fileobj_lookup_page;

static struct memobj_ops fileobj_ops = {
	.free =	&fileobj_free,
	.get_page =	&fileobj_get_page,
	.copy_page =	NULL,
	.flush_page =	&fileobj_flush_page,
	.invalidate_page =	&fileobj_invalidate_page,
	.lookup_page =	&fileobj_lookup_page,
};

static struct fileobj *to_fileobj(struct memobj *memobj)
{
	return (struct fileobj *)memobj;
}

static struct memobj *to_memobj(struct fileobj *fileobj)
{
	return &fileobj->memobj;
}

struct pageio_args {
	struct fileobj *	fileobj;
	off_t			objoff;
	size_t			pgsize;
};

static struct page *fileobj_page_hash_first(struct fileobj *obj);
static void obj_list_insert(struct fileobj *obj);
static void obj_list_remove(struct fileobj *obj);

/***********************************************************************
 * page_list
 */
static void fileobj_page_hash_init(struct fileobj *obj)
{
	int i;
	for (i = 0; i < FILEOBJ_PAGE_HASH_SIZE; ++i) {
		mcs_lock_init(&obj->page_hash_locks[i]);
		INIT_LIST_HEAD(&obj->page_hash[i]);
	}
	return;
}

/* NOTE: caller must hold page_hash_locks[hash] */
static void __fileobj_page_hash_insert(struct fileobj *obj,
		struct page *page, int hash)
{
	list_add(&page->list, &obj->page_hash[hash]);
}

/* NOTE: caller must hold page_hash_locks[hash] */
static void __fileobj_page_hash_remove(struct page *page)
{
	list_del(&page->list);
}

/* NOTE: caller must hold page_hash_locks[hash] */
static struct page *__fileobj_page_hash_lookup(struct fileobj *obj,
		int hash, off_t off)
{
	struct page *page;

	for (page = ((typeof(*page) *)((char *)((&obj->page_hash[hash])->next) - offsetof(typeof(*page), list))); &page->list != (&obj->page_hash[hash]); page = ((typeof(*page) *)((char *)(page->list.next) - offsetof(typeof(*page), list)))) {
		if (!fileobj_page_mode_valid_result(page->mode)) {
			kprintf("page_list_lookup(%p,%lx): mode %x\n",
					obj, off, page->mode);
			panic("page_list_lookup:invalid obj page");
		}

		if (page->offset == off) {
			goto out;
		}
	}
	page = NULL;

out:
	return page;
}

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
static void *fileobj_phys_to_page_bridge(uintptr_t phys)
{
	return phys_to_page(phys);
}

static off_t fileobj_page_offset_bridge(void *page)
{
	return ((struct page *)page)->offset;
}

static ssize_t fileobj_write_bridge(uintptr_t handle, off_t offset,
				    size_t pgsize, uintptr_t phys)
{
	ihk_mc_user_context_t ctx;

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_WRITE);
	ihk_mc_syscall_set_arg1(&ctx, handle);
	ihk_mc_syscall_set_arg2(&ctx, offset);
	ihk_mc_syscall_set_arg3(&ctx, pgsize);
	ihk_mc_syscall_set_arg4(&ctx, phys);

	dkprintf("%s: syscall_generic_forwarding\n", __FUNCTION__);
	return syscall_generic_forwarding(__NR_mmap, &ctx);
}

static void fileobj_log_bridge(int event, void *memobj, void *obj,
			       uintptr_t phys, size_t pgsize, ssize_t result)
{
	switch (event) {
	case FILEOBJ_LOG_FLUSH_MISSING_PAGE:
		kprintf("%s: warning: tried to flush non-existing page for phys addr: 0x%lx\n",
			"fileobj_flush_page", phys);
		break;
	case FILEOBJ_LOG_FLUSH_SHORT_WRITE:
		dkprintf("fileobj_flush_page(%p,%lx,%lx): %ld (%lx)\n",
			 memobj, phys, pgsize, result, result);
		break;
	case FILEOBJ_LOG_INVALIDATE_UNSUPPORTED:
		(void)obj;
		kprintf("%s: WARNING: file mapping invalidation not supported\n",
			"fileobj_invalidate_page");
		break;
	}
}

static void fileobj_hash_lock_bridge(void *lock, void *node)
{
	mcs_lock_lock((mcs_lock_t *)lock, (struct mcs_lock_node *)node);
}

static void fileobj_hash_unlock_bridge(void *lock, void *node)
{
	mcs_lock_unlock((mcs_lock_t *)lock, (struct mcs_lock_node *)node);
}

static void *fileobj_hash_lookup_bridge(void *obj, int hash, off_t off)
{
	return __fileobj_page_hash_lookup(obj, hash, off);
}

static uintptr_t fileobj_page_phys_bridge(void *page)
{
	return page_to_phys((struct page *)page);
}

static void *fileobj_list_first_bridge(void *head)
{
	if (list_empty((struct list_head *)head)) {
		return NULL;
	}
	return ((struct fileobj *)((char *)(((struct list_head *)head)->next) - offsetof(struct fileobj, list)));
}

static void *fileobj_list_next_bridge(void *head, void *obj)
{
	struct list_head *next = ((struct fileobj *)obj)->list.next;

	if (next == (struct list_head *)head) {
		return NULL;
	}
	return ((struct fileobj *)((char *)(next) - offsetof(struct fileobj, list)));
}

static uintptr_t fileobj_handle_bridge(void *obj)
{
	return ((struct fileobj *)obj)->handle;
}

static int fileobj_ref_bridge(void *obj)
{
	return memobj_ref(&((struct fileobj *)obj)->memobj);
}

static void fileobj_dec_bridge(void *obj)
{
	ihk_atomic_dec(&((struct fileobj *)obj)->memobj.refcnt);
}

static void fileobj_list_lock_noirq_bridge(void *lock, void *node)
{
	mcs_lock_lock_noirq((mcs_lock_t *)lock, (struct mcs_lock_node *)node);
}

static void fileobj_list_unlock_noirq_bridge(void *lock, void *node)
{
	mcs_lock_unlock_noirq((mcs_lock_t *)lock, (struct mcs_lock_node *)node);
}

static void fileobj_list_remove_bridge(void *obj)
{
	obj_list_remove(obj);
}

static void fileobj_list_insert_bridge(void *obj)
{
	obj_list_insert(obj);
}

static void fileobj_size_set_bridge(void *obj, size_t size)
{
	to_memobj((struct fileobj *)obj)->size = size;
}

static void fileobj_flags_set_bridge(void *obj, int flags)
{
	to_memobj((struct fileobj *)obj)->flags = flags;
}

static void fileobj_status_set_bridge(void *obj, int status)
{
	to_memobj((struct fileobj *)obj)->status = status;
}

static void fileobj_refcnt_set_bridge(void *obj, int refcnt)
{
	ihk_atomic_set(&to_memobj((struct fileobj *)obj)->refcnt, refcnt);
}

static unsigned long fileobj_sref_get_bridge(void *obj)
{
	return ((struct fileobj *)obj)->sref;
}

static void fileobj_sref_set_bridge(void *obj, unsigned long sref)
{
	((struct fileobj *)obj)->sref = sref;
}

static void *fileobj_alloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void fileobj_path_copy_bridge(void *dst, const void *src, size_t len)
{
	strncpy(dst, src, len);
}

static void fileobj_path_set_bridge(void *obj, void *path)
{
	to_memobj((struct fileobj *)obj)->path = path;
}

static void fileobj_create_log_bridge(int event, void *obj,
				      const void *path, long value)
{
	(void)obj;
	(void)path;
	(void)value;

	switch (event) {
	case FILEOBJ_CREATE_LOG_PATH_ALLOC_FAILED:
		kprintf("%s: error: allocating path\n", "fileobj_create");
		break;
	}
}

static void fileobj_pages_set_bridge(void *obj, void *pages)
{
	to_memobj((struct fileobj *)obj)->pages = pages;
}

static void fileobj_nr_pages_set_bridge(void *obj, int nr_pages)
{
	to_memobj((struct fileobj *)obj)->nr_pages = nr_pages;
}

static void fileobj_memzero_bridge(void *ptr, size_t len)
{
	memset(ptr, 0, len);
}

static void *fileobj_alloc_pages_node_bridge(int npages, int p2align,
					     unsigned long flags, int node,
					     uintptr_t virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flags, node, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
}

static void fileobj_page_array_set_bridge(void *pages, int index, void *page)
{
	((void **)pages)[index] = page;
}

static void fileobj_rss_add_bridge(size_t size, size_t pgsize)
{
	rusage_memory_stat_mapped_file_add(size, pgsize);
}

static void fileobj_create_premap_log_bridge(int event, void *obj0,
					     void *page, long value)
{
	(void)obj0;

	switch (event) {
	case FILEOBJ_CREATE_LOG_PREMAP_START:
		dkprintf("%s: MF_PREMAP, start node: %ld\n",
			 "fileobj_create", value);
		break;
	case FILEOBJ_CREATE_LOG_PREMAP_ARRAY_ALLOC_FAILED:
		kprintf("%s: WARNING: failed to allocate pages\n",
			"fileobj_create");
		break;
	case FILEOBJ_CREATE_LOG_PREMAP_PAGE_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating pages[%ld]\n",
			"fileobj_create", value);
		break;
	case FILEOBJ_CREATE_LOG_PREMAP_RSS_ADD:
		dkprintf("%lx+,%s: MF_PREMAP&&MPOL_SHM_PREMAP,memory_stat_rss_add,phys=%lx,size=%ld,pgsize=%ld\n",
			 virt_to_phys(page), "fileobj_create",
			 virt_to_phys(page), PAGE_SIZE, PAGE_SIZE);
		break;
	case FILEOBJ_CREATE_LOG_PREMAP_INTERLEAVED_DONE:
		dkprintf("%s: allocated %ld pages interleaved\n",
			 "fileobj_create", value);
		break;
	}
}

static void *fileobj_alloc_pages_bridge(int npages, unsigned long flags,
					uintptr_t virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
}

static void *fileobj_page_array_cmpxchg_bridge(void *pages, int index,
					       void *old, void *new_value)
{
	return atomic_cmpxchg_ptr(&((void **)pages)[index], old, new_value);
}

static uintptr_t fileobj_virt_phys_bridge(void *ptr)
{
	return virt_to_phys(ptr);
}

static void *fileobj_phys_to_page_insert_bridge(uintptr_t phys)
{
	return phys_to_page_insert_hash(phys);
}

static void fileobj_page_offset_set_bridge(void *page, off_t off)
{
	((struct page *)page)->offset = off;
}

static void fileobj_page_count_set_bridge(void *page, long value)
{
	ihk_atomic_set(&((struct page *)page)->count, value);
}

static void fileobj_page_mapped_set_bridge(void *page, long value)
{
	ihk_atomic64_set(&((struct page *)page)->mapped, value);
}

static void fileobj_page_hash_insert_bridge(void *obj, void *page, int hash)
{
	__fileobj_page_hash_insert(obj, page, hash);
}

static void fileobj_page_count_inc_bridge(void *page)
{
	ihk_atomic_inc(&((struct page *)page)->count);
}

static void fileobj_pageio_args_set_bridge(void *args0, void *obj, off_t off,
					   size_t pgsize)
{
	struct pageio_args *args = args0;

	args->fileobj = obj;
	args->objoff = off;
	args->pgsize = pgsize;
}

static void fileobj_pgio_set_bridge(void *thread0, void *pageio_fn, void *args)
{
	struct thread *thread = thread0;

	thread->pgio_fp = pageio_fn;
	thread->pgio_arg = args;
}

static void fileobj_get_log_bridge(int event, void *obj, off_t off,
				   int p2align, uintptr_t virt_addr,
				   uintptr_t physp_addr, void *page,
				   uintptr_t phys, long value)
{
	switch (event) {
	case FILEOBJ_GET_LOG_PREMAP_ALLOC_FAILED:
		kprintf("fileobj_get_page(%p,%lx,%x,%lx,%lx):alloc failed. %ld\n",
			obj, off, p2align, virt_addr, physp_addr, value);
		break;
	case FILEOBJ_GET_LOG_PREMAP_ALLOCATED:
		dkprintf("%s: MF_ZEROFILL: off: %lu -> 0x%lx allocated\n",
			 "fileobj_get_page", off, phys);
		break;
	case FILEOBJ_GET_LOG_PREMAP_RSS_ADD:
		dkprintf("%lx+,%s: MF_PREMAP&&!MPOL_SHM_PREMAP,memory_stat_rss_add,phys=%lx,size=%ld,pgsize=%ld\n",
			 phys, "fileobj_get_page", phys, PAGE_SIZE,
			 PAGE_SIZE);
		break;
	case FILEOBJ_GET_LOG_PREMAP_RESOLVED:
		(void)page;
		dkprintf("%s: MF_ZEROFILL: off: %lu -> 0x%lx resolved\n",
			 "fileobj_get_page", off, phys);
		break;
	}
}

static void fileobj_get_regular_log_bridge(
	int event, void *obj, off_t off, int p2align, uintptr_t virt_addr,
	uintptr_t physp_addr, void *page, uintptr_t phys, uintptr_t value,
	size_t size, int mode, int count)
{
	switch (event) {
	case FILEOBJ_GET_LOG_KMALLOC_FAILED:
		kprintf("fileobj_get_page(%p,%lx,%x,%lx,%lx):kmalloc failed. %ld\n",
			obj, off, p2align, virt_addr, physp_addr, (long)value);
		break;
	case FILEOBJ_GET_LOG_ALLOC_FAILED:
		kprintf("fileobj_get_page(%p,%lx,%x,%lx,%lx):alloc failed. %ld\n",
			obj, off, p2align, virt_addr, physp_addr, (long)value);
		break;
	case FILEOBJ_GET_LOG_NEW_PAGE:
		dkprintf("%s: phys_to_page_insert_hash(),phys=%lx,virt=%lx,size=%lx,pgsize=%lx\n",
			 "fileobj_get_page", phys, value, size, PAGE_SIZE);
		break;
	case FILEOBJ_GET_LOG_MAP_DONE:
		(void)value;
		(void)size;
		(void)mode;
		(void)count;
		dkprintf("%s: PM_DONE_PAGEIO-->PM_MAPPED,obj=%lx,off=%lx,phys=%lx\n",
			 "fileobj_get_page", (uintptr_t)obj, off, phys);
		break;
	case FILEOBJ_GET_LOG_USE_PAGE:
		(void)value;
		(void)size;
		dkprintf("%s: mode=%d,count=%d,obj=%lx,off=%lx,phys=%lx\n",
			 "fileobj_get_page", mode, count, (uintptr_t)obj, off,
			 phys);
		break;
	case FILEOBJ_GET_LOG_RETURN:
		(void)page;
		(void)size;
		(void)mode;
		(void)count;
		dkprintf("fileobj_get_page(%p,%lx,%x,%lx,%lx): %ld %lx\n",
			 obj, off, p2align, virt_addr, physp_addr, (long)value,
			 phys);
		break;
	}
}

static void fileobj_get_regular_panic_bridge(void *obj, off_t off, void *page,
					     int mode)
{
	(void)obj;
	(void)off;
	(void)page;
	(void)mode;
	panic("fileobj_get_page:invalid new page");
}

static void *fileobj_page_first_bridge(void *obj)
{
	return fileobj_page_hash_first(obj);
}

static void fileobj_page_remove_bridge(void *page)
{
	__fileobj_page_hash_remove(page);
}

static void *fileobj_phys_to_virt_bridge(uintptr_t phys)
{
	return phys_to_virt(phys);
}

static int fileobj_page_count_bridge(void *page)
{
	return ihk_atomic_read(&((struct page *)page)->count);
}

static int fileobj_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}

static void fileobj_free_pages_bridge(void *addr, int npages)
{
	_ihk_mc_free_pages(addr, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
}

static void fileobj_rss_sub_bridge(size_t size, size_t pgsize)
{
	rusage_memory_stat_mapped_file_sub(size, pgsize);
}

static void fileobj_kfree_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static int fileobj_release_bridge(uintptr_t handle, unsigned long sref)
{
	ihk_mc_user_context_t ctx;

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_RELEASE);
	ihk_mc_syscall_set_arg1(&ctx, handle);
	ihk_mc_syscall_set_arg2(&ctx, sref);

	return syscall_generic_forwarding(__NR_mmap, &ctx);
}

static void *fileobj_page_array_at_bridge(void *pages, int index)
{
	if (!pages) {
		return NULL;
	}
	return ((void **)pages)[index];
}

static void fileobj_free_log_bridge(int event, void *obj0, void *page0,
				    uintptr_t phys, long value,
				    unsigned long flags)
{
	struct fileobj *obj = obj0;
	struct page *page = page0;

	switch (event) {
	case FILEOBJ_LOG_FREE_INVALID_COUNT:
		kprintf("%s: WARNING: page count is %ld for phys 0x%lx is invalid, flags: 0x%lx\n",
			"fileobj_free", value, page ? page->phys : phys, flags);
		break;
	case FILEOBJ_LOG_FREE_RSS_SUB:
		dkprintf("%lx-,%s: memory_stat_rss_sub,phys=%lx,size=%ld,pgsize=%ld\n",
			 phys, "fileobj_free", phys, value, PAGE_SIZE);
		break;
	case FILEOBJ_LOG_FREE_RELEASE_ERROR:
		dkprintf("%s(%p %lx): free failed. %ld\n",
			 "fileobj_free", obj, phys, value);
		break;
	case FILEOBJ_LOG_FREE_DONE:
		dkprintf("%s(%p %lx):free\n", "fileobj_free", obj, phys);
		break;
	}
}

static int fileobj_page_mode_bridge(void *page)
{
	return ((struct page *)page)->mode;
}

static void fileobj_page_set_mode_bridge(void *page, int mode)
{
	((struct page *)page)->mode = mode;
}

static void fileobj_pageio_zero_bridge(uintptr_t phys)
{
	void *virt = phys_to_virt(phys);

	memset(virt, 0, PAGE_SIZE);
#ifdef PROFILE_ENABLE
	profile_event_add(PROFILE_page_fault_file_clr, PAGE_SIZE);
#endif
}

static ssize_t fileobj_pageio_read_bridge(uintptr_t handle, off_t offset,
					  size_t pgsize, uintptr_t phys)
{
	ihk_mc_user_context_t ctx;

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_READ);
	ihk_mc_syscall_set_arg1(&ctx, handle);
	ihk_mc_syscall_set_arg2(&ctx, offset);
	ihk_mc_syscall_set_arg3(&ctx, pgsize);
	ihk_mc_syscall_set_arg4(&ctx, phys);

	dkprintf("%s: __NR_mmap for handle 0x%lx\n",
		 __FUNCTION__, handle);
	return syscall_generic_forwarding(__NR_mmap, &ctx);
}

static void fileobj_pageio_schedule_bridge(void)
{
	schedule();
}

static void fileobj_pageio_pause_bridge(void)
{
	cpu_pause();
}

static void fileobj_pageio_log_bridge(int event, void *obj0, off_t off,
				      size_t pgsize, long value)
{
	struct fileobj *obj = obj0;

	switch (event) {
	case FILEOBJ_LOG_PAGEIO_SCHEDULE:
		dkprintf("%s: %s:%lu PM_PAGEIO loop %ld -> schedule()\n",
			 "fileobj_do_pageio", to_memobj(obj)->path, off, value);
		break;
	case FILEOBJ_LOG_PAGEIO_EOF:
		dkprintf("fileobj_do_pageio(%p,%lx,%lx):EOF? %ld\n",
			 obj, off, pgsize, value);
		break;
	case FILEOBJ_LOG_PAGEIO_READ_ERROR:
		kprintf("fileobj_do_pageio(%p,%lx,%lx):read failed. %ld\n",
			obj, off, pgsize, value);
		break;
	}
}

static void fileobj_pageio_panic_bridge(void *obj, off_t off, size_t pgsize,
					int mode)
{
	kprintf("fileobj_do_pageio(%p,%lx,%lx):invalid mode %x\n",
		obj, off, pgsize, mode);
	panic("fileobj_do_pageio:invalid page mode");
}
#endif

static struct page *fileobj_page_hash_first(struct fileobj *obj)
{
	int i;

	for (i = 0; i < FILEOBJ_PAGE_HASH_SIZE; ++i) {
		if (!list_empty(&obj->page_hash[i])) {
			break;
		}
	}

	if (i != FILEOBJ_PAGE_HASH_SIZE) {
		return ((struct page *)((char *)((&obj->page_hash[i])->next) - offsetof(struct page, list)));
	}
	else {
		return NULL;
	}
}

/***********************************************************************
 * obj_list
 */
static void obj_list_insert(struct fileobj *obj)
{
	list_add(&obj->list, &fileobj_list);
}

static void obj_list_remove(struct fileobj *obj)
{
	list_del(&obj->list);
}

/* return NULL or locked fileobj */
static struct fileobj *obj_list_lookup(uintptr_t handle)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	return fileobj_obj_list_lookup_body_result(
		handle, &fileobj_list, fileobj_list_first_bridge,
		fileobj_list_next_bridge, fileobj_handle_bridge,
		fileobj_ref_bridge, fileobj_dec_bridge);
#else
	struct fileobj *p;

	for (p = ((typeof(*p) *)((char *)((&fileobj_list)->next) - offsetof(typeof(*p), list))); &p->list != (&fileobj_list); p = ((typeof(*p) *)((char *)(p->list.next) - offsetof(typeof(*p), list)))) {
		if (p->handle == handle) {
			/* for the interval between last put and fileobj_free
			 * taking list_lock
			 */
			if (!fileobj_lookup_ref_keep_result(memobj_ref(&p->memobj))) {
				ihk_atomic_dec(&p->memobj.refcnt);
				continue;
			}
			return p;
		}
	}

	return NULL;
#endif
}

/***********************************************************************
 * fileobj
 */
int fileobj_create(int fd, struct memobj **objp, int *maxprotp, int flags,
		   uintptr_t virt_addr)
{
	ihk_mc_user_context_t ctx;
	struct pager_create_result result __attribute__((aligned(64)));	
	int error;
	struct fileobj *newobj  = NULL;
	struct fileobj *obj;
	struct mcs_lock_node node;

	dkprintf("%s(%d)\n", __func__, fd);

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_CREATE);
	ihk_mc_syscall_set_arg1(&ctx, fd);
	ihk_mc_syscall_set_arg2(&ctx, virt_to_phys(&result));
	memset(&result, 0, sizeof(result));

	error = syscall_generic_forwarding(__NR_mmap, &ctx);

	if (error) {
		/* -ESRCH doesn't mean an error but requesting a fall
		 * back to treat the file as a device file
		 */
		if (error != -ESRCH) {
			kprintf("%s(%d):create failed. %d\n",
				__func__, fd, error);
		}
		goto out;
	}

	if (fileobj_hugetlbfs_result(result.flags)) {
		return hugefileobj_pre_create(&result, objp, maxprotp);
	}

	mcs_lock_lock(&fileobj_list_lock, &node);
	obj = obj_list_lookup(result.handle);
	if (obj)
		goto found;
	mcs_lock_unlock(&fileobj_list_lock, &node);

	// not found: alloc new object and lookup again
	newobj = kmalloc_tracked(sizeof(*newobj), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!newobj) {
		error = -ENOMEM;
		kprintf("%s(%d):kmalloc failed. %d\n", __func__, fd, error);
		goto out;
	}
	memset(newobj, 0, sizeof(*newobj));
	newobj->memobj.ops = &fileobj_ops;
#ifndef MCKERNEL_RUST_OBJECT_HELPERS
	newobj->memobj.flags = fileobj_create_base_flags_result(flags);
#endif
	newobj->handle = result.handle;

	fileobj_page_hash_init(newobj);

	mcs_lock_lock_noirq(&fileobj_list_lock, &node);
	obj = obj_list_lookup(result.handle);
	if (!obj) {
		obj = newobj;
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
		error = fileobj_create_publish_body_result(
			obj, 1, flags, result.flags, result.size,
			fileobj_list_insert_bridge, fileobj_size_set_bridge,
			fileobj_flags_set_bridge, fileobj_status_set_bridge,
			fileobj_refcnt_set_bridge, fileobj_sref_get_bridge,
			fileobj_sref_set_bridge);
		if (error) {
			mcs_lock_unlock_noirq(&fileobj_list_lock, &node);
			goto out;
		}
#else
		obj_list_insert(newobj);
		to_memobj(obj)->size = result.size;
		to_memobj(obj)->flags = fileobj_apply_result_flags_result(
			to_memobj(obj)->flags, result.flags);
		to_memobj(obj)->status =
			fileobj_status_from_flags_result(to_memobj(obj)->flags);
		ihk_atomic_set(&to_memobj(obj)->refcnt,
			       fileobj_initial_refcnt_result());
		obj->sref = fileobj_initial_sref_result();
#endif

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
		error = fileobj_create_path_body_result(
			obj, result.path[0], result.path, PATH_MAX,
			IHK_MC_AP_NOWAIT, fileobj_alloc_bridge,
			fileobj_path_copy_bridge, fileobj_path_set_bridge,
			fileobj_create_log_bridge);
		if (error) {
			mcs_lock_unlock_noirq(&fileobj_list_lock, &node);
			goto out;
		}
#else
		if (fileobj_path_present_result(result.path[0])) {
			newobj->memobj.path = kmalloc_tracked(PATH_MAX, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!newobj->memobj.path) {
				error = -ENOMEM;
				kprintf("%s: error: allocating path\n", __FUNCTION__);
				mcs_lock_unlock_noirq(&fileobj_list_lock, &node);
				goto out;
			}
			strncpy(newobj->memobj.path, result.path, PATH_MAX);
		}
#endif

		dkprintf("%s: %s\n", __FUNCTION__, obj->memobj.path);

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
		error = fileobj_create_premap_body_result(
			obj, to_memobj(obj)->flags, result.size,
			fileobj_premap_zerofill_result(to_memobj(obj)->flags) ?
				get_this_cpu_local_var()->current->proc->mpol_flags : 0,
			fileobj_premap_zerofill_result(to_memobj(obj)->flags) ?
				ihk_mc_get_nr_numa_nodes() : 0,
			virt_addr,
			IHK_MC_AP_NOWAIT, fileobj_alloc_bridge,
			fileobj_pages_set_bridge, fileobj_nr_pages_set_bridge,
			fileobj_memzero_bridge, fileobj_alloc_pages_node_bridge,
			fileobj_page_array_set_bridge, fileobj_rss_add_bridge,
			fileobj_create_premap_log_bridge);
		if (error) {
			mcs_lock_unlock_noirq(&fileobj_list_lock, &node);
			goto out;
		}
#else
		/* XXX: KNL specific optimization for OFP runs */
		if (fileobj_premap_zerofill_result(to_memobj(obj)->flags)) {
			struct memobj *mo = to_memobj(obj);
			int nr_pages = fileobj_premap_npages_result(result.size);
			int j = 0;
			int node = fileobj_premap_start_node_result(
				ihk_mc_get_nr_numa_nodes());
			dkprintf("%s: MF_PREMAP, start node: %d\n",
				__FUNCTION__, node);

			mo->pages = kmalloc_tracked(nr_pages * sizeof(void *), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!mo->pages) {
				kprintf("%s: WARNING: failed to allocate pages\n",
						__FUNCTION__);
				goto error_cleanup;
			}

			mo->nr_pages = nr_pages;
			memset(mo->pages, 0,
			       fileobj_pages_bytes_result(nr_pages));

			if (fileobj_premap_interleave_result(
				    get_this_cpu_local_var()->current->proc->mpol_flags)) {
				/* Get the actual pages NUMA interleaved */
				for (j = 0; j < nr_pages; ++j) {
					mo->pages[j] = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, node, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
					if (!mo->pages[j]) {
						kprintf("%s: ERROR: allocating pages[%d]\n",
								__FUNCTION__, j);
						goto error_cleanup;
					}
					// Track change in memobj->pages[] for MF_PREMAP pages (MPOL_SHM_PREMAP case)
					dkprintf("%lx+,%s: MF_PREMAP&&MPOL_SHM_PREMAP,memory_stat_rss_add,phys=%lx,size=%ld,pgsize=%ld\n", virt_to_phys(mo->pages[j]), __FUNCTION__, virt_to_phys(mo->pages[j]), PAGE_SIZE, PAGE_SIZE);
					rusage_memory_stat_mapped_file_add(PAGE_SIZE, PAGE_SIZE);

					memset(mo->pages[j], 0, PAGE_SIZE);

					node = fileobj_premap_next_node_result(
						node, ihk_mc_get_nr_numa_nodes());
				}
				dkprintf("%s: allocated %d pages interleaved\n",
						__FUNCTION__, nr_pages);
			}
error_cleanup:
			/* TODO: cleanup allocated portion */
			;
		}
#endif

		newobj = NULL;
		dkprintf("%s: new obj 0x%lx %s\n",
			__FUNCTION__,
			obj,
			to_memobj(obj)->flags & MF_ZEROFILL ? "zerofill" : "");
	}
	else {
found:
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
		error = fileobj_create_publish_body_result(
			obj, 0, flags, result.flags, result.size,
			fileobj_list_insert_bridge, fileobj_size_set_bridge,
			fileobj_flags_set_bridge, fileobj_status_set_bridge,
			fileobj_refcnt_set_bridge, fileobj_sref_get_bridge,
			fileobj_sref_set_bridge);
		if (error) {
			mcs_lock_unlock_noirq(&fileobj_list_lock, &node);
			goto out;
		}
#else
		obj->sref = fileobj_next_sref_result(obj->sref);
#endif
		dkprintf("%s: existing obj 0x%lx, %s\n",
			__FUNCTION__,
			obj,
			to_memobj(obj)->flags & MF_ZEROFILL ? "zerofill" : "");
	}

	mcs_lock_unlock_noirq(&fileobj_list_lock, &node);

	error = 0;
	*objp = to_memobj(obj);
	*maxprotp = result.maxprot;

out:
	if (newobj) {
		kfree_tracked(newobj, __FILE__, __LINE__);
	}
	dkprintf("%s(%d):%d %p %x\n", __func__, fd, error, *objp, *maxprotp);
	return error;
}

static void fileobj_free(struct memobj *memobj)
{
	struct fileobj *obj = to_fileobj(memobj);
	struct mcs_lock_node node;
#ifndef MCKERNEL_RUST_OBJECT_HELPERS
	int error;
	ihk_mc_user_context_t ctx;
#endif


	dkprintf("%s: free obj 0x%lx, %s\n", __func__,
		 obj, to_memobj(obj)->flags & MF_ZEROFILL ? "zerofill" : "");

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)fileobj_free_body_result(
		obj, to_memobj(obj)->flags, obj->handle, obj->sref,
		to_memobj(obj)->pages, to_memobj(obj)->nr_pages,
		to_memobj(obj)->path, &fileobj_list_lock, &node,
		fileobj_list_lock_noirq_bridge,
		fileobj_list_unlock_noirq_bridge,
		fileobj_list_remove_bridge, fileobj_page_first_bridge,
		fileobj_page_remove_bridge, fileobj_page_phys_bridge,
		fileobj_phys_to_virt_bridge, fileobj_page_count_bridge,
		fileobj_page_unmap_bridge, fileobj_free_pages_bridge,
		fileobj_rss_sub_bridge, fileobj_kfree_bridge,
		fileobj_release_bridge, fileobj_page_array_at_bridge,
		fileobj_free_log_bridge);
	return;
#else
	mcs_lock_lock_noirq(&fileobj_list_lock, &node);
	obj_list_remove(obj);
	mcs_lock_unlock_noirq(&fileobj_list_lock, &node);

	/* zap page_list */
	for (;;) {
		struct page *page;
		void *page_va;
		uintptr_t phys;

		page = fileobj_page_hash_first(obj);
		if (!page) {
			break;
		}
		__fileobj_page_hash_remove(page);
		phys = page_to_phys(page);
		page_va = phys_to_virt(phys);
		/* Count must be one because set to one on the first
		 * get_page() invoking fileobj_do_pageio and incremented by
		 * the second get_page() reaping the pageio and decremented
		 * by clear_range().
		 */
		if (fileobj_invalid_page_count_result(ihk_atomic_read(&page->count))) {
			kprintf("%s: WARNING: page count is %d for phys 0x%lx is invalid, flags: 0x%lx\n",
				__func__, ihk_atomic_read(&page->count),
				page->phys, to_memobj(obj)->flags);
		}
		else if (fileobj_should_free_hashed_page_result(
				 ihk_atomic_read(&page->count), page_unmap(page))) {
			_ihk_mc_free_pages(page_va, 1, IHK_MC_PG_USER, __FILE__, __LINE__);
			/* Track change in page->count for !MF_PREMAP pages.
			 * It is decremented here or in clear_range()
			 */
			dkprintf("%lx-,%s: calling memory_stat_rss_sub(),phys=%lx,size=%ld,pgsize=%ld\n",
				 phys, __func__, phys, PAGE_SIZE, PAGE_SIZE);
			rusage_memory_stat_mapped_file_sub(PAGE_SIZE,
							   PAGE_SIZE);
			kfree_tracked(page, __FILE__, __LINE__);
		}
	}

	/* Pre-mapped zerofilled? */
	if (fileobj_premap_zerofill_result(to_memobj(obj)->flags)) {
		int i;

		for (i = 0; i < to_memobj(obj)->nr_pages; ++i) {
			if (fileobj_premap_page_present_result(
				    (uintptr_t)to_memobj(obj)->pages[i])) {
				dkprintf("%s: pages[i]=%p\n", __func__, i,
					 to_memobj(obj)->pages[i]);
				// Track change in fileobj->pages[] for MF_PREMAP pages
				// Note that page_unmap() isn't called for MF_PREMAP in
				// free_process_memory_range() --> ihk_mc_pt_free_range()
				dkprintf("%lx-,%s: memory_stat_rss_sub,phys=%lx,size=%ld,pgsize=%ld\n",
					 virt_to_phys(to_memobj(obj)->pages[i]),
					 __func__,
					 virt_to_phys(to_memobj(obj)->pages[i]),
					 PAGE_SIZE, PAGE_SIZE);
				rusage_memory_stat_mapped_file_sub(PAGE_SIZE,
								   PAGE_SIZE);
				_ihk_mc_free_pages(to_memobj(obj)->pages[i], 1, IHK_MC_PG_USER, __FILE__, __LINE__);
			}
		}

		kfree_tracked(to_memobj(obj)->pages, __FILE__, __LINE__);
	}

	if (fileobj_path_present_result((uintptr_t)to_memobj(obj)->path)) {
		dkprintf("%s: %s\n", __func__, to_memobj(obj)->path);
		kfree_tracked(to_memobj(obj)->path, __FILE__, __LINE__);
	}

	/* linux side
	 * sref is necessary because handle is used as key, so there could
	 * be a new mckernel pager with the same handle being created as
	 * this one is being destroyed
	 */
	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_RELEASE);
	ihk_mc_syscall_set_arg1(&ctx, obj->handle);
	ihk_mc_syscall_set_arg2(&ctx, obj->sref);

	error = syscall_generic_forwarding(__NR_mmap, &ctx);
	if (error) {
		dkprintf("%s(%p %lx): free failed. %d\n", __func__,
			obj, obj->handle, error);
		/* through */
	}

	dkprintf("%s(%p %lx):free\n", __func__, obj, obj->handle);
	kfree_tracked(obj, __FILE__, __LINE__);
	return;
#endif

}

/*
 * fileobj_do_pageio():
 * - args0 will be freed with kfree()
 * - args0->fileobj will be released
 */
static void fileobj_do_pageio(void *args0)
{
	struct pageio_args *args = args0;
	struct fileobj *obj = args->fileobj;
	off_t off = args->objoff;
	size_t pgsize = args->pgsize;
	struct mcs_lock_node mcs_node;
	int hash = fileobj_page_hash_result(off);
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	fileobj_do_pageio_body_result(
		obj, to_memobj(obj)->flags, obj->handle, off, pgsize,
		&obj->page_hash_locks[hash], &mcs_node,
		fileobj_hash_lock_bridge, fileobj_hash_unlock_bridge,
		fileobj_hash_lookup_bridge, fileobj_page_mode_bridge,
		fileobj_page_set_mode_bridge, fileobj_page_phys_bridge,
		fileobj_pageio_zero_bridge, fileobj_pageio_read_bridge,
		fileobj_pageio_schedule_bridge, fileobj_pageio_pause_bridge,
		fileobj_pageio_log_bridge, fileobj_pageio_panic_bridge);
#else
	struct page *page;
	ihk_mc_user_context_t ctx;
	ssize_t ss;
	int attempts = 0;

	mcs_lock_lock(&obj->page_hash_locks[hash], &mcs_node);
	page = __fileobj_page_hash_lookup(obj, hash, off);
	if (!page) {
		goto out;
	}

	while (page->mode == PM_PAGEIO) {
		mcs_lock_unlock(&obj->page_hash_locks[hash], &mcs_node);
		++attempts;
		if (fileobj_pageio_should_schedule_result(attempts)) {
			dkprintf("%s: %s:%lu PM_PAGEIO loop %d -> schedule()\n",
				__func__, to_memobj(obj)->path, off, attempts);
			schedule();
		}
		cpu_pause();
		mcs_lock_lock(&obj->page_hash_locks[hash], &mcs_node);
	}

	if (page->mode == PM_WILL_PAGEIO) {
		if (fileobj_pageio_zero_result(to_memobj(obj)->flags)) {
			void *virt = phys_to_virt(page_to_phys(page));
			memset(virt, 0, PAGE_SIZE);
#ifdef PROFILE_ENABLE
			profile_event_add(PROFILE_page_fault_file_clr, PAGE_SIZE);
#endif // PROFILE_ENABLE
		}
		else {
			page->mode = PM_PAGEIO;
			mcs_lock_unlock(&obj->page_hash_locks[hash], &mcs_node);

			ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_READ);
			ihk_mc_syscall_set_arg1(&ctx, obj->handle);
			ihk_mc_syscall_set_arg2(&ctx, off);
			ihk_mc_syscall_set_arg3(&ctx, pgsize);
			ihk_mc_syscall_set_arg4(&ctx, page_to_phys(page));

			dkprintf("%s: __NR_mmap for handle 0x%lx\n",
					__FUNCTION__, obj->handle);
			ss = syscall_generic_forwarding(__NR_mmap, &ctx);

			mcs_lock_lock(&obj->page_hash_locks[hash], &mcs_node);
			if (page->mode != PM_PAGEIO) {
				kprintf("fileobj_do_pageio(%p,%lx,%lx):"
						"invalid mode %x\n",
						obj, off, pgsize, page->mode);
				panic("fileobj_do_pageio:invalid page mode");
			}

			page->mode = fileobj_pageio_mode_after_read_result(ss, pgsize);
			if (page->mode == PM_PAGEIO_EOF) {
				dkprintf("fileobj_do_pageio(%p,%lx,%lx):EOF? %ld\n",
						obj, off, pgsize, ss);
				goto out;
			}
			else if (page->mode == PM_PAGEIO_ERROR) {
				kprintf("fileobj_do_pageio(%p,%lx,%lx):"
						"read failed. %ld\n",
						obj, off, pgsize, ss);
				goto out;
			}
		}

		page->mode = PM_DONE_PAGEIO;
	}
out:
	mcs_lock_unlock(&obj->page_hash_locks[hash], &mcs_node);
#endif
	memobj_unref(&obj->memobj);		/* got fileobj_get_page() */
	kfree_tracked(args0, __FILE__, __LINE__);
	dkprintf("fileobj_do_pageio(%p,%lx,%lx):\n", obj, off, pgsize);
	return;
}

static int fileobj_get_page(struct memobj *memobj, off_t off,
               int p2align, uintptr_t *physp, unsigned long *pflag, uintptr_t virt_addr)
{
	struct thread *proc = get_this_cpu_local_var()->current;
	struct fileobj *obj = to_fileobj(memobj);
	int error = -1;
	uintptr_t phys = -1;
#ifndef MCKERNEL_RUST_OBJECT_HELPERS
	void *virt = NULL;
	struct page *page;
#endif
	struct mcs_lock_node mcs_node;
	int hash = fileobj_page_hash_result(off);
#ifndef MCKERNEL_RUST_OBJECT_HELPERS
	int action;
#endif

	dkprintf("fileobj_get_page(%p,%lx,%x,%x,%p)\n", obj, off, p2align, virt_addr, physp);
	error = fileobj_validate_p2align_result(p2align);
	if (error)
		return error;

#ifdef PROFILE_ENABLE
	profile_event_add(PROFILE_page_fault_file, PAGE_SIZE);
#endif // PROFILE_ENABLE

	if (fileobj_premap_zerofill_result(memobj->flags)) {
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
		error = fileobj_get_premap_body_result(
			obj, memobj->pages, off, p2align, virt_addr, physp,
			IHK_MC_AP_NOWAIT | IHK_MC_AP_USER,
			fileobj_alloc_pages_bridge, fileobj_memzero_bridge,
			fileobj_page_array_at_bridge,
			fileobj_page_array_cmpxchg_bridge,
			fileobj_free_pages_bridge, fileobj_virt_phys_bridge,
			fileobj_rss_add_bridge, fileobj_get_log_bridge);
		goto out_nolock;
#else
		int page_ind = fileobj_premap_page_index_result(off);

		if (!memobj->pages[page_ind]) {
			virt = _ihk_mc_alloc_aligned_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT | IHK_MC_AP_USER, -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);

			if (!virt) {
				error = -ENOMEM;
				kprintf("fileobj_get_page(%p,%lx,%x,%x,%x,%p):"
						"alloc failed. %d\n",
						obj, off, p2align, virt_addr, physp,
						error);
				goto out_nolock;
			}

			/* Update the array but see if someone did it already and use
			 * that if so */
			memset(virt, 0, PAGE_SIZE);
			if (atomic_cmpxchg_ptr(&memobj->pages[page_ind],
					       NULL, virt) != NULL) {
				_ihk_mc_free_pages(virt, 1, IHK_MC_PG_USER, __FILE__, __LINE__);
			}
			else {
				dkprintf("%s: MF_ZEROFILL: off: %lu -> 0x%lx allocated\n",
						__FUNCTION__, off, virt_to_phys(virt));
				// Track change in memobj->pages[] for MF_PREMAP pages (!MPOL_SHM_PREMAP case)
				dkprintf("%lx+,%s: MF_PREMAP&&!MPOL_SHM_PREMAP,memory_stat_rss_add,phys=%lx,size=%ld,pgsize=%ld\n", virt_to_phys(virt), __FUNCTION__, virt_to_phys(virt), PAGE_SIZE, PAGE_SIZE);
				rusage_memory_stat_mapped_file_add(PAGE_SIZE, PAGE_SIZE);
			}
		}

		virt = memobj->pages[page_ind];
		error = 0;
		*physp = virt_to_phys(virt);
		dkprintf("%s: MF_ZEROFILL: off: %lu -> 0x%lx resolved\n",
				__FUNCTION__, off, virt_to_phys(virt));
		goto out_nolock;
#endif
		}

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	error = fileobj_get_regular_body_result(
		obj, memobj->flags, off, p2align, virt_addr, physp, proc,
		fileobj_do_pageio, &obj->page_hash_locks[hash], &mcs_node,
		sizeof(struct pageio_args), IHK_MC_AP_NOWAIT,
		fileobj_hash_lock_bridge, fileobj_hash_unlock_bridge,
		fileobj_hash_lookup_bridge, fileobj_alloc_bridge,
		fileobj_kfree_bridge, fileobj_alloc_pages_bridge,
		fileobj_virt_phys_bridge, fileobj_phys_to_page_insert_bridge,
		fileobj_page_mode_bridge, fileobj_page_offset_set_bridge,
		fileobj_page_count_set_bridge, fileobj_page_mapped_set_bridge,
		fileobj_page_hash_insert_bridge, fileobj_page_set_mode_bridge,
		fileobj_ref_bridge, fileobj_pageio_args_set_bridge,
		fileobj_pgio_set_bridge, fileobj_page_count_inc_bridge,
		fileobj_page_phys_bridge, fileobj_page_count_bridge,
		fileobj_page_remove_bridge, fileobj_phys_to_virt_bridge,
		fileobj_page_unmap_bridge, fileobj_free_pages_bridge,
		fileobj_get_regular_log_bridge,
		fileobj_get_regular_panic_bridge);
	return error;
#else
	mcs_lock_lock(&obj->page_hash_locks[hash], &mcs_node);
	page = __fileobj_page_hash_lookup(obj, hash, off);
	action = fileobj_get_page_action_result(!!page,
			page ? page->mode : PM_NONE, &error);
	if (action == FILEOBJ_PAGE_ACTION_START_IO) {
		struct pageio_args *args;
		args = kmalloc_tracked(sizeof(*args), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!args) {
			error = -ENOMEM;
			kprintf("fileobj_get_page(%p,%lx,%x,%x,%p):"
					"kmalloc failed. %d\n",
					obj, off, p2align, virt_addr, physp, error);
			goto out;
		}

		if (!page) {
			int npages = fileobj_alloc_npages_result(p2align);

			virt = _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, fileobj_alloc_flags_result(to_memobj(obj)->flags), -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
			if (!virt) {
				error = -ENOMEM;
				kprintf("fileobj_get_page(%p,%lx,%x,%x,%p):"
						"alloc failed. %d\n",
						obj, off, p2align, virt_addr, physp,
						error);
				kfree_tracked(args, __FILE__, __LINE__);
				goto out;
			}
			phys = virt_to_phys(virt);
			page = phys_to_page_insert_hash(phys);
			// Track change in page->count for !MF_PREMAP pages. 
			// Add when setting the PTE for a page with count of one in ihk_mc_pt_set_range().
			dkprintf("%s: phys_to_page_insert_hash(),phys=%lx,virt=%lx,size=%lx,pgsize=%lx\n", __FUNCTION__, phys, virt, fileobj_alloc_size_result(npages), PAGE_SIZE);

			if (page->mode != PM_NONE) {
				panic("fileobj_get_page:invalid new page");
			}
			page->offset = off;
			ihk_atomic_set(&page->count, 1);
			ihk_atomic64_set(&page->mapped, 0);
			__fileobj_page_hash_insert(obj, page, hash);
			page->mode = fileobj_new_page_mode_result();
		}

		memobj_ref(&obj->memobj);

		args->fileobj = obj;
		args->objoff = off;
		args->pgsize = fileobj_pageio_pgsize_result(p2align);

		proc->pgio_fp = &fileobj_do_pageio;
		proc->pgio_arg = args;

		goto out;
	}
	else if (action == FILEOBJ_PAGE_ACTION_MAP_DONE) {
		page->mode = fileobj_mapped_mode_result();
		dkprintf("%s: PM_DONE_PAGEIO-->PM_MAPPED,obj=%lx,off=%lx,phys=%lx\n", __FUNCTION__, obj, off, page_to_phys(page));
	}
	else if (action == FILEOBJ_PAGE_ACTION_ERROR) {
		goto pageio_error;
	}

	ihk_atomic_inc(&page->count);
	dkprintf("%s: mode=%d,count=%d,obj=%lx,off=%lx,phys=%lx\n", __FUNCTION__, page->mode, page->count, obj, off, page_to_phys(page));

	error = 0;
	*physp = page_to_phys(page);
out:
	mcs_lock_unlock(&obj->page_hash_locks[hash], &mcs_node);
#endif
out_nolock:
	dkprintf("fileobj_get_page(%p,%lx,%x,%x,%p): %d %lx\n",
			obj, off, p2align, virt_addr, physp, error, phys);
	return error;

#ifndef MCKERNEL_RUST_OBJECT_HELPERS
pageio_error:
	__fileobj_page_hash_remove(page);
	virt = phys_to_virt(page_to_phys(page));
	if (page_unmap(page)) {
		_ihk_mc_free_pages(virt, 1, IHK_MC_PG_USER, __FILE__, __LINE__);
		kfree_tracked(page, __FILE__, __LINE__);
	}

	goto out;
#endif
}

static int fileobj_flush_page(struct memobj *memobj, uintptr_t phys,
		size_t pgsize)
{
	struct fileobj *obj = to_fileobj(memobj);
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	dkprintf("%s: phys=%lx,to_memobj(obj)->flags=%x,memobj->flags=%x,page=%p\n",
		 __FUNCTION__, phys, to_memobj(obj)->flags, memobj->flags,
		 phys_to_page(phys));
	return fileobj_flush_page_body_result(
		memobj, obj, to_memobj(obj)->flags, obj->handle, phys, pgsize,
		fileobj_phys_to_page_bridge, fileobj_page_offset_bridge,
		fileobj_write_bridge, fileobj_log_bridge);
#else
	struct page *page;
	ihk_mc_user_context_t ctx;
	ssize_t ss;

	dkprintf("%s: phys=%lx,to_memobj(obj)->flags=%x,memobj->flags=%x,page=%p\n", __FUNCTION__, phys, to_memobj(obj)->flags, memobj->flags, phys_to_page(phys));
	if (fileobj_flush_skip_result(to_memobj(obj)->flags, 1)) {
		return 0;
	}

	page = phys_to_page(phys);
	if (fileobj_flush_skip_result(to_memobj(obj)->flags, !!page)) {
		kprintf("%s: warning: tried to flush non-existing page for phys addr: 0x%lx\n", 
			__FUNCTION__, phys);
		return 0;
	}

	ihk_mc_syscall_set_arg0(&ctx, PAGER_REQ_WRITE);
	ihk_mc_syscall_set_arg1(&ctx, obj->handle);
	ihk_mc_syscall_set_arg2(&ctx, page->offset);
	ihk_mc_syscall_set_arg3(&ctx, pgsize);
	ihk_mc_syscall_set_arg4(&ctx, phys);

	dkprintf("%s: syscall_generic_forwarding\n", __FUNCTION__);
	ss = syscall_generic_forwarding(__NR_mmap, &ctx);
	if (ss != pgsize) {
		dkprintf("fileobj_flush_page(%p,%lx,%lx): %ld (%lx)\n",
				memobj, phys, pgsize, ss, ss);
		/* through */
	}

	return 0;
#endif
}

static int fileobj_invalidate_page(struct memobj *memobj, uintptr_t phys,
		size_t pgsize)
{
#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	dkprintf("fileobj_invalidate_page(%p,%#lx,%#lx)\n",
			memobj, phys, pgsize);
	return fileobj_invalidate_page_body_result(memobj, phys, pgsize,
						   fileobj_log_bridge);
#else
	dkprintf("fileobj_invalidate_page(%p,%#lx,%#lx)\n",
			memobj, phys, pgsize);

	/* TODO: keep track of reverse mappings so that invalidation
	 * can be performed */
	kprintf("%s: WARNING: file mapping invalidation not supported\n",
		__FUNCTION__);
	return 0;
#endif
}

static int fileobj_lookup_page(struct memobj *memobj, off_t off,
		int p2align, uintptr_t *physp, unsigned long *pflag)
{
	struct fileobj *obj = to_fileobj(memobj);
	int error = -1;
#ifndef MCKERNEL_RUST_OBJECT_HELPERS
	struct page *page;
#endif
	struct mcs_lock_node mcs_node;
	int hash = fileobj_page_hash_result(off);

	dkprintf("fileobj_lookup_page(%p,%lx,%x,%p)\n", obj, off, p2align, physp);

#ifdef MCKERNEL_RUST_OBJECT_HELPERS
	(void)pflag;
	error = fileobj_lookup_page_body_result(
		obj, off, p2align, physp, &obj->page_hash_locks[hash],
		&mcs_node, fileobj_hash_lock_bridge,
		fileobj_hash_unlock_bridge, fileobj_hash_lookup_bridge,
		fileobj_page_phys_bridge);
	dkprintf("fileobj_lookup_page(%p,%lx,%x,%p): %d \n",
			obj, off, p2align, physp, error);
	return error;
#else
	error = fileobj_validate_p2align_result(p2align);
	if (error)
		return error;

	mcs_lock_lock(&obj->page_hash_locks[hash], &mcs_node);

	page = __fileobj_page_hash_lookup(obj, hash, off);
	error = fileobj_lookup_page_error_result(!!page);
	if (error) {
		goto out;
	}

	*physp = page_to_phys(page);
	error = 0;

out:
	mcs_lock_unlock(&obj->page_hash_locks[hash], &mcs_node);

	dkprintf("fileobj_lookup_page(%p,%lx,%x,%p): %d \n",
			obj, off, p2align, physp, error);
	return error;
#endif
}
