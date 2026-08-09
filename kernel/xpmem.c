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

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
struct xpmem_partition *xpmem_my_part = NULL;  /* pointer to this partition */
#endif

#if defined(MCKERNEL_XPMEM_HELPERS_TEST_EXPORT)
#define XPMEM_HELPER_SCOPE
#else
#define XPMEM_HELPER_SCOPE static
#endif

#define XPMEM_LOOKUP_SKIP 0
#define XPMEM_LOOKUP_TAKE 1
#define XPMEM_LOOKUP_STOP 2

#define XPMEM_DEBUG(format, a...) dkprintf("[%d] %s: "format"\n", get_this_cpu_local_var()->current->proc->rgid, __func__, ##a)

//#define USE_DBUG_ON

#ifdef USE_DBUG_ON
#define DBUG_ON(condition) do { if (condition) kprintf("[%d] BUG: func=%s\n", get_this_cpu_local_var()->current->proc->rgid, __func__); } while (0)
#else
#define DBUG_ON(condition)
#endif

#define offset_in_page(p)	((unsigned long)(p) & ~PAGE_MASK)

static int xpmem_vm_munmap(struct process_vm *vm, void *addr, size_t len);
static int xpmem_remove_process_range(struct process_vm *vm,
		unsigned long start, unsigned long end, int *ro_freedp);
static int _xpmem_fault_process_memory_range(struct process_vm *vm,
		struct vm_range *vmr, unsigned long vaddr, uint64_t reason,
		int page_in_remote);
static int xpmem_ensure_valid_page(struct xpmem_segment *seg,
		unsigned long vaddr, int page_in);
static pte_t *xpmem_vaddr_to_pte(struct process_vm *vm,
		unsigned long vaddr, size_t *pgsize);
static void xpmem_detach_att(struct xpmem_access_permit *ap,
		struct xpmem_attachment *att);
static void xpmem_unpin_pages(struct xpmem_segment *seg,
		struct process_vm *vm, unsigned long vaddr, size_t size);
static int xpmem_check_permit_mode(int flags, struct xpmem_segment *seg);
static xpmem_apid_t xpmem_make_apid(struct xpmem_thread_group *ap_tg);
static int xpmem_make(unsigned long vaddr, size_t size, int permit_type,
		void *permit_value, xpmem_segid_t *segid);
static int xpmem_remove(xpmem_segid_t segid);
static int xpmem_get(xpmem_segid_t segid, int flags, int permit_type,
		void *permit_value, xpmem_apid_t *apid);
static int xpmem_release(xpmem_apid_t apid);
static int xpmem_attach(struct mckfd *mckfd, xpmem_apid_t apid,
		off_t offset, size_t size, unsigned long vaddr, int fd,
		int att_flags, unsigned long *at_vaddr_p);
static int xpmem_detach(unsigned long at_vaddr);
static struct xpmem_thread_group *__xpmem_tg_ref_by_tgid_nolock_internal(
		pid_t tgid, int index, int return_destroying);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
void xpmem_id_wrapper_bug_on(int condition);
void xpmem_tg_hashtable_index_log(pid_t tgid, int index);
void xpmem_ap_hashtable_index_log(xpmem_apid_t apid, int index);
void xpmem_destroyable_log(int event);
void *xpmem_refcnt_ptr_bridge(void *object, int kind);
void xpmem_refcnt_log(int kind, int refcnt);
void xpmem_tg_ref_lookup_log(int event, int tgid, int return_destroying,
		void *part, void *result);
int xpmem_atomic_inc_bridge(void *counter);
void xpmem_atomic_set_bridge(void *counter, int value);
int xpmem_atomic_read_bridge(void *counter);
void xpmem_bug_on_bridge(int condition);
void xpmem_rwlock_reader_lock_bridge(void *lock, void *node);
void xpmem_rwlock_reader_unlock_bridge(void *lock, void *node);
void xpmem_tg_ref_bridge(void *tg);
void xpmem_tg_deref_bridge(void *tg);
void xpmem_seg_deref_bridge(void *seg);
void xpmem_ap_deref_bridge(void *ap);
void xpmem_att_deref_bridge(void *att);
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
#define XPMEM_OPEN_LOG_CALL 1
#define XPMEM_OPEN_LOG_SYSCALL_ERROR 2
#define XPMEM_OPEN_LOG_OPEN_ERROR 3
#define XPMEM_OPEN_LOG_ALLOC 4
#define XPMEM_OPEN_LOG_N_OPENED 5
#define XPMEM_OPEN_LOG_RETURN 6
#define XPMEM_REMOVE_SEG_LOG_CALL 1
#define XPMEM_REMOVE_SEG_LOG_RETURN 2
#define XPMEM_REMOVE_SEGS_LOG_CALL 1
#define XPMEM_REMOVE_SEGS_LOG_RETURN 2
#define XPMEM_RELEASE_AP_LOG_CALL 1
#define XPMEM_RELEASE_AP_LOG_RETURN 2
struct xpmem_open_offsets {
	size_t proc_mckfd_lock_offset;
	size_t proc_mckfd_offset;
	size_t part_n_opened_offset;
	size_t mckfd_size;
	size_t mckfd_next_offset;
	size_t mckfd_fd_offset;
	size_t mckfd_sig_no_offset;
	size_t mckfd_data_offset;
	size_t mckfd_ioctl_cb_offset;
	size_t mckfd_close_cb_offset;
	size_t mckfd_dup_cb_offset;
};
struct xpmem_close_offsets {
	size_t part_n_opened_offset;
	size_t mckfd_fd_offset;
	size_t mckfd_data_offset;
};
struct xpmem_partition_offsets {
	size_t part_size;
	size_t part_n_opened_offset;
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
};
struct xpmem_open_tg_offsets {
	size_t proc_pid_offset;
	size_t proc_ruid_offset;
	size_t proc_rgid_offset;
	size_t tg_size;
	size_t tg_lock_offset;
	size_t tg_tgid_offset;
	size_t tg_uid_offset;
	size_t tg_gid_offset;
	size_t tg_uniq_segid_offset;
	size_t tg_uniq_apid_offset;
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
	size_t tg_n_pinned_offset;
	size_t tg_tg_hashlist_offset;
	size_t tg_group_leader_offset;
	size_t tg_vm_offset;
	size_t tg_ap_hashtable_offset;
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
};
struct xpmem_flush_offsets {
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
	size_t mckfd_data_offset;
	size_t proc_pid_offset;
	size_t tg_lock_offset;
	size_t tg_flags_offset;
	size_t tg_hashlist_offset;
	size_t tg_vm_offset;
};
struct xpmem_remove_seg_offsets {
	size_t tg_seg_list_lock_offset;
	size_t seg_lock_offset;
	size_t seg_flags_offset;
	size_t seg_list_offset;
};
struct xpmem_remove_segs_offsets {
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
	size_t seg_list_offset;
};
struct xpmem_release_ap_offsets {
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t ap_lock_offset;
	size_t ap_apid_offset;
	size_t ap_flags_offset;
	size_t ap_seg_offset;
	size_t ap_att_list_offset;
	size_t ap_ap_list_offset;
	size_t ap_hashlist_offset;
	size_t att_att_list_offset;
	size_t seg_lock_offset;
	size_t seg_tg_offset;
};
struct xpmem_release_aps_offsets {
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
	size_t ap_hashlist_offset;
};
struct xpmem_tg_lookup_offsets {
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_list_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t tg_hashlist_offset;
};
struct xpmem_seg_lookup_offsets {
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
	size_t seg_segid_offset;
	size_t seg_flags_offset;
	size_t seg_list_offset;
};
struct xpmem_ap_lookup_offsets {
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
	size_t ap_apid_offset;
	size_t ap_flags_offset;
	size_t ap_hashlist_offset;
};
struct xpmem_deref_offsets {
	size_t refcnt_offset;
	size_t flags_offset;
};
struct xpmem_make_id_offsets {
	size_t tg_tgid_offset;
	size_t tg_uniq_offset;
};
struct xpmem_validate_access_offsets {
	size_t proc_pid_offset;
	size_t proc_vm_offset;
	size_t ap_mode_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
	size_t seg_vaddr_offset;
	size_t seg_size_offset;
};
struct xpmem_perm_offsets {
	size_t proc_ruid_offset;
	size_t proc_rgid_offset;
	size_t perm_uid_offset;
	size_t perm_gid_offset;
	size_t perm_mode_offset;
	size_t seg_permit_type_offset;
	size_t seg_permit_value_offset;
	size_t seg_tg_offset;
	size_t tg_uid_offset;
	size_t tg_gid_offset;
};
struct xpmem_make_segment_offsets {
	size_t proc_pid_offset;
	size_t seg_size;
	size_t seg_lock_offset;
	size_t seg_segid_offset;
	size_t seg_vaddr_offset;
	size_t seg_size_offset;
	size_t seg_permit_type_offset;
	size_t seg_permit_value_offset;
	size_t seg_tg_offset;
	size_t seg_ap_list_offset;
	size_t seg_seg_list_offset;
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
};
struct xpmem_get_offsets {
	size_t proc_pid_offset;
	size_t ap_size;
	size_t ap_lock_offset;
	size_t ap_apid_offset;
	size_t ap_mode_offset;
	size_t ap_seg_offset;
	size_t ap_tg_offset;
	size_t ap_att_list_offset;
	size_t ap_ap_list_offset;
	size_t ap_hashlist_offset;
	size_t seg_lock_offset;
	size_t seg_ap_list_offset;
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
};
struct xpmem_tg_id_offsets {
	size_t tg_tgid_offset;
};
struct xpmem_detach_offsets {
	size_t vm_memory_range_lock_offset;
	size_t range_start_offset;
	size_t range_private_data_offset;
	size_t att_at_lock_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
	size_t ap_lock_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
};
struct xpmem_detach_att_offsets {
	size_t vm_memory_range_lock_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_private_data_offset;
	size_t att_at_lock_offset;
	size_t att_vaddr_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
	size_t ap_lock_offset;
	size_t ap_seg_offset;
};
struct xpmem_clear_ptes_offsets {
	size_t seg_lock_offset;
	size_t seg_vaddr_offset;
	size_t seg_size_offset;
	size_t seg_ap_list_offset;
	size_t ap_lock_offset;
	size_t ap_seg_offset;
	size_t ap_att_list_offset;
	size_t ap_ap_list_offset;
	size_t att_at_lock_offset;
	size_t att_vaddr_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
	size_t vm_memory_range_lock_offset;
};
struct xpmem_remove_process_memory_range_offsets {
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_private_data_offset;
	size_t att_at_lock_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_att_list_offset;
	size_t ap_lock_offset;
};
struct xpmem_remove_process_range_offsets {
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_flag_offset;
	size_t range_private_data_offset;
};
struct xpmem_free_process_range_offsets {
	size_t vm_address_space_offset;
	size_t vm_page_table_lock_offset;
	size_t vm_range_tree_offset;
	size_t vm_range_cache_offset;
	size_t vm_range_cache_count;
	size_t address_space_page_table_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_memobj_offset;
	size_t range_rb_node_offset;
};
struct xpmem_update_page_table_offsets {
	size_t vm_address_space_offset;
	size_t address_space_page_table_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_pgshift_offset;
	size_t range_private_data_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_vmr_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t ap_flags_offset;
	size_t ap_mode_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t seg_flags_offset;
	size_t seg_tg_offset;
};
struct xpmem_fault_process_range_offsets {
	size_t vm_address_space_offset;
	size_t vm_proc_offset;
	size_t vm_memory_range_lock_offset;
	size_t address_space_page_table_offset;
	size_t proc_straight_va_offset;
	size_t proc_straight_len_offset;
	size_t proc_straight_pa_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_flag_offset;
	size_t range_pgshift_offset;
	size_t range_private_data_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_vaddr_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t ap_flags_offset;
	size_t ap_mode_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t tg_vm_offset;
	size_t tg_n_pinned_offset;
	size_t seg_flags_offset;
	size_t seg_tg_offset;
};
struct xpmem_attach_offsets {
	size_t mckfd_fd_offset;
	size_t vm_memory_range_lock_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_private_data_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t ap_lock_offset;
	size_t ap_flags_offset;
	size_t ap_seg_offset;
	size_t ap_att_list_offset;
	size_t seg_flags_offset;
	size_t seg_tg_offset;
	size_t att_size;
	size_t att_at_lock_offset;
	size_t att_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
};
struct xpmem_ioctl_offsets {
	unsigned long cmd_version;
	unsigned long cmd_make;
	unsigned long cmd_remove;
	unsigned long cmd_get;
	unsigned long cmd_release;
	unsigned long cmd_attach;
	unsigned long cmd_detach;
	int current_version;
	size_t make_size;
	size_t make_vaddr_offset;
	size_t make_size_offset;
	size_t make_permit_type_offset;
	size_t make_permit_value_offset;
	size_t make_segid_offset;
	size_t remove_size;
	size_t remove_segid_offset;
	size_t get_size;
	size_t get_segid_offset;
	size_t get_flags_offset;
	size_t get_permit_type_offset;
	size_t get_permit_value_offset;
	size_t get_apid_offset;
	size_t release_size;
	size_t release_apid_offset;
	size_t attach_size;
	size_t attach_apid_offset;
	size_t attach_offset_offset;
	size_t attach_size_offset;
	size_t attach_vaddr_offset;
	size_t attach_fd_offset;
	size_t attach_flags_offset;
	size_t detach_size;
	size_t detach_vaddr_offset;
};
struct xpmem_pin_page_offsets {
	size_t tg_n_pinned_offset;
	size_t vm_memory_range_lock_offset;
	size_t vm_stack_start_offset;
	size_t vm_stack_end_offset;
	size_t range_start_offset;
	size_t range_private_data_offset;
};
struct xpmem_ensure_valid_page_offsets {
	size_t seg_flags_offset;
	size_t seg_tg_offset;
	size_t tg_group_leader_offset;
	size_t tg_vm_offset;
};
struct xpmem_vaddr_to_pte_offsets {
	size_t vm_address_space_offset;
	size_t address_space_page_table_offset;
	size_t range_pgshift_offset;
};
struct xpmem_unpin_pages_offsets {
	size_t seg_tg_offset;
	size_t tg_n_pinned_offset;
};
typedef int (*xpmem_init_fn_t)(void);
typedef long (*xpmem_forward_fn_t)(int syscall_num, void *ctx);
typedef int (*xpmem_open_fn_t)(void);
typedef void *(*xpmem_alloc_fn_t)(size_t size);
typedef long (*xpmem_lock_fn_t)(void *lock);
typedef void (*xpmem_unlock_fn_t)(void *lock, long irqstate);
typedef int (*xpmem_atomic_inc_fn_t)(void *counter);
typedef void (*xpmem_atomic_set_fn_t)(void *counter, int value);
typedef int (*xpmem_atomic_read_fn_t)(void *counter);
typedef int (*xpmem_atomic_dec_fn_t)(void *counter);
typedef void (*xpmem_bug_on_fn_t)(int condition);
typedef void (*xpmem_void_fn_t)(void);
typedef void (*xpmem_mckfd_void_fn_t)(void *mckfd);
typedef void (*xpmem_open_log_fn_t)(int event, int syscall_num,
		const char *pathname, int flags, long value, void *ptr);
typedef void (*xpmem_close_log_fn_t)(int event, void *mckfd, int value);
typedef void *(*xpmem_tg_ref_fn_t)(int pid);
typedef void (*xpmem_rwlock_fn_t)(void *lock, void *node);
typedef void (*xpmem_list_fn_t)(void *entry);
typedef void (*xpmem_spin_fn_t)(void *lock);
typedef void (*xpmem_tg_void_fn_t)(void *tg);
typedef void (*xpmem_flush_log_fn_t)(int event, void *tg, long value);
typedef void (*xpmem_ptr_void_fn_t)(void *ptr);
typedef long (*xpmem_object_id_fn_t)(void *ptr);
typedef void (*xpmem_list_add_tail_fn_t)(void *entry, void *head);
typedef void (*xpmem_remove_seg_log_fn_t)(int event, void *tg, void *seg,
		long value);
typedef void (*xpmem_remove_seg_fn_t)(void *tg, void *seg);
typedef void (*xpmem_remove_segs_log_fn_t)(int event, void *tg, void *seg,
		long value);
typedef void (*xpmem_detach_att_fn_t)(void *ap, void *att);
typedef void (*xpmem_release_ap_log_fn_t)(int event, void *tg, void *ap,
		long value);
typedef void *(*xpmem_id_ref_fn_t)(long id);
typedef void *(*xpmem_ref_by_id_fn_t)(void *parent, long id);
typedef void (*xpmem_rwspin_noirq_fn_t)(void *lock);
typedef unsigned long (*xpmem_rwspin_lock_fn_t)(void *lock);
typedef void (*xpmem_rwspin_unlock_fn_t)(void *lock,
		unsigned long state);
typedef void *(*xpmem_lookup_range_fn_t)(void *vm, unsigned long start,
		unsigned long end);
typedef void *(*xpmem_next_range_fn_t)(void *vm, void *range);
typedef int (*xpmem_split_range_fn_t)(void *vm, void *range,
		unsigned long addr, void **newrangep);
typedef int (*xpmem_range_action_fn_t)(void *vm, void *range);
typedef void (*xpmem_remove_process_range_log_fn_t)(void *vm,
		unsigned long start, unsigned long end, int error,
		int free_error);
typedef int (*xpmem_pt_clear_range_fn_t)(void *page_table, void *vm,
		unsigned long start, unsigned long end);
typedef void (*xpmem_range_erase_fn_t)(void *root, void *node);
typedef void (*xpmem_free_process_range_log_fn_t)(int event, void *vm,
		void *range, unsigned long start, unsigned long end, int error);
typedef int (*xpmem_fault_range_page_in_fn_t)(void *vm, void *range,
		unsigned long vaddr, unsigned long reason, int page_in_remote);
typedef void (*xpmem_update_page_table_log_fn_t)(int event, void *vm,
		void *range, unsigned long vaddr, int error);
typedef int (*xpmem_validate_access_fn_t)(void *ap, off_t offset,
		size_t size, int mode, unsigned long *vaddrp);
typedef unsigned long (*xpmem_mmap_fn_t)(unsigned long addr, size_t len,
		unsigned long prot, unsigned long flags, int fd, off_t offset,
		unsigned long vm_flags, void *private_data);
typedef int (*xpmem_copy_from_user_fn_t)(void *dst, unsigned long src,
		size_t size);
typedef int (*xpmem_copy_to_user_fn_t)(unsigned long dst, const void *src,
		size_t size);
typedef int (*xpmem_make_fn_t)(unsigned long vaddr, size_t size,
		int permit_type, void *permit_value, long *segidp);
typedef int (*xpmem_remove_fn_t)(long segid);
typedef int (*xpmem_get_fn_t)(long segid, int flags, int permit_type,
		void *permit_value, long *apidp);
typedef int (*xpmem_release_fn_t)(long apid);
typedef int (*xpmem_attach_fn_t)(void *mckfd, long apid, off_t offset,
		size_t size, unsigned long vaddr, int fd, int flags,
		unsigned long *at_vaddrp);
typedef int (*xpmem_detach_fn_t)(unsigned long vaddr);
typedef void (*xpmem_unpin_pages_fn_t)(void *seg, void *vm,
		unsigned long vaddr, size_t size);
typedef int (*xpmem_munmap_fn_t)(void *vm, unsigned long addr, size_t len);
typedef int (*xpmem_remove_range_fn_t)(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp);
typedef void (*xpmem_clear_range_fn_t)(void *object, unsigned long start,
		unsigned long end);
typedef int (*xpmem_check_permit_fn_t)(int flags, void *seg);
typedef int (*xpmem_page_fault_vm_fn_t)(void *vm, unsigned long vaddr,
		unsigned long reason);
typedef int (*xpmem_page_fault_range_fn_t)(void *vm, void *range,
		unsigned long vaddr, unsigned long reason);
typedef int (*xpmem_pin_page_fn_t)(void *tg, void *thread, void *vm,
		unsigned long vaddr, int page_in);
typedef int (*xpmem_ensure_valid_fn_t)(void *seg, unsigned long vaddr,
		int page_in);
typedef void *(*xpmem_pt_lookup_pte_fn_t)(void *page_table,
		unsigned long vaddr, int pgshift, void **base, size_t *pgsize,
		int *p2align);
typedef void *(*xpmem_vaddr_to_pte_fn_t)(void *vm, unsigned long vaddr,
		size_t *pgsize);
typedef int (*xpmem_pte_present_fn_t)(void *pte);
typedef void (*xpmem_atomic_sub_fn_t)(int value, void *counter);
typedef void *(*xpmem_pt_lookup_pte_fn_t)(void *page_table,
		unsigned long vaddr, int pgshift, void **base, size_t *pgsize,
		int *p2align);
typedef void *(*xpmem_vaddr_to_pte_fn_t)(void *vm, unsigned long vaddr,
		size_t *pgsize);
typedef int (*xpmem_pte_present_fn_t)(void *pte);
typedef void (*xpmem_atomic_sub_fn_t)(int value, void *counter);
typedef unsigned long (*xpmem_pte_phys_fn_t)(void *pte);
typedef int (*xpmem_get_smaller_page_size_fn_t)(size_t pgsize,
		size_t *new_pgsize, int *p2align);
typedef void (*xpmem_adjust_page_size_fn_t)(void *page_table,
		unsigned long fault_addr, void *pte, void **pgaddr,
		size_t *pgsize);
typedef unsigned long (*xpmem_vrflag_to_ptattr_fn_t)(unsigned long flag,
		unsigned long reason);
typedef int (*xpmem_pgsize_contiguous_fn_t)(size_t pgsize);
typedef int (*xpmem_pt_set_pte_fn_t)(void *page_table, void *pte,
		size_t pgsize, unsigned long phys, unsigned long attr);
typedef int (*xpmem_pt_set_range_fn_t)(void *page_table, void *vm,
		unsigned long start, unsigned long end, unsigned long phys,
		unsigned long attr, int pgshift, void *vmr, int replace);
typedef void (*xpmem_flush_tlb_single_fn_t)(unsigned long vaddr);
typedef void (*xpmem_fault_log_fn_t)(int event, unsigned long a,
		unsigned long b, unsigned long c, size_t size, int error);
struct xpmem_fault_process_range_ops {
	xpmem_ptr_void_fn_t att_ref_fn;
	xpmem_ptr_void_fn_t att_deref_fn;
	xpmem_ptr_void_fn_t ap_ref_fn;
	xpmem_ptr_void_fn_t ap_deref_fn;
	xpmem_ptr_void_fn_t tg_ref_fn;
	xpmem_ptr_void_fn_t tg_deref_fn;
	xpmem_ptr_void_fn_t seg_ref_fn;
	xpmem_ptr_void_fn_t seg_deref_fn;
	xpmem_bug_on_fn_t bug_on_fn;
	xpmem_ensure_valid_fn_t ensure_valid_fn;
	xpmem_rwspin_noirq_fn_t read_lock_noirq_fn;
	xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn;
	xpmem_vaddr_to_pte_fn_t vaddr_to_pte_fn;
	xpmem_pte_present_fn_t pte_present_fn;
	xpmem_pte_phys_fn_t pte_phys_fn;
	xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn;
	xpmem_get_smaller_page_size_fn_t smaller_page_fn;
	xpmem_adjust_page_size_fn_t adjust_page_fn;
	xpmem_vrflag_to_ptattr_fn_t vrflag_to_ptattr_fn;
	xpmem_pgsize_contiguous_fn_t pgsize_contiguous_fn;
	xpmem_pt_set_pte_fn_t pt_set_pte_fn;
	xpmem_pt_set_range_fn_t pt_set_range_fn;
	xpmem_atomic_dec_fn_t atomic_dec_fn;
	xpmem_flush_tlb_single_fn_t flush_tlb_single_fn;
	xpmem_fault_log_fn_t log_fn;
};
extern int xpmem_open_body_result(int syscall_num, const char *pathname,
		int flags, void *ctx, void **partp, void *proc,
		const struct xpmem_open_offsets *offsets,
		unsigned long ioctl_cb_addr, unsigned long close_cb_addr,
		unsigned long dup_cb_addr, xpmem_init_fn_t init_fn,
		xpmem_forward_fn_t forward_fn, xpmem_open_fn_t open_fn,
		xpmem_alloc_fn_t alloc_fn, xpmem_lock_fn_t lock_fn,
		xpmem_unlock_fn_t unlock_fn,
		xpmem_atomic_inc_fn_t atomic_inc_fn,
		xpmem_open_log_fn_t log_fn);
extern int xpmem_ioctl_body_result(void *mckfd, unsigned long cmd,
		unsigned long arg, const struct xpmem_ioctl_offsets *offsets,
		xpmem_copy_from_user_fn_t copy_from_user_fn,
		xpmem_copy_to_user_fn_t copy_to_user_fn,
		xpmem_make_fn_t make_fn,
		xpmem_remove_fn_t remove_fn,
		xpmem_get_fn_t get_fn,
		xpmem_release_fn_t release_fn,
		xpmem_attach_fn_t attach_fn,
		xpmem_detach_fn_t detach_fn);
extern int xpmem_dup_body_result(void *mckfd, void **partp,
		const struct xpmem_close_offsets *offsets,
		xpmem_atomic_inc_fn_t atomic_inc_fn);
extern int xpmem_close_body_result(void *mckfd, void **partp,
		const struct xpmem_close_offsets *offsets,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_mckfd_void_fn_t flush_fn, xpmem_void_fn_t exit_fn,
		xpmem_close_log_fn_t log_fn);
extern int xpmem_partition_init_body_result(void **partp,
		const struct xpmem_partition_offsets *offsets,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t rwlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_atomic_set_fn_t atomic_set_fn);
extern int xpmem_partition_exit_body_result(void **partp,
		xpmem_ptr_void_fn_t free_fn);
extern int xpmem_open_tg_body_result(void **partp, void *current_thread,
		void *current_proc, void *current_vm,
		const struct xpmem_open_tg_offsets *offsets,
		void *rwlock_node, xpmem_tg_ref_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t spinlock_init_fn,
		xpmem_ptr_void_fn_t rwlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_atomic_set_fn_t atomic_set_fn,
		xpmem_ptr_void_fn_t tg_not_destroyable_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn);
extern int xpmem_flush_body_result(void *mckfd, void **partp,
		const struct xpmem_flush_offsets *offsets, void *rwlock_node,
		xpmem_tg_ref_fn_t tg_ref_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_tg_void_fn_t release_aps_fn,
		xpmem_tg_void_fn_t remove_segs_fn,
		xpmem_tg_void_fn_t destroy_tg_fn,
		xpmem_flush_log_fn_t log_fn);
extern int xpmem_remove_seg_body_result(void *seg_tg, void *seg,
		const struct xpmem_remove_seg_offsets *offsets,
		void *rwlock_node, xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_ptr_void_fn_t clear_ptes_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t seg_destroyable_fn,
		xpmem_remove_seg_log_fn_t log_fn);
extern int xpmem_remove_segs_of_tg_body_result(void *seg_tg,
		const struct xpmem_remove_segs_offsets *offsets,
		void *rwlock_node,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_remove_seg_fn_t remove_seg_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_remove_segs_log_fn_t log_fn);
extern int xpmem_release_ap_body_result(void *ap_tg, void *ap,
		const struct xpmem_release_ap_offsets *offsets,
		void *rwlock_node,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_detach_att_fn_t detach_att_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t ap_destroyable_fn,
		xpmem_release_ap_log_fn_t log_fn);
extern int xpmem_release_aps_of_tg_body_result(void *ap_tg,
		const struct xpmem_release_aps_offsets *offsets,
		void *rwlock_node,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_remove_seg_fn_t release_ap_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_remove_segs_log_fn_t log_fn);
extern int xpmem_destroy_tg_body_result(void *tg,
		xpmem_ptr_void_fn_t tg_destroyable_fn,
		xpmem_ptr_void_fn_t tg_deref_fn);
extern int xpmem_remove_body_result(long segid, int current_pid,
		const struct xpmem_tg_id_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_segid_fn,
		xpmem_ref_by_id_fn_t seg_ref_by_segid_fn,
		xpmem_remove_seg_fn_t remove_seg_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn);
extern int xpmem_release_body_result(long apid, int current_pid,
		const struct xpmem_tg_id_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_apid_fn,
		xpmem_ref_by_id_fn_t ap_ref_by_apid_fn,
		xpmem_remove_seg_fn_t release_ap_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn);
extern int xpmem_attach_body_result(void *mckfd, long apid, off_t offset,
		size_t size, unsigned long vaddr, unsigned long *at_vaddrp,
		int current_pid, void *current_vm, int fjmpi_workaround,
		unsigned long prot_flags, unsigned long map_shared,
		unsigned long map_fixed, unsigned long map_anonymous,
		unsigned long vr_xpmem,
		const struct xpmem_attach_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_apid_fn,
		xpmem_ref_by_id_fn_t ap_ref_by_apid_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_validate_access_fn_t validate_access_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t rwspin_init_fn,
		xpmem_list_fn_t list_init_fn,
		xpmem_ptr_void_fn_t att_not_destroyable_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_next_range_fn_t next_range_fn,
		xpmem_mmap_fn_t mmap_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn);
extern int xpmem_vm_munmap_body_result(void *vm, unsigned long addr,
		size_t len, xpmem_void_fn_t begin_fn,
		xpmem_remove_range_fn_t remove_range_fn,
		xpmem_void_fn_t finish_fn);
extern int xpmem_detach_body_result(unsigned long at_vaddr,
		int current_pid, void *vm,
		const struct xpmem_detach_offsets *offsets,
		xpmem_rwspin_noirq_fn_t write_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t write_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_unpin_pages_fn_t unpin_pages_fn,
		xpmem_munmap_fn_t munmap_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn);
extern int xpmem_detach_att_body_result(void *ap, void *att,
		const struct xpmem_detach_att_offsets *offsets,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_unpin_pages_fn_t unpin_pages_fn,
		xpmem_munmap_fn_t munmap_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn);
extern int xpmem_clear_ptes_body_result(void *seg,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_clear_range_fn_t clear_range_fn);
extern int xpmem_clear_ptes_range_body_result(void *seg,
		unsigned long start, unsigned long end,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_clear_range_fn_t clear_ap_fn,
		xpmem_ptr_void_fn_t ap_deref_fn);
extern int xpmem_clear_ptes_of_ap_body_result(void *ap,
		unsigned long start, unsigned long end,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_clear_range_fn_t clear_att_fn,
		xpmem_ptr_void_fn_t att_deref_fn);
extern int xpmem_clear_ptes_of_att_body_result(void *att,
		unsigned long start, unsigned long end,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_unpin_pages_fn_t unpin_pages_fn,
		xpmem_munmap_fn_t munmap_fn);
extern int xpmem_remove_process_memory_range_body_result(void *vm, void *vmr,
		const struct xpmem_remove_process_memory_range_offsets *offsets,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn);
extern int xpmem_remove_process_range_body_result(void *vm,
		unsigned long start, unsigned long end, int *ro_freedp,
		const struct xpmem_remove_process_range_offsets *offsets,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_next_range_fn_t next_range_fn,
		xpmem_split_range_fn_t split_range_fn,
		xpmem_range_action_fn_t remove_private_fn,
		xpmem_range_action_fn_t free_range_fn,
		xpmem_remove_process_range_log_fn_t log_fn);
extern int xpmem_free_process_range_body_result(void *vm, void *range,
		const struct xpmem_free_process_range_offsets *offsets,
		xpmem_spin_fn_t lock_fn,
		xpmem_spin_fn_t unlock_fn,
		xpmem_pt_clear_range_fn_t pt_clear_fn,
		xpmem_ptr_void_fn_t memobj_unref_fn,
		xpmem_range_erase_fn_t erase_fn,
		xpmem_ptr_void_fn_t free_fn,
		xpmem_free_process_range_log_fn_t log_fn);
extern int xpmem_update_process_page_table_body_result(void *vm, void *vmr,
		int current_pid, int page_in_remote_on_attach,
		const struct xpmem_update_page_table_offsets *offsets,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_bug_on_fn_t bug_on_fn,
		xpmem_fault_range_page_in_fn_t fault_fn,
		xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn,
		xpmem_pte_present_fn_t pte_present_fn,
		xpmem_update_page_table_log_fn_t log_fn);
extern int xpmem_fault_process_memory_range_body_result(void *vm, void *vmr,
		unsigned long vaddr, unsigned long reason, int page_in_remote,
		int current_pid, void *current_vm,
		const struct xpmem_fault_process_range_offsets *offsets,
		const struct xpmem_fault_process_range_ops *ops);
extern int xpmem_pin_page_body_result(void *tg, void *src_thread,
		void *src_vm, void *current_vm, unsigned long vaddr,
		int page_in, const struct xpmem_pin_page_offsets *offsets,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_page_fault_vm_fn_t page_fault_vm_fn,
		xpmem_page_fault_range_fn_t page_fault_range_fn,
		xpmem_atomic_inc_fn_t atomic_inc_fn);
extern int xpmem_ensure_valid_page_body_result(void *seg,
		unsigned long vaddr, int page_in,
		const struct xpmem_ensure_valid_page_offsets *offsets,
		xpmem_pin_page_fn_t pin_page_fn);
extern void *xpmem_vaddr_to_pte_body_result(void *vm, unsigned long vaddr,
		size_t *pgsize, const struct xpmem_vaddr_to_pte_offsets *offsets,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn);
