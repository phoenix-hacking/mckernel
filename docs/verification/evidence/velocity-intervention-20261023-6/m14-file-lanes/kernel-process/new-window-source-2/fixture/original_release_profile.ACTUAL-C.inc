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
