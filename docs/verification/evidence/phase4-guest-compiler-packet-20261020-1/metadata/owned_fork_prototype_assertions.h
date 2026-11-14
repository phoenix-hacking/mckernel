/* Verification only: appended to the exact actual whole syscall.c bytes.
 * No added declaration, type replacement, function body or ABI adapter. */
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8,"real x86_64 pointer/word ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&clone_thread),struct thread *(*)(struct thread *,unsigned long,unsigned long,int)),"actual constructor prototype");
_Static_assert(__builtin_types_compatible_p(__typeof__(&release_thread_checked),int(*)(struct thread *)),"actual checked Thread prototype");
_Static_assert(__builtin_types_compatible_p(__typeof__(&release_process_vm_checked),int(*)(struct process_vm *)),"actual checked VM prototype");
#ifdef MCKERNEL_NATIVE_FORK_OWNED_TRANSACTION
_Static_assert(sizeof(struct owned_fork_caller_outcome)==24,"actual outcome matches Rust reprC24");
_Static_assert(__builtin_offsetof(struct owned_fork_caller_outcome,disposition)==0,"actual disposition offset");
_Static_assert(__builtin_offsetof(struct owned_fork_caller_outcome,error)==4,"actual error offset");
_Static_assert(__builtin_offsetof(struct owned_fork_caller_outcome,handle)==8,"actual handle offset");
_Static_assert(sizeof(((struct owned_fork_caller_outcome *)0)->handle)==16,"actual nested handle size");
_Static_assert(__builtin_offsetof(struct owned_fork_caller_outcome,handle.epoch)==16,"actual nested epoch offset");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_fork_construct_current_v1),struct thread *(*)(struct thread *,unsigned long,unsigned long,int,int,void **)),"actual Rust-constructor caller declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_fork_cancel_constructed_current_v1),int(*)(void *)),"actual Rust-cancel caller declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_fork_owned_caller_current_v2),int(*)(struct thread *,struct thread *,int,unsigned long,void *,struct owned_fork_caller_outcome *)),"actual Rust-owned caller declaration");
#endif
