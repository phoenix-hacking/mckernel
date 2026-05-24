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
#include <string.h>
#include <syscall.h>
#include <sysfs.h>

#ifndef MCKERNEL_RUST_OBJECT_HELPERS

#define FILEOBJ_PAGE_HASH_MASK 511

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

#endif /* MCKERNEL_RUST_OBJECT_HELPERS */
