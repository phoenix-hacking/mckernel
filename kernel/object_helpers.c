/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <elfcore.h>
#include <memobj.h>
#include <mman.h>
#include <object_helpers.h>
#include <page.h>
#include <pager.h>
#include <process.h>
#include <registers.h>
#include <shm.h>
#include <string.h>
#include <syscall.h>
#include <sysfs.h>
#include <sysfs_msg.h>

#ifndef MCKERNEL_RUST_OBJECT_HELPERS

#define FILEOBJ_PAGE_HASH_MASK 511
#define SYSFS_INIT_AP_NOWAIT 0x000002
#define PROCFS_INT_MAX ((int)((unsigned int)~0 >> 1))

struct mckernel_procfs_buffer {
	unsigned long next_pa;
	unsigned long pos;
	unsigned long size;
	char buf[0];
};

int memobj_unref_should_free_result(int refcnt)
{
	return refcnt == 0;
}

int memobj_op_present_result(uintptr_t op)
{
	return op != 0;
}

int memobj_missing_page_op_result(void)
{
	return -ENXIO;
}

uintptr_t memobj_missing_copy_page_result(void)
{
	return (uintptr_t)-ENXIO;
}

int memobj_default_page_op_result(void)
{
	return 0;
}

int memobj_has_pager_flags_result(unsigned int flags)
{
	return !!(flags & MF_HAS_PAGER);
}

int memobj_is_removable_flags_result(unsigned int flags)
{
	return !!(flags & MF_IS_REMOVABLE);
}

int memobj_flushable_page_result(int has_page, int page_in_memobj)
{
	return has_page && page_in_memobj;
}

int memobj_flushable_obj_result(int has_memobj, unsigned int flags)
{
	return has_memobj && !(flags & (MF_ZEROFILL | MF_PRIVATE));
}

int memobj_is_freeable_result(int has_memobj, unsigned int flags)
{
	return !has_memobj || !(flags & MF_XPMEM);
}

int memobj_callable_remap_file_pages_result(int has_memobj,
					    unsigned int flags)
{
	return has_memobj && (flags & MF_REMAP_FILE_PAGES);
}

int memobj_get_page(struct memobj *obj, off_t off, int p2align,
		    uintptr_t *physp, unsigned long *pflag,
		    uintptr_t virt_addr)
{
	if (memobj_op_present_result((uintptr_t)obj->ops->get_page)) {
		return (*obj->ops->get_page)(obj, off, p2align, physp, pflag,
					     virt_addr);
	}
	return memobj_missing_page_op_result();
}

uintptr_t memobj_copy_page(struct memobj *obj, uintptr_t orgphys, int p2align)
{
	if (memobj_op_present_result((uintptr_t)obj->ops->copy_page)) {
		return (*obj->ops->copy_page)(obj, orgphys, p2align);
	}
	return memobj_missing_copy_page_result();
}

int memobj_flush_page(struct memobj *obj, uintptr_t phys, size_t pgsize)
{
	if (memobj_op_present_result((uintptr_t)obj->ops->flush_page)) {
		return (*obj->ops->flush_page)(obj, phys, pgsize);
	}
	return memobj_default_page_op_result();
}

int memobj_invalidate_page(struct memobj *obj, uintptr_t phys, size_t pgsize)
{
	if (memobj_op_present_result((uintptr_t)obj->ops->invalidate_page)) {
		return (*obj->ops->invalidate_page)(obj, phys, pgsize);
	}
	return memobj_default_page_op_result();
}

int memobj_lookup_page(struct memobj *obj, off_t off, int p2align,
		       uintptr_t *physp, unsigned long *pflag)
{
	if (memobj_op_present_result((uintptr_t)obj->ops->lookup_page)) {
		return (*obj->ops->lookup_page)(obj, off, p2align, physp,
						pflag);
	}
	return memobj_missing_page_op_result();
}

int memobj_update_page(struct memobj *obj, page_table_t pt,
		       struct page *orig_page, void *vaddr)
{
	if (memobj_op_present_result((uintptr_t)obj->ops->update_page)) {
		return (*obj->ops->update_page)(obj, pt, orig_page, vaddr);
	}
	return memobj_missing_page_op_result();
}

int memobj_has_pager(struct memobj *obj)
{
	return memobj_has_pager_flags_result(obj->flags);
}

int memobj_is_removable(struct memobj *obj)
{
	return memobj_is_removable_flags_result(obj->flags);
}

int is_flushable(struct page *page, struct memobj *memobj)
{
	if (!memobj_flushable_page_result(!!page,
					  page ? page_is_in_memobj(page) : 0))
		return 0;

	return memobj_flushable_obj_result(!!memobj,
					   memobj ? memobj->flags : 0);
}

int is_freeable(struct memobj *memobj)
{
	return memobj_is_freeable_result(!!memobj,
					 memobj ? memobj->flags : 0);
}

int is_callable_remap_file_pages(struct memobj *memobj)
{
	return memobj_callable_remap_file_pages_result(!!memobj,
						       memobj ? memobj->flags : 0);
}

int fileobj_page_hash_result(off_t off)
{
	return (off >> PAGE_SHIFT) & FILEOBJ_PAGE_HASH_MASK;
}

int fileobj_page_mode_valid_result(int mode)
{
	return (mode == PM_WILL_PAGEIO) || (mode == PM_PAGEIO) ||
		(mode == PM_DONE_PAGEIO) || (mode == PM_PAGEIO_EOF) ||
		(mode == PM_PAGEIO_ERROR) || (mode == PM_MAPPED);
}

int fileobj_lookup_ref_keep_result(int refcnt_after_inc)
{
	return refcnt_after_inc > 1;
}

int fileobj_create_base_flags_result(int mmap_flags)
{
	return MF_HAS_PAGER | MF_REG_FILE | MF_REMAP_FILE_PAGES |
		((mmap_flags & MAP_PRIVATE) ? MF_PRIVATE : 0);
}

int fileobj_apply_result_flags_result(int base_flags, int pager_flags)
{
	return base_flags | pager_flags;
}

int fileobj_status_from_flags_result(int flags)
{
	return (flags & MF_PREFETCH) ? MEMOBJ_TO_BE_PREFETCHED : MEMOBJ_READY;
}

int fileobj_hugetlbfs_result(int flags)
{
	return !!(flags & MF_HUGETLBFS);
}

int fileobj_premap_zerofill_result(int flags)
{
	return !!((flags & MF_PREMAP) && (flags & MF_ZEROFILL));
}

int fileobj_premap_npages_result(size_t size)
{
	return (int)((size + (PAGE_SIZE - 1)) >> PAGE_SHIFT);
}

int fileobj_validate_p2align_result(int p2align)
{
	return (p2align != PAGE_P2ALIGN) ? -ENOMEM : 0;
}

int fileobj_get_page_action_result(int has_page, int page_mode, int *errorp)
{
	*errorp = 0;

	if (!has_page || page_mode == PM_WILL_PAGEIO || page_mode == PM_PAGEIO) {
		*errorp = -ERESTART;
		return FILEOBJ_PAGE_ACTION_START_IO;
	}

	if (page_mode == PM_DONE_PAGEIO)
		return FILEOBJ_PAGE_ACTION_MAP_DONE;

	if (page_mode == PM_PAGEIO_EOF) {
		*errorp = -ERANGE;
		return FILEOBJ_PAGE_ACTION_ERROR;
	}

	if (page_mode == PM_PAGEIO_ERROR) {
		*errorp = -EIO;
		return FILEOBJ_PAGE_ACTION_ERROR;
	}

	return FILEOBJ_PAGE_ACTION_USE_EXISTING;
}

int fileobj_pageio_zero_result(int flags)
{
	return !!(flags & MF_ZEROFILL);
}

int fileobj_pageio_mode_after_read_result(ssize_t ssize, size_t pgsize)
{
	if (ssize == 0)
		return PM_PAGEIO_EOF;
	if (ssize != pgsize)
		return PM_PAGEIO_ERROR;
	return PM_DONE_PAGEIO;
}

int fileobj_flush_skip_result(int flags, int has_page)
{
	return (flags & MF_ZEROFILL) || !has_page;
}

int fileobj_initial_refcnt_result(void)
{
	return 1;
}

unsigned long fileobj_initial_sref_result(void)
{
	return 1;
}

int fileobj_premap_start_node_result(int nr_numa_nodes)
{
	return nr_numa_nodes / 2;
}

int fileobj_premap_next_node_result(int node, int nr_numa_nodes)
{
	++node;
	if (node == nr_numa_nodes)
		return nr_numa_nodes / 2;
	return node;
}

size_t fileobj_pages_bytes_result(int nr_pages)
{
	return nr_pages * sizeof(void *);
}

int fileobj_premap_page_index_result(off_t off)
{
	return off >> PAGE_SHIFT;
}

int fileobj_alloc_npages_result(int p2align)
{
	return 1 << p2align;
}

unsigned long fileobj_alloc_flags_result(int flags)
{
	return IHK_MC_AP_NOWAIT |
		((flags & MF_ZEROFILL) ? IHK_MC_AP_USER : 0);
}

size_t fileobj_alloc_size_result(int npages)
{
	return npages * PAGE_SIZE;
}

size_t fileobj_pageio_pgsize_result(int p2align)
{
	return PAGE_SIZE << p2align;
}

int fileobj_pageio_should_schedule_result(int attempts)
{
	return attempts > 49;
}

int fileobj_new_page_mode_result(void)
{
	return PM_WILL_PAGEIO;
}

int fileobj_mapped_mode_result(void)
{
	return PM_MAPPED;
}

int fileobj_path_present_result(unsigned long value)
{
	return value != 0;
}

int fileobj_invalid_page_count_result(int count)
{
	return count != 1;
}

int fileobj_should_free_hashed_page_result(int count, int page_unmap_result)
{
	return count == 1 && page_unmap_result;
}

int fileobj_premap_page_present_result(uintptr_t page)
{
	return page != 0;
}

int fileobj_lookup_page_error_result(int has_page)
{
	return has_page ? 0 : -1;
}

unsigned long fileobj_next_sref_result(unsigned long sref)
{
	return sref + 1;
}

int fileobj_premap_interleave_result(unsigned long mpol_flags)
{
	return !!(mpol_flags & MPOL_SHM_PREMAP);
}

int fileobj_flush_page_body_result(
	void *memobj, void *obj, int flags, uintptr_t handle, uintptr_t phys,
	size_t pgsize, fileobj_phys_to_page_fn_t phys_to_page_fn,
	fileobj_page_offset_fn_t page_offset_fn, fileobj_write_fn_t write_fn,
	fileobj_log_fn_t log_fn)
{
	void *page;
	ssize_t ss;

	if (!phys_to_page_fn || !page_offset_fn || !write_fn || !log_fn) {
		return -EINVAL;
	}

	if (fileobj_flush_skip_result(flags, 1)) {
		return 0;
	}

	page = phys_to_page_fn(phys);
	if (fileobj_flush_skip_result(flags, !!page)) {
		log_fn(FILEOBJ_LOG_FLUSH_MISSING_PAGE, memobj, obj, phys,
		       pgsize, 0);
		return 0;
	}

	ss = write_fn(handle, page_offset_fn(page), pgsize, phys);
	if (ss != (ssize_t)pgsize) {
		log_fn(FILEOBJ_LOG_FLUSH_SHORT_WRITE, memobj, obj, phys,
		       pgsize, ss);
	}

	return 0;
}

int fileobj_invalidate_page_body_result(void *memobj, uintptr_t phys,
					size_t pgsize,
					fileobj_log_fn_t log_fn)
{
	if (!log_fn) {
		return -EINVAL;
	}

	log_fn(FILEOBJ_LOG_INVALIDATE_UNSUPPORTED, memobj, NULL, phys,
	       pgsize, 0);
	return 0;
}

int fileobj_lookup_page_body_result(
	void *obj, off_t off, int p2align, uintptr_t *physp, void *lock,
	void *lock_node, fileobj_lock_fn_t lock_fn,
	fileobj_unlock_fn_t unlock_fn, fileobj_lookup_fn_t lookup_fn,
	fileobj_page_phys_fn_t page_phys_fn)
{
	int error;
	int hash;
	void *page;

	if (!obj || !physp || !lock || !lock_node || !lock_fn || !unlock_fn ||
	    !lookup_fn || !page_phys_fn) {
		return -EINVAL;
	}

	hash = fileobj_page_hash_result(off);
	error = fileobj_validate_p2align_result(p2align);
	if (error) {
		return error;
	}

	lock_fn(lock, lock_node);
	page = lookup_fn(obj, hash, off);
	error = fileobj_lookup_page_error_result(!!page);
	if (!error) {
		*physp = page_phys_fn(page);
	}
	unlock_fn(lock, lock_node);

	return error;
}

void *fileobj_obj_list_lookup_body_result(
	uintptr_t handle, void *list_head,
	fileobj_list_first_fn_t first_fn,
	fileobj_list_next_fn_t next_fn,
	fileobj_handle_fn_t handle_fn,
	fileobj_ref_fn_t ref_fn,
	fileobj_dec_fn_t dec_fn)
{
	void *obj;

	if (!list_head || !first_fn || !next_fn || !handle_fn || !ref_fn ||
	    !dec_fn) {
		return NULL;
	}

	obj = first_fn(list_head);
	while (obj) {
		if (handle_fn(obj) == handle) {
			if (fileobj_lookup_ref_keep_result(ref_fn(obj))) {
				return obj;
			}
			dec_fn(obj);
		}
		obj = next_fn(list_head, obj);
	}

	return NULL;
}

int fileobj_create_publish_body_result(
	void *obj, int is_new, int mmap_flags, int pager_flags,
	size_t result_size, fileobj_ptr_void_fn_t list_insert_fn,
	fileobj_size_set_fn_t size_set_fn,
	fileobj_int_set_fn_t flags_set_fn,
	fileobj_int_set_fn_t status_set_fn,
	fileobj_int_set_fn_t refcnt_set_fn,
	fileobj_ulong_get_fn_t sref_get_fn,
	fileobj_ulong_set_fn_t sref_set_fn)
{
	int flags;

	if (!obj || !list_insert_fn || !size_set_fn || !flags_set_fn ||
	    !status_set_fn || !refcnt_set_fn || !sref_get_fn ||
	    !sref_set_fn) {
		return -EINVAL;
	}

	if (is_new) {
		flags = fileobj_apply_result_flags_result(
			fileobj_create_base_flags_result(mmap_flags),
			pager_flags);
		list_insert_fn(obj);
		size_set_fn(obj, result_size);
		flags_set_fn(obj, flags);
		status_set_fn(obj, fileobj_status_from_flags_result(flags));
		refcnt_set_fn(obj, fileobj_initial_refcnt_result());
		sref_set_fn(obj, fileobj_initial_sref_result());
	} else {
		sref_set_fn(obj, fileobj_next_sref_result(sref_get_fn(obj)));
	}

	return 0;
}

int fileobj_create_path_body_result(
	void *obj, int path_first, const void *path_src, size_t path_len,
	unsigned long alloc_flags, fileobj_alloc_fn_t alloc_fn,
	fileobj_copy_fn_t copy_fn, fileobj_ptr_set_fn_t path_set_fn,
	fileobj_create_log_fn_t log_fn)
{
	void *path;

	if (!obj || !alloc_fn || !copy_fn || !path_set_fn || !log_fn) {
		return -EINVAL;
	}

	if (!fileobj_path_present_result((unsigned long)path_first)) {
		return 0;
	}

	if (!path_src || !path_len) {
		return -EINVAL;
	}

	path = alloc_fn(path_len, alloc_flags);
	if (!path) {
		log_fn(FILEOBJ_CREATE_LOG_PATH_ALLOC_FAILED, obj, path_src,
		       (long)path_len);
		return -ENOMEM;
	}

	path_set_fn(obj, path);
	copy_fn(path, path_src, path_len);
	return 0;
}