extern int xpmem_unpin_pages_body_result(void *seg, void *vm,
		unsigned long vaddr, size_t size,
		const struct xpmem_unpin_pages_offsets *offsets,
		xpmem_vaddr_to_pte_fn_t vaddr_to_pte_fn,
		xpmem_pte_present_fn_t pte_present_fn,
		xpmem_atomic_sub_fn_t atomic_sub_fn);
extern void *xpmem_tg_ref_by_tgid_nolock_body_result(void *part, int tgid,
		int index, int return_destroying,
		const struct xpmem_tg_lookup_offsets *offsets,
		xpmem_ptr_void_fn_t tg_ref_fn);
extern void *xpmem_seg_ref_by_segid_body_result(void *seg_tg, long segid,
		const struct xpmem_seg_lookup_offsets *offsets,
		void *rwlock_node, xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t seg_ref_fn);
extern void *xpmem_ap_ref_by_apid_body_result(void *ap_tg, long apid,
		const struct xpmem_ap_lookup_offsets *offsets,
		void *rwlock_node, xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn);
extern int xpmem_deref_body_result(void *object,
		const struct xpmem_deref_offsets *offsets,
		int require_destroying,
		xpmem_atomic_read_fn_t atomic_read_fn,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_bug_on_fn_t bug_on_fn,
		xpmem_ptr_void_fn_t free_log_fn,
		xpmem_ptr_void_fn_t free_fn);
extern long xpmem_make_object_id_body_result(void *tg,
		const struct xpmem_make_id_offsets *offsets,
		xpmem_atomic_inc_fn_t atomic_inc_fn,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_bug_on_fn_t bug_on_fn);
extern int xpmem_validate_access_body_result(void *ap, void *current_proc,
		off_t offset, size_t size, int mode, unsigned long *vaddr,
		const struct xpmem_validate_access_offsets *offsets);
extern int xpmem_is_remote_vm_body_result(void *current_proc, void *vm,
		const struct xpmem_validate_access_offsets *offsets);
extern int xpmem_perms_body_result(void *perm, int flag, void *current_proc,
		const struct xpmem_perm_offsets *offsets);
extern int xpmem_check_permit_mode_body_result(int flags, void *seg,
		void *current_proc, const struct xpmem_perm_offsets *offsets,
		xpmem_bug_on_fn_t bug_on_fn);
extern int xpmem_make_segment_body_result(unsigned long vaddr, size_t size,
		int permit_type, void *permit_value, long *segid,
		void *current_proc, const struct xpmem_make_segment_offsets *offsets,
		void *rwlock_node, xpmem_tg_ref_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_object_id_fn_t make_segid_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t spinlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_ptr_void_fn_t seg_not_destroyable_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_bug_on_fn_t bug_on_fn);
extern int xpmem_get_body_result(long segid, int flags, int permit_type,
		void *permit_value, long *apid, void *current_proc,
		const struct xpmem_get_offsets *offsets, void *rwlock_node,
		xpmem_id_ref_fn_t tg_ref_by_segid_fn,
		xpmem_ref_by_id_fn_t seg_ref_by_segid_fn,
		xpmem_check_permit_fn_t check_permit_fn,
		xpmem_tg_ref_fn_t tg_ref_by_tgid_fn,
		xpmem_object_id_fn_t make_apid_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t spinlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_ptr_void_fn_t ap_not_destroyable_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_bug_on_fn_t bug_on_fn);
#else
#define XPMEM_OPEN_LOG_CALL 1
#define XPMEM_OPEN_LOG_SYSCALL_ERROR 2
#define XPMEM_OPEN_LOG_OPEN_ERROR 3
#define XPMEM_OPEN_LOG_ALLOC 4
#define XPMEM_OPEN_LOG_N_OPENED 5
#define XPMEM_OPEN_LOG_RETURN 6
#define XPMEM_REMOVE_SEG_LOG_CALL 1
#define XPMEM_REMOVE_SEG_LOG_RETURN 2
#define XPMEM_REMOVE_SEGS_LOG_CALL 1
#define XPMEM_REMOVE_SEGS_LOG_RETURN 2
#define XPMEM_RELEASE_AP_LOG_CALL 1
#define XPMEM_RELEASE_AP_LOG_RETURN 2
struct xpmem_open_offsets {
	size_t proc_mckfd_lock_offset;
	size_t proc_mckfd_offset;
	size_t part_n_opened_offset;
	size_t mckfd_size;
	size_t mckfd_next_offset;
	size_t mckfd_fd_offset;
	size_t mckfd_sig_no_offset;
	size_t mckfd_data_offset;
	size_t mckfd_ioctl_cb_offset;
	size_t mckfd_close_cb_offset;
	size_t mckfd_dup_cb_offset;
};
struct xpmem_close_offsets {
	size_t part_n_opened_offset;
	size_t mckfd_fd_offset;
	size_t mckfd_data_offset;
};
struct xpmem_partition_offsets {
	size_t part_size;
	size_t part_n_opened_offset;
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
};
struct xpmem_open_tg_offsets {
	size_t proc_pid_offset;
	size_t proc_ruid_offset;
	size_t proc_rgid_offset;
	size_t tg_size;
	size_t tg_lock_offset;
	size_t tg_tgid_offset;
	size_t tg_uid_offset;
	size_t tg_gid_offset;
	size_t tg_uniq_segid_offset;
	size_t tg_uniq_apid_offset;
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
	size_t tg_n_pinned_offset;
	size_t tg_tg_hashlist_offset;
	size_t tg_group_leader_offset;
	size_t tg_vm_offset;
	size_t tg_ap_hashtable_offset;
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
};
struct xpmem_flush_offsets {
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
	size_t mckfd_data_offset;
	size_t proc_pid_offset;
	size_t tg_lock_offset;
	size_t tg_flags_offset;
	size_t tg_hashlist_offset;
	size_t tg_vm_offset;
};
struct xpmem_remove_seg_offsets {
	size_t tg_seg_list_lock_offset;
	size_t seg_lock_offset;
	size_t seg_flags_offset;
	size_t seg_list_offset;
};
struct xpmem_remove_segs_offsets {
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
	size_t seg_list_offset;
};
struct xpmem_release_ap_offsets {
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t ap_lock_offset;
	size_t ap_apid_offset;
	size_t ap_flags_offset;
	size_t ap_seg_offset;
	size_t ap_att_list_offset;
	size_t ap_ap_list_offset;
	size_t ap_hashlist_offset;
	size_t att_att_list_offset;
	size_t seg_lock_offset;
	size_t seg_tg_offset;
};
struct xpmem_release_aps_offsets {
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
	size_t ap_hashlist_offset;
};
struct xpmem_tg_lookup_offsets {
	size_t part_tg_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_list_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t tg_hashlist_offset;
};
struct xpmem_seg_lookup_offsets {
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
	size_t seg_segid_offset;
	size_t seg_flags_offset;
	size_t seg_list_offset;
};
struct xpmem_ap_lookup_offsets {
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
	size_t ap_apid_offset;
	size_t ap_flags_offset;
	size_t ap_hashlist_offset;
};
struct xpmem_deref_offsets {
	size_t refcnt_offset;
	size_t flags_offset;
};
struct xpmem_make_id_offsets {
	size_t tg_tgid_offset;
	size_t tg_uniq_offset;
};
struct xpmem_validate_access_offsets {
	size_t proc_pid_offset;
	size_t proc_vm_offset;
	size_t ap_mode_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
	size_t seg_vaddr_offset;
	size_t seg_size_offset;
};
struct xpmem_perm_offsets {
	size_t proc_ruid_offset;
	size_t proc_rgid_offset;
	size_t perm_uid_offset;
	size_t perm_gid_offset;
	size_t perm_mode_offset;
	size_t seg_permit_type_offset;
	size_t seg_permit_value_offset;
	size_t seg_tg_offset;
	size_t tg_uid_offset;
	size_t tg_gid_offset;
};
struct xpmem_make_segment_offsets {
	size_t proc_pid_offset;
	size_t seg_size;
	size_t seg_lock_offset;
	size_t seg_segid_offset;
	size_t seg_vaddr_offset;
	size_t seg_size_offset;
	size_t seg_permit_type_offset;
	size_t seg_permit_value_offset;
	size_t seg_tg_offset;
	size_t seg_ap_list_offset;
	size_t seg_seg_list_offset;
	size_t tg_seg_list_lock_offset;
	size_t tg_seg_list_offset;
};
struct xpmem_get_offsets {
	size_t proc_pid_offset;
	size_t ap_size;
	size_t ap_lock_offset;
	size_t ap_apid_offset;
	size_t ap_mode_offset;
	size_t ap_seg_offset;
	size_t ap_tg_offset;
	size_t ap_att_list_offset;
	size_t ap_ap_list_offset;
	size_t ap_hashlist_offset;
	size_t seg_lock_offset;
	size_t seg_ap_list_offset;
	size_t tg_ap_hashtable_offset;
	size_t hashlist_stride;
	size_t hashlist_lock_offset;
	size_t hashlist_list_offset;
};
struct xpmem_tg_id_offsets {
	size_t tg_tgid_offset;
};
struct xpmem_detach_offsets {
	size_t vm_memory_range_lock_offset;
	size_t range_start_offset;
	size_t range_private_data_offset;
	size_t att_at_lock_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
	size_t ap_lock_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
};
struct xpmem_detach_att_offsets {
	size_t vm_memory_range_lock_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_private_data_offset;
	size_t att_at_lock_offset;
	size_t att_vaddr_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
	size_t ap_lock_offset;
	size_t ap_seg_offset;
};
struct xpmem_clear_ptes_offsets {
	size_t seg_lock_offset;
	size_t seg_vaddr_offset;
	size_t seg_size_offset;
	size_t seg_ap_list_offset;
	size_t ap_lock_offset;
	size_t ap_seg_offset;
	size_t ap_att_list_offset;
	size_t ap_ap_list_offset;
	size_t att_at_lock_offset;
	size_t att_vaddr_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
	size_t vm_memory_range_lock_offset;
};
struct xpmem_remove_process_memory_range_offsets {
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_private_data_offset;
	size_t att_at_lock_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_att_list_offset;
	size_t ap_lock_offset;
};
struct xpmem_remove_process_range_offsets {
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_flag_offset;
	size_t range_private_data_offset;
};
struct xpmem_free_process_range_offsets {
	size_t vm_address_space_offset;
	size_t vm_page_table_lock_offset;
	size_t vm_range_tree_offset;
	size_t vm_range_cache_offset;
	size_t vm_range_cache_count;
	size_t address_space_page_table_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_memobj_offset;
	size_t range_rb_node_offset;
};
struct xpmem_update_page_table_offsets {
	size_t vm_address_space_offset;
	size_t address_space_page_table_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_pgshift_offset;
	size_t range_private_data_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_vmr_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t ap_flags_offset;
	size_t ap_mode_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t seg_flags_offset;
	size_t seg_tg_offset;
};
struct xpmem_fault_process_range_offsets {
	size_t vm_address_space_offset;
	size_t vm_proc_offset;
	size_t vm_memory_range_lock_offset;
	size_t address_space_page_table_offset;
	size_t proc_straight_va_offset;
	size_t proc_straight_len_offset;
	size_t proc_straight_pa_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_flag_offset;
	size_t range_pgshift_offset;
	size_t range_private_data_offset;
	size_t att_at_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_vaddr_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t ap_flags_offset;
	size_t ap_mode_offset;
	size_t ap_tg_offset;
	size_t ap_seg_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t tg_vm_offset;
	size_t tg_n_pinned_offset;
	size_t seg_flags_offset;
	size_t seg_tg_offset;
};
struct xpmem_attach_offsets {
	size_t mckfd_fd_offset;
	size_t vm_memory_range_lock_offset;
	size_t range_start_offset;
	size_t range_end_offset;
	size_t range_private_data_offset;
	size_t tg_tgid_offset;
	size_t tg_flags_offset;
	size_t ap_lock_offset;
	size_t ap_flags_offset;
	size_t ap_seg_offset;
	size_t ap_att_list_offset;
	size_t seg_flags_offset;
	size_t seg_tg_offset;
	size_t att_size;
	size_t att_at_lock_offset;
	size_t att_vaddr_offset;
	size_t att_at_size_offset;
	size_t att_flags_offset;
	size_t att_ap_offset;
	size_t att_vm_offset;
	size_t att_att_list_offset;
};
struct xpmem_ioctl_offsets {
	unsigned long cmd_version;
	unsigned long cmd_make;
	unsigned long cmd_remove;
	unsigned long cmd_get;
	unsigned long cmd_release;
	unsigned long cmd_attach;
	unsigned long cmd_detach;
	int current_version;
	size_t make_size;
	size_t make_vaddr_offset;
	size_t make_size_offset;
	size_t make_permit_type_offset;
	size_t make_permit_value_offset;
	size_t make_segid_offset;
	size_t remove_size;
	size_t remove_segid_offset;
	size_t get_size;
	size_t get_segid_offset;
	size_t get_flags_offset;
	size_t get_permit_type_offset;
	size_t get_permit_value_offset;
	size_t get_apid_offset;
	size_t release_size;
	size_t release_apid_offset;
	size_t attach_size;
	size_t attach_apid_offset;
	size_t attach_offset_offset;
	size_t attach_size_offset;
	size_t attach_vaddr_offset;
	size_t attach_fd_offset;
	size_t attach_flags_offset;
	size_t detach_size;
	size_t detach_vaddr_offset;
};
struct xpmem_pin_page_offsets {
	size_t tg_n_pinned_offset;
	size_t vm_memory_range_lock_offset;
	size_t vm_stack_start_offset;
	size_t vm_stack_end_offset;
	size_t range_start_offset;
	size_t range_private_data_offset;
};
struct xpmem_ensure_valid_page_offsets {
	size_t seg_flags_offset;
	size_t seg_tg_offset;
	size_t tg_group_leader_offset;
	size_t tg_vm_offset;
};
struct xpmem_vaddr_to_pte_offsets {
	size_t vm_address_space_offset;
	size_t address_space_page_table_offset;
	size_t range_pgshift_offset;
};
struct xpmem_unpin_pages_offsets {
	size_t seg_tg_offset;
	size_t tg_n_pinned_offset;
};
typedef int (*xpmem_init_fn_t)(void);
typedef long (*xpmem_forward_fn_t)(int syscall_num, void *ctx);
typedef int (*xpmem_open_fn_t)(void);
typedef void *(*xpmem_alloc_fn_t)(size_t size);
typedef long (*xpmem_lock_fn_t)(void *lock);
typedef void (*xpmem_unlock_fn_t)(void *lock, long irqstate);
typedef int (*xpmem_atomic_inc_fn_t)(void *counter);
typedef void (*xpmem_atomic_set_fn_t)(void *counter, int value);
typedef int (*xpmem_atomic_read_fn_t)(void *counter);
typedef int (*xpmem_atomic_dec_fn_t)(void *counter);
typedef void (*xpmem_bug_on_fn_t)(int condition);
typedef void (*xpmem_void_fn_t)(void);
typedef void (*xpmem_mckfd_void_fn_t)(void *mckfd);
typedef void (*xpmem_open_log_fn_t)(int event, int syscall_num,
		const char *pathname, int flags, long value, void *ptr);
typedef void (*xpmem_close_log_fn_t)(int event, void *mckfd, int value);
typedef void *(*xpmem_tg_ref_fn_t)(int pid);
typedef void (*xpmem_rwlock_fn_t)(void *lock, void *node);
typedef void (*xpmem_list_fn_t)(void *entry);
typedef void (*xpmem_spin_fn_t)(void *lock);
typedef void (*xpmem_tg_void_fn_t)(void *tg);
typedef void (*xpmem_flush_log_fn_t)(int event, void *tg, long value);
typedef void (*xpmem_ptr_void_fn_t)(void *ptr);
typedef long (*xpmem_object_id_fn_t)(void *ptr);
typedef void (*xpmem_list_add_tail_fn_t)(void *entry, void *head);
typedef void (*xpmem_remove_seg_log_fn_t)(int event, void *tg, void *seg,
		long value);
typedef void (*xpmem_remove_seg_fn_t)(void *tg, void *seg);
typedef void (*xpmem_remove_segs_log_fn_t)(int event, void *tg, void *seg,
		long value);
typedef void (*xpmem_detach_att_fn_t)(void *ap, void *att);
typedef void (*xpmem_release_ap_log_fn_t)(int event, void *tg, void *ap,
		long value);
typedef void *(*xpmem_id_ref_fn_t)(long id);
typedef void *(*xpmem_ref_by_id_fn_t)(void *parent, long id);
typedef void (*xpmem_rwspin_noirq_fn_t)(void *lock);
typedef unsigned long (*xpmem_rwspin_lock_fn_t)(void *lock);
typedef void (*xpmem_rwspin_unlock_fn_t)(void *lock,
		unsigned long state);
typedef void *(*xpmem_lookup_range_fn_t)(void *vm, unsigned long start,
		unsigned long end);
typedef void *(*xpmem_next_range_fn_t)(void *vm, void *range);
typedef int (*xpmem_split_range_fn_t)(void *vm, void *range,
		unsigned long addr, void **newrangep);
typedef int (*xpmem_range_action_fn_t)(void *vm, void *range);
typedef void (*xpmem_remove_process_range_log_fn_t)(void *vm,
		unsigned long start, unsigned long end, int error,
		int free_error);
typedef int (*xpmem_pt_clear_range_fn_t)(void *page_table, void *vm,
		unsigned long start, unsigned long end);
typedef void (*xpmem_range_erase_fn_t)(void *root, void *node);
typedef void (*xpmem_free_process_range_log_fn_t)(int event, void *vm,
		void *range, unsigned long start, unsigned long end, int error);
typedef int (*xpmem_fault_range_page_in_fn_t)(void *vm, void *range,
		unsigned long vaddr, unsigned long reason, int page_in_remote);
typedef void (*xpmem_update_page_table_log_fn_t)(int event, void *vm,
		void *range, unsigned long vaddr, int error);
typedef int (*xpmem_validate_access_fn_t)(void *ap, off_t offset,
		size_t size, int mode, unsigned long *vaddrp);
typedef unsigned long (*xpmem_mmap_fn_t)(unsigned long addr, size_t len,
		unsigned long prot, unsigned long flags, int fd, off_t offset,
		unsigned long vm_flags, void *private_data);
typedef int (*xpmem_copy_from_user_fn_t)(void *dst, unsigned long src,
		size_t size);
typedef int (*xpmem_copy_to_user_fn_t)(unsigned long dst, const void *src,
		size_t size);
typedef int (*xpmem_make_fn_t)(unsigned long vaddr, size_t size,
		int permit_type, void *permit_value, long *segidp);
typedef int (*xpmem_remove_fn_t)(long segid);
typedef int (*xpmem_get_fn_t)(long segid, int flags, int permit_type,
		void *permit_value, long *apidp);
typedef int (*xpmem_release_fn_t)(long apid);
typedef int (*xpmem_attach_fn_t)(void *mckfd, long apid, off_t offset,
		size_t size, unsigned long vaddr, int fd, int flags,
		unsigned long *at_vaddrp);
typedef int (*xpmem_detach_fn_t)(unsigned long vaddr);
typedef void (*xpmem_unpin_pages_fn_t)(void *seg, void *vm,
		unsigned long vaddr, size_t size);
typedef int (*xpmem_munmap_fn_t)(void *vm, unsigned long addr, size_t len);
typedef int (*xpmem_remove_range_fn_t)(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp);
typedef void (*xpmem_clear_range_fn_t)(void *object, unsigned long start,
		unsigned long end);
typedef int (*xpmem_check_permit_fn_t)(int flags, void *seg);
typedef int (*xpmem_page_fault_vm_fn_t)(void *vm, unsigned long vaddr,
		unsigned long reason);
typedef int (*xpmem_page_fault_range_fn_t)(void *vm, void *range,
		unsigned long vaddr, unsigned long reason);
typedef int (*xpmem_pin_page_fn_t)(void *tg, void *thread, void *vm,
		unsigned long vaddr, int page_in);
typedef void *(*xpmem_pt_lookup_pte_fn_t)(void *page_table,
		unsigned long vaddr, int pgshift, void **base, size_t *pgsize,
		int *p2align);
typedef void *(*xpmem_vaddr_to_pte_fn_t)(void *vm, unsigned long vaddr,
		size_t *pgsize);
typedef int (*xpmem_pte_present_fn_t)(void *pte);
typedef void (*xpmem_atomic_sub_fn_t)(int value, void *counter);
typedef int (*xpmem_ensure_valid_fn_t)(void *seg, unsigned long vaddr,
		int page_in);
typedef unsigned long (*xpmem_pte_phys_fn_t)(void *pte);
typedef int (*xpmem_get_smaller_page_size_fn_t)(size_t pgsize,
		size_t *new_pgsize, int *p2align);
typedef void (*xpmem_adjust_page_size_fn_t)(void *page_table,
		unsigned long fault_addr, void *pte, void **pgaddr,
		size_t *pgsize);
typedef unsigned long (*xpmem_vrflag_to_ptattr_fn_t)(unsigned long flag,
		unsigned long reason);
typedef int (*xpmem_pgsize_contiguous_fn_t)(size_t pgsize);
typedef int (*xpmem_pt_set_pte_fn_t)(void *page_table, void *pte,
		size_t pgsize, unsigned long phys, unsigned long attr);
typedef int (*xpmem_pt_set_range_fn_t)(void *page_table, void *vm,
		unsigned long start, unsigned long end, unsigned long phys,
		unsigned long attr, int pgshift, void *vmr, int replace);
typedef void (*xpmem_flush_tlb_single_fn_t)(unsigned long vaddr);
typedef void (*xpmem_fault_log_fn_t)(int event, unsigned long a,
		unsigned long b, unsigned long c, size_t size, int error);
struct xpmem_fault_process_range_ops {
	xpmem_ptr_void_fn_t att_ref_fn;
	xpmem_ptr_void_fn_t att_deref_fn;
	xpmem_ptr_void_fn_t ap_ref_fn;
	xpmem_ptr_void_fn_t ap_deref_fn;
	xpmem_ptr_void_fn_t tg_ref_fn;
	xpmem_ptr_void_fn_t tg_deref_fn;
	xpmem_ptr_void_fn_t seg_ref_fn;
	xpmem_ptr_void_fn_t seg_deref_fn;
	xpmem_bug_on_fn_t bug_on_fn;
	xpmem_ensure_valid_fn_t ensure_valid_fn;
	xpmem_rwspin_noirq_fn_t read_lock_noirq_fn;
	xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn;
	xpmem_vaddr_to_pte_fn_t vaddr_to_pte_fn;
	xpmem_pte_present_fn_t pte_present_fn;
	xpmem_pte_phys_fn_t pte_phys_fn;
	xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn;
	xpmem_get_smaller_page_size_fn_t smaller_page_fn;
	xpmem_adjust_page_size_fn_t adjust_page_fn;
	xpmem_vrflag_to_ptattr_fn_t vrflag_to_ptattr_fn;
	xpmem_pgsize_contiguous_fn_t pgsize_contiguous_fn;
	xpmem_pt_set_pte_fn_t pt_set_pte_fn;
	xpmem_pt_set_range_fn_t pt_set_range_fn;
	xpmem_atomic_dec_fn_t atomic_dec_fn;
	xpmem_flush_tlb_single_fn_t flush_tlb_single_fn;
	xpmem_fault_log_fn_t log_fn;
};

XPMEM_HELPER_SCOPE int xpmem_close_decision_result(int n_opened,
		int has_data, int *flush_objects, int *exit_partition);
XPMEM_HELPER_SCOPE int xpmem_tg_hashtable_index_result(pid_t tgid);
XPMEM_HELPER_SCOPE int xpmem_ap_hashtable_index_result(xpmem_apid_t apid);
XPMEM_HELPER_SCOPE int xpmem_positive_id_result(long id);
XPMEM_HELPER_SCOPE int xpmem_owner_policy_result(pid_t current_pid,
		pid_t owner_tgid);
XPMEM_HELPER_SCOPE int xpmem_attach_initial_policy_result(xpmem_apid_t apid,
		off_t offset, unsigned long vaddr, size_t size,
		int fjmpi_workaround, size_t *adjusted_size);
XPMEM_HELPER_SCOPE int xpmem_begin_destroy_result(int flags, int *new_flags);
XPMEM_HELPER_SCOPE int xpmem_finish_destroy_result(int flags);
XPMEM_HELPER_SCOPE int xpmem_destroying_error_result(int flags, int error);
XPMEM_HELPER_SCOPE int xpmem_two_destroying_error_result(int first_flags,
		int second_flags, int error);
XPMEM_HELPER_SCOPE int xpmem_three_destroying_error_result(int first_flags,
		int second_flags, int third_flags, int error);
XPMEM_HELPER_SCOPE int xpmem_attach_destroying_result(int seg_flags,
		int seg_tg_flags);
XPMEM_HELPER_SCOPE int xpmem_detach_lookup_result(int has_range,
		unsigned long range_start, unsigned long at_vaddr,
		int has_private_data);
XPMEM_HELPER_SCOPE int xpmem_attach_overlap_result(pid_t current_pid,
		pid_t seg_tgid, unsigned long requested_vaddr, size_t size,
		unsigned long seg_vaddr);
XPMEM_HELPER_SCOPE int xpmem_is_destroying_result(int flags);
XPMEM_HELPER_SCOPE int xpmem_remove_range_step_result(
		unsigned long range_start, unsigned long range_end,
		unsigned long start, unsigned long end, unsigned long range_flags,
		int has_private_data, int *split_start, int *split_end,
		int *ro_freed, int *remove_private);
XPMEM_HELPER_SCOPE int xpmem_free_process_range_body_result(void *vm,
		void *range,
		const struct xpmem_free_process_range_offsets *offsets,
		xpmem_spin_fn_t lock_fn,
		xpmem_spin_fn_t unlock_fn,
		xpmem_pt_clear_range_fn_t pt_clear_fn,
		xpmem_ptr_void_fn_t memobj_unref_fn,
		xpmem_range_erase_fn_t erase_fn,
		xpmem_ptr_void_fn_t free_fn,
		xpmem_free_process_range_log_fn_t log_fn);
XPMEM_HELPER_SCOPE int xpmem_update_process_page_table_body_result(
		void *vm, void *vmr, int current_pid,
		int page_in_remote_on_attach,
		const struct xpmem_update_page_table_offsets *offsets,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_bug_on_fn_t bug_on_fn,
		xpmem_fault_range_page_in_fn_t fault_fn,
		xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn,
		xpmem_pte_present_fn_t pte_present_fn,
		xpmem_update_page_table_log_fn_t log_fn);
XPMEM_HELPER_SCOPE int xpmem_fault_process_memory_range_body_result(
		void *vm, void *vmr, unsigned long vaddr,
		unsigned long reason, int page_in_remote, int current_pid,
		void *current_vm,
		const struct xpmem_fault_process_range_offsets *offsets,
		const struct xpmem_fault_process_range_ops *ops);
XPMEM_HELPER_SCOPE int xpmem_ioctl_body_result(void *mckfd,
		unsigned long cmd, unsigned long arg,
		const struct xpmem_ioctl_offsets *offsets,
		xpmem_copy_from_user_fn_t copy_from_user_fn,
		xpmem_copy_to_user_fn_t copy_to_user_fn,
		xpmem_make_fn_t make_fn,
		xpmem_remove_fn_t remove_fn,
		xpmem_get_fn_t get_fn,
		xpmem_release_fn_t release_fn,
		xpmem_attach_fn_t attach_fn,
		xpmem_detach_fn_t detach_fn);
XPMEM_HELPER_SCOPE int xpmem_attach_body_result(void *mckfd, long apid,
		off_t offset, size_t size, unsigned long vaddr,
		unsigned long *at_vaddrp, int current_pid, void *current_vm,
		int fjmpi_workaround, unsigned long prot_flags,
		unsigned long map_shared, unsigned long map_fixed,
		unsigned long map_anonymous, unsigned long vr_xpmem,
		const struct xpmem_attach_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_apid_fn,
		xpmem_ref_by_id_fn_t ap_ref_by_apid_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_validate_access_fn_t validate_access_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t rwspin_init_fn,
		xpmem_list_fn_t list_init_fn,
		xpmem_ptr_void_fn_t att_not_destroyable_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_next_range_fn_t next_range_fn,
		xpmem_mmap_fn_t mmap_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn);
XPMEM_HELPER_SCOPE int xpmem_remove_memory_range_action_result(
		unsigned long vmr_start, unsigned long vmr_end,
		unsigned long att_at_vaddr, size_t att_at_size,
		unsigned long *remaining_vaddrp,
		unsigned long *middle_lookup_vaddrp,
		int *full_detachp, int *needs_middle_lookupp);
XPMEM_HELPER_SCOPE int xpmem_range_private_invalid_result(int has_range,
		unsigned long range_start, unsigned long vaddr,
		int private_matches);
XPMEM_HELPER_SCOPE int xpmem_clear_pte_range_result(int att_flags,
		unsigned long att_vaddr, unsigned long att_at_vaddr,
		size_t att_at_size, unsigned long start, unsigned long end,
		unsigned long *unpin_atp, unsigned long *invalidate_lenp,
		int *clear_validp);
XPMEM_HELPER_SCOPE int xpmem_fault_vaddr_result(unsigned long vaddr,
		unsigned long att_at_vaddr, size_t att_at_size,
		unsigned long att_vaddr, unsigned long *seg_vaddr);
XPMEM_HELPER_SCOPE int xpmem_straight_phys_result(unsigned long seg_vaddr,
		unsigned long straight_va, size_t straight_len,
		unsigned long straight_pa, unsigned long *seg_phys,
		size_t *seg_pgsize);
XPMEM_HELPER_SCOPE int xpmem_remote_pte_missing_result(int has_pte,
		int pte_is_empty, int page_in_remote);
XPMEM_HELPER_SCOPE unsigned long xpmem_seg_phys_plus_off_result(
		unsigned long seg_phys, size_t seg_pgsize,
		unsigned long seg_vaddr);
XPMEM_HELPER_SCOPE int xpmem_att_page_fits_result(unsigned long att_pgaddr,
		size_t att_pgsize, unsigned long vmr_start,
		unsigned long vmr_end, size_t seg_pgsize);
XPMEM_HELPER_SCOPE int xpmem_pte_mismatch_result(unsigned long att_phys,
		unsigned long seg_phys_aligned);
XPMEM_HELPER_SCOPE int xpmem_unpin_step_result(unsigned long vaddr,
		size_t vsize, int has_present_pte,
		unsigned long *next_vaddr, int *unpinned);

XPMEM_HELPER_SCOPE int
xpmem_open_body_result(int syscall_num, const char *pathname, int flags,
		void *ctx, void **partp, void *proc,
		const struct xpmem_open_offsets *offsets,
		unsigned long ioctl_cb_addr, unsigned long close_cb_addr,
		unsigned long dup_cb_addr, xpmem_init_fn_t init_fn,
		xpmem_forward_fn_t forward_fn, xpmem_open_fn_t open_fn,
		xpmem_alloc_fn_t alloc_fn, xpmem_lock_fn_t lock_fn,
		xpmem_unlock_fn_t unlock_fn,
		xpmem_atomic_inc_fn_t atomic_inc_fn,
		xpmem_open_log_fn_t log_fn)
{
	long fd_long;
	int fd;
	int ret;
	void *mckfd;
	void **headp;
	void *old_head;
	void *lock;
	void *part;
	long irqstate;
	int n_opened;

	if (!partp || !proc || !offsets || !init_fn || !forward_fn ||
			!open_fn || !alloc_fn || !lock_fn || !unlock_fn ||
			!atomic_inc_fn) {
		return -EINVAL;
	}

	if (log_fn) {
		log_fn(XPMEM_OPEN_LOG_CALL, syscall_num, pathname, flags,
				0, NULL);
	}

	if (!*partp) {
		ret = init_fn();
		if (ret) {
			return ret;
		}
	}

	fd_long = forward_fn(syscall_num, ctx);
	if (fd_long < 0) {
		if (log_fn) {
			log_fn(XPMEM_OPEN_LOG_SYSCALL_ERROR, syscall_num,
					pathname, flags, fd_long, NULL);
		}
		return (int)fd_long;
	}
	fd = (int)fd_long;

	ret = open_fn();
	if (ret) {
		if (log_fn) {
			log_fn(XPMEM_OPEN_LOG_OPEN_ERROR, syscall_num,
					pathname, flags, ret, NULL);
		}
		return ret;
	}

	mckfd = alloc_fn(offsets->mckfd_size);
	if (!mckfd) {
		return -ENOMEM;
	}
	memset(mckfd, 0, offsets->mckfd_size);
	if (log_fn) {
		log_fn(XPMEM_OPEN_LOG_ALLOC, syscall_num, pathname, flags,
				0, mckfd);
	}

	*(int *)((char *)mckfd + offsets->mckfd_fd_offset) = fd;
	*(int *)((char *)mckfd + offsets->mckfd_sig_no_offset) = -1;
	*(long *)((char *)mckfd + offsets->mckfd_data_offset) = (long)proc;
	*(unsigned long *)((char *)mckfd + offsets->mckfd_ioctl_cb_offset) =
		ioctl_cb_addr;
	*(unsigned long *)((char *)mckfd + offsets->mckfd_close_cb_offset) =
		close_cb_addr;
	*(unsigned long *)((char *)mckfd + offsets->mckfd_dup_cb_offset) =
		dup_cb_addr;

	lock = (char *)proc + offsets->proc_mckfd_lock_offset;
	headp = (void **)((char *)proc + offsets->proc_mckfd_offset);
	irqstate = lock_fn(lock);
	old_head = *headp;
	*(void **)((char *)mckfd + offsets->mckfd_next_offset) = old_head;
	*headp = mckfd;
	unlock_fn(lock, irqstate);

	part = *partp;
	if (!part) {
		return -EINVAL;
	}
	n_opened = atomic_inc_fn((char *)part + offsets->part_n_opened_offset);
	if (log_fn) {
		log_fn(XPMEM_OPEN_LOG_N_OPENED, syscall_num, pathname,
				flags, n_opened, NULL);
		log_fn(XPMEM_OPEN_LOG_RETURN, syscall_num, pathname, flags,
				fd, NULL);
	}

	return fd;
}

