void process_release_thread_profile_bridge(void *thread, void *proc)
{
#ifdef PROFILE_ENABLE
	profile_accumulate_events(thread, proc);
	profile_dealloc_thread_events(thread);
#else
	(void)thread;
	(void)proc;
#endif
}