int fileobj_create_premap_body_result(
	void *obj, int flags, size_t result_size, unsigned long mpol_flags,
	int nr_numa_nodes, uintptr_t virt_addr, unsigned long alloc_flags,
	fileobj_alloc_fn_t alloc_fn, fileobj_ptr_set_fn_t pages_set_fn,
	fileobj_int_set_fn_t nr_pages_set_fn,
	fileobj_memzero_fn_t zero_fn,
	fileobj_alloc_pages_node_fn_t alloc_pages_node_fn,
	fileobj_page_array_set_fn_t page_set_fn,
	fileobj_rss_add_fn_t rss_add_fn,
	fileobj_create_premap_log_fn_t log_fn)
{
	int nr_pages;
	int node;
	void *pages;

	if (!obj || !alloc_fn || !pages_set_fn || !nr_pages_set_fn ||
	    !zero_fn || !alloc_pages_node_fn || !page_set_fn ||
	    !rss_add_fn || !log_fn) {
		return -EINVAL;
	}

	if (!fileobj_premap_zerofill_result(flags)) {
		return 0;
	}

	nr_pages = fileobj_premap_npages_result(result_size);
	node = fileobj_premap_start_node_result(nr_numa_nodes);
	log_fn(FILEOBJ_CREATE_LOG_PREMAP_START, obj, NULL, node);

	pages = alloc_fn(fileobj_pages_bytes_result(nr_pages), alloc_flags);
	if (!pages) {
		log_fn(FILEOBJ_CREATE_LOG_PREMAP_ARRAY_ALLOC_FAILED, obj, NULL,
		       0);
		return 0;
	}

	pages_set_fn(obj, pages);
	nr_pages_set_fn(obj, nr_pages);
	zero_fn(pages, fileobj_pages_bytes_result(nr_pages));

	if (fileobj_premap_interleave_result(mpol_flags)) {
		int j;

		for (j = 0; j < nr_pages; ++j) {
			void *page = alloc_pages_node_fn(1, PAGE_P2ALIGN,
							 alloc_flags, node,
							 virt_addr);
			if (!page) {
				log_fn(FILEOBJ_CREATE_LOG_PREMAP_PAGE_ALLOC_FAILED,
				       obj, NULL, j);
				return 0;
			}
			page_set_fn(pages, j, page);
			log_fn(FILEOBJ_CREATE_LOG_PREMAP_RSS_ADD, obj, page,
			       PAGE_SIZE);
			rss_add_fn(PAGE_SIZE, PAGE_SIZE);
			zero_fn(page, PAGE_SIZE);
			node = fileobj_premap_next_node_result(node,
							       nr_numa_nodes);
		}
		log_fn(FILEOBJ_CREATE_LOG_PREMAP_INTERLEAVED_DONE, obj, NULL,
		       nr_pages);
	}

	return 0;
}

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
	fileobj_get_log_fn_t log_fn)
{
	int page_ind;
	void *virt;
	uintptr_t phys;

	if (!obj || !pages || !physp || !alloc_pages_fn || !zero_fn ||
	    !page_at_fn || !cmpxchg_fn || !free_pages_fn || !phys_fn ||
	    !rss_add_fn || !log_fn) {
		return -EINVAL;
	}

	page_ind = fileobj_premap_page_index_result(off);
	virt = page_at_fn(pages, page_ind);
	if (!virt) {
		void *new_virt = alloc_pages_fn(1, alloc_flags, virt_addr);

		if (!new_virt) {
			log_fn(FILEOBJ_GET_LOG_PREMAP_ALLOC_FAILED, obj, off,
			       p2align, virt_addr, (uintptr_t)physp, NULL, 0,
			       -ENOMEM);
			return -ENOMEM;
		}

		zero_fn(new_virt, PAGE_SIZE);
		virt = cmpxchg_fn(pages, page_ind, NULL, new_virt);
		if (virt) {
			free_pages_fn(new_virt, 1);
		}
		else {
			virt = new_virt;
			phys = phys_fn(virt);
			log_fn(FILEOBJ_GET_LOG_PREMAP_ALLOCATED, obj, off,
			       p2align, virt_addr, (uintptr_t)physp, virt,
			       phys, 0);
			log_fn(FILEOBJ_GET_LOG_PREMAP_RSS_ADD, obj, off,
			       p2align, virt_addr, (uintptr_t)physp, virt,
			       phys, PAGE_SIZE);
			rss_add_fn(PAGE_SIZE, PAGE_SIZE);
		}
	}

	virt = page_at_fn(pages, page_ind);
	phys = phys_fn(virt);
	*physp = phys;
	log_fn(FILEOBJ_GET_LOG_PREMAP_RESOLVED, obj, off, p2align, virt_addr,
	       (uintptr_t)physp, virt, phys, 0);
	return 0;
}

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
	fileobj_get_regular_panic_fn_t panic_fn)
{
	int hash;
	int action;
	int error = -1;
	void *page;
	void *virt = NULL;
	uintptr_t phys_state = (uintptr_t)-1;
	uintptr_t page_phys;

	if (!obj || !physp || !thread || !pageio_fn || !lock || !lock_node ||
	    !lock_fn || !unlock_fn || !lookup_fn || !alloc_fn || !free_fn ||
	    !alloc_pages_fn || !phys_fn || !page_insert_lookup_fn ||
	    !page_mode_fn || !page_offset_set_fn || !page_count_set_fn ||
	    !page_mapped_set_fn || !hash_insert_fn || !page_mode_set_fn ||
	    !memobj_ref_fn || !args_set_fn || !pgio_set_fn ||
	    !page_count_inc_fn || !page_phys_fn || !page_count_fn ||
	    !page_remove_fn || !phys_to_virt_fn || !page_unmap_fn ||
	    !free_pages_fn || !log_fn || !panic_fn) {
		return -EINVAL;
	}

	hash = fileobj_page_hash_result(off);
	lock_fn(lock, lock_node);
	page = lookup_fn(obj, hash, off);
	action = fileobj_get_page_action_result(!!page,
						page ? page_mode_fn(page) : PM_NONE,
						&error);
	if (action == FILEOBJ_PAGE_ACTION_START_IO) {
		void *args = alloc_fn(args_size, args_alloc_flags);

		if (!args) {
			error = -ENOMEM;
			log_fn(FILEOBJ_GET_LOG_KMALLOC_FAILED, obj, off, p2align,
			       virt_addr, (uintptr_t)physp, NULL, phys_state,
			       (uintptr_t)error, 0, 0, 0);
			goto out;
		}

		if (!page) {
			int npages = fileobj_alloc_npages_result(p2align);

			virt = alloc_pages_fn(npages,
					      fileobj_alloc_flags_result(flags),
					      virt_addr);
			if (!virt) {
				error = -ENOMEM;
				log_fn(FILEOBJ_GET_LOG_ALLOC_FAILED, obj, off,
				       p2align, virt_addr, (uintptr_t)physp,
				       NULL, phys_state, (uintptr_t)error, 0, 0,
				       0);
				free_fn(args);
				goto out;
			}

			phys_state = phys_fn(virt);
			page = page_insert_lookup_fn(phys_state);
			log_fn(FILEOBJ_GET_LOG_NEW_PAGE, obj, off, p2align,
			       virt_addr, (uintptr_t)physp, page, phys_state,
			       (uintptr_t)virt,
			       fileobj_alloc_size_result(npages), 0, 0);
			{
				int mode = page_mode_fn(page);

				if (mode != PM_NONE) {
					panic_fn(obj, off, page, mode);
				}
			}
			page_offset_set_fn(page, off);
			page_count_set_fn(page, 1);
			page_mapped_set_fn(page, 0);
			hash_insert_fn(obj, page, hash);
			page_mode_set_fn(page, fileobj_new_page_mode_result());
		}

		memobj_ref_fn(obj);
		args_set_fn(args, obj, off, fileobj_pageio_pgsize_result(p2align));
		pgio_set_fn(thread, pageio_fn, args);
		goto out;
	}
	else if (action == FILEOBJ_PAGE_ACTION_MAP_DONE) {
		page_mode_set_fn(page, fileobj_mapped_mode_result());
		page_phys = page_phys_fn(page);
		log_fn(FILEOBJ_GET_LOG_MAP_DONE, obj, off, p2align, virt_addr,
		       (uintptr_t)physp, page, page_phys, 0, 0,
		       fileobj_mapped_mode_result(), page_count_fn(page));
	}
	else if (action == FILEOBJ_PAGE_ACTION_ERROR) {
		page_remove_fn(page);
		virt = phys_to_virt_fn(page_phys_fn(page));
		if (page_unmap_fn(page)) {
			free_pages_fn(virt, 1);
			free_fn(page);
		}
		goto out;
	}

	page_count_inc_fn(page);
	page_phys = page_phys_fn(page);
	log_fn(FILEOBJ_GET_LOG_USE_PAGE, obj, off, p2align, virt_addr,
	       (uintptr_t)physp, page, page_phys, 0, 0, page_mode_fn(page),
	       page_count_fn(page));
	error = 0;
	*physp = page_phys;
out:
	unlock_fn(lock, lock_node);
	log_fn(FILEOBJ_GET_LOG_RETURN, obj, off, p2align, virt_addr,
	       (uintptr_t)physp, page, phys_state, (uintptr_t)error, 0, 0, 0);
	return error;
}

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
	fileobj_pageio_panic_fn_t panic_fn)
{
	int hash;
	int attempts = 0;
	void *page;

	if (!obj || !lock || !lock_node || !lock_fn || !unlock_fn ||
	    !lookup_fn || !page_mode_fn || !page_set_mode_fn ||
	    !page_phys_fn || !zero_fn || !read_fn || !schedule_fn ||
	    !pause_fn || !log_fn || !panic_fn) {
		return -EINVAL;
	}

	hash = fileobj_page_hash_result(off);
	lock_fn(lock, lock_node);
	page = lookup_fn(obj, hash, off);
	if (!page) {
		unlock_fn(lock, lock_node);
		return 0;
	}

	while (page_mode_fn(page) == PM_PAGEIO) {
		unlock_fn(lock, lock_node);
		++attempts;
		if (fileobj_pageio_should_schedule_result(attempts)) {
			log_fn(FILEOBJ_LOG_PAGEIO_SCHEDULE, obj, off,
			       pgsize, attempts);
			schedule_fn();
		}
		pause_fn();
		lock_fn(lock, lock_node);
	}

	if (page_mode_fn(page) == PM_WILL_PAGEIO) {
		if (fileobj_pageio_zero_result(flags)) {
			zero_fn(page_phys_fn(page));
		} else {
			ssize_t ss;
			uintptr_t phys;
			int mode;

			page_set_mode_fn(page, PM_PAGEIO);
			phys = page_phys_fn(page);
			unlock_fn(lock, lock_node);
			ss = read_fn(handle, off, pgsize, phys);
			lock_fn(lock, lock_node);

			mode = page_mode_fn(page);
			if (mode != PM_PAGEIO) {
				panic_fn(obj, off, pgsize, mode);
				unlock_fn(lock, lock_node);
				return -EINVAL;
			}

			mode = fileobj_pageio_mode_after_read_result(ss, pgsize);
			page_set_mode_fn(page, mode);
			if (mode == PM_PAGEIO_EOF) {
				log_fn(FILEOBJ_LOG_PAGEIO_EOF, obj, off,
				       pgsize, ss);
				unlock_fn(lock, lock_node);
				return 0;
			}
			if (mode == PM_PAGEIO_ERROR) {
				log_fn(FILEOBJ_LOG_PAGEIO_READ_ERROR, obj, off,
				       pgsize, ss);
				unlock_fn(lock, lock_node);
				return 0;
			}
		}

		page_set_mode_fn(page, PM_DONE_PAGEIO);
	}

	unlock_fn(lock, lock_node);
	return 0;
}

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
	fileobj_free_log_fn_t log_fn)
{
	int error;

	if (!obj || !list_lock || !lock_node || !lock_fn || !unlock_fn ||
	    !list_remove_fn || !page_first_fn || !page_remove_fn ||
	    !page_phys_fn || !phys_to_virt_fn || !page_count_fn ||
	    !page_unmap_fn || !free_pages_fn || !rss_sub_fn || !free_fn ||
	    !release_fn || !page_at_fn || !log_fn) {
		return -EINVAL;
	}

	lock_fn(list_lock, lock_node);
	list_remove_fn(obj);
	unlock_fn(list_lock, lock_node);

	for (;;) {
		void *page;
		uintptr_t phys;
		void *virt;
		int count;

		page = page_first_fn(obj);
		if (!page) {
			break;
		}

		page_remove_fn(page);
		phys = page_phys_fn(page);
		virt = phys_to_virt_fn(phys);
		count = page_count_fn(page);
		if (fileobj_invalid_page_count_result(count)) {
			log_fn(FILEOBJ_LOG_FREE_INVALID_COUNT, obj, page,
			       phys, count, flags);
		}
		else if (fileobj_should_free_hashed_page_result(
				 count, page_unmap_fn(page))) {
			free_pages_fn(virt, 1);
			rss_sub_fn(PAGE_SIZE, PAGE_SIZE);
			log_fn(FILEOBJ_LOG_FREE_RSS_SUB, obj, page, phys,
			       PAGE_SIZE, flags);
			free_fn(page);
		}
	}

	if (fileobj_premap_zerofill_result(flags)) {
		int i;

		for (i = 0; i < nr_pages; ++i) {
			void *page = page_at_fn(pages, i);

			if (fileobj_premap_page_present_result(
				    (uintptr_t)page)) {
				free_pages_fn(page, 1);
				rss_sub_fn(PAGE_SIZE, PAGE_SIZE);
				log_fn(FILEOBJ_LOG_FREE_RSS_SUB, obj, page,
				       (uintptr_t)page, PAGE_SIZE, flags);
			}
		}
		if (pages) {
			free_fn(pages);
		}
	}

	if (fileobj_path_present_result((uintptr_t)path)) {
		free_fn(path);
	}

	error = release_fn(handle, sref);
	if (error) {
		log_fn(FILEOBJ_LOG_FREE_RELEASE_ERROR, obj, NULL, handle,
		       error, flags);
	}

	log_fn(FILEOBJ_LOG_FREE_DONE, obj, NULL, handle, error, flags);
	free_fn(obj);

	return error;
}

size_t devobj_npages_result(size_t len)
{
	return (len + PAGE_SIZE - 1) / PAGE_SIZE;
}

size_t devobj_pfn_table_npages_result(size_t npages)
{
	const size_t uintptr_per_page = PAGE_SIZE / sizeof(uintptr_t);

	return (npages + uintptr_per_page - 1) / uintptr_per_page;
}

size_t devobj_pfn_table_bytes_result(size_t pfn_npages)
{
	return pfn_npages * PAGE_SIZE;
}

off_t devobj_pgoff_result(off_t off)
{
	return off >> PAGE_SHIFT;
}

int devobj_get_page_index_result(off_t pgoff, off_t base_pgoff,
				 size_t npages, int *ixp)
{
	if ((pgoff < base_pgoff) ||
	    ((base_pgoff + npages) <= (uintptr_t)pgoff)) {
		return -EFBIG;
	}

	*ixp = pgoff - base_pgoff;
	return 0;
}

int devobj_cached_pfn_needs_fetch_result(uintptr_t pfn)
{
	return !(pfn & PFN_VALID);
}

int devobj_pfn_present_result(uintptr_t pfn)
{
	return !!(pfn & PFN_PRESENT);
}

uintptr_t devobj_pfn_attr_result(uintptr_t pfn)
{
	return pfn & ~PFN_PFN;
}

uintptr_t devobj_pfn_phys_result(uintptr_t pfn)
{
	return pfn & PFN_PFN;
}

int devobj_pfn_absent_error_result(uintptr_t pfn)
{
	return (pfn & PFN_PRESENT) ? 0 : -EFAULT;
}

int devobj_base_flags_result(void)
{
	return MF_HAS_PAGER | MF_REMAP_FILE_PAGES | MF_DEV_FILE;
}

int devobj_initial_refcnt_result(void)
{
	return 1;
}

off_t devobj_pfn_request_offset_result(off_t off)
{
	return off & ~(PAGE_SIZE - 1);
}

int devobj_should_store_pfn_result(uintptr_t current_pfn)
{
	return current_pfn == 0;
}

size_t devobj_map_size_result(void)
{
	return PAGE_SIZE;
}

int devobj_path_present_result(unsigned long value)
{
	return value != 0;
}

int devobj_pfn_table_present_result(uintptr_t pfn_table)
{
	return pfn_table != 0;
}

uintptr_t devobj_mapped_pfn_result(uintptr_t mapped_pfn, uintptr_t attr)
{
	return devobj_pfn_phys_result(mapped_pfn) | attr;
}

int devobj_free_body_result(void *obj, void *path, void *pfn_table,
			    uintptr_t handle, size_t npages,
			    devobj_unmap_fn_t unmap_fn,
			    devobj_free_pages_fn_t free_pages_fn,
			    devobj_free_fn_t free_fn,
			    devobj_log_fn_t log_fn)
{
	size_t pfn_npages;
	int error;

	if (!obj || !unmap_fn || !free_pages_fn || !free_fn || !log_fn) {
		return -EINVAL;
	}

	pfn_npages = devobj_pfn_table_npages_result(npages);
	error = unmap_fn(handle);
	if (error) {
		log_fn(DEVOBJ_LOG_RELEASE_FAILED, NULL, obj, 0, 0, 0, 0,
		       error, handle);
	}

	if (devobj_pfn_table_present_result((uintptr_t)pfn_table)) {
		free_pages_fn(pfn_table, pfn_npages);
	}

	if (devobj_path_present_result((uintptr_t)path)) {
		free_fn(path);
	}

	free_fn(obj);
	log_fn(DEVOBJ_LOG_FREE_DONE, NULL, obj, 0, 0, 0, 0, 0, handle);

	return 0;
}

int devobj_get_page_body_result(
	void *memobj, void *obj, uintptr_t handle, off_t off, int p2align,
	off_t pfn_pgoff, size_t npages, void *pfn_table_lock,
	uintptr_t *physp, unsigned long *flagp, devobj_profile_fn_t profile_fn,
	devobj_lock_fn_t lock_fn, devobj_unlock_fn_t unlock_fn,
	devobj_pfn_load_fn_t pfn_load_fn, devobj_fetch_pfn_fn_t fetch_pfn_fn,
	devobj_pfn_write_combined_fn_t write_combined_fn,
	devobj_map_memory_fn_t map_memory_fn,
	devobj_pfn_store_fn_t pfn_store_fn,
	devobj_log_fn_t log_fn)
{
	off_t pgoff;
	uintptr_t pfn;
	uintptr_t attr;
	int error;
	int ix;
	unsigned long irqstate;

	if (!obj || !pfn_table_lock || !physp || !flagp || !profile_fn ||
	    !lock_fn || !unlock_fn || !pfn_load_fn || !fetch_pfn_fn ||
	    !write_combined_fn || !map_memory_fn || !pfn_store_fn ||
	    !log_fn) {
		return -EINVAL;
	}

	pgoff = devobj_pgoff_result(off);
	error = devobj_get_page_index_result(pgoff, pfn_pgoff, npages, &ix);
	if (error) {
		log_fn(DEVOBJ_LOG_OUT_OF_RANGE, memobj, obj, off, pgoff,
		       p2align, 0, error, 0);
		return error;
	}

	profile_fn();

	irqstate = lock_fn(pfn_table_lock);
	pfn = pfn_load_fn(obj, ix);
	unlock_fn(pfn_table_lock, irqstate);

	if (devobj_cached_pfn_needs_fetch_result(pfn)) {
		pfn = 0;
		error = fetch_pfn_fn(memobj, obj, handle, off, p2align, &pfn);
		if (error) {
			log_fn(DEVOBJ_LOG_FETCH_FAILED, memobj, obj, off,
			       pgoff, p2align, ix, error, pfn);
			return error;
		}

		if (devobj_pfn_present_result(pfn)) {
			attr = devobj_pfn_attr_result(pfn);
			if (write_combined_fn(pfn)) {
				*flagp |= VR_WRITE_COMBINED;
			}
			pfn = map_memory_fn(devobj_pfn_phys_result(pfn),
					    devobj_map_size_result());
			pfn = devobj_mapped_pfn_result(pfn, attr);
		}

		irqstate = lock_fn(pfn_table_lock);
		pfn_store_fn(obj, ix, pfn);
		unlock_fn(pfn_table_lock, irqstate);
	}

	error = devobj_pfn_absent_error_result(pfn);
	if (error) {
		log_fn(DEVOBJ_LOG_NOT_PRESENT, memobj, obj, off, pgoff,
		       p2align, ix, error, pfn);
		return error;
	}

	*physp = devobj_pfn_phys_result(pfn);
	return 0;
}

int procfs_thread_ctl_result(void *channel, struct ikc_scd_packet *packet,
			     int *donep, int msg, int osnum, int cpu_id,
			     int pid, int tid,
			     procfs_thread_phys_fn_t phys_fn,
			     procfs_thread_send_fn_t send_fn,
			     procfs_thread_pause_fn_t pause_fn)
{
	int error;

	if (!packet || !donep || !phys_fn || !send_fn)
		return -EINVAL;

	memset(packet, '\0', sizeof(*packet));
	packet->arg = tid;
	packet->msg = msg;
	packet->osnum = osnum;
	packet->ref = cpu_id;
	packet->pid = pid;
	packet->resp_pa = phys_fn(donep);
	packet->err = 0;

	error = send_fn(channel, packet);
	if (msg == SCD_MSG_PROCFS_TID_CREATE) {
		while (!*donep) {
			if (!pause_fn)
				return error ? error : -EINVAL;
			pause_fn();
		}
	}
	return error;
}

int procfs_answer_result(void *channel, struct ikc_scd_packet *request,
			 int err, procfs_answer_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;

	if (!request || !send_fn)
		return -EINVAL;

	memset(&packet, '\0', sizeof(packet));
	packet.msg = SCD_MSG_PROCFS_ANSWER;
	packet.ref = request->ref;
	packet.arg = request->arg;
	packet.err = err;
	packet.reply = request->reply;
	packet.pid = request->pid;
	send_fn(channel, &packet);
	return 0;
}

