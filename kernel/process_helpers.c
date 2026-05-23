/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <process.h>
#include <process_helpers.h>
#include <string.h>

#ifndef MCKERNEL_RUST_PROCESS_HELPERS

enum ihk_mc_pt_attribute common_vrflag_to_ptattr(unsigned long flag, uint64_t fault,
						 pte_t *ptep)
{
	enum ihk_mc_pt_attribute attr;

	attr = PTATTR_USER | PTATTR_FOR_USER;

	if (flag & VR_REMOTE) {
		attr |= IHK_PTA_REMOTE;
	}
	else if (flag & VR_IO_NOCACHE) {
		attr |= PTATTR_UNCACHABLE;
	}

	if ((flag & VR_PROT_MASK) != VR_PROT_NONE) {
		attr |= PTATTR_ACTIVE;
	}

	if (flag & VR_PROT_WRITE) {
		attr |= PTATTR_WRITABLE;
	}

	if (!(flag & VR_PROT_EXEC)) {
		attr |= PTATTR_NO_EXECUTE;
	}

	if (flag & VR_WRITE_COMBINED) {
		attr |= PTATTR_WRITE_COMBINED;
	}

	return attr;
}

int process_split_pgshift_result(int pgshift, uintptr_t addr)
{
	if (pgshift > 0 && pgshift < (int)(sizeof(unsigned long) * 8) &&
	    (addr & ((1UL << pgshift) - 1)))
		return 0;

	return pgshift;
}

int process_add_range_bounds_result(unsigned long user_start,
				    unsigned long user_end,
				    unsigned long start,
				    unsigned long end)
{
	return (start < user_start || user_end < end) ? -EINVAL : 0;
}

int process_extend_up_result(unsigned long current_end,
			     unsigned long user_end, int has_next,
			     unsigned long next_start,
			     unsigned long newend)
{
	if (newend <= current_end)
		return -EINVAL;
	if (user_end < newend)
		return -EPERM;
	if (has_next && next_start < newend)
		return -ENOMEM;

	return 0;
}

unsigned long process_change_prot_newflag_result(unsigned long oldflag,
						 unsigned long protflag)
{
	return (oldflag & ~VR_PROT_MASK) | (protflag & VR_PROT_MASK);
}

void process_attr_delta_result(unsigned long oldattr, unsigned long newattr,
			       unsigned long *clrattrp,
			       unsigned long *setattrp)
{
	*clrattrp = oldattr & ~newattr;
	*setattrp = newattr & ~oldattr;
}

unsigned long process_private_file_setattr_result(int has_memobj,
						  unsigned long range_flags,
						  unsigned int memobj_flags,
						  unsigned long setattr)
{
	if (has_memobj && (range_flags & VR_PRIVATE) &&
	    !(memobj_flags & MF_HUGETLBFS))
		setattr &= ~PTATTR_WRITABLE;

	return setattr;
}

int process_remove_region_alignment_result(unsigned long start,
					   unsigned long end)
{
	return ((start & (PAGE_SIZE - 1)) || (end & (PAGE_SIZE - 1))) ?
		-EINVAL : 0;
}

int process_access_initial_result(int has_range, unsigned long range_start,
				  unsigned long addr)
{
	return (!has_range || range_start > addr) ? -EFAULT : 0;
}

int process_access_adjacent_result(unsigned long range_end, int has_next,
				   unsigned long next_start)
{
	return (!has_next || range_end != next_start) ? -EFAULT : 0;
}

int process_access_permission_result(int verify_type, unsigned long flags)
{
	if ((verify_type == VERIFY_WRITE && !(flags & VR_PROT_WRITE)) ||
	    (verify_type == VERIFY_READ && !(flags & VR_PROT_READ)))
		return -EACCES;

	return 0;
}

int process_range_cache_hit_result(unsigned long cache_start,
				   unsigned long cache_end,
				   unsigned long start,
				   unsigned long end)
{
	return cache_start <= start && cache_end >= end;
}

int process_lookup_range_relation_result(unsigned long start,
					 unsigned long end,
					 unsigned long range_start,
					 unsigned long range_end)
{
	if (end <= range_start)
		return -1;
	if (start >= range_end)
		return 1;
	if (start < range_start)
		return -2;
	return 0;
}

