/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
extern void *f03_execveat_allocate_descriptor_v1(const char *file,
        int source_line, int *error);
#endif
