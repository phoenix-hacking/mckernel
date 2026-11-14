#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	f03_execveat_release_temporaries_v1(envp_flat, argv_flat, desc,
			__FILE__, 7285, 7288, 7290);
#else
	if (envp_flat) {
		kfree_tracked(envp_flat, __FILE__, __LINE__);
	}
	if (argv_flat) {
		kfree_tracked(argv_flat, __FILE__, __LINE__);
	}
	_ihk_mc_free_pages(desc, 4, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
#endif
