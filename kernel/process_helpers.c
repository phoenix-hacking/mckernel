/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <auxvec.h>
#include <cls.h>
#include <process.h>
#include <process_helpers.h>
#include <string.h>

#ifndef MCKERNEL_RUST_PROCESS_HELPERS

static int affinity_cpu_in_range(unsigned long cpu, unsigned long setsize)
{
	return cpu < setsize * 8;
}

static unsigned long affinity_cpu_word(unsigned long cpu)
{
	return cpu / __NCPUBITS;
}

static __cpu_mask affinity_cpu_mask(unsigned long cpu)
{
	return (__cpu_mask)1 << (cpu % __NCPUBITS);
}

unsigned long CPU_SET_S(unsigned long cpu, unsigned long setsize,
			cpu_set_t *cpusetp)
{
	__cpu_mask *bits;
	__cpu_mask value;

	if (!cpusetp || !affinity_cpu_in_range(cpu, setsize))
		return 0;

	bits = cpusetp->__bits;
	value = bits[affinity_cpu_word(cpu)] | affinity_cpu_mask(cpu);
	bits[affinity_cpu_word(cpu)] = value;
	return value;
}

int CPU_ISSET_S(unsigned long cpu, unsigned long setsize,
		const cpu_set_t *cpusetp)
{
	const __cpu_mask *bits;

	if (!cpusetp || !affinity_cpu_in_range(cpu, setsize))
		return 0;

	bits = cpusetp->__bits;
	return !!(bits[affinity_cpu_word(cpu)] & affinity_cpu_mask(cpu));
}

void CPU_ZERO_S(unsigned long setsize, cpu_set_t *cpusetp)
{
	unsigned long i;
	unsigned long imax;

	if (!cpusetp)
		return;

	imax = setsize / sizeof(__cpu_mask);
	for (i = 0; i < imax; ++i)
		cpusetp->__bits[i] = 0;
}

unsigned long CPU_SET(unsigned long cpu, cpu_set_t *cpusetp)
{
	return CPU_SET_S(cpu, sizeof(cpu_set_t), cpusetp);
}

int CPU_ISSET(unsigned long cpu, const cpu_set_t *cpusetp)
{
	return CPU_ISSET_S(cpu, sizeof(cpu_set_t), cpusetp);
}

void CPU_ZERO(cpu_set_t *cpusetp)
{
	CPU_ZERO_S(sizeof(cpu_set_t), cpusetp);
}

unsigned long PROT_TO_VR_FLAG(unsigned long prot)
{
	return (prot << 16) & VR_PROT_MASK;
}

unsigned long VRFLAG_PROT_TO_MAXPROT(unsigned long vrflag)
{
	return (vrflag & VR_PROT_MASK) << 4;
}

unsigned long VRFLAG_MAXPROT_TO_PROT(unsigned long vrflag)
{
	return (vrflag & VR_MAXPROT_MASK) >> 4;
}

int __WEXITSTATUS(int status)
{
	return (status & 0xff00) >> 8;
}

int __WTERMSIG(int status)
{
	return status & 0x7f;
}

int __WSTOPSIG(int status)
{
	return __WEXITSTATUS(status);
}

int __WIFEXITED(int status)
{
	return __WTERMSIG(status) == 0;
}

int __WIFSIGNALED(int status)
{
	return (((signed char)(((status) & 0x7f) + 1)) >> 1) > 0;
}

int __WIFSTOPPED(int status)
{
	return (status & 0xff) == 0x7f;
}

int process_hash(int pid)
{
	return pid % HASH_SIZE;
}

int thread_hash(int tid)
{
	return tid % HASH_SIZE;
}

int has_cap_ipc_lock(struct thread *th)
{
	/* CAP_IPC_LOCK (= 14) */
	return !th->proc->euid;
}

int has_cap_sys_admin(struct thread *th)
{
	/* CAP_SYS_ADMIN (= 21) */
	return !th->proc->euid;
}

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

int process_add_range_init_result(struct vm_range *range, unsigned long start,
				  unsigned long end, unsigned long flag,
				  void *memobj, off_t offset, int pgshift,
				  void *private_data)
{
	if (!range)
		return 0;

	RB_CLEAR_NODE(&range->vm_rb_node);
	range->start = start;
	range->end = end;
	range->flag = flag;
	range->memobj = memobj;
	range->objoff = offset;
	range->pgshift = pgshift;
	range->private_data = private_data;
	range->straight_start = 0;
#ifdef ENABLE_TOFU
	INIT_LIST_HEAD(&range->tofu_stag_list);
#endif
	return 1;
}

int process_add_range_mapping_result(unsigned long phys, unsigned long flag,
				     unsigned long range_flag,
				     unsigned long *attrp,
				     int *memclearp)
{
	unsigned long attr = 0;
	int action = PROCESS_ADD_RANGE_MAP_SKIP;
	int memclear = phys != NOPHYS &&
		!(flag & (VR_REMOTE | VR_DEMAND_PAGING | VR_XPMEM)) &&
		((flag & VR_PROT_MASK) != VR_PROT_NONE);

	if (phys == NOPHYS) {
		action = PROCESS_ADD_RANGE_MAP_SKIP;
	}
	else if (flag & VR_REMOTE) {
		attr = IHK_PTA_REMOTE;
		action = PROCESS_ADD_RANGE_MAP_UPDATE;
	}
	else if (flag & VR_IO_NOCACHE) {
		attr = PTATTR_UNCACHABLE;
		action = PROCESS_ADD_RANGE_MAP_UPDATE;
	}
	else if (flag & VR_XPMEM) {
		action = PROCESS_ADD_RANGE_MAP_MARK_XPMEM;
	}
	else if (flag & VR_DEMAND_PAGING) {
		action = PROCESS_ADD_RANGE_MAP_DEMAND;
	}
	else if ((range_flag & VR_PROT_MASK) == VR_PROT_NONE) {
		action = PROCESS_ADD_RANGE_MAP_SKIP;
	}
	else {
		action = PROCESS_ADD_RANGE_MAP_UPDATE;
	}

	if (attrp)
		*attrp = attr;
	if (memclearp)
		*memclearp = memclear;

	return action;
}

struct vm_range *process_add_range_alloc_result(
		unsigned long range_size,
		process_add_range_alloc_fn_t alloc_fn)
{
	if (!alloc_fn)
		return NULL;

	return alloc_fn(range_size);
}

int process_add_range_free_result(
		struct vm_range *range,
		process_add_range_free_fn_t free_fn)
{
	if (!free_fn)
		return -EINVAL;

	free_fn(range);
	return 0;
}

int process_add_range_insert_result(
		struct process_vm *vm, struct vm_range *range,
		process_add_range_insert_fn_t insert_fn)
{
	if (!insert_fn)
		return -EINVAL;

	return insert_fn(vm, range);
}

int process_add_range_update_result(
		struct process_vm *vm, struct vm_range *range,
		unsigned long phys, unsigned long attr,
		process_add_range_update_fn_t update_fn)
{
	if (!update_fn)
		return -EINVAL;

	return update_fn(vm, range, phys, attr);
}

int process_add_range_remove_result(
		struct process_vm *vm, unsigned long start, unsigned long end,
		process_add_range_remove_fn_t remove_fn)
{
	if (!remove_fn)
		return -EINVAL;

	remove_fn(vm, start, end);
	return 0;
}

int process_add_range_mark_xpmem_result(
		struct vm_range *range,
		process_add_range_mark_xpmem_fn_t mark_xpmem_fn)
{
	if (!mark_xpmem_fn)
		return -EINVAL;

	mark_xpmem_fn(range);
	return 0;
}

int process_add_range_memclear_result(
		unsigned long phys, unsigned long bytes,
		process_add_range_memclear_fn_t memclear_fn)
{
	if (!memclear_fn)
		return -EINVAL;

	memclear_fn(phys, bytes);
	return 0;
}

int process_add_range_log_result(
		int event, int rc, unsigned long start, unsigned long end,
		process_add_range_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, rc, start, end);
	return 0;
}

int process_add_range_orchestrate_result(
	struct process_vm *vm, unsigned long range_size, unsigned long start,
	unsigned long end, unsigned long phys, unsigned long flag,
	struct memobj *memobj, off_t offset, int pgshift, void *private_data,
	struct vm_range **rp, process_add_range_alloc_fn_t alloc_fn,
	process_add_range_free_fn_t free_fn,
	process_add_range_insert_fn_t insert_fn,
	process_add_range_update_fn_t update_fn,
	process_add_range_remove_fn_t remove_fn,
	process_add_range_mark_xpmem_fn_t mark_xpmem_fn,
	process_add_range_memclear_fn_t memclear_fn,
	process_add_range_log_fn_t log_fn)
{
	struct vm_range *range;
	unsigned long map_attr = 0;
	int should_memclear = 0;
	int map_action;
	int rc;

	if (!alloc_fn || !free_fn || !insert_fn || !update_fn || !remove_fn ||
	    !mark_xpmem_fn || !memclear_fn)
		return -EINVAL;

	range = process_add_range_alloc_result(range_size, alloc_fn);
	if (!range) {
		process_add_range_log_result(PROCESS_ADD_RANGE_LOG_ALLOC_FAILED,
					     -ENOMEM, start, end, log_fn);
		return -ENOMEM;
	}

	process_add_range_init_result(range, start, end, flag, memobj, offset,
			pgshift, private_data);

	rc = process_add_range_insert_result(vm, range, insert_fn);
	if (rc) {
		process_add_range_log_result(PROCESS_ADD_RANGE_LOG_INSERT_FAILED,
					     rc, start, end, log_fn);
		process_add_range_free_result(range, free_fn);
		return rc;
	}

	map_action = process_add_range_mapping_result(phys, flag, range->flag,
			&map_attr, &should_memclear);
	if (map_action == PROCESS_ADD_RANGE_MAP_UPDATE) {
		rc = process_add_range_update_result(vm, range, phys,
						     map_attr, update_fn);
	}
	else if (map_action == PROCESS_ADD_RANGE_MAP_MARK_XPMEM) {
		process_add_range_mark_xpmem_result(range, mark_xpmem_fn);
	}
	else if (map_action == PROCESS_ADD_RANGE_MAP_DEMAND) {
		process_add_range_log_result(PROCESS_ADD_RANGE_LOG_DEMAND, 0,
					     range->start, range->end,
					     log_fn);
	}

	if (rc) {
		process_add_range_log_result(PROCESS_ADD_RANGE_LOG_PREP_FAILED,
					     rc, range->start, range->end,
					     log_fn);
		process_add_range_remove_result(vm, range->start, range->end,
						remove_fn);
		process_add_range_free_result(range, free_fn);
		return rc;
	}

	if (should_memclear)
		process_add_range_memclear_result(phys, end - start,
						  memclear_fn);

	if (rp)
		*rp = range;

	return 0;
}

int process_add_range_public_body_result(
	struct process_vm *vm, unsigned long range_size,
	unsigned long user_start, unsigned long user_end,
	unsigned long start, unsigned long end, unsigned long phys,
	unsigned long flag, struct memobj *memobj, off_t offset,
	int pgshift, void *private_data, struct vm_range **rp,
	process_add_range_alloc_fn_t alloc_fn,
	process_add_range_free_fn_t free_fn,
	process_add_range_insert_fn_t insert_fn,
	process_add_range_update_fn_t update_fn,
	process_add_range_remove_fn_t remove_fn,
	process_add_range_mark_xpmem_fn_t mark_xpmem_fn,
	process_add_range_memclear_fn_t memclear_fn,
	process_add_range_log_fn_t log_fn)
{
	int rc;

	rc = process_add_range_bounds_result(user_start, user_end, start, end);
	if (rc) {
		process_add_range_log_result(PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED,
					     rc, start, end, log_fn);
		return rc;
	}

	return process_add_range_orchestrate_result(vm, range_size, start, end,
			phys, flag, memobj, offset, pgshift, private_data, rp,
			alloc_fn, free_fn, insert_fn, update_fn, remove_fn,
			mark_xpmem_fn, memclear_fn, log_fn);
}

int process_vm_range_insert_log_result(
		int event, struct process_vm *vm, struct vm_range *newrange,
		struct vm_range *range, process_vm_range_insert_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, vm, newrange, range);
	return 0;
}

int process_vm_range_insert_dump_result(
		struct process_vm *vm,
		process_vm_range_insert_dump_fn_t dump_fn)
{
	if (!dump_fn)
		return 0;

	dump_fn(vm);
	return 0;
}

int process_vm_range_insert_result(struct rb_root *root,
				   struct vm_range *newrange,
				   struct process_vm *vm,
				   process_vm_range_insert_log_fn_t log_fn,
				   process_vm_range_insert_dump_fn_t dump_fn)
{
	struct rb_node **new, *parent = NULL;
	struct vm_range *range;

	if (!root || !newrange)
		return -EINVAL;

	new = &root->rb_node;
	while (*new) {
		range = ((struct vm_range *)((char *)(*new) - offsetof(struct vm_range, vm_rb_node)));
		parent = *new;
		if (newrange->end <= range->start) {
			new = &(*new)->rb_left;
		}
		else if (newrange->start >= range->end) {
			new = &(*new)->rb_right;
		}
		else {
			process_vm_range_insert_log_result(
				PROCESS_VM_RANGE_INSERT_LOG_OVERLAP, vm,
				newrange, range, log_fn);
			return -EFAULT;
		}
	}

	process_vm_range_insert_log_result(PROCESS_VM_RANGE_INSERT_LOG_SUCCESS,
					   vm, newrange, NULL, log_fn);
	process_vm_range_insert_dump_result(vm, dump_fn);
	rb_link_node(&newrange->vm_rb_node, parent, new);
	rb_insert_color(&newrange->vm_rb_node, root);

	return 0;
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

int process_noirq_lock_result(unsigned long lock_addr,
			      process_noirq_lock_fn_t lock_fn)
{
	if (!lock_fn)
		return -EINVAL;

	lock_fn(lock_addr);
	return 0;
}

int process_noirq_unlock_result(unsigned long lock_addr,
				process_noirq_unlock_fn_t unlock_fn)
{
	if (!unlock_fn)
		return -EINVAL;

	unlock_fn(lock_addr);
	return 0;
}

int process_pt_change_attr_result(void *page_table, unsigned long start,
				  unsigned long end, unsigned long clrattr,
				  unsigned long setattr,
				  process_pt_change_attr_fn_t change_attr_fn)
{
	if (!change_attr_fn)
		return -EINVAL;

	return change_attr_fn(page_table, start, end, clrattr, setattr);
}

int process_pt_set_range_result(void *page_table, struct process_vm *vm,
				unsigned long start, unsigned long end,
				unsigned long phys, unsigned long attr,
				int pgshift, struct vm_range *range, int flags,
				process_pt_set_range_fn_t pt_set_range_fn)
{
	if (!pt_set_range_fn)
		return -EINVAL;

	return pt_set_range_fn(page_table, vm, start, end, phys, attr,
			       pgshift, range, flags);
}

int process_update_page_table_log_result(
	int error, process_update_page_table_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(error);
	return 0;
}

int process_zeroobj_match_result(void *memobj,
				 process_zeroobj_match_fn_t zeroobj_match_fn)
{
	if (!zeroobj_match_fn)
		return -EINVAL;

	return zeroobj_match_fn(memobj);
}

int process_fault_range_result(struct process_vm *vm, struct vm_range *range,
			       unsigned long fault_addr, unsigned long reason,
			       process_fault_range_fn_t fault_fn)
{
	if (!fault_fn)
		return -EINVAL;

	return fault_fn(vm, range, fault_addr, reason);
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

struct vm_range *process_lookup_memory_range_body_result(
	struct process_vm *vm, unsigned long start, unsigned long end)
{
	struct vm_range *range = NULL, *match = NULL;
	struct rb_node *node;
	int i;

	if (!vm || end <= start)
		return NULL;

	for (i = 0; i < VM_RANGE_CACHE_SIZE; ++i) {
		int c_i = (i + vm->range_cache_ind) % VM_RANGE_CACHE_SIZE;

		if (!vm->range_cache[c_i])
			continue;
		if (process_range_cache_hit_result(vm->range_cache[c_i]->start,
				vm->range_cache[c_i]->end, start, end))
			return vm->range_cache[c_i];
	}

	node = vm->vm_range_tree.rb_node;
	while (node) {
		int relation;

		range = ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node)));
		relation = process_lookup_range_relation_result(start, end,
				range->start, range->end);
		if (relation < -1) {
			match = range;
			node = node->rb_left;
		} else if (relation < 0) {
			node = node->rb_left;
		} else if (relation > 0) {
			node = node->rb_right;
		} else {
			match = range;
			break;
		}
	}

	if (match && end > match->start)
		process_range_cache_store_result(vm->range_cache,
				VM_RANGE_CACHE_SIZE, &vm->range_cache_ind,
				match);

	return match;
}

struct vm_range *process_next_memory_range_body_result(struct vm_range *range)
{
	struct rb_node *node;

	if (!range)
		return NULL;
	node = rb_next(&range->vm_rb_node);
	return node ? ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node))) : NULL;
}

struct vm_range *process_previous_memory_range_body_result(
	struct vm_range *range)
{
	struct rb_node *node;

	if (!range)
		return NULL;
	node = rb_prev(&range->vm_rb_node);
	return node ? ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node))) : NULL;
}

int process_extend_up_body_result(struct process_vm *vm,
				  struct vm_range *range,
				  unsigned long newend)
{
	struct vm_range *next;
	int error;

	if (!vm || !range)
		return -EINVAL;
	next = process_next_memory_range_body_result(range);
	error = process_extend_up_result(range->end, vm->region.user_end,
			next != NULL, next ? next->start : 0, newend);
	if (error)
		return error;
	process_range_end_commit_result(range, newend);
	return 0;
}

int process_range_public_log_result(
	int event, struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, int error,
	process_range_public_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, vm, range, start, end, error);
	return 0;
}

struct vm_range *process_lookup_memory_range_public_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_range_public_log_fn_t log_fn)
{
	struct vm_range *match;

	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER,
					vm, NULL, start, end, 0, log_fn);
	match = process_lookup_memory_range_body_result(vm, start, end);
	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT,
					vm, match, start, end, 0, log_fn);
	return match;
}

struct vm_range *process_next_memory_range_public_result(
	struct process_vm *vm, struct vm_range *range,
	process_range_public_log_fn_t log_fn)
{
	struct vm_range *next;
	unsigned long start = range ? range->start : 0;
	unsigned long end = range ? range->end : 0;

	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER,
					vm, range, start, end, 0, log_fn);
	next = process_next_memory_range_body_result(range);
	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT,
					vm, next, start, end, 0, log_fn);
	return next;
}

struct vm_range *process_previous_memory_range_public_result(
	struct process_vm *vm, struct vm_range *range,
	process_range_public_log_fn_t log_fn)
{
	struct vm_range *prev;
	unsigned long start = range ? range->start : 0;
	unsigned long end = range ? range->end : 0;

	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER,
					vm, range, start, end, 0, log_fn);
	prev = process_previous_memory_range_body_result(range);
	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT,
					vm, prev, start, end, 0, log_fn);
	return prev;
}

int process_extend_up_public_result(struct process_vm *vm,
				    struct vm_range *range,
				    unsigned long newend,
				    process_range_public_log_fn_t log_fn)
{
	int error;

	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER,
					vm, range,
					range ? range->start : 0,
					newend, 0, log_fn);
	error = process_extend_up_body_result(vm, range, newend);
	process_range_public_log_result(PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT,
					vm, range,
					range ? range->start : 0,
					newend, error, log_fn);
	return error;
}

int process_change_prot_body_result(struct process_vm *vm,
				    struct vm_range *range,
				    unsigned long protflag,
				    process_attr_from_vrflag_fn_t attr_fn,
				    process_noirq_lock_fn_t lock_fn,
				    process_noirq_unlock_fn_t unlock_fn,
				    process_pt_change_attr_fn_t change_attr_fn)
{
	unsigned long newflag;
	unsigned long oldattr, newattr;
	unsigned long clrattr, setattr;
	int error;

	if (!vm || !range)
		return -EINVAL;

	newflag = process_change_prot_newflag_result(range->flag, protflag);
	if (range->flag == newflag)
		return 0;

	if (!attr_fn)
		return -EINVAL;
	oldattr = process_attr_from_vrflag_result(range->flag, PF_POPULATE,
						  NULL, attr_fn);
	newattr = process_attr_from_vrflag_result(newflag, PF_POPULATE,
						  NULL, attr_fn);
	process_attr_delta_result(oldattr, newattr, &clrattr, &setattr);

	if (range->memobj && (range->flag & VR_PRIVATE)) {
		setattr = process_private_file_setattr_result(1, range->flag,
				range->memobj->flags, setattr);
		if (!clrattr && !setattr) {
			process_range_flag_commit_result(range, newflag);
			return 0;
		}
	}

	if (!lock_fn || !unlock_fn || !change_attr_fn || !vm->address_space)
		return -EINVAL;

	error = process_noirq_lock_result((unsigned long)&vm->page_table_lock,
					  lock_fn);
	if (error)
		return error;
	error = process_pt_change_attr_result(vm->address_space->page_table,
			range->start, range->end, clrattr, setattr,
			change_attr_fn);
	process_noirq_unlock_result((unsigned long)&vm->page_table_lock,
				    unlock_fn);
	if (error && error != -ENOENT)
		return error;

	process_range_flag_commit_result(range, newflag);
	return 0;
}

