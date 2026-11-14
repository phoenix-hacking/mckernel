/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Declarative ABI fragment only, insert before original do_execveat definition.
 * Tracking line data in the call fragment is bound to the saved C preimage;
 * root must rebind this origin data explicitly if rebasing that preimage. */
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
extern void f03_execveat_release_temporaries_v1(void *envp_flat, void *argv_flat,
        void *descriptor, const char *file, int envp_line, int argv_line,
        int descriptor_line);
#endif
