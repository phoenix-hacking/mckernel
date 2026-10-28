#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
extern int util_show_syscall_profile(void);
#else
#line 28277
int util_show_syscall_profile()
{
	int i;
	struct uti_desc *desc = (struct uti_desc *)uti_desc;

	kprintf("Syscall stats for offloaded thread:\n");
	for (i = 0; i < 512; i++) {
		if (desc->syscalls[i]) {
			kprintf("nr=%d #called=%ld\n", i, desc->syscalls[i]);
		}
	}
	
	kprintf("Syscall stats for other threads:\n");
	for (i = 0; i < 512; i++) {
		if (desc->syscalls2[i]) {
			kprintf("nr=%d #called=%ld\n", i, desc->syscalls2[i]);
		}
	}

	return 0;
}
#endif
#line 28297