int process_change_prot_public_log_result(
	int event, struct process_vm *vm, struct vm_range *range,
	unsigned long protflag, int error,
	process_change_prot_public_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, vm, range, protflag, error);
	return 0;
}

int process_change_prot_public_result(
	struct process_vm *vm, struct vm_range *range, unsigned long protflag,
	process_attr_from_vrflag_fn_t attr_fn,
	process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_pt_change_attr_fn_t change_attr_fn,
	process_change_prot_public_log_fn_t log_fn)
{
	int error;

	process_change_prot_public_log_result(
		PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER, vm, range, protflag,
		0, log_fn);
	error = process_change_prot_body_result(vm, range, protflag, attr_fn,
			lock_fn, unlock_fn, change_attr_fn);
	if (error && error != -ENOENT)
		process_change_prot_public_log_result(
			PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR, vm, range,
			protflag, error, log_fn);
	process_change_prot_public_log_result(
		PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT, vm, range, protflag,
		error, log_fn);
	return error;
}

int process_update_page_table_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long phys,
	unsigned long populate_fault, process_attr_from_vrflag_fn_t attr_fn,
	process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn,
	process_pt_set_range_fn_t pt_set_range_fn,
	process_update_page_table_log_fn_t log_fn)
{
	unsigned long attr;
	unsigned long flags;
	int error;

	if (!vm || !range || !attr_fn || !lock_fn || !unlock_fn ||
	    !pt_set_range_fn || !vm->address_space)
		return -EINVAL;

	attr = process_attr_from_vrflag_result(range->flag, populate_fault,
					       NULL, attr_fn);
	flags = process_spin_lock_result((unsigned long)&vm->page_table_lock,
					 lock_fn);
	error = process_pt_set_range_result(vm->address_space->page_table,
			vm, range->start, range->end, phys, attr,
			range->pgshift, range, 0, pt_set_range_fn);
	process_spin_unlock_result((unsigned long)&vm->page_table_lock, flags,
				   unlock_fn);
	if (error) {
		process_update_page_table_log_result(error, log_fn);
		return error;
	}

	return 0;
}

int process_update_page_table_public_result(
	struct process_vm *vm, struct vm_range *range, unsigned long phys,
	unsigned long flag, process_attr_from_vrflag_fn_t attr_fn,
	process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn,
	process_pt_set_range_fn_t pt_set_range_fn,
	process_update_page_table_log_fn_t log_fn)
{
	(void)flag;

	return process_update_page_table_body_result(vm, range, phys,
			PF_POPULATE, attr_fn, lock_fn, unlock_fn,
			pt_set_range_fn, log_fn);
}

int process_access_ok_body_result(struct process_vm *vm, int verify_type,
				  unsigned long addr, size_t len)
{
	struct vm_range *range, *next;
	unsigned long end = addr + len;
	int rc;

	if (!vm)
		return -EFAULT;

	range = process_lookup_memory_range_body_result(vm, addr, end);
	rc = process_access_initial_result(range != NULL,
			range ? range->start : 0, addr);
	if (rc)
		return rc;

	for (;;) {
		rc = process_access_permission_result(verify_type, range->flag);
		if (rc)
			return rc;
		if (end <= range->end)
			return 0;

		next = process_next_memory_range_body_result(range);
		rc = process_access_adjacent_result(range->end,
				next != NULL, next ? next->start : 0);
		if (rc)
			return rc;
		range = next;
	}
}

int process_access_ok_log_result(
	struct process_vm *vm, int verify_type, unsigned long addr, size_t len,
	int error, process_access_ok_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(vm, verify_type, addr, len, error);
	return 0;
}

int process_access_ok_public_result(
	struct process_vm *vm, int verify_type, unsigned long addr, size_t len,
	process_access_ok_log_fn_t log_fn)
{
	int error;

	error = process_access_ok_body_result(vm, verify_type, addr, len);
	if (error)
		process_access_ok_log_result(vm, verify_type, addr, len,
					     error, log_fn);
	return error;
}

int process_do_page_fault_vm_body_result(
	struct process_vm *vm, struct process_vm *current_vm,
	unsigned long fault_addr, unsigned long reason, int current_cpu,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_noirq_lock_fn_t write_lock_fn,
	process_noirq_unlock_fn_t write_unlock_fn,
	process_zeroobj_match_fn_t zeroobj_match_fn,
	process_fault_range_fn_t normal_fault_fn,
	process_fault_range_fn_t xpmem_fault_fn)
{
	struct vm_range *range = NULL;
	int read_locked = 0;
	int write_locked = 0;
	int error;

	if (!vm || !current_vm)
		return -EFAULT;
	if (!read_lock_fn || !read_unlock_fn || !write_lock_fn ||
	    !write_unlock_fn || !normal_fault_fn || !xpmem_fault_fn)
		return -EINVAL;

	if (fault_addr >= current_vm->region.stack_start &&
	    fault_addr < current_vm->region.stack_end) {
		range = process_lookup_memory_range_body_result(
			vm, current_vm->region.stack_end - 1,
			current_vm->region.stack_end);
		if (!range)
			return -EFAULT;

		if (!range->memobj && fault_addr < range->start) {
			if (current_vm->is_memory_range_lock_taken == -1 ||
			    current_vm->is_memory_range_lock_taken != current_cpu) {
				error = process_noirq_lock_result(
					(unsigned long)&vm->memory_range_lock,
					write_lock_fn);
				if (error)
					return error;
				write_locked = 1;
			}
			process_range_stack_start_commit_result(range, fault_addr,
							       range->pgshift);
			if (write_locked)
				process_noirq_unlock_result(
					(unsigned long)&vm->memory_range_lock,
					write_unlock_fn);
		}
	}

	if (current_vm->is_memory_range_lock_taken == -1 ||
	    current_vm->is_memory_range_lock_taken != current_cpu) {
		error = process_noirq_lock_result(
			(unsigned long)&vm->memory_range_lock, read_lock_fn);
		if (error)
			return error;
		read_locked = 1;
	}

	if (vm->exiting) {
		error = -ECANCELED;
		goto out;
	}

	if (!range) {
		range = process_lookup_memory_range_body_result(vm, fault_addr,
							       fault_addr + 1);
		if (!range) {
			error = -EFAULT;
			goto out;
		}
	}

	if (((range->flag & VR_PROT_MASK) == VR_PROT_NONE) ||
	    (((reason & PF_WRITE) && !(reason & PF_PATCH)) &&
	     !(range->flag & VR_PROT_WRITE)) ||
	    ((reason & PF_INSTR) && !(range->flag & VR_PROT_EXEC))) {
		error = -EFAULT;
		goto out;
	}

	if ((range->flag & VR_PRIVATE) && range->memobj) {
		if (!zeroobj_match_fn) {
			error = -EINVAL;
			goto out;
		}
		if (process_zeroobj_match_result(range->memobj,
						 zeroobj_match_fn))
			reason |= PF_POPULATE;
	}

	if (!range->private_data)
		error = process_fault_range_result(vm, range, fault_addr,
						   reason, normal_fault_fn);
	else
		error = process_fault_range_result(vm, range, fault_addr,
						   reason, xpmem_fault_fn);
out:
	if (read_locked)
		process_noirq_unlock_result((unsigned long)&vm->memory_range_lock,
					    read_unlock_fn);
	return error;
}

int process_page_fault_vm_dispatch_result(struct process_vm *vm,
					  unsigned long fault_addr,
					  unsigned long reason,
					  process_page_fault_vm_fn_t fault_fn)
{
	if (!fault_fn)
		return -EINVAL;

	return fault_fn(vm, fault_addr, reason);
}

int process_preempt_result(process_preempt_fn_t preempt_fn)
{
	if (!preempt_fn)
		return -EINVAL;

	preempt_fn();
	return 0;
}

int process_pgio_dispatch_pending_result(
	void *thread, unsigned long pgio_fp_offset,
	unsigned long pgio_arg_offset,
	process_pgio_dispatch_fn_t pgio_dispatch_fn)
{
	void **fp_slot;
	void **arg_slot;

	if (!pgio_dispatch_fn)
		return -EINVAL;
	if (!thread)
		return 0;

	fp_slot = (void **)((char *)thread + pgio_fp_offset);
	arg_slot = (void **)((char *)thread + pgio_arg_offset);
	if (*fp_slot) {
		pgio_dispatch_fn(*fp_slot, *arg_slot);
		*fp_slot = NULL;
	}

	return 0;
}

int process_populate_warn_result(struct process_vm *vm, unsigned long addr,
				 unsigned long reason, unsigned long off,
				 size_t len, int error,
				 process_populate_warn_fn_t warn_fn)
{
	if (!warn_fn)
		return 0;

	warn_fn(vm, addr, reason, off, len, error);
	return 0;
}

int process_page_fault_vm_retry_body_result(
	struct process_vm *vm, unsigned long fault_addr, unsigned long reason,
	void *thread, unsigned long pgio_fp_offset,
	unsigned long pgio_arg_offset, process_page_fault_vm_fn_t do_fault_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_pgio_dispatch_fn_t pgio_dispatch_fn)
{
	int error;

	if (!do_fault_fn || !preempt_enable_fn || !preempt_disable_fn ||
	    !pgio_dispatch_fn)
		return -EINVAL;

	for (;;) {
		error = process_page_fault_vm_dispatch_result(vm, fault_addr,
				reason, do_fault_fn);
		if (error != -ERESTART)
			break;

		process_preempt_result(preempt_enable_fn);
		process_pgio_dispatch_pending_result(thread, pgio_fp_offset,
				pgio_arg_offset, pgio_dispatch_fn);
		process_preempt_result(preempt_disable_fn);
	}

	return error;
}

int process_page_fault_vm_public_result(
	struct process_vm *vm, struct process_vm *current_vm,
	unsigned long fault_addr, unsigned long reason, int current_cpu,
	void *thread, unsigned long pgio_fp_offset,
	unsigned long pgio_arg_offset,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_noirq_lock_fn_t write_lock_fn,
	process_noirq_unlock_fn_t write_unlock_fn,
	process_zeroobj_match_fn_t zeroobj_match_fn,
	process_fault_range_fn_t normal_fault_fn,
	process_fault_range_fn_t xpmem_fault_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_pgio_dispatch_fn_t pgio_dispatch_fn)
{
	int error;

	if (!preempt_enable_fn || !preempt_disable_fn || !pgio_dispatch_fn)
		return -EINVAL;

	for (;;) {
		error = process_do_page_fault_vm_body_result(vm, current_vm,
				fault_addr, reason, current_cpu, read_lock_fn,
				read_unlock_fn, write_lock_fn, write_unlock_fn,
				zeroobj_match_fn, normal_fault_fn,
				xpmem_fault_fn);
		if (error != -ERESTART)
			break;

		process_preempt_result(preempt_enable_fn);
		process_pgio_dispatch_pending_result(thread, pgio_fp_offset,
				pgio_arg_offset, pgio_dispatch_fn);
		process_preempt_result(preempt_disable_fn);
	}

	return error;
}

int process_populate_memory_body_result(
	struct process_vm *vm, unsigned long start, size_t len,
	unsigned long page_size, unsigned long reason,
	process_page_fault_vm_fn_t page_fault_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_populate_warn_fn_t warn_fn)
{
	unsigned long end = start + len;
	unsigned long addr;
	int error;

	if (!page_fault_fn || !preempt_disable_fn || !preempt_enable_fn ||
	    !page_size)
		return -EINVAL;

	process_preempt_result(preempt_disable_fn);
	for (addr = start; addr < end; addr += page_size) {
		error = process_page_fault_vm_dispatch_result(vm, addr, reason,
				page_fault_fn);
		if (error) {
			process_populate_warn_result(vm, addr, reason,
					addr - start, len, error, warn_fn);
			process_preempt_result(preempt_enable_fn);
			return error;
		}
	}
	process_preempt_result(preempt_enable_fn);
	return 0;
}

int process_populate_memory_public_result(
	struct process_vm *vm, struct process_vm *current_vm,
	unsigned long start, size_t len, unsigned long page_size,
	unsigned long reason, int current_cpu, void *thread,
	unsigned long pgio_fp_offset, unsigned long pgio_arg_offset,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_noirq_lock_fn_t write_lock_fn,
	process_noirq_unlock_fn_t write_unlock_fn,
	process_zeroobj_match_fn_t zeroobj_match_fn,
	process_fault_range_fn_t normal_fault_fn,
	process_fault_range_fn_t xpmem_fault_fn,
	process_preempt_fn_t preempt_disable_fn,
	process_preempt_fn_t preempt_enable_fn,
	process_pgio_dispatch_fn_t pgio_dispatch_fn,
	process_populate_warn_fn_t warn_fn)
{
	unsigned long end = start + len;
	unsigned long addr;
	int error;

	if (!preempt_disable_fn || !preempt_enable_fn || !pgio_dispatch_fn ||
	    !page_size)
		return -EINVAL;

	process_preempt_result(preempt_disable_fn);
	for (addr = start; addr < end; addr += page_size) {
		error = process_page_fault_vm_public_result(vm, current_vm,
				addr, reason, current_cpu, thread,
				pgio_fp_offset, pgio_arg_offset,
				read_lock_fn, read_unlock_fn, write_lock_fn,
				write_unlock_fn, zeroobj_match_fn,
				normal_fault_fn, xpmem_fault_fn,
				preempt_enable_fn, preempt_disable_fn,
				pgio_dispatch_fn);
		if (error) {
			process_populate_warn_result(vm, addr, reason,
					addr - start, len, error, warn_fn);
			process_preempt_result(preempt_enable_fn);
			return error;
		}
	}
	process_preempt_result(preempt_enable_fn);
	return 0;
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

int process_memobj_ref_direct_result(struct memobj *memobj)
{
	if (!memobj)
		return -EINVAL;

	return ihk_atomic_inc_return(&memobj->refcnt);
}

int process_memobj_unref_direct_result(struct memobj *memobj)
{
	int cnt;

	if (!memobj)
		return -EINVAL;

	cnt = ihk_atomic_dec_return(&memobj->refcnt);
	if (cnt == 0 && memobj->ops && memobj->ops->free)
		(*memobj->ops->free)(memobj);

	return cnt;
}

int process_range_memobj_ref_result(struct memobj *memobj,
				    process_range_memobj_ref_fn_t memobj_ref_fn)
{
	if (!memobj)
		return 0;
	if (!memobj_ref_fn)
		return -EINVAL;

	memobj_ref_fn(memobj);
	return 0;
}

int process_range_optional_memobj_ref_result(
		struct memobj *memobj,
		process_range_memobj_ref_fn_t memobj_ref_fn)
{
	if (!memobj || !memobj_ref_fn)
		return 0;

	memobj_ref_fn(memobj);
	return 0;
}

int process_range_memobj_ref_or_direct_result(
		struct memobj *memobj,
		process_range_memobj_ref_fn_t memobj_ref_fn)
{
	if (!memobj)
		return 0;
	if (memobj_ref_fn) {
		memobj_ref_fn(memobj);
		return 0;
	}

	process_memobj_ref_direct_result(memobj);
	return 0;
}

int process_range_memobj_unref_or_direct_result(
		struct memobj *memobj,
		process_range_memobj_ref_fn_t memobj_unref_fn)
{
	if (!memobj)
		return 0;
	if (memobj_unref_fn) {
		memobj_unref_fn(memobj);
		return 0;
	}

	process_memobj_unref_direct_result(memobj);
	return 0;
}

int process_range_optional_memobj_ref_or_direct_result(
		struct memobj *memobj,
		process_range_memobj_ref_fn_t memobj_ref_fn)
{
	if (!memobj)
		return 0;

	return process_range_memobj_ref_or_direct_result(memobj, memobj_ref_fn);
}

int process_range_optional_memobj_unref_or_direct_result(
		struct memobj *memobj,
		process_range_memobj_ref_fn_t memobj_unref_fn)
{
	if (!memobj)
		return 0;

	return process_range_memobj_unref_or_direct_result(memobj,
							   memobj_unref_fn);
}

int process_split_range_insert_result(struct process_vm *vm,
				      struct vm_range *range,
				      process_split_range_insert_fn_t insert_fn)
{
	if (!insert_fn)
		return -EINVAL;

	return insert_fn(vm, range);
}

int process_split_range_publish_result(
	struct process_vm *vm, struct vm_range *low, struct vm_range *high,
	uintptr_t addr, struct vm_range **splitp,
	process_range_memobj_ref_fn_t memobj_ref_fn,
	process_split_range_insert_fn_t insert_fn)
{
	int rc;

	if (!low || !high || !insert_fn)
		return -EINVAL;

	if (low->memobj) {
		rc = process_range_memobj_ref_or_direct_result(low->memobj,
							       memobj_ref_fn);
		if (rc)
			return rc;
	}

	process_split_range_commit_result(low, addr);

	rc = process_split_range_insert_result(vm, high, insert_fn);
	if (rc)
		return rc;

	if (splitp)
		*splitp = high;

	return 0;
}

struct vm_range *process_split_range_alloc_init_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	void *splitp, unsigned long range_size, unsigned long alloc_flags,
	int *errorp, process_split_range_alloc_fn_t alloc_fn,
	process_split_range_alloc_log_fn_t log_fn)
{
	struct vm_range *newrange;

	if (!errorp)
		return NULL;

	*errorp = 0;
	if (!range || !alloc_fn) {
		*errorp = -EINVAL;
		return NULL;
	}

	newrange = alloc_fn(range_size, alloc_flags);
	if (!newrange) {
		*errorp = -ENOMEM;
		if (log_fn)
			log_fn(vm, range, addr, splitp);
		return NULL;
	}

	if (!process_split_range_init_result(range, newrange, addr)) {
		*errorp = -EINVAL;
		return newrange;
	}

	return newrange;
}

int process_split_range_publish_body_result(
	struct process_vm *vm, struct vm_range *low, struct vm_range *high,
	uintptr_t addr, struct vm_range **splitp,
	process_range_memobj_ref_fn_t memobj_ref_fn,
	process_split_range_insert_fn_t insert_fn,
	process_split_range_publish_log_fn_t log_fn)
{
	int rc;

	rc = process_split_range_publish_result(vm, low, high, addr, splitp,
						memobj_ref_fn, insert_fn);
	if (rc && log_fn)
		log_fn(rc);

	return rc;
}

int process_split_range_pt_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	process_split_range_pt_split_fn_t split_fn,
	process_split_range_pt_log_fn_t log_fn)
{
	int rc;

	if (!vm || !range)
		return -EINVAL;

	range->pgshift = process_split_pgshift_result(range->pgshift, addr);

	if (!split_fn || !vm->address_space)
		return -EINVAL;

	rc = split_fn(vm->address_space->page_table, vm, range, (void *)addr);
	if (rc && log_fn)
		log_fn(rc);

	return rc;
}

int process_split_shm_log_result(int event, int error,
				 process_split_shm_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, error);
	return 0;
}

int process_split_shm_update_body_result(
	struct process_vm *vm, struct vm_range *range, unsigned long addr,
	unsigned long page_pgshift_offset,
	process_split_shm_lookup_page_fn_t lookup_page_fn,
	process_split_shm_phys_to_page_fn_t phys_to_page_fn,
	process_split_shm_update_page_fn_t update_page_fn,
	process_split_shm_log_fn_t log_fn)
{
	uintptr_t phys = 0;
	void *page;
	int pgshift;
	unsigned long page_mask;
	int error;

	if (!vm || !range)
		return -EINVAL;
	if (!range->memobj || !(range->memobj->flags & MF_SHM))
		return 0;
	if (!lookup_page_fn || !phys_to_page_fn || !update_page_fn ||
	    !vm->address_space)
		return -EINVAL;

	error = lookup_page_fn(range->memobj,
			range->objoff + addr - range->start, 0, &phys, NULL);
	if (error && error != -ENOENT) {
		process_split_shm_log_result(
			PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED, error, log_fn);
		return error;
	}

	page = phys_to_page_fn(phys);
	if (!page)
		return 0;

	pgshift = *(int *)((char *)page + page_pgshift_offset);
	page_mask = ~((1UL << pgshift) - 1);
	error = update_page_fn(range->memobj, vm->address_space->page_table,
			       page, (void *)(addr & page_mask));
	if (error) {
		process_split_shm_log_result(
			PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED, error, log_fn);
		return error;
	}

	return 0;
}

int process_join_range_free_result(struct vm_range *range,
				   process_join_range_free_fn_t free_fn)
{
	if (!free_fn)
		return -EINVAL;

	free_fn(range);
	return 0;
}