XPMEM_HELPER_SCOPE int
xpmem_ioctl_body_result(void *mckfd, unsigned long cmd, unsigned long arg,
		const struct xpmem_ioctl_offsets *offsets,
		xpmem_copy_from_user_fn_t copy_from_user_fn,
		xpmem_copy_to_user_fn_t copy_to_user_fn,
		xpmem_make_fn_t make_fn,
		xpmem_remove_fn_t remove_fn,
		xpmem_get_fn_t get_fn,
		xpmem_release_fn_t release_fn,
		xpmem_attach_fn_t attach_fn,
		xpmem_detach_fn_t detach_fn)
{
	unsigned long storage[16] = { 0 };
	void *buf = storage;
	size_t cap = sizeof(storage);
	int ret;

	if (!mckfd || !offsets || !copy_from_user_fn || !copy_to_user_fn ||
			!make_fn || !remove_fn || !get_fn || !release_fn ||
			!attach_fn || !detach_fn) {
		return -EINVAL;
	}

	if (cmd == offsets->cmd_version) {
		return offsets->current_version;
	}

	if (cmd == offsets->cmd_make) {
		long segid = 0;

		if (offsets->make_size > cap) {
			return -EINVAL;
		}
		if (copy_from_user_fn(buf, arg, offsets->make_size)) {
			return -EFAULT;
		}

		ret = make_fn(*(unsigned long *)((char *)buf +
					offsets->make_vaddr_offset),
				*(size_t *)((char *)buf +
					offsets->make_size_offset),
				*(int *)((char *)buf +
					offsets->make_permit_type_offset),
				(void *)(uintptr_t)*(unsigned long *)((char *)buf +
					offsets->make_permit_value_offset),
				&segid);
		if (ret) {
			return ret;
		}
		if (copy_to_user_fn(arg + offsets->make_segid_offset, &segid,
					sizeof(segid))) {
			(void)remove_fn(segid);
			return -EFAULT;
		}
		return ret;
	}

	if (cmd == offsets->cmd_remove) {
		if (offsets->remove_size > cap) {
			return -EINVAL;
		}
		if (copy_from_user_fn(buf, arg, offsets->remove_size)) {
			return -EFAULT;
		}
		return remove_fn(*(long *)((char *)buf +
					offsets->remove_segid_offset));
	}

	if (cmd == offsets->cmd_get) {
		long apid = 0;

		if (offsets->get_size > cap) {
			return -EINVAL;
		}
		if (copy_from_user_fn(buf, arg, offsets->get_size)) {
			return -EFAULT;
		}

		ret = get_fn(*(long *)((char *)buf + offsets->get_segid_offset),
				*(int *)((char *)buf + offsets->get_flags_offset),
				*(int *)((char *)buf +
					offsets->get_permit_type_offset),
				(void *)(uintptr_t)*(unsigned long *)((char *)buf +
					offsets->get_permit_value_offset),
				&apid);
		if (ret) {
			return ret;
		}
		if (copy_to_user_fn(arg + offsets->get_apid_offset, &apid,
					sizeof(apid))) {
			(void)release_fn(apid);
			return -EFAULT;
		}
		return ret;
	}

	if (cmd == offsets->cmd_release) {
		if (offsets->release_size > cap) {
			return -EINVAL;
		}
		if (copy_from_user_fn(buf, arg, offsets->release_size)) {
			return -EFAULT;
		}
		return release_fn(*(long *)((char *)buf +
					offsets->release_apid_offset));
	}

	if (cmd == offsets->cmd_attach) {
		unsigned long at_vaddr = 0;

		if (offsets->attach_size > cap) {
			return -EINVAL;
		}
		if (copy_from_user_fn(buf, arg, offsets->attach_size)) {
			return -EFAULT;
		}

		ret = attach_fn(mckfd,
				*(long *)((char *)buf +
					offsets->attach_apid_offset),
				*(off_t *)((char *)buf +
					offsets->attach_offset_offset),
				*(size_t *)((char *)buf +
					offsets->attach_size_offset),
				*(unsigned long *)((char *)buf +
					offsets->attach_vaddr_offset),
				*(int *)((char *)buf + offsets->attach_fd_offset),
				*(int *)((char *)buf +
					offsets->attach_flags_offset),
				&at_vaddr);
		if (ret) {
			return ret;
		}
		if (copy_to_user_fn(arg + offsets->attach_vaddr_offset,
					&at_vaddr, sizeof(at_vaddr))) {
			(void)detach_fn(at_vaddr);
			return -EFAULT;
		}
		return ret;
	}

	if (cmd == offsets->cmd_detach) {
		if (offsets->detach_size > cap) {
			return -EINVAL;
		}
		if (copy_from_user_fn(buf, arg, offsets->detach_size)) {
			return -EFAULT;
		}
		return detach_fn(*(unsigned long *)((char *)buf +
					offsets->detach_vaddr_offset));
	}

	return -EINVAL;
}

