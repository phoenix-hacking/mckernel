/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
struct f03_clear_host_pte_binding {
	int munmap_nr;
	syscall_do_syscall3_fn_t forward;
	clear_host_pte_log_fn_t log;
};
const struct f03_clear_host_pte_binding f03_clear_host_pte_binding_v1 = {
	.munmap_nr = __NR_munmap,
	.forward = syscall_do_syscall3_bridge,
	.log = clear_host_pte_log_bridge,
};
extern long clear_host_pte(uintptr_t, size_t, int);