int process_join_range_tofu_result(struct process_vm *vm,
				   struct vm_range *surviving,
				   struct vm_range *merging,
				   process_join_range_tofu_fn_t tofu_fn)
{
	if (!tofu_fn)
		return 0;

	return tofu_fn(vm, surviving, merging);
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

int process_join_range_body_result(
	struct process_vm *vm, struct rb_root *root, struct vm_range **cache,
	int cache_count, struct vm_range *surviving, struct vm_range *merging,
	process_range_memobj_ref_fn_t memobj_unref_fn,
	process_join_range_free_fn_t free_fn,
	process_join_range_tofu_fn_t tofu_fn)
{
	int rc;

	if (!root || !cache || !free_fn)
		return -EINVAL;

	rc = process_join_range_prepare_result(surviving, merging);
	if (rc)
		return rc;

	if (merging->memobj) {
		rc = process_range_memobj_unref_or_direct_result(
				merging->memobj, memobj_unref_fn);
		if (rc)
			return rc;
	}

	rb_erase(&merging->vm_rb_node, root);
	process_range_cache_replace_result(cache, cache_count,
			merging, surviving);

	rc = process_join_range_tofu_result(vm, surviving, merging, tofu_fn);
	if (rc)
		return rc;

	return process_join_range_free_result(merging, free_fn);
}

static unsigned long process_align_down(unsigned long value, size_t size)
{
	return value & ~(size - 1);
}

static unsigned long process_align_up(unsigned long value, size_t size)
{
	return (value + size - 1) & ~(size - 1);
}

int process_free_range_page_size_result(
	size_t current, size_t *nextp,
	process_free_range_page_size_fn_t page_size_fn)
{
	if (!page_size_fn)
		return -EINVAL;

	return page_size_fn(current, nextp);
}

static unsigned long process_free_lower_bound(
	unsigned long start, int has_prev, unsigned long prev_end,
	process_free_range_page_size_fn_t page_size_fn, int *first_errorp)
{
	size_t pgsize = -1;

	for (;;) {
		unsigned long lpstart;
		int rc = process_free_range_page_size_result(pgsize, &pgsize,
							     page_size_fn);

		if (rc) {
			if (!*first_errorp)
				*first_errorp = rc;
			break;
		}
		lpstart = process_align_down(start, pgsize);
		if (!has_prev || prev_end <= lpstart) {
			start = lpstart;
			break;
		}
	}

	return start;
}

static unsigned long process_free_upper_bound(
	unsigned long end, int has_next, unsigned long next_start,
	process_free_range_page_size_fn_t page_size_fn, int *first_errorp)
{
	size_t pgsize = -1;

	for (;;) {
		unsigned long lpend;
		int rc = process_free_range_page_size_result(pgsize, &pgsize,
							     page_size_fn);

		if (rc) {
			if (!*first_errorp)
				*first_errorp = rc;
			break;
		}
		lpend = process_align_up(end, pgsize);
		if (!has_next || lpend <= next_start) {
			end = lpend;
			break;
		}
	}

	return end;
}

int process_free_range_pt_plan_result(
	const struct vm_range *range, unsigned long straight_va, int has_prev,
	unsigned long prev_end, int has_next, unsigned long next_start,
	int has_memobj, unsigned int memobj_flags, unsigned long *startp,
	unsigned long *endp, int *actionp,
	process_free_range_page_size_fn_t page_size_fn)
{
	unsigned long start;
	unsigned long end;
	int action = PROCESS_FREE_RANGE_PT_SKIP;
	int first_error = 0;

	if (!range || !startp || !endp || !actionp)
		return -EINVAL;

	start = range->start;
	end = range->end;

	if (!range->straight_start && range->start != straight_va) {
		if (range->flag & (VR_REMOTE | VR_IO_NOCACHE | VR_RESERVED)) {
			action = PROCESS_FREE_RANGE_PT_CLEAR;
		}
		else {
			if (!page_size_fn)
				return -EINVAL;
			start = process_free_lower_bound(start, has_prev,
					prev_end, page_size_fn, &first_error);
			end = process_free_upper_bound(end, has_next,
					next_start, page_size_fn, &first_error);
			action = (has_memobj && (memobj_flags & MF_HUGETLBFS)) ?
				PROCESS_FREE_RANGE_PT_CLEAR :
				PROCESS_FREE_RANGE_PT_FREE;
		}
	}

	*startp = start;
	*endp = end;
	*actionp = action;
	return first_error;
}

int process_free_range_finalize_result(
	struct process_vm *vm, struct rb_root *root, struct vm_range **cache,
	int cache_count, struct vm_range *range, unsigned long straight_va,
	size_t *straight_lenp, unsigned long straight_pa,
	process_free_range_phys_to_virt_fn_t phys_to_virt_fn,
	process_free_range_pages_fn_t free_pages_fn,
	process_free_range_clear_main_fn_t clear_main_fn,
	process_free_range_free_fn_t free_fn)
{
	int needs_straight_free;
	int is_main_straight;

	if (!root || !cache || !range || !straight_lenp || !free_fn)
		return -EINVAL;

	needs_straight_free = range->straight_start != 0;
	is_main_straight = !needs_straight_free &&
		range->start == straight_va &&
		range->end == straight_va + *straight_lenp;

	if (needs_straight_free && (!phys_to_virt_fn || !free_pages_fn))
		return -EINVAL;
	if (is_main_straight && !clear_main_fn)
		return -EINVAL;

	rb_erase(&range->vm_rb_node, root);
	process_range_cache_replace_result(cache, cache_count, range, NULL);

	if (needs_straight_free) {
		unsigned long phys = straight_pa +
			(range->straight_start - straight_va);

		void *addr = process_free_range_phys_to_virt_result(phys,
				phys_to_virt_fn);
		int rc = process_free_range_free_pages_result(addr,
				(range->end - range->start) >> PAGE_SHIFT,
				free_pages_fn);
		if (rc)
			return rc;
	}
	else if (is_main_straight) {
		process_free_range_clear_main_result(vm, range->start,
				range->end, clear_main_fn);
		*straight_lenp = 0;
	}

	return process_free_range_free_result(range, free_fn);
}

void *process_free_range_phys_to_virt_result(
		unsigned long phys,
		process_free_range_phys_to_virt_fn_t phys_to_virt_fn)
{
	if (!phys_to_virt_fn)
		return NULL;

	return phys_to_virt_fn(phys);
}

int process_free_range_free_pages_result(
		void *addr, unsigned long pages,
		process_free_range_pages_fn_t free_pages_fn)
{
	if (!free_pages_fn)
		return -EINVAL;

	free_pages_fn(addr, pages);
	return 0;
}

int process_free_range_clear_main_result(
		struct process_vm *vm, unsigned long start, unsigned long end,
		process_free_range_clear_main_fn_t clear_main_fn)
{
	if (!clear_main_fn)
		return -EINVAL;

	return clear_main_fn(vm, start, end);
}

int process_free_range_free_result(struct vm_range *range,
				   process_free_range_free_fn_t free_fn)
{
	if (!free_fn)
		return -EINVAL;

	free_fn(range);
	return 0;
}

int process_free_range_pt_free_result(
		void *page_table, struct process_vm *vm, unsigned long start,
		unsigned long end, void *memobj,
		process_free_range_pt_free_fn_t pt_free_fn)
{
	if (!pt_free_fn)
		return -EINVAL;

	return pt_free_fn(page_table, vm, start, end, memobj);
}

int process_free_range_pt_clear_result(
		void *page_table, struct process_vm *vm, unsigned long start,
		unsigned long end, process_free_range_pt_clear_fn_t pt_clear_fn)
{
	if (!pt_clear_fn)
		return -EINVAL;

	return pt_clear_fn(page_table, vm, start, end);
}

int process_free_range_tofu_remove_result(
		struct process_vm *vm, struct vm_range *range,
		process_free_range_tofu_remove_fn_t tofu_remove_fn)
{
	if (!tofu_remove_fn)
		return 0;

	return tofu_remove_fn(vm, range);
}

int process_free_range_log_result(
		int event, struct process_vm *vm, struct vm_range *range,
		unsigned long start, unsigned long end, int error,
		process_free_range_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, vm, range, start, end, error);
	return 0;
}

int process_free_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long straight_va, size_t *straight_lenp,
	unsigned long straight_pa, int tofu_enabled,
	process_free_range_page_size_fn_t page_size_fn,
	process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_range_memobj_ref_fn_t memobj_ref_fn,
	process_range_memobj_ref_fn_t memobj_unref_fn,
	process_free_range_pt_free_fn_t pt_free_fn,
	process_free_range_pt_clear_fn_t pt_clear_fn,
	process_free_range_tofu_remove_fn_t tofu_remove_fn,
	process_free_range_phys_to_virt_fn_t phys_to_virt_fn,
	process_free_range_pages_fn_t free_pages_fn,
	process_free_range_clear_main_fn_t clear_main_fn,
	process_free_range_free_fn_t free_fn,
	process_free_range_log_fn_t log_fn)
{
	unsigned long start;
	unsigned long end;
	unsigned long start0;
	unsigned long end0;
	struct vm_range *prev;
	struct vm_range *next;
	unsigned int memobj_flags;
	int has_memobj;
	int pt_action = PROCESS_FREE_RANGE_PT_SKIP;
	int error;

	if (!vm || !range || !straight_lenp || !vm->address_space)
		return -EINVAL;

	start0 = range->start;
	end0 = range->end;
	start = start0;
	end = end0;
	prev = process_previous_memory_range_body_result(range);
	next = process_next_memory_range_body_result(range);
	has_memobj = range->memobj != NULL;
	memobj_flags = has_memobj ? range->memobj->flags : 0;
	error = process_free_range_pt_plan_result(range, straight_va,
			prev != NULL, prev ? prev->end : 0,
			next != NULL, next ? next->start : 0, has_memobj,
			memobj_flags, &start, &end, &pt_action, page_size_fn);
	if (error)
		process_free_range_log_result(PROCESS_FREE_BODY_LOG_PLAN_FAILED,
					      vm, range, start, end, error,
					      log_fn);

	if (pt_action != PROCESS_FREE_RANGE_PT_SKIP) {
		if (!lock_fn || !unlock_fn)
			return -EINVAL;

		if (pt_action == PROCESS_FREE_RANGE_PT_FREE) {
			if (!pt_free_fn)
				return -EINVAL;
			process_noirq_lock_result(
				(unsigned long)&vm->page_table_lock, lock_fn);
			process_range_optional_memobj_ref_or_direct_result(
				range->memobj, memobj_ref_fn);
			error = process_free_range_pt_free_result(
				vm->address_space->page_table, vm, start, end,
				range->memobj, pt_free_fn);
			process_range_optional_memobj_unref_or_direct_result(
				range->memobj, memobj_unref_fn);
			process_noirq_unlock_result(
				(unsigned long)&vm->page_table_lock,
				unlock_fn);
			if (error && error != -ENOENT)
				process_free_range_log_result(
					PROCESS_FREE_BODY_LOG_PT_FREE_FAILED,
					vm, range, start, end, error, log_fn);
		}
		else if (pt_action == PROCESS_FREE_RANGE_PT_CLEAR) {
			if (!pt_clear_fn)
				return -EINVAL;
			process_noirq_lock_result(
				(unsigned long)&vm->page_table_lock, lock_fn);
			error = process_free_range_pt_clear_result(
				vm->address_space->page_table, vm, start, end,
				pt_clear_fn);
			process_noirq_unlock_result(
				(unsigned long)&vm->page_table_lock,
				unlock_fn);
			if (error && error != -ENOENT)
				process_free_range_log_result(
					PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED,
					vm, range, start, end, error, log_fn);
		}

		process_range_optional_memobj_unref_or_direct_result(
			range->memobj, memobj_unref_fn);
	}

	if (tofu_enabled) {
		int entries = process_free_range_tofu_remove_result(
			vm, range, tofu_remove_fn);

		if (entries > 0)
			process_free_range_log_result(
				PROCESS_FREE_BODY_LOG_TOFU_REMOVED, vm, range,
				start0, end0, entries, log_fn);
	}

	error = process_free_range_finalize_result(vm, &vm->vm_range_tree,
			vm->range_cache, VM_RANGE_CACHE_SIZE, range, straight_va,
			straight_lenp, straight_pa, phys_to_virt_fn,
			free_pages_fn, clear_main_fn, free_fn);
	if (error) {
		process_free_range_log_result(
			PROCESS_FREE_BODY_LOG_FINALIZE_FAILED, vm, range,
			start0, end0, error, log_fn);
		return error;
	}

	process_free_range_log_result(PROCESS_FREE_BODY_LOG_DONE, vm, range,
				      start0, end0, 0, log_fn);
	return 0;
}

int process_sync_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, void *arg,
	void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_sync_range_log_fn_t log_fn)
{
	int error;
	struct memobj *memobj;

	if (!vm || !range || !vm->address_space || !range->memobj ||
	    !lock_fn || !unlock_fn || !visit_fn)
		return -EINVAL;

	memobj = range->memobj;
	process_noirq_lock_result((unsigned long)&vm->page_table_lock, lock_fn);
	if (!(memobj->flags & MF_ZEROFILL))
		process_memobj_ref_direct_result(memobj);

	error = visit_fn(vm->address_space->page_table, start, end,
			 range->pgshift, VPTEF_SKIP_NULL, visit_step_fn, arg);

	if (!(memobj->flags & MF_ZEROFILL))
		process_memobj_unref_direct_result(memobj);
	process_noirq_unlock_result((unsigned long)&vm->page_table_lock,
				    unlock_fn);

	if (error && log_fn)
		log_fn(vm, range, start, end, error);

	return error;
}

int process_remap_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, long off, void *arg,
	void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_remap_range_log_fn_t log_fn)
{
	int error;
	unsigned int old_pgshift;
	struct memobj *memobj;

	if (!vm || !range || !vm->address_space || !range->memobj ||
	    !lock_fn || !unlock_fn || !visit_fn)
		return -EINVAL;

	memobj = range->memobj;
	process_noirq_lock_result((unsigned long)&vm->page_table_lock, lock_fn);
	process_memobj_ref_direct_result(memobj);

	old_pgshift = __sync_val_compare_and_swap(&range->pgshift, 0,
						  PAGE_SHIFT);
	if (old_pgshift != 0 && old_pgshift != PAGE_SHIFT) {
		error = -E2BIG;
		if (log_fn)
			log_fn(PROCESS_REMAP_RANGE_LOG_PGSHIFT, vm, range,
			       start, end, off, old_pgshift, error);
		goto out;
	}

	error = visit_fn(vm->address_space->page_table, start, end,
			 range->pgshift, 0, visit_step_fn, arg);
	if (error && log_fn)
		log_fn(PROCESS_REMAP_RANGE_LOG_VISIT_FAILED, vm, range,
		       start, end, off, old_pgshift, error);

out:
	process_memobj_unref_direct_result(memobj);
	process_noirq_unlock_result((unsigned long)&vm->page_table_lock,
				    unlock_fn);
	return error;
}

int process_invalidate_memory_range_body_result(
	struct process_vm *vm, struct vm_range *range,
	unsigned long start, unsigned long end, void *arg,
	void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_lookup_pte_fn_t lookup_pte_fn,
	process_pte_test_fn_t pte_contiguous_fn,
	process_pte_pgsize_test_fn_t pte_head_fn,
	process_pte_pgsize_test_fn_t pte_tail_fn,
	process_split_contiguous_pages_fn_t split_fn,
	process_free_range_pt_free_fn_t pt_free_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_sync_range_log_fn_t log_fn)
{
	int error = 0;
	int should_log = 0;
	void *ptep;
	size_t pgsize = 0;
	struct memobj *memobj;

	if (!vm || !range || !vm->address_space || !range->memobj ||
	    !lock_fn || !unlock_fn || !lookup_pte_fn || !pte_contiguous_fn ||
	    !pte_head_fn || !pte_tail_fn || !split_fn || !pt_free_fn ||
	    !visit_fn)
		return -EINVAL;

	memobj = range->memobj;
	process_noirq_lock_result((unsigned long)&vm->page_table_lock, lock_fn);
	process_memobj_ref_direct_result(memobj);

	ptep = lookup_pte_fn(vm->address_space->page_table, start, 0, &pgsize);
	if (ptep && pte_contiguous_fn(ptep) && !pte_head_fn(ptep, pgsize)) {
		error = split_fn(ptep, pgsize, memobj->flags);
		if (error)
			goto out;
	}

	ptep = lookup_pte_fn(vm->address_space->page_table, end - 1, 0,
			     &pgsize);
	if (ptep && pte_contiguous_fn(ptep) && !pte_tail_fn(ptep, pgsize)) {
		error = split_fn(ptep, pgsize, memobj->flags);
		if (error)
			goto out;
	}

	should_log = 1;
	if (memobj->flags & MF_SHM) {
		error = pt_free_fn(vm->address_space->page_table, vm, start, end,
				   memobj);
	} else {
		error = visit_fn(vm->address_space->page_table, start, end,
				 range->pgshift, VPTEF_SKIP_NULL,
				 visit_step_fn, arg);
	}

out:
	process_memobj_unref_direct_result(memobj);
	process_noirq_unlock_result((unsigned long)&vm->page_table_lock,
				    unlock_fn);

	if (should_log && error && log_fn)
		log_fn(vm, range, start, end, error);

	return error;
}

int process_invalidate_one_page_body_result(
	void *arg, void *page_table, void *ptep, void *pgaddr, int pgshift,
	process_pte_test_fn_t pte_null_fn,
	process_pte_pgsize_test_fn_t pte_fileoff_fn,
	process_pte_get_phys_fn_t pte_get_phys_fn,
	process_phys_to_page_fn_t phys_to_page_fn,
	process_page_offset_fn_t page_offset_fn,
	process_pte_make_fileoff_fn_t pte_make_fileoff_fn,
	process_pte_xchg_fn_t pte_xchg_fn,
	process_flush_tlb_single_fn_t flush_tlb_single_fn,
	process_pte_test_fn_t pte_contiguous_fn,
	process_pte_pgsize_test_fn_t pte_head_fn,
	process_pgsize_to_tbllv_fn_t pgsize_to_tbllv_fn,
	process_tbllv_to_contpgsize_fn_t tbllv_to_contpgsize_fn,
	process_page_unmap_fn_t page_unmap_fn,
	process_panic_fn_t panic_fn,
	process_memobj_invalidate_page_fn_t memobj_invalidate_page_fn,
	process_invalidate_one_page_log_fn_t log_fn)
{
	struct vm_range *range;
	size_t pgsize;
	int error;
	uintptr_t phys;
	void *page;
	long linear_off;
	unsigned long apte = 0;
	size_t memobj_pgsize;

	if (!arg || !ptep || pgshift < 0 ||
	    pgshift >= (int)(sizeof(size_t) * 8) ||
	    !pte_null_fn || !pte_fileoff_fn || !pte_get_phys_fn ||
	    !phys_to_page_fn || !page_offset_fn || !pte_make_fileoff_fn ||
	    !pte_xchg_fn || !flush_tlb_single_fn || !pte_contiguous_fn ||
	    !pte_head_fn || !pgsize_to_tbllv_fn ||
	    !tbllv_to_contpgsize_fn || !page_unmap_fn || !panic_fn ||
	    !memobj_invalidate_page_fn)
		return -EINVAL;

	range = *(struct vm_range **)arg;
	if (!range || !range->memobj)
		return -EINVAL;

	pgsize = (size_t)1 << pgshift;
	if (pte_null_fn(ptep) || pte_fileoff_fn(ptep, pgsize))
		return 0;

	phys = pte_get_phys_fn(ptep);
	page = phys_to_page_fn(phys);
	linear_off = range->objoff + ((uintptr_t)pgaddr - range->start);

	if (page) {
		long page_off = page_offset_fn(page);

		if (page_off != linear_off)
			pte_make_fileoff_fn(page_off, pgsize, &apte);
	}

	pte_xchg_fn(ptep, &apte);
	flush_tlb_single_fn((unsigned long)pgaddr);

	if (pte_contiguous_fn(&apte)) {
		if (pte_head_fn(ptep, pgsize)) {
			int level = pgsize_to_tbllv_fn(pgsize);

			memobj_pgsize = tbllv_to_contpgsize_fn(level);
		} else {
			return 0;
		}
	} else {
		memobj_pgsize = pgsize;
	}

	if (page && page_unmap_fn(page))
		panic_fn("invalidate_one_page");

	error = memobj_invalidate_page_fn(range->memobj, phys, memobj_pgsize);
	if (error && log_fn)
		log_fn(arg, page_table, ptep, *(unsigned long *)ptep, pgaddr,
		       pgshift, error);

	return error;
}

int process_remove_straight_convert_result(
	unsigned long straight_va, size_t straight_len,
	const struct vm_range *range, unsigned long start, unsigned long end,
	unsigned long *new_startp, unsigned long *new_endp,
	unsigned long *lenp)
{
	unsigned long len;
	unsigned long straight_end;

	if (!new_startp || !new_endp || !lenp)
		return -EINVAL;

	len = end - start;
	*new_startp = start;
	*new_endp = end;
	*lenp = len;

	straight_end = straight_va + straight_len;
	if (!straight_va || start < straight_va || end > straight_end ||
	    (start == straight_va && end == straight_end))
		return PROCESS_REMOVE_STRAIGHT_NO_CONVERT;

	if (!range)
		return PROCESS_REMOVE_STRAIGHT_NEED_RANGE;

	if (range->straight_start &&
	    start >= range->straight_start &&
	    start < (range->straight_start + (range->end - range->start))) {
		*new_startp = range->start + (start - range->straight_start);
		*new_endp = *new_startp + len;
		return PROCESS_REMOVE_STRAIGHT_CONVERTED;
	}

	return PROCESS_REMOVE_STRAIGHT_NEED_RANGE;
}

int process_remove_range_split_result(
		struct process_vm *vm, struct vm_range *range, unsigned long addr,
		struct vm_range **splitp,
		process_remove_range_split_fn_t split_fn)
{
	if (!split_fn)
		return -EINVAL;

	return split_fn(vm, range, addr, splitp);
}

int process_remove_range_xpmem_result(
		struct process_vm *vm, struct vm_range *range,
		process_remove_range_xpmem_fn_t xpmem_remove_fn)
{
	if (!xpmem_remove_fn)
		return -EINVAL;

	xpmem_remove_fn(vm, range);
	return 0;
}