int procfs_buf_release_result(unsigned long phys,
			      procfs_buf_phys_to_virt_fn_t phys_to_virt_fn,
			      procfs_buf_free_page_fn_t free_page_fn)
{
	struct mckernel_procfs_buffer *pbuf;
	unsigned long next;

	if (!phys_to_virt_fn || !free_page_fn)
		return -EINVAL;

	while (phys != (unsigned long)-1) {
		pbuf = phys_to_virt_fn(phys);
		if (!pbuf)
			return -EINVAL;
		next = pbuf->next_pa;
		free_page_fn(pbuf);
		phys = next;
	}
	return 0;
}

struct mckernel_procfs_buffer *procfs_buf_alloc_result(
		unsigned long *phys, long pos,
		procfs_buf_page_alloc_fn_t alloc_fn,
		procfs_buf_phys_fn_t phys_fn, unsigned long alloc_flags)
{
	struct mckernel_procfs_buffer *pbuf;

	if (!alloc_fn || (phys && !phys_fn))
		return NULL;

	pbuf = alloc_fn(1, alloc_flags);
	if (!pbuf)
		return NULL;

	pbuf->next_pa = (unsigned long)-1;
	pbuf->pos = pos;
	pbuf->size = 0;
	if (phys)
		*phys = phys_fn(pbuf);
	return pbuf;
}

int procfs_buf_add_result(struct mckernel_procfs_buffer **top,
			  struct mckernel_procfs_buffer **cur,
			  const void *buf, int len,
			  procfs_buf_alloc_fn_t alloc_fn,
			  procfs_buf_free_top_fn_t free_top_fn,
			  procfs_buf_copy_fn_t copy_fn)
{
	size_t pos = 0;
	size_t remaining;
	size_t r;
	const size_t bufmax = PAGE_SIZE - sizeof(struct mckernel_procfs_buffer);
	const char *chr = buf;

	if (!top || !cur || !buf || len < 0 || !alloc_fn || !free_top_fn ||
			!copy_fn)
		return -EINVAL;

	if (!*top) {
		*top = *cur = alloc_fn(NULL, 0);
		if (!*top)
			return -ENOMEM;
	}
	if (!*cur)
		return -EINVAL;

	remaining = (size_t)len;
	while (remaining) {
		r = bufmax - (*cur)->size;
		if (!r) {
			*cur = alloc_fn(&(*cur)->next_pa,
					(long)((*cur)->pos + bufmax));
			if (!*cur) {
				free_top_fn(*top);
				*top = NULL;
				return -ENOMEM;
			}
			r = bufmax;
		}
		if (r > remaining)
			r = remaining;
		copy_fn((*cur)->buf + (*cur)->size, chr + pos, r);
		remaining -= r;
		pos += r;
		(*cur)->size += r;
	}
	return 0;
}

int procfs_release_request_result(struct procfs_read *request,
				  procfs_buf_phys_to_virt_fn_t phys_to_virt_fn,
				  procfs_buf_free_page_fn_t free_page_fn)
{
	int error;

	if (!request)
		return -EINVAL;

	error = procfs_buf_release_result(request->pbuf, phys_to_virt_fn,
			free_page_fn);
	if (error)
		return error;
	request->ret = 0;
	return 0;
}

int procfs_finish_request_result(struct procfs_read *request, int ret, int eof,
				 struct mckernel_procfs_buffer *buf_top,
				 procfs_buf_phys_fn_t phys_fn)
{
	if (!request)
		return -EINVAL;

	request->ret = ret;
	request->eof = eof;
	if (procfs_buffer_chain_attach_result(request->pbuf,
			(uintptr_t)buf_top)) {
		if (!phys_fn)
			return -EINVAL;
		request->pbuf = phys_fn(buf_top);
	}
	return 0;
}

int procfs_backlog_result(struct ikc_scd_packet *request,
			  procfs_backlog_fn_t backlog_fn,
			  procfs_backlog_alloc_fn_t alloc_fn,
			  procfs_backlog_copy_fn_t copy_fn,
			  procfs_backlog_add_fn_t add_fn,
			  procfs_backlog_free_fn_t free_fn,
			  unsigned long packet_size,
			  unsigned long alloc_flags)
{
	void *arg;
	int err;

	if (!request || !backlog_fn || !alloc_fn || !copy_fn || !add_fn ||
	    !free_fn)
		return -EINVAL;

	arg = alloc_fn(packet_size, alloc_flags);
	if (!arg)
		return -ENOMEM;

	copy_fn(arg, request, packet_size);
	err = add_fn(backlog_fn, arg);
	if (err)
		free_fn(arg);

	return err;
}

int sysfs_path_error_result(ssize_t n, int path_is_absolute, size_t capacity)
{
	if (n >= capacity)
		return -ENAMETOOLONG;
	if (!path_is_absolute)
		return -ENOENT;
	return 0;
}

int sysfs_special_kind_result(long client_ops)
{
	switch (client_ops) {
	case (long)SYSFS_SNOOPING_OPS_d32:
	case (long)SYSFS_SNOOPING_OPS_d64:
	case (long)SYSFS_SNOOPING_OPS_u32:
	case (long)SYSFS_SNOOPING_OPS_u64:
	case (long)SYSFS_SNOOPING_OPS_u32K:
		return SYSFS_SPECIAL_KIND_DIRECT;
	case (long)SYSFS_SNOOPING_OPS_s:
		return SYSFS_SPECIAL_KIND_STRING;
	case (long)SYSFS_SNOOPING_OPS_pbl:
	case (long)SYSFS_SNOOPING_OPS_pb:
		return SYSFS_SPECIAL_KIND_BITMAP;
	}

	return -EINVAL;
}

int sysfs_string_nbits_result(size_t len)
{
	return 8 * (len + 1);
}

int sysfs_response_error_result(ssize_t ssize)
{
	return (ssize < 0) ? (int)ssize : 0;
}

int sysfs_param_sizes_valid_result(size_t create_size, size_t mkdir_size,
				   size_t symlink_size, size_t lookup_size,
				   size_t unlink_size, size_t setup_size)
{
	return create_size <= PAGE_SIZE && mkdir_size <= PAGE_SIZE &&
		symlink_size <= PAGE_SIZE && lookup_size <= PAGE_SIZE &&
		unlink_size <= PAGE_SIZE && setup_size <= PAGE_SIZE;
}

size_t sysfs_data_bufsize_result(void)
{
	return PAGE_SIZE;
}

int sysfs_packet_error_result(int send_error, int packet_error)
{
	return send_error || packet_error;
}

int sysfs_request_busy_result(int busy)
{
	return busy != 0;
}

int sysfs_handle_pointer_valid_result(uintptr_t handlep)
{
	return handlep != 0;
}

ssize_t sysfs_default_response_ssize_result(void)
{
	return -EIO;
}

int sysfs_release_response_error_result(void)
{
	return 0;
}

int sysfss_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
				 int err, long arg1, long arg2)
{
	if (!packet)
		return -EINVAL;

	packet->msg = msg;
	packet->err = err;
	packet->sysfs_arg1 = arg1;
	packet->sysfs_arg2 = arg2;

	return 0;
}

int sysfs_request_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
					long arg1)
{
	if (!packet)
		return -EINVAL;

	packet->msg = msg;
	packet->sysfs_arg1 = arg1;

	return 0;
}

int sysfs_request_handler_kind_result(int msg)
{
	switch (msg) {
	case SCD_MSG_SYSFS_REQ_SHOW:
		return SYSFS_HANDLER_SHOW;
	case SCD_MSG_SYSFS_REQ_STORE:
		return SYSFS_HANDLER_STORE;
	case SCD_MSG_SYSFS_REQ_RELEASE:
		return SYSFS_HANDLER_RELEASE;
	default:
		return SYSFS_HANDLER_UNKNOWN;
	}
}

int sysfs_pointer_missing_result(uintptr_t ptr)
{
	return ptr == 0;
}

int sysfs_should_call_show_result(uintptr_t show)
{
	return show != 0;
}

int sysfs_should_call_store_result(uintptr_t store)
{
	return store != 0;
}

int sysfs_should_call_release_result(uintptr_t release)
{
	return release != 0;
}

int sysfs_setup_special_create_result(struct sysfs_req_create_param *param,
				      struct sysfs_bitmap_param *pbp,
				      sysfs_init_phys_fn_t phys_fn)
{
	void *cinstance;

	if (!param || !pbp || !phys_fn)
		return -EINVAL;

	cinstance = (void *)param->client_instance;
	switch (sysfs_special_kind_result(param->client_ops)) {
	case SYSFS_SPECIAL_KIND_DIRECT:
		param->client_instance = phys_fn(cinstance);
		return 0;

	case SYSFS_SPECIAL_KIND_STRING:
		pbp->nbits = sysfs_string_nbits_result(strlen(cinstance));
		pbp->ptr = (void *)phys_fn(cinstance);
		param->client_instance = phys_fn(pbp);
		return 0;

	case SYSFS_SPECIAL_KIND_BITMAP:
		*pbp = *(struct sysfs_bitmap_param *)cinstance;
		pbp->ptr = (void *)phys_fn(pbp->ptr);
		param->client_instance = phys_fn(pbp);
		return 0;
	}

	return -EINVAL;
}

static int sysfs_request_known_msg(int msg)
{
	switch (msg) {
	case SCD_MSG_SYSFS_REQ_CREATE:
	case SCD_MSG_SYSFS_REQ_MKDIR:
	case SCD_MSG_SYSFS_REQ_SYMLINK:
	case SCD_MSG_SYSFS_REQ_LOOKUP:
	case SCD_MSG_SYSFS_REQ_UNLINK:
	case SCD_MSG_SYSFS_REQ_SETUP:
		return 1;
	default:
		return 0;
	}
}

static int sysfs_request_busy_value(int msg, void *param)
{
	switch (msg) {
	case SCD_MSG_SYSFS_REQ_CREATE:
		return ((struct sysfs_req_create_param *)param)->busy;
	case SCD_MSG_SYSFS_REQ_MKDIR:
		return ((struct sysfs_req_mkdir_param *)param)->busy;
	case SCD_MSG_SYSFS_REQ_SYMLINK:
		return ((struct sysfs_req_symlink_param *)param)->busy;
	case SCD_MSG_SYSFS_REQ_LOOKUP:
		return ((struct sysfs_req_lookup_param *)param)->busy;
	case SCD_MSG_SYSFS_REQ_UNLINK:
		return ((struct sysfs_req_unlink_param *)param)->busy;
	case SCD_MSG_SYSFS_REQ_SETUP:
		return ((struct sysfs_req_setup_param *)param)->busy;
	default:
		return 0;
	}
}

static int sysfs_request_error_value(int msg, void *param)
{
	switch (msg) {
	case SCD_MSG_SYSFS_REQ_CREATE:
		return ((struct sysfs_req_create_param *)param)->error;
	case SCD_MSG_SYSFS_REQ_MKDIR:
		return ((struct sysfs_req_mkdir_param *)param)->error;
	case SCD_MSG_SYSFS_REQ_SYMLINK:
		return ((struct sysfs_req_symlink_param *)param)->error;
	case SCD_MSG_SYSFS_REQ_LOOKUP:
		return ((struct sysfs_req_lookup_param *)param)->error;
	case SCD_MSG_SYSFS_REQ_UNLINK:
		return ((struct sysfs_req_unlink_param *)param)->error;
	case SCD_MSG_SYSFS_REQ_SETUP:
		return ((struct sysfs_req_setup_param *)param)->error;
	default:
		return -EINVAL;
	}
}

static long sysfs_request_handle_value(int msg, void *param)
{
	switch (msg) {
	case SCD_MSG_SYSFS_REQ_MKDIR:
		return ((struct sysfs_req_mkdir_param *)param)->handle;
	case SCD_MSG_SYSFS_REQ_LOOKUP:
		return ((struct sysfs_req_lookup_param *)param)->handle;
	default:
		return 0;
	}
}

int sysfs_request_body_result(int msg, void *param, long param_rpa,
			      sysfs_request_send_fn_t send_fn,
			      sysfs_request_pause_fn_t pause_fn,
			      sysfs_request_barrier_fn_t barrier_fn,
			      long *handlep, int *phasep)
{
	int error;

	if (phasep)
		*phasep = SYSFS_REQUEST_PHASE_NONE;

	if (!param || !sysfs_request_known_msg(msg))
		return -EINVAL;

	if (!send_fn) {
		if (phasep)
			*phasep = SYSFS_REQUEST_PHASE_SEND;
		return -EIO;
	}

	error = send_fn(msg, param_rpa);
	if (error) {
		if (phasep)
			*phasep = SYSFS_REQUEST_PHASE_SEND;
		return error;
	}

	while (sysfs_request_busy_result(
			sysfs_request_busy_value(msg, param))) {
		if (!pause_fn) {
			if (phasep)
				*phasep = SYSFS_REQUEST_PHASE_SEND;
			return -EIO;
		}
		pause_fn();
	}
	if (barrier_fn)
		barrier_fn();

	error = sysfs_request_error_value(msg, param);
	if (error) {
		if (phasep)
			*phasep = SYSFS_REQUEST_PHASE_RESPONSE;
		return error;
	}

	if (handlep)
		*handlep = sysfs_request_handle_value(msg, param);
	return 0;
}

static void sysfs_request_emit_log(sysfs_request_log_fn_t log_fn, int event,
				   int msg, int error)
{
	if (log_fn) {
		log_fn(event, msg, error);
	}
}

int sysfs_request_logged_result(int msg, void *param, long param_rpa,
				sysfs_request_send_fn_t send_fn,
				sysfs_request_pause_fn_t pause_fn,
				sysfs_request_barrier_fn_t barrier_fn,
				long *handle_dstp,
				sysfs_request_log_fn_t log_fn,
				int *phasep)
{
	long handle = 0;
	long *handlep = NULL;
	int phase = SYSFS_REQUEST_PHASE_NONE;
	int error;

	if (sysfs_handle_pointer_valid_result((uintptr_t)handle_dstp)) {
		handlep = &handle;
	}

	error = sysfs_request_body_result(msg, param, param_rpa, send_fn,
			pause_fn, barrier_fn, handlep, &phase);
	if (phasep) {
		*phasep = phase;
	}
	if (error) {
		if (phase == SYSFS_REQUEST_PHASE_SEND) {
			sysfs_request_emit_log(log_fn,
					SYSFS_REQUEST_LOG_SEND_ERROR, msg,
					error);
		}
		else if (phase == SYSFS_REQUEST_PHASE_RESPONSE) {
			sysfs_request_emit_log(log_fn,
					SYSFS_REQUEST_LOG_RESPONSE_ERROR, msg,
					error);
		}
		return error;
	}

	if (handlep && handle_dstp) {
		*handle_dstp = handle;
	}
	return 0;
}

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
			   int *stagep, int *phasep)
{
	struct sysfs_req_setup_param *param;
	size_t data_bufsize;
	void *data_buf;
	int error;

	if (stagep)
		*stagep = SYSFS_INIT_STAGE_NONE;
	if (phasep)
		*phasep = SYSFS_REQUEST_PHASE_NONE;

	if (!sysfs_param_sizes_valid_result(create_size, mkdir_size,
			symlink_size, lookup_size, unlink_size, setup_size)) {
		if (stagep)
			*stagep = SYSFS_INIT_STAGE_SIZE;
		return -EINVAL;
	}

	if (!data_bufp || !data_bufsizep || !alloc_fn || !free_fn || !phys_fn)
		return -EINVAL;

	data_bufsize = sysfs_data_bufsize_result();
	*data_bufsizep = data_bufsize;

	data_buf = alloc_fn(1, SYSFS_INIT_AP_NOWAIT);
	if (!data_buf) {
		if (stagep)
			*stagep = SYSFS_INIT_STAGE_DATA_ALLOC;
		return -ENOMEM;
	}
	*data_bufp = data_buf;

	param = alloc_fn(1, SYSFS_INIT_AP_NOWAIT);
	if (!param) {
		if (stagep)
			*stagep = SYSFS_INIT_STAGE_PARAM_ALLOC;
		return -ENOMEM;
	}

	param->busy = 1;
	param->buf_rpa = phys_fn(data_buf);
	param->bufsize = data_bufsize;

	error = sysfs_request_body_result(SCD_MSG_SYSFS_REQ_SETUP, param,
			phys_fn(param), send_fn, pause_fn, barrier_fn, NULL,
			phasep);
	free_fn(param, 1);
	if (error && stagep)
		*stagep = SYSFS_INIT_STAGE_REQUEST;
	return error;
}

int sysfss_req_show_body_result(long nodeh, void *ops, void *instance,
				void *data_buf, size_t data_bufsize,
				sysfss_show_fn_t show_fn,
				sysfss_send_fn_t send_fn, ssize_t *ssizep,
				int *packet_errp)
{
	ssize_t ssize = sysfs_default_response_ssize_result();
	int packet_err;
	int send_error;

	if (show_fn) {
		ssize = show_fn(ops, instance, data_buf, data_bufsize);
	}

	packet_err = sysfs_response_error_result(ssize);
	send_error = send_fn(SCD_MSG_SYSFS_RESP_SHOW, packet_err, nodeh,
			ssize);
	if (ssizep) {
		*ssizep = ssize;
	}
	if (packet_errp) {
		*packet_errp = packet_err;
	}
	return send_error;
}

int sysfss_req_store_body_result(long nodeh, void *ops, void *instance,
				 void *data_buf, size_t size,
				 sysfss_store_fn_t store_fn,
				 sysfss_send_fn_t send_fn, ssize_t *ssizep,
				 int *packet_errp)
{
	ssize_t ssize = sysfs_default_response_ssize_result();
	int packet_err;
	int send_error;

	if (store_fn) {
		ssize = store_fn(ops, instance, data_buf, size);
	}

	packet_err = sysfs_response_error_result(ssize);
	send_error = send_fn(SCD_MSG_SYSFS_RESP_STORE, packet_err, nodeh,
			ssize);
	if (ssizep) {
		*ssizep = ssize;
	}
	if (packet_errp) {
		*packet_errp = packet_err;
	}
	return send_error;
}

static void sysfss_req_emit_log(sysfss_req_log_fn_t log_fn, int event,
				long nodeh, void *ops, void *instance,
				size_t size, int error, int packet_err,
				ssize_t ssize)
{
	if (log_fn) {
		log_fn(event, nodeh, ops, instance, size, error, packet_err,
				ssize);
	}
}

int sysfss_req_show_logged_result(long nodeh, void *ops, void *instance,
				  void *data_buf, size_t data_bufsize,
				  uintptr_t show, sysfss_show_fn_t show_fn,
				  sysfss_send_fn_t send_fn,
				  sysfss_req_log_fn_t log_fn,
				  ssize_t *ssizep, int *packet_errp)
{
	sysfss_show_fn_t call_show_fn = NULL;
	ssize_t ssize = 0;
	int packet_err = 0;
	int error;

	if (sysfs_should_call_show_result(show)) {
		call_show_fn = show_fn;
	}

	error = sysfss_req_show_body_result(nodeh, ops, instance, data_buf,
			data_bufsize, call_show_fn, send_fn, &ssize, &packet_err);
	if (call_show_fn && ssize < 0) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_CALLBACK_ERROR,
				nodeh, ops, instance, data_bufsize, error,
				packet_err, ssize);
	}
	if (error) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_SEND_ERROR, nodeh,
				ops, instance, data_bufsize, error, packet_err,
				ssize);
	}
	if (sysfs_packet_error_result(error, packet_err)) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_PACKET_ERROR,
				nodeh, ops, instance, data_bufsize, error,
				packet_err, ssize);
	}
	sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_DEBUG, nodeh, ops,
			instance, data_bufsize, error, packet_err, ssize);
	if (ssizep) {
		*ssizep = ssize;
	}
	if (packet_errp) {
		*packet_errp = packet_err;
	}
	return error;
}

