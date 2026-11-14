#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void move_pages_log_bridge(int event, unsigned long value, int error);
#else
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
#endif