int process_range_cache_replace_result(struct vm_range **cache, int count,
				       struct vm_range *from,
				       struct vm_range *to)
{
	int i;
	int replaced = 0;

	if (!cache || count <= 0 || !from)
		return 0;

	for (i = 0; i < count; ++i) {
		if (cache[i] == from) {
			cache[i] = to;
			replaced++;
		}
	}

	return replaced;
}

int process_range_cache_store_result(struct vm_range **cache, int count,
				     int *indexp, struct vm_range *match)
{
	if (!cache || count <= 0 || !indexp || !match)
		return -EINVAL;

	*indexp = (*indexp - 1 + count) % count;
	cache[*indexp] = match;
	return *indexp;
}

int process_range_end_commit_result(struct vm_range *range, uintptr_t newend)
{
	if (!range)
		return 0;

	range->end = newend;
	return 1;
}

int process_range_flag_commit_result(struct vm_range *range,
				     unsigned long newflag)
{
	if (!range)
		return 0;

	range->flag = newflag;
	return 1;
}

int process_range_stack_start_commit_result(struct vm_range *range,
					    uintptr_t fault_addr,
					    int pgshift)
{
	if (!range)
		return 0;

	if (pgshift > 0 && pgshift < (int)(sizeof(unsigned long) * 8))
		range->start = fault_addr & ~((1UL << pgshift) - 1);
	else if (pgshift == 0)
		range->start = fault_addr & PAGE_MASK;
	else
		return 0;

	return 1;
}

void process_remove_range_step_result(unsigned long range_start,
				      unsigned long range_end,
				      unsigned long remove_start,
				      unsigned long remove_end,
				      unsigned long range_flags,
				      unsigned long private_data,
				      int *split_startp, int *split_endp,
				      int *ro_freedp, int *xpmem_removep)
{
	if (split_startp)
		*split_startp = range_start < remove_start;
	if (split_endp)
		*split_endp = remove_end < range_end;
	if (ro_freedp)
		*ro_freedp = !(range_flags & VR_PROT_WRITE);
	if (xpmem_removep)
		*xpmem_removep = private_data != 0;
}

int process_split_range_init_result(const struct vm_range *low,
				    struct vm_range *high, uintptr_t addr)
{
	if (!low || !high)
		return 0;

	high->start = addr;
	high->straight_start = 0;
	if (low->straight_start)
		high->straight_start =
			low->straight_start + (addr - low->start);
	high->end = low->end;
	high->flag = low->flag;
	high->pgshift = low->pgshift;
	high->private_data = low->private_data;

	if (low->memobj) {
		high->memobj = low->memobj;
		high->objoff = low->objoff + (addr - low->start);
	}
	else {
		high->memobj = NULL;
		high->objoff = 0;
	}

	return 1;
}

void process_split_range_commit_result(struct vm_range *low, uintptr_t addr)
{
	if (low)
		low->end = addr;
}

int process_join_range_prepare_result(struct vm_range *surviving,
				      const struct vm_range *merging)
{
	if (!surviving || !merging)
		return -EINVAL;

	if ((surviving->end != merging->start)
			|| (surviving->flag != merging->flag)
			|| (surviving->memobj != merging->memobj))
		return -EINVAL;

	if (surviving->memobj != NULL) {
		size_t len;
		off_t endoff;

		len = surviving->end - surviving->start;
		endoff = surviving->objoff + len;
		if (endoff != merging->objoff)
			return -EINVAL;
	}

	surviving->end = merging->end;
	return 0;
}

int process_ref_release_should_destroy_result(int dec_and_test)
{
	return dec_and_test != 0;
}

int process_release_address_space_should_destroy_result(int dec_and_test)
{
	return dec_and_test != 0;
}

int process_release_address_space_should_run_free_cb_result(
	unsigned long free_cb_addr)
{
	return free_cb_addr != 0;
}

int process_create_cpu_allowed_result(int cpu, int num_processors)
{
	return cpu >= 0 && cpu < num_processors;
}

int process_create_use_default_cpu_set_result(int cpu_set_empty)
{
	return cpu_set_empty != 0;
}