int sysfss_req_store_logged_result(long nodeh, void *ops, void *instance,
				   void *data_buf, size_t size,
				   uintptr_t store, sysfss_store_fn_t store_fn,
				   sysfss_send_fn_t send_fn,
				   sysfss_req_log_fn_t log_fn,
				   ssize_t *ssizep, int *packet_errp)
{
	sysfss_store_fn_t call_store_fn = NULL;
	ssize_t ssize = 0;
	int packet_err = 0;
	int error;

	if (sysfs_should_call_store_result(store)) {
		call_store_fn = store_fn;
	}

	error = sysfss_req_store_body_result(nodeh, ops, instance, data_buf,
			size, call_store_fn, send_fn, &ssize, &packet_err);
	if (call_store_fn && ssize < 0) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_CALLBACK_ERROR,
				nodeh, ops, instance, size, error, packet_err,
				ssize);
	}
	if (error) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_SEND_ERROR, nodeh,
				ops, instance, size, error, packet_err, ssize);
	}
	if (sysfs_packet_error_result(error, packet_err)) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_PACKET_ERROR,
				nodeh, ops, instance, size, error, packet_err,
				ssize);
	}
	sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_DEBUG, nodeh, ops,
			instance, size, error, packet_err, ssize);
	if (ssizep) {
		*ssizep = ssize;
	}
	if (packet_errp) {
		*packet_errp = packet_err;
	}
	return error;
}

int sysfss_req_release_body_result(long nodeh, void *ops, void *instance,
				   sysfss_release_fn_t release_fn,
				   sysfss_send_fn_t send_fn,
				   int *packet_errp)
{
	int packet_err;
	int send_error;

	if (release_fn) {
		release_fn(ops, instance);
	}

	packet_err = sysfs_release_response_error_result();
	send_error = send_fn(SCD_MSG_SYSFS_RESP_RELEASE, packet_err, nodeh, 0);
	if (packet_errp) {
		*packet_errp = packet_err;
	}
	return send_error;
}

int sysfss_req_release_logged_result(long nodeh, void *ops, void *instance,
				     uintptr_t release,
				     sysfss_release_fn_t release_fn,
				     sysfss_send_fn_t send_fn,
				     sysfss_req_log_fn_t log_fn,
				     int *packet_errp)
{
	sysfss_release_fn_t call_release_fn = NULL;
	int packet_err = 0;
	int error;

	if (sysfs_should_call_release_result(release)) {
		call_release_fn = release_fn;
	}

	error = sysfss_req_release_body_result(nodeh, ops, instance,
			call_release_fn, send_fn, &packet_err);
	if (error) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_SEND_ERROR, nodeh,
				ops, instance, 0, error, packet_err, 0);
	}
	if (sysfs_packet_error_result(error, packet_err)) {
		sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_PACKET_ERROR,
				nodeh, ops, instance, 0, error, packet_err, 0);
	}
	sysfss_req_emit_log(log_fn, SYSFSS_REQ_LOG_DEBUG, nodeh, ops,
			instance, 0, error, packet_err, 0);
	if (packet_errp) {
		*packet_errp = packet_err;
	}
	return error;
}

int sysfss_packet_handler_body_result(int msg, int error, long arg1,
				      long arg2, long arg3,
				      sysfss_packet_show_fn_t show_fn,
				      sysfss_packet_store_fn_t store_fn,
				      sysfss_packet_release_fn_t release_fn,
				      int *kindp)
{
	int kind = sysfs_request_handler_kind_result(msg);

	if (kindp) {
		*kindp = kind;
	}

	switch (kind) {
	case SYSFS_HANDLER_SHOW:
		if (!show_fn) {
			return -EIO;
		}
		show_fn(arg1, (void *)arg2, (void *)arg3);
		return 0;
	case SYSFS_HANDLER_STORE:
		if (!store_fn) {
			return -EIO;
		}
		store_fn(arg1, (void *)arg2, (void *)arg3, error);
		return 0;
	case SYSFS_HANDLER_RELEASE:
		if (!release_fn) {
			return -EIO;
		}
		release_fn(arg1, (void *)arg2, (void *)arg3);
		return 0;
	default:
		return -EINVAL;
	}
}

int sysfss_packet_handler_logged_result(int msg, int error, long arg1,
					long arg2, long arg3,
					sysfss_packet_show_fn_t show_fn,
					sysfss_packet_store_fn_t store_fn,
					sysfss_packet_release_fn_t release_fn,
					sysfss_packet_unknown_fn_t unknown_fn,
					int *kindp)
{
	int kind = SYSFS_HANDLER_UNKNOWN;
	int result;

	result = sysfss_packet_handler_body_result(msg, error, arg1, arg2,
			arg3, show_fn, store_fn, release_fn, &kind);
	if (kindp) {
		*kindp = kind;
	}
	if (kind == SYSFS_HANDLER_UNKNOWN && unknown_fn) {
		unknown_fn(msg, error, arg1, arg2, arg3);
	}
	return result;
}

unsigned long procfs_mem_reason_result(int readwrite)
{
	if (readwrite)
		return PF_POPULATE | PF_WRITE | PF_USER;
	return PF_POPULATE | PF_USER;
}

int procfs_mem_chunk_size_result(unsigned long offset, unsigned long left)
{
	int pos = offset & (PAGE_SIZE - 1);
	int size = PAGE_SIZE - pos;

	if (size > left)
		size = left;
	return size;
}

int procfs_mem_copy_body_result(void *vm, void *page_table, void *buf,
				unsigned long offset, unsigned long count,
				int readwrite,
				procfs_mem_page_fault_fn_t page_fault_fn,
				procfs_mem_virt_to_phys_fn_t virt_to_phys_fn,
				procfs_mem_is_memory_fn_t is_memory_fn,
				procfs_mem_phys_to_virt_fn_t phys_to_virt_fn,
				procfs_mem_copy_fn_t copy_fn)
{
	unsigned long reason;
	unsigned long left = count;
	int ans = 0;

	if (!vm || !page_table || !buf || !page_fault_fn || !virt_to_phys_fn ||
			!is_memory_fn || !phys_to_virt_fn || !copy_fn)
		return -EINVAL;

	reason = procfs_mem_reason_result(readwrite);
	if (procfs_zero_length_result(left))
		return 0;

	while (left) {
		unsigned long pa;
		void *va;
		int ret;
		int size = procfs_mem_chunk_size_result(offset, left);

		ret = page_fault_fn(vm, offset, reason);
		if (ret)
			return ans == 0 ? -EIO : ans;
		ret = virt_to_phys_fn(page_table, offset, &pa);
		if (ret)
			return ans == 0 ? -EIO : ans;

		if (!is_memory_fn(pa, pa + size))
			return -EIO;

		va = phys_to_virt_fn(pa);
		if (readwrite)
			copy_fn(va, (char *)buf + ans, size);
		else
			copy_fn((char *)buf + ans, va, size);
		offset += size;
		left -= size;
		ans += size;
	}
	return ans;
}

static int procfs_add_bytes(struct mckernel_procfs_buffer **top,
			    struct mckernel_procfs_buffer **cur,
			    const void *buf, size_t len,
			    procfs_buf_alloc_fn_t alloc_fn,
			    procfs_buf_free_top_fn_t free_top_fn,
			    procfs_buf_copy_fn_t copy_fn)
{
	static const char empty[] = "";

	if (!buf && len == 0)
		buf = empty;
	if (!buf || len > PROCFS_INT_MAX)
		return -EINVAL;
	return procfs_buf_add_result(top, cur, buf, (int)len, alloc_fn,
			free_top_fn, copy_fn);
}

static int procfs_add_cstr(struct mckernel_procfs_buffer **top,
			   struct mckernel_procfs_buffer **cur,
			   const char *text, procfs_buf_alloc_fn_t alloc_fn,
			   procfs_buf_free_top_fn_t free_top_fn,
			   procfs_buf_copy_fn_t copy_fn)
{
	if (!text)
		return -EINVAL;
	return procfs_add_bytes(top, cur, text, strlen(text), alloc_fn,
			free_top_fn, copy_fn);
}

static int procfs_cpu_line(int cpu, char *line, size_t line_size)
{
	char digits[10];
	unsigned int value;
	size_t pos = 0;
	size_t nr_digits = 0;

	if (cpu < 0 || line_size < 5)
		return -EINVAL;

	line[pos++] = 'c';
	line[pos++] = 'p';
	line[pos++] = 'u';
	value = (unsigned int)cpu;
	do {
		digits[nr_digits++] = '0' + (value % 10);
		value /= 10;
	} while (value);
	while (nr_digits)
		line[pos++] = digits[--nr_digits];
	line[pos++] = '\n';
	return (int)pos;
}

int procfs_root_entry_body_result(int entry_kind, const char *version,
				  const char *buildid, int num_processors,
				  int count,
				  struct mckernel_procfs_buffer **top,
				  struct mckernel_procfs_buffer **cur,
				  procfs_buf_alloc_fn_t alloc_fn,
				  procfs_buf_free_top_fn_t free_top_fn,
				  procfs_buf_copy_fn_t copy_fn)
{
	int error;
	int cpu;

	switch (entry_kind) {
	case PROCFS_ENTRY_MCKERNEL:
		error = procfs_add_cstr(top, cur, version, alloc_fn, free_top_fn,
				copy_fn);
		if (error)
			return error;
		error = procfs_add_bytes(top, cur, "-", 1, alloc_fn,
				free_top_fn, copy_fn);
		if (error)
			return error;
		error = procfs_add_cstr(top, cur, buildid, alloc_fn,
				free_top_fn, copy_fn);
		if (error)
			return error;
		return procfs_add_bytes(top, cur, "\n", 1, alloc_fn,
				free_top_fn, copy_fn);

	case PROCFS_ENTRY_STAT:
		if (count < 0 || num_processors < 0)
			return -EINVAL;
		for (cpu = 0; cpu < num_processors; ++cpu) {
			char line[32];
			int len = procfs_cpu_line(cpu, line, sizeof(line));

			if (len < 0)
				return len;
			if (procfs_format_error_result(len, count))
				return -EIO;
			error = procfs_add_bytes(top, cur, line, (size_t)len,
					alloc_fn, free_top_fn, copy_fn);
			if (error)
				return error;
		}
		return 0;

	default:
		return -EINVAL;
	}
}

int procfs_pid_simple_entry_body_result(int entry_kind, const void *saved_auxv,
					const char *saved_cmdline,
					unsigned int saved_cmdline_len,
					const char *comm_fallback,
					struct mckernel_procfs_buffer **top,
					struct mckernel_procfs_buffer **cur,
					procfs_buf_alloc_fn_t alloc_fn,
					procfs_buf_free_top_fn_t free_top_fn,
					procfs_buf_copy_fn_t copy_fn)
{
	static const char empty[] = "";
	unsigned int limit;
	const char *source;
	const char *comm;
	int error;

	switch (entry_kind) {
	case PROCFS_ENTRY_AUXV:
		return procfs_add_bytes(top, cur, saved_auxv,
				procfs_auxv_limit_result(), alloc_fn, free_top_fn,
				copy_fn);
	case PROCFS_ENTRY_CMDLINE:
		limit = procfs_cmdline_limit_result((uintptr_t)saved_cmdline,
				saved_cmdline_len);
		source = procfs_pointer_present_result((uintptr_t)saved_cmdline) ?
			saved_cmdline : empty;
		return procfs_add_bytes(top, cur, source, limit, alloc_fn,
				free_top_fn, copy_fn);
	case PROCFS_ENTRY_COMM:
		comm = (const char *)procfs_comm_name_result(
				(uintptr_t)comm_fallback,
				procfs_comm_basename_result(
					(uintptr_t)saved_cmdline));
		error = procfs_add_cstr(top, cur, comm, alloc_fn, free_top_fn,
				copy_fn);
		if (error)
			return error;
		return procfs_add_bytes(top, cur, "\n", 1, alloc_fn,
				free_top_fn, copy_fn);
	default:
		return -EINVAL;
	}
}

int procfs_pagemap_range_result(unsigned long offset, int count,
				unsigned long *startp, unsigned long *endp)
{
	if ((offset % sizeof(uint64_t) != 0) ||
	    (count % sizeof(uint64_t) != 0)) {
		return -EINVAL;
	}

	*startp = (offset / sizeof(uint64_t)) << PAGE_SHIFT;
	*endp = *startp + (((unsigned long)count / sizeof(uint64_t)) <<
			   PAGE_SHIFT);
	return 0;
}

int procfs_pagemap_body_result(void *page_table, unsigned long *buf,
			       unsigned long start, unsigned long end, int count,
			       procfs_pagemap_value_fn_t value_fn)
{
	if (!page_table || !buf || !value_fn)
		return -EINVAL;

	while (start < end) {
		*buf = value_fn(page_table, start);
		start = procfs_pagemap_next_result(start);
		++buf;
	}
	return count;
}

static size_t procfs_ulong_dec_len(unsigned long value)
{
	size_t len = 1;

	while (value >= 10) {
		value /= 10;
		++len;
	}
	return len;
}

static size_t procfs_long_dec_len(long value)
{
	if (value < 0)
		return 1 + procfs_ulong_dec_len((unsigned long)(-value));
	return procfs_ulong_dec_len((unsigned long)value);
}

static size_t procfs_ulong_hex_len(unsigned long value)
{
	size_t len = 1;

	while (value >= 16) {
		value >>= 4;
		++len;
	}
	return len;
}

static int procfs_line_len_valid(size_t len, int count)
{
	if (len > PROCFS_INT_MAX)
		return -EINVAL;
	return procfs_format_error_result((int)len, count) ? -EIO : 0;
}

static int procfs_add_char(struct mckernel_procfs_buffer **top,
			   struct mckernel_procfs_buffer **cur, char ch,
			   procfs_buf_alloc_fn_t alloc_fn,
			   procfs_buf_free_top_fn_t free_top_fn,
			   procfs_buf_copy_fn_t copy_fn)
{
	return procfs_add_bytes(top, cur, &ch, 1, alloc_fn, free_top_fn,
			copy_fn);
}

static int procfs_add_ulong_dec_width(struct mckernel_procfs_buffer **top,
				      struct mckernel_procfs_buffer **cur,
				      unsigned long value, size_t min_width,
				      procfs_buf_alloc_fn_t alloc_fn,
				      procfs_buf_free_top_fn_t free_top_fn,
				      procfs_buf_copy_fn_t copy_fn)
{
	char out[32];
	char digits[20];
	unsigned long tmp = value;
	size_t nr_digits = 0;
	size_t pos = 0;
	size_t dec_len = procfs_ulong_dec_len(value);
	size_t width = min_width > dec_len ? min_width : dec_len;

	do {
		digits[nr_digits++] = '0' + tmp % 10;
		tmp /= 10;
	} while (tmp);
	while (pos + nr_digits < width)
		out[pos++] = ' ';
	while (nr_digits)
		out[pos++] = digits[--nr_digits];
	return procfs_add_bytes(top, cur, out, pos, alloc_fn, free_top_fn,
			copy_fn);
}

static int procfs_add_ulong_dec(struct mckernel_procfs_buffer **top,
				struct mckernel_procfs_buffer **cur,
				unsigned long value,
				procfs_buf_alloc_fn_t alloc_fn,
				procfs_buf_free_top_fn_t free_top_fn,
				procfs_buf_copy_fn_t copy_fn)
{
	return procfs_add_ulong_dec_width(top, cur, value, 0, alloc_fn,
			free_top_fn, copy_fn);
}

static int procfs_add_long_dec(struct mckernel_procfs_buffer **top,
			       struct mckernel_procfs_buffer **cur,
			       long value, procfs_buf_alloc_fn_t alloc_fn,
			       procfs_buf_free_top_fn_t free_top_fn,
			       procfs_buf_copy_fn_t copy_fn)
{
	int error;

	if (value < 0) {
		error = procfs_add_bytes(top, cur, "-", 1, alloc_fn,
				free_top_fn, copy_fn);
		if (error)
			return error;
		return procfs_add_ulong_dec(top, cur, (unsigned long)(-value),
				alloc_fn, free_top_fn, copy_fn);
	}
	return procfs_add_ulong_dec(top, cur, (unsigned long)value, alloc_fn,
			free_top_fn, copy_fn);
}

static int procfs_add_ulong_hex_width(struct mckernel_procfs_buffer **top,
				      struct mckernel_procfs_buffer **cur,
				      unsigned long value, size_t min_width,
				      procfs_buf_alloc_fn_t alloc_fn,
				      procfs_buf_free_top_fn_t free_top_fn,
				      procfs_buf_copy_fn_t copy_fn)
{
	static const char hex[] = "0123456789abcdef";
	char out[32];
	size_t hex_len = procfs_ulong_hex_len(value);
	size_t width = min_width > hex_len ? min_width : hex_len;
	size_t pos = width;

	while (pos) {
		out[--pos] = hex[value & 0xf];
		value >>= 4;
	}
	return procfs_add_bytes(top, cur, out, width, alloc_fn, free_top_fn,
			copy_fn);
}

static const char *procfs_maps_default_path(int path_kind)
{
	switch (path_kind) {
	case PROCFS_MAPS_PATH_VDSO:
		return "[vdso]";
	case PROCFS_MAPS_PATH_VVAR:
		return "[vvar]";
	case PROCFS_MAPS_PATH_STACK:
		return "[stack]";
	case PROCFS_MAPS_PATH_HEAP:
		return "[heap]";
	default:
		return "";
	}
}

