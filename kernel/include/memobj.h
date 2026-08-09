/* memobj.h COPYRIGHT FUJITSU LIMITED 2015-2016 */
/**
 * \file memobj.h
 *  License details are found in the file LICENSE.
 * \brief
 *  defines and declares for memory object
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#ifndef HEADER_MEMOBJ_H
#define HEADER_MEMOBJ_H

#include <ihk/types.h>
#include <ihk/atomic.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <errno.h>
#include <list.h>
#include <pager.h>
#include <page.h>
#include <object_helpers.h>

enum {
	/* for memobj.flags */
	MF_HAS_PAGER	= 0x0001,
	MF_SHMDT_OK	= 0x0002,
	MF_IS_REMOVABLE	= 0x0004,
	MF_PREFETCH = 0x0008,
	MF_ZEROFILL = 0x0010,
	MF_REG_FILE = 0x1000,
	MF_DEV_FILE = 0x2000,
	MF_PREMAP   = 0x8000,
	MF_XPMEM   = 0x10000, /* To identify XPMEM attachment pages for rusage accounting */
	MF_ZEROOBJ = 0x20000, /* To identify pages of anonymous, on-demand paging ranges for rusage accounting */
	MF_SHM =     0x40000,
	MF_HUGETLBFS = 0x100000,
	MF_PRIVATE   = 0x200000, /* To prevent flush in clear_range_* */
	MF_REMAP_FILE_PAGES = 0x400000, /* remap_file_pages possible */
};

#define MEMOBJ_READY              0
#define MEMOBJ_TO_BE_PREFETCHED   1

struct memobj {
	struct memobj_ops *ops;
	uint32_t flags;
	uint32_t status;
	size_t size;
	ihk_atomic_t refcnt;

	/* For pre-mapped memobjects */
	void **pages;
	int nr_pages;
	char *path;
};

typedef void memobj_free_func_t(struct memobj *obj);
typedef int memobj_get_page_func_t(struct memobj *obj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag, uintptr_t virt_addr);
typedef uintptr_t memobj_copy_page_func_t(struct memobj *obj, uintptr_t orgphys, int p2align);
typedef int memobj_flush_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);
typedef int memobj_invalidate_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);
typedef int memobj_lookup_page_func_t(struct memobj *obj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag);
typedef int memobj_update_page_func_t(struct memobj *obj, page_table_t pt,
		struct page *orig_page, void *vaddr);

struct memobj_ops {
	memobj_free_func_t *free;
	memobj_get_page_func_t *get_page;
	memobj_copy_page_func_t *copy_page;
	memobj_flush_page_func_t *flush_page;
	memobj_invalidate_page_func_t *invalidate_page;
	memobj_lookup_page_func_t *lookup_page;
	memobj_update_page_func_t *update_page;
};

int memobj_ref(struct memobj *obj);
int memobj_unref(struct memobj *obj);
int memobj_get_page(struct memobj *obj, off_t off, int p2align,
		    uintptr_t *physp, unsigned long *pflag,
		    uintptr_t virt_addr);
uintptr_t memobj_copy_page(struct memobj *obj, uintptr_t orgphys,
			   int p2align);
int memobj_flush_page(struct memobj *obj, uintptr_t phys, size_t pgsize);
int memobj_invalidate_page(struct memobj *obj, uintptr_t phys, size_t pgsize);
int memobj_lookup_page(struct memobj *obj, off_t off, int p2align,
		       uintptr_t *physp, unsigned long *pflag);
int memobj_update_page(struct memobj *obj, page_table_t pt,
		       struct page *orig_page, void *vaddr);
int memobj_has_pager(struct memobj *obj);
int memobj_is_removable(struct memobj *obj);

int fileobj_create(int fd, struct memobj **objp, int *maxprotp, int flags,
		   uintptr_t virt_addr);
struct shmid_ds;
int shmobj_create(struct shmid_ds *ds, struct memobj **objp);
int zeroobj_create(struct memobj **objp);
int devobj_create(int fd, size_t len, off_t off, struct memobj **objp, int *maxprotp,
	int prot, int populate_flags);
int hugefileobj_pre_create(struct pager_create_result *result,
			   struct memobj **objp, int *maxprotp);
int hugefileobj_create(struct memobj *obj, size_t len, off_t off,
		       int *pgshiftp, uintptr_t virt_addr);
void hugefileobj_cleanup(void);

int is_flushable(struct page *page, struct memobj *memobj);
int is_freeable(struct memobj *memobj);
int is_callable_remap_file_pages(struct memobj *memobj);

#endif /* HEADER_MEMOBJ_H */
