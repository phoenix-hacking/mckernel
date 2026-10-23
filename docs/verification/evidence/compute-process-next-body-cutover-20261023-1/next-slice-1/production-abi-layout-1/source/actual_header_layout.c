/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual current production C headers/config and source declarations/initializers.
 * GCC9 header-layout scope; this file is NOT the exact GCC14 whole process TU. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
#include <ihk/monitor.h>
#include <string.h>
#include <timer.h>
#define PROCESS_SCHED_PUBLIC_BRIDGE
unsigned long process_timer_spin_lock_bridge(unsigned long lock_addr);
void process_timer_spin_unlock_bridge(unsigned long lock_addr,
					     unsigned long irqstate);
void process_timer_lapic_enable_bridge(unsigned int clocks);
void process_timer_lapic_disable_bridge(void);
unsigned long process_sched_irq_save_bridge(void);
void process_sched_irq_restore_bridge(unsigned long irqstate);
unsigned long process_spin_lock_bridge(unsigned long lock_addr);
void process_spin_unlock_bridge(unsigned long lock_addr,
				unsigned long irqstate);
void process_sched_noirq_lock_bridge(unsigned long lock_addr);
void process_sched_noirq_unlock_bridge(unsigned long lock_addr);
void process_sched_schedule_bridge(void);
void process_sched_zero_free_bridge(void);
void process_sched_pause_bridge(void);
int process_sched_has_signal_bridge(unsigned long thread_addr);
void process_sched_runq_log_bridge(int event,
					  unsigned long arg0,
					  unsigned long arg1, int arg2,
					  int arg3);
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
PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets process_timer_runtime_offsets = {
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
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_spin_lock_bridge),unsigned long (*)(unsigned long)),"process_timer_spin_lock_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_spin_unlock_bridge),void (*)(unsigned long,unsigned long)),"process_timer_spin_unlock_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_lapic_enable_bridge),void (*)(unsigned int)),"process_timer_lapic_enable_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_timer_lapic_disable_bridge),void (*)(void)),"process_timer_lapic_disable_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_irq_save_bridge),unsigned long (*)(void)),"process_sched_irq_save_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_irq_restore_bridge),void (*)(unsigned long)),"process_sched_irq_restore_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_spin_lock_bridge),unsigned long (*)(unsigned long)),"process_spin_lock_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_spin_unlock_bridge),void (*)(unsigned long,unsigned long)),"process_spin_unlock_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_noirq_lock_bridge),void (*)(unsigned long)),"process_sched_noirq_lock_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_noirq_unlock_bridge),void (*)(unsigned long)),"process_sched_noirq_unlock_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_schedule_bridge),void (*)(void)),"process_sched_schedule_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_zero_free_bridge),void (*)(void)),"process_sched_zero_free_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_pause_bridge),void (*)(void)),"process_sched_pause_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_has_signal_bridge),int (*)(unsigned long)),"process_sched_has_signal_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sched_runq_log_bridge),void (*)(int,unsigned long,unsigned long,int,int)),"process_sched_runq_log_bridge actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var*)0)->current),struct thread*),"actual current pointer type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void(*)(int)),"set_timer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&spin_sleep_or_schedule),void(*)(void)),"spin_sleep ABI");
const unsigned long *const M14_C_SPIN = (const unsigned long *)&process_sched_runqueue_offsets;
const unsigned long *const M14_C_TIMER = (const unsigned long *)&process_timer_runtime_offsets;
const unsigned long M14_C_LAYOUT[130] = {
 sizeof(void *),
 sizeof(unsigned long),
 sizeof(int),
 sizeof(struct thread),
 _Alignof(struct thread),
 sizeof(struct cpu_local_var),
 _Alignof(struct cpu_local_var),
 sizeof(struct process),
 _Alignof(struct process),
 sizeof(struct sig_common),
 _Alignof(struct sig_common),
 sizeof(struct timer),
 _Alignof(struct timer),
 __builtin_offsetof(struct cpu_local_var,current),
 __builtin_offsetof(struct thread,cpu_id),
 __builtin_offsetof(struct thread,tid),
 __builtin_offsetof(struct thread,status),
 __builtin_offsetof(struct thread,spin_sleep_lock),
 __builtin_offsetof(struct thread,spin_sleep),
 __builtin_offsetof(struct thread,sched_list),
 __builtin_offsetof(struct thread,sigpending),
 __builtin_offsetof(struct thread,sigcommon),
 __builtin_offsetof(struct sig_common,sigpending),
 __builtin_offsetof(struct thread,proc),
 __builtin_offsetof(struct thread,mod_clone),
 __builtin_offsetof(struct process,pid),
 __builtin_offsetof(struct process,status),
 __builtin_offsetof(struct process,update_lock),
 __builtin_offsetof(struct process,clone_count),
 __builtin_offsetof(struct cpu_local_var,runq_lock),
 __builtin_offsetof(struct cpu_local_var,runq_irqstate),
 __builtin_offsetof(struct cpu_local_var,current),
 __builtin_offsetof(struct cpu_local_var,prevpid),
 __builtin_offsetof(struct cpu_local_var,runq),
 __builtin_offsetof(struct cpu_local_var,runq_len),
 __builtin_offsetof(struct cpu_local_var,runq_reserved),
 __builtin_offsetof(struct cpu_local_var,flags),
 __builtin_offsetof(struct cpu_local_var,status),
 __builtin_offsetof(struct cpu_local_var,in_interrupt),
 __builtin_offsetof(struct cpu_local_var,nr_ctx_switches),
 __builtin_offsetof(struct thread,status),
 __builtin_offsetof(struct thread,sched_list),
 __builtin_offsetof(struct thread,spin_sleep_lock),
 __builtin_offsetof(struct thread,spin_sleep),
 __builtin_offsetof(struct thread,itimer_enabled),
 __builtin_offsetof(struct cpu_local_var,runq_lock),
 __builtin_offsetof(struct cpu_local_var,runq),
 __builtin_offsetof(struct cpu_local_var,runq_len),
 __builtin_offsetof(struct cpu_local_var,current),
 __builtin_offsetof(struct cpu_local_var,timer_enabled),
 __builtin_offsetof(struct cpu_local_var,backlog_list),
 __builtin_offsetof(struct timer,timeout),
 __builtin_offsetof(struct timer,processes),
 __builtin_offsetof(struct timer,list),
 __builtin_offsetof(struct timer,thread),
 sizeof(struct sched_runqueue_offsets),
 _Alignof(struct sched_runqueue_offsets),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_cpu_id_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_tid_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_status_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_spin_sleep_lock_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_spin_sleep_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_sched_list_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_sigpending_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_sigcommon_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,sigcommon_sigpending_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_proc_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,thread_mod_clone_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,proc_pid_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,proc_status_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,proc_update_lock_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,proc_clone_count_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_lock_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_irqstate_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_current_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_prevpid_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_len_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_runq_reserved_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_flags_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_status_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_in_interrupt_offset),
 __builtin_offsetof(struct sched_runqueue_offsets,cpu_nr_ctx_switches_offset),
 sizeof(struct timer_runtime_offsets),
 _Alignof(struct timer_runtime_offsets),
 __builtin_offsetof(struct timer_runtime_offsets,thread_status_offset),
 __builtin_offsetof(struct timer_runtime_offsets,thread_sched_list_offset),
 __builtin_offsetof(struct timer_runtime_offsets,thread_spin_sleep_lock_offset),
 __builtin_offsetof(struct timer_runtime_offsets,thread_spin_sleep_offset),
 __builtin_offsetof(struct timer_runtime_offsets,thread_itimer_enabled_offset),
 __builtin_offsetof(struct timer_runtime_offsets,cpu_runq_lock_offset),
 __builtin_offsetof(struct timer_runtime_offsets,cpu_runq_offset),
 __builtin_offsetof(struct timer_runtime_offsets,cpu_runq_len_offset),
 __builtin_offsetof(struct timer_runtime_offsets,cpu_current_offset),
 __builtin_offsetof(struct timer_runtime_offsets,cpu_timer_enabled_offset),
 __builtin_offsetof(struct timer_runtime_offsets,cpu_backlog_list_offset),
 __builtin_offsetof(struct timer_runtime_offsets,timer_timeout_offset),
 __builtin_offsetof(struct timer_runtime_offsets,timer_waitq_offset),
 __builtin_offsetof(struct timer_runtime_offsets,timer_list_offset),
 __builtin_offsetof(struct timer_runtime_offsets,timer_thread_offset),
 sizeof(__typeof__(&process_timer_spin_lock_bridge)),
 _Alignof(__typeof__(&process_timer_spin_lock_bridge)),
 sizeof(__typeof__(&process_timer_spin_unlock_bridge)),
 _Alignof(__typeof__(&process_timer_spin_unlock_bridge)),
 sizeof(__typeof__(&process_timer_lapic_enable_bridge)),
 _Alignof(__typeof__(&process_timer_lapic_enable_bridge)),
 sizeof(__typeof__(&process_timer_lapic_disable_bridge)),
 _Alignof(__typeof__(&process_timer_lapic_disable_bridge)),
 sizeof(__typeof__(&process_sched_irq_save_bridge)),
 _Alignof(__typeof__(&process_sched_irq_save_bridge)),
 sizeof(__typeof__(&process_sched_irq_restore_bridge)),
 _Alignof(__typeof__(&process_sched_irq_restore_bridge)),
 sizeof(__typeof__(&process_spin_lock_bridge)),
 _Alignof(__typeof__(&process_spin_lock_bridge)),
 sizeof(__typeof__(&process_spin_unlock_bridge)),
 _Alignof(__typeof__(&process_spin_unlock_bridge)),
 sizeof(__typeof__(&process_sched_noirq_lock_bridge)),
 _Alignof(__typeof__(&process_sched_noirq_lock_bridge)),
 sizeof(__typeof__(&process_sched_noirq_unlock_bridge)),
 _Alignof(__typeof__(&process_sched_noirq_unlock_bridge)),
 sizeof(__typeof__(&process_sched_schedule_bridge)),
 _Alignof(__typeof__(&process_sched_schedule_bridge)),
 sizeof(__typeof__(&process_sched_zero_free_bridge)),
 _Alignof(__typeof__(&process_sched_zero_free_bridge)),
 sizeof(__typeof__(&process_sched_pause_bridge)),
 _Alignof(__typeof__(&process_sched_pause_bridge)),
 sizeof(__typeof__(&process_sched_has_signal_bridge)),
 _Alignof(__typeof__(&process_sched_has_signal_bridge)),
 sizeof(__typeof__(&process_sched_runq_log_bridge)),
 _Alignof(__typeof__(&process_sched_runq_log_bridge))
};