int process_remove_range_free_result(
		struct process_vm *vm, struct vm_range *range,
		process_memory_range_free_fn_t free_fn)
{
	if (!free_fn)
		return -EINVAL;

	return free_fn(vm, range);
}

int process_remove_range_log_result(
		int event, struct process_vm *vm, unsigned long start,
		unsigned long end, struct vm_range *range, int error,
		process_remove_range_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(event, vm, start, end, range, error);
	return 0;
}

int process_remove_memory_range_body_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	int *ro_freedp, unsigned long straight_va, size_t straight_len,
	process_remove_range_split_fn_t split_fn,
	process_remove_range_xpmem_fn_t xpmem_remove_fn,
	process_memory_range_free_fn_t free_fn,
	process_remove_range_log_fn_t log_fn)
{
	struct vm_range *range, *next;
	unsigned long converted_start;
	unsigned long converted_end;
	unsigned long len;
	int action;
	int ro_freed = 0;

	if (!vm || !split_fn || !free_fn)
		return -EINVAL;

	action = process_remove_straight_convert_result(straight_va,
			straight_len, NULL, start, end, &converted_start,
			&converted_end, &len);
	if (action == PROCESS_REMOVE_STRAIGHT_NEED_RANGE) {
		struct vm_range *range_iter;
		struct vm_range *converted_range = NULL;

		range_iter = process_lookup_memory_range_body_result(vm, 0, -1UL);
		while (range_iter) {
			action = process_remove_straight_convert_result(
					straight_va, straight_len, range_iter,
					start, end, &converted_start,
					&converted_end, &len);
			if (action == PROCESS_REMOVE_STRAIGHT_CONVERTED) {
				converted_range = range_iter;
				break;
			}

			range_iter = process_next_memory_range_body_result(range_iter);
		}

		if (!converted_range) {
			process_remove_range_log_result(
				PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT, vm,
				start, end, NULL, 0, log_fn);
			return 0;
		}

		process_remove_range_log_result(
			PROCESS_REMOVE_RANGE_LOG_CONVERTED, vm,
			converted_start, converted_end, converted_range, 0,
			log_fn);
		start = converted_start;
		end = converted_end;
	}

	next = process_lookup_memory_range_body_result(vm, start, end);
	while ((range = next) && range->start < end) {
		int split_start;
		int split_end;
		int mark_ro_freed;
		int remove_xpmem;
		int error;

		next = process_next_memory_range_body_result(range);
		process_remove_range_step_result(range->start, range->end,
				start, end, range->flag,
				(unsigned long)range->private_data,
				&split_start, &split_end, &mark_ro_freed,
				&remove_xpmem);

		if (split_start) {
			error = process_remove_range_split_result(
				vm, range, start, &range, split_fn);
			if (error) {
				process_remove_range_log_result(
					PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED,
					vm, start, end, range, error, log_fn);
				return error;
			}
		}

		if (split_end) {
			error = process_remove_range_split_result(
				vm, range, end, NULL, split_fn);
			if (error) {
				process_remove_range_log_result(
					PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED,
					vm, start, end, range, error, log_fn);
				return error;
			}
		}

		if (mark_ro_freed)
			ro_freed = 1;

		if (remove_xpmem) {
			error = process_remove_range_xpmem_result(
				vm, range, xpmem_remove_fn);
			if (error)
				return error;
		}

		error = process_remove_range_free_result(vm, range, free_fn);
		if (error) {
			process_remove_range_log_result(
				PROCESS_REMOVE_RANGE_LOG_FREE_FAILED,
				vm, start, end, range, error, log_fn);
			return error;
		}
	}

	if (ro_freedp)
		*ro_freedp = ro_freed;
	process_remove_range_log_result(PROCESS_REMOVE_RANGE_LOG_DONE, vm,
					start, end, NULL, ro_freed, log_fn);
	return 0;
}

int process_remove_region_body_result(
	struct process_vm *vm, unsigned long start, unsigned long end,
	process_noirq_lock_fn_t lock_fn, process_noirq_unlock_fn_t unlock_fn,
	process_remove_region_clear_fn_t clear_fn,
	process_remove_region_log_fn_t log_fn)
{
	int rc;

	if (!vm)
		return -EINVAL;

	rc = process_remove_region_alignment_result(start, end);
	if (rc)
		return rc;

	if (!lock_fn || !unlock_fn || !clear_fn || !vm->address_space)
		return -EINVAL;

	rc = process_noirq_lock_result((unsigned long)&vm->page_table_lock,
				       lock_fn);
	if (rc)
		return rc;
	process_remove_region_clear_result(vm->address_space->page_table,
					   vm, start, end, clear_fn);
	process_noirq_unlock_result((unsigned long)&vm->page_table_lock,
				    unlock_fn);

	return process_remove_region_log_result(vm, start, end, log_fn);
}

int process_remove_region_clear_result(
		void *page_table, struct process_vm *vm, unsigned long start,
		unsigned long end, process_remove_region_clear_fn_t clear_fn)
{
	if (!clear_fn)
		return -EINVAL;

	return clear_fn(page_table, vm, start, end);
}

int process_remove_region_log_result(
		struct process_vm *vm, unsigned long start, unsigned long end,
		process_remove_region_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(vm, start, end);
	return 0;
}

static void process_init_stack_push(unsigned long *base, int *s_indp,
				    unsigned long value)
{
	base[*s_indp] = value;
	(*s_indp)--;
}

void *process_init_stack_alloc_aligned_result(
		int npages, int p2align, unsigned long flags,
		unsigned long virt_addr,
		process_init_stack_alloc_aligned_fn_t alloc_aligned_fn)
{
	if (!alloc_aligned_fn)
		return NULL;

	return alloc_aligned_fn(npages, p2align, flags, virt_addr);
}

int process_init_stack_free_pages_result(
		void *addr, int npages,
		process_init_stack_free_pages_fn_t free_pages_fn)
{
	if (!free_pages_fn)
		return -EINVAL;

	free_pages_fn(addr, npages);
	return 0;
}

int process_init_stack_add_range_result(
		struct process_vm *vm, unsigned long start, unsigned long end,
		unsigned long phys, unsigned long flag, int pgshift,
		struct vm_range **rangep,
		process_init_stack_add_range_fn_t add_range_fn)
{
	if (!add_range_fn)
		return -EINVAL;

	return add_range_fn(vm, start, end, phys, flag, pgshift, rangep);
}

unsigned long process_init_stack_virt_to_phys_result(
		void *addr, process_init_stack_virt_to_phys_fn_t virt_to_phys_fn)
{
	if (!virt_to_phys_fn)
		return 0;

	return virt_to_phys_fn(addr);
}

unsigned long process_attr_from_vrflag_result(
		unsigned long flag, unsigned long fault, void *ptep,
		process_attr_from_vrflag_fn_t attr_fn)
{
	if (!attr_fn)
		return 0;

	return attr_fn(flag, fault, ptep);
}

int process_init_stack_pt_set_range_result(
		void *page_table, struct process_vm *vm, unsigned long start,
		unsigned long end, unsigned long phys, unsigned long attr,
		int pgshift, struct vm_range *range, int flags,
		process_init_stack_pt_set_range_fn_t pt_set_range_fn)
{
	if (!pt_set_range_fn)
		return -EINVAL;

	return pt_set_range_fn(page_table, vm, start, end, phys, attr,
			       pgshift, range, flags);
}

unsigned long process_init_stack_hwcap_result(
		process_init_stack_hwcap_fn_t hwcap_fn)
{
	if (!hwcap_fn)
		return 0;

	return hwcap_fn();
}

int process_init_stack_modify_context_result(
		void *uctx, int reg, unsigned long value,
		process_init_stack_modify_context_fn_t modify_context_fn)
{
	if (!modify_context_fn)
		return -EINVAL;

	modify_context_fn(uctx, reg, value);
	return 0;
}

int process_init_stack_log_result(int event, const unsigned long *args,
				  process_init_stack_log_fn_t log_fn)
{
	if (!log_fn || !args)
		return -EINVAL;

	log_fn(event, args);
	return 0;
}

static void process_init_stack_log(process_init_stack_log_fn_t log_fn,
				   int event, unsigned long arg0,
				   unsigned long arg1, unsigned long arg2,
				   unsigned long arg3, unsigned long arg4,
				   unsigned long arg5, unsigned long arg6,
				   unsigned long arg7, unsigned long arg8,
				   unsigned long arg9, unsigned long arg10,
				   unsigned long arg11)
{
	unsigned long args[12];

	if (!log_fn)
		return;

	args[0] = arg0;
	args[1] = arg1;
	args[2] = arg2;
	args[3] = arg3;
	args[4] = arg4;
	args[5] = arg5;
	args[6] = arg6;
	args[7] = arg7;
	args[8] = arg8;
	args[9] = arg9;
	args[10] = arg10;
	args[11] = arg11;
	process_init_stack_log_result(event, args, log_fn);
}