int process_address_space_pid_detach_result(int *pids, int nslots, int pid)
{
	int i;

	if (!pids || nslots <= 0)
		return -1;

	for (i = 0; i < nslots; i++) {
		if (pids[i] == pid) {
			pids[i] = 0;
			return i;
		}
	}

	return -1;
}

int process_clone_shares_vm_result(int clone_flags)
{
	return (clone_flags & CLONE_VM) != 0;
}

int process_clone_shares_sighand_result(int clone_flags)
{
	return (clone_flags & CLONE_SIGHAND) != 0;
}

int process_mckfd_should_dup_result(unsigned long dup_cb_addr)
{
	return dup_cb_addr != 0;
}

int process_clone_copy_vm_thread_state_result(
	void *dst_vm, const void *src_vm, unsigned long vdso_offset,
	unsigned long vvar_offset, void *dst_thread, const void *src_thread,
	unsigned long sigstack_offset, size_t sigstack_size)
{
	char *dvm = dst_vm;
	const char *svm = src_vm;
	char *dthread = dst_thread;
	const char *sthread = src_thread;

	if (!dvm || !svm || !dthread || !sthread)
		return 0;

	*(void **)(dvm + vdso_offset) = *(void * const *)(svm + vdso_offset);
	*(void **)(dvm + vvar_offset) = *(void * const *)(svm + vvar_offset);
	memcpy(dthread + sigstack_offset, sthread + sigstack_offset,
	       sigstack_size);

	return 1;
}

int process_tid_index_for_thread_result(const void *tids, int nr_tids,
					unsigned long entry_stride,
					unsigned long thread_offset,
					unsigned long thread_addr)
{
	const char *base = tids;
	int i;

	if (!tids || nr_tids <= 0 || entry_stride == 0 || thread_addr == 0)
		return -1;

	for (i = 0; i < nr_tids; ++i) {
		const unsigned long *slot =
			(const unsigned long *)(base + i * entry_stride +
						thread_offset);

		if (*slot == thread_addr)
			return i;
	}

	return -1;
}

int process_tid_index_found_result(int index)
{
	return index >= 0;
}

static void *process_entry_member_addr(void *base, int index,
				       unsigned long entry_stride,
				       unsigned long member_offset)
{
	if (!base || index < 0 || entry_stride == 0)
		return NULL;

	return (char *)base + (unsigned long)index * entry_stride +
		member_offset;
}

int process_tid_release_slot_result(void *tids, int index,
				    unsigned long entry_stride,
				    unsigned long thread_offset)
{
	unsigned long *thread_slot;

	thread_slot = process_entry_member_addr(tids, index, entry_stride,
						thread_offset);
	if (!thread_slot)
		return 0;

	*thread_slot = 0;
	return 1;
}

int process_tid_replace_slot_result(void *tids, int index,
				    unsigned long entry_stride,
				    unsigned long tid_offset,
				    unsigned long thread_offset,
				    int new_tid)
{
	int *tid_slot;
	unsigned long *thread_slot;

	tid_slot = process_entry_member_addr(tids, index, entry_stride,
					     tid_offset);
	thread_slot = process_entry_member_addr(tids, index, entry_stride,
						thread_offset);
	if (!tid_slot || !thread_slot)
		return 0;

	*thread_slot = 0;
	*tid_slot = new_tid;
	return 1;
}

int process_sigpending_cleanup_needed_result(int list_empty)
{
	return list_empty == 0;
}

void *process_sigpending_pop_front_result(struct list_head *head,
					  unsigned long list_offset)
{
	struct list_head *first;
	struct list_head *next;

	if (!head)
		return NULL;

	first = head->next;
	if (!first || first == head)
		return NULL;

	next = first->next;
	head->next = next;
	if (next)
		next->prev = head;
	first->next = LIST_POISON1;
	first->prev = LIST_POISON2;

	return (char *)first - list_offset;
}

int process_list_is_linked_result(const struct list_head *entry)
{
	if (!entry || !entry->next)
		return 0;

	return entry->next != entry;
}

static int process_list_detach_inner(struct list_head *entry)
{
	struct list_head *prev;
	struct list_head *next;

	if (!entry)
		return 0;

	prev = entry->prev;
	next = entry->next;
	if (!prev || !next || next == entry)
		return 0;

	next->prev = prev;
	prev->next = next;
	entry->next = LIST_POISON1;
	entry->prev = LIST_POISON2;
	return 1;
}