static int procfs_maps_add_line(struct mckernel_procfs_buffer **top,
				struct mckernel_procfs_buffer **cur,
				unsigned long start, unsigned long end,
				unsigned long flags, const char *path,
				const char *default_path, int count,
				procfs_buf_alloc_fn_t alloc_fn,
				procfs_buf_free_top_fn_t free_top_fn,
				procfs_buf_copy_fn_t copy_fn)
{
	static const char zero_fields[] = " 0 0:0 0\t\t\t";
	size_t path_len = strlen(path ? path : default_path);
	size_t line_len = 12 + 1 + 12 + 1 + 4 + strlen(zero_fields) +
		path_len + 1;
	int error;

	error = procfs_line_len_valid(line_len, count);
	if (error)
		return error;
	error = procfs_add_ulong_hex_width(top, cur, start, 12, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, "-", 1, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_ulong_hex_width(top, cur, end, 12, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, " ", 1, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_char(top, cur, procfs_maps_read_char_result(flags),
			alloc_fn, free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_char(top, cur, procfs_maps_write_char_result(flags),
			alloc_fn, free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_char(top, cur, procfs_maps_exec_char_result(flags),
			alloc_fn, free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_char(top, cur,
			procfs_maps_private_char_result(flags), alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, zero_fields, strlen(zero_fields),
			alloc_fn, free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_cstr(top, cur, path ? path : default_path, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	return procfs_add_bytes(top, cur, "\n", 1, alloc_fn, free_top_fn,
			copy_fn);
}

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
			    procfs_range_next_fn_t range_next_fn)
{
	int error;

	if (!range_ulong_fn || !range_path_fn || !range_next_fn)
		return -EINVAL;

	while (range) {
		unsigned long start = range_ulong_fn(range,
				PROCFS_RANGE_FIELD_START);
		unsigned long end = range_ulong_fn(range,
				PROCFS_RANGE_FIELD_END);
		unsigned long flags = range_ulong_fn(range,
				PROCFS_RANGE_FIELD_FLAG);
		const char *path = range_path_fn(range);
		int path_kind = procfs_maps_path_kind_result(start, end, flags,
				vdso_addr, vvar_addr, brk_start,
				brk_end_allocated);

		error = procfs_maps_add_line(top, cur, start, end, flags, path,
				procfs_maps_default_path(path_kind), count,
				alloc_fn, free_top_fn, copy_fn);
		if (error)
			return error;
		range = range_next_fn(vm, range);
	}
	return 0;
}

unsigned long procfs_locked_size_body_result(void *vm, void *range,
					     procfs_range_ulong_fn_t range_ulong_fn,
					     procfs_range_next_fn_t range_next_fn)
{
	unsigned long lockedsize = 0;

	if (!range_ulong_fn || !range_next_fn)
		return 0;
	while (range) {
		lockedsize = procfs_locked_size_add_result(lockedsize,
				range_ulong_fn(range, PROCFS_RANGE_FIELD_START),
				range_ulong_fn(range, PROCFS_RANGE_FIELD_END),
				range_ulong_fn(range, PROCFS_RANGE_FIELD_FLAG));
		range = range_next_fn(vm, range);
	}
	return lockedsize;
}

static const char *procfs_status_state_name(int status)
{
	switch (procfs_status_state_result(status)) {
	case PROCFS_STATUS_STOPPED:
		return "T (stopped)";
	case PROCFS_STATUS_TRACED:
		return "T (tracing stop)";
	case PROCFS_STATUS_EXITED:
		return "Z (zombie)";
	default:
		return "R (running)";
	}
}

static int procfs_status_add_head(struct mckernel_procfs_buffer **top,
				  struct mckernel_procfs_buffer **cur,
				  const struct procfs_status_body_input *input,
				  const char *state, int count,
				  procfs_buf_alloc_fn_t alloc_fn,
				  procfs_buf_free_top_fn_t free_top_fn,
				  procfs_buf_copy_fn_t copy_fn)
{
	unsigned long locked_kb = procfs_locked_kb_result(input->lockedsize);
	size_t locked_len = procfs_ulong_dec_len(locked_kb);
	size_t len = strlen("Pid:\t") + procfs_long_dec_len(input->pid) +
		strlen("\nUid:\t") + procfs_long_dec_len(input->ruid) + 1 +
		procfs_long_dec_len(input->euid) + 1 +
		procfs_long_dec_len(input->suid) + 1 +
		procfs_long_dec_len(input->fsuid) +
		strlen("\nGid:\t") + procfs_long_dec_len(input->rgid) + 1 +
		procfs_long_dec_len(input->egid) + 1 +
		procfs_long_dec_len(input->sgid) + 1 +
		procfs_long_dec_len(input->fsgid) +
		strlen("\nState:\t") + strlen(state) +
		strlen("\nVmLck:\t") + (locked_len > 9 ? locked_len : 9) +
		strlen(" kB\nThreads:\t") +
		procfs_long_dec_len(input->nr_threads) + 1;
	int error = procfs_line_len_valid(len, count);

	if (error)
		return error;
#define ADD_LIT(lit) do { \
	error = procfs_add_bytes(top, cur, (lit), strlen(lit), alloc_fn, \
			free_top_fn, copy_fn); \
	if (error) \
		return error; \
} while (0)
#define ADD_LONG(v) do { \
	error = procfs_add_long_dec(top, cur, (long)(v), alloc_fn, \
			free_top_fn, copy_fn); \
	if (error) \
		return error; \
} while (0)
#define ADD_TAB() do { \
	error = procfs_add_char(top, cur, '\t', alloc_fn, free_top_fn, \
			copy_fn); \
	if (error) \
		return error; \
} while (0)
	ADD_LIT("Pid:\t");
	ADD_LONG(input->pid);
	ADD_LIT("\nUid:\t");
	ADD_LONG(input->ruid);
	ADD_TAB();
	ADD_LONG(input->euid);
	ADD_TAB();
	ADD_LONG(input->suid);
	ADD_TAB();
	ADD_LONG(input->fsuid);
	ADD_LIT("\nGid:\t");
	ADD_LONG(input->rgid);
	ADD_TAB();
	ADD_LONG(input->egid);
	ADD_TAB();
	ADD_LONG(input->sgid);
	ADD_TAB();
	ADD_LONG(input->fsgid);
	ADD_LIT("\nState:\t");
	ADD_LIT(state);
	ADD_LIT("\nVmLck:\t");
	error = procfs_add_ulong_dec_width(top, cur, locked_kb, 9, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	ADD_LIT(" kB\nThreads:\t");
	ADD_LONG(input->nr_threads);
	ADD_LIT("\n");
#undef ADD_TAB
#undef ADD_LONG
#undef ADD_LIT
	return 0;
}

static int procfs_status_add_cstr_line(struct mckernel_procfs_buffer **top,
				       struct mckernel_procfs_buffer **cur,
				       const char *prefix, const char *value,
				       int count,
				       procfs_buf_alloc_fn_t alloc_fn,
				       procfs_buf_free_top_fn_t free_top_fn,
				       procfs_buf_copy_fn_t copy_fn)
{
	int error;

	if (!value)
		return -EINVAL;
	error = procfs_line_len_valid(strlen(prefix) + strlen(value) + 1,
			count);
	if (error)
		return error;
	error = procfs_add_cstr(top, cur, prefix, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_cstr(top, cur, value, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	return procfs_add_bytes(top, cur, "\n", 1, alloc_fn, free_top_fn,
			copy_fn);
}

int procfs_status_body_result(const struct procfs_status_body_input *input,
			      int count, struct mckernel_procfs_buffer **top,
			      struct mckernel_procfs_buffer **cur,
			      procfs_buf_alloc_fn_t alloc_fn,
			      procfs_buf_free_top_fn_t free_top_fn,
			      procfs_buf_copy_fn_t copy_fn)
{
	int error;

	if (!input)
		return -EINVAL;
	error = procfs_status_add_head(top, cur, input,
			procfs_status_state_name(input->status), count, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_status_add_cstr_line(top, cur, "Cpus_allowed:\t",
			input->cpu_bitmask, count, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_status_add_cstr_line(top, cur,
			"Cpus_allowed_list:\t", input->cpu_list, count,
			alloc_fn, free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_status_add_cstr_line(top, cur, "Mems_allowed:\t",
			input->numa_bitmask, count, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	return procfs_status_add_cstr_line(top, cur, "Mems_allowed_list:\t",
			input->numa_list, count, alloc_fn, free_top_fn,
			copy_fn);
}

#define PROCFS_STAT_AFTER_PID_BEFORE_THREADS \
	" 0 0 0 0 0 0 0 0 0 0 0 0 0 0 "
#define PROCFS_STAT_AFTER_THREADS_BEFORE_CPU \
	" 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 "
#define PROCFS_STAT_AFTER_CPU " 0 0 0 0 0\n"

int procfs_stat_body_result(const struct procfs_stat_body_input *input,
			    int count, struct mckernel_procfs_buffer **top,
			    struct mckernel_procfs_buffer **cur,
			    procfs_buf_alloc_fn_t alloc_fn,
			    procfs_buf_free_top_fn_t free_top_fn,
			    procfs_buf_copy_fn_t copy_fn)
{
	size_t len;
	int error;

	if (!input || !input->comm)
		return -EINVAL;
	len = procfs_long_dec_len(input->tid) + strlen(" (") +
		strlen(input->comm) + strlen(") ") + 1 + 1 +
		procfs_long_dec_len(input->ppid) + 1 +
		procfs_long_dec_len(input->pid) +
		strlen(PROCFS_STAT_AFTER_PID_BEFORE_THREADS) +
		procfs_long_dec_len(input->nr_threads) +
		strlen(PROCFS_STAT_AFTER_THREADS_BEFORE_CPU) +
		procfs_long_dec_len(input->cpu_id) +
		strlen(PROCFS_STAT_AFTER_CPU);
	error = procfs_line_len_valid(len, count);
	if (error)
		return error;
	error = procfs_add_long_dec(top, cur, input->tid, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, " (", 2, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_cstr(top, cur, input->comm, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, ") ", 2, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_char(top, cur, input->state, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, " ", 1, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_long_dec(top, cur, input->ppid, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, " ", 1, alloc_fn, free_top_fn,
			copy_fn);
	if (error)
		return error;
	error = procfs_add_long_dec(top, cur, input->pid, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur, PROCFS_STAT_AFTER_PID_BEFORE_THREADS,
			strlen(PROCFS_STAT_AFTER_PID_BEFORE_THREADS), alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_long_dec(top, cur, input->nr_threads, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_bytes(top, cur,
			PROCFS_STAT_AFTER_THREADS_BEFORE_CPU,
			strlen(PROCFS_STAT_AFTER_THREADS_BEFORE_CPU),
			alloc_fn, free_top_fn, copy_fn);
	if (error)
		return error;
	error = procfs_add_long_dec(top, cur, input->cpu_id, alloc_fn,
			free_top_fn, copy_fn);
	if (error)
		return error;
	return procfs_add_bytes(top, cur, PROCFS_STAT_AFTER_CPU,
			strlen(PROCFS_STAT_AFTER_CPU), alloc_fn, free_top_fn,
			copy_fn);
}

int procfs_status_state_result(int status)
{
	if (status == PS_STOPPED)
		return PROCFS_STATUS_STOPPED;
	if (status == PS_TRACED)
		return PROCFS_STATUS_TRACED;
	if (status == PS_EXITED)
		return PROCFS_STATUS_EXITED;
	return PROCFS_STATUS_RUNNING;
}

char procfs_thread_stat_state_result(int status, int in_syscall_offload)
{
	switch (status & 0x3f) {
	case PS_INTERRUPTIBLE:
		return 'S';
	case PS_UNINTERRUPTIBLE:
		return 'D';
	case PS_ZOMBIE:
		return 'Z';
	case PS_EXITED:
		return 'X';
	case PS_STOPPED:
		return 'T';
	case PS_RUNNING:
	default:
		return in_syscall_offload > 0 ? 'S' : 'R';
	}
}

int procfs_default_count_result(void)
{
	return PAGE_SIZE;
}

int procfs_remote_count_result(unsigned long mapped_addr, int count)
{
	return count + (mapped_addr & (PAGE_SIZE - 1));
}

int procfs_remote_npages_result(int count)
{
	return (count + (PAGE_SIZE - 1)) / PAGE_SIZE;
}

int procfs_format_error_result(int ans, int count)
{
	return ans < 0 || ans > count;
}

unsigned long procfs_locked_kb_result(unsigned long lockedsize)
{
	return (lockedsize + 1023) >> 10;
}

char procfs_maps_read_char_result(unsigned long flags)
{
	return (flags & VR_PROT_READ) ? 'r' : '-';
}

char procfs_maps_write_char_result(unsigned long flags)
{
	return (flags & VR_PROT_WRITE) ? 'w' : '-';
}

char procfs_maps_exec_char_result(unsigned long flags)
{
	return (flags & VR_PROT_EXEC) ? 'x' : '-';
}

char procfs_maps_private_char_result(unsigned long flags)
{
	return (flags & VR_PRIVATE) ? 'p' : 's';
}

int procfs_maps_path_kind_result(unsigned long range_start,
				 unsigned long range_end,
				 unsigned long range_flags,
				 unsigned long vdso_addr,
				 unsigned long vvar_addr,
				 unsigned long brk_start,
				 unsigned long brk_end_allocated)
{
	if (range_start == vdso_addr)
		return PROCFS_MAPS_PATH_VDSO;
	if (range_start == vvar_addr)
		return PROCFS_MAPS_PATH_VVAR;
	if (range_flags & VR_STACK)
		return PROCFS_MAPS_PATH_STACK;
	if (range_start >= brk_start && range_end <= brk_end_allocated)
		return PROCFS_MAPS_PATH_HEAP;
	return PROCFS_MAPS_PATH_NONE;
}

unsigned long procfs_pagemap_next_result(unsigned long start)
{
	return start + PAGE_SIZE;
}

unsigned int procfs_auxv_limit_result(void)
{
	return AUXV_LEN * sizeof(unsigned long);
}

unsigned int procfs_cmdline_limit_result(uintptr_t saved_cmdline,
					 unsigned int saved_cmdline_len)
{
	return saved_cmdline ? saved_cmdline_len : 0;
}

int procfs_is_release_result(int msg)
{
	return msg == SCD_MSG_PROCFS_RELEASE;
}

int procfs_root_matched_result(int sscanf_ret)
{
	return sscanf_ret == 1;
}

int procfs_osnum_match_result(int osnum, int requested_osnum)
{
	return osnum == requested_osnum;
}

int procfs_zero_length_result(unsigned long left)
{
	return left == 0;
}

unsigned long procfs_locked_size_add_result(unsigned long lockedsize,
					    unsigned long range_start,
					    unsigned long range_end,
					    unsigned long flags)
{
	return (flags & VR_LOCKED) ? lockedsize + range_end - range_start :
		lockedsize;
}

int procfs_bitmask_next_offset_result(int offset, int written)
{
	return offset + written + 1;
}

int procfs_pbuf_is_empty_result(unsigned long pbuf)
{
	return pbuf == (unsigned long)-1;
}

int procfs_backlog_needed_result(uintptr_t resultp)
{
	return resultp == 0;
}

int procfs_lock_failed_action_result(uintptr_t resultp)
{
	return procfs_backlog_needed_result(resultp) ?
		PROCFS_LOCK_ACTION_BACKLOG : PROCFS_LOCK_ACTION_EAGAIN;
}

int procfs_lock_retry_result(void)
{
	return -EAGAIN;
}

int procfs_thread_tid_result(int task_match, int parsed_tid, int pid)
{
	return task_match ? parsed_tid : pid;
}

int procfs_task_missing_terminal_result(int task_match)
{
	return task_match != 0;
}

int procfs_pointer_present_result(uintptr_t ptr)
{
	return ptr != 0;
}

int procfs_buffer_chain_attach_result(unsigned long pbuf, uintptr_t buf_top)
{
	return procfs_pbuf_is_empty_result(pbuf) && buf_top != 0;
}

int procfs_entry_kind_result(const char *name)
{
	if (!name)
		return PROCFS_ENTRY_UNKNOWN;
	if (!strcmp(name, "mckernel"))
		return PROCFS_ENTRY_MCKERNEL;
	if (!strcmp(name, "stat"))
		return PROCFS_ENTRY_STAT;
	if (!strcmp(name, "cpuinfo"))
		return PROCFS_ENTRY_CPUINFO;
	if (!strcmp(name, "mem"))
		return PROCFS_ENTRY_MEM;
	if (!strcmp(name, "maps"))
		return PROCFS_ENTRY_MAPS;
	if (!strcmp(name, "pagemap"))
		return PROCFS_ENTRY_PAGEMAP;
	if (!strcmp(name, "status"))
		return PROCFS_ENTRY_STATUS;
	if (!strcmp(name, "auxv"))
		return PROCFS_ENTRY_AUXV;
	if (!strcmp(name, "cmdline"))
		return PROCFS_ENTRY_CMDLINE;
	if (!strcmp(name, "comm"))
		return PROCFS_ENTRY_COMM;
	return PROCFS_ENTRY_UNKNOWN;
}

uintptr_t procfs_comm_basename_result(uintptr_t saved_cmdline)
{
	const char *comm = (const char *)saved_cmdline;
	const char *slash;

	if (!comm)
		return 0;

	slash = strrchr(comm, '/');
	return (uintptr_t)(slash ? slash + 1 : comm);
}

uintptr_t procfs_comm_name_result(uintptr_t fallback, uintptr_t basename)
{
	return basename ? basename : fallback;
}

int pager_linux_io_retry_result(ssize_t ret)
{
	return ret == -EINTR;
}

int pager_linux_io_stop_result(ssize_t ret)
{
	return ret <= 0;
}

int pager_linux_io_first_result(ssize_t done)
{
	return done == 0;
}

ssize_t pager_linux_io_advance_result(ssize_t done, ssize_t ret)
{
	return done + ret;
}

size_t pager_linux_io_remaining_result(size_t remaining, ssize_t ret)
{
	return remaining - ret;
}

uintptr_t pager_linux_io_next_buf_result(uintptr_t buf, ssize_t ret)
{
	return buf + ret;
}

int pager_linux_io_complete_result(ssize_t done, size_t target)
{
	return done == target;
}

int pager_copy_fault_retry_result(int faulted)
{
	return !faulted;
}

int pager_copy_fault_error_result(int ret)
{
	return ret ? -EFAULT : 0;
}

int pager_myalloc_fits_result(size_t allocated, size_t request, size_t size)
{
	return (allocated + request) < size;
}

size_t pager_myalloc_next_alloced_result(size_t allocated, size_t request)
{
	return allocated + request;
}

int pager_copy_size_error_result(size_t size)
{
	return (size > PAGE_SIZE) ? -EFAULT : 0;
}

unsigned long pager_fault_addr_result(unsigned long addr)
{
	return addr & PAGE_MASK;
}

size_t pager_read_chunk_size_result(size_t off, size_t size)
{
	size_t chunk = size - off;

	return (chunk > PAGE_SIZE) ? PAGE_SIZE : chunk;
}

int pager_arealist_tail_room_result(int tail_count)
{
	if (tail_count < 128 - 1)
		return 128 - tail_count;
	return 0;
}

int pager_arealist_count_add_result(int count, int add)
{
	return count + add;
}

ssize_t pager_addrpair_size_result(unsigned long start, unsigned long end)
{
	return end - start;
}

ssize_t pager_file_pos_result(ssize_t off, ssize_t total_size)
{
	return off + total_size;
}

ssize_t pager_arealist_write_result(ssize_t written, int count,
				    size_t entry_size)
{
	return (written != entry_size * count) ? -1 : 0;
}

int pager_mlock_more_result(unsigned long start)
{
	return start == (unsigned long)-1;
}

unsigned long pager_mlock_next_start_result(unsigned long end)
{
	return end;
}

int pager_mlock_container_empty_result(uintptr_t from, uintptr_t tail,
				       int ccount, int tail_count)
{
	return from == tail && ccount == tail_count;
}

int pager_mlock_needs_next_result(int ccount, int cur_count)
{
	return ccount == cur_count;
}

int pager_mlock_reset_count_result(void)
{
	return 1;
}

int pager_mlock_next_count_result(int count)
{
	return count + 1;
}

ssize_t pager_pagein_data_pos_result(unsigned int swap_count,
				     unsigned int mlock_count,
				     size_t header_size, size_t area_size)
{
	return header_size + swap_count * area_size + mlock_count * area_size;
}

int pager_pageout_args_result(uintptr_t fname, uintptr_t buf, size_t size,
			      unsigned long user_start, unsigned long user_end)
{
	if (fname < user_start || fname >= user_end ||
	    buf < user_start || buf >= user_end ||
	    size > user_end - user_start)
		return -EINVAL;
	return 0;
}

int pager_skip_anon_range_result(int has_memobj, unsigned long start,
				 unsigned long text_start,
				 unsigned long stack_start,
				 unsigned long user_start,
				 unsigned long user_end,
				 unsigned long flags)
{
	return has_memobj || start == text_start || start == stack_start ||
		start < user_start || start >= user_end ||
		!(flags & VR_PROT_WRITE) || !(flags & VR_AP_USER);
}

int pager_range_locked_result(unsigned long flags)
{
	return !!(flags & VR_LOCKED);
}

int pager_skip_physical_removal_result(int flags)
{
	return !!(flags & 0x04);
}

int pager_fd_valid_result(int fd)
{
	return fd >= 0;
}

int pager_should_unlink_swap_result(long result)
{
	return result != 0;
}

long pager_io_short_result(long result)
{
	return result >= 0 ? -EIO : result;
}

int zeroobj_initial_flags_result(void)
{
	return MF_ZEROOBJ;
}

int zeroobj_initial_refcnt_result(void)
{
	return 2;
}

int zeroobj_initial_page_mode_result(void)
{
	return PM_MAPPED;
}

off_t zeroobj_initial_page_offset_result(void)
{
	return 0;
}

int zeroobj_get_page_validate_result(off_t off, int p2align, int has_page)
{
	if (off & ~PAGE_MASK)
		return -EINVAL;
	if (p2align != PAGE_P2ALIGN)
		return -ENOMEM;
	if (!has_page)
		return -ENOMEM;
	return 0;
}

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
	zeroobj_publish_fn_t publish_fn)
{
	void *obj = NULL;
	void *virt = NULL;
	void *page;
	uintptr_t phys;
	int error = 0;

	if (!lock || !ops || !log_fn || !lock_fn || !unlock_fn || !alloc_fn ||
	    !free_fn || !memset_fn || !obj_init_fn || !page_alloc_fn ||
	    !page_free_fn || !phys_fn || !page_insert_fn || !page_mode_fn ||
	    !duplicate_page_fn || !page_init_fn || !page_list_insert_fn ||
	    !publish_fn) {
		return -EINVAL;
	}

	lock_fn(lock);
	if (existing_obj) {
		log_fn(ZEROOBJ_LOG_ALREADY, 0, existing_obj, NULL, 0);
		goto out_unlock;
	}

	obj = alloc_fn(obj_size, IHK_MC_AP_NOWAIT);
	if (!obj) {
		error = -ENOMEM;
		log_fn(ZEROOBJ_LOG_KMALLOC_FAILED, error, NULL, NULL, 0);
		goto out_unlock;
	}

	memset_fn(obj, 0, obj_size);
	obj_init_fn(obj, ops);

	virt = page_alloc_fn(1, IHK_MC_AP_NOWAIT);
	if (!virt) {
		error = -ENOMEM;
		log_fn(ZEROOBJ_LOG_ALLOC_PAGES_FAILED, error, obj, NULL, 0);
		goto out_unlock;
	}

	phys = phys_fn(virt);
	page = page_insert_fn(phys);
	if (page_mode_fn(page) != PM_NONE) {
		error = -EINVAL;
		duplicate_page_fn(page);
		goto out_unlock;
	}

	memset_fn(virt, 0, PAGE_SIZE);
	page_init_fn(page);
	page_list_insert_fn(obj, page);
	virt = NULL;

	publish_fn(obj);
	obj = NULL;

out_unlock:
	unlock_fn(lock);
	if (virt) {
		page_free_fn(virt, 1);
	}
	if (obj) {
		free_fn(obj);
	}

	return error;
}

int zeroobj_create_body_result(void **objp, void *existing_obj,
			       zeroobj_alloc_singleton_fn_t alloc_fn,
			       zeroobj_get_singleton_fn_t get_singleton_fn,
			       zeroobj_ref_fn_t ref_fn,
			       zeroobj_log_fn_t log_fn)
{
	void *obj = existing_obj;
	int error;

	if (!objp || !alloc_fn || !get_singleton_fn || !ref_fn || !log_fn) {
		return -EINVAL;
	}

	if (!obj) {
		error = alloc_fn();
		if (error) {
			return error;
		}
		obj = get_singleton_fn();
		if (!obj) {
			log_fn(ZEROOBJ_LOG_KMALLOC_FAILED, -ENOMEM, NULL,
			       NULL, 0);
			return -ENOMEM;
		}
	}

	*objp = obj;
	ref_fn(obj);
	return 0;
}

int zeroobj_get_page_body_result(void)
{
	return 0;
}

int shmobj_init_pgshift_result(int init_pgshift)
{
	return init_pgshift ? init_pgshift : PAGE_SHIFT;
}

size_t shmobj_pgsize_result(int pgshift)
{
	return (size_t)1 << pgshift;
}

int shmobj_initial_flags_result(void)
{
	return MF_SHM;
}

int shmobj_indexed_flags_result(int flags)
{
	return flags | MF_SHMDT_OK | MF_IS_REMOVABLE;
}

size_t shmobj_real_segsz_result(size_t segsz, size_t pgsize)
{
	return (segsz + pgsize - 1) & ~(pgsize - 1);
}

int shmobj_page_contains_offset_result(off_t page_offset, int pgshift,
				       off_t off)
{
	return page_offset <= off && off < page_offset + (1UL << pgshift);
}

int shmobj_destroy_page_npages_result(int pgshift)
{
	return (size_t)1 << (pgshift - PAGE_SHIFT);
}

size_t shmobj_destroy_page_size_result(int pgshift)
{
	return (size_t)1 << pgshift;
}

int shmobj_destroy_index_word_result(int index)
{
	return index / 64;
}

unsigned long shmobj_destroy_index_mask_result(int index)
{
	return 1UL << (index % 64);
}

int shmlock_user_locked_result(size_t locked)
{
	return locked != 0;
}

int shmlock_user_match_result(int user_ruid, int ruid)
{
	return user_ruid == ruid;
}

int shmlock_user_is_list_head_result(uintptr_t chain, uintptr_t head)
{
	return chain == head;
}

size_t shmlock_user_after_unlock_result(size_t locked, size_t size)
{
	return locked - size;
}

int shmlock_user_should_free_result(size_t locked)
{
	return locked == 0;
}

int shmobj_has_user_result(uintptr_t user)
{
	return user != 0;
}

int shmobj_destroy_page_count_invalid_result(int count)
{
	return count != 1;
}

int shmobj_destroy_page_should_free_result(int count, int page_unmap_result)
{
	return count == 1 && page_unmap_result;
}

int shmobj_should_free_direct_result(int index)
{
	return index < 0;
}

int shmobj_destroy_missing_flag_result(int mode)
{
	return !(mode & SHM_DEST);
}

int shmobj_initial_refcnt_result(void)
{
	return 1;
}

int shmobj_initial_index_result(void)
{
	return -1;
}

int shmobj_initial_ds_pgshift_result(void)
{
	return 0;
}

int shmobj_get_page_validate_result(size_t real_segsz, off_t off,
				    int p2align)
{
	if (off & ~PAGE_MASK)
		return -EINVAL;
	if (real_segsz <= off)
		return -ERANGE;
	if ((real_segsz - off) < (PAGE_SIZE << p2align))
		return -ENOSPC;
	return 0;
}

int shmobj_lookup_page_validate_result(size_t real_segsz, off_t off)
{
	if (off & ~PAGE_MASK)
		return -EINVAL;
	if (real_segsz <= off)
		return -ERANGE;
	return 0;
}

int shmobj_page_npages_result(int p2align)
{
	return 1 << p2align;
}

int shmobj_page_pgshift_result(int p2align)
{
	return p2align + PAGE_SHIFT;
}

int shmobj_need_alloc_page_result(uintptr_t page)
{
	return page == 0;
}

int shmobj_new_page_mode_result(void)
{
	return PM_MAPPED;
}

int shmobj_new_page_count_result(void)
{
	return 1;
}

long shmobj_new_page_mapped_result(void)
{
	return 0;
}

int shmobj_page_mode_valid_for_new_result(int mode)
{
	return mode == PM_NONE;
}

int shmobj_lookup_page_missing_error_result(uintptr_t page)
{
	return page ? 0 : -ENOENT;
}

int shmobj_lookup_should_store_phys_result(uintptr_t physp)
{
	return physp != 0;
}

int shmobj_lookup_page_body_result(
	void *memobj, void *obj, size_t real_segsz, off_t off, int p2align,
	uintptr_t *physp, uintptr_t *resolved_physp, shmobj_ref_fn_t ref_fn,
	shmobj_unref_fn_t unref_fn, shmobj_page_list_lock_fn_t lock_fn,
	shmobj_page_list_unlock_fn_t unlock_fn,
	shmobj_page_lookup_fn_t lookup_fn, shmobj_page_phys_fn_t page_phys_fn,
	shmobj_lookup_log_fn_t log_fn)
{
	int error;
	void *page;
	uintptr_t phys = (uintptr_t)NOPHYS;

	if (!memobj || !obj || !ref_fn || !unref_fn || !lock_fn ||
	    !unlock_fn || !lookup_fn || !page_phys_fn || !log_fn) {
		return -EINVAL;
	}

	ref_fn(memobj);
	error = shmobj_lookup_page_validate_result(real_segsz, off);
	if (error == -EINVAL) {
		log_fn(SHMOBJ_LOG_LOOKUP_INVALID, memobj, off, p2align,
		       physp, error, phys);
		goto out;
	}
	if (error == -ERANGE) {
		log_fn(SHMOBJ_LOG_LOOKUP_RANGE, memobj, off, p2align,
		       physp, error, phys);
		goto out;
	}

	lock_fn(obj);
	page = lookup_fn(obj, off);
	unlock_fn(obj);
	error = shmobj_lookup_page_missing_error_result((uintptr_t)page);
	if (error) {
		log_fn(SHMOBJ_LOG_LOOKUP_MISSING, memobj, off, p2align,
		       physp, error, phys);
		goto out;
	}

	phys = page_phys_fn(page);
	if (resolved_physp) {
		*resolved_physp = phys;
	}
	error = 0;
	if (shmobj_lookup_should_store_phys_result((uintptr_t)physp)) {
		*physp = phys;
	}

out:
	unref_fn(memobj);
	return error;
}

int shmobj_update_args_result(int has_pt, int has_orig_page, int has_vaddr)
{
	return (has_pt && has_orig_page && has_vaddr) ? 0 : -ENOENT;
}

size_t shmobj_update_orig_pgsize_result(int pgshift)
{
	return 1UL << pgshift;
}

uintptr_t shmobj_update_page_phys_result(uintptr_t base_phys, size_t page_off)
{
	return base_phys + page_off;
}

off_t shmobj_update_page_offset_result(off_t orig_offset, size_t page_off)
{
	return orig_offset + page_off;
}

int shmobj_pte_missing_result(uintptr_t pte)
{
	return pte == 0 ? -ENOENT : 0;
}

int shmobj_update_has_more_pages_result(size_t page_off, size_t orig_pgsize)
{
	return page_off < orig_pgsize;
}

size_t shmobj_update_next_page_off_result(size_t page_off, size_t pte_size)
{
	return page_off + pte_size;
}

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
	shmobj_update_log_fn_t log_fn)
{
	int error;
	void *pte;
	size_t pte_size;
	size_t orig_pgsize;
	size_t page_off;
	int p2align;
	uintptr_t base_phys;

	if (!memobj || !ref_fn || !unref_fn || !page_phys_fn ||
	    !pte_lookup_fn || !page_pgshift_fn || !page_set_pgshift_fn ||
	    !page_mode_fn || !page_set_mode_fn || !page_offset_fn ||
	    !page_set_offset_fn || !page_count_fn || !page_set_count_fn ||
	    !page_mapped_fn || !page_set_mapped_fn || !page_insert_hash_fn ||
	    !page_list_insert_fn || !log_fn) {
		return -EINVAL;
	}

	ref_fn(memobj);

	error = shmobj_update_args_result(!!pt, !!orig_page, !!vaddr);
	if (error) {
		log_fn(SHMOBJ_LOG_UPDATE_INVALID, memobj, pt, orig_page,
		       vaddr, error);
		goto out;
	}

	base_phys = page_phys_fn(orig_page);
	pte = pte_lookup_fn(pt, vaddr, &pte_size, &p2align);
	error = shmobj_pte_missing_result((uintptr_t)pte);
	if (error) {
		log_fn(SHMOBJ_LOG_UPDATE_PTE_MISSING, memobj, pt,
		       orig_page, vaddr, error);
		goto out;
	}

	orig_pgsize = shmobj_update_orig_pgsize_result(
		page_pgshift_fn(orig_page));
	page_set_pgshift_fn(orig_page, shmobj_page_pgshift_result(p2align));

	page_off = pte_size;
	while (shmobj_update_has_more_pages_result(page_off, orig_pgsize)) {
		void *page;
		uintptr_t phys;

		pte = pte_lookup_fn(pt, (void *)((uintptr_t)vaddr + page_off),
				    &pte_size, &p2align);
		error = shmobj_pte_missing_result((uintptr_t)pte);
		if (error) {
			log_fn(SHMOBJ_LOG_UPDATE_PTE_MISSING, memobj, pt,
			       orig_page, vaddr, error);
			goto out;
		}

		phys = shmobj_update_page_phys_result(base_phys, page_off);
		page = page_insert_hash_fn(phys);

		page_set_mode_fn(page, page_mode_fn(orig_page));
		page_set_offset_fn(page, shmobj_update_page_offset_result(
					   page_offset_fn(orig_page),
					   page_off));
		page_set_pgshift_fn(page, shmobj_page_pgshift_result(p2align));
		page_set_count_fn(page, page_count_fn(orig_page));
		page_set_mapped_fn(page, page_mapped_fn(orig_page));
		page_list_insert_fn(obj, page);

		page_off = shmobj_update_next_page_off_result(
			page_off, pte_size);
	}

	error = 0;

out:
	unref_fn(memobj);
	return error;
}

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
	shmobj_panic_fn_t panic_fn, shmobj_get_log_fn_t log_fn)
{
	int error;
	void *page;
	void *virt = NULL;
	uintptr_t phys = (uintptr_t)-1;
	int npages = 0;

	if (!memobj || !obj || !physp || !ref_fn || !unref_fn || !lock_fn ||
	    !unlock_fn || !lookup_fn || !alloc_page_fn || !free_page_fn ||
	    !virt_to_phys_fn || !page_insert_hash_fn || !page_mode_fn ||
	    !page_set_mode_fn || !page_set_offset_fn ||
	    !page_set_pgshift_fn || !page_set_count_fn ||
	    !page_set_mapped_fn || !page_list_insert_fn ||
	    !page_count_inc_fn || !page_phys_fn || !memset_fn || !panic_fn ||
	    !log_fn) {
		return -EINVAL;
	}

	ref_fn(memobj);
	error = shmobj_get_page_validate_result(real_segsz, off, p2align);
	if (error == -EINVAL) {
		log_fn(SHMOBJ_LOG_GET_INVALID, memobj, off, p2align, physp,
		       error, NULL, phys);
		goto out;
	}
	if (error == -ERANGE) {
		log_fn(SHMOBJ_LOG_GET_RANGE, memobj, off, p2align, physp,
		       error, NULL, phys);
		goto out;
	}
	if (error == -ENOSPC) {
		log_fn(SHMOBJ_LOG_GET_TOO_LARGE, memobj, off, p2align, physp,
		       error, NULL, phys);
		goto out;
	}

	lock_fn(obj);
	page = lookup_fn(obj, off);
	if (shmobj_need_alloc_page_result((uintptr_t)page)) {
		npages = shmobj_page_npages_result(p2align);
		virt = alloc_page_fn(npages, p2align, IHK_MC_AP_NOWAIT,
				     virt_addr);
		if (!virt) {
			unlock_fn(obj);
			error = -ENOMEM;
			log_fn(SHMOBJ_LOG_GET_ALLOC_FAILED, memobj, off,
			       p2align, physp, error, NULL, phys);
			goto out;
		}

		phys = virt_to_phys_fn(virt);
		page = page_insert_hash_fn(phys);
		if (!shmobj_page_mode_valid_for_new_result(
			    page_mode_fn(page))) {
			error = -EINVAL;
			log_fn(SHMOBJ_LOG_GET_PAGE_INVALID, memobj, off,
			       p2align, physp, error, page, phys);
			panic_fn();
			unlock_fn(obj);
			goto out;
		}

		memset_fn(virt, 0, shmobj_page_npages_result(p2align) *
				    PAGE_SIZE);
		page_set_mode_fn(page, shmobj_new_page_mode_result());
		page_set_offset_fn(page, off);
		page_set_pgshift_fn(page, shmobj_page_pgshift_result(p2align));
		page_set_count_fn(page, shmobj_new_page_count_result());
		page_set_mapped_fn(page, shmobj_new_page_mapped_result());
		page_list_insert_fn(obj, page);
		virt = NULL;
		log_fn(SHMOBJ_LOG_GET_ALLOCATED, memobj, off, p2align,
		       physp, 0, page, phys);
	}
	unlock_fn(obj);

	page_count_inc_fn(page);
	error = 0;
	*physp = page_phys_fn(page);

out:
	unref_fn(memobj);
	if (virt) {
		free_page_fn(virt, npages);
	}
	return error;
}

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
	shmobj_destroy_log_fn_t log_fn)
{
	if (!obj || !user_clear_fn || !user_locked_fn || !user_set_locked_fn ||
	    !users_lock_fn || !users_unlock_fn || !user_free_fn ||
	    !page_first_fn || !page_remove_fn || !page_phys_fn ||
	    !phys_to_virt_fn || !page_pgshift_fn || !page_count_fn ||
	    !page_unmap_fn || !free_page_fn || !rss_sub_fn || !free_fn ||
	    !indexed_free_fn || !log_fn) {
		return -EINVAL;
	}

	if (shmobj_has_user_result((uintptr_t)user)) {
		size_t locked;

		user_clear_fn(obj);
		users_lock_fn(obj);
		locked = shmlock_user_after_unlock_result(
			user_locked_fn(user), real_segsz);
		user_set_locked_fn(user, locked);
		if (shmlock_user_should_free_result(locked)) {
			user_free_fn(user);
		}
		users_unlock_fn(obj);
	}

	for (;;) {
		void *page;
		void *page_va;
		uintptr_t phys;
		int pgshift;
		int npages;
		int count;

		page = page_first_fn(obj);
		if (!page) {
			break;
		}

		page_remove_fn(obj, page);
		phys = page_phys_fn(page);
		page_va = phys_to_virt_fn(phys);
		pgshift = page_pgshift_fn(page);
		npages = shmobj_destroy_page_npages_result(pgshift);
		count = page_count_fn(page);

		if (shmobj_destroy_page_count_invalid_result(count)) {
			log_fn(SHMOBJ_LOG_DESTROY_PAGE_COUNT_INVALID, obj, page,
			       phys, 0, 0);
		} else if (shmobj_destroy_page_should_free_result(
				   count, page_unmap_fn(page))) {
			size_t free_pgsize =
				shmobj_destroy_page_size_result(pgshift);
			size_t free_size =
				shmobj_destroy_page_size_result(pgshift);

			free_page_fn(page_va, npages);
			log_fn(SHMOBJ_LOG_DESTROY_RSS_SUB, obj, page, phys,
			       free_size, free_pgsize);
			rss_sub_fn(free_size, free_pgsize);
			free_fn(page);
		}
	}

	if (shmobj_should_free_direct_result(index)) {
		free_fn(obj);
	} else {
		indexed_free_fn(obj, shmobj_destroy_index_word_result(index),
				shmobj_destroy_index_mask_result(index));
	}

	return 0;
}

int shmobj_free_body_result(void *memobj, void *obj, int mode,
			    shmobj_page_list_lock_fn_t list_lock_fn,
			    shmobj_page_list_unlock_fn_t list_unlock_fn,
			    shmobj_destroy_fn_t destroy_fn,
			    shmobj_free_log_fn_t log_fn)
{
	if (!obj || !list_lock_fn || !list_unlock_fn || !destroy_fn ||
	    !log_fn) {
		return -EINVAL;
	}

	list_lock_fn(obj);
	if (shmobj_destroy_missing_flag_result(mode)) {
		log_fn(SHMOBJ_LOG_FREE_MISSING_DEST, memobj);
	}
	destroy_fn(obj);
	list_unlock_fn(obj);

	return 0;
}

int shmobj_create_body_result(
	void *ds, void **objp, size_t segsz, int init_pgshift, size_t obj_size,
	shmobj_alloc_fn_t alloc_fn, shmobj_free_fn_t free_fn,
	shmobj_memset_fn_t memset_fn, shmobj_next_seq_fn_t next_seq_fn,
	shmobj_create_init_fn_t init_fn, shmobj_create_log_fn_t log_fn)
{
	void *obj;
	void *memobj;
	int pgshift;
	size_t pgsize;
	size_t real_segsz;
	int seq;
	int error;

	if (!ds || !objp || !alloc_fn || !free_fn || !memset_fn ||
	    !next_seq_fn || !init_fn || !log_fn) {
		return -EINVAL;
	}

	pgshift = shmobj_init_pgshift_result(init_pgshift);
	pgsize = shmobj_pgsize_result(pgshift);
	real_segsz = shmobj_real_segsz_result(segsz, pgsize);

	obj = alloc_fn(obj_size, IHK_MC_AP_NOWAIT);
	if (!obj) {
		error = -ENOMEM;
		log_fn(SHMOBJ_LOG_CREATE_ALLOC_FAILED, ds, objp, error);
		return error;
	}

	memset_fn(obj, 0, obj_size);
	seq = next_seq_fn();
	memobj = init_fn(obj, ds, pgshift, pgsize, real_segsz, seq);
	if (!memobj) {
		free_fn(obj);
		return -EINVAL;
	}

	*objp = memobj;
	return 0;
}

int shmobj_create_indexed_body_result(
	void *ds, void **objp, shmobj_create_fn_t create_fn,
	shmobj_memobj_flags_fn_t flags_fn,
	shmobj_memobj_set_flags_fn_t set_flags_fn,
	shmobj_to_shmobj_fn_t to_shmobj_fn)
{
	void *memobj = NULL;
	int error;
	int flags;

	if (!ds || !objp || !create_fn || !flags_fn || !set_flags_fn ||
	    !to_shmobj_fn) {
		return -EINVAL;
	}

	error = create_fn(ds, &memobj);
	if (!error) {
		flags = shmobj_indexed_flags_result(flags_fn(memobj));
		set_flags_fn(memobj, flags);
		*objp = to_shmobj_fn(memobj);
	}

	return error;
}

int shmlock_user_free_body_result(
	void *user, shmobj_user_locked_fn_t user_locked_fn,
	shmlock_user_list_fn_t list_del_fn, shmobj_free_fn_t free_fn,
	shmobj_panic_fn_t panic_fn)
{
	if (!user || !user_locked_fn || !list_del_fn || !free_fn ||
	    !panic_fn) {
		return -EINVAL;
	}

	if (shmlock_user_locked_result(user_locked_fn(user))) {
		panic_fn();
	}
	list_del_fn(user);
	free_fn(user);

	return 0;
}

int shmlock_user_get_body_result(
	int ruid, void **userp, size_t user_size,
	shmlock_user_first_fn_t first_fn, shmlock_user_next_fn_t next_fn,
	shmlock_user_ruid_fn_t ruid_fn, shmobj_alloc_fn_t alloc_fn,
	shmlock_user_init_fn_t init_fn, shmlock_user_list_fn_t list_add_fn)
{
	void *user;

	if (!userp || !first_fn || !next_fn || !ruid_fn || !alloc_fn ||
	    !init_fn || !list_add_fn) {
		return -EINVAL;
	}

	for (user = first_fn(); user; user = next_fn(user)) {
		if (shmlock_user_match_result(ruid_fn(user), ruid)) {
			break;
		}
	}

	if (!user) {
		user = alloc_fn(user_size, IHK_MC_AP_NOWAIT);
		if (!user) {
			return -ENOMEM;
		}
		init_fn(user, ruid);
		list_add_fn(user);
	}

	*userp = user;
	return 0;
}

size_t gencore_align32_result(size_t value)
{
	return ((value + 3) / 4) * 4;
}

size_t gencore_alignpage_result(size_t value)
{
	return ((value + PAGE_SIZE - 1) / PAGE_SIZE) * PAGE_SIZE;
}

int gencore_range_inaccessible_result(unsigned long flags)
{
	return (flags & (VR_RESERVED | VR_MEMTYPE_UC | VR_DONTDUMP)) != 0;
}

int gencore_prstatus_size_result(void)
{
	return sizeof(struct note) + gencore_align32_result(sizeof("CORE")) +
		gencore_align32_result(sizeof(struct elf_prstatus64));
}

int gencore_prpsinfo_size_result(void)
{
	return sizeof(struct note) + gencore_align32_result(sizeof("CORE")) +
		gencore_align32_result(sizeof(struct elf_prpsinfo64));
}

int gencore_auxv_size_result(void)
{
	return sizeof(struct note) + gencore_align32_result(sizeof("CORE")) +
		sizeof(unsigned long) * AUXV_LEN;
}

int gencore_fill_elf_header_body_result(void *ehp, int segs)
{
	Elf64_Ehdr *eh = ehp;

	if (!eh) {
		return -EINVAL;
	}

	eh->e_ident[EI_MAG0] = 0x7f;
	eh->e_ident[EI_MAG1] = 'E';
	eh->e_ident[EI_MAG2] = 'L';
	eh->e_ident[EI_MAG3] = 'F';
	eh->e_ident[EI_CLASS] = ELF_CLASS;
	eh->e_ident[EI_DATA] = ELF_DATA;
	eh->e_ident[EI_VERSION] = El_VERSION;
	eh->e_ident[EI_OSABI] = ELF_OSABI;
	eh->e_ident[EI_ABIVERSION] = ELF_ABIVERSION;
	eh->e_type = ET_CORE;
	eh->e_machine = ELF_ARCH;
	eh->e_version = EV_CURRENT;
	eh->e_entry = 0;
	eh->e_phoff = 64;
	eh->e_shoff = 0;
	eh->e_flags = 0;
	eh->e_ehsize = 64;
	eh->e_phentsize = 56;
	eh->e_phnum = segs;
	eh->e_shentsize = 0;
	eh->e_shnum = 0;
	eh->e_shstrndx = 0;

	return 0;
}

int gencore_fill_prstatus_body_result(
	void *headp, void *thread, void *regs, int sig,
	gencore_arch_fill_prstatus_fn_t arch_fill_prstatus_fn)
{
	struct note *head = headp;
	void *name;
	struct elf_prstatus64 *prstatus;

	if (!head || !thread || !arch_fill_prstatus_fn) {
		return -EINVAL;
	}

	head->namesz = sizeof("CORE");
	head->descsz = sizeof(struct elf_prstatus64);
	head->type = NT_PRSTATUS;
	name = (void *)(head + 1);
	memcpy(name, "CORE", sizeof("CORE"));
	prstatus = (struct elf_prstatus64 *)(name +
					     gencore_align32_result(sizeof("CORE")));
	arch_fill_prstatus_fn(prstatus, thread, regs, sig);

	return 0;
}

int gencore_fill_prpsinfo_body_result(void *headp, int status, int pid,
				      const char *cmdline)
{
	struct note *head = headp;
	void *name;
	struct elf_prpsinfo64 *prpsinfo;

	if (!head || !cmdline) {
		return -EINVAL;
	}

	head->namesz = sizeof("CORE");
	head->descsz = sizeof(struct elf_prpsinfo64);
	head->type = NT_PRPSINFO;
	name = (void *)(head + 1);
	memcpy(name, "CORE", sizeof("CORE"));
	prpsinfo = (struct elf_prpsinfo64 *)(name +
					     gencore_align32_result(sizeof("CORE")));
	prpsinfo->pr_state = status;
	prpsinfo->pr_pid = pid;
	memcpy(prpsinfo->pr_fname, cmdline, 16);

	return 0;
}

int gencore_fill_auxv_body_result(void *headp, const unsigned long *saved_auxv)
{
	struct note *head = headp;
	void *name;
	void *auxv;

	if (!head || !saved_auxv) {
		return -EINVAL;
	}

	head->namesz = sizeof("CORE");
	head->descsz = sizeof(unsigned long) * AUXV_LEN;
	head->type = NT_AUXV;
	name = (void *)(head + 1);
	memcpy(name, "CORE", sizeof("CORE"));
	auxv = name + gencore_align32_result(sizeof("CORE"));
	memcpy(auxv, saved_auxv, sizeof(unsigned long) * AUXV_LEN);

	return 0;
}

int gencore_fill_note_phdr_body_result(void *php, unsigned long offset,
				       long notesize)
{
	Elf64_Phdr *ph = php;

	if (!ph) {
		return -EINVAL;
	}

	ph->p_type = PT_NOTE;
	ph->p_flags = 0;
	ph->p_offset = offset;
	ph->p_vaddr = 0;
	ph->p_paddr = 0;
	ph->p_filesz = notesize;
	ph->p_memsz = notesize;
	ph->p_align = 0;

	return 0;
}

int gencore_fill_load_phdr_body_result(void *php, unsigned long flags,
				       unsigned long offset,
				       unsigned long start, unsigned long size)
{
	Elf64_Phdr *ph = php;

	if (!ph) {
		return -EINVAL;
	}

	ph->p_type = PT_LOAD;
	ph->p_flags = ((flags & VR_PROT_READ) ? PF_R : 0)
		| ((flags & VR_PROT_WRITE) ? PF_W : 0)
		| ((flags & VR_PROT_EXEC) ? PF_X : 0);
	ph->p_offset = offset;
	ph->p_vaddr = start;
	ph->p_paddr = 0;
	ph->p_filesz = size;
	ph->p_memsz = size;
	ph->p_align = PAGE_SIZE;

	return 0;
}

int gencore_fill_initial_coretable_body_result(
	void *ctp, unsigned long eh_phys, unsigned long ph_phys,
	unsigned long note_phys, long phsize, long alignednotesize)
{
	struct coretable *ct = ctp;

	if (!ct) {
		return -EINVAL;
	}

	ct[0].addr = eh_phys;
	ct[0].len = 64;
	ct[1].addr = ph_phys;
	ct[1].len = phsize;
	ct[2].addr = note_phys;
	ct[2].len = alignednotesize;

	return 0;
}

int gencore_count_range_chunks_body_result(
	unsigned long start, unsigned long end, unsigned long flags,
	void *page_table, int *chunks,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn)
{
	unsigned long p;
	unsigned long phys;
	int prevzero = 0;

	if (!chunks) {
		return -EINVAL;
	}

	if (!(flags & VR_DEMAND_PAGING)) {
		(*chunks)++;
		return 0;
	}

	if (!pt_virt_to_phys_fn) {
		return -EINVAL;
	}

	for (p = start; p < end; p += PAGE_SIZE) {
		if (pt_virt_to_phys_fn(page_table, p, &phys) != 0) {
			prevzero = 1;
		} else {
			if (prevzero == 1) {
				(*chunks)++;
			}
			(*chunks)++;
			prevzero = 0;
		}
	}
	if (prevzero == 1) {
		(*chunks)++;
	}

	return 0;
}

int gencore_scan_ranges_for_counts_body_result(
	void *vm, void *page_table, int *chunks, int *segs,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn,
	gencore_range_offset_fn_t objoff_fn,
	gencore_range_log_fn_t log_fn,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn)
{
	void *range;
	void *next_range;
	unsigned long start;
	unsigned long end;
	unsigned long flags;
	long objoff;
	int error;

	if (!chunks || !segs || !lookup_fn || !next_fn || !start_fn ||
	    !end_fn || !flag_fn || !objoff_fn || !log_fn) {
		return -EINVAL;
	}

	range = lookup_fn(vm);
	while (range) {
		next_range = next_fn(vm, range);
		start = start_fn(range);
		end = end_fn(range);
		flags = flag_fn(range);
		objoff = objoff_fn(range);
		log_fn(start, end, flags, objoff);

		if (!gencore_range_inaccessible_result(flags)) {
			error = gencore_count_range_chunks_body_result(
				start, end, flags, page_table, chunks,
				pt_virt_to_phys_fn);
			if (error) {
				return error;
			}
			(*segs)++;
		}

		range = next_range;
	}

	return 0;
}

int gencore_fill_load_phdrs_body_result(
	void *vm, void *php, int *indexp, unsigned long *offsetp,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn)
{
	Elf64_Phdr *ph = php;
	void *range;
	void *next_range;
	unsigned long start;
	unsigned long end;
	unsigned long flags;
	unsigned long size;
	int error;
	int i;
	unsigned long offset;

	if (!ph || !indexp || !offsetp || !lookup_fn || !next_fn ||
	    !start_fn || !end_fn || !flag_fn) {
		return -EINVAL;
	}

	i = *indexp;
	offset = *offsetp;
	range = lookup_fn(vm);
	while (range) {
		next_range = next_fn(vm, range);
		start = start_fn(range);
		end = end_fn(range);
		flags = flag_fn(range);

		if (!gencore_range_inaccessible_result(flags)) {
			size = end - start;
			error = gencore_fill_load_phdr_body_result(
				&ph[i], flags, offset, start, size);
			if (error) {
				return error;
			}
			i++;
			offset += size;
		}

		range = next_range;
	}

	*indexp = i;
	*offsetp = offset;
	return 0;
}

int gencore_emit_demand_coretable_body_result(
	void *ctp, int *indexp, unsigned long start, unsigned long end,
	void *page_table, gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_coretable_log_fn_t log_fn)
{
	struct coretable *ct = ctp;
	unsigned long p;
	unsigned long zero_start;
	unsigned long phys;
	unsigned long size = 0;
	int prevzero = 0;
	int i;

	if (!ct || !indexp || !pt_virt_to_phys_fn || !log_fn) {
		return -EINVAL;
	}

	i = *indexp;
	for (zero_start = p = start; p < end; p += PAGE_SIZE) {
		if (pt_virt_to_phys_fn(page_table, p, &phys) != 0) {
			if (prevzero == 0) {
				size = PAGE_SIZE;
				zero_start = p;
			} else {
				size += PAGE_SIZE;
			}
			prevzero = 1;
		} else {
			if (prevzero == 1) {
				ct[i].addr = 0;
				ct[i].len = size;
				log_fn(i, ct[i].len, ct[i].addr, zero_start);
				i++;
			}
			ct[i].addr = phys;
			ct[i].len = PAGE_SIZE;
			log_fn(i, ct[i].len, ct[i].addr, p);
			i++;
			prevzero = 0;
		}
	}
	if (prevzero == 1) {
		ct[i].addr = 0;
		ct[i].len = size;
		log_fn(i, ct[i].len, ct[i].addr, zero_start);
		i++;
	}

	*indexp = i;
	return 0;
}

int gencore_emit_linear_coretable_body_result(
	void *ctp, int *indexp, unsigned long start, unsigned long end,
	unsigned long user_start, unsigned long user_end, void *page_table,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_virt_to_phys_fn_t virt_to_phys_fn,
	gencore_coretable_log_fn_t log_fn)
{
	struct coretable *ct = ctp;
	unsigned long phys;
	int error;
	int i;

	if (!ct || !indexp || !pt_virt_to_phys_fn || !virt_to_phys_fn ||
	    !log_fn) {
		return -EINVAL;
	}

	if ((user_start <= start) && (end <= user_end)) {
		error = pt_virt_to_phys_fn(page_table, start, &phys);
		if (error) {
			if (error != -EFAULT) {
				return error;
			}
			phys = 0;
		}
	} else {
		phys = virt_to_phys_fn(start);
	}

	i = *indexp;
	ct[i].addr = phys;
	ct[i].len = end - start;
	log_fn(i, ct[i].len, ct[i].addr, start);
	*indexp = i + 1;

	return 0;
}

int gencore_emit_coretable_ranges_body_result(
	void *vm, void *ctp, int *indexp, unsigned long user_start,
	unsigned long user_end, void *page_table, unsigned long *error_startp,
	gencore_lookup_range_fn_t lookup_fn,
	gencore_next_range_fn_t next_fn,
	gencore_range_ulong_fn_t start_fn,
	gencore_range_ulong_fn_t end_fn,
	gencore_range_ulong_fn_t flag_fn,
	gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
	gencore_virt_to_phys_fn_t virt_to_phys_fn,
	gencore_coretable_log_fn_t log_fn)
{
	void *range;
	void *next_range;
	unsigned long start;
	unsigned long end;
	unsigned long flags;
	int error;

	if (!ctp || !indexp || !lookup_fn || !next_fn || !start_fn ||
	    !end_fn || !flag_fn) {
		return -EINVAL;
	}

	range = lookup_fn(vm);
	while (range) {
		next_range = next_fn(vm, range);
		start = start_fn(range);
		end = end_fn(range);
		flags = flag_fn(range);

		if (!gencore_range_inaccessible_result(flags)) {
			if (flags & VR_DEMAND_PAGING) {
				error = gencore_emit_demand_coretable_body_result(
					ctp, indexp, start, end, page_table,
					pt_virt_to_phys_fn, log_fn);
			} else {
				error = gencore_emit_linear_coretable_body_result(
					ctp, indexp, start, end, user_start,
					user_end, page_table,
					pt_virt_to_phys_fn, virt_to_phys_fn,
					log_fn);
			}
			if (error) {
				if (error_startp) {
					*error_startp = start;
				}
				return error;
			}
		}

		range = next_range;
	}

	return 0;
}

int gencore_freecore_body_result(void **coretablep,
				 gencore_phys_to_virt_fn_t phys_to_virt_fn,
				 gencore_free_fn_t free_fn)
{
	struct coretable *ct;

	if (!coretablep || !*coretablep || !phys_to_virt_fn || !free_fn) {
		return -EINVAL;
	}

	ct = *coretablep;
	free_fn(phys_to_virt_fn(ct[2].addr));
	free_fn(phys_to_virt_fn(ct[1].addr));
	free_fn(phys_to_virt_fn(ct[0].addr));
	free_fn(*coretablep);

	return 0;
}

int gencore_note_size_threads_body_result(
	void *proc, int pid, gencore_first_thread_fn_t first_fn,
	gencore_next_thread_fn_t next_fn,
	gencore_thread_tid_fn_t tid_fn,
	gencore_arch_thread_info_size_fn_t arch_size_fn)
{
	void *thread;
	int note = 0;

	if (!proc || !first_fn || !next_fn || !tid_fn || !arch_size_fn) {
		return -EINVAL;
	}

	thread = first_fn(proc);
	while (thread) {
		note += gencore_prstatus_size_result();
		note += arch_size_fn();
		if (tid_fn(thread) == pid) {
			note += gencore_prpsinfo_size_result();
			note += gencore_auxv_size_result();
		}
		thread = next_fn(proc, thread);
	}

	return note;
}

int gencore_fill_note_threads_body_result(
	void *notep, void *proc, char *cmdline, int sig, int pid,
	void **end_notep, gencore_first_thread_fn_t first_fn,
	gencore_next_thread_fn_t next_fn,
	gencore_thread_tid_fn_t tid_fn,
	gencore_thread_regs_fn_t regs_fn,
	gencore_arch_thread_info_size_fn_t arch_size_fn,
	gencore_fill_prstatus_note_fn_t fill_prstatus_fn,
	gencore_arch_fill_thread_info_fn_t arch_fill_fn,
	gencore_fill_proc_note_fn_t fill_prpsinfo_fn,
	gencore_fill_auxv_note_fn_t fill_auxv_fn)
{
	char *note = notep;
	void *thread;

	if (!note || !proc || !cmdline || !first_fn || !next_fn || !tid_fn ||
	    !regs_fn || !arch_size_fn || !fill_prstatus_fn || !arch_fill_fn ||
	    !fill_prpsinfo_fn || !fill_auxv_fn) {
		return -EINVAL;
	}

	thread = first_fn(proc);
	while (thread) {
		fill_prstatus_fn(note, thread, sig);
		note += gencore_prstatus_size_result();

		arch_fill_fn(note, thread, regs_fn(thread));
		note += arch_size_fn();

		if (tid_fn(thread) == pid) {
			fill_prpsinfo_fn(note, proc, cmdline);
			note += gencore_prpsinfo_size_result();
			fill_auxv_fn(note, proc);
			note += gencore_auxv_size_result();
		}

		thread = next_fn(proc, thread);
	}
	if (end_notep) {
		*end_notep = note;
	}

	return 0;
}

static void gencore_cleanup_generated_body(void *eh, void *ct, void *ph,
					   void *note,
					   gencore_free_fn_t free_fn)
{
	free_fn(eh);
	free_fn(ct);
	free_fn(ph);
	free_fn(note);
}

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
	gencore_pt_error_log_fn_t pt_error_log_fn)
{
	void *eh = NULL;
	Elf64_Phdr *ph = NULL;
	void *note = NULL;
	struct coretable *ct = NULL;
	unsigned long offset = 0;
	int notesize;
	unsigned long alignednotesize;
	size_t phsize;
	size_t ctsize;
	unsigned long error_start = 0;
	int i;
	int error;

	if (!proc || !vm || !coretablep || !chunks || !cmdline || segs <= 0 ||
	    !alloc_fn || !zero_fn || !free_fn || !get_note_size_fn ||
	    !fill_note_fn || !virt_to_phys_fn || !coretable_log_fn ||
	    !alloc_error_log_fn || !pt_error_log_fn) {
		return -EINVAL;
	}

	eh = alloc_fn(eh_size, IHK_MC_AP_NOWAIT);
	if (!eh) {
		alloc_error_log_fn(0);
		return -ENOMEM;
	}
	zero_fn(eh, eh_size);
	offset += eh_size;
	error = gencore_fill_elf_header_body_result(eh, segs);
	if (error) {
		goto fail;
	}

	phsize = phdr_size * segs;
	ph = alloc_fn(phsize, IHK_MC_AP_NOWAIT);
	if (!ph) {
		alloc_error_log_fn(1);
		error = -ENOMEM;
		goto fail;
	}
	zero_fn(ph, phsize);
	offset += phsize;

	notesize = get_note_size_fn(proc);
	alignednotesize = gencore_alignpage_result(notesize + offset) - offset;
	note = alloc_fn(alignednotesize, IHK_MC_AP_NOWAIT);
	if (!note) {
		alloc_error_log_fn(2);
		error = -ENOMEM;
		goto fail;
	}
	zero_fn(note, alignednotesize);
	fill_note_fn(note, proc, cmdline, sig);

	error = gencore_fill_note_phdr_body_result(ph, offset, notesize);
	if (error) {
		goto fail;
	}
	offset += alignednotesize;

	i = 1;
	error = gencore_fill_load_phdrs_body_result(
		vm, ph, &i, &offset, lookup_fn, next_fn, start_fn, end_fn,
		flag_fn);
	if (error) {
		goto fail;
	}

	ctsize = coretable_size * (*chunks);
	ct = alloc_fn(ctsize, IHK_MC_AP_NOWAIT);
	if (!ct) {
		alloc_error_log_fn(3);
		error = -ENOMEM;
		goto fail;
	}
	zero_fn(ct, ctsize);

	error = gencore_fill_initial_coretable_body_result(
		ct, virt_to_phys_fn((unsigned long)eh),
		virt_to_phys_fn((unsigned long)ph),
		virt_to_phys_fn((unsigned long)note), phsize,
		alignednotesize);
	if (error) {
		goto fail;
	}
	coretable_log_fn(0, ct[0].len, ct[0].addr, (unsigned long)eh);
	coretable_log_fn(1, ct[1].len, ct[1].addr, (unsigned long)ph);
	coretable_log_fn(2, ct[2].len, ct[2].addr, (unsigned long)note);

	i = 3;
	error = gencore_emit_coretable_ranges_body_result(
		vm, ct, &i, user_start, user_end, page_table, &error_start,
		lookup_fn, next_fn, start_fn, end_fn, flag_fn,
		pt_virt_to_phys_fn, virt_to_phys_fn, coretable_log_fn);
	if (error) {
		pt_error_log_fn(error_start, error);
		goto fail;
	}

	*coretablep = ct;
	return 0;

fail:
	gencore_cleanup_generated_body(eh, ct, ph, note, free_fn);
	return error;
}

int hugefileobj_expected_p2align_result(int pgshift)
{
	return pgshift - PTL1_SHIFT;
}

int hugefileobj_validate_p2align_result(int p2align, int pgshift)
{
	return p2align == hugefileobj_expected_p2align_result(pgshift) ?
		0 : -ENOMEM;
}

off_t hugefileobj_page_index_result(off_t off, int pgshift)
{
	return off >> pgshift;
}

int hugefileobj_npages_per_page_result(size_t pgsize)
{
	return pgsize >> PAGE_SHIFT;
}

size_t hugefileobj_pgsize_result(int pgshift)
{
	return 1UL << pgshift;
}

int hugefileobj_initial_status_result(void)
{
	return MEMOBJ_READY;
}

int hugefileobj_initial_refcnt_result(void)
{
	return 2;
}

int hugefileobj_pointer_present_result(uintptr_t ptr)
{
	return ptr != 0;
}

int hugefileobj_pointer_missing_result(uintptr_t ptr)
{
	return ptr == 0;
}

int hugefileobj_page_present_result(uintptr_t page)
{
	return page != 0;
}

size_t hugefileobj_page_array_bytes_result(size_t nr_pages)
{
	return nr_pages * sizeof(void *);
}

int hugefileobj_create_nr_pages_result(off_t off, size_t len, int pgshift)
{
	return (off + len) >> pgshift;
}

int hugefileobj_needs_grow_result(size_t current_nr_pages,
				  int needed_nr_pages)
{
	return current_nr_pages < (size_t)needed_nr_pages;
}

size_t hugefileobj_copy_bytes_result(size_t current_nr_pages)
{
	return current_nr_pages * sizeof(void *);
}

size_t hugefileobj_zero_bytes_result(size_t old_nr_pages, size_t new_nr_pages)
{
	return (new_nr_pages - old_nr_pages) * sizeof(void *);
}

size_t hugefileobj_zero_start_index_result(size_t old_nr_pages)
{
	return old_nr_pages;
}

int hugefileobj_free_body_result(void *obj, void *lock,
				 hugefileobj_void_fn_t lock_fn,
				 hugefileobj_void_fn_t unlock_fn,
				 hugefileobj_void_fn_t list_del_fn,
				 hugefileobj_void_fn_t free_fn)
{
	if (!obj || !lock || !lock_fn || !unlock_fn || !list_del_fn ||
	    !free_fn) {
		return -EINVAL;
	}

	lock_fn(lock);
	list_del_fn(obj);
	unlock_fn(lock);
	free_fn(obj);

	return 0;
}

int hugefileobj_cleanup_body_result(void *lock, void *list_head,
				    hugefileobj_void_fn_t lock_fn,
				    hugefileobj_void_fn_t unlock_fn,
				    hugefileobj_bool_fn_t list_empty_fn,
				    hugefileobj_first_fn_t first_fn,
				    hugefileobj_void_fn_t list_del_fn,
				    hugefileobj_void_fn_t free_fn)
{
	int count = 0;

	if (!lock || !list_head || !lock_fn || !unlock_fn ||
	    !list_empty_fn || !first_fn || !list_del_fn || !free_fn) {
		return -EINVAL;
	}

	while (1) {
		void *obj;

		lock_fn(lock);
		if (list_empty_fn(list_head)) {
			unlock_fn(lock);
			break;
		}

		obj = first_fn(list_head);
		if (!obj) {
			unlock_fn(lock);
			return -EINVAL;
		}
		list_del_fn(obj);
		unlock_fn(lock);

		free_fn(obj);
		++count;
	}

	return count;
}

int hugefileobj_inner_free_body_result(
	void *obj, void *lock, void *path, void *pages, size_t nr_pages,
	size_t pgsize, hugefileobj_void_fn_t lock_fn,
	hugefileobj_void_fn_t unlock_fn, hugefileobj_void_fn_t free_fn,
	hugefileobj_free_page_fn_t free_page_fn,
	hugefileobj_page_at_fn_t page_at_fn,
	hugefileobj_void_fn_t clear_path_fn,
	hugefileobj_log_fn_t log_fn)
{
	int npages;
	size_t i;

	if (!obj || !lock || !lock_fn || !unlock_fn || !free_fn ||
	    !free_page_fn || !page_at_fn || !clear_path_fn || !log_fn) {
		return -EINVAL;
	}

	npages = hugefileobj_npages_per_page_result(pgsize);
	lock_fn(lock);
	if (hugefileobj_pointer_present_result((uintptr_t)path)) {
		free_fn(path);
		clear_path_fn(obj);
	}

	if (hugefileobj_pointer_present_result((uintptr_t)pages)) {
		for (i = 0; i < nr_pages; ++i) {
			void *page = page_at_fn(obj, (long)i);

			if (hugefileobj_page_present_result((uintptr_t)page)) {
				free_page_fn(page, npages);
				log_fn(HUGEFILEOBJ_LOG_FREE_PAGE, obj, 0,
				       (long)i, pgsize, 0);
			}
		}

		free_fn(pages);
	}

	unlock_fn(lock);
	free_fn(obj);

	return 0;
}

int hugefileobj_get_page_body_result(
	void *obj, void *lock, off_t off, int p2align, int pgshift,
	size_t pgsize, uintptr_t virt_addr, uintptr_t *physp,
	hugefileobj_void_fn_t lock_fn, hugefileobj_void_fn_t unlock_fn,
	hugefileobj_page_at_fn_t page_at_fn,
	hugefileobj_set_page_fn_t set_page_fn,
	hugefileobj_alloc_page_fn_t alloc_page_fn,
	hugefileobj_memset_fn_t memset_fn, hugefileobj_phys_fn_t phys_fn,
	hugefileobj_log_fn_t log_fn)
{
	off_t pgind;
	int npages;
	int ret;
	void *page;

	if (!obj || !lock || !physp || !lock_fn || !unlock_fn ||
	    !page_at_fn || !set_page_fn || !alloc_page_fn || !memset_fn ||
	    !phys_fn || !log_fn) {
		return -EINVAL;
	}

	ret = hugefileobj_validate_p2align_result(p2align, pgshift);
	if (ret) {
		log_fn(HUGEFILEOBJ_LOG_GET_P2ALIGN_ERROR, obj, off, p2align,
		       pgsize, hugefileobj_expected_p2align_result(pgshift));
		return ret;
	}

	pgind = hugefileobj_page_index_result(off, pgshift);
	npages = hugefileobj_npages_per_page_result(pgsize);
	lock_fn(lock);
	page = page_at_fn(obj, pgind);
	if (!hugefileobj_page_present_result((uintptr_t)page)) {
		page = alloc_page_fn(npages, p2align,
				     IHK_MC_AP_NOWAIT | IHK_MC_AP_USER,
				     virt_addr);
		if (!page) {
			log_fn(HUGEFILEOBJ_LOG_GET_ALLOC_ERROR, obj, off,
			       pgind, pgsize, virt_addr);
			ret = -EIO;
			goto out;
		}

		set_page_fn(obj, pgind, page);
		memset_fn(page, 0, pgsize);
		log_fn(HUGEFILEOBJ_LOG_GET_ALLOCATED, obj, off, pgind,
		       pgsize, virt_addr);
	}

	*physp = phys_fn(page);

out:
	unlock_fn(lock);
	return ret;
}

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
	hugefileobj_log_fn_t log_fn)
{
	int nr_pages;
	int ret = 0;

	if (!obj || !lock || !pgshiftp || !lock_fn || !unlock_fn ||
	    !alloc_fn || !free_fn || !memcpy_fn || !memset_fn ||
	    !set_nr_pages_fn || !set_pages_fn || !set_size_fn || !log_fn) {
		return -EINVAL;
	}

	nr_pages = hugefileobj_create_nr_pages_result(off, len, pgshift);

	lock_fn(lock);
	if (hugefileobj_needs_grow_result(current_nr_pages, nr_pages)) {
		void *pages;

		pages = alloc_fn(hugefileobj_page_array_bytes_result(nr_pages),
				 alloc_flags);
		if (hugefileobj_pointer_missing_result((uintptr_t)pages)) {
			ret = -ENOMEM;
			goto out;
		}

		if (hugefileobj_pointer_present_result(current_nr_pages)) {
			memcpy_fn(pages, current_pages,
				  hugefileobj_copy_bytes_result(
					  current_nr_pages));
		}

		memset_fn((void *)((void **)pages +
				  hugefileobj_zero_start_index_result(
					  current_nr_pages)),
			  0,
			  hugefileobj_zero_bytes_result(current_nr_pages,
							nr_pages));

		if (hugefileobj_pointer_present_result(current_nr_pages)) {
			free_fn(current_pages);
		}

		set_nr_pages_fn(obj, nr_pages);
		set_pages_fn(obj, pages);
		log_fn(HUGEFILEOBJ_LOG_CREATE_ARRAY, obj, off, nr_pages,
		       pgsize, virt_addr);
	}

	set_size_fn(obj, len);
	*pgshiftp = pgshift;

out:
	unlock_fn(lock);
	return ret;
}

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
	hugefileobj_alloc_error_fn_t alloc_error_fn)
{
	void *obj;
	int ret = 0;

	if (!lock || !path || !ops || !objp || !maxprotp || !lock_fn ||
	    !unlock_fn || !lookup_fn || !alloc_fn || !free_fn ||
	    !to_memobj_fn || !set_handle_fn || !set_pgsize_fn ||
	    !set_pgshift_fn || !set_pages_fn || !set_nr_pages_fn ||
	    !init_lock_fn || !set_flags_fn || !set_status_fn || !set_ops_fn ||
	    !set_refcnt_fn || !set_path_fn || !copy_path_fn || !list_add_fn ||
	    !log_fn || !alloc_error_fn) {
		return -EINVAL;
	}

	lock_fn(lock);
	obj = lookup_fn(handle);
	if (obj) {
		log_fn(HUGEFILEOBJ_LOG_PRE_CREATE_FOUND, obj);
		*maxprotp = maxprot;
		*objp = to_memobj_fn(obj);
		goto out_unlock;
	}

	obj = alloc_fn(obj_size, IHK_MC_AP_NOWAIT);
	if (!obj) {
		alloc_error_fn(HUGEFILEOBJ_PRE_CREATE_ALLOC_OBJ);
		ret = -ENOMEM;
		goto out_unlock;
	}

	set_handle_fn(obj, handle);
	set_pgsize_fn(obj, hugefileobj_pgsize_result(pgshift));
	set_pgshift_fn(obj, pgshift);
	set_pages_fn(obj, NULL);
	set_nr_pages_fn(obj, 0);
	init_lock_fn(obj);
	set_flags_fn(obj, flags);
	set_status_fn(obj, hugefileobj_initial_status_result());
	set_ops_fn(obj, ops);
	set_refcnt_fn(obj, hugefileobj_initial_refcnt_result());

	if (path[0]) {
		void *path_buf = alloc_fn(path_size, IHK_MC_AP_NOWAIT);

		if (!path_buf) {
			alloc_error_fn(HUGEFILEOBJ_PRE_CREATE_ALLOC_PATH);
			free_fn(obj);
			ret = -ENOMEM;
			goto out_unlock;
		}
		set_path_fn(obj, path_buf);
		copy_path_fn(path_buf, path, path_size);
	}

	list_add_fn(obj);
	log_fn(HUGEFILEOBJ_LOG_PRE_CREATE_CREATED, obj);
	*maxprotp = maxprot;
	*objp = to_memobj_fn(obj);

out_unlock:
	unlock_fn(lock);
	return ret;
}

void *hugefileobj_lookup_body_result(
	uintptr_t handle, void *list_head,
	hugefileobj_first_fn_t first_fn,
	hugefileobj_next_fn_t next_fn,
	hugefileobj_handle_fn_t handle_fn,
	hugefileobj_ref_fn_t ref_fn,
	hugefileobj_dec_fn_t dec_fn)
{
	void *obj;

	if (!list_head || !first_fn || !next_fn || !handle_fn || !ref_fn ||
	    !dec_fn) {
		return NULL;
	}

	obj = first_fn(list_head);
	while (obj) {
		if (handle_fn(obj) == handle) {
			if (fileobj_lookup_ref_keep_result(ref_fn(obj))) {
				return obj;
			}
			dec_fn(obj);
		}
		obj = next_fn(list_head, obj);
	}

	return NULL;
}

#endif /* MCKERNEL_RUST_OBJECT_HELPERS */