int process_init_stack_body_result(
	struct thread *thread, struct program_load_desc *pn,
	unsigned long at_base, int argc, char **argv, int envc, char **env,
	unsigned long page_size, int page_shift,
	unsigned long user_stack_page_mask, int user_stack_page_shift,
	unsigned long user_stack_prepage_size,
	unsigned long stack_alloc_size_override, int user_stack_page_p2align,
	unsigned long alloc_nowait, unsigned long alloc_user,
	unsigned long mpol_no_stack, int user_context_sp_reg,
	unsigned long pf_populate,
	process_init_stack_alloc_aligned_fn_t alloc_aligned_fn,
	process_init_stack_free_pages_fn_t free_pages_fn,
	process_init_stack_add_range_fn_t add_range_fn,
	process_init_stack_virt_to_phys_fn_t virt_to_phys_fn,
	process_attr_from_vrflag_fn_t attr_fn,
	process_init_stack_pt_set_range_fn_t pt_set_range_fn,
	process_init_stack_hwcap_fn_t hwcap_fn,
	process_init_stack_modify_context_fn_t modify_context_fn,
	process_init_stack_log_fn_t log_fn)
{
	struct process *proc;
	struct process_vm *vm;
	struct vm_range *range = NULL;
	unsigned long end, start, size, minsz, maxsz;
	unsigned long vrflag, ap_flag, ap_hwcap, at_rand, user_sp;
	unsigned long *p;
	char *stack;
	int stack_populated_size;
	int stack_align_padding = 0;
	int stack_npages;
	int s_ind = -1;
	int arg_ind;
	int error;
	int argv_null_i, env0_i, env_null_i, aux0_i;

	if (!thread || !pn || !page_size || page_shift < 0 ||
	    user_stack_page_shift < 0 || !alloc_aligned_fn || !free_pages_fn ||
	    !add_range_fn || !virt_to_phys_fn || !attr_fn || !pt_set_range_fn ||
	    !hwcap_fn || !modify_context_fn)
		return -EINVAL;
	proc = thread->proc;
	vm = thread->vm;
	if (!proc || !vm || !vm->address_space)
		return -EINVAL;

	end = vm->region.user_end & user_stack_page_mask;
	minsz = (pn->stack_premap + user_stack_prepage_size - 1) &
		user_stack_page_mask;
	maxsz = (end - vm->region.map_start) / 2;
	size = proc->rlimit[MCK_RLIMIT_STACK].rlim_cur;
	if (size > maxsz)
		size = maxsz;
	else if (size < minsz)
		size = minsz;
	size = (size + user_stack_prepage_size - 1) & user_stack_page_mask;
	process_init_stack_log(log_fn, PROCESS_INIT_STACK_LOG_SIZE,
			       pn->stack_premap,
			       proc->rlimit[MCK_RLIMIT_STACK].rlim_cur,
			       minsz, size, maxsz, 0, 0, 0, 0, 0, 0, 0);
	start = (end - minsz) & user_stack_page_mask;

	ap_flag = (minsz >= proc->mpol_threshold &&
		   !(proc->mpol_flags & mpol_no_stack)) ? alloc_user : 0;
	process_init_stack_log(log_fn, PROCESS_INIT_STACK_LOG_AP_USER, size,
			       minsz, ap_flag, 0, 0, 0, 0, 0, 0, 0, 0, 0);
	if (stack_alloc_size_override)
		minsz = stack_alloc_size_override;

	stack_npages = minsz >> page_shift;
	stack = process_init_stack_alloc_aligned_result(stack_npages,
			user_stack_page_p2align, alloc_nowait | ap_flag, start,
			alloc_aligned_fn);
	if (!stack) {
		process_init_stack_log(log_fn,
				       PROCESS_INIT_STACK_LOG_ALLOC_FAILED,
				       0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
				       0);
		return -ENOMEM;
	}
	memset(stack, 0, minsz);

	vrflag = VR_STACK | VR_DEMAND_PAGING | VR_PRIVATE;
	vrflag |= ((ap_flag & alloc_user) ? VR_AP_USER : 0);
	vrflag |= PROT_TO_VR_FLAG(pn->stack_prot);
	vrflag |= VR_MAXPROT_READ | VR_MAXPROT_WRITE | VR_MAXPROT_EXEC;
	error = process_init_stack_add_range_result(vm, start, end, NOPHYS,
			vrflag, user_stack_page_shift, &range, add_range_fn);
	if (error) {
		process_init_stack_free_pages_result(stack, stack_npages,
						     free_pages_fn);
		process_init_stack_log(log_fn,
				       PROCESS_INIT_STACK_LOG_ADD_FAILED,
				       error, 0, 0, 0, 0, 0, 0, 0, 0, 0,
				       0, 0);
		return error;
	}
	if (!range) {
		process_init_stack_free_pages_result(stack, stack_npages,
						     free_pages_fn);
		return -EINVAL;
	}

	error = process_init_stack_pt_set_range_result(
			vm->address_space->page_table, vm, end - minsz, end,
			process_init_stack_virt_to_phys_result(stack,
							       virt_to_phys_fn),
			process_attr_from_vrflag_result(vrflag, pf_populate,
							NULL, attr_fn),
			user_stack_page_shift, range, 0, pt_set_range_fn);
	if (error) {
		process_init_stack_log(log_fn, PROCESS_INIT_STACK_LOG_PT_FAILED,
				       end - minsz, end, (unsigned long)stack,
				       error, 0, 0, 0, 0, 0, 0, 0, 0);
		process_init_stack_free_pages_result(stack, stack_npages,
						     free_pages_fn);
		return error;
	}

	stack_populated_size = 16 + AUXV_LEN * sizeof(unsigned long) +
		(argc + 2) * sizeof(unsigned long) +
		(envc + 1) * sizeof(unsigned long);
	p = (unsigned long *)(stack + minsz);
	while ((unsigned long)(stack + minsz - stack_populated_size -
			       stack_align_padding) & (0x40UL - 1)) {
		s_ind--;
		stack_align_padding += sizeof(unsigned long);
	}

	process_init_stack_push(p, &s_ind, 0x010101011UL);
	process_init_stack_push(p, &s_ind, 0x010101011UL);
	at_rand = end + (s_ind + 1) * sizeof(unsigned long);

	process_init_stack_push(p, &s_ind, 0);
	process_init_stack_push(p, &s_ind, AT_NULL);
	process_init_stack_push(p, &s_ind,
				(argc > 0) ? (unsigned long)argv[0] : 0UL);
	process_init_stack_push(p, &s_ind, (argc > 0) ? AT_EXECFN : AT_IGNORE);
	process_init_stack_push(p, &s_ind, 0);
	process_init_stack_push(p, &s_ind, AT_HWCAP2);
	ap_hwcap = process_init_stack_hwcap_result(hwcap_fn);
	process_init_stack_push(p, &s_ind, ap_hwcap);
	process_init_stack_push(p, &s_ind, ap_hwcap ? AT_HWCAP : AT_IGNORE);
	process_init_stack_push(p, &s_ind, 0);
	process_init_stack_push(p, &s_ind, AT_SECURE);
	process_init_stack_push(p, &s_ind, proc->egid);
	process_init_stack_push(p, &s_ind, AT_EGID);
	process_init_stack_push(p, &s_ind, proc->rgid);
	process_init_stack_push(p, &s_ind, AT_GID);
	process_init_stack_push(p, &s_ind, proc->euid);
	process_init_stack_push(p, &s_ind, AT_EUID);
	process_init_stack_push(p, &s_ind, proc->ruid);
	process_init_stack_push(p, &s_ind, AT_UID);
	process_init_stack_push(p, &s_ind, pn->at_entry);
	process_init_stack_push(p, &s_ind, AT_ENTRY);
	process_init_stack_push(p, &s_ind, 0);
	process_init_stack_push(p, &s_ind, AT_FLAGS);
	process_init_stack_push(p, &s_ind, at_base);
	process_init_stack_push(p, &s_ind, AT_BASE);
	process_init_stack_push(p, &s_ind, pn->at_phnum);
	process_init_stack_push(p, &s_ind, AT_PHNUM);
	process_init_stack_push(p, &s_ind, pn->at_phent);
	process_init_stack_push(p, &s_ind, AT_PHENT);
	process_init_stack_push(p, &s_ind, pn->at_phdr);
	process_init_stack_push(p, &s_ind, AT_PHDR);
	process_init_stack_push(p, &s_ind, page_size);
	process_init_stack_push(p, &s_ind, AT_PAGESZ);
	process_init_stack_push(p, &s_ind, pn->at_clktck);
	process_init_stack_push(p, &s_ind, AT_CLKTCK);
	process_init_stack_push(p, &s_ind, at_rand);
	process_init_stack_push(p, &s_ind, AT_RANDOM);
	process_init_stack_push(p, &s_ind, (unsigned long)vm->vdso_addr);
	process_init_stack_push(p, &s_ind,
				vm->vdso_addr ? AT_SYSINFO_EHDR : AT_IGNORE);
	process_init_stack_log(log_fn, PROCESS_INIT_STACK_LOG_AUXV, proc->pid,
			       thread->tid, pn->at_entry, at_base, pn->at_phdr,
			       (unsigned long)vm->vdso_addr, page_size, at_rand,
			       end, argc, envc, 0);
	memcpy(proc->saved_auxv, &p[s_ind + 1], sizeof(proc->saved_auxv));

	process_init_stack_push(p, &s_ind, 0);
	for (arg_ind = envc - 1; arg_ind > -1; --arg_ind)
		process_init_stack_push(p, &s_ind, (unsigned long)env[arg_ind]);
	process_init_stack_push(p, &s_ind, 0);
	for (arg_ind = argc - 1; arg_ind > -1; --arg_ind)
		process_init_stack_push(p, &s_ind, (unsigned long)argv[arg_ind]);
	p[s_ind] = argc;

	if ((void *)&p[s_ind] !=
	    (void *)(stack + minsz - stack_populated_size -
		     stack_align_padding)) {
		process_init_stack_log(log_fn,
				       PROCESS_INIT_STACK_LOG_SIZE_MISMATCH,
				       (unsigned long)&p[s_ind],
				       (unsigned long)stack + minsz -
				       stack_populated_size -
				       stack_align_padding,
				       0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
	}
	if ((unsigned long)&p[s_ind] & (0x40UL - 1)) {
		process_init_stack_log(log_fn,
				       PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH,
				       0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
				       0);
	}

	user_sp = end + sizeof(unsigned long) * s_ind;
	argv_null_i = s_ind + argc + 1;
	env0_i = argv_null_i + 1;
	env_null_i = env0_i + envc;
	aux0_i = env_null_i + 1;
	process_init_stack_log(log_fn, PROCESS_INIT_STACK_LOG_INITIAL,
			       proc->pid, thread->tid, user_sp, p[s_ind],
			       argc > 0 ? p[s_ind + 1] : 0UL, p[argv_null_i],
			       envc > 0 ? p[env0_i] : 0UL, p[env_null_i],
			       p[aux0_i], p[aux0_i + 1], 0, 0);
	process_init_stack_modify_context_result(thread->uctx,
			user_context_sp_reg, user_sp, modify_context_fn);
	vm->region.stack_end = end;
	vm->region.stack_start = (end - size) & user_stack_page_mask;
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

int process_ref_dec_and_test_result(
		void *object, unsigned long ref_offset,
		process_ref_dec_and_test_fn_t dec_fn)
{
	if (dec_fn)
		return dec_fn(object, ref_offset);

	return process_ref_dec_and_test_direct_result(object, ref_offset);
}

int process_ref_set_result(void *object, unsigned long ref_offset, int value,
			   process_ref_set_fn_t ref_set_fn)
{
	if (ref_set_fn) {
		ref_set_fn(object, ref_offset, value);
		return 0;
	}

	return process_ref_set_direct_result(object, ref_offset, value);
}

int process_ref_inc_direct_result(void *object, unsigned long ref_offset)
{
	if (!object)
		return -EINVAL;

	ihk_atomic_inc((ihk_atomic_t *)((char *)object + ref_offset));
	return 0;
}

int process_ref_dec_and_test_direct_result(void *object,
					   unsigned long ref_offset)
{
	if (!object)
		return -EINVAL;

	return ihk_atomic_dec_and_test((ihk_atomic_t *)((char *)object +
						       ref_offset));
}

int process_ref_set_direct_result(void *object, unsigned long ref_offset,
				  int value)
{
	if (!object)
		return -EINVAL;

	ihk_atomic_set((ihk_atomic_t *)((char *)object + ref_offset), value);
	return 0;
}

void *process_alloc_result(unsigned long size, unsigned long flags,
			   process_alloc_fn_t alloc_fn)
{
	if (!alloc_fn)
		return NULL;

	return alloc_fn(size, flags);
}

int process_free_callback_result(void *ptr, process_free_fn_t free_fn)
{
	if (!free_fn)
		return -EINVAL;

	free_fn(ptr);
	return 0;
}

void *process_pt_create_result(unsigned long flags,
			       process_pt_create_fn_t pt_create_fn)
{
	if (!pt_create_fn)
		return NULL;

	return pt_create_fn(flags);
}

int process_pt_destroy_result(void *page_table,
			      process_pt_destroy_fn_t pt_destroy_fn)
{
	if (!pt_destroy_fn)
		return -EINVAL;

	pt_destroy_fn(page_table);
	return 0;
}

int process_spin_init_result(unsigned long lock_addr,
			     process_spin_init_fn_t spin_init_fn)
{
	if (!spin_init_fn)
		return -EINVAL;

	spin_init_fn(lock_addr);
	return 0;
}

int process_address_space_free_cb_result(
		void *asp, void *opt,
		process_address_space_free_cb_fn_t free_cb)
{
	if (!free_cb)
		return 0;

	free_cb(asp, opt);
	return 0;
}

int process_address_space_action_result(
		void *asp, process_address_space_action_fn_t action_fn)
{
	if (!action_fn)
		return -EINVAL;

	action_fn(asp);
	return 0;
}

int process_release_address_space_body_result(
	void *asp, unsigned long refcount_offset, unsigned long free_cb_offset,
	unsigned long opt_offset, unsigned long page_table_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_pt_destroy_fn_t pt_destroy_fn, process_free_fn_t free_fn)
{
	process_address_space_free_cb_fn_t free_cb;
	void *opt;
	void *page_table;

	if (!asp || !pt_destroy_fn || !free_fn)
		return -EINVAL;

	if (!process_release_address_space_should_destroy_result(
		    process_ref_dec_and_test_result(asp, refcount_offset,
						    dec_fn)))
		return 0;

	free_cb = *(process_address_space_free_cb_fn_t *)
		((char *)asp + free_cb_offset);
	if (process_release_address_space_should_run_free_cb_result(
		    (unsigned long)free_cb)) {
		opt = *(void **)((char *)asp + opt_offset);
		process_address_space_free_cb_result(asp, opt, free_cb);
	}

	page_table = *(void **)((char *)asp + page_table_offset);
	process_pt_destroy_result(page_table, pt_destroy_fn);
	process_free_callback_result(asp, free_fn);
	return 1;
}

int process_hold_address_space_public_result(
	void *asp, unsigned long refcount_offset, process_ref_inc_fn_t inc_fn)
{
	return process_ref_hold_body_result(asp, refcount_offset, inc_fn);
}

int process_release_address_space_public_result(
	void *asp, unsigned long refcount_offset, unsigned long free_cb_offset,
	unsigned long opt_offset, unsigned long page_table_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_pt_destroy_fn_t pt_destroy_fn, process_free_fn_t free_fn)
{
	return process_release_address_space_body_result(asp, refcount_offset,
			free_cb_offset, opt_offset, page_table_offset, dec_fn,
			pt_destroy_fn, free_fn);
}

int process_detach_address_space_body_result(
	void *asp, int pid, unsigned long pids_offset,
	unsigned long nslots_offset, process_address_space_action_fn_t release_fn)
{
	int *pids;
	int nslots;
	int detached;

	if (!asp || !release_fn)
		return -EINVAL;

	pids = (int *)((char *)asp + pids_offset);
	nslots = *(int *)((char *)asp + nslots_offset);
	detached = process_address_space_pid_detach_result(pids, nslots, pid);
	process_address_space_action_result(asp, release_fn);
	return detached;
}

int process_detach_address_space_public_result(
	void *asp, int pid, unsigned long pids_offset,
	unsigned long nslots_offset, process_address_space_action_fn_t release_fn)
{
	return process_detach_address_space_body_result(asp, pid, pids_offset,
			nslots_offset, release_fn);
}

void *process_create_address_space_body_result(
	int nslots, unsigned long address_space_size,
	unsigned long pid_slot_size, unsigned long nowait_flag,
	unsigned long page_table_offset, unsigned long refcount_offset,
	unsigned long cpu_set_offset, unsigned long cpu_set_size,
	unsigned long cpu_set_lock_offset, unsigned long nslots_offset,
	process_alloc_fn_t alloc_fn, process_free_fn_t free_fn,
	process_pt_create_fn_t pt_create_fn, process_ref_set_fn_t ref_set_fn,
	process_spin_init_fn_t spin_init_fn)
{
	unsigned long total_size;
	void *asp;
	void *pt;

	if (nslots < 0 || !alloc_fn || !free_fn || !pt_create_fn ||
	    !spin_init_fn)
		return NULL;

	total_size = address_space_size + pid_slot_size * (unsigned long)nslots;
	asp = process_alloc_result(total_size, nowait_flag, alloc_fn);
	if (!asp)
		return NULL;

	pt = process_pt_create_result(nowait_flag, pt_create_fn);
	if (!pt) {
		process_free_callback_result(asp, free_fn);
		return NULL;
	}

	memset(asp, 0, total_size);
	*(int *)((char *)asp + nslots_offset) = nslots;
	*(void **)((char *)asp + page_table_offset) = pt;
	process_ref_set_result(asp, refcount_offset, 1, ref_set_fn);
	memset((char *)asp + cpu_set_offset, 0, cpu_set_size);
	process_spin_init_result((unsigned long)((char *)asp +
					cpu_set_lock_offset), spin_init_fn);
	return asp;
}

int process_create_cpu_allowed_result(int cpu, int num_processors)
{
	return cpu >= 0 && cpu < num_processors;
}

int process_create_use_default_cpu_set_result(int cpu_set_empty)
{
	return cpu_set_empty != 0;
}

static int process_cpu_set_word(unsigned long cpu_set_addr, int cpu,
				int cpu_set_bits, unsigned long **wordp,
				unsigned long *maskp);

static int process_cpu_input_bit_is_set(unsigned long cpu_set_addr,
					unsigned long cpu)
{
	unsigned long word_bits = sizeof(unsigned long) * 8;
	unsigned long *word;
	unsigned long mask;

	if (!cpu_set_addr)
		return 0;

	word = ((unsigned long *)cpu_set_addr) + cpu / word_bits;
	mask = 1UL << (cpu % word_bits);
	return (*word & mask) != 0;
}

static int process_cpu_set_direct(unsigned long cpu_set_addr, int cpu,
				  int cpu_set_bits)
{
	unsigned long *word;
	unsigned long mask;

	if (!process_cpu_set_word(cpu_set_addr, cpu, cpu_set_bits,
				  &word, &mask))
		return 0;

	*word |= mask;
	return 1;
}

int process_create_cpu_sets_body_result(
	unsigned long requested_cpu_set_addr, unsigned long requested_bits,
	unsigned long thread_cpu_set_addr, unsigned long proc_cpu_set_addr,
	int output_cpu_set_bits, int num_processors, int pid,
	process_default_ncpus_fn_t default_ncpus_fn,
	process_create_cpu_log_fn_t log_fn)
{
	int selected = 0;
	unsigned long cpu;

	if (!thread_cpu_set_addr || !proc_cpu_set_addr || output_cpu_set_bits <= 0)
		return -EINVAL;
	if (requested_bits && !requested_cpu_set_addr)
		return -EINVAL;

	for (cpu = 0; cpu < requested_bits; cpu++) {
		int cpu_i;

		if (!process_cpu_input_bit_is_set(requested_cpu_set_addr, cpu))
			continue;

		cpu_i = (int)cpu;
		if (!process_create_cpu_allowed_result(cpu_i, num_processors)) {
			if (log_fn)
				log_fn(PROCESS_CREATE_CPU_LOG_INVALID,
				       pid, cpu_i);
			return -EINVAL;
		}
		if (log_fn)
			log_fn(PROCESS_CREATE_CPU_LOG_REQUESTED, pid, cpu_i);
		selected += process_cpu_set_direct(thread_cpu_set_addr,
						   cpu_i, output_cpu_set_bits);
		selected += process_cpu_set_direct(proc_cpu_set_addr,
						   cpu_i, output_cpu_set_bits);
	}

	if (process_create_use_default_cpu_set_result(selected == 0)) {
		int default_ncpus;
		int default_cpu;

		if (!default_ncpus_fn)
			return -EINVAL;

		default_ncpus = default_ncpus_fn();
		if (default_ncpus < 0)
			return -EINVAL;

		for (default_cpu = 0; default_cpu < default_ncpus;
		     default_cpu++) {
			selected += process_cpu_set_direct(thread_cpu_set_addr,
							   default_cpu,
							   output_cpu_set_bits);
			selected += process_cpu_set_direct(proc_cpu_set_addr,
							   default_cpu,
							   output_cpu_set_bits);
		}
	}

	return selected / 2;
}

int process_allocated_object_zero_body_result(void *object,
					      unsigned long object_size)
{
	if (!object)
		return -EINVAL;

	memset(object, 0, object_size);
	return 0;
}

int process_vm_init_body_result(
	struct process_vm *vm, struct process *owner, void *asp,
	int nr_numa_nodes, process_rwlock_init_fn_t memory_lock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_vm_init_numa_log_fn_t numa_log_fn)
{
	int i;

	if (!vm || !memory_lock_init_fn || !spin_init_fn)
		return -EINVAL;

	memory_lock_init_fn((unsigned long)&vm->memory_range_lock);
	process_spin_init_result((unsigned long)&vm->page_table_lock,
				 spin_init_fn);

	ihk_atomic_set(&vm->refcount, 1);
	vm->vm_range_tree = RB_ROOT;
	vm->vm_range_numa_policy_tree = RB_ROOT;
	vm->address_space = asp;
	vm->proc = owner;
	vm->exiting = 0;

	memset(&vm->numa_mask, 0, sizeof(vm->numa_mask));
	for (i = 0; i < nr_numa_nodes; ++i) {
		if (i >= PROCESS_NUMA_MASK_BITS) {
			if (numa_log_fn)
				numa_log_fn(i);
			break;
		}
		vm->numa_mask[i / (int)(sizeof(unsigned long) * 8)] |=
			1UL << (i % (int)(sizeof(unsigned long) * 8));
	}
	vm->numa_mem_policy = MPOL_DEFAULT;

	for (i = 0; i < VM_RANGE_CACHE_SIZE; ++i) {
		vm->range_cache[i] = NULL;
	}
	vm->range_cache_ind = 0;

#ifdef ENABLE_TOFU
	process_spin_init_result((unsigned long)&vm->tofu_stag_lock,
				 spin_init_fn);
	for (i = 0; i < TOFU_STAG_HASH_SIZE; ++i) {
		INIT_LIST_HEAD(&vm->tofu_stag_hash[i]);
	}
#endif
	return 0;
}

static void *process_new_resource_cleanup(struct resource_set *res,
					  struct process_hash *phash,
					  struct thread_hash *thash,
					  struct process *pid1,
					  process_free_fn_t free_fn)
{
	if (res)
		free_fn(res);
	if (phash)
		free_fn(phash);
	if (thash)
		free_fn(thash);
	if (pid1)
		free_fn(pid1);
	return NULL;
}

void *process_new_resource_set_body_result(
	unsigned long resource_set_size, unsigned long process_hash_size,
	unsigned long thread_hash_size, unsigned long process_size,
	unsigned long nowait_flag, int hash_size, int init_pid,
	process_alloc_fn_t alloc_fn, process_free_fn_t free_fn,
	process_init_process_fn_t init_process_fn,
	process_rwlock_init_fn_t rwlock_init_fn)
{
	struct resource_set *res;
	struct process_hash *phash;
	struct thread_hash *thash;
	struct process *pid1;
	int i;
	int hash;

	if (!alloc_fn || !free_fn || !init_process_fn || !rwlock_init_fn ||
	    hash_size <= 0 || hash_size > HASH_SIZE)
		return NULL;

	res = alloc_fn(resource_set_size, nowait_flag);
	phash = alloc_fn(process_hash_size, nowait_flag);
	thash = alloc_fn(thread_hash_size, nowait_flag);
	pid1 = alloc_fn(process_size, nowait_flag);
	if (!res || !phash || !thash || !pid1)
		return process_new_resource_cleanup(res, phash, thash, pid1,
						    free_fn);

	if (process_allocated_object_zero_body_result(res, resource_set_size) < 0 ||
	    process_allocated_object_zero_body_result(phash, process_hash_size) < 0 ||
	    process_allocated_object_zero_body_result(thash, thread_hash_size) < 0 ||
	    process_allocated_object_zero_body_result(pid1, process_size) < 0)
		return process_new_resource_cleanup(res, phash, thash, pid1,
						    free_fn);

	INIT_LIST_HEAD(&res->phys_mem_list);
	rwlock_init_fn((unsigned long)&res->phys_mem_lock);
	rwlock_init_fn((unsigned long)&res->cpu_set_lock);

	for (i = 0; i < hash_size; i++) {
		INIT_LIST_HEAD(&phash->list[i]);
		rwlock_init_fn((unsigned long)&phash->lock[i]);
	}
	res->process_hash = phash;

	for (i = 0; i < hash_size; i++) {
		INIT_LIST_HEAD(&thash->list[i]);
		rwlock_init_fn((unsigned long)&thash->lock[i]);
	}
	res->thread_hash = thash;

	if (init_process_fn(pid1, pid1) != 0)
		return process_new_resource_cleanup(res, phash, thash, pid1,
						    free_fn);
	pid1->pid = init_pid;
	hash = init_pid % hash_size;
	process_list_add_tail_result(&pid1->hash_list, &phash->list[hash]);
	res->pid1 = pid1;

	return res;
}

int process_memset_smp_handler_body_result(
	int cpu_index, int nr_cpus, unsigned long phys, size_t len, int value,
	process_phys_to_virt_fn_t phys_to_virt_fn,
	process_memset_fn_t memset_fn,
	process_memset_smp_log_fn_t log_fn)
{
	size_t chunk;
	unsigned long start;
	unsigned long end;

	if (!phys_to_virt_fn || !memset_fn || cpu_index < 0 || nr_cpus <= 0)
		return -EINVAL;

	chunk = len / nr_cpus;
	if (!chunk) {
		if (!cpu_index)
			memset_fn(phys_to_virt_fn(phys), value, len);
		return 0;
	}

	start = phys + cpu_index * chunk;
	end = start + chunk;
	if (cpu_index == nr_cpus - 1)
		end = phys + len;

	memset_fn(phys_to_virt_fn(start), value, end - start);
	if (log_fn)
		log_fn(1, cpu_index, nr_cpus, phys, len, start, end);
	return 0;
}

int process_memset_smp_body_result(
	void *cpu_set, void *addr, int value, size_t len,
	unsigned long *phys_slot, size_t *len_slot, int *value_slot,
	void *handler, void *request,
	process_virt_to_phys_fn_t virt_to_phys_fn,
	process_smp_call_fn_t smp_call_fn)
{
	if (!phys_slot || !len_slot || !value_slot || !handler || !request ||
	    !virt_to_phys_fn || !smp_call_fn)
		return -EINVAL;

	*phys_slot = virt_to_phys_fn(addr);
	*len_slot = len;
	*value_slot = value;
	return smp_call_fn(cpu_set, handler, request);
}

int process_proc_init_body_result(
	void *resource_set, struct list_head *resource_set_list,
	unsigned long resource_set_lock_addr, int num_processors,
	int cpu_set_bits, unsigned long path_size, unsigned long nowait_flag,
	process_alloc_fn_t alloc_fn, process_rwlock_init_fn_t rwlock_init_fn)
{
	struct resource_set *res = resource_set;
	char *path;
	int cpu;

	if (!res || !resource_set_list || !alloc_fn || !rwlock_init_fn ||
	    path_size == 0)
		return -EINVAL;

	INIT_LIST_HEAD(resource_set_list);
	rwlock_init_fn(resource_set_lock_addr);
	for (cpu = 0; cpu < num_processors; cpu++)
		CPU_SET(cpu, &res->cpu_set);

	path = alloc_fn(path_size, nowait_flag);
	if (!path)
		return -ENOMEM;
	path[0] = '/';
	path[0] = '\0';
	res->path = path;
	process_list_add_tail_result(&res->list, resource_set_list);

	(void)cpu_set_bits;
	return 0;
}

int process_sched_init_body_result(
	unsigned long cpu_local_addr, struct list_head *resource_set_list,
	int current_cpu, process_init_process_fn_t init_process_fn,
	process_rwlock_init_fn_t memory_lock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_sched_init_context_fn_t init_context_fn,
	process_sched_save_fp_fn_t save_fp_fn,
	process_sched_timer_init_fn_t timer_init_fn)
{
	struct cpu_local_var *cpu_local = (struct cpu_local_var *)cpu_local_addr;
	struct thread *idle_thread;
	struct process *idle_proc;
	struct process_vm *idle_vm;
	struct resource_set *res;

	if (!cpu_local || !resource_set_list || !init_process_fn ||
	    !memory_lock_init_fn || !spin_init_fn || !init_context_fn ||
	    !save_fp_fn || !timer_init_fn)
		return -EINVAL;
	if (list_empty(resource_set_list))
		return -ENOMEM;

	res = ((struct resource_set *)((char *)((resource_set_list)->next) - offsetof(struct resource_set, list)));
	cpu_local->resource_set = res;

	idle_thread = &cpu_local->idle;
	idle_proc = &cpu_local->idle_proc;
	idle_vm = &cpu_local->idle_vm;
	if (process_allocated_object_zero_body_result(idle_thread,
			sizeof(*idle_thread)) < 0 ||
	    process_allocated_object_zero_body_result(idle_vm,
			sizeof(*idle_vm)) < 0 ||
	    process_allocated_object_zero_body_result(idle_proc,
			sizeof(*idle_proc)) < 0)
		return -EINVAL;

	idle_thread->vm = idle_vm;
	idle_vm->address_space = &cpu_local->idle_asp;
	idle_thread->proc = idle_proc;
	if (init_process_fn(idle_proc, NULL) != 0)
		return -EINVAL;
	idle_proc->nohost = 1;
	idle_proc->vm = idle_vm;
	process_list_add_tail_result(&idle_thread->siblings_list,
				     &idle_proc->children_list);

	init_context_fn(idle_thread);
	memory_lock_init_fn((unsigned long)&idle_vm->memory_range_lock);
	idle_vm->vm_range_tree = RB_ROOT;
	idle_vm->vm_range_numa_policy_tree = RB_ROOT;
	idle_proc->pid = 0;
	idle_thread->tid = current_cpu;

	INIT_LIST_HEAD(&cpu_local->runq);
	cpu_local->runq_len = 0;
	process_spin_init_result((unsigned long)&cpu_local->runq_lock,
				 spin_init_fn);

	INIT_LIST_HEAD(&cpu_local->migq);
	process_spin_init_result((unsigned long)&cpu_local->migq_lock,
				 spin_init_fn);

	save_fp_fn(idle_thread);
	timer_init_fn(current_cpu);

	return 0;
}

int process_init_state_body_result(
	void *process, const void *parent,
	const struct process_init_state_offsets *offsets,
	int initial_pid, int running_status)
{
	char *proc = process;
	const char *pproc = parent;

	if (!proc || !offsets)
		return -EINVAL;

	*(int *)(proc + offsets->pid_offset) = initial_pid;
	*(int *)(proc + offsets->status_offset) = running_status;

	if (!pproc)
		return 0;

	*(void **)(proc + offsets->parent_offset) = (void *)pproc;
	*(void **)(proc + offsets->ppid_parent_offset) = (void *)pproc;
	*(int *)(proc + offsets->pgid_offset) =
		*(const int *)(pproc + offsets->pgid_offset);
	*(int *)(proc + offsets->ruid_offset) =
		*(const int *)(pproc + offsets->ruid_offset);
	*(int *)(proc + offsets->euid_offset) =
		*(const int *)(pproc + offsets->euid_offset);
	*(int *)(proc + offsets->suid_offset) =
		*(const int *)(pproc + offsets->suid_offset);
	*(int *)(proc + offsets->fsuid_offset) =
		*(const int *)(pproc + offsets->fsuid_offset);
	*(int *)(proc + offsets->rgid_offset) =
		*(const int *)(pproc + offsets->rgid_offset);
	*(int *)(proc + offsets->egid_offset) =
		*(const int *)(pproc + offsets->egid_offset);
	*(int *)(proc + offsets->sgid_offset) =
		*(const int *)(pproc + offsets->sgid_offset);
	*(int *)(proc + offsets->fsgid_offset) =
		*(const int *)(pproc + offsets->fsgid_offset);
	*(unsigned long *)(proc + offsets->mpol_flags_offset) =
		*(const unsigned long *)(pproc + offsets->mpol_flags_offset);
	*(unsigned long *)(proc + offsets->mpol_threshold_offset) =
		*(const unsigned long *)(pproc +
					 offsets->mpol_threshold_offset);
	*(int *)(proc + offsets->thp_disable_offset) =
		*(const int *)(pproc + offsets->thp_disable_offset);
	memcpy(proc + offsets->rlimit_offset, pproc + offsets->rlimit_offset,
	       offsets->rlimit_size);
	memcpy(proc + offsets->cpu_set_offset, pproc + offsets->cpu_set_offset,
	       offsets->cpu_set_size);
	*(int *)(proc + offsets->enable_uti_offset) =
		*(const int *)(pproc + offsets->enable_uti_offset);
	return 0;
}

int process_init_links_body_result(
	void *process, unsigned long hash_list_offset,
	unsigned long siblings_list_offset,
	unsigned long ptraced_siblings_list_offset,
	unsigned long update_lock_offset,
	unsigned long report_threads_list_offset,
	unsigned long threads_list_offset,
	unsigned long children_list_offset,
	unsigned long ptraced_children_list_offset,
	unsigned long threads_lock_offset,
	unsigned long children_lock_offset,
	unsigned long coredump_lock_offset,
	unsigned long mckfd_lock_offset,
	unsigned long waitpid_q_offset,
	unsigned long refcount_offset,
	unsigned long monitoring_event_offset,
	process_rwlock_init_fn_t rwlock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_waitq_init_fn_t waitq_init_fn,
	process_ref_set_fn_t ref_set_fn)
{
	char *proc = process;

	if (!proc || !rwlock_init_fn || !spin_init_fn || !waitq_init_fn)
		return -EINVAL;

	INIT_LIST_HEAD((struct list_head *)(proc + hash_list_offset));
	INIT_LIST_HEAD((struct list_head *)(proc + siblings_list_offset));
	INIT_LIST_HEAD((struct list_head *)(proc + ptraced_siblings_list_offset));
	rwlock_init_fn((unsigned long)(proc + update_lock_offset));
	INIT_LIST_HEAD((struct list_head *)(proc + report_threads_list_offset));
	INIT_LIST_HEAD((struct list_head *)(proc + threads_list_offset));
	INIT_LIST_HEAD((struct list_head *)(proc + children_list_offset));
	INIT_LIST_HEAD((struct list_head *)(proc + ptraced_children_list_offset));
	rwlock_init_fn((unsigned long)(proc + threads_lock_offset));
	rwlock_init_fn((unsigned long)(proc + children_lock_offset));
	rwlock_init_fn((unsigned long)(proc + coredump_lock_offset));
	process_spin_init_result((unsigned long)(proc + mckfd_lock_offset),
				 spin_init_fn);
	waitq_init_fn((unsigned long)(proc + waitpid_q_offset));
	if (process_ref_set_result(process, refcount_offset, 2, ref_set_fn))
		return -EINVAL;
	*(void **)(proc + monitoring_event_offset) = NULL;
	return 0;
}

int process_init_profile_body_result(
	void *process, unsigned long profile_lock_offset,
	unsigned long profile_events_offset,
	process_mcs_lock_init_fn_t lock_init_fn)
{
	char *proc = process;

	if (!proc || !lock_init_fn)
		return -EINVAL;

	lock_init_fn((unsigned long)(proc + profile_lock_offset));
	*(void **)(proc + profile_events_offset) = NULL;
	return 0;
}

int process_clone_thread_base_state_body_result(
	void *thread, const void *origin, unsigned long cpu_set_offset,
	unsigned long cpu_set_size, unsigned long in_kernel_offset)
{
	char *dst = thread;
	const char *src = origin;

	if (!dst || !src)
		return -EINVAL;

	memcpy(dst + cpu_set_offset, src + cpu_set_offset, cpu_set_size);
	*(int *)(dst + in_kernel_offset) =
		*(const int *)(src + in_kernel_offset);
	return 0;
}

int process_clone_thread_sched_state_body_result(
	void *thread, const void *origin, unsigned long sched_policy_offset,
	unsigned long sched_priority_offset)
{
	char *dst = thread;
	const char *src = origin;

	if (!dst || !src)
		return -EINVAL;

	*(int *)(dst + sched_policy_offset) =
		*(const int *)(src + sched_policy_offset);
	*(int *)(dst + sched_priority_offset) =
		*(const int *)(src + sched_priority_offset);
	return 0;
}

int process_thread_sched_default_body_result(
	void *thread, unsigned long sched_policy_offset, int default_policy)
{
	if (!thread)
		return -EINVAL;

	*(int *)((char *)thread + sched_policy_offset) = default_policy;
	return 0;
}

int process_create_thread_link_state_body_result(
	void *thread, void *process, void *vm, unsigned long thread_vm_offset,
	unsigned long thread_proc_offset, unsigned long process_vm_offset,
	unsigned long process_main_thread_offset)
{
	char *thread_base = thread;
	char *process_base = process;

	if (!thread || !process || !vm)
		return -EINVAL;

	*(void **)(thread_base + thread_vm_offset) = vm;
	*(void **)(thread_base + thread_proc_offset) = process;
	*(void **)(process_base + process_vm_offset) = vm;
	*(void **)(process_base + process_main_thread_offset) = thread;
	return 0;
}

int process_thread_exit_status_init_body_result(
	void *thread, unsigned long exit_status_offset, int exit_status)
{
	if (!thread)
		return -EINVAL;

	*(int *)((char *)thread + exit_status_offset) = exit_status;
	return 0;
}

int process_thread_spin_sleep_init_body_result(
	void *thread, unsigned long spin_sleep_lock_offset,
	unsigned long spin_sleep_offset, process_spin_init_fn_t spin_init_fn)
{
	char *thread_base = thread;

	if (!thread || !spin_init_fn)
		return -EINVAL;

	process_spin_init_result((unsigned long)(thread_base + spin_sleep_lock_offset),
				 spin_init_fn);
	*(int *)(thread_base + spin_sleep_offset) = 0;
	return 0;
}

int process_thread_sigmask_copy_body_result(
	void *thread, const void *origin, unsigned long sigmask_offset,
	unsigned long sigmask_size)
{
	if (!thread || !origin)
		return -EINVAL;

	memcpy((char *)thread + sigmask_offset,
	       (const char *)origin + sigmask_offset, sigmask_size);
	return 0;
}

int process_clone_profile_state_body_result(
	void *thread, const void *origin, const void *process,
	unsigned long thread_profile_offset, unsigned long process_profile_offset)
{
	char *thread_base = thread;
	const char *origin_base = origin;
	const char *process_base = process;

	if (!thread || !origin || !process)
		return -EINVAL;

	*(int *)(thread_base + thread_profile_offset) =
		*(const int *)(origin_base + thread_profile_offset) |
		*(const int *)(process_base + process_profile_offset);
	return 0;
}

int process_clone_fork_process_termsig_body_result(
	void *process, unsigned long termsig_offset, int termsig)
{
	if (!process)
		return -EINVAL;

	*(int *)((char *)process + termsig_offset) = termsig;
	return 0;
}

int process_clone_fork_saved_cmdline_body_result(
	void *process, const void *origin_process,
	unsigned long saved_cmdline_len_offset,
	unsigned long saved_cmdline_offset, unsigned long nowait_flag,
	process_alloc_fn_t alloc_fn)
{
	char *dst = process;
	const char *src = origin_process;
	long len;
	void *cmdline;

	if (!process || !origin_process || !alloc_fn)
		return -EINVAL;

	len = *(const long *)(src + saved_cmdline_len_offset);
	*(long *)(dst + saved_cmdline_len_offset) = len;
	cmdline = alloc_fn((unsigned long)len, nowait_flag);
	if (!cmdline)
		return -ENOMEM;
	if (len)
		memcpy(cmdline, *(void * const *)(src + saved_cmdline_offset),
		       (size_t)len);
	*(void **)(dst + saved_cmdline_offset) = cmdline;
	return 0;
}

int process_clone_fork_vm_policy_body_result(
	void *dst_vm, const void *src_vm, unsigned long numa_mask_offset,
	unsigned long numa_mask_size, unsigned long numa_mem_policy_offset,
	unsigned long region_offset, unsigned long region_size)
{
	char *dst = dst_vm;
	const char *src = src_vm;

	if (!dst_vm || !src_vm)
		return -EINVAL;

	memcpy(dst + numa_mask_offset, src + numa_mask_offset, numa_mask_size);
	*(int *)(dst + numa_mem_policy_offset) =
		*(const int *)(src + numa_mem_policy_offset);
	memcpy(dst + region_offset, src + region_offset, region_size);
	return 0;
}

int process_clone_thread_shared_vm_state_body_result(
	void *thread, void *process, void *vm, unsigned long thread_vm_offset,
	unsigned long thread_proc_offset)
{
	char *thread_base = thread;

	if (!thread || !process || !vm)
		return -EINVAL;

	*(void **)(thread_base + thread_vm_offset) = vm;
	*(void **)(thread_base + thread_proc_offset) = process;
	return 0;
}

int process_clone_sigcommon_share_body_result(
	void *thread, const void *origin, unsigned long sigcommon_offset,
	unsigned long sigcommon_use_offset, process_ref_inc_fn_t ref_inc_fn)
{
	char *thread_base = thread;
	const char *origin_base = origin;
	void *sigcommon;

	if (!thread || !origin)
		return -EINVAL;

	sigcommon = *(void * const *)(origin_base + sigcommon_offset);
	if (!sigcommon)
		return -EINVAL;

	*(void **)(thread_base + sigcommon_offset) = sigcommon;
	process_ref_inc_result(sigcommon, sigcommon_use_offset, ref_inc_fn);
	return 0;
}

int process_clone_sigcommon_action_copy_body_result(
	void *dst_sigcommon, const void *src_sigcommon,
	unsigned long action_offset, unsigned long action_size)
{
	if (!dst_sigcommon || !src_sigcommon)
		return -EINVAL;

	memcpy((char *)dst_sigcommon + action_offset,
	       (const char *)src_sigcommon + action_offset, action_size);
	return 0;
}

int process_clone_user_context_body_result(
	void *thread, const void *origin, unsigned long uctx_offset,
	unsigned long uctx_size, int stack_pointer_reg, unsigned long sp,
	int program_counter_reg, unsigned long pc,
	process_init_stack_modify_context_fn_t modify_context_fn)
{
	char *thread_base = thread;
	const char *origin_base = origin;
	void *dst_uctx;
	void *src_uctx;

	if (!thread || !origin || !modify_context_fn)
		return -EINVAL;

	dst_uctx = *(void **)(thread_base + uctx_offset);
	src_uctx = *(void * const *)(origin_base + uctx_offset);
	if (!dst_uctx || !src_uctx)
		return -EINVAL;

	memcpy(dst_uctx, src_uctx, uctx_size);
	modify_context_fn(dst_uctx, stack_pointer_reg, sp);
	modify_context_fn(dst_uctx, program_counter_reg, pc);
	return 0;
}

int process_clone_fork_profile_body_result(
	void *process, const void *origin_process, unsigned long profile_offset)
{
	if (!process || !origin_process)
		return -EINVAL;

	*(int *)((char *)process + profile_offset) =
		*(const int *)((const char *)origin_process + profile_offset);
	return 0;
}

int process_clone_on_fork_vm_body_result(
	void *cpu_local, unsigned long on_fork_vm_offset, void *vm)
{
	if (!cpu_local)
		return -EINVAL;

	*(void **)((char *)cpu_local + on_fork_vm_offset) = vm;
	return 0;
}

int process_mckfd_copy_body_result(void *dst, const void *src,
				   unsigned long mckfd_size)
{
	if (!dst || !src)
		return -EINVAL;

	memcpy(dst, src, mckfd_size);
	return 0;
}

int process_copy_user_range_metadata_body_result(
	struct vm_range *dst, const struct vm_range *src,
	process_range_memobj_ref_fn_t memobj_ref_fn)
{
	if (!dst || !src)
		return -EINVAL;

	RB_CLEAR_NODE(&dst->vm_rb_node);
	dst->start = src->start;
	dst->end = src->end;
	dst->flag = src->flag;
	dst->memobj = src->memobj;
	dst->objoff = src->objoff;
	dst->pgshift = src->pgshift;
	dst->private_data = src->private_data;
	dst->straight_start = src->straight_start;

	return process_range_memobj_ref_or_direct_result(dst->memobj,
							memobj_ref_fn);
}

int process_copy_user_pte_args_init_body_result(
	void *args, unsigned long new_vm_offset,
	unsigned long new_vrflag_offset, unsigned long range_offset,
	unsigned long fault_addr_offset, void *vm, unsigned long vrflag,
	void *range, long fault_addr)
{
	char *base = args;

	if (!args || !vm || !range)
		return -EINVAL;

	*(void **)(base + new_vm_offset) = vm;
	*(unsigned long *)(base + new_vrflag_offset) = vrflag;
	*(void **)(base + range_offset) = range;
	*(long *)(base + fault_addr_offset) = fault_addr;
	return 0;
}

int process_copy_user_pte_buffer_body_result(void *dst, const void *src,
					     size_t len, int wipe)
{
	if (!dst || (!wipe && !src))
		return -EINVAL;

	if (wipe)
		memset(dst, 0, len);
	else
		memcpy(dst, src, len);
	return 0;
}

int process_copy_user_ranges_body_result(
	struct process_vm *vm, struct process_vm *orgvm,
	unsigned long range_size, unsigned long alloc_flags, void *copy_args,
	unsigned long new_vm_offset, unsigned long new_vrflag_offset,
	unsigned long range_offset, unsigned long fault_addr_offset,
	void *copy_pte_fn, int visit_flags,
	process_noirq_lock_fn_t read_lock_fn,
	process_noirq_unlock_fn_t read_unlock_fn,
	process_copy_range_lookup_fn_t lookup_fn,
	process_copy_range_next_fn_t next_fn,
	process_add_range_alloc_fn_t alloc_fn,
	process_add_range_free_fn_t free_fn,
	process_add_range_insert_fn_t insert_fn,
	process_visit_pte_range_fn_t visit_fn,
	process_memory_range_free_fn_t free_range_fn,
	process_copy_user_ranges_log_fn_t log_fn)
{
	struct vm_range *src_range;
	struct vm_range *last_insert;
	int error = 0;

	(void)alloc_flags;

	if (!vm || !orgvm || !copy_args || !copy_pte_fn ||
	    !orgvm->address_space || !read_lock_fn || !read_unlock_fn ||
	    !lookup_fn || !next_fn || !alloc_fn || !free_fn || !insert_fn ||
	    !visit_fn || !free_range_fn)
		return -EINVAL;

	process_noirq_lock_result((unsigned long)&orgvm->memory_range_lock,
				  read_lock_fn);

	last_insert = NULL;
	src_range = NULL;
	for (;;) {
		struct vm_range *range;

		if (!src_range)
			src_range = lookup_fn(orgvm, 0, NOPHYS);
		else
			src_range = next_fn(orgvm, src_range);
		if (!src_range)
			break;

		if (src_range->flag & VR_DONTFORK)
			continue;

		range = alloc_fn(range_size);
		if (!range) {
			error = -1;
			break;
		}

		if (process_copy_user_range_metadata_body_result(range,
				src_range, NULL) < 0) {
			free_fn(range);
			error = -1;
			break;
		}

		insert_fn(vm, range);
		last_insert = src_range;

		if (process_copy_user_pte_args_init_body_result(copy_args,
				new_vm_offset, new_vrflag_offset,
				range_offset, fault_addr_offset,
				vm, range->flag, range, -1) < 0) {
			error = -1;
			break;
		}

		error = visit_fn(orgvm->address_space->page_table,
				range->start, range->end, range->pgshift,
				visit_flags, copy_pte_fn, copy_args);
		if (error) {
			long fault_addr = *(long *)((char *)copy_args +
						   fault_addr_offset);

			if (fault_addr != -1 && log_fn)
				log_fn(orgvm, range, fault_addr);
			error = -1;
			break;
		}
	}

	if (error && last_insert) {
		src_range = lookup_fn(orgvm, 0, NOPHYS);
		while (src_range) {
			if (!(src_range->flag & VR_DONTFORK)) {
				struct vm_range *dest_range;

				dest_range = lookup_fn(vm, src_range->start,
						       src_range->end);
				if (dest_range)
					process_memory_range_free_result(
						vm, dest_range, free_range_fn);
				if (src_range == last_insert)
					break;
			}
			src_range = next_fn(orgvm, src_range);
		}
	}

	process_noirq_unlock_result((unsigned long)&orgvm->memory_range_lock,
				    read_unlock_fn);
	return error ? -1 : 0;
}

void *process_sigcommon_alloc_init_body_result(
	unsigned long sigcommon_size, unsigned long flags,
	unsigned long use_offset, unsigned long lock_offset,
	unsigned long sigpending_offset, process_alloc_fn_t alloc_fn,
	process_free_fn_t free_fn, process_ref_set_fn_t ref_set_fn,
	process_rwlock_init_fn_t rwlock_init_fn)
{
	void *sigcommon;

	if (!alloc_fn || !free_fn || !rwlock_init_fn)
		return NULL;

	sigcommon = process_alloc_result(sigcommon_size, flags, alloc_fn);
	if (!sigcommon)
		return NULL;

	memset(sigcommon, 0, sigcommon_size);
	if (process_ref_set_result(sigcommon, use_offset, 1, ref_set_fn)) {
		process_free_callback_result(sigcommon, free_fn);
		return NULL;
	}
	rwlock_init_fn((unsigned long)((char *)sigcommon + lock_offset));
	INIT_LIST_HEAD((struct list_head *)((char *)sigcommon +
					    sigpending_offset));
	return sigcommon;
}

int process_thread_sigpending_init_body_result(
	void *thread, unsigned long lock_offset, unsigned long sigpending_offset,
	process_rwlock_init_fn_t rwlock_init_fn)
{
	if (!thread || !rwlock_init_fn)
		return -EINVAL;

	rwlock_init_fn((unsigned long)((char *)thread + lock_offset));
	INIT_LIST_HEAD((struct list_head *)((char *)thread +
					    sigpending_offset));
	return 0;
}

int process_thread_alloc_init_body_result(
	void *thread, unsigned long thread_size, unsigned long refcount_offset,
	unsigned long hash_list_offset, unsigned long siblings_list_offset,
	process_ref_set_fn_t ref_set_fn)
{
	if (!thread)
		return -EINVAL;

	memset(thread, 0, thread_size);
	if (process_ref_set_result(thread, refcount_offset, 2, ref_set_fn))
		return -EINVAL;
	INIT_LIST_HEAD((struct list_head *)((char *)thread + hash_list_offset));
	INIT_LIST_HEAD((struct list_head *)((char *)thread +
					    siblings_list_offset));
	return 0;
}

int process_thread_sigstack_disable_body_result(
	void *thread, unsigned long sigstack_offset, unsigned long sp_offset,
	unsigned long flags_offset, unsigned long size_offset, int disable_flag)
{
	char *sigstack;

	if (!thread)
		return -EINVAL;

	sigstack = (char *)thread + sigstack_offset;
	*(void **)(sigstack + sp_offset) = NULL;
	*(int *)(sigstack + flags_offset) = disable_flag;
	*(size_t *)(sigstack + size_offset) = 0;
	return 0;
}

void *process_create_thread_body_result(
	unsigned long user_pc, unsigned long requested_cpu_set_addr,
	unsigned long requested_bits, unsigned long thread_pages,
	unsigned long thread_size, unsigned long process_size,
	unsigned long vm_size, unsigned long nowait_flag,
	unsigned long kernel_stack_bytes, int cpu_set_bits, int num_processors,
	int sched_normal, int ss_disable, int current_cpu,
	void *parent_process, unsigned long process_pid_offset,
	unsigned long thread_refcount_offset,
	unsigned long thread_hash_list_offset,
	unsigned long thread_siblings_list_offset,
	unsigned long thread_cpu_set_offset,
	unsigned long thread_sched_policy_offset,
	unsigned long thread_sigcommon_offset,
	unsigned long thread_sigpendinglock_offset,
	unsigned long thread_sigpending_offset,
	unsigned long thread_sigstack_offset,
	unsigned long sigstack_sp_offset,
	unsigned long sigstack_flags_offset,
	unsigned long sigstack_size_offset,
	unsigned long thread_vm_offset, unsigned long thread_proc_offset,
	unsigned long process_cpu_set_offset,
	unsigned long process_vm_offset,
	unsigned long process_main_thread_offset,
	unsigned long vm_address_space_offset,
	unsigned long address_space_cpu_set_offset,
	unsigned long address_space_cpu_set_lock_offset,
	unsigned long thread_exit_status_offset,
	unsigned long thread_spin_sleep_lock_offset,
	unsigned long thread_spin_sleep_offset,
	unsigned long sigcommon_size,
	unsigned long sigcommon_use_offset,
	unsigned long sigcommon_lock_offset,
	unsigned long sigcommon_sigpending_offset,
	process_alloc_pages_fn_t alloc_pages_fn,
	process_alloc_fn_t alloc_fn,
	process_free_fn_t free_fn,
	process_create_address_space_fn_t create_address_space_fn,
	process_release_address_space_fn_t release_address_space_fn,
	process_init_process_fn_t init_process_fn,
	process_init_process_vm_fn_t init_process_vm_fn,
	process_init_user_process_fn_t init_user_process_fn,
	process_default_ncpus_fn_t default_ncpus_fn,
	process_create_cpu_log_fn_t cpu_log_fn,
	process_rwlock_init_fn_t rwlock_init_fn,
	process_spin_init_fn_t spin_init_fn,
	process_spin_lock_fn_t spin_lock_fn,
	process_spin_unlock_fn_t spin_unlock_fn,
	process_thread_action_fn_t free_thread_fn)
{
	void *thread;
	void *proc = NULL;
	void *vm = NULL;
	void *asp = NULL;
	void *sigcommon = NULL;
	char *thread_base;
	char *proc_base;
	char *asp_base;
	int pid;

	if (!alloc_pages_fn || !alloc_fn || !free_fn ||
	    !create_address_space_fn || !release_address_space_fn ||
	    !init_process_fn || !init_process_vm_fn || !init_user_process_fn ||
	    !rwlock_init_fn || !spin_init_fn || !spin_lock_fn ||
	    !spin_unlock_fn || !free_thread_fn)
		return NULL;

	thread = alloc_pages_fn((int)thread_pages, nowait_flag);
	if (!thread)
		return NULL;

	if (process_thread_alloc_init_body_result(thread, thread_size,
			thread_refcount_offset, thread_hash_list_offset,
			thread_siblings_list_offset, NULL) < 0)
		goto err_thread;

	proc = process_alloc_result(process_size, nowait_flag, alloc_fn);
	vm = process_alloc_result(vm_size, nowait_flag, alloc_fn);
	asp = create_address_space_fn(1);
	if (!proc || !vm || !asp)
		goto err;

	if (process_allocated_object_zero_body_result(proc, process_size) < 0)
		goto err;
	if (process_allocated_object_zero_body_result(vm, vm_size) < 0)
		goto err;
	if (init_process_fn(proc, parent_process) < 0)
		goto err;

	proc_base = proc;
	pid = *(int *)(proc_base + process_pid_offset);
	thread_base = thread;
	if (process_create_cpu_sets_body_result(requested_cpu_set_addr,
			requested_bits, (unsigned long)(thread_base +
				thread_cpu_set_offset),
			(unsigned long)(proc_base + process_cpu_set_offset),
			cpu_set_bits, num_processors, pid,
			default_ncpus_fn, cpu_log_fn) < 0)
		goto err;

	if (process_thread_sched_default_body_result(thread,
			thread_sched_policy_offset, sched_normal) < 0)
		goto err;

	sigcommon = process_sigcommon_alloc_init_body_result(
			sigcommon_size, nowait_flag, sigcommon_use_offset,
			sigcommon_lock_offset, sigcommon_sigpending_offset,
			alloc_fn, free_fn, NULL, rwlock_init_fn);
	*(void **)(thread_base + thread_sigcommon_offset) = sigcommon;
	if (!sigcommon)
		goto err;

	if (process_thread_sigpending_init_body_result(thread,
			thread_sigpendinglock_offset, thread_sigpending_offset,
			rwlock_init_fn) < 0)
		goto err;
	if (process_thread_sigstack_disable_body_result(thread,
			thread_sigstack_offset, sigstack_sp_offset,
			sigstack_flags_offset, sigstack_size_offset,
			ss_disable) < 0)
		goto err;

	init_user_process_fn(thread, (unsigned long)thread + kernel_stack_bytes,
			     user_pc, 0);

	if (process_create_thread_link_state_body_result(thread, proc, vm,
			thread_vm_offset, thread_proc_offset, process_vm_offset,
			process_main_thread_offset) < 0)
		goto err;

	if (init_process_vm_fn(proc, asp, vm) != 0)
		goto err;
	if (process_thread_exit_status_init_body_result(thread,
			thread_exit_status_offset, -1) < 0)
		goto err;

	asp_base = asp;
	process_cpu_set_update_body_result(
			(unsigned long)(asp_base + address_space_cpu_set_offset),
			(unsigned long)(asp_base +
				address_space_cpu_set_lock_offset),
			-1, current_cpu, num_processors, spin_lock_fn,
			spin_unlock_fn);

	if (process_thread_spin_sleep_init_body_result(thread,
			thread_spin_sleep_lock_offset, thread_spin_sleep_offset,
			spin_init_fn) < 0)
		goto err;

	(void)vm_address_space_offset;
	return thread;

err:
	if (proc)
		process_free_callback_result(proc, free_fn);
	if (vm)
		process_free_callback_result(vm, free_fn);
	if (asp)
		release_address_space_fn(asp);
	sigcommon = *(void **)((char *)thread + thread_sigcommon_offset);
	if (sigcommon)
		process_free_callback_result(sigcommon, free_fn);
err_thread:
	process_thread_action_result(thread, free_thread_fn);
	return NULL;
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

int process_mckfd_dup_result(struct mckfd *fdp,
			     process_mckfd_dup_fn_t dup_fn)
{
	if (!dup_fn)
		return 0;

	return dup_fn(fdp, NULL);
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

int process_sigpending_drain_free_result(struct list_head *head,
					 unsigned long list_offset,
					 process_free_fn_t free_fn)
{
	int freed = 0;
	void *pending;

	if (!head || !free_fn)
		return 0;

	while ((pending = process_sigpending_pop_front_result(head,
							     list_offset))) {
		process_free_callback_result(pending, free_fn);
		freed++;
	}

	return freed;
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

int process_ptrace_traceme_body_result(
	void *thread, void *proc, void *parent, void *pid1,
	const struct process_ptrace_traceme_offsets *offsets, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_alloc_debugreg_fn_t alloc_debugreg_fn,
	process_thread_action_fn_t clear_single_step_fn,
	process_thread_action_fn_t hold_thread_fn,
	process_ptrace_traceme_log_fn_t log_fn)
{
	char *thread_base = thread;
	char *proc_base = proc;
	char *parent_base = parent;
	int *ptrace_slot;
	void *main_thread;
	void *report_proc;
	void *debugreg;
	int pid;
	int error = 0;

	if (!thread || !proc || !parent || !pid1 || !offsets)
		return -EFAULT;

	pid = *(int *)(proc_base + offsets->proc_pid_offset);
	if (log_fn)
		log_fn(PROCESS_PTRACE_TRACEME_LOG_ENTER, pid,
		       (unsigned long)parent, 0);

	ptrace_slot = (int *)(thread_base + offsets->thread_ptrace_offset);
	if (*ptrace_slot & PT_TRACED)
		return -EPERM;
	if (parent == pid1)
		return -EPERM;

	if (log_fn) {
		int parent_pid = *(int *)(parent_base + offsets->proc_pid_offset);

		log_fn(PROCESS_PTRACE_TRACEME_LOG_PARENT, parent_pid, 0, 0);
	}

	if (!lock_fn || !unlock_fn || !lock_node)
		return -EFAULT;

	main_thread =
		*(void **)(proc_base + offsets->proc_main_thread_offset);
	if (thread == main_thread) {
		unsigned long children_lock =
			(unsigned long)parent + offsets->proc_children_lock_offset;
		struct list_head *ptraced_sibling =
			(struct list_head *)(proc_base +
				offsets->proc_ptraced_siblings_list_offset);
		struct list_head *ptraced_children =
			(struct list_head *)(parent_base +
				offsets->proc_ptraced_children_list_offset);

		lock_fn(children_lock, lock_node);
		process_list_add_tail_result(ptraced_sibling, ptraced_children);
		unlock_fn(children_lock, lock_node);
	}

	report_proc = *(void **)(thread_base +
				 offsets->thread_report_proc_offset);
	if (!report_proc) {
		unsigned long threads_lock =
			(unsigned long)parent + offsets->proc_threads_lock_offset;
		struct list_head *report_sibling =
			(struct list_head *)(thread_base +
				offsets->thread_report_siblings_list_offset);
		struct list_head *report_threads =
			(struct list_head *)(parent_base +
				offsets->proc_report_threads_list_offset);

		lock_fn(threads_lock, lock_node);
		process_thread_report_attach_result(thread, 0, 0, 0,
			offsets->thread_report_proc_offset, parent,
			report_sibling, report_threads);
		unlock_fn(threads_lock, lock_node);
	}

	*ptrace_slot = PT_TRACED | PT_TRACE_EXEC;

	debugreg = *(void **)(thread_base +
			      offsets->thread_ptrace_debugreg_offset);
	if (!debugreg) {
		if (!alloc_debugreg_fn)
			return -EFAULT;
		error = alloc_debugreg_fn(thread);
	}

	if (!clear_single_step_fn || !hold_thread_fn)
		return -EFAULT;
	clear_single_step_fn(thread);
	hold_thread_fn(thread);

	if (log_fn)
		log_fn(PROCESS_PTRACE_TRACEME_LOG_RETURN, pid, 0, error);
	return error;
}

int process_ptrace_attach_thread_body_result(
	void *thread, void *proc,
	const struct process_ptrace_attach_offsets *offsets, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_alloc_debugreg_fn_t alloc_debugreg_fn,
	process_thread_action_fn_t clear_single_step_fn,
	process_thread_action_fn_t hold_thread_fn,
	process_ptrace_traceme_log_fn_t log_fn)
{
	char *thread_base = thread;
	char *proc_base = proc;
	void *old_report_proc;
	void *child;
	void *main_thread;
	void *debugreg;
	struct list_head *report_sibling;
	int error = 0;

	if (!thread || !proc || !offsets || !lock_node)
		return -EFAULT;
	if (!lock_fn || !unlock_fn)
		return -EFAULT;

	old_report_proc = *(void **)(thread_base +
				     offsets->thread_report_proc_offset);
	report_sibling = (struct list_head *)(thread_base +
		offsets->thread_report_siblings_list_offset);
	if (old_report_proc) {
		unsigned long old_threads_lock =
			(unsigned long)old_report_proc +
			offsets->proc_threads_lock_offset;

		lock_fn(old_threads_lock, lock_node);
		process_list_detach_result(report_sibling);
		unlock_fn(old_threads_lock, lock_node);
	}

	{
		unsigned long proc_threads_lock =
			(unsigned long)proc + offsets->proc_threads_lock_offset;
		struct list_head *report_threads =
			(struct list_head *)(proc_base +
				offsets->proc_report_threads_list_offset);

		lock_fn(proc_threads_lock, lock_node);
		process_thread_report_attach_result(thread, 0, 0, 0,
			offsets->thread_report_proc_offset, proc,
			report_sibling, report_threads);
		unlock_fn(proc_threads_lock, lock_node);
	}

	child = *(void **)(thread_base + offsets->thread_proc_offset);
	if (!child)
		return -EFAULT;
	main_thread = *(void **)((char *)child +
				 offsets->proc_main_thread_offset);
	if (thread == main_thread) {
		char *child_base = child;
		void *parent = *(void **)(child_base + offsets->proc_parent_offset);
		char *parent_base = parent;
		unsigned long parent_children_lock;
		unsigned long proc_children_lock;
		struct list_head *child_sibling;
		struct list_head *child_ptraced_sibling;
		struct list_head *parent_ptraced_children;
		struct list_head *proc_children;

		if (!parent)
			return -EFAULT;
		if (log_fn) {
			int parent_pid = *(int *)(parent_base +
						  offsets->proc_pid_offset);

			log_fn(PROCESS_PTRACE_TRACEME_LOG_PARENT, parent_pid,
			       0, 0);
		}
		parent_children_lock =
			(unsigned long)parent + offsets->proc_children_lock_offset;
		child_sibling = (struct list_head *)(child_base +
			offsets->proc_siblings_list_offset);
		child_ptraced_sibling = (struct list_head *)(child_base +
			offsets->proc_ptraced_siblings_list_offset);
		parent_ptraced_children = (struct list_head *)(parent_base +
			offsets->proc_ptraced_children_list_offset);
		lock_fn(parent_children_lock, lock_node);
		process_list_detach_result(child_sibling);
		process_list_add_tail_result(child_ptraced_sibling,
					     parent_ptraced_children);
		unlock_fn(parent_children_lock, lock_node);

		proc_children_lock =
			(unsigned long)proc + offsets->proc_children_lock_offset;
		proc_children = (struct list_head *)(proc_base +
			offsets->proc_children_list_offset);
		lock_fn(proc_children_lock, lock_node);
		process_ptrace_main_attach_reparent_result(child,
			offsets->proc_parent_offset, proc, child_sibling,
			proc_children);
		unlock_fn(proc_children_lock, lock_node);
	}

	debugreg = *(void **)(thread_base +
			      offsets->thread_ptrace_debugreg_offset);
	if (!debugreg) {
		if (!alloc_debugreg_fn)
			return -EFAULT;
		error = alloc_debugreg_fn(thread);
		if (error < 0)
			return error;
	}

	if (!hold_thread_fn || !clear_single_step_fn)
		return -EFAULT;
	hold_thread_fn(thread);
	clear_single_step_fn(thread);
	return error;
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

int process_mckfd_close_all_result(struct mckfd *head,
				   unsigned long next_offset,
				   unsigned long close_offset)
{
	struct mckfd *cur = head;
	int closed = 0;

	while (cur) {
		struct mckfd *next = *(struct mckfd **)
			((char *)cur + next_offset);
		int (**close_cb)(struct mckfd *, ihk_mc_user_context_t *) =
			(void *)((char *)cur + close_offset);

		if (*close_cb) {
			(*close_cb)(cur, NULL);
			closed++;
		}
		cur = next;
	}

	return closed;
}

int process_mckfd_free_result(struct mckfd *fdp,
			      process_mckfd_free_fn_t free_fn)
{
	if (!free_fn)
		return 0;

	free_fn(fdp);
	return 1;
}

int process_mckfd_drain_free_result(struct mckfd **headp,
				    unsigned long next_offset,
				    process_mckfd_free_fn_t free_fn)
{
	struct mckfd *cur;
	int freed = 0;

	if (!headp || !free_fn)
		return 0;

	cur = *headp;
	while (cur) {
		struct mckfd *next = *(struct mckfd **)
			((char *)cur + next_offset);

		*headp = next;
		*(struct mckfd **)((char *)cur + next_offset) = NULL;
		freed += process_mckfd_free_result(cur, free_fn);
		cur = next;
	}

	return freed;
}

int process_memory_range_free_result(struct process_vm *vm,
				     struct vm_range *range,
				     process_memory_range_free_fn_t free_fn)
{
	if (!vm || !range || !free_fn)
		return -EINVAL;

	return free_fn(vm, range);
}

int process_memory_range_log_result(struct process_vm *vm,
				    struct vm_range *range, int error,
				    process_memory_range_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(vm, range, error);
	return 0;
}

int process_memory_range_free_all_result(
	struct process_vm *vm, struct rb_root *root, unsigned long node_offset,
	process_memory_range_free_fn_t free_fn,
	process_memory_range_log_fn_t log_fn)
{
	struct rb_node *node;
	int visited = 0;

	if (!vm || !root || !free_fn)
		return 0;

	node = rb_first(root);
	while (node) {
		struct rb_node *next = rb_next(node);
		struct vm_range *range =
			(void *)((char *)node - node_offset);
		int error = process_memory_range_free_result(vm, range,
							     free_fn);

		if (error)
			process_memory_range_log_result(vm, range, error,
							log_fn);
		visited++;
		node = next;
	}

	return visited;
}

int process_flush_memory_body_result(
	struct process_vm *vm, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_memory_range_free_fn_t free_fn,
	process_memory_range_log_fn_t log_fn)
{
	struct rb_node *node;
	int error;
	int attempted = 0;

	if (!vm)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !free_fn)
		return -EINVAL;

	error = process_noirq_lock_result((unsigned long)&vm->memory_range_lock,
					  lock_fn);
	if (error)
		return error;
	vm->exiting = 1;

	node = rb_first(&vm->vm_range_tree);
	while (node) {
		struct rb_node *next = rb_next(node);
		struct vm_range *range = ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node)));

		if (range->memobj) {
			error = process_memory_range_free_result(vm, range,
								 free_fn);

			attempted++;
			if (error)
				process_memory_range_log_result(vm, range,
								error, log_fn);
		}
		node = next;
	}

	process_noirq_unlock_result((unsigned long)&vm->memory_range_lock,
				    unlock_fn);
	return attempted;
}

int process_free_all_memory_ranges_body_result(
	struct process_vm *vm, process_noirq_lock_fn_t lock_fn,
	process_noirq_unlock_fn_t unlock_fn,
	process_memory_range_free_fn_t free_fn,
	process_memory_range_log_fn_t log_fn)
{
	int visited;

	if (!vm || !lock_fn || !unlock_fn || !free_fn)
		return 0;

	visited = process_noirq_lock_result((unsigned long)&vm->memory_range_lock,
					    lock_fn);
	if (visited)
		return visited;
	visited = process_memory_range_free_all_result(vm, &vm->vm_range_tree,
						       0, free_fn, log_fn);
	process_noirq_unlock_result((unsigned long)&vm->memory_range_lock,
				    unlock_fn);
	return visited;
}

static int process_cpu_set_word(unsigned long cpu_set_addr, int cpu,
				int cpu_set_bits, unsigned long **wordp,
				unsigned long *maskp)
{
	int word_bits = sizeof(unsigned long) * 8;

	if (!cpu_set_addr || cpu < 0 || cpu_set_bits <= 0 ||
	    cpu >= cpu_set_bits)
		return 0;

	*wordp = ((unsigned long *)cpu_set_addr) + cpu / word_bits;
	*maskp = 1UL << (cpu % word_bits);
	return 1;
}

int process_cpu_set_update_body_result(
	unsigned long cpu_set_addr, unsigned long lock_addr, int clear_cpu,
	int set_cpu, int cpu_set_bits, process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn)
{
	unsigned long irqstate;
	unsigned long *word;
	unsigned long mask;
	int changed = 0;

	if (!cpu_set_addr || !lock_addr || !lock_fn || !unlock_fn)
		return -EINVAL;

	irqstate = process_spin_lock_result(lock_addr, lock_fn);
	if (process_cpu_set_word(cpu_set_addr, clear_cpu, cpu_set_bits,
				 &word, &mask)) {
		*word &= ~mask;
		changed++;
	}
	if (process_cpu_set_word(cpu_set_addr, set_cpu, cpu_set_bits,
				 &word, &mask)) {
		*word |= mask;
		changed++;
	}
	process_spin_unlock_result(lock_addr, irqstate, unlock_fn);
	return changed;
}

int process_cpu_set_public_result(
	int cpu, unsigned long cpu_set_addr, unsigned long lock_addr,
	int cpu_set_bits, process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn)
{
	return process_cpu_set_update_body_result(cpu_set_addr, lock_addr,
			-1, cpu, cpu_set_bits, lock_fn, unlock_fn);
}

int process_cpu_clear_public_result(
	int cpu, unsigned long cpu_set_addr, unsigned long lock_addr,
	int cpu_set_bits, process_spin_lock_fn_t lock_fn,
	process_spin_unlock_fn_t unlock_fn)
{
	return process_cpu_set_update_body_result(cpu_set_addr, lock_addr,
			cpu, -1, cpu_set_bits, lock_fn, unlock_fn);
}

int process_cpu_clear_and_set_public_result(
	int clear_cpu, int set_cpu, unsigned long cpu_set_addr,
	unsigned long lock_addr, int cpu_set_bits,
	process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn)
{
	return process_cpu_set_update_body_result(cpu_set_addr, lock_addr,
			clear_cpu, set_cpu, cpu_set_bits, lock_fn, unlock_fn);
}

int process_ref_inc_result(void *object, unsigned long ref_offset,
			   process_ref_inc_fn_t inc_fn)
{
	if (inc_fn) {
		inc_fn(object, ref_offset);
		return 0;
	}

	return process_ref_inc_direct_result(object, ref_offset);
}

int process_hold_thread_warn_result(void *thread,
				    process_hold_thread_warn_fn_t warn_fn)
{
	if (!warn_fn)
		return 0;

	warn_fn(thread);
	return 1;
}

int process_ref_hold_body_result(void *object, unsigned long ref_offset,
				 process_ref_inc_fn_t inc_fn)
{
	int rc;

	if (!object)
		return -EINVAL;

	rc = process_ref_inc_result(object, ref_offset, inc_fn);
	if (rc)
		return rc;
	return 1;
}

int process_hold_thread_body_result(
	void *thread, unsigned long status_offset, unsigned long refcount_offset,
	process_ref_inc_fn_t inc_fn, process_hold_thread_warn_fn_t warn_fn)
{
	int status;

	if (!thread)
		return -EINVAL;

	status = *(int *)((char *)thread + status_offset);
	if (process_hold_thread_warn_exited_result(status))
		process_hold_thread_warn_result(thread, warn_fn);

	return process_ref_hold_body_result(thread, refcount_offset, inc_fn);
}

void *process_current_resource_set_result(
	process_current_resource_set_fn_t current_resource_set_fn)
{
	if (!current_resource_set_fn)
		return NULL;

	return current_resource_set_fn();
}

int process_resource_process_action_result(
	void *resource_set, void *process,
	process_resource_process_action_fn_t action_fn)
{
	if (!action_fn)
		return -EINVAL;

	action_fn(resource_set, process);
	return 0;
}

int process_process_action_result(void *process,
				  process_process_action_fn_t action_fn)
{
	if (!action_fn)
		return -EINVAL;

	action_fn(process);
	return 0;
}

int process_resource_set_action_result(
	void *resource_set, process_resource_set_action_fn_t action_fn)
{
	if (!action_fn)
		return -EINVAL;

	action_fn(resource_set);
	return 0;
}

int process_thread_action_result(void *thread,
				 process_thread_action_fn_t action_fn)
{
	if (!action_fn)
		return -EINVAL;

	action_fn(thread);
	return 0;
}

int process_thread_profile_result(void *thread, void *process,
				  process_thread_profile_fn_t profile_fn)
{
	if (!profile_fn)
		return 0;

	profile_fn(thread, process);
	return 0;
}

int process_vm_action_result(void *vm, process_vm_action_fn_t action_fn)
{
	if (!action_fn)
		return -EINVAL;

	action_fn(vm);
	return 0;
}

int process_policy_free_result(void *policy,
			       process_policy_free_fn_t policy_free_fn)
{
	if (!policy_free_fn)
		return -EINVAL;

	policy_free_fn(policy);
	return 0;
}

int process_vm_free_cb_result(void *vm, void *opt,
			      process_vm_free_cb_fn_t free_cb)
{
	if (!free_cb)
		return 0;

	free_cb(vm, opt);
	return 0;
}

unsigned long process_spin_lock_result(unsigned long lock_addr,
				       process_spin_lock_fn_t lock_fn)
{
	if (!lock_fn)
		return 0;

	return lock_fn(lock_addr);
}

int process_spin_unlock_result(unsigned long lock_addr,
			       unsigned long irqstate,
			       process_spin_unlock_fn_t unlock_fn)
{
	if (!unlock_fn)
		return -EINVAL;

	unlock_fn(lock_addr, irqstate);
	return 0;
}

int process_release_process_body_result(
	void *proc, unsigned long refcount_offset, unsigned long tids_offset,
	unsigned long main_thread_offset, unsigned long mckfd_offset,
	unsigned long mckfd_lock_offset, unsigned long mckfd_next_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_current_resource_set_fn_t current_resource_set_fn,
	process_resource_process_action_fn_t hash_detach_fn,
	process_process_action_fn_t sibling_detach_fn,
	process_process_action_fn_t profile_fn,
	process_thread_action_fn_t free_thread_pages_fn,
	process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
	process_mckfd_free_fn_t mckfd_free_fn, process_free_fn_t free_fn,
	process_resource_set_action_fn_t final_cleanup_fn)
{
	void *resource_set;
	void *tids;
	void *main_thread;
	unsigned long lock_addr;
	unsigned long irqstate;
	struct mckfd **mckfd_headp;

	if (!proc || !current_resource_set_fn || !hash_detach_fn ||
	    !sibling_detach_fn || !free_thread_pages_fn || !lock_fn ||
	    !unlock_fn || !mckfd_free_fn || !free_fn || !final_cleanup_fn)
		return -EINVAL;

	if (!process_ref_release_should_destroy_result(
		    process_ref_dec_and_test_result(proc, refcount_offset,
						    dec_fn)))
		return 0;

	resource_set = process_current_resource_set_result(
		current_resource_set_fn);
	process_resource_process_action_result(resource_set, proc,
					       hash_detach_fn);
	process_process_action_result(proc, sibling_detach_fn);

	tids = *(void **)((char *)proc + tids_offset);
	if (tids)
		process_free_callback_result(tids, free_fn);

	if (profile_fn)
		process_process_action_result(proc, profile_fn);

	main_thread = *(void **)((char *)proc + main_thread_offset);
	if (main_thread)
		process_thread_action_result(main_thread,
					     free_thread_pages_fn);

	lock_addr = (unsigned long)((char *)proc + mckfd_lock_offset);
	irqstate = process_spin_lock_result(lock_addr, lock_fn);
	mckfd_headp = (struct mckfd **)((char *)proc + mckfd_offset);
	process_mckfd_drain_free_result(mckfd_headp, mckfd_next_offset,
					mckfd_free_fn);
	process_spin_unlock_result(lock_addr, irqstate, unlock_fn);

	process_free_callback_result(proc, free_fn);
	process_resource_set_action_result(resource_set, final_cleanup_fn);
	return 1;
}

int process_vm_policy_drain_free_result(struct rb_root *root,
					unsigned long node_offset,
					process_policy_free_fn_t free_fn)
{
	struct rb_node *node;
	int freed = 0;

	if (!root || !free_fn)
		return 0;

	while ((node = rb_first(root))) {
		void *policy = (char *)node - node_offset;

		rb_erase(node, root);
		process_policy_free_result(policy, free_fn);
		freed++;
	}

	return freed;
}

int process_detach_address_space_pid_result(
	void *address_space, int pid, process_detach_address_space_fn_t detach_fn)
{
	if (!detach_fn)
		return -EINVAL;

	detach_fn(address_space, pid);
	return 0;
}

int process_release_process_action_result(
	void *process, process_release_process_fn_t release_fn)
{
	if (!release_fn)
		return -EINVAL;

	release_fn(process);
	return 0;
}

int process_release_vm_detach_process_result(
	struct process_vm *vm, unsigned long address_space_offset,
	unsigned long proc_offset, unsigned long pid_offset,
	unsigned long proc_vm_offset,
	process_detach_address_space_fn_t detach_fn,
	process_release_process_fn_t release_fn)
{
	char *vm_base;
	void *address_space;
	void *proc;
	char *proc_base;
	int pid;

	if (!vm || !detach_fn || !release_fn)
		return 0;

	vm_base = (char *)vm;
	address_space = *(void **)(vm_base + address_space_offset);
	proc = *(void **)(vm_base + proc_offset);
	if (!proc)
		return 0;

	proc_base = (char *)proc;
	pid = *(int *)(proc_base + pid_offset);
	process_detach_address_space_pid_result(address_space, pid, detach_fn);
	*(void **)(proc_base + proc_vm_offset) = NULL;
	process_release_process_action_result(proc, release_fn);
	return 1;
}

int process_release_fp_regs_result(struct thread *thread,
				   process_release_fp_regs_fn_t release_fp_fn)
{
	if (!release_fp_fn)
		return 0;

	release_fp_fn(thread);
	return 1;
}

int process_destroy_thread_optional_cleanup_result(
	struct thread *thread, unsigned long debugreg_offset,
	unsigned long recvsig_offset, unsigned long sendsig_offset,
	unsigned long fp_regs_offset, unsigned long coredump_regs_offset,
	process_optional_free_fn_t free_fn,
	process_release_fp_regs_fn_t release_fp_fn)
{
	unsigned long offsets[3] = {
		debugreg_offset, recvsig_offset, sendsig_offset
	};
	char *base = (char *)thread;
	int actions = 0;
	int i;
	void *fp_regs;
	void *coredump_regs;

	if (!thread || !free_fn)
		return 0;

	for (i = 0; i < 3; i++) {
		void *ptr = *(void **)(base + offsets[i]);

		if (ptr) {
			process_free_callback_result(ptr, free_fn);
			actions++;
		}
	}

	fp_regs = *(void **)(base + fp_regs_offset);
	if (fp_regs)
		actions += process_release_fp_regs_result(thread,
							  release_fp_fn);

	coredump_regs = *(void **)(base + coredump_regs_offset);
	process_free_callback_result(coredump_regs, free_fn);
	return actions + 1;
}

int process_release_sigcommon_body_result(
	void *sigcommon, int dec_and_test, int sigpending_empty,
	unsigned long sigpending_offset, unsigned long pending_list_offset,
	process_free_fn_t free_fn)
{
	struct list_head *head;
	void *pending;

	if (!sigcommon || !free_fn)
		return -EINVAL;
	if (!process_sigcommon_release_should_destroy_result(dec_and_test))
		return 0;

	if (process_sigpending_cleanup_needed_result(sigpending_empty)) {
		head = (struct list_head *)((char *)sigcommon +
					    sigpending_offset);
		while ((pending = process_sigpending_pop_front_result(
				head, pending_list_offset))) {
			process_free_callback_result(pending, free_fn);
		}
	}

	process_free_callback_result(sigcommon, free_fn);
	return 1;
}

int process_release_sigcommon_public_body_result(
	void *sigcommon, unsigned long use_offset,
	unsigned long sigpending_offset, unsigned long pending_list_offset,
	process_ref_dec_and_test_fn_t dec_fn, process_free_fn_t free_fn)
{
	struct list_head *head;
	int sigpending_empty;

	if (!sigcommon)
		return -EINVAL;

	head = (struct list_head *)((char *)sigcommon + sigpending_offset);
	sigpending_empty = head->next == head;
	return process_release_sigcommon_body_result(
		sigcommon,
		process_ref_dec_and_test_result(sigcommon, use_offset, dec_fn),
		sigpending_empty,
		sigpending_offset, pending_list_offset, free_fn);
}

int process_release_tid_body_result(
	void *tids, int nr_tids, unsigned long tid_stride,
	unsigned long tid_thread_offset, void *thread, int thread_tid,
	process_tid_log_fn_t log_fn)
{
	int index;

	if (!tids || !thread)
		return 0;

	index = process_tid_index_for_thread_result(tids, nr_tids, tid_stride,
						    tid_thread_offset,
						    (unsigned long)thread);
	if (!process_tid_index_found_result(index))
		return 0;
	if (!process_tid_release_slot_result(tids, index, tid_stride,
					     tid_thread_offset))
		return 0;

	process_tid_log_result(thread_tid, thread, 0, log_fn);
	return 1;
}

int process_tid_log_result(int old_tid, void *thread, int new_tid,
			   process_tid_log_fn_t log_fn)
{
	if (!log_fn)
		return 0;

	log_fn(old_tid, thread, new_tid);
	return 1;
}

int process_replace_tid_body_result(
	void *tids, int nr_tids, unsigned long tid_stride,
	unsigned long tid_offset, unsigned long tid_thread_offset,
	void *thread, int old_tid, int new_tid, process_tid_log_fn_t log_fn)
{
	int index;

	if (!tids || !thread)
		return 0;

	index = process_tid_index_for_thread_result(tids, nr_tids, tid_stride,
						    tid_thread_offset,
						    (unsigned long)thread);
	if (!process_tid_index_found_result(index))
		return 0;
	if (!process_tid_replace_slot_result(tids, index, tid_stride,
					     tid_offset, tid_thread_offset,
					     new_tid))
		return 0;

	process_tid_log_result(old_tid, thread, new_tid, log_fn);
	return 1;
}

int process_chain_process_body_result(
	struct list_head *siblings_entry, struct list_head *children_head,
	unsigned long children_lock_addr, struct list_head *hash_entry,
	struct list_head *hash_head, unsigned long hash_lock_addr,
	void *lock_node, process_mcs_rwlock_fn_t lock_fn,
	process_mcs_rwlock_fn_t unlock_fn)
{
	if (!siblings_entry || !children_head || !hash_entry || !hash_head ||
	    !lock_node || !lock_fn || !unlock_fn)
		return -EINVAL;

	lock_fn(children_lock_addr, lock_node);
	process_list_add_tail_result(siblings_entry, children_head);
	unlock_fn(children_lock_addr, lock_node);

	lock_fn(hash_lock_addr, lock_node);
	process_list_add_tail_result(hash_entry, hash_head);
	unlock_fn(hash_lock_addr, lock_node);
	return 1;
}

int process_chain_thread_body_result(
	struct list_head *siblings_entry, struct list_head *threads_head,
	unsigned long threads_lock_addr, struct list_head *hash_entry,
	struct list_head *hash_head, unsigned long hash_lock_addr, void *vm,
	unsigned long vm_refcount_offset, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_ref_inc_fn_t ref_inc_fn)
{
	int rc;

	rc = process_chain_process_body_result(siblings_entry, threads_head,
		threads_lock_addr, hash_entry, hash_head, hash_lock_addr,
		lock_node, lock_fn, unlock_fn);
	if (rc < 0)
		return rc;
	return process_ref_inc_result(vm, vm_refcount_offset, ref_inc_fn);
}

int process_destroy_thread_body_result(
	void *thread, unsigned long thread_proc_offset,
	unsigned long thread_vm_offset, unsigned long thread_cpu_id_offset,
	unsigned long thread_siblings_list_offset,
	unsigned long thread_uti_state_offset,
	unsigned long thread_uti_refill_tid_offset,
	unsigned long thread_sigpending_offset,
	unsigned long thread_sigcommon_offset,
	unsigned long proc_threads_lock_offset, unsigned long proc_tids_offset,
	unsigned long proc_main_thread_offset,
	unsigned long vm_address_space_offset,
	unsigned long address_space_cpu_set_offset,
	unsigned long address_space_cpu_set_lock_offset,
	unsigned long pending_list_offset,
	unsigned long debugreg_offset, unsigned long recvsig_offset,
	unsigned long sendsig_offset, unsigned long fp_regs_offset,
	unsigned long coredump_regs_offset, int cpu_set_bits, void *lock_node,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_thread_action_fn_t hash_detach_fn,
	process_thread_action_fn_t time_account_fn,
	process_thread_proc_action_fn_t release_tid_fn,
	process_thread_tid_action_fn_t replace_tid_fn,
	process_spin_lock_fn_t cpu_lock_fn,
	process_spin_unlock_fn_t cpu_unlock_fn,
	process_optional_free_fn_t free_fn,
	process_release_fp_regs_fn_t release_fp_fn,
	process_thread_action_fn_t release_sigcommon_fn,
	process_thread_action_fn_t free_thread_pages_fn)
{
	char *thread_base = thread;
	void *proc;
	void *vm;
	void *address_space;
	struct list_head *sigpending;
	struct list_head *siblings;
	unsigned long threads_lock_addr;
	int uti_state;
	int action;
	int sigpending_empty;

	if (!thread || !lock_node || !lock_fn || !unlock_fn ||
	    !hash_detach_fn || !time_account_fn || !release_tid_fn ||
	    !replace_tid_fn || !cpu_lock_fn || !cpu_unlock_fn || !free_fn ||
	    !release_sigcommon_fn || !free_thread_pages_fn)
		return -EINVAL;

	hash_detach_fn(thread);
	time_account_fn(thread);

	proc = *(void **)(thread_base + thread_proc_offset);
	if (!proc)
		return -EINVAL;

	threads_lock_addr = (unsigned long)proc + proc_threads_lock_offset;
	lock_fn(threads_lock_addr, lock_node);

	siblings = (struct list_head *)(thread_base +
					thread_siblings_list_offset);
	process_list_detach_result(siblings);

	uti_state = *(int *)(thread_base + thread_uti_state_offset);
	action = process_destroy_thread_tid_action_result(
		*(void **)((char *)proc + proc_tids_offset) != NULL,
		thread == *(void **)((char *)proc + proc_main_thread_offset),
		uti_state);
	switch (action) {
	case 2:
		replace_tid_fn(proc, thread,
			       *(int *)(thread_base + thread_uti_refill_tid_offset));
		break;
	case 1:
		release_tid_fn(proc, thread);
		break;
	default:
		break;
	}

	vm = *(void **)(thread_base + thread_vm_offset);
	if (vm) {
		address_space = *(void **)((char *)vm + vm_address_space_offset);
		if (address_space) {
			process_cpu_set_update_body_result(
				(unsigned long)address_space +
					address_space_cpu_set_offset,
				(unsigned long)address_space +
					address_space_cpu_set_lock_offset,
				*(int *)(thread_base + thread_cpu_id_offset),
				-1, cpu_set_bits, cpu_lock_fn, cpu_unlock_fn);
		}
	}

	sigpending = (struct list_head *)(thread_base + thread_sigpending_offset);
	sigpending_empty = sigpending->next && sigpending->next == sigpending;
	if (process_sigpending_cleanup_needed_result(sigpending_empty))
		process_sigpending_drain_free_result(sigpending,
			pending_list_offset, free_fn);

	process_destroy_thread_optional_cleanup_result(thread,
		debugreg_offset, recvsig_offset, sendsig_offset, fp_regs_offset,
		coredump_regs_offset, free_fn, release_fp_fn);
	release_sigcommon_fn(*(void **)(thread_base + thread_sigcommon_offset));

	if (process_thread_should_free_pages_result(
		    thread == *(void **)((char *)proc + proc_main_thread_offset)))
		free_thread_pages_fn(thread);

	unlock_fn(threads_lock_addr, lock_node);
	return 1;
}

static void *process_container_from_list(struct list_head *entry,
					 unsigned long list_offset)
{
	return (char *)entry - list_offset;
}

void *process_find_thread_body_result(
	struct list_head *hash_head, unsigned long hash_lock_addr, void *lock_node,
	int pid, int tid, const struct process_find_thread_offsets *offsets,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
	process_thread_action_fn_t hold_fn)
{
	struct list_head *entry;
	int match_pid = pid;

	if (tid <= 0 || !hash_head || !lock_node || !offsets || !lock_fn ||
	    !unlock_fn || !hold_fn)
		return NULL;

	lock_fn(hash_lock_addr, lock_node);
retry:
	for (entry = hash_head->next; entry && entry != hash_head;
	     entry = entry->next) {
		void *thread = process_container_from_list(
			entry, offsets->thread_hash_list_offset);
		char *thread_base = thread;
		int thread_tid = *(int *)(thread_base +
					  offsets->thread_tid_offset);

		if (thread_tid == tid) {
			void *proc = *(void **)(thread_base +
						offsets->thread_proc_offset);
			int proc_pid = proc ?
				*(int *)((char *)proc + offsets->proc_pid_offset) :
				0;

			if (match_pid <= 0 || proc_pid == match_pid) {
				hold_fn(thread);
				unlock_fn(hash_lock_addr, lock_node);
				return thread;
			}
		}
	}
	if (match_pid > 0 && match_pid == tid) {
		match_pid = 0;
		goto retry;
	}

	unlock_fn(hash_lock_addr, lock_node);
	return NULL;
}

void *process_find_process_body_result(
	struct list_head *hash_head, unsigned long hash_lock_addr, void *lock_node,
	int pid, const struct process_find_process_offsets *offsets,
	process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn)
{
	struct list_head *entry;

	if (pid <= 0 || !hash_head || !lock_node || !offsets || !lock_fn ||
	    !unlock_fn)
		return NULL;

	lock_fn(hash_lock_addr, lock_node);
	for (entry = hash_head->next; entry && entry != hash_head;
	     entry = entry->next) {
		void *proc = process_container_from_list(
			entry, offsets->process_hash_list_offset);
		int proc_pid = *(int *)((char *)proc + offsets->process_pid_offset);

		if (proc_pid == pid)
			return proc;
	}

	unlock_fn(hash_lock_addr, lock_node);
	return NULL;
}

int process_unlock_found_process_result(
	void *process, unsigned long hash_lock_addr, void *lock_node,
	process_mcs_rwlock_fn_t unlock_fn)
{
	if (!process)
		return 0;
	if (!unlock_fn)
		return -EINVAL;
	unlock_fn(hash_lock_addr, lock_node);
	return 1;
}

int process_release_thread_body_result(
	void *thread, unsigned long refcount_offset, unsigned long vm_offset,
	unsigned long proc_offset, process_ref_dec_and_test_fn_t dec_fn,
	process_thread_profile_fn_t profile_fn,
	process_thread_action_fn_t procfs_delete_fn,
	process_thread_action_fn_t destroy_thread_fn,
	process_vm_action_fn_t release_vm_fn)
{
	void *vm;
	void *proc;

	if (!thread || !procfs_delete_fn || !destroy_thread_fn ||
	    !release_vm_fn)
		return -EINVAL;
	if (!process_ref_release_should_destroy_result(
		    process_ref_dec_and_test_result(thread, refcount_offset,
						    dec_fn)))
		return 0;

	vm = *(void **)((char *)thread + vm_offset);
	proc = *(void **)((char *)thread + proc_offset);
	process_thread_profile_result(thread, proc, profile_fn);
	process_thread_action_result(thread, procfs_delete_fn);
	process_thread_action_result(thread, destroy_thread_fn);
	process_vm_action_result(vm, release_vm_fn);
	return 1;
}

int process_release_vm_body_result(
	void *vm, unsigned long refcount_offset, unsigned long proc_offset,
	unsigned long proc_mckfd_offset, unsigned long proc_mckfd_lock_offset,
	unsigned long mckfd_next_offset, unsigned long mckfd_close_offset,
	unsigned long vm_free_cb_offset, unsigned long vm_opt_offset,
	unsigned long vm_address_space_offset, unsigned long proc_pid_offset,
	unsigned long proc_vm_offset, unsigned long vm_policy_tree_offset,
	unsigned long policy_node_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
	process_vm_action_fn_t flush_fn, process_vm_action_fn_t free_ranges_fn,
	process_detach_address_space_fn_t detach_fn,
	process_release_process_fn_t release_process_fn,
	process_policy_free_fn_t policy_free_fn, process_free_fn_t free_vm_fn)
{
	process_vm_free_cb_fn_t free_cb;
	unsigned long lock_addr;
	unsigned long irqstate;
	void *proc;
	void *mckfd_head;
	void *opt;
	struct rb_root *policy_root;

	if (!vm || !lock_fn || !unlock_fn || !flush_fn ||
	    !free_ranges_fn || !free_vm_fn)
		return -EINVAL;
	if (!process_ref_release_should_destroy_result(
		    process_ref_dec_and_test_result(vm, refcount_offset,
						    dec_fn)))
		return 0;

	proc = *(void **)((char *)vm + proc_offset);
	if (!proc)
		return -EINVAL;

	lock_addr = (unsigned long)proc + proc_mckfd_lock_offset;
	irqstate = process_spin_lock_result(lock_addr, lock_fn);
	mckfd_head = *(void **)((char *)proc + proc_mckfd_offset);
	process_mckfd_close_all_result(mckfd_head, mckfd_next_offset,
				       mckfd_close_offset);
	process_spin_unlock_result(lock_addr, irqstate, unlock_fn);

	free_cb = *(process_vm_free_cb_fn_t *)((char *)vm + vm_free_cb_offset);
	if (process_release_vm_should_run_free_cb_result((unsigned long)free_cb)) {
		opt = *(void **)((char *)vm + vm_opt_offset);
		process_vm_free_cb_result(vm, opt, free_cb);
	}

	process_vm_action_result(vm, flush_fn);
	process_vm_action_result(vm, free_ranges_fn);
	process_release_vm_detach_process_result(vm, vm_address_space_offset,
		proc_offset, proc_pid_offset, proc_vm_offset, detach_fn,
		release_process_fn);
	policy_root = (struct rb_root *)((char *)vm + vm_policy_tree_offset);
	process_vm_policy_drain_free_result(policy_root, policy_node_offset,
					    policy_free_fn);
	process_free_callback_result(vm, free_vm_fn);
	return 1;
}

#endif /* MCKERNEL_RUST_PROCESS_HELPERS */