void process_list_detach_result(struct list_head *entry)
{
	process_list_detach_inner(entry);
}

int process_list_detach_counted_result(struct list_head *entry,
				       size_t *lenp)
{
	if (!lenp || !process_list_detach_inner(entry))
		return 0;

	*lenp -= 1;
	return 1;
}

static int process_list_add_tail_inner(struct list_head *entry,
				       struct list_head *head)
{
	struct list_head *prev;

	if (!entry || !head)
		return 0;

	prev = head->prev;
	if (!prev)
		return 0;

	entry->next = head;
	entry->prev = prev;
	prev->next = entry;
	head->prev = entry;
	return 1;
}

void process_list_add_tail_result(struct list_head *entry,
				  struct list_head *head)
{
	process_list_add_tail_inner(entry, head);
}

int process_list_add_tail_counted_result(struct list_head *entry,
					 struct list_head *head,
					 size_t *lenp)
{
	if (!lenp || !process_list_add_tail_inner(entry, head))
		return 0;

	*lenp += 1;
	return 1;
}

int process_list_move_tail_result(struct list_head *entry,
				  struct list_head *head)
{
	if (!entry || !head)
		return 0;
	if (!process_list_detach_inner(entry))
		return 0;
	if (!process_list_add_tail_inner(entry, head))
		return 0;
	return 1;
}

int process_list_del_init_result(struct list_head *entry)
{
	if (!entry || !entry->prev || !entry->next)
		return 0;

	if (entry->next != entry) {
		entry->next->prev = entry->prev;
		entry->prev->next = entry->next;
	}
	INIT_LIST_HEAD(entry);
	return 1;
}

int process_child_reparent_result(void *child,
				  unsigned long ppid_parent_offset,
				  unsigned long parent_offset,
				  void *new_parent,
				  struct list_head *entry,
				  struct list_head *head,
				  int update_parent)
{
	char *base = child;

	if (!child || !new_parent || !entry || !head)
		return 0;

	*(void **)(base + ppid_parent_offset) = new_parent;
	if (update_parent)
		*(void **)(base + parent_offset) = new_parent;

	return process_list_move_tail_result(entry, head);
}

int process_thread_report_attach_result(void *thread,
					unsigned long termsig_offset,
					int update_termsig, int termsig,
					unsigned long report_proc_offset,
					void *report_proc,
					struct list_head *entry,
					struct list_head *head)
{
	char *base = thread;

	if (!thread || !report_proc || !entry || !head)
		return 0;

	if (update_termsig)
		*(int *)(base + termsig_offset) = termsig;
	*(void **)(base + report_proc_offset) = report_proc;

	return process_list_add_tail_inner(entry, head);
}

int process_thread_report_detach_result(void *thread,
					unsigned long report_proc_offset,
					void *report_proc,
					struct list_head *entry)
{
	char *base = thread;

	if (!thread || !entry)
		return 0;

	*(void **)(base + report_proc_offset) = report_proc;
	return process_list_detach_inner(entry);
}

int process_ptrace_main_detach_reparent_result(void *process,
					      unsigned long parent_offset,
					      void *parent,
					      struct list_head *ptraced_entry,
					      struct list_head *sibling_entry,
					      struct list_head *children_head)
{
	char *base = process;

	if (!process || !parent || !ptraced_entry || !sibling_entry ||
	    !children_head)
		return 0;
	process_list_detach_inner(ptraced_entry);
	if (!process_list_add_tail_inner(sibling_entry, children_head))
		return 0;

	*(void **)(base + parent_offset) = parent;
	return 1;
}

int process_ptrace_main_attach_reparent_result(void *process,
					      unsigned long parent_offset,
					      void *parent,
					      struct list_head *sibling_entry,
					      struct list_head *children_head)
{
	char *base = process;

	if (!process || !parent || !sibling_entry || !children_head)
		return 0;
	if (!process_list_add_tail_inner(sibling_entry, children_head))
		return 0;

	*(void **)(base + parent_offset) = parent;
	return 1;
}