XPMEM_HELPER_SCOPE int
xpmem_dup_body_result(void *mckfd, void **partp,
		const struct xpmem_close_offsets *offsets,
		xpmem_atomic_inc_fn_t atomic_inc_fn)
{
	void *part;

	if (!mckfd || !partp || !offsets || !atomic_inc_fn) {
		return -EINVAL;
	}
	part = *partp;
	if (!part) {
		return -EINVAL;
	}

	*(long *)((char *)mckfd + offsets->mckfd_data_offset) = 0;
	atomic_inc_fn((char *)part + offsets->part_n_opened_offset);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_close_body_result(void *mckfd, void **partp,
		const struct xpmem_close_offsets *offsets,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_mckfd_void_fn_t flush_fn, xpmem_void_fn_t exit_fn,
		xpmem_close_log_fn_t log_fn)
{
	void *part;
	int n_opened;
	int flush_objects;
	int exit_partition;
	int has_data;

	if (!mckfd || !partp || !offsets || !atomic_dec_fn) {
		return -EINVAL;
	}
	part = *partp;
	if (!part) {
		return -EINVAL;
	}

	if (log_fn) {
		log_fn(1, mckfd, 0);
	}

	n_opened = atomic_dec_fn((char *)part + offsets->part_n_opened_offset);
	if (log_fn) {
		log_fn(2, mckfd, n_opened);
	}

	has_data = *(long *)((char *)mckfd + offsets->mckfd_data_offset) != 0;
	xpmem_close_decision_result(n_opened, has_data,
			&flush_objects, &exit_partition);

	if (flush_objects) {
		if (!flush_fn) {
			return -EINVAL;
		}
		flush_fn(mckfd);
	}

	if (exit_partition) {
		if (!exit_fn) {
			return -EINVAL;
		}
		exit_fn();
	}

	if (log_fn) {
		log_fn(3, mckfd, 0);
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_open_tg_body_result(void **partp, void *current_thread,
		void *current_proc, void *current_vm,
		const struct xpmem_open_tg_offsets *offsets,
		void *rwlock_node, xpmem_tg_ref_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t spinlock_init_fn,
		xpmem_ptr_void_fn_t rwlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_atomic_set_fn_t atomic_set_fn,
		xpmem_ptr_void_fn_t tg_not_destroyable_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn)
{
	void *part;
	void *existing;
	void *tg;
	void *hashlist;
	void *hash_lock;
	int pid;
	int index;

	if (!partp || !current_proc || !offsets || !rwlock_node ||
			!tg_ref_fn || !tg_deref_fn || !alloc_fn ||
			!spinlock_init_fn || !rwlock_init_fn ||
			!list_init_fn || !atomic_set_fn ||
			!tg_not_destroyable_fn || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !list_add_tail_fn) {
		return -EINVAL;
	}
	part = *partp;
	if (!part) {
		return -EINVAL;
	}

	pid = *(int *)((char *)current_proc + offsets->proc_pid_offset);
	existing = tg_ref_fn(pid);
	if (!IS_ERR(existing) && existing) {
		tg_deref_fn(existing);
		return 0;
	}

	tg = alloc_fn(offsets->tg_size);
	if (!tg) {
		return -ENOMEM;
	}
	memset(tg, 0, offsets->tg_size);

	spinlock_init_fn((char *)tg + offsets->tg_lock_offset);
	*(int *)((char *)tg + offsets->tg_tgid_offset) = pid;
	*(int *)((char *)tg + offsets->tg_uid_offset) =
		*(int *)((char *)current_proc + offsets->proc_ruid_offset);
	*(int *)((char *)tg + offsets->tg_gid_offset) =
		*(int *)((char *)current_proc + offsets->proc_rgid_offset);
	atomic_set_fn((char *)tg + offsets->tg_uniq_segid_offset, 0);
	atomic_set_fn((char *)tg + offsets->tg_uniq_apid_offset, 0);
	rwlock_init_fn((char *)tg + offsets->tg_seg_list_lock_offset);
	list_init_fn((char *)tg + offsets->tg_seg_list_offset);
	atomic_set_fn((char *)tg + offsets->tg_n_pinned_offset, 0);
	list_init_fn((char *)tg + offsets->tg_tg_hashlist_offset);
	*(void **)((char *)tg + offsets->tg_vm_offset) = current_vm;

	for (index = 0; index < XPMEM_AP_HASHTABLE_SIZE; index++) {
		hashlist = (char *)tg + offsets->tg_ap_hashtable_offset +
			index * offsets->hashlist_stride;
		rwlock_init_fn((char *)hashlist + offsets->hashlist_lock_offset);
		list_init_fn((char *)hashlist + offsets->hashlist_list_offset);
	}

	tg_not_destroyable_fn(tg);

	index = xpmem_tg_hashtable_index_result(pid);
	hashlist = (char *)part + offsets->part_tg_hashtable_offset +
		index * offsets->hashlist_stride;
	hash_lock = (char *)hashlist + offsets->hashlist_lock_offset;
	rwlock_lock_fn(hash_lock, rwlock_node);
	list_add_tail_fn((char *)tg + offsets->tg_tg_hashlist_offset,
			(char *)hashlist + offsets->hashlist_list_offset);
	rwlock_unlock_fn(hash_lock, rwlock_node);

	*(void **)((char *)tg + offsets->tg_group_leader_offset) =
		current_thread;

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_partition_init_body_result(void **partp,
		const struct xpmem_partition_offsets *offsets,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t rwlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_atomic_set_fn_t atomic_set_fn)
{
	void *part;
	void *hashlist;
	int index;

	if (!partp || !offsets || !alloc_fn || !rwlock_init_fn ||
			!list_init_fn || !atomic_set_fn) {
		return -EINVAL;
	}

	part = alloc_fn(offsets->part_size);
	if (!part) {
		return -ENOMEM;
	}
	memset(part, 0, offsets->part_size);

	for (index = 0; index < XPMEM_TG_HASHTABLE_SIZE; index++) {
		hashlist = (char *)part + offsets->part_tg_hashtable_offset +
			index * offsets->hashlist_stride;
		rwlock_init_fn((char *)hashlist + offsets->hashlist_lock_offset);
		list_init_fn((char *)hashlist + offsets->hashlist_list_offset);
	}

	atomic_set_fn((char *)part + offsets->part_n_opened_offset, 0);
	*partp = part;

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_partition_exit_body_result(void **partp, xpmem_ptr_void_fn_t free_fn)
{
	void *part;

	if (!partp || !free_fn) {
		return -EINVAL;
	}

	part = *partp;
	if (part) {
		free_fn(part);
		*partp = NULL;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_flush_body_result(void *mckfd, void **partp,
		const struct xpmem_flush_offsets *offsets, void *rwlock_node,
		xpmem_tg_ref_fn_t tg_ref_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_tg_void_fn_t release_aps_fn,
		xpmem_tg_void_fn_t remove_segs_fn,
		xpmem_tg_void_fn_t destroy_tg_fn,
		xpmem_flush_log_fn_t log_fn)
{
	void *part;
	void *proc;
	void *hashlist;
	void *hash_lock;
	void *tg;
	void *tg_lock;
	int pid;
	int index;
	int new_flags;
	int *flags;
	void *vm;

	if (!mckfd || !partp || !offsets || !rwlock_node || !tg_ref_fn ||
			!rwlock_lock_fn || !rwlock_unlock_fn ||
			!list_del_init_fn || !spin_lock_fn || !spin_unlock_fn ||
			!release_aps_fn || !remove_segs_fn || !destroy_tg_fn) {
		return -EINVAL;
	}
	part = *partp;
	if (!part) {
		return -EINVAL;
	}
	proc = *(void **)((char *)mckfd + offsets->mckfd_data_offset);
	if (!proc) {
		return -EINVAL;
	}

	pid = *(int *)((char *)proc + offsets->proc_pid_offset);
	index = xpmem_tg_hashtable_index_result(pid);
	hashlist = (char *)part + offsets->part_tg_hashtable_offset +
		(size_t)index * offsets->hashlist_stride;
	hash_lock = (char *)hashlist + offsets->hashlist_lock_offset;

	rwlock_lock_fn(hash_lock, rwlock_node);
	tg = tg_ref_fn(pid);
	if (!tg || IS_ERR(tg)) {
		rwlock_unlock_fn(hash_lock, rwlock_node);
		return 0;
	}

	list_del_init_fn((char *)tg + offsets->tg_hashlist_offset);
	rwlock_unlock_fn(hash_lock, rwlock_node);

	if (log_fn) {
		vm = *(void **)((char *)tg + offsets->tg_vm_offset);
		log_fn(1, tg, (long)vm);
	}

	tg_lock = (char *)tg + offsets->tg_lock_offset;
	flags = (int *)((char *)tg + offsets->tg_flags_offset);

	spin_lock_fn(tg_lock);
	(void)xpmem_begin_destroy_result(*flags, &new_flags);
	*flags = new_flags;
	spin_unlock_fn(tg_lock);

	release_aps_fn(tg);
	remove_segs_fn(tg);

	spin_lock_fn(tg_lock);
	*flags = xpmem_finish_destroy_result(*flags);
	spin_unlock_fn(tg_lock);

	destroy_tg_fn(tg);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_seg_body_result(void *seg_tg, void *seg,
		const struct xpmem_remove_seg_offsets *offsets,
		void *rwlock_node, xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_ptr_void_fn_t clear_ptes_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t seg_destroyable_fn,
		xpmem_remove_seg_log_fn_t log_fn)
{
	void *seg_lock;
	void *seg_list_lock;
	int *flags;
	int new_flags;

	if (!seg_tg || !seg || !offsets || !rwlock_node || !spin_lock_fn ||
			!spin_unlock_fn || !clear_ptes_fn ||
			!rwlock_lock_fn || !rwlock_unlock_fn ||
			!list_del_init_fn || !seg_destroyable_fn) {
		return -EINVAL;
	}

	if (log_fn) {
		log_fn(XPMEM_REMOVE_SEG_LOG_CALL, seg_tg, seg, 0);
	}

	seg_lock = (char *)seg + offsets->seg_lock_offset;
	flags = (int *)((char *)seg + offsets->seg_flags_offset);
	spin_lock_fn(seg_lock);
	if (!xpmem_begin_destroy_result(*flags, &new_flags)) {
		spin_unlock_fn(seg_lock);
		return 0;
	}
	*flags = new_flags;
	spin_unlock_fn(seg_lock);

	clear_ptes_fn(seg);

	spin_lock_fn(seg_lock);
	*flags = xpmem_finish_destroy_result(*flags);
	spin_unlock_fn(seg_lock);

	seg_list_lock = (char *)seg_tg + offsets->tg_seg_list_lock_offset;
	rwlock_lock_fn(seg_list_lock, rwlock_node);
	list_del_init_fn((char *)seg + offsets->seg_list_offset);
	rwlock_unlock_fn(seg_list_lock, rwlock_node);

	seg_destroyable_fn(seg);

	if (log_fn) {
		log_fn(XPMEM_REMOVE_SEG_LOG_RETURN, seg_tg, seg, 0);
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_segs_of_tg_body_result(void *seg_tg,
		const struct xpmem_remove_segs_offsets *offsets,
		void *rwlock_node,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_remove_seg_fn_t remove_seg_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_remove_segs_log_fn_t log_fn)
{
	void *seg_list_lock;
	struct list_head *head;
	struct list_head *next;
	void *seg;

	if (!seg_tg || !offsets || !rwlock_node || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !seg_ref_fn ||
			!remove_seg_fn || !seg_deref_fn) {
		return -EINVAL;
	}

	if (log_fn) {
		log_fn(XPMEM_REMOVE_SEGS_LOG_CALL, seg_tg, NULL, 0);
	}

	seg_list_lock = (char *)seg_tg + offsets->tg_seg_list_lock_offset;
	head = (struct list_head *)((char *)seg_tg +
			offsets->tg_seg_list_offset);

	rwlock_lock_fn(seg_list_lock, rwlock_node);
	while (!list_empty(head)) {
		next = head->next;
		seg = (char *)next - offsets->seg_list_offset;
		seg_ref_fn(seg);
		rwlock_unlock_fn(seg_list_lock, rwlock_node);

		remove_seg_fn(seg_tg, seg);
		seg_deref_fn(seg);

		rwlock_lock_fn(seg_list_lock, rwlock_node);
	}
	rwlock_unlock_fn(seg_list_lock, rwlock_node);

	if (log_fn) {
		log_fn(XPMEM_REMOVE_SEGS_LOG_RETURN, seg_tg, NULL, 0);
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_release_ap_body_result(void *ap_tg, void *ap,
		const struct xpmem_release_ap_offsets *offsets,
		void *rwlock_node,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_detach_att_fn_t detach_att_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t ap_destroyable_fn,
		xpmem_release_ap_log_fn_t log_fn)
{
	void *ap_lock;
	void *hashlist;
	void *hash_lock;
	void *seg_lock;
	void *seg;
	void *seg_tg;
	void *att;
	struct list_head *att_head;
	struct list_head *next;
	long apid;
	int *flags;
	int new_flags;
	int index;

	if (!ap_tg || !ap || !offsets || !rwlock_node || !spin_lock_fn ||
			!spin_unlock_fn || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !list_del_init_fn ||
			!att_ref_fn || !detach_att_fn || !att_deref_fn ||
			!seg_deref_fn || !tg_deref_fn || !ap_destroyable_fn) {
		return -EINVAL;
	}

	apid = *(long *)((char *)ap + offsets->ap_apid_offset);
	if (log_fn) {
		log_fn(XPMEM_RELEASE_AP_LOG_CALL, ap_tg, ap, apid);
	}

	ap_lock = (char *)ap + offsets->ap_lock_offset;
	flags = (int *)((char *)ap + offsets->ap_flags_offset);
	spin_lock_fn(ap_lock);
	if (!xpmem_begin_destroy_result(*flags, &new_flags)) {
		spin_unlock_fn(ap_lock);
		return 0;
	}
	*flags = new_flags;

	att_head = (struct list_head *)((char *)ap +
			offsets->ap_att_list_offset);
	while (!list_empty(att_head)) {
		next = att_head->next;
		att = (char *)next - offsets->att_att_list_offset;

		att_ref_fn(att);
		spin_unlock_fn(ap_lock);

		detach_att_fn(ap, att);
		att_deref_fn(att);

		spin_lock_fn(ap_lock);
	}

	*flags = xpmem_finish_destroy_result(*flags);
	spin_unlock_fn(ap_lock);

	index = xpmem_ap_hashtable_index_result(apid);
	hashlist = (char *)ap_tg + offsets->tg_ap_hashtable_offset +
			index * offsets->hashlist_stride;
	hash_lock = (char *)hashlist + offsets->hashlist_lock_offset;
	rwlock_lock_fn(hash_lock, rwlock_node);
	list_del_init_fn((char *)ap + offsets->ap_hashlist_offset);
	rwlock_unlock_fn(hash_lock, rwlock_node);

	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	seg_tg = *(void **)((char *)seg + offsets->seg_tg_offset);

	seg_lock = (char *)seg + offsets->seg_lock_offset;
	spin_lock_fn(seg_lock);
	list_del_init_fn((char *)ap + offsets->ap_ap_list_offset);
	spin_unlock_fn(seg_lock);

	seg_deref_fn(seg);
	tg_deref_fn(seg_tg);
	ap_destroyable_fn(ap);

	if (log_fn) {
		log_fn(XPMEM_RELEASE_AP_LOG_RETURN, ap_tg, ap, 0);
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_release_aps_of_tg_body_result(void *ap_tg,
		const struct xpmem_release_aps_offsets *offsets,
		void *rwlock_node,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_remove_seg_fn_t release_ap_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_remove_segs_log_fn_t log_fn)
{
	void *hashlist;
	void *hash_lock;
	struct list_head *head;
	struct list_head *next;
	void *ap;
	int index;

	if (!ap_tg || !offsets || !rwlock_node || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !ap_ref_fn ||
			!release_ap_fn || !ap_deref_fn) {
		return -EINVAL;
	}

	if (log_fn) {
		log_fn(XPMEM_RELEASE_AP_LOG_CALL, ap_tg, NULL, 0);
	}

	for (index = 0; index < XPMEM_AP_HASHTABLE_SIZE; index++) {
		hashlist = (char *)ap_tg + offsets->tg_ap_hashtable_offset +
			index * offsets->hashlist_stride;
		hash_lock = (char *)hashlist + offsets->hashlist_lock_offset;
		head = (struct list_head *)((char *)hashlist +
			offsets->hashlist_list_offset);

		rwlock_lock_fn(hash_lock, rwlock_node);
		while (!list_empty(head)) {
			next = head->next;
			ap = (char *)next - offsets->ap_hashlist_offset;
			ap_ref_fn(ap);
			rwlock_unlock_fn(hash_lock, rwlock_node);

			release_ap_fn(ap_tg, ap);
			ap_deref_fn(ap);

			rwlock_lock_fn(hash_lock, rwlock_node);
		}
		rwlock_unlock_fn(hash_lock, rwlock_node);
	}

	if (log_fn) {
		log_fn(XPMEM_RELEASE_AP_LOG_RETURN, ap_tg, NULL, 0);
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_destroy_tg_body_result(void *tg,
		xpmem_ptr_void_fn_t tg_destroyable_fn,
		xpmem_ptr_void_fn_t tg_deref_fn)
{
	if (!tg || !tg_destroyable_fn || !tg_deref_fn) {
		return -EINVAL;
	}

	tg_destroyable_fn(tg);
	tg_deref_fn(tg);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_body_result(long segid, int current_pid,
		const struct xpmem_tg_id_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_segid_fn,
		xpmem_ref_by_id_fn_t seg_ref_by_segid_fn,
		xpmem_remove_seg_fn_t remove_seg_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn)
{
	void *seg_tg;
	void *seg;
	int ret;
	int owner_tgid;

	if (!offsets || !tg_ref_by_segid_fn || !seg_ref_by_segid_fn ||
			!remove_seg_fn || !seg_deref_fn || !tg_deref_fn) {
		return -EINVAL;
	}

	ret = xpmem_positive_id_result(segid);
	if (ret) {
		return ret;
	}

	seg_tg = tg_ref_by_segid_fn(segid);
	if (!seg_tg || IS_ERR(seg_tg)) {
		return PTR_ERR(seg_tg);
	}

	owner_tgid = *(int *)((char *)seg_tg + offsets->tg_tgid_offset);
	ret = xpmem_owner_policy_result(current_pid, owner_tgid);
	if (ret) {
		tg_deref_fn(seg_tg);
		return ret;
	}

	seg = seg_ref_by_segid_fn(seg_tg, segid);
	if (!seg || IS_ERR(seg)) {
		tg_deref_fn(seg_tg);
		return PTR_ERR(seg);
	}

	remove_seg_fn(seg_tg, seg);
	seg_deref_fn(seg);
	tg_deref_fn(seg_tg);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_release_body_result(long apid, int current_pid,
		const struct xpmem_tg_id_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_apid_fn,
		xpmem_ref_by_id_fn_t ap_ref_by_apid_fn,
		xpmem_remove_seg_fn_t release_ap_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn)
{
	void *ap_tg;
	void *ap;
	int ret;
	int owner_tgid;

	if (!offsets || !tg_ref_by_apid_fn || !ap_ref_by_apid_fn ||
			!release_ap_fn || !ap_deref_fn || !tg_deref_fn) {
		return -EINVAL;
	}

	ret = xpmem_positive_id_result(apid);
	if (ret) {
		return ret;
	}

	ap_tg = tg_ref_by_apid_fn(apid);
	if (!ap_tg || IS_ERR(ap_tg)) {
		return PTR_ERR(ap_tg);
	}

	owner_tgid = *(int *)((char *)ap_tg + offsets->tg_tgid_offset);
	ret = xpmem_owner_policy_result(current_pid, owner_tgid);
	if (ret) {
		tg_deref_fn(ap_tg);
		return ret;
	}

	ap = ap_ref_by_apid_fn(ap_tg, apid);
	if (!ap || IS_ERR(ap)) {
		tg_deref_fn(ap_tg);
		return PTR_ERR(ap);
	}

	release_ap_fn(ap_tg, ap);
	ap_deref_fn(ap);
	tg_deref_fn(ap_tg);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_vm_munmap_body_result(void *vm, unsigned long addr, size_t len,
		xpmem_void_fn_t begin_fn,
		xpmem_remove_range_fn_t remove_range_fn,
		xpmem_void_fn_t finish_fn)
{
	int ret;
	int ro_freed;

	if (!vm || !begin_fn || !remove_range_fn || !finish_fn) {
		return -EINVAL;
	}

	begin_fn();
	ret = remove_range_fn(vm, addr, addr + len, &ro_freed);
	finish_fn();

	return ret;
}

XPMEM_HELPER_SCOPE int
xpmem_detach_body_result(unsigned long at_vaddr, int current_pid, void *vm,
		const struct xpmem_detach_offsets *offsets,
		xpmem_rwspin_noirq_fn_t write_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t write_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_unpin_pages_fn_t unpin_pages_fn,
		xpmem_munmap_fn_t munmap_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn)
{
	void *vm_lock;
	void *range;
	void *att;
	void *att_lock;
	void *ap;
	void *ap_lock;
	void *tg;
	void *seg;
	unsigned long at_lock;
	unsigned long range_start;
	size_t att_size;
	int *flags;
	int new_flags;
	int ret;

	if (!vm || !offsets || !write_lock_noirq_fn ||
			!write_unlock_noirq_fn || !lookup_range_fn ||
			!att_ref_fn || !att_deref_fn || !att_write_lock_fn ||
			!att_write_unlock_fn || !ap_ref_fn || !ap_deref_fn ||
			!unpin_pages_fn || !munmap_fn || !spin_lock_fn ||
			!spin_unlock_fn || !list_del_init_fn ||
			!att_destroyable_fn) {
		return -EINVAL;
	}

	vm_lock = (char *)vm + offsets->vm_memory_range_lock_offset;
	write_lock_noirq_fn(vm_lock);

	range = lookup_range_fn(vm, at_vaddr, at_vaddr + 1);
	range_start = range ?
		*(unsigned long *)((char *)range + offsets->range_start_offset) :
		0;
	att = range ? *(void **)((char *)range +
			offsets->range_private_data_offset) : NULL;
	ret = xpmem_detach_lookup_result(range != NULL, range_start,
			at_vaddr, att != NULL);
	if (ret <= 0) {
		write_unlock_noirq_fn(vm_lock);
		return ret;
	}

	att_ref_fn(att);
	att_lock = (char *)att + offsets->att_at_lock_offset;
	at_lock = att_write_lock_fn(att_lock);

	flags = (int *)((char *)att + offsets->att_flags_offset);
	if (!xpmem_begin_destroy_result(*flags, &new_flags)) {
		att_write_unlock_fn(att_lock, at_lock);
		write_unlock_noirq_fn(vm_lock);
		att_deref_fn(att);
		return 0;
	}
	*flags = new_flags;

	ap = *(void **)((char *)att + offsets->att_ap_offset);
	ap_ref_fn(ap);
	tg = *(void **)((char *)ap + offsets->ap_tg_offset);
	ret = xpmem_owner_policy_result(current_pid,
			*(int *)((char *)tg + offsets->tg_tgid_offset));
	if (ret) {
		*flags &= ~XPMEM_FLAG_DESTROYING;
		ap_deref_fn(ap);
		att_write_unlock_fn(att_lock, at_lock);
		write_unlock_noirq_fn(vm_lock);
		att_deref_fn(att);
		return ret;
	}

	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	att_size = *(size_t *)((char *)att + offsets->att_at_size_offset);
	unpin_pages_fn(seg, vm,
			*(unsigned long *)((char *)att +
				offsets->att_at_vaddr_offset),
			att_size);
	*(void **)((char *)range + offsets->range_private_data_offset) = NULL;

	att_write_unlock_fn(att_lock, at_lock);
	ret = munmap_fn(vm, range_start, att_size);
	write_unlock_noirq_fn(vm_lock);
	(void)ret;

	*flags &= ~XPMEM_FLAG_VALIDPTEs;

	ap_lock = (char *)ap + offsets->ap_lock_offset;
	spin_lock_fn(ap_lock);
	list_del_init_fn((char *)att + offsets->att_att_list_offset);
	spin_unlock_fn(ap_lock);

	att_destroyable_fn(att);
	ap_deref_fn(ap);
	att_deref_fn(att);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_detach_att_body_result(void *ap, void *att,
		const struct xpmem_detach_att_offsets *offsets,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_unpin_pages_fn_t unpin_pages_fn,
		xpmem_munmap_fn_t munmap_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn)
{
	void *att_lock;
	void *vm;
	void *vm_lock;
	void *range;
	void *ap_lock;
	void *seg;
	unsigned long at_lock;
	unsigned long att_vaddr;
	unsigned long range_start;
	size_t att_size;
	int *flags;
	int new_flags;
	int ret;

	if (!ap || !att || !offsets || !read_lock_noirq_fn ||
			!read_unlock_noirq_fn || !att_write_lock_fn ||
			!att_write_unlock_fn || !lookup_range_fn ||
			!unpin_pages_fn || !munmap_fn || !spin_lock_fn ||
			!spin_unlock_fn || !list_del_init_fn ||
			!att_destroyable_fn) {
		return -EINVAL;
	}

	att_lock = (char *)att + offsets->att_at_lock_offset;
	at_lock = att_write_lock_fn(att_lock);

	flags = (int *)((char *)att + offsets->att_flags_offset);
	if (!xpmem_begin_destroy_result(*flags, &new_flags)) {
		att_write_unlock_fn(att_lock, at_lock);
		return 0;
	}
	*flags = new_flags;

	vm = *(void **)((char *)att + offsets->att_vm_offset);
	vm_lock = (char *)vm + offsets->vm_memory_range_lock_offset;
	read_lock_noirq_fn(vm_lock);

	att_vaddr = *(unsigned long *)((char *)att +
			offsets->att_at_vaddr_offset);
	att_size = *(size_t *)((char *)att + offsets->att_at_size_offset);
	range = lookup_range_fn(vm, att_vaddr, att_vaddr + 1);
	range_start = range ?
		*(unsigned long *)((char *)range + offsets->range_start_offset) :
		0;
	if (!range || range_start > att_vaddr) {
		ap_lock = (char *)ap + offsets->ap_lock_offset;
		spin_lock_fn(ap_lock);
		list_del_init_fn((char *)att + offsets->att_att_list_offset);
		spin_unlock_fn(ap_lock);
		att_write_unlock_fn(att_lock, at_lock);
		read_unlock_noirq_fn(vm_lock);
		att_destroyable_fn(att);
		return 0;
	}

	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	unpin_pages_fn(seg, vm, att_vaddr, att_size);
	*(void **)((char *)range + offsets->range_private_data_offset) = NULL;

	*flags &= ~XPMEM_FLAG_VALIDPTEs;

	ap_lock = (char *)ap + offsets->ap_lock_offset;
	spin_lock_fn(ap_lock);
	list_del_init_fn((char *)att + offsets->att_att_list_offset);
	spin_unlock_fn(ap_lock);

	att_write_unlock_fn(att_lock, at_lock);
	ret = munmap_fn(vm, range_start, att_size);
	read_unlock_noirq_fn(vm_lock);
	(void)ret;

	att_destroyable_fn(att);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_clear_ptes_body_result(void *seg,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_clear_range_fn_t clear_range_fn)
{
	unsigned long start;
	size_t size;

	if (!seg || !offsets || !clear_range_fn) {
		return -EINVAL;
	}

	start = *(unsigned long *)((char *)seg + offsets->seg_vaddr_offset);
	size = *(size_t *)((char *)seg + offsets->seg_size_offset);
	clear_range_fn(seg, start, start + size);
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_clear_ptes_range_body_result(void *seg, unsigned long start,
		unsigned long end,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_clear_range_fn_t clear_ap_fn,
		xpmem_ptr_void_fn_t ap_deref_fn)
{
	void *seg_lock;
	struct list_head *head;
	struct list_head *cursor;

	if (!seg || !offsets || !spin_lock_fn || !spin_unlock_fn ||
			!ap_ref_fn || !clear_ap_fn || !ap_deref_fn) {
		return -EINVAL;
	}

	seg_lock = (char *)seg + offsets->seg_lock_offset;
	head = (struct list_head *)((char *)seg + offsets->seg_ap_list_offset);
	spin_lock_fn(seg_lock);

	cursor = head->next;
	while (cursor != head) {
		void *ap = (char *)cursor - offsets->ap_ap_list_offset;
		struct list_head *ap_entry;
		struct list_head *next;

		ap_ref_fn(ap);
		spin_unlock_fn(seg_lock);
		clear_ap_fn(ap, start, end);
		spin_lock_fn(seg_lock);

		ap_entry = (struct list_head *)((char *)ap +
				offsets->ap_ap_list_offset);
		next = list_empty(ap_entry) ? head->next : ap_entry->next;
		ap_deref_fn(ap);
		cursor = next;
	}

	spin_unlock_fn(seg_lock);
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_clear_ptes_of_ap_body_result(void *ap, unsigned long start,
		unsigned long end,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_clear_range_fn_t clear_att_fn,
		xpmem_ptr_void_fn_t att_deref_fn)
{
	void *ap_lock;
	struct list_head *head;
	struct list_head *cursor;

	if (!ap || !offsets || !spin_lock_fn || !spin_unlock_fn ||
			!att_ref_fn || !clear_att_fn || !att_deref_fn) {
		return -EINVAL;
	}

	ap_lock = (char *)ap + offsets->ap_lock_offset;
	head = (struct list_head *)((char *)ap + offsets->ap_att_list_offset);
	spin_lock_fn(ap_lock);

	cursor = head->next;
	while (cursor != head) {
		void *att = (char *)cursor - offsets->att_att_list_offset;
		struct list_head *att_entry;
		struct list_head *next;
		int flags = *(int *)((char *)att + offsets->att_flags_offset);

		if (!(flags & XPMEM_FLAG_VALIDPTEs)) {
			cursor = cursor->next;
			continue;
		}

		att_ref_fn(att);
		spin_unlock_fn(ap_lock);
		clear_att_fn(att, start, end);
		spin_lock_fn(ap_lock);

		att_entry = (struct list_head *)((char *)att +
				offsets->att_att_list_offset);
		next = list_empty(att_entry) ? head->next : att_entry->next;
		att_deref_fn(att);
		cursor = next;
	}

	spin_unlock_fn(ap_lock);
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_clear_ptes_of_att_body_result(void *att, unsigned long start,
		unsigned long end,
		const struct xpmem_clear_ptes_offsets *offsets,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_unpin_pages_fn_t unpin_pages_fn,
		xpmem_munmap_fn_t munmap_fn)
{
	void *vm;
	void *vm_lock;
	void *att_lock;
	void *ap;
	void *seg;
	void *range;
	unsigned long at_lock;
	unsigned long att_vaddr;
	unsigned long att_at_vaddr;
	size_t att_at_size;
	unsigned long unpin_at;
	unsigned long invalidate_len;
	int clear_valid;
	int *flags;
	int ret;

	if (!att || !offsets || !read_lock_noirq_fn ||
			!read_unlock_noirq_fn || !att_write_lock_fn ||
			!att_write_unlock_fn || !lookup_range_fn ||
			!unpin_pages_fn || !munmap_fn) {
		return -EINVAL;
	}

	vm = *(void **)((char *)att + offsets->att_vm_offset);
	if (!vm) {
		return -EINVAL;
	}

	vm_lock = (char *)vm + offsets->vm_memory_range_lock_offset;
	att_lock = (char *)att + offsets->att_at_lock_offset;
	read_lock_noirq_fn(vm_lock);
	at_lock = att_write_lock_fn(att_lock);

	flags = (int *)((char *)att + offsets->att_flags_offset);
	if (*flags & XPMEM_FLAG_VALIDPTEs) {
		att_vaddr = *(unsigned long *)((char *)att +
				offsets->att_vaddr_offset);
		att_at_vaddr = *(unsigned long *)((char *)att +
				offsets->att_at_vaddr_offset);
		att_at_size = *(size_t *)((char *)att +
				offsets->att_at_size_offset);

		ret = xpmem_clear_pte_range_result(*flags, att_vaddr,
				att_at_vaddr, att_at_size, start, end,
				&unpin_at, &invalidate_len, &clear_valid);
		if (ret) {
			ap = *(void **)((char *)att + offsets->att_ap_offset);
			seg = ap ? *(void **)((char *)ap +
					offsets->ap_seg_offset) : NULL;
			if (seg) {
				unpin_pages_fn(seg, vm, unpin_at,
						(size_t)invalidate_len);
			}

			range = lookup_range_fn(vm, att_at_vaddr,
					att_at_vaddr + 1);
			if (range) {
				att_write_unlock_fn(att_lock, at_lock);
				(void)munmap_fn(vm, unpin_at,
						(size_t)invalidate_len);
				at_lock = att_write_lock_fn(att_lock);
				if (clear_valid) {
					*flags &= ~XPMEM_FLAG_VALIDPTEs;
				}
			}
		}
	}

	att_write_unlock_fn(att_lock, at_lock);
	read_unlock_noirq_fn(vm_lock);
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_process_memory_range_body_result(void *vm, void *vmr,
		const struct xpmem_remove_process_memory_range_offsets *offsets,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn)
{
	void **vmr_privatep;
	void *att;
	void *att_lock;
	void *ap;
	void *ap_lock;
	unsigned long at_lock;
	unsigned long vmr_start;
	unsigned long vmr_end;
	unsigned long att_at_vaddr;
	size_t att_at_size;
	unsigned long remaining_vaddr;
	unsigned long middle_lookup_vaddr;
	int full_detach;
	int needs_middle_lookup;
	int new_flags;
	int *flags;

	if (!vm || !vmr || !offsets || !att_ref_fn || !att_deref_fn ||
			!att_write_lock_fn || !att_write_unlock_fn ||
			!lookup_range_fn || !ap_ref_fn || !ap_deref_fn ||
			!spin_lock_fn || !spin_unlock_fn || !list_del_init_fn ||
			!att_destroyable_fn) {
		return -EINVAL;
	}

	vmr_privatep = (void **)((char *)vmr +
			offsets->range_private_data_offset);
	att = *vmr_privatep;
	if (!att) {
		return 0;
	}

	att_ref_fn(att);
	att_lock = (char *)att + offsets->att_at_lock_offset;
	at_lock = att_write_lock_fn(att_lock);
	flags = (int *)((char *)att + offsets->att_flags_offset);

	if (xpmem_is_destroying_result(*flags)) {
		att_write_unlock_fn(att_lock, at_lock);
		att_deref_fn(att);
		return 0;
	}

	vmr_start = *(unsigned long *)((char *)vmr +
			offsets->range_start_offset);
	vmr_end = *(unsigned long *)((char *)vmr +
			offsets->range_end_offset);
	att_at_vaddr = *(unsigned long *)((char *)att +
			offsets->att_at_vaddr_offset);
	att_at_size = *(size_t *)((char *)att + offsets->att_at_size_offset);

	xpmem_remove_memory_range_action_result(vmr_start, vmr_end,
			att_at_vaddr, att_at_size, &remaining_vaddr,
			&middle_lookup_vaddr, &full_detach,
			&needs_middle_lookup);

	if (full_detach) {
		(void)xpmem_begin_destroy_result(*flags, &new_flags);
		*flags = new_flags;

		ap = *(void **)((char *)att + offsets->att_ap_offset);
		ap_ref_fn(ap);
		ap_lock = (char *)ap + offsets->ap_lock_offset;
		spin_lock_fn(ap_lock);
		list_del_init_fn((char *)att + offsets->att_att_list_offset);
		spin_unlock_fn(ap_lock);
		ap_deref_fn(ap);
		att_destroyable_fn(att);

		att_write_unlock_fn(att_lock, at_lock);
		att_deref_fn(att);
		return 0;
	}

	if (needs_middle_lookup) {
		void *remaining_vmr = lookup_range_fn(vm,
				middle_lookup_vaddr - 1, middle_lookup_vaddr);
		unsigned long range_start = remaining_vmr ?
			*(unsigned long *)((char *)remaining_vmr +
				offsets->range_start_offset) : 0;
		int private_matches = remaining_vmr &&
			*(void **)((char *)remaining_vmr +
				offsets->range_private_data_offset) == *vmr_privatep;

		if (xpmem_range_private_invalid_result(remaining_vmr != NULL,
				range_start, middle_lookup_vaddr,
				private_matches)) {
			att_write_unlock_fn(att_lock, at_lock);
			att_deref_fn(att);
			return 0;
		}
		*(void **)((char *)remaining_vmr +
				offsets->range_private_data_offset) = NULL;
	}

	{
		void *remaining_vmr = lookup_range_fn(vm, remaining_vaddr,
				remaining_vaddr + 1);
		unsigned long range_start = remaining_vmr ?
			*(unsigned long *)((char *)remaining_vmr +
				offsets->range_start_offset) : 0;
		int private_matches = remaining_vmr &&
			*(void **)((char *)remaining_vmr +
				offsets->range_private_data_offset) == *vmr_privatep;

		if (!xpmem_range_private_invalid_result(remaining_vmr != NULL,
				range_start, remaining_vaddr, private_matches)) {
			unsigned long remaining_start =
				*(unsigned long *)((char *)remaining_vmr +
					offsets->range_start_offset);
			unsigned long remaining_end =
				*(unsigned long *)((char *)remaining_vmr +
					offsets->range_end_offset);

			*(unsigned long *)((char *)att +
					offsets->att_at_vaddr_offset) =
				remaining_start;
			*(size_t *)((char *)att +
					offsets->att_at_size_offset) =
				remaining_end - remaining_start;
			*vmr_privatep = NULL;
		}
	}

	att_write_unlock_fn(att_lock, at_lock);
	att_deref_fn(att);
	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_remove_process_range_body_result(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp,
		const struct xpmem_remove_process_range_offsets *offsets,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_next_range_fn_t next_range_fn,
		xpmem_split_range_fn_t split_range_fn,
		xpmem_range_action_fn_t remove_private_fn,
		xpmem_range_action_fn_t free_range_fn,
		xpmem_remove_process_range_log_fn_t log_fn)
{
	void *range;
	void *next;
	int ro_freed = 0;

	if (!vm || !offsets || !lookup_range_fn || !next_range_fn ||
			!split_range_fn || !remove_private_fn || !free_range_fn ||
			!log_fn) {
		return -EINVAL;
	}

	next = lookup_range_fn(vm, start, end);
	while ((range = next) &&
			*(unsigned long *)((char *)range +
				offsets->range_start_offset) < end) {
		int split_start;
		int split_end;
		int range_ro_freed;
		int remove_private;
		int ret;

		next = next_range_fn(vm, range);

		ret = xpmem_remove_range_step_result(
				*(unsigned long *)((char *)range +
					offsets->range_start_offset),
				*(unsigned long *)((char *)range +
					offsets->range_end_offset),
				start, end,
				*(unsigned long *)((char *)range +
					offsets->range_flag_offset),
				*(void **)((char *)range +
					offsets->range_private_data_offset) != NULL,
				&split_start, &split_end, &range_ro_freed,
				&remove_private);
		if (ret) {
			return ret;
		}

		if (split_start) {
			void *new_range = NULL;

			ret = split_range_fn(vm, range, start, &new_range);
			if (ret) {
				log_fn(vm, start, end, ret, 0);
				return ret;
			}
			if (!new_range) {
				return -EINVAL;
			}
			range = new_range;
		}

		if (split_end) {
			ret = split_range_fn(vm, range, end, NULL);
			if (ret) {
				log_fn(vm, start, end, ret, 0);
				return ret;
			}
		}

		if (range_ro_freed) {
			ro_freed = 1;
		}

		if (remove_private) {
			(void)remove_private_fn(vm, range);
		}

		ret = free_range_fn(vm, range);
		if (ret) {
			log_fn(vm, start, end, ret, 1);
			return ret;
		}
	}

	if (ro_freedp) {
		*ro_freedp = ro_freed;
	}

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_free_process_range_body_result(void *vm, void *range,
		const struct xpmem_free_process_range_offsets *offsets,
		xpmem_spin_fn_t lock_fn,
		xpmem_spin_fn_t unlock_fn,
		xpmem_pt_clear_range_fn_t pt_clear_fn,
		xpmem_ptr_void_fn_t memobj_unref_fn,
		xpmem_range_erase_fn_t erase_fn,
		xpmem_ptr_void_fn_t free_fn,
		xpmem_free_process_range_log_fn_t log_fn)
{
	void *asp;
	void *page_table;
	void *page_table_lock;
	void **cache;
	void *memobj;
	unsigned long start;
	unsigned long end;
	int error;
	size_t i;

	if (!vm || !range || !offsets || !lock_fn || !unlock_fn ||
			!pt_clear_fn || !memobj_unref_fn || !erase_fn ||
			!free_fn || !log_fn) {
		return -EINVAL;
	}

	start = *(unsigned long *)((char *)range +
			offsets->range_start_offset);
	end = *(unsigned long *)((char *)range + offsets->range_end_offset);
	asp = *(void **)((char *)vm + offsets->vm_address_space_offset);
	if (!asp) {
		return -EINVAL;
	}
	page_table = *(void **)((char *)asp +
			offsets->address_space_page_table_offset);
	page_table_lock = (char *)vm + offsets->vm_page_table_lock_offset;

	lock_fn(page_table_lock);
	error = pt_clear_fn(page_table, vm, start, end);
	unlock_fn(page_table_lock);
	if (error && error != -ENOENT) {
		log_fn(1, vm, range, start, end, error);
	}

	memobj = *(void **)((char *)range + offsets->range_memobj_offset);
	if (memobj) {
		memobj_unref_fn(memobj);
	}

	erase_fn((char *)vm + offsets->vm_range_tree_offset,
			(char *)range + offsets->range_rb_node_offset);

	cache = (void **)((char *)vm + offsets->vm_range_cache_offset);
	for (i = 0; i < offsets->vm_range_cache_count; i++) {
		if (cache[i] == range) {
			cache[i] = NULL;
		}
	}

	free_fn(range);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_update_process_page_table_body_result(void *vm, void *vmr,
		int current_pid, int page_in_remote_on_attach,
		const struct xpmem_update_page_table_offsets *offsets,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_ptr_void_fn_t ap_ref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_bug_on_fn_t bug_on_fn,
		xpmem_fault_range_page_in_fn_t fault_fn,
		xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn,
		xpmem_pte_present_fn_t pte_present_fn,
		xpmem_update_page_table_log_fn_t log_fn)
{
	void *att;
	void *ap;
	void *ap_tg;
	void *seg;
	void *seg_tg;
	void *asp;
	void *page_table;
	unsigned long start;
	unsigned long end;
	unsigned long vaddr;
	int pgshift;
	int ret = 0;

	if (!vm || !vmr || !offsets || !att_ref_fn || !att_deref_fn ||
			!ap_ref_fn || !ap_deref_fn || !tg_ref_fn ||
			!tg_deref_fn || !seg_ref_fn || !seg_deref_fn ||
			!bug_on_fn || !fault_fn || !pt_lookup_pte_fn ||
			!pte_present_fn || !log_fn) {
		return -EINVAL;
	}

	att = *(void **)((char *)vmr + offsets->range_private_data_offset);
	if (!att) {
		return -EFAULT;
	}

	att_ref_fn(att);
	ap = *(void **)((char *)att + offsets->att_ap_offset);
	if (!ap) {
		att_deref_fn(att);
		return -EINVAL;
	}
	ap_ref_fn(ap);
	ap_tg = *(void **)((char *)ap + offsets->ap_tg_offset);
	if (!ap_tg) {
		att_deref_fn(att);
		ap_deref_fn(ap);
		return -EINVAL;
	}
	tg_ref_fn(ap_tg);

	ret = xpmem_two_destroying_error_result(
			*(int *)((char *)ap + offsets->ap_flags_offset),
			*(int *)((char *)ap_tg + offsets->tg_flags_offset),
			-EFAULT);
	if (ret) {
		att_deref_fn(att);
		ap_deref_fn(ap);
		tg_deref_fn(ap_tg);
		return ret;
	}

	bug_on_fn(*(int *)((char *)ap_tg + offsets->tg_tgid_offset) !=
			current_pid);
	bug_on_fn(*(int *)((char *)ap + offsets->ap_mode_offset) !=
			XPMEM_RDWR);

	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	if (!seg) {
		att_deref_fn(att);
		ap_deref_fn(ap);
		tg_deref_fn(ap_tg);
		return -EINVAL;
	}
	seg_ref_fn(seg);
	seg_tg = *(void **)((char *)seg + offsets->seg_tg_offset);
	if (!seg_tg) {
		seg_deref_fn(seg);
		att_deref_fn(att);
		ap_deref_fn(ap);
		tg_deref_fn(ap_tg);
		return -EINVAL;
	}
	tg_ref_fn(seg_tg);

	ret = xpmem_two_destroying_error_result(
			*(int *)((char *)seg + offsets->seg_flags_offset),
			*(int *)((char *)seg_tg + offsets->tg_flags_offset),
			-ENOENT);
	if (ret) {
		goto out_2;
	}

	start = *(unsigned long *)((char *)vmr + offsets->range_start_offset);
	end = *(unsigned long *)((char *)vmr + offsets->range_end_offset);
	*(unsigned long *)((char *)att + offsets->att_at_vaddr_offset) =
		start;
	*(void **)((char *)att + offsets->att_at_vmr_offset) = vmr;

	if (xpmem_three_destroying_error_result(
			*(int *)((char *)att + offsets->att_flags_offset),
			*(int *)((char *)ap_tg + offsets->tg_flags_offset),
			*(int *)((char *)seg_tg + offsets->tg_flags_offset),
			1)) {
		ret = 0;
		goto out_2;
	}

	asp = *(void **)((char *)vm + offsets->vm_address_space_offset);
	if (!asp) {
		ret = -EINVAL;
		goto out_2;
	}
	page_table = *(void **)((char *)asp +
			offsets->address_space_page_table_offset);
	pgshift = *(int *)((char *)vmr + offsets->range_pgshift_offset);

	for (vaddr = start; vaddr < end;) {
		void *pte;
		size_t pgsize = 0;

		ret = fault_fn(vm, vmr, vaddr, 0, page_in_remote_on_attach);
		if (ret) {
			log_fn(1, vm, vmr, vaddr, ret);
		}

		pte = pt_lookup_pte_fn(page_table, vaddr, pgshift, NULL,
				&pgsize, NULL);
		if (!pte || !pte_present_fn(pte)) {
			pgsize = PAGE_SIZE;
		}
		vaddr += pgsize;
	}

out_2:
	tg_deref_fn(seg_tg);
	seg_deref_fn(seg);
	att_deref_fn(att);
	ap_deref_fn(ap);
	tg_deref_fn(ap_tg);

	return ret;
}

static int
xpmem_fault_body_out(int ret, void *ap, void *ap_tg, void *seg_tg,
		void *seg, void *att, xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t att_deref_fn)
{
	ap_deref_fn(ap);
	tg_deref_fn(ap_tg);
	tg_deref_fn(seg_tg);
	seg_deref_fn(seg);
	att_deref_fn(att);

	return ret;
}

static int
xpmem_fault_map_present_page_body(void *vm, void *vmr, unsigned long vaddr,
		unsigned long reason, int page_in_remote, void *current_vm,
		const struct xpmem_fault_process_range_offsets *offsets,
		void *att, void *seg_tg, unsigned long seg_vaddr,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_vaddr_to_pte_fn_t vaddr_to_pte_fn,
		xpmem_pte_present_fn_t pte_present_fn,
		xpmem_pte_phys_fn_t pte_phys_fn,
		xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn,
		xpmem_get_smaller_page_size_fn_t smaller_page_fn,
		xpmem_adjust_page_size_fn_t adjust_page_fn,
		xpmem_vrflag_to_ptattr_fn_t vrflag_to_ptattr_fn,
		xpmem_pgsize_contiguous_fn_t pgsize_contiguous_fn,
		xpmem_pt_set_pte_fn_t pt_set_pte_fn,
		xpmem_pt_set_range_fn_t pt_set_range_fn,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_flush_tlb_single_fn_t flush_tlb_single_fn,
		xpmem_fault_log_fn_t log_fn)
{
	const int log_smaller_page_error = 3;
	const int log_pte_mismatch = 4;
	const int log_set_pte_error = 5;
	const int log_set_range_error = 6;
	void *seg_vm;
	void *seg_proc;
	void *seg_pte;
	void *address_space;
	void *page_table;
	void *att_pte;
	void *att_pgaddr;
	size_t seg_pgsize = 0;
	size_t att_pgsize = 0;
	unsigned long seg_phys = 0;
	unsigned long seg_phys_plus_off;
	unsigned long seg_phys_aligned;
	unsigned long att_attr;
	int att_p2align = 0;
	int pgshift;
	int remote;
	int ret;

	seg_vm = *(void **)((char *)seg_tg + offsets->tg_vm_offset);
	if (!seg_vm) {
		return -EINVAL;
	}
	seg_proc = *(void **)((char *)seg_vm + offsets->vm_proc_offset);
	if (!seg_proc) {
		return -EINVAL;
	}

	remote = seg_vm != current_vm;
	if (remote) {
		read_lock_noirq_fn((char *)seg_vm +
				offsets->vm_memory_range_lock_offset);
	}

	if (!xpmem_straight_phys_result(seg_vaddr,
			(unsigned long)*(void **)((char *)seg_proc +
				offsets->proc_straight_va_offset),
			*(size_t *)((char *)seg_proc +
				offsets->proc_straight_len_offset),
			*(unsigned long *)((char *)seg_proc +
				offsets->proc_straight_pa_offset),
			&seg_phys, &seg_pgsize)) {
		seg_pte = vaddr_to_pte_fn(seg_vm, seg_vaddr, &seg_pgsize);
		ret = xpmem_remote_pte_missing_result(seg_pte != NULL,
				seg_pte && !pte_present_fn(seg_pte),
				page_in_remote);
		if (ret != 1) {
			if (remote) {
				read_unlock_noirq_fn((char *)seg_vm +
					offsets->vm_memory_range_lock_offset);
			}
			return ret;
		}
		seg_phys = pte_phys_fn(seg_pte);
	}

	seg_phys_plus_off = xpmem_seg_phys_plus_off_result(seg_phys,
			seg_pgsize, seg_vaddr);
	if (remote) {
		read_unlock_noirq_fn((char *)seg_vm +
				offsets->vm_memory_range_lock_offset);
	}

	address_space = *(void **)((char *)vm +
			offsets->vm_address_space_offset);
	if (!address_space) {
		return -EINVAL;
	}
	page_table = *(void **)((char *)address_space +
			offsets->address_space_page_table_offset);
	pgshift = *(int *)((char *)vmr + offsets->range_pgshift_offset);
	att_pte = pt_lookup_pte_fn(page_table, vaddr, pgshift, &att_pgaddr,
			&att_pgsize, &att_p2align);

	while (!xpmem_att_page_fits_result((unsigned long)att_pgaddr,
			att_pgsize,
			*(unsigned long *)((char *)vmr +
				offsets->range_start_offset),
			*(unsigned long *)((char *)vmr +
				offsets->range_end_offset),
			seg_pgsize)) {
		att_pte = NULL;
		ret = smaller_page_fn(att_pgsize, &att_pgsize, &att_p2align);
		if (ret) {
			log_fn(log_smaller_page_error,
					*(unsigned long *)((char *)vmr +
						offsets->range_start_offset),
					*(unsigned long *)((char *)vmr +
						offsets->range_end_offset),
					0, att_pgsize, ret);
			return ret;
		}
		att_pgaddr = (void *)(vaddr & ~(att_pgsize - 1));
	}

	adjust_page_fn(page_table, vaddr, att_pte, &att_pgaddr, &att_pgsize);
	seg_phys_aligned = seg_phys_plus_off & ~(att_pgsize - 1);
	att_attr = vrflag_to_ptattr_fn(
			*(unsigned long *)((char *)vmr +
				offsets->range_flag_offset),
			reason);

	if (att_pte && pte_present_fn(att_pte)) {
		unsigned long att_phys = pte_phys_fn(att_pte);

		ret = xpmem_pte_mismatch_result(att_phys, seg_phys_aligned);
		if (ret) {
			log_fn(log_pte_mismatch, vaddr, att_phys,
					seg_phys_aligned, 0, ret);
		}
		if (page_in_remote) {
			atomic_dec_fn((char *)seg_tg +
					offsets->tg_n_pinned_offset);
		}
		return ret;
	}

	if (att_pte && !pgsize_contiguous_fn(att_pgsize)) {
		ret = pt_set_pte_fn(page_table, att_pte, att_pgsize,
				seg_phys_aligned, att_attr);
		if (ret) {
			log_fn(log_set_pte_error, vaddr, seg_phys_aligned,
					0, att_pgsize, ret);
			return -EFAULT;
		}
	}
	else {
		unsigned long start = (unsigned long)att_pgaddr;

		ret = pt_set_range_fn(page_table, vm, start,
				start + att_pgsize, seg_phys_aligned, att_attr,
				pgshift, vmr, 1);
		if (ret) {
			log_fn(log_set_range_error, vaddr, seg_phys_aligned,
					0, att_pgsize, ret);
			return -EFAULT;
		}
	}

	*(int *)((char *)att + offsets->att_flags_offset) |=
		XPMEM_FLAG_VALIDPTEs;
	flush_tlb_single_fn(vaddr);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_fault_process_memory_range_body_result(void *vm, void *vmr,
		unsigned long vaddr, unsigned long reason, int page_in_remote,
		int current_pid, void *current_vm,
		const struct xpmem_fault_process_range_offsets *offsets,
		const struct xpmem_fault_process_range_ops *ops)
{
	const int log_destroying = 1;
	const int log_bad_vaddr = 2;
	void *att;
	void *ap;
	void *ap_tg;
	void *seg;
	void *seg_tg;
	unsigned long seg_vaddr = 0;
	int ret;

	if (!vm || !vmr || !offsets || !ops ||
			!ops->att_ref_fn || !ops->att_deref_fn ||
			!ops->ap_ref_fn || !ops->ap_deref_fn ||
			!ops->tg_ref_fn || !ops->tg_deref_fn ||
			!ops->seg_ref_fn || !ops->seg_deref_fn ||
			!ops->bug_on_fn || !ops->ensure_valid_fn ||
			!ops->read_lock_noirq_fn ||
			!ops->read_unlock_noirq_fn ||
			!ops->vaddr_to_pte_fn || !ops->pte_present_fn ||
			!ops->pte_phys_fn || !ops->pt_lookup_pte_fn ||
			!ops->smaller_page_fn || !ops->adjust_page_fn ||
			!ops->vrflag_to_ptattr_fn ||
			!ops->pgsize_contiguous_fn || !ops->pt_set_pte_fn ||
			!ops->pt_set_range_fn || !ops->atomic_dec_fn ||
			!ops->flush_tlb_single_fn || !ops->log_fn) {
		return -EINVAL;
	}

	att = *(void **)((char *)vmr + offsets->range_private_data_offset);
	if (!att) {
		return -EFAULT;
	}

	ops->att_ref_fn(att);
	ap = *(void **)((char *)att + offsets->att_ap_offset);
	if (!ap) {
		ops->att_deref_fn(att);
		return -EINVAL;
	}
	ops->ap_ref_fn(ap);
	ap_tg = *(void **)((char *)ap + offsets->ap_tg_offset);
	if (!ap_tg) {
		ops->att_deref_fn(att);
		ops->ap_deref_fn(ap);
		return -EINVAL;
	}
	ops->tg_ref_fn(ap_tg);

	ret = xpmem_two_destroying_error_result(
			*(int *)((char *)ap + offsets->ap_flags_offset),
			*(int *)((char *)ap_tg + offsets->tg_flags_offset),
			-EFAULT);
	if (ret) {
		ops->att_deref_fn(att);
		ops->ap_deref_fn(ap);
		ops->tg_deref_fn(ap_tg);
		return ret;
	}

	ops->bug_on_fn(*(int *)((char *)ap_tg + offsets->tg_tgid_offset) !=
			current_pid);
	ops->bug_on_fn(*(int *)((char *)ap + offsets->ap_mode_offset) !=
			XPMEM_RDWR);

	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	if (!seg) {
		ops->att_deref_fn(att);
		ops->ap_deref_fn(ap);
		ops->tg_deref_fn(ap_tg);
		return -EINVAL;
	}
	ops->seg_ref_fn(seg);
	seg_tg = *(void **)((char *)seg + offsets->seg_tg_offset);
	if (!seg_tg) {
		ops->seg_deref_fn(seg);
		ops->att_deref_fn(att);
		ops->ap_deref_fn(ap);
		ops->tg_deref_fn(ap_tg);
		return -EINVAL;
	}
	ops->tg_ref_fn(seg_tg);

	ret = xpmem_two_destroying_error_result(
			*(int *)((char *)seg + offsets->seg_flags_offset),
			*(int *)((char *)seg_tg + offsets->tg_flags_offset),
			-EFAULT);
	if (ret) {
		return xpmem_fault_body_out(ret, ap, ap_tg, seg_tg, seg, att,
				ops->ap_deref_fn, ops->tg_deref_fn,
				ops->seg_deref_fn, ops->att_deref_fn);
	}

	ret = xpmem_three_destroying_error_result(
			*(int *)((char *)att + offsets->att_flags_offset),
			*(int *)((char *)ap_tg + offsets->tg_flags_offset),
			*(int *)((char *)seg_tg + offsets->tg_flags_offset),
			-EFAULT);
	if (ret) {
		ops->log_fn(log_destroying, vaddr, 0, 0, 0, ret);
		goto out;
	}

	ret = xpmem_fault_vaddr_result(vaddr,
			*(unsigned long *)((char *)att +
				offsets->att_at_vaddr_offset),
			*(size_t *)((char *)att + offsets->att_at_size_offset),
			*(unsigned long *)((char *)att +
				offsets->att_vaddr_offset),
			&seg_vaddr);
	if (ret) {
		ops->log_fn(log_bad_vaddr, vaddr,
				*(unsigned long *)((char *)att +
					offsets->att_at_vaddr_offset),
				0,
				*(size_t *)((char *)att +
					offsets->att_at_size_offset),
				ret);
		goto out;
	}

	ret = ops->ensure_valid_fn(seg, seg_vaddr, page_in_remote);
	if (!ret) {
		ret = xpmem_fault_map_present_page_body(vm, vmr, vaddr,
				reason, page_in_remote, current_vm, offsets,
				att, seg_tg, seg_vaddr,
				ops->read_lock_noirq_fn,
				ops->read_unlock_noirq_fn,
				ops->vaddr_to_pte_fn, ops->pte_present_fn,
				ops->pte_phys_fn, ops->pt_lookup_pte_fn,
				ops->smaller_page_fn, ops->adjust_page_fn,
				ops->vrflag_to_ptattr_fn,
				ops->pgsize_contiguous_fn,
				ops->pt_set_pte_fn, ops->pt_set_range_fn,
				ops->atomic_dec_fn,
				ops->flush_tlb_single_fn, ops->log_fn);
	}

out:
	return xpmem_fault_body_out(ret, ap, ap_tg, seg_tg, seg, att,
			ops->ap_deref_fn, ops->tg_deref_fn,
			ops->seg_deref_fn, ops->att_deref_fn);
}

XPMEM_HELPER_SCOPE int
xpmem_attach_body_result(void *mckfd, long apid, off_t offset, size_t size,
		unsigned long vaddr, unsigned long *at_vaddrp, int current_pid,
		void *current_vm, int fjmpi_workaround,
		unsigned long prot_flags, unsigned long map_shared,
		unsigned long map_fixed, unsigned long map_anonymous,
		unsigned long vr_xpmem,
		const struct xpmem_attach_offsets *offsets,
		xpmem_id_ref_fn_t tg_ref_by_apid_fn,
		xpmem_ref_by_id_fn_t ap_ref_by_apid_fn,
		xpmem_ptr_void_fn_t seg_ref_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_ptr_void_fn_t ap_deref_fn,
		xpmem_validate_access_fn_t validate_access_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t rwspin_init_fn,
		xpmem_list_fn_t list_init_fn,
		xpmem_ptr_void_fn_t att_not_destroyable_fn,
		xpmem_ptr_void_fn_t att_ref_fn,
		xpmem_ptr_void_fn_t att_deref_fn,
		xpmem_rwspin_lock_fn_t att_write_lock_fn,
		xpmem_rwspin_unlock_fn_t att_write_unlock_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_next_range_fn_t next_range_fn,
		xpmem_mmap_fn_t mmap_fn,
		xpmem_list_fn_t list_del_init_fn,
		xpmem_ptr_void_fn_t att_destroyable_fn)
{
	void *ap_tg;
	void *ap;
	void *seg;
	void *seg_tg;
	void *att;
	void *att_lock;
	void *ap_lock;
	unsigned long at_lock;
	unsigned long seg_vaddr = 0;
	unsigned long flags;
	int ret;

	if (!mckfd || !at_vaddrp || !current_vm || !offsets ||
			!tg_ref_by_apid_fn || !ap_ref_by_apid_fn ||
			!seg_ref_fn || !seg_deref_fn || !tg_ref_fn ||
			!tg_deref_fn || !ap_deref_fn ||
			!validate_access_fn || !alloc_fn ||
			!rwspin_init_fn || !list_init_fn ||
			!att_not_destroyable_fn || !att_ref_fn ||
			!att_deref_fn || !att_write_lock_fn ||
			!att_write_unlock_fn || !spin_lock_fn ||
			!spin_unlock_fn || !list_add_tail_fn ||
			!read_lock_noirq_fn || !read_unlock_noirq_fn ||
			!lookup_range_fn || !next_range_fn || !mmap_fn ||
			!list_del_init_fn || !att_destroyable_fn) {
		return -EINVAL;
	}

	ret = xpmem_attach_initial_policy_result(apid, offset, vaddr, size,
			fjmpi_workaround, &size);
	if (ret) {
		return ret;
	}

	ap_tg = tg_ref_by_apid_fn(apid);
	if (IS_ERR(ap_tg) || !ap_tg) {
		return PTR_ERR(ap_tg);
	}

	ap = ap_ref_by_apid_fn(ap_tg, apid);
	if (IS_ERR(ap) || !ap) {
		tg_deref_fn(ap_tg);
		return PTR_ERR(ap);
	}

	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	if (!seg) {
		ap_deref_fn(ap);
		tg_deref_fn(ap_tg);
		return -EINVAL;
	}
	seg_ref_fn(seg);
	seg_tg = *(void **)((char *)seg + offsets->seg_tg_offset);
	if (!seg_tg) {
		ap_deref_fn(ap);
		tg_deref_fn(ap_tg);
		seg_deref_fn(seg);
		return -EINVAL;
	}
	tg_ref_fn(seg_tg);

	ret = xpmem_attach_destroying_result(
			*(int *)((char *)seg + offsets->seg_flags_offset),
			*(int *)((char *)seg_tg + offsets->tg_flags_offset));
	if (ret) {
		goto out_1;
	}

	ret = validate_access_fn(ap, offset, size, XPMEM_RDWR, &seg_vaddr);
	if (ret) {
		goto out_1;
	}

	size += offset_in_page(seg_vaddr);
	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	ret = xpmem_attach_overlap_result(current_pid,
			*(int *)((char *)seg_tg + offsets->tg_tgid_offset),
			vaddr, size, seg_vaddr);
	if (ret) {
		goto out_1;
	}

	att = alloc_fn(offsets->att_size);
	if (!att) {
		ret = -ENOMEM;
		goto out_1;
	}
	memset(att, 0, offsets->att_size);

	att_lock = (char *)att + offsets->att_at_lock_offset;
	rwspin_init_fn(att_lock);
	*(unsigned long *)((char *)att + offsets->att_vaddr_offset) =
		seg_vaddr;
	*(size_t *)((char *)att + offsets->att_at_size_offset) = size;
	*(void **)((char *)att + offsets->att_ap_offset) = ap;
	list_init_fn((char *)att + offsets->att_att_list_offset);
	*(void **)((char *)att + offsets->att_vm_offset) = current_vm;
	att_not_destroyable_fn(att);
	att_ref_fn(att);

	at_lock = att_write_lock_fn(att_lock);

	ap_lock = (char *)ap + offsets->ap_lock_offset;
	spin_lock_fn(ap_lock);
	list_add_tail_fn((char *)att + offsets->att_att_list_offset,
			(char *)ap + offsets->ap_att_list_offset);
	ret = xpmem_destroying_error_result(
			*(int *)((char *)ap + offsets->ap_flags_offset),
			-ENOENT);
	if (ret) {
		spin_unlock_fn(ap_lock);
	} else {
		spin_unlock_fn(ap_lock);

		flags = map_shared;
		if (vaddr) {
			flags |= map_fixed;
		}

		if (flags & map_fixed) {
			void *range;
			void *range_lock = (char *)current_vm +
				offsets->vm_memory_range_lock_offset;
			unsigned long end = vaddr + size;

			read_lock_noirq_fn(range_lock);
			range = lookup_range_fn(current_vm, vaddr, end);
			for (; range &&
					*(unsigned long *)((char *)range +
						offsets->range_start_offset) <
						end;
					range = next_range_fn(current_vm,
						range)) {
				if (*(void **)((char *)range +
						offsets->range_private_data_offset)) {
					ret = -EINVAL;
					break;
				}
			}
			read_unlock_noirq_fn(range_lock);
		}

		if (!ret) {
			unsigned long at_vaddr;

			flags |= map_anonymous;
			at_vaddr = mmap_fn(vaddr, size, prot_flags, flags,
					*(int *)((char *)mckfd +
						offsets->mckfd_fd_offset),
					offset, vr_xpmem, att);
			if (IS_ERR((void *)(uintptr_t)at_vaddr)) {
				ret = at_vaddr;
			} else {
				*at_vaddrp = at_vaddr +
					offset_in_page(
						*(unsigned long *)((char *)att +
							offsets->att_vaddr_offset));
			}
		}
	}

	if (ret) {
		int new_flags;
		int *flags_ptr = (int *)((char *)att +
				offsets->att_flags_offset);

		(void)xpmem_begin_destroy_result(*flags_ptr, &new_flags);
		*flags_ptr = new_flags;
		spin_lock_fn(ap_lock);
		list_del_init_fn((char *)att + offsets->att_att_list_offset);
		spin_unlock_fn(ap_lock);
		att_destroyable_fn(att);
	}
	att_write_unlock_fn(att_lock, at_lock);
	att_deref_fn(att);
out_1:
	ap_deref_fn(ap);
	tg_deref_fn(ap_tg);
	seg_deref_fn(seg);
	tg_deref_fn(seg_tg);

	return ret;
}

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

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
pid_t
xpmem_segid_to_tgid(xpmem_segid_t segid)
{
	DBUG_ON(segid <= 0);
	return xpmem_id_to_tgid_result(segid);
}

pid_t
xpmem_apid_to_tgid(xpmem_apid_t apid)
{
	DBUG_ON(apid <= 0);
	return xpmem_id_to_tgid_result(apid);
}

int
xpmem_tg_hashtable_index(pid_t tgid)
{
	int index;

	index = xpmem_tg_hashtable_index_result(tgid);
	XPMEM_DEBUG("return: tgid=%lu, index=%d", tgid, index);

	return index;
}

int
xpmem_ap_hashtable_index(xpmem_apid_t apid)
{
	int index;

	DBUG_ON(apid <= 0);
	index = xpmem_ap_hashtable_index_result(apid);
	XPMEM_DEBUG("return: apid=0x%lx, index=%d", apid, index);

	return index;
}
#endif

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
xpmem_pin_page_body_result(void *tg, void *src_thread, void *src_vm,
		void *current_vm, unsigned long vaddr, int page_in,
		const struct xpmem_pin_page_offsets *offsets,
		xpmem_rwspin_noirq_fn_t read_lock_noirq_fn,
		xpmem_rwspin_noirq_fn_t read_unlock_noirq_fn,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_page_fault_vm_fn_t page_fault_vm_fn,
		xpmem_page_fault_range_fn_t page_fault_range_fn,
		xpmem_atomic_inc_fn_t atomic_inc_fn)
{
	const unsigned long reason = PF_POPULATE | PF_WRITE | PF_USER;

	(void)src_thread;
	if (!tg || !src_vm || !offsets || !read_lock_noirq_fn ||
			!read_unlock_noirq_fn || !lookup_range_fn ||
			!page_fault_vm_fn || !page_fault_range_fn ||
			!atomic_inc_fn) {
		return -EINVAL;
	}

	for (;;) {
		int remote = current_vm != src_vm;
		void *range_lock = (char *)src_vm +
			offsets->vm_memory_range_lock_offset;
		void *range;
		int missing_range;

		if (remote) {
			read_lock_noirq_fn(range_lock);
		}

		range = lookup_range_fn(src_vm, vaddr, vaddr + 1);
		missing_range = !range ||
			*(unsigned long *)((char *)range +
				offsets->range_start_offset) > vaddr;
		if (missing_range) {
			unsigned long stack_start;
			unsigned long stack_end;

			if (remote) {
				read_unlock_noirq_fn(range_lock);
			}

			stack_start = *(unsigned long *)((char *)src_vm +
				offsets->vm_stack_start_offset);
			stack_end = *(unsigned long *)((char *)src_vm +
				offsets->vm_stack_end_offset);
			if (stack_start <= vaddr && stack_end > vaddr) {
				if (page_fault_vm_fn(src_vm, vaddr, reason) < 0) {
					return -ENOENT;
				}
				continue;
			}

			return -ENOENT;
		}

		if (*(void **)((char *)range +
				offsets->range_private_data_offset)) {
			if (remote) {
				read_unlock_noirq_fn(range_lock);
			}
			return -ENOENT;
		}

		if (page_in) {
			int ret = page_fault_range_fn(src_vm, range, vaddr,
					reason);
			if (!ret) {
				atomic_inc_fn((char *)tg +
					offsets->tg_n_pinned_offset);
			}
			if (remote) {
				read_unlock_noirq_fn(range_lock);
			}
			return ret;
		}

		if (remote) {
			read_unlock_noirq_fn(range_lock);
		}
		return 0;
	}
}

XPMEM_HELPER_SCOPE int
xpmem_ensure_valid_page_body_result(void *seg, unsigned long vaddr,
		int page_in,
		const struct xpmem_ensure_valid_page_offsets *offsets,
		xpmem_pin_page_fn_t pin_page_fn)
{
	void *tg;

	if (!seg || !offsets || !pin_page_fn) {
		return -EINVAL;
	}

	if (*(int *)((char *)seg + offsets->seg_flags_offset) &
			XPMEM_FLAG_DESTROYING) {
		return -ENOENT;
	}

	tg = *(void **)((char *)seg + offsets->seg_tg_offset);
	if (!tg) {
		return -EINVAL;
	}

	return pin_page_fn(tg,
			*(void **)((char *)tg +
				offsets->tg_group_leader_offset),
			*(void **)((char *)tg + offsets->tg_vm_offset),
			vaddr, page_in);
}

XPMEM_HELPER_SCOPE void *
xpmem_vaddr_to_pte_body_result(void *vm, unsigned long vaddr,
		size_t *pgsize,
		const struct xpmem_vaddr_to_pte_offsets *offsets,
		xpmem_lookup_range_fn_t lookup_range_fn,
		xpmem_pt_lookup_pte_fn_t pt_lookup_pte_fn)
{
	void *range;
	void *address_space;
	void *page_table;
	void *pte;
	void *base = NULL;
	size_t size = 0;
	int p2align = 0;
	int pgshift;

	if (!vm || !pgsize || !offsets || !lookup_range_fn ||
			!pt_lookup_pte_fn) {
		return NULL;
	}

	range = lookup_range_fn(vm, vaddr, vaddr + 1);
	if (!range) {
		return NULL;
	}

	address_space = *(void **)((char *)vm +
			offsets->vm_address_space_offset);
	if (!address_space) {
		return NULL;
	}
	page_table = *(void **)((char *)address_space +
			offsets->address_space_page_table_offset);
	pgshift = *(int *)((char *)range + offsets->range_pgshift_offset);
	pte = pt_lookup_pte_fn(page_table, vaddr, pgshift, &base, &size,
			&p2align);
	if (pte) {
		*pgsize = size;
	}
	else {
		*pgsize = PAGE_SIZE;
	}

	return pte;
}

XPMEM_HELPER_SCOPE int
xpmem_unpin_pages_body_result(void *seg, void *vm, unsigned long vaddr,
		size_t size, const struct xpmem_unpin_pages_offsets *offsets,
		xpmem_vaddr_to_pte_fn_t vaddr_to_pte_fn,
		xpmem_pte_present_fn_t pte_present_fn,
		xpmem_atomic_sub_fn_t atomic_sub_fn)
{
	int n_pgs_unpinned = 0;
	size_t vsize = 0;
	unsigned long end = vaddr + size;
	void *tg;

	if (!seg || !vm || !offsets || !vaddr_to_pte_fn ||
			!pte_present_fn || !atomic_sub_fn) {
		return -EINVAL;
	}

	vaddr &= PAGE_MASK;
	while (vaddr < end) {
		unsigned long next_vaddr;
		int unpinned;
		void *pte;

		pte = vaddr_to_pte_fn(vm, vaddr, &vsize);
		xpmem_unpin_step_result(vaddr, vsize,
				pte && pte_present_fn(pte), &next_vaddr,
				&unpinned);
		if (unpinned) {
			n_pgs_unpinned++;
		}
		vaddr = next_vaddr;
	}

	tg = *(void **)((char *)seg + offsets->seg_tg_offset);
	if (!tg) {
		return -EINVAL;
	}
	atomic_sub_fn(n_pgs_unpinned,
			(char *)tg + offsets->tg_n_pinned_offset);

	return n_pgs_unpinned;
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

XPMEM_HELPER_SCOPE void *
xpmem_tg_ref_by_tgid_nolock_body_result(void *part, int tgid, int index,
		int return_destroying,
		const struct xpmem_tg_lookup_offsets *offsets,
		xpmem_ptr_void_fn_t tg_ref_fn)
{
	void *hashlist;
	struct list_head *head;
	struct list_head *entry;

	if (!part || !offsets || !tg_ref_fn || index < 0) {
		return ERR_PTR(-EINVAL);
	}

	hashlist = (char *)part + offsets->part_tg_hashtable_offset +
		(size_t)index * offsets->hashlist_stride;
	head = (struct list_head *)((char *)hashlist +
			offsets->hashlist_list_offset);
	for (entry = head->next; entry != head; entry = entry->next) {
		void *tg = (char *)entry - offsets->tg_hashlist_offset;
		int candidate = *(int *)((char *)tg + offsets->tg_tgid_offset);
		int flags = *(int *)((char *)tg + offsets->tg_flags_offset);
		int lookup = xpmem_object_lookup_decision_result(candidate,
				tgid, flags, return_destroying, 0);

		if (lookup == XPMEM_LOOKUP_TAKE) {
			tg_ref_fn(tg);
			return tg;
		}
	}

	return ERR_PTR(-ENOENT);
}

XPMEM_HELPER_SCOPE void *
xpmem_seg_ref_by_segid_body_result(void *seg_tg, long segid,
		const struct xpmem_seg_lookup_offsets *offsets,
		void *rwlock_node, xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t seg_ref_fn)
{
	void *lock;
	struct list_head *head;
	struct list_head *entry;

	if (!seg_tg || !offsets || !rwlock_node || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !seg_ref_fn) {
		return ERR_PTR(-EINVAL);
	}

	lock = (char *)seg_tg + offsets->tg_seg_list_lock_offset;
	head = (struct list_head *)((char *)seg_tg +
			offsets->tg_seg_list_offset);
	rwlock_lock_fn(lock, rwlock_node);
	for (entry = head->next; entry != head; entry = entry->next) {
		void *seg = (char *)entry - offsets->seg_list_offset;
		long candidate = *(long *)((char *)seg +
				offsets->seg_segid_offset);
		int flags = *(int *)((char *)seg + offsets->seg_flags_offset);
		int lookup = xpmem_object_lookup_decision_result(candidate,
				segid, flags, 0, 0);

		if (lookup == XPMEM_LOOKUP_TAKE) {
			seg_ref_fn(seg);
			rwlock_unlock_fn(lock, rwlock_node);
			return seg;
		}
	}
	rwlock_unlock_fn(lock, rwlock_node);

	return ERR_PTR(-ENOENT);
}

XPMEM_HELPER_SCOPE void *
xpmem_ap_ref_by_apid_body_result(void *ap_tg, long apid,
		const struct xpmem_ap_lookup_offsets *offsets,
		void *rwlock_node, xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t ap_ref_fn)
{
	int index;
	void *hashlist;
	void *lock;
	struct list_head *head;
	struct list_head *entry;

	if (!ap_tg || !offsets || !rwlock_node || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !ap_ref_fn) {
		return ERR_PTR(-EINVAL);
	}

	index = xpmem_ap_hashtable_index_result(apid);
	if (index < 0) {
		return ERR_PTR(-EINVAL);
	}
	hashlist = (char *)ap_tg + offsets->tg_ap_hashtable_offset +
		(size_t)index * offsets->hashlist_stride;
	lock = (char *)hashlist + offsets->hashlist_lock_offset;
	head = (struct list_head *)((char *)hashlist +
			offsets->hashlist_list_offset);
	rwlock_lock_fn(lock, rwlock_node);
	for (entry = head->next; entry != head; entry = entry->next) {
		void *ap = (char *)entry - offsets->ap_hashlist_offset;
		long candidate = *(long *)((char *)ap + offsets->ap_apid_offset);
		int flags = *(int *)((char *)ap + offsets->ap_flags_offset);
		int lookup = xpmem_object_lookup_decision_result(candidate,
				apid, flags, 0, 1);

		if (lookup == XPMEM_LOOKUP_TAKE) {
			ap_ref_fn(ap);
			rwlock_unlock_fn(lock, rwlock_node);
			return ap;
		}
		if (lookup == XPMEM_LOOKUP_STOP) {
			break;
		}
	}
	rwlock_unlock_fn(lock, rwlock_node);

	return ERR_PTR(-ENOENT);
}

XPMEM_HELPER_SCOPE int
xpmem_deref_body_result(void *object,
		const struct xpmem_deref_offsets *offsets,
		int require_destroying,
		xpmem_atomic_read_fn_t atomic_read_fn,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_bug_on_fn_t bug_on_fn,
		xpmem_ptr_void_fn_t free_log_fn,
		xpmem_ptr_void_fn_t free_fn)
{
	void *refcnt;
	int flags;

	if (!object || !offsets || !atomic_read_fn || !atomic_dec_fn ||
			!bug_on_fn || !free_fn) {
		return -EINVAL;
	}

	refcnt = (char *)object + offsets->refcnt_offset;
	bug_on_fn(atomic_read_fn(refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(atomic_dec_fn(refcnt))) {
		return 0;
	}

	if (require_destroying) {
		flags = *(int *)((char *)object + offsets->flags_offset);
		bug_on_fn(!(flags & XPMEM_FLAG_DESTROYING));
	}

	if (free_log_fn) {
		free_log_fn(object);
	}
	free_fn(object);

	return 1;
}

XPMEM_HELPER_SCOPE long
xpmem_make_object_id_body_result(void *tg,
		const struct xpmem_make_id_offsets *offsets,
		xpmem_atomic_inc_fn_t atomic_inc_fn,
		xpmem_atomic_dec_fn_t atomic_dec_fn,
		xpmem_bug_on_fn_t bug_on_fn)
{
	void *uniq_counter;
	long id = 0;
	int uniq;
	int tgid;
	int ret;

	if (!tg || !offsets || !atomic_inc_fn || !atomic_dec_fn ||
			!bug_on_fn) {
		return -EINVAL;
	}

	uniq_counter = (char *)tg + offsets->tg_uniq_offset;
	uniq = atomic_inc_fn(uniq_counter);
	tgid = *(int *)((char *)tg + offsets->tg_tgid_offset);
	ret = xpmem_make_id_result(tgid, uniq, &id);
	if (ret) {
		atomic_dec_fn(uniq_counter);
		return ret;
	}

	bug_on_fn(id <= 0);

	return id;
}

XPMEM_HELPER_SCOPE int
xpmem_validate_access_body_result(void *ap, void *current_proc,
		off_t offset, size_t size, int mode, unsigned long *vaddr,
		const struct xpmem_validate_access_offsets *offsets)
{
	void *tg;
	void *seg;

	if (!ap || !current_proc || !vaddr || !offsets) {
		return -EINVAL;
	}

	tg = *(void **)((char *)ap + offsets->ap_tg_offset);
	seg = *(void **)((char *)ap + offsets->ap_seg_offset);
	if (!tg || !seg) {
		return -EINVAL;
	}

	return xpmem_validate_access_result(
			*(int *)((char *)current_proc + offsets->proc_pid_offset),
			*(int *)((char *)tg + offsets->tg_tgid_offset),
			*(int *)((char *)ap + offsets->ap_mode_offset),
			*(unsigned long *)((char *)seg +
				offsets->seg_vaddr_offset),
			*(size_t *)((char *)seg + offsets->seg_size_offset),
			offset, size, mode, vaddr);
}

XPMEM_HELPER_SCOPE int
xpmem_is_remote_vm_body_result(void *current_proc, void *vm,
		const struct xpmem_validate_access_offsets *offsets)
{
	void *current_vm;

	if (!current_proc || !offsets) {
		return 1;
	}

	current_vm = *(void **)((char *)current_proc + offsets->proc_vm_offset);

	return current_vm != vm;
}

XPMEM_HELPER_SCOPE int
xpmem_perms_body_result(void *perm, int flag, void *current_proc,
		const struct xpmem_perm_offsets *offsets)
{
	if (!perm || !current_proc || !offsets) {
		return -EINVAL;
	}

	return xpmem_perms_result(
			*(int *)((char *)perm + offsets->perm_uid_offset),
			*(int *)((char *)perm + offsets->perm_gid_offset),
			*(unsigned long *)((char *)perm +
				offsets->perm_mode_offset),
			(short)flag,
			*(int *)((char *)current_proc +
				offsets->proc_ruid_offset),
			*(int *)((char *)current_proc +
				offsets->proc_rgid_offset));
}

XPMEM_HELPER_SCOPE int
xpmem_check_permit_mode_body_result(int flags, void *seg, void *current_proc,
		const struct xpmem_perm_offsets *offsets,
		xpmem_bug_on_fn_t bug_on_fn)
{
	void *tg;

	if (!seg || !current_proc || !offsets || !bug_on_fn) {
		return -EINVAL;
	}

	bug_on_fn(*(int *)((char *)seg + offsets->seg_permit_type_offset) !=
			XPMEM_PERMIT_MODE);
	tg = *(void **)((char *)seg + offsets->seg_tg_offset);
	if (!tg) {
		return -EINVAL;
	}

	return xpmem_check_permit_mode_result(flags,
			*(int *)((char *)tg + offsets->tg_uid_offset),
			*(int *)((char *)tg + offsets->tg_gid_offset),
			*(unsigned long *)((char *)seg +
				offsets->seg_permit_value_offset),
			*(int *)((char *)current_proc +
				offsets->proc_ruid_offset),
			*(int *)((char *)current_proc +
				offsets->proc_rgid_offset));
}

XPMEM_HELPER_SCOPE int
xpmem_make_segment_body_result(unsigned long vaddr, size_t size,
		int permit_type, void *permit_value, long *segidp,
		void *current_proc, const struct xpmem_make_segment_offsets *offsets,
		void *rwlock_node, xpmem_tg_ref_fn_t tg_ref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_object_id_fn_t make_segid_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t spinlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_ptr_void_fn_t seg_not_destroyable_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_bug_on_fn_t bug_on_fn)
{
	void *seg_tg;
	void *seg;
	void *lock;
	long segid;
	int ret;

	if (!segidp || !current_proc || !offsets || !rwlock_node ||
			!tg_ref_fn || !tg_deref_fn || !make_segid_fn ||
			!alloc_fn || !spinlock_init_fn || !list_init_fn ||
			!seg_not_destroyable_fn || !rwlock_lock_fn ||
			!rwlock_unlock_fn || !list_add_tail_fn || !bug_on_fn) {
		return -EINVAL;
	}

	ret = xpmem_make_initial_policy_result(permit_type,
			(unsigned long)(uintptr_t)permit_value, size);
	if (ret) {
		return ret;
	}

	seg_tg = tg_ref_fn(*(int *)((char *)current_proc +
				offsets->proc_pid_offset));
	if (IS_ERR(seg_tg)) {
		bug_on_fn(PTR_ERR(seg_tg) != -ENOENT);
		return -XPMEM_ERRNO_NOPROC;
	}

	ret = xpmem_make_alignment_result(vaddr, size);
	if (ret) {
		tg_deref_fn(seg_tg);
		return ret;
	}

	segid = make_segid_fn(seg_tg);
	if (segid < 0) {
		tg_deref_fn(seg_tg);
		return (int)segid;
	}

	seg = alloc_fn(offsets->seg_size);
	if (!seg) {
		tg_deref_fn(seg_tg);
		return -ENOMEM;
	}
	memset(seg, 0, offsets->seg_size);

	spinlock_init_fn((char *)seg + offsets->seg_lock_offset);
	*(long *)((char *)seg + offsets->seg_segid_offset) = segid;
	*(unsigned long *)((char *)seg + offsets->seg_vaddr_offset) = vaddr;
	*(size_t *)((char *)seg + offsets->seg_size_offset) = size;
	*(int *)((char *)seg + offsets->seg_permit_type_offset) = permit_type;
	*(void **)((char *)seg + offsets->seg_permit_value_offset) =
		permit_value;
	*(void **)((char *)seg + offsets->seg_tg_offset) = seg_tg;
	list_init_fn((char *)seg + offsets->seg_ap_list_offset);
	list_init_fn((char *)seg + offsets->seg_seg_list_offset);
	seg_not_destroyable_fn(seg);

	lock = (char *)seg_tg + offsets->tg_seg_list_lock_offset;
	rwlock_lock_fn(lock, rwlock_node);
	list_add_tail_fn((char *)seg + offsets->seg_seg_list_offset,
			(char *)seg_tg + offsets->tg_seg_list_offset);
	rwlock_unlock_fn(lock, rwlock_node);

	tg_deref_fn(seg_tg);
	*segidp = segid;

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_get_body_result(long segid, int flags, int permit_type,
		void *permit_value, long *apidp, void *current_proc,
		const struct xpmem_get_offsets *offsets, void *rwlock_node,
		xpmem_id_ref_fn_t tg_ref_by_segid_fn,
		xpmem_ref_by_id_fn_t seg_ref_by_segid_fn,
		xpmem_check_permit_fn_t check_permit_fn,
		xpmem_tg_ref_fn_t tg_ref_by_tgid_fn,
		xpmem_object_id_fn_t make_apid_fn,
		xpmem_alloc_fn_t alloc_fn,
		xpmem_ptr_void_fn_t spinlock_init_fn,
		xpmem_ptr_void_fn_t list_init_fn,
		xpmem_ptr_void_fn_t ap_not_destroyable_fn,
		xpmem_spin_fn_t spin_lock_fn,
		xpmem_spin_fn_t spin_unlock_fn,
		xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_list_add_tail_fn_t list_add_tail_fn,
		xpmem_ptr_void_fn_t seg_deref_fn,
		xpmem_ptr_void_fn_t tg_deref_fn,
		xpmem_bug_on_fn_t bug_on_fn)
{
	void *seg_tg;
	void *seg;
	void *ap_tg;
	void *ap;
	void *hashlist;
	void *hash_lock;
	long apid;
	int index;
	int ret;

	if (!apidp || !current_proc || !offsets || !rwlock_node ||
			!tg_ref_by_segid_fn || !seg_ref_by_segid_fn ||
			!check_permit_fn || !tg_ref_by_tgid_fn ||
			!make_apid_fn || !alloc_fn || !spinlock_init_fn ||
			!list_init_fn || !ap_not_destroyable_fn ||
			!spin_lock_fn || !spin_unlock_fn ||
			!rwlock_lock_fn || !rwlock_unlock_fn ||
			!list_add_tail_fn || !seg_deref_fn ||
			!tg_deref_fn || !bug_on_fn) {
		return -EINVAL;
	}

	ret = xpmem_get_policy_result(segid, flags, permit_type,
			permit_value != NULL);
	if (ret) {
		return ret;
	}

	seg_tg = tg_ref_by_segid_fn(segid);
	if (IS_ERR(seg_tg)) {
		return PTR_ERR(seg_tg);
	}

	seg = seg_ref_by_segid_fn(seg_tg, segid);
	if (IS_ERR(seg)) {
		tg_deref_fn(seg_tg);
		return PTR_ERR(seg);
	}

	if (check_permit_fn(flags, seg) != 0) {
		seg_deref_fn(seg);
		tg_deref_fn(seg_tg);
		return -EACCES;
	}

	ap_tg = tg_ref_by_tgid_fn(*(int *)((char *)current_proc +
				offsets->proc_pid_offset));
	if (IS_ERR(ap_tg)) {
		bug_on_fn(PTR_ERR(ap_tg) != -ENOENT);
		seg_deref_fn(seg);
		tg_deref_fn(seg_tg);
		return -XPMEM_ERRNO_NOPROC;
	}
	if (!ap_tg) {
		seg_deref_fn(seg);
		tg_deref_fn(seg_tg);
		return -XPMEM_ERRNO_NOPROC;
	}

	apid = make_apid_fn(ap_tg);
	if (apid < 0) {
		tg_deref_fn(ap_tg);
		seg_deref_fn(seg);
		tg_deref_fn(seg_tg);
		return (int)apid;
	}

	ap = alloc_fn(offsets->ap_size);
	if (!ap) {
		tg_deref_fn(ap_tg);
		seg_deref_fn(seg);
		tg_deref_fn(seg_tg);
		return -ENOMEM;
	}
	memset(ap, 0, offsets->ap_size);

	spinlock_init_fn((char *)ap + offsets->ap_lock_offset);
	*(long *)((char *)ap + offsets->ap_apid_offset) = apid;
	*(int *)((char *)ap + offsets->ap_mode_offset) = flags;
	*(void **)((char *)ap + offsets->ap_seg_offset) = seg;
	*(void **)((char *)ap + offsets->ap_tg_offset) = ap_tg;
	list_init_fn((char *)ap + offsets->ap_att_list_offset);
	list_init_fn((char *)ap + offsets->ap_ap_list_offset);
	list_init_fn((char *)ap + offsets->ap_hashlist_offset);
	ap_not_destroyable_fn(ap);

	spin_lock_fn((char *)seg + offsets->seg_lock_offset);
	list_add_tail_fn((char *)ap + offsets->ap_ap_list_offset,
			(char *)seg + offsets->seg_ap_list_offset);
	spin_unlock_fn((char *)seg + offsets->seg_lock_offset);

	index = xpmem_ap_hashtable_index_result(apid);
	hashlist = (char *)ap_tg + offsets->tg_ap_hashtable_offset +
		index * offsets->hashlist_stride;
	hash_lock = (char *)hashlist + offsets->hashlist_lock_offset;
	rwlock_lock_fn(hash_lock, rwlock_node);
	list_add_tail_fn((char *)ap + offsets->ap_hashlist_offset,
			(char *)hashlist + offsets->hashlist_list_offset);
	rwlock_unlock_fn(hash_lock, rwlock_node);

	tg_deref_fn(ap_tg);
	*apidp = apid;

	return 0;
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

typedef void (*xpmem_destroyable_log_fn_t)(int event);
typedef void (*xpmem_destroyable_deref_fn_t)(void *object);
typedef void *(*xpmem_refcnt_ptr_fn_t)(void *object, int kind);
typedef void (*xpmem_refcnt_log_fn_t)(int kind, int refcnt);
typedef void (*xpmem_refcnt_set_fn_t)(void *counter, int value);
typedef int (*xpmem_refcnt_read_fn_t)(void *counter);
typedef int (*xpmem_refcnt_inc_fn_t)(void *counter);
typedef void (*xpmem_refcnt_bug_on_fn_t)(int condition);
typedef void (*xpmem_tg_lookup_log_fn_t)(int event, int tgid,
		int return_destroying, void *part, void *result);

XPMEM_HELPER_SCOPE int
xpmem_destroyable_wrapper_result(void *object,
		xpmem_destroyable_log_fn_t log_fn,
		xpmem_destroyable_deref_fn_t deref_fn)
{
	if (!deref_fn)
		return -EINVAL;

	if (log_fn)
		log_fn(1);
	deref_fn(object);
	if (log_fn)
		log_fn(2);

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_not_destroyable_wrapper_result(void *object, int kind,
		xpmem_refcnt_ptr_fn_t refcnt_ptr_fn,
		xpmem_refcnt_set_fn_t atomic_set_fn,
		xpmem_refcnt_read_fn_t atomic_read_fn,
		xpmem_refcnt_log_fn_t log_fn)
{
	void *refcnt;

	if (!refcnt_ptr_fn || !atomic_set_fn || !atomic_read_fn)
		return -EINVAL;

	refcnt = refcnt_ptr_fn(object, kind);
	if (!refcnt)
		return -EINVAL;

	atomic_set_fn(refcnt, 1);
	if (log_fn)
		log_fn(kind, atomic_read_fn(refcnt));

	return 0;
}

XPMEM_HELPER_SCOPE int
xpmem_ref_wrapper_result(void *object, int kind,
		xpmem_refcnt_ptr_fn_t refcnt_ptr_fn,
		xpmem_refcnt_read_fn_t atomic_read_fn,
		xpmem_refcnt_inc_fn_t atomic_inc_fn,
		xpmem_refcnt_bug_on_fn_t bug_on_fn)
{
	void *refcnt;

	if (!refcnt_ptr_fn || !atomic_read_fn || !atomic_inc_fn || !bug_on_fn)
		return -EINVAL;

	refcnt = refcnt_ptr_fn(object, kind);
	if (!refcnt)
		return -EINVAL;

	bug_on_fn(atomic_read_fn(refcnt) <= 0);
	atomic_inc_fn(refcnt);

	return 0;
}

XPMEM_HELPER_SCOPE void *
xpmem_tg_ref_by_tgid_wrapper_result(void *part, int tgid,
		int return_destroying, int locked,
		const struct xpmem_tg_lookup_offsets *lookup_offsets,
		const struct xpmem_partition_offsets *partition_offsets,
		void *rwlock_node, xpmem_rwlock_fn_t rwlock_lock_fn,
		xpmem_rwlock_fn_t rwlock_unlock_fn,
		xpmem_ptr_void_fn_t tg_ref_fn,
		xpmem_tg_lookup_log_fn_t log_fn)
{
	void *tg;
	int index;

	if (!lookup_offsets || !tg_ref_fn)
		return ERR_PTR(-EINVAL);
	if (locked && (!partition_offsets || !rwlock_node ||
				!rwlock_lock_fn || !rwlock_unlock_fn))
		return ERR_PTR(-EINVAL);

	if (log_fn)
		log_fn(1, tgid, return_destroying, part, NULL);

	index = xpmem_tg_hashtable_index(tgid);

	if (locked) {
		char *hashlist;
		void *lock;

		if (!part)
			return ERR_PTR(-EINVAL);
		if (log_fn)
			log_fn(2, tgid, return_destroying, part, NULL);

		hashlist = (char *)part + partition_offsets->part_tg_hashtable_offset +
			(size_t)index * partition_offsets->hashlist_stride;
		lock = hashlist + partition_offsets->hashlist_lock_offset;
		rwlock_lock_fn(lock, rwlock_node);
		tg = xpmem_tg_ref_by_tgid_nolock_body_result(part, tgid, index,
				return_destroying, lookup_offsets, tg_ref_fn);
		rwlock_unlock_fn(lock, rwlock_node);
	}
	else {
		tg = xpmem_tg_ref_by_tgid_nolock_body_result(part, tgid, index,
				return_destroying, lookup_offsets, tg_ref_fn);
	}

	if (log_fn)
		log_fn(3, tgid, return_destroying, part, tg);

	return tg;
}

XPMEM_HELPER_SCOPE int
xpmem_is_private_data_result(void *vmr, size_t private_data_offset)
{
	if (!vmr)
		return 0;

	return *(void **)((char *)vmr + private_data_offset) != NULL;
}
#endif

#undef XPMEM_HELPER_SCOPE

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
static long
xpmem_forward_bridge(int syscall_num, void *ctx)
{
	return syscall_generic_forwarding(syscall_num,
			(ihk_mc_user_context_t *)ctx);
}

static void *
xpmem_mckfd_alloc_bridge(size_t size)
{
	return kmalloc_tracked(size, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
}

static long
xpmem_mckfd_lock_bridge(void *lock)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock);
}

static void
xpmem_mckfd_unlock_bridge(void *lock, long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock, irqstate);
}

static int
xpmem_atomic_dec_bridge(void *counter)
{
	return ihk_atomic_dec_return((ihk_atomic_t *)counter);
}

static void
xpmem_kfree_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static void
xpmem_memobj_unref_bridge(void *ptr)
{
	memobj_unref((struct memobj *)ptr);
}

static void
xpmem_mckfd_flush_bridge(void *mckfd)
{
	xpmem_flush((struct mckfd *)mckfd);
}

static void *
xpmem_tg_ref_all_nolock_bridge(int pid)
{
	return xpmem_tg_ref_by_tgid_all_nolock(pid);
}

static void *
xpmem_tg_ref_by_tgid_bridge(int pid)
{
	return xpmem_tg_ref_by_tgid(pid);
}

static void
xpmem_rwlock_writer_lock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_lock((mcs_rwlock_lock_t *)lock,
			(struct mcs_rwlock_node_irqsave *)node);
}

static void
xpmem_rwlock_writer_unlock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_unlock((mcs_rwlock_lock_t *)lock,
			(struct mcs_rwlock_node_irqsave *)node);
}

static void
xpmem_rwlock_init_bridge(void *lock)
{
	mcs_rwlock_init((mcs_rwlock_lock_t *)lock);
}

static void
xpmem_list_del_init_bridge(void *entry)
{
	list_del_init((struct list_head *)entry);
}

static void
xpmem_list_init_bridge(void *entry)
{
	INIT_LIST_HEAD((struct list_head *)entry);
}

static void
xpmem_list_add_tail_bridge(void *entry, void *head)
{
	list_add_tail((struct list_head *)entry, (struct list_head *)head);
}

static void
xpmem_spinlock_init_bridge(void *lock)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock);
}

static void
xpmem_spin_lock_noirq_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void
xpmem_spin_unlock_noirq_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static void
xpmem_release_aps_of_tg_bridge(void *tg)
{
	xpmem_release_aps_of_tg((struct xpmem_thread_group *)tg);
}

static void
xpmem_remove_segs_of_tg_bridge(void *tg)
{
	xpmem_remove_segs_of_tg((struct xpmem_thread_group *)tg);
}

static void
xpmem_destroy_tg_bridge(void *tg)
{
	xpmem_destroy_tg((struct xpmem_thread_group *)tg);
}

static void
xpmem_clear_ptes_bridge(void *seg)
{
	xpmem_clear_PTEs((struct xpmem_segment *)seg);
}

static void
xpmem_seg_destroyable_bridge(void *seg)
{
	xpmem_seg_destroyable((struct xpmem_segment *)seg);
}

static void
xpmem_seg_not_destroyable_bridge(void *seg)
{
	xpmem_seg_not_destroyable((struct xpmem_segment *)seg);
}

static long
xpmem_make_segid_bridge(void *tg)
{
	return xpmem_make_segid((struct xpmem_thread_group *)tg);
}

static long
xpmem_make_apid_bridge(void *tg)
{
	return xpmem_make_apid((struct xpmem_thread_group *)tg);
}

static int
xpmem_check_permit_mode_bridge(int flags, void *seg)
{
	return xpmem_check_permit_mode(flags, (struct xpmem_segment *)seg);
}

static void
xpmem_seg_ref_bridge(void *seg)
{
	xpmem_seg_ref((struct xpmem_segment *)seg);
}

static void
xpmem_seg_deref_log_bridge(void *seg)
{
	XPMEM_DEBUG("kfree(): seg=0x%p", seg);
}

static void
xpmem_tg_deref_log_bridge(void *tg)
{
	XPMEM_DEBUG("kfree(): tg=0x%p", tg);
}

static void
xpmem_tg_destroyable_bridge(void *tg)
{
	xpmem_tg_destroyable((struct xpmem_thread_group *)tg);
}

static void
xpmem_tg_not_destroyable_bridge(void *tg)
{
	xpmem_tg_not_destroyable((struct xpmem_thread_group *)tg);
}

static void
xpmem_ap_destroyable_bridge(void *ap)
{
	xpmem_ap_destroyable((struct xpmem_access_permit *)ap);
}

static void
xpmem_ap_not_destroyable_bridge(void *ap)
{
	xpmem_ap_not_destroyable((struct xpmem_access_permit *)ap);
}

static void
xpmem_ap_ref_bridge(void *ap)
{
	xpmem_ap_ref((struct xpmem_access_permit *)ap);
}

static void
xpmem_ap_deref_log_bridge(void *ap)
{
	XPMEM_DEBUG("kfree(): ap=0x%p", ap);
}

static void
xpmem_att_ref_bridge(void *att)
{
	xpmem_att_ref((struct xpmem_attachment *)att);
}

static void
xpmem_att_not_destroyable_bridge(void *att)
{
	xpmem_att_not_destroyable((struct xpmem_attachment *)att);
}

static void
xpmem_att_deref_log_bridge(void *att)
{
	XPMEM_DEBUG("kfree(): att=0x%p", att);
}

static void
xpmem_att_destroyable_bridge(void *att)
{
	xpmem_att_destroyable((struct xpmem_attachment *)att);
}

static void
xpmem_rwspin_write_lock_noirq_bridge(void *lock)
{
	ihk_rwspinlock_write_lock_noirq((ihk_rwspinlock_t *)lock);
}

static void
xpmem_rwspin_write_unlock_noirq_bridge(void *lock)
{
	ihk_rwspinlock_write_unlock_noirq((ihk_rwspinlock_t *)lock);
}

static void
xpmem_rwspin_read_lock_noirq_bridge(void *lock)
{
	ihk_rwspinlock_read_lock_noirq((ihk_rwspinlock_t *)lock);
}

static void
xpmem_rwspin_read_unlock_noirq_bridge(void *lock)
{
	ihk_rwspinlock_read_unlock_noirq((ihk_rwspinlock_t *)lock);
}

static void
xpmem_rwspinlock_init_bridge(void *lock)
{
	ihk_rwspinlock_init((ihk_rwspinlock_t *)lock);
}

static unsigned long
xpmem_rwspin_write_lock_bridge(void *lock)
{
	return ihk_rwspinlock_write_lock((ihk_rwspinlock_t *)lock);
}

static void
xpmem_rwspin_write_unlock_bridge(void *lock, unsigned long state)
{
	ihk_rwspinlock_write_unlock((ihk_rwspinlock_t *)lock, state);
}

static void *
xpmem_lookup_range_bridge(void *vm, unsigned long start, unsigned long end)
{
	return lookup_process_memory_range((struct process_vm *)vm, start, end);
}

static void *
xpmem_next_range_bridge(void *vm, void *range)
{
	return next_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range);
}

static int
xpmem_validate_access_bridge(void *ap, off_t offset, size_t size, int mode,
		unsigned long *vaddrp)
{
	return xpmem_validate_access((struct xpmem_access_permit *)ap,
			offset, size, mode, vaddrp);
}

static unsigned long
xpmem_do_mmap_bridge(unsigned long addr, size_t len, unsigned long prot,
		unsigned long flags, int fd, off_t offset, unsigned long vm_flags,
		void *private_data)
{
	return do_mmap(addr, len, prot, flags, fd, offset, vm_flags,
			private_data);
}

static int
xpmem_copy_from_user_bridge(void *dst, unsigned long src, size_t size)
{
	return copy_from_user(dst, (void __user *)src, size);
}

static int
xpmem_copy_to_user_bridge(unsigned long dst, const void *src, size_t size)
{
	return copy_to_user((void __user *)dst, (void *)src, size);
}

static int
xpmem_make_bridge(unsigned long vaddr, size_t size, int permit_type,
		void *permit_value, long *segidp)
{
	return xpmem_make(vaddr, size, permit_type, permit_value,
			(xpmem_segid_t *)segidp);
}

static int
xpmem_remove_bridge(long segid)
{
	return xpmem_remove((xpmem_segid_t)segid);
}

static int
xpmem_get_bridge(long segid, int flags, int permit_type, void *permit_value,
		long *apidp)
{
	return xpmem_get((xpmem_segid_t)segid, flags, permit_type,
			permit_value, (xpmem_apid_t *)apidp);
}

static int
xpmem_release_bridge(long apid)
{
	return xpmem_release((xpmem_apid_t)apid);
}

static int
xpmem_attach_bridge(void *mckfd, long apid, off_t offset, size_t size,
		unsigned long vaddr, int fd, int flags,
		unsigned long *at_vaddrp)
{
	return xpmem_attach((struct mckfd *)mckfd, (xpmem_apid_t)apid,
			offset, size, vaddr, fd, flags, at_vaddrp);
}

static int
xpmem_detach_bridge(unsigned long vaddr)
{
	return xpmem_detach(vaddr);
}

static int
xpmem_split_range_bridge(void *vm, void *range, unsigned long addr,
		void **newrangep)
{
	return split_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range, addr,
			(struct vm_range **)newrangep);
}

static int
xpmem_remove_private_range_bridge(void *vm, void *range)
{
	return xpmem_remove_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range);
}

static int
xpmem_free_range_bridge(void *vm, void *range)
{
	return xpmem_free_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range);
}

static void
xpmem_remove_process_range_log_bridge(void *vm, unsigned long start,
		unsigned long end, int error, int free_error)
{
	if (free_error) {
		ekprintf("xpmem_remove_process_range(%p,%lx,%lx): ERROR: "
			"free failed %d\n", vm, start, end, error);
	} else {
		ekprintf("xpmem_remove_process_range(%p,%lx,%lx): ERROR: "
			"split failed %d\n", vm, start, end, error);
	}
}

static int
xpmem_pt_clear_range_bridge(void *page_table, void *vm, unsigned long start,
		unsigned long end)
{
	return ihk_mc_pt_clear_range((page_table_t)page_table,
			(struct process_vm *)vm, (void *)start, (void *)end);
}

static void
xpmem_range_erase_bridge(void *root, void *node)
{
	rb_erase((struct rb_node *)node, (struct rb_root *)root);
}

static void
xpmem_free_process_range_log_bridge(int event, void *vm, void *range,
		unsigned long start, unsigned long end, int error)
{
	(void)range;
	if (event == 1) {
		ekprintf("xpmem_free_process_memory_range(%p,%lx-%lx): ERROR: "
			"ihk_mc_pt_clear_range(%lx-%lx) failed %d\n",
			vm, start, end, start, end, error);
	}
}

static int
xpmem_fault_range_page_in_bridge(void *vm, void *range, unsigned long vaddr,
		unsigned long reason, int page_in_remote)
{
	return _xpmem_fault_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range, vaddr, reason, page_in_remote);
}

static void
xpmem_update_page_table_log_bridge(int event, void *vm, void *range,
		unsigned long vaddr, int error)
{
	(void)event;
	(void)vm;
	(void)range;
	(void)vaddr;
	ekprintf("%s: ERROR: _xpmem_fault_process_memory_range() failed %d\n",
			"xpmem_update_process_page_table", error);
}

static void *
xpmem_pt_lookup_pte_bridge(void *page_table, unsigned long vaddr,
		int pgshift, void **base, size_t *pgsize, int *p2align)
{
	return ihk_mc_pt_lookup_pte((page_table_t)page_table, (void *)vaddr,
			pgshift, base, pgsize, p2align);
}

static void *
xpmem_vaddr_to_pte_bridge(void *vm, unsigned long vaddr, size_t *pgsize)
{
	return xpmem_vaddr_to_pte((struct process_vm *)vm, vaddr, pgsize);
}

static int
xpmem_ensure_valid_page_bridge(void *seg, unsigned long vaddr, int page_in)
{
	return xpmem_ensure_valid_page((struct xpmem_segment *)seg, vaddr,
			page_in);
}

static int
xpmem_pte_present_bridge(void *pte)
{
	return pte && !pte_is_null((pte_t *)pte);
}

static unsigned long
xpmem_pte_phys_bridge(void *pte)
{
	return pte_get_phys((pte_t *)pte);
}

static int
xpmem_get_smaller_page_size_bridge(size_t pgsize, size_t *new_pgsize,
		int *p2align)
{
	return arch_get_smaller_page_size(NULL, pgsize, new_pgsize, p2align);
}

static void
xpmem_adjust_page_size_bridge(void *page_table, unsigned long fault_addr,
		void *pte, void **pgaddr, size_t *pgsize)
{
	arch_adjust_allocate_page_size((page_table_t)page_table, fault_addr,
			(pte_t *)pte, pgaddr, pgsize);
}

static unsigned long
xpmem_vrflag_to_ptattr_bridge(unsigned long flag, unsigned long reason)
{
	return arch_vrflag_to_ptattr(flag, reason, NULL);
}

static int
xpmem_pgsize_contiguous_bridge(size_t pgsize)
{
	return pgsize_is_contiguous(pgsize);
}

static int
xpmem_pt_set_pte_bridge(void *page_table, void *pte, size_t pgsize,
		unsigned long phys, unsigned long attr)
{
	return ihk_mc_pt_set_pte((page_table_t)page_table, (pte_t *)pte,
			pgsize, phys, (enum ihk_mc_pt_attribute)attr);
}

static int
xpmem_pt_set_range_bridge(void *page_table, void *vm, unsigned long start,
		unsigned long end, unsigned long phys, unsigned long attr,
		int pgshift, void *vmr, int replace)
{
	return ihk_mc_pt_set_range((page_table_t)page_table,
			(struct process_vm *)vm, (void *)start, (void *)end,
			phys, (enum ihk_mc_pt_attribute)attr, pgshift,
			(struct vm_range *)vmr, replace);
}

static void
xpmem_flush_tlb_single_bridge(unsigned long vaddr)
{
	flush_tlb_single(vaddr);
}

static void
xpmem_fault_log_bridge(int event, unsigned long a, unsigned long b,
		unsigned long c, size_t size, int error)
{
	switch (event) {
	case 1:
		kprintf("%s: XPMEM_FLAG_DESTROYING\n",
			"_xpmem_fault_process_memory_range");
		break;
	case 2:
		kprintf("%s: vaddr: %lx, att->at_vaddr: %lx, "
			"att->at_size: %lx\n",
			"_xpmem_fault_process_memory_range", a, b, size);
		break;
	case 3:
		kprintf("%s: arch_get_smaller_page_size failed: "
			" range: %lx-%lx, pgsize: %lx, ret: %d\n",
			"_xpmem_fault_process_memory_range", a, b, size,
			error);
		break;
	case 4:
		ekprintf("%s: ERROR: pte mismatch: 0x%lx != 0x%lx\n",
			"_xpmem_fault_process_memory_range", b, c);
		break;
	case 5:
		ekprintf("%s: ERROR: ihk_mc_pt_set_pte() failed %d\n",
			"_xpmem_fault_process_memory_range", -EFAULT);
		break;
	case 6:
		ekprintf("%s: ERROR: ihk_mc_pt_set_range() failed %d\n",
			"_xpmem_fault_process_memory_range", -EFAULT);
		break;
	default:
		break;
	}
}

static void
xpmem_atomic_sub_bridge(int value, void *counter)
{
	ihk_atomic_sub(value, (ihk_atomic_t *)counter);
}

static int
xpmem_page_fault_vm_bridge(void *vm, unsigned long vaddr,
		unsigned long reason)
{
	return page_fault_process_vm((struct process_vm *)vm, (void *)vaddr,
			reason);
}

static int
xpmem_page_fault_range_bridge(void *vm, void *range, unsigned long vaddr,
		unsigned long reason)
{
	return page_fault_process_memory_range((struct process_vm *)vm,
			(struct vm_range *)range, vaddr, reason);
}

static int
xpmem_pin_page_bridge(void *tg, void *thread, void *vm, unsigned long vaddr,
		int page_in)
{
	return xpmem_pin_page((struct xpmem_thread_group *)tg,
			(struct thread *)thread, (struct process_vm *)vm,
			vaddr, page_in);
}

static void
xpmem_unpin_pages_bridge(void *seg, void *vm, unsigned long vaddr,
		size_t size)
{
	xpmem_unpin_pages((struct xpmem_segment *)seg,
			(struct process_vm *)vm, vaddr, size);
}

static int
xpmem_vm_munmap_bridge(void *vm, unsigned long addr, size_t len)
{
	return xpmem_vm_munmap((struct process_vm *)vm, (void *)addr, len);
}

static void
xpmem_begin_free_pages_pending_bridge(void)
{
	begin_free_pages_pending();
}

static void
xpmem_finish_free_pages_pending_bridge(void)
{
	finish_free_pages_pending();
}

static int
xpmem_remove_process_range_bridge(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp)
{
	return xpmem_remove_process_range((struct process_vm *)vm, start, end,
			ro_freedp);
}

static void
xpmem_detach_att_bridge(void *ap, void *att)
{
	xpmem_detach_att((struct xpmem_access_permit *)ap,
			(struct xpmem_attachment *)att);
}

static void
xpmem_clear_ptes_range_bridge(void *seg, unsigned long start,
		unsigned long end)
{
	xpmem_clear_PTEs_range((struct xpmem_segment *)seg, start, end);
}

static void
xpmem_clear_ptes_of_ap_bridge(void *ap, unsigned long start,
		unsigned long end)
{
	xpmem_clear_PTEs_of_ap((struct xpmem_access_permit *)ap, start, end);
}

static void
xpmem_clear_ptes_of_att_bridge(void *att, unsigned long start,
		unsigned long end)
{
	xpmem_clear_PTEs_of_att((struct xpmem_attachment *)att, start, end);
}

static void
xpmem_remove_seg_bridge(void *tg, void *seg)
{
	xpmem_remove_seg((struct xpmem_thread_group *)tg,
			(struct xpmem_segment *)seg);
}

static void *
xpmem_tg_ref_by_segid_bridge(long segid)
{
	return xpmem_tg_ref_by_segid((xpmem_segid_t)segid);
}

static void *
xpmem_tg_ref_by_apid_bridge(long apid)
{
	return xpmem_tg_ref_by_apid((xpmem_apid_t)apid);
}

static void *
xpmem_seg_ref_by_segid_bridge(void *tg, long segid)
{
	return xpmem_seg_ref_by_segid((struct xpmem_thread_group *)tg,
			(xpmem_segid_t)segid);
}

static void *
xpmem_ap_ref_by_apid_bridge(void *tg, long apid)
{
	return xpmem_ap_ref_by_apid((struct xpmem_thread_group *)tg,
			(xpmem_apid_t)apid);
}

static void
xpmem_release_ap_bridge(void *tg, void *ap)
{
	xpmem_release_ap((struct xpmem_thread_group *)tg,
			(struct xpmem_access_permit *)ap);
}

static void
xpmem_open_log_bridge(int event, int syscall_num, const char *pathname,
		int flags, long value, void *ptr)
{
	switch (event) {
	case XPMEM_OPEN_LOG_CALL:
		XPMEM_DEBUG("call: syscall_num=%d, pathname=%s, flags=%d",
			syscall_num, pathname, flags);
		break;
	case XPMEM_OPEN_LOG_SYSCALL_ERROR:
		XPMEM_DEBUG("syscall_num=%d error: fd=%d", syscall_num,
			(int)value);
		break;
	case XPMEM_OPEN_LOG_OPEN_ERROR:
		XPMEM_DEBUG("return: ret=%d", (int)value);
		break;
	case XPMEM_OPEN_LOG_ALLOC:
		XPMEM_DEBUG("kmalloc(): mckfd=0x%p", ptr);
		break;
	case XPMEM_OPEN_LOG_N_OPENED:
		XPMEM_DEBUG("n_opened=%d", (int)value);
		break;
	case XPMEM_OPEN_LOG_RETURN:
		XPMEM_DEBUG("return: ret=%d", (int)value);
		break;
	default:
		break;
	}
}

static void
xpmem_close_log_bridge(int event, void *mckfdp, int value)
{
	struct mckfd *mckfd = mckfdp;

	switch (event) {
	case 1:
		XPMEM_DEBUG("call: fd=%d, pid=%d, rgid=%d",
			mckfd->fd, get_this_cpu_local_var()->current->proc->pid,
			get_this_cpu_local_var()->current->proc->rgid);
		break;
	case 2:
		XPMEM_DEBUG("n_opened=%d", value);
		break;
	case 3:
		XPMEM_DEBUG("return: ret=%d", value);
		break;
	default:
		break;
	}
}

static void
xpmem_flush_log_bridge(int event, void *tg, long value)
{
	(void)tg;

	switch (event) {
	case 1:
		XPMEM_DEBUG("tg->vm=0x%p", (void *)value);
		break;
	default:
		break;
	}
}

static void
xpmem_remove_seg_log_bridge(int event, void *tgp, void *segp, long value)
{
	struct xpmem_thread_group *tg = tgp;
	struct xpmem_segment *seg = segp;

	(void)value;

	switch (event) {
	case XPMEM_REMOVE_SEG_LOG_CALL:
		XPMEM_DEBUG("call: tgid=%d, segid=0x%lx", tg->tgid,
			seg->segid);
		break;
	case XPMEM_REMOVE_SEG_LOG_RETURN:
		XPMEM_DEBUG("return: ");
		break;
	default:
		break;
	}
}

static void
xpmem_remove_segs_log_bridge(int event, void *tgp, void *segp, long value)
{
	struct xpmem_thread_group *tg = tgp;

	(void)segp;
	(void)value;

	switch (event) {
	case XPMEM_REMOVE_SEGS_LOG_CALL:
		XPMEM_DEBUG("call: tgid=%d", tg->tgid);
		break;
	case XPMEM_REMOVE_SEGS_LOG_RETURN:
		XPMEM_DEBUG("return: ");
		break;
	default:
		break;
	}
}

static void
xpmem_release_ap_log_bridge(int event, void *tgp, void *app, long value)
{
	struct xpmem_thread_group *tg = tgp;
	struct xpmem_access_permit *ap = app;

	switch (event) {
	case XPMEM_RELEASE_AP_LOG_CALL:
		XPMEM_DEBUG("call: tgid=%d, apid=0x%lx", tg->tgid,
			ap->apid);
		break;
	case XPMEM_RELEASE_AP_LOG_RETURN:
		(void)value;
		XPMEM_DEBUG("return: ");
		break;
	default:
		break;
	}
}

static void
xpmem_release_aps_log_bridge(int event, void *tgp, void *app, long value)
{
	struct xpmem_thread_group *tg = tgp;

	(void)app;
	(void)value;

	switch (event) {
	case XPMEM_RELEASE_AP_LOG_CALL:
		XPMEM_DEBUG("call: tgid=%d", tg->tgid);
		break;
	case XPMEM_RELEASE_AP_LOG_RETURN:
		XPMEM_DEBUG("return: ");
		break;
	default:
		break;
	}
}

static const struct xpmem_open_offsets xpmem_open_offsets = {
	.proc_mckfd_lock_offset = __builtin_offsetof(struct process, mckfd_lock),
	.proc_mckfd_offset = __builtin_offsetof(struct process, mckfd),
	.part_n_opened_offset = __builtin_offsetof(struct xpmem_partition,
			n_opened),
	.mckfd_size = sizeof(struct mckfd),
	.mckfd_next_offset = __builtin_offsetof(struct mckfd, next),
	.mckfd_fd_offset = __builtin_offsetof(struct mckfd, fd),
	.mckfd_sig_no_offset = __builtin_offsetof(struct mckfd, sig_no),
	.mckfd_data_offset = __builtin_offsetof(struct mckfd, data),
	.mckfd_ioctl_cb_offset = __builtin_offsetof(struct mckfd, ioctl_cb),
	.mckfd_close_cb_offset = __builtin_offsetof(struct mckfd, close_cb),
	.mckfd_dup_cb_offset = __builtin_offsetof(struct mckfd, dup_cb),
};

static const struct xpmem_close_offsets xpmem_close_offsets = {
	.part_n_opened_offset = __builtin_offsetof(struct xpmem_partition,
			n_opened),
	.mckfd_fd_offset = __builtin_offsetof(struct mckfd, fd),
	.mckfd_data_offset = __builtin_offsetof(struct mckfd, data),
};

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
extern const size_t xpmem_vm_range_private_data_offset;
extern const struct xpmem_partition_offsets xpmem_partition_offsets;
#else
const size_t xpmem_vm_range_private_data_offset =
	__builtin_offsetof(struct vm_range, private_data);

const struct xpmem_partition_offsets xpmem_partition_offsets = {
	.part_size = sizeof(struct xpmem_partition) +
		sizeof(struct xpmem_hashlist) * XPMEM_TG_HASHTABLE_SIZE,
	.part_n_opened_offset = __builtin_offsetof(struct xpmem_partition,
			n_opened),
	.part_tg_hashtable_offset = __builtin_offsetof(
			struct xpmem_partition, tg_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist,
			lock),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist,
			list),
};
#endif

static const struct xpmem_open_tg_offsets xpmem_open_tg_offsets = {
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_ruid_offset = __builtin_offsetof(struct process, ruid),
	.proc_rgid_offset = __builtin_offsetof(struct process, rgid),
	.tg_size = sizeof(struct xpmem_thread_group) +
		sizeof(struct xpmem_hashlist) * XPMEM_AP_HASHTABLE_SIZE,
	.tg_lock_offset = __builtin_offsetof(struct xpmem_thread_group, lock),
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.tg_uid_offset = __builtin_offsetof(struct xpmem_thread_group, uid),
	.tg_gid_offset = __builtin_offsetof(struct xpmem_thread_group, gid),
	.tg_uniq_segid_offset = __builtin_offsetof(struct xpmem_thread_group,
			uniq_segid),
	.tg_uniq_apid_offset = __builtin_offsetof(struct xpmem_thread_group,
			uniq_apid),
	.tg_seg_list_lock_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list_lock),
	.tg_seg_list_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list),
	.tg_n_pinned_offset = __builtin_offsetof(struct xpmem_thread_group,
			n_pinned),
	.tg_tg_hashlist_offset = __builtin_offsetof(
			struct xpmem_thread_group, tg_hashlist),
	.tg_group_leader_offset = __builtin_offsetof(
			struct xpmem_thread_group, group_leader),
	.tg_vm_offset = __builtin_offsetof(struct xpmem_thread_group, vm),
	.tg_ap_hashtable_offset = __builtin_offsetof(
			struct xpmem_thread_group, ap_hashtable),
	.part_tg_hashtable_offset = __builtin_offsetof(struct xpmem_partition,
			tg_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist,
			lock),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist,
			list),
};

static const struct xpmem_flush_offsets xpmem_flush_offsets = {
	.part_tg_hashtable_offset = __builtin_offsetof(struct xpmem_partition,
			tg_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist, lock),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist, list),
	.mckfd_data_offset = __builtin_offsetof(struct mckfd, data),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.tg_lock_offset = __builtin_offsetof(struct xpmem_thread_group, lock),
	.tg_flags_offset = __builtin_offsetof(struct xpmem_thread_group, flags),
	.tg_hashlist_offset = __builtin_offsetof(struct xpmem_thread_group,
			tg_hashlist),
	.tg_vm_offset = __builtin_offsetof(struct xpmem_thread_group, vm),
};

static const struct xpmem_remove_seg_offsets xpmem_remove_seg_offsets = {
	.tg_seg_list_lock_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list_lock),
	.seg_lock_offset = __builtin_offsetof(struct xpmem_segment, lock),
	.seg_flags_offset = __builtin_offsetof(struct xpmem_segment, flags),
	.seg_list_offset = __builtin_offsetof(struct xpmem_segment, seg_list),
};

static const struct xpmem_remove_segs_offsets xpmem_remove_segs_offsets = {
	.tg_seg_list_lock_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list_lock),
	.tg_seg_list_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list),
	.seg_list_offset = __builtin_offsetof(struct xpmem_segment, seg_list),
};

static const struct xpmem_release_ap_offsets xpmem_release_ap_offsets = {
	.tg_ap_hashtable_offset = __builtin_offsetof(
			struct xpmem_thread_group, ap_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist, lock),
	.ap_lock_offset = __builtin_offsetof(struct xpmem_access_permit, lock),
	.ap_apid_offset = __builtin_offsetof(struct xpmem_access_permit, apid),
	.ap_flags_offset = __builtin_offsetof(struct xpmem_access_permit, flags),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.ap_att_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			att_list),
	.ap_ap_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_list),
	.ap_hashlist_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_hashlist),
	.att_att_list_offset = __builtin_offsetof(struct xpmem_attachment,
			att_list),
	.seg_lock_offset = __builtin_offsetof(struct xpmem_segment, lock),
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
};

static const struct xpmem_release_aps_offsets xpmem_release_aps_offsets = {
	.tg_ap_hashtable_offset = __builtin_offsetof(
			struct xpmem_thread_group, ap_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist, lock),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist, list),
	.ap_hashlist_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_hashlist),
};

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
extern const struct xpmem_tg_lookup_offsets xpmem_tg_lookup_offsets;
#else
const struct xpmem_tg_lookup_offsets xpmem_tg_lookup_offsets = {
	.part_tg_hashtable_offset = __builtin_offsetof(struct xpmem_partition,
			tg_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist, list),
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.tg_flags_offset = __builtin_offsetof(struct xpmem_thread_group, flags),
	.tg_hashlist_offset = __builtin_offsetof(struct xpmem_thread_group,
			tg_hashlist),
};
#endif

static const struct xpmem_seg_lookup_offsets xpmem_seg_lookup_offsets = {
	.tg_seg_list_lock_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list_lock),
	.tg_seg_list_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list),
	.seg_segid_offset = __builtin_offsetof(struct xpmem_segment, segid),
	.seg_flags_offset = __builtin_offsetof(struct xpmem_segment, flags),
	.seg_list_offset = __builtin_offsetof(struct xpmem_segment, seg_list),
};

static const struct xpmem_ap_lookup_offsets xpmem_ap_lookup_offsets = {
	.tg_ap_hashtable_offset = __builtin_offsetof(
			struct xpmem_thread_group, ap_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist, lock),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist, list),
	.ap_apid_offset = __builtin_offsetof(struct xpmem_access_permit, apid),
	.ap_flags_offset = __builtin_offsetof(struct xpmem_access_permit, flags),
	.ap_hashlist_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_hashlist),
};

static const struct xpmem_deref_offsets xpmem_tg_deref_offsets = {
	.refcnt_offset = __builtin_offsetof(struct xpmem_thread_group, refcnt),
	.flags_offset = __builtin_offsetof(struct xpmem_thread_group, flags),
};

static const struct xpmem_deref_offsets xpmem_seg_deref_offsets = {
	.refcnt_offset = __builtin_offsetof(struct xpmem_segment, refcnt),
	.flags_offset = __builtin_offsetof(struct xpmem_segment, flags),
};

static const struct xpmem_deref_offsets xpmem_ap_deref_offsets = {
	.refcnt_offset = __builtin_offsetof(struct xpmem_access_permit, refcnt),
	.flags_offset = __builtin_offsetof(struct xpmem_access_permit, flags),
};

static const struct xpmem_deref_offsets xpmem_att_deref_offsets = {
	.refcnt_offset = __builtin_offsetof(struct xpmem_attachment, refcnt),
	.flags_offset = __builtin_offsetof(struct xpmem_attachment, flags),
};

static const struct xpmem_make_id_offsets xpmem_make_segid_offsets = {
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.tg_uniq_offset = __builtin_offsetof(struct xpmem_thread_group,
			uniq_segid),
};

static const struct xpmem_make_id_offsets xpmem_make_apid_offsets = {
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.tg_uniq_offset = __builtin_offsetof(struct xpmem_thread_group,
			uniq_apid),
};

static const struct xpmem_validate_access_offsets
xpmem_validate_access_offsets = {
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_vm_offset = __builtin_offsetof(struct process, vm),
	.ap_mode_offset = __builtin_offsetof(struct xpmem_access_permit, mode),
	.ap_tg_offset = __builtin_offsetof(struct xpmem_access_permit, tg),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.seg_vaddr_offset = __builtin_offsetof(struct xpmem_segment, vaddr),
	.seg_size_offset = __builtin_offsetof(struct xpmem_segment, size),
};

static const struct xpmem_perm_offsets xpmem_perm_offsets = {
	.proc_ruid_offset = __builtin_offsetof(struct process, ruid),
	.proc_rgid_offset = __builtin_offsetof(struct process, rgid),
	.perm_uid_offset = __builtin_offsetof(struct xpmem_perm, uid),
	.perm_gid_offset = __builtin_offsetof(struct xpmem_perm, gid),
	.perm_mode_offset = __builtin_offsetof(struct xpmem_perm, mode),
	.seg_permit_type_offset = __builtin_offsetof(struct xpmem_segment,
			permit_type),
	.seg_permit_value_offset = __builtin_offsetof(struct xpmem_segment,
			permit_value),
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
	.tg_uid_offset = __builtin_offsetof(struct xpmem_thread_group, uid),
	.tg_gid_offset = __builtin_offsetof(struct xpmem_thread_group, gid),
};

static const struct xpmem_make_segment_offsets xpmem_make_segment_offsets = {
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.seg_size = sizeof(struct xpmem_segment),
	.seg_lock_offset = __builtin_offsetof(struct xpmem_segment, lock),
	.seg_segid_offset = __builtin_offsetof(struct xpmem_segment, segid),
	.seg_vaddr_offset = __builtin_offsetof(struct xpmem_segment, vaddr),
	.seg_size_offset = __builtin_offsetof(struct xpmem_segment, size),
	.seg_permit_type_offset = __builtin_offsetof(struct xpmem_segment,
			permit_type),
	.seg_permit_value_offset = __builtin_offsetof(struct xpmem_segment,
			permit_value),
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
	.seg_ap_list_offset = __builtin_offsetof(struct xpmem_segment,
			ap_list),
	.seg_seg_list_offset = __builtin_offsetof(struct xpmem_segment,
			seg_list),
	.tg_seg_list_lock_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list_lock),
	.tg_seg_list_offset = __builtin_offsetof(
			struct xpmem_thread_group, seg_list),
};

static const struct xpmem_get_offsets xpmem_get_offsets = {
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.ap_size = sizeof(struct xpmem_access_permit),
	.ap_lock_offset = __builtin_offsetof(struct xpmem_access_permit,
			lock),
	.ap_apid_offset = __builtin_offsetof(struct xpmem_access_permit,
			apid),
	.ap_mode_offset = __builtin_offsetof(struct xpmem_access_permit,
			mode),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.ap_tg_offset = __builtin_offsetof(struct xpmem_access_permit, tg),
	.ap_att_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			att_list),
	.ap_ap_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_list),
	.ap_hashlist_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_hashlist),
	.seg_lock_offset = __builtin_offsetof(struct xpmem_segment, lock),
	.seg_ap_list_offset = __builtin_offsetof(struct xpmem_segment,
			ap_list),
	.tg_ap_hashtable_offset = __builtin_offsetof(
			struct xpmem_thread_group, ap_hashtable),
	.hashlist_stride = sizeof(struct xpmem_hashlist),
	.hashlist_lock_offset = __builtin_offsetof(struct xpmem_hashlist,
			lock),
	.hashlist_list_offset = __builtin_offsetof(struct xpmem_hashlist,
			list),
};

static const struct xpmem_tg_id_offsets xpmem_tg_id_offsets = {
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
};

static const struct xpmem_detach_offsets xpmem_detach_offsets = {
	.vm_memory_range_lock_offset = __builtin_offsetof(struct process_vm,
			memory_range_lock),
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_private_data_offset = __builtin_offsetof(struct vm_range,
			private_data),
	.att_at_lock_offset = __builtin_offsetof(struct xpmem_attachment,
			at_lock),
	.att_at_vaddr_offset = __builtin_offsetof(struct xpmem_attachment,
			at_vaddr),
	.att_at_size_offset = __builtin_offsetof(struct xpmem_attachment,
			at_size),
	.att_flags_offset = __builtin_offsetof(struct xpmem_attachment, flags),
	.att_ap_offset = __builtin_offsetof(struct xpmem_attachment, ap),
	.att_vm_offset = __builtin_offsetof(struct xpmem_attachment, vm),
	.att_att_list_offset = __builtin_offsetof(struct xpmem_attachment,
			att_list),
	.ap_lock_offset = __builtin_offsetof(struct xpmem_access_permit, lock),
	.ap_tg_offset = __builtin_offsetof(struct xpmem_access_permit, tg),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
};

static const struct xpmem_detach_att_offsets xpmem_detach_att_offsets = {
	.vm_memory_range_lock_offset = __builtin_offsetof(struct process_vm,
			memory_range_lock),
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_end_offset = __builtin_offsetof(struct vm_range, end),
	.range_private_data_offset = __builtin_offsetof(struct vm_range,
			private_data),
	.att_at_lock_offset = __builtin_offsetof(struct xpmem_attachment,
			at_lock),
	.att_vaddr_offset = __builtin_offsetof(struct xpmem_attachment, vaddr),
	.att_at_vaddr_offset = __builtin_offsetof(struct xpmem_attachment,
			at_vaddr),
	.att_at_size_offset = __builtin_offsetof(struct xpmem_attachment,
			at_size),
	.att_flags_offset = __builtin_offsetof(struct xpmem_attachment, flags),
	.att_vm_offset = __builtin_offsetof(struct xpmem_attachment, vm),
	.att_att_list_offset = __builtin_offsetof(struct xpmem_attachment,
			att_list),
	.ap_lock_offset = __builtin_offsetof(struct xpmem_access_permit, lock),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
};

static const struct xpmem_clear_ptes_offsets xpmem_clear_ptes_offsets = {
	.seg_lock_offset = __builtin_offsetof(struct xpmem_segment, lock),
	.seg_vaddr_offset = __builtin_offsetof(struct xpmem_segment, vaddr),
	.seg_size_offset = __builtin_offsetof(struct xpmem_segment, size),
	.seg_ap_list_offset = __builtin_offsetof(struct xpmem_segment, ap_list),
	.ap_lock_offset = __builtin_offsetof(struct xpmem_access_permit, lock),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.ap_att_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			att_list),
	.ap_ap_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			ap_list),
	.att_at_lock_offset = __builtin_offsetof(struct xpmem_attachment,
			at_lock),
	.att_vaddr_offset = __builtin_offsetof(struct xpmem_attachment, vaddr),
	.att_at_vaddr_offset = __builtin_offsetof(struct xpmem_attachment,
			at_vaddr),
	.att_at_size_offset = __builtin_offsetof(struct xpmem_attachment,
			at_size),
	.att_flags_offset = __builtin_offsetof(struct xpmem_attachment, flags),
	.att_ap_offset = __builtin_offsetof(struct xpmem_attachment, ap),
	.att_vm_offset = __builtin_offsetof(struct xpmem_attachment, vm),
	.att_att_list_offset = __builtin_offsetof(struct xpmem_attachment,
			att_list),
	.vm_memory_range_lock_offset = __builtin_offsetof(struct process_vm,
			memory_range_lock),
};

