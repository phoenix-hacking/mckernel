/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
const struct sched_runqueue_offsets original_C_runqueue_offsets = {
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
extern const struct sched_runqueue_offsets process_sched_runqueue_offsets;
extern int printf(const char *, ...);
int main(void) {
 if (process_sched_runqueue_offsets.thread_cpu_id_offset != original_C_runqueue_offsets.thread_cpu_id_offset) return 1;
 if (process_sched_runqueue_offsets.thread_tid_offset != original_C_runqueue_offsets.thread_tid_offset) return 1;
 if (process_sched_runqueue_offsets.thread_status_offset != original_C_runqueue_offsets.thread_status_offset) return 1;
 if (process_sched_runqueue_offsets.thread_spin_sleep_lock_offset != original_C_runqueue_offsets.thread_spin_sleep_lock_offset) return 1;
 if (process_sched_runqueue_offsets.thread_spin_sleep_offset != original_C_runqueue_offsets.thread_spin_sleep_offset) return 1;
 if (process_sched_runqueue_offsets.thread_sched_list_offset != original_C_runqueue_offsets.thread_sched_list_offset) return 1;
 if (process_sched_runqueue_offsets.thread_sigpending_offset != original_C_runqueue_offsets.thread_sigpending_offset) return 1;
 if (process_sched_runqueue_offsets.thread_sigcommon_offset != original_C_runqueue_offsets.thread_sigcommon_offset) return 1;
 if (process_sched_runqueue_offsets.sigcommon_sigpending_offset != original_C_runqueue_offsets.sigcommon_sigpending_offset) return 1;
 if (process_sched_runqueue_offsets.thread_proc_offset != original_C_runqueue_offsets.thread_proc_offset) return 1;
 if (process_sched_runqueue_offsets.thread_mod_clone_offset != original_C_runqueue_offsets.thread_mod_clone_offset) return 1;
 if (process_sched_runqueue_offsets.proc_pid_offset != original_C_runqueue_offsets.proc_pid_offset) return 1;
 if (process_sched_runqueue_offsets.proc_status_offset != original_C_runqueue_offsets.proc_status_offset) return 1;
 if (process_sched_runqueue_offsets.proc_update_lock_offset != original_C_runqueue_offsets.proc_update_lock_offset) return 1;
 if (process_sched_runqueue_offsets.proc_clone_count_offset != original_C_runqueue_offsets.proc_clone_count_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_runq_lock_offset != original_C_runqueue_offsets.cpu_runq_lock_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_runq_irqstate_offset != original_C_runqueue_offsets.cpu_runq_irqstate_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_current_offset != original_C_runqueue_offsets.cpu_current_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_prevpid_offset != original_C_runqueue_offsets.cpu_prevpid_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_runq_offset != original_C_runqueue_offsets.cpu_runq_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_runq_len_offset != original_C_runqueue_offsets.cpu_runq_len_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_runq_reserved_offset != original_C_runqueue_offsets.cpu_runq_reserved_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_flags_offset != original_C_runqueue_offsets.cpu_flags_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_status_offset != original_C_runqueue_offsets.cpu_status_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_in_interrupt_offset != original_C_runqueue_offsets.cpu_in_interrupt_offset) return 1;
 if (process_sched_runqueue_offsets.cpu_nr_ctx_switches_offset != original_C_runqueue_offsets.cpu_nr_ctx_switches_offset) return 1;
 printf("RUNQUEUE208 PASS 26 exact fields\n"); return 0;
}
