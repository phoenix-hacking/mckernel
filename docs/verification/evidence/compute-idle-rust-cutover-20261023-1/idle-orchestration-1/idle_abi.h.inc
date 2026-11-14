/* Caller preserves the existing idle lifetime/IRQ/runqueue contract. */
struct sched_idle_offsets {
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_runq_irqstate_offset;
	unsigned long cpu_current_offset;
	unsigned long cpu_flags_offset;
	unsigned long cpu_status_offset;
	unsigned long cpu_runq_offset;
	unsigned long thread_sched_list_offset;
	unsigned long thread_status_offset;
	unsigned long monitor_status_offset;
	unsigned long monitor_counter_offset;
};

struct sched_idle_values {
	int cpu_running;
	int cpu_idle;
	int cpu_reserved;
	int thread_running;
	int thread_stopped;
	int thread_interruptible;
	unsigned int need_migrate;
	int monitor_idle;
	int monitor_kernel;
};

struct sched_idle_callbacks {
	unsigned long (*current_cpu)(void);
	unsigned long (*lock)(unsigned long lock_addr);
	void (*unlock)(unsigned long lock_addr, unsigned long irqstate);
	void (*enable_interrupt)(void);
	void (*disable_interrupt)(void);
	void (*schedule)(void);
	void (*migrate)(void);
	void (*consolidate)(void);
	void (*zero_free)(void);
	void (*safe_halt)(void);
};

unsigned long sched_idle_current_cpu_bridge(void);
void process_sched_zero_free_bridge(void);
void sched_idle_begin_body_result(unsigned long cpu_addr,
	const struct sched_idle_offsets *offsets,
	const struct sched_idle_values *values,
	const struct sched_idle_callbacks *callbacks);
void sched_idle_iteration_body_result(unsigned long cpu_addr,
	unsigned long monitor_addr, const struct sched_idle_offsets *offsets,
	const struct sched_idle_values *values,
	const struct sched_idle_callbacks *callbacks);
void sched_idle_loop_body_result(unsigned long cpu_addr,
	unsigned long monitor_addr, const struct sched_idle_offsets *offsets,
	const struct sched_idle_values *values,
	const struct sched_idle_callbacks *callbacks) __attribute__((noreturn));