int process_thread_termsig_clear_result(void *thread,
					unsigned long termsig_offset,
					int clear_termsig)
{
	char *base = thread;

	if (!thread || !clear_termsig)
		return 0;

	*(int *)(base + termsig_offset) = 0;
	return 1;
}

void *process_thread_ptrace_cleanup_result(void *thread,
					   unsigned long ptrace_offset,
					   unsigned long saved_valid_offset,
					   unsigned long debugreg_offset)
{
	char *base = thread;
	void **debugreg_slot;
	void *debugreg;

	if (!thread)
		return NULL;

	debugreg_slot = (void **)(base + debugreg_offset);
	debugreg = *debugreg_slot;
	*(int *)(base + ptrace_offset) = 0;
	*(int *)(base + saved_valid_offset) = 0;
	*debugreg_slot = NULL;
	return debugreg;
}

int process_thread_ptrace_saved_context_clear_result(
	void *thread, unsigned long saved_valid_offset)
{
	char *base = thread;

	if (!thread)
		return 0;

	*(int *)(base + saved_valid_offset) = 0;
	return 1;
}

int process_thread_ptrace_trace_syscall_update_result(
	void *thread, unsigned long ptrace_offset, int trace_syscall)
{
	char *base = thread;
	int *ptrace;

	if (!thread)
		return 0;

	ptrace = (int *)(base + ptrace_offset);
	*ptrace &= ~PT_TRACE_SYSCALL;
	if (trace_syscall)
		*ptrace |= PT_TRACE_SYSCALL;
	return *ptrace;
}

void *process_thread_ptrace_pending_signal_take_result(
	void *thread, unsigned long sendsig_offset, unsigned long recvsig_offset,
	int source)
{
	char *base = thread;
	void **slot;
	void *pending;

	if (!thread)
		return NULL;

	if (source == 1)
		slot = (void **)(base + sendsig_offset);
	else if (source == 2)
		slot = (void **)(base + recvsig_offset);
	else
		return NULL;

	pending = *slot;
	*slot = NULL;
	return pending;
}

int process_thread_signal_flags_reap_result(void *thread,
					    unsigned long signal_flags_offset,
					    int options, int clear_mask)
{
	char *base = thread;
	int *signal_flags;

	if (!thread)
		return 0;

	signal_flags = (int *)(base + signal_flags_offset);
	if (!(options & WNOWAIT))
		*signal_flags &= ~clear_mask;
	return *signal_flags;
}

int process_wait_exit_status_reap_result(void *object,
					 unsigned long exit_status_offset,
					 int options)
{
	char *base = object;
	int *exit_status;

	if (!object)
		return 0;

	exit_status = (int *)(base + exit_status_offset);
	if (!(options & WNOWAIT))
		*exit_status = 0;
	return *exit_status;
}

int process_optional_ptr_should_free_result(unsigned long ptr_addr)
{
	return ptr_addr != 0;
}

int process_hold_thread_warn_exited_result(int status)
{
	return status == PS_EXITED;
}

int process_sigcommon_release_should_destroy_result(int dec_and_test)
{
	return dec_and_test != 0;
}

int process_destroy_thread_tid_action_result(int has_tids, int is_main_thread,
					     int uti_state)
{
	if (!has_tids)
		return 0;
	if (uti_state == UTI_STATE_EPILOGUE)
		return 2;
	if (!is_main_thread)
		return 1;

	return 0;
}

int process_thread_should_free_pages_result(int is_main_thread)
{
	return !is_main_thread;
}

int process_release_vm_should_run_free_cb_result(unsigned long free_cb_addr)
{
	return free_cb_addr != 0;
}

int process_release_mckfd_should_close_result(unsigned long close_cb_addr)
{
	return close_cb_addr != 0;
}

int process_mckfd_push_head_result(struct mckfd **headp, struct mckfd *entry)
{
	if (!headp || !entry)
		return 0;

	entry->next = *headp;
	*headp = entry;
	return 1;
}

struct mckfd *process_mckfd_pop_head_result(struct mckfd **headp)
{
	struct mckfd *current;

	if (!headp)
		return NULL;

	current = *headp;
	if (!current)
		return NULL;

	*headp = current->next;
	current->next = NULL;
	return current;
}

#endif /* MCKERNEL_RUST_PROCESS_HELPERS */
