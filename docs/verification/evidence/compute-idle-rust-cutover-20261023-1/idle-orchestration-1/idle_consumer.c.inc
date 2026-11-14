#ifdef MCKERNEL_RUST_PROCESS_HELPERS
static const struct sched_idle_offsets process_idle_offsets = {
	.cpu_runq_lock_offset = offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_irqstate_offset = offsetof(struct cpu_local_var, runq_irqstate),
	.cpu_current_offset = offsetof(struct cpu_local_var, current),
	.cpu_flags_offset = offsetof(struct cpu_local_var, flags),
	.cpu_status_offset = offsetof(struct cpu_local_var, status),
	.cpu_runq_offset = offsetof(struct cpu_local_var, runq),
	.thread_sched_list_offset = offsetof(struct thread, sched_list),
	.thread_status_offset = offsetof(struct thread, status),
	.monitor_status_offset = offsetof(struct ihk_os_cpu_monitor, status),
	.monitor_counter_offset = offsetof(struct ihk_os_cpu_monitor, counter),
};
static const struct sched_idle_values process_idle_values = {
	.cpu_running = CPU_STATUS_RUNNING, .cpu_idle = CPU_STATUS_IDLE,
	.cpu_reserved = CPU_STATUS_RESERVED, .thread_running = PS_RUNNING,
	.thread_stopped = PS_STOPPED, .thread_interruptible = PS_INTERRUPTIBLE,
	.need_migrate = CPU_FLAG_NEED_MIGRATE,
	.monitor_idle = IHK_OS_MONITOR_IDLE, .monitor_kernel = IHK_OS_MONITOR_KERNEL,
};
static const struct sched_idle_callbacks process_idle_callbacks = {
	.current_cpu = sched_idle_current_cpu_bridge,
	.lock = process_spin_lock_bridge, .unlock = process_spin_unlock_bridge,
	.enable_interrupt = cpu_enable_interrupt, .disable_interrupt = cpu_disable_interrupt,
	.schedule = schedule, .migrate = sched_do_migrate_public,
	.consolidate = kmalloc_consolidate_free_list,
	.zero_free = process_sched_zero_free_bridge, .safe_halt = cpu_safe_halt,
};
_Static_assert(sizeof(unsigned long) == 8 && sizeof(void *) == 8,
	"idle callback ABI requires supported LP64");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread *)0)->status), int)
	&& sizeof(((struct thread *)0)->status) == 4, "idle thread status is C int/i32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var *)0)->status), int)
	&& sizeof(((struct cpu_local_var *)0)->status) == 4, "idle CPU status is C int/i32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var *)0)->flags), unsigned int)
	&& sizeof(((struct cpu_local_var *)0)->flags) == 4, "idle CPU flags are u32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ihk_os_cpu_monitor *)0)->status), int)
	&& sizeof(((struct ihk_os_cpu_monitor *)0)->status) == 4, "idle monitor status is C int/i32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ihk_os_cpu_monitor *)0)->counter), unsigned long),
	"idle monitor counter is unsigned long");
_Static_assert(offsetof(struct list_head, next) == 0, "idle scan requires leading next");
_Static_assert(sizeof(struct sched_idle_offsets) == 80, "idle offsets ABI size");
_Static_assert(sizeof(struct sched_idle_values) == 36, "idle constants ABI size");
_Static_assert(sizeof(struct sched_idle_callbacks) == 80, "idle callback ABI size");

static void idle(void)
{
	struct cpu_local_var *v = get_this_cpu_local_var();
	struct ihk_os_cpu_monitor *monitor = v->monitor;

	sched_idle_loop_body_result((unsigned long)v, (unsigned long)monitor,
		&process_idle_offsets, &process_idle_values, &process_idle_callbacks);
}
#else
