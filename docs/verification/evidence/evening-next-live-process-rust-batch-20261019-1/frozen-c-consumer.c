void
release_process(struct process *proc)
{
	process_release_process_body_result(proc,
		__builtin_offsetof(struct process, refcount),
		__builtin_offsetof(struct process, tids),
		__builtin_offsetof(struct process, main_thread),
		__builtin_offsetof(struct process, mckfd),
		__builtin_offsetof(struct process, mckfd_lock),
		__builtin_offsetof(struct mckfd, next),
		NULL,
		process_current_resource_set_bridge,
		process_release_hash_detach_bridge,
		process_release_sibling_detach_bridge,
		process_release_profile_bridge,
		process_free_thread_pages_bridge,
		process_spin_lock_bridge,
		process_spin_unlock_bridge,
		process_mckfd_free_bridge,
		process_optional_free_bridge,
		process_release_final_cleanup_bridge);
}