static const struct xpmem_remove_process_range_offsets
xpmem_remove_process_range_offsets = {
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_end_offset = __builtin_offsetof(struct vm_range, end),
	.range_flag_offset = __builtin_offsetof(struct vm_range, flag),
	.range_private_data_offset = __builtin_offsetof(struct vm_range,
			private_data),
};

static const struct xpmem_free_process_range_offsets
xpmem_free_process_range_offsets = {
	.vm_address_space_offset = __builtin_offsetof(struct process_vm,
			address_space),
	.vm_page_table_lock_offset = __builtin_offsetof(struct process_vm,
			page_table_lock),
	.vm_range_tree_offset = __builtin_offsetof(struct process_vm,
			vm_range_tree),
	.vm_range_cache_offset = __builtin_offsetof(struct process_vm,
			range_cache),
	.vm_range_cache_count = VM_RANGE_CACHE_SIZE,
	.address_space_page_table_offset = __builtin_offsetof(
			struct address_space, page_table),
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_end_offset = __builtin_offsetof(struct vm_range, end),
	.range_memobj_offset = __builtin_offsetof(struct vm_range, memobj),
	.range_rb_node_offset = __builtin_offsetof(struct vm_range,
			vm_rb_node),
};

static const struct xpmem_fault_process_range_offsets
xpmem_fault_process_range_offsets = {
	.vm_address_space_offset = __builtin_offsetof(struct process_vm,
			address_space),
	.vm_proc_offset = __builtin_offsetof(struct process_vm, proc),
	.vm_memory_range_lock_offset = __builtin_offsetof(struct process_vm,
			memory_range_lock),
	.address_space_page_table_offset = __builtin_offsetof(
			struct address_space, page_table),
	.proc_straight_va_offset = __builtin_offsetof(struct process,
			straight_va),
	.proc_straight_len_offset = __builtin_offsetof(struct process,
			straight_len),
	.proc_straight_pa_offset = __builtin_offsetof(struct process,
			straight_pa),
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_end_offset = __builtin_offsetof(struct vm_range, end),
	.range_flag_offset = __builtin_offsetof(struct vm_range, flag),
	.range_pgshift_offset = __builtin_offsetof(struct vm_range, pgshift),
	.range_private_data_offset = __builtin_offsetof(struct vm_range,
			private_data),
	.att_at_vaddr_offset = __builtin_offsetof(struct xpmem_attachment,
			at_vaddr),
	.att_at_size_offset = __builtin_offsetof(struct xpmem_attachment,
			at_size),
	.att_vaddr_offset = __builtin_offsetof(struct xpmem_attachment,
			vaddr),
	.att_flags_offset = __builtin_offsetof(struct xpmem_attachment, flags),
	.att_ap_offset = __builtin_offsetof(struct xpmem_attachment, ap),
	.ap_flags_offset = __builtin_offsetof(struct xpmem_access_permit,
			flags),
	.ap_mode_offset = __builtin_offsetof(struct xpmem_access_permit, mode),
	.ap_tg_offset = __builtin_offsetof(struct xpmem_access_permit, tg),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.tg_flags_offset = __builtin_offsetof(struct xpmem_thread_group,
			flags),
	.tg_vm_offset = __builtin_offsetof(struct xpmem_thread_group, vm),
	.tg_n_pinned_offset = __builtin_offsetof(struct xpmem_thread_group,
			n_pinned),
	.seg_flags_offset = __builtin_offsetof(struct xpmem_segment, flags),
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
};

