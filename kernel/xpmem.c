/* xpmem.c COPYRIGHT FUJITSU LIMITED 2017 */
/**
 * \file xpmem.c
 *  License details are found in the file LICENSE.
 * \brief
 *  Cross Partition Memory (XPMEM) support.
 * \author Yoichi Umezawa  <yoichi.umezawa.qh@hitachi.com> \par
 * 	Copyright (C) 2016 Yoichi Umezawa
 *
 * Original Copyright follows:
 *
 * This file is subject to the terms and conditions of the GNU General Public
 * License.  See the file "COPYING" in the main directory of this archive
 * for more details.
 *
 * Copyright (c) 2004-2007 Silicon Graphics, Inc.  All Rights Reserved.
 * Copyright 2010, 2014 Cray Inc. All Rights Reserved
 * Copyright 2015-2016 Los Alamos National Security, LLC. All rights reserved.
 */
/*
 * HISTORY
 */

#include <errno.h>
#include <kmalloc.h>
#include <limits.h>
#include <memobj.h>
#include <process.h>
#include <mman.h>
#include <page.h>
#include <string.h>
#include <types.h>
#include <vsprintf.h>
#include <ihk/lock.h>
#include <ihk/mm.h>
#include <xpmem_private.h>

struct xpmem_partition *xpmem_my_part = NULL;  /* pointer to this partition */

#if defined(MCKERNEL_XPMEM_HELPERS_TEST_EXPORT)
#define XPMEM_HELPER_SCOPE
#else
#define XPMEM_HELPER_SCOPE static
#endif

#define XPMEM_LOOKUP_SKIP 0
#define XPMEM_LOOKUP_TAKE 1
#define XPMEM_LOOKUP_STOP 2

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
extern pid_t xpmem_id_to_tgid_result(long id);
extern int xpmem_tg_hashtable_index_result(pid_t tgid);
extern int xpmem_ap_hashtable_index_result(xpmem_apid_t apid);
extern int xpmem_make_id_result(pid_t tgid, int uniq, long *idp);
extern int xpmem_positive_id_result(long id);
extern int xpmem_owner_policy_result(pid_t current_pid, pid_t owner_tgid);
extern int xpmem_make_initial_policy_result(int permit_type,
		unsigned long permit_value, size_t size);
extern int xpmem_make_alignment_result(unsigned long vaddr, size_t size);
extern int xpmem_get_policy_result(xpmem_segid_t segid, int flags,
		int permit_type, int has_permit_value);
extern int xpmem_perms_result(uid_t perm_uid, gid_t perm_gid,
		unsigned long perm_mode, short flag, uid_t current_ruid,
		gid_t current_rgid);
extern int xpmem_check_permit_mode_result(int flags, uid_t seg_uid,
		gid_t seg_gid, unsigned long seg_mode, uid_t current_ruid,
		gid_t current_rgid);
extern int xpmem_validate_access_result(pid_t current_pid, pid_t ap_tgid,
		int ap_mode, unsigned long seg_vaddr, size_t seg_size,
		off_t offset, size_t size, int mode, unsigned long *vaddr);
extern int xpmem_attach_initial_policy_result(xpmem_apid_t apid,
		off_t offset, unsigned long vaddr, size_t size,
		int fjmpi_workaround, size_t *adjusted_size);
extern int xpmem_destroying_state_result(int flags, int return_destroying);
extern int xpmem_is_destroying_result(int flags);
extern int xpmem_destroying_error_result(int flags, int error);
extern int xpmem_two_destroying_error_result(int first_flags,
		int second_flags, int error);
extern int xpmem_three_destroying_error_result(int first_flags,
		int second_flags, int third_flags, int error);
extern int xpmem_attach_destroying_result(int seg_flags, int seg_tg_flags);
extern int xpmem_close_decision_result(int n_opened, int has_data,
		int *flush_objects, int *exit_partition);
extern int xpmem_ref_drop_should_free_result(int refcnt_after_dec);
extern int xpmem_begin_destroy_result(int flags, int *new_flags);
extern int xpmem_finish_destroy_result(int flags);
extern int xpmem_object_lookup_decision_result(long candidate_id,
		long requested_id, int flags, int return_destroying,
		int stop_on_destroying);
extern int xpmem_detach_lookup_result(int has_range,
		unsigned long range_start, unsigned long at_vaddr,
		int has_private_data);
extern int xpmem_attach_overlap_result(pid_t current_pid, pid_t seg_tgid,
		unsigned long requested_vaddr, size_t size,
		unsigned long seg_vaddr);
extern int xpmem_remove_range_step_result(unsigned long range_start,
		unsigned long range_end, unsigned long start, unsigned long end,
		unsigned long range_flags, int has_private_data,
		int *split_start, int *split_end, int *ro_freed,
		int *remove_private);
extern int xpmem_remove_memory_range_action_result(unsigned long vmr_start,
		unsigned long vmr_end, unsigned long att_at_vaddr,
		size_t att_at_size, unsigned long *remaining_vaddr,
		unsigned long *middle_lookup_vaddr, int *full_detach,
		int *needs_middle_lookup);
extern int xpmem_range_private_invalid_result(int has_range,
		unsigned long range_start, unsigned long vaddr,
		int private_matches);
extern int xpmem_clear_pte_range_result(int att_flags,
		unsigned long att_vaddr, unsigned long att_at_vaddr,
		size_t att_at_size, unsigned long start, unsigned long end,
		unsigned long *unpin_at, unsigned long *invalidate_len,
		int *clear_valid);
extern int xpmem_fault_vaddr_result(unsigned long vaddr,
		unsigned long att_at_vaddr, size_t att_at_size,
		unsigned long att_vaddr, unsigned long *seg_vaddr);
extern int xpmem_straight_phys_result(unsigned long seg_vaddr,
		unsigned long straight_va, size_t straight_len,
		unsigned long straight_pa, unsigned long *seg_phys,
		size_t *seg_pgsize);
extern int xpmem_remote_pte_missing_result(int has_pte, int pte_is_empty,
		int page_in_remote);
extern unsigned long xpmem_seg_phys_plus_off_result(unsigned long seg_phys,
		size_t seg_pgsize, unsigned long seg_vaddr);
extern int xpmem_att_page_fits_result(unsigned long att_pgaddr,
		size_t att_pgsize, unsigned long vmr_start,
		unsigned long vmr_end, size_t seg_pgsize);
extern int xpmem_pte_mismatch_result(unsigned long att_phys,
		unsigned long seg_phys_aligned);
extern int xpmem_unpin_step_result(unsigned long vaddr, size_t vsize,
		int has_present_pte, unsigned long *next_vaddr, int *unpinned);
#else
XPMEM_HELPER_SCOPE pid_t
xpmem_id_to_tgid_result(long id)
{
	xpmem_id_t xpmem_id = { .segid = id };

	return xpmem_id.xpmem_id.tgid;
}

XPMEM_HELPER_SCOPE int
xpmem_tg_hashtable_index_result(pid_t tgid)
{
	return (unsigned int)tgid % XPMEM_TG_HASHTABLE_SIZE;
}

XPMEM_HELPER_SCOPE int
xpmem_ap_hashtable_index_result(xpmem_apid_t apid)
{
	xpmem_id_t xpmem_id = { .apid = apid };

	return xpmem_id.xpmem_id.uniq % XPMEM_AP_HASHTABLE_SIZE;
}

