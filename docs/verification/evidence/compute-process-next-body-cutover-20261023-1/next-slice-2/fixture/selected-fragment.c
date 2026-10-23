/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Extracted selection only; NOT full process TU. Logging uses the actual current header macro. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
#define PROCESS_SCHED_PUBLIC_BRIDGE
#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
#endif
unsigned long process_spin_lock_bridge(unsigned long);
void process_spin_unlock_bridge(unsigned long,unsigned long);
void process_sched_noirq_lock_bridge(unsigned long);
void process_sched_noirq_unlock_bridge(unsigned long);
void process_sched_waitq_init_bridge(unsigned long);
void process_sched_waitq_prepare_bridge(unsigned long,unsigned long,int);
void process_sched_waitq_finish_bridge(unsigned long,unsigned long);
int process_sched_vector_bridge(int);
void process_sched_interrupt_bridge(int,int);
void process_sched_schedule_bridge(void);
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
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
#endif
PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_migrate_log_bridge(unsigned long thread_addr,
					     int tid, int cpu_id)
{
	(void)thread_addr;
	dkprintf("%s: tid: %d -> cpu: %d\n",
		 "sched_request_migrate", tid, cpu_id);
}
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
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
#endif
