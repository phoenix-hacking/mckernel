/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <cls.h>
#include <timer.h>
#include <sched_helpers.h>
_Static_assert(sizeof(struct timer_runtime_offsets)==120,"genuine15word timer descriptor size");
_Static_assert(__alignof__(struct timer_runtime_offsets)==8,"genuine timer descriptor alignment");
_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8 && sizeof(int)==4,"supported LP64 timer ABI");
_Static_assert(PS_RUNNING==1,"same existing running-state constant");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void (*)(int)),"current timer entry ABI");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, thread_status_offset)==0,"thread_status_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->thread_status_offset),unsigned long),"thread_status_offset original field type");
_Static_assert(__builtin_offsetof(struct thread, status)==4184,"thread_status_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, thread_sched_list_offset)==8,"thread_sched_list_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->thread_sched_list_offset),unsigned long),"thread_sched_list_offset original field type");
_Static_assert(__builtin_offsetof(struct thread, sched_list)==4328,"thread_sched_list_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, thread_spin_sleep_lock_offset)==16,"thread_spin_sleep_lock_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->thread_spin_sleep_lock_offset),unsigned long),"thread_spin_sleep_lock_offset original field type");
_Static_assert(__builtin_offsetof(struct thread, spin_sleep_lock)==4352,"thread_spin_sleep_lock_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, thread_spin_sleep_offset)==24,"thread_spin_sleep_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->thread_spin_sleep_offset),unsigned long),"thread_spin_sleep_offset original field type");
_Static_assert(__builtin_offsetof(struct thread, spin_sleep)==4356,"thread_spin_sleep_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, thread_itimer_enabled_offset)==32,"thread_itimer_enabled_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->thread_itimer_enabled_offset),unsigned long),"thread_itimer_enabled_offset original field type");
_Static_assert(__builtin_offsetof(struct thread, itimer_enabled)==5072,"thread_itimer_enabled_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, cpu_runq_lock_offset)==40,"cpu_runq_lock_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->cpu_runq_lock_offset),unsigned long),"cpu_runq_lock_offset original field type");
_Static_assert(__builtin_offsetof(struct cpu_local_var, runq_lock)==7832,"cpu_runq_lock_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, cpu_runq_offset)==48,"cpu_runq_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->cpu_runq_offset),unsigned long),"cpu_runq_offset original field type");
_Static_assert(__builtin_offsetof(struct cpu_local_var, runq)==7872,"cpu_runq_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, cpu_runq_len_offset)==56,"cpu_runq_len_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->cpu_runq_len_offset),unsigned long),"cpu_runq_len_offset original field type");
_Static_assert(__builtin_offsetof(struct cpu_local_var, runq_len)==7888,"cpu_runq_len_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, cpu_current_offset)==64,"cpu_current_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->cpu_current_offset),unsigned long),"cpu_current_offset original field type");
_Static_assert(__builtin_offsetof(struct cpu_local_var, current)==7848,"cpu_current_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, cpu_timer_enabled_offset)==72,"cpu_timer_enabled_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->cpu_timer_enabled_offset),unsigned long),"cpu_timer_enabled_offset original field type");
_Static_assert(__builtin_offsetof(struct cpu_local_var, timer_enabled)==7980,"cpu_timer_enabled_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, cpu_backlog_list_offset)==80,"cpu_backlog_list_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->cpu_backlog_list_offset),unsigned long),"cpu_backlog_list_offset original field type");
_Static_assert(__builtin_offsetof(struct cpu_local_var, backlog_list)==8056,"cpu_backlog_list_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, timer_timeout_offset)==88,"timer_timeout_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->timer_timeout_offset),unsigned long),"timer_timeout_offset original field type");
_Static_assert(__builtin_offsetof(struct timer, timeout)==0,"timer_timeout_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, timer_waitq_offset)==96,"timer_waitq_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->timer_waitq_offset),unsigned long),"timer_waitq_offset original field type");
_Static_assert(__builtin_offsetof(struct timer, processes)==8,"timer_waitq_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, timer_list_offset)==104,"timer_list_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->timer_list_offset),unsigned long),"timer_list_offset original field type");
_Static_assert(__builtin_offsetof(struct timer, list)==32,"timer_list_offset current055c baseline value");
_Static_assert(__builtin_offsetof(struct timer_runtime_offsets, timer_thread_offset)==112,"timer_thread_offset descriptor position");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets *)0)->timer_thread_offset),unsigned long),"timer_thread_offset original field type");
_Static_assert(__builtin_offsetof(struct timer, thread)==48,"timer_thread_offset current055c baseline value");