XPMEM_HELPER_SCOPE int
xpmem_make_id_result(pid_t tgid, int uniq, long *idp)
{
	xpmem_id_t xpmem_id = { .segid = 0 };

	if (uniq > XPMEM_MAX_UNIQ_ID) {
		return -EBUSY;
	}

	xpmem_id.xpmem_id.tgid = tgid;
	xpmem_id.xpmem_id.uniq = (unsigned int)uniq;
	*idp = xpmem_id.segid;

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_positive_id_result(long id)
{
	if (id <= 0) {
		return -EINVAL;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_owner_policy_result(pid_t current_pid, pid_t owner_tgid)
{
	if (current_pid != owner_tgid) {
		return -EACCES;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_make_initial_policy_result(int permit_type, unsigned long permit_value,
		size_t size)
{
	if (permit_type != XPMEM_PERMIT_MODE ||
			(permit_value & ~00777) ||
			size == 0) {
		return -EINVAL;
	}
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_make_alignment_result(unsigned long vaddr, size_t size)
{
	if (offset_in_page(vaddr) != 0 ||
			(offset_in_page(size) != 0 &&
			 size != 0xffffffffffffffff)) {
		return -EINVAL;
	}
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_get_policy_result(xpmem_segid_t segid, int flags, int permit_type,
		int has_permit_value)
{
	if (segid <= 0) {
		return -EINVAL;
	}

	if ((flags & ~(XPMEM_RDONLY | XPMEM_RDWR)) ||
		(flags & (XPMEM_RDONLY | XPMEM_RDWR)) ==
		(XPMEM_RDONLY | XPMEM_RDWR)) {
		return -EINVAL;
	}

	if (permit_type != XPMEM_PERMIT_MODE || has_permit_value) {
		return -EINVAL;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_perms_result(uid_t perm_uid, gid_t perm_gid, unsigned long perm_mode,
		short flag, uid_t current_ruid, gid_t current_rgid)
{
	int requested_mode;
	unsigned long granted_mode;

	requested_mode = (flag >> 6) | (flag >> 3) | flag;
	granted_mode = perm_mode;
	if (perm_uid == current_ruid) {
		granted_mode >>= 6;
	}
	else if (perm_gid == current_rgid) {
		granted_mode >>= 3;
	}

	if (requested_mode & ~granted_mode & 0007) {
		return -1;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_check_permit_mode_result(int flags, uid_t seg_uid, gid_t seg_gid,
		unsigned long seg_mode, uid_t current_ruid, gid_t current_rgid)
{
	int ret;

	ret = xpmem_perms_result(seg_uid, seg_gid, seg_mode,
			XPMEM_PERM_IRUSR, current_ruid, current_rgid);
	if (ret == 0 && (flags & XPMEM_RDWR)) {
		ret = xpmem_perms_result(seg_uid, seg_gid, seg_mode,
				XPMEM_PERM_IWUSR, current_ruid, current_rgid);
	}

	return ret;
}

XPMEM_HELPER_SCOPE int
xpmem_validate_access_result(pid_t current_pid, pid_t ap_tgid, int ap_mode,
		unsigned long seg_vaddr, size_t seg_size, off_t offset,
		size_t size, int mode, unsigned long *vaddr)
{
	if (current_pid != ap_tgid ||
		(mode == XPMEM_RDWR && ap_mode == XPMEM_RDONLY)) {
		return -EACCES;
	}

	if (offset < 0 || size == 0 ||
			(unsigned long)offset + size > seg_size) {
		return -EINVAL;
	}

	*vaddr = seg_vaddr + offset;
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_attach_initial_policy_result(xpmem_apid_t apid, off_t offset,
		unsigned long vaddr, size_t size, int fjmpi_workaround,
		size_t *adjusted_size)
{
	if (apid <= 0) {
		return -EINVAL;
	}

	if (offset_in_page(vaddr) != 0 || offset_in_page(offset) != 0) {
		return -EINVAL;
	}

	if (fjmpi_workaround) {
		size = (size & ~(PAGE_SIZE - 1));
	}
	else if (offset_in_page(size) != 0) {
		size += PAGE_SIZE - offset_in_page(size);
	}

	*adjusted_size = size;
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_destroying_state_result(int flags, int return_destroying)
{
	if ((flags & XPMEM_FLAG_DESTROYING) && !return_destroying) {
		return 0;
	}

	return 1;
}

XPMEM_HELPER_SCOPE int
xpmem_is_destroying_result(int flags)
{
	if (flags & XPMEM_FLAG_DESTROYING) {
		return 1;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_destroying_error_result(int flags, int error)
{
	if (flags & XPMEM_FLAG_DESTROYING) {
		return error;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_two_destroying_error_result(int first_flags, int second_flags,
		int error)
{
	if ((first_flags & XPMEM_FLAG_DESTROYING) ||
			(second_flags & XPMEM_FLAG_DESTROYING)) {
		return error;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_three_destroying_error_result(int first_flags, int second_flags,
		int third_flags, int error)
{
	if ((first_flags & XPMEM_FLAG_DESTROYING) ||
			(second_flags & XPMEM_FLAG_DESTROYING) ||
			(third_flags & XPMEM_FLAG_DESTROYING)) {
		return error;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_attach_destroying_result(int seg_flags, int seg_tg_flags)
{
	if ((seg_flags & XPMEM_FLAG_DESTROYING) ||
			(seg_tg_flags & XPMEM_FLAG_DESTROYING)) {
		return -ENOENT;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_close_decision_result(int n_opened, int has_data, int *flush_objects,
		int *exit_partition)
{
	*flush_objects = has_data;
	*exit_partition = !n_opened;
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_ref_drop_should_free_result(int refcnt_after_dec)
{
	return refcnt_after_dec == 0;
}

XPMEM_HELPER_SCOPE int
xpmem_begin_destroy_result(int flags, int *new_flags)
{
	if (flags & XPMEM_FLAG_DESTROYING) {
		*new_flags = flags;
		return 0;
	}

	*new_flags = flags | XPMEM_FLAG_DESTROYING;
	return 1;
}

XPMEM_HELPER_SCOPE int
xpmem_finish_destroy_result(int flags)
{
	return flags | XPMEM_FLAG_DESTROYED;
}

XPMEM_HELPER_SCOPE int
xpmem_object_lookup_decision_result(long candidate_id, long requested_id,
		int flags, int return_destroying, int stop_on_destroying)
{
	if (candidate_id != requested_id) {
		return XPMEM_LOOKUP_SKIP;
	}

	if ((flags & XPMEM_FLAG_DESTROYING) && !return_destroying) {
		return stop_on_destroying ? XPMEM_LOOKUP_STOP :
			XPMEM_LOOKUP_SKIP;
	}

	return XPMEM_LOOKUP_TAKE;
}

XPMEM_HELPER_SCOPE int
xpmem_detach_lookup_result(int has_range, unsigned long range_start,
		unsigned long at_vaddr, int has_private_data)
{
	if (!has_range || range_start > at_vaddr) {
		return 0;
	}

	if (!has_private_data) {
		return -EINVAL;
	}

	return 1;
}

XPMEM_HELPER_SCOPE int
xpmem_attach_overlap_result(pid_t current_pid, pid_t seg_tgid,
		unsigned long requested_vaddr, size_t size,
		unsigned long seg_vaddr)
{
	if (current_pid == seg_tgid && requested_vaddr &&
			(requested_vaddr + size > seg_vaddr) &&
			(requested_vaddr < seg_vaddr + size)) {
		return -EINVAL;
	}
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_range_step_result(unsigned long range_start,
		unsigned long range_end, unsigned long start, unsigned long end,
		unsigned long range_flags, int has_private_data,
		int *split_start, int *split_end, int *ro_freed,
		int *remove_private)
{
	*split_start = range_start < start;
	*split_end = end < range_end;
	*ro_freed = !(range_flags & VR_PROT_WRITE);
	*remove_private = has_private_data;
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_memory_range_action_result(unsigned long vmr_start,
		unsigned long vmr_end, unsigned long att_at_vaddr,
		size_t att_at_size, unsigned long *remaining_vaddr,
		unsigned long *middle_lookup_vaddr, int *full_detach,
		int *needs_middle_lookup)
{
	unsigned long att_end = att_at_vaddr + att_at_size;

	if (vmr_start == att_at_vaddr &&
			((vmr_end - vmr_start) == att_at_size)) {
		*full_detach = 1;
		*needs_middle_lookup = 0;
		*remaining_vaddr = 0;
		*middle_lookup_vaddr = 0;
		return 0;
	}

	*full_detach = 0;
	if (vmr_start == att_at_vaddr) {
		*remaining_vaddr = vmr_end;
		*middle_lookup_vaddr = 0;
		*needs_middle_lookup = 0;
	}
	else if (vmr_end == att_end) {
		*remaining_vaddr = att_at_vaddr;
		*middle_lookup_vaddr = 0;
		*needs_middle_lookup = 0;
	}
	else {
		*remaining_vaddr = att_at_vaddr;
		*middle_lookup_vaddr = vmr_end;
		*needs_middle_lookup = 1;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_range_private_invalid_result(int has_range, unsigned long range_start,
		unsigned long vaddr, int private_matches)
{
	return !has_range || range_start > vaddr || !private_matches;
}

XPMEM_HELPER_SCOPE int
xpmem_clear_pte_range_result(int att_flags, unsigned long att_vaddr,
		unsigned long att_at_vaddr, size_t att_at_size,
		unsigned long start, unsigned long end, unsigned long *unpin_at,
		unsigned long *invalidate_len, int *clear_valid)
{
	unsigned long att_vaddr_end;
	unsigned long invalidate_start;
	unsigned long invalidate_end;
	unsigned long offset_start;
	unsigned long offset_end;

	*unpin_at = 0;
	*invalidate_len = 0;
	*clear_valid = 0;
	if (!(att_flags & XPMEM_FLAG_VALIDPTEs)) {
		return 0;
	}

	att_vaddr_end = att_vaddr + att_at_size;
	invalidate_start = max(start, att_vaddr);
	invalidate_end = min(end, att_vaddr_end);
	if (invalidate_start >= att_vaddr_end || invalidate_end <= att_vaddr) {
		return 0;
	}

	offset_start = invalidate_start - att_vaddr;
	offset_end = invalidate_end - att_vaddr;
	*unpin_at = att_at_vaddr + offset_start;
	*invalidate_len = offset_end - offset_start;
	*clear_valid = offset_start == 0 && att_at_size == *invalidate_len;

	return 1;
}

XPMEM_HELPER_SCOPE int
xpmem_fault_vaddr_result(unsigned long vaddr, unsigned long att_at_vaddr,
		size_t att_at_size, unsigned long att_vaddr,
		unsigned long *seg_vaddr)
{
	if (vaddr < att_at_vaddr || vaddr + 1 > att_at_vaddr + att_at_size) {
		return -EFAULT;
	}

	*seg_vaddr = att_vaddr + (vaddr - att_at_vaddr);
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_straight_phys_result(unsigned long seg_vaddr, unsigned long straight_va,
		size_t straight_len, unsigned long straight_pa,
		unsigned long *seg_phys, size_t *seg_pgsize)
{
	if (straight_va && seg_vaddr >= straight_va &&
			seg_vaddr < straight_va + straight_len) {
		*seg_phys = ((seg_vaddr & PAGE_MASK) - straight_va) +
			straight_pa;
		*seg_pgsize = (1UL << 29);
		return 1;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remote_pte_missing_result(int has_pte, int pte_is_empty,
		int page_in_remote)
{
	if (!has_pte || pte_is_empty) {
		return page_in_remote ? -EFAULT : 0;
	}

	return 1;
}

XPMEM_HELPER_SCOPE unsigned long
xpmem_seg_phys_plus_off_result(unsigned long seg_phys, size_t seg_pgsize,
		unsigned long seg_vaddr)
{
	return (seg_phys & ~(seg_pgsize - 1)) |
		(seg_vaddr & (seg_pgsize - 1));
}

XPMEM_HELPER_SCOPE int
xpmem_att_page_fits_result(unsigned long att_pgaddr, size_t att_pgsize,
		unsigned long vmr_start, unsigned long vmr_end,
		size_t seg_pgsize)
{
	return !((unsigned long)att_pgaddr < vmr_start ||
			vmr_end < (uintptr_t)att_pgaddr + att_pgsize ||
			att_pgsize > seg_pgsize);
}

XPMEM_HELPER_SCOPE int
xpmem_pte_mismatch_result(unsigned long att_phys,
		unsigned long seg_phys_aligned)
{
	return att_phys != seg_phys_aligned ? -EFAULT : 0;
}

XPMEM_HELPER_SCOPE int
xpmem_unpin_step_result(unsigned long vaddr, size_t vsize,
		int has_present_pte, unsigned long *next_vaddr, int *unpinned)
{
	if (has_present_pte) {
		*next_vaddr = vaddr + vsize;
		*unpinned = 1;
	}
	else {
		*next_vaddr = ((vaddr + vsize) & (~(vsize - 1)));
		*unpinned = 0;
	}

	return 0;
}
#endif

#undef XPMEM_HELPER_SCOPE

static int do_xpmem_open(int syscall_num, const char *pathname,
		int flags, ihk_mc_user_context_t *ctx)
{
	int ret;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	int fd;
	struct mckfd *mckfd;
	long irqstate;

	XPMEM_DEBUG("call: syscall_num=%d, pathname=%s, flags=%d",
		syscall_num, pathname, flags);

	if (!xpmem_my_part) {
		ret = xpmem_init();
		if (ret) {
			return ret;
		}
	}

	fd = syscall_generic_forwarding(syscall_num, ctx);
	if(fd < 0){
		XPMEM_DEBUG("syscall_num=%d error: fd=%d", syscall_num, fd);
		return fd;
	}

	ret = __xpmem_open();
	if (ret) {
		XPMEM_DEBUG("return: ret=%d", ret);
		return ret;
	}

	mckfd = kmalloc(sizeof(struct mckfd), IHK_MC_AP_NOWAIT);
	if(!mckfd) {
		return -ENOMEM;
	}
	XPMEM_DEBUG("kmalloc(): mckfd=0x%p", mckfd);
	memset(mckfd, 0, sizeof(struct mckfd));
	mckfd->fd = fd;
	mckfd->sig_no = -1;
	mckfd->ioctl_cb = xpmem_ioctl;
	mckfd->close_cb = xpmem_close;
	mckfd->dup_cb = xpmem_dup;
	mckfd->data = (long)proc;
	irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);

	if (proc->mckfd == NULL) {
		proc->mckfd = mckfd;
		mckfd->next = NULL;
	}
	else {
		mckfd->next = proc->mckfd;
		proc->mckfd = mckfd;
	}

	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);

	ihk_atomic_inc_return(&xpmem_my_part->n_opened);
	XPMEM_DEBUG("n_opened=%d", xpmem_my_part->n_opened);

	XPMEM_DEBUG("return: ret=%d", mckfd->fd);

	return mckfd->fd;
}

int xpmem_open(const char *pathname,
		int flags, ihk_mc_user_context_t *ctx)
{
	return do_xpmem_open(__NR_open, pathname, flags, ctx);
}

int xpmem_openat(const char *pathname,
		int flags, ihk_mc_user_context_t *ctx)
{
	return do_xpmem_open(__NR_openat, pathname, flags, ctx);
}

static int xpmem_ioctl(
	struct mckfd *mckfd,
	ihk_mc_user_context_t *ctx)
{
	int ret;
	unsigned int cmd = ihk_mc_syscall_arg1(ctx);
	unsigned long arg = ihk_mc_syscall_arg2(ctx);

	XPMEM_DEBUG("call: cmd=0x%x, arg=0x%lx", cmd, arg);

	switch (cmd) {
	case XPMEM_CMD_VERSION: {
		ret = XPMEM_CURRENT_VERSION;

		XPMEM_DEBUG("return: cmd=0x%x, ret=0x%lx", cmd, ret);

		return ret;
	}
	case XPMEM_CMD_MAKE: {
		struct xpmem_cmd_make make_info;
		xpmem_segid_t segid = 0;

		if (copy_from_user(&make_info, (void __user *)arg, 
			sizeof(struct xpmem_cmd_make)))
			return -EFAULT;

		ret = xpmem_make(make_info.vaddr, make_info.size, 
			make_info.permit_type, 
			(void *)make_info.permit_value, &segid);
		if (ret != 0) {
			XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);
			return ret;
		}

		if (copy_to_user(&((struct xpmem_cmd_make __user *)arg)->segid, 
			(void *)&segid, sizeof(xpmem_segid_t))) {
			(void)xpmem_remove(segid);
			return -EFAULT;
		}

		XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);

		return ret;
	}
	case XPMEM_CMD_REMOVE: {
		struct xpmem_cmd_remove remove_info;

		if (copy_from_user(&remove_info, (void __user *)arg, 
			sizeof(struct xpmem_cmd_remove)))
			return -EFAULT;

		ret = xpmem_remove(remove_info.segid);

		XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);

		return ret;
	}
	case XPMEM_CMD_GET: {
		struct xpmem_cmd_get get_info;
		xpmem_apid_t apid = 0;

		if (copy_from_user(&get_info, (void __user *)arg, 
			sizeof(struct xpmem_cmd_get)))
			return -EFAULT;

		ret = xpmem_get(get_info.segid, get_info.flags,
			get_info.permit_type,
			(void *)get_info.permit_value, &apid);
		if (ret != 0) {
			XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);
			return ret;
		}

		if (copy_to_user(&((struct xpmem_cmd_get __user *)arg)->apid, 
			(void *)&apid, sizeof(xpmem_apid_t))) {
			(void)xpmem_release(apid);
			return -EFAULT;
		}

		XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);

		return ret;
	}
	case XPMEM_CMD_RELEASE: {
		struct xpmem_cmd_release release_info;

		if (copy_from_user(&release_info, (void __user *)arg,
			sizeof(struct xpmem_cmd_release)))
			return -EFAULT;

		ret = xpmem_release(release_info.apid);

		XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);

		return ret;
	}
	case XPMEM_CMD_ATTACH: {
		struct xpmem_cmd_attach attach_info;
		unsigned long at_vaddr = 0;

		if (copy_from_user(&attach_info, (void __user *)arg, 
			sizeof(struct xpmem_cmd_attach)))
			return -EFAULT;

		ret = xpmem_attach(mckfd, attach_info.apid, attach_info.offset, 
			attach_info.size, attach_info.vaddr, 
			attach_info.fd, attach_info.flags, 
			&at_vaddr);
		if (ret != 0) {
			XPMEM_DEBUG("return: at_vaddr: %lx, cmd=0x%x, ret=%d",
				    at_vaddr, cmd, ret);
			return ret;
		}

		if (copy_to_user(
			&((struct xpmem_cmd_attach __user *)arg)->vaddr, 
			(void *)&at_vaddr, sizeof(unsigned long))) {
			(void)xpmem_detach(at_vaddr);
			return -EFAULT;
		}

		XPMEM_DEBUG("XPMEM_CMD_ATTACH: return: at_vaddr: %lx, cmd=0x%x, ret=%d",
			    at_vaddr, cmd, ret);

		return ret;
	}
	case XPMEM_CMD_DETACH: {
		struct xpmem_cmd_detach detach_info;

		if (copy_from_user(&detach_info, (void __user *)arg, 
			sizeof(struct xpmem_cmd_detach)))
			return -EFAULT;

		ret = xpmem_detach(detach_info.vaddr);

		XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);

		return ret;
	}
	default:
		break;
	}

	XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, -EINVAL);

	return -EINVAL;
}

static int xpmem_close(
	struct mckfd *mckfd,
	ihk_mc_user_context_t *ctx)
{
	int n_opened;
	int flush_objects;
	int exit_partition;

	XPMEM_DEBUG("call: fd=%d, pid=%d, rgid=%d", 
		mckfd->fd, cpu_local_var(current)->proc->pid,
		cpu_local_var(current)->proc->rgid);

	n_opened = ihk_atomic_dec_return(&xpmem_my_part->n_opened);
	XPMEM_DEBUG("n_opened=%d", n_opened);

	xpmem_close_decision_result(n_opened, mckfd->data != 0,
			&flush_objects, &exit_partition);

	if (flush_objects) {
		/* release my xpmem-objects */
		xpmem_flush(mckfd);
	}

	if (exit_partition) {
		xpmem_exit();
	}

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}

static int xpmem_dup(
	struct mckfd *mckfd,
	ihk_mc_user_context_t *ctx)
{
	mckfd->data = 0;
	ihk_atomic_inc_return(&xpmem_my_part->n_opened);

	return 0;
}

static int xpmem_init(void)
{
	int i;

	XPMEM_DEBUG("call: ");

	xpmem_my_part = kmalloc(sizeof(struct xpmem_partition) + 
		sizeof(struct xpmem_hashlist) * XPMEM_TG_HASHTABLE_SIZE, 
		IHK_MC_AP_NOWAIT);
	if (xpmem_my_part == NULL) {
		return -ENOMEM;
	}
	XPMEM_DEBUG("kmalloc(): xpmem_my_part=0x%p", xpmem_my_part);
	memset(xpmem_my_part, 0, sizeof(struct xpmem_partition) + 
		sizeof(struct xpmem_hashlist) * XPMEM_TG_HASHTABLE_SIZE);

	for (i = 0; i < XPMEM_TG_HASHTABLE_SIZE; i++) {
		mcs_rwlock_init(&xpmem_my_part->tg_hashtable[i].lock);
		INIT_LIST_HEAD(&xpmem_my_part->tg_hashtable[i].list);
	}

	ihk_atomic_set(&xpmem_my_part->n_opened, 0);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static void xpmem_exit(void)
{
	XPMEM_DEBUG("call: ");

	if (xpmem_my_part) {
		XPMEM_DEBUG("kfree(): xpmem_my_part=0x%p", xpmem_my_part);
		kfree(xpmem_my_part);
		xpmem_my_part = NULL;
	}

	XPMEM_DEBUG("return: ");
}


static int __xpmem_open(void)
{
	struct xpmem_thread_group *tg;
	int index;
	struct mcs_rwlock_node_irqsave lock;

	XPMEM_DEBUG("call: ");

	tg = xpmem_tg_ref_by_tgid(cpu_local_var(current)->proc->pid);
	if (!IS_ERR(tg)) {
		xpmem_tg_deref(tg);
		XPMEM_DEBUG("return: ret=%d, tg=0x%p", 0, tg);
		return 0;
	}

	tg = kmalloc(sizeof(struct xpmem_thread_group) + 
		sizeof(struct xpmem_hashlist) * XPMEM_AP_HASHTABLE_SIZE, 
		IHK_MC_AP_NOWAIT);
	if (tg == NULL) {
		return -ENOMEM;
	}
	XPMEM_DEBUG("kmalloc(): tg=0x%p", tg);
	memset(tg, 0, sizeof(struct xpmem_thread_group) + 
		sizeof(struct xpmem_hashlist) * XPMEM_AP_HASHTABLE_SIZE);

	ihk_mc_spinlock_init(&tg->lock);
	tg->tgid = cpu_local_var(current)->proc->pid;
	tg->uid = cpu_local_var(current)->proc->ruid;
	tg->gid = cpu_local_var(current)->proc->rgid;
	ihk_atomic_set(&tg->uniq_segid, 0);
	ihk_atomic_set(&tg->uniq_apid, 0);
	mcs_rwlock_init(&tg->seg_list_lock);
	INIT_LIST_HEAD(&tg->seg_list);
	ihk_atomic_set(&tg->n_pinned, 0);
	INIT_LIST_HEAD(&tg->tg_hashlist);
	tg->vm = cpu_local_var(current)->vm;

	for (index = 0; index < XPMEM_AP_HASHTABLE_SIZE; index++) {
		mcs_rwlock_init(&tg->ap_hashtable[index].lock);
		INIT_LIST_HEAD(&tg->ap_hashtable[index].list);
	}

	xpmem_tg_not_destroyable(tg);

	index = xpmem_tg_hashtable_index(tg->tgid);
	mcs_rwlock_writer_lock(&xpmem_my_part->tg_hashtable[index].lock, &lock);

	list_add_tail(&tg->tg_hashlist, 
		&xpmem_my_part->tg_hashtable[index].list);

	mcs_rwlock_writer_unlock(&xpmem_my_part->tg_hashtable[index].lock, 
		&lock);

	tg->group_leader = cpu_local_var(current);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static void xpmem_destroy_tg(
	struct xpmem_thread_group *tg)
{
	XPMEM_DEBUG("call: tg=0x%p", tg);

	xpmem_tg_destroyable(tg);
	xpmem_tg_deref(tg);

	XPMEM_DEBUG("return: ");
}


static int xpmem_make(
	unsigned long vaddr,
	size_t size,
	int permit_type,
	void *permit_value,
	xpmem_segid_t *segid_p)
{
	xpmem_segid_t segid;
	struct xpmem_thread_group *seg_tg;
	struct xpmem_segment *seg;
	struct mcs_rwlock_node_irqsave lock;
	int ret;

	XPMEM_DEBUG("call: vaddr=0x%lx, size=0x%lx, permit_type=%d, " 
		"permit_value=0%04lo", 
		vaddr, size, permit_type, 
		(unsigned long)(uintptr_t)permit_value);

	ret = xpmem_make_initial_policy_result(permit_type,
			(unsigned long)(uintptr_t)permit_value, size);
	if (ret) {
		XPMEM_DEBUG("return: ret=%d", -EINVAL);
		return ret;
	}

	seg_tg = xpmem_tg_ref_by_tgid(cpu_local_var(current)->proc->pid);
	if (IS_ERR(seg_tg)) {
		DBUG_ON(PTR_ERR(seg_tg) != -ENOENT);
		return -XPMEM_ERRNO_NOPROC;
	}

	/*
	 * The start of the segment must be page aligned and it must be a
	 * multiple of pages in size.
	 */
	ret = xpmem_make_alignment_result(vaddr, size);
	if (ret) {
		xpmem_tg_deref(seg_tg);
		XPMEM_DEBUG("return: ret=%d", -EINVAL);
		return ret;
	}

	segid = xpmem_make_segid(seg_tg);
	if (segid < 0) {
		xpmem_tg_deref(seg_tg);
		return segid;
	}

	/* create a new struct xpmem_segment structure with a unique segid */
	seg = kmalloc(sizeof(struct xpmem_segment), IHK_MC_AP_NOWAIT);
	if (seg == NULL) {
		xpmem_tg_deref(seg_tg);
		return -ENOMEM;
	}
	XPMEM_DEBUG("kmalloc(): seg=0x%p", seg);
	memset(seg, 0, sizeof(struct xpmem_segment));

	ihk_mc_spinlock_init(&seg->lock);
	seg->segid = segid;
	seg->vaddr = vaddr;
	seg->size = size;
	seg->permit_type = permit_type;
	seg->permit_value = permit_value;
	seg->tg = seg_tg;
	INIT_LIST_HEAD(&seg->ap_list);
	INIT_LIST_HEAD(&seg->seg_list);

	xpmem_seg_not_destroyable(seg);

	mcs_rwlock_writer_lock(&seg_tg->seg_list_lock, &lock);
	list_add_tail(&seg->seg_list, &seg_tg->seg_list);
	mcs_rwlock_writer_unlock(&seg_tg->seg_list_lock, &lock);

	xpmem_tg_deref(seg_tg);

	*segid_p = segid;

	XPMEM_DEBUG("return: ret=%d, segid=0x%lx", 0, *segid_p);

	return 0;
}


static xpmem_segid_t xpmem_make_segid(
	struct xpmem_thread_group *seg_tg)
{
	long segid = 0;
	xpmem_id_t debug_id;
	int ret;
	int uniq;

	XPMEM_DEBUG("call: seg_tg=0x%p, uniq_segid=%d", 
		seg_tg, ihk_atomic_read(&seg_tg->uniq_segid));

	uniq = ihk_atomic_inc_return(&seg_tg->uniq_segid);
	ret = xpmem_make_id_result(seg_tg->tgid, uniq, &segid);
	if (ret) {
		ihk_atomic_dec(&seg_tg->uniq_segid);
		return ret;
	}

	DBUG_ON(segid <= 0);
	debug_id.segid = segid;

	XPMEM_DEBUG("return: segid=0x%lx, segid.tgid=%d, segid.uniq=%d", 
		segid, debug_id.xpmem_id.tgid, debug_id.xpmem_id.uniq);

	return segid;
}


static int xpmem_remove(
	xpmem_segid_t segid)
{
	struct xpmem_thread_group *seg_tg;
	struct xpmem_segment *seg;
	int ret;

	XPMEM_DEBUG("call: segid=0x%lx", segid);

	ret = xpmem_positive_id_result(segid);
	if (ret) {
		XPMEM_DEBUG("return: ret=%d", -EINVAL);
		return ret;
	}

	seg_tg = xpmem_tg_ref_by_segid(segid);
	if (IS_ERR(seg_tg))
		return PTR_ERR(seg_tg);

	ret = xpmem_owner_policy_result(cpu_local_var(current)->proc->pid,
			seg_tg->tgid);
	if (ret) {
		xpmem_tg_deref(seg_tg);
		XPMEM_DEBUG("return: ret=%d", -EACCES);
		return ret;
	}

	seg = xpmem_seg_ref_by_segid(seg_tg, segid);
	if (IS_ERR(seg)) {
		xpmem_tg_deref(seg_tg);
		return PTR_ERR(seg);
	}
	DBUG_ON(seg->tg != seg_tg);

	xpmem_remove_seg(seg_tg, seg);
	xpmem_seg_deref(seg);
	xpmem_tg_deref(seg_tg);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static void xpmem_remove_seg(
	struct xpmem_thread_group *seg_tg,
	struct xpmem_segment *seg)
{
	DBUG_ON(ihk_atomic_read(&seg->refcnt) <= 0);
	struct mcs_rwlock_node_irqsave lock;
	int new_flags;

	XPMEM_DEBUG("call: tgid=%d, segid=0x%lx", seg_tg->tgid, seg->segid);

	ihk_mc_spinlock_lock_noirq(&seg->lock);
	if (!xpmem_begin_destroy_result(seg->flags, &new_flags)) {
		ihk_mc_spinlock_unlock_noirq(&seg->lock);
		return;
	}
	seg->flags = new_flags;
	ihk_mc_spinlock_unlock_noirq(&seg->lock);

	xpmem_clear_PTEs(seg);

	ihk_mc_spinlock_lock_noirq(&seg->lock);
	seg->flags = xpmem_finish_destroy_result(seg->flags);
	ihk_mc_spinlock_unlock_noirq(&seg->lock);

	mcs_rwlock_writer_lock(&seg_tg->seg_list_lock, &lock);
	list_del_init(&seg->seg_list);
	mcs_rwlock_writer_unlock(&seg_tg->seg_list_lock, &lock);

	xpmem_seg_destroyable(seg);

	XPMEM_DEBUG("return: ");
}


static void xpmem_remove_segs_of_tg(
	struct xpmem_thread_group *seg_tg)
{
	struct xpmem_segment *seg;
	struct mcs_rwlock_node_irqsave lock;

	XPMEM_DEBUG("call: tgid=%d", seg_tg->tgid);

	mcs_rwlock_writer_lock(&seg_tg->seg_list_lock, &lock);

	while (!list_empty(&seg_tg->seg_list)) {
		seg = list_entry((&seg_tg->seg_list)->next, 
			struct xpmem_segment, seg_list);
		xpmem_seg_ref(seg);
		mcs_rwlock_writer_unlock(&seg_tg->seg_list_lock, &lock);

		xpmem_remove_seg(seg_tg, seg);

		xpmem_seg_deref(seg);

		mcs_rwlock_writer_lock(&seg_tg->seg_list_lock, &lock);
	}

	mcs_rwlock_writer_unlock(&seg_tg->seg_list_lock, &lock);

	XPMEM_DEBUG("return: ");
}


static int xpmem_get(
	xpmem_segid_t segid,
	int flags,
	int permit_type,
	void *permit_value,
	xpmem_apid_t *apid_p)
{
	xpmem_apid_t apid;
	struct xpmem_access_permit *ap;
	struct xpmem_segment *seg;
	struct xpmem_thread_group *ap_tg, *seg_tg;
	int index;
	struct mcs_rwlock_node_irqsave lock;
	int ret;

	XPMEM_DEBUG("call: segid=0x%lx, flags=%d, permit_type=%d, " 
		"permit_value=0%04lo", 
		segid, flags, permit_type, 
		(unsigned long)(uintptr_t)permit_value);

	ret = xpmem_get_policy_result(segid, flags, permit_type,
			permit_value != NULL);
	if (ret) {
		return ret;
	}

	seg_tg = xpmem_tg_ref_by_segid(segid);
	if (IS_ERR(seg_tg)) {
		return PTR_ERR(seg_tg);
	}

	seg = xpmem_seg_ref_by_segid(seg_tg, segid);
	if (IS_ERR(seg)) {
		xpmem_tg_deref(seg_tg);
		return PTR_ERR(seg);
	}

	if (xpmem_check_permit_mode(flags, seg) != 0) {
		xpmem_seg_deref(seg);
		xpmem_tg_deref(seg_tg);
		return -EACCES;
	}

	ap_tg = xpmem_tg_ref_by_tgid(cpu_local_var(current)->proc->pid);
	if (IS_ERR(ap_tg)) {
		DBUG_ON(PTR_ERR(ap_tg) != -ENOENT);
		xpmem_seg_deref(seg);
		xpmem_tg_deref(seg_tg);
		return -XPMEM_ERRNO_NOPROC;
	}

	apid = xpmem_make_apid(ap_tg);
	if (apid < 0) {
		xpmem_tg_deref(ap_tg);
		xpmem_seg_deref(seg);
		xpmem_tg_deref(seg_tg);
		return apid;
	}

	/* create a new xpmem_access_permit structure with a unique apid */
	ap = kmalloc(sizeof(struct xpmem_access_permit), IHK_MC_AP_NOWAIT);
	if (ap == NULL) {
		xpmem_tg_deref(ap_tg);
		xpmem_seg_deref(seg);
		xpmem_tg_deref(seg_tg);
		return -ENOMEM;
	}
	XPMEM_DEBUG("kmalloc(): ap=0x%p", ap);
	memset(ap, 0, sizeof(struct xpmem_access_permit));

	ihk_mc_spinlock_init(&ap->lock);
	ap->apid = apid;
	ap->mode = flags;
	ap->seg = seg;
	ap->tg = ap_tg;
	INIT_LIST_HEAD(&ap->att_list);
	INIT_LIST_HEAD(&ap->ap_list);
	INIT_LIST_HEAD(&ap->ap_hashlist);

	xpmem_ap_not_destroyable(ap);

	/* add ap to its seg's access permit list */
	ihk_mc_spinlock_lock_noirq(&seg->lock);
	list_add_tail(&ap->ap_list, &seg->ap_list);
	ihk_mc_spinlock_unlock_noirq(&seg->lock);

	/* add ap to its hash list */
	index = xpmem_ap_hashtable_index(ap->apid);
	mcs_rwlock_writer_lock(&ap_tg->ap_hashtable[index].lock, &lock);
	list_add_tail(&ap->ap_hashlist, &ap_tg->ap_hashtable[index].list);
	mcs_rwlock_writer_unlock(&ap_tg->ap_hashtable[index].lock, &lock);

	xpmem_tg_deref(ap_tg);

	*apid_p = apid;

	XPMEM_DEBUG("return: ret=%d, apid=0x%lx", 0, *apid_p);

	return 0;
}


static int xpmem_check_permit_mode(
	int flags,
	struct xpmem_segment *seg)
{
	int ret;

	XPMEM_DEBUG("call: flags=%d", flags);

	DBUG_ON(seg->permit_type != XPMEM_PERMIT_MODE);

	ret = xpmem_check_permit_mode_result(flags, seg->tg->uid,
			seg->tg->gid, (unsigned long)seg->permit_value,
			cpu_local_var(current)->proc->ruid,
			cpu_local_var(current)->proc->rgid);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}


static int xpmem_perms(
	struct xpmem_perm *perm,
	short flag)
{
	int ret = 0;

	XPMEM_DEBUG("call: uid=%d, gid=%d, mode=0%lo, flag=0%o", 
		perm->uid, perm->gid, perm->mode, flag);

	ret = xpmem_perms_result(perm->uid, perm->gid, perm->mode, flag,
			cpu_local_var(current)->proc->ruid,
			cpu_local_var(current)->proc->rgid);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}


static xpmem_apid_t xpmem_make_apid(
	struct xpmem_thread_group *ap_tg)
{
	long apid = 0;
	xpmem_id_t debug_id;
	int ret;
	int uniq;

	XPMEM_DEBUG("call: ap_tg=0x%p, uniq_apid=%d", 
		ap_tg, ihk_atomic_read(&ap_tg->uniq_apid));

	uniq = ihk_atomic_inc_return(&ap_tg->uniq_apid);
	ret = xpmem_make_id_result(ap_tg->tgid, uniq, &apid);
	if (ret) {
		ihk_atomic_dec(&ap_tg->uniq_apid);
		return ret;
	}

	DBUG_ON(apid <= 0);
	debug_id.apid = apid;

	XPMEM_DEBUG("return: apid=0x%lx, apid.tgid=%d, apid.uniq=%d", 
		apid, debug_id.xpmem_id.tgid, debug_id.xpmem_id.uniq);

	return apid;
}


static int xpmem_release(
	xpmem_apid_t apid)
{
	struct xpmem_thread_group *ap_tg;
	struct xpmem_access_permit *ap;
	int ret;

	XPMEM_DEBUG("call: apid=0x%lx", apid);

	ret = xpmem_positive_id_result(apid);
	if (ret) {
		return ret;
	}

	ap_tg = xpmem_tg_ref_by_apid(apid);
	if (IS_ERR(ap_tg)) {
		return PTR_ERR(ap_tg);
	}

	ret = xpmem_owner_policy_result(cpu_local_var(current)->proc->pid,
			ap_tg->tgid);
	if (ret) {
		xpmem_tg_deref(ap_tg);
		return ret;
	}

	ap = xpmem_ap_ref_by_apid(ap_tg, apid);
	if (IS_ERR(ap)) {
		xpmem_tg_deref(ap_tg);
		return PTR_ERR(ap);
	}
	DBUG_ON(ap->tg != ap_tg);

	xpmem_release_ap(ap_tg, ap);
	xpmem_ap_deref(ap);
	xpmem_tg_deref(ap_tg);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static void xpmem_release_ap(
	struct xpmem_thread_group *ap_tg,
	struct xpmem_access_permit *ap)
{
	int index;
	int new_flags;
	struct xpmem_thread_group *seg_tg;
	struct xpmem_attachment *att;
	struct xpmem_segment *seg;
	struct mcs_rwlock_node_irqsave lock;

	XPMEM_DEBUG("call: tgid=%d, apid=0x%lx", ap_tg->tgid, ap->apid);

	ihk_mc_spinlock_lock_noirq(&ap->lock);
	if (!xpmem_begin_destroy_result(ap->flags, &new_flags)) {
		ihk_mc_spinlock_unlock_noirq(&ap->lock);
                return;
        }
	ap->flags = new_flags;

	while (!list_empty(&ap->att_list)) {
		att = list_entry((&ap->att_list)->next, struct xpmem_attachment,
			att_list);
		xpmem_att_ref(att);
		ihk_mc_spinlock_unlock_noirq(&ap->lock);

		xpmem_detach_att(ap, att);

		xpmem_att_deref(att);

		ihk_mc_spinlock_lock_noirq(&ap->lock);
	}

	ap->flags = xpmem_finish_destroy_result(ap->flags);

	ihk_mc_spinlock_unlock_noirq(&ap->lock);

	index = xpmem_ap_hashtable_index(ap->apid);
	mcs_rwlock_writer_lock(&ap_tg->ap_hashtable[index].lock, &lock);
	list_del_init(&ap->ap_hashlist);
	mcs_rwlock_writer_unlock(&ap_tg->ap_hashtable[index].lock, &lock);

	seg = ap->seg;
	seg_tg = seg->tg;

	ihk_mc_spinlock_lock_noirq(&seg->lock);
	list_del_init(&ap->ap_list);
	ihk_mc_spinlock_unlock_noirq(&seg->lock);

	xpmem_seg_deref(seg);
	xpmem_tg_deref(seg_tg);

	xpmem_ap_destroyable(ap);

	XPMEM_DEBUG("return: ");
}


static void xpmem_release_aps_of_tg(
	struct xpmem_thread_group *ap_tg)
{
	struct xpmem_hashlist *hashlist;
	struct xpmem_access_permit *ap;
	struct mcs_rwlock_node_irqsave lock;
	int index;

	XPMEM_DEBUG("call: tgid=%d", ap_tg->tgid);

	for (index = 0; index < XPMEM_AP_HASHTABLE_SIZE; index++) {
		hashlist = &ap_tg->ap_hashtable[index];

		mcs_rwlock_writer_lock(&hashlist->lock, &lock);
		while (!list_empty(&hashlist->list)) {
			ap = list_entry((&hashlist->list)->next,
				struct xpmem_access_permit, ap_hashlist);
			xpmem_ap_ref(ap);
			mcs_rwlock_writer_unlock(&hashlist->lock, &lock);

			xpmem_release_ap(ap_tg, ap);

			xpmem_ap_deref(ap);

			mcs_rwlock_writer_lock(&hashlist->lock, &lock);
		}
		mcs_rwlock_writer_unlock(&hashlist->lock, &lock);
	}

	XPMEM_DEBUG("return: ");
}

static void xpmem_flush(struct mckfd *mckfd)
{
	struct process *proc = (struct process *)mckfd->data;
	struct xpmem_thread_group *tg;
	int index;
	int new_flags;
	struct mcs_rwlock_node_irqsave lock;

	index = xpmem_tg_hashtable_index(proc->pid);

	mcs_rwlock_writer_lock(&xpmem_my_part->tg_hashtable[index].lock, &lock);

	tg = xpmem_tg_ref_by_tgid_all_nolock(proc->pid);
	if (IS_ERR(tg)) {
		mcs_rwlock_writer_unlock(
			&xpmem_my_part->tg_hashtable[index].lock, &lock);
		return;
	}

	list_del_init(&tg->tg_hashlist);

	mcs_rwlock_writer_unlock(&xpmem_my_part->tg_hashtable[index].lock, 
		&lock);

	XPMEM_DEBUG("tg->vm=0x%p", tg->vm);

	ihk_mc_spinlock_lock_noirq(&tg->lock);
	(void)xpmem_begin_destroy_result(tg->flags, &new_flags);
	tg->flags = new_flags;
	ihk_mc_spinlock_unlock_noirq(&tg->lock);

	xpmem_release_aps_of_tg(tg);
	xpmem_remove_segs_of_tg(tg);

	ihk_mc_spinlock_lock_noirq(&tg->lock);
	tg->flags = xpmem_finish_destroy_result(tg->flags);
	ihk_mc_spinlock_unlock_noirq(&tg->lock);

	xpmem_destroy_tg(tg);
}

static int xpmem_attach(
	struct mckfd *mckfd,
	xpmem_apid_t apid,
	off_t offset,
	size_t size,
	unsigned long vaddr,
	int fd,
	int att_flags,
	unsigned long *at_vaddr_p)
{
	int ret;
	unsigned long flags;
	unsigned long prot_flags = PROT_READ | PROT_WRITE;
	unsigned long seg_vaddr;
	unsigned long at_vaddr;
	struct xpmem_thread_group *ap_tg;
	struct xpmem_thread_group *seg_tg;
	struct xpmem_access_permit *ap;
	struct xpmem_segment *seg;
	struct xpmem_attachment *att;
	unsigned long at_lock;
	int new_flags;
	struct process_vm *vm = cpu_local_var(current)->vm;
#ifdef ENABLE_FJMPI_WORKAROUND
	int fjmpi_workaround = 1;
#else
	int fjmpi_workaround = 0;
#endif

	XPMEM_DEBUG("call: apid=0x%lx, offset=0x%lx, size=0x%lx, vaddr=0x%lx, " 
		"fd=%d, att_flags=%d", 
		apid, offset, size, vaddr, fd, att_flags);

	ret = xpmem_attach_initial_policy_result(apid, offset, vaddr, size,
			fjmpi_workaround, &size);
	if (ret) {
		return ret;
	}

	XPMEM_DEBUG("size after fix: 0x%lx", size);

	ap_tg = xpmem_tg_ref_by_apid(apid);
	if (IS_ERR(ap_tg))
		return PTR_ERR(ap_tg);

	ap = xpmem_ap_ref_by_apid(ap_tg, apid);
	if (IS_ERR(ap)) {
		xpmem_tg_deref(ap_tg);
		return PTR_ERR(ap);
	}

	seg = ap->seg;
	xpmem_seg_ref(seg);
	seg_tg = seg->tg;
	xpmem_tg_ref(seg_tg);

	ret = xpmem_attach_destroying_result(seg->flags, seg_tg->flags);
	if (ret) {
		goto out_1;
	}

	ret = xpmem_validate_access(ap, offset, size, XPMEM_RDWR, &seg_vaddr);
	if (ret != 0) {
		goto out_1;
	}

	size += offset_in_page(seg_vaddr);

	seg = ap->seg;
	ret = xpmem_attach_overlap_result(cpu_local_var(current)->proc->pid,
			seg_tg->tgid, vaddr, size, seg_vaddr);
	if (ret) {
		goto out_1;
	}

	/* create new attach structure */
	att = kmalloc(sizeof(struct xpmem_attachment), IHK_MC_AP_NOWAIT);
	if (att == NULL) {
		ret = -ENOMEM;
		goto out_1;
	}
	XPMEM_DEBUG("kmalloc(): att=0x%p", att);
	memset(att, 0, sizeof(struct xpmem_attachment));

	ihk_rwspinlock_init(&att->at_lock);
	att->vaddr = seg_vaddr;
	att->at_size = size;
	att->ap = ap;
	INIT_LIST_HEAD(&att->att_list);
	att->vm = vm;

        xpmem_att_not_destroyable(att);
        xpmem_att_ref(att);

	at_lock = ihk_rwspinlock_write_lock(&att->at_lock);

	ihk_mc_spinlock_lock_noirq(&ap->lock);
	list_add_tail(&att->att_list, &ap->att_list);
	ret = xpmem_destroying_error_result(ap->flags, -ENOENT);
	if (ret) {
		ihk_mc_spinlock_unlock_noirq(&ap->lock);
		goto out_2;
	}
	ihk_mc_spinlock_unlock_noirq(&ap->lock);

	flags = MAP_SHARED;
	if (vaddr != 0)
		flags |= MAP_FIXED;

	if (flags & MAP_FIXED) {
		struct vm_range *existing_vmr;

		ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);

		existing_vmr = lookup_process_memory_range(vm, vaddr, 
			vaddr + size);

		for (; existing_vmr && existing_vmr->start < vaddr + size;
			existing_vmr = next_process_memory_range(vm, 
			existing_vmr)) {
			if (xpmem_is_private_data(existing_vmr)) {
				ret = -EINVAL;
				ihk_rwspinlock_read_unlock_noirq(
					&vm->memory_range_lock);
				goto out_2;
			}
		}

		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
	}

	flags |= MAP_ANONYMOUS;
	XPMEM_DEBUG("do_mmap(): vaddr=0x%lx, size=0x%lx, prot_flags=0x%lx, " 
		"flags=0x%lx, fd=%d, offset=0x%lx", 
		vaddr, size, prot_flags, flags, mckfd->fd, offset);
	/* The new range is associated with shmobj because of
	 * MAP_ANONYMOUS && !MAP_PRIVATE && MAP_SHARED. Note that MAP_FIXED
	 * support prevents us from reusing segment vm_range when segment vm
	 * and attach vm is the same.
	 */
	at_vaddr = do_mmap(vaddr, size, prot_flags, flags, mckfd->fd,
			offset, VR_XPMEM, att);
	if (IS_ERR((void *)(uintptr_t)at_vaddr)) {
		ret = at_vaddr;
		goto out_2;
	}
	XPMEM_DEBUG("at_vaddr=0x%lx", at_vaddr);

	*at_vaddr_p = at_vaddr + offset_in_page(att->vaddr);

	ret = 0;
out_2:
	if (ret != 0) {
		(void)xpmem_begin_destroy_result(att->flags, &new_flags);
		att->flags = new_flags;
		ihk_mc_spinlock_lock_noirq(&ap->lock);
		list_del_init(&att->att_list);
		ihk_mc_spinlock_unlock_noirq(&ap->lock);
		xpmem_att_destroyable(att);
	}
	ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);
	xpmem_att_deref(att);
out_1:
	xpmem_ap_deref(ap);
	xpmem_tg_deref(ap_tg);
	xpmem_seg_deref(seg);
	xpmem_tg_deref(seg_tg);

	XPMEM_DEBUG("return: ret=%d, at_vaddr=0x%lx", ret, *at_vaddr_p);

	return ret;
}

static int xpmem_detach(
	unsigned long at_vaddr)
{
	int ret;
	struct xpmem_access_permit *ap;
	struct xpmem_attachment *att;
	unsigned long at_lock;
	struct vm_range *range;
	int new_flags;
	struct process_vm *vm = cpu_local_var(current)->vm;

	XPMEM_DEBUG("call: at_vaddr=0x%lx", at_vaddr);

	ihk_rwspinlock_write_lock_noirq(&vm->memory_range_lock);

	range = lookup_process_memory_range(vm, at_vaddr, at_vaddr + 1);

	ret = xpmem_detach_lookup_result(range != NULL,
			range ? range->start : 0, at_vaddr,
			range && range->private_data);
	if (ret <= 0) {
		ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
		return ret;
	}

	att = (struct xpmem_attachment *)range->private_data;
	xpmem_att_ref(att);

	at_lock = ihk_rwspinlock_write_lock(&att->at_lock);

	if (!xpmem_begin_destroy_result(att->flags, &new_flags)) {
		ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);
		ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
		xpmem_att_deref(att);
		return 0;
	}
	att->flags = new_flags;

	ap = att->ap;
	xpmem_ap_ref(ap);

	ret = xpmem_owner_policy_result(cpu_local_var(current)->proc->pid,
			ap->tg->tgid);
	if (ret) {
		att->flags &= ~XPMEM_FLAG_DESTROYING;
		xpmem_ap_deref(ap);
		ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);
		ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
		xpmem_att_deref(att);
		return ret;
	}

	xpmem_unpin_pages(ap->seg, vm, att->at_vaddr, att->at_size);

	range->private_data = NULL;
    /* range->memobj is released in xpmem_vm_munmap() --> xpmem_remove_process_range() -->
	   xpmem_free_process_memory_range() */

	ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);

	XPMEM_DEBUG("xpmem_vm_munmap(): start=0x%lx, len=0x%lx", 
		range->start, att->at_size);
	ret = xpmem_vm_munmap(vm, (void *)range->start, att->at_size);
	if (ret) {
		ekprintf("%s: ERROR: xpmem_vm_munmap() failed %d\n", 
			__FUNCTION__, ret);
	}
	ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
	DBUG_ON(ret != 0);

	att->flags &= ~XPMEM_FLAG_VALIDPTEs;

	ihk_mc_spinlock_lock_noirq(&ap->lock);
	list_del_init(&att->att_list);
	ihk_mc_spinlock_unlock_noirq(&ap->lock);

	xpmem_att_destroyable(att);

	xpmem_ap_deref(ap);
	xpmem_att_deref(att);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static int xpmem_vm_munmap(
	struct process_vm *vm,
	void *addr,
	size_t len)
{
	int ret;
	int ro_freed;

	XPMEM_DEBUG("call: vm=0x%p, addr=0x%p, len=0x%lx", vm, addr, len);

	begin_free_pages_pending();

	ret = xpmem_remove_process_range(vm, (intptr_t)addr, 
		(intptr_t)(addr + len), &ro_freed);

	finish_free_pages_pending();

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}


static int xpmem_remove_process_range(
	struct process_vm *vm,
	unsigned long start,
	unsigned long end,
	int *ro_freedp)
{
	int error = 0;
	struct vm_range *range;
	struct vm_range *next;
	int ro_freed = 0;

	XPMEM_DEBUG("call: vm=0x%p, start=0x%lx, end=0x%lx", vm, start, end);

	next = lookup_process_memory_range(vm, start, end);
	while ((range = next) && range->start < end) {
		int split_start;
		int split_end;
		int range_ro_freed;
		int remove_private;

		next = next_process_memory_range(vm, range);

		xpmem_remove_range_step_result(range->start, range->end,
				start, end, range->flag, range->private_data != NULL,
				&split_start, &split_end, &range_ro_freed,
				&remove_private);

		if (split_start) {
			error = split_process_memory_range(vm,
				range, start, &range);
			if (error) {
				ekprintf("%s(%p,%lx,%lx): ERROR: "
					"split failed %d\n",
					__FUNCTION__, vm, start, end, error);
				goto out;
			}
		}

		if (split_end) {
			error = split_process_memory_range(vm, range, end,
				NULL);
			if (error) {
				ekprintf("%s(%p,%lx,%lx): ERROR: "
					"split failed %d\n",
					__FUNCTION__, vm, start, end, error);
				goto out;
			}
		}

		if (range_ro_freed) {
			ro_freed = 1;
		}

		if (remove_private) {
			xpmem_remove_process_memory_range(vm, range);
		}

		error = xpmem_free_process_memory_range(vm, range);
		if (error) {
			ekprintf("%s(%p,%lx,%lx): ERROR: free failed %d\n",
				__FUNCTION__, vm, start, end, error);
			goto out;
		}
	}

	if (ro_freedp) {
		*ro_freedp = ro_freed;
	}

out:
	XPMEM_DEBUG("return: ret=%d, ro_freed=%d", error, ro_freed);

	return error;
}


static int xpmem_free_process_memory_range(
	struct process_vm *vm,
	struct vm_range *range)
{
	int error;
	int i;

	XPMEM_DEBUG("call: vm=0x%p, start=0x%lx, end=0x%lx", 
		vm, range->start, range->end);

	ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);

	error = ihk_mc_pt_clear_range(vm->address_space->page_table, vm,
		(void *)range->start, (void *)range->end);

	ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);

	if (error && (error != -ENOENT)) {
		ekprintf("%s(%p,%lx-%lx): ERROR: "
			"ihk_mc_pt_clear_range(%lx-%lx) failed %d\n",
			__FUNCTION__, vm, range->start, range->end, 
			range->start, range->end, error);
		/* through */
	}

	if (range->memobj) {
		memobj_unref(range->memobj);
	}

	rb_erase(&range->vm_rb_node, &vm->vm_range_tree);
	for (i = 0; i < VM_RANGE_CACHE_SIZE; ++i) {
		if (vm->range_cache[i] == range)
			vm->range_cache[i] = NULL;
	}

	kfree(range);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static void xpmem_detach_att(
	struct xpmem_access_permit *ap,
	struct xpmem_attachment *att)
{
	int ret;
	struct vm_range *range;
	struct process_vm *vm;
	unsigned long at_lock;
	int new_flags;

	XPMEM_DEBUG("call: apid=0x%lx, att=0x%p", ap->apid, att);

	XPMEM_DEBUG("detaching att->vm=0x%p", (void *)att->vm);

	at_lock = ihk_rwspinlock_write_lock(&att->at_lock);

	if (!xpmem_begin_destroy_result(att->flags, &new_flags)) {
		ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);
		XPMEM_DEBUG("return: XPMEM_FLAG_DESTROYING");
		return;
	}
	att->flags = new_flags;

	vm = att->vm;
	ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);

	range = lookup_process_memory_range(vm,
		att->at_vaddr, att->at_vaddr + 1);

	if (!range || range->start > att->at_vaddr) {
		ihk_mc_spinlock_lock_noirq(&ap->lock);
		list_del_init(&att->att_list);
		ihk_mc_spinlock_unlock_noirq(&ap->lock);
		ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);
		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
		xpmem_att_destroyable(att);
		XPMEM_DEBUG("return: range=%p");
		return;
	}
	XPMEM_DEBUG("lookup_process_memory_range(): at_vaddr=0x%lx, " 
		"start=0x%lx, end=0x%lx", 
		att->at_vaddr, range->start, range->end);

	DBUG_ON(!xpmem_is_private_data(range));
	DBUG_ON((range->end - range->start) != att->at_size);
	DBUG_ON(range->private_data != att);

	xpmem_unpin_pages(ap->seg, vm, att->at_vaddr, att->at_size);

	range->private_data = NULL;
	/* range->memobj is released in xpmem_vm_munmap() --> xpmem_remove_process_range() -->
	   xpmem_free_process_memory_range() */

	att->flags &= ~XPMEM_FLAG_VALIDPTEs;

	ihk_mc_spinlock_lock_noirq(&ap->lock);
	list_del_init(&att->att_list);
	ihk_mc_spinlock_unlock_noirq(&ap->lock);

	ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);

	XPMEM_DEBUG("xpmem_vm_munmap(): start=0x%lx, len=0x%lx", 
		range->start, att->at_size);
	ret = xpmem_vm_munmap(vm, (void *)range->start, att->at_size);
	if (ret) {
		ekprintf("%s: ERROR: xpmem_vm_munmap() failed %d\n", 
			__FUNCTION__, ret);
	}

	ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);

	xpmem_att_destroyable(att);

	XPMEM_DEBUG("return: ");
}


static void xpmem_clear_PTEs(
	struct xpmem_segment *seg)
{
	XPMEM_DEBUG("call: segid=0x%lx", seg->segid);

	xpmem_clear_PTEs_range(seg, seg->vaddr, seg->vaddr + seg->size);

	XPMEM_DEBUG("return: ");
}


static void xpmem_clear_PTEs_range(
	struct xpmem_segment *seg,
	unsigned long start,
	unsigned long end)
{
	struct xpmem_access_permit *ap;

	XPMEM_DEBUG("call: segid=0x%lx, start=0x%lx, end=0x%lx", 
		seg->segid, start, end);

	ihk_mc_spinlock_lock_noirq(&seg->lock);

	list_for_each_entry(ap, &seg->ap_list, ap_list) {
		xpmem_ap_ref(ap);
		ihk_mc_spinlock_unlock_noirq(&seg->lock);

		xpmem_clear_PTEs_of_ap(ap, start, end);

		ihk_mc_spinlock_lock_noirq(&seg->lock);
		if (list_empty(&ap->ap_list)) {
			xpmem_ap_deref(ap);
			ap = list_entry(&seg->ap_list, 
				struct xpmem_access_permit, ap_list);
		}
		else {
			xpmem_ap_deref(ap);
		}
	}

	ihk_mc_spinlock_unlock_noirq(&seg->lock);

	XPMEM_DEBUG("return: ");
}


static void xpmem_clear_PTEs_of_ap(
	struct xpmem_access_permit *ap,
	unsigned long start,
	unsigned long end)
{
	struct xpmem_attachment *att;

	XPMEM_DEBUG("call: apid=0x%lx, start=0x%lx, end=0x%lx", 
		ap->apid, start, end);

	ihk_mc_spinlock_lock_noirq(&ap->lock);

	list_for_each_entry(att, &ap->att_list, att_list) {
		if (!(att->flags & XPMEM_FLAG_VALIDPTEs))
			continue;

		xpmem_att_ref(att);
		ihk_mc_spinlock_unlock_noirq(&ap->lock);

		xpmem_clear_PTEs_of_att(att, start, end);

		ihk_mc_spinlock_lock_noirq(&ap->lock);
		if (list_empty(&att->att_list)) {
			xpmem_att_deref(att);
			att = list_entry(&ap->att_list, struct xpmem_attachment,
				att_list);
		}
		else {
			xpmem_att_deref(att);
		}
	}

	ihk_mc_spinlock_unlock_noirq(&ap->lock);

	XPMEM_DEBUG("return: ");
}


static void xpmem_clear_PTEs_of_att(
	struct xpmem_attachment *att,
	unsigned long start,
	unsigned long end)
{
	int ret;
	unsigned long at_lock;

	XPMEM_DEBUG("call: att=0x%p, start=0x%lx, end=0x%lx", 
		att, start, end);

	ihk_rwspinlock_read_lock_noirq(&att->vm->memory_range_lock);
	at_lock = ihk_rwspinlock_write_lock(&att->at_lock);

	if (att->flags & XPMEM_FLAG_VALIDPTEs) {
		struct vm_range *range;
		unsigned long invalidate_len;
		unsigned long unpin_at;
		int clear_valid;

		if (!xpmem_clear_pte_range_result(att->flags, att->vaddr,
				att->at_vaddr, att->at_size, start, end,
				&unpin_at, &invalidate_len, &clear_valid))
			goto out;
		DBUG_ON(offset_in_page(unpin_at) ||
			offset_in_page(invalidate_len));
		XPMEM_DEBUG("unpin_at=0x%lx, invalidate_len=0x%lx\n",
			unpin_at, invalidate_len);

		xpmem_unpin_pages(att->ap->seg, att->vm, unpin_at,
			invalidate_len);

		range = lookup_process_memory_range(att->vm, att->at_vaddr, 
			att->at_vaddr + 1);
		if (!range) {
			ekprintf("%s: ERROR: lookup_process_memory_range() " 
				"failed\n", 
				__FUNCTION__);
			goto out;
		}

		ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);

		XPMEM_DEBUG(
			"xpmem_vm_munmap(): start=0x%lx, len=0x%lx", 
			unpin_at, invalidate_len);
		ret = xpmem_vm_munmap(att->vm, (void *)unpin_at, 
			invalidate_len);
		if (ret) {
			ekprintf("%s: ERROR: xpmem_vm_munmap() failed %d\n", 
				__FUNCTION__, ret);
		}

		at_lock = ihk_rwspinlock_write_lock(&att->at_lock);

		if (clear_valid)
			att->flags &= ~XPMEM_FLAG_VALIDPTEs;
	}
out:
	ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);
	ihk_rwspinlock_read_unlock_noirq(&att->vm->memory_range_lock);

	XPMEM_DEBUG("return: ");
}


int xpmem_remove_process_memory_range(
	struct process_vm *vm,
	struct vm_range *vmr)
{
	struct vm_range *remaining_vmr;
	unsigned long remaining_vaddr;
	unsigned long middle_lookup_vaddr;
	struct xpmem_access_permit *ap;
	struct xpmem_attachment *att;
	unsigned long at_lock;
	int full_detach;
	int needs_middle_lookup;
	int new_flags;

	XPMEM_DEBUG("call: vmr=0x%p, att=0x%p", vmr, vmr->private_data);

	att = (struct xpmem_attachment *)vmr->private_data;
	if (att == NULL) {
		return 0;
	}

	XPMEM_DEBUG("cleaning up vmr with range: 0x%lx - 0x%lx", 
		vmr->start, vmr->end);

	xpmem_att_ref(att);

	at_lock = ihk_rwspinlock_write_lock(&att->at_lock);

	if (xpmem_is_destroying_result(att->flags)) {
		XPMEM_DEBUG("already cleaned up");
		goto out;
	}

	xpmem_remove_memory_range_action_result(vmr->start, vmr->end,
			att->at_vaddr, att->at_size, &remaining_vaddr,
			&middle_lookup_vaddr, &full_detach,
			&needs_middle_lookup);

	if (full_detach) {
		(void)xpmem_begin_destroy_result(att->flags, &new_flags);
		att->flags = new_flags;

		ap = att->ap;
		xpmem_ap_ref(ap);

		ihk_mc_spinlock_lock_noirq(&ap->lock);
		list_del_init(&att->att_list);
		ihk_mc_spinlock_unlock_noirq(&ap->lock);

		xpmem_ap_deref(ap);

		xpmem_att_destroyable(att);
		goto out;
	}

	if (needs_middle_lookup) {
		remaining_vmr = lookup_process_memory_range(
			vm, middle_lookup_vaddr - 1,
			middle_lookup_vaddr);
		if (xpmem_range_private_invalid_result(remaining_vmr != NULL,
				remaining_vmr ? remaining_vmr->start : 0,
				middle_lookup_vaddr,
				remaining_vmr &&
				remaining_vmr->private_data == vmr->private_data)) {
			ekprintf("%s: ERROR: vm_range is NULL\n", __FUNCTION__);
			goto out;
		}

		remaining_vmr->private_data = NULL;
		/* This function is always followed by xpmem_free_process_memory_range() 
		 * which in turn calls memobj_put()
		 */
	}

	remaining_vmr = lookup_process_memory_range(
		vm, remaining_vaddr,
		remaining_vaddr + 1);
	if (xpmem_range_private_invalid_result(remaining_vmr != NULL,
			remaining_vmr ? remaining_vmr->start : 0,
			remaining_vaddr,
			remaining_vmr &&
			remaining_vmr->private_data == vmr->private_data)) {
		ekprintf("%s: ERROR: vm_range is NULL\n", __FUNCTION__);
		goto out;
	}

	att->at_vaddr = remaining_vmr->start;
	att->at_size = remaining_vmr->end - remaining_vmr->start;

	vmr->private_data = NULL;
	/* This function is always followed by [xpmem_]free_process_memory_range()
	 * which in turn calls memobj_put()
	 */

out:
	ihk_rwspinlock_write_unlock(&att->at_lock, at_lock);

	xpmem_att_deref(att);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
}


static int _xpmem_fault_process_memory_range(
	struct process_vm *vm,
	struct vm_range *vmr,
	unsigned long vaddr,
	uint64_t reason,
	int page_in_remote)
{
	int ret = 0;
	unsigned long seg_vaddr;
	struct xpmem_thread_group *ap_tg;
	struct xpmem_thread_group *seg_tg;
	struct xpmem_access_permit *ap;
	struct xpmem_attachment *att;
	struct xpmem_segment *seg;
	pte_t *att_pte;
	void *att_pgaddr;
	size_t att_pgsize;
	int att_p2align;
	pte_t *seg_pte;
	size_t seg_pgsize;
	unsigned long seg_phys;
	unsigned long seg_phys_plus_off;
	unsigned long seg_phys_aligned;
	enum ihk_mc_pt_attribute att_attr;

	XPMEM_DEBUG("call: vmr=0x%p, vaddr=0x%lx, reason=0x%lx, page_in_remote: %d", 
		    vmr, vaddr, reason, page_in_remote);

	att = (struct xpmem_attachment *)vmr->private_data;
	if (att == NULL) {
		return -EFAULT;
	}

	xpmem_att_ref(att);
	ap = att->ap;
	xpmem_ap_ref(ap);
	ap_tg = ap->tg;
	xpmem_tg_ref(ap_tg);
	ret = xpmem_two_destroying_error_result(ap->flags, ap_tg->flags,
			-EFAULT);
	if (ret) {
		xpmem_att_deref(att);
		xpmem_ap_deref(ap);
		xpmem_tg_deref(ap_tg);
		return ret;
	}
	DBUG_ON(cpu_local_var(current)->proc->pid != ap_tg->tgid);
	DBUG_ON(ap->mode != XPMEM_RDWR);

	seg = ap->seg;
	xpmem_seg_ref(seg);
	seg_tg = seg->tg;
	xpmem_tg_ref(seg_tg);

	ret = xpmem_two_destroying_error_result(seg->flags, seg_tg->flags,
			-EFAULT);
	if (ret) {
		goto out;
	}

	ret = xpmem_three_destroying_error_result(att->flags, ap_tg->flags,
			seg_tg->flags, -EFAULT);
	if (ret) {
		kprintf("%s: XPMEM_FLAG_DESTROYING\n",
			__func__);
		goto out;
	}

	ret = xpmem_fault_vaddr_result(vaddr, att->at_vaddr, att->at_size,
			att->vaddr, &seg_vaddr);
	if (ret) {
		kprintf("%s: vaddr: %lx, att->at_vaddr: %lx, att->at_size: %lx\n",
			__func__, vaddr, att->at_vaddr, att->at_size);
		goto out;
	}

	/* page-in remote pages on page-fault or (on attach and
	 * xpmem_page_in_remote_on_attach isn't specified)
	 */
	XPMEM_DEBUG("vaddr=%lx, seg_vaddr=%lx", vaddr, seg_vaddr);

	ret = xpmem_ensure_valid_page(seg, seg_vaddr, page_in_remote);
	if (ret != 0) {
		goto out;
	}

	if (is_remote_vm(seg_tg->vm)) {
		ihk_rwspinlock_read_lock_noirq(&seg_tg->vm->memory_range_lock);
	}

	if (xpmem_straight_phys_result(seg_vaddr,
			(unsigned long)seg_tg->vm->proc->straight_va,
			seg_tg->vm->proc->straight_len,
			seg_tg->vm->proc->straight_pa, &seg_phys,
			&seg_pgsize)) {
		XPMEM_DEBUG("seg_vaddr: 0x%lx in PID %d is straight -> phys: 0x%lx",
			    (unsigned long)seg_vaddr & PAGE_MASK,
			    seg_tg->tgid, seg_phys);
	}
	else {
		seg_pte = xpmem_vaddr_to_pte(seg_tg->vm, seg_vaddr, &seg_pgsize);

		/* map only resident remote pages on attach and
		 * xpmem_page_in_remote_on_attach is specified
		 */
		ret = xpmem_remote_pte_missing_result(seg_pte != NULL,
				seg_pte && pte_is_null(seg_pte),
				page_in_remote);
		if (ret != 1) {
			if (is_remote_vm(seg_tg->vm)) {
				ihk_rwspinlock_read_unlock_noirq(&seg_tg->vm->memory_range_lock);
			}
			goto out;
		}
		ret = 0;

		seg_phys = pte_get_phys(seg_pte);
	}

	/* clear lower bits of the contiguous-PTE tail entries */
	seg_phys_plus_off = xpmem_seg_phys_plus_off_result(seg_phys,
			seg_pgsize, seg_vaddr);
	XPMEM_DEBUG("seg_vaddr: %lx, seg_phys: %lx, seg_phys_plus_off: %lx, seg_pgsize: %lx",
		    seg_vaddr, seg_phys, seg_phys_plus_off, seg_pgsize);

	if (is_remote_vm(seg_tg->vm)) {
		ihk_rwspinlock_read_unlock_noirq(&seg_tg->vm->memory_range_lock);
	}

	/* find largest page-size fitting vm range and segment page */
	att_pte = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
		(void *)vaddr, vmr->pgshift, &att_pgaddr, &att_pgsize,
		&att_p2align);

	while (!xpmem_att_page_fits_result((unsigned long)att_pgaddr,
			att_pgsize, vmr->start, vmr->end, seg_pgsize)) {
		att_pte = NULL;
		ret = arch_get_smaller_page_size(NULL, att_pgsize,
						 &att_pgsize, &att_p2align);
		if (ret) {
			kprintf("%s: arch_get_smaller_page_size failed: "
				 " range: %lx-%lx, pgsize: %lx, ret: %d\n",
				 __func__, vmr->start, vmr->end, att_pgsize,
				 ret);
			goto out;
		}
		att_pgaddr = (void *)(vaddr & ~(att_pgsize - 1));
	}

	arch_adjust_allocate_page_size(vm->address_space->page_table,
				       vaddr, att_pte, &att_pgaddr,
				       &att_pgsize);

	seg_phys_aligned = seg_phys_plus_off & ~(att_pgsize - 1);

	XPMEM_DEBUG("att_pte=%p, att_pgaddr=0x%p, att_pgsize=%lu, "
		    "att_p2align=%d",
		    att_pte, att_pgaddr, att_pgsize, att_p2align);

	/* last arg is not used */
	att_attr = arch_vrflag_to_ptattr(vmr->flag, reason, NULL);
	XPMEM_DEBUG("att_attr=0x%lx", att_attr);

	if (att_pte && !pte_is_null(att_pte)) {
		unsigned long att_phys = pte_get_phys(att_pte);

		ret = xpmem_pte_mismatch_result(att_phys, seg_phys_aligned);
		if (ret) {
			ekprintf("%s: ERROR: pte mismatch: "
				 "0x%lx != 0x%lx\n",
				 __func__, att_phys, seg_phys_aligned);
		}

		if (page_in_remote) {
			ihk_atomic_dec(&seg->tg->n_pinned);
		}
		goto out;
	}

	XPMEM_DEBUG("att_pgaddr: %lx, att_pgsize: %lx, "
		    "seg_vaddr: %lx, seg_pgsize: %lx, "
		    "seg_phys_aligned: %lx\n",
		    att_pgaddr, att_pgsize, seg_vaddr,
		    seg_pgsize, seg_phys_aligned);
	if (att_pte && !pgsize_is_contiguous(att_pgsize)) {
		ret = ihk_mc_pt_set_pte(vm->address_space->page_table,
					att_pte, att_pgsize,
					seg_phys_aligned,
					att_attr);
		if (ret) {
			ret = -EFAULT;
			ekprintf("%s: ERROR: ihk_mc_pt_set_pte() failed %d\n",
				__func__, ret);
			goto out;
		}
	}
	else {
		ret = ihk_mc_pt_set_range(vm->address_space->page_table, vm,
					  att_pgaddr, att_pgaddr + att_pgsize,
					  seg_phys_aligned,
					  att_attr, vmr->pgshift, vmr, 1);
		if (ret) {
			ret = -EFAULT;
			ekprintf("%s: ERROR: ihk_mc_pt_set_range() failed %d\n",
				 __func__, ret);
			goto out;
		}
	}

	att->flags |= XPMEM_FLAG_VALIDPTEs;
	flush_tlb_single(vaddr);

out:
	xpmem_ap_deref(ap);
	xpmem_tg_deref(ap_tg);
	xpmem_tg_deref(seg_tg);
	xpmem_seg_deref(seg);
	xpmem_att_deref(att);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}

int xpmem_fault_process_memory_range(
	struct process_vm *vm,
	struct vm_range *vmr,
	unsigned long vaddr,
	uint64_t reason)
{
	int ret;
	unsigned long at_lock;
	struct xpmem_attachment *att;

	att = (struct xpmem_attachment *)vmr->private_data;
	if (att == NULL) {
		return -EFAULT;
	}
	at_lock = ihk_rwspinlock_read_lock(&att->at_lock);
	ret = _xpmem_fault_process_memory_range(vm, vmr, vaddr, reason, 1);
	ihk_rwspinlock_read_unlock(&att->at_lock, at_lock);
	return ret;
}

int xpmem_update_process_page_table(
	struct process_vm *vm, struct vm_range *vmr)
{
	int ret = 0;
	unsigned long vaddr;
	pte_t *pte;
	size_t pgsize;
	struct xpmem_thread_group *ap_tg;
	struct xpmem_thread_group *seg_tg;
	struct xpmem_access_permit *ap;
	struct xpmem_attachment *att;
	struct xpmem_segment *seg;

	XPMEM_DEBUG("call: vmr=0x%p", vmr);

	att = (struct xpmem_attachment *)vmr->private_data;
	if (att == NULL) {
		return -EFAULT;
	}

	xpmem_att_ref(att);
	ap = att->ap;
	xpmem_ap_ref(ap);
	ap_tg = ap->tg;
	xpmem_tg_ref(ap_tg);

	ret = xpmem_two_destroying_error_result(ap->flags, ap_tg->flags,
			-EFAULT);
	if (ret) {
		goto out_1;
	}

	DBUG_ON(cpu_local_var(current)->proc->pid != ap_tg->tgid);
	DBUG_ON(ap->mode != XPMEM_RDWR);

	seg = ap->seg;
	xpmem_seg_ref(seg);
	seg_tg = seg->tg;
	xpmem_tg_ref(seg_tg);

	ret = xpmem_two_destroying_error_result(seg->flags, seg_tg->flags,
			-ENOENT);
	if (ret) {
		goto out_2;
	}

	att->at_vaddr = vmr->start;
	att->at_vmr = vmr;

	if (xpmem_three_destroying_error_result(att->flags, ap_tg->flags,
			seg_tg->flags, 1)) {
		ret = 0;
		goto out_2;
	}

	for (vaddr = vmr->start; vaddr < vmr->end; vaddr += pgsize) {
		XPMEM_DEBUG("vmr: %lx-%lx, vaddr: %lx",
			    vmr->start, vmr->end, vaddr);

		ret = _xpmem_fault_process_memory_range(vm, vmr, vaddr,
							0,
							xpmem_page_in_remote_on_attach);
		if (ret) {
			ekprintf("%s: ERROR: "
				 "_xpmem_fault_process_memory_range() "
				 "failed %d\n", __func__, ret);
		}

		pte = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
					       (void *)vaddr, vmr->pgshift,
					       NULL, &pgsize, NULL);

		/* when segment page is not resident and
		 * xpmem_page_in_remote_on_attach is specified
		 */
		if (!pte || pte_is_null(pte)) {
			pgsize = PAGE_SIZE;
		}
	}

out_2:
	xpmem_tg_deref(seg_tg);
	xpmem_seg_deref(seg);

out_1:
	xpmem_att_deref(att);
	xpmem_ap_deref(ap);
	xpmem_tg_deref(ap_tg);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}

static int xpmem_ensure_valid_page(
	struct xpmem_segment *seg,
	unsigned long vaddr,
	int page_in)
{
	int ret;
	struct xpmem_thread_group *seg_tg = seg->tg;

	XPMEM_DEBUG("call: segid=0x%lx, vaddr=0x%lx", seg->segid, vaddr);

	ret = xpmem_destroying_error_result(seg->flags, -ENOENT);
	if (ret)
		return ret;

	ret = xpmem_pin_page(seg_tg, seg_tg->group_leader, seg_tg->vm, vaddr,
			     page_in);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}


static pte_t * xpmem_vaddr_to_pte(
	struct process_vm *vm,
	unsigned long vaddr,
	size_t *pgsize)
{
	pte_t *pte = NULL;
	struct vm_range *range;
	int pgshift;
	void *base;
	size_t size;
	int p2align;

	range = lookup_process_memory_range(vm, vaddr, vaddr + 1);
	if (range) {
		pgshift = range->pgshift;
	}
	else {
		goto out;
	}

	pte = ihk_mc_pt_lookup_pte(vm->address_space->page_table, 
		(void *)vaddr, pgshift, &base, &size, &p2align);
	if (pte) {
		*pgsize = size;
	}
	else {
		*pgsize = PAGE_SIZE;
	}

out:
	return pte;
}


static int xpmem_pin_page(
	struct xpmem_thread_group *tg,
	struct thread *src_thread,
	struct process_vm *src_vm,
	unsigned long vaddr,
	int page_in)
{
	int ret = 0;
	struct vm_range *range;

	XPMEM_DEBUG("call: tgid=%d, vaddr=0x%lx", tg->tgid, vaddr);

retry:
	if (is_remote_vm(src_vm)) {
		ihk_rwspinlock_read_lock_noirq(&src_vm->memory_range_lock);
	}

	range = lookup_process_memory_range(src_vm, vaddr, vaddr + 1);

	if (!range || range->start > vaddr) {
		if (is_remote_vm(src_vm)) {
			ihk_rwspinlock_read_unlock_noirq(&src_vm->memory_range_lock);
		}

		/*
		 * Grow the stack if address falls into stack region
		 * so that we can lookup range successfully.
		 */
		if (src_vm->region.stack_start <= vaddr &&
				src_vm->region.stack_end > vaddr) {
			if (page_fault_process_vm(src_vm, (void *)vaddr,
						PF_POPULATE | PF_WRITE | PF_USER) < 0) {
				return -ENOENT;
			}

			goto retry;
		}

		return -ENOENT;
	}

	if (xpmem_is_private_data(range)) {
		ret = -ENOENT;
		goto out;
	}

	/* Page-in remote area */
	if (page_in) {
		/* skip read lock for the case src_vm is local
		 * because write lock is taken in do_mmap.
		 */
		ret = page_fault_process_memory_range(src_vm, range,
						      vaddr,
						      PF_POPULATE | PF_WRITE |
						      PF_USER);
		if (ret) {
			goto out;
		}
		ihk_atomic_inc(&tg->n_pinned);
	}

out:
	if (is_remote_vm(src_vm)) {
		ihk_rwspinlock_read_unlock_noirq(&src_vm->memory_range_lock);
	}
	XPMEM_DEBUG("return: ret=%d", ret);
	return ret;
}


static void xpmem_unpin_pages(
	struct xpmem_segment *seg,
	struct process_vm *vm,
	unsigned long vaddr,
	size_t size)
{
	int n_pgs_unpinned = 0;
	size_t vsize = 0;
	unsigned long end = vaddr + size;
	pte_t *pte = NULL;

	XPMEM_DEBUG("call: segid=0x%lx, vaddr=0x%lx, size=0x%lx", 
		seg->segid, vaddr, size);

	vaddr &= PAGE_MASK;

	/* attachment can't be straight-mapped because it's mapped
	 * with MAP_SHARED
	 */
	while (vaddr < end) {
		unsigned long next_vaddr;
		int unpinned;

		pte = xpmem_vaddr_to_pte(vm, vaddr, &vsize);
		xpmem_unpin_step_result(vaddr, vsize,
				pte && !pte_is_null(pte), &next_vaddr,
				&unpinned);
		if (unpinned) {
			n_pgs_unpinned++;
		}
		vaddr = next_vaddr;
	}

	XPMEM_DEBUG("sub: tg->n_pinned=%d, n_pgs_unpinned=%d", 
		seg->tg->n_pinned, n_pgs_unpinned);
	ihk_atomic_sub(n_pgs_unpinned, &seg->tg->n_pinned);

	XPMEM_DEBUG("return: ");
}


static struct xpmem_thread_group *__xpmem_tg_ref_by_tgid_nolock_internal(
	pid_t tgid,
	int index,
	int return_destroying)
{
	struct xpmem_thread_group *tg;
	int lookup;

	list_for_each_entry(tg, &xpmem_my_part->tg_hashtable[index].list,
		tg_hashlist) {
		lookup = xpmem_object_lookup_decision_result(tg->tgid, tgid,
				tg->flags, return_destroying, 0);
		if (lookup == XPMEM_LOOKUP_TAKE) {

			xpmem_tg_ref(tg);

			return tg;
		}
	}

	return ERR_PTR(-ENOENT);
}


static struct xpmem_thread_group *xpmem_tg_ref_by_segid(
	xpmem_segid_t segid)
{
	struct xpmem_thread_group *tg;

	tg = xpmem_tg_ref_by_tgid(xpmem_segid_to_tgid(segid));

        return tg;
}


static struct xpmem_thread_group *xpmem_tg_ref_by_apid(
	xpmem_apid_t apid)
{
	struct xpmem_thread_group *tg;

	tg = xpmem_tg_ref_by_tgid(xpmem_apid_to_tgid(apid));

	return tg;
}


static void xpmem_tg_deref(
	struct xpmem_thread_group *tg)
{
	DBUG_ON(ihk_atomic_read(&tg->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&tg->refcnt))) {
		/*XPMEM_DEBUG("return: tg->refcnt=%d, tg->n_pinned=%d", 
		  tg->refcnt, tg->n_pinned);*/
		return;
	}

	XPMEM_DEBUG("kfree(): tg=0x%p", tg);
	kfree(tg);
}


static struct xpmem_segment * xpmem_seg_ref_by_segid(
	struct xpmem_thread_group *seg_tg,
	xpmem_segid_t segid)
{
	struct xpmem_segment *seg;
	struct mcs_rwlock_node_irqsave lock;
	int lookup;

	mcs_rwlock_reader_lock(&seg_tg->seg_list_lock, &lock);

	list_for_each_entry(seg, &seg_tg->seg_list, seg_list) {
		lookup = xpmem_object_lookup_decision_result(seg->segid, segid,
				seg->flags, 0, 0);
		if (lookup == XPMEM_LOOKUP_TAKE) {
			xpmem_seg_ref(seg);
			mcs_rwlock_reader_unlock(&seg_tg->seg_list_lock, &lock);
			return seg;
		}
	}

	mcs_rwlock_reader_unlock(&seg_tg->seg_list_lock, &lock);

	return ERR_PTR(-ENOENT);
}


static void xpmem_seg_deref(struct xpmem_segment *seg)
{
	DBUG_ON(ihk_atomic_read(&seg->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&seg->refcnt))) {
		//XPMEM_DEBUG("return: seg->refcnt=%d", seg->refcnt);
		return;
	}

	DBUG_ON(!(seg->flags & XPMEM_FLAG_DESTROYING));

	XPMEM_DEBUG("kfree(): seg=0x%p", seg);
	kfree(seg);
}


static struct xpmem_access_permit * xpmem_ap_ref_by_apid(
	struct xpmem_thread_group *ap_tg,
	xpmem_apid_t apid)
{
	int index;
	struct xpmem_access_permit *ap;
	struct mcs_rwlock_node_irqsave lock;
	int lookup;

	index = xpmem_ap_hashtable_index(apid);
	mcs_rwlock_reader_lock(&ap_tg->ap_hashtable[index].lock, &lock);

	list_for_each_entry(ap, &ap_tg->ap_hashtable[index].list,
		ap_hashlist) {
		lookup = xpmem_object_lookup_decision_result(ap->apid, apid,
				ap->flags, 0, 1);
		if (lookup == XPMEM_LOOKUP_TAKE) {

			xpmem_ap_ref(ap);
			mcs_rwlock_reader_unlock(
				&ap_tg->ap_hashtable[index].lock, &lock);
			return ap;
		}
		if (lookup == XPMEM_LOOKUP_STOP)
			break;
	}

	mcs_rwlock_reader_unlock(&ap_tg->ap_hashtable[index].lock, &lock);

	return ERR_PTR(-ENOENT);
}


static void xpmem_ap_deref(struct xpmem_access_permit *ap)
{
	DBUG_ON(ihk_atomic_read(&ap->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&ap->refcnt))) {
		//XPMEM_DEBUG("return: ap->refcnt=%d", ap->refcnt);
		return;
	}

	DBUG_ON(!(ap->flags & XPMEM_FLAG_DESTROYING));

	XPMEM_DEBUG("kfree(): ap=0x%p", ap);
	kfree(ap);
}


static void xpmem_att_deref(struct xpmem_attachment *att)
{
	DBUG_ON(ihk_atomic_read(&att->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&att->refcnt))) {
		//XPMEM_DEBUG("return: att->refcnt=%d", att->refcnt);
		return;
	}

	DBUG_ON(!(att->flags & XPMEM_FLAG_DESTROYING));

	XPMEM_DEBUG("kfree(): att=0x%p", att);
	kfree(att);
}


static int xpmem_validate_access(
	struct xpmem_access_permit *ap,
	off_t offset,
	size_t size,
	int mode,
	unsigned long *vaddr)
{
	int ret;

	XPMEM_DEBUG("call: apid=0x%lx, offset=0x%lx, size=0x%lx, mode=%d",  
		ap->apid, offset, size, mode);

	ret = xpmem_validate_access_result(cpu_local_var(current)->proc->pid,
			ap->tg->tgid, ap->mode, ap->seg->vaddr, ap->seg->size,
			offset, size, mode, vaddr);
	if (ret) {
		return ret;
	}

	XPMEM_DEBUG("return: ret=%d, vaddr=0x%lx", 0, *vaddr);

	return 0;
}

static int is_remote_vm(struct process_vm *vm)
{
	int ret = 0;

	if (cpu_local_var(current)->proc->vm != vm) {
		/* vm is not mine */
		ret = 1;
	}

	return ret;
}
