static void process_replace_tid_log_bridge(int tid, void *thread, int new_tid)
{
	dkprintf("%s: tid %d (thread %p) has been relaced with tid %d\n",
		"__find_and_replace_tid", tid, thread, new_tid);
}
