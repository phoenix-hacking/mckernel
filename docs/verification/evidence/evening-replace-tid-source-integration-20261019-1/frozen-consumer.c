void process_destroy_thread_replace_tid_bridge(void *proc_arg,
					       void *thread_arg,
					       int new_tid)
{
	__find_and_replace_tid(proc_arg, thread_arg, new_tid);
}
