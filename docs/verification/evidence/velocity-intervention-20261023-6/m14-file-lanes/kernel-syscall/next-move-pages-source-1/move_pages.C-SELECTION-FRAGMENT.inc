#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void
move_pages_log_bridge(int event, unsigned long value, int error)
{
	(void)error;

	if (event == MOVE_PAGES_LOG_UNSUPPORTED_PID) {
		kprintf("%s: ERROR: only self (pid == 0) is supported\n",
				"sys_move_pages");
	}
	else if (event == MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL) {
		kprintf("%s: ERROR: MPOL_MF_MOVE_ALL not supported\n",
				"sys_move_pages");
	}
	else if (event == MOVE_PAGES_LOG_INIT_MALLOC) {
		kprintf("%s: init malloc: %lu \n", "sys_move_pages", value);
	}
	else if (event == MOVE_PAGES_LOG_INIT_VERIFY) {
		kprintf("%s: init verify: %lu \n", "sys_move_pages", value);
	}
	else if (event == MOVE_PAGES_LOG_PARALLEL) {
		kprintf("%s: parallel: %lu \n", "sys_move_pages", value);
	}
}

long sys_move_pages(int n, ihk_mc_user_context_t *ctx);
#else
static int
move_pages_verify_bridge(struct process_vm *vm, unsigned long addr,
		size_t bytes)
{
	return verify_process_vm(vm, (const void *)addr, bytes);
}

static int
move_pages_get_nr_nodes_bridge(void)
{
	return ihk_mc_get_nr_numa_nodes();
}

static void
move_pages_page_table_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void
move_pages_page_table_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static int
move_pages_smp_call_bridge(void *cpu_set, smp_func_t handler, void *arg)
{
	return smp_call_func((cpu_set_t *)cpu_set, handler, arg);
}

static void
move_pages_log_bridge(int event, unsigned long value, int error)
{
	(void)error;

	if (event == MOVE_PAGES_LOG_UNSUPPORTED_PID) {
		kprintf("%s: ERROR: only self (pid == 0) is supported\n",
				"sys_move_pages");
	}
	else if (event == MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL) {
		kprintf("%s: ERROR: MPOL_MF_MOVE_ALL not supported\n",
				"sys_move_pages");
	}
	else if (event == MOVE_PAGES_LOG_INIT_MALLOC) {
		kprintf("%s: init malloc: %lu \n", "sys_move_pages", value);
	}
	else if (event == MOVE_PAGES_LOG_INIT_VERIFY) {
		kprintf("%s: init verify: %lu \n", "sys_move_pages", value);
	}
	else if (event == MOVE_PAGES_LOG_PARALLEL) {
		kprintf("%s: parallel: %lu \n", "sys_move_pages", value);
	}
}

long sys_move_pages(int n, ihk_mc_user_context_t *ctx)
{
	extern int move_pages_smp_handler(int cpu_index, int nr_cpus, void *arg);
	int pid = ihk_mc_syscall_arg0(ctx);
	unsigned long count = ihk_mc_syscall_arg1(ctx);
	const void **user_virt_addr = (const void **)ihk_mc_syscall_arg2(ctx);
	const int *user_nodes = (const int *)ihk_mc_syscall_arg3(ctx);
	int *user_status = (int *)ihk_mc_syscall_arg4(ctx);
	int flags = ihk_mc_syscall_arg5(ctx);
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return move_pages_body_result(pid, count,
			(unsigned long)user_virt_addr,
			(unsigned long)user_nodes, (unsigned long)user_status,
			flags, vm, &vm->page_table_lock,
			&get_this_cpu_local_var()->current->cpu_set,
			get_this_cpu_local_var()->current->proc, IHK_MC_AP_NOWAIT,
			sizeof(void *), sizeof(int), sizeof(pte_t),
			sizeof(unsigned long), move_pages_verify_bridge,
			syscall_copy_from_user_bridge, syscall_copy_to_user_bridge,
			syscall_alloc_bridge, syscall_mckfd_free_bridge,
			move_pages_get_nr_nodes_bridge,
			move_pages_page_table_lock_bridge,
			move_pages_page_table_unlock_bridge,
			move_pages_smp_call_bridge, move_pages_smp_handler,
			syscall_rdtsc_bridge, move_pages_log_bridge);
}
#endif
