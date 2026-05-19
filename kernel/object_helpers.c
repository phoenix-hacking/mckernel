/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <memobj.h>
#include <mman.h>
#include <object_helpers.h>
#include <page.h>
#include <pager.h>
#include <process.h>
#include <registers.h>
#include <shm.h>
#include <sysfs.h>

#ifndef MCKERNEL_RUST_OBJECT_HELPERS

#define FILEOBJ_PAGE_HASH_MASK 511

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

int pager_linux_io_retry_result(ssize_t ret)
{
	return ret == -EINTR;
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

#endif /* MCKERNEL_RUST_OBJECT_HELPERS */