static const struct xpmem_fault_process_range_ops
xpmem_fault_process_range_ops = {
	.att_ref_fn = xpmem_att_ref_bridge,
	.att_deref_fn = xpmem_att_deref_bridge,
	.ap_ref_fn = xpmem_ap_ref_bridge,
	.ap_deref_fn = xpmem_ap_deref_bridge,
	.tg_ref_fn = xpmem_tg_ref_bridge,
	.tg_deref_fn = xpmem_tg_deref_bridge,
	.seg_ref_fn = xpmem_seg_ref_bridge,
	.seg_deref_fn = xpmem_seg_deref_bridge,
	.bug_on_fn = xpmem_bug_on_bridge,
	.ensure_valid_fn = xpmem_ensure_valid_page_bridge,
	.read_lock_noirq_fn = xpmem_rwspin_read_lock_noirq_bridge,
	.read_unlock_noirq_fn = xpmem_rwspin_read_unlock_noirq_bridge,
	.vaddr_to_pte_fn = xpmem_vaddr_to_pte_bridge,
	.pte_present_fn = xpmem_pte_present_bridge,
	.pte_phys_fn = xpmem_pte_phys_bridge,
	.pt_lookup_pte_fn = xpmem_pt_lookup_pte_bridge,
	.smaller_page_fn = xpmem_get_smaller_page_size_bridge,
	.adjust_page_fn = xpmem_adjust_page_size_bridge,
	.vrflag_to_ptattr_fn = xpmem_vrflag_to_ptattr_bridge,
	.pgsize_contiguous_fn = xpmem_pgsize_contiguous_bridge,
	.pt_set_pte_fn = xpmem_pt_set_pte_bridge,
	.pt_set_range_fn = xpmem_pt_set_range_bridge,
	.atomic_dec_fn = xpmem_atomic_dec_bridge,
	.flush_tlb_single_fn = xpmem_flush_tlb_single_bridge,
	.log_fn = xpmem_fault_log_bridge,
};

