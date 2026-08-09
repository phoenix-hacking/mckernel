/* process.c COPYRIGHT FUJITSU LIMITED 2015-2019 */
/**
 * \file process.c
 *  License details are found in the file LICENSE.
 * \brief
 *  process, thread, and, virtual memory management
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * 	Copyright (C) 2012  RIKEN AICS
 * \author Masamichi Takagi  <m-takagi@ab.jp.nec.com> \par
 * 	Copyright (C) 2012 - 2013  NEC Corporation
 * \author Balazs Gerofi  <bgerofi@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2013  The University of Tokyo
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <process.h>
#include <process_helpers.h>
#include <sched_helpers.h>
#include <string.h>
#include <errno.h>
#include <kmalloc.h>
#include <cls.h>
#include <page.h>
#include <cpulocal.h>
#include <auxvec.h>
#include <hwcap.h>
#include <timer.h>
#include <mman.h>
#include <xpmem.h>
#include <shm.h>
#include <rusage_private.h>
#include <ihk/monitor.h>
#include <ihk/debug.h>
#ifdef ENABLE_TOFU
#include <tofu/tofu_stag_range.h>
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
#define PROCESS_SCHED_PUBLIC_BRIDGE
#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
#endif

//#define DEBUG_PRINT_PROCESS

#ifdef DEBUG_PRINT_PROCESS
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
static void dtree(struct rb_node *node, int l) {
	struct vm_range *range;
	if (!node)
		return;

	range = ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node)));

	dtree(node->rb_left, l+1);
	kprintf("dtree: %0*d, %p: %lx-%lx\n", l, 0, range, range->start, range->end);
	dtree(node->rb_right, l+1);
}
static void dump_tree(struct process_vm *vm) {
	kprintf("dump_tree %p\n", vm);
	dtree(vm->vm_range_tree.rb_node, 1);
}
#else
static void dump_tree(struct process_vm *vm) {}
#endif

extern struct thread *arch_switch_context(struct thread *prev, struct thread *next);
extern long alloc_debugreg(struct thread *proc);
extern void save_debugreg(unsigned long *debugreg);
extern void restore_debugreg(unsigned long *debugreg);
extern void clear_debugreg(void);
extern void clear_single_step(struct thread *proc);
static int vm_range_insert(struct process_vm *vm,
		struct vm_range *newrange);
static struct vm_range *vm_range_find(struct process_vm *vm,
		unsigned long addr);
static int copy_user_ranges(struct process_vm *vm, struct process_vm *orgvm);
extern void __runq_add_proc(struct thread *proc, int cpu_id);
extern void lapic_timer_enable(unsigned int clocks);
extern void lapic_timer_disable();

static const struct timer_runtime_offsets process_timer_runtime_offsets = {
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_sched_list_offset = __builtin_offsetof(struct thread, sched_list),
	.thread_spin_sleep_lock_offset =
		__builtin_offsetof(struct thread, spin_sleep_lock),
	.thread_spin_sleep_offset = __builtin_offsetof(struct thread, spin_sleep),
	.thread_itimer_enabled_offset =
		__builtin_offsetof(struct thread, itimer_enabled),
	.cpu_runq_lock_offset = __builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_offset = __builtin_offsetof(struct cpu_local_var, runq),
	.cpu_runq_len_offset = __builtin_offsetof(struct cpu_local_var, runq_len),
	.cpu_current_offset = __builtin_offsetof(struct cpu_local_var, current),
	.cpu_timer_enabled_offset =
		__builtin_offsetof(struct cpu_local_var, timer_enabled),
	.cpu_backlog_list_offset =
		__builtin_offsetof(struct cpu_local_var, backlog_list),
	.timer_timeout_offset = __builtin_offsetof(struct timer, timeout),
	.timer_waitq_offset = __builtin_offsetof(struct timer, processes),
	.timer_list_offset = __builtin_offsetof(struct timer, list),
	.timer_thread_offset = __builtin_offsetof(struct timer, thread),
};

static unsigned long process_timer_spin_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void process_timer_spin_unlock_bridge(unsigned long lock_addr,
					     unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqstate);
}

static void process_timer_lapic_enable_bridge(unsigned int clocks)
{
	lapic_timer_enable(clocks);
}

static void process_timer_lapic_disable_bridge(void)
{
	lapic_timer_disable();
}
extern int num_processors;
extern ihk_spinlock_t cpuid_head_lock;
int ptrace_detach(int pid, int data);
extern void procfs_create_thread(struct thread *);
extern void procfs_delete_thread(struct thread *);

static int free_process_memory_range(struct process_vm *vm,
					struct vm_range *range);
struct address_space *create_address_space(struct resource_set *res, int n);
void hold_address_space(struct address_space *asp);
void detach_address_space(struct address_space *asp, int pid);
int init_process_vm(struct process *owner, struct address_space *asp,
		    struct process_vm *vm);
struct resource_set *new_resource_set(void);
void proc_init(void);
static void free_thread_pages(struct thread *thread);
void process_free_thread_pages_bridge(void *thread);
int update_process_page_table(struct process_vm *vm,
			      struct vm_range *range, uint64_t phys,
			      enum ihk_mc_pt_attribute flag);
int split_process_memory_range(struct process_vm *vm, struct vm_range *range,
			       uintptr_t addr, struct vm_range **splitp);

void process_mckfd_free_bridge(struct mckfd *fdp)
{
	kfree_tracked(fdp, __FILE__, __LINE__);
}

void process_mcs_writer_lock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_lock((struct mcs_rwlock_lock *)lock_addr,
			       (struct mcs_rwlock_node_irqsave *)node);
}

void process_mcs_writer_unlock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_unlock((struct mcs_rwlock_lock *)lock_addr,
				 (struct mcs_rwlock_node_irqsave *)node);
}

void process_mcs_reader_lock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_reader_lock((struct mcs_rwlock_lock *)lock_addr,
			       (struct mcs_rwlock_node_irqsave *)node);
}

void process_mcs_reader_unlock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_reader_unlock((struct mcs_rwlock_lock *)lock_addr,
				 (struct mcs_rwlock_node_irqsave *)node);
}

void process_hold_thread_bridge(void *thread)
{
	hold_thread((struct thread *)thread);
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_ptrace_mcs_lock_noirq_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_lock_noirq((struct mcs_rwlock_lock *)lock_addr,
				     (struct mcs_rwlock_node *)node);
}

void process_ptrace_mcs_unlock_noirq_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_unlock_noirq((struct mcs_rwlock_lock *)lock_addr,
				       (struct mcs_rwlock_node *)node);
}

int process_ptrace_alloc_debugreg_bridge(void *thread)
{
	return alloc_debugreg((struct thread *)thread);
}

void process_ptrace_clear_single_step_bridge(void *thread)
{
	clear_single_step((struct thread *)thread);
}

void process_ptrace_hold_thread_bridge(void *thread)
{
	hold_thread((struct thread *)thread);
}

void process_ptrace_traceme_log_bridge(int event, int pid,
				       unsigned long value, int error)
{
	switch (event) {
	case PROCESS_PTRACE_TRACEME_LOG_ENTER:
		dkprintf("ptrace_traceme,pid=%d,proc->parent=%p\n",
			 pid, (void *)value);
		break;
	case PROCESS_PTRACE_TRACEME_LOG_PARENT:
		dkprintf("ptrace_traceme,parent->pid=%d\n", pid);
		break;
	case PROCESS_PTRACE_TRACEME_LOG_RETURN:
		dkprintf("ptrace_traceme,returning,error=%d\n", error);
		break;
	default:
		break;
	}
}
#endif

void process_policy_free_bridge(void *policy)
{
	kfree_tracked(policy, __FILE__, __LINE__);
}

void process_optional_free_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

int process_default_ncpus_bridge(void)
{
	struct ihk_mc_cpu_info *infop = ihk_mc_get_cpu_info();

	return infop ? infop->ncpus : -EINVAL;
}

void process_create_cpu_log_bridge(int event, int pid, int cpu)
{
	switch (event) {
	case PROCESS_CREATE_CPU_LOG_INVALID:
		kprintf("%s: invalid CPU requested in initial cpu_set\n",
			"create_thread");
		break;
	case PROCESS_CREATE_CPU_LOG_REQUESTED:
		dkprintf("%s: pid: %d, CPU: %d\n",
			"create_thread", pid, cpu);
		break;
	default:
		break;
	}
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_spin_init_bridge(unsigned long lock_addr);
void process_rwlock_init_bridge(unsigned long lock_addr);
void process_waitq_init_bridge(unsigned long waitq_addr);
#else
void process_spin_init_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock_addr);
}

void process_rwlock_init_bridge(unsigned long lock_addr)
{
	mcs_rwlock_init((mcs_rwlock_lock_t *)lock_addr);
}

void process_waitq_init_bridge(unsigned long waitq_addr)
{
	waitq_init((waitq_t *)waitq_addr);
}
#endif

static void process_user_context_modify_bridge(void *uctx, int reg,
					       unsigned long value)
{
	ihk_mc_modify_user_context(uctx, reg, value);
}

#ifdef PROFILE_ENABLE
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_mcs_lock_init_bridge(unsigned long lock_addr);
#else
void process_mcs_lock_init_bridge(unsigned long lock_addr)
{
	mcs_lock_init((mcs_lock_node_t *)lock_addr);
}
#endif
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_vm_rwspin_init_bridge(unsigned long lock_addr);
#else
void process_vm_rwspin_init_bridge(unsigned long lock_addr)
{
	ihk_rwspinlock_init((ihk_rwspinlock_t *)lock_addr);
}
#endif

void process_vm_init_numa_log_bridge(int numa_id)
{
	kprintf("%s: error: NUMA id is larger than mask size!\n",
		"init_process_vm");
	(void)numa_id;
}

void *process_alloc_bridge(unsigned long size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void *process_pt_create_bridge(unsigned long flags);
unsigned long process_spin_lock_bridge(unsigned long lock_addr);
void process_spin_unlock_bridge(unsigned long lock_addr,
				unsigned long irqstate);
void process_sched_noirq_lock_bridge(unsigned long lock_addr);
void process_sched_noirq_unlock_bridge(unsigned long lock_addr);
void process_rw_read_lock_bridge(unsigned long lock_addr);
void process_rw_read_unlock_bridge(unsigned long lock_addr);
void process_rw_write_lock_bridge(unsigned long lock_addr);
void process_rw_write_unlock_bridge(unsigned long lock_addr);
#else
void *process_pt_create_bridge(unsigned long flags)
{
	return ihk_mc_pt_create(flags);
}

unsigned long process_spin_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

void process_spin_unlock_bridge(unsigned long lock_addr,
				unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqstate);
}

void process_sched_noirq_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

void process_sched_noirq_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

void process_rw_read_lock_bridge(unsigned long lock_addr)
{
	ihk_rwspinlock_read_lock_noirq((ihk_rwspinlock_t *)lock_addr);
}

void process_rw_read_unlock_bridge(unsigned long lock_addr)
{
	ihk_rwspinlock_read_unlock_noirq((ihk_rwspinlock_t *)lock_addr);
}

void process_rw_write_lock_bridge(unsigned long lock_addr)
{
	ihk_rwspinlock_write_lock_noirq((ihk_rwspinlock_t *)lock_addr);
}

void process_rw_write_unlock_bridge(unsigned long lock_addr)
{
	ihk_rwspinlock_write_unlock_noirq((ihk_rwspinlock_t *)lock_addr);
}
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_sched_waitq_init_bridge(unsigned long waitq_addr);
void process_sched_waitq_prepare_bridge(unsigned long waitq_addr,
					unsigned long entry_addr,
					int status);
void process_sched_waitq_finish_bridge(unsigned long waitq_addr,
				       unsigned long entry_addr);
#else
static void process_sched_waitq_init_bridge(unsigned long waitq_addr)
{
	waitq_init((waitq_t *)waitq_addr);
}

static void process_sched_waitq_prepare_bridge(unsigned long waitq_addr,
					       unsigned long entry_addr,
					       int status)
{
	waitq_prepare_to_wait((waitq_t *)waitq_addr,
			      (waitq_entry_t *)entry_addr, status);
}

static void process_sched_waitq_finish_bridge(unsigned long waitq_addr,
					      unsigned long entry_addr)
{
	waitq_finish_wait((waitq_t *)waitq_addr,
			  (waitq_entry_t *)entry_addr);
}
#endif

static void process_sched_migrate_log_bridge(unsigned long thread_addr,
					     int tid, int cpu_id)
{
	(void)thread_addr;
	dkprintf("%s: tid: %d -> cpu: %d\n",
		 "sched_request_migrate", tid, cpu_id);
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
int process_sched_vector_bridge(int vector_key);
void process_sched_interrupt_bridge(int cpu, int vector);
void process_sched_schedule_bridge(void);
unsigned long process_sched_cpu_local_bridge(int cpu_id);
void process_sched_waitq_wakeup_bridge(unsigned long waitq_addr);
#else
static int process_sched_vector_bridge(int vector_key)
{
	return ihk_mc_get_vector(vector_key);
}

static void process_sched_interrupt_bridge(int cpu, int vector)
{
	ihk_mc_interrupt_cpu(cpu, vector);
}

static void process_sched_schedule_bridge(void)
{
	schedule();
}

static unsigned long process_sched_cpu_local_bridge(int cpu_id)
{
	return (unsigned long)get_cpu_local_var(cpu_id);
}

static void process_sched_waitq_wakeup_bridge(unsigned long waitq_addr)
{
	waitq_wakeup((waitq_t *)waitq_addr);
}
#endif

PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_do_migrate_log_bridge(unsigned long thread_addr,
						int tid, int old_cpu_id,
						int new_cpu_id)
{
	(void)thread_addr;
	dkprintf("%s: migrated TID %d from CPU %d to CPU %d\n",
		 "do_migrate", tid, old_cpu_id, new_cpu_id);
}

static void process_release_tid_log_bridge(int tid, void *thread, int new_tid)
{
	(void)new_tid;
	dkprintf("%s: tid %d has been released by %p\n",
		"__release_tid", tid, thread);
}

static void process_replace_tid_log_bridge(int tid, void *thread, int new_tid)
{
	dkprintf("%s: tid %d (thread %p) has been relaced with tid %d\n",
		"__find_and_replace_tid", tid, thread, new_tid);
}

void process_release_thread_profile_bridge(void *thread, void *proc)
{
#ifdef PROFILE_ENABLE
	profile_accumulate_events(thread, proc);
	profile_dealloc_thread_events(thread);
#else
	(void)thread;
	(void)proc;
#endif
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_procfs_delete_thread_bridge(void *thread);
void process_destroy_thread_bridge(void *thread);
void process_release_vm_bridge(void *vm);
void process_flush_vm_bridge(void *vm);
#else
void process_procfs_delete_thread_bridge(void *thread)
{
	procfs_delete_thread(thread);
}

void process_destroy_thread_bridge(void *thread)
{
	destroy_thread(thread);
}

void process_release_vm_bridge(void *vm)
{
	release_process_vm(vm);
}

void process_flush_vm_bridge(void *vm)
{
	flush_nfo_tlb_mm(vm);
}
#endif

void process_free_all_ranges_bridge(void *vm)
{
	free_all_process_memory_range(vm);
}

void process_free_vm_bridge(void *vm)
{
	kfree_tracked(vm, __FILE__, __LINE__);
}

struct list_head resource_set_list;
mcs_rwlock_lock_t    resource_set_lock;
ihk_spinlock_t runq_reservation_lock;

int idle_halt = 0;
int allow_oversubscribe = 0;
int time_sharing = 1;

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static const struct process_init_state_offsets process_init_state_offsets = {
	.pid_offset = __builtin_offsetof(struct process, pid),
	.status_offset = __builtin_offsetof(struct process, status),
	.parent_offset = __builtin_offsetof(struct process, parent),
	.ppid_parent_offset = __builtin_offsetof(struct process, ppid_parent),
	.pgid_offset = __builtin_offsetof(struct process, pgid),
	.ruid_offset = __builtin_offsetof(struct process, ruid),
	.euid_offset = __builtin_offsetof(struct process, euid),
	.suid_offset = __builtin_offsetof(struct process, suid),
	.fsuid_offset = __builtin_offsetof(struct process, fsuid),
	.rgid_offset = __builtin_offsetof(struct process, rgid),
	.egid_offset = __builtin_offsetof(struct process, egid),
	.sgid_offset = __builtin_offsetof(struct process, sgid),
	.fsgid_offset = __builtin_offsetof(struct process, fsgid),
	.mpol_flags_offset = __builtin_offsetof(struct process, mpol_flags),
	.mpol_threshold_offset =
		__builtin_offsetof(struct process, mpol_threshold),
	.thp_disable_offset = __builtin_offsetof(struct process, thp_disable),
	.rlimit_offset = __builtin_offsetof(struct process, rlimit),
	.rlimit_size = sizeof(((struct process *)0)->rlimit),
	.cpu_set_offset = __builtin_offsetof(struct process, cpu_set),
	.cpu_set_size = sizeof(((struct process *)0)->cpu_set),
	.enable_uti_offset = __builtin_offsetof(struct process, enable_uti),
};

static const struct process_find_thread_offsets process_find_thread_offsets = {
	.thread_hash_list_offset = __builtin_offsetof(struct thread, hash_list),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
};

static const struct process_find_process_offsets process_find_process_offsets = {
	.process_hash_list_offset =
		__builtin_offsetof(struct process, hash_list),
	.process_pid_offset = __builtin_offsetof(struct process, pid),
};
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void init_process(struct process *proc, struct process *parent);
#else
void
init_process(struct process *proc, struct process *parent)
{
	if (process_init_state_body_result(proc, parent,
			&process_init_state_offsets, -1, PS_RUNNING) < 0)
		panic("failed to initialize process state");

	if (process_init_links_body_result(proc,
			__builtin_offsetof(struct process, hash_list),
			__builtin_offsetof(struct process, siblings_list),
			__builtin_offsetof(struct process,
					   ptraced_siblings_list),
			__builtin_offsetof(struct process, update_lock),
			__builtin_offsetof(struct process,
					   report_threads_list),
			__builtin_offsetof(struct process, threads_list),
			__builtin_offsetof(struct process, children_list),
			__builtin_offsetof(struct process,
					   ptraced_children_list),
			__builtin_offsetof(struct process, threads_lock),
			__builtin_offsetof(struct process, children_lock),
			__builtin_offsetof(struct process, coredump_lock),
			__builtin_offsetof(struct process, mckfd_lock),
			__builtin_offsetof(struct process, waitpid_q),
			__builtin_offsetof(struct process, refcount),
			__builtin_offsetof(struct process, monitoring_event),
			process_rwlock_init_bridge, process_spin_init_bridge,
			process_waitq_init_bridge, NULL) < 0)
		panic("failed to initialize process links");
#ifdef PROFILE_ENABLE
	if (process_init_profile_body_result(proc,
			__builtin_offsetof(struct process, profile_lock),
			__builtin_offsetof(struct process, profile_events),
			process_mcs_lock_init_bridge) < 0)
		panic("failed to initialize process profile state");
#endif
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
chain_process(struct process *proc)
{
	struct mcs_rwlock_node_irqsave lock;
	struct process *parent = proc->parent;
	int hash;
	struct process_hash *phash;

	hash = process_hash(proc->pid);
	phash = get_this_cpu_local_var()->resource_set->process_hash;
	process_chain_process_body_result(&proc->siblings_list,
		&parent->children_list, (unsigned long)&parent->children_lock,
		&proc->hash_list, &phash->list[hash],
		(unsigned long)&phash->lock[hash], &lock,
		process_mcs_writer_lock_bridge,
		process_mcs_writer_unlock_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
chain_thread(struct thread *thread)
{
	struct mcs_rwlock_node_irqsave lock;
	struct process *proc = thread->proc;
	struct process_vm *vm = thread->vm;
	int hash;
	struct thread_hash *thash;

	hash = thread_hash(thread->tid);
	thash = get_this_cpu_local_var()->resource_set->thread_hash;
	process_chain_thread_body_result(&thread->siblings_list,
		&proc->threads_list, (unsigned long)&proc->threads_lock,
		&thread->hash_list, &thash->list[hash],
		(unsigned long)&thash->lock[hash], vm,
		__builtin_offsetof(struct process_vm, refcount), &lock,
		process_mcs_writer_lock_bridge,
		process_mcs_writer_unlock_bridge, NULL);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
struct address_space *
create_address_space(struct resource_set *res, int n)
{
	(void)res;
	return process_create_address_space_body_result(n,
		sizeof(struct address_space), sizeof(int), IHK_MC_AP_NOWAIT,
		__builtin_offsetof(struct address_space, page_table),
		__builtin_offsetof(struct address_space, refcount),
		__builtin_offsetof(struct address_space, cpu_set),
		sizeof(cpu_set_t),
		__builtin_offsetof(struct address_space, cpu_set_lock),
		__builtin_offsetof(struct address_space, nslots),
		process_alloc_bridge,
		process_optional_free_bridge,
		process_pt_create_bridge,
		NULL,
		process_spin_init_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
hold_address_space(struct address_space *asp)
{
	process_hold_address_space_public_result(asp,
		__builtin_offsetof(struct address_space, refcount),
		NULL);
}
#endif

void process_pt_destroy_bridge(void *page_table)
{
	ihk_mc_pt_destroy(page_table);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
release_address_space(struct address_space *asp)
{
	process_release_address_space_public_result(asp,
		__builtin_offsetof(struct address_space, refcount),
		__builtin_offsetof(struct address_space, free_cb),
		__builtin_offsetof(struct address_space, opt),
		__builtin_offsetof(struct address_space, page_table),
		NULL,
		process_pt_destroy_bridge,
		process_optional_free_bridge);
}
#endif

void process_release_address_space_action_bridge(void *asp)
{
	release_address_space(asp);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
detach_address_space(struct address_space *asp, int pid)
{
	process_detach_address_space_public_result(asp, pid,
		__builtin_offsetof(struct address_space, pids),
		__builtin_offsetof(struct address_space, nslots),
		process_release_address_space_action_bridge);
}
#endif

int process_init_process_public_bridge(void *proc, void *parent)
{
	init_process(proc, parent);
	return 0;
}

void process_proc_init_panic_bridge(void)
{
	panic("no mem for resource_set");
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int
init_process_vm(struct process *owner, struct address_space *asp, struct process_vm *vm)
{
	return process_vm_init_body_result(vm, owner, asp,
		ihk_mc_get_nr_numa_nodes(), process_vm_rwspin_init_bridge,
		process_spin_init_bridge, process_vm_init_numa_log_bridge);
}
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void *process_create_thread_alloc_pages_bridge(int npages,
					      unsigned long flags)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

void *process_create_thread_address_space_bridge(int nslots)
{
	return create_address_space(get_this_cpu_local_var()->resource_set, nslots);
}

void process_create_thread_release_address_space_bridge(void *asp)
{
	release_address_space(asp);
}

int process_create_thread_init_process_bridge(void *proc, void *parent)
{
	init_process(proc, parent);
	return 0;
}

int process_create_thread_init_vm_bridge(void *owner, void *asp,
					void *vm)
{
	return init_process_vm(owner, asp, vm);
}

void process_create_thread_init_user_bridge(void *thread,
	unsigned long stack_top, unsigned long user_pc,
	unsigned long user_sp)
{
	struct thread *t = thread;

	ihk_mc_init_user_process(&t->ctx, &t->uctx, (void *)stack_top,
				 user_pc, user_sp);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
struct thread *create_thread(unsigned long user_pc,
		unsigned long *__cpu_set, size_t cpu_set_size)
{
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
	return process_create_thread_body_result(user_pc,
			(unsigned long)__cpu_set, cpu_set_size * BITS_PER_BYTE,
			KERNEL_STACK_NR_PAGES, sizeof(struct thread),
			sizeof(struct process), sizeof(struct process_vm),
			IHK_MC_AP_NOWAIT, KERNEL_STACK_NR_PAGES * PAGE_SIZE,
			CPU_SETSIZE, num_processors, SCHED_NORMAL,
			SS_DISABLE, ihk_mc_get_processor_id(),
			get_this_cpu_local_var()->resource_set->pid1,
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct thread, refcount),
			__builtin_offsetof(struct thread, hash_list),
			__builtin_offsetof(struct thread, siblings_list),
			__builtin_offsetof(struct thread, cpu_set),
			__builtin_offsetof(struct thread, sched_policy),
			__builtin_offsetof(struct thread, sigcommon),
			__builtin_offsetof(struct thread, sigpendinglock),
			__builtin_offsetof(struct thread, sigpending),
			__builtin_offsetof(struct thread, sigstack),
			__builtin_offsetof(stack_t, ss_sp),
			__builtin_offsetof(stack_t, ss_flags),
			__builtin_offsetof(stack_t, ss_size),
			__builtin_offsetof(struct thread, vm),
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, cpu_set),
			__builtin_offsetof(struct process, vm),
			__builtin_offsetof(struct process, main_thread),
			__builtin_offsetof(struct process_vm, address_space),
			__builtin_offsetof(struct address_space, cpu_set),
			__builtin_offsetof(struct address_space, cpu_set_lock),
			__builtin_offsetof(struct thread, exit_status),
			__builtin_offsetof(struct thread, spin_sleep_lock),
			__builtin_offsetof(struct thread, spin_sleep),
			sizeof(struct sig_common),
			__builtin_offsetof(struct sig_common, use),
			__builtin_offsetof(struct sig_common, lock),
			__builtin_offsetof(struct sig_common, sigpending),
			process_create_thread_alloc_pages_bridge,
			process_alloc_bridge, process_optional_free_bridge,
			process_create_thread_address_space_bridge,
			process_create_thread_release_address_space_bridge,
			process_create_thread_init_process_bridge,
			process_create_thread_init_vm_bridge,
			process_create_thread_init_user_bridge,
			process_default_ncpus_bridge, process_create_cpu_log_bridge,
			process_rwlock_init_bridge, process_spin_init_bridge,
			process_spin_lock_bridge, process_spin_unlock_bridge,
			process_free_thread_pages_bridge);
#else
	struct thread *thread;
	struct process *proc;
	struct process_vm *vm = NULL;
	struct address_space *asp = NULL;

	thread = _ihk_mc_alloc_aligned_pages_node(KERNEL_STACK_NR_PAGES, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (!thread)
		return NULL;
	if (process_thread_alloc_init_body_result(thread, sizeof(struct thread),
			__builtin_offsetof(struct thread, refcount),
			__builtin_offsetof(struct thread, hash_list),
			__builtin_offsetof(struct thread, siblings_list),
			NULL) < 0)
		goto err_thread;
	proc = kmalloc_tracked(sizeof(struct process), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	vm = kmalloc_tracked(sizeof(struct process_vm), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	asp = create_address_space(get_this_cpu_local_var()->resource_set, 1);
	if (!proc || !vm || !asp)
		goto err;
	if (process_allocated_object_zero_body_result(proc, sizeof(*proc)) < 0)
		goto err;
	if (process_allocated_object_zero_body_result(vm, sizeof(*vm)) < 0)
		goto err;
	init_process(proc, get_this_cpu_local_var()->resource_set->pid1);

	if (process_create_cpu_sets_body_result((unsigned long)__cpu_set,
			cpu_set_size * BITS_PER_BYTE,
			(unsigned long)&thread->cpu_set,
			(unsigned long)&proc->cpu_set, CPU_SETSIZE,
			num_processors, proc->pid, process_default_ncpus_bridge,
			process_create_cpu_log_bridge) < 0)
		goto err;

	if (process_thread_sched_default_body_result(thread,
			__builtin_offsetof(struct thread, sched_policy),
			SCHED_NORMAL) < 0)
		goto err;

	thread->sigcommon = process_sigcommon_alloc_init_body_result(
		sizeof(struct sig_common), IHK_MC_AP_NOWAIT,
		__builtin_offsetof(struct sig_common, use),
		__builtin_offsetof(struct sig_common, lock),
		__builtin_offsetof(struct sig_common, sigpending),
		process_alloc_bridge, process_optional_free_bridge,
		NULL, process_rwlock_init_bridge);
	if (!thread->sigcommon) {
		goto err;
	}

	dkprintf("fork(): sigshared\n");

	process_thread_sigpending_init_body_result(thread,
		__builtin_offsetof(struct thread, sigpendinglock),
		__builtin_offsetof(struct thread, sigpending),
		process_rwlock_init_bridge);

	if (process_thread_sigstack_disable_body_result(thread,
			__builtin_offsetof(struct thread, sigstack),
			__builtin_offsetof(stack_t, ss_sp),
			__builtin_offsetof(stack_t, ss_flags),
			__builtin_offsetof(stack_t, ss_size), SS_DISABLE) < 0)
		goto err;

	ihk_mc_init_user_process(&thread->ctx, &thread->uctx, ((char *)thread) +
	                       KERNEL_STACK_NR_PAGES * PAGE_SIZE, user_pc, 0);

	if (process_create_thread_link_state_body_result(thread, proc, vm,
			__builtin_offsetof(struct thread, vm),
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, vm),
			__builtin_offsetof(struct process, main_thread)) < 0)
		goto err;

	if(init_process_vm(proc, asp, vm) != 0){
		goto err;
	}
	if (process_thread_exit_status_init_body_result(thread,
			__builtin_offsetof(struct thread, exit_status), -1) < 0)
		goto err;

	process_cpu_set_update_body_result(
		(unsigned long)&thread->vm->address_space->cpu_set,
		(unsigned long)&thread->vm->address_space->cpu_set_lock,
		-1, ihk_mc_get_processor_id(), num_processors,
		process_spin_lock_bridge, process_spin_unlock_bridge);

	if (process_thread_spin_sleep_init_body_result(thread,
			__builtin_offsetof(struct thread, spin_sleep_lock),
			__builtin_offsetof(struct thread, spin_sleep),
			process_spin_init_bridge) < 0)
		goto err;

	return thread;

err_thread:
	process_thread_action_result(thread, process_free_thread_pages_bridge);
	return NULL;

err:
	if(proc)
		process_free_callback_result(proc, process_optional_free_bridge);
	if(vm)
		process_free_callback_result(vm, process_optional_free_bridge);
	if(asp)
		release_address_space(asp);
	if(thread->sigcommon)
		process_free_callback_result(thread->sigcommon,
			process_optional_free_bridge);
	process_thread_action_result(thread, process_free_thread_pages_bridge);

	return NULL;
#endif
}
#endif

struct thread *
clone_thread(struct thread *org, unsigned long pc, unsigned long sp,
              int clone_flags)
{
	struct thread *thread;
	int termsig = clone_flags & 0xff;
	struct process *proc = NULL;
	struct address_space *asp = NULL;
	struct cpu_local_var *v = get_this_cpu_local_var();

	if ((thread = _ihk_mc_alloc_aligned_pages_node(KERNEL_STACK_NR_PAGES, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__)) == NULL) {
		return NULL;
	}

	if (process_thread_alloc_init_body_result(thread, sizeof(struct thread),
			__builtin_offsetof(struct thread, refcount),
			__builtin_offsetof(struct thread, hash_list),
			__builtin_offsetof(struct thread, siblings_list),
			NULL) < 0)
		goto free_thread;

	if (process_clone_thread_base_state_body_result(thread, org,
			__builtin_offsetof(struct thread, cpu_set),
			sizeof(thread->cpu_set),
			__builtin_offsetof(struct thread, in_kernel)) < 0)
		goto free_thread;

	/* NOTE: sp is the user mode stack! */
	ihk_mc_init_user_process(&thread->ctx, &thread->uctx, ((char *)thread) +
				 KERNEL_STACK_NR_PAGES * PAGE_SIZE, pc, sp);

	/* copy fp_regs from parent */
	if (save_fp_regs(org)) {
		goto free_thread;
	}
	if (copy_fp_regs(org, thread)) {
		goto free_fp_regs;
	}
	arch_clone_thread(org, pc, sp, thread);

	if (process_clone_user_context_body_result(thread, org,
			__builtin_offsetof(struct thread, uctx),
			sizeof(*org->uctx), IHK_UCR_STACK_POINTER, sp,
			IHK_UCR_PROGRAM_COUNTER, pc,
			process_user_context_modify_bridge) < 0)
		goto free_fp_regs;

	if (process_clone_thread_sched_state_body_result(thread, org,
			__builtin_offsetof(struct thread, sched_policy),
			__builtin_offsetof(struct thread,
					   sched_param.sched_priority)) < 0)
		goto free_fp_regs;

	/* clone VM */
	if (process_clone_shares_vm_result(clone_flags)) {
		proc = org->proc;
		if (process_clone_thread_shared_vm_state_body_result(thread, proc,
				org->vm, __builtin_offsetof(struct thread, vm),
				__builtin_offsetof(struct thread, proc)) < 0)
			goto free_fp_regs;

		if (process_thread_sigstack_disable_body_result(thread,
				__builtin_offsetof(struct thread, sigstack),
				__builtin_offsetof(stack_t, ss_sp),
				__builtin_offsetof(stack_t, ss_flags),
				__builtin_offsetof(stack_t, ss_size),
				SS_DISABLE) < 0)
			goto free_fp_regs;
	}
	/* fork() */
	else {
		proc = kmalloc_tracked(sizeof(struct process), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if(!proc)
			goto free_fp_regs;
		if (process_allocated_object_zero_body_result(proc,
				sizeof(*proc)) < 0)
			goto free_fork_process_proc;
		init_process(proc, org->proc);
#ifdef PROFILE_ENABLE
		if (process_clone_fork_profile_body_result(proc, org->proc,
				__builtin_offsetof(struct process, profile)) < 0)
			goto free_fork_process_proc;
#endif
		if (process_clone_fork_process_termsig_body_result(proc,
				__builtin_offsetof(struct process, termsig),
				termsig) < 0)
			goto free_fork_process_proc;
		asp = create_address_space(get_this_cpu_local_var()->resource_set, 1);
		if (!asp) {
			goto free_fork_process_proc;
		}
		proc->vm = kmalloc_tracked(sizeof(struct process_vm), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!proc->vm) {
			goto free_fork_process_asp;
		}
		if (process_allocated_object_zero_body_result(proc->vm,
				sizeof(*proc->vm)) < 0)
			goto free_fork_process_vm;

		if (process_clone_fork_saved_cmdline_body_result(proc, org->proc,
				__builtin_offsetof(struct process, saved_cmdline_len),
				__builtin_offsetof(struct process, saved_cmdline),
				IHK_MC_AP_NOWAIT, process_alloc_bridge) != 0) {
			goto free_fork_process_vm;
		}

		dkprintf("fork(): init_process_vm()\n");
		if (init_process_vm(proc, asp, proc->vm) != 0) {
			goto free_fork_process_cmdline;
		}
		if (process_clone_fork_vm_policy_body_result(proc->vm, org->vm,
				__builtin_offsetof(struct process_vm, numa_mask),
				sizeof(proc->vm->numa_mask),
				__builtin_offsetof(struct process_vm,
						   numa_mem_policy),
				__builtin_offsetof(struct process_vm, region),
				sizeof(struct vm_regions)) < 0)
			goto free_fork_process_cmdline;

		if (process_create_thread_link_state_body_result(thread, proc,
				proc->vm, __builtin_offsetof(struct thread, vm),
				__builtin_offsetof(struct thread, proc),
				__builtin_offsetof(struct process, vm),
				__builtin_offsetof(struct process, main_thread)) < 0)
			goto free_fork_process_cmdline;

		dkprintf("fork(): copy_user_ranges()\n");
		/* Copy user-space mappings.
		 * TODO: do this with COW later? */
		if (process_clone_on_fork_vm_body_result(v,
				__builtin_offsetof(struct cpu_local_var,
						   on_fork_vm),
				proc->vm) < 0)
			goto free_fork_process_cmdline;
		if (copy_user_ranges(proc->vm, org->vm) != 0) {
			process_clone_on_fork_vm_body_result(v,
				__builtin_offsetof(struct cpu_local_var,
						   on_fork_vm),
				NULL);
			goto free_fork_process_cmdline;
		}
		process_clone_on_fork_vm_body_result(v,
			__builtin_offsetof(struct cpu_local_var, on_fork_vm),
			NULL);

		/* Copy mckfd list
		   FIXME: Replace list manipulation with list_add() etc. */
		unsigned long irqstate = process_spin_lock_result(
			(unsigned long)&proc->mckfd_lock,
			process_spin_lock_bridge);
		struct mckfd *cur;
		for (cur = org->proc->mckfd; cur; cur = cur->next) {
			struct mckfd *mckfd = kmalloc_tracked(sizeof(struct mckfd), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if(!mckfd) {
				process_spin_unlock_result(
					(unsigned long)&proc->mckfd_lock,
					irqstate, process_spin_unlock_bridge);
				goto free_fork_process_mckfd;
			}
			if (process_mckfd_copy_body_result(mckfd, cur,
					sizeof(struct mckfd)) < 0) {
				kfree_tracked(mckfd, __FILE__, __LINE__);
				process_spin_unlock_result(
					(unsigned long)&proc->mckfd_lock,
					irqstate, process_spin_unlock_bridge);
				goto free_fork_process_mckfd;
			}
			process_mckfd_push_head_result(&proc->mckfd, mckfd);

			if (process_mckfd_should_dup_result(
				    (unsigned long)mckfd->dup_cb)) {
				process_mckfd_dup_result(mckfd,
					(process_mckfd_dup_fn_t)mckfd->dup_cb);
			}
		}
		process_spin_unlock_result((unsigned long)&proc->mckfd_lock,
			irqstate, process_spin_unlock_bridge);

		process_clone_copy_vm_thread_state_result(thread->vm, org->vm,
			__builtin_offsetof(struct process_vm, vdso_addr),
			__builtin_offsetof(struct process_vm, vvar_addr),
			thread, org, __builtin_offsetof(struct thread, sigstack),
			sizeof(thread->sigstack));

		dkprintf("fork(): copy_user_ranges() OK\n");
	}

	/* clone signal handlers */
	if (process_clone_shares_sighand_result(clone_flags)) {
		if (process_clone_sigcommon_share_body_result(thread, org,
				__builtin_offsetof(struct thread, sigcommon),
				__builtin_offsetof(struct sig_common, use),
				NULL) < 0) {
			if (process_clone_shares_vm_result(clone_flags)) {
				goto free_clone_process;
			}
			goto free_fork_process_mckfd;
		}
	}
	/* copy signal handlers (i.e., fork()) */
	else {
		dkprintf("fork(): sigcommon\n");
		thread->sigcommon = process_sigcommon_alloc_init_body_result(
			sizeof(struct sig_common), IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct sig_common, use),
			__builtin_offsetof(struct sig_common, lock),
			__builtin_offsetof(struct sig_common, sigpending),
			process_alloc_bridge, process_optional_free_bridge,
			NULL, process_rwlock_init_bridge);
		if (!thread->sigcommon) {
			if (process_clone_shares_vm_result(clone_flags)) {
				goto free_clone_process;
			}
			goto free_fork_process_mckfd;
		}

		dkprintf("fork(): sigshared\n");

		if (process_clone_sigcommon_action_copy_body_result(
				thread->sigcommon, org->sigcommon,
				__builtin_offsetof(struct sig_common, action),
				sizeof(struct k_sigaction) * _NSIG) < 0) {
			if (process_clone_shares_vm_result(clone_flags)) {
				goto free_clone_process;
			}
			goto free_fork_process_mckfd;
		}
		// TODO: copy signalfd
	}
	process_thread_sigpending_init_body_result(thread,
		__builtin_offsetof(struct thread, sigpendinglock),
		__builtin_offsetof(struct thread, sigpending),
		process_rwlock_init_bridge);
	if (process_thread_sigmask_copy_body_result(thread, org,
			__builtin_offsetof(struct thread, sigmask),
			sizeof(thread->sigmask)) < 0) {
		if (process_clone_shares_vm_result(clone_flags)) {
			goto free_clone_process;
		}
		goto free_fork_process_mckfd;
	}

	if (process_thread_spin_sleep_init_body_result(thread,
			__builtin_offsetof(struct thread, spin_sleep_lock),
			__builtin_offsetof(struct thread, spin_sleep),
			process_spin_init_bridge) < 0) {
		if (process_clone_shares_vm_result(clone_flags)) {
			goto free_clone_process;
		}
		goto free_fork_process_mckfd;
	}

#ifdef PROFILE_ENABLE
	if (process_clone_profile_state_body_result(thread, org, proc,
			__builtin_offsetof(struct thread, profile),
			__builtin_offsetof(struct process, profile)) < 0) {
		if (process_clone_shares_vm_result(clone_flags)) {
			goto free_clone_process;
		}
		goto free_fork_process_mckfd;
	}
#endif

	return thread;

	/*
	 * free process(clone)
	 * case of (clone_flags & CLONE_VM)
	 */
free_clone_process:
	goto  free_fp_regs;

	/*
	 * free process(fork)
	 * case of !(clone_flags & CLONE_VM)
	 */
free_fork_process_mckfd:
	{
		unsigned long irqstate = process_spin_lock_result(
			(unsigned long)&proc->mckfd_lock,
			process_spin_lock_bridge);

		process_mckfd_drain_free_result(&proc->mckfd,
			__builtin_offsetof(struct mckfd, next),
			process_mckfd_free_bridge);
		process_spin_unlock_result((unsigned long)&proc->mckfd_lock,
			irqstate, process_spin_unlock_bridge);
	}
	process_vm_action_result(proc->vm, process_free_all_ranges_bridge);
free_fork_process_cmdline:
	process_free_callback_result(proc->saved_cmdline,
		process_optional_free_bridge);
free_fork_process_vm:
	process_free_callback_result(proc->vm, process_optional_free_bridge);
free_fork_process_asp:
	process_pt_destroy_result(asp->page_table, process_pt_destroy_bridge);
	process_free_callback_result(asp, process_optional_free_bridge);
free_fork_process_proc:
	process_free_callback_result(proc, process_optional_free_bridge);

	/*
	 * free fp_regs
	 */
free_fp_regs:
	process_release_fp_regs_result(thread, release_fp_regs);

	/*
	 * free thread
	 */
free_thread:
	process_thread_action_result(thread, process_free_thread_pages_bridge);
	return NULL;
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int
ptrace_traceme(void)
{
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct process *parent = proc->parent;
	struct mcs_rwlock_node child_lock;
	struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
	struct process *pid1 = resource_set->pid1;
	static const struct process_ptrace_traceme_offsets offsets = {
		.thread_proc_offset = __builtin_offsetof(struct thread, proc),
		.thread_report_proc_offset =
			__builtin_offsetof(struct thread, report_proc),
		.thread_report_siblings_list_offset =
			__builtin_offsetof(struct thread, report_siblings_list),
		.thread_ptrace_offset =
			__builtin_offsetof(struct thread, ptrace),
		.thread_ptrace_debugreg_offset =
			__builtin_offsetof(struct thread, ptrace_debugreg),
		.proc_pid_offset = __builtin_offsetof(struct process, pid),
		.proc_parent_offset =
			__builtin_offsetof(struct process, parent),
		.proc_main_thread_offset =
			__builtin_offsetof(struct process, main_thread),
		.proc_children_lock_offset =
			__builtin_offsetof(struct process, children_lock),
		.proc_threads_lock_offset =
			__builtin_offsetof(struct process, threads_lock),
		.proc_ptraced_siblings_list_offset =
			__builtin_offsetof(struct process, ptraced_siblings_list),
		.proc_ptraced_children_list_offset =
			__builtin_offsetof(struct process, ptraced_children_list),
		.proc_report_threads_list_offset =
			__builtin_offsetof(struct process, report_threads_list),
	};

	return process_ptrace_traceme_body_result(thread, proc, parent, pid1,
			&offsets, &child_lock,
			process_ptrace_mcs_lock_noirq_bridge,
			process_ptrace_mcs_unlock_noirq_bridge,
			process_ptrace_alloc_debugreg_bridge,
			process_ptrace_clear_single_step_bridge,
			process_ptrace_hold_thread_bridge,
			process_ptrace_traceme_log_bridge);
#else
	int error = 0;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct process *parent = proc->parent;
	struct mcs_rwlock_node child_lock;
	struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
	struct process *pid1 = resource_set->pid1;

	dkprintf("ptrace_traceme,pid=%d,proc->parent=%p\n", proc->pid, proc->parent);

	if (thread->ptrace & PT_TRACED) {
		return -EPERM;
	}
	if (parent == pid1) {
		return -EPERM;
	}

	dkprintf("ptrace_traceme,parent->pid=%d\n", proc->parent->pid);

	if (thread == proc->main_thread) {
		mcs_rwlock_writer_lock_noirq(&parent->children_lock,
					     &child_lock);
		process_list_add_tail_result(&proc->ptraced_siblings_list,
					     &parent->ptraced_children_list);
		mcs_rwlock_writer_unlock_noirq(&parent->children_lock,
					       &child_lock);
	}
	if (!thread->report_proc) {
		mcs_rwlock_writer_lock_noirq(&parent->threads_lock,
					     &child_lock);
		process_thread_report_attach_result(thread, 0, 0, 0,
			__builtin_offsetof(struct thread, report_proc),
			parent, &thread->report_siblings_list,
			&parent->report_threads_list);
		mcs_rwlock_writer_unlock_noirq(&parent->threads_lock,
					       &child_lock);
	}

	thread->ptrace = PT_TRACED | PT_TRACE_EXEC;

	if (thread->ptrace_debugreg == NULL) {
		error = alloc_debugreg(thread);
	}

	clear_single_step(thread);
	hold_thread(thread);

	dkprintf("ptrace_traceme,returning,error=%d\n", error);
	return error;
#endif
}
#endif

struct copy_args {
	struct process_vm *new_vm;
	unsigned long new_vrflag;
	struct vm_range *range;

	/* out */
	intptr_t fault_addr;
};

static int copy_user_pte(void *arg0, page_table_t src_pt, pte_t *src_ptep, void *pgaddr, int pgshift)
{
	struct copy_args * const args = arg0;
	int error;
	intptr_t src_phys;
	unsigned long src_lphys = 0;
	void *src_kvirt;
	size_t pgsize = (size_t)1 << pgshift;
	int npages;
	void *virt = NULL;
	intptr_t phys;
	int pgalign = pgshift - PAGE_SHIFT;
	enum ihk_mc_pt_attribute attr;
	int is_mckernel;

	if (!pte_is_present(src_ptep)) {
		error = 0;
		goto out;
	}

	src_phys = pte_get_phys(src_ptep);

	if (args->range->memobj && !(args->new_vrflag & VR_PRIVATE)) {
		error = 0;
		goto out;
	}

	if (args->new_vrflag & VR_REMOTE) {
		phys = src_phys;
		attr = pte_get_attr(src_ptep, pgsize);
	}
	else {
		if (pte_is_contiguous(src_ptep)) {
			if (page_is_contiguous_head(src_ptep, pgsize)) {
				int level = pgsize_to_tbllv(pgsize);

				pgsize = tbllv_to_contpgsize(level);
				pgalign = tbllv_to_contpgshift(level);
				pgalign -= PAGE_SHIFT;
			} else {
				error = 0;
				goto out;
			}
		}

		dkprintf("copy_user_pte(): 0x%lx PTE found\n", pgaddr);
		dkprintf("copy_user_pte(): page size: %d\n", pgsize);

		npages = pgsize / PAGE_SIZE;
		virt = _ihk_mc_alloc_aligned_pages_node(npages, pgalign, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_USER, (uintptr_t)pgaddr, __FILE__, __LINE__);
		if (!virt) {
			kprintf("ERROR: copy_user_pte() allocating new page\n");
			error = -ENOMEM;
			goto out;
		}
		phys = virt_to_phys(virt);
		dkprintf("copy_user_pte(): phys page allocated\n");

		attr = arch_vrflag_to_ptattr(args->new_vrflag, PF_POPULATE,
					     NULL);

		is_mckernel = is_mckernel_memory(src_phys, src_phys + pgsize);
		if (is_mckernel) {
			src_kvirt = phys_to_virt(src_phys);
		} else {
			src_lphys = ihk_mc_map_memory(NULL, src_phys, pgsize);
			src_kvirt = ihk_mc_map_virtual(src_lphys, 1, attr);
		}

		if (process_copy_user_pte_buffer_body_result(virt, src_kvirt,
				pgsize, args->new_vrflag & VR_WIPEONFORK) < 0) {
			error = -EINVAL;
			if (!is_mckernel) {
				ihk_mc_unmap_virtual(src_kvirt, 1);
				ihk_mc_unmap_memory(NULL, src_lphys, pgsize);
			}
			goto out;
		}
		if (args->new_vrflag & VR_WIPEONFORK) {
			dkprintf("%s(): memset OK\n", __func__);
		} else {
			dkprintf("%s(): memcpy OK\n", __func__);
		}

		if (!is_mckernel) {
			ihk_mc_unmap_virtual(src_kvirt, 1);
			ihk_mc_unmap_memory(NULL, src_lphys, pgsize);
		}
	}

	error = ihk_mc_pt_set_range(args->new_vm->address_space->page_table,
								args->new_vm, pgaddr, pgaddr + pgsize, phys, attr,
								pgshift, args->range, 0);
	if (error) {
		args->fault_addr = (intptr_t)pgaddr;
		goto out;
	}
	// fork/clone case: memory_stat_rss_add() is called in ihk_mc_pt_set_range()

	dkprintf("copy_user_pte(): new PTE set\n");
	error = 0;
	virt = NULL;

out:
	if (virt) {
		_ihk_mc_free_pages(virt, npages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	}
	return error;
}

struct vm_range *process_add_range_alloc_bridge(unsigned long size);
void process_add_range_free_bridge(struct vm_range *range);
int process_add_range_insert_bridge(struct process_vm *vm,
				    struct vm_range *range);
int process_visit_pte_range_bridge(void *page_table, unsigned long start,
				   unsigned long end, int pgshift, int flags,
				   void *visit_fn, void *arg);
int process_memory_range_free_bridge(struct process_vm *vm,
				     struct vm_range *range);

static struct vm_range *process_copy_range_lookup_bridge(struct process_vm *vm,
		unsigned long start, unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

static void process_copy_user_ranges_log_bridge(struct process_vm *orgvm,
		struct vm_range *range, long fault_addr)
{
	kprintf("ERROR: copy_user_ranges() "
			"(%p,%lx-%lx %lx,%lx):get pgsize failed\n",
			orgvm, range->start, range->end, range->flag,
			fault_addr);
}

static int copy_user_ranges(struct process_vm *vm, struct process_vm *orgvm)
{
	struct copy_args args;

	return process_copy_user_ranges_body_result(vm, orgvm,
			sizeof(struct vm_range), IHK_MC_AP_NOWAIT, &args,
			__builtin_offsetof(struct copy_args, new_vm),
			__builtin_offsetof(struct copy_args, new_vrflag),
			__builtin_offsetof(struct copy_args, range),
			__builtin_offsetof(struct copy_args, fault_addr),
			&copy_user_pte, VPTEF_SKIP_NULL,
			process_rw_read_lock_bridge,
			process_rw_read_unlock_bridge,
			process_copy_range_lookup_bridge,
			next_process_memory_range,
			process_add_range_alloc_bridge,
			process_add_range_free_bridge,
			process_add_range_insert_bridge,
			process_visit_pte_range_bridge,
			process_memory_range_free_bridge,
			process_copy_user_ranges_log_bridge);
}

unsigned long process_update_page_table_attr_bridge(unsigned long flag,
		unsigned long fault, void *ptep)
{
	return arch_vrflag_to_ptattr(flag, fault, ptep);
}

int process_update_page_table_set_range_bridge(void *page_table,
		struct process_vm *vm, unsigned long start, unsigned long end,
		unsigned long phys, unsigned long attr, int pgshift,
		struct vm_range *range, int flags)
{
	return ihk_mc_pt_set_range(page_table, vm, (void *)start, (void *)end,
			phys, attr, pgshift, range, flags);
}

void process_update_page_table_log_bridge(int error)
{
	kprintf("update_process_page_table:ihk_mc_pt_set_range failed. %d\n",
		error);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int update_process_page_table(struct process_vm *vm,
                          struct vm_range *range, uint64_t phys,
			  enum ihk_mc_pt_attribute flag)
{
	return process_update_page_table_public_result(vm, range, phys, flag,
		process_update_page_table_attr_bridge,
		process_spin_lock_bridge, process_spin_unlock_bridge,
		process_update_page_table_set_range_bridge,
		process_update_page_table_log_bridge);
}
#endif

int process_split_shm_lookup_page_bridge(struct memobj *obj, long off,
		int p2align, uintptr_t *physp, unsigned long *pflag)
{
	return memobj_lookup_page(obj, off, p2align, physp, pflag);
}

void *process_split_shm_phys_to_page_bridge(unsigned long phys)
{
	return phys_to_page(phys);
}

int process_split_shm_update_page_bridge(struct memobj *obj,
		void *page_table, void *page, void *vaddr)
{
	return memobj_update_page(obj, page_table, page, vaddr);
}

struct vm_range *process_split_range_alloc_bridge(unsigned long size,
		unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

void process_split_range_alloc_log_bridge(struct process_vm *vm,
		struct vm_range *range, unsigned long addr, void *splitp)
{
	ekprintf("split_process_memory_range(%p,%lx-%lx,%lx,%p):"
			"kmalloc failed\n",
			vm, range->start, range->end, addr, splitp);
}

void process_split_range_publish_log_bridge(int error)
{
	kprintf("%s: ERROR: could not insert range: %d\n",
		"split_process_memory_range", error);
}

int process_split_range_pt_split_bridge(void *page_table,
		struct process_vm *vm, struct vm_range *range, void *addr)
{
	return ihk_mc_pt_split(page_table, vm, range, addr);
}

void process_split_range_pt_log_bridge(int error)
{
	ekprintf("split_process_memory_range:"
			"ihk_mc_pt_split failed. %d\n", error);
}

void process_split_shm_log_bridge(int event, int error)
{
	switch (event) {
	case PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED:
		ekprintf("%s: memobj_lookup_page failed. %d\n",
			 "split_process_memory_range", error);
		break;
	case PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED:
		ekprintf("%s: memobj_update_page failed. %d\n",
			 "split_process_memory_range", error);
		break;
	default:
		break;
	}
}

unsigned long process_split_page_pgshift_offset_bridge(void)
{
	return __builtin_offsetof(struct page, pgshift);
}

int process_split_range_insert_bridge(struct process_vm *vm,
		struct vm_range *range)
{
	return vm_range_insert(vm, range);
}

void process_split_range_public_log_bridge(int event, struct process_vm *vm,
		struct vm_range *range, unsigned long addr,
		struct vm_range **splitp, struct vm_range *newrange, int error)
{
	switch (event) {
	case 1:
		dkprintf("split_process_memory_range(%p,%lx-%lx,%lx,%p)\n",
				vm, range->start, range->end, addr, splitp);
		break;
	case 2:
		dkprintf("split_process_memory_range(%p,%lx-%lx,%lx,%p):"
				" %d %p %lx-%lx\n",
				vm, range->start, range->end, addr, splitp,
				error, newrange,
				newrange? newrange->start: 0,
				newrange? newrange->end: 0);
		break;
	default:
		break;
	}
}

#ifdef ENABLE_TOFU
void process_split_range_tofu_init_bridge(struct vm_range *range)
{
	INIT_LIST_HEAD(&range->tofu_stag_list);
}

void process_split_range_tofu_split_bridge(struct process_vm *vm,
		struct vm_range *range_low, struct vm_range *range_high,
		uintptr_t addr)
{
	extern int tofu_stag_split_vm_range_on_addr(struct process_vm *vm,
			struct vm_range *range_low, struct vm_range *range_high,
			uintptr_t addr);
	int moved =
		tofu_stag_split_vm_range_on_addr(vm, range_low, range_high, addr);
	if (moved > 0) {
		kprintf("%s: moved %d stag ranges\n",
			"split_process_memory_range", moved);
	}
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int split_process_memory_range(struct process_vm *vm, struct vm_range *range,
		uintptr_t addr, struct vm_range **splitp)
{
	int error;
	struct vm_range *newrange = NULL;

	dkprintf("split_process_memory_range(%p,%lx-%lx,%lx,%p)\n",
			vm, range->start, range->end, addr, splitp);

	error = process_split_range_pt_body_result(vm, range, addr,
			process_split_range_pt_split_bridge,
			process_split_range_pt_log_bridge);
	if (error)
		goto out;
	// memory_stat_rss_add() is called in child-node, i.e. ihk_mc_pt_split() to deal with L3->L2 case

	error = process_split_shm_update_body_result(vm, range, addr,
			__builtin_offsetof(struct page, pgshift),
			process_split_shm_lookup_page_bridge,
			process_split_shm_phys_to_page_bridge,
			process_split_shm_update_page_bridge,
			process_split_shm_log_bridge);
	if (error)
		goto out;

	newrange = process_split_range_alloc_init_body_result(vm, range, addr,
			splitp, sizeof(struct vm_range), IHK_MC_AP_NOWAIT,
			&error, process_split_range_alloc_bridge,
			process_split_range_alloc_log_bridge);
	if (error)
		goto out;

#ifdef ENABLE_TOFU
	INIT_LIST_HEAD(&newrange->tofu_stag_list);
	{
		extern int tofu_stag_split_vm_range_on_addr(struct process_vm *vm,
				struct vm_range *range_low, struct vm_range *range_high,
				uintptr_t addr);

		int moved =
			tofu_stag_split_vm_range_on_addr(vm, range, newrange, addr);
		if (moved > 0) {
			kprintf("%s: moved %d stag ranges\n", __func__, moved);
		}
	}
#endif

	error = process_split_range_publish_body_result(vm, range, newrange,
			addr, splitp, NULL, vm_range_insert,
			process_split_range_publish_log_bridge);
	if (error)
		return error;

out:
	dkprintf("split_process_memory_range(%p,%lx-%lx,%lx,%p): %d %p %lx-%lx\n",
			vm, range->start, range->end, addr, splitp,
			error, newrange,
			newrange? newrange->start: 0, newrange? newrange->end: 0);
	return error;
}
#endif

#ifdef ENABLE_TOFU
int process_join_range_tofu_bridge(struct process_vm *vm,
		struct vm_range *surviving, struct vm_range *merging)
{
	/* Move Tofu stag range entries */
	if (vm->proc->enable_tofu) {
		struct tofu_stag_range *tsr, *next;

		ihk_mc_spinlock_lock_noirq(&vm->tofu_stag_lock);
		for (tsr = ((typeof(*tsr) *)((char *)((&merging->tofu_stag_list)->next) - offsetof(typeof(*tsr), list))), next = ((typeof(*tsr) *)((char *)(tsr->list.next) - offsetof(typeof(*tsr), list))); &tsr->list != (&merging->tofu_stag_list); tsr = next, next = ((typeof(*next) *)((char *)(next->list.next) - offsetof(typeof(*next), list)))) {
			list_del(&tsr->list);
			list_add_tail(&tsr->list, &surviving->tofu_stag_list);
			dkprintf("%s: stag: %d @ %p:%lu moved in VM range merge\n",
					__func__,
					tsr->stag,
					tsr->start,
					(unsigned long)(tsr->end - tsr->start));
		}
		ihk_mc_spinlock_unlock_noirq(&vm->tofu_stag_lock);
	}

	return 0;
}
#endif

void process_range_kfree_bridge(struct vm_range *range)
{
	kfree_tracked(range, __FILE__, __LINE__);
}

void process_join_range_log_bridge(int event, struct process_vm *vm,
		struct vm_range *surviving, struct vm_range *merging, int error)
{
	switch (event) {
	case 1:
		dkprintf("join_process_memory_range(%p,%lx-%lx,%lx-%lx)\n",
			vm, surviving->start, surviving->end,
			merging->start, merging->end);
		break;
	case 2:
		dkprintf("join_process_memory_range(%p,%lx-%lx,%p): %d\n",
			vm, surviving->start, surviving->end, merging, error);
		break;
	default:
		break;
	}
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int join_process_memory_range(struct process_vm *vm,
		struct vm_range *surviving, struct vm_range *merging)
{
	int error;

	process_join_range_log_bridge(1, vm, surviving, merging, 0);

	error = process_join_range_body_result(vm, &vm->vm_range_tree,
			vm->range_cache, VM_RANGE_CACHE_SIZE, surviving,
			merging, NULL,
			process_range_kfree_bridge,
#ifdef ENABLE_TOFU
			process_join_range_tofu_bridge
#else
			NULL
#endif
			);
	process_join_range_log_bridge(2, vm, surviving, merging, error);
	return error;
}
#endif

static int process_free_range_page_size_bridge(size_t current, size_t *nextp)
{
	return arch_get_smaller_page_size(NULL, current, nextp, NULL);
}

static void *process_free_range_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

static void process_free_range_pages_bridge(void *addr, unsigned long pages)
{
	_ihk_mc_free_pages(addr, pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

static int process_free_range_clear_main_bridge(struct process_vm *vm,
		unsigned long start, unsigned long end)
{
	int error;

	ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);
	error = ihk_mc_pt_clear_range(vm->address_space->page_table, vm,
			(void *)start, (void *)end);
	ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);

	return error;
}

void process_free_range_noirq_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

void process_free_range_noirq_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

int process_free_range_pt_free_bridge(void *page_table,
		struct process_vm *vm, unsigned long start, unsigned long end,
		void *memobj)
{
	return ihk_mc_pt_free_range(page_table, vm, (void *)start, (void *)end,
			memobj);
}

static int process_free_range_pt_clear_bridge(void *page_table,
		struct process_vm *vm, unsigned long start, unsigned long end)
{
	return ihk_mc_pt_clear_range(page_table, vm, (void *)start,
			(void *)end);
}

#ifdef ENABLE_TOFU
static int process_free_range_tofu_remove_bridge(struct process_vm *vm,
		struct vm_range *range)
{
	extern int tofu_stag_range_remove_overlapping(struct process_vm *vm,
			struct vm_range *range);

	return tofu_stag_range_remove_overlapping(vm, range);
}
#endif

static void process_free_range_log_bridge(int event, struct process_vm *vm,
		struct vm_range *range, unsigned long start, unsigned long end,
		int error)
{
	switch (event) {
	case PROCESS_FREE_BODY_LOG_PLAN_FAILED:
		kprintf("free_process_memory_range:"
				"arch_get_smaller_page_size failed. %d\n",
				error);
		break;
	case PROCESS_FREE_BODY_LOG_PT_FREE_FAILED:
		ekprintf("free_process_memory_range(%p,%lx-%lx):"
				"ihk_mc_pt_free_range(%lx-%lx,%p) failed. %d\n",
				vm, range->start, range->end, start, end,
				range->memobj, error);
		break;
	case PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED:
		ekprintf("free_process_memory_range(%p,%lx-%lx):"
				"ihk_mc_pt_clear_range(%lx-%lx) failed. %d\n",
				vm, range->start, range->end, start, end, error);
		break;
	case PROCESS_FREE_BODY_LOG_TOFU_REMOVED:
		dkprintf("%s: removed %d Tofu stag entries for range 0x%lx:%lu\n",
				__func__, error, start, end - start);
		break;
	case PROCESS_FREE_BODY_LOG_FINALIZE_FAILED:
		ekprintf("free_process_memory_range(%p,%lx-%lx):"
				"finalize failed. %d\n", vm, start, end, error);
		break;
	case PROCESS_FREE_BODY_LOG_DONE:
		dkprintf("free_process_memory_range(%p,%lx-%lx): 0\n",
				vm, start, end);
		break;
	}
}

static int free_process_memory_range(struct process_vm *vm,
					struct vm_range *range)
{
	dkprintf("free_process_memory_range(%p, 0x%lx - 0x%lx)\n",
			vm, range->start, range->end);
	return process_free_memory_range_body_result(vm, range,
			(unsigned long)vm->proc->straight_va,
			&vm->proc->straight_len, vm->proc->straight_pa,
#ifdef ENABLE_TOFU
			vm->proc->enable_tofu,
#else
			0,
#endif
			process_free_range_page_size_bridge,
			process_free_range_noirq_lock_bridge,
			process_free_range_noirq_unlock_bridge,
			NULL, NULL,
			process_free_range_pt_free_bridge,
			process_free_range_pt_clear_bridge,
#ifdef ENABLE_TOFU
			process_free_range_tofu_remove_bridge,
#else
			NULL,
#endif
			process_free_range_phys_to_virt_bridge,
			process_free_range_pages_bridge,
			process_free_range_clear_main_bridge,
			process_range_kfree_bridge, process_free_range_log_bridge);
}

int process_memory_range_free_bridge(struct process_vm *vm,
				     struct vm_range *range)
{
	return free_process_memory_range(vm, range);
}

void process_memory_range_free_log_bridge(struct process_vm *vm,
					  struct vm_range *range,
					  int error)
{
	ekprintf("free_process_memory(%p):"
			"free range failed. %lx-%lx %d\n",
			vm, range->start, range->end, error);
}

void process_flush_memory_log_bridge(struct process_vm *vm,
				     struct vm_range *range,
				     int error)
{
	ekprintf("flush_process_memory(%p):"
			"free range failed. %lx-%lx %d\n",
			vm, range->start, range->end, error);
}

void process_flush_memory_debug_bridge(struct process_vm *vm, int event)
{
	if (event == 0) {
		dkprintf("flush_process_memory(%p)\n", vm);
	} else {
		dkprintf("flush_process_memory(%p):\n", vm);
	}
}

int process_remove_range_split_bridge(struct process_vm *vm,
				      struct vm_range *range,
				      unsigned long addr,
				      struct vm_range **splitp)
{
	return split_process_memory_range(vm, range, addr, splitp);
}

void process_remove_range_xpmem_bridge(struct process_vm *vm,
				       struct vm_range *range)
{
	xpmem_remove_process_memory_range(vm, range);
}

void process_remove_range_log_bridge(int event, struct process_vm *vm,
				     unsigned long start,
				     unsigned long end,
				     struct vm_range *range,
				     int error)
{
	switch (event) {
	case PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT:
		kprintf("%s: WARNING: no straight mapping range found for 0x%lx\n",
				"remove_process_memory_range", start);
		break;
	case PROCESS_REMOVE_RANGE_LOG_CONVERTED:
		dkprintf("%s: straight range converted from 0x%lx:%lu -> 0x%lx:%lu\n",
				"remove_process_memory_range",
				range ? range->straight_start : start,
				end - start, start, end - start);
		break;
	case PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED:
		ekprintf("remove_process_memory_range(%p,%lx,%lx):"
				"split failed %d\n", vm, start, end, error);
		break;
	case PROCESS_REMOVE_RANGE_LOG_FREE_FAILED:
		ekprintf("remove_process_memory_range(%p,%lx,%lx):"
				"free failed %d\n", vm, start, end, error);
		break;
	case PROCESS_REMOVE_RANGE_LOG_DONE:
		dkprintf("remove_process_memory_range(%p,%lx,%lx): 0 %d\n",
				vm, start, end, error);
		break;
	}
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int remove_process_memory_range(struct process_vm *vm,
		unsigned long start, unsigned long end, int *ro_freedp)
{
	dkprintf("remove_process_memory_range(%p,%lx,%lx)\n",
			vm, start, end);
	return process_remove_memory_range_body_result(vm, start, end,
			ro_freedp, (unsigned long)vm->proc->straight_va,
			vm->proc->straight_len, process_remove_range_split_bridge,
			process_remove_range_xpmem_bridge,
			process_memory_range_free_bridge,
			process_remove_range_log_bridge);
}
#endif

static void vm_range_insert_log_bridge(int event, struct process_vm *vm,
				       struct vm_range *newrange,
				       struct vm_range *range)
{
	if (event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP) {
		ekprintf("vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n",
				vm, newrange->start, newrange->end, newrange->flag,
				range->start, range->end, range->flag);
	}
	else if (event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS) {
		dkprintf("vm_range_insert: %p,%p: %lx-%lx %x\n", vm,
				newrange, newrange->start, newrange->end,
				newrange->flag);
	}
}

static void vm_range_insert_dump_bridge(struct process_vm *vm)
{
	dump_tree(vm);
}

static int vm_range_insert(struct process_vm *vm, struct vm_range *newrange)
{
	return process_vm_range_insert_result(&vm->vm_range_tree, newrange, vm,
			vm_range_insert_log_bridge, vm_range_insert_dump_bridge);
}

void process_range_public_log_bridge(int event, struct process_vm *vm,
				     struct vm_range *range,
				     unsigned long start,
				     unsigned long end, int error)
{
	switch (event) {
	case PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER:
		dkprintf("lookup_process_memory_range(%p,%lx,%lx)\n",
				vm, start, end);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT:
		dkprintf("lookup_process_memory_range(%p,%lx,%lx): %p %lx-%lx\n",
				vm, start, end, range,
				range ? range->start : 0,
				range ? range->end : 0);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER:
		dkprintf("next_process_memory_range(%p,%lx-%lx)\n",
				vm, start, end);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT:
		dkprintf("next_process_memory_range(%p,%lx-%lx): %p %lx-%lx\n",
				vm, start, end, range,
				range ? range->start : 0,
				range ? range->end : 0);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER:
		dkprintf("previous_process_memory_range(%p,%lx-%lx)\n",
				vm, start, end);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT:
		dkprintf("previous_process_memory_range(%p,%lx-%lx): %p %lx-%lx\n",
				vm, start, end, range,
				range ? range->start : 0,
				range ? range->end : 0);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER:
		dkprintf("exntend_up_process_memory_range(%p,%p %#lx-%#lx,%#lx)\n",
				vm, range,
				range ? range->start : 0,
				range ? range->end : 0, end);
		break;
	case PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT:
		dkprintf("exntend_up_process_memory_range(%p,%p %#lx-%#lx,%#lx):%d\n",
				vm, range,
				range ? range->start : 0,
				range ? range->end : 0, end, error);
		break;
	default:
		break;
	}
}

/* Parallel memset implementation on top of general
 * SMP funcution call facility */
struct memset_smp_req {
	unsigned long phys;
	size_t len;
	int val;
};

void *process_memset_smp_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

void process_memset_smp_memset_bridge(void *addr, int value, size_t len)
{
	memset(addr, value, len);
}

void process_memset_smp_log_bridge(int event, int cpu_index,
		int nr_cpus, unsigned long phys, size_t len,
		unsigned long start, unsigned long end)
{
	switch (event) {
	case 1:
		dkprintf("%s: cpu_index: %d, nr_cpus: %d, phys: 0x%lx, "
				"len: %lu, p_s: 0x%lx, p_e: 0x%lx\n",
				"memset_smp_handler", cpu_index, nr_cpus,
				phys, len, start, end);
		break;
	}
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int memset_smp_handler(int cpu_index, int nr_cpus, void *arg)
{
	struct memset_smp_req *req =
		(struct memset_smp_req *)arg;

	return process_memset_smp_handler_body_result(cpu_index, nr_cpus,
			req->phys, req->len, req->val,
			process_memset_smp_phys_to_virt_bridge,
			process_memset_smp_memset_bridge,
			process_memset_smp_log_bridge);
}
#endif

unsigned long process_memset_smp_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

int process_memset_smp_call_bridge(void *cpu_set, void *handler,
		void *arg)
{
	return smp_call_func((cpu_set_t *)cpu_set, (smp_func_t)handler, arg);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void *memset_smp(cpu_set_t *cpu_set, void *s, int c, size_t n)
{
	struct memset_smp_req req;

	(void)process_memset_smp_body_result(cpu_set, s, c, n,
			&req.phys, &req.len, &req.val,
			memset_smp_handler, &req,
			process_memset_smp_virt_to_phys_bridge,
			process_memset_smp_call_bridge);
	return NULL;
}
#endif

struct vm_range *process_add_range_alloc_bridge(unsigned long size)
{
	return kmalloc_tracked(size, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
}

void process_add_range_free_bridge(struct vm_range *range)
{
	kfree_tracked(range, __FILE__, __LINE__);
}

int process_add_range_insert_bridge(struct process_vm *vm,
				    struct vm_range *range)
{
	return vm_range_insert(vm, range);
}

int process_add_range_update_bridge(struct process_vm *vm,
				    struct vm_range *range,
				    unsigned long phys,
				    unsigned long attr)
{
	return update_process_page_table(vm, range, phys, attr);
}

void process_add_range_remove_bridge(struct process_vm *vm,
				     unsigned long start,
				     unsigned long end)
{
	remove_process_memory_range(vm, start, end, NULL);
}

void process_add_range_mark_xpmem_bridge(struct vm_range *range)
{
	range->memobj->flags |= MF_XPMEM;
}

void process_add_range_memclear_bridge(unsigned long phys,
				       unsigned long bytes)
{
#ifdef ARCH_MEMCLEAR
	memclear((void *)phys_to_virt(phys), bytes);
#else
	memset((void *)phys_to_virt(phys), 0, bytes);
#endif
}

void process_add_range_log_bridge(int event, int rc,
				  unsigned long start,
				  unsigned long end)
{
	switch (event) {
	case PROCESS_ADD_RANGE_LOG_ALLOC_FAILED:
		kprintf("%s: ERROR: allocating pages for range\n",
			"add_process_memory_range");
		break;
	case PROCESS_ADD_RANGE_LOG_INSERT_FAILED:
		kprintf("%s: ERROR: could not insert range: %d\n",
			"add_process_memory_range", rc);
		break;
	case PROCESS_ADD_RANGE_LOG_PREP_FAILED:
		kprintf("%s: ERROR: preparing page tables\n",
			"add_process_memory_range");
		break;
	case PROCESS_ADD_RANGE_LOG_DEMAND:
		dkprintf("%s: range: 0x%lx - 0x%lx is demand paging\n",
				"add_process_memory_range", start, end);
		break;
	case PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED:
		kprintf("%s: error: range %lx - %lx is not in user available area\n",
				"add_process_memory_range", start, end);
		break;
	default:
		break;
	}
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int add_process_memory_range(struct process_vm *vm,
		unsigned long start, unsigned long end,
		unsigned long phys, unsigned long flag,
		struct memobj *memobj, off_t offset,
		int pgshift, void *private_data, struct vm_range **rp)
{
	dkprintf("%s: start=%lx,end=%lx,phys=%lx,flag=%lx\n", __FUNCTION__, start, end, phys, flag);
	return process_add_range_public_body_result(vm, sizeof(struct vm_range),
			vm->region.user_start, vm->region.user_end, start, end,
			phys, flag, memobj, offset, pgshift, private_data, rp,
			process_add_range_alloc_bridge, process_add_range_free_bridge,
			process_add_range_insert_bridge,
			process_add_range_update_bridge,
			process_add_range_remove_bridge,
			process_add_range_mark_xpmem_bridge,
			process_add_range_memclear_bridge, process_add_range_log_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
struct vm_range *lookup_process_memory_range(
		struct process_vm *vm, uintptr_t start, uintptr_t end)
{
	return process_lookup_memory_range_public_result(vm, start, end,
			process_range_public_log_bridge);
}

struct vm_range *next_process_memory_range(
		struct process_vm *vm, struct vm_range *range)
{
	return process_next_memory_range_public_result(vm, range,
			process_range_public_log_bridge);
}

struct vm_range *previous_process_memory_range(
		struct process_vm *vm, struct vm_range *range)
{
	return process_previous_memory_range_public_result(vm, range,
			process_range_public_log_bridge);
}

int extend_up_process_memory_range(struct process_vm *vm,
		struct vm_range *range, uintptr_t newend)
{
	return process_extend_up_public_result(vm, range, newend,
			process_range_public_log_bridge);
}
#endif

unsigned long process_change_prot_attr_bridge(unsigned long flag,
		unsigned long fault, void *ptep)
{
	return arch_vrflag_to_ptattr(flag, fault, ptep);
}

int process_change_prot_pt_change_bridge(void *page_table,
		unsigned long start, unsigned long end,
		unsigned long clrattr, unsigned long setattr)
{
	return ihk_mc_pt_change_attr_range(page_table, (void *)start,
			(void *)end, clrattr, setattr);
}

void process_change_prot_public_log_bridge(int event,
		struct process_vm *vm, struct vm_range *range,
		unsigned long protflag, int error)
{
	switch (event) {
	case PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER:
		dkprintf("change_prot_process_memory_range(%p,%lx-%lx,%lx)\n",
				vm, range ? range->start : 0,
				range ? range->end : 0, protflag);
		break;
	case PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR:
		ekprintf("change_prot_process_memory_range(%p,%lx-%lx,%lx):"
				"ihk_mc_pt_change_attr_range failed: %d\n",
				vm, range ? range->start : 0,
				range ? range->end : 0, protflag, error);
		break;
	case PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT:
		dkprintf("change_prot_process_memory_range(%p,%lx-%lx,%lx): %d\n",
				vm, range ? range->start : 0,
				range ? range->end : 0, protflag, error);
		break;
	}
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int change_prot_process_memory_range(struct process_vm *vm,
		struct vm_range *range, unsigned long protflag)
{
	return process_change_prot_public_result(vm, range, protflag,
			process_change_prot_attr_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_change_prot_pt_change_bridge,
			process_change_prot_public_log_bridge);
}
#endif

struct rfp_args {
	off_t off;
	uintptr_t start;
	struct memobj *memobj;
};

int remap_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		   void *pgaddr, int pgshift)
{
	struct rfp_args * const args = arg0;
	const size_t pgsize = (size_t)1 << pgshift;
	int error;
	off_t off;
	pte_t apte = PTE_NULL;
	uintptr_t phys;
	struct page *page;

	dkprintf("remap_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);

	off = args->off + ((uintptr_t)pgaddr - args->start);
	pte_make_fileoff(off, 0, pgsize, &apte);

	pte_xchg(ptep, &apte);
	flush_tlb_single((uintptr_t)pgaddr);	/* XXX: TLB flush */

	if (pte_is_null(&apte) || pte_is_fileoff(&apte, pgsize)) {
		error = 0;
		goto out;
	}
	phys = pte_get_phys(&apte);

	if (pte_is_dirty(&apte, pgsize)) {
		memobj_flush_page(args->memobj, phys, pgsize);	/* XXX: in lock period */
	}

	page = phys_to_page(phys);
	if (page && page_unmap(page)) {
		_ihk_mc_free_pages(phys_to_virt(phys), pgsize/PAGE_SIZE, IHK_MC_PG_USER, __FILE__, __LINE__);
		dkprintf("%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", phys, __FUNCTION__, pgsize, pgsize);
		rusage_memory_stat_sub(args->memobj, pgsize, pgsize); 
	}

	error = 0;
out:
	dkprintf("remap_one_page(%p,%p,%p %#lx,%p,%d): %d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}

int process_visit_pte_range_bridge(void *page_table, unsigned long start,
				   unsigned long end, int pgshift, int flags,
				   void *visit_fn, void *arg)
{
	return visit_pte_range(page_table, (void *)start, (void *)end,
			pgshift, flags,
			(int (*)(void *, page_table_t, pte_t *, void *, int))
			visit_fn, arg);
}

void process_remap_range_log_bridge(int event, struct process_vm *vm,
				    struct vm_range *range, unsigned long start,
				    unsigned long end, long off,
				    int old_pgshift, int error)
{
	switch (event) {
	case PROCESS_REMAP_RANGE_LOG_PGSHIFT:
		ekprintf("%s: pgshift is too big (%d)  failed:%d\n",
				"remap_process_memory_range", old_pgshift, error);
		break;
	case PROCESS_REMAP_RANGE_LOG_VISIT_FAILED:
		ekprintf("remap_process_memory_range(%p,%p,%#lx,%#lx,%#lx):"
				"visit pte failed %d\n",
				vm, range, start, end, off, error);
		break;
	}
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int remap_process_memory_range(struct process_vm *vm, struct vm_range *range,
		uintptr_t start, uintptr_t end, off_t off)
{
	struct rfp_args args;
	int error;

	dkprintf("remap_process_memory_range(%p,%p,%#lx,%#lx,%#lx)\n",
			vm, range, start, end, off);
	args.start = start;
	args.off = off;
	args.memobj = range->memobj;

	error = process_remap_memory_range_body_result(vm, range, start, end,
			off, &args, remap_one_page,
			process_free_range_noirq_lock_bridge,
			process_free_range_noirq_unlock_bridge,
			process_visit_pte_range_bridge,
			process_remap_range_log_bridge);
	dkprintf("remap_process_memory_range(%p,%p,%#lx,%#lx,%#lx):%d\n",
			vm, range, start, end, off, error);
	return error;
}
#endif

struct sync_args {
	struct memobj *memobj;
};

int sync_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		  void *pgaddr, int pgshift)
{
	struct sync_args *args = arg0;
	const size_t pgsize = (size_t)1 << pgshift;
	int error;
	uintptr_t phys;

	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);
	if (pte_is_null(ptep) || pte_is_fileoff(ptep, pgsize)
			|| !pte_is_dirty(ptep, pgsize)) {
		error = 0;
		goto out;
	}

	pte_clear_dirty(ptep, pgsize);
	flush_tlb_single((uintptr_t)pgaddr);	/* XXX: TLB flush */

	phys = pte_get_phys(ptep);
	if (args->memobj->flags & MF_ZEROFILL) {
		error = 0;
		goto out;
	}

	error = memobj_flush_page(args->memobj, phys, pgsize);
	if (error) {
		ekprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):"
				"flush failed. %d\n",
				arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
		pte_set_dirty(ptep, pgsize);
		goto out;
	}

	error = 0;
out:
	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}

void process_sync_range_log_bridge(struct process_vm *vm,
				   struct vm_range *range, unsigned long start,
				   unsigned long end, int error)
{
	ekprintf("sync_process_memory_range(%p,%p,%#lx,%#lx):"
			"visit failed%d\n", vm, range, start, end, error);
}

void *process_lookup_pte_bridge(void *page_table, unsigned long addr,
		int pgshift, size_t *pgsizep)
{
	return ihk_mc_pt_lookup_pte(page_table, (void *)addr, pgshift, NULL,
			pgsizep, NULL);
}

int process_pte_is_contiguous_bridge(void *ptep)
{
	return pte_is_contiguous((pte_t *)ptep);
}

int process_page_is_contiguous_head_bridge(void *ptep, size_t pgsize)
{
	return page_is_contiguous_head((pte_t *)ptep, pgsize);
}

int process_page_is_contiguous_tail_bridge(void *ptep, size_t pgsize)
{
	return page_is_contiguous_tail((pte_t *)ptep, pgsize);
}

int process_split_contiguous_pages_bridge(void *ptep, size_t pgsize,
		unsigned int memobj_flags)
{
	return split_contiguous_pages((pte_t *)ptep, pgsize, memobj_flags);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int sync_process_memory_range(struct process_vm *vm, struct vm_range *range,
		uintptr_t start, uintptr_t end)
{
	int error;
	struct sync_args args;

	dkprintf("sync_process_memory_range(%p,%p,%#lx,%#lx)\n",
			vm, range, start, end);
	args.memobj = range->memobj;

	error = process_sync_memory_range_body_result(vm, range, start, end,
			&args, sync_one_page,
			process_free_range_noirq_lock_bridge,
			process_free_range_noirq_unlock_bridge,
			process_visit_pte_range_bridge,
			process_sync_range_log_bridge);
	dkprintf("sync_process_memory_range(%p,%p,%#lx,%#lx):%d\n",
			vm, range, start, end, error);
	return error;
}
#endif

void process_invalidate_range_log_bridge(struct process_vm *vm,
		struct vm_range *range, unsigned long start, unsigned long end,
		int error)
{
	ekprintf("invalidate_process_memory_range(%p,%p,%#lx,%#lx):"
			"visit failed%d\n", vm, range, start, end, error);
}

struct invalidate_args {
	struct vm_range *range;
};

int process_pte_is_null_bridge(void *ptep)
{
	return pte_is_null((pte_t *)ptep);
}

int process_pte_is_fileoff_bridge(void *ptep, size_t pgsize)
{
	return pte_is_fileoff((pte_t *)ptep, pgsize);
}

uintptr_t process_pte_get_phys_bridge(void *ptep)
{
	return pte_get_phys((pte_t *)ptep);
}

void *process_phys_to_page_bridge(uintptr_t phys)
{
	return phys_to_page(phys);
}

long process_page_offset_bridge(void *page)
{
	return ((struct page *)page)->offset;
}

void process_pte_make_fileoff_bridge(long off, size_t pgsize,
					    void *ptep)
{
	pte_make_fileoff(off, 0, pgsize, (pte_t *)ptep);
}

void process_pte_xchg_bridge(void *ptep, void *valp)
{
	pte_xchg((pte_t *)ptep, (pte_t *)valp);
}

void process_flush_tlb_single_bridge(unsigned long addr)
{
	flush_tlb_single(addr);
}

int process_pgsize_to_tbllv_bridge(size_t pgsize)
{
	return pgsize_to_tbllv(pgsize);
}

size_t process_tbllv_to_contpgsize_bridge(int level)
{
	return tbllv_to_contpgsize(level);
}

int process_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}

void process_panic_bridge(const char *message)
{
	panic(message);
}

int process_memobj_invalidate_page_bridge(struct memobj *memobj,
						 uintptr_t phys,
						 size_t pgsize)
{
	return memobj_invalidate_page(memobj, phys, pgsize);
}

void process_invalidate_one_page_log_bridge(void *arg0,
		void *page_table, void *ptep, unsigned long pte_value,
		void *pgaddr, int pgshift, int error)
{
	ekprintf("invalidate_one_page(%p,%p,%p %#lx,%p,%d):"
			"invalidate failed. %d\n",
			arg0, page_table, ptep, pte_value, pgaddr, pgshift,
			error);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int invalidate_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		void *pgaddr, int pgshift)
{
	int error;

	dkprintf("invalidate_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);
	error = process_invalidate_one_page_body_result(arg0, pt, ptep,
			pgaddr, pgshift, process_pte_is_null_bridge,
			process_pte_is_fileoff_bridge,
			process_pte_get_phys_bridge, process_phys_to_page_bridge,
			process_page_offset_bridge,
			process_pte_make_fileoff_bridge, process_pte_xchg_bridge,
			process_flush_tlb_single_bridge,
			process_pte_is_contiguous_bridge,
			process_page_is_contiguous_head_bridge,
			process_pgsize_to_tbllv_bridge,
			process_tbllv_to_contpgsize_bridge,
			process_page_unmap_bridge, process_panic_bridge,
			process_memobj_invalidate_page_bridge,
			process_invalidate_one_page_log_bridge);
	// memory_stat_rss_sub() is called in downstream, i.e. shmobj_invalidate_page()

	dkprintf("invalidate_one_page(%p,%p,%p %#lx,%p,%d):%d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int invalidate_process_memory_range(struct process_vm *vm,
		struct vm_range *range, uintptr_t start, uintptr_t end)
{
	int error;
	struct invalidate_args args;

	dkprintf("invalidate_process_memory_range(%p,%p,%#lx,%#lx)\n",
			vm, range, start, end);
	args.range = range;

	error = process_invalidate_memory_range_body_result(vm, range, start,
			end, &args, invalidate_one_page,
			process_free_range_noirq_lock_bridge,
			process_free_range_noirq_unlock_bridge,
			process_lookup_pte_bridge,
			process_pte_is_contiguous_bridge,
			process_page_is_contiguous_head_bridge,
			process_page_is_contiguous_tail_bridge,
			process_split_contiguous_pages_bridge,
			process_free_range_pt_free_bridge,
			process_visit_pte_range_bridge,
			process_invalidate_range_log_bridge);
	// memory_stat_rss_sub() is called downstream, i.e. invalidate_one_page() to deal with empty PTEs

	dkprintf("invalidate_process_memory_range(%p,%p,%#lx,%#lx):%d\n",
			vm, range, start, end, error);
	return error;
}
#endif

int page_fault_process_memory_range(struct process_vm *vm,
				    struct vm_range *range,
				    uintptr_t fault_addr, uint64_t reason)
{
	int error;
	pte_t *ptep;
	void *pgaddr;
	size_t pgsize;
	int p2align;
	enum ihk_mc_pt_attribute attr;
	uintptr_t phys;
	struct page *page = NULL;
	unsigned long memobj_flag = 0;
	int private_range, patching_to_rdonly;
	int devfile_or_hugetlbfs_or_premap, regfile_or_shm;

	if (get_this_cpu_local_var()->current->profile) {
		dkprintf("%s: 0x%lx @ %s\n",
				__func__, fault_addr,
				range->memobj && range->memobj->path ?
				range->memobj->path :
				range->private_data ? "XPMEM" : "<unknown>");
	}

	dkprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx)\n", vm, range->start, range->end, range->flag, fault_addr, reason);
	ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);
	/*****/
	ptep = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
			(void *)fault_addr, range->pgshift, &pgaddr, &pgsize,
			&p2align);
	if (!(reason & (PF_PROT | PF_PATCH)) && ptep && !pte_is_null(ptep)
			&& !pte_is_fileoff(ptep, pgsize)) {
		if (!pte_is_present(ptep)) {
			error = -EFAULT;
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):PROT_NONE. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		error = 0;
		goto out;
	}
	if ((reason & PF_PROT) && (!ptep || !pte_is_present(ptep))) {
		flush_tlb_single(fault_addr);
		error = 0;
		goto out;
	}
	/*****/
	dkprintf("%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\n", __FUNCTION__, pgaddr, range->start, range->end, pgaddr + pgsize);
	while (((uintptr_t)pgaddr < range->start)
			|| (range->end < ((uintptr_t)pgaddr + pgsize))) {
		ptep = NULL;
		error = arch_get_smaller_page_size(NULL, pgsize, &pgsize, &p2align);
		if (error) {
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(pte) failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		pgaddr = (void *)(fault_addr & ~(pgsize - 1));
	}

	arch_adjust_allocate_page_size(vm->address_space->page_table,
				       fault_addr, ptep, &pgaddr, &pgsize);

	/*****/
	dkprintf("%s: ptep=%lx,pte_is_null=%d,pte_is_fileoff=%d\n", __FUNCTION__, ptep, ptep ? pte_is_null(ptep) : -1, ptep ? pte_is_fileoff(ptep, pgsize) : -1);
	if (!ptep || pte_is_null(ptep) || pte_is_fileoff(ptep, pgsize)) {
		phys = NOPHYS;
		if (range->memobj) {
			off_t off;

			if (!ptep || !pte_is_fileoff(ptep, pgsize)) {
				off = range->objoff + ((uintptr_t)pgaddr - range->start);
			}
			else {
				off = pte_get_off(ptep, pgsize);
			}
			error = memobj_get_page(range->memobj, off, p2align,
                                       &phys, &memobj_flag, fault_addr);
			if (error) {
				struct memobj *obj;

				if (zeroobj_create(&obj)) {
					panic("PFPMR: zeroobj_crate");
				}

				if (range->memobj != obj) {
					goto out;
				}
			}
			// memory_stat_rss_add() is called downstream, i.e. memobj_get_page() to check page->count
		}
		if (phys == NOPHYS) {
			void *virt = NULL;
			size_t npages;

retry:
			npages = pgsize / PAGE_SIZE;
			virt = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT |
					((range->flag & VR_AP_USER) ? IHK_MC_AP_USER : 0), -1, IHK_MC_PG_USER, fault_addr, __FILE__, __LINE__);
			if (!virt && !range->pgshift && (pgsize != PAGE_SIZE)) {
				error = arch_get_smaller_page_size(NULL, pgsize, &pgsize, &p2align);
				if (error) {
					kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(anon) failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
					goto out;
				}
				ptep = NULL;
				pgaddr = (void *)(fault_addr & ~(pgsize - 1));
				goto retry;
			}
			if (!virt) {
				error = -ENOMEM;
				kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate new page. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
				goto out;
			}
			dkprintf("%s: clearing 0x%lx:%lu\n",
					__FUNCTION__, pgaddr, pgsize);
#ifdef PROFILE_ENABLE
			profile_event_add(PROFILE_page_fault_anon_clr, pgsize);
#endif // PROFILE_ENABLE
			memset(virt, 0, pgsize);
			phys = virt_to_phys(virt);
			if (phys_to_page(phys)) {
				dkprintf("%s: NOPHYS,phys=%lx,vmr(%lx-%lx),flag=%x,fa=%lx,reason=%x\n",
						 __FUNCTION__, page_to_phys(page),
						 range->start, range->end, range->flag, fault_addr, reason);
				
				page_map(phys_to_page(phys));
			}
		}
	}
	else {
		phys = pte_get_phys(ptep);
	}

	page = phys_to_page(phys);

	attr = arch_vrflag_to_ptattr(range->flag | memobj_flag, reason, ptep);

	/* Copy on write */

	private_range = (range->flag & VR_PRIVATE);
	patching_to_rdonly =
		((reason & PF_PATCH) && !(range->flag & VR_PROT_WRITE));

	/* device file map, hugetlbfs file map, pre-mapped file map */
	devfile_or_hugetlbfs_or_premap =
		(!page &&
		 (range->memobj && !(range->memobj->flags | MF_ZEROOBJ)));

	/* regular file map, Sys V shared memory map */
	regfile_or_shm =
		(page &&
		 (page_is_in_memobj(page) || page_is_multi_mapped(page)));

	if ((private_range || patching_to_rdonly) &&
	    (devfile_or_hugetlbfs_or_premap || regfile_or_shm)) {

		if (!(attr & PTATTR_DIRTY)) {
			attr &= ~PTATTR_WRITABLE;
		}
		else {
			void *virt;
			size_t npages;

			if (!page) {
				kprintf("%s: WARNING: cow on non-struct-page-managed page\n", __FUNCTION__);
			}

			npages = pgsize / PAGE_SIZE;
			virt = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_USER, fault_addr, __FILE__, __LINE__);
			if (!virt) {
				error = -ENOMEM;
				kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate copy page. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
				goto out;
			}
			dkprintf("%s: cow,copying virt:%lx<-%lx,phys:%lx<-%lx,pgsize=%lu\n",
					 __FUNCTION__, virt, phys_to_virt(phys), virt_to_phys(virt), phys, pgsize);
			memcpy(virt, phys_to_virt(phys), pgsize);

			/* Count COW-source pointed-to by only fileobj
			 *  The steps in test/rusage/005:
			 *  (1) Private-map regular file
			 *  (2) Don't touch the page
			 *  (3) Fork and then the child touches the page
			 *  (4) Page-in the COW-source
			 *  (5) Reach here
			 */
			if (rusage_memory_stat_add(range, phys, pgsize, pgsize)) {
				dkprintf("%lx+,%s: COW-source pointed-to by only fileobj, calling memory_stat_rss_add(),pgsize=%ld\n",
						phys, __FUNCTION__, pgsize);
			}
			if (page) {
				if (page_unmap(page)) {
					dkprintf("%lx-,%s: cow,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", phys, __FUNCTION__, pgsize, pgsize);
					rusage_memory_stat_sub(range->memobj, pgsize, pgsize); 
				}
			}
			phys = virt_to_phys(virt);
			page = phys_to_page(phys);
		}
	}
	else if (!(range->flag & VR_PRIVATE)) { /*VR_SHARED*/
		if (!(attr & PTATTR_DIRTY)) {
			if (!(range->flag & VR_STACK)) {
				attr &= ~PTATTR_WRITABLE;
			}
		}
	}

	/*****/
	if (ptep && !pgsize_is_contiguous(pgsize)) {
		if (!(reason & PF_PATCH) &&
		    rusage_memory_stat_add(range, phys, pgsize, pgsize)) {
			/* on-demand paging, phys pages are obtained by ihk_mc_alloc_aligned_pages_user() or get_page() */
			dkprintf("%lx+,%s: (on-demand paging && first map) || cow,calling memory_stat_rss_add(),phys=%lx,pgsize=%ld\n",
					 phys, __FUNCTION__, phys, pgsize);
		} else {
			dkprintf("%s: !calling memory_stat_rss_add(),phys=%lx,pgsize=%ld\n",
					 __FUNCTION__, phys, pgsize);
		}

		dkprintf("%s: attr=%x\n", __FUNCTION__, attr);
		error = ihk_mc_pt_set_pte(vm->address_space->page_table, ptep,
		                          pgsize, phys, attr);
		if (error) {
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):set_pte failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		dkprintf("%s: non-NULL pte,page=%lx,page_is_in_memobj=%d,page->count=%d\n", __FUNCTION__, page, page ? page_is_in_memobj(page) : 0, page ? ihk_atomic_read(&page->count) : 0);
	}
	else {
		error = ihk_mc_pt_set_range(vm->address_space->page_table, vm,
		                            pgaddr, pgaddr + pgsize, phys,
					    attr, range->pgshift, range, 1);
		if (error) {
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):set_range failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		// memory_stat_rss_add() is called in downstream with !memobj check
	}
	flush_tlb_single(fault_addr);

	error = 0;
	page = NULL;

out:
	ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);
	if (page) {
		/* Unmap stray struct page */
		dkprintf("%s: out,phys=%lx,vmr(%lx-%lx),flag=%x,fa=%lx,reason=%x\n",
				 __FUNCTION__, page_to_phys(page),
				 range->start, range->end, range->flag, fault_addr, reason);
		if (page_unmap(page)) {
			dkprintf("%lx-,%s: out,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", page_to_phys(page), __FUNCTION__, pgsize, pgsize);
			rusage_memory_stat_sub(range->memobj, pgsize, pgsize); 
		}
	}
	dkprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx): %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
	return error;
}

int process_zeroobj_match_bridge(void *memobj)
{
	struct memobj *obj;

	if (zeroobj_create(&obj)) {
		panic("DPFP: zeroobj_crate");
	}
	return memobj == obj;
}

int process_normal_fault_range_bridge(struct process_vm *vm,
				      struct vm_range *range,
				      unsigned long fault_addr,
				      unsigned long reason)
{
	return page_fault_process_memory_range(vm, range, fault_addr, reason);
}

int process_xpmem_fault_range_bridge(struct process_vm *vm,
				     struct vm_range *range,
				     unsigned long fault_addr,
				     unsigned long reason)
{
	return xpmem_fault_process_memory_range(vm, range, fault_addr, reason);
}

static int do_page_fault_process_vm(struct process_vm *vm, void *fault_addr0, uint64_t reason)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return process_do_page_fault_vm_body_result(vm, thread->vm,
			(uintptr_t)fault_addr0, reason, ihk_mc_get_processor_id(),
			process_rw_read_lock_bridge,
			process_rw_read_unlock_bridge,
			process_rw_write_lock_bridge,
			process_rw_write_unlock_bridge,
			process_zeroobj_match_bridge,
			process_normal_fault_range_bridge,
			process_xpmem_fault_range_bridge);
}

static int process_do_page_fault_process_vm_bridge(struct process_vm *vm,
						   unsigned long fault_addr,
						   unsigned long reason)
{
	return do_page_fault_process_vm(vm, (void *)fault_addr, reason);
}

void process_pgio_dispatch_bridge(void *fp, void *arg)
{
	((pgio_func_t *)fp)(arg);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int page_fault_process_vm(struct process_vm *fault_vm, void *fault_addr, uint64_t reason)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return process_page_fault_vm_retry_body_result(fault_vm,
			(uintptr_t)fault_addr, reason, thread,
			__builtin_offsetof(struct thread, pgio_fp),
			__builtin_offsetof(struct thread, pgio_arg),
			process_do_page_fault_process_vm_bridge,
			preempt_enable, preempt_disable,
			process_pgio_dispatch_bridge);
}
#endif

static void *process_init_stack_alloc_aligned_bridge(int npages, int p2align,
		unsigned long flags, unsigned long virt_addr)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flags, -1, IHK_MC_PG_USER, virt_addr, __FILE__, __LINE__);
}

static void process_init_stack_free_pages_bridge(void *addr, int npages)
{
	_ihk_mc_free_pages(addr, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
}

static int process_init_stack_add_range_bridge(struct process_vm *vm,
		unsigned long start, unsigned long end, unsigned long phys,
		unsigned long flag, int pgshift, struct vm_range **rangep)
{
	struct vm_range *range = NULL;
	int rc;

	rc = add_process_memory_range(vm, start, end, phys, flag, NULL, 0,
			pgshift, NULL, &range);
	if (rangep)
		*rangep = range;
	return rc;
}

static unsigned long process_init_stack_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

static unsigned long process_init_stack_attr_bridge(unsigned long flag,
		unsigned long fault, void *ptep)
{
	return arch_vrflag_to_ptattr(flag, fault, ptep);
}

static int process_init_stack_pt_set_range_bridge(void *page_table,
		struct process_vm *vm, unsigned long start, unsigned long end,
		unsigned long phys, unsigned long attr, int pgshift,
		struct vm_range *range, int flags)
{
	return ihk_mc_pt_set_range(page_table, vm, (void *)start, (void *)end,
			phys, attr, pgshift, range, flags);
}

static unsigned long process_init_stack_hwcap_bridge(void)
{
	return arch_get_hwcap();
}

static void process_init_stack_modify_context_bridge(void *uctx, int reg,
		unsigned long value)
{
	ihk_mc_modify_user_context(uctx, reg, value);
}

static void process_init_stack_log_bridge(int event,
		const unsigned long *args)
{
	const unsigned long arg0 = args ? args[0] : 0;
	const unsigned long arg1 = args ? args[1] : 0;
	const unsigned long arg2 = args ? args[2] : 0;
	const unsigned long arg3 = args ? args[3] : 0;
	const unsigned long arg4 = args ? args[4] : 0;
	const unsigned long arg5 = args ? args[5] : 0;
	const unsigned long arg6 = args ? args[6] : 0;
	const unsigned long arg7 = args ? args[7] : 0;
	const unsigned long arg8 = args ? args[8] : 0;
	const unsigned long arg9 = args ? args[9] : 0;
	const unsigned long arg10 = args ? args[10] : 0;
	const unsigned long arg11 = args ? args[11] : 0;

	switch (event) {
	case PROCESS_INIT_STACK_LOG_SIZE:
		dkprintf("%s: stack_premap: %lu, rlim_cur: %lu, minsz: %lu, size: %lu, maxsz: %lx\n",
				"init_process_stack", arg0, arg1, arg2, arg3,
				arg4);
		break;
	case PROCESS_INIT_STACK_LOG_AP_USER:
		dkprintf("%s: max size: %lu, mapped size: %lu %s\n",
				"init_process_stack", arg0, arg1,
				arg2 ? "(IHK_MC_AP_USER)" : "");
		break;
	case PROCESS_INIT_STACK_LOG_ALLOC_FAILED:
		kprintf("%s: error: couldn't allocate initial stack\n",
				"init_process_stack");
		break;
	case PROCESS_INIT_STACK_LOG_ADD_FAILED:
		kprintf("%s: error addding process memory range: %d\n",
				"init_process_stack", (int)arg0);
		break;
	case PROCESS_INIT_STACK_LOG_PT_FAILED:
		kprintf("init_process_stack:set range %lx-%lx %lx failed. %d\n",
				arg0, arg1, arg2, (int)arg3);
		break;
	case PROCESS_INIT_STACK_LOG_AUXV:
		kprintf("mcexec_v10: auxv pid=%d tid=%d entry=0x%lx base=0x%lx phdr=0x%lx vdso=0x%lx pagesz=%lu at_random=0x%lx stack_top=0x%lx argc=%d envc=%d\n",
				(int)arg0, (int)arg1, arg2, arg3, arg4,
				arg5, arg6, arg7, arg8, (int)arg9,
				(int)arg10);
		break;
	case PROCESS_INIT_STACK_LOG_SIZE_MISMATCH:
		kprintf("%s: WARNING: stack_populated_size mismatch (is AUXV_LEN up-to-date?): &p[s_ind]: %lu, computed: %lu\n",
				"init_process_stack", arg0, arg1);
		break;
	case PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH:
		kprintf("%s: WARNING: stack alignment mismatch\n",
				"init_process_stack");
		break;
	case PROCESS_INIT_STACK_LOG_INITIAL:
		kprintf("mcexec_v10: initial_stack pid=%d tid=%d sp=0x%lx argc_slot=%lu argv0_slot=0x%lx argv_null=0x%lx env0_slot=0x%lx env_null=0x%lx aux0_tag=0x%lx aux0_val=0x%lx\n",
				(int)arg0, (int)arg1, arg2, arg3, arg4,
				arg5, arg6, arg7, arg8, arg9);
		break;
	default:
		(void)arg11;
		break;
	}
}

int init_process_stack(struct thread *thread, struct program_load_desc *pn,
                        unsigned long at_base, int argc, char **argv,
                        int envc, char **env)
{
	unsigned long stack_alloc_size_override = 0;

#ifdef ENABLE_FUGAKU_HACKS
	/*
	 * XXX: Fugaku: Fujitsu's runtime remaps the stack using hugetlbfs, so
	 * don't bother allocating too much here.
	 */
	stack_alloc_size_override = 8 * 1024 * 1024;
#endif

	return process_init_stack_body_result(thread, pn, at_base, argc, argv,
			envc, env, PAGE_SIZE, PAGE_SHIFT, USER_STACK_PAGE_MASK,
			USER_STACK_PAGE_SHIFT, USER_STACK_PREPAGE_SIZE,
			stack_alloc_size_override, USER_STACK_PAGE_P2ALIGN,
			IHK_MC_AP_NOWAIT, IHK_MC_AP_USER, MPOL_NO_STACK,
			IHK_UCR_STACK_POINTER, PF_POPULATE,
			process_init_stack_alloc_aligned_bridge,
			process_init_stack_free_pages_bridge,
			process_init_stack_add_range_bridge,
			process_init_stack_virt_to_phys_bridge,
			process_init_stack_attr_bridge,
			process_init_stack_pt_set_range_bridge,
			process_init_stack_hwcap_bridge,
			process_init_stack_modify_context_bridge,
			process_init_stack_log_bridge);
}


unsigned long extend_process_region(struct process_vm *vm,
		unsigned long end_allocated,
		unsigned long address, unsigned long flag)
{
	unsigned long new_end_allocated;
	void *p;
	int rc;
	size_t len;
	int npages;
	struct vm_range *range;

	size_t align_size = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_SIZE : PAGE_SIZE;
	unsigned long align_mask = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_MASK : PAGE_MASK;
	unsigned long align_p2align = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_P2ALIGN : PAGE_P2ALIGN;
	int align_shift = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_SHIFT : PAGE_SHIFT;

	new_end_allocated = (address + (PAGE_SIZE - 1)) & PAGE_MASK;
	if ((new_end_allocated - end_allocated) < vm->proc->heap_extension) {
		new_end_allocated = (end_allocated + vm->proc->heap_extension +
				(align_size - 1)) & align_mask;
	}

	/* Check if the range to be extended already exists */
	range = lookup_process_memory_range(vm,
			end_allocated, new_end_allocated);
	if (range) {
		dkprintf("%s: warning: vm_range for extension already exists\n",
				__func__);
		return end_allocated;
	}

	len = new_end_allocated - end_allocated;
	npages = len >> PAGE_SHIFT;

	if (flag & VR_DEMAND_PAGING) {
		p = 0;
	}
	else {
		p = _ihk_mc_alloc_aligned_pages_node(npages, align_p2align, IHK_MC_AP_NOWAIT |
				(!(vm->proc->mpol_flags & MPOL_NO_HEAP) ?
				 IHK_MC_AP_USER : 0), -1, IHK_MC_PG_USER, end_allocated, __FILE__, __LINE__);

		if (!p) {
			dkprintf("%s: warning: failed to allocate %d contiguous pages "
					" (bytes: %lu, pgshift: %d), enabling demand paging\n",
					 __func__, npages, len, align_p2align);

			/* Give demand paging a chance */
			flag |= VR_DEMAND_PAGING;
		}
	}

	if ((rc = add_process_memory_range(vm, end_allocated, new_end_allocated,
					(p == 0 ? 0 : virt_to_phys(p)), flag, NULL, 0,
					align_shift, NULL, NULL)) != 0) {
		_ihk_mc_free_pages(p, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
		return end_allocated;
	}
	// memory_stat_rss_add() is called in add_process_memory_range()

	dkprintf("%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n",
		__FUNCTION__, new_end_allocated, align_size, align_mask);

	return new_end_allocated;
}

// Original version retained because dcfa (src/mccmd/client/ibmic/main.c) calls this
int process_remove_region_clear_bridge(void *page_table,
				       struct process_vm *vm,
				       unsigned long start,
				       unsigned long end);
void process_remove_region_log_bridge(struct process_vm *vm,
				      unsigned long start,
				      unsigned long end);

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int remove_process_region(struct process_vm *vm,
                          unsigned long start, unsigned long end)
{
	return process_remove_region_body_result(vm, start, end,
		process_free_range_noirq_lock_bridge,
		process_free_range_noirq_unlock_bridge,
		process_remove_region_clear_bridge,
		process_remove_region_log_bridge);
}
#endif

int process_remove_region_clear_bridge(void *page_table,
				       struct process_vm *vm,
				       unsigned long start,
				       unsigned long end)
{
	/* We defer freeing to the time of exit */
	// XXX: check error
	return ihk_mc_pt_clear_range(page_table, vm, (void *)start,
				     (void *)end);
}

void process_remove_region_log_bridge(struct process_vm *vm,
				      unsigned long start,
				      unsigned long end)
{
	// memory_stat_rss_sub() isn't called because this execution path is no loger reached
	dkprintf("%s: memory_stat_rss_sub() isn't called,start=%lx,end=%lx\n", __FUNCTION__, start, end);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void flush_process_memory(struct process_vm *vm)
{
	dkprintf("flush_process_memory(%p)\n", vm);
	process_flush_memory_body_result(vm,
		process_rw_write_lock_bridge, process_rw_write_unlock_bridge,
		process_memory_range_free_bridge, process_flush_memory_log_bridge);
	dkprintf("flush_process_memory(%p):\n", vm);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void free_process_memory_ranges(struct process_vm *vm)
{
	if (vm == NULL) {
		return;
	}

	process_free_all_memory_ranges_body_result(vm,
		process_rw_write_lock_bridge, process_rw_write_unlock_bridge,
		process_memory_range_free_bridge,
		process_memory_range_free_log_bridge);
}
#endif

static void free_thread_pages(struct thread *thread)
{
	_ihk_mc_free_pages(thread, KERNEL_STACK_NR_PAGES, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

void process_free_thread_pages_bridge(void *thread)
{
	free_thread_pages(thread);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
hold_process(struct process *proc)
{
	process_ref_hold_body_result(proc,
		__builtin_offsetof(struct process, refcount),
		NULL);
}
#endif

void *process_current_resource_set_bridge(void)
{
	return get_this_cpu_local_var()->resource_set;
}

void process_release_hash_detach_bridge(void *resource_set_arg,
					void *proc_arg)
{
	struct resource_set *resource_set = resource_set_arg;
	struct process *proc = proc_arg;
	struct mcs_rwlock_node_irqsave lock;

	if (process_list_is_linked_result(&proc->hash_list)) {
		struct process_hash *phash = resource_set->process_hash;
		int hash = process_hash(proc->pid);

		mcs_rwlock_writer_lock(&phash->lock[hash], &lock);
		process_list_detach_result(&proc->hash_list);
		mcs_rwlock_writer_unlock(&phash->lock[hash], &lock);
	}
}

void process_release_sibling_detach_bridge(void *proc_arg)
{
	struct process *proc = proc_arg;
	struct process *parent = proc->parent;
	struct mcs_rwlock_node_irqsave lock;

	mcs_rwlock_writer_lock(&parent->children_lock, &lock);
	process_list_detach_result(&proc->siblings_list);
	mcs_rwlock_writer_unlock(&parent->children_lock, &lock);
}

void process_release_profile_bridge(void *proc_arg)
{
#ifdef PROFILE_ENABLE
	struct process *proc = proc_arg;

	if (proc->profile) {
		if (proc->nr_processes) {
			profile_accumulate_and_print_job_events(proc);
		}
		else {
			profile_print_proc_stats(proc);
		}
	}
	profile_dealloc_proc_events(proc);
#else
	(void)proc_arg;
#endif
}

void process_release_final_cleanup_bridge(void *resource_set_arg)
{
	struct resource_set *rset = resource_set_arg;
	struct mcs_rwlock_node_irqsave lock;

	mcs_rwlock_reader_lock(&rset->pid1->children_lock, &lock);
	if (list_empty(&rset->pid1->children_list)) {
#ifdef ENABLE_TOFU
		extern void tof_utofu_finalize(void);

		tof_utofu_finalize();
#endif
		hugefileobj_cleanup();
	}
	mcs_rwlock_reader_unlock(&rset->pid1->children_lock, &lock);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
release_process(struct process *proc)
{
	process_release_process_body_result(proc,
		__builtin_offsetof(struct process, refcount),
		__builtin_offsetof(struct process, tids),
		__builtin_offsetof(struct process, main_thread),
		__builtin_offsetof(struct process, mckfd),
		__builtin_offsetof(struct process, mckfd_lock),
		__builtin_offsetof(struct mckfd, next),
		NULL,
		process_current_resource_set_bridge,
		process_release_hash_detach_bridge,
		process_release_sibling_detach_bridge,
		process_release_profile_bridge,
		process_free_thread_pages_bridge,
		process_spin_lock_bridge,
		process_spin_unlock_bridge,
		process_mckfd_free_bridge,
		process_optional_free_bridge,
		process_release_final_cleanup_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
hold_process_vm(struct process_vm *vm)
{
	process_ref_hold_body_result(vm,
		__builtin_offsetof(struct process_vm, refcount),
		NULL);
}
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_detach_address_space_bridge(void *address_space, int pid);
void process_release_process_bridge(void *proc);
#else
void process_detach_address_space_bridge(void *address_space, int pid)
{
	detach_address_space(address_space, pid);
}

void process_release_process_bridge(void *proc)
{
	release_process(proc);
}
#endif

void process_populate_warn_bridge(struct process_vm *vm,
				  unsigned long addr,
				  unsigned long reason,
				  unsigned long off,
				  size_t len, int error)
{
	ekprintf("%s: WARNING: page_fault_process_vm(): vm: %p, "
			"addr: %lx, reason: %lx, off: %lu, len: %lu returns %d\n",
			"populate_process_memory", vm, addr, reason, off, len,
			error);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
free_all_process_memory_range(struct process_vm *vm)
{
	process_free_all_memory_ranges_body_result(vm,
		process_rw_write_lock_bridge, process_rw_write_unlock_bridge,
		process_memory_range_free_bridge,
		process_memory_range_free_log_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void release_process_vm(struct process_vm *vm)
{
	process_release_vm_body_result(vm,
		__builtin_offsetof(struct process_vm, refcount),
		__builtin_offsetof(struct process_vm, proc),
		__builtin_offsetof(struct process, mckfd),
		__builtin_offsetof(struct process, mckfd_lock),
		__builtin_offsetof(struct mckfd, next),
		__builtin_offsetof(struct mckfd, close_cb),
		__builtin_offsetof(struct process_vm, free_cb),
		__builtin_offsetof(struct process_vm, opt),
		__builtin_offsetof(struct process_vm, address_space),
		__builtin_offsetof(struct process, pid),
		__builtin_offsetof(struct process, vm),
		__builtin_offsetof(struct process_vm,
				   vm_range_numa_policy_tree),
		__builtin_offsetof(struct vm_range_numa_policy,
				   policy_rb_node),
		NULL,
		process_spin_lock_bridge,
		process_spin_unlock_bridge,
		process_flush_vm_bridge,
		process_free_all_ranges_bridge,
		process_detach_address_space_bridge,
		process_release_process_bridge,
		process_policy_free_bridge,
		process_free_vm_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static int process_page_fault_process_vm_bridge(struct process_vm *vm,
						unsigned long addr,
						unsigned long reason)
{
	return page_fault_process_vm(vm, (void *)addr, reason);
}

int populate_process_memory(struct process_vm *vm, void *start, size_t len)
{
	const int reason = PF_USER | PF_POPULATE;

	return process_populate_memory_body_result(vm, (uintptr_t)start, len,
			PAGE_SIZE, reason, process_page_fault_process_vm_bridge,
			preempt_disable, preempt_enable,
			process_populate_warn_bridge);
}
#endif

void process_hold_thread_warn_bridge(void *thread_arg)
{
	struct thread *thread = thread_arg;

	kprintf("hold_thread: WARNING: already exited process,tid=%d\n",
		thread->tid);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int hold_thread(struct thread *thread)
{
	process_hold_thread_body_result(thread,
		__builtin_offsetof(struct thread, status),
		__builtin_offsetof(struct thread, refcount),
		NULL, process_hold_thread_warn_bridge);

	return 0;
}
#endif

void hold_sigcommon(struct sig_common *sigcommon);
void release_sigcommon(struct sig_common *sigcommon);

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
hold_sigcommon(struct sig_common *sigcommon)
{
	process_ref_hold_body_result(sigcommon,
		__builtin_offsetof(struct sig_common, use),
		NULL);
}

void
release_sigcommon(struct sig_common *sigcommon)
{
	process_release_sigcommon_public_body_result(sigcommon,
		__builtin_offsetof(struct sig_common, use),
		__builtin_offsetof(struct sig_common, sigpending),
		__builtin_offsetof(struct sig_pending, list),
		NULL,
		process_optional_free_bridge);
}
#endif

/*
 * Release the TID from the process' TID set corresponding to this thread.
 * NOTE: threads_lock must be held.
 */
void __release_tid(struct process *proc, struct thread *thread) {
	process_release_tid_body_result(proc->tids, proc->nr_tids,
		sizeof(proc->tids[0]),
		__builtin_offsetof(struct mcexec_tid, thread),
		thread, thread->tid, process_release_tid_log_bridge);
}

/* Replace tid specified by thread with tid specified by new_tid */
void __find_and_replace_tid(struct process *proc, struct thread *thread, int new_tid) {
	process_replace_tid_body_result(proc->tids, proc->nr_tids,
		sizeof(proc->tids[0]),
		__builtin_offsetof(struct mcexec_tid, tid),
		__builtin_offsetof(struct mcexec_tid, thread),
		thread, thread->tid, new_tid, process_replace_tid_log_bridge);
}

void process_destroy_thread_hash_detach_bridge(void *thread_arg)
{
	struct thread *thread = thread_arg;
	struct mcs_rwlock_node_irqsave lock;

	if (process_list_is_linked_result(&thread->hash_list)) {
		struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
		int hash = thread_hash(thread->tid);

		mcs_rwlock_writer_lock(&resource_set->thread_hash->lock[hash],
					&lock);
		process_list_detach_result(&thread->hash_list);
		mcs_rwlock_writer_unlock(&resource_set->thread_hash->lock[hash],
					&lock);
	}
}

void process_destroy_thread_time_account_bridge(void *thread_arg)
{
	struct thread *thread = thread_arg;
	struct process *proc = thread->proc;
	struct mcs_rwlock_node_irqsave updatelock;
	struct timespec ats;

	mcs_rwlock_writer_lock(&proc->update_lock, &updatelock);
	tsc_to_ts(thread->system_tsc, &ats);
	ts_add(&thread->proc->stime, &ats);
	tsc_to_ts(thread->user_tsc, &ats);
	ts_add(&thread->proc->utime, &ats);
	mcs_rwlock_writer_unlock(&proc->update_lock, &updatelock);
}

void process_destroy_thread_release_tid_bridge(void *proc_arg,
					       void *thread_arg)
{
	__release_tid(proc_arg, thread_arg);
}

void process_destroy_thread_replace_tid_bridge(void *proc_arg,
					       void *thread_arg,
					       int new_tid)
{
	__find_and_replace_tid(proc_arg, thread_arg, new_tid);
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_release_sigcommon_bridge(void *sigcommon);
#else
void process_release_sigcommon_bridge(void *sigcommon)
{
	release_sigcommon(sigcommon);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void destroy_thread(struct thread *thread)
{
	struct mcs_rwlock_node_irqsave lock;

	process_destroy_thread_body_result(thread,
		__builtin_offsetof(struct thread, proc),
		__builtin_offsetof(struct thread, vm),
		__builtin_offsetof(struct thread, cpu_id),
		__builtin_offsetof(struct thread, siblings_list),
		__builtin_offsetof(struct thread, uti_state),
		__builtin_offsetof(struct thread, uti_refill_tid),
		__builtin_offsetof(struct thread, sigpending),
		__builtin_offsetof(struct thread, sigcommon),
		__builtin_offsetof(struct process, threads_lock),
		__builtin_offsetof(struct process, tids),
		__builtin_offsetof(struct process, main_thread),
		__builtin_offsetof(struct process_vm, address_space),
		__builtin_offsetof(struct address_space, cpu_set),
		__builtin_offsetof(struct address_space, cpu_set_lock),
		__builtin_offsetof(struct sig_pending, list),
		__builtin_offsetof(struct thread, ptrace_debugreg),
		__builtin_offsetof(struct thread, ptrace_recvsig),
		__builtin_offsetof(struct thread, ptrace_sendsig),
		__builtin_offsetof(struct thread, fp_regs),
		__builtin_offsetof(struct thread, coredump_regs),
		num_processors, &lock,
		process_mcs_writer_lock_bridge,
		process_mcs_writer_unlock_bridge,
		process_destroy_thread_hash_detach_bridge,
		process_destroy_thread_time_account_bridge,
		process_destroy_thread_release_tid_bridge,
		process_destroy_thread_replace_tid_bridge,
		process_spin_lock_bridge,
		process_spin_unlock_bridge,
		process_optional_free_bridge,
		release_fp_regs,
		process_release_sigcommon_bridge,
		process_free_thread_pages_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void release_thread(struct thread *thread)
{
	process_release_thread_body_result(thread,
		__builtin_offsetof(struct thread, refcount),
		__builtin_offsetof(struct thread, vm),
		__builtin_offsetof(struct thread, proc),
		NULL,
		process_release_thread_profile_bridge,
		process_procfs_delete_thread_bridge,
		process_destroy_thread_bridge,
		process_release_vm_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void cpu_set(int cpu, cpu_set_t *cpu_set, ihk_spinlock_t *lock)
{
	process_cpu_set_public_result(cpu, (unsigned long)cpu_set,
		(unsigned long)lock, CPU_SETSIZE,
		process_spin_lock_bridge, process_spin_unlock_bridge);
}

void cpu_clear(int cpu, cpu_set_t *cpu_set, ihk_spinlock_t *lock)
{
	process_cpu_clear_public_result(cpu, (unsigned long)cpu_set,
		(unsigned long)lock, CPU_SETSIZE,
		process_spin_lock_bridge, process_spin_unlock_bridge);
}

void cpu_clear_and_set(int c_cpu, int s_cpu,
	cpu_set_t *cpu_set, ihk_spinlock_t *lock)
{
	process_cpu_clear_and_set_public_result(c_cpu, s_cpu,
		(unsigned long)cpu_set, (unsigned long)lock, CPU_SETSIZE,
		process_spin_lock_bridge, process_spin_unlock_bridge);
}
#endif


#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void sched_do_migrate_public(void);
#else
static void do_migrate(void);
#endif

static void idle(void)
{
	struct cpu_local_var *v = get_this_cpu_local_var();
	struct ihk_os_cpu_monitor *monitor = v->monitor;

	/* Release runq_lock before starting the idle loop.
	 * See comments at release_runq_lock().
	 */
	ihk_mc_spinlock_unlock(&(get_this_cpu_local_var()->runq_lock),
			get_this_cpu_local_var()->runq_irqstate);

	if(v->status == CPU_STATUS_RUNNING)
		v->status = CPU_STATUS_IDLE;
	cpu_enable_interrupt();

	while (1) {
		get_this_cpu_local_var()->current->status = PS_STOPPED;
		schedule();
		get_this_cpu_local_var()->current->status = PS_RUNNING;
		cpu_disable_interrupt();

		/* See if we need to migrate a process somewhere */
		if (v->flags & CPU_FLAG_NEED_MIGRATE) {
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
			sched_do_migrate_public();
#else
			do_migrate();
#endif
			v->flags &= ~CPU_FLAG_NEED_MIGRATE;
		}

		/*
		 * XXX: KLUDGE: It is desirable to be resolved in schedule().
		 *
		 * There is a problem which causes wait4(2) hang when
		 * wait4(2) called by a process races with its child process
		 * termination. This is a quick fix for this problem.
		 *
		 * The problem occurrd in the following sequence.
		 * 1) The parent process called schedule() from sys_wait4() to
		 *    wait for an event generated by the child process.
		 * 2) schedule() resumed the idle process because there was no
		 *    runnable process in run queue.
		 * 3) At the moment, the child process began to end. It set
		 *    the parent process runnable, and sent an interrupt to
		 *    the parent process's cpu. But this interrupt had no
		 *    effect because the parent process's cpu had not halted.
		 * 4) The idle process was resumed, and halted for waiting for
		 *    the interrupt that had already been handled.
		 */
		if (v->status == CPU_STATUS_IDLE ||
		    v->status == CPU_STATUS_RESERVED) {
			long s;
			struct thread *t;

			s = ihk_mc_spinlock_lock(&v->runq_lock);
			for (t = ((typeof(*t) *)((char *)((&v->runq)->next) - offsetof(typeof(*t), sched_list))); &t->sched_list != (&v->runq); t = ((typeof(*t) *)((char *)(t->sched_list.next) - offsetof(typeof(*t), sched_list)))) {
				if (t->status == PS_RUNNING) {
					v->status = CPU_STATUS_RUNNING;
					break;
				}
			}
			ihk_mc_spinlock_unlock(&v->runq_lock, s);
		}
		if (v->status == CPU_STATUS_IDLE ||
		    v->status == CPU_STATUS_RESERVED) {
			/* No work to do? Consolidate the kmalloc free list */
			kmalloc_consolidate_free_list();
			ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
			monitor->status = IHK_OS_MONITOR_IDLE;
			get_this_cpu_local_var()->current->status = PS_INTERRUPTIBLE;
			cpu_safe_halt();
			monitor->status = IHK_OS_MONITOR_KERNEL;
			monitor->counter++;
			get_this_cpu_local_var()->current->status = PS_RUNNING;
		}
		else {
			cpu_enable_interrupt();
		}
	}
}

void process_sched_init_context_bridge(void *thread_arg)
{
	struct thread *thread = thread_arg;

	ihk_mc_init_context(&thread->ctx, NULL, idle);
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
int process_sched_save_fp_bridge(void *thread);
#else
int process_sched_save_fp_bridge(void *thread)
{
	return save_fp_regs(thread);
}
#endif

void process_sched_timer_init_bridge(int cpu)
{
#ifdef TIMER_CPU_ID
	if (cpu == TIMER_CPU_ID) {
		init_timers();
		wake_timers_loop();
	}
#else
	(void)cpu;
#endif
}

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_sched_init_panic_bridge(void);
#else
void process_sched_init_panic_bridge(void)
{
	panic("failed to initialize idle process state");
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
struct resource_set *
new_resource_set()
{
	return process_new_resource_set_body_result(sizeof(struct resource_set),
		sizeof(struct process_hash), sizeof(struct thread_hash),
		sizeof(struct process), IHK_MC_AP_NOWAIT, HASH_SIZE, 1,
		process_alloc_bridge, process_optional_free_bridge,
		process_init_process_public_bridge, process_rwlock_init_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
proc_init()
{
	struct resource_set *res = new_resource_set();

	if (!res ||
	    process_proc_init_body_result(res, &resource_set_list,
			(unsigned long)&resource_set_lock, num_processors,
			CPU_SETSIZE, 2, IHK_MC_AP_NOWAIT,
			process_alloc_bridge, process_rwlock_init_bridge) < 0) {
		panic("no mem for resource_set");
	}
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void sched_init(void)
{
	if (process_sched_init_body_result((unsigned long)get_this_cpu_local_var(),
			&resource_set_list, ihk_mc_get_processor_id(),
			process_init_process_public_bridge,
			process_vm_rwspin_init_bridge, process_spin_init_bridge,
			process_sched_init_context_bridge,
			process_sched_save_fp_bridge,
			process_sched_timer_init_bridge) < 0)
		process_sched_init_panic_bridge();
}
#endif

struct migrate_request {
	struct list_head list;
	struct thread *thread;
	struct waitq wq;
};

static const struct sched_migrate_offsets process_sched_migrate_offsets = {
	.req_list_offset = __builtin_offsetof(struct migrate_request, list),
	.req_thread_offset = __builtin_offsetof(struct migrate_request, thread),
	.req_wq_offset = __builtin_offsetof(struct migrate_request, wq),
	.thread_cpu_id_offset = __builtin_offsetof(struct thread, cpu_id),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.cpu_migq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, migq_lock),
	.cpu_migq_offset = __builtin_offsetof(struct cpu_local_var, migq),
	.cpu_runq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_flags_offset = __builtin_offsetof(struct cpu_local_var, flags),
	.cpu_status_offset = __builtin_offsetof(struct cpu_local_var, status),
};

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static const struct sched_do_migrate_offsets process_sched_do_migrate_offsets = {
	.req_list_offset = __builtin_offsetof(struct migrate_request, list),
	.req_thread_offset = __builtin_offsetof(struct migrate_request, thread),
	.req_wq_offset = __builtin_offsetof(struct migrate_request, wq),
	.thread_cpu_id_offset = __builtin_offsetof(struct thread, cpu_id),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.thread_cpu_set_offset = __builtin_offsetof(struct thread, cpu_set),
	.thread_sched_list_offset =
		__builtin_offsetof(struct thread, sched_list),
	.thread_vm_offset = __builtin_offsetof(struct thread, vm),
	.vm_address_space_offset =
		__builtin_offsetof(struct process_vm, address_space),
	.address_space_cpu_set_offset =
		__builtin_offsetof(struct address_space, cpu_set),
	.address_space_cpu_set_lock_offset =
		__builtin_offsetof(struct address_space, cpu_set_lock),
	.cpu_migq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, migq_lock),
	.cpu_migq_offset = __builtin_offsetof(struct cpu_local_var, migq),
	.cpu_runq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_offset = __builtin_offsetof(struct cpu_local_var, runq),
	.cpu_runq_len_offset =
		__builtin_offsetof(struct cpu_local_var, runq_len),
	.cpu_flags_offset = __builtin_offsetof(struct cpu_local_var, flags),
};
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
static const struct sched_runqueue_offsets process_sched_runqueue_offsets = {
	.thread_cpu_id_offset = __builtin_offsetof(struct thread, cpu_id),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_spin_sleep_lock_offset =
		__builtin_offsetof(struct thread, spin_sleep_lock),
	.thread_spin_sleep_offset = __builtin_offsetof(struct thread, spin_sleep),
	.thread_sched_list_offset = __builtin_offsetof(struct thread, sched_list),
	.thread_sigpending_offset = __builtin_offsetof(struct thread, sigpending),
	.thread_sigcommon_offset = __builtin_offsetof(struct thread, sigcommon),
	.sigcommon_sigpending_offset =
		__builtin_offsetof(struct sig_common, sigpending),
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_mod_clone_offset = __builtin_offsetof(struct thread, mod_clone),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_status_offset = __builtin_offsetof(struct process, status),
	.proc_update_lock_offset = __builtin_offsetof(struct process, update_lock),
	.proc_clone_count_offset = __builtin_offsetof(struct process, clone_count),
	.cpu_runq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_irqstate_offset =
		__builtin_offsetof(struct cpu_local_var, runq_irqstate),
	.cpu_current_offset = __builtin_offsetof(struct cpu_local_var, current),
	.cpu_prevpid_offset = __builtin_offsetof(struct cpu_local_var, prevpid),
	.cpu_runq_offset = __builtin_offsetof(struct cpu_local_var, runq),
	.cpu_runq_len_offset = __builtin_offsetof(struct cpu_local_var, runq_len),
	.cpu_runq_reserved_offset =
		__builtin_offsetof(struct cpu_local_var, runq_reserved),
	.cpu_flags_offset = __builtin_offsetof(struct cpu_local_var, flags),
	.cpu_status_offset = __builtin_offsetof(struct cpu_local_var, status),
	.cpu_in_interrupt_offset =
		__builtin_offsetof(struct cpu_local_var, in_interrupt),
	.cpu_nr_ctx_switches_offset =
		__builtin_offsetof(struct cpu_local_var, nr_ctx_switches),
};

void process_sched_rwlock_bridge(unsigned long lock_addr,
				 unsigned long node_addr);
void process_sched_rwunlock_bridge(unsigned long lock_addr,
				   unsigned long node_addr);

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_sched_status_set_bridge(unsigned long status_addr, int status);
void process_sched_set_timer_bridge(int runq_locked);
#else
void process_sched_status_set_bridge(unsigned long status_addr, int status)
{
	xchg4((int *)status_addr, status);
}

void process_sched_set_timer_bridge(int runq_locked)
{
	set_timer(runq_locked);
}
#endif

PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_runq_log_bridge(int event,
					  unsigned long arg0,
					  unsigned long arg1, int arg2,
					  int arg3)
{
	switch (event) {
	case SCHED_RUNQ_LOG_NO_MIGRATION_IRQ:
		kprintf("no migration in IRQ context\n");
		break;
	case SCHED_RUNQ_LOG_WAKE_ENTRY:
		dkprintf("%s: proc->pid=%d, valid_states=%08x, "
			"proc->status=%08x, proc->cpu_id=%d,my cpu_id=%d\n",
			"__sched_wakeup_thread", arg2, arg3,
			((struct thread *)arg0)->status,
			((struct thread *)arg0)->cpu_id,
			ihk_mc_get_processor_id());
		(void)arg1;
		break;
	case SCHED_RUNQ_LOG_SPIN_WAKEUP:
		dkprintf("%s: spin wakeup: cpu_id: %d\n",
			 "__sched_wakeup_thread", arg2);
		break;
	case SCHED_RUNQ_LOG_REMOTE_IPI:
		dkprintf("%s: issuing IPI, thread->cpu_id=%d\n",
			 "__sched_wakeup_thread", arg2);
		(void)arg0;
		(void)arg1;
		(void)arg3;
		break;
	case SCHED_RUNQ_LOG_RUNQ_ADD:
		dkprintf("runq_add_proc(): tid %d added to CPU[%d]'s runq\n",
			 arg2, arg3);
		(void)arg0;
		(void)arg1;
		break;
	case SCHED_RUNQ_LOG_IDLE_HALT:
		dkprintf("%s: idle_halt -> schedule()\n",
			 "spin_sleep_or_schedule");
		(void)arg0;
		(void)arg1;
		(void)arg2;
		(void)arg3;
		break;
	case SCHED_RUNQ_LOG_LOST_WAKEUP:
		dkprintf("%s: caught a lost wake-up!\n",
			 "spin_sleep_or_schedule");
		(void)arg0;
		(void)arg1;
		(void)arg2;
		(void)arg3;
		break;
	case SCHED_RUNQ_LOG_SPIN_WOKEN:
		dkprintf("%s: woken while spinning, cpu: %d, do_schedule: %d\n",
			 "spin_sleep_or_schedule", ihk_ikc_get_processor_id(),
			 arg3);
		(void)arg0;
		(void)arg1;
		(void)arg2;
		break;
	case SCHED_RUNQ_LOG_SLEEP_WOKEN:
		dkprintf("%s: woken while sleeping, cpu: %d\n",
			 "spin_sleep_or_schedule", ihk_ikc_get_processor_id());
		(void)arg0;
		(void)arg1;
		(void)arg2;
		(void)arg3;
		break;
	case SCHED_RUNQ_LOG_NO_PREEMPT:
		kprintf("%s: WARNING can't schedule() while no preemption, cnt: %d\n",
			"schedule", arg2);
		(void)arg0;
		(void)arg1;
		(void)arg3;
		break;
	case SCHED_RUNQ_LOG_CLONE_COUNT:
		dkprintf("%s: clone_count is %d\n", "runq_add_thread", arg2);
		(void)arg0;
		(void)arg1;
		(void)arg3;
		break;
	default:
		break;
	}
}

unsigned long process_sched_irq_save_bridge(void);
void process_sched_irq_restore_bridge(unsigned long irqstate);
void process_sched_zero_free_bridge(void);
void process_sched_pause_bridge(void);
int process_sched_has_signal_bridge(unsigned long thread_addr);
void process_sched_reset_cputime_bridge(void);

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_sched_procfs_create_thread_bridge(unsigned long thread_addr);
int process_sched_counter_inc_bridge(unsigned long counter_addr);
void process_sched_counter_dec_bridge(unsigned long counter_addr);
#else
void process_sched_procfs_create_thread_bridge(unsigned long thread_addr)
{
	procfs_create_thread((struct thread *)thread_addr);
}

int process_sched_counter_inc_bridge(unsigned long counter_addr)
{
	return __sync_add_and_fetch((int *)counter_addr, 1);
}

void process_sched_counter_dec_bridge(unsigned long counter_addr)
{
	__sync_fetch_and_sub((unsigned long *)counter_addr, 1);
}
#endif

void process_sched_rusage_threads_inc_bridge(void);

void process_sched_rusage_debug_bridge(void)
{
#ifdef RUSAGE_DEBUG
	if (rusage.num_threads == 1) {
		int i;

		kprintf("total_memory_usage=%ld\n", rusage.total_memory_usage);
		for (i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
			kprintf("memory_stat_rss[%d]=%ld\n", i,
				rusage.memory_stat_rss[i]);
		}
		for (i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
			kprintf("memory_stat_mapped_file[%d]=%ld\n", i,
				rusage.memory_stat_mapped_file[i]);
		}
	}
#endif
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static void do_migrate(void)
{
	int cur_cpu_id = ihk_mc_get_processor_id();
	struct cpu_local_var *cur_v = get_cpu_local_var(cur_cpu_id);

	sched_do_migrate_body_result(cur_cpu_id, (unsigned long)cur_v,
			CPU_SETSIZE, CPU_FLAG_NEED_RESCHED, IHK_GV_IKC,
			&process_sched_do_migrate_offsets,
			process_spin_lock_bridge, process_spin_unlock_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_sched_cpu_local_bridge,
			process_sched_waitq_wakeup_bridge,
			process_sched_vector_bridge, process_sched_interrupt_bridge,
			process_sched_do_migrate_log_bridge);
}
#endif

void set_timer(int runq_locked)
{
	struct cpu_local_var *v = get_this_cpu_local_var();

	timer_set_timer_body_result((unsigned long)v, time_sharing, runq_locked,
			&process_timer_runtime_offsets,
			process_timer_spin_lock_bridge,
			process_timer_spin_unlock_bridge,
			process_timer_lapic_enable_bridge,
			process_timer_lapic_disable_bridge);
}

/*
 * NOTE: it is assumed that a wait-queue (or futex queue) is
 * set before calling this function.
 * NOTE: one must set thread->spin_sleep to 1 before evaluating
 * the wait condition to avoid lost wake-ups.
 */
void spin_sleep_or_schedule(void)
{
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
	sched_spin_sleep_or_schedule_body_result(
			(unsigned long)get_this_cpu_local_var()->current,
			(unsigned long)get_this_cpu_local_var(),
			ihk_ikc_get_processor_id(), idle_halt,
			CPU_FLAG_NEED_RESCHED,
			&process_sched_runqueue_offsets,
			process_sched_irq_save_bridge,
			process_sched_irq_restore_bridge,
			process_spin_lock_bridge,
			process_spin_unlock_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_sched_schedule_bridge,
			process_sched_zero_free_bridge,
			process_sched_pause_bridge,
			process_sched_has_signal_bridge,
			process_sched_runq_log_bridge);
#else
	struct thread *thread = get_this_cpu_local_var()->current;
	struct cpu_local_var *v;
	int do_schedule = 0;
	int woken = 0;
	long irqstate;

	/* Spinning disabled explicitly */
	if (idle_halt) {
		dkprintf("%s: idle_halt -> schedule()\n", __FUNCTION__);
		goto out_schedule;
	}

	/* Try to spin sleep */
	irqstate = ihk_mc_spinlock_lock(&thread->spin_sleep_lock);
	if (thread->spin_sleep == 0) {
		dkprintf("%s: caught a lost wake-up!\n", __FUNCTION__);
	}
	ihk_mc_spinlock_unlock(&thread->spin_sleep_lock, irqstate);

	for (;;) {
		/* Check if we need to reschedule */
		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(
			&(get_this_cpu_local_var()->runq_lock));
		v = get_this_cpu_local_var();

		if (v->flags & CPU_FLAG_NEED_RESCHED || v->runq_len > 1) {
			v->flags &= ~CPU_FLAG_NEED_RESCHED;
			do_schedule = 1;
		}

		ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
		cpu_restore_interrupt(irqstate);

		/* Check if we were woken up */
		irqstate = ihk_mc_spinlock_lock(&thread->spin_sleep_lock);
		if (thread->spin_sleep == 0) {
			woken = 1;
		}

		/* Indicate that we are not spinning any more */
		if (do_schedule) {
			thread->spin_sleep = 0;
		}
		ihk_mc_spinlock_unlock(&thread->spin_sleep_lock, irqstate);

		if ((!list_empty(&thread->sigpending) ||
		     !list_empty(&thread->sigcommon->sigpending)) &&
		    hassigpending(thread)) {
			woken = 1;
		}

		if (woken) {
			dkprintf("%s: woken while spinning, cpu: %d, do_schedule: %d\n",
				 __func__, ihk_ikc_get_processor_id(), do_schedule);
			if (do_schedule) {
				irqstate = ihk_mc_spinlock_lock(&v->runq_lock);
				v->flags |= CPU_FLAG_NEED_RESCHED;
				ihk_mc_spinlock_unlock(&v->runq_lock, irqstate);
			}
			return;
		}

		if (do_schedule) {
			break;
		}

		ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
		cpu_pause();
	}

out_schedule:
	schedule();
	dkprintf("%s: woken while sleeping, cpu: %d\n",
		 __func__, ihk_ikc_get_processor_id());
#endif
}

void schedule(void)
{
	struct cpu_local_var *v;
	struct thread *next, *prev, *thread = NULL, *tmp = NULL;
	int switch_ctx = 0;
	struct thread *last;
	int prevpid;
	unsigned long irqstate = 0;
	static int mcexec_v10_scheduler_logs;

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
	struct sched_schedule_result schedule_result;
	int action;

	(void)thread;
	(void)tmp;
	(void)switch_ctx;
	(void)irqstate;

	action = sched_schedule_prepare_body_result(
			(unsigned long)get_this_cpu_local_var(),
			(unsigned long)&get_this_cpu_local_var()->idle,
			ihk_atomic_read(&get_this_cpu_local_var()->no_preempt),
			CPU_FLAG_NEED_RESCHED, CPU_FLAG_NEED_MIGRATE,
			PS_RUNNING, PS_INTERRUPTIBLE, PS_EXITED,
			SPAWNING_TO_REMOTE, CPU_STATUS_IDLE,
			CPU_STATUS_RESERVED, &process_sched_runqueue_offsets,
			&schedule_result, process_sched_irq_save_bridge,
			process_sched_irq_restore_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_sched_set_timer_bridge,
			process_sched_reset_cputime_bridge,
			process_sched_has_signal_bridge,
			process_sched_runq_log_bridge);
	if (action != SCHED_SCHEDULE_ACTION_SWITCH) {
		return;
	}

	v = (struct cpu_local_var *)schedule_result.cpu_addr;
	prev = (struct thread *)schedule_result.prev_thread_addr;
	next = (struct thread *)schedule_result.next_thread_addr;
	prevpid = schedule_result.prevpid;

	dkprintf("%s: %d => %d [ctx sws: %lu]\n",
			__func__,
			prev ? prev->tid : 0, next ? next->tid : 0,
			get_this_cpu_local_var()->nr_ctx_switches);
	if (next && next != &get_this_cpu_local_var()->idle &&
	    mcexec_v10_scheduler_logs < 32) {
		kprintf("mcexec_v10: scheduler switch cpu=%d %d=>%d pid=%d rip=0x%lx sp=0x%lx status=%d runq_len=%d\n",
			ihk_mc_get_processor_id(),
			prev ? prev->tid : -1, next->tid,
			next->proc ? next->proc->pid : -1,
			next->uctx ? ihk_mc_syscall_pc(next->uctx) : 0UL,
			next->uctx ? ihk_mc_syscall_sp(next->uctx) : 0UL,
			next->status, v->runq_len);
		mcexec_v10_scheduler_logs++;
	}

	if (prev && prev->ptrace_debugreg) {
		save_debugreg(prev->ptrace_debugreg);
		if (next->ptrace_debugreg == NULL) {
			clear_debugreg();
		}
	}
	if (next->ptrace_debugreg) {
		restore_debugreg(next->ptrace_debugreg);
	}

	/* Take care of floating point registers except for idle process */
	/* Not to save fp_regs when the process ends */
	if (prev && (prev != &get_this_cpu_local_var()->idle
			&& prev->status != PS_EXITED)) {
		save_fp_regs(prev);
	}

	if (next != &get_this_cpu_local_var()->idle) {
		restore_fp_regs(next);
	}

	if (prev && prev->vm->address_space->page_table !=
			next->vm->address_space->page_table)
		ihk_mc_load_page_table(next->vm->address_space->page_table);

	/*
	 * Unless switching to a thread in the same process,
	 * to the idle thread, or to the same process that ran
	 * before the idle, clear the instruction cache.
	 */
	if ((prev && prev->proc != next->proc) &&
			next != &get_this_cpu_local_var()->idle &&
			(prevpid != next->proc->pid ||
				prev != &get_this_cpu_local_var()->idle)) {
		arch_flush_icache_all();
	}

	last = arch_switch_context(prev, next);

	/*
	 * We must hold the lock throughout the context switch, otherwise
	 * an IRQ could deschedule this process between page table loading and
	 * context switching and leave the execution in an inconsistent state.
	 * Since we may be migrated to another core meanwhile, we refer
	 * directly to cpu_local_var.
	 */
	ihk_mc_spinlock_unlock_noirq(&(get_this_cpu_local_var()->runq_lock));
	cpu_restore_interrupt(get_this_cpu_local_var()->runq_irqstate);

	if ((last != NULL) && (last->status == PS_EXITED)) {
		v->prevpid = 0;
		arch_flush_icache_all();
		release_thread(last);
		rusage_num_threads_dec();
#ifdef RUSAGE_DEBUG
		if (rusage.num_threads == 0) {
			int i;

			kprintf("total_memory_usage=%ld\n",
				rusage.total_memory_usage);
			for (i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
				kprintf("memory_stat_rss[%d]=%ld\n", i,
					rusage.memory_stat_rss[i]);
			}
			for (i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
				kprintf(
				   "memory_stat_mapped_file[%d]=%ld\n",
				    i,
				    rusage.memory_stat_mapped_file[i]);
			}
		}
#endif
	}

	/* Have we migrated to another core meanwhile? */
	if (v != get_this_cpu_local_var()) {
		v = get_this_cpu_local_var();
	}
	return;
#else
	if (ihk_atomic_read(&get_this_cpu_local_var()->no_preempt)) {
		kprintf("%s: WARNING can't schedule() while no preemption, cnt: %d\n",
			__func__, ihk_atomic_read(&get_this_cpu_local_var()->no_preempt));

		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(
			&(get_this_cpu_local_var()->runq_lock));
		v = get_this_cpu_local_var();

		v->flags |= CPU_FLAG_NEED_RESCHED;

		ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
		cpu_restore_interrupt(irqstate);
		return;
	}

	irqstate = cpu_disable_interrupt_save();
	ihk_mc_spinlock_lock_noirq(&(get_this_cpu_local_var()->runq_lock));
	get_this_cpu_local_var()->runq_irqstate = irqstate;
	v = get_this_cpu_local_var();

	next = NULL;
	prev = v->current;
	prevpid = v->prevpid;
	
	/* All runnable processes are on the runqueue */
	if (prev && prev != &get_this_cpu_local_var()->idle) {
		process_list_detach_counted_result(&prev->sched_list,
						   &v->runq_len);

		/* Round-robin if not exited yet */
		if (prev->status != PS_EXITED) {
			process_list_add_tail_counted_result(&prev->sched_list,
							     &(v->runq),
							     &v->runq_len);
		}
	}

	/* Switch to idle() when prev is PS_EXITED since it always reaches release_thread() 
	   because it always resumes from just after ihk_mc_switch_context() call. See #1029 */
	if (v->flags & CPU_FLAG_NEED_MIGRATE ||
	    (prev && prev->status == PS_EXITED)) {
		next = &get_this_cpu_local_var()->idle;
	} else {
		/* Pick a new running process or one that has a pending signal */
		for (thread = ((typeof(*thread) *)((char *)((&(v->runq))->next) - offsetof(typeof(*thread), sched_list))), tmp = ((typeof(*thread) *)((char *)(thread->sched_list.next) - offsetof(typeof(*thread), sched_list))); &thread->sched_list != (&(v->runq)); thread = tmp, tmp = ((typeof(*tmp) *)((char *)(tmp->sched_list.next) - offsetof(typeof(*tmp), sched_list)))) {
			if (thread->status == PS_RUNNING &&
			    thread->mod_clone == SPAWNING_TO_REMOTE){
				next = thread;
				break;
			}
			if (thread->status == PS_RUNNING ||
				(thread->status == PS_INTERRUPTIBLE && hassigpending(thread))) {
				if(!next)
					next = thread;
			}
		}

		/* No process? Run idle.. */
		if (!next) {
			next = &get_this_cpu_local_var()->idle;
			v->status = v->runq_len? CPU_STATUS_RESERVED: CPU_STATUS_IDLE;
		}
	}

	if (prev != next) {
		switch_ctx = 1;
		v->prevpid = v->current && v->current->proc ?
			v->current->proc->pid : 0;
		v->current = next;
		reset_cputime();
	}

	set_timer(1);

	if (switch_ctx) {
		++get_this_cpu_local_var()->nr_ctx_switches;
		dkprintf("%s: %d => %d [ctx sws: %lu]\n",
				__func__,
				prev ? prev->tid : 0, next ? next->tid : 0,
				get_this_cpu_local_var()->nr_ctx_switches);
		if (next && next != &get_this_cpu_local_var()->idle &&
		    mcexec_v10_scheduler_logs < 32) {
			kprintf("mcexec_v10: scheduler switch cpu=%d %d=>%d pid=%d rip=0x%lx sp=0x%lx status=%d runq_len=%d\n",
				ihk_mc_get_processor_id(),
				prev ? prev->tid : -1, next->tid,
				next->proc ? next->proc->pid : -1,
				next->uctx ? ihk_mc_syscall_pc(next->uctx) : 0UL,
				next->uctx ? ihk_mc_syscall_sp(next->uctx) : 0UL,
				next->status, v->runq_len);
			mcexec_v10_scheduler_logs++;
		}

		if (prev && prev->ptrace_debugreg) {
			save_debugreg(prev->ptrace_debugreg);
			if (next->ptrace_debugreg == NULL) {
				clear_debugreg();
			}
		}
		if (next->ptrace_debugreg) {
			restore_debugreg(next->ptrace_debugreg);
		}

		/* Take care of floating point registers except for idle process */
		/* Not to save fp_regs when the process ends */
		if (prev && (prev != &get_this_cpu_local_var()->idle
				&& prev->status != PS_EXITED)) {
			save_fp_regs(prev);
		}

		if (next != &get_this_cpu_local_var()->idle) {
			restore_fp_regs(next);
		}

		if (prev && prev->vm->address_space->page_table !=
				next->vm->address_space->page_table)
			ihk_mc_load_page_table(next->vm->address_space->page_table);

		/*
		 * Unless switching to a thread in the same process,
		 * to the idle thread, or to the same process that ran
		 * before the idle, clear the instruction cache.
		 */
		if ((prev && prev->proc != next->proc) &&
				next != &get_this_cpu_local_var()->idle &&
				(prevpid != next->proc->pid ||
					prev != &get_this_cpu_local_var()->idle)) {
			arch_flush_icache_all();
		}

		last = arch_switch_context(prev, next);

		/*
		 * We must hold the lock throughout the context switch, otherwise
		 * an IRQ could deschedule this process between page table loading and
		 * context switching and leave the execution in an inconsistent state.
		 * Since we may be migrated to another core meanwhile, we refer
		 * directly to cpu_local_var.
		 */
		ihk_mc_spinlock_unlock_noirq(&(get_this_cpu_local_var()->runq_lock));
		cpu_restore_interrupt(get_this_cpu_local_var()->runq_irqstate);

		if ((last != NULL) && (last->status == PS_EXITED)) {
			v->prevpid = 0;
			arch_flush_icache_all();
			release_thread(last);
			rusage_num_threads_dec();
#ifdef RUSAGE_DEBUG
			if (rusage.num_threads == 0) {
				int i;

				kprintf("total_memory_usage=%ld\n",
					rusage.total_memory_usage);
				for (i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
					kprintf("memory_stat_rss[%d]=%ld\n", i,
						rusage.memory_stat_rss[i]);
				}
				for (i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
					kprintf(
					   "memory_stat_mapped_file[%d]=%ld\n",
					    i,
					    rusage.memory_stat_mapped_file[i]);
				}
			}
#endif
		}

		/* Have we migrated to another core meanwhile? */
		if (v != get_this_cpu_local_var()) {
			v = get_this_cpu_local_var();
		}
	}
	else {
		ihk_mc_spinlock_unlock_noirq(&(get_this_cpu_local_var()->runq_lock));
		cpu_restore_interrupt(get_this_cpu_local_var()->runq_irqstate);
	}
#endif
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
release_cpuid(int cpuid)
{
	unsigned long irqstate;
	struct cpu_local_var *v = get_cpu_local_var(cpuid);
	irqstate = ihk_mc_spinlock_lock(&runq_reservation_lock);
	ihk_mc_spinlock_lock_noirq(&(v->runq_lock));
	if (!v->runq_len)
		v->status = CPU_STATUS_IDLE;
	__sync_fetch_and_sub(&v->runq_reserved, 1);
	ihk_mc_spinlock_unlock_noirq(&(v->runq_lock));
	ihk_mc_spinlock_unlock(&runq_reservation_lock, irqstate);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void check_need_resched(void)
{
	unsigned long irqstate;
	struct cpu_local_var *v = get_this_cpu_local_var();
	irqstate = ihk_mc_spinlock_lock(&v->runq_lock);
	if (v->flags & CPU_FLAG_NEED_RESCHED) {
		if (v->in_interrupt && (v->flags & CPU_FLAG_NEED_MIGRATE)) {
			kprintf("no migration in IRQ context\n");
			ihk_mc_spinlock_unlock(&v->runq_lock, irqstate);
			return;
		}
		v->flags &= ~CPU_FLAG_NEED_RESCHED;
		ihk_mc_spinlock_unlock(&v->runq_lock, irqstate);
		schedule();
	}
	else {
		ihk_mc_spinlock_unlock(&v->runq_lock, irqstate);
	}
}
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
int __sched_wakeup_thread(struct thread *thread,
		int valid_states, int runq_locked);
#else
int __sched_wakeup_thread(struct thread *thread,
		int valid_states, int runq_locked)
{
	int status;
	unsigned long irqstate;
	struct cpu_local_var *v = get_cpu_local_var(thread->cpu_id);
	struct process *proc = thread->proc;
	struct mcs_rwlock_node updatelock;

	dkprintf("%s: proc->pid=%d, valid_states=%08x, "
			"proc->status=%08x, proc->cpu_id=%d,my cpu_id=%d\n",
			__FUNCTION__,
			proc->pid, valid_states, thread->status,
			thread->cpu_id, ihk_mc_get_processor_id());

	irqstate = ihk_mc_spinlock_lock(&(thread->spin_sleep_lock));
	if (thread->spin_sleep == 1) {
		dkprintf("%s: spin wakeup: cpu_id: %d\n",
				__FUNCTION__, thread->cpu_id);

		status = 0;
	}
	thread->spin_sleep = 0;
	ihk_mc_spinlock_unlock(&(thread->spin_sleep_lock), irqstate);

	if (!runq_locked) {
		irqstate = ihk_mc_spinlock_lock(&(v->runq_lock));
	}

	if (thread->status & valid_states) {
		mcs_rwlock_writer_lock_noirq(&proc->update_lock, &updatelock);
		if (proc->status != PS_EXITED)
			proc->status = PS_RUNNING;
		mcs_rwlock_writer_unlock_noirq(&proc->update_lock, &updatelock);
		xchg4((int *)(&thread->status), PS_RUNNING);
		status = 0;

		/* Make interrupt_exit() call schedule() */
		v->flags |= CPU_FLAG_NEED_RESCHED;

		/* Make sure to check if timer needs to be re-enabled */
		if (thread->cpu_id == ihk_mc_get_processor_id()) {
			set_timer(1);
		}
	}
	else {
		status = -EINVAL;
	}

	if (!runq_locked) {
		ihk_mc_spinlock_unlock(&(v->runq_lock), irqstate);
	}

	if (!status && (thread->cpu_id != ihk_mc_get_processor_id())) {
		dkprintf("%s: issuing IPI, thread->cpu_id=%d\n",
				__FUNCTION__, thread->cpu_id);
		ihk_mc_interrupt_cpu(thread->cpu_id,
		                     ihk_mc_get_vector(IHK_GV_IKC));
	}

	return status;
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int sched_wakeup_thread_locked(struct thread *thread, int valid_states)
{
	return __sched_wakeup_thread(thread, valid_states, 1);
}

int sched_wakeup_thread(struct thread *thread, int valid_states)
{
	return __sched_wakeup_thread(thread, valid_states, 0);
}
#endif


/*
 * 1. Add current process to waitq
 * 2. Queue migration request into the target CPU's queue
 * 3. Kick migration on the CPU
 * 4. Wait for completion of the migration
 *
 * struct migrate_request {
 *     list //migq,
 *     wq,
 *     proc
 * }
 *
 * [expected processing of the target CPU]
 * 1. Interrupted by IPI
 * 2. call schedule() via check_resched()
 * 3. Do migration
 * 4. Wake up this thread
 */
void sched_request_migrate(int cpu_id, struct thread *thread)
{
	struct cpu_local_var *v = get_cpu_local_var(cpu_id);
	struct migrate_request req;
	waitq_entry_t entry;

	waitq_init_locked_entry(&entry, get_this_cpu_local_var()->current);

	/*
	 * NOTES:
	 * - migration queue lock must be held before runqueue lock.
	 * - the lock must be held until migration request is added
	 *   and the target core is notified, otherwise an interrupt
	 *   may deschedule this thread and leave it hanging in
	 *   uninterruptible state forever.
	 */
	sched_request_migrate_body_result(cpu_id, (unsigned long)v,
			(unsigned long)&req, (unsigned long)&entry,
			(unsigned long)thread, ihk_mc_get_processor_id(),
			PS_UNINTERRUPTIBLE, CPU_FLAG_NEED_RESCHED,
			CPU_FLAG_NEED_MIGRATE, CPU_STATUS_RUNNING, IHK_GV_IKC,
			&process_sched_migrate_offsets,
			process_spin_lock_bridge, process_spin_unlock_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_sched_waitq_init_bridge,
			process_sched_waitq_prepare_bridge,
			process_sched_waitq_finish_bridge,
			process_sched_vector_bridge, process_sched_interrupt_bridge,
			process_sched_schedule_bridge,
			process_sched_migrate_log_bridge);
}

/* Runq lock must be held here */
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void __runq_add_thread(struct thread *thread, int cpu_id);
#else
void __runq_add_thread(struct thread *thread, int cpu_id)
{
	struct cpu_local_var *v = get_cpu_local_var(cpu_id);
	process_list_add_tail_counted_result(&thread->sched_list, &v->runq,
					     &v->runq_len);
	v->flags |= CPU_FLAG_NEED_RESCHED;
	thread->cpu_id = cpu_id;
	//thread->proc->status = PS_RUNNING;	/* not set here */
	get_cpu_local_var(cpu_id)->status = CPU_STATUS_RUNNING;

	dkprintf("runq_add_proc(): tid %d added to CPU[%d]'s runq\n", 
             thread->tid, cpu_id);
}
#endif

#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void runq_add_thread(struct thread *thread, int cpu_id);
#else
void runq_add_thread(struct thread *thread, int cpu_id)
{
	struct cpu_local_var *v = get_cpu_local_var(cpu_id);
	unsigned long irqstate;
	irqstate = ihk_mc_spinlock_lock(&runq_reservation_lock);
	ihk_mc_spinlock_lock_noirq(&(v->runq_lock));
	__runq_add_thread(thread, cpu_id);
	__sync_fetch_and_sub(&v->runq_reserved, 1);
	ihk_mc_spinlock_unlock_noirq(&(v->runq_lock));
	ihk_mc_spinlock_unlock(&runq_reservation_lock, irqstate);

	procfs_create_thread(thread);

	__sync_add_and_fetch(&thread->proc->clone_count, 1);
	dkprintf("%s: clone_count is %d\n", __FUNCTION__, thread->proc->clone_count);
	rusage_num_threads_inc();
#ifdef RUSAGE_DEBUG
	if (rusage.num_threads == 1) {
		int i;
		kprintf("total_memory_usage=%ld\n", rusage.total_memory_usage);
		for(i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
			kprintf("memory_stat_rss[%d]=%ld\n", i, rusage.memory_stat_rss[i]);
		}
		for(i = 0; i < IHK_MAX_NUM_PGSIZES; i++) {
			kprintf("memory_stat_mapped_file[%d]=%ld\n", i, rusage.memory_stat_mapped_file[i]);
		}
	}
#endif

	/* Kick scheduler */
	if (cpu_id != ihk_mc_get_processor_id()) {
		ihk_mc_interrupt_cpu(thread->cpu_id,
				ihk_mc_get_vector(IHK_GV_IKC));
	}
}
#endif

/* NOTE: shouldn't remove a running process! */
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void runq_del_thread(struct thread *thread, int cpu_id)
{
	struct cpu_local_var *v = get_cpu_local_var(cpu_id);
	unsigned long irqstate;

	irqstate = ihk_mc_spinlock_lock(&(v->runq_lock));
	process_list_detach_counted_result(&thread->sched_list, &v->runq_len);

	if (!v->runq_len)
		get_cpu_local_var(cpu_id)->status = CPU_STATUS_IDLE;

	ihk_mc_spinlock_unlock(&(v->runq_lock), irqstate);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
struct thread *
find_thread(int pid, int tid)
{
	struct thread_hash *thash = get_this_cpu_local_var()->resource_set->thread_hash;
	int hash = thread_hash(tid);
	struct mcs_rwlock_node_irqsave lock;

	return process_find_thread_body_result(&thash->list[hash],
		(unsigned long)&thash->lock[hash], &lock, pid, tid,
		&process_find_thread_offsets,
		process_mcs_reader_lock_bridge,
		process_mcs_reader_unlock_bridge,
		process_hold_thread_bridge);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
thread_unlock(struct thread *thread)
{
	if(!thread)
		return;
	release_thread(thread);
}
#endif

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
struct process *
find_process(int pid, struct mcs_rwlock_node_irqsave *lock)
{
	struct process_hash *phash = get_this_cpu_local_var()->resource_set->process_hash;
	int hash = process_hash(pid);

	return process_find_process_body_result(&phash->list[hash],
		(unsigned long)&phash->lock[hash], lock, pid,
		&process_find_process_offsets,
		process_mcs_reader_lock_bridge,
		process_mcs_reader_unlock_bridge);
}

void
process_unlock(struct process *proc, struct mcs_rwlock_node_irqsave *lock)
{
	struct process_hash *phash = get_this_cpu_local_var()->resource_set->process_hash;
	int hash;

	if (!proc)
		return;
	hash = process_hash(proc->pid);
	process_unlock_found_process_result(proc, (unsigned long)&phash->lock[hash],
		lock, process_mcs_reader_unlock_bridge);
}
#endif

void
debug_log(unsigned long arg)
{
	struct process *p;
	struct thread *t;
	int i;
	struct mcs_rwlock_node_irqsave lock;
	struct resource_set *rset = get_this_cpu_local_var()->resource_set;
	struct process_hash *phash = rset->process_hash;
	struct thread_hash *thash = rset->thread_hash;
	struct process *pid1 = rset->pid1;
	int found = 0;

	switch(arg){
	    case 1:
		for(i = 0; i < HASH_SIZE; i++){
			__mcs_rwlock_reader_lock(&phash->lock[i], &lock);
			for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
				if (p == pid1)
					continue;
				found++;
				kprintf("pid=%d ppid=%d status=%d ref=%d\n",
					p->pid, p->ppid_parent->pid, p->status,
					p->refcount.counter);
			}
			__mcs_rwlock_reader_unlock(&phash->lock[i], &lock);
		}
		kprintf("%d processes are found.\n", found);
		break;
	    case 2:
		for(i = 0; i < HASH_SIZE; i++){
			__mcs_rwlock_reader_lock(&thash->lock[i], &lock);
			for (t = ((typeof(*t) *)((char *)((&thash->list[i])->next) - offsetof(typeof(*t), hash_list))); &t->hash_list != (&thash->list[i]); t = ((typeof(*t) *)((char *)(t->hash_list.next) - offsetof(typeof(*t), hash_list)))){
				found++;
				kprintf("cpu=%d pid=%d tid=%d status=%d "
					"offload=%d ref=%d ptrace=%08x\n",
					t->cpu_id, t->proc->pid, t->tid,
					t->status, t->in_syscall_offload,
					t->refcount.counter, t->ptrace);
			}
			__mcs_rwlock_reader_unlock(&thash->lock[i], &lock);
		}
		kprintf("%d threads are found.\n", found);
		break;
	    case 3:
		for(i = 0; i < HASH_SIZE; i++){
			for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
				if (p == pid1)
					continue;
				found++;
				kprintf("pid=%d ppid=%d status=%d\n",
				        p->pid, p->ppid_parent->pid, p->status);
			}
		}
		kprintf("%d processes are found.\n", found);
		break;
	    case 4:
		for(i = 0; i < HASH_SIZE; i++){
			for (t = ((typeof(*t) *)((char *)((&thash->list[i])->next) - offsetof(typeof(*t), hash_list))); &t->hash_list != (&thash->list[i]); t = ((typeof(*t) *)((char *)(t->hash_list.next) - offsetof(typeof(*t), hash_list)))){
				found++;
				kprintf("cpu=%d pid=%d tid=%d status=%d\n",
				        t->cpu_id, t->proc->pid, t->tid,
				        t->status);
			}
		}
		kprintf("%d threads are found.\n", found);
		break;
	}
}

void process_access_ok_log_bridge(struct process_vm *vm, int type,
		unsigned long addr, size_t len, int rc)
{
	kprintf("%s: refusing access for request 0x%llx-0x%llx %zu, type=%d, rc=%d\n",
		"access_ok", (unsigned long long)addr,
		(unsigned long long)(addr + len), len, type, rc);
}

#ifndef MCKERNEL_RUST_PROCESS_HELPERS
int access_ok(struct process_vm *vm, int type, uintptr_t addr, size_t len)
{
	return process_access_ok_public_result(vm, type, addr, len,
			process_access_ok_log_bridge);
}
#endif
