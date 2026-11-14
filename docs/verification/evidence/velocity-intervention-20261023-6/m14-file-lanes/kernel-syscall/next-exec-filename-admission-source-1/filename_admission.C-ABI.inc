/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
extern int f03_execveat_filename_admission_v1(struct process_vm *vm,
        const void *filename);
#endif