static const struct xpmem_attach_offsets xpmem_attach_offsets = {
	.mckfd_fd_offset = __builtin_offsetof(struct mckfd, fd),
	.vm_memory_range_lock_offset = __builtin_offsetof(struct process_vm,
			memory_range_lock),
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_end_offset = __builtin_offsetof(struct vm_range, end),
	.range_private_data_offset = __builtin_offsetof(struct vm_range,
			private_data),
	.tg_tgid_offset = __builtin_offsetof(struct xpmem_thread_group, tgid),
	.tg_flags_offset = __builtin_offsetof(struct xpmem_thread_group,
			flags),
	.ap_lock_offset = __builtin_offsetof(struct xpmem_access_permit, lock),
	.ap_flags_offset = __builtin_offsetof(struct xpmem_access_permit,
			flags),
	.ap_seg_offset = __builtin_offsetof(struct xpmem_access_permit, seg),
	.ap_att_list_offset = __builtin_offsetof(struct xpmem_access_permit,
			att_list),
	.seg_flags_offset = __builtin_offsetof(struct xpmem_segment, flags),
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
	.att_size = sizeof(struct xpmem_attachment),
	.att_at_lock_offset = __builtin_offsetof(struct xpmem_attachment,
			at_lock),
	.att_vaddr_offset = __builtin_offsetof(struct xpmem_attachment, vaddr),
	.att_at_size_offset = __builtin_offsetof(struct xpmem_attachment,
			at_size),
	.att_flags_offset = __builtin_offsetof(struct xpmem_attachment, flags),
	.att_ap_offset = __builtin_offsetof(struct xpmem_attachment, ap),
	.att_vm_offset = __builtin_offsetof(struct xpmem_attachment, vm),
	.att_att_list_offset = __builtin_offsetof(struct xpmem_attachment,
			att_list),
};

static const struct xpmem_ioctl_offsets xpmem_ioctl_offsets = {
	.cmd_version = XPMEM_CMD_VERSION,
	.cmd_make = XPMEM_CMD_MAKE,
	.cmd_remove = XPMEM_CMD_REMOVE,
	.cmd_get = XPMEM_CMD_GET,
	.cmd_release = XPMEM_CMD_RELEASE,
	.cmd_attach = XPMEM_CMD_ATTACH,
	.cmd_detach = XPMEM_CMD_DETACH,
	.current_version = XPMEM_CURRENT_VERSION,
	.make_size = sizeof(struct xpmem_cmd_make),
	.make_vaddr_offset = __builtin_offsetof(struct xpmem_cmd_make, vaddr),
	.make_size_offset = __builtin_offsetof(struct xpmem_cmd_make, size),
	.make_permit_type_offset = __builtin_offsetof(struct xpmem_cmd_make,
			permit_type),
	.make_permit_value_offset = __builtin_offsetof(struct xpmem_cmd_make,
			permit_value),
	.make_segid_offset = __builtin_offsetof(struct xpmem_cmd_make, segid),
	.remove_size = sizeof(struct xpmem_cmd_remove),
	.remove_segid_offset = __builtin_offsetof(struct xpmem_cmd_remove,
			segid),
	.get_size = sizeof(struct xpmem_cmd_get),
	.get_segid_offset = __builtin_offsetof(struct xpmem_cmd_get, segid),
	.get_flags_offset = __builtin_offsetof(struct xpmem_cmd_get, flags),
	.get_permit_type_offset = __builtin_offsetof(struct xpmem_cmd_get,
			permit_type),
	.get_permit_value_offset = __builtin_offsetof(struct xpmem_cmd_get,
			permit_value),
	.get_apid_offset = __builtin_offsetof(struct xpmem_cmd_get, apid),
	.release_size = sizeof(struct xpmem_cmd_release),
	.release_apid_offset = __builtin_offsetof(struct xpmem_cmd_release,
			apid),
	.attach_size = sizeof(struct xpmem_cmd_attach),
	.attach_apid_offset = __builtin_offsetof(struct xpmem_cmd_attach, apid),
	.attach_offset_offset = __builtin_offsetof(struct xpmem_cmd_attach,
			offset),
	.attach_size_offset = __builtin_offsetof(struct xpmem_cmd_attach,
			size),
	.attach_vaddr_offset = __builtin_offsetof(struct xpmem_cmd_attach,
			vaddr),
	.attach_fd_offset = __builtin_offsetof(struct xpmem_cmd_attach, fd),
	.attach_flags_offset = __builtin_offsetof(struct xpmem_cmd_attach,
			flags),
	.detach_size = sizeof(struct xpmem_cmd_detach),
	.detach_vaddr_offset = __builtin_offsetof(struct xpmem_cmd_detach,
			vaddr),
};

static const struct xpmem_pin_page_offsets xpmem_pin_page_offsets = {
	.tg_n_pinned_offset = __builtin_offsetof(struct xpmem_thread_group,
			n_pinned),
	.vm_memory_range_lock_offset = __builtin_offsetof(struct process_vm,
			memory_range_lock),
	.vm_stack_start_offset = __builtin_offsetof(struct process_vm,
			region.stack_start),
	.vm_stack_end_offset = __builtin_offsetof(struct process_vm,
			region.stack_end),
	.range_start_offset = __builtin_offsetof(struct vm_range, start),
	.range_private_data_offset = __builtin_offsetof(struct vm_range,
			private_data),
};

static const struct xpmem_ensure_valid_page_offsets
xpmem_ensure_valid_page_offsets = {
	.seg_flags_offset = __builtin_offsetof(struct xpmem_segment, flags),
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
	.tg_group_leader_offset = __builtin_offsetof(struct xpmem_thread_group,
			group_leader),
	.tg_vm_offset = __builtin_offsetof(struct xpmem_thread_group, vm),
};

static const struct xpmem_vaddr_to_pte_offsets xpmem_vaddr_to_pte_offsets = {
	.vm_address_space_offset = __builtin_offsetof(struct process_vm,
			address_space),
	.address_space_page_table_offset = __builtin_offsetof(
			struct address_space, page_table),
	.range_pgshift_offset = __builtin_offsetof(struct vm_range, pgshift),
};

static const struct xpmem_unpin_pages_offsets xpmem_unpin_pages_offsets = {
	.seg_tg_offset = __builtin_offsetof(struct xpmem_segment, tg),
	.tg_n_pinned_offset = __builtin_offsetof(struct xpmem_thread_group,
			n_pinned),
};
#endif

static int do_xpmem_open(int syscall_num, const char *pathname,
		int flags, ihk_mc_user_context_t *ctx)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct thread *thread = get_this_cpu_local_var()->current;

	return xpmem_open_body_result(syscall_num, pathname, flags, ctx,
			(void **)&xpmem_my_part, thread->proc,
			&xpmem_open_offsets, (unsigned long)xpmem_ioctl,
			(unsigned long)xpmem_close, (unsigned long)xpmem_dup,
			xpmem_init, xpmem_forward_bridge, __xpmem_open,
			xpmem_mckfd_alloc_bridge, xpmem_mckfd_lock_bridge,
			xpmem_mckfd_unlock_bridge, xpmem_atomic_inc_bridge,
			xpmem_open_log_bridge);
#else
	int ret;
	struct thread *thread = get_this_cpu_local_var()->current;
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

	mckfd = kmalloc_tracked(sizeof(struct mckfd), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
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
#endif
}

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
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
#endif

static int xpmem_ioctl(
	struct mckfd *mckfd,
	ihk_mc_user_context_t *ctx)
{
	int ret;
	unsigned int cmd = ihk_mc_syscall_arg1(ctx);
	unsigned long arg = ihk_mc_syscall_arg2(ctx);

	XPMEM_DEBUG("call: cmd=0x%x, arg=0x%lx", cmd, arg);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_ioctl_body_result(mckfd, cmd, arg, &xpmem_ioctl_offsets,
			xpmem_copy_from_user_bridge,
			xpmem_copy_to_user_bridge,
			xpmem_make_bridge,
			xpmem_remove_bridge,
			xpmem_get_bridge,
			xpmem_release_bridge,
			xpmem_attach_bridge,
			xpmem_detach_bridge);

	XPMEM_DEBUG("return: cmd=0x%x, ret=%d", cmd, ret);

	return ret;
#else
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
#endif
}

static int xpmem_close(
	struct mckfd *mckfd,
	ihk_mc_user_context_t *ctx)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)ctx;

	return xpmem_close_body_result(mckfd, (void **)&xpmem_my_part,
			&xpmem_close_offsets, xpmem_atomic_dec_bridge,
			xpmem_mckfd_flush_bridge, xpmem_exit,
			xpmem_close_log_bridge);
#else
	int n_opened;
	int flush_objects;
	int exit_partition;

	XPMEM_DEBUG("call: fd=%d, pid=%d, rgid=%d", 
		mckfd->fd, get_this_cpu_local_var()->current->proc->pid,
		get_this_cpu_local_var()->current->proc->rgid);

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
#endif
}

static int xpmem_dup(
	struct mckfd *mckfd,
	ihk_mc_user_context_t *ctx)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)ctx;

	return xpmem_dup_body_result(mckfd, (void **)&xpmem_my_part,
			&xpmem_close_offsets, xpmem_atomic_inc_bridge);
#else
	mckfd->data = 0;
	ihk_atomic_inc_return(&xpmem_my_part->n_opened);

	return 0;
#endif
}

static int xpmem_init(void)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: ");

	ret = xpmem_partition_init_body_result((void **)&xpmem_my_part,
			&xpmem_partition_offsets, xpmem_mckfd_alloc_bridge,
			xpmem_rwlock_init_bridge, xpmem_list_init_bridge,
			xpmem_atomic_set_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
	int i;

	XPMEM_DEBUG("call: ");

	xpmem_my_part = kmalloc_tracked(sizeof(struct xpmem_partition) +
		sizeof(struct xpmem_hashlist) * XPMEM_TG_HASHTABLE_SIZE,
		IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
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
#endif
}


static void xpmem_exit(void)
{
	XPMEM_DEBUG("call: ");

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)xpmem_partition_exit_body_result((void **)&xpmem_my_part,
			xpmem_kfree_bridge);
#else
	if (xpmem_my_part) {
		XPMEM_DEBUG("kfree(): xpmem_my_part=0x%p", xpmem_my_part);
		kfree_tracked(xpmem_my_part, __FILE__, __LINE__);
		xpmem_my_part = NULL;
	}
#endif

	XPMEM_DEBUG("return: ");
}


static int __xpmem_open(void)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;
	int ret;

	XPMEM_DEBUG("call: ");

	ret = xpmem_open_tg_body_result((void **)&xpmem_my_part,
			get_this_cpu_local_var()->current, get_this_cpu_local_var()->current->proc,
			get_this_cpu_local_var()->current->vm, &xpmem_open_tg_offsets,
			&lock, xpmem_tg_ref_by_tgid_bridge,
			xpmem_tg_deref_bridge, xpmem_mckfd_alloc_bridge,
			xpmem_spinlock_init_bridge, xpmem_rwlock_init_bridge,
			xpmem_list_init_bridge, xpmem_atomic_set_bridge,
			xpmem_tg_not_destroyable_bridge,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_list_add_tail_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
	struct xpmem_thread_group *tg;
	int index;
	struct mcs_rwlock_node_irqsave lock;

	XPMEM_DEBUG("call: ");

	tg = xpmem_tg_ref_by_tgid(get_this_cpu_local_var()->current->proc->pid);
	if (!IS_ERR(tg)) {
		xpmem_tg_deref(tg);
		XPMEM_DEBUG("return: ret=%d, tg=0x%p", 0, tg);
		return 0;
	}

	tg = kmalloc_tracked(sizeof(struct xpmem_thread_group) +
		sizeof(struct xpmem_hashlist) * XPMEM_AP_HASHTABLE_SIZE,
		IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (tg == NULL) {
		return -ENOMEM;
	}
	XPMEM_DEBUG("kmalloc(): tg=0x%p", tg);
	memset(tg, 0, sizeof(struct xpmem_thread_group) + 
		sizeof(struct xpmem_hashlist) * XPMEM_AP_HASHTABLE_SIZE);

	ihk_mc_spinlock_init(&tg->lock);
	tg->tgid = get_this_cpu_local_var()->current->proc->pid;
	tg->uid = get_this_cpu_local_var()->current->proc->ruid;
	tg->gid = get_this_cpu_local_var()->current->proc->rgid;
	ihk_atomic_set(&tg->uniq_segid, 0);
	ihk_atomic_set(&tg->uniq_apid, 0);
	mcs_rwlock_init(&tg->seg_list_lock);
	INIT_LIST_HEAD(&tg->seg_list);
	ihk_atomic_set(&tg->n_pinned, 0);
	INIT_LIST_HEAD(&tg->tg_hashlist);
	tg->vm = get_this_cpu_local_var()->current->vm;

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

	tg->group_leader = get_this_cpu_local_var()->current;

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
#endif
}


static void xpmem_destroy_tg(
	struct xpmem_thread_group *tg)
{
	XPMEM_DEBUG("call: tg=0x%p", tg);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)xpmem_destroy_tg_body_result(tg,
			xpmem_tg_destroyable_bridge,
			xpmem_tg_deref_bridge);
#else
	xpmem_tg_destroyable(tg);
	xpmem_tg_deref(tg);
#endif

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
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	long rust_segid = 0;
#else
	struct xpmem_thread_group *seg_tg;
	struct xpmem_segment *seg;
#endif
	struct mcs_rwlock_node_irqsave lock;
	int ret;

	XPMEM_DEBUG("call: vaddr=0x%lx, size=0x%lx, permit_type=%d, " 
		"permit_value=0%04lo", 
		vaddr, size, permit_type, 
		(unsigned long)(uintptr_t)permit_value);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_make_segment_body_result(vaddr, size, permit_type,
			permit_value, &rust_segid, get_this_cpu_local_var()->current->proc,
			&xpmem_make_segment_offsets, &lock,
			xpmem_tg_ref_by_tgid_bridge,
			xpmem_tg_deref_bridge, xpmem_make_segid_bridge,
			xpmem_mckfd_alloc_bridge, xpmem_spinlock_init_bridge,
			xpmem_list_init_bridge,
			xpmem_seg_not_destroyable_bridge,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_list_add_tail_bridge, xpmem_bug_on_bridge);
	if (!ret) {
		segid = (xpmem_segid_t)rust_segid;
		*segid_p = segid;
		XPMEM_DEBUG("return: ret=%d, segid=0x%lx", 0, *segid_p);
	}
	else {
		XPMEM_DEBUG("return: ret=%d", ret);
	}

	return ret;
#else
	ret = xpmem_make_initial_policy_result(permit_type,
			(unsigned long)(uintptr_t)permit_value, size);
	if (ret) {
		XPMEM_DEBUG("return: ret=%d", -EINVAL);
		return ret;
	}

	seg_tg = xpmem_tg_ref_by_tgid(get_this_cpu_local_var()->current->proc->pid);
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
	seg = kmalloc_tracked(sizeof(struct xpmem_segment), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
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
#endif
}


static xpmem_segid_t xpmem_make_segid(
	struct xpmem_thread_group *seg_tg)
{
	long segid = 0;
	xpmem_id_t debug_id;
#ifndef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;
	int uniq;
#endif

	XPMEM_DEBUG("call: seg_tg=0x%p, uniq_segid=%d", 
		seg_tg, ihk_atomic_read(&seg_tg->uniq_segid));

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	segid = xpmem_make_object_id_body_result(seg_tg,
			&xpmem_make_segid_offsets, xpmem_atomic_inc_bridge,
			xpmem_atomic_dec_bridge, xpmem_bug_on_bridge);
	if (segid < 0) {
		return segid;
	}
#else
	uniq = ihk_atomic_inc_return(&seg_tg->uniq_segid);
	ret = xpmem_make_id_result(seg_tg->tgid, uniq, &segid);
	if (ret) {
		ihk_atomic_dec(&seg_tg->uniq_segid);
		return ret;
	}

	DBUG_ON(segid <= 0);
#endif
	debug_id.segid = segid;

	XPMEM_DEBUG("return: segid=0x%lx, segid.tgid=%d, segid.uniq=%d", 
		segid, debug_id.xpmem_id.tgid, debug_id.xpmem_id.uniq);

	return segid;
}


static int xpmem_remove(
	xpmem_segid_t segid)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: segid=0x%lx", segid);

	ret = xpmem_remove_body_result(segid,
			get_this_cpu_local_var()->current->proc->pid,
			&xpmem_tg_id_offsets,
			xpmem_tg_ref_by_segid_bridge,
			xpmem_seg_ref_by_segid_bridge,
			xpmem_remove_seg_bridge,
			xpmem_seg_deref_bridge,
			xpmem_tg_deref_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
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

	ret = xpmem_owner_policy_result(get_this_cpu_local_var()->current->proc->pid,
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
#endif
}


static void xpmem_remove_seg(
	struct xpmem_thread_group *seg_tg,
	struct xpmem_segment *seg)
{
	DBUG_ON(ihk_atomic_read(&seg->refcnt) <= 0);
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	(void)xpmem_remove_seg_body_result(seg_tg, seg,
			&xpmem_remove_seg_offsets, &lock,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_clear_ptes_bridge,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_list_del_init_bridge,
			xpmem_seg_destroyable_bridge,
			xpmem_remove_seg_log_bridge);
#else
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
#endif
}


static void xpmem_remove_segs_of_tg(
	struct xpmem_thread_group *seg_tg)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	(void)xpmem_remove_segs_of_tg_body_result(seg_tg,
			&xpmem_remove_segs_offsets, &lock,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_seg_ref_bridge, xpmem_remove_seg_bridge,
			xpmem_seg_deref_bridge, xpmem_remove_segs_log_bridge);
#else
	struct xpmem_segment *seg;
	struct mcs_rwlock_node_irqsave lock;

	XPMEM_DEBUG("call: tgid=%d", seg_tg->tgid);

	mcs_rwlock_writer_lock(&seg_tg->seg_list_lock, &lock);

	while (!list_empty(&seg_tg->seg_list)) {
		seg = ((struct xpmem_segment *)((char *)((&seg_tg->seg_list)->next) - offsetof(struct xpmem_segment, seg_list)));
		xpmem_seg_ref(seg);
		mcs_rwlock_writer_unlock(&seg_tg->seg_list_lock, &lock);

		xpmem_remove_seg(seg_tg, seg);

		xpmem_seg_deref(seg);

		mcs_rwlock_writer_lock(&seg_tg->seg_list_lock, &lock);
	}

	mcs_rwlock_writer_unlock(&seg_tg->seg_list_lock, &lock);

	XPMEM_DEBUG("return: ");
#endif
}


static int xpmem_get(
	xpmem_segid_t segid,
	int flags,
	int permit_type,
	void *permit_value,
	xpmem_apid_t *apid_p)
{
	xpmem_apid_t apid;
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	long rust_apid = 0;
#else
	struct xpmem_access_permit *ap;
	struct xpmem_segment *seg;
	struct xpmem_thread_group *ap_tg, *seg_tg;
	int index;
#endif
	struct mcs_rwlock_node_irqsave lock;
	int ret;

	XPMEM_DEBUG("call: segid=0x%lx, flags=%d, permit_type=%d, " 
		"permit_value=0%04lo", 
		segid, flags, permit_type, 
		(unsigned long)(uintptr_t)permit_value);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_get_body_result(segid, flags, permit_type,
			permit_value, &rust_apid, get_this_cpu_local_var()->current->proc,
			&xpmem_get_offsets, &lock,
			xpmem_tg_ref_by_segid_bridge,
			xpmem_seg_ref_by_segid_bridge,
			xpmem_check_permit_mode_bridge,
			xpmem_tg_ref_by_tgid_bridge,
			xpmem_make_apid_bridge, xpmem_mckfd_alloc_bridge,
			xpmem_spinlock_init_bridge, xpmem_list_init_bridge,
			xpmem_ap_not_destroyable_bridge,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_list_add_tail_bridge,
			xpmem_seg_deref_bridge,
			xpmem_tg_deref_bridge, xpmem_bug_on_bridge);
	if (!ret) {
		apid = (xpmem_apid_t)rust_apid;
		*apid_p = apid;
		XPMEM_DEBUG("return: ret=%d, apid=0x%lx", 0, *apid_p);
	}
	else {
		XPMEM_DEBUG("return: ret=%d", ret);
	}

	return ret;
#else
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

	ap_tg = xpmem_tg_ref_by_tgid(get_this_cpu_local_var()->current->proc->pid);
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
	ap = kmalloc_tracked(sizeof(struct xpmem_access_permit), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
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
#endif
}


static int xpmem_check_permit_mode(
	int flags,
	struct xpmem_segment *seg)
{
	int ret;

	XPMEM_DEBUG("call: flags=%d", flags);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_check_permit_mode_body_result(flags, seg,
			get_this_cpu_local_var()->current->proc, &xpmem_perm_offsets,
			xpmem_bug_on_bridge);
#else
	DBUG_ON(seg->permit_type != XPMEM_PERMIT_MODE);

	ret = xpmem_check_permit_mode_result(flags, seg->tg->uid,
			seg->tg->gid, (unsigned long)seg->permit_value,
			get_this_cpu_local_var()->current->proc->ruid,
			get_this_cpu_local_var()->current->proc->rgid);
#endif

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

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_perms_body_result(perm, flag, get_this_cpu_local_var()->current->proc,
			&xpmem_perm_offsets);
#else
	ret = xpmem_perms_result(perm->uid, perm->gid, perm->mode, flag,
			get_this_cpu_local_var()->current->proc->ruid,
			get_this_cpu_local_var()->current->proc->rgid);
#endif

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}


static xpmem_apid_t xpmem_make_apid(
	struct xpmem_thread_group *ap_tg)
{
	long apid = 0;
	xpmem_id_t debug_id;
#ifndef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;
	int uniq;
#endif

	XPMEM_DEBUG("call: ap_tg=0x%p, uniq_apid=%d", 
		ap_tg, ihk_atomic_read(&ap_tg->uniq_apid));

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	apid = xpmem_make_object_id_body_result(ap_tg,
			&xpmem_make_apid_offsets, xpmem_atomic_inc_bridge,
			xpmem_atomic_dec_bridge, xpmem_bug_on_bridge);
	if (apid < 0) {
		return apid;
	}
#else
	uniq = ihk_atomic_inc_return(&ap_tg->uniq_apid);
	ret = xpmem_make_id_result(ap_tg->tgid, uniq, &apid);
	if (ret) {
		ihk_atomic_dec(&ap_tg->uniq_apid);
		return ret;
	}

	DBUG_ON(apid <= 0);
#endif
	debug_id.apid = apid;

	XPMEM_DEBUG("return: apid=0x%lx, apid.tgid=%d, apid.uniq=%d", 
		apid, debug_id.xpmem_id.tgid, debug_id.xpmem_id.uniq);

	return apid;
}


static int xpmem_release(
	xpmem_apid_t apid)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: apid=0x%lx", apid);

	ret = xpmem_release_body_result(apid,
			get_this_cpu_local_var()->current->proc->pid,
			&xpmem_tg_id_offsets,
			xpmem_tg_ref_by_apid_bridge,
			xpmem_ap_ref_by_apid_bridge,
			xpmem_release_ap_bridge,
			xpmem_ap_deref_bridge,
			xpmem_tg_deref_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
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

	ret = xpmem_owner_policy_result(get_this_cpu_local_var()->current->proc->pid,
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
#endif
}


static void xpmem_release_ap(
	struct xpmem_thread_group *ap_tg,
	struct xpmem_access_permit *ap)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	(void)xpmem_release_ap_body_result(ap_tg, ap,
			&xpmem_release_ap_offsets, &lock,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_list_del_init_bridge,
			xpmem_att_ref_bridge, xpmem_detach_att_bridge,
			xpmem_att_deref_bridge, xpmem_seg_deref_bridge,
			xpmem_tg_deref_bridge, xpmem_ap_destroyable_bridge,
			xpmem_release_ap_log_bridge);
#else
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
		att = ((struct xpmem_attachment *)((char *)((&ap->att_list)->next) - offsetof(struct xpmem_attachment, att_list)));
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
#endif
}


static void xpmem_release_aps_of_tg(
	struct xpmem_thread_group *ap_tg)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	(void)xpmem_release_aps_of_tg_body_result(ap_tg,
			&xpmem_release_aps_offsets, &lock,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_ap_ref_bridge,
			xpmem_release_ap_bridge,
			xpmem_ap_deref_bridge,
			xpmem_release_aps_log_bridge);
#else
	struct xpmem_hashlist *hashlist;
	struct xpmem_access_permit *ap;
	struct mcs_rwlock_node_irqsave lock;
	int index;

	XPMEM_DEBUG("call: tgid=%d", ap_tg->tgid);

	for (index = 0; index < XPMEM_AP_HASHTABLE_SIZE; index++) {
		hashlist = &ap_tg->ap_hashtable[index];

		mcs_rwlock_writer_lock(&hashlist->lock, &lock);
		while (!list_empty(&hashlist->list)) {
			ap = ((struct xpmem_access_permit *)((char *)((&hashlist->list)->next) - offsetof(struct xpmem_access_permit, ap_hashlist)));
			xpmem_ap_ref(ap);
			mcs_rwlock_writer_unlock(&hashlist->lock, &lock);

			xpmem_release_ap(ap_tg, ap);

			xpmem_ap_deref(ap);

			mcs_rwlock_writer_lock(&hashlist->lock, &lock);
		}
		mcs_rwlock_writer_unlock(&hashlist->lock, &lock);
	}

	XPMEM_DEBUG("return: ");
#endif
}

static void xpmem_flush(struct mckfd *mckfd)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	(void)xpmem_flush_body_result(mckfd, (void **)&xpmem_my_part,
			&xpmem_flush_offsets, &lock,
			xpmem_tg_ref_all_nolock_bridge,
			xpmem_rwlock_writer_lock_bridge,
			xpmem_rwlock_writer_unlock_bridge,
			xpmem_list_del_init_bridge,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_release_aps_of_tg_bridge,
			xpmem_remove_segs_of_tg_bridge,
			xpmem_destroy_tg_bridge,
			xpmem_flush_log_bridge);
#else
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
#endif
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
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;
#ifdef ENABLE_FJMPI_WORKAROUND
	int fjmpi_workaround = 1;
#else
	int fjmpi_workaround = 0;
#endif

	(void)fd;
	(void)att_flags;

	XPMEM_DEBUG("call: apid=0x%lx, offset=0x%lx, size=0x%lx, vaddr=0x%lx, "
		"fd=%d, att_flags=%d",
		apid, offset, size, vaddr, fd, att_flags);

	ret = xpmem_attach_body_result(mckfd, apid, offset, size, vaddr,
			at_vaddr_p, get_this_cpu_local_var()->current->proc->pid, vm,
			fjmpi_workaround, PROT_READ | PROT_WRITE, MAP_SHARED,
			MAP_FIXED, MAP_ANONYMOUS, VR_XPMEM,
			&xpmem_attach_offsets,
			xpmem_tg_ref_by_apid_bridge,
			xpmem_ap_ref_by_apid_bridge,
			xpmem_seg_ref_bridge,
			xpmem_seg_deref_bridge,
			xpmem_tg_ref_bridge,
			xpmem_tg_deref_bridge,
			xpmem_ap_deref_bridge,
			xpmem_validate_access_bridge,
			xpmem_mckfd_alloc_bridge,
			xpmem_rwspinlock_init_bridge,
			xpmem_list_init_bridge,
			xpmem_att_not_destroyable_bridge,
			xpmem_att_ref_bridge,
			xpmem_att_deref_bridge,
			xpmem_rwspin_write_lock_bridge,
			xpmem_rwspin_write_unlock_bridge,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_list_add_tail_bridge,
			xpmem_rwspin_read_lock_noirq_bridge,
			xpmem_rwspin_read_unlock_noirq_bridge,
			xpmem_lookup_range_bridge,
			xpmem_next_range_bridge,
			xpmem_do_mmap_bridge,
			xpmem_list_del_init_bridge,
			xpmem_att_destroyable_bridge);

	XPMEM_DEBUG("return: ret=%d, at_vaddr=0x%lx", ret,
			at_vaddr_p ? *at_vaddr_p : 0);

	return ret;
#else
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
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;
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
	ret = xpmem_attach_overlap_result(get_this_cpu_local_var()->current->proc->pid,
			seg_tg->tgid, vaddr, size, seg_vaddr);
	if (ret) {
		goto out_1;
	}

	/* create new attach structure */
	att = kmalloc_tracked(sizeof(struct xpmem_attachment), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
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
#endif
}

static int xpmem_detach(
	unsigned long at_vaddr)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	XPMEM_DEBUG("call: at_vaddr=0x%lx", at_vaddr);

	ret = xpmem_detach_body_result(at_vaddr,
			get_this_cpu_local_var()->current->proc->pid, vm,
			&xpmem_detach_offsets,
			xpmem_rwspin_write_lock_noirq_bridge,
			xpmem_rwspin_write_unlock_noirq_bridge,
			xpmem_lookup_range_bridge,
			xpmem_att_ref_bridge,
			xpmem_att_deref_bridge,
			xpmem_rwspin_write_lock_bridge,
			xpmem_rwspin_write_unlock_bridge,
			xpmem_ap_ref_bridge,
			xpmem_ap_deref_bridge,
			xpmem_unpin_pages_bridge,
			xpmem_vm_munmap_bridge,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_list_del_init_bridge,
			xpmem_att_destroyable_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
	int ret;
	struct xpmem_access_permit *ap;
	struct xpmem_attachment *att;
	unsigned long at_lock;
	struct vm_range *range;
	int new_flags;
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

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

	ret = xpmem_owner_policy_result(get_this_cpu_local_var()->current->proc->pid,
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
#endif
}


static int xpmem_vm_munmap(
	struct process_vm *vm,
	void *addr,
	size_t len)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: vm=0x%p, addr=0x%p, len=0x%lx", vm, addr, len);

	ret = xpmem_vm_munmap_body_result(vm, (unsigned long)addr, len,
			xpmem_begin_free_pages_pending_bridge,
			xpmem_remove_process_range_bridge,
			xpmem_finish_free_pages_pending_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
	int ret;
	int ro_freed;

	XPMEM_DEBUG("call: vm=0x%p, addr=0x%p, len=0x%lx", vm, addr, len);

	begin_free_pages_pending();

	ret = xpmem_remove_process_range(vm, (intptr_t)addr, 
		(intptr_t)(addr + len), &ro_freed);

	finish_free_pages_pending();

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#endif
}


static int xpmem_remove_process_range(
	struct process_vm *vm,
	unsigned long start,
	unsigned long end,
	int *ro_freedp)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: vm=0x%p, start=0x%lx, end=0x%lx", vm, start, end);

	ret = xpmem_remove_process_range_body_result(vm, start, end, ro_freedp,
			&xpmem_remove_process_range_offsets,
			xpmem_lookup_range_bridge, xpmem_next_range_bridge,
			xpmem_split_range_bridge,
			xpmem_remove_private_range_bridge,
			xpmem_free_range_bridge,
			xpmem_remove_process_range_log_bridge);

	XPMEM_DEBUG("return: ret=%d, ro_freed=%d", ret,
			ro_freedp ? *ro_freedp : 0);

	return ret;
#else
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
#endif
}


static int xpmem_free_process_memory_range(
	struct process_vm *vm,
	struct vm_range *range)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: vm=0x%p, start=0x%lx, end=0x%lx",
		vm, range->start, range->end);

	ret = xpmem_free_process_range_body_result(vm, range,
			&xpmem_free_process_range_offsets,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_pt_clear_range_bridge,
			xpmem_memobj_unref_bridge,
			xpmem_range_erase_bridge,
			xpmem_kfree_bridge,
			xpmem_free_process_range_log_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
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

	kfree_tracked(range, __FILE__, __LINE__);

	XPMEM_DEBUG("return: ret=%d", 0);

	return 0;
#endif
}


static void xpmem_detach_att(
	struct xpmem_access_permit *ap,
	struct xpmem_attachment *att)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	XPMEM_DEBUG("call: apid=0x%lx, att=0x%p", ap->apid, att);
	XPMEM_DEBUG("detaching att->vm=0x%p", (void *)att->vm);

	(void)xpmem_detach_att_body_result(ap, att, &xpmem_detach_att_offsets,
			xpmem_rwspin_read_lock_noirq_bridge,
			xpmem_rwspin_read_unlock_noirq_bridge,
			xpmem_rwspin_write_lock_bridge,
			xpmem_rwspin_write_unlock_bridge,
			xpmem_lookup_range_bridge,
			xpmem_unpin_pages_bridge,
			xpmem_vm_munmap_bridge,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_list_del_init_bridge,
			xpmem_att_destroyable_bridge);

	XPMEM_DEBUG("return: ");
#else
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
#endif
}


static void xpmem_clear_PTEs(
	struct xpmem_segment *seg)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)xpmem_clear_ptes_body_result(seg, &xpmem_clear_ptes_offsets,
			xpmem_clear_ptes_range_bridge);
	return;
#else
	XPMEM_DEBUG("call: segid=0x%lx", seg->segid);

	xpmem_clear_PTEs_range(seg, seg->vaddr, seg->vaddr + seg->size);

	XPMEM_DEBUG("return: ");
#endif
}


static void xpmem_clear_PTEs_range(
	struct xpmem_segment *seg,
	unsigned long start,
	unsigned long end)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)xpmem_clear_ptes_range_body_result(seg, start, end,
			&xpmem_clear_ptes_offsets,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_ap_ref_bridge,
			xpmem_clear_ptes_of_ap_bridge,
			xpmem_ap_deref_bridge);
	return;
#else
	struct xpmem_access_permit *ap;

	XPMEM_DEBUG("call: segid=0x%lx, start=0x%lx, end=0x%lx", 
		seg->segid, start, end);

	ihk_mc_spinlock_lock_noirq(&seg->lock);

	for (ap = ((typeof(*ap) *)((char *)((&seg->ap_list)->next) - offsetof(typeof(*ap), ap_list))); &ap->ap_list != (&seg->ap_list); ap = ((typeof(*ap) *)((char *)(ap->ap_list.next) - offsetof(typeof(*ap), ap_list)))) {
		xpmem_ap_ref(ap);
		ihk_mc_spinlock_unlock_noirq(&seg->lock);

		xpmem_clear_PTEs_of_ap(ap, start, end);

		ihk_mc_spinlock_lock_noirq(&seg->lock);
		if (list_empty(&ap->ap_list)) {
			xpmem_ap_deref(ap);
			ap = ((struct xpmem_access_permit *)((char *)(&seg->ap_list) - offsetof(struct xpmem_access_permit, ap_list)));
		}
		else {
			xpmem_ap_deref(ap);
		}
	}

	ihk_mc_spinlock_unlock_noirq(&seg->lock);

	XPMEM_DEBUG("return: ");
#endif
}


static void xpmem_clear_PTEs_of_ap(
	struct xpmem_access_permit *ap,
	unsigned long start,
	unsigned long end)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)xpmem_clear_ptes_of_ap_body_result(ap, start, end,
			&xpmem_clear_ptes_offsets,
			xpmem_spin_lock_noirq_bridge,
			xpmem_spin_unlock_noirq_bridge,
			xpmem_att_ref_bridge,
			xpmem_clear_ptes_of_att_bridge,
			xpmem_att_deref_bridge);
	return;
#else
	struct xpmem_attachment *att;

	XPMEM_DEBUG("call: apid=0x%lx, start=0x%lx, end=0x%lx", 
		ap->apid, start, end);

	ihk_mc_spinlock_lock_noirq(&ap->lock);

	for (att = ((typeof(*att) *)((char *)((&ap->att_list)->next) - offsetof(typeof(*att), att_list))); &att->att_list != (&ap->att_list); att = ((typeof(*att) *)((char *)(att->att_list.next) - offsetof(typeof(*att), att_list)))) {
		if (!(att->flags & XPMEM_FLAG_VALIDPTEs))
			continue;

		xpmem_att_ref(att);
		ihk_mc_spinlock_unlock_noirq(&ap->lock);

		xpmem_clear_PTEs_of_att(att, start, end);

		ihk_mc_spinlock_lock_noirq(&ap->lock);
		if (list_empty(&att->att_list)) {
			xpmem_att_deref(att);
			att = ((struct xpmem_attachment *)((char *)(&ap->att_list) - offsetof(struct xpmem_attachment, att_list)));
		}
		else {
			xpmem_att_deref(att);
		}
	}

	ihk_mc_spinlock_unlock_noirq(&ap->lock);

	XPMEM_DEBUG("return: ");
#endif
}


static void xpmem_clear_PTEs_of_att(
	struct xpmem_attachment *att,
	unsigned long start,
	unsigned long end)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	(void)xpmem_clear_ptes_of_att_body_result(att, start, end,
			&xpmem_clear_ptes_offsets,
			xpmem_rwspin_read_lock_noirq_bridge,
			xpmem_rwspin_read_unlock_noirq_bridge,
			xpmem_rwspin_write_lock_bridge,
			xpmem_rwspin_write_unlock_bridge,
			xpmem_lookup_range_bridge,
			xpmem_unpin_pages_bridge,
			xpmem_vm_munmap_bridge);
	return;
#else
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
#endif
}


#ifndef MCKERNEL_RUST_XPMEM_HELPERS
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
#endif


static int _xpmem_fault_process_memory_range(
	struct process_vm *vm,
	struct vm_range *vmr,
	unsigned long vaddr,
	uint64_t reason,
	int page_in_remote)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: vmr=0x%p, vaddr=0x%lx, reason=0x%lx, page_in_remote: %d",
		    vmr, vaddr, reason, page_in_remote);

	ret = xpmem_fault_process_memory_range_body_result(vm, vmr, vaddr,
			reason, page_in_remote,
			get_this_cpu_local_var()->current->proc->pid,
			get_this_cpu_local_var()->current->proc->vm,
			&xpmem_fault_process_range_offsets,
			&xpmem_fault_process_range_ops);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
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
	DBUG_ON(get_this_cpu_local_var()->current->proc->pid != ap_tg->tgid);
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
#endif
}

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
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
#endif

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
int xpmem_update_process_page_table(
	struct process_vm *vm, struct vm_range *vmr)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	int ret;

	XPMEM_DEBUG("call: vmr=0x%p", vmr);

	ret = xpmem_update_process_page_table_body_result(vm, vmr,
			get_this_cpu_local_var()->current->proc->pid,
			xpmem_page_in_remote_on_attach,
			&xpmem_update_page_table_offsets,
			xpmem_att_ref_bridge,
			xpmem_att_deref_bridge,
			xpmem_ap_ref_bridge,
			xpmem_ap_deref_bridge,
			xpmem_tg_ref_bridge,
			xpmem_tg_deref_bridge,
			xpmem_seg_ref_bridge,
			xpmem_seg_deref_bridge,
			xpmem_bug_on_bridge,
			xpmem_fault_range_page_in_bridge,
			xpmem_pt_lookup_pte_bridge,
			xpmem_pte_present_bridge,
			xpmem_update_page_table_log_bridge);

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
#else
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

	DBUG_ON(get_this_cpu_local_var()->current->proc->pid != ap_tg->tgid);
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
#endif
}
#endif

static int xpmem_ensure_valid_page(
	struct xpmem_segment *seg,
	unsigned long vaddr,
	int page_in)
{
	int ret;
#ifndef MCKERNEL_RUST_XPMEM_HELPERS
	struct xpmem_thread_group *seg_tg = seg->tg;
#endif

	XPMEM_DEBUG("call: segid=0x%lx, vaddr=0x%lx", seg->segid, vaddr);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_ensure_valid_page_body_result(seg, vaddr, page_in,
			&xpmem_ensure_valid_page_offsets,
			xpmem_pin_page_bridge);
#else
	ret = xpmem_destroying_error_result(seg->flags, -ENOENT);
	if (ret)
		return ret;

	ret = xpmem_pin_page(seg_tg, seg_tg->group_leader, seg_tg->vm, vaddr,
			     page_in);
#endif

	XPMEM_DEBUG("return: ret=%d", ret);

	return ret;
}


static pte_t * xpmem_vaddr_to_pte(
	struct process_vm *vm,
	unsigned long vaddr,
	size_t *pgsize)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	return xpmem_vaddr_to_pte_body_result(vm, vaddr, pgsize,
			&xpmem_vaddr_to_pte_offsets,
			xpmem_lookup_range_bridge,
			xpmem_pt_lookup_pte_bridge);
#else
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
#endif
}


static int xpmem_pin_page(
	struct xpmem_thread_group *tg,
	struct thread *src_thread,
	struct process_vm *src_vm,
	unsigned long vaddr,
	int page_in)
{
	int ret = 0;
#ifndef MCKERNEL_RUST_XPMEM_HELPERS
	struct vm_range *range;
#endif

	XPMEM_DEBUG("call: tgid=%d, vaddr=0x%lx", tg->tgid, vaddr);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_pin_page_body_result(tg, src_thread, src_vm,
			get_this_cpu_local_var()->current->proc->vm, vaddr, page_in,
			&xpmem_pin_page_offsets,
			xpmem_rwspin_read_lock_noirq_bridge,
			xpmem_rwspin_read_unlock_noirq_bridge,
			xpmem_lookup_range_bridge, xpmem_page_fault_vm_bridge,
			xpmem_page_fault_range_bridge,
			xpmem_atomic_inc_bridge);
#else
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
#endif
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
#ifndef MCKERNEL_RUST_XPMEM_HELPERS
	size_t vsize = 0;
	unsigned long end = vaddr + size;
	pte_t *pte = NULL;
#endif

	XPMEM_DEBUG("call: segid=0x%lx, vaddr=0x%lx, size=0x%lx", 
		seg->segid, vaddr, size);

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	n_pgs_unpinned = xpmem_unpin_pages_body_result(seg, vm, vaddr, size,
			&xpmem_unpin_pages_offsets,
			xpmem_vaddr_to_pte_bridge,
			xpmem_pte_present_bridge,
			xpmem_atomic_sub_bridge);
	XPMEM_DEBUG("sub: tg->n_pinned=%d, n_pgs_unpinned=%d",
		seg->tg->n_pinned, n_pgs_unpinned);
#else
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
#endif

	XPMEM_DEBUG("return: ");
}


static struct xpmem_thread_group *__xpmem_tg_ref_by_tgid_nolock_internal(
	pid_t tgid,
	int index,
	int return_destroying)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	return (struct xpmem_thread_group *)
		xpmem_tg_ref_by_tgid_nolock_body_result(xpmem_my_part, tgid,
				index, return_destroying,
				&xpmem_tg_lookup_offsets, xpmem_tg_ref_bridge);
#else
	struct xpmem_thread_group *tg;
	int lookup;

	for (tg = ((typeof(*tg) *)((char *)((&xpmem_my_part->tg_hashtable[index].list)->next) - offsetof(typeof(*tg), tg_hashlist))); &tg->tg_hashlist != (&xpmem_my_part->tg_hashtable[index].list); tg = ((typeof(*tg) *)((char *)(tg->tg_hashlist.next) - offsetof(typeof(*tg), tg_hashlist)))) {
		lookup = xpmem_object_lookup_decision_result(tg->tgid, tgid,
				tg->flags, return_destroying, 0);
		if (lookup == XPMEM_LOOKUP_TAKE) {

			xpmem_tg_ref(tg);

			return tg;
		}
	}

	return ERR_PTR(-ENOENT);
#endif
}

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
static struct xpmem_thread_group *xpmem_tg_ref_by_tgid_fallback(
	pid_t tgid,
	int return_destroying,
	int locked)
{
	struct xpmem_thread_group *tg;
	int index;
	struct mcs_rwlock_node_irqsave lock;

	XPMEM_DEBUG("call: tgid=%d, return_destroying=%d",
			tgid, return_destroying);

	index = xpmem_tg_hashtable_index(tgid);
	if (locked) {
		XPMEM_DEBUG("xpmem_my_part=%p\n", xpmem_my_part);
		XPMEM_DEBUG("xpmem_my_part->tg_hashtable=%p\n",
				xpmem_my_part->tg_hashtable);
		mcs_rwlock_reader_lock(&xpmem_my_part->tg_hashtable[index].lock,
				&lock);
	}

	tg = __xpmem_tg_ref_by_tgid_nolock_internal(tgid, index,
			return_destroying);

	if (locked) {
		mcs_rwlock_reader_unlock(
				&xpmem_my_part->tg_hashtable[index].lock, &lock);
	}

	XPMEM_DEBUG("return: tg=0x%p", tg);

	return tg;
}

struct xpmem_thread_group *xpmem_tg_ref_by_tgid(pid_t tgid)
{
	return xpmem_tg_ref_by_tgid_fallback(tgid, 0, 1);
}

struct xpmem_thread_group *xpmem_tg_ref_by_tgid_all(pid_t tgid)
{
	return xpmem_tg_ref_by_tgid_fallback(tgid, 1, 1);
}

struct xpmem_thread_group *xpmem_tg_ref_by_tgid_nolock(pid_t tgid)
{
	return xpmem_tg_ref_by_tgid_fallback(tgid, 0, 0);
}

struct xpmem_thread_group *xpmem_tg_ref_by_tgid_all_nolock(pid_t tgid)
{
	return xpmem_tg_ref_by_tgid_fallback(tgid, 1, 0);
}
#endif


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
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	xpmem_deref_body_result(tg, &xpmem_tg_deref_offsets, 0,
			xpmem_atomic_read_bridge, xpmem_atomic_dec_bridge,
			xpmem_bug_on_bridge, xpmem_tg_deref_log_bridge,
			xpmem_kfree_bridge);
#else
	DBUG_ON(ihk_atomic_read(&tg->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&tg->refcnt))) {
		/*XPMEM_DEBUG("return: tg->refcnt=%d, tg->n_pinned=%d", 
		  tg->refcnt, tg->n_pinned);*/
		return;
	}

	XPMEM_DEBUG("kfree(): tg=0x%p", tg);
	kfree_tracked(tg, __FILE__, __LINE__);
#endif
}


static struct xpmem_segment * xpmem_seg_ref_by_segid(
	struct xpmem_thread_group *seg_tg,
	xpmem_segid_t segid)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	return (struct xpmem_segment *)
		xpmem_seg_ref_by_segid_body_result(seg_tg, segid,
				&xpmem_seg_lookup_offsets, &lock,
				xpmem_rwlock_reader_lock_bridge,
				xpmem_rwlock_reader_unlock_bridge,
				xpmem_seg_ref_bridge);
#else
	struct xpmem_segment *seg;
	struct mcs_rwlock_node_irqsave lock;
	int lookup;

	mcs_rwlock_reader_lock(&seg_tg->seg_list_lock, &lock);

	for (seg = ((typeof(*seg) *)((char *)((&seg_tg->seg_list)->next) - offsetof(typeof(*seg), seg_list))); &seg->seg_list != (&seg_tg->seg_list); seg = ((typeof(*seg) *)((char *)(seg->seg_list.next) - offsetof(typeof(*seg), seg_list)))) {
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
#endif
}


static void xpmem_seg_deref(struct xpmem_segment *seg)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	xpmem_deref_body_result(seg, &xpmem_seg_deref_offsets, 1,
			xpmem_atomic_read_bridge, xpmem_atomic_dec_bridge,
			xpmem_bug_on_bridge, xpmem_seg_deref_log_bridge,
			xpmem_kfree_bridge);
#else
	DBUG_ON(ihk_atomic_read(&seg->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&seg->refcnt))) {
		//XPMEM_DEBUG("return: seg->refcnt=%d", seg->refcnt);
		return;
	}

	DBUG_ON(!(seg->flags & XPMEM_FLAG_DESTROYING));

	XPMEM_DEBUG("kfree(): seg=0x%p", seg);
	kfree_tracked(seg, __FILE__, __LINE__);
#endif
}


static struct xpmem_access_permit * xpmem_ap_ref_by_apid(
	struct xpmem_thread_group *ap_tg,
	xpmem_apid_t apid)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	struct mcs_rwlock_node_irqsave lock;

	return (struct xpmem_access_permit *)
		xpmem_ap_ref_by_apid_body_result(ap_tg, apid,
				&xpmem_ap_lookup_offsets, &lock,
				xpmem_rwlock_reader_lock_bridge,
				xpmem_rwlock_reader_unlock_bridge,
				xpmem_ap_ref_bridge);
#else
	int index;
	struct xpmem_access_permit *ap;
	struct mcs_rwlock_node_irqsave lock;
	int lookup;

	index = xpmem_ap_hashtable_index(apid);
	mcs_rwlock_reader_lock(&ap_tg->ap_hashtable[index].lock, &lock);

	for (ap = ((typeof(*ap) *)((char *)((&ap_tg->ap_hashtable[index].list)->next) - offsetof(typeof(*ap), ap_hashlist))); &ap->ap_hashlist != (&ap_tg->ap_hashtable[index].list); ap = ((typeof(*ap) *)((char *)(ap->ap_hashlist.next) - offsetof(typeof(*ap), ap_hashlist)))) {
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
#endif
}


static void xpmem_ap_deref(struct xpmem_access_permit *ap)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	xpmem_deref_body_result(ap, &xpmem_ap_deref_offsets, 1,
			xpmem_atomic_read_bridge, xpmem_atomic_dec_bridge,
			xpmem_bug_on_bridge, xpmem_ap_deref_log_bridge,
			xpmem_kfree_bridge);
#else
	DBUG_ON(ihk_atomic_read(&ap->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&ap->refcnt))) {
		//XPMEM_DEBUG("return: ap->refcnt=%d", ap->refcnt);
		return;
	}

	DBUG_ON(!(ap->flags & XPMEM_FLAG_DESTROYING));

	XPMEM_DEBUG("kfree(): ap=0x%p", ap);
	kfree_tracked(ap, __FILE__, __LINE__);
#endif
}


static void xpmem_att_deref(struct xpmem_attachment *att)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	xpmem_deref_body_result(att, &xpmem_att_deref_offsets, 1,
			xpmem_atomic_read_bridge, xpmem_atomic_dec_bridge,
			xpmem_bug_on_bridge, xpmem_att_deref_log_bridge,
			xpmem_kfree_bridge);
#else
	DBUG_ON(ihk_atomic_read(&att->refcnt) <= 0);
	if (!xpmem_ref_drop_should_free_result(
				ihk_atomic_dec_return(&att->refcnt))) {
		//XPMEM_DEBUG("return: att->refcnt=%d", att->refcnt);
		return;
	}

	DBUG_ON(!(att->flags & XPMEM_FLAG_DESTROYING));

	XPMEM_DEBUG("kfree(): att=0x%p", att);
	kfree_tracked(att, __FILE__, __LINE__);
#endif
}

#ifndef MCKERNEL_RUST_XPMEM_HELPERS
void xpmem_tg_not_destroyable(struct xpmem_thread_group *tg)
{
	ihk_atomic_set(&tg->refcnt, 1);

	XPMEM_DEBUG("return: tg->refcnt=%d", tg->refcnt);
}

void xpmem_tg_destroyable(struct xpmem_thread_group *tg)
{
	XPMEM_DEBUG("call: ");

	xpmem_tg_deref(tg);

	XPMEM_DEBUG("return: ");
}

void xpmem_seg_not_destroyable(struct xpmem_segment *seg)
{
	ihk_atomic_set(&seg->refcnt, 1);

	XPMEM_DEBUG("return: seg->refcnt=%d", seg->refcnt);
}

void xpmem_seg_destroyable(struct xpmem_segment *seg)
{
	XPMEM_DEBUG("call: ");

	xpmem_seg_deref(seg);

	XPMEM_DEBUG("return: ");
}

void xpmem_ap_not_destroyable(struct xpmem_access_permit *ap)
{
	ihk_atomic_set(&ap->refcnt, 1);

	XPMEM_DEBUG("return: ap->refcnt=%d", ap->refcnt);
}

void xpmem_ap_destroyable(struct xpmem_access_permit *ap)
{
	XPMEM_DEBUG("call: ");

	xpmem_ap_deref(ap);

	XPMEM_DEBUG("return: ");
}

void xpmem_att_not_destroyable(struct xpmem_attachment *att)
{
	ihk_atomic_set(&att->refcnt, 1);

	XPMEM_DEBUG("return: att->refcnt=%d", att->refcnt);
}

void xpmem_att_destroyable(struct xpmem_attachment *att)
{
	XPMEM_DEBUG("call: ");

	xpmem_att_deref(att);

	XPMEM_DEBUG("return: ");
}

void xpmem_tg_ref(struct xpmem_thread_group *tg)
{
	DBUG_ON(ihk_atomic_read(&tg->refcnt) <= 0);
	ihk_atomic_inc(&tg->refcnt);

	//XPMEM_DEBUG("return: tg->refcnt=%d", tg->refcnt);
}

void xpmem_seg_ref(struct xpmem_segment *seg)
{
	DBUG_ON(ihk_atomic_read(&seg->refcnt) <= 0);
	ihk_atomic_inc(&seg->refcnt);

	//XPMEM_DEBUG("return: seg->refcnt=%d", seg->refcnt);
}

void xpmem_ap_ref(struct xpmem_access_permit *ap)
{
	DBUG_ON(ihk_atomic_read(&ap->refcnt) <= 0);
	ihk_atomic_inc(&ap->refcnt);

	//XPMEM_DEBUG("return: ap->refcnt=%d", ap->refcnt);
}

void xpmem_att_ref(struct xpmem_attachment *att)
{
	DBUG_ON(ihk_atomic_read(&att->refcnt) <= 0);
	ihk_atomic_inc(&att->refcnt);

	//XPMEM_DEBUG("return: att->refcnt=%d", att->refcnt);
}

int xpmem_is_private_data(struct vm_range *vmr)
{
	return vmr && vmr->private_data != NULL;
}
#endif


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

#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	ret = xpmem_validate_access_body_result(ap,
			get_this_cpu_local_var()->current->proc, offset, size, mode, vaddr,
			&xpmem_validate_access_offsets);
#else
	ret = xpmem_validate_access_result(get_this_cpu_local_var()->current->proc->pid,
			ap->tg->tgid, ap->mode, ap->seg->vaddr, ap->seg->size,
			offset, size, mode, vaddr);
#endif
	if (ret) {
		return ret;
	}

	XPMEM_DEBUG("return: ret=%d, vaddr=0x%lx", 0, *vaddr);

	return 0;
}

static int is_remote_vm(struct process_vm *vm)
{
#ifdef MCKERNEL_RUST_XPMEM_HELPERS
	return xpmem_is_remote_vm_body_result(get_this_cpu_local_var()->current->proc, vm,
			&xpmem_validate_access_offsets);
#else
	int ret = 0;

	if (get_this_cpu_local_var()->current->proc->vm != vm) {
		/* vm is not mine */
		ret = 1;
	}

	return ret;
#endif
}
